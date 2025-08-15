import os
from dotenv import load_dotenv
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).parent
    load_dotenv(BASE_DIR / ".env")

    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    GROUP_CHAT_ID: int = int(os.getenv("GROUP_CHAT_ID", 0))
    SUPPORT_THREAD_ID: int = int(os.getenv("SUPPORT_THREAD_ID", 0))
    SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID")
    SERVICE_ACCOUNT_FILE: str = str(BASE_DIR / "service_account.json")

    @classmethod
    def validate(cls):
        required_vars = {
            "BOT_TOKEN": cls.BOT_TOKEN,
            "GROUP_CHAT_ID": cls.GROUP_CHAT_ID,
            "SUPPORT_THREAD_ID": cls.SUPPORT_THREAD_ID,
            "SPREADSHEET_ID": cls.SPREADSHEET_ID,
            "SERVICE_ACCOUNT_FILE": cls.SERVICE_ACCOUNT_FILE
        }
        for name, value in required_vars.items():
            if value is None or value == "":
                raise ValueError(f"Переменная окружения {name} не установлена!")

    @classmethod
    def add_env_var(cls, name, default=None, cast=str):
        """
        Универсальный способ добавить новую переменную окружения.
        Пример: Config.add_env_var("REDIS_URL")
        """
        value = os.getenv(name, default)
        if value is None:
            raise ValueError(f"Переменная окружения {name} не установлена!")
        setattr(cls, name, cast(value))
