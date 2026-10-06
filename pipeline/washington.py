"""Stage 2: the Washington list -> site/washington.json (web leaderboard) or, with WA_APP=1, data/app/places.json (the App Store build)

Adapted from wi-eats/pipeline/wisconsin.py. Statewide base: Overture Maps listings (stage1.pkl), kept by the rule calibrate.py measured
against King County's food establishment records (calibration.json):
  - artifact: Meta listings and chain store feeds are kept; single sources (Foursquare, BrightQuery, Microsoft) are dropped, and so is
    anything Google (2021) or Overture already shows as closed;
  - app (WA_APP=1): no Google-derived data at all. Meta listings with Overture confidence >= 0.9 and chain store feeds are kept.
Official records: inside King County a listing that matches a business King County inspected in the last 18 months is marked official,
and King County restaurants the map data lacks are added from the records (placed on Overture address points). King County's food
safety rating (Excellent / Good / Okay / Needs to Improve) is shown as published, never recomputed.
Hand-checked guides (teriyaki, honors, oldest places) come from data/research/app/*.json and data/research/jbf_wa.json: each entry has a
2025-26 source. Places the research found closed are removed (data/research/closed*.json).
"""
import os, re, sys, json, math, glob, hashlib, unicodedata, collections
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep
from rapidfuzz import fuzz
from common import (norm_name, nice, name_sim, cuisine, FOOD_COST, MARGIN, MARGIN_CUISINE, SPEND, GENERIC, _stems, DATA, WA, ROOT,
                    canon_city, town_key, street_key, street_nums, CUISINE_RULES, undir, street_eq)
from brands import brand_of
from listings_util import official_match, _close_words
import official as OFFICIAL

APP = os.environ.get("WA_APP") == "1"
SITE = os.environ.get("WA_SITE") or (os.path.join(ROOT, "data", "app") if APP else os.path.join(ROOT, "site"))
GOOD_SOURCES = {"meta", "AllThePlaces", "DAC"}
BASE = {1: 600_000, 2: 1_000_000, 3: 2_200_000, 4: 3_500_000}   # typical yearly sales by price tier (same as Chicago)
B_FIT = 0.764   # review-volume exponent fit on Chicago's published sales (chi-eats meta.model.b)
GENERATED = "2026-10-05"
TAX_CUISINE = {
    "pizza_restaurant": "Pizza", "mexican_restaurant": "Mexican", "taco_restaurant": "Mexican", "texmex_restaurant": "Mexican",
    "sandwich_shop": "Sandwiches & Deli", "delicatessen": "Sandwiches & Deli", "bakery": "Bakery & Sweets", "donut_shop": "Bakery & Sweets",
    "dessert_shop": "Bakery & Sweets", "ice_cream_shop": "Bakery & Sweets", "bagel_shop": "Bakery & Sweets", "cupcake_shop": "Bakery & Sweets",
    "frozen_yogurt_shop": "Bakery & Sweets", "chocolatier": "Bakery & Sweets", "popcorn_shop": "Bakery & Sweets",
    "bar_and_grill_restaurant": "Bar & Pub", "gastropub": "Bar & Pub", "bar": "Bar & Pub", "brewery": "Bar & Pub", "pub": "Bar & Pub",
    "sports_bar": "Bar & Pub", "cocktail_bar": "Bar & Pub", "wine_bar": "Bar & Pub", "dive_bar": "Bar & Pub", "beer_bar": "Bar & Pub",
    "irish_pub": "Bar & Pub", "tiki_bar": "Bar & Pub", "speakeasy": "Bar & Pub", "hookah_bar": "Bar & Pub", "gay_bar": "Bar & Pub",
    "chinese_restaurant": "Chinese", "italian_restaurant": "Italian", "burger_restaurant": "Burgers",
    "breakfast_and_brunch_restaurant": "Breakfast & Diner", "diner": "Breakfast & Diner", "barbecue_restaurant": "BBQ",
    "chicken_restaurant": "Chicken & Wings", "chicken_wings_restaurant": "Chicken & Wings", "sushi_restaurant": "Japanese & Sushi",
    "japanese_restaurant": "Japanese & Sushi", "ramen_restaurant": "Japanese & Sushi", "seafood_restaurant": "Seafood", "poke_restaurant": "Seafood",
    "steakhouse": "Steakhouse", "indian_restaurant": "South Asian", "pakistani_restaurant": "South Asian", "thai_restaurant": "Thai",
    "hot_dog_restaurant": "Hot Dogs", "mediterranean_restaurant": "Mediterranean & Middle Eastern",
    "greek_restaurant": "Mediterranean & Middle Eastern", "middle_eastern_restaurant": "Mediterranean & Middle Eastern",
    "korean_restaurant": "Korean", "vietnamese_restaurant": "Vietnamese", "salad_bar": "Healthy & Vegan", "vegan_restaurant": "Healthy & Vegan",
    "vegetarian_restaurant": "Healthy & Vegan", "health_food_restaurant": "Healthy & Vegan", "coffee_shop": "Coffee & Café", "cafe": "Coffee & Café",
    "coffee_roastery": "Coffee & Café", "smoothie_juice_bar": "Healthy & Vegan", "juice_bar": "Healthy & Vegan", "bubble_tea_shop": "Coffee & Café",
    "tea_room": "Coffee & Café", "soul_food": "Soul & Southern", "southern_american_restaurant": "Soul & Southern",
    "cajun_and_creole_restaurant": "Seafood", "caribbean_restaurant": "Latin & Caribbean", "jamaican_restaurant": "Latin & Caribbean",
    "latin_american_restaurant": "Latin & Caribbean", "cuban_restaurant": "Latin & Caribbean", "puerto_rican_restaurant": "Latin & Caribbean",
    "peruvian_restaurant": "Latin & Caribbean", "african_restaurant": "African", "ethiopian_restaurant": "African",
    "french_restaurant": "German & European", "german_restaurant": "German & European", "polish_restaurant": "German & European",
    "spanish_restaurant": "German & European", "tapas_bar": "German & European", "noodles_restaurant": "Chinese",
    "belgian_restaurant": "German & European", "russian_restaurant": "German & European", "fondue_restaurant": "German & European",
    "scandinavian_restaurant": "German & European", "european_restaurant": "German & European", "eastern_european_restaurant": "German & European",
    "hungarian_restaurant": "German & European", "british_restaurant": "German & European", "dutch_restaurant": "German & European",
    "hawaiian_restaurant": "Hawaiian", "filipino_restaurant": "Filipino", "ukrainian_restaurant": "German & European",
}
TAGS = ["teriyaki", "pho", "oysters", "drivein", "espresso"]


def curated_matcher(frame):
    """A researched place -> row of frame: same street number and street with a similar name; else a near-exact name in the same town;
    else a near-exact name that's unique statewide."""
    by_key = {}
    for i, a in enumerate(frame.street):
        sk = street_key(a)[1]
        for n in street_nums(a):
            if sk:
                by_key.setdefault((n, undir(sk)), []).append((i, sk))
    towns = [canon_city(c).lower() if isinstance(c, str) else "" for c in frame.city]
    ks = list(frame.k.fillna(""))

    def match(c):
        keys = {norm_name(m) for m in (c.get("match_names") or [])} | {norm_name(c["name"])} \
            | {norm_name(re.sub(r"\s*\([^()]*\)\s*", " ", c["name"]))}   # "Kidd Valley (Kenmore)" -> "Kidd Valley"
        keys.discard("")
        _, sk = street_key(c.get("address") or "")
        cands = set()
        for n in street_nums(c.get("address") or ""):
            cands.update(i for i, k2 in by_key.get((n, undir(sk)), []) if street_eq(sk, k2))
        best, bs = None, 0
        for i in cands:
            s_ = max((fuzz.token_set_ratio(m, ks[i]) for m in keys), default=0)
            if s_ >= 60 and s_ > bs:
                best, bs = i, s_
        if best is None:
            ctown = (canon_city(c.get("city") or "") or "").lower()
            sim = [max(fuzz.ratio(m, k) for m in keys) if k else 0 for k in ks]
            hits = [i for i, s_ in enumerate(sim) if s_ >= 90 and towns[i] == ctown]
            if not hits and not c.get("chain"):   # a chain's name repeats statewide: only its own town counts
                hits = [i for i, s_ in enumerate(sim) if s_ >= 97]
            if len(hits) == 1:
                best = hits[0]
        return best
    return match


def pct(s):
    return (s.rank(pct=True) * 100).round(1)


o = pd.read_pickle(f"{WA}/stage1.pkl")
G = pd.read_pickle(f"{WA}/google21.pkl")
if APP:   # the App Store build ignores every Google 2021 match
    o["in21"] = False; o["closed21"] = False; o["gi"] = np.nan
calib = json.load(open(f"{WA}/calibration.json"))
areas = json.load(open(f"{WA}/calib_areas.json"))
KING = prep(shape(areas["King County|county"]).buffer(0.0003))
o["area"] = ["king" if KING.contains(Point(x, y)) else None for x, y in zip(o.lon, o.lat)]

# ---------------------------------------------------------------- official records: King County businesses inspected in the last 18 months
F0 = pd.read_pickle(f"{WA}/official.pkl")
F = F0[(F0.jur == "king") & F0.active].reset_index(drop=True)
KB = OFFICIAL.king_businesses().set_index("business_id")
o["off"] = np.nan
sel = o.index[o.area == "king"]
m = official_match(o.loc[sel].reset_index(drop=True), F)
for i, j in m.items():
    o.at[sel[i], "off"] = j
o["official"] = o.off.notna()
print("listings matched to a King County record:", int(o.official.sum()))

# ---------------------------------------------------------------- research (hand-checked, each with a 2025-26 source)
base_ok = ~o.j_junk & ~o.j_closedname & ~o.j_outside & ~o.j_far & ~o.ov_closed & ~(o.nowhere & ~o.in21)
CUR = json.load(open(f"{DATA}/curated.json")) if os.path.exists(f"{DATA}/curated.json") else []


def year(v):
    """1954 / "1954" / "1949, Fife WA" / "c. 1938" -> the year as an int (None when no 4-digit year)."""
    m = re.search(r"\b(1[6-9]\d\d|20[0-2]\d)\b", str(v)) if v not in (None, "") else None
    return int(m.group(1)) if m else None


