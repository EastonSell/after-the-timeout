# After the Timeout

A tool call times out. Did the write fail, finish, or leave only part of a batch committed? Retrying can create duplicates; stopping can leave legitimate work unfinished.

## Abstract

This project studies recovery when a failed response leaves a write's outcome uncertain. Deterministic contract models explore status inspection, key lifetime, late commits and partial batches; separate local-process studies test selected mechanisms with real processes and SQLite. The completed [crash/restart study](studies/sqlite-crash-restart/README.md) asks how commit state and retained key/payload binding affect recovery after process death. Across 24 selected trials (six conditions, four repetitions each), an unkeyed retry after COMMIT duplicated the original effect in 4/4 trials, while a same-key, same-payload retry preserved one effect in 4/4. Before COMMIT, changing the payload produced one effect but failed the original goal in 4/4. These results distinguish duplicate prevention, requested-task completion and successful responses. They establish bounded implementation behavior, not production exactly-once guarantees, power-loss durability or model/agent efficacy.

## Research question

**When a local SQLite write loses its reply across process death, how do commit state and a retained payload-bound key change duplicate effects and completion of the original request?**

The original request is payload **A**. Recovery either retries A without a key, retries A with the same key, or sends changed payload **B** with that key as a control. Success on the original task means retaining exactly one A—not merely receiving a 200 response, finding one database row, or matching a predicted outcome.

The broader question—how an agent should recover through arbitrary real service contracts—remains open. The finite question above is answered by the released [crash/restart report](studies/sqlite-crash-restart/REPORT.md), rather than by combining unrelated experiments.

## Method and evidence

The [24-case protocol](studies/sqlite-crash-restart/source/protocol.json) crosses two crash barriers with three recovery requests, repeated four times. A service worker is stopped with SIGKILL either immediately before the Python COMMIT call or after it returns. Its death is confirmed before a distinct process reopens the same file-backed SQLite database and performs one recovery write. The original response is absent in every trial.

The [report](studies/sqlite-crash-restart/REPORT.md) and [review record](studies/sqlite-crash-restart/REVIEW.md) describe checks of raw process receipts, final databases and recovered copies of crash images—not just the runner's summary. This is one-host file/receipt IPC, not an HTTP timeout experiment. The earlier [HTTP/SQLite study](studies/local-process-recovery/README.md) is separate evidence with a separate denominator.

## Answer and results

**Under these selected schedules, retaining the same key and payload prevented the post-COMMIT duplicate; reusing the key identifier did not preserve the original goal when its payload binding had never committed.**

| Crash barrier | Recovery request | Valid / planned | Final effects | Recovery response | Original A outcome |
|---|---|---:|---|---|---|
| Before COMMIT call | No key, A | 4 / 4 | One A | 200, committed | Exactly one A |
| Before COMMIT call | Same key, A | 4 / 4 | One A | 200, committed | Exactly one A |
| Before COMMIT call | Same key, B | 4 / 4 | One B | 200, committed | A absent |
| After COMMIT returned | No key, A | 4 / 4 | Two A effects | 200, committed | A duplicated |
| After COMMIT returned | Same key, A | 4 / 4 | One A | 200, deduplicated | Exactly one A |
| After COMMIT returned | Same key, B | 4 / 4 | One A, no B | 409, rejected | Exactly one A retained |

All 24 trials were valid and matched their literal predictions; none was invalid, not run or a prediction failure. **That does not mean all recoveries succeeded:** the predictions include four duplicated-A outcomes and four outcomes with no original A. Before COMMIT, neither A nor the key binding survived, so B could claim the key. After COMMIT, the retained binding rejected B. The [complete report](studies/sqlite-crash-restart/REPORT.md) retains these controls and all cell denominators.

## Reproduce and check

Python 3.10+ standard library only; no credentials or installation are needed for these checks. From the repository root:

```sh
# Historical seven-suite matrix: 92 software tests.
python -B tools/run_all_tests.py

# Crash/restart apparatus: 30 synthetic software tests, not crash trials.
(cd studies/sqlite-crash-restart/source && python -B -m unittest discover -s tests -v)

# Recount the separate partial-batch study's 256 saved rows; no simulator run.
python -B milestones/partial-commit/recount.py
```

