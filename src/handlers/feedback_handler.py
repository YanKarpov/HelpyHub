import asyncio
from aiogram.types import (
    Message, FSInputFile, InputMediaPhoto,
    InlineKeyboardMarkup, CallbackQuery
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
    SUBCATEGORIES,
    PRINT_REQUEST_NOTIFICATION_TEMPLATE
)
from src.utils.media_utils import send_or_edit_media
from src.utils.helpers import handle_bot_user
from src.utils.filter_profanity import ProfanityFilter
from src.services.google_sheets import append_feedback_to_sheet
from src.utils.feedback_validator import FeedbackValidator 

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
    image_msg_id = state.get("image_message_id", 0)
    text_msg_id = state.get("menu_message_id", 0)

    logger.info(f"Current saved state for user {user_id}: image_msg_id={image_msg_id}, text_msg_id={text_msg_id}")

    back_kb = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])  # Кнопка назад

    if image_msg_id and text_msg_id:
        logger.info(f"Editing existing messages for user {user_id}")
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
                text=message_text,
                reply_markup=back_kb  # Добавляем кнопку назад
            )
            await state_mgr.save_state(prompt_message_id=text_msg_id)
        except Exception as e:
            logger.warning(f"Failed to edit feedback text for user {user_id}: {e}")
    else:
        image_msg = await bot.send_photo(chat_id=user_id, photo=FSInputFile(info.image))
        text_msg = await bot.send_message(chat_id=user_id, text=message_text, reply_markup=back_kb)  # с кнопкой назад

        await state_mgr.save_state(
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id,
            prompt_message_id=text_msg.message_id
        )

    logger.info(f"Feedback prompt sent to user {user_id} for type {feedback_type}")


async def handle_feedback_choice(callback: CallbackQuery, data: str):
    if await handle_bot_user(callback):
        return

    user_id = callback.from_user.id
    state_mgr = StateManager(user_id)

    if await state_mgr.is_blocked():
        await callback.answer("❌ Вы заблокированы и не можете оставлять обращения.", show_alert=True)
        logger.info(f"Blocked user {user_id} попытался выбрать категорию.")
        return

    if not await state_mgr.can_create_feedback():
        await callback.answer(
            "❗️ У вас уже есть открытое обращение. Дождитесь ответа перед созданием нового. ❗️",
            show_alert=True
        )
        logger.info(f"User {user_id} attempted to start new feedback while locked")
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
    else:
        logger.warning(f"msg is None — не сохраняю message_id для user_id={callback.from_user.id}")

    await callback.answer()


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
    await callback.answer()


async def handle_print_request(callback: CallbackQuery, data: str):
    if await handle_bot_user(callback):
        return

    user_id = callback.from_user.id
    bot = callback.message.bot
    state_mgr = StateManager(user_id)

    if await state_mgr.is_blocked():
        await callback.answer("❌ Вы заблокированы и не можете отправлять запросы.", show_alert=True)
        return

    if not await state_mgr.can_create_feedback():
        await callback.answer(
            "❗️ У вас уже есть открытое обращение. Дождитесь ответа перед созданием нового. ❗️",
            show_alert=True
        )
        return

    feedback_type = data  
    await state_mgr.set_feedback_type(feedback_type, expire=300)
    await state_mgr.save_state(type=feedback_type, is_named=True)
    await state_mgr.push_nav("feedback_prompt", {"feedback_type": feedback_type})

    await send_feedback_prompt(bot, user_id, feedback_type)
    await callback.answer()


