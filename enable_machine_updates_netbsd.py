#!/usr/bin/env python3
"""Install one native NetBSD rc.d UpdateWulf worker.

Run from an actual root owner console. The installer never invokes sudo/su,
never starts package upgrades, and never force-kills an existing worker.
"""
import argparse
import glob
import json
import os
import platform
import re
import shlex
import subprocess
import sys
import time
from pathlib import Path


def managed_cron_removed(text):
    pairs=[
        ('# BEGIN PC-MESH','# END PC-MESH'),
        ('# BEGIN UPDATEWULF','# END UPDATEWULF'),
    ]
    for start,end in pairs:
        if (start in text) != (end in text):
            raise RuntimeError('Incomplete managed cron block preserved: '+start)
    text=re.sub(r'(?ms)^# BEGIN PC-MESH\n.*?^# END PC-MESH\n?', '', text)
    return re.sub(r'(?ms)^# BEGIN UPDATEWULF\n.*?^# END UPDATEWULF\n?', '', text)


def heartbeat_pid(state):
    try:
        data=json.loads((Path(state)/'heartbeat.json').read_text())
        return int(data.get('pid',0)),float(data.get('at',0))
    except (OSError,ValueError,TypeError):
        return 0,0.0


def pid_alive(pid):
    if pid <= 0:
        return False
    result=subprocess.run(['/bin/ps','-p',str(pid),'-o','pid='],
                          stdin=subprocess.DEVNULL,capture_output=True,text=True)
    return result.returncode == 0 and result.stdout.strip() == str(pid)


def cooperative_stop(state, timeout=45):
    pid,_=heartbeat_pid(state)
    if not pid_alive(pid):
        return False
    request=Path(state)/'stop.request'
    request.touch()
    deadline=time.time()+timeout
    while time.time()<deadline and pid_alive(pid):
        time.sleep(0.25)
    if pid_alive(pid):
        raise RuntimeError('Existing UpdateWulf worker did not stop cooperatively; no terminating signal was used')
    deadline=time.time()+5
    while request.exists() and time.time()<deadline:
        time.sleep(0.1)
    request.unlink(missing_ok=True)
    return True


def wait_fresh_worker(state, started, timeout=45):
    deadline=time.time()+timeout
    while time.time()<deadline:
        pid,at=heartbeat_pid(state)
        if at >= started-1 and pid_alive(pid):
            return pid
        time.sleep(0.5)
    raise RuntimeError('NetBSD rc.d UpdateWulf worker did not publish a fresh heartbeat')


