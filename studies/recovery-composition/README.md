# Recovery composition: finite synthetic study

**Frozen P5 is false. The composed policy is not superior.** Both adequate
policies have zero duplicate effects over this finite grid and the same 554
universally complete cases. The capability baseline has 423 universally justified
cases versus 417 for horizon-aware. The six losses are one structural defect
replicated over two key scopes and three hidden retry outcomes, not six
independent discoveries.

Start with [the unchanged accepted report](REPORT.md), then the
[portable protocol presentation](PROTOCOL.md) and
[exact machine-readable protocol](protocol.json).

## What this establishes, and what it does not

This is an offline, finite deterministic model, not an API client, a model-behavior
experiment, a production reliability estimate, or a general optimality theorem.
It composes partial batches, late originals, finite reservation/cache retention,
charged observation lag, failed retries, same-tick event orderings, and event
execution after policy return. The 800-case grid contains 486 exhaustive cases
and 128/96/90 preselected structural-family cases. These are not independently
sealed holdouts. The retained run has 3,200 case-policy groups, 319,968 explored
states, and 86,796 complete scheduler paths. Path counts are not probabilities.

| Policy | Unsafe cases / 800 | Universally complete | Universally justified |
|---|---:|---:|---:|
| naive_inspection | 356 | 658 | 344 |
| blind_keyed | 368 | 570 | 300 |
| capability_fallback | 0 | 554 | 423 |
| horizon_aware | 0 | 554 | 417 |

The false P5 compared horizon-aware with an omniscient information upper bound,
not a realizable competing policy. Its original wording and false result remain
in protocol.json and results-v1/predictions.json. All adverse raw traces and
counterexamples are retained without changing scientific values.

The six justified-completion losses occur when both effects already exist at t=0,
lag=2, terminal bound=4, deadline=4, and TTL=20. Horizon-aware stops at t=1 without
a call; the baseline obtains both positives from a safely suppressed replay at
t=2. This identifies a positive-reconciliation versus terminal-negative-waiting
defect, not a demonstrated improvement from a new policy. Any repair must be
compared against an equally optimized baseline and price its calls and latency.
The read-only saved-group diagnostic is in
[portability/saved-case-comparison.json](portability/saved-case-comparison.json).

CACHE is the exact executable contract in source/model.py, not a generic cache
promise. In particular, a fully suppressed request still gets an empty attempt
and later terminal event. For batch CACHE that event can replace a cache entry,
lose an older positive response, and refresh retention. Item CACHE installs on
effects; batch CACHE installs on termination; concurrent admissions do not recheck
at commit. Neither adequate policy uses keyed CACHE replay. Broader comparisons
need an explicit distinction between hits, no-ops, and cache refreshes.

The post-hoc supplementary two-world result is outside the 800-case manifest.
Its safe-action closure concerns only synchronous clients, integer-tick waits,
charged reads, A/B/AB writes with immutable original keys or keyless, successful
retry semantics, unavailable status, no cancellation or compensation, and the
stated finite horizons. It enumerates 60 possible first writes; only the three
suppressed original-key writes at t=1 are safe in both worlds. This is an
action-alphabet-specific finite impossibility result, not exhaustive policy
enumeration or a theorem about real services or general policy optimality.

## Offline saved-evidence verification

Python 3.12.14 on Linux was used for the accepted study; the package uses only the
Python standard library. From this directory, choose fresh sibling paths whose
parent already exists:

```sh
sha256sum -c PUBLIC-SHA256SUMS
python -B -m unittest discover -s packaging -v
python -B tools/reconstruct_payloads.py ../recovery-restored
(cd ../recovery-restored && sha256sum -c ACCEPTED-SCIENTIFIC-BYTES.sha256)
python -B tools/check_saved.py ../recovery-restored --report ../recovery-recount.json
```

