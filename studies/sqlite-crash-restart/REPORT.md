# A lost reply across process restart

## What was observed

The single admitted run executed all 24 planned trials on 2026-10-25. All 24 met
the declared scheduling and evidence checks, with no invalid, failed-prediction,
or not-run rows. Each of six cells contains four trials. These are deliberately
selected implementation checks, not 24 independent production incidents.

The original request asks for payload A. Recovery sends A in the no-key and
same-key conditions, or a changed payload B in the conflict control.

| Crash barrier | Recovery request | Planned / valid | State before recovery | Final effects | Recovery response | Original A outcome |
|---|---|---:|---|---|---|---|
| Before COMMIT call | No key, A | 4 / 4 | No effect or key | One A | 200, committed | A exactly once in 4/4 |
| Before COMMIT call | Same key, A | 4 / 4 | No effect or key | One A | 200, committed | A exactly once in 4/4 |
| Before COMMIT call | Same key, B | 4 / 4 | No effect or key | One B | 200, committed | A absent in 4/4 |
| After COMMIT returned | No key, A | 4 / 4 | Original A retained | Two A effects | 200, committed | A duplicated in 4/4 |
| After COMMIT returned | Same key, A | 4 / 4 | A and its key retained | One A | 200, deduplicated | A exactly once in 4/4 |
| After COMMIT returned | Same key, B | 4 / 4 | A and its key retained | One A, no B | 409, rejected | A retained exactly once in 4/4 |

Every cell has zero invalid, zero not-run, and zero prediction-failure rows.
The complete case list and per-row results are retained, including the expected
duplicate and incomplete-original-goal controls. None was replaced or rerun.

## Why the changed-payload control matters

After the original transaction committed, the retained key bound its payload A.
The same key with B was rejected in all four selected trials, with A unchanged.

Before the original transaction committed, neither its effect nor its key binding
survived. Recovery could bind that key to B and return 200. Each of those four
trials ended with one effect, but none contained the originally requested A.
Those outcomes matched the frozen control prediction; they were not successful
completion of the original goal.

Likewise, the four after-COMMIT no-key trials completed A but duplicated it.
Counting successful requests, nonempty databases, or matching predictions would
hide these distinctions. The retained measurements therefore separate total
effects, copies of A, presence of A, exactly one A, and response status.

## What makes this process-crash evidence

The original worker admitted its operation, then wrote the effect, key, and
terminal attempt state inside a SQLite transaction. An explicit barrier blocked
either before the Python `db.commit()` call or after it returned. The barrier
receipt carried the exact trial nonce, process ID, actor, and phase.

The driver checked that receipt, sent SIGKILL to its owned worker, and observed
the worker's -9 exit before copying the database/journal crash image or starting
recovery. A distinct process reopened the same database and performed exactly
one predeclared recovery write. After that process exited, SQLite was reread
independently. No original response receipt existed in any trial.

The checker additionally reopened a temporary copy of each retained crash image
to verify the pre-recovery database state without changing the original image.
The independent implementation reviewer independently examined all 24 final databases, copied crash
images, payload counts, integrity checks, and raw kill/restart receipt order.

The pending original attempt remains pending after the before-COMMIT crash.
It is not converted into a terminal-absence certificate. The apparatus has no
automatic resume queue or competing writer; confirmed process death prevents
that original worker from later committing. This does not establish that a
remote service has stopped working after a timeout.

## Source and evidence custody

The experiment was frozen before data at SHA-256:

`990faf455cece27c437546899533fb1e1c90a508c5429c13df45fbd20275cdaf`

An independent-of-implementation reviewer admitted those exact bytes before the
single matrix run. The same reviewer performed a separate post-run raw-evidence
audit. These local records establish documented review and content identity;
they are not externally timestamped preregistration or third-party attestation.

The frozen auditor verified all 560 files in the run's output manifest. The
original 38-file source freeze and 12,122 historical non-cache files were also
rechecked unchanged. No result from the earlier excluded unreviewed matrix was
used in this run or its analysis.

Before data, 30 synthetic correctness tests passed and three targeted faulty
store variants were rejected. The historical aggregate also passed 92 tests
across seven suites. Those software checks are separate from the 24 empirical
process-crash trials. Their exception-based fixtures were not relabeled as
crashes or added to the empirical denominator.

For public release, internal paths and coordination-role labels were redacted
from metadata only. Original and public SHA-256 identities are recorded
separately. Original admission was not changed to pretend it admitted the
redacted derivative. The public auditor rechecks the unchanged scientific
evidence through those explicit identity mappings.

See [REVIEW.md](REVIEW.md) and [PUBLICATION.md](PUBLICATION.md) for review scope,
archive layout, exact original manifests, and publication transformations.

## Measured bounds

- Environment: Linux kernel 6.18.55, Python 3.12.14, SQLite 3.53.1; one host.
- SQLite: rollback journal mode DELETE and synchronous FULL, checked by receipts.
- Execution: 24 sequential trials, 48 service-process lifetimes, at most one
  service worker plus the driver at a time.
- Runner loop: 2.923 seconds. External supervisor elapsed time: 3.027 seconds.
- Final retained run: 4,397,608 bytes, including its final hash manifest.
- External limit: 190 seconds, with owned-group cleanup and child reaping.
  It did not time out; no owned child or process group remained afterward.
- Frozen cooperative limits: 180 seconds for the run, 12 seconds per trial,
  32 MiB inter-row output abort threshold. Workers also had 5 CPU seconds,
  512 MiB address space, and a 1 MiB per-file limit.

The cooperative deadlines and output threshold are not hard real-time or total
filesystem quotas. The external supervisor bounded this admitted invocation.
Observed runtime is a resource receipt, not a performance benchmark.

## Interpretation limits

The four after-COMMIT no-key duplicates are concrete counterexamples for this
implementation and these schedules. The keyed controls show the intended
retained transactional binding working under the exercised conditions.

This study cannot establish general crash safety, a provider contract, a failure
rate, or language-model/agent recovery efficacy. It uses synthetic file/receipt
IPC, not HTTP requests or measured socket timeouts. The old HTTP service is not
silently claimed to restart unchanged.

The barriers lie outside the COMMIT call. They neither kill during SQLite's
internal commit protocol nor locate its internal commit point. SIGKILL ends an
application process, not the OS or power supply. No claim covers power-loss
durability, unreliable storage, disk corruption, replication, partitions,
concurrent recoverers, key expiry/loss, automatic replay, or other providers.

SQLite's documented [atomic commit mechanism](https://www.sqlite.org/atomiccommit.html)
and [synchronous settings](https://www.sqlite.org/pragma.html#pragma_synchronous)
motivate the setup. They do not substitute for measurements of any excluded
failure mode. Four repetitions per cell cannot justify a universal guarantee.
