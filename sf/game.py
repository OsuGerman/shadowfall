"""Hauptspiel-Klasse: Update- und Render-Loop, Orchestrierung der Module."""

import math
import random
import pygame
from pygame.math import Vector2

from .constants import (
    SCREEN_W, SCREEN_H, FPS, BG, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM,
    WHITE, BLOOD_LIGHT, MANA, FIRE, FROST, POISON, CLASSES,
)
from .entities import Player, Particle, Floater, Portal
from . import skills, enemies, combat, progression, world, ui as ui_mod, sprites
from . import effects as fx
from . import runes as runes_mod
from . import lighting
from . import town as town_mod
from . import dungeon as dungeon_mod
from . import quests as quests_mod
from . import save as save_mod
from . import achievements as ach_mod
from . import sounds as snd
from . import weather as weather_mod
from .inventory import InventoryUI
from .crafting import CraftingUI
from .shop import ShopUI
from .stash import StashUI
from .ui import TitleUI, SkillTreeUI, RuneChoiceUI, AtlasUI
from .spatial_grid import SpatialGrid
from . import profiler as _profiler_mod


# Update #194: vsync-Setting muss VOR self.settings-Init geladen werden,
# weil display.set_mode der erste Schritt im Constructor ist.
def _preload_vsync_setting() -> bool:
    """Liest vsync-Flag aus dem Settings-File (display.set_mode wird vor
    self.settings-Init aufgerufen, deshalb direkter File-Load).
    Update #195: Default False — damit der 360er-Frame-Cap greifen kann
    (vsync wuerde sonst bei der Monitor-Refresh-Rate kappen).  Bestehende
    Saves behalten ihren gespeicherten Wert.
    """
    try:
        from . import save as _save_mod
        s = _save_mod.load_settings()
        return bool(s.get('vsync', False))
    except Exception:
        return False


# ============================================================
# GAME
# ============================================================
class Game:
    def __init__(self, *, use_gl_post: bool = False):
        snd.init()  # Mixer früh initialisieren
        pygame.init()
        # Update #171: Opt-in PyOpenGL-Post-Process-Mode. Wenn use_gl_post=True
        # initialisieren wir das Display mit OPENGL-Flag + ein separates
        # Off-Screen-Render-Surface, in das alle Pygame-Draws gehen. Die
        # Off-Screen wird per Shader (Bloom + Color-Grade + Vignette) ueber
        # PyOpenGL praesentiert. Default OFF damit klassischer Pygame-Pfad
        # untouched bleibt + 197 Tests gruen bleiben.
        self.use_gl_post = bool(use_gl_post)
        self._render_surface = None     # off-screen wenn gl_post aktiv
        self.gl_post = None             # GLPostProcessor wenn aktiv
        if self.use_gl_post:
            try:
                from . import gl_post as _glp
                if _glp.is_available():
                    # Update #194: vsync pre-load aus Save-File (settings
                    # noch nicht da, deshalb direkt save.load_settings()).
                    # Default False = unlocked, User cycelt im ESC-Menue.
                    _vs = 1 if _preload_vsync_setting() else 0
                    self.screen = pygame.display.set_mode(
                        (SCREEN_W, SCREEN_H),
                        pygame.OPENGL | pygame.DOUBLEBUF, vsync=_vs)
                    if _glp.install(SCREEN_W, SCREEN_H):
                        self.gl_post = _glp.get_active()
                        # Off-Screen-Render-Surface fuer alle Game-Draws
                        self._render_surface = pygame.Surface(
                            (SCREEN_W, SCREEN_H))
                    else:
                        # GL-Init schlug fehl → fallback auf SCALED
                        self.use_gl_post = False
                else:
                    self.use_gl_post = False
            except Exception:
                self.use_gl_post = False

        if not self.use_gl_post:
            # Update #151 (User-Report „Auflösung könnte schärfer sein"):
            # `pygame.SCALED` aktivieren — SDL2 nutzt hardware-accelerated
            # Integer-Scaling.  Auf High-DPI-Monitoren rendert das Spiel
            # jetzt scharf statt bilinear-gestretched vom Windows-DWM.
            # Logische Welt-Größe bleibt SCREEN_W × SCREEN_H (1600×900) —
            # nur die Ausgabe ist crisp.
            try:
                _vs = 1 if _preload_vsync_setting() else 0
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H), pygame.SCALED, vsync=_vs)
            except (pygame.error, TypeError):
                # Fallback wenn SCALED nicht supported (sehr alte SDL)
                self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))

        # Update #171: Pymunk-Physics-World (optional, no-op wenn pymunk
        # nicht installiert). Used by spawn_splitter_burst() / throwables.
        # Eigenes Movement-System bleibt UNANGETASTET — physics nur fuer
        # specific Decor-/Throwable-Effekte.
        # Audit #179 B.4: ImportError isoliert (pymunk-Modul fehlt im
        # Procedural-Build); AttributeError fuer API-Drift bei optionalen
        # Tools-Builds. Andere Exceptions wie ValueError aus dem Constructor
        # WUERDEN ein echter Bug sein und sollen propagieren.
        try:
            from . import physics as _phys
            self.physics = _phys.PhysicsWorld()
        except (ImportError, AttributeError):
            self.physics = None
        pygame.display.set_caption('Shadowfall — Erweitert')
        self.clock = pygame.time.Clock()
        self.fullscreen = False
        # S-07 (Update #79): Controller-Support (XInput-Style).
        # Initialisiert die ersten verfügbaren Gamepads; hot-plug wird
        # via JOYDEVICEADDED/REMOVED-Events nachgezogen.
        try:
            pygame.joystick.init()
            self._joysticks = {}
            for i in range(pygame.joystick.get_count()):
                js = pygame.joystick.Joystick(i)
                js.init()
                self._joysticks[js.get_instance_id()] = js
            # Virtual cursor (Right-Stick) — startet in Bildschirmmitte.
            self._joy_cursor = [SCREEN_W // 2, SCREEN_H // 2]
            # Letzter Axis-Sample für Dead-Zone-Filter.
            self._joy_lstick = (0.0, 0.0)
            self._joy_rstick = (0.0, 0.0)
        except Exception:
            self._joysticks = {}
            self._joy_cursor = [SCREEN_W // 2, SCREEN_H // 2]
            self._joy_lstick = (0.0, 0.0)
            self._joy_rstick = (0.0, 0.0)

        # Update #36: Velgrad-Lore-Fonts (Cinzel/Cormorant) wenn auf System
        # verfügbar, sonst Georgia/Times-Fallback. Plus eigene font_big_dmg
        # für Crit-Numbers (~32pt statt 72pt) damit Combat-Floater nicht
        # den halben Bildschirm einnehmen.
        display_font = pygame.font.match_font(
            'cinzel,trajanpro,georgia,times', bold=True)
        body_font = pygame.font.match_font(
            'cormorantgaramond,ebgaramond,georgia,times', bold=False)
        if display_font:
            self.font_big   = pygame.font.Font(display_font, 72)
            self.font_title = pygame.font.Font(display_font, 48)
            self.font_med   = pygame.font.Font(display_font, 24)
        else:
            self.font_big   = pygame.font.SysFont('georgia,times', 72, bold=True)
            self.font_title = pygame.font.SysFont('georgia,times', 48, bold=True)
            self.font_med   = pygame.font.SysFont('georgia,times', 26, bold=True)
        if body_font:
            self.font_small = pygame.font.Font(body_font, 18)
        else:
            self.font_small = pygame.font.SysFont('georgia,times', 17, bold=True)
        self.font_dmg   = pygame.font.SysFont('georgia,times', 18, bold=True)
        # Mid-Size für große Crits (statt font_big 72pt)
        self.font_big_dmg = pygame.font.SysFont(
            'georgia,times', 28, bold=True)

        self.title_ui = TitleUI(self.font_big, self.font_med, self.font_small)
        self.inv_ui = InventoryUI(self.font_small, self.font_med, self.font_dmg)
        self.tree_ui = SkillTreeUI(self.font_med, self.font_small)
        # Update #184: POE2-Atlas — neue View ersetzt tree_ui beim modal
        self.atlas_ui = AtlasUI(self.font_med, self.font_small)
        self.craft_ui = CraftingUI(self.font_small, self.font_med, self.font_dmg)
        self.rune_ui = RuneChoiceUI(self.font_med, self.font_small)
        self.shop_ui = ShopUI(self.font_small, self.font_med)
        self.stash_ui = StashUI(self.font_small, self.font_med)
        # W-12 (Update #80): Mahnmal-Schrein für Marken-Pakt-Bonus
        self.shrine_ui = ui_mod.ShrineUI(self.font_med, self.font_small)
        # Update #114: Outpost-Mahnmal-Fast-Travel
        self.travel_ui = ui_mod.TravelUI(self.font_med, self.font_small)
        # ROADMAP T1.3 (Update #167+): NPC-Dialog-Modal mit Portrait
        from . import dialog as _dialog_mod
        self._dialog_mod = _dialog_mod
        self.dialog_ui = _dialog_mod.DialogUI(
            self.font_med, self.font_small, self.font_big)
        # PLAN X-09 / ROADMAP T3.5 (Update #168): Cutscene-Player
        from . import cutscene as _cutscene_mod
        self._cutscene_mod = _cutscene_mod
        self.cutscene_player = _cutscene_mod.CutscenePlayer(
            self.font_med, self.font_small, self.font_big)
        # X-09 Cutscene-Cam-Offset (vom Cutscene-Player gesetzt, verbraucht
        # in _update_camera).
        self._cam_cutscene_x = 0.0
        self._cam_cutscene_y = 0.0
        # AA-02 (Update #168): Debug-Console (~-Taste)
        from . import console as _console_mod
        self.console = _console_mod.DebugConsole(
            self.font_med, self.font_small)
        # AA-05 (Update #168): Mod-Hook-API
        # Audit #179 B.4: Lazy-Import-Pattern fuer optionale Module —
        # ImportError ist OK (Module fehlt), AttributeError fuer API-Drift.
        try:
            from . import modloader as _modloader
            self.mod_loader = _modloader.ModLoader()
        except (ImportError, AttributeError):
            self.mod_loader = None
        try:
            from . import replay as _replay
            self.replay_recorder = _replay.ReplayRecorder()
        except (ImportError, AttributeError):
            self.replay_recorder = None
        try:
            from . import asset_validator as _av
            _av.run_startup_validation()
        except (ImportError, AttributeError):
            pass
        self._vignette = ui_mod.make_vignette()
        self.lighting = lighting.LightingSystem(ambient_alpha=130)
        # Update #201 (FPS-Optimierung): Cache fuer fullscreen-Overlay-
        # Surfaces. Vorher allokierte _draw_world bis zu 9 Stueck pro
        # Frame (damage_flash, lowhp-vignette, boss_flash, time_freeze,
        # sandstorm, icestorm, ashrain, miasma, cosmic_pulse,
        # town_color_grading) — jeweils ~5.76 MB SRCALPHA. Heap-Churn
        # killte Combat-FPS. Dict<key, Surface> reused alle.
        self._overlay_surf_cache = {}

        self.running = True
        self.state = 'title'
        # area: 'town' | 'dungeon' | 'outpost'
        self.area = 'town'
        self.modal = None
        self._click_grace = 0.0
        self._damage_flash = 0.0
        self._rune_choices = []
        # Town/Dungeon-State
        self.npcs = []
        self.dungeon_portals = []
        # Update #113: Outpost-Slots
        self.outpost_id = None              # aktives Outpost (None außer area=='outpost')
        self.outpost_return_portal = None   # Portal zurück nach Brassweir
        self.outpost_portals = []           # Portale in Brassweir → Outposts
        self.active_quest = None
        self.active_dungeon_id = None
        self._dungeon_done_timer = 0.0
        self.grid = None
        self._trap_tick_timer = 0.0
        self._step_timer = 0.0
        self._combo_skill_log = []  # list of (time, skill_key)
        self.boss_intro = None
        # Update #132 (B-18): Region-Übergangs-Animation beim Map-Wechsel.
        # `region_transition` ist None oder dict mit `name`, `sub`,
        # `color`, `t`, `total`.  Lebt 1.6 s mit Fade-In/Out.
        self.region_transition = None
        # Update #137 (Z-06): Auto-Save-Timer.  Wird alle
        # AUTOSAVE_INTERVAL_S Sekunden in update() ge'fired.
        self._autosave_timer = 0.0
        # Update #139 (AA-01): Debug-Overlay-Toggle (F3).  Default off.
        self._debug_overlay = False
        # Update #140 (X-01..X-05): Camera-Offset-System.
        # _cam_offset_x/y wird per Frame aus Lookahead + Cursor-Lean +
        # Crit-Zoom + Boss-Pan kombiniert + smooth-lerped.
        self._cam_offset_x = 0.0
        self._cam_offset_y = 0.0
        # Player-Velocity-Track für Lookahead (Diff zwischen prev-Pos)
        self._cam_prev_player_pos = (0.0, 0.0)
        # Crit-Zoom-Pull: Vector2 oder None.  Wird beim Crit gesetzt,
        # decays mit slow_mo_left zurück.
        self._cam_crit_pull = None
        # Boss-Death-Pan: dict mit `boss_pos`, `t`, `total`, `boss_ref`
        # oder None.  Wenn aktiv, folgt Camera dem Boss statt Player.
        self._cam_boss_pan = None
        # Boss-Death-Cinematic: Slow-Mo Timer + Big Flash
        self.slow_mo_left = 0.0
        self.boss_flash = 0.0
        # Heal-Fields (von cast_heal abgelegt)
        self.heal_fields = []   # list of {pos, radius, time_left, heal_per_sec}
        # Welt-Events
        self.event_timer = 35.0
        self.earthquake_left = 0.0
        self.storm_left = 0.0
        self.storm_strike_cd = 0.0
        self.sandstorm_left = 0.0
        self.icestorm_left = 0.0
        self.ashrain_left = 0.0
        self.ashrain_tick = 0.0
        self.miasma_left = 0.0
        self.miasma_tick = 0.0
        self.cosmic_pulse_left = 0.0
        # M-06 + N-12 (Update #66): Rain-Event mit Dynamic-Intensity-Crossfade.
        # 0.0 = kein Regen; rampt in 2 s auf 1.0, hält, tapert in letzten 2 s.
        # Lightning-Skill-Casts während Regen erhalten +30 % Damage-Bonus.
        self.rain_left = 0.0
        self.rain_total = 0.0
        self.rain_intensity = 0.0  # 0..1 — abgeleitet aus rain_left/total
        self.rain_spawn_t = 0.0
        # Time-Freeze (Y-Skill)
        self.time_freeze_left = 0.0
        # Falling Rocks (Erdbeben)
        self.falling_rocks = []
        # Ground Cracks (Boss-Special)
        self.ground_cracks = []
        # Schwarze Löcher (Boss-Pull)
        self.black_holes = []
        # Earthquake-Aftershocks (Spieler-Skill)
        self.pending_aftershocks = []   # [{pos, timer, damage, radius}]
        # Komet-Einschläge (Spieler-Skill)
        self.pending_comets = []        # [{pos, timer, damage, radius}]
        # AoE-Telegraph-Decals (PLAN C-05 / Briefing C.3) — neuer
        # einheitlicher Kanal für tödliche Boden-Marker mit Wind-Up.
        self.decals = []
        # B-07 (Update #49): Breadcrumb-Trail auf Minimap. Speichert die
        # letzten N Spieler-Positionen mit Timestamps; Render fadet sie.
        self.breadcrumbs = []          # list of (world_x, world_y, age_s)
        self._breadcrumb_drop_t = 0.0  # Timer bis zum nächsten Drop
        # Update #138 (V-06): Footprints im Schnee/Sand/Asche.
        # Liste von dicts {x, y, biome, age, side, angle}.  Wird
        # alle 0.32 s beim Step-Tick befüllt (nur biome-relevant).
        self.footprints = []
        self._footprint_side = 0   # 0=L, 1=R, alterniert pro Step
        # E-05 (Update #60): Arena-Features-Catalog initialisieren.
        self.arena_features = []  # list of dicts mit kind/pos/timers/state
        # V-01..V-08 (Update #168): Material-Surface-Effects.
        from . import surface_fx as _sfx
        self.surface_fx = _sfx.SurfaceFXSystem()
        self._surface_fx_mod = _sfx
        # Banner-Cloths (V-08) — Liste von VerletCloth-Instanzen.  Werden
        # in `enter_town`/`enter_outpost` populiert.
        self.cloth_banners = []
        self._wind_t = 0.0
        # U-09 Lightning-Flash-Timer (Frame-skalar).
        self._lightning_flash_t = 0.0
        # U-07 Casting-Timer (vom Skill-Cast-Pfad gesetzt).
        self._casting_t = 0.0
        # X-03 Combat-Zoom-State (zoom 0.92x bei Combat, 1.0 sonst).
        self._combat_zoom_t = 0.0
        self._combat_active_left = 0.0
        # J-13 (Update #64): Particle-Object-Pool zur Allocation-Vermeidung.
        # Cap 800 — über dem Limit werden ältere Particles recycelt.
        self._particle_pool = []
        self._PARTICLE_POOL_MAX = 400  # Pool-Größe-Cap
        # M-07 (Update #69): Performance-Budget — globaler Cap auf aktive
        # Particles. Wenn überschritten, fallen die ÄLTESTEN AMBIENT-
        # Particles zuerst raus (GAMEPLAY/TELEGRAPH bleiben — kritisch).
        # Budget skaliert mit `particle_density`-Setting (M-07 + C-02).
        self._PARTICLE_BUDGET_BASE = 1200
        self.weather = weather_mod.WeatherSystem()
        self.blood_pools = []
        self.last_dungeon_pos = None  # (dungeon_id, pos) für Teleport-zurück
        # Audit #179 B.5: SpatialGrid fuer O(1)-Radius-Queries (Fireball-AoE,
        # Splash, Chain, Pack-Death). Wird in update() einmal pro Frame
        # rebuilt — ~5us bei 50 Enemies. Cell-Size 128 px deckt typische
        # AoE-Radien 40-240 px in 1-4 Zellen ab. False-Positives an Zell-
        # Raendern werden vom Caller per Final-Distance-Check gefiltert.
        self.enemy_grid = SpatialGrid(cell_size=128)
        self.stats = {}
        self.achievements_done = set()
        self.dungeon_tier = {}    # dungeon_id -> max unlocked tier
        self.next_tier = {}       # dungeon_id -> tier to use next entry
        self.current_tier = 1
        self.toast_queue = []     # [(text, color, time_left)]
        # Event-Notifications (G-11/G-12/G-13 — visible feature stack).
        # Eintrag: dict(kind, title, sub, color, time_left, total).
        # Werden in ui._draw_event_notifications gestackt gerendert.
        self.event_notifications = []
        # Event-Log (Pickups + Drops + Story) als 5er-Stack rechts unten.
        # Eintrag: dict(text, color, time_left).
        self.event_log = []
        # Update #22: Visible-Feedback-Timer.
        # crit_flash_t pulsiert nach Crit-Hit (~0.18s decay).
        self.crit_flash_t = 0.0
        # Hit-Vignette (Red-Pulse on player-hit)
        self.hit_vignette_t = 0.0
        self.hovered_enemy = None
        # PLAN A-01: Snapshot des letzten Hits — wird beim Tod gelesen.
        self.last_damage_source = None
        # PLAN A-13: Anzahl der Tode in dieser Session (für Skip-Cinematic).
        self.death_count = 0
        # Death-Cinematic-State: 'none' | 'transition' | 'wakeup_ready'
        self.death_phase = 'none'
        self.death_phase_t = 0.0
        # PLAN E-01: Aktiver Boss-Encounter (von boss_encounter.start_encounter
        # gesetzt; None wenn kein Boss). Wichtig für `_update_music`-Snapshot.
        self.boss_encounter = None
        # Quest-Log: alle aktiven + erledigten Quests + Codex-Daten.
        self.quest_log = None  # wird in reset()/start_game() initialisiert
        # Update #116 (WELT_AUFBAU 3.1): Quest-Choice-Flags.
        # `flags[name] = value` wird von `on_choice()` gesetzt;
        # CONDITIONAL-Stages lesen daraus via `requires_flag`-Expression.
        # Beispiele: flags['shulavh_choice'] = 'heal' | 'defeat'.
        self.flags = {}
        # Settings
        self.settings = {
            # Update #99: Slider-Defaults match jetzt mit den Sounds-
            # Modul-Defaults (MUSIC_VOLUME=0.30, SFX_VOLUME=0.55).
            # Vorher 0.65/0.85 → Slider zeigte falschen Wert.
            'music_vol': 0.30,
            'sfx_vol':   0.55,
            'screen_shake': True,
            # Slider 0.3/0.7/1.0/1.5 = Niedrig/Mittel/Hoch/Ultra.
            # Wirkt seit C-02 nur auf AMBIENT-Layer (Wetter, Funken, Dust).
            # GAMEPLAY-/TELEGRAPH-Partikel werden NICHT reduziert.
            'particle_density': 1.0,
            # C-11: Photosensitive-Modus — max 3 Flash-Frames/s, kein rapid-
            # flashing (Briefing C.4-Accessibility). Dimmt Flashes + Crit-
            # Flash + Death-White-Flash + Decal-Pulse global.
            'photosensitive': False,
            # C-08: Rim-Light-Outline um Spieler — bleibt durch dichte
            # VFX hindurch sichtbar (Briefing C.4 „Player-Outline-Shader").
            'rim_light': True,
            # C-12: High-Contrast Solid-Fill für AoE-Decals (statt Outline).
            'high_contrast_aoe': False,
            # C-10: Tactical-Reduce-Mode — eigene/ally Skill-VFX 50 % Alpha,
            # gegnerische AoE 100 % (Briefing C.4 „Build-clarity").
            'tactical_reduce': False,
            # B-12 (Update #50): Minimap-Rotation. Default Norden-fix-oben;
            # Toggle dreht Minimap mit Spieler-Facing.
            'minimap_rotate': False,
            # Update #171: PROCEDURAL-ONLY-PIVOT.
            # User-Entscheidung: alle KI-generierten Sprite-PNGs entfernt.
            # `ai_sprites` Default jetzt False — Settings-Toggle bleibt als
            # Opt-In falls jemand experimentell wieder PNGs einliefert.
            'ai_sprites': False,
            # P-05 (Update #52): Frame-Cap (30/60/120/144/240/360/0=unlim).
            # Update #202 (User-Request "FPS standardmaessig unlocked"):
            # Default jetzt 0 = komplett ungekappt.  Vorher 360.
            # WICHTIG: vsync muss AUS sein damit >Refresh-Rate erreicht wird
            # (vsync kappt sonst bei der Monitor-Frequenz, egal was hier
            # steht) — deswegen unten vsync-Default ebenfalls auf False.
            'frame_cap': 0,
            # Update #194/#195: VSync on/off — wenn off, FPS bis frame_cap
            # (kein Refresh-Rate-Kappen).  Default jetzt False damit der
            # 360er-Cap ueberhaupt greifen kann.  Bei Screen-Tearing:
            # Settings → ANZEIGE → VSync wieder an.  Take-effect bei
            # naechstem Start (display.set_mode laeuft im Constructor).
            'vsync': False,
            # P-08 (Update #61): Colorblind-Ailment-Farben (kein rot↔grün-
            # Konflikt — Poison wird lila, Burn orange, Frost cyan).
            'colorblind_ailments': False,
            # P-04 (Update #97): Dynamic-Resolution-Scaling.
            # 1.0 = native, 0.85 / 0.7 / 0.5 = Performance-Modi.
            # World-Render erfolgt auf Off-Screen-Surface; UI/HUD bleiben
            # native für Schriften-Schärfe.
            'render_scale': 1.0,
            # PLAN P-07 (Update #101): Multi-Threading-Toggle für
            # Async-Asset-Loading (J-14). True = ThreadPoolExecutor,
            # False = synchroner Single-Thread-Fallback.
            'multi_threading': True,
            # Update #141 (User-Report „werde see krank"): Camera-Cursor-
            # Lean (X-02) ist Motion-Sickness-Trigger.  Default OFF,
            # Spieler kann es opt-in im Settings-Modal aktivieren.
            'camera_cursor_lean': False,
            # Update #141 + User-Request: Camera-Lookahead default OFF
            # (zusammen mit Cursor-Lean) — beide bewegen die Kamera
            # ohne Spieler-Input und triggern bei vielen Spielern
            # Motion-Sickness.  Opt-In im Settings-Modal.
            'camera_lookahead': False,
            # Update #168 (M-10): Bloom-Pass — off/low/high.
            # Performance: low = 4-6 ms/frame, high = 8-12 ms/frame.
            'bloom': 'low',
            # Update #168 (M-12): Heat-Distortion über Lava/Fire-AoE.
            # Toggle für CPU-budgetierte Player.
            'heat_distortion': True,
            # Update #168 (M-13): Optional CRT-Filter (off/scanlines/dither).
            'crt_filter': 'off',
            # Update #168 (X-03): Camera-Zoom-Out im Combat.
            'camera_combat_zoom': True,
            # Update #168 (T1.3): Dialog-Modal beim NPC-Talk.
            'dialog_modal': True,
        }
        # Update #151 (User-Report „Vollbild/Seekrankheits/FPS müssen
        # gespeichert werden"): Persistente Settings aus Disk überlagern
        # die Defaults.  `save_mod.load_settings()` returnt {} wenn die
        # Datei nicht existiert (erster Start).
        try:
            persisted = save_mod.load_settings()
            for k, v in persisted.items():
                if k == 'fullscreen':
                    # Fullscreen ist Toplevel-Attribut; wird unten beim
                    # _toggle_fullscreen-Aufruf angewandt.
                    self._pending_fullscreen = bool(v)
                else:
                    self.settings[k] = v
        except Exception:
            self._pending_fullscreen = False
        # Update #99: Slider-Werte beim Init sofort an Sounds-Modul pushen,
        # damit der Slider-Stand exakt dem laufenden Sound-State entspricht.
        # Behebt User-Bug „Regler funktioniert nicht richtig".
        try:
            snd.set_music_volume(self.settings['music_vol'])
            snd.set_sfx_volume(self.settings['sfx_vol'])
        except Exception:
            pass
        # Update #168: AI-Sprite-Master-Switch beim Init spiegeln.
        # Wenn settings['ai_sprites']=False, schaltet sf.sprites alle
        # Loader auf None-Return -> komplett procedural Look.
        try:
            from . import sprites as _sp_mod
            _sp_mod.set_ai_sprites_enabled(
                bool(self.settings.get('ai_sprites', True)))
        except Exception:
            pass
        # Update #151: Apply persisted fullscreen NACH Display-Init
        # (Toggle erwartet self.screen).
        if getattr(self, '_pending_fullscreen', False) and not self.fullscreen:
            try:
                self._toggle_fullscreen()
            except Exception:
                pass
        self._pending_fullscreen = False
        # C-11 Flash-Limiter: pro Frame-Group max 3 Flashes/s zulassen.
        # Wird in `_emit_photosensitive_flash()` getickt.
        self._flash_window_t = 0.0
        self._flash_window_count = 0
        # Audit #179 C.8: Crash-Recovery-Check beim Start. Wenn ein
        # Autosave existiert das neuer ist als der Slot-Save, halten wir
        # den Eintrag fuer den Title-Screen-Toast vor. F8 wendet ihn an.
        try:
            self.pending_autosave_recovery = save_mod.check_autosave_recovery()
        except Exception:
            self.pending_autosave_recovery = None
        self._autosave_toast_shown = False
        self.reset()

    # ---------- Reset ----------
    def reset(self):
        self.player = Player(self.title_ui.selected)
        # Update #133 (Z-02): Hardcore-Flag.  Default False, wird in
        # start_game überschrieben.
        self.hardcore = False
        self.enemies = []
        self.projectiles = []
        self.loot = []
        self.particles = []
        self.floaters = []
        # Update #136 (O-23): Item-Pickup-Spline-Animationen.
        # Pro Anim: dict mit start_x, start_y, color, kind, t, total,
        # vertex_offset (für Bezier-Bogen-Höhe).  Werden in
        # _update + _draw_world ge-tickt/-rendered.
        self._loot_animations = []
        self.bolts = []
        self.portals = []
        self.npcs = []
        self.dungeon_portals = []
        self.active_quest = None
        self.active_dungeon_id = None
        self._dungeon_done_timer = 0.0
        self.biome = 'crypt'
        self.tiles = world.generate_decor(self.biome)
        self.kills = 0
        self.shake = 0.0
        self.camera = Vector2(0, 0)
        self.camera_shake_offset = (0, 0)

    def start_game(self, mode='adventure', load=False, slot=None,
                    hardcore=False, persist_new=False):
        """Startet ein neues Spiel oder lädt ein Save.

        Update #133 (Z-01/Z-02):
          - `slot` 1..3 (Default = active slot in save_mod).
          - `hardcore` True für Permadeath-Slot (nur bei neuem Game).
        """
        self.reset()
        # Hardcore-Flag: bei load wird er aus dem Save übernommen,
        # bei new-game vom Argument.
        self.hardcore = bool(hardcore)
        if slot is not None:
            save_mod.set_active_slot(slot)
        if load and save_mod.save_exists(slot):
            save_mod.load_game(self, slot=slot)
        ach_mod.init_stats(self)
        # Quest-Log initialisieren — NUR wenn nicht aus Save geladen.
        # save_mod.load_game setzt quest_log direkt; wir überschreiben das
        # nicht. Bei neuem Spiel (oder kein Save) → fresh QuestLog.
        if self.quest_log is None:
            self.quest_log = quests_mod.QuestLog()
            self.quest_log.ensure_initial()
        self.state = 'playing'
        self.modal = None
        self._click_grace = 0.25
        # Klassen-Spawn-Quote als Lore-Toast (Lore-Bibel Teil 7 + Voice-Lines)
        try:
            from . import quotes as _q
            fac = _q.class_faction(self.player.cls)
            origin = _q.class_origin_quote(self.player.cls)
            if fac is not None:
                self.toast(f'{fac["name"]} — Aspekt: {fac["aspect"]}',
                           fac['color'])
            if origin:
                # Erste Zeile als Tease
                short = origin.split('.')[0] + '.'
                self.toast(short, (215, 200, 175))
        except Exception:
            pass
        # Update #194: Breath-SFX-Varianten im Hintergrund vorgenerieren,
        # damit der erste Atemzug im Combat keinen Main-Thread-Hitch
        # ausloest (Synthese ~370ms/Variant). Nicht-blockierend.
        try:
            snd.prewarm_breath_cache()
        except Exception:
            pass
        # Update #121: Survival-Mode entfernt; alle Spiele starten als
        # Adventure (Brassweir → Akt-Welten via Dungeon-/Outpost-Portale).
        self.enter_town()
        # User-Bug („neue Chars verschwinden, nur Krieger bleibt"): Ein
        # frisch erstelltes Spiel wurde bisher erst beim ersten Dungeon-
        # Roundtrip / Autosave auf die Platte geschrieben — wer vorher
        # beendete, dessen Slot blieb leer (und Slot 1 fiel auf den alten
        # Legacy-Save zurueck). Neues Spiel jetzt sofort in seinen Slot
        # persistieren — aber NUR vom echten Neue-Char-Einstieg aus
        # (`persist_new`), nicht wenn start_game als Test-/Init-Helper
        # aufgerufen und danach ein Save drueber-geladen wird.
        if not load and persist_new:
            try:
                # Slot explizit durchreichen (nicht nur via active_slot —
                # so landet der Save garantiert im gewaehlten Slot).
                save_mod.save_game(self, slot=slot)
            except Exception:
                pass

    # ---------- Area-Wechsel ----------
    def enter_town(self):
        # Audit #179 C.9: SFX-Channels beim Scene-Wechsel resetten — sonst
        # spielen Dungeon-Loops (Wind, Lava) noch nachher in Town.
        try:
            snd.stop_all()
        except Exception:
            pass
        # Autosave
        if self.area in ('dungeon', 'outpost'):
            try:
                save_mod.save_game(self)
            except Exception:
                pass
        # Update #36: ein kompakter Tutorial-Toast statt 3 gestapelter.
        # Update #37: nur Erstbesuch, kürzere Lifetime (kein Carry-Over
        # in den Dungeon).
        # Update #201: Controls-Hint-Toast entfernt (Clutter-Reduktion,
        # User „zu viel gleichzeitig") — die Steuerung steht bereits in der
        # persistenten Hinweiszeile unten. _seen_town bleibt fuer andere
        # Erstbesuch-Logik gesetzt.
        if not getattr(self, '_seen_town', False):
            self._seen_town = True

        # Akt-1-Story-Intro (User-Wahl Update #22: Salzwunde-Quest).
        # Lore-Bibel 10.1: Spieler strandet in Brassweir, Korven Vor
        # stellt ihn an, drei verschwundene Dörfer zu untersuchen.
        if not getattr(self.player, 'akt1_intro_seen', False):
            self.player.akt1_intro_seen = True
            self.push_event_notification(
                'story',
                'Brassweir — Letzter Vorposten',
                sub=(f'„Du bist gestrandet. Drei Dörfer sind weg. '
                     f'Sprich mit Korven Vor."'),
                color=(180, 200, 220), duration=4.6)
            self.push_event_log(
                'Akt 1: Salzwunde-Untersuchung — Korven Vor (Ost)',
                (220, 180, 110), duration=8.0)
        # Update #130: Hand-Holding-Tutorial-Toast solange Spieler noch
        # keinen Dungeon abgeschlossen hat — verweist EINDEUTIG auf das
        # Akt-1-Krypta-Portal im Süden (das gelb-markierte).
        # User-Report „Es ist nicht klar ersichtlich welches Portal man
        # nehmen muss".  Erscheint jedes Mal beim Stadt-Entry bis der
        # erste Boss erlegt ist (Stadt-Re-Entry nach Tod = Hint bleibt).
        if len(getattr(self.player, 'completed_dungeons', ())) == 0:
            self.toast_queue.append([
                '→ Gehe nach SÜDEN zum gelb markierten Portal '
                '(Akt I — Krypta).',
                (255, 230, 100), 6.0])
        # Letzten Dungeon merken (für Teleport zurück)
        if self.area == 'dungeon' and self.active_dungeon_id:
            self.last_dungeon_pos = (self.active_dungeon_id,
                                      Vector2(self.player.pos))
        self.area = 'town'
        self.biome = 'town'
        self.grid = None
        self.weather.set_biome('town')
        # Update #82: Flask-Charges voll auffüllen bei Stadt-Entry.
        self._refill_flasks()
        self.blood_pools.clear()
        self.heal_fields.clear()
        self.black_holes.clear()
        self.ground_cracks.clear()
        self.pending_aftershocks.clear()
        self.pending_comets.clear()
        self.decals.clear()
        # Update #179: ephemere World-Entities beim Map-Wechsel clearen,
        # sonst rendern stale falling_rocks-Drop-Shadows / loot-Splines / Funken
        # an ihrer alten Welt-Position in der neuen Map ("Geister-Schatten").
        self.falling_rocks.clear()
        self._loot_animations.clear()
        self.particles.clear()
        self.floaters.clear()
        # V-08 (Update #168): 3 Banner-Cloths bei Brassweir-Stadt-Tor.
        try:
            sfx_mod = self._surface_fx_mod
            self.cloth_banners = [
                sfx_mod.VerletCloth(-180, -440, length=80, segments=5,
                                     color=(190, 150,  90)),
                sfx_mod.VerletCloth(0,    -440, length=80, segments=5,
                                     color=(160, 110,  60)),
                sfx_mod.VerletCloth(180,  -440, length=80, segments=5,
                                     color=(150, 130,  80)),
            ]
            self.surface_fx.clear()
        except Exception:
            self.cloth_banners = []
        # B-07: Trail beim Map-Wechsel löschen
        self.breadcrumbs.clear()
        self._breadcrumb_drop_t = 0.0
        # Update #138 (V-06): Footprints beim Map-Wechsel löschen
        self.footprints.clear()
        # Update #56-Bugfix: stale `boss_encounter` clearen.
        self.boss_encounter = None
        self.boss_intro = None
        # E-05 (Update #60): Arena-Features pro Map clearen.
        self.arena_features = []
        self.enemies = []
        self.projectiles = []
        self.loot = []
        self.portals = []
        self.active_quest = None
        self.active_dungeon_id = None
        self.player.pos = Vector2(0, 0)
        self.player.target = Vector2(0, 0)
        self.player.moving = False
        self.player.attack_target = None
        # HP/MP voll auffüllen
        eff = progression.effective(self.player)
        self.player.hp = eff['hp_max']
        self.player.mp = eff['mp_max']
        # Town generieren — W-10 (Update #52): Akt-Fortschritt für
        # dynamische Mauer-Brüche durchreichen.
        akt = len(getattr(self.player, 'completed_dungeons', ()))
        # Update #121: generate_town returnt jetzt 3-Tupel (kein
        # Survival-Portal mehr).
        tiles, npcs, dportals = town_mod.generate_town(akt_count=akt)
        self.tiles = tiles
        self.npcs = npcs
        self.dungeon_portals = dportals
        # Update #113 + Update #119: Outpost-Portale in Brassweir spawnen.
        # Verschoben von y=-640 (unsichtbar hinter Mara) in eine
        # **Wegmal-Reise-Tor-Zone** südlich der Statue bei y=420 — direkt
        # vom Spawn (0,0) sichtbar. Spieler sieht die Portale sofort.
        # Layout: 1-Reihe entlang x; mehr als 4 Outposts → 2 Reihen.
        from . import outposts as _op
        from .entities import OutpostPortal as _OPortal
        from .entities import Decor as _DecorCls
        self.outpost_portals = []
        # Update #183 (WELT_AUFBAU §10): quest_log durchreichen damit
        # Quest-Flag-Gating greift (z.B. akt1_salzwunde completed -> Akt-2-
        # Outposts entsperren).  Backward-compat: fehlende quest_log -> nur
        # Dungeon-Count-Heuristik wie vorher.
        unlocked = set(_op.unlocked_outposts(
            self.player, quest_log=getattr(self, 'quest_log', None)))
        # Update #180 (User-Request): NUR freigeschaltete Outposts werden
        # gerendert.  Vorher (#143) waren auch locked-Portale mit 🔒-Label
        # sichtbar — gab visuelle UI-Last + Banner-Kollision bei 7+ Portalen
        # in einer Reihe.  Spieler bekommt die Outpost-Reveal-Sequenz jetzt
        # incremental: pro abgeschlossenem Akt taucht ein neues Portal auf.
        # Brassweir (Hub) ist nie ein Portal — bleibt ausgeschlossen.
        all_outpost_keys = [k for k in _op.OUTPOSTS.keys()
                              if k != 'brassweir' and k in unlocked]
        all_outpost_keys.sort(
            key=lambda k: (_op.OUTPOSTS[k].get('akt', 99),
                            _op.OUTPOSTS[k].get('tier_gate', 99)))
        if all_outpost_keys:
            n = len(all_outpost_keys)
            spacing = 130
            base_y = 400
            start_x = -((n - 1) * spacing) / 2.0
            from .constants import DUNGEONS as _DUNGEONS
            for i, ok in enumerate(all_outpost_keys):
                px = start_x + i * spacing
                py = base_y
                op_cfg = _op.OUTPOSTS[ok]
                akt = op_cfg.get('akt', 1)
                if ok == 'zhar_eth_karawane':
                    akt_lbl = 'Akt 1b (Optional)'
                else:
                    akt_lbl = f'Akt {akt}'
                full_lbl = f'{akt_lbl} — {op_cfg["region_name"]}'
                # Level-Req-Hint fuer zu-schwache Spieler
                dungeon_id = op_cfg.get('dungeon_id')
                if dungeon_id and dungeon_id in _DUNGEONS:
                    req = _DUNGEONS[dungeon_id].get('level_req', 1)
                    if self.player.level < req:
                        full_lbl += f' (Stufe {req}+)'
                portal = _OPortal(px, py, ok, label=full_lbl)
                portal._locked = False
                self.outpost_portals.append(portal)
            # Wegmal-Schild als Decor (Lore-Tafel) — Update #124: nach y=280
            # nach oben verschoben (weg von Mahnmal-Stele bei y=305).
            sign = _DecorCls(0, 280, 'lore_tablet', 0, 50, 0.2,
                              collide_radius=10)
            sign.lore_text = ('„Mahnmal-Wegmal. Die Stelen erinnern den '
                               'Weg, wenn du es vergisst."')
            sign.lore_read = False
            self.tiles.append(sign)
            # Wegmal-Laternen flankieren das Tor links/rechts
            lantern_far_x = max(420, abs(start_x) + 70)
            self.tiles.append(_DecorCls(-lantern_far_x, base_y - 20,
                                          'lantern'))
            self.tiles.append(_DecorCls( lantern_far_x, base_y - 20,
                                          'lantern'))
            self.tiles.append(_DecorCls(-lantern_far_x, base_y + 60,
                                          'lantern'))
            self.tiles.append(_DecorCls( lantern_far_x, base_y + 60,
                                          'lantern'))
        self.outpost_return_portal = None
        self.outpost_id = None
        # Update #119: Faction-Banner in Brassweir bei Tier >= 1 sichtbar.
        # Lore: erlangte Faction-Anerkennung manifestiert sich als
        # Banner-Reihe im Hafen-Pier-Bereich (SO der Stadt).
        self._spawn_faction_banners()
        self.shop_ui.maybe_restock(self.player.level)
        # Update #149 (User-Report „NPCs stecken in Objekten"):
        # Nach Decor + Faction-Banner-Placement: Auto-Unstuck für alle
        # NPCs damit sie nicht IN einem Banner/Pfosten/Stele stecken.
        for npc in self.npcs:
            # NPC.radius default ist ~12 (NPCs sind keine Combat-Entities)
            if not hasattr(npc, 'radius'):
                npc.radius = 12
            if self._decor_collides(npc.pos.x, npc.pos.y, npc.radius):
                self._unstuck_entity(npc)
        # Update #132 (B-18): Region-Übergangs-Animation für Brassweir
        self.trigger_region_transition(biome='town')

    def _spawn_faction_banners(self):
        """Update #119/#120 (WELT_AUFBAU 6.1 World-Visibility):
        Faction-Banner-Promenade an der Hafen-Pier-Boardwalk in Brassweir.

        Lore-Anker: Mahnmal-Gilde notiert die Spieler-Faction-Affinitäten
        als sichtbare Welt-Reaktion. Die Banner hängen an dedizierten
        Holz-Pfosten entlang der Pier-Boardwalk (NE-Ecke der Stadt,
        zwischen Markt-Reihe und Hafen-Pier).

        Update #120: Banner werden jetzt mit „Promenade-Pfosten" als
        Visual-Anker gepaart — Banner schweben nicht mehr leer im Raum.
        """
        from . import faction as _fac
        from .entities import Decor as _DecorCls
        # Pier-Promenade-Linie: nördliche Mauer-Außenseite, von Korven
        # (Ost) richtung Hafen-Pier (SE).  6 Slots mit 55 px Spacing.
        promenade_y = -240
        slots_x = [260, 320, 380, 440, 500, 560]
        # Maximal so viele Banner wie Slots
        idx = 0
        for fkey in _fac.all_factions():
            if idx >= len(slots_x):
                break
            rep = _fac.get_rep(self.player, fkey)
            if rep < 10:
                continue
            bx = slots_x[idx]
            # Promenade-Pfosten unter dem Banner (kleines Pier-Post-Stück
            # als visueller Anker)
            post = _DecorCls(bx, promenade_y + 18, 'pier_post',
                              0, 28, 0.18, collide_radius=0)
            self.tiles.append(post)
            # Banner mit Faction-Metadaten
            d = _DecorCls(bx, promenade_y, 'banner')
            d.faction_key = fkey
            d.faction_color = _fac.faction_color(fkey)
            d.faction_name = _fac.faction_display_name(fkey)
            self.tiles.append(d)
            idx += 1

    def enter_outpost(self, outpost_key):
        """Update #113: Spielerwechsel in einen Akt-Vorposten.

        Lädt das Outpost-Layout (Decor + NPCs + Return-Portal) aus
        `sf/outposts.py` und schaltet die Szene um. Brassweir-Persistenz
        (Stash/Memorial/Crafting) bleibt — der Spieler kehrt für diese
        Services über das Return-Portal nach Brassweir zurück.

        Falls `outpost_key == 'brassweir'`, wird `enter_town()` gerufen.
        """
        if outpost_key == 'brassweir':
            return self.enter_town()
        # Audit #179 C.9: SFX-Channels beim Scene-Wechsel resetten.
        try:
            snd.stop_all()
        except Exception:
            pass
        from . import outposts as _op
        cfg = _op.get_outpost(outpost_key)
        if cfg is None:
            return False

        # Region-Banner als Notification
        self.push_event_notification(
            'story',
            cfg['region_name'],
            sub=cfg.get('short_desc', ''),
            color=cfg.get('color', (220, 200, 140)),
            duration=4.0)

        # Letzten Dungeon merken (falls von Dungeon kommend)
        if self.area == 'dungeon' and self.active_dungeon_id:
            self.last_dungeon_pos = (self.active_dungeon_id,
                                      Vector2(self.player.pos))

        # Szene-Reset analog zu enter_town aber **ohne** Akt-1-Story-Intro
        self.area = 'outpost'
        self.outpost_id = outpost_key
        # Engine-Biome ist die Render-Fallback-Variante (wound_salt → crypt
        # etc.); die Lore-Region-Bezeichnung kommt aus outpost_id +
        # regions.REGIONS[cfg['biome_key']].
        from .regions import fallback_biome
        self.outpost_lore_biome = cfg['biome_key']
        self.biome = fallback_biome(cfg['biome_key'])
        self.weather.set_biome(self.biome)
        self.grid = None
        self.blood_pools.clear()
        self.heal_fields.clear()
        self.black_holes.clear()
        self.ground_cracks.clear()
        self.pending_aftershocks.clear()
        self.pending_comets.clear()
        self.decals.clear()
        # Update #179: siehe enter_town — Geister-Schatten vermeiden.
        self.falling_rocks.clear()
        self._loot_animations.clear()
        self.particles.clear()
        self.floaters.clear()
        self.breadcrumbs.clear()
        self._breadcrumb_drop_t = 0.0
        # Update #138 (V-06): Footprints beim Map-Wechsel löschen
        self.footprints.clear()
        self.boss_encounter = None
        self.boss_intro = None
        self.arena_features = []
        self.enemies = []
        self.projectiles = []
        self.loot = []
        self.portals = []
        self.active_quest = None
        self.active_dungeon_id = None
        self.player.pos = Vector2(0, 0)
        self.player.target = Vector2(0, 0)
        self.player.moving = False
        self.player.attack_target = None
        # HP/MP voll auffüllen (sicherer Camp-Spot)
        eff = progression.effective(self.player)
        self.player.hp = eff['hp_max']
        self.player.mp = eff['mp_max']
        # Layout generieren
        # Update #115: generate_outpost returnt jetzt auch optional einen
        # Dungeon-Portal zum lore-passenden Akt-Dungeon.
        tiles, npcs, return_portal, dungeon_portal = \
            _op.generate_outpost(outpost_key)
        self.tiles = tiles
        self.npcs = npcs
        # Outpost-Dungeon-Portal als reguläres `dungeon_portals`-Element
        # einreihen — F-Interact + Click-Handler funktionieren so direkt.
        self.dungeon_portals = [dungeon_portal] if dungeon_portal else []
        self.outpost_return_portal = return_portal
        # Update #149: NPC-Auto-Unstuck (siehe enter_town).
        for npc in self.npcs:
            if not hasattr(npc, 'radius'):
                npc.radius = 12
            if self._decor_collides(npc.pos.x, npc.pos.y, npc.radius):
                self._unstuck_entity(npc)
        # Update #132 (B-18): Region-Übergangs-Animation für Outpost.
        self.trigger_region_transition(biome=self.biome)
        return True

    def enter_dungeon(self, dungeon_id, tier=None):
        # Audit #179 C.9: SFX-Channels beim Scene-Wechsel resetten.
        try:
            snd.stop_all()
        except Exception:
            pass
        # Update #137 (AA-03): Event-Log für Crash-Repro
        try:
            from . import crash_logger as _crash
            _crash.append_event(
                f'enter_dungeon {dungeon_id} tier={tier}')
        except Exception:
            pass
        self.area = 'dungeon'
        self.active_dungeon_id = dungeon_id
        # Update #37: alte Stadt-Toasts beim Dungeon-Entry clearen
        self.toast_queue.clear()
        # Update #168: Surface-FX + Cloth-Banner sind town-spezifisch — clear.
        self.cloth_banners = []
        try:
            self.surface_fx.clear()
        except Exception:
            pass
        # Zufällige Welt-Events
        self.shadow_invasion = (random.random() < 0.15)
        self.roaming_boss_pending = (random.random() < 0.12)
        # Schwierigkeitsgrad
        if tier is None:
            tier = self.next_tier.get(dungeon_id, 1)
        max_unlocked = self.dungeon_tier.get(dungeon_id, 1)
        tier = max(1, min(tier, max_unlocked))
        self.current_tier = tier
        grid, enemies_list, boss_pos, spec, decors, mini_bosses = \
            dungeon_mod.generate_dungeon(dungeon_id, self.player.level)
        # Tier-Skalierung — Update #95: User-Wunsch „Gegner zu leicht".
        # T1 wird etwas gefährlicher, T2/T3 ziehen stärker an.
        tier_hp = {1: 1.20, 2: 1.85, 3: 3.00}[tier]
        tier_dmg = {1: 1.15, 2: 1.55, 3: 2.05}[tier]
        tier_reward = {1: 1.20, 2: 1.75, 3: 2.80}[tier]
        for e in enemies_list:
            e.hp_max *= tier_hp
            e.hp = e.hp_max
            e.dmg *= tier_dmg
            e.xp = int(e.xp * tier_reward)
            e.gold_range = (int(e.gold_range[0] * tier_reward),
                            int(e.gold_range[1] * tier_reward))
        self.tier_reward_mult = tier_reward
        self.tier_hp_mult = tier_hp
        self.tier_dmg_mult = tier_dmg
        self.biome = spec['biome']
        self.weather.set_biome(self.biome)
        # Quest-Trigger: Biome erreicht
        if self.quest_log is not None:
            quests_mod.on_reach_biome(self, self.biome)
        self.blood_pools.clear()
        self.heal_fields.clear()
        self.black_holes.clear()
        self.ground_cracks.clear()
        self.pending_aftershocks.clear()
        self.pending_comets.clear()
        self.decals.clear()
        # Update #179: siehe enter_town — Geister-Schatten vermeiden.
        self.falling_rocks.clear()
        self._loot_animations.clear()
        self.particles.clear()
        self.floaters.clear()
        # B-07: Trail beim Map-Wechsel löschen
        self.breadcrumbs.clear()
        self._breadcrumb_drop_t = 0.0
        # Update #138 (V-06): Footprints beim Map-Wechsel löschen
        self.footprints.clear()
        # Update #56-Bugfix: stale `boss_encounter` clearen.
        self.boss_encounter = None
        self.boss_intro = None
        self.grid = grid
        self.tiles = decors  # Decor-Objekte, KEINE floor-tiles (die kommen aus grid)
        # E-05 (Update #60): Arena-Features aus Grid übernehmen (Deep-Copy,
        # damit Tick-Mutationen nicht das Grid-Template verändern).
        self.arena_features = [dict(f) for f in
                                getattr(self.grid, 'arena_features', [])]
        self.enemies = enemies_list
        self.projectiles = []
        self.loot = []
        self.portals = []
        self.npcs = []
        self.dungeon_portals = []
        # Update #179: Outpost-Return-Portal beim Dungeon-Enter clearen,
        # sonst rendert sich der "Zurueck nach Brassweir"-Stein an seiner
        # alten Outpost-Welt-Koordinate (0, 380) mitten im Dungeon.
        self.outpost_return_portal = None
        self._dungeon_boss_pos = boss_pos
        self._dungeon_boss_spawned = False
        self._dungeon_done_timer = 0.0
        self.player.pos = Vector2(0, 0)
        self.player.target = Vector2(0, 0)
        self.player.moving = False
        self.player.deaths_in_dungeon = 0
        self.active_quest = quests_mod.Quest(dungeon_id)
        self.floaters.append(Floater(
            0, -60, f'{spec["name"]}', GOLD_BRIGHT))
        # Update #132 (B-18) + #139 (X-11): Region-Animation + Lore-
        # Loading-Card mit Klassen-Portrait + Quote + Tip beim Dungeon-
        # Entry (nicht bei Town/Outpost — dort reicht das Lower-Third).
        self.trigger_region_transition(biome=self.biome,
                                         show_loading_card=True)
        # Update #81: Combat-Start-Voice-Line beim Dungeon-Entry.
        try:
            from . import quotes as _q
            vl = _q.class_voice_line(self.player.cls, 'combat_start')
            if vl:
                self.toast(vl, (220, 200, 140))
        except Exception:
            pass
        # Schatten-Invasion: extra Gegner + bessere Drops
        if self.shadow_invasion:
            self.toast('SCHATTEN-INVASION!', (180, 80, 240))
            from . import enemies as _en
            extra = max(5, len(self.enemies) // 3)
            for _ in range(extra):
                room = random.choice(grid.rooms[1:-1])  # nicht spawn/boss
                cx_g = random.randint(room.x + 1, room.x + room.w - 2)
                cy_g = random.randint(room.y + 1, room.y + room.h - 2)
                wx, wy = grid.cell_to_world_center(cx_g, cy_g)
                e = _en.spawn_enemy(random.choice(['wraith', 'warlock']),
                                     wx, wy, max(1, self.player.level + 2),
                                     elite_chance=0.35)
                # Schatten-Tint
                e.color = (40, 20, 60)
                e.glow = (180, 80, 240)
                self.enemies.append(e)
        # Roaming-Boss: extra Boss in zufälligem Raum
        if self.roaming_boss_pending:
            from . import enemies as _en
            room = random.choice(grid.rooms[1:-1])
            cx_g, cy_g = room.center()
            wx, wy = grid.cell_to_world_center(cx_g, cy_g)
            boss_keys = list(_en.BOSS_TEMPLATES.keys())
            roaming = _en.spawn_boss(random.choice(boss_keys),
                                       wx, wy, max(3, self.player.level))
            roaming.hp_max *= 0.5  # schwächer als Endboss
            roaming.hp = roaming.hp_max
            roaming.shield = roaming.shield_max * 0.5
            roaming.shield_max *= 0.5
            # Update #148: Mark als Roaming damit boss_kill-Voice
            # ihn NICHT triggert (sonst Spam).
            roaming._roaming = True
            self.enemies.append(roaming)
            self.toast('Wandernder Boss in Dungeon!', (255, 200, 60))

    # Update #121: enter_survival() entfernt — Endlos-Modus war ein
    # Welle-für-Welle-Spawner ohne Lore-Anchor, redundant zum
    # Tier-3-Dungeon-System. Stattdessen sind alle Akte über Brassweir-
    # Outpost-Portale und Dungeon-Portale erreichbar.

    # Klassen-spezifische Basic-Attack-VFX-Profile.  Lore-Anker:
    #   warrior — Stahl/Eisen-Funken (helles Bronze/Gelb, schwere Splitter)
    #   monk    — Stille-Schritte-Aura (mattes Gold + radiale Pulse)
    #   mage    — Arkan-Funken (Magier-Blau, kompakter)
    #   witch   — Knochen-Asche (lila-magenta, weicher Drift)
    #   ranger  — Wind-Schnitte (Pfeilgrün, lange Streichlinien)
    #   rogue   — Schatten-Klinge (Magenta-Schwarz, scharf)
    #   huntress— Speer-Wirbel (warmes Orange, Wirbelpartikel)
    #   druid   — Wurzel-Funken (erdbraun + grün)
    _BASIC_ATTACK_VFX = {
        'warrior': dict(col=(255, 220, 130), col2=(190, 110, 60),
                         count=6, spread=0.55, dist=(6, 22), size=(2, 3.5),
                         life=0.32),
        'monk':    dict(col=(250, 240, 200), col2=(220, 200, 130),
                         count=8, spread=0.9,  dist=(4, 16), size=(1.5, 2.5),
                         life=0.30, pulse=True),
        'mage':    dict(col=(140, 170, 255), col2=(80, 100, 220),
                         count=5, spread=0.4,  dist=(4, 16), size=(1.5, 3.0),
                         life=0.36),
        'witch':   dict(col=(200, 110, 220), col2=(120, 60, 160),
                         count=7, spread=0.7,  dist=(4, 20), size=(1.5, 3.0),
                         life=0.42),
        'ranger':  dict(col=(170, 240, 130), col2=(80, 160, 80),
                         count=5, spread=0.3,  dist=(8, 24), size=(1.0, 2.0),
                         life=0.28),
        'rogue':   dict(col=(180, 90, 200), col2=(40, 20, 60),
                         count=6, spread=0.35, dist=(6, 22), size=(1.5, 2.5),
                         life=0.30),
        'huntress':dict(col=(255, 200, 110), col2=(200, 120, 60),
                         count=7, spread=0.6,  dist=(6, 22), size=(1.5, 3.0),
                         life=0.34),
        'druid':   dict(col=(180, 150, 90), col2=(110, 80, 50),
                         count=6, spread=0.5,  dist=(6, 20), size=(1.5, 3.0),
                         life=0.36),
    }

    def _spawn_class_basic_attack_vfx(self, p, crit):
        """Update #151: Class-specific Basic-Attack-VFX (User-Report
        „nicht jede Klasse sollte gleich aussehen — Attacken auch nicht").

        Spawnt Partikel + ggf. radialer Pulse-Ring entsprechend dem
        Klassen-Profil.  Bei Crit wird Count + Distanz erhöht.
        """
        prof = self._BASIC_ATTACK_VFX.get(p.cls,
                                            self._BASIC_ATTACK_VFX['warrior'])
        count = prof['count'] + (2 if crit else 0)
        d_min, d_max = prof['dist']
        s_min, s_max = prof['size']
        for i in range(count):
            a = p.facing + random.uniform(-prof['spread'], prof['spread'])
            r = p.radius + random.uniform(d_min, d_max)
            # Mix primary/secondary color randomly
            c = prof['col'] if (i % 2 == 0) else prof['col2']
            # Velocity: leichter Drift in Schwung-Richtung
            vx = math.cos(a) * 30.0
            vy = math.sin(a) * 30.0
            self.particles.append(Particle(
                p.pos.x + math.cos(a) * r,
                p.pos.y + math.sin(a) * r,
                vx, vy, c,
                prof['life'], random.uniform(s_min, s_max),
            ))
        # Mönch: zusätzlicher radialer Pulse-Ring (Stille-Schritte-Aura)
        if prof.get('pulse'):
            self.spawn_particles(p.pos.x, p.pos.y, 12,
                                  (240, 230, 190),
                                  life_max=0.4, size_max=2.0, gravity=-10)
        # Crit-Bonus: kleiner Burst in Klassen-Farbe
        if crit:
            self.spawn_particles(p.pos.x, p.pos.y, 8, prof['col'],
                                  life_max=0.5, size_max=3.5, gravity=0)

    def _get_quest_target_portal(self):
        """Update #151 (User-Report „20 Portale, planlos"):
        Bestimmt welches Portal die nächste Quest-Etappe ist.

        Returnt Tuple `(kind, key, label)`:
          - kind: 'dungeon' (dungeon_portals) oder 'outpost'
          - key: dungeon_id (z.B. 'crypt_lost') oder outpost_key
          - label: kurzer Banner-Text (z.B. „HAUPTQUEST")

        Returnt `(None, None, None)` wenn keine eindeutige Empfehlung
        ableitbar ist (z.B. keine aktive Main-Quest in einer REACH/KILL-
        Stage).

        Priorität:
          1. Aktive Main-Quest mit REACH-Stage `biome=...` → mappe Biome
             auf passendes dungeon_portal / outpost_portal in der Stadt
          2. Aktive Main-Quest mit KILL/BOSS_ROOM-Stage → gleiches Biome
          3. Keine Main-Quest aktiv + completed_dungeons leer → crypt_lost
        """
        # Biome → Portal-Mapping. dungeon_id wenn Brassweir-Krypta-Portal,
        # sonst der outpost_key (für Outpost-Portale die ins Biome führen).
        BIOME_TO_KEY = {
            'crypt':   ('dungeon', 'crypt_lost'),
            'desert':  ('outpost', 'zhar_eth_karawane'),
            'frost':   ('outpost', 'echo_markt'),
            'lava':    ('outpost', 'saeulen_von_helst'),
            'swamp':   ('outpost', 'knoten_markt'),
            'astral':  ('outpost', 'spiegelhof'),
            'wound_salt': ('outpost', 'drei_wunden_lager'),
            'hollow_word': ('outpost', 'hohlwort'),
        }
        # Region → Outpost-Key Fallback (für Quests deren Stage kein
        # explizites biome=… hat, aber deren region eindeutig in einem
        # Outpost liegt — z.B. „Akt 5 — Spiegelstadt" → spiegelhof).
        REGION_TO_OUTPOST = {
            'Akt 1b': 'zhar_eth_karawane',
            'Akt 2 — Glasgoldene Ruinen': 'echo_markt',
            'Akt 2': 'echo_markt',
            'Akt 3 — Aschenfelder': 'saeulen_von_helst',
            'Akt 3': 'saeulen_von_helst',
            'Akt 4 — Wurzelgrab': 'knoten_markt',
            'Akt 4': 'knoten_markt',
            'Akt 5 — Spiegelstadt': 'spiegelhof',
            'Akt 5': 'spiegelhof',
            'Akt 6 — Drei-Wunden': 'drei_wunden_lager',
            'Akt 6': 'drei_wunden_lager',
            'Akt 7 — Hohlwort': 'hohlwort',
            'Akt 7': 'hohlwort',
        }
        log = getattr(self, 'quest_log', None)
        if log is not None:
            for qid, qst in log.active.items():
                quest = qst.quest
                if not quest.get('is_main'):
                    continue
                st = qst.stage
                if st is None:
                    continue
                tgt = st.get('target', {})
                biome = tgt.get('biome')
                if biome and biome in BIOME_TO_KEY:
                    kind, key = BIOME_TO_KEY[biome]
                    return (kind, key, 'HAUPTQUEST')
                # Fallback: Region-Name auf Outpost-Key mappen
                region = quest.get('region', '')
                for prefix, ok in REGION_TO_OUTPOST.items():
                    if region.startswith(prefix):
                        return ('outpost', ok, 'HAUPTQUEST')
        # Tutorial-Fallback: kein Dungeon gemacht → Krypta-Portal
        if len(getattr(self.player, 'completed_dungeons', ())) == 0:
            return ('dungeon', 'crypt_lost', 'HIER STARTEN')
        return (None, None, None)

    def _push_akt_progression_hint(self, akt_count):
        """Update #144: Nach Boss-Kill einen klaren Hint geben wohin
        als nächstes — verhindert „wo sind die Aschenfelder?"-Konfusion.

        Pusht eine event_notification mit der freigeschalteten Region
        + Outpost-Hint.  Inhalt aus Mapping unten (synchron zu
        outposts.OUTPOSTS).
        """
        # akt_count = 1 → gerade Akt 1 abgeschlossen → Akt 2 verfügbar
        # akt_count = 2 → Akt 2 abgeschlossen → Akt 3 verfügbar  etc.
        NEXT_AKT_HINTS = {
            1: ('Akt 2 freigeschaltet',
                'Echo-Markt (Glasgoldene Ruinen) wartet — '
                'sprich mit Bruder Helst.'),
            2: ('Akt 3 freigeschaltet',
                'Säulen-von-Helst (Aschenfelder) wartet — '
                'Tribunal der Asche jagt dort.'),
            3: ('Akt 4 freigeschaltet',
                'Knoten-Markt (Wurzelgrab) wartet — '
                'die Knochenwitwen verwesen langsam.'),
            4: ('Akt 5 freigeschaltet',
                'Spiegelhof (Velharn-Spiegelstadt) wartet — '
                'Echo-Senatoren handeln dort.'),
            5: ('Akt 6 freigeschaltet',
                'Drei-Wunden-Lager wartet — die Endgame-Bosse '
                'erwachen.'),
            6: ('Akt 7 freigeschaltet',
                'Hohlwort-Camp wartet — das Finale beginnt.'),
        }
        hint = NEXT_AKT_HINTS.get(akt_count)
        if hint is None:
            return
        title, sub = hint
        try:
            self.push_event_notification(
                'story', f'★ {title}', sub=sub,
                color=(243, 213, 114), duration=6.0)
            self.toast(f'→ {sub}', (220, 200, 140))
            self.push_event_log(f'Akt-Progress: {title}',
                                  (243, 213, 114), duration=8.0)
        except Exception:
            pass

    def complete_dungeon(self):
        """Wird aufgerufen wenn der Boss tot ist."""
        if self.active_dungeon_id is None:
            return
        quests_mod.on_dungeon_complete(self)
        # Achievements: Dungeon-Stats
        flawless = (self.player.deaths_in_dungeon == 0)
        ach_mod.on_dungeon_complete(self, self.active_dungeon_id, flawless=flawless)
        # Difficulty: nächste Stufe freischalten
        cur_tier = self.current_tier
        max_unlocked = self.dungeon_tier.get(self.active_dungeon_id, 1)
        if cur_tier >= max_unlocked and cur_tier < 3:
            self.dungeon_tier[self.active_dungeon_id] = cur_tier + 1
            self.toast(f'Schwierigkeit freigeschaltet: Tier {cur_tier + 1}',
                       (255, 200, 80))
        # Update #144: prev_count VOR add für Akt-Übergang-Detection
        prev_akt_count = len(self.player.completed_dungeons)
        self.player.completed_dungeons.add(self.active_dungeon_id)
        new_akt_count = len(self.player.completed_dungeons)
        # Update #32: Progression-Tracker
        if hasattr(self.player, 'prog_dungeons_cleared'):
            self.player.prog_dungeons_cleared.add(self.active_dungeon_id)
        # Update #144: Akt-Progression-Hint nach Boss-Kill — sagt
        # dem Spieler klar wohin als nächstes (User-Frage „wo sind
        # die Aschenfelder?").  Wird als event_notification gepusht
        # damit es sichtbar ist (nicht nur Toast).
        if new_akt_count > prev_akt_count:
            self._push_akt_progression_hint(new_akt_count)
        # Bonus-XP für komplettes Dungeon
        bonus_xp = 100 + self.player.level * 30
        self.player.xp += bonus_xp
        if self.player.xp >= self.player.xp_to_next:
            progression.level_up(self.player)
        self.floaters.append(Floater(
            self.player.pos.x, self.player.pos.y - 40,
            f'DUNGEON ABGESCHLOSSEN  ·  +{bonus_xp} XP', GOLD_BRIGHT))
        self._dungeon_done_timer = 10.0
        # Rune-Wahl als Belohnung
        choices = runes_mod.random_choice(self.player, 3)
        if choices:
            self._rune_choices = choices
            self.modal = 'rune_choice'

    # ---------- Koordinaten ----------
    def w2s(self, pos):
        # Update #140 (X-01/X-02/X-04/X-05): Camera-Offsets — addiert
        # zur Shake.  `_cam_offset_x/y` ist die Summe aus Lookahead,
        # Cursor-Lean, Crit-Zoom-Pull und Boss-Death-Pan.
        sx, sy = self.camera_shake_offset
        ox = getattr(self, '_cam_offset_x', 0.0)
        oy = getattr(self, '_cam_offset_y', 0.0)
        return (pos.x - self.camera.x + SCREEN_W / 2 + sx - ox,
                pos.y - self.camera.y + SCREEN_H / 2 + sy - oy)

    def w2s_xy(self, x, y):
        sx, sy = self.camera_shake_offset
        ox = getattr(self, '_cam_offset_x', 0.0)
        oy = getattr(self, '_cam_offset_y', 0.0)
        return (x - self.camera.x + SCREEN_W / 2 + sx - ox,
                y - self.camera.y + SCREEN_H / 2 + sy - oy)

    def s2w(self, sx, sy):
        # Inverse muss die gleichen Offsets benutzen damit Mouse-Click
        # auf Welt-Position konsistent ist.
        ox = getattr(self, '_cam_offset_x', 0.0)
        oy = getattr(self, '_cam_offset_y', 0.0)
        return Vector2(sx - SCREEN_W / 2 + self.camera.x + ox,
                       sy - SCREEN_H / 2 + self.camera.y + oy)

    # ---------- Input ----------
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                self._handle_keydown(ev)
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                if ev.button == 1:
                    self._handle_mousedown(*ev.pos)
                elif ev.button == 2 and self.modal == 'skilltree':
                    # Update #184: Atlas-UI Middle-Mouse-Pan
                    self.atlas_ui.begin_drag(*ev.pos)
                elif ev.button == 3:
                    self._handle_rightclick(*ev.pos)
            elif ev.type == pygame.MOUSEBUTTONUP:
                # Update #158: Settings-Slider-Release-Save.  Der
                # throttled Drag-Save (1×/0.5s) verpasst sonst den
                # Final-Value beim Loslassen. Nur im Settings-Modal
                # relevant — andere Modals brauchen keinen Up-Handler.
                if ev.button == 1 and self.modal == 'settings':
                    try:
                        save_mod.save_settings(self)
                    except Exception:
                        pass
                elif ev.button == 2 and self.modal == 'skilltree':
                    # Update #184: Atlas-UI Pan-End
                    self.atlas_ui.end_drag()
            elif ev.type == pygame.MOUSEMOTION:
                # Update #184: Atlas-UI Pan-Drag fortsetzen
                if self.modal == 'skilltree' and getattr(self.atlas_ui, '_dragging', False):
                    self.atlas_ui.update_drag(*ev.pos)
            elif ev.type == pygame.MOUSEWHEEL:
                # Update #58: Fullmap Mouse-Wheel-Zoom (User-Wunsch).
                # Scroll-Up zoom in, Scroll-Down zoom out.  Andere Modals
                # ignorieren das Event.
                if self.modal == 'fullmap':
                    self._fullmap_wheel_zoom(ev.y)
                # PLAN H-16 (Update #96): Skill-Tree Mouse-Wheel-Zoom.
                # Update #184: route auf Atlas-UI
                elif self.modal == 'skilltree':
                    self.atlas_ui.wheel_zoom(ev.y)
            # S-07 (Update #79): Controller-Hot-Plug
            elif ev.type == pygame.JOYDEVICEADDED:
                self._joy_on_added(ev.device_index)
            elif ev.type == pygame.JOYDEVICEREMOVED:
                self._joy_on_removed(ev.instance_id)
            elif ev.type == pygame.JOYBUTTONDOWN:
                self._joy_on_button(ev.button)
            elif ev.type == pygame.JOYHATMOTION:
                self._joy_on_hat(ev.value)

        # Halten = kontinuierliche Bewegung
        if (self.state == 'playing' and self.modal is None
                and self._click_grace <= 0
                and pygame.mouse.get_pressed()[0]):
            self.handle_world_click(*pygame.mouse.get_pos())

        # Update #99: Slider-Drag-Support im Settings-Modal.
        # User-Wunsch „Regler richtig funktionieren" — vorher war nur
        # ein einzelner Klick möglich, jetzt auch Drag-Bewegung.
        if (self.state == 'playing' and self.modal == 'settings'
                and pygame.mouse.get_pressed()[0]):
            self._handle_settings_drag(*pygame.mouse.get_pos())

        # S-07: Per-Frame Stick-Polling (kontinuierliche Bewegung wie LMB)
        self._joy_poll_sticks()
        # Update #92: Alt-Hold-State für Loot-Label-Highlight
        try:
            _km = pygame.key.get_mods()
            self._loot_alt_held = bool(_km & pygame.KMOD_ALT)
        except Exception:
            self._loot_alt_held = False

    def _handle_keydown(self, ev):
        # Update #131 (Y-01): Tutorial-Overlay fängt ENTER + ESC ab.
        # ENTER → nächster Schritt; ESC → ganzes Tutorial überspringen.
        # Muss VOR der allgemeinen ESC-Handler kommen damit ESC im
        # Tutorial nicht das Pause-Menü öffnet.
        if self.state == 'playing':
            from . import tutorial as _tut
            if _tut.is_active(self):
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER,
                              pygame.K_SPACE):
                    _tut.advance(self)
                    return
                if ev.key == pygame.K_ESCAPE:
                    _tut.skip(self)
                    return
        # ROADMAP T1.3: Dialog-Modal fängt Keys VOR globalem ESC ab
        if self.modal == 'dialog' and self.state == 'playing':
            if self.dialog_ui.handle_key(ev.key, self):
                return
        # AA-02 (Update #168): Debug-Console ~-Toggle.  Wenn offen,
        # alle Keys werden konsumiert.
        if ev.key == pygame.K_BACKQUOTE:
            self.console.toggle()
            return
        if self.console.open:
            if self.console.handle_key(ev, self):
                return
        if ev.key == pygame.K_ESCAPE:
            # Update #133: Slot-Picker abbrechen (Title-Screen).
            if (self.state == 'title'
                    and getattr(self, '_slot_picker_open', False)):
                self._slot_picker_open = False
                return
            if self.modal == 'pause':
                self.modal = None
            elif self.modal:
                self.modal = None
            elif self.state == 'playing':
                self.modal = 'pause'  # erst Pause-Menü statt sofort beenden
            else:
                self.running = False
            return
        if ev.key == pygame.K_F11:
            self._toggle_fullscreen()
            return
        # Update #139 (AA-01): Debug-Overlay-Toggle (F3)
        if ev.key == pygame.K_F3:
            self._debug_overlay = not getattr(self, '_debug_overlay', False)
            return
        # Update #139 (AA-09): Bug-Report-Snapshot (F12)
        if ev.key == pygame.K_F12:
            self._write_bug_report()
            return
        # Audit #179 C.8: F8 = Crash-Recovery aus Autosave anwenden.
        if ev.key == pygame.K_F8:
            self._try_apply_crash_recovery()
            return
        if self.state == 'title':
            if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_game('adventure', persist_new=True)
            elif ev.key == pygame.K_LEFT:
                self._cycle_class(-1)
            elif ev.key == pygame.K_RIGHT:
                self._cycle_class(1)
            return
        if self.state == 'dead':
            # PLAN A-13: Skip ab 2. Tod via Space — Quote sofort
            if ev.key == pygame.K_SPACE and self.death_count >= 2:
                self.death_phase = 'wakeup_ready'
                self._restore_music_volume_after_death()
                return
            # Update #132 (Y-07): Death-Screen-Action-Buttons.
            # T = Charakter wechseln (Title), Q = Spiel beenden.
            if ev.key == pygame.K_t:
                self._restore_music_volume_after_death()
                self.state = 'title'
                return
            if ev.key == pygame.K_q:
                self._restore_music_volume_after_death()
                self.running = False
                return
            # PLAN A-08: ENTER → Wake-Up in Brassweir (Neuer Versuch).
            # Hold Shift + ENTER → zum Title-Screen (Legacy „Aufgeben").
            if ev.key == pygame.K_RETURN:
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    self._restore_music_volume_after_death()
                    self.state = 'title'
                else:
                    self._wake_up_in_town()
            return

        # state == 'playing'
        if ev.key == pygame.K_i:
            self.modal = None if self.modal == 'inventory' else 'inventory'
            return
        if ev.key == pygame.K_k:
            self.modal = None if self.modal == 'skilltree' else 'skilltree'
            # Update #184: Atlas-View beim Oeffnen auf Klassen-Start zentrieren
            if self.modal == 'skilltree':
                self.atlas_ui.open(self)
            return
        if ev.key == pygame.K_c:
            # Update #184: Im Atlas-Modal centriert C auf Klassen-Start.
            if self.modal == 'skilltree':
                self.atlas_ui._center_on_start(self)
                return
            self.modal = None if self.modal == 'crafting' else 'crafting'
            return
        # Update #43: Skill-Rebind-Modus — wenn aktiv, nächster Tastendruck
        # bindet den ausgewählten Skill (auch wenn Modal offen).
        if getattr(self, '_skill_rebind_pending', None):
            self._handle_skill_rebind_key(ev.key)
            return
        if self.modal:
            # Update #135: Quest-Turn-In-Modal — ENTER nimmt Belohnung an,
            # ESC schließt ohne Abgabe.
            if self.modal == 'quest_turnin':
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self._confirm_quest_turnin()
                    return
                if ev.key == pygame.K_ESCAPE:
                    self.modal = None
                    return
            # F schließt Town-Modals
            if ev.key == pygame.K_f and self.modal in ('shop', 'stash'):
                self.modal = None
            # G schließt Skill-Menü
            elif ev.key == pygame.K_g and self.modal == 'skill_menu':
                self.modal = None
            # Update #76 H-14/H-15: Skill-Tree-Tasten F=Filter-Cycle,
            # P=Plan-Mode-Toggle, Enter=Plan ausführen.
            elif self.modal == 'skilltree' and ev.key == pygame.K_f:
                self.tree_ui.cycle_filter()
            elif self.modal == 'skilltree' and ev.key == pygame.K_p:
                self.tree_ui.toggle_plan_mode(self)
            elif self.modal == 'skilltree' and ev.key in (pygame.K_RETURN,
                                                          pygame.K_KP_ENTER):
                self.tree_ui.commit_plan(self)
            return  # Casts pausieren wenn Modal offen
        # Update #23 + #43: Skill-Bindings (User-konfigurierbar).
        # Erst `player.skill_bindings` checken, sonst Fallback auf
        # statischen CLASS_KEYMAP-Slot.
        bindings = getattr(self.player, 'skill_bindings', None)
        if bindings and ev.key in bindings:
            sid = bindings[ev.key]
            if sid in self.player.unlocked_skills:
                skills.cast(sid, self)
            return
        # Legacy-Fallback: Q/W/E/R/1 → CLASS_KEYMAP[cls][0..4]
        cls_pool = skills.class_keymap(self.player.cls)
        skill_hotkey_index = {
            pygame.K_q: 0, pygame.K_w: 1, pygame.K_e: 2,
            pygame.K_r: 3, pygame.K_1: 4,
        }.get(ev.key)
        if skill_hotkey_index is not None:
            sid = (cls_pool[skill_hotkey_index]
                   if skill_hotkey_index < len(cls_pool) else None)
            if sid:
                skills.cast(sid, self)
            return
        # Mage behält Legacy-Slots 2-5 für spark/bone_spear/ice_nova/comet
        # (anderen Klassen werden 2-5 unbelegt — sie haben weniger Skills im
        # MVP, mehr kommt via Gemcutter).
        if self.player.cls == 'mage':
            if ev.key == pygame.K_2:
                skills.cast('spark', self); return
            elif ev.key == pygame.K_3:
                skills.cast('bone_spear', self); return
            elif ev.key == pygame.K_4:
                skills.cast('ice_nova', self); return
            elif ev.key == pygame.K_5:
                skills.cast('comet', self); return
        if ev.key == pygame.K_SPACE:
            skills.dodge_roll(self)
        elif ev.key == pygame.K_F1:
            # Update #95: Kombinierte Atemzug-Phiole (Vital-Flask)
            self._use_flask('vital')
        elif ev.key == pygame.K_f:
            self._interact()
        elif ev.key == pygame.K_l:
            self._cycle_loot_filter()
        elif ev.key == pygame.K_z:
            self._auto_sort_inventory()
        elif ev.key == pygame.K_v:
            # L-08 (Update #71): Weapon-Swap zwischen Set A und Set B
            self._weapon_swap()
        elif ev.key == pygame.K_t:
            # Update #43: D4-Style Town-Portal (User-Wunsch).
            # In Town: Tier-Cycle (alte Funktion).
            # In Dungeon: animiertes Portal nach Brassweir öffnen.
            if self.area == 'town':
                self._cycle_dungeon_tier()
            elif self.area == 'dungeon':
                self._open_town_portal()
        elif ev.key == pygame.K_j:
            self.modal = None if self.modal == 'questlog' else 'questlog'
        elif ev.key == pygame.K_p and self.modal == 'questlog':
            # SHIFT+P im QuestLog: Audit #179 C.2 — getrackte Quest abbrechen.
            # P ohne SHIFT cycelt nur den Track (Update #160).
            mods = pygame.key.get_mods()
            if mods & pygame.KMOD_SHIFT:
                self._abandon_tracked_quest()
            else:
                self._cycle_tracked_quest()
        elif ev.key == pygame.K_n:
            # N = Notizen / Codex (Lore-Discoveries, Bestiarium-Entdeckungen)
            self.modal = None if self.modal == 'codex' else 'codex'
        elif ev.key == pygame.K_o:
            # O = Memorial / Progression-Statistik (Update #32)
            self.modal = None if self.modal == 'memorial' else 'memorial'
        elif self.modal == 'codex' and ev.key in (pygame.K_1, pygame.K_2,
                                                    pygame.K_3, pygame.K_4,
                                                    pygame.K_5, pygame.K_6):
            # Codex-Tab-Switch via 1..6 — #132 fügt How-to-Play-Tab
            tabs = ['bestiary', 'lore', 'aspects', 'achievements',
                    'factions', 'howto']
            self._codex_tab = tabs[{pygame.K_1: 0, pygame.K_2: 1,
                                     pygame.K_3: 2, pygame.K_4: 3,
                                     pygame.K_5: 4, pygame.K_6: 5}[ev.key]]
        elif (self.modal == 'codex'
              and getattr(self, '_codex_tab', '') == 'howto'
              and ev.key in (pygame.K_LEFT, pygame.K_RIGHT)):
            # Update #132 (Y-03): How-to-Play-Seiten-Navigation
            pages = len(self._CODEX_HOWTO_PAGES)
            cur = getattr(self, '_codex_howto_page', 0)
            cur += (-1 if ev.key == pygame.K_LEFT else 1)
            self._codex_howto_page = max(0, min(pages - 1, cur))
        elif ev.key in (pygame.K_m, pygame.K_TAB):
            # M / TAB = Full-Map-Overlay (PLAN B-08)
            self.modal = None if self.modal == 'fullmap' else 'fullmap'
        elif self.modal == 'fullmap' and ev.key in (
                pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_MINUS, pygame.K_KP_MINUS,
                pygame.K_EQUALS):
            # Zoom-Cycling für Full-Map (Keyboard +/-)
            self._fullmap_wheel_zoom(
                +1 if ev.key not in (pygame.K_MINUS, pygame.K_KP_MINUS) else -1)
        elif ev.key == pygame.K_g:
            self.modal = None if self.modal == 'skill_menu' else 'skill_menu'
        elif ev.key == pygame.K_h:
            self.modal = None if self.modal == 'help' else 'help'
        elif ev.key == pygame.K_x:
            from . import skills as _sk
            _sk.cast_ultimate(self)
        elif ev.key == pygame.K_y:
            from . import skills as _sk
            _sk.cast_time_freeze(self)
        elif ev.key == pygame.K_b:
            from . import skills as _sk
            _sk.cast_teleport(self)

    def _cycle_tracked_quest(self):
        """Update #160 (ROADMAP T2.3-C): Cycelt durch active Quests +
        „kein Track" als Stop.

        Sequenz: None → quest0 → quest1 → … → questN → None → …
        Toast meldet den aktuellen Stand.  Compass folgt automatisch
        via `_resolve_quest_target_pos`-Priorität.
        """
        log = getattr(self, 'quest_log', None)
        if log is None or not log.active:
            return
        active_qids = list(log.active.keys())
        cur = getattr(log, 'tracked_quest_id', None)
        if cur is None:
            # Track first active quest
            log.set_tracked(active_qids[0])
        else:
            try:
                idx = active_qids.index(cur)
            except ValueError:
                idx = -1
            next_idx = idx + 1
            if next_idx >= len(active_qids):
                # Wrap to None
                log.tracked_quest_id = None
            else:
                log.set_tracked(active_qids[next_idx])
        # Toast
        new_tracked = log.tracked_quest_id
        if new_tracked is None:
            self.toast('Quest-Pin gelöst.', (200, 180, 140))
        else:
            qst = log.active.get(new_tracked)
            title = qst.title if qst else new_tracked
            self.toast(f'📌 Verfolge: „{title}“', (255, 220, 100))

    def _abandon_tracked_quest(self):
        """Audit #179 C.2: Bricht die getrackte (oder erste aktive) Quest ab.

        Main-Quests sind geschuetzt (kein Brechen der Akt-Progression).
        Toast meldet Erfolg/Schutz.
        """
        log = getattr(self, 'quest_log', None)
        if log is None or not log.active:
            return
        qid = getattr(log, 'tracked_quest_id', None)
        if qid is None:
            qid = next(iter(log.active.keys()), None)
        if qid is None:
            return
        st = log.active.get(qid)
        title = getattr(st, 'title', qid) if st else qid
        if log.abandon(qid):
            self.toast(f'✗ Quest abgebrochen: „{title}"',
                       (220, 150, 100))
        else:
            self.toast(f'⚠ Quest „{title}" kann nicht abgebrochen werden '
                       f'(Main-Quest).', (255, 200, 80))

    def _cycle_class(self, dir):
        keys = list(CLASSES.keys())
        idx = keys.index(self.title_ui.selected)
        self.title_ui.selected = keys[(idx + dir) % len(keys)]

    def _toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        # Update #201: GL-Mode-aware. Vorheriger Bug: in gl_post-Mode
        # rief der Toggle set_mode(SCALED) ohne OPENGL-Flag auf — das
        # zerstoerte den GL-Context und naechster gl_post.present()
        # crashte auf glClearColor (GL_INVALID_OPERATION 1282).
        # Fix: in GL-Mode immer mit OPENGL|DOUBLEBUF erneuern + GL-
        # Resources neu installieren (shader/VAO/VBO/textures liegen
        # zusammen mit dem Context im GPU-Memory und sind dahin).
        if self.use_gl_post:
            from . import gl_post as _glp
            _vs = 1 if self.settings.get('vsync', True) else 0
            flags = pygame.OPENGL | pygame.DOUBLEBUF
            if self.fullscreen:
                flags |= pygame.FULLSCREEN
            try:
                # Update #201: uninstall VOR set_mode, damit teardown
                # die Resources im noch lebendigen alten Context
                # freigeben kann.  Set_mode danach erstellt einen
                # frischen Context, in dem wir wieder neu installieren.
                _glp.uninstall()
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H), flags, vsync=_vs)
                if _glp.install(SCREEN_W, SCREEN_H):
                    self.gl_post = _glp.get_active()
                else:
                    # GL-Re-Init schlug fehl → fallback auf SCALED-Pfad.
                    self.use_gl_post = False
                    self.gl_post = None
                    self._render_surface = None
                    self.screen = pygame.display.set_mode(
                        (SCREEN_W, SCREEN_H),
                        (pygame.FULLSCREEN if self.fullscreen else 0)
                        | pygame.SCALED, vsync=_vs)
            except (pygame.error, TypeError):
                # Worst-Case: GL-Mode komplett deaktivieren.
                self.use_gl_post = False
                self.gl_post = None
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H),
                    (pygame.FULLSCREEN if self.fullscreen else 0)
                    | pygame.SCALED, vsync=_vs)
        else:
            if self.fullscreen:
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H),
                    pygame.FULLSCREEN | pygame.SCALED, vsync=1)
            else:
                # Update #151: Windowed-Mode auch mit SCALED für Sharpness
                # auf High-DPI-Monitoren.
                try:
                    self.screen = pygame.display.set_mode(
                        (SCREEN_W, SCREEN_H), pygame.SCALED, vsync=1)
                except (pygame.error, TypeError):
                    self.screen = pygame.display.set_mode(
                        (SCREEN_W, SCREEN_H))
        # Update #151: Vollbild-Toggle persistieren
        try:
            save_mod.save_settings(self)
        except Exception:
            pass

    def _apply_vsync_setting(self):
        """Update #201: Live-Apply von settings['vsync'].

        SDL kann VSync nicht ohne set_mode-Recreate umschalten. Wir
        ruefen mit selbem flag-Pattern wie _toggle_fullscreen erneut
        set_mode auf — in GL-Mode mit OPENGL|DOUBLEBUF und Re-Install
        des GLPostProcessors (Shader/VAO/VBO/Texturen liegen im
        GL-Context und sind nach set_mode weg).

        Bei Fehler wird KEIN Toast geworfen — der Caller in
        _handle_settings_click wirft selbst den Fail-Toast.
        """
        _vs = 1 if self.settings.get('vsync', True) else 0
        if self.use_gl_post:
            from . import gl_post as _glp
            flags = pygame.OPENGL | pygame.DOUBLEBUF
            if self.fullscreen:
                flags |= pygame.FULLSCREEN
            _glp.uninstall()
            self.screen = pygame.display.set_mode(
                (SCREEN_W, SCREEN_H), flags, vsync=_vs)
            if _glp.install(SCREEN_W, SCREEN_H):
                self.gl_post = _glp.get_active()
            else:
                # GL-Re-Init fehlgeschlagen → fallback auf SCALED.
                self.use_gl_post = False
                self.gl_post = None
                self._render_surface = None
                fb_flags = pygame.SCALED
                if self.fullscreen:
                    fb_flags |= pygame.FULLSCREEN
                self.screen = pygame.display.set_mode(
                    (SCREEN_W, SCREEN_H), fb_flags, vsync=_vs)
        else:
            flags = pygame.SCALED
            if self.fullscreen:
                flags |= pygame.FULLSCREEN
            self.screen = pygame.display.set_mode(
                (SCREEN_W, SCREEN_H), flags, vsync=_vs)

    def _handle_mousedown(self, sx, sy):
        if self.state == 'title':
            # Update #133 (Z-01): Slot-Picker-Overlay fängt Klicks ab
            # wenn offen.  Returns True wenn Klick verarbeitet wurde.
            if getattr(self, '_slot_picker_open', False):
                if self._handle_slot_picker_click(sx, sy):
                    return
            self.title_ui.save_exists = save_mod.save_exists()
            result = self.title_ui.handle_click(sx, sy)
            if result == 'start_adventure':
                # Update #133: erst Slot-Picker, dann Start
                self._slot_picker_open = True
                self._slot_picker_mode = 'new'  # neuer Char
                self._slot_picker_hardcore = False
            elif result == 'continue':
                self._slot_picker_open = True
                self._slot_picker_mode = 'load'
            return
        if self.state == 'dead':
            # Update #132 (Y-07): Wenn ein Button-Rect getroffen wurde,
            # führe die zugeordnete Action aus.
            rects = getattr(self, '_death_action_rects', None) or {}
            mx, my = pygame.mouse.get_pos()
            for action_key, rect in rects.items():
                if rect.collidepoint(mx, my):
                    if action_key == 'retry':
                        self._wake_up_in_town()
                    elif action_key == 'charsel':
                        self._restore_music_volume_after_death()
                        self.state = 'title'
                    elif action_key == 'quit':
                        self._restore_music_volume_after_death()
                        self.running = False
                    return
            # PLAN A-08: Default-Klick ohne Button → Wake-Up.
            self._wake_up_in_town()
            return
        # playing
        if self.modal == 'inventory':
            self.inv_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'skilltree':
            # Update #184: Atlas-UI Linksklick → allokieren
            self.atlas_ui.handle_left_click(self, sx, sy)
            return
        if self.modal == 'crafting':
            self.craft_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'gemcutter':
            self._handle_gemcutter_click(sx, sy)
            return
        if self.modal == 'pause':
            self._handle_pause_click(sx, sy)
            return
        if self.modal == 'quest_turnin':
            # Update #135: Click auf Accept-/Later-Button im Quest-Modal
            rects = getattr(self, '_quest_turnin_button_rects', {}) or {}
            for key, rect in rects.items():
                if rect.collidepoint(sx, sy):
                    if key == 'accept':
                        self._confirm_quest_turnin()
                    else:
                        self.modal = None
                    return
            return
        if self.modal == 'settings':
            self._handle_settings_click(sx, sy)
            return
        if self.modal == 'shop':
            self.shop_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'stash':
            self.stash_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'shrine':
            self.shrine_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'travel':
            self.travel_ui.handle_click(self, sx, sy)
            return
        if self.modal == 'rune_choice':
            picked = self.rune_ui.handle_click(self._rune_choices, sx, sy)
            if picked:
                runes_mod.apply_rune(self.player, picked['skill'], picked['id'])
                self.floaters.append(Floater(
                    self.player.pos.x, self.player.pos.y - 50,
                    f'Rune: {picked["name"]}', (255, 220, 100)))
                self.modal = None
            return
        if self.modal == 'skill_menu':
            self._handle_skill_menu_click(sx, sy)
            return
        if self.modal == 'dialog':
            # ROADMAP T1.3: NPC-Dialog-Modal — Click steuert Skip/Choice.
            self.dialog_ui.handle_click(sx, sy, self)
            return
        if self._click_grace > 0:
            return
        self.handle_world_click(sx, sy)

    def _tick_arena_features(self, dt):
        """E-05 (Update #60): Per-Frame-Tick aller Arena-Features.

        Lava-Stream: Pulse-Phase idle → warn (Decal) → active (Damage) → idle.
        Crypt-Grave: Periodisch spawnen Skelette (alle 12 s) wenn nicht
        zerstört + Boss noch lebt.  Spieler kann das Grab beschädigen
        (Auto-Damage wenn nah + slash-Skill).
        """
        p = self.player
        for af in self.arena_features[:]:
            kind = af.get('kind')
            if kind == 'lava_stream':
                af['pulse_cd'] -= dt
                if af['phase'] == 'idle' and af['pulse_cd'] <= 0:
                    # → warn-Phase: spawn ein Decal-Telegraph (1.0 s)
                    af['phase'] = 'warn'
                    af['phase_t'] = 0.0
                    from . import effects as _fx
                    fx_pos = (af['x'], af['y'])
                    fx_radius = af['radius']
                    fx_dmg = 25 + p.level * 1.5

                    def _on_pulse(g, decal, _x=fx_pos[0], _y=fx_pos[1],
                                   _r=fx_radius, _d=fx_dmg):
                        from pygame.math import Vector2 as _V
                        if (g.player.pos - _V(_x, _y)).length() <= _r:
                            g.damage_player(_d, dmg_type='fire')
                        g.spawn_particles(_x, _y, 24, (255, 120, 40),
                                           life_max=0.7, size_max=5,
                                           gravity=60, friendly=False)
                        g.shake = max(g.shake, 4)

                    _fx.spawn_ground_decal(
                        self, af['x'], af['y'], radius=af['radius'],
                        kind=_fx.DECAL_KIND.DEADLY,
                        windup=1.0, lifetime=0.0,
                        on_activate=_on_pulse, play_windup=False)
                    af['pulse_cd'] = 5.5 + (af.get('_jitter', 0))
                af['phase_t'] += dt
                if af['phase'] == 'warn' and af['phase_t'] > 1.0:
                    af['phase'] = 'idle'
                    af['phase_t'] = 0.0
            elif kind == 'crypt_grave':
                if af.get('destroyed', False):
                    continue
                # Player nah genug + greift mit Melee an → Damage am Grave
                d = ((p.pos.x - af['x']) ** 2
                      + (p.pos.y - af['y']) ** 2) ** 0.5
                if d < af['radius'] + p.radius + 12 and p.attack_target is None:
                    # Auto-Hit alle 0.5 s wenn nah ohne Target
                    af['_hit_cd'] = af.get('_hit_cd', 0.0) - dt
                    if af['_hit_cd'] <= 0:
                        af['_hit_cd'] = 0.5
                        # nur reagieren wenn player gerade attackiert
                        if p.attack_cd <= 0:
                            af['hp'] -= 15
                            self.spawn_particles(af['x'], af['y'], 8,
                                                  (200, 200, 220),
                                                  life_max=0.4, size_max=3)
                            if af['hp'] <= 0:
                                af['destroyed'] = True
                                self.shake = max(self.shake, 4)
                                self.spawn_particles(af['x'], af['y'], 20,
                                                      (200, 200, 220),
                                                      life_max=0.7, size_max=5)
                                self.toast('Grab zerstört!',
                                           (200, 200, 220))
                # Skelett-Spawn-Tick
                af['spawn_cd'] -= dt
                if af['spawn_cd'] <= 0 and not af.get('destroyed', False):
                    af['spawn_cd'] = 14.0
                    # Nur wenn Boss lebt UND nicht zu viele Skelette schon da
                    boss_alive = any(getattr(e, 'is_boss', False)
                                      and not e.dying for e in self.enemies)
                    n_skeletons = sum(1 for e in self.enemies
                                       if e.type_key == 'skeleton'
                                       and not e.dying)
                    if boss_alive and n_skeletons < 6:
                        from . import enemies as _en
                        sk = _en.spawn_enemy(
                            'skeleton', af['x'], af['y'],
                            self.player.level, elite_chance=0)
                        self.enemies.append(sk)
                        self.spawn_particles(af['x'], af['y'], 12,
                                              (200, 200, 220),
                                              life_max=0.5, size_max=4)
            elif kind == 'ice_pillar':
                # E-11 (Update #63): zerstörbarer Eis-Pillar.  Beim Tod
                # spawnen 10 Frost-Bolts radial (Damage-AoE für umliegende
                # Mobs UND Spieler — Vorsicht!).
                if af.get('destroyed', False):
                    continue
                d = ((p.pos.x - af['x']) ** 2
                      + (p.pos.y - af['y']) ** 2) ** 0.5
                if d < af['radius'] + p.radius + 12 and p.attack_target is None:
                    af['_hit_cd'] = af.get('_hit_cd', 0.0) - dt
                    if af['_hit_cd'] <= 0 and p.attack_cd <= 0:
                        af['_hit_cd'] = 0.5
                        af['hp'] -= 15
                        self.spawn_particles(af['x'], af['y'], 8,
                                              (200, 230, 255),
                                              life_max=0.4, size_max=3)
                        if af['hp'] <= 0:
                            af['destroyed'] = True
                            self.shake = max(self.shake, 8)
                            self.spawn_particles(af['x'], af['y'], 32,
                                                  (200, 230, 255),
                                                  life_max=0.8, size_max=5)
                            # 10 Frost-Bolts radial → Damage am Boss + Mobs
                            from .entities import Projectile
                            for k in range(10):
                                ang = (k / 10) * math.tau
                                self.projectiles.append(Projectile(
                                    af['x'], af['y'],
                                    math.cos(ang) * 280,
                                    math.sin(ang) * 280,
                                    18 + p.level * 2, 'frostbolt',
                                    friendly=True, radius=8, life=1.0,
                                ))
                            self.toast('Eis-Säule zerschlagen — Frost-Nova!',
                                       (200, 230, 255))
            elif kind == 'spore_vent':
                # E-11 (Update #63): Periodisch erupt-Sporen.  Während
                # `erupting=True` (0.8 s) appliziert es Poison-Stacks auf
                # den Player wenn nah (<60 px).
                af['erupt_cd'] -= dt
                if af['erupting']:
                    af['erupt_t'] += dt
                    # Damage-Tick alle 0.3 s während eruption
                    d = ((p.pos.x - af['x']) ** 2
                          + (p.pos.y - af['y']) ** 2) ** 0.5
                    af['_poison_tick'] = af.get('_poison_tick', 0.0) - dt
                    if d < af['radius'] and af['_poison_tick'] <= 0:
                        af['_poison_tick'] = 0.3
                        from . import effects as _fx
                        _fx.apply(self, p, 'poison', stacks=1)
                    if af['erupt_t'] >= 0.8:
                        af['erupting'] = False
                        af['erupt_t'] = 0.0
                elif af['erupt_cd'] <= 0:
                    af['erupting'] = True
                    af['erupt_cd'] = 7.0 + random.uniform(-0.5, 0.5)
                    # Eruption-Particles
                    for _ in range(20):
                        ang = random.uniform(0, math.tau)
                        sp = random.uniform(40, 120)
                        self.particles_push(
                            af['x'], af['y'],
                            math.cos(ang) * sp, math.sin(ang) * sp,
                            (140, 200, 100), random.uniform(0.6, 1.0),
                            random.uniform(2, 4), gravity=-30)
            elif kind == 'mirror_echo':
                # E-11 (Update #63): Spiegelhof-Echo spawnt alle 15 s einen
                # Wraith.  Zerstörbar (50 HP).
                if af.get('destroyed', False):
                    continue
                d = ((p.pos.x - af['x']) ** 2
                      + (p.pos.y - af['y']) ** 2) ** 0.5
                if d < af['radius'] + p.radius + 12 and p.attack_target is None:
                    af['_hit_cd'] = af.get('_hit_cd', 0.0) - dt
                    if af['_hit_cd'] <= 0 and p.attack_cd <= 0:
                        af['_hit_cd'] = 0.5
                        af['hp'] -= 12
                        self.spawn_particles(af['x'], af['y'], 6,
                                              (220, 180, 255),
                                              life_max=0.4, size_max=3)
                        if af['hp'] <= 0:
                            af['destroyed'] = True
                            self.shake = max(self.shake, 5)
                            self.spawn_particles(af['x'], af['y'], 24,
                                                  (220, 180, 255),
                                                  life_max=0.7, size_max=5)
                            self.toast('Spiegel-Echo zerstört',
                                       (220, 180, 255))
                # Wraith-Spawn-Tick (nur wenn nicht zerstört)
                af['spawn_cd'] -= dt
                if af['spawn_cd'] <= 0 and not af.get('destroyed', False):
                    af['spawn_cd'] = 16.0
                    n_wraiths = sum(1 for e in self.enemies
                                     if e.type_key == 'wraith' and not e.dying)
                    if n_wraiths < 4:
                        from . import enemies as _en
                        wr = _en.spawn_enemy(
                            'wraith', af['x'], af['y'],
                            self.player.level, elite_chance=0)
                        self.enemies.append(wr)
                        self.spawn_particles(af['x'], af['y'], 16,
                                              (220, 180, 255),
                                              life_max=0.6, size_max=4)

    def _apply_item_music_mod(self, base_vol):
        """N-08 (Update #65): Skill-/Item-spezifische Music-Mute-Overrides.

        Briefing N-08: „The Last Lament"-Crossbow mutet die Music während
        es equipped ist.  Generische Infrastruktur — jedes Item kann ein
        `music_mute`-Attribut (0.0–1.0 als Multiplikator) tragen.  Wirkt
        ausschließlich auf das Music-Volume, nicht auf SFX/Ambient.

        Wenn mehrere Items aktiv sind, wird der KLEINSTE Multiplikator
        gewählt (stärkste Mute gewinnt — narrativ: das mächtigste Item
        bestimmt die Stimmung).
        """
        p = getattr(self, 'player', None)
        if p is None:
            return base_vol
        mod = 1.0
        for it in p.equipment.values():
            if it is None:
                continue
            it_mod = getattr(it, 'music_mute', None)
            if it_mod is not None and 0.0 <= it_mod <= 1.0:
                mod = min(mod, it_mod)
        return base_vol * mod

    def _weapon_swap(self):
        """L-08 (Update #71): Tauscht Weapon + Offhand zwischen Set A und Set B.

        Update #193 (User-Bug "Waffen ploetzlich weg aus Inventar"):
        Vorher hat V den Swap immer ausgefuehrt — wenn Set B leer war,
        wanderten die equippten Waffen in einen unsichtbaren Slot und der
        Spieler sah "Item weg" weil die UI nur Set A zeigt.  Sehr leicht
        per Versehen ausgeloest (V ist neben WASD).
        Jetzt: wenn Set B leer ist UND Set A Items hat, wird der Swap mit
        einer Bestaetigungs-Toast verhindert.  Set-up von Dual-Spec
        funktioniert ueber Shift+V (explizit, akzeptiert leer-werden).
        """
        p = self.player
        # Storage existiert?
        b = getattr(p, 'weapon_set_b', None)
        if b is None:
            p.weapon_set_b = {'weapon': None, 'offhand': None}
            b = p.weapon_set_b
        a_weapon = p.equipment.get('weapon')
        a_offhand = p.equipment.get('offhand')
        b_weapon = b.get('weapon')
        b_offhand = b.get('offhand')
        # Guard: Set B leer + Set A nicht leer -> kein versehentlicher Swap
        b_empty = b_weapon is None and b_offhand is None
        a_has_items = a_weapon is not None or a_offhand is not None
        shift_held = bool(pygame.key.get_mods() & pygame.KMOD_SHIFT)
        if b_empty and a_has_items and not shift_held:
            self.toast(
                'Set B ist leer — Shift+V haelt drueckt um trotzdem zu '
                'tauschen (Dual-Spec einrichten).',
                (240, 200, 100))
            return
        # Swap weapon + offhand
        p.equipment['weapon'] = b_weapon
        p.equipment['offhand'] = b_offhand
        b['weapon'] = a_weapon
        b['offhand'] = a_offhand
        # Set-Toggle
        if getattr(p, 'active_weapon_set', 'a') == 'a':
            p.active_weapon_set = 'b'
        else:
            p.active_weapon_set = 'a'
        # Visual + Audio Feedback — bei leerer Aktiv-Set ein deutlicher
        # Warn-Toast statt nur "Set X: (leer)" damit der Spieler erkennt
        # was passiert ist.
        weap = p.equipment.get('weapon')
        oh = p.equipment.get('offhand')
        if weap is None and oh is None:
            self.toast(
                f'Set {p.active_weapon_set.upper()}: (leer) — '
                f'V erneut druecken um Waffen zurueck zu holen.',
                (255, 180, 80))
        else:
            weap_name = weap.name if weap else '(leer)'
            self.toast(f'Set {p.active_weapon_set.upper()}: {weap_name}',
                       (220, 200, 130))
        try:
            snd.play('dodge', volume=0.5)
        except Exception:
            pass
        # Particle-Burst am Player
        self.spawn_particles(p.pos.x, p.pos.y, 12, (220, 200, 130),
                              life_max=0.5, size_max=4)

    def _fullmap_wheel_zoom(self, delta):
        """Update #58: Mouse-Wheel + Keyboard +/- für Fullmap-Zoom.

        Zooms = [0.5, 1.0, 2.0, 4.0] — snap zum nächstgelegenen Schritt.
        `delta > 0` = zoom in, `delta < 0` = zoom out.  Wenn der Wheel
        mehrere Steps in einem Frame liefert (z.B. 2), entsprechend
        mehrere Stufen springen.
        """
        zooms = [0.5, 1.0, 2.0, 4.0]
        cur = getattr(self, '_fullmap_zoom', 1.0)
        idx = min(range(len(zooms)), key=lambda i: abs(zooms[i] - cur))
        step = int(delta) if delta else 0
        if step > 0:
            idx = min(len(zooms) - 1, idx + step)
        elif step < 0:
            idx = max(0, idx + step)  # step ist negativ
        self._fullmap_zoom = zooms[idx]

    def _handle_skill_menu_click(self, sx, sy):
        """Update #43: Click auf einen Skill-Slot startet Rebind-Modus.

        Spieler kann freigeschaltete Skills auf jede beliebige Taste legen.
        """
        slots = getattr(self, '_skill_menu_slots', None)
        if not slots:
            return
        for rect, sid in slots:
            if rect.collidepoint(sx, sy):
                if sid in self.player.unlocked_skills:
                    self._skill_rebind_pending = sid
                    self.toast(
                        f'Drücke eine Taste für „{sid}“  (Esc = Abbruch)',
                        (255, 220, 100))
                return

    def _handle_skill_rebind_key(self, key):
        """Bindet den aktuell ausgewählten Skill auf die gedrückte Taste.

        Esc = Abbruch. Wenn Taste schon belegt ist, wird sie überschrieben.
        Wenn der gewählte Skill schon woanders gebunden ist, wird die alte
        Bindung entfernt (kein doppelter Eintrag).
        """
        import pygame as _pg
        sid = self._skill_rebind_pending
        self._skill_rebind_pending = None
        if key == _pg.K_ESCAPE:
            self.toast('Rebind abgebrochen', (200, 200, 200))
            return
        # Verbotene Tasten: I/K/C/M/J/N/O/G/H/F/L/Z/T/X/Y/B/SPACE/TAB
        FORBIDDEN = {
            _pg.K_i, _pg.K_k, _pg.K_c, _pg.K_m, _pg.K_j,
            _pg.K_n, _pg.K_o, _pg.K_g, _pg.K_h, _pg.K_f,
            _pg.K_l, _pg.K_z, _pg.K_t, _pg.K_x, _pg.K_y,
            _pg.K_b, _pg.K_SPACE, _pg.K_TAB, _pg.K_ESCAPE,
            _pg.K_RETURN, _pg.K_BACKSPACE,
        }
        if key in FORBIDDEN:
            self.toast('Diese Taste ist reserviert', (255, 120, 80))
            return
        bindings = getattr(self.player, 'skill_bindings', None) or {}
        # Alte Bindung von sid entfernen (falls vorhanden auf anderer Taste)
        for old_key in list(bindings.keys()):
            if bindings[old_key] == sid:
                del bindings[old_key]
        bindings[key] = sid
        self.player.skill_bindings = bindings
        key_name = _pg.key.name(key).upper()
        self.toast(f'„{sid}“ → [{key_name}]', (140, 220, 140))

    # ----- Update #95: KOMBINIERTE Vital-Flasche (User-Wunsch) -----
    def _use_flask(self, kind='vital'):
        """Konsumiert 1 Charge der Vital-Flask und heilt HP+MP gleichzeitig."""
        flasks = getattr(self.player, 'flasks', None)
        if not flasks:
            return
        # Legacy-Aliase: 'life'/'mana' → 'vital'
        if kind in ('life', 'mana'):
            kind = 'vital'
        if kind not in flasks:
            return
        f = flasks[kind]
        if f['charges'] < 1.0:
            self.toast(f'{f["name"]}: keine Ladungen.',
                        (180, 140, 120))
            return
        eff = progression.effective(self.player)
        # Update #106 (Audit F-014): Charge nicht verschwenden wenn schon voll.
        if (self.player.hp >= eff['hp_max']
                and self.player.mp >= eff['mp_max']):
            self.toast('Bereits voll.', (180, 180, 140))
            return
        f['charges'] -= 1.0
        total_hp = eff['hp_max'] * f['hp_pct']
        total_mp = eff['mp_max'] * f['mp_pct']
        frac = f['instant_frac']
        instant_hp = total_hp * frac
        instant_mp = total_mp * frac
        over_hp = total_hp - instant_hp
        over_mp = total_mp - instant_mp
        # Sofort-Heilung
        self.player.hp = min(eff['hp_max'], self.player.hp + instant_hp)
        self.player.mp = min(eff['mp_max'], self.player.mp + instant_mp)
        # Restlicher Heal/Mana als HoT/MoT (kombinierter Effekt)
        if f['duration'] > 0 and (over_hp > 0 or over_mp > 0):
            self.player.flask_effects.append({
                'kind': 'vital',
                'remaining': f['duration'],
                'hp_per_sec': over_hp / f['duration'],
                'mp_per_sec': over_mp / f['duration'],
            })
        # Sound + Particle-Burst (rosé-Farbe)
        try:
            # Update #X — Phase-3-AI: flask_use ist jetzt im SFX-Registry,
            # play_with_fallback findet es ueber _resolve_sfx_file Step 3.
            snd.play_with_fallback('flask_use', 'ui_click', volume=0.55)
            # Glow-Layer abhaengig von HP/MP-Schwerpunkt
            if instant_hp > instant_mp:
                snd.play('flask_health_glow', volume=0.35)
            elif instant_mp > 0:
                snd.play('flask_mana_glow', volume=0.35)
        except Exception:
            pass
        self.spawn_particles(self.player.pos.x, self.player.pos.y,
                              26, f['color'], life_max=0.7, size_max=4,
                              gravity=-80)
        self.toast(f'{f["name"]} verbraucht'
                    f' (+{int(instant_hp)} HP, +{int(instant_mp)} MP)',
                    f['color'])

    def _tick_flask_effects(self, dt):
        """Wendet HoT/MoT aus aktiven Flasks an + tickt Restzeit."""
        flask_effects = getattr(self.player, 'flask_effects', None)
        if not flask_effects:
            return
        eff = progression.effective(self.player)
        keep = []
        for fe in flask_effects:
            dur = min(dt, fe['remaining'])
            # Update #95: Vital-Effekt heilt HP + MP gleichzeitig.
            # Legacy 'life'/'mana' fallback für ältere Saves bevor Migration.
            hp_per = fe.get('hp_per_sec', 0.0)
            mp_per = fe.get('mp_per_sec', 0.0)
            if 'per_sec' in fe:
                # Legacy-Format: per_sec gilt für 'kind'-Resource
                if fe.get('kind') == 'life':
                    hp_per = fe['per_sec']
                elif fe.get('kind') == 'mana':
                    mp_per = fe['per_sec']
            self.player.hp = min(
                eff['hp_max'], self.player.hp + hp_per * dur)
            self.player.mp = min(
                eff['mp_max'], self.player.mp + mp_per * dur)
            fe['remaining'] -= dt
            if fe['remaining'] > 0:
                keep.append(fe)
        self.player.flask_effects = keep

    def _grant_flask_charges(self, amount):
        """Vergibt Charges an die Vital-Flask (Kill-Hook)."""
        flasks = getattr(self.player, 'flasks', None)
        if not flasks:
            return
        f = flasks.get('vital')
        if f is None:
            return
        f['charges'] = min(f['max'], f['charges'] + amount)

    def _refill_flasks(self):
        """Voll-Refill (Stadt-Entry)."""
        flasks = getattr(self.player, 'flasks', None)
        if not flasks:
            return
        for kind, f in flasks.items():
            f['charges'] = float(f['max'])

    # ----- S-07 Controller-Support (Update #79) -----
    _JOY_DEAD_ZONE = 0.22

    def _joy_on_added(self, device_index):
        try:
            js = pygame.joystick.Joystick(device_index)
            js.init()
            self._joysticks[js.get_instance_id()] = js
            self.toast(f'Controller verbunden: {js.get_name()}',
                       (180, 220, 200))
        except Exception:
            pass

    def _joy_on_removed(self, instance_id):
        js = self._joysticks.pop(instance_id, None)
        if js is not None:
            try:
                js.quit()
            except Exception:
                pass
            self.toast('Controller getrennt.', (200, 180, 140))

    def _joy_poll_sticks(self):
        """S-07: Liest L-Stick (Movement) + R-Stick (virtueller Cursor)
        bei jedem Frame. Dead-Zone-Filter unten."""
        if not self._joysticks:
            return
        if self.state != 'playing':
            return
        js = next(iter(self._joysticks.values()))
        try:
            lx = js.get_axis(0)
            ly = js.get_axis(1)
            rx = js.get_axis(2) if js.get_numaxes() > 2 else 0.0
            ry = js.get_axis(3) if js.get_numaxes() > 3 else 0.0
        except Exception:
            return
        dz = self._JOY_DEAD_ZONE
        # L-Stick → Move-Target relativ zum Player (wie LMB-Halten)
        if abs(lx) > dz or abs(ly) > dz:
            if self.modal is None and self._click_grace <= 0:
                # 220 px Ziel-Distanz vor dem Spieler
                tx = self.player.pos.x + lx * 220
                ty = self.player.pos.y + ly * 220
                # In Screen-Coords umwandeln → handle_world_click direkt
                sx, sy = self.w2s_xy(tx, ty)
                self.handle_world_click(sx, sy)
        self._joy_lstick = (lx, ly)
        # R-Stick → virtueller Cursor (für Skill-Aim später)
        if abs(rx) > dz or abs(ry) > dz:
            cx, cy = self._joy_cursor
            cx = max(0, min(SCREEN_W - 1, int(cx + rx * 12)))
            cy = max(0, min(SCREEN_H - 1, int(cy + ry * 12)))
            self._joy_cursor = [cx, cy]
        self._joy_rstick = (rx, ry)

    def _joy_on_button(self, button):
        """S-07: XInput-Style Mapping.
        A(0)=Attack, B(1)=Skill Q, X(2)=Skill W, Y(3)=Skill E,
        LB(4)=Dodge, RB(5)=Skill R, Back(6)=Inventory, Start(7)=Pause."""
        if self.state == 'title':
            if button == 0:
                self.start_game('adventure', persist_new=True)
            return
        if self.state == 'dead' and button == 0:
            # Update #132 (Y-07): Controller-A = Retry-Default.
            self._wake_up_in_town()
            return
        if button == 7:  # Start → Pause-Toggle
            self.modal = None if self.modal == 'pause' else 'pause'
            return
        if button == 6:  # Back → Inventory-Toggle
            self.modal = None if self.modal == 'inventory' else 'inventory'
            return
        if self.modal:
            return
        if button == 0:  # A → Attack am virtuellen Cursor
            self._handle_mousedown(*self._joy_cursor)
            return
        # Skill-Buttons mappen auf bound Keys (Update #43 skill_bindings).
        _key_for_btn = {
            1: pygame.K_q,
            2: pygame.K_w,
            3: pygame.K_e,
            5: pygame.K_r,
            4: pygame.K_SPACE,  # LB → Dodge (Space)
        }
        key = _key_for_btn.get(button)
        if key is None:
            return
        # Synthesize a KEYDOWN event-like dispatch
        fake_ev = type('E', (), {'key': key, 'mod': 0})()
        self._handle_keydown(fake_ev)

    def _joy_on_hat(self, value):
        """S-07: D-Pad → Map-Pan-Vorschlag (vorerst nur Inventory-Cycle)."""
        # Reserved für später (Inventory-Slot-Navigation).
        pass

    def _handle_rightclick(self, sx, sy):
        """Rechts-Klick wird zum Item-Drop im Inventar genutzt."""
        if self.state != 'playing':
            return
        if self.modal == 'inventory':
            self.inv_ui.handle_rightclick(self, sx, sy)
        elif self.modal == 'skilltree':
            # Update #184: Atlas-UI Rechtsklick → refund (Orb-of-Regret).
            self.atlas_ui.handle_right_click(self, sx, sy)
        elif self.modal == 'crafting':
            # Im Crafting: könnte später was tun
            pass

    def handle_world_click(self, sx, sy):
        wpos = self.s2w(sx, sy)
        # Update #57: Item-Click hat höchste Priorität (POE2 click-to-loot).
        # Items werden NUR per Click aufgehoben.  Klick auf ein Item-Loot
        # setzt es als Click-Pickup-Target + Walk-Target zum Item.
        clicked_loot = None
        for l in self.loot:
            if l.kind != 'item' or l.item is None:
                continue
            # Hit-Box: 16 px Radius um Loot-Position
            if (l.pos - wpos).length() < 16:
                clicked_loot = l
                break
        if clicked_loot is not None:
            # Grace blockiert nur Pickup, nicht das Setzen des Targets
            clicked_loot._click_pickup_target = True
            self.player.attack_target = None
            self.player.target = Vector2(clicked_loot.pos)
            self.player.moving = True
            return
        clicked = None
        for e in self.enemies:
            if (e.pos - wpos).length() < e.radius + 6:
                clicked = e
                break
        # Falls Klick auf Gegner: LOS prüfen (in Dungeon)
        if clicked and self.grid is not None:
            if not self.grid.has_los(self.player.pos.x, self.player.pos.y,
                                       clicked.pos.x, clicked.pos.y):
                # Gehe in Richtung, statt direkt anzugreifen
                clicked = None
        if clicked:
            self.player.attack_target = clicked
            self.player.target = Vector2(clicked.pos)
        else:
            self.player.attack_target = None
            self.player.target = wpos
        self.player.moving = True

    def _try_enter_portal(self):
        for portal in self.portals:
            if (portal.pos - self.player.pos).length() < 40:
                self._enter_portal(portal)
                return

    def _tick_whirl(self, eff, dt):
        """Krieger-Ultimate: Schaden an alle Gegner in 90px Umkreis (5 ticks/s)."""
        if not hasattr(self, '_whirl_tick'):
            self._whirl_tick = 0
        self._whirl_tick += 1
        if self._whirl_tick % 6 != 0:  # ~10 fps tick
            return
        p = self.player
        for e in list(self.enemies):
            if (e.pos - p.pos).length() <= 90:
                self.hit_enemy(e, eff['damage'] * 0.6)

    def _meteor_strike(self):
        """Magier-Ultimate: Massiver AoE-Einschlag."""
        spec = self._meteor_pending
        self._meteor_pending = None
        if spec is None:
            return
        pos = spec['pos']
        radius = spec['radius']
        damage = spec['damage']
        for e in list(self.enemies):
            d = (e.pos - pos).length()
            if d <= radius:
                falloff = 1.0 - 0.5 * (d / radius)
                self.hit_enemy(e, damage * falloff, dmg_type='fire')
        # Massive Explosion
        self.spawn_particles(pos.x, pos.y, 100, (255, 100, 30),
                             life_max=1.2, size_max=10, gravity=80)
        self.spawn_particles(pos.x, pos.y, 50, (255, 220, 100),
                             life_max=0.8, size_max=6)
        self.shake = max(self.shake, 20)
        snd.play('boss_intro', volume=0.8)

    def _cold_mirror_wave(self, wave):
        """Update #184: Moench-Keystone „Kalter Spiegel" — verzoegerte
        zweite/dritte Frostnova-Welle. Mini-Wrapper, nutzt den gespeicherten
        Snapshot fuer Position/Radius/Schaden."""
        from . import progression as _prog
        from . import effects as _fx2
        p = self.player
        eff = _prog.effective(p)
        pos = wave['pos']
        radius = wave['radius']
        dmg_mult = wave['dmg_mult']
        skill_mult = wave['skill_mult']
        apply_frost = wave['apply_frost']
        for e in list(self.enemies):
            d = (e.pos - pos).length()
            if d > radius or e.dying:
                continue
            if self.grid is not None and not self.grid.has_los(
                    pos.x, pos.y, e.pos.x, e.pos.y):
                continue
            dmg = (eff['damage'] * dmg_mult * eff['cold_dmg']
                   * skill_mult)
            self.hit_enemy(e, dmg, crit=False, dmg_type='cold')
            if apply_frost:
                _fx2.apply(self, e, 'frost', stacks=3)
            else:
                e.slow_timer = 2.0
                e.slow_factor = 0.5
        for i in range(28):
            a = (i / 28) * math.tau
            self.particles_push(pos.x + math.cos(a) * radius * 0.3,
                                pos.y + math.sin(a) * radius * 0.3,
                                math.cos(a) * 180, math.sin(a) * 180,
                                (150, 200, 240), 0.5, 3)

    def _innkeeper_dialog(self):
        """Story-Dialog beim Wirt: zeigt Story-Kapitel je Fortschritt.

        Update #158: Mojibake-Fix (verlorene Umlaute) + Lore-Konkretheit
        (PLAN Regel 1) — „Held"/„Schattenfürst" sind generic-fantasy,
        ersetzt durch Velgrad-Vokabular (Aithein-berührt, Im-Nesh).
        """
        chapters = [
            ('Willkommen, Verbannter',
             'Bleib eine Weile am Feuer. Da draußen atmet die Salzküste.'),
            ('Erste Schritte',
             'Du hast den Salzhüter gefällt. Velharn hörte — die Glasgoldenen Ruinen warten.'),
            ('Aithein-berührt',
             'Drei Wunden gelesen, drei Aspekte berührt. Im-Nesh atmet wieder.'),
            ('Legende',
             'Du bist eine Legende geworden. Selbst die Toten murmeln deinen Namen.'),
        ]
        done = len(self.player.completed_dungeons)
        idx = min(done, len(chapters) - 1)
        title, text = chapters[idx]
        self.toast(f'{title}', (220, 200, 120))
        # Längere Story als zweite Toast
        self.toast_queue.append([text, (220, 220, 200), 7.0])

    def _tick_traps(self, dt):
        """Wenn Spieler auf Trap-Tile steht: Schaden je nach Typ."""
        self._trap_tick_timer -= dt
        if self._trap_tick_timer > 0:
            return
        self._trap_tick_timer = 0.5
        cx, cy = self.grid.world_to_cell(self.player.pos.x, self.player.pos.y)
        for tx, ty, ttype in self.grid.traps:
            if tx == cx and ty == cy:
                self._trigger_trap(ttype, tx, ty)
                break

    def _trigger_trap(self, ttype, cx, cy):
        base = 5 + self.player.level * 2
        p = self.player
        if ttype == 'spike':
            self.damage_player(base * 0.6)
        elif ttype == 'fire':
            import math
            phase = pygame.time.get_ticks() * 0.005 + cx * 0.5 + cy * 0.3
            if math.sin(phase) > 0.3:
                self.damage_player(base)
                fx.apply(self, p, 'burn', stacks=2)
        elif ttype == 'arrow':
            self.damage_player(base * 1.2)
        elif ttype == 'plate':
            self.damage_player(base * 1.4)
            self.shake = max(self.shake, 6)
        # ---- Biom-Hazards ----
        elif ttype == 'sumpf_pool':
            # Verlangsamt Spieler stark
            p.slow_timer = max(p.slow_timer, 1.5)
            p.slow_factor = min(p.slow_factor, 0.5)
        elif ttype == 'lava_pool':
            # Update #41/#43: weiter reduziert — User: „Man stirbt noch immer
            # in der Lava Welt". Damage 0.15 → 0.06, KEIN Burn-Stack mehr,
            # 1s invuln-Buffer + Floater jedes Mal (nicht nur einmal).
            self.damage_player(base * 0.06)
            p.invuln = max(p.invuln, 0.4)
            self.floaters.append(Floater(
                p.pos.x, p.pos.y - 30,
                'LAVA!', (255, 80, 30)))
        elif ttype == 'ice_patch':
            # Rutscht: setze player.target weiter in Bewegungsrichtung
            if p.moving:
                diff = p.target - p.pos
                if diff.length() > 1:
                    n = diff.normalize()
                    # Schub in dieselbe Richtung
                    self.move_entity(p, n.x * 40, n.y * 40)
        elif ttype == 'quicksand':
            # Slow + Damage
            p.slow_timer = max(p.slow_timer, 1.0)
            p.slow_factor = min(p.slow_factor, 0.6)
            self.damage_player(base * 0.3)
        elif ttype == 'bone_pile':
            # Slow + kleine Damage
            p.slow_timer = max(p.slow_timer, 1.0)
            p.slow_factor = min(p.slow_factor, 0.7)

    def _interact(self):
        """F-Taste: NPC, Dungeon-Portal, Outpost-Portal, Town-Portal.

        Update #146 (User-Report „mehrere Menüs gleichzeitig"):
        Distance-based-Priority — alle Interactables in Reichweite werden
        gesammelt und der NÄHESTE gewinnt. Vorher feuerte das erste
        gefundene → Stele zwischen NPC und Spieler stahl Klick.
        """
        if self.area == 'town' or self.area == 'outpost':
            # Update #146: Alle Interactables sammeln + nach Distanz
            # sortieren. Priority-Tiebreaker bei gleicher Distanz: NPC
            # > Portal > Stele > Lore-Tafel (NPC bevorzugt weil Dialog
            # interaktiver ist als Stein).
            candidates = []
            ppos = self.player.pos
            # NPCs (Radius via town_mod.npc_in_range — ca. 60 px)
            npc = town_mod.npc_in_range(self.player, self.npcs)
            if npc is not None:
                d2 = (npc.pos - ppos).length_squared()
                candidates.append((d2, 0, 'npc', npc))
            # Dungeon-Portale (Radius ~50)
            dp = town_mod.dungeon_portal_in_range(
                self.player, self.dungeon_portals)
            if dp is not None:
                d2 = (dp.pos - ppos).length_squared()
                candidates.append((d2, 1, 'dportal', dp))
            # Outpost-Portale (Radius 45)
            for op_portal in self.outpost_portals:
                if (op_portal.pos - ppos).length() < 45:
                    d2 = (op_portal.pos - ppos).length_squared()
                    candidates.append((d2, 1, 'oportal', op_portal))
            # Outpost-Return-Portal
            rp = self.outpost_return_portal
            if rp and (rp.pos - ppos).length() < 45:
                d2 = (rp.pos - ppos).length_squared()
                candidates.append((d2, 1, 'return', rp))
            # Mahnmal-Stele (Radius 70)
            for t in self.tiles:
                if getattr(t, 'kind', None) != 'mahnmal_stele':
                    continue
                dx = ppos.x - t.x; dy = ppos.y - t.y
                d2 = dx * dx + dy * dy
                if d2 < 70 * 70:
                    candidates.append((d2, 2, 'stele', t))
            # Sortiere nach (priority_class, distance²) — NPC (0) gewinnt
            # immer gegen Stele (2) selbst wenn Stele näher ist.
            candidates.sort(key=lambda c: (c[1], c[0]))
            if not candidates:
                # Last-Dungeon-Statue als Fallback (keine Range-Sammlung)
                if self.last_dungeon_pos is not None:
                    if (abs(ppos.x - 0) < 50
                            and abs(ppos.y - 200) < 50):
                        did, pos = self.last_dungeon_pos
                        self.enter_dungeon(did)
                        if self.grid and self.grid.is_walkable_world(
                                pos.x, pos.y):
                            self.player.pos = Vector2(pos)
                        self.toast('Zurück zum letzten Dungeon',
                                    GOLD_BRIGHT)
                return
            _, _, kind, obj = candidates[0]
            if kind == 'stele':
                snd.play('ui_mahnmal_activate', volume=0.7)
                if self.area == 'outpost':
                    self.modal = 'travel'
                else:
                    self.modal = 'shrine'
                    if hasattr(self.player, 'prog_altars_used'):
                        self.player.prog_altars_used += 1
                return
            if kind == 'dportal':
                from .constants import DUNGEONS
                spec = DUNGEONS[obj.dungeon_id]
                if self.player.level < spec['level_req']:
                    self.floaters.append(Floater(
                        ppos.x, ppos.y - 30,
                        f'Benötigt Stufe {spec["level_req"]}',
                        (200, 80, 80)))
                else:
                    self.enter_dungeon(obj.dungeon_id)
                return
            if kind == 'oportal':
                if getattr(obj, '_locked', False):
                    # Update #156 (ROADMAP T2.4): zentralisierter
                    # Akt-Gating-Check via progression.akt_block_reason.
                    from . import outposts as _op
                    cfg = _op.OUTPOSTS.get(obj.outpost_key, {})
                    akt = cfg.get('akt', 1)
                    reason = progression.akt_block_reason(self.player, akt)
                    region = cfg.get("region_name", "?")
                    if reason:
                        msg = f'🔒 {region} — {reason}'
                    else:
                        msg = f'🔒 {region} noch verschlossen.'
                    self.toast(msg, (220, 150, 100))
                    try:
                        snd.play('ui_click', volume=0.3)
                    except Exception:
                        pass
                    return
                self.enter_outpost(obj.outpost_key)
                return
            if kind == 'return':
                self.enter_town()
                return
            # kind == 'npc' — Fall-through zum NPC-Handler unten
            if False:
                pass   # placeholder, NPC-Handler kommt unten
            # NPC-Handler:
            if True:
                # Update #135: Wenn dieser NPC eine final-RETURN-Stage
                # hat (Quest fertig zum Abgeben) → Quest-Turn-In-Modal
                # statt direktem on_talk-Auto-Advance.  Spieler sieht
                # erst Belohnungs-Preview.
                if self.quest_log is not None:
                    final_st = self._quest_ready_to_turn_in(npc.name)
                    if final_st is not None:
                        self._quest_turnin_state = final_st
                        self._quest_turnin_npc = npc.name
                        self.modal = 'quest_turnin'
                        self._show_npc_greeting(npc)
                        return
                # Quest-Trigger: Talk-Event (advanced stage / offer)
                if self.quest_log is not None:
                    quests_mod.on_talk(self, npc.name)
                # NPC-Dialog-Bubble vor Modal — Lore aus Voice-Lines-Pool
                self._show_npc_greeting(npc)
                if npc.kind == 'vendor':
                    self.shop_ui.maybe_restock(self.player.level)
                    self.modal = 'shop'
                elif npc.kind == 'stash':
                    self.modal = 'stash'
                elif npc.kind == 'mystic':
                    self.modal = 'skilltree'
                    # Update #184: Atlas-View beim NPC-Mystic-Open zentrieren
                    self.atlas_ui.open(self)
                elif npc.kind == 'smith':
                    # PLAN J-10: Otreth Hohlauge = Gemcutter, nicht Schmied.
                    # Lore: graviert Uncut-Gems und levelt Skill-Gems.
                    if npc.name == 'Otreth Hohlauge':
                        self.modal = 'gemcutter'
                    else:
                        self.modal = 'crafting'
                elif npc.kind == 'quest':
                    self.modal = 'questlog'
                elif npc.kind == 'innkeeper':
                    self._innkeeper_dialog()
                return
            # Update #146: Old code path entfernt — alle Town/Outpost-
            # Interactables werden jetzt über die Distance-Sort-Logik
            # oben aufgelöst.  Last-Dungeon-Statue-Fallback bleibt:
            if self.last_dungeon_pos is not None:
                # Statue ist bei (0, 200)
                if abs(self.player.pos.x - 0) < 50 and abs(self.player.pos.y - 200) < 50:
                    did, pos = self.last_dungeon_pos
                    self.enter_dungeon(did)
                    # Spieler zurück zur letzten Position teleportieren falls walkable
                    if self.grid and self.grid.is_walkable_world(pos.x, pos.y):
                        self.player.pos = Vector2(pos)
                    self.toast(f'Zurück zum letzten Dungeon', GOLD_BRIGHT)
                    return
        else:
            # Update #201 (User-Bug-Fix): Dungeon-F-Resolution mit
            # Closest-First + Priority statt naivem stele-zuerst-Check.
            #
            # Vorher: mahnmal_stele wurde ZUERST gecheckt mit Radius 50.
            # Problem: Event-Rooms in dungeon_events.py (lore_echo,
            # treasure_hoard, underworld_rift) platzieren Stelen in
            # 40-80 px Abstand zu Lore-Tafeln/Truhen/Riss. Der Spieler
            # drueckte F um zu lesen -> Stele fing ab und teleportierte
            # ihn zurueck nach Brassweir, weg von Loot/Lore.
            #
            # Fix: Beide in Range sammeln + nahesten waehlen, dabei
            # Lore-Tafel leichte Priority (Read ist destruktionsfrei,
            # Stele-Teleport ist irreversibel und kostet den Run).
            candidates = []
            ppos = self.player.pos
            for t in self.tiles:
                kind = getattr(t, 'kind', None)
                if kind == 'lore_tablet':
                    dx = ppos.x - t.x; dy = ppos.y - t.y
                    d2 = dx * dx + dy * dy
                    if d2 < 60 * 60:
                        candidates.append((d2, 0, 'tablet', t))
                elif kind == 'mahnmal_stele':
                    dx = ppos.x - t.x; dy = ppos.y - t.y
                    d2 = dx * dx + dy * dy
                    if d2 < 50 * 50:
                        candidates.append((d2, 1, 'stele', t))
            candidates.sort(key=lambda c: (c[1], c[0]))
            if candidates:
                _, _, kind, t = candidates[0]
                if kind == 'tablet':
                    if not getattr(t, 'lore_read', False):
                        t.lore_read = True
                        self.player.lore_fragments += 1
                        self.toast('+1 Lore-Fragment (N: Codex)',
                                   (200, 170, 100))
                        quests_mod.on_interact_decor(self, t)
                        log = getattr(self, 'quest_log', None)
                        if log is not None and getattr(t, 'lore_text', ''):
                            log.discovered_lore.add(t.lore_text)
                    self.toast(t.lore_text, (220, 200, 160))
                    self.toast_queue[-1][2] = 8.0
                    return
                if kind == 'stele':
                    self.toast(
                        'Die Stele erinnert den Pfad — zurueck nach Brassweir.',
                        (220, 200, 160))
                    self.toast_queue[-1][2] = 4.0
                    self.enter_town()
                    return
            self._try_enter_portal()

    def _auto_sort_inventory(self):
        """Sortiert Inventar nach Rarity (Unique > Rare > Magic > Common), dann Slot."""
        from .constants import RARITY_COLOR
        order = {'unique': 0, 'rare': 1, 'magic': 2, 'common': 3}
        items = [it for it in self.player.inventory if it is not None]
        items.sort(key=lambda i: (order.get(i.rarity, 9), i.slot, -i.ilvl))
        # Wieder einfüllen
        for i in range(len(self.player.inventory)):
            self.player.inventory[i] = items[i] if i < len(items) else None
        self.toast('Inventar sortiert', (200, 200, 200))

    def _cycle_dungeon_tier(self):
        """T-Taste in Town: zykliert next_tier für nahe Dungeon-Portal."""
        dp = town_mod.dungeon_portal_in_range(self.player, self.dungeon_portals)
        if dp is None:
            return
        max_unlocked = self.dungeon_tier.get(dp.dungeon_id, 1)
        cur = self.next_tier.get(dp.dungeon_id, 1)
        cur = cur + 1 if cur < max_unlocked else 1
        self.next_tier[dp.dungeon_id] = cur
        name = {1: 'Normal', 2: 'Heroisch', 3: 'Mythisch'}[cur]
        self.toast(f'Schwierigkeit: {name}', (200, 200, 80))

    def _cycle_loot_filter(self):
        order = ['off', 'common', 'magic']
        cur = self.player.loot_filter
        try:
            idx = order.index(cur)
        except ValueError:
            idx = 0
        self.player.loot_filter = order[(idx + 1) % len(order)]
        label = {
            'off':    'Loot-Filter: AUS (alles aufsammeln)',
            'common': 'Loot-Filter: Gewöhnliche ignorieren',
            'magic':  'Loot-Filter: nur Seltene+ aufsammeln',
        }[self.player.loot_filter]
        self.floaters.append(Floater(
            self.player.pos.x, self.player.pos.y - 30, label, (200, 200, 200)))

    def _open_town_portal(self):
        """Update #43: D4-Style Town-Portal (User-Wunsch).

        Erstellt ein animiertes Portal nahe Spieler, das zurück nach
        Brassweir führt. Cooldown verhindert Spam.
        """
        if getattr(self, '_town_portal_cd', 0) > 0:
            self.toast('Town-Portal noch nicht bereit', (180, 180, 180))
            return
        if not self.portals:
            self.portals = []
        # Cleanup alter Town-Portale (max 1 aktiv)
        self.portals = [pt for pt in self.portals
                        if getattr(pt, 'biome', None) != 'town']
        # Position 60 px vor dem Spieler in Blick-Richtung
        # Update #147 (User-Report „Portale in der Wand"): robuster
        # Wall-Check mit Player-Radius (statt 12) + Decor-Check + Fallback
        # auf MEHRERE Distance-Versuche (60, 45, 30, 15 px).
        import math as _m
        portal_r = 18   # Portal-Größe für Collision
        px, py = self.player.pos.x, self.player.pos.y   # Default: Player-Pos
        for try_dist in (60, 45, 30, 15):
            tx = self.player.pos.x + _m.cos(self.player.facing) * try_dist
            ty = self.player.pos.y + _m.sin(self.player.facing) * try_dist
            blocked = False
            if self.grid is not None and self.grid.collide_circle(
                    tx, ty, portal_r):
                blocked = True
            if not blocked and self._decor_collides(tx, ty, portal_r):
                blocked = True
            if not blocked:
                px, py = tx, ty
                break
        portal = Portal(px, py, 'town')
        self.portals.append(portal)
        # Spawn-Particles + Sound
        self.spawn_particles(px, py, 40, (140, 200, 240),
                              life_max=0.9, size_max=6)
        self.spawn_particles(px, py, 16, (255, 240, 200),
                              life_max=0.6, size_max=4)
        try:
            snd.play('cast_lightning', volume=0.5)
        except Exception:
            pass
        self.toast('TOWN-PORTAL geöffnet — laufe hinein', (140, 200, 240))
        self._town_portal_cd = 4.0  # 4s Spam-Cooldown

    def _enter_portal(self, portal):
        """Update #43: D4-Style Town-Portal — zurück nach Brassweir.

        Update #121-Fix: ehemalige Wave-Progression-Pfade (für Survival-
        Biome-Wechsel) entfernt. Es gibt nur noch Town-Portale; alle
        anderen Portale wurden über DungeonPortal/OutpostPortal ersetzt.
        """
        if portal.biome == 'town':
            self.portals = [pt for pt in self.portals if pt is not portal]
            self.enter_town()

    # ---------- Hintergrund-Musik + Ambient + Snapshots ----------
    def _update_music(self):
        """Wechselt Musik basierend auf area + Boss-Status + Modal-State.

        Snapshot-Logik (Audio-Bibel Teil 1.4):
          - dying  → DEATH_TRANSITION
          - boss-Encounter aktiv → BOSS_INTRO
          - Modal offen (Inventar/Tree/Shop/Crafting/Pause) → MENU_OPEN
          - sonst DEFAULT
        Boss-Encounter steuert auch den Music-Track-Wechsel (Salzhüter/Vehren
        haben eigene Tracks — vom boss_encounter.start_encounter geladen).
        """
        # Update #102 (Audit-Fix): N-07 Crossfade-Tick muss jeden Frame
        # gerufen werden, sonst läuft ein pending Crossfade nie zu Ende.
        try:
            snd.tick_crossfade(16)
        except Exception:
            pass
        # Update #43: Titel-Screen-Musik (User „Im Hauptmenu ist keine Musik")
        if self.state == 'title':
            snd.play_music('title')
            snd.stop_ambient()
            return
        if self.state != 'playing':
            snd.stop_music()
            snd.stop_ambient()
            return

        # 1) Snapshot ermitteln (Priorität: dying > boss > menu > default)
        if self.player.dying:
            snap = 'DEATH_TRANSITION'
        elif self.boss_encounter is not None and \
                self.boss_encounter['t'] < self.boss_encounter['duration']:
            snap = 'BOSS_INTRO'
        elif self.modal in ('inventory', 'skilltree', 'crafting',
                             'shop', 'stash', 'settings', 'pause'):
            snap = 'MENU_OPEN'
        else:
            snap = 'DEFAULT'
        snd.apply_snapshot(snap)

        # 2) Music-Track wählen (Boss-Encounter überschreibt via eigenen
        #    music_swap-Key; sonst Region-Music aus dem Biome).
        if self.boss_encounter is not None and not self.boss_encounter['boss'].dying:
            return  # Track wurde von start_encounter geladen, lass laufen
        boss_alive = any(getattr(e, 'is_boss', False) and not e.dying
                         for e in self.enemies)
        if boss_alive:
            snd.play_music('boss')
        elif self.area == 'town':
            snd.play_music('town')
        elif self.area == 'outpost':
            # Outposts haben kein eigenes Music-Asset → biome-Music nutzen
            # (mit FALLBACK_BIOME für wound_*/hollow_word).
            from .regions import fallback_biome
            snd.play_music(snd.music_for_biome(fallback_biome(self.biome)))
        else:
            snd.play_music(snd.music_for_biome(self.biome))

    def _spawn_ambient_motes(self, dt):
        """Update #40: Biome-spezifische Floating-Motes spawnen.

        - crypt:  Salzstaub-Motes (blass-blau)
        - frost:  Glas-Gold-Motes (Akt 2 Lore: Goldstaub-Cloud)
        - lava:   Asche-Funken (rot-orange)
        - swamp:  Sporen (grün)
        - astral: Sterne-Glitter (blass-lila)
        - desert: Sand-Wirbel (gelb-braun)
        Spawn-Rate ist niedrig — gibt subtile Atmosphäre ohne Spam.
        """
        if self.state != 'playing' or self.area != 'dungeon':
            return
        if not hasattr(self, '_ambient_mote_timer'):
            self._ambient_mote_timer = 0.0
        self._ambient_mote_timer += dt
        if self._ambient_mote_timer < 0.15:
            return
        self._ambient_mote_timer = 0.0
        biome_motes = {
            'crypt':  ((180, 200, 220), 1.5),   # Salzstaub
            'frost':  ((255, 220, 130), 2.0),   # Goldstaub-Cloud
            'lava':   ((255, 140, 50), 1.8),    # Asche-Funken
            'swamp':  ((140, 220, 140), 1.5),   # Sporen
            'astral': ((200, 170, 255), 1.8),   # Star-Glitter
            'desert': ((220, 200, 130), 1.5),   # Sand
        }
        cfg = biome_motes.get(self.biome)
        if cfg is None:
            return
        color, size_base = cfg
        # 1-3 Motes pro Tick, um Player herum, driften aufwärts
        n = random.randint(1, 3)
        from .effects import ParticleLayer
        for _ in range(n):
            ox = random.uniform(-SCREEN_W // 2, SCREEN_W // 2)
            oy = random.uniform(-SCREEN_H // 2, SCREEN_H // 2)
            self.particles.append(Particle(
                self.player.pos.x + ox,
                self.player.pos.y + oy,
                random.uniform(-8, 8),
                random.uniform(-25, -10),  # aufwärts driften
                color, random.uniform(2.5, 4.5),
                random.uniform(1.0, size_base),
                gravity=-3,
                layer=ParticleLayer.AMBIENT,
            ))

    def _update_ambient(self, dt):
        """Spielt periodisch düstere Ambient-Sounds je nach Biom.

        Update #31: Lang-Tracks (`ambient_*`) blockieren weiteres Spawning
        bis sie ausklingen (sonst überlappen 30s-Loops mit 5s-Intervall).
        Update #43: Fire-Loops nach max 25 s hart abbrechen.
        """
        if self.state != 'playing':
            return
        if not hasattr(self, '_ambient_timer'):
            self._ambient_timer = 4.0
        # Update #43: Long-Track-Cutoff. Wenn ein Fire-/Lava-Long-Loop
        # angefangen hat, brechen wir ihn nach 25 s ab — sonst spielt der
        # 5-Min-Track weiter, selbst wenn Spieler nicht am Feuer steht.
        if getattr(self, '_ambient_long_timer', 0) > 0:
            self._ambient_long_timer -= dt
            if self._ambient_long_timer <= 0:
                try:
                    import pygame as _pg
                    _pg.mixer.Channel(1).fadeout(800)
                except Exception:
                    pass
        self._ambient_timer -= dt
        if self._ambient_timer > 0:
            return
        # Wenn Ambient-Channel busy → Timer kurz verlängern, kein neuer
        # Sound auf den laufenden draufpacken.
        try:
            import pygame
            if pygame.mixer.Channel(1).get_busy():
                self._ambient_timer = 2.0
                return
        except Exception:
            pass
        # Pool je Biom + Boss
        boss_alive = any(getattr(e, 'is_boss', False) and not e.dying
                         for e in self.enemies)
        if boss_alive:
            # Update #38: weniger Growls auch bei Boss-Active
            pool = ['heartbeat', 'whisper', 'whisper']
        else:
            pool = snd.BIOME_AMBIENT_POOL.get(self.biome, [])
        if pool:
            picked = random.choice(pool)
            snd.play_ambient(picked)
            # Update #43: Fire-/Long-Loops nach 25 s abbrechen.
            if picked in ('ambient_fire_loop', 'firewood_burning'):
                self._ambient_long_timer = 25.0
            # Lange Tracks (ambient_*) → Re-Trigger erst nach 30-60s.
            # Kurze SFX (drip/whisper/creak) → 5-12s wie vorher.
            if picked.startswith('ambient_'):
                self._ambient_timer = random.uniform(30.0, 60.0)
                return
        self._ambient_timer = random.uniform(5.0, 12.0)

    def _update_player_breath(self, dt):
        """Update #186: Player-Breath-SFX pro Frame ticken.

        Atem-Cycle wird vom Game-State gesteuert:
          calm     — idle/town/exploration (5-8 s zwischen Atemzuegen)
          stressed — Aggro-Mob in Range ODER kuerzlich Damage (3-4 s)
          ragged   — HP < 30 % (1.8-2.6 s, hechelnd)

        Biome-Shape kommt aus self.biome (crypt/frost/lava/desert/...).
        Wenn Voice-Channel oder Dialog laeuft, skippen wir — Atem soll
        nicht ueber NPC-Dialog kreischen.
        """
        if self.state != 'playing':
            return
        # Skip wenn Player tot/im Modal/Cutscene
        if self.player.hp <= 0:
            return
        if getattr(self, 'modal', None) not in (None, 'pause'):
            return
        if getattr(self, 'cutscene', None) is not None:
            return
        # Skip wenn Voice-Channel (Dialog) busy — Atem ueberlagert sonst
        try:
            import pygame as _pg
            if _pg.mixer.Channel(30).get_busy():
                return
        except Exception:
            pass
        if not hasattr(self, '_breath_timer'):
            self._breath_timer = 2.0
            self._breath_last_intensity = 'calm'
        self._breath_timer -= dt
        if self._breath_timer > 0:
            return
        # Intensitaet aus Player-State + Combat
        from . import progression as _prog
        eff = _prog.effective(self.player)
        hp_frac = self.player.hp / max(1, eff['hp_max'])
        in_combat = bool(getattr(self, 'aggro_count', 0)) or any(
            getattr(e, 'ai_state', None) == 'aggro'
            for e in getattr(self, 'enemies', ()))
        if hp_frac < 0.30:
            intensity = 'ragged'
            next_delay = random.uniform(1.8, 2.6)
        elif in_combat:
            intensity = 'stressed'
            next_delay = random.uniform(3.0, 4.0)
        else:
            intensity = 'calm'
            next_delay = random.uniform(5.0, 8.0)
        self._breath_last_intensity = intensity
        biome = getattr(self, 'biome', 'town')
        try:
            snd.play_player_breath(biome, intensity)
        except Exception:
            pass
        self._breath_timer = next_delay

    # ---------- Toasts (Achievement/Notify) ----------
    def toast(self, text, color=(255, 220, 80)):
        # Update #37: 3.5s → 2.5s default. Toasts überleben kürzer,
        # weniger Screen-Clutter.
        # Update #134 (User-Screenshot): identische Toasts dedupen —
        # statt 3× „X ist gefallen" stacken, verlängern wir den
        # existierenden Toast auf 2.5 s.
        for existing in self.toast_queue:
            if existing[0] == text:
                existing[2] = max(existing[2], 2.5)
                return
        self.toast_queue.append([text, color, 2.5])

    def _tick_toasts(self, dt):
        # Update #134: Toast-Dedup-Pass. Falls mehrere Toasts identischen
        # Text haben (z.B. „Schwester-Wache ist gefallen" 3×), behalten
        # wir nur den mit der längsten Restzeit.  Verhindert Stacking
        # durch direkte `toast_queue.append`-Aufrufer die die `toast()`-
        # Methode umgehen.
        seen = {}
        for t in self.toast_queue[:]:
            key = t[0]
            if key in seen:
                # Längste Restzeit gewinnt
                if t[2] > seen[key][2]:
                    self.toast_queue.remove(seen[key])
                    seen[key] = t
                else:
                    self.toast_queue.remove(t)
            else:
                seen[key] = t
        for t in self.toast_queue[:]:
            t[2] -= dt
            if t[2] <= 0:
                self.toast_queue.remove(t)
        for n in self.event_notifications[:]:
            n['time_left'] -= dt
            if n['time_left'] <= 0:
                self.event_notifications.remove(n)
        for ev in self.event_log[:]:
            ev['time_left'] -= dt
            if ev['time_left'] <= 0:
                self.event_log.remove(ev)
        # Update #132 (B-18): Region-Transition Tick
        if self.region_transition is not None:
            self.region_transition['t'] -= dt
            if self.region_transition['t'] <= 0:
                self.region_transition = None
        # Visible-Feedback decay
        if self.crit_flash_t > 0:
            self.crit_flash_t = max(0.0, self.crit_flash_t - dt)
        if self.hit_vignette_t > 0:
            self.hit_vignette_t = max(0.0, self.hit_vignette_t - dt)
        # Update #28: Low-HP-Breathing-Loop. Spielt alle ~5s wenn HP < 30 %.
        try:
            from . import progression
            eff = progression.effective(self.player)
            hp_frac = (self.player.hp / max(1, eff['hp_max']))
            self._low_hp_breath_t = getattr(self, '_low_hp_breath_t', 0.0) - dt
            if self.state == 'playing' and hp_frac < 0.30 and self.player.hp > 0:
                if self._low_hp_breath_t <= 0:
                    self._low_hp_breath_t = 5.0
                    snd.play('breath_low_hp', volume=0.7)
        except Exception:
            pass

    def push_event_notification(self, kind, title, sub=None,
                                  color=(255, 220, 80), duration=2.8):
        """Größere zentrierte Notification (G-12/G-13).

        Erlaubte `kind`-Werte: 'levelup', 'quest', 'pickup_rare',
        'currency', 'story'. UI rendert sie gestackt im oberen Drittel.
        """
        self.event_notifications.append({
            'kind':       kind,
            'title':      title,
            'sub':        sub,
            'color':      color,
            'time_left':  float(duration),
            'total':      float(duration),
        })

    def _spawn_footprint(self, p, dt):
        """Update #138 (V-06): Spawnt einen biome-spezifischen Footprint.

        Footprints alternieren links/rechts vom Player-Center via
        `_footprint_side`-Flag.  Pro Biome eigene Farbe + Decor-Stil:

          - frost:  weiß-bläulich (im Schnee/Glas-Boden)
          - desert: helles Sand-Beige (im Sand)
          - lava:   schwarz-grau (Asche-Abdrücke)

        Lifetime 1.5 s mit Fade-Out.  Maximal 80 aktive Footprints
        (älteste werden überschrieben — kein unbounded growth).
        """
        # Side-Offset senkrecht zur Bewegungsrichtung
        facing = getattr(p, 'facing', 0.0)
        # Normal zur Bewegung: facing ± π/2
        side_sign = 1 if self._footprint_side == 0 else -1
        self._footprint_side = (self._footprint_side + 1) % 2
        nx = math.cos(facing + math.pi / 2) * side_sign * 5
        ny = math.sin(facing + math.pi / 2) * side_sign * 5
        self.footprints.append({
            'x':      p.pos.x + nx,
            'y':      p.pos.y + ny,
            'biome':  self.biome,
            'age':    0.0,
            'life':   1.5,
            'angle':  facing,
        })
        # Cap
        if len(self.footprints) > 80:
            del self.footprints[:len(self.footprints) - 80]

    def _spawn_loot_pickup_anim(self, start_x, start_y, color, kind='item'):
        """Update #136 (O-23): Spawnt eine Pickup-Spline-Animation.

        Item fliegt in einem Bezier-Bogen (mit vertex_offset für Höhe)
        von der Loot-Position zum Spieler.  Visuell-only — der eigentliche
        Pickup-Effekt (Gold/Item/Skill) wird sofort angewendet.
        """
        import random as _r
        # Bogen-Höhe variiert leicht — sieht organisch aus
        offset = _r.uniform(-30, -50)
        # Side-sway zufällig links/rechts (für Bezier-Tangente)
        offset_x = _r.uniform(-20, 20)
        self._loot_animations.append({
            'start_x':     float(start_x),
            'start_y':     float(start_y),
            'color':       color,
            'kind':        kind,
            't':           0.0,
            'total':       0.35,
            'arc_y':       offset,
            'arc_x':       offset_x,
        })

    def _tick_loot_animations(self, dt):
        """Update #136 (O-23): Tickt + filtert die Pickup-Spline-Anims."""
        for anim in self._loot_animations[:]:
            anim['t'] += dt
            if anim['t'] >= anim['total']:
                self._loot_animations.remove(anim)

    def _tick_footprints(self, dt):
        """Update #138 (V-06): Tickt + filtert Footprints."""
        for fp in self.footprints[:]:
            fp['age'] += dt
            if fp['age'] >= fp['life']:
                self.footprints.remove(fp)

    def _draw_footprints(self):
        """Update #138 (V-06): Rendert Footprints unter Player/Entities.

        Pro Biome eigene Farbe + Decor-Form (Sand=Halbmond, Frost=
        weißer Punkt, Lava=Asche-Strich).
        """
        if not self.footprints:
            return
        # Biome-Color-Map
        FOOT_COLORS = {
            'frost':  (200, 220, 240),   # weiß-bläulich
            'desert': (220, 200, 150),   # sand-beige
            'lava':   (50, 40, 36),      # asche-grau
        }
        for fp in self.footprints:
            col = FOOT_COLORS.get(fp['biome'], (180, 180, 180))
            sx, sy = self.w2s_xy(fp['x'], fp['y'])
            # Update #190: Off-Screen-Culling
            if not (-30 < sx < SCREEN_W + 30 and -30 < sy < SCREEN_H + 30):
                continue
            # Alpha-Fade letzte 50 % der Lifetime
            t = fp['age'] / fp['life']
            if t < 0.5:
                alpha = 180
            else:
                alpha = int(180 * (1.0 - (t - 0.5) / 0.5))
            if alpha <= 0:
                continue
            # Footprint-Surface: rotated ellipse für „Schuh"-Look
            ang = fp['angle']
            footstep = pygame.Surface((10, 6), pygame.SRCALPHA)
            pygame.draw.ellipse(footstep, (*col, alpha),
                                 (0, 0, 10, 6))
            rotated = pygame.transform.rotate(
                footstep, -math.degrees(ang))
            self.screen.blit(rotated,
                              (int(sx) - rotated.get_width() // 2,
                               int(sy) - rotated.get_height() // 2))

    def _draw_loot_animations(self):
        """Update #136 (O-23): Rendert flying loot-icons in Spline-Bogen
        von start-pos zur live-Player-Position.  Quad-Bezier mit
        Mittelpunkt = (start+target)/2 + arc-offset.
        """
        p_pos = self.player.pos
        for anim in self._loot_animations:
            t = anim['t'] / anim['total']
            t = max(0.0, min(1.0, t))
            # Quad-Bezier P(t) = (1-t)²·P0 + 2(1-t)t·P1 + t²·P2
            sx0, sy0 = anim['start_x'], anim['start_y']
            ex, ey = p_pos.x, p_pos.y - 30   # leicht über Player-Kopf
            mx_w = (sx0 + ex) * 0.5 + anim['arc_x']
            my_w = (sy0 + ey) * 0.5 + anim['arc_y']
            inv_t = 1.0 - t
            wx = inv_t * inv_t * sx0 + 2 * inv_t * t * mx_w + t * t * ex
            wy = inv_t * inv_t * sy0 + 2 * inv_t * t * my_w + t * t * ey
            sx, sy = self.w2s_xy(wx, wy)
            sx, sy = int(sx), int(sy)
            # Größe ramps down kurz vor Pickup (Squish-Effekt)
            scale = 1.0 - t * 0.4
            r = max(2, int(5 * scale))
            color = anim['color']
            # Trail-Glow
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            for k in range(3, 0, -1):
                a = int(140 / k * (1.0 - t * 0.5))
                pygame.draw.circle(glow, (*color, a),
                                    (r * 2, r * 2), r + k)
            self.screen.blit(glow, (sx - r * 2, sy - r * 2))
            # Center-Icon (Diamond für Item, Kreis für Gold/Orb)
            kind = anim['kind']
            if kind == 'item' or kind == 'skill_gem':
                pts = [(sx, sy - r), (sx + r, sy),
                       (sx, sy + r), (sx - r, sy)]
                pygame.draw.polygon(self.screen, color, pts)
                pygame.draw.polygon(self.screen, (255, 255, 255), pts, 1)
            else:
                pygame.draw.circle(self.screen, color, (sx, sy), r)
                pygame.draw.circle(self.screen, (255, 255, 255),
                                    (sx - 1, sy - 1), max(1, r // 3))

    def _tick_town_ambient(self, dt):
        """Update #135: Brassweir-Atmosphäre via periodische Mini-Events.

        Zwei Mechaniken:
          1. **Möwen-Flyby**: alle 30-50 s zieht ein 5-7-Möwen-Schwarm
             diagonal über die Stadt + leise `seagull_cry`-SFX.  Reine
             Atmosphäre, kein Gameplay.
          2. **NPC-Murmel**: wenn der Spieler länger als 1.5 s im Radius
             von 140 px um einen NPC steht (ohne F zu drücken),
             chance 25 % auf eine leise Voice-Line aus dem `lore`-Pool.
        """
        import random as _r
        # 1. Möwen-Flyby-Timer
        if not hasattr(self, '_gull_event_t'):
            self._gull_event_t = _r.uniform(20.0, 30.0)
        self._gull_event_t -= dt
        if self._gull_event_t <= 0:
            self._gull_event_t = _r.uniform(30.0, 50.0)
            self._spawn_gull_flyby()
        # 2. NPC-Murmel — pro NPC einen Cooldown
        for npc in getattr(self, 'npcs', ()):
            if not hasattr(npc, '_murmur_cd'):
                npc._murmur_cd = _r.uniform(8.0, 16.0)
                npc._near_player_t = 0.0
            dx = self.player.pos.x - npc.pos.x
            dy = self.player.pos.y - npc.pos.y
            d2 = dx * dx + dy * dy
            if d2 < 140 * 140:
                npc._near_player_t += dt
            else:
                npc._near_player_t = 0.0
            npc._murmur_cd -= dt
            if (npc._murmur_cd <= 0 and npc._near_player_t > 1.5
                    and _r.random() < 0.25):
                npc._murmur_cd = _r.uniform(20.0, 40.0)
                npc._near_player_t = 0.0
                self._npc_murmur(npc)

    def _spawn_gull_flyby(self):
        """Update #135: 5-7 weiße Möwen-Particles ziehen diagonal
        über die Stadt (off-screen → off-screen).  Mit play_at-Cry
        damit der Sound positional ist.
        """
        import random as _r
        n_gulls = _r.randint(5, 7)
        # Start oben-links/rechts, Ziel diagonal entgegengesetzt
        start_side = _r.choice([-1, 1])
        base_x = self.player.pos.x + start_side * 800
        base_y = self.player.pos.y - 400
        # 7 Möwen in Schwarm-Formation, leicht versetzt
        for i in range(n_gulls):
            offset_x = i * 60 * _r.uniform(0.5, 1.5)
            offset_y = i * 20 * _r.uniform(-0.5, 1.0)
            vx = -start_side * _r.uniform(80, 120)
            vy = _r.uniform(20, 40)
            self.particles.append(Particle(
                base_x + offset_x, base_y + offset_y,
                vx, vy,
                (240, 240, 230),
                _r.uniform(10.0, 14.0),
                _r.uniform(3.0, 4.5),
                gravity=0.0))
        # SFX am Spawn-Punkt
        try:
            snd.play_at(self, 'seagull_cry',
                         base_x, base_y, volume=0.4)
        except Exception:
            try:
                snd.play('seagull_cry', volume=0.3)
            except Exception:
                pass

    def _npc_murmur(self, npc):
        """Update #135: NPC murmelt eine leise Voice-Line wenn der
        Spieler im Radius steht.  Pool: `lore` (kurze Gedanken).
        """
        try:
            from . import sounds as _snd
            VOICE_KEY = {
                'Korven Vor':                'korven',
                'Bruder Helst':              'helst',
                'Vossharil':                 'vossharil',
                'Tameris':                   'tameris',
                'Otreth Hohlauge':           'otreth',
                'Mara die Mahnerin':         'mara',
                'Inquisitor-General Vehren': 'vehren',
            }
            vk = VOICE_KEY.get(npc.name)
            if vk:
                _snd.play_voice(vk, 'lore', volume=0.55)
        except Exception:
            pass

    def trigger_region_transition(self, biome=None, area_override=None,
                                    show_loading_card=False):
        """Update #132 (B-18): Startet die 1.6 s Lower-Third-Animation
        beim Map-Wechsel.  Region-Daten kommen aus `regions.REGIONS`;
        Fallback wenn das Biome dort nicht registriert ist.

        Update #139 (X-11): Wenn `show_loading_card=True` (typisch beim
        Dungeon-Entry), wird zusätzlich ein Lore-Loading-Card-Overlay
        gerendert (Klassen-Portrait + Region-Name + Aspekt-Sigil +
        Lore-Quote + Tip).  Bei Town/Outpost-Entry bleibt es bei der
        kleinen Lower-Third-Animation.

        `biome` override für outpost/dungeon; default `self.biome`.
        """
        from . import regions as _reg
        bk = biome or self.biome
        rinfo = _reg.REGIONS.get(bk)
        if rinfo is None:
            # Fallback: nur Biome-Key als Name
            self.region_transition = {
                'name':  bk.title(),
                'sub':   '',
                'color': (200, 180, 140),
                't':     1.6,
                'total': 1.6,
            }
            if show_loading_card:
                self._populate_loading_card(bk, rinfo)
            return
        # Akt-Marker als Sub-Line
        akt = rinfo.get('akt', 0)
        if akt == 0:
            sub = rinfo.get('short_desc', '')[:80]
        else:
            sub = f'Akt {akt}  ·  {rinfo.get("faction", "")}'
        self.region_transition = {
            'name':  rinfo.get('region_name', bk.title()),
            'sub':   sub,
            'color': rinfo.get('accent_color', (220, 180, 110)),
            't':     1.6,
            'total': 1.6,
        }
        if show_loading_card:
            self._populate_loading_card(bk, rinfo)

    def _populate_loading_card(self, biome, rinfo):
        """Update #139 (X-11): füllt die Loading-Card-Felder der aktuellen
        region_transition mit Lore-Quote + Tip + Aspekt-Sigil.
        """
        if self.region_transition is None:
            return
        try:
            from . import tips as _tips
            from . import quotes as _q
        except ImportError:
            return
        # Tip: bevorzugt biome+class-kontextuell
        cls = getattr(self.player, 'cls', None)
        tip = _tips.pick_tip_for_context(biome=biome, cls=cls)
        # Lore-Quote: pick aus VELGRAD_VOICE_LINES_POOL über quotes.pick_death_quote
        # ... nicht ideal, weil Death-Quotes spezifisch sind.  Wir
        # benutzen einen Origin-/Lore-Quote aus dem class_voicelines-Pool
        # statt dessen.  Fallback: rinfo.short_desc als Quote.
        quote = None
        try:
            quote = _q.class_origin_quote(cls) if cls else None
        except Exception:
            pass
        if not quote and rinfo is not None:
            quote = rinfo.get('short_desc', '')
        self.region_transition['loading_card'] = {
            'biome':  biome,
            'cls':    cls,
            'tip':    tip['text'] if tip else None,
            'quote':  (quote or '').strip()[:200],
        }

    def push_event_log(self, text, color=(220, 220, 220), duration=4.5):
        """Pickup-/Story-Mini-Log rechts unten (G-11)."""
        # Max 5 Einträge → ältesten kicken
        self.event_log.insert(0, {
            'text': text, 'color': color,
            'time_left': float(duration),
        })
        while len(self.event_log) > 6:
            self.event_log.pop()

    def _check_achievements(self):
        newly = ach_mod.check_all(self)
        for a in newly:
            self.toast(f'★ {a["name"]} ★  +{a["reward"]}g', (255, 220, 100))

    # ---------- Bewegung mit Wand-/Decor-Kollision ----------
    def _decor_collides(self, x, y, r):
        """Prüft Kollision mit decor (die collide_radius haben)."""
        for t in self.tiles:
            cr = getattr(t, 'collide_radius', 0)
            if cr <= 0:
                continue
            dx = x - t.x
            dy = y - t.y
            if dx * dx + dy * dy < (cr + r) * (cr + r):
                return True
        return False

    def _slide_against_decor(self, x, y, dx, dy, r):
        """Update #147 (User-Report „durch Wände laufen"): Sub-Stepping
        bei großen Moves verhindert Tunneling durch Decor-Walls.
        """
        move_len = math.hypot(dx, dy)
        # Decor-Walls haben typisch collide_radius=10 → max-step = 10 px
        max_step = 10.0
        if move_len > max_step:
            n_steps = int(math.ceil(move_len / max_step))
            step_dx = dx / n_steps
            step_dy = dy / n_steps
            cur_x, cur_y = x, y
            for _ in range(n_steps):
                cur_x, cur_y = self._decor_slide_step(
                    cur_x, cur_y, step_dx, step_dy, r)
            return cur_x, cur_y
        return self._decor_slide_step(x, y, dx, dy, r)

    def _decor_slide_step(self, x, y, dx, dy, r):
        """Single-Step-Decor-Slide ohne Sub-Division."""
        nx, ny = x + dx, y + dy
        if not self._decor_collides(nx, ny, r):
            return nx, ny
        if not self._decor_collides(nx, y, r):
            return nx, y
        if not self._decor_collides(x, ny, r):
            return x, ny
        return x, y

    def move_entity(self, entity, dx, dy, radius=None):
        """Bewegt entity.pos um (dx,dy) mit Wand-Gleiten."""
        r = radius if radius is not None else getattr(entity, 'radius', 14)
        x, y = entity.pos.x, entity.pos.y
        # Erst gegen Dungeon-Wände (falls Grid)
        if self.grid is not None:
            x, y = self.grid.slide_move(x, y, dx, dy, r)
        else:
            x, y = x + dx, y + dy
        # Dann gegen decor (Häuser, Säulen, etc.) — gleichmäßig in beiden Modi
        x, y = self._slide_against_decor(entity.pos.x, entity.pos.y,
                                          x - entity.pos.x, y - entity.pos.y, r)
        entity.pos.x, entity.pos.y = x, y

    def _detect_step_material(self):
        """N-11 (Update #52): Footstep-Material-Detection.

        Prüft was unter dem Spieler liegt (Decor + Grid-Trap-Tiles) und
        returnt den passenden Step-Sound-Key.  Fallback ist Biome-Step.

        Material-Priorität (höher zuerst):
        - water: salt_puddle, blood_pool (lore-konform: Salzwunden + Blut)
        - mud: sumpf_pool (Wurzelgrab-Sumpf)
        - wood: pier_post, fishing_net (Brassweir-Pier)
        - metal: anvil, plate-Trap
        """
        p = self.player
        px, py = p.pos.x, p.pos.y
        # 1) Decor-Material-Check (Tiles in Nähe < 28 px)
        WATER_KINDS = {'salt_puddle', 'lava_pool', 'sumpf_pool'}
        WOOD_KINDS = {'pier_post', 'fishing_net'}
        METAL_KINDS = {'anvil'}
        MUD_KINDS = {'sumpf_pool'}
        for t in self.tiles:
            dx = t.x - px
            dy = t.y - py
            if dx * dx + dy * dy > 28 * 28:
                continue
            if t.kind == 'sumpf_pool':
                return 'step_mud'
            if t.kind in WATER_KINDS:
                return 'step_water'
            if t.kind in WOOD_KINDS:
                return 'step_wood'
            if t.kind in METAL_KINDS:
                return 'step_metal'
        # 2) Trap-Tile-Check für Plate/Spike (metal-ish)
        if self.grid is not None:
            cx, cy = self.grid.world_to_cell(px, py)
            for tx, ty, ttype in self.grid.traps:
                if tx == cx and ty == cy:
                    if ttype in ('plate', 'spike', 'arrow'):
                        return 'step_metal'
                    if ttype == 'lava_pool':
                        return 'step_water'  # heißes Splash-Geräusch
                    break
        # 3) Biome-Fallback (Velgrad-Akte: jedes Biome hat eigenen Step-Sound,
        # gemappt auf Phase-2-AI-Footsteps via SFX_PHASE2_HINTS in sounds.py)
        return {
            'town':         'step_town',     # Brassweir Pier-Holz
            'crypt':        'step_crypt',    # Salzkueste Stein
            'frost':        'step_frost',    # Akt 2 Glasgolden Marmor
            'lava':         'step_lava',     # Akt 3 Aschenfelder
            'swamp':        'step_mud',      # Akt 4 Wurzelgrab
            'astral':       'step_astral',   # Akt 5 Velharn Spiegel
            'desert':       'step_desert',   # Akt 1b Zhar-Eth Sand
            'wound_salt':   'step_water',    # Akt 6a Salzwunde
            'wound_ash':    'step_lava',     # Akt 6b Aschwunde
            'wound_hollow': 'step_void',     # Akt 6c Hohlwunde
            'hollow_word':  'step_void',     # Akt 7 Hohlwort
        }.get(self.biome, 'step_crypt')

    def world_walkable(self, x, y, r=14):
        if self.grid is not None and self.grid.collide_circle(x, y, r):
            return False
        if self._decor_collides(x, y, r):
            return False
        return True

    def _unstuck_player(self, p):
        """Update #43: Pusht den Spieler aus blockierendem Decor heraus."""
        self._unstuck_entity(p)

    def _unstuck_entity(self, e):
        """Pusht eine Entity (Spieler ODER Gegner) aus blockierendem Decor.

        User-Feedback Update #43: „Spieler bleiben manchmal an Gegenständen
        hängen weil sie entweder im Weg sind oder schlecht platziert" UND
        „Gegner stecken zu oft in irgendwelchen Gegenständen".

        Findet das nächste blockende Decor und schiebt die Entity radial
        nach außen, bis sie nicht mehr kollidiert.
        """
        r = getattr(e, 'radius', 14)
        # 1) Finde nächstes blockendes Decor
        nearest = None
        best_d = 1e9
        for t in self.tiles:
            cr = getattr(t, 'collide_radius', 0)
            if cr <= 0:
                continue
            dx = e.pos.x - t.x
            dy = e.pos.y - t.y
            dist2 = dx * dx + dy * dy
            if dist2 < (cr + r) * (cr + r) and dist2 < best_d:
                nearest = t
                best_d = dist2
        if nearest is None:
            return
        # 2) Push radial weg vom Decor-Zentrum
        dx = e.pos.x - nearest.x
        dy = e.pos.y - nearest.y
        d = math.hypot(dx, dy)
        if d < 0.01:
            dx, dy = random.uniform(-1, 1), random.uniform(-1, 1)
            d = math.hypot(dx, dy) or 1.0
        cr = getattr(nearest, 'collide_radius', 0)
        target_dist = cr + r + 1
        nx, ny = dx / d, dy / d
        new_x = nearest.x + nx * target_dist
        new_y = nearest.y + ny * target_dist
        # Falls neue Pos in Wand wäre, mehrere Richtungen testen
        if self.grid is not None and self.grid.collide_circle(
                new_x, new_y, r):
            for ang in (0, math.pi / 2, math.pi, 3 * math.pi / 2,
                        math.pi / 4, 3 * math.pi / 4):
                tx = nearest.x + math.cos(ang) * target_dist
                ty = nearest.y + math.sin(ang) * target_dist
                if not (self.grid.collide_circle(tx, ty, r)
                        or self._decor_collides(tx, ty, r)):
                    new_x, new_y = tx, ty
                    break
        e.pos.x, e.pos.y = new_x, new_y

    # ---------- Hilfsfunktionen für andere Module ----------
    def spawn_particles(self, x, y, count, color, life_max=0.7,
                        size_max=5, gravity=0, layer=fx.ParticleLayer.GAMEPLAY,
                        friendly=True):
        """Spawnt Partikel (Default: GAMEPLAY-Layer, nicht cullable).

        Für atmosphärische Effekte spawn_ambient() nutzen — die werden
        durch Settings-Slider und Dynamic-Culling reduziert.

        C-10: Wenn `tactical_reduce`=True UND `friendly`=True (default),
        wird der Partikel-Count auf 50 % reduziert. Gegnerische VFX
        (friendly=False, gesetzt in enemy-/boss-code) bleiben unverändert.
        """
        cfg = fx.LAYER_CONFIG.get(layer, fx.LAYER_CONFIG[fx.ParticleLayer.GAMEPLAY])
        if cfg['cullable']:
            # AMBIENT: Slider + Dynamic-Culling
            density = fx.ambient_density_multiplier(self)
        else:
            # GAMEPLAY/TELEGRAPH/UI_OVERLAY: niemals reduziert
            density = 1.0
        # C-10: Tactical-Reduce für friendly-VFX
        if friendly and self.settings.get('tactical_reduce', False):
            density *= 0.5
        n = max(1, int(count * density))
        # J-13 (Update #64): Particle-Pool-Reuse statt new Particle()
        pool = self._particle_pool
        for _ in range(n):
            a = random.uniform(0, math.tau)
            s = random.uniform(40, 180)
            life = random.uniform(0.3, life_max)
            size = random.uniform(2, size_max)
            vx, vy = math.cos(a) * s, math.sin(a) * s
            if pool:
                pt = pool.pop()
                pt.reset(x, y, vx, vy, color, life, size, gravity, layer)
            else:
                pt = Particle(x, y, vx, vy, color, life, size, gravity,
                              layer=layer)
            self.particles.append(pt)

    def request_flash(self, intensity=1.0):
        """C-11: Photosensitive Flash-Limiter (max 3 Flashes/s).

        Callsites die bright-white-flashes triggern (`_damage_flash`,
        `crit_flash_t`, Lightning-strikes) sollen das hier durchleiten.
        Returnt die *effektive* Intensität (0..intensity), 0 wenn der
        Frame-Budget für diese Sekunde aufgebraucht ist.

        Mit `photosensitive`=False: ungeprüft durchgereicht.
        """
        if not self.settings.get('photosensitive', False):
            return intensity
        # Fenster pro Sekunde
        now = pygame.time.get_ticks() * 0.001
        if now - self._flash_window_t >= 1.0:
            self._flash_window_t = now
            self._flash_window_count = 0
        if self._flash_window_count >= 3:
            return 0.0  # Budget aufgebraucht
        self._flash_window_count += 1
        # Photosensitive dimmt auf 50 %
        return intensity * 0.5

    def spawn_ambient(self, x, y, count, color, life_max=0.7,
                      size_max=5, gravity=0):
        """Convenience: atmosphärische Partikel (cullable via Settings/Auto)."""
        self.spawn_particles(x, y, count, color, life_max=life_max,
                             size_max=size_max, gravity=gravity,
                             layer=fx.ParticleLayer.AMBIENT)

    def particles_push(self, x, y, vx, vy, color, life, size, gravity=0,
                       layer=fx.ParticleLayer.GAMEPLAY):
        # J-13 (Update #64): Pool-Reuse statt new Particle()
        pool = self._particle_pool
        if pool:
            pt = pool.pop()
            pt.reset(x, y, vx, vy, color, life, size, gravity, layer)
        else:
            pt = Particle(x, y, vx, vy, color, life, size, gravity,
                          layer=layer)
        self.particles.append(pt)

    # Combat-Delegates für skills/enemies-Module
    def hit_enemy(self, e, dmg, crit=False, dmg_type='physical'):
        combat.hit_enemy(self, e, dmg, crit=crit, dmg_type=dmg_type)

    def damage_player(self, dmg, dmg_type='physical', source=None):
        combat.damage_player(self, dmg, dmg_type=dmg_type, source=source)

    # ============================================================
    # UPDATE
    # ============================================================
    def update(self, dt):
        self._click_grace -= dt
        self._tick_toasts(dt)
        # Audit #179 B.5: SpatialGrid einmal pro Frame rebuilden. AoE/Chain/
        # Pack-Death-Queries unten nutzen `enemy_grid.query_radius()` statt
        # linearer Iteration. Rebuild ist O(N) ~5us bei 50 Enemies — billiger
        # als eine einzige O(N^2)-Operation pro Frame.
        if self.enemies:
            self.enemy_grid.rebuild(self.enemies)
        else:
            self.enemy_grid.clear()
        # Audit #179 C.8: One-Shot-Toast wenn Crash-Recovery verfuegbar ist.
        # Erscheint nur einmal im Title-State, damit der User weiss, dass F8
        # das Autosave wiederherstellt.
        if (not self._autosave_toast_shown
                and self.pending_autosave_recovery
                and self.state == 'title'):
            rec = self.pending_autosave_recovery
            age_min = int(rec.get('age_minutes', 0))
            self.toast(
                f'⚠ Crash erkannt — F8 für Autosave (Slot {rec["slot"]}, '
                f'{age_min} Min alt) wiederherstellen.',
                (255, 200, 80))
            self._autosave_toast_shown = True
        # ROADMAP T1.3: Dialog-Modal Word-Reveal Timer
        if self.modal == 'dialog':
            try:
                self.dialog_ui.update(dt)
            except Exception:
                pass
        # V-01..V-08 (Update #168): Surface-FX + Cloth-Sim Banner.
        try:
            self.surface_fx.update(dt)
        except Exception:
            pass
        # Wind-Phase fuer Cloth global driften
        self._wind_t += dt
        wind_strength = 25.0 + 15.0 * math.sin(self._wind_t * 0.4)
        for cloth in self.cloth_banners:
            try:
                cloth.update(dt, wind_x=wind_strength)
            except Exception:
                pass
        # U-09 Lightning-Flash Decay (frame-rate-unabhaengig)
        if self._lightning_flash_t > 0:
            self._lightning_flash_t = max(0.0, self._lightning_flash_t - dt * 4.0)
        if self._casting_t > 0:
            self._casting_t = max(0.0, self._casting_t - dt)
        # X-03 Combat-Zoom-Tick
        if self.state == 'playing':
            aggro = any(getattr(e, 'aggro', False)
                        and not getattr(e, 'dying', False)
                        and (e.pos - self.player.pos).length() < 400
                        for e in getattr(self, 'enemies', ()))
            if aggro:
                self._combat_active_left = 4.0
            else:
                self._combat_active_left = max(0.0, self._combat_active_left - dt)
            target_zoom = 0.92 if (self._combat_active_left > 0
                                    and self.settings.get('camera_combat_zoom', True)) else 1.0
            # smooth-lerp
            self._combat_zoom_t += (target_zoom - self._combat_zoom_t) * min(1.0, dt * 2.5)
        # X-09 Cutscene-Player update
        if self.cutscene_player.is_playing:
            try:
                self.cutscene_player.update(dt, self)
            except Exception:
                pass
        # Update #32: Spielzeit-Tracker für Memorial-Panel
        if self.state == 'playing':
            self.player.prog_play_time_s = (
                getattr(self.player, 'prog_play_time_s', 0.0) + dt)
            # Bestiary-Sync von quest_log → Progression-Tracker
            log = getattr(self, 'quest_log', None)
            if (log is not None
                    and hasattr(self.player, 'prog_bestiary_seen')):
                self.player.prog_bestiary_seen |= log.bestiary_seen
                self.player.prog_lore_read = set(log.discovered_lore)
            # Update #116 (WELT_AUFBAU 3.1): Per-Frame-Tick für ESCORT/
            # DEFEND/TIMED-Stages.  QuestLog.tick prüft alle aktiven
            # Quests auf zeit- oder positions-basierten Fortschritt.
            if log is not None:
                log.tick(dt, self)
        self._update_music()
        self._update_ambient(dt)
        self._update_player_breath(dt)
        self._spawn_ambient_motes(dt)
        # Boss-Intro Timer (läuft mit echtem dt)
        if self.boss_intro is not None:
            self.boss_intro['timer'] -= dt
            if self.boss_intro['timer'] <= 0:
                self.boss_intro = None
        # PLAN E-04: Boss-Intro-Skip (Hold-Space) — nur bei wiederholten Encounters
        if self.state == 'playing':
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                try:
                    from . import boss_encounter as _enc
                    _enc.request_skip(self, dt)
                except Exception:
                    pass
                # X-09 (Update #168): SPACE skipt Cutscene
                if self.cutscene_player.is_playing:
                    self.cutscene_player.request_skip(self)
        # Spielzeit (echtes dt für Tag/Nacht)
        if self.state == 'playing':
            ach_mod.init_stats(self)
            self.stats['time_played'] = self.stats.get('time_played', 0.0) + dt
        # Slow-Motion (Boss-Death-Cinematic)
        if self.slow_mo_left > 0:
            self.slow_mo_left -= dt
            dt = dt * 0.3   # alle nachfolgenden Updates langsamer
        if self.boss_flash > 0:
            self.boss_flash = max(0, self.boss_flash - dt * 0.6)
        # Settings: Screen-Shake
        if not self.settings.get('screen_shake', True):
            self.shake = 0
        if self.shake > 0.3:
            self.camera_shake_offset = (random.uniform(-self.shake, self.shake),
                                        random.uniform(-self.shake, self.shake))
            self.shake *= 0.85
        else:
            self.shake = 0
            self.camera_shake_offset = (0, 0)
        # A-10 (Update #59): Camera-Tilt + Atem-Pulse während Death-Transition.
        # Gibt der Tod-Sequenz spürbares Gewicht (Briefing A.3 „Atem/
        # Herzschlag-Pulse").  Tilt-Offset additiv auf shake_offset.
        if self.player.dying and self.death_phase == 'transition':
            t = self.death_phase_t
            # Atem-Sinus 0.5 Hz, fällt mit Progress
            breath_amp = max(0.0, 6.0 - t * 2.5)
            tilt_x = math.sin(t * 3.0) * breath_amp
            tilt_y = math.sin(t * 1.2) * (breath_amp * 0.7)
            ox, oy = self.camera_shake_offset
            self.camera_shake_offset = (ox + tilt_x, oy + tilt_y)

        if self.state != 'playing' or self.modal is not None:
            self._update_particles(dt)
            # Dungeon-Completion-Timer auch in Modals weiterticken
            if self.area == 'dungeon' and self._dungeon_done_timer > 0:
                self._dungeon_done_timer -= dt
                if self._dungeon_done_timer <= 0:
                    if self.modal == 'rune_choice' and self._rune_choices:
                        # Fallback: erste Rune nehmen
                        c = self._rune_choices[0]
                        runes_mod.apply_rune(self.player, c['skill'], c['id'])
                        self.modal = None
                    self.enter_town()
            return

        # Hover-Erkennung
        if self.modal is None:
            mx, my = pygame.mouse.get_pos()
            wpos = self.s2w(mx, my)
            best = None
            best_d = 1e9
            for e in self.enemies:
                d = (e.pos - wpos).length()
                if d < e.radius + 12 and d < best_d:
                    best, best_d = e, d
            self.hovered_enemy = best
        else:
            self.hovered_enemy = None

        # Update #43: Town-Portal-Cooldown ticken + Auto-Enter wenn Spieler
        # sehr nahe drüber läuft (D4-Style — kein F-Druck nötig).
        if getattr(self, '_town_portal_cd', 0) > 0:
            self._town_portal_cd -= dt
        for _pt in list(getattr(self, 'portals', [])):
            if getattr(_pt, 'biome', None) == 'town':
                if (_pt.pos - self.player.pos).length() < 22:
                    self._enter_portal(_pt)
                    break
        # N-01 (Update #67): Skill-Sound-Phase-Queue ticken (Body/Tail
        # zeitverzögerte Layers werden hier abgefeuert).
        try:
            snd.tick_phase_queue()
        except Exception:
            pass
        # N-09 (Update #64): Music-Phase-Duck-Recovery.  Nach Boss-Phase-
        # Transition wird die Music kurz gedämpft + ein Bell-Cue layered;
        # hier ramped es zurück auf das Original-Volume in 1.2 s.
        # N-08 (Update #65): Item-Music-Mute-Override.  Equipped Unique-Items
        # können `item.music_mute` setzen (0.0..1.0 = Multiplikator).  Wird
        # in `_apply_item_music_mod()` ausgewertet UND mit N-09-Duck combined.
        duck = getattr(self, '_music_phase_duck', None)
        if duck is not None:
            duck['left'] -= dt
            if duck['left'] <= 0:
                try:
                    snd.set_music_volume(
                        self._apply_item_music_mod(duck['orig']))
                except Exception:
                    pass
                self._music_phase_duck = None
            else:
                t = 1.0 - duck['left']
                vol = duck['orig'] * (0.35 + 0.65 * min(1.0, t / 1.0))
                try:
                    snd.set_music_volume(self._apply_item_music_mod(vol))
                except Exception:
                    pass
        # W-11 (Update #48): NPC-Schedules ticken (Korven/Tameris Tag/Nacht)
        if self.area == 'town':
            from . import town as _t
            _t.tick_npc_schedules(self)
            # Update #131 (Y-01): Tutorial-Auto-Advance-Heuristiken
            from . import tutorial as _tut
            _tut.tick(self)
            # Update #135: Stadt-Ambient — Möwen-Flyby + NPC-Murmel
            self._tick_town_ambient(dt)
        # Update #137 (Z-06): Auto-Save-Tick — alle 60 s ein Snapshot
        # in das separate `AUTOSAVE_PATH`.  Nur während aktivem Spiel
        # (kein Modal, kein Dying, kein Title).
        if (self.state == 'playing' and not self.player.dying
                and self.modal is None):
            self._autosave_timer += dt
            if self._autosave_timer >= save_mod.AUTOSAVE_INTERVAL_S:
                self._autosave_timer = 0.0
                try:
                    save_mod.write_autosave(self)
                except Exception:
                    pass
        # B-07 (Update #49): Breadcrumb-Drop alle 0.4 s + Aging.
        # Spuren leben 30 s, danach fadet komplett aus.  Im Town irrelevant.
        if self.area == 'dungeon':
            self._breadcrumb_drop_t -= dt
            if self._breadcrumb_drop_t <= 0:
                self._breadcrumb_drop_t = 0.4
                self.breadcrumbs.append((
                    self.player.pos.x, self.player.pos.y, 0.0))
                # Cap auf 120 (ältester wird verworfen)
                if len(self.breadcrumbs) > 120:
                    self.breadcrumbs.pop(0)
        # Aging
        if self.breadcrumbs:
            self.breadcrumbs = [
                (x, y, age + dt) for (x, y, age) in self.breadcrumbs
                if age + dt < 30.0
            ]
        self._update_player(dt)
        self._update_enemies(dt)
        self._update_projectiles(dt)
        self._update_loot(dt)
        self._update_particles(dt)
        # Update #136 (O-23): Pickup-Spline-Anims ticken
        self._tick_loot_animations(dt)
        # Update #138 (V-06): Footprints ticken
        self._tick_footprints(dt)
        # E-05 (Update #60): Arena-Features ticken (Lava-Streams, Crypt-Graves)
        if self.area == 'dungeon' and self.arena_features:
            self._tick_arena_features(dt)
        # Update #27: Dungeon-Events (Ambush, Altar, Rune-Circle, ...)
        if self.area == 'dungeon':
            from . import dungeon_events as _dev
            _dev.tick_player_in_room(self)
            _dev.tick_event_buffs(self, dt)
        # AoE-Telegraph-Decals (PLAN C-05/C-06/C-07): Wind-Up → Activate → Lifetime
        fx.update_decals(self, dt)
        # Boss-Encounter-Cinematic + Phase-Trigger (PLAN E-Block)
        from . import boss_encounter as _enc
        _enc.tick_encounter(self, dt)
        # Wetter (AMBIENT-Layer: respektiert Density-Slider + Dynamic-Cull)
        self.weather.update(dt, self.camera,
                            ambient_density=fx.ambient_density_multiplier(self))
        # Blut-Pfützen altern
        for bp in self.blood_pools[:]:
            bp.age += dt
            if bp.age >= bp.life:
                self.blood_pools.remove(bp)
        # Earthquake-Aftershocks (Spieler-Slam)
        for shock in self.pending_aftershocks[:]:
            shock['timer'] -= dt
            if shock['timer'] <= 0:
                # Detonation
                for e in list(self.enemies):
                    if (e.pos - shock['pos']).length() <= shock['radius']:
                        self.hit_enemy(e, shock['damage'], dmg_type='physical')
                self.spawn_particles(shock['pos'].x, shock['pos'].y, 60,
                                      (180, 120, 60), life_max=1.0, size_max=8,
                                      gravity=100)
                self.shake = max(self.shake, 12)
                snd.play('hit_heavy', volume=0.9)
                self.pending_aftershocks.remove(shock)

        # Komet-Einschläge
        for cmt in self.pending_comets[:]:
            cmt['timer'] -= dt
            if cmt['timer'] <= 0:
                # Massiver Cold-AoE
                for e in list(self.enemies):
                    d = (e.pos - cmt['pos']).length()
                    if d <= cmt['radius']:
                        falloff = max(0.4, 1.0 - d / cmt['radius'])
                        self.hit_enemy(e, cmt['damage'] * falloff,
                                        dmg_type='cold')
                        if e in self.enemies:
                            from . import effects as _fx
                            _fx.apply(self, e, 'frost', stacks=4)
                # Riesige Explosion
                self.spawn_particles(cmt['pos'].x, cmt['pos'].y, 120,
                                      (180, 220, 255), life_max=1.4, size_max=10,
                                      gravity=60)
                self.spawn_particles(cmt['pos'].x, cmt['pos'].y, 40,
                                      (255, 255, 255), life_max=0.8, size_max=6)
                self.shake = max(self.shake, 18)
                snd.play('boss_intro', volume=0.7)
                self.pending_comets.remove(cmt)

        # Schwarze Löcher: ziehen Spieler + Damage in Mitte
        for bh in self.black_holes[:]:
            bh['time_left'] -= dt
            bh['tick_cd'] -= dt
            if bh['time_left'] <= 0:
                self.black_holes.remove(bh)
                continue
            to_player = bh['pos'] - self.player.pos
            d = to_player.length()
            if 0 < d < bh['radius']:
                # Pull
                n = to_player.normalize()
                pull_force = bh['pull'] * (1 - d / bh['radius']) * dt
                self.move_entity(self.player, n.x * pull_force, n.y * pull_force)
            if d < 40 and bh['tick_cd'] <= 0:
                bh['tick_cd'] = 0.3
                self.damage_player(bh['dmg'])

        # Ground-Cracks ticken + Schaden
        eff_h = progression.effective(self.player)
        for c in self.ground_cracks[:]:
            c['time_left'] -= dt
            c['tick_cd'] -= dt
            if c['time_left'] <= 0:
                self.ground_cracks.remove(c)
                continue
            if c['tick_cd'] <= 0:
                c['tick_cd'] = 0.3
                # Schaden wenn Spieler auf Crack-Linie steht
                to_player = self.player.pos - c['pos']
                proj_len = to_player.x * c['dir'].x + to_player.y * c['dir'].y
                if 0 <= proj_len <= c['len']:
                    closest_x = c['pos'].x + c['dir'].x * proj_len
                    closest_y = c['pos'].y + c['dir'].y * proj_len
                    perp_dist = ((self.player.pos.x - closest_x) ** 2 +
                                  (self.player.pos.y - closest_y) ** 2) ** 0.5
                    if perp_dist < 22:
                        self.damage_player(c['dmg'])

        # Heal-Fields ticken
        # Update #43-bugfix: defensiv gegen malformed Einträge (User-Crash
        # KeyError 'time_left' — falls noch alte Format-Entries aus früheren
        # Sessions im List sind, ignorieren statt crashen).
        for hf in self.heal_fields[:]:
            if 'time_left' not in hf or 'pos' not in hf or 'radius' not in hf:
                self.heal_fields.remove(hf)
                continue
            hf['time_left'] -= dt
            if hf['time_left'] <= 0:
                self.heal_fields.remove(hf)
                continue
            if (hf['pos'] - self.player.pos).length() <= hf['radius']:
                heal = hf.get('heal_per_sec', 0) * dt
                if heal > 0:
                    self.player.hp = min(eff_h['hp_max'],
                                          self.player.hp + heal)
        # Update #121: Survival-Wellen-System entfernt; nur noch
        # Dungeon-Updates.
        if self.area == 'dungeon':
            self._update_dungeon(dt)
            self._update_events(dt)
        # Update #140: Camera-Logik mit Lookahead/Cursor-Lean/Crit-Pull/
        # Boss-Pan statt statischem Player-Follow.
        self._update_camera(dt)

    def _update_camera(self, dt):
        """Update #140 (X-01/X-02/X-04/X-05): Camera-Update mit 4
        Effekten:

        - X-01 Lookahead: Camera schiebt sich 30 % der Player-Velocity
          in Bewegungsrichtung vor (max ±60 px) → mehr Sichtbereich
          nach vorne beim Laufen.
        - X-02 Cursor-Lean: Camera zieht 15 % Richtung Mauszeiger
          (max ±40 px) → Casts/Ziele im Blick.
        - X-04 Crit-Zoom: Bei großen Crits wird die Camera kurz zum
          Target gepullt (decay mit slow_mo_left).
        - X-05 Boss-Death-Pan: Camera folgt dem sterbenden Boss
          statt dem Player für 1.8 s, mit Slow-Mo.
        """
        # Boss-Death-Pan hat höchste Priorität — überschreibt alle
        # anderen Camera-Effekte.
        if self._cam_boss_pan is not None:
            self._cam_boss_pan['t'] -= dt
            if self._cam_boss_pan['t'] <= 0:
                self._cam_boss_pan = None
                self.slow_mo_left = 0.0
            else:
                # Camera auf Boss-Position halten, kein Player-Follow
                bp = self._cam_boss_pan
                target = bp['boss_pos']
                # Smooth-Lerp Camera zur Boss-Position
                lerp_t = min(1.0, dt * 4.0)
                self.camera.x += (target.x - self.camera.x) * lerp_t
                self.camera.y += (target.y - self.camera.y) * lerp_t
                # Slow-Mo erzwungen während Pan
                self.slow_mo_left = max(self.slow_mo_left, 0.3)
                # Clear sonstige Offsets während Boss-Pan
                self._cam_offset_x *= 0.85
                self._cam_offset_y *= 0.85
                # Player-Prev für Lookahead refresh nach Pan-Ende
                self._cam_prev_player_pos = (self.player.pos.x,
                                              self.player.pos.y)
                return
        # Player-Follow Default
        self.camera = Vector2(self.player.pos)
        # X-01 Lookahead — basiert auf Player-Movement-Delta
        # Update #141 (User-Report): Setting-respecting + leicht
        # reduzierte Intensität (30% → 20%, Cap 60 → 45 px).
        prev_x, prev_y = self._cam_prev_player_pos
        vel_x = (self.player.pos.x - prev_x) / max(0.001, dt)
        vel_y = (self.player.pos.y - prev_y) / max(0.001, dt)
        self._cam_prev_player_pos = (self.player.pos.x,
                                       self.player.pos.y)
        if self.settings.get('camera_lookahead', True):
            look_x = max(-45.0, min(45.0, vel_x * 0.2))
            look_y = max(-45.0, min(45.0, vel_y * 0.2))
        else:
            look_x = look_y = 0.0
        # X-02 Cursor-Lean — Default OFF (Motion-Sickness-Trigger).
        # Update #141: Opt-In via Setting `camera_cursor_lean`.
        if self.settings.get('camera_cursor_lean', False):
            try:
                mx, my = pygame.mouse.get_pos()
                dx = mx - SCREEN_W * 0.5
                dy = my - SCREEN_H * 0.5
                lean_x = max(-40.0, min(40.0, dx * 0.15))
                lean_y = max(-40.0, min(40.0, dy * 0.15))
            except Exception:
                lean_x = lean_y = 0.0
        else:
            lean_x = lean_y = 0.0
        # X-04 Crit-Zoom-Pull — von Crit-Target weg-pullen (verstärkt
        # das „Hineinzoom"-Feeling).  Decay via slow_mo_left.
        crit_x = crit_y = 0.0
        if self._cam_crit_pull is not None and self.slow_mo_left > 0:
            tx, ty = self._cam_crit_pull
            # Pull-Intensity skaliert mit verbleibender slow_mo
            pull_factor = min(1.0, self.slow_mo_left / 0.18) * 35.0
            cdiff_x = tx - self.player.pos.x
            cdiff_y = ty - self.player.pos.y
            cd = math.hypot(cdiff_x, cdiff_y)
            if cd > 0.01:
                crit_x = (cdiff_x / cd) * pull_factor
                crit_y = (cdiff_y / cd) * pull_factor
        elif self.slow_mo_left <= 0:
            self._cam_crit_pull = None
        # X-09 (Update #168): Cutscene-Cam-Offset (vom CutscenePlayer
        # gesetzt waehrend camera_move-Steps).  Hat hoechste Prio nach
        # Boss-Pan.
        cut_x = getattr(self, '_cam_cutscene_x', 0.0)
        cut_y = getattr(self, '_cam_cutscene_y', 0.0)
        if not self.cutscene_player.is_playing:
            # Decay zurueck wenn Cutscene endete
            self._cam_cutscene_x *= 0.85
            self._cam_cutscene_y *= 0.85
        # Summe der Offsets, smooth-lerp zur Target-Position für
        # weiche Übergänge (kein abruptes Snap).
        target_ox = look_x + lean_x + crit_x + cut_x
        target_oy = look_y + lean_y + crit_y + cut_y
        lerp_t = min(1.0, dt * 8.0)
        self._cam_offset_x += (target_ox - self._cam_offset_x) * lerp_t
        self._cam_offset_y += (target_oy - self._cam_offset_y) * lerp_t

    def trigger_crit_zoom(self, target_x, target_y):
        """Update #140 (X-04): Trigger Crit-Zoom-Pull zur target-Position.
        Wird in combat.hit_enemy beim Crit + großem Damage aufgerufen.
        Decay automatisch mit slow_mo_left.
        """
        self._cam_crit_pull = (float(target_x), float(target_y))

    def trigger_boss_death_pan(self, boss):
        """Update #140 (X-05): Startet die 1.8 s Cinematic-Pan zum
        sterbenden Boss.  Camera fokussiert ihn, Slow-Mo erzwungen.
        """
        if boss is None or not hasattr(boss, 'pos'):
            return
        self._cam_boss_pan = {
            'boss_pos':  Vector2(boss.pos),
            'boss_ref':  boss,
            't':         1.8,
            'total':     1.8,
        }
        # Initial-Slow-Mo damit's gleich sichtbar ist
        self.slow_mo_left = max(self.slow_mo_left, 0.4)

    def _update_player(self, dt):
        p = self.player
        # Update #171: Physics-Step (no-op wenn pymunk fehlt oder disabled).
        # Macht Splitter + Throwables advance. Affektiert NICHT Player/Enemy-
        # Movement.
        if self.physics is not None:
            self.physics.step(dt)
        # Update #43: Auto-Unstuck — Spieler kann durch Decor-Spawn oder
        # Map-Transition in einem blockenden Decor landen (User-Feedback
        # „Spieler bleiben manchmal an Gegenständen hängen weil sie entweder
        # im Weg sind oder schlecht platziert"). Wenn die aktuelle Pos
        # blockiert ist → radial nach außen pushen bis frei.
        if self._decor_collides(p.pos.x, p.pos.y, p.radius):
            self._unstuck_player(p)
        # Update #165: Sprite-Animation-State advance (idle ↔ walk ↔
        # attack/hit/cast/death). Trigger-Calls fuer One-Shots passieren
        # an spezifischen Event-Stellen (Attack-Start, Damage-Taken, etc.)
        # weiter unten in dieser Funktion.
        try:
            p.anim_state.update(dt, p)
        except AttributeError:
            pass   # alte Player-Instanzen ohne anim_state (save-game-compat)
        # PLAN A-Block: Tod-Sequenz mit Damage-Type-Transition + Wake-Up.
        # Phase 1: 'transition' — Klassen-Sprite-Death-Anim (2.0 s) +
        #          Full-Screen-Transition-Overlay (1.2 s overlap)
        # Phase 2: 'wakeup_ready' — Quote-Display, Spieler klickt → reset.
        if p.dying:
            p.death_timer += dt
            if self.death_phase == 'none':
                self.death_phase = 'transition'
                self.death_phase_t = 0.0
                self.death_count = getattr(self, 'death_count', 0) + 1
                # Audio-Ducking (A-07): Music auf 25 % während Transition.
                try:
                    cur = snd.MUSIC_VOLUME
                    self._music_vol_before_death = cur
                    snd.set_music_volume(cur * 0.25)
                except Exception:
                    pass
                # A-10 (Update #59): Heartbeat-Pulse als Death-Accent.
                # Single-Shot, 1.6 s Pulse, parallel zur Transition-Anim.
                try:
                    snd.play_ambient('heartbeat', volume=0.9)
                except Exception:
                    pass
            self.death_phase_t += dt
            if p.death_timer > 2.0:
                self.state = 'dead'
                self.death_phase = 'wakeup_ready'
            return
        eff = progression.effective(p)

        p.attack_cd -= dt
        p.dodge_cd -= dt
        p.invuln -= dt
        p.dodge -= dt
        p.slow_timer -= dt
        # Update #34: Dodge-Charges-Regen + Trail-Tick
        dc_max = getattr(p, 'dodge_charges_max', 2)
        if getattr(p, 'dodge_charges', 0) < dc_max:
            regen_t = getattr(p, 'dodge_regen_t', 0.0)
            if regen_t > 0:
                p.dodge_regen_t = regen_t - dt
                if p.dodge_regen_t <= 0:
                    p.dodge_charges = min(dc_max,
                                            getattr(p, 'dodge_charges', 0) + 1)
                    if p.dodge_charges < dc_max:
                        p.dodge_regen_t = 4.0  # nächster Charge
        # Trail-Tick
        trail = getattr(p, '_dodge_trail', None)
        if trail:
            for tr in trail[:]:
                tr['age'] += dt
                if tr['age'] >= tr['life']:
                    trail.remove(tr)
        # Combo + Levelup-Invuln Timer
        if p.combo_buff_left > 0:
            p.combo_buff_left -= dt
        if p.levelup_invuln > 0:
            p.levelup_invuln -= dt
            p.invuln = max(p.invuln, 0.1)
        # Update #82: Flask-HoT/MoT-Effekte tick.
        self._tick_flask_effects(dt)
        # Ultimate-CD
        if hasattr(p, 'ult_cd') and p.ult_cd > 0:
            p.ult_cd -= dt
        # Time-Freeze CD
        if hasattr(p, 'tf_cd') and p.tf_cd > 0:
            p.tf_cd -= dt
        # Teleport CD
        if hasattr(p, 'tp_cd') and p.tp_cd > 0:
            p.tp_cd -= dt
        # Wirbel-Angriff (Krieger): tickt Schaden auf alle nahen Gegner
        if hasattr(p, '_whirl_left') and p._whirl_left > 0:
            p._whirl_left -= dt
            self._tick_whirl(eff, dt)
        # Meteor (Magier): nach Timer einschlagen
        if hasattr(self, '_meteor_pending') and self._meteor_pending:
            self._meteor_pending['timer'] -= dt
            if self._meteor_pending['timer'] <= 0:
                self._meteor_strike()
        # Update #184 / Cold-Mirror Keystone: 2 weitere Frostnova-Wellen
        if hasattr(self, '_pending_cold_mirror') and self._pending_cold_mirror:
            for wave in list(self._pending_cold_mirror):
                wave['delay'] -= dt
                if wave['delay'] <= 0:
                    self._cold_mirror_wave(wave)
                    self._pending_cold_mirror.remove(wave)
        # Way-of-Wind iframe-window decay
        if getattr(p, '_way_of_wind_active', 0) > 0:
            p._way_of_wind_active -= dt
        # Klone (Schurke): timer + minimale AI
        if hasattr(self, 'clones') and self.clones:
            for c in list(self.clones):
                c._clone_left -= dt
                if c._clone_left <= 0:
                    self.clones.remove(c)
                    self.spawn_particles(c.pos.x, c.pos.y, 20,
                                         (80, 30, 100), life_max=0.5, size_max=4)
        if p.slow_timer <= 0:
            p.slow_factor = 1.0
        for k in p.skill_cd:
            p.skill_cd[k] -= dt
        # HP/MP-Regeneration
        p.hp = min(eff['hp_max'], p.hp + eff['hp_regen'] * dt)
        p.mp = min(eff['mp_max'], p.mp + eff['mp_regen'] * dt)
        # Regen-Buff aus Heilungs-Rune
        if p.regen_buff_left > 0:
            heal = min(p.regen_buff * dt, eff['hp_max'] - p.hp)
            p.hp += heal
            p.regen_buff_left -= dt
        # Status-Effekte
        fx.tick_target(self, p, dt, is_player=True)
        # Trap-Schaden im Dungeon
        if self.grid is not None:
            self._tick_traps(dt)
        # Schaden-Flash abbauen
        self._damage_flash = max(0, self._damage_flash - dt * 4)

        if p.dodge > 0:
            self.move_entity(p, p.dodge_dir.x * 560 * dt,
                             p.dodge_dir.y * 560 * dt)
            return

        if p.attack_target and p.attack_target not in self.enemies:
            p.attack_target = None
            p.moving = False

        speed = eff['speed'] * p.slow_factor

        if p.attack_target:
            p.target = Vector2(p.attack_target.pos)
            diff = p.attack_target.pos - p.pos
            d = diff.length()
            att_range = p.radius + p.attack_target.radius + 6
            if d <= att_range:
                p.moving = False
                snd.stop_step()
                if d > 0:
                    p.facing = math.atan2(diff.y, diff.x)
                # LOS-Check: nicht durch Wand attacken
                if self.grid is not None and not self.grid.has_los(
                        p.pos.x, p.pos.y,
                        p.attack_target.pos.x, p.attack_target.pos.y):
                    # Kein LOS → Ziel verwerfen
                    p.attack_target = None
                    p.moving = False
                    return
                if p.attack_cd <= 0:
                    # Update #184: Atlas-Effekte fuer Melee
                    atlas_eff_now = eff.get('atlas_effects', set())
                    iron_palm = 'keystone_iron_palm' in atlas_eff_now
                    phys_to_lit = 0.0
                    if 'melee_phys_to_lit_25' in atlas_eff_now:
                        phys_to_lit = 0.25
                    if iron_palm:
                        phys_to_lit = 1.0  # 100% conversion
                    # Iron Palm: kein Crit auf Melee
                    if iron_palm:
                        mult, crit = 1.0, False
                    else:
                        mult, crit = skills._crit_roll(eff)
                    melee_dmg_pct = eff.get('melee_dmg_pct', 0)
                    raw_dmg = eff['damage'] * mult * (1.0 + melee_dmg_pct)
                    # fn_wall: verlangsamte Ziele erleiden +50% Schaden
                    if p.runes.get('frostnova') == 'fn_wall' and \
                            p.attack_target.slow_factor < 1.0:
                        raw_dmg *= 1.5
                    # Atlas-Attack-Speed: kuerzere attack_cd
                    atk_spd = 1.0 + eff.get('attack_speed', 0)
                    # N-05 (Update #51) + Update #53 Fix:
                    # Weapon-Impact-Identity pro Klasse mit Fallback-Chain.
                    # User-Bug „manchmal keine Waffen-Sounds": file-only
                    # Aliases ohne Procedural-Fallback waren still wenn
                    # Audio-Datei fehlt.  `play_with_fallback` garantiert
                    # immer einen Sound (Procedural-Fallback ist 'hit').
                    cls_pl = p.cls
                    swing_snd, impact_snd = _weapon_sound_pair(
                        cls_pl, heavy=(raw_dmg >= 30 or crit))
                    snd.play_with_fallback(swing_snd, 'hit', volume=0.3)
                    # Update #184: Iron-Palm / phys-to-lit Konversion
                    if phys_to_lit >= 1.0:
                        # Voller Lit-Hit (skaliert mit lit_dmg)
                        self.hit_enemy(p.attack_target,
                                       raw_dmg * eff.get('lit_dmg', 1.0),
                                       crit=crit, dmg_type='lightning')
                    elif phys_to_lit > 0.0:
                        phys_part = raw_dmg * (1.0 - phys_to_lit)
                        lit_part = (raw_dmg * phys_to_lit
                                    * eff.get('lit_dmg', 1.0))
                        self.hit_enemy(p.attack_target, phys_part,
                                       crit=crit, dmg_type='physical')
                        self.hit_enemy(p.attack_target, lit_part,
                                       crit=crit, dmg_type='lightning')
                    else:
                        self.hit_enemy(p.attack_target, raw_dmg, crit=crit)
                    # Iron-Palm Chain: 2 weitere Nachbarn werden ebenfalls getroffen
                    if iron_palm:
                        from .entities import LightningBolt as _LB
                        nearby = [e for e in self.enemies
                                  if e is not p.attack_target and not e.dying
                                  and (e.pos - p.attack_target.pos).length() < 120]
                        nearby.sort(key=lambda e: (e.pos - p.attack_target.pos).length())
                        for ne in nearby[:2]:
                            chain_dmg = raw_dmg * 0.7 * eff.get('lit_dmg', 1.0)
                            self.hit_enemy(ne, chain_dmg, crit=False,
                                           dmg_type='lightning')
                            self.bolts.append(_LB(
                                p.attack_target.pos.x, p.attack_target.pos.y,
                                ne.pos.x, ne.pos.y))
                    # Cleave (atlas-cleave_total)
                    cleave = eff.get('cleave', 0)
                    if cleave > 0 and not iron_palm:
                        for e in self.enemies:
                            if e is p.attack_target or e.dying:
                                continue
                            if (e.pos - p.attack_target.pos).length() < 80:
                                self.hit_enemy(e, raw_dmg * cleave,
                                               crit=False)
                    # Hundertfaches-Echo: jeder 5. Hit → free Frostnova am Ziel
                    if 'keystone_hundredfold_echo' in atlas_eff_now:
                        p._echo_counter = getattr(p, '_echo_counter', 0) + 1
                        if p._echo_counter >= 5:
                            p._echo_counter = 0
                            # Mini-Frostnova um attack_target
                            tgt = p.attack_target
                            for e in self.enemies:
                                if (e.pos - tgt.pos).length() <= 110 and not e.dying:
                                    fnova_dmg = eff['damage'] * 1.0 * eff['cold_dmg']
                                    self.hit_enemy(e, fnova_dmg,
                                                   dmg_type='cold')
                                    fx.apply(self, e, 'frost', stacks=2)
                    # Material-Impact-Layer: leise zusätzlich
                    if impact_snd:
                        snd.play_with_fallback(impact_snd, 'hit_heavy',
                                                volume=0.25)
                    # Vampir-Heilung
                    if p.vampire_charges > 0:
                        heal = raw_dmg * 0.3
                        p.hp = min(eff['hp_max'], p.hp + heal)
                        self.floaters.append(Floater(
                            p.pos.x, p.pos.y - 30,
                            f'+{int(heal)}', (220, 80, 80)))
                        p.vampire_charges -= 1
                    p.attack_cd = 0.4 / max(0.5, atk_spd)
                    # Update #165: Animation-Trigger 'attack' (One-Shot,
                    # 6 Frames @ 14fps ≈ 0.43s — matches attack_cd 0.4s).
                    try:
                        p.anim_state.trigger('attack')
                    except AttributeError:
                        pass
                    # Update #151 (User-Report „nicht jede Klasse sollte
                    # gleich aussehen"): Klassen-spezifische Attack-VFX.
                    # Jede Klasse bekommt eigenes Partikel-Profil
                    # (Farbe, Form, Anzahl) — Lore-Anker an die Klassen-
                    # Color + Waffen-Theme.
                    self._spawn_class_basic_attack_vfx(p, crit)
            else:
                p.moving = True

        if p.moving:
            diff = p.target - p.pos
            d = diff.length()
            if d < 3:
                p.moving = False
                snd.stop_step()  # Step-Channel sofort stoppen
            else:
                p.facing = math.atan2(diff.y, diff.x)
                step = min(speed * dt, d)
                n = diff.normalize()
                self.move_entity(p, n.x * step, n.y * step)
                p.walk_phase += dt * 10
                # Update #106 (Audit F-018): Aim-Offset Bow/Crossbow.
                # Wenn der Spieler eine Distanz-Klasse spielt, lehnt sich
                # die Aim-Hand-Position leicht in Bewegungsrichtung.
                if p.cls in ('ranger', 'huntress', 'rogue'):
                    try:
                        from .sprites import get_rig, aim_offset_for_movement
                        rig = get_rig(p)
                        vx = n.x * speed
                        vy = n.y * speed
                        wp = 'bow' if p.cls == 'ranger' else (
                              'crossbow' if p.cls == 'rogue' else 'spear')
                        ox, oy = aim_offset_for_movement(vx, vy, wp)
                        rig.aim_offset_x = ox
                        rig.aim_offset_y = oy
                    except Exception:
                        pass
                # Schritt-Sound je Biom — Update #32: dedizierter
                # Step-Channel via `play_step()`. Damit endet der
                # Sound sofort sobald der Spieler aufhört zu laufen.
                self._step_timer -= dt
                if self._step_timer <= 0:
                    self._step_timer = 0.32
                    # N-11 (Update #52): Material-Detection vor Biome-Fallback.
                    # Prüft Decor + Grid-Traps an Spieler-Pos für Water/Wood/
                    # Metal/Mud-Override; fällt sonst auf Biome-Step.
                    step_sound = self._detect_step_material()
                    snd.play_step(step_sound, volume=0.25)
                    # Update #138 (V-06): Footprints in geeigneten Biomes.
                    # Akt 2 (Frost-Glas), Akt 1b (Desert-Sand),
                    # Akt 3 (Lava-Asche) hinterlassen sichtbare Spuren.
                    if self.biome in ('frost', 'desert', 'lava'):
                        self._spawn_footprint(p, dt)
                # Wenn Wand blockiert hat: stoppe
                actual_diff = (p.target - p.pos).length()
                if actual_diff >= d - 0.1:
                    p.moving = False
                    snd.stop_step()

    def _update_enemies(self, dt):
        # Time-Freeze (Y-Skill): Gegner pausiert
        if self.time_freeze_left > 0:
            for e in self.enemies:
                if not e.dying:
                    e.hit_flash = max(e.hit_flash, 0.05)  # blau-Tint via Render
            return
        # PLAN D-15: Frame-Phase-Counter für Round-Robin-Sight-Checks
        self._ai_frame_phase = (getattr(self, '_ai_frame_phase', 0) + 1) % 1000
        # PLAN D-04: Player-Noise — Standard walking, Sprint/Cast können
        # ihn temporär hochsetzen (player setzt current_noise_px direkt).
        from . import ai as _ai_mod
        if not hasattr(self.player, 'current_noise_px'):
            self.player.current_noise_px = _ai_mod.PLAYER_NOISE['walk']
        # D-06 (Update #48): „Quiet Movement"-Passive für Monk/Rogue.
        # Player-Noise wird halbiert solange diese Klassen gespielt werden.
        # Stationary-Bonus: wenn Spieler steht, geht der Noise auf 25 %.
        cls = self.player.cls
        stealth_mult = getattr(self.player, 'stealth_passive_mult', None)
        if stealth_mult is None:
            stealth_mult = 0.5 if cls in ('monk', 'rogue') else 1.0
            self.player.stealth_passive_mult = stealth_mult
        if stealth_mult < 1.0:
            base_noise = _ai_mod.PLAYER_NOISE['walk']
            if not self.player.moving:
                base_noise = int(base_noise * 0.25)
            else:
                base_noise = int(base_noise * stealth_mult)
            # Nur überschreiben wenn aktuell auf walk-Default (Casts setzen
            # selbst hoch — wir respektieren das).
            if (self.player.current_noise_px
                    <= _ai_mod.PLAYER_NOISE['walk'] + 1):
                self.player.current_noise_px = max(base_noise, 32)
        # PLAN D-09: verzögerte Pack-Alerts ticken (einmal pro Frame)
        _ai_mod.tick_pending_alerts(self, dt)
        # Snapshot, da Bosse während AI Gegner spawnen können.
        for e in list(self.enemies):
            if e not in self.enemies:
                continue
            if e.dying:
                e.death_timer += dt
                if e.death_timer > 0.4:
                    self.enemies.remove(e)
                continue
            e.attack_timer -= dt
            e.hit_flash -= dt
            e.wobble += dt * 4
            e.slow_timer -= dt
            if e.slow_timer <= 0:
                e.slow_factor = 1.0
            e.stun_timer = max(0.0, e.stun_timer - dt)
            # Update #34: Stun-Buildup-Decay + Heavy-Stun-Reset
            if hasattr(e, 'stun_buildup'):
                # Decay um 8/s wenn nicht gerade Stunned
                if e.stun_timer <= 0:
                    e.stun_buildup = max(0.0, e.stun_buildup - 8.0 * dt)
                    if e.stun_buildup <= 0 and e.heavy_stunned:
                        e.heavy_stunned = False
            # Status-Effekte
            fx.tick_target(self, e, dt, is_player=False)
            if e not in self.enemies:
                continue  # status damage hat ihn getötet
            # Stun blockiert AI
            if e.stun_timer > 0:
                continue
            # Update #43: Auto-Unstuck wenn Gegner im Decor hängt (User-Bug).
            if self._decor_collides(e.pos.x, e.pos.y, e.radius):
                self._unstuck_entity(e)
            # PLAN D-14 (Update #96): LOD-Tick — Mobs weit vom Spieler bekommen
            # nur jeden 5. Frame einen AI-Update. Bosse/Mini-Bosse + Mobs
            # mit aktiver Aggro überspringen das Filter (Fairness).
            lod = _ai_mod.lod_tick_factor(e, self.player.pos)
            if lod == 0.0:
                continue
            if (lod < 1.0 and not e.is_boss
                    and not getattr(e, 'is_mini_boss', False)
                    and getattr(e, 'ai_state', None) not in ('AGGRO',)):
                # Sparse-Tick: alle 5 Frames updaten
                if (self._ai_frame_phase + id(e)) % 5 != 0:
                    continue
            # Update #147 (User-Report „Monster stecken an Objekten fest"):
            # Stuck-Detection — wenn ein Aggro-Mob für 1.5 s nicht mehr
            # bewegt UND nicht in einem Wind-Up ist, unstuck-push.
            prev_x = e.pos.x; prev_y = e.pos.y
            enemies.update_enemy_ai(self, e, dt)
            moved = ((e.pos.x - prev_x) ** 2
                     + (e.pos.y - prev_y) ** 2) > 0.05
            if not hasattr(e, '_stuck_t'):
                e._stuck_t = 0.0
            atk_phase = getattr(e, 'atk_phase', 'idle')
            in_action = atk_phase in ('windup', 'swing', 'recover')
            if moved or in_action or getattr(e, 'heavy_stunned', False):
                e._stuck_t = 0.0
            elif getattr(e, 'ai_state', None) == 'aggro':
                e._stuck_t += dt
                if e._stuck_t > 1.5:
                    # Push aus blockierendem Decor (falls da)
                    self._unstuck_entity(e)
                    # Random Side-Step damit nicht direkt wieder
                    # blockiert
                    ang = random.uniform(0, math.tau)
                    push = 12.0
                    self.move_entity(
                        e, math.cos(ang) * push, math.sin(ang) * push)
                    e._stuck_t = 0.0
        enemies.separation(self.enemies, game=self)

    def _update_projectiles(self, dt):
        for proj in self.projectiles[:]:
            proj.age += dt
            proj.pos += proj.vel * dt
            # Wand-Kollision
            if self.grid is not None and not self.grid.is_walkable_world(
                    proj.pos.x, proj.pos.y):
                # Spark-Bounce: prallt von Wand ab
                if proj.kind == 'spark' and proj.extra.get('bounces', 0) > 0:
                    proj.extra['bounces'] -= 1
                    # Position zurück + Velocity umkehren (vereinfacht)
                    proj.pos -= proj.vel * dt
                    # Probiere horizontal Flip; wenn immer noch in Wand, vertikal
                    test_x = proj.pos.x + proj.vel.x * dt * 0.5
                    if not self.grid.is_walkable_world(test_x, proj.pos.y):
                        proj.vel.x = -proj.vel.x
                    else:
                        proj.vel.y = -proj.vel.y
                    self.spawn_particles(proj.pos.x, proj.pos.y, 6,
                                         (180, 200, 255), life_max=0.3, size_max=3)
                    continue
                self._on_projectile_expire(proj)
                self.spawn_particles(proj.pos.x, proj.pos.y, 8,
                                     (220, 180, 100), life_max=0.4, size_max=3)
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue
            if proj.age >= proj.life:
                self._on_projectile_expire(proj)
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue

            # Schweif
            if proj.kind == 'fireball' and random.random() < 0.7:
                self.particles.append(Particle(
                    proj.pos.x, proj.pos.y,
                    random.uniform(-30, 30), random.uniform(-30, 30),
                    FIRE, random.uniform(0.15, 0.3), random.uniform(2, 4),
                ))
            elif proj.kind in ('shadowbolt', 'frostbolt', 'firebolt', 'poisonbolt') \
                    and random.random() < 0.4:
                col = {
                    'shadowbolt': (160, 80, 240),
                    'frostbolt': FROST,
                    'firebolt': FIRE,
                    'poisonbolt': POISON,
                }[proj.kind]
                self.particles.append(Particle(
                    proj.pos.x, proj.pos.y, 0, 0,
                    col, 0.25, random.uniform(2, 4),
                ))

            # Kollision
            if proj.friendly:
                hit = False
                for e in self.enemies[:]:
                    if id(e) in proj.hit_ids:
                        continue
                    if (e.pos - proj.pos).length() < e.radius + proj.radius:
                        proj.hit_ids.add(id(e))
                        crit = proj.extra.get('crit', False)
                        self.hit_enemy(e, proj.damage, crit=crit)
                        # Blut-Splash bei Treffer
                        self.spawn_particles(e.pos.x, e.pos.y, 4,
                                             (180, 30, 30), life_max=0.6,
                                             size_max=3, gravity=120)
                        # Rune: Brennen anwenden
                        if proj.extra.get('burn') and e in self.enemies:
                            fx.apply(self, e, 'burn', stacks=2)
                        if proj.kind == 'fireball':
                            aoe = proj.extra.get('aoe', 60)
                            # Audit #179 B.5: SpatialGrid-Query statt linearer Loop.
                            for e2 in self.enemy_grid.query_radius(
                                    proj.pos.x, proj.pos.y, aoe):
                                if e2 is e:
                                    continue
                                dd = (e2.pos - proj.pos).length()
                                if dd < aoe:
                                    self.hit_enemy(
                                        e2, proj.damage * 0.5 * (1 - dd / aoe),
                                        crit=crit)
                                    if proj.extra.get('burn'):
                                        fx.apply(self, e2, 'burn', stacks=1)
                            self.spawn_particles(proj.pos.x, proj.pos.y, 22,
                                                 (255, 106, 26),
                                                 life_max=0.7, size_max=6)
                            # Rune: Spaltung – 3 mini-Fireballs
                            if proj.extra.get('split'):
                                from .entities import Projectile as P
                                for k in range(3):
                                    a = (k / 3) * math.tau + random.uniform(-0.2, 0.2)
                                    self.projectiles.append(P(
                                        proj.pos.x, proj.pos.y,
                                        math.cos(a) * 360, math.sin(a) * 360,
                                        proj.damage * 0.5, 'fireball',
                                        radius=6, life=0.7,
                                        extra={'aoe': 40, 'crit': crit},
                                    ))
                            self.shake = max(self.shake, 4)
                            hit = True
                            break
                        else:
                            # Update #27: Spell-Impact-Sound (Rescopic).
                            # Wird bei nicht-Fireball-Projektil-Treffer
                            # gespielt — gibt jeder Magie einen „Wumms".
                            if proj.kind in ('bone_spear', 'spark',
                                              'firebolt', 'frostbolt',
                                              'shadowbolt'):
                                snd.play('spell_impact', volume=0.6)
                            # Update #23: Splash-on-Hit (Galvanic Shot —
                            # Lightning splash bei Impact).
                            splash = proj.extra.get('splash_on_hit', 0)
                            if splash > 0:
                                splash_r = proj.extra.get(
                                    'splash_radius', 70)
                                splash_mult = proj.extra.get(
                                    'splash_dmg_mult', 0.5)
                                dmg_type = proj.extra.get(
                                    'dmg_type', 'physical')
                                count = 0
                                # Audit #179 B.5: SpatialGrid statt linear.
                                for e2 in self.enemy_grid.query_radius(
                                        e.pos.x, e.pos.y, splash_r):
                                    if e2 is e or count >= splash:
                                        continue
                                    dd = (e2.pos - e.pos).length()
                                    if dd < splash_r:
                                        self.hit_enemy(
                                            e2,
                                            proj.damage * splash_mult,
                                            crit=False, dmg_type=dmg_type)
                                        count += 1
                                self.spawn_particles(
                                    e.pos.x, e.pos.y, 16,
                                    (220, 240, 255),
                                    life_max=0.4, size_max=4)
                            # Update #23: Chain-on-Hit (Lightning Arrow —
                            # springt zu N nahen Gegnern bei Impact).
                            chains = proj.extra.get('chain_on_hit', 0)
                            if chains > 0:
                                chain_mult = proj.extra.get(
                                    'chain_dmg_mult', 0.65)
                                dmg_type = proj.extra.get(
                                    'dmg_type', 'lightning')
                                from .entities import LightningBolt
                                prev_pos = e.pos
                                prev_dmg = proj.damage
                                hit_chain_ids = {id(e)}
                                for _ in range(chains):
                                    nearest = None
                                    nd = 240.0
                                    # Audit #179 B.5: SpatialGrid statt linear.
                                    for e3 in self.enemy_grid.query_radius(
                                            prev_pos.x, prev_pos.y, 240.0):
                                        if id(e3) in hit_chain_ids or e3.dying:
                                            continue
                                        d3 = (e3.pos - prev_pos).length()
                                        if d3 < nd:
                                            nd = d3
                                            nearest = e3
                                    if nearest is None:
                                        break
                                    self.bolts.append(LightningBolt(
                                        prev_pos.x, prev_pos.y,
                                        nearest.pos.x, nearest.pos.y))
                                    prev_dmg *= chain_mult
                                    self.hit_enemy(nearest, prev_dmg,
                                                    crit=False,
                                                    dmg_type=dmg_type)
                                    hit_chain_ids.add(id(nearest))
                                    prev_pos = nearest.pos
                            # Update #107: Generic apply_status für Klassen-
                            # Skill-Projektile (Frost-Arrow, Burning-Arrow,
                            # Permafrost-Bolts, Plasma-Blast).
                            ast_key = proj.extra.get('apply_status')
                            if ast_key and e in self.enemies:
                                ast_stacks = proj.extra.get(
                                    'apply_stacks', 1)
                                try:
                                    fx.apply(self, e, ast_key,
                                             stacks=ast_stacks)
                                except Exception:
                                    pass
                            ast_key2 = proj.extra.get('apply_status_2')
                            if ast_key2 and e in self.enemies:
                                ast_stacks2 = proj.extra.get(
                                    'apply_stacks_2', 1)
                                try:
                                    fx.apply(self, e, ast_key2,
                                             stacks=ast_stacks2)
                                except Exception:
                                    pass
                            # Pierce: bone_spear durchschlägt mehrere Gegner
                            if proj.extra.get('pierce', 0) > 0:
                                proj.extra['pierce'] -= 1
                                # NICHT removen, weiter pierce'n
                                continue
                            hit = True
                            break
                if hit and proj in self.projectiles:
                    self.projectiles.remove(proj)
            else:
                # Enemy-Projektil → trifft Spieler
                p = self.player
                if (p.pos - proj.pos).length() < p.radius + proj.radius:
                    self.damage_player(proj.damage)
                    if proj.kind == 'frostbolt':
                        fx.apply(self, p, 'frost', stacks=1)
                    elif proj.kind == 'poisonbolt':
                        fx.apply(self, p, 'poison', stacks=2)
                    if proj in self.projectiles:
                        self.projectiles.remove(proj)

    def _on_projectile_expire(self, proj):
        if proj.kind == 'fireball':
            self.spawn_particles(proj.pos.x, proj.pos.y, 14,
                                 (255, 106, 26), life_max=0.6, size_max=5)

    def _update_loot(self, dt):
        p = self.player
        for l in self.loot[:]:
            l.bob += dt * 3
            # Update #57: Drop-Grace dekrementieren (User „hebe sofort wieder auf")
            if getattr(l, '_drop_grace_t', 0) > 0:
                l._drop_grace_t = max(0, l._drop_grace_t - dt)
            diff = p.pos - l.pos
            d = diff.length()
            # Gold/Gem/Vital-Orb magnetisch (Auto-Pickup behalten).
            if l.kind in ('gold', 'gem', 'vital_orb') and 0 < d < 110:
                l.pos += diff.normalize() * 360 * dt
            # Update #57: Items NICHT MEHR magnetisch — Player muss anklicken.
            # Ausnahme: Items mit `_click_pickup_target=True` (vom World-Click
            # gesetzt) ziehen sich sanft Richtung Player als visueller Hint.
            if (l.kind == 'item' and l.item is not None
                    and getattr(l, '_click_pickup_target', False)
                    and 0 < d < 200):
                l.pos += diff.normalize() * 140 * dt
            # Pickup-Check (Update #57):
            #   - Items: nur wenn Click-Target UND Grace abgelaufen (POE2-Style)
            #   - Gold/Gem/Skill-Gem: auto-pickup auf walkover (Currency-Style)
            if d >= p.radius + 8:
                continue
            if l.kind == 'item':
                if getattr(l, '_drop_grace_t', 0) > 0:
                    continue
                if not getattr(l, '_click_pickup_target', False):
                    continue
                # Update #201: Loot-Filter wird jetzt schon beim Drop
                # angewandt (combat._item_passes_loot_filter), nicht mehr
                # beim Pickup. Garantie: was am Boden liegt, ist immer
                # aufhebbar — kein verwirrender un-pickbarer Clutter mehr,
                # auch wenn der Spieler den Filter nach dem Drop aendert.
                placed = False
                for i, slot in enumerate(p.inventory):
                    if slot is None:
                        p.inventory[i] = l.item
                        placed = True
                        break
                if placed:
                    from .constants import RARITY_COLOR
                    self.floaters.append(Floater(
                        p.pos.x, p.pos.y - 30,
                        f'{l.item.name}', RARITY_COLOR[l.item.rarity]))
                    self.spawn_particles(l.pos.x, l.pos.y, 8, l.color,
                                         life_max=0.4, size_max=3)
                    if l.item.rarity == 'unique':
                        ach_mod.on_unique_drop(self)
                        self._check_achievements()
                    # Update #X — Rarity-aware Pickup-SFX (Phase-2-AI-SFX)
                    _pickup_sfx = {
                        'common': 'ui_item_pickup_common',
                        'magic':  'ui_item_pickup_common',
                        'rare':   'ui_item_pickup_rare',
                        'unique': 'ui_item_pickup_unique',
                        'mythic': 'ui_item_pickup_mythic',
                    }.get(l.item.rarity, 'pickup_item')
                    snd.play(_pickup_sfx, volume=0.6)
                    # Update #136 (O-23): Pickup-Spline-Anim spawnen
                    self._spawn_loot_pickup_anim(
                        l.pos.x, l.pos.y, l.color, 'item')
                    self.loot.remove(l)
            elif l.kind == 'skill_gem':
                sid = getattr(l, 'skill_id', None)
                if sid:
                    first_time = sid not in p.unlocked_skills
                    p.unlocked_skills.add(sid)
                    from .skills import SKILL_INFO as _SI
                    info = _SI.get(sid, {})
                    name = info.get('name', sid)
                    hotkey = info.get('key', '?')
                    self.floaters.append(Floater(
                        p.pos.x, p.pos.y - 30,
                        f'★ {name}', (200, 150, 240)))
                    if first_time:
                        self.toast(
                            f'Skill erlernt: {name} — Taste [{hotkey}]',
                            (200, 150, 240))
                    else:
                        self.toast(f'{name} (bereits erlernt)',
                                   (160, 130, 200))
                    self.spawn_particles(l.pos.x, l.pos.y, 18,
                                          (200, 150, 240),
                                          life_max=0.8, size_max=5)
                    snd.play('levelup', volume=0.7)
                # Update #136 (O-23): Pickup-Spline-Anim
                self._spawn_loot_pickup_anim(
                    l.pos.x, l.pos.y, (200, 150, 240), 'skill_gem')
                self.loot.remove(l)
            elif l.kind == 'vital_orb':
                # Update #96: Vital-Orb auto-pickup → heilt HP+MP.
                amt = max(1, int(getattr(l, 'vital_amount', 18)))
                from . import progression as _p
                eff = _p.effective(p)
                p.hp = min(eff['hp_max'], p.hp + amt)
                p.mp = min(eff['mp_max'], p.mp + amt * 0.6)
                self.floaters.append(Floater(
                    p.pos.x, p.pos.y - 30,
                    f'+{amt} Vital', l.color, heal=True))
                self.spawn_particles(l.pos.x, l.pos.y, 14, l.color,
                                      life_max=0.6, size_max=4,
                                      gravity=-40)
                snd.play('pickup_gold', volume=0.6)
                # Update #136 (O-23): Pickup-Spline-Anim für Vital-Orb
                self._spawn_loot_pickup_anim(
                    l.pos.x, l.pos.y, l.color, 'vital_orb')
                self.loot.remove(l)
            elif l.kind == 'gem':
                from .constants import GEM_TYPES
                gem = getattr(l, 'gem_type', None)
                if gem:
                    p.gems.append(gem)
                    gd = GEM_TYPES[gem]
                    self.floaters.append(Floater(
                        p.pos.x, p.pos.y - 30,
                        f'◆ {gd["name"]} ({gd["desc"]})', gd['color']))
                    self.floaters.append(Floater(
                        p.pos.x, p.pos.y - 14,
                        'In Werkstatt (C) in Item sockeln',
                        (180, 180, 180)))
                    self.spawn_particles(l.pos.x, l.pos.y, 10, l.color,
                                         life_max=0.5, size_max=4)
                    # Update #X — Phase-3-AI: Uncut-Shard-Pickup-Sound
                    snd.play('pickup_uncut_shard', volume=0.5)
                    from . import quests
                    quests.on_gem_pickup(self)
                # Update #136 (O-23): Pickup-Spline-Anim für Gem
                self._spawn_loot_pickup_anim(
                    l.pos.x, l.pos.y, l.color, 'gem')
                self.loot.remove(l)
            else:  # gold
                p.gold += l.gold
                ach_mod.on_gold_gained(self, l.gold)
                self._check_achievements()
                self.floaters.append(Floater(
                    p.pos.x, p.pos.y - 30,
                    f'+{l.gold} Gold', (255, 215, 90)))
                self.spawn_particles(l.pos.x, l.pos.y, 8, l.color,
                                     life_max=0.4, size_max=3)
                snd.play('pickup_gold')
                if l.gold >= 25:
                    self.push_event_log(f'+{l.gold} Gold',
                                         (255, 215, 90), duration=3.0)
                # Update #136 (O-23): Pickup-Spline-Anim für Gold
                self._spawn_loot_pickup_anim(
                    l.pos.x, l.pos.y, l.color, 'gold')
                self.loot.remove(l)

    def _update_particles(self, dt):
        # J-13 (Update #64): O(N) Filter-In-Place + Object-Pool-Recycling.
        # Vorher war es O(N²) durch `list.remove()` in der Schleife.
        alive = []
        pool = self._particle_pool
        pool_max = self._PARTICLE_POOL_MAX
        for p in self.particles:
            p.age += dt
            p.pos += p.vel * dt
            p.vel.y += p.gravity * dt
            p.vel *= 0.94
            if p.age >= p.life:
                if len(pool) < pool_max:
                    pool.append(p)
            else:
                alive.append(p)
        self.particles = alive
        # M-07 (Update #69): Particle-Budget-Cap.  Wenn der Frame-Count
        # über `_PARTICLE_BUDGET_BASE × density-mult` ist, droppen wir die
        # ältesten AMBIENT-Particles (cullable Layer).  GAMEPLAY/TELEGRAPH
        # bleiben — sie sind kritisches Feedback.
        budget = int(self._PARTICLE_BUDGET_BASE *
                      max(0.3, self.settings.get('particle_density', 1.0)))
        if len(self.particles) > budget:
            # Sort-stable: alle non-ambient zuerst (überleben), dann ambient
            # nach Age (jüngste zuerst).  Wir behalten die ersten `budget`.
            ambient = []
            critical = []
            for p in self.particles:
                if p.layer == fx.ParticleLayer.AMBIENT:
                    ambient.append(p)
                else:
                    critical.append(p)
            # Nach Age sortieren — älteste raus
            ambient.sort(key=lambda pt: -pt.age)
            # Critical immer behalten, Ambient nur bis budget gefüllt ist
            remaining = max(0, budget - len(critical))
            ambient = ambient[:remaining]
            # Recycelte AMBIENT in den Pool für Reuse
            dropped = self.particles
            self.particles = critical + ambient
            for p in dropped:
                if (p not in self.particles
                        and len(self._particle_pool) < pool_max):
                    self._particle_pool.append(p)
        # Floater/Bolt-Lists genauso O(N) filtern
        alive_floaters = []
        for f in self.floaters:
            f.age += dt
            f.pos.y += f.vy * dt
            f.vy *= 0.92
            if f.age < f.life:
                alive_floaters.append(f)
        self.floaters = alive_floaters
        alive_bolts = []
        for b in self.bolts:
            b.age += dt
            if b.age < b.life:
                alive_bolts.append(b)
        self.bolts = alive_bolts

    # ---------- Welt-Events ----------
    def _update_events(self, dt):
        """Triggert zufällige dramatische Events im Dungeon."""
        self.event_timer -= dt
        # Erdbeben aktiv?
        if self.earthquake_left > 0:
            self.earthquake_left -= dt
            self.shake = max(self.shake, 8 + (self.earthquake_left * 0.5))
            if random.random() < 0.4:
                self._spawn_falling_rock()
        # Sturm aktiv?
        # Update #42: Donner/Blitz war zu häufig (User-Feedback).
        # Strike-CD 0.5–1.2 → 1.8–3.4s, Donner-Sound nur jeder 2. Strike.
        if self.storm_left > 0:
            self.storm_left -= dt
            self.storm_strike_cd -= dt
            if self.storm_strike_cd <= 0:
                self.storm_strike_cd = random.uniform(1.8, 3.4)
                self._trigger_lightning_strike()
                # Donner nur ~jeder zweite Strike, leiser
                if random.random() < 0.5:
                    snd.play('thunder', volume=0.35)
        # Sandsturm aktiv?
        if self.sandstorm_left > 0:
            self.sandstorm_left -= dt
            # Slow + leichter Schaden
            self.player.slow_timer = max(self.player.slow_timer, 0.3)
            self.player.slow_factor = min(self.player.slow_factor, 0.7)
        # Eissturm aktiv?
        if self.icestorm_left > 0:
            self.icestorm_left -= dt
            self.player.slow_timer = max(self.player.slow_timer, 0.3)
            self.player.slow_factor = min(self.player.slow_factor, 0.7)
            for e in self.enemies:
                if not e.dying:
                    e.slow_timer = max(e.slow_timer, 0.3)
                    e.slow_factor = min(e.slow_factor, 0.6)
        # Ascheregen aktiv?
        # Update #43: deutlich entschärft (User „stirbt in der Lava Welt").
        # Tick 0.5 → 1.2 s, Damage 2+lvl*0.3 → 1+lvl*0.15, KEIN Burn.
        if self.ashrain_left > 0:
            self.ashrain_left -= dt
            self.ashrain_tick -= dt
            if self.ashrain_tick <= 0:
                self.ashrain_tick = 1.2
                self.damage_player(1 + self.player.level * 0.15)
        # M-06 + N-12 (Update #66): Rain-Event mit Crossfade-Intensity.
        # Lightning-Skill-Bonus wirkt via `game.rain_intensity` in skills.py.
        if self.rain_left > 0:
            self.rain_left -= dt
            total = max(0.1, self.rain_total)
            elapsed = total - self.rain_left
            # Ramp-up (erste 2 s) + Plateau + Taper-out (letzte 2 s)
            ramp_in = min(1.0, elapsed / 2.0)
            ramp_out = min(1.0, self.rain_left / 2.0)
            self.rain_intensity = ramp_in * ramp_out
            # Rain-Particles spawnen (skaliert mit intensity + density-slider)
            self.rain_spawn_t -= dt
            if self.rain_spawn_t <= 0 and self.rain_intensity > 0.05:
                self.rain_spawn_t = 0.05 / max(0.2, self.rain_intensity)
                n = max(1, int(8 * self.rain_intensity))
                for _ in range(n):
                    px_ = self.player.pos.x + random.uniform(
                        -SCREEN_W // 2, SCREEN_W // 2)
                    py_ = self.player.pos.y - SCREEN_H // 2 - random.uniform(
                        0, 40)
                    self.particles_push(
                        px_, py_, random.uniform(-10, 10),
                        random.uniform(180, 320),
                        (170, 200, 230), 0.8,
                        random.uniform(2, 4), gravity=240,
                        layer=fx.ParticleLayer.AMBIENT)
            # V-01 (Update #168): Wet-Patches alle ~1.5 s am Player-Umkreis.
            # Pfuetzen-Decals persistieren 8 s — auch nach Regen-Ende.
            # Update #183 (User-Fix „Kreise gehen durch Waende"):
            # Walkability-Check vor dem Spawn — Pfuetzen landen nur auf
            # Floor-Cells, nicht auf Wand- oder Void-Tiles.
            if not hasattr(self, '_rain_puddle_t'):
                self._rain_puddle_t = 0.0
            self._rain_puddle_t -= dt
            if self._rain_puddle_t <= 0 and self.rain_intensity > 0.3:
                self._rain_puddle_t = 1.5
                for _ in range(2):
                    rx = self.player.pos.x + random.uniform(-300, 300)
                    ry = self.player.pos.y + random.uniform(-200, 200)
                    if self.grid is not None and not self.grid.is_walkable_world(rx, ry):
                        wk = self.grid.find_walkable_near(rx, ry)
                        if wk is None:
                            continue
                        rx, ry = wk
                    try:
                        self.surface_fx.spawn_wet_patch(
                            rx, ry, radius=random.randint(50, 90))
                    except Exception:
                        pass
        else:
            # Rain expired → intensity dekayed
            if self.rain_intensity > 0:
                self.rain_intensity = max(0.0, self.rain_intensity - dt * 0.5)
        # Miasma (Sumpf)
        if self.miasma_left > 0:
            self.miasma_left -= dt
            self.miasma_tick -= dt
            if self.miasma_tick <= 0:
                self.miasma_tick = 0.7
                fx.apply(self, self.player, 'poison', stacks=1)
        # Kosmischer Puls (Astral)
        if self.cosmic_pulse_left > 0:
            self.cosmic_pulse_left -= dt
            if random.random() < 0.04:
                # Random teleport eines Gegners
                for e in self.enemies:
                    if random.random() < 0.2 and not e.is_boss:
                        e.pos.x += random.uniform(-80, 80)
                        e.pos.y += random.uniform(-80, 80)
        # Time-Freeze (Y-Skill)
        if self.time_freeze_left > 0:
            self.time_freeze_left -= dt
        # Falling Rocks updaten
        for r in self.falling_rocks[:]:
            r['timer'] -= dt
            if r['timer'] <= 0:
                self.spawn_particles(r['x'], r['y'], 16, (140, 100, 70),
                                     life_max=0.7, size_max=5, gravity=160)
                if (Vector2(r['x'], r['y']) - self.player.pos).length() < 40:
                    self.damage_player(15 + self.player.level * 2)
                self.shake = max(self.shake, 5)
                self.falling_rocks.remove(r)
        # Neues Event triggern
        # Update #42: Event-Frequenz reduziert (45–75 → 80–130s)
        if self.event_timer <= 0:
            self.event_timer = random.uniform(80, 130)
            self._trigger_dungeon_event()

    def _trigger_dungeon_event(self):
        # Biom-spezifische Events bevorzugen
        # Update #42: Storm seltener (1 von n) — Biom-Specials häufiger.
        # In Frost/Lava/Desert/Swamp/Astral wird Storm fast vollständig
        # durch Biom-Events verdrängt (war zu dominant).
        events = ['earthquake']
        if self.biome == 'desert':
            events.append('sandstorm')
            events.append('sandstorm')
            events.append('sandstorm')
        elif self.biome == 'frost':
            events.append('icestorm')
            events.append('icestorm')
            events.append('icestorm')
        elif self.biome == 'lava':
            events.append('ashrain')
            events.append('ashrain')
            events.append('ashrain')
        elif self.biome == 'swamp':
            events.append('miasma')
            events.append('miasma')
        elif self.biome == 'astral':
            events.append('cosmic_pulse')
            events.append('cosmic_pulse')
        else:
            # Storm nur in Standard-Biomen (z. B. crypt/forest)
            events.append('storm')
        # M-06 (Update #66): Rain als Event in allen Standard- und
        # Swamp-Biomen.  Storm-Biome haben es schon implizit als Donner.
        if self.biome in ('crypt', 'swamp'):
            events.append('rain')
        e = random.choice(events)
        if e == 'earthquake':
            self.earthquake_left = 5.0
            self.toast('ERDBEBEN!', (200, 140, 60))
            snd.play('roar', volume=0.6)
        elif e == 'storm':
            # Storm-Duration reduziert 8 → 5s, Initial-Donner leiser
            self.storm_left = 5.0
            self.storm_strike_cd = 1.2
            self.toast('GEWITTER TOBT!', (200, 200, 255))
            snd.play('thunder', volume=0.45)
        elif e == 'sandstorm':
            self.sandstorm_left = 7.0
            self.toast('SANDSTURM!', (240, 200, 100))
            snd.play('wind' if 'wind' in snd._AMBIENT_BUILDERS else 'thunder',
                      volume=0.5) if False else snd.play_ambient('wind')
        elif e == 'icestorm':
            self.icestorm_left = 7.0
            self.toast('EISSTURM!', (200, 220, 255))
            snd.play_ambient('wind')
        elif e == 'ashrain':
            self.ashrain_left = 8.0
            self.toast('ASCHEREGEN!', (255, 140, 80))
            snd.play_ambient('lava')
        elif e == 'miasma':
            self.miasma_left = 8.0
            self.toast('GIFTNEBEL!', (160, 220, 100))
            snd.play_ambient('whisper')
        elif e == 'cosmic_pulse':
            self.cosmic_pulse_left = 6.0
            self.toast('KOSMISCHER PULS!', (200, 160, 255))
            snd.play_ambient('chime')
        elif e == 'rain':
            # M-06 + N-12 (Update #66): 12 s Regen mit 2 s Ramp-In + 2 s
            # Taper-Out.  Lightning-Skill-Bonus während Regen.
            self.rain_left = 12.0
            self.rain_total = 12.0
            self.rain_spawn_t = 0.0
            self.toast('REGEN ZIEHT AUF — Blitz-Skills +30 %',
                       (170, 200, 230))
            snd.play_ambient('wind')

    def _spawn_falling_rock(self):
        a = random.uniform(0, math.tau)
        d = random.uniform(60, 180)
        tx = self.player.pos.x + math.cos(a) * d
        ty = self.player.pos.y + math.sin(a) * d
        self.falling_rocks.append({'x': tx, 'y': ty, 'timer': 1.0})

    def _trigger_lightning_strike(self):
        a = random.uniform(0, math.tau)
        d = random.uniform(40, 280)
        tx = self.player.pos.x + math.cos(a) * d
        ty = self.player.pos.y + math.sin(a) * d
        from .entities import LightningBolt
        self.bolts.append(LightningBolt(tx, ty - 600, tx, ty))
        for e in list(self.enemies):
            if (e.pos - Vector2(tx, ty)).length() < 70:
                self.hit_enemy(e, 30 + self.player.level * 3,
                                dmg_type='lightning')
        if (Vector2(tx, ty) - self.player.pos).length() < 50:
            self.damage_player(10 + self.player.level)
        self.spawn_particles(tx, ty, 30, (200, 220, 255),
                              life_max=0.6, size_max=6)
        self.shake = max(self.shake, 5)
        self._damage_flash = max(self._damage_flash, 0.3)

    def _spawn_dungeon_boss_in_room(self):
        """Spawnt den Dungeon-Boss zentriert im Boss-Room.

        Wenn der Boss ein Bestiarium-Encounter ist (z. B. lava → vehren),
        wird stattdessen das Bestiarium-Encounter-System genutzt.
        """
        from . import boss_encounter as _enc
        from . import bestiary as _best
        bx = self._dungeon_boss_pos.x
        by = self._dungeon_boss_pos.y

        # Lore-Mapping Dungeon-Biome → Encounter-Key.
        # Update #110 + #111: Tier-3 routet auf Akt-6-Drei-Wunden-Bosse,
        # Tier-1/2 nutzt die jeweiligen Akt-Hauptbosse aus WELT_AUFBAU 1.2.
        tier = getattr(self, 'current_tier', 1)
        encounter_key = None
        if self.biome == 'crypt':
            # Akt 1 Salzküste / Akt 6a Salzwunde
            encounter_key = 'ertrunkene_koenigin' if tier >= 3 \
                else 'salzhueter_brut'
        elif self.biome == 'frost':
            # Akt 2 Glasgoldene Ruinen — Senator-Geist (NEU Update #111)
            encounter_key = 'senator_geist'
        elif self.biome == 'lava':
            # Akt 3 Aschenfelder / Akt 6b Aschwunde
            encounter_key = 'echo_drache' if tier >= 3 else 'vehren'
        elif self.biome == 'swamp':
            # Akt 4 Wurzelgrab — Shulavh (NEU Update #111)
            encounter_key = 'shulavh'
        elif self.biome == 'astral':
            # Akt 5 Spiegelstadt / Akt 6c Hohlwunde
            encounter_key = 'nicht_gott' if tier >= 3 else 'velharn_trio'

        if encounter_key is not None:
            boss = _best.spawn_bestiary_mob(self, encounter_key, bx, by,
                                            wave=self.player.level + 1)
            boss.is_boss = True
            boss.is_mini_boss = False
            boss.shield_max = boss.hp_max * 0.3
            boss.shield = boss.shield_max
            self.enemies.append(boss)
            _enc.start_encounter(self, boss, encounter_key)
            # Quest-Trigger: REACH-Stage „boss_room" erfüllt
            quests_mod.on_reach_boss_room(self)
            self._dungeon_boss_spawned = True
            self.shake = max(self.shake, 12)
            return

        # Legacy-Bosse (Necromancer, Frostlord, Dragon, …)
        boss = dungeon_mod.spawn_dungeon_boss(
            self.active_dungeon_id, bx, by, self.player.level)
        # Update #95: Bosse +25 % HP, +20 % DMG extra (User-Wunsch).
        boss.hp_max *= getattr(self, 'tier_hp_mult', 1.0) * 1.25
        boss.hp = boss.hp_max
        boss.dmg *= getattr(self, 'tier_dmg_mult', 1.0) * 1.20
        rew = getattr(self, 'tier_reward_mult', 1.0)
        boss.xp = int(boss.xp * rew)
        boss.gold_range = (int(boss.gold_range[0] * rew),
                           int(boss.gold_range[1] * rew))
        self.enemies.append(boss)
        # Quest-Trigger
        quests_mod.on_reach_boss_room(self)
        self._dungeon_boss_spawned = True
        self.boss_intro = {
            'name': boss.boss_name,
            'title': getattr(boss, 'boss_title', ''),
            'timer': 3.0,
        }
        self.shake = max(self.shake, 10)
        snd.play('boss_bong', volume=0.95, bus='ui')
        snd.play('boss_intro')

    def _update_dungeon(self, dt):
        """Dungeon-State-Maschine: Boss-Room-Trigger, Completion checken.

        Boss spawnt jetzt erst wenn der Spieler den **Boss-Room** betritt
        (kein willkürlicher 700-px-Trigger mehr). Lore-Konsistenz: jeder
        Boss ist ein Event, kein Hintergrundspawn.
        """
        if self._dungeon_done_timer > 0:
            self._dungeon_done_timer -= dt
            if self._dungeon_done_timer <= 0:
                self.enter_town()
            return
        # Boss-Room-Trigger
        if not self._dungeon_boss_spawned and self.grid is not None:
            br = getattr(self.grid, 'boss_room_rect', None)
            if br is not None:
                bx, by, bw, bh = br
                px, py = self.player.pos.x, self.player.pos.y
                if bx <= px <= bx + bw and by <= py <= by + bh:
                    self._spawn_dungeon_boss_in_room()
                    return
            # Fallback: alle Gegner besiegt → trigger trotzdem
            alive = sum(1 for e in self.enemies if not e.dying)
            if alive == 0:
                self._spawn_dungeon_boss_in_room()
        else:
            # Wenn Boss tot und nicht im Dying-Anim mehr → complete
            boss_alive = any(e.is_boss and not e.dying for e in self.enemies)
            boss_dying = any(e.is_boss and e.dying for e in self.enemies)
            if not boss_alive and not boss_dying and self.active_quest \
                    and self.active_quest.boss_complete():
                self.complete_dungeon()

    # Update #121: Survival-Wave-System komplett entfernt
    # (_update_waves, _spawn_wave_enemy, _spawn_boss, _spawn_portals,
    # _next_wave). Mob-Spawning passiert ausschließlich im Dungeon-Loop
    # über `_update_dungeon` / `dungeon_gen`. Boss-Encounters über
    # `boss_encounter.start_encounter` aus dem Bestiarium-System.

    # ============================================================
    # RENDER
    # ============================================================
    def draw(self):
        # Update #113: Akt-6/7-Biomes (wound_*/hollow_word) routen über
        # FALLBACK_BIOME zu einem existierenden Render-Profil.
        biome_key = self.biome
        if biome_key not in world.BIOMES:
            from .regions import fallback_biome
            biome_key = fallback_biome(biome_key)
        biome_bg = world.BIOMES.get(biome_key, world.BIOMES['town'])['bg']
        self.screen.fill(biome_bg)
        if self.state in ('playing', 'dead'):
            self._draw_world()
        self.screen.blit(self._vignette, (0, 0))
        if self.state == 'playing':
            ui_mod.draw_hud(self.screen, self,
                            self.font_small, self.font_med, self.font_dmg)
            self._draw_skill_tooltip()
            self._draw_aura_icon()
            # PLAN A-05/A-06: Death-Transition läuft während dying-Phase
            if self.player.dying and self.death_phase == 'transition':
                ui_mod.draw_death_transition(self.screen, self)
            self._draw_buffs_bar()
            self._draw_toasts()
            # Update #131 (Y-01): First-Run-Tutorial-Overlay
            self._draw_tutorial_overlay()
            # Update #132 (B-18): Region-Übergangs-Lower-Third
            self._draw_region_transition()
            # Boss-Bar
            boss = next((e for e in self.enemies if e.is_boss), None)
            if boss:
                ui_mod.draw_boss_bar(self.screen, self.font_med, self.font_small, boss)
            # Interaktions-Prompts
            self._draw_interact_prompts()
            world.draw_minimap(self.screen, self, self.font_small)
            # Legacy-Dungeon-Quest-Panel deaktiviert — überlappte mit dem
            # neuen Velgrad-Quest-Tracker (ui.draw_hud). Dungeon-Objectives
            # bleiben im Quest-Log-Modal (J-Taste) sichtbar.
            # Dungeon-Completion-Countdown
            if self.area == 'dungeon' and self._dungeon_done_timer > 0:
                self._draw_completion_countdown()
            # Boss-Intro Splash
            if self.boss_intro is not None:
                self._draw_boss_intro()
            # Modals on top
            if self.modal == 'inventory':
                self.inv_ui.draw(self.screen, self)
            elif self.modal == 'skilltree':
                # Update #184: Atlas-UI ersetzt SkillTreeUI im Modal.
                self.atlas_ui.draw(self.screen, self)
            elif self.modal == 'crafting':
                self.craft_ui.draw(self.screen, self)
            elif self.modal == 'shop':
                self.shop_ui.draw(self.screen, self)
            elif self.modal == 'stash':
                self.stash_ui.draw(self.screen, self)
            elif self.modal == 'shrine':
                self.shrine_ui.draw(self.screen, self)
            elif self.modal == 'travel':
                self.travel_ui.draw(self.screen, self)
            elif self.modal == 'rune_choice':
                self.rune_ui.draw(self.screen, self._rune_choices)
            elif self.modal == 'questlog':
                self._draw_questlog_modal()
            elif self.modal == 'codex':
                self._draw_codex_modal()
            elif self.modal == 'fullmap':
                self._draw_fullmap_modal()
            elif self.modal == 'gemcutter':
                self._draw_gemcutter_modal()
            elif self.modal == 'pause':
                self._draw_pause_modal()
            elif self.modal == 'settings':
                self._draw_settings_modal()
            elif self.modal == 'skill_menu':
                self._draw_skill_menu_modal()
            elif self.modal == 'help':
                self._draw_help_modal()
            elif self.modal == 'memorial':
                self._draw_memorial_modal()
            elif self.modal == 'quest_turnin':
                # Update #135: Quest-Turn-In-Modal beim Quest-Abgeben.
                self._draw_quest_turnin_modal()
            elif self.modal == 'dialog':
                # ROADMAP T1.3: NPC-Dialog-Modal mit Portrait + Choices.
                self.dialog_ui.draw(self.screen, self)
        elif self.state == 'title':
            self.title_ui.save_exists = save_mod.save_exists()
            self.title_ui.draw(self.screen)
            # Update #133 (Z-01): Slot-Picker-Overlay über dem Title-Screen
            if getattr(self, '_slot_picker_open', False):
                self._draw_slot_picker_overlay()
        elif self.state == 'dead':
            ui_mod.draw_hud(self.screen, self,
                            self.font_small, self.font_med, self.font_dmg)
            ui_mod.draw_death(self.screen, self, self.font_big, self.font_med)
        # Update #83: Loot-Hover-Tooltip (POE2-Style detailed item-inspect).
        # Vor dem Cursor, damit Cursor on-top bleibt.
        if (self.state == 'playing' and self.modal is None
                and self.area in ('dungeon', 'town', 'outpost')):
            # Update #138 (M-19): Hover-Outline VOR Tooltips — gibt
            # visuelles Targeting-Feedback bevor Maus geklickt wird.
            self._draw_hover_outlines()
            self._draw_loot_hover_tooltip()
            # Update #89: Enemy-Hover-Tooltip — Name/Rarity/Affixes/Status
            self._draw_enemy_hover_tooltip()
            # Update #96: NPC-Hover-Tooltip in der Stadt + Outpost
            if self.area == 'town' or self.area == 'outpost':
                self._draw_npc_hover_tooltip()
        ui_mod.draw_cursor(self.screen, self)
        # S-07 (Update #79): Virtueller Controller-Cursor wenn Gamepad
        # angeschlossen — bronze-pulsender Ring, damit User weiß wo „A"
        # zielt.
        if self._joysticks and self.state == 'playing':
            cx, cy = self._joy_cursor
            t = (pygame.time.get_ticks() % 1000) / 1000.0
            pulse = 0.6 + 0.4 * math.sin(t * math.tau)
            r = int(14 + 4 * pulse)
            ring = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(ring, (220, 180, 80, int(200 * pulse)),
                                (r + 2, r + 2), r, 2)
            pygame.draw.circle(ring, (255, 220, 140, 220),
                                (r + 2, r + 2), 3)
            self.screen.blit(ring, (cx - r - 2, cy - r - 2))
        # Update #139 (AA-01): Debug-Overlay als letzter Pass über allem
        self._draw_debug_overlay()
        # X-09 (Update #168): Cutscene-Player als allerletzter Render-Pass
        # (oberhalb Modal-/HUD-/Cursor-Layern).
        if self.cutscene_player.is_playing:
            try:
                self.cutscene_player.draw(self.screen)
            except Exception:
                pass
        # AA-02 (Update #168): Console immer als letzter Pass.
        try:
            self.console.draw(self.screen)
        except Exception:
            pass
        # Update #171: Physics-Splitter/Throwable-Render (no-op wenn pymunk
        # disabled). Wird hier oben gezeichnet damit Splitter ueber dem
        # Floor aber unter HUD/Modal liegen.
        if self.physics is not None and self.physics.enabled:
            self._draw_physics_bodies()
        # Update #171: PyOpenGL-Post-Process-Pass (Bloom + Color-Grade +
        # Vignette). Wenn use_gl_post=False, klassischer Pygame-Flip.
        if self.gl_post is not None and self._render_surface is not None:
            # NOTE: alle Draws gingen bisher direkt auf self.screen statt
            # _render_surface. Fuer einen echten gl_post-Pfad muesste die
            # ganze Engine umgestellt werden — das ist die naechste Phase.
            # Aktueller Stand: gl_post ist initialisiert + Module verfuegbar,
            # wird aber im Default-Pfad nicht aktiv genutzt.
            self.gl_post.present(
                self.screen,
                biome=getattr(self, 'biome', 'town'),
                shake_amount=getattr(self, 'shake', 0.0),
                time_sec=pygame.time.get_ticks() * 0.001,
            )
        else:
            pygame.display.flip()

    # ============================================================
    # Update #171: Physics-Helpers (opt-in, pymunk-based)
    # ============================================================
    def spawn_splitter_burst(self, x: float, y: float, *,
                              count: int = 8,
                              color: tuple = (180, 140, 100),
                              speed_range: tuple = (80, 240),
                              life_sec: float = 1.5) -> None:
        """Spawn N Splitter-Partikel mit Pymunk-Trajectory am (x,y).

        Wird typischerweise aufgerufen wenn ein breakable-Decor zerstoert
        wird (Fass zerbricht, Vase explodiert, Glas-Saeule kollabiert).
        Wenn pymunk fehlt, no-op.
        """
        if self.physics is None or not self.physics.enabled:
            return
        self.physics.add_splitter_burst(
            (x, y), count=count, color=color,
            speed_min=speed_range[0], speed_max=speed_range[1],
            life_sec=life_sec,
        )

    def spawn_throwable(self, start_xy: tuple, target_xy: tuple, *,
                         speed: float = 300.0, color: tuple = (220, 180, 100),
                         kind_id: str = 'throwable',
                         payload: dict | None = None) -> None:
        """Spawn ein Boss-Throwable von start in Richtung target."""
        if self.physics is None or not self.physics.enabled:
            return
        sx, sy = start_xy
        tx, ty = target_xy
        dx = tx - sx
        dy = ty - sy
        d = max(0.001, (dx * dx + dy * dy) ** 0.5)
        vx = dx / d * speed
        vy = dy / d * speed
        self.physics.add_throwable(
            (sx, sy), (vx, vy), color=color, kind_id=kind_id, payload=payload,
        )

    def _draw_physics_bodies(self) -> None:
        """Render alle aktiven pymunk-bodies (Splitter, Throwables) als
        kleine Kreise mit Drop-Shadow. Camera-aware via w2s_xy."""
        if self.physics is None or not self.physics.enabled:
            return
        for entry in self.physics.iter_bodies():
            try:
                pos = entry['body'].position
                sx, sy = self.w2s_xy(pos.x, pos.y)
                sx, sy = int(sx), int(sy)
                r = max(1, int(entry.get('radius', 4)))
                col = entry.get('color', (180, 140, 100))
                # Shadow
                shadow = pygame.Surface((r * 2 + 6, r + 2), pygame.SRCALPHA)
                pygame.draw.ellipse(shadow, (0, 0, 0, 130),
                                     (0, 0, r * 2 + 6, r + 2))
                self.screen.blit(shadow, (sx - r - 3, sy + r // 2))
                # Body
                pygame.draw.circle(self.screen, col, (sx, sy), r)
                pygame.draw.circle(self.screen,
                                    tuple(max(0, c - 50) for c in col),
                                    (sx, sy), r, 1)
            except Exception:
                continue

    # Kinds, die als "stehende" Objekte (Y-sortiert) gerendert werden.
    _TALL_DECOR = {'pillar', 'torch', 'sarcophagus', 'broken_wall',
                   'ice_spike', 'frozen_pillar', 'lantern'}

    def _overlay_surf(self, key, alpha=True):
        """Update #201: Returnt eine cached fullscreen-Surface fuer
        Per-Frame-Overlays (damage_flash, weather-tints, vignettes).

        Caller MUSS die Surface vor dem Bemalen leeren — fill((0,0,0,0))
        fuer SRCALPHA oder fill(color) fuer plain Surface. Wir machen das
        bewusst NICHT hier, damit das single-pass `fill((r,g,b,a))` aus
        dem alten Code unveraendert weiterwerkelt.

        Wahnsinnig viel Heap-Churn gespart: 5.76 MB SRCALPHA-Alloc fuer
        eine 1600x900-Surface, bis zu 9x pro Frame in dichtem Combat.
        """
        cached = self._overlay_surf_cache.get(key)
        if cached is None:
            flags = pygame.SRCALPHA if alpha else 0
            cached = pygame.Surface((SCREEN_W, SCREEN_H), flags)
            self._overlay_surf_cache[key] = cached
        return cached

    def _draw_world(self):
        # 1) Boden: Dungeon-Grid wenn vorhanden, sonst Biom-Kachelung
        # Update #183 (User-Fix „Kreise gehen ueber Waende"): Surface-FX
        # (Wet/Ice/Scorched/Glass) werden jetzt ZWISCHEN Floor und Walls
        # gerendert.  Vorher kamen sie nach Lighting/Walls und konnten
        # so ueber Wand-Sprites bleeden.  Tradeoff: leichtes Darkening
        # durch das Lighting-Overlay — passt aber zur Lore (nasser
        # Boden ist natuerlich etwas dunkler).
        if self.grid is not None:
            world.draw_dungeon_floor(self.screen, self.grid, self.biome,
                                      self.w2s_xy, self.camera)
            try:
                self.surface_fx.draw(self, self.screen)
            except Exception:
                pass
            world.draw_dungeon_walls(self.screen, self.grid, self.biome,
                                      self.w2s_xy, self.camera)
            world.draw_traps(self.screen, self.grid, self.w2s_xy, self.camera)
        else:
            world.draw_floor(self.screen, self.biome, self.camera)
            try:
                self.surface_fx.draw(self, self.screen)
            except Exception:
                pass
        # 1.5) (Update #187) Wolken NICHT mehr hier — sie wurden ganz frueh
        # gezeichnet und von Decor/Entities/Fog/Lighting ueberdeckt, der
        # Spieler sah sie "unter der Map".  Jetzt: zusammen mit dem Fog
        # spaet als atmosphaerischer Overlay (siehe weiter unten).
        # 1.6) Blut-Pfützen direkt auf Boden
        for bp in self.blood_pools:
            sx, sy = self.w2s_xy(bp.x, bp.y)
            if -100 < sx < SCREEN_W + 100 and -100 < sy < SCREEN_H + 100:
                weather_mod.draw_blood_pool(self.screen, bp, int(sx), int(sy))
        # 1.7) Update #138 (V-06): Footprints unter Decor + Entities
        self._draw_footprints()

        # 2) Boden-Decor (klein, liegt flach)
        for t in self.tiles:
            if t.kind in self._TALL_DECOR:
                continue
            sx, sy = self.w2s_xy(t.x, t.y)
            if -150 < sx < SCREEN_W + 150 and -150 < sy < SCREEN_H + 150:
                world.draw_decor(self.screen, t, (sx, sy), self.biome)

        # 3) Loot (am Boden) — Update #190: Off-Screen-Culling
        for l in self.loot:
            sx, sy = self.w2s(l.pos)
            if -100 < sx < SCREEN_W + 100 and -100 < sy < SCREEN_H + 100:
                self._draw_loot(l)
        # Update #136 (O-23): Flying-Pickup-Animationen (über Loot, vor Entities)
        if self._loot_animations:
            self._draw_loot_animations()

        # 3.5) E-05 (Update #60): Arena-Features rendern.
        if self.arena_features:
            self._draw_arena_features()

        # 4) Stehende Objekte Y-sortiert (Pillars, Gegner, Spieler, Portale)
        # Update #190: Off-Screen-Culling fuer Enemies/NPCs/Portale.
        # Vorher wurden alle 35 Mobs durch die volle Sprite-Pipeline
        # geschickt, auch wenn off-screen. ~10-15ms Draw-Zeit gespart
        # bei dichten Raeumen.
        tall = []
        # Cull-Box: 200 px Rand fuer grosse Sprites (Bosse, Decor mit
        # Crest etc.); kleiner als der Sprite-Half-Diagonal-Bounds.
        cull_pad = 200
        in_view = (lambda sx, sy:
                   -cull_pad < sx < SCREEN_W + cull_pad
                   and -cull_pad < sy < SCREEN_H + cull_pad)
        for t in self.tiles:
            if t.kind in self._TALL_DECOR:
                sx, sy = self.w2s_xy(t.x, t.y)
                if in_view(sx, sy):
                    tall.append((t.y, 'decor', t, sx, sy))
        for e in self.enemies:
            sx, sy = self.w2s(e.pos)
            if in_view(sx, sy):
                tall.append((e.pos.y, 'enemy', e, sx, sy))
        for portal in self.portals:
            sx, sy = self.w2s(portal.pos)
            if in_view(sx, sy):
                tall.append((portal.pos.y, 'portal', portal, sx, sy))
        for npc in self.npcs:
            sx, sy = self.w2s(npc.pos)
            if in_view(sx, sy):
                tall.append((npc.pos.y, 'npc', npc, sx, sy))
        for dp in self.dungeon_portals:
            sx, sy = self.w2s(dp.pos)
            if in_view(sx, sy):
                tall.append((dp.pos.y, 'dportal', dp, sx, sy))
        for op in self.outpost_portals:
            sx, sy = self.w2s(op.pos)
            if in_view(sx, sy):
                tall.append((op.pos.y, 'oportal', op, sx, sy))
        if self.outpost_return_portal is not None:
            rp = self.outpost_return_portal
            sx, sy = self.w2s(rp.pos)
            if in_view(sx, sy):
                tall.append((rp.pos.y, 'oportal', rp, sx, sy))
        psx, psy = self.w2s(self.player.pos)
        tall.append((self.player.pos.y, 'player', self.player, psx, psy))

        tall.sort(key=lambda t: t[0])
        for _, kind, obj, sx, sy in tall:
            if kind == 'decor':
                world.draw_decor(self.screen, obj, (sx, sy), self.biome)
            elif kind == 'enemy':
                self._draw_enemy_at(obj, sx, sy)
            elif kind == 'portal':
                world.draw_portal(self.screen, obj, (sx, sy))
            elif kind == 'npc':
                sprites.draw_npc_at(self.screen, obj, sx, sy)
                # Quest-Marker über NPC: '!' = neue Quest, '?' = Stage-Return.
                # Update #145: player-aware → locked Quests zeigen kein „!"
                # Update #200: y-Offset von -64 auf -130 angepasst (neuer
                # NPC-Sprite ist 124px hoch, vorher 38px).
                log = getattr(self, 'quest_log', None)
                if log is not None:
                    mark = log.npc_marker(obj.name, player=self.player)
                    if mark:
                        self._draw_npc_quest_marker(sx, sy - 130, mark)
            elif kind == 'dportal':
                sprites.draw_dungeon_portal_at(self.screen, obj, sx, sy)
                # Update #151: Quest-driven Portal-Highlighting — der
                # Pfeil + Label kommt jetzt auf JEDES Portal, das die
                # aktive Main-Quest braucht (nicht nur die Krypta).
                if self.area == 'town':
                    qkind, qkey, qlbl = self._get_quest_target_portal()
                    if (qkind == 'dungeon'
                            and getattr(obj, 'dungeon_id', None) == qkey):
                        self._draw_tutorial_portal_arrow(sx, sy, label=qlbl)
            elif kind == 'oportal':
                self._draw_outpost_portal(obj, sx, sy)
                # Update #151: Quest-driven Outpost-Highlight
                if self.area == 'town' and not getattr(obj, '_locked', False):
                    qkind, qkey, qlbl = self._get_quest_target_portal()
                    if (qkind == 'outpost'
                            and getattr(obj, 'outpost_key', None) == qkey):
                        self._draw_tutorial_portal_arrow(sx, sy, label=qlbl)
            elif kind == 'player':
                self._draw_player_at(sx, sy)

        # 5) Projektile (über Charakteren)
        for pr in self.projectiles:
            self._draw_projectile(pr)

        # 5.5) Update #120: District-Labels in Stadt + Outpost.
        # Lore-Akzent für die Brassweir-Quartiere.
        if self.area in ('town', 'outpost'):
            self._draw_district_labels()

        # 6) Dynamisches Licht-Overlay
        self.lighting.begin_frame()
        self.lighting.gather_default(self)
        # Tag/Nacht in Stadt
        _town_grading_tint = None
        if self.area == 'town':
            t = self.stats.get('time_played', 0.0) if self.stats else 0.0
            ambient = weather_mod.day_night_ambient(t)
            self.lighting.ambient_alpha = weather_mod.day_night_ambient_alpha(t)
            # Update #138 (M-21): Color-Grading-Tint cachen für Post-Pass
            _town_grading_tint = weather_mod.town_color_grading(t)
        else:
            # Update #178: Akt 6/7 Biomes (wound_* + hollow_word) ambient
            # colors ergaenzt. Sehr dunkles RGB → starke Multiply-Wirkung
            # mit der Lighting-System darkness-Surface.
            ambient = {
                'crypt':        (8, 6, 12),
                'frost':        (6, 10, 22),
                'lava':         (14, 4, 4),
                'desert':       (40, 30, 12),
                'swamp':        (8, 16, 12),
                'astral':       (4, 2, 18),       # tiefes violett
                'town':         (16, 14, 12),
                # Akt 6 Wounds — Lore-mood-spezifisch
                'wound_salt':   (12, 10, 8),      # salzige Daemmerung
                'wound_ash':    (16, 6, 4),       # verbrannt-rotglut
                'wound_hollow': (4, 4, 14),       # void-purple
                # Akt 7 Hollow-Word
                'hollow_word':  (12, 8, 16),      # bronze-Aether
            }.get(self.biome, (8, 6, 12))
            self.lighting.ambient_alpha = 130
        self.lighting.render(self.screen, ambient_color=ambient)

        # Update #138 (M-21): Town-Color-Grading Post-Pass via BLEND_MULT.
        # Morgens warm, mittags neutral, abends rosé, nachts kalt-blau.
        # Subtil — Lore-Akzent über den Tag, nicht stark genug um die
        # Stadt-Lesbarkeit zu beeinträchtigen.
        if _town_grading_tint is not None:
            tr, tg, tb = _town_grading_tint
            if tr != 255 or tg != 255 or tb != 255:
                tint = self._overlay_surf('town_grading', alpha=False)
                tint.fill((tr, tg, tb))
                self.screen.blit(tint, (0, 0),
                                  special_flags=pygame.BLEND_RGB_MULT)

        # U-09 (Update #168): Globaler Lightning-Flash über Light-Pass.
        # Wird durch cast_lightning / Boss-Storm / Rain-Lightning aktiviert.
        # Photosensitive via request_flash bereits gefiltert.
        if getattr(self, '_lightning_flash_t', 0.0) > 0.0:
            self._lightning_flash_t -= 0.016
            try:
                self.lighting.render_lightning_flash(
                    self.screen,
                    intensity=max(0.0, self._lightning_flash_t) * 0.35)
            except Exception:
                pass
        # M-05 (Update #67): Volumetric-Fog pro Biome + Rain-Bonus.
        # Crypt = blaugrauer Nebel, Swamp = gelb-grüner Sumpf-Dunst, Frost =
        # weiß-blauer Whiteout, etc.  Rain steigert die Fog-Dichte temporär.
        FOG_CONFIG = {
            'crypt':  ((140, 150, 170), 22),
            'frost':  ((200, 215, 235), 28),
            'lava':   ((140, 60, 50), 18),
            'swamp':  ((110, 130, 90), 30),
            'astral': ((140, 110, 200), 20),
            'desert': ((220, 200, 140), 12),
            'town':   ((180, 170, 150), 8),
        }
        fcfg = FOG_CONFIG.get(self.biome)
        if fcfg is not None and self.area == 'dungeon':
            fog_col, base_alpha = fcfg
            rain_boost = int(40 * getattr(self, 'rain_intensity', 0.0))
            t_s = pygame.time.get_ticks() / 1000.0
            # Update #186: camera + biome-wind weiterreichen damit der Fog
            # parallaxiert + organisch driftet (statt am Screen zu kleben).
            wind_vec = getattr(self.weather, 'wind_vector', (1.0, 0.0))
            self.lighting.render_fog(
                self.screen, fog_col, base_alpha + rain_boost, t_s,
                camera=self.camera, wind=wind_vec)
        # Update #190 (User-Fix "alles klebt an der Camera"):  Wolken
        # werden NICHT mehr als Screen-Overlay gerendert.  Egal wie sie
        # sich bewegen (screen-anchored / world-anchored), sie werden als
        # separater Layer ueber dem Dungeon wahrgenommen — das war das
        # Kern-Problem aller Iterationen #184..#189.
        #
        # Wenn Wolken-Schatten zurueck sollen: muessen sie IN den Floor-
        # Pass integriert werden (z.B. als dunkle Patches in world.draw_
        # dungeon_floor), nicht als separater spaeter Overlay-Draw.  So
        # sind sie buchstaeblich Teil des Bodens, kein eigener Layer.
        #
        # weather.set_biome() pre-baked die Sprites weiterhin (billig);
        # sie werden nur nicht mehr gezeichnet.  Stars (Astral) und
        # Partikel-Wetter (Regen/Schnee) bleiben aktiv via andere Pfade.

        # V-01..V-04 (Update #168 / #183): Surface-FX-Decals werden jetzt
        # in _draw_world() zwischen Floor und Walls gerendert (siehe oben).
        # Damit bleeden Wet/Ice/Scorched-Patches nicht mehr ueber die
        # Wand-Sprites hinweg.  Hier kein zweiter Pass mehr noetig.

        # V-08 Cloth-Sim Banner — gerendert spaet damit sie ueber dem Boden
        # liegen aber unter Entities/Particles.
        for cloth in self.cloth_banners:
            try:
                cloth.draw(self, self.screen)
            except Exception:
                pass

        # 7) Helle Effekte ÜBER der Beleuchtung
        # C-09: Partikel nach Layer-Priority sortiert rendern, damit
        # TELEGRAPH/UI_OVERLAY garantiert über AMBIENT/GAMEPLAY liegen
        # (Briefing C.4 — kritische VFX müssen immer sichtbar bleiben).
        for p in sorted(self.particles, key=fx.particle_render_priority):
            self._draw_particle(p)
        for b in self.bolts:     self._draw_bolt(b)
        for f in self.floaters:  self._draw_floater(f)

        # 8) Wetter-Partikel im Vordergrund (auch über Lighting)
        self.weather.draw_particles(self.screen)
        # 8.25) Schwarze Löcher (Verzerrung + Aura)
        for bh in self.black_holes:
            sx_b, sy_b = self.w2s(bh['pos'])
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            r = int(bh['radius'])
            # Äußere Aura (rosa-violett)
            aura = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            for k in range(5, 0, -1):
                alpha = int(40 / k * (0.5 + pulse * 0.5))
                pygame.draw.circle(aura, (140, 60, 220, alpha),
                                    (r, r), r - k * 18)
            self.screen.blit(aura, (sx_b - r, sy_b - r))
            # Sing-spiralen
            import math as _m
            t = pygame.time.get_ticks() * 0.003
            for k in range(20):
                ang = t + k * 0.4
                rad = (k * 4 + (pygame.time.get_ticks() % 1000) * 0.04) % (r * 0.9)
                px = sx_b + _m.cos(ang) * rad
                py = sy_b + _m.sin(ang) * rad
                pygame.draw.circle(self.screen, (200, 100, 240),
                                    (int(px), int(py)), 2)
            # Schwarze Mitte
            pygame.draw.circle(self.screen, (0, 0, 0), (sx_b, sy_b), 30)
            pygame.draw.circle(self.screen, (60, 20, 80), (sx_b, sy_b), 30, 3)

        # 8.25) Unified AoE-Decals (PLAN C-05/C-06/C-07)
        self._draw_decals()

        # 8.3) Ground-Cracks (glühende rote Risse)
        for c in self.ground_cracks:
            sx_a, sy_a = self.w2s(c['pos'])
            end_x = c['pos'].x + c['dir'].x * c['len']
            end_y = c['pos'].y + c['dir'].y * c['len']
            sx_b, sy_b = self.w2s_xy(end_x, end_y)
            life_frac = c['time_left'] / 2.5
            # Glow-Linie
            glow_w = max(2, int(8 * life_frac))
            pygame.draw.line(self.screen, (255, 100, 30),
                              (sx_a, sy_a), (sx_b, sy_b), glow_w + 2)
            pygame.draw.line(self.screen, (255, 220, 100),
                              (sx_a, sy_a), (sx_b, sy_b), max(1, glow_w // 2))
            # Random Feuer-Funken entlang
            if random.random() < 0.3:
                t = random.random()
                mid_x = sx_a + (sx_b - sx_a) * t
                mid_y = sy_a + (sy_b - sy_a) * t
                pygame.draw.circle(self.screen, (255, 200, 80),
                                    (int(mid_x), int(mid_y)), 2)

        # 8.35) Falling Rocks (Warnung + Aufprall-Schatten)
        for r in self.falling_rocks:
            sx_r, sy_r = self.w2s_xy(r['x'], r['y'])
            # Wachsender Schatten am Boden zeigt Aufprall
            growing = 1.0 - (r['timer'] / 1.0)
            radius = int(20 + 20 * growing)
            shadow = pygame.Surface((radius * 2, radius), pygame.SRCALPHA)
            pygame.draw.ellipse(shadow, (0, 0, 0, int(140 * growing)),
                                 (0, 0, radius * 2, radius))
            self.screen.blit(shadow, (sx_r - radius, sy_r - radius // 2))
            # Fallender Stein über dem Boden
            rock_y_offset = int(400 * r['timer'])
            pygame.draw.circle(self.screen, (90, 70, 50),
                                (sx_r, sy_r - rock_y_offset), 14)
            pygame.draw.circle(self.screen, (60, 45, 30),
                                (sx_r, sy_r - rock_y_offset), 14, 2)

        # 8.4) Heal-Field-Renders (grüne Zone am Boden) — defensiv
        for hf in self.heal_fields:
            if 'pos' not in hf or 'radius' not in hf:
                continue
            sx, sy = self.w2s(hf['pos'])
            r = int(hf['radius'])
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            zone = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
            pygame.draw.circle(zone, (140, 240, 160, int(60 + pulse * 40)),
                               (r, r), r)
            pygame.draw.circle(zone, (200, 255, 200, 160), (r, r), r, 3)
            self.screen.blit(zone, (sx - r, sy - r))

        # 8.5) Boss Charged-Attack Markierungen
        for e in self.enemies:
            if e.is_boss and e.charged_attack is not None:
                ca = e.charged_attack
                sx, sy = self.w2s(ca['target_pos'])
                r = int(ca['radius'])
                # Pulse je näher Timer
                t = max(0.0, ca['timer'])
                phase = (1.2 - t) / 1.2
                alpha = int(120 + 80 * abs(math.sin(t * 12)))
                warn = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(warn, (255, 60, 30, alpha),
                                   (r + 2, r + 2), r, 4)
                inner_r = int(r * phase)
                if inner_r > 4:
                    pygame.draw.circle(warn, (255, 180, 80, alpha // 2),
                                       (r + 2, r + 2), inner_r, 2)
                self.screen.blit(warn, (sx - r - 2, sy - r - 2))

        # 8.6) Earthquake-Aftershock Markierungen
        for shock in self.pending_aftershocks:
            sx_a, sy_a = self.w2s(shock['pos'])
            r = int(shock['radius'])
            t = max(0, shock['timer'])
            phase = (1.2 - t) / 1.2
            warn = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(warn, (255, 140, 60,
                                        int(80 + 80 * abs(math.sin(t * 8)))),
                                (r + 2, r + 2), r, 5)
            pygame.draw.circle(warn, (180, 100, 40, 100),
                                (r + 2, r + 2), int(r * phase), 3)
            self.screen.blit(warn, (sx_a - r - 2, sy_a - r - 2))

        # 8.7) Komet-Warnung am Boden (großer Kreis + Schatten oben)
        for cmt in self.pending_comets:
            sx_c, sy_c = self.w2s(cmt['pos'])
            r = int(cmt['radius'])
            t = max(0, cmt['timer'])
            # Boden-Kreis
            warn = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            pygame.draw.circle(warn, (180, 220, 255,
                                        int(140 + 60 * abs(math.sin(t * 6)))),
                                (r + 2, r + 2), r, 6)
            pygame.draw.circle(warn, (255, 255, 255, 80),
                                (r + 2, r + 2),
                                int(r * (1 - t / 1.5)), 2)
            self.screen.blit(warn, (sx_c - r - 2, sy_c - r - 2))
            # Komet von oben (fallendes Objekt mit Glow)
            comet_y_offset = int(500 * t)
            cy_top = sy_c - comet_y_offset
            glow = pygame.Surface((60, 60), pygame.SRCALPHA)
            pygame.draw.circle(glow, (180, 220, 255, 200), (30, 30), 24)
            self.screen.blit(glow, (sx_c - 30, cy_top - 30))
            pygame.draw.circle(self.screen, (220, 240, 255), (sx_c, cy_top), 16)
            pygame.draw.circle(self.screen, (255, 255, 255), (sx_c - 4, cy_top - 4), 6)
            # Schweif
            for k in range(6):
                tail_y = cy_top - k * 14
                if tail_y > 0:
                    pygame.draw.circle(self.screen,
                                        (180, 220, 255, 100), (sx_c, tail_y),
                                        max(2, 10 - k))

        # 9) Meteor-Warnung am Boden
        if hasattr(self, '_meteor_pending') and self._meteor_pending:
            spec = self._meteor_pending
            sx, sy = self.w2s(spec['pos'])
            t = spec['timer']
            # Pulsierender Ring
            alpha = int(160 * (1.0 - abs(math.sin(t * 6))))
            r = int(spec['radius'])
            warn = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
            pygame.draw.circle(warn, (255, 60, 30, alpha),
                               (r + 4, r + 4), r, 6)
            pygame.draw.circle(warn, (255, 200, 100, alpha // 2),
                               (r + 4, r + 4), r - 8, 2)
            self.screen.blit(warn, (sx - r - 4, sy - r - 4))

        # Settings: Photosensitive-Modus reduziert Flash-Intensität
        flash_mult = 0.3 if self.settings.get('photosensitive', False) else 1.0
        # 8) Schaden-Bildschirm-Blitz
        if self._damage_flash > 0:
            flash = self._overlay_surf('damage_flash')
            flash.fill((255, 30, 30, int(80 * self._damage_flash * flash_mult)))
            self.screen.blit(flash, (0, 0))
        # Update #136 (M-11): Low-HP-Vignette + Chromatic-Aberration-Approx.
        # Bei HP < 25 % pulsiert ein roter Radial-Vignette-Rand im Herzschlag-
        # Takt; Spieler spürt visuell den Druck.  Photosensitive-Mode dimmt
        # die Intensität.  Pygame hat kein echtes RGB-Channel-Shift —
        # statt dessen layern wir 2 dezente Cyan/Magenta-Ränder am
        # äußeren Bildschirm-Rand für den Aberration-Eindruck.
        try:
            from . import progression as _prog
            eff = _prog.effective(self.player)
            hp_pct = self.player.hp / max(1, eff['hp_max'])
        except Exception:
            hp_pct = 1.0
        if (hp_pct < 0.25 and self.state == 'playing'
                and not self.player.dying):
            t = pygame.time.get_ticks() * 0.006
            # Herzschlag: 2 Pulse pro Zyklus (lub-dub)
            beat = (math.sin(t) + math.sin(t * 1.3) * 0.4) * 0.5 + 0.5
            intensity = (1.0 - hp_pct / 0.25)  # 0..1, voll bei 0% HP
            base_a = int((50 + 80 * beat) * intensity * flash_mult)
            # Vignette: weicher Rot-Radial-Fade von außen
            vig = self._overlay_surf('lowhp_vignette')
            vig.fill((0, 0, 0, 0))   # SRCALPHA reset, Layer schreiben rect
            # 4 Layer für sanften Falloff
            for k in range(4):
                t_k = k / 3.0
                pad_x = int(SCREEN_W * 0.05 * t_k)
                pad_y = int(SCREEN_H * 0.05 * t_k)
                a = int(base_a * (1.0 - t_k))
                pygame.draw.rect(vig, (180, 30, 30, a),
                                  (pad_x, pad_y,
                                   SCREEN_W - pad_x * 2,
                                   SCREEN_H - pad_y * 2),
                                  3 + k * 2)
            self.screen.blit(vig, (0, 0))
            # Chromatic-Aberration-Approx: Cyan/Magenta-Säume am Bildrand
            ca_a = int(60 * intensity * flash_mult)
            if ca_a > 0:
                ca_top = pygame.Surface((SCREEN_W, 4), pygame.SRCALPHA)
                ca_top.fill((255, 80, 220, ca_a))
                self.screen.blit(ca_top, (2, 0))
                ca_bot = pygame.Surface((SCREEN_W, 4), pygame.SRCALPHA)
                ca_bot.fill((80, 220, 255, ca_a))
                self.screen.blit(ca_bot, (-2, SCREEN_H - 4))
        # Boss-Death-Cinematic-Flash
        if self.boss_flash > 0:
            flash = self._overlay_surf('boss_flash')
            flash.fill((255, 240, 200, int(200 * self.boss_flash * flash_mult)))
            self.screen.blit(flash, (0, 0))
        # Time-Freeze: blauer Tint + dezenter Rand-Effekt
        if self.time_freeze_left > 0:
            tint = self._overlay_surf('time_freeze')
            tint.fill((140, 200, 255, 50))
            self.screen.blit(tint, (0, 0))
            pygame.draw.rect(self.screen, (200, 230, 255),
                              (0, 0, SCREEN_W, SCREEN_H), 6)
        # Wetter-Event-Overlays
        if self.sandstorm_left > 0:
            tint = self._overlay_surf('sandstorm_tint')
            tint.fill((220, 180, 100, 70))
            self.screen.blit(tint, (0, 0))
            # Sand-Streifen die diagonal scrollen
            for k in range(30):
                x = (pygame.time.get_ticks() // 4 + k * 80) % (SCREEN_W + 200) - 100
                y = (k * 50) % SCREEN_H
                pygame.draw.line(self.screen, (240, 200, 130),
                                  (x, y), (x + 20, y + 3), 1)
        if self.icestorm_left > 0:
            tint = self._overlay_surf('icestorm_tint')
            tint.fill((180, 220, 255, 55))
            self.screen.blit(tint, (0, 0))
            # Schneeflocken zusätzlich
            for k in range(40):
                x = (pygame.time.get_ticks() // 6 + k * 60) % SCREEN_W
                y = (pygame.time.get_ticks() // 10 + k * 30) % SCREEN_H
                pygame.draw.circle(self.screen, (240, 250, 255), (x, y), 2)
        if self.ashrain_left > 0:
            tint = self._overlay_surf('ashrain_tint')
            tint.fill((180, 80, 30, 60))
            self.screen.blit(tint, (0, 0))
            for k in range(20):
                x = (pygame.time.get_ticks() // 5 + k * 90) % SCREEN_W
                y = (pygame.time.get_ticks() // 8 + k * 40) % SCREEN_H
                pygame.draw.circle(self.screen, (255, 140, 60), (x, y), 2)
        if self.miasma_left > 0:
            tint = self._overlay_surf('miasma_tint')
            tint.fill((100, 160, 80, 60))
            self.screen.blit(tint, (0, 0))
        if self.cosmic_pulse_left > 0:
            tint = self._overlay_surf('cosmic_pulse_tint')
            tint.fill((180, 100, 240, 50))
            self.screen.blit(tint, (0, 0))

        # M-10 (Update #168): Bloom-Pass als letzter Render-Schritt von
        # _draw_world.  Settings-Toggle: bloom = off|low|high.
        bloom_mode = self.settings.get('bloom', 'off') if hasattr(self, 'settings') else 'off'
        if bloom_mode == 'low':
            try:
                self.lighting.render_bloom(
                    self.screen, threshold=205, strength=0.32)
            except Exception:
                pass
        elif bloom_mode == 'high':
            try:
                self.lighting.render_bloom(
                    self.screen, threshold=180, strength=0.55)
            except Exception:
                pass

        # M-12 (Update #168): Heat-Distortion ueber Lava-Cells + Fire-AoE.
        # Performance: Per-Cell render kostet ~22 subsurface.copy + 22 blit
        # in lighting.render_heat_distortion -> bei 24 Cells = ~528
        # subsurface-Ops/Frame, leichte Hauptursache fuer Frame-Drops.
        # Drei Sicherungen gegen Ruckeln:
        #   1. Biome-Early-Exit: nur 'lava' / 'wound_ash' haben Lava-Tiles
        #   2. Cell-Cap 24 -> 8 + Iteration mit early-break
        #   3. Frame-Interleave (jeden 2. Frame skippen): halbiert Cost
        #      bei kaum sichtbarer Aenderung des Heat-Wave-Tempos
        if (self.settings.get('heat_distortion', True)
                and self.area == 'dungeon'
                and getattr(self, 'biome', '') in ('lava', 'wound_ash')):
            self._heat_frame_phase = (
                getattr(self, '_heat_frame_phase', 0) + 1) % 2
            if self._heat_frame_phase == 0:
                heat_cells = []
                for t in self.tiles:
                    if t.kind == 'lava_pool' or t.kind == 'ember':
                        sx, sy = self.w2s_xy(t.x, t.y)
                        if -48 <= sx <= SCREEN_W + 48 and -48 <= sy <= SCREEN_H + 48:
                            heat_cells.append((sx - 22, sy - 22, 44, 44))
                            if len(heat_cells) >= 8:
                                break
                # Active Fire-Decals — Decal ist eine Klasse (sf/entities.py),
                # nicht ein Dict.  Attribute statt .get().  DECAL_KIND.DOT
                # ('dot') deckt fire/poison/bleed ab.
                if len(heat_cells) < 8:
                    for d in self.decals:
                        kind = getattr(d, 'kind', None)
                        dmg_type = getattr(d, 'dmg_type', None)
                        if dmg_type == 'fire' or kind == 'dot':
                            pos = getattr(d, 'pos', None)
                            if pos is None:
                                continue
                            sx, sy = self.w2s(pos)
                            r = int(getattr(d, 'radius', 40))
                            heat_cells.append((sx - r, sy - r, r * 2, r * 2))
                            if len(heat_cells) >= 8:
                                break
                if heat_cells:
                    try:
                        t_s = pygame.time.get_ticks() / 1000.0
                        self.lighting.render_heat_distortion(
                            self.screen, heat_cells, t_s, amplitude=3)
                    except Exception:
                        pass

        # M-13 (Update #168): Optional CRT/Dither-Filter.
        crt_mode = self.settings.get('crt_filter', 'off')
        if crt_mode == 'scanlines':
            try:
                self._draw_crt_scanlines()
            except Exception:
                pass
        elif crt_mode == 'dither':
            try:
                self._draw_dither_overlay()
            except Exception:
                pass

    def _draw_crt_scanlines(self):
        """M-13 (Update #168): Horizontaler Scanline-Overlay (CRT-Look).

        Statisch gecachte 1-Pixel-Stripe-Surface mit α20.  Sehr cheap.
        """
        if not hasattr(self, '_crt_overlay'):
            o = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            for y in range(0, SCREEN_H, 2):
                pygame.draw.line(o, (0, 0, 0, 28), (0, y), (SCREEN_W, y))
            self._crt_overlay = o
        self.screen.blit(self._crt_overlay, (0, 0))

    def _draw_dither_overlay(self):
        """M-13 (Update #168): Bayer-4x4-Dither auf einer 1x-Surface.

        Visualisierte Pixel-Art-Aesthetik.  Sehr leicht — Cache als 4x4-
        Tile + Tile-Fill ueber den ganzen Screen.
        """
        if not hasattr(self, '_dither_overlay'):
            bayer = [
                [0,  8,  2, 10],
                [12, 4, 14,  6],
                [3, 11,  1,  9],
                [15, 7, 13,  5],
            ]
            tile = pygame.Surface((4, 4), pygame.SRCALPHA)
            for y in range(4):
                for x in range(4):
                    a = int(bayer[y][x] * 6)
                    tile.set_at((x, y), (0, 0, 0, a))
            full = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            for ty in range(0, SCREEN_H, 4):
                for tx in range(0, SCREEN_W, 4):
                    full.blit(tile, (tx, ty))
            self._dither_overlay = full
        self.screen.blit(self._dither_overlay, (0, 0))

    def _draw_interact_prompts(self):
        """Zeigt 'F: ...' wenn nahe an etwas Interaktivem."""
        p = self.player
        if self.area == 'town' or self.area == 'outpost':
            npc = town_mod.npc_in_range(p, self.npcs)
            if npc:
                label = {'vendor': f'F: Mit {npc.name} sprechen',
                         'stash':  f'F: Truhe öffnen ({npc.name})',
                         'mystic': f'F: Mit {npc.name} sprechen'}.get(npc.kind, 'F: Sprechen')
                self._show_prompt(label, (220, 180, 110))
                return
            dp = town_mod.dungeon_portal_in_range(p, self.dungeon_portals)
            if dp:
                from .constants import DUNGEONS
                spec = DUNGEONS[dp.dungeon_id]
                req = spec['level_req']
                color = GOLD_BRIGHT if p.level >= req else (200, 80, 80)
                completed = '✓ ' if dp.dungeon_id in p.completed_dungeons else ''
                self._show_prompt(
                    f'F: {completed}{spec["name"]} betreten (Stufe {req}+)',
                    color)
                return
            # Update #113: OutpostPortal in Brassweir → Camp betreten
            for op_p in self.outpost_portals:
                if (op_p.pos - p.pos).length() < 45:
                    self._show_prompt(
                        f'F: Reisen nach {op_p.label}',
                        (220, 200, 140))
                    return
            # Outpost-Return-Portal (im Camp) → zurück nach Brassweir
            rp = self.outpost_return_portal
            if rp and (rp.pos - p.pos).length() < 45:
                self._show_prompt('F: Zurück nach Brassweir',
                                  (220, 200, 140))
                return
            # Update #146 (User-Report „Altäre/Notizen nicht erkennbar"):
            # Prompt-Hint auch für Mahnmal-Stele + Lore-Tafel.
            for t in self.tiles:
                kind = getattr(t, 'kind', None)
                if kind == 'mahnmal_stele':
                    dx = p.pos.x - t.x; dy = p.pos.y - t.y
                    if dx * dx + dy * dy < 70 * 70:
                        if self.area == 'outpost':
                            self._show_prompt('F: Reisen (Mahnmal-Stele)',
                                                (220, 180, 110))
                        else:
                            self._show_prompt('F: Aspekt-Schrein öffnen',
                                                (220, 180, 110))
                        return
                if kind == 'lore_tablet':
                    dx = p.pos.x - t.x; dy = p.pos.y - t.y
                    if dx * dx + dy * dy < 60 * 60:
                        if not getattr(t, 'lore_read', False):
                            self._show_prompt('F: Lore-Tafel lesen (+1 Fragment)',
                                                (240, 200, 100))
                        else:
                            self._show_prompt('F: Lore-Tafel (gelesen)',
                                                (160, 140, 100))
                        return
        else:
            for portal in self.portals:
                if (portal.pos - p.pos).length() < 40:
                    ui_mod.draw_portal_prompt(self.screen, self.font_med,
                                              self.font_small, portal)
                    return

    def _show_prompt(self, text, color):
        surf = self.font_med.render(text, True, color)
        x = SCREEN_W // 2 - surf.get_width() // 2
        y = SCREEN_H - 200
        bg = pygame.Surface((surf.get_width() + 24, surf.get_height() + 12),
                            pygame.SRCALPHA)
        bg.fill((10, 8, 6, 200))
        self.screen.blit(bg, (x - 12, y - 6))
        pygame.draw.rect(self.screen, color,
                         (x - 12, y - 6, surf.get_width() + 24,
                          surf.get_height() + 12), 1)
        self.screen.blit(surf, (x, y))

    def _draw_skill_menu_modal(self):
        """PoE2-Style Skill-Menue: zeigt alle existierenden Skills + Status.

        Update #30: Velgrad-Tome-Page mit Filigree + Aspekt-Akzent.
        """
        from .skills import SKILL_INFO
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        w, h = 920, 620
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament-Gradient
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            t = py / max(1, h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        _asp.draw_filigree_corners(
            self.screen, pygame.Rect(x, y, w, h), bronze, size=26)
        _asp.draw_aspect_watermark(
            self.screen, pygame.Rect(x, y, w, h),
            self.player.cls, alpha=14)
        # Mittellinie (Buch-Falz)
        pygame.draw.line(self.screen, pal['deep'],
                          (x + w // 2, y + 80),
                          (x + w // 2, y + h - 40), 1)
        # Header
        eyebrow = self.font_small.render(
            '— LIBER SKILL-GRIMOIRE —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (x + w // 2 - eyebrow.get_width() // 2, y + 16))
        title_text = 'S K I L L - G R I M O I R E'
        title = self.font_big.render(title_text, True, pal['halo'])
        title_sh = self.font_big.render(title_text, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (x + w // 2 - title.get_width() // 2 + 2,
                           y + 36 + 2))
        self.screen.blit(title,
                          (x + w // 2 - title.get_width() // 2, y + 36))
        _asp.draw_ornament_divider(
            self.screen, x + 24, y + 84, w - 48, bronze)

        # Skill-Liste mit Status (POE2-style umfassend)
        all_skills = [
            ('Q', 'fireball',   'Feuerball',     'Spell · Projectile · Fire · AoE', 1),
            ('W', 'lightning',  'Kettenblitz',   'Spell · Chaining · Lightning', 2),
            ('E', 'heal',       'Heilung',       'Spell · Buff', 3),
            ('R', 'frostnova',  'Frostnova',     'Spell · AoE · Nova · Cold', 4),
            ('1', 'earthquake', 'Erdbeben',      'Spell · AoE · Slam · Phys · Payoff', 5),
            ('2', 'spark',      'Funke',         'Spell · Projectile · Lightning · Bounce', 6),
            ('3', 'bone_spear', 'Knochenspeer',  'Spell · Projectile · Phys · Pierce', 7),
            ('4', 'ice_nova',   'Eis-Nova',      'Spell · AoE · Cold · Payoff', 8),
            ('5', 'comet',      'Komet',         'Spell · AoE · Slam · Cold', 9),
            ('X', 'ultimate',   'Ultimate',      'Klassen-Spezial (CD 60s)', 0),
            ('Y', 'time_freeze','Zeitstillstand','Friert alle Gegner 4s', 4),
            ('B', 'teleport',   'Teleport',      'Kurz-Blink (CD 8s)', 0),
        ]
        unlocked = self.player.unlocked_skills
        # Spezielle Skills (X/Y/B) sind immer freigeschaltet
        ALWAYS_UNLOCKED = {'melee', 'ultimate', 'time_freeze', 'teleport'}
        # Update #43: Click-Rects für Rebind sammeln
        self._skill_menu_slots = []
        # Reverse-Lookup: skill_id → bound key (pygame key code)
        bindings = getattr(self.player, 'skill_bindings', None) or {}
        sid_to_key = {sid_: k_ for k_, sid_ in bindings.items()}
        col_w = (w - 60) // 2
        cell_h = 78
        cy = y + 102  # nach Header-Divider
        col = 0
        from .ui import draw_skill_icon
        for k, sid, name, desc, icon_idx in all_skills:
            is_unlocked = (sid in unlocked) or (sid in ALWAYS_UNLOCKED)
            cell_x = x + 24 + col * (col_w + 12)
            # Slot-Hintergrund
            slot_bg = pygame.Surface((col_w, cell_h - 6), pygame.SRCALPHA)
            slot_col = (40, 30, 16) if is_unlocked else (30, 24, 16)
            slot_bg.fill((*slot_col, 240))
            self.screen.blit(slot_bg, (cell_x, cy))
            border = GOLD_BRIGHT if is_unlocked else (90, 70, 50)
            pygame.draw.rect(self.screen, border,
                              (cell_x, cy, col_w, cell_h - 6), 2)
            # Icon-Kasten
            ic_x = cell_x + 4
            ic_y = cy + 4
            pygame.draw.rect(self.screen, (20, 14, 8), (ic_x, ic_y, 60, 60))
            pygame.draw.rect(self.screen, border, (ic_x, ic_y, 60, 60), 1)
            if is_unlocked:
                draw_skill_icon(self.screen, ic_x, ic_y, 60, icon_idx, True)
            else:
                # Schloss-Symbol
                lock_x = ic_x + 30
                lock_y = ic_y + 30
                pygame.draw.rect(self.screen, (140, 140, 140),
                                  (lock_x - 8, lock_y - 4, 16, 14))
                pygame.draw.arc(self.screen, (140, 140, 140),
                                 (lock_x - 6, lock_y - 14, 12, 14),
                                 0, math.pi, 3)
                pygame.draw.circle(self.screen, (60, 40, 20),
                                    (lock_x, lock_y + 2), 2)
            # Text rechts — Update #43: zeigt USER-BINDING wenn vorhanden
            tx = cell_x + 72
            display_key = k
            if is_unlocked and sid in sid_to_key:
                kn = pygame.key.name(sid_to_key[sid]).upper()
                if kn:
                    display_key = kn
            ks = self.font_med.render(
                f'[{display_key}] {name}', True,
                GOLD_BRIGHT if is_unlocked else (140, 120, 90))
            self.screen.blit(ks, (tx, cy + 4))
            ds = self.font_small.render(
                desc, True, TEXT if is_unlocked else TEXT_DIM)
            self.screen.blit(ds, (tx, cy + 32))
            # Pending-Rebind-Highlight
            pending = (getattr(self, '_skill_rebind_pending', None) == sid)
            if pending:
                status = self.font_small.render(
                    'TASTE DRÜCKEN...', True, (255, 220, 80))
                self.screen.blit(status, (tx, cy + 50))
                # Pulsierender Rahmen
                pulse_a = int(140 + 100 * abs(math.sin(
                    pygame.time.get_ticks() * 0.006)))
                pulse_surf = pygame.Surface(
                    (col_w + 4, cell_h - 2), pygame.SRCALPHA)
                pygame.draw.rect(pulse_surf, (255, 220, 80, pulse_a),
                                 (0, 0, col_w + 4, cell_h - 2), 3)
                self.screen.blit(pulse_surf, (cell_x - 2, cy - 2))
            elif not is_unlocked:
                status = self.font_small.render(
                    'GESPERRT - Skill-Gem von Boss/Elite finden!',
                    True, (200, 100, 80))
                self.screen.blit(status, (tx, cy + 50))
            else:
                status_txt = 'ERLERNT · Klick zum Rebind'
                status = self.font_small.render(
                    status_txt, True, (140, 220, 140))
                self.screen.blit(status, (tx, cy + 50))
            # Click-Rect für Rebind (nur unlocked + rebindbare Skills)
            REBINDABLE = {'melee'}  # explizit nicht rebindbar
            if is_unlocked and sid not in REBINDABLE:
                rect = pygame.Rect(cell_x, cy, col_w, cell_h - 6)
                self._skill_menu_slots.append((rect, sid))
            # 2-Spalten-Layout
            col += 1
            if col >= 2:
                col = 0
                cy += cell_h
        # Footer
        footer = self.font_small.render(
            'G: Schliessen  ·  Klick auf Skill = Tasten-Rebind  ·  '
            'Esc bricht Rebind ab',
            True, TEXT_DIM)
        self.screen.blit(footer, footer.get_rect(
            center=(x + w // 2, y + h - 24)))

    def _draw_memorial_modal(self):
        """Memorial-Progression-Panel (Update #32, O-Taste).

        Velgrad-Lore: ein gravierter Mahnmal-Stein zeigt alle Taten
        des Spielers. Sichtbarer Fortschritt = Lore-Anker.
        """
        from . import aspects as _asp
        from . import quotes as _q
        from .constants import CLASSES, DUNGEONS
        pal = _asp.aspect_palette(self.player.cls)
        p = self.player
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        w, h = 880, 640
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament-Page
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            tt = py / max(1, h - 1)
            rr = int(42 + (28 - 42) * tt)
            gg = int(31 + (22 - 31) * tt)
            bb = int(20 + (16 - 20) * tt)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        _asp.draw_filigree_corners(
            self.screen, pygame.Rect(x, y, w, h), bronze, size=28)
        _asp.draw_aspect_watermark(
            self.screen, pygame.Rect(x, y, w, h),
            self.player.cls, alpha=16)

        # Header
        eyebrow = self.font_small.render(
            '— LIBER MEMORIAE TUI —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (x + w // 2 - eyebrow.get_width() // 2, y + 14))
        title_text = 'D E I N E   T A T E N'
        title = self.font_big.render(title_text, True, pal['halo'])
        title_sh = self.font_big.render(title_text, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (x + w // 2 - title.get_width() // 2 + 2,
                           y + 36 + 2))
        self.screen.blit(title,
                          (x + w // 2 - title.get_width() // 2, y + 36))
        _asp.draw_ornament_divider(
            self.screen, x + 24, y + 84, w - 48, bronze)

        # Klassen-Mastery-Rank-Anzeige groß oben
        MILESTONES = [0, 50, 150, 400, 900, 1800,
                       3500, 6000, 10000, 16000]
        xp = getattr(p, 'class_mastery_xp', 0)
        rank = sum(1 for m in MILESTONES if xp >= m)
        rank = max(1, rank)
        next_threshold = MILESTONES[min(rank, len(MILESTONES) - 1)]
        cur_threshold = MILESTONES[rank - 1]
        prog_frac = ((xp - cur_threshold) /
                       max(1, next_threshold - cur_threshold))
        if rank >= len(MILESTONES):
            prog_frac = 1.0
            next_threshold = xp
        # Rank-Box
        rank_y = y + 100
        rank_w = w - 80
        rank_x = x + 40
        rank_h = 70
        pygame.draw.rect(self.screen, (16, 12, 8),
                          (rank_x, rank_y, rank_w, rank_h))
        pygame.draw.rect(self.screen, pal['primary'],
                          (rank_x, rank_y, rank_w, rank_h), 2)
        ROMAN = ['', 'I', 'II', 'III', 'IV', 'V',
                  'VI', 'VII', 'VIII', 'IX', 'X']
        # Aspekt-Glyph links
        _asp.draw_glyph(self.screen, rank_x + 38,
                         rank_y + rank_h // 2, 56,
                         _asp.aspect_for_class(p.cls),
                         color=pal['bright'])
        # Rank-Text
        rank_text = f'MEISTERSCHAFT  {ROMAN[min(rank, 10)]}'
        rs = self.font_med.render(rank_text, True, pal['halo'])
        self.screen.blit(rs, (rank_x + 90, rank_y + 8))
        cname = CLASSES[p.cls]['name']
        sub_text = f'{cname}  ·  {pal["domain"]}'
        sub = self.font_small.render(sub_text, True, (200, 160, 100))
        self.screen.blit(sub, (rank_x + 90, rank_y + 32))
        # Progress-Bar darunter
        bar_y = rank_y + 52
        bar_w = rank_w - 102
        pygame.draw.rect(self.screen, (10, 6, 4),
                          (rank_x + 90, bar_y, bar_w, 10))
        fw = int(bar_w * prog_frac)
        if fw > 0:
            from .ui import _shade_color as _shc
            for hy in range(10):
                ty = hy / 9
                col = _shc(pal['primary'], 1.4 - ty * 0.6)
                pygame.draw.line(self.screen, col,
                                  (rank_x + 90, bar_y + hy),
                                  (rank_x + 90 + fw, bar_y + hy))
        pygame.draw.rect(self.screen, pal['deep'],
                          (rank_x + 90, bar_y, bar_w, 10), 1)
        prog_text = (f'{xp} / {next_threshold} Klassen-XP'
                      if rank < len(MILESTONES)
                      else 'MAX MEISTERSCHAFT')
        ps = self.font_small.render(prog_text, True, (180, 160, 110))
        self.screen.blit(ps, (rank_x + 90 + bar_w
                                 - ps.get_width(), bar_y - 14))

        # Stats-Grid (2 columns)
        stats_y = rank_y + rank_h + 16
        col_w = (w - 80) // 2
        stats_left = [
            ('Total-Kills',     getattr(p, 'prog_kills_total', 0)),
            ('Bosse erschlagen', getattr(p, 'prog_kills_boss', 0)),
            ('Mini-Bosse',       getattr(p, 'prog_kills_mini', 0)),
            ('Elites',          getattr(p, 'prog_kills_elite', 0)),
            ('Crits gelandet',   getattr(p, 'prog_crits_dealt', 0)),
        ]
        n_dungeons = len(getattr(p, 'prog_dungeons_cleared', set()))
        n_lore = len(getattr(p, 'prog_lore_read', set()))
        n_best = len(getattr(p, 'prog_bestiary_seen', set()))
        stats_right = [
            ('Dungeons geräumt',  f'{n_dungeons} / {len(DUNGEONS)}'),
            ('Lore-Tafeln',       f'{n_lore} entdeckt'),
            ('Bestiarium',        f'{n_best} / 30 Monster'),
            ('Altäre genutzt',     getattr(p, 'prog_altars_used', 0)),
            ('Runen-Kreise',       getattr(p, 'prog_runes_used', 0)),
        ]
        for col, stats in [(0, stats_left), (1, stats_right)]:
            sx = x + 40 + col * (col_w + 20)
            # Spalten-Header
            head_text = ['ERINNERTE TATEN', 'WELT-ENTDECKUNG'][col]
            hs = self.font_small.render(head_text, True, pal['bright'])
            self.screen.blit(hs, (sx, stats_y))
            pygame.draw.line(self.screen, (90, 63, 36),
                              (sx, stats_y + 18),
                              (sx + col_w, stats_y + 18), 1)
            sy = stats_y + 24
            for lbl, val in stats:
                lbl_s = self.font_small.render(lbl, True, (200, 170, 130))
                val_s = self.font_small.render(
                    str(val), True, (243, 213, 114))
                self.screen.blit(lbl_s, (sx, sy))
                self.screen.blit(val_s,
                                  (sx + col_w - val_s.get_width(), sy))
                sy += 20
            # Mahnmal-Marken (links) oder Time (rechts)
            sy += 8
            if col == 0:
                # Mahnmal-Marken-Stack
                marken = getattr(p, 'mahnmal_marken', {})
                total_marken = sum(marken.values())
                lbl_s = self.font_small.render(
                    'Mahnmal-Marken', True, (200, 170, 130))
                val_s = self.font_small.render(
                    f'{total_marken} total', True, (243, 213, 114))
                self.screen.blit(lbl_s, (sx, sy))
                self.screen.blit(val_s,
                                  (sx + col_w - val_s.get_width(), sy))
                sy += 18
                # 7 Marken-Slots zeigen
                ASPEKT_COL = {
                    1: (220, 160, 80),   2: (180, 200, 220),
                    3: (200, 180, 240),  4: (255, 140, 60),
                    5: (140, 220, 140),  6: (200, 80, 160),
                    7: (255, 240, 100),
                }
                ROMAN_S = {1: 'I', 2: 'II', 3: 'III', 4: 'IV',
                            5: 'V', 6: 'VI', 7: 'VII'}
                pill_w = (col_w - 6) // 7
                for mk in range(1, 8):
                    px_ = sx + (mk - 1) * (pill_w + 1)
                    col_m = ASPEKT_COL[mk]
                    n = marken.get(mk, 0)
                    pygame.draw.rect(self.screen, (16, 12, 8),
                                      (px_, sy, pill_w, 18))
                    pygame.draw.rect(self.screen, col_m,
                                      (px_, sy, pill_w, 18), 1)
                    rs = self.font_small.render(ROMAN_S[mk], True, col_m)
                    self.screen.blit(rs, (px_ + 2, sy + 2))
                    if n > 0:
                        ns = self.font_small.render(
                            f'{n}', True, (255, 240, 200))
                        self.screen.blit(ns,
                            (px_ + pill_w - ns.get_width() - 2,
                             sy + 2))
            else:
                # Spielzeit + Gold
                play_t = int(getattr(p, 'prog_play_time_s', 0))
                m = play_t // 60
                s = play_t % 60
                for lbl, val in [
                    ('Spielzeit', f'{m}m {s}s'),
                    ('Gold-Schatz', getattr(p, 'gold', 0)),
                    ('Splitter',   getattr(p, 'shards', 0)),
                ]:
                    lbl_s = self.font_small.render(
                        lbl, True, (200, 170, 130))
                    val_s = self.font_small.render(
                        str(val), True, (243, 213, 114))
                    self.screen.blit(lbl_s, (sx, sy))
                    self.screen.blit(val_s,
                                      (sx + col_w - val_s.get_width(), sy))
                    sy += 20

        # Footer Lore-Quote + Hinweis — Update #104 Fix:
        # Quote 4 px höher, Footer 4 px tiefer → keine Überlappung.
        quote = '„Was du erinnerst, wirst du sein. Was du tust, sind die Steine deines Mahnmals."'
        qsurf = self.font_small.render(quote, True, (200, 160, 100))
        self.screen.blit(qsurf,
                          (x + w // 2 - qsurf.get_width() // 2,
                           y + h - 44))
        footer = self.font_small.render(
            'O: Schließen', True, (140, 110, 70))
        self.screen.blit(footer, footer.get_rect(
            center=(x + w // 2, y + h - 18)))

    def _draw_help_modal(self):
        """Tastenbelegung + Tipps — Velgrad-Tome-Style (Update #30)."""
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        w, h = 720, 620
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament-Hintergrund
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            t = py / max(1, h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        # Doppel-Rahmen
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        _asp.draw_filigree_corners(
            self.screen, pygame.Rect(x, y, w, h), bronze, size=26)
        _asp.draw_aspect_watermark(
            self.screen, pygame.Rect(x, y, w, h),
            self.player.cls, alpha=18)
        # Header
        eyebrow = self.font_small.render(
            '— DAS HOHLE WORT LEHRT —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (x + w // 2 - eyebrow.get_width() // 2,
                           y + 14))
        title_text = 'S T E U E R U N G'
        title = self.font_big.render(title_text, True, pal['halo'])
        title_sh = self.font_big.render(title_text, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (x + w // 2 - title.get_width() // 2 + 2,
                           y + 32 + 2))
        self.screen.blit(title,
                          (x + w // 2 - title.get_width() // 2, y + 32))
        _asp.draw_ornament_divider(
            self.screen, x + 24, y + 80, w - 48, bronze)

        sections = [
            ('BEWEGUNG & KAMPF', [
                ('Linksklick', 'Bewegen / Gegner angreifen'),
                ('Rechtsklick', 'Item im Inventar wegwerfen'),
                ('Leertaste', 'Ausweichrolle (kurze Unverwundbarkeit)'),
                ('Q W E R', 'Magie-Skills (sobald erlernt)'),
                ('X', 'Klassen-Ultimate (CD 60s)'),
                ('Y', 'Zeitstillstand (CD 35s)'),
                ('B', 'Teleport / Blink (CD 8s)'),
            ]),
            ('MENUES', [
                ('I', 'Inventar / Ausruestung'),
                ('K', 'Talentbaum + Auren'),
                ('G', 'Skill-Grimoire (alle Skills)'),
                ('C', 'Werkstatt / Schmiede'),
                ('J', 'Quest-Log (Velgrad-Quests + Dungeon)'),
                ('N', 'Codex (Bestiarium + Lore-Tafeln)'),
                ('O', 'Memorial (deine Taten + Klassen-Meisterschaft)'),
                ('H', 'Diese Hilfe'),
                ('ESC', 'Pause-Menue / Modal schliessen'),
            ]),
            ('STADT & DUNGEONS', [
                ('F', 'Interagieren (NPC, Portal, Lore-Tafel)'),
                ('T', 'Schwierigkeit am Portal wechseln'),
                ('L', 'Loot-Filter umschalten'),
                ('Z', 'Inventar sortieren'),
                ('F11', 'Vollbild umschalten'),
                ('Shift', 'Beim Hover: Item-Vergleich'),
            ]),
        ]
        cy = y + 100
        for section_title, items in sections:
            ts = self.font_med.render(section_title, True, pal['halo'])
            self.screen.blit(ts, (x + 30, cy))
            cy += 24
            # Mini-Divider unter Section
            pygame.draw.line(self.screen, (90, 63, 36),
                              (x + 30, cy), (x + w - 30, cy), 1)
            cy += 4
            for key, desc in items:
                ks = self.font_small.render(key, True, (227, 180, 64))
                self.screen.blit(ks, (x + 50, cy))
                ds = self.font_small.render(desc, True, (220, 200, 170))
                self.screen.blit(ds, (x + 200, cy))
                cy += 17
            cy += 10
        # Footer-Quote + Hint
        quote = self.font_small.render(
            '„Was du nicht erinnerst, wird vergessen."',
            True, (200, 160, 100))
        self.screen.blit(quote,
                          (x + w // 2 - quote.get_width() // 2,
                           y + h - 44))
        footer = self.font_small.render(
            'H: Schliessen', True, (140, 110, 70))
        self.screen.blit(footer, footer.get_rect(
            center=(x + w // 2, y + h - 18)))

    # Setting-Keys in genau der Reihenfolge, in der sie im Modal erscheinen.
    # Update #178: Settings-Modal in Kategorien gruppiert + 2-Spalten-
    # Layout.  Reihenfolge in der Liste = Render-Reihenfolge in der Spalte.
    # `None` = Trennlinie/Spacer zwischen Sub-Gruppen ohne eigenen Header.
    _SETTING_CATEGORIES = [
        # (Spalten-Index, Kategorie-Titel, [setting-keys])
        (0, 'AUDIO', ['music_vol', 'sfx_vol']),
        (0, 'ANZEIGE', ['fullscreen', 'vsync', 'frame_cap', 'render_scale']),
        (0, 'GRAFIK', ['screen_shake', 'particle_density', 'rim_light',
                        'bloom', 'heat_distortion', 'crt_filter']),
        (1, 'KAMERA', ['camera_lookahead', 'camera_cursor_lean',
                        'camera_combat_zoom']),
        (1, 'BARRIEREFREIHEIT', ['photosensitive', 'high_contrast_aoe',
                                   'tactical_reduce', 'colorblind_ailments',
                                   'minimap_rotate']),
        (1, 'SYSTEM', ['ai_sprites', 'multi_threading']),
    ]
    _SETTING_KEYS = [k for _, _, ks in _SETTING_CATEGORIES for k in ks]
    _FRAME_CAP_OPTIONS = [30, 60, 120, 144, 240, 360, 0]  # 0 = unlimited
    # P-04 (Update #97): Render-Scale-Optionen, cyclable im Settings-Modal.
    _RENDER_SCALE_OPTIONS = [0.5, 0.7, 0.85, 1.0]
    _BLOOM_OPTIONS = ['off', 'low', 'high']
    _CRT_OPTIONS = ['off', 'scanlines', 'dither']

    def _settings_layout(self):
        # Update #178: 2-Spalten-Layout. Pro Spalte: Kategorie-Headers
        # (Höhe 28) + Setting-Rows (Höhe 32 mit 4 px Gap = 36).
        w = 980
        col_w = (w - 90) // 2  # 30 padding + 30 gutter + 30 padding
        row_h = 32
        row_gap = 4
        cat_h = 30
        cat_top_gap = 14  # Abstand über jedem Kategorie-Header
        # Pro-Spalte-Höhe berechnen
        col_heights = [0, 0]
        for ci, _title, keys in self._SETTING_CATEGORIES:
            col_heights[ci] += cat_top_gap + cat_h
            col_heights[ci] += len(keys) * (row_h + row_gap)
        content_h = max(col_heights)
        header_h = 130  # Update #179: mehr Luft fuer Title + Divider
        h = header_h + content_h + 70  # Header + content + 70 Footer
        mx = SCREEN_W // 2 - w // 2
        my = SCREEN_H // 2 - h // 2
        rect = pygame.Rect(mx, my, w, h)
        rows = {}
        cats = []  # [(title, rect, col_idx)]
        # Spalten-X-Positions
        col_x = [mx + 30, mx + 30 + col_w + 30]
        # Per-Spalte-Y-Cursor (startet direkt unter dem Header)
        cur_y = [my + header_h, my + header_h]
        for ci, title, keys in self._SETTING_CATEGORIES:
            cur_y[ci] += cat_top_gap
            cats.append((title, pygame.Rect(col_x[ci], cur_y[ci], col_w, cat_h), ci))
            cur_y[ci] += cat_h
            for k in keys:
                rows[k] = pygame.Rect(col_x[ci], cur_y[ci], col_w, row_h)
                cur_y[ci] += row_h + row_gap
        rows['back'] = pygame.Rect(mx + (w - 280) // 2,
                                     my + h - 56, 280, 42)
        return rect, rows, cats

    # Update #178: Slider-Layout-Konstanten (Settings-Modal).  Label
    # nimmt linke Hälfte der Row, Slider+% die rechte.
    _SLIDER_LABEL_W = 160
    _SLIDER_PCT_W = 50

    def _apply_slider_value(self, key, row_rect, sx):
        """Update #99: Slider-Wert-Setzen aus Maus-X.  Wird sowohl von
        Single-Click als auch Drag-Tick aufgerufen."""
        slider_x = row_rect.x + self._SLIDER_LABEL_W
        slider_w = row_rect.w - self._SLIDER_LABEL_W - self._SLIDER_PCT_W - 12
        rel = (sx - slider_x) / max(1, slider_w)
        rel = max(0.0, min(1.0, rel))
        self.settings[key] = rel
        if key == 'music_vol':
            snd.set_music_volume(rel)
        elif key == 'sfx_vol':
            snd.set_sfx_volume(rel)

    def _handle_settings_drag(self, sx, sy):
        """Update #99: kontinuierliches Drag während LMB-Hold im Settings-
        Modal. Triggert nur für Slider-Reihen unter dem Cursor."""
        rect, rows, _cats = self._settings_layout()
        if not rect.collidepoint(sx, sy):
            return
        for key in ('music_vol', 'sfx_vol'):
            r = rows.get(key)
            if r is not None and r.collidepoint(sx, sy):
                self._apply_slider_value(key, r, sx)
                # Update #151: throttled persist (max 1×/0.5s)
                import time as _t
                now = _t.time()
                last = getattr(self, '_settings_save_t', 0.0)
                if now - last > 0.5:
                    self._settings_save_t = now
                    try:
                        save_mod.save_settings(self)
                    except Exception:
                        pass
                return

    # Update #178: Toggle-Keys mit ihren Defaults (für saubere Cycle-
    # Logik ohne mehrfaches `not self.settings.get(...)`).
    _TOGGLE_DEFAULTS = {
        'screen_shake': True,
        'photosensitive': False,
        'rim_light': True,
        'high_contrast_aoe': False,
        'tactical_reduce': False,
        'minimap_rotate': False,
        'colorblind_ailments': False,
        'camera_lookahead': False,
        'camera_cursor_lean': False,
        'camera_combat_zoom': True,
        'heat_distortion': True,
        'multi_threading': True,
        # Update #201 (User-Bug-Fix): vsync war NICHT in _TOGGLE_DEFAULTS.
        # Folge: der Klick auf "VSync (Restart noetig)" tat gar nichts —
        # weder den Wert flippen noch den Toast. Default True.
        'vsync': True,
    }

    def _cycle_value(self, cur, options):
        """Helper: return next element in options after `cur` (wraps).
        Falls cur nicht in options ist, returnt options[0]."""
        try:
            i = options.index(cur)
        except ValueError:
            return options[0]
        return options[(i + 1) % len(options)]

    def _handle_settings_click(self, sx, sy):
        rect, rows, _cats = self._settings_layout()
        if not rect.collidepoint(sx, sy):
            return
        for key, r in rows.items():
            if r.collidepoint(sx, sy):
                changed = False
                if key == 'back':
                    self.modal = 'pause'
                    return
                if key == 'fullscreen':
                    self._toggle_fullscreen()
                    return  # _toggle_fullscreen persistiert selbst
                # Simple toggles (Update #178).
                if key in self._TOGGLE_DEFAULTS:
                    default = self._TOGGLE_DEFAULTS[key]
                    self.settings[key] = not self.settings.get(key, default)
                    changed = True
                    # Update #201 (User-Bug-Fix): VSync live anwenden via
                    # display.set_mode mit neuem vsync-Flag. SDL erlaubt
                    # vsync nur als set_mode-Argument; ein Toggle zur
                    # Laufzeit erfordert recreate.  Selbe GL-Re-Install-
                    # Strategie wie _toggle_fullscreen.
                    if key == 'vsync':
                        try:
                            self._apply_vsync_setting()
                        except Exception:
                            self.toast(
                                'VSync-Switch fehlgeschlagen — '
                                'Restart erforderlich.', (255, 180, 100))
                        else:
                            on = self.settings['vsync']
                            self.toast(
                                f'VSync: {"AN" if on else "AUS"}',
                                (200, 220, 255))
                elif key == 'ai_sprites':
                    new_val = not self.settings.get('ai_sprites', False)
                    self.settings['ai_sprites'] = new_val
                    try:
                        from . import sprites as _sp_mod
                        _sp_mod.set_ai_sprites_enabled(new_val)
                        _sp_mod.reload_sprite_cache()
                    except Exception:
                        pass
                    changed = True
                elif key == 'frame_cap':
                    cur = int(self.settings.get('frame_cap', 360))
                    self.settings['frame_cap'] = self._cycle_value(
                        cur, self._FRAME_CAP_OPTIONS)
                    changed = True
                elif key == 'render_scale':
                    cur = float(self.settings.get('render_scale', 1.0))
                    # Floats brauchen Toleranz fürs Cycle — auf nächsten
                    # Preset snappen und dann weiterschalten.
                    opts = self._RENDER_SCALE_OPTIONS
                    idx = min(range(len(opts)),
                               key=lambda i: abs(opts[i] - cur))
                    self.settings['render_scale'] = opts[(idx + 1) % len(opts)]
                    changed = True
                elif key == 'bloom':
                    self.settings['bloom'] = self._cycle_value(
                        self.settings.get('bloom', 'low'),
                        self._BLOOM_OPTIONS)
                    changed = True
                elif key == 'crt_filter':
                    self.settings['crt_filter'] = self._cycle_value(
                        self.settings.get('crt_filter', 'off'),
                        self._CRT_OPTIONS)
                    changed = True
                elif key == 'particle_density':
                    options = [v for _, v in fx.DENSITY_PRESETS]
                    cur = self.settings['particle_density']
                    idx = min(range(len(options)),
                               key=lambda i: abs(options[i] - cur))
                    self.settings['particle_density'] = options[(idx + 1) % len(options)]
                    changed = True
                elif key in ('music_vol', 'sfx_vol'):
                    self._apply_slider_value(key, r, sx)
                    changed = True
                if changed:
                    try:
                        save_mod.save_settings(self)
                    except Exception:
                        pass
                return

    # Update #178: Setting-Metadaten — Label + Kind (toggle/cycle/slider).
    # Werte werden zur Render-Zeit aus self.settings gelesen.
    _SETTING_META = {
        'music_vol':         ('Musik',                   'slider'),
        'sfx_vol':           ('SFX',                     'slider'),
        'fullscreen':        ('Vollbild',                'toggle'),
        'vsync':             ('VSync',                   'toggle'),
        'frame_cap':         ('Frame-Cap',               'cycle'),
        'render_scale':      ('Render-Skalierung',       'cycle'),
        'screen_shake':      ('Bildschirm-Wackeln',      'toggle'),
        'particle_density':  ('Ambient-Partikel',        'cycle'),
        'rim_light':         ('Spieler-Aura',            'toggle'),
        'bloom':             ('Bloom',                   'cycle'),
        'heat_distortion':   ('Hitze-Verzerrung',        'toggle'),
        'crt_filter':        ('CRT-Filter',              'cycle'),
        'camera_lookahead':  ('Lookahead',               'toggle'),
        'camera_cursor_lean':('Cursor-Lean',             'toggle'),
        'camera_combat_zoom':('Combat-Zoom',             'toggle'),
        'photosensitive':    ('Photosensitiv',           'toggle'),
        'high_contrast_aoe': ('AoE: Hoher Kontrast',     'toggle'),
        'tactical_reduce':   ('Eigene VFX gedaempft',    'toggle'),
        'colorblind_ailments':('Farbenblind-Ailments',   'toggle'),
        'minimap_rotate':    ('Minimap rotiert',         'toggle'),
        'ai_sprites':        ('AI-Sprites',              'toggle'),
        'multi_threading':   ('Multi-Threading',         'toggle'),
    }

    _CYCLE_LABELS = {
        'bloom':      {'off': 'Aus', 'low': 'Niedrig', 'high': 'Hoch'},
        'crt_filter': {'off': 'Aus', 'scanlines': 'Scanlines', 'dither': 'Dither'},
    }

    def _setting_value(self, key):
        """Returnt aktuellen Wert eines Settings.  Fullscreen ist Toplevel-
        Attribut; alle anderen leben in self.settings."""
        if key == 'fullscreen':
            return bool(self.fullscreen)
        return self.settings.get(key, self._TOGGLE_DEFAULTS.get(key))

    def _setting_display_value(self, key):
        """Returnt das Anzeige-Label für einen Setting-Wert (für 'cycle')."""
        if key == 'frame_cap':
            return self._frame_cap_label()
        if key == 'particle_density':
            return self._density_label()
        if key == 'render_scale':
            return f'{int(float(self.settings.get("render_scale", 1.0)) * 100)} %'
        if key in self._CYCLE_LABELS:
            v = self.settings.get(key, 'off')
            return self._CYCLE_LABELS[key].get(v, str(v))
        return str(self.settings.get(key, ''))

    def _draw_settings_modal(self):
        """Velgrad-Tome-Style Settings — 2-Spalten + Kategorien (Update #178)."""
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        rect, rows, cats = self._settings_layout()
        # Dunkler Overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        self.screen.blit(overlay, (0, 0))
        # Pergament-Page mit vertikalem Gradient (Tome-Look)
        page = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        for py in range(rect.h):
            t = py / max(1, rect.h - 1)
            rr = int(42 + (26 - 42) * t)
            gg = int(31 + (20 - 31) * t)
            bb = int(20 + (14 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (rect.w, py))
        self.screen.blit(page, rect.topleft)
        bronze = (154, 118, 66)
        bronze_dim = (96, 72, 42)
        pygame.draw.rect(self.screen, bronze, rect, 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (rect.x + 4, rect.y + 4,
                           rect.w - 8, rect.h - 8), 1)
        _asp.draw_filigree_corners(self.screen, rect, bronze, size=24)
        _asp.draw_aspect_watermark(self.screen, rect,
                                    self.player.cls, alpha=16)
        # Header
        eyebrow = self.font_small.render(
            '— DIE TUEREN DES ATEMS —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (rect.centerx - eyebrow.get_width() // 2,
                           rect.y + 14))
        # Update #179: Settings-Title bekommt eigenen kleineren Font
        # damit er nicht das Modal sprengt + nicht ueber den Divider /
        # Kategorie-Header laeuft.  Nutzt den gleichen Display-Font-Stack
        # wie font_big (Cinzel/Trajan/Georgia) damit das Tome-Feel bleibt.
        if not hasattr(self, '_settings_title_font'):
            try:
                df = pygame.font.match_font(
                    'cinzel,trajanpro,georgia,times', bold=True)
                if df:
                    self._settings_title_font = pygame.font.Font(df, 42)
                else:
                    self._settings_title_font = pygame.font.SysFont(
                        'georgia,times', 42, bold=True)
            except Exception:
                self._settings_title_font = pygame.font.SysFont(
                    'georgia,times', 42, bold=True)
        tf = self._settings_title_font
        max_title_w = rect.w - 120
        title_text = 'E I N S T E L L U N G E N'
        title = tf.render(title_text, True, pal['halo'])
        if title.get_width() > max_title_w:
            title_text = 'EINSTELLUNGEN'
            title = tf.render(title_text, True, pal['halo'])
        title_sh = tf.render(title_text, True, (10, 6, 4))
        title_y = rect.y + 42
        self.screen.blit(title_sh,
                          (rect.centerx - title.get_width() // 2 + 2,
                           title_y + 2))
        self.screen.blit(title,
                          (rect.centerx - title.get_width() // 2,
                           title_y))
        # Divider sitzt unter dem Title — title_y + title_h + 8
        divider_y = title_y + title.get_height() + 6
        _asp.draw_ornament_divider(
            self.screen, rect.x + 20, divider_y,
            rect.w - 40, bronze)

        # Vertikaler Spalten-Divider in der Mitte (unter Header-Bereich)
        col_div_x = rect.centerx
        for y in range(rect.y + 130, rect.y + rect.h - 70, 4):
            self.screen.set_at((col_div_x, y), bronze_dim)

        # Kategorie-Header
        for title_str, crect, _ci in cats:
            # Subtiler Hintergrund-Streifen
            stripe = pygame.Surface((crect.w, crect.h), pygame.SRCALPHA)
            stripe.fill((58, 42, 22, 180))
            self.screen.blit(stripe, crect.topleft)
            # Bronze-Underline
            pygame.draw.line(
                self.screen, bronze,
                (crect.x, crect.bottom - 1),
                (crect.right, crect.bottom - 1), 1)
            # Linker Ornament-Diamant
            cy = crect.centery
            pygame.draw.polygon(
                self.screen, bronze,
                [(crect.x + 8, cy), (crect.x + 14, cy - 4),
                 (crect.x + 20, cy), (crect.x + 14, cy + 4)])
            ts = self.font_small.render(title_str, True, GOLD_BRIGHT)
            self.screen.blit(ts, (crect.x + 30,
                                    crect.y + (crect.h - ts.get_height()) // 2))

        # Rows
        for key, r in rows.items():
            if key == 'back':
                continue
            meta = self._SETTING_META.get(key)
            if meta is None:
                continue
            label, kind = meta
            # Slot-Hintergrund (subtil)
            bgb = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            bgb.fill((26, 20, 12, 200))
            self.screen.blit(bgb, r.topleft)
            pygame.draw.rect(self.screen, (74, 56, 38), r, 1)
            ls = self.font_small.render(label, True, TEXT)
            self.screen.blit(ls, (r.x + 14, r.y + (r.h - ls.get_height()) // 2))
            if kind == 'slider':
                val = float(self.settings.get(key, 0.0))
                slider_x = r.x + self._SLIDER_LABEL_W
                slider_y = r.centery - 3
                slider_w = r.w - self._SLIDER_LABEL_W - self._SLIDER_PCT_W - 12
                pygame.draw.rect(self.screen, (60, 50, 36),
                                  (slider_x, slider_y, slider_w, 6))
                fill_w = int(slider_w * val)
                pygame.draw.rect(self.screen, GOLD,
                                  (slider_x, slider_y, fill_w, 6))
                knob_x = slider_x + fill_w
                pygame.draw.circle(self.screen, GOLD_BRIGHT,
                                    (knob_x, slider_y + 3), 7)
                pygame.draw.circle(self.screen, (60, 42, 20),
                                    (knob_x, slider_y + 3), 7, 1)
                pct = self.font_small.render(f'{int(val * 100)}%', True, GOLD_BRIGHT)
                self.screen.blit(pct, (r.right - pct.get_width() - 10,
                                        r.y + (r.h - pct.get_height()) // 2))
            elif kind == 'toggle':
                val = bool(self._setting_value(key))
                self._draw_toggle_pill(r, val)
            elif kind == 'cycle':
                val_label = self._setting_display_value(key)
                arrow_l = self.font_small.render('<', True, bronze)
                arrow_r = self.font_small.render('>', True, bronze)
                vs = self.font_small.render(val_label, True, GOLD_BRIGHT)
                # Rechtsbuendig mit Pfeilen rechts/links
                vx = r.right - vs.get_width() - 22
                vy = r.y + (r.h - vs.get_height()) // 2
                self.screen.blit(arrow_l,
                                  (vx - arrow_l.get_width() - 6, vy))
                self.screen.blit(vs, (vx, vy))
                self.screen.blit(arrow_r, (vx + vs.get_width() + 6, vy))

        # Back-Button (zentriert unten)
        br = rows['back']
        bgb = pygame.Surface((br.w, br.h), pygame.SRCALPHA)
        bgb.fill((40, 30, 14, 240))
        self.screen.blit(bgb, br.topleft)
        pygame.draw.rect(self.screen, GOLD, br, 2)
        # Kleine Filigree an Back-Button-Ecken
        for cx, cy in ((br.x, br.y), (br.right - 1, br.y),
                        (br.x, br.bottom - 1), (br.right - 1, br.bottom - 1)):
            pygame.draw.circle(self.screen, bronze, (cx, cy), 2)
        ls = self.font_med.render('ZURUECK (ESC)', True, GOLD_BRIGHT)
        self.screen.blit(ls, ls.get_rect(center=br.center))

    def _draw_toggle_pill(self, r, val):
        """Update #178: Toggle als Pill-Switch (rechtsbuendig in Row).
        Ersetzt den schlichten Text-AN/AUS — klarer + thematischer."""
        pill_w, pill_h = 56, 22
        px = r.right - pill_w - 12
        py = r.y + (r.h - pill_h) // 2
        # Track
        track_col = (60, 100, 56) if val else (70, 36, 28)
        border_col = (140, 220, 140) if val else (170, 88, 70)
        track = pygame.Rect(px, py, pill_w, pill_h)
        pygame.draw.rect(self.screen, track_col, track, border_radius=pill_h // 2)
        pygame.draw.rect(self.screen, border_col, track, 1,
                          border_radius=pill_h // 2)
        # Knob
        knob_r = pill_h // 2 - 2
        knob_x = px + pill_w - knob_r - 3 if val else px + knob_r + 3
        knob_y = py + pill_h // 2
        knob_col = (230, 220, 170) if val else (160, 140, 110)
        pygame.draw.circle(self.screen, knob_col, (knob_x, knob_y), knob_r)
        pygame.draw.circle(self.screen, (40, 28, 14),
                            (knob_x, knob_y), knob_r, 1)

    def _draw_decals(self):
        """Rendert AoE-Telegraph-Decals (PLAN C-05/C-07).

        Wind-Up-Phase: pulsierender Outline-Ring + Füll-Phase nach innen
        wachsend, optional Mid-Air-Indicator (Schatten + Stern-Riss).
        Active-Phase: solid Ring mit Lifetime-Fade.
        Briefing C.3.2: zweite Spur, die NIE gecullt wird (TELEGRAPH-Layer).
        """
        if not self.decals:
            return
        # Photosensitive-Setting: weniger Flash (C-11-Vorbereitung)
        flash_mult = 0.5 if self.settings.get('photosensitive', False) else 1.0
        # High-Contrast-Mode (Vorbereitung für C-12): Solid-Fill statt Outline.
        high_contrast = bool(self.settings.get('high_contrast_aoe', False))
        for d in self.decals:
            sx, sy = self.w2s(d.pos)
            r = int(d.radius)
            base_color = fx.DECAL_COLORS.get(d.kind, (255, 255, 255))
            if not d.activated:
                # ---- Wind-Up: pulsierender Outline + Inner-Fill wächst ----
                t = d.age / max(0.001, d.windup)  # 0..1
                # Pulse-Frequenz steigt mit Annäherung an Activate.
                puls_hz = 4 + 8 * t
                puls = abs(math.sin(d.age * puls_hz * math.pi))
                alpha_outline = int((140 + 100 * puls) * flash_mult)
                surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                if high_contrast:
                    # Solid-Fill, alpha steigt mit t
                    pygame.draw.circle(
                        surf, (*base_color, int(80 + 80 * t)),
                        (r + 4, r + 4), r)
                else:
                    # Outline-Ring
                    pygame.draw.circle(surf, (*base_color, alpha_outline),
                                       (r + 4, r + 4), r, 5)
                    # Innerer Füllring wächst von 0 → r
                    inner = int(r * t)
                    if inner > 4:
                        pygame.draw.circle(
                            surf, (*base_color, int(100 * flash_mult)),
                            (r + 4, r + 4), inner, 3)
                self.screen.blit(surf, (sx - r - 4, sy - r - 4))

                # ---- Mid-Air-Indicator (C-07) ----
                if d.aerial:
                    # Schatten am Boden (elliptisch, wird mit t größer)
                    shadow_w = int(r * (0.5 + 0.5 * t))
                    shadow_h = max(6, int(shadow_w * 0.4))
                    shadow = pygame.Surface(
                        (shadow_w * 2, shadow_h * 2), pygame.SRCALPHA)
                    pygame.draw.ellipse(
                        shadow, (0, 0, 0, int(160 * flash_mult)),
                        (0, 0, shadow_w * 2, shadow_h * 2))
                    self.screen.blit(shadow, (sx - shadow_w, sy - shadow_h))
                    # Wachsender Stern-Riss (4-Strahl) als Telegraph in der Luft
                    crack_len = int(r * (0.3 + 0.8 * t))
                    crack_alpha = int((200 + 50 * puls) * flash_mult)
                    crack_col = (*base_color, crack_alpha)
                    crack_surf = pygame.Surface(
                        (crack_len * 2 + 4, crack_len * 2 + 4),
                        pygame.SRCALPHA)
                    cx, cy = crack_len + 2, crack_len + 2
                    for ang in (0.0, math.pi / 2, math.pi, 3 * math.pi / 2):
                        ex = cx + int(math.cos(ang) * crack_len)
                        ey = cy + int(math.sin(ang) * crack_len)
                        pygame.draw.line(crack_surf, crack_col,
                                         (cx, cy), (ex, ey), 3)
                    # Diagonal-Streben (halber Länge), gibt Stern-Look
                    for ang in (math.pi / 4, 3 * math.pi / 4,
                                5 * math.pi / 4, 7 * math.pi / 4):
                        ex = cx + int(math.cos(ang) * crack_len * 0.5)
                        ey = cy + int(math.sin(ang) * crack_len * 0.5)
                        pygame.draw.line(crack_surf, crack_col,
                                         (cx, cy), (ex, ey), 2)
                    self.screen.blit(crack_surf,
                                     (sx - crack_len - 2,
                                      sy - crack_len - 2))
            else:
                # ---- Active: solider Ring, fadet über Lifetime aus ----
                if d.lifetime <= 0.0:
                    continue
                t_active = (d.age - d.windup) / max(0.001, d.lifetime)
                t_active = max(0.0, min(1.0, t_active))
                alpha = int(180 * (1.0 - t_active) * flash_mult)
                surf = pygame.Surface((r * 2 + 8, r * 2 + 8), pygame.SRCALPHA)
                pygame.draw.circle(surf, (*base_color, alpha),
                                   (r + 4, r + 4), r, 4)
                pygame.draw.circle(surf,
                                   (*base_color, max(0, alpha // 3)),
                                   (r + 4, r + 4), max(2, r - 6))
                self.screen.blit(surf, (sx - r - 4, sy - r - 4))

    def _density_label(self):
        v = self.settings['particle_density']
        # Snap an nächstgelegenen DENSITY_PRESETS-Eintrag.
        label, _ = min(fx.DENSITY_PRESETS, key=lambda lv: abs(lv[1] - v))
        return label

    def _frame_cap_label(self):
        v = int(self.settings.get('frame_cap', 360))
        return 'Unbegrenzt' if v == 0 else f'{v} FPS'

    def _pause_buttons(self):
        # Update #180: Pause-Layout-Refit — Title bekommt eigene Zone oben,
        # darunter zwei klar getrennte Spalten (Buttons links, Build rechts),
        # Currency-Strip unten.  Höher (520) damit nichts überlappt.
        w, h = 760, 520
        mx = SCREEN_W // 2 - w // 2
        my = SCREEN_H // 2 - h // 2
        col_w = 300
        # Title-Zone: my..my+118 (Eyebrow + Title + Divider)
        # Content-Zone: my+130..my+h-80 (Buttons / Build-Snapshot)
        btn_top = my + 130
        return {
            'rect': pygame.Rect(mx, my, w, h),
            'resume':    pygame.Rect(mx + 30, btn_top + 0,   col_w, 44),
            'settings':  pygame.Rect(mx + 30, btn_top + 54,  col_w, 44),
            'town':      pygame.Rect(mx + 30, btn_top + 108, col_w, 44),
            'title':     pygame.Rect(mx + 30, btn_top + 162, col_w, 44),
            'quit':      pygame.Rect(mx + 30, btn_top + 216, col_w, 44),
            # Build-Snapshot rechte Spalte (eigene Render-Region)
            'snapshot':  pygame.Rect(mx + col_w + 60, btn_top,
                                       w - col_w - 90, h - 130 - 80),
        }

    def _handle_pause_click(self, sx, sy):
        b = self._pause_buttons()
        if not b['rect'].collidepoint(sx, sy):
            return
        if b['resume'].collidepoint(sx, sy):
            self.modal = None
        elif b['settings'].collidepoint(sx, sy):
            self.modal = 'settings'
        elif b['town'].collidepoint(sx, sy):
            self.modal = None
            self.enter_town()
        elif b['title'].collidepoint(sx, sy):
            self.modal = None
            self.state = 'title'
        elif b['quit'].collidepoint(sx, sy):
            self.running = False

    def _draw_pause_modal(self):
        """Velgrad-Pause: Pergament-Tablet mit Filigree-Frame."""
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        b = self._pause_buttons()
        r = b['rect']
        # Pergament-Gradient
        page = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        for py in range(r.h):
            t = py / max(1, r.h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (r.w, py))
        self.screen.blit(page, r.topleft)
        # Doppel-Rahmen
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, r, 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (r.x + 4, r.y + 4, r.w - 8, r.h - 8), 1)
        # Filigree-Ecken
        _asp.draw_filigree_corners(self.screen, r, bronze, size=24)
        # Aspekt-Watermark
        _asp.draw_aspect_watermark(self.screen, r,
                                    self.player.cls, alpha=18)

        # Eyebrow + Titel — eigene Zone ueber den Spalten, mittig
        eyebrow = self.font_small.render(
            '— DER ATEM ZÄHLT —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (r.centerx - eyebrow.get_width() // 2, r.y + 16))
        title_text = 'P A U S E'
        title = self.font_title.render(title_text, True, pal['halo'])
        title_sh = self.font_title.render(title_text, True, (10, 6, 4))
        title_x = r.centerx - title.get_width() // 2
        self.screen.blit(title_sh, (title_x + 2, r.y + 41))
        self.screen.blit(title, (title_x, r.y + 40))
        # Ornament-Divider direkt unter dem Title
        _asp.draw_ornament_divider(
            self.screen, r.x + 24, r.y + 110, r.w - 48, bronze)
        # Update #180: vertikale Spalten-Trennung zwischen Buttons + Build
        col_div_x = b['snapshot'].x - 14
        col_top = b['resume'].y - 6
        col_bot = b['quit'].bottom + 6
        pygame.draw.line(self.screen, (90, 70, 40),
                          (col_div_x, col_top),
                          (col_div_x, col_bot), 1)

        # Buttons im Velgrad-Style
        labels = [
            ('resume', 'Weiterspielen'),
            ('settings', 'Einstellungen'),
            ('town', 'Zur Stadt'),
            ('title', 'Zum Titel'),
            ('quit', 'Spiel beenden'),
        ]
        mx, my = pygame.mouse.get_pos()
        for key, label in labels:
            br = b[key]
            hovered = br.collidepoint(mx, my)
            # Vertikal-Gradient-Hintergrund
            bg = pygame.Surface((br.w, br.h), pygame.SRCALPHA)
            for hy in range(br.h):
                t = hy / max(1, br.h - 1)
                rr = int(50 + (28 - 50) * t)
                gg = int(35 + (20 - 35) * t)
                bb = int(14 + (8 - 14) * t)
                pygame.draw.line(bg, (rr, gg, bb, 250),
                                  (0, hy), (br.w, hy))
            self.screen.blit(bg, br.topleft)
            # Hover-Glow
            if hovered:
                glow = pygame.Surface((br.w + 8, br.h + 8),
                                       pygame.SRCALPHA)
                pygame.draw.rect(glow, (*pal['bright'], 80),
                                  (0, 0, br.w + 8, br.h + 8), 3)
                self.screen.blit(glow, (br.x - 4, br.y - 4))
                col = pal['halo']
            else:
                col = (227, 180, 64)
            # Border
            pygame.draw.rect(self.screen, col, br, 2)
            # Top-Highlight
            pygame.draw.line(self.screen,
                              tuple(min(255, c + 30) for c in col[:3]),
                              (br.x, br.y), (br.x + br.w, br.y), 1)
            # Label
            ls = self.font_med.render(label, True, (243, 213, 114))
            ls_sh = self.font_med.render(label, True, (10, 6, 4))
            self.screen.blit(ls_sh,
                              (br.centerx - ls.get_width() // 2 + 1,
                               br.centery - ls.get_height() // 2 + 1))
            self.screen.blit(ls, ls.get_rect(center=br.center))

        # Update #94: Compact Currency-Overview unterhalb der Buttons.
        # Lore-Anker: Mahnmal-Verwahrer-Inventar.
        self._draw_pause_currency_overview(r)
        # Update #132 (Y-08): Build-Snapshot rechts
        self._draw_pause_build_snapshot(b['snapshot'])

    def _draw_pause_build_snapshot(self, rect):
        """Update #132 (Y-08): Kompakter Build-Snapshot im Pause-Modal.

        Rechte Spalte zeigt:
          - Klasse + Stufe + Aspekt-Lineage
          - Equipped weapon + offhand (Slot-Snapshot)
          - Top-3 allokierte Skill-Tree-Nodes
          - Mahnmal-Pakt-Stacks (Aspekt-Boni)
          - Faction-Tier-Summary (zwei höchste)
        """
        from . import aspects as _asp
        from . import faction as _fac
        from .constants import CLASSES, TREE_NODES
        p = self.player
        cls_data = CLASSES.get(p.cls, {})
        bronze = (154, 118, 66)
        pal = _asp.aspect_palette(p.cls)
        # Header
        header = self.font_small.render('— BUILD —', True, (180, 140, 80))
        self.screen.blit(header,
                          (rect.centerx - header.get_width() // 2, rect.y))
        cy = rect.y + 20
        # Klasse + Stufe
        cls_name = cls_data.get('name', p.cls)
        cls_line = self.font_med.render(
            f'{cls_name}  ·  Stufe {p.level}', True, pal['halo'])
        self.screen.blit(cls_line, (rect.x, cy))
        cy += cls_line.get_height() + 4
        # Faction-/Aspekt-Lineage über aspects.aspect_palette + desc
        desc = cls_data.get('desc', '')
        if desc:
            # nur erster Satz
            first_part = desc.split('.')[0]
            if len(first_part) > 48:
                first_part = first_part[:45] + '…'
            ls = self.font_small.render(
                first_part, True, (180, 160, 130))
            self.screen.blit(ls, (rect.x, cy))
            cy += ls.get_height() + 2
        # Divider
        pygame.draw.line(self.screen, bronze,
                          (rect.x, cy + 4),
                          (rect.right, cy + 4), 1)
        cy += 12
        # Equipped Waffe + Offhand
        eq = getattr(p, 'equipment', {}) or {}
        weapon = eq.get('weapon')
        offhand = eq.get('offhand')
        wp_text = (weapon.name if weapon else '—')
        oh_text = (offhand.name if offhand else '—')
        for lbl, txt, col in [
            ('Waffe:',    wp_text, (220, 200, 160)),
            ('Offhand:',  oh_text, (200, 180, 140)),
        ]:
            ll = self.font_small.render(lbl, True, (180, 150, 100))
            self.screen.blit(ll, (rect.x, cy))
            tt = self.font_small.render(txt, True, col)
            self.screen.blit(tt, (rect.x + 80, cy))
            cy += ll.get_height() + 2
        cy += 6
        # Top-3 allokierte Tree-Nodes
        tree = getattr(p, 'tree', {}) or {}
        if tree:
            sub = self.font_small.render(
                'Talente (Top 3):', True, (180, 150, 100))
            self.screen.blit(sub, (rect.x, cy))
            cy += sub.get_height() + 1
            # Sort by rank descending
            sorted_nodes = sorted(tree.items(),
                                    key=lambda kv: -kv[1])
            for nid, rank in sorted_nodes[:3]:
                node = TREE_NODES.get(nid, {})
                nname = node.get('name', nid)
                line = f'  • {nname} ({rank})'
                ns = self.font_small.render(line, True, (220, 220, 180))
                self.screen.blit(ns, (rect.x, cy))
                cy += ns.get_height() + 1
            cy += 4
        # Mahnmal-Pakt
        bless = getattr(p, 'mahnmal_blessings', {}) or {}
        bless_total = sum(int(v) for v in bless.values())
        if bless_total > 0:
            sub = self.font_small.render(
                'Mahnmal-Pakt:', True, (180, 150, 100))
            self.screen.blit(sub, (rect.x, cy))
            cy += sub.get_height() + 1
            ASPECT_NAMES = {1: 'Kharn', 2: 'Nheyra', 3: 'Ousen',
                             4: 'Valsa', 5: 'Im-Nesh', 6: 'Shulavh',
                             7: 'Der Siebte'}
            for aid in range(1, 8):
                stacks = int(bless.get(aid, 0))
                if stacks <= 0:
                    continue
                a_name = ASPECT_NAMES.get(aid, f'#{aid}')
                line = f'  • {a_name}: {stacks}/5'
                ns = self.font_small.render(line, True, (220, 200, 140))
                self.screen.blit(ns, (rect.x, cy))
                cy += ns.get_height() + 1
            cy += 4
        # Top-2 Faction-Reps
        rep_dict = getattr(p, 'faction_rep', {}) or {}
        top_reps = sorted(rep_dict.items(),
                          key=lambda kv: -abs(int(kv[1])))[:2]
        if top_reps:
            sub = self.font_small.render(
                'Fraktionen:', True, (180, 150, 100))
            self.screen.blit(sub, (rect.x, cy))
            cy += sub.get_height() + 1
            for fkey, _ in top_reps:
                tier_idx, tier_name = _fac.get_tier(p, fkey)
                rep_val = _fac.get_rep(p, fkey)
                fac_name = _fac.faction_display_name(fkey)
                col = ((220, 180, 110) if tier_idx >= 1
                       else (180, 150, 130) if tier_idx >= 0
                       else (220, 130, 110))
                line = f'  • {fac_name}: {tier_name} ({rep_val:+d})'
                ns = self.font_small.render(line, True, col)
                self.screen.blit(ns, (rect.x, cy))
                cy += ns.get_height() + 1

    def _draw_pause_currency_overview(self, modal_rect):
        """Update #94: Zeigt alle Currencies kompakt im Pause-Modal-Footer."""
        p = self.player
        # Position: zwischen letztem Button (endet bei modal.y+340) und Modal-Bottom
        cx0 = modal_rect.x + 30
        cy0 = modal_rect.y + modal_rect.h - 62
        cw = modal_rect.w - 60
        # Divider
        pygame.draw.line(self.screen, (90, 70, 40),
                          (cx0, cy0 - 6), (cx0 + cw, cy0 - 6), 1)
        # 2-Spalten Currency-Mini-Display
        marken_total = sum(getattr(p, 'mahnmal_marken', {}).values())
        uncut_total = sum(getattr(p, 'uncut_gems', {}).values())
        rows = [
            (f'Gold: {getattr(p, "gold", 0)}',         (243, 213, 114)),
            (f'Mahnmal-Marken: {marken_total}',         (200, 170, 100)),
            (f'Orbs of Regret: {getattr(p, "orbs_of_regret", 0)}',
             (220, 180, 240)),
            (f'Uncut-Steine: {uncut_total}',           (170, 120, 240)),
            (f'Splitter: {getattr(p, "shards", 0)}',   (180, 220, 200)),
            (f'Lore-Frags: {getattr(p, "lore_fragments", 0)}',
             (180, 200, 160)),
        ]
        col_w = cw // 2
        line_h = 14
        for i, (text, col) in enumerate(rows):
            col_idx = i % 2
            row_idx = i // 2
            tx = cx0 + col_idx * col_w
            ty = cy0 + row_idx * line_h
            self.screen.blit(self.font_small.render(text, True, col),
                              (tx, ty))

    def _draw_gemcutter_modal(self):
        """Otreth-Hohlauge-Gemcutter (PLAN J-10).

        Update #30: Velgrad-Tome-Style mit Filigree.
        """
        from . import class_skills as _cs
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        w, h = 720, 540
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            t = py / max(1, h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        _asp.draw_filigree_corners(
            self.screen, pygame.Rect(x, y, w, h), bronze, size=24)
        _asp.draw_aspect_watermark(
            self.screen, pygame.Rect(x, y, w, h),
            self.player.cls, alpha=18)
        # Header
        eyebrow = self.font_small.render(
            '— DER STEINSCHLEIFER —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (x + w // 2 - eyebrow.get_width() // 2, y + 14))
        title_text = 'O T R E T H   H O H L A U G E'
        title = self.font_med.render(title_text, True, pal['halo'])
        title_sh = self.font_med.render(title_text, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (x + w // 2 - title.get_width() // 2 + 1,
                           y + 33))
        self.screen.blit(title,
                          (x + w // 2 - title.get_width() // 2, y + 32))
        sub = self.font_small.render(
            '„Bring mir Steine. Bring sie ungelesen."',
            True, (200, 160, 100))
        self.screen.blit(sub,
                          (x + w // 2 - sub.get_width() // 2, y + 60))
        hint = self.font_small.render(
            'F: Schließen  ·  Klick: Gravieren/Aufleveln',
            True, TEXT_DIM)
        self.screen.blit(hint,
                          (x + w - hint.get_width() - 20, y + 22))
        _asp.draw_ornament_divider(
            self.screen, x + 20, y + 84, w - 40, bronze)

        p = self.player

        # Uncut-Gems-Sektion (links) — verschoben unter Header-Divider
        col1_x = x + 26
        col_top = y + 100
        uh = self.font_small.render('UNCUT MEMORY-SHARDS',
                                     True, (220, 200, 150))
        self.screen.blit(uh, (col1_x, col_top))
        cy = col_top + 22
        uncut = getattr(p, 'uncut_gems', {})
        if not uncut:
            ls = self.font_small.render(
                '(keine — sammle bei Bossen)', True, TEXT_DIM)
            self.screen.blit(ls, (col1_x + 8, cy))
        else:
            for lvl in sorted(uncut.keys()):
                n = uncut[lvl]
                if n <= 0:
                    continue
                ls = self.font_small.render(
                    f'• Uncut Lvl {lvl} × {n}', True, TEXT)
                self.screen.blit(ls, (col1_x + 8, cy))
                cy += 18

        # Skill-Gems-Sektion (rechts, klassen-Pool)
        col2_x = x + w // 2 + 10
        sh = self.font_small.render('DEINE SKILL-GEMS',
                                     True, (220, 200, 150))
        self.screen.blit(sh, (col2_x, col_top))
        cy2 = col_top + 22
        # Iteriere über klassen-pool ∪ unlocked (auch alte SKILL_INFO-Skills)
        pool = _cs.get_skill_pool(p.cls)
        unlocked = getattr(p, 'unlocked_skills', set())
        gem_levels = getattr(p, 'gem_levels', {})
        # Erweitere display-set: alle Klassen-Pool-Gems + alle unlocked
        # Skills auch wenn die nicht im Pool sind (Legacy-SKILL_INFO).
        from .skills import SKILL_INFO as _SI
        display = dict(pool)
        for sid in unlocked:
            if sid == 'melee' or sid in display:
                continue
            info = _SI.get(sid)
            if info is None:
                continue
            from . import gems as _gm
            display[sid] = _gm.skillgem_from_legacy(sid, info)
        self._gemcutter_rects = []
        for sid, gem in list(display.items())[:14]:
            is_unlocked = sid in unlocked
            cur_level = gem_levels.get(sid, 1 if is_unlocked else 0)
            line_rect = pygame.Rect(col2_x, cy2, w // 2 - 30, 18)
            self._gemcutter_rects.append((line_rect, sid, is_unlocked))
            # Hover-Background
            mx, my = pygame.mouse.get_pos()
            if line_rect.collidepoint(mx, my):
                pygame.draw.rect(self.screen, (60, 40, 20), line_rect)
            label_col = (160, 220, 160) if is_unlocked else (160, 140, 100)
            status = (f'Lvl {cur_level}' if is_unlocked else 'GRAVIEREN')
            ls = self.font_small.render(
                f'{status:<10} {gem.name}', True, label_col)
            self.screen.blit(ls, (col2_x + 6, cy2))
            cy2 += 18
            if cy2 > y + h - 60:
                break

        # Footer mit Lore
        foot = self.font_small.render(
            '„Sie wollen erinnert werden. Das ist das einzige '
            'Geheimnis dieser Steine."',
            True, (200, 180, 140))
        self.screen.blit(foot, foot.get_rect(
            center=(x + w // 2, y + h - 30)))

    def _handle_gemcutter_click(self, mx, my):
        """Click in Gemcutter-Modal: graviert oder levelt einen Skill-Gem."""
        rects = getattr(self, '_gemcutter_rects', [])
        if not rects:
            return False
        for rect, sid, is_unlocked in rects:
            if not rect.collidepoint(mx, my):
                continue
            p = self.player
            uncut = getattr(p, 'uncut_gems', {})
            if not is_unlocked:
                # GRAVIEREN: 1 Uncut Lvl 1
                if uncut.get(1, 0) > 0:
                    p.unlocked_skills.add(sid)
                    uncut[1] = uncut[1] - 1
                    p.gem_levels[sid] = 1
                    self.toast(f'Otreth graviert: {sid} (Lvl 1)',
                                (255, 200, 100))
                else:
                    self.toast('Otreth: „Bring mir einen Uncut-Stein."',
                                (200, 150, 100))
            else:
                # AUFLEVELN: nächst-höherer Uncut-Stein nötig
                cur = p.gem_levels.get(sid, 1)
                if cur >= 20:
                    self.toast('Otreth: „Mehr habe ich nicht zu geben."',
                                (200, 150, 100))
                    return True
                need_lvl = cur + 1
                # Suche nach Uncut >= need_lvl
                available = sorted(
                    (l for l, n in uncut.items() if n > 0 and l >= need_lvl))
                if available:
                    use_lvl = available[0]
                    uncut[use_lvl] -= 1
                    p.gem_levels[sid] = cur + 1
                    self.toast(f'{sid} auf Lvl {cur + 1} geschliffen.',
                                (180, 240, 180))
                else:
                    self.toast(
                        f'Otreth: „Brauchst Uncut Lvl {need_lvl} oder höher."',
                        (200, 150, 100))
            return True
        return False

    def _draw_fullmap_modal(self):
        """Vollbild-Karte (PLAN B-08, M / TAB-Taste).

        Update #30: Velgrad-Tome-Style mit Filigree + Aspekt-Akzent.
        """
        from . import regions as _reg
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)

        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((4, 3, 2, 240))
        self.screen.blit(overlay, (0, 0))

        # Header: Eyebrow + Region-Name + Akt-Sub
        biome = self.biome
        region = _reg.region_for_biome(biome)
        eyebrow = self.font_small.render(
            '— TABULA VELGRADENSIS —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (SCREEN_W // 2 - eyebrow.get_width() // 2, 20))
        title_str = (_reg.region_label(biome) or biome.upper()).upper()
        title = self.font_big.render(title_str, True, pal['halo'])
        title_sh = self.font_big.render(title_str, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (SCREEN_W // 2 - title.get_width() // 2 + 2,
                           42 + 2))
        self.screen.blit(title,
                          (SCREEN_W // 2 - title.get_width() // 2, 42))
        if region is not None:
            sub_text = (f"{region['hub_town']}  ·  {region['faction']}"
                        f"  ·  Aspekt: {region['aspect']}")
            sub = self.font_small.render(sub_text, True, (180, 140, 80))
            self.screen.blit(sub,
                              sub.get_rect(center=(SCREEN_W // 2, 88)))
            quote_text = '„' + region['short_desc'] + '"'
            qs = self.font_small.render(quote_text, True, (215, 200, 175))
            self.screen.blit(qs,
                              qs.get_rect(center=(SCREEN_W // 2, 108)))
        # Ornament-Divider
        _asp.draw_ornament_divider(
            self.screen, SCREEN_W // 2 - 300, 122, 600,
            (154, 118, 66))

        # Map-Body
        map_top = 130
        map_size = SCREEN_H - 200
        map_x = SCREEN_W // 2 - map_size // 2
        map_y = map_top

        zoom = getattr(self, '_fullmap_zoom', 1.0)
        # Skala = 0.06 (Mini-Map-base) × Zoom × Verstärkung (4× wegen Fullsize).
        scale = 0.06 * 4.0 * zoom

        # Hintergrund
        bg = pygame.Surface((map_size, map_size), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 240))
        self.screen.blit(bg, (map_x, map_y))
        accent = _reg.region_accent(biome, GOLD)
        pygame.draw.rect(self.screen, accent,
                         (map_x, map_y, map_size, map_size), 2)

        p = self.player
        cx = map_x + map_size // 2
        cy = map_y + map_size // 2

        # Tiles wenn Grid existiert (Dungeon)
        grid = self.grid
        if grid is not None:
            discovered = getattr(grid, '_minimap_discovered', set())
            from .dungeon_gen import FLOOR, DOOR, TRAP, SECRET
            WALKABLE = (FLOOR, DOOR, TRAP, SECRET)
            biome_col = world.BIOMES[biome]['ground']
            tile_size = max(2, int(grid.cell * scale))
            for (tx, ty) in discovered:
                wx, wy = grid.cell_to_world_center(tx, ty)
                rx = int((wx - p.pos.x) * scale + cx - tile_size // 2)
                ry = int((wy - p.pos.y) * scale + cy - tile_size // 2)
                if rx + tile_size < map_x or ry + tile_size < map_y \
                        or rx > map_x + map_size or ry > map_y + map_size:
                    continue
                tt = grid.get(tx, ty)
                col = biome_col if tt in WALKABLE else (24, 16, 10)
                # Edge-Gradient
                undisc = sum(1 for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1))
                             if (tx + ox, ty + oy) not in discovered)
                alpha = max(150, 255 - undisc * 30)
                tile_surf = pygame.Surface((tile_size, tile_size),
                                            pygame.SRCALPHA)
                tile_surf.fill((*col[:3], alpha))
                self.screen.blit(tile_surf, (rx, ry))
        else:
            # Town/Outpost — pauschaler Boden-Tint
            tint = pygame.Surface((map_size - 4, map_size - 4),
                                   pygame.SRCALPHA)
            tint.fill((*world.BIOMES[biome]['ground'], 60))
            self.screen.blit(tint, (map_x + 2, map_y + 2))

        # POIs (NPCs, Portale, Boss, Loot)
        def _to_map(pos):
            rx = (pos.x - p.pos.x) * scale + cx
            ry = (pos.y - p.pos.y) * scale + cy
            return (int(rx), int(ry))

        def _in_map(rx, ry):
            return (map_x + 4 < rx < map_x + map_size - 4
                    and map_y + 4 < ry < map_y + map_size - 4)

        # B-09 (Update #48): POI-Hover-Tooltip-Tracker.  Sammelt
        # gerenderte POIs als (rect, label, sub) Tuples; nach allen Layern
        # wird das geklickte/gehoverte Item für den Tooltip ausgewählt.
        fullmap_pois = []

        # NPCs mit Name
        for npc in getattr(self, 'npcs', ()):
            rx, ry = _to_map(npc.pos)
            if not _in_map(rx, ry):
                continue
            pygame.draw.circle(self.screen, (255, 230, 150), (rx, ry), 6)
            pygame.draw.circle(self.screen, (40, 30, 16), (rx, ry), 6, 1)
            # Name als Tooltip ab Zoom ≥ 1.0
            if zoom >= 1.0:
                ns = self.font_small.render(npc.name, True, (255, 230, 180))
                self.screen.blit(ns, (rx + 10, ry - 8))
            fullmap_pois.append((
                pygame.Rect(rx - 8, ry - 8, 16, 16),
                npc.name,
                f'NPC · {npc.kind}'))

        # Dungeon-Portale (Stadt)
        for dp in getattr(self, 'dungeon_portals', ()):
            rx, ry = _to_map(dp.pos)
            if _in_map(rx, ry):
                pygame.draw.rect(self.screen, (140, 200, 240),
                                 (rx - 5, ry - 7, 10, 14))
                pygame.draw.rect(self.screen, (220, 240, 255),
                                 (rx - 5, ry - 7, 10, 14), 1)
                if zoom >= 1.0:
                    from .constants import DUNGEONS
                    name = DUNGEONS[dp.dungeon_id]['name']
                    ns = self.font_small.render(name, True, (200, 220, 240))
                    self.screen.blit(ns, (rx + 10, ry - 8))
                from .constants import DUNGEONS as _DG
                dname = _DG[dp.dungeon_id]['name']
                lvl_req = _DG[dp.dungeon_id].get('level_req', 1)
                fullmap_pois.append((
                    pygame.Rect(rx - 8, ry - 10, 16, 18),
                    dname,
                    f'Dungeon · Stufe ≥ {lvl_req}'))

        # Boss-Marker — Update #42: Edge-Clamp + Pulse für off-view Boss
        import time as _t
        _puls = 0.7 + 0.3 * abs(math.sin(_t.time() * 2.4))
        for e in getattr(self, 'enemies', ()):
            if getattr(e, 'is_boss', False) and not e.dying:
                rx, ry = _to_map(e.pos)
                # Clamp an Map-Innenrand wenn off-view
                cl_rx = max(map_x + 12, min(map_x + map_size - 12, rx))
                cl_ry = max(map_y + 12, min(map_y + map_size - 12, ry))
                off = (cl_rx != rx) or (cl_ry != ry)
                pul_col = (int(255 * _puls), int(80 * _puls), int(80 * _puls))
                pygame.draw.circle(self.screen, pul_col,
                                   (cl_rx, cl_ry), 10)
                pygame.draw.circle(self.screen, (255, 240, 240),
                                   (cl_rx, cl_ry), 10, 2)
                # Mini-Schädel-Augen
                pygame.draw.circle(self.screen, (10, 6, 4),
                                   (cl_rx - 3, cl_ry - 1), 2)
                pygame.draw.circle(self.screen, (10, 6, 4),
                                   (cl_rx + 3, cl_ry - 1), 2)
                pygame.draw.rect(self.screen, (10, 6, 4),
                                 (cl_rx - 2, cl_ry + 2, 5, 2))
                if off:
                    # Richtungs-Pfeil zur Boss-Richtung
                    dvx, dvy = e.pos.x - p.pos.x, e.pos.y - p.pos.y
                    dlen = math.hypot(dvx, dvy)
                    if dlen > 1:
                        nx_, ny_ = dvx / dlen, dvy / dlen
                        tipx = cl_rx + nx_ * 14
                        tipy = cl_ry + ny_ * 14
                        pygame.draw.polygon(self.screen, (255, 200, 80), [
                            (tipx, tipy),
                            (cl_rx - ny_ * 6, cl_ry + nx_ * 6),
                            (cl_rx + ny_ * 6, cl_ry - nx_ * 6),
                        ])
                if zoom >= 1.0:
                    bn = e.boss_name or 'Boss'
                    ns = self.font_small.render(bn, True, (255, 200, 200))
                    self.screen.blit(ns, (cl_rx + 14, cl_ry - 8))

        # Boss-Room-Rect (Dungeon)
        if grid is not None and hasattr(grid, 'boss_room_rect'):
            bx, by, bw_, bh_ = grid.boss_room_rect
            rx1 = (bx - p.pos.x) * scale + cx
            ry1 = (by - p.pos.y) * scale + cy
            rect_w = int(bw_ * scale)
            rect_h = int(bh_ * scale)
            if rect_w > 4 and rect_h > 4:
                marker = pygame.Surface((rect_w, rect_h), pygame.SRCALPHA)
                pygame.draw.rect(marker, (255, 100, 100, 80),
                                 (0, 0, rect_w, rect_h))
                pygame.draw.rect(marker, (255, 200, 200, 200),
                                 (0, 0, rect_w, rect_h), 2)
                self.screen.blit(marker, (int(rx1), int(ry1)))

        # Player-Marker in der Mitte
        pygame.draw.circle(self.screen, GOLD_BRIGHT, (cx, cy), 7)
        pygame.draw.circle(self.screen, WHITE, (cx, cy), 7, 2)
        # Klassen-Aura
        from . import quotes as _q
        fac = _q.class_faction(p.cls)
        if fac is not None:
            pygame.draw.circle(self.screen, fac['color'],
                               (cx, cy), 14, 1)

        # B-09 (Update #48): POI-Hover-Tooltip
        mx, my = pygame.mouse.get_pos()
        for rect, label, sub in fullmap_pois:
            if rect.collidepoint(mx, my):
                # Tooltip rendern (auto-positioniert, nicht aus map raus)
                ls = self.font_small.render(label, True, (255, 230, 180))
                ss = self.font_small.render(sub, True, TEXT_DIM)
                tw = max(ls.get_width(), ss.get_width()) + 16
                th = ls.get_height() + ss.get_height() + 12
                tx = mx + 14
                ty = my + 14
                if tx + tw > SCREEN_W - 8:
                    tx = mx - tw - 14
                if ty + th > SCREEN_H - 8:
                    ty = my - th - 14
                tip_bg = pygame.Surface((tw, th), pygame.SRCALPHA)
                tip_bg.fill((20, 14, 8, 230))
                self.screen.blit(tip_bg, (tx, ty))
                pygame.draw.rect(self.screen, (154, 118, 66),
                                  (tx, ty, tw, th), 1)
                self.screen.blit(ls, (tx + 8, ty + 4))
                self.screen.blit(ss, (tx + 8, ty + 4 + ls.get_height() + 2))
                break

        # Footer mit Tasten-Hint
        zoom_label = (f'Zoom: {zoom:.1f}×  ·  Mausrad / +/- : Zoom  ·  '
                       f'M / TAB: Schließen')
        zs = self.font_small.render(zoom_label, True, TEXT_DIM)
        self.screen.blit(zs, zs.get_rect(center=(SCREEN_W // 2,
                                                  SCREEN_H - 40)))

    def _draw_codex_modal(self):
        """Codex (N-Taste): entdeckte Bestiarium-Mobs + Lore-Tafel-Texte
        + Die Sieben Aspekte (Lore-Bibel Teil 2).

        Tab-Navigation mit 1/2/3-Tasten oder Klick.
        Update #30: Velgrad-Tome-Page-Style.
        """
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        w, h = 880, 620
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament-Gradient
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            t = py / max(1, h - 1)
            r = int(42 + (28 - 42) * t)
            g = int(31 + (22 - 31) * t)
            b = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (r, g, b, 250), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        # Doppel-Rahmen
        pygame.draw.rect(self.screen, (60, 40, 22), (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        # Filigree-Ecken
        bronze = (154, 118, 66)
        _asp.draw_filigree_corners(self.screen, pygame.Rect(x, y, w, h),
                                    bronze, size=28)
        # Aspekt-Watermark
        _asp.draw_aspect_watermark(self.screen, pygame.Rect(x, y, w, h),
                                    self.player.cls, alpha=18)
        # Header (manuskript-style)
        head_l = self.font_small.render(
            'CODEX VELGRADENSIS', True, (180, 140, 80))
        self.screen.blit(head_l, (x + 28, y + 22))
        # Mittiger Titel
        title_text = 'D I E   V E R G E S S E N E N'
        title = self.font_med.render(title_text, True, pal['halo'])
        title_sh = self.font_med.render(title_text, True, (10, 6, 4))
        tx_c = x + w // 2 - title.get_width() // 2
        self.screen.blit(title_sh, (tx_c + 1, y + 17))
        self.screen.blit(title, (tx_c, y + 16))
        sub = self.font_small.render('„Was du nicht erinnerst, '
                                      'wird vergessen."',
                                      True, (200, 160, 100))
        self.screen.blit(sub, (x + 28, y + 44))
        hint = self.font_small.render(
            '1/2/3/4/5: Tabs  ·  N: Schließen', True, TEXT_DIM)
        self.screen.blit(hint, (x + w - hint.get_width() - 28, y + 22))
        # Ornament-Divider unter Titel
        _asp.draw_ornament_divider(
            self.screen, x + 28, y + 58, w - 56, bronze)

        # Tab-Bar
        tab_y = y + 64
        tabs = [('bestiary',     'Bestiarium'),
                ('lore',         'Lore-Tafeln'),
                ('aspects',      'Die Sieben Aspekte'),
                ('achievements', 'Achievements'),
                ('factions',     'Fraktionen'),    # Update #118
                ('howto',        'Wie Spielen')]   # Update #132 (Y-03)
        cur_tab = getattr(self, '_codex_tab', 'bestiary')
        self._codex_tab_rects = []
        tx = x + 20
        for key, label in tabs:
            ts = self.font_small.render(label, True,
                GOLD_BRIGHT if key == cur_tab else TEXT_DIM)
            tw = ts.get_width() + 24
            rect = pygame.Rect(tx, tab_y, tw, 26)
            self._codex_tab_rects.append((rect, key))
            if key == cur_tab:
                pygame.draw.rect(self.screen, (40, 30, 14), rect)
                pygame.draw.rect(self.screen, GOLD, rect, 1)
            else:
                pygame.draw.rect(self.screen, (24, 18, 10), rect)
                pygame.draw.rect(self.screen, (60, 50, 40), rect, 1)
            self.screen.blit(ts, (tx + 12, tab_y + 6))
            tx += tw + 6

        # Tab-spezifischer Inhalt
        content_top = y + 100
        if cur_tab == 'bestiary':
            self._draw_codex_bestiary(x, y, w, h, content_top)
        elif cur_tab == 'lore':
            self._draw_codex_lore(x, y, w, h, content_top)
        elif cur_tab == 'aspects':
            self._draw_codex_aspects(x, y, w, h, content_top)
        elif cur_tab == 'achievements':
            self._draw_codex_achievements(x, y, w, h, content_top)
        elif cur_tab == 'factions':
            self._draw_codex_factions(x, y, w, h, content_top)
        elif cur_tab == 'howto':
            self._draw_codex_howto(x, y, w, h, content_top)

    def _draw_codex_factions(self, x, y, w, h, top):
        """Update #118 (WELT_AUFBAU 6.1): Faction-Status-Panel im Codex.

        Pro 7 Velgrad-Fraktionen: Lore-Name, Aspekt, Rep-Bar mit Tier-
        Markern, freigeschaltete Unlocks, Konflikt-Warnung wenn Tier ≤ -1.
        """
        from . import faction as _fac
        p = self.player
        # Header-Quote (Lore-Anker)
        header = self.font_small.render(
            '„Die Welt vergisst dich. Die Fraktionen erinnern sich."',
            True, (200, 180, 140))
        self.screen.blit(header, (x + 30, top))

        row_y = top + 30
        row_h = 84
        row_w = w - 60
        # 7 Fraktionen iterieren in dieser festen Reihenfolge (Lore-Reihe)
        order = ['mahnmal_gilde', 'erblinde_kirche', 'tribunal_asche',
                 'saattraeger', 'knochenwitwen', 'speerschwestern',
                 'stille_schritte']
        # Bei mehr als ~5 sichtbar machen wir 2 Spalten
        col_w = (row_w - 20) // 2
        col_h = row_h
        for i, fkey in enumerate(order):
            col = i % 2
            row = i // 2
            cx = x + 30 + col * (col_w + 20)
            cy = row_y + row * (col_h + 10)
            cfg = _fac.FACTIONS.get(fkey, {})
            name = cfg.get('name', fkey)
            color = cfg.get('color', (200, 180, 140))
            aspect = cfg.get('aspect', '—')
            rep = _fac.get_rep(p, fkey)
            tier_idx, tier_name = _fac.get_tier(p, fkey)

            # Hintergrund-Box
            box = pygame.Rect(cx, cy, col_w, col_h)
            bg = pygame.Surface((box.w, box.h), pygame.SRCALPHA)
            tier_dim = (28, 22, 18, 220) if tier_idx >= 0 \
                else (40, 22, 22, 220)
            bg.fill(tier_dim)
            self.screen.blit(bg, box.topleft)
            border_col = color if tier_idx >= 1 else (
                (180, 100, 80) if tier_idx <= -1 else (80, 70, 60))
            pygame.draw.rect(self.screen, border_col, box, 2)

            # Name + Aspekt
            nm = self.font_small.render(f'{name}', True, color)
            self.screen.blit(nm, (cx + 10, cy + 6))
            asp = self.font_small.render(
                f'Aspekt: {aspect}', True, (170, 160, 140))
            self.screen.blit(asp, (cx + col_w - asp.get_width() - 10,
                                    cy + 6))

            # Tier-Label
            tier_color = color if tier_idx >= 1 else (
                (220, 130, 100) if tier_idx <= -1 else (160, 150, 130))
            tier_lbl = self.font_small.render(
                f'Tier: {tier_name}  ({rep:+d} Rep)', True, tier_color)
            self.screen.blit(tier_lbl, (cx + 10, cy + 28))

            # Rep-Bar von -200 bis +200, Marker bei -100/-50/0/50/100/200
            bar_x = cx + 10
            bar_y = cy + 52
            bar_w = col_w - 20
            bar_h = 8
            # Hintergrund
            pygame.draw.rect(self.screen, (40, 32, 24),
                              (bar_x, bar_y, bar_w, bar_h))
            # Fill — clamp [-200, 200] zu [0, 1]
            fill_norm = (rep + 200) / 400.0
            fill_norm = max(0.0, min(1.0, fill_norm))
            fill_w = int(bar_w * fill_norm)
            if rep >= 0:
                pygame.draw.rect(self.screen, color,
                                  (bar_x + bar_w // 2,
                                   bar_y,
                                   max(1, fill_w - bar_w // 2), bar_h))
            else:
                # Negative Fill geht von Mitte nach links
                neg_w = bar_w // 2 - fill_w
                pygame.draw.rect(self.screen, (180, 80, 70),
                                  (bar_x + fill_w,
                                   bar_y, max(1, neg_w), bar_h))
            # Nullmarkierung (Mitte)
            pygame.draw.line(self.screen, (140, 130, 100),
                              (bar_x + bar_w // 2, bar_y - 2),
                              (bar_x + bar_w // 2, bar_y + bar_h + 2), 1)
            # Threshold-Marker bei +50/+100/+200 (Unlocks)
            for thresh in (50, 100, 200):
                tx = bar_x + int(((thresh + 200) / 400.0) * bar_w)
                marker_col = (220, 220, 160) if rep >= thresh \
                    else (90, 80, 70)
                pygame.draw.line(self.screen, marker_col,
                                  (tx, bar_y - 3),
                                  (tx, bar_y + bar_h + 3), 1)
            pygame.draw.rect(self.screen, (90, 78, 60),
                              (bar_x, bar_y, bar_w, bar_h), 1)

            # Unlock-Hint (nächster Unlock)
            unlocks = _fac.UNLOCKS.get(fkey, [])
            next_unlock = None
            for thresh, uid, label in unlocks:
                if rep < thresh:
                    next_unlock = (thresh, label)
                    break
            if next_unlock is not None:
                ul_text = (f'Nächstes: {next_unlock[1]} '
                            f'(@ {next_unlock[0]:+d})')
                ul_col = (180, 170, 140)
            else:
                ul_text = '✓ Alle Stufen erreicht'
                ul_col = (160, 220, 160)
            ul_surf = self.font_small.render(ul_text, True, ul_col)
            self.screen.blit(ul_surf, (cx + 10, cy + 66))

    # Update #132 (Y-03): Codex „Wie Spielen" — Lore-konformes Manual.
    # 5 Seiten zu Klassen, Affixes, Ailments, Crafting, Mahnmal-Pakt.
    # Quelle pro Sektion: kurz aus VELGRAD_LORE_BIBEL + POE2_SKILLS-Briefing.
    _CODEX_HOWTO_PAGES = [
        ('Klassen & Aspekte',
         '8 Velgrad-Klassen, gespeist aus den Sieben Aspekten:',
         [
            '• Warrior — Kharns Eisen.  Phys-Slam + Knockback.  Mace.',
            '• Witch — Vossharils Faden.  Chaos/DoT.  Wand + Skull.',
            '• Sorceress / Mage — Valsas Flamme + Im-Neshs Blitz.  Spell-Spam.',
            '• Ranger — Nheyras Atem.  Bow.  Lightning/Frost/Burn-Arrow.',
            '• Mercenary / Rogue — Crossbow.  Burst-Combos (Galvanic / Permafrost).',
            '• Huntress — Speer + Wirbel.  Zhar-Eth-Wind-Choreographie.',
            '• Druid — Saatträgerinnen.  Storm-Call + Spore + Hailstorm.',
            '• Monk — Stille-Aspekt.  Tempest-Bell + Glacial-Cascade.',
            '',
            'Aspekt-Lineage prägt Sound-Signature, Crit-Color und Death-Quote.',
         ]),
        ('Affixes & Rarity',
         'Gegner-Affixes (Tier-Aura-Farbe = Rarity):',
         [
            '• Magic (blau, +1 Affix):    +60 % HP, ×1.2 Damage, ×1.2 Loot',
            '• Rare (gelb, +2–4 Affixes): +160 % HP, ×1.6 DMG, ×1.8 Loot',
            '• Unique (orange, +5–6):     +240 % HP, ×2.0 DMG, ×2.5 Loot',
            '',
            '10 Mob-Affixes: Flameweaver, Frostbearer, Stormcaller,',
            'Vampiric, Bloodthirsty, Soul-Eater, Necromancer, Phasing,',
            'Teleporter, Detonating.  Item-Affixes folgen demselben Schema.',
            '',
            'Champion / Mini-Boss / Boss = Tier-3, kein Leash, sticky_aggro.',
         ]),
        ('Ailments & Combos',
         'Statuseffekte (rendern als Pips über der HP-Bar):',
         [
            '• Burn (Valsa)  — Tick-DMG, max 10 Stacks, 4 s',
            '• Frost (Nheyra) — Slow, bei 5 Stacks → PINNED 1.5 s',
            '• Shock (Im-Nesh) — +25 % DMG genommen, 3 Stacks',
            '• Poison (Shulavh) — Chaos-Tick, 15 Stacks',
            '• Bleed (Kharn-Phys) — Phys-Tick, 8 Stacks',
            '• Maim / Crush — Slow / Defense-Break (Phys-Crits)',
            '• Armour-Break (Phys) — −10 % Phys-Res pro Stack',
            '',
            'Combo-Payoffs: Frozen+Cold ×1.5, Burning+Fire ×1.3,',
            'Shocked+Lightning ×1.4, Poison+Chaos ×1.25, Stun ×2.0.',
         ]),
        ('Crafting bei Otreth Hohlauge',
         '4 Aktionen am Anvil (West-Werkstatt):',
         [
            '• Aufwerten — Currency: Mahnmal-Schliff.  Hebt Item-Tier.',
            '• Umrollen — Currency: Aspekt-Splitter.  Würfelt Affixes neu.',
            '• Verzaubern — Currency: Mahnmal-Marke I.  Fügt Affix hinzu.',
            '• Salvage — Zerlegt Item zu Roh-Currency.',
            '',
            'Uncut Memory-Shards droppen von Bossen + Mini-Bossen.',
            'Mit Otreth → graviere einen Skill auf einen Uncut für Skill-Level.',
            '',
            'Schliff-Tier folgt Item-Level — höhere Tiers = bessere Rolls.',
         ]),
        ('Mahnmal-Pakt (Aspekt-Boni)',
         'F bei einer Mahnmal-Stele in Brassweir öffnet den Schrein:',
         [
            '• Verzehre 1 Marke I..VII → +1 Pakt-Stack mit dem Aspekt',
            '• Max 5 Stacks pro Aspekt',
            '',
            'Boni pro Stack:',
            '• Kharn (I) — +5 % Damage',
            '• Nheyra (II) — +5 % HP-Max',
            '• Ousen (III) — +0.5 HP-Regen pro Sekunde',
            '• Valsa (IV) — +4 % Fire-Damage',
            '• Im-Nesh (V) — +4 % Lightning-Damage',
            '• Shulavh (VI) — +4 % Cold-Damage',
            '• Der Siebte (VII) — +2 % auf ALLE Damage-Types',
            '',
            'Marken droppen von Bossen.  Mini-Bosse droppen Marke I.',
         ]),
    ]

    def _draw_codex_howto(self, x, y, w, h, top):
        """Update #132 (Y-03): How-to-Play-Codex-Tab.

        5 Lore-konforme Manual-Seiten.  Per Pfeil ← / → navigierbar
        (`_codex_howto_page`-Index).  Layout: Titel + Intro + Bullet-Liste.
        """
        page_idx = getattr(self, '_codex_howto_page', 0)
        page_idx = max(0, min(len(self._CODEX_HOWTO_PAGES) - 1, page_idx))
        title, intro, body = self._CODEX_HOWTO_PAGES[page_idx]
        cy = top
        # Seiten-Counter rechts oben
        cnt = self.font_small.render(
            f'Seite {page_idx + 1} / {len(self._CODEX_HOWTO_PAGES)}',
            True, (180, 150, 100))
        self.screen.blit(cnt, (x + w - 30 - cnt.get_width(), cy))
        # Titel
        ts = self.font_med.render(title, True, (255, 220, 100))
        self.screen.blit(ts, (x + 30, cy))
        cy += ts.get_height() + 4
        # Ornament-Divider
        from . import aspects as _asp
        bronze = (154, 118, 66)
        _asp.draw_ornament_divider(self.screen, x + 28, cy,
                                     w - 56, bronze)
        cy += 12
        # Intro
        intro_surf = self.font_small.render(intro, True, (220, 200, 160))
        self.screen.blit(intro_surf, (x + 30, cy))
        cy += intro_surf.get_height() + 8
        # Body-Zeilen
        for line in body:
            ls = self.font_small.render(line, True, (220, 220, 200))
            self.screen.blit(ls, (x + 30, cy))
            cy += 18
        # Navigation-Hint
        hint = self.font_small.render(
            '← / → Seite blättern   ·   1-6 Tabs wechseln',
            True, (150, 130, 100))
        self.screen.blit(hint,
                          (x + w // 2 - hint.get_width() // 2,
                           y + h - 36))

    def _draw_codex_bestiary(self, x, y, w, h, top):
        log = getattr(self, 'quest_log', None)
        from . import bestiary as _best
        cy = top
        if log is None or not log.bestiary_seen:
            ts = self.font_small.render(
                'Noch keine Wesen entdeckt — töte Gegner, um Codex-Einträge '
                'zu sammeln.', True, TEXT_DIM)
            self.screen.blit(ts, (x + 30, cy))
            return
        for key in sorted(log.bestiary_seen):
            entry = _best.BESTIARY.get(key, {})
            name = entry.get('display_name', key)
            tier = entry.get('tier', '?')
            act  = entry.get('act', '?')
            arch = entry.get('archetype', '?')
            head = self.font_small.render(
                f'• {name}  [Tier {tier} · Akt {act} · {arch}]',
                True, (255, 220, 100))
            self.screen.blit(head, (x + 30, cy))
            cy += 18
            quote = entry.get('lore_quote', '')
            if quote:
                qparts = self._wrap_codex(quote, 78)
                for line in qparts[:2]:
                    qs = self.font_small.render(
                        f'   „{line}"', True, (180, 160, 130))
                    self.screen.blit(qs, (x + 30, cy))
                    cy += 16
            cy += 6
            if cy > y + h - 40:
                break

    def _draw_codex_lore(self, x, y, w, h, top):
        log = getattr(self, 'quest_log', None)
        cy = top
        if log is None or not log.discovered_lore:
            ts = self.font_small.render(
                'Keine Lore-Tafeln gelesen — F auf Tafel zum Entdecken.',
                True, TEXT_DIM)
            self.screen.blit(ts, (x + 30, cy))
            return
        for text in list(log.discovered_lore):
            parts = self._wrap_codex(text, 90)
            for i, line in enumerate(parts):
                col = (215, 200, 175) if i == 0 else (185, 175, 155)
                prefix = '„' if i == 0 else '  '
                suffix = '"' if i == len(parts) - 1 else ''
                ls = self.font_small.render(
                    f'{prefix}{line}{suffix}', True, col)
                self.screen.blit(ls, (x + 30, cy))
                cy += 16
            cy += 8
            if cy > y + h - 40:
                break

    def _draw_codex_achievements(self, x, y, w, h, top):
        """Update #91: Codex-Tab Achievements (15 Stück).
        Erledigte = gold + Häkchen, locked = dim. Reward + Desc inline.
        """
        from . import achievements as _ach
        cy = top
        done = getattr(self, 'achievements_done', set())
        total = len(_ach.ACHIEVEMENTS)
        # Header
        head = self.font_small.render(
            f'„Jede Tat ist ein Schlag auf den Mahnmal-Stein." '
            f'  ·  {len(done)}/{total} erinnert', True, (200, 170, 130))
        self.screen.blit(head, (x + 30, cy))
        cy += 24
        # 2-Spalten-Layout
        col1_x = x + 30
        col2_x = x + w // 2 + 10
        col_w = (w - 80) // 2
        col_y0 = cy
        # 15 Einträge gleichmäßig auf 2 Spalten verteilen
        # Update #133 (Z-07): Jeder Eintrag bekommt eine Progress-Bar
        # + „cur/target"-Label.  Row-Höhe von 40 → 48 erhöht.
        stats = getattr(self, 'stats', {}) or {}
        stats['level'] = self.player.level  # Live-Wert für Level-Achievements
        for i, a in enumerate(_ach.ACHIEVEMENTS):
            col = i % 2
            row = i // 2
            sx = col1_x if col == 0 else col2_x
            sy = col_y0 + row * 48
            is_done = a['id'] in done
            color_name = (243, 213, 114) if is_done else (140, 120, 100)
            color_desc = (200, 180, 140) if is_done else (110, 100,  80)
            mark = '✓' if is_done else '○'
            ts = self.font_small.render(
                f'{mark}  {a["name"]}', True, color_name)
            self.screen.blit(ts, (sx, sy))
            ds = self.font_small.render(
                a['desc'], True, color_desc)
            self.screen.blit(ds, (sx + 18, sy + 16))
            # Belohnung rechts
            rs = self.font_small.render(
                f'+{a["reward"]}g',
                True, (140, 220, 140) if is_done else (90, 110, 90))
            self.screen.blit(rs,
                              (sx + col_w - rs.get_width(), sy + 4))
            # Update #133 (Z-07): Progress-Bar unter dem Desc.
            cur, tgt = _ach.progress_for(a, stats)
            bar_x = sx + 18
            bar_y = sy + 34
            bar_w = col_w - 60
            bar_h = 4
            pygame.draw.rect(self.screen, (40, 32, 24),
                              (bar_x, bar_y, bar_w, bar_h))
            fill_norm = cur / max(1, tgt)
            fill_w = int(bar_w * fill_norm)
            fill_col = ((140, 220, 140) if is_done
                         else (200, 170, 110))
            pygame.draw.rect(self.screen, fill_col,
                              (bar_x, bar_y, max(1, fill_w), bar_h))
            pygame.draw.rect(self.screen, (80, 70, 50),
                              (bar_x, bar_y, bar_w, bar_h), 1)
            # cur/target rechts
            prog_lbl = self.font_small.render(
                f'{cur}/{tgt}',
                True, (180, 180, 140) if is_done else (130, 120, 100))
            self.screen.blit(prog_lbl,
                              (sx + col_w - prog_lbl.get_width(),
                               sy + 26))

    def _draw_codex_aspects(self, x, y, w, h, top):
        """Die Sieben Aspekte — Lore-Bibel Teil 2."""
        from . import quotes as _q
        cy = top
        # Intro-Text
        intro = self.font_small.render(
            '„Aithein dachte — und der Gedanke war eine Welt." — '
            'Sieben Atemzüge, sieben Aspekte.', True, TEXT_DIM)
        self.screen.blit(intro, (x + 30, cy))
        cy += 24
        for asp in _q.ASPECTS:
            name = asp['name']
            domain = asp['domain']
            status = asp['status']
            note = asp['note']
            col = asp['color']
            # Aspekt-Header
            head = self.font_small.render(
                f'★ {name} — {domain}', True, col)
            self.screen.blit(head, (x + 30, cy))
            cy += 18
            # Status-Sub
            stat = self.font_small.render(f'   {status}', True, TEXT)
            self.screen.blit(stat, (x + 30, cy))
            cy += 16
            # Note
            n = self.font_small.render(f'   „{note}"', True, (180, 160, 130))
            self.screen.blit(n, (x + 30, cy))
            cy += 22

        log = getattr(self, 'quest_log', None)
        col1_x = x + 20
        col2_x = x + w // 2 + 10
        col_top = y + 80

        # Bestiarium-Entdeckungen
        head1 = self.font_med.render('Bestiarium', True, GOLD_BRIGHT)
        self.screen.blit(head1, (col1_x, col_top))
        cy1 = col_top + 28
        from . import bestiary as _best
        if log is not None and log.bestiary_seen:
            for key in sorted(log.bestiary_seen):
                entry = _best.BESTIARY.get(key, {})
                name = entry.get('display_name', key)
                ts = self.font_small.render(f'• {name}', True, TEXT)
                self.screen.blit(ts, (col1_x + 8, cy1))
                cy1 += 18
                # Lore-Quote in kursiv (kleiner)
                quote = entry.get('lore_quote', '')
                if quote:
                    qparts = self._wrap_codex(quote, 40)
                    for line in qparts[:3]:
                        qs = self.font_small.render(f'   „{line}"', True,
                                                     (180, 160, 130))
                        self.screen.blit(qs, (col1_x + 8, cy1))
                        cy1 += 15
                cy1 += 4
                if cy1 > y + h - 60:
                    break
        else:
            ts = self.font_small.render(
                'Noch keine Wesen entdeckt.', True, TEXT_DIM)
            self.screen.blit(ts, (col1_x + 8, cy1))

        # Lore-Tafel-Discoveries
        head2 = self.font_med.render('Gefundene Lore-Tafeln', True, GOLD_BRIGHT)
        self.screen.blit(head2, (col2_x, col_top))
        cy2 = col_top + 28
        if log is not None and log.discovered_lore:
            for text in list(log.discovered_lore)[:8]:
                parts = self._wrap_codex(text, 42)
                for line in parts:
                    ls = self.font_small.render(f'„{line}"', True,
                                                 (215, 200, 175))
                    self.screen.blit(ls, (col2_x + 8, cy2))
                    cy2 += 16
                cy2 += 6
                if cy2 > y + h - 40:
                    break
        else:
            ts = self.font_small.render(
                'Noch keine Lore-Tafeln gelesen.', True, TEXT_DIM)
            self.screen.blit(ts, (col2_x + 8, cy2))

    def _wrap_codex(self, text, max_chars):
        words = text.split(' ')
        lines = []
        cur = ''
        for w in words:
            if len(cur) + len(w) + 1 > max_chars and cur:
                lines.append(cur)
                cur = w
            else:
                cur = (cur + ' ' + w) if cur else w
        if cur:
            lines.append(cur)
        return lines

    def _draw_quest_board_section(self, x, y, w, h, cy, log):
        """Update #156 (ROADMAP T2.3): Quest-Board-Sektion im QuestLog-
        Modal.  Listet alle Velgrad-Quests die nicht aktiv UND nicht
        completed sind — gruppiert in 2 Sektionen (Verfügbar / Gelockt).

        Pro Quest-Zeile: Titel, Giver, Region, Stage-Count, Gold/XP.
        Hidden-Quests (giver=None, noch nicht entdeckt) werden NICHT
        gelistet — sie sollen versteckt bleiben bis Discovery.

        Returnt new cy (Y-Cursor nach der Sektion).
        """
        from . import quest_data as _qd
        head = self.font_med.render('Quest-Board', True, GOLD_BRIGHT)
        self.screen.blit(head, (x + 20, cy)); cy += 26
        available = []
        locked = []
        for q in _qd.ALL_QUESTS:
            qid = q['id']
            if qid in log.active or qid in log.completed:
                continue
            # Hidden-Quests mit Discovery-Trigger: nicht im Board zeigen
            if q.get('discover_via_interact') is not None:
                continue
            # Quests ohne NPC-Giver (außer Hidden) sind auto-quests —
            # zeigen wir nicht als „verfügbar" (gibt keinen NPC-Anker).
            if q.get('giver') is None:
                continue
            if log._quest_prerequisite_met(q, self.player):
                available.append(q)
            else:
                locked.append(q)
        if not available and not locked:
            ls = self.font_small.render(
                'Keine offenen Quests — alles gemeldet.', True, TEXT_DIM)
            self.screen.blit(ls, (x + 30, cy)); cy += 22
            cy += 12
            return cy
        # Render limit (Modal-Höhe begrenzt)
        line_budget = max(2, (y + h - cy - 240) // 36)
        if line_budget < 1:
            cy += 12
            return cy
        if available:
            sub = self.font_small.render(
                f'Verfügbar ({len(available)})', True, (180, 220, 140))
            self.screen.blit(sub, (x + 30, cy)); cy += 18
            for q in available[:line_budget]:
                marker = '★' if q.get('is_main') else '•'
                col_t = (255, 220, 100) if q.get('is_main') \
                        else (220, 200, 150)
                title_t = self.font_small.render(
                    f' {marker} {q["title"]}', True, col_t)
                self.screen.blit(title_t, (x + 40, cy)); cy += 16
                meta = (f'   Giver: {q["giver"]} · {q.get("region", "?")}')
                ms = self.font_small.render(meta, True, TEXT_DIM)
                self.screen.blit(ms, (x + 40, cy)); cy += 14
                rwd = q.get('reward') or {}
                rwd_s = (f'   Reward: {rwd.get("gold", 0)} Gold, '
                         f'{rwd.get("xp", 0)} XP')
                if rwd.get('item'):
                    rwd_s += f' + {rwd["item"]}'
                rs = self.font_small.render(rwd_s, True, (180, 180, 140))
                self.screen.blit(rs, (x + 40, cy)); cy += 18
            remain = len(available) - line_budget
            if remain > 0:
                more = self.font_small.render(
                    f'   … +{remain} weitere', True, TEXT_DIM)
                self.screen.blit(more, (x + 40, cy)); cy += 18
        if locked and (y + h - cy) > 140:
            sub = self.font_small.render(
                f'Gelockt ({len(locked)})', True, (180, 140, 90))
            self.screen.blit(sub, (x + 30, cy)); cy += 18
            # Nur top 3 gelocktes zeigen
            for q in locked[:3]:
                marker = '★' if q.get('is_main') else '•'
                title_t = self.font_small.render(
                    f' 🔒 {marker} {q["title"]} — {q.get("region", "?")}',
                    True, (160, 130, 100))
                self.screen.blit(title_t, (x + 40, cy)); cy += 16
            remain = len(locked) - 3
            if remain > 0:
                more = self.font_small.render(
                    f'   … +{remain} weitere', True, TEXT_DIM)
                self.screen.blit(more, (x + 40, cy)); cy += 16
        cy += 12
        return cy

    def _draw_questlog_modal(self):
        """Quest-Log: Velgrad-Storyquests + Dungeon-Objectives + erledigte.
        Update #30: Velgrad-Tome-Style.
        """
        from . import aspects as _asp
        pal = _asp.aspect_palette(self.player.cls)
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 210))
        self.screen.blit(overlay, (0, 0))
        w, h = 780, 580
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        # Pergament
        page = pygame.Surface((w, h), pygame.SRCALPHA)
        for py in range(h):
            t = py / max(1, h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (w, py))
        self.screen.blit(page, (x, y))
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, (x, y, w, h), 2)
        pygame.draw.rect(self.screen, pal['deep'],
                          (x + 4, y + 4, w - 8, h - 8), 1)
        _asp.draw_filigree_corners(
            self.screen, pygame.Rect(x, y, w, h), bronze, size=24)
        _asp.draw_aspect_watermark(
            self.screen, pygame.Rect(x, y, w, h),
            self.player.cls, alpha=18)
        # Header
        eyebrow = self.font_small.render(
            '— LIBER QUAESTI —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (x + w // 2 - eyebrow.get_width() // 2, y + 14))
        title_text = 'D A S   Q U E S T - L O G'
        title = self.font_med.render(title_text, True, pal['halo'])
        title_sh = self.font_med.render(title_text, True, (10, 6, 4))
        self.screen.blit(title_sh,
                          (x + w // 2 - title.get_width() // 2 + 1,
                           y + 33))
        self.screen.blit(title,
                          (x + w // 2 - title.get_width() // 2,
                           y + 32))
        hint = self.font_small.render(
            'J: Schließen · P: Quest pinnen', True, TEXT_DIM)
        self.screen.blit(hint,
                          (x + w - hint.get_width() - 20, y + 22))
        _asp.draw_ornament_divider(
            self.screen, x + 20, y + 64, w - 40, bronze)

        cy = y + 78

        # Velgrad-Story-Quests
        log = getattr(self, 'quest_log', None)
        if log is not None:
            head = self.font_med.render('Velgrad-Quests', True, GOLD_BRIGHT)
            self.screen.blit(head, (x + 20, cy)); cy += 28
            actives = log.all_active()
            if not actives:
                ls = self.font_small.render(
                    'Keine aktiven Velgrad-Quests.', True, TEXT_DIM)
                self.screen.blit(ls, (x + 30, cy)); cy += 22
            tracked_qid = getattr(log, 'tracked_quest_id', None)
            for qs in actives:
                marker = '★' if qs.is_main else '•'
                # Update #160 (T2.3-C): Pin-Marker für getrackte Quest
                is_tracked = (qs.quest['id'] == tracked_qid)
                pin = '📌 ' if is_tracked else ''
                col = (255, 240, 130) if is_tracked else (255, 220, 100)
                head_q = self.font_small.render(
                    f' {pin}{marker} {qs.title}', True, col)
                self.screen.blit(head_q, (x + 30, cy)); cy += 18
                reg = self.font_small.render(
                    f'    {qs.region}', True, TEXT_DIM)
                self.screen.blit(reg, (x + 30, cy)); cy += 16
                stage_t = self.font_small.render(
                    f'    → {qs.display_text()}', True, TEXT)
                self.screen.blit(stage_t, (x + 30, cy)); cy += 22
            if log.completed:
                done = self.font_small.render(
                    f'Abgeschlossen: {len(log.completed)} '
                    f'Velgrad-Quest(s)', True, (160, 200, 140))
                self.screen.blit(done, (x + 30, cy)); cy += 20
            cy += 12

            # Update #156 (ROADMAP T2.3): Quest-Board — Liste aller
            # noch nicht angenommenen Quests mit Status (AVAILABLE/
            # LOCKED), Giver, Region und kurzer Reward-Preview.
            cy = self._draw_quest_board_section(
                x, y, w, h, cy, log)

        # Aktiver Dungeon
        if self.active_quest:
            from .constants import DUNGEONS
            name = DUNGEONS[self.active_dungeon_id]['name']
            head = self.font_med.render(f'Aktuell: {name}', True, GOLD_BRIGHT)
            self.screen.blit(head, (x + 20, cy)); cy += 26
            for label, prog, target, done in self.active_quest.lines():
                icon = '☑' if done else '☐'
                col = (140, 220, 140) if done else TEXT
                ls = self.font_small.render(
                    f'  {icon} {label} ({prog}/{target})', True, col)
                self.screen.blit(ls, (x + 20, cy)); cy += 18
        else:
            ls = self.font_small.render(
                'Keine aktive Quest. Betrete einen Dungeon.', True, TEXT_DIM)
            self.screen.blit(ls, (x + 20, cy)); cy += 26
        # Abgeschlossene Dungeons
        cy += 16
        head2 = self.font_med.render('Abgeschlossen', True, GOLD_BRIGHT)
        self.screen.blit(head2, (x + 20, cy)); cy += 26
        from .constants import DUNGEONS
        if self.player.completed_dungeons:
            for did in self.player.completed_dungeons:
                tier = self.dungeon_tier.get(did, 1)
                tname = {1: 'Normal', 2: 'Heroisch', 3: 'Mythisch'}[tier]
                ls = self.font_small.render(
                    f'  ☑ {DUNGEONS[did]["name"]} — höchster Tier: {tname}',
                    True, (140, 220, 140))
                self.screen.blit(ls, (x + 20, cy)); cy += 18
        else:
            ls = self.font_small.render(
                'Noch keine Dungeons abgeschlossen.', True, TEXT_DIM)
            self.screen.blit(ls, (x + 20, cy)); cy += 18
        # Statistiken
        cy += 12
        head3 = self.font_med.render('Statistiken', True, GOLD_BRIGHT)
        self.screen.blit(head3, (x + 20, cy)); cy += 26
        for label, val in [
            ('Kills',         self.stats.get('kills', 0)),
            ('Bosse',         self.stats.get('bosses', 0)),
            ('Dungeons',      self.stats.get('dungeons', 0)),
            ('Gold gesamt',   self.stats.get('total_gold', 0)),
            ('Achievements',  f'{len(self.achievements_done)}/15'),
            ('Spielzeit',     f'{int(self.stats.get("time_played", 0))}s'),
        ]:
            ls = self.font_small.render(f'  {label}: {val}', True, TEXT)
            self.screen.blit(ls, (x + 20, cy)); cy += 16

    def _draw_buffs_bar(self):
        """Aktive Buffs/Debuffs als horizontale Icon-Leiste links OBEN."""
        from .constants import STATUS_EFFECTS
        p = self.player
        buffs = []
        if p.shield > 0:
            buffs.append(('Schild', (160, 200, 255), f'{int(p.shield)}'))
        if p.combo_buff_left > 0:
            buffs.append(('Combo', (255, 220, 100), f'{p.combo_buff_left:.1f}s'))
        if p.vampire_charges > 0:
            buffs.append(('Vampir', (220, 80, 80), f'×{p.vampire_charges}'))
        if p.regen_buff_left > 0:
            buffs.append(('Regen', (170, 255, 170), f'{p.regen_buff_left:.1f}s'))
        if p.levelup_invuln > 0:
            buffs.append(('Lvl', (255, 215, 90), f'{p.levelup_invuln:.1f}s'))
        if p.slow_factor < 1.0 and p.slow_timer > 0:
            buffs.append(('Slow', (140, 200, 255), f'{p.slow_timer:.1f}s'))
        for key, st in p.status.items():
            if key in STATUS_EFFECTS:
                spec = STATUS_EFFECTS[key]
                buffs.append((spec['label'][:6], spec['color'], f'×{st["stacks"]}'))
        if not buffs:
            return
        # Update #54: Player-Buffs (Schild/Combo/Vampir/Regen/Slow) UNTER
        # dem G-05 Status-Tray (das jetzt bei y=210 sitzt).  Vermeidet
        # Overlap mit Cartouche-Portrait und mit dem Status-Tray.
        # Vertikal statt horizontal stacken → kollidiert nicht mit
        # Top-Status-Bar wenn mehr als 4 Buffs aktiv.
        bx = 16
        # Count active status-effects to push buffs-bar below them
        from .constants import STATUS_EFFECTS as _SE
        status_count = sum(1 for k in p.status if k in _SE)
        by = 210 + status_count * 30  # nach buff_tray-Icons (sz=26+gap=4)
        # Update #54: Vertikale Spalte statt horizontaler Reihe — kollidiert
        # nicht mit Top-Status-Bar, wenn 5+ Buffs aktiv sind.
        for label, color, val in buffs[:8]:
            w = 110
            bg = pygame.Surface((w, 28), pygame.SRCALPHA)
            bg.fill((10, 8, 6, 210))
            self.screen.blit(bg, (bx, by))
            pygame.draw.rect(self.screen, color, (bx, by, w, 28), 1)
            pygame.draw.circle(self.screen, color, (bx + 10, by + 14), 4)
            ls = self.font_small.render(label, True, color)
            self.screen.blit(ls, (bx + 20, by + 2))
            vs = self.font_small.render(val, True, TEXT)
            self.screen.blit(vs, (bx + 20, by + 14))
            by += 28 + 4

    def _draw_aura_icon(self):
        """Aura-Anzeige rechts neben Mini-Map."""
        p = self.player
        if not p.aura:
            return
        from .constants import AURAS
        spec = AURAS[p.aura]
        x = SCREEN_W - 200 - 20  # neben Minimap
        y = 270  # unter Minimap
        w, h = 200, 44
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 220))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, GOLD, (x, y, w, h), 1)
        name = self.font_small.render(spec['name'], True, GOLD_BRIGHT)
        self.screen.blit(name, (x + 8, y + 4))
        # Mana-Reserve-Bar
        reserve = spec['reserve']
        reserve_text = self.font_small.render(
            f'-{int(reserve*100)}% Mana', True, MANA)
        self.screen.blit(reserve_text, (x + 8, y + 22))

    # ==========================================================
    # Update #133 (Z-01/Z-02): Multi-Save-Slot-Picker
    # ==========================================================
    def _slot_picker_rects(self):
        """Berechnet Rects für den Slot-Picker.  Returns dict mit
        rect/cards[3]/hardcore_toggle/cancel.
        """
        W, H = 720, 480
        x = SCREEN_W // 2 - W // 2
        y = SCREEN_H // 2 - H // 2
        rects = {
            'rect': pygame.Rect(x, y, W, H),
            'cards': [],
            'hardcore': pygame.Rect(x + 30, y + H - 100, 280, 36),
            'cancel':   pygame.Rect(x + W - 160, y + H - 60, 130, 36),
        }
        card_w = (W - 60 - 20) // 3
        for i in range(save_mod.MAX_SLOTS):
            rects['cards'].append(pygame.Rect(
                x + 30 + i * (card_w + 10),
                y + 90, card_w, H - 230))
        return rects

    def _handle_slot_picker_click(self, sx, sy):
        """Returns True wenn der Klick verarbeitet wurde."""
        r = self._slot_picker_rects()
        if not r['rect'].collidepoint(sx, sy):
            # Klick außerhalb → schließt Picker
            self._slot_picker_open = False
            return True
        # Cancel-Button
        if r['cancel'].collidepoint(sx, sy):
            self._slot_picker_open = False
            return True
        # Hardcore-Toggle (nur im 'new'-Mode)
        if (getattr(self, '_slot_picker_mode', 'new') == 'new'
                and r['hardcore'].collidepoint(sx, sy)):
            self._slot_picker_hardcore = not getattr(
                self, '_slot_picker_hardcore', False)
            return True
        # Slot-Cards
        summaries = save_mod.list_slot_summaries()
        for i, card in enumerate(r['cards']):
            if card.collidepoint(sx, sy):
                slot = i + 1
                summary = summaries[i]
                mode = getattr(self, '_slot_picker_mode', 'new')
                if mode == 'load':
                    if summary['exists']:
                        self._slot_picker_open = False
                        self.start_game('adventure', load=True, slot=slot)
                    return True
                # mode == 'new'
                if summary['exists']:
                    # Bereits belegt → kurzer Hinweis, kein Start
                    self.toast_queue.append([
                        f'Slot {slot} ist belegt. Lösche ihn zuerst oder '
                        f'wähle einen leeren Slot.',
                        (220, 150, 100), 4.0])
                    return True
                hc = bool(getattr(self, '_slot_picker_hardcore', False))
                self._slot_picker_open = False
                self.start_game('adventure', slot=slot, hardcore=hc,
                                persist_new=True)
                return True
        return False

    def _draw_slot_picker_overlay(self):
        """Update #133 (Z-01): Slot-Picker als Pergament-Overlay über dem
        Title-Screen.  Zeigt 3 Slot-Cards mit Status + Hardcore-Toggle
        (im New-Game-Mode) + Cancel-Button.
        """
        # Verdunklungs-Overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        r = self._slot_picker_rects()
        modal = r['rect']
        # Pergament-Hintergrund
        page = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        for py in range(modal.h):
            t = py / max(1, modal.h - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py),
                              (modal.w, py))
        self.screen.blit(page, modal.topleft)
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, modal, 2)
        # Titel
        mode = getattr(self, '_slot_picker_mode', 'new')
        if mode == 'load':
            title_text = 'SPIELSTAND LADEN'
        else:
            title_text = 'NEUER CHARAKTER'
        title = self.font_big.render(title_text, True, (220, 180, 110))
        self.screen.blit(title,
                          (modal.centerx - title.get_width() // 2,
                           modal.y + 18))
        # Slot-Cards
        from .constants import CLASSES
        summaries = save_mod.list_slot_summaries()
        mx, my = pygame.mouse.get_pos()
        for i, card in enumerate(r['cards']):
            s = summaries[i]
            hovered = card.collidepoint(mx, my)
            # Hintergrund
            bg_col = (30, 22, 12) if not hovered else (50, 36, 18)
            pygame.draw.rect(self.screen, bg_col, card)
            # Border-Color: Bronze-Default, Rot bei Hardcore
            border = (180, 70, 70) if s['hardcore'] else (180, 140, 80)
            pygame.draw.rect(self.screen, border, card, 2)
            # Slot-Header
            sh = self.font_med.render(f'Slot {s["slot"]}', True,
                                        (220, 200, 160))
            self.screen.blit(sh, (card.x + 14, card.y + 10))
            # Hardcore-Tag rechts oben
            if s['hardcore']:
                hc = self.font_small.render('HARDCORE', True,
                                              (240, 100, 100))
                self.screen.blit(hc, (card.right - hc.get_width() - 10,
                                       card.y + 14))
            # Inhalt
            cy = card.y + 50
            if not s['exists']:
                empty = self.font_med.render(
                    s.get('label', 'Leer'), True, (140, 120, 90))
                self.screen.blit(empty,
                                  (card.x + 14, cy + 80))
                hint_txt = ('Klicken um neuen Charakter '
                            'zu erstellen' if mode == 'new' else
                            'Slot leer')
                hint = self.font_small.render(hint_txt, True,
                                                (160, 140, 110))
                self.screen.blit(hint, (card.x + 14, cy + 110))
                continue
            # Existierender Slot
            cls_key = s['cls']
            cls_data = CLASSES.get(cls_key, {})
            cls_name = cls_data.get('name', cls_key)
            cls_col = cls_data.get('color', (220, 200, 160))
            # Klasse + Stufe
            cl = self.font_med.render(
                f'{cls_name}  Stufe {s["level"]}', True, cls_col)
            self.screen.blit(cl, (card.x + 14, cy))
            cy += cl.get_height() + 6
            # Akt-Progress
            akt_line = self.font_small.render(
                f'Akt {s["akt"]}  ·  {s["gold"]} Gold',
                True, (200, 180, 140))
            self.screen.blit(akt_line, (card.x + 14, cy))
            cy += akt_line.get_height() + 4
            # Spielzeit
            hours = s['time_played_h']
            time_str = (f'{hours:.1f} h gespielt' if hours >= 0.1 else
                         '< 0.1 h gespielt')
            ts = self.font_small.render(time_str, True, (180, 160, 130))
            self.screen.blit(ts, (card.x + 14, cy))
            cy += ts.get_height() + 4
            # Letztes Spiel (UTC)
            import time as _t
            if s['last_played_ts'] > 0:
                lp = _t.strftime('%Y-%m-%d %H:%M',
                                  _t.localtime(s['last_played_ts']))
                lps = self.font_small.render(lp, True, (160, 140, 110))
                self.screen.blit(lps, (card.x + 14, cy))
            cy += 30
            # Action-Hint
            if mode == 'load':
                action = 'Klicken zum Laden'
            else:
                action = 'Slot belegt — leeren wählen'
            ac = self.font_small.render(action, True, (200, 180, 130))
            self.screen.blit(ac, (card.x + 14, card.bottom - 28))
        # Hardcore-Toggle (nur New-Mode)
        if mode == 'new':
            ht = r['hardcore']
            hot = getattr(self, '_slot_picker_hardcore', False)
            tog_col = (200, 80, 80) if hot else (140, 120, 90)
            tog_hover = ht.collidepoint(mx, my)
            bg_t = (50, 24, 18) if hot else (30, 24, 16)
            if tog_hover:
                bg_t = tuple(min(255, c + 20) for c in bg_t)
            pygame.draw.rect(self.screen, bg_t, ht)
            pygame.draw.rect(self.screen, tog_col, ht, 2)
            box_r = pygame.Rect(ht.x + 8, ht.y + 8, 20, 20)
            pygame.draw.rect(self.screen, (12, 8, 4), box_r)
            pygame.draw.rect(self.screen, tog_col, box_r, 2)
            if hot:
                # X-Markierung
                pygame.draw.line(self.screen, tog_col,
                                  (box_r.x + 4, box_r.y + 4),
                                  (box_r.right - 4, box_r.bottom - 4), 3)
                pygame.draw.line(self.screen, tog_col,
                                  (box_r.x + 4, box_r.bottom - 4),
                                  (box_r.right - 4, box_r.y + 4), 3)
            lbl = self.font_small.render(
                'Hardcore — Permadeath, Slot wird beim Tod gelöscht',
                True, tog_col)
            self.screen.blit(lbl, (ht.x + 36, ht.y + 10))
        # Cancel-Button
        cancel = r['cancel']
        cnc_hover = cancel.collidepoint(mx, my)
        cnc_bg = (50, 36, 18) if cnc_hover else (30, 22, 12)
        pygame.draw.rect(self.screen, cnc_bg, cancel)
        pygame.draw.rect(self.screen, bronze, cancel, 2)
        cnc_lbl = self.font_small.render('Abbrechen [ESC]', True,
                                           (220, 200, 160))
        self.screen.blit(cnc_lbl, cnc_lbl.get_rect(center=cancel.center))

    def _draw_region_transition(self):
        """Update #132 (B-18): Lower-Third-Animation beim Map-Wechsel.

        Zeigt 1.6 s lang einen breiten Banner unten am Bildschirm mit
        Region-Name (groß) + Akt-Sub (klein) + Aspekt-Akzent-Farbe als
        Banner-Border.  Fade-In über 0.3 s, Hold 1.0 s, Fade-Out 0.3 s.
        """
        rt = self.region_transition
        if rt is None:
            return
        # Lerp-Alpha aus t / total
        t = float(rt['t'])
        total = float(rt['total'])
        elapsed = total - t
        if elapsed < 0.3:
            alpha = elapsed / 0.3
        elif t < 0.3:
            alpha = t / 0.3
        else:
            alpha = 1.0
        alpha = max(0.0, min(1.0, alpha))
        # Banner-Geometrie: untere 80 px, volle Bildschirmbreite
        banner_h = 90
        banner_y = SCREEN_H - 200
        color = rt['color']
        # Hintergrund mit Gradient
        bg = pygame.Surface((SCREEN_W, banner_h), pygame.SRCALPHA)
        for hy in range(banner_h):
            tt = hy / max(1, banner_h - 1)
            edge_fade = abs(tt - 0.5) * 2.0
            base_a = int((1.0 - edge_fade * 0.3) * 200 * alpha)
            pygame.draw.line(bg, (12, 8, 4, base_a),
                              (0, hy), (SCREEN_W, hy))
        self.screen.blit(bg, (0, banner_y))
        # Akzent-Linien oben + unten
        accent_a = int(220 * alpha)
        pygame.draw.line(self.screen,
                          (*color, accent_a) if False else color,
                          (40, banner_y), (SCREEN_W - 40, banner_y), 2)
        pygame.draw.line(self.screen, color,
                          (40, banner_y + banner_h - 2),
                          (SCREEN_W - 40, banner_y + banner_h - 2), 2)
        # Region-Name (groß, zentriert)
        font_title = getattr(self, 'font_big', self.font_med)
        title_surf = font_title.render(rt['name'], True, color)
        title_surf.set_alpha(int(255 * alpha))
        self.screen.blit(title_surf,
                          (SCREEN_W // 2 - title_surf.get_width() // 2,
                           banner_y + 18))
        # Sub (klein)
        sub = rt.get('sub', '')
        if sub:
            sub_surf = self.font_small.render(sub, True, (220, 210, 180))
            sub_surf.set_alpha(int(220 * alpha))
            self.screen.blit(sub_surf,
                              (SCREEN_W // 2 - sub_surf.get_width() // 2,
                               banner_y + 18 + title_surf.get_height() + 2))
        # Update #139 (X-11): Lore-Loading-Card als zusätzliches Overlay
        # OBEN am Bildschirm bei Dungeon-Entry (zusätzlich zum Bottom-
        # Banner).  Zeigt Klassen-Sigil + Lore-Quote + Tip.
        card = rt.get('loading_card')
        if card is not None:
            self._draw_lore_loading_card(card, alpha)

    def _draw_debug_overlay(self):
        """Update #139 (AA-01): Debug-Overlay (F3-Toggle).

        Zeigt FPS, ms/frame, Particle-/Mob-/Projectile-Count, Player-Pos,
        AI-LOD-Stats, current biome, music-snapshot, render-Mode.  Dezent
        oben-rechts, monospace-Style.

        Aktiv via `self._debug_overlay = True` (F3).  Render-Pass läuft
        IMMER (auch in Title/Dead), damit der User die Stats sieht.
        """
        if not getattr(self, '_debug_overlay', False):
            return
        font = getattr(self, 'font_small', None)
        if font is None:
            return
        # FPS via clock
        try:
            fps = int(self.clock.get_fps())
        except Exception:
            fps = 0
        # Counts
        n_part = len(getattr(self, 'particles', []))
        n_mob = len(getattr(self, 'enemies', []))
        n_proj = len(getattr(self, 'projectiles', []))
        n_loot = len(getattr(self, 'loot', []))
        n_floaters = len(getattr(self, 'floaters', []))
        n_blood = len(getattr(self, 'blood_pools', []))
        n_foot = len(getattr(self, 'footprints', []))
        # Player + State
        p = getattr(self, 'player', None)
        if p is not None:
            px = int(p.pos.x); py = int(p.pos.y)
            pcls = getattr(p, 'cls', '?')
            plvl = getattr(p, 'level', '?')
            php = int(getattr(p, 'hp', 0))
        else:
            px = py = 0; pcls = '?'; plvl = '?'; php = 0
        # AI-LOD
        ai_active = sum(
            1 for e in getattr(self, 'enemies', [])
            if getattr(e, 'ai_state', None) is not None)
        # Render-Mode + Music
        rscale = self.settings.get('render_scale', 1.0)
        # Lines
        lines = [
            f'FPS: {fps}',
            f'Particles: {n_part}',
            f'Mobs: {n_mob} (AI-active: {ai_active})',
            f'Projectiles: {n_proj}',
            f'Loot: {n_loot} | Floaters: {n_floaters}',
            f'Blood/Footprints: {n_blood}/{n_foot}',
            f'Player: {pcls} L{plvl} HP={php}',
            f'  pos=({px}, {py})',
            f'Area: {getattr(self, "area", "?")}',
            f'Biome: {getattr(self, "biome", "?")}',
            f'Modal: {getattr(self, "modal", "None") or "None"}',
            f'State: {getattr(self, "state", "?")}',
            f'Render-Scale: {rscale}',
            f'Hardcore: {getattr(self, "hardcore", False)}',
            f'F3=Toggle  F8=Restore  F12=BugReport',
        ]
        # Audit #179 C.13: Frame-Time-Sections (avg ms ueber 60 Frames).
        try:
            frame_summary = _profiler_mod.frame_summary()
            if frame_summary:
                lines.append('-- Frame-Time --')
                for sec, ms in list(frame_summary.items())[:5]:
                    lines.append(f'  {sec}: {ms:.2f} ms')
        except Exception:
            pass
        line_h = font.get_height() + 1
        box_w = 280
        box_h = len(lines) * line_h + 12
        x = SCREEN_W - box_w - 12
        y = SCREEN_H - box_h - 12
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((6, 4, 2, 200))
        self.screen.blit(bg, (x, y))
        pygame.draw.rect(self.screen, (90, 220, 130), (x, y, box_w, box_h), 1)
        # Header
        cy = y + 6
        for line in lines:
            col = (130, 240, 170) if line.startswith('FPS') \
                else (220, 220, 200)
            ls = font.render(line, True, col)
            self.screen.blit(ls, (x + 8, cy))
            cy += line_h

    def _try_apply_crash_recovery(self):
        """Audit #179 C.8: F8 → Autosave-Recovery anwenden.

        Wird gerufen wenn der User F8 drueckt und ein pending Autosave
        vorhanden ist. Zeigt Toasts fuer Erfolg/Fehler. Konsumiert den
        Pending-Marker, damit der Hint-Toast nicht weiter erscheint.
        """
        rec = getattr(self, 'pending_autosave_recovery', None)
        if rec is None:
            self.toast('Kein Autosave-Recovery verfügbar.',
                       (200, 184, 136))
            return
        try:
            ok = save_mod.apply_autosave_recovery(self)
        except Exception:
            ok = False
        if ok:
            self.toast(
                f'✓ Autosave (Slot {rec["slot"]}) wiederhergestellt.',
                (140, 220, 140))
        else:
            self.toast('⚠ Autosave-Recovery fehlgeschlagen.',
                       (220, 150, 100))
        self.pending_autosave_recovery = None

    def _write_bug_report(self):
        """Update #139 (AA-09): F12 → Bug-Report-Snapshot.

        Schreibt nach `bugreports/<timestamp>/`:
          - screenshot.png      (PNG des aktuellen Frames)
          - state.txt           (Game-Snapshot + last events)
          - save_snapshot.json  (Kopie des aktuellen Slot-Saves)

        Failt silently bei OS-Fehlern (Bug-Report darf nie crashen).
        """
        import time as _t
        import shutil as _sh
        import json as _json
        from pathlib import Path
        from . import crash_logger as _crash
        from . import save as _save
        ts = _t.strftime('%Y%m%d_%H%M%S')
        try:
            dir_ = Path('bugreports') / f'report_{ts}'
            dir_.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.toast('Bug-Report fehlgeschlagen (kein Schreibrecht).',
                       (220, 130, 80))
            return
        # 1. Screenshot via pygame.image.save
        try:
            pygame.image.save(self.screen, str(dir_ / 'screenshot.png'))
        except Exception:
            pass
        # 2. State-Snapshot via crash_logger-Helper
        try:
            with (dir_ / 'state.txt').open('w', encoding='utf-8') as f:
                f.write(f'Shadowfall — Bug-Report\n')
                f.write(f'Timestamp: {_t.strftime("%Y-%m-%d %H:%M:%S")}\n')
                f.write(f'SAVE_VERSION: {_save.SAVE_VERSION}\n\n')
                f.write('Game-State:\n')
                # Re-use crash_logger snapshot via direct call
                _crash._game_ref = self
                f.write(_crash._game_snapshot())
                f.write('\n\nRecent events:\n')
                for ev in _crash._recent_events:
                    f.write('  ' + ev + '\n')
        except Exception:
            pass
        # 3. Save-Snapshot (Copy aktueller Slot)
        try:
            slot = _save.get_active_slot()
            sp = _save.slot_path(slot)
            if sp.exists():
                _sh.copy(sp, dir_ / 'save_snapshot.json')
        except Exception:
            pass
        # User-Feedback
        self.toast(f'Bug-Report → {dir_}',
                    (140, 220, 140))
        self.push_event_log(f'Bug-Report gespeichert: {dir_.name}',
                              (140, 220, 140), duration=6.0)

    def _draw_lore_loading_card(self, card, alpha):
        """Update #139 (X-11): Rendert die Lore-Loading-Card oben am
        Bildschirm während der Region-Transition.

        Layout (zentriert, 560×180 px, y=130):
          - Klassen-Aspekt-Sigil links (40×40 Hexagon mit Glyph)
          - Quote (mittig, kursiv-Look via italic-color)
          - „TIP: …"-Zeile unten (gold, font_small)
        """
        from . import aspects as _asp
        cls = card.get('cls') or 'warrior'
        tip = card.get('tip')
        quote = card.get('quote')
        # Modal-Rect
        W, H = 580, 170
        x = SCREEN_W // 2 - W // 2
        y = 130
        # Pergament-Background mit Alpha
        bg = pygame.Surface((W, H), pygame.SRCALPHA)
        for py in range(H):
            t = py / max(1, H - 1)
            rr = int(36 + (24 - 36) * t)
            gg = int(28 + (20 - 28) * t)
            bb = int(18 + (14 - 18) * t)
            pygame.draw.line(bg, (rr, gg, bb, int(220 * alpha)),
                              (0, py), (W, py))
        self.screen.blit(bg, (x, y))
        # Bronze-Border
        bronze = (154, 118, 66)
        bronze_alpha = (*bronze, int(255 * alpha))
        border = pygame.Surface((W, H), pygame.SRCALPHA)
        pygame.draw.rect(border, bronze_alpha,
                          (0, 0, W, H), 2)
        self.screen.blit(border, (x, y))
        # Aspekt-Sigil + Klassen-Hexagon links
        aspect_key = _asp.aspect_for_class(cls)
        pal = _asp.aspect_palette(aspect_key)
        sig_cx = x + 50
        sig_cy = y + H // 2
        # Hexagon-Rahmen
        hex_pts = []
        for k in range(6):
            ang = -math.pi / 2 + k * (math.pi / 3)
            hex_pts.append((sig_cx + math.cos(ang) * 28,
                             sig_cy + math.sin(ang) * 28))
        hex_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
        hex_pts_local = [(p[0] - sig_cx + 45, p[1] - sig_cy + 45)
                          for p in hex_pts]
        # Hex-Fill
        a_int = int(255 * alpha)
        pygame.draw.polygon(hex_surf, (16, 12, 8, a_int),
                              hex_pts_local)
        pygame.draw.polygon(hex_surf,
                              (*pal['primary'], a_int),
                              hex_pts_local, 2)
        self.screen.blit(hex_surf, (sig_cx - 45, sig_cy - 45))
        # Aspekt-Glyph in der Mitte
        _asp.draw_glyph(self.screen, sig_cx, sig_cy, 32,
                          aspect_key, color=pal['bright'])
        # Quote (rechts vom Sigil)
        quote_x = x + 110
        quote_y = y + 18
        font_small = self.font_small
        if quote:
            # Soft-wrap auf ~60 Zeichen pro Zeile
            words = quote.split(' ')
            lines = []
            cur = ''
            for w in words:
                tent = (cur + ' ' + w).strip()
                if len(tent) > 60 and cur:
                    lines.append(cur)
                    cur = w
                else:
                    cur = tent
            if cur:
                lines.append(cur)
            for line in lines[:3]:
                ls = font_small.render(f'„{line}"', True,
                                         (220, 200, 170))
                ls.set_alpha(int(220 * alpha))
                self.screen.blit(ls, (quote_x, quote_y))
                quote_y += ls.get_height() + 2
        # Tip-Zeile unten am Card
        if tip:
            tip_y = y + H - 28
            # Tip-Header
            th = font_small.render('TIP', True, (240, 200, 100))
            th.set_alpha(int(255 * alpha))
            self.screen.blit(th, (quote_x, tip_y))
            # Tip-Text — wrap auf 70 Zeichen
            words = tip.split(' ')
            tip_lines = []
            cur = ''
            for w in words:
                tent = (cur + ' ' + w).strip()
                if len(tent) > 70 and cur:
                    tip_lines.append(cur)
                    cur = w
                else:
                    cur = tent
            if cur:
                tip_lines.append(cur)
            tip_text = tip_lines[0] if tip_lines else ''
            if len(tip_lines) > 1:
                tip_text = tip_text + ' …'
            tt = font_small.render(tip_text, True, (220, 210, 180))
            tt.set_alpha(int(230 * alpha))
            self.screen.blit(tt, (quote_x + 38, tip_y))

    def _draw_tutorial_overlay(self):
        """Update #131 (Y-01): Zeigt das aktuelle First-Run-Tutorial-Panel.

        Zentriertes Lore-Banner über der Stadt mit Titel + Body + Hint
        für ENTER/ESC.  Wird nur gerendert wenn `tutorial.is_active()`.
        """
        from . import tutorial as _tut
        if not _tut.is_active(self):
            return
        step = _tut.current_step(self.player)
        if step is None:
            return
        # Panel-Layout
        W = 540
        font_title = getattr(self, 'font_med', None)
        font_body = getattr(self, 'font_small', None)
        if font_title is None or font_body is None:
            return
        # Body soft-wrappen auf ~64 Zeichen pro Zeile
        body_lines = []
        words = step['body'].split(' ')
        current = ''
        for w in words:
            tentative = (current + ' ' + w).strip()
            if len(tentative) > 64 and current:
                body_lines.append(current)
                current = w
            else:
                current = tentative
        if current:
            body_lines.append(current)
        # Höhe abschätzen
        title_h = font_title.get_height()
        body_h = font_body.get_height()
        line_gap = 4
        pad = 16
        hint_h = font_body.get_height()
        total_h = (pad + title_h + 8 + len(body_lines) * (body_h + line_gap)
                   + 10 + hint_h + pad)
        # Position: oberes Drittel
        px = (SCREEN_W - W) // 2
        py = 110
        # Hintergrund (Pergament-dunkel + Gold-Border)
        bg = pygame.Surface((W, total_h), pygame.SRCALPHA)
        bg.fill((18, 14, 10, 230))
        pygame.draw.rect(bg, (200, 160, 90), bg.get_rect(), 2)
        pygame.draw.rect(bg, (60, 44, 28), (1, 1, W - 2, total_h - 2), 1)
        self.screen.blit(bg, (px, py))
        # Schritt-Counter (oben rechts)
        cnt_txt = f'{int(self.player.tutorial_step) + 1} / {len(_tut.TUTORIAL_STEPS)}'
        cnt_surf = font_body.render(cnt_txt, True, (180, 150, 100))
        self.screen.blit(cnt_surf,
                          (px + W - cnt_surf.get_width() - pad,
                           py + pad - 2))
        # Titel
        title_surf = font_title.render(step['title'], True, (240, 220, 170))
        self.screen.blit(title_surf, (px + pad, py + pad - 2))
        # Body
        y = py + pad + title_h + 8
        for line in body_lines:
            surf = font_body.render(line, True, (220, 210, 180))
            self.screen.blit(surf, (px + pad, y))
            y += body_h + line_gap
        # Hint-Zeile (pulsing)
        puls = abs(math.sin(pygame.time.get_ticks() * 0.004))
        hint_col = (int(180 + 40 * puls), int(150 + 40 * puls), 80)
        hint = font_body.render(
            '[ENTER] Weiter   ·   [ESC] Tutorial überspringen',
            True, hint_col)
        self.screen.blit(hint,
                          (px + W // 2 - hint.get_width() // 2,
                           py + total_h - pad - hint_h + 2))

    def _draw_toasts(self):
        """Toast-Stack — Update #36: max 3 sichtbar, kleinere Schrift.

        Update #149 (User-Report „Schriften gehen aus Boxen"): Soft-Wrap
        auf max 600 px Breite.  Lange Voice-Quotes + NPC-Lines passten
        vorher nicht in eine Zeile und überspülten die Box-Border.
        """
        if not self.toast_queue:
            return
        MAX_VISIBLE = 3
        MAX_WIDTH = 600   # Maximale Box-Breite in Pixel
        visible = self.toast_queue[-MAX_VISIBLE:]
        # User-Fix („untere UI ueberlappt"): Toast-Stack ueber den gesamten
        # Bottom-HUD-Cluster (Spirit-Bar ~ -182, Globes, Hotbar -150) heben,
        # damit Toasts nie mehr ueber Hotbar/Globes liegen.
        y = SCREEN_H - 250
        for text, color, life in reversed(visible):
            alpha = min(1.0, life / 0.6) if life < 0.6 else 1.0
            # Soft-Wrap: zerlege text in Zeilen die in MAX_WIDTH passen
            font = self.font_small
            lines = self._wrap_text_to_width(text, font,
                                              MAX_WIDTH - 24)
            line_h = font.get_height() + 2
            box_w = min(MAX_WIDTH,
                         max(font.size(ln)[0] for ln in lines) + 24)
            box_h = len(lines) * line_h + 8
            bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            bg.fill((10, 8, 6, int(200 * alpha)))
            x = SCREEN_W // 2 - box_w // 2
            # Toast-Block stapelt nach OBEN → y muss nach Render
            # nach oben rücken um die volle Höhe der vorigen Box.
            self.screen.blit(bg, (x, y))
            pygame.draw.rect(self.screen, color,
                              (x, y, box_w, box_h), 1)
            cy = y + 4
            for ln in lines:
                s = font.render(ln, True, color)
                s.set_alpha(int(240 * alpha))
                self.screen.blit(s, (x + 12, cy))
                cy += line_h
            y -= box_h + 3

    def _wrap_text_to_width(self, text, font, max_w):
        """Update #149: Soft-Wrap helper.  Returnt Liste von Zeilen die
        in `max_w` Pixel passen.  Wraps an Wort-Grenzen.
        """
        words = text.split(' ')
        lines = []
        cur = ''
        for w in words:
            tentative = (cur + ' ' + w) if cur else w
            if font.size(tentative)[0] <= max_w:
                cur = tentative
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        if not lines:
            lines = [text]
        return lines

    def _draw_boss_intro(self):
        """Velgrad-Boss-Cinematic mit Letterbox + ornamentalen Linien.

        Update #33: Schwarze Bänder oben/unten (Cinematic-Bars),
        Bronze-Akzent-Linien, Blood-Banner-Mitte mit Name+Title+Quote.
        """
        intro = self.boss_intro
        t = intro['timer']
        if t > 2.5:
            a = (3.0 - t) / 0.5
        elif t < 0.6:
            a = t / 0.6
        else:
            a = 1.0
        a = max(0.0, min(1.0, a))
        alpha = int(255 * a)

        # Cinematic-Letterbox: schwarze Bänder oben + unten (80 px),
        # Höhe scaled mit alpha für sanften Slide-In.
        bar_h_max = 80
        bar_h = int(bar_h_max * a)
        if bar_h > 0:
            top = pygame.Surface((SCREEN_W, bar_h), pygame.SRCALPHA)
            top.fill((0, 0, 0, 235))
            self.screen.blit(top, (0, 0))
            bot = pygame.Surface((SCREEN_W, bar_h), pygame.SRCALPHA)
            bot.fill((0, 0, 0, 235))
            self.screen.blit(bot, (0, SCREEN_H - bar_h))
            # Bronze-Akzent-Linien am inneren Rand der Bänder
            pygame.draw.line(self.screen, (154, 118, 66),
                              (0, bar_h - 1),
                              (SCREEN_W, bar_h - 1), 2)
            pygame.draw.line(self.screen, (154, 118, 66),
                              (0, SCREEN_H - bar_h),
                              (SCREEN_W, SCREEN_H - bar_h), 2)
            # Pulsierender Akzent
            puls = abs(math.sin(pygame.time.get_ticks() * 0.005))
            pulse_alpha = int(60 * puls * a)
            if pulse_alpha > 0:
                glow_top = pygame.Surface((SCREEN_W, 6), pygame.SRCALPHA)
                glow_top.fill((227, 180, 64, pulse_alpha))
                self.screen.blit(glow_top, (0, bar_h - 4))
                self.screen.blit(glow_top, (0, SCREEN_H - bar_h - 2))

        # Mittel-Banner (dunkel, mit Blood-Akzent)
        bh = 130
        bg = pygame.Surface((SCREEN_W, bh), pygame.SRCALPHA)
        bg.fill((10, 4, 4, int(180 * a)))
        self.screen.blit(bg, (0, SCREEN_H // 2 - bh // 2))
        pygame.draw.line(self.screen, (216, 56, 56),
                         (0, SCREEN_H // 2 - bh // 2),
                         (SCREEN_W, SCREEN_H // 2 - bh // 2), 2)
        pygame.draw.line(self.screen, (216, 56, 56),
                         (0, SCREEN_H // 2 + bh // 2),
                         (SCREEN_W, SCREEN_H // 2 + bh // 2), 2)
        # Subtile Bronze-Linien innen (Memorial-Style)
        pygame.draw.line(self.screen, (154, 118, 66),
                         (60, SCREEN_H // 2 - bh // 2 + 4),
                         (SCREEN_W - 60, SCREEN_H // 2 - bh // 2 + 4), 1)
        pygame.draw.line(self.screen, (154, 118, 66),
                         (60, SCREEN_H // 2 + bh // 2 - 4),
                         (SCREEN_W - 60, SCREEN_H // 2 + bh // 2 - 4), 1)

        # Eyebrow oben: BOSS-WARNUNG
        eyebrow_text = '— A N O M A L I E   E R K A N N T —'
        eb = self.font_small.render(eyebrow_text, True, (220, 180, 110))
        eb.set_alpha(alpha)
        self.screen.blit(eb, eb.get_rect(
            center=(SCREEN_W // 2, SCREEN_H // 2 - 50)))
        # Name (groß, mit Glow-Stack)
        name_text = intro['name']
        for ox, oy, col in [(-2, 0, (140, 30, 30)),
                              (2, 0, (140, 30, 30)),
                              (0, -2, (60, 12, 12)),
                              (0, 2, (60, 12, 12))]:
            ns = self.font_big.render(name_text, True, col)
            ns.set_alpha(alpha)
            self.screen.blit(ns, ns.get_rect(
                center=(SCREEN_W // 2 + ox, SCREEN_H // 2 - 18 + oy)))
        name = self.font_big.render(name_text, True, (237, 224, 192))
        name.set_alpha(alpha)
        self.screen.blit(name, name.get_rect(
            center=(SCREEN_W // 2, SCREEN_H // 2 - 18)))
        # Title (Cinzel-Style sperrung)
        if intro['title']:
            title = self.font_med.render(intro['title'], True,
                                          (227, 180, 64))
            title.set_alpha(alpha)
            self.screen.blit(title, title.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2 + 26)))
        # Lore-Quote
        lore_q = intro.get('lore_quote')
        if lore_q:
            lq = self.font_small.render(f'„{lore_q}"', True,
                                          (200, 165, 110))
            lq.set_alpha(alpha)
            self.screen.blit(lq, lq.get_rect(
                center=(SCREEN_W // 2, SCREEN_H // 2 + 52)))
        # PLAN E-04: Skip-Hint nur bei wiederholten Encountern.
        try:
            from . import boss_encounter as _enc
            if _enc.is_skippable(self):
                hint_t = 'LEERTASTE halten zum Überspringen'
                hint_surf = self.font_small.render(hint_t, True,
                                                    (180, 180, 200))
                hint_surf.set_alpha(min(alpha, 200))
                self.screen.blit(hint_surf, hint_surf.get_rect(
                    center=(SCREEN_W // 2, SCREEN_H // 2 + 78)))
        except Exception:
            pass

    def _draw_completion_countdown(self):
        """Großer Banner unten zentriert: Dungeon abgeschlossen + Countdown."""
        secs = max(0, int(self._dungeon_done_timer) + 1)
        msg = f'Dungeon abgeschlossen · Rückkehr zur Stadt in {secs}s'
        sub = self.font_small.render('Beute jetzt einsammeln — Tasche aufmachen (I)',
                                      True, TEXT_DIM)
        main = self.font_med.render(msg, True, GOLD_BRIGHT)
        bw = max(main.get_width(), sub.get_width()) + 40
        bh = main.get_height() + sub.get_height() + 18
        bx = SCREEN_W // 2 - bw // 2
        by = SCREEN_H // 2 - bh - 40
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 220))
        self.screen.blit(bg, (bx, by))
        pygame.draw.rect(self.screen, GOLD, (bx, by, bw, bh), 2)
        self.screen.blit(main, (bx + (bw - main.get_width()) // 2, by + 8))
        self.screen.blit(sub, (bx + (bw - sub.get_width()) // 2,
                               by + 8 + main.get_height() + 4))

    def _draw_quest_panel(self):
        """Quest-Übersicht rechts in der Mitte."""
        q = self.active_quest
        panel_x = SCREEN_W - 260
        panel_y = 270
        line_h = 18
        lines = q.lines()
        h = 16 + line_h * (len(lines) + 1) + 8

        bg = pygame.Surface((240, h), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 210))
        self.screen.blit(bg, (panel_x, panel_y))
        pygame.draw.rect(self.screen, GOLD,
                         (panel_x, panel_y, 240, h), 1)

        from .constants import DUNGEONS
        title = self.font_small.render(
            DUNGEONS[self.active_dungeon_id]['name'].upper(),
            True, GOLD_BRIGHT)
        self.screen.blit(title, (panel_x + 10, panel_y + 6))

        cy = panel_y + 24
        for label, progress, target, done in lines:
            icon = '☑' if done else '☐'
            color = (140, 220, 140) if done else TEXT
            text = f'{icon} {label} ({progress}/{target})'
            ls = self.font_small.render(text, True, color)
            self.screen.blit(ls, (panel_x + 10, cy))
            cy += line_h

    def _draw_player_at(self, sx, sy):
        p = self.player
        self._draw_player_rim_light(p, sx, sy)
        # Update #34: Dodge-Trail (Geist-Klone hinter Player während Dodge)
        trail = getattr(p, '_dodge_trail', None)
        if trail:
            from . import aspects as _asp
            pal = _asp.aspect_palette(p.cls)
            for tr in trail:
                fade = 1.0 - (tr['age'] / tr['life'])
                if fade <= 0:
                    continue
                tx, ty = self.w2s_xy(tr['x'], tr['y'])
                alpha = int(120 * fade)
                # Aspekt-getönter Schatten-Klon (Ellipse + Highlight)
                ghost = pygame.Surface((36, 64), pygame.SRCALPHA)
                pygame.draw.ellipse(ghost,
                                     (*pal['bright'], alpha),
                                     (4, 8, 28, 56), 2)
                pygame.draw.ellipse(ghost,
                                     (*pal['primary'], alpha // 2),
                                     (8, 12, 20, 44))
                self.screen.blit(ghost, (int(tx) - 18, int(ty) - 32))
        # Flicker während i-Frames (alle 0.04s blinken)
        if p.invuln > 0:
            phase = int(pygame.time.get_ticks() * 0.025) % 2
            if phase == 1:
                # Sprite nicht rendern für 1 Halbphase → blink-effect
                # Aber Player muss sichtbar sein, also nur halb-transparent
                # via overlay-Vellum-Surface
                pass
            sprites.draw_player_at(self.screen, p, sx, sy, p.walk_phase)
            # I-Frame-Indikator-Ring am Player-Fuß (Aspekt-Cyan-Glow)
            from . import aspects as _asp
            pal = _asp.aspect_palette(p.cls)
            ring_y = sy + p.radius // 2 + 4
            puls = abs(math.sin(pygame.time.get_ticks() * 0.020))
            ring_alpha = int(140 + 80 * puls)
            ring_surf = pygame.Surface((80, 24), pygame.SRCALPHA)
            pygame.draw.ellipse(ring_surf,
                                 (255, 255, 220, ring_alpha),
                                 (0, 0, 80, 20), 2)
            self.screen.blit(ring_surf, (sx - 40, ring_y - 10))
            return
        sprites.draw_player_at(self.screen, p, sx, sy, p.walk_phase)

    def _restore_music_volume_after_death(self):
        """Setzt Music-Volume nach Death-Audio-Ducking zurück (PLAN A-07)."""
        prev = getattr(self, '_music_vol_before_death', None)
        if prev is not None:
            try:
                snd.set_music_volume(prev)
            except Exception:
                pass
            self._music_vol_before_death = None

    def _wake_up_in_town(self):
        """PLAN A-08: Player erwacht in Brassweir (Mahnmal-Shrine) statt
        Title-Screen. Klassen-spezifische Wake-Up-Quote + HP/MP full.

        Lore-Anker: Brassweir = Mahnmal-Gilde-Sitz, Spieler ist Mahnmal-Pakt-
        Mitglied → respawnt am Shrine. Verlorene Dungeon-Tier-Items
        bleiben.

        Update #133 (Z-02): Hardcore-Modus → Permadeath.  Statt Wake-Up
        wird der Save gelöscht und der Spieler ins Title-Menü zurück-
        geschickt.  Memorial-Eintrag bleibt.
        """
        # AA-04 (Update #168): Telemetrie-Death-Event
        try:
            from . import telemetry as _tel
            cause = '?'
            lds = getattr(self, 'last_damage_source', None)
            if lds:
                cause = lds.get('type', '?')
            _tel.record_death(self, cause=cause)
        except Exception:
            pass
        if getattr(self, 'hardcore', False):
            # Permadeath: Save löschen, kein Wake-Up.
            try:
                save_mod.delete_save()
            except Exception:
                pass
            self.toast_queue.append([
                '⚰ HARDCORE-TOD — Save gelöscht. Memorial bleibt.',
                (255, 80, 80), 6.0])
            self._restore_music_volume_after_death()
            self.state = 'title'
            return
        from . import quotes as _q
        self._restore_music_volume_after_death()
        # Reset Player-Sterben-State
        self.player.dying = False
        self.player.death_timer = 0.0
        self.death_phase = 'none'
        self.death_phase_t = 0.0
        # HP/MP refilled — Sterbe-Strafe nur via verlorene Quest-Stages.
        from . import progression
        eff = progression.effective(self.player)
        self.player.hp = eff['hp_max']
        self.player.mp = eff['mp_max']
        self.player.invuln = 2.0  # 2s Grace nach Wake-Up
        self.state = 'playing'
        # Town betreten (resets Position, generiert NPCs neu)
        self.enter_town()
        # Klassen-Wake-Up-Quote
        boss_arena = (getattr(self, 'last_damage_source', None) is not None
                       and self.last_damage_source.get('source') and
                       getattr(self.last_damage_source.get('source'),
                               'is_boss', False))
        wake = _q.pick_wake_up_quote(self.player.cls, boss_arena=boss_arena)
        if wake:
            self.toast(wake, (215, 200, 175))
        # A-09 (Update #61): Klassen-spezifische Wake-Up-VFX.  Aspekt-themed
        # Partikel-Burst + Floater am Player.  Lore-Bibel Teil 7: jede
        # Klasse hat einen Aspekt-Lineage; der antwortet beim Aufwachen.
        WAKE_VFX = {
            # (color, n_particles, life, label, label_color)
            'warrior':  ((255, 140,  60), 36, 1.0, 'Eisen erinnert sich',
                          (255, 200, 140)),
            'monk':     ((220, 220, 240), 24, 1.4, 'Stille kehrt zurück',
                          (240, 240, 255)),
            'mage':     ((255, 220,  80), 32, 1.0, 'Funken sammeln sich',
                          (255, 240, 160)),
            'witch':    ((180, 100, 220), 30, 1.2, 'Schatten halten',
                          (220, 160, 240)),
            'ranger':   ((140, 220, 140), 28, 1.2, 'Wurzeln tragen dich',
                          (180, 240, 180)),
            'rogue':    ((220, 180, 110), 28, 1.0, 'Mahnmal erkennt dich',
                          (240, 210, 150)),
            'huntress': ((255, 200, 100), 30, 1.0, 'Wind führt zurück',
                          (255, 230, 160)),
            'druid':    ((200, 170, 100), 32, 1.4, 'Tiergeister wachen',
                          (220, 200, 140)),
        }
        cfg = WAKE_VFX.get(self.player.cls, WAKE_VFX['warrior'])
        col, n_p, life, lbl, lbl_col = cfg
        # Burst-Particles
        for _ in range(n_p):
            ang = random.uniform(0, math.tau)
            sp = random.uniform(40, 140)
            self.particles_push(
                self.player.pos.x, self.player.pos.y,
                math.cos(ang) * sp, math.sin(ang) * sp,
                col, random.uniform(0.6, life),
                random.uniform(2, 5), gravity=-30)
        # Aufsteigende Aspekt-Sterne (zusätzliche Vertikal-Schicht)
        for _ in range(8):
            ox = random.uniform(-20, 20)
            self.particles.append(Particle(
                self.player.pos.x + ox,
                self.player.pos.y + random.uniform(-5, 15),
                ox * 0.4, random.uniform(-80, -40),
                col, random.uniform(0.8, life * 1.2),
                random.uniform(2, 3), gravity=-20))
        # Kurzer Class-Floater über dem Player
        self.floaters.append(Floater(
            self.player.pos.x, self.player.pos.y - 50,
            lbl, lbl_col, big=True, life=1.6))
        # Death-Counter wird NICHT zurückgesetzt — bleibt für Skip-Threshold

    # ==========================================================
    # Update #135: Quest-Turn-In-Modal (Y-12 follow-up)
    # ==========================================================
    def _quest_ready_to_turn_in(self, npc_name):
        """Returnt QuestState wenn der NPC eine RETURN-Stage hat die
        die *letzte* Stage der Quest ist (= Quest gleich abgeschlossen).
        Sonst None.
        """
        log = self.quest_log
        if log is None:
            return None
        try:
            from . import quest_data as _qd
        except ImportError:
            return None
        for st in log.active.values():
            stage = st.stage
            if stage is None:
                continue
            if stage.get('type') != _qd.StageType.RETURN:
                continue
            tgt = stage.get('target', {}) or {}
            if tgt.get('npc_name') != npc_name:
                continue
            # Letzte Stage?
            stages = st.quest.get('stages', [])
            if st.stage_index >= len(stages) - 1:
                return st
        return None

    def _draw_quest_turnin_modal(self):
        """Update #135: Quest-Turn-In-Modal mit Belohnungs-Preview.

        Layout: Pergament-Modal mit Quest-Title (groß), Done-Häkchen,
        Beschreibung/Lore-Quote, Reward-Liste (Gold/XP/Item/Faction-Rep),
        und zwei Buttons: [ENTER] Belohnung annehmen / [ESC] Später.
        """
        from . import aspects as _asp
        st = getattr(self, '_quest_turnin_state', None)
        npc_name = getattr(self, '_quest_turnin_npc', '?')
        if st is None:
            self.modal = None
            return
        # Verdunklung
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        self.screen.blit(overlay, (0, 0))
        # Modal-Rect
        W, H = 580, 420
        x = SCREEN_W // 2 - W // 2
        y = SCREEN_H // 2 - H // 2
        modal = pygame.Rect(x, y, W, H)
        # Pergament-Hintergrund
        page = pygame.Surface((W, H), pygame.SRCALPHA)
        for py in range(H):
            t = py / max(1, H - 1)
            rr = int(42 + (28 - 42) * t)
            gg = int(31 + (22 - 31) * t)
            bb = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (rr, gg, bb, 252), (0, py), (W, py))
        self.screen.blit(page, modal.topleft)
        bronze = (154, 118, 66)
        pygame.draw.rect(self.screen, bronze, modal, 2)
        _asp.draw_filigree_corners(self.screen, modal, bronze, size=20)
        # Header: "QUEST ABGABE"
        eyebrow = self.font_small.render(
            f'— QUEST · {npc_name.upper()} —', True, (180, 140, 80))
        self.screen.blit(eyebrow,
                          (modal.centerx - eyebrow.get_width() // 2,
                           y + 14))
        # Quest-Titel (groß)
        title = st.quest.get('title', '?')
        ts = self.font_med.render(title, True, (243, 213, 114))
        self.screen.blit(ts,
                          (modal.centerx - ts.get_width() // 2,
                           y + 36))
        # ✓ Häkchen
        check_surf = self.font_med.render(
            'Erfolgreich abgeschlossen', True, (140, 220, 140))
        self.screen.blit(check_surf,
                          (modal.centerx - check_surf.get_width() // 2,
                           y + 64))
        _asp.draw_ornament_divider(self.screen,
                                     x + 24, y + 92, W - 48, bronze)
        # Lore/Description
        desc = st.quest.get('description', '')
        if desc:
            lines = self._wrap_codex(desc, 56)
            cy = y + 104
            for line in lines[:3]:
                ds = self.font_small.render(
                    line, True, (220, 200, 160))
                self.screen.blit(ds, (x + 30, cy))
                cy += ds.get_height() + 2
        # Reward-Liste (zentriert)
        reward = st.quest.get('reward', {}) or {}
        ry = y + 178
        rh = self.font_med.render(
            'BELOHNUNG', True, (200, 180, 120))
        self.screen.blit(rh,
                          (modal.centerx - rh.get_width() // 2, ry))
        ry += rh.get_height() + 10
        # Zeilen: Gold, XP, Item, Faction-Rep
        rows = []
        gold = reward.get('gold', 0)
        xp = reward.get('xp', 0)
        if gold:
            rows.append(('Gold',     f'+{gold} g',  (255, 215, 90)))
        if xp:
            rows.append(('Erfahrung', f'+{xp} XP',  (180, 220, 255)))
        item = reward.get('item')
        if item:
            rows.append(('Item',     str(item),     (200, 180, 255)))
        frep = reward.get('faction_rep') or {}
        try:
            from . import faction as _fac
            for fk, amount in frep.items():
                name = _fac.faction_display_name(fk)
                col = _fac.faction_color(fk)
                rows.append((name, f'{amount:+d} Rep', col))
        except Exception:
            pass
        if not rows:
            rows.append(('—', 'Keine Belohnung', (140, 130, 110)))
        for label, value, col in rows:
            ls = self.font_small.render(label, True, (200, 180, 140))
            vs = self.font_small.render(value, True, col)
            row_w = ls.get_width() + 24 + vs.get_width()
            row_x = modal.centerx - row_w // 2
            self.screen.blit(ls, (row_x, ry))
            self.screen.blit(vs, (row_x + ls.get_width() + 24, ry))
            ry += ls.get_height() + 4
        # Buttons unten
        btn_w, btn_h = 220, 44
        btn_y = y + H - 70
        gap = 24
        total_bw = btn_w * 2 + gap
        bx_accept = modal.centerx - total_bw // 2
        bx_later = bx_accept + btn_w + gap
        # Accept (Gold)
        rect_a = pygame.Rect(bx_accept, btn_y, btn_w, btn_h)
        rect_l = pygame.Rect(bx_later, btn_y, btn_w, btn_h)
        self._quest_turnin_button_rects = {
            'accept': rect_a, 'later': rect_l,
        }
        mx, my = pygame.mouse.get_pos()
        for rect, label, hot, col, key in [
            (rect_a, 'Belohnung annehmen', '[ENTER]',
             (240, 200, 100), 'accept'),
            (rect_l, 'Später', '[ESC]',
             (180, 160, 130), 'later'),
        ]:
            hovered = rect.collidepoint(mx, my)
            bg = (50, 36, 18) if hovered else (30, 22, 12)
            pygame.draw.rect(self.screen, bg, rect)
            pygame.draw.rect(self.screen, col, rect, 2)
            lbl = self.font_small.render(label, True, col)
            self.screen.blit(lbl, lbl.get_rect(
                center=(rect.centerx, rect.y + 14)))
            hs = self.font_small.render(hot, True, (150, 130, 100))
            self.screen.blit(hs, hs.get_rect(
                center=(rect.centerx, rect.y + 32)))

    def _confirm_quest_turnin(self):
        """Update #135: Spieler bestätigt Quest-Abgabe → tatsächlich
        advance + Modal schließen."""
        st = getattr(self, '_quest_turnin_state', None)
        if st is None:
            self.modal = None
            return
        # Großer Reward-VFX-Burst um den Spieler
        self.spawn_particles(
            self.player.pos.x, self.player.pos.y,
            36, (255, 220, 100),
            life_max=1.4, size_max=5, gravity=-40)
        # Camera-Pulse via shake
        self.shake = max(self.shake, 8)
        # Advance über die normale Pipeline (löst _mark_complete + Notif)
        from . import quests as _q
        _q.on_talk(self, self._quest_turnin_npc)
        self.modal = None
        self._quest_turnin_state = None
        self._quest_turnin_npc = None

    def open_dialog_for_npc(self, npc):
        """ROADMAP T1.3: Oeffne DialogUI fuer einen NPC.

        Baut einen Default-Tree aus den `voice_lines` (Roster oder
        Brassweir-Pool) und rendert das Portrait-Modal.  Wenn der NPC
        kein eigenes Modal (vendor/stash/mystic/smith/quest/innkeeper)
        triggern wuerde, ist Dialog der natuerliche Fallback.

        Wird optional von `_show_npc_greeting` und vom NPC-Click-Handler
        genutzt (Setting `dialog_modal`).
        """
        try:
            roster_key = getattr(npc, 'roster_key', None)
            npc_key = roster_key or getattr(npc, 'name', 'npc').lower().split()[0]
            tree = self._dialog_mod.build_default_tree_for_npc(npc_key, npc)
            self.dialog_ui.open(self, tree, 'start', npc_obj=npc)
        except Exception:
            pass

    def _show_npc_greeting(self, npc):
        """NPC-Greeting aus VELGRAD_VOICE_LINES_POOL.md — Toast vor Modal.

        Update #114: Erweitert um Outpost-NPCs. Wenn der NPC ein
        `roster_key` hat (gesetzt von `outposts.build_outpost_npcs`),
        nutzen wir die `voice_lines`-Tuple aus dem Roster.  Sonst
        Fallback auf die hardgecodeten Brassweir-Greetings.

        Update #X — Phase-2-AI: Wenn der NPC einen Brassweir-Name hat
        (korven/helst/vossharil/tameris/otreth/mara/vehren/drei_muetter),
        spielen wir zusaetzlich eine generierte Voice-Line via
        sf.voice_registry.pick_voice().
        """
        import random as _r
        # Voice-Registry: AI-Voice-Line abspielen falls vorhanden
        try:
            from . import voice_registry as _vr
            VOICE_NPC_KEY = {
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
            voice_key = VOICE_NPC_KEY.get(npc.name)
            if voice_key:
                # Update #129: über play_voice → dedup + dialog-channel.
                from . import sounds as _snd
                _snd.play_voice(voice_key, 'greeting', volume=0.8)
            # Update #131 (Y-01): markiert ersten NPC-Talk für Tutorial-
            # Auto-Advance.
            try:
                from . import tutorial as _tut
                _tut.mech_hint(self, 'first_npc_talk')
            except ImportError:
                pass
        except Exception:
            pass

        # Erst: Outpost-NPC mit Roster-Daten?
        roster_key = getattr(npc, 'roster_key', None)
        if roster_key:
            from . import outposts as _op
            spec = _op.NPC_ROSTER.get(roster_key)
            if spec and spec.get('voice_lines'):
                line = _r.choice(spec['voice_lines'])
                self.toast(f'{npc.name}: „{line}“', (255, 230, 180))
                return
        GREETINGS = {
            'Korven Vor': [
                'Schön, dass du noch atmest. Setz dich.',
                'Zur Sache. Reden ist nicht bezahlt.',
                'Bist du noch ganz? Letztens warst du... weniger.',
            ],
            'Mara die Mahnerin': [
                'Ich habe dich noch nicht getroffen. Aber ich erinnere mich an dich.',
                'Du wirst übermorgen müde sein. Schlaf heute schon.',
                'Wir hatten dieses Gespräch schon. In einer anderen Welt.',
            ],
            'Otreth Hohlauge': [
                'Bring mir Steine. Bring sie sauber. Bring sie ungelesen.',
                'Mein Werkzeug hat mich gewarnt, du würdest heute kommen.',
                'Setz dich. Sprich leise. Die ungeschliffenen Steine sind schreckhaft.',
            ],
            'Tameris': [
                'Der Verbannte. Ich hatte gehofft, du kommst zurück.',
                'Du läufst, als hättest du etwas verloren. Wir alle haben.',
                'Setz dich zu mir am Feuer.',
            ],
            'Mahnmal-Verwahrer': [
                'Lade ab. Was du nicht trägst, vergisst dich nicht.',
                'Die Truhe behält. Mehr braucht sie nicht.',
            ],
            'Stadtsprecher Eldon': [
                'Was Brassweir vergisst, vergisst der Stadtsprecher nicht.',
                # Update #158: Eldon-Voice-Fix — vorher „Tinte tropft noch"
                # (zu poetisch). Eldon ist bürokratisch-formal.
                'Eintrag im Brett aktualisiert. Auftrag ist einsehbar.',
            ],
        }
        pool = GREETINGS.get(npc.name)
        if not pool:
            return
        line = _r.choice(pool)
        self.toast(f'{npc.name}: „{line}“', (255, 230, 180))

    def _draw_skill_tooltip(self):
        """G-14: Tooltip beim Hover über die Skill-Bar.

        Zeigt Name, Tags, Mana, CD und Beschreibung aus SKILL_INFO.
        Slot-Rects werden von ui.draw_hud pro Frame in
        self._hotkey_slot_rects abgelegt.
        """
        rects = getattr(self, '_hotkey_slot_rects', None)
        if not rects:
            return
        mx, my = pygame.mouse.get_pos()
        hovered = None
        for rect, skill_id in rects:
            if rect.collidepoint(mx, my):
                hovered = skill_id
                break
        if hovered is None or hovered == 'melee':
            return
        from .skills import SKILL_INFO
        info = SKILL_INFO.get(hovered)
        if not info:
            return
        # Layout-Berechnung
        name = info.get('name', hovered)
        tags = info.get('tags', [])
        mana = info.get('mana', 0)
        cd   = info.get('cd', 0)
        desc = info.get('desc', '')
        # Mehrzeiliger Body
        lines = []
        lines.append((name, GOLD_BRIGHT, self.font_med))
        if tags:
            lines.append((' · '.join(tags), (180, 160, 120), self.font_small))
        meta = []
        if mana > 0:
            meta.append(f'Mana {int(mana)}')
        if cd > 0:
            meta.append(f'CD {cd:.1f}s')
        if meta:
            lines.append(('  '.join(meta), MANA, self.font_small))
        if desc:
            # Soft-Wrap auf ~38 Zeichen
            words = desc.split()
            cur = ''
            for w in words:
                if len(cur) + len(w) + 1 > 38:
                    lines.append((cur, TEXT, self.font_small))
                    cur = w
                else:
                    cur = (cur + ' ' + w) if cur else w
            if cur:
                lines.append((cur, TEXT, self.font_small))

        # Maßnehmen
        w_max = 0
        h_total = 0
        gap = 4
        rendered = []
        for txt, col, fnt in lines:
            surf = fnt.render(txt, True, col)
            rendered.append(surf)
            w_max = max(w_max, surf.get_width())
            h_total += surf.get_height() + gap
        h_total -= gap
        pad = 12
        bw = w_max + pad * 2
        bh = h_total + pad * 2
        # Positioniere über dem ersten Slot, leicht versetzt
        first_rect = rects[0][0]
        bx = max(8, min(SCREEN_W - bw - 8, mx - bw // 2))
        by = max(8, first_rect.y - bh - 8)
        # Hintergrund
        bg = pygame.Surface((bw, bh), pygame.SRCALPHA)
        bg.fill((16, 12, 8, 235))
        self.screen.blit(bg, (bx, by))
        pygame.draw.rect(self.screen, GOLD, (bx, by, bw, bh), 2)
        # Text
        yy = by + pad
        for surf in rendered:
            self.screen.blit(surf, (bx + pad, yy))
            yy += surf.get_height() + gap

    # Update #120: District-Label-Daten pro Area.  Pro Eintrag:
    #   (text, world_x, world_y, color_tint)
    # Brassweir hat 7 District-Labels für die Lore-Hub-Architektur;
    # Outposts haben jeweils 1 Region-Label.
    _BRASSWEIR_DISTRICTS = [
        ('Tempel-Platz',      0, -480, (200, 180, 240)),
        ('Mahnmal-Halle',     360, -130, (220, 180, 110)),
        ('Gemcutter-Werkstatt', -360, -130, (200, 160, 110)),
        ('Wirtshaus',         -360, 180, (200, 170, 130)),
        ('Hafen-Pier',        430, 320, (160, 200, 220)),
        ('Wegmal-Tor',        0, 270, (240, 220, 160)),
        # Update #125: „Dungeon-Portale" → klarer Lore-Name.
        # Dies IST Akt 1 — der Player muss wissen, dass das sein Start ist.
        ('Akt I — Krypta der Vergessenen', 0, 500, (220, 180, 110)),
        ('Faction-Promenade', 400, -280, (220, 200, 170)),
    ]

    def _draw_district_labels(self):
        """Update #120: Schwebende District-Bezeichner über jeder Stadt-
        Zone. Dezent (alpha ~150), gold-Akzent-Outline. Beim Zoom auf
        eine Zone macht das die Stadt-Architektur klar lesbar.
        """
        if self.area == 'town':
            labels = self._BRASSWEIR_DISTRICTS
            # Faction-Promenade-Label nur wenn ≥1 Faction-Banner existiert
            has_banners = any(
                getattr(t, 'faction_key', None) is not None
                for t in self.tiles)
            if not has_banners:
                labels = [l for l in labels
                          if l[0] != 'Faction-Promenade']
        elif self.area == 'outpost' and self.outpost_id:
            from . import outposts as _op
            cfg = _op.get_outpost(self.outpost_id)
            if cfg is None:
                return
            labels = [(cfg['region_name'], 0, -260, cfg['color'])]
        else:
            return

        for text, wx, wy, color in labels:
            sx, sy = self.w2s_xy(wx, wy)
            # Off-screen-Cull
            if sx < -100 or sx > SCREEN_W + 100:
                continue
            if sy < -50 or sy > SCREEN_H + 50:
                continue
            # Update #125: Akt-Labels (mit „Akt"-Prefix) werden größer
            # gerendert — das ist der wichtigste Marker im Stadtbild.
            is_akt_label = text.startswith('Akt ')
            if is_akt_label and hasattr(self, 'font_med'):
                font = self.font_med
            elif hasattr(self, 'font_small'):
                font = self.font_small
            else:
                continue
            lbl_surf = font.render(text, True, color)
            # Schwarz-Outline (4-Richtungen) für Lesbarkeit auf jedem BG
            outline = font.render(text, True, (0, 0, 0))
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                self.screen.blit(outline,
                                  (int(sx) - lbl_surf.get_width() // 2 + dx,
                                   int(sy) - lbl_surf.get_height() // 2 + dy))
            # Akt-Labels voller Sichtbarkeit (alpha 230), andere dezenter
            lbl_surf.set_alpha(230 if is_akt_label else 190)
            self.screen.blit(lbl_surf,
                              (int(sx) - lbl_surf.get_width() // 2,
                               int(sy) - lbl_surf.get_height() // 2))

    def _draw_outpost_portal(self, op, sx, sy):
        """Update #113 + #119: Render-Pass für OutpostPortal als Wegmal.

        Visuell jetzt deutlich höher und sichtbarer — die alte „Goldring"-
        Variante war zu zurückhaltend.  Aufbau (von unten nach oben):
          1. Stein-Sockel (Bronze-Granit, 28×16)
          2. Wegmal-Stele (28×56, Akzent-Streifen)
          3. Pulsierender Aura-Ring über dem Stein
          4. Banner-Fahne mit Outpost-Akzent-Farbe (lateral wehend)
          5. Aspekt-Sigil an der Spitze (3 rotierende Funken)
          6. Region-Name-Banner unter dem Stein

        Lore-Anker: Mahnmal-Wegmale sind 800-jährige Stein-Stelen aus
        Brassweirs Hafen-Versteinerung.
        """
        from . import outposts as _op
        # Update #143: Locked-Portale gedämpfter (grau + kein Puls)
        is_locked = getattr(op, '_locked', False)
        if is_locked:
            puls = 0.3   # statisch dim
            sway = 0.0
        else:
            puls = abs(math.sin(pygame.time.get_ticks() * 0.003))
            sway = math.sin(pygame.time.get_ticks() * 0.002)
        bob = int(sway * 2)

        # Akzent-Farbe aus Outpost-Cfg
        cfg = _op.OUTPOSTS.get(op.outpost_key) if hasattr(op, 'outpost_key') \
            else None
        accent = cfg['color'] if cfg else (220, 200, 140)
        # Locked: entsättigt zu Grau-Ton
        if is_locked:
            avg = (accent[0] + accent[1] + accent[2]) // 3
            accent = (int(avg * 0.6),
                       int(avg * 0.6),
                       int(avg * 0.65))
        glow_c = (min(255, accent[0] + 30),
                  min(255, accent[1] + 30),
                  min(255, accent[2] + 30))

        cx, cy = int(sx), int(sy)

        # 1. Boden-Schatten (elliptisch unter der Stele)
        shadow = pygame.Surface((70, 24), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120), (0, 0, 70, 24))
        self.screen.blit(shadow, (cx - 35, cy + 30))

        # 2. Stein-Sockel (Bronze-Granit)
        socket = pygame.Rect(cx - 18, cy + 20, 36, 18)
        pygame.draw.rect(self.screen, (90, 70, 50), socket)
        pygame.draw.rect(self.screen, (140, 110, 80), socket, 2)
        # Sockel-Highlight oben
        pygame.draw.line(self.screen, (180, 150, 110),
                          (socket.x + 2, socket.y + 2),
                          (socket.right - 2, socket.y + 2), 1)

        # 3. Wegmal-Stele (vertikaler Stein-Block, 28×64)
        stele = pygame.Rect(cx - 14, cy - 44, 28, 64)
        pygame.draw.rect(self.screen, (70, 56, 40), stele)
        pygame.draw.rect(self.screen, (130, 100, 70), stele, 2)
        # Akzent-Streifen vertikal in Faction-Farbe
        pygame.draw.line(self.screen, accent,
                          (cx, stele.y + 6),
                          (cx, stele.bottom - 6), 3)
        # Akzent-Pulse links + rechts vom Streifen
        side_alpha = int(120 + 80 * puls)
        side_surf = pygame.Surface((4, 50), pygame.SRCALPHA)
        side_surf.fill((*glow_c, side_alpha))
        self.screen.blit(side_surf, (cx - 6, stele.y + 8))
        self.screen.blit(side_surf, (cx + 2, stele.y + 8))

        # 4. Banner-Fahne (rechts vom Stein, wehend)
        flag_top_y = cy - 56 + bob
        flag_h = 28
        flag_x = cx + 14
        sway_offset = int(sway * 6)
        # Banner-Stab oben
        pygame.draw.line(self.screen, (160, 130, 90),
                          (flag_x, cy - 44), (flag_x, flag_top_y), 2)
        # Banner-Fläche (Trapez für „wehender" Effekt)
        banner_pts = [
            (flag_x, flag_top_y),
            (flag_x + 22 + sway_offset, flag_top_y + 4),
            (flag_x + 22 + sway_offset, flag_top_y + flag_h - 2),
            (flag_x, flag_top_y + flag_h - 4),
        ]
        pygame.draw.polygon(self.screen, accent, banner_pts)
        pygame.draw.polygon(self.screen, glow_c, banner_pts, 1)
        # Sigil auf dem Banner (kleines Aspekt-Diamant)
        sigil_x = flag_x + 11 + sway_offset // 2
        sigil_y = flag_top_y + flag_h // 2
        sigil_pts = [
            (sigil_x, sigil_y - 5),
            (sigil_x + 4, sigil_y),
            (sigil_x, sigil_y + 5),
            (sigil_x - 4, sigil_y),
        ]
        pygame.draw.polygon(self.screen, (240, 220, 160), sigil_pts)

        # 5. Pulsierender Aura-Ring über der Stele-Spitze
        aura_cy = cy - 30 + bob
        aura = pygame.Surface((110, 110), pygame.SRCALPHA)
        outer_r = 36 + int(puls * 7)
        pygame.draw.circle(aura, (*glow_c, int(70 + 50 * puls)),
                            (55, 55), outer_r, 2)
        pygame.draw.circle(aura, (*accent, int(40 + 30 * puls)),
                            (55, 55), outer_r - 6, 1)
        self.screen.blit(aura, (cx - 55, aura_cy - 55))

        # 6. Drei rotierende Aspekt-Funken
        ang_offset = pygame.time.get_ticks() * 0.0012
        for i in range(3):
            ang = ang_offset + i * (math.tau / 3)
            fx = cx + int(math.cos(ang) * outer_r)
            fy = aura_cy + int(math.sin(ang) * outer_r)
            pygame.draw.circle(self.screen, glow_c, (fx, fy), 3)
            pygame.draw.circle(self.screen, (255, 250, 220), (fx, fy), 1)

        # 7. Region-Name-Banner unter dem Stein
        label = getattr(op, 'label', None)
        if label and hasattr(self, 'font_small'):
            ls = self.font_small.render(label, True, (240, 230, 200))
            bg_w = ls.get_width() + 18
            bg_h = ls.get_height() + 6
            # Default unter der Stele; aber wenn das ins untere HUD
            # (Hotbar/Globes ab ~SCREEN_H-200) ragen wuerde, ueber die
            # Stele klappen — sonst ueberlappt das Label die Hotbar
            # (User-Report „untere UI ueberlappt").
            label_y = cy + 44
            if label_y + bg_h > SCREEN_H - 200:
                label_y = cy - 58 - bg_h
            bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
            bg.fill((16, 12, 20, 200))
            pygame.draw.rect(bg, (*accent, 200), bg.get_rect(), 1)
            self.screen.blit(bg, (cx - bg_w // 2, label_y))
            self.screen.blit(ls, (cx - ls.get_width() // 2 + 9,
                                   label_y + 3))

    def _draw_tutorial_portal_arrow(self, sx, sy, label='HIER STARTEN'):
        """Update #130: Hand-Holding für den Spieler — großer pulsierender
        Pfeil + Label über dem Akt-1-Krypta-Portal solange er noch keinen
        Dungeon abgeschlossen hat.  Macht eindeutig welches Portal er
        nehmen soll.

        User-Report „Es ist nicht klar ersichtlich welches Portal man
        nehmen muss nimm den Spieler mehr an die hand".
        """
        t = pygame.time.get_ticks()
        puls = abs(math.sin(t * 0.005))
        bob = int(math.sin(t * 0.004) * 6)
        cx = int(sx)
        # Pfeil-Spitze sitzt über dem Portal-Bogen (~ -100 px relativ zum
        # Portal-Mittelpunkt, +bob).  User-Fix („untere UI ueberlappt"):
        # nach oben klemmen, damit Pfeil + Label nicht ins Bottom-HUD
        # (Hotbar/Globes ab ~SCREEN_H-200) rutschen, wenn das Portal am
        # unteren Bildrand liegt.
        arrow_tip_y = min(int(sy) - 90 + bob, SCREEN_H - 300)

        # Glow-Halo um die Pfeilspitze
        glow = pygame.Surface((140, 80), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            a = int(40 / i * (0.5 + puls * 0.5))
            pygame.draw.ellipse(glow, (255, 230, 80, a),
                                 (10 - i, 20 - i, 120 + 2 * i, 40 + 2 * i))
        self.screen.blit(glow, (cx - 70, arrow_tip_y - 20))

        # Großer gelber Pfeil (nach unten zeigend)
        arrow_col = (255, 230, 80)
        arrow_outline = (40, 30, 0)
        arrow_pts = [
            (cx,        arrow_tip_y + 30),         # Spitze unten
            (cx - 26,   arrow_tip_y),              # Links oben
            (cx - 12,   arrow_tip_y),
            (cx - 12,   arrow_tip_y - 22),         # Schaft oben links
            (cx + 12,   arrow_tip_y - 22),         # Schaft oben rechts
            (cx + 12,   arrow_tip_y),
            (cx + 26,   arrow_tip_y),              # Rechts oben
        ]
        pygame.draw.polygon(self.screen, arrow_col, arrow_pts)
        pygame.draw.polygon(self.screen, arrow_outline, arrow_pts, 2)

        # Label-Banner unter dem Pfeil
        if hasattr(self, 'font_med'):
            font = self.font_med
            txt = font.render(label, True, (20, 14, 4))
            bg = pygame.Surface((txt.get_width() + 22, txt.get_height() + 8),
                                 pygame.SRCALPHA)
            bg_alpha = int(200 + 50 * puls)
            bg.fill((255, 230, 80, bg_alpha))
            pygame.draw.rect(bg, arrow_outline, bg.get_rect(), 2)
            bx = cx - bg.get_width() // 2
            by = arrow_tip_y - 22 - bg.get_height() - 2
            self.screen.blit(bg, (bx, by))
            self.screen.blit(txt, (bx + 11, by + 4))

    def _draw_npc_quest_marker(self, sx, sy, sigil):
        """Pulsierender Marker `!` (neu) oder `?` (Return) über einem NPC.

        Update #22: Zusätzlich ein klassen-getönter Bodenring (User-Wahl
        „dynamische Klassen-Tönung" für sekundäre UI-Akzente).
        """
        puls = abs(math.sin(pygame.time.get_ticks() * 0.005))
        bob = int(math.sin(pygame.time.get_ticks() * 0.004) * 3)
        col_main = (255, 220, 80) if sigil == '!' else (255, 200, 130)
        col_glow = (255, 240, 150)

        # Klassen-getönter Bodenring um NPC-Position (sigil-y ist Kopfhöhe,
        # Boden ist +64). Pulsierender, doppelter Ring.
        from .constants import CLASSES
        tint = CLASSES.get(self.player.cls, {}).get('color', col_main)
        ring_y = int(sy) + 64
        ring_r1 = 18 + int(puls * 4)
        ring_r2 = 26 + int(puls * 5)
        ring_surf = pygame.Surface((80, 40), pygame.SRCALPHA)
        pygame.draw.ellipse(ring_surf, (*tint, int(120 + 60 * puls)),
                            (40 - ring_r1, 20 - ring_r1 // 3,
                             ring_r1 * 2, max(6, ring_r1 // 1)), 2)
        pygame.draw.ellipse(ring_surf, (*tint, int(60 + 30 * puls)),
                            (40 - ring_r2, 20 - ring_r2 // 3,
                             ring_r2 * 2, max(6, ring_r2 // 1)), 1)
        self.screen.blit(ring_surf, (int(sx) - 40, ring_y - 20))

        # Glow-Hintergrund über NPC
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*col_glow, int(60 + 40 * puls)),
                           (20, 20), 14)
        pygame.draw.circle(glow, (*col_glow, int(120 + 60 * puls)),
                           (20, 20), 9)
        self.screen.blit(glow, (int(sx) - 20, int(sy) + bob - 20))
        # Symbol
        sigil_surf = self.font_med.render(sigil, True, col_main)
        sigil_rect = sigil_surf.get_rect(center=(int(sx), int(sy) + bob))
        # Outline
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            outline = self.font_med.render(sigil, True, (20, 12, 6))
            outline_rect = outline.get_rect(
                center=(int(sx) + ox, int(sy) + bob + oy))
            self.screen.blit(outline, outline_rect)
        self.screen.blit(sigil_surf, sigil_rect)

    def _draw_player_rim_light(self, p, sx, sy):
        """Update #40: Player-Bodenrune deutlich dezenter.

        User-Feedback: Lichtkreis war zu dominant. Jetzt nur ein
        dünner Aspekt-Akzent-Ring am Fuß, kein großer Lichtkegel.
        """
        if not self.settings.get('rim_light', True):
            return
        if getattr(p, 'dying', False):
            return
        DAYLIGHT_BIOMES = {'town', 'desert'}
        if self.biome in DAYLIGHT_BIOMES:
            return
        from . import aspects as _asp
        pal = _asp.aspect_palette(p.cls)
        t = pygame.time.get_ticks() * 0.001
        puls = 0.6 + 0.4 * math.sin(t * 0.6)
        flash_mult = 0.4 if self.settings.get('photosensitive', False) else 1.0
        amp = puls * flash_mult * 0.6  # auf 60% gedämpft
        # Schmaler Ellipsen-Ring am Fuß (nicht großer Halo)
        ring_y = sy + p.radius // 2 + 4
        ring_w = p.radius * 2 - 2
        ring_h = p.radius // 2
        ring_surf = pygame.Surface((ring_w + 8, ring_h + 6),
                                    pygame.SRCALPHA)
        pygame.draw.ellipse(ring_surf,
                            (*pal['bright'], int(60 * amp)),
                            (2, 2, ring_w, ring_h), 1)
        self.screen.blit(ring_surf, (sx - (ring_w + 8) // 2,
                                       ring_y - (ring_h + 6) // 2))

    # Update #87 — Ailment-Status-Pips über Enemy-HP-Bar
    _STATUS_PIP_ORDER = ('burn', 'poison', 'bleed', 'frost', 'chill',
                          'shock', 'brittle', 'sapped', 'armour_break',
                          'pinned')
    _STATUS_PIP_COLOR = {
        'burn':         (255, 130,  60),
        'poison':       (140, 220,  90),
        'bleed':        (220,  50,  50),
        'frost':        (140, 200, 240),
        'chill':        (180, 220, 240),
        'shock':        (200, 220, 255),
        'brittle':      (220, 240, 255),
        'sapped':       (180, 180, 200),
        'armour_break': (220, 180, 100),
        'pinned':       (180, 140, 220),
    }

    def _draw_enemy_status_pips(self, e, cx, top_y):
        """Update #87: Status-Pips als 4 px Kreise oberhalb der HP-Bar.
        Burn/Poison/Bleed/Frost/Chill/Shock/Brittle/Sapped/Armour-Break/Pinned.
        Falls Status `stacks`>1, zeigt einen kleineren Ring um den Pip.
        Maximal 6 Pips sichtbar — extra werden ausgeblendet (Ordnung).
        """
        status = getattr(e, 'status', None)
        if not status:
            return
        active = []
        for key in self._STATUS_PIP_ORDER:
            if key in status:
                active.append(key)
            if len(active) >= 6:
                break
        if not active:
            return
        n = len(active)
        pip_w = 8
        total_w = n * pip_w + (n - 1) * 2
        x0 = cx - total_w // 2 + pip_w // 2
        for i, key in enumerate(active):
            px = x0 + i * (pip_w + 2)
            py = top_y
            col = self._STATUS_PIP_COLOR.get(key, (200, 200, 200))
            pygame.draw.circle(self.screen, col, (px, py), 3)
            # Stack-Ring wenn Stacks > 1
            try:
                stacks = int(status[key].get('stacks', 1))
            except Exception:
                stacks = 1
            if stacks > 1:
                pygame.draw.circle(self.screen, (255, 240, 200),
                                    (px, py), 4, 1)

    def _draw_enemy_at(self, e, sx, sy):
        # Update #136 (O-19): Aggro-Tell-Animation — bei AGGRO-State-Wechsel
        # 0.35 s Sprite-Flash (heller Rim) + roter Eye-Glow + Y-Scale-Pulse.
        # Spieler sieht „der hat mich gesehen!" sofort.
        if getattr(e, '_aggro_tell_t', 0) > 0:
            e._aggro_tell_t = max(0.0, e._aggro_tell_t - 0.016)
            t_left = e._aggro_tell_t / 0.35
            # 1. Rote Outline-Aura (pulsierend, schnell)
            r = int(e.radius + 6 + 8 * (1.0 - t_left))
            tell_a = int(220 * t_left)
            tell = pygame.Surface((r * 2 + 4, r * 2 + 4),
                                    pygame.SRCALPHA)
            pygame.draw.circle(tell, (255, 60, 40, tell_a),
                                (r + 2, r + 2), r, 3)
            pygame.draw.circle(tell, (255, 200, 60,
                                       tell_a // 2),
                                (r + 2, r + 2), r - 4, 2)
            self.screen.blit(tell,
                              (int(sx) - r - 2,
                               int(sy) - r - 2 - e.radius // 2))
            # 2. Eye-Glow oben am Mob-Kopf (zwei rote Punkte)
            eye_y = int(sy) - e.height + 8
            eye_a = int(255 * t_left)
            for dx in (-3, 3):
                ec = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(ec, (255, 60, 40, eye_a),
                                    (5, 5), 4)
                pygame.draw.circle(ec, (255, 255, 220, eye_a),
                                    (5, 5), 2)
                self.screen.blit(ec, (int(sx) + dx - 5,
                                        eye_y - 5))
            # 3. „!"-Tell-Floater einmalig am Anim-Start
            if t_left > 0.85 and not getattr(e, '_aggro_tell_pushed',
                                              False):
                e._aggro_tell_pushed = True
                self.floaters.append(Floater(
                    e.pos.x, e.pos.y - e.height - 10,
                    '!', (255, 80, 50), big=True, life=0.5))
            if t_left <= 0.0:
                e._aggro_tell_pushed = False
        # Update #40: Attack-Animation-VFX. Wind-Up zeigt Aura über dem
        # Enemy die anschwillt, Spieler kann reagieren.
        atk_phase = getattr(e, 'atk_phase', 'idle')
        if atk_phase == 'windup':
            phase_t = getattr(e, 'atk_phase_t', 0.0)
            # 0.0 → 0.25, intensity wachsend
            intensity = min(1.0, phase_t / 0.25)
            # Aspekt-rot-Aura um Enemy
            aura_r = int(e.radius + 10 + intensity * 14)
            aura = pygame.Surface((aura_r * 2 + 8, aura_r * 2 + 8),
                                    pygame.SRCALPHA)
            aura_alpha = int(80 + 100 * intensity)
            pygame.draw.circle(aura, (255, 80, 60, aura_alpha),
                                (aura_r + 4, aura_r + 4),
                                aura_r, 2)
            # Innen-Fill mit weniger Alpha
            pygame.draw.circle(aura, (255, 60, 40, aura_alpha // 3),
                                (aura_r + 4, aura_r + 4),
                                aura_r - 2)
            self.screen.blit(aura, (int(sx) - (aura_r + 4),
                                      int(sy) - (aura_r + 4)
                                      - e.radius // 2))
            # Tell-Sterne über Kopf (3 pulsing dots)
            t = pygame.time.get_ticks() * 0.012
            for k in range(3):
                a = t + k * math.tau / 3
                star_x = int(sx) + int(math.cos(a) * 12)
                star_y = int(sy) - e.height - 10 + int(math.sin(a) * 3)
                pygame.draw.circle(self.screen,
                                     (255, 200, 100),
                                     (star_x, star_y),
                                     2 + int(intensity * 2))
            # Richtungs-Pfeil zum Player (Telegraph)
            if e.atk_target_pos is not None:
                tx, ty = self.w2s(e.atk_target_pos)
                dx = tx - sx
                dy = ty - sy
                d = math.hypot(dx, dy)
                if d > 0:
                    nx, ny = dx / d, dy / d
                    pt0 = (int(sx + nx * (e.radius + 6)),
                            int(sy + ny * (e.radius + 6)))
                    pt1 = (int(sx + nx * (e.radius + 6 + 24 * intensity)),
                            int(sy + ny * (e.radius + 6 + 24 * intensity)))
                    pygame.draw.line(self.screen, (255, 100, 60),
                                      pt0, pt1, 3)
        elif atk_phase == 'swing':
            # Flash burst around enemy
            phase_t = getattr(e, 'atk_phase_t', 0.0)
            fade = max(0, 1.0 - phase_t / 0.10)
            flash_r = int(e.radius + 18 + (1 - fade) * 12)
            flash = pygame.Surface((flash_r * 2 + 8, flash_r * 2 + 8),
                                     pygame.SRCALPHA)
            pygame.draw.circle(flash, (255, 220, 150,
                                          int(140 * fade)),
                                (flash_r + 4, flash_r + 4),
                                flash_r, 3)
            self.screen.blit(flash, (int(sx) - (flash_r + 4),
                                       int(sy) - (flash_r + 4)
                                       - e.radius // 2))

        # Update #37: Archetyp-Boden-Aura — kleiner Ring am Mob-Fuß in
        # Archetyp-Farbe. Spieler erkennt Charger (rot) / Caster (blau)
        # / Brute (orange) / Aerial (cyan) auf einen Blick.
        if not e.dying and not e.is_boss:
            arch_color = None
            engage_mode = getattr(e, 'engage_mode', None)
            if engage_mode == 'charge':
                arch_color = (220, 80, 80)    # rot — Charger (Krabbe)
            elif engage_mode == 'ranged':
                arch_color = (140, 180, 220)  # blau — Caster (Wraith)
            elif engage_mode == 'aerial':
                arch_color = (200, 230, 255)  # cyan — Flyer (Möwen)
            elif engage_mode == 'kite':
                arch_color = (180, 220, 140)  # grün — Kite (Goblin)
            elif getattr(e, 'is_mini_boss', False):
                arch_color = (255, 200, 100)  # gold — Mini-Boss
            if arch_color is not None:
                t = pygame.time.get_ticks() * 0.001
                pulse = 0.7 + 0.3 * math.sin(t * 2 + sx * 0.01)
                ring_y = int(sy) + e.radius // 2 + 6
                ring_surf = pygame.Surface((e.radius * 4, 16),
                                            pygame.SRCALPHA)
                pygame.draw.ellipse(ring_surf,
                    (*arch_color, int(80 * pulse)),
                    (0, 2, e.radius * 4, 12), 1)
                self.screen.blit(ring_surf,
                    (int(sx) - e.radius * 2, ring_y - 8))

        # Hover-Outline (gelber Ring)
        if e is self.hovered_enemy and not e.dying:
            outline = pygame.Surface((e.height * 2, e.height * 2), pygame.SRCALPHA)
            pygame.draw.circle(outline, (255, 220, 60, 180),
                               (e.height, e.height), e.radius + 4, 2)
            self.screen.blit(outline, (int(sx) - e.height,
                                        int(sy) - e.height - e.radius // 2))
        sprites.draw_enemy_at(self.screen, e, sx, sy)
        # HP-Balken über dem Sprite (Boss bekommt extra Bar oben)
        if e.hp < e.hp_max and not e.is_boss and not e.dying:
            sx_i, sy_i = int(sx), int(sy)
            w = int(e.radius * 2.4)
            x = sx_i - w // 2
            y = sy_i - e.height - 6
            pygame.draw.rect(self.screen, (20, 10, 10), (x, y, w, 4))
            fill = int(w * e.hp / e.hp_max)
            pygame.draw.rect(self.screen, BLOOD_LIGHT, (x, y, fill, 4))
            # Update #87: Ailment-Status-Indicator-Strip über HP-Bar.
            # POE2-Style: kleine farbige Pips für jeden aktiven Status.
            self._draw_enemy_status_pips(e, sx_i, y - 2)
            # Update #34: Stun-Buildup-Bar (gelb, über HP)
            if hasattr(e, 'stun_buildup') and e.stun_buildup > 0:
                sb_y = y - 6
                pygame.draw.rect(self.screen, (40, 30, 10),
                                  (x, sb_y, w, 3))
                sb_fill = int(w * e.stun_buildup / e.stun_buildup_max)
                pygame.draw.rect(self.screen, (255, 220, 80),
                                  (x, sb_y, sb_fill, 3))
            # STUNNED-Marker wenn aktiv stunned
            if e.stun_timer > 0:
                stun_text = self.font_small.render(
                    'STUNNED', True, (255, 240, 120))
                stun_sh = self.font_small.render(
                    'STUNNED', True, (0, 0, 0))
                self.screen.blit(stun_sh, (sx_i - stun_text.get_width() // 2 + 1,
                                            y - 22 + 1))
                self.screen.blit(stun_text, (sx_i - stun_text.get_width() // 2,
                                              y - 22))
                # Sterne über dem Kopf
                t = pygame.time.get_ticks() * 0.005
                for k in range(3):
                    a = t + k * math.tau / 3
                    star_x = sx_i + int(math.cos(a) * 12)
                    star_y = y - 30 + int(math.sin(a) * 4)
                    pygame.draw.line(self.screen, (255, 240, 100),
                                      (star_x - 3, star_y),
                                      (star_x + 3, star_y), 1)
                    pygame.draw.line(self.screen, (255, 240, 100),
                                      (star_x, star_y - 3),
                                      (star_x, star_y + 3), 1)
            # Mini-Boss-Markierung
            if getattr(e, 'is_mini_boss', False):
                mb = self.font_small.render(
                    getattr(e, 'boss_name', 'Elite'), True, (255, 200, 100))
                self.screen.blit(mb, (sx_i - mb.get_width() // 2, y - 14))

    def _draw_projectile(self, proj):
        sx, sy = self.w2s(proj.pos)
        sx, sy = int(sx), int(sy)
        if proj.kind == 'fireball':
            glow = pygame.Surface((80, 80), pygame.SRCALPHA)
            for i in range(5, 0, -1):
                alpha = 60 // i
                pygame.draw.circle(glow, (255, 100, 30, alpha),
                                   (40, 40), proj.radius * i // 2 + 6)
            self.screen.blit(glow, (sx - 40, sy - 40))
            pygame.draw.circle(self.screen, (255, 244, 168), (sx, sy),
                               int(proj.radius * 0.6))
        elif proj.kind == 'shadowbolt':
            glow = pygame.Surface((60, 60), pygame.SRCALPHA)
            for i in range(4, 0, -1):
                pygame.draw.circle(glow, (140, 60, 220, 60 // i),
                                   (30, 30), proj.radius * i // 2 + 4)
            self.screen.blit(glow, (sx - 30, sy - 30))
            pygame.draw.circle(self.screen, (220, 180, 255), (sx, sy), 4)
        elif proj.kind == 'frostbolt':
            glow = pygame.Surface((60, 60), pygame.SRCALPHA)
            for i in range(4, 0, -1):
                pygame.draw.circle(glow, (140, 200, 255, 60 // i),
                                   (30, 30), proj.radius * i // 2 + 4)
            self.screen.blit(glow, (sx - 30, sy - 30))
            pygame.draw.circle(self.screen, WHITE, (sx, sy), 4)
        elif proj.kind == 'firebolt':
            pygame.draw.circle(self.screen, (255, 100, 30), (sx, sy), proj.radius)
            pygame.draw.circle(self.screen, (255, 220, 120), (sx, sy), 3)
        elif proj.kind == 'arrow':
            # Pfeil als Linie in Richtung der Geschwindigkeit
            v = proj.vel
            ln = max(1e-6, math.hypot(v.x, v.y))
            dx, dy = v.x / ln, v.y / ln
            x1 = sx - dx * 8
            y1 = sy - dy * 8
            x2 = sx + dx * 8
            y2 = sy + dy * 8
            pygame.draw.line(self.screen, (240, 220, 150),
                             (x1, y1), (x2, y2), 2)
            pygame.draw.circle(self.screen, (255, 240, 180), (sx, sy), 2)
        elif proj.kind == 'poisonbolt':
            glow = pygame.Surface((40, 40), pygame.SRCALPHA)
            pygame.draw.circle(glow, (140, 220, 100, 100), (20, 20), 14)
            self.screen.blit(glow, (sx - 20, sy - 20))
            pygame.draw.circle(self.screen, (180, 240, 120), (sx, sy), 5)
        elif proj.kind == 'spark':
            glow = pygame.Surface((36, 36), pygame.SRCALPHA)
            for i in range(4, 0, -1):
                pygame.draw.circle(glow, (180, 200, 255, 60 // i),
                                    (18, 18), 4 + i * 3)
            self.screen.blit(glow, (sx - 18, sy - 18))
            # Zackiger kleiner Funke
            pygame.draw.circle(self.screen, (255, 255, 255), (sx, sy), 3)
            pygame.draw.line(self.screen, (220, 240, 255), (sx - 6, sy), (sx + 6, sy), 1)
            pygame.draw.line(self.screen, (220, 240, 255), (sx, sy - 6), (sx, sy + 6), 1)
        elif proj.kind == 'bone_spear':
            # Pfeil-ähnlich, weißlich
            v = proj.vel
            ln = max(1e-6, math.hypot(v.x, v.y))
            dx, dy = v.x / ln, v.y / ln
            x1, y1 = sx - dx * 18, sy - dy * 18
            x2, y2 = sx + dx * 18, sy + dy * 18
            # Schatten
            pygame.draw.line(self.screen, (0, 0, 0), (x1, y1 + 1), (x2, y2 + 1), 5)
            pygame.draw.line(self.screen, (240, 230, 200), (x1, y1), (x2, y2), 4)
            pygame.draw.line(self.screen, (255, 255, 255), (x1, y1), (x2, y2), 1)
            # Spitze
            pygame.draw.circle(self.screen, (255, 255, 255), (int(x2), int(y2)), 3)

    def _draw_bolt(self, b):
        """Update #138 (M-18): rendert Procedural-Lightning mit Glow-
        Halo + Main-Polyline + Branch-Polylines (Decay-Alpha).

        3-Layer-Glow: außen breit/transparent (cyan-blau), innen dünn
        weiß-hell.  Branches mit 60% Alpha gegenüber Main.
        """
        a = 1 - b.age / b.life
        if a <= 0:
            return
        pts = [self.w2s(Vector2(x, y)) for x, y in b.points]
        if len(pts) < 2:
            return
        # Glow-Surface über die Bounding-Box des Bolts
        try:
            min_x = min(p[0] for p in pts)
            max_x = max(p[0] for p in pts)
            min_y = min(p[1] for p in pts)
            max_y = max(p[1] for p in pts)
            # Branches mit in die BBox aufnehmen
            for bpath in getattr(b, 'branches', ()):
                for x, y in bpath:
                    bs = self.w2s(Vector2(x, y))
                    min_x = min(min_x, bs[0]); max_x = max(max_x, bs[0])
                    min_y = min(min_y, bs[1]); max_y = max(max_y, bs[1])
            # Padding für Glow
            pad = 16
            bbw = max(2, int(max_x - min_x + pad * 2))
            bbh = max(2, int(max_y - min_y + pad * 2))
            ox, oy = int(min_x - pad), int(min_y - pad)
            glow_surf = pygame.Surface((bbw, bbh), pygame.SRCALPHA)
            # Offset-Helper für Glow-Surface
            def _shift(p):
                return (int(p[0] - ox), int(p[1] - oy))
            main_shift = [_shift(p) for p in pts]
            # 3-Layer-Render: außen breit + transparent, Mitte normal,
            # innen schmal + hell-weiß
            outer_w = max(2, int(8 * a))
            mid_w = max(1, int(4 * a))
            inner_w = max(1, int(2 * a))
            outer_col = (140, 180, 255, int(80 * a))
            mid_col = (180, 210, 255, int(180 * a))
            inner_col = (255, 255, 255, int(255 * a))
            for col, w in ((outer_col, outer_w),
                            (mid_col, mid_w),
                            (inner_col, inner_w)):
                if len(main_shift) >= 2:
                    pygame.draw.lines(glow_surf, col, False,
                                       main_shift, w)
            # Branches mit Decay-Alpha 0.6
            for bpath in getattr(b, 'branches', ()):
                if len(bpath) < 2:
                    continue
                bpts = [_shift(self.w2s(Vector2(x, y)))
                         for x, y in bpath]
                br_outer = (140, 180, 255, int(50 * a))
                br_mid = (180, 210, 255, int(110 * a))
                br_inner = (255, 255, 255, int(180 * a))
                br_outer_w = max(1, int(5 * a))
                br_mid_w = max(1, int(3 * a))
                br_inner_w = max(1, int(1 * a))
                pygame.draw.lines(glow_surf, br_outer, False,
                                   bpts, br_outer_w)
                pygame.draw.lines(glow_surf, br_mid, False,
                                   bpts, br_mid_w)
                pygame.draw.lines(glow_surf, br_inner, False,
                                   bpts, br_inner_w)
            self.screen.blit(glow_surf, (ox, oy))
        except (TypeError, ValueError):
            # Fallback auf simple polyline wenn Glow fehlschlägt
            try:
                pygame.draw.lines(self.screen, (180, 200, 255),
                                   False, pts, max(1, int(3 * a)))
            except (TypeError, ValueError):
                pass

    def _draw_arena_features(self):
        """E-05 (Update #60): Lava-Streams + Crypt-Graves rendern.

        Lava-Stream: pulsierender Lava-Glow am Boden (rot/orange).
        Crypt-Grave: bemooste Stele mit HP-Balken wenn beschädigt.
        Telegraph-Decals werden separat über das Decal-System gerendert.
        """
        for af in self.arena_features:
            kind = af.get('kind')
            sx, sy = self.w2s_xy(af['x'], af['y'])
            sx, sy = int(sx), int(sy)
            if -100 > sx or sx > SCREEN_W + 100:
                continue
            if -100 > sy or sy > SCREEN_H + 100:
                continue
            if kind == 'lava_stream':
                r = af['radius']
                pulse = 0.6 + 0.4 * abs(math.sin(
                    pygame.time.get_ticks() * 0.003))
                # Boden-Glut
                glow_size = r * 2
                glow = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
                for i in range(4, 0, -1):
                    a = int(60 / i * pulse)
                    pygame.draw.circle(glow, (255, 100, 30, a),
                                       (r, r), r - i * 4)
                self.screen.blit(glow, (sx - r, sy - r))
                # Lava-Mund (zentrierter heller Kreis)
                pygame.draw.circle(self.screen, (255, 180, 50),
                                   (sx, sy), 8)
                pygame.draw.circle(self.screen, (255, 230, 130),
                                   (sx - 2, sy - 2), 3)
            elif kind == 'crypt_grave':
                destroyed = af.get('destroyed', False)
                if destroyed:
                    # Zerschmettert: ein paar Salz-Bruchstücke
                    pygame.draw.rect(self.screen, (60, 50, 44),
                                      (sx - 8, sy + 4, 16, 6))
                    pygame.draw.circle(self.screen, (90, 80, 70),
                                        (sx - 6, sy + 2), 3)
                    pygame.draw.circle(self.screen, (90, 80, 70),
                                        (sx + 5, sy + 1), 3)
                else:
                    # Gravestone-Silhouette
                    pygame.draw.rect(self.screen, (110, 100, 90),
                                      (sx - 8, sy - 4, 16, 12))
                    pygame.draw.circle(self.screen, (110, 100, 90),
                                        (sx, sy - 4), 8)
                    pygame.draw.rect(self.screen, (10, 8, 6),
                                      (sx - 8, sy - 4, 16, 12), 1)
                    # Salzkruste (kleine helle Patches)
                    pygame.draw.circle(self.screen, (220, 230, 240),
                                        (sx - 3, sy - 1), 1)
                    pygame.draw.circle(self.screen, (220, 230, 240),
                                        (sx + 4, sy + 3), 1)
                    # HP-Bar wenn beschädigt
                    if af['hp'] < af['hp_max']:
                        pct = af['hp'] / af['hp_max']
                        pygame.draw.rect(self.screen, (40, 30, 20),
                                          (sx - 12, sy - 16, 24, 3))
                        pygame.draw.rect(self.screen, (220, 230, 240),
                                          (sx - 12, sy - 16,
                                           int(24 * pct), 3))
            elif kind == 'ice_pillar':
                # E-11: vertical kristall mit pulsierendem Glow
                if af.get('destroyed', False):
                    # Bruchstücke
                    for _i in range(3):
                        pygame.draw.polygon(self.screen, (160, 200, 230), [
                            (sx - 6 + _i * 5, sy + 4),
                            (sx - 3 + _i * 5, sy - 1),
                            (sx + _i * 5, sy + 4),
                        ])
                else:
                    pulse = 0.6 + 0.4 * abs(math.sin(
                        pygame.time.get_ticks() * 0.002))
                    # Halo
                    halo = pygame.Surface((40, 40), pygame.SRCALPHA)
                    pygame.draw.circle(halo, (180, 220, 255,
                                              int(50 * pulse)),
                                       (20, 20), 18)
                    self.screen.blit(halo, (sx - 20, sy - 20))
                    # Spike-Polygon
                    pygame.draw.polygon(self.screen, (200, 230, 255), [
                        (sx, sy - 22), (sx + 7, sy - 5),
                        (sx + 4, sy + 8), (sx - 4, sy + 8),
                        (sx - 7, sy - 5),
                    ])
                    pygame.draw.polygon(self.screen, (255, 255, 255), [
                        (sx, sy - 18), (sx + 3, sy - 8), (sx, sy - 2),
                        (sx - 3, sy - 8),
                    ])
                    pygame.draw.polygon(self.screen, (10, 8, 6), [
                        (sx, sy - 22), (sx + 7, sy - 5),
                        (sx + 4, sy + 8), (sx - 4, sy + 8),
                        (sx - 7, sy - 5),
                    ], 1)
                    if af['hp'] < af['hp_max']:
                        pct = af['hp'] / af['hp_max']
                        pygame.draw.rect(self.screen, (40, 30, 20),
                                          (sx - 12, sy - 30, 24, 3))
                        pygame.draw.rect(self.screen, (200, 230, 255),
                                          (sx - 12, sy - 30,
                                           int(24 * pct), 3))
            elif kind == 'spore_vent':
                # E-11: Pilz-Vent mit Sporen-Cloud wenn erupting
                erupting = af.get('erupting', False)
                erupt_t = af.get('erupt_t', 0.0)
                # Stein-Vent
                pygame.draw.ellipse(self.screen, (50, 40, 30),
                                     (sx - 14, sy + 2, 28, 10))
                pygame.draw.ellipse(self.screen, (10, 8, 6),
                                     (sx - 14, sy + 2, 28, 10), 1)
                # Pilz-Kappe
                pygame.draw.circle(self.screen, (140, 80, 60),
                                    (sx, sy - 4), 9)
                pygame.draw.circle(self.screen, (200, 130, 100),
                                    (sx, sy - 4), 7)
                # Erupt-Cloud (transient)
                if erupting:
                    r = int(af['radius'] * (1.0 - erupt_t / 0.8))
                    a = int(120 * (1.0 - erupt_t / 0.8))
                    cloud = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
                    pygame.draw.circle(cloud, (140, 200, 100, a),
                                       (r, r), r)
                    self.screen.blit(cloud, (sx - r, sy - r))
            elif kind == 'mirror_echo':
                # E-11: stehender Spiegel mit pulsierendem Lila-Glow
                if af.get('destroyed', False):
                    # Zerbrochen
                    for _i in range(4):
                        ox = (_i - 1.5) * 6
                        pygame.draw.polygon(self.screen, (130, 110, 160), [
                            (sx + ox, sy + 4),
                            (sx + ox + 3, sy - 2),
                            (sx + ox + 5, sy + 4),
                        ])
                else:
                    pulse = 0.6 + 0.4 * abs(math.sin(
                        pygame.time.get_ticks() * 0.0025))
                    halo = pygame.Surface((48, 48), pygame.SRCALPHA)
                    pygame.draw.circle(halo,
                                       (220, 180, 255, int(60 * pulse)),
                                       (24, 24), 22)
                    self.screen.blit(halo, (sx - 24, sy - 24))
                    # Mirror-Rahmen (Hochformat-Oval)
                    pygame.draw.ellipse(self.screen, (60, 40, 90),
                                         (sx - 8, sy - 18, 16, 28))
                    # Innen-Spiegel (heller pulsierender Kern)
                    inner_col = (200 + int(40 * pulse),
                                  170 + int(50 * pulse),
                                  255)
                    pygame.draw.ellipse(self.screen, inner_col,
                                         (sx - 5, sy - 14, 10, 22))
                    pygame.draw.ellipse(self.screen, (10, 8, 6),
                                         (sx - 8, sy - 18, 16, 28), 1)
                    if af['hp'] < af['hp_max']:
                        pct = af['hp'] / af['hp_max']
                        pygame.draw.rect(self.screen, (40, 30, 20),
                                          (sx - 12, sy - 26, 24, 3))
                        pygame.draw.rect(self.screen, (220, 180, 255),
                                          (sx - 12, sy - 26,
                                           int(24 * pct), 3))

    # ----- Update #96: NPC-Hover-Tooltip -----
    _NPC_ROLE_DESC = {
        'vendor':    ('Händler', 'Kauft und verkauft Waren.'),
        'stash':     ('Verwahrer', 'Verwaltet deine Truhe.'),
        'mystic':    ('Mahnerin', 'Mahnmal-Wissen und Talente.'),
        'smith':     ('Gemcutter', 'Graviert Uncut-Steine.'),
        'quest':     ('Stadtsprecher', 'Vergibt Aufträge.'),
        'innkeeper': ('Wirtin', 'Bietet Rast und Geschichten.'),
    }

    def _draw_npc_hover_tooltip(self):
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            return
        hovered = None
        for npc in getattr(self, 'npcs', ()):
            sx, sy = self.w2s(npc.pos)
            if (sx - mx) ** 2 + (sy - my) ** 2 < 30 * 30:
                hovered = npc
                break
        if hovered is None:
            return
        role_name, role_desc = self._NPC_ROLE_DESC.get(
            hovered.kind, ('NPC', ''))
        font = self.font_small
        line_h = font.get_height() + 2
        lines = [
            (hovered.name,                 (243, 213, 114), font),
            (f'[{role_name}]',              (180, 160, 130), font),
        ]
        if role_desc:
            lines.append((role_desc, (210, 200, 180), font))
        # Quest-Hinweis wenn aktive Quest auf diesen NPC zeigt
        log = getattr(self, 'quest_log', None)
        if log is not None and log.has_quest_for_npc(hovered.name,
                                                     talk_only=True):
            lines.append(('★ Quest hier', (140, 230, 140), font))
        max_w = max(s[2].size(s[0])[0] for s in lines)
        box_w = max_w + 22
        box_h = len(lines) * line_h + 14
        tx = mx + 16
        ty = my + 16
        if tx + box_w > SCREEN_W - 8:
            tx = mx - box_w - 16
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((14, 10, 8, 245))
        self.screen.blit(bg, (tx, ty))
        pygame.draw.rect(self.screen, (180, 140, 80),
                          (tx, ty, box_w, box_h), 2)
        cy = ty + 7
        for text, col, fnt in lines:
            self.screen.blit(fnt.render(text, True, col), (tx + 11, cy))
            cy += line_h

    # ----- Update #89: Enemy-Hover-Tooltip -----
    def _draw_enemy_hover_tooltip(self):
        """POE2-Style Enemy-Inspect-Tooltip beim Mouse-Hover.
        Zeigt Name + Rarity + Affixes + HP-% + Status-Pips."""
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            return
        hovered = None
        for e in self.enemies:
            if e.dying:
                continue
            sx, sy = self.w2s(e.pos)
            # Hit-Radius ~ Enemy-Radius + 4 in Screen-Coords
            if (sx - mx) ** 2 + (sy - my) ** 2 < (e.radius + 4) ** 2:
                hovered = e
                break
        if hovered is None:
            return
        e = hovered
        # Rarity-Klassifikation
        if e.is_boss:
            rarity_label = 'BOSS'
            rarity_col = (220, 80, 80)
        elif getattr(e, 'is_mini_boss', False):
            rarity_label = 'MINI-BOSS'
            rarity_col = (255, 160, 80)
        elif getattr(e, 'elite', False):
            af = getattr(e, 'affixes', None) or []
            if len(af) >= 5:
                rarity_label = 'UNIQUE'
                rarity_col = (220, 120, 60)
            elif len(af) >= 2:
                rarity_label = 'RARE'
                rarity_col = (240, 220, 100)
            else:
                rarity_label = 'MAGIC'
                rarity_col = (120, 160, 240)
        else:
            rarity_label = 'NORMAL'
            rarity_col = (200, 200, 200)
        # Name aus Bestiarium/display_name oder type_key
        name = (getattr(e, 'boss_name', None)
                 or getattr(e, 'display_name', None)
                 or getattr(e, 'type_key', 'Wesen'))
        # Affix-Namen auflösen
        affix_names = []
        try:
            from . import enemies as _en
            for ak in getattr(e, 'affixes', []) or []:
                spec = _en.AFFIX_POOL.get(ak)
                if spec:
                    affix_names.append((spec['name'], spec['color']))
        except Exception:
            pass
        # Layout
        font = self.font_small
        line_h = font.get_height() + 2
        lines = []
        # Header: Name (color = rarity)
        lines.append((str(name), rarity_col, font))
        # Rarity-Tag dim
        lines.append((f'[{rarity_label}]', rarity_col, font))
        # HP-Prozent
        if e.hp_max > 0:
            hp_pct = int(100 * e.hp / e.hp_max)
            lines.append((f'HP: {hp_pct}%  ({int(e.hp)}/{int(e.hp_max)})',
                           (220, 200, 180), font))
        # Affixes
        for an, acol in affix_names:
            lines.append((f'· {an}', acol, font))
        # Status-Effekte
        status = getattr(e, 'status', None) or {}
        if status:
            keys = list(status.keys())[:6]
            lines.append((f'Effekte: {", ".join(keys)}',
                           (200, 200, 240), font))
        # Box
        max_w = max((s[2].size(s[0])[0] for s in lines), default=0)
        box_w = max_w + 22
        box_h = len(lines) * line_h + 14
        tx = mx + 16
        ty = my + 16
        if tx + box_w > SCREEN_W - 8:
            tx = mx - box_w - 16
        if ty + box_h > SCREEN_H - 8:
            ty = SCREEN_H - box_h - 8
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((14, 10, 8, 245))
        self.screen.blit(bg, (tx, ty))
        pygame.draw.rect(self.screen, rarity_col, (tx, ty, box_w, box_h), 2)
        cy = ty + 7
        for text, col, fnt in lines:
            self.screen.blit(fnt.render(text, True, col), (tx + 11, cy))
            cy += line_h

    # ----- Update #83: Loot-Hover-Tooltip -----
    _RARITY_COLOR = {
        'common': (200, 200, 200),
        'magic':  (120, 160, 240),
        'rare':   (240, 220, 100),
        'unique': (220, 120, 60),
    }
    _AFFIX_COLOR = {
        'affix':  (180, 230, 200),
        'dim':    (160, 150, 130),
        'gem':    (170, 120, 240),
    }

    def _draw_hover_outlines(self):
        """Update #138 (M-19): POE2-Style Hover-Outline auf Items / Mobs /
        Interactables.  Vor den Tooltips gerendert, gibt visuelles
        „Mein Cursor ist hier"-Feedback bevor Spieler die Maustaste
        drückt.

        Outline-Farben (Lore-konform):
          - Item-Loot: Rarity-Color (common grau, magic blau, rare gelb,
            unique orange)
          - Mobs: Rarity-Color basierend auf elite/affix_tier
          - NPC / Stelen / Lore-Tablets: cyan (interactable)

        Pulse: 0.6 + 0.4 × |sin(t · 3.0)|
        """
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            return
        # Pulse-Faktor
        t = pygame.time.get_ticks() * 0.005
        puls = 0.6 + 0.4 * abs(math.sin(t * 3.0))
        # 1. Loot-Hover
        for l in self.loot:
            sx, sy = self.w2s(l.pos)
            sy += math.sin(l.bob) * 2
            if (sx - mx) ** 2 + (sy - my) ** 2 < 18 * 18:
                if l.kind == 'item' and l.item is not None:
                    col = self._RARITY_COLOR.get(
                        l.item.rarity, (200, 200, 200))
                elif l.kind == 'skill_gem':
                    col = (200, 150, 240)
                elif l.kind == 'vital_orb':
                    col = (240, 130, 160)
                elif l.kind == 'gem':
                    col = l.color
                else:  # gold
                    col = (255, 215, 90)
                # 3-Layer pulse-Ring um den Loot-Dot
                a = int(180 + 60 * puls)
                outline = pygame.Surface((44, 44), pygame.SRCALPHA)
                pygame.draw.circle(outline, (*col, a),
                                    (22, 22), int(14 + puls * 3), 2)
                pygame.draw.circle(outline, (*col, a // 2),
                                    (22, 22), int(18 + puls * 4), 1)
                self.screen.blit(outline, (int(sx) - 22, int(sy) - 22))
                break
        # 2. Enemy-Hover
        for e in self.enemies:
            sx, sy = self.w2s(e.pos)
            dx = sx - mx
            dy = sy - my
            if dx * dx + dy * dy < (e.radius + 8) ** 2:
                # Threat-Color: Boss=rot, Elite/Affix=orange, sonst rot-dim
                # Update #143: `affix_tier` ist ein STRING ('magic'/
                # 'rare'/'unique') oder None — KEIN int.  Mein vorheriger
                # `>= 2`-Compare war semantisch falsch und hat bei
                # affix_tier='rare' gecrashed.  Jetzt: String-Check
                # gegen Rare-/Unique-Tier-Namen.
                if getattr(e, 'is_boss', False):
                    col = (255, 80, 60)
                elif (getattr(e, 'elite', False)
                      or getattr(e, 'affix_tier', None)
                          in ('rare', 'unique')):
                    col = (255, 160, 80)
                elif getattr(e, 'is_mini_boss', False):
                    col = (255, 100, 100)
                else:
                    col = (220, 130, 100)
                r = int(e.radius + 4 + puls * 3)
                outline = pygame.Surface((r * 2 + 8, r * 2 + 8),
                                          pygame.SRCALPHA)
                a = int(160 + 80 * puls)
                pygame.draw.circle(outline, (*col, a),
                                    (r + 4, r + 4), r, 2)
                pygame.draw.circle(outline, (*col, a // 2),
                                    (r + 4, r + 4), r + 3, 1)
                self.screen.blit(outline, (int(sx) - r - 4,
                                            int(sy) - r - 4))
                break
        # 3. Decor-Hover (Interactables: lore_tablet, mahnmal_stele,
        #    altar, rune_circle)
        INTERACT_KINDS = {'lore_tablet', 'mahnmal_stele', 'altar',
                          'rune', 'rune_circle'}
        for d in getattr(self, 'tiles', ()):
            if getattr(d, 'kind', None) not in INTERACT_KINDS:
                continue
            sx, sy = self.w2s_xy(d.x, d.y)
            dx = sx - mx
            dy = sy - my
            if dx * dx + dy * dy < 22 * 22:
                col = (90, 220, 255)   # cyan = interactable
                r = int(18 + puls * 4)
                outline = pygame.Surface((r * 2 + 8, r * 2 + 8),
                                          pygame.SRCALPHA)
                a = int(180 + 60 * puls)
                pygame.draw.circle(outline, (*col, a),
                                    (r + 4, r + 4), r, 2)
                self.screen.blit(outline, (int(sx) - r - 4,
                                            int(sy) - r - 4))
                break

    def _draw_loot_hover_tooltip(self):
        """Findet das Loot-Item unter dem Mauszeiger und rendert dessen
        Item.display_lines als POE2-Style-Tooltip."""
        try:
            mx, my = pygame.mouse.get_pos()
        except Exception:
            return
        # Suche nach Loot in 18 px Screen-Radius
        hovered = None
        for l in self.loot:
            if l.kind != 'item' or l.item is None:
                continue
            sx, sy = self.w2s(l.pos)
            sy += math.sin(l.bob) * 2
            if (sx - mx) ** 2 + (sy - my) ** 2 < 18 * 18:
                hovered = l
                break
        if hovered is None:
            return
        item = hovered.item
        lines = item.display_lines()
        font = self.font_small
        line_h = font.get_height() + 2
        max_w = 0
        for (text, _kind) in lines:
            if isinstance(text, str):
                w = font.size(text)[0]
                if w > max_w:
                    max_w = w
        box_w = max_w + 24
        box_h = len(lines) * line_h + 16
        # Tooltip neben Cursor (rechts unten); falls über Bildschirm-Kante
        # nach links flippen.
        tx = mx + 16
        ty = my + 16
        if tx + box_w > SCREEN_W - 8:
            tx = mx - box_w - 16
        if ty + box_h > SCREEN_H - 8:
            ty = SCREEN_H - box_h - 8
        # Background
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((12, 10, 8, 240))
        self.screen.blit(bg, (tx, ty))
        rarity = item.rarity
        border = self._RARITY_COLOR.get(rarity, (200, 200, 200))
        pygame.draw.rect(self.screen, border, (tx, ty, box_w, box_h), 2)
        # Lines rendern
        y = ty + 8
        for (text, kind) in lines:
            if not isinstance(text, str):
                y += line_h
                continue
            if kind in self._RARITY_COLOR:
                col = self._RARITY_COLOR[kind]
            elif kind in self._AFFIX_COLOR:
                col = self._AFFIX_COLOR[kind]
            else:
                col = (220, 210, 190)
            self.screen.blit(font.render(text, True, col), (tx + 12, y))
            y += line_h

    def _draw_loot(self, l):
        sx, sy = self.w2s(l.pos)
        sy += math.sin(l.bob) * 2
        sx, sy = int(sx), int(sy)
        # Update #33 / #133 (M-20): Loot-Beam jetzt POE2-mäßig als vertikale
        # Lichtsäule mit Boden-Halo + Top-Twinkle.  Set-Items (item.set_id)
        # bekommen einen Grünton-Override.  Rare/Unique-Säulen sind höher
        # und intensiver (besseres Loot-Spotting in Dungeons).
        beam_cfg = None
        is_set = False
        if l.kind == 'item' and l.item is not None:
            is_set = (getattr(l.item, 'set_id', None) is not None)
            if l.item.rarity == 'unique':
                beam_cfg = (360, 32)   # höhe, breite
            elif l.item.rarity == 'rare':
                beam_cfg = (280, 22)
            elif l.item.rarity == 'magic':
                beam_cfg = (200, 14)
        elif l.kind == 'skill_gem':
            beam_cfg = (300, 24)
        if beam_cfg is not None:
            beam_h, beam_w = beam_cfg
            pulse = 0.6 + 0.4 * abs(math.sin(l.bob))
            # Set-Items: Grünton-Override (PLAN M-20)
            beam_color = (90, 220, 130) if is_set else l.color
            # Update #133 (M-20): Boden-Halo unter dem Loot — verstärkt das
            # „hier liegt was gutes"-Signal.
            halo_r = max(14, beam_w + 8)
            halo = pygame.Surface((halo_r * 2, halo_r), pygame.SRCALPHA)
            for k in range(4, 0, -1):
                a = int(60 / k * pulse)
                pygame.draw.ellipse(halo, (*beam_color, a),
                                     (k * 2, k, halo_r * 2 - k * 4,
                                      halo_r - k * 2))
            self.screen.blit(halo, (sx - halo_r, sy - halo_r // 2 + 6))
            # Vertikale Lichtsäule — POE2-Style (weniger spitz, mehr Säule).
            # Maximum alpha am Boden, langsamer Fade nach oben.
            beam = pygame.Surface((beam_w * 2, beam_h), pygame.SRCALPHA)
            for k in range(beam_h):
                t = k / beam_h
                # Nicht-linearer Fade — bleibt unten lange hell
                fade = max(0.0, 1.0 - t * t * 1.4)
                a = int(190 * fade * pulse)
                # Nur leichte Verjüngung nach oben (statt halbierter Breite)
                w = int(beam_w * (1 - t * 0.25))
                pygame.draw.rect(beam, (*beam_color, a),
                                 (beam_w - w, k, w * 2, 1))
            self.screen.blit(beam, (sx - beam_w, sy - beam_h + 8))
            # Update #133 (M-20): Twinkle-Stern am Top der Säule.
            twinkle_y = sy - beam_h + 12
            twinkle_size = int(3 + 2 * pulse)
            ts = pygame.Surface((twinkle_size * 4, twinkle_size * 4),
                                  pygame.SRCALPHA)
            # 4-Strahl-Stern
            pygame.draw.line(ts, (*beam_color, int(200 * pulse)),
                              (twinkle_size * 2, 0),
                              (twinkle_size * 2, twinkle_size * 4), 1)
            pygame.draw.line(ts, (*beam_color, int(200 * pulse)),
                              (0, twinkle_size * 2),
                              (twinkle_size * 4, twinkle_size * 2), 1)
            pygame.draw.circle(ts, (255, 255, 240),
                                (twinkle_size * 2, twinkle_size * 2),
                                twinkle_size)
            self.screen.blit(ts, (sx - twinkle_size * 2,
                                    twinkle_y - twinkle_size * 2))
            # Aufsteigende Funken-Partikel für Rare+ (sehr vereinzelt)
            if (l.kind == 'item' and l.item.rarity in ('rare', 'unique')
                    and random.random() < 0.06):
                self.particles.append(Particle(
                    l.pos.x + random.uniform(-8, 8),
                    l.pos.y - random.uniform(0, 30),
                    random.uniform(-10, 10), random.uniform(-40, -20),
                    beam_color, random.uniform(0.6, 1.2),
                    random.uniform(2, 4), gravity=-30))
        # Update #205: Loot ~2x skaliert wegen neuer 84x124-Char-Skala.
        # Vorher waren 4-7px-Items neben 124-px-Chars optisch winzig.
        glow = pygame.Surface((80, 80), pygame.SRCALPHA)
        for i in range(5, 0, -1):
            alpha = 80 // i
            pygame.draw.circle(glow, (*l.color, alpha), (40, 40), i * 7)
        self.screen.blit(glow, (sx - 40, sy - 40))
        if l.kind == 'gold':
            # Gold-Muenzen-Stack (mehrere Coins)
            for dy_, r_ in ((0, 9), (-3, 7), (-5, 5)):
                pygame.draw.circle(self.screen, l.color, (sx, sy + dy_), r_)
                pygame.draw.circle(self.screen, (10, 6, 4),
                                    (sx, sy + dy_), r_, 1)
            # Highlight + Symbol auf Top-Coin
            pygame.draw.circle(self.screen, (255, 240, 180),
                                (sx - 3, sy - 7), 2)
            pygame.draw.line(self.screen, (180, 120, 30),
                              (sx - 2, sy - 5), (sx + 2, sy - 5), 1)
        elif l.kind == 'vital_orb':
            # Update #96: Pulsierende rosé Sphäre, jetzt deutlich groesser
            t = pygame.time.get_ticks() * 0.005
            pulse = 0.7 + 0.3 * math.sin(t + l.bob)
            r = int(12 + 3 * pulse)
            glow = pygame.Surface((r * 4, r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*l.color, int(80 * pulse)),
                                (r * 2, r * 2), r * 2)
            self.screen.blit(glow, (sx - r * 2, sy - r * 2))
            pygame.draw.circle(self.screen, l.color, (sx, sy), r)
            pygame.draw.circle(self.screen, (10, 6, 4), (sx, sy), r, 1)
            # Inner Highlight
            pygame.draw.circle(self.screen, (255, 230, 240),
                                (sx - 3, sy - 3), max(2, r // 3))
            # Inner Core
            pygame.draw.circle(self.screen, (255, 255, 255),
                                (sx - 4, sy - 4), 2)
        elif l.kind == 'item':
            # Update #205: Detaillierter Diamant-Item-Marker.
            # Doppel-Kontur (dunkel innen, hell aussen) fuer Plastizitaet.
            outer_pts = [(sx, sy - 14), (sx + 12, sy),
                          (sx, sy + 14), (sx - 12, sy)]
            inner_pts = [(sx, sy - 10), (sx + 8, sy),
                          (sx, sy + 10), (sx - 8, sy)]
            # Schatten unter dem Item
            sh = pygame.Surface((30, 10), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 140), (0, 0, 30, 10))
            self.screen.blit(sh, (sx - 15, sy + 10))
            # Outer-Glow-Ring (rarity-color)
            pygame.draw.polygon(self.screen, l.color, outer_pts)
            pygame.draw.polygon(self.screen, (10, 6, 4), outer_pts, 2)
            # Inner-Fill (heller)
            from .sprites import _shade
            inner_col = _shade(l.color, 1.35)
            pygame.draw.polygon(self.screen, inner_col, inner_pts)
            # Highlight-Glanz (oben links)
            pygame.draw.polygon(self.screen, (255, 255, 255), [
                (sx - 5, sy - 4), (sx - 2, sy - 7),
                (sx, sy - 5), (sx - 3, sy - 2),
            ])
            # Cross-Linien (Facetten)
            pygame.draw.line(self.screen, l.color,
                              (sx, sy - 10), (sx, sy + 10), 1)
            pygame.draw.line(self.screen, l.color,
                              (sx - 8, sy), (sx + 8, sy), 1)
            # Update #57: POE2-Style Ground-Label.  Item-Name + Rarity-Tint
            # über dem Loot wenn Player im 240 px-Radius ist.  Drop-Grace
            # zeigt extra Hint („Klick zum Aufheben").
            # Update #92: Alt-Hold zeigt ALLE Labels (POE2-Style „highlight").
            if l.item is not None:
                dist = (l.pos - self.player.pos).length()
                _alt_held = getattr(self, '_loot_alt_held', False)
                if dist < 240 or _alt_held:
                    name_surf = self.font_small.render(
                        l.item.name, True, l.color)
                    bg_w = name_surf.get_width() + 10
                    bg_h = name_surf.get_height() + 4
                    bg_x = sx - bg_w // 2
                    bg_y = sy - 26 - bg_h
                    name_bg = pygame.Surface((bg_w, bg_h), pygame.SRCALPHA)
                    name_bg.fill((10, 8, 6, 200))
                    self.screen.blit(name_bg, (bg_x, bg_y))
                    pygame.draw.rect(self.screen, l.color,
                                      (bg_x, bg_y, bg_w, bg_h), 1)
                    self.screen.blit(name_surf,
                                      (bg_x + 5, bg_y + 2))
                    # Drop-Grace-Hinweis: „warte..."
                    if getattr(l, '_drop_grace_t', 0) > 0:
                        hint = self.font_small.render(
                            f'({l._drop_grace_t:.1f}s)',
                            True, (180, 160, 110))
                        self.screen.blit(hint,
                                          (sx - hint.get_width() // 2,
                                           bg_y - hint.get_height() - 2))
        elif l.kind == 'gem':
            # Update #205: Hexagonaler Edelstein, deutlich groesser + Facetten
            # Schatten
            sh = pygame.Surface((28, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 140), (0, 0, 28, 8))
            self.screen.blit(sh, (sx - 14, sy + 10))
            pts = []
            for k in range(6):
                a = k * math.pi / 3 - math.pi / 2
                pts.append((sx + math.cos(a) * 12, sy + math.sin(a) * 12))
            pygame.draw.polygon(self.screen, l.color, pts)
            pygame.draw.polygon(self.screen, (10, 6, 4), pts, 2)
            # Inner-Hex (lighter)
            from .sprites import _shade
            inner_col = _shade(l.color, 1.35)
            inner_pts = []
            for k in range(6):
                a = k * math.pi / 3 - math.pi / 2
                inner_pts.append((sx + math.cos(a) * 8, sy + math.sin(a) * 8))
            pygame.draw.polygon(self.screen, inner_col, inner_pts)
            # Facetten-Linien (Center → Vertex)
            for k in range(6):
                a = k * math.pi / 3 - math.pi / 2
                pygame.draw.line(self.screen, l.color,
                                  (sx, sy),
                                  (sx + math.cos(a) * 11,
                                   sy + math.sin(a) * 11), 1)
            # Highlight oben
            pygame.draw.circle(self.screen, (255, 255, 255),
                                (sx - 3, sy - 4), 2)
            pygame.draw.circle(self.screen, (255, 255, 255),
                                (sx - 3, sy - 4), 1)
        elif l.kind == 'skill_gem':
            # Update #205: Skill-Gem deutlich groesser + Star-Pulsation
            pulse = abs(math.sin(pygame.time.get_ticks() * 0.005))
            glow_r = 32 + int(pulse * 6)
            glow_big = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(glow_big, (*l.color, 180),
                                (glow_r, glow_r), glow_r)
            self.screen.blit(glow_big, (sx - glow_r, sy - glow_r))
            # Schatten
            sh = pygame.Surface((30, 8), pygame.SRCALPHA)
            pygame.draw.ellipse(sh, (0, 0, 0, 140), (0, 0, 30, 8))
            self.screen.blit(sh, (sx - 15, sy + 16))
            # Outer-Kristall (Raute)
            outer_pts = [(sx, sy - 18), (sx + 13, sy),
                          (sx, sy + 18), (sx - 13, sy)]
            pygame.draw.polygon(self.screen, l.color, outer_pts)
            pygame.draw.polygon(self.screen, (10, 6, 4), outer_pts, 2)
            # Inner-Kristall (lighter)
            from .sprites import _shade
            inner_col = _shade(l.color, 1.40)
            inner_pts = [(sx, sy - 12), (sx + 9, sy),
                          (sx, sy + 12), (sx - 9, sy)]
            pygame.draw.polygon(self.screen, inner_col, inner_pts)
            # Highlight-Sheen
            pygame.draw.polygon(self.screen, (255, 255, 255), [
                (sx - 7, sy - 4), (sx - 2, sy - 10),
                (sx + 1, sy - 6), (sx - 4, sy - 1),
            ])
            # Stern in der Mitte (mit Glow)
            for r_, col_ in ((5, l.color), (3, inner_col), (2, (255, 255, 255))):
                pygame.draw.line(self.screen, col_,
                                  (sx - r_, sy), (sx + r_, sy), 1)
                pygame.draw.line(self.screen, col_,
                                  (sx, sy - r_), (sx, sy + r_), 1)

    def _draw_particle(self, p):
        a = 1 - p.age / p.life
        if a <= 0:
            return
        sx, sy = self.w2s(p.pos)
        size = max(1, int(p.size * a))
        color = (*p.color[:3], int(255 * a))
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (size, size), size)
        self.screen.blit(surf, (sx - size, sy - size))

    def _draw_floater(self, f):
        sx, sy = self.w2s(f.pos)
        a = 1 - f.age / f.life
        is_big = getattr(f, 'big', False)
        is_crit = getattr(f, 'crit', False)
        is_heal = getattr(f, 'heal', False)
        is_dot = getattr(f, 'dot', False)
        # PLAN G-10: Crit-Pop-Scale (Skala 1.4 → 1.0 über erstes 0.25 s).
        # Heal: grüner Tint + bisschen langsamere Velocity (gemacht in caller).
        # DoT: halbe Alpha (gedeckt).
        # Versuche numerisch zu parsen für extra-large bei >100 Schaden
        # Update #36: Schrift-Sizes kompakter
        # - Crit/Big: font_big_dmg (28pt) statt font_big (72pt!)
        # - Normal-Hits: font_dmg (18pt) statt 20pt
        try:
            n = int(''.join(c for c in str(f.text)
                              if c.isdigit() or c == '-'))
            if is_big:
                font = self.font_big_dmg
            else:
                font = self.font_dmg
        except (ValueError, TypeError):
            font = self.font_big_dmg if is_big else self.font_dmg
        # Outline: text mit schwarzem Schatten 4x rendern
        # M-09 (Update #51): Damage-Numbers gedeckter (kein D4-Hyperscale).
        # Outline-Alpha 220 → 180, Crit-Outline-Farbe gedämpft.
        out_col = (140, 50, 16) if is_crit else (0, 0, 0)
        outline = font.render(f.text, True, out_col)
        outline_alpha = int(180 * a)
        if is_dot:
            outline_alpha = int(outline_alpha * 0.55)
        outline.set_alpha(outline_alpha)
        x = sx - outline.get_width() / 2
        # M-09: Outline-Offsets von 2 px → 1 px (weniger fett)
        for ox, oy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            self.screen.blit(outline, (x + ox, sy + oy))
        # Haupttext (mit Crit-Pop-Scale für die ersten 0.25 s)
        col = f.color
        if is_heal:
            col = (120, 220, 130)
        surf = font.render(f.text, True, col)
        # M-09: Crit-Pop 1.45× → 1.20× (gedeckter)
        if is_crit and f.age < 0.25:
            scale = 1.0 + (1.0 - f.age / 0.25) * 0.20
            new_w = max(1, int(surf.get_width() * scale))
            new_h = max(1, int(surf.get_height() * scale))
            try:
                surf = pygame.transform.smoothscale(surf, (new_w, new_h))
            except Exception:
                surf = pygame.transform.scale(surf, (new_w, new_h))
            x = sx - surf.get_width() / 2
        main_alpha = int(255 * a)
        if is_dot:
            main_alpha = int(main_alpha * 0.65)
        surf.set_alpha(main_alpha)
        self.screen.blit(surf, (x, sy))

    # ---------- Main loop ----------
    def run(self):
        pygame.mouse.set_visible(False)
        # Audit #179 C.13: section() context-manager misst pro Frame
        # update/draw/handle_events. Wird im F3-Overlay aggregiert (avg
        # ueber 60 Frames). Overhead pro Section <0.001 ms.
        _section = _profiler_mod.section
        while self.running:
            # P-05 (Update #52): Frame-Cap aus Settings (0 = unlimited)
            cap = int(self.settings.get('frame_cap', FPS) or 0)
            dt = min(0.05, self.clock.tick(cap if cap > 0 else 0) / 1000)
            with _section('events'):
                self.handle_events()
            with _section('update'):
                self.update(dt)
            with _section('draw'):
                self.draw()
        pygame.quit()


# N-05 (Update #51): Weapon-Impact-Identity-Lookup.
# Map class → (swing_sfx, impact_sfx).  `swing_sfx` läuft beim Anschwung,
# `impact_sfx` (optional) layered Material-Klang beim Treffer.
def _weapon_sound_pair(cls, heavy=False):
    """Returnt (swing_sfx, impact_sfx_or_None).

    Briefing 5.2 / Audio-Bibel 6.1:
    - Mace (warrior)        → Crunch + Sub-Bass-Tail
    - Quarterstaff (monk)   → Wood + Element-Sizzle
    - Wand (mage)           → Soft Cast
    - Dagger (witch)        → Quick Slice
    - Bow (ranger)          → Twang + Whoosh
    - Crossbow (rogue)      → Click + Thunk
    - Spear (huntress)      → Whip + Stab
    - Talisman (druid)      → Air-Sweep + Nature-Chime
    """
    if cls == 'warrior':
        return (f'greatsword_swing_{random.randint(1, 2)}',
                f'axe_metal_{random.randint(1, 4)}' if heavy else None)
    if cls == 'monk':
        return ('melee_swing', 'hit_heavy' if heavy else None)
    if cls == 'mage':
        return ('cast_lightning', None)  # Wand = Spell-Body
    if cls == 'witch':
        return ('melee_swing', 'hit' if heavy else None)
    if cls == 'ranger':
        return (f'arrow_impact_{random.randint(1, 2)}', None)
    if cls == 'rogue':
        return (f'arrow_impact_{random.randint(1, 2)}',
                'hit_heavy' if heavy else None)
    if cls == 'huntress':
        return ('melee_swing',
                'hit_heavy' if heavy else 'hit')
    if cls == 'druid':
        return (f'greatsword_swing_{random.randint(1, 2)}',
                'aoe_impact' if heavy else None)
    return ('melee_swing', None)


def main():
    # Update #137 (AA-03): Crash-Logger installieren VOR Game.__init__,
    # damit auch Init-Crashes geloggt werden.  Game-Referenz wird nach
    # dem Game-Constructor nachgereicht für State-Snapshot.
    from . import crash_logger as _crash
    _crash.install()
    # Update #202 (Perf-Fix): GL-Post-Pipeline standardmaessig AUS.
    # Begruendung: der Hybrid-Pfad lud jede Frame den kompletten
    # 1600x900-Screen via pygame.image.tostring() (~2.4 ms CPU) in eine
    # GL-Texture hoch + Shader-Pass + flip — ein fixer Per-Frame-Overhead,
    # der die "immense Performance-Probleme" mitverursacht hat.  Der
    # Color-Grade/Vignette/Bloom-Look wird bereits CPU-seitig durch
    # lighting.render_bloom + self._vignette + town_color_grading geliefert.
    # SCALED-Pfad (hardware-accel Integer-Scaling) ist der getestete,
    # scharfe Default.  GL bleibt opt-in via Game(use_gl_post=True).
    g = Game(use_gl_post=False)
    _crash.install(g)   # game-ref jetzt verfügbar
    # AA-05 (Update #168): Mod-Discovery
    if g.mod_loader is not None:
        try:
            g.mod_loader.discover_and_register(g)
            if g.mod_loader.loaded:
                for m in g.mod_loader.loaded:
                    print(f"Mod loaded: {m['name']} v{m['version']}")
        except Exception:
            pass
    # AA-07 (Update #168): Profiler-Start wenn dev_profiler-Flag
    try:
        from . import profiler as _prof
        _prof.maybe_start(g)
    except Exception:
        pass
    # AA-04 (Update #168): Telemetrie-Session-Start
    try:
        from . import telemetry as _tel
        _tel.record_session_start(g)
    except Exception:
        pass
    g.run()
    # AA-04: Telemetrie-Session-End
    try:
        from . import telemetry as _tel
        _tel.record_session_end(g)
    except Exception:
        pass
    # AA-07: Profiler-Dump
    try:
        from . import profiler as _prof
        _prof.maybe_stop_and_dump(g)
    except Exception:
        pass
