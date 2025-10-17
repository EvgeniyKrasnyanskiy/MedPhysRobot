# handlers/help.py

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats
from utils.config import ADMIN_GROUP_ID

router = Router()

@router.message(F.chat.id == ADMIN_GROUP_ID, Command("help", ignore_mention=True, ignore_case=True))
async def help_command(message: Message, bot: Bot):
    scope = (
        BotCommandScopeAllGroupChats()
        if message.chat.type in ["group", "supergroup"]
        else BotCommandScopeDefault()
    )

    commands = await bot.get_my_commands(scope=scope)

    help_text = (
        "🤖 <b>MedPhysRobot</b> — бот для ретрансляции сообщений, пересылки новостей и тд.\n\n"
        "📋 <b>Доступные команды:</b>\n\n"
    )

    for cmd in commands:
        help_text += f"/{cmd.command} — {cmd.description}\n"

    help_text += (
        "\n🛡️ <b>Модерация:</b>\n"
        "/ban — забанить навсегда\n"
        "/mute — заглушить на 2 часа\n"
        "/unban — снять бан\n"
        "/unmute — снять заглушку\n"
        "/status — показать статус\n"
        "/send_to_pro_group — переслать в PRO\n\n"
        "🔁 <b>Ретрансляция (only here):</b>\n"
        "Сообщения из лички бота пересылаются в группу админов, ответы возвращаются автору\n\n"
        "🙏 <b>Благодарности (only in PRO):</b>\n"
        "Если пользователь отвечает с фразой типа «спасибо» — бот учитывает это в статистике\n\n"
        "📊 <b>Статистика (only in PRO):</b>\n"
        "/top10 — показать (на 1 минуту) ТОП-10 по благодарностям\n\n"
        "ℹ️ Некоторые команды автоматически удаляются из чата для чистоты\n"
    )

    await message.answer(help_text)

