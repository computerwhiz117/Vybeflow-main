(() => {
  const reelsEl = document.getElementById("reels");
  if (!reelsEl) return;

  const qs  = (s, el=document) => el.querySelector(s);
  const qsa = (s, el=document) => Array.from(el.querySelectorAll(s));

  // GLOBAL SOUND SETTING (stays when scrolling)
  let globalSoundOn = false; // start muted (autoplay rules)
  let activeVideo = null;
  let hintTimer = null;

  function ensureSrc(video){
    if (!video) return;
    if (video.src && video.src.length > 0) return;
    const ds = video.getAttribute("data-src");
    if (ds) video.src = ds;
  }

  function preloadNear(activeSection, n=2){
    const sections = qsa(".reel", reelsEl);
    const idx = sections.indexOf(activeSection);
    if (idx < 0) return;

    for (let i=idx; i<=Math.min(sections.length-1, idx+n); i++){
      const v = qs("video.vf-reel", sections[i]);
      ensureSrc(v);
      try { v.preload = "metadata"; } catch(e){}
    }
  }

  function showHint(section){
    const hint = qs('[data-role="hint"]', section);
    if (!hint) return;
    hint.classList.add("show");
    clearTimeout(hintTimer);
    hintTimer = setTimeout(() => hint.classList.remove("show"), 1600);
  }

  function toast(section, text){
    const t = qs('[data-role="toast"]', section);
    if (!t) return;
    t.textContent = text;
    t.classList.add("show");
    setTimeout(() => t.classList.remove("show"), 650);
  }

  function setSoundPill(section){
    const pill = qs('[data-action="sound"]', section);
    if (!pill) return;
    pill.textContent = globalSoundOn ? "Sound" : "Muted";
  }

  function setProgress(section, pct){
    const bar = qs('[data-role="progressBar"]', section);
    if (bar) bar.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  }

  function getSections(){ return qsa(".reel", reelsEl); }
  function getVideos(){ return qsa("video.vf-reel", reelsEl); }

  function applySound(video){
    if (!video) return;
    video.muted = !globalSoundOn;
  }

  // Intersection: play/pause and lazy-load
  const io = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      const v = entry.target;
      const section = v.closest(".reel");
      if (!section) return;

      if (entry.isIntersecting){
        activeVideo = v;

        ensureSrc(v);
        preloadNear(section, 2);

        applySound(v);
        setSoundPill(section);

        const p = v.play();
        if (p && typeof p.catch === "function") p.catch(() => {});
        showHint(section);
      } else {
        v.pause();
        setProgress(section, 0);
      }
    });
  }, { threshold: 0.65 });

  // Observe all videos
  getVideos().forEach(v => io.observe(v));

  // Progress bars
  function onTimeUpdate(e){
    const v = e.target;
    const section = v.closest(".reel");
    if (!section) return;
    const dur = v.duration || 0;
    const cur = v.currentTime || 0;
    const pct = dur > 0 ? (cur/dur)*100 : 0;
    setProgress(section, pct);
  }
  getVideos().forEach(v => v.addEventListener("timeupdate", onTimeUpdate));

  function togglePlay(v){
    if (!v) return;
    const section = v.closest(".reel");
    if (!section) return;

    if (v.paused){
      ensureSrc(v);
      applySound(v);
      const p = v.play();
      if (p && typeof p.catch === "function") p.catch(() => {});
      toast(section, "Play");
    } else {
      v.pause();
      toast(section, "Paused");
    }
  }

  function toggleLike(section){
    const likeBtn = qs('[data-action="like"]', section);
    const likesEl = qs('[data-role="likes"]', section);
    if (!likeBtn || !likesEl) return;

    const liked = likeBtn.classList.toggle("liked");
    const cur = parseInt(likesEl.textContent || "0", 10) || 0;
    likesEl.textContent = liked ? (cur + 1) : Math.max(0, cur - 1);

    if (liked){
      const heart = qs('[data-role="heart"]', section);
      if (heart){
        heart.classList.add("show");
        setTimeout(() => heart.classList.remove("show"), 520);
      }
    }
  }

  // Long press: temporary sound while holding
  let pressTimer = null;
  let pressActive = false;
  let lastTap = 0;

  reelsEl.addEventListener("pointerdown", (e) => {
    const v = e.target.closest("video.vf-reel");
    if (!v) return;

    pressActive = false;
    pressTimer = setTimeout(() => {
      pressActive = true;
      v.muted = false; // temporary unmute without changing global
      const section = v.closest(".reel");
      toast(section, "Sound");
    }, 380);
  });

  reelsEl.addEventListener("pointerup", (e) => {
    clearTimeout(pressTimer);
    const v = e.target.closest("video.vf-reel");
    if (!v) return;

    const section = v.closest(".reel");
    if (!section) return;

    if (pressActive){
      applySound(v); // restore based on global sound
      pressActive = false;
      return;
    }

    const now = Date.now();
    const delta = now - lastTap;
    lastTap = now;

    if (delta < 260){
      toggleLike(section);
      return;
    }

    togglePlay(v);
  });

  // Rail + top sound + share + follow + comments
  reelsEl.addEventListener("click", async (e) => {
    const btn = e.target.closest("[data-action]");
    if (!btn) return;

    const section = btn.closest(".reel");
    const action = btn.getAttribute("data-action");
    if (!section) return;

    if (action === "like"){
      toggleLike(section);
      return;
    }

    if (action === "follow"){
      btn.textContent = (btn.textContent === "Follow") ? "Following" : "Follow";
      toast(section, btn.textContent);
      return;
    }

    if (action === "sound"){
      globalSoundOn = !globalSoundOn;
      const v = section.querySelector("video.vf-reel");
      if (v) applySound(v);

      getSections().forEach(s => setSoundPill(s));
      toast(section, globalSoundOn ? "Sound On" : "Muted");
      return;
    }

    if (action === "share"){
      // Open custom share modal
      openShareModal(section);
      return;
    }
  // --- Custom Share Modal Logic ---
  const shareModal = document.getElementById("shareModal");
  const shareOkBtn = document.getElementById("shareOkBtn");
  const shareCancelBtn = document.getElementById("shareCancelBtn");
  const shareXBtn = document.getElementById("shareXBtn");
  const copyLinkBtn = document.getElementById("copyLinkBtn");
  let currentShareSection = null;

  function openShareModal(section){
    currentShareSection = section;
    shareModal.classList.remove("hidden");
    shareModal.classList.add("show");
    shareModal.setAttribute("aria-hidden", "false");
  }

  function closeShareModal(){
    shareModal.classList.add("hidden");
    shareModal.classList.remove("show");
    shareModal.setAttribute("aria-hidden", "true");
    currentShareSection = null;
  }

  shareOkBtn && shareOkBtn.addEventListener("click", function(){
    // Simulate posting story (could POST to backend here)
    if(currentShareSection) toast(currentShareSection, "Story shared!");
    closeShareModal();
  });

  shareCancelBtn && shareCancelBtn.addEventListener("click", closeShareModal);

  shareXBtn && shareXBtn.addEventListener("click", function(){
    // Simulate sharing to X (Twitter)
    if(!currentShareSection) return;
    const url = currentShareSection.getAttribute("data-share-url") || window.location.href;
    const text = encodeURIComponent("Check out my VybeFlow story!");
    const shareUrl = `https://twitter.com/intent/tweet?text=${text}&url=${encodeURIComponent(url)}`;
    window.open(shareUrl, "_blank");
    closeShareModal();
  });

  copyLinkBtn && copyLinkBtn.addEventListener("click", function(){
    if(!currentShareSection) return;
    const url = currentShareSection.getAttribute("data-share-url") || window.location.href;
    navigator.clipboard.writeText(url).then(()=>{
      toast(currentShareSection, "Link copied");
    });
    closeShareModal();
  });

  // Close modal on outside click
  shareModal && shareModal.addEventListener("click", function(e){
    if(e.target === shareModal) closeShareModal();
  });

    if (action === "comment"){
      openComments(section);
      return;
    }
  });

  // COMMENTS (front-end modal; hook to backend later)
  const modal = document.getElementById("commentModal");
  const closeBtn = document.getElementById("closeComments");
  const listEl = document.getElementById("commentList");
  const inputEl = document.getElementById("commentInput");
  const sendBtn = document.getElementById("sendComment");
  const emojiDock = document.getElementById("commentEmojiDock");

  let currentCommentSection = null;

  function escapeHtml(s){
    return String(s).replace(/[&<>"']/g, (m) => ({
      "&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#039;"
    }[m]));
  }

  function addComment(u, t){
    const div = document.createElement("div");
    div.className = "comment";
    div.innerHTML = `<div class="u">@${escapeHtml(u)}</div><div class="t">${escapeHtml(t)}</div>`;
    listEl.appendChild(div);
    listEl.scrollTop = listEl.scrollHeight;
  }

  function openComments(section){
    currentCommentSection = section;
    listEl.innerHTML = "";

    const seed = [
      {u:"VybeFlow", t:"🔥🔥🔥"},
      {u:"user2", t:"This smooth as hell"},
      {u:"user3", t:"Post more of these"}
    ];
    seed.forEach(c => addComment(c.u, c.t));

    modal.classList.add("show");
    modal.setAttribute("aria-hidden", "false");
    setTimeout(() => inputEl.focus(), 50);
  }

  function closeComments(){
    modal.classList.remove("show");
    modal.setAttribute("aria-hidden", "true");
    currentCommentSection = null;
  }

  function sendComment(){
    const txt = (inputEl.value || "").trim();
    if (!txt) return;
    addComment("me", txt);
    inputEl.value = "";

    if (currentCommentSection){
      const cEl = currentCommentSection.querySelector('[data-role="comments"]');
      if (cEl){
        const cur = parseInt(cEl.textContent || "0", 10) || 0;
        cEl.textContent = cur + 1;
      }
    }

    // TODO: POST to backend /api/reels/<id>/comments
  }

  closeBtn.addEventListener("click", closeComments);
  modal.addEventListener("click", (e) => { if (e.target === modal) closeComments(); });
  sendBtn.addEventListener("click", sendComment);

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendComment();
    if (e.key === "Escape") closeComments();
  });

  if (emojiDock && inputEl){
    emojiDock.querySelectorAll(".emoji3d").forEach(node => {
      node.addEventListener("click", () => {
        const emoji = node.getAttribute("data-emoji") || node.textContent || "";
        const start = inputEl.selectionStart ?? inputEl.value.length;
        const end = inputEl.selectionEnd ?? inputEl.value.length;
        const before = inputEl.value.slice(0, start);
        const after = inputEl.value.slice(end);
        inputEl.value = before + emoji + after;
        const pos = start + emoji.length;
        if (typeof inputEl.setSelectionRange === "function"){
          inputEl.setSelectionRange(pos, pos);
        }
        inputEl.focus();
      });
    });
  }

  // Initial: ensure first visible loads quickly
  const firstSection = qs(".reel", reelsEl);
  if (firstSection){
    const v = qs("video.vf-reel", firstSection);
    ensureSrc(v);
    preloadNear(firstSection, 2);
    setSoundPill(firstSection);
  }

  // When user leaves tab: pause
  document.addEventListener("visibilitychange", () => {
    if (document.hidden){
      getVideos().forEach(v => v.pause());
    } else {
      const v = activeVideo;
      if (v){
        const p = v.play();
        if (p && typeof p.catch === "function") p.catch(() => {});
      }
    }
  });
})();
