# medphysbot.py

from aiogram.client.session.aiohttp import AiohttpSession

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
from utils.telegram_connect import TELEGRAM_BACKOFF, run_with_network_retry, wait_for_bot_connection

# bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

async def main():
    # Определяем логгер в самом начале, чтобы он был доступен для БД и ошибок
    logger = logging.getLogger("bot")
    proxy_url = "http://127.0.0.1:10808"
    bg_tasks_started = False
    
    # 1. Первичная инициализация БД (вне цикла, чтобы не делать при каждом рестарте сети)
    try:
        init_db()
        cleanup_old_mappings(days=2)
        cleanup_forwarded_news(days=7)
        logger.info("[DB] Все старые связи успешно очищены при старте")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return

    while True:
        # 2. Создаем свежую сессию и объект бота
        session = AiohttpSession(proxy=proxy_url)
        bot = Bot(
            token=BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode="HTML")
        )

        try:
            # Централизованная инициализация всех логгеров
            init_all_loggers(bot)
            logger = logging.getLogger("bot")
            
            # 3. Ждем доступности Telegram через прокси
            await wait_for_bot_connection(bot, logger)

            # 4. Регистрация команд (с повторами)
            async def _setup_commands():
                await setup_bot_commands(bot)
            await run_with_network_retry("Регистрация команд меню бота", _setup_commands, logger)

            # 5. Настройка диспетчера
            dp = Dispatcher(storage=MemoryStorage())
            
            # Регистрация роутеров и middleware
            dp.message.middleware(AlbumMiddleware())
            dp.include_router(moderation.router)
            dp.include_router(start.router)
            dp.include_router(help.router)
            dp.include_router(relay.router)
            dp.include_router(news_monitor.router)
            dp.include_router(status.router)
            dp.include_router(thanks.router)

            # 6. Запуск фоновых задач (только ОДИН раз за все время работы процесса)
            if not bg_tasks_started:
                # Определение функции очистки внутри, чтобы она имела доступ к текущему боту
                async def periodic_cleanup():
                    while True:
                        try:
                            cleanup_old_mappings(days=2)
                            cleanup_forwarded_news(days=7)
                            logger.info("[DB] Периодическая очистка всех старых связей успешно завершена")
                        except Exception as exc:
                            logger.error(f"[DB] Ошибка автоочисток: {exc}")
                        await asyncio.sleep(86400)

                await flush_telegram_loggers()
                start_telegram_loggers()
                asyncio.create_task(periodic_cleanup())
                bg_tasks_started = True

            logger.info(f"Бот запущен в режиме DEBUG: {DEBUG_MODE}")
            logger.info("[STARTUP] Бот полностью готов к работе через прокси")

            # 7. Запуск polling
            await dp.start_polling(bot, backoff_config=TELEGRAM_BACKOFF)
            
            # Если polling завершился без ошибки (например, stop_polling), выходим из цикла
            break

        except (KeyboardInterrupt, SystemExit):
            logger.info("Бот остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"Критический сбой polling: {e}. Рестарт через 10 сек...")
            await asyncio.sleep(10)
        finally:
            # ОБЯЗАТЕЛЬНО закрываем сессию перед следующей попыткой
            await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())

