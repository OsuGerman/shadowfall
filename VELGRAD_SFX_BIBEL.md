# VELGRAD — SFX-BIBEL

> **Zweck.** Vollstaendiger Katalog aller benoetigten Sounds + Generation-Prompts.
> Quell-Dokument fuer die SFX-Pipeline ([tools/sfx_gen.py](tools/sfx_gen.py))
> analog zu [VELGRAD_VOICE_CASTING.md](VELGRAD_VOICE_CASTING.md).
>
> **Tool-Strategie:**
> - **ElevenLabs Sound Effects API** — kurze SFX (<= 22 s) wie Hits, Stinger, Mob-Sounds, UI
> - **Suno AI** — Musik (Akt-Themes, Boss-Themes) — manueller Browser-Workflow (keine offene API)
> - **Stable Audio / MusicGen** — Ambience-Loops (90 s+) — optional, lokal
> - **Freesound.org** (CC0) — Generic UI / Combat (bereits zu 80 % im Bestand)
>
> **Bestand:** 267 MP3s, 45 MB in `Sounds/`. Mehrheit ist Generic-Stock — funktional, aber nicht velgrad-spezifisch.

---

## INDEX

- [I. UI / Menue-Sounds](#i-ui)
- [II. Combat / Waffen-Effekte](#ii-combat)
- [III. Skill / Magic / Aspekt-Sounds](#iii-skills)
- [IV. Monster / Mob-Sounds (30 Mobs)](#iv-monster)
- [V. Boss-Stinger & Phase-Transitions](#v-boss)
- [VI. Cinematic-Stinger (9 Cutscenes)](#vi-cinematic)
- [VII. Environment / Ambience-Loops](#vii-ambience)
- [VIII. Music (Akt + Boss + Town Themes)](#viii-music)
- [IX. Lore-Spezifische Sounds](#ix-lore)
- [X. Generation-Pipeline](#x-pipeline)

---

<a name="i-ui"></a>
## I. UI / MENUE-SOUNDS (30 Sounds, ~5 SFX bereits in Bestand)

Alle UI-SFX sollen **kurz, klar, lore-konsistent** sein. Velgrad-Style: kein Sci-Fi-Bleeps, mehr „Aspekt-Atem" — Stein-auf-Stein, Atem, Kristall-Ton.

### Pflicht-Sounds

| ID | Status | ElevenLabs-Prompt | Dauer |
|---|---|---|---|
| `ui_click` | ⚠ stock vorhanden | "soft stone-on-stone click, subtle reverb, 0.2 sec" | 0.2 s |
| `ui_hover` | ⚠ stock | "very soft breath sigh, almost inaudible, 0.15 sec" | 0.15 s |
| `ui_modal_open` | ❌ | "ancient parchment unfurling, soft, 0.6 sec" | 0.6 s |
| `ui_modal_close` | ❌ | "parchment folding back, soft, 0.4 sec" | 0.4 s |
| `ui_inventory_open` | ❌ | "leather satchel unbuckling, 0.5 sec" | 0.5 s |
| `ui_item_pickup_common` | ⚠ | "cloth bag rustling, brief, 0.4 sec" | 0.4 s |
| `ui_item_pickup_rare` | ❌ | "crystalline ring, soft chime, 0.7 sec" | 0.7 s |
| `ui_item_pickup_unique` | ❌ | "deep resonant chime with reverb tail, like a memory-stone awakening, 1.2 sec" | 1.2 s |
| `ui_item_pickup_mythic` | ❌ | "low temple bell with echo trail, 1.8 sec" | 1.8 s |
| `ui_coin_drop` | ⚠ | "single gold coin hitting stone, clear ring, 0.5 sec" | 0.5 s |
| `ui_levelup` | ✅ `levelup` | (vorhanden) | 2 s |
| `ui_skillpoint` | ❌ | "warm pulse of breath inwards, then a soft exhale, 1 sec" | 1 s |
| `ui_quest_offered` | ✅ `quest_notify` | (vorhanden) | 1 s |
| `ui_quest_advance` | ❌ | "ink scratching on parchment, brief, 0.4 sec" | 0.4 s |
| `ui_quest_complete` | ✅ | (vorhanden) | 1.5 s |
| `ui_skill_unlocked` | ❌ | "memory-stone humming awake, ascending tone, 1.5 sec" | 1.5 s |
| `ui_save_game` | ❌ | "stone tablet being set down on stone, hollow, 0.8 sec" | 0.8 s |
| `ui_death_screen` | ❌ | "long slow exhale that fades into silence, 3 sec" | 3 s |
| `ui_map_open` | ❌ | "parchment map unfolding, 0.7 sec" | 0.7 s |
| `ui_portal_open` | ❌ | "deep resonant tone with shimmer, 2 sec" | 2 s |
| `ui_portal_close` | ❌ | "reverse shimmer fade out, 1.5 sec" | 1.5 s |
| `ui_mahnmal_activate` | ❌ | "ancient stone stele humming awake, deep resonance, 1.8 sec" | 1.8 s |
| `ui_pakt_stone_equip` | ❌ | "memory crystal locking into place, soft click + resonance, 1 sec" | 1 s |
| `ui_aspekt_choice` | ❌ | "seven-toned chord, ethereal, 2 sec" | 2 s |
| `ui_currency_marken` | ❌ | "metal tag clinking on chain, brief, 0.5 sec" | 0.5 s |
| `ui_currency_shard` | ❌ | "shard of memory glass tapping, soft chime, 0.5 sec" | 0.5 s |
| `ui_low_hp_warning` | ⚠ `breath_low_hp` | "ragged shallow breathing, loop 4 sec" | 4 s loop |
| `ui_critical_hp` | ❌ | "rapid heartbeat with breath, loop 3 sec" | 3 s loop |
| `ui_vergessens_welle` | ❌ | "world inhaling — the sound of a memory being forgotten, 2 sec" | 2 s |
| `ui_choice_made` | ❌ | "single deep gong with subtle reverb, 1.5 sec" | 1.5 s |

**Status:** ~6 ✅ vorhanden, **24 zu generieren**. ElevenLabs SFX-Kosten: 24 × ~80 char-equiv = ~1.5k chars = **~0,30 €**.

---

<a name="ii-combat"></a>
## II. COMBAT / WAFFEN-EFFEKTE (45 Sounds)

Pro Waffen-Typ braucht es: **Swing/Cast** (Wind-up) + **Hit-Light** + **Hit-Medium** + **Hit-Heavy** + **Crit** + **Miss/Block**. Generisches Material ist da; **Velgrad-spezifische Variationen fehlen**.

### Bereits Vorhanden (sf/sounds.py Aliases) ✅
- `melee_swing`, `sword_slash`, `axe_metal_1..4`, `axe_dirt`, `axe_wood`
- `greatsword_swing_1/2`, `arrow_impact_1/2`
- `spell_impact`, `roar`, `monster_bite`

### Fehlend pro Waffen-Typ

| Waffen-Klasse | Swing | Light-Hit | Heavy-Hit | Crit | Sondereffekt |
|---|---|---|---|---|---|
| **Mace (Warrior)** | ✅ | ❌ | ❌ | ❌ | „bone-crush" |
| **Sword (1H/2H)** | ✅ | ✅ | ⚠ | ❌ | „flesh-cut" |
| **Axe** | ✅ | ✅ | ✅ | ❌ | „cleave" |
| **Dagger (Witch)** | ❌ | ❌ | ❌ | ❌ | „whisper-stab" — kalt, kaum hörbar |
| **Spear (Huntress)** | ❌ | ❌ | ❌ | ❌ | „pierce-through" |
| **Quarterstaff (Monk)** | ❌ | ❌ | ❌ | ❌ | „whirl-air" |
| **Bow (Ranger)** | ⚠ | ✅ | ❌ | ❌ | „arrow-release-creak" |
| **Crossbow (Merc)** | ❌ | ✅ | ❌ | ❌ | „bolt-mechanism-click" |
| **Wand (Sorceress)** | ❌ | ❌ | — | ❌ | „spark-snap" |
| **Sceptre / Staff** | ❌ | ❌ | — | ❌ | „resonance-charge" |
| **Talisman (Druid)** | ❌ | ❌ | — | ❌ | „animal-roar" |

### Beispiel-Prompts (ElevenLabs SFX)

```
dagger_whisper_stab    "cold dagger stabbing through cloth and flesh, very brief whisper, 0.4 sec"
spear_pierce_through   "spear punching through armor and flesh, single impact, 0.6 sec"
quarterstaff_whirl     "wooden staff whirling through air, ending in solid hit on bone, 0.7 sec"
bow_release_creak      "longbow arrow release with wood creak, 0.4 sec"
crossbow_click_bolt    "crossbow mechanism click followed by bolt fire, 0.5 sec"
wand_spark_snap        "single magical spark snapping with crackle, 0.3 sec"
sceptre_charge         "resonant energy gathering, slight tremor, 1.2 sec"
talisman_bear_roar     "low animal roar through magical filter, 1 sec"
talisman_wolf_howl     "wolf howl through magical reverb, 1.5 sec"
talisman_wyvern_screech "wyvern screech through magical filter, 1 sec"
mace_bone_crush        "heavy iron mace crushing bone, deep impact, 0.6 sec"
sword_flesh_cut        "sword slicing through cloth and flesh, wet, 0.5 sec"
axe_cleave_thru        "heavy two-handed axe cleaving through bone, 0.7 sec"
crit_universal         "high-tension impact with metal ring and deep thud, 0.8 sec"
crit_blood             "crit hit with brief blood splatter, 0.6 sec"
block_metal_metal      "two metal blades clashing and locking, 0.5 sec"
block_shield_wood      "weapon hitting wooden shield, dull thud, 0.4 sec"
parry_ring             "metallic ring of parry, sharp, 0.4 sec"
miss_air               "weapon cutting air, no impact, 0.3 sec"
dodge_cloth            "cloth rustling as character dodges, 0.3 sec"
```

**Status:** ~10 ✅, **30+ zu generieren**. Kosten: ~6 € ElevenLabs.

---

<a name="iii-skills"></a>
## III. SKILL / MAGIC / ASPEKT-SOUNDS (50 Sounds)

Aktuell hat `sf/sounds.py` 4 generische Casts (`cast_fire`, `cast_lightning`, `cast_heal`, `cast_dark`). Velgrad-Lore hat **7 Aspekte** — jeder braucht ein **Cast-Theme** + **Impact** + **Tick** (für DOT).

### Aspekt-Sound-Familie

| Aspekt | Element | Cast | Impact | Tick (DOT) |
|---|---|---|---|---|
| **Kharn (Form)** | Physical/Iron | ❌ | ❌ | n/a |
| **Nheyra (Zeit)** | Time-Slow/Cold | ⚠ (`cast_lightning` als Platzhalter) | ❌ | ❌ |
| **Ousen (Geist)** | Mental/Mind | ❌ | ❌ | ❌ |
| **Valsa (Wille)** | Fire/Brand | ✅ `cast_fire` | ⚠ | ❌ |
| **Im-Nesh (Sprache)** | Chaos/Corruption | ❌ | ❌ | ❌ |
| **Shulavh (Bindung)** | Bind/Root | ❌ | ❌ | ❌ |
| **Der Siebte (Vergessen)** | Void/Forget | ❌ | ❌ | ❌ |

### Generation-Prompts (Aspekt-pro-Aspekt)

```
aspekt_kharn_cast     "iron forge ringing with rising power, 1.5 sec"
aspekt_kharn_impact   "iron crashing into iron, heavy and final, 0.8 sec"

aspekt_nheyra_cast    "clock ticking accelerating into reverse, ethereal, 1.5 sec"
aspekt_nheyra_impact  "time freezing — glass shattering in reverse, 1 sec"
aspekt_nheyra_tick    "single time-distorted tone, 0.4 sec"

aspekt_ousen_cast     "deep telepathic hum rising in pitch, 1.5 sec"
aspekt_ousen_impact   "psychic blast — like a thought breaking, 0.8 sec"

aspekt_valsa_cast     (existiert als cast_fire)
aspekt_valsa_impact   "fire explosion with ash debris, 1 sec"
aspekt_valsa_tick     "single ember crackle, 0.3 sec"

aspekt_imnesh_cast    "whispered alien syllables overlapping, unsettling, 1.5 sec"
aspekt_imnesh_impact  "concept-bending shockwave, 1 sec"
aspekt_imnesh_tick    "single whispered syllable, 0.3 sec"

aspekt_shulavh_cast   "organic roots growing rapidly, wet and tearing, 1.5 sec"
aspekt_shulavh_impact "thick roots binding flesh, 1 sec"
aspekt_shulavh_tick   "single rope-creak tightening, 0.4 sec"

aspekt_vergessen_cast    "world unmaking itself — reverse of sound, 1.5 sec"
aspekt_vergessen_impact  "silence-implosion, brief moment of zero-audio with subtle inhale, 1 sec"
```

### Klassen-Skill-Specials

```
warrior_slam      "two-handed weapon slamming ground with shockwave, 1 sec"
warrior_shout     (use voice_lines from cls_warrior)
monk_three_breath "three rapid breaths of focus, ascending power, 1.5 sec"
monk_pagoda_step  "single bare footstep on wooden floor, soft, 0.4 sec"
sorceress_brand   "fire branding into skin with sizzle, 1 sec"
witch_skeleton_summon "bones clacking together as skeleton assembles, 1.5 sec"
witch_thread_pull "rope of fate snapping into existence, 1 sec"
ranger_seed_fly   "seed-pod flying through air with whistle, 0.7 sec"
ranger_growl_bind "vines growing rapidly with rustle, 1 sec"
mercenary_reload  "crossbow reload with chain clinks, 1.2 sec"
mercenary_signature "single low whistle of mercenary signal, 0.6 sec"
huntress_throw_spear  "spear spinning through air with whoosh, 0.8 sec"
huntress_moon_bind    "lunar resonance — high silver chime, 1 sec"
druid_shapeshift_bear "human-to-bear transformation crunch, 1.5 sec"
druid_shapeshift_wolf "human-to-wolf transformation crunch, 1.5 sec"
druid_shapeshift_wyvern "human-to-wyvern transformation crunch with screech, 1.5 sec"
```

**Status:** ~5 ✅, **35+ zu generieren**. Kosten: ~5 € ElevenLabs.

---

<a name="iv-monster"></a>
## IV. MONSTER / MOB-SOUNDS (30 Mobs × 4 = 120 SFX)

Pro Mob aus [VELGRAD_BESTIARIUM.md](VELGRAD_BESTIARIUM.md): **Idle/Alert** + **Attack** + **Hurt** + **Death**.

Aktuell ist nur ein generisches `monster_bite`, `monster_howl`, `cave_monster` Pool da. **30 Mobs sind im Bestiarium** — jeder braucht eigenen Sound.

### Akt-1-Mob-Sounds (Priorität für Akt-1-Pass)

```
salzgekreuzter_idle     "wet drowned breathing, gurgling, loop 4 sec"
salzgekreuzter_alert    "drowned-throat groan rising, 1 sec"
salzgekreuzter_attack   "wet flesh-grab, brief gurgle, 0.6 sec"
salzgekreuzter_hurt     "drowned scream short, 0.5 sec"
salzgekreuzter_death    "long underwater gurgle fading, 2 sec"

krustenkrabbe_idle      "shell clicking on wet stone, brief, 0.5 sec"
krustenkrabbe_alert     "high-pitched crab screech, 0.4 sec"
krustenkrabbe_attack    "pincer snap with hard click, 0.4 sec"
krustenkrabbe_hurt      "shell crack with crab pain-shriek, 0.5 sec"
krustenkrabbe_death     "shell breaking with wet collapse, 1 sec"

ertrunkenes_echo_idle   "ghostly underwater moan, ethereal, 3 sec loop"
ertrunkenes_echo_attack "ghost wail with water sound, 0.8 sec"
ertrunkenes_echo_death  "ghost dissolving into water mist, 2 sec"

moewen_schwarm_attack   "multiple seagulls screeching dive-bomb, 1 sec"
moewen_schwarm_death    "single dying seagull, 0.7 sec"

salzhueter_brut_roar    "ancient drowned statue roar with deep reverb and water, 2 sec"
salzhueter_brut_attack  "stone arm hitting wet ground heavily, 0.8 sec"
salzhueter_brut_hurt    "stone cracking with drowned voice underneath, 1 sec"
salzhueter_brut_death   "stone statue collapsing into salt water, 3 sec"
salzhueter_brut_phase   "phase-transition — water rushing inward, 2 sec"
```

### Akt-2 (Glasgolden) - Mob-Sounds

```
echo_senator_idle       "echoing aristocratic muttering in ancient tongue, 4 sec loop"
echo_senator_attack     "magical gold dust burst with old-language word, 0.7 sec"
echo_senator_death      "voice fading into golden silence, 2 sec"

goldstaub_diener_idle   "golden particles rustling, soft, 3 sec loop"
goldstaub_diener_attack "gold dust binding form, sharp constrictor, 0.6 sec"
goldstaub_diener_death  "particles dissipating with sigh, 1.5 sec"

glasgolden_waechter_idle    "stone construct heavy breathing, mechanical, 4 sec loop"
glasgolden_waechter_attack  "massive stone fist crashing down, 0.8 sec"
glasgolden_waechter_death   "construct collapsing into golden shards, 2.5 sec"

spiegel_stalker_idle    "glass surface humming, subtle, 4 sec loop"
spiegel_stalker_attack  "mirror shard slicing through air, 0.4 sec"
spiegel_stalker_death   "mirror shattering with thousand reflections, 1.5 sec"

verfallener_magister_cast   "decayed magical incantation with crystal ringing, 1.5 sec"
verfallener_magister_death  "old magic dissipating with sigh, 2 sec"
```

### Akt-3 (Aschenfelder) - Mob-Sounds

```
asch_soldat_alert       "skeletal soldier rattling armor, 0.7 sec"
asch_soldat_attack      "rusted sword swing through ash, 0.5 sec"
asch_soldat_death       "armor collapsing into ash pile, 1.5 sec"

predigtsprecher_cast    "fanatical preacher chanting in burning voice, 2 sec"
predigtsprecher_death   "preacher choking on smoke, 1.5 sec"

inquisitions_klinge_attack  "stealth blade strike, very brief, 0.3 sec"
inquisitions_klinge_death   "single death-gasp, 0.5 sec"

asch_wolf_idle          "wolf growl with ash-rasp, 2 sec"
asch_wolf_attack        "wolf bite with ember crackle, 0.6 sec"
asch_wolf_death         "wolf yelp dissolving into ash-wind, 1.5 sec"

tribunal_konstrukt_step "heavy stone-tribunal footstep, deep thud, 0.6 sec"
tribunal_konstrukt_attack "massive holy hammer impact, 1 sec"
tribunal_konstrukt_death "construct breaking with stone tumble, 2.5 sec"
```

### Akt-4 (Wurzelgrab) - Mob-Sounds

```
knochenhexe_cast        "bone-witch chanting with bone-clack rhythm, 1.5 sec"
knochenhexe_death       "old witch crumbling, 1.5 sec"

wurzel_spinne_idle      "wooden creaking with chitin click, 3 sec loop"
wurzel_spinne_attack    "wood-spider striking with snap, 0.5 sec"
wurzel_spinne_death     "spider collapsing into roots, 1.5 sec"

fadengebundene_idle     "puppet strings creaking taut, 3 sec loop"
fadengebundene_attack   "marionette jerk-strike, 0.5 sec"
fadengebundene_death    "strings snapping with body collapse, 1.5 sec"

hohler_sohn_alert       "child crying from deep underground, distorted, 2 sec"
hohler_sohn_attack      "small hands grabbing flesh, 0.7 sec"
hohler_sohn_death       "child sigh of relief, 1.5 sec"

mark_krieger_idle       "tree-bark armor creaking, 3 sec loop"
mark_krieger_attack     "wooden war club impact, 0.7 sec"
mark_krieger_death      "tree-warrior cracking apart like log, 2 sec"
```

### Akt-5/6/7 - Mob-Sounds (Endgame-Priorität, später generieren)

```
stunden_wandler_idle    "time-distorted ambient hum, eerie, 4 sec loop"
senator_phantom_attack  "ghostly senatorial accusation, 1 sec"
glasscherben_taenzerin  "ballet movement with glass-shard ring, 1 sec"
sich_selbst_spielende   "player's own attack sounds in reverse, 1 sec"
spiegel_hueter_attack   "mirror-guardian massive strike, 1 sec"
ertrunkene_koenigin_roar (Boss — see §V)
echo_drache_roar         (Boss — see §V)
nicht_gott_attack        "wrongness manifest — sound that should not exist, 1.5 sec"
nicht_mann_attack        "anomaly attack — sound bending, 0.8 sec"
aspekt_echo_attack       "corrupted aspect attack — modulated divine voice, 1.2 sec"
```

**Status:** Bestiarium hat 30 Mobs, davon **~5 generisch abgedeckt**. **120 SFX zu generieren** für vollen Pool. Pragmatisch: pro Akt 1 Pass → **Akt-1-Mobs zuerst (20 SFX, ~3 €)**, dann sukzessive.

---

<a name="v-boss"></a>
## V. BOSS-STINGER & PHASE-TRANSITIONS (15 Bosse × 3 = 45 SFX)

Pro Boss-Encounter aus [WELT_AUFBAU.md](WELT_AUFBAU.md) §4 + QUEST_BIBEL.md: **Spawn-Stinger** + **Phase-Transition** + **Kill-Stinger**.

### Generation-Prompts pro Boss

```
salzhueter_spawn        "ancient salt statue awakening with grinding stone and water surge, 3 sec"
salzhueter_phase        "stone cracking with water-pressure increase, 2 sec"
salzhueter_kill         "statue collapsing into salt mist, 4 sec"

senator_geist_spawn     "ghostly gold-dust gathering with senatorial gavel-strike, 3 sec"
senator_geist_phase     "gold-dust storm intensifying, 2 sec"
senator_geist_kill      "voice echoing into eternity then silence, 4 sec"

vehren_spawn            "inquisitor's gavel slamming, then deep horn, 3 sec"
vehren_phase            "valsa-fire bursting through armor, 2 sec"
vehren_kill             "armor falling with last gasp, 4 sec"

shulavh_spawn           "mother's lullaby distorted into wail with root-creak, 4 sec"
shulavh_phase_madness   "lullaby breaking into laughter, unsettling, 2 sec"
shulavh_phase_forget    "lullaby fading into silence-with-inhale, 2 sec"
shulavh_kill            "thread snapping, then a sigh of relief, 4 sec"

velharn_trio_spawn      "three voices speaking at once across time, 4 sec"
velharn_phase_1to2      "time-shift — golden age to war age, 3 sec"
velharn_phase_2to3      "time-shift — war age to present, hollow, 3 sec"
velharn_kill            "three voices silenced one by one, 5 sec"

ertrunkene_koenigin_spawn   "queen rising from salt-wound with crown clinking underwater, 4 sec"
ertrunkene_koenigin_phase   "salt water flooding cavern, 3 sec"
ertrunkene_koenigin_kill    "drowning lament fading, 4 sec"

echo_drache_spawn       "massive dragon roar through ash-storm, 4 sec"
echo_drache_phase       "dragon-fire intensifying, 3 sec"
echo_drache_kill        "dragon falling into ash with final breath, 5 sec"

nicht_gott_spawn        "wrongness — sound that shouldn't exist, reality bending, 4 sec"
nicht_gott_phase        "concept of phase-transition itself glitching, 3 sec"
nicht_gott_kill         "anomaly collapsing into nothing, 4 sec"

im_nesh_spawn           "calm friendly voice fading into hundred voices, layered, 5 sec"
im_nesh_phase_1to2      "voice becoming desperate, faster, 3 sec"
im_nesh_phase_2to3      "voice splitting into hundred languages, 4 sec"
im_nesh_kill            "all voices speaking different last words at once, 5 sec"

aspekt_echo_kharn       "distorted Kharn-iron roar, 4 sec"
aspekt_echo_nheyra      "distorted Nheyra-time-shatter, 4 sec"
aspekt_echo_ousen       "distorted Ousen-mind-blast, 4 sec"
aspekt_echo_valsa       "distorted Valsa-fire-rage, 4 sec"
aspekt_echo_shulavh     "distorted Shulavh-mother-bind, 4 sec"
aithein_echo            "the sound of god dreaming — vast, slow, indescribable, 6 sec"
der_achte               "the missing eighth — sound from a god that shouldn't exist, 5 sec"
```

**Status:** **45 SFX zu generieren**. Kosten: ~12 €. Pragmatisch: Akt-1-Boss + Akt-3-Boss + Im-Nesh zuerst = 9 SFX (~2,50 €).

---

<a name="vi-cinematic"></a>
## VI. CINEMATIC-STINGER (9 Pflicht-Cutscenes × 3 = 27 SFX)

Pro Cutscene aus WELT_AUFBAU §12.8: **Open-Stinger** + **Reveal-Stinger** + **Close-Stinger**.

```
akt1_intro_shipwreck    "shipwreck — wood splintering, water roaring, gull cries, 5 sec"
akt1_intro_reveal       "narrator-voice tone (memory-stone awakening hum), 3 sec"
akt1_intro_close        "calm beach with distant church bell, 4 sec"

akt2_helst_open         "blind priest's first words spoken in ancient hall, 3 sec"
akt2_helst_reveal       "name 'Im-Nesh' spoken — world flinching, 2 sec"
akt2_helst_close        "soft echo fade, 3 sec"

akt3_vehren_open        "inquisition horn echoing across ash field, 4 sec"
akt3_vehren_reveal      "valsa-fire taking over vehren's body, 3 sec"
akt3_vehren_close       "ash settling silently, 4 sec"

akt4_shulavh_open       "mother's hum heard for the first time deep underground, 4 sec"
akt4_shulavh_reveal     "shulavh's true name spoken (whispered by player), 2 sec"
akt4_shulavh_close      "thread tightening or loosening (choice-dependent), 3 sec"

akt5_ousen_open         "the voice in player's head finally speaking out loud, 3 sec"
akt5_ousen_reveal       "ousen's name revealed — name as cosmic event, 3 sec"
akt5_ousen_close        "two clearer thoughts in player's head, 3 sec"

akt6_disguise_open      "trusted ally turning slowly to reveal Im-Nesh-mask, 4 sec"
akt6_disguise_reveal    "voice unchanging but words completely different — betrayal stinger, 3 sec"
akt6_disguise_close     "mask falls, real face revealed (silence), 3 sec"

akt7_imnesh_open        "imnesh greeting player like an old friend, 3 sec"
akt7_imnesh_reveal      "argument starting — civilized debate of cosmic ending, 4 sec"
akt7_imnesh_close       "hundred voices interrupting at once, 3 sec"

ending_a_sacrifice      "player fading into hollow geweihte — long sigh, 6 sec"
ending_b_betrayer       "player taking up im-nesh's pen — single dark stroke, 5 sec"
ending_c_dreamer        "aithein inhaling — the breath that wakes the world, 7 sec"

reveal_universal        "single deep gong with reverb tail — Velgrad's signature reveal sound, 3 sec"
silence_universal       "absence of sound made audible — for vergessens-welle, 2 sec"
chord_seven_aspects     "seven-tone chord of all aspects together, 4 sec"
```

**Status:** **27 Cinematic-SFX zu generieren**. Kosten: ~8 €.

---

<a name="vii-ambience"></a>
## VII. ENVIRONMENT / AMBIENCE-LOOPS (20 Sounds, 6 vorhanden)

Velgrad-spezifische Ambience pro Biome. Aktuell sind generische Fire/Ice/Wind im Bestand — passt aber für Crypt/Frost/Lava noch nicht ganz lore-konsistent.

```
ambient_brassweir_day    "harbor town with seagulls, distant ship bells, salt wind, loop 60 sec"
ambient_brassweir_night  "harbor town at night, lapping water, distant lantern creak, loop 60 sec"

ambient_salzkueste       "salt-cursed coast — wet wind, distant drowned voices, salt-crystals tinkling, loop 60 sec"
ambient_salzwunde        "salt-wound pulsing — wet rhythmic breathing of the world, loop 60 sec"

ambient_echo_markt       "glasgolden ruins market with echo-vendor mutterings, gold-dust falling, loop 60 sec"
ambient_glasgold_ruins   "ancient glass-towers swaying impossibly, golden wind, loop 60 sec"

ambient_aschenfeld       "ash falling silently, distant inquisitor patrol bells, embers, loop 60 sec"
ambient_aschwunde        "ash-wound burning without fuel, pain-undertone, loop 60 sec"

ambient_knoten_markt     "root-market with bone-clack and old-woman-mumbling, loop 60 sec"
ambient_wurzelgrab       "underground root cavern — wood creaking, dripping water, distant lullaby, loop 60 sec"

ambient_spiegelhof       "court of mirrors — three time-layers overlapping audibly, loop 60 sec"
ambient_velharn          "mirror city — voices from past speaking present words, loop 60 sec"

ambient_hohlwunde        "hollow-wound — paradox of audible silence, loop 60 sec"

ambient_hohlwort         "hollow-word — language being unmade, loop 60 sec"
ambient_drei_muetter     "three mothers humming three different lullabies at once, loop 60 sec"

ambient_stille_zone      "complete absence of sound with subtle inhale every 10 sec, loop 60 sec"
ambient_vergessens_welle "world inhaling — a single 8-sec loop of forgetting, loop 8 sec"

ambient_zhar_eth         "wandering caravan — bells, hooves on sand, spear-clinks, loop 60 sec"
ambient_saeulen_helst    "burning pillars of helst — fanatical chants in distance, loop 60 sec"

ambient_atlas_general    "atlas hub — between-worlds humming, loop 60 sec"
```

**Status:** **~6 generisch vorhanden, 14+ velgrad-spezifisch zu generieren**. Loops > 22s gehen NICHT mit ElevenLabs SFX. Stattdessen: **Stable Audio** (90 s native) oder **MusicGen** lokal.

---

<a name="viii-music"></a>
## VIII. MUSIC (Akt + Boss + Town Themes)

**Aktuell:** 2 MP3-Tracks (`Nebel von Arken.mp3` + `Soundtrack 3.mp3`) — beide ~4-5 MB, ~3-4 Min. Stilistisch gut für Velgrad (dunkel, ambient).

**Soll-Liste:**

### Town-/Hub-Music (8 Tracks)
- Brassweir Day Theme (3-4 min)
- Brassweir Night Theme (3-4 min)
- Echo-Markt Theme
- Säulen-von-Helst Theme
- Knoten-Markt Theme
- Spiegelhof Theme
- Drei-Wunden-Lager Theme
- Hohlwort Theme

### Akt-Dungeon-Themes (7 Tracks)
- Salzkueste (Crypt) Theme
- Glasgolden Ruins Theme
- Aschenfelder Theme
- Wurzelgrab Theme
- Velharn Theme
- Drei Wunden Theme
- Hohlwort Dungeon Theme

### Boss-Themes (15 Tracks)
- Pro Boss aus §V eigenes Theme (kürzer, intensiver, 1.5-2 min Loop)

### Cinematic-Music (9 Tracks)
- Pro Cutscene-Phase (Open / Reveal / Close-Theme)

### Endgame-Atlas (3 Tracks)
- Welkende-Welten Atlas-Hub
- Aithein-Echo Pinnacle
- Im-Nesh-Reborn Hardmode

**Total Music: ~42 Tracks**

### Tool-Strategie für Music

**Suno AI** (https://suno.ai):
- Beste Qualität für Game-Music aktuell.
- Pro-Plan ~ 30 €/mo = 2.000 Generations/Monat.
- KEINE offizielle API — Browser-Workflow oder community-Tools.
- Per Theme: 2-3 Generations bis das Ergebnis sitzt.

**Empfohlene Suno-Prompt-Templates** (Velgrad-Stil):

```
Brassweir Day:    "dark folk acoustic, melancholic seafaring, distant bell, German medieval, mid-tempo, instrumental"
Brassweir Night:  "ambient piano, very slow, single melody, sea wind, sparse, melancholic"
Echo-Markt:       "baroque ghost orchestra, decayed nobility, harpsichord with strings, eerie elegance"
Aschenfelder:    "industrial dark ambient, inquisition drums, low brass, distant chants in German"
Wurzelgrab:      "ritualistic forest dark folk, throat singing, drums, female lullaby fragments"
Velharn:         "three layered themes from three eras — baroque + medieval war horns + minimalist ambient"
Hohlwort:        "deconstructed orchestra — pieces of every previous theme breaking apart"

Salzhueter Boss:    "rising dread orchestral, water-themed percussion, ancient statue, 2-min build"
Vehren Boss:        "inquisition battle music, choir + drums + brass, righteous fury, 2-min loop"
Shulavh Boss:       "lullaby breaking into nightmare, mother's voice with strings, 3-phase build"
Im-Nesh Final:      "calm dialog music transitioning to hundred-voice chaos, epic finale, 5 min"
```

**Suno-Workflow:**
1. Prompt eingeben → Suno generiert 2 Varianten
2. Beste Variante „extenden" (3-5 min)
3. Als MP3 herunterladen
4. In `Sounds/music/` ablegen
5. In `sf/sounds.py` `MUSIC_FILES` + `MUSIC_PLAYLISTS` registrieren

**Status:** **40 Tracks zu generieren via Suno**. Suno Pro = 30 €/mo, deckt einen Monat Production locker ab.

---

<a name="ix-lore"></a>
## IX. LORE-SPEZIFISCHE SOUNDS (15 Sounds)

Spezielle Sounds für Velgrad-Mechaniken, die kein anderes Game hat:

```
mahnmal_stele_pulse     "stone stele pulsing softly with memory, loop 4 sec"
mahnmal_stele_save      "stele acknowledging save with single tone, 1 sec"
mahnmal_travel_arrive   "memory-stone teleport arrival, soft chime + breath, 1.5 sec"
mahnmal_travel_depart   "memory-stone teleport departure, reverse chime, 1.5 sec"

pakt_stone_glow         "pact-stone humming in ambient resonance, loop 3 sec"
pakt_stone_activate     "pact-stone surging with power, 1 sec"

vergessens_welle_warn   "world inhaling — warning of upcoming forgetting wave, 2 sec"
vergessens_welle_hit    "object/enemy being unmade from existence, 1.5 sec"

hohle_gewordene_step    "person without shadow walking — almost-no-sound, eerie, 0.5 sec"
hohle_gewordene_voice   "voice that should be there but isn't quite, 1 sec"

drei_zeiten_shift       "time-layer shifting in Velharn, 1.5 sec"

aspekt_pakt_choice      "choosing an aspect — that aspect's signature chord, 2 sec"
aspekt_pakt_activate    "passive pact buff activating per aspect, 0.6 sec"

stille_zone_enter       "stepping into silence-zone — sudden audio absence, 0.5 sec"
stille_zone_exit        "stepping out — audio returning with relief, 0.5 sec"
```

**Status:** **15 SFX zu generieren**. Kosten: ~3 €.

---

<a name="x-pipeline"></a>
## X. GENERATION-PIPELINE

### Phase 1 — Tool aufbauen
- [ ] `tools/sfx_config.py` (analog `voice_config.py`)
- [ ] `tools/sfx_gen.py` — ElevenLabs Sound-Effects API
- [ ] `tools/sfx_catalog_builder.py` — parst VELGRAD_SFX_BIBEL.md → `sounds/sfx/sfx_manifest.json`
- [ ] `sf/sfx_registry.py` — Engine-Integration mit Aspekt-Pool-Picker

### Phase 2 — Akt-1-Pass (Priorität)
- [ ] UI (24 SFX) — ~0,30 €
- [ ] Akt-1-Mobs (20 SFX) — ~3 €
- [ ] Akt-1-Boss (3 SFX) — ~0,80 €
- [ ] Combat-Klassen-Specials (15 SFX) — ~3 €
- [ ] Aspekt-Sounds Kharn/Valsa/Shulavh (9 SFX) — ~2 €
- [ ] **Akt-1-Pass Total: ~71 SFX, ~9 €**

### Phase 3 — Volle Pipeline (Akt 2-7 + Endgame)
- [ ] Akt-2 bis 7 Mobs (100 SFX) — ~15 €
- [ ] Bosse Akt-2 bis Endgame (42 SFX) — ~10 €
- [ ] Cinematic-Stinger (27 SFX) — ~8 €
- [ ] Lore-spezifisch (15 SFX) — ~3 €
- [ ] **Vollausbau Total: ~250 SFX, ~50 €** (ElevenLabs SFX-Cost ≈ char-equivalent)

### Phase 4 — Music via Suno
- [ ] Suno Pro abonnieren (30 €/mo)
- [ ] 42 Tracks generieren — 1-2 Monate Production-Time
- [ ] Naming-Convention: `music/<context>_<variant>.mp3`
- [ ] In `sf/sounds.py` `MUSIC_FILES` + `MUSIC_PLAYLISTS` registrieren

### Phase 5 — Ambience via Stable Audio / MusicGen
- [ ] Stable Audio Web (Free-Tier 20 Generations/mo)
- [ ] 14 Velgrad-spezifische Ambience-Loops generieren
- [ ] Audacity Cross-Fade an Loop-Punkten (sonst Click hörbar)

---

## API-DETAIL: ELEVENLABS SOUND EFFECTS

**Endpoint:** `POST https://api.elevenlabs.io/v1/sound-generation`

**Payload:**
```json
{
  "text": "heavy iron mace crushing bone, deep impact, 0.6 sec",
  "duration_seconds": 0.6,
  "prompt_influence": 0.7
}
```

**Output:** MP3 (default 44.1 kHz, 128 kbit/s)

**Pricing (Stand 2026):**
- Counts as **~50 credits per second of audio** (analog zu Voice).
- Creator-Plan 100k credits/mo deckt ~33 min Audio.
- Bei durchschnittlich 1 s/SFX = 100k credits / 50 = 2.000 SFX/Monat. **Mehr als genug**.

**Prompt-Tipps:**
- Kurze, präzise Beschreibungen
- Dauer in Sekunden explizit nennen
- Lore-Context vermeiden (ElevenLabs versteht "Velgrad" nicht — beschreib das Geräusch konkret)
- Quality-Modifier: "high quality, clear, no music"

---

## NAECHSTE 3 KONKRETE SCHRITTE

1. **`tools/sfx_gen.py` bauen** (analog `voice_gen.py`) — ich kann sofort starten.
2. **Akt-1-Pass starten** (71 SFX, ~9 €) — testet die ganze Pipeline + macht Akt-1 sound-komplett.
3. **Suno Pro entscheiden** (30 €/mo separat) — wenn ja: Brassweir-Day + Salzhueter-Boss-Theme als erste Test-Tracks.

---

<a name="xi-phase2"></a>
## XI. PHASE 2 — ENGINE-CRITICAL SOUNDS

> Was bei der ersten Bibel-Version fehlte. Ohne diese SFX klingt das Game
> nicht „komplett" — vor allem **Footsteps fehlen ganz** (Spieler laeuft
> stumm) und Engine-Calls wie `hit`, `damage`, `combo` zeigen aktuell auf
> generische Stock-Sounds.

### XI.1 Footsteps & Movement (15 SFX)

Pro Biome ein **Single-Step**-Sound, den die Engine pro Player-Schritt
schnell loopt. Plus Action-Sounds.

```
footstep_stone        "single boot on dry stone, brief tap, 0.5 sec"
footstep_wood         "single boot on wooden plank, hollow tap, 0.5 sec"
footstep_wet          "single boot on wet stone with shallow water, splash, 0.5 sec"
footstep_sand         "single boot on dry sand, soft crunch, 0.5 sec"
footstep_ash          "single boot on ash with ember crackle, 0.5 sec"
footstep_roots        "single boot on living roots, organic creak, 0.5 sec"
footstep_marble       "single boot on polished marble, clear ring, 0.5 sec"
footstep_glass        "single boot on broken glass shards, tinkle, 0.5 sec"
footstep_void         "single muffled step in unreality, almost silent, 0.5 sec"
footstep_grass        "single boot on damp grass, soft, 0.5 sec"
footstep_metal        "single armored boot on metal grate, ring, 0.5 sec"
move_jump_off         "player jumping off ground with cloth rustle, 0.5 sec"
move_land_soft        "player landing softly on stone, brief impact, 0.6 sec"
move_land_heavy       "player landing heavily with armor clatter, 0.8 sec"
move_water_splash     "player stepping into ankle-deep water, splash, 0.6 sec"
```

### XI.2 Player Combat-Reaktion (12 SFX)

```
damage_light_cloth    "weapon hitting cloth armor, brief slap, 0.5 sec"
damage_med_leather    "weapon hitting leather armor, dull thud, 0.5 sec"
damage_heavy_plate    "weapon ringing on plate armor, metallic, 0.5 sec"
block_shield_metal    "metal shield deflecting weapon, sharp ring, 0.5 sec"
block_shield_wood     "wooden shield absorbing weapon hit, dull thud, 0.5 sec"
parry_ring            "perfect parry with metallic ringing snap, 0.5 sec"
shield_break          "shield cracking and shattering, 0.8 sec"
armor_break           "armor piece breaking off body, 0.7 sec"
crit_universal_v2     "crit hit with metal ring and deep thud, 0.7 sec"
crit_blood            "crit hit with brief blood splatter, 0.6 sec"
miss_air              "weapon cutting empty air, 0.5 sec"
player_death          "human death-gasp ending in long exhale, 2 sec"
```

### XI.3 Status-Effekte Tick-Loops (9 SFX)

```
poison_tick           "single drop of poison hissing into flesh, 0.5 sec"
burning_loop          "low fire crackle on skin, loop 3 sec"
frozen_apply          "flesh freezing solid with crystal crack, 0.7 sec"
frozen_break          "frozen flesh shattering, 0.6 sec"
shock_tick            "single electrical zap on skin, 0.5 sec"
bleed_tick            "single drop of blood hitting stone, 0.5 sec"
heal_tick             "single warm healing pulse, soft, 0.5 sec"
stun_apply            "head-impact with brief disorientation ring, 0.6 sec"
silence_apply         "voice cutting out abruptly with reverse-reverb, 0.6 sec"
```

### XI.4 Doors / Chests / Interactables (14 SFX)

```
door_open_wood        "wooden door creaking open slowly, 1.5 sec"
door_open_metal       "heavy metal door grinding open, 2 sec"
door_close            "door slamming shut with bolt-click, 1 sec"
door_locked           "doorhandle rattling against locked bolt, 0.7 sec"
chest_open            "wooden chest unlatching and lid opening, 1 sec"
chest_locked          "chest lock rattling, 0.5 sec"
chest_unique          "chest opening with magical chime — unique item inside, 1.5 sec"
lever_pull            "iron lever clunking down with mechanical clack, 0.8 sec"
button_press          "stone button being pressed with click, 0.5 sec"
trap_trigger          "mechanical trap snapping with rapid click and whoosh, 0.7 sec"
trap_disarm           "trap mechanism being neutralized with soft click, 0.6 sec"
portal_enter          "stepping through portal with whoosh and reverb, 1.5 sec"
portal_exit           "emerging from portal with breath-out, 1 sec"
secret_wall_reveal    "stone wall sliding aside slowly, 2 sec"
treasure_jingle       "treasure room entered — soft golden chime, 1.5 sec"
```

### XI.5 Crafting / Inventory (16 SFX)

```
craft_hammer          "blacksmith hammer striking metal once, 0.7 sec"
craft_anvil           "hammer-on-anvil ringing strike, 0.8 sec"
gem_engrave           "gemcutter etching memory-stone with soft scrape, 1 sec"
gem_socket            "gem clicking into item socket with magical hum, 0.7 sec"
gem_unsocket          "gem releasing from socket with reverse hum, 0.6 sec"
reroll_orb            "orb shattering with magical reroll energy, 1 sec"
upgrade_success       "magical upgrade success with ascending chime, 1.5 sec"
upgrade_fail          "magical upgrade failing with descending dissonance, 1 sec"
salvage_breakdown     "item being broken apart for materials, brief crunch, 0.7 sec"
equip_weapon          "weapon being drawn from sheath, brief metal slide, 0.6 sec"
equip_armor           "armor piece being strapped on body, 0.8 sec"
unequip               "armor or weapon being removed, leather rustle, 0.5 sec"
drop_item             "item being dropped on stone floor, 0.5 sec"
sell_item             "coin pouch receiving payment, brief jingle, 0.6 sec"
buy_item              "single gold coin tapping on counter, 0.5 sec"
stash_open            "wooden stash chest unlatching, 0.8 sec"
```

### XI.6 Tieferes Menue (10 SFX)

```
menu_back             "soft reverse-tone, 0.5 sec"
menu_select           "subtle selection chime, 0.5 sec"
menu_confirm          "warm confirmation tone, 0.6 sec"
menu_cancel           "soft cancellation tone, 0.5 sec"
menu_error            "low buzz indicating invalid action, 0.5 sec"
settings_apply        "settings being saved with brief positive tone, 0.7 sec"
save_overwrite_warn   "warning chime — soft alarm, 0.7 sec"
character_select      "character portrait highlight with soft hum, 0.6 sec"
pause_resume          "gameplay resuming with brief whoosh, 0.6 sec"
game_over             "low slow descending tone of failure, 2.5 sec"
```

### XI.7 Quest-Feedback (5 SFX)

```
quest_failed          "low somber tone of quest failure, 1 sec"
quest_marker_reach    "soft positive chime as marker reached, 0.7 sec"
quest_choice_hover    "very subtle hover-tone on choice button, 0.5 sec"
quest_choice_select   "warm choice-locked-in tone, 0.7 sec"
quest_lore_unlock     "codex entry unlocked — magical page turn, 1 sec"
```

### XI.8 Engine-Call-Alias-Erweiterung (sf/sounds.py)

Nach Phase-2-Generation muss `SFX_FILE_ALIASES` erweitert werden, damit
die bestehenden Engine-Calls auf die neuen besseren SFX zeigen:

| Engine-Call | Alt | Neu (Phase 2) |
|---|---|---|
| `hit` | generisch | bleibt oder → `damage_light_cloth` |
| `hit_heavy` | generisch | → `damage_heavy_plate` |
| `damage` | none | → `damage_med_leather` |
| `crit` | generisch | → `crit_universal_v2` |
| `death` | generisch | → `player_death` (fuer Player), bleibt fuer Mob-Deaths |
| `dodge` | generisch | bleibt + optional `move_water_splash` per Biome |
| `combo` | generisch | bleibt |
| `aoe_windup` | vorhanden | bleibt |
| `aoe_impact` | vorhanden | bleibt |

**Wichtig:** Engine-Calls wie `cast_fire/lightning/frost/heal/dark` bleiben unveraendert, sie sind in `SFX_FILE_ALIASES` bereits auf Stock-Sounds gemappt und funktionieren.

**Phase-2-Total:** 15 + 12 + 9 + 14 + 16 + 10 + 5 = **81 SFX** zu generieren.
Geschätzt ~0,80 min Audio = ~2.400 char-equiv = **~0,52 EUR**.

---

<a name="xii-phase3"></a>
## XII. PHASE 3 — VOLL-AUDIT (Code-basierte Lückenliste)

> Resultat eines vollständigen Code-Audits aller `sf/*.py` Module.
> Phase 1 + 2 deckten Mob/Boss/Skill/UI/Movement ab — hier sind die
> verbleibenden Lücken aus Decors, Events, Klassen-Specials, Atmosphäre,
> Tutorial, Achievements, Crafting-Aspekte, Currency, Cinematics.

### XII.1 Decor-Interaction (16 SFX)

In `dungeon.py` + `dungeon_events.py` werden viele interaktive Decors
platziert (chest_decor, fountain, cursed_altar, rune_anchor, lore_tablet,
underworld_rift, bookshelf, rune, crystal, sarcophagus, etc.) —
**aktuell ohne Sound** beim Interagieren oder Berühren.

```
chest_decor_open      "ornate dungeon chest creaking open with metal hinge, 1 sec"
fountain_drink        "drinking from stone fountain with soft splash and revitalizing chime, 1 sec"
cursed_altar_touch    "ancient cursed altar humming dangerously, ominous, 1.5 sec"
cursed_altar_blessing "altar grants blessing — ascending warm tone, 1.2 sec"
cursed_altar_curse    "altar punishes — descending dark tone, 1.2 sec"
rune_anchor_activate  "magical rune circle lighting up with arcane hum, 1.2 sec"
lore_tablet_read      "ancient stone tablet whispering forgotten words, 1.5 sec"
underworld_rift_enter "stepping into reality-tear with reverse-time whoosh, 1.5 sec"
bookshelf_search      "leather-bound book pages flipping rapidly, 0.8 sec"
rune_inscribe         "carving rune into stone with chisel, 0.7 sec"
crystal_resonance     "crystal cluster humming with magical resonance, 1 sec"
sarcophagus_open      "stone sarcophagus lid grinding open, deep, 2 sec"
barrel_break          "wooden barrel breaking apart, 0.7 sec"
pier_post_creak       "wet pier wooden post creaking under weight, 1 sec"
fishing_net_lift      "fishing net being lifted from water with drips, 1 sec"
anvil_touch           "blacksmith anvil ringing once when touched, 0.5 sec"
```

### XII.2 Trap-Trigger-Sounds (8 SFX)

In `dungeon_gen.py` gibt es 4 Trap-Types (`spike`, `fire`, `arrow`,
`plate`) — alle ohne individuelle Sounds.

```
trap_spike_shoot      "metal spikes shooting up from floor with sharp clang, 0.5 sec"
trap_spike_retract    "spikes retracting back into floor, 0.6 sec"
trap_fire_burst       "flame jet bursting from floor tile with whoosh, 0.8 sec"
trap_arrow_volley     "multiple arrows firing from wall with whistle, 0.7 sec"
trap_plate_click      "pressure plate clicking under weight, 0.4 sec"
trap_pendulum_swing   "large pendulum blade swinging through air, 1 sec"
trap_dart             "single dart firing from wall with thwip, 0.5 sec"
trap_acid_spray       "acid being sprayed from ceiling with hiss, 0.8 sec"
```

### XII.3 Weather-Ambient-Loops pro Biome (7 SFX)

`weather.py` definiert 7 Wetter-Typen (dust/snow/ash/pollen/sand/spore/
stardust) — alle ohne Ambient-Loop. Diese sollen **leise** im Hintergrund
laufen pro Biome.

```
weather_crypt_dust    "stone dust falling and settling in old crypt, very quiet loop 8 sec"
weather_frost_snow    "soft snowfall on ancient ruins, loop 8 sec"
weather_lava_ash      "ash falling like snow with distant ember crackle, loop 8 sec"
weather_town_pollen   "warm village ambient with pollen drift, loop 8 sec"
weather_desert_sand   "wind whipping fine sand across stone, loop 8 sec"
weather_swamp_spore   "wet swamp with bubbling spores and distant frog, loop 8 sec"
weather_astral_dust   "ethereal cosmic dust with subtle chimes, loop 8 sec"
```

### XII.4 Klassen-Spezifische Specials (12 SFX)

Klassen haben Voice-Lines aber kaum eigene Skill-SFX. Die wichtigsten
klassen-defining Sounds:

```
druid_shapeshift_bear     "human bones cracking and reshaping into bear form with roar, 1.5 sec"
druid_shapeshift_wolf     "rapid morph into wolf with howl, 1.5 sec"
druid_shapeshift_wyvern   "wings unfolding with leathery snap and screech, 1.5 sec"
druid_return_human        "shapeshifting back to human with sigh, 1.2 sec"
witch_skeleton_summon     "bones rising from ground and assembling, 1.5 sec"
witch_skeleton_dismiss    "skeleton collapsing back to bones, 1 sec"
sorceress_funken_cackle   "manic laugh with electric crackles, 1.5 sec"
monk_atem_disziplin       "three deep controlled breaths of focus, 2 sec"
mercenary_reload_click    "crossbow reload with chain clinks and lock-click, 1.2 sec"
huntress_moon_bind        "lunar resonance — silver high chime, 1 sec"
ranger_seed_pod_burst     "seed pod exploding with leafy debris, 0.7 sec"
warrior_battle_cry        "deep battle cry — disciplined warrior shout, 1.2 sec"
```

### XII.5 Currency / Pickup-Variationen (10 SFX)

`pickup_gold` ist da. Aber Mahnmal-Marken, Uncut Shards, Orbs — alle
sollen sich anders anfühlen.

```
pickup_marke_low      "small Mahnmal-tag tinkling on chain, 0.5 sec"
pickup_marke_high     "heavier Mahnmal-medallion with deep ring, 0.7 sec"
pickup_uncut_shard    "raw memory-crystal humming softly, 0.6 sec"
pickup_orb_regret     "orb of regret pulsing with magical energy, 0.7 sec"
pickup_atlas_stone    "atlas-stone crackling with multi-world resonance, 0.9 sec"
pickup_potion         "glass potion bottle being picked up, 0.5 sec"
pickup_scroll         "rolled parchment being grabbed, 0.5 sec"
pickup_key            "iron key clinking, 0.5 sec"
pickup_quest_item     "quest item glowing with significance, 0.8 sec"
pickup_aithein_frag   "fragment of Aithein's breath — ethereal, 1 sec"
```

### XII.6 Dungeon-Events (8 SFX)

`dungeon_events.py` triggert mehrere Events generisch via `boss_intro`
und `roar` — verdienen eigene Sounds:

```
event_rift_warning        "reality cracking with cosmic groan, 2 sec"
event_ambush_warning      "shadowy figures rising from darkness with rustle, 1.5 sec"
event_lore_echo           "ghostly voice fragment from the past, 1.5 sec"
event_treasure_discover   "discovery chime — soft golden tone, 1.2 sec"
event_secret_room         "hidden passage discovered — subtle revelation, 1.5 sec"
event_dungeon_clear       "last enemy down — dungeon-clear ambient swell, 3 sec"
event_new_area            "new area entered — atmospheric transition, 2.5 sec"
event_quest_giver_appear  "ethereal arrival chime — quest NPC appearing, 1.2 sec"
```

### XII.7 Boss-Special-Attacks (10 SFX)

Generic `cast_lightning` wird in `boss_encounter.py` für ALLE Bosse als
Special-Attack-Sound genutzt. Pro Special-Type ein eigener Sound:

```
boss_special_charge       "boss charging massive attack with rising tension, 2 sec"
boss_special_release      "boss releasing channeled attack with shockwave, 1.5 sec"
boss_stomp                "boss stomping ground with massive impact and shake, 1 sec"
boss_beam                 "boss firing concentrated beam attack, 2 sec"
boss_aoe_telegraph        "boss AoE warning indicator pulse, 1.5 sec"
boss_summon_adds          "boss summoning minions with arcane gesture, 1.5 sec"
boss_teleport             "boss teleporting away with whoosh, 0.7 sec"
boss_rage_trigger         "boss entering rage state with roar, 1.5 sec"
boss_heal_self            "boss restoring health with dark hum, 1.2 sec"
boss_shield_break         "boss shield finally breaking with crack, 1 sec"
```

### XII.8 Flask & Consumables (6 SFX)

`flask_use` wird via `play_with_fallback` aufgerufen aber existiert nicht.

```
flask_use                 "glass flask uncorked and contents gulped, 0.7 sec"
flask_health_glow         "healing potion taking effect with warm pulse, 0.8 sec"
flask_mana_glow           "mana potion taking effect with blue shimmer, 0.8 sec"
flask_dud                 "flask is empty — disappointed click, 0.4 sec"
food_eat                  "eating bread/cheese with chew sounds, 0.8 sec"
scroll_read               "reading magical scroll with arcane whisper, 1 sec"
```

### XII.9 Player Voice-Layer auf Combat (6 SFX)

Aktuell hat Player nur Class-spezifische Voice-Lines via voice_registry.
Was fehlt: ad-hoc Combat-Layer wie Grunt, Hurt, Effort.

```
player_grunt_light        "soft male/female grunt of effort, 0.4 sec"
player_grunt_heavy        "heavy strained grunt from big swing, 0.6 sec"
player_hurt_low_hp        "pained gasp at low HP, 0.6 sec"
player_dodge_breath       "sharp inhale during dodge, 0.3 sec"
player_dash_breath        "rapid exhale during dash, 0.4 sec"
player_revive             "gasping breath of revival, 1 sec"
```

### XII.10 Achievement & Progression (6 SFX)

`achievements.py` triggert keinen Sound aktuell.

```
achievement_unlock        "ceremonial chime of achievement unlock, 1.2 sec"
ascendancy_unlock         "deep gong of ascendancy class unlock, 2 sec"
codex_entry_unlocked      "magical page-turn with reveal chime, 1 sec"
faction_rep_milestone     "faction reputation milestone — warm acknowledgement, 1 sec"
title_earned              "honorific title earned — single deep gong, 1.5 sec"
mastery_node_unlock       "skill-tree mastery node activating with shimmer, 0.8 sec"
```

### XII.11 Aspekt-Engraving (Crafting-Erweiterung, 7 SFX)

Otreth-Gemcutter kann Aspekte einbrennen — pro Aspekt eigener Sound.

```
engrave_kharn       "iron resonance — Form-Aspekt being inscribed, 1.5 sec"
engrave_nheyra      "ticking-reversing — Zeit-Aspekt being inscribed, 1.5 sec"
engrave_ousen       "mental hum — Geist-Aspekt being inscribed, 1.5 sec"
engrave_valsa       "fire crackle — Wille-Aspekt being inscribed, 1.5 sec"
engrave_imnesh      "whispered foreign syllable — Sprache-Aspekt being inscribed, 1.5 sec"
engrave_shulavh     "organic creak — Bindung-Aspekt being inscribed, 1.5 sec"
engrave_vergessen   "world-inhale — Vergessens-Aspekt being inscribed, 1.5 sec"
```

### XII.12 Pakt-Aktivierung (7 SFX)

Wenn der Spieler bei Mahnmal-Schrein einen Aspekt-Pakt wählt — pro
Aspekt eigener Activation-Sound (anders als Engrave).

```
pakt_kharn_active       "Kharn-pact buff activating — iron-form pulse, 1 sec"
pakt_nheyra_active      "Nheyra-pact buff activating — time-distorted pulse, 1 sec"
pakt_ousen_active       "Ousen-pact buff activating — mental clarity wave, 1 sec"
pakt_valsa_active       "Valsa-pact buff activating — fire-aura pulse, 1 sec"
pakt_imnesh_active      "Im-Nesh-pact buff activating — chaotic syllable pulse, 1 sec"
pakt_shulavh_active     "Shulavh-pact buff activating — root-bind pulse, 1 sec"
pakt_vergessen_active   "Vergessens-pact buff activating — silence-implosion pulse, 1 sec"
```

### XII.13 Day/Night & Time (4 SFX)

`weather.day_night_ambient` rotiert Lichtfarbe — aber kein Audio-Cue.

```
dawn_chime          "morning chime — birds and warm light fading in, 3 sec"
dusk_chime          "evening chime — distant bell and cool light, 3 sec"
midnight_bell       "ancient tower bell tolling midnight 12 times, 8 sec"
noon_silence        "high noon — sudden silence of midday sun, 2 sec"
```

### XII.14 Shop & Inventory Detail (10 SFX)

Vendor, Stash, Inventory haben aktuell nur generisches Click.

```
shop_open               "vendor stall opening with cloth rustle, 0.8 sec"
shop_close              "vendor stall closing, 0.6 sec"
shop_buy_confirm        "purchase confirmed — coin counter click, 0.7 sec"
shop_sell_confirm       "sale confirmed — coin into pouch, 0.7 sec"
shop_no_gold            "vendor scoffing — insufficient funds, 0.6 sec"
shop_restock_notify     "vendor inventory refreshed — gentle chime, 0.8 sec"
inv_drag_pickup         "item being lifted from inventory slot, 0.3 sec"
inv_drag_drop_valid     "item dropping into valid slot with click, 0.4 sec"
inv_drag_drop_invalid   "item refused — soft buzz, 0.4 sec"
inv_sort                "inventory sorting — multiple items shuffling briefly, 0.7 sec"
```

### XII.15 Tutorial & Hints (5 SFX)

```
tutorial_arrow_appear   "tutorial hint appearing — soft attention chime, 0.6 sec"
tutorial_arrow_dismiss  "tutorial hint dismissed — subtle fade, 0.4 sec"
tutorial_step_done      "tutorial step completed — positive chime, 0.7 sec"
hint_popup              "in-game hint appearing — soft notification, 0.5 sec"
ping_objective          "player marked objective — pulsing ping, 0.7 sec"
```

### XII.16 Save / Load / Hardcore (5 SFX)

```
save_quick              "quick save chime — brief positive tone, 0.6 sec"
load_game               "save game loading — magical refresh, 1.5 sec"
autosave_subtle         "very quiet autosave acknowledgement, 0.4 sec"
hardcore_death          "dramatic hardcore character death — single tragic gong, 4 sec"
memorial_inscribe       "name being chiseled into memorial stone, 2 sec"
```

### XII.17 Atmospheric Long-Tones (6 SFX)

Spezielle dramatische Stinger für seltene Momente — atmospärische
Highlights die das Game „magisch" wirken lassen.

```
atmos_revelation        "moment of revelation — slow rising tone with deep gong, 4 sec"
atmos_dread             "creeping dread — slow descent into low rumble, 4 sec"
atmos_hope              "hope rising — slow ascending warm chord, 4 sec"
atmos_loss              "loss & melancholy — single sustained low note, 5 sec"
atmos_wonder            "moment of wonder — ethereal harp glissando, 3 sec"
atmos_silence_break     "long silence breaking with single dramatic note, 3 sec"
```

### XII.18 Phase-3-Summary

| Sub-Sektion | Anzahl | Use-Case |
|---|---|---|
| XII.1 Decor-Interaction | 16 | Kisten, Brunnen, Altäre, Tafeln |
| XII.2 Trap-Trigger | 8 | Spike/Fire/Arrow/Plate/Pendulum |
| XII.3 Weather-Loops | 7 | Pro Biome ein Ambient-Loop |
| XII.4 Klassen-Specials | 12 | Shapeshift, Summon, Cackle, etc. |
| XII.5 Currency-Pickups | 10 | Marken, Shards, Orbs, Aithein-Frags |
| XII.6 Dungeon-Events | 8 | Rift, Ambush, Treasure, Echo |
| XII.7 Boss-Specials | 10 | Charge, Stomp, Beam, Summon |
| XII.8 Flask & Consumables | 6 | Heal-, Mana-Pots, Food, Scrolls |
| XII.9 Player-Voice-Layer | 6 | Grunt, Hurt, Effort, Revive |
| XII.10 Achievements | 6 | Unlock, Ascendancy, Codex, Faction |
| XII.11 Aspekt-Engraving | 7 | Pro 7 Aspekte |
| XII.12 Pakt-Activation | 7 | Pro 7 Aspekte Buff-Activation |
| XII.13 Day/Night | 4 | Dawn, Dusk, Midnight, Noon |
| XII.14 Shop/Inventory | 10 | Buy, Sell, Drag, Sort |
| XII.15 Tutorial | 5 | Hints, Arrows, Objectives |
| XII.16 Save/Load/Hardcore | 5 | Quicksave, Hardcore-Death |
| XII.17 Atmospheric | 6 | Revelation, Dread, Hope |
| **PHASE 3 TOTAL** | **133 SFX** | |

Geschätzte Audio-Dauer: ~150 s = ca **1,65 €** ElevenLabs.

---

## CODE-AUDIT — VOLLSTÄNDIGER STATUS

| Bereich | Phase 1 | Phase 2 | Phase 3 | Status |
|---|---|---|---|---|
| Mob-Sounds (30 Mobs) | ✅ 69 | — | — | ✅ |
| Boss-Sounds (15 Bosses) | ✅ 37 | — | — | ✅ |
| Skills (7 Aspekte) | ✅ 32 | — | — | ✅ |
| Cinematic-Stinger | ✅ 27 | — | — | ✅ |
| Lore-Mahnmal/Pakt | ✅ 15 | — | — | ✅ |
| Combat-Klassen | ✅ 20 | — | — | ✅ |
| UI-Generic | ✅ 27 | — | — | ✅ |
| Footsteps | — | ✅ 15 | — | ✅ |
| Player-Combat-Reaktion | — | ✅ 8 | — | ✅ |
| Status-Effekte | — | ✅ 9 | — | ✅ |
| Doors/Chests | — | ✅ 15 | — | ✅ |
| Crafting-Basic | — | ✅ 16 | — | ✅ |
| Menu | — | ✅ 10 | — | ✅ |
| Quest-Feedback | — | ✅ 5 | — | ✅ |
| **Decor-Interaction** | — | — | ❌ 16 | nötig |
| **Trap-Trigger** | — | — | ❌ 8 | nötig |
| **Weather-Loops** | — | — | ❌ 7 | nice-to-have |
| **Klassen-Specials** | — | — | ❌ 12 | nötig |
| **Currency-Variationen** | — | — | ❌ 10 | nötig |
| **Dungeon-Events** | — | — | ❌ 8 | nötig |
| **Boss-Specials** | — | — | ❌ 10 | nötig |
| **Flask & Consumables** | — | — | ❌ 6 | nötig |
| **Player-Voice-Layer** | — | — | ❌ 6 | nice |
| **Achievements** | — | — | ❌ 6 | nötig |
| **Aspekt-Engraving** | — | — | ❌ 7 | später |
| **Pakt-Activation** | — | — | ❌ 7 | später |
| **Day/Night** | — | — | ❌ 4 | nice |
| **Shop/Inventory** | — | — | ❌ 10 | nötig |
| **Tutorial** | — | — | ❌ 5 | nice |
| **Save/Load** | — | — | ❌ 5 | nice |
| **Atmospheric** | — | — | ❌ 6 | nice |

**Audio bisher:** 532 KI-Files (227 Voice + 305 SFX)
**Phase-3-Add:** 133 SFX
**Vollausbau-Target:** 665 KI-Files

---

## KOSTEN-GESAMT-SCHAETZUNG

| Block | Aufwand |
|---|---|
| Akt-1-Pass (SFX) | ~9 € |
| Akt-2 bis 7 (SFX) | ~33 € |
| Cinematic + Lore (SFX) | ~11 € |
| **SFX-Subtotal (ElevenLabs)** | **~53 €** (einmalig, deckt 250+ SFX) |
| Music (Suno Pro) | 30 €/mo × 2 = **60 €** für volle Music-Pipeline |
| Ambience (Stable Audio Free) | **0 €** |
| **GESAMT für komplettes velgrad-spezifisches Audio** | **~115 €** |

Für ein Spiel dieser Tiefe ist das exzellent — kommerzielles SFX-Sammlung-Bundle (Soundly, AAA-Library) kostet >300 € und ist immer noch generisch.
