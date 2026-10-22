import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from demo import ROOT, REVISION, fixture, demonstrate
from validate_checkpoint import validate
SCRIPT = ROOT/'skills/checkpoint-handoff/scripts/validate_checkpoint.py'


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)

    def check(self):
        return validate(self.data, self.root, REVISION)

    def test_consistent_claims_do_not_grant_approval(self):
        report = self.check()
        self.assertEqual(report['handoff_state'], 'ready_for_review')
        self.assertEqual(report['publication_evidence'], 'recorded_complete')
        self.assertFalse(report['approval_granted'])

    def test_missing_artifact(self):
        (self.root/'input.txt').unlink()
        self.assertEqual(self.check()['handoff_state'], 'invalid')

    def test_hash_mismatch(self):
        (self.root/'answer.txt').write_text('edited')
        self.assertIn('answer.txt: hash mismatch', self.check()['errors'])

    def test_current_revision_mismatch(self):
        self.assertFalse(validate(self.data, self.root, 'b'*40)['integrity_valid'])

    def test_reproduction_commit_mismatch(self):
        self.data['reproduction']['commit'] = 'b'*40
        self.assertFalse(self.check()['integrity_valid'])

    def test_failed_and_unrun_checks_block(self):
        for result in ('failed', 'not_run'):
            self.data['reproduction']['result'] = result
            self.assertEqual(self.check()['handoff_state'], 'blocked')

    def test_unresolved_and_denied_operations_block(self):
        for state in ('pending', 'uncertain', 'denied'):
            self.data['operations'] = [dict(id='write-1', state=state, next_observation='Inspect exact operation.')]
            report = self.check()
            self.assertTrue(report['integrity_valid'])
            self.assertEqual(report['handoff_state'], 'blocked')

    def test_duplicate_operation_ids_invalid(self):
        item = dict(id='write-1', state='completed', next_observation='None needed.')
        self.data['operations'] = [item, item.copy()]
        self.assertFalse(self.check()['integrity_valid'])

    def test_partial_and_missing_publication(self):
        del self.data['publication']['receipts'][0]['artifacts']['input.txt']
        self.assertEqual(self.check()['publication_evidence'], 'recorded_partial')
        self.assertEqual(self.check()['handoff_state'], 'blocked')
        self.data['publication']['receipts'] = []
        self.assertEqual(self.check()['publication_evidence'], 'not_recorded')
        self.assertEqual(self.check()['handoff_state'], 'blocked')

    def test_local_only_checkpoint(self):
        self.data['publication'] = dict(expected_destination=None, receipts=[])
        self.assertEqual(self.check()['handoff_state'], 'ready_for_review')

    def test_multiple_receipts_cover_exact_manifest(self):
        receipt = self.data['publication']['receipts'][0]
        second = copy.deepcopy(receipt)
        del receipt['artifacts']['input.txt']; del second['artifacts']['answer.txt']
        self.data['publication']['receipts'].append(second)
        self.assertEqual(self.check()['publication_evidence'], 'recorded_complete')

    def test_receipt_mismatch_invalid(self):
        for key, value in (('destination','wrong'), ('commit','b'*40),
                           ('artifacts', {'extra.txt':'0'*64})):
            with self.subTest(key=key):
                self.data = fixture(self.root)
                self.data['publication']['receipts'][0][key] = value
                self.assertFalse(self.check()['integrity_valid'])
        self.data = fixture(self.root)
        self.data['publication']['receipts'][0]['artifacts']['input.txt'] = '0'*64
        self.assertFalse(self.check()['integrity_valid'])

    def test_unsafe_paths_rejected(self):
        for name in ('../secret', '/absolute', './answer.txt', 'a//b', 'a\\b', 'C:/file'):
            self.data['artifacts'] = {name:'0'*64}
            self.assertFalse(self.check()['integrity_valid'], name)

    def test_symlink_file_and_directory_rejected(self):
        (self.root/'linked').symlink_to(self.root/'answer.txt')
        self.data['artifacts'] = {'linked':self.data['artifacts']['answer.txt']}
        self.assertFalse(self.check()['integrity_valid'])
        (self.root/'linked-dir').symlink_to(self.root, target_is_directory=True)
        self.data['artifacts'] = {'linked-dir/answer.txt':'0'*64}
        self.assertFalse(self.check()['integrity_valid'])

    def test_unknown_fields_cannot_claim_authority(self):
        self.data['approval_granted'] = True
        self.assertFalse(self.check()['integrity_valid'])
        self.assertFalse(self.check()['approval_granted'])

    def test_malformed_values_return_invalid(self):
        for value in (None, [], {}, True, 1):
            self.assertEqual(validate(value, self.root, REVISION)['handoff_state'], 'invalid')
        for commit in ('main', 'a'*39, 'A'*40, None):
            self.assertFalse(validate(self.data, self.root, commit)['integrity_valid'])
        self.data['schema_version'] = True
        self.assertFalse(self.check()['integrity_valid'])

    def cli(self, text):
        (self.root/'checkpoint.json').write_text(text)
        return subprocess.run([sys.executable, str(SCRIPT), 'checkpoint.json', '--workspace',
                               str(self.root), '--current-commit', REVISION],
                              capture_output=True, text=True, check=False)

    def test_cli_exit_codes_and_read_only_behavior(self):
        # A command that would create a marker must remain inert.
        self.data['reproduction']['argv'] = [sys.executable, '-c',
            "from pathlib import Path; Path('EXECUTED').write_text('bad')"]
        before = {p.name:p.read_bytes() for p in self.root.iterdir()}
        result = self.cli(json.dumps(self.data))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.root/'EXECUTED').exists())
        self.assertFalse((Path.cwd()/'EXECUTED').exists())
        self.assertEqual(before, {p.name:p.read_bytes() for p in self.root.iterdir() if p.name!='checkpoint.json'})
        self.data['publication']['receipts'] = []
        self.assertEqual(self.cli(json.dumps(self.data)).returncode, 1)
        self.assertEqual(self.cli('{').returncode, 2)

    def test_duplicate_json_keys_are_not_silently_overwritten(self):
        result = self.cli('{"schema_version":1,"schema_version":1}')
        self.assertEqual(result.returncode, 2)
        self.assertIn('Duplicate JSON object key', result.stdout)

    def test_demo_classifies_all_failures(self):
        cases = demonstrate()['cases']
        self.assertEqual(len(cases), 7)
        self.assertEqual(cases['partial_publication']['handoff_state'], 'blocked')
        self.assertEqual(cases['uncertain_operation']['handoff_state'], 'blocked')
        for name in ('missing_artifact','hash_mismatch','current_revision_changed','wrong_receipt_destination'):
            self.assertEqual(cases[name]['handoff_state'], 'invalid')
        self.assertTrue(all(not r['approval_granted'] for r in cases.values()))


if __name__ == '__main__': unittest.main()
