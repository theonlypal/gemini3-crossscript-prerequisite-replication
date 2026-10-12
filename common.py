"""Offline serialization and frozen-file validation. No credential or network access."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent

def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha(data):
    return hashlib.sha256(data).hexdigest()

def read(path):
    return json.loads(Path(path).read_bytes())

def save(path, value):
    Path(path).write_bytes(encoded(value) + b'\n')

def integrity():
    manifest = read(ROOT / 'freeze_manifest.json')
    for name, digest in manifest['files'].items():
        if sha((ROOT / name).read_bytes()) != digest:
            raise ValueError('Frozen file changed: ' + name)
    return manifest

def request_bytes(cell):
    return (ROOT / 'requests' / (cell + '.json')).read_bytes()
