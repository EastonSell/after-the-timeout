"""Static publication guards, not execution or agent-compliance evaluations.

These checks protect package links, the retained Git example, evidence labels,
and authored fixture coverage. They do not interpret arbitrary service contracts
or test whether an agent chooses or executes the expected action.
"""
import hashlib
from pathlib import Path
import re
import unittest
from urllib.parse import urlsplit


PACKAGE = Path(__file__).resolve().parents[1]
ROOT = PACKAGE.parents[1]
ENTRY = PACKAGE / "SKILL.md"
REFERENCES = PACKAGE / "references"
# Exact section from the public baseline 94dc717fe787b39e470be7e7d277576a6f67ac77.
GIT_SECTION_SHA256 = "fdbcbbf2435bd3f964342203cd24a1f47daa0cbb50a717e9f42e2b6417671b47"
EXPECTED_FIXTURES = {
    "terminal-no-effect": "retry-terminal",
    "valid-original-key": "retry-contract",
    "keyless-operation-contract": "retry-operation",
    "stale-negative": "reconcile",
    "fresh-absent-inflight": "reconcile",
    "expired-key": "reconcile",
    "uncertain-key-age": "reconcile",
    "late-original-after-expiry": "reconcile",
    "wrong-operation": "reconcile",
    "partial-effect": "reconcile",
    "cancellation-requested": "reconcile",
    "retroactive-key": "reconcile",
    "changed-payload": "reconcile",
    "changed-scope": "reconcile",
    "concurrency-uncovered": "reconcile",
    "replayed-error": "not-complete",
    "queued-work": "observe",
    "withdrawn-authorization": "stop",
    "denied-action": "stop",
}


class GuidancePackageTests(unittest.TestCase):
    def test_entrypoint_routes_to_contract_sources_and_examples(self):
        links = re.findall(r"\]\(([^)]+)\)", ENTRY.read_text())
        self.assertTrue({"references/retry-contract-sources.md",
                         "references/regression-examples.md",
                         "references/content-addressed-tree-recovery.md"}.issubset(links))

    def test_package_markdown_local_links_resolve_within_repository(self):
        for document in [ENTRY, *REFERENCES.glob("*.md")]:
            for target in re.findall(r"\]\(([^)]+)\)", document.read_text()):
                parsed = urlsplit(target)
                if parsed.scheme or not parsed.path:
                    continue
                resolved = (document.parent / parsed.path).resolve()
                with self.subTest(document=document.name, target=target):
                    self.assertTrue(resolved.is_relative_to(ROOT.resolve()))
                    self.assertTrue(resolved.is_file())

    def test_content_addressed_git_section_matches_public_baseline(self):
        text = ENTRY.read_text()
        section = re.search(
            r"^## Content-addressed Git objects\n[\s\S]*?"
            r"(?=\n(?:## |A denial is not a transient transport error\.))",
            text, re.MULTILINE)
        self.assertIsNotNone(section)
        self.assertEqual(hashlib.sha256(section.group(0).encode()).hexdigest(),
                         GIT_SECTION_SHA256)

    def test_explicit_denial_stop_is_retained(self):
        self.assertIn("A denial is not a transient transport error. Stop the denied action.",
                      ENTRY.read_text())

    def test_authored_expectation_coverage_and_unique_case_ids(self):
        text = (REFERENCES / "regression-examples.md").read_text()
        rows = [line.split("|")[1:-1] for line in text.splitlines()
                if re.match(r"^\| R\d\d \|", line)]
        self.assertEqual(len(rows), len({cells[0].strip() for cells in rows}))
        expectations = {cells[1].strip(): cells[3].strip() for cells in rows}
        self.assertEqual(len(rows), len(expectations))
        self.assertEqual(expectations, EXPECTED_FIXTURES)

    def test_fixture_evidence_level_is_explicit(self):
        text = (REFERENCES / "regression-examples.md").read_text()
        self.assertIn("authored expectations", text)
        self.assertIn("not measured agent compliance", text)
        self.assertIn("No live action is authorized", text)

    def test_sources_are_primary_contract_examples(self):
        text = (REFERENCES / "retry-contract-sources.md").read_text()
        self.assertIn("https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadConsistency.html", text)
        self.assertIn("https://docs.stripe.com/api/idempotent_requests", text)
        self.assertIn("https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2", text)
        self.assertIn("https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/", text)


if __name__ == "__main__":
    unittest.main()
