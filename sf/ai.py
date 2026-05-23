"""Monster-KI: State-Machine, Sichtfeld, Gehör, Patrouille, Pack-Awareness.

Implementiert PLAN-Tasks D-01..D-15 aus dem Erweiterungs-Briefing Teil D.

Architektur ist additiv: existierende `enemies.update_enemy_ai` bleibt der
Default-Pfad. Nur Gegner mit `e.uses_state_machine = True` durchlaufen
`tick_ai_state(game, e, dt)`. Bestiarium-Mobs (siehe `sf/bestiary.py`) opten
sich beim Spawn ein.

Velgrad-Lore-Notiz: Manche Wesen sehen NICHT mit Augen (Erblinde Mönche,
Faden-Gebundene, Nicht-Männer). Das Sight-Cone-System unterstützt FOV=0,
gekoppelt mit alternativem Hearing/Smell/Faden-Sense.
"""

import math
import random


# ============================================================
# STATE-ENUM (D-01)
# ============================================================
class AIState:
    IDLE   = 'idle'      # Steht, evtl. Idle-Anim
    PATROL = 'patrol'    # Bewegt sich entlang Pfad / im Area-Random
    ALERT  = 'alert'     # Hat etwas gehört/gesehen, untersucht
    AGGRO  = 'aggro'     # Hat Player, kämpft (= Standard-Combat-AI)
    SEARCH = 'search'    # Sicht verloren, sucht letzte bekannte Position
    RESET  = 'reset'     # Auf dem Weg zurück zum Patrol-Pfad, regeneriert


# ============================================================
# SICHTFELD-PROFILE (D-02, D-03)
# ============================================================
class SightCone:
    """Standard-Humanoid-Sichtfeld."""
    __slots__ = ('fov_deg', 'range_px', 'peripheral_fov_deg',
                 'peripheral_range_px', 'requires_los')

    def __init__(self, fov_deg=90, range_px=480,
                 peripheral_fov_deg=180, peripheral_range_px=190,
                 requires_los=True):
        # Briefing nennt Meter — wir nutzen Pixel und skalieren grob mit
        # 32 px ≈ 1 m (Pygame-Iso-Standard im Projekt).
        self.fov_deg = fov_deg
        self.range_px = range_px
        self.peripheral_fov_deg = peripheral_fov_deg
        self.peripheral_range_px = peripheral_range_px
        self.requires_los = requires_los


# Vorgefertigte Profile aus Briefing D.3 + Bestiarium-Beobachtungen.
SIGHT_PROFILES = {
    # Update #27: peripheral_fov auf 360° für alle aktiven Profile.
    # Lore-Justification: Mobs „spüren" Spieler in Nahdistanz auch von
    # hinten (Instinkt, Geräusche, Wärme). Hauptblick bleibt directional.
    'guard':       SightCone(fov_deg=110, range_px=580,
                             peripheral_fov_deg=360, peripheral_range_px=260),
    'beast':       SightCone(fov_deg=160, range_px=420,
                             peripheral_fov_deg=360, peripheral_range_px=240),
    'sleeping':    SightCone(fov_deg=0,   range_px=0),
    'blind':       SightCone(fov_deg=0,   range_px=0),
    'eyestalk':    SightCone(fov_deg=360, range_px=340,
                             peripheral_fov_deg=360, peripheral_range_px=340),
    'spectral':    SightCone(fov_deg=220, range_px=640,
                             peripheral_fov_deg=360, peripheral_range_px=360,
                             requires_los=False),
    'hollowed':    SightCone(fov_deg=90,  range_px=420,
                             peripheral_fov_deg=360, peripheral_range_px=200),
    'skirmisher':  SightCone(fov_deg=140, range_px=460,
                             peripheral_fov_deg=360, peripheral_range_px=240),
    'stalker':     SightCone(fov_deg=80,  range_px=460,
                             peripheral_fov_deg=360, peripheral_range_px=220),
}


