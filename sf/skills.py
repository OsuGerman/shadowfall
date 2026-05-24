"""Skill-Definitionen und Casting-Logik mit Rune-Modifikatoren."""

import math
import random
import pygame
from pygame.math import Vector2

from .constants import FIRE, FROST
from .entities import Projectile, LightningBolt, Floater
from . import progression
from . import effects as fx
from . import sounds as snd


# PLAN O-08 + O-05 (Update #98/#101): Frame-Data-Definition pro Skill.
# Vier Phasen (O-05 Anticipation→Action→Recovery→Settle):
#   anticipation (alias startup) — Wind-Up, kein Cancel via Dodge
#   action       (alias active)   — Damage-Frame, kein Cancel
#   recovery                       — Cooldown-Tail, Cancel via Dodge möglich
#   settle                         — Pose-Reset zu Idle (Polish)
# Werte in Sekunden.
FRAME_DATA = {
    'fireball':   dict(startup=0.10, active=0.05, recovery=0.20, settle=0.10),
    'lightning':  dict(startup=0.08, active=0.05, recovery=0.25, settle=0.10),
    'heal':       dict(startup=0.15, active=0.10, recovery=0.30, settle=0.10),
    'frostnova':  dict(startup=0.18, active=0.15, recovery=0.35, settle=0.12),
    'earthquake': dict(startup=0.25, active=0.20, recovery=0.40, settle=0.15),
    'spark':      dict(startup=0.05, active=0.05, recovery=0.15, settle=0.08),
    'bone_spear': dict(startup=0.10, active=0.06, recovery=0.20, settle=0.08),
    'ice_nova':   dict(startup=0.15, active=0.18, recovery=0.30, settle=0.12),
    'comet':      dict(startup=0.40, active=0.25, recovery=0.45, settle=0.18),
    'melee':      dict(startup=0.08, active=0.05, recovery=0.15, settle=0.06),
    # Update #107 — Klassen-Skill-Frame-Data
    'frost_arrow':       dict(startup=0.10, active=0.05, recovery=0.18, settle=0.08),
    'burning_arrow':     dict(startup=0.10, active=0.05, recovery=0.18, settle=0.08),
    'permafrost_bolts':  dict(startup=0.08, active=0.05, recovery=0.15, settle=0.06),
    'plasma_blast':      dict(startup=0.22, active=0.10, recovery=0.30, settle=0.12),
    'tempest_bell':      dict(startup=0.20, active=0.20, recovery=0.30, settle=0.12),
    'glacial_cascade':   dict(startup=0.18, active=0.18, recovery=0.30, settle=0.10),
    # Update #108 — Warrior/Witch/Huntress/Druid Frame-Data
    'leap_slam':         dict(startup=0.20, active=0.18, recovery=0.40, settle=0.12),
    'molten_blast':      dict(startup=0.18, active=0.08, recovery=0.25, settle=0.10),
    'essence_drain':     dict(startup=0.10, active=0.05, recovery=0.20, settle=0.08),
    'contagion':         dict(startup=0.20, active=0.15, recovery=0.30, settle=0.10),
    'whirling_slash':    dict(startup=0.08, active=0.30, recovery=0.20, settle=0.08),
    'spear_throw':       dict(startup=0.10, active=0.05, recovery=0.18, settle=0.06),
    'spore_burst':       dict(startup=0.15, active=0.18, recovery=0.25, settle=0.10),
    'hailstorm':         dict(startup=0.22, active=0.30, recovery=0.30, settle=0.12),
}

# PLAN O-10 (Update #101): Skill-Animation-Hooks.
# Pro Skill: welche Particle-Hooks bei welcher Phase feuern.
# Engine ruft `trigger_anim_hook(skill_id, phase, game, pos)` auf.
SKILL_ANIM_HOOKS = {
    'earthquake': dict(
        startup_hook='slam_foot_plant_dust',   # Foot-Plant beim Wind-Up
        action_hook='aoe_burst',               # Slam-Impact
        recovery_hook='settle_dust',
    ),
    'fireball': dict(
        startup_hook='cast_charge',            # Glut-Sammelt-Ring
        action_hook='cast_release',
    ),
    'frostnova': dict(
        startup_hook='cast_charge',
        action_hook='nova_burst',
    ),
    'bone_spear': dict(
        startup_hook='cast_charge',
        action_hook='projectile_release',
    ),
    'comet': dict(
        startup_hook='cast_channel',           # Multi-Hit-Channel
        action_hook='aoe_burst',
    ),
}


def trigger_anim_hook(skill_id, phase, game, pos=None):
    """PLAN O-10 (Update #101): Spawnt klassen-spezifische Particle-Hook
    für den aktuellen Skill-Phase-Übergang.  Best-Effort, fail-silent.

    Update #106: nutzt jetzt module-level `math`/`random` (vorher
    `__import__('math')` Anti-Pattern in Hot-Loop).
    """
    hooks = SKILL_ANIM_HOOKS.get(skill_id)
    if hooks is None:
        return
    key = hooks.get(f'{phase}_hook')
    if key is None:
        return
    p = pos or (game.player.pos.x, game.player.pos.y)
    try:
        if key == 'slam_foot_plant_dust':
            for k in range(8):
                ang = (k / 8.0) * math.tau
                game.particles_push(
                    p[0], p[1],
                    math.cos(ang) * 60,
                    math.sin(ang) * 60,
                    (180, 150, 100), 0.4, 3, gravity=40)
        elif key == 'cast_charge':
            for k in range(6):
                game.particles_push(
                    p[0] + random.uniform(-10, 10),
                    p[1] + random.uniform(-10, 10),
                    random.uniform(-20, 20),
                    random.uniform(-60, -20),
                    (220, 180, 100), 0.35, 2, gravity=-40)
        elif key == 'nova_burst' or key == 'aoe_burst':
            for k in range(20):
                ang = (k / 20.0) * math.tau
                sp = 180
                game.particles_push(
                    p[0], p[1],
                    math.cos(ang) * sp,
                    math.sin(ang) * sp,
                    (200, 230, 255), 0.5, 3, gravity=0)
        elif key == 'settle_dust':
            for k in range(4):
                game.particles_push(
                    p[0] + random.uniform(-12, 12),
                    p[1] + 4,
                    random.uniform(-15, 15), 5,
                    (180, 160, 120), 0.3, 2, gravity=20)
    except Exception:
        pass


def skill_can_cancel(skill_id, phase_t):
    """O-08: True wenn der Skill im aktuellen `phase_t` (Sekunden seit
    Cast-Start) via Dodge gecancelt werden kann. Nur die `recovery`-
    Phase ist cancelbar."""
    fd = FRAME_DATA.get(skill_id)
    if fd is None:
        return True  # Unknown skill → assume cancelable
    startup = fd['startup']
    active = fd['active']
    if phase_t < startup + active:
        return False  # Wind-up / Active locked
    return True


def attack_speed_scale(player, skill_id):
    """PLAN O-09 (Update #100): Attack-Speed-Scaling.

    Liefert einen Time-Scale-Multiplikator für die Skill-Phasen + Audio-
    Pitch-Koppelung. Quellen:
      - Player-Speed-Stat (item_stats.speed / 100)
      - Frenzy-Charges (3 Stacks × 5 % = 15 %)
      - Combo-Buff (×1.15 wenn aktiv)

    Returnt 1.0 als Default. >1.0 = schneller (Phasen kürzer).
    """
    scale = 1.0
    try:
        from . import progression as _p
        eff = _p.effective(player)
        # Speed-Stat in % → 0.5 % je Punkt auf Attack-Speed
        scale += (eff.get('speed', 100) - 100) / 100.0 * 0.5
    except Exception:
        pass
    # Frenzy-Charges (PLAN G-06)
    fc = getattr(player, 'frenzy_charges', 0)
    if fc > 0:
        scale += fc * 0.05
    # Combo-Buff
    if getattr(player, 'combo_buff_left', 0) > 0:
        scale *= 1.15
    return max(0.5, min(2.5, scale))


