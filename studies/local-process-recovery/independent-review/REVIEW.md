# Independent review: bounded local-process timeout recovery

Review date: 2026-10-24. Scope: frozen implementation, protocol, tests, and the retained primary measurement in `../evidence/primary-run`. This review is by a separate reviewing agent in the same workspace, not a blinded outside laboratory or a third-party preregistration service. No implementation or primary-evidence file was changed by this reviewer. Review outputs and copied negative probes are confined to this directory.

## Decision

**The retained primary evidence is sufficient for the narrow, bounded result.** I found no invalid primary trial, omitted planned matrix cell, wrong database count, uncompleted write handler, source-hash mismatch, or contradiction of the selected-schedule predictions.

This is evidence of concrete duplicate effects after actual client timeouts in this loopback HTTP/SQLite apparatus, and working controls for the explicitly implemented retained-key and original-fence contracts in the selected schedules. It is not a general recovery theorem or a production guarantee.

The original standalone checker has two demonstrated completeness/provenance gaps. They do not invalidate the actual retained run because the independent audit checks the missing conditions directly and they hold for every primary trial. Preserve the measured source rather than retroactively modifying it. Ship or retain this audit, its script, and its negative probes with the results. Do not represent a successful standalone `verify.py` invocation as sufficient full-matrix validation.

## Independently established results

- Exact ordered matrix: 8 scenarios × 3 timeout settings (0.08, 0.12, 0.20 seconds) × 5 repetitions = 120 planned, indexed, and retained trial directories. No missing, repeated, replaced, extra, failed, invalid, or not-run primary trial was found.
- 105 fault trials have an actual original-client `TimeoutError` event after service admission. The smallest observed admission-to-timeout interval is 74.634843 ms. The other 15 no-fault trials have successful original responses without a timeout.
- Direct, read-only SQLite queries across the stopped databases found 225 attempts and 180 effects. No attempt remains pending. Every admitted operation has exactly one corresponding write-handler completion event before service shutdown, and every service exits with code 0.
- Each retained final in-service inspection has `active = 0` and matches the independently reread stopped database exactly, including effects, attempts, and keys. SQLite integrity checks pass in all 120 databases. All relevant stderr files are empty.
- Service, original-client, and driver PIDs are distinct in each trial. The 15 concurrent-recoverer trials each contain five distinct PIDs: those three plus two recovery clients. Spawn records and client-finish records agree with those identities.
- All 10 source files in the premeasurement hash manifest match both the current implementation and the preserved source-at-measurement copy. Both preimplementation protocol/plan content hashes also match.
- Observed primary duration: 36.261438 seconds. Retained primary files total 4,229,846 bytes including the summary at review time, below the declared 30 MB threshold. These are observed bounds, not a claim of hard global enforcement.

| Selected schedule | Trials | Direct SQL effects in every trial |
| --- | ---: | ---: |
| no_fault | 15 | 1 |
| live_negative | 15 | 2 |
| stale_negative | 15 | 2 |
| same_key | 15 | 1 |
| terminal_fence | 15 | 1 |
| terminal_with_stale_read | 15 | 2 |
| terminal_with_authoritative_read | 15 | 1 |
| concurrent_recoverers | 15 | 2 |

The resulting 60 duplicate-producing and 60 single-effect trials reflect the deliberately chosen matrix. They are not an estimated 50% incident rate. Among the 105 deliberately faulted trials, 60 produced two effects and 45 produced one.

## What the independent audit did

`audit_primary.py` imports none of `service.py`, `client.py`, `experiment.py`, or `verify.py`. It directly parses all retained JSON/JSONL and queries SQLite using a read-only immutable connection. It checks the complete matrix against a separately stated literal matrix, not against merely the directories found on disk.

For every trial it checks trace roles, stable per-role PIDs, positive timestamps/identity fields, monotonically ordered per-process traces, configured timeouts and gates, loopback address, subprocess spawn consistency, exact operation sets and final states, SQL-to-event effect identities, the canonical payload, empty stderr, clean shutdown, completion before shutdown, and agreement between final service inspection, database rows, per-trial result, and the primary index. It checks source content identity separately from result assertions.

Schedule-specific checks include:

1. Admission before the actual timeout, rather than treating any timeout as a valid fault trial.
2. For commit-held originals, gate wait before timeout, timeout before release, and release before the original commit, deduplication, or suppression event.
3. For response-held originals, commit and response-gate wait before the timeout.
4. A genuine current zero/pending read after timeout and before unkeyed retry in the live-negative case.
5. Exact cached snapshot identity: the retained `snapshot_taken` event is zero and precedes original admission; the `/snapshot` reply and later cached read reference that exact timestamp. The stale read occurs after timeout and before retry.
6. Truthful committed-terminal/current-one reads in both terminal-read schedules, followed by an independent stale read in the adverse case or no retry in the authoritative control.
7. A cancelled/terminal/zero fence after timeout and before release; the released original stays cancelled with no effect or original commit.
8. A retained key whose digest matches the canonical effect payload and whose single effect ID is shared by the committed retry and deduplicated original.
9. In each concurrent-recoverer trial, both independent clients receive cancelled/terminal/zero before the barrier and before either recovery write is admitted. Both subsequently make unkeyed writes while the original remains cancelled.

