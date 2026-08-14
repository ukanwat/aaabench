# Contamination log

Every run leaks something. A result without a log of what leaked is a result nobody can check.
Entries are appended as they happen, never reconstructed afterwards. See `HARNESS-RULES.md` for
what counts.

---

## 2026-08-14 — ecosystem inventory added to `docs/tech/stack.md` during a live session

**What happened.** An "ecosystem, by what it replaces" table was added to the stack doc — package
names, versions, star counts, last-push dates and licences for navigation, crowds, particles, SDF
text, frame debugging, GPU timing, character control, atmosphere, lightmap baking and mesh
simplification. It was added **while run `20260814-222943` was in progress**, roughly forty minutes
in, and after the operator had observed that session measure stock forward lighting collapsing at
64 point lights and conclude it needed a clustered light system.

**Why it is logged.** The table is a resource, not a diagnosis: it names what exists and its state,
prescribes nothing, and explicitly declines to say what belongs in the build. The agent has web
search and could assemble the same list itself. But the *timing* is not blind — it was written
after watching a session hit a problem, which is precisely the case `HARNESS-RULES.md` says to
record even when the text names nothing the agent built.

**What it does and does not affect.** The lighting question the session had just posed is not
answered by the table; no GI recommendation is made, and the entry for the most-cited SSGI package
records that it has not shipped since February 2024. Any claim about how quickly this arm found its
rendering architecture should nonetheless be read with this entry in view.

**Parity.** The engine arm has no equivalent addition. Either it gets one, or the difference is a
confound between the arms.

---

## 2026-08-14 — run `20260814-222943` spawned subagents on the bare `opus` alias

**What happened.** The session delegated two lanes ("source and vet vehicle assets", "build district
reference boards") with `model: "opus"` rather than `model: "claude-opus-5"`. `PROMPT.md` states the
full id must be passed and the short alias never used, giving the reason. The agent used the alias
anyway.

**Why it matters.** The alias has previously been observed resolving to a different Opus generation
between sessions. Those two lanes may therefore have run on a model that is not the subject under
test, and their output — a vetted vehicle asset set and district reference boards — fed back into
the main session.

**Status.** Not operator-induced; the harness said the right thing and the agent did not follow it.
Recorded because the run's output is partly the product of an unverified model. The stream-json
`init` event only reports the parent session's model, so a subagent's actual model is not currently
recoverable from the log — which is itself a gap in the instrumentation worth closing.

**This is a finding, not only a contamination.** Whether an agent follows a stated condition it has
no incentive to check is exactly the kind of thing this benchmark exists to observe.

---

## 2026-08-14 — "Build the room you inspect the work from" added to `PROMPT.md` mid-run

**What happened.** A new required section was added to the demand: the agent must build a
navigable free camera, repeatable named viewpoints, a live frame-cost readout, live control of
time and weather, and expose all of it to scripts as well as to a human. `docs/tech/stack.md`
gained a note that three.js ships nine control classes and which debug-UI packages exist.

**Why it was added.** Run `20260814-222943` produced a world with no input handling of any kind —
`window.game` with `goto`/`stand`/`aerial`/`info` for its own screenshots, and nothing a person
could press. The operator opened the page, could not move, and asked for it.

**Why this is provisioning rather than diagnosis, and where that argument is weak.** The engine
arm's agent inherits an editor viewport, a scene outliner, a stat overlay and a time-of-day
control from Unreal, free. This arm inherits none of it, so requiring the equivalent levels the
conditions rather than tilting them, and the section states an outcome without prescribing an
implementation. The weak part is honest: it was written **after watching a session not do it**,
which is exactly the case these rules say to record even when the text names nothing the agent
built.

**Parity.** Must be mirrored into the engine arm's demand. Largely moot there — Unreal supplies
most of it — but the requirement has to be asked of both or the arms are not answering the same
question.

---

## 2026-08-15 — "buildable ground" added to `PROMPT.md`, and an operator-written camera left in a run's workspace

**Two entries, same session.**

**1. Demand change.** A "Buildable ground" bullet was added to the reality constraints: a city needs
flat land, real cities sit on the flat parts with relief at their edges, and where there was not
enough people made it by cut, fill, terracing and reclamation. It closes with the test — *where on
this would anyone actually have laid a grid*.

*Why it is logged.* It was written after measuring run `20260814-222943`'s terrain: median slope
10.2%, only 24.7% of land under 5%, a fifth over 20%. The text names nothing that run built and
prescribes no fix — the constraint is a fact about cities, and the session had already flagged two
districts as too steep on its own — but it was authored in response to an observation, which is the
recorded case.

**2. Operator-written code in a run's workspace.** `workspace/src/debug/operator-camera.js` and a
guarded import in `src/main.js` were written **by hand, by the operator**, after session 1 closed,
because the session had built a scripted camera for its own screenshots and nothing a human could
drive. The file says so in its header and tells a later session to delete it.

*Why it matters.* Any judgement of that workspace must exclude those two files. If a session is ever
resumed against that workspace, it inherits an inspection layer it did not write — and the demand
now requires one, so that inheritance would hand it a graded requirement. **A resumed run on this
workspace cannot be used to claim the agent built its own inspection layer.**

**Parity.** The buildable-ground constraint must be mirrored into the engine arm's demand.