# ============================================================
# GEHÖR (D-04)
# ============================================================
# Player-Noise-Quellen → Pixel-Range (32 px ≈ 1 m).
PLAYER_NOISE = {
    'walk':         3 * 32,   # 3 m
    'sprint':       8 * 32,   # 8 m
    'dodge':        6 * 32,
    'cast_quiet':   8 * 32,
    'cast_medium': 16 * 32,
    'cast_loud':   24 * 32,   # Comet, Earthquake-Slam, Boss-Roar
}


class HearingProfile:
    __slots__ = ('range_px', 'ignores_los', 'stealth_bonus_mult')

    def __init__(self, range_px=320, ignores_los=True,
                 stealth_bonus_mult=1.0):
        self.range_px = range_px
        self.ignores_los = ignores_los
        # Multiplikator, der Player-Noise erhöht (Quiet-Movement-Passive
        # kann hier <1.0 für den Player gesetzt werden, siehe D-06).
        self.stealth_bonus_mult = stealth_bonus_mult


HEARING_PROFILES = {
    'default':   HearingProfile(range_px=320),
    'beast':     HearingProfile(range_px=480),       # Smell-ähnlich
    'stalker':   HearingProfile(range_px=580),       # gute Ohren
    'blind':     HearingProfile(range_px=480),       # nur Hearing
    'deaf':      HearingProfile(range_px=0),         # niemals durch Sound
}


# ============================================================
# PATROL-PATTERNS (D-07)
# ============================================================
class PatrolPattern:
    WAYPOINT   = 'waypoint'      # Spline mit 3-8 Punkten
    RANDOM_AREA= 'random_area'   # Random innerhalb Spawn-Area
    STATIONARY = 'stationary'    # Stehen + Scan-Rotation


# ============================================================
# SICHT-CHECK
# ============================================================
def _angle_diff_deg(a, b):
    """Kleinster Winkelabstand a,b in Grad."""
    d = (a - b + 180) % 360 - 180
    return abs(d)


def line_of_sight(game, x1, y1, x2, y2):
    """True wenn freie Sichtlinie. Nutzt grid.collide_circle als Wand-Test.

    Sampled 8 Punkte entlang der Strecke — günstig genug für ~5–10
    Sight-Checks pro Frame; Round-Robin (D-15) verteilt das eh.
    """
    grid = getattr(game, 'grid', None)
    if grid is None:
        return True  # offene Karte → freie Sicht
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1.0:
        return True
    steps = 8
    for k in range(1, steps):
        t = k / steps
        x = x1 + dx * t
        y = y1 + dy * t
        if grid.collide_circle(x, y, 4):
            return False
    return True


def sees_player(game, e):
    """True wenn der Spieler im Sicht-Kegel des Gegners ist.

    Berücksichtigt facing (`e.facing_deg`), FOV-Kegel + peripherer Kegel,
    Range und Line-of-Sight. Default-Verhalten ohne sight (alte AI): True.
    """
    sight = getattr(e, 'sight', None)
    if sight is None:
        return True  # Old-AI-Mobs sind „magnetisch" wie bisher
    if sight.fov_deg <= 0 and sight.peripheral_fov_deg <= 0:
        return False
    p = game.player.pos
    dx = p.x - e.pos.x
    dy = p.y - e.pos.y
    dist = math.hypot(dx, dy)
    if dist > max(sight.range_px, sight.peripheral_range_px):
        return False
    angle_to = math.degrees(math.atan2(dy, dx))
    facing = getattr(e, 'facing_deg', 0.0)
    delta = _angle_diff_deg(angle_to, facing)
    # Haupt-Kegel
    in_main = (delta <= sight.fov_deg * 0.5 and dist <= sight.range_px)
    # Peripherer Kegel
    in_peri = (delta <= sight.peripheral_fov_deg * 0.5
               and dist <= sight.peripheral_range_px)
    if not (in_main or in_peri):
        return False
    if sight.requires_los and not line_of_sight(game, e.pos.x, e.pos.y, p.x, p.y):
        return False
    return True


