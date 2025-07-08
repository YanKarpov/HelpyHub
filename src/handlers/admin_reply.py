from aiogram.types import Message
from src.redis_client import redis_client
from src.logger import setup_logger

logger = setup_logger(__name__)

async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    logger.info(f"admin_reply_text_handler called from user {admin_id}")

    user_id = await redis_client.get(f"admin_replying:{admin_id}")
    if user_id is None:
        logger.info(f"Message from user {admin_id} ignored in admin reply handler (not replying now)")
        return

    logger.info(f"Admin {admin_id} is replying to user {user_id} with text: {message.text!r}")

    try:
        await message.bot.send_message(chat_id=int(user_id), text=f"Ответ от службы поддержки:\n\n{message.text}")
        await message.reply("Сообщение успешно отправлено пользователю.")
        await redis_client.delete(f"admin_replying:{admin_id}")
    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}")
        await message.reply(f"Ошибка отправки: {e}")
