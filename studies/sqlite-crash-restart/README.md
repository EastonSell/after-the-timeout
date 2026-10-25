# SQLite crash/restart recovery

A committed write can lose its reply when its process dies. In this small local
experiment, retrying without a key then created a duplicate; retaining the same
key and payload kept one effect. A separate changed-payload control shows why
counting one effect is not enough to establish that the original task finished.

The [report](REPORT.md) covers all 24 planned trials: six selected conditions,
four repetitions each. All schedules were valid and matched their literal
predictions. That includes four intended duplicate outcomes and four outcomes
that left the original requested payload absent. "Prediction matched" does not
mean "recovery succeeded."

Scope: actual Linux service-process SIGKILL and SQLite reopen, synthetic requests,
one host, file/receipt IPC, and barriers immediately before the Python COMMIT call
or after it returned. No HTTP socket timeout, power loss, distributed service,
production rate, or model/agent efficacy claim is made.

## Read and inspect

- [Report and complete cell denominators](REPORT.md)
- [Frozen pre-data protocol](source/PROTOCOL.md) and [24 literal cases](source/protocol.json)
- [Independent review summary](REVIEW.md)
- [Publication transformations and original identities](PUBLICATION.md)
- [Restartable store](source/apparatus.py), [worker](source/worker.py),
  [bounded runner](source/runner.py), and [raw-evidence checker](source/assess.py)
- [Frozen source identity](source/PRE_DATA_FREEZE.json)

The earlier HTTP/SQLite study remains unchanged. Its 120 trials did not test
crash/restart. An additional earlier, unreviewed fixed-matrix output remains
excluded from this study and from every claim here.

## Unpack and verify retained evidence

Python 3.10+ standard library; the recorded execution used Python 3.12.14 and
SQLite 3.53.1 on Linux. No installation, account, credential, or endpoint is needed.

From this directory:

    sha256sum -c PUBLIC-SHA256SUMS
    tar -xzf retained-evidence.tar.gz
    python -B verify_public_derivative.py
    cd source
    python -B -m unittest discover -s tests -v

The archive contains a disclosed metadata-redacted derivative. Original/public
hash pairs and a separate public source map identify every transformed file;
numerical outcomes, request/response traces, and database bytes are unchanged.
The original admission still names the original freeze, not the derivative.

The archive adds only `run/`, `execution/`, `review/`, `source/evidence/`, and
`source/upstream/`. It does not overwrite the ordinary source files. It retains
raw database and journal images, all 24 traces and outcomes, source-at-run copies,
admission, synthetic failures and controls, supervisor receipts, and metadata-redacted
independent post-run review records. The public auditor checks all 24 rows, original/public identity pairs,
and final/recovered SQLite state. The historical auditor is retained as source,
but its original-byte checks do not apply directly to redacted metadata. The independent review did not rely on the
runner's summary alone.

The frozen source README and protocol deliberately still say PRE-DATA: those are
the exact pre-measurement documents, not the current status of this completed
study. This README and REPORT.md describe the later executed and reviewed run.

## New replication

A new run is a separate experiment, never a replacement for these 24 rows.
The public metadata derivative is not the originally admitted byte set. Its
`PUBLIC_DERIVATIVE_SOURCE.json` binds its source identities without backdating
admission. The original `PRE_DATA_FREEZE.json` remains the original manifest.

An authorized replication should prepare a new source freeze and obtain new
independent admission for that exact version before invoking the retained
runner. Do not reuse the original one-run admission or claim its hashes validate
redacted metadata. The core store, worker, runner and scientific checker code
are retained unchanged; their synthetic tests can be run without a matrix run.

Use a fresh output outside all source and historical evidence directories and an
external supervisor equivalent to the recorded 190-second owned-process bound.
The retained supervisor script uses portable placeholders for private paths and
is a historical record, not a ready-to-run command. No quiet period establishes
permanent remote absence. Preserve failures and every invalid/not-run row.
