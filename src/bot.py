from aiogram.filters import Command

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import BOT_TOKEN
from src.handlers.start import start_handler
from src.handlers.callback import callback_handler
from src.handlers.feedback import feedback_message_handler
from src.handlers.admin_reply import admin_reply_text_handler, admin_replying

from aiogram.types import Message
from aiogram.filters import Filter


from src.logger import setup_logger
logger = setup_logger(__name__)

class IsAdminReplying(Filter):
    async def __call__(self, message: Message) -> bool:
        result = message.from_user.id in admin_replying
        logger.info(f"IsAdminReplying filter: user_id={message.from_user.id} result={result}")
        return result

    
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command(commands=["start"]))
    dp.callback_query.register(callback_handler)
    dp.message.register(admin_reply_text_handler, IsAdminReplying())
    dp.message.register(feedback_message_handler)


