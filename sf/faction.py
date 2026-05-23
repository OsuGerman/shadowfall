"""Faction-Rep-System (WELT_AUFBAU 6.1).

Sieben Velgrad-Fraktionen mit Rep-Tracking, Tier-Unlocks und einer
Konflikt-Matrix (Tribunal ↔ Erblinde ↔ Knochenwitwen). Rep wird über
Quest-Rewards, Mob-Kills und NPC-Interaktionen verändert.

Lore-Quellen:
  - [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md) Teil 6 (Fraktionen)
  - [WELT_AUFBAU.md](WELT_AUFBAU.md) Sektion 6.1 (Currency-Flow)
  - [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md) (Lore-Tones)

API-Design:
  - `grant_rep(player, faction, amount)` — primärer Mutator. Wendet
    Konflikt-Matrix automatisch an.
  - `get_rep(player, faction)` — aktueller Wert (Default 0).
  - `get_tier(player, faction)` — aktueller Tier-Index (0=Unknown,
    1=Gesehen, 2=Verbündet, 3=Gewährt, 4=Geweiht).
  - `unlocked_perks(player, faction)` — Liste freigeschalteter Unlocks.
  - `apply_quest_reward(player, reward_dict, game)` — Helfer für
    Quest-Engine.

Konflikt-Mechanik:
  Wer einer Fraktion Treue gewährt, verliert bei den verfeindeten.
  Mahnmal-Gilde / Speerschwestern / Stille-Schritte sind neutral
  zueinander; Erblinde / Tribunal / Knochenwitwen sind das große
  Drei-Wege-Konflikt-Dreieck.

Save/Load:
  `player.faction_rep` ist ein einfacher dict[str, int]. Wird in
  [sf/save.py](sf/save.py) automatisch persistiert (Version-2-Saves
  enthalten das Feld; ältere Saves fallen auf {} zurück).
"""


# ============================================================
# FRAKTIONS-DEFINITIONEN
# ============================================================
# Schlüssel werden überall im Code als String referenziert; die Display-
# Namen in `FACTIONS[key]['name']` zeigt die UI an.

FACTIONS = {
    'mahnmal_gilde': dict(
        name='Mahnmal-Gilde',
        color=(220, 180, 110),
        aspect='Mahnmal',
        lore=('Bergungs- und Erinnerungs-Gilde aus Brassweir. Korven Vor '
              'führt — der trinkt, der zahlt, der erinnert sich.'),
    ),
    'erblinde_kirche': dict(
        name='Erblinde Kirche',
        color=(160, 140, 100),
        aspect='Ousen',
        lore=('Bruder Helst der Hundertjährige hat seine Augen abgebunden '
              'um klarer zu sehen. Pakt mit Ousen, dem zweiten Aspekt.'),
    ),
    'tribunal_asche': dict(
        name='Tribunal der Asche',
        color=(220, 100, 60),
        aspect='Valsa',
        lore=('Inquisitions-Sekte aus den Aschenfeldern. Vehren ist '
              'gefallen, aber das Tribunal hat einen neuen General '
              'ernannt. Er ist härter.'),
    ),
    'saattraeger': dict(
        name='Saatträger',
        color=(140, 200, 110),
        aspect='Nheyra',
        lore=('Ranger-Hain, der Saaten aus den welkenden Welten in diese '
              'pflanzt. Nheyra-Lineage; verbündet mit den Wandelnden.'),
    ),
    'knochenwitwen': dict(
        name='Knochenwitwen',
        color=(110, 60, 90),
        aspect='Shulavh',
        lore=('Vossharils Schwesternschaft. Hexen, die mit den Toten '
              'verhandeln. Shulavh-Berührt.'),
    ),
    'speerschwestern': dict(
        name='Speerschwestern',
        color=(240, 200, 100),
        aspect='Shulavh',
        lore=('Zhar-Eth-Wüsten-Schwesternschaft. Speerwurf, Mondbund. '
              'Tameris war eine; Naveth ist Kommandantin.'),
    ),
    'stille_schritte': dict(
        name='Stille Schritte',
        color=(180, 200, 240),
        aspect='Im-Nesh',
        lore=('Mönchs-Orden mit Quarterstaff-Pagoden. Im-Nesh-Echo; '
              'Atem-Disziplin als Lebensform.'),
    ),
}


