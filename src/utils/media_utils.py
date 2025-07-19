from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto
from src.services.redis_client import redis_client, USER_STATE_KEY
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def save_state(user_id: int, key_prefix: str = USER_STATE_KEY, **kwargs):
    for k, v in kwargs.items():
        logger.debug(f"Saving {k} = {v} for user {user_id} under {key_prefix}")
    key = key_prefix.format(user_id=user_id)
    str_mapping = {k: str(v) for k, v in kwargs.items()}
    await redis_client.hset(key, mapping=str_mapping)
    await redis_client.expire(key, 3600)


async def send_or_edit_media(message_or_cb, photo_path, photo_caption, text, reply_markup):
    user_id = message_or_cb.from_user.id
    bot = message_or_cb.bot

    if message_or_cb.from_user.is_bot:
        raise ValueError("Cannot send message to bot user")

    state_key = USER_STATE_KEY.format(user_id=user_id)
    state = await redis_client.hgetall(state_key)

    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    if image_msg_id > 1000000 or text_msg_id > 1000000:
        image_msg_id, text_msg_id = 0, 0

    try:
        if image_msg_id and text_msg_id:
            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=image_msg_id,
                    media=InputMediaPhoto(media=FSInputFile(photo_path), caption=photo_caption)
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=text_msg_id,
                    text=text,
                    reply_markup=reply_markup
                )
            except TelegramBadRequest as e:
                if "message is not modified" not in str(e):
                    raise

            return

        raise ValueError("No saved message IDs for editing")

    except Exception:
        image_msg = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(photo_path),
            caption=photo_caption
        )
        text_msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )
        await save_state(user_id, image_message_id=image_msg.message_id, menu_message_id=text_msg.message_id)
