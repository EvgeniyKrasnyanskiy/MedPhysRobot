# medphysbot.py

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession

# Core utilities (loaded at module level — lightweight, no handler code)
from utils.db import cleanup_old_mappings, init_db
from utils.logger import flush_telegram_loggers, init_all_loggers, start_telegram_loggers
from utils.config import BOT_TOKEN, DEBUG_MODE
from utils.telegram_connect import TELEGRAM_BACKOFF, run_with_network_retry, wait_for_bot_connection
from utils.ttl_storage import TTLMemoryStorage

# ---------------------------------------------------------------------------
# Module-level handle for the periodic cleanup task.
# Kept here (not inside main()) so it survives multiple asyncio.run() calls
# and can be inspected / cancelled explicitly before spawning a replacement.
# ---------------------------------------------------------------------------
_cleanup_task: asyncio.Task | None = None


async def main() -> None:
    # Single logger reference for the lifetime of main().
    # logging.getLogger always returns the same cached object from the registry,
    # so this line is safe to call before and after init_all_loggers().
    logger = logging.getLogger("bot")

    # 1. One-time DB initialisation — outside the retry loop to avoid
    #    re-running expensive migrations on every network hiccup.
    try:
        init_db()
        cleanup_old_mappings(days=2)

        # news_monitor import is deferred to main() below, but cleanup_forwarded_news
        # is needed here before polling starts — import it directly.
        from handlers.news_monitor import cleanup_forwarded_news
        cleanup_forwarded_news(days=7)

        logger.info("[DB] Все старые связи успешно очищены при старте")
    except Exception as e:
        logger.error(f"Ошибка при инициализации БД: {e}")
        return

    # 2. Shared FSM storage — one instance for the whole process lifetime.
    #    TTL=3600 s: abandoned dialogs are evicted after 1 h of inactivity.
    storage = TTLMemoryStorage(ttl=3600, eviction_interval=300)

    while True:
        # ------------------------------------------------------------------
        # 3. Create a fresh aiohttp session and Bot object for each attempt.
        #    A new session is required after each network failure because the
        #    previous one may be in a broken state.
        # ------------------------------------------------------------------
        session = AiohttpSession()
        bot = Bot(
            token=BOT_TOKEN,
            session=session,
            default=DefaultBotProperties(parse_mode="HTML"),
        )

        try:
            # Centralised logger init.  On the first call this creates the
            # TelegramLogHandler; on subsequent calls it only swaps the bot
            # reference so the handler always uses the live session.
            init_all_loggers(bot)

            # 4. Wait until Telegram is reachable.
            await wait_for_bot_connection(bot, logger)

            # 5. Register bot menu commands (with network retry).
            from utils.commands import setup_bot_commands
            async def _setup_commands():
                await setup_bot_commands(bot)
            await run_with_network_retry("Регистрация команд меню бота", _setup_commands, logger)

            # 6. Set up Dispatcher.
            #    Routers are imported here (lazy) so handler modules are only
            #    loaded into memory when polling is actually about to start.
            #    Python caches modules in sys.modules, so subsequent iterations
            #    of the while-loop pay only a dict-lookup cost.
            from handlers import moderation, start, help, relay, news_monitor, status, thanks
            from middlewares.album import AlbumMiddleware

            dp = Dispatcher(storage=storage)
            dp.message.middleware(AlbumMiddleware())
            dp.include_router(moderation.router)
            dp.include_router(start.router)
            dp.include_router(help.router)
            dp.include_router(relay.router)
            dp.include_router(news_monitor.router)
            dp.include_router(status.router)
            dp.include_router(thanks.router)

            # 7. Background tasks — start only once per process.
            global _cleanup_task
            if _cleanup_task is None or _cleanup_task.done():
                async def periodic_cleanup():
                    while True:
                        try:
                            cleanup_old_mappings(days=2)
                            news_monitor.cleanup_forwarded_news(days=7)
                            logger.debug("[DB] Периодическая очистка всех старых связей успешно завершена")
                        except Exception as exc:
                            logger.error(f"[DB] Ошибка автоочисток: {exc}")
                        await asyncio.sleep(86400)

                # Also kick off the TTL eviction loop (safe to call multiple times)
                storage.start_eviction()
                _cleanup_task = asyncio.create_task(periodic_cleanup(), name="periodic_db_cleanup")
            else:
                logger.debug("[STARTUP] periodic_cleanup task already running — skip duplicate")

            # 8. Final log synchronization before starting polling
            await flush_telegram_loggers()
            start_telegram_loggers()

            logger.info(f"Бот запущен в режиме DEBUG: {DEBUG_MODE}")
            logger.info("[STARTUP] Бот полностью готов к работе")

            # 9. Start polling.
            await dp.start_polling(bot, backoff_config=TELEGRAM_BACKOFF)

            # Clean graceful exit (e.g. stop_polling() was called).
            break

        except (KeyboardInterrupt, SystemExit):
            logger.info("Бот остановлен пользователем")
            break
        except Exception as e:
            logger.error(f"Критический сбой polling: {e}. Рестарт через 10 сек...")
            await asyncio.sleep(10)
        finally:
            # Always close the session; the next loop iteration creates a new one.
            await bot.session.close()

    # Graceful shutdown: cancel background tasks and close storage.
    if _cleanup_task and not _cleanup_task.done():
        _cleanup_task.cancel()
        try:
            await _cleanup_task
        except asyncio.CancelledError:
            pass
    await storage.close()


if __name__ == "__main__":
    asyncio.run(main())
