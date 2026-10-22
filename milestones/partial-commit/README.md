# Partial-commit recovery

An isolated, deterministic three-item batch example. Read [PROTOCOL.md](PROTOCOL.md)
for exact assumptions, policy evidence, metrics and pre-run expectations.

From this directory, choose a new output directory with an existing parent:

```sh
python -m unittest discover -s tests -v
sha256sum -c FREEZE.sha256
python run_experiment.py --out /tmp/partial-commit-new-run
```

The example path must not already exist. Without --out, the runner uses results
and refuses to overwrite a previous run, including the published reference output.
It requires Python 3.10+ and the standard library. Frozen inputs include the source,
tests, runner and explicit 256-case list. No account access, network or package
installation is used. experiment.json holds all cases and aggregates; rows.jsonl
is the incrementally flushed case record; status.json marks running, complete or
prediction_failed. A failed prediction is retained before a nonzero exit.

The [retention audit](RETENTION_AUDIT.md) and
[retention skill](../../skills/retain-experiment-evidence/SKILL.md) show the runner's
failure-retention invariants. FREEZE.v1.sha256 records the initial pre-review
freeze and is historical; verify the current files with FREEZE.sha256, not v1.
Results and their limitations are summarized in [REPORT.md](REPORT.md).
The 256 saved rows also pass the separate post-hoc check: python recount.py.
