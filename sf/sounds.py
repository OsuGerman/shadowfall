"""Procedural Sound-Effekte und Hintergrund-Musik (synth, keine Dateien).

Verbessert: ADSR-Envelopes, FM-/AM-Modulation, Layered Voices,
Stereo, Reverb-Annäherung, pre-rendered Music-Loops.
"""

import array
import math
import random
import pygame


_SOUND_CACHE = {}
_MUSIC_CACHE = {}
_ENABLED = False
# 44100 Hz Standard fuer MP3-Wiedergabe (vorher 22050 → Stoergeraeusch)
_RATE = 44100
_CHANNELS = 2
_current_music = None
_current_music_name = None
# True wenn aktueller Track via pygame.mixer.music (externe MP3) statt
# Channel(0) (procedural) läuft. Wird für Dedup gebraucht, damit play_music()
# den MP3-Track nicht jedes Frame neu lädt.
_music_using_external = False

# ============================================================
# Update #126 — SFX-RELIABILITY-PIPELINE
# (User-Report „nicht alle sounds und effekte werden zuverlässig
# wiedergegeben teilweise sounds viel zu laut oder manchmal einfach
# ausgelassen")
# ============================================================
# Drei Mechaniken um die SFX-Zuverlässigkeit zu fixen:
#   1. SFX-Channel-Pool 3..N-1 explizit verwaltet (round-robin + force-
#      replace bei voll); Channels 0/1/2 bleiben Music/Ambient/Step.
#   2. Dedup-Window 40 ms verhindert dass identische Sounds mehrfach
#      pro Frame stacken (5 Mobs sterben simultan = 1 Death-Sound nicht 5).
#   3. Per-Sound Volume-Cap für inherent laute Builds (`roar`, `aoe_impact`).
_SFX_CHANNEL_FIRST = 3      # Channels 0=music, 1=ambient, 2=step
_SFX_CHANNEL_COUNT = 27     # 32 total - 3 reserved - 2 voice → 27 SFX
_LAST_PLAY_MS = {}          # sound_name → pygame.time.get_ticks()
_DEDUP_WINDOW_MS = 40       # Min-Spacing zwischen identischen Sounds

# Update #129 — VOICE-CHANNEL-RESERVATION + ANTI-OVERLAP
# (User-Report „viele Voice-Lines werden abgeschnitten oder spielen
# aufeinander")
#
# Bisher: play_file(bus='voice') rief snd.play() ohne expliziten
# Channel → pygame nimmt irgendeinen freien Channel im Pool, auch
# SFX-Channels.  Daher konnte ein neuer SFX (z.B. monster_bite) eine
# laufende Voice-Line auf demselben Channel überschreiben.
#
# Fix:
#   - 2 dedizierte Voice-Channels (30=dialog, 31=combat-class).
#     Diese stehen nicht im SFX-Round-Robin.  Kein SFX kann sie
#     überschreiben.
#   - Dialog-Voice (NPC-greeting/quest_offer/lore/twist_reveal):
#     wenn dialog-Channel busy → NEUE Voice SKIPPEN (lass die
#     laufende Line zu Ende spielen).  Verhindert Overlap-Kakophonie
#     beim Korven/Helst-Doppelgreeting.
#   - Combat-Voice (class crit/death/level_up/attack/big_skill):
#     wenn busy → REPLACE (Spieler braucht zeitnahes Feedback,
#     veraltete Crit-Voice schon weg).
#   - Voice-Dedup: per (npc, category) 800 ms — verhindert dass
#     identische Greeting-Lines beim Spam-Klick auf einen NPC stacken.
_VOICE_CHANNEL_DIALOG = 30
_VOICE_CHANNEL_COMBAT = 31
_VOICE_DEDUP_WINDOW_MS = 800
_LAST_VOICE_MS = {}         # (npc_key, category) → ticks
# Categories, die als „Combat-Voice" zählen → dürfen unterbrechen
_COMBAT_VOICE_CATS = {
    'attack', 'big_skill', 'crit', 'level_up', 'death',
}

# Per-Sound Volume-Cap (1.0 = kein Cap). Wird VOR effective_volume
# multipliziert.  Anhand der bekannten lauten procedural-Sounds gewählt.
_VOLUME_CAP = {
    'roar':         0.75,   # Boss-Roar ist inherent laut
    'aoe_impact':   0.70,   # AoE-Explosion stackt schnell
    'hit_heavy':    0.80,   # Schwerer Hit
    'boss_bong':    0.85,   # Tubular-Bell ist sehr resonant
    'cast_lightning': 0.85,  # Lightning-Crack
    'cast_fire':    0.85,   # Fire-Whoosh
    'cast_frost':   0.85,   # Frost-Crystal
    'cast_dark':    0.80,
    'death':        0.80,
    'monster_bite': 0.75,
    'slime_attack': 0.70,
    # Update #128 (User-Report „GoT-Sound zu laut"): Quest-Sounds hart
    # gecappt für den Fall dass eine alte Save / ein externer Hook den
    # alten Stock-Sound direkt anspricht.  Mit den PHASE2-Hints landet
    # der Engine-Call normalerweise auf `ui_quest_advance` (leiser).
    'quest_notify':   0.40,
    'quest_update':   0.40,
    'quest_complete': 0.50,
    'quest_accept':   0.50,
    'levelup':        0.65,   # Universfield-Level-Up-Fanfare auch laut
    'levelup_fanfare': 0.65,
}


def _alloc_sfx_channel():
    """Update #126: findet eine freie SFX-Channel oder force-replaced die
    älteste.  Returnt None nur wenn der Mixer nicht initialisiert ist.

    Channels 0/1/2 (Music/Ambient/Step) werden NIE überschrieben.
    """
    if not _ENABLED:
        return None
    try:
        # Erst: freie Channel im SFX-Bereich suchen
        for i in range(_SFX_CHANNEL_FIRST,
                       _SFX_CHANNEL_FIRST + _SFX_CHANNEL_COUNT):
            ch = pygame.mixer.Channel(i)
            if not ch.get_busy():
                return ch
        # Alle SFX-Channels belegt → die mit dem niedrigsten Volume
        # ersetzen (vermutlich der älteste/abklingende Sound).
        # Pygame hat keine native „älteste" API, also nehmen wir
        # einfach die erste Channel im Pool — Round-Robin-Effekt
        # durch _last_alloc-Index.
        global _last_sfx_alloc
        if '_last_sfx_alloc' not in globals():
            _last_sfx_alloc = _SFX_CHANNEL_FIRST
        _last_sfx_alloc = ((_last_sfx_alloc - _SFX_CHANNEL_FIRST + 1)
                            % _SFX_CHANNEL_COUNT) + _SFX_CHANNEL_FIRST
        ch = pygame.mixer.Channel(_last_sfx_alloc)
        ch.stop()
        return ch
    except (pygame.error, AttributeError):
        return None


def _check_dedup(name):
    """Returnt True wenn der Sound gespielt werden darf (außerhalb
    Dedup-Window), False wenn er gerade gerade erst gespielt wurde.

    Erster Aufruf (Name nicht im Dict) ist immer True — wichtig für
    den Fall pygame.time.get_ticks()==0 in der ersten Frame nach Init.
    """
    if name not in _LAST_PLAY_MS:
        try:
            _LAST_PLAY_MS[name] = pygame.time.get_ticks()
        except Exception:
            _LAST_PLAY_MS[name] = 0
        return True
    try:
        now_ms = pygame.time.get_ticks()
    except Exception:
        return True
    last = _LAST_PLAY_MS[name]
    if now_ms - last < _DEDUP_WINDOW_MS:
        return False
    _LAST_PLAY_MS[name] = now_ms
    return True


def _apply_volume_cap(name, volume):
    """Multipliziert volume mit dem Per-Sound-Cap (Default 1.0)."""
    return volume * _VOLUME_CAP.get(name, 1.0)

# ============================================================
# BUS-VOLUME-HIERARCHY (VELGRAD_AUDIO_DESIGN_BIBEL.md Teil 1.2)
# ============================================================
# Pygame-Light-Version von FMOD/Wwise-Bus-Struktur: 5 Sub-Volumes,
# alle ×= MASTER. Snapshot-System (Teil 1.4) multipliziert dann
# zusätzlich pro Bus.
MASTER_VOLUME   = 0.65   # Update #32: -35% Master nach User-Feedback
# Update #99: Music-Bus weiter gedämpft (User „BG-Musik zu laut").
# Slider 0.0..1.0 entspricht jetzt durchgängig dem Bus-Faktor, der
# zusätzlich durch MASTER × SNAPSHOT modifiziert wird (effective_volume).
MUSIC_VOLUME    = 0.30   # MUSIC bus (war 0.40)
SFX_VOLUME      = 0.55   # SFX/Combat/Skills (war 0.85)
AMBIENT_VOLUME  = 0.35   # ENVIRONMENT (war 0.55)
VOICE_VOLUME    = 0.70   # NPC_VOICE (war 1.00)
UI_VOLUME       = 0.60   # UI_NAVIGATION (war 0.85)

# Aktuelle Snapshot-Modifier: Multiplikatoren pro Bus.
# Werden in apply_snapshot / clear_snapshot gesetzt und in den
# Auflösungs-Methoden (effective_music_volume etc.) gelesen.
_SNAPSHOT = {  # default → identity
    'music': 1.0, 'sfx': 1.0, 'ambient': 1.0,
    'voice': 1.0, 'ui': 1.0,
}
_ACTIVE_SNAPSHOT = 'DEFAULT'

# Snapshot-Definitionen (Audio-Bibel Teil 1.4).
# Pro Snapshot: dict von Bus → Faktor. Nicht enthaltene Buses = 1.0.
SNAPSHOTS = {
    'DEFAULT': {},
    # NPC spricht / Modal-Dialog offen: Music duck 30 %, SFX 60 %.
    'DIALOG': {'music': 0.30, 'sfx': 0.60, 'ambient': 0.50},
    # Inventar/Skilltree/Shop offen: Music duck 30 %, Ambient aus.
    'MENU_OPEN': {'music': 0.30, 'ambient': 0.20, 'sfx': 0.50},
    # Boss-Spawn-Cinematic: Ambience aus, Boss-Sounds 100 %.
    'BOSS_INTRO': {'ambient': 0.0, 'sfx': 1.0, 'voice': 1.2,
                    'music': 0.85},
    # Player-Death-Transition: alles auf -20 dB ≈ 0.1.
    'DEATH_TRANSITION': {'music': 0.25, 'sfx': 0.25,
                          'ambient': 0.10, 'voice': 0.40,
                          'ui': 0.50},
    # Vergessens-Welle / Anomalie-Nähe (Stille Zone, Audio-Bibel 7.4).
    'STILLE_ZONE': {'music': 0.10, 'sfx': 0.30, 'ambient': 0.05},
}


def apply_snapshot(name):
    """Aktiviert ein Mixer-Snapshot (Audio-Bibel 1.4). Idempotent."""
    global _SNAPSHOT, _ACTIVE_SNAPSHOT
    if name == _ACTIVE_SNAPSHOT:
        return
    cfg = SNAPSHOTS.get(name, {})
    _SNAPSHOT = {bus: 1.0 for bus in
                 ('music', 'sfx', 'ambient', 'voice', 'ui')}
    _SNAPSHOT.update(cfg)
    _ACTIVE_SNAPSHOT = name
    # Music-Volume live nachziehen (andere Buses via Lookup beim Play)
    _refresh_music_volume()


def clear_snapshot():
    apply_snapshot('DEFAULT')


def active_snapshot():
    return _ACTIVE_SNAPSHOT


def effective_volume(bus, base_vol=1.0):
    """Returnt finale Lautstärke = MASTER × BUS × SNAPSHOT × base."""
    mod = _SNAPSHOT.get(bus, 1.0)
    bus_vol = {
        'music':   MUSIC_VOLUME,
        'sfx':     SFX_VOLUME,
        'ambient': AMBIENT_VOLUME,
        'voice':   VOICE_VOLUME,
        'ui':      UI_VOLUME,
    }.get(bus, 1.0)
    return max(0.0, min(1.0, MASTER_VOLUME * bus_vol * mod * base_vol))


def _refresh_music_volume():
    """Pusht das berechnete Music-Volume an pygame.mixer.music."""
    if not _ENABLED:
        return
    vol = effective_volume('music')
    # Town-Trim bleibt erhalten (siehe play_music)
    if _music_using_external and _current_music_name and \
            (_current_music_name == 'town' or
             _current_music_name.startswith('town:')):
        vol *= 0.85
    try:
        pygame.mixer.music.set_volume(max(0.0, min(1.0, vol)))
    except Exception:
        pass
    try:
        pygame.mixer.Channel(0).set_volume(vol)
    except Exception:
        pass

# Pfad zu externer Musikdatei und Sounds-Ordner
import os as _os
_HERE = _os.path.dirname(_os.path.abspath(__file__))
_PARENT = _os.path.dirname(_HERE)
EXTERNAL_MUSIC_PATH = _os.path.join(_PARENT, 'Nebel von Arken.mp3')
# Zentraler Audio-Ordner — alle weiteren Tracks/SFX werden hier gesucht.
SOUNDS_DIR = _os.path.join(_PARENT, 'Sounds')

# Music-Track-Registry: play_music(track_name) sucht hier nach einer Datei,
# bevor auf procedural-Synth zurückgefallen wird.
# Schlüssel = Track-Identifier (passend zu boss_encounter.music_swap), Wert =
# Datei-Pfad relativ zu SOUNDS_DIR.
# Lore-Verbindung: Track-Namen referenzieren NPCs/Akte aus
# VELGRAD_BESTIARIUM.md und VELGRAD_LORE_BIBEL.md.
MUSIC_FILES = {
    'salzhueter_brut': 'Salzhüter-Brut (Akt 1).mp3',  # Bestiarium #5, Akt 1
    'vehren':          'Vehrens Aschen Tribunal.mp3',  # Bestiarium NPC #7, Akt 3
    'main_2':          'Main soundtrack 2.mp3',        # Alt-Town/Dungeon-Track
}


