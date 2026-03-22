(function () {
  var STYLE_ID = 'vf-theme-enforcer-style';

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) return;
    var style = document.createElement('style');
    style.id = STYLE_ID;
    style.textContent = "\n      body.auth-page,\n      body.feed-page,\n      body.login-page,\n      body.register-page {\n        position: relative !important;\n        min-height: 100vh !important;\n      }\n\n      body.auth-page:not(.retro-2011)::before,\n      body.feed-page:not(.retro-2011)::before {\n        content: '' !important;\n        position: fixed !important;\n        inset: 0 !important;\n        background: url('/static/VFlogo_clean.png') center center / min(84vw, 1120px) no-repeat !important;\n        opacity: .64 !important;\n        filter: drop-shadow(0 0 210px rgba(255,106,0,.99)) !important;\n        pointer-events: none !important;\n        z-index: 0 !important;\n      }\n\n      body.auth-page:not(.retro-2011)::after,\n      body.feed-page:not(.retro-2011)::after {\n        content: '' !important;\n        position: fixed !important;\n        inset: 0 !important;\n        background:\n          radial-gradient(circle at 50% 50%, rgba(255,150,55,.66), rgba(255,120,25,.18) 44%, transparent 66%),\n          radial-gradient(circle at 50% 50%, rgba(255,110,20,.58), transparent 60%) !important;\n        pointer-events: none !important;\n        z-index: 0 !important;\n      }\n\n      body.auth-page main,\n      body.feed-page main,\n      body.login-page main,\n      body.register-page main,\n      body.auth-page .auth-wrap,\n      body.feed-page .feed-app,\n      body.login-page .auth-wrap,\n      body.register-page .auth-wrap {\n        position: relative !important;\n        z-index: 1 !important;\n      }\n\n      body.feed-page .panel,\n      body.feed-page .feed-topbar,\n      body.feed-page .mini-card,\n      body.feed-page .live-post,\n      body.feed-page .ai-log,\n      body.feed-page .story-card,\n      body.feed-page .chip,\n      body.feed-page .action-btn,\n      body.feed-page .menu-item,\n      body.feed-page .trend-chip,\n      body.feed-page .icon-btn,\n      body.feed-page .lab-btn,\n      body.feed-page button,\n      body.auth-page .login-card,\n      body.login-page .login-card,\n      body.register-page .login-card {\n        box-shadow: 0 0 0 1px rgba(255,173,117,.30), 0 0 22px rgba(255,106,0,.40) !important;\n      }\n\n      body.feed-page .panel,\n      body.feed-page .mini-card,\n      body.feed-page .live-post,\n      body.feed-page .ai-log,\n      body.auth-page .login-card,\n      body.login-page .login-card,\n      body.register-page .login-card {\n        background: linear-gradient(180deg, rgba(255,145,54,.06), rgba(34,17,8,.05)) !important;\n        backdrop-filter: blur(30px) saturate(1.2) !important;\n      }\n\n      body.login-page .background,\n      body.register-page .background {\n        background: url('/static/VFlogo_clean.png') center center / contain no-repeat !important;\n        opacity: .50 !important;\n        filter: drop-shadow(0 0 110px rgba(255,98,0,.95)) !important;\n      }\n\n      body.login-page .login-btn,\n      body.register-page .login-btn {\n        box-shadow: 0 0 0 1px rgba(255,173,117,.34), 0 0 24px rgba(255,106,0,.56) !important;\n      }\n\n      /* ══════ GLOBAL 2011 MODE: basic white theme ══════ */\n      body.retro-2011 {\n        background: #f0f0f0 !important;\n        color: #333 !important;\n      }\n      body.retro-2011 .vf-bg {\n        display: none !important;\n      }\n      body.retro-2011::before,\n      body.retro-2011::after {\n        opacity: 0 !important;\n        display: none !important;\n      }\n      body.retro-2011 .sparkle-field,\n      body.retro-2011 .sparkle-dot,\n      body.retro-2011 .vf-spark {\n        display: none !important;\n      }\n      body.retro-2011 .app-shell {\n        background: #f0f0f0 !important;\n      }\n      body.retro-2011 main {\n        background: transparent !important;\n      }\n      body.retro-2011 .auth-wrap,\n      body.retro-2011 .login-card,\n      body.retro-2011 .panel,\n      body.retro-2011 .card {\n        background: #fff !important;\n        border: 1px solid #ddd !important;\n        box-shadow: 0 1px 3px rgba(0,0,0,.08) !important;\n        backdrop-filter: none !important;\n        color: #333 !important;\n      }\n      body.retro-2011 h1,\n      body.retro-2011 h2,\n      body.retro-2011 h3,\n      body.retro-2011 h4,\n      body.retro-2011 h5,\n      body.retro-2011 h6,\n      body.retro-2011 label,\n      body.retro-2011 p,\n      body.retro-2011 span,\n      body.retro-2011 a,\n      body.retro-2011 div {\n        color: #333 !important;\n        -webkit-text-fill-color: #333 !important;\n      }\n      body.retro-2011 a:hover {\n        color: #555 !important;\n        -webkit-text-fill-color: #555 !important;\n      }\n      body.retro-2011 input,\n      body.retro-2011 textarea,\n      body.retro-2011 select {\n        background: #f9f9f9 !important;\n        border: 1px solid #ccc !important;\n        color: #333 !important;\n        -webkit-text-fill-color: #333 !important;\n      }\n      body.retro-2011 button {\n        background: #f5f5f5 !important;\n        border: 1px solid #ccc !important;\n        color: #333 !important;\n        -webkit-text-fill-color: #333 !important;\n        box-shadow: none !important;\n      }\n      body.retro-2011 button:hover {\n        background: #eee !important;\n      }\n      body.retro-2011 .vf-lang-footer nav {\n        background: rgba(255,255,255,.95) !important;\n        border-color: #ddd !important;\n      }\n      body.retro-2011 .vf-lang-footer .lang-link {\n        color: #555 !important;\n        -webkit-text-fill-color: #555 !important;\n      }\n    ";
    document.head.appendChild(style);
  }

  function applyRetroPreference() {
    var enabled = false;
    try {
      enabled = window.localStorage.getItem('vybe_feed_retro_2011') === '1';
    } catch (e) {
      enabled = false;
    }
    document.body.classList.toggle('retro-2011', enabled);
    document.body.setAttribute('data-retro', enabled ? '1' : '0');
  }

  function run() {
    if (!document.body) return;
    document.body.classList.add('vf-theme-enforced');
    injectStyle();
    applyRetroPreference();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }

  var observer = new MutationObserver(function () {
    run();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });
})();
