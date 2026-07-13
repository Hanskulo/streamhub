#!/usr/bin/env python3
"""streaming-hub JustWatch fetcher -- multilingual (HU/EN/DE), NO key/signup/personal-data.
Writes data/<lang>/{providers,releases,premieres}.json for each UI language. build.py generates
one site tree per language. Premieres = movies releasing within the next PREM_DAYS days, exact dates."""
import os, sys, json, time, datetime, urllib.request, urllib.parse

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data")
URL = "https://apis.justwatch.com/graphql"
REGION = os.environ.get("REGION", "HU")
LANGS = ["hu", "en", "de"]
MAX_PROVIDERS = int(os.environ.get("MAX_PROVIDERS", "30"))
PERPROV_CAP = int(os.environ.get("PERPROV_CAP", "6"))
PREM_DAYS = int(os.environ.get("PREM_DAYS", "15"))
PREM_PAGES = int(os.environ.get("PREM_PAGES", "6"))
# FETCH_MODE: "all" (default) | "releases" (only per-provider newest) | "premieres" (only cinema premieres).
# Lets the daily cron / GitHub Action split cadences (e.g. releases every 2 days, premieres weekly).
FETCH_MODE = os.environ.get("FETCH_MODE", "all").lower()
# RELEASE_MAX_AGE_DAYS: drop streaming "new release" titles whose exact date is older than this (0 = keep all).
RELEASE_MAX_AGE_DAYS = int(os.environ.get("RELEASE_MAX_AGE_DAYS", "0"))
IMG = "https://images.justwatch.com"
UA = "Mozilla/5.0 (X11; Linux x86_64)"
TODAY = datetime.date.today()

PASTELS = ["#ff6b9d","#c9b3ff","#a3d5ff","#a8f0e0","#ffd6a3","#b3ffd9","#d9b3ff","#ffb3b3",
           "#a8e0ff","#c0f0d0","#ffc9e0","#b3d9ff","#e0b3ff","#ffe0a3","#b3fff0","#ff9db3",
           "#a8f0c0","#cfd0d8","#ffd0a8","#b3e0ff"]

# JustWatch genre short-codes -> per-language names
GENRES = {
    "hu": {"act":"Akció","ani":"Animáció","cmy":"Vígjáték","crm":"Krimi","doc":"Dokumentum","drm":"Dráma","eur":"Európai","fml":"Családi","fnt":"Fantasy","hrr":"Horror","hst":"Történelmi","msc":"Zene","myt":"Misztikus","rly":"Reality","rma":"Romantikus","scf":"Sci-Fi","spt":"Sport","trl":"Thriller","war":"Háborús","wsn":"Western","hlt":"Életmód","ksp":"Gyerek","nws":"Hírek","otr":"Egyéb"},
    "en": {"act":"Action","ani":"Animation","cmy":"Comedy","crm":"Crime","doc":"Documentary","drm":"Drama","eur":"European","fml":"Family","fnt":"Fantasy","hrr":"Horror","hst":"History","msc":"Music","myt":"Mystery","rly":"Reality","rma":"Romance","scf":"Sci-Fi","spt":"Sport","trl":"Thriller","war":"War","wsn":"Western","hlt":"Lifestyle","ksp":"Kids","nws":"News","otr":"Other"},
    "de": {"act":"Action","ani":"Animation","cmy":"Komödie","crm":"Krimi","doc":"Dokumentation","drm":"Drama","eur":"Europäisch","fml":"Familie","fnt":"Fantasy","hrr":"Horror","hst":"Historie","msc":"Musik","myt":"Mystery","rly":"Reality","rma":"Romantik","scf":"Sci-Fi","spt":"Sport","trl":"Thriller","war":"Kriegsfilm","wsn":"Western","hlt":"Lifestyle","ksp":"Kinder","nws":"Nachrichten","otr":"Andere"},
}
YT_WORD = {"hu": "előzetes", "en": "trailer", "de": "Trailer"}

def gql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    req = urllib.request.Request(URL, data=body, headers={"Content-Type": "application/json", "User-Agent": UA})
    for a in range(6):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                d = json.load(r)
            if "errors" in d:
                raise RuntimeError(json.dumps(d["errors"])[:200])
            return d["data"]
        except urllib.error.HTTPError as e:
            if e.code == 429:                 # rate limited -> back off hard
                time.sleep(7 * (a + 1)); continue
            if a == 5: raise
            time.sleep(1.3 * (a + 1))
        except Exception:
            if a == 5: raise
            time.sleep(1.3 * (a + 1))
    raise RuntimeError("gql: all attempts failed (rate limited?)")

def slugify(name):
    out = "".join(c if c.isalnum() else "-" for c in str(name).lower())
    while "--" in out: out = out.replace("--", "-")
    return out.strip("-") or "provider"

def poster(url):
    return IMG + url.replace("{profile}", "s332").replace("{format}", "jpg") if url else None

