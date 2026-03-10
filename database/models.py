"""
database/models.py
Modelli SQLAlchemy — abstraction layer condiviso tra bot e web panel.
"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime,
    ForeignKey, Text, BigInteger
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Utente(Base):
    """Utente Telegram registrato."""
    __tablename__ = "utenti"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(64), nullable=True)
    nome = Column(String(128), nullable=True)
    cognome = Column(String(128), nullable=True)
    is_admin = Column(Boolean, default=False)
    attivo = Column(Boolean, default=True)
    creato_il = Column(DateTime, default=datetime.utcnow)
    aggiornato_il = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    canali = relationship("Canale", back_populates="proprietario")
    messaggi = relationship("Messaggio", back_populates="autore")

    def __repr__(self):
        return f"<Utente telegram_id={self.telegram_id} username={self.username}>"

    @property
    def nome_completo(self):
        parts = [self.nome, self.cognome]
        return " ".join(p for p in parts if p) or self.username or str(self.telegram_id)


class Canale(Base):
    """Canale Telegram gestito dal bot."""
    __tablename__ = "canali"

    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    nome = Column(String(256), nullable=False)
    username = Column(String(64), nullable=True)
    attivo = Column(Boolean, default=True)
    proprietario_id = Column(Integer, ForeignKey("utenti.id"), nullable=True)
    registrato_il = Column(DateTime, default=datetime.utcnow)

    proprietario = relationship("Utente", back_populates="canali")
    messaggi = relationship("Messaggio", back_populates="canale")

    def __repr__(self):
        return f"<Canale nome={self.nome} id={self.telegram_id}>"


class Messaggio(Base):
    """Storico messaggi pubblicati."""
    __tablename__ = "messaggi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    testo = Column(Text, nullable=True)
    media_id = Column(String(256), nullable=True)
    tipo_media = Column(String(32), nullable=True)  # photo, video, document, None
    pubblicato = Column(Boolean, default=False)
    pubblicato_il = Column(DateTime, nullable=True)
    telegram_message_id = Column(BigInteger, nullable=True)

    autore_id = Column(Integer, ForeignKey("utenti.id"), nullable=True)
    canale_id = Column(Integer, ForeignKey("canali.id"), nullable=True)

    autore = relationship("Utente", back_populates="messaggi")
    canale = relationship("Canale", back_populates="messaggi")

    creato_il = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Messaggio id={self.id} pubblicato={self.pubblicato}>"


class LogEvento(Base):
    """Log eventi del bot per il pannello di monitoraggio."""
    __tablename__ = "log_eventi"

    id = Column(Integer, primary_key=True, autoincrement=True)
    livello = Column(String(16), nullable=False)   # INFO, WARNING, ERROR
    sorgente = Column(String(64), nullable=False)  # bot, web, api
    messaggio = Column(Text, nullable=False)
    dettagli = Column(Text, nullable=True)
    creato_il = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return f"<LogEvento livello={self.livello} sorgente={self.sorgente}>"


class PanelUser(Base):
    """Utenti del web panel — separati dagli utenti Telegram."""
    __tablename__ = "panel_users"

    id            = Column(Integer, primary_key=True, autoincrement=True)
    username      = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    nome          = Column(String(128), nullable=True)
    ruolo         = Column(String(16), default="viewer")   # admin | viewer
    attivo        = Column(Boolean, default=True)
    creato_il     = Column(DateTime, default=datetime.utcnow)
    ultimo_login  = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<PanelUser username={self.username} ruolo={self.ruolo}>"
