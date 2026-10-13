@echo off
rem Double-click to start Investment Advisor on Windows.
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Get it from https://www.python.org/downloads/ and tick "Add Python to PATH".
  pause
  exit /b 1
)
if not exist .venv (
  echo First run: setting things up. This takes a minute...
  python -m venv .venv
)
call .venv\Scripts\activate
pip install -q -r requirements.txt
echo Starting the app. Your browser will open shortly. Close this window to stop it.
streamlit run app.py
pause
