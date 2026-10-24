"""Small JSONL recorder shared by apparatus processes; no simulated clock."""
import json
import os
import threading
import time
from pathlib import Path


class Trace:
    def __init__(self, path, role):
        self.path = Path(path)
        self.role = role
        self.lock = threading.Lock()

    def emit(self, event, **fields):
        with self.lock:
            row = dict(event=event, role=self.role, pid=os.getpid(),
                       thread=threading.get_ident(), mono_ns=time.monotonic_ns(),
                       utc_ns=time.time_ns(), **fields)
            with self.path.open('a', encoding='utf-8') as file:
                file.write(json.dumps(row, sort_keys=True) + '\n')
        return row


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
