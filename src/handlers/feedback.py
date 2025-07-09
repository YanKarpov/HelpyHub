import asyncio
from aiogram.types import Message, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboard import get_reply_to_user_keyboard
from src.config import GROUP_CHAT_ID
from src.logger import setup_logger
from src.services.redis_client import redis_client
from src.services.google_sheets import append_feedback_to_sheet

logger = setup_logger(__name__)


async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    feedback_key = f"feedback_state:{user_id}"

    # Декодер значений из Redis
    def decode(value):
        if isinstance(value, bytes):
            return value.decode('utf-8')
        return value

    # Получаем сохранённое состояние
    feedback = await redis_client.hgetall(feedback_key)
    if not feedback:
        logger.info(f"Received feedback message from user {user_id} but no feedback expected")
        return

    category = decode(feedback.get('type', 'Не указана'))
    is_named = decode(feedback.get('is_named', 'False')) == 'True'
    prompt_message_id = decode(feedback.get('prompt_message_id')) if feedback.get('prompt_message_id') else None
    menu_message_id = decode(feedback.get('menu_message_id')) if feedback.get('menu_message_id') else None

    username = message.from_user.username or ""
    full_name = message.from_user.full_name

    # Определяем, как отображать отправителя
    if is_named:
        sender_display_name = f"@{username}" if username else full_name
    else:
        sender_display_name = "Анонимус"

    text = (
        f"Новое обращение от {sender_display_name}:\n"
        f"Категория: {category}\n\n{message.text}"
    )

    # Отправка сообщения в группу
    try:
        await message.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            reply_markup=get_reply_to_user_keyboard(user_id)
        )
        logger.info(f"Sent feedback message to support group {GROUP_CHAT_ID} from user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send message to support group: {e}")

    # Сохраняем в Google Таблицу
    try:
        await asyncio.get_event_loop().run_in_executor(
            None,
            append_feedback_to_sheet,
            user_id,
            sender_display_name,
            category,
            message.text,
            "",          # answer_text
            "",          # admin_id
            "",          # admin_username
            "Ожидает ответа",
            is_named    
        )
        logger.info(f"Feedback from user {user_id} saved to Google Sheets")
    except Exception as e:
        logger.error(f"Failed to save feedback to Google Sheets: {e}")

    # Удаляем сохранённое состояние
    try:
        await redis_client.delete(feedback_key)
    except Exception as e:
        logger.warning(f"Failed to delete feedback key from Redis: {e}")

    # Удаляем промпт
    if prompt_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=int(prompt_message_id))
        except Exception as e:
            logger.warning(f"Failed to delete prompt message: {e}")

    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    # Показываем пользователю сообщение об успешной отправке
    ack_caption = "Спасибо! Твое сообщение отправлено в службу поддержки."
    ack_photo = FSInputFile("images/other.webp")
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
