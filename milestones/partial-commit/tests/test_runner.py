import hashlib
import tempfile
import unittest
from pathlib import Path
from run_experiment import expected_cases, verify_freeze


class RunnerContracts(unittest.TestCase):
    def test_explicit_design_size_and_uniqueness(self):
        cases = expected_cases()
        self.assertEqual(len(cases), 256)
        self.assertEqual(len({(tuple(c['initial_committed']), c['status_mode'], c['per_item_idempotency'], c['policy']) for c in cases}), 256)

    def test_freeze_detects_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'fixture.txt').write_bytes(b'original')
            (root / 'FREEZE.sha256').write_text(hashlib.sha256(b'original').hexdigest() + '  fixture.txt\n')
            self.assertEqual(len(verify_freeze(root)), 64)
            (root / 'fixture.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Frozen input changed'):
                verify_freeze(root)

class OutputSafety(unittest.TestCase):
    def prepare(self, root):
        import json
        root.joinpath('allowed_cases.json').write_text(json.dumps([{'initial_committed': [], 'status_mode': 'fresh', 'per_item_idempotency': False, 'policy': 'blind_batch'}]))
        return json.loads(root.joinpath('allowed_cases.json').read_text())

    def test_falsified_prediction_keeps_evidence_before_failure(self):
        import json
        from unittest.mock import patch
        from run_experiment import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = self.prepare(root)
            row = dict(policy='blind_batch', per_item_idempotency=False, status_mode='fresh',
                       reported_complete=True, true_complete=False, exact_once_complete=False,
                       extra_side_effects=0, unresolved_count=0, unresolved_items=[],
                       duplicate_items=[], api_calls=2)
            with patch('run_experiment.verify_freeze', return_value='synthetic-test'), patch('run_experiment.expected_cases', return_value=cases), patch('run_experiment.execute', return_value=row):
                with self.assertRaises(AssertionError):
                    run(root)
            result = json.loads((root / 'results/experiment.json').read_text())
            self.assertEqual(result['rows'], [row])
            self.assertFalse(result['predictions']['reported_complete_is_true'])
            self.assertEqual(json.loads((root / 'results/status.json').read_text())['state'], 'prediction_failed')
            self.assertEqual(len((root / 'results/rows.jsonl').read_text().splitlines()), 1)

    def test_preexisting_output_never_executes_or_overwrites(self):
        from unittest.mock import patch
        from run_experiment import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = self.prepare(root)
            output = root / 'results'
            output.mkdir()
            (output / 'experiment.json').write_text('prior')
            with patch('run_experiment.verify_freeze', return_value='synthetic-test'), patch('run_experiment.expected_cases', return_value=cases), patch('run_experiment.execute') as execute:
                with self.assertRaises(FileExistsError):
                    run(root)
                execute.assert_not_called()
            self.assertEqual((output / 'experiment.json').read_text(), 'prior')

    def test_interruption_retains_started_marker(self):
        import json
        from unittest.mock import patch
        from run_experiment import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = self.prepare(root)
            with patch('run_experiment.verify_freeze', return_value='synthetic-test'), patch('run_experiment.expected_cases', return_value=cases), patch('run_experiment.execute', side_effect=KeyboardInterrupt):
                with self.assertRaises(KeyboardInterrupt):
                    run(root)
            self.assertEqual(json.loads((root / 'results/status.json').read_text())['state'], 'running')
            self.assertFalse((root / 'results/experiment.json').exists())

    def test_interruption_preserves_completed_rows(self):
        import json
        from unittest.mock import patch
        from run_experiment import run
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = self.prepare(root) * 2
            (root / 'allowed_cases.json').write_text(json.dumps(cases))
            row = {'synthetic_completed_record': 1}
            with patch('run_experiment.verify_freeze', return_value='synthetic-test'), patch('run_experiment.expected_cases', return_value=cases), patch('run_experiment.execute', side_effect=[row, KeyboardInterrupt]):
                with self.assertRaises(KeyboardInterrupt):
                    run(root)
            self.assertEqual([json.loads(line) for line in (root / 'results/rows.jsonl').read_text().splitlines()], [row])
            self.assertFalse((root / 'results/experiment.json').exists())