def load_research():
    """data/research/app/*.json (facts only, each entry with sources) -> curated-style entries; one per place (name + town)."""
    out, by = [], {(norm_name(c["name"]), (canon_city(c.get("city")) or "").lower()): c for c in CUR}
    for f in sorted(glob.glob(f"{DATA}/research/app/*.json")):
        for e in json.load(open(f)):
            if e.get("open") is False or not e.get("name"):
                continue
            for k in ("opened", "brand_founded"):
                if e.get(k) not in (None, "") and not isinstance(e.get(k), int):
                    e[k] = year(e[k])
            key = (norm_name(e["name"]), (canon_city(e.get("city")) or "").lower())
            c = by.get(key)
            if c is None:
                c = {"name": e["name"], "address": e.get("address"), "city": e.get("city"), "zip": e.get("zip"), "chain": bool(e.get("chain")),
                     "match_names": [e["name"].upper()] + [x.upper() for x in (e.get("aka") or [])], "founded": e.get("opened"), "open": True,
                     "tags": [], "research_only": True}
                by[key] = c; out.append(c)
            c["tags"] = list(dict.fromkeys((c.get("tags") or []) + [k.lower() for k in (e.get("kinds") or [])]))
            c["dishes"] = list(dict.fromkeys((c.get("dishes") or []) + (e.get("dishes") or [])))
            c["rsources"] = (c.get("rsources") or []) + [s_ for s_ in (e.get("sources") or []) if isinstance(s_, dict)]
            # the researcher's `note` mixes facts with working notes; only the edited `display_note` is ever shown
            shown = e.get("display_note") if "display_note" in e else None
            kinds = {k.lower() for k in (e.get("kinds") or [])}
            if shown and kinds & {"oldest", "icon"} and not kinds & {"teriyaki", "pho", "drive-in", "oysters", "seafood"}:
                c["iconic_reason"] = c.get("iconic_reason") or shown   # history goes with the honors
            elif shown:
                c["note"] = c.get("note") or shown
            c["website"] = c.get("website") or e.get("website")
            if not c.get("founded") and e.get("opened"):
                c["founded"] = e["opened"]
            if e.get("brand_founded") and not c.get("brand_founded"):
                c["brand_founded"] = e["brand_founded"]
            if e.get("kasahara"):
                c["kasahara"] = True
            if e.get("honor"):
                c.setdefault("james_beard", []).append(e["honor"])

    return out


def load_jbf():
    """James Beard honors (data/research/jbf_wa.json): one curated entry per open restaurant, honors as facts ("Finalist 2026: ...")."""
    p = f"{DATA}/research/jbf_wa.json"
    if not os.path.exists(p):
        return []
    J = json.load(open(p))
    out = []
    for r in J.get("restaurants", []):
        if r.get("open") is not True or not r.get("name"):   # only places confirmed open in 2025-26 carry an honor
            continue
        hon = []
        for h in r.get("honors") or []:
            if isinstance(h, str):
                hon.append(h); continue
            lvl, yr, cat, who = h.get("level"), h.get("year"), h.get("category"), h.get("person")
            if not lvl:
                continue
            lvl = {"winner": "Winner", "finalist": "Finalist", "semifinalist": "Semifinalist"}.get(str(lvl).lower(), lvl)
            hon.append(f"{lvl} {yr}" + (f": {cat}" if cat else "") + (f" ({who})" if who else ""))
        if not hon:
            continue
        out.append({"name": r["name"], "address": r.get("address"), "city": r.get("city"), "chain": False, "open": True,
                    "match_names": [r["name"].upper()], "james_beard": hon, "tags": ["jbf"], "research_only": True,
                    "rsources": [r["open_source"] if isinstance(r.get("open_source"), dict) else {"url": r.get("open_source")}] if r.get("open_source") else []})
    return out


CUR = CUR + load_jbf() + load_research()
# the same place from two research files: merge by name + town
merged = {}
for c in CUR:
    key = (norm_name(c["name"]), (canon_city(c.get("city")) or "").lower())
    if key in merged:
        m_ = merged[key]
        for k in ("tags", "dishes", "james_beard", "rsources", "match_names"):
            m_[k] = list(m_.get(k) or []) + [x for x in (c.get(k) or []) if x not in (m_.get(k) or [])]
        for k in ("address", "zip", "founded", "brand_founded", "note", "website", "iconic_reason", "kasahara"):
            m_[k] = m_.get(k) or c.get(k)
    else:
        merged[key] = dict(c)
CUR = list(merged.values())
print("verified places:", len(CUR), "| tags:", collections.Counter(t for c in CUR for t in (c.get("tags") or [])).most_common(8))
_m = curated_matcher(o[base_ok].reset_index())
_bo = o.index[base_ok]
verified = pd.Series(False, index=o.index)
for c in CUR:
    if c.get("open") is not False:
        j = _m(c)
        if j is not None:
            verified[_bo[j]] = True
keep = base_ok & (~o.closed21 | o.official | verified) & (o.src.isin(GOOD_SOURCES) | o.official | verified)
if APP:
    # measured against King County's records (calibration.json, app grouping): Meta listings with Overture confidence >= 0.95 matched a
    # King County business 80% of the time, 0.90-0.95 48%, chain store feeds 67%; lower-confidence Meta 23%, BrightQuery >= 0.95 27%
    # and everything else 14% are dropped
    conf = o.confidence.fillna(0)
    keep = base_ok & (o.official | verified | ((o.src == "meta") & (conf >= 0.9)) | o.src.isin(["AllThePlaces", "DAC"]))
print("kept listings:", int(keep.sum()), "of", len(o), "| dropped single-source:", int((base_ok & ~o.src.isin(GOOD_SOURCES) & ~o.official).sum()),
      "| closed per Google 2021:", int((base_ok & o.closed21 & ~o.official).sum()))
o = o[keep].reset_index(drop=True)

# ---------------------------------------------------------------- duplicate listings of one place
o["biz"] = o.off.map(lambda j: F.biz.iat[int(j)] if j == j else np.nan)
o["rank"] = o.official.astype(int) * 8 + o.in21.astype(int) * 4 + o.src.isin(GOOD_SOURCES).astype(int) * 2 + o.confidence.fillna(0)
o = o.sort_values("rank", ascending=False).reset_index(drop=True)
cell, drop = {}, set()
for i, r in o.iterrows():
    key = (round(r.lat / 0.001), round(r.lon / 0.0014))
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for j in cell.get((key[0] + dy, key[1] + dx), []):
                d_ = math.hypot((o.lat.iat[j] - r.lat) * 111000, (o.lon.iat[j] - r.lon) * 75000)
                same_biz = r.biz == r.biz and r.biz == o.biz.iat[j] and name_sim(r.k, o.k.iat[j]) >= 80
                if same_biz or (d_ < 80 and (r.k == o.k.iat[j] or (fuzz.token_set_ratio(r.k, o.k.iat[j]) >= 92 and r.st & o.st.iat[j]))) or (
                        d_ < 150 and isinstance(r.brand_n, str) and r.brand_n == o.brand_n.iat[j]):
                    drop.add(i); break
            if i in drop: break
        if i in drop: break
    if i not in drop:
        cell.setdefault(key, []).append(i)
o = o.drop(index=list(drop)).reset_index(drop=True)
akey = [(b if isinstance(b, str) else k, n, c) if n and isinstance(c, str) else None for b, k, n, c in zip(o.brand_n, o.k, o.num, o.city)]
seen, dup = set(), []
for a in akey:   # o is sorted best-first, so the better-sourced copy survives
    dup.append(a is not None and a in seen)
    if a is not None:
        seen.add(a)
has_addr = o.num.notna()
for b, grp in o[o.brand_n.notna()].groupby("brand_n"):
    with_a, without = grp[has_addr[grp.index]], grp[~has_addr[grp.index]]
    for i, r in without.iterrows():
        if len(with_a) and (np.hypot((with_a.lat - r.lat) * 111, (with_a.lon - r.lon) * 75) < 1.5).any():
            dup[i] = True
o = o[~np.array(dup)].reset_index(drop=True)
near_dup = set()
for (k, c), grp in o[o.brand_n.isna() & o.k.fillna("").str.len().ge(4) & o.city.notna()].groupby(["k", "city"]):
    if len(grp) < 2 or not (_stems(k) - GENERIC):
        continue
    idx = list(grp.index)
    for a in range(len(idx)):
        for b in range(a + 1, len(idx)):
            if idx[b] in near_dup or idx[a] in near_dup:
                continue
            if math.hypot((o.lat[idx[a]] - o.lat[idx[b]]) * 111000, (o.lon[idx[a]] - o.lon[idx[b]]) * 75000) < 500 and not (o.official[idx[a]] and o.official[idx[b]]):
                near_dup.add(idx[b])
    good = grp[grp.in21 | grp.official]
    for i in grp.index[~(grp.in21 | grp.official)]:
        if i not in near_dup and len(good) and (np.hypot((good.lat - o.lat[i]) * 111, (good.lon - o.lon[i]) * 75) < 1.5).any() and i not in good.index:
            near_dup.add(i)
o = o.drop(index=list(near_dup)).reset_index(drop=True)
print("after merging duplicate listings:", len(o), "(dropped", len(drop) + sum(dup) + len(near_dup), ")")
confirmed = ((o.src == "meta") & (o.confidence.fillna(0) >= 0.95)) if APP else o.in21
o["tier"] = np.where(o.official, "official", np.where(confirmed, "both", "listing"))

# ---------------------------------------------------------------- King County restaurants the map listings don't have
found = set(o.biz.dropna())
add = F[(F.kind == "restaurant") & ~F.biz.isin(found)].drop_duplicates("biz").copy()
print("King County restaurants not in the map listings:", len(add), "| without an address point:", int(add.lat.isna().sum()))
rows = []
for j, f in add.iterrows():
    rows.append({"id": f.lic, "name": f["name"], "street": f.addr, "city": f.city, "zip": f.zip, "lat": f.lat, "lon": f.lon, "cat": "restaurant",
                 "tax": None, "confidence": np.nan, "brand": None, "src": "official", "official": True, "off": j, "biz": f.biz, "tier": "official",
                 "in21": False, "closed21": False, "dom": None, "area": "king"})
A = pd.DataFrame(rows)


def clean_official(n):
    n = re.split(r"\s*;\s*", n or "")[0]
    n = re.sub(r"\s*#\s*\d+\w*.*$|\s*\(#?[A-Z]?\d+\)|\s+\d{3,}\s*$", "", n or "")
    n = re.sub(r",?\s+(?:INC|LLC|L\.L\.C|CORP|CORPORATION|LTD)\.?\s*$", "", n, flags=re.I)
    n = re.split(r"\s*/\s*", n)[0] if len(n) > 34 and "/" in n else n
    n = n.strip(" -,&/")
    return nice(n) if n.isupper() or n.islower() else n


A["name"] = A.name.map(clean_official)
A["k"] = A.name.map(norm_name)
A["st"] = A.k.map(lambda k: _stems(k) - GENERIC if k else set())
A["num"] = A.street.map(lambda a: (re.match(r"\s*(\d+)", a or "") or [None, None])[1])
A["brand_n"] = A.k.map(brand_of)
# Google 2021 listings for the added rows (artifact only)
taken = set(o.gi.dropna().astype(int))
grid = {}
for i, (la, lo) in enumerate(zip(G.latitude, G.longitude)):
    grid.setdefault((round(la / 0.0015), round(lo / 0.002)), []).append(i)
pairs = []
for ai, r in ([] if APP else A.iterrows()):
    if not r.k or r.lat != r.lat:
        continue
    gy, gx = round(r.lat / 0.0015), round(r.lon / 0.002)
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for gi in grid.get((gy + dy, gx + dx), []):
                if gi in taken or not G.k.iat[gi] or G.closed21.iat[gi]:
                    continue
                dist = math.hypot((G.latitude.iat[gi] - r.lat) * 111000, (G.longitude.iat[gi] - r.lon) * 75000)
                if dist > 200:
                    continue
                s = name_sim(r.k, G.k.iat[gi])
                same_num = r.num is not None and G.num.iat[gi] == r.num
                if same_num and r.st & G.st.iat[gi]:
                    s = max(s, 80)
                if s < 95 and not r.st & G.st2.iat[gi]:
                    continue
                if (s >= 88 and dist < 150) or (s >= 75 and same_num):
                    pairs.append((s + (10 if same_num else 0) - dist / 25, ai, gi))
