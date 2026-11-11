param(
    [string]$Source = $PSScriptRoot,
    [string]$Python = (Get-Command python -ErrorAction SilentlyContinue).Source,
    [string]$State,
    [string]$Config = "$env:USERPROFILE\.config\pc-mesh\config.json",
    [switch]$PromptOnly,
    [string]$Clink
)
$ErrorActionPreference = 'Stop'
$record = Join-Path $env:USERPROFILE '.config\pc-mesh\installation.json'
$oldInstall = if (Test-Path -LiteralPath $record) { Get-Content -LiteralPath $record -Raw | ConvertFrom-Json } else { $null }
if (-not $State) {
    $State = if ($oldInstall.state) { $oldInstall.state } else { Join-Path $env:USERPROFILE '.local\state\pc-mesh' }
}
if (-not $Python -or $Python -like '*WindowsApps*' -or -not (Test-Path -LiteralPath $Python)) { throw 'A real Python 3.9+ interpreter is required; the Windows Store alias is insufficient' }
& $Python -c 'import sys; assert sys.version_info >= (3,9)'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.9+ validation failed' }
# An incomplete release must never become the active Windows worker.
foreach($required in @('pc_mesh.py','update_control.py','apply_updates.py','apply_windows.ps1')) {
    if (-not (Test-Path -LiteralPath (Join-Path $Source $required) -PathType Leaf)) {
        throw "Incomplete UpdateWulf release: missing $required"
    }
}


function Quote-Ps([string]$s) { "'" + $s.Replace("'", "''") + "'" }
function Managed-Profile([string]$path, [string]$body) {
    $old = if (Test-Path -LiteralPath $path) { [IO.File]::ReadAllText($path) } else { '' }
    if ($old.Contains('# BEGIN PC-MESH') -and -not $old.Contains('# END PC-MESH')) { throw "Incomplete block in $path" }
    $block = "# BEGIN PC-MESH`r`n$body`r`n# END PC-MESH`r`n"
    $pattern = '(?ms)^# BEGIN PC-MESH\r?\n.*?^# END PC-MESH(?:\r?\n|$)'
    $new = if ([regex]::IsMatch($old, $pattern)) { [regex]::Replace($old, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{param($m) $block}) } else { $old.TrimEnd() + "`r`n`r`n" + $block }
    if ($new -ne $old) {
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($path)) | Out-Null
        if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination ($path + '.pc-mesh-backup-' + (Get-Date -Format yyyyMMdd-HHmmss)) }
        [IO.File]::WriteAllText($path, $new, (New-Object Text.UTF8Encoding($true)))
    }
}

$documents = [Environment]::GetFolderPath('MyDocuments')
$body = '$global:PcMeshPython = ' + (Quote-Ps $Python) + "`r`n" +
        '$global:PcMeshScript = ' + (Quote-Ps (Join-Path $Source 'pc_mesh.py')) + "`r`n" +
        '$global:PcMeshState = ' + (Quote-Ps $State) + "`r`n. " + (Quote-Ps (Join-Path $Source 'prompt_windows.ps1'))
$profiles = @()
foreach ($family in @('WindowsPowerShell','PowerShell')) {
    foreach ($name in @('profile.ps1','Microsoft.PowerShell_profile.ps1','Microsoft.VSCode_profile.ps1')) {
        $p = Join-Path (Join-Path $documents $family) $name
        Managed-Profile $p $body
        $profiles += $p
    }
}

$configDir = Join-Path $env:USERPROFILE '.config\pc-mesh'
[IO.Directory]::CreateDirectory($configDir) | Out-Null
$cliDir = Join-Path $env:USERPROFILE '.local\bin'
[IO.Directory]::CreateDirectory($cliDir) | Out-Null
foreach ($entry in @(@('UpdateWulf',''),@('updatewulf',''),@('pc-mesh',''),@('pc-mesh-watch','watch '))) {
    $wrapper = '@echo off' + "`r`n" + '"' + $Python + '" "' + (Join-Path $Source 'pc_mesh.py') + '" ' + $entry[1] + '%* --state "' + $State + '"' + "`r`n"
    [IO.File]::WriteAllText((Join-Path $cliDir ($entry[0]+'.cmd')), $wrapper, (New-Object Text.ASCIIEncoding))
}
$pathParts = @([Environment]::GetEnvironmentVariable('PATH','User') -split ';' | Where-Object {$_})
if ($pathParts -notcontains $cliDir) { [Environment]::SetEnvironmentVariable('PATH',($cliDir + ';' + ($pathParts -join ';')),'User') }
if (($env:PATH -split ';') -notcontains $cliDir) { $env:PATH = $cliDir + ';' + $env:PATH }