# Playlists: bei `play_music(playlist_key)` wird ein zufälliger Track aus
# der Liste gewählt; bei Re-Entry kommt ein ANDERER Track als der zuletzt
# gespielte. Tracks sind File-Pfade (absolut) oder MUSIC_FILES-Keys.
# Nebel-von-Arken liegt im Root, nicht in Sounds/ — wir tracken sie
# als Pseudo-Key '_nebel_von_arken'.
MUSIC_PLAYLISTS = {
    'town':    ['_nebel_von_arken', 'main_2'],
    'dungeon': ['_nebel_von_arken', 'main_2'],
    # Update #43: Titel-Screen-Musik (User „Im Hauptmenu ist keine Musik")
    'title':   ['_nebel_von_arken', 'main_2'],
}

# ============================================================
# REGION-MUSIC-MAP (Audio-Bibel Teil 7 + Bibel Teil 4)
# ============================================================
# Pro Biome (Velgrad-Region) ein Bevorzugter Music-Track.
# Wenn der Track noch nicht im Sounds-Ordner liegt, fällt das
# System automatisch auf die Town/Dungeon-Playlist zurück.
#
# Asset-Naming-Konvention (Audio-Bibel Teil 11): MUSIC_AKTNN_<Kontext>.
# Sobald Designer eigene Akt-Tracks bereitstellt, hier eintragen.
REGION_MUSIC = {
    'town':   'town',     # Playlist (Nebel + Main-2)
    'crypt':  'dungeon',  # Akt 1 Salzküste → Playlist
    'frost':  'dungeon',  # Akt 2 Glasgoldene Ruinen → tbd
    'lava':   'dungeon',  # Akt 3 Aschenfelder → tbd (Boss = vehren-Track)
    'swamp':  'dungeon',  # Akt 4 Wurzelgrab → tbd
    'astral': 'dungeon',  # Akt 5 Spiegelstadt → tbd
    'desert': 'dungeon',  # Zhar-Eth → tbd
}


def music_for_biome(biome):
    """Returnt den passenden Music-Key für ein Biome. Default = 'dungeon'."""
    return REGION_MUSIC.get(biome, 'dungeon')

# Track der zuletzt aus einer Playlist gewählt wurde (pro Playlist-Key),
# damit Re-Entry rotiert statt repeat.
_last_playlist_pick = {}


def _resolve_music_file(track_name):
    """Returnt absoluten Pfad zur Music-Datei oder None."""
    fn = MUSIC_FILES.get(track_name)
    if fn is None:
        return None
    full = _os.path.join(SOUNDS_DIR, fn)
    return full if _os.path.exists(full) else None


# ============================================================
# SFX-File-Alias-Map (Update #27)
# ============================================================
# Erlaubt verbose Dateinamen (vom Audio-Designer) auf interne SFX-Keys
# zu mappen. Beispiel: `cast_fire` → `yodguard-fire-magic-5-378639.mp3`.
# Wird in _resolve_sfx_file VOR der direkten Match-Suche konsultiert.
SFX_FILE_ALIASES = {
    # ============================================================
    # Update #31 — Sound-File-Length-Awareness
    # ============================================================
    # SHORT SFX (< 2 s, OK für häufige Trigger wie Casts, Treffer):
    'cast_fire':       'yodguard-fire-magic-5-378639',     # 1.7s
    'cast_lightning':  'yodguard-wind-magic-5-378630',     # 1.7s
    'cast_heal':       'yodguard-healing-magic-5-378667',  # 1.7s
    'cast_dark':       'yodguard-dark-magic-6-378652',     # 1.7s
    'spell_impact':    'rescopicsound-elemental-magic-spell-impact-outgoing-228342',
    'melee_swing':     'xpmonster-quick-swing-sound-419581',  # < 0.5s
    'sword_slash':     'daviddumaisaudio-sword-slash-and-swing-185432',  # < 1s
    'monster_bite':    'freesound_community-monster-bite-44538',  # < 1s
    # MEDIUM SFX (2-5 s, OK für gelegentliche Trigger):
    'monster_howl':    'freesound_community-monster-howl-85304',  # ~3s
    'cave_monster':    'freesound_community-cave-monster-43826',  # ~3s
    'slime_attack':    'freesound_community-slime-monster-noises-66776',
    'breath_low_hp':   'freesound_community-breathing-6811',     # ~10s (Loop)
    # LONG AMBIENT (> 10 s, NUR als Ambient-Loop, NICHT per-step!):
    'ambient_fire_loop':      'shut_up_ghost-fierce-crackling-fire-5-minutes-looped-135533',
    'firewood_burning':       'engyclick-firewood-burning-sound-179862',
    'ambient_ice_walking':    'gregorquendel_sounddesign-ice-winter-snow-walking-on-ice-iv-138238',
    'ambient_ice_creak':      'gregorquendel_sounddesign-ice-winter-snow-walking-on-ice-v-138240',
    'ambient_ice_deep':       'gregorquendel_sounddesign-ice-winter-snow-walking-on-ice-i-138237',
    'ambient_monster_growl':  'freesound_community-monster-growls-70784',  # ~30s, ambient
    'ambient_monster_step':   'freesound_community-monster-footsteps-01-82898',  # ~10s
    'ambient_boss_step':      'boos footsteeps',
    # Override für bestehende `roar`-Aufrufe (kurz genug für Trigger):
    'roar':            'freesound_community-monster-howl-85304',
    # ============================================================
    # Update #32 — Neue Sound-Aliases (Yodguard-Impact-Pack +
    # Universfield-UI + Dragon-Studio-Boss + Alesia-Davina-Vampire)
    # ============================================================
    # UI / Progression-Cues
    'levelup':         'universfield-level-up-08-402152',  # override
    'levelup_fanfare': 'universfield-level-up-08-402152',
    # Update #128 (User-Report „GoT-Notification ist der schlimmste und
    # lauteste Sound"): die drei quest_* Aliases auf die AI-generierte
    # `ui_quest_advance` umgeleitet (siehe SFX_PHASE2_HINTS). Der alte
    # GoT-Synth-Alert war 2-3× lauter als alle anderen Sounds + hatte
    # einen schroffen Brand-Cue.  Aliases auskommentiert damit der
    # PHASE2-Hint-Fallback greift.
    # 'quest_notify':    'diogodasilvasimoes-game-of-thrones-...-438279',
    # 'quest_update':    'diogodasilvasimoes-game-of-thrones-...-438279',
    # 'quest_complete':  'diogodasilvasimoes-game-of-thrones-...-438279',
    # Combat-Impact (Yodguard-Pack)
    'arrow_impact_1':  'yodguard-a-clean-and-precise-game-style-arrow-impact-1-450238',
    'arrow_impact_2':  'yodguard-a-clean-and-precise-game-style-arrow-impact-4-450239',
    'axe_metal_1':     'yodguard-a-massive-axe-impact-hitting-metal-1-450251',
    'axe_metal_2':     'yodguard-a-massive-axe-impact-hitting-metal-2-450253',
    'axe_metal_3':     'yodguard-a-massive-axe-impact-hitting-metal-3-450254',
    'axe_metal_4':     'yodguard-a-massive-axe-impact-hitting-metal-4-450252',
    'axe_dirt':        'yodguard-giant-axe-impact-striking-into-dirt-2-450260',
    'axe_wood':        'yodguard-giant-axe-strike-hitting-solid-wood-2-450250',
    'greatsword_swing_1': 'yodguard-heavy-greatsword-slash-in-the-air-2-450243',
    'greatsword_swing_2': 'yodguard-heavy-greatsword-slash-in-the-air-3-450245',
    # Boss / Explosion / Atmosphere
    'dragon_roar':       'dragon-studio-dragon-roar-364478',
    'epic_dragon_roar':  'dragon-studio-epic-dragon-roar-364481',
    'explosion_debris':  'dragon-studio-explosion-with-debris-494320',
    'cartoon_explosion': 'universfield-animated-cartoon-explosion-impact-352744',
    'witch_gaze':        'alesiadavina-female-vampire-calculating-gaze-508989',
}

# ============================================================
# Update #X — Phase-2-AI-SFX Engine-Aliases
# ============================================================
# Mapping von bestehenden Engine-Calls auf die in tools/sfx_gen.py
# (Phase 2, Sektion XI) generierten neuen Sounds. Die Resolver-Reihenfolge
# bevorzugt Stock vor AI, daher landen diese Eintraege hier (Stock-Layer).
# Reine AI-Aliase werden NICHT als Aliase-Eintrag eingetragen — sie
# werden ueber den SFX-Registry-Fallback in _resolve_from_sfx_registry
# aufgeloest und sind im Code direkt per sfx_id aufrufbar.
#
# Engine-Call -> AI-SFX-Datei (Stamm ohne .mp3, relativ zu Sounds/, dort
# liegt sie aber NICHT — der Resolver faellt durch und nimmt die AI-Version)
# Daher: NUR die "Velgrad-spezifischen" Verbesserungen werden hier als
# Aliase eingetragen, die direkt auf neue MP3s zeigen sollen. Footsteps
# pro Biome haben ihren eigenen Picker (siehe pick_footstep_for_biome).
SFX_PHASE2_HINTS = {
    # ============================================================
    # COMBAT-ENGINE-CALLS — Schaden/Treffer/Tod
    # ============================================================
    'hit':            'damage_light_cloth',
    'hit_heavy':      'damage_heavy_plate',
    'damage':         'damage_med_leather',
    'crit':           'crit_universal_v2',
    'death':          'player_death',

    # ============================================================
    # FOOTSTEPS — Engine ruft step_* via play_step
    # ============================================================
    'step_water':     'footstep_wet',
    'step_mud':       'footstep_roots',
    'step_wood':      'footstep_wood',
    'step_metal':     'footstep_metal',
    'step_town':      'footstep_wood',     # Brassweir-Pier-Holz
    'step_frost':     'footstep_marble',   # Glasgolden Ruinen
    'step_lava':      'footstep_ash',      # Aschenfelder
    'step_crypt':     'footstep_stone',    # Salzkueste-Krypta
    'step_astral':    'footstep_glass',    # Velharn Spiegel
    'step_desert':    'footstep_sand',     # Zhar-Eth
    'step_swamp':     'footstep_roots',
    'step_void':      'footstep_void',     # Hohlwort

    # ============================================================
    # BOSS-ENCOUNTER-KEY MAPPINGS — laenger als SFX-File-Stamm
    # ============================================================
    'salzhueter_brut_spawn':     'salzhueter_spawn',
    'salzhueter_brut_phase':     'salzhueter_phase',
    'salzhueter_brut_kill':      'salzhueter_kill',
    'velharn_trio_phase_1to2':   'velharn_phase_1to2',
    'velharn_trio_phase_2to3':   'velharn_phase_2to3',
    'velharn_trio_kill':         'velharn_kill',
    'shulavh_phase':             'shulavh_phase_madness',
    'im_nesh_phase':             'im_nesh_phase_1to2',

    # ============================================================
    # Update #127 — SPELL-CASTS (Lore-Aspekt-Mapping)
    # Lore-Bibel Teil 2: Element-Domains pro Aspekt.
    # ============================================================
    # Fire-Casts → Tribunal-Predigt (Valsas Brand-Echo)
    # Lore: Valsa fiel, das Tribunal predigt jetzt mit ihrer Asche-Stimme.
    # `aspekt_valsa_cast` existiert nicht in der Registry; wir nutzen
    # `predigtsprecher_cast` als lore-konformes Fire-Cast-Surrogat.
    'cast_fire':            'predigtsprecher_cast',
    'fireball_cast':        'predigtsprecher_cast',
    'cast_fire_release':    'aspekt_valsa_impact',
    # Lightning-Casts → Im-Nesh-Sprache (Sturm/Blitz)
    'cast_lightning':       'aspekt_imnesh_cast',
    'lightning_cast':       'aspekt_imnesh_cast',
    'cast_lightning_release': 'aspekt_imnesh_impact',
    # Cold/Frost-Casts → Nheyras Zeit (Hagel/Eis)
    'cast_frost':           'aspekt_nheyra_cast',
    'cast_cold':            'aspekt_nheyra_cast',
    'cast_frost_release':   'aspekt_nheyra_impact',
    # Dark/Chaos-Casts → Shulavhs Vergessen
    'cast_dark':            'aspekt_shulavh_cast',
    'cast_chaos':           'aspekt_shulavh_cast',
    'cast_void':            'aspekt_vergessen_cast',
    'cast_void_release':    'aspekt_vergessen_impact',
    # Physical/Kharn-Casts
    'cast_phys':            'aspekt_kharn_cast',
    'cast_physical':        'aspekt_kharn_cast',
    'cast_slam_release':    'aspekt_kharn_impact',
    # Heal-Casts → Ousens Auge (Mahnmal-Heilung)
    'cast_heal':            'aspekt_ousen_cast',
    'heal_cast':            'aspekt_ousen_cast',
    'heal_pulse':           'heal_tick',

    # ============================================================
    # Update #127 — AOE / IMPACT / TELEGRAPH
    # ============================================================
    'aoe_windup':           'boss_aoe_telegraph',
    'aoe_impact':           'aspekt_valsa_impact',  # default-Impact
    'spell_impact':         'aspekt_imnesh_impact',
    'arrow_impact_1':       'damage_med_leather',
    'arrow_impact':         'damage_med_leather',

    # ============================================================
    # Update #127 — UI / MENU / CLICK
    # ============================================================
    'click':                'ui_click',
    'hover':                'ui_hover',
    'modal_open':           'ui_modal_open',
    'modal_close':          'ui_modal_close',
    'menu_open':            'ui_modal_open',
    'menu_close':           'ui_modal_close',
    'menu_back':            'menu_back',
    'menu_cancel':          'menu_cancel',
    'menu_confirm':         'menu_confirm',
    'menu_select':          'menu_select',
    'menu_error':           'menu_error',
    'inventory_open':       'ui_inventory_open',
    'map_open':             'ui_map_open',
    'death_screen':         'ui_death_screen',

    # ============================================================
    # Update #127 — QUEST / LEVEL / PICKUP / FLASK
    # ============================================================
    'quest_accept':         'ui_quest_advance',
    'quest_update':         'ui_quest_advance',
    'quest_complete':       'ui_quest_advance',
    'quest_notify':         'ui_quest_advance',     # Update #128: GoT-Sound-Replacement
    'quest_failed':         'quest_failed',
    'quest_giver_appear':   'event_quest_giver_appear',
    'quest_marker':         'quest_marker_reach',
    'quest_choice':         'quest_choice_select',
    'lore_unlock':          'quest_lore_unlock',
    'level_up':             'ui_skillpoint',
    'skill_unlocked':       'ui_skill_unlocked',
    'pickup':               'inv_drag_pickup',
    'pickup_gold':          'ui_coin_drop',
    'pickup_marke':         'pickup_marke_high',
    'pickup_marke_low':     'pickup_marke_low',
    'pickup_shard':         'ui_currency_shard',
    'pickup_orb':           'pickup_orb_regret',
    'pickup_quest':         'pickup_quest_item',
    'pickup_aithein':       'pickup_aithein_frag',
    'pickup_potion':        'pickup_potion',
    'pickup_key':           'pickup_key',
    'flask_use_hp':         'flask_health_glow',
    'flask_use_mp':         'flask_mana_glow',
    'flask_empty':          'flask_dud',

    # ============================================================
    # Update #127 — CRAFTING / SHOP / DECOR
    # ============================================================
    'altar_activate':       'cursed_altar_touch',
    'altar_bless':          'cursed_altar_blessing',
    'altar_curse':          'cursed_altar_curse',
    'rune_activate':        'rune_anchor_activate',
    'rune_inscribe':        'rune_inscribe',
    'gem_engrave':          'gem_engrave',
    'engrave_kharn':        'engrave_kharn',
    'engrave_nheyra':       'engrave_nheyra',
    'engrave_ousen':        'engrave_ousen',
    'engrave_valsa':        'engrave_valsa',
    'engrave_imnesh':       'engrave_imnesh',
    'engrave_shulavh':      'engrave_shulavh',
    'engrave_vergessen':    'engrave_vergessen',
    'pakt_activate':        'aspekt_pakt_activate',
    'pakt_choice':          'aspekt_pakt_choice',
    'pakt_kharn':           'pakt_kharn_active',
    'pakt_nheyra':          'pakt_nheyra_active',
    'pakt_ousen':           'pakt_ousen_active',
    'pakt_shulavh':         'pakt_shulavh_active',
    'pakt_imnesh':          'pakt_imnesh_active',
    'shop_buy':             'shop_buy_confirm',
    'shop_sell':            'shop_sell_confirm',
    'shop_open':            'shop_open',
    'shop_close':           'shop_close',
    'shop_no_gold':         'shop_no_gold',

    # ============================================================
    # Update #127 — DOORS / TRAPS / PORTALS
    # ============================================================
    'door_open':            'door_open_wood',
    'door_open_metal':      'door_open_metal',
    'portal_open':          'ui_portal_open',
    'portal_close':         'ui_portal_close',
    'trap_plate':           'trap_plate_click',

    # ============================================================
    # Update #127 — MISC / SYSTEM / EVENT
    # ============================================================
    'save_game':            'ui_save_game',
    'achievement':          'achievement_unlock',
    'mahnmal_activate':     'ui_mahnmal_activate',
    'critical_hp':          'ui_critical_hp',
    'low_hp':               'ui_low_hp_warning',
    'vergessens_welle':     'ui_vergessens_welle',
    'item_pickup_common':   'ui_item_pickup_common',
    'item_pickup_rare':     'ui_item_pickup_rare',
    'item_pickup_unique':   'ui_item_pickup_unique',
    'item_pickup_mythic':   'ui_item_pickup_mythic',
}


