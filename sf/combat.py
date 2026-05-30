"""Schadens-, Heil- und Tod-Logik (operiert auf Game)."""

import random
import math

import pygame

from .entities import Floater, Loot
from . import progression
from . import items as items_mod
from . import achievements as ach_mod
from . import sounds as snd
from .crafting import random_gem


def hit_enemy(game, e, dmg, crit=False, dmg_type='physical'):
    if e.dying:
        return
    # PLAN E-02: Boss während Cinematic-Intro unverwundbar (verhindert
    # Cheese-Killen während Lower-Third-UI noch läuft).
    if getattr(e, '_encounter_invuln_left', 0.0) > 0.0:
        # Visuelles Feedback, dass Hit geblockt wurde
        game.spawn_particles(e.pos.x, e.pos.y, 6, (200, 200, 200),
                             life_max=0.3, size_max=4)
        game.floaters.append(Floater(e.pos.x, e.pos.y - e.radius - 6,
                                     'INVULN', (220, 220, 220)))
        return
    # Resistenz anwenden
    resist = e.resistances.get(dmg_type, 0.0)
    # L-05 (Update #47): Armour-Break reduziert Physical-Resist additiv.
    # 5 Stacks × 10 % = bis zu −50 % Physical-Resist (Phys-Dmg schlägt durch).
    if dmg_type == 'physical' and 'armour_break' in e.status:
        from .constants import STATUS_EFFECTS
        per_stack = STATUS_EFFECTS['armour_break'].get(
            'armour_break_per_stack', 0.10)
        resist = max(0.0, resist - e.status['armour_break']['stacks'] * per_stack)
    dmg = dmg * (1.0 - min(0.75, resist))
    # Update #34: Stun-Payoff — Heavy-Stunned-Targets nehmen 2× Damage.
    # Lore: Heavy-Stun = „Payoff-Phase" (POE2 L-04).
    payoff_visible = False
    if getattr(e, 'stun_timer', 0) > 0 and getattr(e, 'heavy_stunned', False):
        dmg *= 2.0
        payoff_visible = True
    # Combo-System (L-09): Frozen-Target → Cold-Damage ×1.5 (Shatter);
    # Burning-Target → Fire-Damage ×1.3 (Cremation); Shocked → Lightning ×1.4.
    status = getattr(e, 'status', {})
    if dmg_type == 'cold' and 'frost' in status:
        dmg *= 1.5
        payoff_visible = True
    elif dmg_type == 'fire' and 'burn' in status:
        dmg *= 1.3
    elif dmg_type == 'lightning' and 'shock' in status:
        dmg *= 1.4
    elif dmg_type == 'chaos' and 'poison' in status:
        dmg *= 1.25
    # Brittle: extra crit chance gegen verspröde Ziele
    if not crit and 'brittle' in e.status:
        from .constants import STATUS_EFFECTS
        bonus = STATUS_EFFECTS['brittle'].get('crit_taken_bonus', 0.1)
        bonus *= e.status['brittle']['stacks']
        if random.random() < bonus:
            crit = True
            crit_mult = progression.effective(game.player)['crit_mult']
            dmg *= crit_mult
    # Sapped: das Ziel verursacht weniger Damage — wirkt aktuell als
    # +Damage-Taken-Mod (Player-side wäre Negative, hier auf Enemy positiv).
    # Lore-Briefing 3.2: „Sapped — less damage" → wir interpretieren als
    # +15% Damage Taken (alternative Lesart, balance-konsistent).
    if 'sapped' in e.status:
        from .constants import STATUS_EFFECTS
        sap_mult = 1.0 + (1.0 - STATUS_EFFECTS['sapped'].get('dmg_dealt_mult', 0.85))
        sap_mult = 1.0 + (sap_mult - 1.0) * e.status['sapped']['stacks']
        dmg *= sap_mult

    # PLAN L-Block: Auto-Ailment-Apply basierend auf damage_type-Tag.
    # Macht die Engine konsistent mit dem POE2-Briefing 3.2 (Fire→Ignite,
    # Cold→Freeze/Chill, Lightning→Shock, Physical→Bleed, Chaos→Poison).
    # Cold-Crit zusätzlich Brittle, Chaos-Crit zusätzlich Sapped.
    try:
        from . import effects as _fx
        _fx.apply_ailments_from_tags(game, e, {dmg_type}, is_crit=crit)
    except Exception:
        pass
    # L-05 (Update #47): Schwere Phys-Hits (≥30 dmg, oder Crit) haben 30 %
    # Armour-Break-Chance. Maces (warrior/monk) +20 % Bonus.
    if dmg_type == 'physical' and (dmg >= 30 or crit):
        ab_chance = 0.30
        if game.player.cls in ('warrior', 'monk'):
            ab_chance += 0.20
        if random.random() < ab_chance:
            try:
                from . import effects as _fx2
                _fx2.apply(game, e, 'armour_break', stacks=1)
            except Exception:
                pass
    # L-06 (Update #47): Pin-Trigger bei vollen Frost-Stacks.
    if 'frost' in e.status:
        from .constants import STATUS_EFFECTS
        max_st = STATUS_EFFECTS['frost'].get('max_stacks', 5)
        if e.status['frost']['stacks'] >= max_st and 'pinned' not in e.status:
            try:
                from . import effects as _fx3
                _fx3.apply(game, e, 'pinned', stacks=1)
                game.floaters.append(Floater(
                    e.pos.x, e.pos.y - e.radius - 22,
                    'PINNED!', (140, 200, 240), big=True))
            except Exception:
                pass
        # V-02 (Update #168): Ice-Surface bei Frost-Stack >=3.
        # Decal unter dem Mob als persistent Boden-Kristall.
        if e.status['frost']['stacks'] >= 3 and not getattr(
                e, '_ice_decal_spawned', False):
            try:
                surf_fx = getattr(game, 'surface_fx', None)
                if surf_fx is not None:
                    surf_fx.spawn_ice_crack(
                        e.pos.x, e.pos.y, radius=72)
                    e._ice_decal_spawned = True
            except Exception:
                pass

    # PLAN J-08: Meta-Trigger-Event bei Crit (Cast-on-Crit).
    if crit:
        try:
            from . import gems as _g
            _g.trigger_meta_event(game.player, _g.TriggerEvent.ON_CRIT,
                                   game=game, target=e)
        except Exception:
            pass

    # Boss-Shield (PHASE-LAYER): erst Phase-Shield brechen.
    # NOTE: e.shield und e.shield_hp (PLAN F-12, weiter unten) sind ZWEI
    # separate Shield-Layer — e.shield ist Boss-Phase-Shield (max-basiert,
    # Phase-Trigger), e.shield_hp ist Brute/Glaslord-Guardian-Buffer
    # (einmalig, kein Regen). Bei Brute-Bossen koennen beide aktiv sein:
    # zuerst Phase-Shield, dann Guardian-HP, dann HP. Audit #179 A.6.
    if e.shield > 0:
        absorbed = min(e.shield, dmg)
        e.shield -= absorbed
        dmg -= absorbed
        # Particle-Feedback am Schild
        game.spawn_particles(e.pos.x, e.pos.y, 3, (160, 200, 255),
                             life_max=0.3, size_max=3)
        if e.shield <= 0 and e.is_boss:
            snd.play('boss_shield')
            game.toast(f'Schild gebrochen!', (160, 200, 255))
        if dmg <= 0:
            game.floaters.append(Floater(e.pos.x, e.pos.y - e.radius - 8,
                                         f'-{int(absorbed)}', (160, 200, 255)))
            return

    # PLAN O-06 (Update #100): Hit-Reaction in 4 Richtungen.
    # Hit-Direction wird aus Player→Enemy-Vector berechnet, in Sprite-Rig
    # geschrieben. Damit kann der Renderer per-Frame eine richtungs-
    # abhängige Sprite-Verschiebung anwenden (knockback + flinch).
    try:
        from .sprites import get_rig
        rig = get_rig(e)
        dx_h = e.pos.x - game.player.pos.x
        dy_h = e.pos.y - game.player.pos.y
        # Dominant axis → kardinale Richtung
        if abs(dx_h) > abs(dy_h):
            rig.last_hit_dir = 'E' if dx_h > 0 else 'W'
        else:
            rig.last_hit_dir = 'S' if dy_h > 0 else 'N'
        # Hit-Offset entgegen der Hit-Direction (visueller Flinch)
        push_mag = 4 + min(8, dmg / 20)
        d_total = max(1.0, (dx_h * dx_h + dy_h * dy_h) ** 0.5)
        rig.hit_offset_x = (dx_h / d_total) * push_mag
        rig.hit_offset_y = (dy_h / d_total) * push_mag
    except Exception:
        pass
    # PLAN F-12 (Update #96): Shield-HP absorbs Damage zuerst.
    # Wenn der Shield bricht, gibt es einen visuellen + Audio-Cue.
    shield = getattr(e, 'shield_hp', 0)
    if shield > 0:
        absorbed_sh = min(shield, dmg)
        e.shield_hp = shield - absorbed_sh
        dmg -= absorbed_sh
        game.floaters.append(Floater(e.pos.x, e.pos.y - e.radius - 6,
                                       f'-{int(absorbed_sh)} ◊',
                                       (160, 200, 255)))
        if e.shield_hp <= 0 and shield > 0:
            # Shield gerade gebrochen
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - e.radius - 18,
                'BARRIERE BRICHT!', (180, 220, 255), big=True))
            game.spawn_particles(e.pos.x, e.pos.y, 18,
                                  (200, 230, 255),
                                  life_max=0.8, size_max=5)
            try:
                snd.play('hit_heavy', volume=0.6)
            except Exception:
                pass
        if dmg <= 0:
            e.hit_flash = 0.10
            return
    e.hp -= dmg
    e.hit_flash = 0.15
    # M-03 (Update #64): Hit-Shake skill-tier-skaliert.
    # Stronger hits (crit / hi-damage / boss) → mehr Shake + Hit-Decal-Spots.
    # Briefing M.3: „Hit-Decals & Screen-Shake skill-tier-skaliert".
    if dmg >= 50 or (crit and dmg >= 20) or e.is_boss and dmg >= 30:
        shake_amt = 6 if dmg < 100 else (10 if dmg < 200 else 14)
        game.shake = max(game.shake, shake_amt)
        # Hit-Decal-Splash: kleine Boden-Mark am Hit-Point
        for _ in range(min(8, int(dmg / 30))):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(120, 280)
            game.particles_push(
                e.pos.x, e.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                (140, 30, 30), random.uniform(0.5, 1.0),
                random.uniform(2, 4), gravity=180)
    # Update #44: Salzgeist blinkt bei 25 % der Hits ein paar Pixel weiter
    if e.type_key == 'salzgeist' and not e.dying and random.random() < 0.25:
        from pygame.math import Vector2 as _V
        ang = random.uniform(0, math.tau)
        new_x = e.pos.x + math.cos(ang) * random.uniform(50, 90)
        new_y = e.pos.y + math.sin(ang) * random.uniform(50, 90)
        # Nur wenn Ziel walkable ist
        if game.grid is None or not game.grid.collide_circle(
                new_x, new_y, e.radius):
            # Particles am Start + Ende für Telegraph
            game.spawn_particles(e.pos.x, e.pos.y, 14, (220, 240, 255),
                                  life_max=0.5, size_max=4)
            e.pos.x, e.pos.y = new_x, new_y
            game.spawn_particles(e.pos.x, e.pos.y, 14, (220, 240, 255),
                                  life_max=0.5, size_max=4)
            e.hit_flash = 0.3  # längeres Flicker
    # Update #34: Stun-Buildup pro Schlag
    # Phys-Damage → mehr Buildup. Warrior (Mace-Lineage) ×1.5.
    # Bei 100 → Heavy-Stun (1.5s lange Disable).
    if not e.dying and hasattr(e, 'stun_buildup'):
        buildup_amount = 8.0
        if dmg_type == 'physical':
            buildup_amount = 14.0
        if game.player.cls in ('warrior', 'monk'):
            buildup_amount *= 1.4  # Mace/Quarterstaff-Bonus
        if crit:
            buildup_amount *= 1.5
        e.stun_buildup = min(e.stun_buildup_max,
                              getattr(e, 'stun_buildup', 0) + buildup_amount)
        # Heavy-Stun-Trigger
        if e.stun_buildup >= e.stun_buildup_max and not e.heavy_stunned:
            e.heavy_stunned = True
            e.stun_timer = max(e.stun_timer, 1.5)
            e.stun_buildup = 0  # zurücksetzen
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - e.radius - 12,
                'STUNNED!', (255, 240, 120), big=True))
            game.spawn_particles(e.pos.x, e.pos.y - e.height // 2,
                                  18, (255, 240, 120),
                                  life_max=0.7, size_max=5)
            # Update #131 (Y-02): erster Stun → Mechanik-Hint
            try:
                from . import tutorial as _tut
                _tut.mech_hint(game, 'first_stun')
            except ImportError:
                pass
    game.spawn_particles(e.pos.x, e.pos.y, 6, e.glow, life_max=0.4)
    # Update #78 O-12: Richtungsabhängiges Blut-Spray — Spritzer fliegt
    # in Hit-Richtung (vom Angreifer weg) in einem ±35° Cone.
    # Lore: Bestiarium-Realismus — Salzgeister bluten silbrig, Glaslord
    # zerspringt nicht, aschenbrut sprüht Asche statt Blut.
    p_pos = game.player.pos
    dx_h = e.pos.x - p_pos.x
    dy_h = e.pos.y - p_pos.y
    d_h = (dx_h * dx_h + dy_h * dy_h) ** 0.5
    if d_h < 0.01:
        base_ang = random.uniform(0, math.tau)
    else:
        base_ang = math.atan2(dy_h, dx_h)
    cone = math.radians(35)
    # Mob-spezifische Blut-Farbe (Lore-konform).
    _BLOOD_COLORS = {
        'salzgeist':   (200, 220, 240),  # silbrig-salzig
        'glaslord':    (180, 210, 240),  # glas-splitter
        'aschenbrut':  (50, 30, 26),     # asche
        'wurzelhueter':(80, 130, 60),    # pflanzlich
    }
    blood_col = _BLOOD_COLORS.get(getattr(e, 'type_key', ''), (160, 30, 30))
    blood_n = 8 if crit else 4
    for _ in range(blood_n):
        ang = base_ang + random.uniform(-cone, cone)
        sp = random.uniform(110, 230) if crit else random.uniform(80, 200)
        game.particles_push(
            e.pos.x, e.pos.y,
            math.cos(ang) * sp, math.sin(ang) * sp,
            blood_col, random.uniform(0.4, 0.8),
            random.uniform(2, 4), gravity=150)
    # Crit: zusätzlicher Arterien-Spurt (lange Linie 3 Partikel hintereinander)
    if crit:
        for k in range(3):
            spurt_sp = 260 + k * 30
            game.particles_push(
                e.pos.x, e.pos.y,
                math.cos(base_ang) * spurt_sp,
                math.sin(base_ang) * spurt_sp,
                blood_col, 0.55,
                random.uniform(3, 5), gravity=120)
    # Schadenstyp-Farbe
    from .constants import DAMAGE_TYPES
    type_color = DAMAGE_TYPES.get(dmg_type, {}).get('color', (255, 100, 100))
    color = (255, 220, 60) if crit else type_color
    text = f'{int(dmg)}!' if crit else int(dmg)
    if resist > 0.5:
        text = f'{text} ▼'
    fl = Floater(e.pos.x, e.pos.y - e.radius - 8, text, color, crit=crit)
    # Update #34: Payoff-Indikator-Floater bei Combo/Stun-Payoff
    if payoff_visible:
        game.floaters.append(Floater(
            e.pos.x, e.pos.y - e.radius - 24,
            'PAYOFF!', (255, 240, 120)))
    if crit:
        # Update #96: Crit-Sound-Variety — Layer Crit + Material-Impact +
        # leichte Pitch-Variation via Channel.
        snd.play('crit', volume=0.85)
        try:
            snd.play_with_fallback('aoe_impact', 'hit_heavy',
                                     volume=0.4)
        except Exception:
            pass
        # Update #127: Klassen-Crit-Voice (z.B. „YES!", „Spalte!")
        # Lore-Voice aus voice_registry/cls_<klasse>/crit.
        try:
            # Update #148: Voice 0.7 → 0.35 (User-Report „zu laut")
            snd.play_class_voice(game.player.cls, 'crit', volume=0.35)
        except Exception:
            pass
        # Update #32: Crit-Counter
        if hasattr(game.player, 'prog_crits_dealt'):
            game.player.prog_crits_dealt += 1
        # Update #131 (Y-02): erster Crit → Mechanik-Hint
        try:
            from . import tutorial as _tut
            _tut.mech_hint(game, 'first_crit')
        except ImportError:
            pass
        # Update #96: Hit-Stop bei Crit verstärkt (0.12 → 0.18 s), Shake 14.
        if hasattr(game, 'slow_mo_left'):
            game.slow_mo_left = max(game.slow_mo_left, 0.18)
        game.shake = max(game.shake, 14)
        # Update #140 (X-04): Crit-Zoom-Pull bei großen Crits oder
        # Boss-Crits.  Camera wird kurz Richtung Target gepullt
        # (synchron mit Hitstop-slow_mo).
        if dmg >= 30 or getattr(e, 'is_boss', False):
            if hasattr(game, 'trigger_crit_zoom'):
                game.trigger_crit_zoom(e.pos.x, e.pos.y)
        # Update #32: Klassen-spezifisches Crit-Impact-Sample (leise).
        cls = game.player.cls
        if cls in ('warrior', 'druid', 'huntress'):
            snd.play(f'axe_metal_{random.randint(1, 4)}', volume=0.35)
        elif cls == 'ranger':
            snd.play(f'arrow_impact_{random.randint(1, 2)}', volume=0.4)
        # Crit-Flash-Tint auf dem Screen
        if hasattr(game, 'crit_flash_t'):
            game.crit_flash_t = max(game.crit_flash_t, 0.18)
        # Hit-Stop: kurze Slow-Mo + Knockback am Gegner
        if hasattr(game, 'slow_mo_left'):
            game.slow_mo_left = max(game.slow_mo_left, 0.08)
        # Knockback: gegner wird vom Spieler weggeschoben
        dir_x = e.pos.x - game.player.pos.x
        dir_y = e.pos.y - game.player.pos.y
        d = (dir_x * dir_x + dir_y * dir_y) ** 0.5
        if d > 0:
            game.move_entity(e, dir_x / d * 14, dir_y / d * 14)
    else:
        if random.random() < 0.4:
            snd.play('hit_heavy' if dmg >= 30 else 'hit',
                       volume=0.35)  # Update #38: leiser
    game.floaters.append(fl)

    # Schurken-Talent: Giftklingen-Chance
    p = game.player
    eff = progression.effective(p)
    if dmg_type == 'physical' and eff.get('poison_chance', 0) > 0:
        if random.random() < eff['poison_chance']:
            from . import effects as fx
            fx.apply(game, e, 'poison', stacks=2)

    if e.hp <= 0:
        # A-04 (Update #47): Damage-Type-Tag für Death-Sound-Layer.
        e._killed_by_dmg_type = dmg_type
        kill_enemy(game, e)


