from aiogram.exceptions import TelegramBadRequest
from aiogram.types import FSInputFile, InputMediaPhoto, Message, ReplyKeyboardMarkup, InlineKeyboardMarkup
from aiogram.types import CallbackQuery, Message as AiogramMessage
from src.services.redis_client import redis_client, USER_STATE_KEY
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


async def save_state(user_id: int, key_prefix: str = USER_STATE_KEY, **kwargs) -> None:
    """
    Сохраняет словарь значений состояния пользователя в Redis.
    """
    key = key_prefix.format(user_id=user_id)
    mapping = {k: str(v) for k, v in kwargs.items()}
    await redis_client.hset(key, mapping=mapping)
    await redis_client.expire(key, 3600)

    for k, v in mapping.items():
        logger.debug(f"[state] {user_id}: {k} = {v}")


async def send_or_edit_media(
    message_or_cb: CallbackQuery | AiogramMessage,
    photo_path: str,
    photo_caption: str | None,
    text: str,
    reply_markup: InlineKeyboardMarkup | ReplyKeyboardMarkup | None
) -> None:
    """
    Отправляет или редактирует изображения и текстовые сообщения в Telegram.

    Если сообщения уже были отправлены ранее (ID хранятся в Redis),
    пытается отредактировать их. В противном случае — отправляет заново.
    """
    user_id = message_or_cb.from_user.id
    bot = message_or_cb.bot

    if message_or_cb.from_user.is_bot:
        raise ValueError("Нельзя отправлять сообщения бот-пользователям.")

    # Получаем предыдущее состояние пользователя
    state_key = USER_STATE_KEY.format(user_id=user_id)
    state = await redis_client.hgetall(state_key)

    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    # Проверка на невалидные ID
    if image_msg_id > 10_000_000 or text_msg_id > 10_000_000:
        logger.warning(f"[state] Невалидные ID сообщений у пользователя {user_id}. Обнуляем.")
        image_msg_id, text_msg_id = 0, 0

    try:
        if image_msg_id and text_msg_id:
            # Пытаемся отредактировать изображение
            try:
                await bot.edit_message_media(
                    chat_id=user_id,
                    message_id=image_msg_id,
                    media=InputMediaPhoto(
                        media=FSInputFile(photo_path),
                        caption=photo_caption
                    )
                )
                logger.info(f"[edit] Обновлено фото у пользователя {user_id}")
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logger.info(f"[edit] Фото не изменилось у пользователя {user_id}")
                else:
                    logger.warning(f"[edit] Ошибка редактирования фото: {e}")
                    raise

            # Пытаемся отредактировать текст
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=text_msg_id,
                    text=text,
                    reply_markup=reply_markup
                )
                logger.info(f"[edit] Обновлён текст у пользователя {user_id}")
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logger.info(f"[edit] Текст не изменился у пользователя {user_id}")
                else:
                    logger.warning(f"[edit] Ошибка редактирования текста: {e}")
                    raise

            return

        raise ValueError("Нет сохранённых ID сообщений для редактирования.")

    except Exception as e:
        logger.warning(f"[fallback] Отправка заново из-за ошибки: {e}")

        # Отправка заново
        image_msg: Message = await bot.send_photo(
            chat_id=user_id,
            photo=FSInputFile(photo_path),
            caption=photo_caption
        )

        text_msg: Message = await bot.send_message(
            chat_id=user_id,
            text=text,
            reply_markup=reply_markup
        )

        await save_state(
            user_id,
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id
        )

        logger.info(f"[fallback] Отправлены новые сообщения пользователю {user_id}")
