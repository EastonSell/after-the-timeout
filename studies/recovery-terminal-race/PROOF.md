# A terminal-read race costs a recovery call

Post-hoc discovery under the published finite simulator, not a change to its frozen predictions, input corpus or reported 800-case results. No production-rate or unrestricted-policy superiority claim is made.

## Source identity

Repository: EastonSell/after-the-timeout, reference commit d301e982db65deed6c065063ac243a1e0c0888c7.
Model: studies/recovery-composition/source/model.py; SHA-256 7379f9464a8b00b68cca1b7cbce67d453335b5315be2959b9c2b85d2fc043766.
Checker: studies/recovery-composition/source/checker.py; SHA-256 9751e07387d849ca8b99592ff7b655235d8596a226a06bd92a38095a7e5b8665.
These are verbatim local copies of the previously verified public source. Existing publication receipts establish the reference identity; this investigation did not re-fetch remote HEAD or publish anything.

## New sufficient boundary, with a sharp call budget

Assume the published synchronous, integer-time model, no recovery attempts before start t=1, a public original-terminal bound T >= 2, integer observation lag L >= 0, certified status, at least two charged calls, and a retry outcome that is success or timeout_commit. A timeout may return before its later effect. The action deadline is inclusive; calls admitted by it may finish later. All pending events, including post-return effects and any additional reconciliation reads, must be drained. For the explicitly capped two-call schedule below, a sufficient horizon is T + max(L,1) + 4. For executable terminal_barrier with a larger budget and looser deadline, use a horizon covering its full pending queue; D+4 suffices because read admissions occur by D and complete within one tick, write admissions occur by D and terminate within four ticks, and waits are scheduled only through D.

Set s = T + max(L,1). Read at s-1, receive the result at s, then keylessly retry precisely certified terminal-absent items at s. This is feasible when D >= s. The policy uses only public metadata and ordinary charged evidence, not hidden fates, actual retry outcome, pending queues, or realized terminal flags.

Proof:
1. For L=0, delivery time s=T+1 is strictly later than every event at T. Its snapshot is T+1. For L>=1, delivery time s=T+L is strictly later than T, and its snapshot is T. Thus all original terminal events have already executed, and every original effect is within the snapshot. This argument is independent of every within-tick permutation.
2. Each intended item is consequently either positively observed, or certified terminal-absent. A certified-absent item has no previous effect and no remaining original attempt capable of an effect. Items with positives are excluded from the write.
3. A single keyless retry of certified-absent items cannot duplicate originals. Under success or timeout_commit it eventually produces one effect per target. Other items already have their single original effect. The first read and this retry cost at most two calls; waiting costs zero.
4. Therefore all paths eventually complete without duplication. This is actual completion, not necessarily justified completion at return. In particular, budget-two timeout_commit can finish its effects after returning unresolved.

The proof applies to the simulator semantics, across key scope/strategy/TTL, because the repair is keyless and follows certified absence. The executable timing matrix isolates scope=none rather than pretending to enumerate every scope.

Two calls are worst-case necessary in this information/action model: fix the same keyless public contract and successful retry outcome, with hidden world E having both originals early and hidden world N having neither original effect. A policy with no initial item evidence and at most one charged operation cannot guarantee both safety and completion across E and N. If that operation is a read (or there is no operation), N remains incomplete. If it is any nonempty write, the same pre-observation decision occurs in E and duplicates an item. Waiting does not distinguish the worlds. This is a worst-case information lower bound, not a claim that every individual case needs two calls. No global minimum-deadline theorem is claimed.

## Why the published policy misses the two-call boundary

At L=0 its read starts at T-1 and is delivered at T. The scheduler may execute the read before the original terminal event. Even if all effects have already occurred or failed to occur, the read then lacks a certified negative. A second read consumes the second call, leaving no call for the repair. The original policy's next decision can also run before or after the terminal event; the enumeration includes both orders.

