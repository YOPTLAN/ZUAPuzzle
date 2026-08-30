# -*- coding: utf-8 -*-
"""ZUA-2026 黑匣子破译行动 —— FastAPI 服务端（方案 C）

安全红线：答案与未解锁关卡只存在于服务端，前端永远拿不到。

运行：
    uvicorn main:app --host 0.0.0.0 --port 8000
"""
import hashlib
import re
import secrets
import time
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import db
from levels import (LEVELS, all_regular_solved, get_level, regular_level_ids,
                    total_levels)

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
cfg = config.config


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(
    title="ZUA-2026 黑匣子破译行动",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None,        # 关闭接口文档页（不对外暴露接口结构）
    redoc_url=None,
    openapi_url=None,
)

# ---- 可内嵌素材页（同源 iframe 使用）：白名单见 config.EMBEDDABLE_STATIC_HTML ----


# ---- 安全响应头（XSS 纵深防御 + 基础加固；上线独立域名后可再加 HSTS）----
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    path = request.url.path
    embeddable = path in cfg.EMBEDDABLE_STATIC_HTML
    frame_ancestors = "'self'" if embeddable else "'none'"
    # 说明：style-src 含 'unsafe-inline' 是因前端用内联 style 属性渲染动态柱状图；
    # 防 XSS 核心的 script-src 保持严格 'self'（站点脚本全部外置，无内联脚本）
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' 'unsafe-inline' fonts.googleapis.com; "
        "font-src 'self' fonts.gstatic.com; img-src 'self'; connect-src 'self'; "
        f"object-src 'none'; base-uri 'self'; frame-ancestors {frame_ancestors}")
    response.headers["X-Content-Type-Options"] = "nosniff"
    # no-cache = 可缓存但每次必须回源校验（StaticFiles 自带 ETag，命中时 304 极廉价）：
    # 前端改动后玩家普通刷新即可拿到新版，杜绝“改了脚本页面不更新”的缓存问题
    response.headers["Cache-Control"] = "no-cache"
    if not embeddable:
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response


# ---- 统一包装参数校验错误，避免泄露 Pydantic/框架特征 ----
@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": "参数错误"}, status_code=422)


# ---- 简易内存限流（DEMO 够用；多进程/多 worker 时需换 Redis/DB）----
wrong_cooldown_until = {}            # (token, level_id) -> 冷却截止时间
wrong_attempts = defaultdict(list)   # (token, level_id) -> [时间戳]
guess_times = defaultdict(list)      # token -> 猜数交互 [时间戳]
session_wrong = defaultdict(list)    # token -> 跨关卡累计错误 [时间戳]
session_cooldown_until = {}          # token -> 会话级锁定截止时间


# ---------------- 会话 ----------------
def ensure_player(request: Request, response: Response):
    token = request.cookies.get(cfg.COOKIE_NAME)
    if not token:
        token = secrets.token_hex(16)
        # HttpOnly 禁止 JS 读取（防 XSS 窃取会话）；SameSite=Lax 防 CSRF；
        # Secure 仅 HTTPS 传输——由启动模式决定（见 config.COOKIE_SECURE）
        response.set_cookie(
            cfg.COOKIE_NAME, token,
            max_age=cfg.COOKIE_MAX_AGE,
            httponly=True, secure=cfg.COOKIE_SECURE, samesite="lax",
        )
    return db.get_or_create_player(token)


# ---------------- 工具 ----------------
def normalize(ans: str) -> str:
    """答案归一化：小写、去空白、全角转半角。"""
    out = []
    for ch in ans.lower():
        code = ord(ch)
        if code == 0x3000:
            code = 0x20
        elif 0xFF01 <= code <= 0xFF5E:
            code -= 0xFEE0
        if chr(code) not in " \t\r\n":
            out.append(chr(code))
    return "".join(out)


def is_unlocked(player, level: dict) -> bool:
    """顺序解锁：第 1 关永远可玩，其余要求前面全部通过。
    附加关（extra）按 requires 指定的前置关解锁：requires=10 → 需第 1~10 关全通过。"""
    if level["id"] == 1:
        return True
    need = level.get("requires", level["id"] - 1)
    solved = db.solved_set(player["id"])
    return all(pid in solved for pid in range(1, need + 1))


