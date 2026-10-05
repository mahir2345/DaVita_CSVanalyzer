@echo off
REM Simple launcher for DaVita on Windows

cd /d "%~dp0"

IF NOT EXIST ".venv" (
    echo Creating virtual environment...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Installing dependencies (first run may take a while)...
pip install -r requirements.txt

echo Starting DaVita on http://127.0.0.1:5000 ...
python main.py

pause

