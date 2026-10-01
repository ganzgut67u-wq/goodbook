@echo off
title BedWars Bots Launcher
cls
echo =======================================================
echo   Launching FunPay & Playerok BedWars Bots...
echo =======================================================
echo.
start "FunPay BedWars Bot" cmd /k "cd /d "%~dp0FunPay_BedWars_Bot" && python main.py"
start "Playerok BedWars Bot" cmd /k "cd /d "%~dp0Playerok_BedWars_Bot" && python main.py"
echo [OK] Оба бота (FunPay + Playerok) успешно запущены в отдельных окнах!
echo.
pause
