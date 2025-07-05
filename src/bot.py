import logging
from aiogram.filters import Command

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from src.config import BOT_TOKEN
from src.handlers import start_handler, callback_handler, feedback_message_handler, admin_reply_text_handler, admin_replying

from aiogram.types import Message
from aiogram.filters import Filter

class IsAdminReplying(Filter):
    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in admin_replying
    
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)


def register_handlers(dp: Dispatcher):
    dp.message.register(start_handler, Command(commands=["start"]))
    dp.callback_query.register(callback_handler)
    dp.message.register(feedback_message_handler)
    dp.message.register(admin_reply_text_handler, IsAdminReplying())
