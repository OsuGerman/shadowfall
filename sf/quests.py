"""Quest-Engine mit Stages, Triggers und Event-Handlern.

Lore-Quelle: VELGRAD_LORE_BIBEL.md Teil 10 + VELGRAD_VOICE_LINES_POOL.md.
Quest-Daten kommen aus sf/quest_data.py.

Architektur:
  - `QuestState` pro aktive Quest (laufende Stage-Index, Counter pro Stage).
  - `QuestLog` als Game-Modul-State (active + completed-Listen).
  - Event-Handler `on_kill`/`on_reach_biome`/`on_talk`/`on_interact`
    machen Stage-Progress.
"""

from . import quest_data as _qd


class QuestState:
    """Eine aktive Quest. Tracking via stage_index + current_count.

    Update #116: Zusätzliche Felder für die 6 neuen Stage-Types
    (WELT_AUFBAU 3.1):
      - `timer`: Sekunden-Akkumulator für DEFEND + TIMED + ESCORT-Patience
      - `puzzle_progress`: Liste der bereits erfolgreich getriggerten
        Sequenz-Schritte (PUZZLE)
    """
    __slots__ = ('quest', 'stage_index', 'count', 'completed',
                 'visible_marker', 'timer', 'puzzle_progress')

    def __init__(self, quest_dict):
        self.quest = quest_dict
        self.stage_index = 0
        self.count = 0
        self.completed = False
        self.visible_marker = True
        self.timer = 0.0
        self.puzzle_progress = []

    # ---- Stage-Helpers ----
    @property
    def stage(self):
        if self.stage_index >= len(self.quest['stages']):
            return None
        return self.quest['stages'][self.stage_index]

    @property
    def title(self):
        return self.quest['title']

    @property
    def region(self):
        return self.quest.get('region', '')

    @property
    def is_main(self):
        return self.quest.get('is_main', False)

    def current_count_target(self):
        st = self.stage
        if st is None:
            return (0, 1)
        return (self.count, st.get('count', 1))

    def display_text(self):
        st = self.stage
        if st is None:
            return 'Quest abgeschlossen.'
        # Update #116: Zeit-basierte Stages zeigen Sekunden-Counter
        stype = st.get('type')
        if stype == _qd.StageType.DEFEND:
            dur = st.get('target', {}).get('duration', 1.0)
            return f"{st['text']}  ({self.timer:.0f}/{int(dur)} s)"
        if stype == _qd.StageType.TIMED:
            lim = st.get('target', {}).get('time_limit', 1.0)
            remaining = max(0.0, lim - self.timer)
            return f"{st['text']}  ({remaining:.0f} s)"
        if stype == _qd.StageType.PUZZLE:
            seq = st.get('target', {}).get('sequence', [])
            return f"{st['text']}  ({len(self.puzzle_progress)}/{len(seq)})"
        target = st.get('count', 1)
        if target > 1:
            return f"{st['text']}  ({self.count}/{target})"
        return st['text']

    # ---- Tick (für zeit-basierte Stages) ----
    def tick(self, dt, game):
        """Update #116: Per-Frame-Tick für ESCORT/DEFEND/TIMED-Stages.

        Wird von `QuestLog.tick(dt, game)` aufgerufen.  Returnt True wenn
        die Stage gerade weitergeschritten ist (für Caller-Cleanup).
        """
        st = self.stage
        if st is None or self.completed:
            return False
        stype = st.get('type')
        target = st.get('target', {})

        if stype == _qd.StageType.DEFEND:
            # Player muss N Sekunden in der Nähe des NPC bleiben + NPC lebt
            npc_name = target.get('npc_name')
            duration = target.get('duration', 30.0)
            npc_alive = _npc_is_alive(game, npc_name)
            player_close = _player_near_npc(game, npc_name, radius=200)
            if npc_alive and player_close:
                self.timer += dt
                if self.timer >= duration:
                    self.timer = 0.0
                    return True   # → Stage advanced (handled by caller)
            elif not npc_alive:
                # NPC tot → Quest scheitert: revert timer
                self.timer = 0.0

        elif stype == _qd.StageType.TIMED:
            # Zeit läuft ab; wenn limit überschritten → fail_action.
            # `tick` returnt False für fail-Pfade — die werden direkt hier
            # gehandhabt (revert/abort), kein advance_stage-Callback nötig.
            limit = target.get('time_limit', 30.0)
            self.timer += dt
            if self.timer >= limit:
                fail = target.get('fail_action', 'revert')
                self.timer = 0.0
                if fail == 'revert':
                    # zurück zur Start-Stage (Stage 0)
                    self.stage_index = 0
                    self.count = 0
                    if hasattr(game, 'toast'):
                        game.toast(
                            f'„{self.title}": Zeit abgelaufen, '
                            f'von vorn.', (220, 130, 80))
                elif fail == 'fail':
                    # Quest komplett abbrechen
                    self._mark_complete(game)
                    if hasattr(game, 'toast'):
                        game.toast(
                            f'„{self.title}" gescheitert: Zeit '
                            f'abgelaufen.', (220, 80, 60))
                return False  # nicht advance_stage rufen

        elif stype == _qd.StageType.ESCORT:
            # Prüfen ob NPC am Ziel angekommen
            npc_name = target.get('npc_name')
            dest = target.get('destination')
            dest_biome = target.get('biome')
            if not _npc_is_alive(game, npc_name):
                # NPC tot → Quest scheitert (revert ESCORT-Stage)
                self.timer = 0.0
                if hasattr(game, 'toast'):
                    game.toast(
                        f'„{self.title}": {npc_name} ist gefallen.',
                        (220, 130, 80))
                return False
            if dest is not None:
                # Distanz NPC↔dest
                npc_obj = _find_npc(game, npc_name)
                if npc_obj is not None:
                    dx = npc_obj.pos.x - dest[0]
                    dy = npc_obj.pos.y - dest[1]
                    if (dx * dx + dy * dy) <= 60 * 60:
                        return True
            elif dest_biome is not None:
                if getattr(game, 'biome', None) == dest_biome:
                    return True

        return False

    # ---- Stage-Transition ----
    def advance_stage(self, game):
        """Markiert aktuelle Stage als done, geht zur nächsten.

        Update #116: Per-Stage-Counter (count, timer, puzzle_progress)
        werden beim Übergang gecleart.  CONDITIONAL-Stages mit nicht
        erfüllter Flag-Bedingung werden automatisch übersprungen.
        """
        st = self.stage
        if st is None:
            return
        # Quote-Toast (Lore-Hook)
        quote = st.get('on_complete')
        if quote and hasattr(game, 'toast'):
            game.toast(quote, (220, 200, 170))
        self.stage_index += 1
        self.count = 0
        self.timer = 0.0
        self.puzzle_progress = []
        # Update #116: CONDITIONAL auto-skip — überspringt Stages mit
        # nicht-passender flag-Bedingung; iteriert bis Stage ohne
        # CONDITIONAL oder bis Quest-Ende erreicht.
        while self.stage_index < len(self.quest['stages']):
            next_st = self.quest['stages'][self.stage_index]
            if next_st.get('type') != _qd.StageType.CONDITIONAL:
                break
            req = next_st.get('target', {}).get('requires_flag', '')
            if _check_flag_condition(game, req):
                # Bedingung erfüllt — bleib auf dieser Stage
                break
            # Bedingung nicht erfüllt — Skip
            self.stage_index += 1
            self.count = 0
            self.timer = 0.0
        # Komplett?
        if self.stage_index >= len(self.quest['stages']):
            self._mark_complete(game)
        else:
            # Update #X — Phase-2-AI-SFX bei Stage-Advance
            _play_quest_sound(game, 'quest_marker_reach')
            # Stage-Update-Toast + große Banner-Notification (G-12).
            if hasattr(game, 'toast'):
                next_st = self.stage
                game.toast(f'„{self.title}" → {next_st["text"]}',
                           (255, 220, 80))
            if hasattr(game, 'push_event_notification'):
                game.push_event_notification(
                    'quest',
                    f'Quest-Fortschritt: {self.title}',
                    sub=self.stage.get('text', ''),
                    color=(255, 220, 100), duration=3.4)
            if hasattr(game, 'push_event_log'):
                game.push_event_log(
                    f'★ {self.title} — {self.stage.get("text", "")}'[:60],
                    (255, 220, 100))
            _play_quest_sound(game, 'quest_update')

    def _mark_complete(self, game):
        self.completed = True
        # Reward
        reward = self.quest.get('reward', {})
        gold = reward.get('gold', 0)
        xp = reward.get('xp', 0)
        if gold and hasattr(game, 'player'):
            game.player.gold += gold
        if xp:
            try:
                from . import progression
                progression.grant_xp(game.player, xp)
            except Exception:
                pass
        # Item (lore-name) — falls Inventar zugänglich
        item_name = reward.get('item')
        if item_name and hasattr(game, 'player'):
            try:
                # Lege als „lore_item" in den Inventar-Bag, ohne Engine-Stats
                if not hasattr(game.player, 'lore_items'):
                    game.player.lore_items = []
                game.player.lore_items.append(item_name)
            except Exception:
                pass
        # Update #117 (WELT_AUFBAU 6.1): Faction-Rep-Belohnung.
        # `reward['faction_rep'] = {faction_key: amount, ...}`
        # apply_quest_reward wendet Konflikt-Matrix + Toasts an.
        if 'faction_rep' in reward and hasattr(game, 'player'):
            try:
                from . import faction as _fac
                _fac.apply_quest_reward(game.player, reward, game)
            except Exception:
                pass
        # Komplett-Quote
        quote = self.quest.get('on_complete_quote')
        if hasattr(game, 'toast'):
            game.toast(f'★ Quest abgeschlossen: {self.title}',
                       (255, 220, 100))
            if quote:
                game.toast(quote, (215, 200, 175))
        if hasattr(game, 'push_event_notification'):
            # Update #135: Quest-Complete-Banner größer + länger.
            # 4.4 s → 6.0 s + gold-saturierter Color statt blass.
            game.push_event_notification(
                'quest',
                f'★ QUEST ABGESCHLOSSEN ★  {self.title}',
                sub=quote or 'Kehre zum Geber zurück',
                color=(255, 240, 130), duration=6.0)
        _play_quest_sound(game, 'quest_complete')
        # Update #135: zusätzlich großer Gold-Particle-Burst um Player
        # + Camera-Shake-Pulse + Klassen-Voice-Line.  Macht Quest-Ende
        # spürbar (nicht nur Toast).
        try:
            p = game.player
            if hasattr(game, 'spawn_particles'):
                # Gold-Rain (50 Particles, gravity nach unten)
                game.spawn_particles(
                    p.pos.x, p.pos.y - 40,
                    50, (255, 215, 90),
                    life_max=1.8, size_max=5, gravity=80)
                # 8-Strahl Pulse-Ring
                game.spawn_particles(
                    p.pos.x, p.pos.y,
                    24, (255, 240, 150),
                    life_max=0.9, size_max=4, gravity=-20)
            if hasattr(game, 'shake'):
                game.shake = max(game.shake, 10)
            # Class-Voice-Line (Triumph) — z.B. crit-Pool als „YES"
            try:
                from . import sounds as _snd
                _snd.play_class_voice(p.cls, 'level_up', volume=0.75)
            except Exception:
                pass
            # Bonus-Floater am Player
            if hasattr(game, 'floaters'):
                from .entities import Floater
                game.floaters.append(Floater(
                    p.pos.x, p.pos.y - 60,
                    'QUEST!', (255, 220, 100), big=True, life=1.6))
        except Exception:
            pass


