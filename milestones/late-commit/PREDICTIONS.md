# Pre-run predictions: delayed original commits

Saved before implementing or executing this follow-on. One deterministic run per
cell: original outcome absent/late; status supported/unsupported; retention
unlimited/1 tick; recovery delay 0/1/2/3; four policies. Total 128 cells (32 per
policy). Original late commit is scheduled for tick 2. Due events run before any
status/read/write at that tick; ties follow insertion order. Deduplication is
checked atomically at commit, not reserved on admission. Cached keys expire at
now >= committed_at + retention. A suppressed event does not renew retention.

Policies blind_retry, inspect_first and lifetime_guard reuse the preceding
study's implementation. wait_terminal is a stronger-contract control: wait for
the known original completion bound (tick 2), then inspect fresh durable state;
retry only if status confirms absence after the bound. Unsupported status stays
unresolved. This bound is supplied as a model contract, not inferred from silence.
Every run drains original events before final metrics, including after a policy
already returned. Record both immediate and settled commit counts.

Predicted extra commits after settling:
- blind_retry: 6/32, late + finite retention, delay 0/1/3, either status mode.
- inspect_first: 5/32, late + finite retention, supported delay 0/1 and
  unsupported delay 0/1/3.
- lifetime_guard: 2/32, late + finite retention, delay 0, either status mode.
- wait_terminal: 0/32.

Predicted unresolved policy outcomes: 0, 0, 10, 16 respectively. The guard's
10 comprise six absent-original cells (finite retention, delay 1/2/3, either
status), one late supported cell (finite, delay 1), and three late unsupported
cells (finite, delay 1/2/3). wait_terminal leaves every unsupported-status cell
unresolved, including cases that eventually commit. No denial mode is included.

Predicted deferred duplicates (not yet visible when policy returns): 4, 4, 2, 0
respectively. All unlimited-retention cells have zero extra commits. A fresh
negative at tick 0 or 1 describes present absence, not impossibility of a future
commit. The lifetime guard can fail despite retrying within its retention window
because the original arrives after that retry's cache expires.

These are consequences of a constructed model, not real-world rates, a vendor
contract or an independent agent evaluation. The checksum records local pre-run
ordering only, not externally timestamped preregistration.
