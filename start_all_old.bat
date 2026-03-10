@echo off
title Telegram Bot Panel - All Services
color 0A
echo.
echo  Avvio di tutti i servizi...
echo.

call start_web.bat
timeout /t 3 /nobreak >nul

echo  Avvio Bot Telegram...
start "Bot Telegram" cmd /k "python bot\main.py"

echo.
echo  Tutti i servizi avviati!
echo.
pause
