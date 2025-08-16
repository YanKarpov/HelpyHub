from aiogram.types import Message

MAX_FEEDBACK_LENGTH = 500

class FeedbackValidator:
    @staticmethod
    def extract_text(message: Message) -> str:
        """
        Достаём текст из обычного сообщения или подписи к медиа.
        Если текста нет, вернём пустую строку.
        """
        return (message.text or message.caption or "").strip()

    @staticmethod
    def check_length(message: Message) -> str | None:
        """
        Проверяем длину текста обращения.
        - Если длина <= MAX_FEEDBACK_LENGTH → возвращаем None.
        - Если длина превышает лимит → возвращаем текст ошибки.
        """
        user_text = FeedbackValidator.extract_text(message)
        if len(user_text) > MAX_FEEDBACK_LENGTH:
            return (
                f"❗️ Текст обращения слишком длинный "
                f"(максимум {MAX_FEEDBACK_LENGTH} символов, "
                f"сейчас {len(user_text)})."
            )
        return None
