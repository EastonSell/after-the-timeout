---
name: verify-repository-publication
description: Complete an authorized repository publication across available interfaces and verify the remote commit and clean-checkout reproduction.
---
# Verify repository publication
Identify the intended owner, repository name, visibility and exact publication file set before writing. Use an explicit allowlist; a live working directory may contain caches, credentials, scratch outputs or incomplete experiments.
If the preferred connector lacks repository creation, distinguish absent capability from denied access. An already authorized signed-in web interface may provide the missing operation. Do not create credentials or broaden permissions merely because a method is missing. Verify the resulting owner, name, visibility and URL before proceeding.
Use a structured Git interface for batch source publication where available. Preserve the expected branch head and avoid overwriting concurrent changes. Handle text and binary blobs with the correct encoding, and retain the verified resulting commit ID.
Read the remote head back. Then reproduce from a fresh checkout or clean archive of that exact commit, not from the working directory that produced it. Verify manifests, dependency versions, tests and the advertised example command. Report remote publication, local reproducibility and hosted CI as separate facts.
When an outcome is uncertain, reconcile the exact operation or branch before repeating a write. A denied action remains stopped. Do not infer that successful code publication authorizes deployment, external outreach or unrelated repository changes.
