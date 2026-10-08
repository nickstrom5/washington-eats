"""Checks every website link the app ships before it ships, because map listings carry stale and hijacked domains.

Chicago found about 3% of its listing websites redirected to gambling, betting or adult sites, including a starred restaurant's.
A link survives only if:
  - the final response is 2xx,
  - it stays on the same registered domain (or the page plainly belongs to the place),
  - the page mentions a distinctive word of the place's name,
  - and nothing looks like gambling spam, adult content, a parked or for-sale domain, an expired account or "coming soon".
A site that blocks the check, times out or errors is dropped too: no link beats a wrong link. The one exception is a chain's own
domain (mcdonalds.com for McDonald's): when its sample pages refuse the check (403, 429, connection refused), the links stay, because
the domain plainly belongs to the brand.

Polite by design: an honest user agent, one request at a time per host, and three sample pages for a chain's own domain (5+ places,
80%+ one brand). Shared hosts (Square, Wix, Linktree, Instagram) carry many unrelated places, so every link there is checked on its own.
Never bypasses bot protection.

Usage: ../.venv/bin/python check_websites.py   (reads data/wa/website_candidates.json) → data/wa/website_check.json ({url: {"ok": bool, "why": str, "final": str}})
The app export (washington.py, WA_APP=1) drops every link that isn't ok. Re-run before each App Store submission.
Copied from wi-eats/pipeline/check_websites.py; Washington adds tribal casino names and a "not affiliated" rule (toshisgrill.com has a page
for each unrelated "Toshi's Teriyaki" saying so, and copycat sites call themselves "unofficial").
"""
import collections
import json
import os
import re
import threading
import time
import unicodedata
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

ROOT = os.path.join(os.path.dirname(__file__), "..")
OUT = f"{ROOT}/data/wa/website_check.json"
UA = "WashingtonEatsLinkCheck/1.0 (+https://washington.eatsranked.com/; work-with-nick@gmail.com)"
GENERIC = set("""the and of a an at on in restaurant restaurants bar bars grill grille cafe caffe coffee pizza pizzeria pub tavern house
supper club inn lounge kitchen bistro eatery diner bakery deli market express food foods co company inc llc ltd corp wa washington
seattle tacoma spokane teriyaki pho espresso family original new old north south east west st saint mt sports place spot shop shoppe taproom brewing brewery
tap taps bbq barbecue burger burgers chicken subs sub sandwich sandwiches tacos taco mexican chinese thai sushi asian italian
american cuisine catering events city downtown village""".split())
# Hijacked domains carry Indonesian slot and lottery spam, Turkish betting pages or porn links: any of these marks a page.
SPAM = re.compile(r"slot ?gacor|situs (?:slot|judi|togel)|slot online|\bslot ?88\b|\btogel\b|judi (?:online|bola|slot|qq|poker)|perjudian|"
                  r"bandar ?(?:slot|qq|togel)|\bmaxwin\b|\brtp slot|\bsbobet\b|\bbahis|casino siteleri|\b1win\b|watch porn|free porn|"
                  r"porn videos?|\bpornhub\b|\bxvideos\b|\bxnxx\b|escort service|adult dating|sex cam|camgirl", re.I)
BLOBS = re.compile(r"[A-Za-z0-9+/=_-]{100,}")   # base64 images and tokens: random letters spell anything
# Words a real casino's restaurant or a brewery near the sportsbook uses too: they count only in the page title or description,
# or repeated in the body, and never on a casino's own page.
BETTING = re.compile(r"online casino|casino online|deposit bonus|sportsbook|\bbaccarat\b|bet365|no deposit", re.I)
HEAD = re.compile(r"<title[^>]*>(.*?)</title>|<meta[^>]+name=.description.[^>]+content=\"([^\"]*)", re.S)
# what a page calls itself: its title and its og:title / og:site_name
TITLE = re.compile(r"<title[^>]*>(.*?)</title>|<meta[^>]+property=.og:(?:title|site_name).[^>]+content=\"([^\"]*)", re.S | re.I)
LOGIN = re.compile(r"/(?:login|log-in|signin|sign-in|accounts/login)(?:[/.?]|$)", re.I)
CASINO_PLACE = re.compile(r"casino|gaming|tulalip|muckleshoot|snoqualmie|emerald queen|puyallup tribe|swinomish|little creek|northern quest|"
                          r"kalispel|ilani|cowlitz tribe|suquamish|clearwater|7 cedars|seven cedars|jamestown s.klallam|lucky eagle|red wind|"
                          r"nisqually|angel of the winds|stillaguamish|quil ceda|legends casino|yakama|coulee|12 tribes|mill bay|chewelah|"
                          r"spokane tribe|shoalwater|quinault|skagit valley casino|upper skagit", re.I)
