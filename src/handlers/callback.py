from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.types.input_file import FSInputFile

from src.keyboard import (
    get_main_keyboard,
    get_submenu_keyboard,
    get_identity_choice_keyboard
)
from src.utils.media_utils import save_feedback_state, send_or_edit_media
from src.utils.logger import setup_logger
from src.services.redis_client import redis_client, can_create_new_feedback
from src.utils.categories import CATEGORIES, CATEGORIES_LIST

logger = setup_logger(__name__)


def safe_decode(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value


async def callback_handler(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    logger.info(f"Callback received from user {user_id} with data: {data}")

    async def save_menu_id(msg):
        await save_feedback_state(user_id, menu_message_id=msg.message_id)
        logger.info(f"Menu message id={msg.message_id} saved for user {user_id}")

    if data.startswith("reply_to_user:"):
        try:
            target_user_id = int(data.split(":", 1)[1])
            await redis_client.set(f"admin_replying:{user_id}", target_user_id, ex=1800)

            new_text = callback.message.text + "\n\nНапишите ответ для пользователя и я его отправлю"
            await callback.message.edit_text(new_text)

            logger.info(f"Admin {user_id} replying to user {target_user_id}")
        except ValueError:
            logger.error(f"Invalid user ID in reply_to_user: {data}")
            await callback.answer("Некорректный ID", show_alert=True)
        return

    if data == "back_to_main":
        msg = await send_or_edit_media(
            callback.message,
            CATEGORIES["Другое"].image,
            f"Привет, {callback.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
            get_main_keyboard()
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    if data == "ignore":
        await callback.answer("Вы уже здесь", show_alert=True)
        logger.info(f"User {user_id} pressed ignore")
        return

    if data in ["Проблемы с техникой", "Обратная связь"]:
        if not await can_create_new_feedback(user_id):
            await callback.answer(
                "❗️ У вас уже есть открытое обращение. Дождитесь ответа перед созданием нового. ❗️",
                show_alert=True
            )
            logger.info(f"User {user_id} attempted to start new feedback while blocked")
            return

        await redis_client.set(f"feedback_type:{user_id}", data, ex=300)

        msg = await send_or_edit_media(
            callback.message,
            CATEGORIES.get(data, CATEGORIES["Другое"]).image,
            "Хочешь остаться анонимом или указать своё имя?",
            get_identity_choice_keyboard()
        )
        await save_feedback_state(user_id, menu_message_id=msg.message_id)
        await callback.answer()
        return

    if data in ["send_anonymous", "send_named"]:
        feedback_type = await redis_client.get(f"feedback_type:{user_id}")
        if not feedback_type:
            await callback.answer("Что-то пошло не так. Попробуй ещё раз.", show_alert=True)
            return

        decoded_type = safe_decode(feedback_type)
        is_named = data == "send_named"

        await save_feedback_state(user_id, type=decoded_type, is_named=is_named)

        image = CATEGORIES.get(decoded_type, CATEGORIES["Другое"]).image

        await callback.message.edit_media(
            media=InputMediaPhoto(
                media=FSInputFile(image),
                caption=f"Опиши проблему по теме '{decoded_type}':"
            ),
            reply_markup=None
        )

        await save_feedback_state(user_id, prompt_message_id=callback.message.message_id)
        logger.info(f"Feedback prompt sent to user {user_id} (named={is_named}) for type {decoded_type}")
        await callback.answer()
        return

    if data == "Другое":
        info = CATEGORIES["Другое"]
        msg = await send_or_edit_media(
            callback.message,
            info.image,
            info.text,
            get_submenu_keyboard("Другое")
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    if data in CATEGORIES_LIST:
        info = CATEGORIES[data]
        msg = await send_or_edit_media(
            callback.message,
            info.image,
            info.text,
            get_main_keyboard(disabled_category=data)
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    logger.warning(f"Unknown callback data received: {data}")
    await callback.answer("Неизвестная команда", show_alert=True)
