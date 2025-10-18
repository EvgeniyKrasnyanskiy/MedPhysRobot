# utils/commands.py

from aiogram import Bot
from utils.config import ADMIN_GROUP_ID, MEDPHYSPRO_GROUP_ID
from aiogram.types import (
    BotCommand,
    BotCommandScopeChat,
    BotCommandScopeAllPrivateChats
)

from utils.logger import get_logger

logger = get_logger("commands")
logger.info("[COMMANDS] commands.py загружен")

async def setup_bot_commands(bot: Bot):
    # Команды для личных сообщений (юзеры)
    await bot.set_my_commands(
        commands=[
            BotCommand(command="start", description="Запустить бота"),
        ],
        scope=BotCommandScopeAllPrivateChats()
    )

    await bot.set_my_commands(
        commands=[
            BotCommand(command="top10", description="Показать ТОП-10 по благодарностям"),
        ],
        scope=BotCommandScopeChat(chat_id=MEDPHYSPRO_GROUP_ID)
    )

    # Команды для всех групп (админы)
    await bot.set_my_commands(
        commands=[
            BotCommand(command="send_to_pro_group", description="Переслать в PRO-группу"),
            BotCommand(command="ban", description="Забанить пользователя"),
            BotCommand(command="unban", description="Разбанить пользователя"),
            BotCommand(command="mute", description="Выдать мут"),
            BotCommand(command="unmute", description="Снять мут"),
            BotCommand(command="status", description="Проверить ограничения"),
            BotCommand(command="help", description="Справка по командам"),
        ],
        scope=BotCommandScopeChat(chat_id=ADMIN_GROUP_ID)
    )

