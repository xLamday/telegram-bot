"""
database/repository.py
Repository pattern — CRUD generico + repository specifici.
Usato sia dal bot (async) che dal web panel (sync/async).
"""
from __future__ import annotations
from datetime import datetime
from typing import Generic, TypeVar, Type, Optional, List

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from database.models import Base, Utente, Canale, Messaggio, LogEvento

T = TypeVar("T", bound=Base)


# ══════════════════════════════════════════════════════════════════════════════
# BASE REPOSITORY (ASYNC)
# ══════════════════════════════════════════════════════════════════════════════
class AsyncRepository(Generic[T]):
    def __init__(self, model: Type[T], session: AsyncSession):
        self.model = model
        self.session = session

    async def get(self, id: int) -> Optional[T]:
        result = await self.session.execute(select(self.model).where(self.model.id == id))
        return result.scalar_one_or_none()

    async def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        result = await self.session.execute(
            select(self.model).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def create(self, **kwargs) -> T:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def update(self, id: int, **kwargs) -> Optional[T]:
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.commit()
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.commit()
        return result.rowcount > 0

    async def count(self) -> int:
        result = await self.session.execute(select(func.count()).select_from(self.model))
        return result.scalar_one()


# ══════════════════════════════════════════════════════════════════════════════
# BASE REPOSITORY (SYNC)  →  per Django views e script
# ══════════════════════════════════════════════════════════════════════════════
class SyncRepository(Generic[T]):
    def __init__(self, model: Type[T], session: Session):
        self.model = model
        self.session = session

    def get(self, id: int) -> Optional[T]:
        return self.session.get(self.model, id)

    def get_all(self, limit: int = 100, offset: int = 0) -> List[T]:
        return self.session.execute(
            select(self.model).offset(offset).limit(limit)
        ).scalars().all()

    def create(self, **kwargs) -> T:
        obj = self.model(**kwargs)
        self.session.add(obj)
        self.session.commit()
        self.session.refresh(obj)
        return obj

    def update(self, id: int, **kwargs) -> Optional[T]:
        self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        self.session.commit()
        return self.get(id)

    def delete(self, id: int) -> bool:
        result = self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        self.session.commit()
        return result.rowcount > 0

    def count(self) -> int:
        return self.session.execute(
            select(func.count()).select_from(self.model)
        ).scalar_one()


# ══════════════════════════════════════════════════════════════════════════════
# REPOSITORY SPECIFICI
# ══════════════════════════════════════════════════════════════════════════════

class UtenteRepository:
    """Repository per Utente — versione asincrona (bot / FastAPI)."""

    def __init__(self, session: AsyncSession):
        self._base = AsyncRepository(Utente, session)
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Utente]:
        result = await self.session.execute(
            select(Utente).where(Utente.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, telegram_id: int, **defaults) -> tuple[Utente, bool]:
        utente = await self.get_by_telegram_id(telegram_id)
        if utente:
            return utente, False
        utente = await self._base.create(telegram_id=telegram_id, **defaults)
        return utente, True

    async def get_all(self, limit=100, offset=0) -> List[Utente]:
        return await self._base.get_all(limit, offset)

    async def count(self) -> int:
        return await self._base.count()

    async def count_attivi(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Utente).where(Utente.attivo == True)
        )
        return result.scalar_one()


