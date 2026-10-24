"""Tests target silent false acceptance, payload misuse, and evidence overwrite."""
import json
import tempfile
import unittest
from pathlib import Path
from client import rpc
from experiment import App, run_trial
from verify import verify_trial


class EvidenceTests(unittest.TestCase):
    def test_payload_change_is_rejected_not_deduplicated(self):
        with tempfile.TemporaryDirectory() as root:
            app = App(root)
            try:
                first = app.call('POST', '/write', {'op': 'first', 'key': 'intent-A', 'payload': {'value': 1}})
                second = rpc(app.port, app.trace, 'POST', '/write', {'op': 'second', 'key': 'intent-A', 'payload': {'value': 2}})
                self.assertEqual(second['http_status'], 409)
                self.assertEqual(second['body']['state'], 'rejected')
                self.assertEqual(len(app.call('GET', '/inspect')['effects']), 1)
                self.assertEqual(first['state'], 'committed')
            finally:
                app.close()

    def test_existing_output_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            marker = Path(root) / 'preserve.txt'
            marker.write_text('existing evidence')
            with self.assertRaises(FileExistsError):
                run_trial('no_fault', Path(root), 0.08)
            self.assertEqual(list(Path(root).iterdir()), [marker])
            self.assertEqual(marker.read_text(), 'existing evidence')

    def test_verifier_rejects_missing_current_negative(self):
        with tempfile.TemporaryDirectory() as root:
            trial = Path(root) / 'trial'
            run_trial('live_negative', trial, 0.08)
            rows = [json.loads(x) for x in (trial / 'service.jsonl').read_text().splitlines()]
            for row in rows:
                if row['event'] == 'authoritative_read' and row['operation_state'] == 'pending':
                    row['effect_count'] = 99
            (trial / 'service.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            self.assertIn('live_negative_missing', verify_trial(trial, 'live_negative')['violations'])

    def test_verifier_rejects_commit_after_timeout_in_stale_schedule(self):
        with tempfile.TemporaryDirectory() as root:
            trial = Path(root) / 'trial'
            run_trial('stale_negative', trial, 0.08)
            rows = [json.loads(x) for x in (trial / 'service.jsonl').read_text().splitlines()]
            commit = next(r['mono_ns'] for r in rows if r['event'] == 'effect_committed' and r['op'] == 'original')
            client = [json.loads(x) for x in (trial / 'original.jsonl').read_text().splitlines()]
            for row in client:
                if row['event'] == 'request_timeout':
                    row['mono_ns'] = commit - 1
            (trial / 'original.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in client))
            self.assertIn('pre_timeout_commit_missing', verify_trial(trial, 'stale_negative')['violations'])

    def test_verifier_rejects_missing_handler_completion(self):
        with tempfile.TemporaryDirectory() as root:
            trial = Path(root) / 'trial'
            run_trial('terminal_fence', trial, 0.08)
            rows = [json.loads(x) for x in (trial / 'service.jsonl').read_text().splitlines()]
            rows = [r for r in rows if not (r['event'] == 'handler_finished' and r['op'] == 'original')]
            (trial / 'service.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in rows))
            self.assertIn('undrained_handlers', verify_trial(trial, 'terminal_fence')['violations'])


if __name__ == '__main__': unittest.main()
