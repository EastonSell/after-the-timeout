"""Synthetic correctness only: no subprocesses, sockets, signals, or matrix run.

Mutations caught: dropped effects/keys, erased restart state, misplaced barrier,
ignored payload binding, partial transaction, and accepting foreign schemas.
"""
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from apparatus import Store

A = {'item': 'A', 'value': 1}
B = {'item': 'A', 'value': 2}


class SyntheticInterruption(Exception):
    pass


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'effects.sqlite3'

    def test_reopening_retains_committed_effect_and_key(self):
        first = Store(self.path).write('original', A, 'K')
        self.assertEqual(first.get('state'), 'committed')
        state = Store(self.path).snapshot()
        self.assertEqual(len(state['effects']), 1)
        self.assertEqual(len(state['keys']), 1)
        self.assertEqual(state['attempts'][0]['state'], 'committed')

    def test_no_key_repetition_appends_second_effect(self):
        store = Store(self.path)
        store.write('original', A)
        store.write('recovery', A)
        self.assertEqual(len(store.snapshot()['effects']), 2)

    def test_retained_key_deduplicates_after_reopen(self):
        Store(self.path).write('original', A, 'K')
        outcome = Store(self.path).write('recovery', A, 'K')
        self.assertEqual(outcome.get('state'), 'deduplicated')
        self.assertEqual(outcome.get('effect_id'), 1)
        self.assertEqual(len(Store(self.path).snapshot()['effects']), 1)

    def test_retained_key_rejects_changed_payload_without_overwrite(self):
        Store(self.path).write('original', A, 'K')
        outcome = Store(self.path).write('recovery', B, 'K')
        self.assertEqual(outcome.get('status'), 409)
        self.assertEqual(outcome.get('state'), 'rejected')
        state = Store(self.path).snapshot()
        self.assertEqual(len(state['effects']), 1)
        self.assertEqual(json.loads(state['effects'][0]['payload']), A)

    def test_precommit_exception_rolls_back_effect_and_key_not_admission(self):
        seen = []
        def hook(phase):
            seen.append(phase)
            if phase == 'before_commit':
                with sqlite3.connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM effects').fetchone()[0], 0)
                raise SyntheticInterruption()
        with self.assertRaises(SyntheticInterruption):
            Store(self.path).write('original', A, 'K', hook)
        self.assertEqual(seen, ['before_commit'])
        state = Store(self.path).snapshot()
        self.assertEqual(state['effects'], [])
        self.assertEqual(state['keys'], [])
        self.assertEqual(state['attempts'][0]['state'], 'pending')
        result = Store(self.path).write('recovery', B, 'K')
        self.assertEqual(result['state'], 'committed')
        self.assertEqual(result['status'], 200)

    def test_postcommit_exception_retains_effect_key_and_original_state(self):
        seen = []
        def hook(phase):
            seen.append(phase)
            if phase == 'after_commit':
                with sqlite3.connect(self.path) as db:
                    self.assertEqual(db.execute('SELECT count(*) FROM effects').fetchone()[0], 1)
                raise SyntheticInterruption()
        with self.assertRaises(SyntheticInterruption):
            Store(self.path).write('original', A, 'K', hook)
        self.assertEqual(seen, ['before_commit', 'after_commit'])
        state = Store(self.path).snapshot()
        self.assertEqual(len(state['effects']), 1)
        self.assertEqual(len(state['keys']), 1)
        self.assertEqual(state['attempts'][0]['state'], 'committed')

    def test_foreign_schema_is_refused_without_modification(self):
        with sqlite3.connect(self.path) as db:
            db.execute('CREATE TABLE unrelated(value TEXT)')
            db.execute("INSERT INTO unrelated VALUES ('keep')")
        before = self.path.read_bytes()
        with self.assertRaises(ValueError):
            Store(self.path)
        self.assertEqual(self.path.read_bytes(), before)

    def test_repeated_operation_id_is_not_silently_replayed(self):
        store = Store(self.path)
        store.write('original', A, 'K')
        with self.assertRaises(sqlite3.IntegrityError):
            store.write('original', A, 'K')
        self.assertEqual(len(store.snapshot()['effects']), 1)


if __name__ == '__main__':
    unittest.main()
