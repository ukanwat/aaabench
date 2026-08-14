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

### The terrain generator — `tools/worldgen/`

`python3 -m tools.worldgen.build --preview --stage N` (1 natural · 2 +deposition · 3 +human works).
~28 s for the whole world. Writes `.worldcache/{height,land,sdf}.npy` and inspection renders to
`shots/world/`. Modules: `config.py` (all authored structure) · `noisefield.py` (vectorised
Perlin/fbm/ridged/warp) · `terrain.py` (the pipeline) · `preview.py` (the instruments) ·
`build.py` (CLI).

**The approach was rewritten once, and that was the right call.** The first version authored
closed coastline polygons and roughened them with noise. It produced two fat potatoes: the
hand-drawn bays were swamped by the noise, the Sound was a scratch between two blobs, and the
land was a 1.9%-slope plane. The failure was not tuning — it was the primitive. A ria is not
"the gap between two polygons", it is a river valley cut when the sea was 40 m lower and then
drowned. So the pipeline now is:

> **uplift (a coastal plain + massifs) → relief noise → carve the valley → erode against a
> −40 m glacial base level → flood to zero → deposition → human works**

The coastline is authored nowhere. It is wherever the finished surface crosses zero, which makes
the bays drowned tributaries, the headlands the ridges between them, and the islands hills the
water went round. Erosion is stream-power incision (`K·A^m·S^n`) on D8 flow accumulation over a
depression-filled DEM, plus hillslope diffusion, 45 iterations at 8 m — so the drainage has a
history rather than a spectrum.

**Measured world:** 6.75 km² of land in a 20 km² box · highest point 117.6 m · deepest water
−62.7 m · median land slope 10.3% · sea p50 −30.5 m.

### Bugs found and fixed in the generator (each was invisible in the data)

1. **35,000 spikes of up to 56 m, as vertical streaks.** `_line_fields` rasterised the valley
   spline with `ImageDraw.line` and looked up "position along the line" per pixel. The Bresenham
   in-fill pixels between samples carry no value, so 0.7% of the map inherited `t = 0` — which at
   the head of the valley means +26 m instead of −30 m. Replaced with a cKDTree over dense spline
   samples: exact distance *and* exact position-along, no rasterisation, no quantisation.
2. **A straight-edged wedge sliced out of the north shore.** Nearest-point-on-curve is
   discontinuous across the curve's medial axis, so floor depth and valley width jumped there.
   Fixed by parameterising down the valley by **x** (monotonic, continuous everywhere) instead.
3. **Massif rim profile inverted.** `(1−d) ** (1/flat)` with `flat > 1` gives an exponent *below*
   one, whose gradient goes to infinity at the rim — a cliff edge and a tableland interior, the
   exact opposite of the intent. Now `smoothstep(1,0,d) ** shape`, zero gradient at both ends.
4. **Only the inner third of each massif was above water.** Adding a fraction of the peak to a
   floor 58 m down. Now interpolates between the deep floor and the peak.
5. **Every summit in the world silently shaved to 35 m.** The valley cross-section clamped `s`
   at 1, so the valley surface plateaued at `floor + SIDE_HEIGHT` and `np.minimum(h, valley)`
   capped the whole map. The profile now keeps climbing past the valley so the min is a no-op.
6. **The entire ocean raised to −0.50 m.** `np.maximum(h, ridge − 0.5)` for the spit: the −0.5
   applies wherever the ridge profile is zero, i.e. everywhere. Then the proximity band that
   replaced it floored a 380 m corridor and put radial caps at the ends of the line — two rounded
   lobes of shallow water in the open sea. Now gated on the ridge actually having height.
7. **The harbour was an open strait, not a harbour.** The two massifs' own coastlines ended far
   apart across the valley, and a subtractive valley cut can never pull two shores together.
   Fixed by adding the **coastal plain** the river had to incise in the first place — the
   landmass — with the massifs as hills on top of it.

### Rules preferred over instances

