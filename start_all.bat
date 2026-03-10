@echo off
title Telegram Bot Panel - All Services
color 0A

:: ============================================================
::  Vai sempre alla root del progetto (dove sta questo .bat)
:: ============================================================
cd /d "%~dp0"

echo.
echo  =====================================================
echo   TelePanel ^| Avvio servizi
echo  =====================================================
echo.

:: ============================================================
::  1. Crea .env se non esiste
:: ============================================================
if not exist ".env" (
    echo  [SETUP] File .env non trovato, creazione in corso...
    echo.

    (
        echo # =====================================================
        echo # TelePanel — Configurazione
        echo # Modifica i valori qui sotto prima di riavviare.
        echo # =====================================================
        echo.
        echo # Token del bot ^(da @BotFather su Telegram^)
        echo TELEGRAM_BOT_TOKEN="8477419835:AAE1mVmAc9TQ6T8lQ0itd3DRInLTtRAyv3g"
        echo.
        echo # ID Telegram degli amministratori ^(separati da virgola^)
        echo ADMIN_IDS=961492841
        echo.
        echo # Database ^(SQLite di default, zero configurazione^)
        echo DATABASE_SYNC_URL=sqlite:///./data/bot.db
        echo.
        echo # Django
        echo DJANGO_SECRET_KEY="vm7@w5tdo(1qj4sfm$u$4*_ng)4v4d5j*3u=(b4q9*o&rs+%q!"
        echo DEBUG=true
        echo ALLOWED_HOSTS=localhost,127.0.0.1
        echo.
        echo # Porte
        echo FASTAPI_PORT=8001
        echo DJANGO_PORT=8000
        echo.
        echo # Credenziali primo admin del web panel
        echo PANEL_ADMIN_USER=admin
        echo PANEL_ADMIN_PASS=admin1234
    ) > .env

    echo  [SETUP] File .env creato!
    echo.
    echo  ATTENZIONE: Prima di continuare devi impostare:
    echo    ^> TELEGRAM_BOT_TOKEN  ^(da @BotFather^)
    echo    ^> ADMIN_IDS           ^(il tuo ID numerico Telegram^)
    echo.
    echo  Puoi trovare il tuo ID scrivendo a @userinfobot su Telegram.
    echo.
    echo  Apri il file .env nella cartella del progetto, modifica
    echo  i valori e poi rilancia start_all.bat.
    echo.
    pause
    start "" notepad ".env"
    exit /b
)

:: ============================================================
::  2. Controlla che il token non sia ancora quello placeholder
:: ============================================================
findstr /C:"INSERISCI_IL_TUO_TOKEN_QUI" .env >nul 2>&1
if %errorlevel%==0 (
    echo  [ERRORE] Il TELEGRAM_BOT_TOKEN nel file .env non e' stato configurato!
    echo.
    echo  Apri .env e sostituisci INSERISCI_IL_TUO_TOKEN_QUI con il token reale.
    echo.
    pause
    start "" notepad ".env"
    exit /b
)

:: ============================================================
::  3. Crea cartelle necessarie
:: ============================================================
if not exist "data"      mkdir data
if not exist ".sessions" mkdir .sessions
if not exist "logs"      mkdir logs

:: ============================================================
::  4. Avvia i servizi
:: ============================================================
echo  Avvio servizi web...
call start_web.bat
timeout /t 3 /nobreak >nul

echo  Avvio Bot Telegram...
start "Bot Telegram" cmd /k "cd /d "%~dp0" && python bot\main.py"

echo.
echo  =====================================================
echo   Tutti i servizi sono avviati!
echo.
echo   Panel:    http://localhost:8000
echo   API docs: http://localhost:8001/docs
echo.
echo   Login panel: controlla le credenziali nel .env
echo   (PANEL_ADMIN_USER / PANEL_ADMIN_PASS)
echo  =====================================================
echo.
pause
