# Completed research milestones

1. [Deterministic recovery benchmark and public capability atlas](README.md): sixteen unique scenarios in three seed orders. Blind retry produced six duplicate commits; inspect-first produced none while leaving six outcomes unresolved and using more calls. This is a counterexample corpus, not a measured production failure rate.
2. [Public-interface publication handoff case](milestones/interface-handoff/CASE.md): one observed cross-interface workflow, with an [original verification skill](milestones/interface-handoff/skills/verify-repository-publication/SKILL.md). It is not a comparative benchmark or proof that another account exposes the same capabilities.
3. [Plainspoken-writing fixtures](skills/plainspoken-writing/): original qualitative editing examples, not independent model-evaluation results.

All experiments and skills are original MIT-licensed work grounded in linked public interfaces. No private tool inventory or proprietary instruction text is included. Skill format validation and simulator tests are distinct from independent model forward-testing, which remains pending. Repository publication evidence must distinguish byte-exact source verification, clean-checkout reproduction and hosted CI; one does not establish the others.

3. [Stale-status follow-on](milestones/stale-status/README.md): a single stale status read increased inspect-first duplicate commits from 0 to 3, with per-cell reporting and 22 tests. [Freshness-aware recovery skill revision](milestones/stale-status/skill-revision/REVISION.md) records the resulting guidance and synthetic review cases.

4. [Idempotency key-lifetime follow-on](milestones/key-lifetime/README.md): 216 unique deterministic cells show that expiry restores duplicates despite reusing a key. A conservative lifetime guard produced zero extra commits but left 10 outcomes unresolved; 11 new regression tests and pre-run predictions accompany per-cell results.

5. [Late-original-commit follow-on](milestones/late-commit/README.md): 128 deterministic event-queue cells expose two delayed duplicates after the prior lifetime guard returns success. A known-completion-bound control avoids duplicates but leaves 16 outcomes unresolved. Twelve new tests cover event ordering, retention boundaries and settled-state evidence.

6. [Durable checkpoint handoff](milestones/checkpoint-handoff/README.md): original public skill, read-only manifest validator and seven temporary-workspace failure examples. Nineteen tests distinguish mismatched/missing evidence from pending work and partial publication, without treating receipts as permission or proof of remote state.
