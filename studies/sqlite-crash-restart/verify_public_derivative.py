"""Audit metadata-redacted publication against explicit original/public hashes.

This does not claim redacted bytes were admitted before measurement. Original
manifests remain original. The public map authenticates the disclosed derivative.
"""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / 'source'))
from assess import assess, read_evidence, summarize, cell_summaries


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify(root=HERE):
    root = Path(root)
    records = json.loads((root / 'ORIGINAL_PUBLIC_HASHES.json').read_text())['files']
    mapping = {item['public_path']: item for item in records}
    errors = []
    if len(mapping) != len(records):
        errors.append('duplicate original/public identity record')
    for name, record in mapping.items():
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()):
            errors.append('unsafe mapped path')
            continue
        if digest(path) != record['public_sha256'] or path.stat().st_size != record['public_bytes']:
            errors.append('public content mismatch: ' + name)
        if name.endswith(('.sqlite3', '.sqlite3-journal')) and record['original_sha256'] != record['public_sha256']:
            errors.append('database bytes changed: ' + name)
    source_map = json.loads((root / 'PUBLIC_DERIVATIVE_SOURCE.json').read_text())
    original_freeze = root / 'source/PRE_DATA_FREEZE.json'
    if digest(original_freeze) != source_map['original_predata_freeze_sha256']:
        errors.append('original pre-data identity mismatch')
    frozen_original = json.loads(original_freeze.read_text())['files']
    for name, original_hash in frozen_original.items():
        record = mapping['source/' + name]
        if record['original_sha256'] != original_hash or record['public_sha256'] != source_map['files'][name]:
            errors.append('source original/derivative identity mismatch: ' + name)
    run = root / 'run'
    original_output = json.loads((run / 'OUTPUT_SHA256.json').read_text())
    actual_names = {str(p.relative_to(run)) for p in run.rglob('*') if p.is_file()} - {'OUTPUT_SHA256.json'}
    if set(original_output) != actual_names:
        errors.append('run file set differs from original output manifest')
    for name, original_hash in original_output.items():
        if mapping['run/' + name]['original_sha256'] != original_hash:
            errors.append('run original identity mismatch: ' + name)
    # Admission retains its ORIGINAL freeze identity; never rewrite it to the derivative.
    admission = json.loads((run / 'admission.json').read_text())
    if admission['freeze_sha256'] != source_map['original_predata_freeze_sha256']:
        errors.append('original admission identity mismatch')
    plan = json.loads((root / 'source/protocol.json').read_text())['matrix']
    if json.loads((run / 'planned.json').read_text()) != plan:
        errors.append('public cases differ from original executed plan')
    rows = []
    for case in plan:
        folder = run / case['id']
        if json.loads((folder / 'case.json').read_text()) != case:
            errors.append('case identity mismatch: ' + case['id'])
        result = dict(id=case['id'], **assess(case, read_evidence(folder)))
        stored = json.loads((folder / 'result.json').read_text())
        if result['classification'] != stored['classification'] or result['measurements'] != stored['measurements']:
            errors.append('raw evidence disagrees with result: ' + case['id'])
        rows.append(result)
    summary = summarize(plan, rows)
    summary['cells'] = cell_summaries(plan, rows)
    saved = json.loads((run / 'summary.json').read_text())
    for name, value in summary.items():
        if saved[name] != value:
            errors.append('summary mismatch: ' + name)
    return {'scope': 'Post-data metadata derivative; original admission and identities preserved, not reassigned.',
            'original_files_checked': len(records), 'source_identity_pairs_checked': len(frozen_original),
            'summary': summary, 'audit_errors': errors,
            'complete_all_pass': not errors and summary['valid_pass'] == 24}


if __name__ == '__main__':
    result = verify()
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result['complete_all_pass'] else 1)
