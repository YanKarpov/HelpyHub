import asyncio
from aiogram.types import Message, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboard import get_reply_to_user_keyboard
from src.utils.config import GROUP_CHAT_ID
from src.utils.logger import setup_logger
from src.services.redis_client import redis_client, can_create_new_feedback, lock_feedback
from src.services.google_sheets import append_feedback_to_sheet
from src.utils.categories import (
    FEEDBACK_NOTIFICATION_TEMPLATE,
    URGENT_FEEDBACK_NOTIFICATION_TEMPLATE,  
    ACKNOWLEDGMENT_CAPTION,
    ACKNOWLEDGMENT_IMAGE_PATH,
    CATEGORIES,
    SUBCATEGORIES
)
from src.utils.media_utils import save_state  
from src.utils.media_utils import send_or_edit_media, save_state
from src.keyboard import get_identity_choice_keyboard
from aiogram.types import CallbackQuery
from src.utils.helpers import safe_decode, save_state

logger = setup_logger(__name__)


async def send_feedback_prompt(bot, user_id, feedback_type, is_named):
    # Определяем, откуда брать инфо и текст
    if feedback_type in SUBCATEGORIES:
        info = SUBCATEGORIES[feedback_type]
        message_text = info.text  # просто текст из подкатегорий
    elif feedback_type in CATEGORIES:
        info = CATEGORIES[feedback_type]
        if feedback_type == "Другое":
            message_text = info.text
        else:
            message_text = f"Опиши проблему по теме '{feedback_type}':\n\n{info.text}"
    else:
        info = CATEGORIES["Другое"]
        message_text = info.text

    state = await redis_client.hgetall(f"user_state:{user_id}")
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    logger.info(f"Current saved state for user {user_id}: image_msg_id={image_msg_id}, text_msg_id={text_msg_id}")

    if image_msg_id and text_msg_id:
        logger.info(f"Editing existing messages for user {user_id}: image_msg_id={image_msg_id}, text_msg_id={text_msg_id}")
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
                reply_markup=None
            )
            await save_state(user_id, prompt_message_id=text_msg_id)
        except Exception as e:
            logger.warning(f"Failed to edit feedback text for user {user_id}: {e}")
    else:
        image_msg = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(info.image)
        )
        logger.info(f"Sent new image message to user {user_id}: message_id={image_msg.message_id}")

        text_msg = await bot.send_message(
            chat_id=user_id,
            text=message_text
        )
        logger.info(f"Sent new text message to user {user_id}: message_id={text_msg.message_id}")

        await save_state(
            user_id,
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id,
            prompt_message_id=text_msg.message_id
        )

    logger.info(f"Feedback prompt sent to user {user_id} (named={is_named}) for type {feedback_type}")


async def handle_feedback_choice(callback: CallbackQuery, data: str):
    user_id = callback.from_user.id
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
        photo_caption="",  
        text="Хочешь остаться анонимом или указать своё?",
        reply_markup=get_identity_choice_keyboard()
    )
    await save_state(user_id, menu_message_id=msg.message_id)
    await callback.answer()


async def handle_send_identity_choice(callback: CallbackQuery, data: str):
    user_id = callback.from_user.id
    bot = callback.message.bot

    feedback_type = await redis_client.get(f"feedback_type:{user_id}")
    if not feedback_type:
        await callback.answer("Что-то пошло не так. Попробуй ещё раз.", show_alert=True)
        return

    decoded_type = safe_decode(feedback_type)
    is_named = data == "send_named"
    await save_state(user_id, type=decoded_type, is_named=is_named)

    await send_feedback_prompt(bot, user_id, decoded_type, is_named)
    await callback.answer()


async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    feedback_key = f"user_state:{user_id}"

    feedback = await redis_client.hgetall(feedback_key)
    if not feedback:
        logger.info(f"User {user_id} sent a message, but feedback not expected. Ignoring.")
        return

    if not await can_create_new_feedback(user_id):
        await message.answer("❗️ У вас уже есть открытое обращение. Пожалуйста, дождитесь ответа на предыдущее перед созданием нового.")
        return

    await lock_feedback(user_id)

    def decode(value):
        return value.decode('utf-8') if isinstance(value, bytes) else value

    category = decode(feedback.get('type', 'Не указана'))
    is_named = decode(feedback.get('is_named', 'False')) == 'True'
    prompt_message_id = decode(feedback.get('prompt_message_id')) if feedback.get('prompt_message_id') else None
    menu_message_id = decode(feedback.get('menu_message_id')) if feedback.get('menu_message_id') else None
    image_message_id = decode(feedback.get('image_message_id')) if feedback.get('image_message_id') else None

    logger.info(f"Feedback state for user {user_id}: prompt_message_id={prompt_message_id}, menu_message_id={menu_message_id}, image_message_id={image_message_id}")

    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    sender_display_name = f"@{username}" if (is_named and username) else (full_name if is_named else "Анонимус")

    # Используем разные шаблоны в зависимости от категории
    if category == "Срочная помощь":
        text = URGENT_FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            message_text=message.text,
        )
    else:
        text = FEEDBACK_NOTIFICATION_TEMPLATE.format(
            sender_display_name=sender_display_name,
            category=category,
            message_text=message.text,
        )

    try:
        await message.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            reply_markup=get_reply_to_user_keyboard(user_id)
        )
        logger.info(f"Sent feedback message to support group {GROUP_CHAT_ID} from user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send message to support group: {e}")

    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            append_feedback_to_sheet,
            user_id,
            sender_display_name,
            category,
            message.text,
            "",  # answer_text
            "",  # admin_id
            "",  # admin_username
            "Ожидает ответа",
            is_named
        )
        logger.info(f"Feedback from user {user_id} saved to Google Sheets")
    except Exception as e:
        logger.error(f"Failed to save feedback to Google Sheets: {e}")

    try:
        await redis_client.delete(feedback_key)
    except Exception as e:
        logger.warning(f"Failed to delete feedback key from Redis: {e}")

    # Удаляем prompt_message_id
    if prompt_message_id:
        logger.info(f"Deleting prompt message for user {user_id}: message_id={prompt_message_id}")
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=int(prompt_message_id))
        except Exception as e:
            logger.warning(f"Failed to delete prompt message: {e}")

    # Удаляем menu_message_id, если он отличается от prompt_message_id
    if menu_message_id and menu_message_id != prompt_message_id:
        logger.info(f"Trying to delete old menu message: chat_id={user_id}, message_id={menu_message_id}")
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=int(menu_message_id))
        except Exception as e:
            logger.warning(f"Failed to delete old menu message: {e}")

    # Удаляем image_message_id, если он не совпадает с другими
    if image_message_id and image_message_id not in [prompt_message_id, menu_message_id]:
        logger.info(f"Trying to delete image message: chat_id={user_id}, message_id={image_message_id}")
        try:
            await message.bot.delete_message(chat_id=user_id, message_id=int(image_message_id))
        except Exception as e:
            logger.warning(f"Failed to delete image message: {e}")

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    ack_caption = ACKNOWLEDGMENT_CAPTION
    ack_photo = FSInputFile(ACKNOWLEDGMENT_IMAGE_PATH)
    back_btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )

    ack_message = await message.answer_photo(photo=ack_photo, caption=ack_caption, reply_markup=back_btn)

    await save_state(
        user_id,
        menu_message_id=ack_message.message_id,
        image_message_id=0  
    )
