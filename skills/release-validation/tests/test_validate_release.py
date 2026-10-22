import copy
import hashlib
import importlib.util
from pathlib import Path
import stat
import tempfile
import unittest
import warnings
import zipfile

spec = importlib.util.spec_from_file_location('validator', Path(__file__).parents[1] / 'scripts/validate_release.py')
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.archive = Path(self.tmp.name) / 'bundle.zip'
        self.files = {'docs/input.txt': b'42\n', 'test_result.py':
                      b'from pathlib import Path\nassert Path("docs/input.txt").read_text() == "42\\n"\nprint("fixture passed")\n'}
        self.manifest = {'version': 1, 'editorial_review': 'approved',
                         'files': [{'path': p, 'sha256': hashlib.sha256(b).hexdigest(),
                                    'category': 'documentation' if p.startswith('docs/') else 'code',
                                    'public_review': 'approved'} for p, b in self.files.items()],
                         'dependencies': [{'id': 'fixture-doc', 'kind': 'bundled', 'path': 'docs/input.txt'}],
                         'tests': [{'script': 'test_result.py', 'requires': ['fixture-doc']}]}

    def write(self, files=None):
        with zipfile.ZipFile(self.archive, 'w') as z:
            for p, data in (self.files if files is None else files).items():
                z.writestr(p, data)

    def test_clean_extraction_runs_declared_test(self):
        self.write()
        result = v.validate(self.archive, self.manifest, True)
        self.assertTrue(result['all_declared_tests_passed'])
        self.assertEqual(result['tests'][0]['stdout'], 'fixture passed\n')

    def test_missing_declared_document_dependency(self):
        del self.files['docs/input.txt']
        self.manifest['files'] = [f for f in self.manifest['files'] if f['path'] != 'docs/input.txt']
        self.write()
        with self.assertRaisesRegex(v.InvalidRelease, 'missing declared dependency'):
            v.validate(self.archive, self.manifest, True)

    def test_undeclared_document_dependency_detected_by_extracted_test(self):
        del self.files['docs/input.txt']
        self.manifest['files'] = [f for f in self.manifest['files'] if f['path'] != 'docs/input.txt']
        self.manifest['dependencies'] = []
        self.manifest['tests'][0]['requires'] = []
        self.write()
        with self.assertRaisesRegex(v.InvalidRelease, 'test failed'):
            v.validate(self.archive, self.manifest, True)

    def test_private_category_rejected_even_if_allowlisted(self):
        self.manifest['files'][0]['category'] = 'coordination-handoff'
        self.write()
        with self.assertRaisesRegex(v.InvalidRelease, 'non-public or unknown artifact category'):
            v.validate(self.archive, self.manifest)

    def test_unexpected_artifact_rejected(self):
        self.write({**self.files, 'private-handoff.md': b'fictional fixture'})
        with self.assertRaisesRegex(v.InvalidRelease, 'allowlist mismatch'):
            v.validate(self.archive, self.manifest)

    def test_tampered_bytes_rejected(self):
        self.write({**self.files, 'docs/input.txt': b'43\n'})
        with self.assertRaisesRegex(v.InvalidRelease, 'hash mismatch'):
            v.validate(self.archive, self.manifest)

    def test_unsafe_paths(self):
        for path in ('../escape', '/absolute', 'C:/drive', 'a\\b', 'a/../b', 'a//b', 'NUL.txt', 'a.'):
            with self.subTest(path=path), self.assertRaises(v.InvalidRelease):
                v.safe_path(path)

    def test_archive_path_checked_before_extraction(self):
        self.write({**self.files, '../escape': b'bad'})
        with self.assertRaisesRegex(v.InvalidRelease, 'unsafe'):
            v.validate(self.archive, self.manifest, True)

    def test_symlink_entry_rejected(self):
        self.write()
        link = zipfile.ZipInfo('link')
        link.create_system = 3
        link.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(self.archive, 'a') as z:
            z.writestr(link, 'docs/input.txt')
        self.manifest['files'].append({'path': 'link', 'sha256': hashlib.sha256(b'docs/input.txt').hexdigest(),
                                       'category': 'data', 'public_review': 'approved'})
        with self.assertRaisesRegex(v.InvalidRelease, 'nonregular'):
            v.validate(self.archive, self.manifest)

    def test_external_model_stays_external_and_test_not_reported_passed(self):
        self.manifest['dependencies'].append({'id': 'model', 'kind': 'external', 'source': 'https://example.org/model',
                                              'pin': 'sha256:' + 'a' * 64})
        self.manifest['tests'][0]['requires'].append('model')
        self.write()
        result = v.validate(self.archive, self.manifest, True)
        self.assertFalse(result['all_declared_tests_passed'])
        self.assertEqual(result['tests'][0]['status'], 'not-run')
        self.assertEqual(result['external_requirements'][0]['id'], 'model')

    def test_review_is_required(self):
        self.write()
        self.manifest['editorial_review'] = 'pending'
        with self.assertRaisesRegex(v.InvalidRelease, 'editorial review'):
            v.validate(self.archive, self.manifest)

    def test_duplicate_allowlist_and_case_collision_rejected(self):
        self.write()
        for path in ('docs/input.txt', 'DOCS/input.txt'):
            manifest = copy.deepcopy(self.manifest)
            entry = copy.deepcopy(manifest['files'][0])
            entry['path'] = path
            manifest['files'].append(entry)
            with self.assertRaises(v.InvalidRelease):
                v.validate(self.archive, manifest)

    def test_duplicate_archive_entry_rejected(self):
        self.write()
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', UserWarning)
            with zipfile.ZipFile(self.archive, 'a') as z:
                z.writestr('docs/input.txt', b'42\n')
        with self.assertRaisesRegex(v.InvalidRelease, 'duplicate archive entries'):
            v.validate(self.archive, self.manifest)

    def test_missing_allowlisted_entry_rejected(self):
        self.write({'test_result.py': self.files['test_result.py']})
        with self.assertRaisesRegex(v.InvalidRelease, 'allowlist mismatch'):
            v.validate(self.archive, self.manifest)

    def test_option_like_script_runs_file_not_python_option(self):
        self.files = {'-c': b'print("reviewed file")\n'}
        self.manifest['files'] = [{'path': '-c', 'sha256': hashlib.sha256(self.files['-c']).hexdigest(),
                                   'category': 'code', 'public_review': 'approved'}]
        self.manifest['dependencies'] = []
        self.manifest['tests'] = [{'script': '-c', 'args': ['print("argument executed")']}]
        self.write()
        result = v.validate(self.archive, self.manifest, True)
        self.assertEqual(result['tests'][0]['stdout'], 'reviewed file\n')

    def test_size_limit(self):
        self.write()
        with self.assertRaisesRegex(v.InvalidRelease, 'size limit'):
            v.validate(self.archive, self.manifest, max_bytes=1)


if __name__ == '__main__':
    unittest.main()
