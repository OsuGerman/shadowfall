# VELGRAD RENDER SPEC

> **Status:** v1.0 (2026-05-24)
> **Zweck:** Single-Source-of-Truth fuer Kamera, Distanz, Aufloesung, In-Game-Size und Hintergrund-Policy aller Asset-Typen. Jede AI-Generation MUSS sich an die hier verankerten Werte halten damit alle Assets visuell zum Rest des Spiels passen.
> **Code-Anker:** [sf/render_spec.py](sf/render_spec.py) (RENDER_SPEC dict)
> **Begleit-Docs:** [_legacy/VELGRAD_SPRITE_BIBEL.md](_legacy/VELGRAD_SPRITE_BIBEL.md), [_legacy/VELGRAD_WORKFLOWS_BIBEL.md](_legacy/VELGRAD_WORKFLOWS_BIBEL.md)

---

## I. WARUM EINE SPEC BRAUCHEN

Velgrad-Sprites entstehen in 3 unterschiedlichen Pipelines:
1. **`tools/sprite_gen.py`** — Single-Sprite Batch aus VELGRAD_SPRITE_BIBEL
2. **`tools/workflow_*.py`** — Multi-Inference-Workflows (Character-Sheet, Animation-Frames, Texture-Tiler, Inpaint)
3. **Extern** — User generiert selbst via ai.nero.com / Krea / Leonardo / etc.

Ohne zentrale Spec passieren Inkonsistenzen:
- Mob-Sprite hat eye-level-Kamera, aber Welt rendert top-down → Klotz auf Boden
- Portrait ist full-body statt head&shoulders → schluckt UI-Platz
- Tile hat Charakter drauf statt seamless → Patchwork
- Item-Icon ist 512×512 statt 128×128 → riesig im Inventar

**Die Spec verankert die richtigen Werte fuer jeden Verwendungs-Kontext.**

---

## II. ASSET-KATEGORIEN — UEBERSICHT

| Kategorie | Kamera | Distanz | Source-Resolution | In-Game-Render-Size | BG-Policy |
|---|---|---|---|---|---|
| **class** | 3/4 top-down ARPG | full body (Kopf bis Fuss) | 512×768 (2:3) | `target_h = radius * 6.0` (~108px) | transparent (alpha=0) |
| **class_walk** | 3/4 top-down ARPG | full body | 8 Frames × 313×627 (~1:2 pro Frame) | wie class | transparent |
| **class_idle** | 3/4 top-down ARPG | full body, subtile-breath-Variants | 4 Frames × 313×627 | wie class | transparent |
| **class_attack** | 3/4 top-down ARPG | full body + weapon-arc-space | 6 Frames × 313×627 | wie class | transparent |
| **class_hit** | 3/4 top-down ARPG | full body (recoil-pose) | 4 Frames × 313×627 | wie class | transparent |
| **class_cast** | 3/4 top-down ARPG | full body + aspekt-glow-space | 6 Frames × 313×627 | wie class | transparent |
| **class_death** | 3/4 top-down ARPG | full body → liegend | 8 Frames × 313×627 (non-directional) | wie class | transparent |
| **mob** | 3/4 top-down ARPG | full body | 512×512 (1:1) | `target_h = radius * 2.5` (~45-80px) | transparent |
| **boss_plate** | cinematic 3/4 hero shot | full body, intimidating angle | 512×512 (1:1) | drawn full-modal-size in Intro | atmospheric (Lore-Mood-BG erlaubt) |
| **portrait** | head-and-shoulders frontal | upper body + Kopf | 256×256 (1:1) | drawn ~128×128 in Dialog-UI | dark vignette (gradient) |
| **tile** | top-down orthographic | KEIN Subjekt, nur Material | 512×512 (1:1) | scaled zu `cell+1` px (32-128) | seamless tileable, KEIN Charakter |
| **tile_wall** | top-down orthographic | KEIN Subjekt | 512×512 | scaled zu `cell+1` | seamless, Wand-Material |
| **item_icon** | frontal isolated, slight 3D-twist | full object centered | 128×128 (1:1) | drawn 32-48px im Inventar/HUD | transparent |
| **decor** (geplant) | 3/4 top-down ARPG | full object | 256×256 (1:1) | drawn 32-64px in der Welt | transparent |
| **ui_card_portrait** (derived) | reused from `class` | reused | reused (512×768) | 50% Card-Hoehe, Vignette-Frame | vignette-masked |
| **ui_detail_hero** (derived) | reused from `class` | reused | reused (512×768) | 42% Panel-Width, Aspekt-Aura+Doppel-Rahmen | vignette-masked |
| **decor_skill_vfx** (geplant) | frontal flat | impact-shape | 256×256 oder 256×128 | drawn dynamisch ueber dem Treffer | transparent |

