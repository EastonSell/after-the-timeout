"""Read-only local checkpoint checks. Never execute commands or contact destinations."""
import argparse
import hashlib
import json
import re
from pathlib import Path, PurePosixPath

COMMIT = re.compile(r'[0-9a-f]{40}|[0-9a-f]{64}')
SHA256 = re.compile(r'[0-9a-f]{64}')


def exact(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise ValueError(f'{label}: expected fields {sorted(keys)}')


def nonempty(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f'{label}: expected nonempty text')


def commit(value, label):
    if not isinstance(value, str) or COMMIT.fullmatch(value) is None:
        raise ValueError(f'{label}: expected full lowercase commit identifier')


def relative(value):
    nonempty(value, 'path')
    p = PurePosixPath(value)
    if p.is_absolute() or '\\' in value or ':' in value or any(
            part in ('', '.', '..') for part in value.split('/')):
        raise ValueError('path: expected normalized relative POSIX path')
    return p


def safe_file(root, name):
    p = relative(name)
    target = root
    for part in p.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f'{name}: symlinks are not accepted')
    if not target.is_file():
        raise ValueError(f'{name}: artifact missing or not a regular file')
    return target


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def file_map(value, label):
    if not isinstance(value, dict) or not value:
        raise ValueError(f'{label}: expected nonempty path-to-sha256 map')
    for name, sha in value.items():
        relative(name)
        if not isinstance(sha, str) or SHA256.fullmatch(sha) is None:
            raise ValueError(f'{label}: invalid sha256')


def validate(data, root, current_commit):
    """current_commit must be independently observed by the caller, not copied from data."""
    errors, blockers = [], []
    publication = 'not_recorded'
    try:
        commit(current_commit, 'current_commit')
        exact(data, ('schema_version', 'source_commit', 'artifacts', 'reproduction',
                     'operations', 'publication'), 'checkpoint')
        if type(data['schema_version']) is not int or data['schema_version'] != 1:
            raise ValueError('Unsupported schema_version')
        commit(data['source_commit'], 'source_commit')
        if data['source_commit'] != current_commit:
            errors.append('source_commit differs from independently supplied current_commit')
        file_map(data['artifacts'], 'artifacts')
        root = Path(root).resolve(strict=True)
        for name, expected in data['artifacts'].items():
            try:
                if digest(safe_file(root, name)) != expected:
                    errors.append(f'{name}: hash mismatch')
            except (ValueError, OSError) as exc:
                errors.append(str(exc))
        reproduction = data['reproduction']
        exact(reproduction, ('argv', 'cwd', 'result', 'commit'), 'reproduction')
        if not isinstance(reproduction['argv'], list) or not reproduction['argv']:
            raise ValueError('reproduction.argv: expected nonempty list')
        for arg in reproduction['argv']:
            nonempty(arg, 'reproduction.argv argument')
        if reproduction['cwd'] != '.':
            raise ValueError('reproduction.cwd must be workspace root (.)')
        commit(reproduction['commit'], 'reproduction.commit')
        if reproduction['commit'] != data['source_commit']:
            errors.append('reproduction record belongs to another commit')
        if reproduction['result'] not in ('passed', 'failed', 'not_run'):
            raise ValueError('reproduction.result: unknown state')
        if reproduction['result'] != 'passed':
            blockers.append('reproduction has not recorded a passing result')
        if not isinstance(data['operations'], list):
            raise ValueError('operations: expected list')
        seen = set()
        for operation in data['operations']:
            exact(operation, ('id', 'state', 'next_observation'), 'operation')
            nonempty(operation['id'], 'operation.id')
            if operation['id'] in seen:
                raise ValueError('duplicate operation id')
            seen.add(operation['id'])
            if operation['state'] not in ('completed', 'not_executed', 'denied', 'pending', 'uncertain'):
                raise ValueError('operation.state: unknown state')
            nonempty(operation['next_observation'], 'operation.next_observation')
            if operation['state'] in ('pending', 'uncertain'):
                blockers.append(f'operation {operation["id"]}: {operation["state"]}; observe before retry')
            elif operation['state'] == 'denied':
                blockers.append(f'operation {operation["id"]}: denied; do not retry from this record')
        pub = data['publication']
        exact(pub, ('expected_destination', 'receipts'), 'publication')
        destination = pub['expected_destination']
        if destination is not None:
            nonempty(destination, 'publication.expected_destination')
        if not isinstance(pub['receipts'], list):
            raise ValueError('publication.receipts: expected list')
        if destination is None and pub['receipts']:
            raise ValueError('receipts require an expected_destination')
        recorded = set()
        for receipt in pub['receipts']:
            exact(receipt, ('destination', 'commit', 'artifacts', 'reference'), 'receipt')
            nonempty(receipt['reference'], 'receipt.reference')
            commit(receipt['commit'], 'receipt.commit')
            file_map(receipt['artifacts'], 'receipt.artifacts')
            if receipt['destination'] != destination or receipt['commit'] != data['source_commit']:
                errors.append('receipt destination or commit mismatch')
                continue
            for name, sha in receipt['artifacts'].items():
                if data['artifacts'].get(name) != sha:
                    errors.append(f'{name}: receipt not in source manifest or hash mismatch')
                else:
                    recorded.add(name)
        if destination is not None:
            if recorded == set(data['artifacts']):
                publication = 'recorded_complete'
            elif recorded:
                publication = 'recorded_partial'
            else:
                publication = 'not_recorded'
            if publication != 'recorded_complete':
                blockers.append('publication evidence is incomplete for the declared destination')
    except (ValueError, OSError, TypeError) as exc:
        errors.append(str(exc))
    return dict(integrity_valid=not errors,
                handoff_state='invalid' if errors else 'blocked' if blockers else 'ready_for_review',
                publication_evidence=publication, errors=errors, blockers=blockers,
                approval_granted=False,
                limits=['Current commit is caller-supplied; working tree ancestry is not verified.',
                        'Commands are inspected, never executed; passing results are recorded claims.',
                        'Receipts are checked locally, not authenticated or remotely verified.',
                        'No status here grants permission to retry, execute, publish or share.'])


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate JSON object key')
        result[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest', help='Relative manifest path beneath workspace')
    parser.add_argument('--workspace', default='.')
    parser.add_argument('--current-commit', required=True,
                        help='Full identifier independently observed from the intended checkout')
    args = parser.parse_args()
    try:
        root = Path(args.workspace).resolve(strict=True)
        manifest = safe_file(root, args.manifest)
        if manifest.stat().st_size > 1024 * 1024:
            raise ValueError('Manifest exceeds 1 MiB limit')
        data = json.loads(manifest.read_text(encoding='utf-8'), object_pairs_hook=unique_object)
        report = validate(data, root, args.current_commit)
    except (ValueError, OSError) as exc:
        report = dict(integrity_valid=False, handoff_state='invalid', errors=[str(exc)], approval_granted=False)
    print(json.dumps(report, indent=2))
    return 2 if report['handoff_state'] == 'invalid' else 1 if report['handoff_state'] == 'blocked' else 0


if __name__ == '__main__':
    raise SystemExit(main())
