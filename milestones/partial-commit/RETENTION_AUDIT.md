# Pre-outcome retention audit

2026-10-22. Applied the original retain-experiment-evidence checklist before any
factorial outcome execution. This is a local audit, not external preregistration.

- Protocol, explicit case grid, implementation, runner and tests are frozen.
- Initial freeze is retained; a prospective amendment explains the output-retention
  correction identified during independent review.
- mkdir(exist_ok=False) reserves the run before outcome execution; a regression
  confirms that existing output is unchanged and execute is not called.
- Each row is appended, flushed and fsynced to rows.jsonl before the next case.
  Interruptions before the first case and after one completed record are tested.
- A running status marker distinguishes incomplete runs; atomically replaced final
  JSON includes complete evidence and failed predictions before a failing exit.
  A deliberately falsified synthetic row verifies this ordering.
- Exact case definitions are checked against the declared factorial before running.
  A checksum regression verifies changed frozen input is rejected.
- Raw and final artifacts are deterministic and can be compared across fresh runs.
  Actual reproduction is pending outcome clearance; no reproduction is claimed here.
- Failed predictions do not suppress output. Whether to publish, extend the model
  or interpret a discrepancy is separate from preserving it. Any later diagnostic
  will be marked post-hoc rather than silently altering the frozen protocol.

Scope: process-interruption retention on this local filesystem. No claim of
power-loss durability, concurrent writers, hostile filesystem resistance or remote
storage replication. A running marker can also indicate an exception, not only an
interruption. A terminal output is valid only after complete coverage and checks.
