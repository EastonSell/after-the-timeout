"""Score written field judgments only; never execute proposed next actions."""
import argparse
import json
from pathlib import Path

FIELDS = ('handoff_state', 'publication_evidence', 'issues', 'next_action',
          'approval_granted', 'remote_publication_verified')
STATES = {'invalid', 'blocked', 'ready_for_review'}
PUBLICATION = {'not_recorded', 'recorded_partial', 'recorded_complete'}
ISSUES = {'missing_artifact','hash_mismatch','stale_revision','partial_publication',
          'uncertain_operation','pending_operation','reproduction_not_run'}
ACTIONS = {'review_within_scope','recover_matching_bytes','review_changed_bytes',
           'reconcile_revision','observe_destination','observe_operation','inspect_pending_then_reproduce'}
ROOT = Path(__file__).resolve().parent


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def score(submission, expected):
    if not isinstance(submission, dict) or set(submission) != {'reviews'}:
        raise ValueError('submission must contain only reviews')
    reviews = submission['reviews']
    if not isinstance(reviews, list) or len(reviews) != len(expected):
        raise ValueError('expected exactly eight reviews')
    by_id = {}
    for review in reviews:
        if not isinstance(review, dict) or set(review) != set(FIELDS)|{'case_id','rationale'}:
            raise ValueError('unknown or missing review fields')
        case_id = review['case_id']
        if not isinstance(case_id, str) or case_id not in expected or case_id in by_id:
            raise ValueError('duplicate or unknown case_id')
        if not isinstance(review['rationale'], str) or not review['rationale'].strip():
            raise ValueError('rationale required')
        for field, choices in (('handoff_state',STATES),('publication_evidence',PUBLICATION),('next_action',ACTIONS)):
            if not isinstance(review[field], str) or review[field] not in choices:
                raise ValueError(f'unknown {field}')
        issues = review['issues']
        if not isinstance(issues, list) or any(not isinstance(x,str) or x not in ISSUES for x in issues):
            raise ValueError('invalid issues')
        if len(set(issues)) != len(issues): raise ValueError('duplicate issue code')
        for field in ('approval_granted','remote_publication_verified'):
            if type(review[field]) is not bool: raise ValueError(f'{field} must be JSON boolean')
        by_id[case_id] = review
    if set(by_id) != set(expected): raise ValueError('missing case IDs')
    checks = []
    for case_id, wanted in expected.items():
        actual = by_id[case_id]
        checks.append(dict(case_id=case_id, fields={
            field: sorted(actual[field]) == sorted(wanted[field]) if field == 'issues'
            else actual[field] == wanted[field] for field in FIELDS}))
    return dict(scored_fields=sum(sum(row['fields'].values()) for row in checks),
                possible_fields=len(expected)*len(FIELDS), cases=checks,
                manual_rationale_review='required separately; not scored here',
                interpretation='One written-response review of eight synthetic cases, not efficacy or approval-compliance measurement.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('submission')
    args = parser.parse_args()
    try:
        submitted = json.loads(Path(args.submission).read_text(), object_pairs_hook=unique_object)
        expected = json.loads((ROOT/'expected.json').read_text(), object_pairs_hook=unique_object)
        print(json.dumps(score(submitted, expected), indent=2))
    except (ValueError, OSError) as exc:
        print(json.dumps(dict(submission_valid=False, error=str(exc))))
        raise SystemExit(2)
