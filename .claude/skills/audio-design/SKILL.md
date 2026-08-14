---
name: audio-design
description: >
  Implement game audio practice — bus/mixer architecture and gain in decibels,
  ducking (sidechain), adaptive/dynamic music via layering and re-sequencing,
  SFX variation, and beat synchronization. Engine-neutral. Use when the user
  mentions audio mixing, audio buses, adaptive/dynamic music, ducking, SFX
  variation, music layers, or syncing gameplay to the beat.
license: Apache-2.0
compatibility: Platform-neutral concepts. The concrete surface is the Web Audio API — no middleware, no engine mixer.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Audio design

Game audio is a **mixing graph plus a music system**. Route every sound through a
small set of buses so you can balance and process groups; make music *react* to
play through layering and re-sequencing rather than looping one track. This skill
teaches the portable practice; here the concrete surface is the Web Audio API —
`AudioContext`, a graph of `GainNode`s for buses, `ConvolverNode` for real-space
reverb — with no middleware and no engine mixer.

## When to use

- Use to design a bus/mixer layout, set group volumes, and apply effects (reverb,
  compression, EQ) to groups of sounds.
- Use to duck music/ambience under dialogue or impacts (sidechain).
- Use to build adaptive music that responds to combat/exploration intensity.
- Use to add SFX variation (pitch/sample randomization) and sync events to a beat.

**When *not* to use:** for the Web Audio API itself, read its documentation. Two
browser facts this practice assumes and does not teach: an `AudioContext` starts
suspended until a user gesture resumes it, and decoding is asynchronous.

## Core workflow

1. **Lay out buses, not per-sound volume.** A typical tree: `Master ← {Music,
   SFX, Ambience, UI, Voice}`. Everything plays into a bus; the player's settings
   sliders map to bus volumes. Never set hundreds of clip volumes by hand.
2. **Work in decibels, not linear.** Perceived loudness is logarithmic. Volume
   controls and automation should operate in dB; convert only at the edges.
3. **Leave headroom.** Mix so the Master peaks below 0 dBFS (aim for a target
   loudness, e.g. around -14 to -16 LUFS for many games) to avoid clipping.
4. **Duck competing sources** with a sidechain compressor (or volume automation):
   when voice/important SFX plays, the music bus dips, then recovers.
5. **Make music adaptive** via *vertical* layering (stems faded in/out) and/or
   *horizontal* re-sequencing (swap segments at musical boundaries). See the
   reference.
6. **Vary repeated SFX** with small random pitch/volume offsets and sample pools
   so footsteps and hits don't sound robotic.
7. **Verify on real output.** Listen on headphones and speakers; check that the
   mix balances, ducking is audible but not pumping, and music transitions land
   on the beat — never assume from the editor meters alone.

## Patterns

### 1. Bus routing and dB gain

```js
// Route sounds through named bus nodes; control GROUPS, not individual clips.
const ctx = new AudioContext();
const buses = {
  master: ctx.createGain(),
  sfx:    ctx.createGain(),
  music:  ctx.createGain(),
  voice:  ctx.createGain(),
};
buses.master.connect(ctx.destination);
for (const k of ["sfx", "music", "voice"]) buses[k].connect(buses.master);

// Web Audio gain is LINEAR amplitude, but loudness is perceived logarithmically,
// so a slider must not drive gain directly — reason in decibels and convert.
const dbToGain = db => 10 ** (db / 20);            // -6 dB ~ half amplitude
function setBusVolume(bus, slider01) {
  const db = slider01 <= 0.0001 ? -80 : 20 * Math.log10(slider01);
  // setTargetAtTime, not .value = — an instant gain jump is an audible click.
  buses[bus].gain.setTargetAtTime(dbToGain(db), ctx.currentTime, 0.02);
}
// RIGHT: slider -> dB -> linear gain, ramped. WRONG: gain.value = slider01
// (0.5 sounds far louder than "half"), or any instant assignment (clicks).
```

### 2. Ducking via sidechain (music dips under voice)

```js
// Randomize pitch slightly and pick from a sample pool so repeats feel organic.
function playVaried(buffers, bus = "sfx") {
  const src = ctx.createBufferSource();
  src.buffer = buffers[(Math.random() * buffers.length) | 0];  // rotate several takes
  src.detune.value = (Math.random() * 120) - 60;               // +/- 60 cents
  src.connect(buses[bus]);
  src.start();
  // An AudioBufferSourceNode is single-use: it cannot be started twice. Create one
  // per shot and let it be collected — but reuse the decoded AudioBuffer forever.
}
```

### 3. SFX variation (kill the "machine gun" repeat)

```js
// Lower music while dialogue plays, then release. This is "sidechain ducking".
//
// A browser fact worth knowing before you design around it: Web Audio's
// DynamicsCompressorNode has NO sidechain input. There is no way to key a
// compressor on the voice bus. You duck by scheduling gain yourself.
const DUCK_DB = -12, ATTACK = 0.08, RELEASE = 0.4;
function duckMusic(active) {
  const g = buses.music.gain, now = ctx.currentTime;
  g.cancelScheduledValues(now);
  g.setTargetAtTime(dbToGain(active ? DUCK_DB : 0), now, active ? ATTACK : RELEASE);
}
// Fast attack so music gets out of the way promptly; slow release so it recovers
// smoothly rather than pumping. Drive it from the voice source's start/ended events.
```

### 4. Beat-synced events (quantize to the music grid)

```js
// Schedule on the AUDIO clock, not frame time, so events land on the beat.
// ctx.currentTime advances in the audio thread and does not drift with frame rate;
// requestAnimationFrame deltas do, and will slide audibly within a few bars.
const BPM = 120;
const secondsPerBeat = 60 / BPM;

const currentBeat = playbackPos => Math.floor(playbackPos / secondsPerBeat);
const timeUntilNextBeat = pos => secondsPerBeat - (pos % secondsPerBeat);

// Schedule ahead rather than firing on the frame you notice the beat:
//   src.start(ctx.currentTime + timeUntilNextBeat(pos))
// Anything started "now" from a rAF callback is already up to a frame late.
```

## Pitfalls

- **Treating slider values as dB.** Volume is logarithmic; map `0..1` through
  `linear_to_db` (and back with `db_to_linear`). A linear slider on raw amplitude
  feels like it does nothing until the very bottom.
- **Per-clip volume instead of buses** makes a global balance pass impossible and
  bloats save/settings. Mix on buses.
- **Clipping the master.** Summed sounds exceed 0 dBFS and distort. Leave
  headroom; put a limiter on Master as a safety net, not as the mixer.
- **Pumping ducking**: too-fast release or too-high ratio makes music audibly
  breathe. Lengthen release; lower ratio.
- **Looping a single music track** for the whole game feels flat. Use layers or
  segments that respond to state (see the reference).
- **Beat sync off frame time.** `delta` drifts; read the **audio playback
  position** for musical timing, and account for output latency.
- **Unbounded one-shot players**: spawning AudioStreamPlayers without freeing
  them leaks. Free on `finished`, or use a small pool.

## References

- `references/adaptive-music.md` — vertical layering vs horizontal re-sequencing,
  transition timing (bars/quantize), stingers, intensity mapping, and crossfades.

## Related skills

- `input-systems` — trigger audio from input actions.
- `physics-tuning` — collision events that drive impact SFX.