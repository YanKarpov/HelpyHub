from aiogram.exceptions import TelegramBadRequest
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    Message,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message as AiogramMessage,
)

from src.utils.logger import setup_logger
from src.services.state_manager import StateManager  

logger = setup_logger(__name__)


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

    state_manager = StateManager(user_id)
    state = await state_manager.get_state()

    image_msg_id = int(state.get("image_message_id", 0))
    text_msg_id = int(state.get("menu_message_id", 0))

    if image_msg_id > 10_000_000 or text_msg_id > 10_000_000:
        logger.warning(f"[state] Невалидные ID сообщений у пользователя {user_id}. Обнуляем.")
        image_msg_id, text_msg_id = 0, 0

    try:
        if image_msg_id and text_msg_id:
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

        await state_manager.save_state(
            image_message_id=image_msg.message_id,
            menu_message_id=text_msg.message_id
        )

        logger.info(f"[fallback] Отправлены новые сообщения пользователю {user_id}")
