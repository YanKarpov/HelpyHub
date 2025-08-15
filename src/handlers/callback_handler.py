from aiogram.types import CallbackQuery
import logging

from src.handlers.feedback_handler import (
    handle_feedback_choice,
    handle_send_identity_choice
)
from src.handlers.admin.reply_handler import handle_admin_reply
from src.services.message_service import (
    handle_category_selection,
    handle_category_other,
)
from src.handlers.back_handler import back_handler  
from src.utils.helpers import handle_bot_user
from src.templates.categories import CATEGORIES_LIST

logger = logging.getLogger(__name__)

CALLBACK_ROUTES = {
    "back": (back_handler, False), 
    "ignore": (lambda cb: cb.answer("Вы уже здесь", show_alert=True), False),
    "send_named": (handle_send_identity_choice, True),
    "send_anonymous": (handle_send_identity_choice, True),
    "Другое": (handle_category_other, False),
    "Проблемы с техникой": (handle_feedback_choice, True),
    "Срочная помощь": (handle_feedback_choice, True),
    "Обратная связь": (handle_feedback_choice, True),
}

async def callback_handler(callback: CallbackQuery):
    if await handle_bot_user(callback):
        return

    data = callback.data
    user_id = callback.from_user.id
    logger.info(f"Callback received from user {user_id} with data: {data}")

    if data.startswith("reply_to_user:"):
        await handle_admin_reply(callback, data)
        return

    if data in CALLBACK_ROUTES:
        handler, needs_data = CALLBACK_ROUTES[data]
        if needs_data:
            await handler(callback, data)
        else:
            await handler(callback)
        return

    if data in CATEGORIES_LIST:
        await handle_category_selection(callback, data)
        return

    logger.warning(f"Unknown callback data received: {data}")
    await callback.answer("Неизвестная команда", show_alert=True)
