Отчет о ревью кода проекта MedPhysRobot
📊 Общая оценка проекта
Статус: 🟡 Средний уровень качества
Критичность проблем: 🟠 Есть важные проблемы
Рекомендация: Провести рефакторинг критичных участков

🔴 Критические проблемы
1. Database Connection Leaks (Утечки соединений БД)
Файлы: 
utils/db.py
, 
handlers/news_monitor.py

Серьезность: 🔴 Критично

Проблема:
В каждой функции работы с БД создается новое соединение sqlite3.connect(), но нет гарантированного закрытия при ошибках.

Примеры:

# utils/db.py:77-84
def get_user_by_forwarded(forwarded_id: int) -> int | None:
    conn = sqlite3.connect(DB_PATH)  # ← Соединение не закрывается при исключении
    cursor = conn.cursor()
    cursor.execute("SELECT...")
    result = cursor.fetchone()
    conn.close()  # ← Не выполнится при ошибке
    return result[0] if result else None
Решение:
Использовать context manager:

def get_user_by_forwarded(forwarded_id: int) -> int | None:
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT...")
        result = cursor.fetchone()
        return result[0] if result else None
Затронутые функции (22 места):

utils/db.py
: все функции (save_mapping, get_user_by_forwarded, mute_user, и т.д.)
handlers/news_monitor.py
: is_hash_already_forwarded, save_forwarded_news, get_group_msg_id, cleanup_forwarded_news
2. Race Condition в AlbumMiddleware
Файл: middlewares/album.py:28
Серьезность: 🔴 Критично

Проблема:
Проверка album[0] == event не потокобезопасна - между проверкой и вызовом handler другой поток может изменить 
album
.

if album and album[0] == event:  # ← Race condition
    data["album"] = album.copy()
    del self.albums[group_key]
Решение:
Использовать asyncio.Lock для синхронизации доступа.

3. Незащищенный доступ к атрибутам
Файл: handlers/relay.py:17, handlers/moderation.py:258
Серьезность: 🟠 Важно

Проблема:
Отсутствует проверка на None перед доступом к user.full_name.

name = f'<a href="tg://user?id={user.id}">{html.escape(user.full_name)}</a>'
Риск: AttributeError если 
user
 или user.full_name равен None.

Решение:

full_name = html.escape(user.full_name or "Unknown User")
🟡 Важные проблемы
4. Неэффективная обработка БД
Файл: 
utils/db.py

Серьезность: 🟡 Средне

Проблема:
Открытие соединения для каждого запроса вместо connection pooling.

Влияние:

Замедление работы при высоких нагрузках
Возможна блокировка SQLite при параллельных записях
Решение:

Использовать aiosqlite для асинхронных операций
Или создать connection pool
5. Отсутствие обработки ошибок при редактировании
Файл: handlers/relay.py:254-270, 281-297
Серьезность: 🟡 Средне

Проблема:
При редактировании сообщений с caption_entities может возникнуть ошибка, если entities "выходят" за границы нового текста.

Пример:

# Если добавляется "(отредактировано)\n" в начало,
# смещаются все offsets в entities!
caption=f"(отредактировано)\n{message.caption}",
caption_entities=message.caption_entities  # ← Некорректные offsets!
Решение:
Пересчитывать offset для entities:

prefix = "(отредактировано)\n"
adjusted_entities = [
    MessageEntity(
        type=e.type,
        offset=e.offset + len(prefix),
        length=e.length,
        url=e.url
    ) for e in (message.caption_entities or [])
]
6. Неконсистентная обработка пустых значений
Файл: utils/sender.py:73
Серьезность: 🟡 Средне

Проблема:

base_text = (message.caption or message.text or "") + (suffix or "")
Если message.caption = "" (пустая строка), будет использован message.text, хотя это медиа-сообщение.

Решение:

text = message.caption if message.caption is not None else (message.text or "")
base_text = text + (suffix or "")
7. Отсутствие валидации thread_id
Файл: utils/sender.py:70
Серьезность: 🟡 Средне

