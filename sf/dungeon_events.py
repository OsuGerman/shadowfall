"""Dynamic Dungeon Events (Update #27).

User-Feedback: „Welten sind langweilig". Statische Räume → tot.
Lösung: Pro Dungeon einige RÄUME bekommen ein „Event"-Tag das beim
ersten Player-Entry feuert:

- AMBUSH       — Wand-Spawns + Floater + Sound. Player wird überrascht.
- ALTAR        — kleine Decor (cursed_altar), bei Berührung Buff/Debuff.
- TREASURE_HOARD — viele Gold-Stapel + 1 garantiertes Magic+ Item.
- LORE_ECHO    — bei Entry feuert Voice-Quote als Toast (Mara, Korven).
- RUNE_CIRCLE  — 4 Runen am Boden, Stand-In für 2s = +30% Damage 8s.

Lore-Anker: VELGRAD_LORE_BIBEL.md (Echos in Akt 2/5, Mahnmal-Marken
in Akt 1, Tribunal-Altäre in Akt 3). Event-Pool ist biome-gefiltert
damit Akt-Stimmung erhalten bleibt.
"""

import math
import random

from .entities import Decor


# ============================================================
# Event-Pool pro Biome (Lore-konform)
# ============================================================
BIOME_EVENT_POOL = {
    # Update #35: Mehr Variation pro Biome — jedes Biome hat eigene Event-
    # Wahrscheinlichkeiten. Lava bekommt mehr Altare (Inquisitor-Sekte),
    # Astral mehr Rune-Kreise (Spiegelhof-Mystik), etc.
    # Update #44: NEUER Event-Typ `underworld_rift` — pro Biome max 1 Slot,
    # spawnt eine Riss-Decor; Spieler kann freiwillig hinein laufen für
    # schwerere Welle + besseren Loot (User-Wunsch „Unterwelt-Event im
    # selben Dungeon"). Niedrige Wahrscheinlichkeit, max 1× pro Run.
    'crypt':  ['ambush', 'altar', 'lore_echo', 'treasure_hoard',
                'ambush', 'lore_echo', 'underworld_rift'],
    'frost':  ['ambush', 'lore_echo', 'rune_circle', 'treasure_hoard',
                'lore_echo', 'rune_circle', 'underworld_rift'],
    'lava':   ['altar', 'ambush', 'rune_circle', 'lore_echo',
                'altar', 'ambush', 'underworld_rift'],
    'swamp':  ['ambush', 'altar', 'lore_echo', 'treasure_hoard',
                'altar', 'rune_circle', 'underworld_rift'],
    'astral': ['rune_circle', 'lore_echo', 'treasure_hoard', 'ambush',
                'rune_circle', 'rune_circle', 'underworld_rift'],
    'desert': ['ambush', 'treasure_hoard', 'lore_echo', 'rune_circle',
                'ambush', 'treasure_hoard', 'underworld_rift'],
}

# Pro Dungeon: wie viele Events platzieren? Update #35: erhöht.
EVENTS_PER_DUNGEON = (3, 6)


# ============================================================
# Lore-Echo Voice-Lines pro Biome (Akt-Lore-Anker)
# ============================================================
ECHO_LINES = {
    'crypt': [
        ('Mara die Mahnerin', '„Hier gingen drei Schiffe unter. Niemand suchte nach ihnen."',
         (140, 60, 180)),
        ('Korven Vor', '„Wenn du etwas findest, das einen Namen hat — '
                       'bring es mir."', (120, 90, 50)),
        ('Salzgeist', '„...niemand kam mehr..." (Echo wiederholt sich)',
         (180, 200, 220)),
    ],
    'frost': [
        ('Bruder Helst', '„Die Senatoren reden noch. Achtundhundert Jahre. '
                          'Keine einigt sich."', (200, 180, 140)),
        ('Echo-Senator', '„Und der Senat beschloss... und der Senat beschloss..."',
         (220, 200, 100)),
    ],
    'lava': [
        ('Inquisitor (fern)', '„Im-Nesh berührt dich. Du erinnerst falsch."',
         (255, 140, 60)),
        ('Valsa-Asche', '„...Valsa..." (Geflüster aus den Säulen)',
         (255, 180, 80)),
    ],
    'swamp': [
        ('Vossharil', '„Du wirst zurückkommen. Dreimal."',
         (200, 80, 160)),
        ('Knochenwitwe', '„Shulavhs Faden hält dich — oder zieht dich hinein."',
         (180, 100, 200)),
    ],
    'astral': [
        ('Mara die Mahnerin', '„Du hast das schon getan. Oder noch nicht."',
         (140, 60, 180)),
        ('Geist-Senator', '„Eine Stunde hier ist drei draußen."',
         (200, 180, 240)),
    ],
    'desert': [
        ('Tameris', '„Meine Schwester ging hier durch. Ich finde keine Spur."',
         (160, 140, 80)),
        ('Speerschwester-Echo', '„Zhar-Eth ist gewandert. Wir bleiben hier."',
         (240, 200, 100)),
    ],
}


