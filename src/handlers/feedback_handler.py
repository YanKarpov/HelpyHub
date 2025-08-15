import asyncio
from aiogram.types import (
    Message, FSInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
)
from src.keyboards.main_menu import back_button
from src.keyboards.identity import get_identity_choice_keyboard
from src.keyboards.reply import get_reply_to_user_keyboard
from src.utils.config import GROUP_CHAT_ID, SUPPORT_THREAD_ID
from src.utils.logger import setup_logger
from src.services.state_manager import StateManager
from src.utils.categories import (
    FEEDBACK_NOTIFICATION_TEMPLATE,
    URGENT_FEEDBACK_NOTIFICATION_TEMPLATE,
    ACKNOWLEDGMENT_CAPTION,
    ACKNOWLEDGMENT_IMAGE_PATH,
    CATEGORIES,
    SUBCATEGORIES
)
from src.utils.media_utils import send_or_edit_media
from src.utils.helpers import handle_bot_user
from src.utils.filter_profanity import ProfanityFilter
from src.services.google_sheets import append_feedback_to_sheet

logger = setup_logger(__name__)

async def send_feedback_prompt(bot, user_id, feedback_type):
    state_mgr = StateManager(user_id)

    if feedback_type in SUBCATEGORIES:
        info = SUBCATEGORIES[feedback_type]
        message_text = info.text
    elif feedback_type in CATEGORIES:
        info = CATEGORIES[feedback_type]
        message_text = (
            info.text if feedback_type == "Другое"
            else f"Опиши проблему по теме '{feedback_type}':\n\n{info.text}"
        )
    else:
        info = CATEGORIES["Другое"]
        message_text = info.text

    state = await state_mgr.get_state()
    menu_msg_id = state.get("menu_message_id", 0)
    image_msg_id = state.get("image_message_id", 0)

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])

    # Редактируем изображение, если есть
    if image_msg_id:
        try:
            await bot.edit_message_media(
                chat_id=user_id,
                message_id=image_msg_id,
                media=InputMediaPhoto(media=FSInputFile(info.image))
            )
        except Exception as e:
            logger.warning(f"Failed to edit feedback image for user {user_id}: {e}")
    else:
        # Если нет старого изображения — отправляем новое
        image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
        await state_mgr.save_state(image_message_id=image_msg.message_id)

    # Редактируем текст меню
    if menu_msg_id:
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=menu_msg_id,
                text=message_text,
                reply_markup=back_kb
            )
            await state_mgr.save_state(prompt_message_id=menu_msg_id)
        except Exception as e:
            logger.warning(f"Failed to edit feedback text for user {user_id}: {e}")
            # Если редактировать не удалось, отправляем новое сообщение
            text_msg = await bot.send_message(chat_id=user_id, text=message_text, reply_markup=back_kb)
            await state_mgr.save_state(menu_message_id=text_msg.message_id, prompt_message_id=text_msg.message_id)
    else:
        text_msg = await bot.send_message(chat_id=user_id, text=message_text, reply_markup=back_kb)
        await state_mgr.save_state(menu_message_id=text_msg.message_id, prompt_message_id=text_msg.message_id)


async def handle_feedback_choice(callback: CallbackQuery, data: str):
    if await handle_bot_user(callback):
        return

    user_id = callback.from_user.id
    state_mgr = StateManager(user_id)

    if await state_mgr.is_blocked():
        await callback.answer("❌ Вы заблокированы и не можете оставлять обращения.", show_alert=True)
        return

    if not await state_mgr.can_create_feedback():
        await callback.answer(
            "❗️ У вас уже есть открытое обращение. Дождитесь ответа перед созданием нового. ❗️",
            show_alert=True
        )
        return

    await state_mgr.set_feedback_type(data, expire=300)
    await state_mgr.push_nav("identity_choice", {"category": data})

    msg = await send_or_edit_media(
        callback,
        CATEGORIES.get(data, CATEGORIES["Другое"]).image,
        photo_caption="",
        text="Хочешь остаться анонимом или указать своё?",
        reply_markup=get_identity_choice_keyboard()
    )

    if msg:
        await state_mgr.save_state(menu_message_id=msg.message_id)


