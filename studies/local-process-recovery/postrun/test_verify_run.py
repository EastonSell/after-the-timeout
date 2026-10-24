"""Post-run regression mutations use copies, never the retained primary data."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_run import verify_run
BASE = Path(__file__).resolve().parents[1]
PRIMARY = BASE / 'evidence' / 'primary-run'


class HardenedVerifierTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.copy = Path(self.temporary.name) / 'run'

    def copy_full(self):
        shutil.copytree(PRIMARY, self.copy)
        return self.copy

    def alter_trace(self, name, mutate):
        target = self.copy / 'trial-002-stale_negative' / name
        rows = [json.loads(x) for x in target.read_text().splitlines()]
        target.write_text(''.join(json.dumps(r)+'\n' for r in mutate(rows)))

    def test_complete_primary_is_accepted(self):
        self.assertTrue(verify_run(PRIMARY)['passed'])

    def test_one_trial_without_manifest_is_rejected(self):
        self.copy.mkdir()
        shutil.copytree(PRIMARY / 'trial-000-no_fault', self.copy / 'trial-000-no_fault')
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_missing_indexed_trial_is_rejected(self):
        self.copy_full()
        shutil.rmtree(self.copy / 'trial-000-no_fault')
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_coordinated_denominator_shrink_is_rejected(self):
        self.copy_full()
        shutil.rmtree(self.copy / 'trial-000-no_fault')
        index = self.copy / 'trials.jsonl'
        index.write_text('\n'.join(index.read_text().splitlines()[1:])+'\n')
        summary = self.copy / 'summary.json'
        data = json.loads(summary.read_text())
        for key in ('planned', 'recorded', 'passed'): data[key] = 119
        summary.write_text(json.dumps(data))
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_missing_snapshot_event_is_rejected(self):
        self.copy_full()
        self.alter_trace('service.jsonl', lambda rows: [r for r in rows if r['event'] != 'snapshot_taken'])
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_wrong_cached_snapshot_identity_is_rejected(self):
        self.copy_full()
        def mutate(rows):
            for row in rows:
                if row['event'] == 'cached_read': row['snapshot_mono_ns'] -= 1
            return rows
        self.alter_trace('service.jsonl', mutate)
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_wrong_snapshot_reply_identity_is_rejected(self):
        self.copy_full()
        def mutate(rows):
            for row in rows:
                if row['event'] == 'response_received' and row['path'] == '/snapshot':
                    row['body']['snapshot_mono_ns'] -= 1
            return rows
        self.alter_trace('driver.jsonl', mutate)
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_nonzero_final_active_handlers_is_rejected(self):
        self.copy_full()
        path = self.copy / 'trial-002-stale_negative' / 'final-service-read.json'
        data = json.loads(path.read_text());data['active'] = 1
        path.write_text(json.dumps(data))
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_missing_service_exit_is_rejected(self):
        self.copy_full()
        self.alter_trace('driver.jsonl', lambda rows: [r for r in rows if r['event'] != 'service_exit'])
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_unclean_service_exit_is_rejected(self):
        self.copy_full()
        def mutate(rows):
            for row in rows:
                if row['event'] == 'service_exit': row['returncode'] = 9
            return rows
        self.alter_trace('driver.jsonl', mutate)
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_server_stop_before_handler_completion_is_rejected(self):
        self.copy_full()
        def mutate(rows):
            finished = min(r['mono_ns'] for r in rows if r['event'] == 'handler_finished')
            for row in rows:
                if row['event'] == 'server_stopped': row['mono_ns'] = finished - 1
            return rows
        self.alter_trace('service.jsonl', mutate)
        self.assertFalse(verify_run(self.copy)['passed'])

    def test_source_hash_mismatch_is_rejected(self):
        self.copy_full()
        path = self.copy / 'frozen-input.json'
        data = json.loads(path.read_text());data['source']['verify.py'] = '0'*64
        path.write_text(json.dumps(data))
        self.assertFalse(verify_run(self.copy)['passed'])


if __name__ == '__main__': unittest.main()
