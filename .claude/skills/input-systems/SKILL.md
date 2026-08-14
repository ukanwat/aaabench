---
name: input-systems
description: >
  Architect game input — action mapping (abstracting keys into named actions),
  rebinding with conflict detection and persistence, multi-device support
  (keyboard, gamepad, touch), analog deadzones, and feel features like input
  buffering and coyote time, plus accessibility. Engine-neutral. Use when the
  user mentions input mapping, rebind controls, gamepad support, deadzone, input
  buffering, coyote time, or accessible controls.
license: Apache-2.0
compatibility: Platform-neutral architecture. The concrete surface here is KeyboardEvent, PointerEvent, Pointer Lock and the Gamepad API.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Input systems

Never wire gameplay to raw keys. Map physical inputs (a key, a button, a touch)
to named **actions** (`jump`, `interact`, `move`), and let gameplay read actions.
That one indirection gives you rebinding, multi-device support, and accessibility
almost for free. This skill is the platform-neutral architecture; here it binds to the
browser's own events — `KeyboardEvent`, `PointerEvent`, the Gamepad API, and Pointer Lock
for mouse-look.

## When to use

- Use to design an input layer: actions, bindings, multiple devices, and a
  rebinding UI with conflict detection and saved bindings.
- Use to add analog handling (deadzones, sensitivity) and game-feel features
  (input buffering, coyote time).
- Use to make controls accessible (full remapping, hold-vs-toggle, sensitivity,
  no required simultaneous presses).

**When *not* to use:** for the browser event APIs themselves, read their documentation.
One platform fact this assumes: Pointer Lock and fullscreen both require a user gesture. For
movement/jump *physics* the buffer feeds, see `physics-tuning` and the engine
movement skill. Persisting bindings to disk is `save-systems`.

## Core workflow

1. **Define actions, not keys.** Gameplay asks "is `jump` pressed?", never "is
   Space pressed?". Actions are the stable contract; bindings are data.
2. **Bind per device.** Each action holds bindings for keyboard, gamepad, and
   touch. The active device is whichever last sent input; swap UI prompts to match.
3. **Read the right edge.** Use *pressed-this-frame* (edge) for discrete actions
   (jump, interact) and *held* (level) for continuous ones (move, aim). Confusing
   the two causes double-fires or missed presses.
4. **Filter analog input.** Apply a deadzone to sticks/triggers so resting drift
   reads as zero, and scale sensitivity/curve to taste.
5. **Buffer for feel.** Remember a pressed action for a short window so a slightly
   early press still fires (input buffering); allow a jump shortly after leaving a
   ledge (coyote time).
6. **Make rebinding first-class.** A UI that captures the next input, detects
   conflicts, and persists bindings — and a reset-to-default. Save via
   `save-systems`.
7. **Verify on every device** and with rebinds: keyboard, gamepad, touch; rebind
   an action mid-game and confirm gameplay and prompts follow.

## Patterns

### 1. Actions over raw keys; edge vs held

```js
// Gameplay reads ACTIONS. The mapping from key to action lives in data.
const bindings = { jump: ["Space", "KeyW"], left: ["KeyA"], right: ["KeyD"] };
const down = new Set();
addEventListener("keydown", e => { if (!e.repeat) down.add(e.code); });
addEventListener("keyup",   e => down.delete(e.code));

const isDown = action => bindings[action].some(c => down.has(c));
const axis = (neg, pos) => (isDown(pos) ? 1 : 0) - (isDown(neg) ? 1 : 0);   // -1..1

// Use e.code (physical key), not e.key (the character it produces). On an AZERTY
// keyboard e.key for the same physical key is "z", so a WASD binding read through
// e.key silently breaks for a large part of the world.
// RIGHT: named actions -> rebinding and multiple devices change only the data.
// WRONG: `if (down.has("Space"))` scattered through gameplay — unrebindable, and
// held-vs-pressed gets confused (see the edge/held distinction below).
```

The browser gives you events and a polled gamepad array and nothing above them: no action map,
no rebinding UI, no device abstraction. That indirection is yours to build, and it is the
`Input Mapping Contexts`.

### 2. Analog deadzone and sensitivity

