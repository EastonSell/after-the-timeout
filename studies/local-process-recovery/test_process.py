"""Literal process outcomes: a missing or extra real database write breaks these tests."""
import tempfile
import unittest
from pathlib import Path
from experiment import run_trial


class ProcessRecoveryTests(unittest.TestCase):
    def check_case(self, scenario, expected):
        with tempfile.TemporaryDirectory() as root:
            result = run_trial(scenario, Path(root) / 'trial', 0.08)
            self.assertEqual(result['effect_count'], expected)
            self.assertEqual(result['violations'], [])
            self.assertTrue(result['all_handlers_finished'])
            self.assertNotEqual(result['server_pid'], result['original_client_pid'])

    def test_no_fault_has_one_effect(self): self.check_case('no_fault', 1)
    def test_live_negative_can_duplicate(self): self.check_case('live_negative', 2)
    def test_stale_negative_can_duplicate(self): self.check_case('stale_negative', 2)
    def test_identical_key_suppresses_late_original(self): self.check_case('same_key', 1)
    def test_terminal_fence_blocks_late_original(self): self.check_case('terminal_fence', 1)
    def test_terminal_flag_does_not_refresh_cache(self): self.check_case('terminal_with_stale_read', 2)
    def test_terminal_current_read_stops_retry(self): self.check_case('terminal_with_authoritative_read', 1)
    def test_original_fence_does_not_fence_other_recoverers(self): self.check_case('concurrent_recoverers', 2)


if __name__ == '__main__': unittest.main()