The new policy changes only earliest read scheduling: replace bound + L - 1 with bound + max(L,1) - 1, where bound is the public maximum of original-terminal and last-write upper bound. It retains the original policy's public-state inputs, stop decisions, charges, certificate requirements, targets and retry mechanics. For positive lag this expression is unchanged. Nothing waits for a hidden realized terminal flag.

## Exact witness

T=4, L=0, D=5, call budget=2, no keys, certified status, original A=early and B=never, retry=success, horizon=12.

Published horizon_aware: five complete scheduler paths, of which two are incomplete. A failing path waits to 3, reads 3->4 before original terminal, sees A but cannot certify B; reads 4->5, now certifies B, and stops with no call remaining. Three other paths repair successfully. These path counts are not probabilities.

terminal_barrier: six complete scheduler paths, all safe and complete. Wait to 4, read 4->5, see A and certified-absent B, write B at 5, effect at 6, successful response at 7. The deadline permits the admission at 5 and later completion. Different policies induce different scheduler trees; no one-to-one pairing of their paths is asserted.

## A dominance boundary, not a universal winner

The delayed read is not universally superior. With the same T=4, L=0 contract but both originals early and D=3, the published policy admits a read at 3 and receives both positives at 4. terminal_barrier cannot start its read at 4 because the deadline has passed, so it returns without that evidence. Both worlds are physically complete but the delayed policy loses justified completion. This witness is retained in witnesses.json.

Waiting can also delay evidence by one tick when the old read already suffices. The proposal improves a worst-case call/completion boundary; it is not a universal Pareto improvement in call cost, latency and evidence. The known P5 counterexample and the published six-case evidence loss are not being relabeled as this finding.

## Bounded exact experiment and verification

run_boundary.py enumerates 972 new post-hoc cases: T in {2,4}, L in {0,1,2}, budget in {1,2,3}, D in {T+max(L,1)-1, T+max(L,1)}, all nine original-fate pairs with late=T-1, and retry outcome in {success,reject,timeout_commit}. It adds four named witnesses, totaling 976 cases and 1,952 policy groups. The old and candidate policies are evaluated under the identical exogenous input in each pair.

Result: 31,350 explored states and 5,953 complete scheduler paths. All groups passed the independent published queue/evidence reconstruction and full enabled-branch coverage check. On the 972-case grid there are 20 gains in guaranteed actual completion and 10 in guaranteed justification, with zero losses on either metric inside this grid. This deliberately selected grid is not a representative distribution; the separate shorter-deadline witness disproves global justification dominance. The theorem antecedent holds in 216 grid cases, with 700 candidate paths; every such path is safe and complete. Reject cases are included as negative controls but excluded from the sufficient theorem.

Hard bounds: 100,000 states per group, 2,000,000 total states, 120 wall seconds, and 50,000,000 compressed output bytes. The completed run took about four seconds; exact elapsed time is in RESULT.json. Exhaustive means all scheduler choices within these explicit cases, not all possible contracts.

The checker imports no simulator code. To apply its existing certified-write safety audit to the new policy, run_boundary.py relabels only a deep copy of each candidate trace as horizon_aware for validation. Saved traces retain terminal_barrier. This does not independently prove the candidate's action-selection function: policies.py is directly inspectable, while the proof above and the checker establish its evidence/scheduling boundary. The source model and checker bytes are pinned before each run. No original scientific data or published source was modified.

Reproduce: python -m unittest -v; python run_boundary.py. paths.jsonl.gz contains all complete traces; groups.json includes individual coverage hashes; witnesses.json preserves the explicit positive and negative results. red-tests.txt records the intended two-call test failing when terminal_barrier initially delegated unchanged to horizon_aware; green-tests.txt records the timing adjustment passing. This is not a replacement for an independent reviewer.

## Review correction

Independent review caught an initially overbroad numerical horizon statement: s+4 drains the capped two-call schedule, but not necessarily extra reconciliation reads when the executable policy receives more than two calls. The statement above now distinguishes these cases and requires full queue drainage. The completed matrix already used a longer horizon and its saved results were not affected.
