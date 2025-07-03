from aiogram import types
from aiogram.types import FSInputFile
from src.keyboard import get_main_keyboard, get_submenu_keyboard
from aiogram.types import InputMediaPhoto

categories = ["Документы", "Учебный процесс", "Служба заботы", "Другое"]

category_pictures = {
    "Документы": "images/documents.jpg",
    "Учебный процесс": "images/study.jpg",
    "Служба заботы": "images/support.jpg",
}

category_texts = {
    "Документы": "Тебе поможет учебный отдел, он находится на 4 этаже рядом с кабинетом 4.2",
    "Учебный процесс": "Ты можешь обратиться на свою кафедру. Она находится на 4 этаже напротив столовой",
    "Служба заботы": "Обратись в кабинет службы заботы на 3 этаже рядом с кабинетом 3.8",
    "Другое": "Разные полезные сведения.",
}

user_last_message = {}

async def start_handler(message: types.Message):
    await message.answer(
        f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
        reply_markup=get_main_keyboard()
    )


async def callback_handler(callback: types.CallbackQuery):
    data = callback.data

    if data == "back_to_main":
        await callback.message.edit_text(
            text=f"Привет, {callback.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️",
            reply_markup=get_main_keyboard()
        )
        await callback.answer()
        return

    if data in categories:
        text = category_texts.get(data, "")
        keyboard = get_main_keyboard(disabled_category=data) 

        if data == "Другое":
            await callback.message.edit_text(
                text=text,
                reply_markup=get_submenu_keyboard("Другое")
            )
        else:
            photo_path = category_pictures.get(data)

            if photo_path:
                media = InputMediaPhoto(media=FSInputFile(photo_path), caption=text)
                try:
                    await callback.message.edit_media(media=media, reply_markup=keyboard)
                except Exception:
                    await callback.message.answer_photo(
                        photo=FSInputFile(photo_path),
                        caption=text,
                        reply_markup=keyboard
                    )
            else:
                await callback.message.edit_text(
                    text=text,
                    reply_markup=keyboard
                )
        await callback.answer()
        return


    await callback.answer("Неизвестная команда", show_alert=True)
