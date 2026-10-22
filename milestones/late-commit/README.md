# A negative status does not rule out a future commit

This additive study extends the [key-lifetime experiment](../key-lifetime/README.md)
with a logical event queue. All previous study files remain unchanged. It imports
their policy implementations instead of silently changing their assumptions.
No live services, network endpoints, subprocess workers or installed packages are
used by the experiment. Python 3.10+ standard library is sufficient.

## Reproduce from the repository root

```sh
python -m unittest discover -s tests -v
(cd milestones/stale-status && python -m unittest discover -s tests -v)
(cd milestones/key-lifetime && python -m unittest discover -s tests -v)
(cd milestones/late-commit && python -m unittest discover -s tests -v)
python milestones/late-commit/run_experiment.py
sha256sum -c milestones/late-commit/PREDICTIONS.sha256
```

Run nested tests in the indicated working directories, as in earlier studies.
The runner writes only this milestone's results directory. Its JSON/CSV are
byte-deterministic; unittest duration text is not.

## Protocol

One initial submission times out at tick 0. Its hidden outcome is either absent
(no future event) or late (a commit event scheduled for tick 2). Status is either
fresh or unsupported. A fresh negative before tick 2 is truthful about present
state, but cannot distinguish an absent original from a pending original.

The factorial corpus has 128 unique cells, one execution per cell: 2 original
outcomes x 2 status capabilities x 2 retention lifetimes (unlimited/1 tick) x
4 recovery delays (0/1/2/3 ticks) x 4 policies. Every grid service supports
idempotency within retention. Calls consume no time; explicit advances process
all due events in timestamp then insertion order, before client actions at the
same tick. Deduplication is checked atomically at commit. There is no pending-key
reservation. Expiry is inclusive: now >= cached_commit_time + lifetime. A cache
hit never extends retention; durable commit history is not erased on expiry.

The three previous policies run unchanged. The wait_terminal control waits until
the known tick-2 original-completion bound, then inspects. Only fresh negative
status after that bound justifies a retry; unsupported status remains unresolved.
This is a deliberately stronger service contract, not something an arbitrary
client can assume from elapsed time. It does not inspect the hidden event queue.

Every run drains pending original events after the policy returns. Evidence
records immediate and settled commits, pending events at return, policy outcome,
return and settlement tick, call counts and a chronological trace. Queue-draining
is evaluator observation, not an extra recovery action or a status API call.
An unresolved policy outcome is not overwritten when hidden state later settles.

## Results

| Policy | Cells | Extra commits | Deferred extra commits | Unresolved | API calls |
|---|---:|---:|---:|---:|---:|
| blind_retry | 32 | 6 | 4 | 0 | 64 |
| inspect_first | 32 | 5 | 4 | 0 | 92 |
| lifetime_guard | 32 | 2 | 2 | 10 | 82 |
| wait_terminal | 32 | 0 | 0 | 16 | 72 |

All [pre-run predictions](PREDICTIONS.md) matched. Predictions and their checksum
were saved before implementing or executing this study. This local sequence is
not independently timestamped preregistration.

The key counterexample is late original + finite retention + immediate retry:
the lifetime guard retries safely with respect to the *current* cache window at
tick 0 and returns committed. The original reaches the commit point at tick 2,
after the retry's key has expired, producing a second durable commit. Both guard
duplicates are deferred until after its decision. Testing only immediate state
would incorrectly report zero duplicates. Unlimited retention suppresses every
extra commit in this corpus.

Waiting for a real completion bound avoids this race in the model, but halves
completion: all 16 unsupported-status cells remain unresolved. Eight of those
have a late commit and eight have no commit. A lack of duplicate writes is not
a guarantee that the requested work completed or that the client knows it did.
The wait control also waits until at least tick 2; call counts alone conceal
that latency tradeoff. Per-cell return/settlement ticks expose it.

[Per-cell CSV](results/per_cell.csv) provides all 128 cell counts and timing
observations. [JSON](results/experiment.json) includes event traces and the same
rows, aggregates and prediction checksum. Twelve new tests cover truthful
negative status, before-commit absence, exact event/status ordering, exact key
expiry, deterministic ties, nonrenewing cache hits, delayed duplicates, queue
draining and independent closed-form per-cell expectations. All 43 prior tests
also passed. This tests simulator behavior, not whether an agent follows a policy.

## Limits

This is a sequential, synthetic, atomic-commit event model, not a live distributed
system or measurement of production failure rates. It excludes pending-key
reservation, payload conflicts, concurrent clients, clock skew, variable retry
latency, status staleness, denials, cancellation, crashes and partial commits.
The event deadline is exact and known; actual systems may supply neither a
bounded execution time nor an authoritative terminal-negative status. A known
retention duration alone is insufficient if an original request can outlive it.
One initial submission and at most one retry per invocation are modeled, not
repeated recovery across invocations or reusing an older operation identifier.

The useful next comparison is admission-time reservation versus commit-time
caching, including reservation expiry while work is still running. No generic
production-safety claim, real-service benchmark or novelty claim is made here.
Original code, documentation and synthetic results use the repository MIT license.
