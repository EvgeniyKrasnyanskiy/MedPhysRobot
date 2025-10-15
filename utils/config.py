# utils/config.py
import logging
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
logger = setup_logger(
    level=LOG_LEVEL,
    bot=None,
    enable_telegram_logging=False,
    log_channel_id=-1
)
logger = logging.getLogger("config")


# Основные переменные
BOT_TOKEN = get_env_var("BOT_TOKEN")
MEDPHYSPRO_CHANNEL_ID = get_env_var("MEDPHYSPRO_CHANNEL_ID", int)
MEDPHYSPRO_GROUP_ID = get_env_var("MEDPHYSPRO_GROUP_ID", int)
ADMIN_GROUP_ID = get_env_var("ADMIN_GROUP_ID", int)
MEDPHYSPRO_GROUP_TOPIC_ID = get_env_var("MEDPHYSPRO_GROUP_TOPIC_ID", int)

LOG_FILE = os.getenv("LOG_FILE", "medphysbot.log")  # fallback на medphysbot.log
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "-1"))
ENABLE_TELEGRAM_LOGGING = os.getenv("ENABLE_TELEGRAM_LOGGING", "False").lower() == "true"

# Путь к базе данных
DB_PATH = get_env_var("DB_PATH", str, required=False, default=os.path.join("data", "relay.db"))