---

## III. KATEGORIE-DETAIL-SPEC

### III.A — class (Static Hero, full-body)

**Beispiel:** `assets/sprites/classes/warrior.png`, `monk.png`

**Camera-Prompt:**
> "3/4 top-down ARPG view, camera slightly elevated looking down, character oriented south facing the camera with body angled naturally toward viewer, full body visible head to toe, centered subject, sprite-ready composition"

**Distance:** Full body, kompletter Charakter von Kopf bis Fuesse, ~10% Padding oben/unten, zentriert

**Resolution:** 512×768 (2:3 Aspect Ratio — vertikal, da Charakter mehr hoch als breit)

**In-Game-Size:** `target_h = player.radius * 6.0`
- `radius = 18` → render-height = 108px
- ~12% der 900px Screen-Hoehe (POE2-/D2-Proportion)

**BG-Policy:** Transparent. Schwarz (oder weiss) im Source erlaubt — wird per `tools/sprite_postprocess.py --bg black|white` zu Alpha=0 konvertiert.

**Verwendet von:** Engine-Player-Render, Title-Screen Class-Card, Title-Screen Detail-Hero-Portrait (3 Verwendungen, 1 Asset)

---

### III.B — class_walk + class_idle + class_attack + class_hit + class_cast + class_death

**Beispiel:** `assets/sprites/classes/monk_anims/walk/down.png`

**Camera-Prompt:** Identisch zu `class` PLUS die Bewegungs-Phase-Description:
> "[same character as reference], [DIRECTION_DESC], [ANIM_FRAME_PROMPT], consistent style and proportions, top-down ARPG sprite, transparent background, single frame in animation cycle"

**Distance:** Identisch zu `class` (full body), aber pro Anim mit reserviertem Wing-Space:
- `attack`/`cast`: ~15% horizontal Extra-Space fuer Weapon-Arc / Aspekt-Glow
- `death`: vertikal "schrumpfend" → letzter Frame ist liegend, also Breite > Hoehe

**Resolution pro Frame:** ~313×627 (entstanden aus 2504×627 Strip / 8 Frames). Aspect ~1:2.

**Frame-Counts** (siehe `sf/sprite_animation.py ANIM_CONFIG`):
- idle: 4 frames @ 4 fps, looping
- walk: 8 frames @ 10 fps, looping
- attack: 6 frames @ 14 fps, one-shot
- hit: 4 frames @ 12 fps, one-shot
- cast: 6 frames @ 10 fps, one-shot
- death: 8 frames @ 8 fps, one-shot, **non-directional** (1 Strip statt 4)

**Strip-Layout:** Horizontale Reihung, alle Frames gleich-breit, Frame-Width = `strip_width / frame_count`

**Filename-Convention:**
- Directional: `assets/sprites/classes/<class>_anims/<anim>/<dir>.png` mit `<dir>` in `(down, up, left, right)`
- Non-directional (death only): `<class>_anims/<anim>/all.png`

**Backward-Compat:** Walk-Anim akzeptiert auch alte `<class>_walk/<class>_<dir>.png`-Convention

**In-Game-Size:** Identisch zu `class` (target_h * 6.0). Auto-Trim crop entfernt leere Transparent-Borders sodass Charakter Cell optimal ausfuellt.

**BG-Policy:** Transparent (alpha=0 nach BG-Removal). Weiss-Halo-Vermeidung: RGB der alpha=0-Pixel wird vor Render zu (0,0,0) genullt damit smoothscale keinen weissen Halo erzeugt.

---

### III.C — mob (Bestiary-Sprites)

**Beispiel:** `assets/sprites/mobs/salzhueter_brut.png`

