from src.utils.logger import setup_logger
logger = setup_logger(__name__)


def safe_str(value) -> str:
    """
    Универсальное приведение значения к строке.
    """
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def get_keyboard_for_category(info, disabled_category):
    """
    Возвращает соответствующую клавиатуру по категории.
    (Импорт CATEGORIES и клавиатур оставить в том модуле, где будет использоваться)
    """
    from src.utils.categories import CATEGORIES
    from src.keyboards.main_menu import get_main_keyboard, get_submenu_keyboard

    if info == CATEGORIES["Другое"]:
        return get_submenu_keyboard("Другое")
    return get_main_keyboard(disabled_category)


async def handle_bot_user(callback):
    """
    Проверяет, является ли пользователь ботом, и при необходимости
    отправляет предупреждение.
    """
    from src.utils.logger import setup_logger
    logger = setup_logger(__name__)

    user = callback.from_user
    if user.is_bot:
        logger.warning(f"Ignoring callback from bot {user.id}")
        await callback.answer("Боты не могут использовать этого бота", show_alert=True)
        return True
    return False
