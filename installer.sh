#!/bin/bash
set -e

LOGFILE="install.log"
echo "[*] Starting installation at $(date)" | tee "$LOGFILE"

if ! command -v python3 &>/dev/null; then
    echo "Python 3 is required but not installed." | tee -a "$LOGFILE"
    exit 1
fi

if ! command -v pip3 &>/dev/null; then
    echo "pip3 is required but not installed." | tee -a "$LOGFILE"
    exit 1
fi

if ! command -v git &>/dev/null; then
    echo "git is required but not installed." | tee -a "$LOGFILE"
    exit 1
fi

echo "[*] Installing virtualenv..." | tee -a "$LOGFILE"
pip3 install --user virtualenv >>"$LOGFILE" 2>&1

echo "[*] Creating virtual environment..." | tee -a "$LOGFILE"
python3 -m virtualenv venv >>"$LOGFILE" 2>&1

echo "[*] Activating virtual environment..." | tee -a "$LOGFILE"
source venv/bin/activate

echo "[*] Installing project requirements..." | tee -a "$LOGFILE"
pip install -r requirements.txt >>"$LOGFILE" 2>&1

if [ -f .env.sample ] && [ ! -f .env ]; then
    echo "[*] Copying .env.sample to .env" | tee -a "$LOGFILE"
    cp .env.sample .env
fi

echo "[*] Installation complete." | tee -a "$LOGFILE"
