# medphysbot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties

from handlers.news_monitor import cleanup_forwarded_news
from utils.db import init_db, cleanup_old_mappings

from handlers import start, relay, news_monitor, status, moderation, help, thanks
from middlewares.album import AlbumMiddleware
from utils.commands import setup_bot_commands

from utils.logger import init_all_loggers, start_telegram_loggers, flush_telegram_loggers
from utils.config import BOT_TOKEN, DEBUG_MODE

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

# Централизованная инициализация всех логгеров
init_all_loggers(bot)
logger = logging.getLogger("bot")


async def main():
    try:
        init_db()
        cleanup_old_mappings(days=2)
        cleanup_forwarded_news(days=7)
        logger.info("[DB] Все старые связи успешно очищены при запуске бота")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return

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

    # Фоновая задача: автоочистка каждые 24 часа
    async def periodic_cleanup():
        while True:
            try:
                cleanup_old_mappings(days=2)
                cleanup_forwarded_news(days=7)
                logger.info("[DB] Периодическая очистка всех старых связей успешно завершена")
            except Exception as e:
                logger.error(f"[DB] Ошибка автоочисток: {e}")
            await asyncio.sleep(86400)

    # Принудительный сброс буфера Telegram-хендлера
    await flush_telegram_loggers()

    # Включаем автофлеш и запускаем фоновую задачу
    start_telegram_loggers()
    asyncio.create_task(periodic_cleanup())

    # Финальные логи запуска
    await asyncio.sleep(0.1)  # дать автоочистке шанс залогировать
    logger.info(f"Бот запущен в режиме DEBUG: {DEBUG_MODE}")
    logger.info("[STARTUP] Бот полностью готов")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