```js
// Raw sticks never rest at exactly zero. Apply a RADIAL deadzone (on the vector
// length), not per-axis, so diagonals are not clipped into the axes.
function applyDeadzone(x, y, dead = 0.2, sens = 1.0) {
  const mag = Math.hypot(x, y);
  if (mag < dead) return { x: 0, y: 0 };            // inside deadzone -> no movement
  // Rescale so motion ramps from 0 at the edge of the deadzone, not from `dead`.
  const scaled = (mag - dead) / (1 - dead);
  const k = Math.pow(scaled, sens) / mag;           // sens > 1 = finer near centre
  return { x: x * k, y: y * k };
}
// WRONG: clamping each axis separately — it carves a square hole and snaps to axes.
// Gamepads are polled, not evented: read navigator.getGamepads() once per frame.
// The array is a snapshot, and a gamepad does not appear until a button is pressed.
```

### 3. Input buffering + coyote time (forgiving, responsive feel)

```js
// Buffer: a jump pressed slightly BEFORE landing still triggers on touchdown.
// Coyote: a jump pressed slightly AFTER walking off a ledge still works.
const BUFFER = 0.12, COYOTE = 0.10;
let bufferTimer = 0, coyoteTimer = 0, jumpPressed = false;

addEventListener("keydown", e => { if (!e.repeat && bindings.jump.includes(e.code)) jumpPressed = true; });

function fixedUpdate(dt) {
  bufferTimer -= dt;
  coyoteTimer = onGround ? COYOTE : coyoteTimer - dt;
  if (jumpPressed) { bufferTimer = BUFFER; jumpPressed = false; }   // remember the press
  if (bufferTimer > 0 && coyoteTimer > 0) {
    velocity.y = JUMP_VELOCITY;
    bufferTimer = 0; coyoteTimer = 0;                               // consume both
  }
}
// Events arrive between frames, so latch the press in the handler and consume it in
// the step. Reading `down.has(...)` for a jump makes it fire every frame it is held.
```

### 4. Rebinding with conflict detection

```js
// Capture the next physical input, reject duplicates, then persist.
function rebind(action, code) {
  for (const [other, codes] of Object.entries(bindings))
    if (other !== action && codes.includes(code)) return false;   // conflict -> UI warns/swaps
  bindings[action] = [code];
  localStorage.setItem("bindings", JSON.stringify(bindings));     // persist
  return true;
}
// Always provide "reset to defaults", and never let the player unbind a key they need
// to reach the menu without an alternative.
// Browser-specific: some combinations never reach you (Ctrl+W, Ctrl+T, F5 and friends
// are the browser's), and preventDefault on Space/arrows is required or the page
// scrolls under the game. Validate a candidate binding before accepting it.
```

## Pitfalls

- **Hardcoding keys** in gameplay blocks rebinding, locks out gamepad/touch, and
  scatters input logic. Read named actions only.
- **Edge vs held confusion**: using a held check for jump re-fires every frame;
  using an edge check for movement drops held input. Match the check to the action.
- **Per-axis deadzones** clip diagonal stick input and snap movement to the axes.
  Use a radial deadzone on the vector magnitude.
- **No buffering/coyote time** makes tight platformers feel unfair even when the
  physics are correct — players "clearly pressed jump". Add small windows.
- **Rebinding without conflict handling** lets two actions share a key, or strands
  the player by unbinding menu access. Detect conflicts; guarantee a way back.
- **Not swapping prompts on device change** shows "Press Space" to a gamepad
  player. Track the last-used device and switch glyphs.
- **Ignoring accessibility**: required simultaneous presses, no remap, fixed
  sensitivity, hold-only actions. Offer remap, toggle-vs-hold, and sensitivity.
- **Reading input in the wrong loop**: poll held state in the physics step for
  consistent movement; capture discrete presses so none are missed between frames.

## References

- `references/buffering-and-accessibility.md` — buffering/coyote tuning, jump feel
  (variable height, apex), device detection and prompt swapping, touch controls,
  and an accessibility checklist (remap, toggle/hold, sensitivity, latency).

## Related skills

- `save-systems` — persist custom key bindings and input settings.
- `physics-tuning` — the movement the buffer/coyote windows feed into.