SKILL_INFO = {
    # ---- Original 4 ----
    'fireball': dict(
        name='Feuerball', key='Q', mana=15, cd=0.5,
        desc='Wirft eine explodierende Flammenkugel.', icon='fire',
        tags=['Spell', 'Projectile', 'Fire', 'AoE'],
    ),
    'lightning': dict(
        name='Kettenblitz', key='W', mana=25, cd=0.8,
        desc='Blitz springt zu bis zu 3 Gegnern.', icon='bolt',
        tags=['Spell', 'Chaining', 'Lightning'],
    ),
    'heal': dict(
        name='Heilung', key='E', mana=30, cd=2.5,
        desc='Stellt 35% der maximalen Lebenspunkte wieder her.', icon='cross',
        tags=['Spell', 'Buff'],
    ),
    'frostnova': dict(
        name='Frostnova', key='R', mana=35, cd=4.0,
        desc='AoE um den Spieler, verlangsamt Gegner stark.', icon='frost',
        tags=['Spell', 'AoE', 'Nova', 'Cold'],
    ),
    # ---- Neue POE2-inspirierte Skills ----
    'earthquake': dict(
        name='Erdbeben', key='1', mana=40, cd=3.0,
        desc='Slam mit Aftershock-AoE nach 1.2s.', icon='quake',
        tags=['Spell', 'AoE', 'Slam', 'Physical', 'Payoff'],
    ),
    'spark': dict(
        name='Funke', key='2', mana=12, cd=0.4,
        desc='Lightning-Projektil das von Waenden abprallt.', icon='spark',
        tags=['Spell', 'Projectile', 'Lightning'],
    ),
    'bone_spear': dict(
        name='Knochenspeer', key='3', mana=20, cd=0.6,
        desc='Hartes physisches Projektil, hohes Single-Target.', icon='spear',
        tags=['Spell', 'Projectile', 'Physical'],
    ),
    'ice_nova': dict(
        name='Eis-Nova', key='4', mana=30, cd=2.5,
        desc='Cold-Nova um Spieler. Detoniert Frost-Stacks (Shatter).',
        icon='nova',
        tags=['Spell', 'AoE', 'Nova', 'Cold', 'Payoff'],
    ),
    'comet': dict(
        name='Komet', key='5', mana=55, cd=6.0,
        desc='Riesiger Cold-Asteroid faellt vom Himmel mit Verzoegerung.',
        icon='comet',
        tags=['Spell', 'AoE', 'Slam', 'Cold'],
    ),
    # ============================================================
    # KLASSEN-SIGNATURE-SKILLS (Update #23 — pro Klasse einzigartig)
    # Lore-Quelle: K-01..K-08 in class_skills.py + Lore-Bibel Teil 7.
    # ============================================================
    'boneshatter': dict(
        name='Boneshatter', key='Q', mana=12, cd=0.5,
        desc='Krieger-Cone-Strike — Phys-Damage in Halbkreis, Stun-Buildup, Knockback.',
        icon='spear', tags=['Attack', 'Melee', 'Physical', 'AoE', 'Stun'],
    ),
    'killing_palm': dict(
        name='Killing Palm', key='Q', mana=15, cd=0.6,
        desc='Mönch-Punch — Phys-Strike, Execute-Bonus auf <30 % HP-Ziele.',
        icon='spear', tags=['Attack', 'Melee', 'Physical', 'Execute'],
    ),
    'detonate_dead': dict(
        name='Detonate Dead', key='W', mana=22, cd=1.2,
        desc='Hexe-AoE — explodiert nächste Leichen-Spur in Chaos-Schaden.',
        icon='nova', tags=['Spell', 'AoE', 'Chaos', 'Trigger'],
    ),
    'lightning_arrow': dict(
        name='Lightning Arrow', key='Q', mana=12, cd=0.4,
        desc='Jägerin-Pfeil — Lightning-Projektil, kettet bei Impact zu 3 Zielen.',
        icon='bolt', tags=['Attack', 'Projectile', 'Lightning', 'Bow', 'Chaining'],
    ),
    'galvanic_shot': dict(
        name='Galvanic Shot', key='Q', mana=14, cd=0.5,
        desc='Söldner-Crossbow — Lightning-Bolt mit 3 Funken-Splash bei Impact.',
        icon='bolt', tags=['Attack', 'Projectile', 'Lightning', 'Crossbow', 'AoE'],
    ),
    'lightning_spear': dict(
        name='Lightning Spear', key='Q', mana=16, cd=0.45,
        desc='Speerschwester-Wurf — Phys+Lightning, durchschlägt 3 Ziele.',
        icon='spear', tags=['Attack', 'Projectile', 'Lightning', 'Spear', 'Pierce'],
    ),
    'storm_call': dict(
        name='Storm Call', key='Q', mana=22, cd=1.5,
        desc='Wandelnde-Sky-Lightning — markiert Boden, schlägt nach 1.2 s ein.',
        icon='bolt', tags=['Spell', 'AoE', 'Lightning', 'Delayed', 'Payoff'],
    ),
    # ============================================================
    # Update #107 — Klassen-Skill-Cast-Erweiterung (K-02/K-05/K-06)
    # Lore-Anker: Velgrad-Klassen × Aspekt-Lineage (Lore-Bibel Teil 7).
    # ============================================================
    'frost_arrow': dict(
        name='Frostpfeil', key='W', mana=10, cd=0.0,
        desc='Saatträgerin-Pfeil — Nheyras Atem im Schacht. Cold-Bolt, '
             'Frost-Stacks bei Treffer.',
        icon='bolt', tags=['Attack', 'Projectile', 'Cold', 'Bow'],
    ),
    'burning_arrow': dict(
        name='Brennpfeil', key='E', mana=10, cd=0.0,
        desc='Saatträgerin-Pfeil — Valsas Asche im Köcher. Fire-Bolt, '
             'hohe Ignite-Chance.',
        icon='bolt', tags=['Attack', 'Projectile', 'Fire', 'Bow', 'DoT'],
    ),
    'permafrost_bolts': dict(
        name='Frost-Bolzen', key='W', mana=10, cd=0.0,
        desc='Mahnmal-Söldner — Salzhüter-Bolzen, +Frost-Slow pro Treffer.',
        icon='bolt', tags=['Attack', 'Projectile', 'Cold', 'Crossbow'],
    ),
    'plasma_blast': dict(
        name='Plasma-Salve', key='E', mana=22, cd=1.8,
        desc='Mahnmal-Söldner — geladener Plasma-Schuss, AoE bei Aufprall, '
             '×2 Schaden gegen Geschockte.',
        icon='nova', tags=['Attack', 'Projectile', 'Lightning', 'AoE',
                            'Crossbow', 'Payoff'],
    ),
    'tempest_bell': dict(
        name='Sturmglocke', key='W', mana=18, cd=2.0,
        desc='Stille-Schritte-Glocke — beschwört pulsierende Lightning-Nova '
             '(3 Pulse über 1.2 s). Im-Nesh-Echo.',
        icon='spark', tags=['Spell', 'AoE', 'Lightning', 'Nova', 'Duration'],
    ),
    'glacial_cascade': dict(
        name='Eiskaskade', key='E', mana=22, cd=2.0,
        desc='Stille-Schritte-Spell — Eis-Spike-Reihe vor dem Mönch, '
             '5 Stufen × Cold-AoE.',
        icon='nova', tags=['Spell', 'AoE', 'Cold', 'Projectile-Pattern'],
    ),
    # ============================================================
    # Update #108 — Warrior / Witch / Huntress / Druid Erweiterung
    # PLAN K-01 / K-04 / K-07 / K-08
    # ============================================================
    'leap_slam': dict(
        name='Sprungschlag', key='R', mana=20, cd=4.5,
        desc='Krieger-Mobility — Eisenwächter springt zu Mauszeiger, '
             'Phys-AoE bei Landung (Kharns Sprung).',
        icon='quake', tags=['Attack', 'AoE', 'Slam', 'Travel', 'Physical'],
    ),
    'molten_blast': dict(
        name='Glutschlag', key='1', mana=18, cd=1.4,
        desc='Krieger-Fire-Projektil — Brennende Stein-Kugel mit '
             'AoE-Explosion bei Impact (Valsa-Volcanic-Echo).',
        icon='fire', tags=['Attack', 'Projectile', 'AoE', 'Fire'],
    ),
    'essence_drain': dict(
        name='Essenzraub', key='E', mana=18, cd=0.5,
        desc='Hexen-Chaos-Projektil — Vossharil-Wunde, Chaos-DoT, '
             'heilt 15 % des Schadens als HP an Casterin.',
        icon='nova', tags=['Spell', 'Projectile', 'Chaos', 'DoT', 'Heal'],
    ),
    'contagion': dict(
        name='Ansteckung', key='R', mana=22, cd=1.8,
        desc='Hexen-Chaos-AoE — Shulavh-Faden, Poison-Stack auf alle '
             'Ziele in 110 px Radius.',
        icon='nova', tags=['Spell', 'AoE', 'Chaos', 'DoT'],
    ),
    'whirling_slash': dict(
        name='Wirbelschlag', key='W', mana=14, cd=0.0,
        desc='Speerschwester-Wirbel — Phys-AoE 90 px um Spielerin, '
             '3 Hits über 0.6 s (Zhar-Eth-Wind-Choreographie).',
        icon='nova', tags=['Attack', 'Melee', 'AoE', 'Channeling', 'Spear'],
    ),
    'spear_throw': dict(
        name='Speerwurf', key='1', mana=10, cd=0.0,
        desc='Speerschwester-Wurf — Phys-Speer, durchschlägt 2 Ziele '
             'bei vollem Schaden.',
        icon='spear', tags=['Attack', 'Projectile', 'Physical', 'Spear',
                            'Pierce'],
    ),
    'spore_burst': dict(
        name='Sporen-Nova', key='W', mana=16, cd=2.0,
        desc='Wandelnde-Chaos-Nova um Spieler (100 px), '
             '2 Poison-Stacks (Saatträgerinnen-Sporen-Lineage).',
        icon='nova', tags=['Spell', 'AoE', 'Nova', 'Chaos', 'Poison'],
    ),
    'hailstorm': dict(
        name='Hagelsturm', key='1', mana=24, cd=3.5,
        desc='Wandelnde-Cold-AoE — Hagel an Maus-Position (140 px), '
             '3 Frost-Stacks + Slow (Nheyra-Hagel).',
        icon='nova', tags=['Spell', 'AoE', 'Cold', 'Duration', 'Slow'],
    ),
    # Universal-Skills (immer verfügbar, separate CD-Felder in Player)
    'ultimate': dict(
        name='Klassen-Ultimate', key='X', mana=0, cd=60.0,
        desc='Klassen-spezifischer Mega-Skill: Wirbel/Meteor/Schatten-Klon.',
        icon='ult',
        tags=['Ultimate', 'AoE', 'Class'],
    ),
    'time_freeze': dict(
        name='Zeitstillstand', key='Y', mana=0, cd=35.0,
        desc='Friert alle Gegner für 4s ein. Nheyra-Lineage.',
        icon='time',
        tags=['Spell', 'CC', 'Time', 'Nova'],
    ),
    'teleport': dict(
        name='Blink', key='B', mana=0, cd=8.0,
        desc='Kurz-Teleport in Maus-Richtung (max 220).',
        icon='blink',
        tags=['Mobility', 'Travel'],
    ),
}


def _has_mana(p, cost):
    return p.mp >= cost


def _on_cooldown(p, skill):
    return p.skill_cd.get(skill, 0.0) > 0


