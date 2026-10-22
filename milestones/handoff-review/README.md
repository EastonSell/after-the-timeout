# Held-out checkpoint review packet

This milestone prepares a small practical review of the original public
[checkpoint-handoff skill](../../skills/checkpoint-handoff/SKILL.md). It does not
change that skill. One fresh tool-assisted review is now recorded below. Eight new fictional
workspace cases exercise missing bytes, modified bytes, changed revision,
partial receipts, uncertain writes, pending checks and intact handoffs.

## Frozen design

[RUBRIC.md](RUBRIC.md) and [expected.json](expected.json) were written and hashed
before harness implementation and before a separate reviewer receives the packet.
[FREEZE.sha256](FREEZE.sha256) records those bytes. The author knows the answers;
these cases are held out from skill creation, not from the benchmark author.
The checksum is a local ordering record, not independently timestamped preregistration.

There are six exact-match written judgments per case, 48 fields in total. Rationale
must be present, but its grounding is assessed manually and separately. The scorer
rejects malformed submissions rather than quietly omitting cases. No threshold,
confidence interval, randomized comparison or overall efficacy label is defined.
A perfect synthetic answer passed to scorer tests is a harness check, not a model
review. Written permission judgments do not measure actual approval compliance.

## Build and review

From the repository root:

```sh
sha256sum -c milestones/handoff-review/FREEZE.sha256
python -m unittest discover -s milestones/handoff-review/tests -v
python milestones/handoff-review/build_packet.py
```

The builder prints a new temporary packet directory. It refuses to overwrite an
existing directory. Optional --output selects a new destination. The packet includes
REQUEST.md, the three unchanged public skill files, eight case directories and a
file-hash manifest. It contains no answer key, generator, scorer, expected outcomes,
author analysis or reviewer results. Case directories are not real Git repositories;
observations.json supplies a separately constructed fictional current revision.
Recorded reproduction passes and receipts are synthetic claims. The reviewer may
run the provided read-only validator but must not execute reproduction commands,
perform external actions or alter fixtures.

Give a fresh reviewer only the generated packet directory. Do not give it this
README, RUBRIC.md, expected.json, generator source, scorer tests or prior author
conclusions. Have it follow REQUEST.md and save JSON outside the packet. Keep the
reviewer's input boundary explicit; shared filesystem access does not technically
isolate the answer key. Record any accidental exposure as contamination. Do not
rewrite expectations or the skill after seeing its response.

## Score after review

```sh
sha256sum -c milestones/handoff-review/FREEZE.sha256
python milestones/handoff-review/score.py /path/to/reviewer-answer.json
```

The scorer reports each field check and a total. It does not execute next_action.
Review rationale separately for case-specific evidence, preserved uncertainty
and unsupported proposed actions; cite excerpts rather than treating nonempty
text as correct reasoning. Preserve the original response, packet hashes and
frozen key with any eventual report. If a fixture or key is wrong, document it
and create a separately versioned run rather than repairing the score post hoc.

## Harness verification and review result

Ten new tests pass: frozen checksums; baseline validator states; repeatable packet
bytes and complete packet manifest; exact exclusion of key/source/results; unchanged
skill copies; refusal to overwrite; perfect and one-wrong-field scorer controls;
issue-set ordering; malformed/duplicate/missing submissions and duplicate JSON keys.
All 74 previous repository tests also pass. The subsequent fresh reviewer response
matched all 48 predeclared written fields. The [report](results/REPORT.md) preserves
that narrow interpretation, raw response, per-field scores, packet hashes and a
separate qualitative author review. No skill or answer-key changes followed the
review. This one tool-assisted sample does not establish comparative efficacy.

The Python harness and fixtures use only the standard library, temporary local
workspaces and original public project artifacts. They use no network or live
service operations and do not mutate real user repositories. MIT license applies.

One reviewer on eight deliberately constructed cases can expose a practical
failure, but cannot estimate generalization, real-world reliability, comparative
skill benefit, randomized efficacy or actual approval behavior. Allowing the
validator makes this a tool-assisted handoff review, not a test of unaided reading.
