# VELGRAD TOOLBOX

> **Zweck:** Single-Source-of-Truth ueber alles was im Projekt verfuegbar ist + Wann was zu benutzen ist. Lebe-Dokument — bei jedem neuen Tool/Library hier eintragen.
>
> **Auto-Audit:** `python tools/list_stack.py` listet den aktuellen Stack-State (Versionen, Modul-Inventar) in der Konsole.
>
> **Companion-Doku:** [VELGRAD_RENDER_SPEC.md](VELGRAD_RENDER_SPEC.md) (Render-Konventionen), [VELGRAD_WORKFLOWS_BIBEL.md](VELGRAD_WORKFLOWS_BIBEL.md) (AI-Workflows), [ROADMAP.md](ROADMAP.md) (Tier-Plan).

---

## 0. QUICK-DECISION-TREE

> **Wenn du X machen willst → benutze Y.** Erste Anlaufstelle.

| Aufgabe | Tool / Modul |
|---|---|
| Neuen Asset-Typ definieren (Spec) | `sf/render_spec.py` editieren + Doku in `VELGRAD_RENDER_SPEC.md` |
| Neue Klassen-Animation einfuegen | `monk_anims/<anim>/<dir>.png` droppen + `tools/sprite_postprocess.py --bg black` |
| Neues Biom-Floor einbauen | `tools/process_biome_tile.py --biome <name>` (One-Command-Pipeline) |
| Wall-Tile aus Floor generieren | `tools/wall_from_floor.py --biome <name>` |
| 16 Edge-Masks fuer ein Biom baken | `tools/workflow_texture_tiler.py --biome <name> --procedural` |
| BG-Removal auf einem Sprite | `tools/sprite_postprocess.py --file <png> --bg black\|white` |
| Asset-Compliance pruefen | `tools/asset_audit.py` |
| Welche Tools sind installiert? | `python tools/list_stack.py` |
| Hand-crafted Map laden | `sf/tiled_loader.py` (Tiled .tmx Format) |
| Physik (Splitter, Boss-Wurf) | `Game.spawn_splitter_burst()` / `Game.spawn_throwable()` |
| Post-Process-Shader (Bloom) | `sf/lighting.py` (intern) ODER `sf/gl_post.py` (PyOpenGL opt-in) |
| Dynamisches Licht (Fackel, Glow) | `sf/lighting.py` — `LightingSystem.add()` |
| Voice generieren | `tools/voice_gen.py` (ElevenLabs) |
| SFX generieren | `tools/sfx_gen.py` (ElevenLabs) |
| AI-Sprite generieren (deprecated post-pivot) | `tools/sprite_gen.py` (Scenario.gg, nur bei Bedarf) |
| Workflow-Run-Log einsehen | `python tools/workflow_runner.py` |
| Tests laufen lassen | `PYTHONPATH=. python tests/smoke.py` |
| Game starten | `python -m sf.main` ODER `python sf/game.py` |

---

## 1. EXTERNE LIBRARIES (pip-installed)

| Library | Version | Zweck | Wann nutzen |
|---|---|---|---|
| **pygame-ce** | 2.5.7 | Core 2D Engine (Surfaces, Events, Mixer, Display) | Immer (Engine-Base) |
| **numpy** | latest | Bild-Pixel-Operationen, Math | Sprite-Postprocess, Lighting, Wall-Gen |
| **PyOpenGL** | 3.1.10 | GLSL-Shader-Post-Process (opt-in) | Wenn `Game(use_gl_post=True)` |
| **PyOpenGL_accelerate** | (paired) | C-Speedup fuer PyOpenGL | Automatisch wenn PyOpenGL aktiv |
| **pymunk** | 7.2.0 | 2D Physik-Engine (Splitter, Throwables) | Decor-Physik, Boss-Projektile (NICHT Movement) |
| **pytmx** | 3.32 | Tiled .tmx Map-Loader | Hand-crafted Maps fuer Outposts/Boss-Arenen |
| **ElevenLabs (HTTP)** | — | TTS + Sound Effects | Voice + SFX Generation (Setup via `ElevenLabs.txt`) |
| **Scenario.gg (HTTP)** | — | AI Sprite-Generation (deprecated post-pivot) | Optional: neue AI-Sprites |

