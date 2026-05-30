"""Status-Effekte, Element-Combos und VFX-Partikel-Layer-System.

target.status ist ein dict:
  effect_key -> {'stacks': int, 'time_left': float, 'next_tick': float}
"""

from .constants import STATUS_EFFECTS, ELEMENT_COMBOS
from .entities import Floater, Decal


# ============================================================
# PARTIKEL-LAYER-SYSTEM (PLAN-Tasks C-01, C-03)
# ============================================================
# Zwei-Schichten-Architektur gemäß Erweiterungs-Briefing Teil C.2:
#   - AMBIENT: atmosphärisch, gameplay-irrelevant, cullable (Asche, Funken, Dust).
#   - GAMEPLAY: Hit-Feedback, Projektil-Trails, Combo-VFX. Nicht cullable.
#   - TELEGRAPH: AoE-Marker, Boss-Wind-Ups. Höchste Priorität, immer sichtbar.
#   - UI_OVERLAY: HUD-Effekte, Notifications.
#
# Jeder Partikel trägt ein layer-Attribut (siehe entities.Particle).
# Render-Reihenfolge nutzt priority; cullable steuert, ob die Dichte
# bei hoher Combat-Last automatisch reduziert wird.

class ParticleLayer:
    AMBIENT    = 'ambient'
    GAMEPLAY   = 'gameplay'
    TELEGRAPH  = 'telegraph'
    UI_OVERLAY = 'ui_overlay'


# M-02 (Update #68): Pro-Element-Look-Rezept (Briefing 5.1).
# Pro Element + Phase eine Partikel-Recipe:
#   - color: Haupt-Tint
#   - accent: 2. Layer (Sparkle/Ember)
#   - gravity: Particle-Gravity (positiv = fällt, negativ = steigt)
#   - life: max-Life-Range
# Phasen-Profile (M-01): wind-up (am Caster vor Damage), travel (Trail),
# impact (Hit-Spot Explosion). Pragmatic: ohne echten Shader, aber
# unterschiedliche Recipes geben sichtbare Element-Identity.
ELEMENT_LOOK = {
    'fire': dict(
        windup=dict(color=(255, 120, 30), accent=(255, 220, 100),
                    n=18, gravity=-40, life=0.6, size=4),
        travel=dict(color=(255, 100, 30), accent=(255, 200, 60),
                    n=4,  gravity=20, life=0.4, size=3),
        impact=dict(color=(255, 80, 30), accent=(255, 220, 130),
                    n=32, gravity=60, life=0.9, size=6),
    ),
    'cold': dict(
        windup=dict(color=(180, 220, 255), accent=(255, 255, 255),
                    n=18, gravity=-20, life=0.7, size=4),
        travel=dict(color=(140, 200, 255), accent=(220, 240, 255),
                    n=4,  gravity=0,  life=0.5, size=3),
        impact=dict(color=(120, 180, 240), accent=(220, 240, 255),
                    n=28, gravity=20, life=1.0, size=5),
    ),
    'lightning': dict(
        windup=dict(color=(200, 220, 255), accent=(255, 255, 200),
                    n=16, gravity=-50, life=0.4, size=3),
        travel=dict(color=(220, 240, 255), accent=(255, 255, 200),
                    n=4,  gravity=-10, life=0.2, size=3),
        impact=dict(color=(255, 240, 120), accent=(220, 240, 255),
                    n=26, gravity=30, life=0.5, size=4),
    ),
    'physical': dict(
        windup=dict(color=(220, 200, 170), accent=(255, 240, 200),
                    n=14, gravity=-30, life=0.5, size=3),
        travel=dict(color=(200, 180, 150), accent=(140, 100, 80),
                    n=3,  gravity=80, life=0.3, size=3),
        impact=dict(color=(140, 30, 30), accent=(255, 220, 200),
                    n=24, gravity=160, life=0.7, size=4),
    ),
    'chaos': dict(
        windup=dict(color=(180, 100, 220), accent=(80, 200, 100),
                    n=18, gravity=-30, life=0.7, size=4),
        travel=dict(color=(140, 80, 200), accent=(60, 180, 80),
                    n=4,  gravity=0,  life=0.5, size=3),
        impact=dict(color=(200, 100, 220), accent=(120, 220, 120),
                    n=30, gravity=40, life=0.9, size=5),
    ),
    'shadow': dict(
        windup=dict(color=(60, 30, 80), accent=(180, 120, 220),
                    n=18, gravity=-20, life=0.7, size=4),
        travel=dict(color=(80, 40, 100), accent=(140, 80, 180),
                    n=4,  gravity=0,  life=0.5, size=3),
        impact=dict(color=(100, 40, 140), accent=(200, 150, 240),
                    n=28, gravity=30, life=0.9, size=5),
    ),
}


