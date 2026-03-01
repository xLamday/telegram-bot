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
│   └── settings.py
│
├── comandi/
│   ├── start.py
│   ├── pubblica.py
│   ├── rimuovi.py
│   └── check_canali.py
│
├── funzioni/
│   ├── registrazione.py
│   ├── gestione_canali.py
│   └── system.py
│
└── database/
    ├── db.py
    └── setup.py
```

---

## 🚀 Caratteristiche

✔️ Gestione comandi personalizzati  
✔️ Pubblicazione messaggi su canali Telegram  
✔️ Inoltro messaggi da chat privata a canali  
✔️ Rimozione e gestione canali registrati  
✔️ Monitoraggio periodico dello stato del bot  
✔️ Logging strutturato degli eventi  
✔️ Gestione automatica dell'aggiunta/rimozione del bot dai canali  

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
