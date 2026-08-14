---
name: browser-profiling
description: >
  What a browser actually exposes to measure a real-time 3D application with —
  renderer counters, frame-time distribution, GPU timer queries, heap and GPU
  memory, long tasks, and how to tell CPU-bound from GPU-bound. Use when the
  question is "how fast is this, and what is it waiting on", when frame rate is
  uneven, when something stutters, or before optimising anything at all.
license: Apache-2.0
compatibility: Browser-specific. There is no profiler UI here — these are the instruments that exist.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Browser profiling

## When to use

Before optimising anything, and any time "it feels slow" needs to become a number. `performance-optimization` is the method — what to measure, how to reason about a budget, which fix follows from which bottleneck. This is the instrument list for a tab, because there is no profiler window here and nothing reports itself.

## The counters the renderer already keeps

A WebGL renderer maintains per-frame counters for nothing but the cost of reading them. Read them *after* the render call, and reset the per-frame ones yourself.

```js
renderer.render(scene, camera);
const i = renderer.info;
// Per frame — reset each frame by the renderer, or manually via renderer.info.reset()
i.render.calls;       // draw calls. The single most predictive number for CPU cost
i.render.triangles;   // triangles submitted (not necessarily drawn)
i.render.frame;       // frame counter
// Cumulative — these are LEAKS if they only ever grow
i.memory.geometries;  // live geometry objects on the GPU
i.memory.textures;    // live textures on the GPU
i.programs.length;    // compiled shader programs
```

`memory.geometries` and `memory.textures` never go down on their own. Dropping a JavaScript reference frees the JS object; the GPU resource is released only when explicitly disposed. A number that climbs while you walk around a city is the leak, and it will end the session as an out-of-memory crash rather than as slowness.

`programs.length` climbing during play means shaders are still compiling — every new one is a stall, usually blamed on whatever happened to be on screen.

## Frame time, not frame rate

FPS is an average, and averages hide exactly the problem you care about. Sixty average with one 200 ms hitch per second reads as broken and scores as fine.

```js
const times = new Float32Array(600);   // ~10s at 60Hz, preallocated
let idx = 0, last = performance.now();
function frame(now) {
  times[idx++ % times.length] = now - last;
  last = now;
  requestAnimationFrame(frame);
}
// Report the distribution, never the mean: p50, p95, p99, and the worst frame.
// A p99 of 40 ms with a p50 of 8 ms is a stutter problem, not a throughput problem,
// and no amount of reducing average cost will fix it.
```

Two facts about the clock itself. `requestAnimationFrame` is capped to the display refresh, so above the refresh rate you cannot see headroom — a scene that could run at 300 fps and one that can just hold 60 look identical. And rAF stops entirely in a background tab, so the first delta after refocus is enormous; clamp it or your measurements and your physics both lie.

## Where the time actually goes

The browser will not tell you this; you have to bisect it, and two experiments separate the cases:

- **Shrink the canvas** (halve the resolution). If frame time drops a lot, you are **GPU-bound** on pixels — fill rate, post-processing, overdraw, shader cost.
- **Remove objects but keep the pixels** (cull half the scene, same canvas size). If frame time drops a lot, you are **CPU-bound** on submission — draw calls, matrix updates, JavaScript.

Neither being true means you are bound on something else: shader compilation, texture upload, garbage collection, or main-thread work that is not rendering at all.

## GPU time, if you can get it

CPU frame time does not tell you what the GPU did — the driver queues work and returns immediately. For actual GPU duration:

```js
const ext = gl.getExtension("EXT_disjoint_timer_query_webgl2");
// Issue a query around your draws, then poll for its result on a LATER frame —
// results are never available in the same frame that submitted them.
```

Expect it to be missing. The extension is frequently unavailable or deliberately coarsened, because precise GPU timers are a fingerprinting and side-channel surface. Under WebGPU the equivalent is timestamp queries, also gated. When it is not there, the shrink-the-canvas experiment above is the honest substitute.

## Memory — two separate ceilings

```js
performance.memory?.usedJSHeapSize   // Chromium only, and JS heap ONLY
```

That number says nothing about GPU memory, which is where a city actually dies. Textures and buffers live outside the JS heap and are not visible to any browser API. Track them yourself, by accounting for what you upload:

```
uncompressed RGBA texture bytes = width * height * 4
with a full mip chain          = * 1.333
so one 4096 x 4096 RGBA map    = ~89 MB
```

Which is the whole reason for compressed textures — see `web-asset-pipeline`. A budget in the low hundreds of megabytes total is a browser tab's reality, and the failure mode when you exceed it is a lost context or a killed tab, not a warning.

## Stutter that is not rendering

```js
new PerformanceObserver(list => {
  for (const e of list.getEntries()) console.warn("long task", e.duration.toFixed(1), "ms");
}).observe({ entryTypes: ["longtask"] });
```

Anything over 50 ms on the main thread is a long task, and it will drop frames regardless of how cheap your rendering is. The usual sources: parsing a large JSON or glTF, decoding textures, garbage collection, and shader compilation. All four are avoidable through *when* rather than *whether* — off the main thread, or during a loading screen instead of during play.

The garbage-collection signature is worth recognising because it is misdiagnosed constantly: a sawtooth heap graph, and frame spikes at regular intervals that do not correlate with anything visible.

## The device pixel ratio trap

```js
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));   // a decision, not a default
```

On a phone at `devicePixelRatio` 3, rendering at full native resolution is nine times the pixels of `1`. This is the single largest performance lever on mobile and the easiest one to leave at its worst setting by not touching it.

## What a screenshot does not measure

A capture proves the frame renders and shows what it looks like. It says nothing about frame time, hitching, memory growth or GPU cost, and a scene that takes four seconds a frame photographs exactly as well as one that runs. Numbers and pictures are separate instruments; a claim about performance needs the first.

## Pitfalls

- **Profiling on a warm frame.** The first frames pay for shader compilation and texture upload. Measure a steady state and measure the cold start separately, because a player experiences both.
- **Measuring while the tab is unfocused.** Throttled timers, capped rAF, garbage numbers.
- **Trusting the average.** See above; the distribution is the measurement.
- **Assuming the JS heap is the memory.** It is the small half.
- **Optimising before bisecting.** Halving draw calls does nothing to a GPU-bound frame, and the hours spent are unrecoverable.

## Related skills

- `performance-optimization` — the method and the fixes; this is the instrument list.
- `web-asset-pipeline` — where texture and geometry memory actually comes from.