# ============================================================
# Update #X — Footstep-Picker pro Biome
# ============================================================
# Mapping biome -> footstep-SFX-ID (im sfx_registry, generiert in Phase 2).
# Engine ruft pick_footstep_for_biome(biome) und bekommt die passende
# SFX-ID zurueck, die dann via _resolve_sfx_file/play() abgespielt wird.
BIOME_FOOTSTEP = {
    'crypt':   'footstep_stone',
    'town':    'footstep_wood',
    'frost':   'footstep_stone',   # Glasgolden Ruinen
    'lava':    'footstep_ash',
    'swamp':   'footstep_roots',
    'astral':  'footstep_marble',
    'desert':  'footstep_sand',
    # Zukuenftig:
    'wound_salt':   'footstep_wet',
    'wound_ash':    'footstep_ash',
    'wound_hollow': 'footstep_void',
    'hollow_word':  'footstep_void',
}


def pick_footstep_for_biome(biome):
    """Returnt die SFX-ID des passenden Footstep-Sounds fuer ein Biome.

    Fallback: 'footstep_stone' (klingt in den meisten Dungeons ok).
    """
    return BIOME_FOOTSTEP.get(biome, 'footstep_stone')


def _resolve_sfx_file(sfx_name):
    """Sucht eine SFX-Datei `<sfx_name>.<ext>` in SOUNDS_DIR.

    Reihenfolge:
      1) SFX_FILE_ALIASES (verbose Stock-Filenames)
      2) Direkter Match in Sounds/
      3) AI-generierte SFX aus sf/sfx_registry.py (via tools/sfx_gen.py)
    Returnt absoluten Pfad oder None.
    """
    if not _os.path.isdir(SOUNDS_DIR):
        # Falls Sounds/ fehlt, trotzdem AI-Registry pruefen (anderer Pfad)
        return _resolve_from_sfx_registry(sfx_name)

    # 1) Alias-Lookup (verbose Audio-Designer-Filenames)
    aliased = SFX_FILE_ALIASES.get(sfx_name)
    if aliased is not None:
        for ext in ('.ogg', '.wav', '.mp3', '.flac'):
            cand = _os.path.join(SOUNDS_DIR, aliased + ext)
            if _os.path.exists(cand):
                return cand
    # 2) Direkter Match in Sounds/
    for ext in ('.ogg', '.wav', '.mp3', '.flac'):
        cand = _os.path.join(SOUNDS_DIR, sfx_name + ext)
        if _os.path.exists(cand):
            return cand
    # 3) AI-generierte SFX (tools/sfx_gen.py Output)
    return _resolve_from_sfx_registry(sfx_name)


def _resolve_from_sfx_registry(sfx_name):
    """Konsultiert sf/sfx_registry.py (auto-generiert von tools/sfx_gen.py).

    Reihenfolge:
      1) Direkter Match (sfx_name selbst ist im Registry)
      2) Phase-2-Hint (Engine-Call -> Velgrad-spezifische AI-SFX)

    Returnt absoluten Pfad oder None.
    """
    try:
        from sf import sfx_registry  # type: ignore
    except ImportError:
        return None
    generated = getattr(sfx_registry, 'SFX_GENERATED', {})

    rel = generated.get(sfx_name)
    # Phase-2-Hint-Indirection (z.B. play('hit') -> damage_light_cloth.mp3)
    if not rel:
        hint = SFX_PHASE2_HINTS.get(sfx_name)
        if hint:
            rel = generated.get(hint)
    if not rel:
        return None
    project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    abs_path = _os.path.join(project_root, rel.replace('/', _os.sep))
    if _os.path.exists(abs_path):
        return abs_path
    return None


def init():
    global _ENABLED
    try:
        # Falls Mixer bereits mit Defaults gestartet wurde (22050 Hz),
        # zuerst beenden, damit pre_init wirkt.
        if pygame.mixer.get_init() is not None:
            pygame.mixer.quit()
        pygame.mixer.pre_init(frequency=_RATE, size=-16,
                              channels=_CHANNELS, buffer=1024)
        pygame.mixer.init(frequency=_RATE, size=-16,
                          channels=_CHANNELS, buffer=1024)
        # Reserve channels: 0 = music, 1 = ambient, 2 = step, 3-31 = sfx pool
        # Update #46: 8 → 16 channels (Affix/AoE-Cutoffs vermeiden).
        # Update #126: 16 → 32 (User-Report „Sounds ausgelassen"). Mit 29
        # SFX-Channels + Dedup-Fenster passen jetzt selbst 5-Mob-Death-
        # Wellen + Skill-Casts simultan ohne Drop.
        pygame.mixer.set_num_channels(32)
        _ENABLED = True
    except (pygame.error, RuntimeError):
        _ENABLED = False
    return _ENABLED


# ============================================================
# ENVELOPES
# ============================================================
def _adsr(n, a=0.05, d=0.1, s=0.6, r=0.3):
    """Returnt eine Lookup-Liste mit n Werten [0..1] für ADSR-Hüllkurve."""
    out = [0.0] * n
    a_n = int(n * a); d_n = int(n * d); r_n = int(n * r)
    s_level = s
    for i in range(a_n):
        out[i] = i / max(1, a_n)
    for i in range(d_n):
        t = i / max(1, d_n)
        out[a_n + i] = 1.0 - (1.0 - s_level) * t
    sus_start = a_n + d_n
    sus_end = n - r_n
    for i in range(sus_start, sus_end):
        out[i] = s_level
    for i in range(r_n):
        t = i / max(1, r_n)
        out[sus_end + i] = s_level * (1.0 - t)
    return out


def _decay(n, exp=2.0):
    return [(1.0 - i / n) ** exp for i in range(n)]


# ============================================================
# OSCILLATORS
# ============================================================
def _osc_sine(freq, n, phase=0.0):
    out = [0.0] * n
    inc = 2 * math.pi * freq / _RATE
    for i in range(n):
        out[i] = math.sin(phase + i * inc)
    return out


def _osc_square(freq, n, duty=0.5):
    out = [0.0] * n
    period = _RATE / freq
    for i in range(n):
        p = (i % period) / period
        out[i] = 1.0 if p < duty else -1.0
    return out


def _osc_saw(freq, n):
    out = [0.0] * n
    period = _RATE / freq
    for i in range(n):
        p = (i % period) / period
        out[i] = 2.0 * p - 1.0
    return out


def _osc_triangle(freq, n):
    out = [0.0] * n
    period = _RATE / freq
    for i in range(n):
        p = (i % period) / period
        if p < 0.5:
            out[i] = 4 * p - 1
        else:
            out[i] = 3 - 4 * p
    return out


def _osc_noise(n, rng=None):
    if rng is None:
        rng = random
    return [rng.uniform(-1, 1) for _ in range(n)]


def _osc_fm(carrier_f, mod_f, mod_amp, n):
    """FM-Synthese: Träger-Frequenz wird durch Modulator beeinflusst."""
    out = [0.0] * n
    mod_inc = 2 * math.pi * mod_f / _RATE
    carrier_inc = 2 * math.pi * carrier_f / _RATE
    for i in range(n):
        mod_v = math.sin(i * mod_inc) * mod_amp
        out[i] = math.sin(i * carrier_inc + mod_v)
    return out


# ============================================================
# UTILITIES
# ============================================================
def _mix(a, b, ratio=0.5):
    """Mischt zwei Wave-Listen (gleiche Länge)."""
    n = min(len(a), len(b))
    return [a[i] * (1 - ratio) + b[i] * ratio for i in range(n)]


def _add(*waves):
    n = max(len(w) for w in waves)
    out = [0.0] * n
    for w in waves:
        for i in range(min(n, len(w))):
            out[i] += w[i]
    return out


def _apply_env(wave, env):
    n = min(len(wave), len(env))
    return [wave[i] * env[i] for i in range(n)]


def _gain(wave, g):
    return [w * g for w in wave]


def _clamp(wave):
    return [max(-1.0, min(1.0, w)) for w in wave]


def _to_pcm_mono(wave, volume=0.7):
    """Float [-1..1] → 16-bit signed PCM (Stereo wenn nötig)."""
    amp = int(32767 * volume)
    pcm = array.array('h')
    if _CHANNELS == 2:
        for v in wave:
            sample = max(-32768, min(32767, int(v * amp)))
            pcm.append(sample)
            pcm.append(sample)  # L + R
    else:
        for v in wave:
            pcm.append(max(-32768, min(32767, int(v * amp))))
    return pcm


def _to_pcm_stereo(wave_l, wave_r, volume=0.7):
    """Zwei Float-Listen → 16-bit stereo interleaved."""
    amp = int(32767 * volume)
    n = min(len(wave_l), len(wave_r))
    pcm = array.array('h')
    for i in range(n):
        pcm.append(max(-32768, min(32767, int(wave_l[i] * amp))))
        pcm.append(max(-32768, min(32767, int(wave_r[i] * amp))))
    return pcm


def _make(wave, volume=0.6, stereo_pair=None):
    if not _ENABLED:
        return None
    try:
        if stereo_pair is not None:
            pcm = _to_pcm_stereo(stereo_pair[0], stereo_pair[1], volume)
        else:
            pcm = _to_pcm_mono(wave, volume)
        return pygame.mixer.Sound(buffer=pcm)
    except Exception:
        return None


# ============================================================
# SFX DEFINITIONEN
# ============================================================
def _sfx_hit():
    # Kurzer Schlag: tiefer Body + scharfer Noise-Transient
    n = int(_RATE * 0.18)
    # Body: 80→40 Hz sweep + sine
    body = []
    for i in range(n):
        t = i / n
        f = 200 - 150 * t
        body.append(math.sin(2 * math.pi * f * i / _RATE))
    # Transient: weißes Rauschen, schnell decay
    noise = _osc_noise(int(_RATE * 0.04))
    noise_env = _decay(len(noise), exp=3.0)
    noise = _apply_env(noise, noise_env)
    # Body Envelope
    body_env = _adsr(n, a=0.01, d=0.2, s=0.3, r=0.5)
    body = _apply_env(body, body_env)
    # Layered
    out = body[:]
    for i in range(len(noise)):
        out[i] += noise[i] * 0.6
    return _clamp(out)


