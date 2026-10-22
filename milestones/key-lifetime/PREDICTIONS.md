# Key-lifetime predictions (recorded before execution)

This additive study varies finite retention, not the existing stale-status files.
The corpus is a complete deterministic grid: faults none/before/after/denied;
status fresh/stale-negative/unsupported; key lifetime unlimited/1 logical tick;
recovery delay 0/1/2 ticks; and blind_retry/inspect_first/lifetime_guard.
All services support idempotency within its retention window. Each cell runs once:
216 cells, 72 per policy. These are constructed cases, not independent samples.

A committed key is valid while now < commit_time + lifetime. At exact expiry it
is no longer deduplicated. Recovery delay occurs after uncertainty and before
inspection/retry. Calls consume no ticks. Keys are stored only on commit; cache
hits do not renew expiry. The guard uses the first-attempt time as a conservative
lower bound, not hidden commit state. A fresh positive status always resolves.
A negative or unsupported status outside the guaranteed window is unresolved,
including a before-commit timeout where retry would actually be harmless.

Predicted totals:
- blind_retry: 72 runs, 6 extra commits, 0 unresolved, 108 calls.
- inspect_first: 72 runs, 4 extra commits, 0 unresolved, 138 calls.
- lifetime_guard: 72 runs, 0 extra commits, 10 unresolved, 128 calls.
- Every policy: 18 denied outcomes, each after exactly one call.
- Unlimited retention and delay zero each eliminate duplicate commits.
- At delay 1 and 2, blind retry duplicates all three after-timeout status modes;
  inspect-first duplicates only stale-negative and unsupported modes.
- The guard sacrifices completion, not just cost: six before-timeout cells and
  four after-timeout cells become unresolved at/after finite expiry.

These predictions follow from the declared model, not observations of services
or model agents. Saving a checksum before execution records local ordering; it
is not independently timestamped preregistration or proof against later edits.
