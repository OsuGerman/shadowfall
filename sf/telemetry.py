"""Telemetrie (PLAN AA-04).

Anonyme, opt-in Stats:
  - Klasse beim Tod
  - Stufe beim Tod
  - Boss-Kills pro Run
  - Spielzeit
  - Distinct Cause-Of-Death

Wird lokal in `~/.shadowfall_telemetry.jsonl` als Line-Delimited-JSON
geloggt.  Kein Netzwerk-Send — User kann die Datei manuell ueber
GitHub-Issues teilen.

Default OFF.  Toggle via Setting `telemetry`.

Audit #179 B.7: Events werden in eine RAM-Queue gepushed; ein Background-
Thread flusht periodisch (alle 30 s oder wenn Queue >= 100) und auch via
`atexit`-Handler beim Programm-Ende. Vorher: sync `f.write()` PRO Event →
bei 10 Events/s = 10 Disk-Writes/s im Main-Thread.
"""

import atexit
import json
import os
import threading
import time


def _path():
    return os.path.expanduser('~/.shadowfall_telemetry.jsonl')


# ============================================================
# Audit #179 B.7: Background-Flusher
# ============================================================
_QUEUE = []
_QUEUE_LOCK = threading.Lock()
_FLUSHER_THREAD = None
_FLUSHER_STOP = threading.Event()
_FLUSH_INTERVAL_S = 30.0
_QUEUE_HIGH_WATER = 100   # bei Ueberschreitung: sofort flushen
_atexit_registered = False


def _drain_and_write():
    """Schreibt alle in der Queue stehenden Events auf Disk.

    Thread-Safe: held _QUEUE_LOCK kurz fuer den Drain, schreibt dann ohne
    Lock auf Disk. So blockiert Disk-IO nie den Main-Thread.
    """
    with _QUEUE_LOCK:
        if not _QUEUE:
            return
        batch = _QUEUE[:]
        _QUEUE.clear()
    try:
        with open(_path(), 'a', encoding='utf-8') as f:
            for payload in batch:
                f.write(json.dumps(payload, ensure_ascii=False) + '\n')
    except OSError:
        # Disk voll / Permission-Fehler — Events sind weg, aber Game
        # laeuft weiter. Telemetry ist opt-in, nicht kritisch.
        pass


def _flusher_loop():
    while not _FLUSHER_STOP.is_set():
        _FLUSHER_STOP.wait(_FLUSH_INTERVAL_S)
        _drain_and_write()


def _ensure_flusher_running():
    """Startet Background-Thread + atexit-Handler beim 1. Event."""
    global _FLUSHER_THREAD, _atexit_registered
    if _FLUSHER_THREAD is None or not _FLUSHER_THREAD.is_alive():
        _FLUSHER_STOP.clear()
        _FLUSHER_THREAD = threading.Thread(
            target=_flusher_loop, name='telemetry-flusher',
            daemon=True)
        _FLUSHER_THREAD.start()
    if not _atexit_registered:
        atexit.register(shutdown_flusher)
        _atexit_registered = True


def shutdown_flusher(timeout=2.0):
    """Stoppt den Flusher-Thread und drained die Queue ein letztes Mal.

    Wird via atexit automatisch gerufen. Kann auch in Tests manuell
    gerufen werden um Thread-Leaks zu vermeiden.
    """
    _FLUSHER_STOP.set()
    if _FLUSHER_THREAD is not None and _FLUSHER_THREAD.is_alive():
        _FLUSHER_THREAD.join(timeout=timeout)
    _drain_and_write()


def is_enabled(game):
    try:
        return bool(game.settings.get('telemetry', False))
    except AttributeError:
        return False


def record(game, event_type, **extra):
    """Queue ein Telemetry-Event fuer Background-Flush."""
    if not is_enabled(game):
        return
    payload = {
        'ts': int(time.time()),
        'event': event_type,
        'class': getattr(game.player, 'cls', '?'),
        'level': getattr(game.player, 'level', 0),
        'akt': len(getattr(game.player, 'completed_dungeons', ())),
        'play_time': int(getattr(game.player, 'prog_play_time_s', 0)),
        **extra,
    }
    flush_now = False
    with _QUEUE_LOCK:
        _QUEUE.append(payload)
        if len(_QUEUE) >= _QUEUE_HIGH_WATER:
            flush_now = True
    _ensure_flusher_running()
    if flush_now:
        # Synchron flushen — Queue ist voll und wir wollen RAM-Bound bleiben.
        # Passiert nur bei extrem hohem Event-Aufkommen (z.B. boss-spam).
        _drain_and_write()


def record_death(game, cause='?'):
    record(game, 'death', cause=cause,
           hp_max=getattr(game.player, 'hp_max', 0))


def record_boss_kill(game, boss_kind, time_taken_s):
    record(game, 'boss_kill', boss=boss_kind,
           time_s=int(time_taken_s))


def record_session_start(game):
    record(game, 'session_start',
           hardcore=bool(getattr(game, 'hardcore', False)))


def record_session_end(game):
    record(game, 'session_end')
    # Bei session_end aggressiv flushen — sonst gehen die letzten Events
    # bei einem nicht-graceful Shutdown (Kill, Crash) verloren.
    _drain_and_write()


def summary(limit=200):
    """Returns aggregated summary of the last N events (for /telemetry-cmd)."""
    if not os.path.isfile(_path()):
        return {}
    out = {'death': 0, 'boss_kill': 0, 'session_start': 0}
    classes = {}
    bosses = {}
    try:
        with open(_path(), 'r', encoding='utf-8') as f:
            lines = f.readlines()[-limit:]
        for ln in lines:
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            ev = obj.get('event', '?')
            out[ev] = out.get(ev, 0) + 1
            cls = obj.get('class', '?')
            classes[cls] = classes.get(cls, 0) + 1
            if ev == 'boss_kill':
                b = obj.get('boss', '?')
                bosses[b] = bosses.get(b, 0) + 1
    except OSError:
        pass
    out['classes'] = classes
    out['bosses'] = bosses
    return out
