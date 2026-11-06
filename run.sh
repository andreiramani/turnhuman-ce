#!/usr/bin/env bash
# ==============================================================================
# TurnHuman Community Edition (CE) - Linux & macOS Launcher
# ==============================================================================

# ANSI Color Codes
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

echo -e "${CYAN}======================================================================${NC}"
echo -e "${GREEN}  TurnHuman Community Edition Launcher${NC}"
echo -e "${YELLOW}  Zero Generative AI | Linguistic Suite${NC}"
echo -e "${CYAN}======================================================================${NC}"
echo ""

# 1. Detect Python command (python3 or python)
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python was not found in your system PATH.${NC}"
    echo -e "${YELLOW}Please install Python 3.10+ from https://www.python.org/ or via your package manager.${NC}"
    exit 1
fi

echo -e "${GRAY}[1/3] Checking Python environment...${NC}"
PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')" 2>/dev/null)
echo -e "      ${GREEN}Detected Python: ${PY_VER}${NC}"

# 2. Verify Streamlit and Core Packages
echo -e "${GRAY}[2/3] Checking core packages...${NC}"
ST_CHECK=$($PYTHON_CMD -c "import streamlit, docx, spacy; print('OK')" 2>/dev/null)
if [ "$ST_CHECK" != "OK" ]; then
    echo -e "      ${YELLOW}Installing missing requirements from requirements.txt...${NC}"
    $PYTHON_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}[ERROR] Failed to install requirements.${NC}"
        exit 1
    fi
fi

# Check spaCy model
SPACY_CHECK=$($PYTHON_CMD -c "import spacy; spacy.load('en_core_web_sm'); print('OK')" 2>/dev/null)
if [ "$SPACY_CHECK" != "OK" ]; then
    echo -e "      ${YELLOW}Downloading spaCy model 'en_core_web_sm'...${NC}"
    $PYTHON_CMD -m spacy download en_core_web_sm
fi

# 3. Launch Application
echo -e "${GRAY}[3/3] Launching TurnHuman CE Dashboard...${NC}"
echo -e "      ${GREEN}Opening http://localhost:8501 in your default browser...${NC}"
echo ""

$PYTHON_CMD -m streamlit run app.py --server.headless=false
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    streamlit run app.py --server.headless=false
fi
