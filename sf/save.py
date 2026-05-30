"""Save/Load: persistierter Spieler-Zustand als JSON.

Update #133 (Z-01/Z-02): Multi-Save-Slot-System.
- 3 nummerierte Slots: `~/.shadowfall_save_slot1.json` .. `_slot3.json`
- Legacy `~/.shadowfall_save.json` wird beim ersten Load als Slot 1 gelesen
  (Backward-Compat).
- Module-level `_active_slot` bestimmt welcher Slot von save_game/load_game
  benutzt wird; via `set_active_slot(n)` setzbar.
- Hardcore-Flag pro Slot persistiert; bei Tod im Hardcore-Mode wird der
  Slot komplett gelöscht (Permadeath).

Update #137 (Z-03/Z-04/Z-06):
- **SAVE_VERSION = 4** + `migrate_save(data)` Chain ersetzt ad-hoc-Migration
  bei jedem `.get(..., default)`-Aufruf.  Pro Version eine Migrator-Fn die
  schreibt was die nächste Version braucht.
- **SHA256-Integrity-Hash**: pro Save wird ein `_integrity_sha256`-Feld
  über den canonical-JSON-String der Daten ohne das Feld selbst berechnet.
  Bei Load wird verifiziert + bei Mismatch ein Warning-Toast gezeigt
  (Save lädt trotzdem, aber Spieler weiß dass evtl. korrupt).
- **Auto-Save**: separates `~/.shadowfall_autosave.json` wird alle 60 s
  geschrieben.  Beim Start prüft `check_autosave_recovery()` ob ein Auto-
  Save existiert das *neuer* als der aktive Slot-Save ist — dann
  Recovery-Dialog anbieten.
"""

import atexit
import hashlib
import json
import os
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

from .items import Item


# ============================================================
# Audit #179 B.7: Async Save-Writer
# ============================================================
# Save-Disk-IO geht in einen Background-Worker-Thread. Atomic write via
# write-then-rename verhindert halb-geschriebene Saves bei Crash waehrend
# Write. Reihenfolge erhalten via Queue (FIFO). Auto-Save (`write_autosave`)
# nutzt den gleichen Worker.
#
# Sync-Fallback: ENV `SHADOWFALL_SAVE_SYNC=1` schaltet das ab (fuer Tests
# und Debugging). Default = async.
_SAVE_QUEUE: queue.Queue = queue.Queue()
_SAVE_WORKER: threading.Thread | None = None
_SAVE_STOP = threading.Event()
# Tests laufen headless und erwarten dass Auto-Save sofort auf Disk landet
# (rufen `.exists()` direkt danach). Default-disable Async im Test-Modus.
_TEST_MODE = os.environ.get('SDL_VIDEODRIVER') == 'dummy'
_SAVE_ASYNC_ENABLED = (
    not bool(os.environ.get('SHADOWFALL_SAVE_SYNC'))
    and not _TEST_MODE
)
_save_atexit_registered = False


def _atomic_write_text(target: Path, text: str) -> bool:
    """Write `text` to `target` atomically via temp-file + rename.

    Verhindert halb-geschriebene Saves wenn der Prozess waehrend Write
    crasht (rename ist atomisch auf POSIX und unter Windows ab Py3.3).
    """
    tmp = target.with_suffix(target.suffix + '.tmp')
    try:
        tmp.write_text(text)
        os.replace(tmp, target)
        return True
    except OSError:
        try:
            if tmp.exists():
                tmp.unlink()
        except OSError:
            pass
        return False


def _save_worker_loop():
    while not _SAVE_STOP.is_set():
        try:
            job = _SAVE_QUEUE.get(timeout=0.5)
        except queue.Empty:
            continue
        if job is None:    # Sentinel fuer Shutdown
            break
        target, text = job
        try:
            _atomic_write_text(Path(target), text)
        except Exception:
            # Worker darf nicht sterben — Game bleibt schreibbar.
            pass
        _SAVE_QUEUE.task_done()


def _ensure_save_worker_running():
    global _SAVE_WORKER, _save_atexit_registered
    if not _SAVE_ASYNC_ENABLED:
        return
    if _SAVE_WORKER is None or not _SAVE_WORKER.is_alive():
        _SAVE_STOP.clear()
        _SAVE_WORKER = threading.Thread(
            target=_save_worker_loop, name='save-writer', daemon=True)
        _SAVE_WORKER.start()
    if not _save_atexit_registered:
        atexit.register(shutdown_save_worker)
        _save_atexit_registered = True


