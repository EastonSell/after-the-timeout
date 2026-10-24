import unittest
from vendor import model
import policies

CASE=dict(id='two-call-terminal-race',family='new_posthoc_not_frozen',originals=['early','never'],late=3,original_terminal=4,scope='none',strategy='reserve',ttl=0,observation='certified',lag=0,retry_outcome='success',budget=2,deadline=5,horizon=12)

class BoundaryTests(unittest.TestCase):
    def test_two_call_completion(self):
        rows=model.simulate(CASE,'terminal_barrier')
        self.assertTrue(all(r['metrics']['actual_complete'] for r in rows))
        self.assertTrue(all(r['metrics']['duplicate_effects']==0 for r in rows))
    def test_old_policy_does_not_guarantee_completion(self):
        rows=model.simulate(CASE,'horizon_aware')
        self.assertTrue(any(not r['metrics']['actual_complete'] for r in rows))
        self.assertTrue(any(r['metrics']['actual_complete'] for r in rows))

    def test_short_deadline_disproves_evidence_dominance(self):
        c=dict(CASE, originals=['early','early'], deadline=3)
        old=model.simulate(c,'horizon_aware')
        new=model.simulate(c,'terminal_barrier')
        self.assertTrue(all(r['metrics']['justified_complete'] for r in old))
        self.assertTrue(all(not r['metrics']['justified_complete'] for r in new))

    def test_timeout_eventual_completion_is_not_return_evidence(self):
        rows=model.simulate(dict(CASE,retry_outcome='timeout_commit'),'terminal_barrier')
        self.assertTrue(all(r['metrics']['actual_complete'] for r in rows))
        self.assertTrue(all(not r['metrics']['justified_complete'] for r in rows))

    def test_extra_calls_require_longer_than_two_call_horizon(self):
        c=dict(CASE, original_terminal=2, late=1, lag=2, budget=3,
               deadline=10, horizon=8, retry_outcome='timeout_commit')
        with self.assertRaisesRegex(RuntimeError,'pending event beyond frozen horizon'):
            model.simulate(c,'terminal_barrier')
        rows=model.simulate(dict(c,horizon=c['deadline']+4),'terminal_barrier')
        self.assertTrue(all(r['metrics']['actual_complete'] for r in rows))
        self.assertTrue(all(r['metrics']['pending_events']==0 for r in rows))

if __name__=='__main__':unittest.main()
