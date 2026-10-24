# Local-process timeout recovery

A bounded, single-host HTTP/SQLite fault-injection experiment. Unlike the prior event simulators, this apparatus starts actual OS processes, makes loopback HTTP requests, observes socket timeouts, and counts rows in a file-backed SQLite database after the service has stopped.

This is deliberately engineered evidence about a tiny synthetic service. It is not production validation, a distributed-host experiment, a provider contract, or a transfer of the prior simulator's two-call theorem.

Read [REPORT.md](REPORT.md) for results, independent verification, limitations and measured bounds.

## Files

- PROTOCOL.md: preimplementation scenarios, literal predictions, denominator, bounds, and interpretation limits.
- PREIMPLEMENTATION.sha256: original protocol and plan content identities, not a third-party timestamped preregistration.
- service.py: loopback-only threaded service with transactional effects, a retained payload-bound idempotency key, and an original-operation cancel fence.
- client.py: actual client requests, subprocess timeout receipts, and two-process recovery barrier.
- experiment.py: isolated trial lifecycle and fixed 120-trial matrix. Existing output paths are refused.
- postrun/verify_run.py: preferred whole-matrix recheck, added after measurement to validate the complete denominator, frozen source identity, exact snapshot provenance, and clean handler completion/shutdown.
- verify.py: frozen original per-trial checker, retained for reproducibility. Its scan alone is insufficient; use the post-run verifier or independent audit.
- test_process.py and test_evidence.py: eight scenario checks plus payload-conflict, overwrite protection, and corrupted-evidence rejection regressions.
- evidence/primary-run/: all primary trial databases, event traces, client outcomes, final service reads, case identities, row-level results, source freeze, and summary.
- evidence/source-at-measurement/: exact hash-matched source used for the primary measurement, preserved before any possible post-review correction.
- evidence/mutations/: supplementary, post-measurement faulty implementations and their failing test logs. These are not part of the primary denominator.
- independent-review/: independently written raw-evidence audit, review, and negative checker probes.

## Unpack retained evidence

The raw evidence and larger checksum manifests are losslessly packaged in `retained-evidence.tar.gz`; readable source, protocol, results, and review documents remain ordinary repository files. From this directory, first verify and extract:

    sha256sum -c ARCHIVE-SHA256SUMS
    tar -xzf retained-evidence.tar.gz
    sha256sum -c ARTIFACT-SHA256SUMS

The archive contains relative paths and does not overwrite the ordinary source/document files already present here. See [PUBLICATION.md](PUBLICATION.md) for publication transformations and preserved identities.

## Reproduce safely

Python 3.10+ and its standard library suffice. The measured environment is recorded in evidence/primary-run/frozen-input.json. No installation, credentials, or public endpoint is required. Service sockets bind only 127.0.0.1 and terminate after each trial.

From this directory:

    python3 -B -m unittest -v
    python3 -B -m unittest discover -s postrun -v
    python3 -B experiment.py --out /path/to/a/new-run-directory
    python3 -B postrun/verify_run.py /path/to/a/new-run-directory

To recheck the retained primary matrix, run python3 -B postrun/verify_run.py evidence/primary-run. The post-run mutation tests require the retained primary directory as their fixture and never edit it. To independently audit the retained primary matrix, run python3 -B independent-review/audit_primary.py. That audit is intentionally tied to evidence/primary-run and the fixed predeclared matrix.

The output parent must exist; the final directory must not. Do not reuse evidence/primary-run as an output path. Reproduction is expected to preserve outcomes and required event order, not PIDs, ports, timestamps, byte-identical databases, or wall duration. Inspect failures and retain them; do not replace failed trials to improve the denominator.

The service is an experimental apparatus, not deployable infrastructure: there is no authentication and fault-control endpoints are intentionally available to the local driver. Do not bind it to a public interface.

## Scope of the terminal certificate

A certificate here is ordinary JSON reporting the original operation's state and a same-transaction current count. The cancel endpoint fences that operation under the same SQLite serialization that governs its write. This does not make an independent cached item view fresh, fence other recovery writers, authenticate a remote provider, prove a time bound, or cover crashes, key expiry, replication or network partitions.
