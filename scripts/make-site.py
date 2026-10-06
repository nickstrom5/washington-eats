"""Writes the public website in docs/ from the same data file the app ships (data/app/places.json).

Pages: the landing page, four statewide guides (Seattle teriyaki, phở, drive-in burgers, oysters & seafood), one page per big city,
the web app (/explore/), privacy, terms, 404, plus sitemap.xml, robots.txt and site.webmanifest. Everything listed is hand-checked
research or licensed open data (Overture Maps, King County's public-domain inspection records); nothing comes from Google, Yelp or
any ratings site, and nothing is ranked by ratings. Adapted from wi-eats/scripts/make-site.py.

Usage (from the repo root): .venv/bin/python scripts/make-site.py
Re-run it after every data rebuild, then check the pages: .venv/bin/python scripts/qa-site.py
"""
import html
import json
import math
import os
import re
import struct
from collections import Counter, defaultdict

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = f"{ROOT}/docs"
# Where the site lives. Until Nick's Cloudflare record `washington CNAME nickstrom5.github.io` (DNS only) resolves, the site is served
# at the GitHub Pages project address. Then set CUSTOM_DOMAIN = "washington.eatsranked.com", re-run, push (with Nick's OK), and GitHub
# forwards the old github.io links (the ones inside shipped app builds) to it.
CUSTOM_DOMAIN = ""
DOMAIN = f"https://{CUSTOM_DOMAIN}" if CUSTOM_DOMAIN else "https://nickstrom5.github.io/washington-eats"
BASE = "" if CUSTOM_DOMAIN else "/washington-eats"     # path prefix for root-relative links
BRAND = "Washington Eats"
TAGLINE = "Teriyaki & Washington State food guide"
EMAIL = "work-with-nick@gmail.com"
TODAY = "2026-10-05"
CHECKED = "October 2026"

D = json.load(open(f"{ROOT}/data/app/places.json"))
CITIES, CUISINES, COUNTIES = D["cities"], D["cuisines"], D["counties"]
THROUGH = D["records_through"]
TERIYAKI, PHO, SEAFOOD, DRIVEIN, ESPRESSO = 1, 2, 4, 8, 16
KCR = {4: "Excellent", 3: "Good", 2: "Okay", 1: "Needs to Improve"}
HIST = json.load(open(f"{ROOT}/data/research/teriyaki_history.json"))


class P:
    """One place, with the same meaning the app gives each field (WashingtonEats/Models/Place.swift)."""

    def __init__(self, r):
        self.r = r
        self.name = r["n"]
        self.city = CITIES[r["c"]] if r.get("c") is not None else ""
        self.county = COUNTIES[r["co"]] if r.get("co") is not None else None
        self.cuisine = CUISINES[r["cu"]] if r.get("cu") is not None else ""
        self.addr = r.get("a") or ""
        self.zip = r.get("z") or ""
        self.lat, self.lon = r.get("la"), r.get("lo")
        self.tags = r.get("g") or 0
        self.checked = r.get("hc") or 0       # which guides it's hand-checked for (bits as tags; 128 = honors only)
        self.chain = (r.get("ch") or 0) >= 5
        self.venue = r.get("v") == 1
        self.ip = r.get("ip")
        self.founded = r.get("f")
        self.brand_founded = r.get("bf")
        self.dishes = r.get("di") or ""
        self.note = r.get("note") or r.get("icon") or ""
        self.site = r.get("w") or ""
        self.jbf = r.get("jbf") or ""
        self.kasahara = r.get("ks") == 1
        self.kc = r.get("kc") or {}

    def key(self):
        return (self.city, self.name.lower())


PLACES = [P(r) for r in D["places"]]
REST = [p for p in PLACES if not p.venue]
TERI = [p for p in REST if p.checked & TERIYAKI]
PHOS = [p for p in REST if p.checked & PHO]
DRIVE = [p for p in REST if p.checked & DRIVEIN]
SEA = [p for p in REST if p.checked & SEAFOOD]
OYSTER_BARS = [p for p in SEA if re.search(r"oyster", p.name + " " + p.dishes + " " + p.note, re.I)]
RATED = [p for p in REST if p.kc.get("r")]

# ---------------------------------------------------------------- regions (counties grouped)
REGIONS = {
    "Seattle and King County": "King",
    "North Sound": "Snohomish Island Skagit Whatcom San_Juan",
    "Tacoma and the South Sound": "Pierce Thurston Mason",
    "Kitsap and the Olympic Peninsula": "Kitsap Clallam Jefferson Grays_Harbor Pacific",
    "Southwest Washington": "Clark Cowlitz Lewis Skamania Wahkiakum Klickitat",
    "Central Washington": "Yakima Kittitas Chelan Douglas Grant Okanogan Benton Franklin Adams",
    "Spokane and eastern Washington": "Spokane Stevens Pend_Oreille Ferry Lincoln Whitman Walla_Walla Columbia Garfield Asotin",
}
REGION_OF = {c.replace("_", " "): r for r, cs in REGIONS.items() for c in cs.split()}
assert len(REGION_OF) == 39, len(REGION_OF)
assert set(REGION_OF) == set(COUNTIES), set(COUNTIES) ^ set(REGION_OF)
for p in PLACES:
    p.region = REGION_OF.get(p.county) if p.county else None


def miles(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


# ---------------------------------------------------------------- html helpers
e = html.escape


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("'", "")).strip("-")


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24])


APPLE = '<svg viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M16.4 12.6c0-2.5 2-3.7 2.1-3.8-1.2-1.7-3-1.9-3.6-2-1.5-.2-3 .9-3.8.9-.8 0-2-.9-3.3-.9-1.7 0-3.3 1-4.1 2.5-1.8 3.1-.5 7.6 1.3 10.1.9 1.2 1.9 2.6 3.2 2.6 1.3-.1 1.8-.8 3.3-.8 1.6 0 2 .8 3.3.8 1.4 0 2.3-1.3 3.1-2.5 1-1.4 1.4-2.8 1.4-2.9 0 0-2.7-1-2.9-4zM14 5.2c.7-.8 1.2-2 1-3.2-1 0-2.2.7-2.9 1.5-.6.7-1.2 1.9-1.1 3.1 1.1.1 2.3-.6 3-1.4z"/></svg>'
# the app icon in miniature: two Rainier cherries on evergreen
LOGO = ('<svg viewBox="0 0 64 64" width="30" height="30" aria-hidden="true"><rect width="64" height="64" rx="14" fill="#1F4D3A"/>'
        '<path d="M22 40 Q24 26 36 14 M40 41 Q40 26 36 14" stroke="#7A9A3A" stroke-width="2.4" fill="none" stroke-linecap="round"/>'
        '<path d="M36 14 Q46 8 54 12 Q46 18 36 14 Z" fill="#5DAE4B"/>'
        '<circle cx="21" cy="44" r="10" fill="#F2A33A"/><circle cx="41" cy="45" r="10" fill="#E5764F"/>'
        '<circle cx="18" cy="41" r="3.2" fill="#FFF1B0"/><circle cx="38" cy="42" r="3.2" fill="#FFE29A"/></svg>')
FAVICON = "data:image/svg+xml," + LOGO.replace('width="30" height="30" ', "").replace(' aria-hidden="true"', "").replace("<svg ", "<svg xmlns='http://www.w3.org/2000/svg' ").replace('"', "'").replace("#", "%23").replace("<", "%3C").replace(">", "%3E")

