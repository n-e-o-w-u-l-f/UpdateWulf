"""Durable, scoped LAN requests. No shell strings or privilege escalation."""
import ctypes
import json
import os
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

ACTIONS = {"refresh", "sync", "install"}
TERMINAL = {"SUCCEEDED", "FAILED", "NEEDS_ADMIN", "EXPIRED", "INTERRUPTED"}
ID = re.compile(r"^[a-f0-9]{24}$")


class ControlQueue:
    def __init__(self, path, members, read_json, save_json):
        self.path, self.members, self.save = Path(path), members, save_json
        self.jobs = read_json(self.path, [])
        self.guard = threading.RLock()

    def persist(self):
        # Retain every active request and a bounded recent audit history.
        active = [j for j in self.jobs if j["status"] not in TERMINAL]
        done = [j for j in self.jobs if j["status"] in TERMINAL][-100:]
        self.jobs = done + active
        self.save(self.path, self.jobs, True)

    def enqueue(self, caller, target, action, request_id):
        if target not in self.members or action not in ACTIONS or not isinstance(request_id, str) or not ID.fullmatch(request_id):
            raise ValueError("invalid target, action or request id")
        if caller != "operator" and caller != target:
            raise PermissionError("control of another host requires an operator token")
        if action == "install" and not self.members[target].get("allow_install", False):
            raise PermissionError("package installation is not enabled for this host")
        with self.guard:
            for job in self.jobs:
                if job["status"] == "QUEUED" and time.time() > job["expires_at"]:
                    job.update(status="EXPIRED", finished_at=time.time())
            existing = next((j for j in self.jobs if j["request_id"] == request_id), None)
            if existing:
                if (existing["target"], existing["action"], existing["caller"]) != (target, action, caller):
                    raise ValueError("request id already belongs to a different request")
                return dict(existing)
            if any(j["target"] == target and j["status"] not in TERMINAL for j in self.jobs):
                raise ValueError("this host already has an active request")
            job = {"id": secrets.token_hex(12), "request_id": request_id, "target": target,
                   "action": action, "caller": caller, "status": "QUEUED", "at": time.time(),
                   "expires_at": time.time() + 600}
            self.jobs.append(job)
            self.persist()
            return dict(job)

    def enqueue_many(self, caller, requests):
        if not isinstance(requests, list) or not requests or len(requests) > 100:
            raise ValueError("invalid control batch")
        with self.guard:
            now=time.time()
            for job in self.jobs:
                if job["status"] == "QUEUED" and now > job["expires_at"]:
                    job.update(status="EXPIRED", finished_at=now)

            candidates=[]
            results=[]
            seen_targets=set()
            seen_requests=set()
            for item in requests:
                if not isinstance(item, dict):
                    raise ValueError("invalid control batch item")
                target=item.get("target")
                action=item.get("action")
                request_id=item.get("request_id")
                if target not in self.members or action not in ACTIONS or not isinstance(request_id,str) or not ID.fullmatch(request_id):
                    raise ValueError("invalid target, action or request id")
                if target in seen_targets or request_id in seen_requests:
                    raise ValueError("duplicate target or request id in control batch")
                seen_targets.add(target);seen_requests.add(request_id)
                if caller != "operator" and caller != target:
                    raise PermissionError("control of another host requires an operator token")
                if action == "install" and not self.members[target].get("allow_install",False):
                    raise PermissionError("package installation is not enabled for this host")
                existing=next((j for j in self.jobs if j["request_id"]==request_id),None)
                if existing:
                    if (existing["target"],existing["action"],existing["caller"]) != (target,action,caller):
                        raise ValueError("request id already belongs to a different request")
                    results.append(("existing",existing))
                    continue
                if any(j["target"]==target and j["status"] not in TERMINAL for j in self.jobs):
                    raise ValueError("this host already has an active request")
                job={"id":secrets.token_hex(12),"request_id":request_id,"target":target,
                     "action":action,"caller":caller,"status":"QUEUED","at":now,
                     "expires_at":now+600}
                candidates.append(job)
                results.append(("new",job))

            before=list(self.jobs)
            self.jobs.extend(candidates)
            try:
                self.persist()
            except Exception:
                self.jobs=before
                raise
            return [dict(job) for _,job in results]

    def pending(self, member):
        if member not in self.members:
            raise PermissionError("a host credential is required")
        with self.guard:
            for job in self.jobs:
                if job["status"] == "QUEUED" and time.time() > job["expires_at"]:
                    job.update(status="EXPIRED", finished_at=time.time())
            self.persist()
            return [dict(j) for j in self.jobs if j["target"] == member and j["status"] == "QUEUED"]

    def result(self, member, job_id, status, detail=""):
        if member not in self.members or status not in TERMINAL | {"RUNNING"}:
            raise ValueError("invalid result")
        with self.guard:
            job = next((j for j in self.jobs if j["id"] == job_id and j["target"] == member), None)
            if not job:
                raise PermissionError("request does not belong to this host")
            if job["status"] in TERMINAL:
                return dict(job)
            if status == "RUNNING" and job["status"] != "QUEUED":
                return dict(job, claimed=False)
            job.update(status=status, detail=re.sub(r"[\x00-\x1f\x7f]", " ", str(detail))[:350], updated_at=time.time())
            self.persist()
            return dict(job, claimed=status == "RUNNING")

    def snapshot(self):
        with self.guard:
            return [dict(j) for j in self.jobs[-100:]]


def can_install():
    if os.name == "nt":
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    # Termux packages belong to the Android app account, not root.
    return os.geteuid() == 0 or os.environ.get("PREFIX", "").startswith("/data/data/com.termux/")


