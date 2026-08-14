---
name: game-feel
description: >
  Add "juice" and game feel that makes actions satisfying — screen shake, hit-stop/freeze
  frames, tweened/eased motion, squash & stretch, knockback, and layered audio-visual
  feedback — as engine-neutral techniques that pair with the detected engine's tween,
  particle, and camera APIs. Use when the user mentions game feel, juice, "make it feel
  good/punchy", screen shake, hit stop, screen freeze, easing, squash and stretch, impact
  frames, or feedback/polish on hits, jumps, pickups, and deaths.
license: Apache-2.0
compatibility: Platform-neutral techniques. Easing and particles are code here, not engine nodes. Pairs with camera-systems and audio-design.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Game feel (juice)

The difference between a mechanic that *works* and one that feels *good* is feedback: the
layered, slightly-exaggerated response an action provokes. This skill covers the engine-
neutral techniques — screen shake, hit-stop, easing, squash & stretch, knockback, and stacked
feedback — and tells you how to apply them without burying the underlying simulation. It
**adds polish on top of** an existing mechanic; it does not implement the mechanic.

## When to use

- Use when an action (hit, jump, dash, pickup, death, button press) is mechanically correct
  but feels weak, weightless, or unsatisfying, and you want it to feel responsive and punchy.
- Use to add screen shake, hit-stop/freeze frames, eased motion, squash & stretch, knockback,
  flashes, or to layer multiple feedback channels onto one event.
- Use to decide *how much* juice is enough and where it crosses into noise.

**When *not* to use:** for the raw controller math (jump height, coyote time) use the
`platformer` genre and the engine movement skill. For camera *follow/deadzone/orbit* framing
use `camera-systems` (this skill only triggers the shake). For mixing, ducking, and adaptive
music use `audio-design`. For shader-based dissolves/flashes use `shader-programming`. There is
no tween node and no particle component here: easing is a function you write, and particles are
instanced geometry or a shader.

## Core principle: feedback is layered and exaggerated

One satisfying hit is usually **5–8 tiny responses firing together** within ~100 ms: a sound,
a particle burst, a brief hit-stop, a flash, a knockback, a small screen shake, and a number
popping up. Each is cheap; stacked, they read as "impact". Two rules keep it from becoming a
mess: **(1)** exaggerate *briefly* and return to rest (juice is transient, not a new resting
state); **(2)** scale juice to event importance — a footstep is not a boss death.

## Core workflow

1. **Confirm the event hooks exist.** Juice attaches to discrete events: `on_hit`, `on_land`,
   `on_pickup`, `on_death`, `on_fire`. If the mechanic doesn't emit these, add them first.
2. **Pick feedback channels per event** from the menu (sound, particles, shake, hit-stop,
   flash, knockback, tween, number pop). Start with 2–3; add until it reads, then stop.
3. **Make motion eased, not linear.** Route scale/position/UI changes through a tween with an
   ease (overshoot for "pop", ease-out for "settle"). Linear motion feels robotic.
4. **Reserve hit-stop and shake for impact.** They are the strongest, most abusable tools —
   short durations, scaled to importance, and never on routine actions.
5. **Keep feedback off the critical simulation.** Shake moves the *camera/visual*, not the
   body; hit-stop uses time scale or a real-time pause, not a gameplay-logic stall.
6. **Tune by importance tiers.** Define small/medium/large feedback presets and assign events
   to a tier, so the whole game's juice stays consistent and proportional.
7. **Verify by playing and watching.** Trigger the event repeatedly; confirm the feedback
   fires, returns to rest, and is not nauseating or input-blocking. Report what you observed
   (does shake decay? does input still register during hit-stop?).

## Patterns

### 1. Screen shake by decaying "trauma" (smooth, not a random jitter)

```js
// Store trauma 0..1; shake = trauma^2 so small hits barely move and big hits punch.
// Drives a camera OFFSET (the visual), never the player body. Decays every frame.
const shake = { trauma: 0, decay: 1.2, maxOffset: { x: 12, y: 8 }, maxRoll: 0.1, t: 0 };

const addTrauma = a => { shake.trauma = Math.min(1, shake.trauma + a); };  // hits ADD

function updateShake(dt) {
  if (shake.trauma <= 0) return { x: 0, y: 0, roll: 0 };
  shake.trauma = Math.max(0, shake.trauma - shake.decay * dt);
  const s = shake.trauma * shake.trauma;        // quadratic: gentle low, sharp high
  shake.t += dt * 30;
  // Smooth pseudo-random via sampled sines, NOT Math.random() per frame (that buzzes).
  return {
    x: shake.maxOffset.x * s * Math.sin(shake.t * 1.7),
    y: shake.maxOffset.y * s * Math.sin(shake.t * 2.3),
    roll: shake.maxRoll * s * Math.sin(shake.t * 1.1),
  };
}
```

