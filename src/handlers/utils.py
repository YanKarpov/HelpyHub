from aiogram.types import FSInputFile, InputMediaPhoto
from src.services.redis_client import redis_client

from src.logger import setup_logger

logger = setup_logger(__name__)


async def save_feedback_state(user_id: int, **kwargs):
    key = f"feedback_state:{user_id}"
    await redis_client.hset(key, mapping=kwargs)
    await redis_client.expire(key, 3600)  
    state = await redis_client.hgetall(key)
    logger.info(f"Feedback state updated for user {user_id}: {state}")

async def send_or_edit_media(message_or_cb, photo_path, caption, reply_markup):
    media = InputMediaPhoto(media=FSInputFile(photo_path), caption=caption)
    try:
        await message_or_cb.edit_reply_markup(reply_markup=None)
        await message_or_cb.edit_media(media=media, reply_markup=reply_markup)
        logger.info(f"Edited media message id={message_or_cb.message_id}")
        return message_or_cb
    except Exception as e:
        logger.warning(f"edit_media failed: {e}, sending new photo instead")
        sent = await message_or_cb.answer_photo(
            photo=FSInputFile(photo_path), caption=caption, reply_markup=reply_markup
        )
        return sent
