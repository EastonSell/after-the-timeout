import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'source'))
import model,checker,runner
from test_model import case

class EvidenceTests(unittest.TestCase):
    def test_branch_checker_rejects_missing_tie_order_family(self):
        rows=model.simulate(case(late=2),'naive_inspection')
        checker.validate_group(rows)
        removed=[r for r in rows if 'B' in r['public_trace'][0]['observation']['positive']]
        with self.assertRaises(ValueError): checker.validate_group(removed)

    def test_predictions_are_retained_before_failure_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'result'
            result=runner.run(out,cases=[case()],policies=['horizon_aware'],force_prediction_failure=True)
            self.assertFalse(result['success'])
            self.assertTrue((out/'rows.jsonl.gz').exists())
            self.assertEqual(json.loads((out/'status.json').read_text())['state'],'prediction_failed')
            self.assertTrue((out/'predictions.json').exists())
            with self.assertRaises(FileExistsError):runner.run(out,cases=[case()])

    def test_checker_rejects_fabricated_positive(self):
        rows=model.simulate(case(originals=['never','never'],retry_outcome='reject'),'horizon_aware')
        tampered=copy.deepcopy(rows[0]);tampered['metrics']['justified_complete']=True
        with self.assertRaises(ValueError):checker.validate(tampered)

    def test_visibility_contract_same_despite_hidden_fates(self):
        left=model.initial_view(case(originals=['early','never'],retry_outcome='success'))
        right=model.initial_view(case(originals=['late','late'],retry_outcome='reject'))
        self.assertEqual(left,right)
        for policy in model.POLICIES:
            self.assertEqual(model.policy_action(policy,left),model.policy_action(policy,right))

if __name__=='__main__':unittest.main()