def shutdown_save_worker(timeout=3.0):
    """Stoppt den Worker und wartet bis pending Writes durch sind.

    Wichtig: Im atexit-Handler garantiert, dass der allerletzte save_game()-
    Call nicht verloren geht. Timeout 3 s ist defensiv (Worst-Case zwei
    queued Writes auf langsamem Disk).
    """
    if _SAVE_WORKER is None:
        return
    # Sentinel pushen damit Worker aus get() rausfaellt
    try:
        _SAVE_QUEUE.put_nowait(None)
    except queue.Full:
        pass
    _SAVE_STOP.set()
    if _SAVE_WORKER.is_alive():
        _SAVE_WORKER.join(timeout=timeout)


def _write_save_text(target: Path, text: str) -> bool:
    """Schreibt Save-JSON entweder async (Queue) oder sync.

    Returnt True wenn der Schreib-Auftrag entgegengenommen wurde. Bei
    async heisst das: in Queue gelandet (nicht: auf Disk). Sync writet
    sofort und returnt das Disk-Ergebnis.
    """
    if _SAVE_ASYNC_ENABLED:
        _ensure_save_worker_running()
        _SAVE_QUEUE.put((str(target), text))
        return True
    return _atomic_write_text(target, text)


# Legacy-Pfad (vor Update #133); wird bei Bedarf als Slot 1 gelesen.
LEGACY_SAVE_PATH = Path.home() / '.shadowfall_save.json'
SAVE_PATH = LEGACY_SAVE_PATH  # Backward-Compat-Alias (alte Imports)

MAX_SLOTS = 3
_active_slot = 1

# Update #137 (Z-03): aktuelle Save-Version. Wird in `save_game()`
# als data['version'] geschrieben, in `load_game()` per
# `migrate_save(data)` upgegradet falls niedriger.
SAVE_VERSION = 4

# Update #137 (Z-06): Auto-Save-Pfad (slot-unabhängig). Wird alle
# `AUTOSAVE_INTERVAL_S` Sekunden vom Game-Loop geschrieben.
AUTOSAVE_PATH = Path.home() / '.shadowfall_autosave.json'
AUTOSAVE_INTERVAL_S = 60.0

# Update #151 (User-Report „Vollbild/Seekrankheits/FPS müssen
# gespeichert werden"): Settings-File (slot-unabhängig — Settings
# gelten global für alle Saves).  Persistiert Display/Performance/
# Audio/Accessibility-Optionen separat vom Player-State.
SETTINGS_PATH = Path.home() / '.shadowfall_settings.json'

# Welche Settings-Keys werden persistiert. Audio-Volume sind separat
# bereits live im Sounds-Modul wirksam — wir nehmen sie hier dennoch
# mit damit der Slider beim Neustart auf dem letzten Wert steht.
_PERSISTED_SETTING_KEYS = (
    'fullscreen',
    'camera_cursor_lean',
    'camera_lookahead',
    'camera_combat_zoom',
    'frame_cap',
    'vsync',
    'render_scale',
    'music_vol',
    'sfx_vol',
    'voice_vol',
    'multi_threading',
    'colorblind_ailments',
    'damage_numbers',
    'screen_shake',
    'show_fps',
    'tutorial_active',
    # Update #178: alle Settings-Modal-Optionen persistieren
    'particle_density',
    'photosensitive',
    'rim_light',
    'high_contrast_aoe',
    'tactical_reduce',
    'minimap_rotate',
    'ai_sprites',
    'bloom',
    'heat_distortion',
    'crt_filter',
)


def save_settings(game):
    """Update #151: Persistiert Game-Einstellungen nach SETTINGS_PATH.

    Wird aufgerufen wann immer eine Option geändert wird (Settings-
    Modal, F11-Fullscreen-Toggle, etc.).  Schreibt nur Keys aus
    `_PERSISTED_SETTING_KEYS` plus den `fullscreen`-Toplevel-Flag.

    Schreib-Fehler werden geschluckt (User-Profile read-only?) — wir
    werfen die App deswegen nicht ab.
    """
    try:
        data = {}
        settings = getattr(game, 'settings', None) or {}
        for k in _PERSISTED_SETTING_KEYS:
            if k in settings:
                data[k] = settings[k]
        # `fullscreen` lebt als Toplevel-Attribut auf game (nicht in
        # settings dict), aber für Persistenz schreiben wir den Wert
        # ins gleiche File.
        data['fullscreen'] = bool(getattr(game, 'fullscreen', False))
        with open(SETTINGS_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, sort_keys=True)
    except (OSError, TypeError, ValueError):
        pass


