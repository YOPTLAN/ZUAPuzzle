/* ZUA-2026 黑匣子破译行动 · 前端逻辑
   安全说明：本文件不含任何答案；答案校验全部在服务端完成。
   UI 规范：图标一律用内联 SVG（不用 emoji）——ui-ux-pro-max 交付清单要求。 */
const $ = (id) => document.getElementById(id);
let LEVELS = [];
let current = null;      // 当前关卡 payload
let fragments = [];

/* ---- 内联 SVG 图标（lucide 风格，stroke 继承 currentColor）---- */
const svg = (paths, cls = "icon-inline") =>
  `<svg class="${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths}</svg>`;
const ICONS = {
  check:  svg('<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>'),
  play:   svg('<polygon points="6 3 20 12 6 21 6 3"/>'),
  lock:   svg('<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>'),
  x:      svg('<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>'),
  alert:  svg('<path d="m21.73 18-8-14a2 2 0 0 0-3.46 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><path d="M12 9v4M12 17h.01"/>'),
  trophy: svg('<path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6M18 9h1.5a2.5 2.5 0 0 0 0-5H18M4 22h16M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22M18 2H6v7a6 6 0 0 0 12 0V2Z"/>'),
  bulb:   svg('<path d="M9 18h6M10 22h4M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5A4.61 4.61 0 0 1 8.91 14"/>'),
};

const views = { map: $("view-map"), level: $("view-level"), rank: $("view-rank") };
const navBtns = document.querySelectorAll("nav button");

function showView(name) {
  Object.entries(views).forEach(([k, el]) => el.classList.toggle("hidden", k !== name));
  navBtns.forEach(b => b.classList.toggle("active", b.dataset.view === name));
  if (name === "map") loadMap();
  if (name === "rank") loadRank();
}

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw Object.assign(new Error(data.detail || "请求失败"), { status: res.status, data });
  return data;
}

/* ---------- 航线图（按章节分组） ---------- */
async function loadMap() {
  const me = await api("/api/me");
  LEVELS = await api("/api/levels");
  fragments = LEVELS.filter(l => l.solved && l.fragment).map(l => l.fragment);
  $("fragList").textContent = fragments.length ? fragments.join(" ") : "—";
  const box = $("levelList");
  box.innerHTML = "";
  let lastStage = "";
  LEVELS.forEach(lv => {
    if (lv.stage !== lastStage) {
      lastStage = lv.stage;
      const h = document.createElement("div");
      h.className = "stage-head";
      h.textContent = `${lastStage}`;
      box.appendChild(h);
    }
    const el = document.createElement("div");
    el.className = "lv " + (lv.solved ? "solved" : lv.unlocked ? "" : "locked");
    const icon = lv.solved ? ICONS.check : lv.unlocked ? ICONS.play : ICONS.lock;
    el.innerHTML = `
      <div>
        <span class="st-icon-wrap">${icon.replace('class="icon-inline"', 'class="st-icon"')}</span>
        <b>第 ${lv.id} 关 · ${lv.title}</b>
        <span class="meta">　难度 ${lv.difficulty}</span>
      </div>
      ${lv.solved && lv.fragment ? `<div class="frag">碎片 ${lv.fragment}</div>` : ""}`;
    if (lv.unlocked) el.addEventListener("click", () => openLevel(lv.id));
    box.appendChild(el);
  });
}

/* ---------- 关卡 ---------- */
async function openLevel(id) {
  try {
    current = await api(`/api/levels/${id}`);
  } catch (e) {
    alert("这关还没解锁：" + e.message);
    return;
  }
  $("lvStory").textContent = current.story;
  $("lvTitle").textContent = `第 ${current.id} 关 · ${current.title}`;
  $("lvPrompt").textContent = current.prompt;
  // 排序柱状图（第 10 关）
  const barsBox = $("barsVisual");
  if (current.bars) {
    barsBox.classList.remove("hidden");
    barsBox.innerHTML = current.bars.map(v =>
      `<div class="bar-col"><div class="bar" style="height:${v * 26}px"></div><div class="bar-val">${v}</div></div>`
    ).join("");
  } else {
    barsBox.classList.add("hidden");
    barsBox.innerHTML = "";
  }
  // Console 线索（第 5 关）
  if (current.console) console.log("[ZUA-2026] " + current.console);
  $("textArea").classList.toggle("hidden", current.type !== "text");
  $("guessArea").classList.toggle("hidden", current.type !== "guess");
  $("checkMsg").textContent = "";
  $("hintMsg").textContent = "";
  if (current.type === "guess") initGuess();
  showView("level");
}

