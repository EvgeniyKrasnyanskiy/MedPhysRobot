# handlers/relay.py

import html
from aiogram import Router, F, Bot
from aiogram.types import Message, MessageEntity, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio, User

from typing import List
from utils.config import ADMIN_GROUP_ID
from utils.db import save_mapping, get_user_by_forwarded, is_banned, is_muted, get_admin_msg_id, get_user_reply_msg, \
    save_reply_mapping
from utils.logger import get_logger
from utils.sender import send_content_to_group, shift_entities, utf16_len

router = Router()
logger = get_logger("relay")
logger.info("[RELAY] relay.py загружен")

from aiogram.utils.formatting import as_list, Text, Bold, TextLink, Code

def format_header(user: User) -> str:
    """Форматирует заголовок с данными пользователя для админ-группы в HTML."""
    username = f" (@{html.escape(user.username)})" if user.username else ""
    header_content = as_list(
        Text("📨 "),
        Bold("Сообщение от ", TextLink(user.full_name, url=f"tg://user?id={user.id}")),
        Text(username, "\nID: "),
        Code(str(user.id)),
        Text("\n\n")
    )
    return header_content.as_html()


async def relay_content(message: Message, bot: Bot, header_html: str = "") -> List[Message]:
    """Forwards a single user message to the admin group with the relay header."""
    return await send_content_to_group(
        message=message,
        bot=bot,
        chat_id=ADMIN_GROUP_ID,
        prefix=header_html,
        parse_mode="HTML"
    )

@router.message(F.chat.type == "private")
async def handle_private_message(message: Message, bot: Bot, album: List[Message] = None):
    user = message.from_user

    if is_banned(user.id):
        await message.answer("🚫 Вы заблокированы.")
        return

    if is_muted(user.id):
        await message.answer("🔇 Вы временно замьючены.")
        return

    try:
        header_html = format_header(user)

        # 🖼️ Альбом
        if album:
            media = []
            for i, msg in enumerate(album):
                # Извлекаем оригинальный HTML-контент
                user_html = msg.html_text or ""
                
                if i == 0:
                    current_caption = header_html + user_html
                else:
                    current_caption = user_html

                if msg.photo:
                    media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=current_caption, parse_mode="HTML"))
                elif msg.video:
                    media.append(InputMediaVideo(media=msg.video.file_id, caption=current_caption, parse_mode="HTML"))
            
            sent = await bot.send_media_group(chat_id=ADMIN_GROUP_ID, media=media)
            save_mapping(sent[0].message_id, user.id, album[0].message_id)
            logger.info(f"[RELAY] Альбом от {user.id} ({user.full_name})")

        # 🔁 Пересланное сообщение
        elif message.forward_from_chat or message.forward_from:
            # Сначала шлем заголовок, т.к. forward не позволяет менять текст
            intro = await bot.send_message(chat_id=ADMIN_GROUP_ID, text=header_html, parse_mode="HTML")
            forwarded = await bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            save_mapping(forwarded.message_id, user.id, message.message_id)

        # 📦 Всё остальное (единичные сообщения)
        else:
            sent_list = await relay_content(message, bot, header_html=header_html)
            if sent_list:
                # Мапим первое сообщение из списка (обычно оно единственное)
                save_mapping(sent_list[0].message_id, user.id, message.message_id)
                logger.info(f"[RELAY] Контент от {user.id} ({user.full_name})")

        await message.answer("✅ Ваше сообщение получено!")

    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки: {e}")
        await message.answer("⚠️ Не удалось переслать сообщение.")


