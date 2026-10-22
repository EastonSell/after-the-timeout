# Checkpoint v1 format

A checkpoint is a JSON object with exactly these fields. Unknown fields and
ambiguous duplicate JSON keys fail validation. Paths are relative POSIX names;
absolute paths, parent traversal and symlinks are rejected. The root itself is
chosen by the caller. Use full lowercase 40- or 64-character commit identifiers.

```json
{
  "schema_version": 1,
  "source_commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "artifacts": {"answer.txt": "<64 lowercase SHA-256 hex characters>"},
  "reproduction": {
    "argv": ["python", "-m", "unittest", "discover", "-s", "tests"],
    "cwd": ".",
    "result": "not_run",
    "commit": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  },
  "operations": [
    {"id": "upload-17", "state": "uncertain", "next_observation": "Read exact destination revision and compare bytes before any retry."}
  ],
  "publication": {"expected_destination": "example-project/review-branch", "receipts": []}
}
```

The placeholder hash above must be replaced by the actual digest. Each operation
state is completed, not_executed, denied, pending or uncertain. All carry a
nonempty next_observation; completed operations may say "No further observation
needed for this checkpoint." Denied, pending and uncertain states block readiness.
A not_executed entry does not authorize execution.

Reproduction result is passed, failed or not_run. It is a claimed observation,
not a check performed by this utility. The command is an argument vector for
human review, never an executable instruction to the validator. Only root cwd
is supported in version 1. Passing results tied to a different revision are
invalid; failed/unrun results block readiness.

Set expected_destination to null and receipts to [] if publication is not part
of this checkpoint. Otherwise each receipt has exactly destination, commit,
artifacts (a subset of the source path/hash map) and reference (an opaque record
identifier or link). The utility never fetches reference or destination. Multiple
matching receipts can cover different files at the same destination and revision.
Wrong revision, destination, extra file or hash is an error. The reference is not
a signature. Repeated matching receipts do not count as independent evidence.

## Invocation and interpretation

Observe the intended checkout revision using your normal read-only repository
inspection. Supply that independently observed full revision, not a value copied
from the checkpoint, as --current-commit:

```sh
python skills/checkpoint-handoff/scripts/validate_checkpoint.py checkpoint.json --workspace /path/to/review-copy --current-commit FULL_OBSERVED_COMMIT
```

Exit 0: ready_for_review, meaning only that these declared local consistency
checks passed. Exit 1: structurally intact but blocked by unresolved operations,
failed/unrun reproduction or incomplete publication evidence. Exit 2: invalid
structure, missing artifact, mismatched bytes or revision, unsafe path or receipt.
The report always sets approval_granted to false. Ready is not permission to act.

publication_evidence is not_recorded, recorded_partial or recorded_complete.
Even recorded_complete means consistent *local claims*, not verified remote
publication. If evidence is missing, first inspect the destination rather than
assuming a write failed. The utility cannot discover omitted artifacts, establish
Git ancestry/cleanliness, authenticate receipts, prove tests ran, or detect changes
after it finishes. Use a stable review copy; symlink rejection is not a hardened
sandbox against concurrent filesystem mutation.

## Practical failure cases

- A session stopped after producing a report but before copying its input fixture.
  Validation flags the missing path. Restore the matching fixture or rebuild the
  report; do not silently remove it from the manifest to manufacture a pass.
- A formatter changed source after tests passed. Artifact hashes no longer match.
  Review the diff, rerun the appropriate authorized checks, then intentionally
  create a new checkpoint instead of editing an old receipt to look current.
- Two files were intended for publication; only one receipt was saved. Report
  partial local evidence. Read the destination to determine whether the second
  file arrived before deciding whether a retry is needed and authorized.
- A write timed out and the new session sees no local receipt. Keep the operation
  uncertain. A checkpoint is useful precisely because it preserves this gap.

The repository demonstration creates temporary workspaces and emits sanitized
reports: python milestones/checkpoint-handoff/demo.py. It makes no real
repository changes or network calls. Fixture receipts are invented local test
records, never evidence of actual publication.