def _sfx_hit_heavy():
    n = int(_RATE * 0.28)
    # Sehr tiefes Boom + breiterer Noise
    body = []
    for i in range(n):
        t = i / n
        f = 90 - 50 * t
        body.append(math.sin(2 * math.pi * f * i / _RATE) * 1.2)
    noise = _osc_noise(int(_RATE * 0.08))
    noise = _apply_env(noise, _decay(len(noise), 2.5))
    env = _adsr(n, a=0.01, d=0.15, s=0.4, r=0.6)
    body = _apply_env(body, env)
    out = body[:]
    for i in range(len(noise)):
        out[i] += noise[i] * 0.5
    # Sub-Click (200Hz Transient)
    click = _osc_sine(180, int(_RATE * 0.03))
    click = _apply_env(click, _decay(len(click), 4.0))
    for i in range(len(click)):
        out[i] += click[i] * 0.4
    return _clamp(out)


def _sfx_crit():
    # Hoher metallischer Schlag + helle Glocke
    n = int(_RATE * 0.32)
    # Glocke: zwei sinus + FM
    bell = _osc_fm(1200, 600, 5.0, n)
    bell_env = _decay(n, 2.0)
    bell = _apply_env(bell, bell_env)
    # Sweep down (zischen)
    sw = []
    for i in range(n):
        t = i / n
        f = 2000 - 1500 * t
        sw.append(math.sin(2 * math.pi * f * i / _RATE))
    sw = _apply_env(sw, _decay(n, 3.0))
    # Layer
    out = [bell[i] * 0.7 + sw[i] * 0.3 for i in range(n)]
    return _clamp(out)


def _sfx_cast_fire():
    # Whoosh: rauschen + low sweep + crackle
    n = int(_RATE * 0.45)
    # Lowpass-ähnliches Rauschen
    noise = _osc_noise(n)
    # Modulieren mit langsamem Sweep
    sweep_env = []
    for i in range(n):
        t = i / n
        # Volumen ansteigend, dann abfallend
        sweep_env.append(math.sin(math.pi * t) ** 1.5)
    noise = _apply_env(noise, sweep_env)
    noise = _gain(noise, 0.5)
    # Tiefer Body
    body = []
    for i in range(n):
        t = i / n
        f = 80 + 200 * t
        body.append(math.sin(2 * math.pi * f * i / _RATE))
    body = _apply_env(body, _adsr(n, a=0.1, d=0.2, s=0.5, r=0.4))
    body = _gain(body, 0.6)
    out = [noise[i] + body[i] for i in range(n)]
    return _clamp(out)


def _sfx_cast_lightning():
    # Crackle + hoher whip-Sound
    n = int(_RATE * 0.32)
    # Crackle: schnelles Rauschen mit Amplituden-Modulation
    noise = _osc_noise(n)
    # AM (zappende Amplitude)
    for i in range(n):
        noise[i] *= 0.5 + 0.5 * math.sin(2 * math.pi * 80 * i / _RATE)
    noise = _apply_env(noise, _adsr(n, a=0.02, d=0.1, s=0.5, r=0.5))
    # Hochfreq whip
    sweep = []
    for i in range(n):
        t = i / n
        f = 3500 - 3000 * t
        sweep.append(math.sin(2 * math.pi * f * i / _RATE))
    sweep = _apply_env(sweep, _decay(n, 2.0))
    out = [noise[i] * 0.6 + sweep[i] * 0.5 for i in range(n)]
    return _clamp(out)


def _sfx_cast_heal():
    # Sanftes Glockenakkord aufsteigend (C-E-G)
    n = int(_RATE * 0.5)
    chord = _add(
        _osc_sine(523.25, n),  # C5
        _osc_sine(659.25, n),  # E5
        _osc_sine(783.99, n),  # G5
    )
    chord = _gain(chord, 0.33)
    env = _adsr(n, a=0.15, d=0.2, s=0.5, r=0.4)
    chord = _apply_env(chord, env)
    # Highlight oben: kurzer hellster Ton bei Ende
    sparkle = _osc_sine(1568, int(_RATE * 0.1))
    sparkle = _apply_env(sparkle, _decay(len(sparkle), 3.0))
    sparkle = _gain(sparkle, 0.3)
    # Bei 0.3s einsetzen
    offset = int(_RATE * 0.3)
    out = chord[:]
    for i in range(len(sparkle)):
        if offset + i < len(out):
            out[offset + i] += sparkle[i]
    return _clamp(out)


def _sfx_cast_frost():
    # Crystalliner Ton + Wind-Rauschen
    n = int(_RATE * 0.45)
    # Tonlayer: 2 sinus harmonics
    tone = _add(
        _osc_sine(880, n),
        _osc_sine(1320, n),
    )
    tone = _gain(tone, 0.4)
    tone = _apply_env(tone, _adsr(n, a=0.08, d=0.2, s=0.4, r=0.5))
    # Wind: lowpass-Rauschen, sanft ein/ausfaden
    noise = _osc_noise(n)
    wind_env = []
    for i in range(n):
        t = i / n
        wind_env.append(math.sin(math.pi * t) * 0.4)
    noise = _apply_env(noise, wind_env)
    out = [tone[i] + noise[i] for i in range(n)]
    return _clamp(out)


def _sfx_pickup_gold():
    # Zwei aufsteigende Ton-Impulse (Coin-Sound)
    n1 = int(_RATE * 0.06)
    n2 = int(_RATE * 0.10)
    pause = int(_RATE * 0.02)
    t1 = _osc_sine(880, n1)
    t1 = _apply_env(t1, _decay(n1, 1.5))
    t2 = _osc_sine(1318, n2)
    t2 = _apply_env(t2, _decay(n2, 2.0))
    out = t1 + [0.0] * pause + t2
    return _clamp(out)


def _sfx_pickup_item():
    # Sweep up + sparkle
    n = int(_RATE * 0.2)
    sw = []
    for i in range(n):
        t = i / n
        f = 600 + 600 * t
        sw.append(math.sin(2 * math.pi * f * i / _RATE))
    sw = _apply_env(sw, _decay(n, 1.5))
    # Sparkle high freq
    sparkle = _osc_sine(2200, int(_RATE * 0.08))
    sparkle = _apply_env(sparkle, _decay(len(sparkle), 2.0))
    sparkle = _gain(sparkle, 0.4)
    offset = int(_RATE * 0.08)
    out = sw[:]
    for i in range(len(sparkle)):
        if offset + i < len(out):
            out[offset + i] += sparkle[i]
    return _clamp(out)


def _sfx_levelup():
    # Aufsteigender Akkord: C-E-G-C (1.2s)
    n_note = int(_RATE * 0.2)
    notes = [261.63, 329.63, 392.00, 523.25]  # C4 E4 G4 C5
    out = []
    for f in notes:
        t = _osc_sine(f, n_note)
        # Doppel-Oktave für reicheren Sound
        t = _add(t, _gain(_osc_sine(f * 2, n_note), 0.4))
        t = _apply_env(t, _adsr(n_note, a=0.05, d=0.15, s=0.6, r=0.2))
        out.extend(t)
    # Letzter Akkord länger gehalten
    fin_n = int(_RATE * 0.4)
    chord = _add(
        _osc_sine(523.25, fin_n),
        _osc_sine(659.25, fin_n),
        _osc_sine(783.99, fin_n),
        _osc_sine(1046.5, fin_n),
    )
    chord = _gain(chord, 0.25)
    chord = _apply_env(chord, _adsr(fin_n, a=0.02, d=0.1, s=0.7, r=0.5))
    out.extend(chord)
    return _clamp(out)


def _sfx_boss_intro():
    # Tiefer Drone + ansteigender Sub-Bass
    n = int(_RATE * 1.0)
    sub = []
    for i in range(n):
        t = i / n
        f = 55 + 25 * t
        sub.append(math.sin(2 * math.pi * f * i / _RATE) * 1.2)
    sub = _apply_env(sub, _adsr(n, a=0.05, d=0.2, s=0.7, r=0.3))
    # Drone (FM)
    drone = _osc_fm(110, 27, 3.0, n)
    drone = _gain(drone, 0.4)
    drone = _apply_env(drone, _adsr(n, a=0.1, d=0.2, s=0.6, r=0.3))
    # Noise rumble
    noise = _osc_noise(n)
    noise = _gain(noise, 0.2)
    noise = _apply_env(noise, _decay(n, 0.8))
    out = [sub[i] + drone[i] + noise[i] for i in range(n)]
    return _clamp(out)


def _sfx_death():
    # Absteigender Pitch + Rauschen
    n = int(_RATE * 0.5)
    sw = []
    for i in range(n):
        t = i / n
        f = 440 - 380 * t
        sw.append(math.sin(2 * math.pi * f * i / _RATE))
    sw = _apply_env(sw, _decay(n, 1.5))
    noise = _osc_noise(n)
    noise = _apply_env(noise, _decay(n, 2.0))
    noise = _gain(noise, 0.3)
    out = [sw[i] + noise[i] for i in range(n)]
    return _clamp(out)


def _sfx_damage():
    # Kurzer scharfer Hit + tiefer Body
    n = int(_RATE * 0.18)
    noise = _osc_noise(n)
    noise = _apply_env(noise, _decay(n, 2.0))
    body = []
    for i in range(n):
        t = i / n
        f = 150 - 100 * t
        body.append(math.sin(2 * math.pi * f * i / _RATE))
    body = _apply_env(body, _adsr(n, a=0.01, d=0.15, s=0.4, r=0.5))
    out = [noise[i] * 0.5 + body[i] * 0.7 for i in range(n)]
    return _clamp(out)


def _sfx_dodge():
    # Schneller Whoosh
    n = int(_RATE * 0.12)
    noise = _osc_noise(n)
    # Bandpass-ähnliches Filter (durch Amplituden-Modulation)
    for i in range(n):
        t = i / n
        noise[i] *= math.sin(math.pi * t) ** 1.5
    return _clamp(_gain(noise, 0.7))


def _sfx_click():
    n = int(_RATE * 0.05)
    sw = []
    for i in range(n):
        t = i / n
        f = 1800 + 600 * t
        sw.append(math.sin(2 * math.pi * f * i / _RATE))
    sw = _apply_env(sw, _decay(n, 3.0))
    return _clamp(_gain(sw, 0.5))


def _sfx_step(biome):
    """Schritt-Sound je Biom (Stein/Schnee/Lava).

    N-11 (Update #52): Auch material-spezifische Varianten:
    `water` (Salzpfütze/Pfütze), `metal` (Eisen-Boden), `wood`
    (Pier/Wirtshaus), `mud` (Sumpf-Pfütze).
    """
    n = int(_RATE * 0.08)
    noise = _osc_noise(n)
    noise = _apply_env(noise, _decay(n, 3.0))
    if biome == 'frost':
        # Knirschiger Schnee-Sound
        noise = _gain(noise, 0.4)
        return _clamp(noise)
    elif biome == 'lava':
        # Crackle
        noise = _gain(noise, 0.5)
        return _clamp(noise)
    elif biome == 'town':
        # Holz-Klopf
        body = _osc_sine(180, n)
        body = _apply_env(body, _decay(n, 3.0))
        out = [noise[i] * 0.3 + body[i] * 0.4 for i in range(n)]
        return _clamp(out)
    elif biome == 'water':
        # Splash: lange Noise + Mid-Frequenz-Body
        nw = int(_RATE * 0.12)
        wet = _osc_noise(nw)
        wet = _apply_env(wet, _decay(nw, 2.0))
        body = _osc_sine(95, nw)
        body = _apply_env(body, _decay(nw, 1.5))
        out = [wet[i] * 0.55 + body[i] * 0.25 for i in range(nw)]
        return _clamp(out)
    elif biome == 'metal':
        # Click + Ring (kurzer hoher Ton)
        body = _osc_sine(420, n)
        body = _apply_env(body, _decay(n, 5.0))
        out = [noise[i] * 0.2 + body[i] * 0.55 for i in range(n)]
        return _clamp(out)
    elif biome == 'wood':
        # Holz wie town aber dunkler
        body = _osc_sine(140, n)
        body = _apply_env(body, _decay(n, 3.5))
        out = [noise[i] * 0.35 + body[i] * 0.45 for i in range(n)]
        return _clamp(out)
    elif biome == 'mud':
        # Sumpfiger Squelch: tiefe Frequenz + langes Decay
        nm = int(_RATE * 0.14)
        wet = _osc_noise(nm)
        wet = _apply_env(wet, _decay(nm, 1.8))
        body = _osc_sine(70, nm)
        body = _apply_env(body, _decay(nm, 1.2))
        out = [wet[i] * 0.4 + body[i] * 0.45 for i in range(nm)]
        return _clamp(out)
    else:
        # Stein-Schritt
        body = _osc_sine(120, n)
        body = _apply_env(body, _decay(n, 3.0))
        out = [noise[i] * 0.3 + body[i] * 0.4 for i in range(n)]
        return _clamp(out)


def _sfx_loot_beam():
    """Sanftes Glimmer für Loot-Beam."""
    n = int(_RATE * 0.5)
    tones = _add(
        _osc_sine(1568, n),  # G6
        _osc_sine(2093, n),  # C7
    )
    tones = _gain(tones, 0.3)
    tones = _apply_env(tones, _decay(n, 2.0))
    return _clamp(tones)


def _sfx_boss_shield():
    """Crystalliner Klink-Sound für Boss-Schild."""
    n = int(_RATE * 0.4)
    bell = _osc_fm(440, 220, 4.0, n)
    bell = _apply_env(bell, _decay(n, 1.5))
    return _clamp(_gain(bell, 0.4))


def _sfx_thunder():
    """Tiefer Donner mit lautem Knall + Rumble."""
    n = int(_RATE * 1.4)
    out = []
    # Sharp transient (Knall)
    transient_n = int(_RATE * 0.05)
    transient = _osc_noise(transient_n)
    transient = _apply_env(transient, _decay(transient_n, 1.5))
    transient = _gain(transient, 0.8)
    # Tiefer Rumble
    rumble = []
    for i in range(n):
        t = i / n
        f = 40 + 20 * math.sin(2 * math.pi * 3 * t)
        rumble.append(math.sin(2 * math.pi * f * i / _RATE) * 0.7)
    rumble = _apply_env(rumble, _adsr(n, a=0.02, d=0.3, s=0.5, r=0.5))
    # Mid-Layer Noise (Donner-Hall)
    mid = _osc_noise(n)
    mid_env = _decay(n, 1.0)
    for i in range(n):
        mid[i] *= mid_env[i] * 0.3
    for i in range(transient_n):
        out.append(transient[i] + rumble[i] + mid[i])
    for i in range(transient_n, n):
        out.append(rumble[i] + mid[i])
    return _clamp(out)


