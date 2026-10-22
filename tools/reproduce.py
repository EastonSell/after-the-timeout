"""Version 1 safe wrapper: run preserved study sources in a temporary copy."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STUDIES = {
    'baseline': '.',
    'stale-status': 'milestones/stale-status',
    'key-lifetime': 'milestones/key-lifetime',
    'late-commit': 'milestones/late-commit',
}


def source_files(study):
    if study not in STUDIES:
        raise ValueError('Unknown study')
    folder = Path(STUDIES[study])
    files = [folder/'run_experiment.py']
    if study in ('baseline', 'stale-status'):
        files += [folder/'workflow.py', folder/'config.json']
    else:
        files += [Path('milestones/stale-status/workflow.py'),
                  Path('milestones/key-lifetime/key_lifetime.py')]
        if study == 'late-commit':
            files.append(folder/'late_commit.py')
    if study != 'baseline':
        files += [folder/'PREDICTIONS.md', folder/'PREDICTIONS.sha256']
    return files


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def reproduce(study, output, root=ROOT):
    root = Path(root).resolve(strict=True)
    output = Path(output).absolute()
    # Reject existing targets, including broken symlinks, before executing anything.
    if output.exists() or output.is_symlink():
        raise ValueError('Output already exists; choose a new directory')
    resolved = output.resolve(strict=False)
    if resolved == root or root in resolved.parents:
        raise ValueError('Output must be outside the source repository')
    if not output.parent.is_dir():
        raise ValueError('Output parent must already exist')
    sources = source_files(study)
    with tempfile.TemporaryDirectory(prefix='atlas-reproduce-') as directory:
        copied = Path(directory)/'source'
        hashes = {}
        for relative in sources:
            source = root/relative
            if source.is_symlink() or not source.is_file():
                raise ValueError(f'Missing or symlinked study source: {relative}')
            target = copied/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            # Hash the exact copied bytes, not a second read of a mutable source.
            target.write_bytes(source.read_bytes())
            hashes[str(relative)] = sha256(target)
        work = copied/STUDIES[study]
        (work/'results').mkdir(exist_ok=True)
        result = subprocess.run([sys.executable, 'run_experiment.py'], cwd=work,
                                capture_output=True, text=True, check=False)
        if result.returncode:
            raise RuntimeError(f'Study failed with exit {result.returncode}: {result.stderr.strip()}')
        generated = sorted(p for p in (work/'results').iterdir() if p.is_file())
        if not generated:
            raise RuntimeError('Study produced no result files')
        manifest = dict(wrapper_version=1, study=study,
                        source_sha256=hashes,
                        output_sha256={p.name:sha256(p) for p in generated},
                        command=['python', 'run_experiment.py'],
                        limits='Sources are copied byte-for-byte; legacy entry points remain unsafe for direct historical reruns.')
        # Exclusive mkdir also prevents a concurrent process replacing an existing result.
        output.mkdir(exist_ok=False)
        for artifact in generated:
            shutil.copyfile(artifact, output/artifact.name)
        (output/'run.stdout.txt').write_text(result.stdout)
        (output/'run.stderr.txt').write_text(result.stderr)
        (output/'reproduction.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', choices=STUDIES, default='baseline')
    parser.add_argument('--out', required=True, help='New directory outside the repository; existing parent required')
    args = parser.parse_args()
    try:
        print(reproduce(args.study, args.out))
    except (ValueError, OSError, RuntimeError) as exc:
        print(f'Reproduction failed: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
