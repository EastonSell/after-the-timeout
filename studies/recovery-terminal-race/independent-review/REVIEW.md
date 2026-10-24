# Independent review: terminal-read race boundary

## Verdict

Accept as a real, narrowly specified same-contract improvement to the published horizon_aware policy, following the horizon clarification now incorporated in PROOF.md. This is a post-hoc policy refinement and conditional theorem, not a globally dominating policy, a new service capability, a production result, or a modification of the original study's findings. The gain is avoidance of an uninformative charged read under adversarial same-tick ordering.

## Independent work performed

- Compared vendored model/checker byte-for-byte with the restored, previously verified published source. Both match their declared SHA-256 pins. This review did not independently contact the remote repository, so it establishes local artifact identity, not current remote HEAD.
- Re-ran the initial two unit tests, then all five final regression tests successfully. The final tests cover the defining gain, old-policy failure, short-deadline evidence loss, timeout completion/evidence distinction, and corrected horizon bound.
- Copied the executable into this review's reproduction directory and re-ran the entire matrix without changing the producer's data. All 5,953 decompressed path records reproduce exactly; all reported result fields other than elapsed time match.
- Wrote a separate public-history policy specification and reconstructed inputs from each trace. All 2,561 candidate paths and 8,529 decisions match. This closes the original checker's explicitly acknowledged lack of decision-function verification for this saved corpus.
- Ran 729 additional post-hoc cases spanning T={1,3,7}, lag={0,1,3}, none/item/batch scopes, certified/opaque/unavailable observations, all three retry outcomes and three representative original-fate pairs. All 1,680 paths passed independent environment/coverage checks and 4,752 independent decision checks. Safety holds throughout; certified nonreject cases satisfy the completion condition. These are reviewer stress tests, not independent held-out scientific confirmation or exhaustive contract enumeration.
- Confirmed that removing scheduler paths from the principal witness is rejected by the independent branch-coverage checker.

Evidence: audit.py, audit-result.json, source-and-horizon.json, reproduction.log, and reproduction/ in this directory.

## Why this is genuinely the same contract

The only live change is the public decision function. It receives the original allowlisted contract and public view. It does not receive original fates, the configured late tick, actual retry outcome, queue, attempt table, terminal flags or evaluator counts. It never substitutes the actual retry duration for the public +4 bound. The functions implementing admissions, effects, reads, reply handling, costs, deadlines, terminal events, queue expansion and completion metrics are unchanged.

The candidate first delegates to horizon_aware and preserves its stop and write decisions. Only certified read/wait scheduling changes from bound+lag-1 to bound+max(lag,1)-1. Thus it is exactly the old function on positive lag and on noncertified observation profiles. The independent decision audit checks the implementation's initial old-policy stop before applying the new barrier, which matters for faithful equivalence at deadline boundaries.

No free read is introduced. Waiting remains free in calls but consumes time. A read is admitted at t, costs one call and returns at t+1; its snapshot is max(0,t+1-lag). A keyless retry costs another call. The inclusive deadline constrains admission, not effects or replies. Actual completion is evaluated after draining pending events, not at policy return.

## Mathematical assessment

For a valid original terminal bound T>=2 and integer lag L>=0, put s=T+max(L,1). A read at s-1 returns strictly after T. With L=0 its snapshot is T+1; with L>=1 its snapshot is T. Every original effect and terminal event is therefore processed and within the snapshot, independently of equal-tick order. Certified status partitions items into reliable positives and terminal-absent targets. A single targeted keyless nonreject retry produces exactly the missing effects without duplication. This uses at most two calls and requires the sufficient action deadline D>=s.

The lower bound of two calls is valid as a worst-case bound over keyless contracts: early/early and never/never worlds are indistinguishable without a charged observation. One read cannot repair the latter; any nonempty unobserved write duplicates in the former. Randomization does not evade a guarantee on every path. This is not a lower bound for every individual case or a claim about arbitrary APIs with different operations.

The claimed scope across key scope, strategy and TTL follows from the candidate making only keyless recovery writes, not from the narrow timing grid. It still assumes the unchanged model's valid original-effect/terminal contract, finite integer time, no prior recovery attempts at entry, certified observation semantics, and nonreject retries. It does not establish optimal latency, minimum deadline, or optimality with richer actions.

The original policy's zero-lag read at T can precede the terminal event. Missing positives then do not yield the certificate needed to write. Its next read can exhaust a two-call budget. In the principal witness, horizon_aware has five scheduler paths, two physically incomplete; terminal_barrier has six, all safe and complete. The policies generate different trees. Scheduler path counts are neither paired trials nor probabilities.

## Correction discovered in review

The draft initially called s+4 a sufficient horizon while allowing budgets larger than two. That bound suffices for a deliberately capped read-plus-retry schedule but not for the executable candidate's optional subsequent reconciliation.

Concrete counterexample: T=2, L=2, budget=3, D=10, timeout_commit, original A early/B never. With H=8=s+4, the simulator correctly rejects pending events beyond its horizon. With sufficient H, the final reconciliation read completes at 10. This changes neither safety nor eventual physical completion; it invalidated the stronger drain-bound wording.

The producer accepted and documented the correction. For the actual finite-budget implementation, D+4 suffices: all waits are scheduled by D, reads finish by D+1, retry terminal events finish by D+4, and their same-tick decisions either stop or remain under the same admission bound. The completed matrix already used horizons large enough, so its data did not require correction.

## Limits that must stay visible

1. No global dominance. With T=4,L=0,D=3 and early/early originals, the old policy gets both positives from its deadline-admitted read, whereas the candidate returns without evidence. Both are physically complete; only the old one is justified complete. Evidence latency can also increase by one tick when the old read happens to suffice.
2. Actual completion is not justified completion. With a two-call timeout retry, the candidate returns unresolved at 6 in the named witness and the effect arrives later. Its positive result cannot be described as confirmed completion by return or completion by the action deadline.
3. The 972-case grid has 20 gains in guaranteed actual completion and 10 in guaranteed justification, with no losses inside that grid. The grid omits the shorter deadline needed for the retained regression. These counts are descriptive of a selected post-hoc matrix, not success rates, general dominance, or evidence of statistical significance.
4. The existing checker independently verifies environment semantics and enabled-branch coverage, not the candidate's policy-selection rule. Relabeling a copy activates its useful certified-write safety audit but is not independently implementing the policy. The new review-side specification adds corpus-level decision verification; universal correctness still rests on the explicit argument and assumptions.
5. The five final unit tests cover the defining witness and three important limitations, not the general theorem. The exhaustive saved matrix and analytic proof are the substantive evidence. No claim of empirical systems impact, broader novelty or dissertation-level sufficiency follows from this small simulator refinement alone.

## Final assessment

The strongest justified contribution is: under the unchanged published event model, postponing a zero-lag certified read by one tick attains a worst-case optimal two-call safe eventual-completion bound under an explicit sufficient deadline and nonreject retries. It exposes a real terminal/read race in the old policy while honestly retaining the cost in evidence latency and short-deadline reconciliation. Keep the qualifier 'eventual actual completion' and the post-hoc status attached to this claim.
