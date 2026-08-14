---
name: game-ui-ux
description: >
  Design and build game UI/UX — HUDs, menus, and overlays — that survive every screen: anchor-
  based responsive layout, resolution/aspect scaling and safe areas, keyboard/gamepad focus
  navigation, a screen/menu state stack, and event-driven (not polled) HUD updates. Engine-
  neutral patterns that pair with the detected engine's UI skill. Use when the user mentions
  HUD, health bar, main menu, pause menu, settings screen, UI layout, anchors, UI scaling,
  aspect ratio, safe area, controller/keyboard menu navigation, or wiring UI to game state.
license: Apache-2.0
compatibility: Platform-neutral UI/UX patterns. Here UI is DOM, a 2D context, or geometry in the scene. Pairs with game-feel.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Game UI/UX

Build HUDs and menus that stay correct on a phone, an ultrawide monitor, and a TV across a
gamepad and a mouse. This skill owns the engine-neutral UI architecture — responsive layout,
scaling, focus navigation, screen flow, and how UI talks to game state — and defers the
concrete widget API to the engine UI skill.

## When to use

- Use when building a HUD (health/ammo/score), a menu (main/pause/settings), an inventory or
  shop screen, or any overlay, and you want it to scale and navigate correctly.
- Use to fix UI that breaks at other resolutions/aspect ratios, ignores notches/safe areas,
  can't be used with a controller, or is wired to game state by per-frame polling.
- Use to structure screen flow (title → game → pause → settings) as a stack, not flag soup.

**When *not* to use:** as a substitute for deciding how UI is drawn at all. Here it is DOM and
CSS over the canvas, geometry in the scene, or a 2D context — each with different costs, and the
choice is yours. For *visual* punch (button pop, damage
numbers, shake) use `game-feel`. For branching conversation UI use `dialogue-systems`. For
translating UI strings, that is localization (see `references/` and `input-systems` for
rebinding screens). For card/board layout specifics, the `card-game` genre composes this skill.

## Core workflow

1. **Pick a layout model: anchors + containers, never absolute pixels.** Anchor elements to
   edges/corners/center and let containers (rows, columns, grids) flow children. Absolute
   `(x, y)` positions break at the first new resolution.
2. **Choose a scaling strategy** for the whole UI: a reference resolution that scales to fit
   (most games), plus a policy for extra width/height on other aspect ratios (letterbox,
   expand, or anchor HUD corners outward).
3. **Respect the safe area.** Inset critical UI from screen edges so notches, rounded corners,
   and TV overscan don't clip it.
4. **Make every screen keyboard/gamepad navigable.** Set an initial focused control per screen,
   define focus order/neighbors, and show a clear focus highlight. Mouse and focus must coexist.
5. **Model screens as a stack.** Push (pause over game), pop (resume), with input + visibility
   handed to the top screen. This makes overlays and "back" trivial.
6. **Drive the HUD from events, not polling.** The HUD subscribes to `health_changed`,
   `score_changed`, etc. and updates only when they fire — it does not read game state every
   frame.
7. **Verify across screens and devices.** Resize the window, switch aspect ratios, unplug the
   mouse and navigate by gamepad only, and confirm focus, scaling, and safe-area insets. Report
   what you actually observed at which resolutions.

## Patterns

### 1. Anchors + containers, not absolute coordinates

```js
<!-- Anchor a HUD element to a corner and let a container flow a row of hearts.
     In a browser the layout engine IS the anchor system — use it rather than
     computing pixel positions, which only ever work at the resolution you tested. -->
<div id="hud">
  <div id="score"></div>
  <div id="hearts"></div>
</div>
<style>
#hud    { position: fixed; inset: 0; pointer-events: none; }  /* overlay, click-through */
#score  { position: absolute; top: 1rem; left: 1rem; }        /* sticks to the corner */
#hearts { position: absolute; top: 1rem; right: 1rem;
          display: flex; gap: .25rem; }                        /* flex spaces them for you */
</style>
<!-- RIGHT: fixed/absolute anchoring plus flex. WRONG: el.style.left = "640px" —
     correct on one screen, wrong on every other, and broken the moment the window
     is resized, which on the web is constantly. -->
```

### 2. Scale to a reference resolution (one UI, many screens)

