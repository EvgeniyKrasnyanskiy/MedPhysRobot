# medphysbot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from utils.db import init_db, cleanup_old_mappings

from handlers import start, relay, news_monitor, status, moderation
from utils.commands import setup_bot_commands
from handlers import help
from middlewares.album import AlbumMiddleware
from handlers import thanks

from utils.logger import setup_logger
from utils.config import BOT_TOKEN, DEBUG_MODE, LOG_LEVEL, ENABLE_TELEGRAM_LOGGING, LOG_CHANNEL_ID

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# Инициализация root-логгера
setup_logger(
    level=LOG_LEVEL,
    bot=bot,
    enable_telegram_logging=ENABLE_TELEGRAM_LOGGING,
    log_channel_id=LOG_CHANNEL_ID
)

logger = logging.getLogger("bot")  # можно использовать именованный логгер

async def main():
    try:
        init_db()
        cleanup_old_mappings(days=2)
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return

    # Фоновая задача: автоочистка каждые 24 часа
    async def periodic_cleanup():
        while True:
            try:
                cleanup_old_mappings(days=2)
                logger.info("[DB] Автоочистка завершена")
            except Exception as e:
                logger.error(f"[DB] Ошибка автоочистки: {e}")
            await asyncio.sleep(86400)  # 24 часа

    asyncio.create_task(periodic_cleanup())

    # Запускаем автофлеш Telegram-хендлера (внутри активного event loop)
    def get_all_handlers(logger):
        handlers = list(logger.handlers)
        if logger.propagate and logger.parent:
            handlers += get_all_handlers(logger.parent)
        return handlers

    for handler in get_all_handlers(logging.getLogger("bot")):
        if hasattr(handler, "start"):
            handler.start()

    await setup_bot_commands(bot)
    dp = Dispatcher(storage=MemoryStorage())

    dp.include_router(moderation.router)
    dp.message.middleware(AlbumMiddleware())
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(relay.router)
    dp.include_router(news_monitor.router)
    dp.include_router(status.router)
    dp.include_router(thanks.router)

    # Принудительная отправка буфера перед polling
    for handler in logger.handlers:
        if hasattr(handler, "_flush"):
            await handler._flush()

    logger.info("Бот готов к работе")
    logger.info(f"Бот запущен в режиме DEBUG: {DEBUG_MODE}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

