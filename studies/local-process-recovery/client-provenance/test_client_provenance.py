"""Mutation regressions copy retained evidence; the primary fixture is read-only."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

BASE = Path(__file__).resolve().parents[1]
PRIMARY = BASE / 'evidence' / 'primary-run'
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_client_run import verify_client_run


class ClientProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.copy = Path(self.temporary.name) / 'run'

    def copy_full(self):
        shutil.copytree(PRIMARY, self.copy)

    def trace(self, trial, role, mutate):
        path = self.copy / trial / (role + '.jsonl')
        rows = [json.loads(line) for line in path.read_text().splitlines()]
        path.write_text(''.join(json.dumps(row) + '\n' for row in mutate(rows)))

    def change_event(self, trial, role, event, **fields):
        def change(rows):
            for row in rows:
                if row['event'] == event:
                    row.update(fields)
            return rows
        self.trace(trial, role, change)

    def rejects(self):
        self.assertFalse(verify_client_run(self.copy)['passed'])

    def cli(self, optimized=False):
        command = [sys.executable, '-B'] + (['-O'] if optimized else [])
        command += [str(Path(__file__).with_name('verify_client_run.py')), str(self.copy)]
        return subprocess.run(command, capture_output=True, text=True, check=False)

    def test_corrupt_database_is_structured_failure(self):
        self.copy_full()
        (self.copy / 'trial-002-stale_negative' / 'effects.sqlite3').write_bytes(b'not a database')
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')
        self.assertFalse(json.loads(result.stdout)['passed'])

    def test_missing_database_is_structured_failure(self):
        self.copy_full()
        (self.copy / 'trial-002-stale_negative' / 'effects.sqlite3').unlink()
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')
        self.assertFalse(json.loads(result.stdout)['passed'])

    def test_source_manifest_wrong_shape_is_structured_failure(self):
        self.copy_full()
        path = self.copy / 'frozen-input.json'
        data = json.loads(path.read_text())
        data['source'] = list(data['source'])
        path.write_text(json.dumps(data))
        result = self.cli()
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')
        self.assertFalse(json.loads(result.stdout)['passed'])

    def test_optimized_cli_preserves_timeout_rejection(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'original', 'request_timeout', exception='ConnectionResetError')
        result = self.cli(optimized=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, '')
        report = json.loads(result.stdout)
        self.assertFalse(report['passed'])
        self.assertTrue(any('invalid_client_evidence' in issue for issue in report['violations']))

    def test_coordinated_non_timeout_receipts_are_rejected(self):
        self.copy_full()
        trial = 'trial-002-stale_negative'
        self.change_event(trial, 'original', 'request_timeout', exception='ConnectionResetError')
        path = self.copy / trial / 'original-result.json'
        outcome = json.loads(path.read_text())
        outcome['exception'] = 'ConnectionResetError'
        path.write_text(json.dumps(outcome))
        self.change_event(trial, 'driver', 'original_outcome_observed', outcome=outcome)
        self.rejects()

    def test_complete_primary_is_accepted(self):
        report = verify_client_run(PRIMARY)
        self.assertTrue(report['passed'], report['violations'])
        self.assertEqual(report['audited_trials'], 120)

    def test_parent_spawn_log_can_follow_child_start(self):
        self.copy_full()
        trial = 'trial-002-stale_negative'
        for role, event in (('service', 'service_spawned'), ('original', 'client_spawned')):
            path = self.copy / trial / (role + '.jsonl')
            child_start = json.loads(path.read_text().splitlines()[0])['mono_ns']
            self.change_event(trial, 'driver', event, mono_ns=child_start + 1)
        report = verify_client_run(self.copy)
        self.assertTrue(report['passed'], report['violations'])

    def test_configured_timeout_must_match_matrix(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'original', 'request_start', timeout_s=999)
        self.rejects()

    def test_timeout_exception_cannot_be_a_connection_reset(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'original', 'request_timeout', exception='ConnectionResetError')
        self.rejects()

    def test_timeout_must_belong_to_the_write(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'original', 'request_timeout', path='/read')
        self.rejects()

    def test_fault_gate_configuration_must_match_scenario(self):
        self.copy_full()
        self.change_event('trial-003-same_key', 'original', 'request_start',
                          data={'op': 'original', 'key': 'intent-A', 'hold_commit': False, 'hold_reply': False})
        self.rejects()

    def test_saved_original_outcome_must_match_trace(self):
        self.copy_full()
        path = self.copy / 'trial-002-stale_negative' / 'original-result.json'
        data = json.loads(path.read_text())
        data['exception'] = 'ConnectionResetError'
        path.write_text(json.dumps(data))
        self.rejects()

    def test_driver_observation_must_match_saved_original_outcome(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'driver', 'original_outcome_observed',
                          outcome={'status': 'response', 'http_status': 200})
        self.rejects()

    def test_client_must_finish_before_driver_observes_outcome(self):
        self.copy_full()
        original = self.copy / 'trial-002-stale_negative' / 'original.jsonl'
        rows = [json.loads(line) for line in original.read_text().splitlines()]
        finished = next(row['mono_ns'] for row in rows if row['event'] == 'client_finished')
        self.change_event('trial-002-stale_negative', 'driver', 'original_outcome_observed', mono_ns=finished - 1)
        self.rejects()

    def test_missing_client_finished_is_rejected(self):
        self.copy_full()
        self.trace('trial-002-stale_negative', 'original',
                   lambda rows: [row for row in rows if row['event'] != 'client_finished'])
        self.rejects()

    def test_trace_process_identity_cannot_change_mid_request(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'original', 'request_timeout', pid=999999)
        self.rejects()

    def test_spawn_receipt_must_identify_client_process(self):
        self.copy_full()
        self.change_event('trial-002-stale_negative', 'driver', 'client_spawned', client_pid=999999)
        self.rejects()

    def test_original_cannot_share_driver_process(self):
        self.copy_full()
        trial = self.copy / 'trial-002-stale_negative'
        pid = json.loads((trial / 'driver.jsonl').read_text().splitlines()[0])['pid']
        self.trace(trial.name, 'original', lambda rows: [dict(row, pid=pid) for row in rows])
        # Keep the old checker's derived result/index identities consistent too.
        for name in ('original-result.json', 'result.json'):
            path = trial / name
            data = json.loads(path.read_text())
            data['pid' if name == 'original-result.json' else 'original_client_pid'] = pid
            path.write_text(json.dumps(data))
        index = self.copy / 'trials.jsonl'
        rows = [json.loads(line) for line in index.read_text().splitlines()]
        rows[2]['original_client_pid'] = pid
        index.write_text(''.join(json.dumps(row) + '\n' for row in rows))
        self.change_event(trial.name, 'driver', 'client_spawned', client_pid=pid)
        self.change_event(trial.name, 'driver', 'original_outcome_observed',
                          outcome={'status': 'timeout', 'exception': 'TimeoutError', 'pid': pid})
        self.rejects()

    def test_recoverer_read_body_must_match_saved_observation(self):
        self.copy_full()
        def change(rows):
            for row in rows:
                if row['event'] == 'response_received' and row['path'] == '/read':
                    row['body']['effect_count'] = 1
            return rows
        self.trace('trial-007-concurrent_recoverers', 'recovery1', change)
        self.rejects()

    def test_recoverer_must_write_only_after_driver_barrier(self):
        self.copy_full()
        def change(rows):
            write = next(row['mono_ns'] for row in rows if row['event'] == 'service_exit')
            for row in rows:
                if row['event'] == 'recoverer_barrier_release':
                    row['mono_ns'] = write - 1
            return rows
        self.trace('trial-007-concurrent_recoverers', 'driver', change)
        self.rejects()

    def test_recoverer_write_reply_must_match_database(self):
        self.copy_full()
        def change(rows):
            for row in rows:
                if row['event'] == 'response_received' and row['path'] == '/write':
                    row['body']['effect_id'] = 999
            return rows
        self.trace('trial-007-concurrent_recoverers', 'recovery1', change)
        self.rejects()

    def test_saved_recoverer_result_must_match_write_reply(self):
        self.copy_full()
        path = self.copy / 'trial-007-concurrent_recoverers' / 'recovery2-result.json'
        data = json.loads(path.read_text())
        data['body']['effect_id'] = 999
        path.write_text(json.dumps(data))
        self.rejects()

    def test_no_fault_reply_must_match_committed_effect(self):
        self.copy_full()
        self.change_event('trial-000-no_fault', 'original', 'response_received',
                          body={'op': 'original', 'state': 'committed', 'effect_id': 999})
        self.rejects()


if __name__ == '__main__':
    unittest.main()
