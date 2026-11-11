
# Cache-only UpdateWulf two-line PowerShell prompt integration.
# The original prompt is delegated to rather than replaced with a default.
function global:UpdateWulf { & $global:PcMeshPython $global:PcMeshScript @args --state $global:PcMeshState }
function global:updatewulf { & $global:PcMeshPython $global:PcMeshScript @args --state $global:PcMeshState }
function global:pc-mesh { & $global:PcMeshPython $global:PcMeshScript @args --state $global:PcMeshState }
function global:pc-mesh-watch { & $global:PcMeshPython $global:PcMeshScript watch @args --state $global:PcMeshState }

function global:Get-PcMeshLines($fleet, [long]$since, [long]$now, [int]$width=80) {
    $width = [Math]::Max(28, $width)
    $nodes = @{}; $latest = @{}
    foreach ($node in @($fleet.nodes)) { $nodes[$node.id] = $node }
    foreach ($event in @($fleet.events | Sort-Object seq)) {
        if ($event.seq -gt $since -and ($now - $event.at) -lt 3600) {
            $key = if ($event.node) { $event.node } else { [string]$event.seq }
            $latest[$key] = $event
        }
    }
    $messages = @()
    foreach ($event in @($latest.Values | Sort-Object seq)) {
        $node = $nodes[$event.node]
        if ($node -and $event.signature -and $event.signature -ne $node.last_signature) { continue }
        if ($node -and -not $event.signature -and $event.message -ne ($node.name + ': ' + $node.updates.count + ' ausstehende Updates')) { continue }
        $messages += '[NEU] ' + ($event.message -replace '[\x00-\x1f\x7f]','')
    }
    $messages = @($messages | Select-Object -Last 3)
    $rows = @()
    foreach ($node in @($fleet.nodes | Sort-Object name)) {
        $u = $node.updates
        if (-not $node.received_at) { $value = 'ausstehend' }
        elseif (($now - $node.received_at) -gt $fleet.offline_after) { $value = if ($null -ne $u.count) { [string]$u.count + ' (offline)' } else { 'offline' } }
        elseif ($u.status -eq 'ERROR') { $value = 'Prueffehler' }
        elseif ($null -eq $u.count) { $value = '?' }
        elseif (($now - $u.checked_at) -gt $fleet.stale_after) { $value = [string]$u.count + ' (veraltet)' }
        else { $value = [string]$u.count; if ($u.status -eq 'CACHED') { $value += '~' } }
        $rows += $node.name + ': ' + $value
    }
    $messages += '[Updates] ' + ($rows -join ' | ')
    foreach ($message in $messages) {
        $line = ''
        foreach ($word in ($message -split ' ')) {
            if (($line.Length + $word.Length + 1) -gt $width -and $line.Trim()) {
                $line; $line = '  '
            }
            while ($word.Length -gt ($width - $line.Length)) {
                $take = $width - $line.Length
                $line + $word.Substring(0,$take)
                $word = $word.Substring($take); $line = '  '
            }
            $line += $(if ($line.Trim()) { ' ' } else { '' }) + $word
        }
        $line
    }
}

