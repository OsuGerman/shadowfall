"""Verifikations-Tests fuer Audit #179 Sektion C (C.3, C.4, C.8, C.9)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
pygame.mixer.init()
pygame.display.set_mode((1280, 720))


def test_c3_save_version_too_new():
    """C.3: migrate_save() wirft SaveVersionTooNewError statt still-downgrade."""
    from sf.save import migrate_save, SaveVersionTooNewError, SAVE_VERSION
    fake_future_save = {'version': SAVE_VERSION + 1, 'player': {}}
    try:
        migrate_save(fake_future_save)
    except SaveVersionTooNewError as exc:
        assert exc.save_version == SAVE_VERSION + 1
        assert exc.current_version == SAVE_VERSION
        print(f"  C.3 OK: SaveVersionTooNewError raised "
              f"(v{exc.save_version} > v{exc.current_version})")
        return True
    print(f"  C.3 FAIL: kein Reject bei v{SAVE_VERSION + 1}")
    return False


def test_c3_save_version_compatible():
    """C.3: Normale (kleinere oder gleiche) Version migriert weiter normal."""
    from sf.save import migrate_save, SAVE_VERSION
    fake_save = {'version': 1, 'player': {}, 'time': 0}
    out = migrate_save(fake_save)
    assert out['version'] == SAVE_VERSION
    print(f"  C.3 OK: v1 -> v{SAVE_VERSION} Migration laeuft")
    return True


def test_c4_skill_cd_roundtrip():
    """C.4: skill_cd ueberlebt save/load roundtrip."""
    from sf.game import Game
    from sf import save as save_mod
    g = Game()
    g.start_game('adventure')
    # Simuliere ge-castete Skills mit CDs
    g.player.skill_cd['fireball'] = 12.5
    g.player.skill_cd['heal'] = 30.0
    # Save
    assert save_mod.save_game(g, slot=99), "save_game failed"
    # Reset CDs zu 0 (simuliert Reload)
    g.player.skill_cd['fireball'] = 0.0
    g.player.skill_cd['heal'] = 0.0
    # Load
    assert save_mod.load_game(g, slot=99), "load_game failed"
    # Verifiziere
    assert abs(g.player.skill_cd['fireball'] - 12.5) < 0.01, \
        f"fireball CD: {g.player.skill_cd['fireball']} != 12.5"
    assert abs(g.player.skill_cd['heal'] - 30.0) < 0.01, \
        f"heal CD: {g.player.skill_cd['heal']} != 30.0"
    print(f"  C.4 OK: skill_cd roundtrip "
          f"(fireball={g.player.skill_cd['fireball']:.1f}, "
          f"heal={g.player.skill_cd['heal']:.1f})")
    # Cleanup
    from sf.save import slot_path
    sp = slot_path(99)
    if sp.exists():
        sp.unlink()
    return True


def test_c8_crash_recovery_field_exists():
    """C.8: Game initialisiert pending_autosave_recovery + F8-Handler."""
    from sf.game import Game
    g = Game()
    assert hasattr(g, 'pending_autosave_recovery'), \
        "pending_autosave_recovery missing"
    assert hasattr(g, '_try_apply_crash_recovery'), \
        "_try_apply_crash_recovery method missing"
    print(f"  C.8 OK: pending_autosave_recovery={g.pending_autosave_recovery}, "
          f"handler-method existiert")
    return True


def test_c9_sound_stop_all_called_on_enter_town():
    """C.9: enter_town() ruft snd.stop_all() auf."""
    from sf.game import Game
    from sf import sounds as snd
    # Monkey-Patch stop_all um Aufruf zu zaehlen
    calls = [0]
    orig = snd.stop_all
    def counting_stop_all():
        calls[0] += 1
        orig()
    snd.stop_all = counting_stop_all
    try:
        g = Game()
        g.start_game('adventure')
        before = calls[0]
        # Simuliere dungeon → town
        g.area = 'dungeon'
        g.enter_town()
        assert calls[0] > before, \
            f"snd.stop_all() nicht gerufen (before={before}, after={calls[0]})"
        print(f"  C.9 OK: snd.stop_all() bei enter_town gerufen "
              f"(Calls: {calls[0] - before})")
    finally:
        snd.stop_all = orig
    return True


def main():
    tests = [
        ('C.3 SaveVersionTooNew',       test_c3_save_version_too_new),
        ('C.3 Migration v1->current',   test_c3_save_version_compatible),
        ('C.4 skill_cd roundtrip',      test_c4_skill_cd_roundtrip),
        ('C.8 Recovery-Hook present',   test_c8_crash_recovery_field_exists),
        ('C.9 stop_all on enter_town',  test_c9_sound_stop_all_called_on_enter_town),
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
    return 0 if passed == len(tests) else 1


if __name__ == '__main__':
    sys.exit(main())
