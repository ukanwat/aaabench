# Verified sources — web build

Every entry was checked by fetching it on **14 August 2026**, from this machine, headless. Where a
key or a login is needed it says so, because that is the difference between a source you can use
and one you cannot. Where something is blocked it stays on the list, marked, so nobody spends an
hour rediscovering the wall.

Counts drift. Treat them as the order of magnitude, not the truth.

## Check what keys you already have

```bash
env | grep -E "FREESOUND|SKETCHFAB|OPENTOPO|HF_TOKEN"
```

Keys may be added while you are working, so check again rather than assuming a source is closed.

## Geometry and props — keyless, glTF native

Everything here loads into three.js with no import step. That is the one place the web build is
easier than an engine.

| Source | Verified | What it is |
|---|---|---|
| **Poly Haven** | `api.polyhaven.com/assets?t=models\|textures\|hdris` → 200 | 521 models · 848 textures · **986 HDRIs**, all CC0, every channel at 1K–8K. `api.polyhaven.com/files/{slug}` returns the file map. The HDRIs matter more than the models. |
| **Google Scanned Objects** | `fuel.gazebosim.org/1.0/GoogleResearch/models` → 200, `X-Total-Count: 1033` | 1,033 real household objects, photogrammetry-scanned by Google. Keyless, paginated. Real objects rather than an artist's idea of them. |
| **ABO (Amazon Berkeley Objects)** | `s3://amazon-berkeley-objects/3dmodels/` (no-sign) → listed | ~8,000 artist-made PBR household objects, already glTF, open S3. |
| **Objaverse** | `import objaverse` → 0.1.7 installed | LVIS subset is category-tagged: `load_lvis_annotations()` is keyed by "car", "bench", "fire_hydrant". `load_objects(uids)` returns `.glb`. Corpus ODC-By, per-item licences vary. |
| **ambientCG** | `ambientcg.com/api/v2/full_json` → 200 | CC0 PBR material sets. Materials carry more of the look than meshes do. |
| **NASA 3D Resources** | GitHub tree API → 200, **257 `.glb`** | Public domain. The best aircraft and spacecraft source that exists. |
| **Smithsonian Open Access** | `s3://smithsonian-open-access/media/3d/` (no-sign) → listed | 2,000+ public-domain scans. |
| **Open Heritage 3D** | `openheritage3d.org` → 200 | Scanned real architecture and monuments. Site reachable; no documented public API — expect to work through its download pages. |

## Needs one free account

| Source | Verified | Note |
|---|---|---|
| **Sketchfab** | search `api.sketchfab.com/v3/models?downloadable=true` → 200 | **Search is open, download is not.** A free token (`sketchfab.com/settings#api`) sent as `Authorization: Token $SKETCHFAB_API_TOKEN` unlocks download. **No token is present in this environment right now.** The filters that make it worth the registration: `rigged=true` and `animated=true`, combinable with `downloadable`, licence and polygon count. |
| **Mixamo** | `mixamo.com` → 200 | 2,000+ animation clips and an auto-rigger, free for commercial use. One Adobe login seeds a session; after that community scripts run headless. FBX → GLB with `assimp`, which is installed. |
| **Freesound** | key at `freesound.org/apiv2/apply` | 700K sounds; filter `license:"Creative Commons 0"`. The `previews` field is fetchable with the key alone. |
| **OpenTopography** | free key, no card | Copernicus GLO-30, SRTMGL1, USGS 3DEP GeoTIFFs. 50 calls/day free. |

## Blocked or gone — verified, do not spend time here

- **Scan the World / MyMiniFactory** — 403 to a headless client.
- **Ready Player Me** — does not resolve at all. The public APIs shut down in January 2026.
- **OSM Buildings tile API** — 403 without a key.
- **archive.org Sonniss mirror** — connection failed from here today. May be transient; re-test
  before relying on it.
- **Everything Epic-licensed** — Fab, Megascans, City Sample, MetaHuman, the Game Animation
  Sample, MetaSounds. The licence binds them to Unreal Engine projects. They do not exist on this
  build, and that is the largest single difference from the engine arm.

## Real-world data — transfers untouched

These describe the world rather than model it. You get a plan and extrude it yourself.

