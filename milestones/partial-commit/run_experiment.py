"""Verify the frozen inputs, then emit deterministic per-case and summary JSON."""
import argparse
import hashlib
import os
import itertools
import json
from pathlib import Path
from partial_commit import ITEMS, MODES, POLICIES, execute

ROOT = Path(__file__).resolve().parent


def verify_freeze(root=ROOT):
    manifest = root / 'FREEZE.sha256'
    for line in manifest.read_text().splitlines():
        digest, relative = line.split('  ', 1)
        if hashlib.sha256((root / relative).read_bytes()).hexdigest() != digest:
            raise ValueError('Frozen input changed: ' + relative)
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def expected_cases():
    return [
        {'initial_committed': [item for index, item in enumerate(ITEMS) if mask & (1 << index)],
         'status_mode': mode, 'per_item_idempotency': keyed, 'policy': policy}
        for mask, mode, keyed, policy in itertools.product(range(8), MODES, (False, True), POLICIES)
    ]


def atomic_json(path, value):
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('x') as handle:
        handle.write(json.dumps(value, indent=2, sort_keys=True) + '\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(root=ROOT, out=None):
    freeze_hash = verify_freeze(root)
    cases = json.loads((root / 'allowed_cases.json').read_text())
    if cases != expected_cases():
        raise ValueError('Case list differs from declared complete factorial ordering')
    destination = Path(out) if out is not None else root / 'results'
    destination.mkdir(exist_ok=False)  # Reserve before any outcome execution.
    atomic_json(destination / 'status.json', {'state': 'running', 'freeze_sha256': freeze_hash})
    rows = []
    with (destination / 'rows.jsonl').open('x') as raw:
        for case in cases:
            row = execute(case['initial_committed'], case['status_mode'],
                          case['per_item_idempotency'], case['policy'])
            raw.write(json.dumps(row, sort_keys=True) + '\n')
            raw.flush()
            os.fsync(raw.fileno())
            rows.append(row)
    summaries = []
    for policy, keyed in itertools.product(POLICIES, (False, True)):
        group = [row for row in rows if row['policy'] == policy and row['per_item_idempotency'] == keyed]
        summaries.append({
            'policy': policy, 'per_item_idempotency': keyed, 'cells': len(group),
            **{metric: sum(row[metric] for row in group) for metric in (
                'true_complete', 'exact_once_complete', 'reported_complete',
                'extra_side_effects', 'unresolved_count', 'api_calls')},
            'cells_with_duplicates': sum(bool(row['duplicate_items']) for row in group),
            'cells_unresolved': sum(bool(row['unresolved_items']) for row in group),
        })
    predictions = {
        'retry_baselines_complete': all(row['reported_complete'] for row in rows if row['policy'] in POLICIES[:2]),
        'evidence_policies_no_duplicates': all(row['extra_side_effects'] == 0 for row in rows if row['policy'] in POLICIES[2:]),
        'keyed_guard_complete': all(row['reported_complete'] and row['exact_once_complete'] for row in rows if row['policy'] == 'capability_guard' and row['per_item_idempotency']),
        'fresh_evidence_exact_once': all(row['exact_once_complete'] for row in rows if row['policy'] in POLICIES[2:] and row['status_mode'] == 'fresh'),
        'reported_complete_is_true': all(not row['reported_complete'] or row['true_complete'] for row in rows),
    }
    output = {'schema_version': 1, 'freeze_sha256': freeze_hash,
              'cells': len(rows), 'predictions': predictions, 'summary': summaries, 'rows': rows}
    atomic_json(destination / 'experiment.json', output)
    passed = all(predictions.values())
    atomic_json(destination / 'status.json', {'state': 'complete' if passed else 'prediction_failed',
                                            'freeze_sha256': freeze_hash, 'retained_rows': len(rows)})
    if not passed:
        raise AssertionError('Predictions falsified; retained evidence in ' + str(destination))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='New output directory; parent must already exist')
    args = parser.parse_args()
    result = run(out=args.out)
    print(json.dumps({'cells': result['cells'], 'summary': result['summary']}, indent=2))
