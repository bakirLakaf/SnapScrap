@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo   SnapScrap Web App
echo   http://127.0.0.1:5000
echo.
python -m flask --app webapp.app run --host 0.0.0.0 --port 5000
