from aiogram.types import InputMediaPhoto
from aiogram.types.input_file import FSInputFile
from aiogram.exceptions import TelegramBadRequest
import json
from aiogram.types import CallbackQuery
from src.keyboard import get_main_keyboard

from src.utils.helpers import safe_decode, save_menu_message_ids, get_user_state, get_keyboard_for_category
from src.utils.categories import CategoryInfo, CATEGORIES, START_INFO

from src.utils.media_utils import save_state
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def update_category_messages(bot, user_id, image_msg_id, text_msg_id, info, disabled_category):
    # Используем константу USER_STATE_KEY для ключа
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

    # Используем get_user_state - он уже берет правильный ключ
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


async def handle_back_to_main(callback: CallbackQuery):
    user_id = callback.from_user.id
    logger.info(f"User {user_id} нажал кнопку 'Назад'")

    state = await get_user_state(user_id)
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    info = CategoryInfo(
        image=START_INFO.image,
        text=START_INFO.text.format(full_name=callback.from_user.full_name or "друг")
    )

    bot = callback.bot
    keyboard = get_main_keyboard()

    logger.info(f"BackToMain for user {user_id}: image_msg_id={image_msg_id}, text_msg_id={text_msg_id}")
    logger.info(f"BackToMain content image: {info.image}")
    logger.info(f"BackToMain content text: {info.text}")
    logger.info(f"BackToMain keyboard: {keyboard}")

    if not image_msg_id or not text_msg_id:
        logger.info(f"No previous messages found. Sending new welcome screen to user {user_id}")
        image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
        text_msg = await bot.send_message(chat_id=user_id, text=info.text, reply_markup=keyboard)

        await save_state(
            user_id,
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id
        )
        await callback.answer()
        logger.info(f"Sent new messages and updated state for user {user_id}")
        return

    try:
        await bot.edit_message_media(
            chat_id=user_id,
            message_id=image_msg_id,
            media=InputMediaPhoto(media=FSInputFile(info.image))
        )
        logger.info(f"Edited image message {image_msg_id} for user {user_id}")

        await bot.edit_message_text(
            chat_id=user_id,
            message_id=text_msg_id,
            text=info.text,
            reply_markup=keyboard
        )
        logger.info(f"Edited text message {text_msg_id} for user {user_id}")

        await callback.answer()
        return
    except Exception as e:
        logger.warning(f"Failed to edit messages for user {user_id}: {e}")

        # Удаляем старые, если редактировать не получилось
        for msg_id, label in [(image_msg_id, "image"), (text_msg_id, "text")]:
            if msg_id:
                try:
                    await bot.delete_message(chat_id=user_id, message_id=msg_id)
                    logger.info(f"Deleted old {label} message {msg_id} for user {user_id}")
                except Exception as del_e:
                    logger.warning(f"Failed to delete {label} message {msg_id} for user {user_id}: {del_e}")

        # Отправляем заново
        image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
        text_msg = await bot.send_message(chat_id=user_id, text=info.text, reply_markup=keyboard)

        await save_state(
            user_id,
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id
        )
        await callback.answer()
        logger.info(f"Sent new messages and updated state for user {user_id}")