def yt(title, lang):
    return "https://www.youtube.com/results?search_query=" + urllib.parse.quote(f"{title} {YT_WORD.get(lang,'trailer')}")

def genres_of(gl, lang):
    m = GENRES[lang]
    out = [m.get(g.get("shortName"), (g.get("shortName") or "").capitalize()) for g in (gl or [])]
    return [x for x in out if x][:3]

TITLE_Q = """query N($country: Country!, $language: Language!, $filter: TitleFilter, $first: Int!, $after: String) {
  popularTitles(country: $country, first: $first, sortBy: RELEASE_YEAR, filter: $filter, after: $after) {
    pageInfo { endCursor hasNextPage }
    edges { node { objectType content(country: $country, language: $language) {
      title shortDescription originalReleaseYear originalReleaseDate posterUrl genres { shortName }
    } } }
  }
}"""

def valid_date(s):
    try:
        return datetime.date.fromisoformat(s) if s else None
    except Exception:
        return None

def fetch_titles(country, lang, package_short=None, object_types=None, first=16, release_year=None, pages=1):
    filt = {"objectTypes": object_types or ["MOVIE", "SHOW"]}
    if package_short: filt["packages"] = [package_short]
    if release_year: filt["releaseYear"] = release_year
    out = []; after = None
    for _ in range(pages):
        data = gql(TITLE_Q, {"country": country, "language": lang, "filter": filt, "first": first, "after": after})
        pt = data["popularTitles"]
        for e in pt["edges"]:
            n = e["node"]; c = n.get("content") or {}
            t = c.get("title")
            if not t: continue
            d = valid_date(c.get("originalReleaseDate"))
            out.append({"title": t, "media": "film" if n.get("objectType") == "MOVIE" else "sorozat",
                        "genres": genres_of(c.get("genres"), lang),
                        "overview": (c.get("shortDescription") or "").strip(),
                        "date": d.isoformat() if d else str(c.get("originalReleaseYear") or ""),
                        "poster": poster(c.get("posterUrl")), "trailer": yt(t, lang), "_d": d})
        if not pt["pageInfo"]["hasNextPage"]: break
        after = pt["pageInfo"]["endCursor"]; time.sleep(0.2)
    return out

def strip(items):
    return [{k: v for k, v in it.items() if not k.startswith("_")} for it in items]

def main():
    horizon = TODAY + datetime.timedelta(days=PREM_DAYS)
    # providers (language-neutral, fetched once)
    pkgs = gql("""query P($c: Country!){ packages(country:$c, platform: WEB, includeAddons:true){
      clearName shortName packageId monetizationTypes } }""", {"c": REGION})["packages"]
    subs = [p for p in pkgs if "FLATRATE" in (p.get("monetizationTypes") or [])] or pkgs
    providers = [{"slug": slugify(p["clearName"]), "name": p["clearName"], "tmdb_id": p["packageId"],
                  "accent": PASTELS[i % len(PASTELS)], "_short": p["shortName"]}
                 for i, p in enumerate(subs[:MAX_PROVIDERS])]

    do_releases = FETCH_MODE in ("all", "releases")
    do_premieres = FETCH_MODE in ("all", "premieres")
    min_date = (TODAY - datetime.timedelta(days=RELEASE_MAX_AGE_DAYS)) if RELEASE_MAX_AGE_DAYS > 0 else None
    for lang in LANGS:
        ddir = os.path.join(DATA, lang); os.makedirs(ddir, exist_ok=True)
        with open(os.path.join(ddir, "providers.json"), "w", encoding="utf-8") as f:
            json.dump({"region": REGION, "providers": [{k: v for k, v in p.items() if k != "_short"} for p in providers]},
                      f, ensure_ascii=False, indent=2)
        # per-provider newest titles (drop far-future + optionally too-old, exact date desc)
        if do_releases:
            by = {}
            for p in providers:
                try:
                    items = fetch_titles(REGION, lang, package_short=p["_short"], first=PERPROV_CAP + 10)
                except Exception as e:
                    print(f"  ! {lang}/{p['slug']}: {e}", file=sys.stderr); items = []
                kept, seen = [], set()
                for it in items:
                    if it["title"] in seen or (it["_d"] and it["_d"] > horizon): continue
                    if min_date and (not it["_d"] or it["_d"] < min_date): continue  # drop older than RELEASE_MAX_AGE_DAYS
                    seen.add(it["title"]); kept.append(it)
                kept.sort(key=lambda x: (x["_d"] or datetime.date.min), reverse=True)
                by[p["slug"]] = strip(kept[:PERPROV_CAP])
                time.sleep(0.12)
            with open(os.path.join(ddir, "releases.json"), "w", encoding="utf-8") as f:
                json.dump({"generated_at": datetime.datetime.now().isoformat(timespec="minutes"),
                           "week": TODAY.isoformat(), "by_provider": by}, f, ensure_ascii=False, indent=2)
        if not do_premieres:
            print(f"OK {lang}: {len(providers)} providers | mode={FETCH_MODE} (premieres skipped)")
            time.sleep(4); continue
        # premieres by region (next PREM_DAYS days, exact date asc)
        def prem(country):
            try:
                items = fetch_titles(country, lang, object_types=["MOVIE"],
                                     first=100, release_year={"min": TODAY.year, "max": horizon.year}, pages=PREM_PAGES)
            except Exception as e:
                print(f"  ! {lang}/prem {country}: {e}", file=sys.stderr); return []
            win = [it for it in items if it["_d"] and TODAY <= it["_d"] <= horizon]
            win.sort(key=lambda x: x["_d"]); seen, uniq = set(), []
            for it in win:
                if it["title"] in seen: continue
                seen.add(it["title"]); uniq.append(it)
            return strip(uniq[:8])
        premieres = {"generated_at": datetime.datetime.now().isoformat(timespec="minutes"),
                     "window": f"{TODAY.isoformat()} .. {horizon.isoformat()}",
                     "days": PREM_DAYS,
                     "regions": {"europe": {"items": prem("DE")}, "hungary": {"items": prem("HU")}, "usa": {"items": prem("US")}}}
        with open(os.path.join(ddir, "premieres.json"), "w", encoding="utf-8") as f:
            json.dump(premieres, f, ensure_ascii=False, indent=2)
        pn = {k: len(premieres["regions"][k]["items"]) for k in premieres["regions"]}
        print(f"OK {lang}: {len(providers)} providers | premieres EU/HU/US={pn}")
        time.sleep(4)  # polite pause between languages (avoid JustWatch 429)

    if do_premieres: reconcile_premieres()
    if do_releases: reconcile_releases()

