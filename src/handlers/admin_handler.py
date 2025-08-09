from aiogram.types import CallbackQuery, Message
from src.services.state_manager import StateManager
from src.utils.logger import setup_logger
from src.services.google_sheets import update_feedback_in_sheet
from src.services.redis_client import redis_client

import asyncio

logger = setup_logger(__name__)

async def handle_admin_reply(callback: CallbackQuery, data: str):
    admin_id = callback.from_user.id
    try:
        target_user_id = int(data.split(":", 1)[1])
        state_manager = StateManager(admin_id)
        
        await state_manager.set_admin_reply_target(target_user_id=target_user_id, expire=1800)
        
        new_text = callback.message.text + "\n\nНапишите ответ для пользователя и я его отправлю"
        await callback.message.edit_text(new_text)
        
        logger.info(f"Admin {admin_id} started replying to user {target_user_id}")
    except ValueError:
        logger.error(f"Invalid user ID in reply_to_user: {data}")
        await callback.answer("Некорректный ID", show_alert=True)


async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    lock_key = f"admin_reply_lock:{admin_id}"

    locked = await redis_client.set(lock_key, "1", ex=10, nx=True)
    if not locked:
        logger.info(f"Admin {admin_id} reply handler is locked, skipping duplicate message.")
        return

    state_manager = StateManager(admin_id)

    try:
        user_id = await state_manager.get_state_field("admin_replying_to")
        if user_id is None:
            logger.info(f"Admin {admin_id} sent message but is not in reply mode, ignoring.")
            return

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
            "Вопрос закрыт"
        )

        user_state_manager = StateManager(int(user_id))
        await user_state_manager.unlock_feedback()

        await state_manager.delete_state_field("admin_replying_to")

        logger.info(f"Admin {admin_id} finished replying to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}")
        await message.reply(f"Ошибка отправки: {e}")

    finally:
        await redis_client.delete(lock_key)