**Install-Befehle:**
```bash
pip install pygame-ce numpy PyOpenGL PyOpenGL_accelerate pymunk pytmx
```

---

## 2. ENGINE-MODULE (sf/)

> Core-Engine-Code. Wenn du Game-Logic aendern willst, gehe hier rein.

### Render & Animation
| Modul | Zweck |
|---|---|
| `sf/game.py` | Main game-loop, state-management, draw-orchestration |
| `sf/world.py` | Biome-Definitionen, Floor/Wall-Render, Mini-Map, Edge-Overlay-Hook |
| `sf/sprites.py` | Sprite-Cache, Walk-Anim-Loader, Edge-Overlay-System, Player/Mob/Decor-Render |
| `sf/sprite_animation.py` | State-Machine (idle/walk/attack/hit/cast/death) — `AnimationState` |
| `sf/sprite_registry.py` | Auto-generierte Sprite-ID → File-Path Map (durch `sprite_gen.py` aktualisiert) |
| `sf/render_spec.py` | **Single Source of Truth** fuer Asset-Render-Konventionen (Kamera/Distance/Resolution/BG/target_h) |
| `sf/lighting.py` | 2D Lighting (Bloom, Fog, Shadow-Polygons, Heat-Distortion, God-Rays, Lightning-Flash) |
| `sf/gl_post.py` | PyOpenGL Post-Process Layer (Bloom + Color-Grade + Vignette via GLSL, opt-in) |
| `sf/physics.py` | Pymunk-Wrapper (`PhysicsWorld.add_splitter_burst`, `add_throwable`) |
| `sf/tiled_loader.py` | Tiled .tmx Map-Loader (`has_map`, `load_map`, `tmx_to_engine`) |
| `sf/constants.py` | SCREEN_W/H, CELL, CLASSES, DUNGEONS, GOLD/colors |
| `sf/entities.py` | Player, Enemy, Decor, Projectile Classes |
| `sf/dungeon_gen.py` | Prozeduraler Dungeon-Generator (Rooms, Corridors, Traps) |

