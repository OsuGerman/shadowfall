# VELGRAD — SPRITE-BIBEL (Lore-Referenz)

> ⚠️ **STATUS (Update #171, 2026-05-24):** Diese Bibel war urspruenglich ein Production-Spec fuer die KI-Sprite-Generation-Pipeline (Scenario.gg + tools/sprite_gen.py). Mit dem **Procedural-Only-Pivot** (User-Entscheidung 2026-05-24) wurde diese Pipeline aufgegeben — alle KI-PNGs sind aus dem Repo entfernt, das Spiel rendert ausschliesslich procedural via [sf/sprites.py](sf/sprites.py).
>
> **Dieses Dokument bleibt als visuelle Lore-Referenz** fuer die procedural-Renderer: Wenn ein Sprite-Element neu im Code beschrieben werden muss (z.B. "wie sieht ein Salzhueter-Brut aus?"), zieht der Code die Vibes/Farben/Silhouette-Beschreibungen aus dieser Bibel. Die KI-Prompts werden NICHT mehr ausgefuehrt — sie dienen nur noch als Beschreibung.
>
> **Tool:** [Scenario.gg](https://scenario.com) — *historisch* (Creator-Plan-Generation-Pipeline ist Legacy in [tools/sprite_gen.py](tools/sprite_gen.py))
> **Style:** Path of Exile 2 — dark fantasy painterly, gothic medieval, volumetric lighting, gedeckte Palette
> **Total Targets:** 41 (historisch) — alle entfernt mit Update #171

---

## ⚙️ PROCEDURAL-PIVOT-NOTIZ (Update #171)

Sprites werden nicht mehr generiert. Stattdessen:
- **Klassen / Mobs / Bosse** → [sf/sprites.py](sf/sprites.py) `draw_player_at` / `draw_enemy_at` rendert procedural-Composit (Kreise, Rects, Polygone, Animation via SpriteRig + SpriteAnimator-Hooks).
- **Decor** → [sf/world.py](sf/world.py) `draw_decor` rendert per `kind`-Dispatch.
- **Items** → [sf/sprites.py](sf/sprites.py) `draw_item_icon` rendert Rarity-Border + Schematic-Glyph.
- **Tiles** → [sf/world.py](sf/world.py) `_make_tile` rendert biome-spezifische Procedural-Pattern.
- **Status-Icons** → [sf/sprites.py](sf/sprites.py) `_status_overlay` rendert farbige Kreise mit Stack-Counter.
- **Portraits (Dialog)** → [sf/dialog.py](sf/dialog.py) `_make_placeholder_portrait` rendert Pergament-Box mit Initial.

Wer wieder KI-Assets aktivieren will:
1. `set_ai_sprites_enabled(True)` in [sf/sprites.py](sf/sprites.py) (oder Settings-Toggle `ai_sprites`)
2. PNGs nach `assets/sprites/<category>/` legen
3. [sf/sprite_registry.py](sf/sprite_registry.py) `SPRITES`-Dict fuellen
4. `reload_sprite_cache()` aufrufen

---

## I. MASTER-STYLE-CONFIG (POE2-Stil)

Diese Tags werden vor JEDEN Target-Prompt gehaengt:

### Positive-Prompt-Prefix
```
path of exile 2 style, dark fantasy painterly artwork, gothic medieval,
volumetric lighting, dramatic chiaroscuro, hyperdetailed concept art,
muted desaturated palette with selective color accents, weathered textures,
realistic-stylized proportions, ArtStation trending, Greg Rutkowski composition,
moody atmosphere, grimdark fantasy, intricate armor details, leather and iron,
8k quality, sharp focus
```

### Negative-Prompt (was wir NICHT wollen)
```
cartoon, anime, chibi, cel-shaded, low-poly, pixel art, MS Paint,
bright cheerful colors, saturated colors, modern clothing, sci-fi, neon,
deformed anatomy, extra limbs, mutated, blurry, jpeg artifacts, watermark,
text, signature, logo, ugly, low quality, amateur, child-like style
```

### Stil-Anchors pro Kategorie

| Kategorie | View-Angle | Background | Resolution | Steps |
|---|---|---|---|---|
| `mob` | 3/4 top-down, full-body | transparent (alpha) | 512×512 | 30 |
| `class` | front-view full-body, hero pose | transparent | 512×768 | 30 |
| `portrait` | head-and-shoulders, slight angle | dark vignette gradient | 256×256 | 25 |
| `boss_plate` | dramatic 3/4 view, full-body | atmospheric backdrop | 512×512 | 30 |
| `item_icon` | 3/4 isometric, single weapon/item | dark gradient | 128×128 | 20 |
| `tile` | top-down orthographic, seamless | tileable edges | 512×512 | 25 |

### Per-Category-Prompt-Suffixes (Auto-Append in sprite_gen.py)

Diese werden pro Kategorie automatisch ans Ende des Lore-Prompts gehängt — damit Mob/Class/Portrait isoliert auf transparentem BG erscheinen während Boss-Plates + Tiles ihre Atmosphäre behalten:

```
mob:         ", isolated full-body character on plain pure-black background,
              no environment, no scenery behind, top-down 3/4 angled hero shot,
              sprite-ready composition, centered subject"
class:       ", isolated full-body hero on plain pure-black background, no
              environment behind, frontal hero pose, sprite-ready composition,
              full body visible head to toe, centered"
portrait:    ", head and shoulders portrait with simple dark vignette gradient
              behind subject, no detailed environment, focus on face and upper
              torso, centered composition"
boss_plate:  ""   # leer — Backdrop ist erwuenscht
item_icon:   ", single isolated weapon on pure-black background, no environment"
tile:        ", seamless tileable texture, edges loop perfectly, no central
              focal point, uniform distribution"
decor:       ", single isolated prop object on plain pure-black background,
              no environment, no scenery behind, top-down 3/4 angled view,
              sprite-ready composition, centered subject, full silhouette visible,
              ground-anchored bottom edge"
status_icon: ", small isolated game-ui icon on plain pure-black background,
              no environment, single symbolic object, painterly icon style,
              clear silhouette, centered, minimal background, ARPG status-effect
              icon for inventory-style display"
```

---

## II. MOB-SPRITES (Phase 1 — 6 Lore-Mobs)

> Pro Mob: top-down 3/4 view, idle pose, transparent BG. Wird in Engine als Sprite-Sheet weiter zerlegt fuer Idle/Walk/Attack/Hurt/Death.

### M1. Salzhueter-Brut *(Akt-1-Boss)*
**Lore (VELGRAD_BESTIARIUM #5):** Eine ertrunkene Statue, einst Aspekt-Statue von Nheyra, jetzt korrumpiert. Wacht an der Salzwunde. Steinerne Gestalt, Salzkristalle wachsen aus den Augenhoehlen, Wasser tropft konstant.
```
[MASTER-PREFIX], ancient drowned statue of a goddess, weathered stone body
covered in salt crystals growing from cracks, glowing pale-blue eye sockets,
seaweed and barnacles on shoulders, slow trickle of saltwater, broken trident
in stone hand, hollow eye sockets, oppressive silence, dark turquoise and
bone-white palette, drowned-temple background atmosphere
```

### M2. Glaslord (Senator-Geist, Akt 2)
**Lore (#6 Echo-Senator + #22):** Politischer Geist aus dem Glasgoldenen Imperium. Glas-Gold-Texturen, durchsichtiger Koerper, goldene Roben die zerfallen, Senatoren-Stab.
```
[MASTER-PREFIX], translucent ghost of an ancient roman-style senator,
shattered glass body with gold veins, decaying golden ceremonial robes,
elaborate senatorial scepter, hollow piercing gaze, gold dust particles
trailing from form, baroque gothic style, amber and pale-gold palette,
ruined glass palace backdrop
```

### M3. Vehren-Echo (Akt 3 Mini-Variante)
**Lore (#13/#15):** Inquisitor-General-Echo. Tribunal-Inquisition-Stil — schwere Plattenruestung mit Brand-Symbolen, blinde Augen, Asch-Schweif von der Ruestung.
```
[MASTER-PREFIX], echoing apparition of a fanatical inquisitor general,
heavy gothic plate armor with branded heretic-marks, hooded visage with
empty eye sockets streaming ash, large two-handed warhammer with valsa-fire
embers, ash-grey and crimson palette, cathedral-ruin backdrop, oppressive
holy fury, blood-red cape billowing
```

### M4. Ertrunkene Koenigin (Akt 6a Boss-Mini)
**Lore (#26):** Letzte Koenigin Velharns, im Krieg ertraenkt, wachte am Boden der Salzwunde wieder auf. Verfallene Roben, Krone aus Korallen, Wasserstroeme aus dem Mund.
```
[MASTER-PREFIX], drowned queen rising from saltwater, tattered royal gown
with coral crown, kelp-tangled long hair, pale waterlogged skin with
glowing blue veins, water streaming from open mouth, broken sword in
trembling hand, deep-sea blue and bone palette, underwater sanctuary
backdrop, sorrowful regal presence
```

### M5. Aschenbrut (Akt 3 Generic-Mob)
**Lore (#11 Asch-Soldat):** Skelett aus der Letzten Legion, in Asche gehuellt, glimmt von Valsas Schmerz.
```
[MASTER-PREFIX], skeletal soldier from the last legion, charred bone armor
glowing with ember veins, ash particles rising from skull, rusted iron
sword, frozen mid-march pose, charcoal-black and amber-orange palette,
burning battlefield backdrop, eternal duty unfulfilled
```

### M6. Wurzelhueter (Akt 4 Generic-Mob)
**Lore (#20 Mark-Krieger):** Wurzel-Waechter aus dem Wurzelgrab. Holzig-organisch, Wurzeln statt Glieder, lebendige Rinde.
```
[MASTER-PREFIX], root-warden creature from the underworld grove,
living-wood torso bristling with thorned roots, bark armor wet with
sap, root-claws dripping resin, faceless head of woven branches with
glowing green eye-sockets, deep forest-green and brown palette,
ancient cavern-grove backdrop, organic primal power
```

---

## III. KLASSEN-SPRITES (Phase 1: 3, Phase 2: 5)

> Full-body hero pose, front-3/4 view. Transparente BG. Klassen-Identitaet aus Lore-Bibel Teil 7.

### C1. Warrior — Eisenwaechter (Kharn-Lineage)
```
[MASTER-PREFIX], iron-clad warrior of the Eisenwaechter order, heavy
gothic plate armor with kharn-tower-sigil etching, long two-handed mace
across back, scarred visage under helm-shadow, weathered red cloak,
stoic stance, iron-grey and bronze palette, sentinel-tower backdrop,
disciplined determination
```

### C2. Witch — Knochenwitwe (Shulavh-Lineage)
```
[MASTER-PREFIX], bone-witch in dark cowled robes adorned with vertebrae
and tied finger-bones, gnarled wooden staff topped with raven skull,
gaunt visage with ash-painted markings, pale hands trailing dark spirit
mist, deep violet and bone-white palette, root-grave backdrop, mournful
power, whispers to her dead
```

### C3. Sorceress — Funkengeborene (Valsa-Beruehrt)
```
[MASTER-PREFIX], spark-born sorceress with embers floating around her,
asymmetric dark mage robes with valsa-fire embroidery, white-hot eyes,
hair lifting in heat-thermals, palms cradling glowing ember-shard,
charcoal-black robes with crimson-orange accents, ash-field backdrop,
contained madness, dangerous beauty
```

### C4. Monk — Stiller Schritt
```
[MASTER-PREFIX], silent-step monk in plain ash-grey robes with rope
belt, shaven head with focus-markings, long quarterstaff held vertical,
bare feet in defensive stance, eyes closed in meditation, muted
slate-grey palette, pagoda backdrop, controlled stillness
```

### C5. Ranger — Saattraegerin
```
[MASTER-PREFIX], seed-bearer ranger in leather-and-bark hunting gear,
elegant longbow strapped to back, quiver of bone-arrows, hooded
silhouette with green-eye glow, vine-wrapped boots, deep forest-green
and warm-brown palette, ancient grove backdrop, watchful protector
```

### C6. Mercenary — Mahnmal-Soeldner
```
[MASTER-PREFIX], hardened mercenary of the mahnmal-guild, repeater
crossbow over shoulder, leather buff-coat with gilt mahnmal-tags
clinking, weather-beaten tricorn hat, cold pragmatic gaze, dark-brown
and tarnished-gold palette, harbor-pier backdrop, businesslike menace
```

### C7. Huntress — Speerschwester
```
[MASTER-PREFIX], spear-sister huntress in light-armor and warpaint,
long throwing spear in one hand, moon-binding cord wrapped around
forearm, braided dark hair with feather adornments, alert pose,
sand-tan and silver palette, desert-caravan backdrop, focused predator
```

### C8. Druid — Wandelnde
```
[MASTER-PREFIX], shape-shifting druid with antlered bone-crown,
fur-lined cloak of bear-pelt, claw-shaped staff of petrified wood,
animal-glyph tattoos pulsing faint-green on bare arms, three-animal
spirit aura (bear-wolf-wyvern) faint behind, earthy ochre and
forest-green palette, sacred grove backdrop, wild power barely contained
```

---

## IV. NPC-PORTRAITS (8, Phase 1)

> Head-and-shoulders, slight angle. Dark vignette background.

### P1. Korven Vor — Soeldnermeister
```
[MASTER-PREFIX], portrait of a scarred mercenary master in his fifties,
weathered face with prominent jaw scar, salt-and-pepper beard, hard
green eyes, dark-brown leather coat with brass mahnmal-tag chain,
neutral pragmatic expression, harbor-tavern candlelight, brown and
amber palette
```

### P2. Bruder Helst der Hundertjaehrige
```
[MASTER-PREFIX], portrait of a wizened blind priest of the Erblinde
Kirche, deep eye-sockets stitched shut with golden thread, long white
beard, dark hooded robe with iron-aspekt sigil, ancient lined skin
with quiet wisdom, pale moonlight rim-light, ivory and deep-grey palette
```

### P3. Vossharil die Dreimalige
```
[MASTER-PREFIX], portrait of a thrice-dead bone-witch elder, three
faded death-scars across throat, wild grey-white hair adorned with
bone-charms, ancient leathered skin with chaos-tattoos, soft pity-smile
in pale grey eyes, dark hooded shawl, dim violet-and-bone palette,
flickering candle-shadow
```

### P4. Tameris die Lichtsucherin
```
[MASTER-PREFIX], portrait of a young spear-sister huntress, alert
dark-blue eyes with grief-shadow, dark braided hair with single
feather, light leather armor over linen tunic, moonlight rim-lighting,
deep blue and silver palette, sister-bond pendant at neck
```

### P5. Otreth Hohlauge — Gemcutter
```
[MASTER-PREFIX], portrait of an obsessive gemcutter, left eye empty
socket covered with leather eyepatch, magnification monocle on right
eye, intense focused expression, dark leather apron with memory-stone
fragments embedded, lamplit workshop background, warm-amber and brown
palette, manic precision
```

### P6. Mara die Mahnerin
```
[MASTER-PREFIX], portrait of a mysterious echo-anomaly woman, pale
ethereal beauty with eyes that look slightly elsewhere, long silver-
white hair with woven mahnmal-threads, simple grey robes, slight
double-image translucency at edges, moonlit and dreamlike, pearl and
shadow palette, otherworldly calm
```

### P7. Inquisitor-General Vehren
```
[MASTER-PREFIX], portrait of a fanatical tribunal-inquisitor in his
forties, severe handsome face with ash-cross brand on forehead, cold
piercing blue eyes, shaved head, heavy ceremonial plate-collar with
valsa-fire sigils, blood-red cape, oppressive righteous fury,
charcoal-black and crimson palette
```

### P8. Die Drei Muetter (Trias, in einem Portrait)
```
[MASTER-PREFIX], triple portrait of the Three Mothers ascendancy-trial
givers, three crone-faces overlapping (gentle/stern/cackling), wild
white hair intertwined, ancient draped robes, sacred-grove backdrop
with hanging dream-catchers, dim ethereal violet and ash palette,
saatkind-mystery vibe
```

---

## V. BOSS-CONCEPT-PLATES (8, Phase 2)

> Dramatic full-body 3/4 view mit atmosphaerischem Backdrop. Wird in Boss-Intro-Cinematic (X-06) gezeigt.

### B1. Salzhueter-Brut — full plate
```
[MASTER-PREFIX], cinematic boss plate of the salt-warden statue,
massive drowned-stone goddess looming in flooded sanctuary, salt-
crystals erupting from cracked stone body, glowing pale-blue eyes
piercing the gloom, ankle-deep saltwater reflections, broken trident
raised, atmospheric god-rays through cathedral-ruins, deep turquoise
and bone palette, awe and dread
```

### B2. Vehren — full plate
```
[MASTER-PREFIX], cinematic boss plate of inquisitor-general vehren,
towering figure in heavy gothic platemail surrounded by ash-storm,
massive valsa-fire warhammer raised overhead, blood-red cape billowing,
piles of heretic-branded skulls underfoot, burning cathedral backdrop,
volumetric god-rays of ash and ember, charcoal-black and crimson palette,
righteous wrath
```

### B3. Senator-Geist — full plate
```
[MASTER-PREFIX], cinematic boss plate of the senator-spirit, translucent
gold-veined ghost in baroque senatorial robes, holding ceremonial scepter
raised, eternal political debate frozen in time, ruined glass-gold
palace with floating debate-scrolls, gold-dust storm swirling,
amber-gold and pale palette, melancholy power
```

### B4. Shulavh — full plate (Phase 1 Muetterlich)
```
[MASTER-PREFIX], cinematic boss plate of shulavh the thread-mother
aspect goddess phase 1, towering motherly figure of woven root-flesh
in vast underground grove, dozens of red threads extending from her
fingertips to unseen targets, sad gentle smile, weeping sap-tears,
warm umber and deep-green palette, melancholy ancient love
```

### B5. Velharn-Trio — full plate (3 Zeitschichten in einem Bild)
```
[MASTER-PREFIX], cinematic boss plate of the three-times boss, three
overlapping figures composited in one frame: gold-age senator on left,
war-age burning general center, present-age hollow king right, each
in their own time-layer with mirror-shard divides, baroque cathedral
backdrop spanning three eras, amber-fire-shadow palette, time-tear
horror
```

### B6. Ertrunkene Koenigin — full plate
```
[MASTER-PREFIX], cinematic boss plate of the drowned queen rising
from salt-wound depths, regal tattered gown billowing in water, coral
crown crowned with kelp, sorrowful pale visage with blue glowing veins,
broken sword pointed at viewer, sunken throne-room with light filtering
from above, deep-sea blue and bone palette, sad regal power
```

### B7. Echo-Drache — full plate
```
[MASTER-PREFIX], cinematic boss plate of the last echo-dragon, massive
ash-stone dragon coiled in ash-wound caldera, half-petrified by sorrow
half-aflame with valsa-fire, glowing molten eyes, broken wings of
charcoal-feathers, ash-storm swirling around, charcoal-black and
ember-orange palette, ancient grief made flame
```

### B8. Nicht-Gott — full plate
```
[MASTER-PREFIX], cinematic boss plate of the not-god anomaly, abstract
wrongness-figure that the eye cannot quite resolve, shifting silhouette
between humanoid and impossible-geometry, hollow-wound rift backdrop
with audible silence, near-monochrome palette of void-violet and pale
nothing, cosmic horror dread
```

---

## VI. ITEM-ICONS (50, aus VELGRAD_ITEMS_UNIQUE_BIBEL, Phase 3)

> Wird automatisch aus VELGRAD_ITEMS_UNIQUE_BIBEL.md geparst. Generation auf Phase 3 verschoben — Phase 1+2 priorisieren Mobs/Klassen/Tilesets.

Prompt-Template:
```
[MASTER-PREFIX], single isolated weapon icon view, [WEAPON_NAME] from
velgrad lore, [LORE_DESCRIPTION], 3/4 angle, top-down hero-shot, dark
gradient background, intricate runic engravings glowing faintly,
weathered surface details, painterly icon style for ARPG inventory,
mahnmal-aspekt sigils
```

Beispiel:
- **„Kharns Geduld"** (Two-Hand Mace [E]) → `[…] massive two-handed iron warhammer with kharn-tower-sigil etched into the head, weathered with countless battle-dents, glowing faint amber along the haft-runes, gothic medieval design`
- **„Tintendolch von Im-Nesh"** (Dagger [X Mythic, Quest-Item]) → `[…] sinister ink-black dagger that seems to absorb light, hilt wrapped in living calligraphy that writhes, edge dripping shadow-ink, im-nesh's hundred-tongued glyphs swirling around blade`

---

## VII. TILESETS (11 Biomes × 4 Floor-Variants + 11 Walls, Phase 2)

> Top-down orthographic, seamless. **4 Variant-Prompts pro Biome** für deterministisches Mixing nach Cell-Hash (eliminiert Pattern-Repeat). Plus **1 Wall-Tile pro Biome** für sichtbare Wand-Cells.
> Format: `T<biome>_<variant>` (z.B. T1a/T1b/T1c/T1d für Crypt-Variants, T1w für Crypt-Wall).

### T1a. Crypt Floor — salt-bricks
```
[MASTER-PREFIX], top-down tileable hand-painted floor texture only,
ancient salt-encrusted square stone bricks in regular grid pattern,
dried seaweed strands, scattered salt-crystal clusters, water-stained
mortar between bricks, deep-turquoise and bone palette, painterly POE2
```

### T1b. Crypt Floor — wet-flagstone
```
[MASTER-PREFIX], top-down tileable hand-painted floor texture only,
wet flagstone slabs with rectangular cuts, shallow saltwater pools in
crevices, barnacle clusters, pale bone-white salt deposits, deep blue
shadows, painterly POE2
```

### T1c. Crypt Floor — mossy-cracked
```
[MASTER-PREFIX], top-down tileable hand-painted floor texture only,
cracked stone slabs heavily overgrown with deep-blue underwater moss,
hairline mortar cracks, scattered small pebbles, occasional bone
fragments, painterly POE2
```

### T1d. Crypt Floor — bone-dust
```
[MASTER-PREFIX], top-down tileable hand-painted floor texture only,
dusty stone tiles with scattered bone fragments and salt-dust drifts,
weathered ancient masonry, dry pale tone, painterly POE2
```

### T1w. Crypt Wall
```
[MASTER-PREFIX], top-down hand-painted wall texture only, dark stone
masonry wall blocks viewed from directly above, salt-encrusted edges,
chiseled stone surface with deep mortar lines, dark blue-grey palette,
painterly POE2 dungeon wall, seamless edges
```

### T2. Frost / Glass-Ruins (Akt 2)
```
[MASTER-PREFIX], top-down tileable tile of glasgolden imperium ruins,
cracked white-gold marble with gold-vein inlays, scattered glass
shards in crevices, gold-dust drifts, faded baroque mosaic remnants,
seamless tile, painterly POE2 style, amber and ivory palette
```

### T3. Lava (Akt 3 — Aschenfelder)
```
[MASTER-PREFIX], top-down tileable tile of burnt-ash battlefield,
charred black soil with ember-glowing cracks, scattered scorched bones
and rusted iron fragments, ash drift patterns, occasional valsa-fire
embers, seamless tile, painterly POE2 style, charcoal and crimson-ember
palette
```

### T4. Swamp (Akt 4 — Wurzelgrab)
```
[MASTER-PREFIX], top-down tileable tile of underground rootgrove floor,
wet living-wood planks woven with thorny roots, glowing-spore patches,
dark-green moss, occasional bone-charm hangings, seamless tile, painterly
POE2 style, deep-green and damp-brown palette
```

### T5. Astral (Akt 5 — Velharn)
```
[MASTER-PREFIX], top-down tileable tile of mirror-city floor, broken
mirror-shards embedded in pale-violet marble, time-distorted patterns
that look like they're slightly moving, faint constellation-glyphs,
seamless tile, painterly POE2 style, pale-violet and starlight palette
```

### T6. Desert (Akt 1b — Zhar-Eth)
```
[MASTER-PREFIX], top-down tileable tile of caravan-desert ground,
wind-rippled fine sand with scattered moon-glyph fragments, half-buried
broken pottery shards, occasional speerschwestern feather-charm,
seamless tile, painterly POE2 style, sand-tan and silver palette
```

### T7. Town (Brassweir)
```
[MASTER-PREFIX], top-down tileable tile of harbor town cobblestone,
worn sea-salt-stained cobbles, occasional rope-fragments and barnacle-
clusters, puddle reflections, mahnmal-tag chain links scattered,
seamless tile, painterly POE2 style, weathered brown and slate palette
```

### T8. Wound_Salt (Akt 6a)
```
[MASTER-PREFIX], top-down tileable tile of the salt-wound,
pulsating salt-crystal floor with deep-blue glow seeping through
cracks, drowned-bones half-buried, salt rivulets streaming, seamless
tile, painterly POE2 style, deep-blue and bone palette, ominous pulse
```

### T9. Wound_Ash (Akt 6b)
```
[MASTER-PREFIX], top-down tileable tile of the ash-wound,
black volcanic glass cracked with valsa-fire veins, ember-glowing
scars in geometric patterns, charred bone fragments fused to ground,
seamless tile, painterly POE2 style, obsidian and ember palette
```

### T10. Wound_Hollow (Akt 6c)
```
[MASTER-PREFIX], top-down tileable tile of the hollow-wound,
near-absence-of-texture floor, faint negative-space patterns where
detail should be, occasional impossible-geometry rifts, seamless
tile, painterly POE2 style, void-violet and pale-nothing palette,
wrongness
```

### T11. Hollow_Word (Akt 7)
```
[MASTER-PREFIX], top-down tileable tile of im-nesh's hollow-word
realm, alien calligraphy carved into pale-stone tiles, the glyphs
shifting subtly, hundred-tongues sigils echoing, seamless tile,
painterly POE2 style, ivory and shadow palette, blasphemous language
```

---

## VIII. GENERATION-PIPELINE

### Phase 1 — Start mit Test (1 Sprite, ~0,02 % vom Budget)
1. Generiere **nur Salzhueter-Brut** (M1) als Single-Test
2. User beurteilt: POE2-Stil getroffen? Welche Anpassungen?
3. Master-Prompt-Anpassung wenn noetig

### Phase 2 — Mob+Class+Portrait (17 Sprites × 4 Gens = 68 Calls)
4. 6 Mob-Sprites
5. 3 Klassen-Sprites (Warrior/Witch/Sorceress)
6. 8 NPC-Portraits

### Phase 3 — Boss-Plates + Tilesets (19 Sprites × 4 Gens = 76 Calls)
7. 8 Boss-Concept-Plates
8. 11 Tilesets

### Phase 4 — Item-Icons (~50 × 2 Gens = 100 Calls)
9. Aus VELGRAD_ITEMS_UNIQUE_BIBEL parsen + generieren

**Total: ~244 API-Calls** (4,9 % vom 5000-Bilder-Creator-Plan)

---

## IX. ENGINE-INTEGRATION

Nach Generation:
1. Best-of-4 manuell auswaehlen pro Target (oder Scenario-Voting via API)
2. PNG-Alpha-Check (transparenter BG bei Mob/Class/Portrait)
3. Speicher-Pfad: `assets/sprites/<category>/<target_id>.png`
4. `sf/sprite_registry.py` auto-generieren mit `sprite_path(target_id) → abs_path`
5. `sf/sprites.py` `SpriteAtlas`-Loader nutzt Registry (ROADMAP T2.2-A bis T2.2-D)
6. Procedural-Fallback bleibt aktiv (T-04) — wenn Sprite fehlt, render Composit

---

## XI. DECOR-SPRITES (17, Phase 3 — Prio-Pass HOCH)

> Top-down 3/4 Einzel-Props, transparente BG. Lore-konform zu BIOMES-decor_kinds in [sf/world.py](sf/world.py) + neue Lore-Anker (Brassweir-Hafen, Erblinde-Kirche-Mahnmal, Eisenwächter-Schmiede, Wurzelgrab-Webrahmen). Geladen via `sf.sprites.get_decor_sprite(kind)`.

### D1. Mahnmal-Stele *(Erblinde Kirche, Akt 1)*
**Lore (VELGRAD_LORE_BIBEL Aspekt-Pakt):** Stehender Grab-Stein der Erblinden Kirche. Eingelassen mit den 7 Aspekt-Glyphen plus die leere achte Stelle. Wird in Brassweir + Karawanen-Routen aufgestellt.
```
[MASTER-PREFIX], single isolated prop, weathered standing memorial stele
roughly waist-high, carved from dark salt-grey stone, seven aspect-sigils
chiseled vertically with the eighth slot deliberately empty, faint bronze
inlay traces in the engravings, hairline cracks, slight forward lean as if
weighed down by memory, dark slate and tarnished bronze palette
```

### D2. Pier-Post *(Brassweir-Hafen, Akt 1)*
**Lore (WELT_AUFBAU Brassweir):** Salzverkrustete Holz-Pfosten am Hafen, mit Tau und Mahnmal-Tag-Kette behangen. Markiert Liegeplätze der Schiffe.
```
[MASTER-PREFIX], single isolated prop, weathered wooden pier post about
hip-high, sea-salt encrusted dark oak, frayed rope coil wrapped around top,
brass mahnmal-tag chain hanging from an iron nail, barnacle clusters near
base, drip stains, harbor-brown and tarnished-brass palette
```

### D3. Anvil *(T. Eldros' Eisenwächter-Schmiede, Akt 1)*
**Lore (Warrior-Origin / „Letzter Hammer von Velhost"):** T. Eldros' Schmiede-Amboss. Schwer, geschwärzt, ein Hammer-Abdruck eingebrannt. Quest-Anker.
```
[MASTER-PREFIX], single isolated prop, heavy blackened iron anvil on
weathered oak stump base, scorched horn end with countless hammer-dents,
faint ember-glow in deep tool-grooves, eisenwaechter-tower-sigil engraved
on the side, soot streaks, iron-grey and orange-ember palette
```

### D4. Brassweir-Barrel *(Hafen, Akt 1)*
**Lore:** Salz-Faß für Fisch und Schiffsproviant. Korven Vors Söldner-Lager voll davon.
```
[MASTER-PREFIX], single isolated prop, weathered oak salt-barrel with
rusted iron banding, dark wood with salt-bleached top staves, faint mahnmal-
brand on side, slight bulge midway, frayed rope handle, harbor-brown and
salt-grey palette
```

### D5. Mahnmal-Pyre *(Asch-Pyre, Akt 3 Aschenfelder)*
**Lore (Bestiarium #11 Asch-Soldat / Valsa):** Eisen-Korb auf Dreibein, in dem Valsas Asche brennt. Markiert Tribunal-Lager.
```
[MASTER-PREFIX], single isolated prop, wrought-iron tripod brazier waist-
high, ash-filled bowl with valsa-fire embers glowing crimson-orange,
charred soot stains running down legs, ash drift around base, scorched-
black iron and ember-glow palette
```

### D6. Shulavh-Loom *(Wurzelgrab-Webrahmen, Akt 4)*
**Lore (Bestiarium #20 Wurzelgrab / Shulavh-Faden-Item):** Vertikaler Webrahmen aus lebendem Wurzelholz. Rote Fäden hängen unfertig herab. Knotenwitwen-Werkstatt-Marker.
```
[MASTER-PREFIX], single isolated prop, vertical loom frame made from
living-wood roots, half-finished red thread tapestry hanging mid-weave,
gnarled bark posts, a few woven finger-bones as shuttle weights, dark
forest-green wood and blood-red thread palette
```

### D7. Echo-Glass-Shard *(Glasgolden-Imperium, Akt 2)*
**Lore (Bestiarium #6 Echo-Senator):** Großer Glasgold-Splitter — Überrest eines zerschlagenen Senats-Spiegels. Reflektiert kurze Echos.
```
[MASTER-PREFIX], single isolated prop, large fractured glass-gold shard
standing upright in cracked marble base, translucent body shot through
with gold veins, faint flickering reflection inside as if showing an
echo, sharp jagged edges, baroque-ornate base, amber-gold and ivory palette
```

### D8. Salt-Spire *(Salzwunde, Akt 6a)*
**Lore (WELT_AUFBAU Akt 6a):** Pulsierender Salzkristall-Stalagmit aus der Salzwunde. Leuchtet wenn der Spieler nah ist.
```
[MASTER-PREFIX], single isolated prop, vertical salt-crystal spire knee-
to-shoulder tall, pulsating deep-blue inner glow through translucent
crystal layers, brine droplets clinging, drowned-bone fragments fused
near base, deep-turquoise and bone-white palette, ominous pulse
```

### D9. Velharn-Mirror *(Spiegelstadt, Akt 5)*
**Lore (Bestiarium #22 / Akt 5 Velharn):** Aufgehängter Stadt-Spiegel der Drei-Zeitschichten. Zeigt manchmal andere Zeit-Echos.
```
[MASTER-PREFIX], single isolated prop, ornate baroque mirror about head-
high mounted on filigree gold stand, mirror surface shows faint time-
distortion ripple instead of clean reflection, three subtle figure
silhouettes ghosted within, pale-violet starlight rim, gilded frame with
mahnmal sigil, ivory and violet palette
```

### D10. Bonewitch-Skull-Altar *(Knochenwitwen-Werkstatt, Akt 4)*
**Lore (Lore-Bibel Vossharil / Witch-Origin):** Schädel-Stapel-Altar mit Knochen-Charms und Ritual-Kerzen. Knochenwitwen-Marker.
```
[MASTER-PREFIX], single isolated prop, stacked stone altar topped with
three human skulls in a triangle arrangement, bone-charm strings draped
between, two melting black ritual candles with dripping wax, scattered
dried herbs and finger-bones, dim violet aura, bone-white and shadow-
violet palette
```

### D11. Caravan-Wagon *(Zhar-Eth Speerschwestern, Akt 1b)*
**Lore (Bestiarium / Tameris-Origin):** Speerschwester-Karawanen-Wagen. Sandgewohnte Holz-Plane, Mond-Glyphe.
```
[MASTER-PREFIX], single isolated prop, small sand-worn covered caravan
wagon with weathered canvas top showing a faded crescent moon glyph,
two spoke-wheels embedded in fine sand drift, frayed feather-charm
hanging from front post, sand-tan and silver palette, desert prop
```

### D12. Mahnmal-Chain *(Erblinde Kirche, mehrere Akte)*
**Lore (Mercenary-Origin / Mahnmal-Gilde):** Kette aus gegossenen Bronze-Mahnmal-Tags. Hängt an Stadt-Toren und Wegkreuzungen.
```
[MASTER-PREFIX], single isolated prop, draped chain of cast-bronze mahnmal
tags hanging in a U-curve from two iron pegs, each tag stamped with a
different aspect-sigil, slight green oxidation, faint engraved names,
weathered bronze and verdigris palette
```

### D13. Seedbearer-Torch *(Saatträger-Hain, Akt 4)*
**Lore (Ranger-Origin / Saatträger):** Holz-Fackel mit Pflanzen-Knospen am Schaft. Brennt warm-grün statt orange.
```
[MASTER-PREFIX], single isolated prop, tall wooden torch with bark-
wrapped shaft and small spring buds growing from notches, flame burning
with warm-green seedbearer fire instead of orange, faint vine creeping
up shaft, deep forest-green and soft amber palette
```

### D14. Drowned-Idol *(Nheyra-Statue, Akt 6a / Akt 1)*
**Lore (Lore-Bibel Nheyra / Bestiarium #5 Salzhüter):** Halbversunkene Aspekt-Statue Nheyras. Korrumpiert, Salzkristalle wachsen aus den Augen.
```
[MASTER-PREFIX], single isolated prop, small toppled stone idol about
knee-high of nheyra the salt-mother, weathered face half-eroded, salt
crystals erupting from eye-sockets, ankle of statue cracked, kelp
fragments draped across shoulder, deep-blue and bone palette, drowned
sorrow
```

### D15. Inquisitor-Pyre-Stake *(Vehren-Lager, Akt 3)*
**Lore (Bestiarium Vehren / Lore-Bibel Tribunal):** Brand-Pfahl der Tribunal-Inquisition. Verkohlte Ketten, halb verbrannte Häretiker-Marke.
```
[MASTER-PREFIX], single isolated prop, charred wooden execution stake
about head-high planted in scorched earth ring, hanging burnt chains,
half-melted iron heretic-brand mark embedded in wood, ash drift around
base, charcoal-black and dried-blood palette, oppressive holy fury
```

### D16. Monk-Meditation-Bell *(Stille-Schritte-Tempel, Akt 4/5)*
**Lore (Monk-Origin / Bestiarium Stille-Schritte):** Bronze-Glocke auf Holz-Gestell. Wird nur einmal pro Atemzug angeschlagen.
```
[MASTER-PREFIX], single isolated prop, small hanging bronze meditation
bell about palm-sized suspended in a simple wooden frame waist-high,
weathered patina, single hanging striker rope, three faded pagoda
glyphs around rim, muted slate-grey wood and aged-bronze palette,
controlled stillness
```

### D17. Forgotten-Obelisk *(Hohlwunde, Akt 6c)*
**Lore (WELT_AUFBAU Akt 6c Hohlwunde / Im-Nesh):** Schwarzer Obelisk dessen Inschriften sich auflösen wenn man sie anschaut.
```
[MASTER-PREFIX], single isolated prop, tall narrow black obelisk shoulder-
high tapering to a point, surface partially covered in alien calligraphy
that appears to be dissolving into the stone, faint negative-space rifts
near the base where geometry feels wrong, near-monochrome void-violet and
pale-nothing palette, cosmic wrongness
```

---

## XII. ITEM-ICONS — 50 UNIQUES (Phase 3 — Prio-Pass HOCH)

> Vollständige 1:1-Abbildung der 50 Uniques aus [VELGRAD_ITEMS_UNIQUE_BIBEL.md](VELGRAD_ITEMS_UNIQUE_BIBEL.md). 128×128 Item-Icon, 3/4-Top-Down, pure-black BG, Master-Suffix `item_icon`. Lore-Anker pro Item ist die jeweilige Bibel-Beschreibung. Geladen via `sf.sprites.get_item_unique_icon(unique_slug)`.

### U1. Kharns-Geduld *(Two-Hand Mace [E])*
```
[MASTER-PREFIX], single isolated weapon icon, massive two-handed warhammer
of kharns-geduld, head carved from black stone inlaid with slowly pulsing
bronze veins, weathered ship-wood haft, leather grip wrap, faint amber
glow along bronze inlay, gothic medieval, weighty and patient design
```

### U2. Aschen-Ankunft *(Two-Hand Mace [M])*
```
[MASTER-PREFIX], single isolated weapon icon, two-handed slam-mace
aschen-ankunft, head of re-solidified molten stone with cracked orange
ember-glow inside, ash-soot streaking down haft, falling spark particles
near head, valsa-fire crimson and obsidian palette
```

### U3. Letzter-Hammer-von-Velhost *(One-Hand Mace [L])*
```
[MASTER-PREFIX], single isolated weapon icon, simple one-handed smith
hammer letzter-hammer-von-velhost, dented iron head with scratched name
"T. Eldros" gouged into the side, plain wooden grip, eisenwaechter-
tower-sigil faintly stamped on butt, humble craftsman tool design
```

### U4. Der-Schweigende *(One-Hand Mace [E])*
```
[MASTER-PREFIX], single isolated weapon icon, one-handed mace der-
schweigende, head of jet-black stone that visibly absorbs surrounding
light, no highlights or reflections, wrapped in dark cloth around grip,
muted-velvet shadow palette, silent menacing design
```

### U5. Wachturm-Faust *(Two-Hand Mace [M])*
```
[MASTER-PREFIX], single isolated weapon icon, two-handed eisenwaechter
mace wachturm-faust, head forged from fallen tower stones with faint
inscription "Wir halten" half-worn-off, iron banding, tower-sigil
emblem, stoic iron-grey and tarnished-bronze palette
```

### U6. Echo-Klinge *(One-Hand Sword [M])*
```
[MASTER-PREFIX], single isolated weapon icon, one-handed sword echo-
klinge with deliberately unsharp blurry blade appearing to exist in
multiple time-layers simultaneously, slight ghost-trail of two extra
blade silhouettes offset, simple cross-guard, velharn pale-violet
shimmer along edge
```

### U7. Verbrannte-Treue *(Two-Hand Sword [M])*
```
[MASTER-PREFIX], single isolated weapon icon, two-handed greatsword
verbrannte-treue, blackened scorched blade with deeply branded oath
script in old velgrad-runes glowing faint ember red, charred leather
grip wrap, fanatical inquisitor design, charcoal and dried-blood palette
```

### U8. Senatorin-Stahl *(One-Hand Sword [L])*
```
[MASTER-PREFIX], single isolated weapon icon, elegant one-handed senator
sword senatorin-stahl, slim filigree-etched blade with glasgolden glyphs
along fuller, gold-dust residue clinging to engravings, fine ornate hilt
with amber pommel, baroque imperial design, amber-gold and ivory palette
```

### U9. Der-Erste-Eid *(Two-Hand Sword [X — Mythic])*
```
[MASTER-PREFIX], single isolated weapon icon, two-handed mythic greatsword
der-erste-eid, the cutting edge itself is a single unbroken sacred oath
inscribed in glowing pale-gold runes that form the actual sharpened line,
solemn ceremonial hilt, faint divine aura, ancient world-binding design
```

### U10. Wurzelschlitzer *(One-Hand Axe [M])*
```
[MASTER-PREFIX], single isolated weapon icon, one-handed root-wood axe
wurzelschlitzer, curved blade of dark rootwood inset with bone-splinter
teeth along edge, visible sap trickling from a weeping notch, gnarled
branch grip, deep forest-green and bone palette
```

### U11. Saatkind-Beil *(Two-Hand Axe [E])*
```
[MASTER-PREFIX], single isolated weapon icon, two-handed saatkind-beil
axe, blade carved from a single petrified oak splinter, fur-wrapped
haft with bone-claw fetishes hanging, faint green sprout growing from
crack in head, earth-ochre and forest-green palette, primal ancient design
```

### U12. Brassweir-Schaedelbrecher *(One-Hand Axe [L])*
```
[MASTER-PREFIX], single isolated weapon icon, oversized harbor-worker
axe brassweir-schaedelbrecher with pier-wood haft, salt-encrusted blade
edge, barnacle clusters near socket, frayed rope wrap around grip,
weathered harbor-brown and salt-grey palette
```

### U13. Vossharils-Bruder *(Dagger [M])*
```
[MASTER-PREFIX], single isolated weapon icon, slim white-bone dagger
vossharils-bruder, polished bone blade tapering to needle point, tiny
moving black eye inlaid into tip glinting wetly, bone-bead pommel,
chaos-violet aura, mournful family-relic design
```

### U14. Hohle-Zunge *(Dagger [E])*
```
[MASTER-PREFIX], single isolated weapon icon, dagger hohle-zunge with
semi-transparent glass-like blade containing faint flickering shape
inside, dangerous edge despite glass appearance, dark wrapped grip with
silence-glyph pommel, pale-violet hollow palette
```

### U15. Tintendolch-von-Im-Nesh *(Dagger [X — Mythic])*
```
[MASTER-PREFIX], single isolated weapon icon, mythic ink-black dagger
tintendolch-von-im-nesh, blade dripping living calligraphy-ink that
hangs in mid-air leaving burning script traces, hilt wrapped in writhing
calligraphy threads, im-nesh hundred-tongue glyphs swirling around blade,
void-violet and ink-black palette
```

### U16. Der-Zweite-Atem *(Dagger [M])*
```
[MASTER-PREFIX], single isolated weapon icon, unassuming plain dagger
der-zweite-atem with subtle organic curve as if breathing, polished
steel blade with faint warm rim-light, leather grip, simple cross-guard
with quiet life-pulse aura, muted steel and warm-bronze palette
```

### U17. Tameris-Suchender *(Spear [M])*
```
[MASTER-PREFIX], single isolated weapon icon, long slim huntress spear
tameris-suchender, spear-shaft of polished ash-wood with small brass
bell hanging just below leaf-shaped spearpoint, silver thread wrap
around grip, feather charm at base, sand-tan and silver palette
```

### U18. Zhar-Eth-Mondbinder *(Spear [E])*
```
[MASTER-PREFIX], single isolated weapon icon, huntress spear zhar-eth-
mondbinder, crescent-moon shaped spearhead with razor-sharp inner curve,
shaft wrapped in silver moonlight-glowing threads, hanging crescent
moon-charm, pale silver and night-blue palette
```

### U19. Faden-Spitze *(Spear [E])*
```
[MASTER-PREFIX], single isolated weapon icon, spear faden-spitze with
spearpoint forged into ornate woven knot-shape, long unbroken red
shulavh-thread trailing from base of point, dark wood shaft, blood-red
thread and dark-wood palette, fate-binding design
```

### U20. Der-Sechzehnte *(Spear [M])*
```
[MASTER-PREFIX], single isolated weapon icon, standard huntress spear
der-sechzehnte with prominent "XVI" engraved on socket, leather cord
with tiny bone-charm pendant tied near grip, well-used patina, sand-tan
and silver palette, sisterhood-marker design
```

### U21. Sturmspeer-von-Veh *(Spear [M])*
```
[MASTER-PREFIX], single isolated weapon icon, lightning-spear sturmspeer-
von-veh, polished steel spearpoint with arcing blue-white electrical
glow crawling along shaft, ozone-particle mist around head, weathered
storm-grey shaft, electric-blue and steel palette
```

### U22. Drei-Pagoden *(Quarterstaff [E])*
```
[MASTER-PREFIX], single isolated weapon icon, monk quarterstaff drei-
pagoden composed of three bamboo segments joined with brass rings, each
segment carved with a different pagoda glyph faintly glowing, dark
lacquered bamboo and aged-brass palette, controlled balance design
```

### U23. Der-Atemzaehler *(Quarterstaff [M])*
```
[MASTER-PREFIX], single isolated weapon icon, plain monk quarterstaff
der-atemzaehler in dark bamboo covered in hundreds of tiny tally-mark
notches running its full length, slight wear pattern on grip section,
muted slate-bamboo and bone palette, ascetic discipline design
```

### U24. Schlafsplitter *(Quarterstaff [E])*
```
[MASTER-PREFIX], single isolated weapon icon, monk staff schlafsplitter
carved from petrified single-breath tree wood, pale fossilized wood
grain with faint kharn-bronze veins, simple grip wrap, sleepy slow-
pulse glow, bone-pale and bronze palette, drowsy peace design
```

### U25. Bambus-des-Schweigens *(Quarterstaff [M])*
```
[MASTER-PREFIX], single isolated weapon icon, unbroken single-segment
bamboo monk staff bambus-des-schweigens, hollow opening at the top
visible, polished dark green bamboo with no decoration whatsoever,
absolute simplicity, deep-bamboo-green and shadow palette, silence design
```

### U26. Letzter-Schritt *(Quarterstaff [X])*
```
[MASTER-PREFIX], single isolated weapon icon, mythic monk staff letzter-
schritt, lower half is solid dark wood with brass band, upper half
gradually dissolves into faint mist as if not entirely physical, pale
ethereal glow at tip, slate-grey and silver-mist palette
```

### U27. Saatwaechter *(Bow [M])*
```
[MASTER-PREFIX], single isolated weapon icon, ranger bow saatwaechter
made of living curved wood with small green buds growing from the limbs,
braided green-grass bowstring, leather grip wrap, faint life-pulse glow,
deep forest-green and warm-bark palette, living-bow design
```

### U28. Erinnerungs-Bogen-von-Saath *(Bow [E])*
```
[MASTER-PREFIX], single isolated weapon icon, recurve bow erinnerungs-
bogen-von-saath carved from ancient bear-skeleton bones, braided dark-
human-hair bowstring, bone-white limbs with faint silver carvings,
hunter-memory blue rim-light, bone-white and silver palette
```

### U29. Tannenbein *(Bow [L])*
```
[MASTER-PREFIX], single isolated weapon icon, simple longbow tannenbein
of dark pine-wood with small animal-crest emblem carved at lower tip,
hempen bowstring, leather grip wrap, well-loved patina, forest-brown
and weathered-green palette, generational hunter design
```

### U30. Der-Unbeschriebene *(Bow [X — Mythic])*
```
[MASTER-PREFIX], single isolated weapon icon, mythic invisible bow der-
unbeschriebene rendered as only the faintest outline of a bow shape
visible in negative-space, mostly empty air with edge-of-vision shimmer,
single barely-visible string, deep void-blue and pale-grey palette,
absence-as-weapon design
```

### U31. Mahnmal-Marke-VII *(Crossbow [M])*
```
[MASTER-PREFIX], single isolated weapon icon, industrial mercenary
crossbow mahnmal-marke-vii with brass fittings, "M-VII" engraved on
barrel, polished walnut stock, automatic spring-loader mechanism
visible, expensive precision design, brushed-brass and dark-walnut palette
```

### U32. Korvens-Wahrheit *(Crossbow [E])*
```
[MASTER-PREFIX], single isolated weapon icon, heavy sniper crossbow
korvens-wahrheit with elongated barrel and large glasgolden-lens scope
attached, weighty oak stock, bronze trigger guard, professional
craftsman-grade design, dark-walnut and amber-glass palette
```

### U33. Der-Letzte-Hauch *(Crossbow [E])*
```
[MASTER-PREFIX], single isolated weapon icon, small pistol-sized crossbow
der-letzte-hauch with tiny bore-hole in barrel softly whistling, compact
mercy-weapon design, hollow grey-iron and dark bone palette, swift-
finish executioner aesthetic
```

### U34. Verraten-Sieben *(Crossbow [E])*
```
[MASTER-PREFIX], single isolated weapon icon, fan-shaped crossbow verraten-
sieben with seven small barrels arrayed radially, each barrel marked with
a different aspect-glyph and the seventh struck through with a slash,
heavy brass mounting, betrayal-design aesthetic, brushed-brass and
charred palette
```

### U35. Eisenfaust-Repetier *(Crossbow [L])*
```
[MASTER-PREFIX], single isolated weapon icon, robust repeater crossbow
eisenfaust-repetier with wooden tube-magazine on top, iron-banded stock,
brass winding lever, sturdy mercenary design, dark-iron and oak palette,
reliable repeating workhorse
```

### U36. Funken-Fluch *(Wand [M])*
```
[MASTER-PREFIX], single isolated weapon icon, knotted wooden caster wand
funken-fluch with small glass orb at tip containing constantly crackling
fire-sparks visibly arcing inside, brass cap, weathered grip wrap,
funkengeborene-fire orange and brass palette
```

### U37. Asche-Aspekt *(Wand [E])*
```
[MASTER-PREFIX], single isolated weapon icon, charred-black wooden wand
asche-aspekt with single tiny never-extinguishing ember glowing at tip,
ash-soot streaks along shaft, simple iron-band grip, valsa-fire and
charcoal palette
```

### U38. Tintenfeder-von-Im-Nesh *(Wand [X])*
```
[MASTER-PREFIX], single isolated weapon icon, mythic black quill wand
tintenfeder-von-im-nesh with single raven feather shape, dripping ink
from tip, faint script floating in air around quill rewriting itself,
hand-line ink stains near grip, void-violet and ink-black palette
```

### U39. Bischof-Schwur *(Sceptre [M])*
```
[MASTER-PREFIX], single isolated weapon icon, golden ceremonial sceptre
bischof-schwur with large inlaid sapphire-eye that visibly opens and
closes, ornate cathedral-style golden rod, filigree engravings, erblinde-
kirche sigil at top, polished-gold and deep-sapphire palette
```

### U40. Spirit-Anker *(Sceptre [E])*
```
[MASTER-PREFIX], single isolated weapon icon, heavy stone sceptre spirit-
anker with bronze bands wrapping the shaft, weighty club-like profile
that doubles as weapon, eisenwaechter-tower-sigil at head, dark-stone
and tarnished-bronze palette, anchoring presence design
```

### U41. Hohlauges-Erbe *(Sceptre [E])*
```
[MASTER-PREFIX], single isolated weapon icon, filigree sceptre hohlauges-
erbe with empty eye-socket at top instead of gem, otreth-gemcutter's
finest work, ornate silver wirework around shaft, faint memory-stone
fragments embedded, silver and bone-white palette
```

### U42. Sieben-Atem-Stab *(Staff [X])*
```
[MASTER-PREFIX], single isolated weapon icon, massive mythic staff sieben-
atem-stab with seven aspect-glyphs inlaid vertically along shaft and a
seventh slot deliberately left empty as raw stone, brass bindings between
each glyph, faint multi-elemental aura, weathered ironwood and brass
palette
```

### U43. Glasgoldener-Zepter-Stab *(Staff [E])*
```
[MASTER-PREFIX], single isolated weapon icon, elegant casting staff
glasgoldener-zepter-stab of fused glass-and-gold with floating gold-dust
particles visible circling inside hollow glass shaft, ornate baroque
cap, amber-gold and ivory palette, imperial-magic design
```

### U44. Wurzelmark-Stuetze *(Staff [M])*
```
[MASTER-PREFIX], single isolated weapon icon, living root staff
wurzelmark-stuetze of intertwined dark roots with small green buds
sprouting at intervals, weeping sap droplets, leather grip wrap, druid-
healer aesthetic, deep forest-green and warm-bark palette
```

### U45. Vergessens-Brand *(Staff [E])*
```
[MASTER-PREFIX], single isolated weapon icon, void staff vergessens-
brand of black wood that visibly partially dissolves and re-forms in
sections, transparent gaps along shaft, dark capped tip, dim void-violet
and pale-grey palette, absence-burning design
```

### U46. Drei-Tier-Anhaenger *(Talisman [E])*
```
[MASTER-PREFIX], single isolated talisman icon, druid necklace drei-
tier-anhaenger with three small carved bone fetishes — bear / wolf /
wyvern — hanging from a leather cord, faint animal-spirit aura around
each charm, earth-ochre and bone palette
```

### U47. Baerenhirten-Kette *(Talisman [M])*
```
[MASTER-PREFIX], single isolated talisman icon, druid bear-claw necklace
baerenhirten-kette with five large curved bear-claws threaded on a thick
leather cord, faint warm fur-trim accent, weathered ochre-brown and
bone palette, primal protector design
```

### U48. Wolfsmond-Amulett *(Talisman [M])*
```
[MASTER-PREFIX], single isolated talisman icon, druid pendant wolfsmond-
amulett with silver crescent moon shape holding a tiny wolf-skull at its
focus, silver chain, faint moonlight glow, polished silver and bone palette
```

### U49. Kharns-Traene *(Amulet [X])*
```
[MASTER-PREFIX], single isolated amulet icon, mythic teardrop pendant
kharns-traene of warm-bronze single tear suspended inside an ornate
filigree silver cage, faint inner warmth-glow, delicate silver chain,
warm-bronze and silver-filigree palette, ancient never-fallen design
```

### U50. Der-Achte *(Mystery-Fragment [X])*
```
[MASTER-PREFIX], single isolated weapon fragment icon, mysterious shard
der-achte of unidentifiable material that the eye slides off of, neither
stone nor metal nor wood, faint whisper-aura around fragment, irregular
jagged shape, near-monochrome palette of void-violet and pale-nothing,
forgotten-eighth-aspect aesthetic
```

---

## XIII. STATUS-EFFECT-ICONS (15, Phase 3 — Prio-Pass HOCH)

> 64×64-Icons für HUD-Buff-Tray + Enemy-Status-Pips. Lore-konsistent zu STATUS_EFFECTS in [sf/constants.py](sf/constants.py). Geladen via `sf.sprites.get_status_icon(key)`. Pure-black BG, painterly-icon-style.

### S1. Burn *(Brennen — Valsa-Feuer-DoT)*
```
[MASTER-PREFIX], small isolated game-ui icon, single rising flame icon
in valsa-fire orange-red, painterly stylized flame with embers, faint
glowing core, dark outline for readability, fire-damage-over-time
indicator
```

### S2. Poison *(Gift — Sumpf/Wurzelgrab-DoT)*
```
[MASTER-PREFIX], small isolated game-ui icon, dripping toxic green
droplet icon with single tendril of vapor rising, painterly stylized,
faint glowing core, dark outline for readability, swamp-poison palette
```

### S3. Frost *(Frost — Tiefer Frost, hartes Slow)*
```
[MASTER-PREFIX], small isolated game-ui icon, six-pointed frost crystal
icon in pale ice-blue, painterly stylized with faceted geometry, faint
inner-glow, dark outline for readability, cold-snap palette
```

### S4. Bleed *(Bluten — Phys-DoT)*
```
[MASTER-PREFIX], small isolated game-ui icon, single falling red blood
droplet with smaller splash below, painterly stylized, deep crimson
core with darker outer rim, dark outline for readability, blood-loss
indicator
```

### S5. Shock *(Schock — Blitz-Verwundbarkeit)*
```
[MASTER-PREFIX], small isolated game-ui icon, jagged lightning-bolt
icon in pale electric-white-blue, painterly stylized with arcing
side-sparks, faint glowing core, dark outline for readability, electric
ailment palette
```

### S6. Chill *(Kaelte — Soft-Slow Vorstufe zu Frost)*
```
[MASTER-PREFIX], small isolated game-ui icon, single snowflake icon
softer and rounder than frost, pale icy-blue, painterly stylized with
gentle curves, faint cold mist around, dark outline for readability,
chill-slow palette
```

### S7. Brittle *(Sproede — Crit-Verwundbarkeit)*
```
[MASTER-PREFIX], small isolated game-ui icon, fractured glass-like shard
icon with hairline cracks radiating outward, pale-blue-white painterly
style, faint inner-light leaking through cracks, dark outline for
readability, glass-fragility indicator
```

### S8. Sapped *(Ausgelaugt — Schaden reduziert)*
```
[MASTER-PREFIX], small isolated game-ui icon, half-empty drained vial
icon with sagging liquid level and faint vapor, washed-out grey-violet
palette, painterly stylized, dark outline for readability, energy-drain
indicator
```

### S9. Armour-Break *(Panzer-Bruch — Phys-Resist gebrochen)*
```
[MASTER-PREFIX], small isolated game-ui icon, broken shield fragment
icon with crack splitting it diagonally, tarnished gold-bronze palette,
painterly stylized, dark outline for readability, defense-reduced
indicator
```

### S10. Pinned *(Festgepinnt — Movement-Lock)*
```
[MASTER-PREFIX], small isolated game-ui icon, single iron spike-nail
driven through a small target ring icon, dark steel and pale-blue ring
palette, painterly stylized, dark outline for readability, immobilize
indicator
```

### S11. Maim *(Verkruepelt — Phys-Slow)*
```
[MASTER-PREFIX], small isolated game-ui icon, severed tendon-rope icon
with frayed cut-ends, deep blood-red painterly style, faint dripping
detail, dark outline for readability, movement-cripple physical-ailment
indicator
```

### S12. Crush *(Zerschmettert — Defense-Break)*
```
[MASTER-PREFIX], small isolated game-ui icon, splintered armor fragment
icon with impact-fracture pattern radiating from center, tarnished
copper-bronze palette, painterly stylized, dark outline for readability,
defense-break ailment indicator
```

### S13. Stun *(Betaeubt — Action-Lock)*
```
[MASTER-PREFIX], small isolated game-ui icon, three small swirling stars
icon orbiting an implied central head silhouette, pale-gold painterly
style, faint motion blur, dark outline for readability, action-locked
disable indicator
```

### S14. Slow *(Verlangsamt — Generic Speed-Reduce)*
```
[MASTER-PREFIX], small isolated game-ui icon, dragging boot-print icon
with trailing motion-lines behind, washed-out brown-grey palette,
painterly stylized, dark outline for readability, movement-reduce
indicator
```

### S15. Silence *(Verstummt — Cast-Lock)*
```
[MASTER-PREFIX], small isolated game-ui icon, closed-lips icon with
sealing-thread sewn across, pale-stitch and dark-lip palette, painterly
stylized, dark outline for readability, no-cast disable indicator
```

---

## X. KOSTEN-SUMMARY

| Phase | Targets × Gens | API-Calls | % von 5000-Budget |
|---|---|---|---|
| Test | 1 × 4 | 4 | 0,08 % |
| Phase 2 | 17 × 4 | 68 | 1,4 % |
| Phase 3 | 19 × 4 | 76 | 1,5 % |
| Phase 4 | 50 × 2 | 100 | 2,0 % |
| **Prio-Pass HOCH** (Decor 17 + Items 50 + Status 15) × 2 | 82 × 2 | 164 | 3,3 % |
| **TOTAL** | **— ** | **412** | **8,3 %** |

Bei Creator-Plan (29 €/Monat) deckt das alles + viel Reserve fuer Iterationen / Re-Gens.
