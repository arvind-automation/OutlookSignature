$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

Write-Host "Starting Arvind Signature Generator (Docker Compose)..."
Write-Host "App will be available at http://localhost:5000"
Write-Host "Press Ctrl+C to stop."

if (-not (Test-Path ".env")) {
  Copy-Item ".env.example" ".env"
  Write-Host "Created .env from .env.example"
}

docker compose up --build
