# Handbook index — web build

Read `../PROMPT.md` (the job) first. Everything here is reference; load what you need.

## tech/ — the machine you are working on
- [stack.md](tech/stack.md) — what exists in a browser, at what version, and **what state each
  package is in**. Two of the obvious choices are stale and one is merged but unreleased. Read this
  before you plan a subsystem around a dependency.
- [feedback.md](tech/feedback.md) — how to see your own work: the server, the screenshot sensor,
  and the flags without which a headless browser renders on the CPU and reports no WebGPU at all.

## workflow/ — how professionals build this
- [phases.md](workflow/phases.md) — production phases and their exit gates
- [level-pipeline.md](workflow/level-pipeline.md) — blockout → set dress → lighting → polish
- [metrics.md](workflow/metrics.md) — real-world dimensions and conventions
- [game-content.md](workflow/game-content.md) — what a complete game contains: mission counts and
  anatomy from shipped titles, story arc, cast size, cheap narrative, and the minimum viable
  content set in priority order
- [systems.md](workflow/systems.md) — genre systems with real parameters: wanted-level thresholds
  and search radii, police tiers, driving handling values, cover and aim-assist, economy rates,
  streaming budgets, POI density, audio stack, game-feel timings, triage
- [detail-density.md](workflow/detail-density.md) — how "thousands of unique things" is really
  done: combinatorial variation maths, per-block density targets, and the eye-height detail pass
  (wear, contact, edges, verticality, lit windows, ground)
- [world-inventory.md](workflow/world-inventory.md) — the catalogue: hundreds of *kinds* of thing a
  map contains (infrastructure, utilities, transport, industry, street furniture, signage, life),
  plus the real world's own taxonomy mined from OpenStreetMap and ranked by how often each thing
  actually occurs, with the API call so you can query any category yourself
- [parallel.md](workflow/parallel.md) — subagent lanes and the contract rules. Note that the
  constraint here is different from an engine build: your world is text, so lanes can genuinely run
  in parallel as long as file ownership is disjoint

## sources/ — getting things in
- [assets.md](sources/assets.md) — every source checked by fetching it, with the walls named
  and the Epic-licensed losses stated. Includes keyless glTF-native model sources, real
  photogrammetry scans, materials, HDRIs, humans and animation, sound, and reference photography.
- [mapdata.md](sources/mapdata.md) — real-world map data: OSM, Overpass, bulk extracts.
- `tools/check-sources.py` re-verifies all of it and exits non-zero on drift. The list is only
  trustworthy because it can be re-run.

## Skills — `.claude/skills/`
Craft packs that are engine-agnostic and carried over from the engine arm so both builds have the
same knowledge available: **game-ai · level-design · game-feel · camera-systems ·
performance-optimization · physics-tuning · procedural-gen · audio-design · game-ui-ux ·
shader-programming · input-systems · dialogue-systems · save-systems · reference-images**.

They occasionally name an engine's equivalent API for comparison. Those cross-references are not
available here; the concepts are.

## Tools — `tools/`
- `serve.py` — static server with the MIME types, COOP/COEP and no-store you need
- `shot.py` — GPU-backed headless screenshot, console capture, `--eval` hook, `--gpu-info`
- `check-sources.py` — re-verify every source in `sources/assets.md`
- `gen-image.py` — on-device image generation for signage, billboards, posters, murals, packaging,
  liveries and brand marks. No key, no cost.
