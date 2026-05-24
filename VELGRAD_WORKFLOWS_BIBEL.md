# VELGRAD WORKFLOWS BIBEL

> **Status:** v1.0 (2026-05-24)
> **Scope:** Scenario.gg Standard-Library Workflows + Velgrad-spezifische Verwendung
> **Begleit-Dokumente:** [VELGRAD_SPRITE_BIBEL.md](VELGRAD_SPRITE_BIBEL.md), [ROADMAP.md](ROADMAP.md), [PLAN.md](PLAN.md)

Diese Bibel dokumentiert die 4 Scenario.gg-Workflows, die wir gezielt einsetzen
um spezifische Asset-Probleme zu loesen, die mit einfacher Single-Sprite-
Generation (siehe `tools/sprite_gen.py`) NICHT machbar sind. Jeder Workflow hat
einen eigenen Runner unter `tools/workflow_*.py`. Die Workflows orchestrieren
mehrere Inference-Calls in einem festen Muster und produzieren strukturierte
Outputs (Sprite-Sheets, Mask-Sets, Variants).

---

## I. UEBERSICHT — Wann welcher Workflow

| Workflow | Loest welches Problem | Phase | Kosten/Run | Tool |
|---|---|---|---|---|
| **Character Sheet Generator** | 1 Konzept → 4 directional views (Front/Side/Back/3Q) | T2.6 Phase 3 (Animation-Foundation) | ~4 EUR / Charakter | `workflow_character_sheet.py` |
| **Sprite Animation Frames** | 1 Pose → 8-Frame Walk/Attack Cycle | T2.6 Phase 3 (Animation-Frames) | ~6 EUR / Cycle (oder 0 wenn extern erstellt) | `workflow_animation_frames.py` + Engine-Loader |
| **Texture Tiler** | 1 Floor + 1 Wall → 16-Mask modular Tileset | T2.7 Phase 4 (Modular Tilesets) | ~3 EUR / Biome ODER 0 (procedural) | `workflow_texture_tiler.py` |
| **Inpaint / Outpaint** | Decor-Variations, BG-Removal-Fixes, Door-Sprites, Wand-Boden-Transitions | jederzeit | ~0.25 EUR / Edit | `workflow_inpaint.py` |

Kostenbasis: Scenario.gg "creator" Plan, ~5000 images/Monat. Schaetzungen ohne
Re-Rolls; in der Praxis +30% fuer Quality-Iteration einplanen.

---

## II. WORKFLOW 1 — CHARACTER SHEET GENERATOR

### Zweck
Aus 1 Referenz-Charakter (z.B. unsere existierenden Klassen-Sprites wie
`warrior.png`) wird ein **4-Richtungs-Sprite-Sheet** generiert
(Front / Right-Side / Back / 3-Quarter-View). Das ist der **Foundation-Step**
fuer alle Top-Down-ARPG-Animationen — ohne 4-direction-Set kann der Spieler nicht
in 4 Richtungen laufen.

### Wann verwenden
- **T2.6 Phase 3:** vor dem Animation-Rigging-Workflow
- **Vorbedingung:** Ein "anchor"-Sprite existiert bereits (Front-View aus Phase 1)
- **NICHT verwenden** wenn der Charakter nur statisch dargestellt wird (Portrait, Boss-Plate)

### Input
- 1 Referenz-Sprite (PNG, transparent BG, idealerweise full-body Front-View)
- Character-Slug (z.B. `warrior`, `salzhueter_brut`)
- Stil-Anker: Master-Style-Prompt aus VELGRAD_SPRITE_BIBEL.md §I

### Output
- `assets/sprites/sheets/<slug>_4dir.png` (2048×2048, 2×2-Grid)
  - Top-Left: Front (S, Spieler schaut Kamera an)
  - Top-Right: Right-Side (E)
  - Bottom-Left: Back (N)
  - Bottom-Right: 3-Quarter-Front-Right (SE, Standard-Lauf-Pose)
- `assets/sprites/sheets/<slug>_4dir.meta.json` mit Sub-Sprite-Bounds + Hashes

### Pipeline-Schritte
1. Reference-Sprite laden + an Scenario hochladen (assets-Upload)
2. 4× Inference-Call mit direction-spezifischem Prompt:
   - Front: "facing camera, frontal full-body pose"
   - Side: "perfect side profile, 90 degrees turn right"
   - Back: "back view, away from camera, full-body"
   - 3Q: "three-quarter front-right view, dynamic walking pose"
