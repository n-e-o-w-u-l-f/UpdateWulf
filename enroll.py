#!/usr/bin/env python3
"""Generate independent read-only GitHub keys on the receiving host.

Catalog files contain public repository metadata. Private key files remain
outside source control; the output is public enrollment information only.
"""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from pc_mesh import atomic_write, save_json

ap = argparse.ArgumentParser()
ap.add_argument('--catalog', type=Path, required=True)
ap.add_argument('--directory', type=Path, default=Path.home() / '.config/pc-mesh/github')
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
catalog = json.loads(args.catalog.read_text(encoding='utf-8-sig'))
args.directory.mkdir(parents=True, exist_ok=True)
if os.name != 'nt':
    args.directory.chmod(0o700)
keys = []
for repo in catalog:
    if not repo['private']:
        continue
    name = repo['name']
    key = args.directory / ('repo-' + hashlib.sha256(name.encode()).hexdigest()[:16])
    if not key.exists():
        subprocess.run(['ssh-keygen', '-q', '-t', 'ed25519', '-N', '', '-C', 'pc-mesh-readonly-' + name, '-f', str(key)], check=True)
    pub = key.with_name(key.name + '.pub').read_text().strip()
    keys.append({'name': name, 'path': str(key), 'public_key': pub})
save_json(args.output, keys)
print(json.dumps({'public_keys': len(keys), 'output': str(args.output)}))
