"""Adversarial tests against retained rows, never a simulator."""
import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import completeness_check as check

HERE = Path(__file__).resolve().parent
STUDY = Path(os.environ.get('RECOVERY_STUDY_ROOT', str(HERE.parent)))


class CompletenessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original = json.loads((HERE / 'fixture.json').read_text())
        cls.verifiers = check.load_verifiers(STUDY)

    def setUp(self):
        self.data = copy.deepcopy(self.original)

    def audit(self):
        d = self.data
        return check.audit_rows(iter(d['rows']), d['cases'], d['policies'],
                                d['group_summaries'], d['summary'], *self.verifiers)

    def test_accepts_complete_retained_fixture(self):
        result = self.audit()
        self.assertTrue(result['passed'])
        self.assertEqual(result['cases'], 2)
        self.assertEqual(result['groups'], 8)
        self.assertEqual(result['paths'], 14)

    def test_rejects_missing_group(self):
        self.data['rows'] = [r for r in self.data['rows']
                            if not (r['case']['id'] == 'exhaustive-0000'
                                    and r['policy'] == 'naive_inspection')]
        with self.assertRaisesRegex(ValueError, 'missing.*group'):
            self.audit()

    def test_rejects_missing_case(self):
        self.data['rows'] = [r for r in self.data['rows']
                            if r['case']['id'] != 'exhaustive-0000']
        with self.assertRaisesRegex(ValueError, 'missing.*group'):
            self.audit()

    def test_rejects_contiguous_duplicate_terminal_trace(self):
        self.data['rows'].insert(1, copy.deepcopy(self.data['rows'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate.*trace'):
            self.audit()

    def test_rejects_noncontiguous_repeated_group(self):
        self.data['rows'].append(copy.deepcopy(self.data['rows'][0]))
        with self.assertRaisesRegex(ValueError, 'repeated group'):
            self.audit()

    def test_accepts_reordered_complete_groups_and_paths(self):
        # Membership is semantic, not an accidental dependency on file order.
        groups = {}
        for row in self.data['rows']:
            groups.setdefault((row['case']['id'], row['policy']), []).append(row)
        self.data['rows'] = [r for group in reversed(list(groups.values())) for r in reversed(group)]
        self.assertEqual(self.audit()['paths'], 14)

    def test_rejects_same_trace_with_new_path_index(self):
        self.data['rows'][2]['hidden_trace'] = copy.deepcopy(self.data['rows'][1]['hidden_trace'])
        with self.assertRaisesRegex(ValueError, 'duplicate.*trace'):
            self.audit()

    def test_rejects_dynamics_valid_policy_relabel(self):
        # The historical dynamics checker alone accepts this label substitution.
        d = self.data
        d['cases'] = [d['cases'][0]]
        d['policies'] = ['naive_inspection']
        d['rows'] = [r for r in d['rows'] if r['case']['id'] == 'exhaustive-0000'
                     and r['policy'] == 'blind_keyed']
        d['group_summaries'] = [g for g in d['group_summaries']
                                if g['case_id'] == 'exhaustive-0000' and g['policy'] == 'blind_keyed']
        for row in d['rows']:
            row['policy'] = 'naive_inspection'
        d['group_summaries'][0]['policy'] = 'naive_inspection'
        self.assertEqual(self.verifiers[0].validate_group(d['rows']), d['group_summaries'][0]['coverage'])
        with self.assertRaisesRegex(ValueError, 'expected.*got'):
            self.audit()

    def test_rejects_case_label_changed_without_contract(self):
        self.data['rows'][0]['case']['id'] = 'expiry_late_original-0589'
        with self.assertRaisesRegex(ValueError, 'case.*manifest'):
            self.audit()

    def test_rejects_changed_case_contract(self):
        self.data['rows'][0]['case']['ttl'] += 1
        with self.assertRaisesRegex(ValueError, 'case.*manifest'):
            self.audit()

    def test_rejects_numeric_boolean_case_alias(self):
        # Python normally considers False == 0; exact case identity must not.
        self.data['rows'][0]['case']['ttl'] = False
        with self.assertRaisesRegex(ValueError, 'case.*manifest'):
            self.audit()

    def test_rejects_unknown_case(self):
        self.data['rows'][0]['case']['id'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'case.*manifest'):
            self.audit()

    def test_rejects_unknown_policy(self):
        self.data['rows'][0]['policy'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'unexpected.*group'):
            self.audit()

    def test_rejects_duplicate_manifest_case(self):
        self.data['cases'].append(copy.deepcopy(self.data['cases'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate.*case'):
            self.audit()

    def test_rejects_duplicate_policy_registration(self):
        self.data['policies'].append(self.data['policies'][0])
        with self.assertRaisesRegex(ValueError, 'duplicate.*polic'):
            self.audit()

    def test_rejects_duplicate_group_certificate(self):
        self.data['group_summaries'].append(copy.deepcopy(self.data['group_summaries'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate.*certificate'):
            self.audit()

    def test_rejects_missing_group_certificate(self):
        self.data['group_summaries'].pop()
        with self.assertRaisesRegex(ValueError, 'certificate.*membership'):
            self.audit()

    def test_rejects_extra_group_certificate(self):
        extra = copy.deepcopy(self.data['group_summaries'][0])
        extra['policy'] = 'unknown'
        self.data['group_summaries'].append(extra)
        with self.assertRaisesRegex(ValueError, 'certificate.*membership'):
            self.audit()

    def test_rejects_missing_scheduler_path(self):
        self.data['rows'].pop(1)  # blind_keyed has three distinct retained paths
        with self.assertRaisesRegex(ValueError, 'path|coverage'):
            self.audit()

    def test_rejects_duplicate_path_index(self):
        self.data['rows'][2]['path_index'] = self.data['rows'][1]['path_index']
        with self.assertRaisesRegex(ValueError, 'path indices'):
            self.audit()

    def test_rejects_boolean_path_index(self):
        self.data['rows'][0]['path_index'] = False
        with self.assertRaisesRegex(ValueError, 'path indices'):
            self.audit()

    def test_rejects_wrong_scheduler_path_count(self):
        self.data['rows'][0]['scheduler_paths'] += 1
        with self.assertRaisesRegex(ValueError, 'scheduler_paths'):
            self.audit()

    def test_rejects_wrong_state_counter(self):
        self.data['rows'][0]['states_explored'] += 1
        with self.assertRaisesRegex(ValueError, 'states_explored'):
            self.audit()

    def test_rejects_wrong_coverage_certificate(self):
        self.data['group_summaries'][0]['coverage']['coverage_hash'] = '0' * 64
        with self.assertRaisesRegex(ValueError, 'coverage certificate'):
            self.audit()

    def test_rejects_wrong_group_metric(self):
        self.data['group_summaries'][0]['actual_complete_paths'] = 0
        with self.assertRaisesRegex(ValueError, 'group metric'):
            self.audit()

    def test_rejects_wrong_family_aggregate(self):
        self.data['summary']['totals']['exhaustive|naive_inspection']['paths'] += 1
        with self.assertRaisesRegex(ValueError, 'aggregate'):
            self.audit()

    def test_rejects_wrong_global_group_count(self):
        self.data['summary']['groups'] += 1
        with self.assertRaisesRegex(ValueError, 'aggregate'):
            self.audit()

    def test_rejects_empty_input(self):
        self.data['rows'] = []
        with self.assertRaisesRegex(ValueError, 'missing.*group'):
            self.audit()

    def test_rejects_dynamics_mutation(self):
        self.data['rows'][0]['metrics']['actual_complete'] = False
        with self.assertRaisesRegex(ValueError, 'metric mismatch'):
            self.audit()

    def test_rejects_duplicate_json_keys(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            check.parse_json('{"policy":"blind_keyed","policy":"horizon_aware"}')

    def test_rejects_nonfinite_json(self):
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            check.parse_json('{"value":NaN}')

    def test_reads_plain_and_gzip_jsonl(self):
        import gzip
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / 'rows.jsonl'
            zipped = Path(tmp) / 'rows.jsonl.gz'
            text = ''.join(json.dumps(r) + '\n' for r in self.data['rows'])
            plain.write_text(text, encoding='utf-8')
            with gzip.open(zipped, 'wt', encoding='utf-8') as f:
                f.write(text)
            self.assertEqual(list(check.saved_rows(plain)), self.data['rows'])
            self.assertEqual(list(check.saved_rows(zipped)), self.data['rows'])

    def test_rejects_blank_or_truncated_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'rows.jsonl'
            for text in ('\n', '{"case":'):
                path.write_text(text)
                with self.assertRaises(ValueError):
                    list(check.saved_rows(path))

    def test_rejects_altered_verifier_before_executing_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for relative in check.VERIFIER_SHA256:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(STUDY / relative, target)
            for relative in check.VERIFIER_SHA256:
                target = root / relative
                original = target.read_bytes()
                target.write_bytes(original + b'\nraise RuntimeError("must never execute")\n')
                with self.assertRaisesRegex(ValueError, 'pinned bytes mismatch'):
                    check.load_verifiers(root)
                target.write_bytes(original)

    def test_rejects_modified_expected_manifest_before_processing(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'cases.json').write_text('[]')
            with self.assertRaisesRegex(ValueError, 'pinned.*cases.json'):
                check.load_pinned_expectations(Path(tmp))


if __name__ == '__main__':
    unittest.main()
