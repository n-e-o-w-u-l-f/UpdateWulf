param(
    [string]$Source = $PSScriptRoot,
    [Parameter(Mandatory=$true)][string]$Python,
    [string]$Config = "$env:USERPROFILE\.config\pc-mesh\config.json",
    [string]$Owner = ([Security.Principal.WindowsIdentity]::GetCurrent().Name)
)
$ErrorActionPreference = 'Stop'

function Get-UpdateWulfOwnerState {
    $record = Join-Path $env:USERPROFILE '.config\pc-mesh\installation.json'
    if (Test-Path -LiteralPath $record) {
        try {
            $installation = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
            if ($installation.state) { return [string]$installation.state }
        } catch {}
    }
    $task = Get-ScheduledTask -TaskName 'UpdateWulf-User' -ErrorAction SilentlyContinue
    if ($task) {
        foreach ($action in @($task.Actions)) {
            if ([string]$action.Arguments -match '--state\s+"([^"]+)"') { return $Matches[1] }
        }
    }
    return $null
}

function Stop-UpdateWulfOwnerWorker([string]$OwnerState) {
    if (-not $OwnerState) { return }
    $heartbeat = Join-Path $OwnerState 'heartbeat.json'
    if (-not (Test-Path -LiteralPath $heartbeat)) { return }
    $pidValue = 0
    try { $pidValue = [int]((Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json).pid) } catch { $pidValue = 0 }
    if ($pidValue -le 0 -or -not (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) { return }
    $request = Join-Path $OwnerState 'stop.request'
    New-Item -ItemType File -Path $request -Force | Out-Null
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline -and (Get-Process -Id $pidValue -ErrorAction SilentlyContinue)) {
        Start-Sleep -Milliseconds 500
    }
    if (Get-Process -Id $pidValue -ErrorAction SilentlyContinue) {
        throw 'Existing UpdateWulf user worker did not stop cooperatively; SYSTEM takeover aborted without force-kill.'
    }
    Remove-Item -LiteralPath $request -Force -ErrorAction SilentlyContinue
}

