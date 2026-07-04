"""Watches OCR/inbox for new receipt images and runs the pipeline on them.

Run with: python -m app.watcher   (from the backend/ directory, inside the venv)
"""

import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .config import INBOX_DIR
from .db import init_db
from .pipeline.organizer import run_pipeline

ALLOWED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def _wait_until_stable(path: Path, checks: int = 3, interval: float = 0.5) -> bool:
    """Waits for a file's size to stop changing (avoids reading a half-written file)."""
    last_size = -1
    stable_count = 0
    for _ in range(20):
        if not path.exists():
            return False
        size = path.stat().st_size
        if size == last_size:
            stable_count += 1
            if stable_count >= checks:
                return True
        else:
            stable_count = 0
        last_size = size
        time.sleep(interval)
    return True


def _process_file(path: Path) -> None:
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return
    if not _wait_until_stable(path):
        return
    print(f"[watcher] Processing {path.name}")
    try:
        record = run_pipeline(str(path))
        print(f"[watcher] Done: transaction #{record.get('id')} status={record.get('status')}")
    except Exception as exc:
        print(f"[watcher] Failed to process {path.name}: {exc}")


class InboxHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        _process_file(Path(event.src_path))


def main():
    init_db()
    INBOX_DIR.mkdir(parents=True, exist_ok=True)

    existing = [p for p in INBOX_DIR.iterdir() if p.is_file() and p.suffix.lower() in ALLOWED_SUFFIXES]
    if existing:
        print(f"[watcher] Found {len(existing)} existing file(s) in inbox, processing now...")
        for path in existing:
            _process_file(path)

    observer = Observer()
    observer.schedule(InboxHandler(), str(INBOX_DIR), recursive=False)
    observer.start()
    print(f"[watcher] Watching {INBOX_DIR} — drop receipt images here.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    main()
