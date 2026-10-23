> Portable presentation derivative, not the executed original text. Only introductory
> provenance presentation differs; the scientific specification is unchanged.
> Original accepted SHA-256: 0ec8d71de2e4988aeb867abc05f1d36c59dc66d4d54cafad587b5ea14d772982.

# Combined recovery-contract study: frozen protocol v1

Frozen before simulator numerical outcomes. This is a pure finite, synthetic,
standard-library, single-process study, not an API client or model behavior test.
The reference public revision is 2dd04258dd9e50b1769f8e8af39b31dc25a8f5a7.
This portable presentation retains the scientific specification below unchanged;
see TRANSFORMATIONS.json for its accepted original text identity.

## Question and improvement criterion

Compose partial effects, late originals, finite keys, observation lag and failed
retries. Seek a new composition counterexample or a precisely tested conditional
safety/completion boundary. Test count and a favorable policy ranking are not the
improvement criterion. No synthetic frequency is a production rate.

## State and contracts

Two immutable intended items A and B. The original batch is admitted at t=0; its
reply is lost. Each item has one of three hidden fates: early effect at t=0, late
effect at the family's specified tick, or no effect. All original work becomes
terminal at the public specified bound. Recovery starts at t=1 with no item result.
An effect is irreversible and increments the evaluator's item counter.

Keys have none/item/batch scope. A batch-keyed replay must preserve the complete
original payload; item-keyed replay preserves the selected original item keys.
Keyless targeted writes remain an authorized recovery option only when evidence
justifies them. No key can be added retroactively to the original.

RESERVE: admission atomically checks and reserves each applicable key. Existing
unexpired entries suppress execution, including cached failures. The owner may
still execute after its reservation expires. Expiry does not cancel execution.
Retention starts at admission and is not extended by completion. CACHE: admission
checks only completed cached entries, making no in-flight reservation; an admitted
execution never rechecks at effect time. Item entries are installed when that
item's effect occurs, batch entries at attempt termination, including partial or
failed outcomes. Retention starts at cache installation. This cache contract does
NOT promise concurrent at-most-once behavior. Neither policy may infer that it does.
Entries are valid iff now < installation + TTL. Equality is expired independently
of scheduling. Original and recovery attempts use exactly the same key scope.

Retries either succeed (effect +1, positive reply +2, terminal +2), reject without
effect (reply/terminal +1), or time out (unknown reply +1, effect +3, terminal +4).
The outcome family is hidden, identical for every admitted retry in a case. The
public upper bound is +4 for all retries, never the hidden actual delay. Suppressed
replays reply after +1 with reliable positives for the suppressed original items,
not completion by fiat. A partly suppressed item-scoped batch executes only its
admitted items. Whole-batch cache/reservation suppression never fills missing items.

## Observations and information boundary

Every policy receives the same public contract, start time, item IDs, budget,
deadline, and its own charged observations/replies. It never receives original
item fates, actual retry outcome, evaluator counts, admission ownership, event
queue, or hidden terminal flags. Public observations show reliable positive
existence, not multiplicity. A certified terminal negative is exposed only if the
snapshot contains no effect and all attempts for that item have actually become
terminal by that snapshot. An opaque negative is never a terminal certificate.
Unavailable status has no usable item evidence. Known observation lag is charged:
a read started at t completes at t+1, sampling max(0,t+1-lag). At lag 0 a read sees
only effects/terminal events already ordered before it at the same tick. A stale
terminal certificate remains valid only for the attempts it covers; new writes
invalidate its use until their public bounds pass. No policy sees future events.

Separate public and hidden evaluator traces are saved. Public-only policy
functions are tested by swapping hidden fates while keeping their input identical.

## Policies, fixed before outcomes

- naive_inspection: read once immediately, treat every unseen item as absent,
  write those items without keys, and stop on the reply. Ignores stale/in-flight
  ambiguity and does not mistake a timeout for successful completion in reporting.