# ============================================================
# Altar-Effekte (Buff/Debuff bei Berührung)
# ============================================================
ALTAR_EFFECTS = [
    # (label, color, on_touch lambda(game) → None, lore_text)
    ('Altar der Form (Kharn)', (220, 160, 80),
     lambda game: _apply_buff(game, 'damage', 0.30, 25.0,
                               '+30% Schaden für 25s — Kharn nimmt deinen Kampf an.'),
     'Steinerner Altar mit Eisen-Bändern.'),
    ('Altar des Ersten Atems (Aithein)', (255, 215, 100),
     lambda game: _apply_heal(game, 0.5, 'Geheilt — Aithein atmet in dich.'),
     'Goldgravierter Altar, pulsiert sanft.'),
    ('Altar der Zeit (Nheyra)', (180, 200, 220),
     lambda game: _apply_buff(game, 'speed', 0.40, 20.0,
                               '+40% Tempo für 20s — Nheyras Zeit verlangsamt sich um dich.'),
     'Spiegel-Altar, dein Spiegelbild verzögert.'),
    ('Altar des Vergessens (der Siebte)', (60, 30, 80),
     lambda game: _apply_debuff(game, 'damage_taken', 0.15, 15.0,
                                 '−15% Damage Taken für 15s — der Siebte hält die Welt zurück.'),
     'Schwarzer Altar mit der Kontur eines Mundes.'),
]


# ============================================================
# Event-Platzierung (wird in dungeon.py aufgerufen)
# ============================================================
def assign_room_events(grid, biome, rng=None):
    """Wählt 2-4 Räume aus und gibt ihnen ein Event-Tag.

    Spawn-/Boss-/Secret-Räume werden nie zu Event-Räumen.
    Returnt None — modifiziert grid.rooms in-place via `room.event`.
    """
    if rng is None:
        rng = random.Random()
    pool = list(BIOME_EVENT_POOL.get(biome, ['ambush', 'lore_echo']))
    candidates = [r for r in grid.rooms
                  if r.kind in ('normal', 'fountain', 'library')]
    rng.shuffle(candidates)
    n = rng.randint(*EVENTS_PER_DUNGEON)
    rift_placed = False
    for room in candidates[:n]:
        kind = rng.choice(pool)
        # Update #44: underworld_rift max 1× pro Dungeon
        if kind == 'underworld_rift':
            if rift_placed:
                # Re-pick ohne rift im Pool
                alt_pool = [k for k in pool if k != 'underworld_rift']
                kind = rng.choice(alt_pool) if alt_pool else 'ambush'
            else:
                rift_placed = True
        room.event = kind
        room.event_triggered = False


