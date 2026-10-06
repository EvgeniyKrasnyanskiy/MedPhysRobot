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

def create_input_media(
    msg: Message,
    caption: str | None = None
) -> InputMediaPhoto | InputMediaVideo | InputMediaDocument | InputMediaAudio | None:
    """Creates an InputMedia object for Telegram send_media_group based on message media type."""
    kwargs = {"caption": caption, "parse_mode": "HTML"} if caption is not None else {}
    if msg.photo:
        return InputMediaPhoto(media=msg.photo[-1].file_id, **kwargs)
    elif msg.video:
        return InputMediaVideo(media=msg.video.file_id, **kwargs)
    elif msg.document:
        return InputMediaDocument(media=msg.document.file_id, **kwargs)
    elif msg.audio:
        return InputMediaAudio(media=msg.audio.file_id, **kwargs)
    return None


def get_media_category(msg: Message) -> str | None:
    """Returns Telegram-compatible media category for grouping into albums."""
    if msg.photo or msg.video:
        return "visual"
    elif msg.document:
        return "document"
    elif msg.audio:
        return "audio"
    return None


def partition_media_album(album: List[Message]) -> List[List[Message]]:
    """Partitions album messages into Telegram-compatible groups of <= 10 items."""
    groups: List[List[Message]] = []
    for msg in album:
        cat = get_media_category(msg)
        if not groups or get_media_category(groups[-1][0]) != cat or cat is None:
            groups.append([msg])
        else:
            if len(groups[-1]) < 10:
                groups[-1].append(msg)
            else:
                groups.append([msg])
    return groups


