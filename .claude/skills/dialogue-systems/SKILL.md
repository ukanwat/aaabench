---
name: dialogue-systems
description: >
  Build branching dialogue and narrative — a node/choice graph with conditions,
  variables, and localization hooks — and choose between authoring tools Ink and
  Yarn Spinner or a custom data-driven runner. Engine-neutral. Use when the user
  mentions dialogue system, branching dialogue, conversation tree, choices,
  Ink (.ink), Yarn Spinner (.yarn), or NPC dialogue.
license: Apache-2.0
compatibility: Platform-neutral. Ink (inkle) and Yarn Spinner 2.x syntax; both have JavaScript runtimes.
metadata:
  engine: none
  category: disciplines
  difficulty: intermediate
---

# Dialogue systems

Model conversations as a **graph**: nodes hold lines, choices branch the flow,
conditions gate options, and variables remember what the player did. The first
real decision is *build vs. buy* — adopt a proven authoring tool (**Ink** or
**Yarn Spinner**) or write a small data-driven runner. This skill owns both Ink
and Yarn; the `visual-novel` and `rpg` genres consume it.

## When to use

- Use to design branching conversations, choice menus, or narrative state
  (flags, relationship values) that affect later dialogue.
- Use to decide between Ink, Yarn Spinner, and a custom JSON/resource format.
- Use to wire a dialogue script into your game loop (advance line, present
  choices, run commands, resolve variables).

**When *not* to use:** for the UI that renders text boxes, portraits and choice
buttons, use `game-ui-ux` — here that is DOM or canvas, not an engine widget tree.
For persisting narrative variables across sessions, use `save-systems`. Dialogue
data is JSON or ES modules on disk; there is no resource system to author it in.

## Core workflow

1. **Choose the authoring approach.**
   - **Ink** — prose-first, writer-friendly, weave/gather flow; great for
     dialogue-heavy or CYOA narrative. Integrate via ink runtime / inkle plugins.
   - **Yarn Spinner** — node-based, explicit `<<commands>>`, strong for
     game-driven dialogue with lots of engine hooks.
   - **Custom runner** — a JSON/resource graph + a small interpreter when you need
     full control or minimal dependencies. Don't build a *language*; build a graph.
2. **Define the node contract.** A node yields one of: a line (speaker + text),
   a set of choices, a command/side-effect, or an end/jump. The runner advances
   through nodes and hands lines/choices to the UI.
3. **Separate variables from flow.** Keep a variable store (booleans, numbers,
   strings) the dialogue reads/writes; gate choices with conditions over it.
4. **Localize from the start.** Author with **line IDs**, not raw strings, so the
   displayed text comes from a string table keyed by locale.
5. **Drive it from the game loop.** The runner is a state machine: `current` node
   → emit content → wait for input (continue or choice) → advance.
6. **Verify by walking branches.** Exercise each choice path; confirm conditions,
   variable writes, and that every branch reaches an end or a valid jump.

## Patterns

### 1. Engine-neutral dialogue graph (data, not code)

```json
{
  "start": "guard_intro",
  "nodes": {
    "guard_intro": {
      "speaker": "Guard", "line": "DLG_GUARD_001",
      "choices": [
        { "text": "DLG_OPT_BRIBE", "to": "bribe", "if": "gold >= 50" },
        { "text": "DLG_OPT_LEAVE", "to": "end" }
      ]
    },
    "bribe": {
      "speaker": "Guard", "line": "DLG_GUARD_BRIBED",
      "set": { "gate_open": true, "gold": "gold - 50" },
      "next": "end"
    },
    "end": { "end": true }
  }
}
```

`line`/`text` are **string-table IDs** (localization), not literal text. `if`
gates a choice; `set` mutates the variable store. The full interpreter that walks
this graph is in `references/runner.md`.

### 2. Runner step (a state machine over the graph)

```js
// The runner holds the current node and a variable store; the UI calls advance().
function present(node) {
  if (node.line) ui.showLine(node.speaker, localize(node.line));
  if (node.choices) {
    const shown = node.choices.filter(c => evalCond(c.if ?? ""));
    ui.showChoices(shown);              // only choices whose condition passes
  }
}

function choose(choice) {                // called when the player picks one
  applySet(choice.set ?? {});            // write variables
  goto(choice.to);
}

function goto(id) {
  current = graph.nodes[id];
  applySet(current.set ?? {});
  if (current.end) { ui.close(); return; }
  present(current);
  if (current.next && !current.choices) goto(current.next);   // auto-advance linear nodes
}
// Keep the graph as plain data (JSON or an ES module) so it can be diffed, validated
// and regenerated. A dialogue tree encoded in code is one nobody can review.
```

### 3. Ink — branching with knots, choices, and variables (inkle)

```ink
// Ink: '*' = once-only choice, '+' = sticky. [bracketed] text shows only in the
// choice, not the printed result. '->' diverts; '-> END' stops the flow.
VAR gold = 60

=== guard_intro ===
The guard blocks the gate.
* {gold >= 50} [Offer 50 gold]   "Here, take it."
    ~ gold = gold - 50
    The guard pockets it and steps aside. -> END
* [Leave]   You turn back. -> END
```

Ink tracks how often each knot was seen, so `{visited_knot}` is a built-in
condition. Variables are global (`VAR`) or temporary (`~ temp`).

### 4. Yarn Spinner — nodes, options, and commands (Yarn 2.x)

```yarn
title: GuardIntro
---
<<declare $gold = 60>>
Guard: You can't pass.
-> Offer 50 gold <<if $gold >= 50>>
    <<set $gold = $gold - 50>>
    Guard: ...fine. Go on through.
    <<set $gate_open to true>>
-> Leave
    Guard: Good choice.
===
```

Yarn lines may start with `Speaker:`; options use `->`; `<<set>>`/`<<declare>>`
manage `$variables`; `<<if>>` gates an option; `<<jump NodeName>>` moves between
nodes. Interpolate values in text with `{$gold}`.

## Pitfalls

- **Hardcoding display strings** instead of line IDs makes localization a
  rewrite. Author against a string table from day one.
- **Inventing a scripting language** for a simple branching tree. If you only
  need lines + choices + flags, a JSON/resource graph plus a 50-line runner beats
  a parser you must maintain. Use Ink/Yarn when writers need real flow control.
- **Variables coupled to the UI**: store narrative state separately so the same
  dialogue works in cutscenes, menus, and tests. Persist it via `save-systems`.
- **Unreachable or dead-end nodes**: a node with no `next`, choices, or end
  silently stalls. Validate that every node terminates or branches.
- **Mutating state in a line node the player can revisit** double-applies (`gold`
  drained twice). Apply `set` on the transition, or guard with a seen-flag.
- **Mixing Ink's `*` (once-only) and `+` (sticky)** by accident: looped menus
  need sticky `+` choices or the options vanish after one use.

## References

- `references/ink-and-yarn.md` — side-by-side syntax cheat sheet (choices,
  diverts/jumps, variables, conditions, includes) and integration notes.
- `references/runner.md` — a complete custom dialogue runner: graph schema,
  condition/expression evaluation, variable store, and localization lookup.

## Related skills

- `save-systems` — persist narrative variables and seen-flags.