def load_settings():
    """Update #151: Lädt persistierte Settings.  Returnt dict (möglicher-
    weise leer wenn Datei nicht existiert).  Wird in Game.__init__ vor
    self.settings-Bau aufgerufen und überlagert die Defaults.
    """
    try:
        if not SETTINGS_PATH.exists():
            return {}
        with open(SETTINGS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        # Whitelist filter — kein injecten von unbekannten Keys
        out = {k: data[k] for k in _PERSISTED_SETTING_KEYS if k in data}
        if 'fullscreen' in data:
            out['fullscreen'] = bool(data['fullscreen'])
        return out
    except (OSError, ValueError):
        return {}

# Update #137 (Z-04): Field-Name für den Integrity-SHA256 im Save-Dict.
# Wird beim Hash-Compute ausgeschlossen (sonst zirkulär).
_INTEGRITY_FIELD = '_integrity_sha256'


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
    d = {
        'slot': item.slot,
        'rarity': item.rarity,
        'name': item.name,
        'affixes': list(item.affixes),
        'ilvl': item.ilvl,
        'sockets': list(item.sockets),
        'set_id': item.set_id,
    }
    # Update #154: quest_item nur schreiben wenn True (Backward-Compat)
    if getattr(item, 'quest_item', False):
        d['quest_item'] = True
    # Update #161 (WELT_AUFBAU 5.5): link_id (Shulavhs Faden)
    if getattr(item, 'link_id', None):
        d['link_id'] = item.link_id
    return d


def _item_from_dict(d):
    if d is None:
        return None
    return Item(
        slot=d['slot'], rarity=d['rarity'], name=d['name'],
        affixes=[tuple(a) for a in d['affixes']], ilvl=d['ilvl'],
        sockets=list(d['sockets']),
        set_id=d.get('set_id'),
        quest_item=d.get('quest_item', False),
        link_id=d.get('link_id'),
    )


def _quest_log_to_dict(log):
    """Serialisiert QuestLog für Save (PLAN Quest-Save).

    Update #158: `discovery_counts` werden mit-persistiert — sonst
    verliert ein Spieler, der 2 von 3 Lore-Tafeln für eine Hidden-
    Quest angefasst hat, seinen Fortschritt beim Save/Load.
    """
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
        # Update #158: Hidden-Quest-Discovery-Counter (#154 T1.1-D)
        'discovery_counts': dict(getattr(log, 'discovery_counts', {})),
        # Update #160 (ROADMAP T2.3-C): Quest-Pin
        'tracked_quest_id': getattr(log, 'tracked_quest_id', None),
        # Audit #179 C.2: Abgebrochene Quests — verhindert Re-Offer
        # nach Save/Load.
        'abandoned': list(getattr(log, 'abandoned', set())),
        # Audit C.2: Gescheiterte Quests (ESCORT/DEFEND-Timeout) — blocken
        # Re-Offer nach Save/Load wie abandoned.
        'failed': list(getattr(log, 'failed', set())),
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
    # Update #158: discovery_counts restaurieren (Backward-Compat:
    # alte Saves haben den Key nicht → {})
    log.discovery_counts = dict(d.get('discovery_counts', {}))
    # Update #160 (T2.3-C): tracked_quest_id restaurieren
    tracked = d.get('tracked_quest_id')
    if tracked and tracked in log.active:
        log.tracked_quest_id = tracked
    else:
        log.tracked_quest_id = None
    # Audit #179 C.2: Abgebrochene Quests restaurieren (schema-additiv,
    # alte Saves haben den Key nicht → leeres Set).
    log.abandoned = set(d.get('abandoned', []))
    # Audit C.2: Gescheiterte Quests restaurieren (schema-additiv, alte
    # Saves haben den Key nicht → leeres Set).
    log.failed = set(d.get('failed', []))
    return log


# ============================================================
# Update #137 (Z-03): Save-Versioning + Migration-Chain
# ============================================================
# Pro Version eine Migrator-Funktion `_migrate_vN_to_vN1(data)` die
# das gleiche dict in-place mutiert / Felder hinzufügt um auf v(N+1)
# zu kommen.  `migrate_save(data)` ruft die Chain von der gespeicherten
# Version bis SAVE_VERSION durch.  Migrator-Fns dürfen Schreibrechte
# auf alle Schlüssel haben und SOLLEN explicit alle neu hinzukommenden
# Felder mit lore-konformen Defaults befüllen.
def _migrate_v1_to_v2(data):
    """v1 → v2: Update #62 erweiterte Player-Felder (unlocked_skills,
    skill_bindings, uncut_gems, etc.). Backward-compat-Defaults werden
    von Load-Pfad bereits angewandt — Migration ist Noop-Stub.
    """
    return data


def _migrate_v2_to_v3(data):
    """v2 → v3: Update #133 Multi-Slot + Hardcore.
    Schreibt `hardcore=False` falls fehlend (alte single-Slot-Saves
    sind keine Hardcore-Chars).
    """
    if 'hardcore' not in data:
        data['hardcore'] = False
    return data


def _migrate_v3_to_v4(data):
    """v3 → v4: Update #137 Integrity-Hash + Auto-Save-Support.
    Tutorial-Felder (top-level, nicht in player) bekommen Defaults
    falls fehlend.  Integrity-Hash wird beim nächsten Save geschrieben,
    nicht beim Migrate (sonst zirkulär).
    """
    data.setdefault('tutorial_step', 0)
    data.setdefault('tutorial_done', False)
    data.setdefault('seen_mech_hints', [])
    return data


_MIGRATIONS = {
    1: _migrate_v1_to_v2,
    2: _migrate_v2_to_v3,
    3: _migrate_v3_to_v4,
}


class SaveVersionTooNewError(Exception):
    """Audit #179 C.3: Save wurde mit einer neueren Game-Version erstellt.

    Verhindert stille Daten-Korruption beim Downgrade (z.B. User testet
    v5-Beta, dann wieder v4-Release — v5-Save darf nicht stillschweigend
    als v4 reinterpretiert werden).
    """

    def __init__(self, save_version, current_version):
        self.save_version = save_version
        self.current_version = current_version
        super().__init__(
            f'Save-Version {save_version} ist neuer als unterstuetzt '
            f'(max {current_version}). Game-Update noetig.')


def migrate_save(data):
    """Update #137 (Z-03): rufe alle Migratoren von data['version']
    bis SAVE_VERSION durch.  Returnt das migrierte Dict (in-place
    mutiert).  Setzt am Ende `version = SAVE_VERSION`.

    Audit #179 C.3: Bei `version > SAVE_VERSION` wird `SaveVersionTooNewError`
    geworfen statt still zu "downgraden" — das verhinderte zuvor erkennbare
    Schema-Inkompatibilitaeten und konnte zu Daten-Verlust fuehren.
    """
    v = int(data.get('version', 1))
    if v > SAVE_VERSION:
        raise SaveVersionTooNewError(v, SAVE_VERSION)
    while v < SAVE_VERSION:
        mig = _MIGRATIONS.get(v)
        if mig is None:
            break
        data = mig(data) or data
        v += 1
    data['version'] = SAVE_VERSION
    return data


# ============================================================
# Update #137 (Z-04): SHA256-Integrity-Verify
# ============================================================
def _compute_integrity_hash(data):
    """SHA256 über den canonical-JSON-String der Save-Daten OHNE das
    Integrity-Feld selbst.  Ergibt einen 64-Char-Hex-String.

    Canonical heißt: `sort_keys=True` + Standard-Separators → stabil
    über Python-Versionen + identisch auf jedem System.
    """
    payload = {k: v for k, v in data.items() if k != _INTEGRITY_FIELD}
    canon = json.dumps(payload, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False)
    return hashlib.sha256(canon.encode('utf-8')).hexdigest()


def verify_save_integrity(data):
    """Returnt True wenn der eingebettete Hash zum berechneten passt.
    Saves OHNE Hash (alte Versionen) returnen True (keine Korruption-
    Detection möglich, aber nicht hart-failen).
    """
    saved_hash = data.get(_INTEGRITY_FIELD)
    if not saved_hash:
        return True
    return _compute_integrity_hash(data) == saved_hash


def save_game(game, slot=None):
    p = game.player
    data = {
        'version': SAVE_VERSION,
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
            # Update #184: POE2-Atlas
            'atlas': list(getattr(p, 'atlas', set())),
            'atlas_points': getattr(p, 'atlas_points', 0),
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
            # Audit #179 C.4: Skill-Cooldowns persistieren — vorher wurden
            # CDs beim Reload still auf 0.0 zurueckgesetzt → Save-Scumming
            # fuer Ultimate (60s CD) moeglich.
            'skill_cd': dict(getattr(p, 'skill_cd', {})),
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
    # Writes IMMER in den canonical Slot-Pfad (nie in Legacy)
    target = slot_path(int(slot) if slot is not None else _active_slot)
    # Update #137 (Z-04): SHA256-Integrity-Hash über canonical-JSON
    # berechnen + ins Dict einbetten.  `verify_save_integrity()` checkt
    # beim Load.
    data[_INTEGRITY_FIELD] = _compute_integrity_hash(data)
    # Audit #179 B.7: save_game() bleibt SYNCHRON (atomic write-then-rename).
    # Explizite User-Saves sind selten und Tests/Load-Roundtrips erwarten
    # konsistente Disk-Sichtbarkeit. NUR write_autosave() ist async — das
    # ist die wirklich heisse Stelle (Game-Loop alle 60 s).
    return _atomic_write_text(target, json.dumps(data, indent=2))


def write_autosave(game):
    """Update #137 (Z-06): Schreibt einen Auto-Save in den
    `AUTOSAVE_PATH` — separat von den 3 Slots.  Wird vom Game-Loop alle
    `AUTOSAVE_INTERVAL_S` Sekunden aufgerufen.  Behält den `slot`-
    Reference im Save (damit Recovery den Original-Slot kennt).

    Failt silently (Auto-Save darf das Spiel nie crashen).
    """
    try:
        from .items import Item as _Item  # late import; nicht zirkulär
    except Exception:
        return False
    p = game.player
    try:
        # Schnell-Snapshot via save_game-Logik, aber Pfad ist AUTOSAVE
        # statt slot_path.  Trick: rufe save_game auf, swap Datei.
        # Cleaner: explizite Auto-Save-Path-Funktion.
        slot = get_active_slot()
        # Re-use save_game payload generation via temporary path swap
        # ist zu invasiv — wir bauen das Dict hier direkt-ish.
        # Einfacher: save_game(game, slot=N) schreibt in slot_path(N);
        # für AutoSave wollen wir AUTOSAVE_PATH.  Wir machen einen
        # quick-copy via reading the slot save.
        if not save_game(game, slot=slot):
            return False
        src = slot_path(slot)
        if not src.exists():
            return False
        # Embed slot-info in das auto-save-Dict
        data = json.loads(src.read_text())
        data['_autosave_source_slot'] = slot
        data['_autosave_time'] = time.time()
        # Hash über neue Felder neu berechnen
        if _INTEGRITY_FIELD in data:
            del data[_INTEGRITY_FIELD]
        data[_INTEGRITY_FIELD] = _compute_integrity_hash(data)
        # Audit #179 B.7: Auto-Save async (atomic write-then-rename).
        _write_save_text(AUTOSAVE_PATH, json.dumps(data, indent=2))
        return True
    except Exception:
        return False


def check_autosave_recovery():
    """Update #137 (Z-06): Prüft beim Start ob der Auto-Save existiert
    UND neuer ist als der zugehörige Slot-Save.  Returnt entweder
    `None` (kein Recovery nötig) oder ein dict mit
    `{slot, autosave_time, slot_time, age_minutes}`.
    """
    if not AUTOSAVE_PATH.exists():
        return None
    try:
        data = json.loads(AUTOSAVE_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    slot = data.get('_autosave_source_slot', 1)
    autosave_time = float(data.get('_autosave_time', 0.0))
    sp = slot_path(slot)
    slot_time = sp.stat().st_mtime if sp.exists() else 0.0
    # Recovery nur anbieten wenn AutoSave WIRKLICH neuer ist
    if autosave_time <= slot_time:
        return None
    age_s = max(0.0, time.time() - autosave_time)
    return {
        'slot':          int(slot),
        'autosave_time': autosave_time,
        'slot_time':     slot_time,
        'age_minutes':   age_s / 60.0,
    }


def apply_autosave_recovery(game):
    """Update #137 (Z-06): Lädt den Auto-Save in `game` (überschreibt
    den aktuellen Slot-Save).  Returnt True bei Erfolg.
    """
    if not AUTOSAVE_PATH.exists():
        return False
    try:
        # Hole Slot-Number aus AutoSave-Header
        data = json.loads(AUTOSAVE_PATH.read_text())
        slot = int(data.get('_autosave_source_slot', 1))
        # Schreibe in den canonical Slot-Pfad
        # (überschreibt evtl. älteren Slot-Save).
        # Audit #179 B.7: SYNC bewusst — load_game() liest unmittelbar
        # danach und muss den frisch geschriebenen Save sehen.
        _atomic_write_text(slot_path(slot), json.dumps(data, indent=2))
        # Lade in das game-Objekt
        ok = load_game(game, slot=slot)
        if ok:
            # AutoSave nach erfolgreicher Recovery löschen
            try:
                AUTOSAVE_PATH.unlink()
            except OSError:
                pass
        return ok
    except Exception:
        return False


def discard_autosave():
    """Update #137 (Z-06): Auto-Save löschen ohne Recovery."""
    try:
        if AUTOSAVE_PATH.exists():
            AUTOSAVE_PATH.unlink()
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
    # Update #137 (Z-04): Integrity-Hash verifizieren.  Bei Mismatch
    # zeigen wir einen Toast (Save wird trotzdem geladen — graceful
    # degradation statt hart-fail).
    if not verify_save_integrity(data):
        try:
            if hasattr(game, 'toast'):
                game.toast(
                    '⚠ Save evtl. korrupt (Hash-Mismatch). '
                    'Inhalt wird trotzdem geladen.',
                    (220, 150, 100))
        except Exception:
            pass
    # Update #137 (Z-03): Migration-Chain auf SAVE_VERSION ziehen.
    # Audit #179 C.3: Reject statt still-downgrade bei v > SAVE_VERSION.
    try:
        data = migrate_save(data)
    except SaveVersionTooNewError as exc:
        try:
            if hasattr(game, 'toast'):
                game.toast(
                    f'Save Slot {slot} mit Version {exc.save_version} kann '
                    f'nicht geladen werden (Build max v{exc.current_version}).',
                    (255, 100, 100))
        except Exception:
            pass
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
    # Update #184: POE2-Atlas — laden oder aus Legacy migrieren.
    from . import skill_atlas as _atlas
    if 'atlas' in pd:
        # Verwaiste Node-IDs filtern (z.B. alte `*_stub_*`-Nodes, die beim
        # Klassen-Arm-Ausbau ersetzt wurden) — sonst blockiert ein nicht
        # mehr existenter, unerreichbarer Eintrag den Refund-Connectivity-
        # Check. Erstattete Punkte werden zurueckgegeben.
        raw_atlas = set(pd.get('atlas', []))
        valid_atlas = {nid for nid in raw_atlas if nid in _atlas.ATLAS_NODES}
        refunded = len(raw_atlas) - len(valid_atlas)
        new_player.atlas = valid_atlas
        new_player.atlas_points = pd.get('atlas_points', 0) + refunded
        # Sicherheit: Start-Node garantieren
        start = _atlas.CLASS_STARTS.get(new_player.cls)
        if start and start not in new_player.atlas:
            new_player.atlas.add(start)
    else:
        # Alter Save → Migration (Refund alter Punkte als Atlas-Points)
        _atlas.migrate_legacy_points(new_player)
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
    # Audit #179 C.4: Skill-Cooldowns aus Save uebernehmen, falls vorhanden.
    # Player.__init__ hat default-skill_cd-Dict — nur ueberschreiben was im
    # Save steht, Rest bleibt 0.0. Schema-additiv: alte Saves (kein
    # 'skill_cd'-Key) bleiben kompatibel.
    saved_cds = pd.get('skill_cd')
    if isinstance(saved_cds, dict):
        for skill, cd in saved_cds.items():
            try:
                new_player.skill_cd[skill] = float(cd)
            except (TypeError, ValueError):
                pass
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
