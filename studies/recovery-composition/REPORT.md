# Combined recovery contracts: result and limitations

## The failed prediction is the first result

Frozen P5 said: "horizon_aware completes whenever a safe omniscient schedule exists
under the same budget and deadline." It is FALSE. It remains false in the saved
prediction file, with its original wording in the untouched protocol. It was not
converted into a passing claim after results. The run succeeds because P5 was
predeclared falsifiable but not a required safety assertion.

The first retained witness has A committed early, B never committed, an item
reservation key expiring at t=2, and opaque status. The horizon policy waits,
observes A, declines to treat missing B as terminal evidence, and returns B
unresolved. A clairvoyant schedule would write only B. That benchmark knows hidden
truth and is not a realizable competing policy. This witness alone does NOT prove
that the algorithm is information-theoretically optimal or that all completion
losses are necessary.

## What improved

The old partial-batch model excluded late originals, finite expiry and failed
recovery writes; key-lifetime calls consumed no logical time and excluded partial
or concurrent effects. This new model composes those hazards with explicit
admission-reservation versus completion-cache semantics, charged observation lag,
retry failures, full post-return event drainage, and every allowed event tie order.

A concrete new composed counterexample, retained in
supplementary/composed-post-return-counterexample.json:

1. At t=0 the keyed original reserves A/B until t=2. A commits; B may execute at
   t=8, and the original becomes terminal at t=9.
2. A blind replay at t=1 is suppressed while its key is valid. Its reply at t=2
   knows A but not B.
3. A replay admitted exactly at expiry t=2 is no longer suppressed. It times out
   at t=3 but its effects are still scheduled for t=5.
4. The third replay at t=3 is suppressed by that new reservation. The policy
   exhausts its three charged calls and returns at t=4, with B unresolved.
5. Recovery effects execute at t=5; the original B executes at t=8. Both duplicate
   effects occur strictly after return. Final counts are A=2, B=2.

The key being valid at an earlier replay did not cancel or protect its expired
owner's future effect. The B duplicate remains the substantive issue even if an
optimized item client omits already-confirmed A. CACHE-only dedup is a separate
contract: without an admission reservation, overlapping executions can both be
admitted even while retention is long. A batch cached partial response can also
suppress execution without completing missing items.

## Frozen experiment

Local protocol freeze preceded numerical tests. Source/tests and the complete
input manifest were then frozen before full-grid execution. The 800 inputs are:
486 exhaustive small-grid cases, 128 later-original/expiry cases, 96 cases lacking
terminal evidence, and 90 tight-deadline/budget cases. The latter three are
preselected structural holdouts, not independently authored or sealed cases.

Four public-observation policies share the same contract metadata and charged
budget in each case. Hidden original fates, true retry outcomes, evaluator counts
and pending queues are not policy inputs. The adequate baseline checks concurrency,
scope, payload and full-horizon retention; it is not a key-present strawman.

The simulator explored 319,968 states and retained 86,796 complete scheduler
paths. Every enabled same-tick ordering is enumerated, with fixed explicit atomic
batch-effect groups and causal successors. Half-open expiry is arithmetic at
admission, not a favorable expiry-event priority. All pending events drain after
return. The independent checker reconstructs the queue/state/evidence and uses a
prefix-tree coverage certificate, including omission and tampering tests. A
separate saved-output recount passed all 3,200 groups and all paths.

## Finite-case outcomes, not production rates

A case is unsafe if ANY allowed scheduler path duplicates an item. "Guaranteed
complete" means EVERY path eventually has all intended effects. "Guaranteed
justified" means EVERY path has reliable positive item evidence by policy return.
These are different outcomes; neither positive evidence nor completion certifies
absence of duplicates.

| Policy | Unsafe cases / 800 | Guaranteed complete | Guaranteed justified |
|---|---:|---:|---:|
| naive_inspection | 356 | 658 | 344 |
| blind_keyed | 368 | 570 | 300 |
| capability_fallback | 0 | 554 | 423 |
| horizon_aware | 0 | 554 | 417 |

The two adequate policies have zero duplicate effects over all their enumerated
paths. This is a bounded-model result, not a production guarantee. The horizon
policy is NOT superior: it has the same guaranteed completion count and six fewer
guaranteed-justification cases than the adequate baseline.

