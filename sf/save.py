"""Save/Load: persistierter Spieler-Zustand als JSON.

Update #133 (Z-01/Z-02): Multi-Save-Slot-System.
- 3 nummerierte Slots: `~/.shadowfall_save_slot1.json` .. `_slot3.json`
- Legacy `~/.shadowfall_save.json` wird beim ersten Load als Slot 1 gelesen
  (Backward-Compat).
- Module-level `_active_slot` bestimmt welcher Slot von save_game/load_game
  benutzt wird; via `set_active_slot(n)` setzbar.
- Hardcore-Flag pro Slot persistiert; bei Tod im Hardcore-Mode wird der
  Slot komplett gelöscht (Permadeath).
"""

import json
import os
import time
from pathlib import Path

from .items import Item


# Legacy-Pfad (vor Update #133); wird bei Bedarf als Slot 1 gelesen.
LEGACY_SAVE_PATH = Path.home() / '.shadowfall_save.json'
SAVE_PATH = LEGACY_SAVE_PATH  # Backward-Compat-Alias (alte Imports)

MAX_SLOTS = 3
_active_slot = 1


def slot_path(slot):
    """Returnt den absoluten Pfad für einen Save-Slot (1..MAX_SLOTS)."""
    return Path.home() / f'.shadowfall_save_slot{int(slot)}.json'


def set_active_slot(slot):
    """Setzt den aktiven Save-Slot (1..MAX_SLOTS).  save_game / load_game
    nutzen ab da diesen Slot per Default.
    """
    global _active_slot
    slot = int(slot)
    if 1 <= slot <= MAX_SLOTS:
        _active_slot = slot


def get_active_slot():
    return _active_slot


def _effective_path(slot=None):
    """Returnt den Save-Path für `slot` oder den active_slot.

    Backward-Compat: wenn der explizite Slot-File nicht existiert UND
    der Legacy-Path existiert UND wir Slot 1 ansprechen, gib Legacy.
    """
    s = int(slot) if slot is not None else _active_slot
    sp = slot_path(s)
    if s == 1 and not sp.exists() and LEGACY_SAVE_PATH.exists():
        return LEGACY_SAVE_PATH
    return sp


def _item_to_dict(item):
    if item is None:
        return None
    return {
        'slot': item.slot,
        'rarity': item.rarity,
        'name': item.name,
        'affixes': list(item.affixes),
        'ilvl': item.ilvl,
        'sockets': list(item.sockets),
        'set_id': item.set_id,
    }


def _item_from_dict(d):
    if d is None:
        return None
    return Item(
        slot=d['slot'], rarity=d['rarity'], name=d['name'],
        affixes=[tuple(a) for a in d['affixes']], ilvl=d['ilvl'],
        sockets=list(d['sockets']),
        set_id=d.get('set_id'),
    )


def _quest_log_to_dict(log):
    """Serialisiert QuestLog für Save (PLAN Quest-Save)."""
    if log is None:
        return None
    return {
        'active': [
            {'qid': qid, 'stage_index': st.stage_index, 'count': st.count}
            for qid, st in log.active.items()
        ],
        'completed': list(log.completed),
        'discovered_lore': list(log.discovered_lore),
        'bestiary_seen': list(log.bestiary_seen),
    }


def _quest_log_from_dict(d):
    if d is None:
        return None
    from . import quests as _q
    log = _q.QuestLog()
    # Active wieder herstellen
    for entry in d.get('active', []):
        st = log.offer(entry['qid'])
        if st is None:
            continue
        st.stage_index = entry.get('stage_index', 0)
        st.count = entry.get('count', 0)
    log.completed = set(d.get('completed', []))
    log.discovered_lore = set(d.get('discovered_lore', []))
    log.bestiary_seen = set(d.get('bestiary_seen', []))
    return log


