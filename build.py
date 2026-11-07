# /// script
# requires-python = ">=3.12"
# ///
"""Build index.html: a map of active FCC ULS site-licensed transmitters in 900-932 MHz around the SF Bay Area."""
import collections, json, math, pathlib, sys

ULS = pathlib.Path(sys.argv[1])
HERE = pathlib.Path(__file__).parent
DIRS = ["l_paging", "l_LMcomm", "l_micro"]  # hold every service in CATEGORIES
LO_MHZ, HI_MHZ = 900, 932
S, N, W, E = 36.95, 38.45, -123.2, -121.55  # Santa Cruz to Santa Rosa, coast to Livermore
SAME_SITE_M = 100  # licenses often file one tower with coordinates a few meters apart
CATEGORIES = [  # (label, color, matches(service, mhz)), in band order; the map shows only matching transmitters
    ("Tag readers (LMS), 902–904 and 909.75–921.75 MHz", "#3cb44b", lambda svc, mhz: svc == "LN"),
    ("SCADA radio remotes (Part 101), 928–929 MHz", "#f58231", lambda svc, mhz: svc in ("MG", "MW")),
    ("Paging control links, 928.85–929 MHz", "#4363d8", lambda svc, mhz: svc == "CD" and mhz < 929),
    ("Private carrier paging, 929–930 MHz", "#e6194b", lambda svc, mhz: svc == "GS"),
    ("Common-carrier paging, 931–932 MHz", "#911eb4", lambda svc, mhz: svc == "CD" and mhz >= 931),
]


def rows(d, table):
    with open(ULS / d / f"{table}.dat", encoding="latin-1") as f:
        for line in f:
            yield line.rstrip("\r\n").split("|")


def num(s):
    return float(s) if s else None


def power(r):
    """Return (watts ERP, basis): ERP when filed, else EIRP converted."""
    if r[16]:
        return float(r[16]), "erp"
    if r[20]:
        return 10 ** ((float(r[20]) - 30) / 10) / 1.64, "eirp"
    return None, None


def category(svc, mhz):
    matches = [i for i, (_, _, test) in enumerate(CATEGORIES) if test(svc, mhz)]
    if len(matches) > 1:
        raise ValueError(f"{svc} at {mhz} MHz matches categories {matches}; make CATEGORIES exclusive")
    return matches[0] if matches else None


def distance_m(a, b):
    dy = (a["lat"] - b["lat"]) * 111_320
    dx = (a["lon"] - b["lon"]) * 111_320 * math.cos(math.radians(a["lat"]))
    return math.hypot(dx, dy)


licenses, freqs, sites, antennas = {}, collections.defaultdict(dict), {}, {}
for d in DIRS:
    for r in rows(d, "HD"):
        if r[5] == "A":
            licenses[r[1]] = {"usi": r[1], "call": r[4], "service": r[6], "expires": r[8]}
    for r in rows(d, "EN"):
        if r[1] in licenses and r[5] == "L":
            licenses[r[1]]["licensee"] = r[7]
    for r in rows(d, "FR"):
        if r[1] in licenses and r[10]:
            lo, hi = float(r[10]), num(r[11])
            cat = category(licenses[r[1]]["service"], lo)
            if lo <= HI_MHZ and (hi or lo) >= LO_MHZ and cat is not None:
                watts, basis = power(r)
                f = {"mhz": lo, "hi": hi, "ant": r[7], "cls": r[8], "w": watts, "basis": basis, "cat": cat}
                same = freqs[(r[1], r[6])].get(lo)  # a frequency repeats once per antenna; keep its strongest row
                if same is None or (watts or 0) > (same["w"] or 0):
                    freqs[(r[1], r[6])][lo] = f
    for r in rows(d, "LO"):
        if (r[1], r[8]) in freqs and r[6] == "F" and r[19]:  # fixed transmit sites only; other location types are area centers
            lat = int(r[19]) + int(r[20] or 0) / 60 + float(r[21] or 0) / 3600
            lon = int(r[23]) + int(r[24] or 0) / 60 + float(r[25] or 0) / 3600
            lat, lon = (lat if r[22] == "N" else -lat), (-lon if r[26] == "W" else lon)
            if S < lat < N and W < lon < E:
                sites[(r[1], r[8])] = {"lat": round(lat, 5), "lon": round(lon, 5), "addr": ", ".join(x for x in (r[11], r[12]) if x), "ground": num(r[18])}
    for r in rows(d, "AN"):
        if (r[1], r[7]) in sites:
            antennas[(r[1], r[7], r[6])] = {"height": num(r[10] or r[11]), "haat": num(r[19])}  # tip height, else center height

points = []
for (usi, loc), site in sites.items():
    if "licensee" not in licenses[usi]:
        raise ValueError(f"license {licenses[usi]['call']} has no licensee entity")
    p = next((p for p in points if distance_m(p, site) < SAME_SITE_M), None)
    if p is None:
        p = {**site, "addr": [], "tx": []}
        points.append(p)
    if site["addr"] and site["addr"] not in p["addr"]:
        p["addr"].append(site["addr"])
    for f in freqs[(usi, loc)].values():
        ant = antennas.get((usi, loc, f["ant"]), {})
        p["tx"].append({**licenses[usi], **{k: f[k] for k in ("mhz", "hi", "cls", "w", "basis", "cat")}, "height": ant.get("height"), "haat": ant.get("haat")})
for p in points:
    p["addr"] = " / ".join(p["addr"])

data = {"categories": [{"label": label, "color": color} for label, color, _ in CATEGORIES], "sites": sorted(points, key=lambda p: (p["lat"], p["lon"])), "source": (ULS / "l_paging" / "counts").read_text().splitlines()[0]}
(HERE / "index.html").write_text((HERE / "template.html").read_text().replace("/*DATA*/", json.dumps(data, separators=(",", ":")).replace("</", "<\\/")))
print(f"{len(data['sites'])} sites, {sum(len(p['tx']) for p in data['sites'])} transmitters")
print(collections.Counter(CATEGORIES[t["cat"]][0] for p in data["sites"] for t in p["tx"]).most_common())
