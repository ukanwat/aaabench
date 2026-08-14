# PROGRESS

The running log. Append; never delete. Open problems only leave this file when they are
actually fixed.

Entry points: [MAP_PLAN.md](MAP_PLAN.md) · [STORY_BIBLE.md](STORY_BIBLE.md) ·
[ASSETS.md](ASSETS.md) · [WORLD_INVENTORY.md](WORLD_INVENTORY.md)

## Rebuilding the world — run this first if the page is blank

`workspace/world/height.bin` is generated output and is not in git; the generator is
authoritative and deterministic (`SEED = 20260814` in `tools/worldgen/config.py`), so it is
rebuilt rather than stored. From the repo root:

```bash
python3 -m tools.worldgen.build  --preview     # terrain  → .worldcache/  (~28 s)
python3 -m tools.worldgen.roads  --preview     # roads    → .worldcache/roads.npz
python3 -m tools.worldgen.export               # runtime  → workspace/world/
```

Then `http://127.0.0.1:8080` (server: `python3 tools/serve.py --dir workspace --port 8080`).
Check it with:

```bash
~/imagegen/bin/python tools/shot.py http://127.0.0.1:8080 -o shots/check.png --wait 6000 \
  --eval "game.setHour(9); game.stand(150, 620, 20)" --report "game.info()"
```

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

### The road network — `tools/worldgen/roads.py`

`python3 -m tools.worldgen.roads --preview` → `shots/world/roads.png`. 0.3 s, 24.7 km of road.

Roads are **routed, not drawn**: least-cost path (`skimage.graph.route_through_array`) over a cost
surface built from the finished terrain — gradient penalised as `(grade/0.04)^2.6`, low ground
penalised because it floods, water at 4000. Routed **in the order the real ones were built**, and
after each route its corridor is discounted, because an existing corridor is already cut, drained
and owned. The result shares alignments and bends around what was in the way without anyone
placing a curve.

**Crossings are measured, not authored.** `find_narrows` scans a stretch of water for the
shortest contiguous span with land on both banks — which is what decided where the bridge went,
and where the ferry ran for two centuries before it. Narrows Bridge: **472 m span at x = 644**.

Grades, after fixes (p95 / max over a 16 m chord): Harbour Street 9.9 / 17.9 · Ash Street 9.1 /
19.2 · Route 9 7.7 / **12.1** · Vantage Drive 10.3 / 22.5 · Bar Road 8.0 / 13.1 · Fenmoor Road
6.7 / 17.0 · Kiln Road 4.2 / **49.4** · Old Ferry Road 8.4 / 9.8.

Fixed during the pass:
- **Every road had an unclimbable maximum grade and Bar Road was 8% in water with a 446% max.**
  `smooth_path` splined at `s = len·24`, which pulled the centreline so far off the least-cost
  path that roads left the corridor they had just paid to find and ran over cliffs and across the
  lagoon. Now `s = len·1.8`: routing decides where the road goes, smoothing only removes the
  staircase.
- **Grade was measured between adjacent samples**, so one bad cell in a 2 m heightfield read as a
  cliff. Now measured over a 16 m chord, which is what a gradient actually means.
- **Bar Road ran off the bottom of the map into open sea.** A waypoint with no reachable land near
  it is now dropped rather than routed to.
- **The Causeway crossing could not be found at all.** `find_narrows` measured min-to-max water in
  a column, so it rejected any span whose water touched the search window — which is every
  crossing where the far bank is a thin spit with open sea beyond it. Now finds the shortest
  contiguous run with land on both sides.

### The world is in the browser

`tools/worldgen/export.py` → `workspace/world/`: **height.bin** (1250 × 1000 at 4 m, int16
centimetres, **2.5 MB**), **land.png**, **manifest.json** (bounds, districts, 8 road centrelines,
stats).

The heightfield ships as **one raw image, not per-chunk geometry**. The GPU holds it as a single
texture and terrain is drawn by displacing a plain grid in the vertex shader, which means: level
of detail costs nothing but a coarser grid; neighbouring chunks at different detail levels sample
the same source so they cannot disagree at their seams and there is nothing to stitch; and there
is no per-chunk mesh data to stream at all. Normals are taken per-fragment from the height
texture rather than from the mesh, so a coarse distant chunk is still lit by the real shape of
the ground instead of by its own faceting. The same numbers are kept on the CPU
(`Heightfield.heightAt/normalAt/slopeAt/isLand`) so that placement, collision and spawning cannot
drift from what is drawn.

