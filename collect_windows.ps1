param([switch]$Fingerprint)
$ErrorActionPreference = 'Stop'
$session = $searcher = $null
try {
    $session = New-Object -ComObject Microsoft.Update.Session
    $session.ClientApplicationID = 'PC-Mesh update notification service'
    $searcher = $session.CreateUpdateSearcher()
    $reboot = [bool](Test-Path 'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired')
    if ($Fingerprint) {
        $historyCount = $searcher.GetTotalHistoryCount()
        $last = if ($historyCount -gt 0) { $searcher.QueryHistory(0,1).Item(0).Date.ToUniversalTime().Ticks } else { 0 }
        [pscustomobject]@{history=$historyCount; last=$last; reboot=$reboot} | ConvertTo-Json -Compress
        return
    }
    $result = $searcher.Search("IsInstalled=0 and IsHidden=0 and Type='Software'")
    if ([int]$result.ResultCode -ne 2) { throw "Windows Update result code $($result.ResultCode)" }
    $packages = @()
    $titles = @()
    for ($i = 0; $i -lt $result.Updates.Count; $i++) {
        $update = $result.Updates.Item($i)
        $packages += ($update.Identity.UpdateID + ':' + $update.Identity.RevisionNumber)
        $titles += $update.Title
    }
    [pscustomobject]@{status='OK'; count=$result.Updates.Count; packages=$packages; titles=$titles; reboot_required=$reboot; source='Windows Update'; metadata_fresh=$true} | ConvertTo-Json -Compress -Depth 5
} catch {
    [pscustomobject]@{status='ERROR'; count=$null; error=$_.Exception.Message; source='Windows Update'} | ConvertTo-Json -Compress
    exit 1
}
finally { foreach ($obj in @($searcher,$session)) { if ($null -ne $obj) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($obj) } } }