Under the same exogenous case/budget, horizon-aware has a lower worst-case call
count in 108 cases and the same worst-case call count in 692, but is strictly
slower in every ordering in 18 cases. The baseline is strictly slower in every
ordering in 108 cases. Horizon-aware has possible completion in eight cases where
the baseline has none, without increasing guaranteed-completion count. These are
scheduler-envelope comparisons, not paired stochastic effects or expected costs.

The simple non-dominance witness is two early effects with item reservations
lasting seven ticks: keyed replay can reconcile both positives at t=2 for one
call; skipping it waits for a status result at t=4 for the same call cost. In tight
deadlines, skipping that replay can lose obtainable positive evidence. Conversely,
a redundant initial replay can consume a call needed for later reconciliation.

## A precisely tested conditional boundary

Post-hoc, not a new preregistered superiority claim: in 452 frozen cases (2,533
horizon-policy scheduler paths), all intended effects complete when status is
certified, recovery either succeeds or times out with a scheduled commit, the call
budget is at least three, and the admission deadline is at least
original_terminal + observation_lag + 1. All those paths are safe.

Why the finite condition is sufficient: schedule the first read so its snapshot
can reach the original terminal bound. If lag=0 and the read wins the terminal tie,
a second read reaches the next tick. At most two reads precede one targeted write.
Reliable terminal absence rules out every older pending effect for those items.
A successful or timeout-committing retry then supplies each missing effect, and
the justified evaluation horizon drains it. An acknowledgement may still be lost,
so actual completion does not imply justified completion. Rejected retries or
smaller budgets/deadlines invalidate this completion condition.

The bounded safety invariant is separate: keyless writes require certified
terminal absence covering every admitted predecessor and are not repeated from a
stale certificate after a new write. Keyed baseline replay requires an atomic
reservation with retention strictly covering every possible execution bound.
These arguments do not transfer to an undocumented real service contract.

## Supplementary two-world boundary, explicitly post-hoc

The original P5 failure above is preserved unchanged. A new two-world probe under
the same frozen service semantics is OUTSIDE the 800-case manifest:
- Both worlds have A early, unavailable status, original item-key reservations
  valid on [0,2), public original terminal bound t=4, success recovery behavior,
  three charged calls, admission deadline t=10 and evaluation horizon t=15.
- In one world B never executes; in the other its original effect executes at t=3.

The supported alphabet is integer-tick waits; status reads costing one call and
one tick; writes of A, B or AB using original keys or keyless, costing one call;
and stop. The client waits for each reply before another request. There is no
cancellation, compensation, free status oracle or arbitrary new observation.

The retained horizon and blind policy trace sets are identical across worlds,
although hidden counts differ. A separate checker that imports no simulator
enumerates all 60 first-mutation choices (10 ticks × 3 target subsets × 2 key
choices). Exactly three are safe in both worlds: original-key writes at t=1.
They are all suppressed, return at t=2 with identical positives, and neither
create a new effect nor renew a key. Reads/waits/stop do not alter that state.
After t=2, any write that could complete B in the never world duplicates an item
in the late world. Thus the safe action class closes without completing B in the
never world. The finite pair admits no policy guaranteeing both safety and
completion within this exact alphabet/horizon. This does not show the tested
horizon algorithm is generally optimal or explain every P5 failure.

The trace probe and independently calculated safe-action closure are retained in
supplementary/indistinguishability-pair.json and safe-action-closure.json, with
explicit post-hoc labels. The checker and all costs/boundaries are inspectable.

## Limits and next improvement target

This is finite deterministic semantics, not a proof for unbounded schedules,
unknown bounds, clock skew, crashes, arbitrary retry layers, undocumented service
behavior or model adherence. Atomic grouped effects and truthful public contract
metadata are strong assumptions. CACHE here explicitly lacks in-flight atomicity;
not every real service's cache does. Path counts are not probabilities, and no
workload distribution, production failure rate, time/token saving or statistical
agent-behavior benefit is inferred.

Next loop: design a public-only, budget/deadline-aware reconciliation frontier
that chooses early positive-result retrieval versus terminal-negative waiting.
Compare it against an equally optimized capability baseline, retaining this
non-dominance and failed-P5 evidence. A useful jump would remove the six known
justification losses without introducing duplicates or merely replacing them
with more abstention, not increase test count or claim victory over blind replay.