def hears_player(game, e):
    """True wenn der Spieler durch Gehör erkannt wird.

    Nutzt `game.player.current_noise_px` (Default `walk`-Wert). Skills,
    die laute Casts emittieren, können diesen Wert kurz hochsetzen.

    PLAN D-05 (Update #98): Wind-Vector — wenn Mob im `beast`-Profil ist
    (Smell-Sensor via Olfactory), wird Player-Position via Wind-Direction
    leicht skaliert: stromaufwärts × 1.5, stromabwärts × 0.6.
    """
    hearing = getattr(e, 'hearing', None)
    if hearing is None or hearing.range_px <= 0:
        return False
    p = game.player
    noise_px = getattr(p, 'current_noise_px', PLAYER_NOISE['walk'])
    noise_px = int(noise_px * hearing.stealth_bonus_mult)
    if noise_px <= 0:
        return False
    dx = p.pos.x - e.pos.x
    dy = p.pos.y - e.pos.y
    dist = math.hypot(dx, dy)
    # D-05 Wind-Vector: Beast-Mobs riechen besser stromaufwärts.
    if getattr(e, 'is_beast', False) and dist > 0:
        # Wind aus weather-Service oder default Süd-Wind (0, -1)
        wind = getattr(getattr(game, 'weather', None),
                       'wind_vector', None) or (0.0, -1.0)
        # Player→Mob-Richtung normalisieren
        nx, ny = dx / dist, dy / dist
        # Dot-Product: > 0 wenn Player in Windrichtung (Mob upwind, riecht)
        dot = nx * wind[0] + ny * wind[1]
        smell_mult = 1.0 + dot * 0.5  # +50% upwind, -50% downwind
        noise_px = int(noise_px * smell_mult)
    return dist <= min(hearing.range_px, noise_px + hearing.range_px)


# ============================================================
# STATE-MACHINE (D-01, D-08, D-11)
# ============================================================
# Konfiguration: Zeiten in Sekunden, Distanzen in px (32 px ≈ 1 m).
ALERT_DURATION_S      = 4.0
SEARCH_DURATION_S     = 6.0
RESET_HEAL_DURATION_S = 3.0
LEASH_LOSE_SIGHT_S    = 5.0
LEASH_MAX_RANGE_PX    = 30 * 32  # 30 m


def _enter_state(e, state, now_t=None):
    e.ai_state = state
    e.ai_state_t = 0.0
    if state == AIState.ALERT:
        e.ai_alert_left = ALERT_DURATION_S
    elif state == AIState.SEARCH:
        e.ai_search_left = SEARCH_DURATION_S
    elif state == AIState.RESET:
        e.ai_reset_heal_left = RESET_HEAL_DURATION_S
        e.ai_reset_start_hp = e.hp


