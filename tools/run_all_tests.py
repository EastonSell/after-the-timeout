"""Run every maintained suite in an isolated interpreter and its required cwd."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SUITES = (
    ('baseline', '.', 'tests'),
    ('stale-status', 'milestones/stale-status', 'tests'),
    ('key-lifetime', 'milestones/key-lifetime', 'tests'),
    ('late-commit', 'milestones/late-commit', 'tests'),
    ('checkpoint-handoff', '.', 'milestones/checkpoint-handoff/tests'),
    ('handoff-review', '.', 'milestones/handoff-review/tests'),
    ('release-tools', '.', 'tests/release'),
)


def run_all(root=ROOT):
    failed = []
    for name, cwd, discovery in SUITES:
        print(f'\n=== {name} ===', flush=True)
        result = subprocess.run([sys.executable, '-m', 'unittest', 'discover',
                                 '-s', discovery, '-v'], cwd=Path(root)/cwd, check=False)
        if result.returncode:
            failed.append(name)
    print(f'\nSuites: {len(SUITES)-len(failed)}/{len(SUITES)} passed', flush=True)
    if failed:
        print('Failed: '+', '.join(failed), flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(run_all())
