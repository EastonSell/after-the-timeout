"""Bounded stale-negative-status extension of the immutable baseline model."""
from dataclasses import dataclass, field

class Denied(Exception):
    pass

class UnknownOutcome(Exception):
    pass

@dataclass
class Service:
    fault: str = 'none'
    status_supported: bool = True
    idempotent: bool = False
    calls: int = 0
    records: list = field(default_factory=list)
    seen: set = field(default_factory=set)
    status_staleness: int = 0
    stale_reads_remaining: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        if self.fault not in ('none', 'before', 'after', 'denied'):
            raise ValueError('Unknown fault')
        if type(self.status_staleness) is not int or self.status_staleness not in (0, 1):
            raise ValueError('status_staleness must be integer 0 or 1')

    def write(self, operation_id):
        self.calls += 1
        if self.fault == 'denied':
            raise Denied('operation refused')
        first = operation_id not in self.seen
        self.seen.add(operation_id)
        if first and self.fault == 'before':
            raise UnknownOutcome('transport failed before commit')
        if not self.idempotent or operation_id not in self.records:
            self.records.append(operation_id)
        if first and self.fault == 'after':
            self.stale_reads_remaining[operation_id] = self.status_staleness
            raise UnknownOutcome('transport failed after commit')
        return 'committed'

    def status(self, operation_id):
        self.calls += 1
        if not self.status_supported:
            return 'unknown'
        if self.stale_reads_remaining.get(operation_id, 0):
            self.stale_reads_remaining[operation_id] -= 1
            return 'not_committed'
        return 'committed' if operation_id in self.records else 'not_committed'


def execute(service, policy, operation_id='example-001'):
    if policy not in ('blind_retry', 'inspect_first'):
        raise ValueError('Unknown policy')
    try:
        return service.write(operation_id)
    except Denied:
        return 'denied'
    except UnknownOutcome:
        if policy == 'inspect_first':
            state = service.status(operation_id)
            if state == 'committed':
                return state
            if state == 'unknown' and not service.idempotent:
                return 'needs_reconciliation'
        try:
            return service.write(operation_id)
        except Denied:
            return 'denied'
        except UnknownOutcome:
            return 'needs_reconciliation'


def read_all(fetch, max_pages=100):
    """Unchanged baseline pagination behavior, retained for equivalence tests."""
    cursor = None
    seen = set()
    rows = []
    for _ in range(max_pages):
        page = fetch(cursor)
        rows.extend(page['items'])
        cursor = page.get('next_cursor')
        if cursor is None:
            return rows
        if cursor in seen:
            raise ValueError('Cursor loop')
        seen.add(cursor)
    raise ValueError('Page budget exhausted')