def tick_ai_state(game, e, dt):
    """Aktualisiert die State-Machine. Wird pro Frame aus enemies.update_enemy_ai
    aufgerufen, falls `e.uses_state_machine` True ist.

    Returnt einen Hint-String, was der Combat-Code als Nächstes tun soll:
      - 'engage'  → normale Aggro-Routine (Movement+Attack)
      - 'investigate' → bewegt sich zur last_known_player_pos
      - 'patrol'      → bewegt sich auf Patrol-Pfad
      - 'idle'        → steht still
    """
    if not hasattr(e, 'ai_state'):
        _enter_state(e, AIState.IDLE)
    e.ai_state_t = getattr(e, 'ai_state_t', 0.0) + dt

    # 1) Sicht/Gehör polln. D-15 (Update #97): Round-Robin Sight-Cache.
    # Volle LOS-Berechnung ist teuer (Raycast). Wir cachen pro Mob das
    # letzte sees-Resultat in `_cached_sees` + Frame-Counter; nur jeder
    # 3. Frame wird neu berechnet (außer AGGRO-State braucht Live-Daten).
    frame = getattr(game, '_ai_frame_phase', 0)
    cached_sees = getattr(e, '_cached_sees', None)
    cached_frame = getattr(e, '_cached_sees_frame', -10)
    if (e.ai_state == AIState.AGGRO
            or cached_sees is None
            or (frame - cached_frame) >= 3):
        sees = sees_player(game, e)
        e._cached_sees = sees
        e._cached_sees_frame = frame
    else:
        sees = cached_sees
    hears = hears_player(game, e)

    # Memorize letzte Player-Position bei sicherem Kontakt
    if sees:
        e.last_known_player_pos = (game.player.pos.x, game.player.pos.y)
        e.ai_lost_sight_t = 0.0

    state = e.ai_state

    # 2) Transitions
    # Update #27: Aggressivere AI — der User-Feedback war „Gegner greifen
    # nicht an". Fixes:
    #   - Direkt-AGGRO bei nahem Sicht-Kontakt (≤220 px, kein ALERT-Detour)
    #   - HP-Loss seit letztem Tick → SOFORT AGGRO (player hat angegriffen)
    #   - Anhaltendes Hören in ALERT → ebenfalls AGGRO (player macht
    #     Krach in der Nähe, ist aggressiv)
    player_dist = (game.player.pos - e.pos).length()
    hp_changed = (getattr(e, '_ai_last_hp', e.hp) - e.hp) > 0.001
    e._ai_last_hp = e.hp

    if state == AIState.IDLE:
        if hp_changed:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif sees and player_dist <= 220:
            # Naher Sicht-Kontakt → sofort AGGRO
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif sees or hears:
            _enter_state(e, AIState.ALERT)
        elif _has_patrol(e):
            _enter_state(e, AIState.PATROL)

    elif state == AIState.PATROL:
        if hp_changed:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif sees and player_dist <= 220:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif sees or hears:
            _enter_state(e, AIState.ALERT)

    elif state == AIState.ALERT:
        e.ai_alert_left = getattr(e, 'ai_alert_left', ALERT_DURATION_S) - dt
        # Update #27: ALERT akkumuliert Hearing-Zeit. Nach 1.0s Dauer-Hören
        # geht er auf AGGRO (player IST nah genug zu hören = aggressiv).
        if hears:
            e._ai_hear_acc = getattr(e, '_ai_hear_acc', 0.0) + dt
        else:
            e._ai_hear_acc = max(0.0, getattr(e, '_ai_hear_acc', 0.0) - dt * 0.5)
        if hp_changed:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif sees:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif e._ai_hear_acc >= 1.0:
            _enter_state(e, AIState.AGGRO)
            _on_aggro_enter(game, e)
        elif e.ai_alert_left <= 0:
            _enter_state(e, AIState.PATROL if _has_patrol(e) else AIState.IDLE)

    elif state == AIState.AGGRO:
        # Verloren-Sicht-Zähler
        if not sees and not hears:
            e.ai_lost_sight_t = getattr(e, 'ai_lost_sight_t', 0.0) + dt
        # Leash: weit weg & lange ohne Sicht → SEARCH
        far = (game.player.pos - e.pos).length() > LEASH_MAX_RANGE_PX
        if getattr(e, 'sticky_aggro', False):
            # Bosse/Elites mit sticky aggro halten bis Tod
            pass
        elif far and e.ai_lost_sight_t >= LEASH_LOSE_SIGHT_S:
            _enter_state(e, AIState.SEARCH)

    elif state == AIState.SEARCH:
        e.ai_search_left = getattr(e, 'ai_search_left', SEARCH_DURATION_S) - dt
        if sees:
            _enter_state(e, AIState.AGGRO)
        elif e.ai_search_left <= 0:
            _enter_state(e, AIState.RESET)

    elif state == AIState.RESET:
        # Heal zurück über RESET_HEAL_DURATION_S auf full HP
        e.ai_reset_heal_left = getattr(e, 'ai_reset_heal_left',
                                       RESET_HEAL_DURATION_S) - dt
        # Linearer HP-Regen
        target_hp = e.hp_max
        start_hp = getattr(e, 'ai_reset_start_hp', e.hp)
        prog = 1.0 - max(0.0, e.ai_reset_heal_left) / RESET_HEAL_DURATION_S
        e.hp = min(e.hp_max, start_hp + (target_hp - start_hp) * prog)
        if e.ai_reset_heal_left <= 0:
            _enter_state(e, AIState.PATROL if _has_patrol(e) else AIState.IDLE)

    # 3) Action-Hint zurückgeben
    if state == AIState.AGGRO:
        return 'engage'
    if state == AIState.ALERT or state == AIState.SEARCH:
        return 'investigate'
    if state == AIState.PATROL:
        return 'patrol'
    return 'idle'