def reconcile_releases():
    """Self-heal empty per-provider release lists (same rationale as
    reconcile_premieres): a provider's newest titles are the same across UI
    languages, only overview/genres localize. When the last language (de) gets
    429-throttled, some providers come back empty; backfill each empty provider
    slug from a sibling language (en preferred). Zero API calls."""
    loaded = {}
    for lang in LANGS:
        p = os.path.join(DATA, lang, "releases.json")
        try:
            loaded[lang] = json.load(open(p, encoding="utf-8"))
        except Exception:
            loaded[lang] = None
    for lang in LANGS:
        cur = loaded.get(lang)
        if not cur:
            continue
        by = cur.get("by_provider", {})
        donor_order = ["en"] + [l for l in LANGS if l != "en"]
        healed = 0
        for slug, items in list(by.items()):
            if items:
                continue
            for donor in donor_order:
                if donor == lang or not loaded.get(donor):
                    continue
                ditems = loaded[donor].get("by_provider", {}).get(slug)
                if ditems:
                    by[slug] = ditems
                    healed += 1
                    break
        if healed:
            with open(os.path.join(DATA, lang, "releases.json"), "w", encoding="utf-8") as f:
                json.dump(cur, f, ensure_ascii=False, indent=2)
            print(f"  ~ {lang}: {healed} empty provider release-lists healed from sibling")

def reconcile_premieres():
    """Self-heal empty premiere blocks. Premiere titles are region-based and
    language-independent (same movies premiere in DE/HU/US regardless of UI lang);
    only overview/genres are localized. If one language's premiere fetch was
    rate-limited (429 -> empty), backfill each empty region from any sibling
    language that has items. Costs zero API calls. Degradation: the borrowed
    overview/genres stay in the donor language, which beats a blank block."""
    loaded = {}
    for lang in LANGS:
        p = os.path.join(DATA, lang, "premieres.json")
        try:
            loaded[lang] = json.load(open(p, encoding="utf-8"))
        except Exception:
            loaded[lang] = None
    for lang in LANGS:
        cur = loaded.get(lang)
        if not cur:
            continue
        changed = False
        for region in cur.get("regions", {}):
            if cur["regions"][region].get("items"):
                continue
            # prefer English as the universally-readable fallback, then the rest
            donor_order = ["en"] + [l for l in LANGS if l != "en"]
            for donor in donor_order:
                if donor == lang or not loaded.get(donor):
                    continue
                items = loaded[donor].get("regions", {}).get(region, {}).get("items")
                if items:
                    cur["regions"][region]["items"] = items
                    cur["regions"][region]["_source_lang"] = donor
                    changed = True
                    break
        if changed:
            with open(os.path.join(DATA, lang, "premieres.json"), "w", encoding="utf-8") as f:
                json.dump(cur, f, ensure_ascii=False, indent=2)
            pn = {k: len(cur["regions"][k]["items"]) for k in cur["regions"]}
            print(f"  ~ {lang}: premieres healed from sibling -> EU/HU/US={pn}")

if __name__ == "__main__":
    main()
