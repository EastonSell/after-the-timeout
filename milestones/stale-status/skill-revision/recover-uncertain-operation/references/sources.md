# Source grounding

Primary vendor documentation read on October 21, 2026. These are examples of contract differences, not universal specifications. Recheck the actual service's current endpoint/version contract before acting.

1. [DynamoDB read consistency](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html): eventual reads can omit recent successful writes; strong reads cover prior successful writes, while later modifications remain possible. This motivates separating observation freshness from the lifecycle of an unresolved operation. The rule that an in-flight request can still commit after an absent read is a conservative reasoning inference, not a quoted vendor promise about arbitrary operation-status APIs.
2. [Stripe idempotent requests](https://docs.stripe.com/api/idempotent_requests): API v1 records a response after execution starts and can replay errors; retained keys compare parameters, and a pruned key can initiate new work. API v2 has different retry semantics. This supports checking endpoint/version, key lifetime, payload equivalence, and error meaning rather than relying on the word “idempotent.” No Stripe-specific duration is made a general rule in the skill.
3. [AWS Builders' Library: Making retries safe with idempotent APIs](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/): discusses caller-supplied request identity, duplicate side effects, reconciliation ambiguity, atomic association of tokens with effects, late requests, and differences in intent. This motivates exact request identity and contract-specific limits, not an unconditional retry guarantee.

## Local evidence and boundaries

The sibling `stale-status` study is an offline counterexample: a one-read stale negative changes inspect-first from 0 to 3 duplicate commits across 16 scenarios in three shuffled orders, while a modeled permanent idempotency key prevents duplicates. The 22 simulator tests validate that model, not this skill's execution by an LLM. No independent model forward-test of this revised skill is claimed here.

The revision adds normative decision checks, not a new experimentally evaluated recovery policy. Authorization gates are preserved independently of the distributed-systems evidence. Vendor documentation cannot grant the agent permission to take external actions.
