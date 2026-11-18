@echo off
chcp 65001 >nul
title Pro +6 months - step 2
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
echo ============================================
echo   Google AI Pro 5TB - add 6 months (step 2)
echo   Run this ONLY after step 1 succeeded
echo ============================================
python ultra0.py --account "current@device" --no-add --force --plan pro6
echo.
pause