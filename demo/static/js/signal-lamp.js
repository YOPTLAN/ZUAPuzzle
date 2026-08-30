/* 信号灯 · 摩斯节奏播放器（灯 + Web Audio 哔声同源同步；外置以满足 CSP script-src 'self'）
   点划串由父页面在加载后注入（服务端按答案生成，本文件不含明文答案）；
   必须在用户点击里创建 AudioContext（浏览器自动播放策略） */
(function () {
  const T = 320; // 单位时长 ms
  let SIGNAL = "";        // 空格分隔字母的点划串，如 ".-- . .-.."
  let token = 0;
  let audioCtx = null;
  let soundOn = false;

  /* 供父页面注入信号序列（app.js 在 iframe onload 后调用） */
  window.setSignal = function (s) {
    SIGNAL = typeof s === "string" ? s.trim() : "";
    schedule();
  };

  /* 摩斯哔声：700Hz 正弦波，起音/收尾 6ms 渐变防爆音，时长与灯亮一致 */
  function beep(ms) {
    if (!soundOn || !audioCtx) return;
    const t0 = audioCtx.currentTime + 0.02;
    const dur = ms / 1000;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.value = 700;
    gain.gain.setValueAtTime(0, t0);
    gain.gain.linearRampToValueAtTime(0.35, t0 + 0.006);
    gain.gain.setValueAtTime(0.35, t0 + Math.max(0.006, dur - 0.006));
    gain.gain.linearRampToValueAtTime(0, t0 + dur);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t0);
    osc.stop(t0 + dur + 0.03);
  }

  function schedule() {
    const my = ++token;
    const lamp = document.getElementById("lamp");
    const st   = document.getElementById("status");
    if (!lamp) return;
    if (!SIGNAL) { st.textContent = "WAITING SIGNAL"; return; }

    const letters = SIGNAL.split(" ");
    const seq = [];
    letters.forEach((sym, li) => {
      sym.split("").forEach((s, si) => {
        seq.push({ on: true,  t: s === "." ? 1 : 3 });
        if (si < sym.length - 1) seq.push({ on: false, t: 1 });
      });
      if (li < letters.length - 1) seq.push({ on: false, t: 3 });   // 字母间隔
    });
    seq.push({ on: false, t: 15 });                                 // 循环间歇

    let i = 0;
    (function step() {
      if (my !== token) return;                                     // 已被重播取代
      const f = seq[i];
      lamp.classList.toggle("on", f.on);
      if (f.on) beep(f.t * T);                                      // 灯亮即响，灯灭即停
      i = (i + 1) % seq.length;
      setTimeout(step, f.t * T);
    })();
  }

  function flashStatus(t) {
    const s = document.getElementById("status");
    s.textContent = t;
    setTimeout(function () { s.textContent = "RECEIVING · LOOP"; }, 600);
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("replay").addEventListener("click", function () {
      flashStatus("REPLAYING");
      schedule();
    });
    document.getElementById("sound").addEventListener("click", function () {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) { flashStatus("AUDIO NOT SUPPORTED"); return; }
      if (!audioCtx) audioCtx = new AC();
      if (audioCtx.state === "suspended") audioCtx.resume();
      soundOn = !soundOn;
      this.textContent = soundOn ? "♪ 声音开" : "♪ 播放声音";
      flashStatus(soundOn ? "SOUND ON" : "SOUND OFF");
    });
    schedule();
  });
})();
