from aiogram import types
from aiogram.types import FSInputFile, InputMediaPhoto
from src.keyboard import get_main_keyboard, get_submenu_keyboard

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


async def send_or_edit_media_message(message: types.Message, photo_path: str, caption: str, keyboard):
    media = InputMediaPhoto(media=FSInputFile(photo_path), caption=caption)
    try:
        await message.edit_reply_markup(reply_markup=None)
        await message.edit_media(media=media, reply_markup=keyboard)
    except Exception:
        await message.answer_photo(photo=FSInputFile(photo_path), caption=caption, reply_markup=keyboard)


async def start_handler(message: types.Message):
    await send_or_edit_media_message(
        message=message,
        photo_path="images/other.webp",
        caption=f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
        keyboard=get_main_keyboard()
    )


async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        await send_or_edit_media_message(
            message=callback.message,
            photo_path="images/other.webp",
            caption=f"Привет, {callback.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
            keyboard=get_main_keyboard()
        )
        await callback.answer()
        return

    if data == "ignore":
        await callback.answer("Вы уже здесь 😉", show_alert=True)
        return

    if data in categories:
        text = category_texts.get(data, "Информация не найдена.")
        photo_path = category_pictures.get(data)
        keyboard = get_main_keyboard(disabled_category=data) if data != "Другое" else get_submenu_keyboard("Другое")

        await send_or_edit_media_message(
            message=callback.message,
            photo_path=photo_path,
            caption=text,
            keyboard=keyboard
        )
        await callback.answer()
        return

    await callback.answer("Неизвестная команда", show_alert=True)