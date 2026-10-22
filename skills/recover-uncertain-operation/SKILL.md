---
name: recover-uncertain-operation
description: Reconcile a timed-out write when the service may already have committed it; use only within the original authorized operation.
---
# Recover an uncertain operation
Record the original operation identifier and exact target. A transport timeout does not establish whether a write happened.
If a documented status lookup exists, inspect that operation before choosing another write. A confirmed intended effect resolves that operation, not necessarily the whole workflow; a confirmed non-commit permits retry only within existing authorization. An unknown status remains unresolved.
When the service documents idempotency, preserve the same key and payload across a retry. Never assume an operation identifier automatically provides deduplication. Without status or guaranteed idempotency, report the unresolved state instead of manufacturing success or repeating a possibly committed write.

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

A denial is not a transient transport error. Stop the denied action. Preserve the evidence needed for a human to reconcile it, excluding secrets.
For an offline demonstration, run the repository's tests and compare the blind-retry and inspect-first policies. The simulator is not a production client and proves nothing about a particular remote service's consistency guarantees.