async def handle_send_identity_choice(callback: CallbackQuery, data: str):
    if await handle_bot_user(callback):
        return

    user_id = callback.from_user.id
    bot = callback.message.bot
    state_mgr = StateManager(user_id)

    feedback_type = await state_mgr.get_feedback_type()
    if not feedback_type:
        await callback.answer("Что-то пошло не так. Попробуй ещё раз.", show_alert=True)
        return

    is_named = data == "send_named"
    await state_mgr.save_state(type=feedback_type, is_named=is_named)
    await state_mgr.push_nav("feedback_prompt", {"feedback_type": feedback_type})

    await send_feedback_prompt(bot, user_id, feedback_type)


async def feedback_message_handler(message: Message):
    if message.chat.type != "private":
        return

    user_id = message.from_user.id
    state_mgr = StateManager(user_id)
    feedback = await state_mgr.get_state()

    if not feedback or not feedback.get("prompt_message_id"):
        return

    if await state_mgr.is_blocked():
        await message.answer("❌ Вы заблокированы и не можете создавать обращения.")
        return

    if not await state_mgr.can_create_feedback():
        await message.answer("❗️ У вас уже есть открытое обращение. Пожалуйста, дождитесь ответа на предыдущее.")
        return

    # Получаем текст из сообщения или подписи к медиа
    text_part = message.caption if (message.photo or message.video or message.document or message.animation) else message.text
    
    # Проверяем наличие текста
    if not text_part:
        await message.answer("❌ Пожалуйста, добавьте текстовое описание к вашему обращению.")
        return

    # Проверка на мат
    try:
        ProfanityFilter().check_and_raise(text_part)
    except ValueError as e:
        await message.answer(str(e))
        return

    await state_mgr.lock_user()

    category = feedback.get('type', 'Не указана')
    is_named = feedback.get('is_named', False)
    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    sender_display_name = f"@{username}" if (is_named and username) else (full_name if is_named else "Анонимус")

    # Формируем текст уведомления
    if category == "Срочная помощь":
        notification_text = URGENT_FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            message_text=text_part
        )
    else:
        notification_text = FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            category=category,
            message_text=text_part
        )

    # Отправка в группу поддержки
    try:
        if message.photo:
            await message.bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                photo=message.photo[-1].file_id,
                caption=notification_text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                video=message.video.file_id,
                caption=notification_text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                document=message.document.file_id,
                caption=notification_text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.animation:
            await message.bot.send_animation(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                animation=message.animation.file_id,
                caption=notification_text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        else:
            await message.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                text=notification_text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
    except Exception as e:
        logger.error(f"Failed to send feedback to support: {e}")

    # Сохранение в Google Sheets (как раньше)
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            append_feedback_to_sheet,
            user_id,
            sender_display_name,
            category,
            text_part,  # Сохраняем только текст
            "", "", "",
            "Ожидает ответа",
            is_named
        )
    except Exception as e:
        logger.error(f"Failed to save to Google Sheets: {e}")

    # Очистка состояния
    await state_mgr.clear_state()

    # Удаление сообщения пользователя
    try:
        await message.delete()
    except Exception:
        pass

    # Отправка подтверждения
    ack_photo = FSInputFile(ACKNOWLEDGMENT_IMAGE_PATH)
    back_btn = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])
    
    try:
        await message.bot.send_photo(
            chat_id=user_id,
            photo=ack_photo,
            caption=ACKNOWLEDGMENT_CAPTION,
            reply_markup=back_btn
        )
    except Exception as e:
        logger.warning(f"Failed to send acknowledgment: {e}")

    await state_mgr.reset_nav()