| Source | Verified | What it carries |
|---|---|---|
| **Overture Maps** | `overturemaps` installed | Buildings **with heights and floor counts**, which raw OSM usually lacks. CDLA Permissive. |
| **Geofabrik** | `download.geofabrik.de/index-v1.json` → 200 | 555 daily OSM `.pbf` regions. |
| **Microsoft Global Building Footprints** | dataset-links CSV → 200 | 1.4 billion footprints with height estimates. |
| **osmnx** | installed | Street graphs and building features as Python queries. |
| **USGS 3DEP point elevation** | `epqs.nationalmap.gov/v1/json` → 200 | Keyless single-point elevation. |
| **awesome-citygml** | repo → 200 (MIT, updated May 2026) | Index of open semantic 3D city models. **Textured LOD2 exists for several European cities** — Hamburg, Vienna, Namur, Vantaa, the Netherlands via the 3DBAG API (→ 200), Switzerland via swissBUILDINGS3D (→ 200). |
| **opencitymodel (US)** | repo → 200 but **last commit 2019**, LOD1 only | There is no maintained US equivalent. For an American city the route is footprints plus heights plus your own extrusion. |

## Humans and animation — the hardest gap on this build

The engine arm had 500+ AAA mocap clips with a working Motion Matching setup. This one does not.

- **Mixamo** — the primary route. Rigged characters plus the clip library.
- **MPFB2** (MakeHuman for Blender) — `static.makehumancommunity.org/mpfb.html` → 200. Parametric
  humans with auto-rigging, CC0, fully headless through `blender --background --python`.
- **100STYLE** — → 200. 4M+ frames across 100 locomotion styles, CC BY 4.0, BVH.
- **CMU mocap** — → 200. Large, free, BVH.
- **Sketchfab filtered `rigged`+`animated`** — the only large source of *varied* rigged content.

BVH needs retargeting onto whatever rig you use. That work is yours.

## Reference photography — look at the real thing

| Source | Verified |
|---|---|
| **Wikimedia Commons** (search and geosearch by coordinate) | → 200 |
| **KartaView** street-level by coordinate — your exact game camera | `api.openstreetcam.org/2.0/photo/?lat=&lng=&radius=` → 200 |
| **Openverse** | `api.openverse.org/v1/images/` → 200. Terms are ANDed; keep queries to two or three words. |

## Sound

- **Freesound** — key required, 700K sounds, best city-ambience coverage.
- **EchoThief** — → 200, no login. 115 impulse responses recorded in real spaces, CC0. These work
  **natively** in the browser through Web Audio's `ConvolverNode`, no plugin.
- **OpenGameArt**, **Free Music Archive / ccMixter / Jamendo** — CC-licensed audio and music.
- There is no MetaSounds here. Procedural audio — engine drone from an RPM parameter, Doppler on
  passing traffic, wind, rain — is Web Audio you write yourself.

## Generation

- **2D, on-device, free.** `tools/gen-image.py` runs SDXL-Turbo locally through `diffusers`. No API
  key, no network cost. This is how a city gets its signage, billboards, posters, murals,
  packaging and brand marks.
- **3D, not on this machine.** TRELLIS (MIT, image/text → mesh + PLY/GLB) requires an NVIDIA GPU
  with ≥16 GB VRAM and is tested on Linux only. Hunyuan3D-2.1 wants 21 GB for texture generation,
  29 GB for both stages. Neither runs on Apple Silicon. If 3D generation is wanted it needs rented
  GPU time; otherwise meshes are authored in code or in headless Blender.

## Web pipeline — not optional

Browser memory is the constraint an engine does not have. Poly Haven's 8K textures are unusable
raw.

- **KTX2 / Basis** for textures and **Draco or meshopt** for geometry, both via `gltf-transform`
  (installed).
- `BatchedMesh` and `InstancedMesh` for draw calls.
- `three-mesh-bvh` for fast raycasts — which is also what grounds an object to the surface it
  stands on.

Budget in the low hundreds of megabytes, total.

## Installed on this machine

`blender` · `ffmpeg` · `imagemagick` · `assimp` (FBX/OBJ/DAE → GLB) · `gltf-transform` ·
`objaverse` · `overturemaps` · `osmnx` · `shapely` · `trimesh` · `scipy` · `opencv` ·
`scikit-image` · `pyproj` · `mapbox_earcut` · `noise` · `pygltflib`
