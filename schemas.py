from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ChannelCreate(BaseModel):
    channel_id: int
    name: str
    username: Optional[str] = ""


class ChannelOut(BaseModel):
    id: int
    channel_id: int
    name: str
    username: str
    is_active: bool
    added_at: datetime

    class Config:
        from_attributes = True


class MessagePublish(BaseModel):
    channel_id: int
    content: str


class MessageOut(BaseModel):
    id: int
    channel_id: int
    content: str
    status: str
    telegram_message_id: Optional[int] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class StatsOut(BaseModel):
    channels_active: int
    messages_total: int
    messages_published: int
    messages_failed: int
    bot_uptime_seconds: Optional[float] = None
