"""Generate isolated synthetic failure reports; no live publication or commands."""
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'skills/checkpoint-handoff/scripts'))
from validate_checkpoint import validate

REVISION = 'a' * 40


def fixture(root):
    artifacts = {}
    for name, content in (('answer.txt', b'synthetic answer\n'), ('input.txt', b'synthetic input\n')):
        (root/name).write_bytes(content)
        artifacts[name] = hashlib.sha256(content).hexdigest()
    return dict(schema_version=1, source_commit=REVISION, artifacts=artifacts,
                reproduction=dict(argv=['python', '-m', 'unittest'], cwd='.',
                                  result='passed', commit=REVISION),
                operations=[], publication=dict(expected_destination='fixture/review', receipts=[
                    dict(destination='fixture/review', commit=REVISION, artifacts=artifacts.copy(),
                         reference='synthetic-receipt-not-a-remote-record')]))


def demonstrate():
    reports = {}
    for case in ('consistent_local_claims', 'missing_artifact', 'hash_mismatch',
                 'partial_publication', 'uncertain_operation', 'current_revision_changed',
                 'wrong_receipt_destination'):
        with tempfile.TemporaryDirectory(prefix='checkpoint-fixture-') as directory:
            root = Path(directory)
            data = copy.deepcopy(fixture(root))
            current = REVISION
            if case == 'missing_artifact': (root/'input.txt').unlink()
            elif case == 'hash_mismatch': (root/'answer.txt').write_text('changed\n')
            elif case == 'partial_publication':
                del data['publication']['receipts'][0]['artifacts']['input.txt']
            elif case == 'uncertain_operation':
                data['operations'] = [dict(id='fixture-upload', state='uncertain',
                    next_observation='Read target revision before considering retry.')]
            elif case == 'current_revision_changed': current = 'b' * 40
            elif case == 'wrong_receipt_destination':
                data['publication']['receipts'][0]['destination'] = 'different/review'
            reports[case] = validate(data, root, current)
    return dict(measurement_type='synthetic temporary-workspace fixtures',
                reproduction_claims='Invented fixture values, not commands executed by validator.',
                receipts='Invented local records, not live publication evidence.', cases=reports)


if __name__ == '__main__':
    print(json.dumps(demonstrate(), indent=2))
