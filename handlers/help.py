# handlers/help.py

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats
from utils.config import ADMIN_GROUP_ID

router = Router()

@router.message(Command("help", ignore_mention=True, ignore_case=True))
async def help_command(message: Message, bot: Bot):
    is_admin = False
    if message.chat.id == ADMIN_GROUP_ID:
        is_admin = True
    elif message.chat.type == "private":
        try:
            member = await bot.get_chat_member(chat_id=ADMIN_GROUP_ID, user_id=message.from_user.id)
            if member.status in ["administrator", "creator", "member"]:
                is_admin = True
        except Exception:
            pass

    if is_admin:
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
            "/mute — заглушить (1m, 2h, 3d)\n"
            "/unban — снять бан\n"
            "/unmute — снять заглушку\n"
            "/status — показать статус\n"
            "/send_to_pro_group — переслать в PRO\n"
            "/send_to_channel [ссылка] — переслать в канал (или отредактировать существующий пост при указании ссылки/ID)\n\n"
            "🔁 <b>Ретрансляция (only here):</b>\n"
            "Сообщения из лички бота пересылаются в группу админов, ответы возвращаются автору\n\n"
            "🙏 <b>Благодарности (only in PRO):</b>\n"
            "Если пользователь отвечает с фразой типа «спасибо» — бот учитывает это в статистике\n\n"
            "📊 <b>Статистика (only in PRO):</b>\n"
            "/top10 — показать (на 1 минуту) ТОП-10 по благодарностям\n\n"
            "ℹ️ Некоторые команды автоматически удаляются из чата для чистоты\n"
        )
    else:
        help_text = (
            "🤖 <b>MedPhysRobot</b> — бот для связи с администрацией MedPhysPro.\n\n"
            "💬 Вы можете отправить любое текстовое сообщение или медиафайл (фото, видео, документ) прямо в этот чат. "
            "Администраторы получат его и обязательно ответят вам!\n\n"
            "📋 <b>Доступные команды:</b>\n"
            "/start — запустить бота\n"
            "/help — показать эту справку\n"
        )

    await message.answer(help_text)

