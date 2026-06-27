param(
    [switch]$StaticOnly
)

$ErrorActionPreference = "Stop"

$ProjectDir = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectDir

Write-Host "[dev-check] validating docker compose config"
docker compose config *> $null

Write-Host "[dev-check] compiling worker python files"
python -m compileall services/worker/app

Write-Host "[dev-check] compiling api python files"
python -m compileall services/api/app

python -m ruff --version *> $null
if ($LASTEXITCODE -eq 0) {
    Write-Host "[dev-check] checking Python dead code/imports with ruff"
    python -m ruff check services scripts
} else {
    Write-Host "[dev-check][warn] ruff not installed; skipping Python dead-code/import checks"
}

Write-Host "[dev-check] validating source registry"
python scripts/validate_sources.py --strict

if (Get-Command npm -ErrorAction SilentlyContinue) {
    if (Select-String -Path dashboard/package.json -Pattern '"lint"' -Quiet) {
        Write-Host "[dev-check] running dashboard lint"
        npm --prefix dashboard run lint
    } else {
        Write-Host "[dev-check][warn] dashboard lint script not found; skipping"
    }
}

if ($StaticOnly -or $env:STATIC_ONLY -eq "true") {
    Write-Host "[dev-check] static checks passed; skipping runtime smoke test"
    exit 0
}

Write-Host "[dev-check] checking running containers"
$runningServices = docker compose ps --services --filter status=running
if (-not $runningServices -or -not ($runningServices -split "`n" | Where-Object { $_.Trim() -eq "api" })) {
    Write-Host "Run docker compose up -d --build first."
    exit 1
}

Write-Host "[dev-check] running smoke test"
if (Get-Command bash -ErrorAction SilentlyContinue) {
    bash scripts/smoke_test.sh
} else {
    Write-Host "[dev-check][warn] bash not found; run scripts/smoke_test.sh from a POSIX shell after containers are up"
}

Write-Host "[dev-check] all checks passed"
