from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
import json
from src.services.state_manager import StateManager
from src.utils.logger import setup_logger
from src.handlers.start_handler import start_handler
from src.handlers.feedback_handler import send_feedback_prompt, handle_feedback_choice
from src.utils.categories import START_INFO
from src.keyboards.main_menu import get_main_keyboard

logger = setup_logger(__name__)

async def try_edit_main_menu(bot, user_id, state_mgr, full_name):
    state = await state_mgr.get_state()

    image_msg_id = state.get("image_message_id")
    text_msg_id = state.get("menu_message_id")

    if not image_msg_id or not text_msg_id:
        return False

    photo_path = START_INFO.image
    caption_text = START_INFO.text.format(full_name=full_name or "друг")
    keyboard = get_main_keyboard()

    try:
        await bot.edit_message_media(
            chat_id=user_id,
            message_id=image_msg_id,
            media=InputMediaPhoto(media=FSInputFile(photo_path))
        )
        await bot.edit_message_text(
            chat_id=user_id,
            message_id=text_msg_id,
            text=caption_text,
            reply_markup=keyboard
        )
        await state_mgr.save_state(
            last_text=caption_text,
            last_image=photo_path,
            last_keyboard=json.dumps(keyboard.model_dump())
        )
        logger.info(f"[main] Отредактировано главное меню для пользователя {user_id}")
        return True
    except Exception as e:
        logger.warning(f"[main] Не удалось отредактировать главное меню для пользователя {user_id}: {e}")
        try:
            if image_msg_id:
                await bot.delete_message(chat_id=user_id, message_id=image_msg_id)
            if text_msg_id:
                await bot.delete_message(chat_id=user_id, message_id=text_msg_id)
        except Exception:
            pass
        return False


async def back_handler(callback: CallbackQuery):
    """
    Единый обработчик кнопки 'Назад'.
    Достаёт предыдущий экран из StateManager и отрисовывает его.
    """
    user_id = callback.from_user.id
    state_mgr = StateManager(user_id)

    screen, params = await state_mgr.go_back()

    if not screen:
        logger.info(f"User {user_id} нажал 'Назад', но стек пуст.")
        await callback.answer("Нет предыдущего экрана", show_alert=True)
        return

    logger.info(f"User {user_id} возвращается на экран '{screen}' с params={params}")

    # Рендерим нужный экран
    if screen == "main":
        edited = await try_edit_main_menu(callback.bot, user_id, state_mgr, callback.from_user.full_name)
        if not edited:
            await start_handler(callback.message)

    elif screen == "identity_choice":
        category = params.get("category", "Другое")
        await handle_feedback_choice(callback, category)

    elif screen == "feedback_prompt":
        feedback_type = params.get("feedback_type", "Другое")
        await send_feedback_prompt(callback.bot, user_id, feedback_type)

    elif screen == "feedback_ack":
        await start_handler(callback.message)

    else:
        logger.warning(f"Неизвестный экран '{screen}', возвращаем в main")
        await state_mgr.reset_nav()
        await start_handler(callback.message)

    await callback.answer()
