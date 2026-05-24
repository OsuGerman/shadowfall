# VELGRAD — AUDIO DESIGN BIBEL

> Vollständiges Sound-Design-Skript für jedes Audio-Element im Spiel. Lore-konsistent zu Velgrad. Für Claude Code als Implementation-Auftrag direkt verwendbar.

**Lese-Konvention:** Jeder Sound hat **4 Layer**:
- **WIND-UP** (Telegraph, anticipation) — was VOR der Aktion zu hören ist
- **BODY** (main sound) — die Aktion selbst
- **TAIL** (decay/echo/aftermath) — was nach der Aktion hängenbleibt
- **IMPACT** (collision/landing) — wo es trifft, was es trifft

Plus pro Sound: **FOLEY-REZEPT** = wie der Sound entstehen soll (DIY-Aufnahmen / Library-Search-Terms).

---

## TEIL 0 — VELGRAD SOUND-DNA

### Was klingt nach Velgrad
- **Ancient & melancholisch** — kein moderner, glatter Sound. Alles ist ein wenig *verbraucht*, *vergessen*, *zu lange dagewesen*.
- **Acoustic over electronic** — echtes Cello, echtes Holz, echter Atem. Nur sparsame elektronische Layer für Anomalien.
- **Reverb-Heavy** — alles atmet in einer großen Halle. Velgrad ist ein leerer Raum, in dem Klänge nicht zur Ruhe kommen.
- **Sub-Bass present, but never modern** — kein 808-Drop. Stattdessen tiefes Dröhnen wie aus dem Erdinneren.
- **Stimmen, Chor, Atem** — als Texture. Aber selten Worte.
- **Stille als Instrument** — Pausen sind erlaubt, ja notwendig.

### Was klingt NICHT nach Velgrad (verboten)
- Pop-Drum-Patterns
- Helle, fröhliche Glockenspiel-Themes
- Synth-Trance-Lead-Sounds
- Cartoon-Boings, Cartoon-Whooshes, Comedy-Slide-Whistles
- Über-prozessierte EDM-Drops
- Modernes Smartphone-UI-Tick-Tock
- Generic Hollywood-Trailer-Braams (zu generisch)
- Saubere, glatte, „rein digitale" Klänge

### 5 Core-Sound-Ankerpunkte
1. **Tiefer Cello-Drone in A-Moll** — Klangbett des Spiels.
2. **Ferner Frauen-Chor (gesummte Vokale, kein Text)** — taucht in Atmospheric-Layer auf.
3. **Knirschender Stein/Asche-Foley** — Bodenständigkeit, Substanz.
4. **Atmen / Herzschlag** — Lebenszeichen in einer toten Welt.
5. **Glasiges Klingeln (Crystal-Mallet, sparsam)** — Memento mori, fragile Erinnerung.

---

## TEIL 1 — AUDIO-ARCHITEKTUR (Implementation-Grundlage)

### 1.1 Middleware-Wahl
**Empfehlung:** **FMOD Studio** (Indie kostenlos bis $200k Umsatz) oder **Wwise** (Indie kostenlos bis 2000 Sounds).
- FMOD = einfacher für mittelgroße Teams, gute Studio-UI
- Wwise = mächtiger, AAA-Standard, steile Lernkurve

### 1.2 Bus-Struktur (Mixer-Hierarchie)
```
MASTER
├── SFX
│   ├── PLAYER
│   │   ├── PLAYER_FOOTSTEPS
│   │   ├── PLAYER_COMBAT
│   │   ├── PLAYER_SKILLS
│   │   ├── PLAYER_VOICE (Grunts, Death-Lines)
│   │   └── PLAYER_FOLEY (Cloth, Gear-Rattle)
│   ├── ENEMIES
│   │   ├── ENEMY_FOOTSTEPS
│   │   ├── ENEMY_VOCALS
│   │   ├── ENEMY_ATTACKS
│   │   └── BOSS_DEDICATED (eigener Bus für Boss-Encounter)
│   ├── ENVIRONMENT
│   │   ├── AMBIENCE_BED (loops)
│   │   ├── WEATHER
│   │   └── INTERACTIVE_PROPS (doors, chests, switches)
│   ├── MAGIC_FX (alle Spell-/Skill-Effekte)
│   └── UI
│       ├── UI_NAVIGATION
│       ├── UI_FEEDBACK (level-up, pickup)
│       └── UI_ALERTS (death, boss-spawn)
├── MUSIC
│   ├── MUSIC_AMBIENT (exploration)
│   ├── MUSIC_COMBAT (fight)
│   ├── MUSIC_BOSS (encounter)
│   └── MUSIC_CINEMATIC (cutscenes, death-transitions)
└── DIALOGUE
    └── NPC_VOICE
```

### 1.3 RTPCs (Real-Time Parameter Controls)
Diese Parameter müssen existieren und vom Code aus geschrieben werden:

| RTPC | Range | Beeinflusst |
|---|---|---|
| `player_health_percent` | 0-1 | Music-Tension, Heartbeat-Volume |
| `player_in_combat` | 0/1 | Music-Bus-Crossfade |
| `player_indoors` | 0/1 | Reverb-Send, Wind-Volume |
| `player_underwater` | 0/1 | Low-Pass-Filter auf gesamten Mix |
| `boss_phase` | 0-3 | Music-Stem-Crossfade |
| `environment_type` | enum | Reverb-Preset (cave, hall, outdoor, void) |
| `time_of_day` | 0-1 (Mitternacht zu Mittag) | Ambient-Bed-Crossfade |
| `weather_intensity` | 0-1 | Wind/Regen-Volume |
| `vergessens_proximity` | 0-1 | Audio-Distortion, Whisper-Volume |

### 1.4 Snapshots (Mixer-States)
| Snapshot | Trigger | Effekt |
|---|---|---|
| `DEFAULT` | Standard | Normale Lautstärken |
| `DIALOG` | NPC spricht | Music auf 30%, SFX auf 60% |
| `BOSS_INTRO` | Boss-Spawn-Cinematic | Ambience aus, Music-Build, Boss-Vocals 100% |
| `BOSS_PHASE_2/3` | HP-Schwellen | Music-Layer dazumischen |
| `DEATH_TRANSITION` | Player-Death | Alles auf -20dB, dann Cut |
| `MENU_OPEN` | Inventar/Tree | Music duck 30%, Wind aus |
| `UNDERWATER` | Wasser-Bereich | Lowpass 800Hz auf alles |
| `STILLE_ZONE` (Anomaly) | Vergessens-Nähe | Music wegfaden, alle SFX gedämpft |

### 1.5 3D-Spatial-Audio
- **HRTF Pflicht** (Steam Audio, Microsoft Spatial Sound, oder Wwise Reflect)
- Minimum-Distance: 1m (innerhalb voll), Falloff bis 50m
- Boss-Sounds: erweiterte Range 80m
- Spatial-Reverb auf Environment-spezifischen Bussen

---

## TEIL 2 — PLAYER MOVEMENT

