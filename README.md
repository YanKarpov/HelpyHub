Описание позже, пока что просто красивая структура проекта ввиде дерева:
```
├── .dockerignore
├── .gitignore
├── Dockerfile
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
├── docker-compose.yml
├── filter_profanity.py
├── main.py
├── requirements.txt
├── src
│   ├── bot.py
│   ├── handlers
│   │   ├── admin_handler.py
│   │   ├── callback_handler.py
│   │   ├── feedback_handler.py
│   │   └── start_handler.py
│   ├── keyboard.py
│   ├── services
│   │   ├── google_sheets.py
│   │   ├── message_service.py
│   │   └── redis_client.py
│   └── utils
│       ├── categories.py
│       ├── config.py
│       ├── dir_tree.py
│       ├── helpers.py
│       ├── logger.py
│       └── media_utils.py
├── tests
│   ├── __init__.py
│   └── test_profanity_filter.py
└── watchdog_runner.py
```