# ============================================================
# REP-TIERS (WELT_AUFBAU 6.1: +50 / +100 / +200)
# ============================================================
# (lower_bound, tier_index, tier_name)
# Negative Werte: Verfeindet-Tiers.
REP_TIERS = [
    (-200, -3, 'Verflucht'),
    (-100, -2, 'Verfeindet'),
    ( -50, -1, 'Misstrauisch'),
    (   0,  0, 'Unbekannt'),
    (  10,  1, 'Gesehen'),
    (  50,  2, 'Verbündet'),
    ( 100,  3, 'Gewährt'),
    ( 200,  4, 'Geweiht'),
]


def get_tier(player, faction):
    """Returnt (tier_index, tier_name) für die aktuelle Rep des Players."""
    rep = get_rep(player, faction)
    cur = REP_TIERS[0]
    for entry in REP_TIERS:
        if rep >= entry[0]:
            cur = entry
    return cur[1], cur[2]


# ============================================================
# UNLOCKS — was wird bei welchem Tier freigeschaltet?
# ============================================================
# Pro Fraktion: Liste von (rep_threshold, unlock_id, label).
# unlock_id ist Engine-Hook (Bool-Check in zukünftigen Systemen);
# label wird in der UI angezeigt.
UNLOCKS = {
    'mahnmal_gilde': [
        ( 50, 'vendor_discount_small', 'Vendor-Rabatt 10 %'),
        (100, 'exclusive_crossbows',   'Exklusive Crossbows bei Korven'),
        (200, 'korven_endgame_quest',  'Korven-Endgame-Quest verfügbar'),
    ],
    'erblinde_kirche': [
        ( 50, 'pact_stones_unlock',    'Pact-Stones zugänglich'),
        (100, 'exclusive_sceptres',    'Exklusive Sceptres bei Helst'),
        (200, 'aspekt_choice',         'Aspekt-Wahl im Schrein'),
    ],
    'tribunal_asche': [
        ( 50, 'tribunal_steel',        'Inquisitions-Klinge craftbar'),
        (100, 'tribunal_konstrukt',    'Tribunal-Konstrukt-Begleiter'),
        (200, 'inquisitor_rank',       'Inquisitor-Rang (Lore-Reveal)'),
    ],
    'saattraeger': [
        ( 50, 'saatkind_bow',          'Saatkind-Bow als Faction-Drop'),
        (100, 'wandelnde_form_slot',   'Wandelnde-Form Skill-Slot'),
        (200, 'nheyra_blessing',       'Nheyra-Blessing-Trigger'),
    ],
    'knochenwitwen': [
        ( 50, 'vossharils_bruder',     'Vossharils-Bruder-Dagger'),
        (100, 'skeleton_familiar',     'Skelett-Familiar-Beschwörung'),
        (200, 'shulavh_voice',         'Shulavhs Stimme — Lore-Reveal'),
    ],
    'speerschwestern': [
        ( 50, 'mondbinder_spear',      'Zhar-Eth-Mondbinder-Spear'),
        (100, 'schwestern_faden_buff', 'Schwestern-Faden-Buff (Aura)'),
        (200, 'mondbund_ascension',    'Mondbund-Ascendancy-Path'),
    ],
    'stille_schritte': [
        ( 50, 'drei_pagoden',          'Quarterstaff-Drei-Pagoden Skill'),
        (100, 'atem_disziplin',        'Atem-Disziplin-Passive'),
        (200, 'inneres_echo',          'Inneres Echo — Spirit-Doppel-Cap'),
    ],
}


def unlocked_perks(player, faction):
    """Liste der bereits freigeschalteten Unlock-IDs für diese Fraktion."""
    rep = get_rep(player, faction)
    out = []
    for threshold, unlock_id, label in UNLOCKS.get(faction, ()):
        if rep >= threshold:
            out.append((unlock_id, label))
    return out


def has_unlock(player, faction, unlock_id):
    """True wenn der spezifische Unlock-ID freigeschaltet ist.

    Engine-Hook für „nur wenn ≥ 50 Mahnmal-Rep gewähre Vendor-Rabatt".
    """
    for uid, _label in unlocked_perks(player, faction):
        if uid == unlock_id:
            return True
    return False