# Cache-only fleet status belongs to the PowerShell prompt, not to Write-Host.
# Keep the original owner's prompt and refresh the status only from fleet.json.
function global:Format-UpdateWulfHeader {
    param($Fleet, [long]$Now=0, [int]$Width=160, [bool]$Color=$false)
    if (-not $Now) { $Now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds() }
    $Width=[Math]::Max(22,$Width)
    $esc=[string][char]27
    $mint=if($Color){$esc+'[1;38;5;85m'}else{''}
    $blue=if($Color){$esc+'[38;5;39m'}else{''}
    $red=if($Color){$esc+'[38;5;196m'}else{''}
    $reset=if($Color){$esc+'[0m'}else{''}
    $pattern=[regex]::Escape($esc)+'\[[0-9;]*m'
    $prefix='[ '+$mint+'UpdateWulf'+$reset
    $sep='  '+$blue+'::'+$reset+'  '
    $close=' ]'
    $parts=@()
    $displayNames=@{ 'android'='S23'; 'android-s23'='S23'; 's23'='S23'; 'bmax'='BMAX'; 'bmax-b6'='BMAX'; 'legion'='Legion'; 'spinnennet'='Spinnennet'; 'spin'='Spinnennet'; 'pi'='pi-hole'; 'pihole'='pi-hole'; 'pi-hole'='pi-hole'; 'android-a71'='A71'; 'a71'='A71'; 'samsung-a71'='A71'; 'phobos'='PHOBOS'; 'hp'='HP-NetBSD'; 'hp-netbsd'='HP-NetBSD'; 'hp-tpnw121'='HP-NetBSD'; 'hp-twn121'='HP-NetBSD' }
    $displayOrder=@('S23','BMAX','HP-NetBSD','Legion','PHOBOS','pi-hole','Spinnennet','A71')
    $nodes=@($Fleet.nodes | Where-Object { $null -ne $_ } | Sort-Object {
        $key=([string]$_.id).ToLowerInvariant()
        $label=if($displayNames.ContainsKey($key)){$displayNames[$key]}else{([string]$_.hostname).Split('.')[0]}
        $rank=[array]::IndexOf($displayOrder,$label)
        if($rank -lt 0){99}else{$rank}
    },id)
    $lastSnapshot=0
    if($null -ne $Fleet.generated_at) { $lastSnapshot=[double]$Fleet.generated_at }
    $offlineAfter=if($Fleet.offline_after -gt 0){[double]$Fleet.offline_after}else{150}
    $staleAfter=if($Fleet.stale_after -gt 0){[double]$Fleet.stale_after}else{5400}
    $hubFresh=($lastSnapshot -gt 0 -and ($Now-$lastSnapshot) -ge -300 -and ($Now-$lastSnapshot) -le [Math]::Max(60,[Math]::Min(180,$offlineAfter)))
    foreach($node in $nodes) {
        # Display-only fallback for hosts without a report; never use friendly
        # labels as authenticated CLI routing or DNS identities.
        $hostname='unknown'
        foreach($candidateName in @($node.hostname,$node.enrolled_hostname,$node.name,$node.id)) {
            if($null -eq $candidateName){continue}
            $raw=([string]$candidateName).Trim().TrimEnd('.')
            if($raw -and $raw.Length -le 253 -and
                $raw -match '^[A-Za-z0-9_-]{1,63}(\.[A-Za-z0-9_-]{1,63})*$') {
                $hostname=$raw.Split('.')[0]
                break
            }
        }
        # Display aliases do not change authenticated IDs or CLI routing.
        foreach($aliasKey in @(([string]$node.id).ToLowerInvariant(),$hostname.ToLowerInvariant())) {
            if($displayNames.ContainsKey($aliasKey)){$hostname=$displayNames[$aliasKey];break}
        }
        $u=$node.updates
        # Compact prompt: positive and verified pending updates only.
        # Retain offline/cached positives, but omit offline zero and unknown.
        if($null -eq $u -or $u.status -notin @('OK','CACHED') -or
           $null -eq $u.count -or $u.count -isnot [ValueType] -or
           $u.count -is [bool] -or [double]$u.count -le 0){continue}
        $count=[string]$u.count
        $state=$null
        if(-not $node.received_at){$state='?'}
        elseif(-not $hubFresh){$state='stale'}
        elseif(($Now-[double]$node.received_at) -gt $offlineAfter){$state='off'}
        elseif($u.status -eq 'ERROR'){$state='err'}
        elseif($u.status -in @('UNKNOWN','UNSUPPORTED','CHECKING')){$state='?'}
        elseif(-not $u.checked_at -or ($Now-[double]$u.checked_at) -gt $staleAfter){$state='stale'}
        elseif($u.status -eq 'CACHED'){$state='cached'}
        $nameLabel=if($Color){$esc+'[1;38;5;255m'+$hostname+$reset}else{$hostname}
        $entry=$nameLabel+' - '+$count+' Update(s)'
        if($state -eq 'off'){$entry+=' ['+$red+'off'+$reset+']'}
        elseif($state){$entry+=' ['+$state+']'}
        $parts+= $entry
    }
    if($parts.Count -eq 0){$parts=@('keine ausstehenden Updates')}
    # Exactly one transient status row immediately above the owner PS1.
    # Do not hide truncated devices silently; summarize them as +N.
    $visible = { param([string]$text) ([regex]::Replace($text,$pattern,'')).Length }
    # A zero-update fleet is not an omitted host. Fit it to narrow SSH windows.
    if ($parts.Count -eq 1 -and $parts[0] -eq 'keine ausstehenden Updates') {
        foreach ($zero in @('keine ausstehenden Updates', '0 Updates', '0')) {
            $empty = $prefix + $sep + $zero + $close
            if ((& $visible $empty) -lt $Width) { return $empty }
        }
        return ($prefix + $close)
    }
    $selected = New-Object 'System.Collections.Generic.List[string]'
    $hidden = 0
    foreach ($part in $parts) {
        $candidate = $prefix + $sep + (($selected.ToArray() + @($part)) -join $sep) + $close
        if ((& $visible $candidate) -lt $Width) { $selected.Add($part) }
        else { $hidden++ }
    }
    if ($hidden -gt 0) {
        while ($true) {
            $shown = @($selected.ToArray()) + @('+' + $hidden)
            $candidate = $prefix + $sep + ($shown -join $sep) + $close
            if ((& $visible $candidate) -lt $Width -or $selected.Count -eq 0) { break }
            $selected.RemoveAt($selected.Count - 1)
            $hidden++
        }
        if ((& $visible $candidate) -ge $Width) { return ('[ UpdateWulf +' + $hidden + ' ]') }
        return $candidate
    }
    if ($selected.Count -eq 0) { return ($prefix + $close) }
    return ($prefix + $sep + ($selected.ToArray() -join $sep) + $close)
}

