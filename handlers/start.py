# handlers/start.py

from aiogram import Router
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart
from utils.logger import get_logger
from utils.config import MEDPHYSPRO_CHANNEL_USERNAME

logger = get_logger("start")
router = Router()

@router.message(CommandStart())
async def handle_start(message: Message):
    channel_user = (MEDPHYSPRO_CHANNEL_USERNAME or "MedPhysProChannel").lstrip("@")
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📢 Наш канал",
                    url=f"https://t.me/{channel_user}"
                )
            ]
        ]
    )

    await message.answer(
        "👋 <b>Добро пожаловать в бот обратной связи MedPhysPro!</b>\n\n"
        "Здесь вы можете связаться с администрацией сообщества:\n"
        "• 👥 <b>Для вступления в группу MedPhysPro:</b> кратко расскажите о себе и вашей связи с медицинской физикой;\n"
        "• ❓ Задать вопрос или предложить тему для обсуждения;\n"
        "• 📢 Отправить материалы, новости или статьи;\n"
        "• 📁 Прислать файлы любого формата (документы, PDF, фото, видео, архивы).\n\n"
        "✉️ <i>Просто отправьте ваше сообщение прямо в этот чат. "
        "Дежурный администратор получит его и ответит вам здесь же.</i>\n\n"
        "ℹ️ Если вы захотите изменить отправленное сообщение, просто отредактируйте его — "
        "правка мгновенно обновится у администраторов.",
        reply_markup=keyboard,
        parse_mode="HTML"
    )
    logger.info(f"[START] Обрабатываю /start от {message.from_user.id}")