CSS = """
  :root {
    --bg: #f9fbf9; --surface: #fff; --surface2: #eef4f1; --rule: #dbe5e0;
    --ink: #13231c; --ink2: #2b4038; --muted: #4f635a;
    --green: #1f4d3a; --green2: #2c6a50; --sound: #1b5e7a; --soundsoft: #e3eff4; --red: #b3262e;
    --gold: #f7c948; --goldsoft: #fdf0c4;
    --radius: 16px;
    --display: "Avenir Next Condensed", "HelveticaNeue-CondensedBold", "Arial Narrow", system-ui, sans-serif;
  }
  @media (prefers-color-scheme: dark) {
    :root { --bg: #0f1814; --surface: #16211c; --surface2: #1d2b25; --rule: #2a3a33; --ink: #eef3f0; --ink2: #d0dbd5; --muted: #a6b8ae; --green: #9fd3b8; --green2: #7fbf9f; --sound: #8cc6de; --soundsoft: #183039; --red: #f09096; }
  }
  * { box-sizing: border-box; }
  html { -webkit-text-size-adjust: 100%; }
  @media (prefers-reduced-motion: no-preference) { html { scroll-behavior: smooth; } }
  @media (prefers-reduced-motion: reduce) { * { animation: none !important; transition: none !important; } }
  body { margin: 0; background: var(--bg); color: var(--ink); font: 17px/1.55 -apple-system, BlinkMacSystemFont, "SF Pro Text", system-ui, sans-serif; -webkit-font-smoothing: antialiased; }
  a { color: var(--green); text-underline-offset: 2px; }
  a:focus-visible, summary:focus-visible, button:focus-visible { outline: 3px solid var(--gold); outline-offset: 3px; border-radius: 6px; }
  .skip { position: absolute; left: -9999px; top: 0; background: var(--gold); color: #13231c; padding: 10px 14px; font-weight: 700; z-index: 10; }
  .skip:focus { left: 8px; top: 8px; }
  .wrap { max-width: 760px; margin: 0 auto; padding: 0 20px; }
  .ridge { display: block; width: 100%; height: 26px; color: var(--green); margin-top: 6px; }
  header.site { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 14px 0 18px; border-bottom: 4px solid var(--gold); }
  .logo { display: flex; align-items: center; gap: 10px; font: 800 22px/1 var(--display); text-transform: uppercase; letter-spacing: .01em; color: var(--green); text-decoration: none; }
  header.site nav { display: flex; flex-wrap: wrap; gap: 4px 16px; justify-content: flex-end; }
  header.site nav a { color: var(--ink2); text-decoration: none; font-size: 15px; }
  header.site nav a:hover { color: var(--green); text-decoration: underline; }
  h1, h2 { font-family: var(--display); font-weight: 800; color: var(--green); letter-spacing: -.005em; }
  h1 { font-size: clamp(36px, 7.5vw, 56px); line-height: 1.02; margin: 0 0 16px; text-transform: uppercase; text-wrap: balance; }
  h1 .kicker { display: block; font: 700 15px/1.4 -apple-system, system-ui, sans-serif; letter-spacing: .06em; color: var(--muted); margin-bottom: 12px; }
  h2 { font-size: 32px; line-height: 1.1; margin: 0 0 10px; text-wrap: balance; }
  h3 { font-size: 18px; margin: 0; line-height: 1.3; }
  .lede { font-size: 19px; color: var(--ink2); margin: 0 0 26px; }
  .hero { padding: 44px 0 28px; }
  section { padding: 36px 0; border-top: 1px solid var(--rule); }
  section.hero { border: 0; }
  .sub { color: var(--ink2); margin: 0 0 22px; }
  .cta-row { display: flex; gap: 12px; flex-wrap: wrap; align-items: center; }
  .btn { display: inline-flex; align-items: center; gap: 10px; background: var(--gold); color: #13231c; font-weight: 700; padding: 14px 20px; border-radius: 14px; text-decoration: none; font-size: 17px; }
  .btn svg { width: 22px; height: 22px; }
  .btn-ghost { background: transparent; color: var(--green); border: 2px solid var(--green); }
  .pill { font-size: 14px; color: var(--muted); }
  .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin: 28px 0 0; padding: 0; list-style: none; }
  .stats li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px; }
  .stats b { display: block; font: 800 30px/1 var(--display); color: var(--green); font-variant-numeric: tabular-nums; }
  .stats span { font-size: 14px; color: var(--muted); }
  .steps { display: grid; gap: 12px; list-style: none; margin: 0; padding: 0; }
  .step { display: flex; gap: 14px; background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .step .n { flex: 0 0 32px; height: 32px; border-radius: 50%; background: var(--gold); color: #13231c; font-weight: 800; display: grid; place-items: center; }
  .step p { margin: 4px 0 0; color: var(--ink2); }
  .shots { display: flex; gap: 14px; overflow-x: auto; margin: 0 -20px; padding: 4px 20px 14px; scroll-snap-type: x proximity; list-style: none; }
  .shots li { flex: 0 0 auto; width: 210px; scroll-snap-align: start; }
  .shots img { display: block; width: 210px; height: auto; border-radius: 24px; border: 1px solid var(--rule); background: var(--surface2); }
  .shots p { font-size: 14px; color: var(--muted); margin: 8px 2px 0; }
  .grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
  .card { background: var(--surface); border: 1px solid var(--rule); border-radius: var(--radius); padding: 18px; }
  .card p { margin: 6px 0 0; color: var(--ink2); }
  a.card { display: block; text-decoration: none; color: var(--ink); }
  a.card:hover h3 { text-decoration: underline; color: var(--green); }
  .card.lead { border-color: var(--gold); background: var(--goldsoft); }
  @media (prefers-color-scheme: dark) { .card.lead { background: var(--surface); } }
  .cities { display: flex; flex-wrap: wrap; gap: 8px; list-style: none; padding: 0; margin: 0; }
  .cities a { display: inline-block; padding: 8px 12px; border-radius: 999px; border: 1px solid var(--rule); background: var(--surface); text-decoration: none; color: var(--ink); font-size: 15px; }
  .cities a:hover { border-color: var(--green); }
  details { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 2px 18px; margin-bottom: 10px; }
  summary { cursor: pointer; padding: 14px 0; font-weight: 600; list-style: none; display: flex; justify-content: space-between; gap: 12px; }
  summary::-webkit-details-marker { display: none; }
  summary::after { content: "+"; color: var(--green); font-weight: 800; }
  details[open] summary::after { content: "\\2013"; }
  details p { margin: 0 0 16px; color: var(--ink2); }
  .final { text-align: center; }
  .final .cta-row { justify-content: center; }
  nav.crumbs { font-size: 14px; color: var(--muted); padding: 16px 0 0; }
  nav.crumbs ol { list-style: none; padding: 0; margin: 0; display: flex; flex-wrap: wrap; gap: 6px; }
  nav.crumbs li + li::before { content: "/"; margin-right: 6px; color: var(--rule); }
  nav.crumbs a { color: var(--muted); }
  .places { list-style: none; padding: 0; margin: 0; display: grid; gap: 10px; }
  .places li { background: var(--surface); border: 1px solid var(--rule); border-radius: 14px; padding: 14px 16px; min-width: 0; overflow-wrap: anywhere; }
  .places .where { margin: 2px 0 0; font-size: 15px; color: var(--muted); }
  .places .facts { margin: 8px 0 0; font-size: 15px; color: var(--ink2); }
  .places .facts b { color: var(--ink); font-weight: 600; }
  .places .note { margin: 6px 0 0; font-size: 15px; color: var(--ink2); }
  .places .link { font-size: 14px; }
  .tag { display: inline-block; font-size: 12px; font-weight: 700; letter-spacing: .05em; text-transform: uppercase; background: var(--goldsoft); color: #13231c; border-radius: 6px; padding: 1px 6px; margin-right: 4px; }
  .tag-sound { background: var(--soundsoft); color: var(--sound); }
  .tag-kc { color: #fff; } .kc-4 { background: #12733a; } .kc-3 { background: #4b7a1b; } .kc-2 { background: #f2b01e; color: #2b1d00; } .kc-1 { background: #c1302f; }
  .toc { columns: 2; padding-left: 20px; margin: 0; }
  table { border-collapse: collapse; width: 100%; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--rule); }
  td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
  .fine { font-size: 14px; color: var(--muted); }
  .sources { font-size: 15px; color: var(--ink2); padding-left: 20px; }
  .legal h2 { font-size: 26px; margin-top: 28px; }
  .legal p, .legal li { color: var(--ink2); }
  footer { padding: 32px 0 56px; color: var(--muted); font-size: 14px; border-top: 1px solid var(--rule); margin-top: 20px; }
  footer nav { display: flex; flex-wrap: wrap; gap: 8px 16px; }
  footer a { color: var(--muted); }
  footer p { margin: 12px 0 0; }
  @media (max-width: 600px) {
    .grid2 { grid-template-columns: 1fr; }
    .stats { grid-template-columns: 1fr 1fr; }
    .toc { columns: 1; }
    header.site { flex-direction: column; align-items: flex-start; }
    header.site nav { justify-content: flex-start; }
  }
"""
RIDGE = ('<svg class="ridge" viewBox="0 0 760 26" preserveAspectRatio="none" aria-hidden="true"><path d="M0 26 L0 20 L70 17 L130 19 L190 13 L240 15 '
         'L300 10 L340 12 L382 4 L398 1 L414 3 L450 9 L490 8 L550 14 L610 12 L670 16 L720 14 L760 18 L760 26 Z" fill="currentColor"/>'
         '<path d="M382 4 L398 1 L414 3 L404 7 L398 5 L390 8 Z" fill="#fff" opacity=".9"/></svg>')


def jsonld(obj):
    big = obj.get("@type") == "ItemList"
    return ('<script type="application/ld+json">\n' + json.dumps(obj, ensure_ascii=False, indent=None if big else 1, separators=(",", ":") if big else None)
            + "\n</script>")


def crumbs(trail):
    """trail: [(name, url)] ending with the current page."""
    items = "".join(f'<li><a href="{u}">{e(n)}</a></li>' if i < len(trail) - 1 else f'<li aria-current="page">{e(n)}</li>'
                    for i, (n, u) in enumerate(trail))
    ld = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": DOMAIN + u} for i, (n, u) in enumerate(trail)]}
    return f'<nav class="crumbs" aria-label="Breadcrumb"><ol>{items}</ol></nav>', ld


def store_button(label="Get early access"):
    return (f'<a class="btn store-btn" href="mailto:{EMAIL}?subject=Washington%20Eats%20early%20access&amp;body=Send%20me%20the%20TestFlight%20link.">'
            f'{APPLE}<span class="store-label">{label}</span></a>')