def _trigger_on_death(game, e):
    """Bestiarium-spezifisches Death-Behavior (Lore-Kanon Bestiarium #1–5).

    Wird aus kill_enemy direkt nach den Standard-Death-Effekten gefeuert.
    Salt-Explosion und Slow-Pool nutzen das Decal-System (C-05/C-06).
    """
    behavior = getattr(e, 'on_death_behavior', None)
    if not behavior:
        return
    if behavior == 'salt_explosion':
        # Salzgekreuzter zerfällt zu Salzkristallen, die nach 2s als AoE
        # explodieren — Lore: „vollendet das Vergessen".
        from . import effects as _fx
        from pygame.math import Vector2 as _V

        damage = e.dmg * 1.2
        explode_pos = _V(e.pos.x, e.pos.y)
        explode_color = (220, 230, 240)  # salt-white

        def _on_salt_explode(g, decal, _d=damage, _p=explode_pos,
                             _col=explode_color):
            if (g.player.pos - _p).length() <= decal.radius:
                g.damage_player(_d)
            for ang_i in range(36):
                ang = (ang_i / 36) * math.tau
                g.particles_push(
                    _p.x, _p.y,
                    math.cos(ang) * 220, math.sin(ang) * 220,
                    _col, 0.8, 5)
            g.shake = max(g.shake, 6)

        _fx.spawn_ground_decal(
            game, e.pos.x, e.pos.y, radius=58,
            kind=_fx.DECAL_KIND.DEADLY,
            windup=2.0, lifetime=0.0,
            on_activate=_on_salt_explode)

    elif behavior == 'tiny_slow_pool':
        # Krustenkrabbe → Salzwasser-Pfütze (Slow-Field, kein Damage)
        game.spawn_particles(e.pos.x, e.pos.y, 18, (160, 200, 230),
                             life_max=1.5, size_max=6, gravity=20)
        # Mini-Heal-Field-style entry (heal_fields ist Slow-/Effect-Pool im Game)
        if hasattr(game, 'heal_fields'):
            from pygame.math import Vector2 as _V
            # Nutzt heal_fields-Pool für Render, heilt aber nicht
            # (heal_per_sec=0) — Slow-Effekt wäre eigene Mechanik.
            game.heal_fields.append({
                'pos': _V(e.pos.x, e.pos.y),
                'radius': 60,
                'time_left': 4.0,
                'kind': 'salt_slow',
                'color': (160, 200, 230),
                'heal_per_sec': 0,
            })

    elif behavior == 'silent_collapse':
        # Ertrunkenes Echo: keine zusätzliche Mechanik — der death_audio
        # 'roar' wurde bereits gespielt. Visueller Nebel-Effekt.
        game.spawn_particles(e.pos.x, e.pos.y, 24, (180, 200, 220),
                             life_max=1.2, size_max=4, gravity=-30)

    elif behavior == 'death_pop':
        # Möwen-Schwarm: kleiner Federn-Pop + lautes Schreien
        for _ in range(20):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(60, 200)
            game.particles_push(
                e.pos.x, e.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp - 30,
                (240, 240, 230), random.uniform(0.4, 0.9),
                random.uniform(2, 4), gravity=60)

    elif behavior == 'ice_shatter':
        # Update #44: Glaslord zerspringt zu 5 radialen Eis-Splittern.
        # Jeder Splitter ist ein Frost-Projektil mit ×0.5 dmg.
        from .entities import Projectile
        for k in range(5):
            ang = (k / 5) * math.tau + random.uniform(-0.1, 0.1)
            game.projectiles.append(Projectile(
                e.pos.x, e.pos.y,
                math.cos(ang) * 280, math.sin(ang) * 280,
                e.dmg * 0.5, 'frostbolt', friendly=False,
                radius=7, life=1.0,
            ))
        game.spawn_particles(e.pos.x, e.pos.y, 30, (200, 230, 255),
                              life_max=0.7, size_max=5)
        game.shake = max(game.shake, 5)

    elif behavior == 'affix_detonate':
        # F-15 (Update #45)/#46: Detonating-Affix — 70 px Fire-AoE bei Tod
        # User-Bug „stirbt einfach so": jetzt mit 0.5 s Telegraph-Decal
        # statt instant damage. Radius 90 → 70, dmg 1.4× → 1.0×.
        from pygame.math import Vector2 as _V
        from . import effects as _fx
        burst_pos = _V(e.pos.x, e.pos.y)
        burst_dmg = e.dmg * 1.0

        def _on_detonate(g, decal, _p=burst_pos, _d=burst_dmg, _src=e):
            if (g.player.pos - _p).length() <= decal.radius:
                g.damage_player(_d, dmg_type='fire', source=_src)
            for _ in range(40):
                ang = random.uniform(0, math.tau)
                sp = random.uniform(140, 260)
                g.particles_push(
                    _p.x, _p.y,
                    math.cos(ang) * sp, math.sin(ang) * sp,
                    (255, 200, 60), random.uniform(0.5, 0.8),
                    random.uniform(3, 6), gravity=40)
            g.shake = max(g.shake, 10)
            try:
                snd.play('explosion_debris', volume=0.5)
            except Exception:
                pass

        _fx.spawn_ground_decal(
            game, burst_pos.x, burst_pos.y, radius=70,
            kind=_fx.DECAL_KIND.DEADLY,
            windup=0.5, lifetime=0.0,
            on_activate=_on_detonate, play_windup=False)

    elif behavior == 'fire_burst':
        # Update #44/#46: Aschen-Brut Death-Explosion mit 0.4 s Telegraph.
        # User-Bug „stirbt einfach so": Telegraph statt instant damage.
        from pygame.math import Vector2 as _V
        from . import effects as _fx
        burst_pos = _V(e.pos.x, e.pos.y)
        burst_dmg = e.dmg * 1.0

        def _on_burst(g, decal, _p=burst_pos, _d=burst_dmg, _src=e):
            if (g.player.pos - _p).length() <= decal.radius:
                g.damage_player(_d, dmg_type='fire', source=_src)
            for _ in range(28):
                ang = random.uniform(0, math.tau)
                sp = random.uniform(120, 240)
                g.particles_push(
                    _p.x, _p.y,
                    math.cos(ang) * sp, math.sin(ang) * sp,
                    (255, 130, 50), random.uniform(0.4, 0.7),
                    random.uniform(3, 5), gravity=60)
            for _ in range(10):
                g.spawn_particles(
                    _p.x + random.uniform(-15, 15),
                    _p.y + random.uniform(-15, 15),
                    1, (255, 200, 80), life_max=0.5, size_max=4,
                    friendly=False)
            g.shake = max(g.shake, 7)
            try:
                snd.play('explosion_debris', volume=0.4)
            except Exception:
                pass

        _fx.spawn_ground_decal(
            game, burst_pos.x, burst_pos.y, radius=50,
            kind=_fx.DECAL_KIND.DEADLY,
            windup=0.4, lifetime=0.0,
            on_activate=_on_burst, play_windup=False)