**Camera-Prompt:**
> "3/4 top-down ARPG view, camera slightly elevated, full-body creature centered, isolated character on plain pure-black background, no environment, sprite-ready composition, top-down hero shot angle"

**Distance:** Full body (smaller creatures: more padding um den Body, sodass alle Mob-Sprites die gleiche Body-fill-ratio haben)

**Resolution:** 512×512 (1:1 quadratisch, da Mobs in der Cell-Position rendern und nicht so vertikal sind wie Heroes)

**In-Game-Size:** `target_h = enemy.radius * 2.5`
- Kleinere Mobs (radius 14) → 35px tall
- Groessere Mobs (radius 28) → 70px tall
- Boss-Mobs (radius 40+) → 100-150px

**BG-Policy:** Transparent. Schwarz im Source wird via postprocess weggemacht.

**Style-Anker:** Master-Style (POE2 Dark Fantasy painterly) + Lore-Beschreibung aus ../gameplay/VELGRAD_BESTIARIUM.md

---

### III.D — boss_plate (Cinematic-Intro)

**Beispiel:** `assets/sprites/bosses/vehren.png`

**Camera-Prompt:**
> "cinematic dark fantasy boss render, full-body intimidating angle, dramatic atmospheric lighting, hero-shot composition, painterly POE2 style, atmospheric background showing boss arena setting"

**Distance:** Full body, intimidating-angle (leicht von unten oder direkt frontal), Lore-Atmosphäre im BG erlaubt

**Resolution:** 512×512

**In-Game-Size:** Modal-fuellend in Boss-Intro-Splash (ca. 600×600 zentral)

**BG-Policy:** Atmospheric. Boss-Arena darf sichtbar sein (e.g. Salzhuter-Brut in Marrowport-Salzwasser, Vehren in Heaven-Aether-Pavillon). NICHT transparent — das ist absichtlich.

---

### III.E — portrait (NPC-Dialog-UI)

**Beispiel:** `assets/sprites/portraits/korven_vor.png`

**Camera-Prompt:**
> "head and shoulders portrait, frontal eye-contact composition, upper body and face visible, simple dark vignette gradient behind subject, no detailed environment, focus on face and upper torso, painterly POE2 style"

**Distance:** Schulter + Kopf, Kamera auf Augenhoehe (NICHT top-down, da Dialog-Kontext intimer ist als World-View)

**Resolution:** 256×256 (1:1, kleiner als class weil weniger Detail noetig in der UI)

**In-Game-Size:** ~128×128 px in Dialog-Modal (links neben Text)

**BG-Policy:** Dark vignette gradient. Charakter ist die Hauptattraktion, BG hilft Kontrast ohne abzulenken. NICHT transparent — der dunkle Vignette-BG IST der Dialog-UI-Hintergrund.

**Style-Anker:** Mehr Detail im Gesicht als bei class-Sprites (da man ihn aus der Naehe sieht)

---

### III.F — tile (Boden-Texturen)

**Beispiel:** `assets/sprites/tiles/crypt_floor_a.png`

**Camera-Prompt:**
> "seamless repeating tileable ground texture, completely flat top-down orthographic view straight down from above, no perspective, no depth, no walls, no pillars, no arches, no architecture, no buildings, no scenery, no horizon, no sky, no characters, no objects, uniform floor pattern only, edges loop perfectly, no central focal point, repeatable game-map tile, pure flat ground material, hand-painted POE2 texture style"

**Negative-Prompt-Pflicht:** `walls, pillars, arches, columns, buildings, scenery, horizon, perspective, depth, sky, character, person, creature, archway, ruins, statue, doorway, room, sunbeams, god rays`

**Distance:** Kein Subjekt — direkt von oben gesehen, alles im gleichen Materialgrad

**Resolution:** 512×512 (1:1, fuer reibungsloses Skalieren auf cell-size)

**In-Game-Size:** Scaled zu `grid.cell + 1` Pixel (32-128 px je nach Zoom-Level)

**BG-Policy:** N/A — kein BG, die ganze Surface IST das Material

**Variants (T<i>a/b/c/d):** Mehrere Variants pro Biome um Patchwork-Look zu vermeiden, allerdings nur falls Variants visuell harmonisch sind (User-Feedback 2026-05-24: 4 Crypt-Variants ergaben Patchwork-Chaos → temporaer auf 1 reduziert)

