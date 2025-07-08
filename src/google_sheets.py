import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import config  

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

credentials = Credentials.from_service_account_file(
    config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = config.SPREADSHEET_ID

sh = gc.open_by_key(SPREADSHEET_ID)
worksheet = sh.sheet1

def append_feedback_to_sheet(user_id, username, category, message_text, answer_text="", admin_id="", status="Ожидает ответа"):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    row = [
        date_str,
        time_str,
        str(user_id),
        username or "",
        category,
        message_text,
        answer_text,
        admin_id,
        status
    ]

    worksheet.append_row(row)

# Тестовое соединение
# if __name__ == "__main__":
#     append_feedback_to_sheet(
#         user_id=123456789,
#         username="user123",
#         category="Обратная связь",
#         message_text="Пример сообщения для теста",
#         answer_text="",
#         admin_id="",
#         status="Ожидает ответа"
#     )
#     print("Данные успешно отправлены в таблицу")