def _item_passes_loot_filter(game, item):
    """Update #201 (User-Bug-Fix): Gefilterte Rarities droppen gar nicht
    erst als Boden-Loot.

    Vorher: Commons droppten sichtbar, waren aber wegen des Default-
    Filters ('common', siehe Player.loot_filter) nicht aufhebbar — der
    Pickup-Code in game._update_loot uebersprang sie. Resultat: grauer
    Clutter am Boden, den der Spieler nicht anfassen konnte + unnoetige
    Render-Last. Jetzt wird der Filter schon beim Drop angewandt, genau
    wie in den meisten ARPGs (Loot-Filter blendet Drops aus).

    `loot_filter`:  'off' = alles | 'common' = Commons aus |
                    'magic' = alles unter Rare aus.
    """
    if item is None:
        return True
    flt = getattr(game.player, 'loot_filter', 'off')
    if flt == 'off':
        return True
    order = {'common': 0, 'magic': 1, 'rare': 2, 'unique': 3, 'mythic': 4}
    r = order.get(getattr(item, 'rarity', 'common'), 0)
    if flt == 'common' and r == 0:
        return False
    if flt == 'magic' and r < 2:
        return False
    return True


def kill_enemy(game, e):
    if e.dying:
        return
    e.dying = True
    e.death_timer = 0.0
    snd.play('death', volume=0.4)  # Update #38: war zu laut

    # Update #184: Moench-Atlas "Klang der Stille" — Kills refunden 12% max-MP
    try:
        from . import skill_atlas as _atl
        if _atl.has_keystone(game.player, 'kill_refunds_mana_12'):
            eff_p = progression.effective(game.player)
            refund = eff_p['mp_max'] * 0.12
            game.player.mp = min(eff_p['mp_max'],
                                 game.player.mp + refund)
    except Exception:
        pass

    # Update #X — Bestiarium-spezifischer Death-Sound (Phase-2-SFX-Pipeline)
    # Wenn der Mob ein bestiary_key hat, versuche <key>_death zu spielen.
    # Fallback ist still — generic 'death' oben hat bereits gespielt.
    bk = getattr(e, 'bestiary_key', None)
    if bk:
        snd.play(f'{bk}_death', volume=0.5)

    # J-12 (Update #65): Event-Bus — Enemy-Killed + Boss-Defeated
    try:
        from . import events as _ev
        _ev.publish(_ev.EventKey.ON_ENEMY_KILLED, game=game, enemy=e)
        if getattr(e, 'is_boss', False):
            _ev.publish(_ev.EventKey.ON_BOSS_DEFEATED, game=game, boss=e)
    except Exception:
        pass
    # AA-04 (Update #168): Telemetrie-Hook (opt-in via Setting).
    if getattr(e, 'is_boss', False):
        try:
            from . import telemetry as _tel
            _tel.record_boss_kill(
                game,
                boss_kind=getattr(e, 'bestiary_key', '?'),
                time_taken_s=getattr(game.player,
                                      'prog_play_time_s', 0.0))
        except Exception:
            pass
    # A-04 (Update #47): Damage-Type-Death-Sound-Layer.  Spielt einen leisen
    # Type-spezifischen Sound über den generischen 'death'-Trigger, sodass
    # Spieler die Todes-Ursache hört (Fire-Sizzle, Ice-Crack, Zap, …).
    DEATH_LAYER = {
        'fire':      ('cast_fire',      0.20),
        'cold':      ('cast_frost',     0.22),
        'lightning': ('cast_lightning', 0.22),
        'chaos':     ('aoe_impact',     0.18),
        'poison':    ('aoe_impact',     0.16),
        'physical':  ('hit_heavy',      0.22),
        'bleed':     ('hit_heavy',      0.20),
        'shadow':    ('aoe_impact',     0.18),
    }
    dt_killer = getattr(e, '_killed_by_dmg_type', None)
    layer = DEATH_LAYER.get(dt_killer)
    if layer is not None:
        try:
            snd.play_at(layer[0], (e.pos.x, e.pos.y),
                         (game.player.pos.x, game.player.pos.y),
                         volume=layer[1])
        except Exception:
            pass
    # Update #100 (PLAN A-03): Per-Damage-Type-Death-Sprite-Variant.
    # Cold-Shatter → 8 Polygon-Splitter fliegen radial weg.
    # Lightning-Spasm → 3 Zackelinien.
    # Fire-Ignite-Collapse → Glut-Cloud aufsteigend.
    # Bleed → extra Blut-Puddle.
    if dt_killer == 'cold':
        # 8 hexagonale „Eis-Scherben" als Particles mit longer lifetime
        for k in range(8):
            ang = (k / 8.0) * math.tau + random.uniform(-0.1, 0.1)
            sp = random.uniform(140, 260)
            game.particles_push(
                e.pos.x, e.pos.y - e.height * 0.3,
                math.cos(ang) * sp, math.sin(ang) * sp - 40,
                (200, 230, 255), random.uniform(0.8, 1.4),
                random.uniform(4, 6), gravity=140)
        # Frost-Crack-Sound
        try:
            snd.play_with_fallback('cast_frost', 'hit', volume=0.35)
        except Exception:
            pass
    elif dt_killer == 'lightning':
        # 3 Zackel-Linien (Particles in Zickzack-Pattern)
        for _ in range(3):
            ang = random.uniform(0, math.tau)
            for step in range(6):
                offset = random.uniform(-0.6, 0.6)
                a = ang + offset
                game.particles_push(
                    e.pos.x + math.cos(ang) * step * 8,
                    e.pos.y + math.sin(ang) * step * 8,
                    math.cos(a) * 40, math.sin(a) * 40 - 20,
                    (200, 220, 255), 0.4,
                    random.uniform(2, 3))
    elif dt_killer == 'fire':
        # Glut-Cloud aufsteigend (4 lange-life Particles)
        for k in range(20):
            game.particles_push(
                e.pos.x + random.uniform(-12, 12),
                e.pos.y,
                random.uniform(-20, 20),
                random.uniform(-90, -40),
                (255, 140, 60), random.uniform(1.0, 1.8),
                random.uniform(3, 5), gravity=-30)
    # F-15 (Update #45): Soul-Eater-Affix in der Nähe → stärker
    # Audit #179 B.5: SpatialGrid-Query statt linear.
    _grid = getattr(game, 'enemy_grid', None)
    _soul_iter = (_grid.query_radius(e.pos.x, e.pos.y, 200)
                  if _grid is not None else game.enemies)
    for ally in _soul_iter:
        if ally is e or ally.dying:
            continue
        if 'soul_eater' in getattr(ally, 'affixes', ()):
            if (ally.pos - e.pos).length() < 200:
                ally.dmg *= 1.05
                ally.hp = min(ally.hp_max, ally.hp + ally.hp_max * 0.05)
                game.spawn_particles(ally.pos.x, ally.pos.y - 10, 6,
                                      (180, 100, 220),
                                      life_max=0.5, size_max=3,
                                      friendly=False)
    # D-10 (Update #47): Alpha-Mob-Death-Pack-Reaktion.
    # Wenn ein Elite/Champion/Affix-Mob stirbt, reagieren umliegende Mobs:
    # 50 % Pack wird FEARFUL (Backstep, ‑30 % DMG für 2.5 s),
    # 50 % Pack wird ENRAGED (+30 % DMG/SPD für 2.5 s).
    # Entscheidung pro Alpha-Death einmalig (kohärentes Pack-Verhalten).
    is_alpha = (e.is_boss or e.elite or
                 getattr(e, 'affix_tier', None) in ('rare', 'unique'))
    if is_alpha and not e.is_boss:  # Boss-Tod hat eigene Death-Sequence
        is_enraged = random.random() < 0.5
        reaction_type = 'enraged' if is_enraged else 'fearful'
        radius = 220
        # Audit #179 B.5: SpatialGrid-Query statt linear.
        _grid2 = getattr(game, 'enemy_grid', None)
        _pack_iter = (_grid2.query_radius(e.pos.x, e.pos.y, radius)
                      if _grid2 is not None else game.enemies)
        for ally in _pack_iter:
            if ally is e or ally.dying:
                continue
            if (ally.pos - e.pos).length() < radius:
                ally._pack_reaction_type = reaction_type
                ally._pack_reaction_left = 2.5
                if is_enraged:
                    ally._dmg_mult = 1.3
                    ally._speed_mult = 1.25
                    label = 'WUT!'
                    col = (255, 100, 60)
                else:
                    ally._dmg_mult = 0.7
                    ally._speed_mult = 0.85
                    label = 'FURCHT!'
                    col = (140, 180, 220)
                # Floater ist bereits global oben (Z. 8) importiert — kein
                # local-import nötig (würde sonst Python's UnboundLocalError
                # für ALLE Floater-Zugriffe in kill_enemy triggern).
                game.floaters.append(Floater(
                    ally.pos.x, ally.pos.y - 30, label, col,
                    big=False, life=1.0))
                game.spawn_particles(ally.pos.x, ally.pos.y - 8, 6, col,
                                      life_max=0.4, size_max=3,
                                      friendly=False)
    # Update #32: Progression-Tracker
    p = game.player
    p.prog_kills_total = getattr(p, 'prog_kills_total', 0) + 1
    if e.is_boss:
        p.prog_kills_boss = getattr(p, 'prog_kills_boss', 0) + 1
        p.class_mastery_xp = getattr(p, 'class_mastery_xp', 0) + 50
        # Dragon-Roar bei Boss-Death — sehr leise, nur Atmosphere
        try:
            snd.play('epic_dragon_roar', volume=0.25)
        except Exception:
            pass
    elif getattr(e, 'is_mini_boss', False):
        p.prog_kills_mini = getattr(p, 'prog_kills_mini', 0) + 1
        p.class_mastery_xp = getattr(p, 'class_mastery_xp', 0) + 15
    elif e.elite:
        p.prog_kills_elite = getattr(p, 'prog_kills_elite', 0) + 1
        p.class_mastery_xp = getattr(p, 'class_mastery_xp', 0) + 5
    else:
        p.class_mastery_xp = getattr(p, 'class_mastery_xp', 0) + 1
    # Class-Mastery-Rank Milestones (0..9)
    MILESTONES = [0, 50, 150, 400, 900, 1800, 3500, 6000, 10000, 16000]
    old_rank = sum(1 for m in MILESTONES
                    if (p.class_mastery_xp - getattr(p, '_last_kill_xp', 0)) >= 0
                    and (getattr(p, '_last_kill_xp', 0) >= m))
    new_rank = sum(1 for m in MILESTONES if p.class_mastery_xp >= m)
    if new_rank > old_rank:
        from . import aspects as _asp
        pal = _asp.aspect_palette(p.cls)
        try:
            game.push_event_notification(
                'levelup',
                f'KLASSEN-MEISTERSCHAFT {new_rank}',
                sub=f'{pal["domain"]}-Aspekt erkennt dich.',
                color=pal['halo'], duration=4.0)
            snd.play('levelup_fanfare', volume=0.4)
        except Exception:
            pass
    p._last_kill_xp = p.class_mastery_xp

    # Bestiarium-Death-Audio (Lore-Hook)
    death_audio = getattr(e, 'death_audio', None)
    if death_audio:
        try:
            snd.play(death_audio, volume=0.6)
        except Exception:
            pass

    # PLAN J-08: Cast-on-Minion-Death-Trigger (wenn Mob ein Minion war).
    # Minion-Heuristik: Skelette/Knochen vom Witch-Build, oder e.is_minion-Flag.
    if getattr(e, 'is_minion', False):
        try:
            from . import gems as _g
            _g.trigger_meta_event(game.player,
                                   _g.TriggerEvent.ON_MINION_DEATH,
                                   game=game, target=e)
        except Exception:
            pass

    # PLAN F-13/F-14: on_death_behavior Dispatch.
    # Lore-Anker: Bestiarium definiert pro Mob konkrete Death-Effekte.
    _trigger_on_death(game, e)

    # Lore-Floater: Bestiarium-Quote als kleiner subtiler Hinweis
    # (1. Treffer ein Mob → Codex-Marker; siehe CHANGELOG offene Punkte).
    lore = getattr(e, 'lore_quote', None)
    if lore and not getattr(game, '_bestiary_quoted', set()).__contains__(
            getattr(e, 'bestiary_key', None)):
        # Pro Bestiarium-Key nur einmal pro Session anzeigen.
        if not hasattr(game, '_bestiary_quoted'):
            game._bestiary_quoted = set()
        key = getattr(e, 'bestiary_key', None)
        if key:
            game._bestiary_quoted.add(key)
            # Erstes Vorkommen → kurzer Toast mit Display-Name.
            name = getattr(e, 'display_name', None) or key
            game.toast(f'Erste Begegnung: {name}', (200, 180, 140))
    # Blut-Pfütze am Todesort
    # Update #136 (V-05): Lore-spezifische Pool-Farbe + Kind aus Bestiarium-
    # Realismus.  Salzgeist hinterlässt Salzkristalle, Glaslord Glas-Splitter,
    # Aschenbrut Asche-Pool, Wurzelhüter Pflanzen-Saft.
    from .weather import BloodPool
    if hasattr(game, 'blood_pools'):
        _BLOOD_LORE = {
            'salzgeist':    ((200, 220, 240), 'salt_crystal'),
            'glaslord':     ((180, 210, 240), 'salt_crystal'),  # Glas-Splitter wie Salz
            'aschenbrut':   ((50, 30, 26),    'ash'),
            'wurzelhueter': ((80, 130, 60),   'sap'),
        }
        spec = _BLOOD_LORE.get(getattr(e, 'type_key', ''))
        # Pool-Size skaliert mit Mob-Radius — größere Mobs = größere Pfützen
        pool_size = e.radius * 0.9 + random.uniform(-3, 5)
        # Boss-Pools sind ~1.5× größer und leben länger
        is_boss = getattr(e, 'is_boss', False) or getattr(
            e, 'is_mini_boss', False)
        if is_boss:
            pool_size *= 1.5
            pool_life = 25.0
        else:
            pool_life = 15.0   # PLAN V-05: ~15s, „trocknet aus"
        if spec is not None:
            game.blood_pools.append(BloodPool(
                e.pos.x + random.uniform(-6, 6),
                e.pos.y + random.uniform(-6, 6),
                pool_size, color=spec[0], life=pool_life, kind=spec[1]))
        else:
            game.blood_pools.append(BloodPool(
                e.pos.x + random.uniform(-6, 6),
                e.pos.y + random.uniform(-6, 6),
                pool_size, life=pool_life))
    # PLAN J-10: Boss/Mini-Boss-Drops einen Uncut Memory-Shard.
    # Lore: gefundene Tropfen aus dem Glasgoldenen Zeitalter.
    if e.is_boss or getattr(e, 'is_mini_boss', False):
        p_player = game.player
        if not hasattr(p_player, 'uncut_gems'):
            p_player.uncut_gems = {}
        # Boss-Level = Player-Level + 2 (etwas höher)
        drop_lvl = max(1, p_player.level + (2 if e.is_boss else 0))
        p_player.uncut_gems[drop_lvl] = p_player.uncut_gems.get(drop_lvl, 0) + 1
        game.toast(f'Uncut Memory-Shard Lvl {drop_lvl} gefunden.',
                    (255, 200, 100))
        # Update #82: Boss/Mini-Boss gibt 5/3 Flask-Charges.
        try:
            if e.is_boss:
                game._grant_flask_charges(5.0)
            elif getattr(e, 'is_mini_boss', False):
                game._grant_flask_charges(3.0)
        except Exception:
            pass
        # Update #96 + #106 (Audit F-002): Vital-Orb-Drops mit Walkable-
        # Check, damit Orbs nicht in Walls/Decor verschwinden.
        try:
            n_orbs = 3 if e.is_boss else 1
            amt = 35 if e.is_boss else 18
            for k in range(n_orbs):
                ang = random.uniform(0, math.tau)
                r = random.uniform(20, 50)
                ox = e.pos.x + math.cos(ang) * r
                oy = e.pos.y + math.sin(ang) * r
                # Wall-Check: nutze grid.find_walkable_near falls vorhanden
                if game.grid is not None:
                    if not game.grid.is_walkable_world(ox, oy):
                        wk = game.grid.find_walkable_near(ox, oy)
                        if wk is not None:
                            ox, oy = wk
                        else:
                            # Kein walkable-Spot in der Nähe → Boss-Position
                            ox, oy = e.pos.x, e.pos.y
                game.loot.append(Loot(ox, oy, vital_orb=True,
                                       vital_amount=amt))
        except Exception:
            pass
        # Update #75 H-17: Boss garantiert +1 Orb-of-Regret, Mini-Boss 33%.
        # Lore: aus dem Spiegelhof gewobene Erinnerungssphäre.
        if e.is_boss or random.random() < 0.33:
            p_player.orbs_of_regret = getattr(
                p_player, 'orbs_of_regret', 0) + 1
            game.toast('Orb-of-Regret erhalten (Spiegelhof-Reflexion).',
                        (220, 180, 240))
    elif e.elite and random.random() < 0.08:
        # Update #75: Elites ~8% Drop-Chance.
        p_player = game.player
        p_player.orbs_of_regret = getattr(
            p_player, 'orbs_of_regret', 0) + 1
        game.toast('Orb-of-Regret erhalten.', (220, 180, 240))
    # Update #82: Elite +2.0 Charges, normales Mob +0.5
    try:
        if e.elite:
            game._grant_flask_charges(2.0)
        else:
            game._grant_flask_charges(0.5)
    except Exception:
        pass

    # Boss-Death-Cinematic: Slow-Mo + großer Flash + Explosion + Voice
    if e.is_boss:
        game.slow_mo_left = 1.5
        game.boss_flash = 1.0
        game.shake = max(game.shake, 16)
        # Update #140 (X-05): Cinematic-Camera-Pan zum sterbenden Boss
        # für 1.8 s.  Slow-Mo + Camera-Follow-Override.
        if hasattr(game, 'trigger_boss_death_pan'):
            game.trigger_boss_death_pan(e)
        # Update #33: Boss-Death-Banner-Notification (visible progression)
        try:
            game.push_event_notification(
                'levelup',
                f'{e.boss_name.upper()} GEFALLEN',
                sub=f'Akt {game.player.level // 5 + 1} schreitet voran...',
                color=(243, 213, 114), duration=4.0)
        except Exception:
            pass
        # Klassen-Voice-Line (Lore-Anker zu VELGRAD_VOICE_LINES_POOL.md)
        # Update #146 + #148 (User-Report „Schöner Tod kommt immer noch
        # richtig oft"):
        #   1. Cooldown 8 s → **90 s** (Boss-Kill ist seltenes Event)
        #   2. Nur echte Story-Bosse triggern — Roaming-Boss + Mini-Boss
        #      bekommen KEINE boss_kill-Voice (sonst Spam in Dungeons
        #      mit 5+ Mini-Bossen).
        #   3. „Last-quote"-Memo verhindert dass dieselbe Quote-Line
        #      zweimal in Folge erscheint.
        is_real_story_boss = (e.is_boss
                               and not getattr(e, 'is_mini_boss', False)
                               and not getattr(e, '_roaming', False)
                               and not getattr(e, '_invasion', False))
        if is_real_story_boss:
            import time as _t
            now = _t.time()
            last = getattr(game, '_class_voice_last_t', 0.0)
            if now - last > 90.0:
                game._class_voice_last_t = now
                try:
                    from . import quotes as _q
                    last_quote = getattr(game,
                                          '_class_voice_last_quote', None)
                    # Bis zu 3 Versuche eine NEUE Quote zu picken
                    vl = None
                    for _ in range(3):
                        cand = _q.class_voice_line(
                            game.player.cls, 'boss_kill')
                        if cand and cand != last_quote:
                            vl = cand
                            break
                        vl = cand
                    if vl:
                        game._class_voice_last_quote = vl
                        game.toast(vl, (255, 220, 100))
                except Exception:
                    pass
        # Massive Partikel-Explosion
        game.spawn_particles(e.pos.x, e.pos.y, 120,
                             e.glow, life_max=1.5, size_max=10, gravity=40)
        game.spawn_particles(e.pos.x, e.pos.y, 60,
                             (255, 255, 255), life_max=0.8, size_max=6)
        for k in range(36):
            ang = (k / 36) * math.tau
            game.particles_push(
                e.pos.x, e.pos.y,
                math.cos(ang) * 320, math.sin(ang) * 320,
                e.color, 1.0, 5)
        snd.play('boss_intro', volume=0.9)

    game.spawn_particles(e.pos.x, e.pos.y, 22, e.color,
                         life_max=0.9, size_max=5, gravity=60)
    game.spawn_particles(e.pos.x, e.pos.y, 8, (255, 255, 255))
    # Mehr Blut beim Tod
    for _ in range(14):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(40, 220)
        game.particles_push(
            e.pos.x, e.pos.y,
            math.cos(ang) * sp, math.sin(ang) * sp - 50,
            (140, 20, 20), random.uniform(0.5, 1.0),
            random.uniform(2, 4), gravity=180)

    gold = random.randint(*e.gold_range)
    if gold > 0:
        game.loot.append(Loot(e.pos.x + random.uniform(-20, 20),
                              e.pos.y + random.uniform(-20, 20),
                              gold=gold))

    # Update #41: Item-Drop-Chance deutlich erhöht — User-Feedback
    # „Loot dropt zu wenig". Normal-Mobs 8%→22%, Elite 50%→70%,
    # Mini-Boss eigene 80%×2-Items-Chance, Boss 6-10 statt 5-8.
    drop_chance = 0.22
    rarity_boost = 0
    if e.elite:
        drop_chance = 0.70
        rarity_boost = 8
    # Update #121-Fix: game.wave existiert nicht mehr (Survival entfernt).
    # Loot-ilvl basiert jetzt auf player.level — natürliche Progression.
    # Tier-3-Dungeon-Boost wird über `current_tier` mit eingepreist.
    ilvl = max(1, getattr(game.player, 'level', 1)
                + (getattr(game, 'current_tier', 1) - 1) * 2)
    if getattr(e, 'is_mini_boss', False):
        # Mini-Boss garantiert 2-3 items
        for _ in range(random.randint(2, 3)):
            it = items_mod.make_item(ilvl=ilvl, rarity_boost=12)
            if not _item_passes_loot_filter(game, it):
                continue
            game.loot.append(Loot(e.pos.x + random.uniform(-40, 40),
                                    e.pos.y + random.uniform(-40, 40),
                                    item=it))
        drop_chance = 0  # bereits gedropt
    if e.is_boss:
        drop_chance = 1.0
        rarity_boost = 25
        # Multi-Drop: 6-10 Items
        for _ in range(random.randint(6, 10)):
            it = items_mod.make_item(ilvl=ilvl, rarity_boost=rarity_boost)
            if not _item_passes_loot_filter(game, it):
                continue
            game.loot.append(Loot(e.pos.x + random.uniform(-60, 60),
                                  e.pos.y + random.uniform(-60, 60),
                                  item=it))
        # Bosse droppen garantiert 2 Edelsteine
        for _ in range(2):
            gem = random_gem()
            game.loot.append(Loot(e.pos.x + random.uniform(-30, 30),
                                  e.pos.y + random.uniform(-30, 30),
                                  gold=0))
            game.loot[-1].kind = 'gem'
            from .constants import GEM_TYPES
            game.loot[-1].color = GEM_TYPES[gem]['color']
            game.loot[-1].gem_type = gem
    elif drop_chance > 0 and random.random() < drop_chance:
        it = items_mod.make_item(ilvl=ilvl, rarity_boost=rarity_boost)
        if _item_passes_loot_filter(game, it):
            game.loot.append(Loot(e.pos.x + random.uniform(-20, 20),
                                  e.pos.y + random.uniform(-20, 20),
                                  item=it))

    # Edelstein-Drop: 8% Chance bei normalen, 25% bei Eliten
    gem_chance = 0.25 if e.elite else 0.08
    if not e.is_boss and random.random() < gem_chance:
        gem = random_gem()
        loot = Loot(e.pos.x + random.uniform(-20, 20),
                    e.pos.y + random.uniform(-20, 20), gold=0)
        loot.kind = 'gem'
        from .constants import GEM_TYPES
        loot.color = GEM_TYPES[gem]['color']
        loot.gem_type = gem
        game.loot.append(loot)

    # Schleim: spawnt 2 kleinere Schleime beim Tod (nur wenn nicht selbst klein)
    if e.type_key == 'slime' and not getattr(e, '_mini_slime', False):
        from . import enemies as _en
        for _ in range(2):
            ang = random.uniform(0, math.tau)
            sx_s = e.pos.x + math.cos(ang) * 20
            sy_s = e.pos.y + math.sin(ang) * 20
            mini = _en.spawn_enemy('slime', sx_s, sy_s,
                                    max(1, getattr(game.player, 'level', 1)),
                                    elite_chance=0)
            mini.hp_max *= 0.5
            mini.hp = mini.hp_max
            mini.dmg *= 0.6
            mini.radius = max(8, int(mini.radius * 0.65))
            mini.height = int(mini.radius * 2.2)
            mini.xp = max(2, mini.xp // 2)
            mini._mini_slime = True
            game.enemies.append(mini)

    # Explosive Elite: AoE-Schaden beim Tod MIT Wind-Up-Telegraph.
    # Update #26: Vorher detonierten 12 Firebolts SOFORT beim Tod ohne
    # Warnung → User stirbt durch „Funken aus dem Nichts". Jetzt:
    # 0.9s-Decal mit Pulse-Glow → dann erst die Explosion. Spieler kann
    # weg-dashen oder auf Distanz gehen.
    if e.affix == 'explosive':
        from .entities import Decal, Projectile
        det_x, det_y = e.pos.x, e.pos.y
        dmg_per_bolt = e.dmg * 0.6

        def _detonate(g, _decal=None):
            for i in range(12):
                a = (i / 12) * math.tau
                g.projectiles.append(Projectile(
                    det_x, det_y,
                    math.cos(a) * 240, math.sin(a) * 240,
                    dmg_per_bolt, 'firebolt', friendly=False,
                    radius=8, life=0.8,
                ))
            g.spawn_particles(det_x, det_y, 30, (255, 120, 40),
                              life_max=0.8, size_max=6)
            g.shake = max(g.shake, 10)
            try:
                snd.play('explosion_debris', volume=0.35)
            except Exception:
                pass

        decal = Decal(det_x, det_y, 70, kind='deadly',
                       windup=0.9, lifetime=0.0,
                       on_activate=_detonate, source=e)
        game.decals.append(decal)
        # Pre-Warning-Partikel + Floater
        game.spawn_particles(det_x, det_y, 14, (255, 80, 40),
                             life_max=0.5, size_max=4)
        game.floaters.append(Floater(det_x, det_y - 20,
                                      'EXPLODIERT!', (255, 100, 60),
                                      big=True))

    # Vampirische Elite: heilt Spieler-Schaden nicht, aber heilt sich nicht mehr
    # (Effekt rein bei Spielertreffer wäre besser - hier nur Symbolik)

    # Boss-XP-Mult (3x)
    xp_gain = e.xp * 3 if e.is_boss else e.xp
    game.player.xp += xp_gain
    progression.grant_skill_xp(game.player, xp_gain)
    # Spezial-Währungen droppen
    if e.is_boss:
        game.player.souls += random.randint(2, 5)
        game.player.lore_fragments += 1
        game.floaters.append(Floater(e.pos.x, e.pos.y - 50,
                                      '+Seelen', (180, 100, 240)))
    elif e.elite:
        game.player.shards += random.randint(1, 3)
        game.floaters.append(Floater(e.pos.x, e.pos.y - 30,
                                      '+Splitter', (140, 200, 255)))

    # Update #22: Mahnmal-Marken I..VII Drop (User-Wahl Lore-Bibel 6.4).
    # Boss → Marke nach Akt-Lineage; Mini-Boss → Marke I (Eisen-Kharn).
    # Aspekt-Mapping: biome → Marke-Nummer.
    biome_to_marke = {
        'crypt':  7,  # Salzhüter → VII (Items-Bibel, der Siebte)
        'frost':  2,  # Senator-Geist → II (Nheyra Glas)
        'lava':   4,  # Vehren → IV (Valsa Flamme)
        'swamp':  6,  # Shulavh → VI (Faden)
        'astral': 3,  # Spiegelhof → III (Ousen Geist)
        'desert': 5,  # Zhar-Eth → V (Im-Nesh Sprache)
    }
    biome_now = getattr(game, 'biome', 'crypt')
    marken_dict = getattr(game.player, 'mahnmal_marken', None)
    if marken_dict is not None:
        if e.is_boss:
            mk = biome_to_marke.get(biome_now, 7)
            cnt = random.randint(1, 2)
            marken_dict[mk] = marken_dict.get(mk, 0) + cnt
            ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV',
                      5: 'V', 6: 'VI', 7: 'VII'}
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - 70,
                f'+{cnt} Mahnmal-Marke {ROMAN[mk]}',
                (220, 180, 110)))
            game.push_event_notification(
                'currency',
                f'Mahnmal-Marke {ROMAN[mk]} erhalten',
                sub=f'{cnt}× zur Mahnmal-Halle bringen', duration=3.2)
            game.push_event_log(
                f'+{cnt} Marke {ROMAN[mk]}', (220, 180, 110))
            # Update #131 (Y-02): erste Marke → Pakt-Mechanik-Hint
            try:
                from . import tutorial as _tut
                _tut.mech_hint(game, 'first_marken')
            except ImportError:
                pass
        elif getattr(e, 'is_mini_boss', False):
            # Mini-Boss → Marke I (Eisen, Kharn-Aspekt)
            marken_dict[1] = marken_dict.get(1, 0) + 1
            game.floaters.append(Floater(
                e.pos.x, e.pos.y - 50,
                '+1 Mahnmal-Marke I', (220, 160, 80)))
            game.push_event_log('+1 Marke I', (220, 160, 80))

    # Skill-Gem-Drops (PoE2-Style): vom Boss garantiert, vom Elite 10%
    SKILL_GEM_POOL = ['fireball', 'lightning', 'heal', 'frostnova',
                       'earthquake', 'spark', 'bone_spear', 'ice_nova', 'comet']
    drop_gem = None
    if e.is_boss:
        missing = [s for s in SKILL_GEM_POOL
                   if s not in game.player.unlocked_skills]
        if missing:
            drop_gem = random.choice(missing)
    elif e.elite and random.random() < 0.10:
        missing = [s for s in SKILL_GEM_POOL
                   if s not in game.player.unlocked_skills]
        if missing:
            drop_gem = random.choice(missing)
    if drop_gem:
        loot = Loot(e.pos.x + random.uniform(-15, 15),
                    e.pos.y + random.uniform(-15, 15), gold=0)
        loot.kind = 'skill_gem'
        loot.skill_id = drop_gem
        loot.color = (200, 150, 240)
        game.loot.append(loot)
    game.kills += 1
    game.shake = max(game.shake, 8 if e.is_boss else 5)

    # Achievement: Kill
    ach_mod.on_kill(game, e)
    if hasattr(game, '_check_achievements'):
        game._check_achievements()

    # Quest-Fortschritt
    if hasattr(game, 'active_quest') and game.active_quest is not None:
        from . import quests
        quests.on_kill(game, e)

    if game.player.xp >= game.player.xp_to_next:
        progression.level_up(game.player)
        eff = progression.effective(game.player)
        game.player.hp = eff['hp_max']
        game.player.mp = eff['mp_max']
        game.player.levelup_invuln = 5.0
        # J-12 (Update #65): Event-Bus — Player-Levelup
        try:
            from . import events as _ev
            _ev.publish(_ev.EventKey.ON_PLAYER_LEVELUP,
                         game=game, new_level=game.player.level)
        except Exception:
            pass
        game.floaters.append(Floater(game.player.pos.x, game.player.pos.y - 40,
                                     'STUFENAUFSTIEG!', (255, 215, 90)))
        game.spawn_particles(game.player.pos.x, game.player.pos.y, 80,
                             (255, 215, 90), life_max=1.6, size_max=8)
        # X-07 (Update #168): Level-Up-Mini-Cinematic.  0.6 s Camera-Zoom-
        # to-Player via Crit-Pull, Gold-Aura-Burst (8-strahliges Pulse-
        # Ring), Slow-Mo-Beat 0.18 s.  Anti-Spam via _levelup_cinematic_t.
        try:
            import time as _t
            now_anim = _t.time()
            if now_anim - getattr(game, '_levelup_cinematic_t', 0.0) > 8.0:
                game._levelup_cinematic_t = now_anim
                # Slow-Mo + Shake-Pulse
                game.slow_mo_left = max(getattr(game, 'slow_mo_left', 0.0), 0.18)
                game.shake = max(getattr(game, 'shake', 0), 14)
                # 8-Strahl Pulse-Ring Particles
                import math as _m
                for k in range(8):
                    a = _m.tau * k / 8
                    vx = _m.cos(a) * 220
                    vy = _m.sin(a) * 220
                    game.particles_push(
                        game.player.pos.x, game.player.pos.y,
                        vx, vy,
                        (255, 240, 130), 0.5, 6, gravity=-20)
                # Crit-Zoom-Pull zum Player
                if hasattr(game, 'trigger_crit_zoom'):
                    game.trigger_crit_zoom(
                        game.player.pos.x, game.player.pos.y)
                # Banner-Notification
                if hasattr(game, 'push_event_notification'):
                    game.push_event_notification(
                        'levelup',
                        f'Stufenaufstieg: {game.player.level}',
                        sub='Mahnmal-Schritt vorwärts',
                        color=(255, 230, 130), duration=2.6)
        except Exception:
            pass
        # Update #81 + #148: Klassen-Voice-Line bei Level-Up (Lore-Anker
        # zu VELGRAD_VOICE_LINES_POOL.md).  Cooldown 30 s damit nicht
        # bei XP-Flood (4-5 Level-Ups in Folge) gespammt wird.
        # Anti-Repeat-Memo wie bei boss_kill.
        import time as _t
        now = _t.time()
        last_lvl = getattr(game, '_class_voice_levelup_t', 0.0)
        if now - last_lvl > 30.0:
            game._class_voice_levelup_t = now
            try:
                from . import quotes as _q
                last_q = getattr(game,
                                  '_class_voice_levelup_last_quote', None)
                vl = None
                for _ in range(3):
                    cand = _q.class_voice_line(
                        game.player.cls, 'levelup')
                    if cand and cand != last_q:
                        vl = cand
                        break
                    vl = cand
                if vl:
                    game._class_voice_levelup_last_quote = vl
                    game.toast(vl, (255, 220, 130))
            except Exception:
                pass
            # Update #127: AI-Klassen-Level-Up-Voice (MP3-Audio).
            # Update #148: Volume 0.9 → 0.45 (User-Report „Voice viel
            # zu laut").  Lautstärke war doppelt so hoch wie SFX-Cap.
            try:
                snd.play_class_voice(game.player.cls, 'level_up',
                                      volume=0.45)
            except Exception:
                pass
        for k in range(24):
            ang = (k / 24) * math.tau
            game.particles_push(
                game.player.pos.x, game.player.pos.y,
                math.cos(ang) * 200, math.sin(ang) * 200,
                (255, 240, 180), 0.6, 4)
        game.shake = max(game.shake, 8)
        snd.play('levelup')
        # G-13: Prominente Banner-Notification oben Mitte.
        game.push_event_notification(
            'levelup',
            f'STUFE {game.player.level} ERREICHT',
            sub=f'+1 Skillpunkt · +3 Attribut · +1 Klassen-Punkt',
            color=(255, 220, 100), duration=3.4)