def page(path, title, desc, body, lds=(), robots="index,follow,max-image-preview:large", og_alt=None, extra_css=""):
    assert 50 <= len(title) <= 60 or path == "404.html", (path, len(title), title)
    assert 140 <= len(desc) <= 160 or path == "404.html", (path, len(desc), desc)
    assert body.count("<h1") == 1, path
    url = DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))
    og_alt = og_alt or f"{BRAND}: {TAGLINE}. Washington State restaurants, with hand-checked teriyaki, phở, drive-ins and oysters."
    ld = "\n".join(jsonld(x) for x in lds)
    doc = f"""<!DOCTYPE html>
<html lang="en" data-base="{BASE}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{url}">
<meta name="robots" content="{robots}">
<meta name="theme-color" content="#1F4D3A">
<!-- Smart App Banner: once the App Store Connect record exists, replace APP_ID with the numeric Apple ID and uncomment.
<meta name="apple-itunes-app" content="app-id=APP_ID">
-->
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{url}">
<meta property="og:type" content="{'website' if path == 'index.html' else 'article'}">
<meta property="og:site_name" content="{BRAND}">
<meta property="og:locale" content="en_US">
<meta property="og:image" content="{DOMAIN}/og.png">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(og_alt)}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{e(title)}">
<meta name="twitter:description" content="{e(desc)}">
<meta name="twitter:image" content="{DOMAIN}/og.png">
<link rel="icon" type="image/svg+xml" href="{FAVICON}">
<link rel="icon" type="image/png" sizes="32x32" href="/favicon-32.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<style>{CSS}{extra_css}</style>
{ld}
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<div class="wrap">
  {RIDGE}
  <header class="site">
    <a class="logo" href="/" aria-label="{BRAND} home">{LOGO}{BRAND}</a>
    <nav aria-label="Main">
      <a href="/washington-teriyaki.html">Teriyaki</a>
      <a href="/washington-pho.html">Phở</a>
      <a href="/washington-drive-ins.html">Drive-ins</a>
      <a href="/washington-oysters-seafood.html">Oysters</a>
      <a href="/#cities">Cities</a>
      <a href="/explore/">Search</a>
    </nav>
  </header>
{body}
  <footer>
    <nav aria-label="Footer">
      <a href="/">{BRAND} app</a>
      <a href="/explore/">Search Washington restaurants</a>
      <a href="/washington-teriyaki.html">Seattle teriyaki guide</a>
      <a href="/washington-pho.html">Washington phở</a>
      <a href="/washington-drive-ins.html">Drive-in burgers</a>
      <a href="/washington-oysters-seafood.html">Oysters &amp; seafood</a>
      <a href="/privacy.html">Privacy policy</a>
      <a href="/terms.html">Terms of use</a>
      <a href="mailto:{EMAIL}">Email us</a>
    </nav>
    <p>Place data: hand-checked research by {BRAND} ({CHECKED}); Overture Maps Foundation (CDLA Permissive 2.0); © OpenStreetMap contributors (ODbL); Public Health – Seattle &amp; King County food establishment inspection data (public domain). Not affiliated with or endorsed by any restaurant, team, chain or government agency. James Beard Foundation and James Beard Award are trademarks of the James Beard Foundation. Places open and close, so check before you go.</p>
    <p>© 2026 {BRAND}.</p>
  </footer>
</div>
<script>
  // Once the App Store listing exists, paste its URL here (looks like https://apps.apple.com/app/id123456789).
  // Every button switches from "Get early access" to "Download on the App Store" automatically.
  // Also fill in the apple-itunes-app meta tag in <head> on every page (re-run scripts/make-site.py after editing it there).
  var APP_STORE_URL = "";
  if (APP_STORE_URL) {{
    document.querySelectorAll(".store-btn").forEach(function (b) {{ b.href = APP_STORE_URL; b.rel = "noopener"; }});
    document.querySelectorAll(".store-label").forEach(function (l) {{ l.textContent = "Download on the App Store"; }});
    document.querySelectorAll(".store-note").forEach(function (n) {{ n.textContent = "Free for iPhone and iPad."; }});
  }}
</script>
</body>
</html>
"""
    if BASE:   # served under /washington-eats/: every root-relative link and asset gets the prefix
        doc = re.sub(r'(href|src|srcset)="/', rf'\1="{BASE}/', doc)
    os.makedirs(os.path.dirname(f"{DOCS}/{path}"), exist_ok=True)
    open(f"{DOCS}/{path}", "w").write(doc)
    return path


def place_item(p, show_town=True, extra=None):
    facts = []
    if p.dishes:
        facts.append(f"<b>Serves:</b> {e(p.dishes)}")
    if p.founded:
        facts.append(f"<b>Since</b> {p.founded}")
    elif p.brand_founded:
        facts.append(f"<b>Business founded</b> {p.brand_founded}")
    kinds = [(k, cls) for bit, k, cls in ((TERIYAKI, "Teriyaki", ""), (PHO, "Phở", " tag-sound"), (DRIVEIN, "Drive-in", " tag-sound"),
                                          (SEAFOOD, "Seafood", " tag-sound")) if p.checked & bit]
    if p.kasahara:
        kinds.insert(0, ("Toshi Kasahara's shop", ""))
    if p.kc.get("r"):
        kinds.append((f"King County: {KCR[p.kc['r']]}", f" tag-kc kc-{p.kc['r']}"))
    where = ", ".join(x for x in (p.addr, p.city) if x)
    if extra:
        where += f" · {extra}"
    out = [f"<li><h3>{e(p.name)}</h3>", f'<p class="where">{e(where)}</p>']
    if kinds or facts:
        out.append('<p class="facts">' + "".join(f'<span class="tag{cls}">{e(k)}</span>' for k, cls in kinds) + (" " + " · ".join(facts) if facts else "") + "</p>")
    if p.note:
        out.append(f'<p class="note">{e(p.note)}</p>')
    if p.site:
        host = re.sub(r"^https?://(www\.)?", "", p.site).split("/")[0]
        out.append(f'<p class="link"><a href="{e(p.site)}" rel="noopener nofollow">{e(host)}</a></p>')
    out.append("</li>")
    return "".join(out)


def restaurant_ld(p):
    x = {"@type": "Restaurant", "name": p.name,
         "address": {"@type": "PostalAddress", "streetAddress": p.addr, "addressLocality": p.city, "addressRegion": "WA", "addressCountry": "US"}}
    if p.zip:
        x["address"]["postalCode"] = p.zip
    if p.site:
        x["url"] = p.site
    if p.founded:
        x["foundingDate"] = str(p.founded)
    if p.cuisine and p.cuisine not in ("American & Other",):
        x["servesCuisine"] = p.cuisine
    return x


def item_list(name, places, url):
    return {"@context": "https://schema.org", "@type": "ItemList", "name": name, "url": url, "numberOfItems": len(places),
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "item": restaurant_ld(p)} for i, p in enumerate(places)]}


def article_ld(url, headline, desc):
    return {"@context": "https://schema.org", "@type": "Article", "headline": headline, "description": desc,
            "datePublished": TODAY, "dateModified": TODAY, "inLanguage": "en", "mainEntityOfPage": url,
            "image": f"{DOMAIN}/og.png", "author": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/"},
            "publisher": {"@type": "Organization", "name": BRAND, "url": DOMAIN + "/", "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png"}}}


def fit(options, lo, hi):
    for o in options:
        if lo <= len(o) <= hi:
            return o
    raise ValueError(f"nothing fits {lo}-{hi}: {[(len(o), o) for o in options]}")


N_REST = len(REST)
N_TOWNS = len({p.city for p in REST if p.city})


def by_region(places):
    groups = defaultdict(list)
    for p in places:
        groups[p.region or "Elsewhere in Washington"].append(p)
    order = list(REGIONS) + ["Elsewhere in Washington"]
    return [(r, sorted(groups[r], key=P.key)) for r in order if groups.get(r)]


def region_sections(places, noun, plural=None):
    plural = plural or noun + "s"
    toc = '<ul class="toc">' + "".join(f'<li><a href="#{slug(r)}">{e(r)}</a> ({len(ps)})</li>' for r, ps in by_region(places)) + "</ul>"
    secs = []
    for r, ps in by_region(places):
        secs.append(f'<section id="{slug(r)}" aria-labelledby="h-{slug(r)}"><h2 id="h-{slug(r)}">{e(r)}</h2>'
                    f'<p class="sub">{len(ps)} {noun if len(ps) == 1 else plural}, by town.</p><ol class="places">'
                    + "".join(place_item(p) for p in ps) + "</ol></section>")
    return toc, "\n".join(secs)


CITY_PAGES = ["Seattle", "Spokane", "Tacoma", "Vancouver", "Bellevue", "Everett", "Kent", "Renton", "Federal Way", "Kirkland",
              "Olympia", "Bellingham", "Yakima", "Kennewick", "Walla Walla", "Wenatchee"]


def city_url(c):
    return f"/cities/{slug(c)}.html"


def city_links(skip=None):
    return '<ul class="cities">' + "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES if c != skip) + "</ul>"


def guide_cta():
    return f'<div class="cta-row">{store_button()}<span class="pill store-note">Free for iPhone and iPad. Coming to the App Store.</span></div>'


written = []
region_counts = lambda ps: ", ".join(f"{r} ({len(x)})" for r, x in by_region(ps))

# ---------------------------------------------------------------- the headline guide: Seattle-style teriyaki
url = f"{DOMAIN}/washington-teriyaki.html"
src = {s["url"]: s for c in HIST["claims"] for s in c["sources"]}
SW = "https://www.seattleweekly.com/food/how-teriyaki-became-seattles-own-fast-food-phenomenon/"
SM = "https://www.seattlemet.com/eat-and-drink/2008/12/1108-feat-restchange"
TG = "https://www.toshisgrill.com/story"
for u in (SW, SM, TG):
    assert u in src, u   # every history source the page cites is in the research file (robots-allowed hosts only)
outside_king = sum(1 for p in TERI if p.county != "King")
teri_dish = Counter()
for p in TERI:
    for d in {x.strip().lower() for x in p.dishes.split(",") if x.strip()}:
        teri_dish[re.sub(r"\s+(plate|bowl)s?$", "", d)] += 1
spicy = sum(1 for p in TERI if "spicy" in p.dishes.lower())
gyoza = sum(1 for p in TERI if "gyoza" in p.dishes.lower())
katsu = sum(1 for p in TERI if "katsu" in p.dishes.lower())
kasa = next((p for p in TERI if p.kasahara), None)
assert kasa is not None and kasa.city == "Mill Creek", "the Kasahara shop must be on the guide"
title = fit([f"Seattle Teriyaki Guide: {len(TERI)} Washington Shops | {BRAND}", f"Seattle-Style Teriyaki: {len(TERI)} Checked Shops | {BRAND}",
             f"Washington Teriyaki Guide: {len(TERI)} Checked Shops"], 50, 60)
desc = fit([f"{len(TERI)} Seattle-style teriyaki shops across Washington, each checked open in {CHECKED}, with what they serve, by region and town. Free, no ads.",
            f"{len(TERI)} Seattle-style teriyaki shops statewide, checked open in {CHECKED} with what they serve, plus the 1976 history. Free, no ratings, no ads."], 140, 160)