```text
# Godot 4.x — Project Settings > Display > Window > Stretch:
#   Mode = "canvas_items", Aspect = "expand", reference size e.g. 1920x1080.
#   UI scales to the window; "expand" reveals extra space you anchor HUD corners into.
# Unity 6 — Canvas > CanvasScaler:
#   UI Scale Mode = "Scale With Screen Size", Reference Resolution = 1920x1080,
#   Match = 0.5 (blend width/height) — pick 1.0 if your HUD is height-critical.
```

### 3. Safe-area inset for notches / overscan

```js
<!-- Inset the UI to the device's safe area (notches, rounded corners, home bars).
     Two halves, and it silently does nothing if you forget the first. -->
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<style>
#hud {
  padding-top:    env(safe-area-inset-top);
  padding-right:  env(safe-area-inset-right);
  padding-bottom: env(safe-area-inset-bottom);
  padding-left:   env(safe-area-inset-left);
}
</style>
<!-- Without viewport-fit=cover the env() values are all zero and the page is simply
     letterboxed away from the notch. With it, they are real and yours to respect.
     Also worth knowing: 100vh on mobile includes browser chrome that comes and goes;
     use 100dvh, or the visualViewport API, if the HUD must hug the bottom edge. -->
```

### 4. Gamepad/keyboard focus (UI is unusable on a controller without it)

```js
// Give each screen a default focus and let a stick or d-pad walk it.
function onScreenShown(root) {
  root.querySelector("[data-default-focus]")?.focus();   // always focus SOMETHING
}
// The browser walks focus for Tab and Shift+Tab from DOM order — so get the DOM
// order right and most keyboard navigation is free. A gamepad gets nothing free:
// nothing moves DOM focus for you, so map stick/d-pad to your own next/previous
// over a list of focusable elements, then call .focus() yourself.
function moveFocus(dir) {
  const items = [...document.querySelectorAll("#screen [tabindex], #screen button")];
  const i = items.indexOf(document.activeElement);
  items[Math.max(0, Math.min(items.length - 1, i + dir))]?.focus();
}
// RIGHT: something is focused when a screen opens. WRONG: nothing selected — the
// gamepad appears dead and the player is stuck with no way to discover why.
```

### 5. Event-driven HUD (decouple UI from game logic)

```js
// RIGHT: the HUD reacts to an event; it updates only when health actually changes.
player.addEventListener("healthchanged", e => {
  healthBar.style.width = `${(e.detail.current / e.detail.max) * 100}%`;
});
// WRONG: updating it inside the render loop —
//   function frame() { healthBar.style.width = ...; requestAnimationFrame(frame); }
// It polls every frame, couples the UI to the player's internals, and writes to the
// DOM sixty times a second for a value that changes twice a minute. Every one of
// those writes can force the browser to recompute layout, inside your frame budget.
```

## Pitfalls

- **Absolute pixel positions / a single design resolution.** Looks right on your monitor, broken
  everywhere else. Anchor to edges/center and flow with containers.
- **No aspect-ratio policy.** 16:9-only layouts crop or letterbox badly on ultrawide and phones.
  Decide expand vs letterbox and anchor HUD to corners that move outward.
- **Ignoring the safe area.** HUD under a notch or lost to TV overscan. Inset critical elements.
- **No initial focus / no focus neighbors.** The game is unplayable on a gamepad; players land
  on a menu with nothing selected. Always focus one control and define navigation.
- **Polling game state in `_process`/`Update`.** Couples UI to internals and wastes work. Push
  updates via signals/events.
- **Tiny fixed font sizes.** Unreadable on a TV-at-distance or a small phone. Scale text with the
  UI and offer a text-size option.
- **Menu flow as boolean flags** (`isPaused`, `inSettings`, …) becomes unmanageable. Use a
  screen stack with push/pop.
- **Hardcoded English strings baked into layout.** Translations overflow buttons. Externalize
  strings and let containers size to content (see `references/`).
- **Mouse-only or focus-only.** Support both; switching input device should not strand the user.

## References

- For stretch/scale modes per engine, the safe-area math, a complete focus-navigation and
  screen-stack pattern, diegetic vs non-diegetic UI, accessibility (text size, contrast,
  colorblind-safe state), and localization-ready layout, read `references/layout-and-flow.md`.

## Related skills

- `game-feel` — button pops, transitions, and HUD juice that ride on top of this layout.
- `dialogue-systems` — conversation/choice UI that lives inside this UI shell.
- `input-systems` — device switching, rebinding screens, and accessible controls.