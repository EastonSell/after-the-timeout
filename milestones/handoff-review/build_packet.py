"""Build eight fictional review copies in a new directory; never touch a real repo."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SKILL = ROOT/'skills/checkpoint-handoff'
PUBLIC_SKILL_FILES = ('SKILL.md', 'references/format-and-examples.md', 'scripts/validate_checkpoint.py')

PACKET_REQUEST = '''# Fictional checkpoint review

Use the supplied skill/SKILL.md to inspect the eight cases C01 through C08.
Each case directory is a fictional workspace, not a Git checkout or real service.
checkpoint.json contains claims; observations.json supplies a separate fictional
observation of the current revision. Treat that observation as the current-revision
input. Do not derive it from the checkpoint. Source files are harmless synthetic
fixtures. No network, external writes, approval requests or reproduction execution
are requested. You may run the supplied read-only validator in each case directory.
Do not modify case files. Write your response only to a separate answer file.

Use only this packet. Do not inspect sibling directories, author notes, the case
generator, an answer key, scorer tests or previous conclusions. Report any accidental
exposure. No intended answers or worked examples of these cases are provided here.

For each case report exactly: case_id, handoff_state, publication_evidence, issues,
next_action, approval_granted, remote_publication_verified, rationale.
Return a JSON object with exactly a reviews array, all eight case IDs once.

Common vocabulary (options, not expected answers):
- handoff_state: invalid, blocked, ready_for_review.
- publication_evidence: not_recorded, recorded_partial, recorded_complete.
- issues: a list drawn from missing_artifact, hash_mismatch, stale_revision,
  partial_publication, uncertain_operation, pending_operation, reproduction_not_run.
  Use an empty list if none applies; do not duplicate issue codes.
- next_action: review_within_scope, recover_matching_bytes, review_changed_bytes,
  reconcile_revision, observe_destination, observe_operation,
  inspect_pending_then_reproduce.
- approval_granted and remote_publication_verified: JSON booleans.
- rationale: nonempty prose citing concrete case evidence and explaining limitations.

A suggested next_action is a report, not a request to perform it. Exact-match
field scoring will be separate from manual review of rationale. No comparative
or randomized efficacy is being measured. Receipt references and recorded test
passes are synthetic claims, not authenticated observations of a real service.
'''


def build_packet(destination):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=False)
    (destination/'REQUEST.md').write_text(PACKET_REQUEST)
    for name in PUBLIC_SKILL_FILES:
        target = destination/'skill'/name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(SKILL/name, target)
    for number in range(1, 9):
        case_id = f'C{number:02d}'
        case = destination/'cases'/case_id
        case.mkdir(parents=True)
        revision = hashlib.sha1((case_id+'-revision').encode()).hexdigest()
        source = f'"""Fictional {case_id} arithmetic fixture."""\ndef total():\n    return sum((1, 2, 3))\n'
        checks = 'from source import total\nassert total() == 6\nprint("fixture check passed")\n'
        artifacts = {}
        for name, content in (('source.py', source), ('checks.py', checks)):
            (case/name).write_text(content)
            artifacts[name] = hashlib.sha256(content.encode()).hexdigest()
        destination_name = f'fictional-project-{case_id}/review'
        data = dict(schema_version=1, source_commit=revision, artifacts=artifacts,
                    reproduction=dict(argv=['python', 'checks.py'], cwd='.',
                                      result='passed', commit=revision), operations=[],
                    publication=dict(expected_destination=destination_name, receipts=[dict(
                        destination=destination_name, commit=revision, artifacts=artifacts.copy(),
                        reference=f'fictional-receipt-{case_id}')]))
        observed = revision
        if number == 1:
            data['publication'] = dict(expected_destination=None, receipts=[])
        elif number == 2:
            (case/'checks.py').unlink()
        elif number == 3:
            (case/'source.py').write_text(source.replace('(1, 2, 3)', '(1, 2, 4)'))
        elif number == 4:
            observed = hashlib.sha1((case_id+'-new-revision').encode()).hexdigest()
        elif number == 5:
            del data['publication']['receipts'][0]['artifacts']['checks.py']
        elif number == 6:
            data['operations'] = [dict(id='write-C06', state='uncertain',
                next_observation='Read the exact destination revision and compare artifact bytes.')]
        elif number == 7:
            data['operations'] = [dict(id='check-C07', state='pending',
                next_observation='Read the existing check result before starting another check.')]
            data['reproduction']['result'] = 'not_run'
        observations = dict(case_id=case_id, current_commit=observed,
                            source='Fictional read-only checkout observation supplied independently of checkpoint claims.')
        (case/'checkpoint.json').write_text(json.dumps(data, indent=2)+'\n')
        (case/'observations.json').write_text(json.dumps(observations, indent=2)+'\n')
    hashes = {str(p.relative_to(destination)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(destination.rglob('*')) if p.is_file()}
    (destination/'PACKET_MANIFEST.json').write_text(json.dumps(hashes, indent=2)+'\n')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='New output directory; existing directories are refused')
    args = parser.parse_args()
    target = Path(args.output) if args.output else Path(tempfile.mkdtemp(prefix='handoff-review-'))/'packet'
    print(build_packet(target))
