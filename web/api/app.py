"""
web/api/app.py
FastAPI — REST API per il web panel.
Usa i modelli reali in database/models.py e la sessione in database/session.py.

Avvio:  uvicorn web.fastapi_app:app --reload --port 8001
"""
from __future__ import annotations

import sys
import os

# ROOT nel path PRIMA di qualsiasi import locale
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telegram import Bot
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
from shared.config import bot_config, web_config
from web.api.dependencies import jwt_required, admin_required

# ---------------------------------------------------------------------------
app = FastAPI(title="Telegram Bot — Web Panel API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        f"http://localhost:{web_config.DJANGO_PORT}",
        f"http://127.0.0.1:{web_config.DJANGO_PORT}",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Bot singleton — inizializzato una volta sola all'avvio di FastAPI
# e riutilizzato da tutte le richieste broadcast.
_bot: Bot | None = None


@app.on_event("startup")
async def startup():
    global _bot
    init_db_sync()
    _bot = Bot(token=bot_config.TOKEN)
    await _bot.initialize()
    print(f"[STARTUP] Bot inizializzato: {_bot.token[:10]}...", flush=True)


@app.on_event("shutdown")
async def shutdown():
    global _bot
    if _bot:
        await _bot.shutdown()
        print("[SHUTDOWN] Bot chiuso.", flush=True)


# DB dependency
def get_db():
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


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


# ── Auth endpoints (pubblici, no JWT richiesto) ──────────────────────────────

class LoginPayload(BaseModel):
    username: str
    password: str

class RefreshPayload(BaseModel):
    refresh: str

@app.post("/api/auth/token", tags=["auth"])
def login(payload: LoginPayload):
    """
    Autentica tramite django.contrib.auth + genera JWT con simplejwt.
    """
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
    if not django.apps.registry.apps.ready:
        django.setup()

    from django.contrib.auth import authenticate as dj_authenticate
    from web.core.auth import genera_token_per_utente

    class _Req:
        META = {}
        session = {}
        method = "POST"

    user = dj_authenticate(_Req(), username=payload.username, password=payload.password)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Credenziali non valide.")

    return genera_token_per_utente(user)


@app.post("/api/auth/refresh", tags=["auth"])
def token_refresh(payload: RefreshPayload):
    """Rinnova l'access token dato un refresh token valido (simplejwt)."""
    import django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "web.core.settings")
    if not django.apps.registry.apps.ready:
        django.setup()

    from web.core.auth import refresh_access_token
    from rest_framework_simplejwt.exceptions import InvalidToken
    try:
        return refresh_access_token(payload.refresh)
    except InvalidToken as e:
        raise HTTPException(status_code=401, detail=str(e))
@app.get("/api/stats", response_model=StatsSchema)
def get_stats(db: Session = Depends(get_db), _user=Depends(jwt_required)):
    oggi = date.today()
    return StatsSchema(
        utenti_totali=db.query(Utente).count(),
        utenti_attivi=db.query(Utente).filter_by(attivo=True).count(),
        canali_attivi=db.query(Canale).filter_by(attivo=True).count(),
        messaggi_totali=db.query(Messaggio).count(),
        messaggi_oggi=db.query(Messaggio).filter(Messaggio.creato_il >= oggi).count(),
    )

@app.get("/api/utenti", response_model=List[UtenteSchema])
def get_utenti(db: Session = Depends(get_db), _user=Depends(jwt_required)):
    return db.query(Utente).order_by(desc(Utente.creato_il)).all()

@app.get("/api/utenti/{utente_id}", response_model=UtenteSchema)
def get_utente(utente_id: int, db: Session = Depends(get_db), _user=Depends(jwt_required)):
    u = db.query(Utente).filter_by(id=utente_id).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    return u

@app.patch("/api/utenti/{utente_id}/ban")
def ban_utente(utente_id: int, db: Session = Depends(get_db), _user=Depends(admin_required)):
    u = db.query(Utente).filter_by(id=utente_id).first()
    if not u:
        raise HTTPException(404, "Utente non trovato")
    u.attivo = not u.attivo
    db.commit()
    return {"attivo": u.attivo}

@app.get("/api/canali", response_model=List[CanaleSchema])
def get_canali(solo_attivi: bool = False, db: Session = Depends(get_db), _user=Depends(jwt_required)):
    q = db.query(Canale)
    if solo_attivi:
        q = q.filter_by(attivo=True)
    return q.order_by(desc(Canale.registrato_il)).all()

@app.delete("/api/canali/{telegram_id}")
def rimuovi_canale(telegram_id: int, db: Session = Depends(get_db), _user=Depends(admin_required)):
    c = db.query(Canale).filter_by(telegram_id=telegram_id).first()
    if not c:
        raise HTTPException(404, "Canale non trovato")
    c.attivo = False
    db.commit()
    return {"rimosso": True}

@app.get("/api/messaggi", response_model=List[MessaggioSchema])
def get_messaggi(limit: int = 50, db: Session = Depends(get_db), _user=Depends(jwt_required)):
    return db.query(Messaggio).order_by(desc(Messaggio.creato_il)).limit(limit).all()

@app.get("/api/logs", response_model=List[LogSchema])
def get_logs(limit: int = 100, db: Session = Depends(get_db), _user=Depends(jwt_required)):
    return db.query(LogEvento).order_by(desc(LogEvento.creato_il)).limit(limit).all()

@app.post("/api/broadcast")
async def broadcast(payload: BroadcastPayload, _user=Depends(admin_required)):
    """
    Usa il Bot singleton inizializzato all'avvio — mai ricreato per ogni richiesta.
    Questo garantisce che la sessione HTTP sia già aperta e stabile.
    """
    if _bot is None:
        raise HTTPException(status_code=503, detail="Bot non ancora inizializzato, riprova tra un secondo.")

    risultato = await pubblica_su_canali(bot=_bot, testo=payload.testo)
    return {"inviato_a": risultato.ok, "errori": risultato.fail}

@app.get("/api/health")
def health():
    return {"status": "ok"}

