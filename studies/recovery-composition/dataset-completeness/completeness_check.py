"""Check the complete retained recovery-composition dataset, without simulation.

The CLI authenticates expected membership and certificates against fixed public
artifact hashes, then checks rows against those expectations. It composes the
existing pinned dynamics/coverage and policy-attribution verifiers. No network,
model/runner import, report file write, or modification of input files occurs.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import json
from pathlib import Path
import sys
import types

STUDY_ROOT = Path(__file__).resolve().parents[1]
SOURCE_COMMIT = '68d60a8b4fead07a024b1ecdb00a9875c161b36b'
EXPECTED_SHA256 = {
    'cases.json': 'b3c752d5184a5444307c5e693b90e93ed0cdc10cf23ba4da9f90e951f854f14c',
    'results-v1/run-input.json': 'd1ba837f43083f0b41d592b7b647150fcd6ab288d8dec88052469c70f9cec5ec',
    'results-v1/group-summaries.jsonl': '63ab8bba57c0bacda44a8411db6e19d50abb33dcdb7af78eb0b663c325638974',
    'results-v1/summary.json': 'acdb20e99ac705875f0d7d446ccc9721b34ae1f6b2d9d193f81aa09b7b467094',
    'results-v1/independent-recount.json': '9e95a90441551caed58f47134bcdb98eb74f2888767383b49db8fa700af2697f',
    'protocol.json': 'd7f3b680664ed630057d8091f20388011847ea387867f4a5d3980ef4b5945786',
}
VERIFIER_SHA256 = {
    'source/checker.py': '9751e07387d849ca8b99592ff7b655235d8596a226a06bd92a38095a7e5b8665',
    'policy-attribution/policy_replay.py': '239e1313b82bc76c0f6cca461e68e07f7018e721008757b690136abe49d37a8d',
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        _require(key not in result, 'duplicate JSON key: ' + key)
        result[key] = value
    return result


def _nonfinite(value):
    raise ValueError('non-finite JSON number: ' + value)


def parse_json(text):
    """Reject ambiguous duplicate-key objects and non-standard numeric values."""
    return json.loads(text, object_pairs_hook=_unique_object, parse_constant=_nonfinite)


def _pinned_bytes(root, relative, expected):
    data = (Path(root) / relative).read_bytes()
    _require(hashlib.sha256(data).hexdigest() == expected,
             'pinned bytes mismatch: ' + relative)
    return data


def load_verifiers(study_root=None):
    """Execute only verified bytes, avoiding a hash-check/import-path race."""
    root = Path(study_root) if study_root is not None else STUDY_ROOT
    modules = []
    for relative, sha256 in VERIFIER_SHA256.items():
        data = _pinned_bytes(root, relative, sha256)
        module = types.ModuleType('pinned_' + Path(relative).stem)
        module.__file__ = str(root / relative)
        exec(compile(data, module.__file__, 'exec'), module.__dict__)
        modules.append(module)
    return tuple(modules)


def load_pinned_expectations(saved_root):
    """Read immutable expectations, independent of supplied row membership."""
    data = {path: _pinned_bytes(saved_root, path, sha)
            for path, sha in EXPECTED_SHA256.items()}
    cases = parse_json(data['cases.json'])
    run_input = parse_json(data['results-v1/run-input.json'])
    case_digest = hashlib.sha256(json.dumps(cases, sort_keys=True).encode()).hexdigest()
    _require(case_digest == run_input['cases_sha256'], 'run-input case digest mismatch')
    _require(len(cases) == run_input['case_count'], 'run-input case count mismatch')
    _require(hashlib.sha256(data['protocol.json']).hexdigest() == run_input['protocol_sha256'],
             'run-input protocol digest mismatch')
    return {
        'cases': cases,
        'policies': run_input['policies'],
        'group_summaries': [parse_json(line) for line in
                            data['results-v1/group-summaries.jsonl'].splitlines()],
        'summary': parse_json(data['results-v1/summary.json']),
        'recount': parse_json(data['results-v1/independent-recount.json']),
    }


def audit_rows(rows, cases, policies, group_summaries, summary, dynamics, attribution):
    """Validate rows against supplied expectations (not itself a provenance claim).

    Library callers own expectation/verifier provenance. The CLI always uses the
    pinned loaders. Rows may reorder groups or paths within a contiguous group;
    split/repeated groups and duplicate terminal traces are rejected.
    """
    case_map = {}
    for case in cases:
        case_id = case['id']
        _require(isinstance(case_id, str) and bool(case_id), 'invalid manifest case ID')
        _require(case_id not in case_map, 'duplicate manifest case: ' + case_id)
        case_map[case_id] = _canonical(case)
    _require(bool(case_map), 'empty case manifest')
    _require(all(isinstance(p, str) and p for p in policies) and bool(policies),
             'empty or invalid policy registration')
    _require(len(policies) == len(set(policies)), 'duplicate policy registration')
    expected = {(case_id, policy) for case_id in case_map for policy in policies}
    certificates = {}
    for certificate in group_summaries:
        key = (certificate['case_id'], certificate['policy'])
        _require(key not in certificates, 'duplicate group certificate: ' + repr(key))
        certificates[key] = certificate
    _require(set(certificates) == expected, 'certificate membership differs from case-policy product')

    groups = {}
    totals = defaultdict(Counter)
    row_counts = Counter()
    paths = states = decisions = 0

    def process(group):
        nonlocal paths, states, decisions
        if not group:
            return
        first = group[0]
        case = first['case']
        policy = first['policy']
        key = (case['id'], policy)
        _require(key not in groups, 'noncontiguous repeated group: ' + repr(key))
        certificate = certificates[key]
        traces = [_canonical(row['hidden_trace']) for row in group]
        _require(len(set(traces)) == len(traces), 'duplicate terminal scheduler trace: ' + repr(key))
        n = len(group)
        indices = [row['path_index'] for row in group]
        _require(all(type(i) is int for i in indices) and sorted(indices) == list(range(n)),
                 'invalid or duplicate path indices: ' + repr(key))
        _require(n == certificate['paths'], 'retained path count mismatch: ' + repr(key))
        for row in group:
            # Retained format: each row is one terminal path, not a group count.
            _require(type(row['scheduler_paths']) is int and row['scheduler_paths'] == 1,
                     'scheduler_paths mismatch: ' + repr(key))
            _require(type(row['states_explored']) is int
                     and row['states_explored'] == certificate['states'],
                     'states_explored mismatch: ' + repr(key))
            metrics = row['metrics']
            _require(all(type(metrics[k]) is bool for k in ('actual_complete', 'justified_complete')),
                     'invalid completion metric types')
            _require(all(type(metrics[k]) is int for k in
                         ('calls', 'return_time', 'duplicate_effects', 'post_return_duplicate_effects')),
                     'invalid count/time metric types')

        # The retained checker validates each row's causal dynamics and metrics
        # before its prefix-tree coverage result can be used or policy replay run.
        coverage = dynamics.validate_group(group)
        _require(_canonical(coverage) == _canonical(certificate['coverage']),
                 'coverage certificate mismatch: ' + repr(key))
        for row in group:
            decisions += attribution.validate_policy(row)['decisions_checked']
        metrics = [row['metrics'] for row in group]
        measured = {
            'case_id': case['id'], 'family': case['family'], 'policy': policy,
            'paths': n,
            'unsafe_paths': sum(m['duplicate_effects'] > 0 for m in metrics),
            'actual_complete_paths': sum(m['actual_complete'] for m in metrics),
            'justified_complete_paths': sum(m['justified_complete'] for m in metrics),
            'post_return_unsafe_paths': sum(m['post_return_duplicate_effects'] > 0 for m in metrics),
            'min_calls': min(m['calls'] for m in metrics),
            'max_calls': max(m['calls'] for m in metrics),
            'min_return': min(m['return_time'] for m in metrics),
            'max_return': max(m['return_time'] for m in metrics),
        }
        _require(_canonical(measured) == _canonical({k: certificate[k] for k in measured}),
                 'group metric mismatch: ' + repr(key))
        totals[case['family'] + '|' + policy].update({
            'cases': 1, 'paths': n,
            'unsafe_cases': int(measured['unsafe_paths'] > 0),
            'all_safe_cases': int(measured['unsafe_paths'] == 0),
            'all_actual_complete_cases': int(measured['actual_complete_paths'] == n),
            'any_actual_complete_cases': int(measured['actual_complete_paths'] > 0),
            'all_justified_cases': int(measured['justified_complete_paths'] == n),
            'post_return_unsafe_cases': int(measured['post_return_unsafe_paths'] > 0),
        })
        groups[key] = coverage
        paths += n
        states += certificate['states']
        row_counts[policy] += n

    current = []
    last = None
    for row in rows:
        case_id = row['case']['id']
        _require(_canonical(row['case']) == case_map.get(case_id), 'row case differs from manifest: ' + str(case_id))
        key = (case_id, row['policy'])
        _require(key in expected, 'unexpected case-policy group: ' + repr(key))
        if key != last:
            process(current)
            current = []
            _require(key not in groups, 'noncontiguous repeated group: ' + repr(key))
        current.append(row)
        last = key
    process(current)
    missing = expected - set(groups)
    _require(not missing, 'missing case-policy groups: ' + repr(sorted(missing)[:8]))
    measured_summary = {'groups': len(groups), 'paths': paths, 'states': states, 'totals': dict(totals)}
    _require(_canonical(measured_summary) == _canonical({k: summary[k] for k in measured_summary}),
             'aggregate recount mismatch')
    coverage_digest = hashlib.sha256(json.dumps(
        sorted((list(key), value) for key, value in groups.items()), sort_keys=True).encode()).hexdigest()
    return {
        'passed': True, 'cases': len(case_map), 'groups': len(groups), 'paths': paths,
        'decisions_checked': decisions, 'branch_nodes': sum(g['branch_nodes'] for g in groups.values()),
        'recorded_states_consistent': states, 'totals': dict(totals),
        'rows_per_policy': dict(row_counts), 'coverage_manifest_sha256': coverage_digest,
    }


def saved_rows(path):
    path = Path(path)
    opener = gzip.open if path.name.endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8') as stream:
        for number, line in enumerate(stream, 1):
            _require(bool(line.strip()), 'blank row at line ' + str(number))
            yield parse_json(line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('saved_root', type=Path, help='freshly reconstructed accepted study root')
    parser.add_argument('--study-root', type=Path, default=STUDY_ROOT,
                        help='published study containing the pinned dynamics and policy verifiers')
    parser.add_argument('--rows', type=Path, help='alternative JSONL or JSONL.gz to check against fixed expectations')
    args = parser.parse_args(argv)
    try:
        expected = load_pinned_expectations(args.saved_root)
        dynamics, attribution = load_verifiers(args.study_root)
        path = args.rows if args.rows is not None else args.saved_root / 'results-v1/rows.jsonl.gz'
        result = audit_rows(saved_rows(path), expected['cases'], expected['policies'],
                            expected['group_summaries'], expected['summary'], dynamics, attribution)
        recount = expected['recount']
        for key in ('groups', 'paths', 'totals', 'coverage_manifest_sha256'):
            _require(_canonical(result[key]) == _canonical(recount[key]),
                     'retained independent-recount mismatch: ' + key)
        result.update({
            'source_commit': SOURCE_COMMIT,
            'pinned_expectation_sha256': EXPECTED_SHA256,
            'pinned_verifier_sha256': VERIFIER_SHA256,
            'scope': 'complete retained case-policy membership, full case identity, unique scheduler paths, dynamics, branch coverage, policy attribution, group metrics and aggregates',
            'limits': [
                'Completeness is relative to the retained case manifest, registered policies and finite scheduler contract, not every possible real-world scenario.',
                'Recorded states are reconciled, not independently regenerated; omniscient_feasible is not rederived.',
                'No new simulation, policy efficacy result, production reliability result, or independent preregistration is established.',
                'The original dynamics checker and prior policy replay are reused after hash verification, not newly independent implementations.',
            ],
            'imports_simulator': False,
        })
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (OSError, EOFError, ValueError, KeyError, TypeError, IndexError) as error:
        print(json.dumps({'passed': False, 'error': str(error)}, sort_keys=True), file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
