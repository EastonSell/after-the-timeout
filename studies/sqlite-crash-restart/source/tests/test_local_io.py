"""Synthetic, in-process I/O checks only. No crash signal or worker launch."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from assess import recover_crash_copy
from io_utils import write_once
from runner import main
from worker import run


class LocalIOTests(unittest.TestCase):
    def test_inprocess_nonfault_write_retains_complete_receipts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'original-start').touch()
            write_once(root / 'original-request.json', {'op': 'original', 'payload': {'item': 'A', 'value': 1}, 'key': 'K'})
            run(root, 'original', 'synthetic-correctness-only', 'none')
            response = json.loads((root / 'original-response.json').read_text())
            self.assertEqual(response, {'op': 'original', 'effect_id': 1, 'state': 'committed', 'status': 200})
            events = [json.loads(line) for line in (root / 'original.jsonl').read_text().splitlines()]
            self.assertEqual([r['event'] for r in events], ['ready', 'request_received', 'before_commit', 'after_commit', 'response_ready', 'worker_finished'])
            self.assertTrue(all(row['nonce'] == 'synthetic-correctness-only' for row in events))
            shutil.copyfile(root / 'effects.sqlite3', root / 'crash-effects.sqlite3')
            before = (root / 'crash-effects.sqlite3').read_bytes()
            state = recover_crash_copy(root)
            self.assertEqual(state['effects'], [{'id': 1, 'op': 'original', 'payload': '{"item":"A","value":1}'}])
            self.assertEqual((root / 'crash-effects.sqlite3').read_bytes(), before)

    def test_exclusive_artifact_write_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'receipt.json'
            write_once(path, {'keep': 1})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_once(path, {'replace': 2})
            self.assertEqual(path.read_bytes(), before)

    def test_runner_cli_refuses_missing_admission_before_output_creation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(['--out', str(root / 'no-output'), '--admission', str(root / 'missing-review.json')])
            self.assertEqual(code, 2)
            self.assertFalse((root / 'no-output').exists())


if __name__ == '__main__':
    unittest.main()
