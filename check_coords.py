# /// script
# requires-python = ">=3.12"
# dependencies = ["pyshp", "shapely"]
# ///
"""List mapped sites that lie outside the state they were filed in, as candidates for corrections.csv.

Usage: uv run check_coords.py <cb_*_us_state_500k.shp>  (Census cartographic boundary file, run after build.py)
"""
import json, pathlib, sys

import shapefile
from shapely.geometry import Point, shape

KM_PER_DEGREE = 111
TOLERANCE_KM = 5  # coastal towers and the generalized boundary file can disagree by a few km

states = {rec.record["STUSPS"]: shape(rec.shape.__geo_interface__) for rec in shapefile.Reader(sys.argv[1]).shapeRecords()}
for path in sorted((pathlib.Path(__file__).parent / "data").glob("*.json")):
    code = path.stem
    if code in ("bay", "GM"):  # the Bay Area repeats California; GM sites are offshore by definition
        continue
    for site in json.loads(path.read_text()):
        point = Point(site["lon"], site["lat"])
        off_km = states[code].distance(point) * KM_PER_DEGREE
        if off_km > TOLERANCE_KM:
            inside = next((other for other, geom in states.items() if geom.contains(point)), "none")
            calls = " ".join(sorted({t["call"] for t in site["tx"]}))
            print(f"{code}\t{off_km:.0f} km out\tin {inside}\t{site['lat']}, {site['lon']}\t{calls}\t{site['addr']}")
