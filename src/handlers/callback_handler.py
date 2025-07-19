from aiogram.types import CallbackQuery
import logging

from src.handlers.feedback import (
    handle_feedback_choice,      
    handle_send_identity_choice   
)
from src.handlers.admin_reply import handle_admin_reply  
from src.services.message_service import (
    handle_category_selection,
    handle_category_other,
    handle_back_to_main
)
from src.utils.helpers import handle_bot_user

logger = logging.getLogger(__name__)

async def callback_handler(callback: CallbackQuery):
    if await handle_bot_user(callback):
        return

    data = callback.data
    user_id = callback.from_user.id
    logger.info(f"Callback received from user {user_id} with data: {data}")

    if data.startswith("reply_to_user:"):
        await handle_admin_reply(callback, data)
        return

    if data == "back_to_main":
        await handle_back_to_main(callback)
        return

    if data == "ignore":
        await callback.answer("Вы уже здесь", show_alert=True)
        logger.info(f"User {user_id} pressed ignore")
        return

    if data in ["Проблемы с техникой", "Обратная связь"]:
        await handle_feedback_choice(callback, data)
        return

    if data in ["send_anonymous", "send_named"]:
        await handle_send_identity_choice(callback, data)
        return

    if data == "Другое":
        await handle_category_other(callback)
        return

    from src.utils.categories import CATEGORIES_LIST
    if data in CATEGORIES_LIST:
        await handle_category_selection(callback, data)
        return

    logger.warning(f"Unknown callback data received: {data}")
    await callback.answer("Неизвестная команда", show_alert=True)
