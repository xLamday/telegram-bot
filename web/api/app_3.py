"""
web/api/app.py
FastAPI — REST API per il web panel.
Usa i modelli reali in database/models.py e la sessione in database/session.py.

Avvio:  uvicorn web.fastapi_app:app --reload --port 8001
"""
from __future__ import annotations

import sys
import os
from contextlib import asynccontextmanager

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telegram import Bot
from shared.config import bot_config
from bot.comandi.pubblica import pubblica_su_canali

from datetime import datetime, date
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from database.models import Base, Utente, Canale, Messaggio, LogEvento
from database.session import SyncSessionLocal, init_db_sync
from shared.config import web_config

# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db_sync()
    _seed_panel_admin()
    yield


app = FastAPI(title="Telegram Bot — Web Panel API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{web_config.DJANGO_PORT}",
        f"http://127.0.0.1:{web_config.DJANGO_PORT}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# DB dependency
def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


def _seed_panel_admin():
    """Crea il primo admin panel se non ne esiste nessuno."""
    try:
        from database.models import PanelUser
        from web.core.auth import hash_password
        db = SyncSessionLocal()
        try:
            if db.query(PanelUser).filter_by(ruolo="admin").count() == 0:
                admin_user = os.getenv("PANEL_ADMIN_USER", "admin")
                admin_pass = os.getenv("PANEL_ADMIN_PASS", "admin1234")
                db.add(PanelUser(
                    username=admin_user,
                    password_hash=hash_password(admin_pass),
                    nome="Amministratore",
                    ruolo="admin",
                ))
                db.commit()
                print(f"[AUTH] Admin panel creato: {admin_user} / {admin_pass}")
                print("[AUTH] Cambia la password dal pannello!")
        finally:
            db.close()
    except Exception as e:
        print(f"[AUTH] Seed admin saltato: {e}")


# Schemas
class UtenteSchema(BaseModel):
    id: int
    telegram_id: int
    username: Optional[str]
    nome: Optional[str]
    cognome: Optional[str]
    attivo: bool
    is_admin: bool
    creato_il: datetime
    class Config:
        from_attributes = True

class CanaleSchema(BaseModel):
    id: int
    telegram_id: int
    nome: str
    username: Optional[str]
    attivo: bool
    registrato_il: datetime
    class Config:
        from_attributes = True

class MessaggioSchema(BaseModel):
    id: int
    testo: Optional[str] = None
    tipo_media: Optional[str] = None
    pubblicato: bool
    pubblicato_il: Optional[datetime] = None
    creato_il: datetime
    class Config:
        from_attributes = True

class LogSchema(BaseModel):
    id: int
    livello: str
    sorgente: Optional[str] = None
    messaggio: str
    dettagli: Optional[str] = None
    creato_il: datetime
    class Config:
        from_attributes = True

class StatsSchema(BaseModel):
    utenti_totali: int
    utenti_attivi: int
    canali_attivi: int
    messaggi_totali: int
    messaggi_oggi: int

class BroadcastPayload(BaseModel):
    testo: str


# Routes
@app.get("/api/stats", response_model=StatsSchema)
def get_stats(db: Session = Depends(get_db)):
    oggi = date.today()
    return StatsSchema(
        utenti_totali=db.query(Utente).count(),
        utenti_attivi=db.query(Utente).filter_by(attivo=True).count(),
        canali_attivi=db.query(Canale).filter_by(attivo=True).count(),
        messaggi_totali=db.query(Messaggio).count(),
        messaggi_oggi=db.query(Messaggio).filter(Messaggio.creato_il >= oggi).count(),
    )

@app.get("/api/utenti", response_model=List[UtenteSchema])
def get_utenti(db: Session = Depends(get_db)):
    return db.query(Utente).order_by(desc(Utente.creato_il)).all()

@app.get("/api/utenti/{utente_id}", response_model=UtenteSchema)
def get_utente(utente_id: int, db: Session = Depends(get_db)):
    u = db.query(Utente).filter_by(id=utente_id).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    return u

@app.patch("/api/utenti/{utente_id}/ban")
def ban_utente(utente_id: int, db: Session = Depends(get_db)):
    u = db.query(Utente).filter_by(id=utente_id).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    u.attivo = not u.attivo
    db.commit()
    return {"attivo": u.attivo}

@app.get("/api/canali", response_model=List[CanaleSchema])
def get_canali(solo_attivi: bool = False, db: Session = Depends(get_db)):
    q = db.query(Canale)
    if solo_attivi:
        q = q.filter_by(attivo=True)
    return q.order_by(desc(Canale.registrato_il)).all()

@app.delete("/api/canali/{telegram_id}")
def rimuovi_canale(telegram_id: int, db: Session = Depends(get_db)):
    c = db.query(Canale).filter_by(telegram_id=telegram_id).first()
    if not c:
        raise HTTPException(404, "Canale non trovato")
    c.attivo = False
    db.commit()
    return {"rimosso": True}

@app.get("/api/messaggi", response_model=List[MessaggioSchema])
def get_messaggi(limit: int = 50, db: Session = Depends(get_db)):
    return db.query(Messaggio).order_by(desc(Messaggio.creato_il)).limit(limit).all()

@app.get("/api/logs", response_model=List[LogSchema])
def get_logs(limit: int = 100, db: Session = Depends(get_db)):
    return db.query(LogEvento).order_by(desc(LogEvento.creato_il)).limit(limit).all()

@app.post("/api/broadcast")
async def broadcast(payload: BroadcastPayload):
    # bot = Bot(token=bot_config.TOKEN)
    # async with bot:
    #     risultato = await pubblica_su_canali(bot=bot, testo=payload.testo)
    # return {"inviato_a": risultato.ok, "errori": risultato.fail}
    import traceback
    from shared.logger import get_logger
    log = get_logger("api.broadcast")

    log.debug(f"[BROADCAST] Richiesta ricevuta — testo: {payload.testo!r}")

    try:
        token = bot_config.TOKEN
        log.debug(f"[BROADCAST] Token presente: {bool(token)}, lunghezza: {len(token) if token else 0}")

        bot = Bot(token=token)
        log.debug(f"[BROADCAST] Istanza Bot creata")

        async with bot:
            log.debug("[BROADCAST] Bot inizializzato, chiamo pubblica_su_canali...")
            risultato = await pubblica_su_canali(bot=bot, testo=payload.testo)

        log.debug(f"[BROADCAST] Completato — ok={risultato.ok}, fail={risultato.fail}")
        return {"inviato_a": risultato.ok, "errori": risultato.fail}

    except Exception as e:
        tb = traceback.format_exc()
        log.error(f"[BROADCAST] ECCEZIONE: {type(e).__name__}: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=f"{type(e).__name__}: {e}")

