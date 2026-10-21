# Frozen pre-execution prediction

Frozen at 2026-10-21T23:45:44.033796+00:00. This document is written and hashed before executing the modified simulator or its tests. Manual code trace only. Baseline aggregate data were already known; this is not a blind preregistration.

## Intervention
Preserve the baseline policies, one-shot write faults, atomic commits, permanent conflict-free idempotency, and 16 cells × 3 shuffled orders (seeds 11, 29, 47). The only experimental knob is status_staleness in {0, 1}: how many supported status reads return the pre-commit value not_committed after a timeout-after-commit for the same operation ID. Unsupported status remains unknown and does not consume the stale-read budget. A successful retry does not refresh the observer; the budget decreases only on supported status reads.

## Predictions from manual trace
Each staleness level has 48 runs per policy.

- Staleness 0: blind_retry 6 duplicates / 0 unresolved / 72 calls; inspect_first 0 duplicates / 6 unresolved / 84 calls.
- Staleness 1: blind_retry 6 duplicates / 0 unresolved / 72 calls; inspect_first 3 duplicates / 6 unresolved / 90 calls.
- Only inspect_first with fault=after and status_supported=True changes. Each of the two idempotency cells adds 3 calls across seeds. The non-idempotent cell gains 3 duplicate commits; the idempotent cell remains duplicate-free. No outcomes or unresolved counts change.
- Every cell has 3 executions per policy per staleness value. Fault=none or denied uses 3 calls per cell. Blind retry uses 6 calls for before/after. Inspect-first before uses 9 calls except unsupported status plus no idempotency, which uses 6 and leaves all 3 unresolved. Inspect-first after: supported fresh uses 6 calls, supported stale uses 9; unsupported/idempotent uses 9; unsupported/non-idempotent uses 6 and leaves all 3 unresolved.

## Reviewer discrepancy
The external review as relayed by the parent predicted inspect-first duplicates 0→6. Independently tracing the code gives 0→3: only ONE of the 16 cells (after, supported status, non-idempotent) becomes newly duplicate-producing, repeated across 3 seed orders. Unsupported status still returns unknown and stops without idempotency. The idempotent supported-status cell retries but cannot duplicate. We will report disagreement rather than alter the intervention or count to match the review.

## Interpretation and stopping rule
Run the bounded corpus and tests, retain raw rows and per-cell aggregates, compare results to these fixed predictions, and report mismatches. No inference from shuffled order repetitions as independent observations; no statistical uncertainty or estimated deployment rates. This examines stale negative status, not partial writes, expiring keys, repeated faults, network failures on inspection, or LLM behavior.