function global:Get-PcMeshPromptHeader {
    try {
        $fleetPath=Join-Path $global:PcMeshState 'fleet.json'
        if(Test-Path -LiteralPath $fleetPath){
            $fleet=[IO.File]::ReadAllText($fleetPath) | ConvertFrom-Json
        }else{$fleet=[pscustomobject]@{nodes=@()}}
        $width=try{$Host.UI.RawUI.WindowSize.Width}catch{160}
        $color=[bool]($Host.UI.SupportsVirtualTerminal -or $env:WT_SESSION -or $env:TERM_PROGRAM -eq 'vscode')
        # Preserve NO_COLOR even when the environment value is empty.
        if ($null -ne (Get-Item Env:NO_COLOR -ErrorAction SilentlyContinue)) { $color=$false }
        return Format-UpdateWulfHeader -Fleet $fleet -Now ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds()) -Width $width -Color $color
    } catch {
        return '[ UpdateWulf :: ? ]'
    }
}

# Optional hook for Shell-Color when it owns the prompt. Works across profile
# load orders and delegates only cached UpdateWulf status, never command output.
$global:ShellColorPrePromptProvider = { Get-PcMeshPromptHeader }

# Preserve the owner's prompt exactly once. If replacing a legacy PC-Mesh
# prompt wrapper, reuse its stored original instead of wrapping it twice.
$legacyWrapper = ($function:prompt -and $function:prompt.ToString().Contains('PcMeshOriginalPrompt'))
if (-not $global:UpdateWulfPromptInstalled -and
    (-not $legacyWrapper -or -not ($global:PcMeshOriginalPrompt -is [scriptblock]))) {
    $global:PcMeshOriginalPrompt = if ($function:prompt) {
        $function:prompt
    } else {
        { 'PS ' + $executionContext.SessionState.Path.CurrentLocation + '> ' }
    }
}
$global:UpdateWulfPromptInstalled = $true