def play_skill_vfx_phase(game, x, y, element, phase='impact'):
    """M-01/M-02 (Update #68): Phased Element-VFX-Spawn.

    `phase` in ('windup', 'travel', 'impact').  Spawnt Main-Color +
    Accent-Layer mit element-spezifischer Recipe.  Fall-through auf
    `physical` wenn das Element nicht registriert ist.
    """
    look = ELEMENT_LOOK.get(element) or ELEMENT_LOOK['physical']
    cfg = look.get(phase) or look['impact']
    n_main = cfg['n']
    n_accent = max(1, n_main // 3)
    game.spawn_particles(x, y, n_main, cfg['color'],
                         life_max=cfg['life'],
                         size_max=cfg['size'],
                         gravity=cfg['gravity'])
    # Accent-Layer: kleiner + längere Life, andere Farbe
    game.spawn_particles(x, y, n_accent, cfg['accent'],
                         life_max=cfg['life'] * 1.2,
                         size_max=max(2, cfg['size'] - 1),
                         gravity=cfg['gravity'])


LAYER_CONFIG = {
    ParticleLayer.AMBIENT:    {'priority': 10, 'cullable': True,  'bloom': 0.3},
    ParticleLayer.GAMEPLAY:   {'priority': 50, 'cullable': False, 'bloom': 0.8},
    ParticleLayer.TELEGRAPH:  {'priority': 80, 'cullable': False, 'bloom': 1.0},
    ParticleLayer.UI_OVERLAY: {'priority': 99, 'cullable': False, 'bloom': 1.0},
}

# Dynamisches Culling (C-03):
# Wenn so viele non-cullable Partikel aktiv sind, wird AMBIENT-Density
# automatisch um DYNAMIC_AMBIENT_CULL_FACTOR reduziert.
GAMEPLAY_CRITICAL_THRESHOLD = 120
DYNAMIC_AMBIENT_CULL_FACTOR  = 0.4

# Boss-Encounter (C-04): AMBIENT um 70 % reduzieren, damit Telegraphs
# und Boss-Mechaniken klar lesbar bleiben (Briefing Teil C.2 — 60–80 %).
BOSS_AMBIENT_CULL_FACTOR = 0.3


def gameplay_critical_count(game):
    """Anzahl aktiver Partikel in non-cullable Layern (GAMEPLAY + TELEGRAPH)."""
    return sum(1 for p in game.particles
               if not LAYER_CONFIG[getattr(p, 'layer', ParticleLayer.GAMEPLAY)]['cullable'])


def particle_render_priority(p):
    """Z-Order-Key für Partikel-Rendering (C-09).

    AMBIENT (10) zuerst → GAMEPLAY (50) → TELEGRAPH (80) → UI_OVERLAY (99).
    Damit überschreibt jeder Telegraph-Partikel atmosphärische Particles,
    selbst wenn diese später gespawned wurden — Briefing C.4 verlangt,
    dass kritische VFX IMMER über Ambient gezeichnet werden.
    """
    return LAYER_CONFIG[getattr(p, 'layer', ParticleLayer.GAMEPLAY)]['priority']


def is_boss_active(game):
    """True wenn ein Boss-Encounter aktiv ist (Intro-Cinematic ODER lebender Boss)."""
    if getattr(game, 'boss_intro', None) is not None:
        return True
    for e in getattr(game, 'enemies', ()):
        if getattr(e, 'is_boss', False) and not getattr(e, 'dying', False):
            return True
    return False


def ambient_density_multiplier(game):
    """Effektiver AMBIENT-Density-Faktor: User-Setting × dynamisches Culling
    × Boss-Encounter-Reduktion.

    Wird von spawn_ambient() und vom Wetter-System konsultiert.
    GAMEPLAY/TELEGRAPH-Partikel sind NICHT betroffen (cullable=False).
    """
    mult = game.settings.get('particle_density', 1.0)
    if gameplay_critical_count(game) > GAMEPLAY_CRITICAL_THRESHOLD:
        mult *= DYNAMIC_AMBIENT_CULL_FACTOR
    if is_boss_active(game):
        mult *= BOSS_AMBIENT_CULL_FACTOR
    return mult


# Vorgegebene Slider-Stufen (C-02): Low / Medium / High / Ultra.
DENSITY_PRESETS = [
    ('Niedrig', 0.3),
    ('Mittel',  0.7),
    ('Hoch',    1.0),
    ('Ultra',   1.5),
]


# ============================================================
# L-BLOCK — AILMENT-PIPELINE (Status-Effekt-Application aus Tags)
# ============================================================
# Briefing 3.2: Elemental Ailments = Ignite (Fire DoT), Freeze (Hard-CC),
# Chill (Slow), Shock (Damage-Taken-Up), Brittle (Crit-Chance-Up),
# Sapped (Less Damage).
# Physical Ailments: Bleed.
# Chaos: Poison (stackbar).
#
# `apply_ailments_from_context(game, target, ctx, is_crit)` liest den
# SkillContext aus gems.py und löst basierend auf damage-tags + crit
# das passende Ailment aus. Damit wird L mit J-04 verknüpft.

import random as _r


# Ailment-Apply-Chancen pro Damage-Tag (Base, modifiable).
# Ohne explizite Skill-Tags → keine Ailment-Application.
DEFAULT_AILMENT_CHANCE = {
    'fire':      ('burn',   0.30),   # Ignite-Chance 30%
    'cold':      ('frost',  0.20),   # Freeze-Buildup
    'lightning': ('shock',  0.25),   # Shock-Stack
    'physical':  ('bleed',  0.18),   # Bleed-on-Crit höher
    'chaos':     ('poison', 0.35),   # Poison stackbar
}

CRIT_AILMENT_BONUS = 0.25   # +25% Chance bei Crit


def apply_ailments_from_context(game, target, ctx, is_crit=False):
    """Wendet Ailments basierend auf ctx.tags an (L-Block).

    Liest damage-tags aus dem SkillContext, würfelt pro Tag eine
    Application-Chance, applied das passende Ailment.
    Crit erhöht jede Chance um +25 % und kann zusätzlich Brittle
    (Cold-Crit) bzw. Sapped (Chaos-Crit) auslösen.
    """
    if target is None or getattr(target, 'dying', False):
        return
    tags = getattr(ctx, 'tags', set())
    if not tags:
        return
    crit_bonus = CRIT_AILMENT_BONUS if is_crit else 0.0
    for dtag, (ailment_key, base_chance) in DEFAULT_AILMENT_CHANCE.items():
        if dtag not in tags:
            continue
        chance = base_chance + crit_bonus
        if _r.random() < chance:
            stacks = 2 if is_crit else 1
            apply(game, target, ailment_key, stacks=stacks)
            # Bonus-Ailments bei Crit
            if is_crit:
                if dtag == 'cold':
                    # Cold-Crit baut Brittle auf
                    apply(game, target, 'brittle', stacks=1)
                elif dtag == 'chaos':
                    # Chaos-Crit baut Sapped auf
                    apply(game, target, 'sapped', stacks=1)


def apply_ailments_from_tags(game, target, tags, is_crit=False):
    """Convenience-Wrapper für Skill-Casts ohne vollen SkillContext.

    Erlaubt schrittweise Migration: Legacy-Casts können direkt das
    Tag-Set übergeben statt einen ganzen ctx aufzubauen.
    """
    class _MiniCtx:
        pass
    ctx = _MiniCtx()
    ctx.tags = set(tags)
    apply_ailments_from_context(game, target, ctx, is_crit=is_crit)


# ============================================================
# GROUND-DECAL / AoE-TELEGRAPH-SYSTEM (PLAN-Tasks C-05, C-06, C-07)
# ============================================================
# Briefing Teil C.3 — jede tödliche Boden-AoE braucht drei Indikatoren:
#   1) Ground-Decal-Outline (Farbe nach Kategorie)
#   2) Sound-Cue (tieffrequenter Wind-Up)  ← C-06
#   3) Mid-Air-Indicator für aerial AoE     ← C-07
#
# DECAL_KIND-Farbcode aus dem Briefing (C.3):
#   - DEADLY   = Rot     — Schaden bei Eintritt
#   - DOT      = Orange  — Schaden über Zeit (Lava, Poison)
#   - CC       = Gelb    — Knockback / CC, kein Direkt-Schaden
#   - CHAOS    = Lila    — Chaos / Curse-Field
#   - BUFF     = Cyan    — Verbündete Buff-Zone

class DECAL_KIND:
    DEADLY = 'deadly'
    DOT    = 'dot'
    CC     = 'cc'
    CHAOS  = 'chaos'
    BUFF   = 'buff'


DECAL_COLORS = {
    DECAL_KIND.DEADLY: (255,  60,  40),   # Rot
    DECAL_KIND.DOT:    (255, 150,  40),   # Orange
    DECAL_KIND.CC:     (245, 220,  60),   # Gelb
    DECAL_KIND.CHAOS:  (190,  90, 240),   # Lila
    DECAL_KIND.BUFF:   ( 80, 220, 240),   # Cyan
}

# Damage-Type → Decal-Kind-Mapping (für Convenience-Aufrufe).
DAMAGE_TYPE_TO_DECAL_KIND = {
    'physical': DECAL_KIND.DEADLY,
    'fire':     DECAL_KIND.DOT,
    'cold':     DECAL_KIND.DEADLY,
    'lightning':DECAL_KIND.DEADLY,
    'poison':   DECAL_KIND.DOT,
    'bleed':    DECAL_KIND.DOT,
    'chaos':    DECAL_KIND.CHAOS,
    'cc':       DECAL_KIND.CC,
    'buff':     DECAL_KIND.BUFF,
}


def spawn_ground_decal(game, x, y, radius, kind=DECAL_KIND.DEADLY,
                       windup=0.8, lifetime=0.0, aerial=False,
                       on_activate=None, source=None, play_windup=True):
    """Spawnt einen AoE-Telegraph-Decal + spielt optional Wind-Up-Sound.

    Standard-Wind-Up 0.8 s entspricht Briefing C.3 (tieffrequenter Brumm
    0.5–1.0 s vor Aktivierung). Für sehr kurze Pokes < 0.4 s wird kein
    Wind-Up-Sound gespielt (zu kurz, würde Audio-Spam erzeugen).
    """
    decal = Decal(x, y, radius, kind=kind, windup=windup, lifetime=lifetime,
                  aerial=aerial, on_activate=on_activate, source=source)
    decals = getattr(game, 'decals', None)
    if decals is None:
        game.decals = []
        decals = game.decals
    decals.append(decal)
    # J-12 (Update #65): Event-Bus Hook für AoE-Spawn
    try:
        from . import events as _ev
        _ev.publish(_ev.EventKey.ON_AOE_SPAWNED,
                     game=game, x=x, y=y, radius=radius,
                     kind=kind, windup=windup, source=source)
    except Exception:
        pass
    if play_windup and windup >= 0.4:
        try:
            from . import sounds as _snd
            # Update #184 (User-Report „aoe_windup ballert die Ohren weg"):
            # Lautstaerke-Kurve hart runter — vorher 0.6+windup*0.3 erreichte
            # bei langen Windups Vollgas (1.0).  Jetzt 0.30+windup*0.10 mit
            # Cap 0.55.  Volume-Cap auf 'aoe_windup' (0.35) im sounds.py
            # bremst zusaetzlich.
            vol = min(0.55, 0.30 + windup * 0.10)
            # C-13 (Update #51): Sound-Only-AoE-Cue. play_at statt play
            # gibt Distance-Falloff + L/R-Pan — Sehbehinderte können die
            # AoE-Position rein audio-spatial lokalisieren. Wenn das Game
            # keinen Player hat (Title), fällt es auf normales play zurück.
            try:
                listener = (game.player.pos.x, game.player.pos.y)
                _snd.play_at('aoe_windup', (x, y), listener, volume=vol)
            except Exception:
                _snd.play('aoe_windup', volume=vol)
        except Exception:
            pass
    return decal


class AoeTelegraph:
    """C-14 (Update #49): High-Level-Wrapper über das Decal-System.

    Klare Combat-API für AoE-Hits: Position + Radius + Damage-Type +
    Wind-Up + Lifetime + Damage-Amount → spawned ein DECAL mit
    type-passender Kind-Farbe und einem default `on_activate` der
    Damage-Type-korrekt am Spieler-Target appliziert.

    Verwendung (z. B. in Boss-Skills):
        AoeTelegraph(
            game, x, y, radius=80, dmg_type='fire',
            damage=base_dmg * 1.2, windup=0.7, source=enemy
        ).spawn()

    Sehr lose Kopplung: Wer mehr Kontrolle braucht (z. B. eigene VFX bei
    Activate), nutzt weiter direkt `spawn_ground_decal()`.
    """
    __slots__ = ('game', 'x', 'y', 'radius', 'dmg_type', 'damage',
                 'windup', 'lifetime', 'source', 'aerial', 'extra_fn')

    def __init__(self, game, x, y, radius, dmg_type='physical',
                 damage=0.0, windup=0.7, lifetime=0.0,
                 source=None, aerial=False, extra_fn=None):
        self.game = game
        self.x = float(x)
        self.y = float(y)
        self.radius = float(radius)
        self.dmg_type = dmg_type
        self.damage = float(damage)
        self.windup = float(windup)
        self.lifetime = float(lifetime)
        self.source = source
        self.aerial = bool(aerial)
        # Optionaler Extra-Hook bei Activate (Partikel, Status-Apply, …).
        # Wird nach dem Damage-Hit gerufen mit (game, decal).
        self.extra_fn = extra_fn

    def spawn(self):
        """Spawnt den Telegraph-Decal. Returnt das Decal-Objekt."""
        kind = DAMAGE_TYPE_TO_DECAL_KIND.get(self.dmg_type, DECAL_KIND.DEADLY)
        dmg = self.damage
        dt_t = self.dmg_type
        src = self.source
        extra = self.extra_fn
        center_x = self.x
        center_y = self.y

        def _on_activate(g, decal, _dmg=dmg, _dt=dt_t, _src=src,
                          _extra=extra, _cx=center_x, _cy=center_y):
            # Damage-Anwendung am Spieler wenn in Radius
            if _dmg > 0:
                px = g.player.pos.x - _cx
                py = g.player.pos.y - _cy
                if (px * px + py * py) ** 0.5 <= decal.radius:
                    g.damage_player(_dmg, dmg_type=_dt, source=_src)
            if _extra is not None:
                try:
                    _extra(g, decal)
                except Exception:
                    pass

        return spawn_ground_decal(
            self.game, self.x, self.y, radius=self.radius,
            kind=kind, windup=self.windup, lifetime=self.lifetime,
            aerial=self.aerial,
            on_activate=_on_activate, source=self.source)


def update_decals(game, dt):
    """Tickt alle Decals: Wind-Up→Activate→Lifetime→Remove. Engine-agnostisch.

    Bei Activate wird der on_activate-Callback gefeuert + aoe_impact-SFX.
    """
    decals = getattr(game, 'decals', None)
    if not decals:
        return
    for d in decals[:]:
        prev_age = d.age
        d.age += dt
        # C-13 (Update #51): „Imminent-Impact"-Audio-Cue 0.15 s vor Activate.
        # Ein letzter klar identifizierbarer Tick-Sound — Sehbehinderte
        # haben damit eine eindeutige Reaction-Window-Signalisierung.
        imminent_threshold = d.windup - 0.15
        if (not d.activated and not getattr(d, '_imminent_played', False)
                and prev_age < imminent_threshold <= d.age
                and d.windup >= 0.5):
            d._imminent_played = True
            try:
                from . import sounds as _snd
                listener = (game.player.pos.x, game.player.pos.y)
                _snd.play_at('click', (d.pos.x, d.pos.y), listener,
                              volume=0.50)
            except Exception:
                pass
        if not d.activated and d.age >= d.windup:
            d.activated = True
            if d.on_activate is not None:
                try:
                    d.on_activate(game, d)
                except Exception:
                    pass
            try:
                from . import sounds as _snd
                # C-13: aoe_impact ebenfalls positional
                try:
                    listener = (game.player.pos.x, game.player.pos.y)
                    _snd.play_at('aoe_impact', (d.pos.x, d.pos.y),
                                  listener, volume=0.8)
                except Exception:
                    _snd.play('aoe_impact', volume=0.8)
            except Exception:
                pass
            # V-03 (Update #168): Scorched-Earth nach Fire-AoE.
            # Persistent 18 s Boden-Decal an der Aktivierungs-Stelle.
            try:
                dmg_type = getattr(d, 'dmg_type', None)
                kind = getattr(d, 'kind', None)
                if dmg_type == 'fire' or kind == DECAL_KIND.DOT:
                    surf_fx = getattr(game, 'surface_fx', None)
                    if surf_fx is not None and d.radius >= 30:
                        surf_fx.spawn_scorched_earth(
                            d.pos.x, d.pos.y,
                            radius=int(d.radius * 0.85))
            except Exception:
                pass
        if d.activated and (d.age - d.windup) >= d.lifetime:
            decals.remove(d)


def apply(game, target, key, stacks=1, source='player', _skip_combo=False):
    """Wendet einen Status-Effekt an. Kann einen Combo auslösen."""
    if key not in STATUS_EFFECTS:
        return
    # Combo check (außer bei kaskadierten Anwendungen aus einem Combo selbst)
    if not _skip_combo:
        for other_key in list(target.status.keys()):
            if other_key == key:
                continue
            pair = tuple(sorted([key, other_key]))
            if pair in ELEMENT_COMBOS:
                _trigger_combo(game, target, pair)
                return  # Beide Effekte verbraucht, kein Stacking

    spec = STATUS_EFFECTS[key]
    first_apply = key not in target.status
    if key in target.status:
        st = target.status[key]
        st['stacks'] = min(spec['max_stacks'], st['stacks'] + stacks)
        st['time_left'] = spec['duration']
    else:
        target.status[key] = {
            'stacks': min(spec['max_stacks'], stacks),
            'time_left': spec['duration'],
            'next_tick': spec['tick'],
        }
        # Update #X — Phase-2-AI-SFX bei erster Effekt-Anwendung
        try:
            from . import sounds as _snd
            STATUS_APPLY_SFX = {
                'burn':    None,           # Loop ueber burning_loop separat
                'frost':   'frozen_apply',
                'shock':   'shock_tick',   # einmaliger Zap
                'poison':  'poison_tick',
                'bleed':   'bleed_tick',
                'stun':    'stun_apply',
                'silence': 'silence_apply',
            }
            sfx = STATUS_APPLY_SFX.get(key)
            if sfx:
                _snd.play(sfx, volume=0.35)
        except Exception:
            pass

    # PLAN J-08: Meta-Trigger bei erster Ailment-Application.
    # Cast-on-Ignite/Freeze/Shock + Cast-on-Elemental-Ailment werden hier
    # gefeuert, wenn das Ziel ein Gegner ist (kein Player-Self-Apply).
    if first_apply and source == 'player' and target is not getattr(
            game, 'player', None):
        event_map = {
            'burn':  'on_ignite',
            'frost': 'on_freeze',
            'shock': 'on_shock',
        }
        evt = event_map.get(key)
        if evt is not None:
            try:
                from . import gems as _g
                _g.trigger_meta_event(getattr(game, 'player', None), evt,
                                       game=game, target=target)
            except Exception:
                pass
        # Update #131 (Y-02): erstes Ailment einer Sorte → Mechanik-Hint
        try:
            from . import tutorial as _tut
            hint_map = {'frost': 'frost_stacks', 'burn': 'first_burn'}
            hk = hint_map.get(key)
            if hk:
                _tut.mech_hint(game, hk)
        except ImportError:
            pass


def tick_target(game, target, dt, is_player=False):
    """Verarbeitet alle aktiven Effekte am Ziel."""
    if not target.status:
        return
    for key in list(target.status.keys()):
        spec = STATUS_EFFECTS[key]
        st = target.status[key]
        st['time_left'] -= dt
        st['next_tick'] -= dt
        if st['next_tick'] <= 0:
            dmg = spec['dmg_per_tick'] * st['stacks']
            if dmg > 0:
                _apply_status_damage(game, target, dmg, spec['color'], is_player)
            st['next_tick'] = spec['tick']

        # Frost: Slow anwenden (über update_player/update_enemy)
        if key == 'frost' and 'slow' in spec:
            stack_factor = 1.0 - min(0.9, spec['slow'] + (st['stacks'] - 1) * 0.05)
            target.slow_factor = min(target.slow_factor, stack_factor)
            target.slow_timer = max(target.slow_timer, 0.25)
        # Chill: leichter Slow (kumulativ mit Frost)
        if key == 'chill' and 'slow' in spec:
            stack_factor = 1.0 - min(0.7, spec['slow'] + (st['stacks'] - 1) * 0.10)
            target.slow_factor = min(target.slow_factor, stack_factor)
            target.slow_timer = max(target.slow_timer, 0.25)

        # Shock: chance auf kurzen Stun
        if key == 'shock' and not is_player:
            if st['next_tick'] >= spec['tick'] - dt - 0.01:  # bei tick gerade
                if st['stacks'] >= 3:
                    target.stun_timer = max(getattr(target, 'stun_timer', 0), 0.4)

        if st['time_left'] <= 0:
            del target.status[key]


def _apply_status_damage(game, target, dmg, color, is_player):
    if is_player:
        # Spieler: über damage_player (respektiert Schild aber nicht invuln)
        if target.shield > 0:
            absorbed = min(target.shield, dmg)
            target.shield -= absorbed
            dmg -= absorbed
        if dmg > 0:
            target.hp -= dmg
            game.floaters.append(Floater(
                target.pos.x, target.pos.y - 30, int(dmg), color,
                dot=True))
            if target.hp <= 0:
                game.state = 'dead'
        return
    # Gegner — Ailment-Tick = DoT (gedeckt + halbe Alpha gerendert)
    target.hp -= dmg
    target.hit_flash = max(target.hit_flash, 0.08)
    game.floaters.append(Floater(
        target.pos.x, target.pos.y - target.height - 4, int(dmg), color,
        dot=True))
    if target.hp <= 0:
        from . import combat
        combat.kill_enemy(game, target)


def _trigger_combo(game, target, pair):
    combo = ELEMENT_COMBOS[pair]
    from . import progression
    eff = progression.effective(game.player)
    dmg = eff['damage'] * combo['dmg_mult']
    color = combo['color']
    radius = combo['radius']

    # AoE-Schaden an Gegnern in Radius (inkl. Ziel)
    for e in list(game.enemies):
        if (e.pos - target.pos).length() <= radius:
            game.hit_enemy(e, dmg)

    # Spezial-Nebenwirkungen
    if combo == ELEMENT_COMBOS[('burn', 'frost')]:
        # Splitter: Frost an Nachbarn
        for e in list(game.enemies):
            if (e.pos - target.pos).length() <= radius:
                apply(game, e, 'frost', stacks=3, _skip_combo=True)
    elif combo == ELEMENT_COMBOS[('burn', 'poison')]:
        # Toxische Detonation: Poison anwenden
        for e in list(game.enemies):
            if (e.pos - target.pos).length() <= radius:
                apply(game, e, 'poison', stacks=4, _skip_combo=True)
    elif combo == ELEMENT_COMBOS[('bleed', 'poison')]:
        # Verwesung: viele Bleed-Stacks am Ziel
        if target in game.enemies:
            apply(game, target, 'bleed', stacks=5, _skip_combo=True)
    elif combo == ELEMENT_COMBOS[('burn', 'shock')]:
        # Plasma: shock AoE
        for e in list(game.enemies):
            if (e.pos - target.pos).length() <= radius:
                apply(game, e, 'shock', stacks=2, _skip_combo=True)
    elif combo == ELEMENT_COMBOS[('bleed', 'shock')]:
        # Krampf: Stun
        if hasattr(target, 'stun_timer'):
            target.stun_timer = max(target.stun_timer, 1.2)

    # Visuell
    game.shake = max(game.shake, 8)
    game.spawn_particles(target.pos.x, target.pos.y, 40, color,
                         life_max=1.0, size_max=8)
    game.floaters.append(Floater(
        target.pos.x, target.pos.y - 50, combo['name'], color))

    # Beide Effekte am Ziel löschen
    if hasattr(target, 'status'):
        target.status.pop(pair[0], None)
        target.status.pop(pair[1], None)
