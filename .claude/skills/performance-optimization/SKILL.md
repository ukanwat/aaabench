---
name: performance-optimization
description: >
  Find and fix game performance problems methodically — measure with the engine profiler first,
  reason about the frame-time budget, locate the CPU-vs-GPU bottleneck, then apply the right fix:
  object pooling, draw-call batching, fewer allocations/GC spikes, and asset budgets. Engine-
  neutral method that pairs with each engine's profiler. Use when the user mentions performance,
  optimize, low/dropping FPS, frame drops, stutter, lag, profiler, frame budget, draw calls,
  batching, garbage collection/GC spikes, object pooling, or "the game runs slow".
license: Apache-2.0
compatibility: Platform-neutral methodology. There is no profiler UI here — the instruments are the browser's own.
metadata:
  engine: none
  category: disciplines
  difficulty: advanced
---

# Performance optimization

Performance work is a measurement discipline, not a bag of tricks. The method is always the
same: **profile → find the one bottleneck → fix that → measure again**. This skill teaches that
loop and the highest-leverage fixes (pooling, batching, allocation control, asset budgets), and
points you at each engine's profiler. It pairs with `physics-tuning` for simulation cost.

## When to use

- Use when the frame rate is low or uneven, the game stutters/hitches, or it must hit a target
  (60 FPS desktop, 30/60 mobile) and currently doesn't.
- Use to decide *what* to optimize: profile, read the frame budget, and identify whether the CPU
  or GPU is the bottleneck before changing any code.
- Use to apply specific fixes: object pooling, draw-call/batch reduction, removing per-frame
  allocations and GC spikes, and setting asset budgets.

**When *not* to use:** for physics jitter/tunneling/timestep specifically, use `physics-tuning`.
For what a browser actually exposes to measure with — there is no profiler UI here — see
`docs/tech/stack.md` and the browser's own developer-tools documentation. This skill is the
method and the shared fixes, not the instrument.

## The golden rule: measure first, never guess

Most performance "fixes" applied without profiling target the wrong thing and add complexity for
no gain. **Do not optimize code you have not measured.** Open the profiler, find the single
biggest cost in a representative scene on representative hardware, and fix that. Re-measure to
confirm the fix helped before moving on. Profile a **release/optimized build** where it matters —
editor and debug builds lie (editor overhead, no compiler optimization).

## Core workflow

1. **Define the target and reproduce.** State the goal (e.g. 60 FPS = 16.67 ms/frame) and find a
   repeatable worst-case scene. "Sometimes slow" is unfixable; a reproducible spike is fixable.
2. **Profile before touching code.** Run the engine profiler and read the frame: total frame
   time, and the split between CPU (game logic, physics, scripts) and GPU (rendering).
3. **Find the bottleneck — CPU or GPU.** If GPU time ≫ CPU, attack draw calls/overdraw/shaders/
   resolution. If CPU time dominates, attack scripts/physics/allocations. Fixing the wrong side
   does nothing.
4. **Fix the single biggest cost.** Prefer an **algorithmic** win (do less work, cache, spatial
   partition, run less often) over micro-optimizing a hot line. Apply the matching shared fix
   (pooling, batching, allocation removal).
5. **Re-measure on the same scene/hardware.** Confirm the number moved. Keep or revert based on
   data, not intuition.
6. **Set budgets so it stays fixed.** Per-frame ms budgets per subsystem, plus asset budgets
   (texture sizes, triangle counts, draw-call ceilings); add a perf check to verification.
7. **Report measured numbers.** State before/after frame time, the bottleneck found, and the fix
   — never "should be faster". If you could only measure in-editor, say so.

## Patterns

### 1. Frame budget math (turn "feels slow" into a number)

```text
target FPS → frame budget:   60 FPS = 16.67 ms   |   30 FPS = 33.3 ms   |   120 FPS = 8.33 ms
The WHOLE frame (CPU sim + render submit + GPU) must fit the budget; the GPU runs in parallel,
so the slower of CPU-frame and GPU-frame sets your FPS. Allocate sub-budgets, e.g. @60 FPS:
  gameplay/scripts ~5 ms · physics ~3 ms · rendering(CPU submit) ~4 ms · UI/other ~2 ms · slack.
If one subsystem blows its slice, that's your target — not whatever you assumed.
```

### 2. Measure before any fix

