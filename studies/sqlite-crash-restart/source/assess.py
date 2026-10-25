"""Raw receipt checks separate schedule validity from literal prediction failure."""
import hashlib
import json
import sqlite3
import shutil
import tempfile
from contextlib import closing
from pathlib import Path


def sql_snapshot(path):
    with closing(sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)) as db:
        db.row_factory = sqlite3.Row
        result = {table: [dict(row) for row in db.execute(f'SELECT * FROM {table} ORDER BY 1')]
                  for table in ('effects', 'keys', 'attempts')}
        result.update(integrity=[row[0] for row in db.execute('PRAGMA integrity_check')],
                      journal_mode=db.execute('PRAGMA journal_mode').fetchone()[0],
                      synchronous=db.execute('PRAGMA synchronous').fetchone()[0])
    return result


def read_evidence(root):
    root = Path(root)
    def read(name):
        return json.loads((root / name).read_text())
    result = {actor: [json.loads(line) for line in (root / f'{actor}.jsonl').read_text().splitlines()]
              for actor in ('driver', 'original', 'recovery')}
    result.update(nonce=read('identity.json')['nonce'], barrier=read('original-barrier.json'),
                  original_request=read('original-request.json'), recovery_request=read('recovery-request.json'),
                  original_response_exists=(root / 'original-response.json').exists(),
                  recovery_response=read('recovery-response.json'), before_recovery=read('recovery-before.json'),
                  before_recovery_sql=recover_crash_copy(root),
                  final_saved=read('final-sql.json'), final_sql=sql_snapshot(root / 'effects.sqlite3'))
    result['stderr_clean'] = all((root / f'{actor}-stderr.txt').read_bytes() == b'' for actor in ('original', 'recovery'))
    return result


def recover_crash_copy(root):
    """Recover copied crash bytes, never mutate the retained crash image."""
    root = Path(root)
    with tempfile.TemporaryDirectory(prefix='timeout-crash-audit-') as temporary:
        destination = Path(temporary) / 'effects.sqlite3'
        shutil.copyfile(root / 'crash-effects.sqlite3', destination)
        journal = root / 'crash-effects.sqlite3-journal'
        if journal.exists():
            shutil.copyfile(journal, destination.with_name('effects.sqlite3-journal'))
        with closing(sqlite3.connect(destination, timeout=2)) as db:
            db.execute('SELECT count(*) FROM effects').fetchone()  # SQLite recovery, if required.
        return sql_snapshot(destination)


