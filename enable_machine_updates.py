#!/usr/bin/env python3
"""One-time native owner-console installation for Linux machine services.

Run as actual root at an independently authorized owner console. This helper
never invokes sudo/su and never installs pending packages itself.
"""
import argparse
import json
import os
import pwd
import re
import shutil
import subprocess
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
        pid=int(data.get('pid',0))
        return pid, float(data.get('at',0))
    except (OSError,ValueError,TypeError):
        return 0,0.0


def pid_alive(pid):
    return pid > 0 and Path('/proc') .joinpath(str(pid)).exists()


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
        raise RuntimeError('Existing UpdateWulf worker did not stop cooperatively; no force-kill was used')
    deadline=time.time()+5
    while request.exists() and time.time()<deadline:
        time.sleep(0.1)
    if request.exists():
        request.unlink(missing_ok=True)
    return True


def wait_fresh_worker(state, started, timeout=45):
    deadline=time.time()+timeout
    while time.time()<deadline:
        pid,at=heartbeat_pid(state)
        if at >= started-1 and pid_alive(pid):
            return pid
        time.sleep(0.5)
    raise RuntimeError('systemd UpdateWulf worker did not publish a fresh heartbeat')


def restart_user_worker(source, config, state, account):
    def drop_privileges():
        os.initgroups(account.pw_name, account.pw_gid)
        os.setgid(account.pw_gid)
        os.setuid(account.pw_uid)
    child=subprocess.Popen(
        ['/usr/bin/python3',str(source/'pc_mesh.py'),'daemon','--config',str(config),'--state',str(state)],
        stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
        cwd=str(source),start_new_session=True,preexec_fn=drop_privileges)
    deadline=time.time()+15
    while time.time()<deadline:
        pid,at=heartbeat_pid(state)
        if pid==child.pid and pid_alive(pid):
            return child.pid
        if child.poll() is not None:
            break
        time.sleep(0.25)
    raise RuntimeError('rollback user worker did not publish its heartbeat')


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--user',required=True)
    ap.add_argument('--config',required=True,type=Path)
    ap.add_argument('--state',required=True,type=Path)
    ap.add_argument('--source',type=Path,default=Path(__file__).resolve().parent)
    args=ap.parse_args()
    if os.geteuid()!=0: ap.error('actual root owner console required; no elevation was attempted')
    if not shutil.which('systemctl') or subprocess.run(['systemctl','show-environment'],capture_output=True).returncode: ap.error('live systemd required; NetBSD keeps its native rc/cron route')
    account=pwd.getpwnam(args.user)
    source=args.source.resolve(); state=args.state.resolve(); config=args.config.resolve()
    if any(c in str(p) for p in [source,state,config] for c in ['\n','\r','"','%']): ap.error('unsupported path characters')
    code=Path('/usr/local/lib/pc-mesh-installer'); native_state=Path('/var/lib/pc-mesh-installer')
    for directory in [code,native_state]:
        if directory.is_symlink(): ap.error('installer directories must not be symlinks')
        directory.mkdir(exist_ok=True,parents=True); directory.chmod(0o755); os.chown(directory,0,0)
    for name in ['apply_updates.py','apply_windows.ps1','update_control.py','machine_installer.py']:
        destination=code/name
        if destination.is_symlink(): ap.error('installer code must not be symlinks')
        shutil.copyfile(source/name,destination); os.chown(destination,0,0); destination.chmod(0o644)
    installer='[Unit]\nDescription=PC-Mesh explicitly requested native package updates\nAfter=network-online.target\n\n[Service]\nType=oneshot\nExecStart=/usr/bin/python3 /usr/local/lib/pc-mesh-installer/machine_installer.py\nTimeoutStartSec=infinity\n'
    announce='[Unit]\nDescription=PC-Mesh Update Announce\nAfter=network-online.target\nWants=network-online.target\n\n[Service]\nUser='+args.user+'\nEnvironment="HOME='+account.pw_dir+'"\nEnvironment="PATH=/usr/local/bin:/usr/bin:/bin"\nExecStart=/usr/bin/python3 "'+str(source/'pc_mesh.py')+'" daemon --config "'+str(config)+'" --state "'+str(state)+'"\nRestart=always\nRestartSec=5\nNoNewPrivileges=true\n\n[Install]\nWantedBy=multi-user.target\n'
    Path('/etc/systemd/system/pc-mesh-install.service').write_text(installer)
    Path('/etc/systemd/system/pc-mesh-announce.service').write_text(announce)
    rule='polkit.addRule(function(action,subject) { if (action.id == "org.freedesktop.systemd1.manage-units" && action.lookup("unit") == "pc-mesh-install.service" && action.lookup("verb") == "start" && subject.user == '+json.dumps(args.user)+') return polkit.Result.YES; });\n'
    rules=Path('/etc/polkit-1/rules.d'); rules.mkdir(parents=True,exist_ok=True)
    (rules/'49-pc-mesh-installer.rules').write_text(rule)
    data=json.loads(config.read_text()); data['native_installer']=True
    config.write_text(json.dumps(data,indent=2)+'\n'); os.chown(config,account.pw_uid,account.pw_gid); config.chmod(0o600)
    subprocess.run(['systemd-analyze','verify','/etc/systemd/system/pc-mesh-install.service','/etc/systemd/system/pc-mesh-announce.service'],check=True)
    subprocess.run(['systemctl','daemon-reload'],check=True)
    # Inspect and validate every existing persistence path before enabling a
    # second boot-time scheduler. A failed preflight must leave boot behavior
    # unchanged.
    existing=subprocess.run(['crontab','-u',args.user,'-l'],capture_output=True,text=True)
    if existing.returncode not in (0,1):
        raise RuntimeError('Could not inspect existing user cron supervision')
    old_cron=existing.stdout if existing.returncode==0 else ''
    updated=managed_cron_removed(old_cron)
    if updated!=old_cron:
        backup=native_state/'previous-user-crontab.txt'
        if not backup.exists():
            backup.write_text(old_cron); backup.chmod(0o600)

    # Only after the old persistence is proven well-formed is the native boot
    # unit enabled. It is still not started until the live user worker exits.
    subprocess.run(['systemctl','enable','pc-mesh-announce.service'],check=True)
    had_worker=cooperative_stop(state)
    started=time.time()
    try:
        subprocess.run(['systemctl','start','pc-mesh-announce.service'],check=True)
        system_pid=wait_fresh_worker(state,started)
    except Exception:
        subprocess.run(['systemctl','disable','--now','pc-mesh-announce.service'],check=False)
        if had_worker:
            restart_user_worker(source,config,state,account)
        raise

    # Only after the native service owns the live heartbeat may its former
    # user cron persistence be retired. Unrelated cron entries are untouched.
    if updated!=old_cron:
        subprocess.run(['crontab','-u',args.user,'-'],input=updated,text=True,check=True)
    print('UpdateWulf machine service verified PID=%s; user cron supervision retired. Fixed native installer authorized; no package upgrade started.' % system_pid)


if __name__=='__main__': main()