@router.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def handle_group_reply(message: Message, bot: Bot, album: list[Message] = None):
    forwarded_id = message.reply_to_message.message_id
    user_id = get_user_by_forwarded(forwarded_id)

    if not user_id:
        logger.warning(f"[RELAY] Не найден user_id для forwarded_id={forwarded_id}")
        return

    try:
        # --- Альбом (несколько фото/видео/доков/аудио) ---
        if album:
            media = []
            for msg in album:
                if msg.photo:
                    media.append(InputMediaPhoto(
                        media=msg.photo[-1].file_id,
                        caption=msg.html_text or "",
                        parse_mode="HTML"
                    ))
                elif msg.video:
                    media.append(InputMediaVideo(
                        media=msg.video.file_id,
                        caption=msg.html_text or "",
                        parse_mode="HTML"
                    ))
                elif msg.document:
                    media.append(InputMediaDocument(
                        media=msg.document.file_id,
                        caption=msg.html_text or "",
                        parse_mode="HTML"
                    ))
                elif msg.audio:
                    media.append(InputMediaAudio(
                        media=msg.audio.file_id,
                        caption=msg.html_text or "",
                        parse_mode="HTML"
                    ))
            if media:
                sent = await bot.send_media_group(chat_id=user_id, media=media)
                save_reply_mapping(admin_msg_id=message.message_id,
                                   user_id=user_id,
                                   user_msg_id=sent[0].message_id)
                logger.info(f"[RELAY] Ответ-альбом отправлен пользователю {user_id}")
            else:
                logger.warning(f"[RELAY] Альбом не содержит поддерживаемых типов")

        # --- Одиночное сообщение ---
        else:
            if message.text:
                sent = await bot.send_message(
                    chat_id=user_id,
                    text=message.html_text,
                    parse_mode="HTML"
                )
            elif message.photo:
                sent = await bot.send_photo(
                    chat_id=user_id,
                    photo=message.photo[-1].file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.video:
                sent = await bot.send_video(
                    chat_id=user_id,
                    video=message.video.file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.document:
                sent = await bot.send_document(
                    chat_id=user_id,
                    document=message.document.file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.audio:
                sent = await bot.send_audio(
                    chat_id=user_id,
                    audio=message.audio.file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.voice:
                sent = await bot.send_voice(
                    chat_id=user_id,
                    voice=message.voice.file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.animation:
                sent = await bot.send_animation(
                    chat_id=user_id,
                    animation=message.animation.file_id,
                    caption=message.html_text,
                    parse_mode="HTML"
                )
            elif message.sticker:
                sent = await bot.send_sticker(
                    chat_id=user_id,
                    sticker=message.sticker.file_id
                )
            elif message.video_note:
                sent = await bot.send_video_note(
                    chat_id=user_id,
                    video_note=message.video_note.file_id
                )
            else:
                sent = await bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=message.chat.id,
                    message_id=message.message_id
                )

            save_reply_mapping(admin_msg_id=message.message_id,
                               user_id=user_id,
                               user_msg_id=sent.message_id)
            logger.info(f"[RELAY] Ответ отправлен пользователю {user_id}")

    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки ответа: {e}")


@router.edited_message(F.chat.type == "private")
async def handle_edited_private_message(message: Message, bot: Bot):
    admin_msg_id = get_admin_msg_id(message.from_user.id, message.message_id)
    if not admin_msg_id:
        logger.warning(f"[RELAY] Нет admin_msg_id для user_id={message.from_user.id}, msg_id={message.message_id}")
        return

    try:
        if message.caption and (message.photo or message.video or message.document):
            await bot.edit_message_caption(
                chat_id=ADMIN_GROUP_ID,
                message_id=admin_msg_id,
                caption=f"(отредактировано)\n{message.html_text}",
                parse_mode="HTML"
            )
        elif message.text:
            await bot.edit_message_text(
                chat_id=ADMIN_GROUP_ID,
                message_id=admin_msg_id,
                text=f"(отредактировано)\n{message.html_text}",
                parse_mode="HTML"
            )
        logger.info(f"[RELAY] Обновлено сообщение от {message.from_user.id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка при обновлении сообщения: {e}")

@router.edited_message(F.chat.id == ADMIN_GROUP_ID)
async def handle_admin_edit(message: Message, bot: Bot):
    result = get_user_reply_msg(message.message_id)
    if not result:
        logger.warning(f"[RELAY] Не найдено соответствие для admin_msg_id={message.message_id}")
        return

    user_id, user_msg_id = result
    try:
        if message.caption and (message.photo or message.video or message.document):
            await bot.edit_message_caption(
                chat_id=user_id,
                message_id=user_msg_id,
                caption=f"(отредактировано)\n{message.caption}",
                caption_entities=message.caption_entities
            )
        elif message.text:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=user_msg_id,
                text=f"(отредактировано)\n{message.text}",
                entities=message.entities
            )
        logger.info(f"[RELAY] Редактированный ответ обновлён для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка редактирования ответа: {e}")

@router.edited_message(F.chat.type == "private")
async def handle_edited_album_caption(message: Message, bot: Bot):
    if not message.caption:
        return  # не редактировали caption — пропускаем

    admin_msg_id = get_admin_msg_id(message.from_user.id, message.message_id)
    if not admin_msg_id:
        logger.warning(f"[RELAY] Нет admin_msg_id для альбома user_id={message.from_user.id}, msg_id={message.message_id}")
        return

    try:
        await bot.edit_message_caption(
            chat_id=ADMIN_GROUP_ID,
            message_id=admin_msg_id,
            caption=f"(отредактировано)\n{message.caption}",
            caption_entities=message.caption_entities
        )
        logger.info(f"[RELAY] Обновлён caption альбома от {message.from_user.id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка редактирования caption альбома: {e}")

@router.edited_message(F.chat.id == ADMIN_GROUP_ID)
async def handle_admin_album_edit(message: Message, bot: Bot):
    if not message.caption:
        return

    result = get_user_reply_msg(message.message_id)
    if not result:
        logger.warning(f"[RELAY] Нет соответствия для admin_msg_id={message.message_id}")
        return

    user_id, user_msg_id = result
    try:
        await bot.edit_message_caption(
            chat_id=user_id,
            message_id=user_msg_id,
            caption=f"(отредактировано)\n{message.caption}",
            caption_entities=message.caption_entities
        )
        logger.info(f"[RELAY] Обновлён caption альбома для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка редактирования caption альбома: {e}")
