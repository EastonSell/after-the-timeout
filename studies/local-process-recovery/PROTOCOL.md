# Local-process timeout recovery protocol v1

Written before implementation or measurement on 2026-10-24. Base public repository: EastonSell/after-the-timeout at bb7c59a61f95575edbd3c90719f69dffa1dfd5db. This is a new additive experiment, not a replacement or validation of every assumption of the terminal-read simulator.

## Question and scope
Can concrete loopback HTTP clients time out while real SQLite writes remain possible or have already committed, and which additional service contracts prevent duplicates in a deliberately selected set of schedules?

The apparatus is Python standard library only: a separate threaded HTTP service process, subprocess original clients, a driver/recovery client process, and a real file-backed SQLite database. The service binds only 127.0.0.1. All data are synthetic. No installs, credentials, external endpoints, remote writes, or changes to historical results. Fault gates deliberately hold original commit or response; they are not random Internet failures. The cached view is an actual earlier SQLite query retained unchanged, not arbitrary fabricated absence.

## Service contracts under test
- Unkeyed write: every admitted, unfenced attempt can append one effect.
- Retained idempotency control: identical key and canonical payload share one SQLite-transactional effect. Changed payload with the same key is rejected. No key expiry is implemented.
- Original-operation fence: a SQLite transaction changes a pending original to cancelled; the commit path checks that state in its own serialized transaction. A terminal certificate concerns that original operation, not all other writers. An associated authoritative count is read in the same transaction. This is an explicit abort/fence API, not a presumed time bound or a cryptographic certificate.
- A terminal flag and an independently stale item read are not an atomic terminal-absence certificate.

## Fixed primary matrix and literal predictions
Eight schedules, five repetitions each, at socket timeout values 0.08, 0.12, and 0.20 seconds: 120 planned trials. These are selected demonstrations and repeated engineering checks, not independent production samples or exhaustive scheduler exploration.

1. no_fault: original returns success; one final effect.
2. live_negative: hold original before commit; original client times out; authoritative read says zero while original pending; retry unkeyed; release original; two effects.
3. stale_negative: original commits, response held until timeout; retained pre-write cached read says zero; retry unkeyed; two effects.
4. same_key: hold original before commit; timeout; retry identical retained key/payload; release original; one effect, including a recorded deduplication.
5. terminal_fence: hold original before commit; timeout; atomic fence returns cancelled and zero current effects; retry unkeyed; release original; one effect, and the fenced original never commits.
6. terminal_with_stale_read: original commits before timeout; truthful original-terminal certificate says committed; an independent cached read still says zero; deliberately incorrect recovery retries unkeyed; two effects.
7. terminal_with_authoritative_read: original commits before timeout; terminal certificate and same-transaction current effect count show one; recovery stops; one effect.
8. concurrent_recoverers: original held, timeout, then fenced; two recovery clients both read terminal/current zero before either retry is admitted; both retry unkeyed; two effects even though the original remains fenced.

A separate regression checks same-key/different-payload rejection. It is not added to the primary matrix denominator.

## Measurements and failure criteria
Keep service and client event JSONL with wall-clock UTC nanoseconds, monotonic nanoseconds, PID, thread, and event identity. Keep client replies/errors, service stderr, final SQLite database plus SQL-derived JSON rows, trial result, environment and source hashes. Every final count comes from querying the real database after all admitted handlers finish, never from a predicted answer. Record actual timeout exceptions. Compare monotonic event order only on this one host. Event emission happens near the transaction boundary and is not the database commit timestamp.

The final read happens after every submitted operation has a terminal state and every held handler has exited, then the service is shut down and its database is independently reread. A bounded watchdog failure is an invalid trial, not a pass. Report every planned trial, including invalid or failed trials. No replacement trials or selective reruns in the primary denominator.

Predeclared checks: expected effect count; distinct service and original-client process IDs; real timeout in fault trials; original admission before timeout; for late-original schedules, timeout before original commit/dedup/suppression; exact retained zero snapshot in stale schedules; original remains cancelled after release in fence schedules; both zero observations precede the two recoverer writes in the concurrency control. One-thread interleaving or cross-process order that misses a required schedule makes the trial invalid.

## Bounds and execution
Per HTTP request: at most 3 seconds except the deliberately shorter original socket timeout. Fault gates and trial watchdog: 10 seconds. Primary run watchdog: 120 seconds. At most 120 primary trials. Output cap: 30 MB. The harness refuses an existing output directory. Unit/regression tests use their own temporary directories. Preserve red test output, final test output, all raw primary traces, protocol hash recorded before code, and a code/input hash manifest immediately before measurement. Hashes establish local content identity, not third-party preregistration timestamps.

## Interpretation rules and non-claims
Obtain independent code/evidence review before writing the final interpretation. A valid observed duplicate is a concrete counterexample for this implementation and schedule. Repeated one-effect controls support only the exercised implementation and schedules. No production realism, provider guarantees, distributed-host behavior, Byzantine safety, crash durability, statistical incident rates, exhaustive schedules, LLM efficacy, or formal general theorem is claimed. The fence and idempotency controls deliberately build strong contracts into this service; observing them work does not establish that an external service has them. No inference from a short quiet period to permanent absence. No claim that the earlier simulator's two-call timing theorem transfers unchanged.
