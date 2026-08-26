/* 信号灯 · 摩斯节奏播放器（外置以满足 CSP script-src 'self'） */
(function () {
  const T = 320; // 单位时长 ms
  const CODE = { A:".-", B:"-...", C:"-.-.", D:"-..", E:".", F:"..-.", G:"--.",
                 H:"....", I:"..", J:".---", K:"-.-", L:".-..", M:"--", N:"-.",
                 O:"---", P:".--.", Q:"--.-", R:".-.", S:"...", T:"-",
                 U:"..-", V:"...-", W:".--", X:"-..-", Y:"-.--", Z:"--.." };
  const WORD = "WELCOME";
  let token = 0;

  function schedule() {
    const my = ++token;
    const lamp = document.getElementById("lamp");
    const st   = document.getElementById("status");
    if (!lamp) return;
    const seq = [];
    WORD.split("").forEach((ch, li) => {
      CODE[ch].split("").forEach((s, si) => {
        seq.push({ on: true,  t: s === "." ? 1 : 3 });
        if (si < CODE[ch].length - 1) seq.push({ on: false, t: 1 });
      });
      if (li < WORD.length - 1) seq.push({ on: false, t: 3 });   // 字母间隔
    });
    seq.push({ on: false, t: 15 });                              // 循环间歇

    let i = 0;
    (function step() {
      if (my !== token) return;                                  // 已被重播取代
      const f = seq[i];
      lamp.classList.toggle("on", f.on);
      i = (i + 1) % seq.length;
      setTimeout(step, f.t * T);
    })();
  }

  document.addEventListener("DOMContentLoaded", function () {
    document.getElementById("replay").addEventListener("click", function () {
      const s = document.getElementById("status");
      s.textContent = "REPLAYING";
      setTimeout(function () { s.textContent = "RECEIVING · LOOP"; }, 600);
      schedule();
    });
    schedule();
  });
})();
