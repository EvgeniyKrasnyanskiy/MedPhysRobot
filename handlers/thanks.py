# handlers/thanks.py

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from utils.config import TARGET_GROUP_ID
from utils.thanks_db import increment_thanks, get_top_thanked
from utils.thanks_words import load_thanks_words
from utils.logger import setup_logger
import re

router = Router()
logger = setup_logger("thanks")

THANKS_WORDS = load_thanks_words()
EMOJI_TRIGGERS = {"🙏", "🤝", "❤️", "💐"}

@router.message(F.chat.id == TARGET_GROUP_ID, F.reply_to_message)
async def detect_thanks(message: Message):
    text = (message.text or "").lower()

    # Удаляем знаки препинания, разбиваем на слова
    words = re.findall(r"\b\w+\b", text)

    # Fuzzy matching: ищем слова, начинающиеся с благодарностей
    fuzzy_hits = [
        word for word in words
        if any(word.startswith(thx) for thx in THANKS_WORDS)
    ]

    # Проверка на эмодзи
    emoji_hits = any(emoji in message.text for emoji in EMOJI_TRIGGERS)

    if fuzzy_hits or emoji_hits:
        target_user = message.reply_to_message.from_user
        if target_user:
            increment_thanks(target_user.id, target_user.full_name)
            logger.info(f"[THANKS] +1 для {target_user.full_name} ({target_user.id})")
            return

@router.message(F.chat.id == TARGET_GROUP_ID, Command("top10", ignore_mention=True, ignore_case=True))
async def show_top_thanked(message: Message):
    top = get_top_thanked(limit=10)
    if not top:
        await message.answer("Пока никто не получил благодарностей.")
        return

    lines = [f"🏆 ТОП-10 по благодарностям:"]
    for i, (name, count) in enumerate(top, 1):
        lines.append(f"{i}. {name} — {count}")
    await message.answer("\n".join(lines))
