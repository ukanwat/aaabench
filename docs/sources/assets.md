# Where things come from — web build

Models, materials, HDRIs, humans and animation, real-world map data, splats, sound, reference
photography, and what can be generated on this machine.

Every entry was checked by fetching it on **14 August 2026**, from this machine, headless. Where a
key or a login is needed it says so, because that is the difference between a source you can use
and one you cannot. Where something is blocked or dead it stays on the list, marked, so nobody
spends an hour rediscovering the wall.

**That claim is executable, not a promise about the past.** Sources move, and a document that
asserts it was verified becomes a confident liar the week something dies. So run it:

```bash
python3 tools/check-sources.py        # 30 endpoints, including the known walls
```

It exits non-zero and names the lines in this file that no longer describe reality. Do that before
a session rather than discovering it an hour in. Counts drift too — treat them as the order of
magnitude, not the truth.

## Check what keys you already have

```bash
env | grep -E "SKETCHFAB|FREESOUND|MIXAMO|HF_TOKEN|MAPILLARY"
```

The runner loads them from `~/.aaabench.env`, which is outside this repository and readable only
by its owner. Keys may be added while you are working, so check again rather than assuming a
source is closed — a wall named below may have opened since.

## Geometry and props — keyless, glTF native

Everything here loads into three.js with no import step. That is the one place the web build is
easier than an engine.

| Source | Verified | What it is |
|---|---|---|
| **Poly Haven** | `api.polyhaven.com/assets?t=models\|textures\|hdris` → 200 | 521 models · 848 textures · **986 HDRIs**, all CC0, every channel at 1K–8K. `api.polyhaven.com/files/{slug}` returns the file map. |
| **Google Scanned Objects** | `fuel.gazebosim.org/1.0/GoogleResearch/models` → 200, `X-Total-Count: 1033` | 1,033 real household objects, photogrammetry-scanned by Google. Keyless, paginated. Real objects rather than an artist's idea of them. |
| **ABO (Amazon Berkeley Objects)** | `s3://amazon-berkeley-objects/3dmodels/` (no-sign) → listed | ~8,000 artist-made PBR household objects, already glTF, open S3. |
| **Objaverse** | `import objaverse` → 0.1.7 installed; XL dataset page → 200 | LVIS subset is category-tagged: `load_lvis_annotations()` keyed by "car", "bench", "fire_hydrant"; `load_objects(uids)` returns `.glb`. Objaverse-XL reaches 10M+. Corpus ODC-By, per-item licences vary, and it aggregates Sketchfab so it inherits Sketchfab's provenance problems. |
| **ambientCG** | `ambientcg.com/api/v2/full_json` → 200 | CC0 PBR material sets. |
| **NASA 3D Resources** | GitHub tree API → 200, **257 `.glb`** | Public domain. The best aircraft and spacecraft source that exists. |
| **Smithsonian Open Access** | `s3://smithsonian-open-access/media/3d/` (no-sign) → listed | 2,000+ public-domain scans. |
| **Open Heritage 3D** | `openheritage3d.org` → 200 | Scanned real architecture and monuments. No documented public API — expect to work through its download pages. |
| **Quaternius** | → 200 | CC0, and deliberately stylised low-poly. Listed for completeness; hold it against the asset bar in `PROMPT.md` before using it. |
| **Poly Pizza** | → 200 | Free key. Also low-poly. Same caveat. |

## Needs one free account