A["gi"] = np.nan
ta, tg = set(), set()
for sc, ai, gi in sorted(pairs, key=lambda t: -t[0]):
    if ai in ta or gi in tg:
        continue
    ta.add(ai); tg.add(gi); A.at[ai, "gi"] = gi
A["in21"] = A.gi.notna()
nog = A.lat.isna() & A.gi.notna()
A.loc[nog, "lat"] = A.loc[nog, "gi"].map(lambda g: G.latitude.iat[int(g)])
A.loc[nog, "lon"] = A.loc[nog, "gi"].map(lambda g: G.longitude.iat[int(g)])
print("added rows matched to Google 2021:", int(A.in21.sum()), "| still unmapped:", int(A.lat.isna().sum()))
# a licensed place the address match missed can sit on top of its own map listing under a slightly different name: merge it into that
# listing, unless the listing already matched a record of its own
kgrid = {}
for j, (la, lo) in enumerate(zip(o.lat, o.lon)):
    kgrid.setdefault((round(la / 0.0015), round(lo / 0.002)), []).append(j)
merge, same_lic = {}, set()
o_addr = {}
for j, a in enumerate(o.street):
    sk = street_key(a)[1]
    for n in street_nums(a):
        if sk:
            o_addr.setdefault((n, undir(sk)), []).append((j, sk))
for ai, r in A.iterrows():
    if not r.k:
        continue
    if r.lat != r.lat:   # no coordinates: the same street address and a similar name
        sk = street_key(r.street)[1]
        for n in street_nums(r.street):
            for j in [j for j, k2 in o_addr.get((n, undir(sk)), []) if street_eq(sk, k2)]:
                s = name_sim(r.k, o.k.iat[j]) if o.k.iat[j] else 0
                if s >= 60 or bool(r.st & o.st.iat[j]):
                    (same_lic.add(ai) if o.official.iat[j] else merge.setdefault(ai, j))
        continue
    best, bs = None, -1
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            for j in kgrid.get((round(r.lat / 0.0015) + dy, round(r.lon / 0.002) + dx), []):
                if j in merge.values():
                    continue
                dist = math.hypot((o.lat.iat[j] - r.lat) * 111000, (o.lon.iat[j] - r.lon) * 75000)
                s = name_sim(r.k, o.k.iat[j]) if o.k.iat[j] else 0
                if o.official.iat[j]:
                    if dist <= 80 and s >= 95:
                        same_lic.add(ai)
                    continue
                shared = bool(r.st & o.st.iat[j]) or _close_words(r.st, o.st.iat[j])
                if (dist <= 60 and (s >= 88 or (shared and s >= 60))) or (dist <= 25 and s >= 75):
                    if s - dist / 10 > bs:
                        best, bs = j, s - dist / 10
    if best is not None:
        merge[ai] = best
for ai, j in merge.items():
    for c in ("official", "off", "biz", "tier", "area"):
        o.at[o.index[j], c] = A.at[ai, c]
A = A.drop(index=list(set(merge) | same_lic)).reset_index(drop=True)
print("records merged into a map listing on the second pass:", len(merge), "| second permits of listed places:", len(same_lic - set(merge)),
      "| King County rows added:", len(A))
# food courts, stadium stands and shared kitchens: 5+ record-only places at one address are hidden with the non-restaurants
akey = [(n, st) for n, st in zip(A.num, A.street.map(lambda a: street_key(a)[1]))]
shared_n = collections.Counter(akey)
A["lic_shared"] = [shared_n[k] >= 5 and not g for k, g in zip(akey, A.in21)]
print("record-only places at shared addresses (hidden with non-restaurants):", int(A.lic_shared.sum()))
o = pd.concat([o, A], ignore_index=True)
o["city"] = o.city.map(canon_city)
main = o.city.dropna().groupby(o.city.dropna().map(town_key)).agg(lambda x: x.mode().iat[0])
o["city"] = o.city.map(lambda c: main.get(town_key(c), c) if isinstance(c, str) else c)

# ---------------------------------------------------------------- hand-checked places the map listings don't have as a place to eat
_m = curated_matcher(o)
missing = [c for c in CUR if c.get("open") is not False and (not c.get("chain") or c.get("address")) and _m(c) is None]
added = []
SHOPCAT = r"store|shop|market|manufacturer|farm|butcher|creamery|wholesale|supplier|outlet"
import duckdb
OV = duckdb.connect().execute(f"""SELECT name, street, city, zip, lat, lon, cat, tax FROM '{WA}/overture_wa_bbox.parquet'
                                  WHERE region = 'WA' AND name IS NOT NULL""").df()
OV["k"] = OV.name.map(norm_name); OV["town"] = OV.city.map(lambda c: (canon_city(c) or "").lower())
ov_by_town = {t: g for t, g in OV.groupby("town")}
GEOCACHE = json.load(open(f"{DATA}/research/geocode_census.json")) if os.path.exists(f"{DATA}/research/geocode_census.json") else {}
GEO_TODO = []
GEO = OFFICIAL.Geocoder() if missing else None


def geo_key(c):
    a, t = (c.get("address") or "").strip(), (c.get("city") or "").strip()
    return f"{a}, {t}, WA {c.get('zip') or ''}".strip() if re.match(r"\s*\d", a) and t else None


for c in missing:
    keys = {norm_name(m_) for m_ in (c.get("match_names") or [])} | {norm_name(c["name"])}
    keys.discard("")
    town = (canon_city(c.get("city") or "") or "").lower()
    spot = None
    g = ov_by_town.get(town)
    if g is not None:   # Overture's own listing of the business in any category (an inn, a market, a hotel bar)
        sims = [max(fuzz.ratio(m_, k) for m_ in keys) if isinstance(k, str) and k else 0 for k in g.k]
        j = int(np.argmax(sims)) if len(sims) else -1
        if j >= 0 and sims[j] >= 88:
            h = g.iloc[j]
            spot = (h["lat"], h["lon"], (h["zip"] or "")[:5] or c.get("zip"), str(h["cat"] or "") + " " + str(h["tax"] or ""))
    if spot is None and c.get("address"):
        hit = GEO(c["address"], c.get("city"), (c.get("zip") or "")[:5] or None)
        if hit:
            spot = (hit[0], hit[1], hit[2] or c.get("zip"), "")
    if spot is None:
        gq = geo_key(c)
        hit = GEOCACHE.get(gq) if gq else None
        if hit:
            spot = (hit["lat"], hit["lon"], hit.get("zip") or c.get("zip"), "")
        else:
            if gq:
                GEO_TODO.append(gq)
            continue
    la, lo, zp, catx = spot
    near = o[(np.abs(o.lat - la) < 0.003) & (np.abs(o.lon - lo) < 0.004)]
    if len(near) and any(max(fuzz.token_set_ratio(m_, k) for m_ in keys) >= 80 for k in near.k.fillna("")):
        continue   # the place is already here under a slightly different name or address: the matcher will pick it up as is
    added.append({"id": "research-" + c["name"], "name": c["name"], "street": c.get("address"), "city": canon_city(c.get("city")), "zip": zp,
                  "lat": la, "lon": lo, "cat": "restaurant", "tax": None, "confidence": np.nan, "brand": None, "src": "research",
                  "official": False, "off": np.nan, "biz": np.nan, "tier": "both", "in21": False, "closed21": False, "dom": None, "area": None,
                  "gi": np.nan, "k": norm_name(c["name"]), "st": _stems(norm_name(c["name"])) - GENERIC,
                  "num": (re.match(r"\s*(\d+)", c.get("address") or "") or [None, None])[1], "brand_n": None, "venue": False, "web": c.get("website"),
                  "shop": bool(re.search(SHOPCAT, catx, re.I)) and not re.search(r"TAVERN|RESTAURANT|TERIYAKI|INN|GRILL|BAR\b|CAFE", norm_name(c["name"]))})
if added:
    o = pd.concat([o, pd.DataFrame(added)], ignore_index=True)
json.dump(sorted(set(GEO_TODO)), open(f"{DATA}/research/geocode_todo.json", "w"), indent=1)
print("hand-checked places added (not in the map listings as a place to eat):", len(added), "of", len(missing), "| waiting for the Census geocoder:",
      len(set(GEO_TODO)))

# counties: every place gets one (the map's county filter and the per-county counts)
cty = json.load(open(f"{WA}/wa_counties_detail.geojson"))["features"]
# the exact outline first; the buffered one (about 300 m) only for a place just off the simplified coast or state line. Places on a
# county line (N 205th St, SW 356th St) took the neighbor's name when the buffered outlines were tried first.
_cx = [(f["properties"]["name"].replace(" County", ""), prep(shape(f["geometry"]))) for f in cty]
_cp = [(f["properties"]["name"].replace(" County", ""), prep(shape(f["geometry"]).buffer(0.003))) for f in cty]
o["county"] = [(next((n for n, p in _cx if p.contains(Point(lo, la))), None) or next((n for n, p in _cp if p.contains(Point(lo, la))), None))
               if la == la else None for la, lo in zip(o.lat, o.lon)]
o.loc[o.official, "county"] = "King"   # a business King County inspects is in King County
# towns that share a name in different corners of the state are two towns
split = 0
for c, grp in o[o.city.notna() & o.county.notna()].groupby("city"):
    if grp.county.nunique() < 2:
        continue
    med = grp.groupby("county")[["lat", "lon"]].median()
    far = max(math.hypot((a.lat - b.lat) * 111, (a.lon - b.lon) * 75) for _, a in med.iterrows() for _, b in med.iterrows())
    if far > 60:
        big = grp.county.value_counts()
        if big.iloc[0] < 0.9 * len(grp):
            o.loc[grp.index, "city"] = [f"{c} ({n} Co.)" for n in grp.county]
            split += 1
print("same-name towns split by county:", split)

# ---------------------------------------------------------------- fields
gi = [int(v) if v == v and v is not None else None for v in o.gi]
o["rating"] = [G.avg_rating.iat[i] if i is not None else np.nan for i in gi]
o["reviews"] = [G.num_of_reviews.iat[i] if i is not None else np.nan for i in gi]
o["gprice"] = [len(G.price.iat[i]) if i is not None and isinstance(G.price.iat[i], str) else np.nan for i in gi]
o["gcats"] = ["|".join(G.category.iat[i] or []) if i is not None else "" for i in gi]
o["name_out"] = [b if isinstance(b, str) and fuzz.ratio(norm_name(n), norm_name(b)) >= 88 else nice(n) if n.isupper() or n.islower() else n
                 for n, b in zip(o.name, o.brand_n)]


def pick_cuisine(tax, k, gcats, raw):
    for c, pat in CUISINE_RULES[:-1]:          # a specific word in the name wins ("Toshi's Teriyaki", "Pho Bac")
        if pat.search(k or ""):
            return c
    if isinstance(tax, str) and tax in TAX_CUISINE:
        return TAX_CUISINE[tax]
    return cuisine(k, gcats, raw)


o["cuisine"] = [pick_cuisine(t, k, gc, n) for t, k, gc, n in zip(o.tax, o.k, o.gcats, o.name)]
first_cat = o.gcats.str.split("|").str[0].fillna("")
cafe_tax = o.tax.isin(["cafe", "coffee_shop"]) & o.cuisine.eq("Coffee & Café") & first_cat.ne("") & ~first_cat.str.contains(r"Coffee|Cafe|Café|Espresso|Tea|Bakery|Donut|Dessert|Ice cream|Juice|Breakfast")
o.loc[cafe_tax, "cuisine"] = [cuisine(k, g, "") for k, g in zip(o.loc[cafe_tax, "k"], o.loc[cafe_tax, "gcats"])]
o.loc[o.cat.isin(["bar", "brewery"]) & (o.cuisine == "American & Other"), "cuisine"] = "Bar & Pub"
o.loc[o.cat.isin(["coffee_shop", "cafe"]) & (o.cuisine == "American & Other"), "cuisine"] = "Coffee & Café"
o.loc[o.city.fillna("") == "", "city"] = None


