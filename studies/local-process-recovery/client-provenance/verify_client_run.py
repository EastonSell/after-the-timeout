"""Add client-observation provenance to the frozen whole-matrix verifier.

This post-hoc supplement reads the same retained evidence. It does not modify the
producer, original verifier, protocol, measurement, or historical manifests, and
cannot authenticate coordinated fabrication of logs and their accompanying data.
"""
import argparse
import json
from pathlib import Path
import sys
import sqlite3

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE / 'postrun'))
from verify_run import verify_run

HELD_COMMIT = {'live_negative', 'same_key', 'terminal_fence', 'concurrent_recoverers'}
EVIDENCE_ERRORS = (OSError, KeyError, TypeError, ValueError, AttributeError, IndexError, StopIteration, sqlite3.Error)


def read(path):
    return json.loads(path.read_text())


def require(condition, issue):
    if not condition:
        raise ValueError(issue)


def one(trace, event, **fields):
    matches = [row for row in trace if row['event'] == event
               and all(row.get(key) == value for key, value in fields.items())]
    require(len(matches) == 1, f'expected one {event} {fields}, found {len(matches)}')
    return matches[0]


def trace(root, role):
    rows = [json.loads(line) for line in (root / f'{role}.jsonl').read_text().splitlines()]
    require(bool(rows), role + ': empty trace')
    require(all(row['role'] == role for row in rows), role + ': trace role mismatch')
    require(all(type(row[key]) is int and row[key] > 0 for row in rows
                for key in ('pid', 'mono_ns', 'utc_ns', 'thread')), role + ': invalid event identity/timestamp')
    require(len({row['pid'] for row in rows}) == 1, role + ': process identity changed')
    require(all(left['mono_ns'] < right['mono_ns'] for left, right in zip(rows, rows[1:])),
            role + ': nonmonotonic trace')
    return rows


def require_rpc(row, method, path, **fields):
    require(row['method'] == method and row['path'] == path
            and all(row.get(key) == value for key, value in fields.items()),
            f'{row["role"]}: {row["event"]} does not match {method} {path} {fields}')


def committed_reply(actor, attempts):
    attempt = attempts[actor]
    require(attempt['state'] == 'committed', actor + ': write not committed in database')
    return dict(status='response', http_status=200,
                body=dict(op=actor, state='committed', effect_id=attempt['effect_id']))


