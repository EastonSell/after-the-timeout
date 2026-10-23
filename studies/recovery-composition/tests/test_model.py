import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'source'))
import model
import checker


def case(**changes):
    value = dict(id='unit', family='unit', originals=['early','late'], late=3,
        original_terminal=4, scope='item', strategy='reserve', ttl=7,
        observation='certified', lag=0, retry_outcome='success', budget=3,
        deadline=10, horizon=15)
    value.update(changes)
    return value

class ContractTests(unittest.TestCase):
    def test_reservation_prevents_concurrent_replay(self):
        rows = model.simulate(case(), 'blind_keyed')
        self.assertTrue(rows)
        self.assertTrue(all(max(r['metrics']['counts'].values()) <= 1 for r in rows))

    def test_cache_without_reservation_admits_concurrent_duplicate(self):
        rows = model.simulate(case(strategy='cache'), 'blind_keyed')
        self.assertTrue(any(r['metrics']['duplicate_effects'] for r in rows))

    def test_expiry_does_not_cancel_original_owner(self):
        rows = model.simulate(case(ttl=2), 'blind_keyed')
        self.assertTrue(any(r['metrics']['duplicate_effects'] for r in rows))

    def test_stale_missing_is_not_terminal_noncommit(self):
        rows = model.simulate(case(lag=2), 'naive_inspection')
        self.assertTrue(any(r['metrics']['duplicate_effects'] for r in rows))
        later=model.simulate(case(lag=2,late=6,original_terminal=7), 'naive_inspection')
        self.assertTrue(any(r['metrics']['post_return_duplicate_effects'] for r in later))

    def test_effect_observation_ties_include_both_orders(self):
        rows = model.simulate(case(late=2, original_terminal=4), 'naive_inspection')
        seen = {tuple(r['public_trace'][0]['observation']['positive']) for r in rows}
        self.assertIn(('A',), seen)
        self.assertIn(('A','B'), seen)

    def test_horizon_policy_safe_through_all_pending_events(self):
        for scope in ['none','item','batch']:
            for strategy in ['reserve','cache']:
                rows = model.simulate(case(scope=scope,strategy=strategy,ttl=2,
                    retry_outcome='timeout_commit',lag=2), 'horizon_aware')
                self.assertTrue(rows)
                self.assertTrue(all(r['metrics']['duplicate_effects']==0 for r in rows))
                self.assertTrue(all(not r['metrics']['pending_events'] for r in rows))

    def test_retry_failure_not_reported_complete(self):
        rows = model.simulate(case(originals=['never','never'],retry_outcome='reject'), 'horizon_aware')
        self.assertTrue(rows)
        self.assertTrue(all(not r['metrics']['actual_complete'] and not r['metrics']['justified_complete'] for r in rows))

    def test_batch_cache_suppression_does_not_fill_missing(self):
        rows = model.simulate(case(scope='batch',strategy='cache',original_terminal=1,originals=['early','never']), 'blind_keyed')
        self.assertTrue(rows)
        self.assertTrue(any(not r['metrics']['actual_complete'] for r in rows))

    def test_public_action_function_does_not_receive_hidden_case(self):
        view = model.initial_view(case())
        self.assertNotIn('originals', view['contract'])
        self.assertNotIn('retry_outcome', view['contract'])
        self.assertEqual(model.policy_action('horizon_aware',copy.deepcopy(view)),
                         model.policy_action('horizon_aware',copy.deepcopy(view)))

    def test_cost_budget_and_terminal_horizon(self):
        rows = model.simulate(case(budget=2), 'capability_fallback')
        self.assertTrue(rows)
        self.assertTrue(all(r['metrics']['calls']<=2 for r in rows))
        self.assertTrue(all(r['metrics']['evaluation_end']<=15 for r in rows))

    def test_independent_checker_accepts_then_rejects_tampered_cost(self):
        rows = model.simulate(case(), 'horizon_aware')
        self.assertTrue(rows)
        checker.validate(rows[0])
        changed=copy.deepcopy(rows[0]); changed['metrics']['calls']+=1
        with self.assertRaises(ValueError): checker.validate(changed)

    def test_checker_rejects_deleted_effect(self):
        rows=model.simulate(case(), 'naive_inspection')
        self.assertTrue(rows)
        changed=copy.deepcopy(rows[0])
        changed['hidden_trace']=[e for e in changed['hidden_trace'] if e['kind']!='effect']
        with self.assertRaises(ValueError): checker.validate(changed)

    def test_oracle_is_information_bound_not_policy(self):
        c=case(originals=['early','never'],observation='opaque',ttl=2)
        rows=model.simulate(c, 'horizon_aware')
        self.assertTrue(rows)
        self.assertTrue(model.omniscient_feasible(c))
        self.assertTrue(all(not r['metrics']['actual_complete'] for r in rows))

    def test_grid_and_heldout_are_disjoint_named_families(self):
        cases=model.generate_cases()
        self.assertTrue(cases)
        self.assertEqual(len({c['id'] for c in cases}),len(cases))
        self.assertEqual({c['family'] for c in cases}, {'exhaustive','expiry_late_original','no_terminal_evidence','tight_deadline_and_budget'})

if __name__=='__main__': unittest.main()
