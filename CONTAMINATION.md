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
