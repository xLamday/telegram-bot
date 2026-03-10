# 🤖 Telegram Bot Web Panel

Stack: **Python 3.10+** | **Django 4.2** | **FastAPI** | **SQLite/PostgreSQL** | **Tailwind CSS**

## 📁 Struttura

```
telegram-bot-panel/
│
├── bot/                        # Logica bot Telegram (originale)
│   ├── comandi/                # Handlers comandi (/start, /pubblica, ecc.)
│   ├── funzioni/               # Utility bot
│   ├── config/                 # Settings bot
│   └── main.py                 # Entry point bot
│
├── database/                   # Abstraction layer DB (condiviso)
│   ├── models.py               # Modelli SQLAlchemy
│   ├── repository.py           # Repository pattern (CRUD)
│   ├── session.py              # Gestione sessioni DB
│   └── migrations/             # Alembic migrations
│
├── web/
│   ├── django_panel/           # App Django (frontend pannello)
│   │   ├── views.py            # Views Django
│   │   ├── urls.py             # URL routing
│   │   ├── templates/          # HTML templates
│   │   └── static/             # CSS / JS
│   │
│   └── fastapi_app/            # FastAPI (REST API)
│       ├── main.py             # Entry point FastAPI
│       ├── routers/            # Route handlers
│       └── schemas/            # Pydantic schemas
│
├── shared/                     # Codice condiviso bot + web
│   ├── config.py               # Configurazione globale
│   └── logger.py               # Logger condiviso
│
├── manage.py                   # Django management
├── django_settings.py          # Configurazione Django
├── requirements.txt
├── start_bot.bat               # Avvia bot (Windows)
├── start_web.bat               # Avvia web panel (Windows)
└── start_all.bat               # Avvia tutto (Windows)
```

## 🚀 Avvio rapido (Windows 11)

```bat
# Installa dipendenze
pip install -r requirements.txt

# Inizializza database
python manage.py migrate

# Avvia tutto
start_all.bat
```

- **Pannello Web**: http://localhost:8000
- **API FastAPI**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
