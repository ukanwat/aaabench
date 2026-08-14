---
name: physics-tuning
description: >
  Tune game physics for stable, good-feeling motion — fixed vs variable
  timestep, render interpolation, mass/gravity/drag, continuous collision
  detection (CCD) to stop tunneling, fixing jitter, and collision layers/masks.
  Engine-neutral. Use when the user mentions physics feel, jitter, tunneling,
  fixed timestep, CCD, bouncing or unstable physics, or collision layers and masks.
license: Apache-2.0
compatibility: Platform-neutral concepts. Physics is whichever WASM engine you choose; see docs/tech/stack.md.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Physics tuning

Most "bad physics" is not a bug in the engine — it's a mismatch between the
**fixed-timestep simulation** and the **variable-rate render loop**, or untuned
mass/drag/CCD/layer settings. This skill covers the engine-neutral knobs that
make physics stable and responsive. There is no built-in physics here; the concrete API is
whichever WASM engine you choose — see `docs/tech/stack.md` for what exists and in what state.

## When to use

- Use when motion jitters, objects pass through walls (tunneling), stacks
  explode, or movement feels floaty/sticky/laggy.
- Use to decide what goes in the fixed (physics) step vs the render frame, and
  how to interpolate between them.
- Use to tune gravity, mass, drag, restitution, solver iterations, sleeping, and
  collision layers/masks.

**When *not* to use:** for a specific physics library's API and collision events, read its
own documentation. For *movement
decisions* (when to jump, AI steering) use `input-systems` and `game-ai`. For
platformer jump-feel specifics like coyote time/jump buffering, that's input/
controller territory — see `input-systems` and the `platformer` genre.

## Core workflow

1. **Run physics on a fixed timestep.** Simulate at a constant rate (e.g. 50–60
   Hz). A fixed `dt` makes the simulation deterministic-ish and stable; a
   variable `dt` makes integration and collisions inconsistent.
2. **Put physics work in the physics callback**, not the render frame. Apply
   forces/velocities and read collisions in the fixed step, using that step's `dt` — never the
   frame delta.
3. **Interpolate rendering between physics ticks.** The render frame rate ≠ the
   physics rate, so smoothly interpolate transforms toward the latest physics
   state, or enable the engine's Rigidbody interpolation, to remove visible
   stutter.
4. **Tune the body, not the scene.** Set mass for relative weight, drag for
   damping, gravity scale per object, and restitution/friction via materials.
5. **Stop tunneling with CCD** on small/fast bodies; cap maximum velocity.
6. **Stabilize stacks/joints** with more solver iterations, sane mass ratios, and
   sleeping for resting bodies.
7. **Verify by feel and stress test.** Play at low and high frame rates; throw
   fast objects at thin walls; stack and shove bodies. Report what you observed.

## Patterns

### 1. Fixed timestep for simulation, render interpolation for smoothness

```js
// Fixed step for simulation, variable rate for rendering, interpolation between.
// Nothing provides this loop for you here; it is the first thing to get right,
// because every other tuning decision is downstream of it.
const STEP = 1 / 60;
let accumulator = 0, prev = { ...body.position }, curr = { ...body.position };

function frame(dt) {
  accumulator += Math.min(dt, 0.25);        // clamp: a long stall must not spiral
  while (accumulator >= STEP) {
    prev = { ...curr };
    physicsStep(STEP);                      // integrate with the FIXED dt, always
    curr = { ...body.position };
    accumulator -= STEP;
  }
  const alpha = accumulator / STEP;         // 0..1 within the current tick
  visual.position.lerpVectors(prev, curr, alpha);
  renderer.render(scene, camera);
}
// RIGHT: integrate in the fixed step, render via interpolation.
// WRONG: stepping physics with the frame delta — speed and collision behaviour then
// depend on frame rate, and the game plays differently on a 144 Hz monitor.
```

Nothing offers this for you here — there is no interpolation flag to set. Store the previous and
current transform each step and interpolate between them yourself; the alternative
before hand-rolling.

### 2. Stop tunneling: CCD + a speed cap

```js
// Fast, small bodies skip past thin colliders between ticks. Two fixes:
body.setCcdEnabled(true);          // most WASM engines expose continuous detection per body
// Cap velocity so a single step cannot move more than ~one collider thickness.
const MAX_SPEED = 40;
if (speed > MAX_SPEED) velocity.multiplyScalar(MAX_SPEED / speed);
// Rule of thumb: distance_per_step (= speed / hz) must be < the thinnest wall.
// Raise the step rate or enable CCD when that fails — but note that raising the rate
// costs you everywhere, and CCD costs you only on the bodies that need it.
```

### 3. Body tuning: mass, drag, gravity scale, material

```js
// Mass is RELATIVE weight in collisions; it does NOT change fall speed (gravity
// accelerates all masses equally). Use damping and per-body gravity to shape feel.
body.setMass(2.0);            // heavier pushes lighter in collisions
body.setLinearDamping(0.5);   // air drag: higher = stops sooner
body.setGravityScale(1.5);    // snappier fall without changing world gravity
// Bounce and slide come from the collider's material properties, not from code:
collider.setRestitution(0.2); // 0..1
collider.setFriction(0.8);    // surface grip
// Exact names vary by library; the model does not. Look them up rather than guess.
```

### 4. Collision layers and masks (who collides with whom)

```js
// A body is ON its group(s) and INTERACTS WITH the groups in its filter. Both
// directions of a pair must agree, or the interaction silently does not happen —
// which looks exactly like a broken collider and is the harder bug of the two.
const LAYER = { WORLD: 1 << 0, PLAYER: 1 << 1, ENEMY: 1 << 2, PICKUP: 1 << 3 };
playerCollider.setCollisionGroups(pack(LAYER.PLAYER, LAYER.WORLD | LAYER.ENEMY));
pickupCollider.setCollisionGroups(pack(LAYER.PICKUP, LAYER.PLAYER));
// Many engines pack membership and filter into one 32-bit value (upper half membership,
// lower half filter). Keep a named table, never magic numbers, and write the packing
// helper once.
```

## Pitfalls

- **Applying forces/movement in the render frame** (`Update`/`_process`) makes
  behavior frame-rate dependent — faster PCs run faster, and collisions get
  flaky. Do simulation in the fixed step.
- **Visible jitter** even with a fixed step usually means no render
  interpolation: the physics rate and display rate beat against each other.
  Enable interpolation.
- **Tunneling** through thin walls: discrete collision misses fast movers. Enable
  CCD, cap speed, thicken walls, or raise the physics rate.
- **Expecting heavier objects to fall faster.** Gravity is acceleration; mass
  affects collision response, not fall speed. Use `gravity_scale`/drag for feel.
- **Exploding stacks / jittery joints**: mass ratios too extreme, or too few
  solver iterations. Keep mass ratios modest and raise iteration counts.
- **Bodies that never rest** burn CPU and twitch. Enable sleeping and a sensible
  sleep threshold for resting objects.
- **One-directional layer setup**: A's mask includes B but B's mask excludes A.
  Detection/collision can need both sides; verify the full matrix.
- **Huge `dt` spikes** (load hitches, breakpoints) blow up integration. Clamp the
  max physics step / substep count so a stall doesn't launch everything.

## References

- `references/timestep-and-ccd.md` — the fixed-timestep accumulator loop,
  interpolation math, substepping, CCD modes, solver/iteration tuning, sleeping,
  and a stability checklist.

## Related skills

- `input-systems` — responsive controls, jump buffering, coyote time.
- `game-ai` — agent movement that must agree with the physics step.