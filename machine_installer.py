"""Root/SYSTEM-owned native one-shot. No remotely supplied command or paths."""
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


def main():
    state = (Path(os.environ.get('ProgramData', 'C:/ProgramData'))/'PC-Mesh-Installer') if os.name=='nt' else Path('/var/lib/pc-mesh-installer')
    state.mkdir(exist_ok=True)
    started = time.time()
    def status(value):
        fd, name = tempfile.mkstemp(dir=str(state))
        with os.fdopen(fd,'w',encoding='utf-8') as stream:
            json.dump(dict(started_at=started,updated_at=time.time(),**value),stream)
        if os.name!='nt': os.chmod(name,0o644)
        os.replace(name,state/'status.json')
    status({'status':'RUNNING','pid':os.getpid()})
    try:
        with open(state/'installation.log','ab') as log:
            result=subprocess.run([sys.executable,str(Path(__file__).with_name('apply_updates.py'))],stdin=subprocess.DEVNULL,stdout=log,stderr=log)
        status({'status':'SUCCEEDED' if result.returncode==0 else 'FAILED','exit':result.returncode})
        return result.returncode
    except Exception as error:
        status({'status':'FAILED','exit':1,'error':str(error)[:300]})
        return 1


if __name__=='__main__': raise SystemExit(main())