function global:prompt {
    $savedExitCode = $global:LASTEXITCODE
    try {
        $ownerPrompt = (& $global:PcMeshOriginalPrompt) -join ''
        # Shell-Color's prefix-aware prompt may already include this line.
        # Do not duplicate it when both prompt integrations are active.
        if ($ownerPrompt -match '^(?:\x1b\[[0-9;]*m)*: :(?:\x1b\[[0-9;]*m)* (?:\x1b\[[0-9;]*m)*UpdateWulf|^\[ (?:\x1b\[[0-9;]*m)*UpdateWulf') {
            return $ownerPrompt
        }
        if ($global:UpdateWulfTransientPrompt) {
            # PSReadLine repaints the old two-line prompt immediately before
            # AcceptLine. Keep its height stable to avoid corrupting the input
            # buffer, but erase the UpdateWulf header from terminal history.
            $blankLines=[Math]::Max(1,[int]$global:UpdateWulfLastHeaderLines)
            return ((@(' ') * $blankLines) -join [Environment]::NewLine) + [Environment]::NewLine + $ownerPrompt
        }
        $header = Get-PcMeshPromptHeader
        $global:UpdateWulfLastHeaderLines=@($header -split '\r?\n').Count
        if($global:UpdateWulfTransientHandlerInstalled -and (Get-Command Set-PSReadLineOption -ErrorAction SilentlyContinue)){
            try { Set-PSReadLineOption -ExtraPromptLineCount $global:UpdateWulfLastHeaderLines } catch {}
        }
        return ($header + [Environment]::NewLine + $ownerPrompt)
    } finally {
        $global:LASTEXITCODE = $savedExitCode
    }
}

# A normal two-line PS1 scrolls into history. PSReadLine can replace its
# previous header with a blank line on Enter, then draw a fresh status above
# the next input. This is NOT a fixed terminal footer or background redraw.
# Never steal custom Enter handlers from Shell-Color, oh-my-posh, or the user.
function global:Enable-UpdateWulfTransientPrompt {
    if ($global:UpdateWulfTransientHandlerInstalled -or $env:UPDATEWULF_TRANSIENT_PROMPT -eq '0') { return }
    if ($Host.Name -ne 'ConsoleHost' -or $ExecutionContext.SessionState.LanguageMode -ne 'FullLanguage') { return }
    try {
        if ([Console]::IsInputRedirected -or [Console]::IsOutputRedirected) { return }
        if (-not (Get-Command Get-PSReadLineKeyHandler -ErrorAction SilentlyContinue)) { return }
        $option=Get-PSReadLineOption -ErrorAction Stop
        if ($option.EditMode -eq 'Vi') { return }
        # PSReadLine 2.0 on Windows PowerShell 5.1 has no -Key filter.
        # Enumerate bindings instead; -Chord is supported on both old and new.
        $handler=Get-PSReadLineKeyHandler -ErrorAction Stop |
            Where-Object { $_.Key -eq 'Enter' } | Select-Object -First 1
        if ($null -eq $handler -or $handler.Function -ne 'AcceptLine') { return }
        if ($option.ExtraPromptLineCount -lt 1) {
            Set-PSReadLineOption -ExtraPromptLineCount 1
        }
        Set-PSReadLineKeyHandler -Chord Enter -BriefDescription 'UpdateWulfTransientAcceptLine' -ScriptBlock {
            try {
                $ast=$null; $tokens=$null; $parseErrors=$null; $cursor=$null
                [Microsoft.PowerShell.PSConsoleReadLine]::GetBufferState(
                    [ref]$ast,[ref]$tokens,[ref]$parseErrors,[ref]$cursor)
                # Do not transient-repaint incomplete multi-line expressions.
                if ($null -ne $ast -and -not $parseErrors) {
                    try {
                        $global:UpdateWulfTransientPrompt=$true
                        [Microsoft.PowerShell.PSConsoleReadLine]::InvokePrompt()
                    } catch {
                        # Console/PSReadLine repaint support varies by version.
                    } finally {
                        $global:UpdateWulfTransientPrompt=$false
                    }
                }
            } catch {
                $global:UpdateWulfTransientPrompt=$false
            } finally {
                [Microsoft.PowerShell.PSConsoleReadLine]::AcceptLine()
            }
        }
        $global:UpdateWulfTransientHandlerInstalled=$true
    } catch {
        # Unsupported terminal: retain the original, working two-line PS1.
    }
}
Enable-UpdateWulfTransientPrompt
