---
name: camera-systems
description: >
  Build game cameras that feel good — 2D follow with a deadzone, look-ahead, smoothing, and
  level-bounds clamping; 3D third-person orbit with collision and first-person look; plus
  multi-target framing and a shake hook. Engine-neutral techniques that pair with the engine's
  camera rig, built from scratch — there is no camera node and no rig package. Use when the user
  mentions camera follow, follow camera, deadzone, look-ahead, camera smoothing, camera bounds/
  limits, third-person camera, orbit camera, first-person look, or camera jitter.
license: Apache-2.0
compatibility: Platform-neutral camera techniques. There is no camera component to configure — the rig is yours. Pairs with game-feel.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Camera systems

The camera is the player's window; bad camera work makes a good game feel awful. This skill
covers the engine-neutral camera techniques — smooth follow, deadzones, look-ahead, bounds
clamping, third-person orbit with collision, first-person look, and multi-target framing — and
maps them onto each engine's camera node or rig.

## When to use

- Use when a 2D camera should follow the player smoothly, stay inside the level, lead the
  player's motion, or ignore small movements (deadzone).
- Use when building a 3D third-person orbit camera (mouse/stick look, collision push-in) or a
  first-person look controller, or framing multiple targets at once.
- Use to fix camera jitter, snapping, motion sickness, or a camera that shows past the level edge.

**When *not* to use:** for the *magnitude and trigger* of screen shake and impact juice, use
`game-feel` (this skill exposes the shake offset hook it drives). For the engine's concrete
camera object, read the renderer's own documentation. For player movement itself — there is no
movement skill and no character controller here; that is yours to write. For
performance of many cameras/render targets, see `performance-optimization`.

## Core workflow

1. **Decide what the camera serves.** Platformer (lead the jump, see hazards), top-down (center
   with deadzone), third-person (orbit + collision), first-person (look only). The genre sets the
   rules.
2. **Follow smoothly and frame-rate independently.** Move the camera toward the target with
   exponential smoothing or a spring (`SmoothDamp`), not a fixed `lerp(a, b, 0.1)` — that 0.1 is
   per-frame and changes with frame rate.
3. **Add a deadzone** so tiny target movements don't nudge the camera; it only follows once the
   target leaves a box/zone. Stops nausea in twitchy games.
4. **Lead the action with look-ahead** by offsetting the camera target in the direction of
   motion or facing, eased in/out so it doesn't whip.
5. **Clamp to level bounds** so the camera never shows outside the playable area; combine with
   smoothing so it eases to a stop at the edge.
6. **For 3D, separate look from collision.** Orbit via yaw/pitch on a rig; use a spring arm /
   ray to pull the camera in when geometry blocks it; clamp pitch.
7. **Update the camera after the target moves.** Follow in the late/post step (after movement and
   physics resolve) to avoid a one-frame lag jitter.
8. **Verify by moving the target at low and high frame rates**, into corners and walls, and at
   the level edges; confirm no jitter, no peeking past bounds, smooth stops. Report what you saw.

## Patterns

### 1. Follow: smoothing + bounds (you are hand-rolling this, so get it right once)

```js
// There is no camera node to configure here — no built-in smoothing, no limit
// rectangle, no drag margins. The rig is an object you own, and every property an
// engine would have exposed is a line you write. That is the whole difference.
const rig = {
  focus:  { x: 0, y: 0 },   // where the camera is looking, after smoothing
  rate:   6.0,              // higher = snappier, lower = floatier
  bounds: { minX: 0, minY: 0, maxX: levelWidth, maxY: levelHeight },
};
// Update it in ONE place, after the target has moved for the frame, and write the
// result to the camera object last. Two systems both nudging the camera in the same
// frame is the most common source of jitter nobody can find.
```

### 2. Frame-rate-independent smooth follow (when you hand-roll it)

```js
// RIGHT: exponential smoothing — same feel at any frame rate. `rate` ~ 5..12.
function follow(dt) {
  const t = 1 - Math.exp(-rig.rate * dt);   // converges correctly regardless of dt
  rig.focus.x += (target.x - rig.focus.x) * t;
  rig.focus.y += (target.y - rig.focus.y) * t;
}
// WRONG: focus.x += (target.x - focus.x) * 0.1
//        -> smooths faster at higher frame rates; a different feel on every machine,
//        and the bug is invisible on the machine you develop on.
```

