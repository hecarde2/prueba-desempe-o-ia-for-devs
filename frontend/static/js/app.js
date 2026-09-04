const chat = document.getElementById('chat');
    const input = document.getElementById('message');
    const sendBtn = document.getElementById('sendBtn');
    const charCount = document.getElementById('charCount');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('overlay');
    const openSidebar = document.getElementById('openSidebar');
    const closeSidebar = document.getElementById('closeSidebar');
    const quickInfoBtn = document.getElementById('quickInfoBtn');
    const themeLight = document.getElementById('themeLight');
    const themeDark = document.getElementById('themeDark');
    const themeToggle = document.getElementById('themeToggle');
    const topThemeBtn = document.getElementById('topThemeBtn');
    const themeLabel = document.getElementById('themeLabel');
    const fontRange = document.getElementById('fontRange');
    const fontLabel = document.getElementById('fontLabel');
    const fontDown = document.getElementById('fontDown');
    const fontUp = document.getElementById('fontUp');
    const densityComfort = document.getElementById('densityComfort');
    const densityCompact = document.getElementById('densityCompact');
    const animToggle = document.getElementById('animToggle');
    const resetBtn = document.getElementById('resetBtn');
    const prefs = {
      theme: localStorage.getItem('sora-theme') || 'dark',
      font: parseInt(localStorage.getItem('sora-font') || '100', 10),
      density: localStorage.getItem('sora-density') || 'comfort',
      anim: localStorage.getItem('sora-anim') !== 'false'
    };
    function applyTheme(t){
      prefs.theme = t;
      document.documentElement.setAttribute('data-theme', t);
      localStorage.setItem('sora-theme', t);
      themeLabel.textContent = t === 'light' ? 'Claro' : 'Oscuro';
      themeLight.classList.toggle('active', t === 'light');
      themeDark.classList.toggle('active', t === 'dark');
    }
    function applyFont(v){
      prefs.font = v;
      document.documentElement.style.setProperty('--font-scale', (v/100).toString());
      fontRange.value = v;
      fontLabel.textContent = v + '%';
      localStorage.setItem('sora-font', String(v));
    }
    function applyDensity(d){
      prefs.density = d;
      document.documentElement.setAttribute('data-density', d);
      localStorage.setItem('sora-density', d);
      densityComfort.classList.toggle('active', d === 'comfort');
      densityCompact.classList.toggle('active', d === 'compact');
    }
    function applyAnim(on){
      prefs.anim = on;
      document.documentElement.style.setProperty('--anim', on ? '1' : '0');
      if(!on){
        const s=document.createElement('style'); s.id='no-anim'; s.textContent='*{animation:none !important; transition:none !important}';
        if(!document.getElementById('no-anim')) document.head.appendChild(s);
      } else {
        const el=document.getElementById('no-anim'); if(el) el.remove();
      }
      localStorage.setItem('sora-anim', String(on));
      animToggle.checked = on;
    }
    applyTheme(prefs.theme);
    applyFont(prefs.font);
    applyDensity(prefs.density);
    applyAnim(prefs.anim);
    themeLight.addEventListener('click', ()=> applyTheme('light'));
    themeDark.addEventListener('click', ()=> applyTheme('dark'));
    const toggleTheme = ()=> applyTheme(prefs.theme === 'dark' ? 'light' : 'dark');
    themeToggle.addEventListener('click', toggleTheme);
    topThemeBtn.addEventListener('click', toggleTheme);
    fontRange.addEventListener('input', e=> applyFont(parseInt(e.target.value,10)));
    fontDown.addEventListener('click', ()=> applyFont(Math.max(85, prefs.font - 5)));
    fontUp.addEventListener('click', ()=> applyFont(Math.min(130, prefs.font + 5)));
    densityComfort.addEventListener('click', ()=> applyDensity('comfort'));
    densityCompact.addEventListener('click', ()=> applyDensity('compact'));
    animToggle.addEventListener('change', e=> applyAnim(e.target.checked));
    resetBtn.addEventListener('click', ()=>{
      localStorage.clear();
      applyTheme('dark'); applyFont(100); applyDensity('comfort'); applyAnim(true);
    });
    function openBar(){ sidebar.classList.add('open'); overlay.classList.add('open'); document.body.style.overflow='hidden'; }
    function closeBar(){ sidebar.classList.remove('open'); overlay.classList.remove('open'); document.body.style.overflow=''; }
    openSidebar.addEventListener('click', openBar);
    quickInfoBtn.addEventListener('click', openBar);
    closeSidebar.addEventListener('click', closeBar);
    overlay.addEventListener('click', closeBar);
    if(window.innerWidth > 960){ sidebar.classList.add('open'); }
    window.addEventListener('resize', ()=>{
      if(window.innerWidth > 960){ overlay.classList.remove('open'); document.body.style.overflow=''; sidebar.classList.add('open'); }
      else { sidebar.classList.remove('open'); }
    });
    function renderSidebarInfo(items){
      const map = Object.fromEntries((items||[]).map(i=> [i.label.toLowerCase(), i.value]));
      const supportEmail = document.getElementById('supportEmail');
      const admissionsEmail = document.getElementById('admissionsEmail');
      const hoursSub = document.getElementById('hoursSub');
      const priceTable = document.getElementById('priceTable');
      if(map['soporte'] && supportEmail){ supportEmail.textContent = map['soporte']; supportEmail.closest('a').href = 'mailto:'+map['soporte']; }
      if(map['admisiones'] && admissionsEmail){ admissionsEmail.textContent = map['admisiones']; admissionsEmail.closest('a').href = 'mailto:'+map['admisiones']; }
      if(map['horario'] && hoursSub){ hoursSub.textContent = map['horario']; }
      const stats = document.getElementById('quickStats');
      if(map['precio'] && stats){
        const m = map['precio'].match(/\$(\d+)/);
        if(m) stats.children[1].querySelector('strong').textContent = '$' + m[1];
      }
    }
    function loadInfo(){
      fetch('/api/info').then(r=>r.json()).then(d=>{ if(d.items) renderSidebarInfo(d.items); }).catch(()=>{
        renderSidebarInfo([
          {label:'Cursos', value:'Bots · Data Science · Prompt Eng.'},
          {label:'Precio', value:'$150 · $280 · $160 USD'},
          {label:'Soporte', value:'soporte@academiatech.com'},
          {label:'Admisiones', value:'admisiones@academiatech.com'},
          {label:'Horario', value:'Lun-Vie 8:00-18:00 GMT-5'}
        ]);
      });
    }
    function addMessage(text, sender='bot'){
      const row=document.createElement('div'); row.className='msg '+sender;
      const bubble=document.createElement('div'); bubble.className='bubble'; bubble.textContent=text;
      row.appendChild(bubble); chat.appendChild(row); chat.scrollTop=chat.scrollHeight;
    }
    function showTyping(){
      const row=document.createElement('div'); row.className='msg bot'; row.id='typing';
      const bubble=document.createElement('div'); bubble.className='bubble';
      bubble.innerHTML='<div class="typing"><span></span><span></span><span></span></div>';
      row.appendChild(bubble); chat.appendChild(row); chat.scrollTop=chat.scrollHeight;
    }
    function hideTyping(){ const t=document.getElementById('typing'); if(t) t.remove(); }
    function autoResize(){
      input.style.height='auto';
      input.style.height=Math.min(input.scrollHeight,120)+'px';
    }
    input.addEventListener('input', ()=>{ autoResize(); charCount.textContent=input.value.length; });
    input.addEventListener('keydown', e=>{
      if(e.key==='Enter' && !e.shiftKey){ e.preventDefault(); sendMessage(); }
    });
    function sendMessage(q){
      const text = (q !== undefined ? String(q) : input.value).trim();
      if(!text) return;
      addMessage(text,'user');
      if(q === undefined) input.value='';
      charCount.textContent='0'; autoResize();
      input.disabled=true; sendBtn.disabled=true;
      showTyping();
      fetch('/api/chat',{
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({message:text})
      }).then(async res=>{
        const data=await res.json();
        hideTyping();
        if(!res.ok) throw new Error(data.error||'Error');
        addMessage(data.answer||'Sin respuesta','bot');
      }).catch(err=>{
        hideTyping();
        addMessage('No tengo esa información disponible contacto con un asesor humano en sora@mail.com','bot');
        console.error(err);
      }).finally(()=>{
        input.disabled=false; sendBtn.disabled=false; input.focus();
      });
    }
    sendBtn.addEventListener('click', ()=> sendMessage());
    document.getElementById('suggestions').addEventListener('click', e=>{
      const btn=e.target.closest('.chip'); if(!btn) return;
      sendMessage(btn.dataset.q);
    });
    loadInfo();
    addMessage('¡Hola! Soy Sora, la asistente virtual de la Academia de Tecnología e IA. ¿En qué te puedo ayudar hoy?', 'bot');
    document.addEventListener('keydown', e=>{
      if((e.ctrlKey||e.metaKey) && e.key.toLowerCase()==='b'){ e.preventDefault(); sidebar.classList.contains('open') ? closeBar() : openBar(); }
      if(e.key==='Escape') closeBar();
    });