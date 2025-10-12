# utils/commands.py

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    # BotCommandScopeDefault,
    BotCommandScopeAllGroupChats,
    BotCommandScopeAllPrivateChats
)

async def setup_bot_commands(bot: Bot):
    # Команды для личных сообщений (юзеры)
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запустить бота"),
            # BotCommand(command="status", description="Проверить ограничения"),
            # BotCommand(command="help", description="Справка по командам"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )

    # Команды для всех групп (админы)
    await bot.set_my_commands(
        commands=[
            # BotCommand(command="start", description="Запустить бота"),
            BotCommand(command="status", description="Проверить ограничения"),
            BotCommand(command="ban", description="Забанить пользователя"),
            BotCommand(command="unban", description="Разбанить пользователя"),
            BotCommand(command="mute", description="Выдать мут"),
            BotCommand(command="unmute", description="Снять мут"),
            BotCommand(command="help", description="Справка по командам"),
        ],
        scope=BotCommandScopeAllGroupChats()
    )