Проблема:
int(thread_id)
 может упасть с ValueError если thread_id некорректный.

Решение:

try:
    kwargs["message_thread_id"] = int(thread_id)
except (ValueError, TypeError):
    logger.warning(f"Invalid thread_id: {thread_id}")
🟢 Минорные проблемы и улучшения
8. Дублирование кода
Файлы: 
handlers/relay.py
, 
handlers/moderation.py

Серьезность: 🟢 Низко

Проблема:
Дублируется логика отправки медиа (InputMedia*) в разных местах.

Решение:
Вынести в отдельную функцию в 
utils/sender.py
.

9. Магические числа
Файлы: Повсюду
Серьезность: 🟢 Низко

Проблемы:

0.3 в middlewares/album.py:9 - время ожидания альбома
3, 57, 60 в 
handlers/thanks.py
 - таймауты
2, 7 в 
medphysbot.py
 - дни хранения
Решение:
Вынести в константы или конфиг.

10. Отсутствие типов в некоторых местах
Файл: handlers/thanks.py:19
Серьезность: 🟢 Низко

THANKS_WORDS = load_thanks_words()  # Нет типа
Решение:

THANKS_WORDS: set[str] = load_thanks_words()
11. Избыточное логирование
Файл: 
utils/db.py

Серьезность: 🟢 Низко

Слишком много INFO-логов, которые засоряют вывод. Рекомендуется перенести часть на DEBUG уровень.

12. Неоптимальная очистка БД
Файл: utils/db.py:235-245
Серьезность: 🟢 Низко

Проблема:
cleanup_old_mappings
 выполняет 2 отдельных DELETE-запроса.

Решение:

cursor.execute("""
    DELETE FROM relay_map WHERE timestamp < ?;
    DELETE FROM reply_map WHERE timestamp < ?
""", (cutoff, cutoff))
🛡️ Безопасность
✅ Хорошо реализовано:
HTML-экранирование для user.full_name ✅
Использование 
entities
 вместо parse_mode="HTML" для пользовательского контента ✅
Проверка прав доступа через F.chat.id ✅
⚠️ Требует внимания:
Отсутствует rate limiting для команд
Отсутствует защита от SQL injection (но используется параметризация - ОК)
BOT_TOKEN хранится в .env (хорошо), но нет проверки наличия
📈 Рекомендации по улучшению
Приоритет 1 (Критично):
✅ Рефакторинг БД: Использовать context manager для всех операций
✅ Fix Race Condition: Добавить блокировки в AlbumMiddleware
✅ Обработка None: Проверять user.full_name перед использованием
Приоритет 2 (Важно):
✅ Fix entity offsets: Пересчитывать при редактировании
✅ Асинхронная БД: Перейти на aiosqlite
✅ Валидация: Добавить try-except для 
int(thread_id)
Приоритет 3 (Желательно):
⭐ Дедупликация: Вынести общую логику отправки медиа
⭐ Константы: Вынести магические числа в config
⭐ Типизация: Добавить type hints везде
⭐ Логирование: Настроить уровни (INFO/DEBUG)
📝 Дополнительные замечания
Положительные стороны:
✅ Хорошая структура проекта (handlers, utils, middlewares)
✅ Логирование реализовано корректно
✅ Модульность кода
✅ Использование aiogram 3.x (современная версия)
Архитектурные улучшения:
Рассмотреть использование DI (Dependency Injection) для БД
Добавить unit-тесты (coverage ~0% сейчас)
Рассмотреть использование alembic для миграций БД
🎯 Итоговая оценка
Критерий	Оценка
Безопасность	🟡 7/10
Надежность	🟠 6/10
Производительность	🟡 7/10
Поддерживаемость	🟢 8/10
Качество кода	🟡 7/10
Общая оценка: 🟡 7/10 - Хороший код с потенциалом для улучшения