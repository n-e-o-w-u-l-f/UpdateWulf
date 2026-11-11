"""Native owner-console setup for a source-local restricted machine SSH key.

Only its public key reaches the existing SSH owner. Private keys are not copied.
This is not part of the SYSTEM daemon or update task.
"""
import argparse
import json
import re
import shlex
import subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--config', required=True, type=Path)
    ap.add_argument('--key', required=True, type=Path)
    args = ap.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8-sig'))
    spec = config['ssh_tunnel']
    public = Path(str(args.key) + '.pub').read_text().strip()
    if not re.fullmatch(r'ssh-ed25519 [A-Za-z0-9+/=]+ [a-zA-Z0-9_.-]+', public):
        ap.error('unexpected machine public key')
    code = '''import sys,pathlib,shutil,time
public=sys.stdin.read().strip()
directory=pathlib.Path.home()/'.ssh'
directory.mkdir(exist_ok=True,mode=0o700)
path=directory/'authorized_keys'
old=path.read_text() if path.exists() else ''
if public.split()[1] not in old:
 if path.exists(): shutil.copy2(path,path.with_name('authorized_keys.before-pc-mesh-machine-'+str(time.time_ns())))
 line='restrict,port-forwarding,permitopen="127.0.0.1:9797",permitlisten="none",command="/bin/false" '+public
 path.write_text(old.rstrip()+'\\n'+line+'\\n');path.chmod(0o600)
print('Restricted machine forwarding public key enrolled in existing owner account')
'''
    command = [spec['ssh'], '-T', '-i', spec['key'].replace('\\', '/'), '-o', 'BatchMode=yes',
               '-o', 'IdentitiesOnly=yes', '-o', 'StrictHostKeyChecking=yes',
               '-o', 'UserKnownHostsFile=' + spec['known_hosts'].replace('\\', '/'), '-o', 'ConnectTimeout=8',
               spec['user'] + '@' + spec['host'], 'python3 -c ' + shlex.quote(code)]
    result = subprocess.run(command, input=public + '\n', text=True, capture_output=True, timeout=30)
    if result.returncode:
        raise RuntimeError(result.stderr[-500:] or 'Existing owner SSH did not authorize machine transport enrollment')
    print(result.stdout.strip())


if __name__ == '__main__':
    main()
