# utils/telegram_logger.py

import logging
import asyncio
import threading
from aiogram import Bot

class TelegramLogHandler(logging.Handler):
    def __init__(self, bot: Bot, log_channel_id: int, batch_size: int = 10, flush_interval: int = 30):
        super().__init__()
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer = []
        self.buffer_lock = asyncio.Lock()
        self.lock = threading.Lock()
        self._started = False

    def emit(self, record):
        log_entry = self.format(record)
        print(f"[LOGGER] emit: {log_entry}")  # отладка
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._add_to_buffer(log_entry))
        except RuntimeError:
            print("[LOGGER] emit: нет активного event loop — буферим напрямую")
            self.buffer.append(log_entry)

    async def _add_to_buffer(self, entry: str):
        async with self.buffer_lock:
            self.buffer.append(entry)
            if len(self.buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        if not self.buffer:
            print("[LOGGER] flush: буфер пуст — ничего не отправляем")
            return

        text = "\n".join(self.buffer)
        self.buffer.clear()

        MAX_LENGTH = 4000
        chunks = [text[i:i + MAX_LENGTH] for i in range(0, len(text), MAX_LENGTH)]
        print(f"[LOGGER] flush: отправляем {len(chunks)} чанков в Telegram")

        for chunk in chunks:
            try:
                await self.bot.send_message(
                    chat_id=self.log_channel_id,
                    text=f"🧾 <b>Логи:</b>\n<pre>{chunk}</pre>",
                    parse_mode="HTML"
                )
                print("[LOGGER] flush: отправка успешна")
            except Exception as e:
                print(f"[LOGGER] flush: ошибка отправки — {e}")
                import traceback
                traceback.print_exc()

    def start(self):
        if not self._started:
            self._started = True
            print("[LOGGER] start: запускаем автофлеш")
            asyncio.create_task(self._auto_flush_loop())
        else:
            print("[LOGGER] start: уже запущен — пропускаем")

    async def _auto_flush_loop(self):
        while True:
            await asyncio.sleep(self.flush_interval)
            async with self.buffer_lock:
                await self._flush()

