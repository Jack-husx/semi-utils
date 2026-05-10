# Semi-Utils local Windows packaging script
# Usage: right-click in project root -> Run with PowerShell, or run .\build_local.ps1
$ErrorActionPreference = "Stop"

$projectRoot     = $PSScriptRoot
$distPath        = Join-Path $projectRoot "dist"
$venvPip         = Join-Path $projectRoot ".venv\Scripts\pip.exe"
$venvPyinstaller = Join-Path $projectRoot ".venv\Scripts\pyinstaller.exe"

Write-Host ""
Write-Host "======================================" -ForegroundColor Cyan
Write-Host "  Semi-Utils Windows Build Script" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# ---- Step 1: ensure PyInstaller is present in venv ----
Write-Host "[1/5] Ensuring PyInstaller in venv..." -ForegroundColor Yellow
if (-not (Test-Path $venvPip)) { Write-Error "No .venv found. Please run: python -m venv .venv && pip install -r requirements.txt"; exit 1 }
& $venvPip install pyinstaller --quiet
Write-Host "      OK" -ForegroundColor Green

# ---- Step 2: clean old build artifacts ----
Write-Host "[2/5] Cleaning old build artifacts..." -ForegroundColor Yellow
if (Test-Path $distPath)                        { Remove-Item -Path $distPath  -Recurse -Force }
if (Test-Path (Join-Path $projectRoot "build")) { Remove-Item -Path (Join-Path $projectRoot "build") -Recurse -Force }
Write-Host "      OK" -ForegroundColor Green

# ---- Step 3: PyInstaller build ----
Write-Host "[3/5] Building with PyInstaller (may take 1-2 min)..." -ForegroundColor Yellow
Set-Location $projectRoot
& $venvPyinstaller ./build_win_pkg.spec
if ($LASTEXITCODE -ne 0) { Write-Error "Build failed. Check errors above."; exit 1 }
Write-Host "      OK" -ForegroundColor Green

# ---- Step 4: assemble release directory ----
Write-Host "[4/5] Assembling release directory..." -ForegroundColor Yellow

# config (fonts, logos, watermark templates)
Copy-Item -Path (Join-Path $projectRoot "config") -Destination $distPath -Recurse -Force

# project version info
Copy-Item -Path (Join-Path $projectRoot "pyproject.toml") -Destination $distPath -Force

# NOTE: input/ and output/ are NOT included in the package.
# start.bat creates them automatically on first launch.

# ExifTool
$exiftoolSrc = Join-Path $projectRoot "exiftool"
if (Test-Path $exiftoolSrc) {
    Copy-Item -Path $exiftoolSrc -Destination $distPath -Recurse -Force
    Write-Host "      ExifTool copied." -ForegroundColor Green
} else {
    New-Item -Path (Join-Path $distPath "exiftool") -ItemType Directory -Force | Out-Null
    Write-Host "      WARNING: ./exiftool not found. Copy exiftool.exe into dist/exiftool/ manually." -ForegroundColor Red
}

Write-Host "      OK" -ForegroundColor Green

# ---- Step 5: generate launcher batch file (pure ASCII) ----
Write-Host "[5/5] Generating launcher batch file..." -ForegroundColor Yellow
$batContent = "@echo off`r`ncd /d `"%~dp0`"`r`nif not exist `"input`" mkdir input`r`nif not exist `"output`" mkdir output`r`nsemi-utils.exe`r`npause`r`n"
[System.IO.File]::WriteAllText((Join-Path $distPath "start.bat"), $batContent, [System.Text.Encoding]::ASCII)
Write-Host "      OK" -ForegroundColor Green

# ---- Summary ----
Write-Host ""
Write-Host "======================================" -ForegroundColor Green
Write-Host "  Build Complete!" -ForegroundColor Green
Write-Host "======================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Release dir : $distPath" -ForegroundColor White
Write-Host ""
Write-Host "  Layout:" -ForegroundColor White
Write-Host "    dist/" -ForegroundColor Gray
Write-Host "    +-- semi-utils.exe   <- main program" -ForegroundColor Gray
Write-Host "    +-- start.bat        <- double-click to launch (creates input/output if missing)" -ForegroundColor Gray
Write-Host "    +-- config/          <- fonts / logos / templates" -ForegroundColor Gray
Write-Host "    +-- exiftool/        <- EXIF reader" -ForegroundColor Gray
Write-Host ""

# ---- Pack into ZIP ----
$zipPath = Join-Path $projectRoot "semi-utils-win.zip"
Write-Host "Packing zip..." -ForegroundColor Yellow
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $distPath "*") -DestinationPath $zipPath -Force
$sizeMB = [math]::Round((Get-Item $zipPath).Length / 1MB, 1)
Write-Host "  ZIP ready: $zipPath ($sizeMB MB)" -ForegroundColor Green
Write-Host ""