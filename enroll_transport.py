#!/usr/bin/env python3
"""One-time restricted SSH forwarding enrollment. Never copies private keys."""
import argparse
import json
import os
import re
import shlex
import subprocess
from pathlib import Path

ap = argparse.ArgumentParser()
ap.add_argument('action', choices=['client', 'server'])
ap.add_argument('--directory', type=Path)
ap.add_argument('--name')
ap.add_argument('--auth', type=Path)
ap.add_argument('--public', type=Path)
args = ap.parse_args()
if args.action == 'client':
    args.directory.mkdir(parents=True, exist_ok=True)
    key = args.directory / 'hub_transport_key'
    if not key.exists():
        keygen = Path(os.environ.get('ProgramFiles', 'C:/Program Files')) / 'Git/usr/bin/ssh-keygen.exe' if os.name == 'nt' else Path('ssh-keygen')
        result = subprocess.run([str(keygen), '-t', 'ed25519', '-N', '', '-f', str(key), '-C', 'pc-mesh-' + args.name + '-forward-only'], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stderr[-300:])
    print(json.dumps({'name': args.name, 'public_key': key.with_suffix('.pub').read_text().strip()}))
else:
    import paramiko
    jobs = json.loads(args.auth.read_text())
    job = next(j for j in jobs if j['host'] == '10.1.0.10' and j['user'] == 'andreas')
    records = json.loads(args.public.read_text())
    for record in records:
        if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+ pc-mesh-[a-z]+-forward-only', record['public_key']):
            raise ValueError('invalid transport public key')
    client = paramiko.SSHClient()
    client.load_system_host_keys(str(Path.home() / '.ssh/known_hosts'))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    client.connect(job['host'], username=job['user'], password=job['password'], timeout=8,
                   look_for_keys=False, allow_agent=False)
    code = '''import json,sys,os
from pathlib import Path
directory=Path.home()/'.ssh'
directory.mkdir(exist_ok=True,mode=0o700)
path=directory/'authorized_keys'
old=path.read_text() if path.exists() else ''
for item in json.load(sys.stdin):
    public=item['public_key']
    if public.split()[1] not in old:
        old=old.rstrip()+'\\ncommand="/bin/false",no-pty,no-agent-forwarding,no-X11-forwarding,no-user-rc,permitopen="127.0.0.1:9797" '+public+'\\n'
path.write_text(old)
path.chmod(0o600)
print('restricted forwarding keys enrolled for '+str(len(json.loads(PUBLIC))))
'''.replace('PUBLIC', repr(json.dumps(records)))
    stdin, stdout, stderr = client.exec_command('python3 -c ' + shlex.quote(code), timeout=20)
    stdin.write(json.dumps(records))
    stdin.channel.shutdown_write()
    output, error = stdout.read().decode(), stderr.read().decode()
    rc = stdout.channel.recv_exit_status()
    client.close()
    if rc:
        raise RuntimeError(error[-300:])
    print(output.strip())
