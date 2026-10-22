# Partial-commit recovery: frozen protocol v1

Purpose: compare explicit recovery rules for one synthetic three-item operation.
This additive study does not change earlier models. It is not an agent evaluation,
a production incident sample, a novelty claim, or a measured real-world rate.
All code and prose are original; no credentials, private inventories or logs are inputs.
Python 3.10+ standard library only; no network or account actions.

## Allowed cases and timing

The fixed item identities are a, b, c, each with an unchanged synthetic payload and
an operation-scoped key. Exactly one initial batch times out after committing any
of the eight subsets of these items. The original attempt is terminal before recovery:
no pending work, later commits, rollback or concurrent clients. Every recovery
batch succeeds synchronously and returns a complete item acknowledgement. There
is at most one status read and one recovery batch. This isolates partial-commit
and observation errors, not the late-original-commit and expiry studies.

The Cartesian grid is eight subsets × four status contracts × two idempotency
capabilities × four policies = 256 unique cells, each executed once. allowed_cases.json
lists every case explicitly. No random generator or prevalence weighting is used.

Status contracts:
- fresh: all three item records reflect current committed/absent state and carry
  a terminal, authoritative certificate. A negative justifies retry in this model.
- incomplete: only a is returned, with the same authoritative certificate. Missing
  b/c records carry no evidence of absence. The fixed mask is not a random sample.
- stale_negative: all three records say absent but are explicitly non-authoritative.
  These are old snapshots taken before the initial attempt. They cannot justify retry.
- unsupported: no records, and the interface advertises unsupported status.

Idempotency is either absent or per-item and durable throughout both calls. The
latter deduplicates unchanged operation/item/payload identities atomically at item
commit, including a replay of a partial batch. No batch-level idempotency, expiry,
key conflict, cross-operation key reuse, reordering effects or malformed evidence
is modeled. Public capability metadata is truthful. Identical requests are assumed.

## Policies and evidence boundary

All policies receive an observation (immutable public status records/capabilities),
not service state, original commit subset, or evaluator counters.
- blind_batch: skip status; retry all three, regardless of idempotency.
- missing_is_absent: skip reported committed items; retry every other item,
  incorrectly treating missing and stale-negative records as retry evidence.
- evidence_only: preserve authoritative positives; retry only authoritative terminal
  negatives; leave every other item unresolved, even when idempotency is available.
- capability_guard: preserve authoritative positives; retry authoritative terminal
  negatives and, only with durable per-item idempotency, every otherwise unknown item.

After a successful recovery acknowledgement, requested items are known committed.
A positive means at least one commit, never proof of exactly once. No policy can
observe duplicate counts. Evidence-only is an intentionally cautious ablation,
not a claim that ignoring available idempotency is optimal.

## Measurements

Each row records input case, status evidence, selected retry items, item commit
counts (evaluator only), true aggregate completion (all counts >= 1), exact-once
completion (all counts == 1), extra side effects (sum(max(count - 1, 0))), items
with duplicates, policy-reported complete, unresolved item identities/count, and
API calls (initial + optional status + optional recovery). Unresolved is epistemic:
it may coexist with actual complete or incomplete work. Reported completion can
coexist with duplicates. A fixed one-pass study cannot demonstrate eventual recovery.

## Pre-run expectations and falsification

1. Blind and missing-is-absent always report completion because recovery succeeds,
   but can duplicate previously committed items without per-item idempotency.
2. Evidence-only and capability-guard never produce duplicate side effects under
   these stated contracts. Both can leave unresolved items when evidence is missing;
   durable per-item idempotency removes that uncertainty for capability-guard.
3. Incomplete status does not justify retrying omitted items without idempotency.
4. Fresh terminal status lets both evidence policies achieve exact-once completion
   even without idempotency. Stale negatives alone do not provide that guarantee.
5. No reported-complete result has an uncommitted item. This does not imply exactly once.

Tests use a small declared set of contract examples, not the complete factorial
outcome grid. Tests, implementation, runner, case list and this protocol are hashed
in FREEZE.sha256 before review and outcome execution. A changed frozen file requires
an explicit revision and re-review; hashes establish local integrity, not an
independently timestamped preregistration. Results are not in the freeze. Review
must precede the first runner invocation. Record any deviations in REPORT.md.

## Prospective amendment, 2026-10-22, before factorial execution

Independent review identified that a failed prediction could abort before saving
case evidence. The original freeze is retained in FREEZE.v1.sha256; its digest is
22e222fa1005a86728954a7fe6e81782eada8f8986c061b947ffbf7304a7b566.
The revised runner exclusively reserves a fresh output directory before execution,
writes a running marker, and flushes/fsyncs each completed row to rows.jsonl. It
atomically publishes experiment.json with every row and prediction result before
returning a failed assertion/nonzero exit. Existing output is never reused.
An interruption leaves the running marker and any completed raw rows; a truncated
last line is not a completed row. This is process-interruption resilience, not a
power-loss filesystem guarantee. --out selects a fresh reproduction destination.

Regression tests deliberately inject a false prediction, an interruption and an
existing output directory into a one-row synthetic runner harness. These are
retention checks, not executions of the outcome grid. All prior policy/contract
fixtures remain unchanged. The updated freeze covers this amendment and revised
runner/tests before review and outcomes.

The policies have unequal call counts; this is not an equal-budget efficiency
comparison. Non-blind policies make one status call even for unsupported status.
The status-supported metadata could allow an optimized implementation to skip it,
but that optimization is outside this fixed comparison. No latency/cost or real
failure-frequency inference is made from these synthetic call counts.
