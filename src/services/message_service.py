from aiogram.types import InputMediaPhoto
from aiogram.types.input_file import FSInputFile
from aiogram.exceptions import TelegramBadRequest
import json
import logging

from src.utils.helpers import safe_decode, save_menu_message_ids, get_user_state, get_keyboard_for_category
from src.utils.categories import CategoryInfo, CATEGORIES

from src.utils.media_utils import save_state

logger = logging.getLogger(__name__)

async def update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category):
    state = await get_user_state(user_id)
    prev_text = safe_decode(state.get("last_text", ""))
    prev_image = safe_decode(state.get("last_image", ""))
    prev_keyboard = safe_decode(state.get("last_keyboard", ""))

    keyboard = get_keyboard_for_category(info, disabled_category)
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


async def handle_category_selection(callback, data: str):
    user_id = callback.from_user.id
    bot = callback.message.bot
    info = CATEGORIES[data]
    state = await get_user_state(user_id)
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
            reply_markup=get_keyboard_for_category(info, disabled_category=data)
        )
        await save_menu_message_ids(user_id, image_msg.message_id, text_msg.message_id)

    await callback.answer()


async def handle_category_other(callback):
    user_id = callback.from_user.id
    info = CATEGORIES["Другое"]
    state = await get_user_state(user_id)
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))
    await update_category_messages(callback.message.bot, user_id, image_msg_id, text_msg_id, info, disabled_category=None)
    await callback.answer()



async def handle_back_to_main(callback):
    user_id = callback.from_user.id
    full_name = callback.from_user.full_name or "друг"
    
    start_info = CATEGORIES.get("start")
    if not start_info:
        start_info = CategoryInfo(
            image="assets/images/welcome.jpg",
            text="Привет, {full_name}! Добро пожаловать!"
        )
    
    info = CategoryInfo(
        image=start_info.image,
        text=start_info.text.format(full_name=full_name)
    )

    state = await get_user_state(user_id)
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    await update_category_messages(callback.message.bot, user_id, image_msg_id, text_msg_id, info, disabled_category=None)
    await callback.answer()