def restart_root_worker(python, source, config, state):
    child=subprocess.Popen(
        [str(python),str(source/'pc_mesh.py'),'daemon','--config',str(config),'--state',str(state)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        cwd=str(source),start_new_session=True)
    deadline=time.time()+15
    while time.time()<deadline:
        pid,_=heartbeat_pid(state)
        if pid==child.pid and pid_alive(pid):
            return child.pid
        if child.poll() is not None:
            break
        time.sleep(0.25)
    raise RuntimeError('rollback root worker did not publish its heartbeat')


def rc_script():
    return """#!/bin/sh
# PROVIDE: updatewulf
# REQUIRE: NETWORKING
# BEFORE: LOGIN

. /etc/rc.subr

name=updatewulf
rcvar=$name
pidfile=/var/run/updatewulf.pid
start_cmd=updatewulf_start
stop_cmd=updatewulf_stop
status_cmd=updatewulf_status
extra_commands="status"

load_rc_config $name

updatewulf_alive()
{
    [ -s "$pidfile" ] || return 1
    _pid=$(head -n 1 "$pidfile" 2>/dev/null)
    case "$_pid" in *[!0-9]*|'') return 1 ;; esac
    _seen=$(/bin/ps -p "$_pid" -o pid= 2>/dev/null | tr -d ' ')
    [ "$_seen" = "$_pid" ]
}

updatewulf_start()
{
    if updatewulf_alive; then
        echo "UpdateWulf already running."
        return 0
    fi
    rm -f "$updatewulf_state/stop.request" "$pidfile"
    mkdir -p "$updatewulf_state" || return 1
    cd "$updatewulf_source" || return 1
    HOME="$updatewulf_home" PATH="/usr/pkg/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
        /usr/bin/nohup "$updatewulf_python" "$updatewulf_source/pc_mesh.py" daemon \
        --config "$updatewulf_config" --state "$updatewulf_state" \
        >>"$updatewulf_state/service.log" 2>&1 </dev/null &
    echo $! > "$pidfile"
    sleep 1
    if ! updatewulf_alive; then
        rm -f "$pidfile"
        echo "UpdateWulf failed to stay running."
        return 1
    fi
}

updatewulf_stop()
{
    if ! updatewulf_alive; then
        rm -f "$pidfile"
        return 0
    fi
    touch "$updatewulf_state/stop.request" || return 1
    _n=0
    while updatewulf_alive && [ "$_n" -lt 45 ]; do
        sleep 1
        _n=$((_n + 1))
    done
    if updatewulf_alive; then
        echo "UpdateWulf did not stop cooperatively; no terminating signal was sent."
        return 1
    fi
    rm -f "$pidfile" "$updatewulf_state/stop.request"
}

updatewulf_status()
{
    if updatewulf_alive; then
        echo "UpdateWulf is running as PID $(cat "$pidfile")."
        return 0
    fi
    echo "UpdateWulf is not running."
    return 1
}

run_rc_command "$1"
"""


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument('--config',type=Path,required=True)
    ap.add_argument('--state',type=Path,required=True)
    ap.add_argument('--python',type=Path,default=Path(sys.executable))
    args=ap.parse_args()
    if platform.system()!='NetBSD':
        ap.error('NetBSD target required')
    if os.geteuid()!=0:
        ap.error('actual root owner console required; no elevation was attempted')
    source=args.source.resolve();config=args.config.resolve();state=args.state.resolve();python=args.python.resolve()
    for path in [source,config,state,python]:
        if any(c in str(path) for c in ['\n','\r','"']):
            ap.error('unsupported path characters')
    # Prevent HP-style runtime failures: the worker source must contain the
    # installer it will execute later (not only the announce daemon).
    required = ('pc_mesh.py', 'update_control.py', 'apply_updates.py')
    missing = [name for name in required if not (source / name).is_file()]
    if missing:
        ap.error('incomplete UpdateWulf release: missing ' + ', '.join(missing))
    if not config.is_file() or not python.is_file():
        ap.error('config and Python interpreter must exist')

    result=subprocess.run(['crontab','-l'],capture_output=True,text=True)
    if result.returncode not in (0,1):
        raise RuntimeError('Could not inspect existing root cron supervision')
    old_cron=result.stdout if result.returncode==0 else ''
    updated=managed_cron_removed(old_cron)

    rc=Path('/etc/rc.d/updatewulf')
    rc_conf=Path('/etc/rc.conf.d/updatewulf')
    rc_conf.parent.mkdir(parents=True,exist_ok=True)
    for path in [rc,rc_conf]:
        if path.is_symlink():
            raise RuntimeError('Refusing symlinked NetBSD service file: '+str(path))
    backups=Path('/var/backups/updatewulf')
    backups.mkdir(parents=True,exist_ok=True)
    stamp=str(int(time.time()))
    if rc.exists():
        (backups/('rc.d.updatewulf.'+stamp)).write_bytes(rc.read_bytes())
    if rc_conf.exists():
        (backups/('rc.conf.d.updatewulf.'+stamp)).write_bytes(rc_conf.read_bytes())
    if updated!=old_cron:
        cron_backup=backups/('root.crontab.'+stamp)
        cron_backup.write_text(old_cron);cron_backup.chmod(0o600)

    rc.write_text(rc_script())
    rc.chmod(0o555)
    q=shlex.quote
    rc_conf.write_text(
        'updatewulf=YES\n'
        'updatewulf_python='+q(str(python))+'\n'
        'updatewulf_source='+q(str(source))+'\n'
        'updatewulf_config='+q(str(config))+'\n'
        'updatewulf_state='+q(str(state))+'\n'
        'updatewulf_home='+q(str(Path.home()))+'\n')
    rc_conf.chmod(0o600)

    # rcorder proves that the script participates in the native dependency
    # graph before the current worker is touched.
    rc_files=sorted(glob.glob('/etc/rc.d/*'))
    order=subprocess.run(['/sbin/rcorder',*rc_files],capture_output=True,text=True)
    if order.returncode or '/etc/rc.d/updatewulf' not in order.stdout.splitlines():
        raise RuntimeError('NetBSD rcorder did not accept the UpdateWulf rc.d service')

    had_worker=cooperative_stop(state)
    started=time.time()
    try:
        subprocess.run([str(rc),'start'],check=True)
        service_pid=wait_fresh_worker(state,started)
    except Exception:
        subprocess.run([str(rc),'stop'],check=False)
        if had_worker:
            restart_root_worker(python,source,config,state)
        raise

    if updated!=old_cron:
        subprocess.run(['crontab','-'],input=updated,text=True,check=True)
    print('UpdateWulf NetBSD rc.d service verified PID=%s; root cron supervision retired. No package upgrade started.' % service_pid)


if __name__=='__main__':
    main()
