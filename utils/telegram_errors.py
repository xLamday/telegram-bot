from telegram.error import NetworkError
from telegram.error import BadRequest, Forbidden, RetryAfter, TelegramError

class TelegramErrorClassificatore:
    """
    Classifica gli errori Telegram basandosi sul messaggio ufficiale dell'API.
    I messaggi sono stabili nell'API di Telegram (snake_case = error code interno).
    """

    # Errori che indicano chat permanentemente irraggiungibile
    CHAT_UNREACHABLE = frozenset({
        "chat not found",
        "channel not found",
        "supergroup not found",
        "peer_id_invalid",
        "chat_id_invalid",
        "user is deactivated",
        "bot was blocked by the user",
        "bot was kicked from the group chat",
        "bot was kicked from the supergroup chat",
        "bot is not a member of the channel chat",
        "bot is not a member of the supergroup",
        "bot is not a member of the group",
        "have no rights to send a message",
    })

    CHAT_RESTRICTED = frozenset({
        "chat_restricted",
    })

    # Errori che indicano che il messaggio specifico non esiste più
    MESSAGE_NOT_FOUND = frozenset({
        "message to delete not found",
        "message to copy not found",
        "message to forward not found",
        "message not found",
        "message can't be deleted",
        "message can't be deleted for everyone",
    })

    # Errori transitori → ha senso ritentare
    TRANSIENT = frozenset({
        "bad gateway",
        "service unavailable",
        "gateway timeout",
        "internal server error",
    })

    @classmethod
    def _normalize(cls, error: TelegramError) -> str:
        return str(error).lower().strip()

    @classmethod
    def _matches(cls, error: TelegramError, phrase_set: frozenset) -> bool:
        msg = cls._normalize(error)
        return any(phrase in msg for phrase in phrase_set)

    @classmethod
    def è_chat_irraggiungibile(cls, error: TelegramError) -> bool:
        """Controlla i seguenti casi in cui la chat non è raggiungibile:
        - è inesistente
        - bot bannato
        - canale eliminato 
        
        Operazione eseguita: → rimozione dal DB."""
        if isinstance(error, Forbidden):
            return True
        if isinstance(error, BadRequest):
            return cls._matches(error, cls.CHAT_UNREACHABLE)
        return False

    @classmethod
    def è_messaggio_non_trovato(cls, error: TelegramError) -> bool:
        """Controlla se il messaggio specifico non è più esistente 
        
        - Operazione eseguita: → post eliminato."""
        if isinstance(error, BadRequest):
            return cls._matches(error, cls.MESSAGE_NOT_FOUND)
        return False

    @classmethod
    def è_chat_restricted(cls, error: TelegramError) -> bool:
        """Controlla se c'è un errore di restrizione del chat (temporaneo, ma non transitorio)"""
        if isinstance(error, BadRequest):
            return cls._matches(error, cls.CHAT_RESTRICTED)
        return False

    @classmethod
    def è_transitorio(cls, error: TelegramError) -> bool:
        """Controlla se c'è un errore transitorio (temporaneo) lato Telegram"""
        if isinstance(error, (BadRequest, Forbidden)):
            return cls._matches(error, cls.TRANSIENT)
        return isinstance(error, NetworkError) or cls._matches(error, cls.TRANSIENT)

    @classmethod
    def è_errore_generico(cls, error: TelegramError) -> bool:
        """True se l'errore è un TelegramError generico non classificabile. Utile per separare gli errori noti da quelli inaspettati nel logging."""
        return not any([
            cls.è_chat_irraggiungibile(error),
            cls.è_messaggio_non_trovato(error),
            cls.è_chat_restricted(error),
            cls.è_transitorio(error),
            isinstance(error, RetryAfter),
        ])

    @classmethod
    def classifica(cls, error: TelegramError) -> str:
        """
        Restituisce una stringa che descrive la categoria dell'errore.
        Utile per logging.
        """
        if isinstance(error, Forbidden):
            return "chat_unreachable:no_rights"
        if cls.è_chat_irraggiungibile(error):
            return "chat_unreachable:notfound"
        if cls.è_messaggio_non_trovato(error):
            return "message_not_found"
        if cls.è_chat_restricted(error):
            return "chat_restricted"
        if cls.è_transitorio(error):
            return "transitorio"
        if isinstance(error, RetryAfter):
            return "rate_limited"
        return "unknown"