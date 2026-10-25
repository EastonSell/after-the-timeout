# SQLite crash/restart protocol v1

Prepared 2026-10-25, before empirical data from this apparatus. Status: PRE-DATA,
pending independent review. Source, protocol, and analysis must be frozen and
admitted together. Authorized review decides execution and publication, not this file.

## Question and scope

When an original write's service process is killed at either of two explicit
barriers surrounding SQLite COMMIT, what remains after reopening the database,
and what happens when one recovery write reuses the retained key, has no key, or
reuses the key with a changed payload?

This is a bounded implementation demonstration on one Linux host with synthetic
data. Unlike the historical HTTP study, communication here is by local files and
process receipts. A response withheld by killing its worker is a lost reply, not
a measured network timeout. No socket or external endpoint is used.

## Derivation and alternatives

The historical service admits an operation in a separate autocommit statement,
then writes its effect, key, and terminal attempt state in one SQLite transaction.
Its startup uses unconditional CREATE TABLE statements. We preserve that entire
study rather than silently changing its source or replaying its historical rows.

Options considered: (1) modify the historical server, which would blur evidence
identity; (2) copy and extend its HTTP/fault endpoints, which adds unnecessary
transport and shutdown races to this narrow question; (3) a separate process/file
derivative retaining its SQL contract. This preparation chooses (3). That is an
engineering design choice, not evidence of equivalence to the HTTP transport.
The difference must remain prominent in any later report.

The new store creates a versioned schema only for a new database. Reopening
requires the exact table schema, application ID, and version; incompatible
databases are refused without migration/reset. SQLite journal mode is explicitly
DELETE and synchronous is FULL on each writing connection. No key expiry,
eviction, concurrent writer, background queue, or automatic resumption exists.

SQLite documents rollback-journal atomic commit and the separate meanings of
journal mode and synchronous settings. Those documents motivate this controlled
setup, but do not prove this host's power-loss durability or our implementation:
https://www.sqlite.org/atomiccommit.html
https://www.sqlite.org/pragma.html#pragma_synchronous
https://www.sqlite.org/pragma.html#pragma_journal_mode

## Hypotheses, matrix, and literal predictions

`protocol.json` is the authoritative ordered case list. It fixes 2 barrier phases
× 3 recovery modes × 4 repetitions = 24 planned trials, with 4 in each of 6 cells.
Order: repetition, before then after COMMIT, then no-key, same-key, conflict.
There is no random sampling, adaptive allocation, outcome-based early stop, or
replacement. Repetitions are engineering checks, not independent incident draws.

Original operation: ID `original`, payload A = {item: A, value: 1}. Recovery ID:
`recovery`. The request's key is null in no-key mode and K in both keyed modes.
Same-key recovery sends A. Conflict recovery sends B = {item: A, value: 2} with K.
The canonical payload digest and key/effect binding are committed atomically.

Before-COMMIT predictions, all 3 modes (12 planned):
- Restart sees zero effects and zero keys, with original state still pending.
- No-key and same-key recovery each commits A once; status 200.
- Conflict recovery commits B once; status 200, not 409. There is no retained
  binding to A because that transaction did not commit. The original intended A
  is NOT completed. A key protects its first committed binding, not an intention
  that never committed. This is a control, not a successful recovery claim.

After-COMMIT predictions (12 planned):
- Restart sees the original committed effect A. Keyed modes also retain K→A.
- No-key recovery appends a second A: 2 effects and 2 copies of A, status 200.
- Same-key recovery returns the original effect ID without adding an effect:
  1 effect A, state deduplicated, status 200.
- Conflict recovery returns 409/rejected, leaves A and K unchanged, and adds no B.

These are implementation-specific hypotheses, not presupposed pass criteria for
discarding rows. The protocol retains valid contrary outcomes as prediction
failures. In particular, 1 effect is not automatically task completion, and
status 200 is not automatically correct recovery of A.

## Objective barriers and crash semantics

1. Each trial uses a fresh directory, fresh SQLite file, unique nonce, and fixed
   case/request files. All artifacts use exclusive creation. Each writer gets
   its own OS process; at most one writer process lives at any moment.
2. The driver records the child PID and releases a startup file handshake.
3. The original process initializes the database and records a startup snapshot,
   then admits the original operation as pending in a separate transaction.
4. For `before_commit`, a hook runs after effect/key/state SQL statements within
   BEGIN IMMEDIATE but before `db.commit()` is called. For `after_commit`, the
   hook runs after `db.commit()` has returned, before a response can be written.
5. The selected hook appends and fsyncs a barrier event, writes/fsyncs a nonce,
   actor, PID, and phase receipt, atomically renames that receipt into view, then
   blocks for up to 10 seconds. Receipt timestamps are not database commit times.
6. The driver validates the exact receipt, records kill_requested, sends SIGKILL
   to that owned child, and waits for an actual -9 exit before doing anything
   else with the database. The process cannot execute further writes after exit.
7. After exit, the driver copies both database and journal bytes if present to
   retained crash-image names, before any SQLite open can perform recovery.
8. A distinct recovery process reopens the same original database path. It records
   its recovered snapshot, then performs exactly one recovery write. The original
   pending row, if any, is not resumed, cancelled, or converted into a certificate.
