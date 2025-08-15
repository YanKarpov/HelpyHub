from aiogram.types import CallbackQuery, Message
from src.services.state_manager import StateManager
from src.services.google_sheets import update_feedback_in_sheet
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger
from src.templates.admin_messages import (
    ADMIN_REPLY_PROMPT,
    ADMIN_REPLY_ERROR_ID,
    ADMIN_REPLY_ERROR_GENERAL,
    ADMIN_REPLY_NO_TEXT,
    ADMIN_REPLY_SUCCESS
)
import asyncio

logger = setup_logger(__name__)

async def handle_admin_reply(callback: CallbackQuery, data: str):
    admin_id = callback.from_user.id
    try:
        target_user_id = int(data.split(":", 1)[1])
        state_manager = StateManager(admin_id)
        
        await state_manager.set_admin_reply_target(target_user_id, expire=1800)
        await state_manager.save_state(admin_replying_from_chat=callback.message.chat.id)

        current_text = callback.message.text
        current_caption = callback.message.caption

        new_message = ADMIN_REPLY_PROMPT

        if current_text:
            await callback.message.edit_text(current_text + "\n\n" + new_message, reply_markup=None)
        elif current_caption:
            updated_caption = current_caption + "\n\n" + new_message
            if callback.message.photo:
                await callback.message.edit_caption(caption=updated_caption, reply_markup=None)
            elif callback.message.video:
                await callback.message.edit_caption(caption=updated_caption, reply_markup=None)
            elif callback.message.document:
                await callback.message.edit_caption(caption=updated_caption, reply_markup=None)
        else:
            await callback.message.edit_text(new_message, reply_markup=None)

        logger.info(f"Admin {admin_id} started replying to user {target_user_id} from chat {callback.message.chat.id}")

    except ValueError:
        logger.error(f"Invalid user ID in reply_to_user: {data}")
        await callback.answer(ADMIN_REPLY_ERROR_ID, show_alert=True)
    except Exception as e:
        logger.error(f"Error in handle_admin_reply: {e}", exc_info=True)
        await callback.answer(ADMIN_REPLY_ERROR_GENERAL, show_alert=True)


async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    lock_key = f"admin_reply_lock:{admin_id}"

    locked = await redis_client.set(lock_key, "1", ex=10, nx=True)
    if not locked:
        logger.info(f"Admin {admin_id} reply handler is locked, skipping duplicate message.")
        return

    state_manager = StateManager(admin_id)

    try:
        user_id = await state_manager.get_admin_reply_target()
        chat_id = await state_manager.get_state_field("admin_replying_from_chat")

        if user_id is None or chat_id is None or message.chat.id != int(chat_id):
            logger.info(f"Admin {admin_id} sent message from wrong chat ({message.chat.id}), expected {chat_id}. Ignoring.")
            return

        if not (message.text and message.text.strip()) and not (message.caption and message.caption.strip()):
            await message.reply(ADMIN_REPLY_NO_TEXT)
            return

        caption_text = f"Ответ от службы поддержки:\n\n{message.caption or message.text or ''}"

        if message.photo:
            await message.bot.send_photo(chat_id=user_id, photo=message.photo[-1].file_id, caption=caption_text)
        elif message.video:
            await message.bot.send_video(chat_id=user_id, video=message.video.file_id, caption=caption_text)
        elif message.document:
            await message.bot.send_document(chat_id=user_id, document=message.document.file_id, caption=caption_text)
        elif message.animation:
            await message.bot.send_animation(chat_id=user_id, animation=message.animation.file_id, caption=caption_text)
        else:
            await message.bot.send_message(chat_id=user_id, text=caption_text)

        await message.reply(ADMIN_REPLY_SUCCESS)

        admin_username = message.from_user.username or ""
        await asyncio.get_event_loop().run_in_executor(
            None,
            update_feedback_in_sheet,
            user_id,
            message.caption or message.text or "",
            str(admin_id),
            admin_username,
            "Вопрос закрыт"
        )

        await StateManager(user_id).unlock_feedback()
        await state_manager.delete_state_field("admin_replying_from_chat")
        await state_manager.delete_state_field("admin_replying_to")
        if hasattr(state_manager, "admin_replying_key") and state_manager.admin_replying_key:
            await redis_client.delete(state_manager.admin_replying_key)

        logger.info(f"Admin {admin_id} finished replying to user {user_id}")

    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}", exc_info=True)
        await message.reply(f"Ошибка отправки: {e}")

    finally:
        await redis_client.delete(lock_key)