3. Jeder Call: same character, same style, same proportions (style-locked via referenceImages)
4. Composit zu 2×2-Sheet via Pygame
5. Optional BG-Removal je Sub-Sprite (threshold=18, feather=10)
6. Manifest-Eintrag in `assets/sprite_manifest.json`

### CLI
```bash
# Dry-Run (Kosten anzeigen, keine API-Calls)
python tools/workflow_character_sheet.py --target warrior --dry-run

# 1 Klasse: full sheet
python tools/workflow_character_sheet.py --target warrior

# Alle 8 Klassen (Tier 3.4)
python tools/workflow_character_sheet.py --all-classes

# Eigenes Modell forcen
python tools/workflow_character_sheet.py --target warrior --model model_a2dvNsgst7PCnpiucRY7bEHW
```

### Status — Kandidaten
| Slug | Anchor-Sprite vorhanden | 4-Dir-Sheet | Status |
|---|---|---|---|
| warrior | ✓ classes/warrior.png | — | pending |
| witch | ✓ classes/witch.png | — | pending |
| sorceress | ✓ classes/sorceress.png | — | pending |
| monk | ✓ classes/monk.png | — | pending |
| ranger | ✓ classes/ranger.png | — | pending |
| mercenary | ✓ classes/mercenary.png | — | pending |
| huntress | ✓ classes/huntress.png | — | pending |
| druid | ✓ classes/druid.png | — | pending |

**Roadmap-Hinweis:** Erst NACH erfolgreichem Pilot-Test mit 1 Klasse (warrior)
sollten alle 8 batch-generiert werden. Kosten: ~32 EUR fuer alle 8 Klassen.

---

## III. WORKFLOW 2 — SPRITE ANIMATION FRAMES

### Zweck
Aus 1 Idle-Pose werden **8 Animation-Frames** (Walk-Cycle oder Attack-Cycle)
generiert. Das ergibt eine fluessige Bewegungs-Sequenz fuer Top-Down-ARPG-
Charaktere. Funktioniert pro Richtung (also 8 Frames × 4 Richtungen = 32 Frames
pro vollstaendigem Walk-Cycle).

### Wann verwenden
- **T2.6 Phase 3:** Nach Character-Sheet-Generator
- **Vorbedingung:** 4-Direction-Sheet vorhanden (Workflow 1)
- **Pro Animation-Type:** Walk, Run (optional), Attack-Light, Attack-Heavy, Hit-React, Death
- **Pro Klasse:** Mindestens Walk + Attack-Light + Death (3 Cycles)

### Input
- 1 Anchor-Pose (z.B. Front-View aus 4-Dir-Sheet)
- Animation-Type: `walk` | `attack_light` | `attack_heavy` | `hit_react` | `death` | `idle_breath`
- Direction (S/E/N/W) — bestimmt welche Sub-Sprite vom 4-Dir-Sheet als Anchor genutzt wird

### Output
- `assets/sprites/sheets/<slug>_<anim>_<dir>_8f.png` (1024×128, 1×8-Strip)
- Metadata: Frame-Rate-Hint (Walk: 12fps, Attack: 18fps, Death: 8fps)

### Pipeline-Schritte
1. Anchor-Pose laden
2. 8× Inference-Call mit per-Frame-Phase-Prompt:
   - Walk-Cycle: contact-pass (1), down-pass (2), passing-pose (3), up-pass (4), contact-pass-opposite (5), down-opposite (6), passing-opposite (7), up-opposite (8)
   - Attack-Cycle: wind-up start (1-3), strike-peak (4-5), follow-through (6-7), return-to-idle (8)
3. style-lock via referenceImages = [anchor]
4. Composit zu 1×8-Strip
5. Manifest-Eintrag

### CLI
```bash
# Walk-Cycle fuer warrior, S-Direction
python tools/workflow_animation_frames.py --target warrior --anim walk --dir S

# Attack-Cycle fuer alle 8 Klassen, alle 4 Richtungen
python tools/workflow_animation_frames.py --all-classes --anim attack_light

# Dry-Run
python tools/workflow_animation_frames.py --target warrior --anim walk --dry-run
```

### Status — Kandidaten
Erst nach Workflow 1 sinnvoll. Priorisierung:
1. **Pilot:** warrior walk_S (8 Frames) — Cost: ~6 EUR
2. **Volltest:** warrior alle 4 Richtungen walk (32 Frames) — Cost: ~24 EUR
3. **Skalierung:** alle 8 Klassen × 3 Anims × 4 Richtungen = 96 Strips × 8 Frames = 768 Calls — Cost: ~190 EUR

