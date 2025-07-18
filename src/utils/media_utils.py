from aiogram.types import FSInputFile, InputMediaPhoto
from src.services.redis_client import redis_client
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def save_feedback_state(user_id: int, **kwargs):
    key = f"user_state:{user_id}"  # лучше совпадать с ключом, где хранятся message_id
    str_mapping = {k: str(v) for k, v in kwargs.items()}
    await redis_client.hset(key, mapping=str_mapping)
    await redis_client.expire(key, 3600)
    state = await redis_client.hgetall(key)
    logger.info(f"Feedback state updated for user {user_id}: {state}")


async def send_or_edit_media(message_or_cb, photo_path, text, reply_markup):
    """
    Редактирует или отправляет два сообщения:
    1) Фото с подписью
    2) Сообщение с текстом и клавиатурой

    При редактировании обновляет оба, при ошибке — отправляет заново.
    Сохраняет message_id обоих сообщений в redis.
    """
    user_id = message_or_cb.from_user.id
    bot = message_or_cb.bot

    state = await redis_client.hgetall(f"user_state:{user_id}")
    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    try:
        if image_msg_id and text_msg_id:
            # Редактируем сообщение с фото и подписью (caption)
            await bot.edit_message_media(
                chat_id=user_id,
                message_id=image_msg_id,
                media=InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
            )

            # Редактируем отдельное текстовое сообщение с кнопками
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=text_msg_id,
                text=text,  # можно изменить, либо оставить для дублирования, либо как-то убрать
                reply_markup=reply_markup
            )
            logger.info(f"Edited media and text messages for user {user_id} (IDs: {image_msg_id}, {text_msg_id})")
            return

        raise ValueError("No saved message IDs for editing")

    except Exception as e:
        logger.warning(f"Failed to edit messages for user {user_id}: {e}, sending new messages")

        # Отправляем фото с подписью
        image_msg = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(photo_path),
            caption=text
        )

        # Отправляем текстовое сообщение с кнопками
        text_msg = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )

        # Сохраняем новые message_id в redis
        await save_feedback_state(user_id, image_message_id=image_msg.message_id, menu_message_id=text_msg.message_id)
