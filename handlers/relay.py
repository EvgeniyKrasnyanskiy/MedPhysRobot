# handlers/relay.py

from aiogram import Router, F
from aiogram.types import Message, InputMediaPhoto, InputMediaVideo
from aiogram import Bot
from utils.config import RELAY_GROUP_ID
from utils.db import (
    save_mapping, get_user_by_forwarded, is_banned, is_muted
)
from utils.logger import setup_logger
from typing import List

router = Router()
logger = setup_logger("relay")

@router.message(F.chat.type == "private")
async def handle_private_message(message: Message, bot: Bot, album: List[Message] = None):
    user_id = message.from_user.id

    if is_banned(user_id):
        await message.answer("🚫 Вы заблокированы.")
        return

    if is_muted(user_id):
        await message.answer("🔇 Вы временно замьючены.")
        return

    try:
        if album:
            media = []
            for msg in album:
                if msg.photo:
                    media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=msg.caption or ""))
                elif msg.video:
                    media.append(InputMediaVideo(media=msg.video.file_id, caption=msg.caption or ""))
            sent = await bot.send_media_group(chat_id=RELAY_GROUP_ID, media=media)
            save_mapping(sent[0].message_id, user_id, album[0].message_id)
            logger.info(f"[RELAY] Переслан альбом из {len(album)} элементов")
        else:
            forwarded = await bot.copy_message(
                chat_id=RELAY_GROUP_ID,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            save_mapping(forwarded.message_id, user_id, message.message_id)
            logger.info(f"[RELAY] Переслано одиночное сообщение от {user_id}")
        await message.answer("✅ Ваше сообщение получено!")
    except Exception as e:
        logger.error(f"[RELAY] Ошибка пересылки: {e}")
        await message.answer("⚠️ Не удалось переслать сообщение.")

@router.message(F.chat.id == RELAY_GROUP_ID, F.reply_to_message)
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
                    media.append(InputMediaPhoto(media=msg.photo[-1].file_id, caption=msg.caption or ""))
                elif msg.video:
                    media.append(InputMediaVideo(media=msg.video.file_id, caption=msg.caption or ""))
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