Phase 3 wird daher **selektiv** ausgerollt: erst Held-der-Stunde (warrior), dann
On-demand-Erweiterung wenn Engine die Frames wirklich nutzt.

### Engine-Integration (Update #164)

Walk-Sheets werden von `sf/sprites.py` automatisch geladen wenn unter
`assets/sprites/classes/<class>_walk/<class>_<dir>.png` vorhanden:

- **Konvention:** 1 horizontaler Strip pro Direction (down/up/left/right),
  enthaelt 8 gleich-breite Frames
- **Direction-Lookup:** `direction_from_facing(p.facing)` → 'down'|'up'|'left'|'right'
- **Frame-Picker:** `int(walk_phase % 8)` — laeuft mit dem existierenden
  Procedural-Walk-Phase-Counter mit
- **Auto-Trim:** transparente Borders um den Charakter werden beim Load
  weggecroppt → maximale Cell-Auslastung
- **Fallback-Kette:** Walk-Anim → Static-Sprite (`<class>.png`) → Procedural-Composit
- **Hot-Reload:** `sprites.reload_sprite_cache()` leert auch den Walk-Frame-Cache

**Externe Quellen** sind erlaubt (selber rendern, AI-Tools wie Krea/Leonardo,
gepatchte Workflows). Wichtig: nach dem Generieren ggf. via
`tools/sprite_postprocess.py --bg white|black` den BG transparent machen
(Vorsicht: PNGs aus manchen Tools sind 24-bit RGB ohne Alpha-Channel und
brauchen Postprocess auch wenn sie "transparent" aussehen).

