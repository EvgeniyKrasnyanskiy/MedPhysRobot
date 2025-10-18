# utils/config.py

import os
from dotenv import load_dotenv

load_dotenv()

def resolve_bool_env(var_name: str, default: bool = False) -> bool:
    """
    Безопасно извлекает булеву переменную из .env.
    Поддерживает значения: true/false, 1/0, yes/no (регистр не важен).
    """
    raw = os.getenv(var_name)
    if raw is None:
        return default
    value = raw.strip().lower()
    if value in ("true", "1", "yes"):
        return True
    elif value in ("false", "0", "no"):
        return False
    else:
        from utils.logger import get_logger
        logger = get_logger("config")
        logger.warning(f"[CONFIG] Некорректное булево значение {var_name}={raw!r} — используется default={default}")
        return default

def resolve_int_env(
    var_name: str,
    *,
    min_value: int = 1,
    default: int | None = None,
    allow_equal: bool = False
) -> int | None:
    """
    Безопасно извлекает числовое значение из .env.
    Возвращает None, если значение отсутствует, некорректно или меньше (или меньше/равно) min_value.
    """
    raw = os.getenv(var_name)
    try:
        if not raw or str(raw).strip() in ("", "0"):
            return default
        value = int(raw)
        if (not allow_equal and value <= min_value) or (allow_equal and value < min_value):
            from utils.logger import get_logger
            logger = get_logger("config")
            logger.warning(
                f"[CONFIG] Значение {var_name}={value} не удовлетворяет порогу "
                f"({'<=' if not allow_equal else '<'} {min_value}) — игнорируется"
            )
            return default
        return value
    except ValueError:
        from utils.logger import get_logger
        logger = get_logger("config")
        logger.warning(f"[CONFIG] Переменная {var_name} содержит нечисловое значение: {raw}")
        return default

def get_env_var(name: str, cast_type=str, required=True, default=None):
    value = os.getenv(name, default)
    if required and value is None:
        from utils.logger import get_logger
        logger = get_logger("config")
        logger.error(f"Переменная окружения '{name}' не задана")
        return None
    try:
        return cast_type(value)
    except Exception as e:
        from utils.logger import get_logger
        logger = get_logger("config")
        logger.error(f"Ошибка преобразования '{name}' в {cast_type.__name__}: {e}")
        return default

# Загружаем режимы
DEBUG_MODE = resolve_bool_env("DEBUG_MODE")
ENABLE_TELEGRAM_LOGGING = resolve_bool_env("ENABLE_TELEGRAM_LOGGING")
LOG_LEVEL = get_env_var("LOG_LEVEL", str, required=False, default="INFO")

# Основные переменные
BOT_TOKEN = get_env_var("BOT_TOKEN")
MEDPHYSPRO_CHANNEL_USERNAME = os.getenv("MEDPHYSPRO_CHANNEL_USERNAME", "MedPhysProChannel")
MEDPHYSPRO_CHANNEL_ID = get_env_var("MEDPHYSPRO_CHANNEL_ID", int)

MEDPHYSPRO_GROUP_ID = get_env_var("MEDPHYSPRO_GROUP_ID", int)
ADMIN_GROUP_ID = get_env_var("ADMIN_GROUP_ID", int)
MEDPHYSPRO_GROUP_TOPIC_ID = resolve_int_env("MEDPHYSPRO_GROUP_TOPIC_ID", min_value=0)

LOG_FILE = get_env_var("LOG_FILE", str, required=False, default="medphysbot.log")
LOG_CHANNEL_ID = resolve_int_env("LOG_CHANNEL_ID", min_value=-10**13, default=-1)

# Путь к базе данных
DB_PATH = get_env_var("DB_PATH", str, required=False, default=os.path.join("data", "medphysbot.db"))
