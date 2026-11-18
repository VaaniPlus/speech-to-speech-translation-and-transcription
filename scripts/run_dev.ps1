$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"
$frontendDir = Join-Path $repoRoot "frontend"

$uv = Get-Command uv -ErrorAction SilentlyContinue
$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $uv) {
    throw "uv is required."
}
if (-not $npm) {
    throw "npm is required."
}

Push-Location $backendDir
try {
    & uv sync
    if ($LASTEXITCODE -ne 0) { throw "Backend dependency sync failed." }
} finally {
    Pop-Location
}

Push-Location $frontendDir
try {
    if (-not (Test-Path "node_modules")) {
        & npm ci
        if ($LASTEXITCODE -ne 0) { throw "Frontend dependency install failed." }
    }
} finally {
    Pop-Location
}

Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$backendDir'; uv run uvicorn app.main:app --host 127.0.0.1 --port 8000"
)
Start-Process powershell -ArgumentList @(
    "-NoExit",
    "-Command",
    "Set-Location '$frontendDir'; npm run dev"
)

Write-Host "Backend: http://127.0.0.1:8000"
Write-Host "Frontend: http://127.0.0.1:5173"