def run_install(source, state, save_json, native=False):
    if native:
        status_path = (Path(os.environ.get("ProgramData", "C:/ProgramData")) / "PC-Mesh-Installer/status.json") if os.name == "nt" else Path("/var/lib/pc-mesh-installer/status.json")
        previous = json.loads(status_path.read_text()) if status_path.exists() else {}
        if previous.get("status") == "RUNNING":
            return "FAILED", "Native installation is already running; inspect the native status/log."
        began = time.time()
        if os.name == "nt":
            ps = str(Path(os.environ.get("SystemRoot", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe")
            args = [ps, "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", "Start-ScheduledTask -TaskName 'PC-Mesh-Install' -ErrorAction Stop"]
        else:
            args = ["systemctl", "start", "--no-block", "pc-mesh-install.service"]
        request = subprocess.run(args, stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
        if request.returncode:
            return "NEEDS_ADMIN", "Native installer is not enabled for this service account; run enable_machine_updates at the owner console."
        handshake = time.time() + 30
        while True:
            try:
                status = json.loads(status_path.read_text())
            except (ValueError, OSError):
                status = {}
            if status.get("started_at", 0) >= began - 1:
                if status.get("status") in ("SUCCEEDED", "FAILED"):
                    return status["status"], "Native installer exit %s; %s" % (status.get("exit"), status_path)
                handshake = float("inf")  # Observe the real installer; never kill it on a CLI timeout.
            if time.time() > handshake:
                return "FAILED", "Native installer did not expose a new start; inspect the native scheduler."
            time.sleep(2)
    if not can_install():
        return "NEEDS_ADMIN", "Native administrator/root service is required; no elevation was attempted."
    opts = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == "nt" else {}
    with open(Path(state) / "update-install.log", "ab") as log:
        child = subprocess.Popen([sys.executable, str(Path(source) / "apply_updates.py")],
                                 stdin=subprocess.DEVNULL, stdout=log, stderr=log, **opts)
        save_json(Path(state) / "installer.json", {"pid": child.pid, "started_at": time.time(), "status": "RUNNING"})
        # Never kill a package manager to satisfy a CLI timeout. Reports and
        # heartbeat continue in separate threads while installation completes.
        rc = child.wait()
        save_json(Path(state) / "installer.json", {"pid": child.pid, "finished_at": time.time(), "exit": rc,
                                                   "status": "SUCCEEDED" if rc == 0 else "FAILED"})
    return ("SUCCEEDED" if rc == 0 else "FAILED"), "Native installer exit %s; see update-install.log" % rc


def worker(client, state, stopping, refresh, sync, install, read_json, save_json, log, allowed_actions=ACTIONS):
    path = Path(state) / "executed-commands.json"
    completed = read_json(path, {})
    # An interrupted install is never repeated automatically after a restart.
    for job_id, entry in list(completed.items()):
        if entry["status"] == "RUNNING":
            entry.update(status="INTERRUPTED", detail="Worker restarted during execution; inspect installer.json and native package logs.")
    save_json(path, completed, True)
    while not stopping.is_set():
        try:
            for job_id, entry in list(completed.items()):
                if not entry.get("acknowledged") and entry["status"] in TERMINAL:
                    client.request("/command-result", {"id": job_id, "status": entry["status"], "detail": entry.get("detail", "")})
                    entry["acknowledged"] = True
                    save_json(path, completed, True)
            for job in client.request("/commands").get("commands", []):
                job_id = job.get("id", "")
                if not ID.fullmatch(job_id) or job.get("action") not in ACTIONS & set(allowed_actions) or time.time() > job.get("expires_at", 0):
                    continue
                if job_id in completed:
                    continue
                # Persist before claiming/executing; a lost HTTP response cannot
                # cause a second package installation with this request ID.
                completed[job_id] = {"status": "RUNNING", "action": job["action"], "at": time.time()}
                save_json(path, completed, True)
                try:
                    claim = client.request("/command-result", {"id": job_id, "status": "RUNNING"})
                    if claim.get("status") != "RUNNING" or not claim.get("claimed"):
                        completed[job_id].update(status="INTERRUPTED", acknowledged=True)
                        save_json(path, completed, True)
                        continue
                    if job["action"] == "refresh":
                        data = refresh()
                        status = "SUCCEEDED" if data.get("status") in ("OK", "CACHED") else "FAILED"
                        detail = "Remaining updates: %s" % data.get("count")
                    elif job["action"] == "sync":
                        results = sync()
                        status = "FAILED" if any(r["status"] in {"ERROR", "AUTH_OR_NETWORK_ERROR", "FF_FAILED", "VERIFY_FAILED"} for r in results) else "SUCCEEDED"
                        detail = "Repository states: " + ", ".join(sorted({r["status"] for r in results}))
                    else:
                        status, detail = install()
                        if status != "NEEDS_ADMIN":
                            refresh()  # A successful installer is not a zero-count assumption.
                except Exception as e:
                    status, detail = "FAILED", str(e)[:350]
                completed[job_id].update(status=status, detail=detail, finished_at=time.time())
                # Bound terminal history while retaining unacknowledged work.
                acknowledged = [k for k, v in completed.items() if v.get("acknowledged")]
                for k in acknowledged[:-100]:
                    completed.pop(k)
                save_json(path, completed, True)
                client.request("/command-result", {"id": job_id, "status": status, "detail": detail})
                completed[job_id]["acknowledged"] = True
                save_json(path, completed, True)
        except Exception as e:
            log.warning("control: %s", e)
        stopping.wait(5)
