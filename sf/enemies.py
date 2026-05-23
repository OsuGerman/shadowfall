"""Gegner-Templates, AI, Elite-Affixe, Boss-Mechaniken."""

import math
import random

from pygame.math import Vector2

from .entities import Enemy, Projectile, Floater


# ============================================================
# TEMPLATES
# ============================================================
ENEMY_TYPES = {
    'zombie':   dict(name='Zombie',    color=(90, 122, 58),  glow=(154, 255, 122),
                     hp=25,  dmg=8,  speed=60,  radius=18, xp=8,  gold=(1, 4),
                     att_range=30, att_cd=1.2),
    'skeleton': dict(name='Skelett',   color=(216, 200, 168), glow=(255, 255, 204),
                     hp=18,  dmg=6,  speed=90,  radius=16, xp=10, gold=(2, 5),
                     att_range=32, att_cd=0.9),
    'wraith':   dict(name='Geist',     color=(74, 58, 106),  glow=(170, 138, 255),
                     hp=35,  dmg=10, speed=140, radius=17, xp=18, gold=(4, 10),
                     att_range=34, att_cd=1.1),
    'demon':    dict(name='Dämon',     color=(139, 26, 26),  glow=(255, 74, 74),
                     hp=50,  dmg=14, speed=110, radius=22, xp=22, gold=(5, 12),
                     att_range=38, att_cd=1.0),
    'brute':    dict(name='Berserker', color=(106, 58, 26),  glow=(255, 170, 58),
                     hp=120, dmg=22, speed=70,  radius=28, xp=50, gold=(12, 25),
                     att_range=44, att_cd=1.5),
    'archer':   dict(name='Bogner',    color=(160, 130, 80),  glow=(240, 200, 130),
                     hp=22,  dmg=12, speed=80,  radius=17, xp=15, gold=(3, 8),
                     att_range=350, att_cd=1.6, ranged=True),
    'shaman':   dict(name='Schamane',  color=(80, 160, 120),  glow=(140, 240, 180),
                     hp=30,  dmg=8,  speed=85,  radius=18, xp=20, gold=(5, 10),
                     att_range=290, att_cd=2.2, ranged=True),
    'warlock':  dict(name='Hexenmeister', color=(100, 50, 140), glow=(200, 130, 240),
                     hp=40,  dmg=10, speed=70,  radius=18, xp=28, gold=(8, 15),
                     att_range=310, att_cd=2.4, ranged=True),
    'berserker':dict(name='Berserker', color=(160, 60, 30),    glow=(255, 140, 60),
                     hp=60,  dmg=14, speed=95,  radius=21, xp=24, gold=(6, 14),
                     att_range=34, att_cd=0.7),
    'lurker':   dict(name='Schatten-Lurker', color=(20, 16, 36), glow=(150, 100, 240),
                     hp=45, dmg=18, speed=130, radius=16, xp=30, gold=(7, 14),
                     att_range=30, att_cd=1.0),
    'slime':    dict(name='Schleim', color=(80, 200, 100), glow=(180, 255, 160),
                     hp=20, dmg=6, speed=55, radius=15, xp=8, gold=(1, 4),
                     att_range=24, att_cd=1.4),
    # Update #44: 4 neue Bestiarium-Mobs mit eigenen Mechaniken
    # — User „Neue Monster und Bosse sind sehr wichtig"
    'salzgeist':   dict(name='Salzgeist',
                        color=(180, 200, 220), glow=(240, 250, 255),
                        hp=28, dmg=11, speed=130, radius=16, xp=20,
                        gold=(4, 9), att_range=32, att_cd=1.0),
    'glaslord':    dict(name='Glaslord',
                        color=(140, 180, 220), glow=(220, 240, 255),
                        hp=55, dmg=13, speed=70, radius=20, xp=32,
                        gold=(8, 16), att_range=38, att_cd=1.3),
    'aschenbrut':  dict(name='Aschen-Brut',
                        color=(80, 30, 30), glow=(255, 120, 60),
                        hp=30, dmg=9, speed=120, radius=15, xp=24,
                        gold=(6, 12), att_range=28, att_cd=0.9),
    'wurzelhueter':dict(name='Wurzelhüter',
                        color=(60, 100, 40), glow=(120, 200, 80),
                        hp=45, dmg=12, speed=78, radius=19, xp=28,
                        gold=(7, 13), att_range=34, att_cd=1.2),
}

ELITE_AFFIXES = ['fast', 'fire', 'vampiric', 'explosive']

# F-15/F-16/F-17 (Update #45): 10-Affix-Pool aus dem POE2-Briefing.
# Jeder Affix = Velgrad-Lore-konformer Bezeichner + Farbe + on-tick/on-hit
# Hook. Verteilung per `roll_affixes()`:
#   Tier 1 (magic, blau)   → 1 Affix
#   Tier 2-4 (rare, gelb)  → 2-4 Affixes
#   Tier 5-6 (unique, orange) → 5-6 Affixes
# Magic-Chance = elite_chance (10 %), Rare 3 %, Unique 0.4 %.
AFFIX_POOL = {
    'flameweaver':  dict(name='Flammenweber',  color=(255, 120, 40),
                          dmg_type='fire',
                          desc='Brennende Aura — Fire-DoT um den Mob'),
    'frostbearer':  dict(name='Frostträger',   color=(140, 200, 255),
                          dmg_type='cold',
                          desc='Eisige Schwelle — verlangsamt Spieler in Nähe'),
    'stormcaller':  dict(name='Sturmrufer',    color=(220, 220, 120),
                          dmg_type='lightning',
                          desc='Spontane Blitze auf den Spieler'),
    'vampiric':     dict(name='Blutbund',      color=(220, 60, 60),
                          dmg_type='physical',
                          desc='Heilt sich pro Hit am Spieler'),
    'bloodthirsty': dict(name='Blutdürstig',   color=(180, 30, 30),
                          dmg_type='physical',
                          desc='+30 % Speed wenn unter 50 % HP'),
    'soul_eater':   dict(name='Seelenfresser', color=(180, 100, 220),
                          dmg_type='chaos',
                          desc='Wird stärker bei jedem nahen Mob-Tod'),
    'necromancer':  dict(name='Beschwörer',    color=(110, 80, 160),
                          dmg_type='chaos',
                          desc='Beschwört 1 Skelett alle 8 s'),
    'phasing':      dict(name='Phasenwandler', color=(160, 180, 220),
                          dmg_type='physical',
                          desc='Wird kurz unverwundbar (3 s CD)'),
    'teleporter':   dict(name='Springer',      color=(200, 140, 240),
                          dmg_type='chaos',
                          desc='Teleportiert zu Spieler alle 5 s'),
    'detonating':   dict(name='Detonierend',   color=(255, 200, 60),
                          dmg_type='fire',
                          desc='Explodiert bei Tod (90 px AoE)'),
}
AFFIX_KEYS = list(AFFIX_POOL.keys())


def roll_affixes(rng=None):
    """F-16: rollt Tier + Affix-Liste basierend auf gestaffelten Chancen.

    Returnt (tier, [affix_keys]):
      tier = 'magic'  → 1 Affix
      tier = 'rare'   → 2-4 Affixes
      tier = 'unique' → 5-6 Affixes
      tier = None     → keine
    """
    rng = rng or random
    roll = rng.random()
    if roll < 0.004:
        tier = 'unique'
        n = rng.randint(5, 6)
    elif roll < 0.034:
        tier = 'rare'
        n = rng.randint(2, 4)
    elif roll < 0.134:
        tier = 'magic'
        n = 1
    else:
        return (None, [])
    affixes = rng.sample(AFFIX_KEYS, min(n, len(AFFIX_KEYS)))
    return (tier, affixes)


# F-16: Tier-Outline-Farben
AFFIX_TIER_COLOR = {
    'magic':  (90, 130, 220),    # blau
    'rare':   (240, 220, 80),    # gelb
    'unique': (255, 140, 60),    # orange
}


# type_key → Archetyp-Mapping für die D-State-Machine.
# Legacy-Mobs werden damit automatisch nicht-magnetisch (Sight/Hearing).
_TYPE_TO_ARCHETYPE = {
    'zombie':    'brute',
    'skeleton':  'skirmisher',
    'wraith':    'caster',     # ranged spectral
    'demon':     'brute',
    'brute':     'brute',
    'archer':    'ranged',
    'shaman':    'caster',
    'warlock':   'caster',
    'berserker': 'charger',
    'lurker':    'stalker',
    'slime':     'skirmisher',
    # Update #44: neue Mobs
    'salzgeist':    'stalker',     # blinkt bei Hit
    'glaslord':     'brute',       # langsam, explodiert bei Tod
    'aschenbrut':   'skirmisher',  # schnell, explodiert bei Tod
    'wurzelhueter': 'brute',       # langsam, Poison-Root
}


def spawn_enemy(type_key, x, y, wave, elite_chance=0.18):
    # F-15/F-16 (Update #45): neuer Tier-Roll.  Pre-#45 nutzte `elite_chance`
    # nur für 4-Affix-Single-Roll; jetzt rollen wir Tier (magic/rare/unique)
    # mit gestaffelten Wahrscheinlichkeiten und mehreren Affixes.  Damit der
    # `elite_chance`-Parameter (z. B. underworld_rift mit 0.65) weiter
    # funktioniert, skalieren wir die magic-Schwelle entsprechend.
    base_tier, base_affixes = roll_affixes()
    if base_tier is None and random.random() < elite_chance:
        # Caller hat explizit eine erhöhte Elite-Chance → erzwinge magic
        base_tier = 'magic'
        base_affixes = random.sample(AFFIX_KEYS, 1)
    elite = base_tier is not None
    affix = base_affixes[0] if base_affixes else None  # Legacy-Field
    e = Enemy(type_key, x, y, wave, ENEMY_TYPES[type_key],
              elite=elite, affix=affix)
    # Multi-Affix-Tracking (F-16)
    e.affix_tier = base_tier
    e.affixes = list(base_affixes)
    # Rare/Unique bekommen multiplikativen HP/DMG-Bonus (F-16)
    if base_tier == 'rare':
        e.hp_max *= 1.6
        e.hp = e.hp_max
        e.dmg *= 1.2
        e.xp = int(e.xp * 2.0)
        e.gold_range = (e.gold_range[0] * 2, e.gold_range[1] * 3)
    elif base_tier == 'unique':
        e.hp_max *= 2.4
        e.hp = e.hp_max
        e.dmg *= 1.5
        e.xp = int(e.xp * 4.0)
        e.gold_range = (e.gold_range[0] * 4, e.gold_range[1] * 6)
    # PLAN D-Block: Legacy-Mobs nicht-magnetisch machen — State-Machine
    # mit Sight/Hearing-Profilen statt direkter Aggro vom Bildschirmrand.
    arch = _TYPE_TO_ARCHETYPE.get(type_key)
    if arch is not None:
        from . import archetypes as _arch
        _arch.apply_to_enemy(e, arch)
    # Update #44: Bestiarium-Behaviors
    if type_key == 'glaslord':
        e.on_death_behavior = 'ice_shatter'
    elif type_key == 'aschenbrut':
        e.on_death_behavior = 'fire_burst'
    # F-15 Affix-Effekte direkt am Spawn anwenden
    if 'flameweaver' in e.affixes:
        e.dmg *= 1.10  # Fire-Aura ist DPS-Boost
    if 'bloodthirsty' in e.affixes:
        e._bloodthirsty_triggered = False
    if 'detonating' in e.affixes:
        e.on_death_behavior = 'affix_detonate'  # überschreibt Mob-Standard
    # PLAN F-12 (Update #96): Guardian-Shield-HP-System.
    # Brutes mit hoher HP bekommen einen Shield-Buffer der zuerst gebrochen
    # werden muss. Shield regeneriert NICHT — einmal weg, immer weg.
    if type_key in ('brute', 'glaslord'):
        e.shield_hp = e.hp_max * 0.30
        e.shield_hp_max = e.shield_hp
    return e


# ============================================================
# BOSSE
# ============================================================
BOSS_TEMPLATES = {
    'necromancer': dict(
        name='Mortis der Beschwörer', title='Herr der Toten',
        kind='necromancer',
        color=(70, 30, 80), glow=(180, 100, 240),
        hp=600,  dmg=18, speed=70, radius=34, xp=400, gold=(80, 150),
        att_range=48, att_cd=1.4, ranged=False, ability_cd=4.5,
    ),
    'bone_knight': dict(
        name='Sir Ossian', title='Knochenritter',
        kind='bone_knight',
        color=(200, 190, 170), glow=(255, 240, 200),
        hp=900,  dmg=24, speed=85, radius=36, xp=500, gold=(100, 180),
        att_range=52, att_cd=1.0, ranged=False, ability_cd=5.0,
        resistances={'physical': 0.4},
    ),
    'frostlord': dict(
        name='Glacius der Eisherr', title='Wächter des ewigen Frosts',
        kind='frostlord',
        color=(50, 100, 180), glow=(180, 220, 255),
        hp=900,  dmg=22, speed=80, radius=36, xp=700, gold=(150, 280),
        att_range=54, att_cd=1.2, ranged=False, ability_cd=3.2,
        resistances={'cold': 0.6},
    ),
    'snow_queen': dict(
        name='Elsara', title='Königin des ewigen Winters',
        kind='snow_queen',
        color=(140, 180, 240), glow=(230, 250, 255),
        hp=1100, dmg=20, speed=100, radius=32, xp=850, gold=(180, 320),
        att_range=320, att_cd=1.3, ranged=False, ability_cd=2.8,
        resistances={'cold': 0.7, 'physical': 0.2},
    ),
    'dragon': dict(
        name='Pyron der Schwarzdrache', title='Verzehrer der Welten',
        kind='dragon',
        color=(120, 30, 30), glow=(255, 120, 60),
        hp=1500, dmg=28, speed=95, radius=42, xp=1200, gold=(300, 500),
        att_range=60, att_cd=1.1, ranged=False, ability_cd=2.5,
        resistances={'fire': 0.7},
    ),
    'magma_golem': dict(
        name='Vulkanus', title='Lebende Lava',
        kind='magma_golem',
        color=(80, 30, 20), glow=(255, 140, 60),
        hp=1800, dmg=32, speed=60, radius=44, xp=1400, gold=(340, 560),
        att_range=58, att_cd=1.5, ranged=False, ability_cd=4.0,
        resistances={'fire': 0.8, 'physical': 0.3},
    ),
    'shadow_lord': dict(
        name='Nox Eternus', title='Schattenfürst der Vergessenheit',
        kind='shadow_lord',
        color=(20, 0, 30), glow=(180, 80, 240),
        hp=3000, dmg=40, speed=110, radius=38, xp=3000, gold=(600, 1200),
        att_range=56, att_cd=1.0, ranged=False, ability_cd=2.2,
        resistances={'physical': 0.4, 'fire': 0.4, 'cold': 0.4, 'lightning': 0.4},
    ),
}

# Mapping: biome → mögliche Bosse für jeweilige Dungeons
BIOME_BOSSES = {
    'crypt': ['necromancer', 'bone_knight'],
    'frost': ['frostlord', 'snow_queen'],
    'lava':  ['dragon', 'magma_golem'],
}


def boss_for_wave(wave):
    """Returnt eine Boss-Variante basierend auf einem Wave-Counter.

    Update #121: Survival-Modus entfernt; diese Funktion wird aktuell
    nicht mehr direkt aufgerufen, bleibt aber als Helper für
    Boss-Rotation in zukünftigen Atlas-/Endgame-Modi erhalten.
    """
    keys = ['necromancer', 'frostlord', 'dragon', 'bone_knight',
            'snow_queen', 'magma_golem']
    return keys[(wave // 5 - 1) % len(keys)]


def spawn_boss(boss_key, x, y, wave):
    t = BOSS_TEMPLATES[boss_key]
    e = Enemy('zombie', x, y, wave, t)  # type_key egal, override unten
    e.type_key = boss_key
    e.color = t['color']
    e.glow = t['glow']
    e.is_boss = True
    e.boss_name = t['name']
    e.boss_title = t.get('title', '')
    e.boss_kind = t['kind']
    e.boss_ability_cd = t['ability_cd']
    e.resistances = dict(t.get('resistances', {}))
    # Boss-Shield: 30% der HP als Schild
    e.shield_max = e.hp_max * 0.3
    e.shield = e.shield_max
    return e


# ============================================================
# AI-UPDATE (wird von Game aufgerufen)
# ============================================================
def _engage_charge(game, e, dt, diff, d):
    """CHARGER-Pattern (F-08): Approach → Wind-Up-Telegraph → Sprint → Hit → CD.

    Bestiarium-Beispiel Krustenkrabbe: „Charge mit Schere, telegraphed
    durch hochgezogene Pinzette (1s)." — wir setzen einen DEADLY-Decal
    an die Player-Pos beim Charge-Start, sprintet dann durch.
    """
    speed = e.speed * e.slow_factor
    state = getattr(e, '_charge_state', 'approach')  # approach|windup|sprint|cd

    if state == 'approach':
        # Range ~5 m heran, dann Wind-Up starten.
        if d > 6 * 32:
            n = diff.normalize() if d > 0 else None
            if n:
                game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
        else:
            # Wind-Up: Telegraph an Player-Pos
            from . import effects as _fx
            target_x = game.player.pos.x
            target_y = game.player.pos.y
            _fx.spawn_ground_decal(
                game, target_x, target_y, radius=e.radius + 14,
                kind=_fx.DECAL_KIND.DEADLY,
                windup=1.0, lifetime=0.0)
            e._charge_state = 'windup'
            e._charge_target = (target_x, target_y)
            e._charge_t = 1.0  # Wind-Up-Dauer
        return True

    if state == 'windup':
        # Wind-Up: leichte Bewegung Richtung Spieler (anvisieren) aber langsam
        e._charge_t -= dt
        if d > 0:
            n = diff.normalize()
            game.move_entity(e, n.x * speed * 0.25 * dt, n.y * speed * 0.25 * dt)
        if e._charge_t <= 0:
            e._charge_state = 'sprint'
            e._charge_t = 0.6  # max Sprint-Dauer
        return True

    if state == 'sprint':
        # Sprint Richtung Charge-Target mit doppelter Speed
        e._charge_t -= dt
        tx, ty = e._charge_target
        dx = tx - e.pos.x
        dy = ty - e.pos.y
        dist = math.hypot(dx, dy)
        if dist < 4 or e._charge_t <= 0:
            # Treffer-Check am Ziel + AoE-Damage in Mini-Radius
            if (game.player.pos - e.pos).length() <= e.radius + 32:
                game.damage_player(e.dmg * 1.5, dmg_type='physical', source=e)
            game.shake = max(game.shake, 6)
            game.spawn_particles(e.pos.x, e.pos.y, 16, e.color,
                                 life_max=0.5, size_max=4, gravity=80)
            e._charge_state = 'cd'
            e._charge_t = 1.8 + random.uniform(0, 0.6)
            return True
        n_x = dx / dist
        n_y = dy / dist
        game.move_entity(e, n_x * speed * 2.0 * dt, n_y * speed * 2.0 * dt)
        return True

    if state == 'cd':
        e._charge_t -= dt
        if e._charge_t <= 0:
            e._charge_state = 'approach'
        # Während CD: leichtes Backstep für „kreisen"-Feeling
        if d > 0:
            n = diff.normalize()
            game.move_entity(e, -n.x * speed * 0.35 * dt, -n.y * speed * 0.35 * dt)
        return True

    return False


def _engage_aerial(game, e, dt, diff, d):
    """FLYER-Pattern (F-14): Kreist über Player, dann Dive-Bomb mit
    aerial Telegraph (Briefing C-07 — Schatten + wachsender Stern-Riss).

    Bestiarium-Beispiel Möwen-Schwarm: „Kreisen erst über dem Spieler,
    stürzen einzeln im Wechsel ab (jeweils 0.5s Telegraph mit Schatten
    am Boden)."
    """
    speed = e.speed * e.slow_factor
    state = getattr(e, '_aerial_state', 'circle')

    if state == 'circle':
        # Halte ~6 m Distanz, kreise gegen Uhrzeigersinn
        ideal = e.prefers_distance_px or (6 * 32)
        if d > ideal + 60:
            n = diff.normalize() if d > 0 else None
            if n:
                game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
        elif d < ideal - 30:
            n = diff.normalize() if d > 0 else None
            if n:
                game.move_entity(e, -n.x * speed * dt, -n.y * speed * dt)
        else:
            # Strafen quer zur Sichtlinie
            if d > 0:
                n = diff.normalize()
                tang_x, tang_y = -n.y, n.x  # 90°-Rotation
                game.move_entity(e, tang_x * speed * 0.6 * dt,
                                 tang_y * speed * 0.6 * dt)
        # Dive-Cooldown
        e._aerial_dive_cd = getattr(e, '_aerial_dive_cd', 2.5) - dt
        if e._aerial_dive_cd <= 0:
            # Telegraph mit aerial=True
            from . import effects as _fx
            target_x = game.player.pos.x
            target_y = game.player.pos.y
            _fx.spawn_ground_decal(
                game, target_x, target_y, radius=42,
                kind=_fx.DECAL_KIND.DEADLY,
                windup=0.6, lifetime=0.0, aerial=True,
                play_windup=False)  # FLYER hat eigenen Wind-Up-Audio via Decal
            e._aerial_state = 'dive'
            e._aerial_t = 0.6
            e._aerial_target = (target_x, target_y)
        return True

    if state == 'dive':
        e._aerial_t -= dt
        tx, ty = e._aerial_target
        dx = tx - e.pos.x
        dy = ty - e.pos.y
        dist = math.hypot(dx, dy)
        if e._aerial_t <= 0 or dist < 4:
            if (game.player.pos - e.pos).length() <= 32:
                game.damage_player(e.dmg, dmg_type='physical', source=e)
                # Möwen-Bonus: Bleed-Buildup
                from . import effects as _fx
                _fx.apply(game, game.player, 'bleed', stacks=1)
            e._aerial_state = 'circle'
            e._aerial_dive_cd = 3.5 + random.uniform(0, 1.0)
            return True
        if dist > 0:
            n_x = dx / dist
            n_y = dy / dist
            game.move_entity(e, n_x * speed * 2.5 * dt,
                             n_y * speed * 2.5 * dt)
        return True
    return False


def _engage_caster_telegraphed(game, e, dt, diff, d):
    """CASTER-Pattern (F-04): hält Distanz, casts AoE-Decals statt
    direkt-Schaden.

    Bestiarium-Beispiel Ertrunkenes Echo: „Castet Wasser-Speer (langsam,
    hohe Cold-Damage), telegraphed 1.2s". Wir nutzen den Decal-Pfad mit
    Cold-Damage-Apply beim Activate.
    """
    speed = e.speed * e.slow_factor
    ideal = e.prefers_distance_px or (10 * 32)

    # Movement: halte Distanz
    if d > ideal + 80:
        n = diff.normalize() if d > 0 else None
        if n:
            game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
    elif d < ideal - 50:
        n = diff.normalize() if d > 0 else None
        if n:
            game.move_entity(e, -n.x * speed * 0.8 * dt,
                             -n.y * speed * 0.8 * dt)

    # Cast-Cooldown
    e._cast_cd = getattr(e, '_cast_cd', 2.0) - dt
    if e._cast_cd <= 0:
        # Update #106 (Audit F-012): LOS-Check vor Cast. Boss-Fairness —
        # Caster sollen nicht durch Wände casten.  Wenn kein LOS, kurzer
        # Re-Try-CD setzen (0.5 s) statt Decal spawnen.
        if game.grid is not None and not game.grid.has_los(
                e.pos.x, e.pos.y,
                game.player.pos.x, game.player.pos.y):
            e._cast_cd = 0.5
            return True
        from . import effects as _fx
        from pygame.math import Vector2 as _V
        target_x = game.player.pos.x
        target_y = game.player.pos.y
        damage = e.dmg * 1.4
        target_pos = _V(target_x, target_y)

        def _on_activate(g, decal, _dmg=damage, _tp=target_pos, _src=e):
            if (g.player.pos - _tp).length() <= decal.radius:
                g.damage_player(_dmg, dmg_type='cold', source=_src)
                # Ertrunkenes Echo macht Cold-Damage mit Freeze-Buildup
                _fx.apply(g, g.player, 'frost', stacks=2)
            g.spawn_particles(_tp.x, _tp.y, 24, (150, 200, 230),
                              life_max=0.7, size_max=5, gravity=40)

        _fx.spawn_ground_decal(
            game, target_x, target_y, radius=50,
            kind=_fx.DECAL_KIND.DEADLY,
            windup=1.2, lifetime=0.0,
            on_activate=_on_activate)
        e._cast_cd = 2.4 + random.uniform(0, 0.8)
    return True


def _do_non_combat_movement(game, e, dt, hint):
    """Patrol/Investigate/Idle-Bewegung für State-Machine-Mobs.

    Sehr leichtgewichtig: keine Pathfinding-Suche, nur Direkt-Vektor.
    Combat-Tick wird übersprungen — der Mob greift NICHT an, solange er
    nicht in AGGRO ist (D-08: ALERT untersucht erst, attackiert nicht).
    """
    if hint == 'idle' or hint is None:
        return
    speed = e.speed * e.slow_factor * 0.6  # Patrol-Speed = 60 % Combat-Speed

    target = None
    if hint == 'investigate':
        lk = getattr(e, 'last_known_player_pos', None)
        if lk is not None:
            target = lk
    elif hint == 'patrol':
        target = _next_patrol_target(e)

    if target is None:
        return
    tx, ty = target
    dx = tx - e.pos.x
    dy = ty - e.pos.y
    dist = math.hypot(dx, dy)
    if dist < 6:
        # Waypoint erreicht — nächsten Punkt im Patrol-Cycle nehmen
        if hint == 'patrol' and e.patrol_pattern == 'waypoint':
            e.patrol_index = (e.patrol_index + 1) % max(
                1, len(e.patrol_waypoints or []))
        return
    nx = dx / dist
    ny = dy / dist
    e.facing_deg = math.degrees(math.atan2(ny, nx))
    new_x = e.pos.x + nx * speed * dt
    new_y = e.pos.y + ny * speed * dt
    if game.world_walkable(new_x, new_y, e.radius):
        e.pos.x = new_x
        e.pos.y = new_y


def _next_patrol_target(e):
    pat = e.patrol_pattern
    if pat == 'waypoint' and e.patrol_waypoints:
        idx = e.patrol_index % len(e.patrol_waypoints)
        wp = e.patrol_waypoints[idx]
        return (wp[0], wp[1])
    if pat == 'random_area':
        # Wenn kein Sub-Target gesetzt oder erreicht, neues Random
        sub = getattr(e, '_patrol_subtarget', None)
        if sub is None:
            sp = e.spawn_pos
            sub = (sp.x + random.uniform(-200, 200),
                   sp.y + random.uniform(-200, 200))
            e._patrol_subtarget = sub
        # Reached?
        if math.hypot(sub[0] - e.pos.x, sub[1] - e.pos.y) < 8:
            e._patrol_subtarget = None
        return e._patrol_subtarget
    if pat == 'stationary':
        # Scan-Rotation: ändert facing periodisch +-45°
        e.facing_deg = (getattr(e, 'facing_deg', 90.0)
                        + math.sin(getattr(e, 'ai_state_t', 0) * 0.8) * 30)
        return None
    return None


# ============================================================
# BOSS-HELPER (Update #42)
# ============================================================
def _boss_can_target(game, e, max_dist=700.0):
    """Boss darf nur dann Fähigkeiten zünden, wenn Spieler in Reichweite
    UND Line-of-Sight existiert. Verhindert Wand-Angriffe (User-Feedback)."""
    p = game.player
    d = (p.pos - e.pos).length()
    if d > max_dist:
        return False
    if game.grid is not None and not game.grid.has_los(
            e.pos.x, e.pos.y, p.pos.x, p.pos.y):
        return False
    return True


def _telegraph_floater(game, e, text, color=(255, 90, 60)):
    """Roter Warn-Floater über dem Boss-Kopf (Telegraph für neue Attacke)."""
    h = getattr(e, 'height', e.radius * 2)
    game.floaters.append(Floater(
        e.pos.x, e.pos.y - h - 14, text, color, big=True, life=1.1))


def _boss_meteor_storm(game, e, n_meteors, dmg, color=(255, 120, 50)):
    """Aerial-Meteor-Sturm: n Decals fallen verzögert in Spieler-Nähe.

    Nutzt das Decal-System (aerial=True → Schatten + Stern-Riss).
    Jeder Meteor hat 0.7–1.1 s Wind-Up + AoE-Damage bei Aufschlag.
    """
    from . import effects as _fx
    p = game.player
    base_x = p.pos.x
    base_y = p.pos.y
    for i in range(n_meteors):
        # Spread um Spieler, leicht versetzt, einer landet immer fast direkt
        if i == 0:
            ox, oy = random.uniform(-30, 30), random.uniform(-30, 30)
        else:
            r = random.uniform(40, 140)
            a = random.uniform(0, math.tau)
            ox, oy = math.cos(a) * r, math.sin(a) * r
        mx, my = base_x + ox, base_y + oy
        windup = random.uniform(0.7, 1.1) + i * 0.05  # gestaffelt
        radius = random.uniform(58, 72)
        meteor_dmg = float(dmg)
        meteor_col = tuple(color)

        def _on_activate(g, decal, _dmg=meteor_dmg, _mx=mx, _my=my,
                         _col=meteor_col, _src=e):
            from pygame.math import Vector2 as _V
            if (g.player.pos - _V(_mx, _my)).length() <= decal.radius:
                g.damage_player(_dmg, dmg_type='fire', source=_src)
            g.spawn_particles(_mx, _my, 42, _col,
                              life_max=0.9, size_max=8, gravity=80)
            g.spawn_particles(_mx, _my, 18, (255, 230, 120),
                              life_max=0.6, size_max=5)
            g.shake = max(g.shake, 7)

        _fx.spawn_ground_decal(
            game, mx, my, radius=radius,
            kind=_fx.DECAL_KIND.DEADLY,
            windup=windup, lifetime=0.0,
            aerial=True, on_activate=_on_activate)


def _tick_affixes(game, e, dt, _diff, d):
    """F-15 (Update #45): pro-Frame Affix-Effekte.

    Hängt eigenständige Timer/State-Variablen an den Mob.  Wird in
    update_enemy_ai zu Beginn aufgerufen.
    """
    affixes = getattr(e, 'affixes', None)
    if not affixes:
        return
    p = game.player
    # Stormcaller: alle 4.5 s ein Blitz auf den Spieler (50 px AoE)
    # Update #46: Telegraph-Decal 0.7 s vor dem Strike — User-Bug
    # „stirbt einfach so". Spieler kann jetzt ausweichen.
    if 'stormcaller' in affixes:
        e._storm_cd = getattr(e, '_storm_cd', 4.5) - dt
        if e._storm_cd <= 0 and d < 500:
            e._storm_cd = 4.5
            from . import effects as _fx
            from pygame.math import Vector2 as _V
            target_x, target_y = p.pos.x, p.pos.y
            dmg_val = e.dmg * 0.7

            def _on_storm(g, decal, _x=target_x, _y=target_y,
                          _dmg=dmg_val, _src=e):
                from .entities import LightningBolt
                g.bolts.append(LightningBolt(_x, _y - 320, _x, _y))
                if (g.player.pos - _V(_x, _y)).length() < decal.radius:
                    g.damage_player(_dmg, dmg_type='lightning', source=_src)
                g.spawn_particles(_x, _y, 18, (220, 220, 120),
                                   life_max=0.4, size_max=4, friendly=False)
                try:
                    from . import sounds as _snd
                    _snd.play('cast_lightning', volume=0.4)
                except Exception:
                    pass

            _fx.spawn_ground_decal(
                game, target_x, target_y, radius=60,
                kind=_fx.DECAL_KIND.DEADLY,
                windup=0.7, lifetime=0.0,
                on_activate=_on_storm)
    # Frostbearer-Aura: Spieler in 90 px slow
    if 'frostbearer' in affixes and d < 90:
        p.slow_timer = max(p.slow_timer, 0.5)
        p.slow_factor = min(p.slow_factor, 0.75)
    # Flameweaver-Aura: Spieler in 70 px burn
    if 'flameweaver' in affixes and d < 70:
        e._flame_tick = getattr(e, '_flame_tick', 0.0) + dt
        if e._flame_tick >= 0.7:
            e._flame_tick = 0.0
            from . import effects as _fx
            _fx.apply(game, p, 'burn', stacks=1)
    # Bloodthirsty: bei <50 % HP einmaliger Speed-Buff
    if 'bloodthirsty' in affixes and not getattr(e, '_bloodthirsty_triggered',
                                                   False):
        if e.hp < e.hp_max * 0.5:
            e._bloodthirsty_triggered = True
            e.speed *= 1.3
            game.floaters.append(Floater(e.pos.x, e.pos.y - 30,
                                          'BLUTRAUSCH!', (220, 60, 60)))
    # Necromancer-Affix: alle 8 s 1 Skelett
    if 'necromancer' in affixes:
        e._necro_cd = getattr(e, '_necro_cd', 8.0) - dt
        if e._necro_cd <= 0:
            e._necro_cd = 8.0
            sx = e.pos.x + random.uniform(-30, 30)
            sy = e.pos.y + random.uniform(-30, 30)
            # Update #121-Fix: game.wave entfernt, nutze player.level.
            minion = spawn_enemy('skeleton', sx, sy,
                                  max(1, game.player.level),
                                  elite_chance=0)
            game.enemies.append(minion)
            game.spawn_particles(sx, sy, 12, (110, 80, 160),
                                  life_max=0.6, size_max=4, friendly=False)
    # Phasing: alle 7 s 1.2 s unverwundbar
    # Update #55-Bugfix: Decrement von `_encounter_invuln_left` läuft jetzt
    # zentral in `update_enemy_ai` (Safety-Net).  User-Bug „Monster ist
    # gegen alles immun" — vorher fehlte der Decrement komplett.
    if 'phasing' in affixes:
        e._phase_cd = getattr(e, '_phase_cd', 7.0) - dt
        if e._phase_cd <= 0:
            e._phase_cd = 7.0
            e._encounter_invuln_left = 1.2  # Phase startet — wird zentral getickt
            game.spawn_particles(e.pos.x, e.pos.y, 16, (160, 180, 220),
                                  life_max=0.5, size_max=4, friendly=False)
    # Teleporter: alle 5 s zu Spieler (wenn weit weg)
    if 'teleporter' in affixes:
        e._tele_cd = getattr(e, '_tele_cd', 5.0) - dt
        if e._tele_cd <= 0 and d > 200:
            e._tele_cd = 5.0
            ang = random.uniform(0, math.tau)
            nx = p.pos.x + math.cos(ang) * 80
            ny = p.pos.y + math.sin(ang) * 80
            if game.grid is None or not game.grid.collide_circle(
                    nx, ny, e.radius):
                game.spawn_particles(e.pos.x, e.pos.y, 18, (200, 140, 240),
                                      life_max=0.5, size_max=4, friendly=False)
                e.pos.x, e.pos.y = nx, ny
                game.spawn_particles(nx, ny, 18, (200, 140, 240),
                                      life_max=0.5, size_max=4, friendly=False)


def update_enemy_ai(game, e, dt):
    p = game.player
    diff = p.pos - e.pos
    d = diff.length()
    if d == 0:
        return
    # Update #55-Bugfix Safety-Net: für nicht-Boss-Mobs sicherstellen, dass
    # `_encounter_invuln_left` auch IMMER dekrementiert wird, falls ein
    # Code-Pfad das Feld setzt aber kein eigener Tick existiert.  Boss-Mobs
    # nutzen `tick_encounter()` für ihre Decrement-Logik — nicht anfassen.
    if (not e.is_boss
            and getattr(e, '_encounter_invuln_left', 0.0) > 0):
        e._encounter_invuln_left = max(
            0.0, e._encounter_invuln_left - dt)
    # F-15: Affix-Tick (Stormcaller/Frost-Aura/Necro-Summon/Phase/Teleport)
    if getattr(e, 'affixes', None):
        _tick_affixes(game, e, dt, diff, d)
    # Update #106 (Audit F-009): Pending-Special-Wind-Up-Tick.
    # Wenn ein Special angekündigt wurde, läuft sein Timer ab.  Erst
    # nach Wind-Up wird das Projectile gespawnt — gibt dem Spieler Frames
    # zur Reaktion (POE2-Telegraph-Standard).
    ps = getattr(e, '_pending_special', None)
    if ps is not None:
        ps['timer'] -= dt
        if ps['timer'] <= 0:
            _resolve_pending_special(game, e, ps)
            e._pending_special = None
    # PLAN F-13 (Update #96): EXPLODER-Aura (lebende Plague-Aura).
    # Aschenbrut hat im Leben eine kleine Ascheglut-Aura, die Spieler bei
    # Berührung leicht beschädigt (1 dmg/Tick).  Lore: glimmende Asche.
    if e.type_key == 'aschenbrut' and d < 38 and d > 0:
        if not hasattr(e, '_plague_aura_t'):
            e._plague_aura_t = 0.0
        e._plague_aura_t += dt
        if e._plague_aura_t >= 1.0:
            e._plague_aura_t = 0.0
            try:
                game.damage_player(2 + e.dmg * 0.05, dmg_type='fire',
                                     source=e)
            except Exception:
                pass
    # D-10 (Update #47): Pack-Reaction-Timer-Decay
    if getattr(e, '_pack_reaction_left', 0) > 0:
        e._pack_reaction_left -= dt
        if e._pack_reaction_left <= 0:
            e._pack_reaction_type = None
            e._dmg_mult = 1.0
            e._speed_mult = 1.0
    # L-06 (Update #47): Pin sperrt Bewegung komplett (kein AI-Tick)
    if 'pinned' in getattr(e, 'status', {}):
        return
    # Update #40: Attack-Animation ticks ZUERST. Wenn busy mit
    # windup/swing/recover → keine andere AI-Aktion.
    if hasattr(e, 'atk_phase') and e.atk_phase != 'idle':
        tick_enemy_attack_animation(game, e, dt)
        return

    # PLAN D-Block: State-Machine-Mobs (Bestiarium-Spawns) durchlaufen
    # eine Sicht/Gehör-State-Machine. Ergebnis ist ein Action-Hint, der
    # entscheidet, ob die Aggro-Combat-Logik unten überhaupt läuft.
    #
    # Frame-Phase (D-15) ist als Hook gedacht, um bei sehr vielen Gegnern
    # den line_of_sight-Raycast zu cachen — aktuell ist der Tick immer
    # vollständig (transitions würden sonst verschluckt werden, siehe
    # CHANGELOG #6). Performance-Optimization für späteren Zeitpunkt.
    if getattr(e, 'uses_state_machine', False) and not e.is_boss:
        from . import ai as _ai
        hint = _ai.tick_ai_state(game, e, dt)
        if hint != 'engage':
            _do_non_combat_movement(game, e, dt, hint)
            return

    # D-10 (Update #47): Pack-Reaction-Speed-Mod
    speed = e.speed * e.slow_factor * getattr(e, '_speed_mult', 1.0)

    # PLAN F-02..F-14 Signature-Combat: archetype-spezifische engage-Pattern.
    # Greift nur bei state-machine-Mobs in AGGRO; alte Mobs durchlaufen den
    # alten Code unten. Handler returnen True wenn sie den Tick abschließen.
    if getattr(e, 'uses_state_machine', False) and not e.is_boss:
        mode = getattr(e, 'engage_mode', 'melee')
        if mode == 'charge' and _engage_charge(game, e, dt, diff, d):
            return
        if mode == 'aerial' and _engage_aerial(game, e, dt, diff, d):
            return
        if mode == 'ranged' and _engage_caster_telegraphed(game, e, dt, diff, d):
            return
        # PLAN F-05 (Update #96): KITE-Movement — RANGED mit kite-engage
        # hält Abstand zum Spieler. Wenn Spieler näher als ideal kommt,
        # bewegt sich der Mob aktiv weg.
        # PLAN F-03 (Update #97): SKIRMISHER Stab + Backstep.
        # Nach jedem Angriff (atk_phase=='recover') springt der Mob 60 px
        # zurück (Sprite-Float-back). Verhindert Brute-Force-Melee-Lock.
        if mode == 'skirmisher':
            phase = getattr(e, 'atk_phase', 'idle')
            if phase == 'recover' and getattr(e, '_did_backstep', False) is False:
                # Backstep ausführen
                if d > 0:
                    back_dist = 60
                    e.pos.x -= (diff.x / d) * back_dist
                    e.pos.y -= (diff.y / d) * back_dist
                    e._did_backstep = True
                    # Sand-/Dust-Particles am Backstep-Origin
                    for k in range(6):
                        a = random.uniform(0, math.tau)
                        sp = random.uniform(60, 100)
                        game.particles_push(
                            e.pos.x, e.pos.y,
                            math.cos(a) * sp, math.sin(a) * sp,
                            (160, 140, 100), random.uniform(0.3, 0.5),
                            random.uniform(2, 3), gravity=80)
            elif phase == 'idle':
                e._did_backstep = False
            # Continue mit default-Movement
        # PLAN F-07 (Update #97): SUMMONER-Logic.
        # Mob mit engage_mode='summon' beschwört alle 8 s einen kleinen
        # Minion (skeleton/zombie) in 50 px Radius. Limit: max 3 Minions.
        if mode == 'summon':
            if not hasattr(e, '_summon_cd'):
                e._summon_cd = 4.0
                e._summoned_minions = []
            e._summon_cd -= dt
            # Tote/expirierte Minions filtern
            e._summoned_minions = [
                m for m in e._summoned_minions
                if not m.dying and m in game.enemies]
            if e._summon_cd <= 0 and len(e._summoned_minions) < 3:
                e._summon_cd = 8.0
                ang = random.uniform(0, math.tau)
                sx_n = e.pos.x + math.cos(ang) * 50
                sy_n = e.pos.y + math.sin(ang) * 50
                minion_key = random.choice(['skeleton', 'zombie'])
                m = spawn_enemy(minion_key, sx_n, sy_n,
                                  max(1, game.player.level),
                                  elite_chance=0)
                m.is_minion = True
                game.enemies.append(m)
                e._summoned_minions.append(m)
                # Summon-Particles
                for k in range(20):
                    a = random.uniform(0, math.tau)
                    sp = random.uniform(60, 140)
                    game.particles_push(
                        sx_n, sy_n,
                        math.cos(a) * sp, math.sin(a) * sp,
                        (180, 130, 220), random.uniform(0.4, 0.8),
                        random.uniform(2, 4))
                try:
                    from . import sounds as _snd
                    _snd.play_with_fallback('cast_dark', 'cast_lightning',
                                              volume=0.4)
                except Exception:
                    pass
            return
        # PLAN F-06 (Update #97): SUPPORT/HEALER-Heal-Beam.
        # Mobs mit engage_mode='support' suchen verbündete Mobs in Range,
        # heilen sie für 2.5 dmg/s über einen 1.5 s Heal-Beam.
        if mode == 'support':
            ally_target = getattr(e, '_heal_target', None)
            if ally_target is None or ally_target.dying or ally_target.hp >= ally_target.hp_max:
                # Suche neuen Verbündeten
                best = None
                best_score = 0
                for other in game.enemies:
                    if other is e or other.dying:
                        continue
                    if other.hp >= other.hp_max:
                        continue
                    dist = (other.pos - e.pos).length()
                    if dist > 280:
                        continue
                    miss = (other.hp_max - other.hp) / other.hp_max
                    if miss > best_score:
                        best_score = miss
                        best = other
                e._heal_target = best
                ally_target = best
            if ally_target is not None:
                heal_amt = 2.5 * dt
                ally_target.hp = min(
                    ally_target.hp_max, ally_target.hp + heal_amt)
                # Heal-Beam-Particle alle paar Frames
                if random.random() < 0.4:
                    ang = math.atan2(
                        ally_target.pos.y - e.pos.y,
                        ally_target.pos.x - e.pos.x)
                    for k in range(2):
                        t = random.uniform(0.2, 0.8)
                        px = e.pos.x + math.cos(ang) * (ally_target.pos - e.pos).length() * t
                        py = e.pos.y + math.sin(ang) * (ally_target.pos - e.pos).length() * t
                        game.particles_push(
                            px, py, 0, -20,
                            (140, 230, 140), 0.4, 3,
                            gravity=-40)
                return
        if mode == 'kite':
            ideal = getattr(e, 'prefers_distance_px', 12 * 32)
            if d < ideal * 0.7 and d > 0:
                # Player zu nah → wegrennen
                e.pos.x -= (diff.x / d) * e.speed * dt
                e.pos.y -= (diff.y / d) * e.speed * dt
                return  # skip standard movement
            elif d > ideal * 1.3 and d > 0:
                # Zu weit → näher kommen aber langsam
                e.pos.x += (diff.x / d) * e.speed * 0.6 * dt
                e.pos.y += (diff.y / d) * e.speed * 0.6 * dt
                return
            # Im Sweet-Spot → in-place stehen + Ranged-Attack möglich
            return
        # 'melee', 'stalk', 'support', 'burrow', 'stationary' →
        # fallen aktuell auf default-Logik unten zurück.

    # Boss-Logik
    if e.is_boss:
        e.boss_ability_cd -= dt
        # Phase 2 Trigger: bei <50% HP einmaliger Effekt + Roar
        if not e.phase2_triggered and e.hp < e.hp_max * 0.5:
            e.phase2_triggered = True
            e.boss_phase = 2
            e.boss_ability_cd = 0.5
            e.att_cd *= 0.7
            e.speed *= 1.25
            game.shake = max(game.shake, 14)
            # Roar: visueller Pulse + Sound
            game.spawn_particles(e.pos.x, e.pos.y, 80, (255, 80, 80),
                                 life_max=1.0, size_max=8)
            game._damage_flash = max(game._damage_flash, 0.6)
            from . import sounds as _snd
            _snd.play('boss_intro', volume=0.8)
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - 60,
                f'{e.boss_name} entfesselt!', (255, 100, 100)))
            game.toast(f'Phase 2: {e.boss_name}', (255, 100, 100))

        # Heal-Once: einmaliger 50% HP-Heal bei <30%
        if not e.heal_used and e.hp < e.hp_max * 0.3:
            e.heal_used = True
            e.hp = min(e.hp_max, e.hp + e.hp_max * 0.5)
            game.spawn_particles(e.pos.x, e.pos.y, 60, (170, 255, 170),
                                 life_max=1.0, size_max=8)
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - 60,
                f'Boss heilt!', (170, 255, 170)))
            game.toast(f'{e.boss_name} heilt sich!', (170, 255, 170))

        # Charged-Attack ankündigen alle 8s (Phase2 6s)
        # Update #42: nur zünden wenn Spieler in Reichweite + LOS — sonst
        # Cooldown pausieren (Boss "wartet" auf Sicht).
        e.charge_cd -= dt
        if (e.charge_cd <= 0 and e.charged_attack is None
                and _boss_can_target(game, e, max_dist=520)):
            from pygame.math import Vector2 as _V
            e.charge_cd = 6.0 if e.boss_phase == 2 else 9.0
            e.charged_attack = {
                'target_pos': _V(game.player.pos.x, game.player.pos.y),
                'timer': 1.2,
                'radius': 120,
                'damage': e.dmg * 2.5,
            }
            # Audio-TELEGRAPH: Boss-Brüll-Warnung vor Schlag
            from . import sounds as _snd
            _snd.play('roar', volume=0.4)
            # Toast für visuellen Cue
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - e.height - 14,
                'WIND-UP!', (255, 100, 80)))
        # Charged-Attack-Timer (Boden-Markierung dann Schlag + Ground-Crack)
        if e.charged_attack is not None:
            e.charged_attack['timer'] -= dt
            if e.charged_attack['timer'] <= 0:
                ca = e.charged_attack
                # Update #106 (Audit F-008): LOS-Check vor Damage-Apply.
                # Boss-Fairness — Specials dürfen NICHT durch Wände hitten.
                in_radius = ((ca['target_pos'] - game.player.pos).length()
                              <= ca['radius'])
                has_los = True
                if game.grid is not None:
                    has_los = game.grid.has_los(
                        ca['target_pos'].x, ca['target_pos'].y,
                        game.player.pos.x, game.player.pos.y)
                if in_radius and has_los:
                    game.damage_player(ca['damage'])
                game.spawn_particles(ca['target_pos'].x, ca['target_pos'].y,
                                     50, (255, 80, 40),
                                     life_max=1.0, size_max=10, gravity=60)
                game.shake = max(game.shake, 12)
                # GROUND-CRACK: 5 radiale Risse, glühen rot, schaden 2.5s
                from pygame.math import Vector2 as _V
                crack_pos = _V(ca['target_pos'].x, ca['target_pos'].y)
                for k in range(5):
                    angle = (k / 5) * math.tau + random.uniform(-0.2, 0.2)
                    length = random.uniform(140, 200)
                    if hasattr(game, 'ground_cracks'):
                        game.ground_cracks.append({
                            'pos': crack_pos,
                            'dir': _V(math.cos(angle), math.sin(angle)),
                            'len': length,
                            'time_left': 2.5,
                            'dmg': ca['damage'] * 0.3,
                            'tick_cd': 0.3,
                        })
                # Schwarzer Flash am Aufprall
                if hasattr(game, '_damage_flash'):
                    game._damage_flash = max(game._damage_flash, 0.4)
                from . import sounds as _snd
                _snd.play('boss_intro', volume=0.6)
                e.charged_attack = None

        ability_mult = 0.7 if e.boss_phase == 2 else 1.0
        # Update #42: Bosse zünden Specials nur mit Sicht UND Reichweite.
        # Verhindert Angriffe durch Wände aus anderen Räumen (User-Bug).
        # Bei fehlender Sicht „wartet" der Cooldown auf 0.05s — Boss zündet
        # sofort, sobald Spieler sichtbar wird (kein Warte-Cheese).
        _can_cast = _boss_can_target(game, e, max_dist=700)
        if not _can_cast:
            if e.boss_ability_cd < 0.05:
                e.boss_ability_cd = 0.05
        if _can_cast and e.boss_kind == 'necromancer':
            # Beschwört regelmäßig Skelette + wirkt Schattenkugel
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 5.5 * ability_mult
                # 3 Skelette spawnen
                for _ in range(3):
                    a = random.uniform(0, math.tau)
                    sx = e.pos.x + math.cos(a) * 60
                    sy = e.pos.y + math.sin(a) * 60
                    minion = spawn_enemy('skeleton', sx, sy,
                                          max(1, game.player.level),
                                          elite_chance=0)
                    game.enemies.append(minion)
                # Schattenprojektil
                if d > 0:
                    dn = diff.normalize()
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y, dn.x * 280, dn.y * 280,
                        e.dmg * 1.2, 'shadowbolt', friendly=False,
                        radius=10, life=2.2,
                    ))
        elif _can_cast and e.boss_kind == 'frostlord':
            # Frost-Welle: AoE-Ring von Projektilen
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 4.5 * ability_mult
                for i in range(16):
                    a = (i / 16) * math.tau
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y,
                        math.cos(a) * 260, math.sin(a) * 260,
                        e.dmg * 0.8, 'frostbolt', friendly=False,
                        radius=11, life=1.8,
                    ))
        elif _can_cast and e.boss_kind == 'dragon':
            # Update #42: 3 verschiedene Attacks rotieren (Cone / Beam-Sweep / Meteor-Storm)
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 3.2 * ability_mult
                e._pattern = (getattr(e, '_pattern', 0) + 1) % 3
                pat = e._pattern
                if pat == 0:
                    # 1) Feuerstoß-Kegel (klassisch)
                    base_angle = math.atan2(diff.y, diff.x)
                    n_bolts = 7 if e.boss_phase == 2 else 5
                    spread = 0.5 if e.boss_phase == 2 else 0.35
                    for k in range(n_bolts):
                        offset = -spread + (k * 2 * spread / max(1, n_bolts - 1))
                        a = base_angle + offset
                        game.projectiles.append(Projectile(
                            e.pos.x, e.pos.y,
                            math.cos(a) * 360, math.sin(a) * 360,
                            e.dmg * 0.9, 'firebolt', friendly=False,
                            radius=9, life=1.3,
                        ))
                    _telegraph_floater(game, e, 'FLAMMENSTOSS!')
                elif pat == 1:
                    # 2) METEOR-STURM: 4-6 Delay-Decals an random Player-Nähe-Pos
                    n_meteors = 6 if e.boss_phase == 2 else 4
                    _boss_meteor_storm(game, e, n_meteors,
                                       dmg=e.dmg * 1.2,
                                       color=(255, 120, 50))
                    _telegraph_floater(game, e, 'METEOR-STURM!')
                else:
                    # 3) FEUER-BEAM-SWEEP: 8 Bolts in einem Bogen schnell hintereinander
                    base_angle = math.atan2(diff.y, diff.x)
                    sweep = 0.9
                    n = 8
                    for k in range(n):
                        a = base_angle - sweep / 2 + sweep * (k / max(1, n - 1))
                        # Stagger via delayed via vel/life-Trick:
                        # gleicher Spawn, gleiche Speed → spread-Effekt
                        game.projectiles.append(Projectile(
                            e.pos.x, e.pos.y,
                            math.cos(a) * 380, math.sin(a) * 380,
                            e.dmg * 0.7, 'firebolt', friendly=False,
                            radius=10, life=1.6,
                        ))
                    _telegraph_floater(game, e, 'FEUER-SWEEP!')
        elif _can_cast and e.boss_kind == 'bone_knight':
            # Charge: schiebt Spieler weg + AoE
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 4.8 * ability_mult
                if d > 0:
                    n = diff.normalize()
                    # Schnell-Charge
                    game.move_entity(e, n.x * 200, n.y * 200)
                # Schock-Ring
                for k in range(8):
                    a = (k / 8) * math.tau
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y,
                        math.cos(a) * 200, math.sin(a) * 200,
                        e.dmg * 0.7, 'firebolt', friendly=False,
                        radius=8, life=1.0,
                        extra={'color': (220, 200, 160)},
                    ))
                game.shake = max(game.shake, 8)
        elif _can_cast and e.boss_kind == 'snow_queen':
            # Eissalve: 3 Eis-Projektile auf Spieler, gelegentlich Eis-Nova
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 2.8 * ability_mult
                base_angle = math.atan2(diff.y, diff.x)
                # Salve
                for k in range(3):
                    a = base_angle + (k - 1) * 0.25
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y,
                        math.cos(a) * 320, math.sin(a) * 320,
                        e.dmg * 0.7, 'frostbolt', friendly=False,
                        radius=10, life=1.6,
                    ))
                # Phase 2: zusätzliche Frost-Nova
                if e.boss_phase == 2:
                    for k in range(12):
                        a = (k / 12) * math.tau
                        game.projectiles.append(Projectile(
                            e.pos.x, e.pos.y,
                            math.cos(a) * 220, math.sin(a) * 220,
                            e.dmg * 0.5, 'frostbolt', friendly=False,
                            radius=8, life=1.2,
                        ))
        elif _can_cast and e.boss_kind == 'magma_golem':
            # Schlagboden-AoE: Säulen aus Lava unter Spieler
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 3.8 * ability_mult
                # Spawnt 3-5 Lava-Säulen an Spieler-Position + benachbarte
                from pygame.math import Vector2 as _V
                target_positions = [
                    _V(game.player.pos.x, game.player.pos.y),
                    _V(game.player.pos.x + 80, game.player.pos.y),
                    _V(game.player.pos.x - 80, game.player.pos.y),
                ]
                if e.boss_phase == 2:
                    target_positions += [
                        _V(game.player.pos.x, game.player.pos.y + 80),
                        _V(game.player.pos.x, game.player.pos.y - 80),
                    ]
                for tp in target_positions:
                    # Erst Warn-Marker als Particle
                    for _ in range(8):
                        game.particles_push(tp.x, tp.y, 0, -80,
                                            (255, 120, 40), 0.4, 4)
                    # Sofortiger AoE-Hit
                    if (tp - game.player.pos).length() < 60:
                        game.damage_player(e.dmg * 0.8)
                    game.spawn_particles(tp.x, tp.y, 16, (255, 80, 30),
                                         life_max=0.6, size_max=5, gravity=120)
                game.shake = max(game.shake, 6)
        elif _can_cast and e.boss_kind == 'shadow_lord':
            # Multi-Phase: rotiert zwischen Shadow Cone, Teleport+Slam, Schwarzes Loch
            if e.boss_ability_cd <= 0:
                e.boss_ability_cd = 2.2 * ability_mult
                # Pattern: rotate
                pattern_idx = (int(getattr(e, '_pattern', 0))) % 3
                e._pattern = pattern_idx + 1
                if pattern_idx == 0:
                    # Shadow Cone
                    base_angle = math.atan2(diff.y, diff.x)
                    for k in range(7):
                        a = base_angle + (k - 3) * 0.18
                        game.projectiles.append(Projectile(
                            e.pos.x, e.pos.y,
                            math.cos(a) * 380, math.sin(a) * 380,
                            e.dmg * 0.8, 'shadowbolt', friendly=False,
                            radius=10, life=1.4,
                        ))
                elif pattern_idx == 1:
                    # Teleport hinter Spieler + Slam
                    behind = -diff.normalize() * 80 + game.player.pos
                    e.pos.x, e.pos.y = behind.x, behind.y
                    game.spawn_particles(e.pos.x, e.pos.y, 30,
                                         (180, 80, 240), life_max=0.8, size_max=6)
                    if (e.pos - game.player.pos).length() < 80:
                        game.damage_player(e.dmg * 1.2)
                    game.shake = max(game.shake, 10)
                else:
                    # SCHWARZES LOCH bei Spieler
                    if hasattr(game, 'black_holes'):
                        from pygame.math import Vector2 as _V
                        game.black_holes.append({
                            'pos': _V(game.player.pos.x, game.player.pos.y),
                            'time_left': 3.5,
                            'radius': 180,
                            'pull': 220,
                            'dmg': e.dmg * 0.5,
                            'tick_cd': 0.0,
                        })
                        from . import sounds as _snd
                        _snd.play('boss_intro', volume=0.7)
        # Bosse bewegen sich kontinuierlich auf Spieler zu
        # Update #43: Pathfinding-Fallback wenn Wand zwischen Boss + Spieler.
        # Ohne diesen Block laufen Bosse einfach gegen eine Wand und „stecken
        # fest" — User-Feedback. Logik gespiegelt vom normalen Mob-Code unten.
        if d > e.radius + p.radius:
            has_los = (game.grid is None) or game.grid.has_los(
                e.pos.x, e.pos.y, p.pos.x, p.pos.y)
            if game.grid is not None and not has_los:
                # Repath alle 0.6s (Boss = häufiger als Mob, da langsamer)
                e.path_age = getattr(e, 'path_age', 0.0) + dt
                if e.path is None or e.path_age > 0.6:
                    start = game.grid.world_to_cell(e.pos.x, e.pos.y)
                    end = game.grid.world_to_cell(p.pos.x, p.pos.y)
                    e.path = game.grid.astar(start, end, max_steps=600)
                    e.path_age = 0.0
                if e.path:
                    next_cell = e.path[0]
                    tx, ty = game.grid.cell_to_world_center(*next_cell)
                    ndx = tx - e.pos.x
                    ndy = ty - e.pos.y
                    ndist = math.hypot(ndx, ndy)
                    if ndist < 22:
                        e.path.pop(0)
                    elif ndist > 0:
                        nx, ny = ndx / ndist, ndy / ndist
                        old_x, old_y = e.pos.x, e.pos.y
                        game.move_entity(e, nx * speed * dt, ny * speed * dt)
                        # Stuck-Detection auch für Bosse
                        if (e.pos.x - old_x) ** 2 + (e.pos.y - old_y) ** 2 < 0.5:
                            e.stuck_timer = getattr(e, 'stuck_timer', 0.0) + dt
                            if e.stuck_timer > 0.4:
                                e.path = None
                                e.stuck_timer = 0.0
                        else:
                            e.stuck_timer = 0.0
                else:
                    # Kein Pfad gefunden → trotzdem in Richtung wackeln
                    n = diff.normalize()
                    game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
            else:
                n = diff.normalize()
                game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
        elif e.attack_timer <= 0:
            game.damage_player(e.dmg)
            e.attack_timer = e.att_cd
        return

    # Berserker: bei <30% HP rampage (Tempo + Damage)
    if e.type_key == 'berserker' and not getattr(e, '_berserker_rampage', False):
        if e.hp < e.hp_max * 0.3:
            e._berserker_rampage = True
            e.speed *= 2.0
            e.dmg *= 1.5
            e.att_cd *= 0.7
            game.floaters.append(Floater(e.pos.x, e.pos.y - e.radius - 4,
                                          'RAGE!', (255, 100, 30)))
            game.spawn_particles(e.pos.x, e.pos.y, 18, (255, 120, 40),
                                 life_max=0.6, size_max=5)

    # Hexenmeister: castet Buffs auf nahe Gegner + Schatten-Bolt
    if e.type_key == 'warlock':
        # Buff-Tick alle 5s
        if not hasattr(e, '_buff_cd'):
            e._buff_cd = 4.0
        e._buff_cd -= dt
        if e._buff_cd <= 0:
            e._buff_cd = 6.0
            buffed = 0
            for ally in game.enemies:
                if ally is e or ally.dying or ally.is_boss:
                    continue
                if (ally.pos - e.pos).length() < 220 and buffed < 3:
                    # +20% HP-Restore + visueller Effekt
                    ally.hp = min(ally.hp_max, ally.hp + ally.hp_max * 0.10)
                    ally.dmg *= 1.10
                    game.spawn_particles(ally.pos.x, ally.pos.y, 10,
                                         (200, 130, 240),
                                         life_max=0.4, size_max=3)
                    buffed += 1
            if buffed > 0:
                game.floaters.append(Floater(
                    e.pos.x, e.pos.y - 30, 'Verstärkung!', (200, 130, 240)))
        # AI verhält sich wie Ranged
        ideal = e.att_range * 0.7
        if d > e.att_range:
            n = diff.normalize()
            game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
        elif d < ideal * 0.6:
            n = diff.normalize()
            game.move_entity(e, -n.x * speed * 0.7 * dt, -n.y * speed * 0.7 * dt)
            if e.attack_timer <= 0:
                if d > 0:
                    dn = diff.normalize()
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y, dn.x * 280, dn.y * 280,
                        e.dmg, 'shadowbolt', friendly=False,
                        radius=8, life=1.8,
                    ))
                e.attack_timer = e.att_cd
        else:
            if e.attack_timer <= 0:
                if d > 0:
                    dn = diff.normalize()
                    game.projectiles.append(Projectile(
                        e.pos.x, e.pos.y, dn.x * 280, dn.y * 280,
                        e.dmg, 'shadowbolt', friendly=False,
                        radius=8, life=1.8,
                    ))
                e.attack_timer = e.att_cd
        return

    # Ranged: feuert aus Distanz (nur mit LOS)
    if e.ranged:
        ideal = e.att_range * 0.7
        # LOS-Check
        has_los = True
        if game.grid is not None:
            has_los = game.grid.has_los(e.pos.x, e.pos.y, p.pos.x, p.pos.y)
        if d > e.att_range or not has_los:
            # Bewege zum Spieler bis LOS + Reichweite OK
            n = diff.normalize()
            game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
        elif d < ideal * 0.6:
            n = diff.normalize()
            game.move_entity(e, -n.x * speed * 0.7 * dt, -n.y * speed * 0.7 * dt)
            if e.attack_timer <= 0 and has_los:
                _enemy_ranged_shot(game, e, diff)
                e.attack_timer = e.att_cd
        else:
            if e.attack_timer <= 0 and has_los:
                _enemy_ranged_shot(game, e, diff)
                e.attack_timer = e.att_cd
        return

    # Normal: Nahkampf mit Pathfinding wenn keine LOS
    if d > e.att_range:
        # Pathfinding wenn Wand zwischen Spieler und Gegner
        if game.grid is not None and not game.grid.has_los(
                e.pos.x, e.pos.y, p.pos.x, p.pos.y):
            # Repath alle 0.8s oder wenn kein Pfad existiert
            e.path_age += dt
            if e.path is None or e.path_age > 0.8:
                start = game.grid.world_to_cell(e.pos.x, e.pos.y)
                end = game.grid.world_to_cell(p.pos.x, p.pos.y)
                e.path = game.grid.astar(start, end, max_steps=400)
                e.path_age = 0.0
            # Folge dem Pfad
            if e.path:
                next_cell = e.path[0]
                tx, ty = game.grid.cell_to_world_center(*next_cell)
                ndx = tx - e.pos.x
                ndy = ty - e.pos.y
                ndist = math.hypot(ndx, ndy)
                if ndist < 18:
                    e.path.pop(0)
                elif ndist > 0:
                    nx, ny = ndx / ndist, ndy / ndist
                    old_x, old_y = e.pos.x, e.pos.y
                    game.move_entity(e, nx * speed * dt, ny * speed * dt)
                    # Stuck-Detection
                    if (e.pos.x - old_x) ** 2 + (e.pos.y - old_y) ** 2 < 0.5:
                        e.stuck_timer += dt
                        if e.stuck_timer > 0.4:
                            e.path = None  # Repath
                            e.stuck_timer = 0.0
                    else:
                        e.stuck_timer = 0.0
                return
        # Hat LOS oder kein Grid → direkter Anlauf
        n = diff.normalize()
        game.move_entity(e, n.x * speed * dt, n.y * speed * dt)
    elif e.attack_timer <= 0:
        # Update #40: 3-Phasen-Attack-Animation.
        # Update #43: Combos + erhöhte Aggression (User-Feedback „Gegner
        # wehren sich zu wenig sie sollen auch combos machen").
        # Special-Chance 18 → 28 %. Brutes/Berserker bekommen 40 %.
        if e.type_key in ('brute', 'berserker'):
            special_chance = 0.40
        else:
            special_chance = 0.28
        special = (not getattr(e, '_recently_special', False)
                    and random.random() < special_chance)
        if special:
            e._recently_special = True
            if _enemy_special_attack(game, e, diff):
                e.attack_timer = e.att_cd * 1.2
                return
        else:
            e._recently_special = False
        # Wind-up starten — Damage erst nach 0.25s
        e.atk_phase = 'windup'
        e.atk_phase_t = 0.0
        e.atk_target_pos = Vector2(game.player.pos.x, game.player.pos.y)
        # Combo-Chain: wenn dieser Hit nicht schon ein Combo-Follow-Up war,
        # gibt es 30 % (brute/berserker 50 %) Chance auf einen 2. Schlag
        # direkt nach Recover — günstigerer Cooldown, dafür weniger Damage.
        already_combo = getattr(e, '_combo_step', 0) > 0
        combo_roll = random.random()
        combo_chance = 0.50 if e.type_key in ('brute', 'berserker') else 0.30
        if not already_combo and combo_roll < combo_chance:
            e._combo_step = 1
            e._combo_max = random.choice([2, 2, 3])
        e.attack_timer = e.att_cd  # cooldown läuft schon


def tick_enemy_attack_animation(game, e, dt):
    """Update #40: 3-Phasen Attack-Animation.

    windup (0.25s): Wind-Up-Pose, Aura schwillt an, kein Schaden
    swing (0.10s):  Damage + Slash-Arc-VFX + Particles + Sound
    recover (0.15s): Cooldown, dann wieder idle
    Returnt True wenn enemy busy mit Animation (skip andere AI).
    """
    if e.atk_phase == 'idle':
        return False
    e.atk_phase_t += dt
    if e.atk_phase == 'windup':
        if e.atk_phase_t >= 0.25:
            # Switch to swing — Damage applizieren + VFX
            e.atk_phase = 'swing'
            e.atk_phase_t = 0.0
            _execute_attack_swing(game, e)
        return True
    if e.atk_phase == 'swing':
        if e.atk_phase_t >= 0.10:
            e.atk_phase = 'recover'
            e.atk_phase_t = 0.0
        return True
    if e.atk_phase == 'recover':
        if e.atk_phase_t >= 0.15:
            e.atk_phase = 'idle'
            e.atk_phase_t = 0.0
            # Update #43: Combo-Chain — wenn ein Combo aktiv ist, sofort
            # nächsten Schlag queuen (kein att_cd-Wait). Damage ×0.75 pro
            # Folge-Schlag, damit Combos nicht zur Damage-Spitze werden.
            step = getattr(e, '_combo_step', 0)
            cmax = getattr(e, '_combo_max', 0)
            if step > 0 and step < cmax:
                p = game.player
                d_now = (p.pos - e.pos).length()
                # Combo bricht ab wenn Spieler aus Range
                if d_now <= e.att_range + p.radius + 8:
                    e._combo_step = step + 1
                    e._combo_dmg_mult = 0.75
                    e.atk_phase = 'windup'
                    e.atk_phase_t = 0.0
                    e.atk_target_pos = Vector2(p.pos.x, p.pos.y)
                else:
                    e._combo_step = 0
                    e._combo_max = 0
                    e._combo_dmg_mult = 1.0
            else:
                e._combo_step = 0
                e._combo_max = 0
                e._combo_dmg_mult = 1.0
        return True
    return False


def _execute_attack_swing(game, e):
    """Wendet Damage an + spawnt VFX + Sound."""
    from . import sounds as _snd
    p = game.player
    # PLAN F-02 (Update #96): BRUTE-Slam-AoE — Brute/Berserker hat 25 %
    # Chance auf einen 90 px-Radius-Schlag statt Single-Target. Combo-
    # Folge-Hits sind Single-Target (sonst zu viel Damage).
    is_brute = e.type_key in ('brute', 'berserker')
    combo_active = getattr(e, '_combo_step', 0) > 0
    slam_aoe = (is_brute and not combo_active and random.random() < 0.25)
    if slam_aoe:
        slam_radius = 90
        d_slam = (p.pos - e.pos).length()
        if d_slam <= slam_radius + p.radius:
            # AoE-Hit + Pre-Telegraph-Toast (Lore: „Wuchtschlag")
            combo_mult = getattr(e, '_combo_dmg_mult', 1.0)
            pack_mult = getattr(e, '_dmg_mult', 1.0)
            dmg_dealt = e.dmg * combo_mult * pack_mult * 1.20
            game.damage_player(dmg_dealt)
            game.shake = max(game.shake, 12)
            # AoE-Ring-VFX
            for k in range(28):
                ang = (math.tau / 28) * k
                game.particles_push(
                    e.pos.x + math.cos(ang) * 24,
                    e.pos.y + math.sin(ang) * 24,
                    math.cos(ang) * 220, math.sin(ang) * 220,
                    (220, 100, 60), random.uniform(0.4, 0.7),
                    random.uniform(3, 5), gravity=80)
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - e.radius - 20,
                'SLAM-AOE', (255, 140, 60)))
            try:
                _snd.play_with_fallback('aoe_impact', 'hit_heavy',
                                          volume=0.55)
            except Exception:
                pass
            return  # Skip regular swing-path
    # Check ob Player noch in att_range — wenn weg, verfehlt
    d = (p.pos - e.pos).length()
    in_range = (d <= e.att_range + p.radius + 6)
    if in_range:
        # Update #43: Combo-Folge-Schläge bekommen ×0.75 Damage
        combo_mult = getattr(e, '_combo_dmg_mult', 1.0)
        # D-10 (Update #47): Pack-Reaction-Mod (fearful 0.7 / enraged 1.3)
        pack_mult = getattr(e, '_dmg_mult', 1.0)
        dmg_dealt = e.dmg * combo_mult * pack_mult
        game.damage_player(dmg_dealt)
        # Update #44: Wurzelhüter wurzelt Spieler bei Hit (Slow + Poison)
        if e.type_key == 'wurzelhueter':
            p.slow_timer = max(p.slow_timer, 1.5)
            p.slow_factor = min(p.slow_factor, 0.55)
            from . import effects as _fx
            _fx.apply(game, p, 'poison', stacks=2)
            game.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                          'WURZEL!', (120, 200, 80)))
        # F-15 (Update #45): Vampiric-Affix heilt Mob pro Player-Hit
        if 'vampiric' in getattr(e, 'affixes', ()):
            heal = dmg_dealt * 0.4
            e.hp = min(e.hp_max, e.hp + heal)
            game.spawn_particles(e.pos.x, e.pos.y - 10, 8, (220, 60, 60),
                                  life_max=0.4, size_max=3, friendly=False)
        # Hit-VFX am Spieler
        if hasattr(game, 'hit_vignette_t'):
            game.hit_vignette_t = max(game.hit_vignette_t, 0.25)
        # Impact-Partikel am Spieler-Position
        for _ in range(8):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(80, 180)
            game.particles_push(
                p.pos.x, p.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                (220, 60, 60), random.uniform(0.3, 0.5),
                random.uniform(2, 4), gravity=120)
        game.shake = max(game.shake, 4)
    # Slash-Arc-VFX (immer, auch wenn Verfehler — Spieler sieht Versuch)
    if e.atk_target_pos is not None:
        target = e.atk_target_pos
        dx = target.x - e.pos.x
        dy = target.y - e.pos.y
        d_t = math.hypot(dx, dy)
        if d_t > 0:
            ang = math.atan2(dy, dx)
            # Arc-Particles in 90° Bogen
            arc_r = e.radius + 18
            for k in range(8):
                a_off = -math.pi / 4 + (k / 7) * (math.pi / 2)
                a = ang + a_off
                px_ = e.pos.x + math.cos(a) * arc_r
                py_ = e.pos.y + math.sin(a) * arc_r
                game.particles_push(
                    px_, py_,
                    math.cos(a) * 100, math.sin(a) * 100,
                    (255, 200, 100), 0.3, 3)
    # Sound
    try:
        if e.type_key == 'slime':
            _snd.play_at('slime_attack', (e.pos.x, e.pos.y),
                          (p.pos.x, p.pos.y), volume=0.35)
        else:
            _snd.play_at('monster_bite', (e.pos.x, e.pos.y),
                          (p.pos.x, p.pos.y), volume=0.3)
    except Exception:
        pass
    # Push enemy slightly back (recoil)
    if e.atk_target_pos is not None:
        dx = e.atk_target_pos.x - e.pos.x
        dy = e.atk_target_pos.y - e.pos.y
        d_t = math.hypot(dx, dy)
        if d_t > 0:
            game.move_entity(e, -dx / d_t * 4, -dy / d_t * 4)


def _resolve_pending_special(game, e, ps):
    """Update #106 (Audit F-009): Feuert ein pending Special nach Wind-Up.

    Wird vom update_enemy_ai-Tick gerufen sobald `ps['timer'] <= 0`.
    Spawnt jetzt das Projectile/Damage; Pre-Telegraph-Phase ist vorbei.
    """
    kind = ps.get('kind')
    if kind == 'spit':
        dn = ps.get('dir')
        if dn is None:
            return
        game.projectiles.append(Projectile(
            e.pos.x, e.pos.y, dn.x * 200, dn.y * 200,
            e.dmg * 0.6, 'poisonbolt', friendly=False,
            radius=7, life=2.0,
        ))
        try:
            from . import sounds as _snd
            _snd.play_at('slime_attack', (e.pos.x, e.pos.y),
                          (game.player.pos.x, game.player.pos.y),
                          volume=0.55)
        except Exception:
            pass
    elif kind == 'bone_fan':
        ang = ps.get('ang', 0.0)
        for offset in (-0.18, 0.0, 0.18):
            a = ang + offset
            game.projectiles.append(Projectile(
                e.pos.x, e.pos.y,
                math.cos(a) * 280, math.sin(a) * 280,
                e.dmg * 0.7, 'shadowbolt', friendly=False,
                radius=6, life=1.5,
            ))
        try:
            from . import sounds as _snd
            _snd.play_at('hit', (e.pos.x, e.pos.y),
                          (game.player.pos.x, game.player.pos.y),
                          volume=0.45)
        except Exception:
            pass


def _enemy_special_attack(game, e, diff):
    """Spezial-Attacke je Mob-Typ. Returnt True wenn ausgeführt.

    Update #35: Bricht Combat-Monotonie. Pro Mob-Typ andere Mechanik:
    - zombie: Vergiftungs-Spuck (poison-Projektil)
    - skeleton: Knochenwurf (3-Bolt-Fan)
    - wraith: Schatten-Charge (kurzer Sprint + 1.5× dmg)
    - imp/demon: Feuer-Schlag (AoE-Brand 60px)
    - slime: Sprung-Splash (springt + Slow-Pool)
    N-04 (Update #51): Telegraph-Sound 1 Frame vorab — der Spieler hört
    den Special bevor der Damage greift (kurzes Audio-Cue 0.1–0.2 s vor
    der eigentlichen Wirkung).
    """
    from . import sounds as _snd
    p = game.player
    # N-04: pro Mob-Typ ein Telegraph-Sound (Spatial via play_at)
    TELEGRAPH = {
        'zombie':       ('monster_bite',  0.30),  # Spuck-Aufnahme
        'skeleton':     ('hit',           0.28),  # Knochen-Rattle
        'wraith':       ('roar',          0.25),  # spektraler Schrei
        'demon':        ('cast_fire',     0.32),  # Flammen-Atem
        'slime':        ('slime_attack',  0.30),  # Schleim-Sprung
        'brute':        ('roar',          0.40),  # Brute-Growl
        'berserker':    ('roar',          0.35),
        'aschenbrut':   ('cast_fire',     0.30),
        'glaslord':     ('cast_frost',    0.32),
        'salzgeist':    ('whisper',       0.28),
        'wurzelhueter': ('croak',         0.32),
    }
    tcue = TELEGRAPH.get(e.type_key)
    if tcue is not None:
        try:
            _snd.play_at(tcue[0], (e.pos.x, e.pos.y),
                          (p.pos.x, p.pos.y), volume=tcue[1])
        except Exception:
            pass
    if e.type_key == 'zombie':
        # Update #106 (Audit F-009): Poison-Spuck mit 0.35 s Wind-Up.
        # Queue pending action statt sofort feuern → Spieler hat Frames
        # zum Ausweichen.
        if diff.length() == 0:
            return False
        e._pending_special = {
            'kind': 'spit',
            'timer': 0.35,
            'dir': diff.normalize(),
        }
        game.floaters.append(Floater(e.pos.x, e.pos.y - 36,
                                       'SPUCKT!', (150, 220, 100)))
        try:
            _snd.play_at('slime_attack', (e.pos.x, e.pos.y),
                          (p.pos.x, p.pos.y), volume=0.4)
        except Exception:
            pass
        return True
    if e.type_key == 'skeleton':
        # Update #106: 3-Bolt-Knochen-Fan mit 0.40 s Wind-Up.
        if diff.length() == 0:
            return False
        e._pending_special = {
            'kind': 'bone_fan',
            'timer': 0.40,
            'ang': math.atan2(diff.y, diff.x),
        }
        game.floaters.append(Floater(e.pos.x, e.pos.y - 36,
                                       'KNOCHEN-FAN!', (220, 210, 180)))
        return True
    if e.type_key == 'wraith':
        # Schatten-Charge: kurzer Sprint + extra-Dmg-Schlag
        d = diff.length()
        if d <= 0:
            return False
        n = diff.normalize()
        game.move_entity(e, n.x * 60, n.y * 60)
        game.spawn_particles(e.pos.x, e.pos.y, 14, (160, 80, 240),
                              life_max=0.5, size_max=4)
        if d < 80:
            game.damage_player(e.dmg * 1.6, dmg_type='shadow', source=e)
        try:
            # Update #38: Volume runter
            _snd.play_at('monster_growl', (e.pos.x, e.pos.y),
                          (p.pos.x, p.pos.y), volume=0.2)
        except Exception:
            pass
        return True
    if e.type_key == 'demon':
        # Fire-AoE-Schlag in 60px
        d = diff.length()
        if d > 100:
            return False
        for k in range(8):
            ang = k * math.tau / 8
            game.particles_push(
                e.pos.x, e.pos.y,
                math.cos(ang) * 180, math.sin(ang) * 180,
                (255, 120, 40), 0.5, 4)
        if d <= 60:
            game.damage_player(e.dmg * 1.3, dmg_type='fire', source=e)
        game.shake = max(game.shake, 4)
        game.floaters.append(Floater(e.pos.x, e.pos.y - 36,
                                       'FLAMME!', (255, 130, 50)))
        return True
    if e.type_key == 'slime':
        # Sprung + Slow-Pool unter Player
        # Update #43-bugfix: heal_fields-Format war kaputt (x/y/r/t/dmg_target
        # statt pos/radius/time_left). Crashte beim ersten Tick.
        d = diff.length()
        if d > 200 or d <= 0:
            return False
        target_x = p.pos.x
        target_y = p.pos.y
        game.move_entity(e, target_x - e.pos.x,
                           target_y - e.pos.y)
        # Splash-Partikel + Direktschaden im Aufschlag-Bereich
        game.spawn_particles(target_x, target_y, 20,
                              (160, 220, 120),
                              life_max=0.6, size_max=5)
        if (p.pos - e.pos).length() < 50:
            game.damage_player(e.dmg * 0.5, dmg_type='poison', source=e)
            p.slow_timer = max(p.slow_timer, 1.0)
            p.slow_factor = min(p.slow_factor, 0.7)
        game.floaters.append(Floater(e.pos.x, e.pos.y - 36,
                                       'SPLASH!', (160, 220, 120)))
        return True
    return False


