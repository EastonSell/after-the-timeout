import unittest
from key_lifetime import Service, execute, baseline, UnknownOutcome, POLICIES
from run_experiment import collect, summarize


class KeyLifetimeTests(unittest.TestCase):
    def test_before_at_after_boundary(self):
        for delay, expected in ((0, 1), (1, 2), (2, 2)):
            with self.subTest(delay=delay):
                s = Service('after', False, True, key_lifetime=1)
                execute(s, 'blind_retry', delay)
                self.assertEqual(len(s.records), expected)

    def test_cache_hit_does_not_renew(self):
        s = Service(idempotent=True, key_lifetime=2)
        s.write('a'); s.advance(1); s.write('a'); s.advance(1); s.write('a')
        self.assertEqual(s.records, ['a', 'a'])
        self.assertEqual(s.committed_at['a'], 2)

    def test_expiry_does_not_erase_commit_history(self):
        s = Service(idempotent=True, key_lifetime=1)
        s.write('a'); s.advance(1)
        self.assertEqual(s.status('a'), 'committed')
        self.assertEqual(s.records, ['a'])

    def test_keys_are_operation_scoped(self):
        s = Service(idempotent=True, key_lifetime=2)
        s.write('a'); s.advance(1); s.write('b'); s.advance(1)
        s.write('a'); s.write('b')
        self.assertEqual(s.records, ['a', 'b', 'a'])

    def test_before_timeout_does_not_cache(self):
        s = Service('before', idempotent=True, key_lifetime=1)
        with self.assertRaises(UnknownOutcome):
            s.write('a')
        self.assertEqual(s.committed_at, {})
        s.advance(3); s.write('a')
        self.assertEqual(s.records, ['a'])

    def test_zero_lifetime_has_no_retention(self):
        s = Service(idempotent=True, key_lifetime=0)
        s.write('a'); s.write('a')
        self.assertEqual(s.records, ['a', 'a'])

    def test_guard_cannot_use_hidden_state(self):
        for fault, commits in (('before', 0), ('after', 1)):
            s = Service(fault, False, True, key_lifetime=1)
            self.assertEqual(execute(s, 'lifetime_guard', 1), 'needs_reconciliation')
            self.assertEqual((len(s.records), s.calls), (commits, 2))

    def test_positive_status_resolves_after_expiry(self):
        s = Service('after', True, True, key_lifetime=1)
        self.assertEqual(execute(s, 'lifetime_guard', 20), 'committed')
        self.assertEqual((len(s.records), s.calls), (1, 2))

    def test_unlimited_matches_published_model(self):
        for fault in ('none', 'before', 'after', 'denied'):
            for status in (False, True):
                for stale in (0, 1):
                    for idem in (False, True):
                        for policy in ('blind_retry', 'inspect_first'):
                            a = baseline.Service(fault, status, idem, status_staleness=stale)
                            b = Service(fault, status, idem, status_staleness=stale)
                            self.assertEqual(baseline.execute(a, policy), execute(b, policy, 99))
                            self.assertEqual((a.calls, a.records), (b.calls, b.records))

    def test_invalid_values_fail_before_effects(self):
        for value in (-1, True, 1.2, '1'):
            with self.assertRaises(ValueError): Service(key_lifetime=value)
            with self.assertRaises(ValueError): Service(now=value)
            s = Service()
            with self.assertRaises(ValueError): execute(s, 'blind_retry', value)
            self.assertEqual(s.calls, 0)
        with self.assertRaises(ValueError): execute(Service(), 'typo')

    def test_full_grid_independent_cell_oracle(self):
        rows = collect()
        self.assertEqual(len(rows), 216)
        self.assertEqual(len({tuple(r[k] for k in ('fault','status_mode','key_lifetime','delay','policy')) for r in rows}), 216)
        for r in rows:
            uncertain = r['fault'] in ('before', 'after')
            expired = r['key_lifetime'] == 1 and r['delay'] >= 1
            positive = r['fault'] == 'after' and r['status_mode'] == 'fresh'
            guarded = r['policy'] == 'lifetime_guard'
            blind = r['policy'] == 'blind_retry'
            unresolved = uncertain and guarded and expired and not positive
            duplicate = r['fault'] == 'after' and expired and (blind or (not guarded and not positive))
            calls = 1 if not uncertain else 2 if blind or positive or unresolved else 3
            self.assertEqual((r['duplicates'], r['unresolved'], r['calls']),
                             (int(duplicate), int(unresolved), calls), r)
            self.assertEqual(r['runs'], 1)
        self.assertEqual(summarize(rows), {
            'blind_retry': dict(runs=72, duplicates=6, unresolved=0, denied=18, calls=108),
            'inspect_first': dict(runs=72, duplicates=4, unresolved=0, denied=18, calls=138),
            'lifetime_guard': dict(runs=72, duplicates=0, unresolved=10, denied=18, calls=128)})


if __name__ == '__main__':
    unittest.main()
