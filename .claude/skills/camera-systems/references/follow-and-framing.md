# Follow & framing — depth for `camera-systems`

Detail the `camera-systems` body defers here: the smoothing math, a full 2D rig, 3D orbit/first-
person specifics, multi-target framing, cinematic blends, and the per-engine rig mapping.
There is no camera rig package here; every mechanism below is one you write.

## 1. Why `1 - exp(-rate*dt)` (frame-rate-independent smoothing)

A naive `pos = lerp(pos, target, k)` applies `k` *per frame*, so at 144 FPS it smooths far more
per second than at 30 FPS — the feel changes with hardware. Exponential smoothing fixes the rate
*per second*:

```text
t = 1 - exp(-rate * dt)      # rate ≈ 5 (floaty) .. 12 (snappy)
pos = lerp(pos, target, t)   # identical convergence at any frame rate
```

A critically-damped spring — the model behind `SmoothDamp`-style helpers, and about ten lines
gives the same frame-rate independence plus velocity continuity (no overshoot). Prefer the
engine's built-in spring/smoothing before hand-rolling.

## 2. Full 2D rig: deadzone + look-ahead + bounds

Order of operations each frame, after the target moves:

1. Compute target overflow beyond the **deadzone** (box or circle) → move the focus by the
   overflow only.
2. Add **look-ahead**: `focus += dir_of_motion * lookAheadDist`, but **ease the look-ahead offset
   itself** toward its goal so a direction flip doesn't snap the view.
3. **Smooth** the camera toward the focus (section 1).
4. **Clamp** so the *visible rectangle* stays in bounds: clamp camera center to
   `[min + halfView, max - halfView]` per axis (clamp the view, not the center).

```js
// Clamp the VIEW, not the focus point, accounting for zoom and viewport size.
function clampToLevel(center) {
  const halfW = (canvas.width  * 0.5) / zoom;
  const halfH = (canvas.height * 0.5) / zoom;
  return {
    x: Math.min(Math.max(center.x, level.minX + halfW), level.maxX - halfW),
    y: Math.min(Math.max(center.y, level.minY + halfH), level.maxY - halfH),
  };
}
// If the level is smaller than the view on an axis, centre on that axis instead of
// clamping — otherwise min > max and the camera snaps to a corner.
// In a browser the viewport changes size whenever the window does, so recompute on
// resize rather than caching half-extents at startup.
```

Tunables: deadzone `32–64 px`, look-ahead `40–120 px` eased over `0.2–0.4 s`, smoothing
`rate 6–10`.

## 3. 3D third-person orbit

- **Rig:** an invisible pivot at the character's shoulder/head height; yaw on the pivot, pitch on
  a child; the camera sits at `-springLength` on local Z.
- **Collision:** there is no spring arm. Cast a ray from the pivot to the desired camera position
  every frame and shorten to the first hit (minus a small skin) so the camera never clips through
  walls. Without it, the camera goes inside geometry the first time the player backs into a wall.
- **Pitch clamp:** ~`[-80°, +45°]` so the camera can't flip or bury into the floor.
- **Sensitivity & invert:** expose look sensitivity and invert-Y (see `input-systems`).
- **Recovery:** when the ray shortens and then clears, ease the boom back out rather than snapping.
  An instantly-restored camera reads as a glitch even though it is geometrically correct.

## 4. First-person look

- Yaw rotates the body (so movement aligns with view); pitch rotates only the camera head.
- Clamp pitch; never let roll accumulate.
- Mouse: use relative motion (`movementX/Y`) and Pointer Lock. Lock requires a user gesture and
  can be dropped at any time by Esc — handle losing it without stranding the player.
- Stick: apply a response curve + deadzone (see `input-systems`) and frame-rate-scaled turn rate.

## 5. Multi-target / group framing

- Compute the bounding box of all targets; place the camera at the box center.
- **2D:** set zoom so the box (plus padding) fits the viewport; clamp zoom min/max.
- **3D:** dolly the camera back or widen the FOV to fit the box. Prefer dollying: changing FOV
  changes the perspective and reads as the world distorting rather than the camera moving.
- **Split-screen:** one camera per player rendering to a viewport rectangle; budget the extra
  render cost (`performance-optimization`).

## 6. Cinematic blends & transitions

- Blend between gameplay and cutscene cameras over a short time (ease-in-out). Nothing blends for
  you: interpolate position and orientation between two rigs and swap which one drives the camera
  at the end. Interpolate rotation as quaternions, not as euler angles, or the camera takes the
  scenic route through a gimbal.
- Reset smoothing state on hard cuts/teleports so the camera doesn't slingshot across the map.

## 7. The pieces, and the order they run in

One update per frame, in this order, or they fight each other:

1. target moves (physics/controller has already stepped)
2. focus point updates — deadzone, then exponential smoothing or a spring
3. clamp the focus to level bounds, accounting for viewport size and zoom
4. resolve occlusion — ray from pivot toward the desired camera position
5. add the shake offset from `game-feel`, last, so smoothing never chases it
6. write to the camera, once

Anything writing to the camera outside step 6 is the cause of jitter nobody can find.