class QuestLog:
    """Game-Modul-State für alle Quests."""
    def __init__(self):
        self.active = {}    # qid → QuestState
        self.completed = set()
        self.discovered_lore = set()  # für Codex
        self.bestiary_seen = set()    # für Codex

    def offer(self, qid):
        if qid in self.active or qid in self.completed:
            return None
        q = _qd.quest_by_id(qid)
        if q is None:
            return None
        st = QuestState(q)
        self.active[qid] = st
        return st

    def ensure_initial(self):
        """Startet die Default-Akt-1-Quests bei Game-Start."""
        for qid in _qd.initial_quests_for_new_game():
            self.offer(qid)

    def has_quest_for_npc(self, npc_name):
        """Gibt es eine aktive Quest, deren aktuelle Stage diesen NPC braucht?"""
        for st in self.active.values():
            stage = st.stage
            if stage is None:
                continue
            tgt = stage.get('target', {})
            if tgt.get('npc_name') == npc_name:
                return st
        return None

    def npc_has_offer(self, npc_name):
        """True wenn dieser NPC eine neue, noch nicht angenommene Quest hat."""
        for q in _qd.quests_offered_by_npc(npc_name):
            qid = q['id']
            if qid not in self.active and qid not in self.completed:
                return q
        return None

    def npc_marker(self, npc_name):
        """Returnt '!' wenn neue Quest verfügbar, '?' wenn aktuelle Stage hier
        abzuschließen ist, sonst None.
        """
        if self.has_quest_for_npc(npc_name):
            return '?'
        if self.npc_has_offer(npc_name):
            return '!'
        return None

    def main_quest_state(self):
        """Returnt die aktive Hauptquest (zur Anzeige im HUD)."""
        for st in self.active.values():
            if st.is_main:
                return st
        # Fallback: irgendeine aktive Quest
        for st in self.active.values():
            return st
        return None

    def all_active(self):
        return list(self.active.values())

    # ---- Update #116: Per-Frame-Tick für ESCORT/DEFEND/TIMED ----
    def tick(self, dt, game):
        """Tickt alle aktiven Quests einmal pro Frame.

        Wird von `Game.update(dt)` aufgerufen.  Zeit-basierte Stages
        (DEFEND/TIMED/ESCORT) prüfen sich hier selbst — keine externe
        Event-Quelle.
        """
        for st in list(self.active.values()):
            ok = st.tick(dt, game)
            if ok:
                # tick() returned True = Stage fertig
                _advance(st, game, self)


