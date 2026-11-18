@echo off
chcp 65001 >nul
title Ultra 5x 20TB - 12 months
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================
echo   Google AI Ultra 5x 20TB - 12 months free
echo   Confirm the sheet says: 12-month free trial
echo ============================================
python ultra0.py --account "current@device" --no-add --force --plan 5x
echo.
pause