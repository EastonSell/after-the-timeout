# Concrete timeout recovery failures and controls

## Result

The experiment reproduced real duplicate database effects after actual loopback HTTP client timeouts. It also reproduced two ways that a truthful terminal statement can be insufficient: pairing it with an independent stale read, or allowing two unfenced recovery writers to act after the original has been cancelled.

The complete primary run contains 120/120 predeclared trials: eight selected schedules × three socket timeouts (80, 120, 200 ms) × five repetitions. Every retained trial matched its predeclared effect count and required event ordering. There were no failed, invalid, omitted, or replacement primary trials. “Matched” includes the deliberately adverse outcomes; it does not mean every recovery was safe.

An independent audit, which does not import the implementation or its verifier, checked all raw traces and stopped databases. It found 105 actual post-admission timeout exceptions, 225 attempted operations, 180 persisted effects, and zero pending attempts or unfinished write handlers. All primary service processes shut down cleanly. Each ordinary trial had three distinct process IDs (driver, service, original client); each two-recoverer trial had five.

| Selected schedule | Trials | Final effects per trial | Observed outcome |
|---|---:|---:|---|
| No injected fault | 15 | 1 | Normal response and one persisted effect |
| Current negative while original remains live | 15 | 2 | Retry and original both commit |
| Stale negative after original committed | 15 | 2 | Retry duplicates the committed original |
| Identical retained key and payload | 15 | 1 | Retry commits; late original deduplicates |
| Atomic original fence, then one recovery writer | 15 | 1 | Retry commits; late original is suppressed |
| Truthful original-terminal flag plus stale item read | 15 | 2 | The terminal flag does not refresh the stale read |
| Terminal flag and same-transaction authoritative count | 15 | 1 | Recovery observes the existing effect and stops |
| Two recovery writers after an original fence | 15 | 2 | The original stays cancelled; both recoverers commit |

These are 120 repeated engineered trials, not independent production incidents. The 60 duplicate-producing trials and 60 one-effect trials reflect the chosen matrix, not estimated rates.

## A concrete trace

In the first current-negative trial, relative to the original client's request:

- 3.946 ms: the service admits the original.
- 81.461 ms: the original client records a socket TimeoutError and closes its connection.
- 131.361 ms: the authoritative database read reports zero effects and original state pending.
- 137.254 ms: the retry's SQLite effect commits.
- 140.852 ms: after the fault gate is released, the original's separate effect commits.
- The stopped database contains both effects.

In the corresponding original-fence control, the fence reports cancelled and zero effects at 127.906 ms; the retry commits at 132.305 ms; the late original is suppressed at 134.061 ms. The stopped database contains one effect.

These timestamps are host-monotonic event-log times near the relevant operation boundaries, not exact storage commit timestamps or performance benchmarks. Full event identities and additional examples are retained in evidence/representative-timelines.json, with primary raw logs as the source of truth.

## What this establishes

1. The failure mechanisms are executable with real processes, sockets, timeout exceptions, transactions and persisted rows, rather than only enumerated in a simulator.
2. A current negative observation does not establish that an admitted original cannot commit later.
3. A stale negative can contradict an already committed original even after a genuine timeout.
4. In this implementation and these schedules, a retained payload-bound atomic key prevents duplicate effects, and an atomic original-operation cancel fence blocks that original's late commit.
5. The scope of a terminal statement matters. Original terminality does not make another read fresh or prevent other recovery actors from appending effects.

The controls intentionally implement strong service contracts. Passing their tests does not show that an external provider supplies those contracts.

## Verification and review findings

