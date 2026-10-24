# Supplemental independent review: post-measurement verifier

Date: 2026-10-24. This supplements `../REVIEW.md`; it does not replace the frozen primary measurement or revise its denominator.

## Decision

The final `postrun/verify_run.py` is an appropriate preferred whole-matrix recheck for this bounded experiment. It accepts the complete retained 120-trial matrix and rejects every omission/corruption probe exercised in this supplemental review. No remaining material blocker to the reported bounded result was identified. The original independent raw-data audit remains the stronger, separate corroboration of the full evidence record.

All changes reviewed here are post-measurement validation tooling. The primary apparatus, frozen source, and primary trial files remain unchanged. No new primary run is necessary to validate an evidence-checker correction.

## Independent executions

1. Inspected the post-run verifier and its tests directly. The first version adds a fixed 120-cell denominator, expected directory names, metadata/index/summary consistency, source-hash identity, and exact retained snapshot-event/reply identity checks around the frozen per-trial checker.
2. Independently ran the initial eight post-run tests: all passed. Independently ran its CLI against the primary data: passed, 120 audited, zero violations.
3. Re-exercised both earlier retained one-trial probes. Both were rejected for missing run metadata. Because that early failure alone cannot demonstrate a repaired snapshot check, also tested complete-matrix copies with the snapshot event removed or the cached reply timestamp changed. Both were rejected specifically for the intended snapshot/provenance defect.
4. Tested four further lifecycle corruptions against complete copied matrices: final active-handler count changed to 1; service-exit event deleted; exit code changed to 9; server-stop timestamp moved before handler completion. The initial post-run verifier incorrectly accepted all four. These were reported before sign-off and preserved under this directory.
5. Inspected the subsequent lifecycle-only patch. It compares the final service snapshot to the independently reread database with `active = 0`; cross-checks the final inspection response; requires the exact handler-completion multiset; requires completion before stopped before exit, exit code 0, no forced cleanup, and final inspection before shutdown.
6. Independently reran all 12 final post-run tests: all passed. Re-executed the same retained probes without replacing their input evidence. All four lifecycle corruptions now fail with the intended lifecycle checks. Both complete-matrix snapshot corruptions and the two earlier incomplete probes also fail. The unmodified primary matrix still passes with 120 audited trials and zero violations.

The final direct probe run has nine cases: one unchanged full-matrix acceptance and eight deliberately corrupted/incomplete evidence rejections. Its exact return codes and violations are in `final-probes.json`; full command output for each case is retained as `final-*-verifier.json`. `final-unit-tests.txt` contains the independent 12-test run. Initial results, exact copied corruptions, and the initially reviewed verifier source are retained rather than overwritten.

## Claim review

I read `REPORT.md` and the revised `README.md`. Their description remains appropriately limited to a single-host, deliberately engineered loopback HTTP/SQLite apparatus with synthetic effects and explicitly implemented service contracts. They do not assert a production failure rate, provider guarantee, exhaustive scheduler result, general theorem, or transferred simulator timing guarantee.

I independently recomputed both illustrative timelines from the raw original-client and service traces. Every reported millisecond value matches the cited event timestamps. The report explicitly labels these as near-boundary log timestamps rather than exact storage commit times or benchmarks.

The revised README correctly makes the post-run verifier the preferred CLI, retains the frozen checker for reproducibility, and explains that post-run mutation tests use the retained primary directory as their fixture. The final test count is 12, including four lifecycle regressions added after the first eight-test hardening step.

## Remaining qualifications

- This is still a consistency/evidence checker, not an authenticated or tamper-proof ledger. Coordinated fabrication of all logs, database rows, hashes, and metadata is outside its threat model.
- The post-run verifier uses the frozen per-trial checker; the independently written `audit_primary.py` does not import it and separately checked more trace details. Do not describe the wrapper as an entirely independent implementation of every check.
- Passing corruption tests demonstrates rejection of the specified faults, not exhaustive detection of every possible malformed artifact.
- Original conclusions and limitations stand: selected schedules, one host, explicit retained-key/fence contracts, no crash durability or real provider experiment, and observed rather than hard-enforced global resource caps.

The discovered checker defects were real, were reproduced before fixes, and were resolved in separate post-measurement code without changing favorable primary results. The corrected validator and the independent raw audit support the stated bounded empirical result.
