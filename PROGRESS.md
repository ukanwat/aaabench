# PROGRESS

The running log. Append; never delete. Open problems only leave this file when they are
actually fixed.

Entry points: [MAP_PLAN.md](MAP_PLAN.md) · [STORY_BIBLE.md](STORY_BIBLE.md) ·
[ASSETS.md](ASSETS.md) · [WORLD_INVENTORY.md](WORLD_INVENTORY.md)

---

## Session 1 — 2026-08-14

Arrived to an empty `workspace/`. No prior work exists; this is the first session.

### Environment verified

| thing | state |
|---|---|
| `tools/serve.py` on :8080 | up, 200 |
| `shot.py --gpu-info` | `ANGLE Metal Renderer: Apple M4 Max`, webgpu **true**, maxTexture 16384 |
| node / npm | v25.3.0 / 11.7.0 |
| blender · gltf-transform · assimp · ffmpeg · imagemagick | all present |
| credentials in env | `SKETCHFAB_API_TOKEN` `MIXAMO_BEARER` `MIXAMO_USER_GUID` `FREESOUND_API_KEY` `FREESOUND_CLIENT_ID` `MAPILLARY_TOKEN` `HF_TOKEN` — all set |

### Decisions taken (architecture — mine, single-threaded)

**Renderer: three.js r185 `WebGPURenderer` + TSL.** Pinned `three@0.185.1`, vendored to
`workspace/vendor/three/` (build + jsm) and served through an import map — no bundler, so
every byte stays readable text and there is no build step to forget between an edit and a
screenshot. Verified running on the WebGPU backend headless.

Why WebGPU over WebGL2: compute shaders (needed for the light clustering below, and later for
crowd/traffic/particle work), and r185 ships a full TSL post chain natively —
`GTAONode` `SSGINode` `SSRNode` `TRAANode` `BloomNode` `DepthOfFieldNode` `GodraysNode`
`SMAANode` `FilmNode` `ChromaticAberrationNode` `Lut3DNode` `MotionBlur` `DenoiseNode`.
That removes the reason to depend on pmndrs `postprocessing` (WebGL-only) at all. Notably
**`SSGINode` exists** — screen-space GI in the box, which is a real partial answer to the
bounce-light problem `docs/tech/stack.md` calls open.

### Measurement: the point-light ceiling (this decides the night architecture)

Written as a permanent instrument: `workspace/probe.html?lights=N&shadows=0` →
`src/probe/lights.js`. A street canyon (two facades + road) with N stock `PointLight`s,
sampled with `shot.py --frames 240`. **Frame time, p50 / p99 (ms):**

| lights | p50 | p99 | note |
|---|---|---|---|
| 0 | 8.3 | 9.3 | at the 120 Hz refresh cap — "at least this fast" |
| 16 | 8.3 | 9.3 | free |
| 64 | 16.1 | 925 | already halved; p99 spike is shader compilation |
| 160 | **133.3** | 3308 | 7.5 fps — unplayable |
| 320 | **258.4** | 9235 | 4 fps |

**Conclusion: stock three.js forward lighting cannot render a night city.** One street with
160 lamps is already unplayable and the city needs thousands. So the lighting architecture is
a **clustered (Forward+) light system written by hand** — a WebGPU compute pass binning lights
from a storage buffer into a froxel grid over the view frustum, and a TSL lighting node that
loops only the lights in the fragment's cluster. Designed for now, built before the night pass.
Everything downstream is written so lighting is pluggable rather than assuming the stock path.

Second finding from the same probe: `renderer.info.render.calls` **does not auto-reset** on
this path (it accumulates across the passes of a frame). Call `renderer.info.reset()` at the
top of each frame or every draw-call number is nonsense. First smoke test reported 3927 calls
for five spheres before I noticed.

### Fixed

- **Whole frame rendered monochrome red.** `GTAONode` renders into a `RedFormat` target, so
  `colour.mul(aoPass.getTextureNode())` multiplies G and B by zero. Take `.r`.
  Before: `shots/00-smoke.png` · after: `shots/01-smoke-fixed.png`.
- `PostProcessing` → `RenderPipeline` and `renderAsync()` → `render()`; both are deprecated in
  r185 and warn on every load.

### Verified by looking

- `shots/01-smoke-fixed.png` — sun + shadow, rough concrete, wet asphalt, clearcoat car paint
  with a tight specular, transmissive glass with refraction, AO darkening at contact. The
  material model needed for a city works on this path.

### Open problems

1. **No environment lighting.** The smoke frame's shaded sides are dead flat — a hemisphere
   light is not fill. Needs real IBL (Poly Haven HDRIs, 986 available) plus SSGI before any
   lighting judgement is worth making. This is the "shadow is not absence of light" failure
   and it will be the single biggest realism gap until solved.
2. **Clustered lighting not built yet** (see measurement above).
3. Nothing else exists yet: no world, no player, no streaming, no assets.

### Next

Coastline + terrain generator, validated as data before anything is built, then the road
network, then the whole-map blockout.
