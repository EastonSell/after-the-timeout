"""Synthetic SQLite contract, derived from the historical local-process service.

This module has no process launch, signal handling, or network endpoints.
Hooks surround db.commit(), not SQLite's internal durability/linearization point.
"""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

SCHEMA = {
    'effects': 'CREATE TABLE effects(id INTEGER PRIMARY KEY, op TEXT NOT NULL, payload TEXT NOT NULL)',
    'attempts': 'CREATE TABLE attempts(op TEXT PRIMARY KEY, state TEXT NOT NULL, effect_id INTEGER)',
    'keys': 'CREATE TABLE keys(key TEXT PRIMARY KEY, digest TEXT NOT NULL, effect_id INTEGER NOT NULL)',
}
APPLICATION_ID = 0x41545432


def canonical(payload):
    text = json.dumps(payload, sort_keys=True, separators=(',', ':'), allow_nan=False)
    if len(text.encode()) > 1024:
        raise ValueError('payload exceeds 1024 bytes')
    return text


class Store:
    def __init__(self, path):
        self.path = Path(path)
        existing = self.path.exists()
        with closing(sqlite3.connect(self.path, timeout=2, isolation_level=None)) as db:
            if existing:
                actual = dict(db.execute("SELECT name, sql FROM sqlite_master WHERE type='table'"))
                if (actual != SCHEMA or db.execute('PRAGMA application_id').fetchone()[0] != APPLICATION_ID
                        or db.execute('PRAGMA user_version').fetchone()[0] != 1):
                    raise ValueError('foreign or incompatible database; refusing migration/reset')
                if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
                    raise ValueError('only the frozen DELETE journal mode is supported')
            else:
                db.execute('PRAGMA journal_mode=DELETE')
                db.execute('PRAGMA synchronous=FULL')
                db.execute('BEGIN IMMEDIATE')
                try:
                    for sql in SCHEMA.values():
                        db.execute(sql)
                    db.execute(f'PRAGMA application_id={APPLICATION_ID}')
                    db.execute('PRAGMA user_version=1')
                    db.commit()
                except BaseException:
                    db.rollback()
                    raise

    def connect(self):
        db = sqlite3.connect(self.path, timeout=2, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA synchronous=FULL')
        if db.execute('PRAGMA journal_mode').fetchone()[0] != 'delete':
            db.close()
            raise ValueError('journal mode changed')
        return db

    def snapshot(self):
        with closing(self.connect()) as db:
            db.execute('BEGIN')
            result = {name: [dict(row) for row in db.execute(f'SELECT * FROM {name} ORDER BY 1')]
                      for name in SCHEMA}
            result['integrity'] = [row[0] for row in db.execute('PRAGMA integrity_check')]
            result['journal_mode'] = db.execute('PRAGMA journal_mode').fetchone()[0]
            result['synchronous'] = db.execute('PRAGMA synchronous').fetchone()[0]
            db.commit()
        return result

    def write(self, op, payload, key=None, hook=None):
        if not isinstance(op, str) or not op or len(op) > 64:
            raise ValueError('invalid operation id')
        if key is not None and (not isinstance(key, str) or not key or len(key) > 128):
            raise ValueError('invalid key')
        body = canonical(payload)
        digest = hashlib.sha256(body.encode()).hexdigest()
        # Admission is durable separately, just as in the historical service.
        # A pending row after a crash is NOT a terminal-absence certificate.
        with closing(self.connect()) as db:
            db.execute('INSERT INTO attempts VALUES (?, ?, NULL)', (op, 'pending'))
            db.execute('BEGIN IMMEDIATE')
            try:
                old = db.execute('SELECT * FROM keys WHERE key=?', (key,)).fetchone() if key is not None else None
                if old and old['digest'] != digest:
                    state, status, effect_id = 'rejected', 409, None
                elif old:
                    state, status, effect_id = 'deduplicated', 200, old['effect_id']
                else:
                    effect_id = db.execute('INSERT INTO effects(op, payload) VALUES (?, ?)', (op, body)).lastrowid
                    if key is not None:
                        db.execute('INSERT INTO keys VALUES (?, ?, ?)', (key, digest, effect_id))
                    state, status = 'committed', 200
                db.execute('UPDATE attempts SET state=?, effect_id=? WHERE op=?', (state, effect_id, op))
                if hook:
                    hook('before_commit')
                db.commit()
                if hook:
                    hook('after_commit')
            except BaseException:
                db.rollback()  # No effect after COMMIT; normal exceptions are not SIGKILL.
                raise
        return {'op': op, 'state': state, 'status': status, 'effect_id': effect_id}