/* 文本关 */
$("submitBtn").addEventListener("click", async () => {
  const ans = $("answerInput").value.trim();
  if (!ans || !current) return;
  try {
    const r = await api(`/api/levels/${current.id}/check`, {
      method: "POST", body: JSON.stringify({ answer: ans }),
    });
    if (r.correct) {
      $("checkMsg").innerHTML =
        `<span class="ok">${ICONS.check}正确！获得碎片【${r.fragment}】` +
        (r.done ? " —— 黑匣子已完整破解！" : "") + `</span>`;
      fragments.push(r.fragment);
      await loadMap();
      if (r.done) { showFinish(); return; }
      setTimeout(() => { openLevel(current.id + 1); $("answerInput").value = ""; }, 900);
    } else {
      $("checkMsg").innerHTML = `<span class="err">${ICONS.x}${r.message || "答案不对"}</span>`;
    }
  } catch (e) {
    $("checkMsg").innerHTML = `<span class="err">${ICONS.alert}${e.message}</span>`;
  }
});

/* 猜数交互关 */
let guessHistory = [];
function initGuess() {
  guessHistory = [];
  const g = current.guess;
  $("guessInfo").textContent = `范围 1 ~ ${g.hi}，最多猜 ${g.max_guesses} 次（二分法每次排除一半）`;
  renderGuessHistory();
  $("guessInput").value = "";
}
function renderGuessHistory() {
  $("guessHistory").innerHTML = guessHistory.length
    ? guessHistory.map(h => `<span class="log-line ${h.cls}">${h.text}</span>`).join("")
    : "<span class='dim'>—</span>";
}
$("guessBtn").addEventListener("click", async () => {
  const v = parseInt($("guessInput").value, 10);
  if (!Number.isFinite(v) || !current) return;
  try {
    const r = await api(`/api/levels/${current.id}/guess`, {
      method: "POST", body: JSON.stringify({ guess: v }),
    });
    if (r.result === "correct") {
      guessHistory.push({ text: `${v} ✓`, cls: "log-hit" });
      renderGuessHistory();
      $("guessInfo").textContent = `猜中了！用了 ${r.used} 次。获得碎片【${r.fragment}】`;
      fragments.push(r.fragment);
      await loadMap();
      if (r.done) { showFinish(); return; }
      setTimeout(() => openLevel(current.id + 1), 1200);
    } else if (r.result === "fail") {
      $("guessInfo").textContent = r.message;
    } else {
      const up = r.result === "higher";
      guessHistory.push({ text: `${v} ${up ? "↑" : "↓"}`, cls: up ? "log-hi" : "log-low" });
      renderGuessHistory();
      $("guessInfo").textContent = `已用 ${r.used} / ${r.max} 次（${up ? "小了，往大了猜" : "大了，往小了猜"}）`;
    }
  } catch (e) {
    $("guessInfo").textContent = e.message;
  }
});

/* 提示 */
$("hintBtn").addEventListener("click", async () => {
  if (!current) return;
  try {
    const r = await api(`/api/levels/${current.id}/hints`);
    $("hintMsg").innerHTML = r.hint
      ? `<span class="warn">${ICONS.bulb}提示 ${r.hint_index + 1}：${r.hint}</span>`
      : `<span class="warn">${ICONS.alert}没有更多提示了</span>`;
  } catch (e) {
    $("hintMsg").textContent = e.message;
  }
});

/* ---------- 排行榜与收尾 ---------- */
async function loadRank() {
  const r = await api("/api/rank");
  const box = $("rankBox");
  if (!r.rank.length) {
    box.innerHTML = `<p class="dim">// 尚无通关记录，等第一位黑匣子破译师出现…</p>`;
    return;
  }
  box.innerHTML = `<table class="rank">
    <thead><tr><th>#</th><th>CALLSIGN / 昵称</th><th>通关时间</th></tr></thead>
    <tbody>` +
    r.rank.map(x =>
      `<tr class="${x.me ? "me" : ""}"><td class="${x.rank === 1 ? "rk-1" : ""}">${String(x.rank).padStart(2, "0")}</td><td>${x.nickname}</td><td>${fmt(x.finished_at)}</td></tr>`
    ).join("") +
    `</tbody></table>`;
}
function fmt(ts) {
  const d = new Date(ts * 1000);
  const p = n => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}月${d.getDate()}日 ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

function showFinish() {
  $("checkMsg").innerHTML =
    `<span class="ok">${ICONS.trophy}黑匣子完全破解！登记呼号，登上排行榜：</span>
    <input type="text" id="nickInput" placeholder="昵称 / 呼号（最多24字）" style="margin-top:10px">
    <button id="nickBtn" class="btn btn-primary" style="margin-top:10px">登记上榜单</button>`;
  $("nickBtn").addEventListener("click", async () => {
    const nick = $("nickInput").value.trim();
    if (!nick) return;
    await api("/api/rank/register", { method: "POST", body: JSON.stringify({ nickname: nick }) });
    showView("rank");
  });
}

/* 事件绑定与启动 */
$("backBtn").addEventListener("click", () => showView("map"));
navBtns.forEach(b => b.addEventListener("click", () => showView(b.dataset.view)));
loadMap();