def public_level(level: dict, solved: bool, unlocked: bool) -> dict:
    d = {
        "id": level["id"],
        "stage": level["stage"],
        "title": level["title"],
        "difficulty": level["difficulty"],
        "type": level["type"],
        "solved": solved,
        "unlocked": unlocked,
        "guess": level.get("guess"),
        "extra": bool(level.get("extra")),
    }
    if level.get("label"):  # 附加关展示编号（如 "10（附加题）"）
        d["label"] = level["label"]
    # ⚠️ 附加关没有 fragment 字段，必须容忍缺失（见 levels.py 附加关规范）
    if solved and "fragment" in level:
        d["fragment"] = level["fragment"]  # 已通关才可见碎片，前端据此重建碎片收集
    return d


def _freq_wait(stamps: list, limit: int, window: int) -> int:
    """滑动窗口频率检查：返回还需等待秒数；0 表示放行。"""
    now = time.time()
    recent = [t for t in stamps if now - t < window]
    stamps[:] = recent
    if len(recent) >= limit:
        return window - int(now - recent[0]) + 1
    return 0


def rate_limited(token: str, level_id: int) -> int:
    """单关答案校验限速：返回还需等待秒数；0 表示可以继续尝试。"""
    key = (token, level_id)
    if wrong_cooldown_until.get(key, 0) > time.time():
        return int(wrong_cooldown_until[key] - time.time()) + 1
    return _freq_wait(wrong_attempts[key], cfg.RATE_LIMIT_PER_MIN,
                      cfg.RATE_LIMIT_COOLDOWN)


def session_limited(token: str) -> int:
    """会话级惩罚：跨关卡累计答错达上限后整体锁定一段时间。"""
    if session_cooldown_until.get(token, 0) > time.time():
        return int(session_cooldown_until[token] - time.time()) + 1
    wait = _freq_wait(session_wrong[token], cfg.SESSION_MAX_WRONG,
                      cfg.SESSION_WRONG_WINDOW)
    if wait:
        until = time.time() + cfg.SESSION_COOLDOWN
        session_cooldown_until[token] = until
        return cfg.SESSION_COOLDOWN
    return 0


def record_wrong(token: str, level_id: int):
    """记录一次答错：触发单关短冷却 + 计入会话级累计。"""
    now = time.time()
    wrong_cooldown_until[(token, level_id)] = now + cfg.WRONG_ANSWER_COOLDOWN
    wrong_attempts[(token, level_id)].append(now)
    session_wrong[token].append(now)


# ---------------- 页面 ----------------
@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


# ---- 第 7 关素材：404 链（/missing → robots.txt → /secret）----
@app.get("/missing")
def missing():
    return HTMLResponse(
        "<h1>404 NOT FOUND</h1><p>线索没有丢——它被拦在了一个叫 robots.txt 的地方？<br>"
        "去 <a href='/robots.txt'>/robots.txt</a> 看看。</p>",
        status_code=404,
    )


@app.get("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nDisallow: /secret\n"
        "# 机器人守则：不让机器人看的东西，人类也别错过\n",
        media_type="text/plain",
    )


@app.get("/secret")
def secret():
    return HTMLResponse(
        "<h1>🎉 秘密页面</h1><p>你找到了。答案：<b>robot</b></p>"
    )


# ---------------- API ----------------
@app.get("/api/me")
def api_me(request: Request, response: Response):
    player = ensure_player(request, response)
    return {"token": player["token"][:8], "nickname": player["nickname"],
            "total": total_levels()}


@app.get("/api/levels")
def api_levels(request: Request, response: Response):
    player = ensure_player(request, response)
    solved = db.solved_set(player["id"])
    return [public_level(lv, lv["id"] in solved, is_unlocked(player, lv))
            for lv in LEVELS]


