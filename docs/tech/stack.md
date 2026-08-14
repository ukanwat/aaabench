# The stack — what exists in a browser, and what state it is in

Version-checked on **14 August 2026** against the npm registry and the GitHub API. Packages rot.
The dates matter more than the descriptions, so they are here.

## The renderer

**three.js** — npm latest `0.185.1`, and the newest tagged release is **r185, 1 July 2026**.

WebGL2 and WebGPU are both shipped. WebGPU brings compute shaders and clustered lighting, which
is what makes hundreds of small light sources affordable — a night city is exactly that case. TSL
(the node material language) compiles to both backends, so a TSL material runs unmodified on
either.

## Gaussian splatting — merged, not released

PR **#33950**, *"Gaussian Splat renderer / loader using TSL for WebGPU/WebGL + glTF import"*, was
merged into `dev` on **8 August 2026**. It lands as:

```
examples/jsm/objects/GaussianSplatMesh.js
examples/jsm/loaders/SPLATLoader.js
examples/jsm/loaders/KSPLATLoader.js
examples/jsm/loaders/GLTFGaussianSplatLoaderExtension.js
examples/jsm/utils/GaussianSplatUtils.js
```

**It is not in r185.** Using it means pinning a `dev` commit or waiting for r186. The standalone
alternative is `mkkellogg/GaussianSplats3D` (MIT, 2.8k★) — last pushed October 2025.

A splat replays a capture of a real place rather than approximating one, so it is the most
photoreal thing available in a browser. It also cannot be relit and is awkward to collide with.
`playcanvas/supersplat` (MIT, 9.8k★, pushed 13 August) is the editor. Captures come from Luma,
Scaniverse or Polycam — free to make, but their galleries are built to keep other people's scans
inside the app, so a splat here means one you captured.

## Global illumination — the honest state

There is no Lumen. What exists:

| Package | State | Note |
|---|---|---|
| `pmndrs/react-three-lightmap` | MIT, **pushed 14 Aug 2026** | In-browser lightmap and AO baking: path-traced, xatlas UV unwrap, BVH tracing, denoise, progressive preview. The maintained route for static bounce light. |
| `three-gpu-pathtracer` `0.0.24` | MIT, **pushed 14 Aug 2026** | Progressive path tracing in the browser, on `three-mesh-bvh`. |
| `CodyJasonBennett/three-rc` | 75★, last push **9 Feb 2026**, **no licence declared** | Radiance-cascade GI in 3D via screen-space probes and a BVH. Real, small, and unshippable as-is until it has a licence. |
| `realism-effects` `1.1.2` | **last push 4 February 2024**, 35 open issues | SSGI/TRAA/motion blur. Two and a half years stale. The "v2 in development" note in circulation is that old. |

Baked light is static light. What happens to bounce when the sun moves is an open problem on this
build, not a solved one.

## The camera layer

`postprocessing` `6.39.4` (2.8k★, pushed 13 August) carries bokeh depth of field, chromatic
aberration, vignette, film grain, bloom, SMAA, and ACES / AgX tonemapping.

`n8ao` `2.0.1` for ambient occlusion.

## Materials, shadows, atmosphere

- `MeshPhysicalMaterial` covers the hard cases directly: **clearcoat** (car paint over metallic
  flake), **transmission** with thickness (glass), **sheen** (fabric), **anisotropy** (brushed
  metal).
- **TSL** node materials for custom shading that compiles to both backends.
- Cascaded shadow maps for large scenes; contact shadows for grounding; progressive/accumulative
  soft shadows for static scenes.
- `@takram/three-atmosphere` `0.19.1` — precomputed atmospheric scattering with a moving sun, and
  volumetric clouds.

## Physics

- `@dimforge/rapier3d-compat` `0.20.0` — WASM, ships a **raycast vehicle controller**: four
  downward casts for suspension, per-wheel friction. This is what most driving games use.
- `jolt-physics` `1.1.0` — WASM port of Jolt, with a fuller wheeled-vehicle constraint:
  suspension, tyre friction, anti-roll bars, engine and transmission.

Simulating every vehicle is not how this is done anywhere. One simulated vehicle plus kinematic
traffic on lanes is both the standard approach and the only one that holds frame rate.

## Pipeline — non-negotiable at city scale

- `@gltf-transform/cli` `4.4.2` — KTX2/Basis for textures, Draco or meshopt for geometry.
- `three-mesh-bvh` `0.9.14` — fast raycasting, and the basis of both the path tracer and the
  lightmap baker.
- `3d-tiles-renderer` `0.5.1` — streaming tilesets, if real-world tiles ever come into it.
- `BatchedMesh` / `InstancedMesh` for draw-call count.

