# Research Workflow Atlas

A source-linked map of public tool capabilities, reusable skills, and executable failure/recovery experiments. The first benchmark covers uncertain writes and paginated reads; the growing atlas connects these patterns to published vendor APIs and independently testable workflows.

See [public capability catalog](docs/public-capabilities.md) and [research roadmap](docs/roadmap.md).

## Reproduce
Python 3.10+ standard library only. No downloads, credentials or remote execution.

```sh
python tools/run_all_tests.py
python tools/reproduce.py --study baseline --out ../atlas-baseline-run-001
```

The aggregate runner executes all seven maintained suites in separate interpreters,
including 84 existing tests and eight release-tool tests (92 total). It continues
through failing suites and exits nonzero if any suite fails. See the full
[test matrix and safe reproduction guide](docs/reproduction.md). The output path
above must be new, outside this repository, with an existing parent. The wrapper
runs unchanged study sources in a temporary copy and never overwrites historical
results. Do not directly rerun legacy run_experiment.py entry points against the
source checkout: those preserved scripts overwrite their historical outputs.

The original ten baseline tests cover committed and uncommitted timeouts, idempotency, unsupported status, terminal denial, an empty page with continuation, and a cursor loop. The deterministic corpus has 16 unique scenarios, run in three seeded orders for 48 trials per policy. Repeated seed orders do not create independent statistical evidence.

## Baseline result
In the checked-in run, blind retry produced 6 duplicate commits; inspect-first produced 0, at 84 rather than 72 total calls. Inspect-first left 6 outcomes explicitly unresolved because neither status nor idempotency provided safe recovery. That is intentional incompleteness, not an unqualified success. In those cases the environment's actual hidden state and the agent's justified knowledge differ. Denials stopped after one call.

The corpus assumes a reliable immediate status response when that capability exists, and correctly implemented idempotency when enabled. Real services can violate these assumptions through eventual consistency, partial commits, expired keys, conflicting payloads, or status lookup failure. Thus the result is an executable counterexample to blind retries, not a proof of safe production behavior or an estimated real-world failure rate. It measures calls, not tokens, wall-clock latency, or agent intelligence.

## Public interface atlas
| Capability | Input | Observable result | Common failure | Recovery boundary |
|---|---|---|---|---|
| Discover tools | Public tool-list endpoint and cursor | Name, input schema, optional output schema | Stale catalog, missing capability | Refresh discovery; do not invent a tool |
| Validate result | Declared output schema and returned result | Protocol error vs tool-level error vs data | Treating transport success as operation success | Validate both layers |
| Read pages | Query plus opaque continuation | Items and next cursor | Empty intermediate page, repeated cursor | Continue on cursor; detect loops and cap work |
| Submit operation | Authorized payload plus supported idempotency key | Commit or uncertain result | Timeout after commit | Inspect exact operation before retry |
| Observe operation | Exact operation ID | Committed, not committed, unknown | Stale or unsupported status | Preserve unknown; do not infer non-commit |
| Complete workflow | Verified final artifact/state | Evidence-linked completion | Declaring done on request acceptance | Report confirmed outcome and unresolved limits |

These are abstract public contracts. No named private tools, authenticated inventories, credentials, private logs or proprietary instruction text are included.

## Reusable workflow
`skills/recover-uncertain-operation/SKILL.md` is newly authored for this project using the skill-creation workflow. Its frontmatter passed the available skill validator. The code tests validate the simulator's decision invariants; they do not establish that an LLM will follow the skill. Independent forward-testing with a model and adversarial status responses remains future work.

## Primary references
- JSON-RPC 2.0 specification: https://www.jsonrpc.org/specification. Request identifiers and response/error envelopes do not themselves establish application-level idempotency.
- MCP tools specification, pinned 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25/server/tools. Public tool discovery, input/output schemas, and tool errors are interface foundations, not blanket authorization.
- AgentBench (2023): https://arxiv.org/abs/2308.03688. Broader multi-environment agent evaluation context; not reproduced here.
- τ-bench (2024): https://arxiv.org/abs/2406.12045. Motivates evaluating stateful tool interactions and consistency, rather than plausible prose alone; not reproduced here.

Sources checked October 21, 2026. No claim of exhaustive coverage or research novelty.

## Completed follow-ons and next work
- [Stale status](milestones/stale-status/README.md): one stale read can defeat inspect-first recovery.
- [Key lifetime](milestones/key-lifetime/README.md): expired idempotency keys restore duplicate risk.
- [Late original commits](milestones/late-commit/README.md): two lifetime-guard duplicates occur after the policy returns success.
- [Durable checkpoint handoffs](milestones/checkpoint-handoff/README.md): local evidence validation without treating receipts as permission.
- [Held-out handoff review](milestones/handoff-review/results/REPORT.md): one tool-assisted reviewer matched 48 predeclared written fields across eight fictional cases. This is not randomized efficacy or actual approval-compliance evidence.

Still future: partial commits, admission-time reservations, controlled recovery-skill
comparisons, and realistic latency/fault models. Separate completion, duplicate cost,
unresolved rate and wall-clock cost. Extend the atlas only with original/public
interfaces and reproducible examples; live mutations require separate authorization.

## License and provenance
Original code, skill text, documentation, configurations and synthetic results are MIT licensed. There are no external model weights or datasets. Linked standards/papers retain their own copyrights and are not bundled. No proprietary skill text is redistributed.

## Additional skill case: plainspoken writing
`skills/plainspoken-writing/` contains a newly authored editing workflow with 20 synthetic regression fixtures. It checks whether edits preserve uncertainty, scope, permission boundaries, and factual meaning while removing formulaic prose. Fixtures are qualitative examples, not automated model-evaluation results. No user conversations are included.

Historical MANIFEST.json files describe their original snapshots, not current-tree
integrity after subsequent documentation or code additions. The safe wrapper emits
a fresh source/output hash manifest for each reproduction; see [provenance notes](docs/reproduction.md#historical-evidence).
