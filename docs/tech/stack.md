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

## What a browser does not have

Stated plainly so nobody plans around a thing that isn't there: no Lumen, no Nanite, no MetaHuman,
no Chaos Vehicles, no Mass crowd or traffic framework, no Motion Matching, no MetaSounds, no
PoseSearch, no Sequencer, and no editor. There is a canvas, a GPU, and whatever gets written.
