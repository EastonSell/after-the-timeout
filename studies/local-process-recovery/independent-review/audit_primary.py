"""Independent evidence audit: does not import service/client/experiment/verify.

Only reads the frozen experiment and retained primary evidence. The parent
invocation redirects this script's JSON output into the review directory.
"""
import collections
import hashlib
import json
import sqlite3
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
RUN = BASE / 'evidence' / 'primary-run'
SCENARIOS = ['no_fault', 'live_negative', 'stale_negative', 'same_key',
             'terminal_fence', 'terminal_with_stale_read',
             'terminal_with_authoritative_read', 'concurrent_recoverers']
EXPECTED = dict(zip(SCENARIOS, [1, 2, 2, 1, 1, 2, 1, 2]))
LATE = {'live_negative', 'same_key', 'terminal_fence', 'concurrent_recoverers'}
issues = []
rows = []

def check(value, description):
    if not value:
        issues.append(description)

def read(path):
    return json.loads(path.read_text())

def lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]

def select(trace, event, **fields):
    return [r for r in trace if r['event'] == event and all(r.get(k) == v for k, v in fields.items())]

def one(trace, event, **fields):
    result = select(trace, event, **fields)
    assert len(result) == 1, (event, fields, len(result))
    return result[0]

manifest = read(RUN / 'frozen-input.json')
summary = read(RUN / 'summary.json')
index = lines(RUN / 'trials.jsonl')
expected_cells = [(timeout, repeat, scenario) for timeout in (0.08, 0.12, 0.20)
                  for repeat in range(5) for scenario in SCENARIOS]
actual_cells = [(r['socket_timeout_s'], r['repetition'], r['scenario']) for r in index]
check(actual_cells == expected_cells, 'planned matrix differs from complete ordered trial index')
check(len(index) == 120, 'index is not 120 trials')
check(len(set(r['trial'] for r in index)) == 120, 'trial names are not 120 unique values')
directories = {p.name for p in RUN.glob('trial-*') if p.is_dir()}
check(directories == {r['trial'] for r in index}, 'directories differ from indexed trials')
check(manifest['plan'] == {'planned_trials': 120, 'repetitions': 5,
      'scenarios': SCENARIOS, 'timeouts': [0.08, 0.12, 0.20]}, 'frozen plan mismatch')
hash_results = {name: hashlib.sha256((BASE / name).read_bytes()).hexdigest() == value
                for name, value in manifest['source'].items()}
check(all(hash_results.values()), 'source hash mismatch against premeasurement manifest')
for line in (BASE / 'PREIMPLEMENTATION.sha256').read_text().splitlines():
    digest, name = line.split()
    check(hashlib.sha256((BASE / name).read_bytes()).hexdigest() == digest,
          f'preimplementation content mismatch: {name}')