### Game-Systems
| Modul | Zweck |
|---|---|
| `sf/combat.py` | Damage-System, hit_enemy, damage_player, dodge, knockback |
| `sf/skills.py` + `sf/class_skills.py` | Klassen-Skills (fireball, lightning, heal, frostnova, ...) + SkillGem-Definitionen |
| `sf/progression.py` | Level-Up, XP, Stat-Berechnung, effective(p), Akt-Gating |
| `sf/inventory.py` + `sf/stash.py` | Item-Slots, Equipment, Weapon-Swap, Drag/Drop + persistenter Storage |
| `sf/items.py` | Item-Datenklasse, Affixes, Rarity, Quest-Items |
| `sf/crafting.py` | Otreth-Gemcutter, Affix-Roll, Reroll, Socket, Salvage |
| `sf/gems.py` + `sf/runes.py` | Gem-/Tag-/Support-System (PLAN J-01..J-04) + Runen-Slot-System |
| `sf/shop.py` | Vendor-System, Faction-Discounts, Buy/Sell |
| `sf/save.py` | Save/Load (JSON), Backward-Compat |
| `sf/quests.py` + `sf/quest_data.py` | Quest-Engine + Quest-Definitionen |
| `sf/dialog.py` | NPC-Dialog-Modal mit Portrait + Choices |
| `sf/cutscene.py` | Story-Cutscene-Framework |
| `sf/faction.py` | Faction-Rep-System, CONFLICT_MATRIX |
| `sf/outposts.py` + `sf/town.py` | NPC_ROSTER, Outpost-Layouts + Stadt-Logik |
| `sf/regions.py` | Biome-Fallbacks, Akt-Bindings |
| `sf/sounds.py` + `sf/sfx_registry.py` + `sf/voice_registry.py` | Audio-Engine + Asset-Lookups |
| `sf/aspects.py` | Aspekt-Palettes, Class-Themes |
| `sf/ui.py` | TitleUI, HUD, Codex, Quest-Log, Memorial, etc. |
| `sf/weather.py` | Day/Night, Fog, Tag/Nacht-Tinte |
| `sf/enemies.py` + `sf/bestiary.py` + `sf/ai.py` + `sf/archetypes.py` | Enemy-Templates + Bestiarium-Lore + KI + Verhaltens-Templates |
| `sf/boss_encounter.py` | Boss-Spawn-Cinematics, Multi-Phase-Trigger |
| `sf/effects.py` + `sf/surface_fx.py` | Status-Effects + VFX-Particle-Layer-System |
| `sf/dungeon.py` + `sf/dungeon_events.py` | Dungeon-Spec-Loader + Dynamic-Events (Update #27) |
| `sf/events.py` | Event-Bus (PLAN J-12) fuer lose Kopplung Combat/UI/Audio |
| `sf/quotes.py` | Voice-Line-Pools fuer Death/Wake/Bestiary-Encounters |
| `sf/tips.py` + `sf/tutorial.py` | Loading-Tips + First-Run-Tutorial (PLAN Y-01) |
| `sf/locale.py` | Localization-Foundation (PLAN S-08) |
| `sf/achievements.py` | 15 Meilensteine mit Gold-Belohnungen |

### Internal/Dev-Tools (selten geaendert)
| Modul | Zweck |
|---|---|
| `sf/console.py` | Debug-Console (PLAN AA-02) — F1 In-Game |
| `sf/profiler.py` | Profiler-Mode (PLAN AA-07) |
| `sf/replay.py` | Replay-Recording (PLAN AA-06) |
| `sf/telemetry.py` | Anonyme Usage-Stats |
| `sf/crash_logger.py` | Crash-Logger (PLAN AA-03) |
| `sf/modloader.py` | Mod-Hook-API (PLAN AA-05) |
| `sf/async_loader.py` | Async-Asset-Loading (PLAN J-14) |
| `sf/asset_validator.py` | Asset-Validator (PLAN AA-08) |

---

## 3. CLI-TOOLS (tools/)

> Standalone-Scripts. Drop-and-run, kein Engine-Import-Setup noetig.

### Sprite-Pipeline
| Tool | Zweck | Beispiel |
|---|---|---|
| `tools/sprite_gen.py` | Scenario.gg AI-Sprite-Batch (deprecated post-pivot) | `python tools/sprite_gen.py --target salzhueter_brut` |
| `tools/sprite_postprocess.py` | BG-Removal (black/white) + flood-fill + hard-mask | `python tools/sprite_postprocess.py --file x.png --bg black` |
| `tools/asset_audit.py` | Spec-Compliance-Check pro Asset | `python tools/asset_audit.py --only fail` |
| `tools/scenario_config.py` | Scenario API Credential-Loader (Module, kein CLI) | — |
| `tools/scenario_list_models.py` | Scenario LoRA/Model-Diagnose | `python tools/scenario_list_models.py --search "dark"` |

### Workflow-Runner (Multi-Inference)
| Tool | Zweck | Beispiel |
|---|---|---|
| `tools/workflow_runner.py` | Shared Base + Audit-Log-Reader | `python tools/workflow_runner.py` (zeigt Runs) |
| `tools/workflow_character_sheet.py` | 4-Direction-Hero-Sheet | `python tools/workflow_character_sheet.py --target warrior` |
| `tools/workflow_animation_frames.py` | 8-Frame Walk/Attack/Hit-Cycles | `python tools/workflow_animation_frames.py --target monk --anim walk --dir S` |
| `tools/workflow_texture_tiler.py` | 16-Mask Modular Tileset (procedural+AI-Hybrid) | `python tools/workflow_texture_tiler.py --biome crypt --procedural` |
| `tools/workflow_inpaint.py` | img2img Inpaint via Scenario | `python tools/workflow_inpaint.py --image x.png --bounds X,Y,W,H --prompt "..."` |
| `tools/wall_from_floor.py` | Procedural Wall-Generator (per-Biom unique Algorithmen) | `python tools/wall_from_floor.py --biome lava` |
| `tools/process_biome_tile.py` | One-Command-Pipeline: Floor → Variants + Wall + Masks + Engine-Registry | `python tools/process_biome_tile.py --biome desert --source x.png` |

### Audio-Pipeline (ElevenLabs)
| Tool | Zweck | Beispiel |
|---|---|---|
| `tools/voice_config.py` | ElevenLabs Credential + Voice-IDs (Modul) | — |
| `tools/voice_gen.py` | Voice-Lines via TTS | `python tools/voice_gen.py --line "..."` |
| `tools/sfx_gen.py` | Sound-Effects via ElevenLabs | `python tools/sfx_gen.py --target damage_light_cloth` |
| `tools/voice_list.py` | Verfuegbare Voice-IDs listen | `python tools/voice_list.py` |
| `tools/voice_manifest_builder.py` | Voice-Cast-Sheet generieren | — |

### Sonstige
| Tool | Zweck |
|---|---|
| `tools/walk_strip_chatgpt.py` | Walk-Strip via OpenAI gpt-image-1 (alternative zu Scenario) |
| `tools/list_stack.py` | **Auto-Diagnose des aktuellen Stack-State** |

### Migration / One-Shot (selten benutzt, mit `_` prefix)
| Tool | Zweck |
|---|---|
| `tools/_migrate_md_links.py` | One-shot: MD cross-refs nach docs/-Restruktur fixen |
| `tools/_post_gen_pipeline.py` | Post-Generation-Pipeline: BG-Removal + Audit nach Scenario.gg run |
| `tools/_reconcile_manifest.py` | One-shot: sprite_manifest.json gegen Disk reconcilen |

---

## 4. BIBLES & DOCS (Project-Root)

| Doc | Zweck |
|---|---|
| `VELGRAD_TOOLBOX.md` | **DIESES DOC** — Tool-Inventar + Decision-Tree |
| `VELGRAD_RENDER_SPEC.md` | Asset-Render-Konventionen (Kamera/Distance/BG/Size pro Kategorie) |
| `VELGRAD_WORKFLOWS_BIBEL.md` | Scenario.gg Multi-Inference-Workflows |
| `VELGRAD_SPRITE_BIBEL.md` | Sprite-Targets mit Lore-Prompts (M/C/P/B/T/D/U/S) |
| `VELGRAD_SFX_BIBEL.md` | 433 SFX-Definitionen |
| `VELGRAD_VOICE_CASTING.md` | NPC → Voice-ID Mapping |
| `VELGRAD_VOICE_LINES_POOL.md` | Voice-Lines pro NPC + Trigger-Keys |
| `VELGRAD_AUDIO_DESIGN_BIBEL.md` | Audio-Design-Konventionen |
| `VELGRAD_LORE_BIBEL.md` | Velgrad-Welt-Lore (7 Aspekte, 7 Akte, 7 Fraktionen) |
| `VELGRAD_BESTIARIUM.md` | 30-Mob Lore + Mechaniken |
| `VELGRAD_ITEMS_UNIQUE_BIBEL.md` | 50 Unique-Items mit Affixes |
| `PLAN.md` | Engine-Tasks-Historie (A-AA) |
| `ROADMAP.md` | Tier-basierter Sprint-Plan |
| `WELT_AUFBAU.md` | Akt-Content-Specifikation |
| `QUEST_BIBEL.md` | 53 Quests in 7 Akten |
| `CHANGELOG.md` | Per-Update Changes (~#178) |
| `README.md` | Repo-Overview + Setup |

---

## 5. COMMON WORKFLOWS — Step-by-Step

### Recipe A: Neuen Hero-Sprite einfuegen (procedural-only-konform)
1. AI-Tool deiner Wahl (ai.nero.com / Krea / Leonardo / Scenario)
2. Drop nach `assets/sprites/classes/<class>.png` (512×768 transparent BG)
3. F5 im Game → Hot-Reload via `sprites.reload_sprite_cache()`
4. Falls noch BG nicht transparent: `python tools/sprite_postprocess.py --file <path> --bg black`

### Recipe B: Neuen Walk-Cycle einfuegen
1. AI-Tool generiert 4 Strips (down/up/left/right), je 8 Frames horizontal
2. Drop nach `assets/sprites/classes/<class>_anims/walk/<dir>.png`
3. `python tools/sprite_postprocess.py --file <path> --bg black --threshold 30 --feather 6`
4. F5 im Game

### Recipe C: Neues Biom-Floor mit allem drum und dran
1. AI-Tool generiert seamless Floor-Tile (~512×512)
2. Drop nach `assets/sprites/tiles/<biome>_drop.png`
3. `python tools/process_biome_tile.py --biome <name>` → fertig (Variants + Wall + Masks + Engine-Register)

### Recipe D: Hand-crafted Map (Boss-Arena)
1. Tiled-Editor oeffnen → New Map 32×32 px tiles
2. Layers: `floor`, `walls`, `spawns`, `decor`, `regions`
3. Save as `assets/maps/<biome>/<name>.tmx`
4. (TODO Update #179) Game.enter_dungeon-Hook → tiled_loader.has_map prueft

### Recipe E: Boss-Wurfprojektil (Pymunk)
```python
# In Boss-Encounter-Phase, z.B. vehren_phase2:
game.spawn_throwable(
    start_xy=(boss.x, boss.y),
    target_xy=(player.x, player.y),
    speed=350,
    color=(180, 140, 220),
    kind_id='vehren_aether',
    payload={'damage': 25, 'effect': 'aether_burn'},
)
```

### Recipe F: Decor zerbricht mit Splitter
```python
# In combat-Hit-on-Decor:
game.spawn_splitter_burst(
    decor.x, decor.y,
    count=10,
    color=(140, 90, 50),
    speed_range=(80, 240),
)
```

### Recipe G: GLSL Post-Process aktivieren
```python
# Im Settings-Menu oder direkt:
game = Game(use_gl_post=True)
# → Lava-Cracks gluehen via Bloom, jedes Biom hat eigenen Mood-Grade
```

### Recipe H: Asset-Audit vor Commit
```bash
python tools/asset_audit.py --only warn   # zeigt was nicht zur Spec passt
python tools/asset_audit.py --only fail   # blocker
```

---

## 6. PITFALLS & GOTCHAS

### Sprite-Postprocess
- **Pure-black BG:** `--bg black --threshold 30 --feather 6` (Default)
- **Pure-white BG:** `--bg white` (manche AI-Tools schicken white statt black)
- **24-bit RGB ohne Alpha:** Pygame setzt alpha=255 obwohl "transparent" angezeigt — Postprocess konvertiert zu 32-bit + setzt alpha basierend auf brightness
- **Belt/thin features durchsichtig:** Hard-Mask (Update #176/#177) erzwingt — keine feathered Alpha mehr im Body

### Walk-Animations
- **Char wechselt Charakter beim Laufen-nach-Links:** Wahrscheinlich AI generierte "Character Variation Sheet" statt "Walk Cycle". Direction-Fallback (Update #169) faengt das ab — broken sheets ins `_broken/`-Subfolder.
- **Frame-Jitter:** Union-BBox-Trim (Update #175) — alle 8 Frames bekommen exakt die gleichen Dimensionen.

### Lighting
- **Schon implementiert!** Nicht doppelt bauen. `sf/lighting.py` ist voll integriert in `game.draw()` mit Bloom + Fog + Shadow-Polygons + God-Rays + Heat-Distortion.

### Engine-Render
- **Char zu klein:** `target_h = radius * 6.0` (Update #164) — kommt aus `render_spec.get_target_h_mult('class')`
- **Tile-Patchwork:** TILE_VARIANT_MAP haelt nur 1 Variant aktiv (a) — Patchwork-Chaos vermeiden

### Credentials
- **Niemals committen:** `.gitignore` blockt `ElevenLabs.txt`, `scenario.txt`, `.env`, `*.key`
- **Bei Leak:** sofort revoken auf https://app.scenario.com/team bzw. ElevenLabs-Dashboard

---

## 7. AKTUELL OFFEN (post-Update-#178)

- [ ] Game.enter_outpost/enter_dungeon mit tiled_loader-Hook (procedural-Fallback wenn keine .tmx)
- [ ] Erste hand-crafted Map als Pilot (z.B. Brassweir-Hub)
- [ ] Settings-Toggle UI fuer `use_gl_post`
- [ ] gl_post als Layer-Composition (off-screen-render-surface) — aktuell nur Direct-Pass

---

## 7a. RELEASE-READY-ROADMAP (kuratierte Tool-Empfehlungen)

> **Stand:** noch nicht installiert. Bei jedem aktivierten Tool: pip install + TOOLBOX-Section-1 update + list_stack.py reflektiert automatisch.

### Tier 1 — KRITISCH fuer Release (ohne kein Ship moeglich)

| Tool | Zweck | Aufwand | Pflicht? |
|---|---|---|---|
| **Nuitka** | Python → C-Compile → .exe single-file (~30-50 MB) | 1 Tag | JA |
| **PyInstaller** (Alternative) | einfacher aber langsamer als Nuitka | 1 Tag | (Nuitka oder PyInstaller) |
| **moviepy** | Gameplay-Trailer-Recording fuer Marketing/Steam-Page | 0.5 Tag | empfohlen |

### Tier 2 — Graphics/Animation-Quality

| Tool | Zweck | Aufwand |
|---|---|---|
| **scipy.ndimage** | Echter Gaussian-Bloom (ersetzt 2-Pass-Approx in sf/lighting.py render_bloom) | 0.5 Tag |
| **noise** (Perlin/Simplex) | Natuerliche Variations: Tile-Variance, Fog-Density, Particle-Drift, Wind | 0.5 Tag |
| **moderngl** | Cleaner Shader-Workflow als PyOpenGL (70% weniger Code, bessere Errors) | 1 Tag |

### Tier 3 — UI/UX-Polish

| Tool | Zweck | Aufwand |
|---|---|---|
| **pygame_menu** | Settings-Menue mit Key-Rebind, Volume-Sliders, Resolution, Accessibility | 1-2 Tage |
| **pysrt** | Untertitel-File-Management fuer Voice-Lines (Accessibility) | 0.5 Tag |

### Tier 4 — Code-Quality + Tests

| Tool | Zweck | Aufwand |
|---|---|---|
| **pytest** | Migration von ad-hoc smoke.py auf strukturiertes pytest | 1 Tag |
| **pytest-benchmark** | FPS-Regression-Catching pro Test | 0.5 Tag |
| **hypothesis** | Property-based Testing fuer Combat-RNG/Loot-Rolls | 0.5 Tag |
| **ruff** | Fast Linter (10000x schneller als pylint) | 0.25 Tag |
| **mypy** | Static-Type-Check fuer game.py (9487 LOC, Types finden Bugs) | 1 Tag |

### Tier 5 — Marketing/Distribution (wenn Release nah)

| Tool | Zweck |
|---|---|
| **steamworks-py** | Steam-Achievements, Cloud-Save, Friend-Invites |
| **discord-rpc** | Discord Rich Presence ("Spielt Velgrad — Akt 3") |
| **itch.io butler** | Auto-Upload zu Itch.io (CLI-Tool, kein Python-Package) |

### Was wir **NICHT** brauchen (verworfene Alternativen)

- ~~arcade~~ — komplette Engine-Migration unrealistisch
- ~~Spine/DragonBones~~ — bone-animation, widerspricht Procedural-Pivot
- ~~Panda3D / Godot~~ — 3D-Engines, alles neu
- ~~FMOD/Wwise~~ — Pro-Audio-Middleware, overkill
- ~~pyglet~~ — Pygame-Alternative, kein Mehrwert hier
- ~~Cython~~ — Numba reicht fuer Hot-Loop-Speedup ohne Compile-Step

### Empfohlene Aktivierungs-Reihenfolge (wenn Release-Ready werden soll)

1. **scipy.ndimage** + **noise** — sofortiger Quality-Sprung, 1 Tag
2. **pygame_menu** — Settings-UI, ohne das fehlt's beim Release
3. **pytest** + **ruff** + **mypy** — Quality-Foundation
4. **Nuitka** — Distribution
5. **moviepy** — Trailer fuer Steam-Page

Erst dann Steam/Itch-Spezifika.

---

## 8. WIE MAN DIESE DOC AKTUELL HAELT

Bei JEDER neuen Library/Tool/Modul:
1. Hier eintragen (Tabelle + Recipe wenn neu)
2. `tools/list_stack.py` listet automatisch (kommt aus dieser Doku abgeleitet)
3. ROADMAP-Update bei groesseren Tier-Hits

**Convention:** Diese Datei ist auctoritativ. Wenn `list_stack.py` etwas zeigt was hier fehlt → Doc-Update. Wenn hier etwas steht das nicht in `list_stack.py` taucht → ist es eventuell entfernt worden?

---

**Stand:** 2026-05-24 (nach Update #178). Naechster Maintenance-Update bei Engine-Hook tiled_loader (#179).
