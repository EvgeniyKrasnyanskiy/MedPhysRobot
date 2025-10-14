# utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot
from utils.paths import LOG_FILE_PATH
from utils.telegram_logger import TelegramLogHandler

def setup_logger(
    level: str = "INFO",
    bot: Bot = None,
    enable_telegram_logging: bool = False,
    log_channel_id: int = -1
) -> logging.Logger:
    logger = logging.getLogger()

    # Добавляем Telegram-хендлер, даже если логгер уже настроен
    if getattr(logger, "_logger_initialized", False):
        if bot and enable_telegram_logging and log_channel_id != -1:
            # Проверяем, что Telegram-хендлер ещё не добавлен
            if not any(isinstance(h, TelegramLogHandler) for h in logger.handlers):
                tg_handler = TelegramLogHandler(bot, log_channel_id=log_channel_id, batch_size=10, flush_interval=30)
                tg_handler.setFormatter(logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                ))
                logger.addHandler(tg_handler)
        return logger

    # Первая инициализация
    logger._logger_initialized = True
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

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

    if bot and enable_telegram_logging and log_channel_id != -1:
        tg_handler = TelegramLogHandler(bot, log_channel_id=log_channel_id, batch_size=10, flush_interval=30)
        tg_handler.setFormatter(formatter)
        logger.addHandler(tg_handler)

    return logger


