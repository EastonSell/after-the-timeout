---
name: retain-experiment-evidence
description: Audit a research runner before outcome execution so failed predictions, interruptions and reruns preserve inspectable evidence instead of overwriting or hiding results.
---

# Retain experiment evidence

Use this checklist before collecting the outcomes used for a research claim:

- Freeze the protocol, complete source, case definitions and tests. Include exact
  hashes and declared exclusions. Preserve prior versions when changing a frozen
  design; date and explain prospective amendments before new outcome execution.
- Reserve an exclusive, fresh output directory before the first case. Refuse an
  existing path rather than silently overwriting, appending to or reusing a run.
- Write a running marker and append each completed raw case promptly, flushing
  records before continuing. Preserve successful and failed cases alike. A crash
  marker or partial file is not a completed experiment; do not infer missing rows.
- Save the complete case evidence and prediction checks before raising an assertion
  or returning a failing exit code. Falsifying a hypothesis is a result to retain,
  not a reason to erase the run. Publication criteria are a separate decision.
- Verify expected case identity/coverage and source hashes. Keep the recorded
  source identity in the result. Hash result artifacts when reporting them.
- Reproduce into another fresh directory. Compare deterministic output bytes, not
  just a reassuring summary. Label extra diagnostics or changed hypotheses after
  seeing results as post-hoc, not preregistered checks.

Audit with injected failures, not only happy paths: falsify one prediction; start
with an existing output path; interrupt before the first case and after one complete
case. Check the retained artifacts after each failure. Atomic final-file replacement
prevents a half-written final file, but does not alone retain earlier cases or prove
power-loss durability.

The [regression examples](../../milestones/partial-commit/tests/test_runner.py) use
an isolated temporary directory and synthetic one/two-row harnesses. They make no
network calls. Their behavior is a local executable example, not proof that another
runner, filesystem or distributed execution service has the same guarantees.
