#!/usr/bin/env python3
"""Install cached UpdateWulf shell status and one persistent Unix worker.

Shell integration reads an already-rendered local cache. The Bash PS1 header
is a reversible decorator preserving the owner prompt and other hooks; other
shells retain their passive startup text until native prompt support is added.
Linux prefers a native systemd user service. A single @reboot cron entry is the
fallback when the user service manager is unavailable; no periodic supervisor
is installed.
"""
import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from pc_mesh import atomic_write, save_json


def managed(path, text):
    path = Path(path)
    if path.is_symlink():
        path = path.resolve(strict=True)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    start, end = "# BEGIN PC-MESH", "# END PC-MESH"
    if start in old and end not in old:
        raise RuntimeError("incomplete managed block: " + str(path))
    pattern = r"(?ms)^# BEGIN PC-MESH\n.*?^# END PC-MESH(?:\n|$)"
    block = start + "\n" + text.rstrip() + "\n" + end + "\n"
    new = re.sub(pattern, lambda _m: block, old) if re.search(pattern, old) else old.rstrip("\n") + "\n\n" + block
    if new != old:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            backup = path.with_name(path.name + ".pc-mesh-backup-" + str(int(time.time())))
            shutil.copy2(path, backup)
        atomic_write(path, new)
    return str(path)


def hooks(source, cache, home):
    q = shlex.quote
    command = q(sys.executable) + " " + q(str(source / "pc_mesh.py")) + " line --state " + q(str(cache))
    hookdir = home / ".config/pc-mesh"
    hookdir.mkdir(parents=True, exist_ok=True)
    bash_template = source / "hooks" / "updatewulf.bash.in"
    if not bash_template.is_file():
        raise RuntimeError("UpdateWulf Bash prompt hook missing: " + str(bash_template))
    bash = bash_template.read_text(encoding="utf-8").replace("__STATE_QUOTED__", q(str(cache)))
    zsh = """[[ -o interactive ]] || return
if [[ -z ${UPDATEWULF_SHELL_SHOWN-} ]]; then
 typeset -g UPDATEWULF_SHELL_SHOWN=1
 __UPDATEWULF_LINE__ 2>/dev/null || true
fi
""".replace("__UPDATEWULF_LINE__", command)
    fish = """if status is-interactive; and not set -q UPDATEWULF_SHELL_SHOWN
 set -g UPDATEWULF_SHELL_SHOWN 1
 __UPDATEWULF_LINE__ 2>/dev/null
end
""".replace("__UPDATEWULF_LINE__", command)
    tcsh = """if ( $?prompt ) then
 if ( ! $?UPDATEWULF_SHELL_SHOWN ) then
  set UPDATEWULF_SHELL_SHOWN=1
  __UPDATEWULF_LINE__
 endif
endif
""".replace("__UPDATEWULF_LINE__", command)
    for name, body in [("prompt.bash",bash),("prompt.sh",bash),("prompt.zsh",zsh),("prompt.fish",fish),("prompt.tcsh",tcsh)]:
        atomic_write(hookdir / name, body)
    path_hook = 'case ":$PATH:" in *":$HOME/.local/bin:"*) ;; *) PATH="$HOME/.local/bin:$PATH"; export PATH ;; esac'
    changed = [
        managed(home / ".bashrc", path_hook + "\n. " + q(str(hookdir / "prompt.bash"))),
        managed(home / ".zshrc", path_hook + "\nsource " + q(str(hookdir / "prompt.zsh"))),
        managed(home / ".config/fish/config.fish", "source " + q(str(hookdir / "prompt.fish"))),
        managed(home / ".shrc", ". " + q(str(hookdir / "prompt.sh"))),
        managed(home / ".kshrc", ". " + q(str(hookdir / "prompt.sh"))),
        managed(home / ".tcshrc", "source " + q(str(hookdir / "prompt.tcsh"))),
    ]
    login = next((home / n for n in [".bash_profile", ".bash_login", ".profile"] if (home / n).exists()), home / ".profile")
    login_old = login.read_text(encoding="utf-8") if login.exists() else ""
    bash_login = "" if ".bashrc" in login_old else '[ -n "${BASH_VERSION-}" ] && [ -r "$HOME/.bashrc" ] && . "$HOME/.bashrc"\n'
    changed.append(managed(
        login,
        path_hook + "\n" + bash_login +
        '[ -n "${BASH_VERSION-}" ] && . ' + q(str(hookdir / "prompt.bash")) + "\n" +
        '[ -z "${BASH_VERSION-}${ZSH_VERSION-}" ] && [ -z "${ENV-}" ] && ENV="$HOME/.config/pc-mesh/prompt.sh" && export ENV'
    ))
    bindir = home / ".local/bin"
    bindir.mkdir(parents=True, exist_ok=True)
    for name, action in [("UpdateWulf",""),("updatewulf",""),("pc-mesh",""),("pc-mesh-watch","watch")]:
        path = bindir / name
        prefix = (action + " ") if action else ""
        atomic_write(path, "#!/bin/sh\nexec " + q(sys.executable) + " " + q(str(source / "pc_mesh.py")) + " " + prefix + '--state ' + q(str(cache)) + ' "$@"\n')
        path.chmod(0o755)
    return changed


