# utils/telegram_connect.py
# Ожидание доступности Telegram при нестабильном прокси / сети.

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import TypeVar

import aiohttp
from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest, TelegramNetworkError, TelegramUnauthorizedError
from aiogram.utils.backoff import Backoff, BackoffConfig

from utils.config import TELEGRAM_BACKOFF_MAX_SEC, TELEGRAM_BACKOFF_MIN_SEC

T = TypeVar("T")

# Общий backoff: ожидание перед стартом, повтор set_my_commands и интервалы между getUpdates при сбоях
TELEGRAM_BACKOFF = BackoffConfig(
    min_delay=TELEGRAM_BACKOFF_MIN_SEC,
    max_delay=TELEGRAM_BACKOFF_MAX_SEC,
    factor=1.35,
    jitter=0.12,
)


def _is_transient_network_error(exc: BaseException) -> bool:
    if isinstance(exc, (asyncio.CancelledError, KeyboardInterrupt, SystemExit)):
        return False
    if isinstance(exc, TelegramUnauthorizedError):
        return False
    if isinstance(exc, TelegramBadRequest):
        return False
    if isinstance(exc, TelegramNetworkError):
        return True
    if isinstance(exc, aiohttp.ClientError):
        return True
    if isinstance(exc, (asyncio.TimeoutError, TimeoutError, ConnectionError)):
        return True
    return False


async def wait_for_bot_connection(bot: Bot, logger: logging.Logger) -> None:
    """Повторяет get_me до успеха — тот же запрос, что и bot.me() перед polling."""
    backoff = Backoff(config=TELEGRAM_BACKOFF)
    failed_attempts = 0
    while True:
        try:
            await bot.get_me()
            if failed_attempts:
                logger.info(
                    "Связь с Telegram восстановлена после %d неудачных попыток", failed_attempts
                )
            return
        except Exception as e:
            if not _is_transient_network_error(e):
                raise
            failed_attempts += 1
            logger.warning(
                "Нет связи с Telegram (%s: %s). Повтор через %.1f с (попытка %d)...",
                type(e).__name__,
                e,
                backoff.next_delay,
                failed_attempts,
            )
            await backoff.asleep()


async def run_with_network_retry(
    op_label: str,
    factory: Callable[[], Awaitable[T]],
    logger: logging.Logger,
) -> T:
    """Выполняет async-операцию с повтором при сетевых сбоях."""
    backoff = Backoff(config=TELEGRAM_BACKOFF)
    while True:
        try:
            return await factory()
        except Exception as e:
            if not _is_transient_network_error(e):
                raise
            logger.warning(
                "%s: временная ошибка сети (%s: %s). Повтор через %.1f с...",
                op_label,
                type(e).__name__,
                e,
                backoff.next_delay,
            )
            await backoff.asleep()
