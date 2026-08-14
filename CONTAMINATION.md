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

---

## 2026-08-15 — `PROMPT.md` corrected five minutes into campaign session 1

**What happened.** The inspection-layer section said both "usable with nothing to type" and "gate it
behind a flag, a key, or a query parameter". Contradictory. Rewritten so the gate is the build:
present and immediate during development, absent from a release, with a toggle key for captures.

**Effect on the live session.** None. The runner assembles the prompt into the session directory at
launch, so session 1 of campaign `20260815-0012` is running against the earlier text. The
correction applies from session 2. Recorded because a demand that changed mid-campaign means
sessions in the same campaign were not asked exactly the same thing.

---

## 2026-08-15 — the subagent alias failure reproduced, and it is a finding

**What happened.** Campaign session `20260815-0012` spawned **17 subagents: 16 with
`model: "opus"` and one with no model set**. None used `claude-opus-5`. This is the second
independent run to do it; the first was `20260814-222943` with 2 of 2.

**Why it is a finding rather than a slip.** `PROMPT.md` states the full id must be passed, gives
the reason (the bare alias has been observed resolving to a different Opus generation between
sessions), and says explicitly never to use the short form. Two runs, seventeen-plus lanes, zero
compliance. A model reliably declining a stated, justified, checkable condition about its own
configuration is exactly the kind of long-horizon behaviour this benchmark exists to observe.

**Why it is also a validity problem.** A material share of the work — asset vetting, reference
gathering, writing — is being done by lanes running on an unverified model. The stream-json `init`
event reports only the parent session's model, so a subagent's actual model is not recoverable from
the transcript. Any claim of the form "Opus 5 produced this world" is, strictly, "Opus 5 and
seventeen lanes on an alias produced this world".

**Not fixed by making the instruction louder.** It is already explicit and reasoned. Making it
louder in response to observing non-compliance would also be a demand edit driven by a run.
Recorded and left alone; the instrumentation gap (subagent model not logged) is the part worth
closing, because it is harness work rather than a change to what is asked.

---

## 2026-08-15 — self-critique required of every lane

**What happened.** `PROMPT.md` gained a requirement that any lane producing judgeable work opens a
fresh critic context before returning, briefed to find fault rather than assess, and reports what
came back along with what it did about it. The same is asked of the agent's own work.

**Why it is logged.** Written after observing campaign session `20260815-0012` spawn 17 lanes and
run zero critics, while the existing text already said critics were free and unlimited. The
addition prescribes a working method rather than an outcome, which is a heavier hand than most of
this brief — justified on the grounds that the brief already prescribes delegation structure (lane
counts, file ownership, brief contents), but it is a change to *how* rather than *what*, made in
response to a run.

**Parity.** Must be mirrored into the engine arm.

---

## 2026-08-15 — three practices adopted from `mshumer/Claude-of-Duty`

**What happened.** After reading that repository — a Three.js FPS built by Opus 5 from an
eleven-line prompt, 3.1k stars — three standards were added to `PROMPT.md`:

1. **Blind comparison against a named bar.** Critics are shown the work and a reference *without
   being told which is which* and must pick. Replaces an earlier, weaker "self-critique" wording
   that the self-correction literature says is the failing version: intrinsic critique without a
   grounded external signal often does not help and can degrade output.
2. **A visual regression gate on optimisation.** Fixed shot set before, same set after, compared
   pixel by pixel; any change is a bug or a deliberate, written-down trade. Taken from that repo's
   `imagediff.mjs`, whose header states the rule exactly.
3. **An engine contract document** — hard rules, subsystem interfaces, ownership map, events,
   quality bar — taken from its `ARCHITECTURE.md`, for coherence across cold sessions and lanes.

**Why it is logged.** These are demand changes, and their source is an artefact built by the same
model family under a different prompt. They are craft standards rather than answers about this
world, and none of them says anything about what to build — but a benchmark whose brief absorbs
techniques from a successful run elsewhere should say so plainly.

**Parity.** All three must be mirrored into the engine arm.

---

## 2026-08-15 — engine-contract requirement reverted

The "keep a contract for the machine you are building" paragraph added earlier from
`mshumer/Claude-of-Duty`'s `ARCHITECTURE.md` was **removed at the operator's instruction**, on the
grounds that the demand should not absorb a practice merely because the operator happened to read
it that evening. The blind-comparison bar and the visual-regression gate were kept.

Recorded because the demand text differed for part of one session, and because the reasoning
matters: two of three adopted practices survived a deliberate second look and one did not. Nothing
in the live session had read any of the three — session 1 of campaign `20260815-0012` runs against
the prompt assembled at launch.

---

## 2026-08-15 — "verify each layer in the thing that ships" added to `PROMPT.md`

**What happened.** Two sentences added to the generation section: verify each layer in the real
build before stacking the next on it, and make instruments capable of showing absence.

**Why it is logged.** Written after watching campaign session `20260815-0012` cache terrain, coast,
roads and parcels in Python across ~20 minutes, then capture a browser frame that was almost
entirely black — because `world/manifest.json` was never exported and every chunk request 404s,
while its own overlay reported `chunks 1301 cells / 21.3 MB` for a grid that had not loaded. The
text names none of that and prescribes no fix, but it was authored in response to it.

**Parity.** Must be mirrored into the engine arm.
