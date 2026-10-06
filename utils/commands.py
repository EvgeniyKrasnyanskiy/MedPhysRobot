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
            BotCommand(command="help", description="Показать справку по командам"),
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
            BotCommand(command="pro", description="Переслать в PRO-группу (быстро)"),
            BotCommand(command="channel", description="В канал (или /channel [ссылка])"),
            BotCommand(command="send_to_pro_group", description="Переслать в PRO-группу (полная)"),
            BotCommand(command="send_to_channel", description="Переслать в канал (полная)"),
            BotCommand(command="mute", description="Выдать мут (1m, 2h, 3d, 1w)"),
            BotCommand(command="unmute", description="Снять мут"),
            BotCommand(command="ban", description="Забанить пользователя"),
            BotCommand(command="unban", description="Разбанить пользователя"),
            BotCommand(command="status", description="Проверить статус пользователя"),
            BotCommand(command="help", description="Подробная справка по функциям"),
        ],
        scope=BotCommandScopeChat(chat_id=ADMIN_GROUP_ID)
    )
