# medphysbot.py

import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
# from aiogram.types import BotCommand
from aiogram.client.default import DefaultBotProperties

from utils.config import BOT_TOKEN, DEBUG_MODE, LOG_LEVEL
from utils.logger import setup_logger
from utils.db import init_db

from handlers import start, relay, news_monitor, status, moderation
from utils.commands import setup_bot_commands
from handlers import help
from middlewares.album import AlbumMiddleware

logger = setup_logger("bot", level=LOG_LEVEL)

async def main():
    # Инициализация базы данных
    try:
        init_db()
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return

    # Создание бота и диспетчера
    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await setup_bot_commands(bot)
    dp = Dispatcher(storage=MemoryStorage())

    # Подключение всех роутеров
    dp.include_router(moderation.router)
    dp.message.middleware(AlbumMiddleware())
    dp.include_router(start.router)
    dp.include_router(help.router)
    dp.include_router(relay.router)
    dp.include_router(news_monitor.router)
    dp.include_router(status.router)

    logger.info("Бот готов к работе")
    logger.info(f"Бот запущен в режиме DEBUG: {DEBUG_MODE}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