- blind_keyed: replay all original items with the original keys when available
  (keyless otherwise); repeat on unresolved replies until budget/deadline. Never
  reads. Uses no hidden knowledge or special protection from the scheduler.
- capability_fallback: adequate structural/temporal contract check. Key replay is
  allowed without inspection only for atomic RESERVE, original keys and a window
  strictly covering all original/pending/new retry execution bounds. Otherwise
  wait until a terminal snapshot is possible, read, and retry only certified
  terminal-absent items without keys. Following an unknown retry, wait its full
  public bound before another status read. Positive replies resolve items; cached
  failures or suppression do not. This baseline deliberately includes temporal
  adequacy; it is not a key-present strawman.
- horizon_aware: same evidence and full-horizon safety conditions, but skips an
  initially known-to-be-suppressed reservation replay and goes directly to the
  earliest terminal snapshot; then the same bounded evidence fallback. It trades
  an early result-reconciliation opportunity for one saved call. It is not assumed
  to dominate the adequate baseline. Both continue reconciliation within budget.

Certified terminal-absent retry targets are chosen from their latest read only,
excluding positively resolved or newly in-flight items. Key replay may happen at
most once before evidence fallback in the adequate baseline. The horizon policy
never does this initially redundant key replay. Waiting consumes time, not calls.
Every read/write costs one unit; no hidden free oracle read or uncharged mutation.
No new admission/read starts after the inclusive action deadline. A request begun
by the deadline may finish later. Early policy return does not stop the evaluator.

## Scheduler, horizon, enumeration and limits

protocol.json is the authoritative finite grid/family list, including held-out
families selected before outcomes. Every possible ordering of simultaneously
enabled events is explored at each tick, including observation versus effect,
termination versus observation, and decision/admission versus late effect. Tied
same-attempt effects are one atomic group; original effects grouped by equal tick.
Causal response successors cannot precede their triggering decision/effect.
There is no favorable fixed class tie priority. Equivalent event states may be
merged only if future state, public history, return status and metrics agree; the
path multiplicity and one complete witness ordering must be retained. The saved
outputs explicitly distinguish unique terminal traces from scheduler-path counts.
All pending events drain through the justified family horizon, at least deadline
+4+1, even after policy return. Any leftover event or crossed cap invalidates the
run rather than being silently treated as a success. All families are finite.

The initial small grid exhaustively crosses every protocol.json field, not all
possible real services. Held-out means distinct preselected structural families,
not sealed independent authorship and not statistical independence.

## Outcomes and evidence retention

Primary safety: any item counter >1 after all events drain. Also report duplicate
items/effects and duplicates whose effect occurs strictly after policy return.
Actual completion: all intended counters >=1. Justified completion: all items have
reliable positive evidence by return. Report unresolved items and return time,
charged calls/cost, actions, terminal path multiplicity and evaluator horizon.
Rates are descriptive finite-grid fractions only, separately by family and policy.

A checker written without importing simulator/policy code independently reconstructs
admissions, key suppression, scheduled effects, observations, counts and costs from
saved event traces and inputs. Tampered safety, counts, effects and costs must be
rejected. Source/test freeze precedes experiment run. Each result row is flushed
before aggregate predictions/assertions, and output directories are exclusive.
Predictions in protocol.json are retained whether true or false, including P5,
which is expected to expose the information/completion limit rather than a safety
proof. Store counterexamples before checking P1-P4. Never delete adverse rows or
rewrite an old freeze. Any needed correction gets an append-only amendment and a
new run; the original source and results remain available.

## Pre-run implementation plan

1. Freeze this protocol, grid, prediction list and input provenance.
2. Write failing contract/policy/retention/checker tests; retain red evidence.
3. Implement the pure event simulator and separately written recount/checker.
4. Pass tests, freeze source, then run the exhaustive and held-out families once.
5. Retain all rows and false predictions first, run independent checker, analyze
   minimal witnesses and conditional boundaries. Report hashes and resource ledger.
