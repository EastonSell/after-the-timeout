# Full test matrix and safe reproduction

Python 3.10+ standard library only. No downloads, credentials or live services.
From the repository root run:

```sh
python tools/run_all_tests.py
```

Every suite runs in a fresh interpreter, avoiding collisions between historical
modules named workflow and run_experiment. The runner attempts all suites and
returns nonzero if any failed. It runs tests, not new research experiments; fixture
reproductions use temporary workspaces. This is local validation, not hosted CI.

| Suite | Working directory | Discovery path | Tests |
|---|---|---|---:|
| Baseline | repository root | tests | 10 |
| Stale status | milestones/stale-status | tests | 22 |
| Key lifetime | milestones/key-lifetime | tests | 11 |
| Late commit | milestones/late-commit | tests | 12 |
| Checkpoint handoff | repository root | milestones/checkpoint-handoff/tests | 19 |
| Handoff review harness | repository root | milestones/handoff-review/tests | 10 |
| Release tools | repository root | tests/release | 8 |
| Total | | | 92 |

Each row can also be run as python -m unittest discover -s DISCOVERY_PATH -v
from its listed working directory. Running only the old root discovery command
executes ten baseline tests, not this full matrix. Counts are tested release
facts, not promises that future additions will automatically be discovered;
maintain the suite list when adding another independently rooted suite.

## Reproduce without replacing historical outputs

Use the version-1 wrapper and select a new output directory outside the source
repository. Its parent must already exist. For example:

```sh
python tools/reproduce.py --study baseline --out ../atlas-baseline-run-001
python tools/reproduce.py --study stale-status --out ../atlas-stale-run-001
python tools/reproduce.py --study key-lifetime --out ../atlas-key-run-001
python tools/reproduce.py --study late-commit --out ../atlas-late-run-001
```

The wrapper copies only the selected study's necessary original sources,
configuration, prediction records and imported-model dependencies into a temporary
workspace. It runs the unmodified historical script there, then exports generated
files, stdout/stderr and reproduction.json into an exclusively created directory.
The manifest records wrapper version 1 and SHA-256 hashes of the copied input
bytes and generated outputs. It does not authenticate Git ancestry or confer
permission for external actions.

Existing files/directories, broken symlink targets and outputs inside the source
repository are refused. A failed study creates no output directory. If an I/O error
occurs during export, a partial new directory can remain: do not call that a valid
reproduction or automatically reuse it. A complete reproduction.json is written
last. Verify its listed hashes, inspect the error and choose a separate fresh path
for an authorized retry. This is a local convenience wrapper for trusted study
sources, not a sandbox for malicious code or concurrent filesystem manipulation.

## Historical evidence

The original root and milestone run_experiment.py files are intentionally left
byte-identical. Their direct entry points still overwrite the results paths they
were originally designed to produce. Archived study README commands describe
those historical entry points; use the wrapper above for new runs.

Root and milestone MANIFEST.json files are historical evidence, not living
current-tree manifests. Do not rewrite them to make later changes look original.
This release leaves all model sources, predictions, recorded result files and
existing manifests unchanged. Wrapper provenance hashes identify the exact
preserved sources used for a new run without revising older records.

Generated rows and summary values should match the archived study. Runtime
metadata can differ: the baseline records Python version, and stale-status records
run time/version. Compare measurement rows and summaries rather than assuming
all historical result files are byte-repeatable. The release regression test
reproduces each of the four studies and compares rows/summaries while checking
that the source checkout and its historical result bytes remain unchanged.
