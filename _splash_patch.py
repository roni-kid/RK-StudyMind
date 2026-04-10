# ── CSS ───────────────────────────────────────────────────────────
css = """
.gradio-container{max-width:100%!important;width:100%!important;margin:0!important;padding:20px!important;}
footer{display:none!important;}
html,body{background:#060b18!important;}

@keyframes rk-dot-bounce{0%,80%,100%{transform:translateY(0);opacity:.4}40%{transform:translateY(-7px);opacity:1}}
.rk-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:#818cf8;margin:0 2px;animation:rk-dot-bounce 1.3s ease-in-out infinite;}
.rk-dot:nth-child(1){animation-delay:0s}.rk-dot:nth-child(2){animation-delay:.18s}.rk-dot:nth-child(3){animation-delay:.36s}
.rk-hidden-btn{position:absolute!important;width:1px!important;height:1px!important;overflow:hidden!important;clip:rect(0,0,0,0)!important;white-space:nowrap!important;pointer-events:none!important;opacity:0!important;}
.rk-feat-card:hover{border-color:#4F46E5!important;background:#1a2540!important;}

/* ════════════════════════════════════════════
   STARTUP SPLASH SCREEN
   ════════════════════════════════════════════ */
#rk-splash{
  position:fixed;inset:0;
  background:#060b18;
  z-index:999999;
  display:flex;flex-direction:column;align-items:center;justify-content:center;gap:22px;
  font-family:'Segoe UI',sans-serif;
}
#rk-splash.rk-splash-out{
  animation:rk-splash-dismiss .75s ease forwards;
}
@keyframes rk-splash-dismiss{
  0%{opacity:1;transform:scale(1)}
  60%{opacity:0;transform:scale(1.03)}
  100%{opacity:0;pointer-events:none}
}

/* macOS-style radial spinner — 12 ticks */
#rk-spinner{position:relative;width:72px;height:72px;}
#rk-spinner .rk-tick{
  position:absolute;top:50%;left:50%;
  width:7px;height:19px;
  margin-left:-3.5px;
  border-radius:4px;
  transform-origin:center 38px;
  animation:rk-tick-fade 1.2s linear infinite;
}
#rk-spinner .rk-tick:nth-child(1) {transform:rotate(0deg)   translateY(-38px);animation-delay:-1.10s}
#rk-spinner .rk-tick:nth-child(2) {transform:rotate(30deg)  translateY(-38px);animation-delay:-1.00s}
#rk-spinner .rk-tick:nth-child(3) {transform:rotate(60deg)  translateY(-38px);animation-delay:-0.90s}
#rk-spinner .rk-tick:nth-child(4) {transform:rotate(90deg)  translateY(-38px);animation-delay:-0.80s}
#rk-spinner .rk-tick:nth-child(5) {transform:rotate(120deg) translateY(-38px);animation-delay:-0.70s}
#rk-spinner .rk-tick:nth-child(6) {transform:rotate(150deg) translateY(-38px);animation-delay:-0.60s}
#rk-spinner .rk-tick:nth-child(7) {transform:rotate(180deg) translateY(-38px);animation-delay:-0.50s}
#rk-spinner .rk-tick:nth-child(8) {transform:rotate(210deg) translateY(-38px);animation-delay:-0.40s}
#rk-spinner .rk-tick:nth-child(9) {transform:rotate(240deg) translateY(-38px);animation-delay:-0.30s}
#rk-spinner .rk-tick:nth-child(10){transform:rotate(270deg) translateY(-38px);animation-delay:-0.20s}
#rk-spinner .rk-tick:nth-child(11){transform:rotate(300deg) translateY(-38px);animation-delay:-0.10s}
#rk-spinner .rk-tick:nth-child(12){transform:rotate(330deg) translateY(-38px);animation-delay: 0.00s}

@keyframes rk-tick-fade{
  0%  {background:#a5b4fc;box-shadow:0 0 8px #4F46E5;opacity:1  }
  40% {background:#1e1b4b;box-shadow:none;           opacity:0.15}
  100%{background:#a5b4fc;box-shadow:0 0 8px #4F46E5;opacity:1  }
}

/* "Loading......." text */
#rk-splash-text{
  font-size:15px;font-weight:600;
  color:#64748b;letter-spacing:1.5px;
  min-width:140px;text-align:center;
}

/* Segmented progress bar */
#rk-splash-bar-wrap{display:flex;gap:5px;align-items:center;}
.rk-seg{
  width:24px;height:11px;border-radius:3px;
  background:#0f172a;border:1px solid #1e293b;
  transition:background .12s ease, box-shadow .12s ease;
}
.rk-seg.on{
  background:#4F46E5;border-color:#6366f1;
  box-shadow:0 0 10px #4F46E5cc;
}
"""

# ── Splash JS injected via gr.Blocks(js=...) ─────────────────────
# Runs once after Gradio mounts all components.
SPLASH_JS = """
() => {
  /* ── Inject the splash HTML at top of <body> ── */
  var splash = document.createElement('div');
  splash.id = 'rk-splash';
  splash.innerHTML =
    '<div id="rk-spinner"></div>' +
    '<div id="rk-splash-text">Loading.</div>' +
    '<div id="rk-splash-bar-wrap">' +
    '<div class="rk-seg"></div><div class="rk-seg"></div>' +
    '<div class="rk-seg"></div><div class="rk-seg"></div>' +
    '<div class="rk-seg"></div><div class="rk-seg"></div>' +
    '<div class="rk-seg"></div><div class="rk-seg"></div>' +
    '<div class="rk-seg"></div><div class="rk-seg"></div>' +
    '</div>';
  document.body.insertBefore(splash, document.body.firstChild);

  /* ── Build the 12 spinner ticks ── */
  var spinner = document.getElementById('rk-spinner');
  for (var i = 0; i < 12; i++) {
    var tick = document.createElement('div');
    tick.className = 'rk-tick';
    spinner.appendChild(tick);
  }

  /* ── Animate segmented bar (sweep left-to-right, loop) ── */
  var segs = splash.querySelectorAll('.rk-seg');
  var segIdx = 0;
  var barTimer = setInterval(function() {
    segs.forEach(function(s) { s.classList.remove('on'); });
    for (var k = 0; k <= segIdx; k++) segs[k].classList.add('on');
    segIdx++;
    if (segIdx >= segs.length) segIdx = 0;
  }, 150);

  /* ── Animate "Loading......." text ── */
  var textEl = document.getElementById('rk-splash-text');
  var dots = 1;
  var dotTimer = setInterval(function() {
    dots = (dots % 7) + 1;
    if (textEl) textEl.textContent = 'Loading' + '.'.repeat(dots);
  }, 200);

  /* ── Dismiss: fill all segments then fade out ── */
  setTimeout(function() {
    segs.forEach(function(s) { s.classList.add('on'); });
    setTimeout(function() {
      clearInterval(barTimer);
      clearInterval(dotTimer);
      splash.classList.add('rk-splash-out');
      setTimeout(function() {
        if (splash.parentNode) splash.parentNode.removeChild(splash);
      }, 800);
    }, 300);
  }, 2300);
}
"""