@app.get("/api/levels/{level_id}")
def api_level(request: Request, response: Response, level_id: int):
    player = ensure_player(request, response)
    lv = get_level(level_id)
    if not lv:
        return JSONResponse({"detail": "no such level"}, status_code=404)
    if not is_unlocked(player, lv):
        return JSONResponse({"detail": "locked"}, status_code=403)
    db.mark_level_view(player["id"], lv["id"])
    viewed_at = db.first_viewed_at(player["id"], lv["id"])
    revealed_idx = db.revealed_hint_indices(player["id"], lv["id"])
    solved = level_id in db.solved_set(player["id"])
    return {
        "id": lv["id"], "stage": lv["stage"], "title": lv["title"],
        "difficulty": lv["difficulty"], "type": lv["type"],
        "story": lv["story"], "prompt": lv["prompt"],
        "solved": solved, "hints_count": len(lv["hints"]),
        "label": lv.get("label"),
        "revealed_hints": [{"index": i, "text": lv["hints"][i]}
                           for i in revealed_idx if i < len(lv["hints"])],
        "guess": lv.get("guess"),
        "console": lv.get("console"),
        "bars": lv.get("bars"),
        "embed": lv.get("embed"),
        "signal": lv.get("signal"),   # L2 摩斯点划串（服务端由答案生成，客户端不含明文）
        # 教学代码（C 参考实现）只在通关后下发，未通关恒为 None（防泄题解法）
        "code": lv.get("code") if solved else None,
        "viewed_at": viewed_at,
        "server_now": time.time(),
        "hint_delays": list(cfg.HINT_UNLOCK_DELAYS),
    }


class CheckIn(BaseModel):
    answer: str


@app.post("/api/levels/{level_id}/check")
def api_check(request: Request, response: Response, level_id: int, body: CheckIn):
    player = ensure_player(request, response)
    lv = get_level(level_id)
    if not lv or lv.get("type") != "text":
        return JSONResponse({"detail": "no such level"}, status_code=404)
    if not is_unlocked(player, lv):
        return JSONResponse({"detail": "locked"}, status_code=403)
    if level_id in db.solved_set(player["id"]):
        return {"correct": True, "already": True, "message": "这关你已经通过啦"}
    wait = rate_limited(player["token"], level_id)
    if not wait:
        wait = session_limited(player["token"])
    if wait:
        return JSONResponse(
            {"correct": False, "message": f"尝试太频繁，请 {wait} 秒后再试",
             "cooldown": wait}, status_code=429)
    guess = normalize(body.answer)
    if guess in [normalize(a) for a in lv["answers"]]:
        db.record_solve(player["id"], level_id)
        solved = db.solved_set(player["id"])
        return {
            "correct": True,
            "fragment": lv.get("fragment"),
            "fragment_hint": lv.get("fragment_hint"),
            "code": lv.get("code"),
            "solved_count": len(solved),
            "done": all_regular_solved(solved),
        }
    record_wrong(player["token"], level_id)
    return {"correct": False, "message": f"答案不对，再想想（{cfg.WRONG_ANSWER_COOLDOWN} 秒后可重试）", "cooldown": cfg.WRONG_ANSWER_COOLDOWN}


class GuessIn(BaseModel):
    guess: int


@app.post("/api/levels/{level_id}/guess")
def api_guess(request: Request, response: Response, level_id: int, body: GuessIn):
    player = ensure_player(request, response)
    lv = get_level(level_id)
    if not lv or lv.get("type") != "guess":
        return JSONResponse({"detail": "no such level"}, status_code=404)
    if not is_unlocked(player, lv):
        return JSONResponse({"detail": "locked"}, status_code=403)
    if level_id in db.solved_set(player["id"]):
        return {"result": "correct", "solved": True}
    g = lv["guess"]
    if not (g["lo"] <= body.guess <= g["hi"]):
        return JSONResponse({"detail": "超出范围"}, status_code=400)
    token = player["token"]
    wait = _freq_wait(guess_times[token], cfg.GUESS_RATE_PER_MIN, 60)
    if wait:
        return JSONResponse(
            {"detail": f"猜测太频繁，请 {wait} 秒后再试"}, status_code=429)
    guess_times[token].append(time.time())
    used = len(guess_times[token])
    if used > g["max_guesses"]:
        return JSONResponse(
            {"result": "fail",
             "message": f"超过 {g['max_guesses']} 次限制，重新开始。",
             "used": used, "max": g["max_guesses"]}, status_code=400)
    # 目标数由 token 确定性派生，无需存储
    span = g["hi"] - g["lo"] + 1
    target = (int(hashlib.sha256(token.encode()).hexdigest()[:cfg.TOKEN_HASH_CHARS], 16) % span) + g["lo"]
    if body.guess == target:
        db.record_solve(player["id"], level_id)
        solved = db.solved_set(player["id"])
        return {
            "result": "correct", "solved": True, "used": used,
            "fragment": lv.get("fragment"), "fragment_hint": lv.get("fragment_hint"),
            "code": lv.get("code"),
            "solved_count": len(solved), "done": all_regular_solved(solved),
        }
    return {"result": "higher" if body.guess < target else "lower",
            "used": used, "max": g["max_guesses"]}


