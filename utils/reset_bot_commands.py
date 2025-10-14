# utils/reset_bot_commands.py

import asyncio
from aiogram import Bot
from aiogram.types import BotCommandScopeDefault, BotCommandScopeAllGroupChats, BotCommandScopeAllPrivateChats
from utils.config import BOT_TOKEN

async def reset():
    bot = Bot(token=BOT_TOKEN)
    await bot.delete_my_commands(scope=BotCommandScopeDefault())
    await bot.delete_my_commands(scope=BotCommandScopeAllGroupChats())
    await bot.delete_my_commands(scope=BotCommandScopeAllPrivateChats())
    print("✅ Команды сброшены")

if __name__ == "__main__":
    asyncio.run(reset())
