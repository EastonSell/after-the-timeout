import hashlib
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'tools'))
from reproduce import reproduce, source_files, STUDIES
import run_all_tests


class ReleaseToolTests(unittest.TestCase):
    def test_matrix_names_and_entrypoints(self):
        self.assertEqual(len(run_all_tests.SUITES), 7)
        self.assertEqual(len({s[0] for s in run_all_tests.SUITES}), 7)
        for _, cwd, discovery in run_all_tests.SUITES:
            self.assertTrue((ROOT/cwd/discovery).is_dir())

    def test_aggregate_continues_after_failure_and_returns_failure(self):
        from types import SimpleNamespace
        responses = [SimpleNamespace(returncode=0) for _ in run_all_tests.SUITES]
        responses[1].returncode = 1
        with patch.object(run_all_tests.subprocess, 'run', side_effect=responses) as run, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(run_all_tests.run_all(), 1)
            self.assertEqual(run.call_count, 7)
            self.assertTrue(all(call.kwargs['check'] is False for call in run.call_args_list))

    def test_all_studies_reproduce_without_changing_sources_or_history(self):
        tracked = [p for p in ROOT.rglob('*') if p.is_file() and '__pycache__' not in str(p) and '.git' not in p.parts]
        before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked}
        with tempfile.TemporaryDirectory() as directory:
            for study in STUDIES:
                with self.subTest(study=study):
                    output = reproduce(study, Path(directory)/study)
                    manifest = json.loads((output/'reproduction.json').read_text())
                    self.assertEqual(manifest['wrapper_version'], 1)
                    for relative,digest in manifest['source_sha256'].items():
                        self.assertEqual(hashlib.sha256((ROOT/relative).read_bytes()).hexdigest(),digest)
                    for name,digest in manifest['output_sha256'].items():
                        self.assertEqual(hashlib.sha256((output/name).read_bytes()).hexdigest(),digest)
                    fresh = json.loads((output/'experiment.json').read_text())
                    historical = json.loads((ROOT/STUDIES[study]/'results/experiment.json').read_text())
                    self.assertEqual(fresh['summary'],historical['summary'])
                    self.assertEqual(fresh['rows'],historical['rows'])
        self.assertEqual(before,{p:hashlib.sha256(p.read_bytes()).hexdigest() for p in tracked})

    def test_existing_output_refused_without_running_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)/'old';out.mkdir();(out/'keep').write_text('keep')
            with patch('reproduce.subprocess.run') as run:
                with self.assertRaises(ValueError):reproduce('baseline',out)
                run.assert_not_called()
            self.assertEqual((out/'keep').read_text(),'keep')

    def test_outputs_inside_repository_refused(self):
        with self.assertRaises(ValueError): reproduce('baseline', ROOT/'new-result-output')
        self.assertFalse((ROOT/'new-result-output').exists())

    def test_missing_parent_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'missing'/'result'
            with self.assertRaises(ValueError):reproduce('baseline',out)
            link=Path(directory)/'link';link.symlink_to(Path(directory)/'missing')
            with self.assertRaises(ValueError):reproduce('baseline',link)

    def test_failure_does_not_create_output(self):
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'failed'
            with patch('reproduce.subprocess.run',return_value=SimpleNamespace(returncode=2,stderr='fixture failure')):
                with self.assertRaises(RuntimeError):reproduce('baseline',out)
            self.assertFalse(out.exists())

    def test_unknown_study_rejected(self):
        with self.assertRaises(ValueError):source_files('typo')


if __name__ == '__main__': unittest.main()
