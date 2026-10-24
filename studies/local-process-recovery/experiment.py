"""Bounded local process experiment. No random scheduler or in-memory effect model."""
import argparse
import hashlib
import json
import os
import platform
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from common import Trace, write_json
from client import rpc
from verify import verify_trial

HERE = Path(__file__).resolve().parent
SCENARIOS = ('no_fault', 'live_negative', 'stale_negative', 'same_key', 'terminal_fence',
             'terminal_with_stale_read', 'terminal_with_authoritative_read', 'concurrent_recoverers')
HELD_COMMIT = ('live_negative', 'same_key', 'terminal_fence', 'concurrent_recoverers')


class App:
    def __init__(self, root):
        self.root = Path(root)
        self.trace = Trace(self.root / 'driver.jsonl', 'driver')
        self.deadline = time.monotonic() + 10
        self.children = []
        self.files = []
        stderr = (self.root / 'service-stderr.txt').open('w')
        self.files.append(stderr)
        self.process = subprocess.Popen([sys.executable, '-B', str(HERE / 'service.py'), str(self.root)],
                                        stdout=subprocess.DEVNULL, stderr=stderr)
        self.trace.emit('service_spawned', server_pid=self.process.pid)
        self.waitfor(lambda: (self.root / 'ready.json').exists())
        ready = json.loads((self.root / 'ready.json').read_text())
        self.port = ready['port']

    def remaining(self):
        value = self.deadline - time.monotonic()
        if value <= 0:
            raise TimeoutError('trial watchdog')
        return value

    def waitfor(self, condition):
        while not condition():
            self.remaining()
            if self.process.poll() is not None:
                raise RuntimeError(f'service exited {self.process.returncode}')
            time.sleep(0.002)

    def call(self, method, path, data=None):
        result = rpc(self.port, self.trace, method, path, data, min(3, self.remaining()))
        if result.get('http_status') != 200:
            raise RuntimeError(f'{path}: {result}')
        return result['body']

    def client(self, actor, data, timeout=3, recoverer=False):
        stderr = (self.root / f'{actor}-stderr.txt').open('w')
        self.files.append(stderr)
        args = [sys.executable, '-B', str(HERE / 'client.py'), str(self.port), str(self.root), actor, str(timeout), json.dumps(data)]
        if recoverer:
            args.append('--recoverer')
        process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=stderr)
        self.children.append(process)
        self.trace.emit('client_spawned', actor=actor, client_pid=process.pid)
        return process

    def join(self, process):
        code = process.wait(timeout=min(3, self.remaining()))
        if code:
            raise RuntimeError(f'client exited {code}')

    def close(self):
        if self.process.poll() is None:
            try:
                rpc(self.port, self.trace, 'POST', '/release', {})
                rpc(self.port, self.trace, 'POST', '/shutdown', {})
                self.process.wait(timeout=3)
            except Exception as exc:
                self.trace.emit('cleanup_terminated', error=type(exc).__name__)
                self.process.terminate()
                self.process.wait(timeout=3)
        for process in self.children:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=3)
        for file in self.files:
            file.close()
        self.trace.emit('service_exit', returncode=self.process.returncode)