## The ecosystem, by what it replaces

Checked on 14 August 2026: version, stars, last push, licence. The dates are the point — this
ecosystem has a lot of well-known packages that stopped shipping years ago, and a recommendation
you find in a blog post is not evidence that something is maintained.

| Need | What exists | State |
|---|---|---|
| **Frame debugging** | `spectorjs` | MIT, 1.6k★, pushed 11 Aug 2026. Captures a frame and shows every draw call, state change, shader and binding. The closest thing to an engine's frame debugger. |
| **GPU timing** | `stats-gl` 4.2.3 | 277★, pushed Jul 2026. Real GPU milliseconds via timer queries, not rAF deltas. |
| **Navigation + crowds** | `recast-navigation-js` 0.43.1 | MIT, 425★, pushed Jul 2026. Recast/Detour in WASM: navmesh generation *and* DetourCrowd agents, with a three.js binding. |
| **Agent behaviour** | `yuka` 0.7.8 | MIT, 1.4k★, pushed Jul 2026. Steering, state machines, path following, vehicle behaviours. |
| **Character / vehicle control** | `ecctrl` 2.0.0 | MIT, 775★, pushed Jun 2026. Physics-driven controller on Rapier. |
| **Particles / VFX** | `three.quarks` 0.17.1 | MIT, 1k★, pushed May 2026. |
| **Text and signage** | `troika-three-text` 0.52.5 | MIT, 1.9k★, pushed Jul 2026. SDF text: crisp at any distance from one atlas, rather than a texture per sign. |
| **Mesh simplification / meshlets** | `meshoptimizer` 1.2.0 | MIT, 8.2k★, pushed Aug 2026. Simplification, clustering, vertex optimisation. |
| **Meshlet LOD (Nanite-like)** | `three-nanite` | MIT, 480★, **last push Sep 2024**. An attempt, not a system. three.js Blocks lists meshlet streaming on its *roadmap*. |
| **Cascaded shadows** | `three-csm` 4.2.1 | For large scenes. |
| **Atmosphere / clouds** | `@takram/three-atmosphere` 0.19.1, `@takram/three-clouds` 0.7.6 | MIT, 1.6k★, pushed May 2026. Precomputed scattering and volumetric clouds. |
| **Light shafts** | `three-good-godrays` 0.12.1 | 231★, pushed Aug 2026, **licence unasserted** — check before shipping. |
| **Lightmap baking** | `@react-three/lightmap` | MIT, 156★, pushed Aug 2026. In-browser, path-traced, xatlas unwrap. |
| **Pipeline** | `@gltf-transform/cli` 4.4.2, `gltfpack` | MIT, 1.9k★, pushed Aug 2026. Installed. |
| **Audio** | `tone` 15.1.22 | If Web Audio directly is not enough. |

**There is no play-in-editor for vanilla three.js.** Checked: Theatre.js (12.6k★) is a
motion-design tool and last shipped August 2024; Needle Inspector is a Chrome extension, so it
cannot be part of a build; the three.js editor has standing issues about which camera renders in
play mode. The two-camera, one-key pattern is yours to write — it is not large, and nothing
packaged does it.

**Navigation and debug UI, if you are building the inspection layer:** three.js itself ships
`FlyControls`, `FirstPersonControls`, `OrbitControls`, `MapControls`, `PointerLockControls`,
`TrackballControls`, `ArcballControls`, `DragControls` and `TransformControls` — free-camera
navigation is an import, not a dependency. For panels, `lil-gui` 0.21.0 or `tweakpane` 4.0.5;
for a GPU-aware frame readout, `stats-gl` 4.2.3. Dedicated three.js *inspectors* are thin —
the best maintained is 63★ and last shipped June 2024 — so a panel you wire yourself is likely
to be better than one you adopt.

Built into three.js already, and easy to miss: `LOD`, `InstancedMesh`, `BatchedMesh`, `AnimationMixer`,
`PositionalAudio`, `Sky`, `Water`, `EffectComposer`, `LightProbe`, `DecalGeometry`, and TSL node
materials.

**This is an inventory, not a recommendation.** Nothing here says which of these belongs in your
build, whether you need it at all, or whether writing your own is better. Check the dates yourself
before depending on anything: two of the most commonly recommended packages in this ecosystem have
not shipped since 2024.

## What a browser does not have

Stated plainly so nobody plans around a thing that isn't there: no Lumen, no Nanite, no MetaHuman,
no Chaos Vehicles, no Mass crowd or traffic framework, no Motion Matching, no MetaSounds, no
PoseSearch, no Sequencer, and no editor. There is a canvas, a GPU, and whatever gets written.
