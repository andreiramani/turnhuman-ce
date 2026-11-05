@echo off
setlocal
title TurnHuman Community Edition (CE)
echo ======================================================================
echo   TurnHuman Community Edition Launcher
echo   AI Footprint Removal Engine
echo ======================================================================
echo.

REM 1. Check Python
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [ERROR] Python was not found in your system PATH.
    echo Please install Python 3.10 or higher from https://www.python.org/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

echo [1/3] Checking Python environment...
python -c "import sys; print(f'      Active Python: {sys.version}')"

REM 2. Check Streamlit dependency
python -c "import streamlit" >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Required dependencies not found. Installing requirements...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install dependencies. Please run 'pip install -r requirements.txt' manually.
        pause
        exit /b 1
    )
)

echo [2/3] Checking spaCy linguistic model...
python -c "import spacy; spacy.load('en_core_web_sm')" >nul 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Downloading spaCy model 'en_core_web_sm'...
    python -m spacy download en_core_web_sm
)

REM 3. Launch Application
echo [3/3] Launching TurnHuman CE dashboard in your default browser...
echo.
python -m streamlit run app.py --server.headless=false
if %errorlevel% neq 0 (
    echo.
    echo [INFO] Trying direct streamlit command...
    streamlit run app.py --server.headless=false
    if %errorlevel% neq 0 (
        echo [ERROR] Application exited with error.
        pause
    )
)
