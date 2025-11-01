# utils/sender.py

from aiogram import Bot
from aiogram.types import Message
from utils.logger import get_logger

logger = get_logger("sender")
logger.info("[SENDER] sender.py загружен")

MAX_CAPTION = 1024
MAX_TEXT = 4096

def split_text(text: str, limit: int) -> list[str]:
    return [text[i:i+limit] for i in range(0, len(text), limit)]

async def send_content_to_group(
    message: Message,
    bot: Bot,
    chat_id: int,
    thread_id: int | None = None,
    suffix: str = ""
) -> Message | None:
    """
    Универсальная пересылка сообщений в группу.
    Длинные подписи (>1024) и тексты (>4096) автоматически режутся.
    """
    def add_thread(kwargs: dict):
        if thread_id is not None:
            kwargs["message_thread_id"] = int(thread_id)
        return kwargs

    base_text = (message.caption or message.text or "") + (suffix or "")

    sent = None

    # Фото / Видео / Документы / Аудио / Голос
    if message.photo or message.video or message.document or message.audio or message.voice:
        parts = split_text(base_text, MAX_CAPTION)
        caption = parts[0] if parts else None
        rest = parts[1:] if len(parts) > 1 else []

        if message.photo:
            sent = await bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=caption, **add_thread({}))
        elif message.video:
            sent = await bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=caption, **add_thread({}))
        elif message.document:
            sent = await bot.send_document(chat_id=chat_id, document=message.document.file_id, caption=caption, **add_thread({}))
        elif message.audio:
            sent = await bot.send_audio(chat_id=chat_id, audio=message.audio.file_id, caption=caption, **add_thread({}))
        elif message.voice:
            sent = await bot.send_voice(chat_id=chat_id, voice=message.voice.file_id, caption=caption, **add_thread({}))

        # Остаток текста отдельными сообщениями
        for chunk in rest:
            await bot.send_message(chat_id=chat_id, text=chunk, **add_thread({}))

    # Чистый текст
    elif message.text:
        parts = split_text(base_text, MAX_TEXT)
        for idx, chunk in enumerate(parts):
            sent = await bot.send_message(chat_id=chat_id, text=chunk, **add_thread({}))

    return sent