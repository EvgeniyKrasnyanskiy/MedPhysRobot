# handlers/status.py
# Note: The /status command for ADMIN_GROUP_ID is handled in moderation.py.
# This module is kept for potential future per-user status checks outside admin group.

from aiogram import Router
from utils.logger import get_logger

logger = get_logger("status")
router = Router()
