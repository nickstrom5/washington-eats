"""QA for the website in docs/. Exits 1 on any problem.

Static checks, every HTML file (fast, no browser):
  <html lang="en">; title 50-60 and description 140-160 characters, unique (404 exempt); one <h1> and no skipped heading level;
  canonical = the page's own https URL = og:url = its sitemap entry (the 404 page names none and is noindex with a link home);
  robots meta; Open Graph and Twitter tags complete and equal to the title and description, og.png 1200x630; theme-color, an SVG
  favicon file (never a data: URI), favicon-32, apple-touch-icon 180 and a manifest whose icons exist; a Content-Security-Policy
  meta before any inline block whose hashes match exactly this page's inline <script>/<style> blocks, default-src 'none' and nothing
  unsafe; the referrer meta; no inline style or on* attributes; JSON-LD that parses, has no raw "<" and no ratings or reviews, with
  sane types (Organization with the Eats Ranked parentOrganization, WebSite, MobileApplication/WebApplication offers, Article
  dates, BreadcrumbList URLs that resolve, ItemList counts that match the visible list, FAQPage equal to the visible FAQ) and
  @id references that resolve; the footer's "Part of Eats Ranked" link and the contact address nick@eatsranked.com (the old
  gmail address nowhere in docs/); no "every/all N restaurants", "confirmed/verified open" or best/#1 overclaims; only http(s),
  mailto and tel links, every same-site link and #anchor resolves, external links carry rel=noopener; images with alt, width,
  height and decoding=async; no Apple logo on the early-access button; index under 150 KB; every page carries the #org Organization; og:type article only for Article pages; wording the data doesn't back (UNBACKED); city pages promise only the sections
  they have; guide pages list exactly the hand-checked places in the data, and the numbers on the pages equal the data's (towns, teriyaki dishes,
  King County ratings, drive-in groups);
  no website from pipeline/website_blocklist.json anywhere in docs/;
  sitemap = the indexable pages, lastmod valid and not in the future; robots.txt; no notes (*.md) in docs/; every indexable page
  linked from another and within 3 clicks of home; the web app keeps localStorage under "wae-" (the github.io origin is shared).

Browser checks (headless Chrome via Python Playwright, channel="chrome"), every page plus a missing URL (served the 404 page with
status 404, as GitHub Pages does), at 375x812 and 1280x800, light and dark: no sideways scroll, one <h1>, no console errors, no CSP
violations, no failed or off-site requests, no broken images, no clipped text; at 375 px light, every link, button and field that
isn't inside a sentence is at least 24x24 px (WCAG 2.5.8); text contrast 4.5:1 on the main pages in both schemes.

The web app (explore/), at both widths: loads (CLS under 0.05 with a slow core.json, transfer measured), the teriyaki guide lists
the data's hand-checked shops; searches (a famous place, a town, a dish with and without the accent, a street, emoji, punctuation,
empty); town, kind and Hide chains filters; Near me inside Washington sorts by distance, outside says so, denied says so, and the
list never claims "Nearest" without a location; a place opens as a labelled modal dialog (page inert, focus on Close) showing the
data file's own address, phone and website; Escape and the browser's Back close it; Near me works again after a move (a fresh fix each press); bad stored values don't stop the app; a #p= deep link opens the right place on a fresh
load; Save survives a reload under the "wae-" prefix; hostile hashes, a junk stored guide and script/quote/bidi text in the hash or
the search box stay inert; the skip link doesn't reset a search; the map draws and a dot opens its place; keyboard focus is visible;
every control has an accessible name; prefers-reduced-motion turns smooth scrolling off; a failed core.json is reported; the search
box's placeholder isn't cut off at 375 px (scrollWidth against clientWidth) and is 16px or more; a famous place that isn't in the opening
guide (Canlis, in Teriyaki) finds nothing there but offers "See N matches in All restaurants", and one click shows it there with the
same search (a guide search with only a few matches offers it too, and a search nothing matches offers nothing).

Usage: .venv/bin/python scripts/qa-site.py [--static]
  QA_DOCS=<dir>   check another copy of docs/ (used to prove each check can fail)
  QA_PORT=<port>  serve on this port (default: any free one; the machine is shared, so sessions keep to their own range)
  QA_SHOTS=<dir>  also save screenshots of the key pages there
Until the custom domain is live the site sits under /washington-eats/ on github.io, so it's served here under that same path.
Adapted from wi-eats, co-eats and ct-eats scripts/qa-site.py. Never drives anyone's own browser.
"""
import base64
import datetime
import functools
import gzip
import hashlib
import html
import html.parser
import http.server
import json
import math
import os
import re
import struct
import sys
import tempfile
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET
from collections import Counter, deque

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DOCS = os.path.abspath(os.environ.get("QA_DOCS") or os.path.join(ROOT, "docs"))
SHOTS = os.environ.get("QA_SHOTS")
STATIC_ONLY = "--static" in sys.argv
NS = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
INDEX_HTML = open(os.path.join(DOCS, "index.html"), encoding="utf-8").read()
BASE = re.search(r'data-base="([^"]*)"', INDEX_HTML).group(1)              # "/washington-eats" on github.io, "" on a custom domain
DOMAIN = re.search(r'<link rel="canonical" href="([^"]+)"', INDEX_HTML).group(1).rstrip("/")   # https://host[/washington-eats]
HOST = urllib.parse.urlparse(DOMAIN).netloc
STORAGE_PREFIX = "wae-"                 # Wisconsin is "we-", Connecticut "ce-", Colorado "coeats-": all on nickstrom5.github.io
EMAIL = "nick@eatsranked.com"           # Nick, 2026-10-12
OLD_EMAIL = "work-with-nick@gmail.com"
PARENT = {"@type": "Organization", "@id": "https://eatsranked.com/#organization", "name": "Eats Ranked", "url": "https://eatsranked.com/"}
PART_OF = 'Part of <a href="https://eatsranked.com/">Eats Ranked</a>, restaurant apps state by state.'
ROBOTS = "index,follow,max-image-preview:large"
TODAY = datetime.date.today().isoformat()
BANNED_LD = {"aggregateRating", "review", "reviews", "reviewRating", "ratingValue", "reviewCount", "bestRating"}
# claims the data can't back: the lists hold what was checked or matched, never "every"/"all N" restaurants, and a dated check
# isn't a promise that a place is open now
OVERCLAIMS = [
    r"\bevery\s+(?:single\s+)?(?:washington\s+|local\s+)?(?:restaurant|place to eat|eatery|caf[eé]|bar|menu)\b",
    r"\bevery\s+place\s+in\s+(?:washington|the\s+state)",
    r"\ball\s+(?:of\s+the\s+)?\d[\d,]*\s+(?:\w+\s+){0,2}(?:restaurants|places|shops|spots|caf[eé]s|bars)\b",
    r"\b(?:all|every)\s+(?:the\s+)?(?:restaurants|places)\s+in\s+(?:the\s+state|washington|town)\b",
    r"\bsearch\s+all\b", r"\bhas\s+all\b", r"\ball\s+of\s+washington'?s\s+restaurants",
    r"\b(?:confirmed|verified)\s+open\b", r"\bguaranteed\s+open\b",
    r"\b(?:the\s+)?best\s+(?:teriyaki|ph[oở]|burgers?|drive-?ins?|oysters?|seafood|restaurants?|places?)\b",
    r"#1\b", r"\bnumber[\s-]one\b", r"\btop[\s-]rated\b", r"\bhighest[\s-]rated\b",
    r"\biconic\s+pts\b",
]
# wording the data doesn't back (found in verification): an honoree's years at one address are often unknown (the Windmill, Paul's);
# the app asks Apple Maps for place cards, so something does leave the phone; Kitsap publishes a placard layer (playbook/12-sources.md);
# Walla Walla and Wenatchee aren't among the biggest towns; the app's home screen puts search above the lists
UNBACKED = [r"decades at the same address", r"leaves your phone", r"publish(?:es)? ratings in bulk", r"biggest towns", r"lists, then search"]
problems = []


def bad(msg):
    problems.append(msg)


# ---------------------------------------------------------------- parsing
class Page(html.parser.HTMLParser):
    """The facts the static checks need from one HTML file."""

    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.lang, self.title, self.meta, self.prop, self.links = None, "", {}, {}, []
        self.headings, self.ids, self.section_ids, self.imgs, self.sources, self.anchors = [], [], set(), [], [], []
        self.scripts, self.styles, self.ldjson, self.bad_attrs, self.csp_pos, self.first_inline = [], [], [], [], None, None
        self._in, self._buf, self._h, self._a, self.pos = None, [], None, None, 0
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self.pos += 1
        for k, _ in attrs:
            if k == "style" or k.startswith("on"):
                self.bad_attrs.append(f"<{tag} {k}=…>")
        if tag == "html":
            self.lang = a.get("lang")
        if "id" in a:
            self.ids.append(a["id"])
            if tag == "section":
                self.section_ids.add(a["id"])
        if tag == "img":
            self.imgs.append(a)
        if tag == "source":
            self.sources.append(a)
        if tag == "meta":
            if a.get("name"):
                self.meta[a["name"]] = a.get("content", "")
            if a.get("property"):
                self.prop[a["property"]] = a.get("content", "")
            if (a.get("http-equiv") or "").lower() == "content-security-policy":
                self.meta["csp"] = a.get("content", "")
                self.csp_pos = self.pos
        if tag == "link":
            self.links.append(a)
        if tag == "a":
            self._a = dict(a, _text=[])
            self.anchors.append(self._a)
        if tag in ("script", "style", "title"):
            if tag in ("script", "style") and self.first_inline is None:
                self.first_inline = self.pos
            self._in, self._buf = (tag, a.get("type")), []
        if re.fullmatch(r"h[1-6]", tag):
            self._h = (int(tag[1]), [])

    def handle_endtag(self, tag):
        if self._in and tag == self._in[0]:
            text = "".join(self._buf)
            kind, typ = self._in
            if kind == "title":
                self.title = text
            elif kind == "style":
                self.styles.append(text)
            elif typ == "application/ld+json":
                self.ldjson.append(text)
            else:
                self.scripts.append(text)
            self._in = None
        if self._h and tag == f"h{self._h[0]}":
            self.headings.append((self._h[0], "".join(self._h[1]).strip()))
            self._h = None
        if tag == "a":
            self._a = None

    def handle_data(self, data):
        if self._in:
            self._buf.append(data)
        if self._h is not None:
            self._h[1].append(data)
        if self._a is not None:
            self._a["_text"].append(data)

    def link(self, rel):
        return next((l for l in self.links if l.get("rel") == rel), None)


def sha(s):
    return "'sha256-" + base64.b64encode(hashlib.sha256(s.encode("utf-8")).digest()).decode() + "'"


