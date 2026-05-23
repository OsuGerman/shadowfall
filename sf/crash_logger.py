"""Crash-Logger (Update #137 — AA-03).

Globaler `sys.excepthook` schreibt unhandled exceptions in eine
`crashes/<timestamp>.log` Datei mit Stack-Trace + Save-State-Snapshot.
Macht Bug-Repro deutlich einfacher: ein User kann die crash-log-Datei
schicken statt zu beschreiben „es ist abgestürzt".

API:
    crash_logger.install(game)        — installiert den excepthook
    crash_logger.uninstall()          — stellt den Original-Hook wieder her
    crash_logger.write_crash(exc, tb) — manueller Crash-Log (z.B. aus Try-Catch)

Crash-Log-Format:
    [timestamp]
    Python: <version>
    Game-Version: SAVE_VERSION
    Game-State: <area / state / modal / player.cls / player.level / hp>
    Recent log-events (last 50)
    ---
    Traceback (most recent call last):
    ...
"""

import os
import sys
import time
import traceback
from pathlib import Path


# Wohin Crashes geschrieben werden — relativ zum Working-Directory
CRASH_DIR = Path('crashes')

# Original-Hook für uninstall()
_original_excepthook = None
# Game-Referenz für Snapshot — wird in install() gesetzt
_game_ref = None
# In-Memory-Ring-Buffer mit letzten Events (Push via append_event())
_recent_events = []
_MAX_RECENT = 50


def _ensure_crash_dir():
    """Stellt sicher dass crashes/ existiert.  Failt silently."""
    try:
        CRASH_DIR.mkdir(parents=True, exist_ok=True)
        return True
    except OSError:
        return False


def append_event(text):
    """Push einen Event-String in den Ring-Buffer.  Bei Crash werden
    die letzten N Events mitgeschrieben damit man den Verlauf vor
    dem Crash sieht.
    """
    _recent_events.append(f'[{time.strftime("%H:%M:%S")}] {text}')
    if len(_recent_events) > _MAX_RECENT:
        del _recent_events[0]


def _game_snapshot():
    """Returnt eine kurze Beschreibung des aktuellen Game-States als String."""
    g = _game_ref
    if g is None:
        return '(no game reference set)'
    lines = []
    try:
        lines.append(f'state={getattr(g, "state", "?")}')
        lines.append(f'area={getattr(g, "area", "?")}')
        lines.append(f'modal={getattr(g, "modal", "?")}')
        lines.append(f'biome={getattr(g, "biome", "?")}')
        lines.append(f'hardcore={getattr(g, "hardcore", False)}')
        p = getattr(g, 'player', None)
        if p is not None:
            lines.append(f'player.cls={getattr(p, "cls", "?")}')
            lines.append(f'player.level={getattr(p, "level", "?")}')
            lines.append(f'player.hp={getattr(p, "hp", "?")}')
            lines.append(f'player.pos=({p.pos.x:.0f}, {p.pos.y:.0f})'
                          if hasattr(p, 'pos') else 'player.pos=?')
        lines.append(f'enemies={len(getattr(g, "enemies", []))}')
        lines.append(f'projectiles={len(getattr(g, "projectiles", []))}')
        lines.append(f'particles={len(getattr(g, "particles", []))}')
    except Exception as snap_err:
        lines.append(f'(snapshot-error: {snap_err})')
    return '\n'.join('  ' + l for l in lines)


def write_crash(exc_type, exc_value, exc_tb):
    """Schreibt einen Crash-Log und returnt den Pfad (oder None bei Fehler)."""
    if not _ensure_crash_dir():
        return None
    ts = time.strftime('%Y%m%d_%H%M%S')
    path = CRASH_DIR / f'crash_{ts}.log'
    try:
        from . import save as _save
        save_version = _save.SAVE_VERSION
    except Exception:
        save_version = '?'
    try:
        with path.open('w', encoding='utf-8') as f:
            f.write(f'Shadowfall — Crash-Log\n')
            f.write(f'Timestamp: {time.strftime("%Y-%m-%d %H:%M:%S")}\n')
            f.write(f'Python:    {sys.version.split()[0]} on {sys.platform}\n')
            f.write(f'SAVE_VERSION: {save_version}\n')
            f.write('\nGame-State-Snapshot:\n')
            f.write(_game_snapshot())
            f.write('\n\nRecent events (last %d):\n' % _MAX_RECENT)
            for ev in _recent_events:
                f.write('  ' + ev + '\n')
            f.write('\n' + '-' * 60 + '\n')
            f.write('Traceback (most recent call last):\n')
            traceback.print_exception(exc_type, exc_value, exc_tb,
                                       file=f)
        return path
    except Exception:
        return None


def _crash_hook(exc_type, exc_value, exc_tb):
    """sys.excepthook-Implementation: schreibt Log + ruft Original-Hook."""
    try:
        path = write_crash(exc_type, exc_value, exc_tb)
        if path is not None:
            sys.stderr.write(f'\n[crash_logger] Crash-Log: {path}\n')
    except Exception:
        pass
    # Original-Hook (Default-Verhalten = stderr-Trace)
    if _original_excepthook is not None:
        _original_excepthook(exc_type, exc_value, exc_tb)


def install(game=None):
    """Installiert den globalen Crash-Logger.  Optional `game`-Referenz
    für den State-Snapshot bei Crash.
    """
    global _original_excepthook, _game_ref
    if _original_excepthook is None:
        _original_excepthook = sys.excepthook
    sys.excepthook = _crash_hook
    _game_ref = game


def uninstall():
    """Restauriert den Original-Excepthook.  Hauptsächlich für Tests."""
    global _original_excepthook, _game_ref
    if _original_excepthook is not None:
        sys.excepthook = _original_excepthook
        _original_excepthook = None
    _game_ref = None
    _recent_events.clear()
