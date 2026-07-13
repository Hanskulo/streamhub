#!/usr/bin/env python3
"""streaming-hub multilingual static site builder (HU/EN/DE).
Reads data/<lang>/{providers,releases,premieres}.json, writes site/ (hu at root, en/ de/ subdirs).
Language switcher, visitor counter + contact form (call API_BASE backend), SEO (canonical/hreflang/sitemap/robots).
Pastell cyber design, self-contained. Relative paths -> works at site root or subpath."""
import json, os, html, hashlib, base64, datetime, posixpath

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
SITE = os.path.join(ROOT, "site")
LANGS = ["hu", "en", "de"]
DEFAULT = "hu"
API_BASE = os.environ.get("API_BASE", "")            # backend for contact+counter ("" = same origin)
SITE_URL = os.environ.get("SITE_URL", "https://sean-enlarge-houses-fathers.trycloudflare.com").rstrip("/")

def esc(s): return html.escape(str(s or ""))
def load(lang, name):
    with open(os.path.join(DATA, lang, name), encoding="utf-8") as f:
        return json.load(f)

# ---------- i18n (chrome strings) ----------
T = {
 "hu": {"lang":"hu","contact":"Írj nekem","region":"RÉGIÓ","hero_pill":"naponta frissül · régió",
   "h1a":"Mi az ","h1b":"új","h1c":" a streamingen ezen a héten?",
   "hero_sub":"A(z) {n} magyar szolgáltató friss megjelenései egy helyen. Válassz egy platformot, és nézd meg mi érkezett — leírással, műfajjal, előzetessel.",
   "providers":"Szolgáltatók","new_cnt":"új cím","banner_k":"MOZIFILM PREMIEREK","banner_t":"Európa · Magyarország · USA — a következő {d} nap bemutatói, pontos dátummal",
   "back_home":"vissza a főoldalra","back_prov":"vissza a szolgáltatókhoz","weekline":"friss megjelenések",
   "no_h3":"Ezen a héten nincs új cím","no_p":"Nézz vissza holnap — naponta frissül.",
   "prem_h1":"Mozifilm premierek","prem_sub":"Európa · Magyarország · USA — régióra bontva, a következő {d} napban megjelenő filmek",
   "prem_win":"premierek · {w} (következő {d} nap)","prem_empty_h3":"Nincs premier a következő {d} napban",
   "prem_empty_p":"Ebben a régióban most nincs bemutató a megadott időablakban.","movie":"film","series":"sorozat",
   "trailer":"Előzetes","footer_data":"Adatok: JustWatch — nem hivatalos, non-commercial","footer_tag":"naponta frissül",
   "visitors":"látogató","search_ph":"Szűrj a szolgáltatók között...","no_match":"Nincs ilyen szolgáltató.",
   "stat_prov":"szolgáltató","stat_new":"friss cím összesen","stat_days":"nap premier-ablak","live":"élő",
   "m_title":"Írj Csabának","m_sub":"Az üzeneted közvetlenül, változtatás nélkül jut el hozzá.",
   "m_name":"Neved / elérhetőség (opcionális)","m_name_ph":"pl. Kovács Anna / anna@email.hu","m_msg":"Üzenet","m_msg_ph":"Írd ide az üzeneted...",
   "m_cancel":"Mégse","m_send":"Küldés","m_short":"Írj egy üzenetet.","m_sending":"Küldés...","m_ok":"Elküldve, köszönöm!","m_err":"Hiba, próbáld újra.",
   "reg":{"europe":"Európa","hungary":"Magyarország","usa":"USA"}},
 "en": {"lang":"en","contact":"Message me","region":"REGION","hero_pill":"updated daily · region",
   "h1a":"What's ","h1b":"new","h1c":" on streaming this week?",
   "hero_sub":"Fresh releases from {n} providers in one place. Pick a platform and see what just arrived — with description, genre and trailer.",
   "providers":"Providers","new_cnt":"new titles","banner_k":"MOVIE PREMIERES","banner_t":"Europe · Hungary · USA — premieres in the next {d} days, with exact dates",
   "back_home":"back to home","back_prov":"back to providers","weekline":"fresh releases",
   "no_h3":"No new titles this week","no_p":"Check back tomorrow — updated daily.",
   "prem_h1":"Movie premieres","prem_sub":"Europe · Hungary · USA — by region, films releasing in the next {d} days",
   "prem_win":"premieres · {w} (next {d} days)","prem_empty_h3":"No premieres in the next {d} days",
   "prem_empty_p":"No releases in this region within the given window right now.","movie":"movie","series":"series",
   "trailer":"Trailer","footer_data":"Data: JustWatch — unofficial, non-commercial","footer_tag":"updated daily",
   "visitors":"visitors","search_ph":"Filter providers...","no_match":"No such provider.",
   "stat_prov":"providers","stat_new":"fresh titles total","stat_days":"day premiere window","live":"live",
   "m_title":"Message Csaba","m_sub":"Your message reaches him directly, unchanged.",
   "m_name":"Your name / contact (optional)","m_name_ph":"e.g. Anna Smith / anna@email.com","m_msg":"Message","m_msg_ph":"Type your message...",
   "m_cancel":"Cancel","m_send":"Send","m_short":"Write a message.","m_sending":"Sending...","m_ok":"Sent, thank you!","m_err":"Error, try again.",
   "reg":{"europe":"Europe","hungary":"Hungary","usa":"USA"}},
 "de": {"lang":"de","contact":"Schreib mir","region":"REGION","hero_pill":"täglich aktualisiert · Region",
   "h1a":"Was ist ","h1b":"neu","h1c":" im Streaming diese Woche?",
   "hero_sub":"Neue Veröffentlichungen von {n} Anbietern an einem Ort. Wähle eine Plattform und sieh, was gerade kam — mit Beschreibung, Genre und Trailer.",
   "providers":"Anbieter","new_cnt":"neue Titel","banner_k":"KINO-PREMIEREN","banner_t":"Europa · Ungarn · USA — Premieren in den nächsten {d} Tagen, mit genauem Datum",
   "back_home":"zurück zur Startseite","back_prov":"zurück zu den Anbietern","weekline":"neue Veröffentlichungen",
   "no_h3":"Diese Woche keine neuen Titel","no_p":"Schau morgen wieder vorbei — täglich aktualisiert.",
   "prem_h1":"Kino-Premieren","prem_sub":"Europa · Ungarn · USA — nach Region, Filme der nächsten {d} Tage",
   "prem_win":"Premieren · {w} (nächste {d} Tage)","prem_empty_h3":"Keine Premieren in den nächsten {d} Tagen",
   "prem_empty_p":"In dieser Region gibt es derzeit keine Veröffentlichungen im angegebenen Zeitfenster.","movie":"Film","series":"Serie",
   "trailer":"Trailer","footer_data":"Daten: JustWatch — inoffiziell, non-commercial","footer_tag":"täglich aktualisiert",
   "visitors":"Besucher","search_ph":"Anbieter filtern...","no_match":"Kein solcher Anbieter.",
   "stat_prov":"Anbieter","stat_new":"neue Titel gesamt","stat_days":"Tage Premieren-Fenster","live":"live",
   "m_title":"Schreib an Csaba","m_sub":"Deine Nachricht erreicht ihn direkt, unverändert.",
   "m_name":"Dein Name / Kontakt (optional)","m_name_ph":"z.B. Anna Muster / anna@email.de","m_msg":"Nachricht","m_msg_ph":"Schreib deine Nachricht...",
   "m_cancel":"Abbrechen","m_send":"Senden","m_short":"Schreib eine Nachricht.","m_sending":"Senden...","m_ok":"Gesendet, danke!","m_err":"Fehler, bitte erneut.",
   "reg":{"europe":"Europa","hungary":"Ungarn","usa":"USA"}},
}