toc, secs = region_sections(TERI, "teriyaki shop")
nav, bc = crumbs([("Home", "/"), ("Seattle teriyaki guide", "/washington-teriyaki.html")])
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} guide · checked {CHECKED}</span>Seattle-style teriyaki, statewide</h1>
    <p class="lede">{len(TERI)} teriyaki shops across Washington, {outside_king} of them outside King County, each confirmed open in {CHECKED} on its own website, menu or ordering page, or in dated local news, with what it serves.</p>
    {guide_cta()}
  </section>
  <section id="history">
    <h2>Where Seattle teriyaki comes from</h2>
    <p>Seattle-style teriyaki is credited to Toshihiro "Toshi" Kasahara, who opened Toshi's Teriyaki on Roy Street in Lower Queen Anne in March 1976: about 30 seats and a short menu of chicken and beef teriyaki, served with rice and a small cabbage salad (<a href="{SW}" rel="noopener">Seattle Weekly, 2007</a>; <a href="{SM}" rel="noopener">Seattle Met, 2008</a>). By his own estimate he went on to open about 30 Toshi's shops, which he sold or franchised over the years, and he left the business around 2003. Buyers and imitators kept the name, which is why so many unrelated shops are called Toshi's. Since 2013 he has run <a href="#{slug(kasa.region or '')}">Toshi's Teriyaki Grill in Mill Creek</a>, the one Toshi's that is his (<a href="{TG}" rel="noopener">its own site</a>).</p>
    <p>The plate that spread from there is grilled chicken, usually thigh meat, glazed with a sweet soy sauce and served with a scoop of white rice and a small salad. In 2007, Seattle Weekly counted more than 100 teriyaki shops inside Seattle city limits alone.</p>
    <h2>What the {len(TERI)} shops serve</h2>
    <p>Chicken teriyaki is on every menu here. {spicy} list a spicy chicken teriyaki, {katsu} a chicken katsu and {gyoza} gyoza. Many also serve beef or pork teriyaki, yakisoba, bento boxes and, at shops with a mixed menu, sushi or phở; each place's note says so.</p>
    <p>How the list was built: every shop was checked against a 2025 or 2026 source, such as its own menu page, a live online-ordering page it runs, or a dated local news story. A listing merely named "Teriyaki", with a dead website or no current source, stays in the app's directory but not on this guide. Places in King County also show Public Health – Seattle &amp; King County's official food safety rating, as published. Nothing here comes from review sites, and the order is by region and town, not by anyone's rating.</p>
    <p>In the {BRAND} app, the same list sorts by distance from you, and each shop opens Apple Maps' own card for live hours and photos. For noodle soup instead, see the <a href="/washington-pho.html">Washington phở guide</a>.</p>
    <h2>Jump to a region</h2>
    {toc}
    <p class="fine">City pages: {", ".join(f'<a href="{city_url(c)}">{e(c)}</a>' for c in CITY_PAGES)}.</p>
  </section>
{secs}
  </main>"""
written.append(page("washington-teriyaki.html", title, desc, body,
                    [article_ld(url, "Seattle-style teriyaki in Washington", desc), bc, item_list("Seattle-style teriyaki shops in Washington", sorted(TERI, key=P.key), url)]))

# ---------------------------------------------------------------- phở
url = f"{DOMAIN}/washington-pho.html"
title = fit([f"Washington Phở Guide: {len(PHOS)} Checked Pho Shops | {BRAND}", f"Washington Pho Guide: {len(PHOS)} Checked Shops | {BRAND}",
             f"Seattle & Washington Pho: {len(PHOS)} Checked Shops"], 50, 60)
desc = fit([f"{len(PHOS)} phở shops in Washington, from Seattle's Little Saigon to Spokane, each checked open in {CHECKED}, with the bowls they serve. Free, no ads.",
            f"{len(PHOS)} Washington phở shops, from Little Saigon to Spokane, checked open in {CHECKED} and listed by region and town with what they serve."], 140, 160)
toc, secs = region_sections(PHOS, "phở shop")
nav, bc = crumbs([("Home", "/"), ("Washington phở", "/washington-pho.html")])
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} guide · checked {CHECKED}</span>Washington phở guide</h1>
    <p class="lede">{len(PHOS)} restaurants whose menus center on phở, the Vietnamese beef or chicken noodle soup, each confirmed open in {CHECKED} on its own site, menu or ordering page, or in dated local news.</p>
    {guide_cta()}
  </section>
  <section id="about-pho">
    <h2>About this list</h2>
    <p>Seattle's Little Saigon, around South Jackson Street and 12th Avenue South, and the Chinatown-International District have the state's densest run of phở shops, and they spread from there to Tacoma, Everett, Olympia, Vancouver and Spokane. Most serve a numbered menu of phở bowls (rare steak, brisket, tendon, tripe and meatballs, or chicken), plus bún, bánh mì and cơm tấm.</p>
    <p>How the list was built: every place was checked against a 2025 or 2026 source, such as its own menu or a dated news story. A teriyaki shop with one phở item doesn't count; places with a mixed menu say so. Places in King County also show King County's official food safety rating, as published. The order is by region and town, never by rating.</p>
    <p>In the {BRAND} app, the list sorts by distance and each place opens Apple Maps' own card with live hours. See also the <a href="/washington-teriyaki.html">Seattle teriyaki guide</a>.</p>
    <h2>Jump to a region</h2>
    {toc}
  </section>
{secs}
  </main>"""
written.append(page("washington-pho.html", title, desc, body,
                    [article_ld(url, "Washington phở guide", desc), bc, item_list("Phở shops in Washington", sorted(PHOS, key=P.key), url)]))

# ---------------------------------------------------------------- drive-ins
url = f"{DOMAIN}/washington-drive-ins.html"
chains = Counter(p.r.get("b") for p in DRIVE if p.r.get("b") is not None)
brand_names = D["brands"]
chain_line = ", ".join(f"{brand_names[b]} ({n})" for b, n in chains.most_common(6))
indep = sum(1 for p in DRIVE if p.r.get("b") is None and (p.r.get("ch") or 1) < 2)
title = fit([f"Washington Drive-In Burgers: {len(DRIVE)} Checked Stands | {BRAND}", f"Washington Drive-Ins: {len(DRIVE)} Burger Stands | {BRAND}",
             f"Washington Drive-In Burgers: {len(DRIVE)} Checked Places"], 50, 60)
desc = fit([f"{len(DRIVE)} drive-ins and burger stands in Washington, from Dick's in Seattle to Zip's in Spokane, each checked open in {CHECKED}. Free app, no ads.",
            f"{len(DRIVE)} Washington drive-ins and burger stands, from Dick's in Seattle to Zip's in the east, checked open in {CHECKED} and listed by town."], 140, 160)
toc, secs = region_sections(DRIVE, "drive-in")
nav, bc = crumbs([("Home", "/"), ("Washington drive-ins", "/washington-drive-ins.html")])
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} guide · checked {CHECKED}</span>Washington drive-in burgers</h1>
    <p class="lede">{len(DRIVE)} drive-ins, walk-up windows and burger stands across Washington, each confirmed open in {CHECKED} on its own site or the brand's own location list.</p>
    {guide_cta()}
  </section>
  <section id="about-drive-ins">
    <h2>Chains and independents</h2>
    <p>The state's regional drive-in brands are on the list location by location: {e(chain_line)}. Each brand's founding year comes from its own site. The other {indep} are independent stands, many in small towns, some seasonal; when a place says it closes for winter, its note says so.</p>
    <p>How the list was built: every location was checked against a 2025 or 2026 source, such as the brand's own location list or the stand's own menu. Places in King County also show King County's official food safety rating, as published. The order is by region and town, never by rating.</p>
    <h2>Jump to a region</h2>
    {toc}
  </section>
{secs}
  </main>"""
written.append(page("washington-drive-ins.html", title, desc, body,
                    [article_ld(url, "Washington drive-in burgers", desc), bc, item_list("Drive-ins and burger stands in Washington", sorted(DRIVE, key=P.key), url)]))

# ---------------------------------------------------------------- oysters & seafood
url = f"{DOMAIN}/washington-oysters-seafood.html"
sea_out = sum(1 for p in SEA if p.county != "King")
title = fit([f"Washington Oysters & Seafood: {len(SEA)} Checked Places | {BRAND}", f"Washington Oyster Bars & Seafood: {len(SEA)} Places",
             f"Oysters & Seafood in Washington: {len(SEA)} Checked Places"], 50, 60)
desc = fit([f"{len(SEA)} oyster bars, seafood houses, chowder and fish-and-chips counters in Washington, each checked open in {CHECKED}, by region and town. Free.",
            f"{len(SEA)} Washington oyster bars and seafood places, from Puget Sound to Willapa Bay, checked open in {CHECKED} and listed by region and town."], 140, 160)
toc, secs = region_sections(SEA, "place")
nav, bc = crumbs([("Home", "/"), ("Oysters & seafood", "/washington-oysters-seafood.html")])
body = f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} guide · checked {CHECKED}</span>Washington oysters &amp; seafood</h1>
    <p class="lede">{len(SEA)} oyster bars, shellfish farms with a counter, seafood houses, chowder and fish-and-chips spots, {sea_out} of them outside King County, each confirmed open in {CHECKED}.</p>
    {guide_cta()}
  </section>
  <section id="about-seafood">
    <h2>About this list</h2>
    <p>{len(OYSTER_BARS)} of the {len(SEA)} serve oysters, from Puget Sound, Hood Canal, Samish Bay and Willapa Bay growers. The rest are seafood houses, chowder counters and fish-and-chips stands. Chain locations are listed when the brand's own location list confirms them.</p>
    <p>How the list was built: every place was checked against a 2025 or 2026 source, such as its own menu or a dated news story. Seasonal places that have closed for the year stay in the app's directory but come off this list until they reopen. Places in King County also show King County's official food safety rating, as published.</p>
    <h2>Jump to a region</h2>
    {toc}
  </section>
{secs}
  </main>"""
written.append(page("washington-oysters-seafood.html", title, desc, body,
                    [article_ld(url, "Washington oysters and seafood", desc), bc, item_list("Oyster bars and seafood in Washington", sorted(SEA, key=P.key), url)]))

