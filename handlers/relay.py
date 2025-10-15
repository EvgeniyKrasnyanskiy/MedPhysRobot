# handlers/relay.py

from aiogram import Router, F, Bot
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo, User
from typing import List
from utils.config import ADMIN_GROUP_ID
from utils.db import save_mapping, get_user_by_forwarded, is_banned, is_muted
from utils.logger import setup_logger

router = Router()
logger = setup_logger("relay")

def format_caption(user: User, original: str = "") -> str:
    name = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    header = f"📨 Сообщение от {name} \n(user_id: <code>{user.id}</code>) ⬇️"
    if original:
        return f"{header}\n\n{original}"
    return header

async def relay_content(message: Message, bot: Bot, user: User) -> Message | None:
    if message.photo:
        return await bot.send_photo(
            chat_id=ADMIN_GROUP_ID,
            photo=message.photo[-1].file_id,
            caption=message.caption or "",
            parse_mode="HTML"
        )
    elif message.video:
        return await bot.send_video(
            chat_id=ADMIN_GROUP_ID,
            video=message.video.file_id,
            caption=message.caption or "",
            parse_mode="HTML"
        )
    elif message.document:
        return await bot.send_document(
            chat_id=ADMIN_GROUP_ID,
            document=message.document.file_id,
            caption=message.caption or "",
            parse_mode="HTML"
        )
    elif message.audio:
        return await bot.send_audio(
            chat_id=ADMIN_GROUP_ID,
            audio=message.audio.file_id,
            caption=message.caption or "",
            parse_mode="HTML"
        )
    elif message.voice:
        return await bot.send_voice(
            chat_id=ADMIN_GROUP_ID,
            voice=message.voice.file_id,
            caption=message.caption or "",
            parse_mode="HTML"
        )
    elif message.location:
        return await bot.send_location(
            chat_id=ADMIN_GROUP_ID,
            latitude=message.location.latitude,
            longitude=message.location.longitude
        )
    elif message.contact:
        return await bot.send_contact(
            chat_id=ADMIN_GROUP_ID,
            phone_number=message.contact.phone_number,
            first_name=message.contact.first_name,
            last_name=message.contact.last_name or "",
            vcard=message.contact.vcard or None
        )
    elif message.sticker:
        return await bot.send_sticker(
            chat_id=ADMIN_GROUP_ID,
            sticker=message.sticker.file_id
        )
    else:
        return await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=message.text or message.caption or "",
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
        # 📨 Сервисное сообщение
        intro = await bot.send_message(
            chat_id=ADMIN_GROUP_ID,
            text=format_caption(user),
            parse_mode="HTML"
        )
        save_mapping(intro.message_id, user.id, message.message_id)

        # 🖼️ Альбом
        if album:
            media = []
            for i, msg in enumerate(album):
                caption = msg.caption if i == 0 else ""
                if msg.photo:
                    media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=caption, parse_mode="HTML"))
                elif msg.video:
                    media.append(InputMediaVideo(media=msg.video.file_id, caption=caption, parse_mode="HTML"))
            sent = await bot.send_media_group(chat_id=ADMIN_GROUP_ID, media=media)
            save_mapping(sent[0].message_id, user.id, album[0].message_id)
            logger.info(f"[RELAY] Альбом от {user.id} ({user.full_name})")

        # 🔁 Пересланное сообщение
        elif message.forward_from_chat or message.forward_from:
            forwarded = await bot.forward_message(
                chat_id=ADMIN_GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            save_mapping(forwarded.message_id, user.id, message.message_id)
            logger.info(f"[RELAY] Переслано от {user.id} ({user.full_name})")

        # 📦 Всё остальное
        else:
            sent = await relay_content(message, bot, user)
            if sent:
                save_mapping(sent.message_id, user.id, message.message_id)
                logger.info(f"[RELAY] Контент от {user.id} ({user.full_name})")

        await message.answer("✅ Ваше сообщение получено!")

    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки: {e}")
        await message.answer("⚠️ Не удалось переслать сообщение.")


@router.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def handle_group_reply(message: Message, bot: Bot, album: List[Message] = None):
    forwarded_id = message.reply_to_message.message_id
    user_id = get_user_by_forwarded(forwarded_id)

    if not user_id:
        logger.warning(f"[RELAY] Не найден user_id для forwarded_id={forwarded_id}")
        return

    try:
        if album:
            media = []
            for msg in album:
                if msg.photo:
                    media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=msg.caption or "", parse_mode="HTML"))
                elif msg.video:
                    media.append(InputMediaVideo(media=msg.video.file_id, caption=msg.caption or "", parse_mode="HTML"))
            await bot.send_media_group(chat_id=user_id, media=media)
            logger.info(f"[RELAY] Ответ-альбом отправлен пользователю {user_id}")
        else:
            await bot.copy_message(
                chat_id=user_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            logger.info(f"[RELAY] Ответ отправлен пользователю {user_id}")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки ответа: {e}")
