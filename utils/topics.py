# utils/topics.py

from aiogram.types import Message
from utils.logger import get_logger

# Маршрутизация новостей по ключевым словам
# Ключ — thread_id, значение — список ключевых слов (в любом регистре)

TOPIC_KEYWORDS = {
    24851: ["#юмор", "#хобби", "#отдых"],  # Юмор/Хобби/Отдых
    24852: ["#радбез", "#радиационнаябезопасность"],  # Радиационная безопасность
    24853: ["#соут", "#льготы", "#пенсия"],  # СОУТ/Льготы/Пенсия
    24854: ["#оборудование", "#аппараты"],  # Аппараты/Оборудование/Ремонт
    24855: ["#правила", "#навигация", "#важно"],  # Правила и навигация
    24857: ["#образование", "#курсы", "#студентам"],  # Образование/Курсы/Студентам
    24858: ["#сп", "#по", "#soft"],  # Системы планирования
    24869: ["#клинреки", "#фракционирование", "#QUANTEC"],  # Клинические рекомендации
    24870: ["#дозиметрия", "#гарантиякачества"],  # Дозиметрия/Гарантия качества
    34319: ["#вакансия", "#работа"],  # Вакансии/Резюме/Практика
    39883: ["#аккредитация", "#нмо"],  # Аккредитация
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