# brand sanity: a brand rule that matched a name prefix must agree with the listing's website, Overture's brand feed, or its kind of food
def mode(x):
    return x.mode().iat[0]


bdom = {}
for b, grp in o[o.brand_n.notna()].groupby("brand_n"):
    d = grp.dom.dropna()
    if len(d) >= 3:
        top, n = collections.Counter(d).most_common(1)[0]
        if n >= 0.5 * len(d):
            bdom[b] = top
FAMILY = {"Chicken & Wings": "quick", "Burgers": "quick", "Hot Dogs": "quick", "Sandwiches & Deli": "cafe", "Pizza": "pizza",
          "Mexican": "mex", "Latin & Caribbean": "mex", "Coffee & Café": "cafe", "Bakery & Sweets": "cafe",
          "Breakfast & Diner": "cafe", "Healthy & Vegan": "cafe", "Steakhouse": "sitdown", "Seafood": "sea",
          "Bar & Pub": "bar", "Italian": "italian", "Chinese": "asian", "Japanese & Sushi": "asian", "Thai": "asian", "Korean": "asian",
          "Vietnamese": "asian", "Teriyaki": "asian", "Hawaiian": "asian", "Filipino": "asian", "South Asian": "sasian",
          "Mediterranean & Middle Eastern": "med", "German & European": "sitdown", "BBQ": "bbq", "Soul & Southern": "soul", "African": "african"}
brand_cuisine = o[o.brand_n.notna()].groupby("brand_n").cuisine.agg(mode)


def core(k):
    w = [x for x in k.split() if x not in GENERIC and x not in ("RESTAURANT", "RESTAURANTS", "CAFE", "STORE")]
    return " ".join(w) or k


def brand_ok(b, dm, cu, tax, obrand, name, src):
    if not isinstance(b, str):
        return None
    dm = dm if isinstance(dm, str) else None
    nk, bk = norm_name(name), norm_name(b)
    if src not in ("AllThePlaces", "DAC") and brand_of(nk) != b:
        return None
    ob = norm_name(obrand) if isinstance(obrand, str) else ""
    brand_feed = src in ("AllThePlaces", "DAC")
    label = bool(ob) and fuzz.token_set_ratio(ob, bk) >= 80
    related = brand_feed or fuzz.partial_ratio(bk, nk) >= 60 or (label and fuzz.partial_ratio(ob, nk) >= 60)
    if not related:
        return None
    squashed = re.sub(r"[^a-z]", "", b.lower())
    own_site = dm and (bdom.get(b) == dm or dm.split(".")[0].replace("-", "") in (squashed, squashed + "s"))
    exact = fuzz.ratio(core(nk), core(bk)) >= 90 or (label and fuzz.ratio(core(nk), core(ob)) >= 90) \
        or (len(bk) >= 6 and (nk == bk or nk.startswith(bk + " ")))
    if exact or own_site or (label and brand_feed):
        return b
    if dm and b in bdom and src != "BrightQuery":
        return None
    want = brand_cuisine.get(b)
    if isinstance(tax, str) and tax in TAX_CUISINE and want and FAMILY.get(cu) and FAMILY.get(want) and FAMILY[cu] != FAMILY[want]:
        return None
    return b


old_brand = o.brand_n.copy()
o["brand_n"] = [brand_ok(b, dm, cu, t, ob, n, sr) for b, dm, cu, t, ob, n, sr in zip(o.brand_n, o.dom, o.cuisine, o.tax, o.brand, o.name, o.src)]
rej = o[old_brand.notna() & o.brand_n.isna()]
print("brand matches rejected:", len(rej), collections.Counter(old_brand[rej.index]).most_common(8))
o.loc[o.brand_n.notna(), "name_out"] = [b if fuzz.ratio(norm_name(n), norm_name(b)) >= 80 or len(norm_name(n)) <= len(norm_name(b)) + 2 else n
                                        for n, b in zip(o.loc[o.brand_n.notna(), "name_out"], o.loc[o.brand_n.notna(), "brand_n"])]


def chain_mode(x):
    real = x[x != "American & Other"]
    return (real if len(real) else x).mode().iat[0]


CHAIN_CUISINE = {"Dick's Drive-In": "Burgers", "Zip's Drive-In": "Burgers", "Burgerville": "Burgers", "Kidd Valley": "Burgers", "Burgermaster": "Burgers",
                 "Red Robin": "Burgers", "Jack in the Box": "Burgers", "Carl's Jr.": "Burgers", "In-N-Out Burger": "Burgers",
                 "Dutch Bros": "Coffee & Café", "Black Rock Coffee Bar": "Coffee & Café", "Starbucks": "Coffee & Café", "Dunkin'": "Coffee & Café",
                 "Ziggi's Coffee": "Coffee & Café", "Coffee Oasis": "Coffee & Café", "Tully's Coffee": "Coffee & Café", "Caffe Ladro": "Coffee & Café",
                 "Top Pot Doughnuts": "Bakery & Sweets", "Mighty-O Donuts": "Bakery & Sweets", "Molly Moon's": "Bakery & Sweets",
                 "Dairy Queen": "Bakery & Sweets", "Baskin-Robbins": "Bakery & Sweets", "Ivar's": "Seafood", "Anthony's": "Seafood",
                 "Duke's Seafood": "Seafood", "Taco Time": "Mexican", "Taco del Mar": "Mexican", "Teriyaki Madness": "Teriyaki", "Sarku Japan": "Teriyaki",
                 "Panda Express": "Chinese", "Din Tai Fung": "Chinese", "Shari's": "Breakfast & Diner", "Elmer's": "Breakfast & Diner",
                 "Black Bear Diner": "Breakfast & Diner", "IHOP": "Breakfast & Diner", "Denny's": "Breakfast & Diner", "Panera Bread": "Sandwiches & Deli",
                 "Texas Roadhouse": "Steakhouse", "El Gaucho": "Steakhouse", "L&L Hawaiian Barbecue": "Hawaiian", "Jollibee": "Filipino",
                 "Pagliacci Pizza": "Pizza", "Zeeks Pizza": "Pizza", "Mod Pizza": "Pizza", "MOD Pizza": "Pizza", "Ezell's Famous Chicken": "Chicken & Wings",
                 "13 Coins": "American & Other", "Applebee's": "American & Other", "Azteca": "Mexican"}
allc = o.loc[o.brand_n.notna(), ["brand_n", "cuisine"]]
all_brand_cuisine = allc.groupby("brand_n").cuisine.agg(chain_mode)
o.loc[o.brand_n.notna(), "cuisine"] = o.loc[o.brand_n.notna(), "brand_n"].map(lambda b: CHAIN_CUISINE.get(b) or all_brand_cuisine.get(b))

# price: Google price level (artifact), else the chain's usual level, else the cuisine's usual level
o["price"] = o.gprice
o["price_est"] = o.price.isna().astype(int)
bp = o[o.gprice.notna()].groupby("brand_n").gprice.median()
o.loc[o.price.isna() & o.brand_n.notna(), "price"] = o.brand_n.map(bp)
cp = o[o.gprice.notna()].groupby("cuisine").gprice.median()
o.loc[o.price.isna(), "price"] = o.cuisine.map(cp)
o["price"] = o.price.fillna(2).round().clip(1, 4).astype(int)

# chain size statewide. Unbranded same-name places count as one chain only when they share a website
bc = o.brand_n.value_counts()
o["chain_n"] = o.brand_n.map(lambda b: int(bc.get(b, 0)) if isinstance(b, str) else 1)
STORE_DOMS_ALL = {"safeway.com", "qfc.com", "fredmeyer.com", "albertsons.com", "haggen.com", "walmart.com", "target.com", "costco.com", "winco.com",
                  "7-eleven.com", "chevron.com", "arco.com", "ampm.com", "shell.us", "maverik.com", "circlek.com", "pccmarkets.com", "townandcountrymarkets.com",
                  "metropolitan-market.com", "groceryoutlet.com", "traderjoes.com", "wholefoodsmarket.com", "uwajimaya.com", "yokesfreshmarkets.com",
                  "rosauers.com", "saarsmarketplace.com", "grocery.walmart.com", "samsclub.com"}
first_stem = o.k.fillna("").map(lambda k: next((w for w in k.split() if w not in GENERIC and len(w) >= 3), None))
# toshisgrill.com (Kasahara's Mill Creek shop) has a page for each unrelated "Toshi's Teriyaki" saying it's "no longer affiliated": not a chain
NOT_CHAIN_DOMS = {"toshisgrill.com"}
grpkey = pd.Series([(d, s) if isinstance(d, str) and isinstance(s, str) and not isinstance(b, str) and d not in STORE_DOMS_ALL | NOT_CHAIN_DOMS else None for d, s, b in zip(o.dom, first_stem, o.brand_n)], index=o.index)
gsize = grpkey.dropna().value_counts()
member = [g is not None and gsize.get(g, 0) >= 2 for g in grpkey]
o.loc[member, "chain_n"] = [int(gsize[g]) for g, m_ in zip(grpkey, member) if m_]
o["ckey"] = grpkey.map(lambda g: "|".join(g) if g else None)
grp_cuisine = o[member].groupby("ckey").cuisine.agg(chain_mode)
o.loc[member, "cuisine"] = [grp_cuisine.get(k) for k in o.loc[member, "ckey"]]
sib = o.gprice.notna()
for key, sel_ in (("brand_n", o.brand_n.notna()), ("ckey", pd.Series(member, index=o.index))):
    med = o[sel_ & sib].groupby(key).gprice.median()
    fill = sel_ & (o.price_est == 1) & o[key].isin(med.index)
    o.loc[fill, "price"] = o.loc[fill, key].map(med).round().clip(1, 4).astype(int)
print("name-based chains:", len(set(o.ckey[member])), "|", int(sum(member)), "locations")

o["bar"] = o.cat.isin(["bar", "brewery"]) | (o.cuisine == "Bar & Pub")
EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]+")
CJK = r"[぀-ヿ㐀-鿿가-힯豈-﫿＀-￯]"
TAILWORDS = re.compile(r"^(?:best|award|voted|magazine|official|order|delivery|takeout|take out|catering|now open|open|to go|curbside|franchise|inside .*|"
                       r"(?:(?:ice cream|chocolates?|fudge|coffee|cafe|café|restaurant|bar|grill|pizza|shawarma|hookah lounge|espresso|drive thru|drive-thru|"
                       r"bakery|deli|sandwiches|tacos|gifts?|shopping|treats|sweets|full bar|food|game room|drinks|spirits|live music|events|patio|"
                       r"lodging|rooms|resort|motel|campground|cocktails|beer|wine|burgers|wings|craft beer|sports bar|teriyaki|pho|and|&|,|-|\s)+))$", re.I)


