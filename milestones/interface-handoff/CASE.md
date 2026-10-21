# Capability handoff case: public repository publication

## Observed workflow
A connector supported Git data operations but did not expose repository creation. An existing authenticated cloud web session exposed the vendor's creation form. After verifying owner, name and public visibility, creation proceeded there. Structured Git operations then published explicit source allowlists. Remote heads were read back, and fresh checkouts reproduced tests and experiment commands.

This is one observed end-to-end workflow, not a comparative benchmark or a guarantee that another account has the same capabilities. It required no new credentials or access expansion. Source allowlists prevented intermediate experiment folders and generated caches from accidentally entering the initial release.

## Reusable decisions
- Missing wrapper capability does not establish missing vendor capability or missing authorization.
- A safe interface handoff preserves the same requested object and permissions.
- Expected-head updates protect against concurrent changes.
- Clean-checkout reproduction finds hidden dependencies that same-workspace tests can miss.
- Remote commit verification and hosted CI are different checks.

## Public references
GitHub repository endpoints: https://docs.github.com/en/rest/repos/repos
GitHub Git database API: https://docs.github.com/en/rest/git
Agent Skills specification: https://github.com/agentskills/agentskills/blob/main/docs/specification.mdx

## Validation status
The associated skill is original and format-validated. Its routing logic still needs independent forward-testing on fake interfaces, including a denied creation action, a concurrent branch update and a binary-manifest mismatch. No private credentials, session identifiers or user-specific account inventory are included.
