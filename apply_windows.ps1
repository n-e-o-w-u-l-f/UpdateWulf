$ErrorActionPreference = 'Stop'
$session = $searcher = $downloader = $installer = $null
try {
    $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $admin) { throw 'Native elevated service required; no elevation attempted' }
    $session = New-Object -ComObject Microsoft.Update.Session
    $session.ClientApplicationID = 'PC-Mesh explicit LAN update request'
    $searcher = $session.CreateUpdateSearcher()
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
    if ([int]$result.ResultCode -ne 2) { throw "Search result $($result.ResultCode)" }
    $selected = New-Object -ComObject Microsoft.Update.UpdateColl
    $skipped = @()
    for ($i=0; $i -lt $result.Updates.Count; $i++) {
        $u = $result.Updates.Item($i)
        if ($u.InstallationBehavior.CanRequestUserInput -or $u.InstallationBehavior.Impact -eq 2) { $skipped += $u.Title; continue }
        if (-not $u.EulaAccepted) { $u.AcceptEula() }
        [void]$selected.Add($u)
    }
    if ($selected.Count -gt 0) {
        $downloader = $session.CreateUpdateDownloader()
        $downloader.Updates = $selected
        $download = $downloader.Download()
        if ([int]$download.ResultCode -ne 2) { throw "Download result $($download.ResultCode)" }
        $installer = $session.CreateUpdateInstaller()
        $installer.AllowSourcePrompts = $false
        $installer.Updates = $selected
        $installed = $installer.Install()
        [pscustomobject]@{status='COMPLETED'; result=[int]$installed.ResultCode; reboot_required=[bool]$installed.RebootRequired; skipped=$skipped} | ConvertTo-Json -Compress
        if ([int]$installed.ResultCode -ne 2) { throw "Install result $($installed.ResultCode); inspect Windows Update history" }
    } else { [pscustomobject]@{status='NO_APPLICABLE_AUTOMATIC_UPDATES'; skipped=$skipped} | ConvertTo-Json -Compress }
    if ($skipped.Count) { throw 'Some updates require interactive/exclusive installation; remaining count is refreshed separately' }
} catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }
finally {
    foreach ($obj in @($installer,$downloader,$searcher,$session)) { if ($null -ne $obj) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($obj) } }
}
