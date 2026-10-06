"""Download the Overture Maps extracts that washington.py reads -> data/wa/

- overture_wa_bbox.parquet     every place in Washington's bounding box (name, category, address, point)
- overture_wa_sources.parquet  which datasets each eating/drinking listing in the box came from (Meta, Foursquare, ...)
- wa_state_detail.geojson      the state outline at full detail, for the in-state test (drops Portland, Idaho and B.C. rows)
- wa_counties_detail.geojson   the 39 county outlines at full detail, for the county of each place
- wa_shapes.json               simplified state and county outlines for the map (big lakes cut out of the drawing)

Reads the public Overture bucket over S3 with DuckDB (no account needed). Adapted from wi-eats/pipeline/fetch_overture.py.
"Washington" also means D.C. in map data: everything here is filtered by the bounding box and region code WA / US-WA.
"""
import os, json, time
import duckdb
from shapely import wkb
from shapely.geometry import mapping, Polygon
from shapely.ops import unary_union

RELEASE = "2026-09-23.1"
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "wa")
# Washington (45°33'N–49°N, 116°55'W–124°48'W) plus a margin for border towns; the polygon test does the rest
BBOX = "bbox.xmin BETWEEN -124.9 AND -116.8 AND bbox.ymin BETWEEN 45.5 AND 49.05"
EAT = "('restaurant','casual_eatery','bar','fast_food_restaurant','coffee_shop','cafe','smoothie_juice_bar','brewery','food_court')"
os.makedirs(OUT, exist_ok=True)

con = duckdb.connect()
con.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET s3_region='us-west-2';")
places = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=places/type=place/*.parquet"

t = time.time()
if not os.path.exists(f"{OUT}/overture_wa_bbox.parquet"):
    con.execute(f"""
COPY (
  SELECT id, names.primary AS name, basic_category AS cat, taxonomy.primary AS tax, taxonomy.hierarchy AS hier, confidence,
         operating_status AS status, brand.names.primary AS brand, addresses[1].freeform AS street, addresses[1].locality AS city,
         addresses[1].postcode AS zip, addresses[1].region AS region, ST_Y(geometry) AS lat, ST_X(geometry) AS lon, websites[1] AS web,
         phones[1] AS phone
  FROM read_parquet('{places}', hive_partitioning=1) WHERE {BBOX}
) TO '{OUT}/overture_wa_bbox.parquet' (FORMAT PARQUET)""")
    print("places in bbox", round(time.time() - t), "s", flush=True)
if not os.path.exists(f"{OUT}/overture_wa_sources.parquet"):
    con.execute(f"""
COPY (
  SELECT id, list_transform(sources, x -> x.dataset) AS ds, list_transform(sources, x -> x.update_time) AS ut,
         list_transform(sources, x -> x.record_id) AS rid,
         len(socials) AS n_soc, len(websites) AS n_web, len(phones) AS n_ph
  FROM read_parquet('{places}', hive_partitioning=1)
  WHERE {BBOX} AND basic_category IN {EAT}
) TO '{OUT}/overture_wa_sources.parquet' (FORMAT PARQUET)""")
    print("sources", round(time.time() - t), "s", flush=True)

areas = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=divisions/type=division_area/*.parquet"
water = f"s3://overturemaps-us-west-2/release/{RELEASE}/theme=base/type=water/*.parquet"
rows = con.execute(f"""
  SELECT subtype, names.primary AS name, ST_AsWKB(geometry) AS g
  FROM read_parquet('{areas}', hive_partitioning=1)
  WHERE country = 'US' AND region = 'US-WA' AND subtype IN ('region', 'county') AND class = 'land'
    AND bbox.xmin > -125.5 AND bbox.xmax < -116.5 AND bbox.ymin > 45.3 AND bbox.ymax < 49.2""").fetchall()
print("division areas:", len(rows), round(time.time() - t), "s", flush=True)
# big lakes and reservoirs (Lake Washington, Chelan, Roosevelt, Banks, Moses, Sammamish...) are cut from the drawn map, not from the state test
inland = con.execute(f"""
  SELECT names.primary, ST_AsWKB(geometry) FROM read_parquet('{water}', hive_partitioning=1)
  WHERE subtype IN ('lake', 'reservoir') AND bbox.xmin > -124.9 AND bbox.xmax < -116.8 AND bbox.ymin > 45.5 AND bbox.ymax < 49.05
    AND (bbox.xmax - bbox.xmin) * (bbox.ymax - bbox.ymin) > 0.002 AND ST_Area(geometry) > 0.0015""").fetchall()
print("inland lakes cut from the map:", sorted({n for n, _ in inland if n})[:40], round(time.time() - t), "s", flush=True)
inland = unary_union([wkb.loads(bytes(g)).buffer(0) for _, g in inland]).buffer(0)


def rings(geom, tol, min_area, holes=False):
    """Outer rings, or with holes=True one list per polygon: [outer, hole, hole...] (the page fills even-odd, so lakes stay water)."""
    geom = geom.simplify(tol, preserve_topology=True)
    polys = [p for p in getattr(geom, "geoms", [geom]) if p.geom_type == "Polygon" and p.area >= min_area]
    r = lambda ring: [[round(x, 3), round(y, 3)] for x, y in ring.coords]
    if holes:
        return [[r(p.exterior)] + [r(h) for h in p.interiors if abs(Polygon(h).area) >= min_area] for p in polys]
    return [r(p.exterior) for p in polys]


out, detail = {"state": None, "counties": []}, {"type": "FeatureCollection", "features": []}
for sub, name, g in rows:
    geom = wkb.loads(bytes(g)).buffer(0)
    if sub == "region":
        json.dump(mapping(geom.simplify(0.0003, preserve_topology=True)), open(f"{OUT}/wa_state_detail.geojson", "w"))
        # the drawn shoreline: fine enough that waterfront places sit on land when the map zooms to a town; the San Juans stay
        out["state"] = rings(geom.difference(inland).buffer(-0.0005).buffer(0.0005), 0.001, 0.00008, holes=True)
    else:
        detail["features"].append({"type": "Feature", "properties": {"name": name}, "geometry": mapping(geom.simplify(0.0003, preserve_topology=True))})
        out["counties"].append({"name": name, "c": rings(geom.difference(inland).buffer(-0.0005).buffer(0.0005), 0.004, 0.0005)})
json.dump(detail, open(f"{OUT}/wa_counties_detail.geojson", "w"))
json.dump(out, open(f"{OUT}/wa_shapes.json", "w"), separators=(",", ":"))
print("outlines: state", len(out["state"] or []), "rings +", len(out["counties"]), "counties;", round(time.time() - t), "s total")
