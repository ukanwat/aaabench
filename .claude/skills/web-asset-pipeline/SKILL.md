---
name: web-asset-pipeline
description: >
  Getting downloaded 3D assets into a browser and keeping them affordable —
  glTF structure, texture memory arithmetic, KTX2/Basis and Draco/meshopt
  compression, GPU instancing, and the normalisation pass that stops a library
  assembled from many sources looking assembled. Use before importing anything
  at volume, when load time or memory is a problem, or when downloaded assets
  do not sit right in the scene.
license: Apache-2.0
compatibility: Browser-specific. glTF is native here — there is no import step and no asset database.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Web asset pipeline

## When to use

Before pulling assets in at volume, and any time load time, memory or visual coherence is the problem. An engine would give you an import pipeline, an asset database and a cooking step. None of that exists here: a `.glb` is a file the page fetches, and everything an importer would have done for you is either done by you or not done at all.

## What a glTF actually is

A `.glb` is a scene graph, not a model. One file can contain many nodes, many meshes, and many primitives — and **a primitive is a draw call**, so "one asset" can cost fifty.

```
scene → nodes (transform hierarchy)
          └─ mesh
               └─ primitives[]        ← one draw call each, one material each
                     ├─ attributes    → accessors → bufferViews → buffer
                     └─ material      → textures → images, samplers
```

Read the node graph before deciding an asset is usable, because the structure decides what you can do with it:

```bash
gltf-transform inspect model.glb    # nodes, meshes, primitives, materials, textures, sizes
```

That inspection answers questions no screenshot can. Are the wheels separate nodes, or welded into the body — which decides whether a vehicle can steer and roll at all. Is the origin at the base or at the centre of mass, which decides whether it sits on the ground or floats. Does it carry an armature. How many materials, and therefore how many draw calls it costs to place one.

## The arithmetic that decides whether a city loads

This is the number to internalise:

```
uncompressed RGBA on the GPU = width * height * 4 bytes
with a full mip chain        = * 1.333

1024²  →  5.6 MB        2048²  →  22 MB
4096²  →  89 MB         8192²  →  358 MB
```

A file size tells you the download; it does not tell you the GPU cost. A 3 MB JPEG at 4096² expands to ~89 MB of video memory the moment it is uploaded, because JPEG is not a GPU format — the GPU stores it uncompressed. Twenty such textures is a dead tab.

**KTX2 with Basis is the fix, and it is a different kind of compression:** it stays compressed *on the GPU*, so a 4096² map costs single-digit megabytes resident rather than 89. Two modes, and the trade is real — ETC1S is much smaller and softer, UASTC is larger and preserves detail, which matters for normal maps where artefacts read as bumps that are not there.

```bash
gltf-transform uastc  in.glb out.glb --slots "{normalTexture,metallicRoughnessTexture}"
gltf-transform etc1s  out.glb out.glb                      # everything else
gltf-transform meshopt in.glb out.glb                      # geometry
```

Loading them needs a transcoder configured on the loader; a KTX2 texture with no transcoder fails at load, not at build.

**Geometry: Draco or meshopt.** Draco compresses harder and decodes slower; meshopt decodes fast enough not to be a hitch and also handles animation data. Neither reduces GPU memory the way KTX2 does — they reduce *download*. Vertex data on the GPU is what it is.

## Instancing, because draw calls are the other ceiling

A thousand distinct trees placed as a thousand nodes is a thousand draw calls. The same thousand as one instanced draw is one. `EXT_mesh_gpu_instancing` carries this in the file; `InstancedMesh` and `BatchedMesh` do it at runtime. This is the difference between a street and a city, and it constrains how you author: variation has to come from per-instance transforms and attributes rather than from unique meshes, or you give the saving straight back.

## The normalisation pass

Assets from different sources disagree, and a library assembled without reconciling them looks assembled — the "asset store salad" that no amount of lighting fixes. What they disagree about:

- **Units.** glTF is metres by convention, and plenty of files ignore it. A model exported in centimetres arrives 100× too large. Worse is 1.2× — obviously wrong is easy, *almost* right is what ships.
- **Up axis.** glTF is Y-up. Content authored Z-up (most CAD, much scanned data) arrives on its side.
- **Origin.** Base-centre, geometric centre, or wherever the artist left it. This is what decides whether things sit on the ground.
- **Forward axis.** Nothing enforces one. A fleet facing three directions is a fleet you cannot drive.
- **Texel density.** A 4K bench beside a 512px one, in the same frame — one crisp, one soft. Nobody consciously notices; everybody feels it.
- **PBR conventions.** Roughness ranges, metalness authoring, and whether AO is already multiplied into base colour — which then gets darkened again by the renderer.
- **Baked lighting in albedo.** The counterintuitive one: **scanned assets are the worst offenders**, because photogrammetry bakes the capture day's light into the colour texture. A sunny-afternoon scanned bench dropped into a dusk street glows from a sun that is not there. The most "real" assets are the hardest to mix.

Deciding *which* of these to enforce, and what to do with an asset that fails, is judgement. But doing none of it is not a decision, it is a bug that surfaces as "the street looks wrong" with no single object to blame.

## Loading is part of the game

A first visit downloads a world. What is fetched, in what order, and what the player looks at while it happens are design decisions.

- Stream by distance; do not block the first frame on the whole city.
- Parse off the main thread where the loader supports it — a large glTF parsed on the main thread is a multi-second long task that freezes everything.
- Cache decoded results; re-fetching is cheap, re-decoding is not.
- `Cache-Control: no-store` during development is correct and a disaster in production.

## Pitfalls

- **Judging cost by file size.** The download and the GPU footprint are unrelated numbers.
- **Compressing at the end.** Retrofitting KTX2 means reprocessing every asset and re-testing every material. Decide the format on the way in.
- **Uploading everything at once.** Texture upload is a main-thread stall; a hundred at load is a frozen page.
- **Never disposing.** GPU resources are not garbage-collected. Unload what you unstream, or memory only grows.
- **One asset, one draw call.** Check the primitive count before believing that.

## Related skills

- `browser-profiling` — the counters that tell you when this has gone wrong.
- `performance-optimization` — the method behind the fixes.