class CanaleRepository:
    """Repository per Canale — versione asincrona."""

    def __init__(self, session: AsyncSession):
        self._base = AsyncRepository(Canale, session)
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[Canale]:
        result = await self.session.execute(
            select(Canale).where(Canale.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    async def get_attivi(self) -> List[Canale]:
        result = await self.session.execute(
            select(Canale).where(Canale.attivo == True)
        )
        return result.scalars().all()

    async def get_all(self, limit=100, offset=0) -> List[Canale]:
        return await self._base.get_all(limit, offset)

    async def registra(self, telegram_id: int, nome: str, **kwargs) -> tuple[Canale, bool]:
        canale = await self.get_by_telegram_id(telegram_id)
        if canale:
            return canale, False
        canale = await self._base.create(telegram_id=telegram_id, nome=nome, **kwargs)
        return canale, True

    async def disattiva(self, telegram_id: int) -> bool:
        canale = await self.get_by_telegram_id(telegram_id)
        if not canale:
            return False
        await self._base.update(canale.id, attivo=False)
        return True

    async def count(self) -> int:
        return await self._base.count()


class MessaggioRepository:
    """Repository per Messaggio — versione asincrona."""

    def __init__(self, session: AsyncSession):
        self._base = AsyncRepository(Messaggio, session)
        self.session = session

    async def crea(self, **kwargs) -> Messaggio:
        return await self._base.create(**kwargs)

    async def segna_pubblicato(self, id: int, telegram_message_id: int) -> Optional[Messaggio]:
        return await self._base.update(
            id,
            pubblicato=True,
            pubblicato_il=datetime.utcnow(),
            telegram_message_id=telegram_message_id,
        )

    async def get_recenti(self, limit: int = 20) -> List[Messaggio]:
        result = await self.session.execute(
            select(Messaggio)
            .order_by(Messaggio.creato_il.desc())
            .limit(limit)
        )
        return result.scalars().all()

    async def count(self) -> int:
        return await self._base.count()

    async def count_pubblicati(self) -> int:
        result = await self.session.execute(
            select(func.count()).select_from(Messaggio).where(Messaggio.pubblicato == True)
        )
        return result.scalar_one()


class LogEventoRepository:
    """Repository per LogEvento."""

    def __init__(self, session: AsyncSession):
        self._base = AsyncRepository(LogEvento, session)
        self.session = session

    async def log(self, livello: str, sorgente: str, messaggio: str, dettagli: str = None):
        return await self._base.create(
            livello=livello,
            sorgente=sorgente,
            messaggio=messaggio,
            dettagli=dettagli,
        )

    async def get_recenti(self, limit: int = 50) -> List[LogEvento]:
        result = await self.session.execute(
            select(LogEvento)
            .order_by(LogEvento.creato_il.desc())
            .limit(limit)
        )
        return result.scalars().all()


# ── Sync versions per Django views ────────────────────────────────────────────

class SyncUtenteRepository:
    def __init__(self, session: Session):
        self._base = SyncRepository(Utente, session)
        self.session = session

    def get_all(self, limit=100, offset=0): return self._base.get_all(limit, offset)
    def count(self): return self._base.count()

    def count_attivi(self):
        return self.session.execute(
            select(func.count()).select_from(Utente).where(Utente.attivo == True)
        ).scalar_one()


class SyncCanaleRepository:
    def __init__(self, session: Session):
        self._base = SyncRepository(Canale, session)
        self.session = session

    def get_all(self, limit=100, offset=0): return self._base.get_all(limit, offset)
    def get_attivi(self):
        return self.session.execute(
            select(Canale).where(Canale.attivo == True)
        ).scalars().all()
    def count(self): return self._base.count()


class SyncMessaggioRepository:
    def __init__(self, session: Session):
        self._base = SyncRepository(Messaggio, session)
        self.session = session

    def get_recenti(self, limit=20):
        return self.session.execute(
            select(Messaggio).order_by(Messaggio.creato_il.desc()).limit(limit)
        ).scalars().all()
    def count(self): return self._base.count()
    def count_pubblicati(self):
        return self.session.execute(
            select(func.count()).select_from(Messaggio).where(Messaggio.pubblicato == True)
        ).scalar_one()


class SyncLogEventoRepository:
    def __init__(self, session: Session):
        self._base = SyncRepository(LogEvento, session)
        self.session = session

    def get_recenti(self, limit=50):
        return self.session.execute(
            select(LogEvento).order_by(LogEvento.creato_il.desc()).limit(limit)
        ).scalars().all()
