@echo off
cd /d "%~dp0"
echo Activating virtual environment...
if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo Virtual environment not found at .venv
    echo Please make sure you have created the virtual environment in the project root.
    pause
    exit /b
)

echo Starting mABC Blockchain API Server...
python frontend/api_server.py
pause