def _sfx_roar():
    """Generischer Boss-Roar (tief + lang)."""
    n = int(_RATE * 1.5)
    out = []
    for i in range(n):
        t = i / n
        f = 70 + 50 * math.sin(2 * math.pi * 2 * t)
        env = math.sin(math.pi * t) ** 0.8
        out.append(math.sin(2 * math.pi * f * i / _RATE) * env * 1.2)
    noise = _osc_noise(n)
    for i in range(n):
        noise[i] *= math.sin(math.pi * (i / n)) ** 1.5 * 0.4
    out = [out[i] + noise[i] for i in range(n)]
    return _clamp(out)


def _sfx_combo():
    """Aufsteigender Glockenton für Combo-Trigger."""
    n = int(_RATE * 0.25)
    tones = _add(
        _osc_sine(880, n),
        _osc_sine(1320, n),
    )
    tones = _gain(tones, 0.3)
    tones = _apply_env(tones, _decay(n, 2.0))
    return _clamp(tones)


def _sfx_aoe_windup():
    """Tieffrequenter Warn-Brumm für AoE-Telegraphs (Briefing C.3.2 / C-06).

    ~0.8s, baut langsam Lautstärke auf, Sub-Bass-Sinus mit Tremolo,
    leichte Rausch-Schicht. Bewusst nicht melodisch — soll als Warnsignal
    funktionieren, auch wenn Partikel die Decal verdecken.
    """
    n = int(_RATE * 0.8)
    out = []
    for i in range(n):
        t = i / n
        # Tieftöner: zwischen 48 und 62 Hz schwebend
        f_base = 48 + 14 * math.sin(2 * math.pi * 1.2 * t)
        # Tremolo (~7 Hz) — typisches Bedrohungs-Signal
        tremolo = 0.75 + 0.25 * math.sin(2 * math.pi * 7 * t)
        # Rise-Envelope: leise → laut über die ganze Dauer
        rise = t ** 1.4
        out.append(math.sin(2 * math.pi * f_base * i / _RATE)
                   * tremolo * rise * 0.85)
    # Sub-Bass-Layer eine Oktave tiefer als „Druck"
    sub = []
    for i in range(n):
        t = i / n
        sub.append(math.sin(2 * math.pi * 30 * i / _RATE) * (t ** 1.6) * 0.4)
    # Leichtes pinkes Rauschen, gedämpft
    noise = _osc_noise(n)
    for i in range(n):
        out[i] += sub[i] + noise[i] * (i / n) * 0.08
    return _clamp(out)


def _sfx_quest_accept():
    """Pergament + leiser Glocken-Ping (Audio-Bibel 6.5).

    Velgrad-Lore: Quest = Vertrag/Pakt → klingt nach Tinte und Glocke.
    """
    n = int(_RATE * 0.45)
    out = [0.0] * n
    # Pergament-Rascheln via Noise
    noise = _osc_noise(int(_RATE * 0.25))
    for i, v in enumerate(noise):
        out[i] += v * (1.0 - i / len(noise)) * 0.25
    # Glocken-Ping (hoher Sinus mit Decay)
    bell_n = int(_RATE * 0.35)
    for i in range(bell_n):
        t = i / bell_n
        out[i + int(_RATE * 0.1)] += (
            math.sin(2 * math.pi * 1320 * i / _RATE) * (1.0 - t) ** 2.5 * 0.35)
    return _clamp(out)


def _sfx_quest_update():
    """Stage-Progress: kurzer doppelter Glocken-Ping."""
    n = int(_RATE * 0.5)
    out = [0.0] * n
    for offset_s in (0.0, 0.18):
        off = int(_RATE * offset_s)
        sub_n = int(_RATE * 0.25)
        for i in range(sub_n):
            t = i / sub_n
            if off + i < n:
                out[off + i] += (math.sin(2 * math.pi * 1760 * i / _RATE)
                                 * (1.0 - t) ** 2.0 * 0.30)
    return _clamp(out)


def _sfx_quest_complete():
    """Choir-Wave + Sub-Bass-Drop (Audio-Bibel 6.5 Unique-Item-Stinger).

    Velgrad-Lore: Quest fertig = Pakt erfüllt → großer Moment.
    """
    n = int(_RATE * 1.3)
    out = [0.0] * n
    # Sub-Bass-Drop
    for i in range(n):
        t = i / n
        f = 65 - 20 * t  # fällt von 65 auf 45 Hz
        out[i] += math.sin(2 * math.pi * f * i / _RATE) * (1.0 - t) * 0.45
    # Choir-Layer (mehrere harmonische Sinus)
    for freq, vol_l in ((220, 0.18), (330, 0.14), (440, 0.10), (660, 0.06)):
        for i in range(n):
            t = i / n
            env = math.sin(math.pi * t) ** 0.7
            out[i] += math.sin(2 * math.pi * freq * i / _RATE) * env * vol_l
    # Glas-Klingel im Tail
    bell_start = int(_RATE * 0.7)
    bell_n = n - bell_start
    for i in range(bell_n):
        t = i / bell_n
        out[bell_start + i] += (math.sin(2 * math.pi * 2200 * i / _RATE)
                                * (1.0 - t) ** 2.5 * 0.12)
    return _clamp(out)


def _sfx_boss_bong():
    """Tubular-Bell-Bong für Boss-Health-Bar-Erscheinen (Audio-Bibel 6.7).

    Tief, reverberant, „großer Moment". Klingt nicht wie Hollywood-Braam,
    sondern wie eine Klangschale in einer Steinhalle.
    """
    n = int(_RATE * 1.4)
    out = [0.0] * n
    # Fundamental + zwei höhere Partials (Bell-Spektrum)
    for f, vol_layer in ((52, 0.85), (104, 0.45), (208, 0.18), (312, 0.12)):
        for i in range(n):
            phase = 2 * math.pi * f * i / _RATE
            out[i] += math.sin(phase) * vol_layer
    # Decay-Envelope (1.4 s langer exponentieller Ausklang)
    decay_env = _decay(n, 1.6)
    for i in range(n):
        out[i] *= decay_env[i]
    # Mini-Tail mit Hochfrequenz-Noise (Glas-Anteil, Audio-Bibel 6.7)
    noise = _osc_noise(int(_RATE * 0.3))
    for i, v in enumerate(noise):
        out[i] += v * (1.0 - i / len(noise)) * 0.08
    return _clamp(out)


def _sfx_aoe_impact():
    """Kurzer Impact-Cue, wenn der AoE-Telegraph aktiviert (Briefing C-06)."""
    n = int(_RATE * 0.35)
    # Sub-Punch (40 Hz, sehr kurz)
    punch = []
    for i in range(n):
        t = i / n
        punch.append(math.sin(2 * math.pi * 42 * i / _RATE)
                     * (1.0 - t) ** 1.8 * 0.9)
    # Mid-Burst (250 Hz Sägezahn-Annäherung via Noise+Sine)
    mid = _osc_noise(n)
    for i in range(n):
        t = i / n
        mid[i] = mid[i] * (1.0 - t) ** 2.2 * 0.5
    return _clamp([punch[i] + mid[i] for i in range(n)])


# ============================================================
# AMBIENT-SOUNDS (düster, biom-spezifisch)
# ============================================================
def _amb_drip():
    """Wasser-Tropfen mit Reverb-artigem Schwanz."""
    n = int(_RATE * 0.5)
    out = [0.0] * n
    # Sharp transient (drop hits water)
    transient = _osc_sine(2200, int(_RATE * 0.03))
    transient = _apply_env(transient, _decay(len(transient), 3.0))
    # Tieferes Echo
    echo = _osc_sine(440, int(_RATE * 0.35))
    echo = _apply_env(echo, _decay(len(echo), 1.5))
    for i, v in enumerate(transient):
        out[i] += v * 0.6
    for i, v in enumerate(echo):
        if int(_RATE * 0.05) + i < n:
            out[int(_RATE * 0.05) + i] += v * 0.3
    return _clamp(out)


def _amb_wind():
    """Wind-Heulen (rauschen mit langem Sweep)."""
    n = int(_RATE * 1.8)
    noise = _osc_noise(n)
    # Filtere mit langsamer AM (Wind-Pumping)
    for i in range(n):
        t = i / n
        env = math.sin(math.pi * t) * 0.6
        # Niedere Frequenz für Wind-Tonalität
        am = 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * i / _RATE)
        noise[i] *= env * am
    return _clamp(_gain(noise, 0.45))


def _amb_lava():
    """Bubble + Crackle für Lava."""
    n = int(_RATE * 0.6)
    # Tiefer Bubble (Sub-Bass mit FM)
    bubble = _osc_fm(80, 40, 4.0, n)
    bubble = _apply_env(bubble, _adsr(n, a=0.1, d=0.2, s=0.5, r=0.4))
    bubble = _gain(bubble, 0.45)
    # Crackle-Layer
    crackle = _osc_noise(n)
    for i in range(n):
        crackle[i] *= 0.3 + 0.5 * abs(math.sin(2 * math.pi * 40 * i / _RATE))
    crackle = _apply_env(crackle, _decay(n, 2.0))
    crackle = _gain(crackle, 0.25)
    out = [bubble[i] + crackle[i] for i in range(n)]
    return _clamp(out)


def _amb_chime():
    """Mystisches Glockenspiel (3 zufällige Glockentöne)."""
    rng = random.Random()
    n = int(_RATE * 1.5)
    out = [0.0] * n
    notes = rng.sample([440, 554, 659, 740, 880, 988, 1175], 3)
    offset = 0
    for f in notes:
        seg = _osc_fm(f, f * 0.7, 3.0, int(_RATE * 0.5))
        seg = _apply_env(seg, _decay(len(seg), 1.5))
        seg = _gain(seg, 0.3)
        for i, v in enumerate(seg):
            if offset + i < n:
                out[offset + i] += v
        offset += int(_RATE * 0.18)
    return _clamp(out)


def _amb_whisper():
    """Geisterhaftes Wispern (gefiltertes Rauschen mit Formant)."""
    n = int(_RATE * 1.3)
    noise = _osc_noise(n)
    # Formant-Filter: simuliere durch Modulation mit Sprach-Frequenz
    for i in range(n):
        t = i / n
        # Slow envelope (fade in/out)
        env = math.sin(math.pi * t) ** 1.2 * 0.4
        # Modulation mit 'Vokal'-Frequenz ~200Hz
        mod = 0.5 + 0.5 * math.sin(2 * math.pi * 200 * i / _RATE)
        noise[i] *= env * mod
    # Layer tiefen Drone drunter
    drone = _osc_sine(120, n)
    drone = _gain(drone, 0.1)
    out = [noise[i] + drone[i] for i in range(n)]
    return _clamp(_gain(out, 0.5))


def _amb_creak():
    """Holz/Tür-Knarren."""
    n = int(_RATE * 0.7)
    out = []
    for i in range(n):
        t = i / n
        # Aufsteigende Frequenz mit kleinen Jitter
        f = 80 + 60 * t + math.sin(2 * math.pi * 8 * i / _RATE) * 5
        out.append(math.sin(2 * math.pi * f * i / _RATE))
    out = _apply_env(out, _adsr(n, a=0.1, d=0.3, s=0.4, r=0.5))
    return _clamp(_gain(out, 0.35))


def _amb_growl():
    """Ferne Bestie (tiefes Grollen mit Modulation)."""
    n = int(_RATE * 1.4)
    out = []
    for i in range(n):
        t = i / n
        f = 60 + 30 * math.sin(2 * math.pi * 1.5 * t)
        env = math.sin(math.pi * t) ** 1.5
        out.append(math.sin(2 * math.pi * f * i / _RATE) * env)
    # Noise-Layer (Atem)
    noise = _osc_noise(n)
    for i in range(n):
        noise[i] *= 0.2 * math.sin(math.pi * (i / n))
    out = [out[i] + noise[i] for i in range(n)]
    return _clamp(_gain(out, 0.55))


def _amb_sand():
    """Sand-Wisch (gefiltertes Rauschen)."""
    n = int(_RATE * 1.2)
    noise = _osc_noise(n)
    for i in range(n):
        t = i / n
        env = math.sin(math.pi * t) ** 1.2
        noise[i] *= env * 0.5
    return _clamp(_gain(noise, 0.45))


def _amb_croak():
    """Frosch-Quaken (kurzer rhythmischer Burst)."""
    n = int(_RATE * 0.4)
    out = []
    for i in range(n):
        t = i / n
        # Frequenz-Wobble
        f = 150 + 80 * math.sin(2 * math.pi * 30 * t)
        out.append(math.sin(2 * math.pi * f * i / _RATE))
    out = _apply_env(out, _adsr(n, a=0.02, d=0.1, s=0.5, r=0.3))
    return _clamp(_gain(out, 0.4))


def _amb_seagull_cry():
    """W-12 (Update #48): Möwenschrei für Brassweir-Hafen.

    Audio-Bibel 7.7: „Möwen über halb-versunkenem Pier".
    Zwei kurze, ansteigende Cries (~0.6 s).
    """
    n = int(_RATE * 0.6)
    out = [0.0] * n
    for burst_start, burst_len_s in ((0.0, 0.18), (0.3, 0.22)):
        bs = int(_RATE * burst_start)
        bl = int(_RATE * burst_len_s)
        for i in range(bl):
            if bs + i >= n:
                break
            t = i / bl
            # Ansteigende Pitch (Möwenschrei-Charakteristik)
            f = 900 + 800 * t
            v = math.sin(2 * math.pi * f * i / _RATE)
            # Krächz-Modulation
            v *= 0.6 + 0.4 * math.sin(2 * math.pi * 50 * t)
            out[bs + i] += v
    out = _apply_env(out, _adsr(n, a=0.02, d=0.1, s=0.5, r=0.4))
    return _clamp(_gain(out, 0.35))


