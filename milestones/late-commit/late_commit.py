"""Synthetic event queue: late completion is not a failed initial write."""
import heapq
import importlib.util
import sys
from dataclasses import dataclass, field
from pathlib import Path

SOURCE = Path(__file__).resolve().parents[1] / 'key-lifetime' / 'key_lifetime.py'
spec = importlib.util.spec_from_file_location('late_commit_prior', SOURCE)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
POLICIES = (*prior.POLICIES, 'wait_terminal')
COMPLETION_BOUND = 2


@dataclass
class Service(prior.Service):
    original_outcome: str = 'late'
    events: list = field(default_factory=list, init=False)
    sequence: int = field(default=0, init=False)
    trace: list = field(default_factory=list, init=False)

    def __post_init__(self):
        super().__post_init__()
        if self.original_outcome not in ('absent', 'late'):
            raise ValueError('Unknown original outcome')
        if self.fault != 'none' or self.status_staleness != 0:
            raise ValueError('This study requires no other fault or stale status')

    def schedule(self, at, operation_id):
        prior.tick(at, 'event time')
        if at < self.now:
            raise ValueError('Cannot schedule in the past')
        heapq.heappush(self.events, (at, self.sequence, operation_id))
        self.sequence += 1

    def commit(self, operation_id, origin):
        stored = self.committed_at.get(operation_id)
        retained = stored is not None and (
            self.key_lifetime is None or self.now < stored + self.key_lifetime)
        deduplicated = self.idempotent and retained
        if not deduplicated:
            self.records.append(operation_id)
            self.committed_at[operation_id] = self.now
        self.trace.append(dict(time=self.now, event=origin,
                               operation_id=operation_id, deduplicated=deduplicated))

    def advance(self, ticks):
        prior.tick(ticks, 'ticks')
        target = self.now + ticks
        while self.events and self.events[0][0] <= target:
            at, _, operation_id = heapq.heappop(self.events)
            self.now = at
            self.commit(operation_id, 'original_completion')
        self.now = target

    def drain(self):
        while self.events:
            self.advance(self.events[0][0] - self.now)

    def write(self, operation_id):
        self.advance(0)  # Due events precede client actions at the same tick.
        self.calls += 1
        first = operation_id not in self.seen
        self.seen.add(operation_id)
        if first:
            self.trace.append(dict(time=self.now, event='initial_timeout',
                                   operation_id=operation_id))
            if self.original_outcome == 'late':
                self.schedule(self.now + COMPLETION_BOUND, operation_id)
            raise prior.UnknownOutcome('initial response unavailable')
        self.commit(operation_id, 'retry_completion')
        return 'committed'

    def status(self, operation_id):
        self.advance(0)
        state = super().status(operation_id)
        self.trace.append(dict(time=self.now, event='status', state=state,
                               operation_id=operation_id))
        return state


def execute(service, policy, delay=0, operation_id='example-001'):
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    prior.tick(delay, 'delay')
    if policy != 'wait_terminal':
        return prior.execute(service, policy, delay, operation_id)
    attempted_at = service.now
    try:
        return service.write(operation_id)
    except prior.UnknownOutcome:
        # Known completion bound is a stronger service contract, not a timeout guess.
        service.advance(max(delay, COMPLETION_BOUND))
        assert service.now >= attempted_at + COMPLETION_BOUND
        state = service.status(operation_id)
        if state == 'committed':
            return state
        if state == 'unknown':
            return 'needs_reconciliation'
        return service.write(operation_id)
