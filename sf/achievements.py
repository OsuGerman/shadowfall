"""Achievements: 15 Meilensteine mit Gold-Belohnungen.

Update #133 (Z-07): Pro Achievement zusätzlich `progress` + `target`
für Fortschritts-Anzeige im Codex (z.B. „47/100 Kills").
"""

ACHIEVEMENTS = [
    dict(id='first_kill',     name='Erster Blut',         desc='Erschlage deinen ersten Gegner',          reward=30,  check=lambda s: s.get('kills', 0) >= 1,                       progress=lambda s: s.get('kills', 0),                target=1),
    dict(id='hundred_kills',  name='Schlächter',          desc='100 Gegner erschlagen',                   reward=200, check=lambda s: s.get('kills', 0) >= 100,                     progress=lambda s: s.get('kills', 0),                target=100),
    dict(id='thousand_kills', name='Legion-Brecher',      desc='1000 Gegner erschlagen',                  reward=1500,check=lambda s: s.get('kills', 0) >= 1000,                    progress=lambda s: s.get('kills', 0),                target=1000),
    dict(id='first_boss',     name='Boss-Bezwinger',      desc='Besiege deinen ersten Boss',              reward=150, check=lambda s: s.get('bosses', 0) >= 1,                      progress=lambda s: s.get('bosses', 0),               target=1),
    dict(id='all_bosses',     name='Sammler der Krone',   desc='Besiege alle 7 verschiedenen Bosse',      reward=2000,check=lambda s: len(s.get('boss_kinds', [])) >= 7,             progress=lambda s: len(s.get('boss_kinds', [])),     target=7),
    dict(id='lvl10',          name='Adept',               desc='Erreiche Stufe 10',                       reward=200, check=lambda s: s.get('level', 1) >= 10,                      progress=lambda s: s.get('level', 1),                target=10),
    dict(id='lvl25',          name='Veteran',             desc='Erreiche Stufe 25',                       reward=800, check=lambda s: s.get('level', 1) >= 25,                      progress=lambda s: s.get('level', 1),                target=25),
    dict(id='lvl50',          name='Meister',             desc='Erreiche Stufe 50',                       reward=3000,check=lambda s: s.get('level', 1) >= 50,                      progress=lambda s: s.get('level', 1),                target=50),
    dict(id='rich',           name='Goldhamster',         desc='Sammle 10.000 Gold',                      reward=500, check=lambda s: s.get('total_gold', 0) >= 10000,              progress=lambda s: s.get('total_gold', 0),           target=10000),
    dict(id='first_dungeon',  name='Entdecker',           desc='Schließe deinen ersten Dungeon ab',       reward=100, check=lambda s: s.get('dungeons', 0) >= 1,                    progress=lambda s: s.get('dungeons', 0),             target=1),
    dict(id='all_dungeons',   name='Welt-Wanderer',       desc='Schließe alle Dungeons mindestens 1x ab', reward=1000,check=lambda s: len(s.get('dungeon_ids', [])) >= 3,            progress=lambda s: len(s.get('dungeon_ids', [])),    target=3),
    dict(id='unique_drop',    name='Einzigartiger Fund',  desc='Finde dein erstes Einzigartiges Item',    reward=400, check=lambda s: s.get('uniques_found', 0) >= 1,               progress=lambda s: s.get('uniques_found', 0),        target=1),
    dict(id='craft_master',   name='Werkstatt-Liebhaber', desc='Werte ein Item 5x auf',                   reward=300, check=lambda s: s.get('upgrades_done', 0) >= 5,               progress=lambda s: s.get('upgrades_done', 0),        target=5),
    dict(id='gem_socketed',   name='Juwelier',            desc='Sockle den ersten Edelstein',             reward=80,  check=lambda s: s.get('gems_socketed', 0) >= 1,               progress=lambda s: s.get('gems_socketed', 0),        target=1),
    dict(id='no_death',       name='Unsterblich',         desc='Schließe einen Dungeon ohne zu sterben',  reward=500, check=lambda s: s.get('flawless_dungeons', 0) >= 1,          progress=lambda s: s.get('flawless_dungeons', 0),    target=1),
]


def progress_for(ach, stats):
    """Returnt (current, target) für ein Achievement.

    Wenn `progress`/`target` nicht definiert sind, fällt auf
    (1 wenn done, 0 sonst) / 1 zurück.
    """
    try:
        cur = int(ach.get('progress', lambda s: 0)(stats))
        tgt = int(ach.get('target', 1))
    except Exception:
        cur, tgt = 0, 1
    cur = max(0, min(tgt, cur))
    return cur, max(1, tgt)


def check_all(game):
    """Prüft alle Achievements und vergibt Belohnungen für neu erreichte."""
    if not hasattr(game, 'achievements_done'):
        game.achievements_done = set()
    stats = getattr(game, 'stats', {})
    # Aktuelle abgeleitete Stats
    stats['level'] = game.player.level
    newly = []
    for a in ACHIEVEMENTS:
        if a['id'] in game.achievements_done:
            continue
        try:
            if a['check'](stats):
                game.achievements_done.add(a['id'])
                game.player.gold += a['reward']
                newly.append(a)
        except Exception:
            pass
    # Update #X — Phase-3-AI: Achievement-Unlock-Sound bei jedem neuen Achievement
    if newly:
        try:
            from . import sounds as _snd
            _snd.play('achievement_unlock', volume=0.7)
        except Exception:
            pass
    return newly


def init_stats(game):
    if not hasattr(game, 'stats') or not game.stats:
        game.stats = {
            'kills': 0, 'bosses': 0, 'dungeons': 0,
            'total_gold': 0, 'uniques_found': 0,
            'upgrades_done': 0, 'gems_socketed': 0,
            'flawless_dungeons': 0,
            'time_played': 0.0,
            'boss_kinds': [],
            'dungeon_ids': [],
        }
    if not hasattr(game, 'achievements_done'):
        game.achievements_done = set()


def on_kill(game, enemy):
    init_stats(game)
    game.stats['kills'] = game.stats.get('kills', 0) + 1
    if enemy.is_boss:
        game.stats['bosses'] = game.stats.get('bosses', 0) + 1
        kinds = game.stats.setdefault('boss_kinds', [])
        if enemy.boss_kind not in kinds:
            kinds.append(enemy.boss_kind)


def on_dungeon_complete(game, dungeon_id, flawless=False):
    init_stats(game)
    game.stats['dungeons'] = game.stats.get('dungeons', 0) + 1
    ids = game.stats.setdefault('dungeon_ids', [])
    if dungeon_id not in ids:
        ids.append(dungeon_id)
    if flawless:
        game.stats['flawless_dungeons'] = game.stats.get('flawless_dungeons', 0) + 1


def on_gold_gained(game, amount):
    init_stats(game)
    game.stats['total_gold'] = game.stats.get('total_gold', 0) + amount


def on_unique_drop(game):
    init_stats(game)
    game.stats['uniques_found'] = game.stats.get('uniques_found', 0) + 1


def on_upgrade(game):
    init_stats(game)
    game.stats['upgrades_done'] = game.stats.get('upgrades_done', 0) + 1


def on_socket(game):
    init_stats(game)
    game.stats['gems_socketed'] = game.stats.get('gems_socketed', 0) + 1
