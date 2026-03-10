@echo off
title Web Services

:: Crea la cartella sessioni se non esiste
if not exist ".sessions" mkdir .sessions

echo  Avvio FastAPI (porta %FASTAPI_PORT%)...
set FASTAPI_PORT=8001
start "FastAPI API" cmd /k "python -m uvicorn web.fastapi_app:app --reload --port %FASTAPI_PORT% --host 127.0.0.1"

timeout /t 2 /nobreak >nul

echo  Avvio Django Panel (porta %DJANGO_PORT%)...
set DJANGO_PORT=8000
start "Django Panel" cmd /k "python -m django runserver %DJANGO_PORT% --settings web.core.settings"

echo.
echo  Web services avviati:
echo    Panel:    http://localhost:%DJANGO_PORT%
echo    API docs: http://localhost:%FASTAPI_PORT%/docs
echo.
