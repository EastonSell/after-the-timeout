# Recovery skill revision proposal

Status: locally drafted and structurally validated; not published or installed. The original published skill and stale-status experiment remain unchanged.

## Changes

- Replaces the ambiguous “confirmed non-commit” shortcut with an explicit contract: exact request, authoritative fresh evidence, terminal no-effect state, and no remaining possibility that the original attempt commits later.
- Separates freshness from finality. Stale negatives, missing records, in-flight work, and partial effects remain unresolved unless a different valid recovery basis applies.
- Keeps a valid idempotency contract as a separate retry basis. Checks original use, endpoint/version, key scope, retention, payload equivalence, concurrency, and error semantics rather than describing idempotency as an unconditional guarantee.
- Preserves authorization as an independent gate. Known non-commit does not authorize changed scope or override cancellation, denial, or required approvals.
- Distinguishes confirmed effects and accepted work from completion of the entire requested workflow.
- Adds 16 synthetic regression examples, including positive retry cases to guard against overly conservative blanket refusal.

## Grounding and validation

Used the available skill-creator guidance and its `quick_validate.py`: `Skill is valid!`. Three current primary vendor sources are linked in `references/sources.md`, with service-specific limits separated from conservative reasoning inferences.

Structural validation checks frontmatter and package conventions only. The regression examples are authored expectations, not a passing behavioral test suite. The earlier simulator's 22 passing tests do not establish LLM adherence to this revision. Parent-led independent forward-testing and publication review remain necessary before making any behavioral-validation claim.

Package entrypoint: `recover-uncertain-operation/SKILL.md`.