# ============================================================
# Decor-Anchor pro Event (wird mit Boss-/Treasure-Decor zusammen platziert)
# ============================================================
def make_event_decor(room, grid, biome, rng):
    """Returnt Liste von Decor-Objekten für ein Event-Room."""
    decors = []
    event = getattr(room, 'event', None)
    if event is None:
        return decors
    cx, cy = room.center()
    wx, wy = grid.cell_to_world_center(cx, cy)

    if event == 'altar':
        # Steinerner Altar (cursed_altar) in der Mitte
        altar_idx = rng.randint(0, len(ALTAR_EFFECTS) - 1)
        d = Decor(wx, wy, 'cursed_altar', 0, 60, 0.2, collide_radius=16)
        d.altar_idx = altar_idx
        d.altar_used = False
        decors.append(d)
        # 4 Kerzen rundherum
        for k in range(4):
            a = (k / 4) * math.tau + math.pi / 4
            decors.append(Decor(wx + math.cos(a) * 50,
                                wy + math.sin(a) * 50, 'torch'))

    elif event == 'rune_circle':
        # 6 Runen im Kreis + leichte Schwellen-Markierung
        for k in range(6):
            a = (k / 6) * math.tau
            decors.append(Decor(wx + math.cos(a) * 55,
                                wy + math.sin(a) * 55, 'rune'))
        d = Decor(wx, wy, 'rune_anchor', 0, 50, 0.0, collide_radius=0)
        d.rune_active = False
        d.rune_t = 0.0
        decors.append(d)

    elif event == 'treasure_hoard':
        # 2-3 Truhen + 4 Mahnmal-Stelen flankieren
        n_chests = rng.randint(2, 3)
        for k in range(n_chests):
            a = (k / n_chests) * math.tau + math.pi / 4
            decors.append(Decor(wx + math.cos(a) * 40,
                                wy + math.sin(a) * 40, 'chest_decor',
                                0, 50, 0.2))
        for k in range(4):
            a = (k / 4) * math.tau
            decors.append(Decor(wx + math.cos(a) * 80,
                                wy + math.sin(a) * 80,
                                'mahnmal_stele', 0, 40, 0.18,
                                collide_radius=10))

    elif event == 'ambush':
        # Visueller Hint: 4 zerbrochene Säulen markieren das Killing-Field
        for k in range(4):
            a = (k / 4) * math.tau + math.pi / 4
            decors.append(Decor(wx + math.cos(a) * 60,
                                wy + math.sin(a) * 60, 'broken_wall',
                                rng.uniform(0, math.tau), 40, 0.15,
                                collide_radius=10))

    elif event == 'lore_echo':
        # Marker am Boden — ein Mahnmal-Stein mit Glow
        decors.append(Decor(wx, wy, 'mahnmal_stele', 0, 50, 0.2,
                            collide_radius=10))
        # Eine Lore-Tafel daneben
        d = Decor(wx + 40, wy, 'lore_tablet', 0, 50, 0.2)
        echoes = ECHO_LINES.get(biome, [])
        if echoes:
            speaker, line, _ = rng.choice(echoes)
            d.lore_text = f'{speaker}: {line}'
            d.lore_read = False
        decors.append(d)

    elif event == 'underworld_rift':
        # Update #44: Unterwelt-Riss — animierter Riss in der Raummitte.
        # Spieler kann freiwillig hineinlaufen für eine schwere Welle
        # (8-12 Elite-Spawns + besserer Loot). Klar markiert mit 4
        # Knochen-Stelen, damit man's nicht versehentlich auslöst.
        d = Decor(wx, wy, 'underworld_rift', 0, 80, 0.0, collide_radius=0)
        d.rift_used = False
        d.room_cx = cx
        d.room_cy = cy
        decors.append(d)
        # 4 Warn-Stelen
        for k in range(4):
            a = (k / 4) * math.tau + math.pi / 4
            decors.append(Decor(wx + math.cos(a) * 70,
                                wy + math.sin(a) * 70,
                                'mahnmal_stele', rng.uniform(0, math.tau),
                                40, 0.2, collide_radius=10))

    return decors


# ============================================================
# Event-Trigger (wird in game.update aufgerufen wenn player Raum betritt)
# ============================================================
def trigger_event(game, room):
    """Feuert das Event-für-Room-Verhalten. Wird einmal pro Room ausgelöst.

    Returnt True wenn ein Event gefeuert wurde.
    """
    event = getattr(room, 'event', None)
    if event is None or getattr(room, 'event_triggered', False):
        return False
    room.event_triggered = True
    biome = game.biome

    if event == 'ambush':
        _trigger_ambush(game, room, biome)
    elif event == 'lore_echo':
        _trigger_lore_echo(game, room, biome)
    elif event == 'treasure_hoard':
        _trigger_treasure_hoard(game, room, biome)
    elif event == 'underworld_rift':
        _announce_rift(game, room, biome)
    # altar + rune_circle + underworld_rift sind passiv (Player muss berühren)
    return True


