---
name: recover-uncertain-operation
description: Reconcile a timed-out write that may have committed, distinguishing authoritative terminal evidence from stale or in-flight status and checking the retry contract within existing authorization.
---
# Recover an uncertain operation

Preserve the original operation identifier, exact target, payload, and any original idempotency key. Record non-secret evidence needed to distinguish this request from similar work. A timeout does not establish whether the write happened.

## Inspect evidence, not just a status label

Use the documented lookup for the exact operation when available. Classify the evidence:

- **Confirmed effect:** Authoritative evidence ties the intended committed effect to this operation. Do not repeat it. Verify any separately requested downstream completion before declaring the whole task done; acceptance or queued work is not final completion.
- **Confirmed terminal non-commit:** The service's documented contract establishes that this exact attempt ended without the relevant effect, cannot still commit later, and the observation is authoritative and fresh for that decision. This supports considering a retry, subject to authorization and service retry rules.
- **Unresolved:** A missing record, stale/cached negative, unsupported or failed lookup, uncertain freshness, pending work, or partial effect is not confirmed non-commit. Even a strongly consistent read of an absent effect does not by itself prove a still-running attempt cannot commit afterward. Do not convert repeated negative reads or elapsed time into a guarantee the service does not provide.

A status string such as `not_committed`, `failed`, or `cancelled` is insufficient without its documented semantics. A requested cancellation is not evidence of completed cancellation or rollback.

## Check the retry contract separately

A retry may be justified by confirmed terminal non-commit or by a documented idempotency contract that covers the uncertain request. For the latter, verify that the original attempt actually used the key, and check the applicable endpoint/version, account or other key scope, retention window, payload constraints, and treatment of concurrent requests and error responses. Reuse the same key and semantically identical request within that contract. Do not assume a correlation ID deduplicates effects, add a key retroactively, or change a key/payload to bypass a conflict. An expired or uncertain key window is not reliable duplicate protection. A replayed error is not proof that the requested effect succeeded.

Execution evidence and authorization are different gates. A known non-commit or valid key does not authorize a new target, changed payload, revoked action, payment, or other action requiring separate approval. Respect a denial; do not route around it as a timeout recovery.

Use the service's bounded retry/backoff guidance and the task's allowed time/call budget. Stop additional writes when their basis no longer holds. If the outcome remains unresolved, retain that label and explain the missing evidence; use authorized read-only reconciliation or request the necessary decision rather than inventing success. Existing permission to finish a task does not establish a service's consistency guarantees.

For contract rationale and synthetic review cases, see [sources](references/sources.md) and [regression examples](references/regression-examples.md). This skill is guidance, not a proof of production safety or model adherence.
