from aiogram.types import Message, FSInputFile
from src.keyboard import get_main_keyboard
from src.utils.media_utils import save_state 
from src.utils.logger import setup_logger
from src.utils.categories import START_INFO  

logger = setup_logger(__name__)

async def start_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"/start received from user {user_id}")

    photo = FSInputFile(START_INFO.image)
    caption_text = START_INFO.text.format(full_name=message.from_user.full_name)

    photo_msg = await message.answer_photo(photo=photo)

    text_msg = await message.answer(caption_text, reply_markup=get_main_keyboard())

    await save_state(
        user_id,
        image_message_id=photo_msg.message_id,
        menu_message_id=text_msg.message_id
    )

    logger.info(f"Sent start photo (id={photo_msg.message_id}) and text (id={text_msg.message_id}) to user {user_id}")
