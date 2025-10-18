# utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot

from utils.config import LOG_LEVEL
from utils.paths import LOG_FILE_PATH
from utils.telegram_logger import TelegramLogHandler

_telegram_handler: TelegramLogHandler | None = None


def setup_logger(name: str = "medphysbot", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)

    level_name = level.upper()
    if not hasattr(logging, level_name):
        level_name = "INFO"

    if getattr(logger, "_logger_initialized", False):
        return logger

    logger._logger_initialized = True
    logger.setLevel(getattr(logging, level_name))
    logger.propagate = False  # отключаем передачу вверх

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    if _telegram_handler:
        _telegram_handler.setFormatter(formatter)
        logger.addHandler(_telegram_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVEL)
    logger.propagate = False
    return logger


def init_all_loggers(bot: Bot) -> None:
    """
    Инициализация всех логгеров проекта + Telegram-хендлер.
    """
    from utils.config import ENABLE_TELEGRAM_LOGGING, LOG_CHANNEL_ID
    global _telegram_handler

    if ENABLE_TELEGRAM_LOGGING and LOG_CHANNEL_ID != -1:
        _telegram_handler = TelegramLogHandler(
            bot=bot,
            log_channel_id=LOG_CHANNEL_ID,
            batch_size=1000,         # большой буфер для запуска
            flush_interval=30        # автофлеш после старта
        )

    for name in [
        "bot", "topics", "db", "moderation", "relay", "news", "startup",
        "cleanup", "errors", "commands", "status", "thanks", "thanks_db",
        "thanks_words", "sender", "telegram_logger"
    ]:
        setup_logger(name=name, level=LOG_LEVEL)


def start_telegram_loggers():
    """
    Включает автофлеш Telegram-хендлера.
    """
    if _telegram_handler:
        _telegram_handler.auto_flush_enabled = True
        _telegram_handler.start()


async def flush_telegram_loggers():
    """
    Принудительно сбрасывает буфер Telegram-хендлера.
    """
    if _telegram_handler:
        # type: ignore[attr-defined]
        await _telegram_handler._flush()  # noqa



