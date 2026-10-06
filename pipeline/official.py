"""Official records for Washington.

There is no statewide restaurant or inspection list. What exists in bulk:
- King County (Public Health – Seattle & King County): "Food Establishment Inspection Data", data.kingcounty.gov r878-4sxa, Public Domain.
  One row per violation (an inspection without violations is one row), 2021 to the present, no coordinates. `Grade` is the business's
  current official food safety rating (Excellent / Good / Okay / Needs To Improve / Not Rated / Rating Not Available). We show it,
  labeled official, and never recompute it.
- City of Seattle "Active Business License Tax Certificate" (data.seattle.gov wnbq-64tb, Public Domain): NAICS-coded, includes
  sole proprietors whose trade name can be a person's name, so it's used for calibration only and never shown.
- Washington State Liquor and Cannabis Board "On Premise" licensee list (lcb.wa.gov frequently requested lists): statewide places
  licensed to serve alcohol. The page cites RCW 42.56.070(8) (no commercial use) and warns of a data-transfer issue: used here for
  calibration only until Nick decides. `Licensee` (a person's name) is never read.

load() returns one table of official records with a normalized name key, street number and street key, coordinates (placed on
Overture address points), the source ("king", "seattle", "lcb") and a kind.
"""
import os, re, json
import numpy as np, pandas as pd
from common import norm_name, RAW, WA, street_key, street_nums, canon_city, name_sim, _stems, GENERIC

OFF = os.path.join(RAW, "official")
# King County publishes through the last week; the dataset said "current from 1/1/2021 to 10/02/2026" when fetched on 2026-10-05.
# Inspections are entered days to weeks late, so everything after RECORDS_THROUGH is dropped and every date shown derives from it.
RECORDS_THROUGH = pd.Timestamp("2026-09-25")
KING_FETCHED = "2026-10-05"
ACTIVE_SINCE = RECORDS_THROUGH - pd.DateOffset(months=18)   # a business inspected in the last 18 months is treated as operating
KING_RESTAURANT = {"General Food Services", "General Food Service", "Limited Food Service", "Bakery"}
KING_RETAIL = {"Grocery Store", "Meat/Fish Market"}


def _names(*vals):
    out = []
    for v in vals:
        if not isinstance(v, str):
            continue
        for part in re.split(r"\s*/\s*|\s+\bdba\b\s+|\s+\bd/b/a\b\s+", v, flags=re.I):
            k = norm_name(re.sub(r"\b(?:LLC|INC|CORP|CORPORATION|LTD|CO)\b\.?", "", part, flags=re.I))
            if k and k not in out:
                out.append(k)
    return out


# ---------------------------------------------------------------- address points (Overture addresses theme) -> coordinates
class Geocoder:
    """Places a street address on Overture's address points: the same number and street key, preferring the same zip, then the same
    town; refuses when the matching points spread over more than 1 km (the same address in two towns)."""

    def __init__(self):
        ap = pd.read_parquet(f"{WA}/addresses_wa.parquet", columns=["number", "street", "postcode", "postal_city", "state", "muni", "lat", "lon"])
        ap = ap[ap.state == "WA"]
        ap["skey"] = [street_key(f"{n} {s}")[1] for n, s in zip(ap.number.astype(str), ap.street.fillna(""))]
        ap = ap[ap.skey.notna()]
        towns = {t: (canon_city(t) or "").lower() for t in set(ap.postal_city.dropna()) | set(ap.muni.dropna())}
        self.by = {}
        for n, k, la, lo, pc, pci, mu in zip(ap.number.astype(str), ap.skey, ap.lat, ap.lon, ap.postcode, ap.postal_city, ap.muni):
            self.by.setdefault((n, k), []).append((la, lo, pc[:5] if isinstance(pc, str) else "", towns.get(pci, ""), towns.get(mu, "")))

    def __call__(self, addr, city=None, zip5=None):
        num, sk = street_key(addr)
        if not num:
            return None
        pts = self.by.get((num, sk), [])
        if not pts:
            return None
        town = (canon_city(city) or "").lower()
        for sel in ([p for p in pts if zip5 and p[2] == zip5], [p for p in pts if town and town in (p[3], p[4])], pts):
            if sel:
                la, lo = float(np.median([p[0] for p in sel])), float(np.median([p[1] for p in sel]))
                if max(np.hypot((p[0] - la) * 111, (p[1] - lo) * 75) for p in sel) <= 1.0:
                    return la, lo, sel[0][2]
                return None
        return None


