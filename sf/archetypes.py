"""Monster-Archetypen — die 14 Verhaltens-Templates aus
POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG Teil F.

Jeder Archetyp bündelt:
  - default sight & hearing-Profil
  - Engagement-Pattern (melee/ranged/kite/charge/stalk/...)
  - pack-Awareness-Radius
  - Signature-Attack-Hint (was der Combat-Code priorisiert)
  - „uses_state_machine" → ob diese Archetyp-Variante die D-AI nutzt

Konkrete Monster (Salzgekreuzter, Echo-Senator, Asch-Soldat, ...) leben
in `sf/bestiary.py` und referenzieren einen Archetyp.

Lore-Anker: jede Archetyp-Beschreibung verweist auf das Bestiarium-Beispiel,
damit Designer schnell den passenden Mob-Look findet.
"""

from . import ai as _ai


# ============================================================
# ARCHETYP-IDENTIFIER
# ============================================================
class Archetype:
    BRUTE         = 'brute'
    SKIRMISHER    = 'skirmisher'
    CASTER        = 'caster'
    RANGED        = 'ranged'
    SUPPORT       = 'support'      # Heal/Buff/Aura
    SUMMONER      = 'summoner'
    CHARGER       = 'charger'
    STALKER       = 'stalker'
    ELITE         = 'elite'        # Rare-Tier
    CHAMPION      = 'champion'     # Mini-Boss-Tier
    GUARDIAN      = 'guardian'     # Shield-block
    EXPLODER      = 'exploder'
    FLYER         = 'flyer'
    TUNNELER      = 'tunneler'


# ============================================================
# ARCHETYP-DEFINITIONEN
# ============================================================
# Felder pro Archetyp:
#   sight_profile, hearing_profile         (Keys in ai.SIGHT_PROFILES / HEARING_PROFILES)
#   engage                                 → 'melee' | 'ranged' | 'kite' | 'charge' | 'stalk' | 'stationary' | 'aerial' | 'burrow' | 'support'
#   pack_alert_radius_px                   → Range, in der Allies mit-aggroen
#   prefers_distance_px                    → Idealabstand zum Spieler (für Kiter)
#   uses_state_machine                     → ob D-AI aktiviert wird
#   sticky_aggro                           → für Mini-Boss/Champion (kein RESET)
#   priority_kill                          → True für SUPPORT/HEALER (Spieler-Hint)
#   notes_lore                             → freier Lore-Hint
ARCHETYPES = {
    Archetype.BRUTE: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='melee', pack_alert_radius_px=8 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Tank, langsame schwere Hits — Ogre, Big Zombie, Mark-Krieger.",
    ),
    Archetype.SKIRMISHER: dict(
        sight_profile='skirmisher', hearing_profile='default',
        engage='melee', pack_alert_radius_px=10 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Schnell, Hit-and-Run — Goblin, Cultist, Goldstaub-Diener.",
    ),
    Archetype.CASTER: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='ranged', pack_alert_radius_px=12 * 32,
        prefers_distance_px=10 * 32, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Telegraphed Spells — Witch, Warlock, Ertrunkenes Echo.",
    ),
    Archetype.RANGED: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='kite', pack_alert_radius_px=12 * 32,
        prefers_distance_px=12 * 32, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Pfeile/Bolts mit Kiting — Archer, Crossbowman.",
    ),
    Archetype.SUPPORT: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='support', pack_alert_radius_px=14 * 32,
        prefers_distance_px=8 * 32, uses_state_machine=True,
        sticky_aggro=False, priority_kill=True,
        notes_lore="Heilt Allies, buffs — Cleric, Verfallener Magister.",
    ),
    Archetype.SUMMONER: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='ranged', pack_alert_radius_px=14 * 32,
        prefers_distance_px=10 * 32, uses_state_machine=True,
        sticky_aggro=False, priority_kill=True,
        notes_lore="Spawned Adds dauerhaft — Bone Witch, Knochenwitwen-Schwester.",
    ),
    Archetype.CHARGER: dict(
        sight_profile='beast',     hearing_profile='beast',
        engage='charge', pack_alert_radius_px=6 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Sprintet auf Spieler, telegraphed-explodiert — "
                   "Demon-Dog, Krustenkrabbe, Asch-Wolf.",
    ),
    Archetype.STALKER: dict(
        sight_profile='stalker',   hearing_profile='stalker',
        engage='stalk', pack_alert_radius_px=4 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Stealth/Backstab — Shadow, Assassin, Inquisitions-Klingenmesser.",
    ),
    Archetype.ELITE: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='melee', pack_alert_radius_px=8 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Stronger version mit 1-2 Affixes — Goldener Champion.",
    ),
    Archetype.CHAMPION: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='melee', pack_alert_radius_px=0,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=True, priority_kill=False,
        notes_lore="Mini-Boss, eigenes Moveset — Salzhüter-Brut, Pack-Leader.",
    ),
    Archetype.GUARDIAN: dict(
        sight_profile='guard',     hearing_profile='default',
        engage='melee', pack_alert_radius_px=8 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Schildblock vorn, Bash-Counter — Knight, Glasgolden-Wächter, "
                   "Tribunal-Konstrukt, Spiegel-Hüter.",
    ),
    Archetype.EXPLODER: dict(
        sight_profile='beast',     hearing_profile='default',
        engage='charge', pack_alert_radius_px=4 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="DoT-Aura, Death-Explosion — Plague-Zombie.",
    ),
    Archetype.FLYER: dict(
        sight_profile='eyestalk',  hearing_profile='default',
        engage='aerial', pack_alert_radius_px=12 * 32,
        prefers_distance_px=6 * 32, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Air-Layer, Dive-Bomb — Bat, Wyvern-Whelp, Möwen-Schwarm.",
    ),
    Archetype.TUNNELER: dict(
        sight_profile='blind',     hearing_profile='beast',
        engage='burrow', pack_alert_radius_px=6 * 32,
        prefers_distance_px=0, uses_state_machine=True,
        sticky_aggro=False, priority_kill=False,
        notes_lore="Burrowed Pop-Up — Sandworm, Wurzel-Spinne, Krustenkrabbe.",
    ),
}