def _apply_cd(p, skill, base_cd, cdr):
    p.skill_cd[skill] = max(0.1, base_cd * (1.0 - cdr))
    # Update #165: Animation-Trigger 'cast' bei Skill-Use.
    # Wird hier zentral getriggert weil _apply_cd von ALLEN cast-Pfaden
    # aufgerufen wird (fireball, lightning, heal, frostnova).
    try:
        p.anim_state.trigger('cast')
    except AttributeError:
        pass


def _crit_roll(eff):
    if random.random() < eff['crit_chance']:
        return eff['crit_mult'], True
    return 1.0, False


def _spend_mana(p, info, eff):
    """Verbrauche Mana. Free-cast-Chance kann das umgehen."""
    if eff.get('free_cast', 0) > 0 and random.random() < eff['free_cast']:
        return True  # gratis
    p.mp -= info['mana']
    return False


# ============================================================
# FIREBALL
# ============================================================
def cast_fireball(game):
    p = game.player
    info = SKILL_INFO['fireball']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'fireball'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'fireball', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'fireball')

    rune = p.runes.get('fireball')
    base_speed = 520
    radius = 9
    dmg_mult = 1.8
    aoe = 60
    extra = {'dmg_type': 'fire'}

    if rune == 'fb_giant':
        dmg_mult = 2.5
        radius = 14
        aoe = 100
        base_speed = 380
    elif rune == 'fb_split':
        extra['split'] = True
    elif rune == 'fb_burn':
        extra['burn'] = True
    elif rune == 'fb_volley':
        angles = [-0.35, 0, 0.35]
        for a in angles:
            cos_a, sin_a = math.cos(a), math.sin(a)
            dx = direction.x * cos_a - direction.y * sin_a
            dy = direction.x * sin_a + direction.y * cos_a
            mult, crit = _crit_roll(eff)
            dmg = eff['damage'] * 1.2 * eff['fire_dmg'] * mult * skill_mult
            game.projectiles.append(Projectile(
                p.pos.x + dx * p.radius,
                p.pos.y + dy * p.radius,
                dx * base_speed, dy * base_speed,
                dmg, 'fireball',
                radius=8,
                extra={'crit': crit, 'aoe': 50, 'volley': True, 'dmg_type': 'fire'},
            ))
        game.spawn_particles(p.pos.x, p.pos.y, 10, FIRE)
        return

    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * dmg_mult * eff['fire_dmg'] * mult * skill_mult
    extra['crit'] = crit
    extra['aoe'] = aoe
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * base_speed, direction.y * base_speed,
        dmg, 'fireball',
        radius=radius,
        extra=extra,
    ))
    # M-01/M-02 (Update #68): Wind-Up-VFX am Caster (Element-Recipe).
    from . import effects as _fx
    _fx.play_skill_vfx_phase(game, p.pos.x, p.pos.y, 'fire', phase='windup')
    # N-02 + N-01 (Update #65/#67): Phased Fire-Signature (Whoom sofort,
    # Crackle nach 0.15s, Sizzle/Impact nach 0.45s).
    snd.play_skill_sequence('fire')


# ============================================================
# LIGHTNING
# ============================================================
def cast_lightning(game):
    p = game.player
    info = SKILL_INFO['lightning']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'lightning'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    rune = p.runes.get('lightning')

    max_targets = 3
    dmg_mult = 1.4
    first_bonus = 1.0
    apply_shock_stacks = 0
    cause_stun = False
    if rune == 'lt_chains':
        max_targets = 6
    elif rune == 'lt_shock':
        apply_shock_stacks = 2
    elif rune == 'lt_arc':
        first_bonus = 1.6
    elif rune == 'lt_thunder':
        cause_stun = True

    # LOS-Filter: nur Gegner mit Sichtlinie
    candidates = []
    for e in game.enemies:
        dist = (e.pos - wpos).length()
        if dist >= 260 or e.dying:
            continue
        if game.grid is not None and not game.grid.has_los(
                p.pos.x, p.pos.y, e.pos.x, e.pos.y):
            continue
        candidates.append((e, dist))
    candidates.sort(key=lambda t: t[1])
    targets = [c[0] for c in candidates][:max_targets]
    if not targets:
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'lightning', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'lightning')
    # M-06 (Update #66): Rain-Bonus für Lightning-Skills. +30 % bei voller
    # Intensity, skaliert linear mit `game.rain_intensity` (0..1).
    rain_bonus = 1.0 + 0.30 * getattr(game, 'rain_intensity', 0.0)
    prev = p.pos
    for i, e in enumerate(targets):
        mult, crit = _crit_roll(eff)
        bonus = first_bonus if i == 0 else 1.0
        dmg = (eff['damage'] * dmg_mult * bonus * eff['lit_dmg']
                * mult * skill_mult * rain_bonus)
        game.bolts.append(LightningBolt(prev.x, prev.y, e.pos.x, e.pos.y))
        game.hit_enemy(e, dmg, crit=crit, dmg_type='lightning')
        if apply_shock_stacks and e in game.enemies:
            fx.apply(game, e, 'shock', stacks=apply_shock_stacks)
        if cause_stun and e in game.enemies:
            e.stun_timer = max(getattr(e, 'stun_timer', 0), 0.6)
        prev = Vector2(e.pos)
    game.shake = max(game.shake, 5 if not cause_stun else 9)
    # M-01/M-02: Wind-Up-VFX am Caster
    from . import effects as _fx
    _fx.play_skill_vfx_phase(game, p.pos.x, p.pos.y, 'lightning',
                               phase='windup')
    # N-02 + N-01: Phased Lightning-Signature (Cracker sofort, Tesla nach
    # 0.10 s, Thunder-Hum nach 0.35 s).
    snd.play_skill_sequence('lightning', body_delay=0.10, impact_delay=0.35)


# ============================================================
# HEAL
# ============================================================
def cast_heal(game):
    p = game.player
    info = SKILL_INFO['heal']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'heal'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'heal', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'heal')

    rune = p.runes.get('heal')
    # Update #43: Heal-Balance — User-Feedback „Manche Skills healen einen
    # mehr als man Schaden nimmt". Cap auf 25 % HP_max + Skill-Mult max 1.5×.
    capped_mult = min(skill_mult, 1.5)
    base_heal = eff['hp_max'] * 0.25 * capped_mult
    if rune == 'hl_shield':
        amt = eff['hp_max'] * 0.6 * skill_mult
        p.shield = max(p.shield, amt)
        game.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                     f'⛨ {int(amt)}', (160, 200, 255)))
        game.spawn_particles(p.pos.x, p.pos.y, 30, (160, 200, 255))
        return
    if rune == 'hl_vampire':
        p.vampire_charges = 4
        game.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                     'Blutbund × 4', (220, 80, 80)))
        game.spawn_particles(p.pos.x, p.pos.y, 30, (220, 80, 80))
        return
    if rune == 'hl_regen':
        total = base_heal * 1.4
        p.regen_buff = total / 4.0
        p.regen_buff_left = 4.0
        game.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                     f'Anhaltend +{int(total)}', (170, 255, 170)))
        return

    p.hp = min(eff['hp_max'], p.hp + base_heal)
    game.spawn_particles(p.pos.x, p.pos.y, 30, (170, 255, 170))
    game.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                 f'+{int(base_heal)}', (170, 255, 170)))
    snd.play('cast_heal')
    # Heal-Field: 3s persistent zone am Spieler-Standort
    # Update #43: heal_per_sec 4 % → 2 %, time_left 4 → 3 s (Balance-Nerf)
    if hasattr(game, 'heal_fields'):
        game.heal_fields.append({
            'pos': Vector2(p.pos.x, p.pos.y),
            'radius': 80,
            'time_left': 3.0,
            'heal_per_sec': eff['hp_max'] * 0.02,
        })

    if rune == 'hl_nova':
        radius = 130
        for e in list(game.enemies):
            if (e.pos - p.pos).length() <= radius:
                game.hit_enemy(e, eff['damage'] * 1.5 * skill_mult, dmg_type='physical')
        for i in range(40):
            a = (i / 40) * math.tau
            game.particles_push(p.pos.x + math.cos(a) * 20,
                                p.pos.y + math.sin(a) * 20,
                                math.cos(a) * 240, math.sin(a) * 240,
                                (220, 240, 200), 0.6, 4)
        game.shake = max(game.shake, 6)


# ============================================================
# FROSTNOVA
# ============================================================
def cast_frostnova(game):
    p = game.player
    info = SKILL_INFO['frostnova']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'frostnova'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'frostnova', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'frostnova')

    rune = p.runes.get('frostnova')
    radius = 140
    dmg_mult = 1.1
    apply_frost = False
    if rune == 'fn_wide':
        radius = 220
    elif rune == 'fn_shatter':
        dmg_mult = 1.9
    elif rune == 'fn_frost':
        apply_frost = True

    for e in list(game.enemies):
        d = (e.pos - p.pos).length()
        if d > radius or e.dying:
            continue
        # LOS-Filter (kein Frost durch Wände)
        if game.grid is not None and not game.grid.has_los(
                p.pos.x, p.pos.y, e.pos.x, e.pos.y):
            continue
        mult, crit = _crit_roll(eff)
        dmg = eff['damage'] * dmg_mult * eff['cold_dmg'] * mult * skill_mult
        game.hit_enemy(e, dmg, crit=crit, dmg_type='cold')
        if apply_frost and e in game.enemies:
            fx.apply(game, e, 'frost', stacks=3)
        elif e in game.enemies:
            e.slow_timer = 3.0
            e.slow_factor = 0.4

    for i in range(48):
        a = (i / 48) * math.tau
        game.particles_push(p.pos.x + math.cos(a) * radius * 0.3,
                            p.pos.y + math.sin(a) * radius * 0.3,
                            math.cos(a) * 240, math.sin(a) * 240,
                            FROST, 0.6, 4)
    game.shake = max(game.shake, 4)
    # M-01/M-02: Wind-Up-VFX am Caster (Cold-Recipe)
    from . import effects as _fx
    _fx.play_skill_vfx_phase(game, p.pos.x, p.pos.y, 'cold', phase='windup')
    # N-02 + N-01: Phased Cold-Signature (Glass-Crack sofort, Chime nach
    # 0.20 s, Wind-Whisper-Tail nach 0.50 s)
    snd.play_skill_sequence('cold', body_delay=0.20, impact_delay=0.50)


