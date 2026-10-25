# Independent PRE-DATA review request

Review the frozen package before any actual process-crash execution. The author
has run only synthetic, in-process correctness/receipt fixtures and the existing
seven-suite historical aggregate. No service subprocess, signal, endpoint, or
empirical matrix was run. The runner's end-to-end crash lifecycle remains
unexecuted; synthetic success must not be presented as measured crash behavior.

Please return ADMIT or HOLD with exact blockers and bind the decision to the
SHA-256 of `PRE_DATA_FREEZE.json`. Do not execute the matrix as part of this review.
Do not publish or modify old packages. If proposing fixes, report them first so
the author can preserve this freeze and prepare a new one for renewed review.

Review questions:

1. Is the derivative's file/receipt IPC scope clear enough to avoid implying an
   HTTP timeout result or unchanged historical service?
2. Do the barriers truly establish a kill before calling COMMIT versus after its
   return, without implying a kill inside COMMIT or disk/power durability?
3. Does the restarted store preserve committed rows and reject incompatible
   schema rather than wiping or automatically replaying pending operations?
4. Are effect, key, and terminal attempt state in one transaction, with the
   original admission explicitly separate? Are payload conflicts handled only
   when a retained binding actually exists?
5. Does the driver wait for owned-process SIGKILL exit before retaining the crash
   image and launching the recovery process? Is cleanup bounded and complete?
6. Is one fixed recovery write applied without conditioning the policy on the
   audit snapshot? Are key retention and absence of competing writers explicit?
7. Are exact request identity, source identity, PID/nonce, event order, original
   response absence, restart snapshot, and final SQL independently checked?
8. Do 24 planned rows and 6 cells of 4 remain visible under failures, invalid
   schedules, budget abort, and not-run rows? Are contrary outcomes retained?
9. Is the pre-commit conflict control correctly reported as B accepted and A
   incomplete, rather than equating a single final effect/status 200 with success?
10. Are bounds honest about cooperative I/O deadlines and the inter-row output
    threshold? Is there any unintended installation, credential, network endpoint,
    historical mutation, external sharing, or permission expansion?
11. Does the code/protocol need a correction before data? If so, HOLD. Once data
    are admitted and collected, failures cannot be replaced in this denominator.

The prior excluded fresh-fixed-matrix remains unchanged and out of scope.
Post-data evidence and interpretation will require a separate independent review
before publication. PRE-DATA admission alone is not publication authorization.
