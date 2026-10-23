"""Read-only attribution audit of saved recovery-composition traces.

New review derivative targeting commit 9dacb69be1f0ef7a79d5cb5f0a8869b1a1224087.
No simulator import, event generation, source mutation, or empirical execution.
This supplements rather than replaces the original dynamics/coverage checker.
Only the four declared deterministic policies and their exact current contracts
are supported. This is separately coded replay, not independent policy design.
Attribution is conditional on an already validated, complete event/action trace.
Use combined_check.py as the normal entry point; this standalone does not reject
every omitted action or fabricated timeline.
"""
import argparse
import gzip
import json
from pathlib import Path

ITEMS = ('A', 'B')
POLICIES = {'naive_inspection', 'blind_keyed', 'capability_fallback', 'horizon_aware'}
CONTRACT_FIELDS = ('scope', 'strategy', 'ttl', 'observation', 'lag',
                   'original_terminal', 'budget', 'deadline', 'horizon')


def choose(policy, contract, now, known, calls, writes, last_write_bound, observations):
    """Choose from public contract and received observations, never hidden fates."""
    if policy not in POLICIES:
        raise ValueError('unregistered policy')
    missing = [item for item in ITEMS if item not in known]
    if not missing:
        return {'kind': 'stop', 'reason': 'positive evidence for all items'}
    if calls >= contract['budget'] or now > contract['deadline']:
        return {'kind': 'stop', 'reason': 'resource limit'}
    if policy == 'naive_inspection':
        if not observations:
            return {'kind': 'read'}
        if writes == 0:
            return {'kind': 'write', 'targets': missing, 'keyed': False,
                    'reason': 'naive missing-as-absent'}
        return {'kind': 'stop', 'reason': 'one inspected replay finished'}
    if policy == 'blind_keyed':
        return {'kind': 'write', 'targets': list(ITEMS),
                'keyed': contract['scope'] != 'none', 'reason': 'blind identical replay'}
    admissible_reservation = (
        contract['scope'] != 'none'
        and contract['strategy'] == 'reserve'
        and all(bound < contract['ttl'] for bound in
                (contract['original_terminal'], now + 4, last_write_bound)))
    if policy == 'capability_fallback' and calls == 0 and admissible_reservation:
        return {'kind': 'write', 'targets': list(ITEMS), 'keyed': True,
                'reason': 'full-horizon atomic reservation'}
    if contract['observation'] == 'unavailable':
        return {'kind': 'stop', 'reason': 'no evidence interface'}
    if observations and observations[-1]['write_count'] == writes:
        latest = observations[-1]
        targets = [item for item in latest['terminal_absent'] if item in missing]
        if targets:
            return {'kind': 'write', 'targets': targets, 'keyed': False,
                    'reason': 'certified terminal absence'}
        if contract['observation'] == 'opaque':
            return {'kind': 'stop', 'reason': 'negative is not terminal evidence'}
    read_start = max(now, max(contract['original_terminal'], last_write_bound)
                     + contract['lag'] - 1)
    if read_start > contract['deadline']:
        return {'kind': 'stop', 'reason': 'terminal snapshot exceeds action deadline'}
    if read_start > now:
        return {'kind': 'wait', 'until': read_start}
    return {'kind': 'read'}


def validate_policy(row):
    """Audit attribution only, assuming a dynamics-validated complete timeline.

Use combined_check.validate_combined() to enforce that prerequisite. This
function intentionally does not replace missing-event/scheduler validation.

The retained trace has no standalone public action timeline. Its event/action
markers supply order, while all received evidence is taken from public_trace.
Hidden effect contents, original fates, retry outcomes, evaluator metrics and
pending queues never enter choose(). Same-tick messages are consumed in order.
"""
    policy = row['policy']
    if policy not in POLICIES:
        raise ValueError('unregistered policy')
    contract = {key: row['case'][key] for key in CONTRACT_FIELDS}
    known, observations = set(), []
    calls = writes = last_write_bound = public_index = decisions = 0
    stopped = False
    for entry in row['hidden_trace']:
        kind = entry['kind']
        is_reply = kind == 'event' and entry['event']['kind'] == 'response'
        is_observation = kind == 'observation'
        if is_reply or is_observation:
            if public_index >= len(row['public_trace']):
                raise ValueError('missing public evidence event')
            event = row['public_trace'][public_index]
            public_index += 1
            expected_kind = 'reply' if is_reply else 'observation'
            if event['kind'] != expected_kind or event['t'] != entry['t']:
                raise ValueError('public evidence order/time mismatch')
            evidence = event[expected_kind]
            known.update(evidence['positive'])
            if is_observation:
                observations.append(evidence)
        elif kind == 'action':
            if stopped:
                raise ValueError('action after policy stop')
            expected = choose(policy, contract, entry['t'], known, calls, writes,
                              last_write_bound, observations)
            if entry['action'] != expected:
                raise ValueError(f"{row['case']['id']} / {policy} at t={entry['t']}: "
                                 f"expected {expected!r}, got {entry['action']!r}")
            decisions += 1
            if expected['kind'] == 'stop':
                stopped = True
            elif expected['kind'] in ('read', 'write'):
                calls += 1
                if expected['kind'] == 'write':
                    writes += 1
                    last_write_bound = entry['t'] + 4
    if not stopped or public_index != len(row['public_trace']):
        raise ValueError('incomplete decision/evidence timeline')
    return {'policy': policy, 'case_id': row['case']['id'], 'decisions_checked': decisions}


def saved_rows(path):
    path = Path(path)
    if path.name.endswith('.jsonl.gz'):
        with gzip.open(path, 'rt') as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    elif path.name.endswith('.jsonl'):
        with path.open() as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)
    else:
        yield json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+', type=Path)
    args = parser.parse_args()
    rows = decisions = 0
    policies = set()
    cases = set()
    groups = set()
    policy_counts = {}
    for path in args.paths:
        for row in saved_rows(path):
            result = validate_policy(row)
            rows += 1
            decisions += result['decisions_checked']
            policies.add(result['policy'])
            cases.add(result['case_id'])
            groups.add((result['case_id'], result['policy']))
            policy_counts[result['policy']] = policy_counts.get(result['policy'], 0) + 1
    if rows == 0:
        raise ValueError('no rows supplied')
    print(json.dumps({'passed': True, 'saved_rows_checked': rows,
                      'decisions_checked': decisions, 'policies': sorted(policies),
                      'distinct_cases': len(cases), 'distinct_case_policy_groups': len(groups),
                      'rows_per_policy': policy_counts,
                      'scope': 'registered-policy action attribution only; not dynamics, coverage, provenance, or behavioral efficacy'},
                     indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
