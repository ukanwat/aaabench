#!/usr/bin/env python3
"""Look at every vehicle in the palette, on a turntable, under one light.

A library assembled from many sources looks assembled, and the only way to know
whether yours does is to put every asset in one frame, under one light, at one
camera height, and stare at it. This builds that frame.

    ~/imagegen/bin/python tools/vehicle_contact_sheet.py                     # fit mode
    ~/imagegen/bin/python tools/vehicle_contact_sheet.py --mode scale        # true relative size
    ~/imagegen/bin/python tools/vehicle_contact_sheet.py --angles 0,90,180
    ~/imagegen/bin/python tools/vehicle_contact_sheet.py --dir workspace/assets/vehicles/_review
    ~/imagegen/bin/python tools/vehicle_contact_sheet.py --only dz_shvan92_van --tile 1200x900

Two modes, because they catch different lies:

  fit    each vehicle framed to fill its own tile. Equalises apparent size, so
         what you are judging is surface — panel shutlines, glass curvature,
         tyre sidewalls, paint, wear, and texel density against its neighbours.

  scale  every tile shares one world framing, with a 1 m grid and a 1.75 m human
         beside the vehicle. A model 15% too large is invisible on its own and
         obvious here. This is the mode that catches units and proportion.

Each tile is rendered on its own and the sheet is stitched afterwards, rather
than accumulated into one canvas with viewport/scissor. That costs a screenshot
per model and buys correctness: shadow-map passes reset the colour attachment
between renders, so the accumulate-into-one-canvas version silently produced a
sheet containing only the last vehicle.

Carries the Metal/WebGPU launch flags and asserts on the backend string — a
headless Chromium on default flags renders through SwiftShader, and a screenshot
from a CPU rasterizer looks exactly like a screenshot.
"""
import argparse, io, json, pathlib, sys, time

ROOT = pathlib.Path(__file__).resolve().parent.parent
GPU_ARGS = [
    "--enable-unsafe-webgpu",
    "--use-angle=metal",
    "--enable-features=Vulkan,WebGPU",
    "--ignore-gpu-blocklist",
]
FONT_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_R = "/System/Library/Fonts/Supplemental/Arial.ttf"

