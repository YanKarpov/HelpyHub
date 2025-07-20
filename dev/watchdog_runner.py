import subprocess
import sys
import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

IGNORED_DIRS = {"venv"}

class RestartOnChangeHandler(FileSystemEventHandler):
    def __init__(self, script_path):
        self.script_path = script_path
        self.process = None
        self.restart()

    def restart(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print("Запускаем бота...")
        self.process = subprocess.Popen([sys.executable, self.script_path])

    def on_modified(self, event):
        if not event.src_path.endswith(".py"):
            return

        if any(ignored in event.src_path.split(os.sep) for ignored in IGNORED_DIRS):
            return

        print(f"Файл изменён: {event.src_path}. Перезапуск бота...")
        self.restart()


if __name__ == "__main__":
    script = "main.py"  

    event_handler = RestartOnChangeHandler(script)
    observer = Observer()
    observer.schedule(event_handler, path='.', recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()