$principal = [Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run at an actual elevated owner console; this installer never invokes elevation.' }
$sid = (New-Object Security.Principal.NTAccount($Owner)).Translate([Security.Principal.SecurityIdentifier])
$base = Join-Path $env:ProgramData 'PC-Mesh-Installer'
function Protect-Directory([string]$path, [bool]$Private=$false) {
    if ((Test-Path -LiteralPath $path) -and ((Get-Item -LiteralPath $path).Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Reparse directory refused: $path" }
    [IO.Directory]::CreateDirectory($path) | Out-Null
    $acl = New-Object Security.AccessControl.DirectorySecurity
    $acl.SetAccessRuleProtection($true,$false)
    $acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    $pairs = @(@('S-1-5-18','FullControl'),@('S-1-5-32-544','FullControl'))
    if (-not $Private) { $pairs += ,@('S-1-5-32-545','ReadAndExecute') }
    foreach ($pair in $pairs) {
        $identity = New-Object Security.Principal.SecurityIdentifier($pair[0])
        $rule = New-Object Security.AccessControl.FileSystemAccessRule($identity,$pair[1],'ContainerInherit,ObjectInherit','None','Allow')
        $acl.AddAccessRule($rule)
    }
    Set-Acl -LiteralPath $path -AclObject $acl
}
Protect-Directory $base
$code = Join-Path $base 'code'
$runtime = Join-Path $base 'python'
Protect-Directory $code
Protect-Directory $runtime
# SYSTEM never executes a Python binary or script writable by the service user.
$pythonFolder = Split-Path -Parent $Python
Get-ChildItem -LiteralPath $pythonFolder | Copy-Item -Destination $runtime -Recurse -Force
Get-ChildItem -LiteralPath $Source -Filter '*.py' | Copy-Item -Destination $code -Force
Get-ChildItem -LiteralPath $Source -Filter '*.ps1' | Copy-Item -Destination $code -Force
$machinePython = Join-Path $runtime 'python.exe'
Get-ChildItem -LiteralPath $runtime -Filter '*._pth' | ForEach-Object {
    $lines = [IO.File]::ReadAllLines($_.FullName) | Where-Object {$_ -notmatch 'pc-mesh'}
    [IO.File]::WriteAllLines($_.FullName,@($lines)+@($code))
}
$client = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$cert = Join-Path $base 'hub.crt'
Copy-Item -LiteralPath $client.certificate -Destination $cert -Force
$client.certificate = $cert
$client.hubs = @($client.hubs | Where-Object {$_ -notmatch '127\.0\.0\.1'})
# A separate SYSTEM key handles pre-login LAN transport when the direct HTTPS
# port is unreachable. Generate it here; never copy the user's private SSH key.
if ($client.ssh_tunnel) {
    $transport = Join-Path $base 'transport'
    $sshRuntime = Join-Path $base 'ssh'
    Protect-Directory $transport $true
    Protect-Directory $sshRuntime
    $original = $client.ssh_tunnel
    $sshDirectory = Split-Path -Parent $original.ssh
    if (-not (Test-Path (Join-Path $sshDirectory 'ssh-keygen.exe'))) { throw 'The tested SSH runtime must also provide ssh-keygen.exe' }
    Get-ChildItem -LiteralPath $sshDirectory -Filter '*.dll' | Copy-Item -Destination $sshRuntime -Force
    foreach ($name in @('ssh.exe','ssh-keygen.exe')) { Copy-Item -LiteralPath (Join-Path $sshDirectory $name) -Destination $sshRuntime -Force }
    $machineKey = Join-Path $transport 'hub_transport_key'
    if (-not (Test-Path -LiteralPath $machineKey)) {
        & $machinePython -c "import subprocess,sys; subprocess.run([sys.argv[1],'-t','ed25519','-N','','-f',sys.argv[2],'-C','pc-mesh-machine-forward-only'],check=True,capture_output=True)" (Join-Path $sshRuntime 'ssh-keygen.exe') $machineKey
        if ($LASTEXITCODE -ne 0) { throw 'Machine key generation failed; existing user key was preserved' }
    }
    $machineKnown = Join-Path $transport 'known_hosts'
    Copy-Item -LiteralPath $original.known_hosts -Destination $machineKnown -Force
    & $machinePython (Join-Path $code 'enroll_machine_transport.py') --config $Config --key $machineKey
    if ($LASTEXITCODE -ne 0) { throw 'Existing authenticated owner SSH is required to enroll the restricted machine public key' }
    $client.ssh_tunnel = [pscustomobject]@{ssh=(Join-Path $sshRuntime 'ssh.exe');key=$machineKey;known_hosts=$machineKnown;port=19898;host=$original.host;user=$original.user}
    $client.hubs = @('https://127.0.0.1:19898') + @($client.hubs)
} elseif (-not $client.hubs.Count) { throw 'A direct trusted HTTPS LAN hub address or existing authenticated SSH transport is required' }
$client | Add-Member -NotePropertyName announce_only -NotePropertyValue $true -Force
$client | Add-Member -NotePropertyName machine_control -NotePropertyValue $true -Force
$client | Add-Member -NotePropertyName native_installer -NotePropertyValue $true -Force
$client.repositories = @()
$client.PSObject.Properties.Remove('hub')
$machineConfig = Join-Path $base 'config.json'
$client | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $machineConfig -Encoding UTF8
$acl = New-Object Security.AccessControl.FileSecurity
$acl.SetAccessRuleProtection($true,$false)
$acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
foreach ($identity in @('S-1-5-18','S-1-5-32-544')) { $acl.AddAccessRule((New-Object Security.AccessControl.FileSystemAccessRule((New-Object Security.Principal.SecurityIdentifier($identity)),'FullControl','Allow'))) }
Set-Acl -LiteralPath $machineConfig -AclObject $acl
$system = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$serviceSettings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
$installAction = New-ScheduledTaskAction -Execute $machinePython -Argument ('"'+(Join-Path $code 'machine_installer.py')+'"') -WorkingDirectory $code
Register-ScheduledTask -TaskName 'PC-Mesh-Install' -Action $installAction -Principal $system -Settings $settings -Description 'Fixed explicit PC-Mesh update installation; no automatic reboot' -Force | Out-Null
# Give the existing service owner only read/execute on this fixed task, never
# write permission to SYSTEM's task action, Python binary or installed code.
$scheduler = New-Object -ComObject Schedule.Service
$scheduler.Connect()
$task = $scheduler.GetFolder('\').GetTask('PC-Mesh-Install')
$descriptor = New-Object Security.AccessControl.CommonSecurityDescriptor($false,$false,'O:BAG:BAD:(A;;GA;;;SY)(A;;GA;;;BA)')
$descriptor.DiscretionaryAcl.AddAccess('Allow',$sid,(-2147483648 -bor 536870912),'None','None') # GENERIC_READ | GENERIC_EXECUTE
$task.SetSecurityDescriptor($descriptor.GetSddlForm('Owner, Group, Access'),0)
$state = Join-Path $base 'announce-state'
Protect-Directory $state
$announceAction = New-ScheduledTaskAction -Execute $machinePython -Argument ('"'+(Join-Path $code 'pc_mesh.py')+'" daemon --config "'+$machineConfig+'" --state "'+$state+'"') -WorkingDirectory $code
$startup = New-ScheduledTaskTrigger -AtStartup
Register-ScheduledTask -TaskName 'PC-Mesh-Announce-System' -Action $announceAction -Trigger $startup -Principal $system -Settings $serviceSettings -Description 'One persistent UpdateWulf worker; no periodic launcher' -Force | Out-Null
$ownerConfig = Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$ownerConfig | Add-Member -NotePropertyName native_installer -NotePropertyValue $true -Force
$ownerConfig | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $Config -Encoding UTF8
# Copy-created files must also belong to Administrators. A service user's
# implicit owner WRITE_DAC would otherwise undo a read-only inherited ACL.
foreach ($item in @(Get-Item -LiteralPath $base) + @(Get-ChildItem -LiteralPath $base -Recurse -Force)) {
    if ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Privileged runtime reparse point refused' }
    $sealed = Get-Acl -LiteralPath $item.FullName
    $sealed.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    Set-Acl -LiteralPath $item.FullName -AclObject $sealed
}
$ownerTask = Get-ScheduledTask -TaskName 'UpdateWulf-User' -ErrorAction SilentlyContinue
$legacyTask = Get-ScheduledTask -TaskName 'PC-Mesh' -ErrorAction SilentlyContinue
$legacyManaged = $false
if ($legacyTask) {
    $legacyText = @($legacyTask.Actions | ForEach-Object { [string]$_.Execute + ' ' + [string]$_.Arguments }) -join ';'
    $legacyManaged = $legacyText -match 'manage\.py'
}
$ownerState = Get-UpdateWulfOwnerState
if (($ownerTask -or $legacyManaged) -and -not $ownerState) {
    throw 'A user UpdateWulf scheduler exists but its state directory cannot be identified; refusing a possible duplicate SYSTEM worker.'
}

$rollbackTasks = @()
if ($ownerTask) { $rollbackTasks += 'UpdateWulf-User' }
if ($legacyManaged) { $rollbackTasks += 'PC-Mesh' }
Stop-UpdateWulfOwnerWorker $ownerState

$systemStart = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
try {
    Start-ScheduledTask -TaskName 'PC-Mesh-Announce-System'
    $heartbeat = Join-Path $state 'heartbeat.json'
    $deadline = (Get-Date).AddSeconds(45)
    $healthy = $false
    while ((Get-Date) -lt $deadline -and -not $healthy) {
        if (Test-Path -LiteralPath $heartbeat) {
            try {
                $hb = Get-Content -LiteralPath $heartbeat -Raw | ConvertFrom-Json
                $healthy = ([double]$hb.at -ge ($systemStart - 2)) -and
                           ([int]$hb.pid -gt 0) -and
                           [bool](Get-Process -Id ([int]$hb.pid) -ErrorAction SilentlyContinue)
            } catch { $healthy = $false }
        }
        if (-not $healthy) { Start-Sleep -Milliseconds 500 }
    }
    if (-not $healthy) { throw 'SYSTEM UpdateWulf worker did not publish a fresh heartbeat; user scheduler will be restored.' }
} catch {
    foreach ($name in $rollbackTasks) {
        Start-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    }
    throw
}

if ($ownerTask) { Unregister-ScheduledTask -TaskName 'UpdateWulf-User' -Confirm:$false }
if ($legacyManaged) { Unregister-ScheduledTask -TaskName 'PC-Mesh' -Confirm:$false }

$record = Join-Path $env:USERPROFILE '.config\pc-mesh\installation.json'
if (Test-Path -LiteralPath $record) {
    try {
        $installation = Get-Content -LiteralPath $record -Raw | ConvertFrom-Json
        $installation.scheduler = 'SYSTEM_MACHINE'
        $installation | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $record -Encoding UTF8
    } catch {}
}
Write-Output 'UpdateWulf SYSTEM worker verified; user/legacy scheduler retired. Fixed update task authorized. No package update was started.'
