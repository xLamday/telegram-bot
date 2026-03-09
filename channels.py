from fastapi import APIRouter, HTTPException
from typing import List
from ..schemas import ChannelCreate, ChannelOut

router = APIRouter()

# In-memory store (sostituisci con DB reale: Tortoise ORM / SQLAlchemy)
_channels: dict[int, dict] = {}
_next_id = 1


@router.get("/", response_model=List[ChannelOut])
async def list_channels():
    return list(_channels.values())


@router.post("/", response_model=ChannelOut, status_code=201)
async def add_channel(body: ChannelCreate):
    global _next_id
    from datetime import datetime, timezone
    record = {
        "id": _next_id,
        "channel_id": body.channel_id,
        "name": body.name,
        "username": body.username or "",
        "is_active": True,
        "added_at": datetime.now(timezone.utc),
    }
    _channels[_next_id] = record
    _next_id += 1
    return record


@router.patch("/{channel_id}/toggle")
async def toggle_channel(channel_id: int):
    ch = _channels.get(channel_id)
    if not ch:
        raise HTTPException(404, "Canale non trovato")
    ch["is_active"] = not ch["is_active"]
    return {"ok": True, "is_active": ch["is_active"]}


@router.delete("/{channel_id}", status_code=204)
async def delete_channel(channel_id: int):
    if channel_id not in _channels:
        raise HTTPException(404, "Canale non trovato")
    del _channels[channel_id]
