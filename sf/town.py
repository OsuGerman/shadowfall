"""Brassweir-Stadt (Hub Akt 1) — lore-konforme Zonen mit Sinn.

Lore-Bibel 4.1 / 10.1: Brassweir = halb-versunkene Hafenstadt der
Mahnmal-Gilde, letzter Vorposten an der Salzküste. Drei Dörfer im
Hinterland sind verschwunden — die Stadt selbst ist umgeben von
Salzwasser-Pfützen, das Meer rückt jedes Jahr näher. Audio-Bible 7.7
beschreibt das als „Möwen, Ruderboot-Knarzen, Salz-Pfützen, leise
Volk-Stimmen".

Layout — Top-Down (Norden = oben):

                        [NORD-TEMPEL-PLATZ]
                        Bibliothek + Stelen
                              |
                        [Mara die Mahnerin]
                              |
                              |     (Mauer-Lücke)
       [GEMCUTTER-WERKSTATT]══O══[MARKT-REIHE]
       [Otreth] · Anvil      BRUNNEN     [Korven Vor] · Mahnmal-Halle
       [Mahnmal-Verwahrer]                [Stadt-Sprecher Eldon]
              |                                    |
              |          (SPAWN)                   |
              |             |                      |
              |             |                      |
       [WIRTSHAUS]══════════O══════════════[HAFEN-PIER]
       [Tameris] · Fässer        Statue   Salzpfützen, zerbrochene
                                          Pfosten, Fischer-Netze
                                  |
                          [STADT-TOR]
                          Mauer-Lücke + Banner-Pforten
                                  |
                     [Dungeon-Portale]
                     (südliche Salzküste)

Die Mauer-Segmente bilden einen unvollständigen Ring um den Markt-
Platz — der Süden ist offen zum Hafen und zur Pforte hin (sonst
wären die Portale nicht erreichbar). Lore-Anker: die Stadt hat sich
nie ganz fertig befestigt, und das Salz hat schon Teile zerstört.
"""

import math

from .entities import Decor, NPC, DungeonPortal


