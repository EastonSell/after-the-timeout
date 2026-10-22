"""Deterministic offline lost-reply simulation, not a client or live-service claim.

Run from the repository root: python docs/examples/lost_reply.py
Atomic calls, one sequential caller, explicit logical time, no in-flight work.
"""


class LostReply(Exception):
    """The caller observes the same message before and after a hidden commit."""


class ToyService:
    """The operation ID is a key ONLY when this toy service promises deduplication.

    lifetime=None retains keys indefinitely. A finite key expires at
    now >= commit time + lifetime; a cache hit does not renew it. Durable effects
    survive expiry. These are chosen simulator rules, not real API guarantees.
    """

    def __init__(self, deduplicates=True, lifetime=None):
        if type(deduplicates) is not bool:
            raise ValueError("deduplicates must be a boolean")
        if lifetime is not None and (type(lifetime) is not int or lifetime <= 0):
            raise ValueError("lifetime must be a positive integer or None")
        self.deduplicates = deduplicates
        self.lifetime = lifetime
        self.effects = []  # Evaluator-only ground truth, unavailable in a lost reply.
        self._keys = {}
        self._last_time = 0

    def submit(self, operation_id, payload, *, now, lose=None):
        if type(now) is not int or now < self._last_time:
            raise ValueError("Use nondecreasing nonnegative logical time")
        if lose not in (None, "before", "after"):
            raise ValueError("lose must be None, before, or after")
        if not isinstance(operation_id, str) or not operation_id:
            raise ValueError("Provide a nonempty operation ID")
        if not isinstance(payload, str) or not payload:
            raise ValueError("Provide a nonempty payload")
        self._last_time = now
        if lose == "before":
            raise LostReply("reply unavailable")
        cached = self._keys.get(operation_id) if self.deduplicates else None
        if cached is not None:
            original_payload, result, expires = cached
            if expires is None or now < expires:
                if payload != original_payload:
                    raise ValueError("Retained key conflicts with a different payload")
                if lose == "after":
                    raise LostReply("reply unavailable")
                return result
        self.effects.append((operation_id, payload))
        result = len(self.effects)
        if self.deduplicates:
            expires = None if self.lifetime is None else now + self.lifetime
            self._keys[operation_id] = (payload, result, expires)
        if lose == "after":
            raise LostReply("reply unavailable")
        return result


def main():
    print("SYNTHETIC CONTRACTS ONLY: no real write, live API, or model evaluation")
    cases = (
        ("ID only, no deduplication", False, None, "after"),
        ("Durable deduplication contract", True, None, "after"),
        ("Key expires at retry time", True, 1, "after"),
        ("Initial request failed before commit", False, None, "before"),
    )
    for label, deduplicates, lifetime, fault in cases:
        service = ToyService(deduplicates=deduplicates, lifetime=lifetime)
        try:
            service.submit("op-1", "add A", now=0, lose=fault)
        except LostReply as error:
            observation = str(error)
        service.submit("op-1", "add A", now=1)
        print(f"{label}: caller first sees '{observation}'; hidden final effects={len(service.effects)}")
    print("The observation alone cannot tell the caller whether the first write committed.")
    print("Inspect service-specific evidence and retention contracts; preserve unknown when neither resolves it.")


if __name__ == "__main__":
    main()
