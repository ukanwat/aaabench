<h1 align="center">AAABench — web build</h1>

<p align="center">
  <strong>No engine. One canvas, one GPU, and a demand.<br>
  Build an open-world game that looks real.</strong>
</p>

<p align="center">
  <img alt="renderer: three.js" src="https://img.shields.io/badge/renderer-three.js-black?style=flat-square">
  <img alt="engine: none" src="https://img.shields.io/badge/engine-none-black?style=flat-square">
  <img alt="status: experimental" src="https://img.shields.io/badge/status-experimental-black?style=flat-square">
  <img alt="contains: no results" src="https://img.shields.io/badge/contains-no%20results-black?style=flat-square">
</p>

This is an experimental arm of [AAABench](https://github.com/ukanwat/aaabench), on its own branch
with no shared history. Same question, one variable moved.

**The engine arm asks whether a model can operate professional tooling.** Unreal supplies Lumen,
Nanite, MetaHuman, Chaos vehicles, Mass crowds, Motion Matching — the agent's job is to know what
to reach for and to build a world with it.

**This arm asks whether it can build the tooling.** There is no editor, no global illumination, no
crowd framework, no vehicle physics, no animation system, no asset library that isn't fetched over
HTTP. There is a renderer and a canvas. Everything between that and a city is written.

Both arms run the same demand and the same measurements. **The difference between them is the
result** — how much of a model's apparent capability was the engine's.

## Why the browser is not the soft option

The obvious read is that this is the easy version because the bar is lower. It isn't. Removing the
engine removes the floor, not the ceiling:

- **Bounce light has to be solved, not enabled.** There is no Lumen. Baked lightmaps are static;
  what happens when the sun moves is an open problem the agent has to answer.
- **Every vehicle, crowd and animation system is authored.** Getting into a car was four pieces of
  Epic machinery. Here it is inverse kinematics, motion warping and a state machine, written.
- **The frame budget is real.** A browser tab, one WebGL2 or WebGPU context, and a memory ceiling
  in the low hundreds of megabytes. Draw calls are a design constraint, not a profiling note.
- **The best asset libraries are gone.** Everything Epic-licensed disappears with the engine.
  What's left is HTTP and whatever the agent can author.

What it gains: the result is a URL anyone can open, every byte is auditable text rather than
binary `.uasset`, and a run costs a fraction of an engine session — which is what makes comparing
models across releases affordable at all.

## What's here

```
PROMPT.md            the demand — this is the benchmark
HARNESS-RULES.md     the line between operating it and doing the agent's job
docs/sources/        where things come from, every entry checked by fetching it
docs/tech/           the stack, with versions and what state each package is in
bin/                 run it, keep it alive, check whether it is working
tools/               what the agent uses: eyes, probe, server
workspace/           the empty room
```

## Status

Being built. Nothing here has produced a result yet, and nothing in this branch should be read as
one.