for ordinal, entry in enumerate(index):
    root = RUN / entry['trial']
    scenario = entry['scenario']
    before = len(issues)
    def trialcheck(value, description):
        check(value, root.name + ': ' + description)
    try:
        trialcheck(root.name == f'trial-{ordinal:03d}-{scenario}', 'unexpected trial name')
        trialcheck(read(root / 'case.json') == {'scenario': scenario,
              'socket_timeout_s': entry['socket_timeout_s']}, 'case/index mismatch')
        service, original, driver = [lines(root / f'{role}.jsonl')
                                     for role in ('service', 'original', 'driver')]
        traces = {'service': service, 'original': original, 'driver': driver}
        actors = ['original']
        if scenario == 'concurrent_recoverers':
            for actor in ('recovery1', 'recovery2'):
                traces[actor] = lines(root / f'{actor}.jsonl')
                actors.append(actor)
        pids = {}
        for role, trace in traces.items():
            trialcheck(bool(trace), f'{role} empty trace')
            trialcheck(len({r['pid'] for r in trace}) == 1, f'{role} PID changed')
            trialcheck(all(r['role'] == role for r in trace), f'{role} role mismatch')
            trialcheck(all(isinstance(r[k], int) and r[k] > 0 for r in trace
                           for k in ('mono_ns', 'utc_ns', 'pid', 'thread')), f'{role} malformed timestamp/identity')
            trialcheck(all(a['mono_ns'] < b['mono_ns'] for a, b in zip(trace, trace[1:])),
                       f'{role} nonmonotonic event log')
            pids[role] = trace[0]['pid']
        trialcheck(len(set(pids.values())) == len(pids), 'process identities not distinct')
        ready = read(root / 'ready.json')
        trialcheck(ready['host'] == '127.0.0.1' and ready['pid'] == pids['service'], 'ready identity/address')
        trialcheck(one(driver, 'service_spawned')['server_pid'] == pids['service'], 'service spawn mismatch')
        for actor in actors:
            trialcheck(one(driver, 'client_spawned', actor=actor)['client_pid'] == pids[actor], f'{actor} spawn mismatch')
            trialcheck(one(traces[actor], 'client_finished')['pid'] == pids[actor], f'{actor} not finished')
        with sqlite3.connect(f'file:{root / "effects.sqlite3"}?mode=ro&immutable=1', uri=True) as db:
            db.row_factory = sqlite3.Row
            integrity = db.execute('PRAGMA integrity_check').fetchone()[0]
            sql = {table: [dict(r) for r in db.execute(f'SELECT * FROM {table} ORDER BY {order}')]
                   for table, order in [('effects', 'id'), ('attempts', 'op'), ('keys', 'key')]}
        trialcheck(integrity == 'ok', 'SQLite integrity failure')
        trialcheck(len(sql['effects']) == EXPECTED[scenario], 'wrong SQL effect count')
        attempts = {a['op']: a for a in sql['attempts']}
        expected_states = {'original': 'committed'}
        if scenario == 'same_key':
            expected_states = {'original': 'deduplicated', 'retry': 'committed'}
        elif scenario == 'terminal_fence':
            expected_states = {'original': 'cancelled', 'retry': 'committed'}
        elif scenario == 'concurrent_recoverers':
            expected_states = {'original': 'cancelled', 'recovery1': 'committed', 'recovery2': 'committed'}
        elif scenario in ('live_negative', 'stale_negative', 'terminal_with_stale_read'):
            expected_states['retry'] = 'committed'
        trialcheck({op: a['state'] for op, a in attempts.items()} == expected_states, 'SQL operation states mismatch')
        trialcheck(collections.Counter(r['op'] for r in select(service, 'admitted')) == collections.Counter(expected_states.keys()),
                   'admission/operation mismatch')
        trialcheck(collections.Counter(r['op'] for r in select(service, 'handler_finished')) == collections.Counter(expected_states.keys()),
                   'handler completion/operation mismatch')
        trialcheck(not select(service, 'handler_error'), 'handler error retained')
        trialcheck(not select(driver, 'cleanup_terminated'), 'service forced termination')
        exit_event = one(driver, 'service_exit')
        stopped = one(service, 'server_stopped')
        trialcheck(exit_event['returncode'] == 0 and stopped['mono_ns'] < exit_event['mono_ns'], 'unclean service exit')
        trialcheck(max(r['mono_ns'] for r in select(service, 'handler_finished')) < stopped['mono_ns'],
                   'handler not completed before service stopped')
        final = read(root / 'final-service-read.json')
        trialcheck(final == dict(active=0, **sql), 'final service snapshot differs from stopped database')
        inspections = select(driver, 'response_received', path='/inspect')
        trialcheck(inspections and inspections[-1]['body'] == final, 'last inspect not retained exactly')
        trialcheck(inspections[-1]['mono_ns'] < one(driver, 'request_start', path='/shutdown')['mono_ns'],
                   'final inspect not before shutdown')
        for path in root.glob('*-stderr.txt'):
            trialcheck(path.stat().st_size == 0, f'nonempty stderr {path.name}')
        commits = select(service, 'effect_committed')
        trialcheck(len(commits) == len(sql['effects']), 'commit event count differs from SQLite')
        for effect in sql['effects']:
            committed = one(service, 'effect_committed', op=effect['op'])
            trialcheck(committed['effect_id'] == effect['id'] == attempts[effect['op']]['effect_id'], 'effect identity mismatch')
            trialcheck(effect['payload'] == '{"item":"A","value":1}', 'unexpected effect payload')
        admitted = one(service, 'admitted', op='original')
        start = one(original, 'request_start', path='/write')
        trialcheck(start['mono_ns'] < admitted['mono_ns'], 'admission before client request')
        trialcheck(start['timeout_s'] == entry['socket_timeout_s'], 'configured socket timeout mismatch')
        trialcheck(start['data']['hold_commit'] == (scenario in LATE), 'wrong commit gate configuration')
        trialcheck(start['data']['hold_reply'] == (scenario != 'no_fault' and scenario not in LATE), 'wrong reply gate configuration')
        timeout_event = None
        if scenario == 'no_fault':
            response = one(original, 'response_received')
            trialcheck(response['http_status'] == 200 and response['body']['state'] == 'committed', 'no-fault not successful')
            trialcheck(not select(original, 'request_timeout'), 'no-fault timeout')
        else:
            timeout_event = one(original, 'request_timeout', path='/write')
            trialcheck(timeout_event['exception'] == 'TimeoutError', 'not actual timeout exception')
            trialcheck(admitted['mono_ns'] < timeout_event['mono_ns'], 'timeout before admission')
            trialcheck(not select(original, 'response_received'), 'fault original also received success')
            outcome = read(root / 'original-result.json')
            trialcheck(outcome == {'status': 'timeout', 'exception': 'TimeoutError', 'pid': pids['original']}, 'original outcome mismatch')
            outcome_event = one(driver, 'original_outcome_observed')
            trialcheck(outcome_event['outcome'] == outcome and timeout_event['mono_ns'] < outcome_event['mono_ns'], 'driver outcome mismatch')
        snap = one(service, 'snapshot_taken')
        trialcheck(snap['effect_count'] == 0 and snap['mono_ns'] < admitted['mono_ns'], 'snapshot not pre-admission zero')
        snapshot_response = one(driver, 'response_received', path='/snapshot')
        trialcheck(snapshot_response['body'] == {'effect_count': 0, 'snapshot_mono_ns': snap['mono_ns']}, 'snapshot identity mismatch')
        if scenario in LATE:
            outcome_name = 'deduplicated' if scenario == 'same_key' else 'suppressed' if scenario in ('terminal_fence', 'concurrent_recoverers') else 'effect_committed'
            gate = one(service, 'commit_gate_wait', op='original')
            outcome = one(service, outcome_name, op='original')
            release = select(service, 'gates_released')[0]
            trialcheck(gate['mono_ns'] < timeout_event['mono_ns'] < release['mono_ns'] < outcome['mono_ns'], 'late original ordering mismatch')
        if scenario in ('stale_negative', 'terminal_with_stale_read', 'terminal_with_authoritative_read'):
            commit = one(service, 'effect_committed', op='original')
            wait = one(service, 'reply_gate_wait', op='original')
            trialcheck(commit['mono_ns'] < wait['mono_ns'] < timeout_event['mono_ns'], 'original not committed/reply-held before timeout')
        if scenario == 'live_negative':
            negatives = [r for r in select(service, 'authoritative_read') if r['operation_state'] == 'pending']
            trialcheck(len(negatives) == 1, 'missing exact live pending read')
            negative = negatives[0]
            trialcheck(negative['effect_count'] == 0 and not negative['terminal'], 'live read not pending zero')
            trialcheck(timeout_event['mono_ns'] < negative['mono_ns'] < one(service, 'admitted', op='retry')['mono_ns'], 'live read recovery order')
        if scenario in ('stale_negative', 'terminal_with_stale_read'):
            cache = one(service, 'cached_read')
            trialcheck(cache['effect_count'] == 0 and cache['snapshot_mono_ns'] == snap['mono_ns'], 'cache not exact retained zero snapshot')
            trialcheck(timeout_event['mono_ns'] < cache['mono_ns'] < one(service, 'admitted', op='retry')['mono_ns'], 'cached read recovery order')
        if scenario in ('terminal_fence', 'concurrent_recoverers'):
            fence = one(service, 'fence')
            trialcheck(fence['terminal'] and fence['operation_state'] == 'cancelled' and fence['effect_count'] == 0, 'fence not cancelled zero')
            trialcheck(timeout_event['mono_ns'] < fence['mono_ns'] < select(service, 'gates_released')[0]['mono_ns'], 'fence timing mismatch')
            trialcheck(not select(service, 'effect_committed', op='original') and attempts['original']['effect_id'] is None, 'fenced original has effect')
        if scenario == 'same_key':
            trialcheck(len(sql['keys']) == 1 and sql['keys'][0]['key'] == 'intent-A', 'retained key absent')
            key = sql['keys'][0]
            trialcheck(key['digest'] == hashlib.sha256(sql['effects'][0]['payload'].encode()).hexdigest(), 'key digest mismatch')
            trialcheck(all(a['effect_id'] == key['effect_id'] for a in attempts.values()), 'dedup not same effect')
            trialcheck(all(r['key'] == 'intent-A' for r in select(service, 'admitted')), 'idempotency keys differ')
        else:
            trialcheck(sql['keys'] == [], 'unexpected key control')
        if scenario.startswith('terminal_with_'):
            terminal_reads = [r for r in select(service, 'authoritative_read') if r['terminal']]
            trialcheck(len(terminal_reads) == 1, 'not exactly one terminal read')
            terminal = terminal_reads[0]
            trialcheck(terminal['operation_state'] == 'committed' and terminal['effect_count'] == 1, 'terminal read not committed one')
            trialcheck(timeout_event['mono_ns'] < terminal['mono_ns'], 'terminal read before timeout')
            if scenario == 'terminal_with_stale_read':
                trialcheck(terminal['mono_ns'] < one(service, 'cached_read')['mono_ns'], 'cache precedes terminal read')
            else:
                trialcheck(one(driver, 'policy_decision')['action'] == 'no_driver_retry', 'authoritative read failed to stop retry')
        if scenario == 'concurrent_recoverers':
            reads, writes = [], []
            barrier = one(driver, 'recoverer_barrier_release')
            for actor in ('recovery1', 'recovery2'):
                response = one(traces[actor], 'response_received', path='/read')
                body = response['body']
                trialcheck(response['http_status'] == 200 and body == {'op': 'original', 'operation_state': 'cancelled', 'terminal': True, 'effect_count': 0}, f'{actor} not terminal zero')
                trialcheck(read(root / f'{actor}-observed.json') == {k: response[k] for k in ('status','http_status','body')}, f'{actor} observation mismatch')
                write = one(traces[actor], 'request_start', path='/write')
                admitted_recovery = one(service, 'admitted', op=actor)
                trialcheck(response['mono_ns'] < barrier['mono_ns'] < write['mono_ns'] < admitted_recovery['mono_ns'], f'{actor} barrier/write timing')
                trialcheck(admitted_recovery['key'] is None, f'{actor} unexpectedly keyed')
                reads.append(response['mono_ns'])
                writes.append(admitted_recovery['mono_ns'])
            trialcheck(max(reads) < min(writes), 'recovery writes precede both reads')
        result = read(root / 'result.json')
        trialcheck(entry['status'] == 'pass' and entry['violations'] == [] and result['violations'] == [], 'recorded status not pass')
        trialcheck(result['database'] == dict(integrity=integrity, **sql), 'reported database differs from independent SQL')
        trialcheck(entry['database'] == result['database'] and result['effect_count'] == len(sql['effects']), 'index/result/SQL mismatch')
        rows.append({'trial': root.name, 'scenario': scenario, 'socket_timeout_s': entry['socket_timeout_s'],
                     'effect_count': len(sql['effects']), 'attempt_count': len(sql['attempts']),
                     'process_count': len(pids), 'original_admission_to_timeout_ms': None if timeout_event is None else
                     (timeout_event['mono_ns'] - admitted['mono_ns']) / 1e6,
                     'violations': issues[before:]})
    except Exception as exc:
        issues.append(f'{root.name}: audit exception: {type(exc).__name__}: {exc}')