async def feedback_message_handler(message: Message):
    if message.chat.type != "private":
        logger.debug(f"Ignoring message from chat_id={message.chat.id}, type={message.chat.type}")
        return
    
    if not (message.text and message.text.strip()) and not (message.caption and message.caption.strip()):
        await message.answer("❗️ Пожалуйста, добавьте текстовое описание к вашему обращению.")
        return

    # --- проверка длины текста через валидатор ---
    length_error = FeedbackValidator.check_length(message)
    if length_error:
        await message.answer(length_error)
        return

    user_id = message.from_user.id
    state_mgr = StateManager(user_id)
    feedback = await state_mgr.get_state()

    if not feedback or not feedback.get("prompt_message_id"):
        logger.info(f"User {user_id} sent a message, but feedback prompt not expected. Ignoring.")
        return

    if await state_mgr.is_blocked():
        await message.answer("❌ Вы заблокированы и не можете создавать обращения.")
        logger.info(f"Blocked user {user_id} попытался отправить обращение")
        return

    if not await state_mgr.can_create_feedback():
        await message.answer(
            "❗️ У вас уже есть открытое обращение. Пожалуйста, дождитесь ответа на предыдущее перед созданием нового."
        )
        return

    try:
        ProfanityFilter().check_and_raise(message.text or "")
    except ValueError as e:
        await message.answer(str(e))
        return

    await state_mgr.lock_user()

    category = feedback.get('type', 'Не указана')
    is_named = feedback.get('is_named', False)
    prompt_message_id = feedback.get('prompt_message_id')
    menu_message_id = feedback.get('menu_message_id')
    image_message_id = feedback.get('image_message_id')

    logger.info(
        f"Feedback state for user {user_id}: "
        f"prompt_message_id={prompt_message_id}, menu_message_id={menu_message_id}, image_message_id={image_message_id}"
    )

    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    sender_display_name = (
        f"@{username}" if (is_named and username) else (full_name if is_named else "Анонимус")
    )

    # Определяем текст сообщения: если есть текст, берём его, иначе подпись медиа
    message_text = message.text or message.caption or ""

    if category == "Срочная помощь":
        text = URGENT_FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            message_text=message_text
        )
    elif category == "Запрос на печать":
        text = PRINT_REQUEST_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            message_text=message_text
        )
    else:
        text = FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            category=category,
            message_text=message_text
        )


    # --- отправка в группу с медиа ---
    try:
        if message.photo:
            await message.bot.send_photo(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                photo=message.photo[-1].file_id,
                caption=text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.document:
            await message.bot.send_document(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                document=message.document.file_id,
                caption=text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.video:
            await message.bot.send_video(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                video=message.video.file_id,
                caption=text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        elif message.animation:  # если есть гифка
            await message.bot.send_animation(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                animation=message.animation.file_id,
                caption=text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        else:
            await message.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                message_thread_id=SUPPORT_THREAD_ID,
                text=text,
                reply_markup=get_reply_to_user_keyboard(user_id)
            )
        logger.info(f"Sent feedback message to support group {GROUP_CHAT_ID} from user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send message to support group: {e}")

    # --- запись в Google Sheets ---
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            append_feedback_to_sheet,
            user_id,
            sender_display_name,
            category,
            message.text or "[медиа без текста]",
            "", "", "",
            "Ожидает ответа",
            is_named
        )
        logger.info(f"Feedback from user {user_id} saved to Google Sheets")
    except Exception as e:
        logger.error(f"Failed to save feedback to Google Sheets: {e}")

    await state_mgr.clear_state()

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    # Показываем экран подтверждения
    ack_photo = FSInputFile(ACKNOWLEDGMENT_IMAGE_PATH)
    back_btn = InlineKeyboardMarkup(inline_keyboard=[[back_button()]])

    try:
        if image_message_id:
            await message.bot.edit_message_media(
                chat_id=user_id,
                message_id=image_message_id,
                media=InputMediaPhoto(media=ack_photo)
            )

        if menu_message_id:
            await message.bot.edit_message_text(
                chat_id=user_id,
                message_id=menu_message_id,
                text=ACKNOWLEDGMENT_CAPTION,
                reply_markup=back_btn
            )

            await state_mgr.save_state(
                image_message_id=image_message_id,
                menu_message_id=menu_message_id,
                last_text=ACKNOWLEDGMENT_CAPTION,
                last_image=ACKNOWLEDGMENT_IMAGE_PATH,
                last_keyboard=back_btn
            )
    except Exception as e:
        logger.warning(f"Failed to edit existing messages: {e}")
        ack_message = await message.answer_photo(
            photo=ack_photo,
            caption=ACKNOWLEDGMENT_CAPTION,
            reply_markup=back_btn
        )
        await state_mgr.save_state(
            image_message_id=ack_message.message_id,
            menu_message_id=ack_message.message_id,
            last_text=ACKNOWLEDGMENT_CAPTION,
            last_image=ACKNOWLEDGMENT_IMAGE_PATH,
            last_keyboard=back_btn
        )

    await state_mgr.reset_nav()
