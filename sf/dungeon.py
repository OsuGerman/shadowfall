"""Dungeon-Generation: nutzt Tile-Grid mit Räumen + Korridoren."""

import math
import random

from pygame.math import Vector2

from .constants import DUNGEONS
from .entities import Decor
from . import enemies as en_mod
from . import dungeon_gen
from . import world
from . import dungeon_events as _events


# Mini-Boss-Templates (schwächer als End-Boss, stärker als Elite)
MINI_BOSSES = {
    'crypt': dict(type='brute',    name='Knochenkönig',     hp_mult=3.0, dmg_mult=1.5),
    'frost': dict(type='wraith',   name='Frostwraith',      hp_mult=3.5, dmg_mult=1.4),
    'lava':  dict(type='demon',    name='Glutkrieger',      hp_mult=3.2, dmg_mult=1.6),
    'town':  dict(type='zombie',   name='Wanderer',         hp_mult=2.0, dmg_mult=1.2),
}


def generate_dungeon(dungeon_id, player_level):
    """Returnt: (grid, enemies, boss_pos, spec, decors, mini_bosses)

    Lore-Layout pro Biome:
      crypt  — Salzkrypta von Marrowport: schmal & klaustrophobisch (8 R.)
      frost  — Glasgoldene Ruinen: weitläufige Säulen-Halle (12 R.)
      lava   — Aschen-Hof (Säulen-von-Helst): zentraler Hof + Außenringe (10 R.)
      swamp  — Wurzelgrab: verwinkelt, viele Sackgassen (13 R.)
      astral — Spiegelhof von Velharn: symmetrisch (11 R.)
      desert — Zhar-Eth-Karawane: linearer Sandgrab-Pfad (9 R.)
    """
    spec = DUNGEONS[dungeon_id]
    biome = spec['biome']
    # Update #96 User-Wunsch: 40 % mehr Gegner pro Dungeon.
    enemy_count = int(spec['enemy_count'] * 1.40)

    # Biome-spezifische Room-Anzahl (Lore-konformes Layout-Feeling)
    # Update #43: Größere Dungeons (User „größere Dungeons sind sehr wichtig")
    rooms_for_biome = {
        'crypt':  13,
        'frost':  18,
        'lava':   15,
        'swamp':  18,
        'astral': 16,
        'desert': 14,
    }
    num_rooms = rooms_for_biome.get(biome, 15)
    # Grid auch größer (64×64 → 80×80) für mehr Raum-Spielraum
    grid = dungeon_gen.generate(num_rooms=num_rooms, w=80, h=80)

    # Update #27: Pro Dungeon 2-4 Räume bekommen ein Event-Tag.
    _events.assign_room_events(grid, biome, rng=random.Random())

    # Wave-skalierung
    wave_for_scaling = max(1, player_level + 1)

    enemies_list = []
    mini_boss_list = []
    decors = []

    pool = en_mod.spawn_pool(biome, wave_for_scaling)
    rng = random.Random()

    # Biom-spezifische Boden-Hazards
    biome_hazard = {
        'swamp':  'sumpf_pool',
        'lava':   'lava_pool',
        'frost':  'ice_patch',
        'crypt':  'bone_pile',
        'desert': 'quicksand',
    }.get(biome)
    if biome_hazard:
        # Update #41: deutlich weniger Hazards — vorher 55%×(2-5) konnte
        # bis zu 5 Tiles pro Raum geben (zu viel für Lava-Räume). Jetzt
        # 35%×(1-3) und für Lava noch weniger (User-Feedback: „Lava
        # killt mich einfach").
        # Update #43: Lava-Hazards weiter reduziert (User „stirbt in Lava")
        spawn_chance = 0.12 if biome == 'lava' else 0.35
        max_count = 1 if biome == 'lava' else 3
        for room in grid.rooms:
            if room.kind in ('spawn', 'boss', 'secret'):
                continue
            if random.random() < spawn_chance:
                hcount = random.randint(1, max_count)
                for _ in range(hcount):
                    hx = random.randint(room.x + 1, room.x + room.w - 2)
                    hy = random.randint(room.y + 1, room.y + room.h - 2)
                    from . import dungeon_gen as _dg
                    if grid.tiles[hy][hx] == _dg.FLOOR:
                        grid.traps.append((hx, hy, biome_hazard))

    # Boss-Position aus Boss-Raum (Lore-konform — kein zufälliger Spawn)
    boss_room = next((r for r in grid.rooms if r.kind == 'boss'), grid.rooms[-1])
    bx, by = grid.cell_to_world_center(*boss_room.center())
    boss_pos = Vector2(bx, by)
    # Boss-Room-Rect in Welt-Koordinaten (für Trigger-Volume).
    bxw, byw = grid.cell_to_world_corner(boss_room.x, boss_room.y)
    grid.boss_room_rect = (bxw, byw,
                            boss_room.w * grid.cell,
                            boss_room.h * grid.cell)
    grid.boss_room_obj = boss_room

    # Welcome-Tafel im Spawn-Raum (Velgrad-Lore zum Region-Einstieg)
    spawn_room = next((r for r in grid.rooms if r.kind == 'spawn'),
                      grid.rooms[0])
    swx, swy = grid.cell_to_world_center(spawn_room.cx, spawn_room.cy + 1)
    welcome_text = {
        'crypt':  "Marrowport. Drei Wochen vergessen. Folge dem Weg, "
                  "bevor die Wache aufwacht.",
        'frost':  "Velharn — die Liga ruht. Die Senatoren reden noch. "
                  "Tritt vorsichtig.",
        'lava':   "Die Aschenfelder. Valsa brennt unter deinen Schritten. "
                  "Atme flach.",
        'swamp':  "Das Wurzelgrab. Shulavhs Faden hält dich — oder zieht "
                  "dich hinein.",
        'astral': "Die Stunden-Spiegel. Was du tust, hast du schon getan. "
                  "Oder noch nicht.",
        'desert': "Zhar-Eth ist gewandert. Du folgst der Spur. Sie ist "
                  "trocken.",
    }.get(biome, "Velgrad behält dich nicht. Geh weiter.")
    welcome = Decor(swx, swy, 'lore_tablet', 0, 50, 0.2)
    welcome.lore_text = welcome_text
    welcome.lore_read = False
    decors.append(welcome)

    # ============================================================
    # BIOME-DECOR-SIGNATUR — Lore-Anker pro Region
    # ============================================================
    # Lore-Bibel Teil 4.1 + Bestiarium pro Akt:
    #   crypt  → Akt 1 Salzküste, Marrowport-Salzgekreuzte: Gräber+Salzkristalle
    #   frost  → Akt 2 Glasgoldene Ruinen: Echo-Markt-Reste, Stelen
    #   lava   → Akt 3 Aschenfelder, Säulen-von-Helst: Säulen-Trümmer
    #   swamp  → Akt 4 Wurzelgrab: Pilze + Stelen (Knochenwitwen)
    #   astral → Akt 5 Spiegelhof: Kristalle + Stelen
    #   desert → Zhar-Eth-Karawane: Speerschwester-Pfähle (Pillars schräg)
    # Signature = Liste of (kind, scale_radius, count_per_room) Tupel
    biome_signature = {
        'crypt':  [('gravestone', 28, 2), ('salt_crystal', 22, 1)],
        'frost':  [('mahnmal_stele', 24, 1), ('rock', 26, 2)],
        'lava':   [('broken_wall', 30, 1), ('rock', 24, 2)],
        'swamp':  [('mushroom', 22, 2), ('mahnmal_stele', 24, 1)],
        'astral': [('crystal', 26, 1), ('rune', 18, 2)],
        'desert': [('pillar', 22, 1), ('rock', 24, 2)],
    }.get(biome, [('rock', 24, 2)])

    # Decor je Raum-Typ
    for room in grid.rooms:
        cx, cy = room.center()
        wx, wy = grid.cell_to_world_center(cx, cy)

        # Update #27: Event-Decor wird UNABHÄNGIG vom room.kind platziert.
        # Vorher landeten Altare/Runen-Kreise nur in `normal`-Rooms.
        if getattr(room, 'event', None):
            decors.extend(_events.make_event_decor(room, grid, biome, rng))

        # Interior-Cover-Pillars in größeren Räumen (≥8×8 floor cells).
        # Combat-Need: ohne Cover sind Rooms reine Magnet-Arenen. 2-4
        # Pillars an Innen-Ecken brechen das auf. Lore: zerfallene
        # Säulenhalle bzw. Trümmer.
        if room.kind in ('normal', 'arena', 'library', 'fountain',
                          'treasure'):
            if room.w >= 8 and room.h >= 8:
                # 4 Innen-Ecken-Pillars mit 2-Zellen-Abstand zur Wand
                offsets = [(2, 2), (room.w - 3, 2),
                            (2, room.h - 3), (room.w - 3, room.h - 3)]
                for ox, oy in offsets:
                    ix = room.x + ox
                    iy = room.y + oy
                    if (grid.in_bounds(ix, iy) and
                            grid.tiles[iy][ix] == dungeon_gen.FLOOR):
                        pwx, pwy = grid.cell_to_world_center(ix, iy)
                        decors.append(Decor(pwx, pwy, 'pillar',
                                             rng.uniform(0, math.tau),
                                             40, 0.15, collide_radius=14))
            elif room.w >= 6 and room.h >= 6 and room.kind == 'normal':
                # 2 diagonal-gegenüber-Pillars in mittleren Räumen
                if rng.random() < 0.45:
                    for ox, oy in [(2, 2), (room.w - 3, room.h - 3)]:
                        ix = room.x + ox
                        iy = room.y + oy
                        if (grid.in_bounds(ix, iy) and
                                grid.tiles[iy][ix] == dungeon_gen.FLOOR):
                            pwx, pwy = grid.cell_to_world_center(ix, iy)
                            decors.append(Decor(pwx, pwy, 'pillar',
                                                 rng.uniform(0, math.tau),
                                                 40, 0.15,
                                                 collide_radius=14))

        if room.kind == 'fountain':
            decors.append(Decor(wx, wy, 'fountain', 0, 50, 0.2))
        elif room.kind == 'treasure':
            decors.append(Decor(wx, wy, 'chest_decor', 0, 50, 0.2))
            # 2 Mahnmal-Stelen flankieren Truhen (Lore: Mahnmal-Gilde-
            # Bergungsgut, jede gefundene Truhe gilt als Mahnung).
            decors.append(Decor(wx - 50, wy, 'mahnmal_stele', 0, 40, 0.18,
                                collide_radius=10))
            decors.append(Decor(wx + 50, wy, 'mahnmal_stele', 0, 40, 0.18,
                                collide_radius=10))
        elif room.kind == 'arena':
            # Ring aus Säulen + Fackeln auf 4 Achsen für Drama
            for k in range(6):
                a = (k / 6) * math.tau
                decors.append(Decor(wx + math.cos(a) * 70,
                                    wy + math.sin(a) * 70,
                                    'pillar', rng.uniform(0, math.tau),
                                    50, 0.15))
            for k in range(4):
                a = (k / 4) * math.tau + math.pi / 4
                decors.append(Decor(wx + math.cos(a) * 50,
                                    wy + math.sin(a) * 50,
                                    'torch'))
        elif room.kind == 'library':
            # Bücherregale + Lore-Tafel (Bibliothek der Vergessenen)
            decors.append(Decor(wx - 50, wy - 30, 'bookshelf'))
            decors.append(Decor(wx + 50, wy - 30, 'bookshelf'))
            decors.append(Decor(wx - 50, wy + 30, 'bookshelf'))
            decors.append(Decor(wx + 50, wy + 30, 'bookshelf'))
            decors.append(Decor(wx, wy, 'rune'))
        elif room.kind == 'boss':
            # Boss-Arena: Säulenring + Fackelring + Runenkreis +
            # biome-spezifischer Focal-Anchor in der Mitte.
            for k in range(8):
                a = (k / 8) * math.tau
                decors.append(Decor(bx + math.cos(a) * 160,
                                    by + math.sin(a) * 160,
                                    'pillar', rng.uniform(0, math.tau),
                                    60, 0.15, collide_radius=14))
            for k in range(4):
                a = (k / 4) * math.tau + math.pi / 4
                decors.append(Decor(bx + math.cos(a) * 130,
                                    by + math.sin(a) * 130,
                                    'torch'))
            for k in range(12):
                a = (k / 12) * math.tau
                decors.append(Decor(bx + math.cos(a) * 100,
                                    by + math.sin(a) * 100, 'rune'))
            # Focal-Anchor: das Ding, auf das Spieler von weitem zusteuert.
            # Lore-spezifisch pro Biome (Bestiarium-Boss-Theme).
            if biome == 'crypt':
                # Salzhüter-Statue: korrupterte Aspekt-Statue, signalisiert
                # den Boss-Standort von weit weg.
                decors.append(Decor(bx, by - 40, 'salt_statue', 0, 60, 0.2))
                decors.append(Decor(bx - 40, by + 60, 'salt_crystal'))
                decors.append(Decor(bx + 40, by + 60, 'salt_crystal'))
            elif biome == 'frost':
                # Echo-Markt-Throne: zerbrochenes Senator-Sitzpodest
                decors.append(Decor(bx, by - 40, 'statue', 0, 60, 0.2,
                                     collide_radius=18))
                decors.append(Decor(bx - 50, by, 'frozen_pillar'))
                decors.append(Decor(bx + 50, by, 'frozen_pillar'))
            elif biome == 'lava':
                # Säulen-von-Helst: geschmolzener Säulenstumpf in Mitte
                decors.append(Decor(bx, by - 40, 'lava_pool', 0, 80, 0.3))
                decors.append(Decor(bx, by + 30, 'broken_wall'))
            elif biome == 'swamp':
                # Wurzel-Thron: Pilz-Cluster + Stele (Vossharil-Anker)
                decors.append(Decor(bx, by - 40, 'mahnmal_stele', 0, 60, 0.2,
                                     collide_radius=12))
                for k in range(4):
                    a = (k / 4) * math.tau + math.pi / 4
                    decors.append(Decor(bx + math.cos(a) * 50,
                                        by + math.sin(a) * 50, 'mushroom'))
            elif biome == 'astral':
                # Spiegelhof: Krystall-Anker (Time-Spiegel-Stand-in)
                decors.append(Decor(bx, by - 40, 'crystal'))
                for k in range(4):
                    a = (k / 4) * math.tau
                    decors.append(Decor(bx + math.cos(a) * 60,
                                        by + math.sin(a) * 60, 'rune'))
            elif biome == 'desert':
                # Zhar-Eth: schräger Speer (Pillar) als Mahnmal
                decors.append(Decor(bx, by - 40, 'pillar',
                                     math.pi * 0.1, 70, 0.2,
                                     collide_radius=16))
                decors.append(Decor(bx, by + 30, 'mahnmal_stele', 0, 60, 0.2,
                                     collide_radius=12))
            else:
                decors.append(Decor(bx, by - 40, 'statue', 0, 60, 0.2,
                                     collide_radius=18))
            # Boss-Lore-Tafel am Eingang des Boss-Rooms (bleibt)
            entry_x, entry_y = grid.cell_to_world_center(room.cx, room.y)
            tablet = Decor(entry_x, entry_y + 30, 'lore_tablet', 0, 50, 0.2)
            boss_text = {
                'crypt':  ("„Sie war einst Wache an Velharns Hafentor. "
                           "Sie wartet seit 800 Jahren auf Ablösung."),
                'frost':  ("„412 Senatoren stritten hier. Einer streitet "
                           "immer noch."),
                'lava':   ("„Vehren kommt nicht selbst. Er schickt sein "
                           "Echo, weil sein Echo schon brennt."),
                'swamp':  ("„Vossharil ist dreimal gestorben. Diesen Saal "
                           "verlässt du nur einmal."),
                'astral': ("„Drei Zeiten, ein Saal. Tritt vorsichtig — "
                           "deine Schritte sind schon Geschichte."),
                'desert': ("„Zhar-Eth ist gewandert. Was hier blieb, "
                           "war nie zum Mitnehmen gedacht."),
            }.get(biome,
                   "Diesen Saal hat seit dem Götterkrieg niemand verlassen.")
            tablet.lore_text = boss_text
            tablet.lore_read = False
            decors.append(tablet)
            # E-05 (Update #60): Arena-Features pro Biome.  Werden später
            # in game.update getickt + gerendert.  Wir hängen die Features
            # an die Grid-Instanz; enter_dungeon liest sie und kopiert sie
            # nach `game.arena_features`.
            if not hasattr(grid, 'arena_features'):
                grid.arena_features = []
            if biome == 'lava':
                # 3 Lava-Streams in Dreieck um den Boss
                for k in range(3):
                    a = (k / 3) * math.tau + math.pi / 6
                    sx = bx + math.cos(a) * 140
                    sy = by + math.sin(a) * 140
                    grid.arena_features.append({
                        'kind': 'lava_stream',
                        'x': sx, 'y': sy,
                        'radius': 55,
                        'pulse_cd': 5.0 + k * 0.7,  # versetzt damit nicht synchron
                        'phase': 'idle',  # idle | warn | active
                        'phase_t': 0.0,
                    })
            elif biome == 'crypt':
                # 4 zerstörbare Salzgekreuzte-Gräber in Quadrat um Boss
                for k in range(4):
                    a = (k / 4) * math.tau + math.pi / 4
                    sx = bx + math.cos(a) * 150
                    sy = by + math.sin(a) * 150
                    grid.arena_features.append({
                        'kind': 'crypt_grave',
                        'x': sx, 'y': sy,
                        'radius': 22,
                        'hp': 40,
                        'hp_max': 40,
                        'spawn_cd': 12.0 + k * 1.5,
                        'destroyed': False,
                    })
            elif biome == 'frost':
                # E-11 (Update #63): 4 Ice-Pillars in Diagonal-Kreuz —
                # Spieler kann zerstören (60 HP) → Frost-Nova (10 cold-bolts
                # radial).  Briefing-Anker: zerbrochenes Senator-Sitzpodest.
                for k in range(4):
                    a = (k / 4) * math.tau + math.pi / 4
                    sx = bx + math.cos(a) * 130
                    sy = by + math.sin(a) * 130
                    grid.arena_features.append({
                        'kind': 'ice_pillar',
                        'x': sx, 'y': sy,
                        'radius': 18,
                        'hp': 60,
                        'hp_max': 60,
                        'destroyed': False,
                    })
            elif biome == 'swamp':
                # E-11 (Update #63): 3 Poison-Spore-Vents.  Periodisch
                # (alle 7 s) erupten sie kurz und applizieren Poison-Stacks
                # auf den Player wenn nah (60 px).  Vossharil-Lineage.
                for k in range(3):
                    a = (k / 3) * math.tau + math.pi / 4
                    sx = bx + math.cos(a) * 150
                    sy = by + math.sin(a) * 150
                    grid.arena_features.append({
                        'kind': 'spore_vent',
                        'x': sx, 'y': sy,
                        'radius': 60,
                        'erupt_cd': 7.0 + k * 0.8,
                        'erupting': False,
                        'erupt_t': 0.0,
                    })
            elif biome == 'astral':
                # E-11 (Update #63): 2 Mirror-Echo-Pads — spawnen alle 15 s
                # einen Wraith (Player-Echo aus dem Spiegelhof).
                for k in range(2):
                    a = (k / 2) * math.tau + math.pi / 4
                    sx = bx + math.cos(a) * 140
                    sy = by + math.sin(a) * 140
                    grid.arena_features.append({
                        'kind': 'mirror_echo',
                        'x': sx, 'y': sy,
                        'radius': 30,
                        'spawn_cd': 15.0 + k * 2.0,
                        'destroyed': False,
                        'hp': 50,
                        'hp_max': 50,
                    })
        elif room.kind == 'secret':
            decors.append(Decor(wx, wy, 'chest_decor', 0, 50, 0.2))
            decors.append(Decor(wx - 30, wy, 'rune'))
            decors.append(Decor(wx + 30, wy, 'rune'))
        elif room.kind == 'normal':
            # Biome-Signatur: 1-3 themed objects an Raumrändern, keine
            # Block-Pillars (die kommen oben aus der ≥8×8-Logik).
            sig_count = rng.randint(2, 4)
            for _ in range(sig_count):
                kind, _, _ = rng.choice(biome_signature)
                # Versuche eine FLOOR-Zelle am Rand (1-2 von der Wand)
                attempts = 0
                while attempts < 6:
                    attempts += 1
                    edge = rng.choice(['n', 's', 'e', 'w'])
                    if edge == 'n':
                        sx_c = rng.randint(room.x + 1, room.x + room.w - 2)
                        sy_c = room.y + 1
                    elif edge == 's':
                        sx_c = rng.randint(room.x + 1, room.x + room.w - 2)
                        sy_c = room.y + room.h - 2
                    elif edge == 'e':
                        sx_c = room.x + room.w - 2
                        sy_c = rng.randint(room.y + 1, room.y + room.h - 2)
                    else:
                        sx_c = room.x + 1
                        sy_c = rng.randint(room.y + 1, room.y + room.h - 2)
                    if grid.tiles[sy_c][sx_c] != dungeon_gen.FLOOR:
                        continue
                    swx, swy = grid.cell_to_world_center(sx_c, sy_c)
                    # Nicht zu nah an anderem Decor (40 px-Buffer)
                    too_close = any(
                        abs(d.x - swx) < 40 and abs(d.y - swy) < 40
                        for d in decors)
                    if too_close:
                        continue
                    # collide_radius nur bei massiven Objekten setzen
                    cr = 12 if kind in ('mahnmal_stele', 'pillar',
                                          'broken_wall',
                                          'gravestone', 'rock') else 0
                    decors.append(Decor(swx, swy, kind,
                                         rng.uniform(0, math.tau),
                                         28 + rng.randint(-4, 8), 0.16,
                                         collide_radius=cr))
                    break

    # Mini-Bosse: 1-2 in 'arena' oder zufälligen normalen Räumen
    mini_template = MINI_BOSSES.get(biome, MINI_BOSSES['crypt'])
    arenas = [r for r in grid.rooms if r.kind == 'arena']
    candidates = arenas if arenas else [r for r in grid.rooms
                                         if r.kind not in ('spawn', 'boss', 'secret')]
    rng.shuffle(candidates)
    for room in candidates[:2]:
        cx, cy = room.center()
        wx, wy = grid.cell_to_world_center(cx, cy)
        if not grid.is_walkable_world(wx, wy):
            wk = grid.find_walkable_near(wx, wy)
            if wk: wx, wy = wk
        mb = en_mod.spawn_enemy(mini_template['type'], wx, wy,
                                wave_for_scaling, elite_chance=1.0)
        mb.hp_max *= mini_template['hp_mult']
        mb.hp = mb.hp_max
        mb.dmg *= mini_template['dmg_mult']
        mb.radius = int(mb.radius * 1.4)
        mb.height = int(mb.radius * 2.2)
        mb.xp = int(mb.xp * 3)
        mb.gold_range = (mb.gold_range[0] * 3, mb.gold_range[1] * 4)
        mb.is_mini_boss = True
        mb.boss_name = mini_template['name']
        enemies_list.append(mb)
        mini_boss_list.append(mb)

    # Normale Gegner in non-spawn-/non-boss-/non-secret-Räumen verteilen
    target = enemy_count - len(mini_boss_list)
    spawn_rooms = [r for r in grid.rooms
                   if r.kind not in ('spawn', 'boss', 'secret', 'treasure')]
    if not spawn_rooms:
        spawn_rooms = grid.rooms[1:]  # Fallback
    placed = 0
    for room in spawn_rooms:
        if placed >= target:
            break
        # Anzahl pro Raum proportional zu Größe.
        # Update #96: User-Wunsch „Gegner zu leicht" → dichtere Packs.
        # Capacity / 10 statt / 14, Mindest-Range 3-5 statt 2-X.
        room_capacity = max(3, (room.w * room.h) // 10)
        n = min(target - placed, rng.randint(3, room_capacity))
        for _ in range(n):
            cx = rng.randint(room.x + 1, room.x + room.w - 2)
            cy = rng.randint(room.y + 1, room.y + room.h - 2)
            wx, wy = grid.cell_to_world_center(cx, cy)
            # KEIN random offset — bleibt mittig in der Zelle (verhindert Wand-Spawn)
            elite_chance = 0.05 + min(0.20, player_level * 0.01)
            # Begehbarkeit nochmal prüfen
            if not grid.is_walkable_world(wx, wy):
                walkable = grid.find_walkable_near(wx, wy)
                if walkable:
                    wx, wy = walkable
            enemies_list.append(en_mod.spawn_enemy(
                rng.choice(pool), wx, wy, wave_for_scaling,
                elite_chance=elite_chance))
            placed += 1

    # Lore-Tafeln aus quest_data (Velgrad-Kanon, biome-spezifisch)
    from . import quest_data as _qd
    placed_lore = 0
    rooms_for_lore = [r for r in grid.rooms if r.kind not in ('spawn', 'boss')]
    rng.shuffle(rooms_for_lore)
    for room in rooms_for_lore[:4]:
        wx, wy = grid.cell_to_world_center(room.cx, room.cy + 1)
        text = _qd.lore_tablet_for_region(
            biome, placed_lore + hash(dungeon_id) % 100)
        d = Decor(wx, wy, 'lore_tablet', 0, 50, 0.2)
        d.lore_text = text
        d.lore_read = False
        decors.append(d)
        placed_lore += 1

    return grid, enemies_list, boss_pos, spec, decors, mini_boss_list


def spawn_dungeon_boss(dungeon_id, x, y, player_level):
    spec = DUNGEONS[dungeon_id]
    boss_key = spec['boss']
    wave_for_scaling = max(5, player_level + 2)
    return en_mod.spawn_boss(boss_key, x, y, wave_for_scaling)
