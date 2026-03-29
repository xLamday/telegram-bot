# 🤖 Telegram Bot

Bot Telegram sviluppato in **Python** per la gestione avanzata di messaggi e canali.  
Permette di inoltrare messaggi privati verso canali, gestire comandi personalizzati, monitorare lo stato dei canali e mantenere il controllo delle pubblicazioni.

---
    
## 📌 Indice

- [Caratteristiche](#-caratteristiche)
- [Tecnologie Utilizzate](#-tecnologie-utilizzate)
- [Requisiti](#-requisiti)
- [Struttura del Progetto](#struttura-del-progetto)

---

## Struttura del progetto
```text
telegram-bot/
│
├── main.py
├── loggerinfo.py
├── requirements.txt
├── README.md
│
├── config/
│   ├── __init__.py
│   └── settings.py
│
├── comandi/
│   └── cmd.py
│
├── funzioni/
│   ├── registra.py
│   ├── scheduledfunzioni.py
│   └── system.py
│
│
├── utils/
│   ├── __init__.py
│   ├── rate_limiter.py
│   └── telegram_errors.py
│
└── database/
    ├── __init__.py
    ├── base.py
    ├── manager.py
    ├── post_db.py
    ├── channel_db.py
    ├── database.py
    └── connection.py
```

---

## 🚀 Caratteristiche

✔️Layer database in un package modulare:
- Package database con i moduli manager, base, channel_db e post_db
- Implementa il nuovo DatabaseManager con API .channel e .post

✔️ Gestione comandi personalizzati

✔️ Pubblicazione messaggi su canali Telegram

✔️ Inoltro messaggi da chat privata a canali

✔️ Rimozione e gestione canali registrati

✔️ Monitoraggio periodico dello stato del bot

✔️ Logging strutturato degli eventi

✔️ Gestione automatica dell'aggiunta/rimozione del bot dai canali

✔️ RateLimiter asincrono (utils.rate_limiter) con attese preventive, gestione RetryAfter e statistiche

✔️ TelegramErrorClassificatore (utils.telegram_errors) per la classificazione strutturata degli errori Telegram

---

## 🛠 Tecnologie Utilizzate

- Python 3.10+
- python-telegram-bot
- Sistema di logging personalizzato
- Struttura modulare a cartelle

---

## 📋 Requisiti

Assicurati di avere installato:

- Python 3.10 o superiore
- pip

Installa le dipendenze con:

```bash
pip install -r requirements.txt
