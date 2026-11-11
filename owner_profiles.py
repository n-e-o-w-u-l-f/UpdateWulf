#!/usr/bin/env python3
"""One-time owner-profile enrollment through ordinary authenticated SSH.

Optional auth input lives in a mode-600 file outside Git and is removed after
provisioning. This helper does not elevate accounts or modify SSH permissions.
Paramiko is an enrollment dependency only, not a daemon dependency.
"""
import argparse
import json
import shlex
from pathlib import Path
import paramiko

ap = argparse.ArgumentParser()
ap.add_argument('--input', type=Path, required=True)
ap.add_argument('--output', type=Path, required=True)
args = ap.parse_args()
jobs = json.loads(args.input.read_text())
results = []
for job in jobs:
    client = paramiko.SSHClient()
    client.load_system_host_keys(str(Path.home() / '.ssh/known_hosts'))
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(job['host'], port=job.get('port',22), username=job['user'], password=job.get('password'),
                       key_filename=job.get('key'), timeout=8, banner_timeout=8, auth_timeout=8,
                       look_for_keys=False, allow_agent=False)
        source, state = job['source'], job['state']
        if job.get('windows'):
            if job.get('enable_default_profiles'):
                # Normal per-user profile setup only when every execution-policy
                # scope is still the Windows default. Never bypass an explicit
                # user, administrator or organization execution policy.
                setup = "powershell.exe -NoLogo -NoProfile -NonInteractive -Command \"$p=Get-ExecutionPolicy -List; if(@($p | Where-Object {$_.ExecutionPolicy -ne 'Undefined'}).Count -eq 0){$d=Join-Path $env:USERPROFILE '.config\\pc-mesh'; New-Item -ItemType Directory -Path $d -Force | Out-Null; 'Undefined' | Set-Content (Join-Path $d 'execution_policy_previous.txt'); Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force}; Get-ExecutionPolicy\""
                _, policy_out, policy_err = client.exec_command(setup, timeout=30)
                policy_text, policy_error = policy_out.read().decode(errors='replace'), policy_err.read().decode(errors='replace')
                if policy_out.channel.recv_exit_status():
                    raise RuntimeError(policy_error[-300:])
            command = 'powershell.exe -NoLogo -NoProfile -NonInteractive -File "' + source + '\\install_windows.ps1" -PromptOnly -Source "' + source + '" -State "' + state + '" -Clink "' + job['clink'] + '"'
        else:
            command = ' '.join(shlex.quote(s) for s in [job.get('python','python3'), source+'/install.py','--source',source,'--state',state,'--prompt-only'])
        _, out, err = client.exec_command(command, timeout=45)
        stdout, stderr = out.read().decode(errors='replace'), err.read().decode(errors='replace')
        rc = out.channel.recv_exit_status()
        results.append({'host':job['host'],'user':job['user'],'exit':rc,'out':stdout[-4000:],'error':stderr[-1000:]})
    except Exception as e:
        results.append({'host':job['host'],'user':job['user'],'exit':None,'error':str(e)[:400]})
    finally:
        client.close()
    args.output.write_text(json.dumps(results, indent=2)+'\n')
print(json.dumps(results))