$scheduler = if ($PromptOnly -and $oldInstall.scheduler) { $oldInstall.scheduler } else { 'PROMPT_ONLY' }
if (-not $PromptOnly) {
    if (-not (Test-Path -LiteralPath $Config)) { throw 'Configuration required before service installation' }
    [IO.Directory]::CreateDirectory($State) | Out-Null

    $stopRequest = Join-Path $State 'stop.request'
    $heartbeat = Join-Path $State 'heartbeat.json'
    function Get-LiveUpdateWulfPid {
        if (-not (Test-Path -LiteralPath $heartbeat)) { return 0 }
        try {
            $value = [int]((Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json).pid)
            if ($value -gt 0 -and (Get-Process -Id $value -ErrorAction SilentlyContinue)) { return $value }
        } catch {}
        return 0
    }

    # Preserve scheduler definitions before changing them. This gives the
    # handover a real rollback path without killing a service process.
    $oldUserTask = Get-ScheduledTask -TaskName 'UpdateWulf-User' -ErrorAction SilentlyContinue
    $oldUserXml = if ($oldUserTask) { Export-ScheduledTask -TaskName 'UpdateWulf-User' } else { $null }
    $legacy = Get-ScheduledTask -TaskName 'PC-Mesh' -ErrorAction SilentlyContinue
    $legacyManaged = $false
    $legacyXml = $null
    if ($legacy) {
        $legacyText = @($legacy.Actions | ForEach-Object { [string]$_.Execute + ' ' + [string]$_.Arguments }) -join ';'
        # The v1 task points to the *previous* source tree, not the new release.
        # Retire only a precisely recognized v1 owner task for this same user,
        # config and state; never remove an unrelated task by name alone.
        $principal = [string]$legacy.Principal.UserId
        $ownerName = ([Security.Principal.WindowsIdentity]::GetCurrent().Name -split '\\')[-1]
        $legacyManaged = ($legacyText -match 'manage\.py"?\s+ensure\b') -and
                         $legacyText.Contains([string]$Config) -and
                         $legacyText.Contains([string]$State) -and
                         ($principal -ieq $ownerName -or $principal -ieq [Security.Principal.WindowsIdentity]::GetCurrent().Name)
        if ($legacyManaged) { $legacyXml = Export-ScheduledTask -TaskName 'PC-Mesh' }
    }

    $args = '"' + (Join-Path $Source 'pc_mesh.py') + '" daemon --config "' + $Config + '" --state "' + $State + '"'
    # Keep the persistent worker independent of console windows being closed.
    # CLI wrappers continue to use the normal console interpreter.
    $backgroundPython = Join-Path (Split-Path -Parent $Python) 'pythonw.exe'
    $workerPython = if (Test-Path -LiteralPath $backgroundPython) { $backgroundPython } else { $Python }
    $action = New-ScheduledTaskAction -Execute $workerPython -Argument $args -WorkingDirectory $Source
    $login = New-ScheduledTaskTrigger -AtLogOn -User ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
    # Preserve an explicitly elevated owner task during future reinstalls.
    # Never elevate a previously limited task without owner authorization.
    $level = if ($oldUserTask -and $oldUserTask.Principal.RunLevel -eq 'Highest') { 'Highest' } else { 'Limited' }
    if ($level -eq 'Highest' -and -not ([Security.Principal.WindowsPrincipal]::new([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw 'Existing elevated UpdateWulf task requires an elevated owner console for reinstallation'
    }
    $principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel $level
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
    Register-ScheduledTask -TaskName 'UpdateWulf-User' -Action $action -Trigger $login -Principal $principal -Settings $settings -Description 'One persistent UpdateWulf worker; no periodic launcher' -Force | Out-Null
    # Keep the old boot task as rollback until the new worker has proven alive.

    $oldPid = Get-LiveUpdateWulfPid
    try {
        if ($oldPid -gt 0) {
            New-Item -ItemType File -Path $stopRequest -Force | Out-Null
            $deadline = (Get-Date).AddSeconds(45)
            while ((Get-Date) -lt $deadline -and (Get-Process -Id $oldPid -ErrorAction SilentlyContinue)) {
                Start-Sleep -Milliseconds 500
            }
            if (Get-Process -Id $oldPid -ErrorAction SilentlyContinue) {
                throw 'Existing UpdateWulf worker did not stop cooperatively; it was not force-killed.'
            }
        }
        Remove-Item -LiteralPath $stopRequest -Force -ErrorAction SilentlyContinue

        $started = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
        Start-ScheduledTask -TaskName 'UpdateWulf-User'
        $deadline = (Get-Date).AddSeconds(45)
        $healthy = $false
        while ((Get-Date) -lt $deadline -and -not $healthy) {
            if (Test-Path -LiteralPath $heartbeat) {
                try {
                    $hb = Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
                    $healthy = ([double]$hb.at -ge ($started - 2)) -and
                               ([int]$hb.pid -gt 0) -and
                               [bool](Get-Process -Id ([int]$hb.pid) -ErrorAction SilentlyContinue)
                } catch { $healthy = $false }
            }
            if (-not $healthy) { Start-Sleep -Milliseconds 500 }
        }
        if (-not $healthy) { throw 'New UpdateWulf user worker did not publish a fresh heartbeat.' }
        if ($legacyManaged) { Unregister-ScheduledTask -TaskName 'PC-Mesh' -Confirm:$false }
    } catch {
        Remove-Item -LiteralPath $stopRequest -Force -ErrorAction SilentlyContinue
        if ($oldUserXml) {
            Register-ScheduledTask -TaskName 'UpdateWulf-User' -Xml $oldUserXml -Force | Out-Null
        } else {
            Unregister-ScheduledTask -TaskName 'UpdateWulf-User' -Confirm:$false -ErrorAction SilentlyContinue
        }
        if ($legacyXml) { Register-ScheduledTask -TaskName 'PC-Mesh' -Xml $legacyXml -Force | Out-Null }
        if ((Get-LiveUpdateWulfPid) -eq 0) {
            if ($oldUserXml) { Start-ScheduledTask -TaskName 'UpdateWulf-User' -ErrorAction SilentlyContinue }
            elseif ($legacyXml) { Start-ScheduledTask -TaskName 'PC-Mesh' -ErrorAction SilentlyContinue }
        }
        throw
    }
    $scheduler = 'TASK_SCHEDULER_DIRECT_DAEMON_AT_LOGON'
}
[pscustomobject]@{
    profiles=$profiles
    state=$State
    scheduler=$scheduler
    shell='PASSIVE_STARTUP_LINE_ONLY'
    command='UpdateWulf'
    user=[Security.Principal.WindowsIdentity]::GetCurrent().Name
} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath $record -Encoding UTF8
Get-Content -LiteralPath $record
