# handlers/help.py

from aiogram import Router, Bot
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats


router = Router()

@router.message(Command("help"))
async def help_command(message: Message, bot: Bot):
    # Определяем тип чата
    scope = (
        BotCommandScopeAllGroupChats()
        if message.chat.type in ["group", "supergroup"]
        else BotCommandScopeDefault()
    )

    commands = await bot.get_my_commands(scope=scope)

    if not commands:
        await message.answer("Нет доступных команд.")
        return

    help_text = "📋 Доступные команды:\n\n"
    for cmd in commands:
        help_text += f"/{cmd.command} — {cmd.description}\n"

    await message.answer(help_text)

