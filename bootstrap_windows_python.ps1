param([string]$Source=$PSScriptRoot)
$ErrorActionPreference='Stop'
$version='3.14.7'
$expected='d297e5ff019966817ad8502465176139f2d3d840fa4ed84b13bed399a6ab1f15'
$directory=Join-Path $env:USERPROFILE '.local\lib\pc-mesh\python'
[IO.Directory]::CreateDirectory($directory) | Out-Null
$archive=Join-Path $directory ('python-'+$version+'-embed-amd64.zip')
if (-not (Test-Path -LiteralPath $archive)) { Invoke-WebRequest -UseBasicParsing -Uri ('https://www.python.org/ftp/python/'+$version+'/python-'+$version+'-embed-amd64.zip') -OutFile $archive }
$hash=(Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
if ($hash -ne $expected) { throw 'Official Python archive SHA256 mismatch; no interpreter was executed' }
$python=Join-Path $directory 'python.exe'
if (-not (Test-Path -LiteralPath $python)) { Expand-Archive -LiteralPath $archive -DestinationPath $directory -Force }
$signature=Get-AuthenticodeSignature -LiteralPath $python
if ($signature.Status -ne 'Valid') { throw ('Python executable Authenticode status: '+$signature.Status) }
$pth=Join-Path $directory 'python314._pth'
[IO.File]::WriteAllLines($pth,@('python314.zip','.',[IO.Path]::GetFullPath($Source)),(New-Object Text.UTF8Encoding($false)))
& $python -c 'import sys,ssl; assert sys.version_info >= (3,9); print(sys.version)'
if ($LASTEXITCODE -ne 0) { throw 'Embedded interpreter verification failed' }
[pscustomobject]@{python=$python; source=$Source; archive_sha256=$hash; signature=[string]$signature.Status} | ConvertTo-Json -Compress
