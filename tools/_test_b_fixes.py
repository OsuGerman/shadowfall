"""Verifikations-Tests fuer Audit #179 Sektion B (B.3, B.4, B.7)."""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Force ASYNC for testing — Smoke-Tests sind sync, hier wollen wir async.
os.environ.pop('SDL_VIDEODRIVER', None)
os.environ.pop('SHADOWFALL_SAVE_SYNC', None)


def test_b3_aliases_in_registry():
    """B.3: Alias-Maps sind in sprite_registry, sprites.py re-exportiert."""
    from sf import sprite_registry as _reg
    from sf import sprites as _sp
    # Direkt aus Registry
    assert _reg.resolve_class('mage') == 'sorceress'
    assert _reg.resolve_mob('glaslord') == 'glaslord_senator_geist_akt_2'
    assert _reg.resolve_portrait('korven') == 'korven_vor_soeldnermeister'
    assert _reg.resolve_boss('vehren') == 'vehren'
    # Backward-Compat in sprites.py
    assert _sp.CLASS_SPRITE_ALIAS['mage'] == 'sorceress'
    assert _sp.MOB_SPRITE_ALIAS['glaslord'] == 'glaslord_senator_geist_akt_2'
    print("  B.3 OK: 5 Aliase aus sprite_registry abrufbar, "
          "Re-Exports in sprites.py funktionieren")
    return True


def test_b4_trace_swallowed_helper():
    """B.4: trace_swallowed schreibt in Ring-Buffer wenn ENV gesetzt."""
    from sf import crash_logger as _cl
    # Force enable
    _cl._TRACE_SWALLOWED = True
    _cl._TRACE_TO_STDERR = False
    _cl._recent_events.clear()
    try:
        raise RuntimeError("synth-exception")
    except Exception:
        _cl.trace_swallowed('test.b4.synth')
    found = [e for e in _cl._recent_events if 'test.b4.synth' in e]
    assert found, f"trace_swallowed schrieb nichts. events={_cl._recent_events}"
    assert 'RuntimeError' in found[0]
    print(f"  B.4 OK: trace_swallowed schreibt event: '{found[0]}'")
    # Cleanup
    _cl._TRACE_SWALLOWED = False
    return True


def test_b4_lazy_import_specific():
    """B.4: Game.__init__-Lazy-Imports fangen jetzt (ImportError, AttributeError)."""
    import os
    os.environ['SDL_VIDEODRIVER'] = 'dummy'
    os.environ['SDL_AUDIODRIVER'] = 'dummy'
    import pygame
    pygame.init()
    pygame.mixer.init()
    pygame.display.set_mode((1280, 720))
    from sf.game import Game
    g = Game()
    # Diese Felder MUESSEN existieren (auch wenn Module nicht da sind)
    assert hasattr(g, 'physics')
    assert hasattr(g, 'mod_loader')
    assert hasattr(g, 'replay_recorder')
    print(f"  B.4 OK: Game(): physics={g.physics is not None}, "
          f"mod_loader={g.mod_loader is not None}, "
          f"replay_recorder={g.replay_recorder is not None}")
    return True


def test_b7_telemetry_async_queue():
    """B.7: telemetry.record() queued statt sync zu schreiben."""
    from sf import telemetry as _tel
    # Mock-Game mit telemetry-Setting enabled
    class _MG:
        class _MP:
            cls = 'warrior'
            level = 5
            completed_dungeons = ()
            prog_play_time_s = 0
        player = _MP()
        settings = {'telemetry': True}
        hardcore = False
    g = _MG()
    # Queue leeren falls vorher Events drin
    with _tel._QUEUE_LOCK:
        _tel._QUEUE.clear()
    # 5 Events queuen
    for i in range(5):
        _tel.record(g, f'test_event_{i}', detail=i)
    with _tel._QUEUE_LOCK:
        assert len(_tel._QUEUE) == 5, f"Queue size: {len(_tel._QUEUE)}"
    # Flush
    _tel._drain_and_write()
    with _tel._QUEUE_LOCK:
        assert len(_tel._QUEUE) == 0, "Queue nicht geleert nach drain"
    print(f"  B.7 OK: Telemetry queued 5 events, drain leert Queue")
    return True


def test_b7_save_async_helper_exists():
    """B.7: save.py exportiert _write_save_text + atomic helper."""
    from sf import save as _save
    assert hasattr(_save, '_atomic_write_text')
    assert hasattr(_save, '_write_save_text')
    assert hasattr(_save, 'shutdown_save_worker')
    print(f"  B.7 OK: Async-Save API vorhanden "
          f"(_atomic_write_text, _write_save_text, shutdown_save_worker)")
    return True


def test_b7_atomic_write_works():
    """B.7: _atomic_write_text schreibt Datei korrekt."""
    from sf.save import _atomic_write_text
    from pathlib import Path
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        target = Path(td) / 'test.json'
        ok = _atomic_write_text(target, '{"hello": "world"}')
        assert ok, "atomic_write_text returned False"
        assert target.exists()
        assert target.read_text() == '{"hello": "world"}'
        # tmp-File darf nicht uebrig sein
        tmp = target.with_suffix(target.suffix + '.tmp')
        assert not tmp.exists(), f"tmp-File leak: {tmp}"
    print(f"  B.7 OK: atomic write-then-rename funktioniert, kein tmp-leak")
    return True


def main():
    tests = [
        ('B.3 Aliases in registry',     test_b3_aliases_in_registry),
        ('B.4 trace_swallowed',         test_b4_trace_swallowed_helper),
        ('B.4 Lazy-Import specific',    test_b4_lazy_import_specific),
        ('B.7 Telemetry async queue',   test_b7_telemetry_async_queue),
        ('B.7 Save API present',        test_b7_save_async_helper_exists),
        ('B.7 Atomic write',            test_b7_atomic_write_works),
    ]
    passed = 0
    for name, fn in tests:
        print(f"[{name}]")
        try:
            if fn():
                passed += 1
            else:
                print(f"  -> FAIL")
        except Exception as e:
            import traceback
            traceback.print_exc()
            print(f"  -> CRASH: {e}")
    print(f"\n{passed}/{len(tests)} passed")
    # Cleanup Background-Threads
    try:
        from sf import telemetry as _t
        _t.shutdown_flusher(timeout=1.0)
    except Exception:
        pass
    try:
        from sf import save as _s
        _s.shutdown_save_worker(timeout=1.0)
    except Exception:
        pass
    return 0 if passed == len(tests) else 1


if __name__ == '__main__':
    sys.exit(main())
