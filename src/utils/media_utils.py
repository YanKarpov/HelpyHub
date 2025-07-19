from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def save_state(user_id: int, key_prefix: str = "user_state", **kwargs):
    for k, v in kwargs.items():
        logger.debug(f"Saving {k} = {v} for user {user_id} under {key_prefix}")
    key = f"{key_prefix}:{user_id}"
    str_mapping = {k: str(v) for k, v in kwargs.items()}
    await redis_client.hset(key, mapping=str_mapping)
    await redis_client.expire(key, 3600)


async def send_or_edit_media(message_or_cb, photo_path, text, reply_markup):
    logger.warning(f"[DEBUG] send_or_edit_media: from_user.id={message_or_cb.from_user.id}, is_bot={message_or_cb.from_user.is_bot}")
    logger.warning(f"[DEBUG] send_or_edit_media: type={type(message_or_cb)}")

    user_id = message_or_cb.from_user.id
    bot = message_or_cb.bot

    # Защита от попытки отправить сообщение другому боту
    if message_or_cb.from_user.is_bot:
        logger.warning(f"Attempt to send message to bot user_id={user_id}, aborting")
        raise ValueError("Cannot send message to bot user")

    state = await redis_client.hgetall(f"user_state:{user_id}")
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    # Проверяем, что message_id выглядят адекватно (Telegram message_id обычно не превышает нескольких сотен тысяч)
    if image_msg_id > 1000000 or text_msg_id > 1000000:
        logger.warning(
            f"Suspicious message IDs for user {user_id}: "
            f"image_msg_id={image_msg_id}, text_msg_id={text_msg_id}. Resetting IDs."
        )
        image_msg_id, text_msg_id = 0, 0  # сбрасываем, чтобы отправить новые сообщения

    try:
        if image_msg_id and text_msg_id:
            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=image_msg_id,
                    media=InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logger.info(f"Image message not modified for user {user_id}")
                else:
                    raise

            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=text_msg_id,
                    text=text,
                    reply_markup=reply_markup
                )
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logger.info(f"Text message not modified for user {user_id}")
                else:
                    raise

            logger.info(f"Edited media and text messages for user {user_id} (IDs: {image_msg_id}, {text_msg_id})")
            return

        raise ValueError("No saved message IDs for editing")

    except Exception as e:
        logger.warning(f"Failed to edit messages for user {user_id}: {e}, sending new messages")

        image_msg = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(photo_path),
            caption=text
        )

        text_msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )

        await save_state(user_id, image_message_id=image_msg.message_id, menu_message_id=text_msg.message_id)