# ============================================================
# KONFLIKT-MATRIX
# ============================================================
# Wer Rep bei `source` gewinnt/verliert, kriegt automatisch
# anti-gewichtete Side-Effects bei den verbundenen Fraktionen.
#
# Format: source → [(other, factor)]
# Factor=-0.5 bedeutet: +20 bei source → -10 bei other.
# Factor=+0.3 bedeutet: +20 bei source → +6 bei other (Allianz).
#
# WELT_AUFBAU 6.1 nennt das Drei-Wege-Konflikt-Dreieck zwischen
# Erblinde Kirche, Tribunal der Asche und Knochenwitwen. Andere
# Fraktionen sind neutral.
CONFLICT_MATRIX = {
    'erblinde_kirche': [
        ('tribunal_asche', -0.5),
        ('knochenwitwen',  -0.3),
    ],
    'tribunal_asche': [
        ('erblinde_kirche', -0.5),
        ('knochenwitwen',   -0.5),
        ('saattraeger',     -0.3),   # Tribunal jagt Saatträger als „Heiden"
    ],
    'knochenwitwen': [
        ('erblinde_kirche',  -0.3),
        ('tribunal_asche',   -0.5),
        ('speerschwestern',  +0.2),  # Shulavh-Lineage-Allianz
    ],
    'saattraeger': [
        ('tribunal_asche',  -0.3),
    ],
    'speerschwestern': [
        ('knochenwitwen',   +0.2),
    ],
    # Mahnmal-Gilde + Stille-Schritte sind neutral zu allen.
}


# ============================================================
# CORE-API
# ============================================================

def get_rep(player, faction):
    """Aktueller Rep-Wert (Default 0).

    Toleriert Player ohne `faction_rep`-Attr (gibt 0 zurück).
    """
    rep_dict = getattr(player, 'faction_rep', None)
    if rep_dict is None:
        return 0
    return rep_dict.get(faction, 0)


def _set_rep(player, faction, value):
    """Internal: setzt Rep direkt (clamped auf [-200, 200])."""
    if not hasattr(player, 'faction_rep') or player.faction_rep is None:
        player.faction_rep = {}
    player.faction_rep[faction] = max(-200, min(200, int(value)))


def grant_rep(player, faction, amount, _depth=0):
    """Primärer Mutator. Wendet CONFLICT_MATRIX automatisch an.

    Returnt eine Liste der Tier-Übergänge: `[(faction, old_tier, new_tier)]`
    — Caller kann darauf reagieren (Toast, Unlock-Notification).

    `_depth` ist interner Rekursions-Schutz (Konflikt-Matrix triggert
    nur einmal, nicht kaskadierend).
    """
    if faction not in FACTIONS:
        return []
    transitions = []
    old_tier_idx, _ = get_tier(player, faction)
    new_value = get_rep(player, faction) + amount
    _set_rep(player, faction, new_value)
    new_tier_idx, new_tier_name = get_tier(player, faction)
    if new_tier_idx != old_tier_idx:
        transitions.append((faction, old_tier_idx, new_tier_idx))

    # Konflikt-Matrix nur einmal anwenden (kein Kaskaden-Loop)
    if _depth == 0:
        for other, factor in CONFLICT_MATRIX.get(faction, ()):
            delta = int(amount * factor)
            if delta == 0:
                continue
            transitions.extend(grant_rep(player, other, delta, _depth=1))
    return transitions


# ============================================================
# QUEST-INTEGRATION (Update #117, WELT_AUFBAU 6.1)
# ============================================================

def apply_quest_reward(player, reward_dict, game=None):
    """Wird vom Quest-Engine bei `_mark_complete` aufgerufen.

    Erwartet `reward_dict.get('faction_rep')` als `{faction: amount}`-
    Mapping. Wendet die Beträge inkl. Konflikt-Matrix an.

    Optional: emittiert Tier-Übergangs-Toasts via `game.toast`.
    """
    rep_rewards = reward_dict.get('faction_rep') if reward_dict else None
    if not rep_rewards:
        return []
    all_transitions = []
    for faction, amount in rep_rewards.items():
        transitions = grant_rep(player, faction, amount)
        all_transitions.extend(transitions)
    # UI-Feedback
    if game is not None and hasattr(game, 'toast'):
        for faction, old_t, new_t in all_transitions:
            cfg = FACTIONS.get(faction, {})
            name = cfg.get('name', faction)
            color = cfg.get('color', (220, 200, 140))
            _idx, tier_name = get_tier(player, faction)
            direction = 'aufgestiegen' if new_t > old_t else 'verfallen'
            game.toast(
                f'{name}: {direction} → „{tier_name}"', color)
    return all_transitions


def faction_display_name(faction):
    """Lore-Display-Name oder Fallback auf Key."""
    cfg = FACTIONS.get(faction)
    return cfg['name'] if cfg else faction


def faction_color(faction):
    """Lore-Akzent-Farbe."""
    cfg = FACTIONS.get(faction)
    return cfg['color'] if cfg else (220, 200, 140)


def all_factions():
    """Returnt Liste aller Fraktions-Keys (für UI-Iteration)."""
    return list(FACTIONS.keys())
