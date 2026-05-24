# Shadowfall — Die Chronik von Velgrad

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![pygame-ce](https://img.shields.io/badge/pygame--ce-2.5+-green.svg)](https://pyga.me/)
[![Audio](https://img.shields.io/badge/audio-660%20KI%20Files-orange.svg)](#ki-audio-pipeline)
[![Status](https://img.shields.io/badge/status-foundation-yellow.svg)](#status--roadmap)

Ein narratives 2D-ARPG in Pygame, angesiedelt in der Welt **Velgrad** — einer Welt, die sich selbst vergisst.

> *„Die Welt vergisst sich selbst. Wer erinnert dich — wenn du nicht?"*

**Self-contained:** Game ist sofort spielbar nach `git clone` — alle 660 KI-generierten Audio-Files (Voice + SFX) sind im Repo enthalten.

---

## Was ist Shadowfall?

Shadowfall ist ein **Single-Player Action-RPG** mit dichter Lore, taktischem Top-Down-Combat und einer vollstaendig KI-generierten Audio-Pipeline. Inspiriert von **Path of Exile 2**, **Diablo IV** und **Dark Souls** — aber mit eigener mythologischer Welt: Sieben Aspekte, sieben Atemzuege, ein verlorener Pakt und ein Verraeter mit hundert Zungen.

**Status:** Foundation-Phase. Akt 1 spielbar mit vollem KI-Audio, Akt 2–7 + Endgame in Planung.

---

## Quick-Start

```bash
git clone https://github.com/OsuGerman/shadowfall.git
cd shadowfall
pip install pygame-ce
python shadowfall.py
```

Das ist alles. Game laeuft mit komplettem Sound + 8 Klassen + Akt-1-Quests + Boss-Encounters.

---

## Kern-Features

### Spielwelt & Story

- **7 Akte** durch die Welt Velgrad — von der Salzkueste ueber die Glasgoldenen Ruinen bis zum Hohlwort
- **8 spielbare Klassen** mit eigenen Lineages:
  - **Warrior** (Eisenwaechter, Kharn-Lineage)
  - **Monk** (Stiller Schritt, Selbst-Lineage)
  - **Sorceress** (Funkengeborene, Valsa-Beruehrt)
  - **Witch** (Knochenwitwe, Shulavh-Beruehrt)
  - **Ranger** (Saattraegerin, Wilde Lineage)
  - **Mercenary** (Mahnmal-Soeldner, Korven-Vor-Lineage)
  - **Huntress** (Speerschwester, Shulavh-Lineage)
  - **Druid** (Wandelnde, Drei-Tiere-Lineage)
- **7 Fraktionen** mit Konflikt-Matrix (Erblinde Kirche, Tribunal der Asche, Mahnmal-Gilde, Knochenwitwen, Saattraeger, Speerschwestern, Stille Schritte)
- **53 Quests** ausformuliert (Haupt + Faction + Side + Lore + Crafting + Bounty + Hidden) — siehe [docs/lore/QUEST_BIBEL.md](docs/lore/QUEST_BIBEL.md)
- **3 Endings** mit Akt-7-Wahl
- **Voice-Acting fuer alle Haupt-NPCs** — Korven, Helst, Vossharil, Tameris, Otreth, Mara, Vehren, Drei Muetter

### Gameplay-Systeme

- **30 Bestiarium-Mobs** mit individuellen Hurt/Death-Sounds — siehe [docs/gameplay/VELGRAD_BESTIARIUM.md](docs/gameplay/VELGRAD_BESTIARIUM.md)
- **15 Boss-Encounters** mit Multi-Phase-Cinematics + Spawn-Methods (`rise_from_grave`, `assemble`, `descend_from_throne`, `emerge_from_liquid`, ...)
- **50 Unique-Items** — siehe [docs/gameplay/VELGRAD_ITEMS_UNIQUE_BIBEL.md](docs/gameplay/VELGRAD_ITEMS_UNIQUE_BIBEL.md)
- **7 Aspekt-Pakte** als Skill-Gem-System (Kharn/Nheyra/Ousen/Valsa/Im-Nesh/Shulavh/Vergessen)
- **Crafting**: Upgrade, Reroll, Socket, Enchant, Salvage + Otreth-Gemcutter
- **Mahnmal-Fast-Travel** zwischen freigeschalteten Outposts
- **Status-Effekte** mit Element-Combos (burn + frost = shatter, etc.)
- **Procedural Dungeons** pro Biome mit Multi-Stage-Sub-Areas
- **Quest-Engine** mit 12 Stage-Types (TALK/KILL/REACH/COLLECT/INTERACT/RETURN/ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL)
- **Faction-Rep-System** (geplant — UI-Wiring in Arbeit)

### KI-Audio-Pipeline

Vollstaendige Sound-Pipeline via **ElevenLabs** — **alle Files im Repo enthalten**:

| Kategorie | Anzahl | Groesse |
|---|---|---|
| KI-Voice-Lines (8 NPCs + 8 Klassen + Generic) | **227** | 13 MB |
| KI-SFX Phase 1 (Mob/Boss/Skill/UI/Combat) | 227 | 8 MB |
| KI-SFX Phase 2 (Footsteps/Status/Crafting/Menu/Quest) | 78 | 3 MB |
| KI-SFX Phase 3 (Decor/Trap/Weather/Pakt/Atmos/...) | 128 | 5 MB |
| **KI-SFX Total** | **433** | **~16 MB** |
| Stock-Sounds (Freesound, CC0) | 267 | 45 MB |
| Music-Tracks | 2 | 9 MB |
| **Gesamt-Audio** | **~927 Files** | **~80 MB** |

Pipeline-Tools in [`tools/`](tools/) erlauben **Re-Generation** mit eigenem ElevenLabs-Account (Voice-Casting-Aenderungen, neue Lines, etc.). Audio-Generierung kostete einmalig **10,35 EUR** ElevenLabs Creator-Plan.

### Engine-Highlights

- **Procedural Particle-System** mit 4 Layern (Ambient/Gameplay/Telegraph/UI-Overlay)
- **Dynamic Ambient Culling** waehrend Boss-Encounters (~70% Reduktion fuer klare Lesbarkeit)
- **Day/Night-Zyklus** mit Wetter-Variation pro Biome (dust/snow/ash/pollen/sand/spore/stardust)
- **Lighting-Pass** mit per-Aspekt-Color-Lights
- **NPC-Schedules** (Tag/Nacht-Position)
- **Footsteps pro Biome** automatisch via `pick_footstep_for_biome()` (11 Material-Surfaces)
- **Save-Game-Versionierung** mit Migration-Pfaden
- **Hardcore-Memorial-System** fuer permadeath-Modus
- **Engine-Wiring der KI-Audio**: Boss-Spawn-Stinger, Mahnmal-Stelen-Activation, Rarity-aware Item-Pickup, NPC-Voice beim Reden, Quest-Marker-Reach, Achievement-Unlock, Status-Apply (frozen/shock/poison/bleed/stun/silence)

---

## Welt-Aufbau (Storyline)

| Akt | Region | Hub | Lore-Hook |
|---|---|---|---|
| 1 | Salzkueste | Brassweir | Drei Doerfer fehlen — die Salzwunde lockt |
| 1b | Zhar-Eth | Wandernde Karawane | Speerschwestern-Mondbund |
| 2 | Glasgoldene Ruinen | Echo-Markt | Das alte Imperium erinnert sich an seinen Tod |
| 3 | Aschenfelder | Saeulen-von-Helst | Wo Valsa fiel. Tribunal-Inquisition jagt dich |
| 4 | Wurzelgrab | Knoten-Markt | Shulavh, die Faden-Mutter, hat dich gewaehlt |
| 5 | Spiegelstadt Velharn | Spiegelhof | Drei Zeit-Schichten — Glasgolden, Goetterkrieg, Gegenwart |
| 6 | Drei Wunden | Wunden-Lager | Salzwunde, Aschwunde, Hohlwunde — den Pakt lesen |
| 7 | Hohlwort | Drei Muetter | Konfrontation mit Im-Nesh, dem Hundertzuengigen |

Vollstaendige Lore in [docs/lore/VELGRAD_LORE_BIBEL.md](docs/lore/VELGRAD_LORE_BIBEL.md) (588 Zeilen).

---

## Projekt-Struktur

```
shadowfall/
├── shadowfall.py              ← Game-Entry-Point (Pygame Main-Loop)
│
├── sf/                        ← Engine-Code (30 Module)
│   ├── game.py                ← Game-Loop, Update, Render
│   ├── combat.py              ← Damage, Crit, Death-Layer, bestiary_key-Sounds
│   ├── boss_encounter.py      ← Multi-Phase-Boss-Cinematics + Spawn/Phase-Stinger
│   ├── skills.py + class_skills.py  ← 8 Klassen × Skill-Pool
│   ├── enemies.py + bestiary.py     ← 30 Velgrad-Mobs
│   ├── quests.py + quest_data.py    ← Quest-Engine + 12 Stage-Types
│   ├── crafting.py + items.py       ← Otreth-Gemcutter, Affix-System
│   ├── effects.py             ← Status-Effekte mit Element-Combos
│   ├── sounds.py              ← Audio-Bus, Footstep-Picker, AI-SFX-Resolver
│   ├── voice_registry.py      ← Auto-generiert: 85 Voice-Pools
│   ├── sfx_registry.py        ← Auto-generiert: 433 SFX-Eintraege
│   ├── dungeon.py + dungeon_events.py + dungeon_gen.py
│   ├── sprites.py + lighting.py + weather.py
│   ├── ui.py + town.py + outposts.py + shop.py + stash.py
│   ├── ai.py + entities.py + progression.py + save.py
│   ├── achievements.py + tutorial.py + crash_logger.py + tips.py
│   └── ... (regions, runes, gems, archetypes, aspects, ...)
│
├── tools/                     ← KI-Audio-Pipeline (Re-Generation optional)
│   ├── voice_gen.py           ← ElevenLabs Voice-Generator
│   ├── voice_manifest_builder.py    ← Parst Voice-Pool + Casting → JSON
│   ├── voice_list.py          ← Listet ElevenLabs-Library-Stimmen
│   ├── voice_config.py        ← API-Key-Loader, Pronunciation-Map
│   ├── sfx_gen.py             ← ElevenLabs SFX-Generator (alle Phasen)
│   └── README.md              ← Pipeline-Workflow
│
├── sounds/                    ← KI-Audio (committet, ~24 MB)
│   ├── voice/                 ← 227 KI-Voice-Lines (8 NPCs + 8 Klassen + Generic)
│   │   ├── korven/ helst/ vossharil/ tameris/ otreth/ mara/ vehren/
│   │   ├── drei_muetter/ generic/
│   │   └── cls_warrior/ cls_monk/ cls_sorceress/ cls_witch/ ...
│   └── sfx/generated/         ← 433 KI-SFX in 31 Sektionen
│       ├── ui/ combat/ skills/ monster/ boss/ cinematic/ lore/
│       ├── movement/ player_combat/ status/ interact/ crafting/ menu/ quest/
│       ├── decor/ trap/ weather/ class_special/ currency/ event/
│       ├── boss_special/ flask/ player_voice/ achievement/
│       ├── engrave/ pakt/ daynight/ shop/ tutorial/ saveload/ atmos/
│       └── voice_manifest.json + sfx_manifest.json
│
├── Sounds/                    ← 267 Stock-MP3s (Freesound, CC0)
│
├── Nebel von Arken.mp3        ← Music-Track 1
├── Soundtrack 3.mp3           ← Music-Track 2
│
├── docs/project-mgmt/PLAN.md                    ← Master-Plan (140+ Updates)
├── docs/project-mgmt/WELT_AUFBAU.md             ← Welt-Topologie + NPC-Roster + Phasen-Plan
├── docs/lore/QUEST_BIBEL.md             ← 53 Quests ausformuliert + Stage-Definitionen
├── docs/lore/VELGRAD_LORE_BIBEL.md      ← Kosmologie + 7 Aspekte + Akt-Storyline (588 Zeilen)
├── docs/gameplay/VELGRAD_BESTIARIUM.md      ← 30 Mobs mit AI-Patterns
├── docs/gameplay/VELGRAD_ITEMS_UNIQUE_BIBEL.md      ← 50 Unique-Items
├── docs/design/VELGRAD_VOICE_LINES_POOL.md        ← Dialog-Texte pro NPC
├── docs/design/_legacy/VELGRAD_VOICE_CASTING.md           ← Voice-IDs pro Charakter (ElevenLabs)
├── docs/design/VELGRAD_AUDIO_DESIGN_BIBEL.md      ← Audio-Vision
├── docs/design/VELGRAD_SFX_BIBEL.md               ← 453 SFX-Definitionen + Generation-Prompts
├── docs/gameplay/POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md  ← Mechanik-Referenz
├── docs/gameplay/POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md  ← Skill-Tree-Referenz
├── docs/meta/CHANGELOG.md               ← Update-Historie (Update #1 → #150+)
├── tests/                     ← pytest Smoke-Tests
└── Design idee/               ← UI-Mockups (HTML/JSX)
```

---

## Setup & Installation

### Voraussetzungen
- **Python 3.10+** (getestet mit 3.14)
- **pygame-ce 2.5+** (Community-Fork, performanter als Mainline)

### Standard-Installation

```bash
git clone https://github.com/OsuGerman/shadowfall.git
cd shadowfall
pip install pygame-ce
python shadowfall.py
```

Game laeuft mit vollem Sound. Keine weiteren Schritte noetig.

### Optional: Eigene Voice-Casting-Aenderungen

Falls du z. B. eine andere Stimme fuer Korven oder Vossharil willst, kannst du das Voice-Casting anpassen und neu generieren:

1. **ElevenLabs-Account** erstellen ([elevenlabs.io](https://elevenlabs.io)) — Creator-Plan (~22 EUR/mo) empfohlen
2. **API-Key** holen unter Settings → API Keys
3. Im Projekt-Root `ElevenLabs.txt` anlegen mit dem Key (eine Zeile, nichts sonst)
4. In `docs/design/_legacy/VELGRAD_VOICE_CASTING.md` die `voice_id` fuer einen NPC ersetzen
5. Voice-Generation:
   ```bash
   python tools/voice_manifest_builder.py
   python tools/voice_gen.py --npc korven   # nur Korven neu
   ```

**Sicherheit:** `ElevenLabs.txt` ist in `.gitignore` eingetragen — der Key wird nie versehentlich committet.

### SFX-Re-Generation

Analog fuer SFX, falls du z. B. den Salzhueter-Boss-Roar dramatischer haben willst:

1. In `docs/design/VELGRAD_SFX_BIBEL.md` den ElevenLabs-Prompt anpassen
2. Im SFX-Manifest die `status` auf `pending` setzen (`sounds/sfx/sfx_manifest.json`)
3. `python tools/sfx_gen.py` rufen

---

## Sprachen & Inhalte

- **Spielsprache:** Deutsch
- **Code:** Englisch (Variablen, Funktionen) — Kommentare gemischt DE/EN
- **Lore-Dokumente:** Deutsch (Velgrad'scher Stil mit altertuemlichen Wendungen)
- **NPC-Voices:** Deutsch (ElevenLabs `eleven_multilingual_v2`)

---

## Tests

```bash
python -m pytest tests/
```

Smoke-Tests in [`tests/smoke.py`](tests/smoke.py) decken Engine-Importe, Save/Load, Crafting-Logik, Quest-Engine, NPC-Spawning und Akt-Progression ab (Update #150 hat 237 Zeilen Regression-Tests ergaenzt).

---

## Status & Roadmap

### Aktuell (Foundation komplett)
- ✅ Pygame-Engine mit 30 Modulen
- ✅ Akt 1 (Salzkueste) komplett spielbar — Korven, Otreth, Tameris, Mara, Eldon, Mahnmal-Verwahrer, Helst-Vorpost
- ✅ Boss-Encounter-System mit Salzhueter-Brut + Vehren + 6 weiteren Encounter-Configs (Senator-Geist, Shulavh, Velharn-Trio, Ertrunkene Koenigin, Echo-Drache, Nicht-Gott)
- ✅ **KI-Audio-Pipeline vollstaendig im Repo** — 227 Voice + 433 SFX
- ✅ Quest-Engine mit 12 Stage-Types
- ✅ Crafting + Affix-System + Otreth-Gemcutter
- ✅ Mahnmal-Schrein mit 7-Aspekt-Pakt-Wahl
- ✅ NPC-Voice-Greeting beim Reden mit Haupt-NPCs
- ✅ Footsteps pro Biome (11 Material-Surfaces)
- ✅ Engine-Wiring der Phase-2/3-SFX (Doors, Chests, Cursed-Altar, Rune-Anchor, etc.)

### Naechste Schritte
- ⏳ Akt 1 vollstaendig (4 weitere Quests, Tameris-Schwester-Chain, Tribunal-Geruecht, Bounty-Salzgekreuzte, Versunkenes Grab)
- ⏳ Faction-Rep-System UI im Codex
- ⏳ Akt 2 Implementierung (Echo-Markt-Hub, Helst-NPC, Senator-Geist-Boss-Mechanik)
- ⏳ Music-Tracks via Suno AI (42 geplant — Akt-Themes, Boss-Themes, Town-Themes)
- ⏳ Ambience-Loops via Stable Audio (14 velgrad-spezifische Loops)
- ⏳ Cutscene-Framework + 9 Pflicht-Cutscenes
- ⏳ Endgame-Atlas (Welkende Welten)
- ⏳ KI-generierte Sprites via Scenario.gg / Stable Diffusion (geplant)

Detail-Roadmap in [docs/project-mgmt/ROADMAP.md](docs/project-mgmt/ROADMAP.md) (5-Tier-Sprint-Plan, 149 priorisierte Tasks aus docs/project-mgmt/PLAN.md + docs/project-mgmt/WELT_AUFBAU.md + docs/lore/QUEST_BIBEL.md synthetisiert).

---

## Letzte Updates

- **Update #150** — Akt-Progression-Blocker fixed (Quest-Objectives wurden nirgendwo abgeschlossen → alle Akt-2+ Outposts waren permanent gelockt)
- **Update #149** — ESCORT-Stage-Robustheit + Phantom-NPC-Fix
- **Update #148** — Phase-3-SFX (128 zusaetzliche SFX: Decor, Trap, Weather, Pakt, Atmos)
- **Update #147** — Phase-2-SFX-Generation (78 SFX: Footsteps, Player-Combat, Status, Doors)
- **Update #146** — Phase-1-SFX-Generation (227 SFX: Mob/Boss/Skill/UI/Cinematic)
- **Update #145** — Voice-Lines-Generation (227 Lines, alle 8 Haupt-NPCs)

Vollstaendige Update-Historie in [docs/meta/CHANGELOG.md](docs/meta/CHANGELOG.md).

---

## Mitwirken

Das Projekt ist aktuell Solo-Dev. Bug-Reports und Lore-Ideen via [GitHub-Issues](https://github.com/OsuGerman/shadowfall/issues) willkommen. Code-Beitraege bitte erst nach Diskussion (das Game ist eng mit der Lore verzahnt — willkuerliche Mechanik-Aenderungen passen oft nicht zum Setting).

---

## Lizenz & Credits

- **Spielkonzept, Lore, Code:** Adrian Mirwaldt ([@OsuGerman](https://github.com/OsuGerman))
- **Stock-Sounds:** [Freesound.org](https://freesound.org) (CC0 + verschiedene Lizenzen — Attribution in den Dateinamen)
- **KI-Voice:** [ElevenLabs](https://elevenlabs.io) (`eleven_multilingual_v2`) — kommerzielle Lizenz via Creator-Plan
- **KI-SFX:** [ElevenLabs Sound Effects API](https://elevenlabs.io/sound-effects)
- **Engine:** [pygame-ce](https://pyga.me/) (LGPL)
- **Genre-Inspiration:** Path of Exile 2, Diablo IV, Dark Souls, Hollow Knight

Lizenz: aktuell **kein offizielles Lizenz-Modell** — privat / nicht-kommerzieller Open-Development. Lizenz wird vor erstem Release finalisiert. Bei Fragen zur Nutzung: Issue oeffnen.

---

## Drei Kern-Zitate (Lore)

> *„Du wirfst keinen Feuerball. Du erinnerst die Luft daran, dass sie einst ein Feuerball war."*
> — Bruder Helst, Erblinder Priester, Akt 2

> *„Ein Schwur ist ein Faden. Ein Faden haelt die Welt. Reisst der Faden, faellt die Welt. Reisst sie nicht aus Boesheit — sondern weil niemand sie mehr hielt."*

> *„Es gab einmal sieben Atemzuege. Sechs davon halten dich. Den siebten — den fuerchtet jeder. Den fuerchte ich am wenigsten. Er ist der einzige, der mir mein Ende laesst."*
> — Vossharil die Dreimalige

---

*„Atme. Wieder. Bitte."* — Ousen, Endgame
