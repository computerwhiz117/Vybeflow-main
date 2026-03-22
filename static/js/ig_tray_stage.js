// IG Tray/Stage JavaScript for create_post.html
(function(){
  const tray = document.getElementById('ig-tray');
  const stage = document.getElementById('ig-stage');
  const grid = document.getElementById('ig-grid');
  const search = document.getElementById('ig-tray-search');
  const pills = document.getElementById('ig-pack-pills');
  const tabs = document.querySelectorAll('.ig-tab');
  let currentTab = 'stickers';
  let stickerList = [
    {type:'sticker', label:'🔥', group:'Fun'},
    {type:'sticker', label:'😂', group:'Fun'},
    {type:'sticker', label:'💯', group:'Fun'},
    {type:'sticker', label:'🎉', group:'Party'},
    {type:'sticker', label:'😎', group:'Cool'},
    {type:'sticker', label:'✨', group:'Party'},
    {type:'sticker', label:'❤️', group:'Love'},
    {type:'sticker', label:'👑', group:'Royalty'},
    {type:'sticker', label:'🚀', group:'Fun'},
    {type:'sticker', label:'🥳', group:'Party'},
    {type:'sticker', label:'🌈', group:'Fun'},
    {type:'sticker', label:'🦄', group:'Fun'},
    {type:'sticker', label:'😇', group:'Cool'},
    {type:'sticker', label:'😱', group:'Fun'},
    {type:'sticker', label:'😈', group:'Party'},
    {type:'sticker', label:'👻', group:'Party'},
    {type:'sticker', label:'💩', group:'Fun'},
    {type:'sticker', label:'🎸', group:'Party'},
    {type:'sticker', label:'🎵', group:'Party'},
    {type:'sticker', label:'🍕', group:'Food'},
    {type:'sticker', label:'🍔', group:'Food'},
    {type:'sticker', label:'🍦', group:'Food'},
    {type:'sticker', label:'🍉', group:'Food'},
    {type:'sticker', label:'🍩', group:'Food'},
    {type:'sticker', label:'🍿', group:'Food'},
    {type:'sticker', label:'🥤', group:'Food'},
    {type:'sticker', label:'☕', group:'Food'},
    {type:'sticker', label:'🍺', group:'Food'}
  ];
  let emojiList = [
    '😀','😂','😍','🥰','😎','😭','😡','🥳','🤩','😇','😱','🤔','😴','😜','😏','😬','🥺','🤗','🤑','🤯','😤','😈','👻','💩','🔥','✨','🌈','🎉','❤️','👍','🙏','👏','💯','🚀','🦄','👑','🥇','🎵','⚡','🌙','🕶️','💎','🍕','🍔','🍦','🍉','🍩','🍿','🥤','☕','🍺','⚽','🏀','🏆','🎸','🎮','🎲','🚗','✈️','🚴','🏝️','🏠','🛒','🎁','📱','💡','📚','✏️','📸','🎬','🎤','🎧','🧊','🧸','🦋','🌻','🌵','🌊','🌋','🌟','🌞','🌚','🌪️','🌈','🌬️','🌦️','🌧️','🌨️','🌩️','🌫️','👽','💀','👻','👹','👺','🤖','😺','😸','😹','😻','😼','😽','🙀','😿','😾','🧠','💪','🦾','🦿','🦴','👁️','👀','👅','👂','🦷'
  ];
  // --- Tray open/close ---
  document.querySelectorAll('[data-open-tray]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      tray.classList.add('is-open');
      setTab(btn.getAttribute('data-open-tray'));
      search.value = '';
      renderGrid();
    });
  });
  document.querySelectorAll('[data-tray-close]').forEach(btn=>{
    btn.addEventListener('click',()=>{
      tray.classList.remove('is-open');
    });
  });
  // --- Tab switching ---
  tabs.forEach(tab=>{
    tab.addEventListener('click',()=>{
      setTab(tab.getAttribute('data-tab'));
      renderGrid();
    });
  });
  function setTab(tab){
    currentTab = tab;
    tabs.forEach(t=>t.classList.toggle('is-active', t.getAttribute('data-tab')===tab));
  }
  // --- Search ---
  search.addEventListener('input', renderGrid);
  // --- Grid rendering ---
  function renderGrid(){
    let items = [];
    const q = search.value.trim().toLowerCase();
    if(currentTab==='stickers'){
      items = stickerList.filter(s=>!q||s.label.toLowerCase().includes(q)||s.group.toLowerCase().includes(q));
      grid.innerHTML = items.map(s=>`<div class=\"ig-item\" data-type=\"sticker\" data-label=\"${s.label}\"><span class=\"ig-emoji\">${s.label}</span></div>`).join('');
    }else{
      items = emojiList.filter(e=>!q||e.includes(q));
      grid.innerHTML = items.map(e=>`<div class=\"ig-item\" data-type=\"emoji\" data-label=\"${e}\"><span class=\"ig-emoji\">${e}</span></div>`).join('');
    }
  }
  // --- Add to stage ---
  grid.addEventListener('click',function(e){
    const item = e.target.closest('.ig-item');
    if(!item) return;
    const type = item.getAttribute('data-type');
    const label = item.getAttribute('data-label');
    addToStage(label);
    tray.classList.remove('is-open');
  });
  // --- Add sticker/emoji node to stage ---
  function addToStage(label){
    const node = document.createElement('div');
    node.className = 'ig-node';
    node.style.setProperty('--x','80px');
    node.style.setProperty('--y','60px');
    node.style.setProperty('--s','1');
    node.innerHTML = `<span class=\"ig-emoji\">${label}</span>`;
    // Drag logic
    let dragging = false, startX=0, startY=0, origX=80, origY=60;
    node.addEventListener('mousedown',startDrag);
    node.addEventListener('touchstart',startDrag);
    function startDrag(ev){
      dragging = true;
      const evt = ev.touches ? ev.touches[0] : ev;
      startX = evt.clientX;
      startY = evt.clientY;
      origX = parseFloat(node.style.getPropertyValue('--x'))||0;
      origY = parseFloat(node.style.getPropertyValue('--y'))||0;
      document.addEventListener('mousemove',moveDrag);
      document.addEventListener('touchmove',moveDrag);
      document.addEventListener('mouseup',endDrag);
      document.addEventListener('touchend',endDrag);
      ev.preventDefault();
    }
    function moveDrag(ev){
      if(!dragging) return;
      const evt = ev.touches ? ev.touches[0] : ev;
      let dx = evt.clientX - startX;
      let dy = evt.clientY - startY;
      node.style.setProperty('--x', (origX+dx)+ 'px');
      node.style.setProperty('--y', (origY+dy)+ 'px');
    }
    function endDrag(){
      dragging = false;
      document.removeEventListener('mousemove',moveDrag);
      document.removeEventListener('touchmove',moveDrag);
      document.removeEventListener('mouseup',endDrag);
      document.removeEventListener('touchend',endDrag);
    }
    // Double-click to remove
    node.addEventListener('dblclick',()=>node.remove());
    stage.appendChild(node);
  }
})();
