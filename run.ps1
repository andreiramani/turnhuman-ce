# ==============================================================================
# TurnHuman Community Edition (CE) - PowerShell One-Click Launcher
# ==============================================================================

Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "  TurnHuman Community Edition Launcher" -ForegroundColor Green
Write-Host "  Zero Generative AI | Linguistic Suite" -ForegroundColor Yellow
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Verify Python availability
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[ERROR] Python was not found in your system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/ and check 'Add to PATH'." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "[1/3] Checking Python environment..." -ForegroundColor Gray
$pyVer = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
Write-Host "      Detected Python: $pyVer" -ForegroundColor Green

# 2. Verify Streamlit and Core Packages
Write-Host "[2/3] Checking core packages..." -ForegroundColor Gray
$stCheck = python -c "import streamlit, docx, spacy; print('OK')" 2>$null
if ($stCheck -ne "OK") {
    Write-Host "      Installing missing requirements from requirements.txt..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install requirements." -ForegroundColor Red
        Read-Host "Press Enter to exit..."
        exit 1
    }
}

# Check spaCy model
$spacyModelCheck = python -c "import spacy; spacy.load('en_core_web_sm'); print('OK')" 2>$null
if ($spacyModelCheck -ne "OK") {
    Write-Host "      Downloading spaCy model 'en_core_web_sm'..." -ForegroundColor Yellow
    python -m spacy download en_core_web_sm
}

# 3. Launch Application
Write-Host "[3/3] Launching TurnHuman CE Dashboard..." -ForegroundColor Gray
Write-Host "      Opening http://localhost:8501 in your default browser..." -ForegroundColor Green
Write-Host ""

python -m streamlit run app.py --server.headless=false
if ($LASTEXITCODE -ne 0) {
    streamlit run app.py --server.headless=false
}
