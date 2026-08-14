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
