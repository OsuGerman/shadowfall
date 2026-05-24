# CLAUDE.md — AI-Assistant Onboarding

> **Lese DIES als allererstes** wenn du ein neuer Claude/AI-Assistent in diesem Projekt bist. Spart Stunden des "wo-ist-was-was-wurde-schon-gebaut" Rumstoeberns.

---

## TL;DR — Velgrad / Shadowfall

**Was:** Python/pygame-ce 2D Top-Down Dark-Fantasy ARPG (POE2/D2-Stil). Akt 1 spielbar, Akte 2-7 in Arbeit.

**Stack:** pygame-ce 2.5.7 (Engine), numpy (Bilder), PyOpenGL (opt-in Post-Process), pymunk (Decor-Physik), pytmx (Tiled-Maps), ElevenLabs (Voice+SFX), Scenario.gg (deprecated post-pivot).

**Wichtigste Wahrheit:** Update #171 = **PROCEDURAL-ONLY-PIVOT**. Aktuell **KEINE externen AI-Sprite-Assets** im Repo (alle entfernt). Engine rendert procedural. Sprite-Pipeline-Tools sind erhalten fuer optional re-introduction.

---

## ANLAUFSTELLEN — wo finde ich was

| Frage | Antwort |
|---|---|
| **Was gibts an Tools/Libraries?** | [VELGRAD_TOOLBOX.md](VELGRAD_TOOLBOX.md) (kuratiert) + `python tools/list_stack.py` (live) |
| **Render-Konventionen (Kamera, Distanz, Size pro Asset)?** | [VELGRAD_RENDER_SPEC.md](VELGRAD_RENDER_SPEC.md) + `sf/render_spec.py` |
| **AI-Workflows (Scenario.gg)?** | [VELGRAD_WORKFLOWS_BIBEL.md](VELGRAD_WORKFLOWS_BIBEL.md) |
| **Was wurde wann gebaut?** | [CHANGELOG.md](CHANGELOG.md) + git log |
| **Was kommt als naechstes?** | [ROADMAP.md](ROADMAP.md) (Tier-Plan) |
| **Welt-Lore?** | [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md) |
| **Quests?** | [QUEST_BIBEL.md](QUEST_BIBEL.md) + `sf/quest_data.py` |
| **Engine-Tasks (Update-Historie A-AA)?** | [PLAN.md](PLAN.md) |

---

## CRITICAL CONTEXT — vermeidet Stolpersteine

### 1. Procedural-Only-Pivot (Update #171)
Der User hat entschieden: **kein externes AI-Asset im Repo**. Wenn du Code schreibst der `assets/sprites/<class>.png` erwartet → bricht. `sprites.py` hat `_AI_SPRITES_ENABLED=False` Flag. Engine faellt auf Procedural-Composit zurueck.

→ **DO:** Procedural-Logic erweitern (Edge-Overlays, Lighting, dynamic FX).
→ **DON'T:** Neue AI-Sprite-Files committen (User wird sie raus-rebasen).
→ **AUSNAHME:** monk_anims/walk/ Files sind aktuell tracked weil sie procedural komplementaer sind.

### 2. Lighting ist BEREITS implementiert
`sf/lighting.py` ist ein **komplettes 2D-Lighting-System** mit Bloom, Fog, Heat-Distortion, God-Rays, Shadow-Polygons, Lightning-Flash, Cell-Glow. Gewired in `game.py` (begin_frame → gather_default → render). **Nicht duplizieren.** Erweitern wenn noetig.