Runtime modules: `src/world/heightfield.js` · `src/world/terrain.js` (256 m chunks, 4 LOD levels
at 64/32/16/8 segments, 3.4 km draw distance) · `src/world/roadmesh.js` · `src/main.js`.

**The outside interface** — `window.game`: `setHour(h)` · `goto(district, {dist,yaw,pitch})` ·
`stand(x, z, bearing, eye)` · `aerial(y)` · `info()`. Every capture from here on is repeatable
and comparable across sessions rather than depending on getting the camera back by hand.

**Measured, whole map streaming, camera over The Spine at 600 m:**
frame time **p50 8.3 ms / p95 9.3 / p99 9.3** (at the 120 Hz refresh cap — "at least this fast"),
319 chunks live, 163 k triangles, 16 textures. Plenty of headroom at blockout stage.

### Verified by looking — and what the frames say

- `shots/03-world-aerial.png` — the whole island from 4.2 km, silhouette matching the generator,
  road network legible.
- `shots/04-bellcross-street.png` — standing in Bellcross at eye height. **This frame is the
  argument for open problem 1.** The water is *black*, because a surface at roughness 0.07 with
  nothing to reflect can only be black; the ground is a single flat olive with no landform in it;
  the sky is a flat colour with no gradient; and the horizon is dead. Nothing here is a texturing
  problem — it is the absence of environment lighting, and it will not be fixed by adjusting any
  of these values.
- Fog was at `FogExp2 0.00028`, which washed the entire map to sky colour from altitude and left
  a frame with no weather in it at all, just even grey. Now 0.00006. Haze has to grow with
  distance, not sit on everything equally.

### Environment lighting and a real day — `src/world/sky.js`

**Open problem 1 is now partly closed.** The environment is the Preetham analytic daylight sky
(`SkyMesh`, the TSL/node version — the only one that works on the WebGPU path), rendered to a
cube map and PMREM-filtered into an irradiance probe, and **the probe is rebuilt whenever the sun
moves more than ~0.7°**. So the ambient at dusk is the dusk sky, not noon turned down — which is
the difference between night as a world and night as a colour grade.

A captured HDRI would be more photoreal for one instant and wrong for every other, because it
bakes the sun position it was shot at. This world has a moving sun, so the sky has to be a
function of it. The sun disc is excluded from the probe: a few thousand-nit pixels in a 256px
cube face become a blotchy hotspot in the irradiance, and the sun is already the directional light.

**The sun is now real solar geometry** — declination, hour angle, latitude 38°N — not a curve.

Fixed in this pass, each of them a cause rather than a value:

- **Dawn, 18:30, dusk and night were four identical dead grey frames.** The day model was a
  half-sine over 06:00–18:00, so the sun hard-switched off at both ends: the golden hour and
  twilight did not exist in the model at all. Replaced with solar position; direct sun now fades
  through the last few degrees and reddens as it does, because that reddening *is* the golden
  hour and it comes from atmospheric path length, i.e. from elevation.
- **The whole sky turned sage green at dawn and dusk.** Two independent causes. (a) Fog was being
  applied to the sky dome — it sits at 20 km, where `FogExp2 0.00006` reaches ~70%, so the sky was
  being dragged to the haze colour. Fog is what the atmosphere does to things seen *through* it;
  the sky *is* the atmosphere. `sky.mesh.material.fog = false`. (b) The horizon colour was
  interpolated by **rotating hue** from blue (0.58) toward orange (0.07), which passes through
  green and parked on 0.33. Hue is a circle; lerping it takes whichever way round the numbers go.
  Now a lerp between three explicit colours.
- **A heavy ordered stipple over the entire frame.** GTAO's raw output carries its magic-square
  sampling noise and needs either TRAA or an explicit `DenoiseNode`. It was being multiplied into
  the frame unfiltered. Took the denoise.
- **The ground blew out to near-white.** The Preetham sky is bright in linear units and PMREM
  keeps that brightness. Swept `environmentIntensity` × `toneMappingExposure` as a 4-up contact
  sheet (`shots/07-exposure-sweep.png`) and read the frames rather than the numbers; landed on
  env 0.08 / exposure 0.70 at full day, both now driven by sun elevation so twilight opens up.

