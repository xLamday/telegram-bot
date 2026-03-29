# utils/__init__.py
from utils.rate_limiter import RateLimiter
from utils.telegram_errors import TelegramErrorClassificatore as TEC

rate_limiter = RateLimiter()  # ← istanza condivisa Rate limiter
tec = TEC() # ← istanza condivisa TEC (TelegramErrorClassificatore)