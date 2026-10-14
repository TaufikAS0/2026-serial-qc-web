$ErrorActionPreference='Stop'
$repo=Split-Path $PSScriptRoot -Parent
$python=Join-Path $repo '.venv\Scripts\python.exe'
$launcher=Join-Path $repo 'launcher.py'
$status=(& $python $launcher status | ConvertFrom-Json)
if (-not $status.lan_url) { throw 'Aktifkan LAN lewat launcher enable-lan terlebih dahulu.' }
$dataPath=$status.data_directory
$resultPath=Join-Path $dataPath 'firewall-result.json'
if (Test-Path -LiteralPath $resultPath) { Remove-Item -LiteralPath $resultPath }
$helper=Join-Path $PSScriptRoot 'Set-LAN-Firewall.ps1'
$arguments=@('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$helper+'"'),'-DataDirectory',('"'+$dataPath+'"'))
Start-Process -FilePath powershell.exe -Verb RunAs -WindowStyle Hidden -ArgumentList $arguments | Out-Null
Write-Output 'Windows UAC diminta; hasil ditulis pada direktori data layanan.'
