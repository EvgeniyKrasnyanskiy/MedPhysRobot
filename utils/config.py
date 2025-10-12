# utils/config.py

import os
from dotenv import load_dotenv
from utils.logger import setup_logger

load_dotenv()

def get_env_var(name: str, cast_type=str, required=True, default=None):
    value = os.getenv(name, default)
    if required and value is None:
        logger.error(f"Переменная окружения '{name}' не задана")
        return None
    try:
        return cast_type(value)
    except Exception as e:
        logger.error(f"Ошибка преобразования '{name}' в {cast_type.__name__}: {e}")
        return default

# Загружаем режимы
DEBUG_MODE = get_env_var("DEBUG_MODE", lambda x: x.lower() == "true", required=False, default=False)
LOG_LEVEL = get_env_var("LOG_LEVEL", str, required=False, default="INFO")

# Настройка логгера с уровнем из .env
logger = setup_logger("config", level=LOG_LEVEL)

# Основные переменные
BOT_TOKEN = get_env_var("BOT_TOKEN")
SOURCE_CHANNEL_ID = get_env_var("SOURCE_CHANNEL_ID", int)
TARGET_GROUP_ID = get_env_var("TARGET_GROUP_ID", int)
RELAY_GROUP_ID = get_env_var("RELAY_GROUP_ID", int)
TARGET_TOPIC_ID = get_env_var("TARGET_TOPIC_ID", int)

LOG_FILE = os.getenv("LOG_FILE", "medphysbot.log")  # fallback на medphysbot.log

# Путь к базе данных
DB_PATH = get_env_var("DB_PATH", str, required=False, default=os.path.join("data", "relay.db"))