def walk(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            yield path + "." + k, k, v
            yield from walk(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o):
            yield from walk(v, f"{path}[{i}]")


def nodes(ld):
    """Every dict with an @type, nested ones included."""
    out = []
    def go(x):
        if isinstance(x, dict):
            if "@type" in x:
                out.append(x)
            for v in x.values():
                go(v)
        elif isinstance(x, list):
            for v in x:
                go(v)
    go(ld)
    return out


def html_files():
    out = []
    for d, _, fs in os.walk(DOCS):
        out += [os.path.relpath(os.path.join(d, f), DOCS) for f in fs if f.endswith(".html")]
    return sorted(out)


def page_url(path):
    return DOMAIN + "/" + ("" if path == "index.html" else path.removesuffix("index.html"))


def file_for(path):
    """A site path (with or without BASE) -> the file in docs/, or None."""
    path = urllib.parse.unquote(path.split("#")[0].split("?")[0])
    if BASE and (path == BASE or path.startswith(BASE + "/")):
        path = path[len(BASE):]
    f = os.path.join(DOCS, path.lstrip("/"))
    if os.path.isdir(f):
        f = os.path.join(f, "index.html")
    return f if os.path.isfile(f) else None


def url_to_file(u):
    p = urllib.parse.urlparse(u)
    if p.scheme != "https" or p.netloc != HOST:
        return None
    return file_for(p.path)


def png_size(path):
    with open(path, "rb") as f:
        head = f.read(24)
    return struct.unpack(">II", head[16:24]) if head[:8] == b"\x89PNG\r\n\x1a\n" else None


def visible_text(s):
    t = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", s, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()


# ---------------------------------------------------------------- the data the pages are built from (docs/data, as served)
CORE = json.load(open(os.path.join(DOCS, "data/core.json"), encoding="utf-8"))
DETAIL = json.load(open(os.path.join(DOCS, "data/detail.json"), encoding="utf-8"))
C = CORE["cols"]
N = len(C["id"])
REST = [i for i in range(N) if C["v"][i] != 1]
CITY = lambda i: CORE["cities"][C["c"][i]] if C["c"][i] is not None else ""
GUIDE_BITS = {"washington-teriyaki.html": 1, "washington-pho.html": 2, "washington-oysters-seafood.html": 4, "washington-drive-ins.html": 8}
IN_GUIDE = {b: [i for i in REST if (C["hc"][i] or 0) & b] for b in (1, 2, 4, 8)}
N_REST, N_TOWNS = len(REST), len({CITY(i) for i in REST if CITY(i)})
KCR = {4: "Excellent", 3: "Good", 2: "Okay", 1: "Needs to Improve"}
CLAIMY_NAMES = sorted({n for n in C["n"] if any(re.search(rx, n, re.I) for rx in OVERCLAIMS)}, key=len, reverse=True)


# ---------------------------------------------------------------- static checks
def static_checks():
    files = html_files()
    pages = {f: open(os.path.join(DOCS, f), encoding="utf-8").read() for f in files}
    parsed = {f: Page(t) for f, t in pages.items()}
    smap = sitemap_checks(files, parsed)
    titles, descs, defined_ids, referenced_ids = {}, {}, set(), []
    for rel, s in pages.items():
        pg, w = parsed[rel], rel
        indexable = "noindex" not in pg.meta.get("robots", "")
        if pg.lang != "en":
            bad(f"{w}: <html lang> is {pg.lang!r}")
        title, desc = pg.title, pg.meta.get("description", "")
        if rel != "404.html":
            if not 50 <= len(title) <= 60:
                bad(f"{w}: title is {len(title)} characters: {title}")
            if not 140 <= len(desc) <= 160:
                bad(f"{w}: description is {len(desc)} characters: {desc}")
            if title in titles:
                bad(f"{w}: same title as {titles[title]}")
            if desc in descs:
                bad(f"{w}: same description as {descs[desc]}")
            titles[title], descs[desc] = rel, rel
        # headings: one h1, first, and no level skipped on the way down
        levels = [h for h, _ in pg.headings]
        if levels.count(1) != 1:
            bad(f"{w}: {levels.count(1)} <h1>")
        if levels and levels[0] != 1:
            bad(f"{w}: the first heading is h{levels[0]}, not h1")
        for a, b in zip(levels, levels[1:]):
            if b > a + 1:
                bad(f"{w}: heading jumps from h{a} to h{b}")
                break
        # canonical, robots, Open Graph, Twitter
        can = (pg.link("canonical") or {}).get("href")
        if rel == "404.html":
            if can or "og:url" in pg.prop:
                bad("404.html: names a canonical or og:url (it's served at whatever address was missing)")
            if "noindex" not in pg.meta.get("robots", ""):
                bad("404.html: isn't noindex")
            if not any(a.get("href") == BASE + "/" for a in pg.anchors):
                bad("404.html: no link home")
        else:
            if can != page_url(rel):
                bad(f"{w}: canonical {can} isn't {page_url(rel)}")
            if pg.prop.get("og:url") != can:
                bad(f"{w}: og:url {pg.prop.get('og:url')} isn't the canonical")
            if pg.meta.get("robots") != ROBOTS:
                bad(f"{w}: robots meta is {pg.meta.get('robots')!r}")
            if indexable and can not in smap:
                bad(f"{w}: indexable but not in sitemap.xml")
        for k, want in (("og:title", title), ("og:description", desc), ("twitter:title", title), ("twitter:description", desc)):
            got = pg.prop.get(k) if k.startswith("og:") else pg.meta.get(k)
            if got != want:
                bad(f"{w}: {k} doesn't match the {'title' if 'title' in k else 'description'}")
        if pg.prop.get("og:type") not in ("website", "article") or not pg.prop.get("og:site_name") or not pg.prop.get("og:image:alt"):
            bad(f"{w}: og:type/site_name/image:alt missing")
        img = pg.prop.get("og:image", "")
        if img != DOMAIN + "/og.png" or pg.meta.get("twitter:image") != img or pg.meta.get("twitter:card") != "summary_large_image":
            bad(f"{w}: og:image/twitter:image/card is {img!r} / {pg.meta.get('twitter:image')!r} / {pg.meta.get('twitter:card')!r}")
        if (pg.prop.get("og:image:width"), pg.prop.get("og:image:height")) != ("1200", "630"):
            bad(f"{w}: og:image size tags aren't 1200x630")
        # icons, manifest, theme
        if not pg.meta.get("theme-color"):
            bad(f"{w}: no theme-color")
        icons = {(l.get("rel"), l.get("type") or l.get("sizes")): l.get("href", "") for l in pg.links if "icon" in (l.get("rel") or "")}
        svg = icons.get(("icon", "image/svg+xml"), "")
        if not svg or svg.startswith("data:") or not file_for(svg):
            bad(f"{w}: the SVG favicon isn't a file on the site ({svg[:40]!r}); search engines can't use a data: favicon")
        for (relname, kind), want in ((("icon", "image/png"), (32, 32)), (("apple-touch-icon", "180x180"), (180, 180))):
            href = icons.get((relname, kind)) or next((h for (r, _), h in icons.items() if r == relname and h.endswith(".png")), "")
            f = file_for(href) if href else None
            if not f or png_size(f) != want:
                bad(f"{w}: {relname} {href!r} isn't a {want[0]}x{want[1]} PNG on the site")
        man = (pg.link("manifest") or {}).get("href", "")
        if not file_for(man):
            bad(f"{w}: manifest link {man!r} doesn't resolve")
        # Content-Security-Policy
        csp = pg.meta.get("csp")
        if not csp:
            bad(f"{w}: no Content-Security-Policy meta")
        else:
            pol = {d.split()[0]: d.split()[1:] for d in (x.strip() for x in csp.split(";")) if d}
            if pg.first_inline is not None and pg.csp_pos > pg.first_inline:
                bad(f"{w}: the CSP meta comes after an inline block, so it doesn't cover it")
            want = {"default-src": ["'none'"], "img-src": ["'self'"], "connect-src": ["'self'"], "manifest-src": ["'self'"],
                    "base-uri": ["'none'"], "form-action": ["'none'"], "object-src": ["'none'"]}
            for k, v in want.items():
                if pol.get(k) != v:
                    bad(f"{w}: CSP {k} is {pol.get(k)}, want {v}")
            for name, blocks in (("script-src", pg.scripts), ("style-src", pg.styles)):
                have = pol.get(name, [])
                need = [sha(b) for b in blocks] or ["'none'"]
                if sorted(have) != sorted(need):
                    bad(f"{w}: CSP {name} hashes don't match the page's inline blocks")
        if '<!-- <meta name="apple-itunes-app" content="app-id=APP_ID"> fill in once the App Store record exists -->' not in s:
            bad(f"{w}: no commented apple-itunes-app placeholder (SEO-SPEC)")
        if '<meta name="referrer" content="strict-origin-when-cross-origin">' not in s:
            bad(f"{w}: no referrer meta")
        if pg.bad_attrs:
            bad(f"{w}: inline style/event attributes (blocked by the CSP): {pg.bad_attrs[:3]}")
        for css in pg.styles:   # "font: 14px inherit" is invalid, so the browser drops it (the search box fell to 13.3px)
            for m in re.finditer(r"(?<![-\w])font:\s*([^;}]*)", css):
                if "inherit" in m.group(1) and m.group(1).strip() != "inherit":
                    bad(f"{w}: invalid CSS shorthand “font: {m.group(1).strip()}” (inherit can't sit inside it)")
        # JSON-LD
        lds = []
        for raw in pg.ldjson:
            if "<" in raw:
                bad(f"{w}: raw '<' inside JSON-LD")
            try:
                lds.append(json.loads(raw))
            except ValueError as ex:
                bad(f"{w}: bad JSON-LD ({ex})")
        # every page carries the site's Organization with its Eats Ranked parent (the hub lists this site as a subOrganization)
        if not any(n.get("@type") == "Organization" and n.get("@id") == DOMAIN + "/#org" for ld in lds for n in nodes(ld)):
            bad(f"{w}: no #org Organization node (with the Eats Ranked parentOrganization) on this page")
        # og:type follows the page: an Article's page is an article, the rest (home, web app, privacy, terms, 404) a website
        want_type = "article" if any(n.get("@type") == "Article" for ld in lds for n in nodes(ld)) else "website"
        if pg.prop.get("og:type") != want_type:
            bad(f"{w}: og:type is {pg.prop.get('og:type')!r}, want {want_type!r}")
        for ld in lds:
            if ld.get("@context") != "https://schema.org":
                bad(f"{w}: JSON-LD @context is {ld.get('@context')!r}")
            for p, k, v in walk(ld):
                if k in BANNED_LD:
                    bad(f"{w}: ratings or reviews in JSON-LD at {p}")
                if k == "streetAddress" and not str(v).strip():
                    bad(f"{w}: empty streetAddress at {p}")
                if k == "@id" and isinstance(v, str):
                    referenced_ids.append((w, v))
            for n in nodes(ld):
                if "@id" in n and len(n) > 1:
                    defined_ids.add(n["@id"])
                jsonld_node_checks(w, rel, n, pg, s, smap)
        # the family line and the contact address
        foot = s[s.rfind("<footer"):s.rfind("</footer>")]
        if PART_OF not in foot:
            bad(f"{w}: footer lacks “Part of Eats Ranked” linking https://eatsranked.com/")
        if f'href="mailto:{EMAIL}"' not in foot:
            bad(f"{w}: footer has no mailto:{EMAIL}")
        for a in pg.anchors:
            href = a.get("href") or ""
            if href.startswith("mailto:") and urllib.parse.unquote(href[7:].split("?")[0]) != EMAIL:
                bad(f"{w}: mailto to {href[7:].split('?')[0]!r}, not {EMAIL}")
        # overclaims: text, meta, alt text, JSON-LD and the web app's strings
        hay = re.sub(r"\s+", " ", html.unescape(re.sub(r"<style>.*?</style>", " ", s, flags=re.S)).replace("\\u0026", "&"))
        for name in CLAIMY_NAMES:          # a restaurant called "Best Teriyaki" is its name, not our claim
            hay = hay.replace(name, " ")
        for rx in OVERCLAIMS:
            for m in re.finditer(rx, hay, re.I):
                bad(f"{w}: overclaim “{m.group(0)}” (…{hay[max(0, m.start() - 50):m.end() + 20]}…)")
        for rx in UNBACKED:
            for m in re.finditer(rx, hay, re.I):
                bad(f"{w}: unbacked wording “{m.group(0)}” (…{hay[max(0, m.start() - 50):m.end() + 20]}…)")
        # links
        for a in pg.anchors:
            href = html.unescape(a.get("href") or "")
            sp = urllib.parse.urlsplit(href)
            scheme = sp.scheme.lower()
            if scheme in ("http", "https"):
                if sp.netloc == HOST:
                    bad(f"{w}: absolute link to our own site {href} (use a site path)")
                # the family's own hub link is first-party and carries the exact markup every state site shares
                if "noopener" not in (a.get("rel") or "") and href != "https://eatsranked.com/":
                    bad(f"{w}: external link without rel=noopener: {href[:60]}")
                continue
            if scheme in ("mailto", "tel"):
                if scheme == "tel" and not re.fullmatch(r"tel:\+1\d{10}", href):
                    bad(f"{w}: bad tel: link {href}")
                continue
            if scheme:
                bad(f"{w}: link with scheme {scheme}: {href[:50]}")
                continue
            if href.startswith("#"):
                if href[1:] and href[1:] not in pg.ids:
                    bad(f"{w}: link to a missing anchor {href}")
                continue
            if not href.startswith(BASE + "/"):
                bad(f"{w}: relative link {href!r} (pages are served at different depths; use {BASE}/…)")
                continue
            f = file_for(href)
            if not f:
                bad(f"{w}: broken link {href}")
            elif sp.fragment and f.endswith(".html") and "=" not in sp.fragment and sp.fragment not in Page(open(f, encoding="utf-8").read()).ids:
                bad(f"{w}: link to a missing anchor {href}")
        for l in pg.links:
            href = l.get("href", "")
            if href.startswith("/") and not file_for(href):
                bad(f"{w}: <link> to a missing file {href}")
            if href.startswith("http://"):
                bad(f"{w}: mixed content: <link> over http {href}")
        for m in re.finditer(r'<(?:img|script|source|iframe)\b[^>]*\s(?:src|srcset)="http://', s):
            bad(f"{w}: mixed content: {m.group(0)[:60]}")
        # images
        for i, im in enumerate(pg.imgs):
            if not (im.get("alt") or "").strip():
                bad(f"{w}: <img> without alt text: {im.get('src')}")
            if not im.get("width") or not im.get("height"):
                bad(f"{w}: <img> without width/height: {im.get('src')}")
            if im.get("decoding") != "async":
                bad(f"{w}: <img> without decoding=async: {im.get('src')}")
            if not file_for(im.get("src", "")):
                bad(f"{w}: <img> file missing: {im.get('src')}")
        for so in pg.sources:
            if not file_for(so.get("srcset", "")):
                bad(f"{w}: <source> file missing: {so.get('srcset')}")
        for m in re.finditer(r'<a class="btn store-btn"[^>]*>(.*?)</a>', s, re.S):
            if "<svg" in m.group(1):
                bad(f"{w}: the early-access button carries an Apple logo (only Apple's own badge may)")
        dup = {i for i in pg.ids if pg.ids.count(i) > 1}
        if dup:
            bad(f"{w}: duplicate ids {sorted(dup)[:5]}")
        if rel.startswith("cities/"):
            city_promise_checks(w, pg)
    for w, ref in referenced_ids:
        if ref not in defined_ids:
            bad(f"{w}: JSON-LD @id {ref} isn't defined on any page")
    if len(pages["index.html"].encode()) > 150_000:
        bad(f"index.html is {len(pages['index.html'].encode()):,} bytes (budget 150 KB)")
    content_checks(pages, parsed)
    link_graph_checks(pages, parsed, smap)
    site_file_checks(parsed)
    return files, parsed


def jsonld_node_checks(w, rel, n, pg, s, smap):
    t = n.get("@type")
    if t == "Organization" and n.get("@id", "").endswith("/#org"):
        if n.get("parentOrganization") != PARENT:
            bad(f"{w}: the #org Organization's parentOrganization is {n.get('parentOrganization')!r}, want Eats Ranked's")
        if n.get("email") != EMAIL or n.get("contactPoint", {}).get("email") != EMAIL:
            bad(f"{w}: the Organization's email isn't {EMAIL}")
        if n.get("url") != DOMAIN + "/" or not url_to_file(n.get("logo", {}).get("url", "")):
            bad(f"{w}: the Organization's url or logo is wrong")
    if t in ("MobileApplication", "WebApplication"):
        o = n.get("offers", {})
        if not n.get("name") or not n.get("operatingSystem") or not n.get("applicationCategory") or o.get("price") != "0" or o.get("priceCurrency") != "USD":
            bad(f"{w}: {t} lacks name/operatingSystem/applicationCategory or a free USD offer")
        if n.get("url") and n["url"] != page_url(rel) and n["url"] != DOMAIN + "/":
            bad(f"{w}: {t} url {n['url']} isn't this site's page")
    if t == "WebSite" and n.get("url") != DOMAIN + "/":
        bad(f"{w}: WebSite url {n.get('url')}")
    if t == "Article":
        dp, dm = n.get("datePublished", ""), n.get("dateModified", "")
        if not (re.fullmatch(r"\d{4}-\d{2}-\d{2}", dp) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", dm) and dp <= dm <= TODAY):
            bad(f"{w}: Article dates {dp} / {dm} (published ≤ modified ≤ today)")
        if smap.get(page_url(rel)) and smap[page_url(rel)] != dm:
            bad(f"{w}: Article dateModified {dm} isn't the sitemap lastmod {smap[page_url(rel)]}")
        if n.get("mainEntityOfPage") != page_url(rel) or not n.get("headline") or not url_to_file(n.get("image", "")):
            bad(f"{w}: Article mainEntityOfPage/headline/image is wrong")
    if t == "BreadcrumbList":
        items = n.get("itemListElement", [])
        if [i.get("position") for i in items] != list(range(1, len(items) + 1)):
            bad(f"{w}: BreadcrumbList positions aren't 1..n")
        for i in items:
            if not url_to_file(i.get("item", "")):
                bad(f"{w}: breadcrumb {i.get('name')!r} → {i.get('item')} doesn't resolve")
        if items and items[-1].get("item") != page_url(rel):
            bad(f"{w}: the last breadcrumb isn't this page")
        shown = re.findall(r'<nav class="crumbs"[^>]*>(.*?)</nav>', s, re.S)
        names = [html.unescape(re.sub(r"<[^>]+>", "", x)) for x in re.findall(r"<li[^>]*>(.*?)</li>", shown[0] if shown else "")]
        if names != [i.get("name") for i in items]:
            bad(f"{w}: BreadcrumbList names {[i.get('name') for i in items]} aren't the visible crumbs {names}")
    if t == "ItemList":
        items = n.get("itemListElement", [])
        if n.get("numberOfItems") != len(items) or [i.get("position") for i in items] != list(range(1, len(items) + 1)):
            bad(f"{w}: ItemList numberOfItems/positions don't match its {len(items)} items")
        if n.get("url") != page_url(rel):
            bad(f"{w}: ItemList url isn't this page")
        visible = {html.unescape(x) for x in re.findall(r'<ol class="places">.*?</ol>', s, re.S) for x in re.findall(r"<li><h3>(.*?)</h3>", x)}
        for i in items:
            r = i.get("item", {})
            if r.get("@type") != "Restaurant" or not r.get("name") or r.get("address", {}).get("addressRegion") != "WA":
                bad(f"{w}: ItemList item isn't a Washington Restaurant: {str(r)[:80]}")
            if r.get("name") not in visible:
                bad(f"{w}: ItemList names {r.get('name')!r}, which the page doesn't list")
            if r.get("url") and not re.match(r"https://", r["url"]) and not re.match(r"http://", r["url"]):
                bad(f"{w}: ItemList item url {r['url']!r} isn't http(s)")
    if t == "FAQPage":
        shown = [(html.unescape(q), html.unescape(a)) for q, a in re.findall(r"<details><summary>(.*?)</summary><p>(.*?)</p></details>", s, re.S)]
        ld = [(q.get("name"), q.get("acceptedAnswer", {}).get("text")) for q in n.get("mainEntity", [])]
        if not shown or shown != ld:
            bad(f"{w}: FAQPage doesn't mirror the visible FAQ exactly ({len(ld)} vs {len(shown)} questions)")


CITY_PROMISES = [(r"teriyaki", "teriyaki"), (r"ph[oở]\b", "pho"), (r"drive-?ins?", "drive-ins"), (r"seafood|oyster", "seafood"),
                 (r"honors|james beard", "honors"), (r"\boldest\b", "oldest")]


def city_promise_checks(w, pg):
    """A city page's title, h1 and description name only the sections it has (Wenatchee has no hand-checked teriyaki nearby)."""
    h1 = next((t for l, t in pg.headings if l == 1), "")
    h1 = re.sub(r"^Washington Eats · [^,]+, Washington", "", h1)      # the kicker names the state, not a section
    promise = " ".join([pg.title, h1, pg.meta.get("description", "")]).lower()
    for rx, sec in CITY_PROMISES:
        if re.search(rx, promise) and sec not in pg.section_ids:
            bad(f"{w}: title/h1/description mention {rx!r} but the page has no #{sec} section")


def content_checks(pages, parsed):
    """Numbers on the pages equal the data file's; guide pages list exactly the hand-checked places."""
    idx = visible_text(pages["index.html"])
    for want in (f"{N_REST:,} restaurants, cafés, espresso stands and bars in {N_TOWNS:,} Washington towns", f"{len(IN_GUIDE[1])} teriyaki shops",
                 f"{len(IN_GUIDE[2])} phở shops", f"{len(IN_GUIDE[8])} drive-ins"):
        if want not in idx:
            bad(f"index.html: doesn't say “{want}” (the data's count)")
    for g, bit in GUIDE_BITS.items():
        s = pages.get(g)
        if not s:
            bad(f"missing guide page {g}")
            continue
        names = [html.unescape(x) for ol in re.findall(r'<ol class="places">(.*?)</ol>', s, re.S) for x in re.findall(r"<li><h3>(.*?)</h3>", ol)]
        want = [C["n"][i] for i in IN_GUIDE[bit]]
        if Counter(names) != Counter(want):
            bad(f"{g}: lists {len(names)} places, the data has {len(want)} hand-checked for it "
                f"(extra {sorted((Counter(names) - Counter(want)))[:3]}, missing {sorted((Counter(want) - Counter(names)))[:3]})")
        if str(len(want)) not in parsed[g].title:
            bad(f"{g}: the title's count isn't {len(want)}")
        # every website link on a guide is the place's own link from the data
        sites = {x for i in IN_GUIDE[bit] for x in [(DETAIL[i] or {}).get("w")] if x}
        for a in parsed[g].anchors:
            if "nofollow" in (a.get("rel") or "") and html.unescape(a["href"]) not in sites:
                bad(f"{g}: website link {a['href'][:60]} isn't any listed place's own link in the data")
    teri = visible_text(pages.get("washington-teriyaki.html", ""))
    # what the teriyaki shops serve, counted from the data's dish lists (a spicy chicken katsu is a spicy chicken dish too)
    items = lambda i: [d.strip().lower() for d in re.split(r"[;,]", C["di"][i] or "") if d.strip()]
    tg = IN_GUIDE[1]
    dish = (sum(1 for i in tg if re.search(r"chicken (?:thigh |breast )?teriyaki|teriyaki chicken", C["di"][i] or "", re.I)),
            sum(1 for i in tg if any("spicy" in d and "chicken" in d for d in items(i))),
            sum(1 for i in tg if "chicken katsu" in (C["di"][i] or "").lower()), sum(1 for i in tg if "gyoza" in (C["di"][i] or "").lower()))
    want = f"{dish[0]} of the {len(tg)} list chicken teriyaki by name, {dish[1]} a spicy chicken dish, {dish[2]} a chicken katsu and {dish[3]} gyoza"
    if want not in teri:
        bad(f"washington-teriyaki.html: the dish counts aren't the data's (want “{want}”)")
    # King County's ratings: the counts on the pages are the data's
    king = [i for i in REST if C["co"][i] is not None and CORE["counties"][C["co"][i]] == "King"]
    rated = lambda ids: sum(1 for i in ids if C["kr"][i])
    idx_want = [f"{rated(REST):,} of King County's {len(king):,} places also carry", f"{rated(REST):,} King County places have one"]
    for x in idx_want:
        if x not in idx:
            bad(f"index.html: doesn't say “{x}” (the data's King County rating counts)")
    for g, bit in GUIDE_BITS.items():
        t = visible_text(pages.get(g, ""))
        m = re.search(r"(\d+) of the (\d+) (?:carry|show)\b[^.]*food safety rating", t) or re.search(r"(\d+) King County stands show", t)
        if not m:
            bad(f"{g}: no count of the places with King County's rating")
        elif int(m.group(1)) != rated(IN_GUIDE[bit]) or (m.lastindex == 2 and int(m.group(2)) != len(IN_GUIDE[bit])):
            bad(f"{g}: says “{m.group(0)}”, the data has {rated(IN_GUIDE[bit])} of {len(IN_GUIDE[bit])} rated")
    # drive-ins: the multi-location groups and the independents add up to the list
    t = visible_text(pages.get("washington-drive-ins.html", ""))
    m, m2 = re.search(r"location by location: (.*?)\. Each brand", t), re.search(r"The other (\d+) are independent", t)
    if not m or not m2 or sum(int(x) for x in re.findall(r"\((\d+)\)", m.group(1))) + int(m2.group(1)) != len(IN_GUIDE[8]):
        bad(f"washington-drive-ins.html: the brands and independents don't add up to the {len(IN_GUIDE[8])} drive-ins")
    # a city lede with a single hand-checked place doesn't say "each"
    for rel, s in pages.items():
        if rel.startswith("cities/"):
            m = re.search(r'<p class="lede">([^<]*?) in and around [^,<]+, (each )?checked open', s)
            if m and sum(int(x) for x in re.findall(r"\b(\d+) ", m.group(1))) == 1 and m.group(2):
                bad(f"{rel}: “{m.group(1)} … each checked open” (one place)")
    outside = sum(1 for i in IN_GUIDE[1] if C["co"][i] is None or CORE["counties"][C["co"][i]] != "King")
    if f"{outside} of them outside King County" not in teri:
        bad(f"washington-teriyaki.html: the count outside King County isn't {outside}")
    ex = visible_text(pages.get("explore/index.html", ""))
    if f"{N_REST:,} restaurants" not in ex:
        bad(f"explore/index.html: doesn't give the data's {N_REST:,} restaurants")
    for rel, s in pages.items():
        t = visible_text(s)
        for d in re.findall(r"through (\d{4}-\d{2}-\d{2})", t):
            if d != CORE["records_through"]:
                bad(f"{rel}: says records through {d}, the data says {CORE['records_through']}")
        m = re.search(r"app lists ([\d,]+) restaurants, cafés, espresso stands and bars in ([^.]+?) and sorts", t)
        if rel.startswith("cities/"):
            if not m:
                bad(f"{rel}: no count of the town's restaurants")
            else:
                n = sum(1 for i in REST if CITY(i) == m.group(2))
                if int(m.group(1).replace(",", "")) != n:
                    bad(f"{rel}: says {m.group(1)} restaurants in {m.group(2)}, the data has {n}")


def link_graph_checks(pages, parsed, smap):
    """Every indexable page is linked from another page and is within 3 clicks of the home page."""
    graph = {}
    for rel, pg in parsed.items():
        outs = set()
        for a in pg.anchors:
            f = file_for(a.get("href", "")) if (a.get("href") or "").startswith(BASE + "/") else None
            if f and f.endswith(".html"):
                outs.add(os.path.relpath(f, DOCS))
        graph[rel] = outs - {rel}
    depth, q = {"index.html": 0}, deque(["index.html"])
    while q:
        u = q.popleft()
        for v in graph.get(u, ()):
            if v not in depth:
                depth[v] = depth[u] + 1
                q.append(v)
    for u in smap:
        f = url_to_file(u)
        rel = os.path.relpath(f, DOCS) if f else None
        if not rel:
            continue
        if rel != "index.html" and not any(rel in outs for src, outs in graph.items() if src != rel):
            bad(f"{rel}: orphan page (no other page links to it)")
        if depth.get(rel, 99) > 3:
            bad(f"{rel}: {depth.get(rel, 'unreachable')} clicks from the home page")


def sitemap_checks(files, parsed):
    """sitemap.xml lists exactly the indexable pages, at their canonical URLs, with a valid lastmod. Returns {url: lastmod}."""
    out = {}
    try:
        root = ET.parse(os.path.join(DOCS, "sitemap.xml")).getroot()
    except (OSError, ET.ParseError) as ex:
        bad(f"sitemap.xml: {ex}")
        return out
    for u in root.findall("s:url", NS):
        loc, lm = u.find("s:loc", NS).text, u.find("s:lastmod", NS)
        lm = lm.text if lm is not None else ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", lm or "") or lm > TODAY:
            bad(f"sitemap: {loc} lastmod {lm!r} isn't a date up to today")
        f = url_to_file(loc)
        if not f:
            bad(f"sitemap: {loc} isn't a page on {DOMAIN}")
        elif "noindex" in parsed.get(os.path.relpath(f, DOCS), Page("")).meta.get("robots", ""):
            bad(f"sitemap: {loc} is noindex")
        elif loc != page_url(os.path.relpath(f, DOCS)):
            bad(f"sitemap: {loc} isn't the page's canonical form")
        if loc in out:
            bad(f"sitemap: {loc} twice")
        out[loc] = lm
    for rel in files:
        if rel != "404.html" and "noindex" not in parsed[rel].meta.get("robots", "") and page_url(rel) not in out:
            bad(f"sitemap: {rel} is indexable but not listed")
    return out


def site_file_checks(parsed):
    robots = open(os.path.join(DOCS, "robots.txt")).read() if os.path.exists(os.path.join(DOCS, "robots.txt")) else ""
    if f"Sitemap: {DOMAIN}/sitemap.xml" not in robots or "Allow: /" not in robots or re.search(r"Disallow: /\s*$", robots, re.M):
        bad("robots.txt: needs Allow: / and an absolute Sitemap: line")
    if not os.path.exists(os.path.join(DOCS, ".nojekyll")):
        bad("docs/.nojekyll is missing")
    cname = os.path.join(DOCS, "CNAME")
    if BASE and os.path.exists(cname):
        bad("docs/CNAME exists while the site is built for the github.io address")
    if not BASE and (not os.path.exists(cname) or open(cname).read().strip() != HOST):
        bad("docs/CNAME doesn't match the canonical host")
    og = os.path.join(DOCS, "og.png")
    if png_size(og) != (1200, 630):
        bad(f"og.png is {png_size(og)}, not 1200x630")
    try:
        man = json.load(open(os.path.join(DOCS, "site.webmanifest")))
        if man.get("start_url") != BASE + "/" or not man.get("name") or not man.get("icons"):
            bad("site.webmanifest: start_url/name/icons wrong")
        for ic in man.get("icons", []):
            f = file_for(ic["src"])
            if not f or png_size(f) != tuple(int(x) for x in ic["sizes"].split("x")):
                bad(f"site.webmanifest: icon {ic['src']} missing or not {ic['sizes']}")
    except (OSError, ValueError) as ex:
        bad(f"site.webmanifest: {ex}")
    for d, _, fs in os.walk(DOCS):
        for f in fs:
            full = os.path.join(d, f)
            if f.endswith((".md", ".py", ".swift", ".log")) or f in (".DS_Store",) or "playbook" in full:
                bad(f"docs/ holds a non-site file: {os.path.relpath(full, DOCS)}")
            if f.endswith((".html", ".json", ".xml", ".txt", ".webmanifest", ".svg", ".js", ".css")):
                if OLD_EMAIL in open(full, encoding="utf-8", errors="replace").read():
                    bad(f"{os.path.relpath(full, DOCS)}: still shows {OLD_EMAIL} (the site's address is {EMAIL})")
    blocklist_checks()
    js = "\n".join(parsed.get("explore/index.html", Page("")).scripts)
    # every key the web app writes is named on the privacy page (the github.io origin is shared, so the prefix matters too)
    privacy = visible_text(open(os.path.join(DOCS, "privacy.html"), encoding="utf-8").read()) if os.path.exists(os.path.join(DOCS, "privacy.html")) else ""
    for k in sorted(set(re.findall(r"""store\.set\(\s*["'](\w+)["']""", js))):
        if STORAGE_PREFIX + k not in privacy:
            bad(f"privacy.html: doesn't name the web app's localStorage key {STORAGE_PREFIX + k}")
    if re.search(r"privacy label is\b", privacy) and "isn't on the App Store yet" not in privacy:
        bad("privacy.html: states an App Store privacy label as current before the app is on the store")
    other_state_checks()
    if f'"{STORAGE_PREFIX}"' not in js:
        bad(f"explore: localStorage prefix {STORAGE_PREFIX!r} not found")
    for m in re.finditer(r"""localStorage\.(?:get|set|remove)Item\(\s*(["'`])([^"'`]*)\1""", js):
        if not m.group(2).startswith(STORAGE_PREFIX):
            bad(f"explore: localStorage key {m.group(2)!r} doesn't start with {STORAGE_PREFIX!r}")
    if len(C["id"]) != len(set(C["id"])):
        bad("core.json: duplicate place ids")
    for i, d in enumerate(DETAIL):
        d = d or {}
        if d.get("w") and not re.match(r"https?://", d["w"]):
            bad(f"detail.json: website {d['w'][:40]!r} for {C['n'][i]!r} isn't http(s)")
        if d.get("ph") and not re.fullmatch(r"\+1\d{10}", re.sub(r"[^\d+]", "", d["ph"])):
            bad(f"detail.json: phone {d['ph']!r} for {C['n'][i]!r} isn't a +1 ten-digit number")


BLOCKLIST = os.path.join(ROOT, "pipeline", "website_blocklist.json")


def blocklist_checks():
    """No hacked, expired or wrong-business website from pipeline/website_blocklist.json appears anywhere in docs/ (pages and the web
    app's data): a "domain" entry covers the domain and every subdomain, any scheme; a "url" entry that exact address."""
    try:
        entries = json.load(open(BLOCKLIST, encoding="utf-8"))
    except (OSError, ValueError) as ex:
        bad(f"pipeline/website_blocklist.json: {ex}")
        return
    if not isinstance(entries, list) or not entries:
        bad("pipeline/website_blocklist.json: no entries (the check would pass vacuously)")
        return
    rxs = []
    for b in entries:
        if b.get("match") not in ("domain", "url") or not b.get("domain"):
            bad(f"pipeline/website_blocklist.json: bad entry {str(b)[:80]}")
            continue
        if b["match"] == "domain":
            d = re.sub(r"^www\.", "", b["domain"].strip().lower())
            rxs.append((b, re.compile(r"(?<![a-z0-9-])" + re.escape(d) + r"(?![a-z0-9-])", re.I)))
        else:
            u = re.sub(r"^(?:https?:)?//(?:www\.)?", "", b["domain"].strip(), flags=re.I).rstrip("/")
            rxs.append((b, re.compile(r"//(?:www\.)?" + re.escape(u) + r"/?(?![\w/.-])", re.I)))
    for d, _, fs in os.walk(DOCS):
        for f in fs:
            if not f.endswith((".html", ".json", ".xml", ".txt", ".webmanifest", ".svg", ".js", ".css")):
                continue
            full = os.path.join(d, f)
            t = html.unescape(open(full, encoding="utf-8", errors="replace").read()).replace("\\/", "/")
            for b, rx in rxs:
                m = rx.search(t)
                if m:
                    bad(f"{os.path.relpath(full, DOCS)}: blocklisted website for {b.get('place')} ({b.get('reason', '')[:50]}): …{t[max(0, m.start() - 30):m.end() + 10]}…")


OTHER_STATES = re.compile(r"\b(?:Wisconsin|Colorado|Connecticut|Chicago|Illinois|Florida|California|Maine|Idaho|New York|Michigan|Texas|Oregon Eats"
                          r"|WI Eats|CO Eats|CT Eats|FL Eats|CA Eats|ME Eats|ID Eats|NY Eats|Chi Ranked)\b"
                          r"|\b(?:wi|co|ct|fl|ca|me|id|ny|chi|il|mi|tx)-eats\b|chicago-restaurants-ranked|[\"'](?:we|ce|cae|nye|me|coeats|fleats|ideats)-[\"']")


def other_state_checks():
    """Public pages (text, comments, inline code) name no other state's app, repo or storage prefix. A restaurant, street or dish
    from the data ("California Ave SW", "California roll", "New York Teriyaki") is fine, so the data's own strings are set aside."""
    allowed = set()
    for k in ("n", "a", "di"):
        allowed |= {x for x in C[k] if isinstance(x, str) and OTHER_STATES.search(x)}
    for d in DETAIL:
        for k in ("note", "icon", "hon", "jbf", "w", "src"):
            x = (d or {}).get(k)
            if isinstance(x, str) and OTHER_STATES.search(x):
                allowed.add(x)
    allowed = sorted(allowed, key=len, reverse=True)
    for rel in html_files():
        s = html.unescape(open(os.path.join(DOCS, rel), encoding="utf-8").read()).replace("\\u0026", "&")
        for x in allowed:
            s = s.replace(x, " ")
        for m in OTHER_STATES.finditer(s):
            bad(f"{rel}: names another state's app or repo: “{m.group(0)}” (…{s[max(0, m.start() - 50):m.end() + 20]!r}…)")


# ---------------------------------------------------------------- server (the github.io path, and GitHub's 404 behaviour)
class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def send_error(self, code, message=None, explain=None):
        if code == 404 and os.path.exists(os.path.join(DOCS, "404.html")):   # GitHub Pages answers a missing path with 404.html
            body = open(os.path.join(DOCS, "404.html"), "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        super().send_error(code, message, explain)


def serve():
    root = DOCS
    if BASE:
        root = tempfile.mkdtemp(prefix="wa-qa-")
        os.symlink(DOCS, os.path.join(root, BASE.strip("/")))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", int(os.environ.get("QA_PORT") or 0)), functools.partial(Handler, directory=root))
    srv.handle_error = lambda *a: None     # a browser dropping a connection mid-file isn't a site problem
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


# ---------------------------------------------------------------- browser checks
INIT = """window.__csp = []; window.__cls = 0; window.__dialogs = 0;
document.addEventListener('securitypolicyviolation', e => window.__csp.push(e.violatedDirective + ' ' + (e.blockedURI || 'inline')));
try { new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) window.__cls += e.value; })
  .observe({type: 'layout-shift', buffered: true}); } catch (e) {}"""
TAP = """() => {
  const out = [];
  const blockOf = (el) => { let n = el.parentElement; while (n && getComputedStyle(n).display.startsWith('inline')) n = n.parentElement; return n; };
  for (const el of document.querySelectorAll('a[href], button, input:not([type=hidden]), select, textarea, summary')) {
    let t = el;
    if (el.matches('input[type=checkbox], input[type=radio]') && el.closest('label')) t = el.closest('label');
    if (t.closest('[hidden], [inert]')) continue;
    const cs = getComputedStyle(t);
    if (cs.visibility === 'hidden' || cs.display === 'none') continue;
    const r = t.getBoundingClientRect();
    if (r.width === 0 || r.height === 0 || r.right + scrollX <= 0 || r.bottom + scrollY <= 0) continue;   // the off-screen skip link
    if (t.tagName === 'A' && cs.display === 'inline') {     // a link inside a sentence is exempt (WCAG 2.5.8)
      const b = blockOf(t), own = t.textContent.replace(/\\s+/g, ' ').trim(), all = (b ? b.textContent : '').replace(/\\s+/g, ' ').trim();
      if (all.length > own.length + 2) continue;
    }
    if (r.width < 24 || r.height < 24) out.push(`${t.tagName.toLowerCase()} "${(t.textContent || t.getAttribute('aria-label') || '').trim().slice(0, 30)}" ${Math.round(r.width)}x${Math.round(r.height)}`);
  }
  return out;
}"""
CONTRAST = """(scope) => {
  const parse = (c) => { const m = c.match(/rgba?\\(([^)]+)\\)/); if (!m) return null; const p = m[1].split(/[\\s,\\/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; }; return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const bgOf = (el) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) { const c = parse(getComputedStyle(n).backgroundColor); if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; } }
    let base = parse(getComputedStyle(document.body).backgroundColor) || [255, 255, 255, 1];
    if (layers.length && layers[layers.length - 1][3] >= 1) base = layers.pop();
    for (const c of layers.reverse()) base = [0, 1, 2].map((i) => c[i] * c[3] + base[i] * (1 - c[3])).concat(1);
    return base;
  };
  const out = [];
  for (const root of document.querySelectorAll(scope)) {
    for (const el of [root, ...root.querySelectorAll('*')]) {
      if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
      if (el.closest('[hidden], .vh, .skip, option') || el.disabled) continue;
      const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
      if (!r.width || !r.height || cs.visibility === 'hidden') continue;
      const fg = parse(cs.color), bg = bgOf(el);
      if (!fg) continue;
      const a = lum(fg), b = lum(bg), ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
      if (ratio < 4.5) out.push(`${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} "${el.textContent.trim().slice(0, 24)}" ${ratio.toFixed(2)}:1`);
    }
  }
  return out;
}"""
CLIPPED = """() => {
  const out = [];
  for (const el of document.querySelectorAll('body *')) {
    if (el.closest('[hidden], .vh, .skip, svg, canvas, select, option, .ex-guides, .shots, script, style')) continue;
    const cs = getComputedStyle(el);
    if (!/(hidden|clip)/.test(cs.overflowX + ' ' + cs.overflowY)) continue;     // only a box that hides its overflow can clip text
    if (![...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim())) continue;
    if (el.scrollWidth > el.clientWidth + 1 || el.scrollHeight > el.clientHeight + 1)
      out.push(`${el.tagName.toLowerCase()}.${(el.className || '').toString().split(' ')[0]} "${el.textContent.trim().slice(0, 30)}"`);
  }
  return out;
}"""
NAMES = """(scope) => {
  const out = [];
  for (const el of document.querySelectorAll(scope + ' a[href], ' + scope + ' button, ' + scope + ' input:not([type=hidden]), ' + scope + ' select')) {
    if (el.closest('[hidden]')) continue;
    let name = (el.getAttribute('aria-label') || '').trim();
    if (!name && el.getAttribute('aria-labelledby')) name = el.getAttribute('aria-labelledby').split(' ').map((i) => document.getElementById(i)?.textContent || '').join(' ').trim();
    if (!name && el.id) name = [...document.querySelectorAll(`label[for="${el.id}"]`)].map((l) => l.textContent).join(' ').trim();
    if (!name && el.closest('label')) name = el.closest('label').textContent.trim();
    if (!name && !/^(INPUT|SELECT)$/.test(el.tagName)) name = el.textContent.trim();
    if (!name) out.push(el.outerHTML.slice(0, 80));
  }
  return out;
}"""


def goto(page, url, until="load"):
    for timeout in (30000, 90000):     # once more, with a longer wait, if the machine is busy
        try:
            return page.goto(url, wait_until=until, timeout=timeout)
        except Exception as ex:
            err = ex
    bad(f"{urllib.parse.urlparse(url).path}: didn't load ({str(err).splitlines()[0][:80]})")
    return None


def fresh(page, url):
    """A real page load, even when only the #hash differs from the current URL."""
    page.goto("about:blank")
    return goto(page, url, "networkidle")


def watch(page, base):
    """Collects console errors, failed and off-site requests, and dialogs (alert() from injected script) on a page."""
    log = {"errors": [], "failed": [], "offsite": [], "dialogs": []}
    host = urllib.parse.urlparse(base).netloc
    page.on("console", lambda m: log["errors"].append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: log["errors"].append(str(e)))
    page.on("requestfailed", lambda r: log["failed"].append(f"{r.url} ({r.failure})"))
    page.on("response", lambda r: log["failed"].append(f"{r.url} → {r.status}") if r.status >= 400 and "/404-check/" not in r.url else None)
    page.on("request", lambda r: log["offsite"].append(r.url) if urllib.parse.urlparse(r.url).netloc not in (host, "") and not r.url.startswith(("data:", "about:")) else None)
    page.on("dialog", lambda d: (log["dialogs"].append(d.message), d.dismiss()))
    return log


def page_checks(browser, base):
    files = [f for f in html_files() if f != "404.html"]
    urls = [(f, base + BASE + "/" + ("" if f == "index.html" else f.removesuffix("index.html"))) for f in files]
    urls.append(("404.html", base + BASE + "/404-check/deeper/missing.html"))     # GitHub serves 404.html for any missing path
    loads = 0
    for scheme in ("light", "dark"):
        for vw, vh in ((375, 812), (1280, 800)):
            ctx = browser.new_context(viewport={"width": vw, "height": vh}, color_scheme=scheme)
            ctx.add_init_script(INIT)
            page = ctx.new_page()
            log = watch(page, base)
            for rel, url in urls:
                for v in log.values():
                    v.clear()
                resp = goto(page, url, "networkidle" if rel.startswith("explore") else "load")
                if not resp:
                    continue
                loads += 1
                w = f"{rel} @{vw} {scheme}"
                if rel == "404.html":
                    if resp.status != 404 or page.title() != "Page not found | Washington Eats":
                        bad(f"{w}: a missing path didn't get the 404 page with status 404 ({resp.status}, {page.title()!r})")
                elif resp.status != 200:
                    bad(f"{w}: status {resp.status}")
                if rel.startswith("explore"):
                    page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
                over = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                if over > 1:
                    bad(f"{w}: scrolls sideways by {over}px")
                if page.locator("h1").count() != 1:
                    bad(f"{w}: {page.locator('h1').count()} <h1>")
                for v in page.evaluate("window.__csp"):
                    bad(f"{w}: CSP violation: {v}")
                for t in page.evaluate(CLIPPED):
                    bad(f"{w}: clipped text: {t}")
                imgs = page.evaluate("[...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.currentSrc || i.src)")
                problems.extend(f"{w}: image didn't load {u}" for u in imgs)
                problems.extend(f"{w}: console error: {e[:160]}" for e in log["errors"] if "404-check" not in e and "the server responded with a status of 404" not in e)
                problems.extend(f"{w}: failed request {u}" for u in log["failed"])
                problems.extend(f"{w}: request to another host {u}" for u in log["offsite"])
                if vw == 375 and scheme == "light":
                    for t in page.evaluate(TAP):
                        bad(f"{w}: tap target under 24px: {t}")
                if rel in ("index.html", "washington-teriyaki.html", "cities/seattle.html", "cities/wenatchee.html", "privacy.html", "404.html") and vw == 375:
                    for t in page.evaluate(CONTRAST, "header.site, main, footer"):
                        bad(f"{w}: text contrast under 4.5:1: {t}")
                if SHOTS and rel in ("index.html", "washington-teriyaki.html", "cities/seattle.html", "cities/wenatchee.html", "privacy.html", "404.html", "explore/index.html"):
                    os.makedirs(SHOTS, exist_ok=True)
                    page.screenshot(path=os.path.join(SHOTS, f"{rel.replace('/', '_').replace('.html', '')}-{vw}-{scheme}.png"))
            ctx.close()
    return loads


def rows(page):
    return page.evaluate("[...document.querySelectorAll('.ex-row')].map(r => r.innerText.replace(/\\s+/g, ' '))")


def count(page):
    m = re.match(r"([\d,]+) place", page.locator("#ex-count").text_content() or "")
    return int(m.group(1).replace(",", "")) if m else -1


def search(page, q):
    page.locator("#ex-q").fill(q)
    page.wait_for_timeout(450)


def lonlat_px(page, lat, lon):
    """Where explore.js draws a place on the canvas before any pan or zoom (its fitCam and proj)."""
    return page.evaluate("""([la, lo]) => {
      const cv = document.querySelector('#ex-map');
      cv.scrollIntoView({ block: 'center', behavior: 'instant' });   // the site scrolls smoothly; measure where it lands, not mid-way
      const b = cv.getBoundingClientRect(), w = cv.clientWidth, h = cv.clientHeight;
      const LAT0 = 47.3, KX = Math.cos(LAT0 * Math.PI / 180), proj = (lo, la) => [(lo + 120) * KX, -(la - LAT0)];
      const [x0, y0] = proj(-124.8, 49.05), [x1, y1] = proj(-116.9, 45.5);
      const k = Math.min(w / (x1 - x0), h / (y1 - y0)) * 0.95, cx = (w - (x1 - x0) * k) / 2 - x0 * k, cy = (h - (y1 - y0) * k) / 2 - y0 * k;
      const [x, y] = proj(lo, la); return [b.left + x * k + cx, b.top + y * k + cy, w, h];
    }""", [lat, lon])


PLACEHOLDER = """() => {
  // the placeholder's own width: the same text as the value of a plain text field with the search box's computed font, padding,
  // border and width (in the search box itself a value brings a clear button that an empty box doesn't show), so scrollWidth >
  // clientWidth means the hint is cut off
  const i = document.querySelector('#ex-q'), cs = getComputedStyle(i), ph = i.placeholder, c = document.createElement('input');
  c.type = 'text';
  for (const k of ['font', 'letterSpacing', 'wordSpacing', 'textIndent', 'boxSizing', 'width', 'paddingLeft', 'paddingRight', 'borderLeftWidth', 'borderRightWidth', 'borderStyle'])
    c.style[k] = cs[k];
  c.style.position = 'absolute'; c.style.visibility = 'hidden';
  i.parentElement.appendChild(c);
  c.value = ph;
  const sw = c.scrollWidth, cw = c.clientWidth, same = Math.abs(c.offsetWidth - i.offsetWidth) <= 1;
  c.remove();
  return { ph, sw, cw, same, px: parseFloat(getComputedStyle(i, '::placeholder').fontSize) };
}"""


def placeholder_cut(page):
    """The search box's placeholder fits in the box (California's read "…zip or d" at 375 px) at 16px or more (under that, iOS zooms)."""
    r = page.evaluate(PLACEHOLDER)
    out = []
    if not r["ph"]:
        out.append("the search box has no placeholder")
    if not r["same"]:
        out.append("the placeholder measure didn't copy the search box's width (fix PLACEHOLDER in qa-site.py)")
    if r["sw"] > r["cw"]:
        out.append(f"the search placeholder {r['ph']!r} is cut off ({r['sw']}px of text and padding in a {r['cw']}px box)")
    if r["px"] < 16:
        out.append(f"the search placeholder is {r['px']}px (under 16px)")
    return out


def guide_search_checks(browser, base):
    """A search inside a guide that finds none or only a few offers the same search in All restaurants, with its count, and one click
    shows it there (ME-V08 / WI-V-03: the app opens on Teriyaki, so a first visit typing a famous restaurant found nothing)."""
    ex = base + BASE + "/explore/"
    famous = "Canlis"     # Seattle's best-known fine-dining room: in the data, not on the teriyaki guide
    fi = [i for i in REST if C["n"][i] == famous]
    if not fi or any(i in IN_GUIDE[1] for i in fi):
        bad(f"guide search: pick another famous non-guide place ({famous!r} is {'on the teriyaki guide' if fi else 'not in the data'})")
        return
    for vw, vh, scheme in ((375, 812, "light"), (1280, 800, "dark")):
        w = f"explore @{vw} {scheme} (guide search)"
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, color_scheme=scheme)
        ctx.add_init_script(INIT)
        page = ctx.new_page()
        log = watch(page, base)
        goto(page, ex, "networkidle")     # no hash, nothing stored: the app opens on its first guide, Teriyaki
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        if page.evaluate("document.querySelector('.ex-guides button[aria-pressed=true]')?.dataset.g") != "teriyaki":
            bad(f"{w}: a first visit didn't open on the teriyaki guide")
        search(page, famous.lower())
        btn = page.locator("#ex-widen")
        if page.locator(".ex-row").count() or not btn.count() or not btn.is_visible():
            bad(f"{w}: “{famous.lower()}” in the teriyaki guide listed {page.locator('.ex-row').count()} and offered no All restaurants button: "
                f"{(page.locator('#ex-list').text_content() or '').strip()[:90]!r}")
        else:
            m = re.fullmatch(r"See ([\d,]+) match(?:es)? in All restaurants", (btn.text_content() or "").strip())
            if not m:
                bad(f"{w}: the All restaurants button says {btn.text_content()!r}")
            if vw == 375:
                for t in page.evaluate(TAP):
                    bad(f"{w}: tap target under 24px: {t}")
            for t in page.evaluate(CONTRAST, "#ex-list"):
                bad(f"{w}: text contrast under 4.5:1: {t}")
            btn.click()
            page.wait_for_timeout(300)
            st = page.evaluate("""() => ({ g: document.querySelector('.ex-guides button[aria-pressed=true]')?.dataset.g, q: document.querySelector('#ex-q').value,
                hash: location.hash, focus: document.activeElement?.classList.contains('ex-row') })""")
            if st["g"] != "all" or st["q"] != famous.lower() or "g=all" not in st["hash"]:
                bad(f"{w}: the button didn't switch to All restaurants with the same search: {st}")
            if m and count(page) != int(m.group(1).replace(",", "")):
                bad(f"{w}: the button promised {m.group(1)} matches, All restaurants lists {count(page)}")
            if not any(r.startswith(famous) and CITY(fi[0]) in r for r in rows(page)):
                bad(f"{w}: one click didn't find {famous}: {rows(page)[:2]}")
            if not st["focus"]:
                bad(f"{w}: focus didn't move to the results after the click")
            if page.locator("#ex-widen").count():
                bad(f"{w}: All restaurants still offers to widen the search")
        # a few in the guide and more statewide: the button follows the short list. "seafood" names a few teriyaki-and-seafood
        # shops; checked against the counts the browser shows for both lists, so it can't pass by finding nothing.
        fresh(page, ex + "#g=teriyaki")
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        search(page, "seafood")
        n_guide, btn = count(page), page.locator("#ex-widen")
        offered = btn.text_content() if btn.count() and btn.is_visible() else None
        page.locator('.ex-guides button[data-g="all"]').click()
        page.wait_for_timeout(300)
        n_all = count(page)
        if not 0 < n_guide < 5 or n_all <= n_guide:
            bad(f"{w}: pick another few-matches query (“seafood”: {n_guide} in the teriyaki guide, {n_all} in All restaurants)")
        elif not offered or not re.fullmatch(rf"See {n_all:,} match(?:es)? in All restaurants", offered.strip()):
            bad(f"{w}: “seafood” found {n_guide} in the teriyaki guide and {n_all} in All restaurants, but the guide offered {offered!r}")
        # nothing anywhere: no button, the plain message
        page.locator('.ex-guides button[data-g="teriyaki"]').click()
        search(page, "qqzxv")
        if page.locator("#ex-widen").count() or "No places match" not in (page.locator("#ex-list").text_content() or ""):
            bad(f"{w}: a search nothing matches offered a button or lost its message: {(page.locator('#ex-list').text_content() or '')[:80]!r}")
        problems.extend(f"{w}: CSP violation: {v}" for v in page.evaluate("window.__csp"))
        problems.extend(f"{w}: console error: {e[:160]}" for e in log["errors"])
        ctx.close()


def webapp_checks(browser, base):
    ex = base + BASE + "/explore/"
    kas = next(i for i in range(N) if C["ks"][i] == 1)
    seattle, sf = {"latitude": 47.6062, "longitude": -122.3321}, {"latitude": 37.7749, "longitude": -122.4194}
    for vw, vh in ((375, 812), (1280, 800)):
        w = f"explore @{vw}"
        ctx = browser.new_context(viewport={"width": vw, "height": vh}, geolocation=seattle, permissions=["geolocation"])
        ctx.add_init_script(INIT)
        page = ctx.new_page()
        log = watch(page, base)
        sizes = {}
        page.on("requestfinished", lambda r: sizes.__setitem__(r.url, r.url))
        page.route("**/data/core.json", lambda r: (time.sleep(0.6), r.continue_()))     # the list arrives after first paint
        goto(page, base + BASE + "/", "load")                                            # a page before it, so Back has somewhere to go
        t0 = time.time()
        goto(page, ex, "load")
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        usable = time.time() - t0
        page.wait_for_timeout(1500)
        if page.evaluate("window.__cls") >= 0.05:
            bad(f"{w}: layout shift (CLS) {page.evaluate('window.__cls'):.3f} while loading")
        page.unroute("**/data/core.json")
        # what a first visit transfers, gzipped as GitHub Pages serves it
        total = 0
        for u in sizes:
            f = file_for(urllib.parse.urlparse(u).path)
            if f:
                total += len(gzip.compress(open(f, "rb").read(), 6)) if f.endswith((".html", ".json", ".js", ".css", ".svg", ".webmanifest")) else os.path.getsize(f)
        print(f"  {w}: usable in {usable:.1f}s (core.json held 0.6s), first-load transfer ≈ {total / 1e6:.2f} MB gzipped")
        if total > 1_500_000:
            bad(f"{w}: first load transfers {total / 1e6:.2f} MB gzipped (budget 1.5 MB)")
        # the default guide is the data's hand-checked teriyaki shops, and the order never claims "Nearest" without a location
        if count(page) != len(IN_GUIDE[1]):
            bad(f"{w}: the teriyaki guide lists {count(page)}, the data has {len(IN_GUIDE[1])}")
        if "· Nearest" in (page.locator("#ex-count").text_content() or ""):
            bad(f"{w}: says 'Nearest' with no location")
        if vw == 375:
            for t in page.evaluate(TAP):
                bad(f"{w}: tap target under 24px: {t}")
        for t in page.evaluate(NAMES, "body"):
            bad(f"{w}: control without an accessible name: {t}")
        if vw == 375:   # iOS Safari zooms the page when a field under 16px gets focus
            for sel, px in page.evaluate("[...document.querySelectorAll('#ex-q, .ex-row2 select')].map(e => [e.id, parseFloat(getComputedStyle(e).fontSize)])"):
                if px < 16:
                    bad(f"{w}: #{sel} is {px}px, so iOS zooms the page when it gets focus")
        for t in placeholder_cut(page):
            bad(f"{w}: {t}")
        # searches, in All restaurants
        page.locator('.ex-guides button[data-g="all"]').click()
        page.wait_for_timeout(300)
        n_all = count(page)
        if n_all != N_REST:
            bad(f"{w}: All restaurants lists {n_all}, the data has {N_REST}")
        search(page, "toshi's teriyaki grill")
        if not any("Toshi's Teriyaki Grill" in r and "Mill Creek" in r for r in rows(page)):
            bad(f"{w}: “toshi's teriyaki grill” didn't find Kasahara's Mill Creek shop: {rows(page)[:2]}")
        search(page, "spokane")
        r = rows(page)
        if not r or not all("Spokane" in x for x in r[:50]):
            bad(f"{w}: “spokane” listed places outside Spokane: {[x for x in r[:50] if 'Spokane' not in x][:2]}")
        search(page, "pho")
        n_pho = count(page)
        search(page, "phở")
        if n_pho < len(IN_GUIDE[2]) or count(page) != n_pho:
            bad(f"{w}: “pho” found {n_pho} and “phở” {count(page)} (want the same, at least the {len(IN_GUIDE[2])} phở shops)")
        search(page, "main st")
        if count(page) < 20:
            bad(f"{w}: “main st” found only {count(page)} places")
        else:
            page.locator(".ex-row").first.click()
            page.wait_for_selector("#ex-panel:not([hidden])")
            if not re.search(r"\bMain St\b", page.locator(".ex-addr").text_content() or ""):
                bad(f"{w}: the first “main st” result isn't on a Main St: {page.locator('.ex-addr').text_content()!r}")
            page.keyboard.press("Escape")
        for q in ("🍜", "!!!", "“”‘’"):
            search(page, q)
            if page.locator(".ex-row").count() or not page.locator(".ex-empty").count():
                bad(f"{w}: the search {q!r} listed places instead of saying none match")
        search(page, "")
        if count(page) != n_all:
            bad(f"{w}: clearing the search didn't bring back all {n_all}")
        search(page, '<img src=x onerror="window.__pwn=1">"\'‮')
        if page.evaluate("window.__pwn") or page.locator("img[src=x]").count() or log["dialogs"]:
            bad(f"{w}: markup typed into the search box ran")
        search(page, "")
        # filters (teriyaki guide): town, kind, Hide chains, Clear
        page.locator('.ex-guides button[data-g="teriyaki"]').click()
        page.locator("#ex-town").select_option("Tacoma")
        page.wait_for_timeout(300)
        want = sum(1 for i in IN_GUIDE[1] if CITY(i) == "Tacoma")
        if count(page) != want or not all("Tacoma" in x for x in rows(page)):
            bad(f"{w}: the Tacoma filter shows {count(page)}, the data has {want}")
        page.locator("#ex-clear").click()
        page.wait_for_timeout(200)
        if count(page) != len(IN_GUIDE[1]):
            bad(f"{w}: Clear filters didn't restore the guide")
        page.locator("#ex-chains").check()
        page.wait_for_timeout(200)
        n_chain = sum(1 for i in IN_GUIDE[1] if (C["ch"][i] or 1) >= 5)     # 5+ locations: the app's "Chain" (there are some on the guide)
        if not n_chain or count(page) != len(IN_GUIDE[1]) - n_chain or any("Chain ·" in x for x in rows(page)):
            bad(f"{w}: Hide chains shows {count(page)}, want {len(IN_GUIDE[1]) - n_chain} (the data has {n_chain} chain shops on the guide)")
        page.locator("#ex-chains").uncheck()
        kind = page.evaluate("document.querySelector('#ex-cuisine').options[1].value")
        page.locator("#ex-cuisine").select_option(kind)
        page.wait_for_timeout(200)
        want = sum(1 for i in IN_GUIDE[1] if CORE["cuisines"][C["cu"][i]] == kind)
        if count(page) != want:
            bad(f"{w}: the {kind!r} filter shows {count(page)}, the data has {want}")
        page.locator("#ex-clear").click()
        # the place panel: a labelled modal dialog with the data's own facts; Escape and Back close it
        search(page, "toshi's teriyaki grill")
        page.locator(".ex-row").first.click()
        page.wait_for_function("() => document.querySelector('#ex-panel .ex-sec')", timeout=30000)
        page.wait_for_timeout(300)
        st = page.evaluate("""() => { const p = document.querySelector('#ex-panel'); return { role: p.getAttribute('role'), modal: p.getAttribute('aria-modal'),
            label: document.getElementById(p.getAttribute('aria-labelledby'))?.textContent || '', inert: document.querySelector('.wrap').inert,
            focus: document.activeElement?.id, name: document.querySelector('#ex-pname')?.textContent, addr: document.querySelector('.ex-addr')?.textContent,
            site: document.querySelector('#ex-panel a[rel~=nofollow]')?.getAttribute('href') || null,
            tel: [...document.querySelectorAll('#ex-panel a[href^="tel:"]')].map(a => a.getAttribute('href'))[0] || null,
            text: p.innerText }; }""")
        if st["role"] != "dialog" or st["modal"] != "true" or not st["label"] or not st["inert"] or st["focus"] != "ex-close":
            bad(f"{w}: the place panel isn't a labelled modal dialog with the page inert and focus on Close: { {k: st[k] for k in ('role', 'modal', 'inert', 'focus')} }")
        d = DETAIL[kas] or {}
        if st["name"] != C["n"][kas] or C["a"][kas] not in (st["addr"] or "") or st["site"] != d.get("w") \
                or (st["tel"] or None) != ("tel:" + re.sub(r"[^\d+]", "", d["ph"]) if d.get("ph") else None) or "Toshi Kasahara" not in st["text"]:
            bad(f"{w}: the panel for {C['n'][kas]} doesn't show the data's address/phone/website: {st['addr']!r} {st['site']!r} {st['tel']!r}")
        if C["kr"][kas] and KCR[C["kr"][kas]] not in st["text"]:
            bad(f"{w}: the panel lacks King County's rating {KCR[C['kr'][kas]]}")
        if vw == 375:
            for t in page.evaluate(TAP):
                bad(f"{w} (panel open): tap target under 24px: {t}")
        for t in page.evaluate(NAMES, "#ex-panel"):
            bad(f"{w}: panel control without an accessible name: {t}")
        page.keyboard.press("Escape")
        page.wait_for_timeout(300)
        st = page.evaluate("({ hidden: document.querySelector('#ex-panel').hidden, inert: document.querySelector('.wrap').inert, row: document.activeElement?.classList.contains('ex-row'), url: location.href })")
        if not st["hidden"] or st["inert"] or not st["row"] or not st["url"].startswith(ex):
            bad(f"{w}: Escape didn't close the panel, restore the page and return focus to the row: {st}")
        page.locator(".ex-row").first.click()
        page.wait_for_selector("#ex-panel:not([hidden])")
        page.go_back()
        page.wait_for_timeout(500)
        if not page.url.startswith(ex) or page.locator("#ex-panel").is_visible() or page.evaluate("document.querySelector('.wrap').inert"):
            bad(f"{w}: Back with a place open didn't just close it (now at {page.url})")
        elif page.locator("#ex-q").input_value() != "toshi's teriyaki grill":
            bad(f"{w}: Back lost the search")
        page.go_forward()
        page.wait_for_timeout(500)
        if page.locator("#ex-pname").count() == 0 or not page.locator("#ex-panel").is_visible():
            bad(f"{w}: Forward didn't reopen the place")
        else:
            page.keyboard.press("Escape")
        # the skip link is an in-page jump, not app state
        search(page, "teriyaki kent")
        n = count(page)
        page.evaluate("document.querySelector('.skip').focus()")
        page.keyboard.press("Enter")
        page.wait_for_timeout(300)
        if page.locator("#ex-q").input_value() != "teriyaki kent" or count(page) != n:
            bad(f"{w}: the skip link reset the search")
        if n < 1 or not all("Kent" in x for x in rows(page)[:5]):
            bad(f"{w}: “teriyaki kent” didn't list Kent shops first")
        search(page, "")
        # Near me: inside Washington sorts by distance
        page.locator("#ex-locate").click()
        page.wait_for_timeout(800)
        dist = [float(m.group(1)) for x in rows(page)[:30] for m in [re.search(r"([\d.]+) mi away", x)] if m]
        if len(dist) < 20 or dist != sorted(dist) or "Sorted by distance" not in page.locator("#ex-locmsg").text_content():
            bad(f"{w}: Near me in Seattle didn't sort by distance: {dist[:5]}")
        # every press asks for a fresh fix (the playbook's rule): after a move to Spokane, pressing Near me again re-sorts from there
        spokane = (47.6588, -117.4260)
        rad = math.radians
        hav = lambda i: math.asin(math.sqrt(math.sin(rad(C["la"][i] - spokane[0]) / 2) ** 2 + math.cos(rad(spokane[0])) * math.cos(rad(C["la"][i])) * math.sin(rad(C["lo"][i] - spokane[1]) / 2) ** 2))
        near_spokane = C["n"][min((i for i in IN_GUIDE[1] if C["la"][i] is not None), key=hav)]
        ctx.set_geolocation({"latitude": spokane[0], "longitude": spokane[1]})
        if not page.locator("#ex-locate").is_visible():
            bad(f"{w}: Near me is gone after the first fix, so a second press can't ask for a fresh one")
        else:
            page.locator("#ex-locate").click()
            page.wait_for_timeout(800)
            if not (rows(page) or [""])[0].startswith(near_spokane):
                bad(f"{w}: after moving to Spokane, Near me didn't re-sort from there: first row {(rows(page) or [''])[0][:40]!r}, want {near_spokane!r}")
        ctx.set_geolocation(seattle)
        # the map draws, and a dot opens its place
        page.locator('.ex-guides button[data-g="drivein"]').click()
        page.locator('.ex-view button[data-v="map"]').click()
        page.wait_for_timeout(1200)
        painted = page.evaluate("""() => { const c = document.querySelector('#ex-map'), d = c.getContext('2d').getImageData(0, 0, c.width, c.height).data;
            let n = 0; for (let i = 3; i < d.length; i += 4 * 7) if (d[i]) n++; return n; }""")
        if painted < 500:
            bad(f"{w}: the map didn't draw")
        # Near me centred the map on Seattle; reload the map view fresh so it's the whole state, then click the loneliest drive-in
        fresh(page, ex + "#g=drivein")
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        page.locator('.ex-view button[data-v="map"]').click()
        page.wait_for_timeout(1000)
        pts = [(i, lonlat_px(page, C["la"][i], C["lo"][i])) for i in IN_GUIDE[8] if C["la"][i] is not None]
        lonely = max(pts, key=lambda a: min((math.dist(a[1][:2], b[1][:2]) for b in pts if b is not a), default=0))
        page.mouse.click(lonely[1][0], lonely[1][1])
        page.wait_for_timeout(500)
        got = page.locator("#ex-pname").text_content() if page.locator("#ex-pname").count() and page.locator("#ex-panel").is_visible() else None
        if got != C["n"][lonely[0]]:
            bad(f"{w}: clicking {C['n'][lonely[0]]}'s dot opened {got!r}")
        page.keyboard.press("Escape")
        page.locator('.ex-view button[data-v="list"]').click()
        # Save survives a reload, under the wae- prefix
        page.locator(".ex-row").first.click()
        page.wait_for_selector("#ex-save")
        name = page.locator("#ex-pname").text_content()
        page.locator("#ex-save").click()
        page.keyboard.press("Escape")
        keys = page.evaluate("Object.keys(localStorage)")
        if not keys or any(not k.startswith(STORAGE_PREFIX) for k in keys):
            bad(f"{w}: localStorage keys {keys} (all should start {STORAGE_PREFIX!r}; the origin is shared with other state sites)")
        fresh(page, ex + "#g=saved")
        page.wait_for_function("() => document.querySelector('.ex-row, .ex-empty')", timeout=60000)
        if name not in (page.locator("#ex-list").text_content() or ""):
            bad(f"{w}: a saved place wasn't in Saved after a reload")
        # a #p= link opens the right place on a fresh load
        fresh(page, ex + f"#p={C['id'][kas]}")
        page.wait_for_timeout(600)
        if (page.locator("#ex-pname").text_content() if page.locator("#ex-pname").count() else None) != C["n"][kas]:
            bad(f"{w}: #p={C['id'][kas]} didn't open {C['n'][kas]}")
        # hostile hashes and a junk stored guide
        for h in ("#g=constructor", "#g=__proto__", "#g=toString&sort=__proto__&town=constructor&kind=hasOwnProperty&p=__proto__",
                  "#q=%3Cimg%20src%3Dx%20onerror%3Dwindow.__pwn%3D1%3E", "#q=%22%3E%3Cscript%3Ewindow.__pwn%3D1%3C%2Fscript%3E&town=%3Cb%3E",
                  "#q=%E2%80%AEkcab&g=all", "#p=%3Csvg%2Fonload%3Dalert(1)%3E"):
            log["errors"].clear()
            fresh(page, ex + h)
            page.wait_for_timeout(300)
            if log["errors"] or log["dialogs"] or page.evaluate("window.__pwn") or page.locator("img[src=x], #ex-list script, #ex-list svg, #ex-panel svg, #ex-count b, #ex-sub b").count() \
                    or not re.match(r"[\d,]+ places? ·", page.locator("#ex-count").text_content() or ""):
                bad(f"{w}: the hash {h} broke the web app or ran markup: {log['errors'][:1]} {log['dialogs'][:1]}")
        page.evaluate(f"localStorage.setItem('{STORAGE_PREFIX}guide', JSON.stringify('__proto__'))")
        fresh(page, ex)
        page.wait_for_timeout(300)
        if not page.locator(".ex-row").count():
            bad(f"{w}: a junk stored guide broke the web app")
        # any page on the shared github.io origin can write these keys: bad JSON, a non-array or junk entries must not stop the app
        for key, val in (("saved", '{"x":1}'), ("saved", "not json"), ("saved", "5"), ("saved", "[null, 5, {}]"), ("guide", '{"x":1}')):
            log["errors"].clear()
            page.evaluate(f"localStorage.setItem('{STORAGE_PREFIX}{key}', {json.dumps(val)})")
            fresh(page, ex if key == "guide" else ex + "#g=teriyaki")     # no hash for the guide case: the stored value is what loads
            page.wait_for_timeout(300)
            if log["errors"] or not page.locator(".ex-row").count():
                bad(f"{w}: a stored {STORAGE_PREFIX}{key} of {val} broke the web app: {log['errors'][:1]}")
                continue
            if key == "saved":
                page.locator(".ex-row").first.click()
                page.wait_for_selector("#ex-save")
                page.locator("#ex-save").click()
                page.keyboard.press("Escape")
                kept = page.evaluate(f"JSON.parse(localStorage.getItem('{STORAGE_PREFIX}saved'))")
                if not isinstance(kept, list) or not kept or not all(isinstance(x, str) for x in kept):
                    bad(f"{w}: after a stored {STORAGE_PREFIX}saved of {val}, Save wrote {kept!r} (want a list of place ids)")
        page.evaluate(f"localStorage.removeItem('{STORAGE_PREFIX}saved'); localStorage.removeItem('{STORAGE_PREFIX}guide')")
        # keyboard: the skip link comes first and every stop shows a focus ring
        fresh(page, ex)
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        page.keyboard.press("Tab")
        first = page.evaluate("({ cls: document.activeElement.className, left: document.activeElement.getBoundingClientRect().left })")
        if first["cls"] != "skip" or first["left"] < 0:
            bad(f"{w}: the first Tab stop isn't a visible skip link: {first}")
        for _ in range(28):
            page.keyboard.press("Tab")
            ring = page.evaluate("""() => { const e = document.activeElement, cs = getComputedStyle(e);
              return { el: e.tagName + (e.id ? '#' + e.id : '') + ' ' + (e.textContent || '').trim().slice(0, 20),
                       ok: (cs.outlineStyle !== 'none' && parseFloat(cs.outlineWidth) > 0) || cs.boxShadow !== 'none' }; }""")
            if not ring["ok"]:
                bad(f"{w}: no visible focus on {ring['el']}")
                break
        problems.extend(f"{w}: CSP violation: {v}" for v in page.evaluate("window.__csp"))
        problems.extend(f"{w}: console error: {e[:160]}" for e in log["errors"])
        problems.extend(f"{w}: request to another host {u}" for u in log["offsite"])
        ctx.close()
    # Near me outside Washington, and denied
    for geo, perm, want in ((sf, ["geolocation"], "outside Washington"), (None, [], "Location is off"), ("timeout", [], "Couldn't get a fix")):
        ctx = browser.new_context(viewport={"width": 375, "height": 812}, geolocation=None if geo == "timeout" else geo, permissions=perm)
        if geo == "timeout":    # the browser never gets a fix: getCurrentPosition fails with TIMEOUT (code 3)
            ctx.add_init_script("navigator.geolocation.getCurrentPosition = (ok, fail) => setTimeout(() => fail({ code: 3, message: 'timeout' }), 50);")
        page = ctx.new_page()
        goto(page, ex, "networkidle")
        page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
        page.locator("#ex-locate").click()
        page.wait_for_timeout(1500)
        msg = page.locator("#ex-locmsg").text_content() or ""
        if want not in msg:
            bad(f"explore (location {'timed out' if geo == 'timeout' else 'denied' if not perm else 'in San Francisco'}): says {msg!r}, want “{want}”")
        if not perm and "· Nearest" in (page.locator("#ex-count").text_content() or ""):
            bad(f"explore (location {'timed out' if geo == 'timeout' else 'denied'}): claims 'Nearest'")
        ctx.close()
    # a failed core.json is reported where the list would be
    ctx = browser.new_context(viewport={"width": 375, "height": 812})
    page = ctx.new_page()
    page.route("**/data/core.json", lambda r: r.abort())
    goto(page, ex, "networkidle")
    page.wait_for_timeout(500)
    if "couldn" not in (page.locator("#ex-loading").text_content() or ""):
        bad("explore: a failed core.json wasn't reported")
    ctx.close()
    # prefers-reduced-motion turns smooth scrolling off
    for motion, want in (("reduce", "auto"), ("no-preference", "smooth")):
        ctx = browser.new_context(reduced_motion=motion)
        page = ctx.new_page()
        goto(page, base + BASE + "/", "load")
        if page.evaluate("getComputedStyle(document.documentElement).scrollBehavior") != want:
            bad(f"reduced motion {motion}: scroll-behavior isn't {want}")
        ctx.close()
    # contrast of the web app's controls, list, map hint and panel, light and dark
    for scheme in ("light", "dark"):
        ctx = browser.new_context(viewport={"width": 375, "height": 812}, color_scheme=scheme)
        page = ctx.new_page()
        for h in ("#g=honors", "#g=safety", "#g=teriyaki"):
            fresh(page, ex + h)
            page.wait_for_function("() => document.querySelectorAll('.ex-row').length > 0", timeout=60000)
            for t in page.evaluate(CONTRAST, "header.site, .ex-controls, #ex-list"):
                bad(f"explore{h} ({scheme}): text contrast under 4.5:1: {t}")
        page.locator('.ex-view button[data-v="map"]').click()
        page.wait_for_timeout(300)
        for t in page.evaluate(CONTRAST, ".ex-view, #ex-maphint, .ex-zoom"):
            bad(f"explore map ({scheme}): text contrast under 4.5:1: {t}")
        page.locator('.ex-view button[data-v="list"]').click()
        fresh(page, ex + f"#p={C['id'][kas]}")
        page.wait_for_function("() => document.querySelector('#ex-panel .ex-sec')", timeout=30000)
        page.locator("#ex-save").click()
        page.wait_for_timeout(200)
        for t in page.evaluate(CONTRAST, "#ex-panel"):
            bad(f"explore panel ({scheme}): text contrast under 4.5:1: {t}")
        if SHOTS:
            page.screenshot(path=os.path.join(SHOTS, f"explore-panel-375-{scheme}.png"))
        ctx.close()


def main():
    files, parsed = static_checks()
    n_static = len(problems)
    loads = 0
    if not STATIC_ONLY:
        from playwright.sync_api import sync_playwright
        srv, base = serve()
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome")
            loads = page_checks(browser, base)
            webapp_checks(browser, base)
            guide_search_checks(browser, base)
            browser.close()
        srv.shutdown()
    print(f"static: {len(files)} HTML files, {n_static} problems" + ("" if STATIC_ONLY else f" | browser: {loads} page loads (375 and 1280 px, light and dark), plus the web app"))
    for p in problems:
        print("  ✗", p)
    print("OK" if not problems else f"{len(problems)} problems")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