def dodge_roll(game):
    """Update #34: Dodge-Roll mit Charges + i-Frames + Trail.

    - 2 Charges Default (regen 4s pro Charge bei 0 Charges)
    - 0.35s i-Frame-Window (Player ist invuln + Sprite-Flicker)
    - Visual: Aspekt-getönte Boden-Pulse + Geist-Klone-Trail
    """
    p = game.player
    if p.dodge > 0:
        return
    # Charge-System
    charges = getattr(p, 'dodge_charges', 0)
    if charges <= 0:
        # Kein Charge → Fallback auf alten CD (für Skill-Compatibility)
        if p.dodge_cd > 0:
            return
    from .constants import SCREEN_W, SCREEN_H
    mx, my = pygame.mouse.get_pos()
    dx, dy = mx - SCREEN_W / 2, my - SCREEN_H / 2
    length = math.hypot(dx, dy)
    if length == 0:
        return
    eff = progression.effective(p)
    p.dodge_dir = Vector2(dx / length, dy / length)
    p.dodge = 0.30  # längere Dodge-Animation
    # i-Frames: 0.35s — komplette Dodge-Dauer + leichter Buffer
    p.invuln = max(p.invuln, 0.35)
    # Charge verbrauchen wenn vorhanden
    if charges > 0:
        p.dodge_charges = charges - 1
        # Start Regen-Timer wenn alle weg
        if p.dodge_charges < getattr(p, 'dodge_charges_max', 2):
            p.dodge_regen_t = max(getattr(p, 'dodge_regen_t', 0.0), 4.0)
    else:
        p.dodge_cd = 1.0 * (1.0 - eff['dodge_cdr'])
    snd.play('dodge')
    # Trail-Spawn: ein Geist-Klon-Marker am Start-Pos
    if not hasattr(p, '_dodge_trail'):
        p._dodge_trail = []
    p._dodge_trail.append({
        'x': p.pos.x, 'y': p.pos.y, 'age': 0.0, 'life': 0.4,
    })
    # V-07 (Update #168): Dust-Puff am Dodge-Start.
    try:
        surf_fx = getattr(game, 'surface_fx', None)
        if surf_fx is not None:
            surf_fx.spawn_dust_puff(p.pos.x, p.pos.y, radius=28,
                                     color=(190, 170, 120))
    except Exception:
        pass


def cast_ultimate(game):
    """Klassen-Ultimate (X-Taste, 60s CD).

    Warrior: Wirbel-Angriff (2s rotating melee AoE)
    Mage:    Meteor (1s delayed massive AoE strike)
    Rogue:   Schatten-Klon (klon kämpft 6s mit)
    """
    p = game.player
    if not hasattr(p, 'ult_cd'):
        p.ult_cd = 0.0
    if p.ult_cd > 0:
        return
    eff = progression.effective(p)
    p.ult_cd = 60.0
    cls = p.cls
    if cls == 'warrior':
        # Wirbel-Effekt: 2s lang alle Gegner im Umkreis treffen
        if not hasattr(p, '_whirl_left'):
            p._whirl_left = 0.0
        p._whirl_left = 2.0
        game.spawn_particles(p.pos.x, p.pos.y, 30, (255, 220, 100),
                             life_max=0.6, size_max=5)
        game.shake = max(game.shake, 10)
        game.toast('Wirbel-Angriff!', (255, 200, 80))
    elif cls == 'mage':
        # Meteor: 1s delayed AoE-Einschlag an Maus-Position
        wpos = game.s2w(*pygame.mouse.get_pos())
        game._meteor_pending = {
            'pos': Vector2(wpos),
            'timer': 1.0,
            'damage': eff['damage'] * 10.0 * eff['fire_dmg'],
            'radius': 180,
        }
        game.toast('Meteor beschworen!', (255, 100, 40))
    else:  # rogue
        # Schatten-Klon: kämpft 6s
        if not hasattr(p, '_clone'):
            p._clone = None
        from .entities import Player as _P
        clone = _P(p.cls)
        clone.pos = Vector2(p.pos.x - 30, p.pos.y)
        clone.skill_levels = dict(p.skill_levels)
        clone._clone_left = 6.0
        clone._is_clone = True
        # Cloning für AI: einfach den Klon in Game tracken
        if not hasattr(game, 'clones'):
            game.clones = []
        game.clones.append(clone)
        game.spawn_particles(clone.pos.x, clone.pos.y, 30, (80, 30, 100),
                             life_max=0.5, size_max=5)
        game.toast('Schatten-Klon erschienen!', (80, 30, 200))
    snd.play('boss_intro', volume=0.6)


def cast_time_freeze(game):
    """Y-Skill: friert alle Gegner 4s ein. CD 35s."""
    p = game.player
    if not hasattr(p, 'tf_cd'):
        p.tf_cd = 0.0
    if p.tf_cd > 0:
        return
    p.tf_cd = 35.0
    game.time_freeze_left = 4.0
    # Visuell: blauer Tint + Eis-Partikel auf jeden Gegner
    for e in game.enemies:
        game.spawn_particles(e.pos.x, e.pos.y, 10, FROST,
                              life_max=0.5, size_max=4)
    game.spawn_particles(p.pos.x, p.pos.y, 50, (200, 220, 255),
                          life_max=0.8, size_max=5)
    game.shake = max(game.shake, 8)
    snd.play('cast_frost', volume=0.8)
    game.toast('ZEITSTILLSTAND', (200, 220, 255))


def cast_teleport(game):
    """B-Skill: Kurz-Blink in Maus-Richtung (max 220 Welt-Units). CD 8s.

    Update #43: Wand-Durchbruch-Bug behoben — neue Ziel-Suche prüft
    Line-of-Sight UND Decor-Kollision entlang der ganzen Bahn, nicht nur
    am Endpunkt. Spieler kann nicht mehr durch dünne Wände/Säulen blinken.
    """
    p = game.player
    if not hasattr(p, 'tp_cd'):
        p.tp_cd = 0.0
    if p.tp_cd > 0:
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    diff = wpos - p.pos
    # Audit #179 A.5: length_squared() ist schneller (kein sqrt) und schuetzt
    # explizit vor Null-Vektor in normalize() (Vector2.normalize() crasht bei
    # length == 0).
    if diff.length_squared() < 1.0:
        return
    dist = min(diff.length(), 220)
    direction = diff.normalize()
    # Default: bleibt stehen wenn nichts walkable ist
    target_x, target_y = p.pos.x, p.pos.y
    # Schrittweise von außen nach innen: für jeden Kandidat-Endpunkt
    # MÜSSEN sowohl Endpunkt als auch ALLE Punkte zwischen Start und Ende
    # frei sein (keine Wand, kein blockendes Decor). Erste passende Position
    # wird genommen.
    if game.grid is not None or game.tiles:
        for step in range(int(dist), 10, -10):
            tx = p.pos.x + direction.x * step
            ty = p.pos.y + direction.y * step
            # 1) Endpunkt frei?
            if game.grid is not None and game.grid.collide_circle(tx, ty, p.radius):
                continue
            if game._decor_collides(tx, ty, p.radius):
                continue
            # 2) Pfad zwischen Start und Endpunkt frei?
            #    LOS-Check + Decor-Sampling alle 8 Px
            blocked = False
            if game.grid is not None and not game.grid.has_los(
                    p.pos.x, p.pos.y, tx, ty):
                blocked = True
            if not blocked:
                # Decor-Sampling: 8-px-Steps prüfen, ob unterwegs blockendes
                # Decor liegt (Säulen, Statuen, Häuser, ...).
                sample_steps = max(2, step // 8)
                for s in range(1, sample_steps):
                    t = s / sample_steps
                    sx = p.pos.x + direction.x * step * t
                    sy = p.pos.y + direction.y * step * t
                    if game._decor_collides(sx, sy, p.radius):
                        blocked = True
                        break
            if not blocked:
                target_x, target_y = tx, ty
                break
    else:
        target_x = p.pos.x + direction.x * dist
        target_y = p.pos.y + direction.y * dist
    # Wenn keine Position gefunden wurde → kein Teleport, kein CD
    if target_x == p.pos.x and target_y == p.pos.y:
        # Visueller Feedback: kurzes Fizzle-Particle, kein CD verbraucht
        game.spawn_particles(p.pos.x, p.pos.y, 8, (180, 100, 240),
                              life_max=0.3, size_max=3)
        return
    p.tp_cd = 8.0
    # Partikel am Start + Ende
    game.spawn_particles(p.pos.x, p.pos.y, 30, (180, 100, 240),
                          life_max=0.6, size_max=5)
    p.pos.x, p.pos.y = target_x, target_y
    game.spawn_particles(p.pos.x, p.pos.y, 30, (180, 100, 240),
                          life_max=0.6, size_max=5)
    p.invuln = max(p.invuln, 0.3)
    snd.play('dodge', volume=0.7)


# ============================================================
# NEUE POE2-INSPIRIERTE SKILLS
# ============================================================
def cast_earthquake(game):
    """Slam mit Aftershock-Detonation nach 1.2s.
    Setup-Slam → Payoff-Explosion."""
    p = game.player
    info = SKILL_INFO['earthquake']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'earthquake'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'earthquake', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'earthquake')
    # Sofort-Slam: kleiner Schaden im Nahbereich
    mult, crit = _crit_roll(eff)
    inst_dmg = eff['damage'] * 1.2 * mult * skill_mult
    radius = 90
    for e in list(game.enemies):
        if (e.pos - p.pos).length() <= radius:
            if game.grid is None or game.grid.has_los(
                    p.pos.x, p.pos.y, e.pos.x, e.pos.y):
                game.hit_enemy(e, inst_dmg, crit=crit, dmg_type='physical')
    # Aftershock queue: nach 1.2s detoniert es nochmal mit doppeltem Schaden
    if hasattr(game, 'pending_aftershocks'):
        from pygame.math import Vector2 as _V
        game.pending_aftershocks.append({
            'pos': _V(p.pos.x, p.pos.y),
            'timer': 1.2,
            'damage': eff['damage'] * 2.6 * skill_mult,
            'radius': 160,
        })
    # Spawn Boden-Riss-Partikel
    for k in range(20):
        a = (k / 20) * math.tau
        game.particles_push(
            p.pos.x, p.pos.y,
            math.cos(a) * 180, math.sin(a) * 180,
            (180, 120, 60), 0.7, 5, gravity=80)
    game.shake = max(game.shake, 8)
    snd.play('hit_heavy')