# ============================================================
# EVENT-HANDLER (vom Game-Code aufgerufen)
# ============================================================

def on_kill(game, enemy):
    """Wird in combat.kill_enemy gerufen."""
    log = _get_log(game)
    if log is None:
        return
    # Bestiarium-Discovery für Codex
    bkey = getattr(enemy, 'bestiary_key', None)
    if bkey and bkey not in log.bestiary_seen:
        log.bestiary_seen.add(bkey)

    for st in list(log.active.values()):
        stage = st.stage
        if stage is None:
            continue
        if stage['type'] != _qd.StageType.KILL:
            continue
        target = stage.get('target', {})
        bkey_target = target.get('bestiary_key')
        type_target = target.get('type_key')
        is_match = False
        if bkey_target and getattr(enemy, 'bestiary_key', None) == bkey_target:
            is_match = True
        elif type_target and getattr(enemy, 'type_key', None) == type_target:
            is_match = True
        if is_match:
            st.count += 1
            need = stage.get('count', 1)
            if st.count >= need:
                _advance(st, game, log)


def on_reach_biome(game, biome):
    """Aufruf wenn Spieler ein Biome betritt (enter_dungeon o.ä.)."""
    log = _get_log(game)
    if log is None:
        return
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.REACH:
            continue
        target = stage.get('target', {})
        if target.get('biome') == biome:
            _advance(st, game, log)