def _amb_wave_crash():
    """W-12 (Update #48): Wellenbrechen an Brassweir-Pier.

    Audio-Bibel 7.7: „Wellen, die ans Holz schlagen — der Ozean drückt
    gegen das Vergessen."  Filtered noise mit langem Decay.
    """
    n = int(_RATE * 1.8)
    out = []
    state = 0.0
    for i in range(n):
        # Pink-noise-ish (Smoothed white noise)
        white = random.uniform(-1, 1)
        state = state * 0.85 + white * 0.15
        out.append(state)
    # Schwellender Lautstärke-Verlauf (crash + retreat)
    env = []
    for i in range(n):
        t = i / n
        # Steile Attack, weicher Decay
        if t < 0.15:
            env.append(t / 0.15)
        else:
            env.append(max(0.0, 1.0 - (t - 0.15) / 0.85) ** 1.6)
    out = [out[i] * env[i] for i in range(n)]
    return _clamp(_gain(out, 0.45))


def _amb_oar_creak():
    """W-12 (Update #48): Ruder-Knarzen am Pier.

    Audio-Bibel 7.7: „Salzpfützen knirschen, Ruder-Knarzen".
    Tieffrequenter Knarz-Sound (Bootsholz unter Bewegung).
    """
    n = int(_RATE * 0.9)
    out = []
    for i in range(n):
        t = i / n
        # Vibrato-Knarzen: tiefe Sinus + Reibungs-Modulation
        f = 70 + 30 * math.sin(2 * math.pi * 1.2 * t)
        v = math.sin(2 * math.pi * f * i / _RATE)
        # Reibungs-Layer
        v += 0.4 * math.sin(2 * math.pi * 180 * t) * (1.0 - t)
        out.append(v)
    out = _apply_env(out, _adsr(n, a=0.15, d=0.2, s=0.4, r=0.4))
    return _clamp(_gain(out, 0.38))


def _amb_heartbeat():
    """Herzschlag (boss-Ambient)."""
    n = int(_RATE * 1.6)
    out = [0.0] * n
    # Zwei Schläge pro Sekunde (lub-dub)
    beat_len = int(_RATE * 0.12)
    for offset in (int(_RATE * 0.05), int(_RATE * 0.2),
                   int(_RATE * 0.85), int(_RATE * 1.0)):
        beat = _osc_sine(55, beat_len)
        beat = _apply_env(beat, _decay(beat_len, 4.0))
        beat = _gain(beat, 0.6)
        for i, v in enumerate(beat):
            if offset + i < n:
                out[offset + i] += v
    return _clamp(out)


_AMBIENT_BUILDERS = {
    'drip':         (_amb_drip,         0.40),
    'wind':         (_amb_wind,         0.45),
    'lava':         (_amb_lava,         0.55),
    'chime':        (_amb_chime,        0.45),
    'whisper':      (_amb_whisper,      0.40),
    'creak':        (_amb_creak,        0.40),
    'growl':        (_amb_growl,        0.50),
    'sand':         (_amb_sand,         0.40),
    'croak':        (_amb_croak,        0.40),
    'heartbeat':    (_amb_heartbeat,    0.55),
    # W-12 (Update #48): Brassweir-Hafen-Ambience (Audio-Bibel 7.7)
    'seagull_cry':  (_amb_seagull_cry,  0.30),
    'wave_crash':   (_amb_wave_crash,   0.40),
    'oar_creak':    (_amb_oar_creak,    0.35),
}


def _ensure_ambient(name):
    if not _ENABLED:
        return None
    if name in _SOUND_CACHE:
        return _SOUND_CACHE[name]
    # Update #27: File-First für ambient — `ambient_fire_loop` etc.
    sfx_path = _resolve_sfx_file(name)
    if sfx_path is not None:
        try:
            snd = pygame.mixer.Sound(sfx_path)
            _SOUND_CACHE[name] = snd
            return snd
        except pygame.error:
            pass
    builder = _AMBIENT_BUILDERS.get(name)
    if builder is None:
        _SOUND_CACHE[name] = None
        return None
    fn, vol = builder
    snd = _make(fn(), volume=vol)
    _SOUND_CACHE[name] = snd
    return snd


def play_step(name, volume=1.0):
    """Spielt einen Movement/Step-Sound auf reserviertem Step-Channel 2.

    Update #32: Dedizierter Channel sorgt dafür, dass nur EIN Schritt
    gleichzeitig aktiv ist. Sobald der Spieler stehen bleibt und
    `play_step` nicht mehr aufgerufen wird, endet der Sound nach max
    seiner eigenen Dauer (Procedural-Synth = 80ms). Wenn ein Datei-
    Override hier länger ist (z.B. 2s) → der nächste Step-Trigger
    stoppt ihn sofort.
    """
    if not _ENABLED:
        return
    snd = _ensure(name)
    if snd is None:
        return
    try:
        ch = pygame.mixer.Channel(2)
        ch.stop()  # vorherigen Step ALWAYS abbrechen
        ch.play(snd)
        ch.set_volume(effective_volume('sfx', volume))
    except Exception:
        pass


def stop_step():
    """Stoppt den Step-Channel sofort (wenn Spieler stehen bleibt)."""
    if not _ENABLED:
        return
    try:
        pygame.mixer.Channel(2).stop()
    except Exception:
        pass


def play_ambient(name, volume=1.0):
    """Spielt einen Ambient-Sound auf reserviertem Kanal 1.

    Update #43: Feuer-Loops sind deutlich leiser (User-Feedback „Feuer
    Geräusche sind scheiße und zu laut und zu lange").  Long-Tracks
    (`ambient_fire_loop` ist ein 5-Minuten-Loop) bekommen einen harten
    Volume-Cap von 0.25 und werden vom `_update_ambient`-Tracker später
    nach max 25 s abgebrochen.
    """
    if not _ENABLED:
        return
    snd = _ensure_ambient(name)
    if snd is None:
        return
    try:
        ch = pygame.mixer.Channel(1)
        if not ch.get_busy():
            # Spezielle Lautstärken-Caps für problematische Tracks
            if name in ('ambient_fire_loop', 'firewood_burning'):
                eff_vol = 0.20 * volume
            else:
                eff_vol = 0.5 * volume
            ch.play(snd)
            ch.set_volume(eff_vol)
    except Exception:
        pass


def stop_ambient():
    if not _ENABLED:
        return
    try:
        pygame.mixer.Channel(1).stop()
    except Exception:
        pass


# Pro Biom: Liste von Ambient-Sounds, die zufällig getriggert werden
# Update #27: Lava-Biome kann jetzt echte Fire-Loops nutzen
# (shut_up_ghost-Pack) statt nur procedural-Synth.
BIOME_AMBIENT_POOL = {
    # N-10 (Update #61): Environmental Layered Ambience — Pools haben jetzt
    # 8-10 Einträge mit Lore-spezifischer Variation pro Biome statt 4-6.
    # Wiederholungen sind Wahrscheinlichkeitsgewichte (z. B. wave_crash×3
    # = dreifach so wahrscheinlich gepickt).  Trotzdem nur 1 Track auf
    # Channel 1 gleichzeitig (Update #38-Dedup).
    # Lore-Bibel + Audio-Bibel 7.7 (Region-Ambience):
    #   - crypt   = Marrowport, Höhlen-Cave-Atmo + Salz-Drip + Salzgekreuzte-Growl
    #   - frost   = 412-Senatoren-Halle, kalter Wind durch Glasgolden-Säulen
    #   - lava    = Aschenfelder, knisterndes Holz + Lava + Risse
    #   - desert  = Zhar-Eth, Wind + Sandverwehung + ferne Chime-Schalen
    #   - swamp   = Wurzelgrab, Drip + Croak + Knochen-Whisper
    #   - astral  = Spiegelhof, Chime + multiple Whisper (Echo-Schichten)
    #   - town    = Brassweir-Pier, Welle + Möwe + Knarzen
    'crypt':  ['cave_monster', 'drip', 'drip', 'drip', 'whisper',
                'creak', 'creak', 'whisper', 'ambient_monster_growl'],
    'frost':  ['wind', 'wind', 'wind', 'chime', 'creak', 'whisper',
                'whisper', 'creak', 'chime'],
    'lava':   ['firewood_burning', 'lava', 'lava', 'lava', 'lava',
                'creak', 'creak', 'whisper', 'firewood_burning'],
    'desert': ['wind', 'wind', 'sand', 'sand', 'whisper', 'chime',
                'whisper', 'wind', 'chime'],
    'swamp':  ['drip', 'drip', 'croak', 'croak', 'whisper', 'creak',
                'drip', 'croak', 'whisper'],
    'astral': ['chime', 'whisper', 'chime', 'chime', 'whisper',
                'whisper', 'chime', 'whisper', 'chime'],
    'town':   ['wave_crash', 'wave_crash', 'wave_crash', 'seagull_cry',
                'wind', 'creak', 'oar_creak', 'drip', 'wave_crash',
                'oar_creak'],
}


_SFX_BUILDERS = {
    'hit':        (_sfx_hit, 0.35),
    'hit_heavy':  (_sfx_hit_heavy, 0.45),
    'crit':       (_sfx_crit, 0.45),
    'cast_fire':  (_sfx_cast_fire, 0.40),
    'cast_lightning': (_sfx_cast_lightning, 0.40),
    'cast_heal':  (_sfx_cast_heal, 0.45),
    'cast_frost': (_sfx_cast_frost, 0.40),
    'pickup_gold':(_sfx_pickup_gold, 0.50),
    'pickup_item':(_sfx_pickup_item, 0.55),
    'levelup':    (_sfx_levelup, 0.55),
    'boss_intro': (_sfx_boss_intro, 0.65),
    'death':      (_sfx_death, 0.45),
    'damage':     (_sfx_damage, 0.50),
    'dodge':      (_sfx_dodge, 0.40),
    'click':      (_sfx_click, 0.35),
    'loot_beam':  (_sfx_loot_beam, 0.40),
    'boss_shield':(_sfx_boss_shield, 0.50),
    'combo':      (_sfx_combo, 0.40),
    'step_crypt': (lambda: _sfx_step('crypt'), 0.20),
    'step_frost': (lambda: _sfx_step('frost'), 0.20),
    'step_lava':  (lambda: _sfx_step('lava'), 0.20),
    'step_town':  (lambda: _sfx_step('town'), 0.20),
    # N-11 (Update #52): Material-spezifische Steps
    'step_water': (lambda: _sfx_step('water'), 0.22),
    'step_metal': (lambda: _sfx_step('metal'), 0.22),
    'step_wood':  (lambda: _sfx_step('wood'),  0.20),
    'step_mud':   (lambda: _sfx_step('mud'),   0.22),
    'thunder':    (_sfx_thunder, 0.65),
    'roar':       (_sfx_roar, 0.60),
    # AoE-Telegraph (C-06)
    'aoe_windup': (_sfx_aoe_windup, 0.45),
    'aoe_impact': (_sfx_aoe_impact, 0.55),
    # Boss-Health-Bar erscheint (Audio-Bibel 6.7)
    'boss_bong':  (_sfx_boss_bong, 0.70),
    # Quest-Sounds (Audio-Bibel 6.5)
    'quest_accept':   (_sfx_quest_accept, 0.55),
    'quest_update':   (_sfx_quest_update, 0.50),
    'quest_complete': (_sfx_quest_complete, 0.75),
}


def _ensure(name):
    if not _ENABLED:
        return None
    if name in _SOUND_CACHE:
        return _SOUND_CACHE[name]
    # 1) Datei-Fallback aus Sounds/ — Designer kann Procedural per Datei
    #    überschreiben, einfach z.B. `aoe_windup.wav` ablegen.
    sfx_path = _resolve_sfx_file(name)
    if sfx_path is not None:
        try:
            snd = pygame.mixer.Sound(sfx_path)
            _SOUND_CACHE[name] = snd
            return snd
        except pygame.error:
            pass  # auf procedural fallen lassen
    # 2) Procedural-Synth-Builder
    builder = _SFX_BUILDERS.get(name)
    if builder is None:
        _SOUND_CACHE[name] = None
        return None
    fn, vol = builder
    snd = _make(fn(), volume=vol)
    _SOUND_CACHE[name] = snd
    return snd


def play(name, volume=1.0, bus='sfx'):
    """Spielt einen SFX über den angegebenen Bus.

    bus = 'sfx' | 'voice' | 'ui' | 'ambient' — wird zur Snapshot-Berechnung
    verwendet (Audio-Bibel Teil 1.2 / 1.4).

    Update #126: Drei Reliability-Mechaniken:
      - Dedup-Window 40 ms verhindert Stacking identischer Sounds.
      - Forcierte Channel-Allokation aus dem SFX-Pool (3..31), nie Music/
        Ambient/Step überschrieben — verhindert silent drops.
      - Per-Sound Volume-Cap dämpft inherent laute Builds.

    Returnt True wenn ein Sound erfolgreich gespielt wurde, False wenn der
    Name unbekannt ist ODER der Mixer disabled ODER der Sound durch Dedup
    übersprungen wurde.
    """
    if not _ENABLED:
        return False
    snd = _ensure(name)
    if snd is None:
        return False
    # Update #126: Dedup — identische Sounds nicht innerhalb 40 ms doppelt
    if not _check_dedup(name):
        return False
    # Update #126: explizite SFX-Channel-Allokation (force-replace bei voll)
    ch = _alloc_sfx_channel()
    if ch is None:
        # Fallback: pygame's auto-channel-selection (kann None returnen)
        try:
            ch = snd.play()
            if ch is None:
                return False
        except Exception:
            return False
    else:
        try:
            ch.play(snd)
        except Exception:
            return False
    try:
        capped_vol = _apply_volume_cap(name, volume)
        ch.set_volume(effective_volume(bus, capped_vol))
        return True
    except Exception:
        return False