def cast_spark(game):
    """Lightning-Projektil das von Waenden abprallt (Bounce)."""
    p = game.player
    info = SKILL_INFO['spark']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'spark'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'spark', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'spark')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 1.0 * eff['lit_dmg'] * mult * skill_mult
    # 3 Sparks im 30°-Fächer
    for a_offset in (-0.25, 0, 0.25):
        cos_a, sin_a = math.cos(a_offset), math.sin(a_offset)
        dx = direction.x * cos_a - direction.y * sin_a
        dy = direction.x * sin_a + direction.y * cos_a
        game.projectiles.append(Projectile(
            p.pos.x + dx * p.radius,
            p.pos.y + dy * p.radius,
            dx * 460, dy * 460,
            dmg, 'spark',
            radius=6, life=1.4,
            extra={'crit': crit, 'bounces': 3, 'dmg_type': 'lightning'},
        ))
    snd.play('cast_lightning')


def cast_bone_spear(game):
    """Hartes physisches Projektil mit hoher Single-Target-Schaden + Pierce."""
    p = game.player
    info = SKILL_INFO['bone_spear']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'bone_spear'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'bone_spear', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'bone_spear')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 3.0 * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 720, direction.y * 720,
        dmg, 'bone_spear',
        radius=8, life=1.0,
        extra={'crit': crit, 'pierce': 3, 'dmg_type': 'physical'},
    ))
    game.spawn_particles(p.pos.x, p.pos.y, 6, (220, 210, 180))
    # Update #27: Bone-Spear = dark-magic (Knochenwitwen-Lore)
    snd.play('cast_dark', volume=0.8)


def cast_ice_nova(game):
    """AoE-Nova um Spieler. Bei Frost-Stacks am Ziel: SHATTER-Combo."""
    p = game.player
    info = SKILL_INFO['ice_nova']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'ice_nova'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'ice_nova', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'ice_nova')
    radius = 160
    for e in list(game.enemies):
        d = (e.pos - p.pos).length()
        if d > radius or e.dying:
            continue
        if game.grid is not None and not game.grid.has_los(
                p.pos.x, p.pos.y, e.pos.x, e.pos.y):
            continue
        mult, crit = _crit_roll(eff)
        base_dmg = eff['damage'] * 1.4 * eff['cold_dmg'] * mult * skill_mult
        # Shatter-Payoff: bei Frost-Stacks auf Ziel = 2.5x Schaden
        if 'frost' in e.status:
            base_dmg *= 2.5
            game.spawn_particles(e.pos.x, e.pos.y, 30,
                                  (220, 240, 255), life_max=0.8, size_max=6)
            from . import sounds as _snd
            _snd.play('crit', volume=0.8)
        game.hit_enemy(e, base_dmg, crit=crit, dmg_type='cold')
        # Wendet auch Frost-Stacks an
        if e in game.enemies:
            fx.apply(game, e, 'frost', stacks=2)
    # Visueller Ring
    for k in range(36):
        a = (k / 36) * math.tau
        game.particles_push(p.pos.x + math.cos(a) * 40,
                             p.pos.y + math.sin(a) * 40,
                             math.cos(a) * 320, math.sin(a) * 320,
                             FROST, 0.7, 5)
    game.shake = max(game.shake, 6)
    snd.play('cast_frost')


def cast_comet(game):
    """Riesiger Cold-Asteroid faellt mit 1.5s Verzoegerung an Maus-Position."""
    p = game.player
    info = SKILL_INFO['comet']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'comet'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'comet', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'comet')
    wpos = game.s2w(*pygame.mouse.get_pos())
    # In game.comets-Liste hinzufuegen (game muss das verarbeiten)
    if not hasattr(game, 'pending_comets'):
        game.pending_comets = []
    game.pending_comets.append({
        'pos': Vector2(wpos.x, wpos.y),
        'timer': 1.5,
        'damage': eff['damage'] * 8.0 * eff['cold_dmg'] * skill_mult,
        'radius': 220,
    })
    snd.play('cast_frost', volume=0.8)


# ============================================================
# KLASSEN-SIGNATURE-CASTS (Update #23)
# ============================================================
def cast_boneshatter(game):
    """Warrior — Phys-Cone-Strike vor dem Spieler. Stun-Buildup, Knockback."""
    p = game.player
    info = SKILL_INFO['boneshatter']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'boneshatter'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    facing = wpos - p.pos
    if facing.length_squared() == 0:
        return
    facing = facing.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'boneshatter', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'boneshatter')
    # 120° Cone, Radius 140
    cone_radius = 140
    cone_cos = math.cos(math.radians(60))  # Halb-Winkel = 60°
    hits = 0
    for e in list(game.enemies):
        d_vec = e.pos - p.pos
        d = d_vec.length()
        if d > cone_radius + e.radius or e.dying:
            continue
        if d > 0:
            cos_a = (d_vec.x * facing.x + d_vec.y * facing.y) / d
            if cos_a < cone_cos:
                continue
        mult, crit = _crit_roll(eff)
        dmg = eff['damage'] * 2.6 * mult * skill_mult
        game.hit_enemy(e, dmg, crit=crit, dmg_type='physical')
        # Knockback
        if d > 0:
            game.move_entity(e, d_vec.x / d * 22, d_vec.y / d * 22)
        e.stun_timer = max(getattr(e, 'stun_timer', 0), 0.5)
        hits += 1
    # VFX: Bone-Splitter im Cone
    for k in range(28):
        a = math.atan2(facing.y, facing.x) + random.uniform(-math.pi/3, math.pi/3)
        sp = random.uniform(180, 360)
        game.particles_push(p.pos.x + facing.x * 30,
                             p.pos.y + facing.y * 30,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (220, 210, 180), random.uniform(0.4, 0.7),
                             random.uniform(3, 6))
    game.shake = max(game.shake, 7 if hits else 4)
    snd.play('hit_heavy' if hits else 'hit')


def cast_killing_palm(game):
    """Monk — Phys-Melee, Execute-Bonus gegen <30 % HP-Ziele."""
    p = game.player
    info = SKILL_INFO['killing_palm']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'killing_palm'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    facing = wpos - p.pos
    if facing.length_squared() == 0:
        return
    facing = facing.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'killing_palm', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'killing_palm')
    # Such nächsten Gegner in 110px Reichweite + Cone (cos 30°)
    cone_cos = math.cos(math.radians(30))
    best = None
    best_d = 999
    for e in game.enemies:
        d_vec = e.pos - p.pos
        d = d_vec.length()
        if d > 130 + e.radius or e.dying:
            continue
        if d > 0:
            cos_a = (d_vec.x * facing.x + d_vec.y * facing.y) / d
            if cos_a < cone_cos:
                continue
        if d < best_d:
            best = e
            best_d = d
    if not best:
        return
    mult, crit = _crit_roll(eff)
    base = eff['damage'] * 3.4 * mult * skill_mult
    # Execute-Bonus: <30 % HP → 3× Damage
    if best.hp / max(1, best.hp_max) < 0.30:
        base *= 3.0
        game.floaters.append(Floater(best.pos.x, best.pos.y - best.radius - 12,
                                      'EXECUTE!', (255, 240, 200), big=True))
    game.hit_enemy(best, base, crit=crit, dmg_type='physical')
    # Ring-Shock-Wave VFX
    for k in range(20):
        a = (k / 20) * math.tau
        game.particles_push(best.pos.x, best.pos.y,
                             math.cos(a) * 260, math.sin(a) * 260,
                             (255, 230, 180), 0.5, 5)
    game.shake = max(game.shake, 8)
    snd.play('crit')


def cast_detonate_dead(game):
    """Witch — explodiert nächste „Leiche" (kürzlich-toter Enemy-Decal)."""
    p = game.player
    info = SKILL_INFO['detonate_dead']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'detonate_dead'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'detonate_dead', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'detonate_dead')
    # Suche Blood-Pool als „Leiche"-Marker (Engine-Hack: Pools werden bei
    # Enemy-Death gesetzt). Sonst: AoE um Player.
    wpos = game.s2w(*pygame.mouse.get_pos())
    epi_x, epi_y = wpos.x, wpos.y
    pools = getattr(game, 'blood_pools', [])
    if pools:
        nearest = min(pools, key=lambda b: (b[0] - wpos.x) ** 2 +
                                              (b[1] - wpos.y) ** 2)
        epi_x, epi_y = nearest[0], nearest[1]
    # AoE-Damage in 130 Radius
    radius = 130
    hits = 0
    for e in list(game.enemies):
        d = ((e.pos.x - epi_x) ** 2 + (e.pos.y - epi_y) ** 2) ** 0.5
        if d > radius or e.dying:
            continue
        mult, crit = _crit_roll(eff)
        dmg = eff['damage'] * 2.2 * mult * skill_mult
        game.hit_enemy(e, dmg, crit=crit, dmg_type='chaos')
        # Apply Poison-Stack on chaos-AoE
        from . import effects as _fx
        _fx.apply(game, e, 'poison', stacks=2)
        hits += 1
    # VFX: Lila/Grün-Explosion
    for k in range(40):
        a = (k / 40) * math.tau
        sp = random.uniform(140, 320)
        game.particles_push(epi_x, epi_y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (160, 80, 200) if k % 2 == 0 else (120, 200, 100),
                             0.7, 5)
    game.shake = max(game.shake, 6)
    # Update #27: Detonate Dead = dark magic (Witch Lore-Anker)
    snd.play('cast_dark', volume=1.0)