def on_reach_boss_room(game):
    """Player betritt den Boss-Raum (für REACH-Stages mit boss_room=True)."""
    log = _get_log(game)
    if log is None:
        return
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.REACH:
            continue
        target = stage.get('target', {})
        if target.get('boss_room'):
            _advance(st, game, log)


def on_talk(game, npc_name):
    """Player redet mit NPC (Interaktion)."""
    log = _get_log(game)
    if log is None:
        return False
    # Erst: Stage-Ziel "talk" / "return" voll-machen
    progressed = False
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None:
            continue
        tgt = stage.get('target', {})
        if tgt.get('npc_name') != npc_name:
            continue
        if stage['type'] in (_qd.StageType.TALK, _qd.StageType.RETURN):
            _advance(st, game, log)
            progressed = True
    # Dann: neue Quest anbieten
    if not progressed:
        offer = log.npc_has_offer(npc_name)
        if offer is not None:
            log.offer(offer['id'])
            _play_quest_sound(game, 'quest_accept')
            # Update #127: NPC-Voice-Line „quest_offer" aus voice_registry
            # falls vorhanden — Lore-Anker statt nur generic SFX.
            try:
                from . import sounds as _snd
                voice_key = _VOICE_NPC_KEY.get(npc_name)
                if voice_key:
                    _snd.play_voice(voice_key, 'quest_offer', volume=0.85)
            except Exception:
                pass
            if hasattr(game, 'toast'):
                game.toast(f'Neue Quest: {offer["title"]}', (255, 215, 100))
    return progressed


