# Execution and review record

## Completed scope

- Preimplementation protocol and plan were recorded and hashed; eight initial process-outcome tests failed against the missing apparatus.
- Implemented the loopback HTTP/SQLite apparatus without installing dependencies or using credentials.
- Eight process outcomes passed; two newly added corruption tests first exposed verifier omissions and passed after premeasurement fixes. Thirteen apparatus/regression tests passed before measurement.
- Frozen source before the primary run; retained all 120 planned trials, no replacement or invalid trials.
- Independent raw-evidence audit checked every trial, exact denominator, SQLite contents, source identities, process separation and termination.
- Retained supplementary implementation mutants and all initial adverse receipts outside the primary denominator.
- Added a separate post-run verifier without changing producer/source-at-measurement or data. Seven initial omission/provenance mutation tests and four lifecycle corruption tests failed before their respective fixes. Final post-run suite: 12/12 passed. Original apparatus suite: 13/13 passed.
- Independent reviewer validated the final post-run verifier on complete evidence and deliberately corrupted copies. Final review found no material blocker to the bounded result.
- Existing aggregate repository tests: 92/92 across seven suites; terminal-race 5/5; composition 18/18.

## Explicit decisions

The primary data were not rerun after checker-only hardening. The independent raw audit had already established the relevant conditions in every retained trial; the post-run tool changes how that same evidence is rechecked, not the measurement or denominator.

The original producer and weak original per-trial checker remain frozen to preserve reproducibility. The preferred recheck is postrun/verify_run.py, with the separately written independent-review/audit_primary.py as another check. Neither is a cryptographic authenticity system.

The runtime and size targets were met in the actual run, but global checks are not hard operating-system resource caps. This limitation remains disclosed rather than changing the historical protocol or implying stronger enforcement.

One host and deliberate application-level gates were chosen for a safe, concrete existence-and-control experiment. This does not provide production, distributed-host, crash-recovery, or probabilistic reliability evidence.

During measurement and independent review, no publication, external mutation or third-party workload was performed. This publication copy subsequently packages those results for the reference repository; see PUBLICATION.md. Read-only source acquisition was verified separately by Git blob hashes. The source-reference materialization is not a full git checkout.