def _wall_segment(x, y, length, vertical=False, segs=None):
    """Mehrere Wall-Stein-Blöcke entlang einer Linie. Segs = #Steine.
    Vertical=True -> Y-Achse, sonst X-Achse. Length ist Gesamtlänge.
    """
    if segs is None:
        segs = max(2, length // 30)
    out = []
    step = length / segs
    for i in range(segs):
        if vertical:
            sy = y - length / 2 + step * (i + 0.5)
            out.append(Decor(x, sy, 'town_wall',
                              rot=math.pi / 2,  # vertical
                              size=step + 4,
                              collide_radius=10))
        else:
            sx = x - length / 2 + step * (i + 0.5)
            out.append(Decor(sx, y, 'town_wall',
                              rot=0.0,
                              size=step + 4,
                              collide_radius=10))
    return out


def _apply_wall_damage(tiles, akt_count):
    """W-10 (Update #52): Dynamische Mauer-Brüche.

    Akt 0       — Mauer unbeschädigt (Default)
    Akt 1       — 1 Wall-Segment fällt, 1 broken_wall an seine Pos
    Akt 2       — 2 Wall-Segments fallen, je 1 broken_wall
    Akt 3+      — 30 % aller Wall-Segments fallen + Schutt-Decor
    Lore: Bibel 4.1 — „Brassweir bröckelt mit jedem gefallenen Boss."
    Salz-Lineage frisst die Mauern.
    """
    if akt_count <= 0:
        return tiles
    import random as _r
    rng = _r.Random(42)  # deterministisch pro Save
    walls = [i for i, t in enumerate(tiles) if t.kind == 'town_wall']
    if not walls:
        return tiles
    if akt_count == 1:
        n_collapse = 1
    elif akt_count == 2:
        n_collapse = 2
    elif akt_count == 3:
        n_collapse = max(3, int(len(walls) * 0.20))
    else:
        n_collapse = int(len(walls) * 0.30)
    n_collapse = min(n_collapse, len(walls))
    collapsed_idx = set(rng.sample(walls, n_collapse))
    new_tiles = []
    for i, t in enumerate(tiles):
        if i in collapsed_idx:
            # Wall-Segment durch broken_wall ersetzen (sichtbar liegt, kein
            # Collision-Block mehr)
            new_tiles.append(Decor(t.x, t.y, 'broken_wall',
                                    rot=rng.uniform(0, 6.28),
                                    size=getattr(t, 'size', 30) + 4,
                                    collide_radius=0))
            # 50 % Chance auf 1-2 zusätzliche Schutt-Stones daneben
            if rng.random() < 0.5:
                for _k in range(rng.randint(1, 2)):
                    dx = rng.uniform(-12, 12)
                    dy = rng.uniform(-12, 12)
                    new_tiles.append(Decor(t.x + dx, t.y + dy, 'stone',
                                            rng.uniform(0, 6.28)))
        else:
            new_tiles.append(t)
    return new_tiles


def generate_town(akt_count=0):
    """Returnt (tiles, npcs, dungeon_portals).

    Brassweir-Hub: 6 Zonen + Mauerring + Hafenkante. Pfade verbinden
    SPAWN→alle NPCs ohne Wand-Hindernisse.

    Update #121: Survival-Portal entfernt (kein Endlos-Modus mehr).
    """
    tiles = []

    # ========================================================
    # PFADE (Kreuz + diagonal zum Hafen + Stadt-Tor)
    # ========================================================
    # Nord-Süd Achse (durchgehend, Spawn-Mitte)
    for y in range(-300, 480, 36):
        tiles.append(Decor(0, y, 'path_tile'))
    # Ost-West Achse durch Spawn
    for x in range(-400, 420, 36):
        tiles.append(Decor(x, 0, 'path_tile'))
    # West-Diagonale zum Hafen (SW)
    for d in range(60, 380, 36):
        tiles.append(Decor(int(-d * 0.85), int(d * 0.55), 'path_tile'))
    # Ost-Diagonale zum Hafen (SE)
    for d in range(60, 380, 36):
        tiles.append(Decor(int(d * 0.85), int(d * 0.55), 'path_tile'))

    # ========================================================
    # MAUERRING — unvollständig, lore-konform (Salz hat Teile zerstört)
    # ========================================================
    # Nord-Mauer (durchgehend, mit Lücke zur Mara-Zone)
    tiles += _wall_segment(-280, -300, 200, vertical=False, segs=6)
    tiles += _wall_segment( 280, -300, 200, vertical=False, segs=6)
    # West-Mauer (mit Lücke für Otreth-Eingang bei y=80)
    tiles += _wall_segment(-460, -180, 180, vertical=True, segs=5)
    tiles += _wall_segment(-460,  200, 180, vertical=True, segs=5)
    # Ost-Mauer (mit Lücke für Markt-Reihe bei y=0)
    tiles += _wall_segment( 460, -180, 180, vertical=True, segs=5)
    tiles += _wall_segment( 460,  200, 180, vertical=True, segs=5)
    # NW-Eck-Verbindung
    tiles += _wall_segment(-460, -290, 30, vertical=True, segs=1)
    tiles += _wall_segment(-435, -300, 30, vertical=False, segs=1)
    # NE-Eck
    tiles += _wall_segment( 460, -290, 30, vertical=True, segs=1)
    tiles += _wall_segment( 435, -300, 30, vertical=False, segs=1)
    # Süd-Mauer: nur 2 Stümpfe, weil zum Hafen offen — narratives Loch
    tiles += _wall_segment(-400, 310, 80, vertical=False, segs=2)
    tiles += _wall_segment( 400, 310, 80, vertical=False, segs=2)

    # ========================================================
    # MITTE: Brunnen + Statue (Spawn-Anker)
    # Update #130: Spawn-Aufräumung — die Statue lag bei (0, 220)
    # auf der Süd-Sichtachse und verdeckte den Pfad zum Akt-1-Portal.
    # Statue jetzt nach Westen versetzt (-200, 220), Brunnen bleibt
    # nördlich des Spawns als Orientierungs-Anker.  So hat der
    # Spieler vom Spawn aus eine freie Sicht nach Süden zur Krypta.
    # ========================================================
    # Brunnen (Norden vom Spawn, Marktplatz-Zentrum)
    tiles.append(Decor(0, -160, 'well', 0, 60, 0.15, collide_radius=22))
    # 4 Laternen rund um Brunnen
    for sx, sy in [(-60, -200), (60, -200), (-60, -120), (60, -120)]:
        tiles.append(Decor(sx, sy, 'lantern'))
    # Statue jetzt WEST vom Spawn (war zentral → Sichtblocker)
    tiles.append(Decor(-200, 220, 'statue', 0, 50, 0.2, collide_radius=18))
    tiles.append(Decor(-240, 250, 'lantern'))
    tiles.append(Decor(-160, 250, 'lantern'))

    # ========================================================
    # NORD: TEMPEL-PLATZ — Mara die Mahnerin
    # Lore: Mara taucht überall auf, ist Echo-Anomalie.
    # Inszenierung: Bibliothek (sie liest Echos) + 2 Stelen (Mahnungen).
    # ========================================================
    tiles.append(Decor(-100, -380, 'bookshelf'))
    tiles.append(Decor( 100, -380, 'bookshelf'))
    # 2 Mahnmal-Stelen flankieren Mara
    tiles.append(Decor(-50, -440, 'mahnmal_stele', 0, 50, 0.2,
                       collide_radius=12))
    tiles.append(Decor( 50, -440, 'mahnmal_stele', 0, 50, 0.2,
                       collide_radius=12))
    # Pillar-Pendant für Säulenhalle-Look
    tiles.append(Decor(-110, -440, 'pillar', 0, 50, 0.2, collide_radius=14))
    tiles.append(Decor( 110, -440, 'pillar', 0, 50, 0.2, collide_radius=14))
    # Runen am Boden (Mara liest dort)
    tiles.append(Decor(-30, -380, 'rune'))
    tiles.append(Decor( 30, -380, 'rune'))

    # ========================================================
    # OST: MARKT-REIHE + MAHNMAL-HALLE — Korven Vor + Eldon
    # Mahnmal-Halle = Säulen-Anker + Banner; hier nimmt Korven Aufträge an.
    # ========================================================
    # 3 Marktstände entlang der Markt-Reihe (Korven steht in der Mitte)
    tiles.append(Decor(380, -80, 'market_stall', collide_radius=16))
    tiles.append(Decor(380,  60, 'market_stall', collide_radius=16))
    tiles.append(Decor(440,  -10, 'market_stall', collide_radius=16))
    # Fässer + Kisten für Markt-Atmo
    tiles.append(Decor(330, -120, 'crate'))
    tiles.append(Decor(330, 100, 'crate'))
    tiles.append(Decor(440, 60, 'barrel'))
    # Mahnmal-Halle: 4 Pillars als Säulenhof um Korven (360, 0)
    for dx, dy in ((-40, -40), (40, -40), (-40, 40), (40, 40)):
        tiles.append(Decor(360 + dx, dy, 'pillar', 0, 50, 0.18,
                           collide_radius=14))
    # 2 Banner (Mahnmal-Gilde-Wappen)
    tiles.append(Decor(310, -10, 'banner'))
    tiles.append(Decor(410, -10, 'banner'))
    # Mahnmal-Stele neben Korven (er hängt ungelöste Aufträge dran)
    tiles.append(Decor(310, 0, 'mahnmal_stele', 0, 50, 0.2,
                       collide_radius=10))

    # Quest-Board-Zone (SE — Stadt-Sprecher Eldon)
    tiles.append(Decor(380, 250, 'banner'))
    tiles.append(Decor(360, 280, 'lore_tablet', 0, 50, 0.2))
    tiles[-1].lore_text = ('Brassweir-Anschlag: „Drei Dörfer im Hinterland '
                           'sind verschwunden. Wer Spuren findet, melde sich '
                           'bei Korven Vor."')
    tiles[-1].lore_read = False
    tiles.append(Decor(420, 250, 'crate'))

    # ========================================================
    # WEST: GEMCUTTER-WERKSTATT — Otreth + Mahnmal-Verwahrer
    # Otreth = Edelstein-Schleifer, Werkstatt-Signature: Anvil + Kisten.
    # Mahnmal-Verwahrer (Stash) = Lagerregal-Signature.
    # ========================================================
    # Otreth-Werkstatt (südwest des Spawns) — Anvil seitlich neben Otreth
    tiles.append(Decor(-400, 140, 'anvil', 0, 40, 0.18, collide_radius=14))
    tiles.append(Decor(-410,  70, 'crate'))
    tiles.append(Decor(-310, 130, 'crate'))
    tiles.append(Decor(-310,  80, 'lantern'))
    # Mahnmal-Verwahrer (Stash, bei y=0) — Buchregal-Signature
    tiles.append(Decor(-410, -10, 'bookshelf'))
    tiles.append(Decor(-360, -50, 'crate'))
    tiles.append(Decor(-310, -10, 'lantern'))
    # Banner zur Markierung des Verwahrers
    tiles.append(Decor(-360, -50, 'banner'))

    # ========================================================
    # SÜDWEST: WIRTSHAUS — Tameris
    # Speerschwester auf Reise — sitzt im Wirtshaus, sucht ihre
    # Schwester. Signature: Fässer + Krüge + ein Speer am Pfosten.
    # ========================================================
    tiles.append(Decor(-380, 250, 'barrel'))
    tiles.append(Decor(-340, 250, 'barrel'))
    tiles.append(Decor(-360, 280, 'crate'))
    # Pfosten mit angelehntem Pillar als „Speer-am-Pfosten"
    tiles.append(Decor(-300, 240, 'pillar', math.pi * 0.08, 40, 0.15,
                       collide_radius=10))
    tiles.append(Decor(-380, 210, 'lantern'))

    # ========================================================
    # SÜDOST: HAFEN-PIER — Lore-Brassweir-Signature
    # „Halb in Salz versunkene Hafenstadt" → Salzpfützen, zerbrochene
    # Pier-Pfosten, Fischer-Netze, salz-überzogene Statue (Vorgeschmack
    # auf Salzhüter im Dungeon).
    # ========================================================
    # Pier-Achse: 5 Pfosten vom Stadtrand (350, 350) bis (580, 480)
    pier_path = [(360, 350), (410, 380), (460, 410), (510, 440), (560, 470)]
    for px, py in pier_path:
        tiles.append(Decor(px, py, 'pier_post',
                            math.pi * 0.04, 40, 0.2, collide_radius=8))
    # Salzpfützen entlang des Piers
    for k in range(7):
        a = 0.55 + k * 0.06
        d = 380 + k * 18
        tiles.append(Decor(math.cos(a) * d, math.sin(a) * d, 'salt_puddle'))
    # Zusatzpfützen im Hinterhof
    for px, py in ((300, 410), (380, 330), (440, 470)):
        tiles.append(Decor(px, py, 'salt_puddle'))
    # 2 Fischer-Netze zum Trocknen
    tiles.append(Decor(330, 410, 'fishing_net'))
    tiles.append(Decor(430, 360, 'fishing_net'))
    # 1 Salz-Kristall (Foreshadowing — der Salzhüter im Dungeon)
    tiles.append(Decor(490, 470, 'salt_crystal'))
    tiles.append(Decor(550, 450, 'salt_crystal'))
    # Lore-Tafel am Pier-Anfang (Korven-Quote)
    pier_tablet = Decor(330, 360, 'lore_tablet', 0, 50, 0.2)
    pier_tablet.lore_text = ('„Der letzte Frachter ging vor drei Wochen los. '
                              'Er kam nie wieder. Drei Wochen, dieselbe Welle, '
                              'jede Nacht."  — Korven Vor')
    pier_tablet.lore_read = False
    tiles.append(pier_tablet)

    # ========================================================
    # SÜD: WEGMAL-TOR-DISTRICT — Stadt-Ausgang + Akt-Wegmale
    # Update #120 → #124: Layout entzerrt nach User-Report („Portale sind
    # ineinander").  Konvention jetzt klar getrennt nach Y-Bändern:
    #   y=280  Wegmal-Schild (lore_tablet)
    #   y=305  Mahnmal-Stele (zentral, Aspekt-Schrein-Anker)
    #   y=340  Banner-Querreihe + Eck-Säulen oben (Wegmal-Tor-Rahmen)
    #   y=400  Outpost-Portal-Reihe (game.enter_town → spawn dort)
    #   y=540  Eck-Säulen unten (Frame zum Krypta-Tor)
    #   y=580  Krypta-Tor-Banner („AKT I")
    #   y=640  Dungeon-Krypta-Portal (allein, eingerahmt)
    # ========================================================
    # Update #130: Banner-Wall entzerrt — von 4 → 2 Bannern (an den
    # Seiten), die mittlere Lücke bleibt frei.  Mahnmal-Stele bei
    # (0, 305) entfernt (war redundant: Schild bei y=280 + Tor bei
    # y=340 reichen).  Spieler sieht jetzt vom Spawn direkt durch
    # das Tor auf die Outpost-Portale.
    # 2 Eck-Säulen oben — flankieren das Wegmal-Tor von oben
    tiles.append(Decor(-450, 340, 'pillar', 0, 70, 0.22, collide_radius=20))
    tiles.append(Decor( 450, 340, 'pillar', 0, 70, 0.22, collide_radius=20))
    # Banner-Querreihe (2 Banner an den Seiten, Mitte frei)
    for bx in (-260, 260):
        tiles.append(Decor(bx, 340, 'banner'))
    # Laternen am Tor-Eingang
    tiles.append(Decor(-340, 340, 'lantern'))
    tiles.append(Decor( 340, 340, 'lantern'))

    # ========================================================
    # KRYPTA-TOR (eigener Rahmen für das einzelne Dungeon-Portal)
    # ========================================================
    # 2 Eck-Säulen umrahmen die Krypta — schmaler als Wegmal-Tor weil
    # nur 1 Portal in der Mitte (game.enter_town → y=640 (verschoben))
    tiles.append(Decor(-120, 580, 'pillar', 0, 70, 0.22, collide_radius=18))
    tiles.append(Decor( 120, 580, 'pillar', 0, 70, 0.22, collide_radius=18))
    # 1 Banner mittig oben („AKT I")
    tiles.append(Decor(0, 540, 'banner'))
    # Laternen
    tiles.append(Decor(-70, 540, 'lantern'))
    tiles.append(Decor( 70, 540, 'lantern'))
    # Lore-Tafel über dem Krypta-Tor („Hier endet Brassweir.")
    krypta_sign = Decor(0, 520, 'lore_tablet', 0, 50, 0.2,
                         collide_radius=8)
    krypta_sign.lore_text = ('„Hier endet Brassweir.  Vor dir die Krypta '
                              'der Vergessenen.  Akt I beginnt."')
    krypta_sign.lore_read = False
    tiles.append(krypta_sign)
    # Update #130: Salzpfützen reduziert (4 → 2) — die südlichen lagen
    # zu nahe an der Outpost-Portal-Reihe und blockierten Sichtlinien.
    for px, py in ((-380, 380), (380, 380)):
        tiles.append(Decor(px, py, 'salt_puddle'))

    # ========================================================
    # AUSSEN-RING: Häuser — Brassweir-Hafenstadt
    # Sechs Häuser, gleichmäßig verteilt um die Stadt aber außerhalb
    # des Mauerrings. Schiff-Wracks im Süd-Bogen.
    # ========================================================
    for k in range(6):
        a = (k / 6) * math.tau + math.pi / 6
        d = 660
        hx = math.cos(a) * d
        hy = math.sin(a) * d
        tiles.append(Decor(hx, hy, 'house', 0, 60, 0.15, collide_radius=36))

    # 2 zerbrochene Schiffsmasten — südliche „halb-versunkene"-Signature
    tiles.append(Decor(-560, 380, 'pier_post', math.pi * 0.12, 80, 0.2,
                       collide_radius=14))
    tiles.append(Decor( 580, 400, 'pier_post', -math.pi * 0.12, 80, 0.2,
                       collide_radius=14))

    # ========================================================
    # LATERNEN entlang der Hauptachsen (sparsam, nur Orientierung)
    # ========================================================
    for y in (-100, 100):
        tiles.append(Decor(-200, y, 'lantern'))
        tiles.append(Decor( 200, y, 'lantern'))

    # ========================================================
    # NPCS — Lore-Bibel Teil 12 + Voice-Lines-Pool
    # Brassweir = Mahnmal-Gilde-Hub. NPC-Pos passt zur Zone:
    #   Korven Vor: Mahnmal-Halle (Ost, Mahnmal-Stele)
    #   Mara die Mahnerin: Tempel-Platz (Nord, Bibliothek)
    #   Otreth Hohlauge: Gemcutter-Werkstatt (West, Anvil)
    #   Mahnmal-Verwahrer: Stash-Zone (West, Bücherregal)
    #   Tameris: Wirtshaus (SW, Fässer)
    #   Stadt-Sprecher Eldon: Quest-Board (SE, Banner)
    # ========================================================
    npcs = [
        NPC( 360,    0, 'vendor',     'Korven Vor',         (120, 90, 50)),
        NPC(-360,  -10, 'stash',      'Mahnmal-Verwahrer',  (80, 60, 120)),
        NPC(   0, -400, 'mystic',     'Mara die Mahnerin',  (140, 60, 180)),
        NPC(-360,  100, 'smith',      'Otreth Hohlauge',    (170, 70, 40)),
        NPC( 380,  250, 'quest',      'Stadtsprecher Eldon',(80, 130, 70)),
        NPC(-360,  250, 'innkeeper',  'Tameris',            (160, 140, 80)),
    ]
    # W-11 (Update #48): NPC-Schedules — Korven + Tameris wechseln zwischen
    # Tag- und Nacht-Position. Lore-Bibel 4.1: Korven sammelt am Tag
    # Aufträge im Markt, in der Nacht hält er Wache an der Mahnmal-Halle
    # (Mahnmal-Stele). Tameris ist tagsüber an den Fässern (SW), nachts
    # bedient sie die wenigen Gäste am Tresen (Wirtshaus-Mitte).
    # Andere NPCs bleiben statisch (Mara meditiert im Tempel,
    # Otreth schmiedet immer, Eldon hält Stellung am Quest-Board).
    _schedule_map = {
        'Korven Vor': dict(
            day_pos=(360, 0),       # Markt-Reihe
            night_pos=(360, -90),   # Mahnmal-Halle / Stele
        ),
        'Tameris': dict(
            day_pos=(-360, 250),    # Fässer am Wirtshaus-Eingang
            night_pos=(-320, 200),  # Tresen im Wirtshaus
        ),
    }
    for npc in npcs:
        sched = _schedule_map.get(npc.name)
        if sched is not None:
            npc.day_pos = sched['day_pos']
            npc.night_pos = sched['night_pos']
            # Spawn-Position = Tag-Position (Default)
            npc.pos.x, npc.pos.y = sched['day_pos']

    # ========================================================
    # DUNGEON-PORTAL — Akt-1-Krypta (Salzküste).
    # Update #123: nur 1 Portal; alle anderen Akte über Outposts.
    # Update #124: nach y=640 verschoben — innerhalb des Krypta-Tor-
    # Rahmens (Säulen y=580, Banner y=540, Schild y=520).  So hat
    # die Krypta ihren eigenen klaren Tor-Bereich, getrennt von der
    # Outpost-Portal-Reihe oben.
    # ========================================================
    dungeon_portals = []
    dungeon_portals.append(DungeonPortal(0, 640, 'crypt_lost'))

    # W-10 (Update #52): Akt-Fortschritt-Damage auf Mauerring anwenden.
    tiles = _apply_wall_damage(tiles, akt_count)
    return tiles, npcs, dungeon_portals


def tick_npc_schedules(game):
    """W-11 (Update #48): Per-Frame NPC-Schedule-Update.

    NPCs mit `day_pos`/`night_pos` werden sanft (lerp) zur aktuellen
    Tagesphase-Position gezogen.  Erste 60 s nach Town-Entry sind
    Snap-To-Target (kein „läuft langsam quer durch die Stadt").

    Update #150: Zusätzlich ESCORT-Follow-AI für NPCs mit
    `_escort_follow_player=True` — sanftes Folgen mit ~70 px Trail-
    Offset hinter dem Player, max 90 Px/s.
    """
    from . import weather as _w
    t = game.stats.get('time_played', 0.0) if game.stats else 0.0
    is_day = _w.is_day_phase(t)
    p = getattr(game, 'player', None)
    for npc in getattr(game, 'npcs', ()):
        # Update #150: ESCORT-Follow-AI hat Priorität über day/night.
        if getattr(npc, '_escort_follow_player', False) and p is not None:
            dest = getattr(npc, '_escort_dest', None)
            # Wenn Player nahe am Ziel ist → NPC snappt aufs Ziel
            # (escort tick triggert arrived).
            if dest is not None:
                pdx = p.pos.x - dest[0]
                pdy = p.pos.y - dest[1]
                if (pdx * pdx + pdy * pdy) <= 120.0 * 120.0:
                    npc.pos.x, npc.pos.y = dest
                    continue
            # Folgt dem Player mit Trail-Offset (diagonal hinten).
            off_x, off_y = 50.0, 50.0
            target_x = p.pos.x - off_x
            target_y = p.pos.y - off_y
            dx = target_x - npc.pos.x
            dy = target_y - npc.pos.y
            d = (dx * dx + dy * dy) ** 0.5
            max_step = 110.0 * (1.0 / 60.0)
            if d < max_step:
                npc.pos.x, npc.pos.y = target_x, target_y
            elif d > 2:
                npc.pos.x += dx / d * max_step
                npc.pos.y += dy / d * max_step
            continue
        day_p = getattr(npc, 'day_pos', None)
        night_p = getattr(npc, 'night_pos', None)
        if day_p is None or night_p is None:
            continue
        target = day_p if is_day else night_p
        # Lerp Richtung Ziel — max 60 Px/s (ruhiger Walk)
        dx = target[0] - npc.pos.x
        dy = target[1] - npc.pos.y
        d = (dx * dx + dy * dy) ** 0.5
        if d < 2:
            npc.pos.x, npc.pos.y = target
            continue
        max_step = 60.0 * (1.0 / 60.0)  # ~60 Px/s bei 60 FPS
        if d < max_step:
            npc.pos.x, npc.pos.y = target
        else:
            npc.pos.x += dx / d * max_step
            npc.pos.y += dy / d * max_step


def npc_in_range(player, npcs, radius=55):
    for n in npcs:
        if (n.pos - player.pos).length() < radius:
            return n
    return None


def dungeon_portal_in_range(player, portals, radius=45):
    for p in portals:
        if (p.pos - player.pos).length() < radius:
            return p
    return None
