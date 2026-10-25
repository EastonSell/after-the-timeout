"""Gated 24-row process-crash matrix. PRE-DATA: do not execute before admission."""
import argparse
import json
import os
import platform
import secrets
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from assess import assess, read_evidence, sql_snapshot, summarize, cell_summaries
from guard import check_admission, reserve_output, sha256
from io_utils import Trace, write_once

ROOT = Path(__file__).resolve().parent


def output_bytes(root):
    return sum(path.stat().st_size for path in root.rglob('*') if path.is_file())


def trial(case, root, source, global_deadline):
    root.mkdir(exist_ok=False)
    started = time.monotonic()
    deadline = min(global_deadline, started + 12)
    nonce = secrets.token_hex(16)
    write_once(root / 'case.json', case)
    write_once(root / 'identity.json', {'nonce': nonce, 'driver_pid': os.getpid()})
    trace = Trace(root, 'driver', nonce)
    key = None if case['mode'] == 'no_key' else 'K'
    write_once(root / 'original-request.json', {'op': 'original', 'payload': {'item': 'A', 'value': 1}, 'key': key})
    write_once(root / 'recovery-request.json', {'op': 'recovery', 'payload': case['expected']['recovery_payload'], 'key': key})
    process, streams = None, []

    def remaining(cap):
        left = min(cap, deadline - time.monotonic())
        if left <= 0:
            raise TimeoutError('trial/global deadline')
        return left

    def launch(actor, barrier):
        nonlocal process
        stdout = (root / f'{actor}-stdout.txt').open('xb')
        stderr = (root / f'{actor}-stderr.txt').open('xb')
        streams.extend((stdout, stderr))
        process = subprocess.Popen([sys.executable, '-B', str(source / 'worker.py'), str(root), actor, nonce, '--barrier', barrier],
                                   stdout=stdout, stderr=stderr, cwd=source,
                                   env={'PYTHONDONTWRITEBYTECODE': '1', 'LANG': 'C.UTF-8'})
        trace.emit(f'{actor}_started', child_pid=process.pid)
        (root / f'{actor}-start').touch(exist_ok=False)
        return process

    result = None
    try:
        original = launch('original', case['phase'])
        barrier_path = root / 'original-barrier.json'
        barrier_deadline = min(deadline, time.monotonic() + 4)
        while not barrier_path.exists():
            if original.poll() is not None:
                raise RuntimeError(f'original exited before barrier: {original.returncode}')
            if time.monotonic() >= barrier_deadline:
                raise TimeoutError('barrier acquisition deadline')
            time.sleep(0.002)
        receipt = json.loads(barrier_path.read_text())
        if (receipt['pid'] != original.pid or receipt['nonce'] != nonce or receipt['phase'] != case['phase']
                or receipt['event'] != 'barrier_reached' or receipt['actor'] != 'original'):
            raise ValueError('barrier identity mismatch')
        if original.poll() is not None:
            raise RuntimeError('original exited before driver kill')
        trace.emit('kill_requested', child_pid=original.pid)
        original.kill()
        returncode = original.wait(timeout=remaining(2))
        trace.emit('original_exit', child_pid=original.pid, returncode=returncode)
        if returncode != -signal.SIGKILL:
            raise RuntimeError('unexpected original exit')
        # No live writer. Preserve pre-recovery DB/journal bytes before SQLite
        # opens them, so normal recovery cannot erase the crash image evidence.
        for name in ('effects.sqlite3', 'effects.sqlite3-journal'):
            path = root / name
            if path.exists():
                shutil.copyfile(path, root / f'crash-{name}')
        recovery = launch('recovery', 'none')
        code = recovery.wait(timeout=remaining(4))
        trace.emit('recovery_exit', child_pid=recovery.pid, returncode=code)
        if code != 0:
            raise RuntimeError(f'recovery exited {code}')
        write_once(root / 'final-sql.json', sql_snapshot(root / 'effects.sqlite3'))
        trace.emit('final_read')
        result = assess(case, read_evidence(root))
    except Exception as exc:
        trace.emit('trial_error', error=type(exc).__name__, detail=str(exc))
        result = {'classification': 'invalid', 'validity_errors': [f'{type(exc).__name__}: {exc}'], 'prediction_errors': []}
    finally:
        if process is not None and process.poll() is None:
            trace.emit('cleanup_kill', child_pid=process.pid)
            process.kill()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                # Do not continue to another trial with an unconfirmed live child.
                raise RuntimeError('cleanup could not reap worker; stop entire run')
        for stream in streams:
            stream.close()
    result.update(id=case['id'], elapsed_s=time.monotonic()-started)
    write_once(root / 'result.json', result)
    return result


