@echo off
title Setup - Prima Installazione
color 0E
echo.
echo  ══════════════════════════════════════════════════
echo   SETUP - Telegram Bot Web Panel
echo  ══════════════════════════════════════════════════
echo.

REM Crea .env se non esiste
if not exist ".env" (
    echo  [1] Creo .env da .env.example...
    copy .env.example .env
    echo  [!] Apri il file .env e inserisci il tuo TELEGRAM_BOT_TOKEN!
    echo.
)

REM Crea cartella data/
if not exist "data" mkdir data
if not exist "logs" mkdir logs

REM Installa dipendenze
echo  [2] Installazione dipendenze Python...
pip install -r requirements.txt
echo.

REM Init database
echo  [3] Inizializzazione database...
python manage.py migrate --run-syncdb
echo.

REM Crea superuser
echo  [4] Creazione account admin per il pannello web...
echo  (Inserisci username e password quando richiesto)
echo.
python manage.py createsuperuser
echo.

echo  ══════════════════════════════════════════════════
echo   Setup completato!
echo.
echo   Prossimi passi:
echo   1. Modifica .env con il tuo TELEGRAM_BOT_TOKEN
echo   2. Esegui start_web.bat per avviare il pannello
echo   3. Esegui start_all.bat per avviare tutto
echo  ══════════════════════════════════════════════════
echo.
pause
