# Routing partial-batch recovery

This entry extends the [public capability catalog](public-capabilities.md) with an
original offline example. It describes required contracts, not an inventory of
installed plugins and not a promise that a named API supplies these guarantees.

| Required interface evidence | Why it changes recovery | If absent |
|---|---|---|
| Stable item identities and unchanged payloads | Tie each retry to the intended original item | Reconstruct the item ledger before mutating |
| Per-item results with reliable positive evidence | Preserve successful items rather than replaying the entire batch | Keep the item's outcome unknown |
| Authoritative terminal per-item negative | Establish that an item neither committed nor can commit later | Missing entries and stale negatives remain unknown |
| Documented per-item idempotency through the full execution horizon | Permit retry of an uncertain item without additional side effects under that contract | Do not treat a batch request identifier as sufficient |
| Final item acknowledgement or independent read | Support a completion report at item granularity | Report unresolved items rather than aggregate success |

Route a timed-out single write to [recover-uncertain-operation](../skills/recover-uncertain-operation/SKILL.md).
Route a multi-item operation with mixed or missing item results to
[recover-partial-batch](../skills/recover-partial-batch/SKILL.md).
The latter preserves the original authorized scope and does not authorize retries,
compensation, new credentials or additional interfaces by itself.

The [partial-commit study](../milestones/partial-commit/README.md) compares four
explicit deterministic policies on a finite synthetic case grid. Its declared
contracts exclude late original execution and finite key expiry; those hazards
remain covered separately in the existing late-commit and key-lifetime studies.
No model behavior, real plugin compatibility, production rates or universal
exactly-once guarantee is inferred from simulator tests. Public vendor capability
claims must still be checked against the specific interface's documentation and
actually exposed schema before use.

For research tooling, route a runner that might discard falsified predictions or
overwrite previous evidence to
[retain-experiment-evidence](../skills/retain-experiment-evidence/SKILL.md).
Its local regression examples cover failed predictions, exclusive output and
incremental retention under injected interruption. This is an evidence-handling
capability, not an API integration or behavioral efficacy result.
