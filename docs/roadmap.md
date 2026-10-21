# Research roadmap

The initial simulator and skills are the first testable layer of a broader capability atlas.

## Milestone 1: reproducible foundation
Completed locally: ten recovery tests, 96 deterministic policy trials, two original skills, public capability/source matrix. Parent publication and remote CI verification are tracked separately.

## Milestone 2: independent behavioral evaluation
Prepare held-out fake-service tasks with stale statuses, malformed output, missing capabilities, conflicting idempotency payloads and partial commits. Compare no skill, recovery skill, and unrelated-skill controls. Use identical prompts, model versions and tool budgets; separate safety/duplicate errors from ordinary task failure. Run fresh evaluators without expected answers. Publish task fixtures, outputs after secret scanning, failure categories, call counts and confidence intervals by task family. No paid API/model run has been performed yet.

## Milestone 3: interface-grounded workflow cases
Turn observed successful public-service workflows into original examples: discover capabilities, use an existing authorized interface for a missing operation, verify exact resulting object, and return to structured API operations. Record which steps were actually observed, which were simulated, and the public source for each capability. Validate no unintended credential or permission expansion. Add a skill only when a reusable decision invariant emerges.

## Milestone 4: efficiency and transfer
Measure completion per tool call and per elapsed second, alongside duplicate/error cost. Test whether the same skill transfers across two fake services with different response shapes. Introduce realistic latency/fault distributions separately from deterministic regression tests. Token and cost measurements require explicit model/account instrumentation and must not be inferred from character count.

## Release gate
All examples must be original or license-compatible, use synthetic/public inputs, avoid secrets/private inventory, pass tests, and link to verified public sources. A useful negative result or clearly bounded unresolved case qualifies as research progress. Novelty claims require a focused literature comparison and independent review.