def get(archetype_id):
    """Dict-Lookup mit Fallback auf BRUTE, damit Tipos nicht crashen."""
    return ARCHETYPES.get(archetype_id, ARCHETYPES[Archetype.BRUTE])


def apply_to_enemy(e, archetype_id):
    """Setzt sight/hearing/engage-Felder + state-machine-Opt-In auf einem Enemy.

    Wird einmal beim Spawn aufgerufen (siehe bestiary.spawn_bestiary_mob).
    """
    cfg = get(archetype_id)
    e.archetype = archetype_id
    e.sight   = _ai.SIGHT_PROFILES.get(cfg['sight_profile'], _ai.SIGHT_PROFILES['guard'])
    e.hearing = _ai.HEARING_PROFILES.get(cfg['hearing_profile'], _ai.HEARING_PROFILES['default'])
    e.engage_mode = cfg['engage']
    e.pack_alert_radius_px = cfg['pack_alert_radius_px']
    e.prefers_distance_px = cfg['prefers_distance_px']
    e.uses_state_machine = cfg['uses_state_machine']
    e.sticky_aggro = cfg['sticky_aggro']
    e.priority_kill = cfg['priority_kill']
    # State-Machine-Initial-Setup
    if cfg['uses_state_machine']:
        e.ai_state = _ai.AIState.IDLE
        e.ai_state_t = 0.0
        e.last_known_player_pos = None
        e.ai_lost_sight_t = 0.0
        # Round-Robin sight-tick phase
        import random as _r
        e.ai_sight_tick_phase = _r.randint(0, 9)
        # Facing-Default: nach unten (Iso-Standard)
        if not hasattr(e, 'facing_deg'):
            e.facing_deg = 90.0
