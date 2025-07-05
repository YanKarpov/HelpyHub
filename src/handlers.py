import logging
from aiogram.types import (
    FSInputFile,
    InputMediaPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    Message,
)
from src.keyboard import get_main_keyboard, get_submenu_keyboard, get_reply_to_user_keyboard
from src.config import GROUP_CHAT_ID
from src.state import user_feedback_waiting, admin_replying

# Константы 
categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

category_pictures = {
    "Документы": "images/documents.jpg",
    "Учебный процесс": "images/study.jpg",
    "Служба заботы": "images/support.jpg",
    "Другое": "images/other.webp",
}

category_texts = {
    "Документы": "Тебе поможет учебный отдел, он находится на 4 этаже рядом с кабинетом 4.2",
    "Учебный процесс": "Ты можешь обратиться на свою кафедру. Она находится на 4 этаже напротив столовой",
    "Служба заботы": "Обратись в кабинет службы заботы на 3 этаже рядом с кабинетом 3.8",
    "Другое": "Разные полезные сведения.",
}

# Логирование
logger = logging.getLogger(__name__)

async def save_feedback_state(user_id: int, **kwargs):
    if user_id in user_feedback_waiting:
        user_feedback_waiting[user_id].update(kwargs)
    else:
        user_feedback_waiting[user_id] = kwargs
    logger.info(f"Feedback state updated for user {user_id}: {user_feedback_waiting[user_id]}")


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


# Хендлер: /start
async def start_handler(message: Message):
    logger.info(f"/start received from user {message.from_user.id}")
    caption = f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️"
    photo = FSInputFile("images/other.webp")

    sent = await message.answer_photo(photo=photo, caption=caption, reply_markup=get_main_keyboard())
    await save_feedback_state(message.from_user.id, menu_message_id=sent.message_id)
    logger.info(f"Sent start photo message id={sent.message_id} to user {message.from_user.id}")


# Хендлер: Callback-кнопки 
async def callback_handler(callback: CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    logger.info(f"Callback received from user {user_id} with data: {data}")

    async def save_menu_id(msg: Message):
        await save_feedback_state(user_id, menu_message_id=msg.message_id)
        logger.info(f"Menu message id={msg.message_id} saved for user {user_id}")

    # Ответ от админа
    if data.startswith("reply_to_user:"):
        try:
            admin_replying[callback.from_user.id] = int(data.split(":", 1)[1])
            await callback.answer("Напиши сообщение для пользователя в этом чате")
            await callback.message.answer(f"Ответ пользователю ID {admin_replying[callback.from_user.id]}:")
            logger.info(f"Admin {callback.from_user.id} replying to user {admin_replying[callback.from_user.id]}")
        except ValueError:
            logger.error(f"Invalid user ID in reply_to_user: {data}")
            await callback.answer("Некорректный ID", show_alert=True)
        return

    # Назад в главное меню
    if data == "back_to_main":
        msg = await send_or_edit_media(
            callback.message,
            "images/other.webp",
            f"Привет, {callback.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
            get_main_keyboard()
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    # Игнор
    if data == "ignore":
        await callback.answer("Вы уже здесь 😉", show_alert=True)
        logger.info(f"User {user_id} pressed ignore")
        return

    # Обратная связь
    if data in ["Проблемы с техникой", "Обратная связь"]:
        prompt_msg = await callback.message.answer(f"Опиши проблему по теме '{data}':")
        await save_feedback_state(user_id, type=data, prompt_message_id=prompt_msg.message_id)
        logger.info(f"Feedback prompt sent to user {user_id} for type {data}")
        await callback.answer()
        return

    # Подменю "Другое"
    if data == "Другое":
        msg = await send_or_edit_media(
            callback.message,
            category_pictures["Другое"],
            category_texts["Другое"],
            get_submenu_keyboard("Другое")
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    # Основные категории
    if data in categories:
        msg = await send_or_edit_media(
            callback.message,
            category_pictures[data],
            category_texts[data],
            get_main_keyboard(disabled_category=data)
        )
        await save_menu_id(msg)
        await callback.answer()
        return

    logger.warning(f"Unknown callback data received: {data}")
    await callback.answer("Неизвестная команда", show_alert=True)


# Хендлер: Сообщение от пользователя (фидбек) 
async def feedback_message_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_feedback_waiting:
        logger.info(f"Received feedback message from user {user_id} but no feedback expected")
        return

    feedback = user_feedback_waiting.pop(user_id)
    text = (
        f"Новое обращение от @{message.from_user.username or message.from_user.full_name}:\n"
        f"Категория: {feedback.get('type')}\n\n{message.text}"
    )

    logger.info(f"Sending feedback message to support group {GROUP_CHAT_ID} from user {user_id}")

    try:
        await message.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text=text,
            reply_markup=get_reply_to_user_keyboard(user_id)
        )
    except Exception as e:
        logger.error(f"Failed to send message to support group: {e}")

    if (msg_id := feedback.get("prompt_message_id")):
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=msg_id)
            logger.info(f"Deleted prompt message id={msg_id} for user {user_id}")
        except Exception as e:
            logger.warning(f"Failed to delete prompt message: {e}")

    try:
        await message.delete()
        logger.info(f"Deleted feedback message from user {user_id}")
    except Exception as e:
        logger.warning(f"Failed to delete user message: {e}")

    ack_caption = "Спасибо! Твое сообщение отправлено в службу поддержки."
    ack_photo = FSInputFile("images/other.webp")
    back_btn = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]]
    )

    if (menu_id := feedback.get("menu_message_id")):
        try:
            await message.bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=menu_id,
                media=InputMediaPhoto(media=ack_photo, caption=ack_caption),
                reply_markup=back_btn
            )
            logger.info(f"Edited menu message id={menu_id} with ack photo")
            return
        except Exception as e:
            logger.warning(f"Failed to edit menu message: {e}")

    await message.answer_photo(photo=ack_photo, caption=ack_caption, reply_markup=back_btn)
    logger.info(f"Sent acknowledgment photo to user {user_id}")


# Хендлер: Ответ от админа пользователю 
async def admin_reply_text_handler(message: Message):
    admin_id = message.from_user.id
    logger.info(f"admin_reply_text_handler called from user {admin_id}")

    user_id = admin_replying.get(admin_id)
    if user_id is None:
        logger.info(f"Message from user {admin_id} ignored in admin reply handler (not replying now)")
        return

    logger.info(f"Admin {admin_id} is replying to user {user_id} with text: {message.text!r}")

    try:
        await message.bot.send_message(chat_id=user_id, text=f"Ответ от службы поддержки:\n\n{message.text}")
        logger.info(f"Message successfully sent to user {user_id}")

        await message.reply("Сообщение успешно отправлено пользователю.")
        logger.info(f"Admin {admin_id} notified about successful sending")

        # Удаляем только после успешной отправки
        admin_replying.pop(admin_id, None)
        logger.info(f"Removed admin {admin_id} from admin_replying")

    except Exception as e:
        logger.error(f"Error sending admin reply from admin {admin_id} to user {user_id}: {e}")
        await message.reply(f"Ошибка отправки: {e}")