# ---------------------------------------------------------------- King County inspections
def king_inspections():
    """One row per inspection (violation rows rolled up): date, type, result, red/blue points, closure, pest-item flag."""
    k = pd.read_csv(f"{OFF}/king/r878-4sxa.csv", dtype=str)
    k["d"] = pd.to_datetime(k["Inspection Date"], format="%m/%d/%Y")
    k = k[k.d <= RECORDS_THROUGH]
    k["pts"] = pd.to_numeric(k["Violation Points"], errors="coerce").fillna(0)
    k["red_pts"] = np.where(k["Violation Type"] == "RED", k.pts, 0)
    k["blue_pts"] = np.where(k["Violation Type"] == "BLUE", k.pts, 0)
    k["is_red"] = (k["Violation Type"] == "RED").astype(int)
    # 3200 "Insects, rodents, animals not present; entrance controlled" also covers door gaps: counted as a pest-control item, never as "rodents"
    k["pest_item"] = k["Violation Description"].fillna("").str.startswith("3200").astype(int)
    g = k.groupby("Inspection_Serial_Num")
    i = g.agg(biz=("Business_ID", "first"), d=("d", "first"), typ=("Inspection Type", "first"), res=("Inspection Result", "first"),
              closed=("Inspection Closed Business", "first"), red=("red_pts", "sum"), blue=("blue_pts", "sum"), n_red=("is_red", "sum"),
              pest=("pest_item", "max"))
    i["routine"] = i.typ.str.startswith("Routine")
    return i.reset_index()


def king_businesses():
    """One row per King County business permit (Business_ID): name, address, classification, risk, seating, the official rating,
    and inspection facts through RECORDS_THROUGH."""
    k = pd.read_csv(f"{OFF}/king/r878-4sxa.csv", dtype=str)
    k["d"] = pd.to_datetime(k["Inspection Date"], format="%m/%d/%Y")
    k = k[k.d <= RECORDS_THROUGH]
    last = k.sort_values("d").groupby("Business_ID").tail(1).set_index("Business_ID")
    first = k.groupby("Business_ID").d.min()
    i = king_inspections()
    r = i[i.routine].sort_values("d")
    lr = r.groupby("biz").tail(1).set_index("biz")
    since = r[r.d >= "2023-01-01"].groupby("biz")
    b = pd.DataFrame({
        "name": last.Name, "program": last["Program Identifier"], "addr": last.Address, "city": last.City.map(canon_city), "zip": last["Zip Code"].str[:5],
        "classification": last.Classification, "risk": last["Risk Category"], "seating": last["Seating Range"], "grade": last.Grade,
        "parcel": last["Parcel Number"], "first_seen": first.dt.strftime("%Y-%m-%d"), "last_date": i.groupby("biz").d.max().dt.strftime("%Y-%m-%d"),
    })
    b["lr_date"] = lr.d.dt.strftime("%Y-%m-%d").reindex(b.index)
    b["lr_result"] = lr.res.reindex(b.index)
    b["lr_red"] = lr.red.reindex(b.index)
    b["lr_blue"] = lr.blue.reindex(b.index)
    b["n_routine"] = since.size().reindex(b.index).fillna(0).astype(int)
    b["n_unsat"] = since.res.apply(lambda s: int((s == "Unsatisfactory").sum())).reindex(b.index).fillna(0).astype(int)
    b["avg_red"] = since.red.mean().reindex(b.index)
    rets = i[i.typ.str.startswith("Return") & (i.d >= "2023-01-01")].groupby("biz").size()
    b["n_return"] = rets.reindex(b.index).fillna(0).astype(int)
    cl = i[(i.closed == "Yes")].groupby("biz").d.max()
    b["last_closure"] = cl.dt.strftime("%Y-%m-%d").reindex(b.index)
    b["active"] = pd.to_datetime(b.last_date) >= ACTIVE_SINCE
    b.index.name = "business_id"
    return b.reset_index()


def king_display_name(n):
    """'#807 TUTTA BELLA' -> 'TUTTA BELLA'; 'STARBUCKS #12345' -> 'STARBUCKS'."""
    n = re.sub(r"^#\s*\d+\s*", "", n or "")
    n = re.sub(r"\s*#\s*\d+\w*\s*$|\s+\d{3,}\s*$|\s*\(#?\d+\)\s*$", "", n)
    return n.strip(" -,")


