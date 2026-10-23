# Retained authored-expectation corrections before the source freeze

No failed full-grid result was removed or rewritten. The first test run used
empty stubs: 13 intended missing-feature failures and one passing interface-shape
check are retained in logs/tests-red.txt. During implementation, three test
fixture assumptions were wrong under the already frozen protocol:

1. A batch CACHE entry is installed at attempt termination, not at the first
   partial effect. A proposed test expected early suppression before termination.
   The corrected unit case places termination at t=1 and requires at least one
   allowed ordering with suppression, rather than claiming all paths suppress.
2. A late original effect at t=3 is not strictly after a success reply/return at
   t=4. The stale-negative test still checks duplicates at t=3; a separate t=6
   original checks the post-return criterion. The initial failed expectation is
   retained in logs/tests-model-first.txt.
3. A metric-tampering test set justified_complete=True in a success case where it
   already was True. The corrected fixture uses a rejected recovery, so the
   mutation actually changes the metric. The failed expectation is retained in
   logs/tests-retention-red.txt.

These corrections aligned tests to the unchanged frozen semantics; they were not
policy or protocol changes selected after full-grid outcomes. Source, corrected
tests and all 800 inputs were then frozen before the main run. All 18 tests pass
in the fresh final log. The full-grid P5 failure remains in predictions.json.
