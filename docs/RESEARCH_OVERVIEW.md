# After the Timeout
## Evidence-dependent recovery, partial effects and durable handoffs in tool workflows

Evidence snapshot: 22 October 2026. Deterministic policy experiments, software checks, qualitative fixtures and the small reviewer exercise are reported as different evidence types.

## Abstract

A failed response does not uniquely identify a failed action. This project studies recovery when a tool operation may have committed, status may be stale, idempotency may expire or only part of a batch has taken effect. Small deterministic simulators compare explicit policies using duplicate effects, actual completion, reported completion, unresolved outcomes and call counts. Inspect-first recovery avoids baseline duplicates under reliable status contracts, but later studies expose failures under stale observations, finite keys and delayed original commits. A partial-batch study shows the value and limits of item-level evidence and durable keys; a blind keyed baseline also succeeds under its narrow contracts. Separate artifacts examine checkpoint handoffs and evidence retention. Their scope is executable policy counterexamples and workflow tests. Production rates and model behavior require different evidence.

## Question and motivation

After a timeout, an agent has an epistemic problem as well as an execution problem: what happened, and what can be justified from the available evidence? Hidden simulator truth and a policy's justified knowledge must remain separate. The same problem appears in handoffs, where a receipt may be incomplete, stale or tied to a different source version.

The research asks:

1. Which interface guarantees make a retry safe over a declared execution horizon?
2. When does preserving uncertainty prevent duplicates at the cost of unresolved work?
3. What evidence is required to report completion at operation, item and artifact level?
4. Can a reusable workflow improve model-assisted decisions, beyond validating a hand-written policy?

## Related primary work and contracts

- [JSON-RPC 2.0](https://www.jsonrpc.org/specification) defines request/response envelopes and correlation identifiers. Correlation identifiers and application-level deduplication have separate contracts.
- [MCP tools specification, version 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/server/tools) distinguishes discovery, schemas and tool-level errors. The repository models selected recovery contracts; a wire-compatible MCP implementation is outside its scope.
- [AgentBench](https://arxiv.org/abs/2308.03688v2) motivates evaluating decisions in interactive environments. [τ-bench](https://arxiv.org/abs/2406.12045) motivates stateful tool interaction and consistency measures. Those model benchmarks evaluate a broader class of behavior than these deterministic policies.

The [public capability catalog](public-capabilities.md) links vendor-published interfaces. Actual connector methods and account permissions require separate verification. [Partial-batch routing](partial-commit-capabilities.md) specifies the contracts needed for item-level reconciliation.

## Hypotheses and comparison logic

**Baseline:** authoritative status inspection or documented idempotency can prevent some duplicate effects relative to blind retry. Policies must also report unresolved cases and extra calls.

**Contract stress tests:** stale status, key expiry and delayed original execution can invalidate a policy that works under stronger assumptions. These follow-ons test bounded counterexamples; their constructed frequencies are not estimates of how often services fail.

**Partial batches:** missing item results should remain unknown unless the interface provides authoritative terminal negatives. Durable per-item, payload-stable keys can support retries under the declared horizon. The keyed blind baseline tests whether sophisticated inspection is actually needed in that contract.

**Behavioral proposal:** a recovery skill may help a model identify these boundaries. That hypothesis requires behavior measurements beyond format and simulator checks. A controlled model-assisted comparison remains necessary.

## Methods and controls

The [baseline](../README.md#baseline-result) has 16 unique scenarios in three seeded orders, yielding 48 trials per policy. Tests cover committed and uncommitted timeouts, unsupported status, denial, idempotency and pagination edge cases. The three orders reuse the same scenario set.

[Stale-status](../milestones/stale-status/README.md), [key-lifetime](../milestones/key-lifetime/README.md) and [late-commit](../milestones/late-commit/README.md) studies weaken specific assumptions. The last uses an event queue so final effects can be checked after a policy has already returned.

The [partial-commit protocol](../milestones/partial-commit/PROTOCOL.md) compares four policies across 256 fixed cases, with and without durable item keys. It separates public evidence from evaluator-only truth. A prospective retention correction ensures false predictions are saved before assertions. A post-hoc recount uses a separate closed-form analysis of retained rows.

[Checkpoint validation](../milestones/checkpoint-handoff/README.md) tests artifact identity and completeness. The [handoff-review harness](../milestones/handoff-review/README.md) uses eight fictional held-out cases and a frozen field rubric. [Release-validation tests](../skills/release-validation/README.md) concern packaging and declared tests, separate from scientific reproduction.

## Measured findings

- **Baseline:** blind retry produced six duplicate commits; inspect-first produced none, with 84 versus 72 calls and six unresolved outcomes. Reliable immediate status and correct idempotency were assumptions. [Reproduction guide](reproduction.md).
- **Stress tests:** stale status caused inspect-first duplicates. Key expiry restored duplicate risk. The late-commit study found two delayed duplicates after the lifetime guard returned success; a known-bound control avoided duplicates while leaving 16 outcomes unresolved. [Study sequence](../MILESTONES.md).
- **Partial commits:** without keys, blind-batch replay generated 48 extra effects across 32 cases; evidence-only recovery generated none but left 24 cases with unknown items. With durable keys, capability-guard and blind-batch each achieved exact-once effects in all 32 cases of their respective groups. The blind keyed policy used fewer calls. [Full report, raw rows and recount](../milestones/partial-commit/REPORT.md).
- **Reviewer exercise:** one tool-assisted reviewer matched all 48 predeclared written fields over eight fictional cases. This unrandomized small exercise does not establish efficacy, reliable live behavior or approval compliance. [Report](../milestones/handoff-review/results/REPORT.md).

## Reproducibility and limitations

[Start here](START_HERE.md) teaches one uncertain-operation example. Use the [safe reproduction wrapper](reproduction.md), which copies preserved study sources and requires a fresh output location. Legacy entrypoints can overwrite their historical outputs. Historical manifests describe their original snapshots; fresh wrapper manifests cover the reproduced source/output set.

The partial-batch model assumes the original is terminal, recovery writes succeed, keys remain valid and evidence is truthful. It excludes overlapping late execution, expiry, concurrent writers and retries that also time out. Calls have no realistic latency or price. Model adherence still needs behavioral evaluation. Unresolved outcomes, reported success and actual completion remain separate even when an evaluator knows the hidden state.

## Falsifiable next steps

1. Combine partial effects, finite key lifetime and late originals in a frozen event-driven corpus. A policy claiming safe retry should retain that property through the declared final horizon, including after it returns.
2. Compare skill-assisted and unassisted model decisions on held-out cases with fixed models, prompts and budgets. Preserve raw decisions and separately score duplicates, justified completion, true completion and unresolved work. A behavioral improvement claim would fail if performance did not exceed the control under the predeclared analysis.
3. Add explicit call latency, fault correlation and cost assumptions, then test sensitivity. A policy that saves duplicates but violates the service target should be reported as that tradeoff rather than a universal winner.

These are prospective extensions. Unpublished corpora or harness candidates do not establish completed results. Live-service validation would require a separately bounded, authorized test environment.