# Update #127: zentrales NPC-Name → voice_registry-Key Mapping.
# Wird in `on_talk` für quest_offer-Voices verwendet.
_VOICE_NPC_KEY = {
    'Korven Vor':                      'korven',
    'Bruder Helst':                    'helst',
    'Bruder Helst der Hundertjährige': 'helst',
    'Vossharil':                       'vossharil',
    'Vossharil die Dreimalige':        'vossharil',
    'Tameris':                         'tameris',
    'Otreth Hohlauge':                 'otreth',
    'Mara die Mahnerin':               'mara',
    'Inquisitor-General Vehren':       'vehren',
    'Die Drei Mütter':                 'drei_muetter',
}


def on_interact_decor(game, decor):
    """Player interagiert mit Decor (Lore-Tafel, Altar)."""
    log = _get_log(game)
    if log is None:
        return
    kind = getattr(decor, 'kind', None)
    if kind == 'lore_tablet':
        text = getattr(decor, 'lore_text', '')
        if text:
            log.discovered_lore.add(text)
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.INTERACT:
            continue
        tgt = stage.get('target', {})
        if tgt.get('decor_kind') == kind:
            st.count += 1
            need = stage.get('count', 1)
            if st.count >= need:
                _advance(st, game, log)


def on_gem_pickup(game):
    """Wird beim Loot-Aufnehmen für gem-Type aufgerufen."""
    log = _get_log(game)
    if log is None:
        return
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.COLLECT:
            continue
        tgt = stage.get('target', {})
        if tgt.get('item_kind') == 'gem':
            st.count += 1
            need = stage.get('count', 1)
            if st.count >= need:
                _advance(st, game, log)


def on_dungeon_complete(game):
    """Legacy-Hook — aktuell unbenutzt (kein no_death-Quest mehr)."""
    pass


# ============================================================
# Update #116 — WELT_AUFBAU 3.1: Event-Handler für neue Stage-Types
# ============================================================

def on_choice(game, flag_name, value):
    """CHOICE-Stage: Spieler wählt eine Option.

    Setzt `game.flags[flag_name] = value` und schreitet die aktive
    CHOICE-Stage mit passendem `target.flag` weiter.

    Beispiel: on_choice(game, 'shulavh_choice', 'heal')
    """
    log = _get_log(game)
    if log is None:
        return
    if not hasattr(game, 'flags') or game.flags is None:
        game.flags = {}
    game.flags[flag_name] = value
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.CHOICE:
            continue
        tgt = stage.get('target', {})
        if tgt.get('flag') != flag_name:
            continue
        options = tgt.get('options', [])
        if options and value not in options:
            continue
        _advance(st, game, log)


def on_puzzle_step(game, step_key):
    """PUZZLE-Stage: Spieler aktiviert ein Sequenz-Element.

    Wenn die Reihenfolge passt, wird das Element zur `puzzle_progress`
    hinzugefügt.  Falsche Reihenfolge resettet `puzzle_progress` auf [].

    Beispiel-Sequenz: ['glasgolden', 'goetterkrieg', 'gegenwart']
    Player aktiviert 'glasgolden' → progress=['glasgolden'] (1/3).
    """
    log = _get_log(game)
    if log is None:
        return
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.PUZZLE:
            continue
        seq = stage.get('target', {}).get('sequence', [])
        if not seq:
            continue
        expected_idx = len(st.puzzle_progress)
        if expected_idx >= len(seq):
            continue
        expected = seq[expected_idx]
        if step_key == expected:
            st.puzzle_progress.append(step_key)
            if len(st.puzzle_progress) >= len(seq):
                _advance(st, game, log)
            else:
                if hasattr(game, 'toast'):
                    game.toast(
                        f'Reihenfolge richtig ({len(st.puzzle_progress)}/'
                        f'{len(seq)}).',
                        (220, 200, 120))
        else:
            # Falscher Schritt — reset
            st.puzzle_progress = []
            if hasattr(game, 'toast'):
                game.toast(
                    'Reihenfolge falsch — von vorn.', (220, 130, 80))