def cast_lightning_arrow(game):
    """Ranger — Lightning-Bow-Projektil; kettet bei Impact zu 3 Zielen."""
    p = game.player
    info = SKILL_INFO['lightning_arrow']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'lightning_arrow'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'lightning_arrow', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'lightning_arrow')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.0 * eff['lit_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 880, direction.y * 880,
        dmg, 'spark',
        radius=7, life=1.2,
        extra={'crit': crit, 'dmg_type': 'lightning',
               'chain_on_hit': 3, 'chain_dmg_mult': 0.65},
    ))
    game.spawn_particles(p.pos.x, p.pos.y, 8, (180, 220, 255),
                         life_max=0.4, size_max=4)
    snd.play('cast_lightning')


def cast_galvanic_shot(game):
    """Mercenary/Rogue — Crossbow-Lightning + Splash-Funken bei Impact."""
    p = game.player
    info = SKILL_INFO['galvanic_shot']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'galvanic_shot'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'galvanic_shot', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'galvanic_shot')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.4 * eff['lit_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 820, direction.y * 820,
        dmg, 'firebolt',
        radius=8, life=1.0,
        extra={'crit': crit, 'dmg_type': 'lightning',
               'splash_on_hit': 3, 'splash_dmg_mult': 0.5,
               'splash_radius': 80},
    ))
    game.spawn_particles(p.pos.x, p.pos.y, 10, (200, 230, 255),
                         life_max=0.4, size_max=4)
    snd.play('cast_lightning')


def cast_lightning_spear(game):
    """Huntress — Phys+Lightning-Speer, durchschlägt 3 Ziele."""
    p = game.player
    info = SKILL_INFO['lightning_spear']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'lightning_spear'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'lightning_spear', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'lightning_spear')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.8 * mult * skill_mult
    # Speer als bone_spear-Projektil mit Lightning-Tint
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 760, direction.y * 760,
        dmg, 'bone_spear',
        radius=9, life=1.0,
        extra={'crit': crit, 'pierce': 3, 'dmg_type': 'lightning',
               'color_override': (220, 240, 255)},
    ))
    # Pre-Shock-Bolt zur Mauszeiger-Richtung (visuell)
    end_x = p.pos.x + direction.x * 220
    end_y = p.pos.y + direction.y * 220
    game.bolts.append(LightningBolt(p.pos.x, p.pos.y, end_x, end_y))
    game.spawn_particles(p.pos.x, p.pos.y, 8, (220, 240, 255),
                         life_max=0.4, size_max=4)
    snd.play('cast_lightning')


# ============================================================
# Update #107 — Klassen-Skill-Cast-Erweiterung (PLAN K-02/K-05/K-06)
# ============================================================

def cast_frost_arrow(game):
    """Ranger — Cold-Bow-Projektil mit Frost-Stack-Apply (Nheyras Atem)."""
    p = game.player
    info = SKILL_INFO['frost_arrow']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'frost_arrow'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'frost_arrow', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'frost_arrow')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.1 * eff['cold_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 860, direction.y * 860,
        dmg, 'frost_bolt',
        radius=7, life=1.1,
        extra={'crit': crit, 'dmg_type': 'cold',
               'apply_status': 'frost', 'apply_stacks': 2,
               'color_override': (190, 230, 255)},
    ))
    # Frost-Sparkle am Bogen
    for _ in range(6):
        a = math.atan2(direction.y, direction.x) + random.uniform(-0.4, 0.4)
        sp = random.uniform(80, 200)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (200, 240, 255), random.uniform(0.3, 0.5), 3)
    snd.play('cast_frost', volume=0.7)


def cast_burning_arrow(game):
    """Ranger — Fire-Bow-Projektil mit hoher Ignite-Chance (Valsas Asche)."""
    p = game.player
    info = SKILL_INFO['burning_arrow']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'burning_arrow'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'burning_arrow', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'burning_arrow')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.0 * eff['fire_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 820, direction.y * 820,
        dmg, 'firebolt',
        radius=7, life=1.1,
        extra={'crit': crit, 'dmg_type': 'fire',
               'apply_status': 'burn', 'apply_stacks': 3,
               'color_override': (255, 180, 80)},
    ))
    # Glut-Trail
    for _ in range(8):
        a = math.atan2(direction.y, direction.x) + random.uniform(-0.3, 0.3)
        sp = random.uniform(60, 180)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (255, 160, 60), random.uniform(0.3, 0.6), 4)
    snd.play('cast_fire', volume=0.7)


def cast_permafrost_bolts(game):
    """Mercenary/Rogue — Crossbow-Cold-Bolt, +Frost-Stack-Apply (Salzhüter-Bolzen)."""
    p = game.player
    info = SKILL_INFO['permafrost_bolts']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'permafrost_bolts'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'permafrost_bolts', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'permafrost_bolts')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 1.9 * eff['cold_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 920, direction.y * 920,
        dmg, 'frost_bolt',
        radius=7, life=0.9,
        extra={'crit': crit, 'dmg_type': 'cold',
               'apply_status': 'frost', 'apply_stacks': 1,
               'apply_status_2': 'chill', 'apply_stacks_2': 1,
               'color_override': (180, 220, 255)},
    ))
    for _ in range(5):
        a = math.atan2(direction.y, direction.x) + random.uniform(-0.25, 0.25)
        sp = random.uniform(100, 200)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (200, 230, 255), random.uniform(0.25, 0.4), 3)
    snd.play('cast_frost', volume=0.6)


def cast_plasma_blast(game):
    """Mercenary/Rogue — Geladener AoE-Lightning-Bolt mit Shocked-Payoff."""
    p = game.player
    info = SKILL_INFO['plasma_blast']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'plasma_blast'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'plasma_blast', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'plasma_blast')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.6 * eff['lit_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 700, direction.y * 700,
        dmg, 'spark',
        radius=11, life=1.3,
        extra={'crit': crit, 'dmg_type': 'lightning',
               'splash_on_hit': 5, 'splash_dmg_mult': 0.7,
               'splash_radius': 110,
               'apply_status': 'shock', 'apply_stacks': 2,
               'payoff_status': 'shock', 'payoff_dmg_mult': 2.0,
               'color_override': (220, 240, 255)},
    ))
    # Wind-Up: lila-weiß Korona um Player
    for k in range(14):
        a = (k / 14) * math.tau
        sp = random.uniform(40, 90)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (220, 180, 255) if k % 2 == 0 else (255, 255, 255),
                             0.35, 4)
    game.shake = max(game.shake, 5)
    snd.play('cast_lightning', volume=0.9)


def cast_tempest_bell(game):
    """Monk — Sturmglocke pulsiert 3× Lightning-Nova über 1.2 s."""
    p = game.player
    info = SKILL_INFO['tempest_bell']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'tempest_bell'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'tempest_bell', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'tempest_bell')
    base_dmg = eff['damage'] * 1.2 * eff['lit_dmg'] * skill_mult
    radius = 130

    def _pulse(bell_x, bell_y, hit_dmg):
        def _strike(g, _decal=None):
            for e in list(g.enemies):
                d = ((e.pos.x - bell_x) ** 2 +
                     (e.pos.y - bell_y) ** 2) ** 0.5
                if d > radius or e.dying:
                    continue
                m, c = _crit_roll(progression.effective(g.player))
                g.hit_enemy(e, hit_dmg * m, crit=c, dmg_type='lightning')
                fx.apply(g, e, 'shock', stacks=1)
            for k in range(22):
                a = (k / 22) * math.tau
                sp = random.uniform(150, 320)
                g.particles_push(bell_x, bell_y,
                                  math.cos(a) * sp, math.sin(a) * sp,
                                  (240, 230, 200) if k % 2 == 0
                                  else (255, 255, 200),
                                  0.6, 4)
            g.bolts.append(LightningBolt(bell_x, bell_y - 320,
                                          bell_x, bell_y))
            g.shake = max(g.shake, 6)
            snd.play('cast_lightning', volume=0.5)
        return _strike

    from .entities import Decal
    # Drei Pulse: 0.0 / 0.4 / 0.8 s.  Decal nutzt windup als Verzögerung
    # vor dem on_activate.
    for i, delay in enumerate((0.0, 0.4, 0.8)):
        d = Decal(wpos.x, wpos.y, radius, kind='cc',
                   windup=delay + 0.1, lifetime=0.25,
                   on_activate=_pulse(wpos.x, wpos.y, base_dmg),
                   source=p)
        game.decals.append(d)
    # Glocke-Visual: stiller Gold-Funken-Ring
    for k in range(18):
        a = (k / 18) * math.tau
        game.particles_push(wpos.x, wpos.y,
                             math.cos(a) * 30, math.sin(a) * 30 - 40,
                             (240, 220, 160), 0.6, 4)
    snd.play('cast_lightning', volume=0.4)


def cast_glacial_cascade(game):
    """Monk — Cold-AoE-Reihe vor dem Mönch (5 Eis-Stufen mit Frost-Stack)."""
    p = game.player
    info = SKILL_INFO['glacial_cascade']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'glacial_cascade'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'glacial_cascade', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'glacial_cascade')
    stage_dmg = eff['damage'] * 0.95 * eff['cold_dmg'] * skill_mult

    def _stage_strike(sx, sy, hit_dmg):
        def _strike(g, _decal=None):
            for e in list(g.enemies):
                d = ((e.pos.x - sx) ** 2 + (e.pos.y - sy) ** 2) ** 0.5
                if d > 60 or e.dying:
                    continue
                m, c = _crit_roll(progression.effective(g.player))
                g.hit_enemy(e, hit_dmg * m, crit=c, dmg_type='cold')
                fx.apply(g, e, 'frost', stacks=2)
            # Eis-Spike-VFX
            for k in range(14):
                a = (k / 14) * math.tau
                sp = random.uniform(110, 240)
                g.particles_push(sx, sy,
                                  math.cos(a) * sp,
                                  math.sin(a) * sp - 40,
                                  (200, 240, 255) if k % 2 == 0
                                  else (160, 200, 240),
                                  0.55, 5)
            snd.play('cast_frost', volume=0.4)
        return _strike

    from .entities import Decal
    # 5 Stufen entlang facing-Richtung; je Stage 0.08 s Versatz
    for i in range(5):
        dist = 60 + i * 55
        sx = p.pos.x + direction.x * dist
        sy = p.pos.y + direction.y * dist
        d = Decal(sx, sy, 60, kind='cc',
                   windup=0.08 * i + 0.08, lifetime=0.25,
                   on_activate=_stage_strike(sx, sy, stage_dmg),
                   source=p)
        game.decals.append(d)
    snd.play('cast_frost', volume=0.7)


# ============================================================
# Update #108 — Warrior / Witch / Huntress / Druid Cast-Erweiterung
# PLAN K-01 / K-04 / K-07 / K-08
# ============================================================

def cast_leap_slam(game):
    """Warrior — springt zu Mauszeiger, Phys-AoE bei Landung."""
    p = game.player
    info = SKILL_INFO['leap_slam']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'leap_slam'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'leap_slam', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'leap_slam')
    # Move-Cap: max 280 px in Richtung Maus
    dir_vec = wpos - p.pos
    dist = dir_vec.length()
    if dist > 0:
        cap = min(dist, 280.0)
        dir_vec = dir_vec * (cap / dist)
    land_x = p.pos.x + dir_vec.x
    land_y = p.pos.y + dir_vec.y
    # Take-Off-Particles
    for k in range(20):
        a = (k / 20) * math.tau
        sp = random.uniform(110, 240)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp + 40,
                             (200, 180, 140), 0.45, 5)
    # Teleport-Move (mit Wand-Slide)
    game.move_entity(p, dir_vec.x, dir_vec.y)
    # Landung — AoE 100 px
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.4 * mult * skill_mult
    radius = 100
    hits = 0
    for e in list(game.enemies):
        d = ((e.pos.x - land_x) ** 2 + (e.pos.y - land_y) ** 2) ** 0.5
        if d > radius + e.radius or e.dying:
            continue
        m2, c2 = _crit_roll(eff)
        game.hit_enemy(e, dmg * m2 / mult if mult else dmg,
                       crit=(crit or c2), dmg_type='physical')
        # Knockback
        if d > 0:
            kx = (e.pos.x - land_x) / d * 28
            ky = (e.pos.y - land_y) / d * 28
            game.move_entity(e, kx, ky)
        e.stun_timer = max(getattr(e, 'stun_timer', 0), 0.4)
        hits += 1
    # Landungs-Ring
    for k in range(28):
        a = (k / 28) * math.tau
        sp = random.uniform(180, 340)
        game.particles_push(land_x, land_y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (230, 200, 140) if k % 2 == 0
                             else (200, 170, 100),
                             0.55, 5)
    game.shake = max(game.shake, 14 if hits else 8)
    snd.play('hit_heavy', volume=0.85)


def cast_molten_blast(game):
    """Warrior — Fire-Projektil mit AoE-Explosion bei Impact."""
    p = game.player
    info = SKILL_INFO['molten_blast']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'molten_blast'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'molten_blast', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'molten_blast')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.0 * eff['fire_dmg'] * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 580, direction.y * 580,
        dmg, 'fireball',
        radius=10, life=1.3,
        extra={'crit': crit, 'dmg_type': 'fire',
               'aoe': 75, 'burn': True,
               'color_override': (255, 130, 40)},
    ))
    # Wind-Up: Glut-Pulse am Caster
    for k in range(12):
        a = math.atan2(direction.y, direction.x) + random.uniform(
            -math.pi / 3, math.pi / 3)
        sp = random.uniform(60, 160)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (255, 160, 60), random.uniform(0.3, 0.5), 5)
    snd.play('cast_fire', volume=0.85)


def cast_essence_drain(game):
    """Witch — Chaos-Projektil, DoT, heilt 15 % des Schadens an Casterin."""
    p = game.player
    info = SKILL_INFO['essence_drain']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'essence_drain'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'essence_drain', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'essence_drain')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 1.9 * mult * skill_mult
    # Heilt 15 % des Damage als HP zurück bei Impact — engine-Hook über
    # apply_status='poison' und Self-Heal vor Cast (kein extra dispatcher
    # nötig: wir heilen sofort einen kleinen Tick).
    heal = max(1, int(dmg * 0.15))
    p.hp = min(eff['hp_max'], p.hp + heal)
    if heal >= 2:
        from .entities import Floater
        game.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 12,
                                      f'+{heal}', (120, 220, 120), heal=True))
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 580, direction.y * 580,
        dmg, 'shadowbolt',
        radius=8, life=1.4,
        extra={'crit': crit, 'dmg_type': 'chaos',
               'apply_status': 'poison', 'apply_stacks': 3,
               'color_override': (130, 80, 180)},
    ))
    # Lila-Grün-Trail
    for k in range(10):
        a = math.atan2(direction.y, direction.x) + random.uniform(-0.4, 0.4)
        sp = random.uniform(70, 180)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (140, 80, 180) if k % 2 == 0
                             else (120, 200, 110),
                             random.uniform(0.4, 0.6), 4)
    snd.play('cast_dark', volume=0.7)


def cast_contagion(game):
    """Witch — Chaos-AoE 110 px, Poison-Stack auf alle in Radius."""
    p = game.player
    info = SKILL_INFO['contagion']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'contagion'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'contagion', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'contagion')
    radius = 110
    hits = 0
    for e in list(game.enemies):
        d = ((e.pos.x - wpos.x) ** 2 + (e.pos.y - wpos.y) ** 2) ** 0.5
        if d > radius or e.dying:
            continue
        mult, crit = _crit_roll(eff)
        dmg = eff['damage'] * 1.6 * mult * skill_mult
        game.hit_enemy(e, dmg, crit=crit, dmg_type='chaos')
        try:
            fx.apply(game, e, 'poison', stacks=3)
        except Exception:
            pass
        hits += 1
    # Lila-Grün-Spreading-Wolke
    for k in range(34):
        a = (k / 34) * math.tau
        sp = random.uniform(140, 310)
        game.particles_push(wpos.x, wpos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (150, 90, 190) if k % 2 == 0
                             else (130, 210, 110),
                             0.7, 5)
    game.shake = max(game.shake, 5)
    snd.play('cast_dark', volume=0.9)


def cast_whirling_slash(game):
    """Huntress — Channeling-Wirbel 90 px um Spielerin, 3 Hits über 0.6 s."""
    p = game.player
    info = SKILL_INFO['whirling_slash']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'whirling_slash'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'whirling_slash', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'whirling_slash')
    radius = 90
    base = eff['damage'] * 0.85 * skill_mult

    def _wirbel_tick(tick_dmg):
        def _strike(g, _decal=None):
            pl = g.player
            for e in list(g.enemies):
                d = (e.pos - pl.pos).length()
                if d > radius + e.radius or e.dying:
                    continue
                m, c = _crit_roll(progression.effective(pl))
                g.hit_enemy(e, tick_dmg * m, crit=c, dmg_type='physical')
            for k in range(12):
                a = (k / 12) * math.tau + random.random() * 0.3
                sp = random.uniform(120, 230)
                g.particles_push(pl.pos.x, pl.pos.y,
                                  math.cos(a) * sp, math.sin(a) * sp,
                                  (230, 220, 200), 0.35, 4)
            snd.play('hit', volume=0.45)
        return _strike

    from .entities import Decal
    for i, delay in enumerate((0.0, 0.2, 0.4)):
        d = Decal(p.pos.x, p.pos.y, radius, kind='cc',
                   windup=delay + 0.05, lifetime=0.2,
                   on_activate=_wirbel_tick(base),
                   source=p)
        game.decals.append(d)
    snd.play('hit_heavy', volume=0.45)


def cast_spear_throw(game):
    """Huntress — Wurf-Speer, pierce 2 Ziele, voller Schaden."""
    p = game.player
    info = SKILL_INFO['spear_throw']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'spear_throw'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    direction = wpos - p.pos
    if direction.length_squared() == 0:
        return
    direction = direction.normalize()
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'spear_throw', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'spear_throw')
    mult, crit = _crit_roll(eff)
    dmg = eff['damage'] * 2.5 * mult * skill_mult
    game.projectiles.append(Projectile(
        p.pos.x + direction.x * p.radius,
        p.pos.y + direction.y * p.radius,
        direction.x * 880, direction.y * 880,
        dmg, 'bone_spear',
        radius=9, life=1.0,
        extra={'crit': crit, 'pierce': 2, 'dmg_type': 'physical',
               'apply_status': 'bleed', 'apply_stacks': 1,
               'color_override': (220, 200, 160)},
    ))
    for _ in range(5):
        a = math.atan2(direction.y, direction.x) + random.uniform(-0.2, 0.2)
        sp = random.uniform(80, 200)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (220, 210, 180), random.uniform(0.3, 0.45), 4)
    snd.play('hit', volume=0.6)


def cast_spore_burst(game):
    """Druid — Chaos-Nova 100 px um Player, 2 Poison-Stacks."""
    p = game.player
    info = SKILL_INFO['spore_burst']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'spore_burst'):
        return
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'spore_burst', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'spore_burst')
    radius = 100
    hits = 0
    for e in list(game.enemies):
        d = (e.pos - p.pos).length()
        if d > radius + e.radius or e.dying:
            continue
        mult, crit = _crit_roll(eff)
        dmg = eff['damage'] * 1.3 * mult * skill_mult
        game.hit_enemy(e, dmg, crit=crit, dmg_type='chaos')
        try:
            fx.apply(game, e, 'poison', stacks=2)
        except Exception:
            pass
        hits += 1
    # Grün-Lila-Sporen-Wolke
    for k in range(30):
        a = (k / 30) * math.tau
        sp = random.uniform(130, 260)
        game.particles_push(p.pos.x, p.pos.y,
                             math.cos(a) * sp, math.sin(a) * sp,
                             (140, 200, 110) if k % 2 == 0
                             else (170, 90, 180),
                             0.6, 5)
    snd.play('cast_dark', volume=0.65)


def cast_hailstorm(game):
    """Druid — Hagel-Cold-AoE 140 px an Maus-Position, 3 Frost-Stacks."""
    p = game.player
    info = SKILL_INFO['hailstorm']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'hailstorm'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'hailstorm', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'hailstorm')
    radius = 140
    base_dmg = eff['damage'] * 0.6 * eff['cold_dmg'] * skill_mult

    def _hagel_tick(g, _decal=None):
        pl = g.player
        for e in list(g.enemies):
            d = ((e.pos.x - wpos.x) ** 2 + (e.pos.y - wpos.y) ** 2) ** 0.5
            if d > radius or e.dying:
                continue
            m, c = _crit_roll(progression.effective(pl))
            g.hit_enemy(e, base_dmg * m, crit=c, dmg_type='cold')
            try:
                fx.apply(g, e, 'frost', stacks=3)
                fx.apply(g, e, 'chill', stacks=1)
            except Exception:
                pass
        # Hagel-VFX: Eis-Splitter aus oben
        for k in range(24):
            a = (k / 24) * math.tau
            sp = random.uniform(120, 250)
            g.particles_push(wpos.x, wpos.y,
                              math.cos(a) * sp,
                              math.sin(a) * sp + 80,
                              (210, 240, 255) if k % 2 == 0
                              else (170, 200, 240),
                              0.6, 5)
        snd.play('cast_frost', volume=0.5)

    # Drei Hagel-Pulse: 0.0 / 0.45 / 0.9 s
    from .entities import Decal
    for i, delay in enumerate((0.0, 0.45, 0.9)):
        d = Decal(wpos.x, wpos.y, radius, kind='cc',
                   windup=delay + 0.1, lifetime=0.3,
                   on_activate=_hagel_tick, source=p)
        game.decals.append(d)
    snd.play('cast_frost', volume=0.85)


def cast_storm_call(game):
    """Druid — markiert Boden, schlägt nach 1.2 s als Sky-Lightning ein."""
    p = game.player
    info = SKILL_INFO['storm_call']
    if not _has_mana(p, info['mana']) or _on_cooldown(p, 'storm_call'):
        return
    wpos = game.s2w(*pygame.mouse.get_pos())
    eff = progression.effective(p)
    _spend_mana(p, info, eff)
    _apply_cd(p, 'storm_call', info['cd'], eff['cdr'])
    skill_mult = progression.skill_level_mult(p, 'storm_call')
    dmg = eff['damage'] * 3.4 * eff['lit_dmg'] * skill_mult
    radius = 120

    def _strike(g, _decal=None):
        for e in list(g.enemies):
            d = (e.pos - wpos).length()
            if d > radius or e.dying:
                continue
            mult, crit = _crit_roll(progression.effective(g.player))
            g.hit_enemy(e, dmg * mult, crit=crit, dmg_type='lightning')
            from . import effects as _fx
            _fx.apply(g, e, 'shock', stacks=2)
        # Massive lightning bolt vertical
        g.bolts.append(LightningBolt(wpos.x, wpos.y - 600, wpos.x, wpos.y))
        for k in range(36):
            a = (k / 36) * math.tau
            g.particles_push(wpos.x, wpos.y,
                              math.cos(a) * 320, math.sin(a) * 320,
                              (220, 240, 255), 0.7, 5)
        g.shake = max(g.shake, 10)
        snd.play('cast_lightning', volume=1.0)

    from .entities import Decal
    decal = Decal(wpos.x, wpos.y, radius, kind='deadly',
                   windup=1.2, lifetime=0.3,
                   on_activate=_strike, source=p)
    game.decals.append(decal)
    snd.play('cast_lightning', volume=0.6)


CAST_DISPATCH = {
    'fireball':         cast_fireball,
    'lightning':        cast_lightning,
    'heal':             cast_heal,
    'frostnova':        cast_frostnova,
    'earthquake':       cast_earthquake,
    'spark':            cast_spark,
    'bone_spear':       cast_bone_spear,
    'ice_nova':         cast_ice_nova,
    'comet':            cast_comet,
    # Class signatures (Update #23)
    'boneshatter':      cast_boneshatter,
    'killing_palm':     cast_killing_palm,
    'detonate_dead':    cast_detonate_dead,
    'lightning_arrow':  cast_lightning_arrow,
    'galvanic_shot':    cast_galvanic_shot,
    'lightning_spear':  cast_lightning_spear,
    'storm_call':       cast_storm_call,
    # Klassen-Skill-Erweiterung Update #107
    'frost_arrow':       cast_frost_arrow,
    'burning_arrow':     cast_burning_arrow,
    'permafrost_bolts':  cast_permafrost_bolts,
    'plasma_blast':      cast_plasma_blast,
    'tempest_bell':      cast_tempest_bell,
    'glacial_cascade':   cast_glacial_cascade,
    # Klassen-Skill-Erweiterung Update #108
    'leap_slam':         cast_leap_slam,
    'molten_blast':      cast_molten_blast,
    'essence_drain':     cast_essence_drain,
    'contagion':         cast_contagion,
    'whirling_slash':    cast_whirling_slash,
    'spear_throw':       cast_spear_throw,
    'spore_burst':       cast_spore_burst,
    'hailstorm':         cast_hailstorm,
}


# ============================================================
# CLASS-KEYMAP (Update #23 — pro Klasse eigene Q/W/E/R/1/2/3)
# ============================================================
# Lore-konforme Skill-Hotkey-Belegung pro Klasse.
# Q = Signature (klassen-unique), W/E/R/1/2 mischen aus Klassen-Pool.
CLASS_KEYMAP = {
    'warrior':  ['boneshatter',     'earthquake',      'heal',
                 'leap_slam',       'molten_blast'],
    'monk':     ['killing_palm',    'tempest_bell',    'glacial_cascade',
                 'spark',           'ice_nova'],
    'mage':     ['fireball',        'lightning',       'frostnova',
                 'spark',           'comet'],
    'witch':    ['bone_spear',      'detonate_dead',   'essence_drain',
                 'contagion',       'comet'],
    'ranger':   ['lightning_arrow', 'frost_arrow',     'burning_arrow',
                 'heal',            'comet'],
    'rogue':    ['galvanic_shot',   'permafrost_bolts','plasma_blast',
                 'heal',            'frostnova'],
    'huntress': ['lightning_spear', 'whirling_slash',  'heal',
                 'ice_nova',        'spear_throw'],
    'druid':    ['storm_call',      'spore_burst',     'heal',
                 'earthquake',      'hailstorm'],
}

# Hotkey-Reihenfolge (Q/W/E/R/1) — index in CLASS_KEYMAP[cls]
HOTKEY_LABELS = ['Q', 'W', 'E', 'R', '1']


def class_keymap(cls):
    """Returnt die Skill-IDs in Hotkey-Reihenfolge für eine Klasse."""
    return CLASS_KEYMAP.get(cls, CLASS_KEYMAP['mage'])


def class_skill_at(cls, hotkey_index):
    """Returnt die Skill-ID für (Klasse, Hotkey-Index 0..4)."""
    pool = class_keymap(cls)
    if 0 <= hotkey_index < len(pool):
        return pool[hotkey_index]
    return None


def default_unlocked_for_class(cls):
    """Returnt die Skill-Set, die eine neue Klasse beim Start kann.

    Includes Q/W (Signature + 1) sowie E (Heal/Utility). R+1 sind über
    Gemcutter zu freischalten — gibt Progression-Anreiz.
    """
    pool = class_keymap(cls)
    return set(pool[:3])  # Q, W, E


def cast(name, game):
    # PoE2-Style: nur freigeschaltete Skills castbar
    if name not in game.player.unlocked_skills:
        game.toast(f'{name.capitalize()}-Gem nicht erlernt!', (200, 150, 100))
        return
    fn = CAST_DISPATCH.get(name)
    if fn:
        fn(game)
        # Combo-Tracking: 3 verschiedene Skills in 2s → +30% Schaden für 2s
        import time
        now = time.time()
        game._combo_skill_log.append((now, name))
        # Alte Einträge raus (>2s)
        game._combo_skill_log = [(t, n) for t, n in game._combo_skill_log
                                 if now - t <= 2.0]
        unique_skills = {n for _, n in game._combo_skill_log}
        if len(unique_skills) >= 3 and not getattr(game.player, 'combo_buff_left', 0):
            game.player.combo_buff_left = 2.5
            game.toast('COMBO! +30% Schaden', (255, 220, 100))
            from . import sounds as _snd
            _snd.play('combo')