def tidy(n, brand):
    """Emoji and non-Latin duplicates of an English name, LLC in the middle, marketing tails, notes in parentheses."""
    n = unicodedata.normalize("NFKC", n)
    if re.search(r"[ÃÂâð][\u0080-¿ŒœŠšŸŽžƒˆ˜–-›€™]", n):
        for enc in ("cp1252", "latin-1"):
            try:
                n = n.encode(enc).decode("utf-8"); break
            except (UnicodeEncodeError, UnicodeDecodeError):
                pass
    n = re.sub(r"[®™©]", "", EMOJI.sub("", n))
    if re.search(r"[A-Za-z]{3,}", re.sub(CJK, "", n)):
        n = re.sub(r"\s*\([^()]*" + CJK + r"[^()]*\)", "", n)
    latin = re.sub(CJK + "+", " ", n)
    if re.search(r"[A-Za-z]{3,}", latin) and re.search(CJK, n):
        n = re.sub(r"\(\s*\)", "", latin)
    m_ = re.match(r"^(.*?)[,\s]+(?:LLC|Inc)\.?\s*-{1,2}\s*(.+)$", n, flags=re.I)
    if m_:
        n = m_.group(2) if len(m_.group(2).split()) >= 2 and len(m_.group(1).split()) <= 2 else m_.group(1)
    n = re.sub(r"[,\s]+(?:LLC|L\.L\.C|LLP|L\.L\.P|Inc|Corp)\.?(?=\s|$|,)", "", n, flags=re.I)
    n = re.sub(r"\s*\([^()]*\)\s*$", "", n) if re.sub(r"\s*\([^()]*\)\s*$", "", n).strip() else n
    n = re.sub(r",?\s+(?:WA|Wash\.?|Washington)\s*$", "", n)
    parts = re.split(r"\s+[-–]{1,2}\s+|--", n)
    if len(parts) > 1:
        tail = " ".join(parts[1:])
        if TAILWORDS.match(tail.strip()) or re.search(r"\b(?:Best|Award|Magazine|Voted|20\d\d)\b", tail):
            n = parts[0]
    if isinstance(brand, str):
        n = re.sub(r"\s*#\s*\d+\s*$", "", n)
    n = re.sub(r"\s+", " ", n).strip(" -–,") or n
    return nice(n) if n.isupper() and len(n) > 4 else n


o["name_out"] = [tidy(n, b) for n, b in zip(o.name_out, o.brand_n)]
o.loc[o.brand_n.notna(), "name_out"] = [b if norm_name(n).startswith(norm_name(b)) and len(norm_name(b)) >= 3 else n
                                        for n, b in zip(o.loc[o.brand_n.notna(), "name_out"], o.loc[o.brand_n.notna(), "brand_n"])]
o["spell"] = o.name_out.map(lambda n: re.sub(r"[^a-z0-9]", "", n.lower()))
o["name_out"] = o.groupby("spell").name_out.transform(lambda s: s.mode().iat[0] if len(s) > 1 else s.iat[0])
towns_l = set(o.city.dropna().str.lower())
nm = o.name_out.fillna("")
junk = (nm.str.match(r"(?i)^\d+\s+(?:[NSEW]{1,2}\.?\s+)?[\w.' ]+?\b(?:St|Street|Ave|Avenue|Dr|Drive|Rd|Road|Blvd|Ln|Lane|Way|Ct|Pl|Hwy|Pkwy|Trl)\b\.?(?:\s*(?:[NSEW]{1,2}))?(?:\s*#\s*\w+)?(?:\s*,.*)?$")
        | nm.str.contains(r"(?i)(?:\bclosed|\bretired)\s*\)?\s*$") | (nm.str.lower().str.strip().isin(towns_l) & o.brand_n.isna())
        | nm.str.match(r"(?i)^(?:city|town) of ") | nm.str.strip().str.lower().isin(["kitchen", "bar", "pub", "tavern", "grill", "deli", "pizza", "bakery", "coffee", "diner", "restaurant", "cafe", "café", "espresso", "teriyaki"])
        | ~nm.str.contains(r"[A-Za-z]"))
print("junk names dropped:", int(junk.sum()), nm[junk].head(12).tolist())
o = o[~junk].reset_index(drop=True)

# ---------------------------------------------------------------- not restaurants (hidden unless "include non-restaurants" is on)
STORE = re.compile(r"^(?:SAFEWAY|QFC|FRED MEYER|ALBERTSONS|HAGGEN|WINCO(?: FOODS)?|WALMART\b.*|COSTCO\b.*|TARGET|PCC(?: COMMUNITY MARKETS?)?|TOWN AND COUNTRY MARKET|"
                   r"METROPOLITAN MARKET|GROCERY OUTLET|TRADER JOES|WHOLE FOODS(?: MARKET)?|YOKES(?: FRESH MARKET)?|ROSAUERS|SAARS|CHEVRON|ARCO|AM ?PM|SHELL|"
                   r"MAVERIK|CIRCLE K|7 ELEVEN|TEXACO|CONOCO|76|SINCLAIR|BP|EXXON|MOBIL|DASHMART|GO ?PUFF|SAMS CLUB|BEST FOODS)$|"
                   r"\b(?:SAMS CLUB|BIMBO BAKERIES|BAKERIES USA|BAKERY OUTLET|THRIFT STORE|HUNT BROTHERS|HOT STUFF (?:PIZZA|FOODS|KITCHEN)|KRISPY KRUNCHY|"
                   r"CHESTERS (?:FRIED )?CHICKEN|GAS STATION|TRAVEL (?:CENTER|PLAZA)|TRUCK STOP|TRUCKSTOP|FARMERS FRIDGE|MRBEAST|MR BEAST|ITS JUST WINGS|"
                   r"BURGER DEN|BANDA BURRITO|TENDERFIX|PARDON MY CHEESESTEAK|THE MELTDOWN|WOW BAO|GHOST KITCHEN|VIRTUAL KITCHEN|"
                   r"LIQUORS? (?:STORE|MART|DEPOT|OUTLET)|LIQUORS?$|SPIRITS AND WINE|GENTLEM[AE]NS CLUB|DEJA VU|SHOWGIRLS|TRAMPOLINE|INDOOR PLAYGROUND|"
                   r"MEAT MARKET|MEATS$|BUTCHER|VENDING|COMMISSARY|FOOD PANTRY|FOOD BANK|WINE (?:MERCHANTS?|SHOP|STORE|DEPOT|OUTLET)|"
                   r"JELLY BELLY|LINDT|ROCKY MOUNTAIN CHOCOLATE|CANNABIS|DISPENSARY|POT SHOP|MARIJUANA)\b")
STORE_DOMS = STORE_DOMS_ALL | {"huntbrotherspizza.com", "hotstuffpizza.com", "krispykrunchy.com", "chesters.com", "farmersfridge.com", "mrbeastburger.com"}
REALFOOD = re.compile(r"\b(?:RESTAURANT|GRILL|BAR|PUB|TAVERN|PIZZA|CAFE|KITCHEN|STEAK|BISTRO|DINER|BREWING|BREWERY|TAP|SALOON|TERIYAKI|PHO|"
                      r"TAPROOM|LOUNGE|INN|EATERY|BURGERS?|BBQ|TACOS?|DRIVE IN|DELI|COFFEE|ESPRESSO|ICE CREAM|CREAMERY|BAKERY|DONUTS?|SUSHI|THAI)\b")
CANDY = re.compile(r"\b(?:CANDY|CANDIES|FUDGE|POPCORN|CONFECTION\w*|CHOCOLATES?|CHOCOLATIER|TRUFFLES?|SWEETS? SHOPPE?|KETTLE CORN|NUTRITION)\b")
HARD = re.compile(r"\b(?:AIRPORT|TERMINAL|CONCOURSE|SEA TAC INTERNATIONAL|SEATTLE TACOMA INTERNATIONAL|LUMEN FIELD|T MOBILE PARK|CLIMATE PLEDGE|"
                  r"HUSKY STADIUM|ALASKA AIRLINES ARENA|TACOMA DOME|SPOKANE ARENA|WASHINGTON STATE FAIR|EVERGREEN STATE FAIR|FAIRGROUNDS?|"
                  r"LEVY|AVIANDS|SODEXO|ARAMARK|DELAWARE NORTH|CENTERPLATE|COMPASS GROUP|CHARTWELLS|BON APPETIT|HMSHOST|EUREST|GUCKENHEIMER|"
                  r"SSP AMERICA|DELTA SKY CLUB|CENTURION LOUNGE|ALASKA LOUNGE|COMMISSARY|DINING HALL|UNIVERSITY DINING|CORRECTIONAL|PRISON|"
                  r"MICROSOFT CAFE|MICROSOFT CAFETERIA|AMAZON CAFE|BOEING|TRUCK ENTRANCE|CAREERS|FERRY TERMINAL)\b")
SOFT = re.compile(r"\b(?:STADIUM|ARENA|FESTIVAL|CONCESSIONS?|FOOD ?SERVICES?|UNIVERSITY|COLLEGE|SCHOOL|ACADEMY|ELEMENTARY|STUDENT|CAMPUS|"
                  r"HOSPITAL|MEDICAL CENTER|CLINIC|HEALTH CENTER|SENIOR|RETIREMENT|ASSISTED LIVING|NURSING|CARE CENTER|REHAB|CHURCH|PARISH|"
                  r"CONGREGATION|TEMPLE|SYNAGOGUE|MOSQUE|MINISTR(?:Y|IES)|VFW|AMERICAN LEGION|AMVETS|EAGLES|FRATERNAL ORDER|ELKS LODGE|"
                  r"MOOSE LODGE|KNIGHTS OF COLUMBUS|COUNTRY CLUB|GOLF CLUB|GOLF COURSE|YACHT CLUB|ATHLETIC CLUB|SOCIAL CLUB|"
                  r"SPORTSMEN'?S CLUB|ROD AND GUN|CATERING|CATERERS?|BANQUETS?|BANQUET HALL|EVENT (?:CENTER|VENUE|SPACE)|"
                  r"CONVENTION CENTER|CONFERENCE CENTER|MUSEUM|ZOO|AQUARIUM|THEATER|THEATRE|CINEMAS?|REGAL|AMC|BOWLING|LANES|CASINO|"
                  r"HOTEL|MOTEL|INN AND SUITES|SUITES|MARRIOTT|HILTON|HYATT|SHERATON|WESTIN|HOLIDAY INN|HAMPTON INN|FAIRFIELD INN|RESIDENCE INN|"
                  r"COURTYARD|SPRINGHILL|RADISSON|BEST WESTERN|COMFORT INN|SUPER 8|RED ROOF|DAYS INN|LA QUINTA|GREAT WOLF|"
                  r"CORPORATE|EMPLOYEE|CAFETERIA|MOBILE|FOOD TRUCK|KIOSK|GYM|FITNESS|YMCA|YWCA|BOYS AND GIRLS CLUB|DAYCARE|DAY CARE|CHILD CARE|"
                  r"CHILDCARE|LEARNING CENTER|JAIL|MILITARY|NATIONAL GUARD|BUILDING|COMMONS)\b")
kd = o.name_out.map(norm_name).fillna("")
k_ = o.k.fillna("")
busy = o.reviews.fillna(0) >= 200
gfirst = o.gcats.fillna("").str.split("|").str[0]
plainly_food = kd.str.contains(REALFOOD) | o.cat.isin(["bar", "brewery", "coffee_shop", "cafe"]) \
    | gfirst.str.contains(r"\b(?:Bar|Pub|Restaurant|Cafe|Café|Coffee|Tavern|Grill|Brewery|Diner|Bakery)\b", regex=True)
