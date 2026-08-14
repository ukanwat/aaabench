# Feedback recipes — depth for `game-feel`

Detail the `game-feel` body defers here: the shake math, easing cheat sheet, the rest of the
feedback menu (knockback, flash, number pop, freeze), importance-tier presets, and the
per-engine bindings for tweens and particles. All snippets target **Godot 4.x** and **Unity 6**.

## 1. The trauma model (why shake feels good)

Track a single `trauma` value in `[0, 1]`. Events **add** trauma; it **decays** linearly each
frame. The actual shake amount is `trauma^2` (or `trauma^3`) so:

- small/frequent events barely nudge the screen (low trauma, squared → tiny),
- big events punch hard (high trauma, squared → near full),
- shake **always ends** on its own because trauma decays to 0.

Offset and rotation are `max_* * shake * noise(t)`. Sample a noise function or summed sines
across time — never a fresh `rand()` per frame, which produces a harsh buzz instead of a shake.

```js
// 1D value-noise-ish sampler with no dependency: layered sines at incommensurate rates.
const shakeAxis = (seed, t) =>
  0.6 * Math.sin(t * 11.0 + seed) + 0.4 * Math.sin(t * 23.0 + seed * 2.0);
// Incommensurate frequencies matter: pick rates with a simple ratio (say 10 and 20)
// and the pattern repeats visibly, which reads as a mechanism rather than an impact.
```

Tunable starting points: `max_offset = (8..16, 6..10) px`, `max_roll = 0.05..0.12 rad`,
`decay = 1.0..1.5` trauma/sec, per-hit trauma `0.15` (light) → `0.8` (heavy).

## 2. Easing cheat sheet — which curve for which job

| Goal | Ease | Godot `Tween` | Notes |
|------|------|---------------|-------|
| UI/element "pop" in | overshoot | `TRANS_BACK`, `EASE_OUT` | shoots past target, settles back |
| Bouncy, lively land | bounce/elastic | `TRANS_ELASTIC`/`TRANS_BOUNCE`, `EASE_OUT` | use sparingly; reads as cartoonish |
| Settle / decelerate | ease-out | `TRANS_CUBIC`/`TRANS_QUAD`, `EASE_OUT` | the default for "comes to rest" |
| Anticipation / wind-up | ease-in | `TRANS_CUBIC`, `EASE_IN` | slow start before a fast action |
| Smooth A→B both ends | ease-in-out | `TRANS_SINE`, `EASE_IN_OUT` | camera moves, menu slides |

Unity 6 has no built-in tween library; options in order of preference: `Vector3.SmoothDamp`
for spring-like follow, `Mathf.SmoothStep`/hand-rolled ease in a coroutine, Animator curves,
or a third-party tween package if the project already uses one. Keep the *curve choice* the
same regardless of tool.

```js
// A minimal eased scale "pop", no dependencies, driven by the frame loop.
function popScale(obj, dur = 0.18) {
  const start = { x: 1.3, y: 0.7 };
  const t0 = performance.now();
  const step = now => {
    const k = Math.min((now - t0) / (dur * 1000), 1);
    const e = 1 - (1 - k) ** 3;                      // ease-out cubic
    obj.scale.x = start.x + (1 - start.x) * e;
    obj.scale.y = start.y + (1 - start.y) * e;
    if (k < 1) requestAnimationFrame(step);
    else obj.scale.set(1, 1, 1);                     // land exactly on 1
  };
  requestAnimationFrame(step);
}
```

## 3. The rest of the feedback menu

- **Flash:** tint the sprite/material white for 1–3 frames on hit (`modulate`/material color),
  then tween back. Cheap, hugely legible.
- **Knockback:** apply an impulse away from the hit normal, clamped and short; let
  `physics-tuning` own stability. Pair with brief control lockout, not a long one.
- **Number/text pop:** spawn a damage number that rises, fades, and eases out; randomize the
  horizontal drift so stacked hits fan out.
- **Particles:** a short burst at the contact point (sparks, dust, debris). Pool them
  (`performance-optimization`) — do not instance-and-free per hit.
- **Freeze frame:** the hit-stop in the body; scale duration to importance (0.04 s light →
  0.15 s heavy). Optionally freeze only the attacker+target, not the whole world.
- **Anticipation & follow-through:** a tiny wind-up before a big action and a settle after read
  as weight; this is animation, not code (engine animation skill).
- **Chromatic/▒vignette/zoom punch:** post-process nudges for big moments; keep brief.

## 4. Importance tiers (keep the whole game proportional)

Define three presets and assign every juicy event to one. This is what stops a game from
feeling either dead (under-juiced) or exhausting (everything maxed).

| Tier | Trauma | Hit-stop | Particles | Extra | Example events |
|------|:------:|:--------:|:---------:|-------|----------------|
| small | 0.10–0.20 | none | 0–4 | tick SFX | footstep, UI hover, coin |
| medium | 0.30–0.50 | 0.04–0.06 s | 6–12 | flash | normal hit, jump-land, pickup |
| large | 0.70–1.00 | 0.10–0.15 s | 20–40 | flash + zoom + number | crit, boss hit, death, explosion |

## 5. Accessibility (ship these toggles)

- **Reduce screen shake** (scale trauma output by a 0–100% setting, default ~60–80%).
- **Reduce/disable flashing** (photosensitivity) — replace white flashes with a static tint.
- **Reduce camera motion** — cut shake roll and zoom punches.

These pair with `game-ui-ux` (settings menu) and `input-systems` (accessibility section).

## 6. Per-engine binding summary

- **Godot 4.x:** `create_tween()` + `tween_property().set_trans().set_ease()`; `GPUParticles2D/3D`
  one-shot; `Engine.time_scale` + `ignore_time_scale` timer; shake on `Camera2D.offset`.
- **Unity 6:** coroutines + `SmoothDamp`/curves (or a tween package); `ParticleSystem.Play()`;
  `Time.timeScale` + `WaitForSecondsRealtime`; shake via `CinemachineBasicMultiChannelPerlin`
  amplitude/frequency driven by `trauma^2` (see `camera-systems`).
- **Web (Phaser/Pixi/three):** tween via the engine/library tween; `this.cameras.main.shake()`
  in Phaser; `requestAnimationFrame`-driven eases elsewhere.
