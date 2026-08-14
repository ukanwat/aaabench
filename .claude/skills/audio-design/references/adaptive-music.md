# Adaptive (dynamic) music

Adaptive music changes with gameplay instead of looping one track. Two techniques
dominate, and they combine:

- **Vertical layering (re-orchestration)** — several stems (drums, bass, melody,
  tension pad) play in sync; you fade layers in/out to change intensity without
  changing the underlying loop. Seamless because all layers share the same
  timeline.
- **Horizontal re-sequencing** — the track is split into segments (intro, loop A,
  loop B, combat, outro); you switch which segment plays next, transitioning at
  musical boundaries (bar/phrase) so the change lands on beat.

## Vertical layering

All layers are the same length and start together; only their volumes change.

```js
// Keep N stem players in sync and fade volumes by intensity.
const layers = {};   // name -> { src, gain }
function startLayers(buffers, when = ctx.currentTime + 0.1) {
  for (const [name, buffer] of Object.entries(buffers)) {
    const src = ctx.createBufferSource(), gain = ctx.createGain();
    src.buffer = buffer; src.loop = true;
    gain.gain.value = 0;                 // start silent
    src.connect(gain).connect(buses.music);
    src.start(when);                     // ALL start at the same absolute time
    layers[name] = { src, gain };        // -> they stay sample-aligned forever
  }
  fade("base", 1);
}
// Starting them on separate frames is the classic failure: they drift apart by
// milliseconds and the stack smears instead of locking.

function setIntensity(level) {           // 0 calm .. 2 combat
  fade("drums",   level >= 1 ? 1 : 0);
  fade("tension", level >= 2 ? 1 : 0);
}
const fade = (name, target, t = 0.8) =>
  layers[name].gain.gain.setTargetAtTime(target, ctx.currentTime, t / 3);
```

Tips: author stems at the same BPM/length and bounce them aligned. Fades of
~0.5–1.5 s feel musical; instant cuts feel mechanical. Because layers never
restart, intensity can change any time without losing sync.

## Horizontal re-sequencing

Switch segments at safe musical points so transitions don't sound abrupt.

```js
// Combine signals into 0..1, smooth it, then map to layers with hysteresis.
let intensity = 0;
function intensityFromState(enemiesNear, playerHp01) {
  const raw = Math.min(enemiesNear / 5, 1) * (1 - 0.4 * playerHp01);
  intensity += (raw - intensity) * 0.05;      // smooth so it does not flicker
  return intensity;
}

// Hysteresis: different thresholds up vs down, so the music does not oscillate
// while intensity hovers on a boundary.
function levelFromIntensity(i, current) {
  if (current < 1 && i > 0.6) return 1;
  if (current >= 1 && i < 0.4) return 0;
  return current;
}
```

Transition strategies, roughly increasing in polish:

- **Immediate crossfade** — quick volume blend; fine for low-stakes changes.
- **Quantized switch** — wait for the next beat/bar/phrase, then switch. The
  default for music that should stay "in time".
- **Transition segments** — short bridge clips written to connect A→B musically.
- **Stingers** — one-shot musical accents layered over the bed for events (boss
  appears, secret found) without altering the loop.

## Mapping gameplay to intensity

Drive the music from a small, smoothed intensity value rather than raw events:

```js
// Request a section change; apply it only at the next bar boundary.
let pendingSection = null;
const BPM = 120, BEATS_PER_BAR = 4;
const secPerBar = (60 / BPM) * BEATS_PER_BAR;

const requestSection = name => { pendingSection = name; };   // queue, never switch mid-bar

function onBarBoundary() {
  if (!pendingSection) return;
  crossfadeTo(pendingSection, 0.2);      // short crossfade across the seam
  pendingSection = null;
}
// Find the boundary from the audio clock, and schedule the switch slightly ahead:
//   const barPos = (ctx.currentTime - startedAt) % secPerBar;
//   const nextBar = ctx.currentTime + (secPerBar - barPos);
```

## Practical notes

- **Drive timing from the audio clock**, not frame delta, and account for output
  latency when scheduling.
- **Loop points** must be sample-accurate; gaps or clicks betray the seam. Author
  loops to bar boundaries and test the wrap.
- **Middleware** (FMOD, Wwise) implements layering, quantized transitions, and
  parameter-driven intensity natively — reach for it when the music system grows
  beyond a handful of stems/segments.
- **Budget**: many simultaneous stems cost voices and memory. Stream long music;
  keep stem counts modest on low-end targets.