The complete machine-readable report is `primary-audit.json`, with 120 per-trial audit records and zero violations.

## Tests and falsification checks

I independently ran all 13 current unit/regression tests with temporary outputs redirected under this review directory. All passed. The test run includes all eight literal process outcomes, same-key/different-payload HTTP 409 rejection, existing-output protection, and three checker negative tests. See `independent-unit-tests.txt`.

I inspected the retained red tests and the two checker omissions caught before measurement. These local records support the documented development sequence, but hashes and logs cannot independently prove the historical time at which a prediction was conceived or establish third-party preregistration.

I independently reran two post-measurement implementation mutants, without changing their sources or the measured code:

- `ignore_idempotency_key`: the same-key process test fails specifically with `AssertionError: 2 != 1`.
- `disable_original_fence`: the fence process test fails specifically with `AssertionError: 2 != 1`.

Their independent logs are `mutation-ignore_idempotency_key.txt` and `mutation-disable_original_fence.txt`. These checks show that the one-effect assertions are sensitive to removing the relevant mechanisms, rather than merely reporting a hard-coded prediction. They are post-measurement controls, not additional primary trials.

The earlier `disable_key_deduplication` mutant is different: bypassing lookup while preserving unique-key insertion causes a pending operation and trial-watchdog ERROR. Its retained failure must not be described as a two-effect witness. The existing mutation summary initially listed this earlier error and the fence failure; use the named logs/edits, not an undifferentiated count of rejected mutants, when describing duplicate witnesses.

## Concrete findings and required qualifications

### 1. Standalone checker does not establish denominator completeness

A copied directory containing only `trial-000-no_fault`, with no matrix index or frozen manifest, is accepted by `verify.py` with exit code 0 and `trials = passed = 1`. The CLI scans only existing trial directories. This is not an observed missing-trial defect in the primary measurement, whose full denominator I verified independently. It is a limitation of what that command proves.

Evidence: `verifier-probes/incomplete_matrix/`, `verifier-probes/incomplete_matrix-verifier-output.json`, and `verifier-probes/results.json`.

### 2. Standalone checker does not establish exact snapshot provenance

Deleting `snapshot_taken` from a copied stale-negative service trace still yields exit code 0 with no violations. The original checker only checks the cached timestamp's relative ordering, not equality to an actual retained snapshot event. Every actual primary stale trial does have the exact pre-write zero snapshot, and the independent audit verifies the event and both response references directly. Again, this is a checker insufficiency, not a fabricated or missing snapshot in the primary run.

Evidence: `verifier-probes/missing_snapshot_event/` and its corresponding verifier output.

### 3. Global limits are not hard resource caps

The primary watchdog is checked before starting each trial, so an in-progress trial and cleanup can extend past the nominal global deadline. The output-size cap is calculated after the run, not enforced while writing. Per-call, gate, and trial checks substantially bound normal operation, but do not turn these global limits into hard operating-system kill or disk quotas. The measured run actually finished in 36.26 seconds and used about 4.23 MB. Report those observations and the check placement accurately.

### 4. Controls intentionally contain the needed service contracts

Retained idempotency and atomic original cancellation are built directly into serialized SQLite transactions. Success demonstrates these implementations and schedules, not the existence of such APIs in an outside provider. The fence concerns one original operation, not ownership of all future recovery work. The concurrent-recoverer adverse control correctly exposes that distinction.

## Interpretation limits

- Faults are deliberately selected application-level commit/response holds on loopback, not Internet packet loss, production load, stochastic latency, or a sampled failure distribution.
- All processes run on one host. Cross-process monotonic comparisons rely on that shared clock. Timestamps are emitted near operations, not by SQLite as authenticated commit timestamps.
- The cache is one intentionally retained earlier SQLite query. There is no distributed replica, quorum, or multi-region consistency implementation.
- The effect is a synthetic database row with the same intended payload, not an external payment, email, or other third-party side effect.
- SQLite serializes write transactions. Concurrent actors overlap in the read/decision phase; the result does not require simultaneous physical commits and should not be described as proving parallel database writes.
- No crash, power failure, forced restart, storage corruption, cancellation-during-crash, or durability-after-power-loss experiment is performed. Clean shutdown and `synchronous=FULL` alone do not establish crash durability.
- Idempotency keys do not expire. Eviction, expiry, cross-service key scope, changed-payload races beyond the explicit regression, and long-lived operational semantics are not exhaustively tested.
- No external service guarantee, Byzantine safety, exhaustive interleaving coverage, confidence interval, production incident rate, formal general theorem, or LLM effectiveness conclusion follows.
- The public reference repository is not the new experiment. I checked all 212 materialized reference files against the supplied Git-blob hashes and all matched; I did not independently reauthenticate the remote GitHub commit/tree. See `source-provenance-check.json`.

## Bottom line

The strong claim supported here is an existence-and-control result: concrete HTTP clients timed out after admission; selected later or already-committed SQLite writes caused real duplicate rows under unkeyed recovery; retained identical keys and an atomic original fence prevented duplicates only under their exercised conditions; stale evidence and multiple recovery actors defeated insufficient interpretations of a terminal signal. The complete 120-trial primary record supports that statement despite the disclosed standalone-checker limitations. No broader theorem or production assurance is warranted.