def read_crontab():
    if not shutil.which("crontab"):
        return None
    result = subprocess.run(["crontab","-l"], text=True, capture_output=True)
    if result.returncode not in (0,1):
        raise RuntimeError(result.stderr)
    return result.stdout if result.returncode == 0 else ""


def clean_project_cron(text):
    text = re.sub(r"(?ms)^# BEGIN PC-MESH\n.*?^# END PC-MESH\n?", "", text)
    return re.sub(r"(?ms)^# BEGIN UPDATEWULF\n.*?^# END UPDATEWULF\n?", "", text)


def systemd_quote(value):
    return '"' + str(value).replace("\\","\\\\").replace('"','\\"') + '"'


def enable_user_service(source, config, state):
    if not shutil.which("systemctl"):
        return None
    userdir = Path.home() / ".config/systemd/user"
    userdir.mkdir(parents=True, exist_ok=True)
    unit = userdir / "updatewulf.service"
    text = """[Unit]
Description=UpdateWulf persistent update-status service
After=network-online.target

[Service]
Type=simple
ExecStart=__PYTHON__ __SCRIPT__ daemon --config __CONFIG__ --state __STATE__
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
"""
    for key,value in {
        "__PYTHON__":sys.executable, "__SCRIPT__":source/"pc_mesh.py",
        "__CONFIG__":config, "__STATE__":state
    }.items():
        text=text.replace(key,systemd_quote(value))
    atomic_write(unit,text)
    if subprocess.run(["systemctl","--user","daemon-reload"],capture_output=True).returncode:
        return None
    if subprocess.run(["systemctl","--user","enable","--now","updatewulf.service"],capture_output=True).returncode:
        return None
    old=read_crontab()
    if old is not None and clean_project_cron(old) != old:
        subprocess.run(["crontab","-"],input=clean_project_cron(old),text=True,check=True)
    return "SYSTEMD_USER"


def enable_boot_fallback(source, config, state):
    old=read_crontab()
    if old is None:
        raise RuntimeError("neither systemd user services nor crontab are available")
    q=shlex.quote
    command="exec "+q(sys.executable)+" "+q(str(source/"pc_mesh.py"))+" daemon --config "+q(str(config))+" --state "+q(str(state))
    clean=clean_project_cron(old).rstrip()
    new=(clean+"\n" if clean else "")+"# BEGIN UPDATEWULF\n@reboot "+command+" >>"+q(str(state/"service.log"))+" 2>&1\n# END UPDATEWULF\n"
    subprocess.run(["crontab","-"],input=new,text=True,check=True)
    options={"creationflags":subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW} if os.name=="nt" else {"start_new_session":True}
    with open(state/"launcher.log","ab") as log:
        subprocess.Popen([sys.executable,str(source/"pc_mesh.py"),"daemon","--config",str(config),"--state",str(state)],
                         stdin=subprocess.DEVNULL,stdout=log,stderr=log,**options)
    return "CRON_REBOOT_ONLY"


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source",type=Path,default=Path(__file__).resolve().parent)
    ap.add_argument("--config",type=Path,default=Path.home()/".config/pc-mesh/config.json")
    ap.add_argument("--state",type=Path,default=Path.home()/".local/state/pc-mesh")
    ap.add_argument("--prompt-only",action="store_true")
    args=ap.parse_args()
    source=args.source.resolve(); config=args.config.resolve(); state=args.state.resolve()
    # Reject incomplete source/config before hooks can change any owner profile.
    for relative in ("pc_mesh.py", "update_control.py", "apply_updates.py",
                     "self_update.py", "tui.py", "owner_profiles.py",
                     "hooks/updatewulf.bash.in"):
        path = source / relative
        if not path.is_file():
            ap.error("incomplete UpdateWulf source: " + relative)
        try:
            with path.open("rb") as stream:
                stream.read(1)
        except OSError:
            ap.error("unreadable UpdateWulf source: " + relative)
    try:
        (source / "hooks/updatewulf.bash.in").read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        ap.error("UpdateWulf Bash prompt hook must be readable UTF-8")
    if not args.prompt_only:
        try:
            configured = json.loads(config.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, ValueError):
            ap.error("a readable JSON config must exist before service installation")
        if not isinstance(configured, dict):
            ap.error("config must contain a JSON object")
    paths=hooks(source,state,Path.home())
    result={"user_home":str(Path.home()),"profiles":paths,"shell":"CACHED_BASH_PREPROMPT_AND_PASSIVE_OTHERS"}
    if not args.prompt_only:
        state.mkdir(parents=True,exist_ok=True)
        old=read_crontab()
        if old:
            save_json(state/("crontab-backup-"+str(int(time.time()))),{"content":old},True)
        scheduler=enable_user_service(source,config,state) or enable_boot_fallback(source,config,state)
        result["scheduler"]=scheduler
    save_json(Path.home()/".config/pc-mesh/installation.json",result)
    print(json.dumps(result))


if __name__=="__main__":
    main()