- The spit's line is **derived from the generated south coast** (smoothed hard, stepped seaward)
  rather than hand-placed, because a hand-placed line was 400–800 m out in deep water the moment
  the terrain moved, and would be again on every retune. The lagoon is then derived from the
  spit, because a lagoon is shallow *because* the bar is there.
- Reclaimed land only fills ground that is actually shallow water, and the quarry only cuts where
  there is actually a hillside — so an overshooting polygon costs nothing instead of stamping a
  plateau across the harbour.
- Polygon edges are broken up by noise in `_poly_mask`, once, so every authored region in the
  world inherits the fix.

### Instruments built

- `probe.html` + `src/probe/lights.js` — the point-light ceiling sweep.
- `tools/worldgen/preview.py` — hillshaded hypsometric aerial, slope map with unclimbable
  gradients flagged, cross-sections through the harbour, and **per-district land/slope/elevation
  stats**. That last one is the useful one: global median slope says nothing, because a hilly
  coast is legitimately steep. The only question is whether the ground each district sits on is
  ground a city could be built on. It immediately caught North Point and The Reach as too steep
  and Cray Lagoon as having no lagoon.

### Verified by looking

`shots/world/aerial-s3.png` — enclosed ria harbour with an inner basin, irregular emergent
coastline with real headlands and inlets, correct bathymetry (deep channel, shallow lagoon),
drift-built spit with the lagoon behind it, flooded quarry, erosion drainage on the hillsides.
Seven earlier iterations are in the same directory under `-s1`.

### Documents written

`MAP_PLAN.md` (the whole city, nine districts, real-world anchors with coordinates, quality
tiers, what is in and out) · `STORY_BIBLE.md` (premise, 3-act arc, five factions, fourteen named
cast with want/contradiction/register/colour, performance and costume notes, invented brands).

**The generator corrected the plan and the correction was kept:** North Point came out as a
peninsula rather than an island, because the valley floor climbs above sea level at the head of
the harbour — which is where a drowned valley stops being drowned. That is better than the sketch
and `MAP_PLAN.md` now says why.

### Open problems

1. **No environment lighting.** Shaded sides are dead flat; a hemisphere light is not fill. Needs
   real IBL (Poly Haven, 986 HDRIs) plus SSGI before any lighting judgement is worth making.
   This is the "shadow is not absence of light" failure and it is the biggest realism gap.
2. **Clustered lighting not built.** Measured ceiling above; a night city is impossible without it.
3. **Reclaim and quarry edges still read as geometric from the air** despite the edge jitter —
   the straight runs are still visible in `aerial-s3.png` mid-map. Needs the edges to follow
   something real (a seawall alignment, a rail spur, a contour) rather than noise on a polygon.
4. **The lagoon has a hard straight edge at its eastern end** where the derived strip is cut off
   in x, visible around `(2000, 1250)`.
5. **North Point (18.6% median slope) and The Reach (14.0%) are too steep** for cliff-top estates
   and postwar tract housing respectively. Bellcross at 10.9% is correct — it is meant to be a
   steep terrace district.
6. **The spit is narrower than a real barrier island** and Tern Bar is only 16% land within its
   district radius, so the district as planned does not yet have ground to stand on.
7. **`renderer.info.render.calls` does not auto-reset** on the WebGPU + post-processing path;
   call `renderer.info.reset()` per frame or every draw-call number is meaningless.
8. Nothing else exists yet: no roads, no streaming, no buildings, no player, no assets in the
   world.

### Next, in order

1. **Road network** as a graph over the finished terrain — shore road first (it came first in
   reality), then the downtown grid on the outcrop, then the climbing streets, then the Ring, the
   Causeway and Vantage Drive. Gradient and connectivity checked as data before anything is built.
2. **Whole-map blockout** — every district in primitives at real scale. This is the gate: the
   full city must exist as grey boxes before anything is dressed.
3. Streaming from the first line of the renderer, not retrofitted.
4. Then the clustered light system, then IBL, then the art passes in tier order.
