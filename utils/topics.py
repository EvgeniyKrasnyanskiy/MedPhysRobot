# utils/topics.py

from aiogram.types import Message
from utils.logger import get_logger

# Маршрутизация новостей по ключевым словам
# Ключ — thread_id, значение — список ключевых слов (в любом регистре)

TOPIC_KEYWORDS = {
    39883: ["#аккредитация", "#нмо"],          # Аккредитация
    34319: ["#вакансия", "#работа"],           # Вакансии/Резюме/Практика
    24854: ["#оборудование", "#аппараты"],     # Аппараты/Оборудование/Ремонт
    24857: ["#образование", "#курсы", "#студентам"],  # Образование/Курсы/Студентам
}

logger = get_logger("topics")

def resolve_topic_id_by_keywords(message: Message) -> int | None:
    """
    Возвращает thread_id по ключевым словам.
    Если ключевых слов нет → возвращает None (значит, уйдёт в General).
    """
    text = (message.text or "") + (message.caption or "")
    lowered_text = text.lower()

    for thread_id, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            if keyword.lower() in lowered_text:
                logger.info(f"[TOPIC] Ключ '{keyword}' → thread_id={thread_id}")
                return thread_id

    logger.info("[TOPIC] Ключевых слов не найдено → отправляем в General (thread_id=None)")
    return None