def play_file(abs_path, volume=1.0, bus='voice', voice_channel=None):
    """Spielt eine Audio-Datei von einem absoluten Pfad direkt.

    Update #129: bei `bus='voice'` wird ein expliziter Voice-Channel
    (30=dialog, 31=combat) benutzt — kein SFX kann eine laufende
    Voice mehr überschreiben.

    `voice_channel` Override (z.B. _VOICE_CHANNEL_DIALOG /
    _VOICE_CHANNEL_COMBAT).  Default für bus='voice' = DIALOG.
    """
    if not _ENABLED:
        return False
    try:
        snd = pygame.mixer.Sound(abs_path)
    except Exception:
        return False
    try:
        if bus == 'voice':
            ch_idx = voice_channel if voice_channel is not None \
                else _VOICE_CHANNEL_DIALOG
            try:
                ch = pygame.mixer.Channel(ch_idx)
            except (pygame.error, AttributeError):
                return False
            # Dialog (Channel 30): wenn busy → skip, laufende Line zuende
            # Combat (Channel 31): wenn busy → ersetzen
            if ch_idx == _VOICE_CHANNEL_DIALOG and ch.get_busy():
                return False
            ch.play(snd)
            ch.set_volume(effective_volume(bus, volume))
            return True
        # Nicht-voice Bus: ad-hoc Channel (Legacy-Verhalten)
        ch = snd.play()
        if ch is not None:
            ch.set_volume(effective_volume(bus, volume))
            return True
    except Exception:
        pass
    return False


def play_voice(npc_key, category, volume=0.85):
    """Update #127 / #129: Spielt eine zufällige Voice-Line.

    `npc_key` ∈ {korven, helst, vossharil, tameris, otreth, mara, vehren,
                 drei_muetter, generic, cls_warrior, cls_witch, cls_mage,
                 cls_ranger, cls_mercenary, cls_huntress, cls_druid,
                 cls_monk}
    `category` z.B. greeting / quest_offer / death / lore / twist_reveal
                    / attack / big_skill / crit / level_up / pickup

    Update #129:
      - 800-ms-Dedup per (npc, category) — Spam-Klick stackt nicht mehr.
      - Combat-Cats (crit/death/level_up/attack/big_skill) → Channel 31
        (interrupt erlaubt).  Dialog-Cats → Channel 30 (skip wenn busy).
    """
    if not _ENABLED:
        return False
    # Voice-Dedup: identische (npc, category) max 1× pro 800 ms
    now = pygame.time.get_ticks()
    key = (npc_key, category)
    last = _LAST_VOICE_MS.get(key, -10000)
    if now - last < _VOICE_DEDUP_WINDOW_MS:
        return False
    try:
        from sf import voice_registry as _vr
    except ImportError:
        return False
    mp3_rel = _vr.pick_voice(npc_key, category)
    if not mp3_rel:
        return False
    project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    abs_path = _os.path.join(project_root, mp3_rel.replace('/', _os.sep))
    if not _os.path.exists(abs_path):
        return False
    # Channel-Wahl per Kategorie
    ch_idx = _VOICE_CHANNEL_COMBAT if category in _COMBAT_VOICE_CATS \
        else _VOICE_CHANNEL_DIALOG
    ok = play_file(abs_path, volume=volume, bus='voice',
                   voice_channel=ch_idx)
    if ok:
        _LAST_VOICE_MS[key] = now
    return ok


# Klassen-Voice-Mapping: Engine-Klassen-Key → voice_registry-NPC-Key.
# (Sorceress wird auf cls_sorceress gemappt, Mage als Lore-Alias.)
_CLASS_VOICE_KEY = {
    'warrior':   'cls_warrior',
    'witch':     'cls_witch',
    'sorceress': 'cls_sorceress',
    'mage':      'cls_sorceress',
    'ranger':    'cls_ranger',
    'mercenary': 'cls_mercenary',
    'rogue':     'cls_mercenary',
    'huntress':  'cls_huntress',
    'druid':     'cls_druid',
    'monk':      'cls_monk',
}


def play_class_voice(class_key, category, volume=0.85):
    """Update #127: Convenience-Wrapper für Klassen-Voices.

    `class_key` = sf.constants Player-cls-key (z.B. 'warrior', 'sorceress').
    `category` ∈ {attack, big_skill, crit, death, level_up}

    Returnt True wenn eine Class-Voice gespielt wurde, sonst False.
    """
    vk = _CLASS_VOICE_KEY.get(class_key)
    if not vk:
        return False
    return play_voice(vk, category, volume=volume)


def play_with_fallback(primary, fallback, volume=1.0, bus='sfx'):
    """Spielt `primary`; wenn der nicht da/spielbar ist, fällt auf `fallback`.

    Update #53: User-Bug-Fix „manchmal keine Waffen-Sounds" — file-only
    Aliases (greatsword_swing/axe_metal/arrow_impact/melee_swing) hatten
    keinen Procedural-Builder als Fallback.  Dieser Helper sorgt dafür,
    dass IMMER ein Sound spielt, auch wenn die externe Audio-Datei fehlt.
    """
    if play(primary, volume=volume, bus=bus):
        return True
    return play(fallback, volume=volume * 0.9, bus=bus)


# N-02 (Update #65): Element-Sonic-Signatures.
# Briefing 5.2 / Audio-Bibel 6.1:
#   - Fire:      Whoom + Crackle + Sizzle
#   - Cold:      Glass + Wind + Chime + Sub-Bass
#   - Lightning: Cracker + Tesla + Hum
#   - Phys:      Sub-Bass + Bone + Rumble
#   - Chaos:     Whisper + Pulse
# Pygame Multi-Channel: wir layered 2–3 vorhandene SFX gleichzeitig auf
# verschiedene Channels — gibt richtige Sonic-Identity ohne neue Assets.
_ELEMENT_SIGNATURES = {
    'fire':      [('cast_fire',      1.00),
                  ('firewood_burning', 0.18),  # Sizzle-Layer
                  ('hit_heavy',      0.20)],  # Whoom-Sub-Layer
    'cold':      [('cast_frost',     1.00),
                  ('chime',          0.25),   # Glass-Crystal
                  ('wind',           0.18)],  # Wind-Whisper
    'lightning': [('cast_lightning', 1.00),
                  ('crit',           0.22),   # Cracker
                  ('thunder',        0.10)],  # Tesla-Hum
    'physical':  [('hit_heavy',      1.00),
                  ('aoe_impact',     0.25)],  # Bone-Rumble
    'chaos':     [('cast_dark',      1.00),
                  ('whisper',        0.35),
                  ('aoe_impact',     0.18)],
    'shadow':    [('cast_dark',      1.00),
                  ('whisper',        0.30)],
}


def play_element_signature(element, volume=1.0, bus='sfx'):
    """N-02: Spielt die layered Element-Sonic-Signature.

    Fall-back auf `play(element_base, volume)` wenn kein Signature-Eintrag
    existiert (z. B. bei custom dmg_types).  Erst-Sound nutzt
    `play_with_fallback`-Pfad damit zumindest EIN Sound garantiert spielt.
    """
    layers = _ELEMENT_SIGNATURES.get(element)
    if not layers:
        play(f'cast_{element}', volume=volume, bus=bus)
        return
    for i, (sfx_name, layer_vol) in enumerate(layers):
        if i == 0:
            play_with_fallback(sfx_name, 'hit',
                                volume=volume * layer_vol, bus=bus)
        else:
            play(sfx_name, volume=volume * layer_vol, bus=bus)


# N-01 (Update #67): Skill-Sound-Schicht-Pipeline (Wind-Up/Body/Tail/Impact).
# Briefing 5.2: jede Schicht hat einen anderen Timing-Slot.  Wind-Up läuft
# am Cast-Start (Telegraph), Body während Travel/Channel, Tail am Ausklingen,
# Impact bei Hit.  Wir tracken offene Phasen pro `phase_id` und queuen die
# nachgelagerten via `_PHASE_QUEUE` (game.update tickt sie ab).
_PHASE_QUEUE = []  # list of dicts {fire_at, name, volume, bus}


def queue_phase_sound(delay_s, name, volume=1.0, bus='sfx'):
    """Queue einen Sound für späteren Trigger (für N-01-Phase-Pipeline)."""
    import pygame as _pg
    now = _pg.time.get_ticks() * 0.001
    _PHASE_QUEUE.append({
        'fire_at': now + max(0.0, float(delay_s)),
        'name': name, 'volume': float(volume), 'bus': bus,
    })


def tick_phase_queue():
    """Per-Frame-Tick aller queued Phase-Sounds.  Returnt #gefeuerte."""
    if not _PHASE_QUEUE:
        return 0
    import pygame as _pg
    now = _pg.time.get_ticks() * 0.001
    fired = 0
    remaining = []
    for entry in _PHASE_QUEUE:
        if entry['fire_at'] <= now:
            play(entry['name'], volume=entry['volume'], bus=entry['bus'])
            fired += 1
        else:
            remaining.append(entry)
    _PHASE_QUEUE[:] = remaining
    return fired


def play_skill_sequence(element, volume=1.0, body_delay=0.15,
                         impact_delay=0.45, bus='sfx'):
    """N-01: Spielt eine full Skill-Sound-Sequenz mit Phasen-Timing.

    - **Wind-Up** (sofort): Layer 0 des Element-Signature
    - **Body** (delay `body_delay`): Layer 1
    - **Tail / Impact** (delay `impact_delay`): Layer 2 (oder aoe_impact)

    Ohne registrierte Layers fällt es auf `play(cast_<element>)` zurück.
    """
    layers = _ELEMENT_SIGNATURES.get(element)
    if not layers:
        play(f'cast_{element}', volume=volume, bus=bus)
        return
    # Layer 0 sofort
    name0, v0 = layers[0]
    play_with_fallback(name0, 'hit', volume=volume * v0, bus=bus)
    # Layer 1 nach body_delay
    if len(layers) > 1:
        name1, v1 = layers[1]
        queue_phase_sound(body_delay, name1, volume=volume * v1, bus=bus)
    # Layer 2 (Impact) nach impact_delay — sonst Fallback aoe_impact
    if len(layers) > 2:
        name2, v2 = layers[2]
        queue_phase_sound(impact_delay, name2, volume=volume * v2, bus=bus)
    else:
        queue_phase_sound(impact_delay, 'aoe_impact', volume=volume * 0.3,
                           bus=bus)


def play_at(name, source_pos, listener_pos, volume=1.0, bus='sfx',
            max_dist_px=1600, min_dist_px=80):
    """3D-/Distance-Audio (Audio-Bibel 1.5): Lautstärke fällt mit Distanz,
    L/R-Pan folgt der Source-Position relativ zum Listener.

    Pygame hat kein echtes HRTF — wir nutzen Channel.set_volume(left, right)
    als pseudo-spatial. Listener = Player-Position.
    """
    if not _ENABLED:
        return
    if source_pos is None or listener_pos is None:
        return play(name, volume=volume, bus=bus)
    dx = source_pos[0] - listener_pos[0]
    dy = source_pos[1] - listener_pos[1]
    dist = (dx * dx + dy * dy) ** 0.5
    if dist >= max_dist_px:
        return
    # Distance-Falloff: linear-quadratic hybrid
    if dist <= min_dist_px:
        falloff = 1.0
    else:
        t = (dist - min_dist_px) / max(1.0, max_dist_px - min_dist_px)
        falloff = max(0.0, 1.0 - t * t)
    # Pan: -1 (links) ... +1 (rechts)
    pan = max(-1.0, min(1.0, dx / max(1.0, max_dist_px * 0.5)))
    snd = _ensure(name)
    if snd is None:
        return
    # PLAN N-03 (Update #96): Pseudo-3D Lowpass-Approximation für ferne
    # Sounds (Pygame hat kein echtes Filter). Ab ~50 % Max-Distance dropt
    # die effektive Volume zusätzlich (-15 dB ≈ ×0.18) — das simuliert
    # die Auralisation entfernter Sounds (Lowpass + Reverb-Tail).
    if dist > max_dist_px * 0.50:
        far_t = (dist - max_dist_px * 0.50) / max(1.0, max_dist_px * 0.50)
        far_factor = 1.0 - far_t * 0.82  # 1.0 → 0.18
        falloff *= max(0.18, far_factor)
    # Update #126: Dedup + explizite SFX-Channel-Allokation auch hier.
    if not _check_dedup(name):
        return
    ch = _alloc_sfx_channel()
    try:
        if ch is None:
            ch = snd.play()
            if ch is None:
                return
        else:
            ch.play(snd)
        # Per-Sound Volume-Cap + Bus + Distance-Falloff
        capped_vol = _apply_volume_cap(name, volume * falloff)
        base = effective_volume(bus, capped_vol)
        left = base * max(0.0, min(1.0, 1.0 - max(0.0, pan)))
        right = base * max(0.0, min(1.0, 1.0 + min(0.0, pan)))
        # Anti-Mute: bei sehr nahen Sounds beide Kanäle nicht ganz auf 0
        if dist < 200:
            left = max(left, base * 0.6)
            right = max(right, base * 0.6)
        ch.set_volume(left, right)
    except Exception:
        pass


def stop_all():
    if _ENABLED:
        try:
            pygame.mixer.stop()
        except Exception:
            pass


# ============================================================
# BACKGROUND-MUSIC (procedurale Loops)
# ============================================================
def _note_to_freq(midi):
    """MIDI-Note → Hz (A4=69=440)."""
    return 440.0 * (2 ** ((midi - 69) / 12.0))


def _arp(notes_midi, dur_total, n_repeats, vol=0.3):
    """Erzeugt Arpeggio: spielt durch notes_midi in dur_total Sekunden."""
    n_total = int(_RATE * dur_total)
    out = [0.0] * n_total
    n_per_note = n_total // (len(notes_midi) * n_repeats)
    pos = 0
    for r in range(n_repeats):
        for midi in notes_midi:
            f = _note_to_freq(midi)
            seg = _osc_triangle(f, n_per_note)
            # Sanftes Decay je Note
            seg = _apply_env(seg, _adsr(n_per_note, a=0.05, d=0.2, s=0.5, r=0.4))
            for i, v in enumerate(seg):
                if pos + i < n_total:
                    out[pos + i] += v * vol
            pos += n_per_note
    return out


