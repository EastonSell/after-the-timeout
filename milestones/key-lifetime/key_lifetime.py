"""Logical-clock retention extension of the published stale-status simulator."""
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'stale-status' / 'workflow.py'
spec = importlib.util.spec_from_file_location('key_lifetime_baseline', SOURCE)
baseline = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = baseline
spec.loader.exec_module(baseline)
Denied, UnknownOutcome = baseline.Denied, baseline.UnknownOutcome
POLICIES = ('blind_retry', 'inspect_first', 'lifetime_guard')


def tick(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f'{name} must be a nonnegative integer')


@dataclass
class Service(baseline.Service):
    key_lifetime: int | None = None
    now: int = 0
    committed_at: dict = field(default_factory=dict, init=False)

    def __post_init__(self):
        super().__post_init__()
        if self.key_lifetime is not None:
            tick(self.key_lifetime, 'key_lifetime')
        tick(self.now, 'now')

    def advance(self, ticks):
        tick(ticks, 'ticks')
        self.now += ticks

    def write(self, operation_id):
        self.calls += 1
        if self.fault == 'denied':
            raise Denied('operation refused')
        first = operation_id not in self.seen
        self.seen.add(operation_id)
        if first and self.fault == 'before':
            raise UnknownOutcome('transport failed before commit')
        stored = self.committed_at.get(operation_id)
        retained = stored is not None and (
            self.key_lifetime is None or self.now < stored + self.key_lifetime)
        if not self.idempotent or not retained:
            self.records.append(operation_id)
            self.committed_at[operation_id] = self.now
        if first and self.fault == 'after':
            self.stale_reads_remaining[operation_id] = self.status_staleness
            raise UnknownOutcome('transport failed after commit')
        return 'committed'


def execute(service, policy, delay=0, operation_id='example-001'):
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    tick(delay, 'delay')
    attempted_at = service.now
    try:
        return service.write(operation_id)
    except Denied:
        return 'denied'
    except UnknownOutcome:
        service.advance(delay)
        if policy != 'blind_retry':
            state = service.status(operation_id)
            if state == 'committed':
                return state
            if policy == 'lifetime_guard':
                guaranteed = service.idempotent and (
                    service.key_lifetime is None or
                    service.now < attempted_at + service.key_lifetime)
                if not guaranteed:
                    return 'needs_reconciliation'
            elif state == 'unknown' and not service.idempotent:
                return 'needs_reconciliation'
        try:
            return service.write(operation_id)
        except Denied:
            return 'denied'
        except UnknownOutcome:
            return 'needs_reconciliation'