# ---------- paths (root-relative) ----------
def page_path(lang, kind, slug=None):
    pre = "" if lang == DEFAULT else f"{lang}/"
    if kind == "index": return f"{pre}index.html"
    if kind == "premierek": return f"{pre}premierek.html"
    if kind == "provider": return f"{pre}provider/{slug}.html"
    raise ValueError(kind)
def rel(frm, to):
    return posixpath.relpath(to, posixpath.dirname(frm)) or "."

# ---------- poster placeholder ----------
PASTELS = ["#ffb3d9","#c9b3ff","#a3d5ff","#a8f0e0","#ffd6a3","#b3ffd9","#d9b3ff","#ffb3b3"]
def poster_svg(title):
    h = int(hashlib.md5(title.encode("utf-8")).hexdigest(), 16)
    a = PASTELS[h % len(PASTELS)]; b = PASTELS[(h // 7) % len(PASTELS)]
    ini = "".join(w[0] for w in title.split()[:2]).upper() or "?"
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="450" viewBox="0 0 300 450">'
           f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{a}"/>'
           f'<stop offset="1" stop-color="{b}"/></linearGradient></defs><rect width="300" height="450" fill="#0f0e18"/>'
           f'<rect width="300" height="450" fill="url(#g)" opacity="0.22"/><g stroke="{a}" stroke-width="1" opacity="0.25">'
           + "".join(f'<line x1="0" y1="{y}" x2="300" y2="{y}"/>' for y in range(0,450,30))
           + "".join(f'<line x1="{x}" y1="0" x2="{x}" y2="450"/>' for x in range(0,300,30))
           + f'</g><text x="150" y="235" font-family="monospace" font-size="72" font-weight="700" fill="{a}" '
           f'text-anchor="middle" opacity="0.9">{esc(ini)}</text></svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode("utf-8")).decode()

CSS = open(os.path.join(ROOT, "_style.css"), encoding="utf-8").read() if os.path.exists(os.path.join(ROOT,"_style.css")) else ""

APP_JS = r"""// StreamHub interactions — reveal, count-up, provider filter, spotlight, header, region tabs.
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
"""

def title_card(it, acc, t):
    ps = it.get("poster") or poster_svg(it["title"])
    chips = "".join(f'<span class="chip">{esc(g)}</span>' for g in it.get("genres", []))
    tr = (f'<a class="trailer" href="{esc(it["trailer"])}" target="_blank" rel="noopener">&#9654; {esc(t["trailer"])}</a>'
          if it.get("trailer") else "")
    media = t["movie"] if it.get("media") == "film" else t["series"]
    return f"""<article class="tcard reveal" style="--acc:{acc}">
      <div class="pw"><img loading="lazy" src="{esc(ps)}" alt="{esc(it['title'])}"></div>
      <div class="body"><div class="media">{esc(media)}</div><h4>{esc(it['title'])}</h4>
      <div class="chips">{chips}</div><p>{esc(it.get('overview',''))}</p>{tr}
      <div class="date">&#128197; {esc(it.get('date',''))}</div></div></article>"""

def langswitch(cur_path, lang, kind, slug=None):
    out = []
    for L in LANGS:
        tgt = page_path(L, kind, slug)
        cls = "lsw on" if L == lang else "lsw"
        out.append(f'<a class="{cls}" href="{esc(rel(cur_path, tgt))}" hreflang="{L}">{L.upper()}</a>')
    return '<div class="langsw">' + "".join(out) + '</div>'

def topbar(cur_path, lang, kind, slug=None):
    t = T[lang]; region = "HU"
    home = rel(cur_path, page_path(lang, "index"))
    return f"""<header class="top"><div class="wrap"><div class="nav">
  <a class="brand" href="{esc(home)}"><span class="glyph">&#9678;</span> Stream<b>Hub</b></a>
  <div class="topright">
    <span class="region">{esc(t['region'])} // {region}</span>
    {langswitch(cur_path, lang, kind, slug)}
    <button type="button" class="cbtn" onclick="cxOpen()">&#9993; {esc(t['contact'])}</button>
  </div>
</div></div></header>"""

def foot(t):
    return f"""<footer><div class="wrap"><div class="fx">
  <span>{esc(t['footer_data'])}</span>
  <span class="visitors">&#128064; <b id="hitcount">…</b> {esc(t['visitors'])}</span>
  <span>StreamHub &middot; {esc(t['footer_tag'])}</span>
</div></div></footer>"""

JS_TMPL = """
<script>
var API=__API__;
function cxOpen(){document.getElementById('cxback').classList.add('on');document.getElementById('cxtext').focus()}
function cxClose(){document.getElementById('cxback').classList.remove('on')}
document.addEventListener('keydown',function(e){if(e.key==='Escape')cxClose()});
async function cxSend(){
  var t=document.getElementById('cxtext').value.trim(),f=document.getElementById('cxfrom').value.trim(),m=document.getElementById('cxmsg');
  if(t.length<2){m.className='cxmsg err';m.textContent=__SHORT__;return}
  m.className='cxmsg';m.textContent=__SENDING__;
  try{var r=await fetch(API+'/api/contact',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({from:f,message:t})});
    var j=await r.json();
    if(r.ok&&j.ok){m.className='cxmsg ok';m.textContent=__OK__;document.getElementById('cxtext').value='';document.getElementById('cxfrom').value='';setTimeout(cxClose,1400);}
    else{m.className='cxmsg err';m.textContent=(j&&j.error)||__ERR__;}
  }catch(e){m.className='cxmsg err';m.textContent=__ERR__;}
}
window.__API_BASE=API;
</script>"""

def contact_and_counter(t):
    modal = f"""
<div class="cxback" id="cxback" onclick="if(event.target===this)cxClose()">
  <div class="cxmodal" role="dialog" aria-modal="true">
    <h3>&#9993; {esc(t['m_title'])}</h3><p>{esc(t['m_sub'])}</p>
    <label for="cxfrom">{esc(t['m_name'])}</label>
    <input id="cxfrom" maxlength="120" placeholder="{esc(t['m_name_ph'])}">
    <label for="cxtext">{esc(t['m_msg'])}</label>
    <textarea id="cxtext" rows="5" maxlength="2000" placeholder="{esc(t['m_msg_ph'])}"></textarea>
    <div class="cxmsg" id="cxmsg"></div>
    <div class="cxrow"><button type="button" class="cxcancel" onclick="cxClose()">{esc(t['m_cancel'])}</button>
    <button type="button" class="cxsend" onclick="cxSend()">{esc(t['m_send'])}</button></div>
  </div>
</div>"""
    js = (JS_TMPL.replace("__API__", json.dumps(API_BASE)).replace("__SHORT__", json.dumps(t['m_short']))
          .replace("__SENDING__", json.dumps(t['m_sending'])).replace("__OK__", json.dumps(t['m_ok']))
          .replace("__ERR__", json.dumps(t['m_err'])))
    return modal + js

def head(lang, cur_path, kind, title, desc, slug=None):
    css = rel(cur_path, "assets/style.css")
    appjs = rel(cur_path, "assets/app.js")
    alts = "".join(f'<link rel="alternate" hreflang="{L}" href="{SITE_URL}/{page_path(L,kind,slug)}">' for L in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{SITE_URL}/{page_path(DEFAULT,kind,slug)}">'
    canon = f"{SITE_URL}/{cur_path}"
    return f"""<!DOCTYPE html>
<html lang="{lang}"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<meta name="theme-color" content="#0b0a14">
<link rel="canonical" href="{esc(canon)}">
{alts}
<meta property="og:title" content="{esc(title)}"><meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website"><meta property="og:url" content="{esc(canon)}">
<meta name="robots" content="index, follow">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='88'>&#128250;</text></svg>">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700;12..96,800&family=Instrument+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="{esc(css)}">
<script defer src="{esc(appjs)}"></script>
</head><body>"""

def write(path, content):
    full = os.path.join(SITE, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(content)

def build():
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    with open(os.path.join(SITE, "assets", "style.css"), "w", encoding="utf-8") as f:
        f.write(CSS)
    with open(os.path.join(SITE, "assets", "app.js"), "w", encoding="utf-8") as f:
        f.write(APP_JS)
    all_urls = []
    for lang in LANGS:
        t = T[lang]
        prov = load(lang, "providers.json"); rel_data = load(lang, "releases.json"); prem = load(lang, "premieres.json")
        providers = prov["providers"]; by = rel_data.get("by_provider", {})
        idx_path = page_path(lang, "index")
        # index
        total_new = sum(len(by.get(p["slug"], [])) for p in providers)
        pdays = prem.get("days", 15)
        cards = []
        for i, p in enumerate(providers, 1):
            cnt = len(by.get(p["slug"], []))
            cards.append(f"""<a class="pcard reveal" data-name="{esc(p['name'].lower())}" style="--acc:{esc(p['accent'])}" href="{esc(rel(idx_path, page_path(lang,'provider',p['slug'])))}">
        <div class="rank">#{i:02d}</div><div class="badge">{esc(p['name'][0])}</div>
        <h3>{esc(p['name'])}</h3><div class="cnt"><b>{cnt}</b> {esc(t['new_cnt'])}</div></a>""")
        search_svg = '<svg viewBox="0 0 24 24" fill="none" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'
        body = f"""{topbar(idx_path, lang, 'index')}
  <section class="hero"><div class="wrap hero-grid">
    <div class="hero-main">
      <span class="pill"><span class="dot"></span> {esc(t['hero_pill'])} HU</span>
      <h1>{esc(t['h1a'])}<span class="g">{esc(t['h1b'])}</span>{esc(t['h1c'])}</h1>
      <p>{esc(t['hero_sub'].format(n=len(providers)))}</p>
      <div class="toolbar">
        <div class="search">{search_svg}<input id="provSearch" type="search" autocomplete="off" placeholder="{esc(t['search_ph'])}" aria-label="{esc(t['search_ph'])}"></div>
        <a class="ghostbtn" href="{esc(rel(idx_path, page_path(lang,'premierek')))}">&#127916; {esc(t['prem_h1'])} &#8594;</a>
      </div>
    </div>
    <aside class="hero-side">
      <div class="stat reveal"><div class="n" data-count="{len(providers)}">0</div><div class="l">{esc(t['stat_prov'])}</div></div>
      <div class="stat s2 reveal"><div class="n" data-count="{total_new}">0</div><div class="l">{esc(t['stat_new'])}</div></div>
      <div class="stat s3 reveal"><div class="n" data-count="{pdays}">0</div><div class="l">{esc(t['stat_days'])}</div></div>
    </aside>
  </div></section>
  <div class="wrap">
    <a class="pbanner reveal" href="{esc(rel(idx_path, page_path(lang,'premierek')))}">
      <div><div class="pb-k">&#127916; {esc(t['banner_k'])}</div><div class="pb-t">{esc(t['banner_t'].format(d=pdays))}</div></div>
      <span class="pb-arrow">&#8594;</span></a>
    <div class="seclabel"><h2>{esc(t['providers'])}</h2><span class="cnt-badge">Top {len(providers)}</span><div class="ln"></div></div>
    <div class="grid" id="provGrid">{''.join(cards)}</div>
    <div class="nomatch" id="noMatch" hidden>{esc(t['no_match'])}</div>
  </div>{foot(t)}"""
        write(idx_path, head(lang, idx_path, "index", f"StreamHub — {t['prem_h1']} · {len(providers)} {t['providers']}", t['hero_sub'].format(n=len(providers)))
              + body + contact_and_counter(t) + "</body></html>")
        all_urls.append(idx_path)
        # provider pages
        for p in providers:
            pp = page_path(lang, "provider", p["slug"]); acc = esc(p["accent"]); items = by.get(p["slug"], [])
            if items:
                inner = f'<div class="titles">{"".join(title_card(it, acc, t) for it in items)}</div>'
            else:
                inner = f'<div class="empty"><div class="ic">&#128268;</div><h3>{esc(t["no_h3"])}</h3><p>{esc(t["no_p"])}</p></div>'
            body = f"""{topbar(pp, lang, 'provider', p['slug'])}
  <div class="wrap"><a class="back" href="{esc(rel(pp, idx_path))}">&#8592; {esc(t['back_prov'])}</a>
    <div class="phead"><div class="big" style="--acc:{acc}">{esc(p['name'][0])}</div>
      <div><h1><span style="color:{acc}">{esc(p['name'])}</span></h1><div class="weekline">{esc(t['weekline'])}</div></div></div>
    {inner}</div>{foot(t)}"""
            write(pp, head(lang, pp, "provider", f"{p['name']} — StreamHub", f"{p['name']}: {t['weekline']}", slug=p['slug'])
                  + body + contact_and_counter(t) + "</body></html>")
            all_urls.append(pp)
        # premieres
        pr_path = page_path(lang, "premierek"); acc_map = {"europe":"#c9b3ff","hungary":"#a8f0e0","usa":"#ffb3d9"}
        flags = {"europe":"\U0001F1EA\U0001F1FA","hungary":"\U0001F1ED\U0001F1FA","usa":"\U0001F1FA\U0001F1F8"}
        days = prem.get("days", 15); win = prem.get("window", "")
        secs = []; tabs = []
        for rk in ("europe","hungary","usa"):
            its = prem.get("regions", {}).get(rk, {}).get("items", []); acc = acc_map[rk]
            tabs.append(f'<button type="button" class="regtab" data-region="{rk}"><span>{flags[rk]}</span> {esc(t["reg"][rk])} <span class="rc">{len(its)}</span></button>')
            if its:
                inner = f'<div class="titles">{"".join(title_card(it, acc, t) for it in its)}</div>'
            else:
                inner = f'<div class="empty"><div class="ic">&#127917;</div><h3>{esc(t["prem_empty_h3"].format(d=days))}</h3><p>{esc(t["prem_empty_p"])}</p></div>'
            secs.append(f"""<section class="region-sec reveal" id="reg-{rk}" data-region="{rk}"><h2><span>{flags[rk]}</span> {esc(t['reg'][rk])}</h2>
      <div class="rsub">{esc(t['prem_win'].format(w=win, d=days))}</div>{inner}</section>""")
        body = f"""{topbar(pr_path, lang, 'premierek')}
  <div class="wrap"><a class="back" href="{esc(rel(pr_path, idx_path))}">&#8592; {esc(t['back_home'])}</a>
    <div class="phead"><div><h1>&#127916; {esc(t['prem_h1'])}</h1><div class="weekline">{esc(t['prem_sub'].format(d=days))}</div></div></div>
    <div class="regtabs" id="regTabs" data-all="{esc({'hu':'Mind','en':'All','de':'Alle'}[lang])}">{''.join(tabs)}</div>
    {''.join(secs)}</div>{foot(t)}"""
        write(pr_path, head(lang, pr_path, "premierek", f"{t['prem_h1']} — StreamHub", t['prem_sub'].format(d=days))
              + body + contact_and_counter(t) + "</body></html>")
        all_urls.append(pr_path)
    # SEO: robots.txt + sitemap.xml
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    today = datetime.date.today().isoformat()
    urls = "".join(f"<url><loc>{SITE_URL}/{u}</loc><lastmod>{today}</lastmod></url>" for u in all_urls)
    write("sitemap.xml", f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
    print(f"built {len(LANGS)} langs, {len(all_urls)} pages -> {SITE}  (SITE_URL={SITE_URL}, API_BASE={API_BASE or 'same-origin'})")

if __name__ == "__main__":
    build()
