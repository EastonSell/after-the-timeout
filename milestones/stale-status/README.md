# Stale-status recovery: bounded follow-on milestone

A deterministic counterexample to treating a negative status lookup as authoritative evidence that an uncertain write did not commit. This is a separate milestone; the published Research Workflow Atlas baseline is unchanged. No network operations, credentials, user data, external model calls, or deployment actions are used.

## Result

| Stale reads after committed timeout | Policy | Runs | Duplicate commits | Unresolved | Calls |
|---|---|---:|---:|---:|---:|
| 0 | blind_retry | 48 | 6 | 0 | 72 |
| 0 | inspect_first | 48 | 0 | 6 | 84 |
| 1 | blind_retry | 48 | 6 | 0 | 72 |
| 1 | inspect_first | 48 | 3 | 6 | 90 |

All frozen aggregate and cell-level predictions matched. The change is concentrated in two cells:

| Policy | Fault | Supported status | Idempotent | Fresh → stale duplicates | Fresh → stale calls | Unresolved |
|---|---|---|---|---|---|---|
| inspect_first | after | true | false | 0 → 3 | 6 → 9 | 0 |
| inspect_first | after | true | true | 0 → 0 | 6 → 9 | 0 |

Each table cell above aggregates three order-seed repetitions. All other cells are unchanged. Full counts for all 64 policy × staleness × scenario cells are in `results/per_cell.csv` and `results/experiment.json`; all 192 execution rows are in `results/rows.csv` and the JSON.

The review relayed to this milestone predicted 0 → 6 inspect-first duplicates. Our independent pre-execution trace predicted 0 → 3 and the executable result agrees. Only one non-idempotent supported-status after-commit cell changes, repeated in three orders. Unsupported status remains unknown; it is not a stale negative. Idempotent retries do not duplicate. We did not change the intervention or reinterpret duplicate counts to fit the review.

## Frozen prediction and provenance

`PREDICTIONS.md` was written at 2026-10-21T23:45:44.033796+00:00 and hashed before executing the modified simulator or tests. Its SHA-256 is recorded in `PREDICTIONS.sha256`, the raw experiment JSON, and `MANIFEST.json`. This is a local pre-execution record, not a third-party timestamp or independent preregistration. The published baseline results and review hypothesis were known in advance.

`baseline/` contains exact copies of the baseline model, runner, configuration, raw results, and tests used for equivalence checks. `baseline_hashes_before.json` records every file of the original published tree before the experiment. `results/baseline_integrity.json` verifies every original file is unchanged and that no file was added or removed. The baseline was not run or edited in place.

## Exact intervention

The only new experimental factor is `status_staleness`, an integer in {0, 1}. A first write that commits and then raises a timeout arms that operation ID with this number of stale supported status reads. Each such read returns `not_committed` and consumes one unit; subsequent reads return current state. Unsupported status returns `unknown` without consuming the budget. A successful retry does not refresh the observer or reset the budget. Distinct operation IDs have separate budgets.

The policies are unchanged: inspect-first checks once after uncertainty, returns on committed, stops on unknown without idempotency, and otherwise retries once. Blind retry retries once without inspection. There is no new policy that detects freshness. We deliberately expose the existing policy's failure, rather than silently repairing it.

Corpus: four faults (none, before commit, after commit, denied) × supported/unsupported status × idempotent/non-idempotent = 16 scenarios. Each policy runs those same scenarios in orders shuffled with seeds 11, 29, 47 at both staleness values. Seeds randomize order only. Every execution uses a new service; these are repeated deterministic traces, not independent randomized trials, service workloads, or deployment-rate estimates.

## Interpretation and limits

Inspecting first does not by itself prevent duplicate effects. A stale negative can induce precisely the unsafe retry that inspection was supposed to avoid. Under this model, inspection still avoids duplicates on fresh supported lookups and intentionally leaves unsupported, non-idempotent uncertain outcomes unresolved. An unresolved after-commit case can already have a committed effect; unresolved is a knowledge-state measure, not a failed-write count.

Idempotency is independently protective here: both policies remain duplicate-free in every idempotent cell, even when status is stale or unsupported. This relies on permanent, correctly implemented, conflict-free keys. It does not establish production guarantees for expired keys, payload conflicts, racing writes, or broken deduplication.

Remaining assumptions are deliberately unchanged: one-shot write faults, atomic writes, no concurrent operations, exact operation IDs, and no timeout/error on status itself. Freshness is sufficient for the modeled fresh branch only because uncertain writes have already completed or failed before inspection; an in-flight operation in a real service adds a separate race. Partial commits, repeated faults, changing permissions, backoff, latency, token cost, real API semantics, and LLM adherence are out of scope. Calls count both writes and status reads, including denied or unsupported calls. Duplicate commits count extra records beyond the first for an operation; there is no severity weighting.

This milestone supports a narrow executable result, not a novel distributed-systems theorem or a recommendation that an unchecked status response authorizes retries. The next policy experiment could treat unverified-fresh negative status as unknown and compare explicit reconciliation against retries protected by a documented idempotency contract. That policy is not implemented or evaluated here.

## Reproduce and verify

Python 3.10+; standard library only. From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
PYTHONDONTWRITEBYTECODE=1 python run_experiment.py
sha256sum -c PREDICTIONS.sha256
```

22 tests passed: the 10 original baseline tests and 12 extensions covering deterministic stale-then-fresh reads, immediate freshness, stale duplicate behavior, idempotent retry, unsupported status and budget semantics, operation-scoped budgets, fault gating, invalid knob values, all-cell original-model equivalence, exact published-row equivalence, per-cell calls/duplicates/unresolved/denominators, and order-only seed invariance. Captured output is in `results/tests.txt`.

Rerunning writes fresh timestamps in the result JSON, so it intentionally changes the archival manifest hash. Scientific rows and aggregates should remain identical. `MANIFEST.json` records hashes for the delivered snapshot, excluding itself.

## License

MIT, inherited from the baseline project; see `LICENSE`. Code, predictions, and synthetic results require no external datasets. This milestone makes no additional literature-derived claim; the baseline's references remain in the unchanged baseline project documentation.
