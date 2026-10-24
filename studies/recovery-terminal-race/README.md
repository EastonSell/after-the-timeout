# Terminal-read race: a bounded two-call recovery result

This additive, post-hoc supplement studies the unchanged [recovery-composition simulator](../recovery-composition/source/model.py) at reference commit `d301e982db65deed6c065063ac243a1e0c0888c7`. It does not replace the original 800-case study, frozen predictions, adverse results, or source.

A certified zero-lag read can race the original terminal event and consume a recovery call without certifying absence. Waiting one extra tick avoids that race. Under the stated synchronous integer-time contract, certified status, a sufficient admission deadline, and nonreject retry semantics, a read plus targeted keyless retry guarantees safe eventual actual completion in at most two calls. Two calls are worst-case necessary in the stated information/action model.

Read [PROOF.md](PROOF.md) for assumptions and the sharp call-budget argument, [independent review](independent-review/REVIEW.md) for the critique and horizon correction, and [RESULT.json](RESULT.json) for exact counts. The executable policy requires full queue drainage; `D+4` suffices, whereas the tighter bound in the proof applies to the capped two-call schedule.

## Evidence and limits

- 972 selected timing-grid cases plus four named witnesses; 1,952 policy groups, 31,350 explored states, and 5,953 complete scheduler paths.
- On that grid: 20 gains in guaranteed actual completion and 10 in guaranteed justification, with no losses inside the grid. A separate shorter-deadline witness disproves global justification dominance.
- Exact path reproduction and a separate policy-decision specification checked 2,561 candidate paths and 8,529 decisions; 729 additional post-hoc stress cases passed.
- Five new regression tests and the original 18 study tests passed. Historical test receipts are retained, including the initial red result.

Path counts are not probabilities. Actual completion can occur after return and is not necessarily justified completion. These are finite synthetic results, not production rates, literature novelty, minimum-deadline optimality, or a globally superior policy.

## Reproduce without overwriting retained evidence

Requires Python 3 and only its standard library. From this directory:

```sh
sha256sum -c SHA256SUMS
sha256sum -c PUBLICATION-SHA256SUMS
python -B -m unittest -v
mkdir independent-review/reproduction
cp policies.py run_boundary.py test_boundary.py independent-review/reproduction/
cp -R vendor independent-review/reproduction/
(cd independent-review/reproduction && python -B run_boundary.py)
python -B independent-review/audit.py
```

The reproduction directory must be absent before `mkdir`. The copied runner writes only its own reproduction outputs; it does not change retained scientific results. The audit compares every decompressed path and all result fields except elapsed time, then repeats decision checks, branch-rejection control, and additional stress cases. Running the audit refreshes its `audit-result.json` deterministically. New gzip headers and wall times need not match the original bytes.

To run the original study tests separately from the repository root:

```sh
(cd studies/recovery-composition && python -B -m unittest discover -s tests -v)
```

## Provenance

`SHA256SUMS` and `independent-review/ACCEPTANCE.json` preserve the accepted artifact identities. `PUBLICATION-SHA256SUMS` additionally covers the publication README and all shipped files except itself. These are content manifests, not timestamped preregistrations. No duplicate reproduction payload is shipped; the recipe regenerates it.

Publication verified that live main still equaled the reference commit and that both vendored source Git blob hashes matched its source tree: model `a727446826a2d54ac7039e59aceba5fd137b82e3`, checker `e05c52522c4ff6d37dee7cfe5294769e9ba2b3bb`. SOURCE.json and the review retain their original, more limited local-verification chronology. The original failed-test traceback retains its historical task-workspace path; it contains no credentials or private research notes.
