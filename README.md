Описание позже, пока что просто красивая структура проекта ввиде дерева:
```
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
├── LICENSE
├── README.md
├── assets
│   └── images
│       ├── documents.jpg
│       ├── feedback.jpg
│       ├── other.jpg
│       ├── redbutton.jpg
│       ├── study.jpg
│       ├── support.jpg
│       ├── support_received.jpg
│       ├── tech_issues.jpg
│       └── welcome.jpg
├── dev
│   ├── dir_tree.py
│   └── watchdog_runner.py
├── docker-compose.yml
├── main.py
├── requirements.txt
├── src
│   ├── bot.py
│   ├── handlers
│   │   ├── admin_commands.py
│   │   ├── admin_handler.py
│   │   ├── callback_handler.py
│   │   ├── feedback_handler.py
│   │   └── start_handler.py
│   ├── keyboards
│   │   ├── identity.py
│   │   ├── main_menu.py
│   │   └── reply.py
│   ├── services
│   │   ├── google_sheets.py
│   │   ├── message_service.py
│   │   ├── redis_client.py
│   │   └── state_manager.py
│   └── utils
│       ├── categories.py
│       ├── config.py
│       ├── filter_profanity.py
│       ├── helpers.py
│       ├── logger.py
│       └── media_utils.py
├── tests
│   ├── __init__.py
│   └── test_profanity_filter.py
```

## Запуск и развёртывание проекта

### Предварительные требования

- Установлен Docker
- Установлен Docker Compose
- Создан и заполнен файл `.env` с необходимыми переменными окружения:
  - `BOT_TOKEN` — токен Telegram бота
  - `GROUP_CHAT_ID` — ID группы для сообщений
  - `SERVICE_ACCOUNT` — путь к файлу с Google сервисным аккаунтом
  - `SPREADSHEET_ID` — ID Google таблицы

---

### Быстрый запуск с Docker Compose

1. Клонируйте репозиторий и перейдите в папку проекта:

    ```bash
    git clone https://github.com/YanKarpov/HelpyBot.git
    cd HelpyBot
    ```

2. Создайте файл `.env` на основе примера `.env.example` и заполните все переменные.

3. Запустите сервисы (бот и Redis) с помощью Docker Compose:

    ```bash
    docker-compose up --build
    ```

4. Бот запустится и подключится к Redis, готов принимать сообщения.

---

### Запуск локально (без Docker)

1. Создайте виртуальное окружение и активируйте его:

    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Linux/macOS
    venv\Scripts\activate     # Windows
    ```

2. Установите зависимости:

    ```bash
    pip install -r requirements.txt
    ```

3. Создайте и заполните `.env` с переменными окружения (как описано выше).

4. Запустите Redis (локально или через Docker):

    ```bash
    docker run -d -p 6379:6379 --name redis redis:7
    ```

5. Запустите бота:

    ```bash
    python main.py
    ```

---

### Тестирование

Для запуска тестов используется `pytest`:

```bash
pytest tests/