### 3. Walk-Animation-Pipeline
- **Filename-Convention:** `assets/sprites/classes/<class>_anims/<anim>/<dir>.png` (Update #165)
- **anim:** `idle`, `walk`, `attack`, `hit`, `cast`, `death`
- **dir:** `down`, `up`, `left`, `right` (oder `all.png` fuer non-directional)
- **Frame-Count:** aus `sf/sprite_animation.py ANIM_CONFIG`
- **Backward-Compat:** alte `<class>_walk/<class>_<dir>.png` funktioniert auch noch

### 4. BG-Removal-Konvention
- Default: black BG (`--bg black --threshold 30 --feather 6`)
- White BG vorhanden: `--bg white`
- **Bekanntes Risiko:** thin Char-Features (Guertel, Stoffstreifen) wurden in #176 durchsichtig wegen feathered alpha. Fix in #177 — Hard-Mask: `alpha=255` fuer alle non-reachable Pixel, nur 1px Boundary bei 220.

### 5. Tile-Patchwork-Falle
`TILE_VARIANT_MAP['<biome>'] = ['<biome>_floor_a']` — nur 1 Variant aktiv. Variants b/c/d existieren aber sind aus. User-Feedback war eindeutig: 4 Variants ergaben Patchwork-Chaos.

### 6. Credentials-Schutz
- `scenario.txt`, `ElevenLabs.txt`, `.env`, `*.key` sind `.gitignore`-blocked
- **NIEMALS** Key-Content in Chat-Output oder Code drucken
- Bei Leak: revoken auf https://app.scenario.com/team bzw. ElevenLabs-Dashboard

### 7. Pygame-Display-Modes
- Default: `pygame.SCALED` (vsync, scharfes Scaling)
- Opt-in: `Game(use_gl_post=True)` → `OPENGL | DOUBLEBUF` (anderes Surface-Pipeline, gl_post statt direct-flip)

### 8. Test-Konvention
`PYTHONPATH=. python tests/smoke.py` — 197 Tests. Manche sind flaky (random-loot-roll, motion-sickness-defaults, hardcore_permadeath). Wenn 195-197 pass → ok. Wenn <195 → echte Regression.

---

## TYPICAL TASK-FLOWS

### Wenn der User sagt "drop hier liegt Asset X":
1. Pfad checken (oft `~/Desktop/maps/*.png`)
2. Asset-Typ identifizieren (floor / wall / hero / mob / portrait / boss)
3. Passende Pipeline ausfuehren:
   - **Floor:** `tools/process_biome_tile.py --biome X --source <path>`
   - **Hero/Class:** Copy nach `assets/sprites/classes/<class>.png` + `sprite_postprocess.py`
   - **Walk-Strip:** Copy nach `assets/sprites/classes/<class>_anims/walk/<dir>.png` + postprocess
4. F5-Hot-Reload-Hint (`reload_sprite_cache()`)

### Wenn der User sagt "Bug X":
1. Reproduce mit headless-test (siehe `tmp_*.png`-Pattern in chat history)
2. Diagnose via numpy-Alpha-Stats (`pygame.surfarray.pixels_alpha`)
3. Fix + smoke-tests + commit

### Wenn der User sagt "wie geht's weiter":
1. `cat ROADMAP.md | head -100` fuer Tier-Plan
2. AskUserQuestion mit Top-3-Optionen (mit Aufwand-Schaetzung)
3. Erst nach Confirmation: implementieren

### Commit-Format
```
feat: <kurze Beschreibung> (Update #NNN)

<Detail-Body>

Tests: NNN/197 pass.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```
- `feat:` neue Feature, `fix:` Bug, `docs:` Doku, `content:` Asset/Lore
- Update-Nummer hochzaehlen (zuletzt: #178)
- Co-Author-Trailer ist Pflicht

### Git-Workflow
- User pushed selber (`git push origin main` ist auto-mode-blocked)
- Bei jedem commit: nicht mehr als ein logisches Stueck
- User arbeitet parallel — `git status` checken BEVOR du `git add .` machst, sonst greifst du user's work
- Spezifisch staging: `git add <konkrete-files>`, nicht `git add -A`

---

## DON'T (Wiederholungen vermeiden)

- ❌ Lighting-System neu bauen (existiert in sf/lighting.py)
- ❌ AI-Sprites generieren ohne explizite User-Anweisung (procedural-pivot)
- ❌ `git add -A` (greift User-Parallelwork)
- ❌ `git push origin main` (auto-mode-block, user macht selbst)
- ❌ feathered alpha auf inner-pixels (siehe Update #176/#177 — Hard-Mask jetzt)
- ❌ Per-Frame trim (Update #175 — Union-BBox fuer Konsistenz)
- ❌ Doppelte Sprites/Tools bauen (erst `tools/list_stack.py --check`)

---

## DO (Best Practices)

- ✅ `python tools/list_stack.py` als erste Diagnose
- ✅ `python tools/asset_audit.py` vor Asset-Commits
- ✅ AskUserQuestion bei mehreren Optionen
- ✅ Tasks tracken mit TaskCreate fuer Multi-Step-Work
- ✅ Smoke-Tests vor jedem commit
- ✅ Doku-Files aktualisieren wenn Stack waechst
- ✅ Bei Asset-Konvention-Aenderung: `sf/render_spec.py` + `VELGRAD_RENDER_SPEC.md` synchron

---

## CONTACT-PERSONS

User: adrian.mirwaldt21@gmail.com — Repo: github.com/OsuGerman/shadowfall

---

**Stand:** 2026-05-24 (Update #179, TOOLBOX-Verankerung). Bei jeder neuen Library/Modul: hier nachpflegen.
