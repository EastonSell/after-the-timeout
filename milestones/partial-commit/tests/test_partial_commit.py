import unittest
from partial_commit import Observation, Record, Service, decide, execute, make_observation


class Contracts(unittest.TestCase):
    def test_fresh_subset(self):
        obs = make_observation(('a', 'c'), 'fresh', False)
        self.assertEqual(obs.records, (Record('a', 'committed', True), Record('b', 'absent', True), Record('c', 'committed', True)))

    def test_incomplete_is_not_negative(self):
        obs = make_observation(('a', 'b'), 'incomplete', False)
        self.assertEqual(decide('evidence_only', obs), ((), ('b', 'c')))
        self.assertEqual(decide('missing_is_absent', obs), (('b', 'c'), ()))

    def test_stale_negative_is_not_authoritative(self):
        obs = make_observation(('b',), 'stale_negative', False)
        self.assertEqual(decide('capability_guard', obs), ((), ('a', 'b', 'c')))

    def test_supported_keys_resolve_unknown(self):
        obs = make_observation(('b',), 'unsupported', True)
        self.assertEqual(decide('capability_guard', obs), (('a', 'b', 'c'), ()))

    def test_fresh_negative_safe_without_keys(self):
        row = execute(('a', 'c'), 'fresh', False, 'capability_guard')
        self.assertEqual(row['retry_items'], ['b'])
        self.assertTrue(row['exact_once_complete'])
        self.assertEqual(row['api_calls'], 3)

    def test_duplicate_completion_not_exact_once(self):
        row = execute(('a', 'c'), 'unsupported', False, 'blind_batch')
        self.assertTrue(row['true_complete'])
        self.assertTrue(row['reported_complete'])
        self.assertFalse(row['exact_once_complete'])
        self.assertEqual(row['extra_side_effects'], 2)
        self.assertEqual(row['api_calls'], 2)

    def test_keys_deduplicate_partial_replay(self):
        row = execute(('a', 'c'), 'unsupported', True, 'blind_batch')
        self.assertEqual(row['commit_counts'], {'a': 1, 'b': 1, 'c': 1})

    def test_unresolved_can_hide_success(self):
        row = execute(('a', 'b', 'c'), 'unsupported', False, 'evidence_only')
        self.assertTrue(row['true_complete'])
        self.assertFalse(row['reported_complete'])
        self.assertEqual(row['unresolved_items'], ['a', 'b', 'c'])
        self.assertEqual(row['api_calls'], 2)

    def test_unresolved_can_hide_missing_work(self):
        row = execute((), 'stale_negative', False, 'capability_guard')
        self.assertFalse(row['true_complete'])
        self.assertEqual(row['extra_side_effects'], 0)

    def test_no_retry_for_verified_complete(self):
        row = execute(('a', 'b', 'c'), 'fresh', False, 'evidence_only')
        self.assertTrue(row['reported_complete'])
        self.assertEqual(row['api_calls'], 2)
        self.assertEqual(row['retry_items'], [])

    def test_observation_has_no_hidden_counts(self):
        obs = make_observation(('a',), 'unsupported', False)
        self.assertEqual(set(obs.__dataclass_fields__), {'records', 'status_supported', 'per_item_idempotency'})
        with self.assertRaises(Exception):
            obs.per_item_idempotency = True

    def test_identical_evidence_indistinguishable(self):
        for policy in ('missing_is_absent', 'evidence_only', 'capability_guard'):
            left = make_observation((), 'stale_negative', False)
            right = make_observation(('a', 'b', 'c'), 'stale_negative', False)
            self.assertEqual(left, right)
            self.assertEqual(decide(policy, left), decide(policy, right))

    def test_invalid_inputs_rejected(self):
        for args in [(('d',), 'fresh', False), (('a', 'a'), 'fresh', False), ((), 'other', False), ((), 'fresh', 'yes')]:
            with self.assertRaises(ValueError):
                make_observation(*args)
        with self.assertRaises(ValueError):
            decide('other', Observation((), False, False))

    def test_service_rejects_unknown_before_writing(self):
        service = Service(('a',), False)
        with self.assertRaises(ValueError):
            service.retry(('b', 'd'))
        self.assertEqual(service.counts, {'a': 1, 'b': 0, 'c': 0})


if __name__ == '__main__':
    unittest.main()

class EvidenceAdversaries(unittest.TestCase):
    def test_omitted_items_do_not_leak(self):
        left = make_observation(('a',), 'incomplete', False)
        right = make_observation(('a', 'b', 'c'), 'incomplete', False)
        self.assertEqual(left, right)
        for policy in ('evidence_only', 'capability_guard', 'missing_is_absent'):
            self.assertEqual(decide(policy, left), decide(policy, right))

    def test_unsupported_does_not_leak(self):
        self.assertEqual(make_observation((), 'unsupported', True),
                         make_observation(('a', 'b', 'c'), 'unsupported', True))

    def test_unknown_positive_is_not_verified(self):
        obs = Observation((Record('a', 'committed', False),), True, False)
        self.assertEqual(decide('evidence_only', obs), ((), ('a', 'b', 'c')))
