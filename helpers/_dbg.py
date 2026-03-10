"""
helper/debug.py
Funzioni di debug condivise tra bot e web panel.
"""
from __future__ import annotations

from datetime import datetime
from shared.logger import get_logger

_logger = get_logger("debug")


def dbg(step: str, logger_name: str = "debug", **kwargs) -> None:
    """
    Stampa un blocco debug strutturato nel terminale.

    Uso:
        from helper.debug import dbg
        dbg("STEP 1 — avvio", testo="ciao", canale_id=42)

    Output:
        [DEBUG 14:32:01.123] ▶ STEP 1 — avvio
                  testo = 'ciao'
                  canale_id = 42
    """
    ts   = datetime.utcnow().strftime("%H:%M:%S.%f")[:-3]
    line = f"[DEBUG {ts}] ▶ {step}"
    for k, v in kwargs.items():
        line += f"\n          {k} = {v!r}"
    print(line, flush=True)
    get_logger(logger_name).debug(line)