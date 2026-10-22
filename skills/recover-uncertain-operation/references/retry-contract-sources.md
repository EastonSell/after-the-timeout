# Retry-contract source grounding

Primary documentation checked October 22, 2026. These are examples of differing
contracts, not a universal API specification. Check the actual service,
endpoint/version, scope and documented lifetime before applying a retry basis.

- [RFC 9110 §9.2.2: Idempotent Methods](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2): distinguishes repeated requests' intended effects from incidental effects and permits retry of idempotent methods after a lost response. A caller key is not a universal prerequisite. Apply the actual operation's effect and concurrency/precondition contract; the verb alone does not establish those application guarantees.
- [DynamoDB read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html): eventual reads can omit recently completed writes; strong reads reflect prior successful writes. The page also distinguishes reading committed values from preventing later modifications. Inference: freshness and the original operation's terminality are separate questions. An absent-effect snapshot alone cannot rule out a later effect from an unfinished original. This is conservative reasoning, not a claimed universal operation-status contract.
- [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests): API v1 saves results after execution starts, can replay errors, compares retry parameters and can treat a pruned key as new work. Validation failures and concurrent conflicts do not save an idempotent result in that v1 flow. API v2 has different recovery semantics. This supports checking the actual endpoint/version, retention, payload, concurrency and error behavior. No Stripe retention duration is generalized to other services.
- [AWS Builders' Library: Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): explains caller-provided request identity, atomic association of identity with effects, semantically equivalent responses, late arrivals and changed intent. Retention requirements vary across services/resources. This motivates verifying that the original used the identifier and that its contract covers overlapping or late requests, rather than assuming any matching key string provides unconditional protection.

The requirement for authoritative fresh terminal no-effect evidence is an explicit
conservative retry criterion. These sources illustrate why a weaker observation
may not suffice; none establishes that an arbitrary service offers that criterion.
Documentation cannot grant authorization for external actions.

## Provenance and evidence level

This canonical correction incorporates the freshness/finality and key-contract
checks from the [historical stale-status proposal](../../../milestones/stale-status/skill-revision/recover-uncertain-operation/SKILL.md),
while preserving the canonical content-addressed Git section. The proposal's
status text, experiments, outputs and manifests remain historical records, not
measurements of this correction.

The [authored regression expectations](regression-examples.md) are review inputs
and an answer key. The accompanying package tests check local links, retained
content, coverage and evidence labels only. Neither is an agent execution study;
no claim of improved behavioral reliability, latency or token cost follows.
