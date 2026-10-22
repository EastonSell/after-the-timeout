# Research roadmap

The initial simulator and skills are the first testable layer of a broader capability atlas.

## Milestone 1: reproducible foundation
Completed: baseline recovery corpus, public capability/source matrix, stale-status, key-lifetime and late-original-commit follow-ons, plus durable checkpoint tooling. The aggregate test runner now includes all 92 tests across seven suites. Source publication and hosted CI are distinct; this release does not claim hosted CI results.

## Milestone 2: independent behavioral evaluation
A narrow handoff review is complete: one fresh tool-assisted reviewer matched 48 written fields across eight constructed cases. The original response and limits are preserved in [the report](../milestones/handoff-review/results/REPORT.md). It is not a randomized or comparative efficacy result. The broader recovery-policy evaluation below remains future work.

Prepare held-out fake-service tasks with stale statuses, malformed output, missing capabilities, conflicting idempotency payloads and partial commits. Compare no skill, recovery skill, and unrelated-skill controls. Use identical prompts, model versions and tool budgets; separate safety/duplicate errors from ordinary task failure. Run fresh evaluators without expected answers. Publish task fixtures, outputs after secret scanning, failure categories, call counts and confidence intervals by task family. No paid API/model run has been performed yet.

## Milestone 3: interface-grounded workflow cases
Turn observed successful public-service workflows into original examples: discover capabilities, use an existing authorized interface for a missing operation, verify exact resulting object, and return to structured API operations. Record which steps were actually observed, which were simulated, and the public source for each capability. Validate no unintended credential or permission expansion. Add a skill only when a reusable decision invariant emerges.

## Milestone 4: efficiency and transfer
Measure completion per tool call and per elapsed second, alongside duplicate/error cost. Test whether the same skill transfers across two fake services with different response shapes. Introduce realistic latency/fault distributions separately from deterministic regression tests. Token and cost measurements require explicit model/account instrumentation and must not be inferred from character count.

## Release gate
All examples must be original or license-compatible, use synthetic/public inputs, avoid secrets/private inventory, pass tests, and link to verified public sources. A useful negative result or clearly bounded unresolved case qualifies as research progress. Novelty claims require a focused literature comparison and independent review.
