# handlers/help.py

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats
from utils.config import RELAY_GROUP_ID

router = Router()

@router.message(F.chat.id == RELAY_GROUP_ID, Command("help", ignore_mention=True, ignore_case=True))
async def help_command(message: Message, bot: Bot):
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

