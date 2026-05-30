# handlers/thanks.py

import asyncio
import re

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message

from utils.config import MEDPHYSPRO_GROUP_ID
from utils.thanks_db import increment_thanks, get_top_thanked
from utils.thanks_words import load_thanks_words
from utils.logger import get_logger

router = Router()
logger = get_logger("thanks")
logger.info("[THANKS] thanks.py загружен")

THANKS_WORDS = load_thanks_words()
EMOJI_TRIGGERS = {"🙏", "🤝", "❤️", "💐"}

@router.message(F.chat.id == MEDPHYSPRO_GROUP_ID, F.reply_to_message)
async def detect_thanks(message: Message):
    text = (message.text or "").lower()
    words = re.findall(r"\b\w+\b", text)

    fuzzy_hits = [
        word for word in words
        if any(word.startswith(thx) for thx in THANKS_WORDS)
    ]

    emoji_hits = any(emoji in (message.text or "") for emoji in EMOJI_TRIGGERS)

    if fuzzy_hits or emoji_hits:
        target_user = message.reply_to_message.from_user
        if target_user and not target_user.is_bot and target_user.id != message.from_user.id:
            increment_thanks(target_user.id, target_user.full_name)
            logger.info(
                f"[THANKS] +1 для {target_user.full_name} ({target_user.id}) — "
                f"слова: {fuzzy_hits}, эмодзи: {emoji_hits}"
            )

@router.message(F.chat.id == MEDPHYSPRO_GROUP_ID, Command("top10", ignore_mention=True, ignore_case=True))
async def show_top_thanked(message: Message):
    logger.info(f"[THANKS] Команда /top10 вызвана пользователем {message.from_user.full_name} ({message.from_user.id})")

    top = get_top_thanked(limit=10)
    if not top:
        reply = await message.answer("Пока никто не получил благодарностей.")
        logger.info("[THANKS] Список благодарностей пуст")
    else:
        lines = [f"🏆 ТОП-10 по благодарностям:"]
        for i, (name, count) in enumerate(top, 1):
            lines.append(f"{i}. {name} — {count}")
        reply = await message.answer("\n".join(lines))
        logger.info(f"[THANKS] Список ТОП-10 отправлен ({len(top)} записей)")

    # ⏳ Удаление команды через 3 секунды
    await asyncio.sleep(3)
    try:
        await message.delete()
        logger.info(f"[THANKS] Команда /top10 удалена")
    except Exception as e:
        logger.warning(f"[THANKS] Не удалось удалить команду /top10: {e}")

    # ⏳ Удаление ответа через 60 секунд
    await asyncio.sleep(57)
    try:
        await reply.delete()
        logger.info(f"[THANKS] Ответ по /top10 удалён")
    except Exception as e:
        logger.warning(f"[THANKS] Не удалось удалить ответ по /top10: {e}")