NOT_OURS = re.compile(r"(?:is|are) no longer affiliated with us|not affiliated with (?:the |this )?restaurant|unofficial (?:web ?site|page)|"
                      r"not the official (?:web ?site|page)|this is not an official|is not owned by (?:the |this )?restaurant", re.I)
PARKED = re.compile(r"domain (?:is|may be) for sale|buy this domain|this domain is parked|parked free|sedoparking|hugedomains|"
                    r"afternic|domain has expired|this domain name has expired|account (?:has been )?suspended|website coming soon|"
                    r"site (?:is )?coming soon|future home of|launching soon|godaddy\.com/domainsearch|dan\.com", re.I)
# directories, listings, review sites, shorteners and fundraisers: not the place's own page
BAD_HOSTS = ("business.site", "negocio.site", "google.com", "goo.gl", "g.co/", "share.google", "yelp.com", "tripadvisor.",
             "facebook.com/pages", "doordash.com", "grubhub.com", "ubereats.com", "seamless.com", "allmenus.com", "menupix.com",
             "zmenu.com", "restaurantji.com", "yellowpages.com", "superpages.com", "whitepages.com", "chamberofcommerce.com",
             "cortera.com", "dandb.com", "bizapedia.com", "city-data.com", "mapquest.com", "citysearch.com", "yahoo.com", "hub.biz",
             "edan.io", "poi.place", "placeweb.site", "jany.io", "lany.io", "keeq.io", "restoguides.com", "dinehere.us", "foodspot.com",
             "gastrobars.com", "indulgery.com", "clubplanet.com", "restaurant.com", "groupon.com", "seatgeek.com", "opentable.com",
             "menuism.com", "barfinder.com", "friendseat.com", "local.com", "usplaces.com", "foodeist.com", "jmaps.net", "kwickmenu.com",
             "tinyurl.com", "bit.ly", "forms.gle", "gofund.me", "gofundme.com", "cash.app", "tiktok.com", "reverbnation.com",
             "resy.com", "exploretock.com", "sevenrooms.com",   # booking widgets are not a place's own page
             # 2026-10-07 review: redirect wrappers, payment, fundraising, event, video and job pages, and ad-feed/parking hosts
             "l.facebook.com", "lm.facebook.com", "l.instagram.com", "paypal.com", "paypal.me", "venmo.com", "fundrazr.com",
             "eventbrite.", "ticketmaster.", "youtube.com", "youtu.be", "spotify.com", "linkedin.com", "indeed.com", "bnsf.com",
             "searchesinteractive.com", "site17.com", "zipweb.com", "seahawks.com", "airbnb.com", "discord.com", "discord.gg",
             "paperlesspost.com", "zip-codes.com", "facebook.com/permalink.php", "facebook.com/story.php", "facebook.com/groups/",
             "facebook.com/events/", "://foe.com", "www.foe.com",
             "wa.me/", "whatsapp.com", "squareup.com/gift/", "book.squareup.com")   # chat links, gift-card and booking pages   # foe.com is the Eagles' national site, not a local aerie's
SHADY = re.compile(r"(?:^|\.)food\d+\.com$|\.top$")   # food73.com-style listing farms, .top redirect farms
# a brand that moved its stores to a short domain
ALIASES = {"burgerking.com": "bk.com"}
BLOCKED = re.compile(r"^(?:http 40[39]|http 429|error: (?:ConnectionError|ConnectTimeout|ReadTimeout))$")


def norm(s):
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", " ", s.replace("'", "")).strip()


def regdom(host):
    parts = host.lower().removeprefix("www.").split(".")
    if len(parts) >= 3 and parts[-2] in ("co", "com", "org", "net") and len(parts[-1]) == 2:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def bad_host(url):
    return any(b in url.lower() for b in BAD_HOSTS) or bool(SHADY.search(regdom(urllib.parse.urlparse(url).netloc)))


def _towns():
    """Washington town names: "Joy's Sedro Woolley Bakery" is told apart by "joys", not by a town a history journal also names."""
    try:
        return {w for c in json.load(open(f"{ROOT}/data/app/places.json"))["cities"] for w in norm(c).split()}
    except (OSError, KeyError, ValueError):
        return set()


TOWNS = _towns()


def words(name):
    return [w for w in norm(name).split() if len(w) >= 4 and w not in GENERIC and w not in TOWNS]


STOP = {"the", "and", "of", "a", "an", "at", "on", "in", "by", "to", "for", "co", "inc", "llc"}


