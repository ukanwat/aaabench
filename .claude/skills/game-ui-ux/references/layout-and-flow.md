# Layout, scaling & flow — depth for `game-ui-ux`

Detail the `game-ui-ux` body defers here: canvas and UI scaling, safe-area handling, a complete
focus and screen-stack pattern, diegetic UI, accessibility, and localization-ready layout.

## 1. Scaling: three sizes, not one

A canvas has a *CSS size* (layout pixels) and a *backing-store size* (real pixels), and confusing
them is the most common scaling bug there is:

```js
const dpr = Math.min(devicePixelRatio, 2);        // a decision — 3 is 9x the pixels of 1
canvas.style.width = `${cssW}px`;                  // what the page lays out
canvas.style.height = `${cssH}px`;
canvas.width  = Math.round(cssW * dpr);            // what the GPU actually fills
canvas.height = Math.round(cssH * dpr);
renderer.setPixelRatio(dpr);                       // must agree with the above
```

Reapply on every resize, and note that a mobile browser resizes constantly as its chrome slides in
and out. `100vh` includes that chrome and will not match what you can see; `100dvh` follows it, and
the `visualViewport` API tells you what is actually visible.

UI itself should scale by *relative* units — `rem`, `%`, `clamp()`, `vmin` — rather than a global
multiplier applied to a fixed design size. There is no reference-resolution setting to configure,
which is a loss and a freedom at once: nothing scales your HUD for you, but nothing forces one
design size on you either.

## 2. Safe-area math

The OS reports a safe rectangle inside the screen (excludes notch, rounded corners, and — on TVs
— overscan margins). Inset only **critical** UI (health, timers, prompts); decorative art can
bleed to the edge.

```text
# Normalized anchors from a pixel safe rect (engine-neutral):
anchorMin = (safe.x / screenW,                 safe.y / screenH)
anchorMax = ((safe.x + safe.w) / screenW,       (safe.y + safe.h) / screenH)
# Re-apply on resolution change / orientation change, not once at startup.
```

- **Browser:** `env(safe-area-inset-top/right/bottom/left)` in CSS — but they are all zero unless
  the viewport meta carries `viewport-fit=cover`, which is the half everyone forgets. CSS reapplies
  them on rotation and resize for free, so there is nothing to recompute.

## 3. Focus navigation (full pattern)

Requirements for controller/keyboard usability:

1. **Initial focus** on every screen open — call `.focus()` on something, or the gamepad appears
   dead with no clue why.
2. **Predictable movement.** Tab order comes from DOM order for free; a gamepad gets nothing free,
   so map the stick to your own ordering and call `.focus()` yourself.
3. **Visible focus style** distinct from hover. Style `:focus-visible`, never remove the outline
   without replacing it, and never rely on colour alone (see accessibility).
4. **Wrap or stop** intentionally at list ends; trap focus inside modal dialogs.
5. **Device coexistence:** moving the mouse can update selection; a gamepad press acts on the
   focused control. Don't clear focus when the mouse moves.

```js
// Trap focus inside a modal so Tab and the stick cannot escape to the game behind it.
let prevFocus = null;
function openModal(modal) {
  prevFocus = document.activeElement;
  document.getElementById("game-ui").inert = true;   // whole subtree unfocusable
  modal.hidden = false;
  modal.querySelector("[data-default-focus]")?.focus();
}
function closeModal(modal) {
  modal.hidden = true;
  document.getElementById("game-ui").inert = false;
  prevFocus?.focus();                                 // restore where they were
}
// `inert` does the job that a manual focus trap used to: it removes a subtree from
// the tab order and from hit-testing at once, so there is no keydown handler to get
// subtly wrong.
```

## 4. Screen/menu stack

Model screens as a stack of UI states; the top owns input and is visible. Push for overlays,
pop for "back". This generalizes pause, settings-over-pause, and confirm dialogs.

```js
// A screen stack: one visible screen, the rest inert underneath.
const stack = [];
function push(screen) {
  if (stack.length) stack.at(-1).inert = true;
  stack.push(screen);
  document.body.append(screen);
  screen.querySelector("[data-default-focus]")?.focus();
}
function pop() {
  stack.pop()?.remove();
  const top = stack.at(-1);
  if (top) { top.inert = false; top.querySelector("[data-default-focus]")?.focus(); }
}
// Pausing is yours: set a paused flag the loop reads. Do NOT stop the render loop —
// a paused game that stops rendering also stops resizing, stops repainting on focus,
// and comes back to a stale frame.
```

This mirrors the state-stack idea in `love2d-core`'s `references/state-stack.md`, applied to UI.

## 5. Diegetic vs non-diegetic UI

- **Non-diegetic:** drawn on the screen plane, outside the fiction (most HUDs). Cheapest, clearest.
- **Diegetic:** UI that exists in the world (ammo counter on the gun, health on the suit). More
  immersive, more work, can hurt readability. Use for key elements, keep a non-diegetic fallback.
- **Spatial/world-space:** floating health bars, damage numbers — anchor to world position,
  clamp to screen edges when off-screen, and scale with distance (3D).

## 6. Accessibility (bake in, don't bolt on)

- **Text size option** and never hardcode tiny fonts; size to a percentage of reference height.
- **Contrast & color independence:** don't encode state in color alone — add icon/shape/text.
  Provide colorblind-safe palettes.
- **Scalable hit targets** for touch (≥ ~9 mm); padding around small buttons.
- **Reduce-motion / reduce-flashing** toggles (coordinate with `game-feel`).
- **Full keyboard + gamepad** reachability (section 3); don't gate actions behind mouse-only.

## 7. Localization-ready layout

- Externalize strings into per-locale files loaded at runtime; never bake display text into layout
  logic. `Intl.NumberFormat` / `Intl.DateTimeFormat` / `Intl.RelativeTimeFormat` handle numbers,
  dates and plurals correctly per locale and are already in the browser.
- Let containers **size to content** so longer translations (German is ~30% longer) don't clip.
  Avoid fixed-width buttons sized to English.
- Leave room for RTL mirroring and different number/date formats.
- Keep icons separate from text so only strings need translating.
