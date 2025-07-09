from aiogram.types import Message, FSInputFile
from src.keyboard import get_main_keyboard
from src.utils.utils import save_feedback_state
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

async def start_handler(message: Message):
    logger.info(f"/start received from user {message.from_user.id}")
    caption = f"Привет, {message.from_user.full_name}!\nЯ знаю, что у тебя вопрос и я постараюсь его решить ❤️"
    photo = FSInputFile("images/other.webp")

    sent = await message.answer_photo(photo=photo, caption=caption, reply_markup=get_main_keyboard())
    await save_feedback_state(message.from_user.id, menu_message_id=sent.message_id)
    logger.info(f"Sent start photo message id={sent.message_id} to user {message.from_user.id}")
