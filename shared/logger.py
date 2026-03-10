"""
shared/logger.py
Logger centralizzato — stesso formato per bot e web panel.
"""
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
from pathlib import Path


class LoggerInfo:
    """Classe per creare logger avanzati con file, console e formatter personalizzati."""

    def __init__(self, name: str = __name__, log_dir: str = "logs", log_file: str = "app.log", level=logging.DEBUG):
        self.name = name
        self.level = level
        
        
        os.makedirs(log_dir, exist_ok=True)
        self.log_path = os.path.join(log_dir, log_file)

        # Crea il logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        self.logger.propagate = False  # evita duplicazione log

        _fmt = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        _datefmt = "%Y-%m-%d %H:%M:%S"

                # Console handler
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        ch.setFormatter(logging.Formatter(_fmt, _datefmt))

                # File handler
        fh = RotatingFileHandler(
            filename=self.log_path,
            maxBytes=5*1024*1024,  # 5 MB
            backupCount=5,
            encoding="utf-8"
             )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter(_fmt, _datefmt))

        if not self.logger.handlers:
            self.logger.addHandler(ch)
            self.logger.addHandler(fh)

    
    def get_logger(self):
        return self.logger