async def send_single_reply_to_user(bot: Bot, user_id: int, message: Message) -> Message:
    """Sends a single admin reply message back to the original user."""
    if message.text:
        return await bot.send_message(
            chat_id=user_id,
            text=message.html_text,
            parse_mode="HTML"
        )
    elif message.photo:
        return await bot.send_photo(
            chat_id=user_id,
            photo=message.photo[-1].file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.video:
        return await bot.send_video(
            chat_id=user_id,
            video=message.video.file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.document:
        return await bot.send_document(
            chat_id=user_id,
            document=message.document.file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.audio:
        return await bot.send_audio(
            chat_id=user_id,
            audio=message.audio.file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.voice:
        return await bot.send_voice(
            chat_id=user_id,
            voice=message.voice.file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.animation:
        return await bot.send_animation(
            chat_id=user_id,
            animation=message.animation.file_id,
            caption=message.html_text,
            parse_mode="HTML"
        )
    elif message.sticker:
        return await bot.send_sticker(
            chat_id=user_id,
            sticker=message.sticker.file_id
        )
    elif message.video_note:
        return await bot.send_video_note(
            chat_id=user_id,
            video_note=message.video_note.file_id
        )
    else:
        return await bot.copy_message(
            chat_id=user_id,
            from_chat_id=message.chat.id,
            message_id=message.message_id
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

        # 🖼️ Альбом (пакет медиа/файлов)
        if album:
            groups = partition_media_album(album)
            for grp_idx, grp in enumerate(groups):
                cat = get_media_category(grp[0])
                is_first_group = (grp_idx == 0)

                if len(grp) >= 2 and cat is not None:
                    user_html = grp[0].html_text or ""
                    first_caption = ""

                    if is_first_group:
                        combined_caption = header_html + user_html
                        if utf16_len(combined_caption) <= 1024:
                            first_caption = combined_caption
                        else:
                            await bot.send_message(chat_id=ADMIN_GROUP_ID, text=header_html, parse_mode="HTML")
                            first_caption = user_html if utf16_len(user_html) <= 1024 else ""
                            if not first_caption and user_html:
                                await bot.send_message(chat_id=ADMIN_GROUP_ID, text=user_html, parse_mode="HTML")
                    else:
                        first_caption = user_html if utf16_len(user_html) <= 1024 else ""

                    media = []
                    for i, msg in enumerate(grp):
                        cap = first_caption if i == 0 else (msg.html_text or "")
                        if utf16_len(cap) > 1024:
                            cap = cap[:1024]
                        media_item = create_input_media(msg, caption=cap if cap else None)
                        if media_item:
                            media.append(media_item)

                    if len(media) >= 2:
                        sent = await bot.send_media_group(chat_id=ADMIN_GROUP_ID, media=media)
                        for s_msg, orig_msg in zip(sent, grp):
                            save_mapping(s_msg.message_id, user.id, orig_msg.message_id)
                        logger.info(f"[RELAY] Альбом ({cat}, {len(media)} шт.) от {user.id} ({user.full_name})")
                    else:
                        for msg in grp:
                            sent_list = await relay_content(msg, bot, header_html=header_html if is_first_group else "")
                            if sent_list:
                                save_mapping(sent_list[0].message_id, user.id, msg.message_id)
                            is_first_group = False
                else:
                    for msg in grp:
                        prefix_to_use = header_html if is_first_group else ""
                        sent_list = await relay_content(msg, bot, header_html=prefix_to_use)
                        if sent_list:
                            save_mapping(sent_list[0].message_id, user.id, msg.message_id)
                        is_first_group = False

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
                save_mapping(sent_list[0].message_id, user.id, message.message_id)
                logger.info(f"[RELAY] Контент от {user.id} ({user.full_name})")

        await message.answer("✅ Ваше сообщение получено!")

    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки: {e}")
        await message.answer("⚠️ Не удалось переслать сообщение.")


@router.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def handle_group_reply(message: Message, bot: Bot, album: list[Message] = None):
    # Ignore replies to messages not sent by the bot (e.g., admin-to-admin chat)
    if not message.reply_to_message.from_user or message.reply_to_message.from_user.id != bot.id:
        return

    forwarded_id = message.reply_to_message.message_id
    user_id = get_user_by_forwarded(forwarded_id)

    if not user_id:
        logger.warning(f"[RELAY] Не найден user_id для forwarded_id={forwarded_id}")
        await message.reply("⚠️ Не удалось найти пользователя для ответа. Возможно, сообщение слишком старое (более 14 дней).")
        return

    try:
        # --- Альбом (несколько фото/видео/доков/аудио) ---
        if album:
            groups = partition_media_album(album)
            for grp in groups:
                cat = get_media_category(grp[0])
                if len(grp) >= 2 and cat is not None:
                    media = []
                    for msg in grp:
                        cap = msg.html_text or ""
                        if utf16_len(cap) > 1024:
                            cap = cap[:1024]
                        media_item = create_input_media(msg, caption=cap if cap else None)
                        if media_item:
                            media.append(media_item)

                    if len(media) >= 2:
                        sent = await bot.send_media_group(chat_id=user_id, media=media)
                        for s_msg, a_msg in zip(sent, grp):
                            save_reply_mapping(admin_msg_id=a_msg.message_id,
                                               user_id=user_id,
                                               user_msg_id=s_msg.message_id)
                        logger.info(f"[RELAY] Ответ-альбом ({cat}, {len(media)} шт.) отправлен пользователю {user_id}")
                    else:
                        for msg in grp:
                            sent_msg = await send_single_reply_to_user(bot, user_id, msg)
                            if sent_msg:
                                save_reply_mapping(admin_msg_id=msg.message_id,
                                                   user_id=user_id,
                                                   user_msg_id=sent_msg.message_id)
                else:
                    for msg in grp:
                        sent_msg = await send_single_reply_to_user(bot, user_id, msg)
                        if sent_msg:
                            save_reply_mapping(admin_msg_id=msg.message_id,
                                               user_id=user_id,
                                               user_msg_id=sent_msg.message_id)

        # --- Одиночное сообщение ---
        else:
            sent = await send_single_reply_to_user(bot, user_id, message)
            if sent:
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
        try:
            await message.reply("⚠️ К сожалению, это сообщение слишком старое (или связь была очищена), и я не могу синхронизировать правки.")
        except:
            pass
        return

    try:
        if message.caption is not None and (message.photo or message.video or message.document):
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
        else:
            logger.warning(f"[RELAY] Не удалось обновить сообщение от {message.from_user.id}: нет text/caption")
            return
        logger.info(f"[RELAY] Обновлено сообщение от {message.from_user.id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка при обновлении сообщения: {e}")

@router.edited_message(F.chat.id == ADMIN_GROUP_ID)
async def handle_admin_edit(message: Message, bot: Bot):
    # Ignore edits if this message is not a reply to a bot message
    if not message.reply_to_message or not message.reply_to_message.from_user or message.reply_to_message.from_user.id != bot.id:
        return

    result = get_user_reply_msg(message.message_id)
    if not result:
        logger.warning(f"[RELAY] Не найдено соответствие для admin_msg_id={message.message_id}")
        await message.reply("⚠️ Не удалось найти пользователя для ответа. Возможно, сообщение слишком старое (более 14 дней).")
        return

    user_id, user_msg_id = result
    try:
        if message.caption is not None and (message.photo or message.video or message.document):
            await bot.edit_message_caption(
                chat_id=user_id,
                message_id=user_msg_id,
                caption=f"(отредактировано)\n{message.html_text}",
                parse_mode="HTML"
            )
        elif message.text:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=user_msg_id,
                text=f"(отредактировано)\n{message.html_text}",
                parse_mode="HTML"
            )
        else:
            logger.warning(f"[RELAY] Не удалось обновить ответ для {user_id}: нет text/caption")
            return
        logger.info(f"[RELAY] Редактированный ответ обновлён для пользователя {user_id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка редактирования ответа: {e}")

