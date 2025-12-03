# utils/editor.py

import asyncio
import re
import os
from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from dotenv import load_dotenv

# Загружаем токен из .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))

def parse_group_link(link: str) -> tuple[int, int]:
    m = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if not m:
        raise ValueError("Неверный формат ссылки")
    chat_id = int("-100" + m.group(1))   # правильно!
    msg_id = int(m.group(2))
    return chat_id, msg_id

async def edit_group_message(group_link: str, new_text: str) -> bool:
    try:
        group_chat, group_msg_id = parse_group_link(group_link)

        await bot.edit_message_text(
            chat_id=group_chat,
            message_id=group_msg_id,
            text=new_text
        )
        print(f"Сообщение {group_msg_id} в чате {group_chat} обновлено")
        return True
    except Exception as e:
        print(f"Ошибка при редактировании: {e}")
        return False
    finally:
        await bot.session.close()

async def main():
    group_link = "https://t.me/c/1102663807/40322"

    new_text = """Редактируемый текст

Источник: @MedPhysProChannel
"""


    await edit_group_message(group_link, new_text)

if __name__ == "__main__":
    asyncio.run(main())