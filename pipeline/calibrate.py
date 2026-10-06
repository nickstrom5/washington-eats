"""How often is a map listing a real, licensed restaurant? Measured where official lists exist -> data/wa/calibration*.json

- King County: every Overture eating/drinking listing inside the county is checked against King County's food establishment records
  (businesses inspected in the last 18 months): same business name nearby, or the same street address with a distinctive name word.
- Seattle: listings inside city limits against the city's active business licenses with a food/drink NAICS code (722).
- Statewide, per county: the share of the liquor board's active on-premise licensees (restaurants and taverns) that the kept map
  listings contain. A lower bound on coverage, since a place licensed under a different name counts as a miss. (Calibration only:
  the LCB list carries a no-commercial-use note that Nick hasn't cleared.)
Adapted from wi-eats/pipeline/calibrate.py.
"""
import json
import numpy as np, pandas as pd
from shapely.geometry import shape, Point
from shapely.prepared import prep
from common import WA
from listings_util import official_match

o = pd.read_pickle(f"{WA}/stage1.pkl")
F = pd.read_pickle(f"{WA}/official.pkl")
areas = json.load(open(f"{WA}/calib_areas.json"))
king, sea = prep(shape(areas["King County|county"]).buffer(0.0003)), prep(shape(areas["Seattle|locality"]).buffer(0.0003))
o = o[~o.j_junk & ~o.j_outside].reset_index(drop=True)
o["in_king"] = [king.contains(Point(x, y)) for x, y in zip(o.lon, o.lat)]
o["in_sea"] = [sea.contains(Point(x, y)) for x, y in zip(o.lon, o.lat)]
print("listings inside King County:", int(o.in_king.sum()), "| inside Seattle:", int(o.in_sea.sum()))


def groups(L, app=False):
    s, conf = L.src.fillna("none"), L.confidence.fillna(0)
    if app:   # the App Store build can't use Google: group by Overture's own source and confidence
        return np.select([L.ov_closed, (s == "meta") & (conf >= 0.95), (s == "meta") & (conf >= 0.9), s.isin(["AllThePlaces", "DAC"]),
                          (s == "BrightQuery") & (conf >= 0.95), s == "meta"],
                         ["Overture says closed", "meta_high", "meta_mid", "brand_feed", "bq_high", "meta_low"], "other_sources")
    return np.select([L.closed21, L.ov_closed, (s == "meta") & L.in21, s == "meta", s.isin(["AllThePlaces", "DAC"]) & L.in21,
                      s.isin(["AllThePlaces", "DAC"]), L.in21, s == "Foursquare", s == "BrightQuery", s == "Microsoft"],
                     ["Google 2021 says closed", "Overture says closed", "Meta + open in Google 2021", "Meta only",
                      "brand feed + Google 2021", "brand feed only", "Foursquare/BrightQuery/Microsoft + Google 2021",
                      "Foursquare only", "BrightQuery only", "Microsoft only"], "other")


res = {}
for area, sel, R in (("king", o.in_king, F[(F.jur == "king") & F.active]), ("seattle", o.in_sea, F[(F.jur == "seattle") & F.kind.isin(["restaurant", "tavern"])])):
    L = o[sel].reset_index(drop=True)
    R = R.reset_index(drop=True)
    m = official_match(L, R)
    L["hit"] = L.index.map(lambda i: i in m)
    L["hit_rest"] = L.index.map(lambda i: i in m and R.kind.iat[m[i]] in ("restaurant", "tavern"))
    out = {"listings": int(len(L)), "official": int(len(R))}
    for name, app in (("artifact", False), ("app", True)):
        L["grp"] = groups(L, app)
        t = L.groupby("grp").agg(n=("id", "size"), official=("hit", "mean"), rest=("hit_rest", "mean")).sort_values("n", ascending=False)
        print(f"\n== {area} ({name} grouping): {len(L)} listings, {len(R)} official records")
        print(t.assign(official=(t.official * 100).round(1), rest=(t.rest * 100).round(1)).to_string())
        out[name] = {g: {"n": int(r.n), "official": round(float(r.official), 3), "rest": round(float(r.rest), 3)} for g, r in t.iterrows()}
    got = set(R.biz.iloc[list(m.values())])
    Rr = R[R.kind.isin(["restaurant", "tavern"])].drop_duplicates("biz")
    out["coverage_all_listings"] = round(float(np.mean([b in got for b in Rr.biz])), 3)
    # coverage by the listings the app keeps (Meta >= 0.9 or a chain store feed)
    keep = ((L.src == "meta") & (L.confidence.fillna(0) >= 0.9) | L.src.isin(["AllThePlaces", "DAC"])) & ~L.ov_closed & ~L.j_closedname
    mk = official_match(L[keep].reset_index(drop=True), R)
    gotk = set(R.biz.iloc[list(mk.values())])
    out["coverage_app_listings"] = round(float(np.mean([b in gotk for b in Rr.biz])), 3)
    out["official_restaurants"] = int(len(Rr))
    print(f"official restaurants/taverns (one per business) found among all listings: {out['coverage_all_listings']*100:.1f}%, among app-kept listings: "
          f"{out['coverage_app_listings']*100:.1f}% of {len(Rr)}")
    res[area] = out
json.dump(res, open(f"{WA}/calibration.json", "w"), indent=1)

# ---- per county: liquor board on-premise licensees (restaurants, taverns) found among the app-kept listings
cty = json.load(open(f"{WA}/wa_counties_detail.geojson"))["features"]
cp = [(f["properties"]["name"].replace(" County", ""), prep(shape(f["geometry"]).buffer(0.002))) for f in cty]
cx = [(f["properties"]["name"].replace(" County", ""), prep(shape(f["geometry"]))) for f in cty]
o["county"] = [next((n for n, p in cx if p.contains(Point(x, y))), None) or next((n for n, p in cp if p.contains(Point(x, y))), None)
               for x, y in zip(o.lon, o.lat)]   # the exact outline first, so county-line places keep their own county
keep = ((o.src == "meta") & (o.confidence.fillna(0) >= 0.9) | o.src.isin(["AllThePlaces", "DAC"])) & ~o.ov_closed & ~o.j_closedname & ~o.nowhere
lcb = F[(F.jur == "lcb") & F.kind.isin(["restaurant", "tavern"])].reset_index(drop=True)
rows = []
for c, _ in cp:
    L = o[keep & (o.county == c)].reset_index(drop=True)
    R = lcb[lcb.county == c].reset_index(drop=True)
    if not len(R):
        rows.append({"county": c, "listings_kept": int(len(L)), "lcb_on_premise": 0, "lcb_found": None}); continue
    m = official_match(L, R)
    got = set(R.biz.iloc[list(m.values())])
    rows.append({"county": c, "listings_kept": int(len(L)), "listings_all": int((o.county == c).sum()), "lcb_on_premise": int(R.biz.nunique()),
                 "lcb_found": round(float(np.mean([b in got for b in R.biz.unique()])), 3)})
cov = pd.DataFrame(rows).sort_values("listings_kept", ascending=False)
print("\n== per county: kept listings and liquor-licensed restaurants/taverns found among them\n" + cov.to_string(index=False))
cov.to_json(f"{WA}/coverage_county.json", orient="records", indent=1)