def _announce_rift(game, room, biome):
    """Update #44: Toast bei Raum-Entry — kein automatischer Spawn."""
    try:
        game.push_event_notification(
            'story', 'UNTERWELT-RISS',
            sub='Ein pulsierender Riss. Wage dich hinein für schwere Beute.',
            color=(180, 80, 220), duration=4.0)
    except Exception:
        pass
    try:
        from . import sounds as _snd
        # Update #X — Phase-3-AI: Rift-Warning (lore-spezifisch statt boss_intro)
        _snd.play('event_rift_warning', volume=0.5)
    except Exception:
        pass


def interact_underworld_rift(game, decor):
    """Update #44: Spieler läuft in den Riss → schwere Elite-Welle spawnt
    direkt im Raum, mit garantiertem Loot beim Clear.

    Lore: Unterwelt = das was Velgrad VOR der Salzwunde war. Spieler
    erinnert sich an verbotene Form (Im-Nesh berührt ihn).
    """
    if getattr(decor, 'rift_used', False):
        return False
    d2 = ((decor.x - game.player.pos.x) ** 2 +
          (decor.y - game.player.pos.y) ** 2)
    if d2 > 30 ** 2:
        return False
    decor.rift_used = True
    # 8-12 starke Elite-Spawns rund um den Riss
    from . import enemies as en_mod
    biome = game.biome
    BIOME_RIFT_POOL = {
        'crypt':  ['wraith', 'demon', 'berserker'],
        'frost':  ['wraith', 'berserker', 'brute'],
        'lava':   ['demon', 'brute', 'berserker'],
        'swamp':  ['shaman', 'warlock', 'berserker'],
        'astral': ['wraith', 'warlock', 'lurker'],
        'desert': ['berserker', 'brute', 'shaman'],
    }
    pool = BIOME_RIFT_POOL.get(biome, ['demon', 'berserker'])
    wave = max(1, game.player.level + 2)  # +2 Level für mehr Druck
    n = random.randint(8, 12)
    for k in range(n):
        ang = (k / n) * math.tau + random.uniform(-0.15, 0.15)
        rad = random.uniform(80, 160)
        ex = decor.x + math.cos(ang) * rad
        ey = decor.y + math.sin(ang) * rad
        e = en_mod.spawn_enemy(random.choice(pool), ex, ey, wave,
                                elite_chance=0.65)  # 65 % Elite!
        if hasattr(e, 'ai_state'):
            from . import ai as _ai
            e.ai_state = _ai.AIState.AGGRO
            e.last_known_player_pos = (game.player.pos.x, game.player.pos.y)
        # +50 % HP/DMG da Rift-Mobs
        e.hp_max *= 1.5
        e.hp = e.hp_max
        e.dmg *= 1.3
        e.xp = int(e.xp * 1.6)
        e.gold_range = (int(e.gold_range[0] * 1.8),
                         int(e.gold_range[1] * 1.8))
        # Mark als Rift-Mob für Tracking + Loot-Bonus beim Tod
        e._rift_spawned = True
        game.enemies.append(e)
    # Riss-Visual: dunkler Pulse + Shake + Voice-Line
    try:
        game.push_event_notification(
            'story', 'DER RISS ÖFFNET SICH',
            sub=f'{n} Wesen aus der verbotenen Form steigen hervor.',
            color=(180, 80, 220), duration=4.5)
    except Exception:
        pass
    game.shake = max(getattr(game, 'shake', 0), 18)
    if hasattr(game, '_damage_flash'):
        game._damage_flash = max(game._damage_flash, 0.5)
    try:
        from . import sounds as _snd
        _snd.play('boss_intro', volume=0.8)
        _snd.play('roar', volume=0.6)
    except Exception:
        pass
    # Particles: dunkler Riss-Explosion
    for _ in range(40):
        game.spawn_particles(decor.x, decor.y, 1, (180, 80, 220),
                              life_max=1.0, size_max=8)
    return True