### 2.1 Schritte (Footsteps)
**Wichtig:** Material-Detection unter dem Spieler-Fuß = Raycast nach unten zum Boden-Material-Tag.

Pro Material **mindestens 8 Variationen** (Anti-Repetition). Schuhwerk skaliert mit Klasse (Warrior schwerer als Monk).

#### MATERIAL 2.1.A: STEIN
**Body:** Lederstiefel auf trockenem Stein, leicht hallend (wenn indoors).
**Foley:** Lederabsatz auf altem Marmor, in Treppenhaus aufgenommen.
**Search Terms:** "footstep stone", "boot stone hard", Freesound CC0.

#### MATERIAL 2.1.B: SAND / SALZ (Akt 1 — Salzküste)
**Body:** Knirschende Sandkörner, leicht knusprig.
**Tail:** Sandfall nach jedem Schritt (0.1s).
**Foley:** Stiefel im trockenen Sand + leichte Salz-Knister-Variation.
**Search Terms:** "footstep sand crunch", "salt crystal crush".

#### MATERIAL 2.1.C: ASCHE (Akt 3 — Aschenfelder)
**Body:** Tiefer dumpfer Aufschlag, dann feines Sieben/Knirschen.
**Tail:** Asche staubt auf, wirbelt.
**Foley:** Stiefel in feiner Vulkanasche + leichtes „Husten" der Luft.
**Search Terms:** "footstep ash", "footstep volcanic dust".

#### MATERIAL 2.1.D: WURZEL/HOLZ (Akt 4 — Wurzelgrab)
**Body:** Organisches Knacken, leicht feucht.
**Foley:** Stiefel auf morschem Holz + feucht-organisches Pressen (Pilze treten).
**Search Terms:** "footstep wet wood", "rotten wood crack".

#### MATERIAL 2.1.E: GLAS (Akt 5 — Spiegelstadt)
**Body:** Hohes Klirren bei jedem Schritt, kristallin.
**Tail:** Splitter rieseln, kleine Schwingung.
**Foley:** Glasscherben in flachem Behälter + auf Marmor knirschen.
**Search Terms:** "footstep glass crunch", "broken glass step".

#### MATERIAL 2.1.F: WASSER (überall — Pfützen, Teiche)
**Body:** Klatsch, dann Wasserverdrängung.
**Tail:** Tropfen für 0.3s.
**Foley:** Stiefel in flachem Wasserbecken (Studio-Aufnahme).
**Search Terms:** "footstep water splash", "boot puddle".

#### MATERIAL 2.1.G: METALL (Tribunal-Festung, Konstrukte-Arena)
**Body:** Heller, klingender Aufschlag mit kurzer Resonanz.
**Foley:** Stiefel auf Stahlgitter / Blechplatte.
**Search Terms:** "footstep metal grate", "boot steel plate".

#### MATERIAL 2.1.H: LEERE (Anomalie-Zonen, Hohlwunde)
**Body:** **Kein Sound.** Aber der Spieler fühlt die Abwesenheit (Sub-Bass-Drop von -3dB).
**Tail:** Statt Tail: ein winziges Whisper-Sample, manchmal.
**Foley:** Side-Chain-Effect, der Footstep-Audio cuttet.

### 2.2 Sprint / Dodge / Spezial-Movements

#### SPRINT
**Body:** Schnellere Schritt-Frequenz + Stoff-Whoosh (Cape rauscht).
**Foley:** Aufgenommen aufgenommene Stiefel-Steps beschleunigen + Stoff-Sample (Mantel-Rauschen).
**RTPC-Modulation:** `player_breathing` steigt — atmen wird hörbarer.