def damage_player(game, dmg, dmg_type='physical', source=None):
    """Player-Schaden mit Damage-Type-Tracking für Death-Cinematic (A-01).

    `dmg_type`: physical / fire / cold / lightning / chaos / bleed / void /
    falling — wird via quotes.normalize_damage_type gemappt.
    `source`: optional Enemy/Projectile-Verweis (für last_damage_source).
    """
    p = game.player
    if p.invuln > 0 or p.dodge > 0:
        return
    eff = progression.effective(p)
    atlas_eff = eff.get('atlas_effects', set())
    # Schurken-Ausweichchance (+ Atlas dodge_chance)
    if eff.get('dodge_chance', 0) > 0 and random.random() < eff['dodge_chance']:
        game.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 10,
                                     'Ausgewichen', (180, 220, 200)))
        p.invuln = 0.2
        return
    # Aura: Schaden-Reduktion + Atlas dmg_red
    dmg = dmg * eff.get('dmg_taken_mult', 1.0)
    # Update #184: Atlas-Stat dmg_red (additiv 0..1)
    from .skill_atlas import aggregate_stats as _atlas_stats
    _astats = _atlas_stats(p)
    if _astats.get('dmg_red', 0) > 0:
        dmg *= max(0.0, 1.0 - _astats['dmg_red'])
    # Update #184: Way-of-Wind Keystone — +40% dmg taken in iframe-phase
    if getattr(p, '_way_of_wind_active', 0) > 0:
        dmg *= 1.40
    # Sapped: Spieler verursacht weniger Schaden, aber hier wirkt auf erlitten:
    # Wir interpretieren sapped als "weniger Damage dealt", angewendet auf Gegner.
    # Player Variante: skip hier.
    # Update #106 (Audit F-010): Spike-Cap — kein One-Shot über 65 % HP_max.
    # Schützt vor unfairen Boss-Charged-Attacks die HP überschießen können
    # (z.B. Tier-3-Boss × Berserk × 2.5× Damage > 200 HP).
    hp_max_cap = eff['hp_max'] * 0.65
    if dmg > hp_max_cap:
        dmg = hp_max_cap
    # Mana-Shield (Magier-Talent): teil des Schadens auf Mana
    if eff.get('mp_to_hp', 0) > 0 and p.mp > 0:
        portion = eff['mp_to_hp']
        mana_absorb = min(p.mp, dmg * portion)
        p.mp -= mana_absorb
        dmg -= mana_absorb
    # Schild absorbiert dann
    if p.shield > 0:
        absorbed = min(p.shield, dmg)
        p.shield -= absorbed
        dmg -= absorbed
        if absorbed > 0:
            game.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 10,
                                         f'-{int(absorbed)}', (160, 200, 255)))
    if dmg <= 0:
        p.invuln = 0.2
        return

    hp_before = p.hp
    p.hp -= dmg
    p.invuln = 0.3
    # Update #184: Moench-Notable "Klangloser Tritt" — 25% chance auf
    # Iframe-Refresh nach Hit (effektiv evade-cancel).
    if 'evade_after_hit_25' in atlas_eff and random.random() < 0.25:
        p.invuln = max(p.invuln, 0.4)
        game.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 22,
                                     'Klangloser Tritt',
                                     (200, 230, 200)))
    game.shake = max(game.shake, 10)
    # Update #165: Animation-Trigger 'hit' (One-Shot 4 Frames @ 12fps ≈ 0.33s)
    try:
        p.anim_state.trigger('hit')
    except AttributeError:
        pass
    # Update #131 (Y-02): Low-HP-Mechanik-Hint einmalig wenn unter 30 %.
    try:
        if p.hp > 0 and p.hp / max(1, eff['hp_max']) < 0.30:
            from . import tutorial as _tut
            _tut.mech_hint(game, 'low_hp')
    except (ImportError, KeyError, TypeError):
        pass
    game._damage_flash = 1.0
    # Update #81: Low-HP-Voice-Line beim ersten Mal unter 25 % HP pro
    # Kampf-Sequenz. Cooldown 12 s damit nicht spammt.
    hp_max = eff['hp_max']
    if hp_max > 0:
        before_pct = hp_before / hp_max
        after_pct = p.hp / hp_max
        if before_pct >= 0.25 and after_pct < 0.25:
            now_lhp = pygame.time.get_ticks() * 0.001
            if now_lhp - getattr(game, '_last_low_hp_quote_t', 0) > 12.0:
                game._last_low_hp_quote_t = now_lhp
                try:
                    from . import quotes as _q
                    vl = _q.class_voice_line(game.player.cls, 'low_hp')
                    if vl:
                        game.toast(vl, (240, 130, 130))
                except Exception:
                    pass
    # PLAN A-01: Snapshot des letzten Treffers, wird beim Tod gelesen.
    game.last_damage_source = {
        'type': dmg_type,
        'amount': float(dmg),
        'source': source,
        'time': pygame.time.get_ticks() / 1000.0,
        'hit_pos': (p.pos.x, p.pos.y),
    }
    # Update #46: Damage-Sound mit 0.12 s Cooldown — verhindert Audio-Spam
    # bei mehreren simultanen Treffern (Stormcaller-Burst, AoE-Decals,
    # Aschen-Brut-Welle). User-Bug „Sound-Bugs".
    now_t = pygame.time.get_ticks() * 0.001
    if now_t - getattr(game, '_last_damage_sound_t', 0) > 0.12:
        game._last_damage_sound_t = now_t
        snd.play('damage')
    game.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 10,
                                 int(dmg), (255, 136, 136)))
    game.spawn_particles(p.pos.x, p.pos.y, 8, (255, 68, 68))
    # Blutspritzer am Spieler
    for _ in range(10):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(60, 180)
        game.particles_push(
            p.pos.x, p.pos.y,
            math.cos(ang) * sp, math.sin(ang) * sp - 30,
            (180, 30, 30), random.uniform(0.4, 0.8),
            random.uniform(2, 4), gravity=180)

    # Dornen-Affix
    if eff['thorns'] > 0:
        for e in list(game.enemies):
            if (e.pos - p.pos).length() < 80:
                hit_enemy(game, e, eff['thorns'])

    if p.hp <= 0:
        # Dungeon: Tod-Counter erhöhen
        if hasattr(game, 'area') and game.area == 'dungeon':
            p.deaths_in_dungeon += 1
        # Tod-Animation starten (2s) bevor Death-Screen
        if not p.dying:
            p.dying = True
            p.death_timer = 0.0
            # Update #165: Death-Anim ueberschreibt alles (permanent lock)
            try:
                p.anim_state.trigger('death')
            except AttributeError:
                pass
            # J-12 (Update #65): Event-Bus — Player-Died
            try:
                from . import events as _ev
                _ev.publish(_ev.EventKey.ON_PLAYER_DIED,
                             game=game, damage_type=dmg_type, source=source)
            except Exception:
                pass
            # Klassen-spezifische Partikel
            cls_particle_color = {
                'warrior': (160, 80, 80),
                'mage':    (140, 100, 60),    # Asche
                'rogue':   (80, 30, 100),     # Schatten
            }.get(p.cls, (200, 100, 100))
            game.spawn_particles(p.pos.x, p.pos.y, 50,
                                 cls_particle_color, life_max=1.5, size_max=6,
                                 gravity=40)
            game._player_death_anim_start = True
            # Update #127: Klassen-Death-Voice (z.B. „Nicht so..." /
            # Klangschalen-Stille). Lore-Voice aus voice_registry.
            try:
                # Update #148: Voice 0.9 → 0.5 (User-Report „zu laut")
                snd.play_class_voice(p.cls, 'death', volume=0.5)
            except Exception:
                pass
