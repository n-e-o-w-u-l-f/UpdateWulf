param([string]$Source=$PSScriptRoot,[string]$State)
$ErrorActionPreference='Stop'
foreach ($file in (Get-ChildItem -LiteralPath $Source -Filter '*.ps1')) {
    $tokens=$null; $errors=$null
    [void][Management.Automation.Language.Parser]::ParseFile($file.FullName,[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw ($file.Name+': '+($errors.Message -join '; ')) }
}
$machineEnable = Get-Content -LiteralPath (Join-Path $Source 'enable_machine_updates_windows.ps1') -Raw
foreach ($required in @('Stop-UpdateWulfOwnerWorker','UpdateWulf-User','Unregister-ScheduledTask','heartbeat.json','SYSTEM UpdateWulf worker')) {
    if ($machineEnable -notmatch [regex]::Escape($required)) { throw "Windows SYSTEM handover missing: $required" }
}
if ($machineEnable -match '(?i)taskkill|Stop-Process') { throw 'Windows SYSTEM handover must remain cooperative; force-kill helper detected' }
if ($machineEnable.IndexOf("SYSTEM UpdateWulf worker did not publish a fresh heartbeat") -gt $machineEnable.IndexOf("Unregister-ScheduledTask -TaskName 'UpdateWulf-User'")) {
    throw 'User task is retired before the SYSTEM heartbeat acceptance gate'
}
$promptSource = Get-Content -LiteralPath (Join-Path $Source 'prompt_windows.ps1') -Raw
if ($promptSource -match 'Get-PSReadLineKeyHandler -Key' -or $promptSource -match 'Set-PSReadLineKeyHandler -Key') {
    throw 'PSReadLine 2.0 has no -Key parameter; use enumeration and -Chord'
}
if ($promptSource -notmatch 'Set-PSReadLineKeyHandler -Chord Enter') {
    throw 'Transient prompt must use PSReadLine 2.0-compatible Enter binding'
}
$userInstall = Get-Content -LiteralPath (Join-Path $Source 'install_windows.ps1') -Raw
foreach ($required in @('Export-ScheduledTask','Get-LiveUpdateWulfPid','New UpdateWulf user worker did not publish a fresh heartbeat','Register-ScheduledTask -TaskName ''UpdateWulf-User'' -Xml $oldUserXml')) {
    if ($userInstall -notmatch [regex]::Escape($required)) { throw "Windows user handover missing: $required" }
}
if ($userInstall -match '(?i)taskkill|Stop-Process') { throw 'Windows user handover must remain cooperative; force-kill helper detected' }
if ($userInstall.IndexOf("Register-ScheduledTask -TaskName 'UpdateWulf-User' -Action") -gt $userInstall.IndexOf("New-Item -ItemType File -Path $stopRequest")) {
    throw 'Windows user task is not prepared before the old worker is stopped'
}
$descriptor=New-Object Security.AccessControl.CommonSecurityDescriptor($false,$false,'O:BAG:BAD:(A;;GA;;;SY)(A;;GA;;;BA)')
$sid=[Security.Principal.WindowsIdentity]::GetCurrent().User
$descriptor.DiscretionaryAcl.AddAccess('Allow',$sid,(-2147483648 -bor 536870912),'None','None')
$ace=@($descriptor.DiscretionaryAcl | Where-Object {$_.SecurityIdentifier -eq $sid})[0]
if (($ace.AccessMask -band 268435456) -ne 0) { throw 'Task test unexpectedly grants GENERIC_ALL' }
if (($ace.AccessMask -band 536870912) -eq 0) { throw 'Task test lacks GENERIC_EXECUTE' }
if ($descriptor.Owner.Value -ne 'S-1-5-32-544') { throw 'Task owner must not retain implicit service-user WRITE_DAC' }
[void]$descriptor.GetSddlForm('Owner, Group, Access')
function global:prompt { 'OWNER-PROMPT> ' }
$global:PcMeshState=$State
$global:LASTEXITCODE=73
. (Join-Path $Source 'prompt_windows.ps1')
$text=prompt
$rows=@($text -split '\r?\n')
if ($rows[-1] -ne 'OWNER-PROMPT> ' -or $rows[0] -notmatch 'UpdateWulf' -or $global:LASTEXITCODE -ne 73) {
    throw 'UpdateWulf two-line prompt failed to preserve the owner prompt or exit code'
}
if (($text -split 'OWNER-PROMPT> ').Count -ne 2) { throw 'Owner prompt unexpectedly duplicated' }
. (Join-Path $Source 'prompt_windows.ps1')
$reloaded=prompt
if (($reloaded -split '\r?\n')[-1] -ne 'OWNER-PROMPT> ' -or
    (@($reloaded -split 'OWNER-PROMPT> ').Count -ne 2)) {
    throw 'Reload recursed, duplicated, or replaced the owner prompt'
}
if ($global:LASTEXITCODE -ne 73) { throw 'Reload changed LASTEXITCODE' }
if (-not (Get-Command pc-mesh -ErrorAction SilentlyContinue)) { throw 'pc-mesh command is missing' }
# Single-line ANSI scopes: mint/bold title, blue separators, red text only for off.
$stamp=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$colors=[pscustomobject]@{generated_at=$stamp;offline_after=150;stale_after=5400;nodes=@(
    [pscustomobject]@{id='bmax';hostname='BMAX-B6';name='BMAX';received_at=($stamp-200);
        updates=[pscustomobject]@{status='OK';count=1;checked_at=$stamp}},
    [pscustomobject]@{id='pi';hostname='pi-hole';name='Pi-hole';received_at=$stamp;
        updates=[pscustomobject]@{status='OK';count=0;checked_at=$stamp}}
)}
$esc=[string][char]27
$ansi=Format-UpdateWulfHeader -Fleet $colors -Now $stamp -Width 220 -Color $true
if (-not $ansi.Contains($esc+'[1;38;5;85mUpdateWulf'+$esc+'[0m')) { throw 'Mint/bold UpdateWulf title missing' }
if (-not $ansi.Contains($esc+'[38;5;39m::'+$esc+'[0m')) { throw 'Blue delimiter missing' }
if (-not $ansi.Contains('['+$esc+'[38;5;196moff'+$esc+'[0m]')) { throw 'Positive offline status must be red' }
if ($ansi.Contains($esc+'[38;5;196m[')) { throw 'Status bracket color leaked' }
if (-not $ansi.Contains($esc+'[1;38;5;255mBMAX'+$esc+'[0m - 1 Update(s)')) { throw 'Machine name style missing' }
if ($ansi -match '\?\.local|\.local|\.lan') { throw 'DNS suffix in prompt' }
if ($ansi.Contains('pi-hole') -or $ansi.Contains('+1')) { throw 'Zero update not hidden' }
$withoutReport=[pscustomobject]@{generated_at=$stamp;offline_after=150;stale_after=5400;nodes=@(
    [pscustomobject]@{id='bmax';name='BMAX-B6';received_at=0;updates=[pscustomobject]@{status='UNKNOWN';count=$null}},
    [pscustomobject]@{id='pi';enrolled_hostname='pi-hole.lan';name='Pi-hole';received_at=0;updates=[pscustomobject]@{status='UNKNOWN';count=$null}},
    [pscustomobject]@{id='hp-netbsd';name='Invalid machine name!';received_at=0;updates=[pscustomobject]@{status='OK';count=2;checked_at=$stamp}}
)}
$offlineHeader=Format-UpdateWulfHeader -Fleet $withoutReport -Now $stamp -Width 240 -Color $false
if(-not $offlineHeader.Contains('HP-NetBSD - 2 Update(s)') -or $offlineHeader.Contains('BMAX') -or $offlineHeader.Contains('pi-hole')) { throw 'Nonpositive or unknown nodes not filtered' }
if ($offlineHeader -match '\?\.local|\.local|\.lan') { throw 'Offline DNS suffix' }
$aliases=[pscustomobject]@{generated_at=$stamp;nodes=@(
    @('android','bmax','legion','spinnennet','pihole','a71','phobos','hp') | ForEach-Object {
        [pscustomobject]@{id=$_;received_at=$stamp;updates=[pscustomobject]@{status='OK';count=1;checked_at=$stamp}}
    }
)}
$aliasHeader=Format-UpdateWulfHeader -Fleet $aliases -Now $stamp -Width 1000 -Color $false
$expectedNames=@('S23','BMAX','HP-NetBSD','Legion','PHOBOS','pi-hole','Spinnennet','A71')
$expectedHeader='[ UpdateWulf  ::  '+(($expectedNames | ForEach-Object {$_+' - 1 Update(s)'}) -join '  ::  ')+' ]'
if($aliasHeader -ne $expectedHeader){throw ('Display aliases, order or framing incorrect: '+$aliasHeader)}
$zeroFleet=[pscustomobject]@{generated_at=$stamp;nodes=@(
    [pscustomobject]@{id='bmax';received_at=$stamp;updates=[pscustomobject]@{status='OK';count=0;checked_at=$stamp}},
    [pscustomobject]@{id='legion';received_at=$stamp;updates=[pscustomobject]@{status='OK';count=1;checked_at=$stamp}}
)}
$zeroHeader=Format-UpdateWulfHeader -Fleet $zeroFleet -Now $stamp -Width 500 -Color $false
if($zeroHeader.Contains('BMAX') -or $zeroHeader.Contains('+1') -or -not $zeroHeader.Contains('Legion - 1')){throw 'Zero filtering failed'}
$shortHeader=Format-UpdateWulfHeader -Fleet $aliases -Now $stamp -Width 40 -Color $false
if($shortHeader -match '[\r\n]' -or $shortHeader.Contains('...') -or $shortHeader -notmatch '\+\d+') {
    throw 'A narrow console must retain one status row and a +N overflow indicator'
}
$emptyFleet=[pscustomobject]@{generated_at=$stamp;offline_after=150;stale_after=5400;nodes=@()}
foreach($cols in @(22,28,40,80,160)) {
    $zero=Format-UpdateWulfHeader -Fleet $emptyFleet -Now $stamp -Width $cols -Color $false
    if($zero -match '[\r\n]' -or $zero.Length -ge $cols -or $zero -match '\+\d+' -or $zero -notmatch '(0|keine ausstehenden Updates)') {
        throw ('Empty fleet must show zero, not hidden hosts, at width '+$cols)
    }
}
$global:UpdateWulfTransientPrompt=$true
$transient=prompt
$global:UpdateWulfTransientPrompt=$false
if ($transient -match 'UpdateWulf' -or (@($transient -split '\r?\n')).Count -ne ([Math]::Max(1,[int]$global:UpdateWulfLastHeaderLines)+1) -or
    (@($transient -split '\r?\n'))[-1] -ne 'OWNER-PROMPT> ' -or $global:LASTEXITCODE -ne 73) {
    throw 'Transient prompt must clear only the status line and preserve the input prompt'
}
if ($ansi -like '*[[]NEU[]]*') { throw 'Separate notification printed in prompt' }
foreach ($cols in @(22,28,40,80)) {
    $line=Format-UpdateWulfHeader -Fleet $colors -Now $stamp -Width $cols -Color $true
    $clean=[regex]::Replace($line,([regex]::Escape($esc)+'\[[0-9;]*m'),'')
    if (@($clean -split '\r?\n' | Where-Object { $_.Length -ge $cols }).Count) { throw "Header overflowed width $cols" }
}
$now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$fixture=[pscustomobject]@{nodes=@([pscustomobject]@{id='hp';name='HP';received_at=$now;last_signature='zero';updates=[pscustomobject]@{status='OK';count=0;checked_at=$now}});sequence=3;offline_after=150;stale_after=5400;events=@(
    [pscustomobject]@{node='hp';seq=1;at=$now;signature='old';message='HP: 99 ausstehende Updates'},
    [pscustomobject]@{node='hp';seq=2;at=$now;signature='zero';message='HP: 0 ausstehende Updates'},
    [pscustomobject]@{node='hp';seq=3;at=$now;signature='zero';message='HP: 0 ausstehende Updates'})}
$lines=@(Get-PcMeshLines $fixture 0 $now 28)
if (($lines -join ' ') -match '99' -or @($lines | Where-Object {$_ -like '[[]NEU[]]*'}).Count -ne 1) { throw 'Old Windows notifications were repeated' }
if (@($lines | Where-Object {$_.Length -gt 28}).Count) { throw 'Phone-width Windows prompt exceeded its terminal width' }
& (Join-Path $Source 'collect_windows.ps1') -Fingerprint
if ($LASTEXITCODE -eq 1) { throw 'Native Windows history fingerprint failed' }
Write-Output 'WINDOWS_PARSE_TASK_MASK_PROMPT_EXIT_RELOAD_HOSTNAME_TRANSIENT_VERIFIED'