def _trigger_ambush(game, room, biome):
    """Spawnt 3-6 Mobs an Raum-Ecken."""
    from . import enemies as en_mod
    grid = game.grid
    if grid is None:
        return
    # Update #44: neue Bestiarium-Mobs in den Biome-Ambush-Pools
    BIOME_AMBUSH_POOL = {
        'crypt':  ['zombie', 'skeleton', 'wraith', 'salzgeist'],
        'frost':  ['skeleton', 'wraith', 'glaslord'],
        'lava':   ['demon', 'berserker', 'aschenbrut', 'aschenbrut'],
        'swamp':  ['zombie', 'shaman', 'wurzelhueter'],
        'astral': ['wraith', 'shaman'],
        'desert': ['skeleton', 'berserker'],
    }
    pool = BIOME_AMBUSH_POOL.get(biome, ['zombie'])
    wave = max(1, game.player.level)
    spawn_positions = [
        (room.x + 1, room.y + 1),
        (room.x + room.w - 2, room.y + 1),
        (room.x + 1, room.y + room.h - 2),
        (room.x + room.w - 2, room.y + room.h - 2),
    ]
    n = random.randint(3, min(6, len(spawn_positions) + 2))
    for k in range(n):
        ax, ay = spawn_positions[k % len(spawn_positions)]
        wx, wy = grid.cell_to_world_center(ax, ay)
        e = en_mod.spawn_enemy(random.choice(pool), wx, wy, wave,
                                elite_chance=0.10)
        # AGGRESSIV vom Start: direkt AGGRO statt IDLE
        if hasattr(e, 'ai_state'):
            from . import ai as _ai
            e.ai_state = _ai.AIState.AGGRO
            e.last_known_player_pos = (game.player.pos.x, game.player.pos.y)
        game.enemies.append(e)
    # Visible Feedback
    try:
        game.push_event_notification(
            'story', 'HINTERHALT!',
            sub=f'{n} Feinde aus dem Schatten — kämpfe oder fliehe.',
            color=(255, 80, 60), duration=3.4)
    except Exception:
        pass
    game.shake = max(getattr(game, 'shake', 0), 8)
    try:
        from . import sounds as _snd
        # Update #X — Phase-3-AI: Ambush-Warning statt generic roar
        _snd.play('event_ambush_warning', volume=0.6)
    except Exception:
        pass


def _trigger_lore_echo(game, room, biome):
    """Spielt eine Lore-Voice-Line als ambient-Toast."""
    echoes = ECHO_LINES.get(biome, [])
    if not echoes:
        return
    speaker, line, col = random.choice(echoes)
    try:
        game.push_event_notification(
            'story', f'{speaker}', sub=line,
            color=col, duration=5.0)
        game.push_event_log(f'„{line[:40]}..." — {speaker}',
                             col, duration=6.0)
        # Update #X — Phase-3-AI: Lore-Echo-Sound
        from . import sounds as _snd
        _snd.play('event_lore_echo', volume=0.45)
    except Exception:
        pass


def _trigger_treasure_hoard(game, room, biome):
    """Vorschau-Toast — Loot ist als chest_decor schon im Room."""
    try:
        game.push_event_notification(
            'currency', 'SCHATZKAMMER',
            sub='Mahnmal-Bergungsgut — Truhen warten.',
            color=(255, 220, 100), duration=3.4)
        game.push_event_log('Schatzkammer entdeckt',
                             (255, 220, 100), duration=6.0)
        from . import sounds as _snd
        # Update #X — Phase-3-AI: Treasure-Discover-Stinger statt pickup_gold
        _snd.play('event_treasure_discover', volume=0.5)
    except Exception:
        pass


