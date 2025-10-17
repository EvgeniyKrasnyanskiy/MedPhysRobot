# utils/sender.py

from aiogram import Bot
from aiogram.types import Message
from utils.logger import get_logger

logger = get_logger("sender")
logger.info("[SENDER] sender.py загружен")

async def send_content_to_group(
    message: Message,
    bot: Bot,
    chat_id: int,
    thread_id: int | None = None,
    suffix: str = ""
) -> Message | None:
    if message.photo:
        return await bot.send_photo(
            chat_id=chat_id,
            photo=message.photo[-1].file_id,
            caption=(message.caption or "") + suffix,
            message_thread_id=thread_id
        )
    elif message.video:
        return await bot.send_video(
            chat_id=chat_id,
            video=message.video.file_id,
            caption=(message.caption or "") + suffix,
            message_thread_id=thread_id
        )
    elif message.document:
        return await bot.send_document(
            chat_id=chat_id,
            document=message.document.file_id,
            caption=(message.caption or "") + suffix,
            message_thread_id=thread_id
        )
    elif message.text:
        return await bot.send_message(
            chat_id=chat_id,
            text=message.text + suffix,
            message_thread_id=thread_id
        )
    return None
