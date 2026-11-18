@echo off
chcp 65001 >nul
title Ultra 20x 30TB - 1 month
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================
echo   Google AI Ultra 20x 30TB - 1 month free
echo ============================================
python ultra0.py --account "current@device" --no-add --force --plan 20x
echo.
pause