"""PLAN J-14 (Update #97): Asynchronous Asset-Loading.

Pygame-Engines können Sounds/Sprites synchron beim Bootstrap laden, was
einen langen Start-Freeze gibt. Diese kleine Helper-Klasse erlaubt
Background-Threading via `concurrent.futures.ThreadPoolExecutor`.

Pygame.mixer.Sound() ist thread-safe für load + decode (laut SDL_mixer-
Doku). Sprite-Surface-Load via `pygame.image.load()` ist NICHT
thread-safe für convert/convert_alpha — daher müssen die Convert-Calls
im Main-Thread laufen. Wir laden raw Bytes im Worker, finalisieren im
Main-Thread.

API:
    loader = AsyncAssetLoader(max_workers=2)
    loader.queue_sound('cast_fire', '...path.wav')
    loader.queue_sprite('hero_idle', '...path.png')
    # Pro Frame:
    loader.poll_completed()       # ruft Callbacks ab → fertige Assets

    # Optional am Ende:
    loader.shutdown(wait=False)

Falls Pygame/Threading nicht verfügbar → fallback auf sofortiges Laden
im Main-Thread.
"""

import threading
import queue

try:
    from concurrent.futures import ThreadPoolExecutor
    _EXECUTOR_OK = True
except ImportError:
    _EXECUTOR_OK = False


class AsyncAssetLoader:
    """Thread-Pool-basierter Asset-Loader für Skill-/Sprite-/Sound-Assets."""

    def __init__(self, max_workers=2):
        self._completed = queue.Queue()
        self._pending_count = 0
        self._lock = threading.Lock()
        if _EXECUTOR_OK:
            self._executor = ThreadPoolExecutor(
                max_workers=max_workers,
                thread_name_prefix='AssetLoader')
        else:
            self._executor = None

    def queue_load(self, key, loader_fn, on_complete=None):
        """Generic load — `loader_fn()` läuft im Worker, `on_complete(result)`
        wird über poll_completed im Main-Thread aufgerufen."""
        with self._lock:
            self._pending_count += 1

        def task():
            try:
                result = loader_fn()
                self._completed.put(('ok', key, result, on_complete))
            except Exception as ex:
                self._completed.put(('err', key, ex, on_complete))

        if self._executor is not None:
            self._executor.submit(task)
        else:
            # Fallback: synchron im Main-Thread
            task()

    def poll_completed(self, max_items=8):
        """Verarbeitet bis zu `max_items` fertige Loads im Main-Thread.
        Aufrufen pro Frame im Game-Loop."""
        processed = 0
        while processed < max_items:
            try:
                status, key, payload, cb = self._completed.get_nowait()
            except queue.Empty:
                break
            with self._lock:
                self._pending_count = max(0, self._pending_count - 1)
            if cb is not None:
                try:
                    cb(status, key, payload)
                except Exception:
                    pass
            processed += 1
        return processed

    def pending(self):
        with self._lock:
            return self._pending_count

    def shutdown(self, wait=False):
        if self._executor is not None:
            try:
                self._executor.shutdown(wait=wait)
            except Exception:
                pass
            self._executor = None


# Singleton-Instanz für Convenience-API
_default_loader = None


def get_loader():
    global _default_loader
    if _default_loader is None:
        _default_loader = AsyncAssetLoader(max_workers=2)
    return _default_loader