`shots/10-time-of-day-fixed.png` — six hours side by side. Dawn has deep blue overhead with a
warm band at the horizon; 18:30 puts genuine golden light on the ground; night is dark rather
than grey.

New in the outside interface: `setEnv(i)` · `setExposure(e)` · `setSunIntensity(i)`, so lighting
can be swept from the harness instead of edited and reloaded.

### Open problems

1. **Environment lighting is half solved.** The sky-driven probe is in and it tracks the sun, but
   **there is still no bounce**: the light a sunlit wall throws back across a street does not
   exist, because there are no walls yet and because sky-probe irradiance is not interreflection.
   `SSGINode` ships in r185 and is the obvious next instrument. **The real test cannot be run
   yet** — it has to be judged in the narrowest street in the city, and there are no streets.
   Re-open this the moment buildings exist.
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

8. **NOTHING USES THE NARROWS BRIDGE.** Diagnosed this far, so a later session does not have to
   redo it: the crossing *is* found (472 m span at x = 644, north bank `(644, −624)`, south bank
   `(644, −144)`) and `stamp_bridge` *does* write a 3-cell corridor at price 5.0 across it before
   any routing. The two waypoints either side genuinely snap to opposite banks — `(760, −60)` →
   `(732, −8)` on the south shore, `(820, −520)` → `(812, −816)` on the north — so the segment
   must cross somehow, and yet a check of every routed path against the land mask shows **no road
   crossing water anywhere near x = 644, z ∈ [−624, −144]**. Vantage Drive goes the long way round
   the harbour head instead. Back-of-envelope says the bridge should win (≈472 m at 5 ≈ 2,400
   cost·m, versus ~4 km of land route), so either the stamp is not landing where it is calculated
   to, or `route_through_array`'s geometric weighting makes the corridor dearer than it looks.
   **Next step: render the cost surface itself and look at it** rather than reasoning about it.
   This is the single most important road bug — the bridge is the signature landmark of the map.

9. **The Causeway crossing is in the wrong place.** `find_narrows` correctly returns the shortest
   span in the search window, but the shortest span in that window is a **64 m inlet on the
   mainland at x = 644**, not the lagoon crossing to Tern Bar. Ash Street and Bar Road are both
   using it (80 m of water each). "Shortest span" is the right rule but it needs a second
   condition — that the two banks are on *different* landmasses — or the search window has to be
   narrowed to the lagoon.

10. **No road reaches Tern Bar or Cray Lagoon**, because the spit is too thin for a waypoint to
    snap to. Downstream of open problem 6.

11. **Kiln Road still has a 49% maximum grade** where it climbs Kiln Rise to the quarry. Every
    other road is inside 23%.

12. **Draw-call accounting is still not trustworthy.** `renderer.info.reset()` is now called at
    the top of every frame and the number is still ~4,300 for ~320 chunks (≈640 draws expected
    across the shadow and main passes). Either `reset()` does not clear everything on the
    WebGPU + `RenderPipeline` path or there are passes I am not counting. **Do not quote a
    draw-call figure until this is settled** — get a real instrument on it (`spectorjs` captures a
    frame and lists every draw; `stats-gl` gives GPU milliseconds via timer queries; both are
    current per `docs/tech/stack.md`).

13. **Speckled/dithered artefacts along the coastline** at grazing angles in
    `shots/04-bellcross-street.png`. Untriaged — suspect the terrain surface interpenetrating the
    water plane, or the AO pass at grazing incidence.

14. **Water is a flat plane with a single colour.** No swell, no wind chop, no shoreline
    interaction, no depth. Downstream of open problem 1 for the reflection, but the surface
    itself is also unbuilt.

15. Nothing else exists yet: no buildings, no parcels, no player controller, no vehicles in the
    world, no crowds, no interiors, no UI, no missions. The road network is a graph of
    centrelines rendered as flat ribbons — no camber, crossfall, superelevation, kerbs or graded
    verge, all of which is mesh-pass work against a layout that is still moving.

### Next, in order

1. **Road network** as a graph over the finished terrain — shore road first (it came first in
   reality), then the downtown grid on the outcrop, then the climbing streets, then the Ring, the
   Causeway and Vantage Drive. Gradient and connectivity checked as data before anything is built.
2. **Whole-map blockout** — every district in primitives at real scale. This is the gate: the
   full city must exist as grey boxes before anything is dressed.
3. Streaming from the first line of the renderer, not retrofitted.
4. Then the clustered light system, then IBL, then the art passes in tier order.
