# Local-process timeout recovery Implementation Plan

> For agentic workers: use superpowers:executing-plans for native implementation, with an independent reviewer after the full run.

Goal: Produce a bounded reproducible concrete counterexample/control experiment.
Architecture: A subprocess HTTP server persists effects and operation state in SQLite; subprocess original clients and recovery driver exercise frozen schedules; an independent checker reads retained traces and the stopped database.
Tech Stack: Python 3.12 standard library, SQLite, loopback HTTP.
Spec: PROTOCOL.md.

## Global constraints
No installs, credentials, public endpoints, remote mutation, or publication. Do not overwrite historical evidence. Freeze protocol before implementation and source before primary run.

## Review focus
- Timeout may not occur after admission: invalidate that trial.
- Terminal certificate may be paired with stale data: retain explicit adverse control.
- Multiple recovery actors can race a valid original fence: retain adverse control.
- Same key with changed payload must not silently deduplicate: regression rejection check.
- Pending handler after apparent completion must not be hidden: drain and check all handlers, then stop and independently read the database.

## Task 1: Implement and test the apparatus
- [ ] Write eight literal outcome tests before implementation and retain their failing run.
- [ ] Implement service.py, experiment.py, and verify.py with the protocol contracts and bounded cleanup.
- [ ] Test payload conflict and existing-output protection; run all new tests.
- [ ] Run the repository aggregate suite and separately the terminal-race suite.

## Task 2: Execute and independently audit
- [ ] Freeze exact source hashes and run the 120-trial primary matrix in one fresh output directory.
- [ ] Preserve failed/invalid trials without replacements. Check raw process and ordering evidence, database rows, and resource caps.
- [ ] Obtain an independent code/evidence review, resolve important issues with fresh tests, and disclose any post-freeze changes.
- [ ] Write limitations and result counts only after that review; return artifacts to parent without publication.

## Rulings
Native implementation was assigned by the parent, with an independent review gate. The scoped research protocol is the design; no product feature or external side effect is being approved through this document. Source-reference is a Git-blob-verified text materialization, not a git checkout; omitted animation binaries and compressed/payload archives are outside this new experiment.
