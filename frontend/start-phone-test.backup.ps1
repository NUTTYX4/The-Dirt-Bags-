<# Temporary trusted-LAN launcher. Requires the physical network to be Private. #>
$physical = Get-NetIPAddress -AddressFamily IPv4 | Where-Object {
  $_.IPAddress -notlike '127.*' -and $_.InterfaceAlias -notmatch 'WSL|vEthernet|Loopback' -and $_.AddressState -eq 'Preferred'
} | Select-Object -First 1
if (-not $physical) { throw 'No physical IPv4 address found.' }
$profile = Get-NetConnectionProfile -InterfaceIndex $physical.InterfaceIndex
if ($profile.NetworkCategory -ne 'Private') {
  throw "Refusing LAN launch: '$($profile.InterfaceAlias)' is $($profile.NetworkCategory). Mark the trusted network Private first."
}
$ip = $physical.IPAddress
"VITE_API_BASE_URL=http://$ip`:8000" | Set-Content -NoNewline .env.local
$backendEnv = Join-Path $PSScriptRoot '..\backend\.env'
$cors = "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173,http://$ip`:5173"
$lines = @(Get-Content $backendEnv -ErrorAction Stop | Where-Object { $_ -notmatch '^CORS_ORIGINS=' }) + $cors
Set-Content -Path $backendEnv -Value $lines
Push-Location (Join-Path $PSScriptRoot '..\backend')
docker compose up -d --force-recreate api
Pop-Location
try { Invoke-RestMethod 'http://127.0.0.1:8000/health/ready' -TimeoutSec 20 | Out-Null } catch { throw 'Docker API did not become ready.' }
Write-Host "Phone URL: http://$ip`:5173" -ForegroundColor Green
Write-Host "API URL:   http://$ip`:8000/health/ready" -ForegroundColor Green
npm.cmd run dev -- --host 0.0.0.0 --port 5173
