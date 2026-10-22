"""Synthetic partial-batch recovery. Public observations are separate from truth."""
from dataclasses import asdict, dataclass

ITEMS = ('a', 'b', 'c')
MODES = ('fresh', 'incomplete', 'stale_negative', 'unsupported')
POLICIES = ('blind_batch', 'missing_is_absent', 'evidence_only', 'capability_guard')


def validate_items(items):
    if len(set(items)) != len(items) or not set(items) <= set(ITEMS):
        raise ValueError('Items must be a unique subset of a, b, c')


@dataclass(frozen=True)
class Record:
    item: str
    state: str
    authoritative_terminal: bool


@dataclass(frozen=True)
class Observation:
    records: tuple
    status_supported: bool
    per_item_idempotency: bool


def make_observation(committed, mode, keyed):
    """Service-side adapter. Only its returned object is visible to the policy."""
    validate_items(committed)
    if mode not in MODES or type(keyed) is not bool:
        raise ValueError('Unknown status contract or non-boolean capability')
    if mode == 'unsupported':
        return Observation((), False, keyed)
    records = tuple(
        Record(item, 'committed' if item in committed else 'absent', True)
        for item in (('a',) if mode == 'incomplete' else ITEMS)
    )
    if mode == 'stale_negative':
        records = tuple(Record(item, 'absent', False) for item in ITEMS)
    return Observation(records, True, keyed)


def decide(policy, observation):
    """Return (retry items, unresolved items), using public evidence only."""
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    if policy == 'blind_batch':
        return ITEMS, ()
    records = {record.item: record for record in observation.records}
    retry, unresolved = [], []
    for item in ITEMS:
        record = records.get(item)
        if policy == 'missing_is_absent':
            if record is None or record.state != 'committed':
                retry.append(item)
            continue
        verified = record is not None and record.authoritative_terminal
        if verified and record.state == 'committed':
            continue
        if (verified and record.state == 'absent') or (
            policy == 'capability_guard' and observation.per_item_idempotency
        ):
            retry.append(item)
        else:
            unresolved.append(item)
    return tuple(retry), tuple(unresolved)


class Service:
    """Evaluator-owned simulator. Initial timeout is terminal, keys never expire."""
    def __init__(self, committed, keyed):
        validate_items(committed)
        if type(keyed) is not bool:
            raise ValueError('Non-boolean capability')
        self.counts = {item: int(item in committed) for item in ITEMS}
        self.keyed = keyed

    def retry(self, items):
        validate_items(items)
        for item in items:
            if not self.keyed or self.counts[item] == 0:
                self.counts[item] += 1
        return tuple(items)  # Complete successful per-item acknowledgement.


def execute(committed, mode, keyed, policy):
    observation = make_observation(committed, mode, keyed)
    service = Service(committed, keyed)
    # Blind retry performs no status read, so its evidence contains no records.
    if policy == 'blind_batch':
        observation = Observation((), mode != 'unsupported', keyed)
    retry, unresolved = decide(policy, observation)
    if retry:
        acknowledged = service.retry(retry)
        assert acknowledged == retry
    counts = service.counts
    return {
        'initial_committed': list(committed), 'status_mode': mode,
        'per_item_idempotency': keyed, 'policy': policy,
        'evidence': asdict(observation), 'retry_items': list(retry),
        'commit_counts': counts,
        'true_complete': all(count >= 1 for count in counts.values()),
        'exact_once_complete': all(count == 1 for count in counts.values()),
        'extra_side_effects': sum(max(count - 1, 0) for count in counts.values()),
        'duplicate_items': [item for item, count in counts.items() if count > 1],
        'reported_complete': not unresolved,
        'unresolved_items': list(unresolved), 'unresolved_count': len(unresolved),
        'api_calls': 1 + int(policy != 'blind_batch') + int(bool(retry)),
    }
