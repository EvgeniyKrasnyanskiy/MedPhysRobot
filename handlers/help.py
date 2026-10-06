# handlers/help.py

from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command
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
        help_text = (
            "🤖 <b>MedPhysRobot — Справка для администраторов</b>\n\n"
            "💬 <b>1. Ответ пользователю:</b>\n"
            "• Нажмите <b>Reply (Ответить)</b> на любое сообщение бота в этой группе.\n"
            "• Поддерживаются: текст, альбомы фото, пакеты файлов, документы, голосовые и кружочки.\n"
            "• ✏️ <b>Синхронизация правок:</b> если вы отредактируете свой ответ здесь, бот обновит его у пользователя.\n\n"
            "📢 <b>2. Публикация и автодублирование новостей:</b>\n"
            "• <code>/channel</code> (в ответ на сообщение) — опубликовать пост в канал.\n"
            "  └ <i>Автодублирование:</i> любой пост канала (отправленный ботом или вручную) <b>автоматически дублируется в PRO-группу</b> в нужный топик по ключевым словам!\n"
            "• <code>/channel [ссылка или ID]</code> — отредактировать пост в канале. <i>Правка синхронно обновится и в PRO-группе!</i>\n"
            "• <code>/pro</code> (в ответ на сообщение) — прямая отправка сообщения в PRO-группу в топик по ключевым словам.\n"
            "• <code>/pro [ссылка или ID]</code> — отредактировать отправленное ботом сообщение в PRO-группе!\n\n"
            "🛡️ <b>3. Модерация (в ответ на сообщение):</b>\n"
            "• <code>/mute [время]</code> — ограничить отправку сообщений боту:\n"
            "  └ <code>/mute 30m</code> (минуты), <code>/mute 2h</code> (часы, дефолт 2h), <code>/mute 1d</code> (дни), <code>/mute 1w</code> (недели).\n"
            "• <code>/unmute</code> — досрочно снять мут.\n"
            "• <code>/ban</code> — заблокировать пользователя навсегда.\n"
            "• <code>/unban</code> — разблокировать пользователя.\n"
            "• <code>/status</code> — проверить ограничения автора сообщения.\n\n"
            "🙏 <b>4. Благодарности (в PRO-группе):</b>\n"
            "• <code>/top10</code> — показать ТОП-10 по благодарностям (исчезает через 1 мин).\n"
            "• Очки начисляются автоматически при ответе со словом «спасибо» или эмодзи 🙏, 🤝, ❤️, 💐.\n\n"
            "ℹ️ <i>Команды без reply или с неверными аргументами автоматически удаляются через пару секунд для чистоты чата.</i>"
        )
    else:
        help_text = (
            "🤖 <b>MedPhysRobot — Связь с администрацией</b>\n\n"
            "Здесь вы можете задать вопрос, предложить материал или новость для публикации.\n\n"
            "📨 <b>Как отправить обращение:</b>\n"
            "• Просто отправьте текст или файлы (документы, PDF, фото, видео) прямо в этот чат.\n"
            "• Бот доставит ваше сообщение дежурным администраторам.\n"
            "• Ответ администраторов придёт вам прямо в этот диалог.\n\n"
            "✏️ <i>Если вы допустили неточность, отредактируйте ваше сообщение — бот автоматически обновит его у администраторов!</i>\n\n"
            "📋 <b>Команды:</b>\n"
            "/start — перезапустить бота\n"
            "/help — показать эту справку"
        )

    await message.answer(help_text, parse_mode="HTML")


