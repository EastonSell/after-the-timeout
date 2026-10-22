"""Record decisions before settling and durable state after all events finish."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
from late_commit import POLICIES, Service, execute

ROOT = Path(__file__).resolve().parent
INPUTS = ('original_outcome', 'status_supported', 'key_lifetime', 'delay', 'policy')
COUNTS = ('runs', 'duplicates', 'deferred_duplicates', 'unresolved', 'calls')


def collect():
    rows = []
    for outcome, status, lifetime, delay, policy in itertools.product(
            ('absent', 'late'), (True, False), (None, 1), (0, 1, 2, 3), POLICIES):
        service = Service(original_outcome=outcome, status_supported=status,
                          key_lifetime=lifetime, idempotent=True)
        decision = execute(service, policy, delay)
        immediate_commits, returned_at = len(service.records), service.now
        pending_at_return = len(service.events)
        service.drain()
        rows.append(dict(zip(INPUTS, (outcome, status, lifetime, delay, policy))) | dict(
            runs=1, decision=decision, returned_at=returned_at,
            pending_at_return=pending_at_return, immediate_commits=immediate_commits,
            settled_at=service.now, settled_commits=len(service.records),
            duplicates=max(0, len(service.records)-1),
            deferred_duplicates=max(0, len(service.records)-1)-max(0, immediate_commits-1),
            unresolved=int(decision == 'needs_reconciliation'),
            calls=service.calls, trace=service.trace))
    return rows


def summarize(rows):
    return {p: {k: sum(r[k] for r in rows if r['policy'] == p) for k in COUNTS}
            for p in POLICIES}


def run():
    digest = hashlib.sha256((ROOT/'PREDICTIONS.md').read_bytes()).hexdigest()
    if digest != (ROOT/'PREDICTIONS.sha256').read_text().split()[0]:
        raise ValueError('Prediction checksum mismatch')
    rows = collect()
    result = dict(measurement_type='deterministic offline event simulation',
                  prediction_sha256=digest, unique_cells=len(rows),
                  summary=summarize(rows), rows=rows)
    out = ROOT/'results'
    out.mkdir(exist_ok=True)
    (out/'experiment.json').write_text(json.dumps(result, indent=2)+'\n')
    fields = [k for k in rows[0] if k != 'trace']
    with (out/'per_cell.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader(); writer.writerows(rows)
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    run()
