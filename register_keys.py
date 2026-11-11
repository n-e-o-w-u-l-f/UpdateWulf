#!/usr/bin/env python3
"""Use the owner's normal gh session to register received PUBLIC deploy keys."""
import argparse
import json
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('--keys', type=Path, required=True)
ap.add_argument('--host', required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
keys = json.loads(args.keys.read_text(encoding='utf-8-sig'))
results = []
for key in keys:
    title = 'pc-mesh-' + args.host
    endpoint = 'repos/' + key['name'] + '/keys'
    old = subprocess.run(['gh','api',endpoint], capture_output=True, text=True, check=True)
    match = next((k for k in json.loads(old.stdout) if k['key'].split()[:2] == key['public_key'].split()[:2]), None)
    if match:
        result = match
    else:
        request = json.dumps({'title':title,'key':key['public_key'],'read_only':True})
        call = subprocess.run(['gh','api',endpoint,'--method','POST','--input','-'], input=request, capture_output=True, text=True)
        if call.returncode:
            results.append({'repo':key['name'],'status':'BLOCKED','error':call.stderr[-1000:], 'response':call.stdout[-1000:]})
            args.output.write_text(json.dumps(results, indent=2)+'\n')
            print(json.dumps(results[-1]), flush=True)
            continue
        result = json.loads(call.stdout)
    if result.get('read_only') is not True:
        raise RuntimeError('expected read-only deploy key: ' + key['name'])
    results.append({'repo':key['name'],'id':result['id'],'title':result['title'],'read_only':result['read_only']})
    args.output.write_text(json.dumps(results, indent=2) + '\n')
    print(json.dumps(results[-1]), flush=True)
args.output.write_text(json.dumps(results, indent=2) + '\n')
print(json.dumps(results))
