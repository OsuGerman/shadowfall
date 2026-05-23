# Shadowfall — Die Chronik von Velgrad

Ein narratives 2D-ARPG in Pygame, angesiedelt in der Welt **Velgrad** — einer Welt, die sich selbst vergisst.

> *„Die Welt vergisst sich selbst. Wer erinnert dich — wenn du nicht?"*

---

## Was ist Shadowfall?

Shadowfall ist ein **Single-Player Action-RPG** mit dichter Lore, taktischem Top-Down-Combat und einer vollständig KI-generierten Audio-Pipeline. Inspiriert von **Path of Exile 2**, **Diablo IV** und **Dark Souls** — aber mit eigener mythologischer Welt: Sieben Aspekte, sieben Atemzüge, ein verlorener Pakt und ein Verräter mit hundert Zungen.

**Status:** Foundation-Phase. Akt 1 spielbar, Akt 2–7 + Endgame in Planung.

---

## Kern-Features

### Spielwelt & Story

- **7 Akte** durch die Welt Velgrad — von der Salzkueste über die Glasgoldenen Ruinen bis zum Hohlwort
- **8 spielbare Klassen** mit eigenen Lineages: Warrior (Eisenwaechter), Monk (Stiller Schritt), Sorceress (Funkengeborene), Witch (Knochenwitwe), Ranger (Saattraegerin), Mercenary (Mahnmal-Soeldner), Huntress (Speerschwester), Druid (Wandelnde)
- **7 Fraktionen** mit Konflikt-Matrix (Erblinde Kirche, Tribunal der Asche, Mahnmal-Gilde, Knochenwitwen, Saattraeger, Speerschwestern, Stille Schritte)
- **53 Quests** geplant (Haupt + Faction + Side + Lore + Crafting + Bounty + Hidden) — 4 implementiert, 49 in [QUEST_BIBEL.md](QUEST_BIBEL.md) ausformuliert
- **3 Endings** mit Akt-7-Wahl

### Gameplay-Systeme

- **30 Bestiarium-Mobs** (siehe [VELGRAD_BESTIARIUM.md](VELGRAD_BESTIARIUM.md))
- **15 Boss-Encounters** mit Multi-Phase-Cinematics + Spawn-Methods (`rise_from_grave`, `assemble`, `descend_from_throne`, ...)
- **50 Unique-Items** (siehe [VELGRAD_ITEMS_UNIQUE_BIBEL.md](VELGRAD_ITEMS_UNIQUE_BIBEL.md))
- **7 Aspekt-Pakte** als Skill-Gem-System (Kharn/Nheyra/Ousen/Valsa/Im-Nesh/Shulavh/Vergessen)
- **Crafting**: Upgrade, Reroll, Socket, Enchant, Salvage + Otreth-Gemcutter
- **Mahnmal-Fast-Travel** zwischen freigeschalteten Outposts
- **Status-Effekte** mit Element-Combos (burn + frost = shatter, etc.)
- **Procedural Dungeons** pro Biome mit Multi-Stage-Sub-Areas

### KI-Audio-Pipeline

Vollständige Sound-Pipeline via **ElevenLabs**:

- **227 NPC-Voice-Lines** (8 Hauptcharaktere + 8 Klassen-Voices) — total 13 MB
- **433 KI-generierte SFX** in 24 Kategorien (Mob/Boss/Skill/UI/Footsteps/Combat/Crafting/Lore) — 11 MB
- **267 Stock-Sounds** (Freesound, Velgrad-Atmosphaere) — 45 MB
- **2 Music-Tracks** im Repo, weitere 42 Tracks geplant via Suno AI

Pipeline-Tools in [`tools/`](tools/) — Voice + SFX werden aus den Bibel-MDs parsed und batch-generiert. Audio-Generierung kostete **10,35 EUR ElevenLabs** insgesamt.

### Engine-Highlights

- **Procedural Particle-System** mit 4 Layern (Ambient/Gameplay/Telegraph/UI-Overlay)
- **Dynamic Ambient Culling** waehrend Boss-Encounters
- **Day/Night-Zyklus** mit Wetter-Variation pro Biome
- **Lighting-Pass** mit per-Aspekt-Color-Lights
- **NPC-Schedules** (Tag/Nacht-Position)
- **Save-Game-Versionierung** + Hardcore-Memorial

---