| Source | Verified | Note |
|---|---|---|
| **Sketchfab** | search → 200; `downloadable=true&rigged=true&animated=true` returns results | **Search is open, download is not.** Send `Authorization: Token $SKETCHFAB_API_TOKEN` to unlock download; **that token is provisioned** — check your environment before concluding otherwise. The filters that make it worth registering: `rigged` and `animated`, combinable with `downloadable`, licence and polygon count. Dropping the `license=cc0` filter multiplies the pool. |
| **Mixamo** | API → 200 with `$MIXAMO_BEARER`: **360 walk motions, 108 characters** | Rigged characters and 2,000+ clips, free for commercial use. Call it with `Authorization: Bearer $MIXAMO_BEARER` **and** `X-Api-Key: mixamo2` — the second header is not optional and its absence looks like an auth failure. FBX → GLB with `assimp`, installed. **The bearer is an Adobe IMS token and dies after 24 hours** — it is not an API key, and it is not something you can renew yourself, because the sign-in belongs to the operator. The runner prints how long it has left and says plainly when it has expired. If it has, record that you need a fresh one and get on with the rest; do not treat the 401 as evidence the source does not work. |
| **Freesound** | key **provisioned** as `$FREESOUND_API_KEY` | 700K sounds; filter `license:"Creative Commons 0"` (1,243 CC0 hits for city traffic ambience alone). The `previews` field is fetchable with the key alone. |
| **BlenderKit** | → 200 | Addon only — no REST API, so not scriptable. |

## Blocked, dead, or a trap — verified, do not spend time here

- **Scan the World / MyMiniFactory** — 403 to a headless client.
- **Ready Player Me** — does not resolve at all. Public APIs shut down January 2026.
- **ShapeNet** — 503, and registration plus non-commercial terms even when up.
- **OSM Buildings tile API** — 403 without a key.
- **ccMixter API** — 404.
- **OpenTopography** — works, but there is no reason to use it here. It is email-and-password only
  (no SSO), rate-limited to 50 calls/day, and it serves Copernicus and SRTM — which are already
  keyless above. Worth knowing why it does not matter for this brief in particular: measured
  elevation across a Miami-shaped site is **0.1 m downtown, 1.6 m at the beach, 1.7 m inland**. A
  DEM of that is a flat plane, and any relief worth driving on has to be invented regardless.
- **Cesium ion** — the OSM Buildings tileset needs an account; not provisioned.
- **Rokoko Motion Library** — checked while signed in. It is a **marketplace**, not a free library:
  clips are sold individually and delivered through Rokoko Studio, their desktop GUI application.
  There is no headless route and no free bulk tier, whatever older notes about "263 free clips"
  suggest. An account gets you nothing an agent can use.
- **archive.org Sonniss mirror** — connection failed from here today, twice. Re-test before
  relying on it; the bundles themselves are the best free professional audio library that exists.
- **AMASS / SMPL-X / LAFAN1 / 3D-FUTURE** — reachable but registration and/or non-commercial,
  which makes them unusable for a published artefact.
- **Google Photorealistic 3D Tiles** — docs → 200, and it covers thousands of real cities through
  the 3D-tiles renderers. But it is **billed per request**, **not available in the EEA**, and the
  terms restrict it to *visualization*, which a playable game arguably is not. It is also
  photogrammetry: convincing from altitude, mushy at street level.
- **Everything Epic-licensed** — Fab, Megascans, City Sample (2,000 building meshes, 13 driveable
  vehicles, MassTraffic), MetaHuman, the Game Animation Sample (500+ mocap clips with Motion
  Matching), MetaSounds. The licence binds them to Unreal Engine projects. They do not exist on
  this build, and that is the largest single difference from the engine arm.

## Real-world data — transfers untouched

These describe the world rather than model it. You get a plan and extrude it yourself.

| Source | Verified | What it carries |
|---|---|---|
| **Overture Maps** | `overturemaps` installed | Buildings **with heights and floor counts**, which raw OSM usually lacks. CDLA Permissive. |
| **Geofabrik** | `index-v1.json` → 200 | 555 daily OSM `.pbf` regions. |
| **Microsoft Global Building Footprints** | dataset-links CSV → 200 | 1.4 billion footprints with height estimates. |
| **osmnx** | installed | Street graphs and building features as Python queries. See `mapdata.md`. |
| **USGS 3DEP point elevation** | `epqs.nationalmap.gov/v1/json` → 200 | Keyless, but one point per call — a sanity check, not a raster. |
| **AWS terrain tiles** | `s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png` → 200 | Global elevation as tiles, keyless, no quota. `terrarium` and `normal` encodings. This is the raster route. |
| **Copernicus GLO-30 DEM** | `s3://copernicus-dem-30m/` (no-sign) → listed | The same 30 m global DEM that keyed services resell, in an open bucket. |
| **awesome-citygml** | repo → 200 (MIT, updated May 2026) | The index of open semantic 3D city models. **Textured LOD2 exists for several European cities** — Hamburg (portal → 200), Vienna, Namur, Vantaa, the Netherlands via the 3DBAG API (→ 200), Switzerland via swissBUILDINGS3D (→ 200). |
| **opencitymodel (US)** | repo → 200 but **last commit 2019**, LOD1 only | There is no maintained US equivalent. For an American city the route is footprints plus heights plus your own extrusion. |

