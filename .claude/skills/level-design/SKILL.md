---
name: level-design
description: >
  Design and build playable levels — the blockout/whitebox-to-playable workflow,
  player metrics and grid layout, pacing and flow (tension/rest curve), gating
  and the critical path, and encounter design. Engine-neutral practice. Use when
  the user mentions level design, blockout/whitebox/greybox, level layout, level
  pacing, encounter design, or the critical path through a level.
license: Apache-2.0
compatibility: Platform-neutral practice. No level editor here — blockout is geometry placed from code.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Level design

A level is a **sequence of intentional experiences** delivered through space.
Good level design is a *process*: define the metrics movement is built on, block
out geometry with primitives, play it, then dress it — never the reverse. This
skill is the platform-neutral practice. There is no tile painter and no level editor
here — blockout means geometry you place from code, which makes the discipline of
playing it before dressing it harder to skip and easier to forget.

## When to use

- Use to plan a level's structure: critical path, pacing, gating, encounters,
  and where the player learns vs is tested.
- Use the **blockout → test → iterate → dress** workflow to build a level that
  plays well before any art exists.
- Use to derive level **metrics** from the character's movement so geometry is
  reachable and fair.

**When *not* to use:** to *generate* levels algorithmically, use `procedural-gen`
(authored and procedural design are complementary). For the movement abilities the
metrics come from, that is your own character controller plus `input-systems`.

## Core workflow

1. **Derive metrics first.** Measure the character: max jump height and distance,
   run speed, reach, camera range. Every gap, ledge, and corridor is sized in
   these units. Lock them before building geometry.
2. **Blockout (whitebox/greybox).** Build the whole level from untextured
   primitives at correct scale. Validate flow, sightlines, and reachability while
   changes are cheap. No art yet.
3. **Define the critical path** (start → goal) and the **golden path** you expect
   most players to take. Layer optional/secret paths off it.
4. **Pace the experience.** Alternate tension and rest in a deliberate curve;
   don't run combat-combat-combat. Give the player room to breathe and to
   anticipate.
5. **Teach, then test.** Introduce each mechanic in a safe space, let the player
   practice, then test it under pressure. Difficulty rises in a sawtooth, not a
   straight line.
6. **Gate with intent.** Use locks/keys, abilities, and one-way drops to control
   order and pacing; guide with light, lines, and landmarks rather than walls.
7. **Playtest and iterate.** Watch real players: where do they get lost, stuck,
   bored, or killed unfairly? Fix the blockout; only dress when it plays well.

## Patterns

### 1. Player metrics drive every dimension

```js
// Measure the character ONCE, then size geometry in these units. If the jump
// changes, gaps must be re-derived — never eyeball reachability.
const RUN_SPEED     = 6.0;    // m/s
const MAX_JUMP_H    = 1.4;    // peak height of a full jump, metres
const MAX_JUMP_DIST = 4.2;    // horizontal distance of a running jump
const SAFE_GAP      = MAX_JUMP_DIST * 0.7;   // comfortable, not pixel-perfect
const HARD_GAP      = MAX_JUMP_DIST * 0.95;  // a deliberate skill check
// Build so required traversals use SAFE_GAP; reserve HARD_GAP for optional reward.
// Work in real units from the start — a person is ~1.8 m, a lane ~3.5 m, a storey
// ~3 m — because everything you source or generate later assumes metres.
```

A reachable level falls out of honest metrics. A platform placed `MAX_JUMP_DIST +
1` away is impossible; one at `SAFE_GAP` is fair. Keep these constants beside the
level data so designers and code agree.

### 2. Encounter / pacing as data (a tension timeline)

```js
// Author the level as a sequence of beats with an intended intensity (0..1).
// This makes the pacing curve explicit and reviewable before you build anything.
const BEATS = [
  { room: "entry",     type: "teach",  intensity: 0.1 },
  { room: "hall_1",    type: "combat", intensity: 0.5 },
  { room: "vista",     type: "rest",   intensity: 0.1 },   // breather + reward
  { room: "gauntlet",  type: "combat", intensity: 0.8 },
  { room: "save_room", type: "rest",   intensity: 0.2 },   // before the boss
  { room: "boss",      type: "climax", intensity: 1.0 },
];
// Read the intensity column top to bottom: it should rise overall but dip for rests
// (a sawtooth), never flatline high. Drive spawn density and music intensity from
// this same array so the curve you designed is the curve that ships.
```

### 3. Gating and the critical path (a small graph)

```js
// Model the level as rooms plus gated connections, then VALIDATE reachability.
const ROOMS = {
  entry:     { exits: [{ to: "hall_1" }] },
  hall_1:    { exits: [{ to: "vista", needs: "double_jump" }, { to: "side_room" }] },
  side_room: { exits: [{ to: "hall_1" }], grants: "double_jump" },
  vista:     { exits: [{ to: "boss", needs: "red_key" }] },
};
// Validation (do this): from "entry", can the player reach "boss" given that
// "double_jump" is granted in "side_room" before "vista" requires it? A flood fill
// that only traverses an exit when its `needs` is already satisfiable proves the
// critical path is not soft-locked. Run it in the build, not by hand — a gating
// mistake is invisible until someone is trapped an hour in.
```

## Pitfalls

- **Dressing before it plays.** Detailing a blockout you haven't validated wastes
  the most expensive work on a layout you'll change. Greybox and test first.
- **Geometry that ignores metrics**: gaps the jump can't clear, ledges below
  reach, corridors narrower than the camera needs. Size everything in player units.
- **Flat pacing.** Wall-to-wall combat (or wall-to-wall calm) numbs the player.
  Alternate tension and rest; place a breather and a save before the climax.
- **Testing a mechanic before teaching it.** Players meet a hazard for the first
  time in a lethal spot. Introduce safely, let them practice, then test.
- **Soft-locks and dead ends.** A gate needs an ability/key obtainable only past
  the gate. Validate the critical path's key/ability order, not just connectivity.
- **No readability / guidance.** Players get lost when nothing draws the eye. Use
  light, leading lines, color, and landmarks to point toward the path.
- **One-way drops with no signposting** strand or surprise players. Telegraph
  irreversible moves.
- **Confusing procedural with authored.** Generation gives variety, not
  authored pacing. Use `procedural-gen` for variety; hand-author for intent.

## References

- `references/pacing-and-flow.md` — the difficulty/tension curve in depth,
  teaching-loop design (introduce→develop→twist→test), readability and guidance
  techniques, 2D vs 3D layout considerations, and a blockout review checklist.

## Related skills

- `procedural-gen` — generate variety to complement authored structure.
- `game-ai` — encounter enemies that navigate the space you build.