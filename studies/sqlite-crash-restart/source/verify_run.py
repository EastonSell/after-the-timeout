"""Recount every planned row from retained raw evidence, including failures."""
import argparse
import json
from pathlib import Path
from assess import assess, read_evidence, summarize, cell_summaries
from guard import check_admission, sha256


def verify(root):
    root = Path(root).resolve()
    check_admission(root / 'source', root / 'admission.json')
    plan = json.loads((root / 'source/protocol.json').read_text())['matrix']
    errors, rows = [], []
    if json.loads((root / 'planned.json').read_text()) != plan:
        errors.append('planned cases differ from admitted matrix')
    for case in plan:
        folder = root / case['id']
        try:
            recorded = json.loads((folder / 'result.json').read_text())
            if json.loads((folder / 'case.json').read_text()) != case:
                raise ValueError('case differs from frozen plan')
            if recorded['classification'] in ('invalid', 'not_run'):
                row = recorded
            else:
                row = dict(id=case['id'], **assess(case, read_evidence(folder)))
                if row['classification'] != recorded['classification']:
                    errors.append(f"{case['id']}: recorded/recomputed classification mismatch")
            rows.append(row)
        except Exception as exc:
            rows.append({'id': case['id'], 'classification': 'invalid', 'reason': f'{type(exc).__name__}: {exc}'})
            errors.append(f"{case['id']}: missing or malformed retained evidence")
    summary = summarize(plan, rows)
    summary['cells'] = cell_summaries(plan, rows)
    recorded_summary = json.loads((root / 'summary.json').read_text())
    for key, value in summary.items():
        if recorded_summary.get(key) != value:
            errors.append(f'summary mismatch: {key}')
    manifest = json.loads((root / 'OUTPUT_SHA256.json').read_text())
    actual_names = {str(p.relative_to(root)) for p in root.rglob('*') if p.is_file()} - {'OUTPUT_SHA256.json'}
    if set(manifest) != actual_names:
        errors.append('output manifest does not cover exact file set')
    for name, expected in manifest.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root) or sha256(path) != expected:
            errors.append(f'output hash mismatch: {name}')
    return {'summary': summary, 'audit_errors': errors, 'rows': rows,
            'complete_all_pass': not errors and summary['valid_pass'] == 24}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    result = verify(args.run)
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['complete_all_pass'] else 1)
