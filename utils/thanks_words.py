# utils/thanks_words.py

import logging
from utils.paths import THANKS_WORDS_PATH

logger = logging.getLogger("thanks")

def load_thanks_words(path=THANKS_WORDS_PATH) -> set[str]:
    try:
        with open(path, encoding="utf-8") as f:
            words = set(line.strip().lower() for line in f if line.strip())
            logger.info(f"[THANKS] Загружено {len(words)} слов благодарности из {path}")
            return words
    except Exception as e:
        logger.warning(f"[THANKS] Не удалось загрузить слова благодарности: {e}")
        return {"спасибо", "благодарю", "мерси", "thanks", "thx"}
