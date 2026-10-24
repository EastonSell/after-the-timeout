"""Synthetic local service with actual SQLite effects and controllable fault gates.

This service is intentionally tiny and has no authentication. Bind loopback only.
It is an experimental apparatus, NOT a deployable or distributed service.
"""
import argparse
import hashlib
import json
import os
import sqlite3
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from common import Trace, write_json


class State:
    def __init__(self, root):
        self.root = Path(root)
        self.db = self.root / 'effects.sqlite3'
        self.trace = Trace(self.root / 'service.jsonl', 'service')
        self.commit_gate = threading.Event()
        self.reply_gate = threading.Event()
        self.guard = threading.Lock()
        self.active = 0
        self.cached = None
        with self.connect() as db:
            db.executescript('''
                CREATE TABLE effects(id INTEGER PRIMARY KEY, op TEXT NOT NULL, payload TEXT NOT NULL);
                CREATE TABLE attempts(op TEXT PRIMARY KEY, state TEXT NOT NULL, effect_id INTEGER);
                CREATE TABLE keys(key TEXT PRIMARY KEY, digest TEXT NOT NULL, effect_id INTEGER NOT NULL);
            ''')

    def connect(self):
        db = sqlite3.connect(self.db, timeout=3, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        return db

    def read(self, op='original', fence=False):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if fence:
                db.execute("UPDATE attempts SET state='cancelled' WHERE op=? AND state='pending'", (op,))
            row = db.execute('SELECT * FROM attempts WHERE op=?', (op,)).fetchone()
            count = db.execute('SELECT count(*) FROM effects').fetchone()[0]
            result = dict(op=op, operation_state=row['state'] if row else 'unknown',
                          terminal=bool(row and row['state'] != 'pending'), effect_count=count)
            db.commit()
        self.trace.emit('fence' if fence else 'authoritative_read', **result)
        return result

    def write(self, data):
        op = data['op']
        payload = json.dumps(data.get('payload', {'item': 'A', 'value': 1}), sort_keys=True, separators=(',', ':'))
        key = data.get('key')
        digest = hashlib.sha256(payload.encode()).hexdigest()
        with self.connect() as db:
            db.execute('INSERT INTO attempts VALUES (?, ?, NULL)', (op, 'pending'))
        self.trace.emit('admitted', op=op, key=key, payload=payload)
        if data.get('hold_commit'):
            self.trace.emit('commit_gate_wait', op=op)
            if not self.commit_gate.wait(10):
                raise TimeoutError('commit fault gate watchdog')
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = db.execute('SELECT state FROM attempts WHERE op=?', (op,)).fetchone()[0]
            effect_id = None
            http_status = 200
            if state == 'cancelled':
                event = 'suppressed'
            else:
                old = db.execute('SELECT digest, effect_id FROM keys WHERE key=?', (key,)).fetchone() if key is not None else None
                if old and old['digest'] != digest:
                    state, event, http_status = 'rejected', 'payload_conflict', 409
                elif old:
                    state, event, effect_id = 'deduplicated', 'deduplicated', old['effect_id']
                else:
                    effect_id = db.execute('INSERT INTO effects(op, payload) VALUES (?, ?)', (op, payload)).lastrowid
                    if key is not None:
                        db.execute('INSERT INTO keys VALUES (?, ?, ?)', (key, digest, effect_id))
                    state, event = 'committed', 'effect_committed'
                db.execute('UPDATE attempts SET state=?, effect_id=? WHERE op=?', (state, effect_id, op))
            db.commit()
        self.trace.emit(event, op=op, effect_id=effect_id, state=state)
        if data.get('hold_reply'):
            self.trace.emit('reply_gate_wait', op=op)
            if not self.reply_gate.wait(10):
                raise TimeoutError('response fault gate watchdog')
        return http_status, dict(op=op, state=state, effect_id=effect_id)


class Server(ThreadingHTTPServer):
    daemon_threads = False


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    @property
    def state(self):
        return self.server.state

    def respond(self, status, value):
        raw = json.dumps(value).encode()
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError) as exc:
            self.state.trace.emit('reply_disconnected', exception=type(exc).__name__)

    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/read':
            self.respond(200, self.state.read(parse_qs(parsed.query).get('op', ['original'])[0]))
        elif parsed.path == '/cached':
            value = dict(self.state.cached)
            self.state.trace.emit('cached_read', **value)
            self.respond(200, value)
        elif parsed.path == '/inspect':
            with self.state.connect() as db:
                attempts = [dict(r) for r in db.execute('SELECT * FROM attempts ORDER BY op')]
                effects = [dict(r) for r in db.execute('SELECT * FROM effects ORDER BY id')]
                keys = [dict(r) for r in db.execute('SELECT * FROM keys ORDER BY key')]
            with self.state.guard:
                active = self.state.active
            self.respond(200, dict(attempts=attempts, effects=effects, keys=keys, active=active))
        else:
            self.respond(404, {'error': 'not found'})

    def do_POST(self):
        data = json.loads(self.rfile.read(int(self.headers.get('Content-Length', '0'))) or b'{}')
        path = urlsplit(self.path).path
        if path == '/write':
            with self.state.guard:
                self.state.active += 1
            try:
                status, value = self.state.write(data)
                self.respond(status, value)
            except Exception as exc:
                self.state.trace.emit('handler_error', error=type(exc).__name__, detail=str(exc), op=data.get('op'))
                self.respond(500, {'error': type(exc).__name__})
            finally:
                self.state.trace.emit('handler_finished', op=data.get('op'))
                with self.state.guard:
                    self.state.active -= 1
        elif path == '/snapshot':
            value = self.state.read()
            row = self.state.trace.emit('snapshot_taken', effect_count=value['effect_count'])
            self.state.cached = dict(effect_count=value['effect_count'], snapshot_mono_ns=row['mono_ns'])
            self.respond(200, self.state.cached)
        elif path == '/fence':
            self.respond(200, self.state.read(data.get('op', 'original'), fence=True))
        elif path == '/release':
            self.state.trace.emit('gates_released')
            self.state.commit_gate.set()
            self.state.reply_gate.set()
            self.respond(200, {'released': True})
        elif path == '/shutdown':
            self.respond(200, {'stopping': True})
            threading.Thread(target=self.server.shutdown).start()
        else:
            self.respond(404, {'error': 'not found'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('root', type=Path)
    args = parser.parse_args()
    state = State(args.root)
    server = Server(('127.0.0.1', 0), Handler)
    server.state = state
    state.trace.emit('server_ready', address='127.0.0.1', port=server.server_port)
    write_json(args.root / 'ready.json', {'host': '127.0.0.1', 'port': server.server_port, 'pid': os.getpid()})
    server.serve_forever(poll_interval=0.01)
    server.server_close()
    state.trace.emit('server_stopped')


if __name__ == '__main__':
    main()
