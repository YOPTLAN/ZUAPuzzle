# ZUA-2026 · 新生网页解密活动

> 郑州航空工业管理学院 计算机学院 · 面向大一新生的入门级网页解密活动
> 一周制 · 线上闯关 · 零基础可玩

**故事主题**：编号 ZUA-2026 的校园测绘无人机失联，只传回一段加密信号。
新生扮演"信号分析小组"成员，逐关破译黑匣子数据，最终拼出无人机留下的秘密。

---

## ✨ 特性

- **15 关 · 四章**难度曲线：启程（编码入门）→ 探秘（网页即谜题）→ 基础算法训练（查找/排序/递归/递推/DP/图）→ 终局（碎片拼装）
- **交互式关卡**：二分查找猜数游戏、可拖拽排序试验场、信号灯摩斯观察窗、藏头货单
- **服务端权威**：答案与未解锁关卡只存在服务端；顺序解锁门禁；提示按打开题目后 5/15/30 分钟分级解锁（服务端计时）
- **提示持久化**：已解锁提示入库，刷新页面 / 重启服务都不丢，常驻显示
- **游戏化**：碎片收集、通关排行榜、三级提示、每日彩蛋位
- **安全加固**：CSP/XFO 响应头（含同源内嵌白名单）、昵称白名单防存储型 XSS、单关限速 + 会话级连错锁定、Cookie HttpOnly/Secure 双模式、接口文档页关闭
- **零框架依赖**：前端原生 HTML/CSS/JS；后端仅 FastAPI + SQLite

## 🚀 快速开始

环境要求：Windows + Python 3.12+（首次运行 `setup.ps1` 会自动创建虚拟环境并安装依赖）。

```powershell
cd demo
powershell -ExecutionPolicy Bypass -File setup.ps1   # 仅首次：建 venv + 装依赖
```

| 场景 | 启动方式 | 说明 |
|---|---|---|
| 本机 / 局域网测试 | 双击 `demo\start-local.bat` | Cookie Secure 关闭（HTTP 可登录）、热重载开启、自动探测局域网 IP |
| frp 隧道 / HTTPS 访问 | 双击 `demo\start-prod.bat` | Cookie Secure 开启（浏览器仅在 HTTPS 携带会话）、无热重载 |

启动后访问 `http://127.0.0.1:8000`。清空数据库（慎用）：`powershell -File demo\reset_db.ps1`。

## 🗂️ 目录结构

```
├── answer.md            # 答案总表（组织者专用，已 gitignore，勿入库）
├── 出题大纲 md           # 设计文档
└── demo/
    ├── main.py          # FastAPI 服务端（校验/门禁/限流/排行）
    ├── config.py        # 统一配置：端口、提示时长、内嵌白名单、Cookie 模式…
    ├── db.py            # SQLite（players/solves/level_views/hints_revealed）
    ├── levels.py        # ⚠️ 15 关定义 + 答案（组织者专用，改题必同步 answer.md）
    ├── setup.ps1        # 一键安装脚本
    ├── start-local.bat / start-prod.bat / reset_db.ps1
    ├── static/          # 前端与素材页（信号灯 / 货单 / SVG…）
    └── data/puzzle.db   # 运行数据库（自动备份至 data/backup/，保留 10 份）
```

## ⚙️ 常用配置（`demo/config.py`）

| 配置项 | 默认 | 说明 |
|---|---|---|
| `PORT` | 8000 | 服务端口 |
| `HINT_UNLOCK_DELAYS` | (300, 900, 1800) | 提示一/二/三解锁延迟（秒，自首次打开关卡起算） |
| `EMBEDDABLE_STATIC_HTML` | 两个素材页 | 允许被 iframe 内嵌的白名单路径 |
| `WRONG_ANSWER_COOLDOWN` / `SESSION_*` | 3s / 20 次·10 分钟 | 答错冷却与会话级锁定 |

## 🔒 安全设计要点

1. 答案只存在于服务端 `levels.py`；未解锁关卡接口返回 403，前端拿不到内容
2. 昵称走正则白名单 + 一次性登记，渲染全程 `textContent`（防存储型 XSS）
3. 全站安全响应头：CSP（script-src 'self'，站点无内联脚本）、nosniff、XFO DENY；
   可内嵌素材页通过 `config.EMBEDDABLE_STATIC_HTML` 白名单放行同源 frame
4. 答错触发单关冷却；跨关卡累计答错触发会话级锁定
5. 接口文档页（/docs、/openapi.json）已关闭

## 🧭 维护约定（红线）

1. **改题必同步 `answer.md`**（该文件已入库，但正式活动前可选择移出历史——见 gitignore 注释）
2. 新增内嵌素材页：放入 `static/` → 追加 `config.EMBEDDABLE_STATIC_HTML` → 页面脚本一律外置 .js → 同步 answer.md
3. 所有编码类题目改动后必须用程序实测解码一遍再上线
4. `data/` 不入 git；正式活动期间每日另拷一份到仓库外

## 📦 部署提示

- 测试期直接用 SakuraFrp 隧道 + `start-local.bat`
- 正式活动建议迁移至自有服务器（2C2G 即可）：`start-prod.bat`（Secure Cookie）+
  Nginx 反代 + 域名证书；SQLite 单文件每日备份
- 单进程内存限流的设计上限约几百并发玩家，超出再考虑多实例 + Redis

---

*计算机学院 · 信号分析小组 · 编程队 / ACM 队 / 编程社团联合出品*
