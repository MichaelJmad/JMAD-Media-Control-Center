
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from PySide6.QtCore import QObject, Signal

class DirectoryMonitor(QObject, FileSystemEventHandler):
    def __init__(self, path, signal_emitter):
        super().__init__()
        self.path = path
        self.signal_emitter = signal_emitter
        self.observer = Observer()

    def start(self):
        self.observer.schedule(self, self.path, recursive=True)
        self.observer.start()
        print(f"Started monitoring directory: {self.path}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print(f"Stopped monitoring directory: {self.path}")

    def on_created(self, event):
        if not event.is_directory:
            self.signal_emitter.emit("created", event.src_path, None)

    def on_modified(self, event):
        if not event.is_directory:
            self.signal_emitter.emit("modified", event.src_path, None)

    def on_deleted(self, event):
        if not event.is_directory:
            self.signal_emitter.emit("deleted", event.src_path, None)

    def on_moved(self, event):
        if not event.is_directory:
            self.signal_emitter.emit("moved", event.src_path, event.dest_path)
