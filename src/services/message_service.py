from aiogram.types import InputMediaPhoto, CallbackQuery
from aiogram.types.input_file import FSInputFile
from aiogram.exceptions import TelegramBadRequest
import json

from src.keyboards.main_menu import get_main_keyboard
from src.utils.helpers import handle_bot_user, get_keyboard_for_category
from src.utils.categories import CategoryInfo, CATEGORIES, START_INFO
from src.services.state_manager import StateManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_fresh_menu(bot, user_id, info: CategoryInfo, keyboard):
    image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
    text_msg = await bot.send_message(chat_id=user_id, text=info.text, reply_markup=keyboard)

    state = StateManager(user_id)
    await state.save_state(
        image_message_id=image_msg.message_id,
        menu_message_id=text_msg.message_id,
        last_text=info.text,
        last_image=info.image,
        last_keyboard=json.dumps(keyboard.model_dump())
    )

    logger.info(f"[menu] Sent fresh menu to user {user_id}")
    return image_msg, text_msg


async def _process_category_selection(bot, user_id, info: CategoryInfo, disabled_category=None):
    state = StateManager(user_id)
    state_data = await state.get_state()

    image_msg_id = state_data.get("image_message_id", 0)
    text_msg_id = state_data.get("menu_message_id", 0)

    prev_text = state_data.get("last_text", "")
    prev_image = state_data.get("last_image", "")
    prev_keyboard = state_data.get("last_keyboard", "")

    keyboard = get_keyboard_for_category(info, disabled_category)
    keyboard_str = json.dumps(keyboard.model_dump())

    if image_msg_id and info.image != prev_image:
        try:
            await bot.edit_message_media(
                chat_id=user_id,
                message_id=image_msg_id,
                media=InputMediaPhoto(media=FSInputFile(info.image))
            )
            logger.info(f"[image] Updated for user {user_id}")
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                logger.debug(f"[image] Not modified for user {user_id}")
            else:
                logger.warning(f"Failed to edit image for user {user_id}: {e}")
    else:
        logger.debug(f"[image] Skipped update for user {user_id} (same image)")

    if text_msg_id and (info.text != prev_text or keyboard_str != prev_keyboard):
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
                logger.debug(f"[text] Not modified for user {user_id}")
            else:
                logger.warning(f"Failed to edit text for user {user_id}: {e}")
    else:
        logger.debug(f"[text] Skipped update for user {user_id} (same text and keyboard)")

    if not image_msg_id or not text_msg_id:
        await send_fresh_menu(bot, user_id, info, keyboard)
    else:
        await state.save_state(
            last_text=info.text,
            last_image=info.image,
            last_keyboard=keyboard_str
        )


async def handle_category_selection(callback: CallbackQuery, data: str):
    if await handle_bot_user(callback):
        return
    await _process_category_selection(callback.message.bot, callback.from_user.id, CATEGORIES[data], disabled_category=data)
    await callback.answer()


async def handle_category_other(callback: CallbackQuery):
    if await handle_bot_user(callback):
        return
    await _process_category_selection(callback.message.bot, callback.from_user.id, CATEGORIES["Другое"])
    await callback.answer()


async def handle_back_to_main(callback: CallbackQuery):
    if await handle_bot_user(callback):
        return

    user_id = callback.from_user.id
    state = StateManager(user_id)
    state_data = await state.get_state()

    ack_msg_id = state_data.get("ack_message_id", 0)

    if ack_msg_id:
        try:
            await callback.bot.delete_message(chat_id=user_id, message_id=ack_msg_id)
            await state.save_state(ack_message_id=0)
            logger.info(f"[ack] Deleted ack message {ack_msg_id} for user {user_id}")
        except Exception as e:
            logger.warning(f"[ack] Failed to delete message {ack_msg_id} for user {user_id}: {e}")

    image_msg_id = state_data.get("image_message_id", 0)
    text_msg_id = state_data.get("menu_message_id", 0)

    info = CategoryInfo(
        image=START_INFO.image,
        text=START_INFO.text.format(full_name=callback.from_user.full_name or "друг")
    )
    keyboard = get_main_keyboard()

    if image_msg_id and text_msg_id:
        try:
            await callback.bot.edit_message_media(
                chat_id=user_id,
                message_id=image_msg_id,
                media=InputMediaPhoto(media=FSInputFile(info.image))
            )
            await callback.bot.edit_message_text(
                chat_id=user_id,
                message_id=text_msg_id,
                text=info.text,
                reply_markup=keyboard
            )
            await state.save_state(
                last_text=info.text,
                last_image=info.image,
                last_keyboard=json.dumps(keyboard.model_dump())
            )
            logger.info(f"[main] Restored main menu for user {user_id}")
            await callback.answer()
            return
        except Exception as e:
            logger.warning(f"[main] Failed to edit main menu: {e}")

        for msg_id, label in [(image_msg_id, "image"), (text_msg_id, "text")]:
            if msg_id:
                try:
                    await callback.bot.delete_message(chat_id=user_id, message_id=msg_id)
                    logger.info(f"[main] Deleted {label} message {msg_id} for user {user_id}")
                except Exception as del_e:
                    logger.warning(f"[main] Failed to delete {label} message {msg_id}: {del_e}")

    await send_fresh_menu(callback.bot, user_id, info, keyboard)
    await callback.answer()