**Pilot abgeschlossen:** Monk (Update #164) — 4 Direction-Strips à 8 Frames,
auto-trimmed, in-Game als walking Animation sichtbar.

### Update #165: Vollstaendige Animation-State-Machine

Engine-Side ist jetzt komplett — die folgenden Animation-Types werden
unterstuetzt sobald Sheets vorhanden sind, **mit procedural Fallback wenn
Sheets fehlen**:

| Anim   | Frames | FPS | Loop | Dir | Trigger / Auto                       |
|--------|--------|-----|------|-----|--------------------------------------|
| idle   | 4      | 4   | ja   | ja  | auto bei !p.moving                   |
| walk   | 8      | 10  | ja   | ja  | auto bei p.moving                    |
| attack | 6      | 14  | nein | ja  | sf/game.py Basic-Attack-Hook         |
| hit    | 4      | 12  | nein | ja  | sf/combat.py damage_player           |
| cast   | 6      | 10  | nein | ja  | sf/skills.py _apply_cd (alle Skills) |
| death  | 8      | 8   | nein | nein| sf/combat.py wenn p.hp<=0            |

**Procedural Visual-Fallback** wenn ein Anim-Sheet fehlt:
- **attack** → Scale-Pulse (0.95 → 1.10 → 1.0) + Forward-Shake
- **hit** → Red-Tint-Multiplikation + Backward-Shake (fade-out ueber Cycle)
- **cast** → Aspekt-Aura (Klassen-Farbe, pulsing) + leichter Scale-Up
- **death** → Slide-Down (0.5x sprite-height) + Fade-Out (0.7x alpha) + Horizontal-Collapse

Damit ist der Monk (oder jede Klasse) **sofort spielbar mit allen
Anim-States**, auch wenn nur das Walk-Sheet existiert. Sobald
weitere Sheets generiert werden, schalten sie automatisch auf die
AI-Frames um.

**Filename-Konvention (Update #165):**
```
assets/sprites/classes/<class>_anims/
├── idle/<dir>.png        (4 Frames horizontaler Strip)
├── walk/<dir>.png        (8 Frames)
├── attack/<dir>.png      (6 Frames)
├── hit/<dir>.png         (4 Frames)
├── cast/<dir>.png        (6 Frames)
└── death/all.png         (8 Frames, non-directional)
```
`<dir>` ∈ `(down, up, left, right)`. Backward-Compat: alte `<class>_walk/`
Convention bleibt fuer `anim=walk` erhalten.

---

## IV. WORKFLOW 3 — TEXTURE TILER (DER WICHTIGE)

### Zweck
**Loest das Modular-Tile-Problem strukturell.** Aus 1 base floor tile + 1 base
wall tile pro Biome wird ein **16-Pattern-Mask-Set** generiert, sodass die
Engine pro Floor-Cell die korrekte Edge-Variante blittet — ohne sichtbare
Wiederholungs-Pattern, mit sauberen Wand-Uebergaengen wie POE2/Hades/D2.

### Modi
**Modus A — Procedural (Default, 0 Kosten):**
Bakt unser existierendes Edge-Overlay-System (siehe `sf/sprites.py
get_edge_overlay`) in 16 separate PNG-Masks pro Biome aus. Nutzt:
- Base Floor-Tile (z.B. `crypt_floor_a.png`)
- Base Wall-Tile (`crypt_wall_w.png`)
- Procedural Edge-Shadow-Gradient (32% depth, alpha 170→0)
- Wall-Average-RGB fuer Color-Bleed (15% wall-tint)

Output: 16 PNGs pro Biome, direkt von der Engine ladbar.

**Modus B — AI-Hybrid (Optional, ~3 EUR/Biome):**
Generiert 4 transition-edge Tiles (N/E/S/W floor-meets-wall) via Scenario.gg
img2img mit dem Hand-Painted Textures Modell + dem Base-Floor als Reference.
Composit dann mit Procedural-Shadows zu 16-Mask-Set. Resultat: realistischere
Stein-/Moos-/Risse an den Kanten, nicht nur abstrakter Schatten.

### Wann verwenden
- **T2.7 Phase 4:** Wenn ein Biome mit Auto-Tile-Edge-Overlays optisch funktioniert (Crypt ✓)
- **Vor weiteren Biomes:** Sicherstellen dass der Wall-Tile-Stil zum Floor passt
- **Modus B nur wenn Procedural sichtbar zu generisch aussieht** (Crypt = OK, Lava + Astral koennten Modus B brauchen)

### Input
- Biome-Slug (`crypt`, `frost`, `lava`, ...)
- Pflicht: Floor-Tile + Wall-Tile bereits in TILE_VARIANT_MAP / TILE_WALL_MAP
- Modus A: `--procedural` (default)
- Modus B: `--ai-hybrid`

### Output
- `assets/sprites/tiles/<biome>_mask_<NN>.png` fuer NN in 00..15
- Bitmask-Konvention: NN = N(1) | E(2) | S(4) | W(8)
- `assets/sprites/tiles/<biome>_mask_index.json` mit Pattern-Hashes

### Pipeline-Schritte (Modus A)
1. Floor + Wall laden
2. Wall-Average-RGB sampeln (16×16 grid)
3. Pro Mask-Pattern (0..15):
   - Floor blitten
   - Edge-Shadow-Gradient pro gesetzter Bit (N/E/S/W)
   - Color-Bleed-Tint (15% Wand-Farbe)
4. PNG schreiben + Hash-Index aktualisieren

### Pipeline-Schritte (Modus B, optional)
1. Modus A komplett ausfuehren (Procedural Masks als Basis)
2. Pro Richtung N/E/S/W:
   - Composit "floor + wall at edge" als Inpaint-Mask
   - Scenario img2img mit Prompt "seamless transition between {floor_material} and {wall_material}, weathered, naturally worn"
3. AI-generierte Edge-Tiles in die 12 wandberuehrenden Masks integrieren

### CLI
```bash
# Procedural Mask-Set fuer Crypt (kostenlos, sofort)
python tools/workflow_texture_tiler.py --biome crypt --procedural

# Alle Biome procedural die Wall haben
python tools/workflow_texture_tiler.py --all --procedural

# AI-Hybrid fuer Lava (3 EUR)
python tools/workflow_texture_tiler.py --biome lava --ai-hybrid

# Dry-Run
python tools/workflow_texture_tiler.py --biome crypt --ai-hybrid --dry-run
```

### Status — Biome-Readiness
| Biome | Floor | Wall | Edge-Overlay aktiv | Mask-Set generiert |
|---|---|---|---|---|
| crypt | ✓ | ✓ | ✓ | ✗ (next) |
| frost | ✓ | ✗ | ✗ | — |
| lava | ✓ | ✗ | ✗ | — |
| swamp | ✓ | ✗ | ✗ | — |
| astral | ✓ | ✗ | ✗ | — |
| desert | ✓ | ✗ | ✗ | — |
| town | ✓ | ✗ | ✗ | — |
| wound_salt | ✓ | ✗ | ✗ | — |
| wound_ash | ✓ | ✗ | ✗ | — |
| wound_hollow | ✓ | ✗ | ✗ | — |
| hollow_word | ✓ | ✗ | ✗ | — |

**Naechster Schritt:** Walls fuer die 10 verbleibenden Biome generieren (via
`sprite_gen.py --category tile` mit T*w-Prefix in der Bibel), dann
`workflow_texture_tiler.py --all --procedural` laufen lassen.

---

## V. WORKFLOW 4 — INPAINT / OUTPAINT

### Zweck
Gezielte Bild-Modifikationen mittels Mask + Prompt. **Allzweck-Werkzeug** fuer:
- BG-Removal-Fehler nachbessern (Restpixel, Schatten-Reste)
- Decor-Variations (1 Fass → 5 verschiedene Faesser)
- Door-Sprites aus Wand-Tiles ableiten
- Wand-Boden-Uebergaenge wo Modus A des Texture-Tilers nicht reicht
- Item-Icon-Polish (Glow hinzufuegen, Material wechseln)

### Wann verwenden
- **Jederzeit** wenn ein Sprite "fast richtig" ist und nur ein bestimmter Bereich angepasst werden soll
- **Vor einem Re-Generate** — Inpaint ist 10× billiger als kompletter Re-Run
- **Fuer Variations** — gleiche Komposition, anderer Inhalt im maskierten Bereich

### Input
- Source-Image (PNG)
- Mask-Image (PNG, weiss = inpaint, schwarz = keep) ODER Mask-Bounds (x,y,w,h)
- Prompt: Was im maskierten Bereich erscheinen soll
- Strength: 0.0..1.0 (wie stark der Bereich veraendert wird; 0.7 default)

### Output
- `assets/sprites/<category>/<source_id>_inpaint_<seed>.png`

### Pipeline-Schritte
1. Source + Mask laden (oder Mask aus Bounds bauen)
2. Beide an Scenario hochladen
3. Inference mit type=`img2img-mask`, prompt, strength, modelId
4. Download Result
5. Optional: Source ersetzen wenn `--replace` flag

### CLI
```bash
# Mit Mask-Datei
python tools/workflow_inpaint.py \
    --image assets/sprites/classes/warrior.png \
    --mask masks/warrior_helmet.png \
    --prompt "ornate gold helmet, dragon motif"

# Mit Bounds (kein Mask-File noetig)
python tools/workflow_inpaint.py \
    --image assets/sprites/tiles/lava_akt_3.png \
    --bounds 0,0,512,80 \
    --prompt "stone wall transitioning into lava floor, weathered"

# 5 Decor-Variations aus 1 Fass
python tools/workflow_inpaint.py \
    --image assets/sprites/decor/barrel.png \
    --bounds 50,50,200,200 \
    --prompt "weathered barrel, broken slats" \
    --variants 5
```

### Use-Cases — Konkret fuer Velgrad

| Use-Case | Source | Mask | Prompt |
|---|---|---|---|
| Door aus Crypt-Wall | crypt_wall_w.png | mittlerer Rechteck | "wooden door, iron hinges, gothic" |
| Helm-Variante Warrior | classes/warrior.png | Kopf-Bereich | "horned warrior helmet" |
| Faesser-Variations | decor/barrel.png | Body-Bereich | 5× verschiedene Prompts |
| BG-Reste entfernen | mobs/salzhueter_brut.png | Ecken | "transparent background" + strength=1.0 |

### Status
- **Tool implementiert** ✓
- **Use-Cases offen** — wird on-demand verwendet, kein Batch-Pass geplant
- **Budget-Reserve:** ~5 EUR/Monat fuer Polish-Inpaints

### External-Tool Fallback fuer BG-Removal

Wenn `tools/sprite_postprocess.py` einen schwarzen Halo um den Charakter
nicht vollstaendig entfernen kann (kompressionsartefakte / Anti-Aliased-
Outlines aus Scenario.gg), nutze **https://ai.nero.com/background-remover/**
als externen Fallback:

1. Lade das problematische PNG dort hoch
2. Klick "Remove Background"
3. Download das saubere PNG
4. Ersetze die Datei in `assets/sprites/<category>/<id>.png`
5. F5 im Game → Hot-Reload via `sprites.reload_sprite_cache()`

Validiert fuer: `classes/warrior.png` (Update #163). Vorteil: ai.nero.com
versteht Anti-Aliased-Edges deutlich besser als unsere brightness-basierte
Flood-Fill-Heuristik und produziert butterweiche Silhouetten.

Verwende es als **erste Wahl** wenn:
- Sprite hat dunkle Innenbereiche die Flood-Fill aufessen koennte
- Anti-Aliased-Rand mit Black-Halo
- Single-Sprite Polish ist noetig (zu wenig fuer Batch)

Eigenes Tool (`sprite_postprocess.py`) bleibt fuer Batch-Verarbeitung (alle
8 Klassen auf einmal, headless im Workflow).

---

## VI. GEMEINSAME INFRASTRUKTUR

### `tools/workflow_runner.py`
Shared Base-Class `WorkflowBase` mit:
- `submit()` — generischer Scenario-Inference-Call
- `poll()` — Job-Polling mit Timeout
- `download()` — Asset-Fetch
- `composit_grid(images, cols, rows)` — Sprite-Sheet-Compositor (Pygame)
- `audit_log(workflow_name, args, result)` — Append to `assets/workflow_runs.json`

### Audit-Log
Jeder Workflow-Run wird in `assets/workflow_runs.json` protokolliert:
```json
{
  "runs": [
    {
      "timestamp": "2026-05-24T18:30:00Z",
      "workflow": "character_sheet",
      "args": {"target": "warrior"},
      "outputs": ["assets/sprites/sheets/warrior_4dir.png"],
      "cost_estimate_eur": 4.0,
      "scenario_inference_ids": ["job_abc...", "job_def...", "job_ghi...", "job_jkl..."],
      "duration_sec": 87.3,
      "status": "success"
    }
  ]
}
```

Damit ist nachvollziehbar:
- Wieviel haben wir wofuer ausgegeben
- Welche Sprites kamen aus welchem Workflow
- Reproducibility: dieselbe `args`-Hash erzeugt dieselbe Output-ID

### Secrets — Reminder
`scenario.txt` enthaelt id+secret. **Niemals committen.** `.gitignore`
sperrt: `scenario.txt`, `Scenario.txt`, `.scenario_key`. Bei Verdacht auf Leak:
sofort revoken auf https://app.scenario.com/team

---

## VII. ROADMAP-ANBINDUNG

| ROADMAP-Tier | Workflow | Aktion |
|---|---|---|
| T2.5 (Phase 2 Sprites) | Inpaint | Decor-Variations, Items-Polish |
| **T2.6 (Phase 3 Animation)** | **Character Sheet → Animation Frames** | Heroes-Animation |
| T2.7 (Phase 4 Modular) | **Texture Tiler** | Per-Biome 16-Mask Sets |
| jederzeit | Inpaint | Spot-Fixes |

Siehe ROADMAP.md §W (Workflows) fuer detaillierte Sprint-Planung.

---

## VIII. WORKFLOW-LIFECYCLE

```
                                   ┌─────────────────┐
   Idee / Bedarf  ───────────────► │ Workflow waehlen│
                                   └────────┬────────┘
                                            │
                          ┌─────────────────┴────────────────┐
                          │                                  │
                          ▼                                  ▼
                  ┌──────────────┐                  ┌────────────────┐
                  │ Dry-Run      │                  │  Cost-Check    │
                  │ (Kosten)     │                  │  (Plan-Budget) │
                  └──────┬───────┘                  └────────┬───────┘
                         │                                   │
                         └──────────────┬────────────────────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Execute     │
                                 └──────┬───────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Audit-Log   │  ──►  assets/workflow_runs.json
                                 └──────┬───────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  Manifest    │  ──►  sf/sprite_registry.py
                                 │  Update      │
                                 └──────┬───────┘
                                        │
                                        ▼
                                 ┌──────────────┐
                                 │  In-Engine   │  ──►  F5 Hot-Reload
                                 │  Validate    │
                                 └──────────────┘
```

---

## IX. CHEAT-SHEET

```bash
# Pipeline 1 — Single Sprite (existing)
python tools/sprite_gen.py --target salzhueter_brut

# Pipeline 2 — Workflow Runners (neu)
python tools/workflow_character_sheet.py --target warrior         # 4-Dir-Sheet
python tools/workflow_animation_frames.py --target warrior --anim walk --dir S
python tools/workflow_texture_tiler.py --biome crypt --procedural   # 16 Masks
python tools/workflow_inpaint.py --image X --bounds X,Y,W,H --prompt "..."

# Diagnose
python tools/scenario_list_models.py --search "fantasy"   # verfuegbare LoRAs
python tools/sprite_postprocess.py <png> --threshold 18   # BG-Removal-Fix
```

---

**Stand:** 2026-05-24. Wartung: jede Bibel-Erweiterung MUSS hier verzeichnet
sein damit die Workflows zentral steuerbar bleiben.
