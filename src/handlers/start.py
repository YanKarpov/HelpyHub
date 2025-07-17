from aiogram.types import Message, FSInputFile
from src.keyboard import get_main_keyboard
from src.utils.media_utils import save_feedback_state
from src.utils.logger import setup_logger
from src.utils.categories import START_INFO  

logger = setup_logger(__name__)

async def start_handler(message: Message):
    logger.info(f"/start received from user {message.from_user.id}")
    
    caption = START_INFO.text.format(full_name=message.from_user.full_name)
    photo = FSInputFile(START_INFO.image)
    
    sent = await message.answer_photo(
        photo=photo,
        caption=caption,
        reply_markup=get_main_keyboard()
    )
    
    await save_feedback_state(message.from_user.id, menu_message_id=sent.message_id)
    logger.info(f"Sent start photo message id={sent.message_id} to user {message.from_user.id}")