from aiogram.types import Message, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.state import user_feedback_waiting
from src.keyboard import get_reply_to_user_keyboard
from src.config import GROUP_CHAT_ID

from src.logger import setup_logger

logger = setup_logger(__name__)
async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_feedback_waiting:
        logger.info(f"Received feedback message from user {user_id} but no feedback expected")
        return

    feedback = user_feedback_waiting.pop(user_id)
    text = (
        f"Новое обращение от @{message.from_user.username or message.from_user.full_name}:\n"
        f"Категория: {feedback.get('type')}\n\n{message.text}"
    )

    logger.info(f"Sending feedback message to support group {GROUP_CHAT_ID} from user {user_id}")

    try:
        await message.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            reply_markup=get_reply_to_user_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Failed to send message to support group: {e}")

    if (msg_id := feedback.get("prompt_message_id")):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
        except Exception as e:
            logger.warning(f"Failed to delete prompt message: {e}")

    try:
        await message.delete()
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    ack_caption = "Спасибо! Твое сообщение отправлено в службу поддержки."
    ack_photo = FSInputFile("images/other.webp")
    back_btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )

    if (menu_id := feedback.get("menu_message_id")):
        try:
            await message.bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=menu_id,
                media=InputMediaPhoto(media=ack_photo, caption=ack_caption),
                reply_markup=back_btn
            )
            return
        except Exception as e:
            logger.warning(f"Failed to edit menu message: {e}")

    await message.answer_photo(photo=ack_photo, caption=ack_caption, reply_markup=back_btn)
