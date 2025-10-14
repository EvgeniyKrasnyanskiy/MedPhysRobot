# utils/paths.py

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RESOURCES_DIR = BASE_DIR / "resources"

THANKS_WORDS_PATH = RESOURCES_DIR / "thanks_words.txt"

LOGS_DIR = BASE_DIR / "logs"
LOG_FILE_PATH = LOGS_DIR / "medphysbot.log"