def name_words(name):
    """The distinctive words, or for a name made only of common words ("The Fan Club Sports Bar") all its words of 3+ letters."""
    return words(name) or [w for w in norm(name).split() if len(w) >= 3 and w not in STOP]


def ad_feed(url):
    """Parking and ad-feed pages carry the domain they were reached from in the query (searchesinteractive.com?dn=...)."""
    return bool(re.search(r"(?:^|&)(?:dn|domain|domainname|kw)=", urllib.parse.urlsplit(url).query, re.I))


def host_path(url):
    s = urllib.parse.urlsplit(url)
    return norm(s.netloc + " " + s.path)


def compact(s):
    return re.sub(r"[^a-z0-9]", "", norm(s))


def lead(name):
    """The name's first two words run together ("Aki Sushi & Ramen" -> "akisushi"): domains are usually spelled from the start of the name."""
    return compact(" ".join(norm(name).replace(" and ", " ").split()[:2]))


def head(name):
    """The name's first distinctive word: "happy" in Happy Time Bar and Grill. Matching any word let tacotime.com pass on "time"."""
    ws = name_words(name)
    return ws[0] if ws else ""


def own_address(name, url):
    """The link's address carries the place's name: its first distinctive word in the host or path, or a domain spelled from the
    name's start."""
    if head(name) and head(name) in host_path(url):
        return True
    host = compact(urllib.parse.urlsplit(url).netloc.lower().removeprefix("www.").rsplit(".", 1)[0])
    lw = lead(name)
    return (len(lw) >= 5 and lw in host) or (len(host) >= 6 and host in compact(name))


def own_title(name, title):
    return bool(head(name)) and head(name) in norm(title) or (len(lead(name)) >= 5 and lead(name) in compact(title))


host_locks = collections.defaultdict(threading.Lock)
session = requests.Session()
session.headers.update({"User-Agent": UA, "Accept": "text/html,*/*;q=0.5", "Accept-Language": "en-US"})


def check(url, name):
    u = url if url.startswith("http") else "https://" + url
    host = urllib.parse.urlparse(u).netloc.lower()
    if bad_host(u):
        return {"ok": False, "why": "directory or Google link", "final": u}
    with host_locks[regdom(host)]:
        try:
            r = session.get(u, timeout=(8, 15), allow_redirects=True, stream=True)
            body = r.raw.read(400_000, decode_content=True).decode(r.encoding or "utf-8", "ignore") if r.ok else ""
            final = r.url
            r.close()
        except Exception as e:
            return {"ok": False, "why": "error: " + type(e).__name__, "final": u}
        finally:
            time.sleep(0.3)
    if not r.ok:
        return {"ok": False, "why": f"http {r.status_code}", "final": final}
    text = BLOBS.sub(" ", body).lower()
    head = " ".join(a or b for a, b in HEAD.findall(text[:60_000]))
    casino = CASINO_PLACE.search(name) or CASINO_PLACE.search(urllib.parse.urlparse(final).netloc)
    if SPAM.search(text) or SPAM.search(final) or (not casino and (BETTING.search(head) or len(BETTING.findall(text)) >= 2)):
        return {"ok": False, "why": "gambling or adult content", "final": final}
    if PARKED.search(text[:60_000]):
        return {"ok": False, "why": "parked, expired or coming soon", "final": final}
    if NOT_OURS.search(text):
        return {"ok": False, "why": "page says it isn't the place's own", "final": final}
    if bad_host(final):
        return {"ok": False, "why": "redirects to a directory", "final": final}
    if ad_feed(final):
        return {"ok": False, "why": "parked, expired or coming soon", "final": final}
    if LOGIN.search(urllib.parse.urlsplit(final).path):
        return {"ok": False, "why": "a login page", "final": final}
    # the page text and the site's own host and path, never the query: an ad feed's ?dn=thetwindragon.com isn't the place mentioning itself
    ws = name_words(name)
    page = norm(re.sub(r"<script.*?</script>|<style.*?</style>", " ", body, flags=re.S)) + " " + host_path(final)
    mentions = bool(ws) and any(w in page for w in ws)
    same = regdom(urllib.parse.urlparse(final).netloc) in (regdom(host), ALIASES.get(regdom(host)))
    if not mentions:
        return {"ok": False, "why": "page doesn't mention the place", "final": final}
    if not same and not any(w in norm(urllib.parse.urlparse(final).netloc) for w in ws):
        return {"ok": False, "why": "moved to another domain", "final": final}
    # When the address doesn't carry the name, the page has to call itself by it: a directory, a news story, a bank branch or a chain's
    # site that merely mentions the place in its text isn't the place's own page (2026-10-07 review: Japan Teriyaki -> burgerking.com).
    if not own_address(name, final) and not own_title(name, " ".join(a or b for a, b in TITLE.findall(body[:200_000]))):
        return {"ok": False, "why": "name only in the page text, not its title", "final": final}
    return {"ok": True, "why": "ok", "final": final}


