# Saved-trace policy attribution

This post-hoc, read-only supplement checks the four declared deterministic
policies against the retained recovery-composition traces. It supplements, rather
than replaces, the [original study](../README.md) and its saved-evidence checks.
It does not change a policy, repair the failed P5 prediction, establish policy
superiority, or run a new simulator or model experiment.

## What is checked

Use `combined_check.py` as the normal entry point. For each supplied row it:

1. Validates dynamics, evidence and metrics using the original
   [checker](../source/checker.py), after verifying its pinned SHA-256.
2. Reconstructs the public decision state and checks that the registered policy
   selected every recorded action. A dynamics error stops processing before
   attribution is attempted.

The separately coded replay follows the four rules in the
[pinned policy specification](https://github.com/EastonSell/after-the-timeout/blob/9dacb69be1f0ef7a79d5cb5f0a8869b1a1224087/studies/recovery-composition/source/model.py).
It uses received public evidence, call/write counts, public timing bounds and
action order. Because the original format has no separate public action timeline,
event/action markers in `hidden_trace` supply sequencing, including same-tick
order. Hidden effect contents, original fates, retry outcomes, evaluator counters
and pending queues do not enter policy selection. Shared specification mistakes
remain possible.

The standalone `policy_replay.py` assumes an already complete, dynamically valid
timeline. Deleting an initial wait from a retained fixture can still pass
standalone attribution; the combined entry point rejects it through dynamics
validation. A second regression relabels a `naive_inspection` trace as
`blind_keyed`: original dynamics accepts that intentionally mislabeled fixture,
while attribution rejects it. Neither mutation is an allegation about the saved
published data.

## Reproduce without new experiments

Python 3.10+ standard library only. From the repository root:

```sh
python -B -m unittest discover -s studies/recovery-composition/policy-attribution -v
python -B studies/recovery-composition/tools/reconstruct_payloads.py ../after-the-timeout-saved-review-001
python -B studies/recovery-composition/policy-attribution/combined_check.py ../after-the-timeout-saved-review-001/results-v1/rows.jsonl.gz
```

Choose a fresh, absent output directory with an existing parent. The existing
reconstructor verifies all manifest-listed inputs and outputs before creating
that directory, and refuses to overwrite an existing destination. It decodes
retained bytes, not regenerated scientific output. If an already reconstructed
archive is available, use its path in the final command instead. Do not delete or
replace original evidence to rerun these commands.

The new tests use retained counterexamples and hand-written decision fixtures;
neither these tests nor the combined command imports the simulator or calls an
API. Existing aggregate test commands are separate and may run model fixtures.

## Retained-data result and identity

On 23 October 2026, ten focused regression tests passed and the combined command
accepted all 86,796 rows in the retained archive, checking 338,660 decisions.
The input contained 800 distinct case identifiers and 3,200 observed case-policy
groups. Rows by policy were:

- `blind_keyed`: 72,840
- `capability_fallback`: 4,002
- `horizon_aware`: 3,944
- `naive_inspection`: 6,010

The original checker is pinned to SHA-256
`9751e07387d849ca8b99592ff7b655235d8596a226a06bd92a38095a7e5b8665`.
The retained `results-v1/rows.jsonl.gz` has 6,000,978 bytes and SHA-256
`b0f3db1fbd2f87593683646c0956bc8dfdaa264855e804b7110b2b31ae958281`.
Its identity is recorded in the unchanged
[payload manifest](../payload-manifest.json) at the reviewed base commit
[`9dacb69`](https://github.com/EastonSell/after-the-timeout/commit/9dacb69be1f0ef7a79d5cb5f0a8869b1a1224087).
The supplement references existing source and payloads; it does not duplicate
them or extend historical manifests to cover itself.

## Deliberate limits

`passed: true` means per-row dynamics/evidence/metrics and policy attribution
passed for the supplied rows. It does **not** independently establish cross-row
scheduler coverage, equality to a case manifest, group completeness or dataset
completeness. A subset or repeated valid rows can pass while reporting different
counts. The combined command does not authenticate an arbitrary supplied archive;
use the verified reconstruction and identity above for this retained-data result.
See the original [saved-group checker](../tools/check_saved.py) for its separate
study-level checks.

The original 423-versus-417 justified-completion result and failed P5 remain
unchanged. No production reliability, probability of incidents, language-model
behavioral efficacy, general policy optimality or recovery of missing historical
freezes follows from this supplement.
