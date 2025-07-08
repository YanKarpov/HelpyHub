from aiogram.types import Message
from src.redis_client import redis_client
from src.logger import setup_logger
from src.google_sheets import update_feedback_in_sheet
import asyncio

logger = setup_logger(__name__)

async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    logger.info(f"admin_reply_text_handler called from user {admin_id}")

    user_id = await redis_client.get(f"admin_replying:{admin_id}")
    if user_id is None:
        logger.info(f"Message from user {admin_id} ignored in admin reply handler (not replying now)")
        return

    user_id = user_id.decode() if isinstance(user_id, bytes) else user_id

    logger.info(f"Admin {admin_id} is replying to user {user_id} with text: {message.text!r}")

    try:
        await message.bot.send_message(chat_id=int(user_id), text=f"Ответ от службы поддержки:\n\n{message.text}")
        await message.reply("Сообщение успешно отправлено пользователю.")
        admin_username = message.from_user.username or ""

        await asyncio.get_event_loop().run_in_executor(
            None,
            update_feedback_in_sheet,
            int(user_id),
            message.text,
            str(admin_id),
            admin_username,
            "Отвечено"
        )

        await redis_client.delete(f"admin_replying:{admin_id}")
    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}")
        await message.reply(f"Ошибка отправки: {e}")
