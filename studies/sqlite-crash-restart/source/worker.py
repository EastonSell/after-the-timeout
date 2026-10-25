"""One local service-process lifetime; no sockets and no automatic restart replay.

Do not invoke before independent PRE-DATA admission. The runner owns SIGKILL.
The only request is a bounded local JSON file produced by the admitted runner.
"""
import argparse
import resource
import sqlite3
import sys
import time
from pathlib import Path
from apparatus import Store
from io_utils import Trace, write_once
import json


def run(root, actor, nonce, barrier):
    deadline = time.monotonic() + 2
    while not (root / f'{actor}-start').exists():
        if time.monotonic() >= deadline:
            raise TimeoutError('driver startup handshake missing')
        time.sleep(0.002)
    trace = Trace(root, actor, nonce)
    store = Store(root / 'effects.sqlite3')
    initial = store.snapshot()
    write_once(root / f'{actor}-before.json', initial)
    trace.emit('ready', sqlite_version=sqlite3.sqlite_version, python=sys.version,
               journal_mode=initial['journal_mode'], synchronous=initial['synchronous'])
    request = json.loads((root / f'{actor}-request.json').read_text())
    trace.emit('request_received', request=request)

    def hook(phase):
        trace.emit(phase, op=request['op'])
        if barrier == phase:
            receipt = trace.emit('barrier_reached', phase=phase, op=request['op'])
            # Fully write a temporary receipt, then publish by rename: the driver
            # never accepts an incomplete JSON document as a crash barrier.
            temporary = root / f'{actor}-barrier.tmp'
            write_once(temporary, receipt)
            temporary.rename(root / f'{actor}-barrier.json')
            time.sleep(10)
            trace.emit('barrier_watchdog_expired')
            raise TimeoutError('driver did not kill service at the admitted barrier')

    response = store.write(request['op'], request['payload'], request.get('key'), hook)
    trace.emit('response_ready', response=response)
    write_once(root / f'{actor}-response.json', response)
    trace.emit('worker_finished')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    parser.add_argument('actor', choices=['original', 'recovery'])
    parser.add_argument('nonce')
    parser.add_argument('--barrier', choices=['none', 'before_commit', 'after_commit'], default='none')
    args = parser.parse_args()
    resource.setrlimit(resource.RLIMIT_CPU, (5, 5))
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (1024 * 1024,) * 2)
    run(args.root, args.actor, args.nonce, args.barrier)


if __name__ == '__main__':
    main()