### 3. Deadzone + look-ahead (lead the player, ignore jitter)

```js
// The camera only chases once the target leaves a deadzone box, then aims AHEAD.
function cameraTarget(dt) {
  const toX = target.x - rig.focus.x, toY = target.y - rig.focus.y;
  const dz = { x: 48, y: 32 };                       // deadzone half-extents
  // Move the focus only by the overflow beyond the deadzone, per axis.
  rig.focus.x += Math.max(Math.abs(toX) - dz.x, 0) * Math.sign(toX);
  rig.focus.y += Math.max(Math.abs(toY) - dz.y, 0) * Math.sign(toY);
  const speed = Math.hypot(target.vx, target.vy) || 1;
  return {                                            // aim ahead of travel
    x: rig.focus.x + (target.vx / speed) * lookAheadDist,
    y: rig.focus.y + (target.vy / speed) * lookAheadDist,
  };
}
```

### 4. 3D third-person orbit with collision push-in

```js
// Third-person orbit: yaw/pitch a pivot, then pull the camera in when blocked.
// Mouse-look needs Pointer Lock, and Pointer Lock needs a user gesture — request it
// from a click handler, and handle the lock being lost (Esc) without breaking input.
function onMouseMove(e) {
  if (document.pointerLockElement !== canvas) return;
  yaw   -= e.movementX * sensitivity;
  pitch  = Math.max(-1.2, Math.min(0.4, pitch - e.movementY * sensitivity));  // clamp!
}

// There is no spring arm. Occlusion is a ray you cast yourself, every frame, from
// the pivot toward the desired camera position; if it hits world geometry, place the
// camera at the hit minus a small skin. Without it the camera clips through walls,
// which reads as broken instantly.
function resolveBoom(pivot, desired) {
  const hit = raycast(pivot, desired);            // yours to implement
  return hit ? lerpTo(pivot, desired, hit.t - 0.05) : desired;
}
```

### 5. Screen shake hook (owned trigger lives in `game-feel`)

```js
// Expose an additive offset the game-feel trauma model writes to, so follow and
// shake compose instead of fighting. Shake rides ON TOP of smooth follow.
let shakeOffset = { x: 0, y: 0 };                // set each frame by game-feel (trauma^2 * noise)
function applyToCamera(finalFocus) {
  camera.position.x = finalFocus.x + shakeOffset.x;
  camera.position.y = finalFocus.y + shakeOffset.y;
}
// Never fold shake into `focus` itself — the smoothing will then chase the shake and
// the camera drifts toward wherever it last rattled.
```

## Pitfalls

- **`lerp(pos, target, const)` per frame** is frame-rate dependent — floatier at 30 FPS, snappier
  at 144. Use `1 - exp(-rate*dt)` or `SmoothDamp`.
- **Following in the normal update before the target has moved** yields a one-frame lag jitter.
  Follow in `LateUpdate` / after movement/physics resolve.
- **No bounds clamp** lets the camera show black past the level edge. Clamp focus to the level
  rect (account for the viewport half-size so the *view*, not the center, stays inside).
- **No deadzone in twitchy games** makes the camera twitch with every micro-movement → nausea.
- **Unclamped pitch** in third/first-person flips the camera over the top. Clamp pitch to ~±80°.
- **Camera clipping through walls** in 3D — use a spring arm / occlusion ray to pull in.
- **Snapping on teleport/respawn** is jarring; either hard-cut intentionally (and reset
  smoothing) or fast-ease. Don't let a huge `SmoothDamp` distance whip across the level.
- **Shake driving the follow target** instead of an additive offset makes follow fight shake.
  Compose: smooth follow first, add shake offset last.
- **Per-axis vs radial deadzone confusion** — a box deadzone feels different from a circular one;
  pick deliberately.

## References

- For the exponential-smoothing/spring derivation, a complete deadzone+look-ahead+bounds 2D rig,
  3D spring-arm/orbit details, first-person look, multi-target/group framing and split-screen,
  cinematic camera blends, and the order the pieces must run in each frame, read
  `references/follow-and-framing.md`.

## Related skills

- `game-feel` — owns screen-shake trauma/triggers; this skill exposes the offset it writes.
- `physics-tuning` — interpolate camera follow with the physics step to kill jitter.
- `performance-optimization` — cost of extra cameras, render targets, and split-screen.