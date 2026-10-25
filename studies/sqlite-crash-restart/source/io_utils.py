"""Bounded, exclusive JSON artifacts and append-only per-process receipts."""
import json
import os
import time
from pathlib import Path


def write_once(path, value):
    raw = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    with Path(path).open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class Trace:
    def __init__(self, root, actor, nonce):
        self.path = Path(root) / f'{actor}.jsonl'
        self.actor, self.nonce = actor, nonce

    def emit(self, event, **fields):
        row = dict(event=event, actor=self.actor, nonce=self.nonce, pid=os.getpid(),
                   mono_ns=time.monotonic_ns(), utc_ns=time.time_ns(), **fields)
        with self.path.open('a') as stream:
            stream.write(json.dumps(row, sort_keys=True, allow_nan=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        return row
