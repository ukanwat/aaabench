#!/usr/bin/env python3
"""Re-verify every source in docs/sources/assets.md, so the claim in that file is
executable rather than a promise about the past.

    python3 tools/check-sources.py             # check everything
    python3 tools/check-sources.py --only poly # substring filter

Exits non-zero if anything that was reachable is not any more. Run it before a session:
an agent that spends an hour on a source that died last month has lost the hour, and the
harness is what should have caught it.

`expect` is what was true on 14 August 2026. A mismatch is not automatically a failure —
sources move — it is a line in this file that now needs editing.
"""
import argparse, concurrent.futures, sys, urllib.request, urllib.error

# name, url, expected status ("200", "403" for known-blocked, etc.)
SOURCES = [
    ("polyhaven models",      "https://api.polyhaven.com/assets?t=models", "200"),
    ("polyhaven hdris",       "https://api.polyhaven.com/assets?t=hdris", "200"),
    ("polyhaven textures",    "https://api.polyhaven.com/assets?t=textures", "200"),
    ("ambientCG",             "https://ambientcg.com/api/v2/full_json?limit=1", "200"),
    ("google scanned objects","https://fuel.gazebosim.org/1.0/GoogleResearch/models?per_page=1", "200"),
    ("NASA 3D (tree api)",    "https://api.github.com/repos/nasa/NASA-3D-Resources/git/trees/master?recursive=1", "200"),
    ("open heritage 3d",      "https://openheritage3d.org/", "200"),
    ("sketchfab search",      "https://api.sketchfab.com/v3/models?downloadable=true&count=1", "200"),
    ("poly pizza",            "https://poly.pizza/", "200"),
    ("quaternius",            "https://quaternius.com/", "200"),
    ("blenderkit (addon only)","https://www.blenderkit.com/", "200"),
    ("mixamo (adobe login)",  "https://www.mixamo.com/", "200"),
    ("MPFB2",                 "https://static.makehumancommunity.org/mpfb.html", "200"),
    ("100STYLE",              "https://www.ianxmason.com/100style/", "200"),
    ("geofabrik index",       "https://download.geofabrik.de/index-v1.json", "200"),
    ("MS building footprints","https://minedbuildings.z5.web.core.windows.net/global-buildings/dataset-links.csv", "200"),
    ("USGS 3DEP point",       "https://epqs.nationalmap.gov/v1/json?x=-80.19&y=25.77&wkid=4326&units=Meters", "200"),
    ("3DBAG api",             "https://api.3dbag.nl/collections", "200"),
    ("swisstopo buildings3D", "https://www.swisstopo.admin.ch/en/landscape-model-swissbuildings3d-3-0-beta", "200"),
    ("awesome-citygml",       "https://api.github.com/repos/OloOcki/awesome-citygml", "200"),
    ("openverse images",      "https://api.openverse.org/v1/images/?q=miami&page_size=1", "200"),
    ("wikimedia commons api", "https://commons.wikimedia.org/w/api.php?action=query&list=search&srsearch=miami&format=json", "200"),
    ("kartaview",             "https://api.openstreetcam.org/2.0/photo/?lat=25.77&lng=-80.19&radius=100", "200"),
    ("mapillary (no token)",  "https://graph.mapillary.com/images?fields=id&limit=1", "400"),
    ("echothief",             "http://www.echothief.com/downloads/", "200"),
    ("opengameart",           "https://opengameart.org/", "200"),
    ("jamendo api",           "https://api.jamendo.com/v3.0/tracks/?client_id=56d30c95&format=json&limit=1", "200"),
    ("supersplat",            "https://api.github.com/repos/playcanvas/supersplat", "200"),
    ("aws terrain tiles",     "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/10/281/408.png", "200"),
    ("esri world imagery",    "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/17/54507/36795", "200"),
    ("usgs naip (0.3m)",      "https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPPlus/ImageServer?f=json", "200"),
    ("trellis.2 gradio api",  "https://microsoft-trellis-2.hf.space/gradio_api/info", "200"),
    # known walls — these SHOULD fail, and it is worth knowing if one ever opens
    ("scan the world (walled)","https://www.myminifactory.com/scantheworld/", "403"),
    ("osm buildings (walled)", "https://data.osmbuildings.org/0.2/anonymous/tile/15/17605/10746.json", "403"),
]


def check(item):
    name, url, expect = item
    req = urllib.request.Request(url, headers={"User-Agent": "aaabench-source-check/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=25) as r:
            got = str(r.status)
    except urllib.error.HTTPError as e:
        got = str(e.code)
    except Exception as e:
        got = f"ERR {type(e).__name__}"
    return name, url, expect, got


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="substring filter on the name")
    a = ap.parse_args()
    items = [s for s in SOURCES if not a.only or a.only.lower() in s[0].lower()]

    drift = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for name, url, expect, got in ex.map(check, items):
            ok = got == expect
            print(f"{'ok ' if ok else 'DRIFT'}  {name:26s} expected {expect:4s} got {got}")
            if not ok:
                drift.append((name, expect, got, url))

    print(f"\n{len(items) - len(drift)}/{len(items)} as documented")
    if drift:
        print("\nThese lines in docs/sources/assets.md no longer describe reality:")
        for name, expect, got, url in drift:
            print(f"  {name}: {expect} -> {got}   {url}")
        sys.exit(1)