counts = {scenario: {'trials': sum(r['scenario'] == scenario for r in rows),
                   'effects': sorted({r['effect_count'] for r in rows if r['scenario'] == scenario}),
                   'violations': sum(bool(r['violations']) for r in rows if r['scenario'] == scenario)} for scenario in SCENARIOS}
actual_bytes = sum(p.stat().st_size for p in RUN.rglob('*') if p.is_file())
check(actual_bytes < 30_000_000, 'actual retained primary output exceeds 30 MB')
check(summary['planned'] == summary['recorded'] == summary['passed'] == 120 and
      summary['failed'] == summary['invalid'] == summary['not_run'] == 0, 'primary summary denominator/status mismatch')
check(summary['elapsed_s'] < 120, 'observed primary duration exceeds 120 seconds')
check(summary['source_unchanged'] and summary['output_cap_ok'], 'primary summary source/bounds failed')
for scenario in SCENARIOS:
    check(summary['by_scenario'][scenario]['effect_counts'] == [r['effect_count'] for r in rows if r['scenario'] == scenario], 'summary effect counts mismatch: ' + scenario)
report = {'independent_audit_passed': not issues, 'planned_trials': 120, 'indexed_trials': len(index),
          'audited_trials': len(rows), 'retained_trial_directories': len(directories),
          'actual_bytes_including_summary': actual_bytes, 'primary_elapsed_s': summary['elapsed_s'],
          'source_hash_matches': hash_results, 'by_scenario': counts,
          'total_effects': sum(r['effect_count'] for r in rows),
          'total_attempts': sum(r['attempt_count'] for r in rows),
          'distinct_processes_per_trial': dict(collections.Counter(r['process_count'] for r in rows)),
          'fault_trials': sum(r['original_admission_to_timeout_ms'] is not None for r in rows),
          'min_admission_to_timeout_ms': min(r['original_admission_to_timeout_ms'] for r in rows if r['original_admission_to_timeout_ms'] is not None),
          'violations': issues, 'rows': rows}
print(json.dumps(report, indent=2, sort_keys=True))
sys.exit(0 if not issues else 1)
