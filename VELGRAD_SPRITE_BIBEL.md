# VELGRAD — SPRITE-BIBEL (POE2-Style)

> **Zweck.** Vollstaendige Sprite-Generation-Bibel mit lore-spezifischen Prompts pro Target. Quelle fuer [tools/sprite_gen.py](tools/sprite_gen.py) analog zu [VELGRAD_VOICE_CASTING.md](VELGRAD_VOICE_CASTING.md) + [VELGRAD_SFX_BIBEL.md](VELGRAD_SFX_BIBEL.md).
>
> **Tool:** [Scenario.gg](https://scenario.com) — Creator-Plan (5000 Bilder/Monat)
> **Style:** Path of Exile 2 — dark fantasy painterly, gothic medieval, volumetric lighting, gedeckte Palette
> **Total Targets:** 41 (in 6 Kategorien)

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

## X. KOSTEN-SUMMARY

| Phase | Targets × Gens | API-Calls | % von 5000-Budget |
|---|---|---|---|
| Test | 1 × 4 | 4 | 0,08 % |
| Phase 2 | 17 × 4 | 68 | 1,4 % |
| Phase 3 | 19 × 4 | 76 | 1,5 % |
| Phase 4 | 50 × 2 | 100 | 2,0 % |
| **TOTAL** | **— ** | **248** | **5,0 %** |

Bei Creator-Plan (29 €/Monat) deckt das alles + viel Reserve fuer Iterationen / Re-Gens.