def _has_patrol(e):
    return getattr(e, 'patrol_pattern', None) is not None


def _on_aggro_enter(game, e):
    """Pack-Awareness (D-09): Alle Pack-Members im Radius gehen mit
    leichter Verzögerung ebenfalls in ALERT/AGGRO und übernehmen die
    last_known_player_pos vom Alerter — sonst stehen sie ratlos rum.
    """
    radius = getattr(e, 'pack_alert_radius_px', 8 * 32)
    if radius <= 0:
        return
    pack_id = getattr(e, 'pack_id', None)
    shared_lk = (game.player.pos.x, game.player.pos.y)
    for ally in getattr(game, 'enemies', ()):
        if ally is e or ally.dying:
            continue
        if not getattr(ally, 'uses_state_machine', False):
            continue
        same_pack = pack_id is not None and getattr(ally, 'pack_id', None) == pack_id
        in_range = (ally.pos - e.pos).length() <= radius
        if not (same_pack or in_range):
            continue
        # Last-Known-Pos propagieren — der Allie weiß jetzt, wo der Player war.
        ally.last_known_player_pos = shared_lk
        if getattr(ally, 'ai_pending_alert', None) is None:
            ally.ai_pending_alert = random.uniform(0.5, 1.5)


def tick_pending_alerts(game, dt):
    """Tickt die verzögerten Pack-Alerts (D-09).

    Wird aus enemies.update_enemy_ai oder besser zentral aus game.update
    aufgerufen, EINMAL pro Frame nach den AI-Ticks.
    """
    for e in getattr(game, 'enemies', ()):
        if not getattr(e, 'uses_state_machine', False) or e.dying:
            continue
        pend = getattr(e, 'ai_pending_alert', None)
        if pend is None:
            continue
        pend -= dt
        if pend <= 0:
            e.ai_pending_alert = None
            if e.ai_state in (AIState.IDLE, AIState.PATROL):
                _enter_state(e, AIState.ALERT)
        else:
            e.ai_pending_alert = pend


# ============================================================
# ROUND-ROBIN SIGHT-TICK-RATE (D-15)
# ============================================================
# Caller setzt e.ai_sight_tick_phase = random.randint(0, 9) beim Spawn.
# In jedem Frame inkrementiert game ein _sight_tick_phase und nur Gegner
# mit passendem Phase-Match führen den expensive sight-Raycast aus.
SIGHT_TICK_DIV = 6


def should_tick_sight(e, frame_phase):
    """True wenn dieser Gegner in diesem Frame seinen sight-Check macht."""
    return (getattr(e, 'ai_sight_tick_phase', 0) % SIGHT_TICK_DIV) == (frame_phase % SIGHT_TICK_DIV)


# ============================================================
# LOD-TICK (D-14)
# ============================================================
def lod_tick_factor(e, player_pos):
    """Returnt einen Multiplikator für die AI-Tick-Frequenz.

    1.0 = Full-Tick (≤30 m). 0.2 = sparsam (30–80 m). 0.0 = frozen (>80 m).
    """
    dist = (e.pos - player_pos).length()
    if dist <= 30 * 32:
        return 1.0
    if dist <= 80 * 32:
        return 0.2
    return 0.0
