from aiogram.types import CallbackQuery, Message
from src.services.state_manager import StateManager
from src.utils.logger import setup_logger
from src.services.google_sheets import update_feedback_in_sheet
import asyncio

logger = setup_logger(__name__)

async def handle_admin_reply(callback: CallbackQuery, data: str):
    user_id = callback.from_user.id
    try:
        target_user_id = int(data.split(":", 1)[1])
        state_manager = StateManager(user_id)
        
        await state_manager.save_state_with_ttl(
            field="admin_replying_to",
            value=str(target_user_id),
            ttl=1800
        )
        
        new_text = callback.message.text + "\n\nНапишите ответ для пользователя и я его отправлю"
        await callback.message.edit_text(new_text)
        logger.info(f"Admin {user_id} replying to user {target_user_id}")
    except ValueError:
        logger.error(f"Invalid user ID in reply_to_user: {data}")
        await callback.answer("Некорректный ID", show_alert=True)


async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    logger.info(f"admin_reply_text_handler called from user {admin_id}")

    state_manager = StateManager(admin_id)
    user_id = await state_manager.get_state_field("admin_replying_to")
    
    if user_id is None:
        logger.info(f"Message from user {admin_id} ignored in admin reply handler (not replying now)")
        return

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
            "Вопрос закрыт"
        )

        # Разблокируем feedback для пользователя
        user_state_manager = StateManager(int(user_id))
        await user_state_manager.unlock_feedback()  # Используем совместимый метод
        
        # Удаляем информацию о текущем ответе
        await state_manager.delete_state_field("admin_replying_to")

    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}")
        await message.reply(f"Ошибка отправки: {e}")