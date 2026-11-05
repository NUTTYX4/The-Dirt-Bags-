$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$bridgePort = 8010

Write-Host "Checking for a trusted physical LAN adapter..." -ForegroundColor Cyan

$candidates = @(
    foreach ($profile in Get-NetConnectionProfile) {
        if ($profile.NetworkCategory -ne 'Private') { continue }
        $adapter = Get-NetAdapter -InterfaceIndex $profile.InterfaceIndex -ErrorAction SilentlyContinue
        if (-not $adapter -or $adapter.Status -ne 'Up' -or -not $adapter.HardwareInterface) { continue }

        Get-NetIPAddress -InterfaceIndex $profile.InterfaceIndex -AddressFamily IPv4 -AddressState Preferred -ErrorAction SilentlyContinue |
            Where-Object { $_.IPAddress -notlike '127.*' -and $_.IPAddress -notlike '169.254.*' } |
            ForEach-Object {
                [PSCustomObject]@{ Interface = $adapter.Name; Address = $_.IPAddress; Network = $profile.Name }
            }
    }
)

$preferred = @($candidates | Where-Object { $_.Interface -match 'Wi-?Fi|Wireless' })
if ($preferred.Count -eq 1) { $network = $preferred[0] }
elseif ($candidates.Count -eq 1) { $network = $candidates[0] }
else {
    throw 'Connect the laptop and phone to the same trusted Wi-Fi, mark that Windows network Private, then run this helper again.'
}

$frontendEnv = Join-Path $PSScriptRoot '.env.local'
if (Test-Path $frontendEnv) {
    $configuredApi = Get-Content $frontendEnv | Where-Object { $_ -match '^VITE_API_BASE_URL=' } | Select-Object -First 1
    if ($configuredApi -and $configuredApi -ne 'VITE_API_BASE_URL=') {
        throw 'Set VITE_API_BASE_URL= (empty) in frontend/.env.local. The phone test uses Vite’s same-origin proxy and must not hardcode a laptop IP.'
    }
}

Write-Host "Using $($network.Interface): $($network.Address) ($($network.Network))" -ForegroundColor Green

Push-Location $backendRoot
try {
    docker compose up -d
    if ($LASTEXITCODE -ne 0) { throw 'Docker Compose failed to start the backend.' }
}
finally { Pop-Location }

if (-not (Test-NetConnection -ComputerName 127.0.0.1 -Port $bridgePort -InformationLevel Quiet)) {
    $python = Join-Path $projectRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) { throw 'The project Python environment is missing; cannot start the Gemini routing bridge.' }
    Start-Process -FilePath $python -ArgumentList 'gemini_bridge.py' -WorkingDirectory $backendRoot -WindowStyle Hidden
}

$ready = $false
for ($attempt = 1; $attempt -le 20; $attempt++) {
    try {
        $ready = (Invoke-RestMethod 'http://127.0.0.1:8000/health/ready' -TimeoutSec 3).ready
        if ($ready) { break }
    }
    catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) { throw 'The API did not become ready. Run: docker compose -f backend/compose.yaml logs api' }

Write-Host "Backend ready. Gemini image routing bridge: $(Test-NetConnection -ComputerName 127.0.0.1 -Port $bridgePort -InformationLevel Quiet)" -ForegroundColor Green
Write-Host "Open this on the phone: http://$($network.Address):5173" -ForegroundColor Green
Write-Host 'Starting Vite with LAN access. Press Ctrl+C here when phone testing is complete.' -ForegroundColor Cyan

Push-Location $PSScriptRoot
try { npm.cmd run dev -- --host 0.0.0.0 --port 5173 }
finally { Pop-Location }