def main():
    # every link the export considered (written by wisconsin.py, WI_APP=1), so a link dropped last time gets another chance
    cands = json.load(open(f"{ROOT}/data/wa/website_candidates.json"))
    jobs = collections.defaultdict(list)   # registered domain -> [(url, name)]
    for w, name in cands.items():
        u = w if w.startswith("http") else "https://" + w
        jobs[regdom(urllib.parse.urlparse(u).netloc)].append((w, name))
    prev = json.load(open(OUT)) if os.path.exists(OUT) else {}
    # chain verdicts are recomputed every run; host rules may have grown since a page was fetched
    prev = {u: v for u, v in prev.items() if not v["why"].startswith(("chain domain", "brand's own"))
            and v["why"] not in ("moved to another domain", "gambling or adult content")}
    todo, chain_hosts, brand_of = [], {}, {}
    for dom, items in jobs.items():
        uniq = list(dict.fromkeys(items))
        top, n = collections.Counter(name for _, name in uniq).most_common(1)[0]
        if len(uniq) >= 5 and n >= 0.8 * len(uniq):   # a chain's own domain: three samples stand for all of that brand's links
            mine = [(u, nm) for u, nm in uniq if nm == top]
            chain_hosts[dom] = [u for u, _ in mine]
            brand_of[dom] = top
            # other names on the chain's domain (a teriyaki shop whose listing points at subway.com) are checked one by one
            todo += mine[:3] + [(u, nm) for u, nm in uniq if nm != top]
        else:
            todo += uniq
    for u, v in prev.items():   # host rules apply to cached pages too, no request needed
        if v["ok"] and (bad_host(u) or bad_host(v["final"])):
            prev[u] = {"ok": False, "why": "redirects to a directory", "final": v["final"]}
        elif v["ok"] and ad_feed(v["final"]):
            prev[u] = {"ok": False, "why": "parked, expired or coming soon", "final": v["final"]}
    # Rule change 2026-10-07: a name word in the URL's query no longer counts as the page mentioning the place, and a name without a
    # distinctive word needs one of its words on the page. Passes cached before then whose host and path don't carry a name word are
    # fetched again (the cache keeps verdicts, not pages).
    for u, v in list(prev.items()):
        if u in cands and v.get("rule", 1) < 5 and (v["ok"] and not own_address(cands[u], v["final"])
                                                    or v["why"] == "name only in the page text, not its title"):
            del prev[u]   # rules 3-4 (2026-10-07/08): such a page must call itself by the name; town words don't count
    todo = [(u, n) for u, n in todo if u not in prev]
    print(f"{sum(len(v) for v in jobs.values())} links, {len(jobs)} domains, {len(chain_hosts)} chain domains; checking {len(todo)}")
    results, done = dict(prev), 0
    lock = threading.Lock()

    def run(item):
        nonlocal done
        res = {**check(*item), "rule": 5, "for": item[1]}   # the name the verdict was earned for
        with lock:
            results[item[0]] = res
            done += 1
            if done % 500 == 0:
                print(f"  {done}/{len(todo)}", flush=True)
                json.dump(results, open(OUT, "w"))

    with ThreadPoolExecutor(max_workers=24) as ex:
        list(ex.map(run, todo))
    for dom, urls in chain_hosts.items():
        samples = [results.get(u) for u in urls[:3] if results.get(u)]
        verdict = bool(samples) and sum(s["ok"] for s in samples) >= 2
        why = "chain domain " + ("ok" if verdict else "failed its samples")
        own = any(w in norm(dom) for w in words(brand_of[dom]))
        if not verdict and own and samples and all(s["ok"] or BLOCKED.match(s["why"]) for s in samples):
            verdict, why = True, "brand's own site (blocked the check)"
            for u in urls[:3]:
                results[u] = {**results[u], "ok": True, "why": why}
        for u in urls[3:]:
            results[u] = {"ok": verdict, "why": why, "final": u, "for": brand_of[dom]}
    json.dump(results, open(OUT, "w"), indent=0)
    c = collections.Counter(v["why"] if not v["ok"] else "ok" for v in results.values())
    print("results:", c.most_common())


if __name__ == "__main__":
    main()
