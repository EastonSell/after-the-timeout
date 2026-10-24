"""Post-run whole-matrix verifier, added after the primary measurement.

Keeps the frozen producer/per-trial verifier unchanged. Adds strict completeness,
source identity, and exact cached-snapshot provenance checks. This is an integrity
checker for this fixed experiment, not an authenticated/tamper-proof ledger.
"""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE))
from verify import verify_trial

SCENARIOS = ('no_fault', 'live_negative', 'stale_negative', 'same_key', 'terminal_fence',
             'terminal_with_stale_read', 'terminal_with_authoritative_read', 'concurrent_recoverers')
SOURCE_FILES = {'PLAN.md', 'PREIMPLEMENTATION.sha256', 'PROTOCOL.md', 'client.py', 'common.py',
                'experiment.py', 'service.py', 'test_evidence.py', 'test_process.py', 'verify.py'}


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(row) for row in Path(path).read_text().splitlines()]


def verify_run(run, source_root=None):
    run, source_root = Path(run), Path(source_root or BASE)
    issues, rows = [], []
    def check(value, message):
        if not value:
            issues.append(message)
    def one(trace, event, **fields):
        selected = [r for r in trace if r['event'] == event and all(r.get(k) == v for k, v in fields.items())]
        if len(selected) != 1:
            raise ValueError(f'expected one {event} {fields}, found {len(selected)}')
        return selected[0]
    try:
        manifest, summary, index = read(run / 'frozen-input.json'), read(run / 'summary.json'), lines(run / 'trials.jsonl')
    except (OSError, ValueError) as exc:
        return {'passed': False, 'planned_trials': 120, 'audited_trials': 0,
                'violations': [f'missing_or_invalid_run_metadata: {type(exc).__name__}: {exc}'], 'rows': []}
    try:
        expected = [(timeout, repeat, scenario) for timeout in (0.08, 0.12, 0.20)
                    for repeat in range(5) for scenario in SCENARIOS]
        expected_names = [f'trial-{i:03d}-{cell[2]}' for i, cell in enumerate(expected)]
        check(len(index) == 120, 'index_count_not_120')
        check([(r['socket_timeout_s'], r['repetition'], r['scenario']) for r in index] == expected, 'index_matrix_mismatch')
        check([r['trial'] for r in index] == expected_names, 'index_trial_names_mismatch')
        actual_names = {p.name for p in run.glob('trial-*') if p.is_dir()}
        check(actual_names == set(expected_names), 'trial_directory_matrix_mismatch')
        check(manifest['plan'] == dict(scenarios=list(SCENARIOS), timeouts=[0.08, 0.12, 0.20], repetitions=5, planned_trials=120), 'frozen_plan_mismatch')
        check(set(manifest['source']) == SOURCE_FILES, 'source_file_set_mismatch')
        for name in SOURCE_FILES:
            check(hashlib.sha256((source_root / name).read_bytes()).hexdigest() == manifest['source'].get(name), 'source_hash_mismatch: ' + name)
        check(hashlib.sha256((BASE / 'verify.py').read_bytes()).hexdigest() == manifest['source'].get('verify.py'), 'loaded_per_trial_verifier_mismatch')
        for record in (source_root / 'PREIMPLEMENTATION.sha256').read_text().splitlines():
            digest, name = record.split()
            if name not in ('PLAN.md', 'PROTOCOL.md'):
                raise ValueError('unexpected preimplementation source name')
            check(hashlib.sha256((source_root / name).read_bytes()).hexdigest() == digest, 'preimplementation_hash_mismatch: ' + name)
        check(summary['planned'] == summary['recorded'] == summary['passed'] == 120, 'summary_denominator_mismatch')
        check(summary['failed'] == summary['invalid'] == summary['not_run'] == 0, 'summary_records_nonpassing_trials')
        check(summary['source_unchanged'] and summary['output_cap_ok'], 'summary_source_or_size_failed')
        check(0 <= summary['elapsed_s'] < 120, 'observed_runtime_out_of_bounds')
        check(sum(p.stat().st_size for p in run.rglob('*') if p.is_file()) <= 30_000_000, 'observed_size_out_of_bounds')
    except (OSError, KeyError, TypeError, ValueError) as exc:
        issues.append(f'malformed_run_metadata: {type(exc).__name__}: {exc}')
        return {'passed': False, 'planned_trials': 120, 'audited_trials': 0, 'violations': issues, 'rows': []}

    for number, (timeout, repetition, scenario) in enumerate(expected):
        name = expected_names[number]
        root = run / name
        before = len(issues)
        try:
            check(read(root / 'case.json') == dict(scenario=scenario, socket_timeout_s=timeout), name + ': case_mismatch')
            result = verify_trial(root, scenario)
            issues.extend(name + ': ' + message for message in result['violations'])
            service, driver = lines(root / 'service.jsonl'), lines(root / 'driver.jsonl')
            finished = [r for r in service if r['event'] == 'handler_finished']
            attempts = result['database']['attempts']
            check(collections.Counter(r['op'] for r in finished) == collections.Counter(r['op'] for r in attempts), name + ': handler_completion_set_mismatch')
            stopped = one(service, 'server_stopped')
            exited = one(driver, 'service_exit')
            check(exited['returncode'] == 0, name + ': unclean_service_exit')
            check(finished and max(r['mono_ns'] for r in finished) < stopped['mono_ns'] < exited['mono_ns'], name + ': shutdown_completion_order_mismatch')
            check(not any(r['event'] == 'cleanup_terminated' for r in driver), name + ': forced_service_termination')
            final = read(root / 'final-service-read.json')
            database = {k: result['database'][k] for k in ('attempts', 'effects', 'keys')}
            check(final == dict(active=0, **database), name + ': final_service_snapshot_mismatch')
            inspections = [r for r in driver if r['event'] == 'response_received' and r['path'] == '/inspect']
            check(inspections and inspections[-1]['http_status'] == 200 and inspections[-1]['body'] == final, name + ': final_inspection_reply_mismatch')
            shutdown = one(driver, 'request_start', path='/shutdown')
            check(inspections and inspections[-1]['mono_ns'] < shutdown['mono_ns'] < stopped['mono_ns'], name + ': final_inspection_shutdown_order_mismatch')
            snapshot = one(service, 'snapshot_taken')
            admitted = one(service, 'admitted', op='original')
            check(snapshot['effect_count'] == 0 and snapshot['mono_ns'] < admitted['mono_ns'], name + ': snapshot_not_prewrite_zero')
            snapshot_body = dict(effect_count=0, snapshot_mono_ns=snapshot['mono_ns'])
            reply = one(driver, 'response_received', path='/snapshot')
            check(reply['http_status'] == 200 and reply['body'] == snapshot_body, name + ': snapshot_reply_identity_mismatch')
            check(snapshot['mono_ns'] < reply['mono_ns'] < admitted['mono_ns'], name + ': snapshot_reply_order_mismatch')
            if scenario in ('stale_negative', 'terminal_with_stale_read'):
                cache = one(service, 'cached_read')
                check(cache['effect_count'] == 0 and cache['snapshot_mono_ns'] == snapshot['mono_ns'], name + ': cached_snapshot_identity_mismatch')
                cached_reply = one(driver, 'response_received', path='/cached')
                check(cached_reply['http_status'] == 200 and cached_reply['body'] == snapshot_body, name + ': cached_reply_identity_mismatch')
                check(cache['mono_ns'] < cached_reply['mono_ns'] < one(service, 'admitted', op='retry')['mono_ns'], name + ': cached_reply_order_mismatch')
            saved = read(root / 'result.json')
            entry = index[number] if number < len(index) else {}
            for key in ('database', 'effect_count', 'server_pid', 'original_client_pid', 'driver_pid'):
                check(saved.get(key) == result[key] == entry.get(key), name + ': saved_result_mismatch: ' + key)
            check(entry.get('status') == 'pass' and entry.get('violations') == [] and saved.get('violations') == [], name + ': recorded_status_mismatch')
            rows.append(dict(trial=name, scenario=scenario, effect_count=result['effect_count'], violations=issues[before:]))
        except (OSError, KeyError, TypeError, ValueError, StopIteration, IndexError) as exc:
            issues.append(f'{name}: invalid_trial_evidence: {type(exc).__name__}: {exc}')
    for scenario in SCENARIOS:
        actual = [r['effect_count'] for r in rows if r['scenario'] == scenario]
        group = summary.get('by_scenario', {}).get(scenario, {})
        check(group.get('trials') == group.get('passed') == 15 and len(actual) == 15, 'scenario_denominator_mismatch: ' + scenario)
        check(group.get('effect_counts') == actual, 'scenario_counts_mismatch: ' + scenario)
    return dict(passed=not issues and len(rows) == 120, planned_trials=120, indexed_trials=len(index),
                audited_trials=len(rows), violations=issues, rows=rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run', type=Path)
    parser.add_argument('--source-root', type=Path, default=BASE)
    args = parser.parse_args()
    report = verify_run(args.run, args.source_root)
    print(json.dumps(report, indent=2, sort_keys=True))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