**Variants T<i>w:** Wall-Tile-Variante mit gleicher Konvention, aber Wand-Material statt Boden

---

### III.G — item_icon (Inventar/HUD)

**Beispiel:** `assets/sprites/items/<sword>.png` (geplant, Phase 2)

**Camera-Prompt:**
> "single isolated weapon centered, frontal with slight 3D-twist for depth, pure-black background, no environment, item-card style, painterly POE2 detail, sharp focus, sprite-ready"

**Distance:** Komplettes Item zentriert, ~10% Padding aussen

**Resolution:** 128×128 (1:1, klein wegen Inventar-Use)

**In-Game-Size:** ~32-48px im Inventar-Grid, ~24px im Skill-Bar/HUD

**BG-Policy:** Transparent (Schwarz im Source → postprocess)

**Style-Anker:** Fantasy-Blades LoRA (Scenario.gg model_FHNbZENXLkay9bUNwMxo8e77)

---

### III.H — ui_card_portrait + ui_detail_hero (Title-Screen Verwendung)

**Beispiel:** Verwendet `assets/sprites/classes/monk.png` als Source

**Wichtig:** Das sind KEINE separaten Assets — sie reusen die existierenden class-Sprites. Die UI rendert sie nur unterschiedlich:

**ui_card_portrait** (Class-Card):
- Source: `class` Sprite (512×768)
- Rendered-Size: 50% der Card-Hoehe (Card ist 180×198 → Portrait 156×91 px nach Aspect-Fit)
- BG-Handling: Vignette-Fade (Side-Edges + Bottom) versteckt unbeabsichtigte BG-Reste

**ui_detail_hero** (Detail-Panel rechts):
- Source: `class` Sprite (512×768)
- Rendered-Size: 42% der Panel-Width (~300×420 px nach Aspect-Fit)
- BG-Handling: Faktion-Aura-Glow hinter dem Sprite, Doppel-Rahmen, Vignette-Fades

**Implikation:** class-Sprites muessen so generiert werden dass sie 3 Verwendungen aushalten (Engine-Render + UI-Card + UI-Detail). Daher 512×768 statt kleiner — gibt genug Detail fuer das grosse Detail-Hero ohne pixelig zu wirken.

---

## IV. RESPONSIVE-DESIGN-REGEL

Folgende Werte sind **proportional** zur Engine-Konfiguration, nicht fixe Pixel:

| Variable | Wert | Source |
|---|---|---|
| `player.radius` | 18 | sf/constants.py |
| `enemy.radius` | 14-50 (mob-spezifisch) | bestiary |
| Screen-Resolution | 1600×900 (default) | sf/constants.py SCREEN_W/H |
| Title-Screen Card-Size | 180×198 | sf/ui.py TitleUI.draw |
| Title-Screen Card-Grid | 4×2 | sf/ui.py TitleUI.draw |
| Title-Screen Panel-Width | `SCREEN_W - grid_w - 88` | sf/ui.py TitleUI.draw |

**Wenn jemand die Engine-Werte aendert** (z.B. radius 18 → 20 fuer einen mod), passen sich alle Sprite-Render-Sizes automatisch an, weil sie via `radius * multiplier` berechnet werden — die Multiplier sind die einzigen fixen Werte.

---

## V. PROMPT-BAUSTEINE (zu RENDER_SPEC.PROMPT)

Jeder Generator (sprite_gen, workflow_*) komponiert Prompts nach folgendem Schema:

```
[MASTER_POSITIVE]
  ↳ POE2 dark fantasy painterly, volumetric lighting, etc.

[CATEGORY_CAMERA]
  ↳ "3/4 top-down ARPG view, camera slightly elevated looking down"
     (variiert pro Kategorie — class/mob/portrait/boss_plate/tile/item)

[CATEGORY_DISTANCE]
  ↳ "full body, head to toe visible, centered"
     (variiert pro Kategorie — class/mob = full body, portrait = head&shoulders, etc.)

[CATEGORY_BG]
  ↳ "isolated on plain pure-black background, no environment"
     (variiert pro Kategorie — transparent/atmospheric/vignette/seamless)

[LORE_PROMPT]
  ↳ Charakter-/Mob-/Item-/Tile-spezifische Beschreibung aus VELGRAD_*_BIBEL

[CATEGORY_NEGATIVE]
  ↳ Master-Negative + category-spezifische Negatives (z.B. tile braucht extra
     "no character, no person, no architecture")
```

