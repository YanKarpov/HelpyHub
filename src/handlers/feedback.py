from aiogram.types import Message, FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboard import get_reply_to_user_keyboard
from src.config import GROUP_CHAT_ID
from src.logger import setup_logger
from src.redis_client import redis_client  

logger = setup_logger(__name__)

async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    feedback_key = f"feedback_state:{user_id}"  # заменить здесь

    feedback = await redis_client.hgetall(feedback_key)
    if not feedback:
        logger.info(f"Received feedback message from user {user_id} but no feedback expected")
        return

    await redis_client.delete(feedback_key)

    text = (
        f"Новое обращение от Анонимуса:\n"
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

    prompt_message_id = feedback.get("prompt_message_id")
    if prompt_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=int(prompt_message_id))
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

    menu_message_id = feedback.get("menu_message_id")
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