brand_store = o.brand_n.isin(["7-Eleven", "Hunt Brothers Pizza", "Hot Stuff Pizza", "Krispy Krunchy Chicken", "Chesters Chicken", "Farmer's Fridge",
                              "MrBeast Burger", "It's Just Wings", "Burger Den", "The Meltdown", "Banda Burrito", "Tenderfix", "Pardon My Cheesesteak"])
store = kd.str.contains(STORE) | k_.str.contains(r"\b(?:GAS STATION)\b") | brand_store | (o.dom.isin(STORE_DOMS) & ~plainly_food) \
    | (kd.str.contains(CANDY) & ~kd.str.contains(REALFOOD) & ~busy)
venue = kd.str.contains(HARD) | k_.str.contains(HARD) | o.name.fillna("").str.upper().str.contains(r"\(T-?\d|\bGATE [A-Z]?\d|\bPIER \d+ TERMINAL", regex=True) \
    | (kd.str.contains(SOFT) & ~(busy | plainly_food))
LICENSE_ONLY_NONREST = re.compile(r"\b(?:APARTMENTS?|POOLS?|SWIM|AQUATIC|ASSOCIATION|ATTN|C O|EVENTS?|STUDIOS?|HOSPITALITY GROUP|KNIGHTS|HEALTH|"
                                  r"CONDOMINIUMS?|HOMEOWNERS|NEIGHBORHOOD|COMMUNITY|PARKS AND REC|RECREATION|CAMP|BIBLE|FOUNDATION|SOCIETY|COUNCIL|"
                                  r"LEAGUE|UNION|INSTITUTE|CENTER$|FARMS?|AMUSEMENT|PREP|EDUCATIONAL|ENTERTAINMENT|CORPORATION|HOLDINGS|MANAGEMENT|"
                                  r"VENTURES|FIELD|SUITE|LOUNGE ACCESS|CLUB LEVEL|CONCOURSE|SECTION|PORTABLE|CART|STAND \d+)\b")
lic_only = o.src.eq("official")
club = kd.str.contains(r"\bCLUB\b") & ~kd.str.contains(r"NIGHT ?CLUB|SUPPER CLUB|SANDWICH CLUB|BREAKFAST CLUB")
venue |= lic_only & (kd.str.contains(LICENSE_ONLY_NONREST) | club) & ~busy
# stadiums, the airport, Seattle Center and corporate campuses (addresses with many King County permits)
VENUE_ADDR = {("800", "OCCIDENTAL S"), ("1250", "1ST S"), ("334", "1ST N"), ("17801", "INTERNATIONAL"), ("3800", "MONTLAKE NE"),
              ("305", "HARRISON"), ("1", "MICROSOFT"), ("410", "TERRY N"), ("2700", "E PIERCE"), ("2727", "E D"), ("720", "W MALLON")}
vaddr = pd.Series([bool(street_nums(a) & {n for n, s2 in VENUE_ADDR if s2 == s_}) for a, s_ in
                   zip(o.street, o.street.map(lambda a: street_key(a)[1]))], index=o.index)
airport = o.street.fillna("").str.upper().str.contains(r"^17801 INTERNATIONAL")
vaddr &= ~((o.reviews.fillna(0) >= 300) & ~airport)
venue |= vaddr
print("stadium / airport / campus addresses:", int(vaddr.sum()))
o["venue"] = store | venue | o.get("lic_shared", pd.Series(False, index=o.index)).fillna(False).astype(bool)
print("non-restaurants flagged:", int(o.venue.sum()), "| stores:", int(store.sum()), "| venues:", int((venue & ~store).sum()))

# ---------------------------------------------------------------- Washington tags (named in the directory; guides use hand-checked ones only)
nmu = o.name_out.fillna("").str.upper()
o["t_teriyaki"] = o.cuisine.eq("Teriyaki")
o["t_pho"] = nmu.str.contains(r"\bPH[OỞ]\b", regex=True) | o.name_out.fillna("").str.contains("Phở")
o["t_oysters"] = nmu.str.contains(r"\bOYSTERS?\b|\bCLAMS?\b|\bCHOWDER\b|SHELLFISH|FISH (?:AND|&) CHIPS", regex=True)
o["t_drivein"] = nmu.str.contains(r"\bDRIVE[- ]?INN?S?\b", regex=True) | o.brand_n.isin(["Dick's Drive-In", "Zip's Drive-In"])
o["t_espresso"] = (o.cuisine.eq("Coffee & Café") & nmu.str.contains(r"\bESPRESSO\b|\bDRIVE[- ]?TH?RU\b|\bCOFFEE (?:STAND|HUT|SHACK|KIOSK)\b|\bJAVA HUT\b", regex=True)) \
    | o.brand_n.isin(["Dutch Bros", "Black Rock Coffee Bar", "Ziggi's Coffee", "Coffee Oasis"])

# ---------------------------------------------------------------- research and honors (hand-checked)
for col in ("jbf", "honors", "icon", "founded", "brand_founded", "cur_tags", "dishes", "rnote", "rsite", "rsrc", "kasahara"):
    o[col] = None
match_curated = curated_matcher(o)
o["hc"] = False
o["hc_tags"] = ""
matched_cur, unmatched = 0, []
for c in CUR:
    if c.get("open") is False:
        continue
    best = match_curated(c)
    if best is None:
        unmatched.append(c["name"] + " (" + (c.get("city") or "") + ")")
        continue
    matched_cur += 1
    i = o.index[best]
    o.at[i, "hc"] = True
    o.at[i, "hc_tags"] = ";".join(dict.fromkeys([x for x in (o.at[i, "hc_tags"] or "").split(";") if x] + list(c.get("tags") or [])))
    for col, vals in (("jbf", c.get("james_beard")), ("honors", c.get("other_honors")), ("dishes", c.get("dishes"))):
        if vals:
            have = [x for x in (o.at[i, col] or "").split("; ") if x]
            o.at[i, col] = "; ".join(have + [v for v in dict.fromkeys(vals) if v not in have])
    for col, v in (("icon", c.get("iconic_reason")), ("founded", c.get("founded")), ("brand_founded", c.get("brand_founded")),
                   ("rnote", c.get("note")), ("rsite", c.get("website")), ("kasahara", c.get("kasahara"))):
        if v and not o.at[i, col]:
            o.at[i, col] = v
    srcs = [s_.get("url") for s_ in (c.get("rsources") or []) if isinstance(s_, dict) and s_.get("url")]
    if srcs and not o.at[i, "rsrc"]:
        o.at[i, "rsrc"] = srcs[0]
print(f"hand-checked entries matched: {matched_cur}/{len(CUR)}; unmatched ({len(unmatched)}): {unmatched[:20]}")
closed_v = []
for f in sorted(glob.glob(f"{DATA}/research/closed*.json")):
    for c in json.load(open(f)):
        if c.get("name"):
            closed_v.append({"name": c["name"], "address": c.get("address"), "city": c.get("city"), "match_names": [c["name"].upper()]})
gone = [(c["name"], o.name_out.iat[b]) for c in closed_v for b in [match_curated(c)] if b is not None]
drop_closed = {o.index[b] for c in closed_v for b in [match_curated(c)] if b is not None}
o = o.drop(index=list(drop_closed)).reset_index(drop=True)
print("verified closed, removed:", len(drop_closed), gone[:20])
hct = o.hc_tags.fillna("")
HC_PAT = {"teriyaki": "teriyaki", "pho": "pho", "oysters": "oysters|seafood", "drivein": "drive-?in", "espresso": "espresso"}
for t in TAGS:
    o["hc_" + t] = hct.str.contains(r"(?:^|;)(?:" + HC_PAT[t] + r")(?:;|$)", regex=True)
    o["t_" + t] |= o["hc_" + t]
o.loc[o.hc_teriyaki & o.brand_n.isna() & ~o.cuisine.isin(["Japanese & Sushi"]), "cuisine"] = "Teriyaki"
o["honored"] = o.jbf.notna() | o.icon.notna() | (o.hc & hct.str.contains("oldest|icon"))
shop = o.get("shop", pd.Series(False, index=o.index)).fillna(False).astype(bool)
o.loc[o.honored & ~shop, "venue"] = False
o.loc[o.hc & ~shop, "venue"] = False
o.loc[shop & o.jbf.isna(), "venue"] = True   # a shop is an icon but not a restaurant, unless James Beard honored it as one (Beast & Cleaver)
o["bar"] = o.cat.isin(["bar", "brewery"]) | (o.cuisine == "Bar & Pub")

# ---------------------------------------------------------------- King County: the official rating and inspection facts
o["lic"] = [F.lic.iat[int(j)] if j == j and j is not None else None for j in o.off]
kc = [KB.loc[l[3:]] if isinstance(l, str) and l.startswith("KC-") and l[3:] in KB.index else None for l in o.lic]
RATING = {"Excellent": 4, "Good": 3, "Okay": 2, "Needs To Improve": 1}
o["kc_rating"] = [r_.grade if r_ is not None and r_.active and r_.grade in RATING else None for r_ in kc]
for col, fld in (("kc_lr_date", "lr_date"), ("kc_lr_result", "lr_result"), ("kc_lr_red", "lr_red"), ("kc_n", "n_routine"), ("kc_unsat", "n_unsat"),
                 ("kc_avg_red", "avg_red"), ("kc_return", "n_return"), ("kc_closure", "last_closure"), ("kc_risk", "risk"), ("kc_last", "last_date"),
                 ("kc_class", "classification"), ("kc_seating", "seating")):
    o[col] = [r_[fld] if r_ is not None and r_.active else None for r_ in kc]
print("places with King County's official rating:", int(o.kc_rating.notna().sum()), o.kc_rating.value_counts().to_dict())

# ---------------------------------------------------------------- sales / profit: the Chicago model (artifact only)
auv = {a["brand"]: a for a in json.load(open(f"{DATA}/chain_auv.json")) if a.get("auv_usd")}
med_rev = o[o.reviews.notna() & (o.chain_n < 5)].groupby("price").reviews.median()
rel = (o.reviews + 10) / (o.price.map(med_rev) + 10)
bump = np.where(o.bar, 1.15, 1.0)
o["rev"] = (o.price.map(BASE) * bump * rel.fillna(0.6) ** B_FIT).clip(100_000, 40_000_000)
o["rev_src"] = np.where(o.reviews.notna(), "model", "model-low")
n_auv = 0
for b, a in auv.items():
    sel_ = o.brand_n == b
    if not sel_.any():
        continue
    n_auv += 1
    med = o.loc[sel_, "reviews"].median()
    r_ = (o.loc[sel_, "reviews"] / med) ** 0.35 if med == med else pd.Series(np.nan, index=o.index[sel_])
    o.loc[sel_, "rev"] = a["auv_usd"] * r_.fillna(0.85).clip(0.6, 1.5)
    o.loc[sel_, "rev_src"] = "chain"