def run_trial(scenario, out, timeout):
    if scenario not in SCENARIOS:
        raise ValueError(scenario)
    out = Path(out)
    out.mkdir()  # Exclusive output: never overwrite evidence.
    write_json(out / 'case.json', dict(scenario=scenario, socket_timeout_s=timeout))
    app = App(out)
    try:
        app.call('POST', '/snapshot', {})
        data = dict(op='original', hold_commit=scenario in HELD_COMMIT,
                    hold_reply=scenario != 'no_fault' and scenario not in HELD_COMMIT)
        if scenario == 'same_key':
            data['key'] = 'intent-A'
        original = app.client('original', data, timeout)
        app.join(original)
        observed = json.loads((out / 'original-result.json').read_text())
        app.trace.emit('original_outcome_observed', outcome=observed)
        retry = None
        if scenario == 'live_negative':
            evidence = app.call('GET', '/read')
            if evidence['effect_count'] == 0:
                retry = dict(op='retry')
        elif scenario == 'stale_negative':
            evidence = app.call('GET', '/cached')
            if evidence['effect_count'] == 0:
                retry = dict(op='retry')
        elif scenario == 'same_key':
            retry = dict(op='retry', key='intent-A')
        elif scenario == 'terminal_fence':
            evidence = app.call('POST', '/fence', {})
            if evidence['terminal'] and evidence['effect_count'] == 0:
                retry = dict(op='retry')
        elif scenario == 'terminal_with_stale_read':
            terminal = app.call('GET', '/read')
            evidence = app.call('GET', '/cached')
            if terminal['terminal'] and evidence['effect_count'] == 0:
                retry = dict(op='retry')
        elif scenario == 'terminal_with_authoritative_read':
            evidence = app.call('GET', '/read')
            if evidence['terminal'] and evidence['effect_count'] == 0:
                retry = dict(op='retry')
        elif scenario == 'concurrent_recoverers':
            app.call('POST', '/fence', {})
            clients = [app.client(actor, {'op': actor}, recoverer=True) for actor in ('recovery1', 'recovery2')]
            app.waitfor(lambda: all((out / f'{actor}-observed.json').exists() for actor in ('recovery1', 'recovery2')))
            app.trace.emit('recoverer_barrier_release')
            (out / 'release-recoverers').touch()
            for process in clients:
                app.join(process)
        app.trace.emit('policy_decision', action='retry' if retry else 'no_driver_retry', request=retry)
        if retry:
            app.call('POST', '/write', retry)
        app.call('POST', '/release', {})
        def drained():
            current = app.call('GET', '/inspect')
            return current['active'] == 0 and all(r['state'] != 'pending' for r in current['attempts'])
        app.waitfor(drained)
        write_json(out / 'final-service-read.json', app.call('GET', '/inspect'))
    finally:
        app.close()
    result = verify_trial(out, scenario)
    write_json(out / 'result.json', result)
    return result


def source_manifest():
    files = sorted([*HERE.glob('*.py'), HERE / 'PROTOCOL.md', HERE / 'PLAN.md', HERE / 'PREIMPLEMENTATION.sha256'])
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


def run_matrix(out):
    out = Path(out)
    out.mkdir()
    started = time.monotonic()
    manifest = dict(utc_ns=time.time_ns(), source=source_manifest(), base_commit='bb7c59a61f95575edbd3c90719f69dffa1dfd5db',
                    environment=dict(python=sys.version, sqlite=sqlite3.sqlite_version, platform=platform.platform()),
                    plan=dict(scenarios=list(SCENARIOS), timeouts=[0.08, 0.12, 0.20], repetitions=5, planned_trials=120))
    write_json(out / 'frozen-input.json', manifest)
    rows = []
    for timeout in (0.08, 0.12, 0.20):
        for repeat in range(5):
            for scenario in SCENARIOS:
                number = len(rows)
                trial = out / f'trial-{number:03d}-{scenario}'
                row = dict(trial=trial.name, scenario=scenario, socket_timeout_s=timeout, repetition=repeat)
                if time.monotonic() - started > 120:
                    row.update(status='not_run', violations=['primary_watchdog'])
                else:
                    try:
                        result = run_trial(scenario, trial, timeout)
                        row.update(status='pass' if not result['violations'] else 'failed', **result)
                    except Exception as exc:
                        row.update(status='invalid', violations=[f'{type(exc).__name__}: {exc}'])
                rows.append(row)
                with (out / 'trials.jsonl').open('a') as file:
                    file.write(json.dumps(row, sort_keys=True) + '\n')
                print(f"{number + 1}/120 {scenario}: {row['status']}", flush=True)
    size = sum(p.stat().st_size for p in out.rglob('*') if p.is_file())
    summary = dict(planned=120, recorded=len(rows), passed=sum(r['status']=='pass' for r in rows),
                   failed=sum(r['status']=='failed' for r in rows), invalid=sum(r['status']=='invalid' for r in rows),
                   not_run=sum(r['status']=='not_run' for r in rows), elapsed_s=time.monotonic()-started, bytes=size,
                   source_unchanged=source_manifest()==manifest['source'], output_cap_ok=size<=30_000_000,
                   by_scenario={s: dict(trials=sum(r['scenario']==s for r in rows), passed=sum(r['scenario']==s and r['status']=='pass' for r in rows),
                                             effect_counts=[r.get('effect_count') for r in rows if r['scenario']==s]) for s in SCENARIOS})
    write_json(out / 'summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    summary = run_matrix(args.out)
    print(json.dumps(summary, indent=2))
    raise SystemExit(0 if summary['passed']==120 and summary['source_unchanged'] and summary['output_cap_ok'] else 1)


if __name__ == '__main__':
    main()
