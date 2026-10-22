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

Fresh extraction prevents accidental reliance on the checkout's ordinary neighboring files. It is not hermetic reproduction: installed Python packages and the host remain accessible, test code can access absolute paths/network, and earlier tests can affect later tests in the extracted directory. Tests are reviewed trusted Python scripts, run sequentially with a minimal environment and bounded individual timeout (1–600 seconds). The runner is not a hostile-code sandbox. Review code and use external OS-level isolation when warranted. No scientific experiments are included.

The fixture suite covers a missing declared documentation dependency, an undeclared missing dependency exposed only at runtime, private-category/extra artifacts, changed bytes, unsafe paths, symlinks, collisions, size limits, editorial gating, clean extraction, and external model deferral. This is evidence about the packaging helper, not full research reproduction or privacy proof. Every release still needs its own source and editorial review before publication. The helper does not inspect scientific correctness, authenticate review approval fields, or infer undeclared dependencies.