o.loc[o.venue & o.rev_src.isin(["model", "model-low"]), "rev_src"] = "venue"
m_rat = o.rating.mean()
o["bayes"] = (o.reviews * o.rating + 40 * m_rat) / (o.reviews + 40)
margin = o.price.map(MARGIN)
margin = o.cuisine.map(MARGIN_CUISINE).fillna(margin) * (0.8 + 0.4 * pct(o.bayes).fillna(40) / 100)
o["margin"] = margin.round(4)
o["profit"] = o.rev * o.margin
o["food_cost"] = o.cuisine.map(FOOD_COST).fillna(30)
o["value_raw"] = o.bayes - 0.18 * (o.price - 1)
jb = o.jbf.fillna("")
acc = (jb.str.contains("America's Classic") * 35 + jb.str.contains(r"\bWinner\b") * 22
       + (jb.str.contains(r"\bFinalist\b") & ~jb.str.contains(r"\bWinner\b")) * 12 + (jb.str.contains("Semifinalist") & ~jb.str.contains(r"\bFinalist\b")) * 5
       + o.icon.notna() * 24 + o.honors.notna() * 6 + o.hc_tags.fillna("").str.contains("oldest") * 18).clip(upper=48)
years = (2026 - pd.to_numeric(o.founded, errors="coerce")).clip(lower=0)
o["s_icon"] = np.where(o.honored, (acc + years.fillna(0).clip(upper=80) / 80 * 32 + pct(np.log1p(o.reviews)).fillna(0) / 100 * 20).clip(upper=100), np.nan)


def r(x, n=0):
    if x is None or (isinstance(x, float) and x != x):
        return None
    return int(round(float(x))) if n == 0 else round(float(x), n)


# map listings the research found to be bad copies of a listed place (a mistyped street number), each with a source
for dl in (json.load(open(f"{DATA}/research/drop_listings.json")) if os.path.exists(f"{DATA}/research/drop_listings.json") else []):
    hit = (o.name_out.str.upper() == dl["name"].upper()) & (o.city == dl["town"]) & (o.street.fillna("").str.upper() == dl["street"].upper())
    print("dropped listing:", dl["name"], dl["street"], int(hit.sum()))
    o = o[~hit]
# hand-checked places that still have no spot: the US Census geocoder's match for the verified street address (geocode_research.py)
GEOCACHE2 = json.load(open(f"{DATA}/research/geocode_census.json")) if os.path.exists(f"{DATA}/research/geocode_census.json") else {}
todo2 = []
for i in o.index[o.lat.isna() & o.hc]:
    a_, t_ = (o.at[i, "street"] or "").split(",")[0].strip(), (o.at[i, "city"] or "").strip()
    q = f"{a_}, {t_}, WA {o.at[i, 'zip'] or ''}".strip()
    hit = GEOCACHE2.get(q)
    if hit:
        o.at[i, "lat"], o.at[i, "lon"] = hit["lat"], hit["lon"]
    else:
        todo2.append(q)
if todo2:
    json.dump(sorted(set(json.load(open(f"{DATA}/research/geocode_todo.json")) + todo2)), open(f"{DATA}/research/geocode_todo.json", "w"), indent=1)
    print("hand-checked places without a spot, waiting for the Census geocoder:", todo2)
o = o[o.lat.notna() | o.official].reset_index(drop=True)
if APP:
    fixes = json.load(open(f"{DATA}/research/name_fixes.json")) if os.path.exists(f"{DATA}/research/name_fixes.json") else []
    for fx in fixes:
        hit = (o.name_out.str.upper() == fx["name"].upper()) & (o.city == fx["town"]) & o.street.fillna("").str.startswith(fx["street_number"] + " ")
        o.loc[hit, "name_out"] = fx["fixed"]
        print("name fix:", fx["name"], "->", fx["fixed"], int(hit.sum()))
    # the same place twice: same name at the same street address, or (not a chain) same name in the same town within 400 m.
    # The licensed record wins, then a confirmed listing, then the one with more facts; the kept copy inherits what the dropped one knew.
    rank = o.tier.map({"official": 2, "both": 1, "listing": 0}).fillna(0) * 10 + o.hc.astype(int) * 5 + o.get("web", pd.Series(None, index=o.index)).notna().astype(int)
    keyname = o.name_out.map(norm_name)
    keyaddr = [k[0] + "|" + undir(k[1]) if all(k := street_key(s_)) else None for s_ in o.street]   # same name + number + street, direction or not
    drop, merged, seen = set(), [], {}
    for i in o.index:
        if keyaddr[o.index.get_loc(i)] and keyname[i]:
            k = (keyname[i], keyaddr[o.index.get_loc(i)])
            if k in seen:
                j = seen[k]
                lose = i if rank[i] <= rank[j] else j
                drop.add(lose); seen[k] = j if lose == i else i
                merged.append((seen[k], lose))
            else:
                seen[k] = i
    single = o[(o.chain_n.fillna(1) < 2) & o.lat.notna() & ~o.index.isin(drop)]
    for (nm_, town), g in single.groupby([keyname[single.index], single.city]):
        if len(g) < 2 or not nm_:
            continue
        idx = list(g.index)
        for a_ in range(len(idx)):
            for b_ in range(a_ + 1, len(idx)):
                i, j = idx[a_], idx[b_]
                if i in drop or j in drop:
                    continue
                dkm = math.hypot((o.at[j, "lat"] - o.at[i, "lat"]) * 111, (o.at[j, "lon"] - o.at[i, "lon"]) * 75)
                if dkm < 0.4:
                    lose = i if rank[i] <= rank[j] else j
                    drop.add(lose)
                    merged.append((j if lose == i else i, lose))
    INHERIT = [c for c in o.columns if c.startswith(("t_", "hc_"))] + ["hc", "honored"]
    for keep_, lose in merged:
        if o.at[keep_, "lat"] != o.at[keep_, "lat"] and o.at[lose, "lat"] == o.at[lose, "lat"]:   # a record with no spot takes its twin's
            o.at[keep_, "lat"], o.at[keep_, "lon"] = o.at[lose, "lat"], o.at[lose, "lon"]
        for col in INHERIT:
            if col in o.columns and bool(o.at[lose, col]) and not bool(o.at[keep_, col]):
                o.at[keep_, col] = o.at[lose, col]
        for col in ("dishes", "rnote", "rsite", "rsrc", "web", "phone", "founded", "brand_founded", "icon", "jbf", "honors", "s_icon", "kasahara", "hc_tags",
                    "kc_rating", "kc_lr_date", "kc_lr_result", "kc_lr_red", "kc_n", "kc_unsat", "kc_avg_red", "kc_return", "kc_closure", "kc_risk", "lic"):
            if col in o.columns and (pd.isna(o.at[keep_, col]) if not isinstance(o.at[keep_, col], str) else o.at[keep_, col] == "") and not pd.isna(o.at[lose, col]):
                o.at[keep_, col] = o.at[lose, col]
    print("duplicates removed for the app:", len(drop), [o.at[i, "name_out"] for i in list(drop)[:8]])
    o = o.drop(index=list(drop))
    webs = o.get("web", pd.Series("", index=o.index)).fillna("").astype(str) + " " + o.rsite.fillna("").astype(str)
    adult = o.name_out.str.contains(r"gentlem[ae]n'?s club|exotic dancer|strip club|adult entertainment|\bdeja vu\b|bikini (?:bar|club)", case=False, regex=True) \
        | webs.str.contains(r"centerfolds|gentlemensclub|stripclub|dejavu", case=False, regex=True)
    print("adult clubs removed:", int(adult.sum()), o.name_out[adult].tolist())
    o = o[~adult]
    smoke = o.name_out.str.contains(r"\bvape\b|smoke shop|\btobacco\b|cigar lounge|\bcbd\b|dispensary|head shop|cannabis|marijuana", case=False, regex=True)
    o.loc[smoke, "venue"] = True
    print("smoke/vape/cannabis shops hidden with non-restaurants:", int(smoke.sum()))


def clean_url(u):
    """Website links without tracking parameters (Reserve with Google tokens, utm_*, click ids)."""
    base, _, q = u.partition("?")
    keep_ = [kv for kv in q.split("&") if kv and not re.match(r"(rwg_token|utm_[a-z]+|fbclid|gclid|y_source)=", kv)]
    return base + ("?" + "&".join(keep_) if keep_ else "")


