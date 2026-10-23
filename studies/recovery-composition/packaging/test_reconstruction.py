"""Transport-only tests. No simulator or new scientific run."""
import base64
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('reconstruct_payloads',ROOT/'tools/reconstruct_payloads.py')
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
def sha(b):return hashlib.sha256(b).hexdigest()

class ReconstructionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.bundle=self.root/'bundle';self.bundle.mkdir()
        self.raw=b'accepted scientific bytes\x00\n'*16
        self.compressed=gzip.compress(self.raw,mtime=0)
        self.encoded=base64.b64encode(self.compressed)+b'\n'
        (self.bundle/'chunk.txt').write_bytes(self.encoded)
        self.item=dict(path='results/rows.jsonl',bytes=len(self.raw),sha256=sha(self.raw),source=dict(kind='chunks',compression='gzip',transport_bytes=len(self.compressed),transport_sha256=sha(self.compressed),parts=[dict(path='chunk.txt',bytes=len(self.encoded),sha256=sha(self.encoded))]))
        self.manifest=self.bundle/'manifest.json';self.output=self.root/'fresh'
    def tearDown(self):self.tmp.cleanup()
    def run_manifest(self):
        self.manifest.write_text(json.dumps(dict(format='recovery-exact-bytes-v1',files=[self.item])))
        return r.reconstruct(self.bundle,self.manifest,self.output)
    def test_recovers_exact_bytes(self):
        self.run_manifest();self.assertTrue((self.output/'results/rows.jsonl').exists());self.assertEqual((self.output/'results/rows.jsonl').read_bytes(),self.raw)
    def test_refuses_existing_output(self):
        self.output.mkdir()
        with self.assertRaises((ValueError,FileExistsError)):self.run_manifest()
    def test_refuses_output_symlink(self):
        self.output.symlink_to(self.bundle,target_is_directory=True)
        with self.assertRaises((ValueError,FileExistsError)):self.run_manifest()
    def test_refuses_traversal(self):
        self.item['path']='../escaped'
        with self.assertRaises(ValueError):self.run_manifest()
        self.assertFalse((self.root/'escaped').exists())
    def test_refuses_absolute_path(self):
        self.item['path']='/escaped-example'
        with self.assertRaises(ValueError):self.run_manifest()
    def test_rejects_chunk_tampering(self):
        (self.bundle/'chunk.txt').write_bytes(b'x'+self.encoded[1:])
        with self.assertRaises(ValueError):self.run_manifest()
    def test_rejects_wrong_output_hash(self):
        self.item['sha256']='0'*64
        with self.assertRaises(ValueError):self.run_manifest()
    def test_bounds_decompression(self):
        self.item['bytes']=1
        with self.assertRaises(ValueError):self.run_manifest()
    def test_refuses_excessive_size(self):
        self.item['bytes']=1000000000
        with self.assertRaises(ValueError):self.run_manifest()
    def test_refuses_duplicate_targets(self):
        self.manifest.write_text(json.dumps(dict(format='recovery-exact-bytes-v1',files=[self.item,self.item])))
        with self.assertRaises(ValueError):r.reconstruct(self.bundle,self.manifest,self.output)
    def test_refuses_source_symlink(self):
        (self.bundle/'link.txt').symlink_to(self.bundle/'chunk.txt')
        self.item['source']['parts'][0]['path']='link.txt'
        with self.assertRaises(ValueError):self.run_manifest()
    def test_copies_verified_direct_file(self):
        (self.bundle/'small.txt').write_bytes(self.raw)
        self.item['source']=dict(kind='file',path='small.txt')
        self.run_manifest();self.assertEqual((self.output/'results/rows.jsonl').read_bytes(),self.raw)

if __name__=='__main__':unittest.main()