#### DODGE-ROLL
**Wind-Up:** Ein knapper Stoff-Whoosh (cape flair).
**Body:** Body-Aufprall auf Boden + Rolle (Pelz/Rüstung schleifend).
**Tail:** Aufstehen mit kurzem Aufstemmen-Grunt.
**Foley:** Mensch rollt durch Decke + Lederrüstung knarrt.
**Class-Variation:** Monk = leiser (lautlos sogar bei „Bambus des Schweigens"-Item), Warrior = klangvoller (Metall klirrt).

#### JUMP (falls vorhanden)
**Wind-Up:** Ansatz-Grunt.
**Body:** Whoosh in Luft.
**Impact:** Material-spezifischer Landschritt + Knie-Kreis.

#### KLETTERN (Felsen, Leitern)
**Body:** Hand-an-Stein/Holz-Reibung, mit Atem-Pausen.

#### SCHWIMMEN
**Body:** Wasserarme-Bewegung, leise Atemzüge zwischen Strokes.
**RTPC:** `player_underwater = 1` aktiviert Lowpass auf Mix.

### 2.3 Player-Voice (Movement-Begleitung)
- **Heavy Breath**, wenn Stamina niedrig (Loop, RTPC-gesteuert)
- **Pain Grunt**, bei Schaden (siehe Voice-Lines-Doc)
- **Climbing Grunt**, beim Klettern (Klasse-spezifisch)

### 2.4 Foley-Layer (Equipment-Rasseln)
Pro Klasse anders! Pflicht-Layer beim Laufen:
- **Warrior:** Schwere Metallplatten klirren, Kette rasselt.
- **Monk:** Stoff raschelt, Holzstab leise an Gürtel.
- **Sorceress:** Robe rauscht, kleine Glas-Ampullen (Tränke) klingeln.
- **Witch:** Knochenfetische klacken aneinander.
- **Ranger:** Köcher-Pfeile klappern, Bogen-Sehnen zittern bei Bewegung.
- **Mercenary:** Crossbow-Bolts klacken, Lederholster knarzen.
- **Huntress:** Speer-an-Rücken, Ledergürtel.
- **Druid:** Tier-Fetische rascheln, in Tierform = Pranken-Pads + Atem.

---

## TEIL 3 — COMBAT — BASIC ATTACKS PRO WAFFE

Jeder Basic-Attack hat den 4-Layer-Aufbau. Hier die Standards pro Waffentyp.

### 3.1 MACE (Warrior)
**Wind-Up:** Schwere Holz/Stahl-Reibung, kurzer Atem-Grunt (0.3s).
**Body:** Massive Whoosh durch Luft (tiefe Frequenz).
**Tail:** Vibration nach Schwung, Stahl klingelt aus.
**Impact:**
- **Auf Fleisch:** Tiefer Bone-Crunch + Squelch.
- **Auf Stein:** Funken-Schwirren + heller Klang.
- **Auf Metall:** Hoher Klingelschlag.
**Foley:** Vorschlaghammer durch Luft + Holzklotz auf Fleisch (im Filmstudio) + Stahlring auf Amboss.

### 3.2 SWORD (One-Hand)
**Wind-Up:** Klinge wird gezogen, kurzes Singen.
**Body:** Saubere Klinge durch Luft, „shing".
**Tail:** Klinge schwingt aus, leichtes Vibrieren.
**Impact:**
- **Schnitt durch Fleisch:** Wet-slice + kurzer Bone-Crack.
- **Block auf Klinge:** Heller Stahl-auf-Stahl-Schlag.
- **Block auf Schild:** Dumpfer Thunk.
**Foley:** Schwert-Library + Wassermelone-aufschneiden + Stahlplatte-Schlag.

### 3.3 DAGGER
**Wind-Up:** Schneller Mini-Atem.
**Body:** Schnelles, hohes Whoosh.
**Tail:** Quick Cut, kein Nachklang.
**Impact:** Schneller Stich, wet-puncture, sehr kurz.
**Foley:** Gemüsemesser durch Luft + Sellerie-Stich + Tomate.

### 3.4 BOW
**Wind-Up:** Sehne wird gespannt (langsam, anstrengend), Holz knarzt.
**Body:** Sehnen-Twang, hoch und scharf.
**Tail:** Pfeilflug durch Luft (Fffffft).
**Impact:**
- **Fleisch:** Wet-thunk, Pfeil bohrt sich ein.
- **Holz:** Dumpfes Holz-Thunk.
- **Stein:** Pfeil zerbricht (Wood-Crack + Splitter).
**Foley:** Echter Bogen (in Sportverein) + Pfeil-in-Schaumstoff + Holz-Brecheffekt.

### 3.5 CROSSBOW
**Wind-Up:** Mechanisches Aufladen (Ratschen-Klang) — automatisch oder bei Reload-Skill.
**Body:** Trockener, lauter „THUNK!" (Schussabgabe) — keine Sehne, sondern Mechanik.
**Tail:** Bolt-Flug, leiser als Bogen.
**Impact:** Härter als Bogen — Penetration, manchmal Durchschlag.
**Foley:** Ratschen-Mechanik + Industrial-Schlag (Hammerwerk-Sample) + Pfeil-Impact.

### 3.6 SPEAR (Huntress)
**Wind-Up:** Speerschaft zittert leicht beim Anlegen.
**Body:** Schnelle Stoß-Whoosh, sehr direktional.
**Tail:** Bei Wurf: pfeifend durch Luft, geringer als Pfeil aber tiefer.
**Impact:** Tiefer Stich, oft Knochen-Brech-Layer dabei.
**Foley:** Besenstiel durch Luft + Steakmesser-Stich + Trockenholz-Bruch.

### 3.7 QUARTERSTAFF (Monk)
**Wind-Up:** **Stille.** Monks sind leise (lore-konsistent).
**Body:** Bambus-Schlag, hohl klingend.
**Tail:** Resonanz im Bambus.
**Impact:** Trommel-artiger Aufprall auf Körper, sehr perkussiv.
**Foley:** Echter Bambus-Stab (Holzladen) + Trommel-Sample + Mensch-Atem.

### 3.8 WAND (Sorceress)
**Wind-Up:** Funken-Knistern, kurzer Cast-Beginn.
**Body:** Element-spezifisch (siehe Teil 4 — Skill-Casts).
**Tail:** Magic-Decay.
**Impact:** Element-Spezifisch.

### 3.9 SCEPTRE
**Wind-Up:** Tiefes Resonanz-Brummen, da das Sceptre Spirit-Channel ist.
**Body:** Air-Push mit metallischem Klang.
**Impact:** Stumpfer Hit + Magic-Layer.

### 3.10 STAFF (Two-Hand)
**Wind-Up:** Tiefes Aufladen, Bass-Whomp.
**Body:** Großer Spell-Cast, je nach Element.
**Impact:** Großflächiger Hit + Echo.

### 3.11 TALISMAN (Druid — Shapeshift!)
**Wind-Up vor Shapeshift:** Tiefes Atmen, fast schon Brüllen.
**Body — Bär-Form:** Knochen-Knacken (Skeleton-Reshape), Wachsen-Stretch, dann Bärenbrüllen.
**Body — Wolf-Form:** Schnelleres Morphen, Haar-Rascheln, Heulen.
**Body — Wyvern-Form:** Flügel entfalten, Hals-Knacken, Drachen-Krächzen.
**Tail:** 1s Atem-Stabilisierung in neuer Form.
**Foley:** Aus „The Wolfman" / „Howl" Library, plus Knochen-Knacken (Sellerie-Stiele) + Tier-Vocals.

---

## TEIL 4 — SKILL-CASTS (PRO ELEMENT)

Jeder Skill folgt diesem Schema, modifiziert durch Element.

### 4.1 FIRE (Valsa-Element, brennende Magie)
**Wind-Up:** Funken-Knistern aus Hand/Waffe (0.5-1.2s). Kann mit Choir-Pad unterlegt sein.
**Body:** Tiefes Whoom + animiertes Flammen-Crackle (Loop für Channeling-Skills).
**Tail:** Sizzle-Decay, glühende Reste.
**Impact:** Brutzeln auf getroffenem Material + Ignite-Layer (für DoT-Tick: leichtes Sizzeln am Feind alle 0.5s).
**Foley:** Lagerfeuer-Library + Backflammwerfer + Schweißerflamme.
**Lore-Note:** Bei manchen Fire-Skills: ein leises *Frauenflüstern* von Valsa unterhalb (subtil, atmospheric).

### 4.2 COLD (Nheyra/Frost-Element)
**Wind-Up:** Hohes Kristallisier-Singen, Glas-Schimmern (0.6-1.5s).
**Body:** Knirschen wie Eis sich bildet + Wind-Whistle.
**Tail:** Frost-Decay, Eis-Tinkle.
**Impact:** Frost-Crack, dann Eis-Splittern. Bei Freeze: Spieler-Hörbares „Knirschen" am Feind, dann komplette Stille.
**Shatter-Sound:** Glas-Bruch-Library × 3 Layer + tiefer Crash für Sub-Bass.
**Foley:** Glas-Wein-Glas zerspringen + Frost in Kühlschrank + Synth-Bell sehr cold-gepitched.

### 4.3 LIGHTNING (Ousen-Element, kosmisch)
**Wind-Up:** Tesla-Funkenflug, knisterndes Aufladen (0.4-1.0s).
**Body:** Cracker-Schlag — KEINE klassische Donner-Bombe, sondern *trockener Funkenschlag* mit Hochfrequenz-Sizzle.
**Tail:** Statisches Knistern, das langsam abklingt.
**Impact:** Bei Treffer: Body-Spasm-Audio (Feind zuckt), Ozon-Layer (kann nicht „gehört" werden, aber psychologisch fühlbar via High-Frequency-Hiss).
**Foley:** Tesla-Spule + Hochspannungstrafo + Mikrofon-Static + Synth-Crackle.
**Lore-Note:** Lightning klingt in Velgrad **nie wie Disney-Magic**. Eher industriell, gefährlich, fast wissenschaftlich.

### 4.4 PHYSICAL / SLAM (Kharn-Element)
**Wind-Up:** Tiefes Bass-Aufladen, Erdrumpeln.
**Body:** Massiver Aufschlag mit Erdbeben-Sub (40Hz).
**Tail:** Erdrutsch-Klang, Staub setzt sich.
**Impact:** Knochen-Crack + Erd-Verdrängung.
**Foley:** Schwere Holzkiste auf Erde + Granitblock + Granat-Explosion (sub only) + Vorschlaghammer.

### 4.5 CHAOS / POISON (Im-Nesh-Element)
**Wind-Up:** Nasses Bubbeln, leises Flüstern aus mehreren Stimmen.
**Body:** Verschleimt, säurig, niemals sauber. Verschwommene Frequenzen.
**Tail:** Drip-Drip-Drop für 3-5 Sekunden.
**Impact:** Hisseln auf Haut, Säure-Schmelze-Layer, DoT-Tick alle 1s ein leises *„ssss"*.
**Foley:** Sauerteig-Bubbeln + Säure-auf-Metall (Studio-Sample) + Stimme rückwärts und gepitched.
**Lore-Note:** Chaos-Spells klingen *verdorben*, nicht „cool". Spieler soll sie ungern hören.

### 4.6 VOID / VERGESSEN (Siebter Aspekt)
**Wind-Up:** **Audio wird stiller.** Anderer Sound im Raum dimmt um -6dB für 0.5s.
**Body:** Sehr tiefes Sub-Drone, fast subliminal. Plus Reverse-Whisper-Layer.
**Tail:** Audio kommt langsam zurück, aber leicht falsch gemischt.
**Impact:** Spieler hört einen einzelnen Herzschlag — den eigenen — und einen seltsamen Schwindel-Sound (binaural beat).
**Foley:** Side-Chain-Compressor auf Mix + tiefe Klangschale + Stimme rückwärts.
**Lore-Note:** Void-Skills sind selten, mythisch, unangenehm. Spieler soll fühlen, dass er etwas tut, das er nicht tun sollte.

### 4.7 BONE / SUMMON (Witch / Necromancy)
**Wind-Up:** Knochen-Knacken aus dem Boden, leises Flüstern (Vossharil-Layer).
**Body:** Mehrere Knochen-Klacks, Schädel-Klacken.
**Tail:** Skelett richtet sich auf (Knirschen) + leises Wimmern.
**Foley:** Trockene Stöcke brechen + Kürbis-Schnitzen (Hohlraum) + alte Frau-Atem.

### 4.8 NATURE / SAATTRÄGER (Druid, Ranger)
**Wind-Up:** Holz knarzt, Blätter rascheln.
**Body:** Wurzeln brechen aus Boden, organisches Streckung.
**Tail:** Vogelruf-Echo, Wind in Blättern.
**Foley:** Echte Wald-Aufnahmen + Selleriestange-Brechen + Pilz-Pressen.

### 4.9 SPIRIT / AURA (Persistent Buffs)
**Body:** Subtiler Loop, leise. Ein Drone in der Tonlage des Aspekts (siehe Boss-Doc):
  - Kharn-Aura: tiefe Cello-Bordun
  - Ousen-Aura: hoher Singenton im Hintergrund
  - Valsa-Aura: ferner Choir-„Aaaaah"
  - Shulavh-Aura: warmes Pulsieren wie Herzschlag
**Tail:** Beim Deaktivieren: 1s Fade-Out mit kurzem „Atem"-Effekt.

---

## TEIL 5 — SKILL-FAMILIEN (KONKRETE PRESETS)

Für jeden Skill aus dem Skill-Briefing braucht es einen passenden Sound. Hier die Templates pro Skill-Familie:

### 5.1 Slam-Skills (Boneshatter, Earthquake, Sunder, Earthshatter)
- Variation von Teil 4.4 (Physical).
- **Earthquake:** Zusätzlich: Aftershock-Audio 2s nach Slam (kleinere Schläge).
- **Sunder:** Welle-Audio, die sich ausbreitet (Doppler).
- **Earthshatter:** Spike-Steigen aus Boden (Knirsch-Sequenz) vor Detonation.

### 5.2 Channeling-Skills (Charged Staff, Resonating Shield, Perfect Strike)
- **Loop-Audio mit Build-Up-Layer** über 1-3 Sekunden.
- Wenn Maximum erreicht: Audio-Höhepunkt (Pitch-Up oder Layer-Add).
- Release: Explosiver Burst entsprechend Element.

### 5.3 Projektil-Skills (Spark, Fireball, Frostbolt, Lightning Spear)
- Wind-Up + Body (Cast) + Travel-Loop (während Flug) + Impact.
- Travel-Loop: jeweils Element-spezifisch (Fire = Flammen-Loop, Cold = Whistle, Lightning = Crackle, Phys = Whoosh).

### 5.4 AoE-Skills (Ice Nova, Comet, Volcanic Fissure, Bone Storm)
- **Air-Skill (Comet):** Sky-Wind-Up 2s + Falling-Whistle + Impact-Crater.
- **Ground-Skill (Volcanic Fissure):** Erdriss-Audio + Lava-Eruption-Layer.
- **Nova:** Zentrum-Impact + sich ausbreitender Whoosh.

### 5.5 Summon-Skills (Raise Zombie, Skeletal Warrior)
- Siehe Teil 4.7 (Bone-Cast).
- Plus: Minion-Voice-Loop (passiv-Audio während Existenz, leise atmen/knirschen).

### 5.6 Buff / Herald-Skills
- Aktivierungs-Audio: 1.5s Build-Up + „Lock-In"-Klang.
- Persistent-Loop: siehe Teil 4.9.

### 5.7 Mobility (Leap Slam, Shield Charge, Whirling Assault, Blink, Flicker Strike)
- **Leap Slam:** Sprung-Whoosh + Air-Phase (1s Stille fast) + Slam-Impact.
- **Charge:** Sprint-Audio mit Wind-im-Ohr-Layer.
- **Flicker Strike:** **Audio-Cut für 0.1s** dann an neuer Position Body-Impact (Teleport-Effekt).
- **Blink (Sorceress):** Reverse-Whoosh-In + Forward-Whoosh-Out.

### 5.8 Curses (Despair, Enfeeble, Temporal Chains, Hunters Mark)
- Wind-Up: Sprechen-Audio (gerne in alter Sprache, gemurmelt).
- Body: Curse-Wave (visueller Marker bekommt akustischen Layer, ein leises Pulsieren am gecursteten Feind).
- Tail: Wave-Reverb.

### 5.9 Warcries (Infernal Cry, Seismic Cry, Rallying Cry)
- Klassen-spezifischer Schrei (siehe Voice-Lines-Doc).
- Plus AoE-Layer (Druck-Welle).
- Element-spezifisch wenn relevant.

---

## TEIL 6 — UI-SOUNDS

**Style-Anker:** UI in Velgrad ist **diegetisch** — klingt wie alte Mechanik, nicht wie Smartphone. Keine glatten Pings. Stattdessen: Pergament, alte Mechanismen, Glas, Knochen.

### 6.1 Navigation (Hover, Click, Page-Turn)
- **Menü-Hover:** Sanftes Papier-Rascheln (0.1s).
- **Menü-Click:** Federkielsturz auf Pergament + leiser Mechanik-Klick.
- **Sub-Menu-Open:** Ein leises Knirschen wie Schwurbel-Tür.
- **Sub-Menu-Close:** Selbiges, rückwärts.
- **Foley:** Echtes Pergament + alte Holzkiste + Schreibmaschine.

### 6.2 Inventar
- **Item-Hover:** Sehr leiser High-End-Ping (1 Frame, fast subliminal).
- **Item-Equip:** Material-spezifisch (Metall klingelt, Stoff raschelt, Holz pocht).
- **Item-Drop in Slot:** Klingelhaft, je nach Item.
- **Item-Discard / Verkaufen:** Pergament reißt + kurzes „Sshh"-Whisper-Sample.

### 6.3 Skill-Tree
- **Node-Hover:** Klassen-spezifischer Mini-Ping (siehe Gameplay-Doc Teil H — Skilltree-Optik).
  - Warrior: Hammer-auf-Amboss (sehr leise).
  - Witch: Knochen-Klack.
  - Sorceress: Glas-Chime.
  - Ranger: Holz-Knarzen.
  - Monk: Pinselstrich auf Papier.
  - Druid: Tier-Atem.
  - Huntress: Speer-Schaft-Vibration.
  - Mercenary: Mechanik-Klick.
- **Node-Allocate:** Klassen-spezifischer Aktivierungs-Sound (siehe Gameplay-Doc Teil H.5).
- **Refund / Respec:** Reverse-Allocate-Audio.
- **Tree-Pan / Zoom:** Sehr leises Air-Whoosh.

### 6.4 Pickup-Sounds
- **Currency-Pickup:** Münzen klingelnd, je nach Wert anderes Sample-Pack.
- **Common-Item:** Generic-Pickup-Klingel.
- **Rare-Item:** Hellerer Klingel + Glas-Anteil.
- **Unique-Item:** Choir-Stinger (kurzes „Aaaah") + Sub-Bass-Drop. Diese Audio-Cue ist wichtig — sie ist die Belohnung.
- **Mythic-Item:** Full-on Choir-Stinger (1.5s) + dramatischer Sub-Bass + Glas-Klingelteppich + minor pause in music.
- **Erinnerungsstein (Gem)-Pickup:** Glas-Tinkle + Energie-„Snap" + ferner Choir.

### 6.5 Notifications & Feedback
- **Level-Up:** **Großer Moment.** 1.5s Layer: Cello-Swell + Choir-Welle + Glas-Klingel. NICHT generisch — Spielerklassen-spezifisch nuanciert.
- **Skill-Slot Unlocked:** Mini-Stinger, klassen-thematisch.
- **Quest-Updated:** Pergament + leiser Glocken-Ping.
- **Quest-Complete:** Längere Variation, mit dezenter Choir-Wave.
- **Map-Discovered (Atlas-Map):** Atmosphere-Hint (Region-spezifisch — Salzwellen für Coastal-Map, Asche-Wind für Aschwunde, etc.).

### 6.6 Death-UI
**(Implementiert in Gameplay-Doc Teil A.)** Audio-Layer kommt aus PostProcess-Stack:
- Damage-Type-spezifischer Full-Screen-Transition-Sound.
- Heartbeat-Slow-Down.
- Wake-Up: Atmen, Stadt-Ambience verzögert einsetzend.

### 6.7 Boss-Spawn / Health-Bar
- **Boss-Health-Bar erscheint:** Tiefer „Bong"-Sound (Tubular Bell, sehr nass mit Reverb) + Music-Stinger.
- **Boss-Phase-Transition:** Sub-Bass-Drop + Music-Layer-Swap (RTPC `boss_phase`).
- **Boss-Death:** Choir-Choke-Off + Music-Resolution (Auflösung in Moll-Tonika).

---

## TEIL 7 — ENVIRONMENT & WETTER

### 7.1 Wind (Universal-Ambient)
Wind ist überall in Velgrad. Aber er ist nie generisch.

#### REGION 7.1.A: Salzküste (Akt 1)
**Body:** Mittlerer Wind mit Salz-Geruch-Andeutung (psychologisch via High-End-Whistle).
**Layer:** Ferne Möwen, Wellenbrechen, fernes Schiffs-Knarren.
**Foley:** Field Recording an Nordsee/Atlantik + Möwen-Library.

#### REGION 7.1.B: Glasgoldene Ruinen (Akt 2)
**Body:** Wind durch Lücken in Ruinen — pfeifend, hohl.
**Layer:** Ferner Glas-Klingel-Ton (subtil!), Echo von Reden aus weiter Distanz (Senator-Phantoms).
**Foley:** Wind durch Holzhütte + Glas-Mobile sehr leise.

#### REGION 7.1.C: Aschenfelder (Akt 3)
**Body:** Trockener, heißer Wind. Asche wirbelt hörbar.
**Layer:** Ferne Schreie der Letzten Legion (sehr leise, am Rande der Wahrnehmung). Manchmal: ein einzelnes „Valsa..." als Whisper.
**Foley:** Saharawind + Glut-Crackle + Whisper-Vocals.

#### REGION 7.1.D: Wurzelgrab (Akt 4)
**Body:** Kein Wind. Stattdessen Atem-Loop — wie eine schlafende Riese.
**Layer:** Wasser-Drip in der Ferne, Wurzel-Knarzen, gelegentlich ein Herzschlag (das Wurzelgrab lebt).
**Foley:** Indoor-Höhle + Atemspur + ferne Trommel.

#### REGION 7.1.E: Spiegelstadt Velharn (Akt 5)
**Body:** Stille mit hohem Tinnitus-Ton (uncanny).
**Layer:** Glas-Mobile-Klingel sehr leise, gelegentlich eine vergangene Senator-Stimme („...und der Senat beschloss..."), Echo aus mehreren Zeiten gleichzeitig.
**Foley:** Glas-Klingel + Reverse-Reverb-Stimmen.

#### REGION 7.1.F: Hohlwunde (Akt 6, Endgame-Nähe)
**Body:** **Negativer Wind.** Audio wird subtil leiser je näher man dem Zentrum kommt.
**Layer:** Reverse-Whisper, sehr tiefer Drone.
**Foley:** Side-Chain auf Mix + Sub-Drone + Reverse-Stimmen.

### 7.2 Regen
- **Light Rain:** Tropfen auf Stein/Stoff/Holz (material-abhängig vom Standort des Players, RTPC-gesteuert).
- **Heavy Rain:** Intensiver, gleichzeitig Donner-Andeutungen in Ferne.
- **Indoor:** Filter über Regen (LowPass auf 2kHz) + Tropfen-auf-Dach-Layer.
**Foley:** Echter Regen + Schauer auf Plane + Trommelfell.

### 7.3 GEWITTER (besonders wichtig — atmosphärisch)
**Drei-Phasen-Modell:**
1. **Anschwellende Spannung:** Wind nimmt zu, Druck steigt (Sub-Bass-Bed schwillt langsam an, RTPC `weather_intensity` → 0.7).
2. **Blitz:** Visueller Flash. **0.5-3 Sekunden später** (entfernungsabhängig) Donner.
3. **Donner:** Tief, rollend, mit langem Tail. Klingt in Velgrad **organisch — fast wie wenn eine Welt seufzt**, nicht wie ein Hollywood-Donner.

**Blitz-Audio (direkt sichtbar):**
- **Wind-Up:** Hochfrequentes Aufladen (statischer Pre-Click).
- **Body:** Crackle + Blitzschlag-Schlag (kurzer Cracker).
- **Tail:** Hallender Donner-Roll, der 4-8 Sekunden dauern kann.

**Variationen pro Region:**
- **Aschenfelder-Gewitter:** Asche regnet statt Wasser, Donner klingt brüllender (Valsa-Echo-Layer).
- **Hohlwunde-Gewitter:** Audio-glitch beim Blitz (Audio cuttet für 1 Frame), Donner kommt rückwärts.
- **Spiegelstadt-Gewitter:** Donner kommt **aus mehreren Richtungen gleichzeitig** (Zeit-Echo-Effekt).

**Foley:** Echte Donner-Aufnahmen + Sub-Bass-Synth + Hochfrequenz-Crackle (Tesla).

### 7.4 Spezielle Wetter
- **Asche-Sturm:** Wind + hörbares Asche-Streuen + reduzierte Sicht-Audio (Mid-Range-Mufflung).
- **Salz-Nebel:** Stille fast, mit einzelnen Wassertropfen, leises Glocken-Klingen (geisterhaft).
- **Vergessens-Welle (mechanik!):** Sehr seltenes Event. **Audio reduziert sich erst, dann fühlt sich ALLES leiser an** (RTPC `vergessens_proximity` → 1). Whisper-Layer, sub-Bass-Drone, dann ein einzelner Klingelton wenn die Welle vorüber ist.

### 7.5 Interaktive Props (Türen, Truhen, Schalter)
- **Holztür auf:** Knarzen, lang, 2-3 Sekunden.
- **Steintür / Tor:** Schweres Mahlen, mit Steinklirren.
- **Eisengitter:** Quietschen + Klang von Metall-Stäben.
- **Truhe öffnen (common):** Holzdeckel knarzt.
- **Truhe öffnen (rare/gold):** Knarzen + Choir-Stinger + Glas-Klingel-Layer.
- **Truhe öffnen (mythic):** Wie rare + längerer Build-Up + Sub-Bass-Drop.
- **Schalter / Hebel:** Mechanisches Knacken + Echo.
- **Tür von innen zugeschlossen (Boss-Lock):** Schwerer Riegel + ferner Donner.

### 7.6 Höhlen-spezifisch
- **Drip-Drip-Loop:** Wasser tropft, 4-8 Sek randomisiert.
- **Distant-Rumble:** Manchmal Erdrumpeln (Kharn-Schnarchen, lore-konsistent!).
- **Bat-Wings:** Selten, in der Höhe.
- **Echo:** Player-Audio bekommt extreme Cave-Reverb-Send.

### 7.7 Stadt / Hub-Audio
- **Brassweir (Akt 1):** Hafen-Geräusche — Möwen, Ruderboot-Knarzen, Salz-Pfützen, leise Volk-Stimmen.
- **Echo-Markt (Akt 2):** Geist-Händler murmeln, Münzen klingeln, Glasgolden-Bewegung.
- **Säulen-von-Helst (Akt 3):** Gemurmelte Gebete der Erblinden, Kerzen-Crackle.
- **Knoten-Markt (Akt 4):** Knochen-Klacken, Vossharil murmelt mit Toten, organische Loops.
- **Drei-Pagoden (Stille Schritte):** Sehr leise, Wind-Glocken (sparsam!), ferne Atem-Übungen.

---

## TEIL 8 — PORTALE & TELEPORT

### 8.1 Standard-Waypoint (Town-Portal)
**Wind-Up:** Energie-Build-Up, 1.5s, hörbar von beiden Seiten (am Spawn-Punkt und am Ziel-Punkt!).
**Body:** Phasing-Whoosh + Choir-Layer (kurzes „Aaaah"), als ob die Welt sich öffnet.
**Tail:** Decay des Portals, 2s.
**Foley:** Reverse-Whoosh + Synth-Pad + Choir-Library.
**Lore-Note:** Portale in Velgrad sind kein klinischer Sci-Fi-Effekt. Sie klingen *spirituell*, **als ob man die Welt um Erlaubnis bittet**.

### 8.2 Boss-Arena-Portal (Türen schließen)
**Body:** Schwerer Riegel + Sub-Bass-Boom + Lock-In-Klang.
**Tail:** Stille — kurz die Music wechseln (Snapshot `BOSS_INTRO`).

### 8.3 Stunden-Spiegel-Teleport (Velharn-Spezialfeature)
**Wind-Up:** Glas-Klingel-Crescendo, 2s.
**Body:** Audio-Reverse-Effect auf allem für 0.5s, dann Phase-In im Ziel-Bereich.
**Tail:** Glas-Klingel-Decay + leises Tick-Tock einer Uhr.

### 8.4 Vergessens-Portal (Endgame, Atlas)
**Wind-Up:** Audio dimmt langsam (1.5s).
**Body:** **Stille** für 1 Sekunde — dann Plopp-Whoosh am Ziel.
**Tail:** Audio kommt langsam zurück, im neuen Raum.

### 8.5 Anomaly-Phasing (Stunden-Wandler, Nicht-Mann)
**Body:** Sehr kurzer Audio-Cut (0.1s) — wie Audio-Glitch.
**Foley:** Tape-Stop + Reverse-Bit.

---

## TEIL 9 — MONSTER GENERIC AUDIO

(Spezifische Monster siehe `../gameplay/VELGRAD_BESTIARIUM.md`. Hier die generischen Layer.)

### 9.1 Idle / Patrouille
- **Atem-Loop:** je nach Monster (humanoid = Atem, Bestie = Knurren, Geist = leiser Whisper, Konstrukt = Mechanik-Tick).
- **Footsteps:** Wie Player, aber pro Archetyp (Brute = schwer, Skirmisher = leicht, Stalker = lautlos).

### 9.2 Alert / Detection
- **Audio-Cue für Spieler:** Klares Alert-Signal — Monster bemerkt dich. Sollte über Music hörbar sein (RTPC: SFX bus volume + 6dB für 0.5s).
- **Vocal:** je nach Monster (Goblin = Knurren-Höhepunkt, Mensch = „Hey!" oder Schrei, Geist = anschwellender Whisper).

### 9.3 Combat-Vocals
- **Attack-Grunt:** Bei jedem Schwung.
- **Pain-Reaction:** Bei Treffer auf Monster.
- **Death-Vocal:** Klar markant — Spieler soll wissen „der ist tot".

### 9.4 Hit-Reaction (Spieler-Hits Monster)
Material-spezifisch:
- **Flesh:** Wet thunk, blood-spurt.
- **Bone:** Knochen-Crack.
- **Armor:** Metall-Clang.
- **Stein/Construct:** Hartes Schlagen + Funken.
- **Geist:** Wirbel-Hiss (kein direkter Impact, eher Energie-Flicker).

### 9.5 Death-Audio (Monster)
- **Sterben-Vocal:** Spezies-spezifischer Death-Schrei oder -Atem.
- **Body-Fall:** Material-Aufprall auf Boden.
- **Spezial-Death:**
  - **Burn-Death:** Schreien + Sizzeln.
  - **Freeze-Shatter:** Glas-Shatter-Sequenz.
  - **Lightning-Death:** Zucken + Sizzle.
  - **Chaos-Death:** Auflösen-Schmelze + Whisper-Drop.

---

## TEIL 10 — MUSIK-SYSTEM

### 10.1 Adaptive Music-Layer
Pro Region ein Music-Set mit **mindestens 4 Stems**:
1. **Bed** — Drone, immer aktiv im Akt
2. **Tension** — Schicht, die bei Combat-Nähe einblendet
3. **Combat** — volle Combat-Music
4. **Resolution** — Outro nach Combat-End

**Crossfading via RTPC `player_in_combat`:**
- 0 (idle): Bed + leise Tension
- 0.5 (alert): Bed + Tension
- 1 (combat): Tension + Combat

### 10.2 Boss-Music (siehe Boss-Audio-Doc)
- Separater Bus `MUSIC_BOSS`.
- Crossfade aus Region-Music in 2s.
- Phase-Layer via RTPC `boss_phase`.

### 10.3 Cinematic-Music
- Death-Transition: spezifisch (siehe Gameplay-Doc Teil A).
- Boss-Intro: dedizierte 3-8s Stinger.
- Cutscene-Music: pro Cutscene komponiert.

### 10.4 Music-Composition-Guidelines
**Tonalität:** Phrygisch oder dorisch (Modal-Stil, klingt antik). Vermeide Dur. A-Moll als Heimattonart.
**BPM:** 60-90 für Ambient, 100-130 für Combat, 70-100 für Boss.
**Instrumentierung:**
- Streicher (Cello, Violine, Bratsche, Kontrabass)
- Chor (gemischter, oft Vokalise ohne Worte)
- Solo-Instrumente: Cello, Frauenstimme, Klavier (gestimmt leicht verstimmt für Velgrad-Feeling)
- Selten: Synth-Drone (nur für Anomalie-Regionen!)
- Perkussion: Trommel, Holz-Klocks, Cembalo-Töne, niemals Drum-Kit.
- Foley-Integration: Sound-Design verschmilzt mit Music (z.B. Wind-Field-Recording als Pad).

---

## TEIL 11 — ASSET-NAMING-CONVENTION

Pflicht für saubere Library-Pflege:

```
[CATEGORY]_[SUBCATEGORY]_[VARIANT]_[INDEX].wav

Beispiele:
PLAYER_FOOTSTEP_STONE_01.wav
PLAYER_FOOTSTEP_SAND_07.wav
SKILL_FIRE_FIREBALL_CAST_01.wav
SKILL_FIRE_FIREBALL_IMPACT_03.wav
ENEMY_BRUTE_ATTACK_SLAM_02.wav
ENEMY_BRUTE_VOICE_DEATH_01.wav
BOSS_SHULAVH_WAILING_LULLABY_LOOP.wav
ENV_WIND_ASCHENFELDER_LOOP_01.wav
ENV_RAIN_LIGHT_LOOP.wav
WEATHER_THUNDER_DISTANT_03.wav
UI_HOVER_DEFAULT.wav
UI_PICKUP_UNIQUE_STINGER.wav
MUSIC_AKT01_BED_LOOP.wav
MUSIC_AKT01_COMBAT_STEM.wav
```

**Regeln:**
- Nur Großbuchstaben + Unterstriche.
- Index 2-stellig (01, 02, ..., 99).
- Variationen pro Sound: mindestens 4, ideal 6-8.
- Loops mit `_LOOP` suffixiert.
- Stems mit `_STEM` suffixiert.

---

## TEIL 12 — MIXING & MASTERING STANDARDS

### 12.1 Volume-Levels (relative dB)
- **Music:** -18dB LUFS (background-bed); Boss-Music: -16dB LUFS.
- **Ambient SFX:** -20dB LUFS.
- **Player Combat SFX:** -12dB LUFS.
- **Skill Casts:** -10dB LUFS (laut, wichtig für Feedback).
- **UI:** -16dB LUFS.
- **Voice / Dialogue:** -14dB LUFS (priorität).
- **Master Output:** -14 LUFS (Standard-Streaming-Compliant).

### 12.2 Frequency-Mapping (avoid mud)
- **Sub-Bass (20-60Hz):** nur Skills, Boss-Hits, große Slams, Donner.
- **Bass (60-250Hz):** Music-Bed, Atem, schwere Footsteps.
- **Low-Mids (250-500Hz):** Stimmen, Holz-Foley.
- **Mids (500-2000Hz):** Combat-Klang, Schreie, Skill-Body.
- **High-Mids (2-4kHz):** Klarheit, Konsonanten in Voice.
- **Treble (4-10kHz):** UI-Pings, Glas, Frost, Detail.
- **Air (10-20kHz):** Atmosphere, Reverb-Tails.

**HP/LP-Pflicht:** HighPass auf alles bei 40Hz (kein Mud), LowPass auf manche bei 18kHz (kein Hiss).

### 12.3 Reverb-Presets pro Region
- **Outdoor (Salzküste, Aschenfelder):** Subtiler natural-reverb, kurzer Tail.
- **Höhle (Tiefe Ader):** Long cavernous reverb (3-5s tail).
- **Spiegelstadt:** Glas-Haus-Reverb, hochfrequent dominiert.
- **Wurzelgrab:** Organisch, gedämpft, kurzer Tail.
- **Tribunal-Festung:** Stein-Halle, mittlerer Tail.
- **Anomalie-Zone:** Inverted Reverb (Pre-Delay-Effect — Reverb VOR dem Sound, uncanny).

### 12.4 Compression
- **Music:** Sanfter Bus-Compressor (-2 dB GR), kein Pumping.
- **Combat-SFX:** Etwas aggressiver (-4 dB GR) für Punch.
- **Voice:** Vocal-Compressor (-6 dB GR) für Konsistenz.

### 12.5 Master-Bus
- **Limiter:** -1 dB Ceiling.
- **Loudness:** -14 LUFS integriert (Standard für Spiele/Streaming).
- **Stereo-Imaging:** breit, aber nicht extrem (Sub-Bass mono!).

---

## TEIL 13 — IMPLEMENTATION-CHECKLISTE FÜR CLAUDE CODE

Bevor jeder Sound-Asset als „done" markiert wird:

- [ ] **Lore-konsistent?** (Passt zur Velgrad-DNA? Kein Pop, keine Cartoon-Effekte?)
- [ ] **4-Layer-Aufbau?** (Wind-up, Body, Tail, Impact wo applicable?)
- [ ] **Mindestens 4 Variationen?** (Anti-Repetition)
- [ ] **Frequency-Balance?** (Kein Mud im Mix, hat eigenen Platz im Spectrum?)
- [ ] **Spatial-Audio aktiviert?** (3D-Position, HRTF?)
- [ ] **RTPCs gesetzt?** (Wenn relevant: Distance, Health, Environment)
- [ ] **Snapshot-Trigger?** (Wenn Audio-Mix-Wechsel notwendig)
- [ ] **Asset-Naming korrekt?** (Convention aus Teil 11)
- [ ] **Loop-Punkte sauber?** (Bei Loops: nahtlos, keine Klicks)
- [ ] **Loudness-Konformität?** (LUFS-Target getroffen)
- [ ] **Accessibility-Fallback?** (Wichtige Audio-Cues haben Visual-Backup)

---

## TEIL 14 — PER-AKT-SOUND-CHECKLISTE

Damit Claude Code pro Akt weiß, was minimum implementiert sein muss:

### AKT 1 — Salzküste
- [ ] Wind-Bed (loop)
- [ ] Möwen-Library
- [ ] Wellenbrechen-Loop
- [ ] Salzfußschritte (8 Varianten)
- [ ] Schiffsknarzen (interactive props)
- [ ] Salzhüter-Boss-Pack (alle Attacken siehe Boss-Doc)
- [ ] Brassweir-Stadt-Ambience
- [ ] Generic Combat-SFX

### AKT 2 — Glasgoldene Ruinen
- [ ] Hohler Wind durch Ruinen
- [ ] Ferne Senatorenreden-Loop (echo, gemurmelt)
- [ ] Glas-Klingel-Layer
- [ ] Glas-Footsteps
- [ ] Echo-Senator-Voice-Library
- [ ] Senator-Phantom-Boss-Pack
- [ ] Echo-Markt-Ambience

### AKT 3 — Aschenfelder
- [ ] Heißer trockener Wind
- [ ] Asche-Stream-Foley
- [ ] Asche-Footsteps
- [ ] Glut-Crackle-Loop
- [ ] Ferne Schlacht-Schreie
- [ ] Tribunal-Predigt-Voice-Layer (gemurmelt im Wind)
- [ ] Vehren-Boss-Pack
- [ ] Säulen-von-Helst-Ambience

### AKT 4 — Wurzelgrab
- [ ] Atem-Loop (das Wurzelgrab atmet)
- [ ] Wurzel-Knarzen
- [ ] Wasser-Drip
- [ ] Wurzel/Holz-Footsteps
- [ ] Vossharil-Voice-Library
- [ ] Shulavh-Boss-Pack (sehr wichtig!)
- [ ] Knoten-Markt-Ambience
- [ ] Faden-Sound-Family (Skill-Family für Bindung-Effekte)

### AKT 5 — Spiegelstadt Velharn
- [ ] Stille mit Tinnitus-Layer
- [ ] Glas-Klingel-Mobile
- [ ] Glas-Footsteps
- [ ] Reverse-Reverb-Stimmen (Zeit-Echos)
- [ ] Drei-Köpfe-Senator-Boss-Pack
- [ ] Stunden-Wandler-Phasing-FX
- [ ] Spiegelhof-Ambience
- [ ] Glas-Shatter-Library

### AKT 6 — Drei Wunden
- [ ] Wunden-Spezifika:
  - Salzwunde: Wasser-Drone + ertrunkene Geister
  - Aschwunde: Brennen + Drachen-Atem
  - Hohlwunde: Stille + Reverse-Audio
- [ ] Drei Boss-Packs (Ertrunkene Königin, Echo-Drache, Nicht-Gott)
- [ ] Anomalien-Audio-Family

### AKT 7 — Hohlwort & Endgame
- [ ] Im-Nesh-Boss-Pack (komplex, viele Layer)
- [ ] Hundert-Zungen-Voice-Library (15+ Schauspieler)
- [ ] Pakt-Beschwörung-Audio
- [ ] Endgame-Wahl-Cinematic-Music (4 verschiedene Outcomes)

### ATLAS / WELKENDE WELTEN
- [ ] Aspekt-Echo-Boss-Pool (7 verschiedene Audio-Identitäten)
- [ ] Atlas-Map-Travel-Audio
- [ ] Welkende-Welt-Korruptions-Layer

---

## TEIL 15 — FREIE SOUND-QUELLEN-LISTE (Quick-Reference)

Für Claude Code, der Sounds sucht:

**Top-Quellen kommerziell nutzbar, kostenlos:**
1. `sonniss.com/gameaudiogdc` — Sonniss GDC-Bundles (alle Jahre, ~100GB AAA-Qualität)
2. `freesound.org` (CC0-Filter setzen!)
3. `pixabay.com/sound-effects`
4. `opengameart.org`
5. `99sounds.org`

**Spezifisch hilfreich für Velgrad:**
- **Wind/Wetter:** Free To Use Sounds (Field Recordings)
- **Ambient/Dungeon:** Tabletop Audio (CC-BY)
- **Combat:** GameDev Market Sound-Packs (5-30€)
- **Voice/Choir:** Eigene Aufnahmen (immer am besten, einzigartig)

**Asset-Tracking:** Für jeden externen Sound in `audio_credits.csv` festhalten: File-Pfad, Quelle, Author, Lizenz, URL.

---

## ABSCHLUSS — GOLDENE REGELN

1. **Lore-Konsistenz vor Coolness.** Wenn ein Sound „cool" ist, aber Velgrad nicht atmet, raus damit.
2. **Stille ist erlaubt.** Sogar erforderlich. Velgrad lebt im Atem zwischen den Klängen.
3. **Telegraph alles.** Jede gefährliche Aktion (Spieler & Gegner) braucht Audio-Pre-Cue, nicht nur Visual.
4. **4-Layer-Pflicht.** Wind-up, Body, Tail, Impact — wo immer es Sinn macht.
5. **Multiple Variationen.** Anti-Ohrenmüdigkeit. Mindestens 4 Variationen pro repetitiven Sound.
6. **Accessibility.** Audio-Cues haben Visual-Backups (und umgekehrt). Sehbehinderte sollen kämpfen können.
7. **3D-Audio Pflicht.** Spieler positioniert sich auch akustisch.
8. **Mixing-Disziplin.** Frequency-Hierarchie. Nichts im Mix kämpft.
9. **Test in Combat-Chaos.** Boss-Encounter mit 20+ Mobs — bleibt Wichtiges hörbar?
10. **Test mit verschiedenen Setups.** Headphones, Stereo-TV, Laptop-Speaker — alles muss funktionieren.

---

*„Velgrad atmet. Atme mit. Wenn dein Spiel nicht atmet, kannst du es nicht hören. Wenn du es nicht hörst, ist es schon vergessen."*
— Audio-Direktive
