# Client-observation provenance supplement

This additive, post-hoc checker closes a gap in the local-process study's original
whole-matrix verifier. The earlier checker accepted a copied fault trace even when
its timeout exception was changed from `TimeoutError` to `ConnectionResetError`,
or its declared 0.08-second socket timeout was changed to 999 seconds. Accepting
those mutations did not show that the retained primary evidence was wrong; it
showed that the checker did not verify those claims.

`verify_client_run.py` first requires the existing whole-matrix checks to pass,
then binds each original client's request, process identity, observed outcome,
completion receipt, and saved result to the declared scenario. For the two
concurrent recoverers, it additionally checks their exact terminal-zero read
receipts, barrier ordering, unkeyed write requests, successful replies, and saved
results against the already-verified database attempts.

The original producer, protocol, per-trial verifier, post-run verifier, primary
measurements, archive, and historical manifests are unchanged. This is not a new
primary experiment or a change to the original 120-trial denominator.

## Prepare the retained fixture

Python 3.10+ and its standard library suffice. Use a fresh, disposable checkout.
The expanded `evidence/primary-run` fixture is intentionally **not** an ordinary
Git directory: it must first be restored from the hash-verified retained archive.
From the repository root:

```sh
cd studies/local-process-recovery
sha256sum -c ARCHIVE-SHA256SUMS
tar -xzf retained-evidence.tar.gz
sha256sum -c ARTIFACT-SHA256SUMS
```

Do not extract over an edited or partly restored evidence directory. The commands
above verify the unchanged published archive and its historical members; the new
supplement is not retroactively included in those manifests. Tests copy the
expanded primary fixture into temporary directories and never edit the original.

## Check and test

From `studies/local-process-recovery`, after preparing the fixture:

```sh
python -B client-provenance/verify_client_run.py evidence/primary-run
python -B -m unittest discover -s client-provenance -v
python -B -O client-provenance/verify_client_run.py evidence/primary-run
```

The CLI emits JSON and exits 0 only if both verification stages pass. It returns a
nonzero exit and a failed JSON report for the tested missing/corrupt database and
malformed-source-manifest cases, instead of abandoning the report with a traceback.
The unchanged retained matrix passes with 120 audited trials and 150 validated
client lifecycles: 120 originals plus two recoverers in each of 15 concurrency
trials. The 23 regression tests include malformed and mismatched receipts, a
coordinated non-timeout rewrite, optimized-Python rejection, and acceptance of a
legitimate parent/child scheduling variation.

To check a fresh run from the unchanged apparatus, pass its new directory instead
of `evidence/primary-run`. The existing experiment command writes its source/input
freeze before its first trial and refuses existing output directories. Keep failed
trials; do not replace them to improve the denominator. The original apparatus,
historical post-run, and repository aggregate tests retain their separate commands
in the parent study and repository reproduction guides.

## Boundaries

- This checks consistency and declared observation provenance in saved evidence.
  It does not authenticate logs, prove actual OS execution from bytes alone, or
  resist coordinated fabrication of every source, trace, and database record.
- Process identities must be distinct within a trial, not across trials. A parent
  can record a spawn receipt after its child has already started; the checker
  validates the receipt's identity without assuming the opposite scheduler order.
- Monotonic event ordering is used only within the existing single-host study.
  Timeout configuration and exception identity do not establish a hard wall-time
  latency guarantee, a distributed clock, or a production failure probability.
- This supplement adds client checks, not a complete hostile-input parser or a
  general validator for arbitrary future scenarios. It inherits the original
  fixed matrix and existing verifier's other checks and limitations.
- No new safety mechanism, provider contract, production realism, crash durability,
  key-expiry guarantee, exhaustive schedule coverage, or model-agent efficacy is
  established. All conclusions remain bounded to the synthetic loopback
  HTTP/SQLite apparatus and exercised schedules.
