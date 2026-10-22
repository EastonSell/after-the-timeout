# Release validation

Freshly authored, Python 3.9+ standard-library workflow. No installs or network are needed by the validator or its synthetic tests. Only ZIP is supported; write regular files without explicit directory entries. Paths use a conservative portable ASCII subset. Default total uncompressed payload limit: 100 MB. This is not a total process-memory, archive-metadata, CPU, or test-output limit; use trusted-size inputs and external resource controls where needed. The manifest is an external, independently reviewed input, not a file that must hash itself.

## Run

```sh
python3 -B -m unittest discover -s tests -v
python3 scripts/validate_release.py release.zip release-manifest.json
python3 scripts/validate_release.py release.zip release-manifest.json --run-tests
```

CLI exit codes: 0 = packaging valid (and all declared tests passed if requested); 1 = validation or test failure; 2 = test run incomplete, including no declared tests or tests deferred for external requirements. The JSON result distinguishes these outcomes. API callers must check `all_declared_tests_passed` rather than just successful function return.

## Manifest example

Replace hashes with SHA-256 of actual reviewed bytes and approval fields with the actual review outcome. A test's `requires` list refers to dependency IDs. Every bundled dependency must also appear in `files`.

```json
{
  "version": 1,
  "editorial_review": "approved",
  "files": [
    {"path": "test_result.py", "sha256": "<64 lowercase hex digits>", "category": "code", "public_review": "approved"},
    {"path": "docs/input.txt", "sha256": "<64 lowercase hex digits>", "category": "documentation", "public_review": "approved"}
  ],
  "dependencies": [
    {"id": "fixture-doc", "kind": "bundled", "path": "docs/input.txt"},
    {"id": "optional-model", "kind": "external", "source": "https://example.org/model", "pin": "sha256:<reviewed model digest>"}
  ],
  "tests": [
    {"script": "test_result.py", "args": [], "requires": ["fixture-doc"], "timeout_seconds": 60}
  ]
}
```

Approved file categories: code, data, documentation, scientific-report, skill. Unknown or private categories fail closed. Categories are editor assertions, not automated content analysis. Review reports and skills can be public when their actual content is suitable. Dependencies marked external are listed, never downloaded or resolved. Pin values are not authenticated or checked against remote services; use immutable revisions/digests, not mutable tags. Tests that list an external dependency are deferred rather than treated as passed.

## Review evidence and authorization

Keep three decisions separate:

- Editorial/content review: an explicitly identified, accountable reviewer checks the actual final public bytes and intended audience. The reviewer may be human or agent when task authorization permits that role. Record agent review as agent review, never as invented human approval.
- Execution trust: inspect the declared test code, establish trust, and confirm permission to run it. Editorial approval and a matching hash do not make code safe to execute.
- Publication permission: check the owner's applicable authorization for the actual destination and content, and follow the governing confirmation policy. A passing validator, a review record, or this skill does not provide permission, satisfy a required action-time confirmation or handoff, or bypass a denied action.

Maintain a review record outside the ZIP, or in an existing review system, identifying the reviewer and type (human or agent), review date, intended audience, exact file paths and SHA-256 hashes reviewed, actual outcome, and unresolved findings. Bind the record to the final manifest by its SHA-256 or by the complete reviewed path/hash list. Re-review changed bytes and update the record and hashes before setting approval fields. Review evidence must describe what actually happened; neither a hash nor an approval string authenticates who performed a review. Keep private authorization evidence out of public bundles.

No v1 manifest/schema change is needed: `editorial_review` and each file's `public_review` remain approval assertions, with reviewer provenance in the separate record. The helper checks these fields for `approved`; it does not verify reviewer identity, authenticate approval, inspect content for privacy, establish execution trust, or authorize publication. The synthetic fixtures' approval fields are fictional test inputs, not evidence of a real release review.

Fresh extraction prevents accidental reliance on the checkout's ordinary neighboring files. It is not hermetic reproduction: installed Python packages and the host remain accessible, test code can access absolute paths/network, and earlier tests can affect later tests in the extracted directory. Tests are reviewed trusted Python scripts, run sequentially with a minimal environment and bounded individual timeout (1–600 seconds). The runner is not a hostile-code sandbox. Review code and use external OS-level isolation when warranted. No scientific experiments are included.

The fixture suite covers a missing declared documentation dependency, an undeclared missing dependency exposed only at runtime, private-category/extra artifacts, changed bytes, unsafe paths, symlinks, collisions, size limits, editorial gating, clean extraction, and external model deferral. This is evidence about the packaging helper, not full research reproduction or privacy proof. Every release still needs its own source and editorial review before publication. The helper does not inspect scientific correctness, authenticate review approval fields, or infer undeclared dependencies.

## Fixture evidence history

`TEST_EVIDENCE.txt` is the unchanged historical 15-test author run. `REVIEW_EVIDENCE.txt` is the later, unchanged 16-test review run: it added `test_option_like_script_runs_file_not_python_option` after reproducing and fixing Python option dispatch for a script named `-c`. The current fixture source contains 16 tests, not 15. `REVIEW_V2_TEST_EVIDENCE.txt` records the current documentation-revision candidate run, with the actual command, environment, output, and exit status. Earlier logs remain historical records and are not silently rewritten as current results.
