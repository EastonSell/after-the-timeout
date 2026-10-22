---
name: recover-uncertain-operation
description: Reconcile a timed-out write that may have committed, checking authoritative terminal evidence or the original request's retry contract within existing authorization.
---
# Recover an uncertain operation

Preserve the original operation identifier, exact target and service scope, payload,
and any original idempotency key. Retain non-secret evidence that distinguishes
this request from similar work. A transport timeout does not establish whether a
write happened.

## Inspect evidence, not just a status label

Use the documented lookup for the exact operation when available. Classify the
evidence before treating it as a basis for another write:

- **Confirmed effect:** Authoritative evidence associates the intended committed
  effect with this operation. Do not repeat that effect. Verify separately requested
  downstream completion before declaring the whole workflow done; accepted or
  queued work is not final completion.
- **Confirmed terminal non-commit:** The documented contract establishes that this
  exact attempt ended without the relevant effect, cannot still commit later, and
  the observation is authoritative and fresh for this decision. This supports
  considering a retry, subject to authorization and service retry rules.
- **Unresolved:** Missing records, stale/cached negatives, unsupported or failed
  lookups, uncertain freshness, in-flight work, or partial effects do not establish
  terminal non-commit. Even a strongly consistent absent-effect read does not prove
  that a still-running attempt cannot commit afterward. Repeated negative reads or
  elapsed time cannot supply a guarantee absent from the service contract.

A label such as `not_committed`, `failed`, or `cancelled` is insufficient without
its documented semantics. A cancellation request is not confirmed cancellation
or rollback. A terminal failure may still leave partial effects.

## Check the retry contract separately

For ordinary service writes, a retry needs either confirmed terminal non-commit
or a documented idempotency contract covering the uncertain request. The latter
can justify retry even without a status lookup or known non-commit. For a
key-based contract, verify:

- The original attempt actually used the key, on the applicable endpoint/version
  and account, region, or other documented key scope.
- The guaranteed retention window covers the retry and any original request that
  can still arrive or complete. A key valid only at retry time need not cover a
  later original; unknown or expired protection is not sufficient.
- Payload-equivalence constraints, concurrent/overlapping request handling, and
  error/partial-result semantics preserve the required duplicate protection.

A documented operation-level idempotency contract can instead justify keyless
replay of the same endpoint/version, scope and semantically identical request
when its intended-effect, failure/partial-result and concurrency/precondition
guarantees make repetition safe. An HTTP verb alone is not proof.

For key-based replay, reuse the original key and semantically identical request
within that contract.
A correlation ID is not automatically a deduplication key. Adding a key after the
original cannot retroactively protect it; changing a key or payload must not bypass
a conflict. Replayed errors or duplicate suppression do not prove successful
completion. Confirmed terminal non-commit does not universally require a key.

## Content-addressed Git objects

Creating an exact Git tree is narrower than sending a message or moving a branch:
identical immutable tree contents have the same object identity. Preserve the
timeout receipt and frozen path/mode/object-ID manifest; reconcile by the
independently expected tree hash. A failed lookup alone is not proof of absence.
An authorized reconstruction may use smaller bottom-up tree requests only if it
preserves the exact final tree. Verify the complete result before the separate
commit and branch-publication steps. Commit timestamp defaults and mutable refs
do not inherit this retry argument. See the [worked recovery and offline
planner](references/content-addressed-tree-recovery.md) for assumptions, checks
and limits. Deterministic identity is not permission to retry a denied action.

## Authorization, stopping and reporting

Execution evidence and authorization are different gates. Known non-commit,
a valid key, or deterministic object identity does not authorize a new target,
changed payload, revoked action, payment, or another separately approved step.
A denial is not a transient transport error. Stop the denied action. Preserve the evidence needed for a human to reconcile it, excluding secrets.

Use the service's bounded retry/backoff guidance and the task's time/call budget.
Stop additional writes when their basis no longer holds. If neither recovery
basis applies, preserve the unresolved label and use authorized read-only
reconciliation or request the necessary decision rather than inventing success.

Read the [contract sources](references/retry-contract-sources.md) for rationale
and the [regression examples](references/regression-examples.md) for authored
expectations. Static package checks and offline simulations are not measured
agent compliance or a proof of production safety. The repository simulator is
not a production client and establishes no particular remote service's consistency
guarantees.
