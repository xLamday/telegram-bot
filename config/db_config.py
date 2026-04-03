"""
Database settings and configuration.
"""
import os
from dotenv import load_dotenv

load_dotenv()
class DatabaseConfig:
    HOST = os.getenv("DB_HOST")
    PORT = os.getenv("DB_PORT")
    NAME = os.getenv("DB_NAME")
    USER = os.getenv("DB_USER")
    PASSWORD = os.getenv("DB_PASSWORD")