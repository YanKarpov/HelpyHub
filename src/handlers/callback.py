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


async def update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category):
    try:
        await bot.edit_message_media(
            chat_id=user_id,
            message_id=image_msg_id,
            media=InputMediaPhoto(media=FSInputFile(info.image))
        )
    except Exception as e:
        logger.warning(f"Failed to edit image for user {user_id}: {e}")

    try:
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=text_msg_id,
            text=info.text,
            reply_markup=get_main_keyboard(disabled_category)
        )
    except Exception as e:
        logger.warning(f"Failed to edit text for user {user_id}: {e}")


async def callback_handler(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    bot = callback.message.bot
    logger.info(f"Callback received from user {user_id} with data: {data}")

    async def save_menu_ids(image_id=None, text_id=None):
        mapping = {}
        if image_id:
            mapping["image_message_id"] = image_id
        if text_id:
            mapping["menu_message_id"] = text_id
        if mapping:
            await save_feedback_state(user_id, **mapping)
            logger.info(f"Saved message IDs for user {user_id}: {mapping}")

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
        info = CATEGORIES["Другое"]
        state = await redis_client.hgetall(f"user_state:{user_id}")
        image_msg_id = int(state.get("image_message_id", 0))
        text_msg_id = int(state.get("menu_message_id", 0))
        await update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category=None)
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

        info = CATEGORIES.get(decoded_type, CATEGORIES["Другое"])
        state = await redis_client.hgetall(f"user_state:{user_id}")
        image_msg_id = int(state.get("image_message_id", 0))
        text_msg_id = int(state.get("menu_message_id", 0))

        if image_msg_id and text_msg_id:
            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=image_msg_id,
                    media=InputMediaPhoto(media=FSInputFile(info.image))
                )
            except Exception as e:
                logger.warning(f"Failed to edit feedback image for user {user_id}: {e}")

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=text_msg_id,
                    text=f"Опиши проблему по теме '{decoded_type}':",
                    reply_markup=None
                )
                await save_feedback_state(user_id, prompt_message_id=text_msg_id)
            except Exception as e:
                logger.warning(f"Failed to edit feedback text for user {user_id}: {e}")
        else:
            image_msg = await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(info.image)
            )
            text_msg = await bot.send_message(
                chat_id=user_id,
                text=f"Опиши проблему по теме '{decoded_type}':"
            )
            await save_menu_ids(image_msg.message_id, text_msg.message_id)
            await save_feedback_state(user_id, prompt_message_id=text_msg.message_id)

        logger.info(f"Feedback prompt sent to user {user_id} (named={is_named}) for type {decoded_type}")
        await callback.answer()
        return

    if data == "Другое":
        info = CATEGORIES["Другое"]
        state = await redis_client.hgetall(f"user_state:{user_id}")
        image_msg_id = int(state.get("image_message_id", 0))
        text_msg_id = int(state.get("menu_message_id", 0))
        await update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category=None)
        await callback.answer()
        return

    if data in CATEGORIES_LIST:
        info = CATEGORIES[data]
        state = await redis_client.hgetall(f"user_state:{user_id}")
        image_msg_id = int(state.get("image_message_id", 0))
        text_msg_id = int(state.get("menu_message_id", 0))

        if image_msg_id and text_msg_id:
            await update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category=data)
        else:
            image_msg = await bot.send_photo(
                chat_id=user_id,
                photo=FSInputFile(info.image)
            )
            text_msg = await bot.send_message(
                chat_id=user_id,
                text=info.text,
                reply_markup=get_main_keyboard(disabled_category=data)
            )
            await save_menu_ids(image_msg.message_id, text_msg.message_id)

        await callback.answer()
        return

    logger.warning(f"Unknown callback data received: {data}")
    await callback.answer("Неизвестная команда", show_alert=True)
