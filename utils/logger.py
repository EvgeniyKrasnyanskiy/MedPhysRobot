# utils/logger.py

import logging
from logging.handlers import RotatingFileHandler
from utils.paths import LOG_FILE_PATH

def setup_logger(name: str = "med_phys_bot", level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 🔧 Убедимся, что папка logs/ существует
    LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

    file_handler = RotatingFileHandler(LOG_FILE_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger

