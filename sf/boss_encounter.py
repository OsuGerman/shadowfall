"""Boss-Encounter-System: Spawn-Cinematics, Multi-Phase-Trigger, Lore-Lines.

Implementiert PLAN-Tasks E-01..E-13 aus dem Erweiterungs-Briefing Teil E.
Aktuelle Welle: Akt-1-Boss **Salzhüter-Brut** mit RISE_FROM_GRAVE-Spawn.

Velgrad-Lore: Boss-Identitäten und Lore-Lines werden NICHT generisch
abgeleitet — sie stammen aus [VELGRAD_BESTIARIUM.md](VELGRAD_BESTIARIUM.md)
und sind in dieser Datei direkt referenziert.

Architektur:
  - `SpawnMethod` listet 10 Cinematic-Varianten aus Briefing E.3.
  - `BOSS_ENCOUNTERS` mappt boss-key → dict mit Method/Duration/Lore.
  - `start_encounter(game, boss, encounter_key)` startet die Sequenz.
  - `tick_cinematic(game, dt)` wird pro Frame im Game-Update aufgerufen.
"""

import math
import random


# ============================================================
# SPAWN-METHODS (Briefing E.3 — 10 Varianten)
# ============================================================
class SpawnMethod:
    RISE_FROM_GRAVE       = 'rise_from_grave'
    RIDE_IN               = 'ride_in'
    PORTAL                = 'portal'
    ASSEMBLE              = 'assemble'
    FALL_FROM_SKY         = 'fall_from_sky'
    AWAKEN                = 'awaken'
    REVEAL                = 'reveal'
    DESCEND_FROM_THRONE   = 'descend_from_throne'
    EMERGE_FROM_LIQUID    = 'emerge_from_liquid'
    SHATTER_PRISON        = 'shatter_prison'


# ============================================================
# ENCOUNTER-REGISTRY
# ============================================================
# Schlüssel = `bestiary_key`-Eintrag des Boss-Mobs (siehe bestiary.py).
# Felder:
#   spawn_method        SpawnMethod.*
#   intro_duration      Cinematic-Dauer in Sekunden (Boss invuln+still)
#   intro_audio         SFX-Key (None = kein extra Sound)
#   lore_quote          Zitat aus Bestiarium/Voice-Lines
#   phase_thresholds    HP-Anteile, an denen Phase-Trigger feuern
#   music_swap          'boss' | 'town' | 'dungeon' (None = unverändert)
BOSS_ENCOUNTERS = {
    'salzhueter_brut': dict(
        spawn_method=SpawnMethod.RISE_FROM_GRAVE,
        intro_duration=3.5,
        intro_audio='roar',
        lore_quote=("Sie wartet immer noch auf Ablösung. "
                    "Niemand kommt mehr."),
        phase_thresholds=[1.0, 0.66, 0.33],
        # Boss-spezifischer Music-Track aus Sounds/Salzhüter-Brut (Akt 1).mp3
        # (siehe sounds.MUSIC_FILES). Fallback auf 'boss' procedural.
        music_swap='salzhueter_brut',
        title="Wache am Hafentor von Velharn",
        cinematic_color=(180, 175, 165),       # Salz-Patina
        ground_particle_color=(220, 220, 200), # Salzkristalle
    ),
    # Akt-3-Boss: Inquisitor-General Vehren. Tribunal-Sekte aus den
    # Aschenfeldern. Phase-Quotes wörtlich aus VELGRAD_VOICE_LINES_POOL.md
    # NPC 7.
    'vehren': dict(
        spawn_method=SpawnMethod.REVEAL,
        intro_duration=4.0,
        intro_audio='roar',
        lore_quote=("Du bist Im-Nesh-berührt. Es tut mir leid. "
                    "Es ist meine Pflicht."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap='vehren',
        title="Inquisitor-General des Tribunals der Asche",
        cinematic_color=(255, 140, 60),
        ground_particle_color=(255, 200, 100),
        # Phase-Voice-Lines (Voice-Lines-Pool NPC 7 Sektion B + C)
        phase_quotes={
            2: "Valsa. Brenne durch mich. Brenne mich klar.",
            3: "Tribunal — wenn ich falle, zähle nicht meine Sünden.",
        },
    ),
    # ============================================================
    # AKT 6 — DIE DREI WUNDEN (Update #110)
    # Bestiarium #26-28 als Boss-Encounter.  Nicht-Mann (#29) ist ein
    # Add-Spawn aus Phase 3 von Nicht-Gott (#28).
    # ============================================================
    'ertrunkene_koenigin': dict(
        spawn_method=SpawnMethod.EMERGE_FROM_LIQUID,
        intro_duration=4.5,
        intro_audio='roar',
        lore_quote=("Sie war die Letzte Königin Velharns, ertränkt im "
                    "Krieg. Sie wachte am Boden der Salzwunde wieder "
                    "auf."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap='salzhueter_brut',   # Salz-Atmosphäre, Fallback OK
        title="Königin der Salzwunde",
        cinematic_color=(90, 130, 170),
        ground_particle_color=(190, 220, 240),
        phase_quotes={
            2: "Mein Schwur galt noch — er gilt unter Wasser auch.",
            3: "Komm zu mir herunter. Es ist nicht so kalt, wie es scheint.",
        },
    ),
    'echo_drache': dict(
        spawn_method=SpawnMethod.AWAKEN,
        intro_duration=5.0,
        intro_audio='roar',
        lore_quote=("Einer der drei letzten Drachen Velgrads. Er sah "
                    "Valsa fallen und versteinerte vor Trauer."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap='vehren',            # Asche-Track recycelt
        title="Letzter Drache der Aschwunde",
        cinematic_color=(255, 100, 40),
        ground_particle_color=(255, 160, 80),
        phase_quotes={
            2: "Valsa — ich rieche dich noch in deiner Asche.",
            3: "Ich war Wache. Ich bin Klage. Ich werde Feuer.",
        },
    ),
    'nicht_gott': dict(
        spawn_method=SpawnMethod.REVEAL,
        intro_duration=4.0,
        intro_audio=None,               # Stille als Drama
        lore_quote=("Manche Theologen flüstern: Das ist der Siebte. "
                    "Andere: Es ist nur ein Echo. Niemand weiß. "
                    "Niemand fragt."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap=None,                # Music ducks/cuts statt swappt
        title="Hohlwunden-Anomalie",
        cinematic_color=(40, 35, 50),
        ground_particle_color=(80, 60, 100),
        phase_quotes={
            2: "…",
            3: "Du erinnerst dich an mich. Das ist gefährlich.",
        },
        # Phase-3-Add-Spawn: Nicht-Männer
        spawn_adds_key='nicht_mann',
        spawn_adds_count=3,
    ),

    # ============================================================
    # AKT-BOSSE aus WELT_AUFBAU.md Sektion 4 (Update #111)
    # Schließt die Boss-Coverage-Lücken für Akt 2 / Akt 4 / Akt 5.
    # ============================================================
    'senator_geist': dict(
        spawn_method=SpawnMethod.ASSEMBLE,        # Glas-Splitter formen sich
        intro_duration=4.0,
        intro_audio='roar',
        lore_quote=("Einer der 412 Senatoren. Heute hört ihm zum "
                    "ersten Mal jemand wirklich zu."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap=None,                          # Fallback procedural
        title="Senator der Glasgoldenen Liga",
        cinematic_color=(230, 200, 130),          # Goldstaub
        ground_particle_color=(255, 230, 160),
        phase_quotes={
            2: "Die Liga vergisst nicht. Sie spricht durch mich.",
            3: "Höre meine letzte Rede. Sie ist immer noch dieselbe.",
        },
        # Phase 3: 3 Goldstaub-Diener als Adds
        spawn_adds_key='goldstaub_diener',
        spawn_adds_count=3,
    ),
    'shulavh': dict(
        spawn_method=SpawnMethod.RISE_FROM_GRAVE,  # Wurzeln öffnen sich
        intro_duration=5.0,
        intro_audio='roar',
        lore_quote=("Sie hat dich gewählt. Was auch immer du tust — "
                    "sie liebt dich."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap=None,
        title="Faden-Mutter, Aspektin des Vergessens",
        cinematic_color=(110, 60, 90),            # Wurzel-Schmerzgewebe
        ground_particle_color=(220, 100, 130),    # rote Fäden
        # Lore-Bibel Teil 10.4: Mütterlich → Wahnsinnig → Vergessend
        phase_quotes={
            2: "Wer trägt dich, Kind? Wer hält deinen Faden noch?",
            3: "Ich erinnere mich nicht mehr — wie hieß dein Name?",
        },
        # Phase 3: 3 Faden-Gebundene als Adds
        spawn_adds_key='faden_gebundener',
        spawn_adds_count=3,
    ),
    'velharn_trio': dict(
        spawn_method=SpawnMethod.PORTAL,           # Stundenspiegel-Portal
        intro_duration=4.5,
        intro_audio='roar',
        lore_quote=("Drei Senatoren in einem Körper, vereint im Tod, "
                    "geteilt in der Zeit."),
        phase_thresholds=[1.0, 0.66, 0.33],
        music_swap=None,
        title="Drei-Zeiten-Senatoren",
        cinematic_color=(190, 180, 220),          # Stundenspiegel-Lavendel
        ground_particle_color=(230, 220, 255),
        # Drei verschiedene Sprecher pro Phase (Glasgolden / Götterkrieg /
        # Gegenwart) — Lore-Bibel 10.5.
        phase_quotes={
            2: "Glasgolden: Wir haben den Hafen gebaut. Wir bauten ihn richtig.",
            3: "Gegenwart: Wir sind das, was vom Senat übrig blieb. Wenig.",
        },
        # Phase 3: 3 Stunden-Wandler als Adds (Bestiarium #21)
        spawn_adds_key='stunden_wandler',
        spawn_adds_count=3,
    ),
}


# ============================================================
# CINEMATIC-TIMELINE
# ============================================================
def start_encounter(game, boss, encounter_key):
    """Initiiert eine Boss-Cinematic. Boss ist invulnerable & idle bis
    die Timeline fertig durchgelaufen ist.
    """
    cfg = BOSS_ENCOUNTERS.get(encounter_key)
    if cfg is None:
        # Fallback: bestehender Boss-Intro-Pfad
        return False

    # PLAN E-04: Skip-Cinematic ab 2. Encounter dieses Bosses.
    # `game._seen_encounters` ist ein Set, das beim ersten Spawn pro
    # encounter_key gefüllt wird; bei späteren Spawns wird der Skip-Hint
    # angezeigt (Hold-Space im Player-Input-Handler).
    if not hasattr(game, '_seen_encounters'):
        game._seen_encounters = set()
    already_seen = encounter_key in game._seen_encounters
    game._seen_encounters.add(encounter_key)

    game.boss_encounter = dict(
        boss=boss,
        cfg=cfg,
        method=cfg['spawn_method'],
        duration=cfg['intro_duration'],
        t=0.0,
        phase_thresholds=list(cfg['phase_thresholds']),
        current_phase=1,
        triggered_phases={1},
        skippable=already_seen,  # Skip-Hint nur ab 2. Begegnung
        skip_held_t=0.0,
    )

    # Boss wird für die Dauer der Cinematic unverwundbar gemacht.
    boss._encounter_invuln_left = cfg['intro_duration']
    boss._encounter_key = encounter_key

    # Phase-3-Marker (zusätzlich zur Legacy-Phase-2-Logik in enemies.py)
    boss.phase3_triggered = False

    # Boss-Intro im UI: Lower-Third + Title
    game.boss_intro = dict(
        name=boss.boss_name,
        title=cfg.get('title', boss.boss_title),
        timer=cfg['intro_duration'],
        encounter=True,
        lore_quote=cfg['lore_quote'],
    )

    # Music swap
    if cfg.get('music_swap'):
        try:
            from . import sounds as _snd
            _snd.play_music(cfg['music_swap'])
        except Exception:
            pass

    # Spawn-Method-spezifischer initialer VFX-Burst
    _spawn_method_init(game, boss, cfg)

    # Audio: Tubular-Bell-„Bong" + Velgrad-Boss-Stinger + Intro-Roar.
    try:
        from . import sounds as _snd
        # Boss-Health-Bar erscheint → großer Moment.
        _snd.play('boss_bong', volume=0.95, bus='ui')
        # Update #X — Phase-2-AI: Velgrad-spezifischer Boss-Spawn-Stinger
        # Resolver-Reihenfolge (siehe sounds._resolve_sfx_file):
        #   1) cfg.intro_audio (explicit override im Encounter-Cfg)
        #   2) <boss_key>_spawn (z.B. 'salzhueter_brut_spawn' -> Hint -> salzhueter_spawn.mp3)
        boss_key = getattr(boss, '_encounter_key', None) or getattr(boss, 'boss_key', None) or cfg.get('key')
        if boss_key:
            _snd.play(f'{boss_key}_spawn', volume=0.85)
        if cfg.get('intro_audio'):
            _snd.play(cfg['intro_audio'], volume=0.85, bus='voice')
    except Exception:
        pass

    return True


def _spawn_method_init(game, boss, cfg):
    """Initialer Effekt der Spawn-Methode (T=0)."""
    method = cfg['spawn_method']
    color = cfg.get('ground_particle_color', (200, 200, 200))
    if method == SpawnMethod.RISE_FROM_GRAVE:
        # Erd-Riss: Boden-Decal + aufsteigende Particles (Erde+Staub)
        game.shake = max(game.shake, 16)
        for _ in range(60):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(80, 240)
            game.particles_push(
                boss.pos.x, boss.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp - 120,
                color, random.uniform(0.6, 1.4),
                random.uniform(3, 6), gravity=120)
        # Salzkristalle nach oben sprühen
        for _ in range(30):
            game.particles_push(
                boss.pos.x + random.uniform(-30, 30),
                boss.pos.y + random.uniform(-10, 10),
                random.uniform(-20, 20), random.uniform(-260, -180),
                (240, 240, 220), random.uniform(0.8, 1.6),
                random.uniform(2, 5), gravity=180)
    elif method == SpawnMethod.FALL_FROM_SKY:
        # Update #97 PLAN E-03: Volleres Meteor-Cinematic.
        # Pre-Impact-Schatten-Decal + verzögerter Aufschlag, Boss erscheint
        # erst am Impact-Frame.
        game.shake = max(game.shake, 24)
        # Boden-Schatten-Vorbereitung: Telegraph-Decal vor Impact
        try:
            from .effects import Decal
            d = Decal(boss.pos.x, boss.pos.y, 80, kind='meteor',
                       windup=0.3, lifetime=0.0)
            game.decals.append(d)
        except Exception:
            pass
        # Aufschlag-Dust-Wave: 80 Partikel radial + 40 vertikal hoch
        for _ in range(80):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(160, 360)
            game.particles_push(
                boss.pos.x, boss.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                (255, 180, 80), random.uniform(0.5, 1.2),
                random.uniform(3, 7), gravity=80)
        for _ in range(40):
            game.particles_push(
                boss.pos.x + random.uniform(-30, 30),
                boss.pos.y,
                random.uniform(-40, 40),
                random.uniform(-280, -150),
                (200, 150, 70), random.uniform(0.8, 1.6),
                random.uniform(3, 6), gravity=180)
        try:
            from . import sounds as _snd
            _snd.play('boss_intro', volume=0.9)
        except Exception:
            pass
    elif method == SpawnMethod.AWAKEN:
        # Statue-Erwachen: ruhige Particles, langsam pulsierend
        for _ in range(30):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(30, 80)
            game.particles_push(
                boss.pos.x, boss.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                color, random.uniform(1.0, 2.0),
                random.uniform(2, 4))
    elif method == SpawnMethod.EMERGE_FROM_LIQUID:
        for _ in range(50):
            game.particles_push(
                boss.pos.x + random.uniform(-40, 40),
                boss.pos.y,
                random.uniform(-30, 30), random.uniform(-180, -80),
                (140, 180, 220), random.uniform(0.6, 1.2),
                random.uniform(2, 5), gravity=120)
    elif method == SpawnMethod.REVEAL:
        # NPC-Maske fällt → Transformation. Lore: Vehren war in der
        # Tribunal-Robe „nur ein Inquisitor", jetzt zeigt sich der General.
        # Visuell: Maskensplitter fliegen weg, Funken-Explosion, Glut-Ring.
        game.shake = max(game.shake, 14)
        # Maskensplitter (graue Bronze) fliegen radial weg.
        for _ in range(24):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(180, 320)
            game.particles_push(
                boss.pos.x, boss.pos.y - boss.height * 0.4,
                math.cos(ang) * sp, math.sin(ang) * sp,
                (120, 100, 80), random.uniform(0.6, 1.2),
                random.uniform(3, 5), gravity=240)
        # Funken / Glut (Inquisitor-Brand)
        for _ in range(50):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(60, 220)
            game.particles_push(
                boss.pos.x, boss.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp - 40,
                color, random.uniform(0.8, 1.6),
                random.uniform(2, 5), gravity=120)
        # Telegraph-Decal als „Glut-Ring" beim Boss
        try:
            from . import effects as _fx
            _fx.spawn_ground_decal(
                game, boss.pos.x, boss.pos.y,
                radius=boss.radius + 30,
                kind=_fx.DECAL_KIND.DOT,         # Tribunal-Glut = DoT-Orange
                windup=cfg['intro_duration'],
                lifetime=0.0,
                play_windup=False)
        except Exception:
            pass
    # Update #100 (PLAN E-03 Erweiterung): RIDE_IN / PORTAL / ASSEMBLE /
    # DESCEND_FROM_THRONE / SHATTER_PRISON Spawn-Cinematics.
    elif method == SpawnMethod.RIDE_IN:
        # Boss „reitet" herein — Dust-Stream hinter ihm, Galopp-Shake.
        game.shake = max(game.shake, 16)
        for _ in range(45):
            game.particles_push(
                boss.pos.x - 30 + random.uniform(-10, 10),
                boss.pos.y + random.uniform(0, 12),
                random.uniform(-180, -100), random.uniform(-40, 40),
                (180, 150, 100), random.uniform(0.5, 1.0),
                random.uniform(2, 4), gravity=60)
    elif method == SpawnMethod.PORTAL:
        # Portal-Schwall: lila Funken in Spirale, Implosion → Boss erscheint.
        game.shake = max(game.shake, 18)
        for k in range(60):
            ang = (k / 60.0) * math.tau * 3
            r = 80 * (1.0 - k / 60.0)
            game.particles_push(
                boss.pos.x + math.cos(ang) * r,
                boss.pos.y + math.sin(ang) * r,
                -math.cos(ang) * 120, -math.sin(ang) * 120,
                (170, 80, 220), random.uniform(0.6, 1.2),
                random.uniform(3, 5))
        try:
            from . import sounds as _snd
            # Update #X — Phase-3-AI: Boss-Special-Charge statt cast_lightning
            _snd.play('boss_special_charge', volume=0.7)
        except Exception:
            pass
    elif method == SpawnMethod.ASSEMBLE:
        # Stücke fügen sich zusammen — Splitter fliegen radial REIN.
        game.shake = max(game.shake, 12)
        for _ in range(40):
            ang = random.uniform(0, math.tau)
            r = random.uniform(60, 140)
            sx_p = boss.pos.x + math.cos(ang) * r
            sy_p = boss.pos.y + math.sin(ang) * r
            # Geschwindigkeit nach innen
            game.particles_push(
                sx_p, sy_p,
                -math.cos(ang) * 240, -math.sin(ang) * 240,
                (200, 200, 220), 0.5,
                random.uniform(3, 5))
    elif method == SpawnMethod.DESCEND_FROM_THRONE:
        # Boss schreitet langsam herab — vertikale Dust-Säulen + Gold-Glanz.
        for _ in range(35):
            game.particles_push(
                boss.pos.x + random.uniform(-25, 25),
                boss.pos.y - 40,
                random.uniform(-20, 20), random.uniform(60, 120),
                color, random.uniform(0.8, 1.4),
                random.uniform(2, 4), gravity=20)
        # Gold-Funken oben über Boss-Kopf
        for _ in range(20):
            game.particles_push(
                boss.pos.x + random.uniform(-15, 15),
                boss.pos.y - 80,
                random.uniform(-30, 30), random.uniform(-80, -20),
                (255, 220, 140), random.uniform(0.5, 1.0),
                random.uniform(2, 3))
    elif method == SpawnMethod.SHATTER_PRISON:
        # Käfig-Splitter explodieren — Eis/Glas-Scherben fliegen weg.
        game.shake = max(game.shake, 20)
        for _ in range(60):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(220, 380)
            game.particles_push(
                boss.pos.x, boss.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                (200, 230, 255), random.uniform(0.5, 1.0),
                random.uniform(3, 6), gravity=180)
        try:
            from . import sounds as _snd
            _snd.play_with_fallback('aoe_impact', 'hit_heavy', volume=0.7)
        except Exception:
            pass


def tick_encounter(game, dt):
    """Wird pro Frame gerufen. Tickt Cinematic + Phasen-Trigger."""
    enc = getattr(game, 'boss_encounter', None)
    if enc is None:
        return
    enc['t'] += dt
    boss = enc['boss']

    # Cinematic-Phase: Boss invulnerable, periodische Particles für VFX-Loop
    if enc['t'] < enc['duration']:
        if enc['method'] == SpawnMethod.RISE_FROM_GRAVE:
            if random.random() < 0.5:
                ang = random.uniform(0, math.tau)
                game.particles_push(
                    boss.pos.x + random.uniform(-30, 30),
                    boss.pos.y,
                    math.cos(ang) * 40, -random.uniform(60, 180),
                    enc['cfg'].get('ground_particle_color', (210, 210, 200)),
                    1.0, 4, gravity=120)
        boss._encounter_invuln_left = max(0.0, enc['duration'] - enc['t'])
        return

    # Cinematic vorbei → Boss kann angreifen, Encounter bleibt aktiv für Phasen.
    boss._encounter_invuln_left = 0.0

    # Phasen-Trigger: HP-Anteil prüfen
    hp_frac = boss.hp / max(1, boss.hp_max)

    # Update #96: Berserk-Modus bei <30 % HP (User-Wunsch „zu leicht").
    # Boss wird permanent aggressiver — Speed +25 %, Att-CD -25 %,
    # Particle-Glow rot-pulsierend.
    if hp_frac < 0.30 and not enc.get('berserk_applied', False):
        boss.speed *= 1.25
        boss.att_cd *= 0.75
        enc['berserk_applied'] = True
        try:
            game.push_event_notification(
                'story',
                f'{boss.boss_name.upper()}  ·  BERSERK',
                sub='„Das Echo bricht aus."',
                color=(220, 60, 40), duration=2.6)
        except Exception:
            pass
        game.shake = max(game.shake, 18)
    thresholds = enc['phase_thresholds']
    for i, t in enumerate(thresholds[1:], start=2):  # skip Phase 1 (= 100%)
        if i in enc['triggered_phases']:
            continue
        if hp_frac <= t:
            _trigger_phase(game, boss, i, enc)
            enc['triggered_phases'].add(i)
            enc['current_phase'] = i

    # Encounter-Ende bei Boss-Tod
    if boss.dying or boss.hp <= 0:
        game.boss_encounter = None


def _trigger_phase(game, boss, phase, enc):
    """Phase-N-Trigger: VFX-Pulse + Damage-Buff + Voice-Line + Adds."""
    from . import sounds as _snd
    cfg = enc['cfg']
    color = cfg.get('cinematic_color', (255, 100, 100))
    game.shake = max(game.shake, 12)
    # Update #131 (Y-02): erste Boss-Phase-Transition → Mechanik-Hint
    try:
        from . import tutorial as _tut
        _tut.mech_hint(game, 'boss_phase')
    except ImportError:
        pass
    game.spawn_particles(boss.pos.x, boss.pos.y, 60, color,
                         life_max=1.0, size_max=8, gravity=40)
    game._damage_flash = max(getattr(game, '_damage_flash', 0), 0.4)
    try:
        # Update #X — Phase-3-AI: Boss-Rage-Trigger statt generic roar
        _snd.play('boss_rage_trigger', volume=0.7)
    except Exception:
        pass
    # N-09 (Update #64): Music-Stem-Swap-Simulation via Volume-Pulse.
    # Pygame kann ohne externe Libs keine echten Stems mixen, aber wir
    # ducken die Music kurz auf 35 %, layern ein Bell-Cue darüber, und
    # lassen die Music wieder auf 100 %.  Audio-Bibel: „Phase-Transition
    # = Stem-Swap (Strings → Strings+Percussion)".
    try:
        cur = _snd.MUSIC_VOLUME
        if not hasattr(game, '_music_phase_duck'):
            game._music_phase_duck = {
                'orig': cur, 'left': 1.0, 'step': 'duck'}
        else:
            game._music_phase_duck['left'] = 1.0
            game._music_phase_duck['step'] = 'duck'
            game._music_phase_duck['orig'] = cur
        _snd.set_music_volume(cur * 0.35)
        _snd.play('boss_bong', volume=0.8)  # Phase-Transition-Bell
        # Update #X — Velgrad-spezifischer Phase-Stinger ueber dem Bell
        boss_key = getattr(boss, '_encounter_key', None) or getattr(boss, 'boss_key', None)
        if boss_key:
            _snd.play(f'{boss_key}_phase', volume=0.75)
    except Exception:
        pass
    from .entities import Floater
    name = boss.boss_name or 'Boss'
    game.floaters.append(Floater(
        boss.pos.x, boss.pos.y - 70,
        f'Phase {phase}: {name}', color))
    game.toast(f'Phase {phase}: {name}', color)

    # PLAN E-07: Boss-spezifische Phase-Voice-Line aus phase_quotes-Dict
    # (Lore-Quelle: VELGRAD_VOICE_LINES_POOL.md pro NPC).
    phase_quotes = cfg.get('phase_quotes') or {}
    quote_text = phase_quotes.get(phase)
    if quote_text:
        game.floaters.append(Floater(
            boss.pos.x, boss.pos.y - 100,
            f'„{quote_text}"', (220, 200, 170)))
        game.toast(f'{name}: „{quote_text}"', (220, 200, 170))

    # Update #30: Large Banner-Notification für Phase-Transition.
    ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}
    try:
        game.push_event_notification(
            'story',
            f'PHASE {ROMAN.get(phase, str(phase))}',
            sub=quote_text or name,
            color=color, duration=3.0)
    except Exception:
        pass

    # Speed/Damage-Buff pro Phase
    boss.speed *= 1.15
    boss.att_cd *= 0.85
    # O-21 (Update #168): Boss-Phase-Transformation-Anim.
    # 0.8 s Roar mit Scale-Pulse + Aspekt-Color-Aura-Burst + extra
    # Camera-Shake + Slow-Mo-Beat 0.35.  Visualisiert das Phase-Tick.
    boss._phase_transform_left = 0.8
    boss._phase_transform_color = color
    boss.phase_idx = phase - 1   # 0-indexed fuer Lighting U-08
    try:
        game.slow_mo_left = max(getattr(game, 'slow_mo_left', 0.0), 0.35)
        game.shake = max(getattr(game, 'shake', 0), 18)
        # Aura-Burst: 36 Particles radial, life 1.0, gravity neg.
        import math as _m
        for k in range(36):
            ang = _m.tau * k / 36
            vx = _m.cos(ang) * 280
            vy = _m.sin(ang) * 280
            game.particles_push(
                boss.pos.x, boss.pos.y,
                vx, vy,
                color, 1.0, 7, gravity=-30)
    except Exception:
        pass

    # Phase 3: Adds spawnen — Boss-Kennung bestimmt den Add-Typ.
    # Update #110: bevorzugt `spawn_adds_key`/`spawn_adds_count` aus
    # BOSS_ENCOUNTERS-Config; legacy-Hardcodes für Salzhüter/Vehren bleiben.
    if phase == 3:
        key = getattr(boss, '_encounter_key', None)
        cfg = BOSS_ENCOUNTERS.get(key, {})
        adds_key = cfg.get('spawn_adds_key')
        adds_count = cfg.get('spawn_adds_count', 0)
        if adds_key and adds_count > 0:
            from . import bestiary as _best
            for k in range(adds_count):
                ang = (k / adds_count) * math.tau
                ox = boss.pos.x + math.cos(ang) * 70
                oy = boss.pos.y + math.sin(ang) * 70
                add = _best.spawn_bestiary_mob(game, adds_key, ox, oy)
                game.enemies.append(add)
        elif key == 'salzhueter_brut':
            from . import bestiary as _best
            for k in range(2):
                ox = boss.pos.x + math.cos(k * math.pi) * 60
                oy = boss.pos.y + math.sin(k * math.pi) * 60
                add = _best.spawn_bestiary_mob(game, 'salzgekreuzter', ox, oy)
                game.enemies.append(add)
        elif key == 'vehren':
            # Vehren ist Tribunal-General → Inquisitions-Klingenmesser-Adds
            # aus dem Akt-3-Bestiarium (#13). Tribunal-Caster-Profile.
            from . import bestiary as _best
            for k in range(2):
                ox = boss.pos.x + math.cos(k * math.pi + 0.5) * 70
                oy = boss.pos.y + math.sin(k * math.pi + 0.5) * 70
                add = _best.spawn_bestiary_mob(game, 'klingenmesser', ox, oy)
                game.enemies.append(add)
        boss.phase3_triggered = True


def is_boss_invulnerable(boss):
    """True wenn Boss während Cinematic noch nicht angreifbar ist."""
    return getattr(boss, '_encounter_invuln_left', 0.0) > 0.0


def request_skip(game, dt):
    """Wird aufgerufen wenn Spieler Space im Boss-Intro hält (PLAN E-04).

    Hold 0.5 s → springt direkt zum Ende der Cinematic.
    """
    enc = getattr(game, 'boss_encounter', None)
    if enc is None or not enc.get('skippable'):
        return
    if enc['t'] >= enc['duration']:
        return
    enc['skip_held_t'] = enc.get('skip_held_t', 0.0) + dt
    if enc['skip_held_t'] >= 0.5:
        # Springe zum Ende
        enc['t'] = enc['duration']
        enc['boss']._encounter_invuln_left = 0.0
        # Boss-Intro UI ebenfalls beenden
        if getattr(game, 'boss_intro', None) is not None:
            game.boss_intro['timer'] = 0.0


def is_skippable(game):
    enc = getattr(game, 'boss_encounter', None)
    if enc is None:
        return False
    return enc.get('skippable', False) and enc['t'] < enc['duration']
