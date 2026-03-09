#!/bin/bash
# run.sh — Avvia Django + FastAPI in parallelo

echo "🤖 TelePanel — Avvio servizi..."

# Django (porta 8000)
DJANGO_SETTINGS_MODULE=settings python manage.py runserver 8000 &
DJANGO_PID=$!

# FastAPI (porta 8001)
uvicorn fastapi_api.main:app --port 8001 --reload &
FASTAPI_PID=$!

echo "✅ Django avviato su http://localhost:8000"
echo "✅ FastAPI avviato su http://localhost:8001"
echo "📖 FastAPI Docs: http://localhost:8001/docs"
echo ""
echo "Premi Ctrl+C per fermare entrambi i servizi."

# Attendi e gestisci Ctrl+C
trap "kill $DJANGO_PID $FASTAPI_PID; echo ''; echo '⏻ Servizi fermati.'" SIGINT SIGTERM
wait