def save_game(game, slot=None):
    p = game.player
    data = {
        'version': 3,  # Update #133: Multi-Slot + Hardcore-Flag
        'time': time.time(),
        # Update #133 (Z-02): Hardcore-Flag persistiert pro Slot.
        'hardcore': bool(getattr(game, 'hardcore', False)),
        'player': {
            'cls': p.cls,
            'level': p.level, 'xp': p.xp, 'xp_to_next': p.xp_to_next,
            'skill_points': p.skill_points, 'attr_points': p.attr_points,
            'class_points': p.class_points,
            'strength': p.strength, 'intellect': p.intellect, 'dexterity': p.dexterity,
            'tree': dict(p.tree),
            'class_tree': dict(p.class_tree),
            'runes': dict(p.runes),
            'aura': p.aura,
            'skill_levels': dict(p.skill_levels),
            'skill_xp': dict(p.skill_xp),
            'gold': p.gold,
            'souls': getattr(p, 'souls', 0),
            'shards': getattr(p, 'shards', 0),
            'lore_fragments': getattr(p, 'lore_fragments', 0),
            'gems': list(p.gems),
            'inventory': [_item_to_dict(it) for it in p.inventory],
            'equipment': {s: _item_to_dict(it) for s, it in p.equipment.items()},
            'stash': [_item_to_dict(it) for it in p.stash],
            'completed_dungeons': list(p.completed_dungeons),
            'loot_filter': p.loot_filter,
            # Update #62: Bisher unspeicherte kritische Felder.
            # User-Bug „nicht alles wird vom Char gespeichert".
            'unlocked_skills':   list(getattr(p, 'unlocked_skills', set())),
            'skill_bindings':    {str(k): v
                                  for k, v in getattr(p, 'skill_bindings',
                                                       {}).items()},
            'uncut_gems':        {str(k): v
                                  for k, v in getattr(p, 'uncut_gems',
                                                       {}).items()},
            'gem_levels':        dict(getattr(p, 'gem_levels', {})),
            'skill_supports':    {k: list(v)
                                  for k, v in getattr(p, 'skill_supports',
                                                       {}).items()},
            'unlocked_supports': list(getattr(p, 'unlocked_supports', set())),
            'spirit_max':        getattr(p, 'spirit_max', 100),
            'class_mastery_xp':  getattr(p, 'class_mastery_xp', 0),
            # Update #32 Progression-Tracker (Memorial-Panel-Daten):
            'prog_kills_total':       getattr(p, 'prog_kills_total', 0),
            'prog_kills_boss':        getattr(p, 'prog_kills_boss', 0),
            'prog_kills_mini':        getattr(p, 'prog_kills_mini', 0),
            'prog_kills_elite':       getattr(p, 'prog_kills_elite', 0),
            'prog_dungeons_cleared':  list(getattr(p, 'prog_dungeons_cleared',
                                                    set())),
            'prog_lore_read':         list(getattr(p, 'prog_lore_read', set())),
            'prog_bestiary_seen':     list(getattr(p, 'prog_bestiary_seen',
                                                    set())),
            'prog_altars_used':       getattr(p, 'prog_altars_used', 0),
            'prog_runes_used':        getattr(p, 'prog_runes_used', 0),
            'prog_crits_dealt':       getattr(p, 'prog_crits_dealt', 0),
            'prog_distance_walked':   getattr(p, 'prog_distance_walked', 0.0),
            'prog_play_time_s':       getattr(p, 'prog_play_time_s', 0.0),
            # L-08 (Update #71): Weapon-Swap Set B + aktiver Set-Pointer
            'weapon_set_b':  {
                'weapon':  _item_to_dict(
                    getattr(p, 'weapon_set_b', {}).get('weapon')),
                'offhand': _item_to_dict(
                    getattr(p, 'weapon_set_b', {}).get('offhand')),
            },
            'active_weapon_set': getattr(p, 'active_weapon_set', 'a'),
            # Update #75 H-17: Orb-of-Regret-Bestand (Respec-Currency)
            'orbs_of_regret':   getattr(p, 'orbs_of_regret', 0),
            # Update #95: Kombinierte Vital-Flask. Legacy life/mana-Felder
            # bleiben für Backward-Compat (alte Saves), werden beim Load
            # gemerged.
            'flask_vital_charges': float(
                getattr(p, 'flasks', {}).get('vital', {}).get('charges', 4)),
        },
        'stats': getattr(game, 'stats', {}),
        'achievements': list(getattr(game, 'achievements_done', [])),
        'difficulty': {dk: int(v) for dk, v in getattr(game, 'dungeon_tier', {}).items()},
        # Velgrad-Quest-Log + Codex-Discoveries (PLAN Quest-Save)
        'quest_log': _quest_log_to_dict(getattr(game, 'quest_log', None)),
        'seen_encounters': list(getattr(game, '_seen_encounters', ())),
        'lore_items': list(getattr(p, 'lore_items', ())),
        # Update #22: Mahnmal-Marken I..VII + Akt-1-Intro-Flag
        'mahnmal_marken': {str(k): v
                           for k, v in getattr(p, 'mahnmal_marken',
                                                 {}).items()},
        # Update #80 W-12: Mahnmal-Schrein-Blessings (Aspekt-Pakt-Stacks)
        'mahnmal_blessings': {str(k): v
                              for k, v in getattr(p, 'mahnmal_blessings',
                                                    {}).items()},
        # Update #117 (WELT_AUFBAU 6.1): Faction-Rep pro Velgrad-Fraktion.
        'faction_rep': dict(getattr(p, 'faction_rep', {})),
        # Update #116 (WELT_AUFBAU 3.1): Quest-Choice-Flags.
        'game_flags': dict(getattr(game, 'flags', {})),
        'akt1_intro_seen': bool(getattr(p, 'akt1_intro_seen', False)),
        # Update #131 (Y-01/Y-02): Tutorial-Progress + Mechanik-Hints.
        'tutorial_step': int(getattr(p, 'tutorial_step', 0)),
        'tutorial_done': bool(getattr(p, 'tutorial_done', False)),
        'seen_mech_hints': sorted(getattr(p, 'seen_mech_hints', set())),
    }
    target = _effective_path(slot) if (slot is None or slot != 1
                                         or not LEGACY_SAVE_PATH.exists()
                                         or slot_path(slot).exists()) \
                                       else slot_path(slot)
    # Writes IMMER in den canonical Slot-Pfad (nie in Legacy)
    target = slot_path(int(slot) if slot is not None else _active_slot)
    try:
        target.write_text(json.dumps(data, indent=2))
        return True
    except OSError:
        return False