The two output paths must not already exist. The recount reads saved outputs and
imports the exact retained source/checker.py, not the simulator or runner. It
reconstructs dynamics, admissions, key behavior, evidence, counts, charged costs,
pending queues and a prefix-tree coverage certificate. The portable wrapper also
checks each row's complete case object against cases.json. It verifies all 3,200
groups and all 86,796 paths against the retained aggregate results. A matching
coverage-manifest digest is
53bbf03853f8252529257ea0a812ee9424dfd090d1541d9a3f34f90bd109c969.
The optional report is exclusively created outside the input tree.

**Checker scope:** dynamics/evidence checking is not registered-policy choice
replay. The retained checker does not independently prove that every action was
the action its named policy would choose. The portable wrapper does not add that
capability. Do not describe this recipe as independently replaying every named
policy decision. No separate policy-replay supplement is included.

The packaging tests exercise only transport fixtures: exact recovery, bounded
decompression, tampered hashes, path traversal, duplicate paths, symlink refusal,
and fresh-output-only behavior. The original tests/ files are also retained
exactly, but they run bounded simulator fixtures and are separate from the
saved-evidence-only recipe above. Their recorded historical outputs are in logs/.

## Exact-byte transport and provenance

Three large files are represented by content-checked payloads rather than large
single uploads:

- results-v1/rows.jsonl.gz: 6,000,978 accepted compressed bytes; reconstruction
  preserves that existing gzip file exactly, including its original header.
- results-v1/group-summaries.jsonl: 1,456,756 accepted bytes.
- supplementary/indistinguishability-pair.json: 762,944 accepted bytes.

[payload-manifest.json](payload-manifest.json) gives every target size, exact
SHA-256, per-part size/hash, and transport digest. Parts are base64 text, at most
480,001 bytes each. The latter two targets use deterministic gzip (level 9,
mtime 0) solely for lossless transport. No row, field, trace, counterexample or
scientific value is filtered or normalized. The reconstructor accepts only safe
relative manifest paths, bounded sizes, canonical base64, and checked hashes. It
validates every byte before creating a fresh destination; it neither extracts
archives nor overwrites existing files.

[TRANSFORMATIONS.json](TRANSFORMATIONS.json) maps original and packaged hashes.
The report, numerical inputs, Python study sources/tests/tools, result JSON,
and supplementary scientific data are exact accepted bytes. Only the protocol's
introductory provenance sentence is made portable; its scientific specification
is unchanged. Three historical test logs replace the old root prefix with
<study-root>/. They are explicitly address-redacted derivatives, not exact logs.
All other shipped historical logs are exact. The README, packaging tests,
reconstructor, portable recount wrapper and saved-group diagnostic are new
publication material, not part of the executed study.

ACCEPTED-SCIENTIFIC-BYTES.sha256 checks the unchanged accepted scientific files
in the reconstructed tree. PUBLIC-SHA256SUMS checks the shipped portable package,
excluding its own checksum file. Neither is presented as the study's original
chronological freeze. Original execution-era text and manifest identities in
results-v1/run-input.json remain unchanged and may differ from public presentation
hashes. Antecedent excerpts and original chronology manifests are not reconstructed.
Local chronological freezes were not independently timestamped preregistrations.

## Reproduction boundaries

This release's documented verification reconstructs and checks the accepted
saved evidence. It does not rerun the 800-case experiment, create a new research
result, repair the six losses, or measure production behavior. The exact
source/runner.py is retained for inspection. Its command-line entry point expects
an original SOURCE-FREEZE.sha256, which is deliberately not reissued here; the
public checksums must not be substituted and relabeled as that executed freeze.
A separate fresh experiment can call the retained runner.run API with an absent
output directory, but its new provenance/time/resource records are not the old
run and its compressed-file bytes need not match the retained gzip header.

The accepted report's post-hoc boundaries, resource ledger, expectation
corrections, failed predictions, and post-return duplicate witnesses are retained.
No fresh scientific run or new policy optimization was performed for packaging.
