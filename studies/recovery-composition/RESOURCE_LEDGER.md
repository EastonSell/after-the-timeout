# Resource ledger and execution scope

Exact machine-readable ledger: results-v1/resource-ledger.json.

Main frozen run:
- 800 cases, 3,200 case-policy groups, 319,968 explored states.
- 86,796 complete scheduler paths; 274,828,679 uncompressed row bytes.
- Compressed retained rows: 6,000,978 bytes.
- 72.5380463959882 seconds elapsed; 72.50987749800001 CPU seconds.
- Peak RSS 23,428 KiB; one process; Python 3.12.14, Linux x86_64.
- Started 2026-10-22T23:38:08.664732+00:00; finished
  2026-10-22T23:39:21.202764+00:00.

Separate saved-output recount, importing no simulator/policy code:
- Same 3,200 groups and 86,796 paths reconstructed and checked.
- 25.31178535700019 seconds elapsed; peak RSS 30,904 KiB; one process.
- Exact coverage manifest hash is in results-v1/independent-recount.json.

Predeclared caps: 100,000 states per case/policy, 10,000,000 total states,
600 seconds elapsed and 500,000,000 uncompressed output bytes. No cap was reached.
A cap crossing is an incomplete failed run, never an early successful result.

Tests and post-hoc probes ran separately in single standard-library Python
processes. Their individual command outputs are retained; exact supplemental CPU
and peak-memory values were not instrumented, so they are not presented as zero.
The final 18-test suite took 0.172 seconds in the fresh recorded test output.

All calculations used zero network requests, real API calls, model inference
calls, device actions, installs, credentials, payments or external writes. These
counts describe the experiment/probes, not the assistant's own orchestration cost.
All effects and costs in the model are declared hypothetical logical units.
