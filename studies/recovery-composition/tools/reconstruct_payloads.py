"""Bounded exact-byte reconstruction. No extraction, network, or overwrite.

Only paths explicitly listed in payload-manifest.json can be created. The
destination must be absent. All inputs and outputs are size- and SHA-256-checked.
"""
import argparse
import base64
import binascii
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import zlib

MAX_FILES = 256
MAX_PARTS = 64
MAX_PART_BYTES = 500_000
MAX_INPUT_BYTES = 12_000_000
MAX_OUTPUT_BYTES = 32_000_000


def _path(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise ValueError('invalid portable relative path')
    p = PurePosixPath(value)
    if p.is_absolute() or any(x in ('', '.', '..') for x in value.split('/')):
        raise ValueError('invalid portable relative path')
    return p


def _size(value, limit):
    if type(value) is not int or value < 0 or value > limit:
        raise ValueError('size exceeds transport bounds')
    return value


def _digest(value):
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise ValueError('invalid SHA-256')
    return value


def _read(bundle, name, size, digest):
    rel = _path(name)
    p = bundle
    for part in rel.parts:
        p = p / part
        if p.is_symlink():
            raise ValueError('symlink input is not supported')
    if not p.is_file() or p.stat().st_size != size:
        raise ValueError('input size mismatch: ' + name)
    with p.open('rb') as f:
        data = f.read(size + 1)
    if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
        raise ValueError('input hash mismatch: ' + name)
    return data


def reconstruct(bundle, manifest_path, output):
    bundle, manifest_path, output = Path(bundle).resolve(), Path(manifest_path), Path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('output must be a fresh, absent path')
    if not output.parent.is_dir():
        raise ValueError('output parent must already exist')
    if manifest_path.stat().st_size > 500_000:
        raise ValueError('manifest exceeds bound')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    entries = manifest.get('files')
    if manifest.get('format') != 'recovery-exact-bytes-v1' or not isinstance(entries, list) or not 0 < len(entries) <= MAX_FILES:
        raise ValueError('unsupported manifest')
    names, total, transport_total, part_count = set(), 0, 0, 0
    for item in entries:
        name = str(_path(item['path']))
        if name in names:
            raise ValueError('duplicate output path')
        names.add(name)
        total += _size(item['bytes'], MAX_OUTPUT_BYTES)
        _digest(item['sha256'])
        source = item['source']
        if source['kind'] == 'file':
            _path(source['path'])
            transport_total += _size(item['bytes'], MAX_PART_BYTES)
        elif source['kind'] == 'chunks':
            _size(source['transport_bytes'], MAX_INPUT_BYTES)
            _digest(source['transport_sha256'])
            if source['compression'] not in ('none', 'gzip') or not isinstance(source['parts'], list) or not source['parts']:
                raise ValueError('invalid chunk source')
            for part in source['parts']:
                _path(part['path']); _digest(part['sha256'])
                transport_total += _size(part['bytes'], MAX_PART_BYTES)
                part_count += 1
        else:
            raise ValueError('unsupported source kind')
    if total > MAX_OUTPUT_BYTES or transport_total > MAX_INPUT_BYTES or part_count > MAX_PARTS:
        raise ValueError('aggregate transport bounds exceeded')
    for name in names:
        if any(str(p) in names for p in PurePosixPath(name).parents if str(p) != '.'):
            raise ValueError('file/directory output collision')
    # Validate all bytes before creating the destination; malformed inputs leave
    # no partially reconstructed output. Memory is bounded above by the constants.
    ready = []
    for item in entries:
        source, expected = item['source'], item['bytes']
        if source['kind'] == 'file':
            data = _read(bundle, source['path'], expected, item['sha256'])
        else:
            decoded = []
            for part in source['parts']:
                encoded = _read(bundle, part['path'], part['bytes'], part['sha256'])
                # Each part is one canonical base64 line with a single final LF.
                if not encoded.endswith(b'\n') or b'\n' in encoded[:-1]:
                    raise ValueError('noncanonical base64 part')
                try:
                    value = base64.b64decode(encoded[:-1], validate=True)
                except binascii.Error as exc:
                    raise ValueError('invalid base64 part') from exc
                if base64.b64encode(value) + b'\n' != encoded:
                    raise ValueError('noncanonical base64 encoding')
                decoded.append(value)
            packed = b''.join(decoded)
            if len(packed) != source['transport_bytes'] or hashlib.sha256(packed).hexdigest() != source['transport_sha256']:
                raise ValueError('transport hash or size mismatch')
            if source['compression'] == 'none':
                data = packed
            else:
                decompressor = zlib.decompressobj(31)
                try:
                    data = decompressor.decompress(packed, expected + 1)
                except zlib.error as exc:
                    raise ValueError('invalid gzip transport') from exc
                if len(data) > expected or not decompressor.eof or decompressor.unused_data or decompressor.unconsumed_tail:
                    raise ValueError('gzip exceeds bound or contains trailing data')
        if len(data) != expected or hashlib.sha256(data).hexdigest() != item['sha256']:
            raise ValueError('reconstructed hash or size mismatch: ' + item['path'])
        ready.append((item['path'], data))
    output.mkdir()
    for name, data in ready:
        target = output.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as f:
            f.write(data)
    return dict(files=len(ready), bytes=total, all_sha256_verified=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, help='fresh absent directory; its parent must exist')
    args = parser.parse_args()
    bundle = Path(__file__).resolve().parents[1]
    print(json.dumps(reconstruct(bundle, bundle/'payload-manifest.json', args.output), sort_keys=True))


if __name__ == '__main__':
    main()
