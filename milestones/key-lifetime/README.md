# Idempotency is a time-bounded guarantee

This follow-on keeps the [stale-status study](../stale-status/README.md) unchanged
and extends its Python simulator with key expiry. No packages, network calls,
credentials, live writes, or model inference are needed. Python 3.10+ suffices.

## Reproduce from repository root

```sh
python -m unittest discover -s tests -v
(cd milestones/stale-status && python -m unittest discover -s tests -v)
(cd milestones/key-lifetime && python -m unittest discover -s tests -v)
python milestones/key-lifetime/run_experiment.py
sha256sum -c milestones/key-lifetime/PREDICTIONS.sha256
```

Run each suite in the indicated directory: the original studies intentionally
use local module names. Root-level discovery of the nested suite is not the
supported entry point. The new experiment writes only its own results directory.
The JSON and CSV outputs are byte-deterministic across repeated runs on the same
Python implementation; test timing output is not.

## Design and predictions

[PREDICTIONS.md](PREDICTIONS.md) and its checksum were saved before the first test
or experiment execution. This is a local pre-run record, not an independently
timestamped preregistration. The runner rejects a changed prediction checksum.

The full factorial grid contains 216 cells with one run each: four fault modes,
three status modes, two lifetimes, three recovery delays and three policies.
The key is retained forever or for one logical tick. Recovery delays are zero,
one or two ticks, covering before, exactly at and after finite expiry. Status is
fresh, stale-negative once, or unsupported. All grid services support deduplication
while the key remains valid. This is not a randomized trial; no seeds or confidence
intervals are presented, and cell counts are not production failure frequencies.

The retained key expires when now >= commit_time + lifetime. Cache hits do not
refresh expiry. Expiry removes the deduplication guarantee, not the durable record.
Before-commit timeouts do not store a key. Each operation gets its own cache entry.
Status reads and write calls consume no logical time; the explicit recovery delay
is the only elapsed-time treatment. Denial is terminal with no recovery delay.
The two original policies are preserved. The new lifetime_guard checks status,
then permits an uncertain retry only within the guaranteed retention window. Its
bound starts at the first submission in that invocation, never hidden commit state.

## Results

| Policy | Runs | Extra commits | Unresolved | Denied | Calls |
|---|---:|---:|---:|---:|---:|
| blind_retry | 72 | 6 | 0 | 18 | 108 |
| inspect_first | 72 | 4 | 0 | 18 | 138 |
| lifetime_guard | 72 | 0 | 10 | 18 | 128 |

All pre-run predictions matched. The four inspect-first duplicate cases are
post-commit timeouts with stale/unsupported status and delay 1/2 after a finite
key lifetime. Fresh positive status resolves even after expiry. The guard instead
leaves those four cases plus six before-commit cases unresolved. Those six cases
contain no commit, so retry would actually succeed, but that fact is unavailable
to the policy. Avoiding duplicates is therefore not equivalent to completing work.
All policies have 18 one-call denials; unlimited retention produces no duplicates.

[Per-cell CSV](results/per_cell.csv) contains every input and count; [JSON](results/experiment.json)
contains the same rows, aggregates and prediction hash. Tests use a separate
closed-form per-cell oracle, exact-expiry checks, operation isolation, no cache
renewal, durable-record retention and unlimited-lifetime equivalence with the
published simulator. Verification: 11 new tests, 10 original tests and 22 tests
in the previous study passed. Tests validate code, not agent behavior.

## Boundaries and next experiment

This model assumes atomic commits and correct deduplication within an advertised,
known retention window, a single sequential client, no time passing during calls,
no clock skew and no payload conflict. It models one initial submission and at
most one retry per execute invocation, not recovery across process restarts or
reuse of an old operation ID. It does not model cache eviction before the stated
lifetime, concurrent requests, late in-flight commits, status failure, latency,
cost, partial writes or human/model adherence to instructions. A live system
needs a service-specific retention contract, persisted first-attempt evidence,
clock/latency margins and reconciliation after that guarantee ends.

The meaningful next control is a known positive status arriving late versus an
expired key with an in-flight original commit. No production safety, real-world
failure probability, or research novelty is claimed here.

Original additive code, documentation and synthetic results follow the repository
MIT license. The only imported source is the existing public stale-status model.
