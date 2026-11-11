# Enable only the fixed installer for an existing authenticated user worker.
param([Parameter(Mandatory=$true)][string]$Config,
      [Parameter(Mandatory=$true)][string]$State)
$ErrorActionPreference='Stop'
$principal=[Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
if(-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)){throw 'Administrator owner session required'}
$base=Join-Path $env:ProgramData 'PC-Mesh-Installer'
$code=Join-Path $base 'code'
$python=Join-Path $base 'python\python.exe'
if(-not (Test-Path $python) -or -not (Test-Path (Join-Path $code 'machine_installer.py'))){throw 'Prepared protected runtime required'}
foreach($item in @(Get-Item $base)+@(Get-ChildItem $base -Recurse -Force)){
    if($item.Attributes -band [IO.FileAttributes]::ReparsePoint){throw 'Reparse point refused'}
    $acl=Get-Acl -LiteralPath $item.FullName
    $acl.SetOwner((New-Object Security.Principal.SecurityIdentifier('S-1-5-32-544')))
    Set-Acl -LiteralPath $item.FullName -AclObject $acl
}
$userTask=Get-ScheduledTask -TaskName 'UpdateWulf-User'
$userId=$userTask.Principal.UserId
$sid=if($userId -match '^S-1-') {New-Object Security.Principal.SecurityIdentifier($userId)} else {(New-Object Security.Principal.NTAccount($userId)).Translate([Security.Principal.SecurityIdentifier])}
$system=New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero)
$action=New-ScheduledTaskAction -Execute $python -Argument ('"'+(Join-Path $code 'machine_installer.py')+'"') -WorkingDirectory $code
Register-ScheduledTask -TaskName 'PC-Mesh-Install' -Action $action -Principal $system -Settings $settings -Force | Out-Null
$scheduler=New-Object -ComObject Schedule.Service
$scheduler.Connect()
$descriptor=New-Object Security.AccessControl.CommonSecurityDescriptor($false,$false,'O:BAG:BAD:(A;;GA;;;SY)(A;;GA;;;BA)')
$descriptor.DiscretionaryAcl.AddAccess('Allow',$sid,(-2147483648 -bor 536870912),'None','None')
$scheduler.GetFolder('\').GetTask('PC-Mesh-Install').SetSecurityDescriptor($descriptor.GetSddlForm('Owner, Group, Access'),0)
Copy-Item -LiteralPath $Config -Destination ($Config+'.before-fixed-installer-'+(Get-Date -Format yyyyMMdd-HHmmss))
$client=Get-Content -LiteralPath $Config -Raw | ConvertFrom-Json
$client | Add-Member -NotePropertyName native_installer -NotePropertyValue $true -Force
[IO.File]::WriteAllText($Config,($client | ConvertTo-Json -Depth 30),[Text.UTF8Encoding]::new($false))
$heartbeat=Join-Path $State 'heartbeat.json'
$oldPid=[int]((Get-Content $heartbeat -Raw | ConvertFrom-Json).pid)
New-Item -ItemType File -Path (Join-Path $State 'stop.request') -Force | Out-Null
$deadline=(Get-Date).AddSeconds(45)
while((Get-Process -Id $oldPid -ErrorAction SilentlyContinue) -and (Get-Date) -lt $deadline){Start-Sleep -Milliseconds 500}
if(Get-Process -Id $oldPid -ErrorAction SilentlyContinue){throw 'Existing worker did not stop cooperatively'}
$start=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
Start-ScheduledTask -TaskName 'UpdateWulf-User'
$deadline=(Get-Date).AddSeconds(45)
do {
    Start-Sleep -Milliseconds 500
    $hb=Get-Content $heartbeat -Raw | ConvertFrom-Json
    $healthy=([double]$hb.at -ge $start-2) -and [bool](Get-Process -Id ([int]$hb.pid) -ErrorAction SilentlyContinue)
} while(-not $healthy -and (Get-Date) -lt $deadline)
if(-not $healthy){throw 'User worker restart not verified'}
Write-Output 'FIXED_INSTALLER_AND_USER_WORKER_VERIFIED'
