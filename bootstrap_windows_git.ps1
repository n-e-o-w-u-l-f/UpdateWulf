param([string]$Destination=(Join-Path $env:USERPROFILE '.local\lib\pc-mesh\git'))
$ErrorActionPreference='Stop'
# Official Git for Windows release, published 2026-10-05. No machine installer.
$version='2.56.0.windows.2'
$uri='https://github.com/git-for-windows/git/releases/download/v2.56.0.windows.2/MinGit-2.56.0.2-64-bit.zip'
$expected='da35e72aa21c005a5a0d298cfbae110bc1609a815730ea0dde84b01a1b3cd3be'
if (Test-Path -LiteralPath $Destination) {
    $actual=& (Join-Path $Destination 'cmd\git.exe') --version
    if ($LASTEXITCODE -eq 0 -and $actual -eq ('git version '+$version)) { Write-Output $actual; return }
    throw 'Existing portable Git directory preserved; inspect it before changing the installation'
}
$archive=Join-Path $env:TEMP 'pc-mesh-mingit-2.56.0.2-20261006.zip'
if (-not (Test-Path -LiteralPath $archive)) { Invoke-WebRequest -UseBasicParsing -Uri $uri -OutFile $archive }
$actual=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($actual -ne $expected) { throw 'Official MinGit archive SHA256 mismatch; nothing was installed' }
$temporary=$Destination+'.installing-20261006'
if (Test-Path -LiteralPath $temporary) { throw 'Earlier temporary installation preserved; inspect it before retrying' }
Expand-Archive -LiteralPath $archive -DestinationPath $temporary
if (-not (Test-Path -LiteralPath (Join-Path $temporary 'usr\bin\ssh.exe'))) { throw 'Verified archive did not contain the required SSH client' }
Move-Item -LiteralPath $temporary -Destination $Destination
& (Join-Path $Destination 'cmd\git.exe') --version
if ($LASTEXITCODE -ne 0) { throw 'Native portable Git validation failed' }
& (Join-Path $Destination 'usr\bin\ssh.exe') -V
if ($LASTEXITCODE -ne 0) { throw 'Native portable SSH validation failed' }
Write-Output ('MINGIT_SHA256_VERIFIED '+$expected)
