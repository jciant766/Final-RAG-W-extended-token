@echo off
echo ============================================================
echo Maltese Law RAG - Starting Production Server
echo ============================================================
echo.

REM Check if virtual environment exists
if exist venv (
    echo Activating virtual environment...
    call venv\Scripts\activate
) else (
    echo No virtual environment found. Using system Python.
)

echo.
echo Installing/updating dependencies...
pip install -r requirements.txt --quiet

echo.
echo Starting server on http://localhost:5000
echo Press Ctrl+C to stop
echo ============================================================
echo.

python api.py
