# Harness rules — for the operator, not the agent

The benchmark measures what the model does with good conditions. Every hint we give it is a
capability we can no longer claim to have measured. So the line is:

## We may (this is harness work)

- Provide the environment: the machine, the runtime, the shell, credentials, disk, compute, a way
  to see the frame.
- Provide resources: the source lists, the stack inventory, reference-image APIs, catalogues of
  ideas. Breadth of available knowledge is a condition, not an answer. Telling it that a library
  exists and what state it is in is giving it a library card; telling it which one to use for its
  problem is not.
- Provide the demand: the brief, the standards, the definition of failure ("uniform coverage is a
  failure", "it must not look like one company built it"). A spec is not a hint — it is what we are
  asking for. Saying *what good means* is legitimate; saying *what is wrong with its build* is not.
- Fix the harness: restart a dead session, repair a sensor, unblock a port, repair a path that
  resolves to nothing, back the work up.
- Restart it and tell it that prior work stands and where the new standards are.
- Observe as much as we like, and write down everything we see.

## We must not (this is the agent's job)

- **Diagnose its bugs.** Not "the ground texture is tiling", not "the cars are floating", not "the
  night pass has no bounce light in it".
- **Name its errors or hand it a working API call.** It has the web, the docs and the source; using
  them is part of what is being measured.
- **Point at a specific broken thing** and ask it to fix that thing.
- **Edit its code, its assets, its plan or its documents.** Ever.
- **Choose its architecture.** Which renderer path, which physics library, whether to bake or solve
  light, how to stream, what the module boundaries are — every one of those is a judgement under
  test. The stack doc says what exists and what state it is in. It does not say what to pick.
- Answer a question it asks. Nobody is coming; that is the premise.

## Why this is strict

The interesting result is not "can the model build a city if told what is wrong with it" — it is
whether the model *notices*. Self-diagnosis is the capability. Helping only costs us the finding.

This arm makes the line easier to cross than the engine arm did, for one specific reason: **there is
no engine, so there are many more decisions, and most of them have a defensible right answer we
already know.** It is very tempting to save the agent forty minutes by naming the package, the
technique or the trap. That forty minutes is the measurement.

## Comparability — the rule this arm adds

This branch exists to be compared against the engine arm, and a comparison is worth nothing if the
two runs were asked for different things. So:

- **The demand is the same demand.** Where `PROMPT.md` differs from the engine arm's, it differs
  only because a passage named a thing that does not exist here. If a change to one arm's brief
  would change what is being asked for, it has to land in both or in neither.
- **The measurements are the same measurements**, taken the same way, at the same points.
- **The variable is the engine.** Anything else that differs between the arms — session length,
  model, number of sessions, how much was provisioned — is a confound, and an unrecorded confound is
  a result nobody can use.

## Contamination log (keep one, and publish it)

Every run leaks something. A result without a contamination log is a result you cannot check, so
keep the log as you go rather than reconstructing it afterwards, and publish it alongside whatever
you claim.

Log an entry whenever any of these happens — each has been seen in practice:

- **The model under test was not the model you meant.** A bare alias can resolve to a different
  generation between sessions. Pin the exact model id, record the id the session actually reported,
  and exclude sessions that ran on something else. The runner does this for you: it runs with
  `--output-format stream-json`, and writes the models the session actually reported to
  `runs/<stamp>/models.txt`. Read it. Note also that this is why no fallback model is configured —
  an automatic fallback when the model is busy would substitute the subject under test and the run
  would still look successful.
- **Reasoning effort differed between arms.** `--effort` changes how hard the model works and is
  as much a condition as session length. Record it, and keep it identical across arms.
- **A restart note carried diagnosis into the subject.** The failure mode is subtle: a note that
  explains *why* the last session ended, or enumerates the errors it hit, has handed the agent
  findings it was supposed to produce. A restart note should say only that prior work stands and
  where the standards changed.
- **The demand was edited because of something you saw a run do.** Adding a requirement after
  observing a fault is legitimate — the brief should get better — but it is not blind authoring.
  Record that the requirement exists because of an observation, even when the text names nothing the
  agent built and prescribes no specific fix.
- **A dependency was chosen, pinned or repaired for it.** Installing a runtime is harness work.
  Deciding which renderer path or physics library it should build on is the agent's job, and doing
  it for them is contamination even when it happens through a `package.json` you thought was
  scaffolding.
- **You answered a question the agent should have answered.** Any hint, working API call, or
  "actually the problem is…" belongs here, however small it felt at the time.
