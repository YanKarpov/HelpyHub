from aiogram.types import InputMediaPhoto, CallbackQuery
from aiogram.types.input_file import FSInputFile
from aiogram.exceptions import TelegramBadRequest
import json

from src.utils.helpers import handle_bot_user, get_keyboard_for_category
from src.templates.categories import CategoryInfo, CATEGORIES
from src.services.state_manager import StateManager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def send_fresh_menu(bot, user_id, info: CategoryInfo, keyboard):
    """Отправка нового меню пользователю с изображением и текстом"""
    image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
    text_msg = await bot.send_message(chat_id=user_id, text=info.text, reply_markup=keyboard)

    # Сохраняем текущее состояние меню
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
    """Обработка выбора категории: обновление изображения, текста и клавиатуры"""
    state = StateManager(user_id)
    state_data = await state.get_state()

    image_msg_id = state_data.get("image_message_id", 0)
    text_msg_id = state_data.get("menu_message_id", 0)
    prev_text = state_data.get("last_text", "")
    prev_image = state_data.get("last_image", "")
    prev_keyboard = state_data.get("last_keyboard", "")

    # Генерация клавиатуры с учетом отключенной категории
    keyboard = get_keyboard_for_category(info, disabled_category)
    keyboard_str = json.dumps(keyboard.model_dump())

    # Обновляем изображение, если оно изменилось
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
                logger.warning(f"[image] Failed to edit image for user {user_id}: {e}")
    else:
        logger.debug(f"[image] Skipped update for user {user_id} (same image)")

    # Обновляем текст и клавиатуру, если они изменились
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
                logger.warning(f"[text] Failed to edit text for user {user_id}: {e}")
    else:
        logger.debug(f"[text] Skipped update for user {user_id} (same text and keyboard)")

    # Если сообщений нет, отправляем новое меню
    if not image_msg_id or not text_msg_id:
        await send_fresh_menu(bot, user_id, info, keyboard)
    else:
        # Сохраняем обновленное состояние
        await state.save_state(
            last_text=info.text,
            last_image=info.image,
            last_keyboard=keyboard_str
        )


async def handle_category_selection(callback: CallbackQuery, data: str):
    """Обработка выбора конкретной категории пользователем"""
    if await handle_bot_user(callback):
        return
    await _process_category_selection(
        callback.message.bot,
        callback.from_user.id,
        CATEGORIES[data],
        disabled_category=data
    )
    await callback.answer()


async def handle_category_other(callback: CallbackQuery):
    """Обработка выбора категории 'Другое'"""
    if await handle_bot_user(callback):
        return
    await _process_category_selection(
        callback.message.bot,
        callback.from_user.id,
        CATEGORIES["Другое"]
    )
    await callback.answer()
