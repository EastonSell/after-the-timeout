#!/usr/bin/env python3
"""Validate a ZIP against a separately reviewed JSON manifest; stdlib only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import zipfile


class InvalidRelease(ValueError):
    pass


def require(ok, message):
    if not ok:
        raise InvalidRelease(message)


def safe_path(value):
    require(isinstance(value, str) and value, 'path must be a nonempty string')
    parts = value.split('/')
    require(all(re.fullmatch(r'[A-Za-z0-9_-][A-Za-z0-9_.-]*', p) and
                not p.endswith('.') and p.split('.')[0].upper() not in
                {'CON', 'PRN', 'AUX', 'NUL', *(f'COM{i}' for i in range(1, 10)),
                 *(f'LPT{i}' for i in range(1, 10))} for p in parts),
            f'unsafe or nonportable path: {value!r}')
    return value


def validate(archive, manifest, run_tests=False, max_bytes=100_000_000):
    require(isinstance(manifest, dict) and manifest.get('version') == 1, 'manifest version must be 1')
    require(manifest.get('editorial_review') == 'approved', 'author/editorial review must be recorded as approved')
    records = manifest.get('files')
    require(isinstance(records, list) and records, 'files must be a nonempty list')
    expected = {}
    for item in records:
        require(isinstance(item, dict), 'file record must be an object')
        path = safe_path(item.get('path'))
        require(path not in expected, f'duplicate allowlist path: {path}')
        require(item.get('category') in {'code', 'data', 'documentation', 'scientific-report', 'skill'},
                f'non-public or unknown artifact category: {path}')
        require(item.get('public_review') == 'approved', f'public content review missing: {path}')
        require(isinstance(item.get('sha256'), str) and re.fullmatch('[0-9a-f]{64}', item['sha256']),
                f'invalid sha256: {path}')
        expected[path] = item
    require(len({p.casefold() for p in expected}) == len(expected), 'case-colliding paths')
    for path in expected:
        require(not any('/'.join(path.split('/')[:i]).casefold() in {p.casefold() for p in expected}
                        for i in range(1, len(path.split('/')))), 'file/directory path collision')
    dependencies = manifest.get('dependencies', [])
    require(isinstance(dependencies, list), 'dependencies must be a list')
    deps = {}
    for dep in dependencies:
        require(isinstance(dep, dict) and isinstance(dep.get('id'), str) and dep['id'], 'dependency needs an id')
        require(dep['id'] not in deps, 'duplicate dependency id')
        if dep.get('kind') == 'bundled':
            require(safe_path(dep.get('path')) in expected, f'missing declared dependency: {dep.get("path")}')
        else:
            require(dep.get('kind') == 'external' and isinstance(dep.get('source'), str) and dep['source'] and
                    isinstance(dep.get('pin'), str) and dep['pin'], 'external dependency needs source and immutable pin')
        deps[dep['id']] = dep
    tests = manifest.get('tests', [])
    require(isinstance(tests, list), 'tests must be a list')
    for test in tests:
        require(isinstance(test, dict), 'test record must be an object')
        require(safe_path(test.get('script')) in expected, 'test script absent from allowlist')
        require(isinstance(test.get('requires', []), list) and all(isinstance(d, str) and d in deps for d in test.get('requires', [])),
                'test references undeclared dependency')
        require(isinstance(test.get('args', []), list) and all(isinstance(a, str) for a in test.get('args', [])), 'test args must be strings')
        require(type(test.get('timeout_seconds', 60)) is int and 1 <= test.get('timeout_seconds', 60) <= 600, 'invalid test timeout')
    with zipfile.ZipFile(archive) as z:
        infos = z.infolist()
        require(all(i.orig_filename == i.filename for i in infos), 'normalized archive entry name')
        names = [safe_path(i.filename) for i in infos]
        require(len(names) == len(set(names)), 'duplicate archive entries')
        require(set(names) == set(expected), f'allowlist mismatch: missing={sorted(set(expected)-set(names))}, unexpected={sorted(set(names)-set(expected))}')
        require(sum(i.file_size for i in infos) <= max_bytes, 'archive exceeds uncompressed size limit')
        payload = {}
        for info in infos:
            mode = info.external_attr >> 16
            require(not info.is_dir() and stat.S_IFMT(mode) in (0, stat.S_IFREG), f'nonregular archive entry: {info.filename}')
            require(not info.flag_bits & 1, 'encrypted archives are unsupported')
            data = z.read(info)
            require(hashlib.sha256(data).hexdigest() == expected[info.filename]['sha256'], f'hash mismatch: {info.filename}')
            payload[info.filename] = data
    results = []
    if run_tests:
        # This is checkout isolation, NOT an OS/network/credential security sandbox.
        with tempfile.TemporaryDirectory(prefix='release-check-') as tmp:
            root = Path(tmp) / 'bundle'
            root.mkdir()
            for path, data in payload.items():
                out = root / path
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(data)
            for test in tests:
                external = [d for d in test.get('requires', []) if deps[d]['kind'] == 'external']
                if external:
                    results.append({'script': test['script'], 'status': 'not-run', 'external_requirements': external})
                    continue
                env = {'PATH': os.defpath, 'HOME': tmp, 'TMPDIR': tmp, 'TEMP': tmp, 'TMP': tmp,
                       'PYTHONNOUSERSITE': '1', 'PYTHONDONTWRITEBYTECODE': '1'}
                if 'SYSTEMROOT' in os.environ:
                    env['SYSTEMROOT'] = os.environ['SYSTEMROOT']
                try:
                    proc = subprocess.run([sys.executable, '-E', '-s', '-B', '--', test['script'], *test.get('args', [])],
                                          cwd=root, env=env, timeout=test.get('timeout_seconds', 60),
                                          capture_output=True, text=True)
                except subprocess.TimeoutExpired as exc:
                    raise InvalidRelease(f'test timed out: {test["script"]}') from exc
                require(proc.returncode == 0, f'test failed: {test["script"]}\n{proc.stdout}\n{proc.stderr}')
                results.append({'script': test['script'], 'status': 'passed', 'stdout': proc.stdout, 'stderr': proc.stderr})
    return {'package': 'validated', 'files': len(expected), 'tests_requested': run_tests,
            'tests': results, 'all_declared_tests_passed': bool(tests) and run_tests and all(r['status'] == 'passed' for r in results),
            'external_requirements': [d for d in dependencies if d['kind'] == 'external']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    parser.add_argument('manifest', type=Path)
    parser.add_argument('--run-tests', action='store_true', help='Execute reviewed Python tests. Not a security sandbox.')
    args = parser.parse_args()
    try:
        result = validate(args.archive, json.loads(args.manifest.read_text()), args.run_tests)
        print(json.dumps(result, indent=2))
        return 2 if args.run_tests and not result['all_declared_tests_passed'] else 0
    except (InvalidRelease, OSError, ValueError, zipfile.BadZipFile, RuntimeError) as exc:
        print(f'INVALID: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