def load_game(game, slot=None):
    """Lädt Save und überschreibt game.player + persistente Felder.

    Returnt True bei Erfolg, False sonst.  `slot` ist optional; Default
    ist der aktive Slot (`_active_slot`).  Legacy `.shadowfall_save.json`
    wird automatisch als Slot 1 erkannt.
    """
    path = _effective_path(slot)
    if not path.exists():
        return False
    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return False
    pd = data.get('player', {})
    from .entities import Player
    new_player = Player(pd.get('cls', 'warrior'))
    new_player.level = pd.get('level', 1)
    new_player.xp = pd.get('xp', 0)
    new_player.xp_to_next = pd.get('xp_to_next', 30)
    new_player.skill_points = pd.get('skill_points', 0)
    new_player.attr_points = pd.get('attr_points', 0)
    new_player.class_points = pd.get('class_points', 0)
    new_player.strength = pd.get('strength', new_player.strength)
    new_player.intellect = pd.get('intellect', new_player.intellect)
    new_player.dexterity = pd.get('dexterity', new_player.dexterity)
    new_player.tree = dict(pd.get('tree', {}))
    new_player.class_tree = dict(pd.get('class_tree', {}))
    new_player.runes = dict(pd.get('runes', {}))
    new_player.aura = pd.get('aura')
    new_player.skill_levels = dict(pd.get('skill_levels', new_player.skill_levels))
    new_player.skill_xp = dict(pd.get('skill_xp', new_player.skill_xp))
    new_player.gold = pd.get('gold', 0)
    new_player.souls = pd.get('souls', 0)
    new_player.shards = pd.get('shards', 0)
    new_player.lore_fragments = pd.get('lore_fragments', 0)
    new_player.gems = list(pd.get('gems', []))
    new_player.inventory = [_item_from_dict(d) for d in pd.get('inventory', [None]*24)]
    new_player.equipment = {s: _item_from_dict(d)
                            for s, d in pd.get('equipment', {}).items()}
    # Ensure all SLOTS present
    from .constants import SLOTS
    for s in SLOTS:
        new_player.equipment.setdefault(s, None)
    new_player.stash = [_item_from_dict(d) for d in pd.get('stash', [None]*48)]
    # Pad inventory/stash to default sizes
    while len(new_player.inventory) < 24:
        new_player.inventory.append(None)
    while len(new_player.stash) < 48:
        new_player.stash.append(None)
    new_player.completed_dungeons = set(pd.get('completed_dungeons', []))
    new_player.loot_filter = pd.get('loot_filter', 'common')
    # Update #62: Bisher unspeicherte Felder zurückladen.
    # `unlocked_skills` ist KRITISCH — Skill-Gem-Drops gehen sonst verloren.
    if 'unlocked_skills' in pd:
        # Start-Set behalten (melee + Klassen-Default), Save addiert.
        new_player.unlocked_skills = set(pd['unlocked_skills']) | {'melee'}
    if 'skill_bindings' in pd:
        # Keys aus JSON sind Strings — zurück zu int (pygame Key-Codes)
        new_player.skill_bindings = {
            int(k): v for k, v in pd['skill_bindings'].items()
        }
    if 'uncut_gems' in pd:
        new_player.uncut_gems = {
            int(k): int(v) for k, v in pd['uncut_gems'].items()
        }
    if 'gem_levels' in pd:
        new_player.gem_levels = dict(pd['gem_levels'])
    if 'skill_supports' in pd:
        new_player.skill_supports = {
            k: list(v) for k, v in pd['skill_supports'].items()
        }
    if 'unlocked_supports' in pd:
        new_player.unlocked_supports = set(pd['unlocked_supports'])
    if 'spirit_max' in pd:
        new_player.spirit_max = int(pd['spirit_max'])
    if 'class_mastery_xp' in pd:
        new_player.class_mastery_xp = int(pd['class_mastery_xp'])
    # Update #32 Progression-Tracker (Memorial-Panel)
    new_player.prog_kills_total = pd.get('prog_kills_total', 0)
    new_player.prog_kills_boss = pd.get('prog_kills_boss', 0)
    new_player.prog_kills_mini = pd.get('prog_kills_mini', 0)
    new_player.prog_kills_elite = pd.get('prog_kills_elite', 0)
    new_player.prog_dungeons_cleared = set(pd.get('prog_dungeons_cleared', []))
    new_player.prog_lore_read = set(pd.get('prog_lore_read', []))
    new_player.prog_bestiary_seen = set(pd.get('prog_bestiary_seen', []))
    new_player.prog_altars_used = pd.get('prog_altars_used', 0)
    new_player.prog_runes_used = pd.get('prog_runes_used', 0)
    new_player.prog_crits_dealt = pd.get('prog_crits_dealt', 0)
    new_player.prog_distance_walked = pd.get('prog_distance_walked', 0.0)
    new_player.prog_play_time_s = pd.get('prog_play_time_s', 0.0)
    # L-08 (Update #71): Weapon-Swap Set B + aktiver Set-Pointer
    wb = pd.get('weapon_set_b', {})
    new_player.weapon_set_b = {
        'weapon': _item_from_dict(wb.get('weapon')),
        'offhand': _item_from_dict(wb.get('offhand')),
    }
    new_player.active_weapon_set = pd.get('active_weapon_set', 'a')
    # Update #75 H-17: Orb-of-Regret-Bestand
    new_player.orbs_of_regret = int(pd.get('orbs_of_regret', 2))
    # Update #95: Vital-Flask-Charges restoren. Legacy life/mana-Saves
    # werden gemerged (Durchschnitt) damit alte Spielstände nicht verlieren.
    if hasattr(new_player, 'flasks'):
        f_vital = new_player.flasks.get('vital')
        if f_vital is not None:
            if 'flask_vital_charges' in pd:
                vc = float(pd['flask_vital_charges'])
            else:
                # Legacy: average der alten life/mana-Charges
                lc = float(pd.get('flask_life_charges', f_vital['max']))
                mc = float(pd.get('flask_mana_charges', f_vital['max']))
                vc = (lc + mc) * 0.5
            f_vital['charges'] = max(0.0, min(f_vital['max'], vc))
        new_player.flask_effects = []

    # HP/MP voll
    from . import progression
    eff = progression.effective(new_player)
    new_player.hp = eff['hp_max']
    new_player.mp = eff['mp_max']

    # Lore-Items (Quest-Reward-Pool)
    new_player.lore_items = list(data.get('lore_items', []))

    # Update #22: Mahnmal-Marken + Akt-1-Intro-Flag
    saved_marken = data.get('mahnmal_marken', {}) or {}
    for k, v in saved_marken.items():
        try:
            new_player.mahnmal_marken[int(k)] = int(v)
        except (ValueError, TypeError):
            pass
    new_player.akt1_intro_seen = bool(data.get('akt1_intro_seen', False))
    # Update #131: Tutorial-Persistenz
    new_player.tutorial_step = int(data.get('tutorial_step', 0))
    new_player.tutorial_done = bool(data.get('tutorial_done', False))
    new_player.seen_mech_hints = set(data.get('seen_mech_hints', []) or [])
    # Update #80 W-12: Mahnmal-Schrein-Blessings (Aspekt-Pakt-Stacks)
    saved_bless = data.get('mahnmal_blessings', {}) or {}
    if not hasattr(new_player, 'mahnmal_blessings'):
        new_player.mahnmal_blessings = {1: 0, 2: 0, 3: 0, 4: 0,
                                          5: 0, 6: 0, 7: 0}
    for k, v in saved_bless.items():
        try:
            new_player.mahnmal_blessings[int(k)] = min(5, int(v))
        except (ValueError, TypeError):
            pass
    # Update #117 (WELT_AUFBAU 6.1): Faction-Rep wiederherstellen.
    saved_rep = data.get('faction_rep', {}) or {}
    new_player.faction_rep = {}
    for fac, amount in saved_rep.items():
        try:
            new_player.faction_rep[str(fac)] = max(-200, min(200,
                                                              int(amount)))
        except (ValueError, TypeError):
            pass

    game.player = new_player
    # Update #116: Quest-Choice-Flags wiederherstellen
    game.flags = dict(data.get('game_flags', {}) or {})
    game.stats = data.get('stats', {})
    game.achievements_done = set(data.get('achievements', []))
    game.dungeon_tier = data.get('difficulty', {})

    # Quest-Log + Codex (PLAN Quest-Save)
    loaded_log = _quest_log_from_dict(data.get('quest_log'))
    if loaded_log is not None:
        game.quest_log = loaded_log
    game._seen_encounters = set(data.get('seen_encounters', []))
    # Update #133 (Z-02): Hardcore-Flag aus Save übernehmen.
    game.hardcore = bool(data.get('hardcore', False))
    # Wenn explizit ein Slot geladen wurde, diesen aktivieren.
    if slot is not None:
        set_active_slot(slot)
    return True