### Aerial and satellite imagery — keyless

Ground truth for layout, and source material for ground and roof textures. Both verified returning
real image data, no key, no account.

| Source | Verified | What it gives |
|---|---|---|
| **Esri World Imagery** | tile → 200, real 256×256 JPEG | Global aerial/satellite as XYZ tiles: `services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}` (note the y/x order). Attribution required. |
| **USGS NAIP** | ImageServer `?f=json` → 200 | **0.3 m per pixel** aerial imagery across the continental US. Far finer than anything global, and an ArcGIS ImageServer, so it can be queried for arbitrary extents rather than fixed tiles. |
| **NASA GIBS** | WMTS capabilities → 200 | Global satellite imagery, many layers and dates. Coarser; useful for context, not for street detail. |

What imagery is *for* here is worth being deliberate about: it shows what is actually on the ground —
block shapes, parking layouts, roof clutter, tree cover, where the industry is — which is exactly
the information a footprint file does not carry.

## Humans and animation — the hardest gap on this build

The engine arm had 500+ AAA mocap clips with a working Motion Matching setup. This one does not.

- **Mixamo** — the primary route. Rigged characters plus the clip library.
- **MPFB2** (MakeHuman for Blender) — **already installed and enabled** in the local Blender, not
  merely available to download. Verified headless: it initialises under `blender --background` and
  exposes **143 operators** under `bpy.ops.mpfb`. Among them `create_human`, `create_random_human`
  and `create_random_human_batch`; `add_standard_rig`, `add_rigify_rig` and `convert_to_rigify`
  (Rigify is installed too); `load_clothes` and `load_library_clothes`; `load_animation`. CC0
  output, no login, nothing that expires. This is the only humans route on the shelf with none of
  those three problems.
- **100STYLE** — → 200. 4M+ frames across 100 locomotion styles, CC BY 4.0, BVH.
- **CMU mocap** — → 200. Large, free, BVH.
- **Sketchfab filtered `rigged`+`animated`** — the only large source of *varied* rigged content.

BVH needs retargeting onto whatever rig you use. That work is yours.

## Gaussian splats

The most photoreal thing available in a browser, because it replays a capture rather than
approximating one. It cannot be relit and is awkward to collide with.

- **Capture your own** — Luma (→ 200), Polycam (→ 200), Scaniverse (→ 200) all capture free and
  export PLY.
- **Downloading other people's** — their galleries are built to keep scans inside the app, and the
  licences are unclear. Treat this as a capture route, not a library.
- **`playcanvas/supersplat`** — MIT, 9.8k★, pushed 13 August. The editor.
- Loading them: see `docs/tech/stack.md` — the renderer support is merged but not released.

## Reference photography — look at the real thing

| Source | Verified |
|---|---|
| **Wikimedia Commons** (search and geosearch by coordinate) | → 200 |
| **Mapillary** — street-level by bounding box, **token provisioned** as `$MAPILLARY_TOKEN` | verified: 3 images returned for a 0.01° box over downtown Miami, with `thumb_1024_url`, `captured_at` and **`compass_angle`** — so you can ask for the view facing a particular direction, which is what makes it usable as a camera reference rather than a photo dump. `graph.mapillary.com/images?access_token=…&bbox=W,S,E,N&fields=…` |
| **KartaView** street-level by coordinate | `api.openstreetcam.org/2.0/photo/?lat=&lng=&radius=` → 200, **but 0 photos within 500 m of downtown Miami**. Coverage is patchy and city-dependent: check it has anything where you are before planning around it. |
| **Openverse** | `api.openverse.org/v1/images/` → 200. Terms are ANDed; keep queries to two or three words. |

