"""Read retained evidence without importing service or experiment implementation."""
import argparse
import json
import sqlite3
from pathlib import Path

EXPECTED = {'no_fault': 1, 'live_negative': 2, 'stale_negative': 2, 'same_key': 1,
            'terminal_fence': 1, 'terminal_with_stale_read': 2,
            'terminal_with_authoritative_read': 1, 'concurrent_recoverers': 2}
LATE = {'live_negative', 'same_key', 'terminal_fence', 'concurrent_recoverers'}
STALE = {'stale_negative', 'terminal_with_stale_read'}


def jsonl(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def verify_trial(root, scenario):
    root = Path(root)
    service = jsonl(root / 'service.jsonl')
    original = jsonl(root / 'original.jsonl')
    driver = jsonl(root / 'driver.jsonl')
    with sqlite3.connect(f'file:{root / "effects.sqlite3"}?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        effects = [dict(r) for r in db.execute('SELECT * FROM effects ORDER BY id')]
        attempts = [dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY op')]
        keys = [dict(r) for r in db.execute('SELECT * FROM keys ORDER BY key')]
        integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
    issues = []
    def check(value, issue):
        if not value:
            issues.append(issue)
    def events(name, op=None):
        return [r for r in service if r['event'] == name and (op is None or r.get('op') == op)]
    timeout = [r for r in original if r['event'] == 'request_timeout']
    admitted = events('admitted', 'original')
    stopped = events('server_stopped')
    finished = events('handler_finished')
    original_state = next(r['state'] for r in attempts if r['op'] == 'original')
    check(integrity == 'ok', 'database_integrity')
    check(len(effects) == EXPECTED[scenario], 'wrong_effect_count')
    check(all(r['state'] != 'pending' for r in attempts), 'pending_attempt')
    check({r['op'] for r in finished} == {r['op'] for r in attempts}, 'undrained_handlers')
    check(len(stopped) == 1, 'service_not_stopped')
    check(not events('handler_error'), 'handler_error')
    check(service[0]['pid'] != original[0]['pid'], 'no_process_isolation')
    check(service[0]['pid'] != driver[0]['pid'], 'no_driver_process_isolation')
    check(len(admitted) == 1, 'original_admission_missing')
    if scenario == 'no_fault':
        replies = [r for r in original if r['event'] == 'response_received']
        check(not timeout and len(replies) == 1 and replies[0]['http_status'] == 200, 'normal_response_missing')
    else:
        check(len(timeout) == 1, 'timeout_not_observed')
        if timeout and admitted:
            check(admitted[0]['mono_ns'] < timeout[0]['mono_ns'], 'timeout_before_admission')
    if scenario in LATE and timeout:
        outcomes = [r for r in service if r.get('op') == 'original' and r['event'] in ('effect_committed', 'deduplicated', 'suppressed')]
        check(len(outcomes) == 1 and timeout[0]['mono_ns'] < outcomes[0]['mono_ns'], 'late_schedule_not_exercised')
    if scenario == 'live_negative':
        check(any(r['operation_state'] == 'pending' and not r['terminal'] and r['effect_count'] == 0
                  for r in events('authoritative_read', 'original')), 'live_negative_missing')
    if scenario in ('stale_negative', 'terminal_with_stale_read', 'terminal_with_authoritative_read'):
        commit = events('effect_committed', 'original')
        check(len(commit) == 1 and timeout and commit[0]['mono_ns'] < timeout[0]['mono_ns'], 'pre_timeout_commit_missing')
    if scenario in STALE:
        cache = events('cached_read')
        commit = events('effect_committed', 'original')
        check(len(cache) == 1 and cache[0]['effect_count'] == 0, 'stale_negative_missing')
        check(len(commit) == 1 and cache and cache[0]['snapshot_mono_ns'] < commit[0]['mono_ns'] < cache[0]['mono_ns'], 'stale_schedule_not_exercised')
    if scenario in ('terminal_fence', 'concurrent_recoverers'):
        fences = events('fence', 'original')
        check(original_state == 'cancelled' and not events('effect_committed', 'original'), 'fenced_original_committed')
        check(len(fences) == 1 and fences[0]['terminal'] and fences[0]['effect_count'] == 0, 'valid_fence_missing')
    if scenario == 'same_key':
        check(len(keys) == 1 and len(events('deduplicated', 'original')) == 1, 'idempotent_control_not_exercised')
    if scenario.startswith('terminal_with_'):
        reads = events('authoritative_read', 'original')
        check(any(r['terminal'] and r['operation_state'] == 'committed' and r['effect_count'] == 1 for r in reads), 'committed_certificate_missing')
    if scenario == 'concurrent_recoverers':
        read_times = []
        for actor in ('recovery1', 'recovery2'):
            observed = json.loads((root / f'{actor}-observed.json').read_text())
            check(observed['body']['terminal'] and observed['body']['effect_count'] == 0, f'{actor}_zero_missing')
            read_times.append(next(r['mono_ns'] for r in jsonl(root / f'{actor}.jsonl') if r['event'] == 'response_received' and r['path'] == '/read'))
        writes = [r['mono_ns'] for r in service if r['event'] == 'admitted' and r['op'] in ('recovery1', 'recovery2')]
        check(len(writes) == 2 and max(read_times) < min(writes), 'recoverer_race_not_exercised')
    return dict(effect_count=len(effects), violations=issues, all_handlers_finished=not any(x in issues for x in ('pending_attempt', 'undrained_handlers', 'service_not_stopped')),
                server_pid=service[0]['pid'], original_client_pid=original[0]['pid'], driver_pid=driver[0]['pid'],
                database=dict(effects=effects, attempts=attempts, keys=keys, integrity=integrity),
                event_count=len(service) + len(original) + len(driver))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('run', type=Path)
    args = parser.parse_args()
    rows = []
    for root in sorted(args.run.glob('trial-*')):
        case = json.loads((root / 'case.json').read_text())
        try:
            result = verify_trial(root, case['scenario'])
            rows.append(dict(trial=root.name, **result))
        except Exception as exc:
            rows.append(dict(trial=root.name, violations=[f'{type(exc).__name__}: {exc}']))
    report = dict(trials=len(rows), passed=sum(not r['violations'] for r in rows), rows=rows)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if rows and all(not r['violations'] for r in rows) else 1)


if __name__ == '__main__':
    main()
