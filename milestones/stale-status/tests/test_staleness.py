import importlib.util
import json
from pathlib import Path
import sys
import unittest
from workflow import Service, execute, UnknownOutcome
from run_experiment import collect, summarize, ROOT

spec = importlib.util.spec_from_file_location('original_workflow', ROOT/'baseline/workflow.py')
original = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = original
spec.loader.exec_module(original)
CFG = json.loads((ROOT/'config.json').read_text())

class StalenessTests(unittest.TestCase):
    def test_stale_then_fresh(self):
        service = Service('after', status_staleness=1)
        with self.assertRaises(UnknownOutcome):
            service.write('a')
        self.assertEqual(service.records, ['a'])
        self.assertEqual(service.status('a'), 'not_committed')
        self.assertEqual(service.status('a'), 'committed')
        self.assertEqual(service.calls, 3)

    def test_fresh_immediately(self):
        service = Service('after', status_staleness=0)
        self.assertEqual(execute(service, 'inspect_first'), 'committed')
        self.assertEqual((len(service.records), service.calls), (1, 2))

    def test_stale_inspection_duplicates_without_idempotency(self):
        service = Service('after', status_staleness=1)
        self.assertEqual(execute(service, 'inspect_first'), 'committed')
        self.assertEqual((len(service.records), service.calls), (2, 3))

    def test_stale_inspection_idempotent_retry(self):
        service = Service('after', idempotent=True, status_staleness=1)
        self.assertEqual(execute(service, 'inspect_first'), 'committed')
        self.assertEqual((len(service.records), service.calls), (1, 3))

    def test_unsupported_status_preserves_budget(self):
        service = Service('after', False, status_staleness=1)
        self.assertEqual(execute(service, 'inspect_first'), 'needs_reconciliation')
        self.assertEqual(service.stale_reads_remaining['example-001'], 1)
        self.assertEqual((len(service.records), service.calls), (1, 2))

    def test_budget_is_operation_scoped(self):
        service = Service('after', status_staleness=1)
        for operation in ('a', 'b'):
            with self.assertRaises(UnknownOutcome):
                service.write(operation)
        self.assertEqual(service.status('a'), 'not_committed')
        self.assertEqual(service.status('a'), 'committed')
        self.assertEqual(service.status('b'), 'not_committed')
        self.assertEqual(service.status('b'), 'committed')
        self.assertEqual(service.status('missing'), 'not_committed')

    def test_only_after_fault_arms_staleness(self):
        for fault in ('none', 'before', 'denied'):
            service = Service(fault, status_staleness=1)
            execute(service, 'inspect_first')
            self.assertFalse(service.stale_reads_remaining)

    def test_invalid_staleness(self):
        for value in (-1, 2, True, 0.5, '1'):
            with self.assertRaises(ValueError):
                Service(status_staleness=value)

    def test_zero_matches_original_every_cell(self):
        for fault in CFG['faults']:
            for status in (True, False):
                for idem in (True, False):
                    for policy in ('blind_retry', 'inspect_first'):
                        with self.subTest(fault=fault, status=status, idem=idem, policy=policy):
                            baseline = original.Service(fault, status, idem)
                            current = Service(fault, status, idem)
                            self.assertEqual(original.execute(baseline, policy), execute(current, policy))
                            self.assertEqual((baseline.calls, baseline.records, baseline.seen),
                                             (current.calls, current.records, current.seen))

    def test_rows_match_published_baseline(self):
        rows = collect(CFG)
        baseline = json.loads((ROOT/'baseline/results/experiment.json').read_text())['rows']
        current = [{k:v for k,v in r.items() if k != 'status_staleness'} for r in rows if r['status_staleness'] == 0]
        self.assertEqual(current, baseline)

    def test_all_cell_counts_and_totals(self):
        rows = collect(CFG)
        self.assertEqual(len(rows), 192)
        summary, cells = summarize(rows)
        self.assertEqual(len(cells), 64)
        for cell in cells:
            self.assertEqual(cell['runs'], 3)
            fault, supported, idem, policy, stale = [cell[k] for k in ('fault','status_supported','idempotent','policy','status_staleness')]
            unresolved = fault in ('before', 'after') and policy == 'inspect_first' and not supported and not idem
            dup = fault == 'after' and not idem and (policy == 'blind_retry' or (supported and stale == 1))
            calls = 1
            if fault in ('before', 'after'):
                calls = 2
                if policy == 'inspect_first' and not unresolved and not (fault == 'after' and supported and stale == 0):
                    calls = 3
            self.assertEqual(cell['duplicates'], 3 * dup, cell)
            self.assertEqual(cell['unresolved'], 3 * unresolved, cell)
            self.assertEqual(cell['calls'], 3 * calls, cell)
        self.assertEqual(summary, {
            '0': {'blind_retry': dict(runs=48, duplicates=6, unresolved=0, calls=72),
                  'inspect_first': dict(runs=48, duplicates=0, unresolved=6, calls=84)},
            '1': {'blind_retry': dict(runs=48, duplicates=6, unresolved=0, calls=72),
                  'inspect_first': dict(runs=48, duplicates=3, unresolved=6, calls=90)}})

    def test_seeds_change_order_not_cell_outcomes(self):
        rows = collect(CFG)
        fields = ('status_staleness','fault','status_supported','idempotent','policy','outcome','calls','commits','duplicate_commits')
        by_seed = [{tuple(r[k] for k in fields) for r in rows if r['seed'] == seed} for seed in CFG['seeds']]
        self.assertEqual(by_seed[0], by_seed[1])
        self.assertEqual(by_seed[1], by_seed[2])

if __name__ == '__main__':
    unittest.main()
