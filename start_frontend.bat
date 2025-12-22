@echo off
cd /d "%~dp0"
echo Starting Frontend...
cd frontend
npm run dev
pause