# ============================================================
# Altar-Interaktion (Decor-Touch im game.update_loot oder _interact)
# ============================================================
def interact_altar(game, decor):
    """Decor-Touch: Altar-Effekt anwenden."""
    if getattr(decor, 'altar_used', False):
        return False
    idx = getattr(decor, 'altar_idx', 0)
    if 0 <= idx < len(ALTAR_EFFECTS):
        label, color, effect_fn, lore = ALTAR_EFFECTS[idx]
        try:
            effect_fn(game)
            game.push_event_notification(
                'story', label, sub=lore, color=color, duration=4.0)
            # Update #X — Phase-3-AI: Cursed-Altar-Sound (Buff oder Curse?
            # ALTAR_EFFECTS hat positive (heal/buff) + negative Effekte.
            # Erkennung via Label-Farbe: warm = blessing, kuehl = curse.
            from . import sounds as _snd
            r, g, b = color[:3]
            is_blessing = (g >= r) and (g >= b)  # gruener-Ton = blessing
            _snd.play('cursed_altar_blessing' if is_blessing
                      else 'cursed_altar_curse', volume=0.7)
        except Exception:
            pass
        decor.altar_used = True
        # Update #33: Progression-Tracker
        if hasattr(game.player, 'prog_altars_used'):
            game.player.prog_altars_used += 1
        return True
    return False


def interact_rune_circle(game, decor):
    """Stehe für 2 s im Kreis → +30 % Damage 8 s."""
    if getattr(decor, 'rune_active', False):
        return False
    d = ((decor.x - game.player.pos.x) ** 2 +
         (decor.y - game.player.pos.y) ** 2) ** 0.5
    if d > 40:
        decor.rune_t = 0.0
        return False
    decor.rune_t = getattr(decor, 'rune_t', 0.0) + 1.0 / 60.0
    if decor.rune_t >= 2.0:
        decor.rune_active = True
        _apply_buff(game, 'damage', 0.30, 8.0,
                     'Runenkreis: +30 % Schaden für 8 s')
        # Update #X — Phase-3-AI: Rune-Activation-Sound
        try:
            from . import sounds as _snd
            _snd.play('rune_anchor_activate', volume=0.7)
        except Exception:
            pass
        # Update #33: Progression-Tracker
        if hasattr(game.player, 'prog_runes_used'):
            game.player.prog_runes_used += 1
        return True
    return False


# ============================================================
# Buff-/Debuff-Helfer (kompakte Implementierung über player-Felder)
# ============================================================
def _apply_buff(game, key, amount, duration, label):
    """Generischer Player-Buff: speichert (key → (amount, time_left))."""
    if not hasattr(game.player, 'event_buffs'):
        game.player.event_buffs = {}
    game.player.event_buffs[key] = (amount, duration)
    try:
        game.toast(label, (200, 220, 140))
    except Exception:
        pass


def _apply_debuff(game, key, amount, duration, label):
    if not hasattr(game.player, 'event_buffs'):
        game.player.event_buffs = {}
    game.player.event_buffs[key] = (-amount, duration)
    try:
        game.toast(label, (220, 180, 140))
    except Exception:
        pass


def _apply_heal(game, frac, label):
    from . import progression
    eff = progression.effective(game.player)
    heal = eff['hp_max'] * frac
    game.player.hp = min(eff['hp_max'], game.player.hp + heal)
    try:
        game.toast(label, (140, 220, 160))
    except Exception:
        pass


def tick_event_buffs(game, dt):
    """Pro Frame: ticke Buff-Timer runter."""
    buffs = getattr(game.player, 'event_buffs', None)
    if not buffs:
        return
    for key in list(buffs.keys()):
        amt, t = buffs[key]
        t -= dt
        if t <= 0:
            del buffs[key]
        else:
            buffs[key] = (amt, t)


# ============================================================
# Player-Room-Tracking (in game.update aufrufen)
# ============================================================
def tick_player_in_room(game):
    """Findet den Raum, in dem der Spieler steht; feuert Event wenn neu.

    Auch: prüft Altar/Rune-Touch durch den player.
    """
    grid = getattr(game, 'grid', None)
    if grid is None:
        return
    px, py = game.player.pos.x, game.player.pos.y
    cx, cy = grid.world_to_cell(px, py)
    for room in grid.rooms:
        if room.contains_cell(cx, cy):
            trigger_event(game, room)
            break
    # Altar-/Rune-/Rift-Touch
    for decor in getattr(game, 'tiles', []):
        if decor.kind == 'cursed_altar':
            d2 = (decor.x - px) ** 2 + (decor.y - py) ** 2
            if d2 < 60 ** 2:
                interact_altar(game, decor)
        elif decor.kind == 'rune_anchor':
            interact_rune_circle(game, decor)
        elif decor.kind == 'underworld_rift':
            interact_underworld_rift(game, decor)
