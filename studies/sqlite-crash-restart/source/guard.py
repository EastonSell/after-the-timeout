"""Administrative PRE-DATA content-identity gate, not authentication."""
import hashlib
import json
from pathlib import Path


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_admission(root, approval):
    root = Path(root).resolve()
    freeze_path = root / 'PRE_DATA_FREEZE.json'
    review = json.loads(Path(approval).read_text())
    if (review.get('phase') != 'PRE-DATA' or review.get('decision') != 'ADMIT'
            or not review.get('reviewer') or review.get('freeze_sha256') != sha256(freeze_path)):
        raise ValueError('independent PRE-DATA ADMIT for these exact frozen bytes is required')
    freeze = json.loads(freeze_path.read_text())
    for name, digest in freeze['files'].items():
        candidate = (root / name).resolve()
        if not candidate.is_relative_to(root) or sha256(candidate) != digest:
            raise ValueError(f'frozen source mismatch: {name}')
    return review

def reserve_output(path, source):
    path, source = Path(path).absolute(), Path(source).resolve()
    if path.exists() or path.is_symlink() or path.resolve().is_relative_to(source):
        raise ValueError('output must be new and outside the frozen source tree')
    if not path.parent.is_dir():
        raise ValueError('output parent must already exist')
    path.mkdir(exist_ok=False)
    return path
