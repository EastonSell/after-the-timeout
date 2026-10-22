import unittest
from late_commit import Service, execute, prior
from run_experiment import collect, summarize, INPUTS


class LateCommitTests(unittest.TestCase):
    def test_negative_is_not_terminal_absence(self):
        s = Service(idempotent=True)
        with self.assertRaises(prior.UnknownOutcome): s.write('a')
        self.assertEqual(s.status('a'), 'not_committed')
        self.assertEqual(len(s.events), 1)
        s.advance(2)
        self.assertEqual(s.status('a'), 'committed')

    def test_absent_original_has_no_future_event(self):
        s = Service(original_outcome='absent')
        with self.assertRaises(prior.UnknownOutcome): s.write('a')
        s.advance(100)
        self.assertEqual((s.records, s.events), ([], []))

    def test_due_event_precedes_exact_boundary_status(self):
        s = Service(idempotent=True, key_lifetime=1)
        self.assertEqual(execute(s, 'inspect_first', 2), 'committed')
        self.assertEqual([e['event'] for e in s.trace],
                         ['initial_timeout', 'original_completion', 'status'])
        self.assertEqual((s.calls, s.records), (2, ['example-001']))

    def test_cache_expiry_at_late_event_boundary(self):
        for lifetime, count in ((1, 2), (2, 1), (None, 1)):
            s = Service(idempotent=True, key_lifetime=lifetime)
            execute(s, 'blind_retry', 1)  # Retry at 1, original at 2.
            s.drain()
            self.assertEqual(len(s.records), count)

    def test_guard_can_return_before_duplicate(self):
        s = Service(idempotent=True, key_lifetime=1)
        self.assertEqual(execute(s, 'lifetime_guard', 0), 'committed')
        self.assertEqual(len(s.records), 1)
        s.drain()
        self.assertEqual(len(s.records), 2)

    def test_tied_events_use_insertion_order(self):
        s = Service(idempotent=True)
        s.schedule(2, 'b'); s.schedule(2, 'a'); s.schedule(2, 'b')
        s.advance(2)
        self.assertEqual(s.records, ['b', 'a'])
        self.assertEqual([e['operation_id'] for e in s.trace], ['b', 'a', 'b'])
        self.assertEqual([e['deduplicated'] for e in s.trace], [False, False, True])

    def test_suppressed_event_does_not_renew_expiry(self):
        s = Service(idempotent=True, key_lifetime=2)
        s.schedule(0, 'a'); s.schedule(1, 'a'); s.schedule(2, 'a'); s.drain()
        self.assertEqual(s.records, ['a', 'a'])
        self.assertEqual(s.committed_at['a'], 2)

    def test_drain_is_idempotent_and_not_api_calls(self):
        s = Service()
        s.schedule(2, 'a'); s.drain(); s.drain()
        self.assertEqual((s.now, s.calls, s.records), (2, 0, ['a']))

    def test_wait_terminal_handles_absent_and_late(self):
        for outcome in ('absent', 'late'):
            s = Service(original_outcome=outcome, idempotent=True, key_lifetime=1)
            self.assertEqual(execute(s, 'wait_terminal'), 'committed')
            self.assertEqual((s.now, len(s.records), len(s.events)), (2, 1, 0))

    def test_unknown_is_unresolved_after_bound(self):
        s = Service(status_supported=False, idempotent=True)
        self.assertEqual(execute(s, 'wait_terminal'), 'needs_reconciliation')
        self.assertEqual((s.calls, len(s.records)), (2, 1))

    def test_invalid_input_is_rejected(self):
        for value in (-1, True, '2', 1.5):
            s = Service()
            with self.assertRaises(ValueError): s.schedule(value, 'a')
            with self.assertRaises(ValueError): s.advance(value)
            with self.assertRaises(ValueError): execute(s, 'blind_retry', value)
            self.assertEqual((s.calls, s.records, s.events), (0, [], []))
        s = Service(); s.advance(2)
        with self.assertRaises(ValueError): s.schedule(1, 'a')
        with self.assertRaises(ValueError): Service(original_outcome='typo')
        with self.assertRaises(ValueError): execute(Service(), 'typo')

    def test_every_cell_oracle(self):
        rows = collect()
        self.assertEqual(len(rows), 128)
        self.assertEqual(len({tuple(r[k] for k in INPUTS) for r in rows}), 128)
        for r in rows:
            late, finite, d, supported, p = (r['original_outcome']=='late',
                r['key_lifetime']==1, r['delay'], r['status_supported'], r['policy'])
            positive = late and supported and d >= 2
            retry = p == 'blind_retry' or (p == 'inspect_first' and not positive) or (
                p == 'lifetime_guard' and not positive and (not finite or d == 0))
            duplicate = late and finite and retry and d in (0, 1, 3)
            unresolved = (p == 'wait_terminal' and not supported) or (
                p == 'lifetime_guard' and finite and d >= 1 and not positive)
            self.assertEqual((r['duplicates'],r['unresolved'],r['deferred_duplicates']),
                             (int(duplicate),int(unresolved),int(duplicate and d < 2)), r)
            self.assertEqual(r['runs'], 1)
        summary = summarize(rows)
        for p, duplicates, unresolved, deferred in (
                ('blind_retry',6,0,4), ('inspect_first',5,0,4),
                ('lifetime_guard',2,10,2), ('wait_terminal',0,16,0)):
            self.assertEqual([summary[p][k] for k in ('runs','duplicates','unresolved','deferred_duplicates')],
                             [32,duplicates,unresolved,deferred])


if __name__ == '__main__': unittest.main()
