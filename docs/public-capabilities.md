# Public capability catalog

Checked 2026-10-21. This catalog describes vendor-published interfaces, not any user's installed integrations or account access. A public API capability does not guarantee that a particular plugin exposes it. Permissions, available methods and schema versions must be checked at execution time. All rows below are documentation-reviewed; no live mutations were performed for this catalog.

| Service/interface | Published capability | Useful workflow | Boundary / observable evidence | Primary source |
|---|---|---|---|---|
| GitHub REST repositories | Create repositories for an authenticated user or organization | Establish an explicitly requested public research repository | Verify owner, name, visibility and returned repository; required scopes depend on credential type | https://docs.github.com/en/rest/repos/repos |
| Google Drive v3 uploads | Create/update file content through media, multipart or resumable uploads | Deliver a generated document and recover from interrupted uploads | Use supported upload mode; verify resulting metadata/size and access separately | https://developers.google.com/workspace/drive/api/guides/manage-uploads |
| Slack Web API | Send messages and return a message timestamp | Deliver an approved result to an identified conversation | Inspect application-level `ok`, conversation identity, scope errors and message reference | https://docs.slack.dev/reference/methods/chat.postmessage |
| Google Calendar v3 | List calendar events, including paginated event resources | Check a bounded time window before scheduling | Distinguish recurring events, visibility and continuation tokens; listing is not a scheduling action | https://developers.google.com/workspace/calendar/api/v3/reference/events/list |
| Figma REST file endpoints | Retrieve file/node information | Inspect a design's source structure before implementation | File access and read scope are separate from file-edit capability | https://developers.figma.com/docs/rest-api/file-endpoints/ |
| Figma REST dev resources | Create/read/update/delete development references | Connect design nodes to implementation references | Dev-resource writes are not arbitrary canvas editing | https://developers.figma.com/docs/rest-api/dev-resources-endpoints/ |
| MCP tools | Discover schemas, invoke tools and interpret tool-level errors | Match a task to an actually exposed tool | Protocol success and tool success are different; annotations alone are not trusted authorization | https://modelcontextprotocol.io/specification/2025-11-25/server/tools |
| JSON-RPC 2.0 | Correlate request IDs with responses/errors | Validate generic client-server envelopes | A correlation ID does not imply deduplication or exactly-once execution | https://www.jsonrpc.org/specification |
| Agent Skills format | Package task instructions with optional scripts/references/assets | Reuse a tested workflow with discoverable metadata | Format validation does not measure behavioral reliability | https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx |

## Capability routing
1. Discover the actual exposed operation and schema. Keep the distinction between vendor API, plugin wrapper and authenticated session.
2. If an operation is absent, check an already authorized interface with the necessary capability. For example, a service's existing authenticated web UI may expose an operation absent from its connector. This does not justify creating credentials or broadening access.
3. After an approved operation, verify the resulting object through an independent read when available. Return to structured APIs for subsequent steps where they are more precise.
4. Treat missing capability, denied access, uncertain outcome, schema mismatch and transient failure as different states. Choose recovery from evidence rather than the error's tone.

## Original skill index
| Skill | Trigger | Artifact | Validation completed | Remaining evidence |
|---|---|---|---|---|
| recover-uncertain-operation | A write timed out and commit status is unknown | Reconciliation decision | Format check; offline policy invariants in ten tests | Independent LLM runs, stale status, real service-specific guarantees |
| plainspoken-writing | Conversational prose obscures meaning with formulaic style | Revised text preserving scope and truth | Format check; twenty synthetic fixtures | Blinded multi-run human evaluation, factual preservation scoring |

## Research citation matrix
| Reference | What it contributes | What this repository tests | What remains untested |
|---|---|---|---|
| AgentBench, https://arxiv.org/abs/2308.03688 | Evaluating agents across interactive environments | Small deterministic workflow failure cases | LLM reasoning and cross-environment task success |
| τ-bench, https://arxiv.org/abs/2406.12045 | Stateful tool interaction and consistency evaluation | Final committed state versus reported outcome | User dialogue, domain policy compliance, repeated model-run consistency |
| Public MCP/JSON-RPC specifications above | Interface contracts and errors | Simplified outcome/pagination contracts | Wire-compatible MCP server/client implementation |

Expansion criterion: add an entry when a primary public reference establishes the capability and an example improves a real decision. Add a behavioral claim only with a reproducible test and stated environment. Do not copy proprietary skill bodies or authenticated account inventories.
