"""Validate saved-row dynamics FIRST, then registered-policy action attribution.

Read-only combined entry point. Imports the byte-verified published checker,
not the simulator. This validates each supplied row; it does NOT establish
cross-row scheduler coverage, exact case-manifest membership, or completeness
of a supplied dataset. Use the original saved-group checker for those checks.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

from policy_replay import saved_rows, validate_policy

ROOT = Path(__file__).resolve().parents[1]
CHECKER = ROOT / 'source/checker.py'
CHECKER_SHA256 = '9751e07387d849ca8b99592ff7b655235d8596a226a06bd92a38095a7e5b8665'


def load_original_checker():
    if hashlib.sha256(CHECKER.read_bytes()).hexdigest() != CHECKER_SHA256:
        raise ValueError('original dynamics checker does not match pinned source bytes')
    spec = importlib.util.spec_from_file_location('pinned_original_dynamics_checker', CHECKER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_DYNAMICS = load_original_checker()


def validate_combined(row):
    # Order is intentional: attribution assumes the action/event timeline is
    # already complete and semantically valid. Never weaken this prerequisite.
    _DYNAMICS.validate(row)
    result = validate_policy(row)
    return dict(result, dynamics_validated=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    rows = decisions = 0
    cases, groups = set(), set()
    policy_counts = {}
    for path in args.paths:
        for row in saved_rows(path):
            result = validate_combined(row)
            rows += 1
            decisions += result['decisions_checked']
            cases.add(result['case_id'])
            groups.add((result['case_id'], result['policy']))
            policy_counts[result['policy']] = policy_counts.get(result['policy'], 0) + 1
    if rows == 0:
        raise ValueError('no rows supplied')
    print(json.dumps({
        'passed': True, 'saved_rows_checked': rows,
        'decisions_checked': decisions, 'distinct_cases': len(cases),
        'distinct_case_policy_groups': len(groups), 'rows_per_policy': policy_counts,
        'original_checker_sha256': CHECKER_SHA256,
        'validation_order': ['original_per_row_dynamics', 'registered_policy_attribution'],
        'scope': 'per-row dynamics/evidence/metrics and policy attribution; not cross-row scheduler coverage, case-manifest membership, dataset completeness, or behavioral efficacy',
    }, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
