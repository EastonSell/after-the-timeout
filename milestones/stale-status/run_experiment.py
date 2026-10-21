"""Deterministic paired corpus; random seeds only shuffle scenario order."""
import csv
import hashlib
import json
import platform
import random
from datetime import datetime, timezone
from pathlib import Path
from workflow import Service, execute

ROOT = Path(__file__).resolve().parent
POLICIES = ('blind_retry', 'inspect_first')


def aggregate(rows):
    return dict(runs=len(rows), duplicates=sum(r['duplicate_commits'] for r in rows),
                unresolved=sum(r['outcome'] == 'needs_reconciliation' for r in rows),
                calls=sum(r['calls'] for r in rows))


def collect(cfg):
    rows = []
    for staleness in cfg['status_staleness']:
        for seed in cfg['seeds']:
            scenarios = [(f, s, i) for f in cfg['faults'] for s in (True, False) for i in (True, False)]
            random.Random(seed).shuffle(scenarios)
            for fault, status, idem in scenarios:
                for policy in POLICIES:
                    service = Service(fault, status, idem, status_staleness=staleness)
                    outcome = execute(service, policy)
                    rows.append(dict(status_staleness=staleness, seed=seed, fault=fault,
                                     status_supported=status, idempotent=idem, policy=policy,
                                     outcome=outcome, calls=service.calls, commits=len(service.records),
                                     duplicate_commits=max(0, len(service.records)-1)))
    return rows


def summarize(rows):
    summary = {str(n): {p: aggregate([r for r in rows if r['status_staleness'] == n and r['policy'] == p])
                       for p in POLICIES} for n in (0, 1)}
    cells = []
    for n in (0, 1):
        for fault in ('none', 'before', 'after', 'denied'):
            for status in (True, False):
                for idem in (True, False):
                    for policy in POLICIES:
                        key = dict(status_staleness=n, fault=fault, status_supported=status, idempotent=idem, policy=policy)
                        cell = [r for r in rows if all(r[k] == v for k, v in key.items())]
                        cells.append({**key, **aggregate(cell)})
    return summary, cells


def run():
    prediction_hash = hashlib.sha256((ROOT/'PREDICTIONS.md').read_bytes()).hexdigest()
    assert prediction_hash == (ROOT/'PREDICTIONS.sha256').read_text().split()[0], 'Prediction changed'
    started = datetime.now(timezone.utc).isoformat()
    cfg = json.loads((ROOT/'config.json').read_text())
    rows = collect(cfg)
    summary, cells = summarize(rows)
    result = dict(measurement_type='deterministic offline fault simulation', started_at=started,
                  prediction_sha256=prediction_hash, python=platform.python_version(), config=cfg,
                  summary=summary, per_cell=cells, rows=rows)
    out = ROOT/'results'
    out.mkdir(exist_ok=True)
    (out/'experiment.json').write_text(json.dumps(result, indent=2)+'\n')
    for filename, values in [('rows.csv', rows), ('per_cell.csv', cells)]:
        with (out/filename).open('w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(values[0]))
            writer.writeheader()
            writer.writerows(values)
    print(json.dumps(summary, indent=2))

if __name__ == '__main__':
    run()
