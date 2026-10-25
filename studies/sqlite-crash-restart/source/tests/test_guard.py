"""The gate must fail closed before creating output or launching processes."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from guard import check_admission, reserve_output


class GuardTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'source'
        self.root.mkdir()
        (self.root / 'source.txt').write_text('frozen')
        spec = {'files': {'source.txt': hashlib.sha256(b'frozen').hexdigest()}, 'study': 'sqlite-crash-restart-v1'}
        self.freeze = json.dumps(spec).encode()
        (self.root / 'PRE_DATA_FREEZE.json').write_bytes(self.freeze)
        self.approval = Path(self.temp.name) / 'approval.json'
        self.admit = {'phase': 'PRE-DATA', 'decision': 'ADMIT', 'reviewer': 'independent-fixture-reviewer',
                      'freeze_sha256': hashlib.sha256(self.freeze).hexdigest()}

    def test_missing_approval_is_rejected(self):
        with self.assertRaises((ValueError, FileNotFoundError)):
            check_admission(self.root, self.approval)

    def test_nonadmission_is_rejected(self):
        self.admit['decision'] = 'HOLD'
        self.approval.write_text(json.dumps(self.admit))
        with self.assertRaises(ValueError):
            check_admission(self.root, self.approval)

    def test_wrong_frozen_identity_is_rejected(self):
        self.admit['freeze_sha256'] = '0' * 64
        self.approval.write_text(json.dumps(self.admit))
        with self.assertRaises(ValueError):
            check_admission(self.root, self.approval)

    def test_mutated_source_is_rejected(self):
        self.approval.write_text(json.dumps(self.admit))
        (self.root / 'source.txt').write_text('changed')
        with self.assertRaises(ValueError):
            check_admission(self.root, self.approval)

    def test_correct_identity_is_accepted_without_launch(self):
        self.approval.write_text(json.dumps(self.admit))
        self.assertEqual(check_admission(self.root, self.approval).get('decision'), 'ADMIT')

    def test_existing_and_source_descendant_output_are_rejected(self):
        with self.assertRaises(ValueError):
            reserve_output(self.root, self.root)
        with self.assertRaises(ValueError):
            reserve_output(self.root / 'new', self.root)

    def test_new_output_is_created_exclusively(self):
        out = Path(self.temp.name) / 'new-output'
        reserve_output(out, self.root)
        self.assertTrue(out.is_dir())
        with self.assertRaises(ValueError):
            reserve_output(out, self.root)


if __name__ == '__main__':
    unittest.main()