def _enemy_ranged_shot(game, e, diff):
    if diff.length_squared() == 0:
        return
    dn = diff.normalize()
    kind = 'arrow'
    speed = 360
    color = (240, 220, 150)
    if e.type_key == 'shaman':
        kind = 'poisonbolt'
        speed = 280
        color = (160, 240, 120)
    game.projectiles.append(Projectile(
        e.pos.x, e.pos.y, dn.x * speed, dn.y * speed,
        e.dmg, kind, friendly=False, radius=7, life=1.6,
        extra={'color': color},
    ))


def separation(enemies, game=None):
    """Sanfte Abstoßung zwischen Gegnern, respektiert Wände."""
    for e in enemies:
        for o in enemies:
            if o is e:
                continue
            ddiff = e.pos - o.pos
            od = ddiff.length()
            min_d = e.radius + o.radius
            if 0 < od < min_d:
                push = ddiff.normalize() * (min_d - od) * 0.5
                if game is not None:
                    game.move_entity(e, push.x, push.y)
                else:
                    e.pos += push


# ============================================================
# WELLEN-SPAWN-POOL
# ============================================================
def spawn_pool(biome, wave):
    """Welche Gegner können in dieser Welle/Biom auftauchen?"""
    pool = ['zombie', 'zombie']
    if wave >= 2:
        pool += ['skeleton', 'skeleton']
    if wave >= 3:
        pool += ['wraith']
    if wave >= 4:
        pool += ['demon']
    if wave >= 5:
        pool += ['archer']
    if wave >= 6:
        pool += ['berserker']
    if wave >= 6 and random.random() < 0.15:
        pool += ['brute']
    if wave >= 7:
        pool += ['shaman', 'warlock']
    if wave >= 8:
        pool += ['lurker']
    if wave >= 5:
        pool += ['slime']
    # Update #44: neue Mobs nach Biome im späteren Wave-Verlauf
    if biome == 'crypt' and wave >= 3:
        pool += ['salzgeist']
    if biome == 'frost' and wave >= 4:
        pool += ['glaslord']
    if biome == 'lava' and wave >= 4:
        pool += ['aschenbrut', 'aschenbrut']
    if biome == 'swamp' and wave >= 3:
        pool += ['wurzelhueter']

    # Biom-Gewichte
    if biome == 'frost':
        pool += ['wraith', 'wraith', 'skeleton']
    elif biome == 'lava':
        pool += ['demon', 'demon', 'brute', 'berserker']
    elif biome == 'crypt':
        pool += ['skeleton', 'zombie', 'warlock', 'lurker']
    elif biome == 'desert':
        pool += ['archer', 'archer', 'berserker']
    elif biome == 'swamp':
        pool += ['warlock', 'wraith', 'shaman', 'slime', 'slime']
    elif biome == 'astral':
        pool += ['wraith', 'lurker', 'warlock', 'shaman']
    return pool