## Sound

- **Freesound** — key required, 700K sounds, best city-ambience coverage.
- **EchoThief** — → 200, no login. 115 impulse responses recorded in real spaces, CC0. These work
  **natively** in the browser through Web Audio's `ConvolverNode`, no plugin.
- **OpenGameArt** — → 200, CC0 filter, direct downloads.
- **Jamendo** — API → 200 with a public client id. **Free Music Archive** → 200. CC-licensed music
  for radio stations.
- There is no MetaSounds here. Procedural audio — engine drone from an RPM parameter, Doppler on
  passing traffic, wind, rain, electrical hum — is Web Audio you write yourself.

## Generation

- **2D, on-device, free.** `tools/gen-image.py` runs SDXL-Turbo locally through `diffusers`. No API
  key, no network cost. This is how a city gets its signage, billboards, posters, murals,
  packaging, liveries and brand marks, and how every storefront gets unique text.
- **3D, locally: no.** TRELLIS (MIT, image/text → mesh, GLB export) needs an NVIDIA GPU with
  ≥16 GB VRAM, Linux-tested. Hunyuan3D-2.1 wants 21 GB for texture generation, 29 GB for both
  stages. Neither runs on Apple Silicon.
- **3D, hosted: yes, and free.** `microsoft/TRELLIS.2` runs on Hugging Face ZeroGPU (`zero-a10g`,
  stage RUNNING as checked) and exposes a **callable Gradio API** — `/preprocess_image`,
  `/image_to_3d`, `/extract_glb`, seven endpoints in total. `gradio_client` is installed, so
  image → textured GLB is reachable from a script with no local GPU. Pair it with
  `tools/gen-image.py`, which generates the input image on-device: concept → mesh, entirely free.
  **Run end to end and verified**, from a CC0 photograph of a hydrant valve:

  | step | time | result |
  |---|---|---|
  | `/preprocess_image` | 7 s | background removed |
  | `/image_to_3d` | 42 s | |
  | `/extract_glb` | 27 s | 97,772 faces, two 1024² textures, 3.9 MB |
  | Blender decimate to 8% | ~2 s | 7,821 faces, 755 KB |

  The output holds up under inspection: a handwheel with spokes and a hole through the hub,
  hex bolting, thread rings on the outlet, worn paint, grime in the crevices. Roughly 76 seconds
  and no money for a game-ready asset with real PBR maps.

  Two gotchas that cost attempts: `extract_glb`'s `decimation_target` has a **minimum of 100000**
  and errors below it, and `gradio_client` 2.6 takes `token=`, not `hf_token=`.

  Caveats worth knowing before planning around it: ZeroGPU is queued and rate-limited, quotas are
  per-account so `$HF_TOKEN` (provisioned) raises them, and a space can go down without notice.
  Treat it as a capable source with an unreliable ceiling, not as infrastructure.

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

**Blender 5.2.0 LTS**, driveable headless (`blender --background --python script.py`, Python 3.13
inside). It imports and exports **both FBX and glTF**, which is the bridge for anything that
arrives as FBX. `MPFB2` and `Rigify` are enabled — see the humans section. Blender is also the
route to anything the web pipeline cannot do itself: decimation and LOD generation, UV unwrapping,
baking, mesh repair, and batch conversion.

Two traps, both of which cost attempts here. `timeout` does not exist on macOS, so a script that
wraps Blender in it fails with `command not found` and looks exactly like Blender producing no
output. And in 5.x the render engine enum is `BLENDER_EEVEE` — `BLENDER_EEVEE_NEXT` was a 4.x name
and now raises.

`node` v25 · `npm` · `ffmpeg` · `imagemagick` · `assimp` (FBX/OBJ/DAE → GLB) ·
`gltf-transform` · `objaverse` · `overturemaps` · `osmnx` · `shapely` · `trimesh` · `scipy` ·
`opencv` · `scikit-image` · `pyproj` · `mapbox_earcut` · `noise` · `pygltflib` · playwright with
Chromium (at `~/imagegen/bin/python`)
