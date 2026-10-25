# SQLite crash/restart study: PRE-DATA review package

Status: apparatus and protocol only. No empirical crash matrix has run. There is
no admission record in this package and no result claim. Do not run `runner.py`
until an independent reviewer admits the exact frozen bytes.

This is an additive derivative of EastonSell/after-the-timeout at published
commit `d11df2f7fc9cd950d472c98b5aba107fb461080a`. The old HTTP/SQLite study and its
120 trials exclude crash/restart. Its unconditional table creation cannot reopen
the same database unchanged. We preserve all old sources and evidence and put
the restart experiment in this separate directory.

The new apparatus retains the transactional effects/key contract, but uses local
file/receipt IPC rather than HTTP. It can test an actual process crash before or
after the Python SQLite COMMIT call, followed by reopening the same file and one
explicit recovery write. It cannot measure socket timeouts, a crash *inside*
SQLite COMMIT, power loss, production reliability, or agent behavior.

## Review first

- `PROTOCOL.md` and `protocol.json`: fixed 24 rows, literal predictions, recovery
  rule, validity barriers, analysis, resource limits, and stopping conditions.
- `SOURCE_PROVENANCE.json`: exact local published-tree reconstruction and source
  identities; the local Git HEAD is the published parent, not d11df2f.
- `apparatus.py`: restartable SQLite contract. Foreign schemas are refused, not
  migrated or reset. Pending original attempts are never resumed automatically.
- `worker.py` and `runner.py`: unexecuted empirical lifecycle code. No sockets.
- `assess.py` and `verify_run.py`: raw evidence checks and full-denominator audit.
- `tests/` and `evidence/`: synthetic checks, retained failures, and baseline test
  results. These are correctness fixtures, not crash observations.
- `PRE_DATA_FREEZE.json`: all review-relevant content hashes. It establishes local
  content identity, not an externally timestamped preregistration.
- `upstream/`: unchanged source excerpts and prior publication provenance.

Run only the synthetic checks before admission:

    python -B -m unittest discover -s tests -v

These checks do not launch service subprocesses, open endpoints, send signals,
or execute matrix rows. Ordinary Python exceptions around COMMIT test code
ordering and rollback handling; they are explicitly not process-crash evidence.

## Later, only after independent admission

The reviewer supplies a separate JSON record containing `phase: PRE-DATA`,
`decision: ADMIT`, their identity in `reviewer`, and `freeze_sha256` equal to the
SHA-256 of `PRE_DATA_FREEZE.json`. A HOLD or stale identity is refused. This file
is an administrative gate, not proof of authorship or authority; the publication reviewer must
verify that the reviewer really is independent and has admitted these bytes.
Do not manufacture that record or infer admission from this README.

    python -B runner.py --admission /path/to/reviewer-admission.json --out /path/to/new-run
    python -B verify_run.py /path/to/new-run

The output must be a new directory outside this package and the historical
source/evidence directories. Never replace a failed run. Any correction after
data requires a new version, renewed review, and an explicitly separate result.
Do not publish before an authorized reviewer approves publication and independent review
of both the evidence and interpretation is complete.

## Excluded earlier output

The earlier unreviewed `timeout-overnight-evidence-20261025/fresh-fixed-matrix`
remains untouched and excluded. No outcome from it was used here for a
prediction, comparison, replication claim, or stopping rule. This package is not
a relabeling or rerun of that output. Historical packages remain byte-identical
under the retained before/after manifests.
