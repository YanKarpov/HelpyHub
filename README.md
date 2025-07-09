Описание позже, пока что просто красивая структура проекта ввиде дерева:
```
├── docker-compose.yml
├── images
│   ├── documents.jpg
│   ├── other.webp
│   ├── study.jpg
│   └── support.jpg
├── main.py
├── requirements.txt
├── service_account.json
├── src
│   ├── bot.py
│   ├── handlers
│   │   ├── admin_reply.py
│   │   ├── callback.py
│   │   ├── feedback.py
│   │   └── start.py
│   ├── keyboard.py
│   ├── services
│   │   ├── google_sheets.py
│   │   └── redis_client.py
│   └── utils
│       ├── config.py
│       ├── dir_tree.py
│       ├── logger.py
│       └── utils.py
└── watchdog_runner.py
```
