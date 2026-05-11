@echo off
echo Starting YGGDRASIL_OS Backend (Flask)...
cd backend
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" app.py
) else (
  python app.py
)
pause
