---
name: recover-partial-batch
description: Reconcile a multi-item write after an ambiguous or partial response, distinguishing item evidence from whole-operation success before any retry.
---

# Recover a partially committed batch

Identify the intended item set and preserve each item's operation identity and
unchanged payload. A batch timeout is not evidence that every item failed.

Build an item ledger from the actual response contract:
- Confirmed committed: retain the returned item evidence; do not assume it proves
  absence of duplicate effects.
- Confirmed not committed: require a reliable negative that also rules out a
  future original commit. An old snapshot, missing list entry or absent page is
  not such a certificate.
- Unknown: leave explicitly unresolved unless the service's documented per-item
  retry guarantee covers this exact operation and payload through the full horizon.

If an authorized retry is justified, retry only the items that need it. Reuse
stable per-item idempotency identities where the interface actually supports
that scope. A batch request ID does not establish per-item deduplication, and a
finite cache window must cover late original execution, not just the retry time.
Do not invent idempotency support, terminal status or a cancellation guarantee.

Verify each acknowledged item. Report aggregate completion separately from
unresolved items and any known duplicate effects. If status stays uncertain and
no suitable retry guarantee exists, return the unresolved item ledger rather than
replaying the whole operation or asserting success. Further mutation, compensation
or expanding the operation requires the applicable authorization; this skill does
not provide it.

The [offline example](../../milestones/partial-commit/PROTOCOL.md) models a terminal
original attempt, durable keys, truthful capability metadata and successful
recovery writes. It demonstrates those contracts, not live reliability or model
adherence. Do not transfer its guarantee to untested service behavior.
