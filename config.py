"""
Configuration module for Health Bot.
Handles all configuration settings, API keys, and environment variables.
"""

import os
import shutil
import sqlite3
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file in the same directory
BASE_DIR_CONFIG = Path(__file__).resolve().parent
load_dotenv(BASE_DIR_CONFIG / ".env", override=True)

# Base directories
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
USERS_DIR = DATA_DIR / "users"
REPORTS_DIR = DATA_DIR / "reports"
BACKUPS_DIR = DATA_DIR / "backups"

# Ensure directories exist
for directory in [DATA_DIR, USERS_DIR, REPORTS_DIR, BACKUPS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database. SQLite lives under data/ so the Docker volume keeps it across rebuilds.
DEFAULT_DB_PATH = DATA_DIR / "health_bot.db"
LEGACY_DB_PATH = BASE_DIR / "health_bot.db"


def sqlite_path_from_url(url: str) -> Optional[Path]:
    """Return the file path for a SQLite URL, or None for other databases."""
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        return None
    raw = url[len(prefix):]
    if raw in ("", ":memory:"):
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def sqlite_url_for(path: Path) -> str:
    """Build a SQLite URL for an absolute filesystem path."""
    return "sqlite:///" + path.resolve().as_posix()


def _migrate_legacy_sqlite(target: Path) -> None:
    """Copy the old database from the image filesystem into the persisted data directory."""
    legacy = LEGACY_DB_PATH.resolve()
    destination = target.resolve()
    if destination.exists() or not legacy.exists() or legacy == destination:
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        with sqlite3.connect(legacy) as source, sqlite3.connect(destination) as copied:
            source.backup(copied)
    except sqlite3.Error:
        shutil.copy2(legacy, destination)


def resolve_database_url() -> str:
    """Use data/health_bot.db unless another database URL is configured."""
    env_url = os.getenv("DATABASE_URL", "").strip()
    if not env_url:
        _migrate_legacy_sqlite(DEFAULT_DB_PATH)
        return sqlite_url_for(DEFAULT_DB_PATH)

    configured_path = sqlite_path_from_url(env_url)
    if configured_path is None:
        return env_url
    if configured_path == LEGACY_DB_PATH.resolve():
        _migrate_legacy_sqlite(DEFAULT_DB_PATH)
        return sqlite_url_for(DEFAULT_DB_PATH)
    return env_url


DATABASE_URL = resolve_database_url()
SQLITE_DB_PATH = sqlite_path_from_url(DATABASE_URL)

# Telegram Bot
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# DeepSeek API
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
DEEPSEEK_CHAT_MODEL = os.getenv("DEEPSEEK_CHAT_MODEL", "deepseek-chat")
DEEPSEEK_REASONER_MODEL = os.getenv("DEEPSEEK_REASONER_MODEL", "deepseek-reasoner")
DEEPSEEK_CODER_MODEL = os.getenv("DEEPSEEK_CODER_MODEL", "deepseek-coder")

# Gemini API (Google)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Samsung Health (optional)
SAMSUNG_HEALTH_API_KEY = os.getenv("SAMSUNG_HEALTH_API_KEY", "")
SAMSUNG_HEALTH_USER_ID = os.getenv("SAMSUNG_HEALTH_USER_ID", "")

# FoodScanner API
FOODSCANNER_API_URL = os.getenv("FOODSCANNER_API_URL", "http://localhost:8000")

# Application settings
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
LANGUAGE = os.getenv("LANGUAGE", "ru")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = BASE_DIR / "health_bot.log"

# Scheduler settings
REMINDER_CHECK_INTERVAL = int(os.getenv("REMINDER_CHECK_INTERVAL", "60"))  # seconds

class Config:
    """Configuration manager for the Health Bot."""

    def __init__(self):
        self.BASE_DIR = BASE_DIR
        self.DATA_DIR = DATA_DIR
        self.USERS_DIR = USERS_DIR
        self.REPORTS_DIR = REPORTS_DIR
        self.BACKUPS_DIR = BACKUPS_DIR
        self.telegram_bot_token = TELEGRAM_BOT_TOKEN
        self.deepseek_api_key = DEEPSEEK_API_KEY
        self.deepseek_base_url = DEEPSEEK_BASE_URL
        self.deepseek_chat_model = DEEPSEEK_CHAT_MODEL
        self.deepseek_reasoner_model = DEEPSEEK_REASONER_MODEL
        self.deepseek_coder_model = DEEPSEEK_CODER_MODEL
        self.gemini_api_key = GEMINI_API_KEY
        self.gemini_model = GEMINI_MODEL
        self.samsung_health_api_key = SAMSUNG_HEALTH_API_KEY
        self.samsung_health_user_id = SAMSUNG_HEALTH_USER_ID
        self.foodscanner_api_url = FOODSCANNER_API_URL
        self.database_url = DATABASE_URL
        self.sqlite_db_path = SQLITE_DB_PATH
        self.timezone = TIMEZONE
        self.language = LANGUAGE
        self.log_level = LOG_LEVEL
        self.log_file = LOG_FILE

    def validate(self) -> tuple[bool, list[str]]:
        """Validate required configuration settings."""
        errors = []
        
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        
        # DeepSeek and Gemini are optional but recommended
        if not self.deepseek_api_key:
            errors.append("DEEPSEEK_API_KEY is not set (AI features will be limited)")
        
        if not self.gemini_api_key:
            errors.append("GEMINI_API_KEY is not set (image recognition will not work)")
        
        return len(errors) == 0, errors
    
    def is_production_ready(self) -> bool:
        """Check if all required configuration keys are set."""
        required = [
            self.telegram_bot_token,
            self.gemini_api_key
        ]
        return all(required)


config = Config()
