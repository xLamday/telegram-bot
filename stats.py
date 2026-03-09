from fastapi import APIRouter
from ..schemas import StatsOut
import time

router = APIRouter()
_start_time = time.time()


@router.get("/", response_model=StatsOut)
async def get_stats():
    from .channels import _channels
    from .messages import _messages

    published = sum(1 for m in _messages.values() if m["status"] == "published")
    failed = sum(1 for m in _messages.values() if m["status"] == "failed")

    return StatsOut(
        channels_active=sum(1 for c in _channels.values() if c["is_active"]),
        messages_total=len(_messages),
        messages_published=published,
        messages_failed=failed,
        bot_uptime_seconds=round(time.time() - _start_time, 1),
    )
