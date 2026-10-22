# Start here: a lost reply is not a failed write

**The question:** After a tool request times out, what do we know happened, and what would make a retry justified?

This repository maps public tool capabilities and tests small failure/recovery models. Its executable examples teach a distinction: **the service's actual state and the caller's justified knowledge can differ**. Simulator tests do not prove that a language model follows a skill or that a real service offers the same guarantees.

## One write, two different hidden histories

Imagine an authorized request to add item A:

1. The request never commits; its reply is unavailable.
2. The request commits, but its reply is unavailable.

The caller can see the same timeout in both cases. Retrying case 1 can complete the work. Retrying case 2 can add a duplicate. A timeout alone does not identify which history occurred.

![Lost-reply sequence: the caller submits an operation, the service commits one effect, and the reply is lost. A retry with the same ID creates a second effect without deduplication, reuses one effect under a valid durable-key contract, or can create a second effect after key expiry. A timeout before commit looks identical to the caller.](figures/lost-reply-sequence.svg)

An **operation ID** can merely label a request or correlate a reply. **Idempotency** means the service promises repeated attempts will not create an additional effect under a defined contract. Reusing a string is not enough. Ask whether the service supports deduplication, which operation/payload the key covers, and how long the guarantee lasts.

## Try the four-case offline example

From the repository root, using Python 3.10+ and its standard library:

```sh
python docs/examples/lost_reply.py
python -m unittest discover -s docs/examples -p 'test_*.py' -v
```

The [simulation](examples/lost_reply.py) deliberately retries once with the same ID. Its evaluator can count hidden effects; the caller cannot learn that count from the lost reply.

| Constructed case | First caller observation | Hidden final effects after retry |
|---|---|---:|
| Commit, no deduplication contract | Reply unavailable | 2 |
| Commit, durable payload-bound key | Reply unavailable | 1 |
| Commit, key expires exactly at retry | Reply unavailable | 2 |
| No initial commit, no deduplication | Reply unavailable | 1 |

These are chosen rules, **not new benchmark results or real API guarantees**. The example has atomic instantaneous calls, one sequential client, explicit logical time, and no late in-flight original. A retained key rejects a changed payload; cache hits do not renew its lifetime. At expiry the key's protection ends, while the committed effect remains.

## How controls turn the example into a research question

A **control** changes a capability while holding the request and fault fixed. Comparing no deduplication, a durable key, and an expiring key shows that retry safety depends on the contract, not the ID's spelling.

Another control is **status inspection**: read evidence about the exact operation before retrying. A reliable committed result can settle the uncertainty. A missing, stale, partial, or unsupported lookup need not prove noncommit. A terminal negative must also rule out an original request still committing later. Sometimes the honest result is **unknown**, not success and not failure.

The [public capability catalog](public-capabilities.md) and [root interface map](../README.md#public-interface-atlas) explain discovery, schemas, paging, writes, and status as distinct capabilities. Do not invent an unavailable lookup or treat a transport-success envelope as proof of application success. Public reusable [recovery](../skills/recover-uncertain-operation/SKILL.md), [partial-batch](../skills/recover-partial-batch/SKILL.md), and [checkpoint](../skills/checkpoint-handoff/SKILL.md) skills organize these decisions; their format checks are not model-adherence evidence.

## Reading the actual results without overclaiming

- [Baseline](../README.md#baseline-result): blind retry produced **6 duplicate commits**, while inspect-first produced **0**, used **84 rather than 72 calls**, and left **6 outcomes unresolved**. Sixteen constructed scenarios appear in three seeded orders, not 48 independent real incidents. Avoiding duplicates and completing work are different outcomes.
- [Stale status](../milestones/stale-status/README.md) and [key lifetime](../milestones/key-lifetime/README.md): one stale negative or an expired key can remove the baseline's protection. In the lifetime study the conservative guard had zero extra commits but 10 unresolved outcomes. Those are synthetic cells, not production failure probabilities.
- [Late commits](../milestones/late-commit/README.md): an original can still commit after the policy reports success. Final settled state matters, not just the state at the return statement.
- [Partial commits](../milestones/partial-commit/REPORT.md): batch recovery needs item-level evidence. With durable item keys the blind baseline was also exact-once in all 32 of its cases and used fewer calls. Inspection is not universally more efficient.

Read completion, duplicates, unknown outcomes, and calls separately. These studies do not measure token cost, realistic wall-clock latency, real-service reliability, or general agent intelligence.

## Inspect safely, then reproduce

Use the [full test matrix and safe reproduction guide](reproduction.md). From the root:

```sh
python tools/run_all_tests.py
python tools/reproduce.py --study baseline --out ../atlas-baseline-run-001
```

Choose a new output path outside the checkout with an existing parent. The wrapper runs preserved sources in a temporary copy and does not overwrite historical results. Do not directly run legacy experiment entrypoints against the source checkout: they can replace their archived outputs. Later studies have separately linked suites; the aggregate matrix is not every future test automatically.

For a more advanced public-API example, [content-addressed Git tree recovery](../skills/recover-uncertain-operation/references/content-addressed-tree-recovery.md) distinguishes an identical immutable tree from a new timestamped commit or a mutable branch update. That special identity argument is not a blanket retry rule.

**Useful next questions:** What exact retention/freshness guarantees does the target service publish? Can original work still be in flight? Can a batch partially commit? Does a persisted checkpoint identify the payload and evidence without pretending to grant permission? For live systems, resolve those service-specific contracts before turning this toy retry into action.