def verify_clients(root, scenario, timeout):
    """Call only after verify_run validates the saved result against stopped SQL."""
    roles = ['service', 'driver', 'original']
    if scenario == 'concurrent_recoverers':
        roles += ['recovery1', 'recovery2']
    traces = {role: trace(root, role) for role in roles}
    pids = {role: rows[0]['pid'] for role, rows in traces.items()}
    require(len(set(pids.values())) == len(pids), 'process identities are not distinct')
    service, driver, original = (traces[role] for role in ('service', 'driver', 'original'))
    ready = one(service, 'server_ready')
    require(ready['address'] == '127.0.0.1' and type(ready['port']) is int
            and 0 < ready['port'] < 65536, 'service address/port mismatch')
    require(read(root / 'ready.json') == dict(host='127.0.0.1', port=ready['port'], pid=pids['service']),
            'ready receipt differs from service identity')
    spawned = one(driver, 'service_spawned')
    require(spawned['server_pid'] == pids['service'], 'service spawn identity mismatch')
    database = read(root / 'result.json')['database']
    attempts = {row['op']: row for row in database['attempts']}

    for actor in roles[2:]:
        client = traces[actor]
        spawned = one(driver, 'client_spawned', actor=actor)
        # Popen can schedule the child before the parent records its spawn receipt.
        require(spawned['client_pid'] == pids[actor], actor + ': client spawn identity mismatch')

    outcome_event = 'response_received' if scenario == 'no_fault' else 'request_timeout'
    require([row['event'] for row in original] == ['request_start', outcome_event, 'client_finished'],
            'original: incomplete or conflicting request lifecycle')
    start, outcome, finished = original
    data = dict(op='original', hold_commit=scenario in HELD_COMMIT,
                hold_reply=scenario != 'no_fault' and scenario not in HELD_COMMIT)
    if scenario == 'same_key':
        data['key'] = 'intent-A'
    require_rpc(start, 'POST', '/write', timeout_s=timeout, data=data)
    admitted = one(service, 'admitted', op='original')
    require(start['mono_ns'] < admitted['mono_ns'] < outcome['mono_ns'],
            'original: request/admission/outcome order mismatch')
    if scenario == 'no_fault':
        expected = committed_reply('original', attempts)
    else:
        expected = dict(status='timeout', exception='TimeoutError')
    require_rpc(outcome, 'POST', '/write', **expected)
    saved = dict(pid=pids['original'], **expected)
    require(read(root / 'original-result.json') == saved, 'original: saved outcome differs from trace')
    observed = one(driver, 'original_outcome_observed')
    require(observed['outcome'] == saved and finished['mono_ns'] < observed['mono_ns'],
            'original: driver observation identity/order mismatch')

    if scenario == 'concurrent_recoverers':
        barrier = one(driver, 'recoverer_barrier_release')
        require(observed['mono_ns'] < barrier['mono_ns'], 'barrier precedes original outcome observation')
        for actor in ('recovery1', 'recovery2'):
            client = traces[actor]
            require([row['event'] for row in client] == [
                'request_start', 'response_received', 'policy_decision',
                'request_start', 'response_received', 'client_finished'],
                actor + ': incomplete or conflicting recovery lifecycle')
            start, response, decision, write, reply, finished = client
            require_rpc(start, 'GET', '/read', timeout_s=3, data=None)
            expected = dict(status='response', http_status=200, body=dict(
                op='original', operation_state='cancelled', terminal=True, effect_count=0))
            require_rpc(response, 'GET', '/read', **expected)
            require(read(root / f'{actor}-observed.json') == expected,
                    actor + ': saved observation differs from read reply')
            require(decision['action'] == 'unkeyed_retry_after_current_zero' and decision['evidence'] == expected,
                    actor + ': decision does not use observed terminal zero')
            require(response['mono_ns'] < barrier['mono_ns'] < decision['mono_ns'],
                    actor + ': decision does not follow read/barrier')
            require_rpc(write, 'POST', '/write', timeout_s=3, data=dict(op=actor))
            admitted = one(service, 'admitted', op=actor)
            require(write['mono_ns'] < admitted['mono_ns'] < reply['mono_ns']
                    and admitted['key'] is None, actor + ': write admission/order/key mismatch')
            expected = committed_reply(actor, attempts)
            require_rpc(reply, 'POST', '/write', **expected)
            require(read(root / f'{actor}-result.json') == dict(pid=pids[actor], **expected),
                    actor + ': saved result differs from committed reply')
    return dict(client_count=len(roles) - 2, process_count=len(roles))


def verify_client_run(run, source_root=None):
    run = Path(run)
    try:
        report = verify_run(run, source_root)
    except EVIDENCE_ERRORS as exc:
        report = dict(passed=False, planned_trials=120, audited_trials=0, rows=[],
                      violations=[f'invalid_base_evidence: {type(exc).__name__}: {exc}'])
    report['client_provenance_trials'] = 0
    report['client_provenance_clients'] = 0
    # Do not promote results from incomplete, source-mismatched, or invalid SQL evidence.
    if not report['passed']:
        return report
    for row in report['rows']:
        root = run / row['trial']
        try:
            case = read(root / 'case.json')
            evidence = verify_clients(root, case['scenario'], case['socket_timeout_s'])
            row['client_provenance'] = evidence
            report['client_provenance_trials'] += 1
            report['client_provenance_clients'] += evidence['client_count']
        except EVIDENCE_ERRORS as exc:
            issue = f'{row["trial"]}: invalid_client_evidence: {type(exc).__name__}: {exc}'
            row['violations'].append(issue)
            report['violations'].append(issue)
    report['passed'] = not report['violations'] and report['client_provenance_trials'] == 120
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--source-root', type=Path, default=BASE)
    args = parser.parse_args()
    report = verify_client_run(args.run, args.source_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
