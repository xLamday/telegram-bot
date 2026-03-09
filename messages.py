from fastapi import APIRouter, HTTPException
from typing import List
from datetime import datetime, timezone
from ..schemas import MessagePublish, MessageOut
import os

router = APIRouter()

_messages: dict[int, dict] = {}
_next_id = 1


async def _send_telegram_message(channel_id: int, text: str) -> int:
    """
    Invia il messaggio al canale Telegram via Bot API.
    Restituisce il telegram_message_id oppure lancia eccezione.
    """
    import httpx
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN non configurato")

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(url, json={
            "chat_id": channel_id,
            "text": text,
            "parse_mode": "HTML",
        })
        data = resp.json()
        if not data.get("ok"):
            raise RuntimeError(data.get("description", "Errore Telegram"))
        return data["result"]["message_id"]


@router.get("/", response_model=List[MessageOut])
async def list_messages():
    return list(_messages.values())


@router.post("/publish")
async def publish_message(body: MessagePublish):
    global _next_id
    record = {
        "id": _next_id,
        "channel_id": body.channel_id,
        "content": body.content,
        "status": "pending",
        "telegram_message_id": None,
        "published_at": None,
        "created_at": datetime.now(timezone.utc),
    }
    _messages[_next_id] = record
    _next_id += 1

    try:
        tg_id = await _send_telegram_message(body.channel_id, body.content)
        record["status"] = "published"
        record["telegram_message_id"] = tg_id
        record["published_at"] = datetime.now(timezone.utc)
        return {"ok": True, "telegram_message_id": tg_id}
    except Exception as e:
        record["status"] = "failed"
        return {"ok": False, "error": str(e)}


@router.delete("/{message_id}", status_code=204)
async def delete_message(message_id: int):
    if message_id not in _messages:
        raise HTTPException(404, "Messaggio non trovato")
    del _messages[message_id]