There is no profiler window here, and nothing reports itself. The instruments a browser does
expose — renderer counters, frame-time distribution, GPU timer queries, heap and long tasks — and
what each of them does and does not mean are in `browser-profiling`. Read it before optimising,
because the first question is not "how do I make this faster" but "what is it waiting on", and
the two experiments that answer it take a minute each.

### 3. Object pooling (stop allocating/freeing in hot loops)

```js
// Bullets, particles, enemies, damage numbers: reuse a fixed set instead of
// creating and discarding every frame — that thrashes memory and feeds the collector.
const pool = [];
function acquire() {
  const n = pool.pop() ?? makeBullet();
  n.visible = true; n.active = true;
  return n;
}
function release(n) {
  n.visible = false; n.active = false;   // disable and hide; do NOT dispose
  pool.push(n);                          // back to the pool for reuse
}
// RIGHT: pre-warm the pool at load and reuse. WRONG: creating per shot.
// Note what disposal means here: dropping a JS reference frees the JS object, but
// GPU buffers and textures are not garbage-collected — they are released only when
// you explicitly dispose them, which is why pooling and leak-checking are the same
// discipline.
```

### 4. Cut draw calls (the most common GPU-side win)

```text
Each unique material/texture/state change is roughly a draw call; thousands of them stall the GPU.
- Atlas textures and share materials so sprites/meshes batch into one call.
- Identical meshes → GPU instancing: one instanced draw for a thousand copies, with per-instance
  transforms and attributes carrying the variation. See `web-asset-pipeline`.
- Static geometry → static batching / baking; mark non-moving objects static.
- Reduce overdraw: limit large overlapping transparent/particle layers (they re-shade pixels).
- Fewer real-time lights/shadows; bake lighting where it doesn't move.
Measure draw calls before and after — the count should drop, and so should GPU frame time.
```

### 5. Kill per-frame allocations (GC spikes = stutter)

```js
// Allocating every frame fills the heap; the collector then stalls a frame, and the
// stutter shows up somewhere unrelated to the code that caused it.
// WRONG (allocates on every call): const dir = new Vector3(...); const hits = arr.filter(...)
// RIGHT: hoist the scratch objects and reuse them.
const _dir = new Vector3(), _hitBuffer = new Array(32);

function update(dt) {
  _dir.copy(target).sub(position).normalize();     // no allocation
  const n = raycastInto(_hitBuffer, ray);          // fills a reused array
  for (let i = 0; i < n; i++) { /* ... */ }
}
// The tells in a profile: a sawtooth heap graph, and frame-time spikes at regular
// intervals that do not correlate with anything on screen. Watch for the quiet ones
// too — array destructuring, spread, closures created per frame, and string
// concatenation for debug output all allocate.
```

## Pitfalls

- **Optimizing without profiling.** The intuitive culprit is usually wrong. Measure first, every
  time.
- **Profiling the editor / a debug build.** Editor overhead and unoptimized code mislead. Profile
  a release build on target hardware for real numbers.
- **Fixing the wrong side.** Micro-optimizing CPU code when the GPU is the bottleneck (or vice
  versa) changes nothing. Check the CPU-vs-GPU split first.
- **Micro-optimizing over algorithm.** Shaving a function when an O(n²) loop or a per-frame
  full-scene query is the real cost. Reduce the work, don't polish it.
- **Instantiate/free in hot loops.** Spawning and destroying bullets/particles every frame causes
  fragmentation and GC spikes. Pool them.
- **Per-frame allocations / LINQ / boxing in `Update`** (C#) feed the GC → periodic hitches.
  Cache and reuse.
- **Draw-call explosion** from unique materials and unbatched sprites/meshes. Atlas, share
  materials, instance, batch.
- **Overdraw** from stacked transparents/particles/full-screen effects re-shading pixels.
- **No budgets.** Without per-subsystem ms and asset ceilings, performance silently regresses;
  enforce them in your build/CI checks.
- **Optimizing too early.** Don't contort a prototype for performance before it's fun or measured.

## References

- For per-engine profiler walkthroughs, the CPU-vs-GPU triage flowchart, a complete pooling
  manager, batching/instancing rules per engine, allocation/GC guidance, LOD/culling, and asset
  budgets (texture sizes, triangle counts, audio, mobile thermals), read
  `references/profiling-and-budgets.md`.

## Related skills

- `physics-tuning` — simulation cost, fixed-step budget, sleeping bodies, broadphase layers.
- `procedural-gen`, `game-ai` — common CPU hotspots (generation, pathfinding) to budget and defer.