def on_npc_arrived(game, npc_name):
    """ESCORT-Stage: NPC hat sein Ziel erreicht.

    Optional aufrufbar als externer Trigger; das `QuestState.tick()`
    prüft das auch automatisch über Position-Check.
    """
    log = _get_log(game)
    if log is None:
        return
    for st in list(log.active.values()):
        stage = st.stage
        if stage is None or stage['type'] != _qd.StageType.ESCORT:
            continue
        if stage.get('target', {}).get('npc_name') == npc_name:
            _advance(st, game, log)


# ============================================================
# Internal-Helpers für neue Stage-Types
# ============================================================

def _npc_is_alive(game, npc_name):
    """True wenn ein NPC mit `npc_name` in `game.npcs` existiert.

    Im Outpost/Town werden NPCs nicht zu Enemies (kein HP-Drop),
    daher reicht „in der Liste".  Falls Outpost-NPCs in Future-
    Updates verwundbar werden, hier Health-Check ergänzen.
    """
    if npc_name is None:
        return False
    for n in getattr(game, 'npcs', ()):
        if getattr(n, 'name', '') == npc_name:
            return True
    return False


def _find_npc(game, npc_name):
    """Returnt NPC-Instanz mit `npc_name` oder None."""
    for n in getattr(game, 'npcs', ()):
        if getattr(n, 'name', '') == npc_name:
            return n
    return None


def _player_near_npc(game, npc_name, radius=200):
    """True wenn Player innerhalb `radius` zu NPC."""
    npc = _find_npc(game, npc_name)
    if npc is None:
        return False
    p = getattr(game, 'player', None)
    if p is None:
        return False
    return (npc.pos - p.pos).length() <= radius


def _check_flag_condition(game, expr):
    """Wertet einen Flag-Vergleich aus.

    Format: `"flag_name=value"` oder `"flag_name!=value"` oder
            `"flag_name"` (truthy-check).

    Returnt True wenn die Bedingung erfüllt ist; sonst False.
    """
    if not expr:
        return True
    flags = getattr(game, 'flags', None) or {}
    if '!=' in expr:
        name, value = expr.split('!=', 1)
        return flags.get(name.strip()) != value.strip()
    if '=' in expr:
        name, value = expr.split('=', 1)
        return flags.get(name.strip()) == value.strip()
    return bool(flags.get(expr.strip()))


# ============================================================
# Helpers
# ============================================================
def _get_log(game):
    return getattr(game, 'quest_log', None)


def _advance(st, game, log):
    st.advance_stage(game)
    if st.completed:
        log.completed.add(st.quest['id'])
        del log.active[st.quest['id']]


def _play_quest_sound(game, key):
    """Spielt einen UI-Bus-Sound (Audio-Bibel 6.5)."""
    try:
        from . import sounds as _snd
        _snd.play(key, volume=0.8, bus='ui')
    except Exception:
        pass


# ============================================================
# LEGACY-KOMPAT (für Dungeon-Quest-System)
# ============================================================
# Die alten Dungeon-Objectives sind weiterhin nutzbar als Quest mit
# „virtual"-id. Wir behalten die Legacy-Klasse für Backward-Compat.

class Quest:
    """Legacy-Klasse für Dungeon-Objectives (DUNGEONS-spec)."""
    def __init__(self, dungeon_id):
        from .constants import DUNGEONS
        self.dungeon_id = dungeon_id
        spec = DUNGEONS[dungeon_id]
        self.objectives = []
        for kind, label, reward, target in spec['objectives']:
            self.objectives.append([kind, label, reward, target, 0, False])

    def all_complete(self):
        return all(o[5] for o in self.objectives)

    def boss_complete(self):
        return any(o[0] == 'boss' and o[5] for o in self.objectives)

    def lines(self):
        return [(o[1], o[4], o[3], o[5]) for o in self.objectives]