RCODE = {"Excellent": 4, "Good": 3, "Okay": 2, "Needs To Improve": 1}
RESCODE = {"Satisfactory": 1, "Unsatisfactory": 2, "Complete": 3}
COUNTIES = sorted({n for n, _ in _cp})
if APP:
    nv = o[~o.venue]
    CITIES = sorted(o.city.dropna().unique().tolist()); CUIS = sorted(o.cuisine.unique().tolist()); BRANDS = sorted(o.brand_n.dropna().unique().tolist())
    ci, cu, br, coi = {c: i for i, c in enumerate(CITIES)}, {c: i for i, c in enumerate(CUIS)}, {c: i for i, c in enumerate(BRANDS)}, {c: i for i, c in enumerate(COUNTIES)}
    TIER = {"listing": 0, "both": 1, "official": 2}
    SRCS = ["official", "meta", "AllThePlaces", "DAC", "research", "BrightQuery", "Foursquare", "Microsoft"]
    places, seen_ids = [], set()
    LINKS = json.load(open(f"{WA}/website_check.json")) if os.path.exists(f"{WA}/website_check.json") else None
    link_drops, link_cands = collections.Counter(), {}
    for i, x in o.iterrows():
        idsrc = f"{norm_name(x.name_out)}|{round(float(x.lat), 3)}|{round(float(x.lon), 3)}" if x.lat == x.lat else f"{norm_name(x.name_out)}|{x.get('lic') or x.get('id')}"
        p = {"id": hashlib.md5(idsrc.encode()).hexdigest()[:12], "n": x.name_out, "c": ci.get(x.city) if isinstance(x.city, str) else None,
             "cu": cu[x.cuisine], "t": TIER[x.tier], "s": SRCS.index(x.src) if x.src in SRCS else 1}
        if isinstance(x.county, str): p["co"] = coi[x.county]
        if isinstance(x.street, str): p["a"] = nice(x.street, addr=True)
        if isinstance(x.zip, str) and re.match(r"^9(?:8\d|9[0-4])\d{2}", x.zip): p["z"] = x.zip[:5]
        if x.lat == x.lat: p["la"], p["lo"] = round(float(x.lat), 5), round(float(x.lon), 5)
        if isinstance(x.brand_n, str): p["b"] = br[x.brand_n]
        if x.chain_n and int(x.chain_n) > 1: p["ch"] = int(x.chain_n)
        if x.venue: p["v"] = 1
        if x.bar: p["bar"] = 1
        tags = sum(1 << bi for bi, tg in enumerate(TAGS) if bool(x["t_" + tg]))
        if tags: p["g"] = tags
        hcg = sum(1 << bi for bi, tg in enumerate(TAGS) if bool(x["hc_" + tg]))
        if x.hc: p["hc"] = hcg or 1 << 7   # which guides it's hand-checked for (bit 7: honors/history only)
        if x.honored:
            jb_ = x.jbf or ""
            p["h"] = (1 if "America's Classic" in jb_ else 0) | (2 if re.search(r"\bWinner\b", jb_) else 0) | (4 if re.search(r"(?<!Semi)Finalist", jb_) else 0) \
                | (8 if "Semifinalist" in jb_ else 0) | (16 if isinstance(x.icon, str) or "oldest" in (x.hc_tags or "") else 0)
            p["ip"] = round(float(x.s_icon), 1) if x.s_icon == x.s_icon else 0
            for k, v in (("icon", x.icon), ("jbf", x.jbf), ("hon", x.honors)):
                if isinstance(v, str) and k == "hon":
                    v = "; ".join(h for h in v.split("; ") if not re.search(
                        r"forbes|readers'? ?choice|reader'?s choice|\bsays\b|\bvote[ds]?\b|\bpoll\b|yelp|tripadvisor|opentable|\bstars?\b", h, re.I)) or None
                if isinstance(v, str): p[k] = v
        if x.founded == x.founded and x.founded is not None: p["f"] = int(float(x.founded))
        if x.brand_founded == x.brand_founded and x.brand_founded is not None: p["bf"] = int(float(x.brand_founded))
        for k, col in (("di", "dishes"), ("note", "rnote"), ("src", "rsrc")):
            if isinstance(x[col], str) and x[col]: p[k] = x[col]
        if x.kasahara is True: p["ks"] = 1
        web = x.rsite if isinstance(x.rsite, str) else (x.web if isinstance(x.get("web"), str) else None)
        if web:
            w_ = clean_url(web)
            link_cands[w_] = x.brand_n if isinstance(x.brand_n, str) else x.name_out
            if re.search(r"(^|\.|//)(?:widgets\.)?(?:resy|exploretock|sevenrooms|opentable)\.com", w_):
                link_drops["booking widget, not the place's own page"] += 1
            elif re.search(r"(^|\.|//)toshisgrill\.com", w_) and x.kasahara is not True:
                link_drops["Kasahara's own site, not this shop's"] += 1   # toshisgrill.com is Toshi's Teriyaki Grill (Mill Creek) only
            elif LINKS is not None and LINKS.get(w_, {}).get("ok"):
                p["w"] = w_
            else:
                link_drops[(LINKS or {}).get(w_, {}).get("why", "not checked yet")] += 1
        if isinstance(x.get("phone"), str) and x.phone: p["ph"] = x.phone
        if isinstance(x.kc_rating, str) or isinstance(x.kc_lr_date, str):
            kcd = {"r": RCODE.get(x.kc_rating), "d": x.kc_lr_date if isinstance(x.kc_lr_date, str) else None, "res": RESCODE.get(x.kc_lr_result), "red": r(x.kc_lr_red), "n": r(x.kc_n),
                   "u": r(x.kc_unsat), "rt": r(x.kc_return), "cl": x.kc_closure if isinstance(x.kc_closure, str) else None, "risk": r(x.kc_risk)}
            p["kc"] = {k: v for k, v in kcd.items() if v is not None}
        while p["id"] in seen_ids:
            p["id"] = p["id"] + "x"
        seen_ids.add(p["id"])
        places.append(p)
    print("website links dropped:", sum(link_drops.values()), link_drops.most_common(8))
    json.dump(link_cands, open(f"{WA}/website_candidates.json", "w"), indent=0, ensure_ascii=False)
    out = {"v": 1, "generated": GENERATED, "records_through": OFFICIAL.RECORDS_THROUGH.strftime("%Y-%m-%d"), "king_fetched": OFFICIAL.KING_FETCHED,
           "cities": CITIES, "cuisines": CUIS, "brands": BRANDS, "counties": COUNTIES, "tags": TAGS, "sources": SRCS,
           "count": len(places), "count_restaurants": int(len(nv)), "calibration": calib, "places": places}
    os.makedirs(SITE, exist_ok=True)
    json.dump(out, open(f"{SITE}/places.json", "w"), separators=(",", ":"), ensure_ascii=False, allow_nan=False, default=str)
    json.dump(json.load(open(f"{WA}/wa_shapes.json")), open(f"{SITE}/wa_shapes.json", "w"), separators=(",", ":"))
    print("APP: wrote", len(places), "places (", len(nv), "restaurants ) |", os.path.getsize(f"{SITE}/places.json") // 1024, "KB | tiers:",
          nv.tier.value_counts().to_dict(), "| tags:", {tg: int(nv["t_" + tg].sum()) for tg in TAGS}, "| hand-checked:",
          {tg: int(nv["hc_" + tg].sum()) for tg in TAGS}, "| honored:", int(nv.honored.sum()))
    sys.exit(0)

CITIES = sorted(o.city.dropna().unique().tolist()); CUIS = sorted(o.cuisine.unique().tolist()); BRANDS = sorted(o.brand_n.dropna().unique().tolist())
ci, cu, br, coi = {c: i for i, c in enumerate(CITIES)}, {c: i for i, c in enumerate(CUIS)}, {c: i for i, c in enumerate(BRANDS)}, {c: i for i, c in enumerate(COUNTIES)}
SRC = {"model": 0, "model-low": 1, "chain": 2, "reported": 3, "venue": 4}
TIER = {"listing": 0, "both": 1, "official": 2}
SCALE = {"lat": 10000, "lon": 10000, "rating": 10, "margin": 1000, "value_raw": 1000}
SRCS = ["official", "meta", "AllThePlaces", "DAC", "research", "BrightQuery", "Foursquare", "Microsoft"]
C = collections.OrderedDict((c, []) for c in ["name", "addr", "city", "county", "zip", "lat", "lon", "cuisine", "brand", "chain_n", "rating", "reviews", "price",
                                               "price_est", "rev_k", "rev_src", "margin", "value_raw", "tier", "bar", "venue", "tags", "hc", "src"])
SP = {"hon": [], "insp": []}
extra = {}
for i, x in o.iterrows():
    tags = sum(1 << b for b, t in enumerate(TAGS) if bool(x["t_" + t]))
    hcg = sum(1 << b for b, t in enumerate(TAGS) if bool(x["hc_" + t])) | (128 if x.hc else 0)
    z = int(x.zip[:5]) if isinstance(x.zip, str) and re.match(r"^9(?:8\d|9[0-4])\d{2}", x.zip) else None
    vals = {"name": x.name_out, "addr": nice(x.street, addr=True) if isinstance(x.street, str) else None,
            "city": ci.get(x.city) if isinstance(x.city, str) else None, "county": coi.get(x.county) if isinstance(x.county, str) else None,
            "zip": z, "lat": x.lat, "lon": x.lon, "cuisine": cu[x.cuisine],
            "brand": br.get(x.brand_n) if isinstance(x.brand_n, str) else None, "chain_n": int(x.chain_n), "rating": x.rating, "reviews": r(x.reviews),
            "price": int(x.price), "price_est": int(x.price_est), "rev_k": int(round(x.rev / 1000)), "rev_src": SRC[x.rev_src], "margin": x.margin,
            "value_raw": x.value_raw, "tier": TIER[x.tier], "bar": int(bool(x.bar)), "venue": int(bool(x.venue)), "tags": tags, "hc": hcg,
            "src": SRCS.index(x.src) if x.src in SRCS else 1}
    if x.honored:
        jb_ = x.jbf or ""
        flags = (1 if "America's Classic" in jb_ else 0) | (2 if re.search(r"\bWinner\b", jb_) else 0) | (4 if re.search(r"(?<!Semi)Finalist", jb_) else 0) \
            | (8 if "Semifinalist" in jb_ else 0) | (16 if isinstance(x.icon, str) or "oldest" in (x.hc_tags or "") else 0)
        SP["hon"].append([i, int(round((x.s_icon if x.s_icon == x.s_icon else 0) * 10)), flags])
    if isinstance(x.kc_rating, str):
        SP["insp"].append([i, RCODE[x.kc_rating], r(x.kc_avg_red, 1) if x.kc_avg_red == x.kc_avg_red and x.kc_avg_red is not None else None, r(x.kc_n), r(x.kc_unsat)])
    for c, v in vals.items():
        if c in SCALE:
            v = None if v is None or v != v else int(round(float(v) * SCALE[c]))
        elif isinstance(v, float):
            v = None if v != v else v
        C[c].append(v.item() if hasattr(v, "item") else v)
    e = {}
    if x.honored or x.hc:
        e.update({k: v for k, v in (("jbf", x.jbf), ("honors", x.honors), ("icon", x.icon), ("founded", r(x.founded)), ("brand_founded", r(x.brand_founded)),
                                    ("dishes", x.dishes), ("note", x.rnote), ("src", x.rsrc), ("kasahara", True if x.kasahara is True else None))
                  if v is not None and v == v})
    if x.official:
        e["lic"] = x.lic if isinstance(x.lic, str) else (x.id if isinstance(x.id, str) and x.id.startswith("KC-") else None)
        e["found"] = "list" if x.src == "official" else "match"
    if isinstance(x.kc_lr_date, str):
        e.update({"kc_rating": x.kc_rating, "kc_date": x.kc_lr_date, "kc_result": x.kc_lr_result, "kc_red": r(x.kc_lr_red), "kc_n": r(x.kc_n),
                  "kc_unsat": r(x.kc_unsat), "kc_return": r(x.kc_return), "kc_closure": x.kc_closure, "kc_risk": r(x.kc_risk)})
    e = {k: v for k, v in e.items() if v is not None and not (isinstance(v, float) and v != v)}
    if e:
        extra[i] = e
nv = o[~o.venue]
meta = {"generated": GENERATED, "records_through": OFFICIAL.RECORDS_THROUGH.strftime("%Y-%m-%d"), "king_fetched": OFFICIAL.KING_FETCHED,
        "cities": CITIES, "counties": COUNTIES, "cuisines": CUIS, "brands": BRANDS, "src": list(SRC), "tiers": list(TIER), "tags": TAGS,
        "food_cost": {k: v for k, v in FOOD_COST.items()}, "spend": SPEND, "count": len(o), "count_restaurants": int(len(nv)),
        "count_official": int(nv.official.sum()), "count_both": int((nv.tier == "both").sum()), "count_listing": int((nv.tier == "listing").sum()),
        "n_cities": int(nv.city.nunique()), "overture_release": "2026-09-23.1", "rating_mean": round(float(m_rat), 3),
        "model": {"b": B_FIT, "n_chains": n_auv}, "calibration": calib, "n_honored": int(o.honored.sum()), "n_hc": int(o.hc.sum()),
        "n_kc_rated": int(nv.kc_rating.notna().sum()), "srcs": SRCS,
        "coverage_county": json.load(open(f"{WA}/coverage_county.json")) if os.path.exists(f"{WA}/coverage_county.json") else []}
for _k, _v in list(C.items()) + list(SP.items()):
    _bad = [j for j, x in enumerate(_v) if (isinstance(x, float) and x != x) or (isinstance(x, list) and any(isinstance(y, float) and y != y for y in x))]
    if _bad: print("NaN in", _k, len(_bad), _v[_bad[0]])
os.makedirs(SITE, exist_ok=True)
json.dump({"n": len(o), "scale": SCALE, "cols": C, "sparse": SP, "meta": meta},
          open(f"{SITE}/washington.json", "w"), separators=(",", ":"), allow_nan=False, default=str)
json.dump({"n": len(o), "extra": {str(k): v for k, v in extra.items()}}, open(f"{SITE}/wa_detail.json", "w"), separators=(",", ":"), allow_nan=False, default=str)
json.dump(json.load(open(f"{WA}/wa_shapes.json")), open(f"{SITE}/wa_shapes.json", "w"), separators=(",", ":"))
o.to_pickle(f"{WA}/stage2.pkl")
print("wrote", len(o), "places (", int(len(nv)), "restaurants ) in", nv.city.nunique(), "towns;", os.path.getsize(f"{SITE}/washington.json") // 1024,
      "KB | tiers:", nv.tier.value_counts().to_dict(), "| top towns:", nv.city.value_counts().head(8).to_dict(),
      "| tags:", {tg: int(nv["t_" + tg].sum()) for tg in TAGS}, "| by county:", nv.county.value_counts().head(12).to_dict())
