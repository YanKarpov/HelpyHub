import asyncio
from aiogram.types import Message, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboard import get_reply_to_user_keyboard
from src.utils.config import GROUP_CHAT_ID
from src.utils.logger import setup_logger
from src.services.redis_client import redis_client, can_create_new_feedback, lock_feedback
from src.services.google_sheets import append_feedback_to_sheet
from src.utils.categories import (
    FEEDBACK_NOTIFICATION_TEMPLATE,
    ACKNOWLEDGMENT_CAPTION,
    ACKNOWLEDGMENT_IMAGE_PATH,
    CATEGORIES,
)
from src.utils.media_utils import save_state  

logger = setup_logger(__name__)


async def send_feedback_prompt(bot, user_id, feedback_type, is_named):
    info = CATEGORIES.get(feedback_type, CATEGORIES["Другое"])
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
                text=f"Опиши проблему по теме '{feedback_type}':",
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
        text_msg = await bot.send_message(
            chat_id=user_id,
            text=f"Опиши проблему по теме '{feedback_type}':"
        )
        # Сохраняем оба id и prompt_message_id одним вызовом
        await save_state(user_id,
                         image_message_id=image_msg.message_id,
                         menu_message_id=text_msg.message_id,
                         prompt_message_id=text_msg.message_id)

    logger.info(f"Feedback prompt sent to user {user_id} (named={is_named}) for type {feedback_type}")


async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    feedback_key = f"user_state:{user_id}"  # обновлённый ключ prefix!

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

    username = message.from_user.username or ""
    full_name = message.from_user.full_name
    sender_display_name = f"@{username}" if (is_named and username) else (full_name if is_named else "Анонимус")

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

    if prompt_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=int(prompt_message_id))
        except Exception as e:
            logger.warning(f"Failed to delete prompt message: {e}")

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    ack_caption = ACKNOWLEDGMENT_CAPTION
    ack_photo = FSInputFile(ACKNOWLEDGMENT_IMAGE_PATH)
    back_btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )

    if menu_message_id:
        try:
            await message.bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=int(menu_message_id),
                media=InputMediaPhoto(media=ack_photo, caption=ack_caption),
                reply_markup=back_btn
            )
            return
        except Exception as e:
            logger.warning(f"Failed to edit menu message: {e}")

    await message.answer_photo(photo=ack_photo, caption=ack_caption, reply_markup=back_btn)
