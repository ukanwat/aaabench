# Profiling & budgets — depth for `performance-optimization`

Detail the body defers here: per-engine profiler walkthroughs, the CPU-vs-GPU triage flow, a
pooling manager, batching/instancing rules, allocation guidance, LOD/culling, and asset budgets.

## 1. CPU-vs-GPU triage (decide before you fix)

```text
1. Read total frame time vs your budget (16.67 ms @60).
2. Compare CPU-frame time and GPU-frame time:
     GPU >> CPU  → GPU-bound  → draw calls, overdraw, shader cost, resolution, lights/shadows.
     CPU >> GPU  → CPU-bound  → scripts, physics, pathfinding, allocations/GC, too many nodes.
     Both high / alternating → find the per-frame spike in the timeline (one function/system).
3. Within the bound side, sort costs descending and attack the top one only.
4. Re-measure. If it didn't move the frame time, you fixed the wrong thing — revert and re-triage.
```

A GPU-bound game won't speed up from faster C#; a CPU-bound game won't speed up from fewer draw
calls. This split is the single most important decision in performance work.

## 2. Getting the numbers

There is no profiler window here. `browser-profiling` covers the instruments a tab exposes and
what each one means; two things about the triage above are worth knowing before you apply it.

**The CPU/GPU split is not handed to you.** GPU timer queries are frequently unavailable or
deliberately coarsened for fingerprinting reasons, so the honest substitute is a pair of
experiments: halve the canvas resolution (if frame time drops sharply, you are GPU-bound on
pixels) and cull half the objects at the same resolution (if it drops sharply, you are CPU-bound
on submission).

**Frame time is a distribution, not a number.** Record the last few hundred deltas and report
p50, p95, p99 and the worst. An average of 8 ms with a p99 of 40 ms is a stutter problem, and
nothing you do to the average will fix it.

## 3. Pooling manager (generic)

```text
class Pool<T>:
    free: list
    create_fn, reset_fn
    prewarm(n):  for n → free.push(create_fn())          # allocate up front, off the hot path
    acquire():   t = free.pop() or create_fn(); activate(t); return t
    release(t):  reset_fn(t); deactivate(t); free.push(t)  # never destroy; recycle
```

Pool anything spawned frequently and briefly: bullets, shells, particles, damage numbers,
enemies in waves, audio one-shots. Pre-warm at load to avoid first-use hitches. Cap the pool and
decide an overflow policy (grow, or recycle the oldest).

## 4. Batching & instancing rules

- **What breaks a batch:** a different material, texture, or render state between objects. Share
  materials and **atlas** textures so runs of objects submit as one draw call.
- **Identical meshes, many instances** → GPU instancing: one draw for a thousand copies, with
  per-instance transforms and attributes carrying the variation. See `web-asset-pipeline`.
- **Many small distinct meshes** → merge at build time where they never move independently; a
  block of static street furniture as one geometry beats forty nodes.
- **UI** → a DOM write can force a layout recalculation inside your frame. Update on change, not
  per frame, and keep anything animating on `transform`/`opacity`, which do not trigger layout.
- **Lights/shadows** → bake static lighting; cap real-time shadow casters; cull small shadows.

## 5. Allocation / GC guidance

- **JavaScript:** no allocation in the frame loop. Hoist scratch vectors and matrices; reuse
  arrays rather than rebuilding them; avoid `map`/`filter`/spread/destructuring on hot paths;
  never build strings per frame. The goal is a flat heap graph in steady state.
- **GPU resources are not garbage-collected.** Dropping a reference frees the JS object and
  leaks the buffer or texture. Dispose explicitly, and watch `renderer.info.memory`.
- **General:** strings are a classic hidden allocator (concatenation, formatting) — build them
  rarely, cache results.

## 6. Do-less techniques (algorithmic wins)

- **Run less often:** update AI/HUD/expensive checks on a timer or every N frames, not every
  frame; stagger across frames (time-slicing).
- **Spatial partition:** grid/quadtree/octree so queries touch nearby objects only, not all N.
- **LOD & culling:** lower detail at distance; frustum/occlusion culling; despawn off-screen
  far entities.
- **Cache results:** memoize pathfinding, line-of-sight, and derived data; invalidate on change.
- **Defer/Amortize:** spread procedural generation and loading across frames to avoid spikes.

## 7. Asset budgets (prevent regressions at the source)

| Asset | Typical desktop budget | Mobile budget | Notes |
|-------|------------------------|---------------|-------|
| Texture max size | 2048–4096 | 1024–2048 | use mipmaps; compress (BCn / ASTC) |
| Character triangles | 30k–80k | 5k–20k | LODs for distance |
| Draw calls / frame | low thousands | a few hundred | the count that matters most on mobile |
| Real-time lights | a few | 1–2 + baked | bake the rest |
| Audio | streamed music, short SFX in memory | same | don't decompress everything at load |

Mobile adds **thermal throttling**: a game that hits 60 FPS for 2 minutes then drops is
overheating — target headroom, cap frame rate, and reduce sustained GPU load.