### 2. Hit-stop / freeze frame (sell impact by briefly stopping time)

```js
// Hit-stop: freeze the world briefly on impact, then resume.
// There is no Engine.time_scale here. You own the clock, which is simpler and also
// means nothing scales for free: every system that reads dt must read YOUR dt.
let timeScale = 1;
function hitStop(duration = 0.08, scale = 0.05) {
  timeScale = scale;
  const until = performance.now() + duration * 1000;   // REAL time, not scaled time
  const restore = () => { if (performance.now() >= until) timeScale = 1;
                          else requestAnimationFrame(restore); };
  requestAnimationFrame(restore);
}
// In the loop: const dt = rawDt * timeScale.
// RIGHT: measure the freeze in real time. WRONG: counting down a timer that is
// itself scaled — at scale 0.05 it takes twenty times as long to expire, and at
// scale 0 it never does.
```

```js
// Two browser specifics that will bite a feel pass, neither of them obvious:
//
// 1. requestAnimationFrame STOPS in a background tab. Come back after a minute and
//    your first dt is enormous. Clamp it — `dt = Math.min(rawDt, 1/30)` — or the
//    player teleports through a wall on tab focus.
// 2. setTimeout is not a gameplay clock. It is throttled in background tabs, has a
//    ~4 ms floor, and drifts. Anything that must land on a frame belongs in the loop.
let last = performance.now();
function frame(now) {
  const rawDt = (now - last) / 1000; last = now;
  const dt = Math.min(rawDt, 1 / 30) * timeScale;   // clamp, THEN scale
  update(dt); render();
  requestAnimationFrame(frame);
}
```

### 3. Squash & stretch + overshoot via an eased tween (the "pop")

```js
// Conserve volume: stretch one axis, squash the other, then spring back with overshoot.
const easeOutBack = k => { const c = 1.70158; return 1 + (c + 1) * (--k) ** 3 + c * k ** 2; };

function pop(obj, dur = 0.18) {
  obj.scale.set(1.3, 0.7, 1);                       // instant squash on the event
  const t0 = performance.now();
  const step = now => {
    const k = Math.min((now - t0) / (dur * 1000), 1);
    const e = easeOutBack(k);                       // overshoots past 1, then settles
    obj.scale.set(1.3 + (1 - 1.3) * e, 0.7 + (1 - 0.7) * e, 1);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}
// RIGHT: an easing curve with overshoot (back/elastic) reads alive.
// WRONG: a linear interpolation back to 1 — mechanical, and worse than no pop.
```

### 4. A feedback bundle scaled by importance (keep juice proportional)

```js
// One call per event; the tier decides intensity so the whole game stays consistent.
function feedback(pos, tier) {
  switch (tier) {
    case "small":
      playSfx("tick");  addTrauma(0.15); break;
    case "medium":
      playSfx("hit");   addTrauma(0.40); hitStop(0.05); spawnParticles(pos, 6); break;
    case "large":
      playSfx("boom");  addTrauma(0.80); hitStop(0.12); spawnParticles(pos, 30);
      flashWhite(0.06); break;
  }
}
// Three tiers, applied everywhere, beat per-event tuning: the game reads as one
// object rather than as a collection of separately-tuned moments.
```

## Pitfalls

- **Shaking the player/body instead of the camera offset** desyncs collision and aim. Shake
  the camera (or a visual pivot), never the simulated transform.
- **Random offset every frame** buzzes like static. Drive shake from sampled noise/sin and a
  decaying trauma value so it's smooth and self-ending.
- **Hit-stop counted in scaled time** never resumes — at time scale 0 a timer that is itself
  scaled never advances. Measure the freeze against `performance.now()`, which is real time.
- **Hit-stop on every frame of a held attack** locks the game. Trigger it once per impact.
- **Linear tweens everywhere** feel robotic. Ease almost everything; reserve overshoot
  (BACK/ELASTIC) for "pop" and ease-out for "settle".
- **Permanent exaggeration** (scale never returns, shake never decays) becomes the new normal
  and stops reading as feedback. Juice must return to rest.
- **Over-juicing routine actions** (full shake + hit-stop on every footstep) causes nausea and
  hides real impacts. Scale to importance; add a "reduce screen shake"/"reduce flashing"
  accessibility option.
- **Feedback that blocks input** (long freeze, un-cancelable animation) hurts responsiveness.
  Keep juice short and let input buffer through it.

## References

- For the trauma-shake math, easing-curve cheat sheet (which ease for pop vs settle), knockback
  + flash + number-pop recipes, importance-tier presets, and per-engine tween/particle bindings,
  read `references/feedback-recipes.md`.

## Related skills

- `camera-systems` — owns camera follow/deadzone/orbit; this skill only feeds it shake trauma.
- `audio-design` — the sound layer of every feedback bundle; ducking and SFX variation.
- `physics-tuning` — knockback forces and the timestep juice must not destabilize.