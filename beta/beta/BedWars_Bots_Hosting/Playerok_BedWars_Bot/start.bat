@echo off
title Playerok BedWars Bot
cls
echo =======================================================
echo   Playerok BedWars Auto-Notifier Bot
echo =======================================================
echo.
python main.py
if errorlevel 1 (
    echo.
    echo [ERROR] Python script failed or Python is not installed.
    echo.
)
pause
