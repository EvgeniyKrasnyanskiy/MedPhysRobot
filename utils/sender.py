# utils/sender.py

from aiogram import Bot
from aiogram.types import Message, MessageEntity
from utils.logger import get_logger

logger = get_logger("sender")
logger.info("[SENDER] sender.py загружен")

MAX_CAPTION = 1024
MAX_TEXT = 4096

def split_text(text: str, limit: int) -> list[str]:
    """Разбивает текст на части по limit символов."""
    return [text[i:i+limit] for i in range(0, len(text), limit)]

def slice_entities(entities: list[MessageEntity] | None, start: int, end: int) -> list[MessageEntity]:
    """Пересчитывает entities для куска текста [start, end)."""
    new_entities = []
    for ent in entities or []:
        ent_start = ent.offset
        ent_end = ent.offset + ent.length

        # полностью внутри куска
        if ent_start >= start and ent_end <= end:
            new_entities.append(
                MessageEntity(
                    type=ent.type,
                    offset=ent_start - start,
                    length=ent.length,
                    url=ent.url,
                    user=ent.user,
                    language=ent.language
                )
            )
        # пересекает границу — обрезаем
        elif ent_start < end and ent_end > start:
            clipped_start = max(ent_start, start)
            clipped_end = min(ent_end, end)
            new_entities.append(
                MessageEntity(
                    type=ent.type,
                    offset=clipped_start - start,
                    length=clipped_end - clipped_start,
                    url=ent.url,
                    user=ent.user,
                    language=ent.language
                )
            )
    return new_entities

async def send_content_to_group(
    message: Message,
    bot: Bot,
    chat_id: int,
    thread_id: int | None = None,
    suffix: str = ""
) -> list[Message]:
    """
    Универсальная пересылка сообщений в группу.
    Длинные подписи (>1024) и тексты (>4096) автоматически режутся.
    Сохраняет entities/caption_entities для форматирования и скрытых ссылок.
    Возвращает список всех отправленных сообщений.
    """
    def add_thread(kwargs: dict):
        if thread_id is not None:
            kwargs["message_thread_id"] = int(thread_id)
        return kwargs

    base_text = (message.caption or message.text or "") + (suffix or "")
    sent_messages: list[Message] = []

    # Фото / Видео / Документы / Аудио / Голос
    if message.photo or message.video or message.document or message.audio or message.voice:
        parts = split_text(base_text, MAX_CAPTION)
        for idx, chunk in enumerate(parts):
            chunk_entities = slice_entities(message.caption_entities, idx*MAX_CAPTION, (idx+1)*MAX_CAPTION)

            if idx == 0:
                if message.photo:
                    sent = await bot.send_photo(
                        chat_id=chat_id,
                        photo=message.photo[-1].file_id,
                        caption=chunk,
                        caption_entities=chunk_entities,
                        **add_thread({})
                    )
                elif message.video:
                    sent = await bot.send_video(
                        chat_id=chat_id,
                        video=message.video.file_id,
                        caption=chunk,
                        caption_entities=chunk_entities,
                        **add_thread({})
                    )
                elif message.document:
                    sent = await bot.send_document(
                        chat_id=chat_id,
                        document=message.document.file_id,
                        caption=chunk,
                        caption_entities=chunk_entities,
                        **add_thread({})
                    )
                elif message.audio:
                    sent = await bot.send_audio(
                        chat_id=chat_id,
                        audio=message.audio.file_id,
                        caption=chunk,
                        caption_entities=chunk_entities,
                        **add_thread({})
                    )
                elif message.voice:
                    sent = await bot.send_voice(
                        chat_id=chat_id,
                        voice=message.voice.file_id,
                        caption=chunk,
                        caption_entities=chunk_entities,
                        **add_thread({})
                    )
                else:
                    sent = None

                if sent:
                    sent_messages.append(sent)

            else:
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=chunk,
                    entities=chunk_entities,
                    **add_thread({})
                )
                sent_messages.append(sent)

    # Чистый текст
    elif message.text:
        parts = split_text(base_text, MAX_TEXT)
        for idx, chunk in enumerate(parts):
            chunk_entities = slice_entities(message.entities, idx*MAX_TEXT, (idx+1)*MAX_TEXT)
            sent = await bot.send_message(
                chat_id=chat_id,
                text=chunk,
                entities=chunk_entities,
                **add_thread({})
            )
            sent_messages.append(sent)

    return sent_messages