def save_exists(slot=None):
    return _effective_path(slot).exists()


def delete_save(slot=None):
    try:
        # Lösche beide möglichen Pfade (Legacy + Slot) — Hardcore-Cleanup
        for path in (slot_path(int(slot) if slot is not None
                                else _active_slot),
                     LEGACY_SAVE_PATH if (slot is None or slot == 1)
                     else None):
            if path is not None and path.exists():
                path.unlink()
        return True
    except OSError:
        return False


def list_slot_summaries():
    """Update #133 (Z-01): liefert Summary-Dicts für alle 3 Slots.

    Wird vom Title-Screen genutzt um die Slot-Picker-UI zu rendern.

    Returnt Liste von dicts mit:
      slot, exists, cls, level, gold, akt, hardcore, time_played_h,
      last_played_ts (UNIX), label (kurz).
    """
    out = []
    for s in range(1, MAX_SLOTS + 1):
        path = _effective_path(s)
        if not path.exists():
            out.append({
                'slot':       s,
                'exists':     False,
                'cls':        None,
                'level':      0,
                'gold':       0,
                'akt':        0,
                'hardcore':   False,
                'time_played_h': 0.0,
                'last_played_ts': 0.0,
                'label':      'Leer',
            })
            continue
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            out.append({
                'slot': s, 'exists': False, 'cls': None, 'level': 0,
                'gold': 0, 'akt': 0, 'hardcore': False,
                'time_played_h': 0.0, 'last_played_ts': 0.0,
                'label': 'Korrupt',
            })
            continue
        pd = data.get('player', {})
        akt = len(pd.get('completed_dungeons', [])) + 1
        time_s = float(pd.get('prog_play_time_s', 0.0))
        out.append({
            'slot':           s,
            'exists':         True,
            'cls':            pd.get('cls', 'warrior'),
            'level':          int(pd.get('level', 1)),
            'gold':           int(pd.get('gold', 0)),
            'akt':            int(akt),
            'hardcore':       bool(data.get('hardcore', False)),
            'time_played_h':  time_s / 3600.0,
            'last_played_ts': float(data.get('time', 0.0)),
            'label':          f'Slot {s}',
        })
    return out