`sf/render_spec.py` liefert alle 4 Category-Bausteine pro Kategorie. Generators rufen `render_spec.format_prompt(category, lore_prompt)` und bekommen den komplett-zusammengesetzten Prompt zurueck.

---

## VI. ASSET-AUDIT-TOOL

`tools/asset_audit.py` prueft jedes Asset gegen die Spec:

```
python tools/asset_audit.py
python tools/asset_audit.py --category class
python tools/asset_audit.py --category mob --strict
```

**Checks pro Asset:**
1. **Resolution-Match** — passt zur Spec (e.g. class = 512×768, mob = 512×512)
2. **Aspect-Ratio** — innerhalb tolerance (e.g. class 2:3 ± 5%)
3. **BG-Transparency** — Kategorie `transparent` → mind. 30% alpha=0 erwartet
4. **Filename-Convention** — folgt der Spec (e.g. `<class>_anims/<anim>/<dir>.png`)
5. **Filesize** — sanity-check (PNG sollte nicht >5MB sein, sonst unkomprimiert?)

Output-Format:
```
[OK]   classes/warrior.png               512×768  alpha-0=64%  ✓
[WARN] classes/witch.png                 512×768  alpha-0=0%   BG-Removal noetig
[FAIL] mobs/aschenbrut.png               748×768  Aspect 0.97  expected 1.0 ±0.05
```

---

## VII. UPGRADE-PATH FUER ALTE ASSETS

Wenn ein Asset NICHT zur Spec passt, ist der Fix:
1. **WARN-Level** (z.B. BG nicht transparent): `tools/sprite_postprocess.py --file <p> --bg <black|white>`
2. **FAIL-Level** (z.B. falsches Aspect-Ratio): Re-Generate mit korrekter Resolution
3. **Composit-Issue** (z.B. Walk-Strip mit unterschiedlichen Frame-Widths): Re-Strip + Re-Slice via workflow_animation_frames.py

---

## VIII. EROEFFNUNG-CHECKLISTE FUER NEUE ASSET-PIPELINE

Wenn ein NEUER Asset-Typ hinzukommt (z.B. "decor" in Phase 2):

1. [ ] Section in dieser Doc adden (Kapitel III.X)
2. [ ] Eintrag in `sf/render_spec.py RENDER_SPEC` mit camera/distance/bg/resolution
3. [ ] CATEGORY-Konstante in `tools/scenario_config.py SPRITE_CATEGORIES`
4. [ ] Filename-Convention dokumentieren
5. [ ] Engine-Loader in `sf/sprites.py` (falls neu)
6. [ ] target_h-Multiplikator definieren
7. [ ] Audit-Check in `tools/asset_audit.py`

---

## IX. ZUSAMMENSPIEL MIT BESTEHENDEN BIBELS

```
VELGRAD_RENDER_SPEC.md     (DIESES DOC)
├─ WIE — Kamera, Distanz, Resolution, BG  ✅
│
├─ WAS — Lore-Beschreibung
│   └─ _legacy/VELGRAD_SPRITE_BIBEL.md (Targets + Prompts)
│   └─ ../gameplay/VELGRAD_BESTIARIUM.md (Mob-Lore)
│   └─ ../gameplay/VELGRAD_ITEMS_UNIQUE_BIBEL.md (Item-Lore)
│
└─ WIE-ORCHESTRIERT — Multi-Inference-Workflows
    └─ _legacy/VELGRAD_WORKFLOWS_BIBEL.md (Workflow-Tools)
```

Drei orthogonale Anliegen, klare Trennung. Jede Bibel ist source-of-truth fuer ihre Achse.

---

**Stand:** 2026-05-24 (Update #167). Wartung: jede Aenderung an einer Render-Konvention MUSS hier UND in `sf/render_spec.py` reflektiert sein. Die beiden Files muessen synchron bleiben.
