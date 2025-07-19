from aiogram.types import CallbackQuery, InputMediaPhoto
from aiogram.types.input_file import FSInputFile
from aiogram.exceptions import TelegramBadRequest  
import json

from src.keyboard import (
    get_main_keyboard,
    get_submenu_keyboard,
    get_identity_choice_keyboard
)
from src.utils.media_utils import save_state, send_or_edit_media  
from src.utils.logger import setup_logger
from src.services.redis_client import redis_client, can_create_new_feedback
from src.utils.categories import CategoryInfo, CATEGORIES, CATEGORIES_LIST, START_INFO

from src.handlers.feedback import send_feedback_prompt  

logger = setup_logger(__name__)

def safe_decode(value):
    return value.decode("utf-8") if isinstance(value, bytes) else value

async def update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category):
    state = await redis_client.hgetall(f"user_state:{user_id}")
    prev_text = safe_decode(state.get("last_text", ""))
    prev_image = safe_decode(state.get("last_image", ""))
    prev_keyboard = safe_decode(state.get("last_keyboard", ""))

    if info == CATEGORIES["Другое"]:
        keyboard = get_submenu_keyboard("Другое")
    else:
        keyboard = get_main_keyboard(disabled_category)
    keyboard_str = json.dumps(keyboard.model_dump())

    if info.image != prev_image:
        try:
            await bot.edit_message_media(
                chat_id=user_id,
                message_id=image_msg_id,
                media=InputMediaPhoto(media=FSInputFile(info.image))
            )
            logger.info(f"[image] Updated for user {user_id}")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.info(f"[image] Not modified for user {user_id}")
            else:
                logger.warning(f"Failed to edit image for user {user_id}: {e}")
    else:
        logger.info(f"[image] Skipped update for user {user_id} (same)")

    if info.text != prev_text or keyboard_str != prev_keyboard:
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=text_msg_id,
                text=info.text,
                reply_markup=keyboard
            )
            logger.info(f"[text] Updated for user {user_id}")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.info(f"[text] Not modified for user {user_id}")
            else:
                logger.warning(f"Failed to edit text for user {user_id}: {e}")
    else:
        logger.info(f"[text] Skipped update for user {user_id} (same)")

    await save_state(user_id,
        last_text=info.text,
        last_image=info.image,
        last_keyboard=keyboard_str
    )

async def callback_handler(callback: CallbackQuery):
    user = callback.from_user
    if user.is_bot:
        logger.warning(f"Ignoring callback from bot {user.id}")
        await callback.answer("Боты не могут использовать этого бота", show_alert=True)
        return
    
    data = callback.data
    user_id = user.id
    bot = callback.message.bot
    logger.info(f"Callback received from user {user_id} with data: {data}")

    async def save_menu_ids(image_id=None, text_id=None):
        mapping = {}
        if image_id:
            mapping["image_message_id"] = image_id
        if text_id:
            mapping["menu_message_id"] = text_id
        if mapping:
            await save_state(user_id, **mapping)
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
        full_name = callback.from_user.full_name or "друг"
        info = CategoryInfo(
            image=START_INFO.image,
            text=START_INFO.text.format(full_name=full_name)
        )
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
            callback,
            CATEGORIES.get(data, CATEGORIES["Другое"]).image,
            "Хочешь остаться анонимом или указать своё?",
            get_identity_choice_keyboard()
        )
        await save_state(user_id, menu_message_id=msg.message_id)
        await callback.answer()
        return

    if data in ["send_anonymous", "send_named"]:
        feedback_type = await redis_client.get(f"feedback_type:{user_id}")
        if not feedback_type:
            await callback.answer("Что-то пошло не так. Попробуй ещё раз.", show_alert=True)
            return

        decoded_type = safe_decode(feedback_type)
        is_named = data == "send_named"
        await save_state(user_id, type=decoded_type, is_named=is_named)

        await send_feedback_prompt(bot, user_id, decoded_type, is_named)

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
