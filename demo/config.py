# -*- coding: utf-8 -*-
"""ZUA-2026 Demo 统一配置模块
所有可调参数集中在此，修改后即时生效，无需改动业务代码。
"""
import os
from pathlib import Path
from dataclasses import dataclass

BASE_DIR = Path(__file__).resolve().parent


@dataclass(frozen=True)
class Config:
    # 服务
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Cookie / Session
    COOKIE_NAME: str = "zua_session"
    COOKIE_MAX_AGE: int = 7 * 24 * 3600  # 7 天
    # Cookie Secure 标志开关：由启动脚本决定（start-local.bat 关 / start-prod.bat 开）
    COOKIE_SECURE: bool = os.environ.get("ZUA_COOKIE_SECURE", "0") == "1"

    # 限流（内存简易限流，多 worker 需换 Redis）
    RATE_LIMIT_PER_MIN: int = 10      # 单关答案校验：每分钟最多尝试次数
    RATE_LIMIT_COOLDOWN: int = 60     # 频率统计窗口（秒）
    WRONG_ANSWER_COOLDOWN: int = 3    # 每次答错后的短冷却（秒）
    GUESS_RATE_PER_MIN: int = 30      # 猜数关交互频率上限（一局最多 11 次）

    # 会话级惩罚：跨关卡累计答错达上限后整体锁定（防逐关枚举短数字答案）
    SESSION_MAX_WRONG: int = 20       # 错误次数上限
    SESSION_WRONG_WINDOW: int = 600   # 错误计数窗口（秒）
    SESSION_COOLDOWN: int = 600       # 触发上限后的锁定时长（秒）

    # 提示解锁延迟（自首次打开关卡起算，单位秒）：提示一 / 提示二 / 提示三
    HINT_UNLOCK_DELAYS: tuple = (300, 900, 1800)

    # 可内嵌素材白名单（同源 iframe）：新增可内嵌页面时在此追加路径，
    # 中间件会对其放行 frame-ancestors 'self' 并省略 X-Frame-Options
    EMBEDDABLE_STATIC_HTML: tuple = (
        "/static/signal-lamp.html",
        "/static/cargo-note.html",
    )

    # 数据库与备份
    DATA_DIR: Path = BASE_DIR / "data"
    DB_NAME: str = "puzzle.db"
    BACKUP_DIR: Path = BASE_DIR / "data" / "backup"
    BACKUP_KEEP: int = 10
    BACKUP_PREFIX: str = "puzzle-"

    # 会话 / 玩家
    NICKNAME_MAX_LEN: int = 24
    TOKEN_HASH_CHARS: int = 8  # 取 token sha256 前 N 字符做确定性种子

    # 关卡元数据
    FINAL_LEVEL_ID: int = 15
    FRAGMENT_LEVEL_RANGE: tuple = (1, 14)  # 含首含尾

    # Python 环境与依赖安装（setup.ps1 运行时动态检测，不预设版本）
    PIP_INDEX_URL: str = "https://pypi.tuna.tsinghua.edu.cn/simple"


config = Config()