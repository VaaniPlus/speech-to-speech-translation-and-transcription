$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $repoRoot "backend"

$uv = Get-Command uv -ErrorAction SilentlyContinue
if (-not $uv) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/getting-started/installation/."
}

Write-Host "Syncing the backend uv project..."
Push-Location $backendDir
try {
    & uv sync
    if ($LASTEXITCODE -ne 0) {
        throw "uv sync failed for the backend project."
    }
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "Backend environment ready in backend\.venv."
Write-Host "Run tests with:"
Write-Host "  uv run --project backend pytest"
