import os
from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto, InlineKeyboardMarkup, InlineKeyboardButton
from src.keyboard import get_main_keyboard, get_submenu_keyboard, get_reply_to_user_keyboard

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

# user_feedback_waiting: user_id -> dict с полями: type, prompt_message_id, menu_message_id
user_feedback_waiting = {}

# admin_replying: admin_user_id -> user_id, кому админ сейчас отвечает
admin_replying = {}

async def start_handler(message: types.Message):
    welcome_text = (
        f"Привет, {message.from_user.full_name}!\n"
        "Я знаю, что у тебя вопрос и я постараюсь его решить ❤️"
    )
    photo_path = "images/other.webp"

    sent = await message.answer_photo(
        photo=FSInputFile(photo_path),
        caption=welcome_text,
        reply_markup=get_main_keyboard()
    )

    user_feedback_waiting[message.from_user.id] = {"menu_message_id": sent.message_id}


async def callback_handler(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id

    async def save_menu_message(message: types.Message):
        if user_id in user_feedback_waiting:
            user_feedback_waiting[user_id]["menu_message_id"] = message.message_id
        else:
            user_feedback_waiting[user_id] = {"menu_message_id": message.message_id}

    # Новый блок: Обработка кнопки "Ответить" в группе поддержки
    if data.startswith("reply_to_user:"):
        # Извлекаем ID пользователя, которому нужно ответить
        try:
            target_user_id = int(data.split(":", 1)[1])
        except ValueError:
            await callback.answer("Некорректный ID пользователя", show_alert=True)
            return

        admin_id = callback.from_user.id
        admin_replying[admin_id] = target_user_id

        await callback.answer("Напиши сообщение для пользователя в этом чате, я перешлю ему ответ.")
        await callback.message.answer(
            f"Вы начали отвечать пользователю с ID {target_user_id}. "
            "Пожалуйста, напишите сообщение, и я отправлю его пользователю."
        )
        return

    if data == "back_to_main":
        welcome_text = (
            f"Привет, {callback.from_user.full_name}!\n"
            "Я знаю, что у тебя вопрос и я постараюсь его решить ❤️"
        )
        photo_path = "images/other.webp"

        media = InputMediaPhoto(media=FSInputFile(photo_path), caption=welcome_text)

        try:
            await callback.message.edit_reply_markup(reply_markup=None)
            await callback.message.edit_media(media=media, reply_markup=get_main_keyboard())
            await save_menu_message(callback.message)
        except Exception:
            sent = await callback.message.answer_photo(
                photo=FSInputFile(photo_path),
                caption=welcome_text,
                reply_markup=get_main_keyboard()
            )
            await save_menu_message(sent)

        await callback.answer()
        return

    if data == "ignore":
        await callback.answer("Вы уже здесь 😉", show_alert=True)
        return

    if data in ["Проблемы с техникой", "Обратная связь"]:
        prompt_msg = await callback.message.answer(
            f"Пожалуйста, опиши свою проблему или вопрос по теме '{data}':"
        )
        if user_id in user_feedback_waiting:
            user_feedback_waiting[user_id].update({
                "type": data,
                "prompt_message_id": prompt_msg.message_id,
            })
        else:
            user_feedback_waiting[user_id] = {
                "type": data,
                "prompt_message_id": prompt_msg.message_id,
            }
        await callback.answer()
        return

    if data == "Другое":
        text = category_texts.get("Другое", "Информация не найдена.")
        photo_path = category_pictures.get("Другое")
        submenu = get_submenu_keyboard("Другое")

        if photo_path:
            media = InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.edit_media(media=media, reply_markup=submenu)
                await save_menu_message(callback.message)
            except Exception:
                sent = await callback.message.answer_photo(
                    photo=FSInputFile(photo_path),
                    caption=text,
                    reply_markup=submenu
                )
                await save_menu_message(sent)
        else:
            try:
                await callback.message.edit_text(text=text, reply_markup=submenu)
                await save_menu_message(callback.message)
            except Exception:
                sent = await callback.message.answer(text=text, reply_markup=submenu)
                await save_menu_message(sent)

        await callback.answer()
        return

    if data in categories:
        text = category_texts.get(data, "Информация не найдена.")
        photo_path = category_pictures.get(data)
        keyboard = get_main_keyboard(disabled_category=data)

        if photo_path:
            media = InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
            try:
                await callback.message.edit_reply_markup(reply_markup=None)
                await callback.message.edit_media(media=media, reply_markup=keyboard)
                await save_menu_message(callback.message)
            except Exception:
                sent = await callback.message.answer_photo(
                    photo=FSInputFile(photo_path),
                    caption=text,
                    reply_markup=keyboard
                )
                await save_menu_message(sent)
        else:
            try:
                await callback.message.edit_text(text=text, reply_markup=keyboard)
                await save_menu_message(callback.message)
            except Exception:
                sent = await callback.message.answer(text=text, reply_markup=keyboard)
                await save_menu_message(sent)

        await callback.answer()
        return

    await callback.answer("Неизвестная команда", show_alert=True)


async def feedback_message_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_feedback_waiting:
        return

    feedback_data = user_feedback_waiting.pop(user_id)
    feedback_type = feedback_data.get("type")
    prompt_message_id = feedback_data.get("prompt_message_id")
    menu_message_id = feedback_data.get("menu_message_id")

    GROUP_CHAT_ID = int(os.getenv("GROUP_CHAT_ID"))

    text = (
        f"Новое обращение от @{message.from_user.username or message.from_user.full_name}:\n"
        f"Категория: {feedback_type}\n\n"
        f"{message.text}"
    )

    reply_markup = get_reply_to_user_keyboard(user_id)

    await message.bot.send_message(chat_id=GROUP_CHAT_ID, text=text, reply_markup=reply_markup)

    if prompt_message_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=prompt_message_id)
        except Exception:
            pass

    try:
        await message.delete()
    except Exception:
        pass

    photo_path = "images/other.webp"
    media = InputMediaPhoto(
        media=FSInputFile(photo_path),
        caption="Спасибо! Твое сообщение отправлено в службу поддержки."
    )

    back_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
    ])

    if menu_message_id:
        try:
            await message.bot.edit_message_media(
                chat_id=message.chat.id,
                message_id=menu_message_id,
                media=media,
                reply_markup=back_keyboard
            )
        except Exception:
            await message.answer_photo(
                photo=FSInputFile(photo_path),
                caption="Спасибо! Твое сообщение отправлено в службу поддержки.",
                reply_markup=back_keyboard
            )
    else:
        await message.answer_photo(
            photo=FSInputFile(photo_path),
            caption="Спасибо! Твое сообщение отправлено в службу поддержки.",
            reply_markup=back_keyboard
        )


# Новый хендлер — обработка текста от админа, который в режиме ответа
async def admin_reply_text_handler(message: types.Message):
    admin_id = message.from_user.id
    if admin_id not in admin_replying:
        return  # Этот админ сейчас ни на кого не отвечает

    user_id = admin_replying[admin_id]
    text = message.text

    try:
        await message.bot.send_message(chat_id=user_id, text=f"Ответ от службы поддержки:\n\n{text}")
        await message.reply("Сообщение успешно отправлено пользователю.")
    except Exception as e:
        await message.reply(f"Не удалось отправить сообщение пользователю: {e}")

    del admin_replying[admin_id]
