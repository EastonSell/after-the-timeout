"""Retained-trace regression fixtures only; never calls model.simulate()."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
import unittest

from policy_replay import validate_policy, choose
from combined_check import validate_combined

ROOT = Path(__file__).resolve().parents[1]
STUDY = ROOT
spec = importlib.util.spec_from_file_location('original_dynamics_checker', STUDY / 'source/checker.py')
original_checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original_checker)
SAVED_NAMES = ('false_P5_completion_upper_bound', 'unsafe_naive_inspection',
               'unsafe_blind_keyed', 'post_return_duplicate')


def read(name):
    return json.loads((STUDY / f'results-v1/counterexamples/{name}.json').read_text())


class PolicyAttributionTests(unittest.TestCase):
    def test_four_retained_traces_pass_both_distinct_audits(self):
        for name in SAVED_NAMES:
            with self.subTest(name=name):
                row = read(name)
                original_checker.validate(row)
                self.assertGreater(validate_policy(row)['decisions_checked'], 0)

    def test_combined_entry_accepts_four_retained_traces(self):
        for name in SAVED_NAMES:
            with self.subTest(name=name):
                result = validate_combined(read(name))
                self.assertTrue(result['dynamics_validated'])

    def test_removed_initial_wait_requires_dynamics_before_attribution(self):
        row = read('false_P5_completion_upper_bound')
        first_wait = next(i for i, e in enumerate(row['hidden_trace'])
                          if e['kind'] == 'action' and e['action']['kind'] == 'wait')
        del row['hidden_trace'][first_wait]
        # The standalone audit checks decisions present in an assumed-valid
        # timeline. Its acceptance here demonstrates the declared precondition.
        self.assertEqual(validate_policy(row)['decisions_checked'], 2)
        with self.assertRaisesRegex(ValueError, 'missing required semantic event'):
            validate_combined(row)

    def test_combined_entry_rejects_policy_relabeling_after_valid_dynamics(self):
        row = read('unsafe_naive_inspection')
        row['policy'] = 'blind_keyed'
        with self.assertRaisesRegex(ValueError, 'expected'):
            validate_combined(row)

    def test_relabeling_valid_dynamics_is_detected(self):
        # Explicitly documented scope gap, not an allegation of corrupted data.
        row = read('unsafe_naive_inspection')
        row['policy'] = 'blind_keyed'
        original_checker.validate(row)  # Expected: dynamics still match.
        with self.assertRaisesRegex(ValueError, 'expected'):
            validate_policy(row)

    def test_unknown_policy_rejected_even_on_valid_trace(self):
        row = read('unsafe_naive_inspection')
        row['policy'] = 'unregistered'
        with self.assertRaisesRegex(ValueError, 'unregistered'):
            validate_policy(row)

    def test_wrong_decision_time_is_detected(self):
        row = read('false_P5_completion_upper_bound')
        first = next(e for e in row['hidden_trace'] if e['kind'] == 'action')
        first['t'] = row['case']['deadline'] + 1
        with self.assertRaisesRegex(ValueError, 'expected'):
            validate_policy(row)

    def test_received_evidence_cannot_be_silently_omitted(self):
        row = read('false_P5_completion_upper_bound')
        row['public_trace'] = []
        with self.assertRaisesRegex(ValueError, 'missing public'):
            validate_policy(row)

    def test_evaluator_only_fields_do_not_drive_action_replay(self):
        row = read('false_P5_completion_upper_bound')
        expected = validate_policy(row)
        row['case']['originals'] = ['never', 'late']
        row['case']['retry_outcome'] = 'reject'
        row['metrics'] = {'not_policy_input': True}
        self.assertEqual(validate_policy(row), expected)

    def test_hand_written_six_loss_initial_action_boundary(self):
        # A NEW contract-only fixture, not a new run or replacement old evidence.
        contract = dict(scope='item', strategy='reserve', ttl=20,
                        observation='certified', lag=2, original_terminal=4,
                        budget=3, deadline=4, horizon=15)
        horizon = choose('horizon_aware', contract, 1, set(), 0, 0, 0, [])
        fallback = choose('capability_fallback', contract, 1, set(), 0, 0, 0, [])
        self.assertEqual(horizon, {'kind': 'stop', 'reason': 'terminal snapshot exceeds action deadline'})
        self.assertEqual(fallback['kind'], 'write')
        self.assertTrue(fallback['keyed'])


if __name__ == '__main__':
    unittest.main()
