from aiogram.types import CallbackQuery
from src.services.redis_client import redis_client, USER_STATE_KEY
from src.utils.media_utils import save_state
from src.utils.categories import CATEGORIES, CategoryInfo
from src.keyboard import get_main_keyboard, get_submenu_keyboard

from src.utils.logger import setup_logger
logger = setup_logger(__name__)


async def get_user_state(user_id: int) -> dict:
    """
    Получает состояние пользователя из Redis.
    """
    key = USER_STATE_KEY.format(user_id=user_id)
    return await redis_client.hgetall(key)


def safe_str(value) -> str:
    """
    Универсальное приведение значения к строке.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


async def save_menu_message_ids(user_id: int, image_id: int = None, text_id: int = None):
    """
    Сохраняет ID сообщений меню (изображение и текст) в Redis.
    """
    mapping = {}
    if image_id is not None:
        mapping["image_message_id"] = image_id
    if text_id is not None:
        mapping["menu_message_id"] = text_id

    if mapping:
        await save_state(user_id, **mapping)


def get_keyboard_for_category(info: CategoryInfo, disabled_category: str | None):
    """
    Возвращает соответствующую клавиатуру по категории.
    """
    if info == CATEGORIES["Другое"]:
        return get_submenu_keyboard("Другое")
    return get_main_keyboard(disabled_category)


async def handle_bot_user(callback: CallbackQuery) -> bool:
    """
    Проверяет, является ли пользователь ботом, и при необходимости
    отправляет предупреждение.
    """
    user = callback.from_user
    if user.is_bot:
        logger.warning(f"Ignoring callback from bot {user.id}")
        await callback.answer("Боты не могут использовать этого бота", show_alert=True)
        return True
    return False
