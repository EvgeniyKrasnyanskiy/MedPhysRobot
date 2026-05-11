# utils/telegram_logger.py

import logging
import asyncio
from collections import deque
from aiogram import Bot

from utils.config import DEBUG_MODE

logger = logging.getLogger("telegram_logger")
if DEBUG_MODE:
    logger.info("[TELEGRAM_LOGGER] telegram_logger.py загружен")


class TelegramLogHandler(logging.Handler):
    def __init__(
        self,
        bot: Bot,
        log_channel_id: int,
        batch_size: int = 200,
        flush_interval: int = 30,
        max_buffer_size: int = 500,
    ):
        super().__init__()
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        # deque with maxlen caps memory usage: oldest entries are auto-dropped on overflow
        self.buffer: deque[str] = deque(maxlen=max_buffer_size)
        self.buffer_lock = asyncio.Lock()
        self._started = False
        self.auto_flush_enabled = False  # автофлеш отключён до старта

    def emit(self, record):
        log_entry = self.format(record)
        if DEBUG_MODE:
            print(f"[LOGGER] emit: {log_entry}")
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._add_to_buffer(log_entry))
        except RuntimeError:
            if DEBUG_MODE:
                print("[LOGGER] emit: нет активного event loop — буферим напрямую")
            self.buffer.append(log_entry)

    async def _add_to_buffer(self, entry: str):
        async with self.buffer_lock:
            # deque auto-drops the oldest entry when maxlen is reached
            self.buffer.append(entry)
            if self.auto_flush_enabled and len(self.buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        if not self.buffer:
            if DEBUG_MODE:
                print("[LOGGER] flush: буфер пуст — ничего не отправляем")
            return

        # Snapshot and clear atomically; deque is mutable so we copy first
        entries = list(self.buffer)
        self.buffer.clear()
        text = "\n".join(entries)

        max_length = 4000
        chunks = [text[i:i + max_length] for i in range(0, len(text), max_length)]
        if DEBUG_MODE:
            print(f"[LOGGER] flush: отправляем {len(chunks)} чанков в Telegram")

        for chunk in chunks:
            try:
                # Add [MedPhysBot] prefix to each chunk's header
                await self.bot.send_message(
                    chat_id=self.log_channel_id,
                    text=f"🧾 <b>[MedPhysBot] Логи:</b>\n<pre>{chunk}</pre>",
                    parse_mode="HTML"
                )
                if DEBUG_MODE:
                    print("[LOGGER] flush: отправка успешна")
            except Exception as e:
                if DEBUG_MODE:
                    print(f"[LOGGER] flush: ошибка отправки — {e}")
                    import traceback
                    traceback.print_exc()

    def flush(self):
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._flush())
        except RuntimeError:
            pass

    def start(self):
        if not self._started:
            self._started = True
            if DEBUG_MODE:
                print("[LOGGER] start: запускаем автофлеш")
            asyncio.create_task(self._auto_flush_loop())

    async def _auto_flush_loop(self):
        while True:
            await asyncio.sleep(self.flush_interval)
            if self.auto_flush_enabled:
                async with self.buffer_lock:
                    await self._flush()
