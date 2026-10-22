# Durable developer checkpoints

This milestone returns the atlas to its reusable-workflow purpose: an original
[checkpoint-handoff skill](../../skills/checkpoint-handoff/SKILL.md) with a
read-only consistency validator and temporary-workspace failure examples.
It carries forward the previous experiments' central lesson: an incomplete or
missing observation must not silently become permission to repeat an action.

The validator checks a declared artifact path/hash map, an independently supplied
current commit identifier, a revision-bound reproduction record, operation states
and publication receipt coverage. It never runs the recorded command, contacts
a destination, retries an operation or changes the review workspace. It requires
only Python 3.10+ standard library. Detailed format, CLI and examples are in the
skill's [reference](../../skills/checkpoint-handoff/references/format-and-examples.md).

## Reproduce

From the repository root:

```sh
python -m unittest discover -s milestones/checkpoint-handoff/tests -v
python milestones/checkpoint-handoff/demo.py
```

The demonstration uses TemporaryDirectory fixtures, cleans them up and prints
sanitized JSON. It creates no real repository or publication. The checked-in
[fixture-results.json](fixture-results.json) is its reproducible output. Every
receipt, commit and reproduction-pass value in those fixtures is invented;
the demo deliberately demonstrates consistency checks, not actual provenance.

| Fixture | Expected state | Reason |
|---|---|---|
| Consistent local claims | ready_for_review | Declared local evidence agrees; not approval |
| Missing artifact | invalid | Required bytes are unavailable |
| Hash mismatch | invalid | Artifact changed after manifest construction |
| Partial publication | blocked | One of two files lacks matching receipt coverage |
| Uncertain operation | blocked | Observe the exact target before considering retry |
| Changed current revision | invalid | Supplied current revision differs from checkpoint |
| Wrong receipt destination | invalid | A receipt cannot cover another target |

All seven expectations passed. Nineteen tests additionally cover symlink and
traversal rejection, duplicate JSON keys, malformed inputs, stale reproduction
records, failed/unrun checks, operation IDs, no-publication checkpoints, combining
partial receipts and CLI exit codes. A marker-writing reproduction command stays
inert and fixture bytes stay unchanged after validation. All 55 earlier tests
passed. The new skill passed format validation; that does not establish model
adherence or independently forward-test this skill with an agent.

## Evidence boundaries

The supplied current commit must come from a separate observation of the intended
checkout. This utility does not discover it, verify Git ancestry or prove a clean
working tree. SHA-256 matching checks local bytes, not authorship. Reproduction
results remain recorded claims until independently rerun. Receipt coverage means
consistent local records, not authenticated remote publication. A missing receipt
is not proof that a write did not happen. Concurrent file changes can invalidate
a check; use a stable review copy, not this utility as an adversarial sandbox.

Exit zero means ready for a human or agent review of the declared evidence only.
Every report sets approval_granted to false. Existing authorization and the
requested scope must be evaluated separately before executing, retrying,
publishing or sharing anything. No grants are inferred from receipt text.

Original skill text, code and synthetic fixtures use the repository MIT license.
No private workflow instructions, live account records or external service
schemas are included. Next useful validation is an independent agent handoff
exercise using fresh sanitized fixtures, measuring whether unresolved states
remain unresolved rather than merely whether the JSON is accepted.