PAGE_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>vehicle turntable</title>
<style>html,body{margin:0;background:#101216;overflow:hidden}canvas{display:block}</style>
</head><body>
<canvas id="c"></canvas>
<script type="importmap">{"imports":{
  "three":"__PREFIX__vendor/three/build/three.webgpu.js",
  "three/webgpu":"__PREFIX__vendor/three/build/three.webgpu.js",
  "three/tsl":"__PREFIX__vendor/three/build/three.tsl.js",
  "three/addons/":"__PREFIX__vendor/three/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

const CFG = __CFG__;
const TW = CFG.tile[0], TH = CFG.tile[1];

const canvas = document.getElementById('c');
const renderer = new THREE.WebGPURenderer({ canvas, antialias: true });
renderer.setPixelRatio(1);
renderer.setSize(TW, TH);
renderer.toneMapping = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
await renderer.init();
window.__backend = renderer.backend.isWebGPUBackend ? 'webgpu' : 'webgl2';

// ---- neutral studio ------------------------------------------------------
// Deliberately unflattering: a soft dome, a warm key, a cool fill, a rim. If an
// asset only holds up under a dramatic HDRI it is not ready for a street at noon.
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2b2f35);

const hemi = new THREE.HemisphereLight(0xbfd4ea, 0x4e5250, 1.6);
scene.add(hemi);
const key = new THREE.DirectionalLight(0xfff2e0, 2.5);
key.position.set(-5.5, 7.5, 6.0);
key.castShadow = true;
key.shadow.mapSize.set(2048, 2048);
const S = 8;
key.shadow.camera.left = -S; key.shadow.camera.right = S;
key.shadow.camera.top = S; key.shadow.camera.bottom = -S;
key.shadow.camera.near = 0.5; key.shadow.camera.far = 40;
key.shadow.bias = -0.0008;
key.shadow.normalBias = 0.02;
scene.add(key);
const fill = new THREE.DirectionalLight(0xcfe0ff, 0.85);
fill.position.set(7, 3, 4);
scene.add(fill);
const rim = new THREE.DirectionalLight(0xffffff, 1.5);
rim.position.set(3, 4.5, -8);
scene.add(rim);

// Car paint is mostly reflection. With no environment, clearcoat reads as flat
// grey and every asset looks equally dead — which would hide exactly the thing
// this sheet exists to judge.
{
  const cnv = document.createElement('canvas'); cnv.width = 8; cnv.height = 256;
  const g = cnv.getContext('2d');
  const grd = g.createLinearGradient(0, 0, 0, 256);
  grd.addColorStop(0.00, '#e6f0fb'); grd.addColorStop(0.46, '#a3b4c8');
  grd.addColorStop(0.52, '#42464c'); grd.addColorStop(1.00, '#282b30');
  g.fillStyle = grd; g.fillRect(0, 0, 8, 256);
  const tex = new THREE.CanvasTexture(cnv);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  scene.environment = tex;
}

const ground = new THREE.Mesh(
  new THREE.CircleGeometry(26, 64),
  new THREE.MeshStandardMaterial({ color: 0x4c5054, roughness: 0.93, metalness: 0.0 }));
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.0015;
ground.receiveShadow = true;
scene.add(ground);

const grid = new THREE.GridHelper(30, 30, 0x848a92, 0x63686e);
grid.position.y = 0.003;
grid.visible = false;
scene.add(grid);

// The only object in frame whose size you already know. Without it a units error
// is invisible; with it, it is the first thing you see.
const human = new THREE.Mesh(
  new THREE.CapsuleGeometry(0.21, 1.28, 6, 16),
  new THREE.MeshStandardMaterial({ color: 0xbb5a42, roughness: 0.8 }));
human.position.set(2.6, 0.86, 1.9);
human.castShadow = true;
human.visible = false;
scene.add(human);

// ---- loading -------------------------------------------------------------
const ktx2 = new KTX2Loader().setTranscoderPath('__PREFIX__vendor/three/jsm/libs/basis/').detectSupport(renderer);
const loader = new GLTFLoader().setKTX2Loader(ktx2).setMeshoptDecoder(MeshoptDecoder);

const slots = [];
const problems = [];

await Promise.all(CFG.items.map((it, i) => new Promise(res => {
  loader.load(it.file, gltf => {
    const g = new THREE.Group();
    g.add(gltf.scene);
    g.visible = false;
    scene.add(g);
    let tris = 0, draws = 0, mats = new Set(), maxTex = 0;
    gltf.scene.traverse(o => {
      if (!o.isMesh) return;
      o.castShadow = true; o.receiveShadow = true;
      draws++;
      const a = o.geometry.index ? o.geometry.index.count : o.geometry.attributes.position.count;
      tris += a / 3;
      const m = o.material;
      for (const mm of (Array.isArray(m) ? m : [m])) {
        mats.add(mm.uuid);
        for (const k of ['map', 'normalMap', 'roughnessMap', 'metalnessMap', 'aoMap', 'emissiveMap'])
          if (mm[k]?.image) maxTex = Math.max(maxTex, mm[k].image.width || 0);
      }
    });
    const box = new THREE.Box3().setFromObject(gltf.scene);
    const wheels = [];
    gltf.scene.traverse(o => { if (/^wheel_(fl|fr|rl|rr)$/.test(o.name)) wheels.push(o.name); });
    slots[i] = { it, g, box, size: box.getSize(new THREE.Vector3()),
                 tris: Math.round(tris), draws, mats: mats.size, maxTex, wheels: wheels.sort() };
    if (Math.abs(box.min.y) > 0.02) problems.push(`${it.id}: min.y=${box.min.y.toFixed(3)} m (floating or sunk)`);
    res();
  }, undefined, e => { problems.push(`${it.id}: LOAD FAILED ${e?.message ?? e}`); slots[i] = null; res(); });
})));

// ---- one rule for every camera -------------------------------------------
const FOV = 32;
function cameraFor(s, mode, angle) {
  const cam = new THREE.PerspectiveCamera(FOV, TW / TH, 0.05, 200);
  const target = new THREE.Vector3(0, s ? s.size.y * 0.45 : 0.8, 0);
  let dist, height;
  if (mode === 'scale') {
    dist = CFG.scaleDist; height = 2.3; target.y = 1.05;
  } else {
    const r = s ? Math.max(s.size.x, s.size.y, s.size.z) : 4;
    dist = r * 1.72 / Math.tan(FOV * Math.PI / 360) * 0.50;
    height = Math.max(0.95, s ? s.size.y * 0.80 : 1.4);
  }
  const a = (CFG.baseAzimuth + angle) * Math.PI / 180;
  cam.position.set(Math.sin(a) * dist, height, Math.cos(a) * dist);
  cam.lookAt(target);
  return cam;
}

window.__show = (i, mode, angle) => {
  for (let k = 0; k < slots.length; k++) if (slots[k]) slots[k].g.visible = (k === i);
  grid.visible = human.visible = (mode === 'scale');
  const s = slots[i];
  renderer.render(scene, cameraFor(s, mode, angle));
  return s ? { id: s.it.id, size: [+s.size.z.toFixed(3), +s.size.x.toFixed(3), +s.size.y.toFixed(3)],
               minY: +s.box.min.y.toFixed(4), tris: s.tris, draws: s.draws, mats: s.mats,
               maxTex: s.maxTex, wheels: s.wheels }
            : { id: CFG.items[i].id, error: 'load failed' };
};

window.__sheet = {
  backend: window.__backend, n: CFG.items.length,
  loaded: slots.filter(Boolean).length, problems,
  totalTris: slots.filter(Boolean).reduce((a, s) => a + s.tris, 0),
  totalDraws: slots.filter(Boolean).reduce((a, s) => a + s.draws, 0),
};
window.__ready = true;
console.log('[sheet] ' + JSON.stringify(window.__sheet));
if (problems.length) console.warn('[sheet] problems:\\n' + problems.join('\\n'));
</script></body></html>
"""


def build_page(asset_dir: pathlib.Path, url_prefix: str, cfg: dict) -> pathlib.Path:
    out = asset_dir / "_contactsheet.html"
    out.write_text(PAGE_HTML.replace("__CFG__", json.dumps(cfg)).replace("__PREFIX__", url_prefix))
    return out


def collect(asset_dir: pathlib.Path, manifest: pathlib.Path, only=None):
    """Prefer the manifest (it carries class order); fall back to a glob."""
    items = []
    if manifest.exists():
        m = json.loads(manifest.read_text())
        for e in (m["vehicles"] if isinstance(m, dict) else m):
            f = asset_dir / e["file"]
            if f.exists():
                items.append({"id": e.get("id") or f.stem, "file": e["file"],
                              "cls": e.get("class", ""), "kb": round(f.stat().st_size / 1024)})
    if not items:
        items = [{"id": p.stem, "file": p.name, "cls": "", "kb": round(p.stat().st_size / 1024)}
                 for p in sorted(asset_dir.glob("*.glb"))]
    if only:
        want = set(only)
        items = [i for i in items if i["id"] in want]
    return items


def stitch(tiles, items, cols, tw, th, out_png, title):
    from PIL import Image, ImageDraw, ImageFont
    rows = (len(tiles) + cols - 1) // cols
    pad, head = 0, 34
    sheet = Image.new("RGB", (cols * tw, head + rows * th), (16, 18, 22))
    d = ImageDraw.Draw(sheet)
    try:
        fb = ImageFont.truetype(FONT_B, 13); fr = ImageFont.truetype(FONT_R, 11)
        ft = ImageFont.truetype(FONT_B, 17)
    except OSError:
        fb = fr = ft = ImageFont.load_default()
    d.text((10, 9), title, font=ft, fill=(235, 238, 242))
    for i, (buf, info) in enumerate(zip(tiles, items)):
        x, y = (i % cols) * tw, head + (i // cols) * th
        if buf:
            sheet.paste(Image.open(io.BytesIO(buf)).convert("RGB"), (x, y))
        d.rectangle([x, y, x + tw - 1, y + th - 1], outline=(58, 62, 68))
        r = info.get("report") or {}
        bad = "error" in r
        d.rectangle([x + 4, y + 4, x + tw - 5, y + 34], fill=(0, 0, 0))
        d.text((x + 8, y + 6), info["id"] + ("  [FAILED]" if bad else ""), font=fb,
               fill=(255, 120, 120) if bad else (255, 255, 255))
        if not bad and r:
            sz = r["size"]
            line = (f"{sz[0]:.2f} x {sz[1]:.2f} x {sz[2]:.2f} m   {r['tris']/1000:.1f}k tri   "
                    f"{r['draws']} dc   {r['mats']} mat   {r['maxTex']}px   "
                    f"{len(r['wheels'])}/4 wheels   {info['kb']}KB")
            d.text((x + 8, y + 21), line, font=fr, fill=(168, 186, 204))
            if abs(r["minY"]) > 0.02:
                d.text((x + 8, y + th - 16), f"!! min.y = {r['minY']:+.3f} m", font=fb, fill=(255, 150, 90))
    out_png.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out_png)
    return sheet.size


def run(url, items, mode, angle, tw, th, wait_ms):
    from playwright.sync_api import sync_playwright
    tiles, logs = [], []
    with sync_playwright() as pw:
        b = pw.chromium.launch(args=GPU_ARGS)
        pg = b.new_page(viewport={"width": tw, "height": th}, device_scale_factor=1)
        pg.on("console", lambda m: logs.append(f"  [{m.type}] {m.text}"))
        pg.on("pageerror", lambda e: logs.append(f"  [pageerror] {e}"))
        pg.on("requestfailed", lambda r: logs.append(f"  [failed] {r.url} {r.failure}"))
        pg.goto(url, wait_until="load", timeout=180_000)
        pg.wait_for_function("window.__ready === true", timeout=300_000)
        pg.wait_for_timeout(wait_ms)
        meta = pg.evaluate("window.__sheet")
        cv = pg.query_selector("#c")
        for i, it in enumerate(items):
            r = pg.evaluate("([i,m,a]) => window.__show(i,m,a)", [i, mode, angle])
            pg.wait_for_timeout(90)
            tiles.append(cv.screenshot())
            it["report"] = r
        b.close()
    return tiles, meta, logs


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default="workspace/assets/vehicles")
    ap.add_argument("--server", default="http://127.0.0.1:8080")
    ap.add_argument("--serve-root", default="workspace")
    ap.add_argument("--out", default=None)
    ap.add_argument("--mode", default="fit", choices=["fit", "scale"])
    ap.add_argument("--angle", type=float, default=0.0, help="turntable degrees")
    ap.add_argument("--angles", default=None, help="comma list; one sheet per angle")
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--tile", default="400x300")
    ap.add_argument("--base-azimuth", type=float, default=32.0,
                    help="degrees off the nose; ~32 is the three-quarter a car is shot from")
    ap.add_argument("--scale-dist", type=float, default=14.0,
                    help="camera distance in scale mode, identical for every tile (m)")
    ap.add_argument("--only", default=None, help="comma list of ids")
    ap.add_argument("--wait", type=int, default=1200)
    ap.add_argument("--manifest", default="manifest.json")
    a = ap.parse_args()

    asset_dir = (ROOT / a.dir).resolve()
    serve_root = (ROOT / a.serve_root).resolve()
    if not asset_dir.is_dir():
        sys.exit(f"no such directory: {asset_dir}")
    try:
        rel = asset_dir.relative_to(serve_root)
    except ValueError:
        sys.exit(f"{asset_dir} is not under the server root {serve_root}")

    items = collect(asset_dir, asset_dir / a.manifest, a.only.split(",") if a.only else None)
    if not items:
        sys.exit(f"no .glb in {asset_dir}")
    tw, th = (int(x) for x in a.tile.lower().split("x"))
    cfg = {"items": items, "tile": [tw, th], "baseAzimuth": a.base_azimuth,
           "scaleDist": a.scale_dist}
    page = build_page(asset_dir, "../" * len(rel.parts), cfg)
    print(f"{len(items)} models -> {page}")

    for ang in ([float(x) for x in a.angles.split(",")] if a.angles else [a.angle]):
        t = time.time()
        url = f"{a.server}/{rel.as_posix()}/{page.name}"
        tiles, meta, logs = run(url, items, a.mode, ang, tw, th, a.wait)
        out = pathlib.Path(a.out) if a.out and not a.angles else \
            ROOT / "shots" / "vehicles" / f"{a.mode}-{int(ang):03d}.png"
        if not out.is_absolute():
            out = ROOT / out
        title = (f"{a.dir}  |  mode={a.mode}  azimuth={a.base_azimuth + ang:.0f}deg  "
                 f"|  {meta['loaded']}/{meta['n']} loaded  {meta['totalTris']:,} tri  "
                 f"{meta['totalDraws']} draw calls  |  backend={meta['backend']}")
        size = stitch(tiles, items, a.cols, tw, th, out, title)
        print(f"\n== {a.mode} @ {ang:g}deg -> {out}  {size[0]}x{size[1]}  ({time.time()-t:.1f}s)")
        for line in logs[:40]:
            if "ERR_ABORTED" not in line:
                print(line)
        if meta["backend"] != "webgpu":
            print("  !! NOT WebGPU — do not trust this image; check the launch flags")
        for p in meta["problems"]:
            print("  !! " + p)
        (out.with_suffix(".json")).write_text(json.dumps(
            {"meta": meta, "items": [{k: v for k, v in i.items()} for i in items]}, indent=1))


if __name__ == "__main__":
    main()
