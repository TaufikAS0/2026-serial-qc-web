param(
  [Parameter(Mandatory=$true)][string]$DataDirectory,
  [ValidateSet('Install','Uninstall')][string]$Action='Install',
  [int]$Port=8770
)
$ErrorActionPreference='Stop'
$resultPath=Join-Path $DataDirectory 'firewall-result.json'
try {
  $identity=[Security.Principal.WindowsIdentity]::GetCurrent()
  $principal=New-Object Security.Principal.WindowsPrincipal($identity)
  if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Administrator diperlukan untuk Windows Firewall.' }
  if ($Port -lt 1024 -or $Port -gt 65535) { throw 'Port tidak valid.' }
  $ruleName="SerialProtocolTestWeb-LAN-$Port"
  if ($Action -eq 'Install') {
    $config=Get-Content -LiteralPath (Join-Path $DataDirectory 'network.json') -Raw | ConvertFrom-Json
    if ($config.host -notmatch '^(10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[01])\.)') { throw 'LAN host harus IPv4 privat.' }
    $existing=Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue
    if ($existing) { Remove-NetFirewallRule -Name $ruleName }
    New-NetFirewallRule -Name $ruleName -DisplayName "Serial Protocol Test Web LAN ($Port)" -Direction Inbound -Action Allow -Protocol TCP -LocalPort $Port -LocalAddress $config.host -RemoteAddress $config.subnet -Profile Any | Out-Null
    $rule=Get-NetFirewallRule -Name $ruleName
    @{ok=$true;action=$Action;rule=$ruleName;enabled=($rule.Enabled -eq 'True')} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
  } else {
    Get-NetFirewallRule -Name $ruleName -ErrorAction SilentlyContinue | Remove-NetFirewallRule
    @{ok=$true;action=$Action} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
  }
} catch {
  @{ok=$false;error=$_.Exception.Message} | ConvertTo-Json | Set-Content -LiteralPath $resultPath -Encoding UTF8
  exit 1
}