def execute(out, approval, source=ROOT):
    # All checks precede output creation and process launch.
    review = check_admission(source, approval)
    if sys.platform != 'linux':
        raise ValueError('frozen experiment requires Linux SIGKILL/resource semantics')
    provenance = json.loads((source / 'SOURCE_PROVENANCE.json').read_text())
    target = Path(out).resolve()
    for protected in provenance['historical_roots']:
        if target.is_relative_to(Path(protected).resolve()):
            raise ValueError('output cannot be inside a protected historical source/evidence tree')
    out = reserve_output(out, source).resolve()
    write_once(out / 'admission.json', review)
    frozen = out / 'source'
    frozen.mkdir()
    manifest = json.loads((source / 'PRE_DATA_FREEZE.json').read_text())
    for name in list(manifest['files']) + ['PRE_DATA_FREEZE.json']:
        target = frozen / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    check_admission(frozen, out / 'admission.json')
    spec = json.loads((frozen / 'protocol.json').read_text())
    if len(spec['matrix']) != 24:
        raise ValueError('wrong fixed denominator')
    plan = spec['matrix']
    write_once(out / 'planned.json', plan)
    write_once(out / 'environment.json', {'python': sys.version, 'sqlite': sqlite3.sqlite_version,
               'platform': platform.platform(), 'kernel': platform.release(),
               'freeze_sha256': sha256(frozen / 'PRE_DATA_FREEZE.json'), 'pid': os.getpid()})
    started = time.monotonic()
    deadline, rows, stop_reason = started + 180, [], None
    for case in plan:
        if time.monotonic() >= deadline:
            stop_reason = stop_reason or 'global deadline reached'
        if output_bytes(out) >= 32 * 1024 * 1024:
            stop_reason = stop_reason or 'output abort threshold reached'
        if stop_reason:
            root = out / case['id']
            root.mkdir()
            write_once(root / 'case.json', case)
            row = {'id': case['id'], 'classification': 'not_run', 'reason': stop_reason}
            write_once(root / 'result.json', row)
        else:
            try:
                row = trial(case, out / case['id'], frozen, deadline)
            except Exception as exc:
                stop_reason = f'unrecoverable lifecycle failure: {type(exc).__name__}: {exc}'
                row = {'id': case['id'], 'classification': 'invalid', 'validity_errors': [stop_reason], 'prediction_errors': []}
                # A partial trial is preserved even when its terminal row cannot be saved.
                path = out / case['id'] / 'result.json'
                if not path.exists():
                    write_once(path, row)
        rows.append(row)
    write_once(out / 'rows.json', rows)
    summary = summarize(plan, rows)
    summary['cells'] = cell_summaries(plan, rows)
    summary.update(elapsed_s=time.monotonic()-started, output_bytes=output_bytes(out), stop_reason=stop_reason,
                   interpretation='Selected local-process schedules only; no efficacy, provider, or power-loss claim.')
    write_once(out / 'summary.json', summary)
    write_once(out / 'OUTPUT_SHA256.json', {str(p.relative_to(out)): sha256(p) for p in sorted(out.rglob('*')) if p.is_file()})
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--admission', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = execute(args.out, args.admission)
    except Exception as exc:
        print(f'NOT COMPLETED: {type(exc).__name__}: {exc}', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0 if result['valid_pass'] == 24 else 1


if __name__ == '__main__':
    raise SystemExit(main())
