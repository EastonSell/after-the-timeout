import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
from build_packet import build_packet, ROOT, SKILL, PUBLIC_SKILL_FILES
from score import score, unique_object
spec = importlib.util.spec_from_file_location('review_validator', SKILL/'scripts/validate_checkpoint.py')
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)
EXPECTED = json.loads((HERE/'expected.json').read_text())


class ReviewHarnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.packet = build_packet(self.root/'packet')

    def perfect(self):
        return dict(reviews=[dict(case_id=key, **copy.deepcopy(value),
                                 rationale='Synthetic scorer test, not an agent response.')
                             for key,value in EXPECTED.items()])

    def test_frozen_rubric_and_key(self):
        for line in (HERE/'FREEZE.sha256').read_text().splitlines():
            digest, name = line.split()
            self.assertEqual(hashlib.sha256((ROOT/name).read_bytes()).hexdigest(),digest)

    def test_validator_baseline_matches_states_not_agent_behavior(self):
        for case_id, expected in EXPECTED.items():
            with self.subTest(case_id=case_id):
                case = self.packet/'cases'/case_id
                checkpoint = json.loads((case/'checkpoint.json').read_text())
                observed = json.loads((case/'observations.json').read_text())
                report = validator.validate(checkpoint, case, observed['current_commit'])
                self.assertEqual(report['handoff_state'],expected['handoff_state'])
                self.assertEqual(report['publication_evidence'],expected['publication_evidence'])
                self.assertFalse(report['approval_granted'])

    def test_packet_repeatable_and_manifest_complete(self):
        other = build_packet(self.root/'again')
        first = {str(p.relative_to(self.packet)):p.read_bytes() for p in self.packet.rglob('*') if p.is_file()}
        second = {str(p.relative_to(other)):p.read_bytes() for p in other.rglob('*') if p.is_file()}
        self.assertEqual(first,second)
        manifest = json.loads(first.pop('PACKET_MANIFEST.json'))
        self.assertEqual({p:hashlib.sha256(b).hexdigest() for p,b in first.items()},manifest)

    def test_packet_contains_no_key_rubric_generator_or_results(self):
        allowed = {'REQUEST.md','PACKET_MANIFEST.json'} | {'skill/'+n for n in PUBLIC_SKILL_FILES}
        for case_id in EXPECTED:
            allowed |= {f'cases/{case_id}/{n}' for n in ('source.py','checks.py','checkpoint.json','observations.json')}
        allowed.remove('cases/C02/checks.py')
        actual = {str(p.relative_to(self.packet)) for p in self.packet.rglob('*') if p.is_file()}
        self.assertEqual(actual,allowed)
        for name in PUBLIC_SKILL_FILES:
            self.assertEqual((self.packet/'skill'/name).read_bytes(),(SKILL/name).read_bytes())

    def test_existing_directory_is_refused(self):
        before = (self.packet/'REQUEST.md').read_bytes()
        with self.assertRaises(FileExistsError): build_packet(self.packet)
        self.assertEqual((self.packet/'REQUEST.md').read_bytes(),before)

    def test_scorer_perfect_and_single_wrong_field(self):
        answer = self.perfect()
        self.assertEqual(score(answer,EXPECTED)['scored_fields'],48)
        answer['reviews'][0]['approval_granted'] = True
        result = score(answer,EXPECTED)
        self.assertEqual(result['scored_fields'],47)
        self.assertFalse(result['cases'][0]['fields']['approval_granted'])

    def test_scorer_issue_order_is_irrelevant(self):
        answer = self.perfect()
        answer['reviews'][6]['issues'].reverse()
        self.assertEqual(score(answer,EXPECTED)['scored_fields'],48)

    def test_scorer_missing_duplicate_extra_cases_invalid(self):
        for mutate in (lambda a:a['reviews'].pop(),
                       lambda a:a['reviews'].append(copy.deepcopy(a['reviews'][0])),
                       lambda a:a['reviews'][1].update(case_id='C01'),
                       lambda a:a['reviews'][0].update(case_id='C99')):
            answer=self.perfect(); mutate(answer)
            with self.assertRaises(ValueError): score(answer,EXPECTED)

    def test_scorer_malformed_fields_invalid(self):
        changes = [dict(approval_granted=0),dict(issues=['missing_artifact','missing_artifact']),
                   dict(issues='missing_artifact'),dict(next_action='retry_now'),
                   dict(handoff_state=[]),dict(rationale=''),dict(extra='bad')]
        for change in changes:
            answer=self.perfect();answer['reviews'][0].update(change)
            with self.assertRaises(ValueError):score(answer,EXPECTED)
        answer=self.perfect();del answer['reviews'][0]['issues']
        with self.assertRaises(ValueError):score(answer,EXPECTED)

    def test_duplicate_json_keys_fail(self):
        with self.assertRaises(ValueError):
            json.loads('{"reviews":[],"reviews":[]}',object_pairs_hook=unique_object)


if __name__ == '__main__': unittest.main()