- 13 new tests passed before measurement and again independently: eight process scenarios, payload-conflict rejection, existing-output protection, and three corrupted-evidence checks.
- The original eight outcome tests first failed against an unimplemented stub. Two later evidence tests exposed missing checks, then passed after those checks were added, all before the source freeze.
- Supplementary mutation tests disable the original fence or ignore idempotency keys. Both cause the relevant process test to fail specifically with two effects rather than one. A different earlier deduplication mutant caused a pending-operation watchdog error instead; that adverse receipt is also retained and is not a duplicate witness.
- Existing repository aggregate: 92 tests across seven suites passed. The prior terminal-race suite (5 tests) and recovery-composition suite (18 tests) also passed. Animation and unrelated later standalone suites were not run; this is not a claim that every repository entrypoint was tested.
- Independent auditing verifies the exact 120-cell denominator, source identities, process separation, timeout/admission order, actual cached snapshot identity, expected SQL states/effects, reply consistency, complete handler drainage, clean exits, and database agreement after shutdown.

The independent review found two limitations in the original per-trial checker. Its CLI accepts a directory containing only one valid trial, and a copied stale-negative trace still passes after the snapshot_taken event is removed. Neither omission occurs in the primary data. The independent auditor explicitly checks both conditions and passes the complete primary evidence. The measured code is retained unchanged; verify.py is not presented as sufficient whole-run or snapshot-provenance verification. A separate post-run verifier, postrun/verify_run.py, is now the preferred recheck. Its 12 tests accept the complete primary record and reject partial/missing or denominator-shrunk matrices, a missing snapshot event, inconsistent cached/snapshot-reply identities, a source-hash mismatch, active handlers at the final read, a missing or unclean service exit, and shutdown recorded before handler completion. Seven initial corruption tests and four additional lifecycle mutation tests failed before their respective fixes and passed afterward. Independent review exposed those lifecycle omissions in the first post-run version; that version and its adverse probes are also retained. This tooling improvement was made after measurement and does not change the primary denominator or frozen producer.

## Bounds, deviations and limitations

The primary run took 36.2614 seconds and retained 4,229,846 bytes including its summary, below the declared 120-second and 30 MB targets. The code checks the run time between trials and output size after execution; these are not hard, continuously enforced global caps. Individual requests, gates and trial waits are bounded, but cleanup can extend a trial's wall duration. The frozen protocol's bound wording should not be read as a hard-kill guarantee.

This is one host, one tiny service, one SQLite database, one synthetic item, and selected gate-controlled schedules. The cached negative is an actual earlier database read held unchanged by the apparatus; there is no independently implemented replication system. The service has no authentication and must not be exposed beyond loopback. HTTP timing and SQLite serialization here do not establish distributed-system behavior.

No service crash, machine crash, disk loss, restart durability, packet-level fault, network partition, key expiry, batch partial commit, third-party provider, adversarial server, or language-model policy execution was tested. The original fence is a real service mutation with an explicitly implemented atomic cancel contract, not a magical status read, a cryptographically authenticated certificate, or a known-time-bound theorem.

No statistical reliability estimate, production incident rate, new general theorem, literature novelty, exhaustive scheduler coverage, or transfer of the prior simulator's two-call guarantee follows. Completion is determined after all submitted operations and handlers have drained and the service has stopped, not from a short quiet interval. A future service with other writers or hidden asynchronous work needs a different completion boundary.

## Provenance and retained evidence

Reference public repository: EastonSell/after-the-timeout at bb7c59a61f95575edbd3c90719f69dffa1dfd5db. The apparatus is additive and does not modify its models or historical results. A separate source materialization contains 212 text files verified against their Git blob identities; large compressed payloads and animation binaries were not copied.

PROTOCOL.md and the implementation plan were hashed before implementation. evidence/primary-run/frozen-input.json records exact source hashes before measurement; evidence/source-at-measurement preserves matching bytes. These establish local content identity, not an externally timestamped preregistration or tamper-proof provenance.

All primary trial directories retain client/service/driver JSONL events, final SQLite files, SQL-derived results, responses, case identities and stderr. Independent review artifacts and negative probes are retained separately from the primary denominator. No experiment request or synthetic workload was sent to an external service. Repository access during measurement and independent review was read-only. This publication copy adds the reviewed apparatus and retained evidence to the reference repository; see PUBLICATION.md for packaging, path-only redactions, and preserved content identities.