# ---------------------------------------------------------------- city pages
city_stats = {}
for c in CITY_PAGES:
    here = [p for p in REST if p.city == c and p.lat is not None]
    n_town = sum(1 for p in REST if p.city == c)
    assert here, c
    center = (sorted(p.lat for p in here)[len(here) // 2], sorted(p.lon for p in here)[len(here) // 2])

    def near(ps, radius):
        out = []
        for p in ps:
            if p.lat is None:
                continue
            d = miles(center, (p.lat, p.lon))
            if p.city == c or d <= radius:
                out.append((0 if p.city == c else 1, d, p))
        out.sort(key=lambda x: (x[0], x[1] if x[0] else 0, x[2].name.lower()))
        return [(d, p) for _, d, p in out]

    radius = 6 if c == "Seattle" else 12
    te, ph, dr, sf = near(TERI, radius), near(PHOS, radius), near(DRIVE, radius), near(SEA, radius)
    honored = sorted([p for p in here if p.ip is not None], key=lambda p: (-p.ip, p.name.lower()))
    oldest = sorted([p for p in here if p.founded], key=lambda p: (p.founded, p.name.lower()))[:10]
    cuis = Counter(p.cuisine for p in REST if p.city == c and p.cuisine and p.cuisine != "American & Other").most_common(10)
    rated = [p for p in REST if p.city == c and p.kc.get("r")]
    city_stats[c] = {"restaurants": n_town, "teriyaki_near": len(te), "pho_near": len(ph), "drivein_near": len(dr), "seafood_near": len(sf), "kc_rated": len(rated)}

    def items(lst):
        return "".join(place_item(p, extra=None if p.city == c else f"{d:.0f} mi from {c}") for d, p in lst)

    path = f"cities/{slug(c)}.html"
    url = DOMAIN + "/" + path
    title = fit([f"{c} Teriyaki, Phở & Restaurants | {BRAND}", f"{c} Teriyaki, Pho & Restaurant Guide | {BRAND}",
                 f"{c}, WA Teriyaki, Phở & Restaurants | {BRAND}", f"{c}, WA Teriyaki, Pho & Restaurant Guide",
                 f"{c}, Washington Teriyaki, Phở & Restaurants", f"{c}, Washington Teriyaki & Restaurant Guide",
                 f"{c} Teriyaki & Restaurants | {BRAND}"], 50, 60)
    desc = fit([f"Teriyaki shops, phở, drive-ins and oyster bars in and near {c}, WA, checked open in {CHECKED}, plus local honors and the oldest places in town.",
                f"Teriyaki, phở, drive-in burgers and seafood in and near {c}, Washington, checked open in {CHECKED}, with local honors and the oldest places.",
                f"Teriyaki shops, phở, drive-ins and seafood in and near {c}, Washington, checked open in {CHECKED}, plus local honors and the oldest restaurants.",
                f"Teriyaki, phở, drive-ins and oyster bars in and near {c}, WA, all checked open in {CHECKED}, plus local honors and the oldest restaurants in town."], 140, 160)
    nav, bc = crumbs([("Home", "/"), ("Cities", "/#cities"), (c, "/" + path)])
    kc_line = (f" {len(rated):,} places in {e(c)} also show King County's official food safety rating, as published, through {THROUGH}." if rated else "")
    parts = [f"""{nav}
  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND} · {e(c)}, Washington</span>{e(c)} teriyaki, phở &amp; restaurants</h1>
    <p class="lede">{len(te)} teriyaki shops, {len(ph)} phở shops, {len(dr)} drive-ins and {len(sf)} oyster bars and seafood places in and around {e(c)}, each checked open in {CHECKED}. The {BRAND} app has all {n_town:,} restaurants, cafés, espresso stands and bars in {e(c)} and sorts them by distance from you.{kc_line}</p>
    {guide_cta()}
  </section>"""]
    sec = lambda sid, h, sub, lst: f'<section id="{sid}"><h2>{h}</h2><p class="sub">{sub}</p><ol class="places">{items(lst)}</ol></section>'
    if te:
        parts.append(sec("teriyaki", f"Teriyaki in and near {e(c)}", f"Shops in {e(c)} first, then others within {radius} miles, closest first. <a href=\"/washington-teriyaki.html\">All {len(TERI)} Washington teriyaki shops</a>.", te))
    if ph:
        parts.append(sec("pho", f"Phở in and near {e(c)}", f"Within {radius} miles. <a href=\"/washington-pho.html\">All {len(PHOS)} Washington phở shops</a>.", ph))
    if dr:
        parts.append(sec("drive-ins", f"Drive-ins near {e(c)}", f"Within {radius} miles. <a href=\"/washington-drive-ins.html\">All {len(DRIVE)} Washington drive-ins</a>.", dr))
    if sf:
        parts.append(sec("seafood", f"Oysters and seafood near {e(c)}", f"Within {radius} miles. <a href=\"/washington-oysters-seafood.html\">All {len(SEA)} oyster bars and seafood places</a>.", sf))
    if honored:
        parts.append(f'<section id="honors"><h2>{e(c)} honors &amp; history</h2><p class="sub">James Beard finalists and semifinalists (never called winners unless they won) and long-running institutions, from the James Beard Foundation\'s own award records and other named sources.</p><ol class="places">'
                     + "".join(place_item(p) for p in honored) + "</ol></section>")
    if oldest:
        parts.append(f'<section id="oldest"><h2>Oldest restaurants in {e(c)}</h2><p class="sub">Opening years at the current address, checked against the restaurant\'s own history page or local news, oldest first.</p><ol class="places">'
                     + "".join(place_item(p) for p in oldest) + "</ol></section>")
    if cuis:
        rows = "".join(f'<tr><td>{e(k)}</td><td class="n">{n:,}</td></tr>' for k, n in cuis)
        parts.append(f'<section id="cuisines"><h2>What {e(c)} eats</h2><p class="sub">The most common kinds of restaurant among the {n_town:,} in {e(c)}, from open map data and King County\'s inspection records.</p><table><thead><tr><th scope="col">Kind of place</th><th scope="col" class="n">Places</th></tr></thead><tbody>{rows}</tbody></table></section>')
    parts.append(f'<section id="more"><h2>More Washington cities</h2>{city_links(skip=c)}</section>\n  </main>')
    seen, uniq = set(), []
    for _, p in te + ph + dr + sf:
        if id(p) not in seen:
            seen.add(id(p)); uniq.append(p)
    written.append(page(path, title, desc, "\n".join(parts),
                        [article_ld(url, f"{c} teriyaki, phở and restaurants", desc), bc, item_list(f"Teriyaki, phở, drive-ins and seafood near {c}", uniq, url)]))

# ---------------------------------------------------------------- web app (docs/explore/): data split + page
os.makedirs(f"{DOCS}/data", exist_ok=True)
CORE_KEYS = ["id", "n", "c", "co", "cu", "t", "s", "a", "z", "la", "lo", "b", "ch", "v", "g", "hc", "ip", "f", "h", "ks", "di"]
cols = {k: [] for k in CORE_KEYS + ["kr", "kd", "kq"]}
detail = []
for r in D["places"]:
    for k in CORE_KEYS:
        v = r.get(k)
        cols[k].append(round(v, 4) if k in ("la", "lo") and v is not None else v)
    kc = r.get("kc") or {}
    cols["kr"].append(kc.get("r")); cols["kd"].append(kc.get("d")); cols["kq"].append(kc.get("res"))
    d = {k: r[k] for k in ("ph", "w", "note", "icon", "hon", "jbf", "src", "bf") if r.get(k)}
    if kc: d["kc"] = kc
    detail.append(d or None)
core = {"generated": D["generated"], "records_through": THROUGH, "cities": CITIES, "cuisines": CUISINES, "counties": COUNTIES, "brands": D["brands"],
        "sources": D["sources"], "calibration": D.get("calibration", {}), "cols": cols}
json.dump(core, open(f"{DOCS}/data/core.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(detail, open(f"{DOCS}/data/detail.json", "w"), separators=(",", ":"), ensure_ascii=False)
json.dump(json.load(open(f"{ROOT}/data/wa/wa_shapes.json")), open(f"{DOCS}/data/wa_shapes.json", "w"), separators=(",", ":"))

EXPLORE_CSS = """
  [hidden] { display: none !important; }
  .ex-hero { padding: 28px 0 8px; }
  .ex-hero h1 { font-size: clamp(30px, 6vw, 44px); }
  .ex-controls { background: var(--bg); padding: 10px 0 8px; border-bottom: 1px solid var(--rule); }
  .ex-guides { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 8px; scrollbar-width: none; }
  .ex-guides button, .ex-view button, .ex-small { flex: 0 0 auto; border: 1px solid var(--rule); background: var(--surface); color: var(--green); border-radius: 999px; padding: 7px 12px; font: 600 14px/1.2 inherit; font-family: inherit; cursor: pointer; }
  .ex-guides button[aria-pressed="true"], .ex-view button[aria-pressed="true"] { background: var(--green); color: var(--bg); border-color: var(--green); }
  .ex-row1 { display: flex; gap: 8px; align-items: center; }
  .ex-row1 input[type=search] { flex: 1; min-width: 0; font: 16px/1.3 inherit; font-family: inherit; padding: 10px 12px; border: 2px solid var(--green); border-radius: 12px; background: var(--surface); color: var(--ink); }
  .ex-row2 { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-top: 8px; font-size: 14px; }
  .ex-row2 select { font: 14px inherit; font-family: inherit; padding: 6px 8px; border: 1px solid var(--rule); border-radius: 8px; background: var(--surface); color: var(--ink); max-width: 46vw; }
  .ex-view { margin-left: auto; display: flex; gap: 4px; }
  #ex-count { margin: 8px 0 0; font-size: 14px; color: var(--muted); }
  #ex-sub { margin: 4px 0 0; font-size: 14px; color: var(--ink2); }
  #ex-locmsg { font-size: 13px; color: var(--muted); margin: 4px 0 0; }
  .ex-list { list-style: none; padding: 0; margin: 10px 0; }
  .ex-list li + li { border-top: 1px solid var(--rule); }
  .ex-row { width: 100%; display: flex; gap: 12px; align-items: center; text-align: left; background: none; border: 0; padding: 12px 4px; cursor: pointer; color: var(--ink); font: inherit; }
  .ex-row:hover { background: var(--surface2); }
  .ex-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
  .ex-main b { font-weight: 650; }
  .ex-town { font-size: 14px; color: var(--muted); }
  .ex-chips .tag { margin: 0 4px 2px 0; }
  .tag-jb { background: var(--green); color: var(--bg); }
  .tag-plain { background: var(--surface2); color: var(--green); }
  .tag-dash { background: transparent; color: var(--muted); border: 1px dashed var(--rule); }
  .ex-metric { text-align: right; display: flex; flex-direction: column; align-items: flex-end; }
  .ex-metric b { font: 800 22px/1 var(--display); color: var(--green); }
  .ex-metric small { font-size: 11px; color: var(--muted); }
  .ex-kc { display: inline-block; padding: 2px 8px; border-radius: 999px; font-weight: 700; font-size: 13px; color: #fff; white-space: nowrap; }
  .ex-kc-4 { background: #12733a; } .ex-kc-3 { background: #4b7a1b; } .ex-kc-2 { background: #f2b01e; color: #2b1d00; } .ex-kc-1 { background: #c1302f; }
  .ex-rank { flex: 0 0 34px; height: 34px; display: grid; place-items: center; font: 800 20px var(--display); color: var(--green); border-radius: 8px; }
  .ex-rank.top { background: var(--gold); color: #13231c; }
  .ex-empty { padding: 24px 4px; color: var(--muted); }
  #ex-more { display: block; margin: 8px auto 24px; }
  #ex-mapwrap { position: relative; height: min(72vh, 620px); margin: 10px 0 20px; border: 1px solid var(--rule); border-radius: 16px; overflow: hidden; background: #cfe3ea; }
  @media (prefers-color-scheme: dark) { #ex-mapwrap { background: #16303a; } }
  #ex-map { width: 100%; height: 100%; display: block; touch-action: none; cursor: grab; }
  .ex-zoom { position: absolute; right: 10px; top: 10px; display: flex; flex-direction: column; gap: 6px; }
  .ex-zoom button { width: 38px; height: 38px; border-radius: 10px; border: 1px solid var(--rule); background: var(--surface); color: var(--green); font: 700 20px/1 inherit; cursor: pointer; }
  #ex-maphint { position: absolute; left: 10px; bottom: 8px; margin: 0; font-size: 13px; background: var(--surface); padding: 3px 8px; border-radius: 999px; color: var(--ink2); }
  .ex-panel { position: fixed; z-index: 20; right: 0; top: 0; bottom: 0; width: min(440px, 100%); overflow-y: auto; background: var(--surface); border-left: 1px solid var(--rule); box-shadow: -8px 0 24px rgba(0,0,0,.12); padding: 18px 20px 40px; }
  @media (max-width: 600px) { .ex-panel { top: auto; height: 86vh; border-left: 0; border-top: 4px solid var(--gold); border-radius: 18px 18px 0 0; } }
  .ex-close { position: sticky; top: 0; float: right; width: 38px; height: 38px; border-radius: 50%; border: 1px solid var(--rule); background: var(--surface); font-size: 24px; line-height: 1; cursor: pointer; color: var(--ink); }
  .ex-kicker { margin: 0; font-size: 12px; font-weight: 700; letter-spacing: .1em; color: var(--sound); }
  .ex-panel h2 { font-size: 34px; margin: 4px 0 6px; text-transform: uppercase; }
  .ex-addr, .ex-dist { margin: 0 0 4px; color: var(--ink2); font-size: 15px; }
  .ex-actions { margin: 14px 0 8px; display: grid; gap: 8px; }
  .ex-apple { justify-content: center; }
  .ex-act-row { display: flex; gap: 8px; flex-wrap: wrap; }
  .ex-act-row a, .ex-act-row button { flex: 1; min-width: 88px; text-align: center; padding: 10px; border: 1px solid var(--rule); border-radius: 12px; text-decoration: none; color: var(--green); font: 600 14px inherit; font-family: inherit; background: var(--surface); cursor: pointer; }
  .ex-act-row button[aria-pressed="true"] { background: var(--goldsoft); color: #13231c; }
  .ex-sec { margin-top: 18px; }
  .ex-sec h3 { font-size: 12px; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); border-bottom: 1px solid var(--rule); padding-bottom: 6px; margin-bottom: 8px; }
  .ex-sec p, .ex-sec li { font-size: 15px; color: var(--ink2); margin: 6px 0; }
  .ex-kv { display: flex; justify-content: space-between; gap: 12px; font-size: 15px; padding: 3px 0; }
  .ex-kv span { color: var(--ink2); }
  .ex-kv b { text-align: right; }
  .ex-fine { font-size: 13px !important; color: var(--muted) !important; }
  .ex-grade { display: flex; align-items: center; gap: 10px; font-weight: 600; flex-wrap: wrap; }
  .ex-app { margin-top: 22px; font-size: 14px; color: var(--muted); }
  body.ex-open { overflow: hidden; }
  @media (min-width: 601px) { body.ex-open { overflow: auto; } }
"""
url = f"{DOMAIN}/explore/"
title = fit(["Search Washington Restaurants, Teriyaki & Phở | Washington Eats", "Search Washington Restaurants, Teriyaki & Pho Shops",
             "Washington Restaurant Search & Map | Washington Eats"], 50, 60)
desc = fit([f"Search all {N_REST:,} Washington State restaurants by name, town, street or dish, and map {len(TERI)} hand-checked teriyaki shops and {len(PHOS)} phở shops. Free.",
            f"Search all {N_REST:,} Washington restaurants by name, town, street or dish, and map {len(TERI)} hand-checked teriyaki shops, {len(PHOS)} phở shops and more.",
            f"Search {N_REST:,} Washington restaurants by name, town, street or dish, and map {len(TERI)} hand-checked teriyaki shops and {len(PHOS)} phở shops."], 140, 160)
nav, bc = crumbs([("Home", "/"), ("Search", "/explore/")])
guide_buttons = "".join(f'<button type="button" data-g="{k}" aria-pressed="false">{e(t)}</button>' for k, t in
                        (("teriyaki", "Teriyaki"), ("pho", "Phở"), ("drivein", "Drive-ins"), ("seafood", "Oysters & seafood"), ("honors", "Honors"),
                         ("oldest", "Oldest"), ("safety", "Food safety"), ("all", "All restaurants"), ("saved", "Saved")))
body = f"""{nav}
  <main id="main">
  <section class="ex-hero">
    <h1><span class="kicker">{BRAND} · on the web</span>Search Washington restaurants</h1>
    <p class="sub">{N_REST:,} restaurants, cafés, espresso stands and bars, with {len(TERI)} hand-checked teriyaki shops, {len(PHOS)} phở shops, {len(DRIVE)} drive-ins and {len(SEA)} oyster bars and seafood places. The same data as the free iPhone and iPad app. Nothing about you is stored anywhere but this browser.</p>
  </section>
  <p id="ex-loading">Loading the restaurant list…</p>
  <noscript><p>The search needs JavaScript. The guides work without it: <a href="/washington-teriyaki.html">teriyaki</a>, <a href="/washington-pho.html">phở</a>, <a href="/washington-drive-ins.html">drive-ins</a>, <a href="/washington-oysters-seafood.html">oysters &amp; seafood</a>.</p></noscript>
  <div id="ex-app" hidden>
    <div class="ex-controls">
      <div class="ex-guides" role="group" aria-label="Guides">{guide_buttons}</div>
      <div class="ex-row1">
        <label class="skip" for="ex-q">Search</label>
        <input id="ex-q" type="search" placeholder="Name, town, street, zip or dish" autocomplete="off" enterkeyhint="search">
        <button type="button" id="ex-locate" class="ex-small">Near me</button>
      </div>
      <div class="ex-row2">
        <label>Sort <select id="ex-sort" aria-label="Sort"></select></label>
        <select id="ex-town" aria-label="Town"></select>
        <select id="ex-cuisine" aria-label="Kind of place"></select>
        <label><input type="checkbox" id="ex-chains"> Hide chains</label>
        <button type="button" id="ex-clear" class="ex-small" hidden>Clear filters</button>
        <div class="ex-view" role="group" aria-label="View"><button type="button" data-v="list" aria-pressed="true">List</button><button type="button" data-v="map" aria-pressed="false">Map</button></div>
      </div>
      <p id="ex-sub"></p>
      <p id="ex-count" aria-live="polite"></p>
      <p id="ex-locmsg"></p>
    </div>
    <div id="ex-listwrap"><ol id="ex-list" class="ex-list"></ol><button type="button" id="ex-more" class="ex-small" hidden></button></div>
    <div id="ex-mapwrap" hidden>
      <canvas id="ex-map" aria-label="Map of Washington with a dot for each place in the list. The list view has the same places."></canvas>
      <div class="ex-zoom"><button type="button" id="ex-zin" aria-label="Zoom in">+</button><button type="button" id="ex-zout" aria-label="Zoom out">−</button></div>
      <p id="ex-maphint"></p>
    </div>
  </div>
  <aside id="ex-panel" class="ex-panel" hidden aria-labelledby="ex-pname"></aside>
  </main>
<script>
{open(f"{ROOT}/scripts/explore.js").read()}
</script>"""
webapp_ld = {"@context": "https://schema.org", "@type": "WebApplication", "name": f"{BRAND} web app", "url": url,
             "applicationCategory": "TravelApplication", "operatingSystem": "Any", "browserRequirements": "Requires JavaScript",
             "description": desc, "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}, "publisher": {"@id": f"{DOMAIN}/#org"}}
written.append(page("explore/index.html", title, desc, body, [webapp_ld, bc], extra_css=EXPLORE_CSS))

# ---------------------------------------------------------------- landing page
shots = [("home", "Washington Eats home screen: the Seattle Teriyaki guide, then Phở, Drive-In Burgers, Oysters & Seafood, Honors & History, Oldest Places and Food Safety, with a search box for every restaurant in the state.", "Guides for teriyaki, phở, drive-ins and oysters."),
         ("teriyaki", "Seattle Teriyaki list in Washington Eats, sorted by distance from downtown Seattle, with what each shop serves.", "Teriyaki shops nearest you first."),
         ("detail", "Toshio's Teriyaki in Seattle in Washington Eats: address, a button for ratings, hours and photos in Apple Maps, what it serves and King County's official food safety rating.", "Each place, with live Apple Maps hours and photos."),
         ("map", "Washington Eats map with pins for hand-checked teriyaki shops.", "The map, by teriyaki, phở, drive-ins or seafood."),
         ("safety", "Food Safety list in Washington Eats: King County's official ratings, best first.", "King County's official food safety ratings.")]
shot_html = []
for i, (name, alt, cap) in enumerate(shots):
    png = f"{DOCS}/img/screen-{name}.png"
    if not os.path.exists(png):
        continue
    w, h = png_size(png)
    lazy = ' loading="lazy"' if i > 1 else ""
    webp = f'<source srcset="/img/screen-{name}.webp" type="image/webp">' if os.path.exists(f"{DOCS}/img/screen-{name}.webp") else ""
    shot_html.append(f'<li><picture>{webp}<img src="/img/screen-{name}.png" alt="{e(alt)}" width="{w}" height="{h}"{lazy} decoding="async"></picture><p>{e(cap)}</p></li>')
shots_section = f"""
  <section id="screens">
    <h2>What it looks like</h2>
    <ul class="shots" tabindex="0" aria-label="Washington Eats app screenshots">
      {"".join(shot_html)}
    </ul>
  </section>
""" if shot_html else ""

faq = [
    ("Is Washington Eats free?", "Yes. The app is free, with no ads, no in-app purchases and no account."),
    ("Where do the teriyaki shops and other guides come from?", f"We checked each one by hand in {CHECKED}: every place on the teriyaki, phở, drive-in and oysters and seafood lists has a 2025 or 2026 source such as its own menu page, a live online-ordering page it runs or a dated news story. The rest of the {N_REST:,} restaurants come from Overture Maps' open place data and King County's food establishment inspection records."),
    ("Is this the Washington in D.C.?", "No. Washington Eats covers Washington State only: Seattle, Spokane, Tacoma, Vancouver, the Tri-Cities, Yakima, Bellingham, Olympia and everywhere in between."),
    ("Does the app show ratings and reviews?", "Not its own. Tap a place and Apple Maps' own place card opens inside the app with Apple's current ratings, hours, photos and directions. Our lists are never ordered by ratings."),
    ("What are the food safety ratings?", f"For King County (Seattle and its suburbs), the app shows Public Health – Seattle & King County's official rating, as published: Excellent, Good, Okay or Needs to Improve, from inspections through {THROUGH}. We never compute our own. Other counties don't publish ratings in bulk."),
    ("Does it need my location?", "Only if you want lists sorted by distance. Your location stays on your iPhone or iPad and is never sent to us. Everything else works without it."),
    ("A place closed or is missing. How do I tell you?", f"Email {EMAIL} with the name and town. Corrections go into the next update."),
    ("Is there an Android version?", f"Not yet. Washington Eats is for iPhone and iPad. If enough people ask at {EMAIL}, it moves up the list."),
]
faq_html = "".join(f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>" for q, a in faq)
faq_ld = {"@context": "https://schema.org", "@type": "FAQPage", "@id": f"{DOMAIN}/#faq",
          "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
app_ld = {"@context": "https://schema.org", "@graph": [
    {"@type": "MobileApplication", "@id": f"{DOMAIN}/#app", "name": "Washington Eats: Restaurants",
     "alternateName": ["Washington Eats", "WA Eats", "Washington Eats: WA State Teriyaki & Food Guide"],
     "description": f"A free guide to {N_REST:,} Washington State restaurants, with hand-checked lists of {len(TERI)} teriyaki shops, {len(PHOS)} phở shops, {len(DRIVE)} drive-ins and {len(SEA)} oyster bars and seafood places. Sort by distance, open Apple Maps' live place card for hours and photos, and save places.",
     "url": f"{DOMAIN}/", "image": f"{DOMAIN}/og.png", "operatingSystem": "iOS, iPadOS", "applicationCategory": "TravelApplication",
     "applicationSubCategory": "Food & Drink", "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"},
     "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD", "category": "free"}},
    {"@type": "Organization", "@id": f"{DOMAIN}/#org", "name": BRAND, "url": f"{DOMAIN}/",
     "logo": {"@type": "ImageObject", "url": f"{DOMAIN}/icon-512.png", "width": 512, "height": 512}, "email": EMAIL,
     "contactPoint": {"@type": "ContactPoint", "contactType": "customer support", "email": EMAIL, "availableLanguage": "en"}},
    {"@type": "WebSite", "@id": f"{DOMAIN}/#website", "name": BRAND, "alternateName": ["WA Eats", "Washington Eats app"], "url": f"{DOMAIN}/",
     "inLanguage": "en", "publisher": {"@id": f"{DOMAIN}/#org"}}]}
if shot_html:
    app_ld["@graph"][0]["screenshot"] = f"{DOMAIN}/img/screen-home.png"
title = "Washington Eats: Teriyaki, Phở & Restaurant App for WA"
desc = fit([f"Free iPhone and iPad guide to {N_REST:,} Washington State restaurants, with {len(TERI)} hand-checked teriyaki shops, {len(PHOS)} phở shops, {len(DRIVE)} drive-ins and oyster bars.",
            f"Free iPhone and iPad guide to {N_REST:,} Washington State restaurants, with {len(TERI)} hand-checked teriyaki shops, {len(PHOS)} phở shops and {len(DRIVE)} drive-in burgers.",
            f"Free iPhone and iPad guide to {N_REST:,} Washington State restaurants, with {len(TERI)} hand-checked teriyaki shops, phở shops and drive-ins."], 140, 160)
city_cards = "".join(f'<li><a href="{city_url(c)}">{e(c)}</a></li>' for c in CITY_PAGES)
body = f"""  <main id="main">
  <section class="hero">
    <h1><span class="kicker">{BRAND}: the {TAGLINE.lower().replace("washington", "Washington")} for iPhone and iPad</span>Washington's restaurants, and the teriyaki Seattle made its own</h1>
    <p class="lede">{BRAND} is a free Washington State restaurant guide. Find a teriyaki shop near you, a bowl of phở, a drive-in burger or an oyster bar, from lists we checked by hand, plus {N_REST:,} restaurants, cafés, espresso stands and bars in {N_TOWNS:,} towns.</p>
    <div class="cta-row">{store_button()}<a class="btn btn-ghost" href="/explore/">Search on the web</a><span class="pill store-note">Free. No ads, no account. Coming to the App Store.</span></div>
    <ul class="stats" aria-label="What's in the app">
      <li><b>{len(TERI)}</b><span>teriyaki shops</span></li>
      <li><b>{len(PHOS)}</b><span>phở shops</span></li>
      <li><b>{len(DRIVE)}</b><span>drive-ins</span></li>
      <li><b>{N_REST:,}</b><span>restaurants</span></li>
    </ul>
  </section>

  <section id="what">
    <h2>A Washington restaurant guide that starts with teriyaki</h2>
    <p class="sub">General restaurant apps rank by star ratings and can't tell a 1976-style teriyaki counter from a sushi bar with a teriyaki roll. {BRAND} starts from what people here look for: a chicken teriyaki plate, a bowl of phở, a Dick's or Zip's run, a dozen oysters, and the old places that have been open for generations. Every one of those was checked open in {CHECKED}. In King County, each place also shows Public Health – Seattle &amp; King County's official food safety rating. For ratings, hours and photos, each place opens Apple Maps' own live card.</p>
  </section>

  <section id="how">
    <h2>How it works</h2>
    <ol class="steps">
      <li class="step"><div class="n" aria-hidden="true">1</div><div><h3>Pick a guide.</h3><p>Seattle Teriyaki, Phở, Drive-In Burgers, Oysters &amp; Seafood, Honors &amp; History, Oldest Places, Food Safety, or search every restaurant by name, town, street or dish.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">2</div><div><h3>See what's near you.</h3><p>Sort by distance, filter by town or cuisine, or browse the map. Each teriyaki shop lists what it serves.</p></div></li>
      <li class="step"><div class="n" aria-hidden="true">3</div><div><h3>Go.</h3><p>Open Apple Maps' place card for live hours and photos, call, get directions, or save it for later.</p></div></li>
    </ol>
  </section>
{shots_section}
  <section id="guides">
    <h2>Washington food guides</h2>
    <p class="sub">The app's hand-checked lists, readable on the web.</p>
    <div class="grid2">
      <a class="card lead" href="/washington-teriyaki.html"><h3>Seattle-style teriyaki</h3><p>{len(TERI)} shops statewide, with what they serve and the 1976 history.</p></a>
      <a class="card" href="/washington-pho.html"><h3>Washington phở</h3><p>{len(PHOS)} phở shops, from Little Saigon to Spokane.</p></a>
      <a class="card" href="/washington-drive-ins.html"><h3>Drive-in burgers</h3><p>{len(DRIVE)} drive-ins and burger stands, Dick's to Zip's.</p></a>
      <a class="card" href="/washington-oysters-seafood.html"><h3>Oysters &amp; seafood</h3><p>{len(SEA)} oyster bars, chowder and fish-and-chips counters.</p></a>
    </div>
  </section>

  <section id="cities">
    <h2>Teriyaki, phở and restaurants by city</h2>
    <p class="sub">Teriyaki, phở, drive-ins, seafood, local honors and the oldest restaurants in Washington's biggest towns.</p>
    <ul class="cities">{city_cards}</ul>
  </section>

  <section id="pricing">
    <h2>Free, and staying that way</h2>
    <p class="sub">No ads, no subscription, no in-app purchases, no account. The whole guide is built into the app, so lists open instantly and work with a weak signal on the ferry or over the pass.</p>
  </section>

  <section id="privacy">
    <h2>Your lunch plans are your business</h2>
    <p class="sub">{BRAND} collects nothing. If you allow location, it only sorts lists by distance on your device. Saved places stay on your device. This website sets no cookies and runs no trackers. <a href="/privacy.html">Read the privacy policy</a>.</p>
  </section>

  <section id="faq">
    <h2>Questions</h2>
    {faq_html}
  </section>

  <section id="download" class="final">
    <h2>Find your teriyaki</h2>
    <p class="sub">{BRAND} is coming to the App Store for iPhone and iPad. Free.</p>
    <div class="cta-row">{store_button()}</div>
  </section>
  </main>"""
written.append(page("index.html", title, desc, body, [app_ld, faq_ld]))

# ---------------------------------------------------------------- privacy and terms
nav, bc = crumbs([("Home", "/"), ("Privacy policy", "/privacy.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Privacy policy</h1>
    <p class="lede">Short version: the {BRAND} app collects nothing about you, and this website doesn't track you. Last updated {TODAY}.</p>
  </section>
  <section>
    <h2>The app</h2>
    <ul>
      <li><b>No account, no analytics, no ads.</b> The app has no sign-in, no advertising and no analytics or crash-reporting code. We receive no data from it.</li>
      <li><b>Location.</b> If you allow it, your location is used on your device to sort places by distance and show where you are on the map. It is never sent to us. You can turn it off in Settings at any time.</li>
      <li><b>Saved places and filters</b> are stored only on your device and are deleted when you delete the app.</li>
      <li><b>Apple Maps.</b> When you open a place's ratings, hours and photos, or ask for directions, the app asks Apple Maps for that place. Apple handles that request under <a href="https://www.apple.com/legal/privacy/" rel="noopener">Apple's privacy policy</a>, as it does for any app that shows a map.</li>
      <li><b>Spotlight.</b> The app adds its hand-checked teriyaki shops, phở shops, drive-ins and seafood places to your device's search index so you can find them from Spotlight. That index stays on your device.</li>
      <li><b>Calls, websites and email</b> you start from a place open in the Phone app, your browser or Mail, and are handled by them.</li>
    </ul>
    <p>On the App Store, the app's privacy label is "Data Not Collected".</p>
    <h2>This website</h2>
    <p>The site is static pages hosted on GitHub Pages. It sets no cookies and loads no analytics, fonts or scripts from anyone else. The web app's saved places stay in your browser's local storage. GitHub may keep standard server logs, such as IP addresses, for security; see <a href="https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement" rel="noopener">GitHub's privacy statement</a>.</p>
    <h2>Email</h2>
    <p>If you email us, we use your message and address only to reply and to fix the listing you told us about. We don't add you to a mailing list or share your address.</p>
    <h2>Children</h2>
    <p>The app collects no personal information from anyone, including children.</p>
    <h2>Changes and contact</h2>
    <p>If this policy changes, the new version will be posted here with a new date. Questions: <a href="mailto:{EMAIL}">{EMAIL}</a>.</p>
  </section>
  </main>"""
written.append(page("privacy.html", "Privacy Policy: Washington Eats Teriyaki & Restaurant App",
                    fit(["The Washington Eats privacy policy: the app collects no data, keeps your location and saved places on your device, and this site sets no cookies."], 140, 160),
                    body, [bc]))

nav, bc = crumbs([("Home", "/"), ("Terms of use", "/terms.html")])
body = f"""{nav}
  <main id="main" class="legal">
  <section class="hero">
    <h1>Terms of use</h1>
    <p class="lede">The plain-language terms for the {BRAND} app and this website. Last updated {TODAY}.</p>
  </section>
  <section>
    <h2>What the app is</h2>
    <p>{BRAND} is a free guide to restaurants in Washington State. It is provided as is, for personal use, without charge and without warranties of any kind.</p>
    <h2>Check before you go</h2>
    <p>Restaurants open, close, change their hours and change their menus. What a place serves and when it opened are what the place or a named source said when we checked in {CHECKED}. We work to keep the lists right, but we can't promise that any listing is current or complete. Call the restaurant before you make the trip.</p>
    <h2>Food safety ratings</h2>
    <p>Ratings in the Food Safety guide are King County's own (Excellent, Good, Okay, Needs to Improve), shown as Public Health – Seattle &amp; King County publishes them in its public-domain inspection data, through {THROUGH}. We don't compute or change them. For the official record, see <a href="https://kingcounty.gov/en/dept/dph/health-safety/food-safety/search-restaurant-safety-ratings" rel="noopener">King County's restaurant safety ratings</a>. King County does not endorse this app.</p>
    <h2>Other people's content</h2>
    <p>Ratings, reviews, hours and photos in each place card come from Apple Maps and are Apple's and its providers', under Apple's terms. Restaurant names and trademarks belong to their owners. {BRAND} is not affiliated with any restaurant, team, chain or government agency.</p>
    <h2>Data sources and licenses</h2>
    <ul>
      <li>Overture Maps Foundation places data, under the Community Data License Agreement, Permissive 2.0; boundaries and water under the Open Database License. © OpenStreetMap contributors, Overture Maps Foundation.</li>
      <li>Public Health – Seattle &amp; King County: Food Establishment Inspection Data (data.kingcounty.gov), public domain.</li>
      <li>James Beard Foundation: finalist and semifinalist history.</li>
      <li>Teriyaki shops, phở shops, drive-ins, oysters and seafood, and opening years: our own research, with a source recorded for every place.</li>
    </ul>
    <h2>Corrections</h2>
    <p>If a listing is wrong, or you own a restaurant and want something fixed, email <a href="mailto:{EMAIL}">{EMAIL}</a>. We fix mistakes in the next update.</p>
    <h2>Liability</h2>
    <p>To the extent the law allows, we are not liable for any loss arising from use of the app or site, including a wasted drive to a closed restaurant. Washington law governs these terms.</p>
    <h2>Changes</h2>
    <p>We may update these terms; the current version and its date are always on this page. See also the <a href="/privacy.html">privacy policy</a>.</p>
  </section>
  </main>"""
written.append(page("terms.html", "Terms of Use: Washington Eats Teriyaki & Restaurant App",
                    fit(["The Washington Eats terms of use: a free Washington State restaurant guide, provided as is. Check before you go, and see where each listing comes from."], 140, 160),
                    body, [bc]))

body = f"""  <main id="main">
  <section class="hero">
    <h1>Page not found</h1>
    <p class="lede">That page isn't here. Try the <a href="/">{BRAND} home page</a>, the <a href="/washington-teriyaki.html">teriyaki guide</a> or the <a href="/explore/">restaurant search</a>.</p>
  </section>
  </main>"""
page("404.html", f"Page not found | {BRAND}", "This page doesn't exist.", body, robots="noindex,follow")

# ---------------------------------------------------------------- plumbing
urls = ["" if w == "index.html" else w.replace("index.html", "") for w in written]
urls.sort(key=lambda u: (u != "", u.startswith("cities/"), u))
open(f"{DOCS}/sitemap.xml", "w").write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                       + "".join(f"  <url><loc>{DOMAIN}/{u}</loc><lastmod>{TODAY}</lastmod></url>\n" for u in urls) + "</urlset>\n")
open(f"{DOCS}/robots.txt", "w").write(f"User-agent: *\nAllow: /\n\nSitemap: {DOMAIN}/sitemap.xml\n")
json.dump({"name": BRAND, "short_name": "WA Eats", "description": f"{TAGLINE}, plus {N_REST:,} Washington State restaurants.", "start_url": f"{BASE}/", "display": "browser",
           "background_color": "#f9fbf9", "theme_color": "#1F4D3A",
           "icons": [{"src": f"{BASE}/icon-192.png", "sizes": "192x192", "type": "image/png"}, {"src": f"{BASE}/icon-512.png", "sizes": "512x512", "type": "image/png"}]},
          open(f"{DOCS}/site.webmanifest", "w"), indent=2)
if CUSTOM_DOMAIN:
    open(f"{DOCS}/CNAME", "w").write(CUSTOM_DOMAIN + "\n")
elif os.path.exists(f"{DOCS}/CNAME"):
    os.remove(f"{DOCS}/CNAME")   # no custom domain yet: GitHub serves the project address
open(f"{DOCS}/.nojekyll", "w").write("")
os.makedirs(f"{ROOT}/playbook", exist_ok=True)
json.dump({"generated": TODAY, "records_through": THROUGH, "restaurants": N_REST, "towns": N_TOWNS, "teriyaki": len(TERI), "teriyaki_outside_king": outside_king,
           "teriyaki_spicy": spicy, "teriyaki_katsu": katsu, "teriyaki_gyoza": gyoza, "pho": len(PHOS), "drive_ins": len(DRIVE), "drive_in_independents": indep,
           "seafood": len(SEA), "oyster_places": len(OYSTER_BARS), "seafood_outside_king": sea_out, "kc_rated": len(RATED),
           "kc_ratings": dict(Counter(KCR[p.kc["r"]] for p in RATED)), "cities": city_stats},
          open(f"{ROOT}/playbook/site-numbers.json", "w"), indent=1)
print("wrote", len(written) + 1, "pages:", ", ".join(written))
print(f"restaurants {N_REST:,} in {N_TOWNS} towns | teriyaki {len(TERI)} ({outside_king} outside King) | pho {len(PHOS)} | drive-ins {len(DRIVE)} | seafood {len(SEA)} | KC rated {len(RATED):,}")