def _pad(midi, dur_total, vol=0.15):
    """Long sustained chord pad."""
    n = int(_RATE * dur_total)
    out = [0.0] * n
    for m in midi:
        f = _note_to_freq(m)
        # Sinus + sanftes Vibrato
        for i in range(n):
            v = math.sin(2 * math.pi * f * i / _RATE + 0.3 * math.sin(2 * math.pi * 4 * i / _RATE))
            out[i] += v * vol
    # Sanftes Ein-/Ausblenden
    fade = int(_RATE * 0.3)
    for i in range(fade):
        out[i] *= i / fade
        out[n - 1 - i] *= i / fade
    return out


def _bass(midi, dur_total, beat_dur=0.5, vol=0.35):
    """Bass-Linie: spielt midi-Notes auf Beat-Pattern."""
    n_total = int(_RATE * dur_total)
    out = [0.0] * n_total
    n_per_beat = int(_RATE * beat_dur)
    pos = 0
    idx = 0
    while pos < n_total:
        m = midi[idx % len(midi)]
        f = _note_to_freq(m - 12)  # Oktave tiefer
        seg = _osc_saw(f, n_per_beat)
        seg = _apply_env(seg, _adsr(n_per_beat, a=0.02, d=0.15, s=0.4, r=0.4))
        for i, v in enumerate(seg):
            if pos + i < n_total:
                out[pos + i] += v * vol
        pos += n_per_beat
        idx += 1
    return out


def _build_music_town():
    """Friedliche Dorf-Musik: F-C-Bb-C Akkord-Progression, gemächliches Arpeggio."""
    # Loop-Dauer: 16 Sekunden
    section = 4.0
    total = section * 4
    # Akkord-MIDI-Noten
    chord_F  = [53, 57, 60, 65]  # F major
    chord_C  = [48, 52, 55, 60]  # C major
    chord_Bb = [46, 50, 53, 58]  # Bb major
    chord_Am = [45, 48, 52, 57]  # A minor
    chords = [chord_F, chord_C, chord_Bb, chord_Am]
    # Pad-Layer (Sustained Chords)
    pad_l = []
    pad_r = []
    for c in chords:
        layer = _pad(c, section, vol=0.1)
        pad_l.extend(layer)
        pad_r.extend([v * 0.85 for v in layer])  # leichte Stereo-Variation
    # Arpeggio-Layer
    arp_l = []
    arp_r = []
    for c in chords:
        arp_notes = [c[0] + 12, c[1] + 12, c[2] + 12, c[3] + 12,
                     c[2] + 12, c[1] + 12]
        a = _arp(arp_notes, section, n_repeats=2, vol=0.18)
        arp_l.extend([v * 0.7 for v in a])
        arp_r.extend(a)
    # Bass-Layer
    bass_notes = [c[0] for c in chords for _ in range(8)]
    bass = _bass(bass_notes, total, beat_dur=0.5, vol=0.2)
    # Mix
    n = min(len(pad_l), len(arp_l), len(bass))
    left = [pad_l[i] + arp_l[i] + bass[i] for i in range(n)]
    right = [pad_r[i] + arp_r[i] + bass[i] for i in range(n)]
    return left, right


def _build_music_dungeon():
    """Düstere Dungeon-Musik: Dm-A-F-C, langsam, mehr Drones."""
    section = 4.5
    total = section * 4
    chord_Dm = [50, 53, 57, 62]   # D minor
    chord_A  = [45, 49, 52, 57]   # A
    chord_F  = [41, 45, 48, 53]   # F (tiefe Lage)
    chord_C  = [48, 52, 55, 60]   # C
    chords = [chord_Dm, chord_A, chord_F, chord_C]
    # Düstere Drone-Bass: Sub-Frequenz konstant
    drone_n = int(_RATE * total)
    drone = []
    for i in range(drone_n):
        f = 55  # Tiefer Drone (A1)
        v = math.sin(2 * math.pi * f * i / _RATE) * 0.15
        v += math.sin(2 * math.pi * f * 1.5 * i / _RATE) * 0.05
        drone.append(v)
    # Pads
    pad_l = []
    pad_r = []
    for c in chords:
        layer = _pad(c, section, vol=0.08)
        pad_l.extend(layer)
        pad_r.extend([v * 0.85 for v in layer])
    # Sparse melody (langsame hohe Triangle-Wave)
    melody_notes = [69, 67, 65, 69, 72, 69, 65, 64]  # A-G-F-A-C-A-F-E
    mel_l = []
    n_per_note = int(_RATE * total / len(melody_notes))
    for m in melody_notes:
        f = _note_to_freq(m)
        seg = _osc_triangle(f, n_per_note)
        seg = _apply_env(seg, _adsr(n_per_note, a=0.1, d=0.3, s=0.4, r=0.4))
        seg = _gain(seg, 0.12)
        mel_l.extend(seg)
    mel_r = [v * 0.6 for v in mel_l]
    n = min(len(pad_l), len(drone), len(mel_l))
    left = [pad_l[i] + drone[i] + mel_l[i] for i in range(n)]
    right = [pad_r[i] + drone[i] + mel_r[i] for i in range(n)]
    return left, right


def _build_music_boss():
    """Aggressive Boss-Musik: schnelle Em-C-G-D Progression."""
    section = 2.0
    total = section * 4
    chord_Em = [52, 55, 59, 64]
    chord_C  = [48, 52, 55, 60]
    chord_G  = [55, 59, 62, 67]
    chord_D  = [50, 54, 57, 62]
    chords = [chord_Em, chord_C, chord_G, chord_D]
    # Schneller Bass-Puls
    bass_notes = [c[0] for c in chords for _ in range(4)]
    bass = _bass(bass_notes, total, beat_dur=0.25, vol=0.28)
    # Schnelles Arpeggio
    arp_l = []
    for c in chords:
        notes_a = [c[0] + 12, c[1] + 12, c[2] + 12, c[3] + 12, c[2] + 12, c[1] + 12]
        layer = _arp(notes_a, section, n_repeats=2, vol=0.20)
        arp_l.extend(layer)
    arp_r = [v * 0.75 for v in arp_l]
    # Pads
    pad_l = []
    for c in chords:
        pad_l.extend(_pad(c, section, vol=0.10))
    pad_r = [v * 0.85 for v in pad_l]
    n = min(len(bass), len(arp_l), len(pad_l))
    left = [bass[i] + arp_l[i] + pad_l[i] for i in range(n)]
    right = [bass[i] + arp_r[i] + pad_r[i] for i in range(n)]
    return left, right


_MUSIC_BUILDERS = {
    'town':    (_build_music_town,    0.45),
    'dungeon': (_build_music_dungeon, 0.40),
    'boss':    (_build_music_boss,    0.55),
}


def _ensure_music(name):
    if not _ENABLED:
        return None
    if name in _MUSIC_CACHE:
        return _MUSIC_CACHE[name]
    builder = _MUSIC_BUILDERS.get(name)
    if builder is None:
        _MUSIC_CACHE[name] = None
        return None
    fn, vol = builder
    left, right = fn()
    snd = _make(None, volume=vol, stereo_pair=(left, right))
    _MUSIC_CACHE[name] = snd
    return snd


def _resolve_playlist_entry(playlist_key):
    """Wählt einen Track aus einer Playlist, vermeidet direkte Wiederholung."""
    import random as _r
    pl = MUSIC_PLAYLISTS.get(playlist_key)
    if not pl:
        return None
    last = _last_playlist_pick.get(playlist_key)
    options = [t for t in pl if t != last] or list(pl)
    pick = _r.choice(options)
    _last_playlist_pick[playlist_key] = pick
    return pick


def _resolve_track_to_path(track):
    """Track-Key → absoluter Pfad. '_nebel_von_arken' → Root-Datei."""
    if track == '_nebel_von_arken':
        return EXTERNAL_MUSIC_PATH if _os.path.exists(EXTERNAL_MUSIC_PATH) else None
    return _resolve_music_file(track)


def play_music(name):
    """Spielt einen Music-Loop ab.

    Auflösungs-Reihenfolge:
      1. `MUSIC_PLAYLISTS[name]` → zufälliger Track aus der Playlist
         (Town/Dungeon rotiert zwischen Nebel von Arken und Main 2).
      2. `MUSIC_FILES[name]` → spezifische Datei in Sounds/ (Boss-Tracks).
      3. Procedural-Fallback aus `_MUSIC_BUILDERS`.

    Dedup verhindert Restart pro Frame. Bei Playlist-Rotation wird der
    Track-Identifier `name:<file>` gespeichert, sodass die gleiche Logical-
    Bucket nicht jedes Frame zwischen Files springt.
    """
    global _current_music, _current_music_name, _music_using_external
    if not _ENABLED:
        return
    # Playlist-Auflösung
    is_playlist = name in MUSIC_PLAYLISTS
    if is_playlist:
        # Wenn ein Playlist-Track gerade läuft (Logical-Name = z.B. 'town'),
        # NICHT rotieren — sonst Dedup futsch. Erst beim NÄCHSTEN play_music
        # nach stop_music wird neu gepickt.
        active_track = _current_music_name
        if active_track and active_track.startswith(f'{name}:'):
            if _music_using_external:
                try:
                    if pygame.mixer.music.get_busy():
                        return
                except Exception:
                    pass
            elif _current_music is not None:
                return
        # Neuer Track aus Playlist
        track_key = _resolve_playlist_entry(name)
        if track_key is None:
            return
        full_path = _resolve_track_to_path(track_key)
        compound_name = f'{name}:{track_key}'
    else:
        full_path = None
        compound_name = name

    # Klassischer Dedup für nicht-Playlist Tracks
    if not is_playlist and _current_music_name == name:
        if _music_using_external:
            try:
                if pygame.mixer.music.get_busy():
                    return
            except Exception:
                pass
        elif _current_music is not None:
            return

    # Erst alles stoppen
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    if _current_music is not None:
        try:
            _current_music.stop()
        except Exception:
            pass
        _current_music = None
    _music_using_external = False

    # ---- 1) Playlist-Track aus Sounds/ oder Root ----
    if is_playlist and full_path is not None:
        try:
            pygame.mixer.music.load(full_path)
            base = effective_volume('music')
            if name == 'town':
                base *= 0.85
            pygame.mixer.music.set_volume(max(0.0, min(1.0, base)))
            pygame.mixer.music.play(-1)
            _current_music = None
            _current_music_name = compound_name
            _music_using_external = True
            return
        except pygame.error:
            _music_using_external = False

    # ---- 2) Direkter MUSIC_FILES-Key (Boss-Tracks) ----
    sounds_path = _resolve_music_file(name)
    if sounds_path is not None:
        try:
            pygame.mixer.music.load(sounds_path)
            pygame.mixer.music.set_volume(effective_volume('music'))
            pygame.mixer.music.play(-1)
            _current_music = None
            _current_music_name = name
            _music_using_external = True
            return
        except pygame.error:
            _music_using_external = False

    # ---- 3) Procedural Fallback ----
    snd = _ensure_music(name)
    if snd is None:
        return
    try:
        ch = pygame.mixer.Channel(0)
        ch.play(snd, loops=-1)
        ch.set_volume(effective_volume('music'))
        _current_music = snd
        _current_music_name = name
    except Exception:
        pass


def stop_music():
    global _current_music, _current_music_name, _music_using_external
    if not _ENABLED:
        return
    try:
        pygame.mixer.music.stop()
    except Exception:
        pass
    try:
        pygame.mixer.Channel(0).stop()
    except Exception:
        pass
    _current_music = None
    _current_music_name = None
    _music_using_external = False


def set_music_volume(v):
    """Update #99: Slider-Bus-Volume (0.0 - 1.0).
    Setzt den Bus-Faktor und ruft `_refresh_music_volume()` → respektiert
    jetzt MASTER × SNAPSHOT × Town-Trim. Vorher umging die Methode die
    volle Pipeline (Bug: Slider auf 1.0 spielte 100 % statt Master-65 %)."""
    global MUSIC_VOLUME
    MUSIC_VOLUME = max(0.0, min(1.0, v))
    if not _ENABLED:
        return
    _refresh_music_volume()


def set_sfx_volume(v):
    """0.0 - 1.0 — wird beim Play angewendet."""
    global SFX_VOLUME
    SFX_VOLUME = max(0.0, min(1.0, v))


# PLAN N-07 (Update #97): Adaptive-Music-Crossfade.
# Pygame.mixer.music erlaubt nativ `fadeout(ms)` und `play(loops, start,
# fade_ms)`. Wir wrapping das in eine `crossfade_music(name, dur_ms)`-API.
_music_crossfade_target = None
_music_crossfade_t = 0.0


def crossfade_music(name, duration_ms=1500):
    """Adaptiv: bestehende Musik fadet aus, neuer Track fade-in.

    Stem-Mimikry für POE2-Adaptive-Music — Pygame hat keine echten
    Stem-Layer (braucht Wwise/FMOD), aber Crossfade gibt 80 % des
    audiozisuellen Adaptive-Effekts.
    """
    if not _ENABLED:
        return
    global _music_crossfade_target
    try:
        pygame.mixer.music.fadeout(duration_ms // 2)
    except Exception:
        pass
    _music_crossfade_target = (name, duration_ms)
    # Tatsächlicher Re-Play wird via tick_crossfade() im Game-Loop
    # umgesetzt, sobald der alte Track aus ist.


def tick_crossfade(dt_ms):
    """Pro-Frame-Check: wenn fadeout fertig, neuer Track fade-in."""
    global _music_crossfade_target, _music_crossfade_t
    if _music_crossfade_target is None:
        return
    if not _ENABLED:
        _music_crossfade_target = None
        return
    try:
        if not pygame.mixer.music.get_busy():
            name, dur_ms = _music_crossfade_target
            _music_crossfade_target = None
            play_music(name)
            try:
                pygame.mixer.music.set_volume(0.0)
                # Linear fade-in via tick (mixer.music hat kein nativen
                # post-play fade-in mit set_volume bei externer mp3).
                _music_crossfade_t = 0.0
            except Exception:
                pass
    except Exception:
        _music_crossfade_target = None
