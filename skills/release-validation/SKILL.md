---
name: release-validation
description: Check research release ZIPs against reviewed allowlists and hashes, audit declared dependencies, and run approved tests from fresh extracted bundles before publication.
---

# Validate a research release

Use this workflow when preparing or reviewing a standalone research/code bundle. It checks packaging, not scientific truth or permission to publish. Keep changes in a staging area until source changes and public content receive author review.

1. Have a human author/editor review each proposed public file and its intended audience. Exclude private coordination/handoff artifacts and unrelated content. Do not classify all review reports or skills as private: purpose, provenance, and reviewed content matter. Filename heuristics and category labels cannot prove privacy. Newly written public instructions are preferable to copying internal material.
2. Prepare a separately reviewed JSON manifest with exact file paths and SHA-256 hashes of the final bytes. Record an approved public category per file; record editorial approval only after it actually occurs. Freeze the manifest separately from the ZIP. A manifest generated from an unreviewed archive is not an independent trust anchor.
3. Declare supporting local files explicitly, including documentation consumed by tests. Keep large model weights or other intentionally external dependencies external, with their source and immutable revision/digest. Do not download or silently bundle them. Review pins manually; the validator checks declaration presence, not remote authenticity.
4. Validate the archive with scripts/validate_release.py and the schema/example in README.md. The helper accepts ZIPs containing only regular files, checks the exact allowlist and hashes, rejects unsafe paths, links and duplicates, and limits uncompressed size. Directory entries must be omitted when packaging.
5. After reviewing the declared Python test code and confirming execution is authorized, use --run-tests. This writes verified bytes into a new temporary directory and runs tests there, not in the populated source checkout. The helper does not provide an OS/network security sandbox. Do not execute untrusted archive code with this helper. Review and establish trust first; additional OS-level isolation or offline execution must be provisioned externally. Do not run installations, experiments or downloads merely to obtain a passing packaging check.
6. Report packaging status and test status separately. A missing bundled requirement blocks validation. Tests requiring declared external dependencies remain explicitly unrun. A clean synthetic/unit-test run does not establish full scientific reproduction. Report what ran, what did not, command, environment, exit status, and remaining editorial/scientific review. Obtain the required review before publication; validation itself does not publish.

Use the included fixture suite to check validator changes. When an actual release fails, fix the source packaging/dependency declarations, rebuild, review changed content and regenerate hashes, then rerun against the new standalone archive. Never remove a needed dependency or weaken a test merely to turn the gate green.
