import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from src.utils import config

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

credentials = Credentials.from_service_account_file(
    config.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
gc = gspread.authorize(credentials)

SPREADSHEET_ID = config.SPREADSHEET_ID

sh = gc.open_by_key(SPREADSHEET_ID)
worksheet = sh.sheet1

def append_feedback_to_sheet(
    user_id, username, category, message_text,
    answer_text="", admin_id="", admin_username="", status="Ожидает ответа",
    is_named=True
):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    row_user_id = str(user_id)

    row_username = username if is_named else "Анонимус"

    row = [
        date_str,
        time_str,
        row_user_id,
        row_username,
        category,
        message_text,
        answer_text,
        admin_id,
        admin_username,
        status
    ]

    worksheet.append_row(row)

def update_feedback_in_sheet(
    user_id, answer_text, admin_id,
    admin_username="", new_status="Вопрос закрыт"
):
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    all_records = worksheet.get_all_records()

    for idx, record in enumerate(all_records, start=2):
        if str(record.get('user_id', '')).strip() == str(user_id) and record.get('Статус', '').strip() == "Ожидает ответа":
            worksheet.update(f'A{idx}', [[date_str]])           # Дата
            worksheet.update(f'B{idx}', [[time_str]])           # Время
            worksheet.update(f'G{idx}', [[answer_text]])        # Ответ
            worksheet.update(f'H{idx}', [[str(admin_id)]])      # ID админа
            worksheet.update(f'I{idx}', [[admin_username]])     # admin_username 
            worksheet.update(f'J{idx}', [[new_status]])         # Статус
            return True

    return False


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
