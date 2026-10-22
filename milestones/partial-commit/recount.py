"""Post-hoc verification only: recount saved rows without executing the simulator."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ITEMS = {'a', 'b', 'c'}


def recount(root=ROOT):
    result = json.loads((root / 'results/experiment.json').read_text())
    raw = [json.loads(line) for line in (root / 'results/rows.jsonl').read_text().splitlines()]
    assert result['rows'] == raw
    cases = json.loads((root / 'allowed_cases.json').read_text())
    observed = [{key: row[key] for key in cases[0]} for row in raw]
    assert observed == cases and len(raw) == 256
    for row in raw:
        prior = set(row['initial_committed'])
        mode, policy, keyed = row['status_mode'], row['policy'], row['per_item_idempotency']
        visible = ITEMS if mode == 'fresh' else ({'a'} if mode == 'incomplete' else set())
        if policy == 'blind_batch':
            retry, unknown = ITEMS, set()
        elif policy == 'missing_is_absent' or (policy == 'capability_guard' and keyed):
            retry, unknown = ITEMS - (visible & prior), set()
        else:
            retry, unknown = visible - prior, ITEMS - visible
        counts = {item: int(item in prior) + int(item in retry and (not keyed or item not in prior)) for item in sorted(ITEMS)}
        checks = {
            'retry_items': sorted(retry), 'unresolved_items': sorted(unknown),
            'commit_counts': counts, 'unresolved_count': len(unknown),
            'reported_complete': not unknown,
            'true_complete': min(counts.values()) >= 1,
            'exact_once_complete': set(counts.values()) == {1},
            'extra_side_effects': sum(max(0, n - 1) for n in counts.values()),
            'duplicate_items': [item for item, n in counts.items() if n > 1],
            'api_calls': 1 + (policy != 'blind_batch') + bool(retry),
        }
        for key, expected in checks.items():
            assert row[key] == expected, (key, row, expected)
    for summary in result['summary']:
        group = [row for row in raw if row['policy'] == summary['policy'] and row['per_item_idempotency'] == summary['per_item_idempotency']]
        assert summary['cells'] == len(group) == 32
        for metric in ('true_complete', 'exact_once_complete', 'reported_complete', 'extra_side_effects', 'unresolved_count', 'api_calls'):
            assert summary[metric] == sum(row[metric] for row in group)
        assert summary['cells_with_duplicates'] == sum(any(n > 1 for n in row['commit_counts'].values()) for row in group)
        assert summary['cells_unresolved'] == sum(bool(row['unresolved_items']) for row in group)
    return {'label': 'post-hoc independent recount, not a pre-run prediction', 'cases_verified': len(raw),
            'raw_equals_final_rows': True, 'closed_form_metrics_match': True,
            'coverage_equals_allowed_cases': True,
            'artifact_sha256': {name: hashlib.sha256((root / 'results' / name).read_bytes()).hexdigest()
                                for name in ('experiment.json', 'rows.jsonl', 'status.json')}}


if __name__ == '__main__':
    print(json.dumps(recount(), indent=2, sort_keys=True))
