"""Profiler-Mode (PLAN AA-07) + Frame-Time-Sections (Audit #179 C.13).

Setting `dev_profiler` aktiv → cProfile umschliesst update()/draw().
Beim Quit: Top-30 Funktionen nach `profile.txt`.

Audit #179 C.13: Zusätzlich ein LIGHTWEIGHT Frame-Time-Tracker (immer
aktiv, ~0.1us Overhead pro Section). Section-Timings werden im F3-Debug-
Overlay angezeigt — kein separates Hotkey noetig.

API:
    from sf import profiler
    profiler.maybe_start(game)        # cProfile-Recording (opt-in)
    profiler.maybe_stop_and_dump(game)

    # Frame-Time-Sections (Audit #179 C.13, always-on):
    with profiler.section('update'):
        game.update(dt)
    summary = profiler.frame_summary()  # dict: {section: avg_ms}
"""

import cProfile
import io
import os
import pstats
import time as _time
from collections import deque


_profiler = None
_PROFILE_PATH = 'profile.txt'


def is_enabled(game):
    try:
        return bool(game.settings.get('dev_profiler', False))
    except Exception:
        return False


def maybe_start(game):
    """Start cProfile recording if enabled (called once per session)."""
    global _profiler
    if _profiler is not None:
        return
    if not is_enabled(game):
        return
    _profiler = cProfile.Profile()
    _profiler.enable()


def maybe_stop_and_dump(game):
    """Stop + dump on quit."""
    global _profiler
    if _profiler is None:
        return
    try:
        _profiler.disable()
        buf = io.StringIO()
        stats = pstats.Stats(_profiler, stream=buf)
        stats.strip_dirs().sort_stats('cumulative')
        stats.print_stats(30)
        with open(_PROFILE_PATH, 'w', encoding='utf-8') as f:
            f.write(buf.getvalue())
    except Exception:
        pass
    finally:
        _profiler = None


# ============================================================
# Audit #179 C.13: Lightweight Frame-Time-Sections
# ============================================================
# Pro Section halten wir einen Ring-Buffer der letzten 60 Frames vor.
# Summary returnt avg_ms pro Section — wird im F3-Debug-Overlay als
# "update: 4.2 ms" usw. dargestellt.

_SECTION_HISTORY: dict[str, deque] = {}
_HISTORY_LEN = 60   # ~1 Sekunde bei 60 FPS


class _SectionTimer:
    """Context-Manager fuer `with profiler.section('label'):`."""
    __slots__ = ('label', '_t0')

    def __init__(self, label):
        self.label = label
        self._t0 = 0.0

    def __enter__(self):
        self._t0 = _time.perf_counter()
        return self

    def __exit__(self, *_exc):
        elapsed_ms = (_time.perf_counter() - self._t0) * 1000.0
        buf = _SECTION_HISTORY.get(self.label)
        if buf is None:
            _SECTION_HISTORY[self.label] = buf = deque(maxlen=_HISTORY_LEN)
        buf.append(elapsed_ms)
        return False   # exception propagieren


def section(label):
    """Returnt einen Context-Manager der die Dauer in den Ring-Buffer
    schreibt. Usage: `with profiler.section('update'): ...`.
    """
    return _SectionTimer(label)


def frame_summary():
    """Returnt `{section_label: avg_ms}` ueber die letzten 60 Frames.

    Sortiert absteigend nach avg_ms — die langsamste Section zuerst.
    Leere Sections (noch keine Samples) werden ausgelassen.
    """
    out = {}
    for label, buf in _SECTION_HISTORY.items():
        if not buf:
            continue
        out[label] = sum(buf) / len(buf)
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def reset_sections():
    """Loescht alle Section-Buffers (z.B. nach Scene-Wechsel)."""
    _SECTION_HISTORY.clear()
