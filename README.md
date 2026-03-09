# 🤖 Telegram Bot — Web Panel

Stack: **Django** (frontend/auth) + **FastAPI** (API layer) + **SQLite/PostgreSQL**

## Struttura

```
telegram-panel/
├── web_panel/              # Django app (UI, auth, dashboard)
│   ├── templates/          # HTML templates
│   ├── static/             # CSS, JS, assets
│   ├── views.py
│   ├── urls.py
│   └── models.py
│
├── fastapi_api/            # FastAPI (REST API per il bot)
│   ├── main.py
│   ├── routes/
│   │   ├── channels.py
│   │   ├── messages.py
│   │   └── stats.py
│   └── schemas.py
│
├── bot_bridge/             # Bridge Django ↔ Bot Telegram
│   └── client.py
│
├── manage.py
├── settings.py
├── requirements.txt
└── run.sh
```

## Avvio rapido

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
# In due terminali separati:
python manage.py runserver        # Django :8000
uvicorn fastapi_api.main:app --port 8001 --reload  # FastAPI :8001
```
