from aiogram.types import Message, FSInputFile
from src.keyboards.main_menu import get_main_keyboard
from src.utils.logger import setup_logger
from src.utils.categories import START_INFO
from src.services.state_manager import StateManager  

logger = setup_logger(__name__)


async def start_handler(message: Message):
    user_id = message.from_user.id
    logger.info(f"/start received from user {user_id}")

    state_manager = StateManager(user_id)

    photo = FSInputFile(START_INFO.image)
    caption_text = START_INFO.text.format(full_name=message.from_user.full_name)

    photo_msg = await message.answer_photo(photo=photo)
    text_msg = await message.answer(caption_text, reply_markup=get_main_keyboard())

    await state_manager.save_state(
        image_message_id=photo_msg.message_id,
        menu_message_id=text_msg.message_id
    )

    logger.info(
        f"Start handler triggered by user_id={user_id}, "
        f"chat_id={message.chat.id}, message_id={message.message_id}"
    )
