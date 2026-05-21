@echo off
REM Change directory to the project location
cd /d "C:\Users\rocks\Documents\CLaude\StudyMind"

REM 1. Create a virtual environment (if it doesn't exist)
python -m venv venv

REM 2. Activate the virtual environment and run the script in one go.
REM NOTE: Directly calling 'activate' within a batch file can sometimes fail to persist the path changes for subsequent commands.
call venv\Scripts\activate.bat

echo --- Running Python Application ---
python app.py

REM Optional: Deactivate when finished
pause
