import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Переменная окружения BOT_TOKEN не установлена!")

if not GROUP_CHAT_ID:
    raise ValueError("Переменная окружения GROUP_CHAT_ID не установлена!")

try:
    GROUP_CHAT_ID = int(GROUP_CHAT_ID)
except ValueError:
    raise ValueError("GROUP_CHAT_ID должен быть числом (int), проверь .env файл.")

# print("Config: GROUP_CHAT_ID =", GROUP_CHAT_ID, type(GROUP_CHAT_ID))
# print("Config: BOT_TOKEN =", BOT_TOKEN, type(GROUP_CHAT_ID))

