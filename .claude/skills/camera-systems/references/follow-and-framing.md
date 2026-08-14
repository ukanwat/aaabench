# Follow & framing — depth for `camera-systems`

Detail the `camera-systems` body defers here: the smoothing math, a full 2D rig, 3D orbit/first-
person specifics, multi-target framing, cinematic blends, and the per-engine rig mapping.
Snippets target **Godot 4.x** and **Unity 6 / Cinemachine 3**.

## 1. Why `1 - exp(-rate*dt)` (frame-rate-independent smoothing)

A naive `pos = lerp(pos, target, k)` applies `k` *per frame*, so at 144 FPS it smooths far more
per second than at 30 FPS — the feel changes with hardware. Exponential smoothing fixes the rate
*per second*:

```text
t = 1 - exp(-rate * dt)      # rate ≈ 5 (floaty) .. 12 (snappy)
pos = lerp(pos, target, t)   # identical convergence at any frame rate
```

A critically-damped spring (Unity `Vector3.SmoothDamp`, or a hand-rolled spring with `smoothTime`)
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
- **Collision:** a spring arm (Godot `SpringArm3D`) or occlusion ray casts from pivot to desired
  camera position and shortens to the first hit so the camera never clips through walls.
- **Pitch clamp:** ~`[-80°, +45°]` so the camera can't flip or bury into the floor.
- **Sensitivity & invert:** expose look sensitivity and invert-Y (see `input-systems`).
- **Cinemachine 3 (Unity 6):** a `CinemachineCamera` (namespace `Unity.Cinemachine`) with an
  **Orbital Follow** component and a **Cinemachine Deoccluder** (collision); the
  `CinemachineBrain` on the `Camera` blends between cameras. This replaces the v2
  `CinemachineVirtualCamera` / `CinemachineCollider` names.

## 4. First-person look

- Yaw rotates the body (so movement aligns with view); pitch rotates only the camera head.
- Clamp pitch; never let roll accumulate.
- Mouse: use relative motion + capture the cursor (`Input.mouse_mode = MOUSE_MODE_CAPTURED`).
- Stick: apply a response curve + deadzone (see `input-systems`) and frame-rate-scaled turn rate.

## 5. Multi-target / group framing

- Compute the bounding box of all targets; place the camera at the box center.
- **2D:** set zoom so the box (plus padding) fits the viewport; clamp zoom min/max.
- **3D:** dolly the camera back / adjust FOV to fit the box; Cinemachine has a Group Framing /
  Target Group component for this.
- **Split-screen:** one camera per player rendering to a viewport rectangle; budget the extra
  render cost (`performance-optimization`).

## 6. Cinematic blends & transitions

- Blend between gameplay and cutscene cameras over a short time (ease-in-out). Cinemachine blends
  automatically when you change the active camera's priority; in Godot, tween a rig between marker
  transforms or swap `current` cameras with a fade.
- Reset smoothing state on hard cuts/teleports so the camera doesn't slingshot across the map.

## 7. Per-engine rig summary

| Need | Godot 4.x | Unity 6 |
|------|-----------|---------|
| 2D follow + smoothing + limits | `Camera2D` (`position_smoothing_*`, `limit_*`, `drag_*`) | Cinemachine `CinemachineCamera` (2D) + Confiner2D |
| 3D follow/orbit | pivot + `SpringArm3D` + `Camera3D` | `CinemachineCamera` + Orbital Follow + Deoccluder |
| Shake | additive `offset` from `game-feel` | `CinemachineBasicMultiChannelPerlin` |
| Bounds | `limit_*` / manual clamp | `CinemachineConfiner2D/3D` |
| Addon option | `PhantomCamera` (declarative 2D/3D rigs) | built-in Cinemachine |
