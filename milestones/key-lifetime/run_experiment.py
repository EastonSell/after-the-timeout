"""One run per constructed cell, no stochastic or production claims."""
import csv
import hashlib
import itertools
import json
from pathlib import Path
from key_lifetime import POLICIES, Service, execute

ROOT = Path(__file__).resolve().parent
FIELDS = ('fault', 'status_mode', 'key_lifetime', 'delay', 'policy')


def collect():
    rows = []
    for fault, mode, lifetime, delay, policy in itertools.product(
            ('none', 'before', 'after', 'denied'),
            ('fresh', 'stale', 'unsupported'), (None, 1), (0, 1, 2), POLICIES):
        service = Service(fault=fault, status_supported=mode != 'unsupported',
                          idempotent=True, status_staleness=int(mode == 'stale'),
                          key_lifetime=lifetime)
        outcome = execute(service, policy, delay)
        rows.append(dict(zip(FIELDS, (fault, mode, lifetime, delay, policy))) | dict(
            runs=1, outcome=outcome, commits=len(service.records),
            duplicates=max(0, len(service.records)-1),
            unresolved=int(outcome == 'needs_reconciliation'),
            denied=int(outcome == 'denied'), calls=service.calls))
    return rows


def summarize(rows):
    return {policy: {key: sum(row[key] for row in rows if row['policy'] == policy)
                     for key in ('runs', 'duplicates', 'unresolved', 'denied', 'calls')}
            for policy in POLICIES}


def run():
    digest = hashlib.sha256((ROOT / 'PREDICTIONS.md').read_bytes()).hexdigest()
    expected = (ROOT / 'PREDICTIONS.sha256').read_text().split()[0]
    if digest != expected:
        raise ValueError('Prediction checksum mismatch')
    rows = collect()
    out = ROOT / 'results'
    out.mkdir(exist_ok=True)
    result = dict(measurement_type='deterministic offline simulation',
                  prediction_sha256=digest, unique_cells=len(rows),
                  runs_per_cell=1, summary=summarize(rows), rows=rows)
    (out / 'experiment.json').write_text(json.dumps(result, indent=2)+'\n')
    with (out / 'per_cell.csv').open('w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(result['summary'], indent=2))


if __name__ == '__main__':
    run()
