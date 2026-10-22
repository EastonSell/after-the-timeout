# Partial commits require item-level evidence

The 256 declared synthetic cases completed under the reviewed revised freeze
`a459a84166189165b34be62545070aeb6f86059578ca416efbda6380c69b6ea8`.
All five executable prediction checks passed. Every raw case, including unresolved
and duplicate-producing outcomes, is retained in [rows.jsonl](results/rows.jsonl).
[experiment.json](results/experiment.json) includes the same rows, public evidence,
evaluator-only truth and aggregates. No live service or model was invoked.

## Results

Each row below summarizes 32 constructed cases, not 32 sampled incidents.
“True complete” means every intended item has at least one effect. “Exactly once”
means exactly one per item. “Reported” counts policy completion reports. “Unknown”
counts cases with at least one unresolved item; it is not actual noncompletion.

| Policy | Item keys | True complete | Exactly once | Reported | Extra effects | Unknown | API calls |
|---|---|---:|---:|---:|---:|---:|---:|
| blind_batch | No | 32 | 4 | 32 | 48 | 0 | 64 |
| blind_batch | Yes | 32 | 32 | 32 | 0 | 0 | 64 |
| missing_is_absent | No | 32 | 12 | 32 | 32 | 0 | 95 |
| missing_is_absent | Yes | 32 | 32 | 32 | 0 | 0 | 95 |
| evidence_only | No | 12 | 12 | 8 | 0 | 24 | 75 |
| evidence_only | Yes | 12 | 12 | 8 | 0 | 24 | 75 |
| capability_guard | No | 12 | 12 | 8 | 0 | 24 | 75 |
| capability_guard | Yes | 32 | 32 | 32 | 0 | 0 | 95 |

Without item keys, blind replay duplicated one or more items in 28/32 cells;
missing-is-absent duplicated items in 20/32. The respective 48 and 32 extra effects
are item counts, not case counts. No-key evidence-only and capability-guard each
leave 64 item outcomes unresolved across 24 cells. Four of those 24 cases actually
completed, but the policies cannot establish it from the evidence they received.

All eight fresh-status cases per policy/capability group give both evidence
policies exact-once completion, because a reliable terminal negative is available.
For incomplete status only a is reported. When a and b initially committed, the
missing-is-absent policy retries b/c, duplicating b without keys. The evidence
policy does not infer that missing b/c records mean failure. Durable per-item keys
let capability-guard safely retry unknown items in this explicitly terminal model.

The blind keyed baseline is also exact-once in every cell and uses fewer calls.
This is not evidence that status inspection is universally better or cost-optimal.
The policies have unequal calls; non-blind policies call status even when it is
unsupported. Calls have no modeled latency or price. No equal-budget efficiency,
production failure-frequency, LLM behavior or general safety claim follows.

## Validation and sequence

The original freeze preceded outcome execution. Independent review identified a
retention defect: the first runner would raise on a false prediction before saving
case evidence. A dated prospective amendment fixed that before any factorial run.
FREEZE.v1.sha256 preserves the original hash list; FREEZE.sha256 is the accepted
current input list. This is a local integrity record, not independently timestamped
preregistration. All 23 contract/retention tests passed before outcome execution.

Exactly one factorial outcome run was performed for this report. A separate
[post-hoc recount](recount.py) reads retained data without importing or executing
the simulator. It checks all 256 case identities against the allowed list, raw/final
row equality, per-cell metrics using a separate set-based closed form, and every
summary total. Its [result](results/recount.json) records artifact hashes. This
post-hoc diagnostic was not a frozen prediction and is not independent replication.
A second byte-for-byte outcome reproduction has not been run for this report.

No prediction changed after outcomes. The reviewed amendment is the only protocol
change. Source checksums still match. Failed-prediction and interrupted-run retention
were exercised with injected synthetic harnesses, not hidden or discarded grid runs.

## Boundaries and reusable outputs

The original operation is terminal before recovery; every recovery write succeeds.
Keys, when supported, are per-item, payload-stable and durable through the whole
horizon. Status capabilities and certificates are truthful. The model excludes
late execution, expiry, concurrent writers, malformed or conflicting records,
payload changes, retries that themselves time out, compensation and cancellation.
One item mask and three item identities do not establish transfer to arbitrary
services, item counts or failure patterns. No novelty or production-rate claim is made.

The [recovery skill](../../skills/recover-partial-batch/SKILL.md) teaches item-level
reconciliation and reporting. The [retention skill](../../skills/retain-experiment-evidence/SKILL.md)
packages the separately tested research-evidence lesson. Both pass format validation;
simulator/format checks do not demonstrate that a language model follows either.
The [capability routing entry](../../docs/partial-commit-capabilities.md) distinguishes
required contracts from actually exposed API/plugin capabilities.