def load(geocode=True):
    rows = []
    kb = king_businesses()
    for _, r in kb.iterrows():
        kind = "restaurant" if r.classification in KING_RESTAURANT else "retail" if r.classification in KING_RETAIL else \
            "mobile" if r.classification == "Mobile Food Unit" else "other"
        num, st = street_key(r.addr)
        nm = king_display_name(r["name"])
        rows.append({"jur": "king", "lic": "KC-" + r.business_id, "name": nm, "keys": _names(nm, r.program if isinstance(r.program, str) and len(r.program) > 3 else None),
                     "addr": r.addr, "city": r.city, "zip": r.zip, "num": num, "street": st, "kind": kind, "active": bool(r.active),
                     "since": r.first_seen, "classification": r.classification})
    s = pd.read_csv(f"{OFF}/seattle/wnbq-64tb.csv", dtype=str)
    s = s[s["NAICS Code"].fillna("").str.startswith("722") & s.City.fillna("").str.upper().eq("SEATTLE")]
    SK = {"722511": "restaurant", "722513": "restaurant", "722515": "restaurant", "722514": "restaurant", "722410": "tavern",
          "722330": "mobile", "722320": "caterer", "722310": "contractor"}
    for _, r in s.iterrows():
        num, st = street_key(r["Street Address"])
        # sole proprietors' trade names can be a person's name: kept as a match key only, never displayed
        rows.append({"jur": "seattle", "lic": "SEA-" + str(r["City Account Number"]), "name": r["Trade Name"], "keys": _names(r["Trade Name"]),
                     "addr": r["Street Address"], "city": "Seattle", "zip": str(r.Zip or "")[:5], "num": num, "street": st,
                     "kind": SK.get(str(r["NAICS Code"])[:6], "other"), "active": True, "since": r["License Start Date"], "classification": r["NAICS Description"]})
    lcb = pd.read_excel(f"{OFF}/lcb/On_Premise_09292026.xlsx", dtype=str, usecols=lambda c: c != "Licensee")
    lcb = lcb[lcb.Status.fillna("").str.startswith("ACTIVE")]
    for _, r in lcb.iterrows():
        pv = (r.Privilege or "").strip()
        kind = "tavern" if re.search(r"TAVERN|NIGHTCLUB", pv) else "venue" if re.search(
            r"HOTEL|SPORTS|THEATER|PRIVATE CLUB|CONVENTION|AIRPORT|FERRY|SHIP|NONPUBLIC|CARAVAN|AIRLINE|TRAIN|CATERER", pv) else \
            "snack" if pv.startswith("SNACK") else "restaurant"
        num, st = street_key(r["Loc Address"])
        rows.append({"jur": "lcb", "lic": "LCB-" + str(r["License Number"]), "name": r.Tradename, "keys": _names(r.Tradename),
                     "addr": r["Loc Address"], "city": canon_city(r["Loc City"]), "zip": str(r["Loc Zip"] or "")[:5], "num": num, "street": st,
                     "kind": kind, "active": True, "since": r["Business Startup Date"], "classification": pv, "county": (r.County or "").title()})
    df = pd.DataFrame(rows)
    df["lat"], df["lon"] = np.nan, np.nan
    if geocode:
        geo = Geocoder()
        hits = [geo(a, c, z) for a, c, z in zip(df.addr, df.city, df.zip)]
        df["lat"] = [h[0] if h else np.nan for h in hits]
        df["lon"] = [h[1] if h else np.nan for h in hits]
    # one business can hold several records (a King County permit, a Seattle license, a liquor license): same address and a name in common
    df["biz"] = np.arange(len(df))
    for (num, st), g in df[df.num.notna() & df.street.notna()].groupby(["num", "street"]):
        idx = list(g.index)
        for a in range(len(idx)):
            for b in range(a + 1, len(idx)):
                ka, kb_ = df.at[idx[a], "keys"], df.at[idx[b], "keys"]
                if (df.at[idx[a], "zip"] or "") != (df.at[idx[b], "zip"] or "") and df.at[idx[a], "zip"] and df.at[idx[b], "zip"]:
                    continue
                if any(name_sim(x, y) >= 85 or ((_stems(x) - GENERIC) & (_stems(y) - GENERIC)) for x in ka for y in kb_):
                    old, new = df.at[idx[b], "biz"], df.at[idx[a], "biz"]
                    df.loc[df.biz == old, "biz"] = new
    return df


if __name__ == "__main__":
    import time
    t = time.time()
    F = load()
    F.to_pickle(f"{WA}/official.pkl")
    print("records:", F.jur.value_counts().to_dict(), "| placed on address points:", F.groupby("jur").lat.apply(lambda s: round(s.notna().mean(), 3)).to_dict(),
          "| active:", F[F.active].jur.value_counts().to_dict(), round(time.time() - t), "s")
    print("King kinds (active):", F[(F.jur == "king") & F.active].kind.value_counts().to_dict())
