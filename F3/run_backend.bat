@echo off
echo Installing and starting Engineering Change Assistant Backend (Python FastAPI)

if not exist venv (
    echo Creating virtual environment...
    python -m venv venv
)

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing requirements...
pip install -r backend\requirements.txt

echo Starting 5-Agent Orchestrator Backend on port 5000...
cd backend
python -u app.py

pause