The historical aggregate does not discover every later study. Its release-tool tests reproduce deterministic simulator fixtures in temporary workspaces without replacing historical outputs. The crash suite uses synthetic interruptions and in-process fixtures; passing it does not independently recheck the 24 empirical trials.

**To audit the 24 retained trials**, use a fresh disposable copy of the complete published crash/restart package. In `studies/sqlite-crash-restart`, verify its files, inspect the archive paths, extract the retained evidence, then run the saved-evidence auditor:

```sh
sha256sum -c PUBLIC-SHA256SUMS
tar -tzf retained-evidence.tar.gz
# After confirming the documented relative prefixes and no source overwrites:
tar -xzf retained-evidence.tar.gz
python -B verify_public_derivative.py
```

The [study's reproduction guide](studies/sqlite-crash-restart/README.md#unpack-and-verify-retained-evidence) explains the archive layout and original/public identity mapping. The archive and `ORIGINAL_PUBLIC_HASHES.json` are required: a source-only copy is insufficient for the raw-evidence audit. Public metadata redactions do not retroactively change the original pre-data freeze. This audit reads saved trials and reopens temporary copies of crash images; it does not launch a new crash matrix.

A **new experiment** is different from rechecking evidence. The crash study requires a fresh source freeze, independent admission and bounded supervision for a new run; see [New replication](studies/sqlite-crash-restart/README.md#new-replication). To reproduce an earlier deterministic simulator study instead, use the [safe wrapper](docs/reproduction.md), for example `python -B tools/reproduce.py --study baseline --out ../atlas-baseline-run-001`. Choose a new output directory outside the repository with an existing parent. Legacy `run_experiment.py` entrypoints can overwrite historical results; do not use them in place.

Historical manifests cover their recorded snapshots, not all later additions. Keep the original sources, results and manifests unchanged when checking or extending this release.

## Limitations and open questions

- These are six selected conditions with four repetitions each, not independent production incidents or a failure-rate estimate.
- Both barriers are **outside** the COMMIT call. SIGKILL kills an application process, not the OS or power supply; no result establishes power-loss durability or behavior during SQLite's internal commit protocol.
- The crash study has no competing recoverer, automatic replay, expiring/lost keys, distributed host, replication, partition or unreliable-storage condition. Confirmed local worker death is not evidence that a remote operation stopped after a timeout.
- A finite successful keyed control is not a general exactly-once guarantee. Earlier studies show that stale status, key expiry and late original execution can invalidate recovery strategies under weaker contracts.
- Software tests and local review records are not external certification, timestamped preregistration or evidence that a language model follows a written recovery workflow.

The current release answers the finite crash/restart question above and retains the earlier studies' adverse results. Open research questions include how these crash/restart observations change with overlapping recovery or key expiry, and whether model-assisted recovery improves **duplicates, actual completion, justified completion, unresolved work and cost** under controlled budgets. Those require separate experiments; this release does not claim to answer them.

## Explore the earlier studies

- [Trace one uncertain write by hand](docs/START_HERE.md).
- [Read the research overview](docs/RESEARCH_OVERVIEW.md) for the earlier questions, controls, related work and proposed behavioral evaluation.
- [Browse the completed milestones](MILESTONES.md), [partial-commit report](milestones/partial-commit/REPORT.md) and [public capability catalog](docs/public-capabilities.md).

## Baseline result

**Inspecting first helped under the baseline's contracts.** Blind retry produced six duplicate commits across 48 trials; inspect-first produced none, using 84 rather than 72 calls and leaving six outcomes unresolved. Those trials reorder 16 unique scenarios, so they are not 48 independent incidents.

## Follow-on studies

**Weakening the contracts exposed new failures.** A [stale status read](milestones/stale-status/README.md) defeated inspect-first recovery. [Key expiry](milestones/key-lifetime/README.md) restored duplicate risk. [Late original commits](milestones/late-commit/README.md) produced duplicates even after a policy had returned success. A completion report needs a stated observation horizon.

**Partial batches need item-level reasoning.** In [256 constructed cases](milestones/partial-commit/REPORT.md), no-key evidence-only recovery avoided extra effects but left outcomes unresolved. With durable item keys, both the capability-aware policy and blind keyed baseline were exact-once in all 32 cases of their respective groups; the blind baseline used fewer calls. The result depends on terminal original operations and truthful, durable contracts.

**Handoff evidence needs separate validation.** [Checkpoint tests](milestones/checkpoint-handoff/README.md) check missing or mismatched artifacts. One [held-out fictional-case review](milestones/handoff-review/results/REPORT.md) matched 48 predeclared written fields across eight cases. That small review does not measure live execution or approval compliance.

## Public interface atlas

The [capability catalog](docs/public-capabilities.md) separates tool discovery, schemas, pagination, writes and status observation. Check the actually exposed operation and its contract before choosing a recovery path. Vendor documentation describes possible interfaces; it does not establish an account's access or a connector's capabilities.

## Reuse the workflows, then test them

Original public skills cover [uncertain writes](skills/recover-uncertain-operation/SKILL.md), [partial batches](skills/recover-partial-batch/SKILL.md), [checkpoint handoffs](skills/checkpoint-handoff/SKILL.md), [evidence retention](skills/retain-experiment-evidence/SKILL.md), [release validation](skills/release-validation/README.md) and [plain language](skills/plain-language/SKILL.md). Their format, fixture and software checks are recorded separately from behavioral efficacy.

Original code, skills, documentation and synthetic results are [MIT licensed](LICENSE). Linked standards and papers retain their copyrights. The catalog describes public interfaces rather than anyone's account access.

## Recovery composition study

[Complete scheduler-path evidence and bounded recovery analysis](studies/recovery-composition/README.md) retain the failed completion prediction P5 and show no composed-policy superiority: `capability_fallback` has 423/800 universally justified cases versus 417/800 for `horizon_aware`. The six losses instantiate one structural defect, not six independent discoveries. Supplementary impossibility reasoning is limited to its declared action alphabet, and cache semantics are model-specific. These are offline contract-model results, not real API or agent-behavior guarantees.

The [saved-trace policy-attribution supplement](studies/recovery-composition/policy-attribution/README.md) checks original per-row dynamics first, then whether the named policy selected each recorded action. It is post-hoc verification of retained evidence, not a new policy result or a whole-dataset completeness proof.

## Real-process evidence checks

The [local-process recovery study](studies/local-process-recovery/README.md) uses actual loopback HTTP client/service processes and a file-backed SQLite database on one host. Its [client-provenance supplement](studies/local-process-recovery/client-provenance/README.md) adds post-hoc checks tying observed failures to declared requests, process identities, saved outcomes, and concurrent-recoverer receipts. It composes the existing whole-matrix verifier without changing the primary evidence; it does not establish distributed-system or provider guarantees.

## Watch the narrated explanation

[![Narrated concept illustration](docs/animations/narrated/poster.png)](docs/animations/narrated/concept.mp4)

[56.1-second narrated MP4](docs/animations/narrated/concept.mp4) · [Complete transcript](docs/animations/narrated/transcript.txt) · [Captions](docs/animations/narrated/captions.vtt) · [Editable source and reproduction](docs/animations/narrated/RENDERING.md)

Speech-led Manim animation with a synthetic stock voice. Synthetic contracts · not real api guarantees. This is an explanatory upgrade, not a new experimental result. Captions have approximate sentence timing. The [static-first viewer](docs/animations/narrated/index.html), poster and complete transcript provide a no-motion alternative. The original silent version and its historical QA remain unchanged below.

## Watch the concept in 24 seconds

[![A same-ID retry produces two hidden effects without deduplication, one under a retained durable payload-bound key, and two after key expiry in an atomic sequential toy.](docs/animations/poster.png)](docs/animations/concept.mp4)

[24-second Manim MP4](docs/animations/concept.mp4) · [Optional GIF preview](docs/animations/concept.gif) · [Text transcript](docs/animations/transcript.txt) · [Captions](docs/animations/captions.vtt)

Rendered with Manim Community 0.22.0. Synthetic contracts · not real API guarantees. No audio. The poster and transcript provide a no-motion alternative. The downloaded [HTML viewer](docs/animations/index.html) is static by default and never autoplays.

The simulators test explicit policies under declared contracts. They do not estimate production incident rates or show that a language model will follow a written skill.

