# utils/sender.py

from aiogram import Bot
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import Message, MessageEntity, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio, InputMediaAnimation
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
    logger.info(f"[SENDER] send_content_to_group: type={message.content_type}, chat_id={chat_id}, thread_id={thread_id}, suffix_len={len(suffix)}")

    def add_thread(kwargs: dict):
        if thread_id is not None:
            kwargs["message_thread_id"] = int(thread_id)
        return kwargs

    base_text = (message.caption or message.text or "") + (suffix or "")
    sent_messages: list[Message] = []
    has_media = bool(message.photo or message.video or message.document or message.audio or message.voice or message.animation or message.sticker or message.video_note)

    try:
        # Добавлено: Проверка на альбом (media group)
        if message.media_group_id:
            logger.info(f"[SENDER] Обнаружен альбом: media_group_id={message.media_group_id}")
            # Для альбомов используем forward_message как fallback, т.к. разбиение не подходит
            sent = await bot.forward_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                **add_thread({})
            )
            sent_messages.append(sent)
            if suffix:
                extra = await bot.send_message(chat_id=chat_id, text=suffix, **add_thread({}))
                sent_messages.append(extra)
            return sent_messages

        # Оптимизированная отправка для коротких сообщений
        limit = MAX_CAPTION if has_media else MAX_TEXT
        if len(base_text) <= limit and not message.poll and not message.media_group_id:
            # Для медиа: используем copy_message с caption_entities
            if has_media:
                sent = await bot.copy_message(
                    chat_id=chat_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id,
                    caption=base_text,
                    caption_entities=message.caption_entities,  # ✅ Сохраняем ссылки/форматирование!
                    parse_mode=None,
                    **add_thread({})
                )
                sent_messages.append(sent)
                logger.info("[SENDER] Использован copy_message (media)")
                return sent_messages
            
            # Для текста: copy_message не может менять текст, используем send_message
            elif message.text:
                sent = await bot.send_message(
                    chat_id=chat_id,
                    text=base_text,
                    entities=message.entities,  # ✅ Сохраняем ссылки/форматирование!
                    parse_mode=None,
                    **add_thread({})
                )
                sent_messages.append(sent)
                logger.info("[SENDER] Использован send_message (text)")
                return sent_messages

    except TelegramBadRequest as e:
        logger.warning(f"[SENDER] copy_message failed: {e}, fallback на manual")

    # Manual для длинных или специальных
    try:
        if has_media:
            parts = split_text(base_text, MAX_CAPTION)
            entities = message.caption_entities or message.entities or []
            for idx, chunk in enumerate(parts):
                chunk_entities = slice_entities(entities, idx * MAX_CAPTION, (idx + 1) * MAX_CAPTION)
                kwargs = add_thread({"caption": chunk, "caption_entities": chunk_entities})

                if idx == 0:
                    if message.photo:
                        sent = await bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, **kwargs)
                    elif message.video:
                        sent = await bot.send_video(chat_id=chat_id, video=message.video.file_id, **kwargs)
                    elif message.document:
                        sent = await bot.send_document(chat_id=chat_id, document=message.document.file_id, **kwargs)
                    elif message.audio:
                        sent = await bot.send_audio(chat_id=chat_id, audio=message.audio.file_id, **kwargs)
                    elif message.voice:
                        sent = await bot.send_voice(chat_id=chat_id, voice=message.voice.file_id, **kwargs)
                    elif message.animation:
                        sent = await bot.send_animation(chat_id=chat_id, animation=message.animation.file_id, **kwargs)
                    elif message.sticker:
                        sent = await bot.send_sticker(chat_id=chat_id, sticker=message.sticker.file_id, **add_thread({}))
                        if chunk:  # Suffix/text отдельно, если есть
                            extra = await bot.send_message(chat_id=chat_id, text=chunk, entities=chunk_entities, **add_thread({}))
                            sent_messages.append(extra)
                    elif message.video_note:
                        sent = await bot.send_video_note(chat_id=chat_id, video_note=message.video_note.file_id, **add_thread({}))
                        if chunk:
                            extra = await bot.send_message(chat_id=chat_id, text=chunk, entities=chunk_entities, **add_thread({}))
                            sent_messages.append(extra)
                    else:
                        sent = None
                else:
                    sent = await bot.send_message(chat_id=chat_id, text=chunk, entities=chunk_entities, **add_thread({}))

                if sent:
                    sent_messages.append(sent)

        elif message.text:
            parts = split_text(base_text, MAX_TEXT)
            for idx, chunk in enumerate(parts):
                chunk_entities = slice_entities(message.entities or [], idx * MAX_TEXT, (idx + 1) * MAX_TEXT)
                sent = await bot.send_message(chat_id=chat_id, text=chunk, entities=chunk_entities, **add_thread({}))
                sent_messages.append(sent)

        elif message.poll:
            question = message.poll.question + (suffix or "")
            sent = await bot.send_poll(
                chat_id=chat_id,
                question=question[:300],  # Лимит
                options=[opt.text for opt in message.poll.options],
                is_anonymous=message.poll.is_anonymous,
                type=message.poll.type,
                allows_multiple_answers=message.poll.allows_multiple_answers,
                **add_thread({})
            )
            sent_messages.append(sent)

        else:  # Fallback для других (location, contact, etc.)
            sent = await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                **add_thread({})
            )
            sent_messages.append(sent)
            if suffix:
                extra = await bot.send_message(chat_id=chat_id, text=suffix, **add_thread({}))
                sent_messages.append(extra)

    except Exception as e:
        logger.error(f"[SENDER] Manual send failed: {e}")

    if not sent_messages:
        logger.warning("[SENDER] Нет отправленных сообщений")

    return sent_messages