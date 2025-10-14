import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from v2.app.services.state_manager import StateManager

class DirectoryMonitor(FileSystemEventHandler):
    def __init__(self, path: str, state_manager: StateManager):
        self.path = path
        self.state_manager = state_manager
        self.observer = Observer()

    def start(self):
        self.observer.schedule(self, self.path, recursive=True)
        self.observer.start()
        print(f"Started monitoring directory: {self.path}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
        print("Stopped monitoring directory.")

    def on_created(self, event):
        if not event.is_directory:
            print(f"File Created: {event.src_path}")
            self.state_manager.add_unorganized_file(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            print(f"File Deleted: {event.src_path}")
            # Future implementation: self.state_manager.remove_file(event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            print(f"File Modified: {event.src_path}")
            # Future implementation: self.state_manager.update_file(event.src_path)

if __name__ == '__main__':
    # This is an example of how to use the DirectoryMonitor
    # It requires a running StateManager and DatabaseManager instance.
    pass
