# ZUA-2026 黑匣子破译行动 · 第一份 DEMO（FastAPI 方案 C）

服务端校验答案 + 关卡门禁 + SQLite + 交互式猜数关 + 排行榜。
**安全设计**：答案与未解锁关卡只存在于服务端 `levels.py`，前端无任何答案
（第 1 关教学关除外——答案故意写在 HTML 注释里，这是关卡设计的一部分）。

## 一、项目结构

```
demo/
├── main.py            # FastAPI 服务（答案校验 / 解锁门禁 / 限流 / 排行榜）
├── db.py              # SQLite：players / solves 两张表
├── levels.py          # ⚠️ 关卡定义 + 答案（组织者专用，勿外传）
├── requirements.txt
├── setup.ps1          # 一键启动脚本（建 venv + 装依赖 + 启动）
├── static/
│   ├── index.html     # 前端页面（雷达主题）
│   ├── style.css
│   └── app.js         # 前端逻辑（不含答案）
└── data/puzzle.db     # 运行时自动创建
```

## 二、启动（在你自己的终端里执行，需要联网）

```powershell
cd demo
powershell -ExecutionPolicy Bypass -File setup.ps1
```

脚本会自动：找 Python → 建 `.venv` → 装依赖（清华源）→ 启动 uvicorn。

如果提示没有 Python：

- 这台机器只装了 Python 管理器，先执行一次 `py install 3.12`（会自动下载真 Python）
- 或浏览器下载 https://www.python.org/downloads/ 官方安装包，勾选 Add to PATH

启动成功后浏览器打开：**http://127.0.0.1:8000**

> 用 PyCharm 也行：File → Open 打开 `demo` 文件夹 → 设置解释器为 `.venv\Scripts\python.exe`
> → 右键 `main.py` → Run（或终端跑 `uvicorn main:app --reload`）。

## 三、DEMO 关卡与答案（组织者专用）

| 关 | 章节 | 标题 | 类型 | 答案 |
|---|---|---|---|---|
| 1 | 第一章 · 启程 | 信号接收 | 文本（看网页源码注释） | `zua` |
| 2 | 第一章 · 启程 | 电码电报 | 文本（摩斯码） | `welcome` |
| 3 | 第一章 · 启程 | 0 与 1 的世界 | 文本（二进制→ASCII） | `computer` |
| 4 | 第一章 · 启程 | 编码不等于加密 | 文本（Base64） | `aviation` |
| 5 | 第二章 · 探秘 | 浏览器里的侦探 | 文本（F12 Console） | `radar` |
| 6 | 第二章 · 探秘 | 藏在图片里 | 文本（SVG 注释） | `centersquare` |
| 7 | 第二章 · 探秘 | 404 未找到 | 文本（404→robots→secret 链） | `robot` |
| 8 | 第二章 · 探秘 | 会自我描述的信号 | 文本（外观数列 / RLE） | `312211` |
| 9 | 第三章 · 基础算法训练 | 猜数大师 | 交互（1~2026 二分 ≤11 次） | 猜中即过 |
| 10 | 第三章 · 基础算法训练 | 排序实验室 | 文本（逆序对/排序） | `7` |
| 11 | 第三章 · 基础算法训练 | 汉诺塔的诅咒 | 文本（递归，2ⁿ−1） | `31` |
| 12 | 第三章 · 基础算法训练 | 斐波那契的尾巴 | 文本（递推+循环节） | `3` |
| 13 | 第三章 · 基础算法训练 | 航线规划·数字三角形 | 文本（动态规划） | `26` |
| 14 | 第三章 · 基础算法训练 | 迷宫救援·最短路径 | 文本（图/BFS） | `9` |
| 15 | 第四章 · 终局 | 黑匣子终章 | 文本（碎片拼接） | `zuawelcome26go` |

> 碎片按关卡顺序拼成 `zuawelcome26go`（14 片），即第 15 关答案（服务端动态计算）。
> 正式版将替换为 校史/社团暗号 + 转换逻辑（见 levels.py 注释）。

## 四、本地 / 局域网测试

- 本机：http://127.0.0.1:8000
- 手机连同一 Wi-Fi：`uvicorn` 已 `--host 0.0.0.0`，手机访问 `http://<电脑IP>:8000`
  （`ipconfig` 查 IPv4；Windows 防火墙需放行 8000 入站）

## 五、内网穿透测试（SakuraFrp，已安装）

1. 打开「SakuraFrp 启动器」（桌面快捷方式 / `C:\Program Files\SakuraFrpLauncher`）
2. 登录 → 创建隧道（或直接用已有隧道）：
   - 隧道类型：**HTTP**（建议开 HTTPS 访问）
   - 本地地址：`127.0.0.1`，本地端口：`8000`
   - 访问密码可不设（测试期）
3. 启动该隧道 → 得到公网地址（形如 `https://xxxx.sakurafrp.com`）
4. 把地址发测试同学，手机流量下也能访问

注意事项：
- 免费隧道域名随机、重启后变化，发链接前先自己打开确认
- 全程要用**同一个链接**（Cookie 跟随域名）
- 正式上线再迁到 2C2G 服务器（PM2 + Nginx + 域名证书）

## 六、curl 验证 API（可选）

```powershell
# 建立会话（保存 cookie）
curl.exe -c cookies.txt http://127.0.0.1:8000/api/me
# 关卡列表：第 1 关 unlocked
curl.exe -b cookies.txt http://127.0.0.1:8000/api/levels
# 未解锁关卡被拒：403 locked
curl.exe -b cookies.txt http://127.0.0.1:8000/api/levels/2
# 提交答案
curl.exe -b cookies.txt -H "Content-Type: application/json" -d "{\"answer\":\"zua\"}" http://127.0.0.1:8000/api/levels/1/check
# 答错触发 3 秒冷却（429）
```

## 七、API 一览

| 接口 | 作用 |
|---|---|
| `GET /` | 前端页面 |
| `GET /api/me` | 会话信息 |
| `GET /api/levels` | 关卡列表（含解锁/通关状态） |
| `GET /api/levels/{id}` | 关卡题面（未解锁 403） |
| `POST /api/levels/{id}/check` | 文本关答案校验 |
| `POST /api/levels/{id}/guess` | 交互关猜数 |
| `GET /api/levels/{id}/hints` | 三级提示 |
| `POST /api/rank/register` | 登记昵称 |
| `GET /api/rank` | 排行榜 |

## 八、已实现 / 待办

**已实现**：会话 cookie、SQLite 存储、顺序解锁门禁、答案服务端校验、
答错冷却 + 每分钟限次、交互式猜数关（目标由 token 派生）、三级提示、
碎片收集、排行榜（按通关时间）、昵称登记、移动端友好雷达主题 UI。

**待办（正式版）**：
- [ ] 真实终极题（碎片拼装 + 校史 / 社团暗号）
- [ ] 积分制（时间加成、少用提示加成）、徽章 / 称号
- [ ] 每日彩蛋题
- [ ] 限流换 Redis / DB（多 worker 时内存版失效）
- [ ] 答错日志（发现刷子）、防爆破细化
- [ ] 部署到 2C2G：PM2 + Nginx + HTTPS + 域名