9. After the recovery process has exited 0, the driver rereads SQLite independently.
   The checker separately copies and reopens the retained crash image in a new
   temporary directory to check the pre-recovery snapshot without altering it.
10. The original emits no response receipt. The recovery has one complete response
    receipt. Three distinct PIDs, exact requests, nonce agreement, configuration,
    monotonic per-process traces, and the cross-process barrier→kill→exit→restart
    →response→exit→final-read sequence are required.

These barriers deliberately EXCLUDE a kill *during* the SQLite commit call. No
claim locates SQLite's internal linearization point or samples the window around
it continuously. SIGKILL kills one application process, not the OS, filesystem,
disk cache, or power supply. FULL is recorded, not interpreted as power-loss proof.

## Recovery policy and observation boundary

The policy is deliberately fixed: after confirmed original-process death and
restart, issue exactly one request with the predeclared payload/key mode. It does
not inspect the recovery snapshot to decide whether to retry. That snapshot is
an audit measurement, not a policy advantage. Same-key mode preserves the same
synthetic key and canonical payload outside the crashed service process.

The driver retains the key/request files; it does not itself crash. Client key
loss, two recoverers, concurrent independent writers, replicas, and automatic
queue replay are excluded. Original process death is established by process
reaping, not by elapsed quiet time. After recovery exit, no worker remains to
append a later effect within this apparatus. That is a process-lifecycle fact,
not a remote service guarantee or a general quiescence theorem.

## Measurements, denominators, and fixed analysis

Save every planned row before execution and preserve every attempted artifact:
request bytes, nonce, process receipts, stdout/stderr, database/journal crash
image, reopened snapshot, response, final database, independent SQL read, row
classification, timing, environment versions, code/protocol copies, admission,
and SHA-256 output manifest. Actual effects come from SQL, never predictions.

Report, overall out of 24 and within each cell out of 4:
- attempted and not-run counts;
- valid/pass and valid/prediction-failure counts;
- invalid schedule/lifecycle/incomplete-measurement counts and exact reasons;
- raw final effect counts, count of A, whether A is present at least once,
  whether A occurs exactly once, excess effects over one, status, and key state.

Valid means the schedule and measurement chain were established. A wrong count,
payload, key binding, attempt state, or response is a valid prediction failure,
not an invalid row to exclude. Invalid schedules and unreadable evidence remain
in the planned denominator. Missing rows are never silently dropped. The full
auditor checks case identity, raw receipts, saved versus independent SQL reads,
all planned IDs, summary totals, and exact output-file hashes. Readable database
integrity-check failures are prediction failures; unreadable SQL is a disclosed
invalid measurement. No aggregate can rescue an individual falsifying trace.

No confidence intervals, significance tests, production incident estimates,
causal population effects, comparison to language models, or "100% safe" claim.
Report the six selected schedules and each literal denominator. A concrete
observed duplicate can demonstrate a failure for this implementation/schedule;
24 passing rows cannot establish general crash safety.

## Resource budget and stopping rules

- Fixed 24 rows, sequential; at most one service worker plus the driver.
- Linux, existing Python standard library only; no installation or new access.
- Per trial: 12-second cooperative deadline, barrier acquisition at most 4s,
  kill/reap at most 2s, recovery wait at most 4s; barrier watchdog 10s.
- Global: 180-second cooperative run deadline; each blocking worker wait is
  clamped to the remaining trial/global budget. Cleanup may take another 2s.
  File I/O, SQLite opening/auditing, and kernel stalls are not hard real-time
  guaranteed. A supervising operator may stop an unresponsive driver; retain all
  partial files and do not count that as a completed matrix.
- Each worker: 5 CPU seconds, 512 MiB address-space limit, 1 MiB per-file limit.
  Fixed requests contain only short synthetic payloads (API cap 1024 bytes).
- Output: 32 MiB abort threshold checked between rows, including frozen source
  copies. This is an inter-row threshold, not a filesystem quota; the current
  trial/cleanup/terminal bookkeeping can overshoot. No artifacts are truncated or
  deleted to hit the threshold. File-size resource-limit failures are retained.
- Infrastructure failure invalidates that row but does not replace it. Continue
  the fixed plan unless the global time/output bound or an unreaped child makes
  further execution unsafe. Remaining rows become not-run with the reason.
- A scientifically contrary but valid row never stops the plan. No rerun or
  changed hypothesis may be inserted into the original denominator.

## Admission, exclusions, and interpretation

Independent PRE-DATA review must examine source/protocol/analysis together,
including the deliberately narrower IPC transport, recovery policy, boundaries,
complete denominator, and honest limitations of synthetic testing. Admission is
bound to `PRE_DATA_FREEZE.json` bytes. There is no admission in this package.

Any post-freeze correction needs a new freeze and review. If data have already
been collected, preserve them as a separate failed/earlier version, do not
replace, relabel, or merge them into v1. Independent post-data review must audit
raw evidence before any final interpretation or publication.

All historical packages are unchanged. The prior unreviewed `fresh-fixed-matrix`
is excluded from this protocol and any claims. It was not used to choose values,
effects, schedules, or stopping rules. There is no new empirical result here.
