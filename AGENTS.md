# AGENTS.md — 项目交接与智能体操作指南

> 本文档供接手本项目的 AI 编程智能体（Claude Code / Cursor / Copilot 等）与人类协作者阅读。
> 它承载了本项目从出题到上线的全部关键决策、机制细节与环境坑。
> 配合根目录 `README.md`、`demo/README.md` 与本地 `answer.md`（答案总表，gitignore 不入库）使用。

---

## 1. 项目是什么

郑州航空工业管理学院计算机学院"ZUA-2026 新生网页解密活动"。
新生通过网页闯关破译"失联无人机黑匣子"的 15 关谜题，限时一周。
**当前状态：完整可玩，main 分支为唯一事实源**（本地与远端已同步）。

## 2. 快速上手（开发机 Windows）

```powershell
cd demo
powershell -ExecutionPolicy Bypass -File setup.ps1   # 仅首次：建 .venv + 装依赖
# 开发调试：
.\start-local.bat     # Cookie Secure OFF + --reload 热重载 + 局域网可访问
# 或手动： .venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
- 访问 `http://127.0.0.1:8000`；外网测试用 SakuraFrp 隧道 + `start-prod.bat`（Secure Cookie ON）
- `demo\data\puzzle.db` 是 SQLite 运行库（启动自动备份到 `data/backup/`，保留 10 份）
- **热重载协作模式**：服务进程由人类维护（窗口），智能体只改文件，uvicorn --reload 自动生效——不要抢占 8000 端口

## 3. 代码地图

| 文件 | 职责 |
|---|---|
| `demo/main.py` | FastAPI：会话、解锁门禁、答案校验、限流/会话锁定、提示门禁、排行、安全头中间件 |
| `demo/levels.py` | ⚠️ 15 关定义：题干 `prompt`、答案 `answers`、提示 `hints`、碎片 `fragment`、内嵌 `embed`、交互 `guess`/`bars`/`console` |
| `demo/db.py` | SQLite：players / solves / level_views / hints_revealed 四张表 |
| `demo/config.py` | 统一配置：PORT、HINT_UNLOCK_DELAYS、EMBEDDABLE_STATIC_HTML、限流参数、COOKIE_SECURE |
| `demo/static/` | 前端（index.html / style.css / app.js）+ 关卡素材页（signal-lamp.html、cargo-note.html、plaza.svg、js/） |
| `answer.md`（本地） | 15 关答案总表 + 碎片链 + 维护清单（**已 gitignore，禁止入库**） |

## 4. 核心机制（改代码前必读）

- **顺序解锁**：第 N 关需前 N−1 关全部 solved；未解锁 GET 返回 403；碎片按 `config.FRAGMENT_LEVEL_RANGE` 拼接为终极答案（服务端动态计算，改碎片=改终极答案）
- **提示系统**：解锁记录持久化在 `hints_revealed` 表；第 k 条提示需 `HINT_UNLOCK_DELAYS[k]` 秒（自首次打开关卡 `level_views.viewed_at` 起算，服务端计时）；前端 `renderHintList` 常驻显示，刷新/重启不丢
- **内嵌素材**：`levels.py` 的 `embed` 字段 → 前端 iframe 渲染；**素材路径必须在 `config.EMBEDDABLE_STATIC_HTML` 白名单内**（否则被安全头拦截报 ERR_BLOCKED_BY_RESPONSE）；素材页脚本一律外置 .js（CSP `script-src 'self'` 禁内联）
- **安全**：答案只存服务端；昵称正则白名单 + 一次性登记 + textContent 渲染（防 XSS）；答错单关冷却 + 会话级累计锁定；CSP/XFO 头全局，白名单页放行同源 frame；/docs 已关闭
- **限流均为内存态**：重启清零；多 worker / 多进程会失效，需迁移到 Redis 或 DB

## 5. 测试方法（无浏览器时）

```powershell
# 会话：cookie 文件必须 -c 保存
curl.exe -c ck.txt http://127.0.0.1:8000/api/me
curl.exe -b ck.txt http://127.0.0.1:8000/api/levels
# 提交答案（PowerShell 引号坑：用 JSON 文件 + -d @file）
Set-Content b.json '{"answer":"zua"}' -NoNewline -Encoding utf8
curl.exe -b ck.txt -c ck.txt -H "Content-Type: application/json" -d @b.json http://127.0.0.1:8000/api/levels/1/check
# 未解锁关卡应 403：curl.exe -o NUL -w "%{http_code}" http://127.0.0.1:8000/api/levels/5
```
- 提示时间门禁测试：先 GET 打开关卡，再 `UPDATE level_views SET viewed_at=viewed_at-4000 WHERE player_id=(SELECT MAX(id) FROM players)` 回拨模拟 5/15/30 分钟已过
- 改完代码回归清单：L1 通关 → L2 内嵌灯可见且 welcome 可过 → 提示逐条解锁且重启后仍在 → 安全头正确（素材页 `frame-ancestors 'self'`、首页 DENY）→ 15 关总数

## 6. 维护红线（不可妥协）

1. **改 `levels.py` 的题面/答案/提示，必须同步 `answer.md`**（本地文件，同步后无需提交）
2. 新增内嵌素材页四步：放 `static/` → 加进 `config.EMBEDDABLE_STATIC_HTML` → JS 外置 → 同步 answer.md
3. 编码类题目（摩斯/Base64/二进制）改动后**必须用程序实测解码**一遍（本项目曾因摩斯码漏点翻车）
4. 答案空间必须大到无法在线穷举（L12 答案 0~9 为已知隐患，改版建议：问循环节长度 60）
5. `data/` 与 `answer.md` 不入 git；正式活动期间数据库每日异机备份

## 7. 已知问题与待办（正式版）

- [ ] L12 答案空间仅 0~9，可被穷举（限流只能拖慢）
- [ ] 终极题仍是"碎片拼接"占位，正式版替换为 校史年份/社团暗号 + 转换逻辑（levels.py 已留注释位）
- [ ] 提示/限流为内存态，多 worker 需 Redis
- [ ] 正式部署：2C2G 服务器 + Nginx + 域名证书 + `start-prod.bat` + 每日备份 cron

## 8. 环境特殊性（迁移到新机器后必须重新验证）

本项目开发机存在沙箱限制，以下行为是**该环境特有**的，新环境大概率不需要：
- git 需 `-c http.sslBackend=openssl -c http.sslVerify=false`（沙箱 mTLS 拦截）
- pip 走 HTTP 镜像：`-i http://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com`
- Python 临时目录写权限受限（venv/ensurepip 需提权）
- 新机器上请按 README 的 setup.ps1 正常流程走一遍，并自行验证网络与依赖

## 9. 协作工作流

- 分支策略：小改动可直接 main；功能级改动开 `feat/xxx` 分支 → PR 合入（仓库已有 PR 合并先例）
- 提交风格：中文 conventional 前缀（`feat:` / `fix:` / `docs:` / `puzzle:` / `chore:`），机制与内容分提交
- 改后端代码后：若服务非 --reload 模式需重启；确认不与他人抢 8000 端口
- 本文件随项目演进同步更新（交接给下一个 Agent 时它就是唯一入口）
