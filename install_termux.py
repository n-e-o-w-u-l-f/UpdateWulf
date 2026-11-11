"""Install one persistent UpdateWulf worker for the actual Termux app account."""
import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from install import hooks
from pc_mesh import FileLock, atomic_write


def worker_active(state):
    try:
        with FileLock(Path(state) / "daemon.lock"):
            return False
    except RuntimeError:
        return True


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--config',type=Path,default=Path.home()/'.config/pc-mesh/config.json')
    ap.add_argument('--state',type=Path,default=Path.home()/'.local/state/pc-mesh')
    args=ap.parse_args()
    if not os.environ.get('PREFIX','').startswith('/data/data/com.termux/'):
        ap.error('actual Termux owner session required')
    if not args.config.exists():
        ap.error('enroll private configuration before starting service')
    args.state.mkdir(parents=True,exist_ok=True)
    wake_lock=shutil.which('termux-wake-lock')
    if wake_lock:
        subprocess.run([wake_lock],check=True,timeout=15)
    profiles=hooks(args.source,args.state,Path.home())
    boot=Path.home()/'.termux/boot/50-updatewulf.sh'
    boot.parent.mkdir(parents=True,exist_ok=True)
    q=shlex.quote
    launch=[sys.executable,str(args.source/'pc_mesh.py'),'daemon','--config',str(args.config),'--state',str(args.state)]
    text='#!'+os.environ['PREFIX']+'/bin/sh\n# UPDATEWULF managed native Termux boot hook\n'
    text+='command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock\n'
    text+='exec '+' '.join(q(s) for s in launch)+' >> '+q(str(args.state/'service.log'))+' 2>&1\n'
    legacy=Path.home()/'.termux/boot/50-pc-mesh.sh'
    if legacy.exists() and 'PC-MESH' in legacy.read_text(errors='replace'):
        backup=legacy.with_name(legacy.name+'.before-updatewulf-v2')
        if not backup.exists():
            shutil.copy2(legacy,backup)
        legacy.unlink()
    if boot.exists() and 'UPDATEWULF' not in boot.read_text(errors='replace'):
        ap.error('unrelated existing boot hook preserved')
    atomic_write(boot,text);boot.chmod(0o700)
    child_pid=None
    if not worker_active(args.state):
        with open(args.state/'service.log','ab') as log:
            child=subprocess.Popen(launch,stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            child_pid=child.pid
            time.sleep(0.2)
    print(json.dumps({'profiles':profiles,'worker_pid':child_pid,'boot_hook':str(boot),
                      'supervisor':'NONE','boot_acceptance':'Termux:Boot must be installed and opened once; real Android reboot not tested'}))


if __name__=='__main__':
    main()
