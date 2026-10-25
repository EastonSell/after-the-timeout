# Original evidence and public metadata derivative

This additive package reports one reviewed 24-row study. The raw original
source, run, supervision, and review records are retained privately. Public
release uses transparent metadata redactions rather than exposing internal
coordination labels or absolute execution paths.

## Identities are not reassigned

- Repository base: `d11df2f7fc9cd950d472c98b5aba107fb461080a`.
- Original pre-data freeze SHA-256:
  `990faf455cece27c437546899533fb1e1c90a508c5429c13df45fbd20275cdaf`.
- Original output-manifest SHA-256:
  `5f979bc0546521e6040a751ef4265d1cbc80ba1e3c911e749f67c8c0b9c0293f`.

The original `source/PRE_DATA_FREEZE.json` and `run/OUTPUT_SHA256.json` preserve
original content identities. They do not falsely claim to hash-match redacted
metadata. The original admission still names the original freeze; its decision
was not rewritten to admit a post-data derivative.

`PUBLIC_DERIVATIVE_SOURCE.json` supplies the public counterparts of all 38
original source-file hashes and is explicitly labeled POST-DATA.
`ORIGINAL_PUBLIC_HASHES.json` lists every retained original/public content pair,
byte length, logical location and redaction status. `METADATA_REDACTIONS.json`
records the replacement categories and original/public hashes without exposing
the removed strings. These provide content custody, not a new preregistration.

## What changed, and what did not

Metadata changes replace absolute workspace, runtime executable and temporary
paths with portable placeholders and replace private coordination-role labels
with neutral implementation/review labels. Review summaries are readable public
provenance rather than a transcript of private coordination. No removed private
string is republished in the redaction ledger.

No numerical result, request/response observation, process ID, timestamp, trial
classification, payload, or SQLite database/journal byte changed. No case was
added, removed, replaced or rerun. Core store, worker, runner and scientific
checker code is unchanged. The original supervisor's private path literals are
placeholder-redacted and that script is retained as history, not a runnable
replication command.

The archive's relative prefixes are packaging choices: `run/`, `execution/`,
`review/`, `source/evidence/`, and `source/upstream/`. The ordinary source files
and their archived companions form the complete metadata-redacted derivative.
The archive does not overwrite ordinary files when extracted.

README.md, REPORT.md, REVIEW.md, this document, the publication manifests, and
`verify_public_derivative.py` are post-measurement additions. They are not
inserted into the original pre-data freeze. The public auditor validates the
explicit identity mappings, the complete original output file set, and all 24
rows from the unchanged scientific receipts and independently reopened SQLite
state. The historical original-byte auditor remains available as source but
must not be presented as directly validating metadata-redacted bytes.

## Scope and exclusions

Only a new study directory and a small root README discovery entry are proposed.
No historical package is replaced. The earlier unreviewed fixed-matrix output
is excluded from the package, predictions, comparisons, and denominator.

The 24 rows cover application-process SIGKILL/restart with synthetic file IPC,
at barriers outside the COMMIT call. The pre-COMMIT changed-payload control
accepts B while leaving original A incomplete. There is no general durability,
HTTP-timeout, power-loss, provider, production-rate, or model-efficacy claim.