## Welt-Aufbau (kurz)

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

Vollstaendige Lore in [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md) (37 KB, 588 Zeilen).

---

## Projekt-Struktur

```
shadowfall/
├── shadowfall.py              ← Game-Entry-Point (Pygame Main-Loop)
├── sf/                        ← Engine-Code (29 Module, ~1 MB)
│   ├── game.py                ← Game-Loop, Update, Render
│   ├── combat.py              ← Damage, Crit, Death-Layer
│   ├── boss_encounter.py      ← Multi-Phase-Boss-Cinematics
│   ├── skills.py + class_skills.py  ← 8 Klassen × Skill-Pool
│   ├── enemies.py + bestiary.py     ← 30 Velgrad-Mobs
│   ├── quests.py + quest_data.py    ← Quest-Engine + Stage-Types
│   ├── crafting.py + items.py       ← Otreth-Gemcutter, Affix-System
│   ├── sounds.py              ← Audio-Bus, Footstep-Picker, AI-SFX-Resolver
│   ├── voice_registry.py      ← Auto-generiert: 85 Voice-Pools
│   ├── sfx_registry.py        ← Auto-generiert: 433 SFX-Eintraege
│   └── ... (sprites, dungeon, weather, lighting, ui, ...)
│
├── tools/                     ← KI-Audio-Pipeline
│   ├── voice_gen.py           ← ElevenLabs Voice-Generator
│   ├── voice_manifest_builder.py    ← Parst Voice-Pool + Casting
│   ├── voice_list.py          ← Listet Library-Stimmen
│   ├── voice_config.py        ← API-Key-Loader, Pronunciation-Map
│   ├── sfx_gen.py             ← ElevenLabs SFX-Generator
│   └── README.md              ← Pipeline-Workflow
│
├── Sounds/                    ← 267 Stock-MP3s (Freesound, CC0)
├── sounds/                    ← (ignoriert via .gitignore)
│   ├── voice/                 ← 227 KI-Voice-Lines (re-generierbar)
│   └── sfx/generated/         ← 433 KI-SFX (re-generierbar)
│
├── PLAN.md                    ← Master-Plan (87 KB)
├── WELT_AUFBAU.md             ← Welt-Topologie + NPC-Roster + Phasen
├── QUEST_BIBEL.md             ← 53 Quests ausformuliert
├── VELGRAD_LORE_BIBEL.md      ← Kosmologie + 7 Aspekte + Storyline
├── VELGRAD_BESTIARIUM.md      ← 30 Mobs mit AI-Patterns
├── VELGRAD_ITEMS_UNIQUE_BIBEL.md  ← 50 Unique-Items
├── VELGRAD_VOICE_LINES_POOL.md    ← Dialog-Texte pro NPC
├── VELGRAD_VOICE_CASTING.md       ← Voice-IDs pro Charakter
├── VELGRAD_AUDIO_DESIGN_BIBEL.md  ← Audio-Vision
├── VELGRAD_SFX_BIBEL.md           ← 433 SFX-Definitionen + Generation-Prompts
├── POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md  ← Mechanik-Referenz
├── POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md  ← Skill-Tree-Referenz
├── CHANGELOG.md               ← Update-Historie (140+ Updates)
└── Design idee/               ← UI-Mockups (HTML/JSX)
```

---

## Setup & Installation

### Voraussetzungen
- **Python 3.10+** (getestet mit 3.14)
- **pygame-ce 2.5+**

### Installation

```bash
git clone https://github.com/OsuGerman/shadowfall.git
cd shadowfall
pip install pygame-ce
python shadowfall.py
```

Stock-Sounds und Game-Code sind sofort spielbar.

### KI-Audio aktivieren (optional)

Die 660 KI-generierten Audio-Files (Voice + SFX) sind nicht im Repo — du regenerierst sie via ElevenLabs:

1. **ElevenLabs-Account** erstellen ([elevenlabs.io](https://elevenlabs.io)) — Creator-Plan (~22 EUR/mo) empfohlen
2. **API-Key** holen unter Settings → API Keys
3. Im Projekt-Root `ElevenLabs.txt` anlegen mit dem Key (eine Zeile, nichts sonst)
4. Voice-Generation:
   ```bash
   python tools/voice_manifest_builder.py
   python tools/voice_gen.py --dry-run    # Kosten checken
   python tools/voice_gen.py              # 227 Voice-Lines, ~2,56 EUR, ~15 min
   ```
5. SFX-Generation:
   ```bash
   python tools/sfx_gen.py --dry-run
   python tools/sfx_gen.py                # 433 SFX, ~7,79 EUR, ~25 min
   ```

Output landet automatisch in `sounds/voice/` und `sounds/sfx/generated/`. Die Registries `sf/voice_registry.py` + `sf/sfx_registry.py` werden auto-generiert. Engine findet die Files via `sf.sounds.play()` ohne weitere Konfiguration.

**Sicherheit:** `ElevenLabs.txt` ist in `.gitignore` eingetragen — der Key wird nie versehentlich committed.

---

## Sprachen & Inhalte

- **Spielsprache:** Deutsch
- **Code:** Englisch (Variablen, Funktionen)
- **Lore-Dokumente:** Deutsch (Velgrad'scher Stil mit altertümlichen Wendungen)
- **NPC-Voices:** Deutsch (ElevenLabs `eleven_multilingual_v2`)

---

## Tests

```bash
python -m pytest tests/
```

Smoke-Tests in [`tests/smoke.py`](tests/smoke.py) decken Engine-Importe, Save/Load und Crafting-Logik ab.

---

## Status & Roadmap

### Aktuell (Foundation)
- ✅ Pygame-Engine mit 29 Modulen
- ✅ Akt 1 (Salzkueste) spielbar — Korven, Otreth, Tameris, Mara, Eldon, Helst-Verwahrer
- ✅ Boss-Encounter-System mit Salzhueter-Brut + Vehren
- ✅ KI-Audio-Pipeline vollstaendig (Voice + SFX)
- ✅ Quest-Engine mit Stage-Types (TALK/KILL/REACH/COLLECT/INTERACT/RETURN/ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL)
- ✅ Crafting + Affix-System + Otreth-Gemcutter
- ✅ Mahnmal-Schrein mit 7-Aspekt-Pakt-Wahl

### Naechste Schritte
- ⏳ Akt 1 vollstaendig (4 weitere Quests, Tameris-Schwester-Chain)
- ⏳ Faction-Rep-System UI im Codex
- ⏳ Akt 2 (Echo-Markt, Helst, Senator-Geist-Boss)
- ⏳ Music-Tracks via Suno AI (42 geplant)
- ⏳ Ambience-Loops via Stable Audio
- ⏳ Cutscene-Framework
- ⏳ Endgame-Atlas

Detail-Roadmap in [WELT_AUFBAU.md](WELT_AUFBAU.md) (Sektion 13: Phasen-Plan).

---

## Mitwirken

Das Projekt ist aktuell Solo-Dev. Bug-Reports und Lore-Ideen via GitHub-Issues willkommen. Code-Beitraege bitte erst nach Diskussion (das Game ist eng mit der Lore verzahnt — willkürliche Mechanik-Aenderungen passen oft nicht zum Setting).

---

## Lizenz & Credits

- **Spielkonzept, Lore, Code:** Adrian Mirwaldt (@OsuGerman)
- **Stock-Sounds:** Freesound.org (CC0 + verschiedene Lizenzen — siehe Dateinamen)
- **KI-Voice:** ElevenLabs (`eleven_multilingual_v2`) — kommerzielle Lizenz via Creator-Plan
- **KI-SFX:** ElevenLabs Sound Effects API
- **Engine:** pygame-ce (LGPL)
- **Genre-Inspiration:** Path of Exile 2, Diablo IV, Dark Souls, Hollow Knight

Lizenz: privat / nicht-kommerzieller Open-Development. Lizenz-Modell wird vor Release finalisiert.

---

## Drei Kern-Zitate (Lore)

> *„Du wirfst keinen Feuerball. Du erinnerst die Luft daran, dass sie einst ein Feuerball war."*
> — Bruder Helst, Erblinder Priester, Akt 2

> *„Ein Schwur ist ein Faden. Ein Faden hält die Welt. Reißt der Faden, fällt die Welt. Reißt sie nicht aus Bösheit — sondern weil niemand sie mehr hielt."*

> *„Es gab einmal sieben Atemzüge. Sechs davon halten dich. Den siebten — den fürchtet jeder. Den fürchte ich am wenigsten. Er ist der einzige, der mir mein Ende lässt."*
> — Vossharil die Dreimalige
