---
name: checkpoint-handoff
description: Prepare or inspect a durable developer-work handoff with source hashes, revision identity, reproduction evidence and unresolved operations. Use when work moves between sessions or reviewers, not as permission to execute or publish.
---

# Checkpoint handoff

Make the next developer able to distinguish intact work, old evidence, unfinished
operations and publication claims without reconstructing a conversation.

- Record the intended repository revision separately from artifact bytes. Observe
  the current checkout revision independently when resuming; do not copy a claimed
  revision from the handoff as proof. Record uncommitted work explicitly in prose.
- List only the concrete source/artifact paths needed for the handoff, with SHA-256
  hashes. Include test inputs and dependencies when necessary to reproduce results.
  Keep credentials and unrelated local files out of the bundle.
- Give an exact reproduction argument vector, workspace-root working directory,
  associated revision and observed result. Record failed or unrun checks honestly.
  A recorded pass does not replace rerunning an authorized check on changed bytes.
- Carry unresolved operations forward by stable identifier, observed state and the
  next read-only observation that could resolve uncertainty. Do not convert a
  timeout into failure or blindly repeat an operation because a session restarted.
- Separate publication intention, accepted write response and independently checked
  remote bytes/revision. A partial receipt must not become a complete-publication
  claim. Name the intended destination so receipts from another destination cannot
  silently fill the gap.

Read [format and examples](references/format-and-examples.md) when writing or
validating a bundle. Use scripts/validate_checkpoint.py for local consistency
checks. It reads artifact bytes but never executes the reproduction command,
retries an operation, contacts a destination or modifies the workspace.

Report integrity errors before interpreting completion. If evidence is intact
but an operation remains pending/uncertain, preserve that state and describe the
next observation. Missing publication evidence is an evidence gap, not proof that
nothing was published. Check an uncertain remote outcome before considering a
retry, within the user's actual authorized scope.

A validator pass or receipt is not runtime permission, proof of authorship, proof
of remote publication, or approval to share files. Re-establish the applicable
scope and authorization independently before consequential work. Stop at a
reviewable handoff if the next action is outside that scope.
