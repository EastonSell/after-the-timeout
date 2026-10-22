# Examples and review cases

These are synthetic examples. The suggested revisions are illustrative, not required strings. Facts supplied in each case are assumed true for that case.

## Before and after

1. Empty contrast
   - Before: “I'll check the logs, rather than make guesses about the failure.”
   - After: “I'll check the logs.”
   - Preserve: the commitment to inspect the logs. The second clause adds no useful boundary.

2. Invented restriction
   - Context: The user requested a full comparison; no word limit was given.
   - Before: “I can only give you a brief overview, so here's a quick summary.”
   - After: “Here's the comparison.”
   - Preserve: the requested scope in the actual answer. Changing the introduction alone does not make an incomplete comparison complete.

3. Meaningful distinction
   - Before: “The fix stops new duplicates; it does not remove existing duplicates.”
   - After: unchanged.
   - Preserve: both effects. “The fix resolves duplicates” would mislead.

4. Real blocker
   - Context: The connected account is read-only.
   - Before: “I can draft the cancellation request, but I can't submit it from this read-only account.”
   - After: “This account is read-only. I can draft the cancellation request.”
   - Preserve: inability to submit and the offer to draft. Either version is acceptable.

5. Uncertainty
   - Before: “It's important to note that the drop may reflect fewer weekend orders, although the sample is small.”
   - After: “The drop may reflect fewer weekend orders, but the sample is small.”
   - Preserve: possible explanation and limited evidence.

6. Commitment and condition
   - Before: “I'll review the logs tomorrow at 09:00 UTC, not restart the service without your approval.”
   - After: “I'll review the logs tomorrow at 09:00 UTC. I'll ask for your approval before restarting the service.”
   - Preserve: scheduled review and approval condition. This does not promise a restart or an approval request if no restart is needed.

7. Attribution and code
   - Before: “The guide says, ‘Do not retry failed payments.’ Keep `if not approved: return` unchanged. It's worth noting that both safeguards matter.”
   - After: “The guide says, ‘Do not retry failed payments.’ Keep `if not approved: return` unchanged. Both safeguards matter.”
   - Preserve: quotation and code exactly, including negation.

8. Answer before ceremony
   - Before: “Great question! Let's dive into the key takeaway: the export contains 18 records.”
   - After: “The export contains 18 records.”
   - Preserve: count and completed-export status.

## Independent evaluation

Give an evaluator the skill and the following prompts without the suggested revisions above. Ask for the rewritten text and a short account of what meaning they preserved.

A. Rewrite: “I'll compare the options, not force everything into a single recommendation.” Context: the reader asked for a comparison, with no restriction on recommendations.

B. Rewrite: “The trial reduced latency in this sample, but it did not establish a production reliability improvement.”

C. Rewrite: “I can prepare the upload. The service is offline, so I can't upload the file yet.”

D. Rewrite: “The outage may be related to the deploy. I'll inspect the logs on Friday at 14:00 UTC, and I won't roll back without approval.”

E. Rewrite only the surrounding prose: “It's important to note that the label reads ‘Do not disconnect.’ The check is `if not connected: stop()`. These details are not optional.”

F. Rewrite: “The detector flagged this paragraph, which proves it was written by AI.”

Review each output for:
- Useful facts, uncertainty, conditions, commitments, and exact quoted/code content retained.
- No invented restriction, permission, capability, deadline, or completed action.
- Unnecessary ceremony reduced without introducing another repeated formula.
- Meaningful negation retained in B–E; unsupported certainty corrected in F. Correcting that false claim is an accuracy correction, not merely a style edit.

Accept multiple phrasings and unchanged text where appropriate. A fluent rewrite that loses meaning fails review. These cases are manual evaluation fixtures, not an automated test suite or evidence that a model consistently follows the skill. Passing them would not establish general writing quality or human authorship.