@app.get("/api/levels/{level_id}/hints")
def api_hint(request: Request, response: Response, level_id: int):
    player = ensure_player(request, response)
    lv = get_level(level_id)
    if not lv:
        return JSONResponse({"detail": "no such level"}, status_code=404)
    if not is_unlocked(player, lv):
        return JSONResponse({"detail": "locked"}, status_code=403)
    # 已解锁提示持久化在数据库中（重启不丢）；下一条待解锁提示 = 已解锁数量
    revealed_idx = db.revealed_hint_indices(player["id"], level_id)
    idx = len(revealed_idx)
    total_hints = len(lv["hints"])
    all_texts = [lv["hints"][i] for i in revealed_idx if i < total_hints]

    if idx >= total_hints:
        return {"hint": None, "hint_index": idx, "all_used": True,
                "revealed_texts": all_texts}

    # 时间门禁：以【首次打开关卡】的时刻起算（服务端计时，防改本地时钟）
    delays = cfg.HINT_UNLOCK_DELAYS
    first = db.first_viewed_at(player["id"], level_id) or time.time()
    elapsed = time.time() - first
    need = delays[idx] if idx < len(delays) else delays[-1]
    if elapsed < need:
        wait = int(need - elapsed)
        return {
            "hint": None, "hint_index": idx, "locked": True,
            "wait_seconds": wait,
            "revealed_texts": all_texts,
            "message": f"提示 {idx + 1} 将在打开本题第 {need // 60} 分钟后解锁，还需等待 {wait} 秒",
        }
    db.reveal_hint(player["id"], level_id, idx)
    all_texts.append(lv["hints"][idx])
    return {
        "hint": lv["hints"][idx], "hint_index": idx,
        "all_used": idx + 1 >= total_hints,
        "revealed_texts": all_texts,
    }


class RankIn(BaseModel):
    nickname: str


# 昵称白名单：仅中英文、数字、下划线（防存储型 XSS，服务端治本）
NICKNAME_PATTERN = re.compile(r"^[a-zA-Z0-9\u4e00-\u9fff_]{1,24}$")


@app.post("/api/rank/register")
def api_rank_register(request: Request, response: Response, body: RankIn):
    player = ensure_player(request, response)
    if player["nickname"]:
        # 每 session 仅可登记一次，防反复改名刷屏/抢注
        return JSONResponse({"detail": "该会话已登记过呼号，无法重复登记"},
                            status_code=409)
    nick = body.nickname.strip()
    if not nick:
        return JSONResponse({"detail": "昵称不能为空"}, status_code=400)
    if len(nick) > cfg.NICKNAME_MAX_LEN or not NICKNAME_PATTERN.fullmatch(nick):
        return JSONResponse(
            {"detail": "昵称仅支持中文、英文、数字和下划线，长度 1~24"},
            status_code=400)
    db.set_nickname(player["id"], nick)
    return {"ok": True, "nickname": nick}


@app.get("/api/rank")
def api_rank(request: Request, response: Response):
    player = ensure_player(request, response)
    # 排行榜只统计主线常规关（按 id 白名单，附加关无论什么 id 都不参与）
    rows = db.finished_rank(total_levels(), regular_level_ids())
    me_id = player["id"]
    rank = []
    for i, r in enumerate(rows, 1):
        rank.append({
            "rank": i,
            "nickname": r["nickname"] or "匿名玩家",
            "finished_at": r["finished_at"],
            "me": r["id"] == me_id,
        })
    return {"rank": rank, "total_finished": len(rank)}


app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
