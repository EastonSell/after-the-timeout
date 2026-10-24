# Publication copy and evidence packaging

This additive study is published under `studies/local-process-recovery/` in EastonSell/after-the-timeout, based on commit `bb7c59a61f95575edbd3c90719f69dffa1dfd5db`. Existing repository files and historical results are not modified.

## Contents

The readable source, protocol, plan, report, post-run verifier, independent audit, and review documents are ordinary files. `retained-evidence.tar.gz` losslessly packages all other retained files, including all 120 primary trial databases and traces, exact source-at-measurement bytes, supplementary mutants, copied negative probes, historical test logs, and larger checksum manifests. Extract it in this study directory after verifying `ARCHIVE-SHA256SUMS`. Its members have only relative paths and do not overlap the ordinary published files.

`ARTIFACT-SHA256SUMS`, available after extraction, covers the complete expanded payload except itself. It deliberately excludes the outer archive and `ARCHIVE-SHA256SUMS` to avoid a circular hash dependency.

## Precisely disclosed transformations

- The frozen producer's 10 source files, preimplementation protocol/plan hashes, exact source-at-measurement directory, and all primary measurement files are byte-for-byte unchanged.
- Historical error logs and probe-output JSON contain 52 occurrences of the local workspace prefix. Only that prefix was replaced by the project-relative `studies/local-process-recovery` path in the publication copy. No event, database, source, result, or diagnostic meaning was changed.
- REPORT.md and EXECUTION.md distinguish the original read-only measurement/review phase from this later repository publication. README.md adds archive extraction instructions. These documents are not part of the frozen producer.
- The review-artifact checksum map and expanded-payload checksum manifest were rebuilt for the publication bytes. Original prepublication checksum maps are retained under `publication-provenance/` as explicitly historical identities, not current verification manifests.
- `PUBLICATION.json` records path-only redaction counts and before/after content hashes. The original reviewed archive SHA-256 was `69421d615dc97d48d2f850c2229b41edb5e302b0fd659bc36e504a3a22458c9c`. That original archive is not republished because it contains the unredacted local prefixes.

## Verification and limits

The post-run verifier and independent raw-data audit must both accept the unchanged primary 120-trial matrix. Apparatus and post-run regression tests are rechecked for this publication copy. Git blob identities and the expected-head, non-force branch update are verified during publication. Repository CI status is reported separately from local checks; a lack of checks is not a CI pass.

The deliberately balanced 60 duplicate-producing and 60 one-effect cases are selected experimental conditions, not a population failure rate. This remains a single-host loopback HTTP/SQLite existence-and-control result, not production validation, crash durability, an external-provider guarantee, or a new general theorem. Independent review means a separate reviewing agent in the same workspace, not an outside blinded laboratory. Full limitations remain in REPORT.md and the review documents.
