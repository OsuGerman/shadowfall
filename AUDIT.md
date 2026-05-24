# Shadowfall — Code-Audit

**Datum:** 2026-05-24
**Scope:** Voll-Audit aller 60+ Python-Files in `sf/` + Entry Points (`shadowfall.py`, `shadowfall2.py`)
**Codebase-Größe:** ~53.000 LoC
**Methode:** 5 parallele Explore-Agenten pro Subsystem + 1 Doc-Inventur

> Lies-Reihenfolge: Erst **Sektion A (Sofortmaßnahmen)** abarbeiten — alles dort ist klein, riskant zu lassen, einfach zu fixen. Danach **Sektion B (Strukturelle Probleme)** planen, das sind die großen Refactors. **Sektion C/D/E** sind Detail-Findings pro Subsystem als Nachschlagewerk.

---

## A. SOFORTMASSNAHMEN (Kleine Fixes, hoher Impact)

> **Status nach Verifikation (Update #179):** Von 13 Findings sind **6 false-positives** (Code war schon korrekt — der Audit hatte zu kleine Read-Fenster und übersah Update #106, F-12 etc.). Echte Fixes: A.1, A.3, A.5, A.12. A.6 ist kein Bug sondern Designentscheidung (jetzt im Code dokumentiert). False-Positives unten mit ❌ markiert.

### A.1 — `shadowfall.py` löschen (1071 Zeilen toter Prototyp) ✅ ARCHIVIERT
- **Status:** Verschoben nach `_archive/shadowfall.py`. Alter PoC, Entry Point ist `shadowfall2.py` → delegiert zu `sf.game.main`.

### A.2 — `Skills.md` löschen (exaktes Duplikat) ✅ GELÖSCHT
- **Status:** Bei MD-Migration entfernt (war Byte-für-Byte-Kopie von `POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md`).

### A.3 — Surface-Copy-Memory-Leak ✅ GEFIXT
- **Datei:** `sf/sprites.py:884-895`
- **Problem:** Bei `alpha < 255` UND `tint != None` wurden **zwei** `scaled.copy()` erzeugt; die erste wurde sofort überschrieben → Leak einer Surface pro Frame pro betroffenem Sprite.
- **Fix:** Konsolidierter `if needs_copy` Branch — eine Kopie, beide Modifikationen darauf.

### A.4 — Boss-Telegraph mit LOS-Check NACH Decal-Spawn ❌ FALSE POSITIVE
- **Datei:** `sf/enemies.py:499-506` (Caster) und `sf/enemies.py:1035-1044` (Charged Attack)
- **Verifikation:** **Update #106 hat den LOS-Check bereits vor Decal-Spawn (Caster) und vor Damage-Apply (Charged Attack) implementiert.** Kommentare im Code referenzieren explizit "Audit F-012" und "Audit F-008".
- **Bzgl. "Schaden gegen alte target_pos":** Das ist GEWOLLT — Boss schlägt auf fixen Punkt, Spieler hatte 1.2s zum Ausweichen. POE2-Standard.

### A.5 — `cast_teleport` Robustness ✅ GETWEAKT (war kein Crash)
- **Datei:** `sf/skills.py:814-820`
- **Verifikation:** Original-Code `if diff.length() < 1: return` fängt Null-Vektor bereits ab (0 < 1 = True). Kein Crash.
- **Tweak:** Auf `diff.length_squared() < 1.0` umgestellt — schneller (kein sqrt) + expliziter Vector2-Guard.

### A.6 — Boss-Shield: zwei Layer (kein Bug, war Design) ✅ DOKUMENTIERT
- **Datei:** `sf/combat.py:131-145` (`e.shield`) und `sf/combat.py:170-192` (`e.shield_hp`)
- **Verifikation:** Das sind zwei intentional getrennte Shield-Layer:
  - `e.shield` = Boss-Phase-Shield (`shield_max`-basiert, Sound `boss_shield`, gesetzt bei Phase-Trigger in `game.py:5080`)
  - `e.shield_hp` = Brute/Glaslord-Guardian-Buffer (PLAN F-12, `enemies.py:220-222`, einmalig, kein Regen)
- **Fix:** Klarstellungs-Kommentar in `combat.py:131-136` eingefügt. Refactor zu konsistenteren Namen → verschoben nach Sektion B (siehe B.8).

### A.7 — `wave_*` / Survival-Code-Reste ❌ FALSE POSITIVE (nur Doku-Kommentar)
- **Verifikation:** `grep` für `_update_waves`, `_spawn_wave_enemy`, `_next_wave`, `_spawn_portals` ergibt **0 Treffer**. Funktionen sind bereits entfernt. Der Kommentar in `game.py:5146-5150` ist Doku-Hinweis, kein Dead Code. Bleibt.

### A.8 — Bestiarium nicht spawnable ❌ FALSE POSITIVE
- **Verifikation:** `spawn_bestiary_mob()` ist auf **`sf/bestiary.py:691`** voll implementiert (~110 Zeilen mit `enemies.spawn_enemy`, Multipliers, Color/Glow). Der Audit hatte nur das Ende der Datei gesehen.

### A.9 — Skill-Dispatch-Lücken ❌ FALSE POSITIVE
- **Verifikation:**
  - `cast_lightning_arrow`, `cast_galvanic_shot`, `cast_lightning_spear` SIND in `CAST_DISPATCH` (`sf/skills.py:1966-1968`).
  - `class_keymap()` (`sf/skills.py:2017`), `class_skill_at()` (`sf/skills.py:2022`), `default_unlocked_for_class()` (`sf/skills.py:2030`) sind voll implementiert.
  - Die ~15 Warrior-Skills in `class_skills.py:46-129` sind absichtlich **data-only** (File-Header Z.17-18: *"Skill-Definitionen sind data-only — Cast-Implementation kommt iterativ. Bestehende cast_*-Funktionen in skills.py funktionieren weiterhin."*) — Roadmap im Code-Form.

### A.10 — `runes.py` Stub ❌ FALSE POSITIVE
- **Verifikation:** `runes.py` enthält `random_choice()`, `apply_rune()` (Z.33: `player.runes[skill_key] = rune_id`), `rune_label()` — alle voll implementiert. `rune_effect()` existiert nicht (war nie geplant — Rune-Logik wird in den cast-Funktionen ausgewertet, das ist das gewollte Pattern).

### A.11 — `aspects.py` ungenutzt ❌ FALSE POSITIVE
- **Verifikation:** `from . import aspects` taucht **32×** auf, in `game.py`, `lighting.py`, `inventory.py`, `sprites.py`, `combat.py`, `world.py`, `ui.py`. Eines der zentralsten Module — definitiv nicht ungenutzt.

### A.12 — `modloader.py` Pfad-Bug ✅ GEFIXT
- **Datei:** `sf/modloader.py:27-30`
- **Fix:** `MOD_DIR = str(Path(__file__).resolve().parent.parent / 'mods')` — absolut zum Projekt-Root.

### A.13 — Modloader-Crash-Isolation ❌ FALSE POSITIVE
- **Verifikation:** `_load_one()` (`sf/modloader.py:45-63`) HAT bereits try-except mit `traceback.print_exc()`. Ein crashender Mod blockiert nachfolgende nicht.

---

## B. STRUKTURELLE PROBLEME (Größere Refactors)

### B.1 — `sf/game.py` ist 11.321 Zeilen (Mega-File)
**Symptome:**
- 122 Methoden in einer Klasse
- 463 `screen.blit()` pro `_draw_world()`-Cycle
- ~80 bare `except Exception: pass`-Blöcke
- Nested O(n²)-Loops in Combat (`sf/game.py:4448-4490, 4537-4557`)

**Vorschlag (in dieser Reihenfolge):**
1. `game_render.py` — alle `_draw_*` Methoden raus (≈3000 Zeilen)
2. `game_update.py` — alle `_update_*` Methoden raus (≈3000 Zeilen)
3. `game_input.py` — Event-Handler raus
4. `game_modal.py` — Modal-State-Machine
5. `camera.py` — die 7 Offset-Quellen aus `sf/game.py:3960-4008` in dedizierte Klasse
6. `spatial_grid.py` — neue Klasse für O(1)-Lookups statt O(n)-Iteration über `self.enemies`

### B.2 — `sf/ui.py` ist 4556 Zeilen
**Symptome:**
- HUD, Skill-Tree-Modal, Death-Screen, Portal-Prompt, Boss-Bar alle in einem File
- ~465 Font-Renders pro Frame ohne Cache
- Quest-Tracker-Box zeichnet Gradient pixel-by-pixel (Z.1349-1355)

**Vorschlag:**
1. `ui/hud.py` — `draw_hud()` + Sub-`_draw_*`
2. `ui/skill_tree_ui.py` — `SkillTreeUI`-Klasse (ab Z.3463)
3. `ui/modals.py` — Death-Screen, Portal, Boss-Bar
4. `text_cache.py` — `@lru_cache` für Font-Renders pro (text, font, color)
5. Pre-rendered Gradient-Surfaces als Modul-Konstanten

### B.3 — `sf/sprites.py` ist 3304 Zeilen ✅ TEIL-UMGESETZT (Aliases)
**Umgesetzt:**
- 5 Alias-Maps (CLASS, MOB, TILE, PORTRAIT, BOSS) nach [sf/sprite_registry.py](sf/sprite_registry.py) verschoben, plus `resolve_*`-Helper-Funktionen.
- [sf/sprites.py](sf/sprites.py) importiert die Alias-Dicts (Backward-Compat) und nutzt die Helper für alle internen Mappings.
- `get_portrait()` und `get_boss_plate()` waren mit lokalen Dicts (in Function-Scope) — jetzt 4 Zeilen pro Funktion.

**Offen** (für separaten Sprint):
- Generischer Scaled-Surface-Cache statt `_STATUS_ICON_SCALED` + `_UNIQUE_ICON_SCALED`
- LRU-Bounds auf alle Sprite-Caches

### B.4 — Defensive Exception-Handling-Plage ✅ TEIL-UMGESETZT (Helper + Hot-Inits)
**Realität:** ~250 bare `except Exception: pass` Stellen — kompletter Cleanup wäre Multi-Day-Sprint.

**Umgesetzt:**
- **Trace-Helper** in [sf/crash_logger.py:152-189](sf/crash_logger.py#L152-L189) — `trace_swallowed(label)` schreibt swallowed exceptions in den Ring-Buffer wenn `SHADOWFALL_TRACE_SWALLOWED=1` (env). Null Overhead in Release. Damit können silent failures sichtbar gemacht werden, OHNE den bestehenden Code-Pfad zu ändern.
- **Lazy-Imports in Game.__init__** auf `(ImportError, AttributeError)` umgestellt ([sf/game.py:86-91, 168-184](sf/game.py#L86-L91)) — andere Exceptions aus Optional-Module-Konstruktoren würden ein echter Bug sein und propagieren jetzt.

**Offen** (für separaten Sprint):
- Systematisches Audit der ~250 bare-excepts mit dem neuen Trace-Helper als Werkzeug (Spiel mit `SHADOWFALL_TRACE_SWALLOWED=stderr` laufen lassen → sichtbare Liste echter Exception-Pfade).

### B.5 — Spatial-Lookups durchgehend linear ✅ UMGESETZT
**Stellen vorher:**
- `sf/game.py:4448-4490` — Fireball-AoE: O(n²)
- `sf/game.py:4537-4557` — Chain-on-Hit: O(n²)
- `sf/enemies.py:840-1070` — Ally-Loops in Enemy-Update: O(n²)
- `sf/game.py:3305-3327` — `_slide_against_decor()` O(n) pro Move
- `sf/inventory.py:513-524` — 30 `rect.collidepoint()`/Frame für Hover

**Umsetzung (Update #179):**
- Neue Klasse: [sf/spatial_grid.py](sf/spatial_grid.py) — Bucket-Grid, 128 px Cell-Size, rebuild O(N) pro Frame, query_radius() liefert Kandidaten.
- Integration: [sf/game.py:312-317](sf/game.py#L312-L317) (init), [sf/game.py:3573-3579](sf/game.py#L3573-L3579) (rebuild pro Frame).
- Umgestellte Hot-Paths:
  - Fireball-AoE: `enemy_grid.query_radius(proj.pos.x, proj.pos.y, aoe)`
  - Splash-on-Hit: `enemy_grid.query_radius(e.pos.x, e.pos.y, splash_r)`
  - Chain-on-Hit: `enemy_grid.query_radius(prev_pos.x, prev_pos.y, 240)`
  - Soul-Eater-Affix (`sf/combat.py:645-651`): `grid.query_radius(e.pos, 200)`
  - Pack-Death-Reactions (`sf/combat.py:670-680`): `grid.query_radius(e.pos, 220)`
- **Decor-Grid + Inventory-Hover skipped:** Decor ist statisch (geringer ROI vs Refactor), Inventory 30 Slots ist nicht in der heißen Schleife.

**Verifikation:** 197/197 Smoke-Tests grün. Live-Game-Run mit 30 Enemies × 60 Frames stabil. Erwartet bei 40+ Mobs: ~80% weniger Distance-Checks/Frame in den umgestellten Hot-Paths.

### B.6 — Particle/Surface-Allokationen pro Frame
**Stellen:**
- `sf/boss_encounter.py:622-630` — 36 Particles × 60 Phase-Transits = 2160 Allocs
- `sf/combat.py:257-296` — Blood-Spray 4-20 Particles × 3 nested Loops
- `sf/sprites.py:888, 895, 1297, 1317, 1335` — viele `Surface.copy()` und `Surface((w,h), SRCALPHA)` im Hotpath

**Vorschlag:** Object-Pool für (32×32, 64×64, 96×96)-Surfaces + Particle-Pool (existiert laut Update #298 in `sf/game.py:299`, wird aber nicht überall genutzt).

### B.7 — Save/Telemetry-Disk-I/O synchron im Mainthread ✅ UMGESETZT
**Telemetry** ([sf/telemetry.py](sf/telemetry.py)):
- Events gehen in `_QUEUE` (RAM), Background-Thread flusht alle 30 s oder wenn Queue ≥ 100.
- `atexit.register(shutdown_flusher)` garantiert finalen Flush.
- Vorher: sync `f.write()` PRO Event → bei 10 Events/s = 10 Disk-Writes/s im Main-Thread.

**Save** ([sf/save.py:34-145](sf/save.py#L34-L145)):
- `save_game()` bleibt **synchron** (atomic write-then-rename `_atomic_write_text`) — Tests und Load-Roundtrips erwarten konsistente Disk-Sichtbarkeit.
- `write_autosave()` ist **async** (das ist die heiße Stelle: Game-Loop alle 60 s).
- `_atomic_write_text` schreibt in `.tmp` und `os.replace()` → kein halb-geschriebener Save bei Crash.
- Test-Mode (`SDL_VIDEODRIVER=dummy`) zwingt sync, damit Smoke-Tests deterministisch bleiben.
- Override-ENV: `SHADOWFALL_SAVE_SYNC=1`.

**Verifikation:** 6/6 in [tools/_test_b_fixes.py](tools/_test_b_fixes.py) (B.3 Aliases, B.4 trace_swallowed + Lazy-Import, B.7 Telemetry-Queue + Save-API + Atomic-Write).

---

## C. CRITICAL GAPS (Wichtige Aspekte, die fehlen)

> **Status nach Verifikation (Update #179):** Von den 13 Gaps wurden **C.3, C.4, C.8, C.9** gefixt. **C.1, C.11** sind False-Positives (Update #42 + `_draw_world` Y-Sort haben das schon). **C.2, C.5, C.6, C.7, C.10, C.12, C.13** bleiben als geplante Arbeit. Verifikations-Tests siehe [tools/_test_c_fixes.py](tools/_test_c_fixes.py).

### C.1 — Boss-Visibility auf Minimap (POE2-Style) ❌ FALSE POSITIVE
- **Verifikation:** Update #42 hat das implementiert ([sf/world.py:1803-1840](sf/world.py#L1803-L1840)): pulsierender Boss-Skull, clamping am Minimap-Rand wenn off-view, Richtungs-Pfeil. Kommentar im Code referenziert explizit "POE2-Style". Memory `feedback_boss_fairness` ist erfüllt.

### C.2 — Quest-Fail/Abandon-Pfad fehlt komplett
- **Datei:** `sf/quests.py`
- **Status:** Keine `on_quest_failed()`, keine `on_quest_abandoned()`, keine Timeouts.
- **Konsequenz:** Escort-NPC stirbt → Quest stuck forever. Spieler will Quest droppen → unmöglich.
- **Fix:** Abandon-Button im Quest-Log + Auto-Fail nach X min Inaktivität.

### C.3 — Save-Migration nur vorwärts ✅ GEFIXT
- **Datei:** [sf/save.py:307-340](sf/save.py#L307-L340) und [sf/save.py:596-610](sf/save.py#L596-L610)
- **Vorher:** `migrate_save()` setzte bei `v > SAVE_VERSION` still `data['version'] = SAVE_VERSION` (stiller Downgrade, möglicherweise inkonsistente Felder).
- **Fix:** Neue Exception `SaveVersionTooNewError` wird geworfen. `load_game()` fängt sie ab, zeigt Toast `Save Slot X mit Version Y kann nicht geladen werden (Build max vZ)` und returnt False.

### C.4 — Skill-Cooldowns nicht persistiert ✅ GEFIXT
- **Datei:** [sf/save.py:378-381](sf/save.py#L378-L381) (serialize) und [sf/save.py:686-695](sf/save.py#L686-L695) (deserialize)
- **Fix:** `'skill_cd': dict(p.skill_cd)` ins Save-Schema. Schema-additiv — alte Saves bleiben kompatibel (Player-Init hat default-Dict, nur überschrieben was im Save steht).
- **Verifiziert:** Save→Reset→Load roundtrip — fireball=12.5s, heal=30.0s überleben (siehe [tools/_test_c_fixes.py](tools/_test_c_fixes.py)).

### C.5 — Faction-Reputation hat keinen Decay
- **Datei:** `sf/faction.py`
- **Status:** Reputation steigt nur. Spieler kann alle 7 Fraktionen maxen.
- **Fix:** Decay-Tick (-1/2h Town-Idle) ODER Konflikt-Matrix (Rep+ bei A ⇒ Rep- bei A's Feind) — die Matrix existiert schon in `grant_rep()`, aber kein Decay.

### C.6 — Vendor-Loot ohne Akt-Gating
- **Datei:** `sf/shop.py` (~Z.167)
- **Status:** Akt-1-Vendor kann Akt-5-Tier-Items verkaufen.
- **Fix:** `vendor.tier_cap = player.max_completed_act`.

### C.7 — A* mit hartem 300-Step-Limit
- **Datei:** `sf/dungeon_gen.py:209-240`
- **Status:** Bei großen Dungeons (80×80) zu klein, Fallback zu "closest walkable" fehlt.
- **Fix:** Limit adaptiv (`grid_w * grid_h // 4`) + Fallback-Pfad.

### C.8 — Crash-Recovery existiert, ist aber nicht in der UI verdrahtet ✅ GEFIXT
- **Datei:** [sf/game.py:466-473](sf/game.py#L466-L473) (Init), [sf/game.py:1391-1394](sf/game.py#L1391-L1394) (F8-Key), [sf/game.py:9016-9039](sf/game.py#L9016-L9039) (`_try_apply_crash_recovery`)
- **Fix:**
  1. `Game.__init__` ruft `save_mod.check_autosave_recovery()` → speichert Result in `self.pending_autosave_recovery`.
  2. Wenn Recovery pending: One-Shot-Toast im Title-Screen `⚠ Crash erkannt — F8 für Autosave (Slot X, N Min alt) wiederherstellen.`
  3. **F8** ruft `_try_apply_crash_recovery()` → `apply_autosave_recovery(self)` + Erfolgs-Toast.

### C.9 — Sound-Cleanup bei Scene-Wechsel fehlt ✅ GEFIXT
- **Datei:** [sf/game.py:550-555](sf/game.py#L550-L555) (`enter_town`), [sf/game.py:803-807](sf/game.py#L803-L807) (`enter_outpost`), [sf/game.py:891-895](sf/game.py#L891-L895) (`enter_dungeon`)
- **Fix:** `snd.stop_all()` am Anfang jeder Scene-Wechsel-Methode. Verhindert dass Dungeon-Loops (Wind, Lava) noch in Town spielen.
- **Verifiziert:** Counting-Monkey-Patch zeigt `stop_all()` wird bei `enter_town()` aufgerufen.

### C.10 — Keine Accessibility-Skalierung
- **Datei:** `sf/constants.py:3` (`SCREEN_W, SCREEN_H = 1600, 900` hardcoded), `sf/ui.py:38-47` (Colorblind nur für Debuff-Tray)
- **Status:** 4K-Monitor → winzige UI. Rot-Grün-Blind → kann Item-Rarität nicht unterscheiden.
- **Fix:** `game.settings['ui_scale']` global, Colorblind-Palette auf alle Farb-Codes (Rarity, Boss-Bar, HP-Bar).

### C.11 — Y-Sorting für Sprites ❌ FALSE POSITIVE
- **Verifikation:** Y-Sort ist in [sf/game.py:5441-5448](sf/game.py#L5441-L5448) implementiert: `_draw_world()` baut `tall`-Liste aus Tall-Decor + Enemies + Player + Portalen und sortiert nach `t.y` vor dem Blit. Die "extern gemanagte Sortierung" ist absichtlich (Renderer arbeitet auf game-Daten, nicht umgekehrt — Y-Sort gehört in den Draw-Coordinator, nicht in `sprites.py`).

### C.12 — Tests fehlen
- **Verzeichnis:** `tests/` existiert (siehe `ls`), aber Test-Coverage unklar.
- **Empfehlung:** Smoke-Test für Save/Load-Roundtrip, Skill-Dispatch (alle Skills castbar?), Quest-Completion-Pfade.

### C.13 — Performance-Telemetrie fehlt
- **Status:** Kein Frame-Time-Tracking, kein Profiler-Hook im Live-Build.
- **Fix:** `sf/profiler.py` (existiert, 58 Zeilen) erweitern: pro-Section Timer (`update_player`, `draw_world`, `update_enemies`), F3-Overlay.

---

## D. OPTIMIERUNGS-HOTLIST (Top 15 nach Impact)

| # | Datei:Zeile | Problem | Geschätzter Gewinn |
|---|---|---|---|
| 1 | `sf/game.py:4448-4490, 4537-4557` | Fireball/Chain O(n²) Enemy-Loops | Hoch (Frame-Drop bei 40+ Mobs) |
| 2 | `sf/ui.py` global | 465 `font.render()` pro Frame ohne Cache | Hoch (5-10ms/Frame) |
| 3 | `sf/sprites.py:1116, 2604-2611` | Status/Unique-Icon-Scale mit dynamischem Size-Key → Cache-Miss/Frame | Hoch |
| 4 | `sf/save.py:446, 488, 534` | Save-Disk-I/O sync im Mainthread | Hoch (100ms Stall) |
| 5 | `sf/combat.py:16-368` | `hit_enemy()` 350-Zeilen-Mega-Funktion, viele try-except | Mittel |
| 6 | `sf/enemies.py:840-1070` | Ally-Loops O(n²) in Enemy-Update | Mittel-Hoch |
| 7 | `sf/inventory.py:513-524` | 30 `rect.collidepoint()`/Frame | Mittel |
| 8 | `sf/quests.py:464-468` | `re.search(r'Akt (\d+)', region)` pro Caller-Call | Mittel |
| 9 | `sf/cutscene.py:309-342` | `_portrait_cache` ohne Größenlimit | Mittel (Memory) |
| 10 | `sf/telemetry.py:33-45` | Sync `f.write()` pro Event | Mittel |
| 11 | `sf/world.py:253-286` | `_dungeon_cell_cache` unbounded | Mittel (Memory-Leak) |
| 12 | `sf/ai.py:153-182` | LOS-Sight-Cycle 3 Frames (zu häufig) | Niedrig-Mittel |
| 13 | `sf/ui.py:1349-1355` | Gradient pixel-by-pixel pro Frame | Niedrig-Mittel |
| 14 | `sf/sprites.py:723-732` | `wall.get_at()` O(n²) Pixel-Sample | Niedrig (selten) |
| 15 | `sf/progression.py:186-198` | `_class_tree_bonuses` pro `effective()`-Call | Niedrig (sehr häufig aber billig) |

---

## E. DETAILBEFUNDE PRO SUBSYSTEM

### E.1 Render-Stack (`sprites.py`, `sprite_animation.py`, `effects.py`, `lighting.py`, `surface_fx.py`, `weather.py`, `gl_post.py`)

**Bugs:**
- `sprites.py:280-289`: Alpha-Premult via NumPy schluckt alle Exceptions (`except Exception: pass`) — wenn NumPy fehlt, keine Warnung; weiße Halos bei Upscale.
- `sprites.py:262-268`: Unbekannter Anim-Type → silent Fallback auf 8 Frames, keine Log-Warnung.
- `gl_post.py:278-287`: Texture-Upload pro Frame (1280×800 RGBA), kein Sub-Update.

**Dead Code:**
- `sprites.py:162-163`: `_WALK_FRAME_CACHE = _ANIM_FRAME_CACHE` Alias, nie direkt benutzt.
- `sprites.py:439-452`: `TILE_VARIANT_MAP` kommentiert 4 Variants, nur `_a` aktiv.

### E.2 Gameplay (`combat.py`, `skills.py`, `class_skills.py`, `ai.py`, `enemies.py`, `boss_encounter.py`)

**Bugs (zusätzlich zu A.4-A.10):**
- `sf/combat.py:769` — `_engage_charge`: kein Guard bei `d == 0` vor `diff.normalize()`.
- `sf/enemies.py:1723, 1740` — Caster: `diff.length() == 0`-Check NACH `normalize()`.
- `sf/combat.py:229-243` — Stun-Buildup: `e.stun_buildup_max` nicht garantiert initialisiert.
- `sf/combat.py:96-108` — Pin-Trigger: `'pinned' not in e.status` aber Pin wird nie in `status`-Dict eingetragen → Doppel-Apply möglich.
- `sf/enemies.py:794-805` — `aschenbrut._plague_aura_t` erst beim 1. Frame initialisiert (1-Frame-Aussetzer).
- `sf/boss_encounter.py:511, 513` — Heal-Once hardcoded 0.5x; sollte `heal_frac`-Config sein.
- `sf/enemies.py:984-985` — Phase2-Multiplier 0.7 vs 0.75 inkonsistent zwischen Bossen.

**AI-State-Machine-Lücke:**
- `sf/ai.py:404-414` — Wenn `_has_patrol(e)` False, fällt Enemy in IDLE und kommt nie wieder raus.

### E.3 Content/World (`quests.py`, `inventory.py`, `crafting.py`, `world.py`, `dungeon_gen.py`)

**Bugs:**
- `sf/quests.py:142-154` — ESCORT-NPC Lazy-Spawn ohne Timeout (Quest stuck wenn Spieler im Dungeon stirbt).
- `sf/quests.py:406-440` — Quest-Prerequisite: alle `requires_quests` müssen erfüllt (AND-only) → keine OR-Pfade.
- `sf/crafting.py:275-300` — `socket_gem` Bounds-Check nur in `can_socket`, nicht redundant.
- `sf/inventory.py:554-556` — Item-Drop Ordering: Quest-Item-Check vor Inventory-Slot-Nulling, OK aber fragil.
- `sf/quest_data.py:1077-1867` — ~790 Zeilen ungelesen, verdacht auf Copy-Paste-Reste (verifizieren).

### E.4 UI/Audio/Infra (`ui.py`, `save.py`, `sounds.py`, `cutscene.py`, `modloader.py`, `telemetry.py`)

**Bugs (zusätzlich zu A.12-A.13, C.3, C.8-C.9):**
- `sf/ui.py:1289, 1321-1322` — Hard-coded Pixel-Positionen für HUD-Boxen ohne Scaling-Faktor.
- `sf/dialog.py:310-311` — Dialog-Modal mit `(SCREEN_W - mw)//2`, reagiert nicht auf Resize.
- `sf/sounds.py:1724, 1757` — Channel-IDs 1, 2 hardcoded für Step/Ambient; Konflikt mit SFX-Pool nicht geprüft.
- `sf/locale.py:104-113` — Locale-Fallback liefert bei unbekanntem Key den Key selbst → UI-Garbage statt Default.

**Dead Code:**
- `sf/ui.py:3746-3758` — `_tick_and_draw_anims()` pflegt Timer, aber keine aktiven Animationen.
- `sf/quotes.py:247-257` — `_pick_no_repeat()` nur für Death/Wake, `CLASS_VOICELINES` (Z.460) ohne No-Repeat.
- `sf/sfx_registry.py` — 470+ Einträge, ~200 Call-Sites → ~270 ungenutzte (z.B. `aspekt_echo_*`, `weather_*`).
- `sf/tutorial.py:130-168` — `advance()` setzt Flags, aber kein UI-Hook → Tutorial sichtbar in Town, nicht in Main-HUD.

---

## F. STATISTIK

| Subsystem | Bugs (krit.) | Dead Code | Opt-Hotspots | Gaps |
|---|---|---|---|---|
| Entry Points + game.py | 5 | shadowfall.py (1071 Zeilen) | 10 | 5 |
| Render | 4 | 4 | 10 | 5 |
| Gameplay | 8 | 7 Subsysteme (bestiary, runes, aspects, ~15 Skills) | 10 | 5 |
| Content/World | 6 | 2 | 10 | 5 |
| UI/Audio/Infra | 6 | 4 | 10 | 5 |
| **Summen** | **~29** | **~20** | **~50** | **~25** |

**Mega-Files zum Splitten:** `game.py` (11k), `ui.py` (4.5k), `sprites.py` (3.3k), `sounds.py` (2.6k), `world.py` (2.3k), `skills.py` (2k)

**Bare-except-Plage:** ~130 Stellen.

---

## G. EMPFOHLENER ABARBEITUNGS-PFAD

**Sprint 1 (1-2 Tage) — Sofort-Cleanup:**
- A.1, A.2 löschen (shadowfall.py, Skills.md)
- A.3, A.5 fixen (Surface-Leak, Teleport-Crash)
- A.4 fixen (Boss-LOS-Order) ← Lore-relevant, Memory `feedback_boss_fairness`
- A.6 konsolidieren (Boss-Shield)
- A.8-A.11 entscheiden: implementieren oder Stubs entfernen

**Sprint 2 (3-5 Tage) — Critical Gaps:**
- C.1 (Boss-Minimap-Marker)
- C.2 (Quest-Abandon/Fail)
- C.3, C.8 (Save-Migration-Reject, Crash-Recovery-UI)
- C.4 (Skill-CD persistieren)
- C.9 (Sound-Cleanup Scene-Wechsel)

**Sprint 3 (1-2 Wochen) — Strukturelles:**
- B.5 (`SpatialGrid` neu, ersetzt 4-5 O(n²)-Stellen)
- B.4 (Bare-except-Plage in 10 hot files reduzieren)
- B.1 (game.py-Split, in Etappen)
- D.1-D.4 (Top-Optimierungen)

**Sprint 4 — Polish:**
- C.10 (Accessibility)
- C.5, C.6 (Faction-Decay, Vendor-Gating)
- B.2-B.3 (ui.py + sprites.py Splits)
- C.12-C.13 (Tests, Profiler-Overlay)