def assess(case, evidence):
    invalid, failures = [], []
    measurements = {}
    def require(condition, reason):
        if not condition:
            invalid.append(reason)
    def predict(condition, reason):
        if not condition:
            failures.append(reason)
    try:
        e, expected = evidence, case['expected']
        events = {}
        for actor in ('driver', 'original', 'recovery'):
            rows = e[actor]
            require(bool(rows), f'{actor}: missing trace')
            require(all(r['actor'] == actor and r['nonce'] == e['nonce'] for r in rows), f'{actor}: identity mismatch')
            require(len({r['pid'] for r in rows}) == 1, f'{actor}: mixed process identities')
            require(all(a['mono_ns'] < b['mono_ns'] for a, b in zip(rows, rows[1:])), f'{actor}: nonmonotonic trace')
            require(len({r['event'] for r in rows}) == len(rows), f'{actor}: repeated event')
            events[actor] = {r['event']: r for r in rows}
        o, r, d = events['original'], events['recovery'], events['driver']
        opid, rpid, dpid = o['ready']['pid'], r['ready']['pid'], d['original_started']['pid']
        require(len({opid, rpid, dpid}) == 3, 'process identities not distinct')
        require(d['original_started']['child_pid'] == d['kill_requested']['child_pid'] == d['original_exit']['child_pid'] == opid, 'original child mismatch')
        require(d['recovery_started']['child_pid'] == d['recovery_exit']['child_pid'] == rpid, 'recovery child mismatch')
        require(d['original_exit']['returncode'] == -9, 'original did not exit via SIGKILL')
        require(d['recovery_exit']['returncode'] == 0, 'recovery did not finish successfully')
        require(e.get('stderr_clean', True), 'unexpected worker stderr')
        require(e['barrier'] == o['barrier_reached'], 'barrier receipt differs from service event')
        require(o['barrier_reached']['phase'] == case['phase'] and o['barrier_reached']['op'] == 'original', 'wrong barrier phase/operation')
        require(not e['original_response_exists'] and 'response_ready' not in o and 'worker_finished' not in o, 'original returned a response')
        original_names = ['ready', 'request_received', 'before_commit']
        if case['phase'] == 'after_commit':
            original_names.append('after_commit')
        original_names.append('barrier_reached')
        require(list(o) == original_names, 'original schedule differs from declared barrier')
        require(list(r) == ['ready', 'request_received', 'before_commit', 'after_commit', 'response_ready', 'worker_finished'], 'recovery lifecycle incomplete')
        timeline = [o['barrier_reached'], d['kill_requested'], d['original_exit'], d['recovery_started'], r['ready'], r['request_received'], r['response_ready'], r['worker_finished'], d['recovery_exit'], d['final_read']]
        require(all(a['mono_ns'] < b['mono_ns'] for a, b in zip(timeline, timeline[1:])), 'crash/restart lifecycle order violated')
        for first in (o['ready'], r['ready']):
            require(first['journal_mode'] == 'delete' and first['synchronous'] == 2, 'wrong SQLite configuration')
        original_request = {'op': 'original', 'payload': {'item': 'A', 'value': 1}, 'key': None if case['mode'] == 'no_key' else 'K'}
        recovery_request = {'op': 'recovery', 'payload': expected['recovery_payload'], 'key': original_request['key']}
        require(e['original_request'] == o['request_received']['request'] == original_request, 'wrong original request')
        require(e['recovery_request'] == r['request_received']['request'] == recovery_request, 'wrong recovery request')
        require(e['recovery_response'] == r['response_ready']['response'], 'recovery reply receipt mismatch')
        require(e['final_saved'] == e['final_sql'], 'final snapshot disagrees with independent SQL reread')
        before, final, reply = e['before_recovery'], e['final_sql'], e['recovery_response']
        require(before == e['before_recovery_sql'], 'restart snapshot differs from independently recovered crash image')
        for snapshot, label in ((before, 'before recovery'), (final, 'final')):
            predict(snapshot['integrity'] == ['ok'], f'{label}: integrity check failed')
            require(snapshot['journal_mode'] == 'delete' and snapshot['synchronous'] == 2, f'{label}: wrong storage configuration')
        predict(len(before['effects']) == expected['effects_before_recovery'], 'wrong restart effect count')
        predict(len(before['keys']) == expected['keys_before_recovery'], 'wrong restart key count')
        predict(len(final['effects']) == expected['effects_final'], 'wrong final effect count')
        predict(len(final['keys']) == expected['keys_final'], 'wrong final key count')
        predict(reply['state'] == expected['recovery_state'] and reply['status'] == expected['recovery_status'], 'wrong recovery response')
        original_effect = 1 if expected['original_payload_survives'] else None
        wanted_original = {'op': 'original', 'state': expected['original_state_after_restart'], 'effect_id': original_effect}
        predict(before['attempts'] == [wanted_original], 'wrong original attempt after restart')
        wanted_effects = []
        if expected['original_payload_survives']:
            wanted_effects.append({'id': 1, 'op': 'original', 'payload': '{"item":"A","value":1}'})
        if expected['recovery_state'] == 'committed':
            wanted_effects.append({'id': len(wanted_effects) + 1, 'op': 'recovery', 'payload': json.dumps(expected['recovery_payload'], sort_keys=True, separators=(',', ':'))})
        predict(final['effects'] == wanted_effects, 'wrong effect identities or payloads')
        recovery_effect = None if expected['recovery_state'] == 'rejected' else len(wanted_effects)
        predict(reply['effect_id'] == recovery_effect, 'wrong returned effect id')
        predict(final['attempts'] == [wanted_original, {'op': 'recovery', 'state': expected['recovery_state'], 'effect_id': recovery_effect}], 'wrong final attempts')
        wanted_keys = [] if case['mode'] == 'no_key' else [{'key': 'K', 'effect_id': 1, 'digest': hashlib.sha256(wanted_effects[0]['payload'].encode()).hexdigest()}]
        predict(final['keys'] == wanted_keys, 'wrong retained payload/key binding')
        original_payload_count = sum(row['payload'] == '{"item":"A","value":1}' for row in final['effects'])
        measurements = {'final_effect_count': len(final['effects']), 'original_payload_count': original_payload_count,
                        'original_goal_completed': original_payload_count >= 1,
                        'original_payload_exactly_once': original_payload_count == 1,
                        'extra_effects_beyond_one': max(0, len(final['effects']) - 1),
                        'recovery_status': reply['status'], 'recovery_state': reply['state']}
        predict(original_payload_count == expected['original_payload_count_final'], 'wrong count of original intended payload')
    except (KeyError, TypeError, IndexError, ValueError) as exc:
        invalid.append(f'incomplete or malformed evidence: {type(exc).__name__}: {exc}')
    return {'classification': 'invalid' if invalid else ('valid_prediction_fail' if failures else 'valid_pass'),
            'validity_errors': invalid, 'prediction_errors': failures, 'measurements': measurements}

def summarize(plan, rows):
    planned = [case['id'] for case in plan]
    ids = [row['id'] for row in rows]
    if len(set(planned)) != len(planned) or len(set(ids)) != len(ids) or not set(ids).issubset(planned):
        raise ValueError('duplicate or unplanned row')
    counts = dict(planned=len(plan), valid_pass=0, valid_prediction_fail=0, invalid=0, not_run=len(plan)-len(rows))
    for row in rows:
        status = row['classification']
        if status not in ('valid_pass', 'valid_prediction_fail', 'invalid', 'not_run'):
            raise ValueError('unrecognized row classification')
        counts[status] += 1
    counts['valid'] = counts['valid_pass'] + counts['valid_prediction_fail']
    counts['attempted'] = len(plan) - counts['not_run']
    return counts


def cell_summaries(plan, rows):
    result = {}
    for phase, mode in sorted({(c['phase'], c['mode']) for c in plan}):
        cell = [c for c in plan if c['phase'] == phase and c['mode'] == mode]
        ids = {c['id'] for c in cell}
        result[f'{phase}/{mode}'] = summarize(cell, [r for r in rows if r['id'] in ids])
    return result
