// StreamHub interactions — reveal, count-up, provider filter, spotlight, header, region tabs.
(function(){
  var RM = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // sticky header state
  var hdr = document.querySelector('header.top');
  function onScroll(){ if(hdr) hdr.classList.toggle('scrolled', window.scrollY > 8); }
  onScroll(); window.addEventListener('scroll', onScroll, {passive:true});

  // scroll reveal
  var reveals = [].slice.call(document.querySelectorAll('.reveal'));
  if(RM || !('IntersectionObserver' in window)){ reveals.forEach(function(el){el.classList.add('in');}); }
  else{
    var io = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target); } });
    }, {rootMargin:'0px 0px -8% 0px', threshold:0.05});
    reveals.forEach(function(el){ io.observe(el); });
  }

  // count-up for [data-count]
  function countUp(el){
    var target = parseInt(el.getAttribute('data-count'),10)||0;
    if(RM){ el.textContent = target.toLocaleString(); return; }
    var dur=1100, t0=null;
    function step(ts){ if(!t0)t0=ts; var p=Math.min((ts-t0)/dur,1); var e=1-Math.pow(1-p,3);
      el.textContent = Math.round(target*e).toLocaleString(); if(p<1) requestAnimationFrame(step); }
    requestAnimationFrame(step);
  }
  var counters = [].slice.call(document.querySelectorAll('[data-count]'));
  if('IntersectionObserver' in window && !RM){
    var cio = new IntersectionObserver(function(entries){
      entries.forEach(function(e){ if(e.isIntersecting){ countUp(e.target); cio.unobserve(e.target); } });
    }, {threshold:0.4});
    counters.forEach(function(el){ cio.observe(el); });
  } else { counters.forEach(countUp); }

  // pointer spotlight on provider cards
  if(!RM){
    document.querySelectorAll('.pcard').forEach(function(card){
      card.addEventListener('pointermove', function(ev){
        var r=card.getBoundingClientRect();
        card.style.setProperty('--mx', (ev.clientX-r.left)+'px');
        card.style.setProperty('--my', (ev.clientY-r.top)+'px');
      });
    });
  }

  // live provider filter
  var search = document.getElementById('provSearch');
  if(search){
    var grid = document.getElementById('provGrid');
    var nomatch = document.getElementById('noMatch');
    var cards = grid ? [].slice.call(grid.querySelectorAll('.pcard')) : [];
    search.addEventListener('input', function(){
      var q = search.value.trim().toLowerCase(); var shown=0;
      cards.forEach(function(c){
        var hit = !q || (c.getAttribute('data-name')||'').indexOf(q) !== -1;
        c.style.display = hit ? '' : 'none'; if(hit) shown++;
      });
      if(nomatch) nomatch.hidden = shown !== 0;
    });
  }

  // premiere region tabs (filter which region section shows)
  var tabsWrap = document.getElementById('regTabs');
  if(tabsWrap){
    var tabs = [].slice.call(tabsWrap.querySelectorAll('.regtab'));
    var secs = [].slice.call(document.querySelectorAll('.region-sec'));
    function activate(region){
      tabs.forEach(function(tb){ tb.classList.toggle('on', tb.getAttribute('data-region')===region); });
      secs.forEach(function(s){ s.style.display = (region==='all'||s.getAttribute('data-region')===region)?'':'none'; });
    }
    // prepend an "all" tab
    var allBtn = document.createElement('button');
    allBtn.type='button'; allBtn.className='regtab on'; allBtn.setAttribute('data-region','all');
    allBtn.textContent = tabsWrap.getAttribute('data-all') || 'Mind';
    tabsWrap.insertBefore(allBtn, tabsWrap.firstChild);
    tabsWrap.addEventListener('click', function(ev){
      var b = ev.target.closest('.regtab'); if(!b) return; activate(b.getAttribute('data-region'));
    });
  }

  // visitor counter (count-up), backend from window.__API_BASE
  var hc = document.getElementById('hitcount');
  if(hc){
    var API = window.__API_BASE || '';
    fetch(API+'/api/hits').then(function(r){return r.json();}).then(function(j){
      if(j && typeof j.count==='number'){ hc.setAttribute('data-count', j.count); countUp(hc); }
      else if(hc.parentNode){ hc.parentNode.style.display='none'; }
    }).catch(function(){ if(hc.parentNode) hc.parentNode.style.display='none'; });
  }
})();

// ---- Közös látogató-számláló (Kata) — a .vc[data-vc-site] widgetre dolgozik, önálló ----
(function () {
  "use strict";
  var el = document.querySelector(".vc[data-vc-site]");
  if (!el) return;
  var site = el.getAttribute("data-vc-site");
  var api = (el.getAttribute("data-vc-api") || "").replace(/\/+$/, "");
  if (!site || !api) return;
  var sid = "";
  try {
    sid = sessionStorage.getItem("vc_sid");
    if (!sid) { sid = Date.now().toString(36) + Math.random().toString(36).slice(2, 10); sessionStorage.setItem("vc_sid", sid); }
  } catch (e) {}
  function render(d) {
    if (!d || typeof d !== "object") return;
    var h = el.querySelector('[data-vc="human"]'); var b = el.querySelector('[data-vc="bot"]');
    if (h && typeof d.human === "number") h.textContent = d.human.toLocaleString();
    if (b && typeof d.bot === "number") b.textContent = d.bot.toLocaleString();
    el.setAttribute("data-vc-ready", "1");
  }
  function fetchCount() {
    fetch(api + "/count?site=" + encodeURIComponent(site), { cache: "no-store" })
      .then(function (r) { return r.ok ? r.json() : null; }).then(render).catch(function () {});
  }
  var hitKey = "vc_hit_" + site, already = false;
  try { already = sessionStorage.getItem(hitKey) === "1"; } catch (e) {}
  if (already) { fetchCount(); }
  else {
    fetch(api + "/hit?site=" + encodeURIComponent(site), {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ sid: sid }), keepalive: true
    }).then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { try { sessionStorage.setItem(hitKey, "1"); } catch (e) {} render(d); })
      .catch(fetchCount);
  }
})();
