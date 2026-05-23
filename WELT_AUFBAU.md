# WELT-AUFBAU — Arbeits-Bibel für Velgrad-Gameplay-Komplettierung

> **Zweck dieses Dokuments.** Eine einzige zentrale Arbeitsdatei, an der alles entlangläuft: Welt-Topologie, NPC-Roster, Quests, Items, Currencies, Bosse, Funktionen. Reihenfolge in Phasen 1–4. Jeder Block hat `[ ]` Checkboxen + Lore-Quelle + Code-Anker.
>
> 📍 **Naechste konkrete Schritte:** Siehe [ROADMAP.md](ROADMAP.md) — 5-Tier-Sprint-Plan synthetisiert aus diesem Doc + [PLAN.md](PLAN.md) + [QUEST_BIBEL.md](QUEST_BIBEL.md). WELT_AUFBAU.md hier ist die Welt-Daten-Bibel, ROADMAP.md ist „Was zuerst, was danach".
>
> **Quellen-Hierarchie (von PLAN.md übernommen):**
> 1. [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md)
> 2. [VELGRAD_BESTIARIUM.md](VELGRAD_BESTIARIUM.md) + [VELGRAD_ITEMS_UNIQUE_BIBEL.md](VELGRAD_ITEMS_UNIQUE_BIBEL.md)
> 3. [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md)
> 4. [VELGRAD_AUDIO_DESIGN_BIBEL.md](VELGRAD_AUDIO_DESIGN_BIBEL.md)
> 5. [POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md](POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md)
> 6. [POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md](POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md)
> 7. [PLAN.md](PLAN.md)
>
> **Engine-Anker:** [sf/](sf/) — Module die berührt werden, sind pro Task verlinkt.

---

## 0. AKZEPTANZ-KRITERIUM „Welt funktioniert komplett"

Eine Velgrad-Welt funktioniert, wenn:

1. Ein neuer Charakter kann **Akt 1 → Akt 7 → Endgame** linear durchlaufen.
2. Jeder Akt hat **Haupt + Neben + Faction + Lore + Crafting + Bounty + Hidden** Quest-Slots befüllt.
3. Jeder Akt hat **eigenen Hub-Vorposten** mit mindestens 4 NPCs aus dem Lore-Roster.
4. Jeder Akt-Boss aus VELGRAD_BESTIARIUM ist im Code als `BOSS_ENCOUNTERS`-Eintrag mit Phase-Quotes.
5. Jedes Unique-Item aus VELGRAD_ITEMS_UNIQUE_BIBEL hat einen **legalen Drop-Pfad** (Boss / Quest / Vendor / Crafting).
6. Currency-Loop schließt: Gold-, Marken-, Shard-, Orb-, Rep-, Atlas-Sinks existieren.
7. Akt-Übergänge sind **Quest-Flag-gegated**, nicht nur Level-gegated.
8. Fast-Travel via Mahnmal-Stelen funktioniert zwischen allen freigeschalteten Akten.
9. Endgame-Atlas hat 20+ Maps mit Modifier + 3+ Pinnacle-Bosse.
10. Drei Endings (Akt-7-Wahl) sind implementierbar.

---

## 1. WELT-TOPOLOGIE — Master-Layout

### 1.1 Hub-Hierarchie

- **Brassweir** (Akt 1) = **Persistenz-Hub**. Stash, Memorial, Crafting-Otreth, Mahnmal-Schrein — bleiben hier für alle Akte. [sf/town.py](sf/town.py)
- **Pro Akt: Vorposten-Camp** (kleine Town-Variante, 3–5 NPCs, kein Stash) erreichbar über Akt-Portal.
- **Mahnmal-Stelen = Fast-Travel-Waypoints** zwischen freigeschalteten Hub-Punkten.

### 1.2 Akt → Biome → Dungeon → Hub-Vorposten Master-Tabelle

| Akt | Lore-Region | Engine-Biome | Dungeon-Key | Vorposten | Boss | Boss-Encounter-Key |
|---|---|---|---|---|---|---|
| 0 | Brassweir-Hub | town | — | Brassweir (existiert) | — | — |
| 1 | Die Salzküste | crypt | `crypt_lost` ✅ | Brassweir | Salzhüter-Brut | `salzhueter_brut` ✅ |
| 1b | Zhar-Eth (Optional) | desert | `desert_temple` ✅ (Level-Req **4** — Update #115) | Zhar-Eth-Karawane ✅ (#113) | Tameris-Trial-Boss (neu) | tameris_trial |
| 2 | Glasgoldene Ruinen | **glass_ruins** (Rename frost) | `glass_palace` (Rename) | Echo-Markt (neu) | Senator-Geist | `senator_geist` (neu) |
| 3 | Aschenfelder | lava | `lava_pit` ✅ | Säulen-von-Helst (neu) | Inquisitor-General Vehren | `vehren` ✅ |
| 4 | Wurzelgrab | swamp | `swamp_ruins` ✅ | Knoten-Markt (neu) | Faden-Mutter Shulavh | `shulavh` (neu) |
| 5 | Spiegelstadt Velharn | astral | `astral_realm` ✅ | Spiegelhof (neu) | Drei-Zeiten-Boss | `velharn_trio` (neu) |
| 6a | Salzwunde | wound_salt (neu) | `wound_salt` (neu) | Drei-Wunden-Lager (neu) | Ertrunkene Königin | `ertrunkene_koenigin` (neu) |
| 6b | Aschwunde | wound_ash (neu) | `wound_ash` (neu) | (selbes Lager) | Echo-Drache | `echo_drache` (neu) |
| 6c | Hohlwunde | wound_hollow (neu) | `wound_hollow` (neu) | (selbes Lager) | Nicht-Gott | `nicht_gott` (neu) |
| 7 | Hohlwort | hollow_word (neu) | `hollow_word` (neu) | Drei Mütter (neu) | Im-Nesh der Hundertzüngige | `im_nesh` (neu) |

### 1.3 Welt-Connectivity (Reise-Modell)

- ✅ **Brassweir-Portale** = Akt-1-Krypta-Direktportal (crypt_lost) + freigeschaltete Outpost-Portale für alle anderen Akte. *Update #113: Outpost-Portal-Reihe südlich vom Spawn. Update #123: Akt-2-7-Dungeons-Direktportale aus Brassweir entfernt — Lore-konformer Flow `Brassweir → Outpost → Dungeon`. crypt_lost bleibt, weil Brassweir selbst der Akt-1-Hub ist.*
- ✅ Portal → **Vorposten-Camp** (klein, ~400×400 weltspace, 3–4 NPCs, kein Mauerring, Mahnmal-Stele am Eingang).
- ✅ Vorposten → **Akt-Dungeon** *Update #115: Nord-Rand jeder Outpost-Karte hat einen DungeonPortal zum lore-passenden Biome-Dungeon. Zhar-Eth→desert_temple, Echo-Markt→frost_palace, Säulen-von-Helst→lava_pit, Knoten-Markt→swamp_ruins, Spiegelhof→astral_realm, Drei-Wunden-Lager→crypt_lost. F-Interact betritt direkt. Multi-stage-Sub-Bereiche bleiben offen (separates Subprojekt).*
- ✅ **Mahnmal-Stelen** als Fast-Travel-Anker (zwischen freigeschalteten Outposts). *Update #114: TravelUI-Modal via F-Interact auf Outpost-Mahnmal — Click auf jedes freigeschaltete Ziel teleportiert. Brassweir-Mahnmal bleibt Aspekt-Schrein.*
- ✅ **NPC-Voice-Lines im Spiel** — Outpost-NPC-Toast zieht Lore-Quote aus `NPC_ROSTER[roster_key].voice_lines`. *Update #114.*
- [ ] **Reise-UI** als M-Modal-Erweiterung (Travel-Tab in Fullmap) — separates Subprojekt; aktuell Mahnmal-Stelen-Travel ausreichend.

---

## 2. NPC-ROSTER MASTER (alle Akte)

### 2.1 Brassweir (Persistenz-Hub) — schon da

- ✅ Korven Vor (vendor / Mahnmal-Gilde) [sf/town.py](sf/town.py)
- ✅ Mahnmal-Verwahrer (stash)
- ✅ Mara die Mahnerin (mystic)
- ✅ Otreth Hohlauge (smith / Gemcutter)
- ✅ Stadtsprecher Eldon (quest)
- ✅ Tameris (innkeeper, wandert in Akt 1b weiter)

> **Update #112 — NPC-Roster + Outpost-Daten in [sf/outposts.py](sf/outposts.py)**
> Alle 22 Roster-NPCs sind als Data-Definitions in `NPC_ROSTER` registriert
> (mit Role, Faction, Voice-Lines, Default-Position). Die 7 Outpost-Camps
> sind in `OUTPOSTS` definiert. Engine-Wire-Up (Akt-Portal-Spawning,
> `Game.enter_outpost`) folgt mit dem Quest-System-Sprint.

### 2.2 Zhar-Eth-Karawane (Akt 1b) — Daten ✓

- [x] **Schwester-Kommandantin Naveth** (quest) — `naveth`
- [x] **Mond-Priesterin Sheh** (mystic) — `sheh`
- [x] **Karawanen-Händlerin Yul** (vendor) — `yul`
- [ ] Tameris (wandert hierher in Akt 1b) — bleibt in `town.py`, optional als Schedule-Erweiterung

### 2.3 Echo-Markt (Akt 2) — Daten ✓

- [x] **Bruder Helst der Hundertjährige** (quest) — `helst`
- [x] **Senator-Geist Vorul** (vendor) — `vorul`
- [x] **Glasgolden-Schmied Athrek** (smith) — `athrek`
- [x] **Otreth-Lehrling Salir** (smith) — `salir`

### 2.4 Säulen-von-Helst (Akt 3) — Daten ✓

- [x] **Acolyt der Erblinden Kirche** (quest) — `acolyt_helst`
- [x] **Tribunal-Doppelagent Korren** (mystic) — `korren`
- [x] **Vehren-Gefangener Selvor** (quest) — `selvor`
- [x] **Asche-Händler Brulm** (vendor) — `brulm`

### 2.5 Knoten-Markt (Akt 4) — Daten ✓

- [x] **Vossharil die Dreimalige** (quest) — `vossharil`
- [x] **Wurzel-Apotheker Bran** (vendor) — `bran`
- [x] **Knochen-Hexe Marvel** (smith) — `marvel`
- [x] **Hohler Sohn** (mystic) — `hohler_sohn_npc`

### 2.6 Spiegelhof (Akt 5) — Daten ✓

- [x] **Erster Senator Voraius** (quest) — `voraius`
- [x] **Spiegel-Magierin Nheya** (mystic) — `nheya`
- [x] **Glasgolden-Händlerin Sehir** (vendor) — `sehir`
- [x] **Mara die Mahnerin (Reveal-Stage)** (quest) — `mara_velharn`

### 2.7 Drei-Wunden-Lager (Akt 6) — Daten ✓

- [x] **Mara die Mahnerin (Akt-6-Stage)** (quest) — `mara_wunden`
- [x] **Korven Vor ODER Helst** (mystic) — `korven_helst_reveal`
- [x] **Wunden-Lesende Tehrnal** (quest) — `tehrnal`

### 2.8 Hohlwort (Akt 7) — Daten ✓

- [x] **Die Drei Mütter** (mystic-Trias) — `drei_muetter`
- [x] **Mara die Mahnerin (Final-Stage)** (quest) — `mara_final`
- [x] **Im-Nesh's Echo-NPC** (mystic) — `im_nesh_echo_npc`

**Gesamt NPCs Roster: 25 (22 Roster + 3 Brassweir-Stamm via town.py). Engine-Wire-Up offen.**

---

## 3. QUEST-MASTER-LISTE (pro Akt: Haupt + Neben + Faction + Lore + Crafting + Bounty + Hidden)

### 3.1 Stage-Type-Erweiterungen NOTWENDIG

Aktuell in [sf/quest_data.py](sf/quest_data.py): TALK, KILL, REACH, COLLECT, INTERACT, RETURN.

> **Update #116 — Alle 6 neuen Stage-Types implementiert.**
> Engine-Foundation steht: `QuestState.tick(dt, game)`, `QuestLog.tick(dt)`
> in Game.update verdrahtet, Event-Handler `on_choice`/`on_puzzle_step`/
> `on_npc_arrived`, CONDITIONAL auto-skip in `advance_stage`.

- [x] **ESCORT** — NPC begleiten bis Zielpunkt (Tameris-Schwester ✓)
- [x] **DEFEND** — N Sekunden Position halten (Vossharil-Ritual ✓)
- [x] **PUZZLE** — Reihenfolge Altäre aktivieren (Velharn-Drei-Zeiten ✓)
- [x] **CHOICE** — Spieler-Wahl mit Konsequenz-Flag (`game.flags[name]=value` ✓)
- [x] **TIMED** — Stage in X Sekunden (Vergessens-Welle ✓, `fail_action`=revert|fail)
- [x] **CONDITIONAL** — Stage übersprungen wenn `requires_flag`-Bedingung nicht passt (Multi-Path-Support ✓)

### 3.2 Akt 1 — Die Salzküste (Brassweir-Hub)

| Quest-ID | Typ | Giver | Stages | Reward | Status |
|---|---|---|---|---|---|
| `akt1_salzwunde` | Main | Korven Vor | 6 | 200 Gold, 180 XP, Mahnmal-Marke VII | ✅ |
| `akt1_otreth_stein` | Crafting | Otreth | 3 | 80 Gold, 60 XP | ✅ |
| `akt1_mara_spur` | Lore | Mara | 3 | 120 Gold, 90 XP | ✅ |
| `akt1_tameris_schwester` | Escort/Hidden | Tameris | 5 (Talk+Escort+Choice+Conditional+Return) | 150 Gold, 120 XP | ✅ #116 |
| `akt1_tribunal_geruecht` | Faction | Eldon | 3 (Kill 5 Tribunal-Spähen, return) | Tribunal-Rep -10, Mahnmal-Gilde-Rep +20 | [ ] |
| `akt1_bounty_salzgekreuzte` | Bounty (Repeatable) | Eldon | 1 (10 kills) | 60 Gold/Run | [ ] |
| `akt1_versunkenes_grab` | Hidden | (Decor-Trigger) | 3 (Find + Decode + Boss-Mini) | 100 Gold, Lore-Codex-Entry | [ ] |

### 3.3 Akt 1b — Zhar-Eth (Desert, optional)

- [ ] `akt1b_speerschwester_aufnahme` — Main (Schwester-Trial: 3 Mob-Kills + Spear-Demo)
- [ ] `akt1b_mondbund` — Faction (Speerschwestern-Rep)
- [ ] `akt1b_wandernde_karawane` — Lore (Karawanen-Spuren finden)
- [ ] `akt1b_bounty_wuestenwesen` — Bounty

### 3.4 Akt 2 — Glasgoldene Ruinen (Echo-Markt-Hub)

- [x] `akt2_asch_prophezeiung` — Main (Helst gibt — Senator-Geist-Boss) ✅ #152
- [ ] `akt2_helst_pact_stones` — Faction (Erblinde Kirche)
- [ ] `akt2_echo_handel` — Side (Senator-Geist-Vendor freischalten)
- [ ] `akt2_otreth_glas_gravur` — Crafting (Glas-Gem schleifen)
- [ ] `akt2_goldstaub_erinnerung` — Lore (Goldstaub-Echo-Events sammeln)
- [ ] `akt2_bounty_goldstaub_diener` — Bounty
- [ ] `akt2_velharn_vorhof` — Hidden (Spiegel-Tor finden vor Akt 5)

### 3.5 Akt 3 — Aschenfelder (Säulen-von-Helst-Hub)

- [x] `akt3_asch_pakt` — Main (Vehren-Boss) ✅ existiert
- [ ] `akt3_erblinder_priester_trial` — Faction (Erblinde Kirche, ja/nein zur Augen-Bind-Probe)
- [ ] `akt3_letzte_legion` — Side (Asch-Soldaten-Aufgabe an die Toten-Ruhe)
- [ ] `akt3_tribunal_infiltration` — Hidden (heimlich Tribunal-Lager durchsuchen)
- [ ] `akt3_bounty_asch_wolf` — Bounty
- [ ] `akt3_valsa_traene` — Lore (3 Asche-Stelen lesen)
- [ ] `akt3_inquisitions_klinge` — Crafting (Tribunal-Stahl schmelzen)

### 3.6 Akt 4 — Wurzelgrab (Knoten-Markt-Hub)

- [x] `akt4_shulavh_faden` — Main (Choice: Heilen oder Bezwingen) ✅ #152
- [ ] `akt4_knochenwitwen_aufnahme` — Faction (Vossharil-Trial)
- [ ] `akt4_hohle_sohn` — Side (Hohlen Sohn folgen, Lore-Reveal)
- [ ] `akt4_drei_tode` — Lore (Vossharils Drei-Tode-Geschichte zusammensetzen)
- [ ] `akt4_wurzel_gift` — Crafting (Sumpf-Brauen)
- [ ] `akt4_bounty_fadengebundene` — Bounty
- [ ] `akt4_versteckter_garten` — Hidden (Saatträger-Geheim-Hain)

### 3.7 Akt 5 — Spiegelstadt Velharn (Spiegelhof-Hub)

- [~] `akt5_drei_zeiten` — Main (Puzzle ✓ #116 — Drei-Zeiten-Altar-Sequenz Glasgolden→Götterkrieg→Gegenwart, Bosse + Ousen-Reveal noch offen)
- [ ] `akt5_senator_streit` — Side (Senatoren-Mediation, Choice)
- [ ] `akt5_stunden_spiegel_meister` — Faction (Spiegel-Magier-Aufnahme)
- [ ] `akt5_velharn_geschichte` — Lore (Glasgolden vs Götterkrieg vs Gegenwart Tafeln)
- [ ] `akt5_bounty_stunden_wandler` — Bounty
- [ ] `akt5_korven_oder_helst` — Hidden (Reveal-Setup für Akt 6 — wer ist Im-Nesh?)

### 3.8 Akt 6 — Drei Wunden (Wunden-Lager-Hub)

- [ ] `akt6_salzwunde_lesen` — Main (Ertrunkene Königin)
- [ ] `akt6_aschwunde_lesen` — Main (Echo-Drache)
- [ ] `akt6_hohlwunde_lesen` — Main (Nicht-Gott)
- [ ] `akt6_pakt_uebersetzen` — Main-Finale (Übergabe Tehrnal)
- [ ] `akt6_korven_helst_reveal` — Choice (Wer ist Im-Nesh in Disguise?)
- [ ] `akt6_bounty_anomalien` — Bounty

### 3.9 Akt 7 — Hohlwort (Drei-Mütter-Hub)

- [ ] `akt7_drei_muetter_trial` — Ascendancy (3 Trial-Dungeons)
- [ ] `akt7_im_nesh_dialog` — Main (Pre-Fight Dialog mit 3 Optionen)
- [ ] `akt7_im_nesh_boss` — Main (3-Phasen-Boss)
- [ ] `akt7_finale_wahl` — Choice (3 Endings):
  - **Pakt erneuern** — Welt überlebt aber Spieler verschwindet (Hohle Geweihte)
  - **Pakt umschreiben** — Im-Nesh-Path, Spieler regiert
  - **Aithein wecken** — Letzter-Träumer-Reveal, leere weiße Welt

**Gesamt-Quests: 6 ✅ + 45 [ ] = 51 Quests im Voll-Ausbau.** *(Update #152: +akt2_asch_prophezeiung, +akt4_shulavh_faden — Akt 1-5 Main-Spine vollständig)*

---

## 4. BOSS-ENCOUNTERS MASTER (BOSS_ENCOUNTERS-Registry erweitern)

Status pro Encounter aus [sf/boss_encounter.py](sf/boss_encounter.py) `BOSS_ENCOUNTERS`:

- [x] `salzhueter_brut` (Akt 1)
- [x] `senator_geist` (Akt 2) — Update #111, frost-Biome Tier 1+. ASSEMBLE-Spawn, 3 Phase-Quotes, spawnt Goldstaub-Diener-Adds in Phase 3.
- [x] `vehren` (Akt 3)
- [x] `shulavh` (Akt 4) — Update #111, swamp-Biome Tier 1+. RISE_FROM_GRAVE-Spawn. Phase-Quotes folgen Lore-Bibel Mütterlich→Wahnsinnig→Vergessend-Bogen. Choice-Outcome (Heilen/Bezwingen) folgt mit Akt-4-Quest-System.
- [x] `velharn_trio` (Akt 5) — Update #111, astral-Biome Tier 1/2 (Tier 3 → nicht_gott). PORTAL-Spawn, 3-Köpfe-3-Zeiten Phase-Quotes.
- [x] `ertrunkene_koenigin` (Akt 6a) — Update #110, Bestiarium #26
- [x] `echo_drache` (Akt 6b) — Update #110, Bestiarium #27
- [x] `nicht_gott` (Akt 6c) — Update #110, Bestiarium #28
- [ ] `tameris_trial` (Akt 1b optional)
- [ ] `im_nesh` (Akt 7) — Bestiarium-Final (3 Phasen, 3 Endings)
- [ ] `aspekt_echo_kharn` (Endgame)
- [ ] `aspekt_echo_nheyra` (Endgame)
- [ ] `aspekt_echo_valsa` (Endgame)
- [ ] `aspekt_echo_ousen` (Endgame)
- [ ] `aspekt_echo_shulavh` (Endgame)

Pro neuem Encounter braucht es: `spawn_method`, `intro_duration`, `intro_audio`, `lore_quote`, `phase_thresholds`, `phase_quotes` (aus VELGRAD_VOICE_LINES_POOL), `music_swap`, `title`. Boss-Fairness-Hausregel: **LOS + Range für jeden Special + sichtbar auf Map (POE2-Style)**.

---

## 5. ITEM-SYSTEM MASTER

### 5.1 Slot-Architektur — bereits da

[sf/constants.py](sf/constants.py) `SLOTS`: weapon, helmet, chest, ring, amulet, offhand.

- [ ] **Slot-Erweiterung erwägen:** `boots`, `gloves`, `belt`, `flask_modifier`. Vier weitere Slots heben die Build-Diversität deutlich (POE2-Niveau).

### 5.2 Rarity-Tiers — bereits da

- common 70 % / magic 22 % / rare 7 % / unique 1 % → ergänzen um:
  - [ ] **set** (Item-Set-Drops, 0.3 %) — Sets aus [sf/constants.py](sf/constants.py) `ITEM_SETS` brauchen eigenen Rarity-Slot
  - [ ] **corrupted** (Atlas-only, Modifier-permanent) — Endgame
  - [ ] **mythic** (Quest-Items + X-Tier-Uniques aus VELGRAD_ITEMS_UNIQUE_BIBEL — 8 Stück gekennzeichnet als [X])

### 5.3 Unique-Items aus VELGRAD_ITEMS_UNIQUE_BIBEL (50 Stück)

Pro Unique brauchts einen **legalen Drop-Pfad**. Aktuell teils via `ITEM_SETS` in `constants.py`. Volle Drop-Map:

| Kategorie | Anzahl | Drop-Pfad |
|---|---|---|
| **Maces** (Warrior) | 5 | Boss 1, Akt-3-Boss, Akt-1-Quest-Reward, ... |
| **Swords** | 4 | Akt-2-Boss-Drop, Vendor-Helst, etc. |
| **Axes** | 3 | Akt-4-Drop, Saatträger-Quest, Brassweir-Vendor |
| **Daggers** | 4 | Vossharil-Quest, Hidden-Quest, Akt-7-only („Tintendolch") |
| **Spears** | 5 | Tameris-Quest-Chain, Zhar-Eth-Faction-Vendor, Boss-Drops |
| **Quarterstaves** | 5 | Stille-Schritte-Faction, Mönchs-Pagoden, „Letzter Schritt" Akt-7-only |
| **Bows** | 4 | Saatträger-Hidden-Hain, „Der Unbeschriebene" Mythic-Quest |
| **Crossbows** | 5 | Korven-Drops, Mahnmal-Gilde-Vendor, „Mahnmal-Marke VII" als Quest-Reward (✅ Akt 1) |
| **Wands** | 3 | Echo-Markt-Vendor, Funkengeborene-Quest, Im-Nesh-Drop |
| **Sceptres** | 3 | Helst-Vendor, Akt-5-Quest, Otreth-Crafting-Endgame |
| **Staves** | 4 | „Sieben-Atem-Stab" Endgame, Glasgolden-Vendor, Wurzelgrab-Drop |
| **Talismans** (Druid) | 3 | Druiden-Quest-Reward, Akt-4-Boss, Akt-7-only |

- [ ] **Drop-Pool-Definition** pro Boss/NPC: Liste der erlaubten Uniques + Drop-Chance.
- [ ] **Quest-Item-Flagging**: Mythics dürfen NICHT random droppen, nur als Quest-Reward.

### 5.4 Affix-System

[sf/constants.py](sf/constants.py) `AFFIXES` — vorhanden, aber sehr generisch.

- [ ] **Lore-Affixes** pro Aspekt einbauen:
  - `kharns_form` (Phys +X %, Form-Tag)
  - `nheyras_zeit` (CDR +X %, Zeit-Tag)
  - `ousens_blick` (Crit Mult +X %, Geist-Tag)
  - `valsas_wille` (Fire +X %, Wille-Tag)
  - `im_neshs_sprache` (Chaos +X %, Sprache-Tag — selten + corrupted)
  - `shulavhs_faden` (Bindung — verbindet 2 Slots = Set-Mechanik)
  - `siebter_atem` (Random-Affix-Würfel beim Equip)
- [ ] **Tag-System auf Items**: Affix bekommt Aspekt-Tag, Mahnmal-Pakt (W-13) buffed Tag-Matches.

### 5.5 Crafting-System

[sf/crafting.py](sf/crafting.py) — Aufwerten / Umrollen / Verzaubern / Salvage existieren.

- [ ] **Aspekt-Engraving** — Otreth kann auf Unique einen Aspekt-Tag einbrennen (Kosten: Mahnmal-Marke + Gold).
- [ ] **Set-Linking** (Shulavhs Faden) — zwei Items zu Set-Paar binden, beim Equip beider greift Set-Bonus.
- [ ] **Corruption** (Atlas-only) — Vegas-Trade: hohes Risk, hoher Reward.
- [ ] **Gemcutting** (J-10 ✅ existiert) — Otreth-Modal Engrave/Levelup.
- [ ] **Recipe-Hinweise** pro Akt freigeschaltet:
  - Akt 1: Aufwerten + Salvage
  - Akt 2: Umrollen + Glas-Gem-Gravur
  - Akt 3: Tribunal-Stahl (Schmelzen)
  - Akt 4: Wurzel-Gift (Brauen)
  - Akt 5: Spiegel-Reflektion (Item-Klon, 1× pro Char)
  - Akt 6: Aspekt-Engraving
  - Akt 7: Corruption

### 5.6 Item-Bibliothek aus dem Bestiarium-Drop-Pool

Jeder der 30 Mobs hat im VELGRAD_BESTIARIUM einen Drop. Diese Drops müssen in [sf/enemies.py](sf/enemies.py) / [sf/bestiary.py](sf/bestiary.py) als Loot-Table befüllt sein.

- [ ] **Drop-Table-Audit** pro Mob: ist der Bestiarium-Drop im Code? Aktuell nur sporadisch.

---

## 6. CURRENCY-FLOW MASTER

| Currency | Source | Sink | Engine-Anker | Status |
|---|---|---|---|---|
| **Gold** | Mob-Drops, Loot-Verkauf, Quest-Reward | Vendor, Repair, Crafting-Fee, Inn-Refill | [sf/shop.py](sf/shop.py) | ✅ |
| **Mahnmal-Marken I–VII** | Boss-Drops, Quest-Reward, Lore-Altar | Mahnmal-Schrein (W-13), Atlas-Currency | [sf/progression.py](sf/progression.py) | ✅ |
| **Uncut Memory-Shards** | Boss/Mini-Boss-Drop | Otreth Gemcutter (J-10) | [sf/items.py](sf/items.py) | ✅ |
| **Orbs of Regret** | Boss/Elite-Drop | Respec Skill-Tree (H-17) | [sf/progression.py](sf/progression.py) | ✅ |
| **Faction-Rep** | Faction-Quest-Reward, Faction-Mob-Kill | Faction-Vendor-unlock, exclusive Skill-Gems, Title | [sf/faction.py](sf/faction.py) | ✅ #117 |
| **Memory-Fragments** (NEU) | Lore-Tafeln + Codex-Entries | Otreth-Lore-Trade, Skill-XP-Boost, Unique-Item-Reroll | (neu) | [ ] |
| **Atlas-Stones** (NEU) | Endgame-Boss-Drops | Map-Tier-Up, Modifier-Roll, Atlas-Tree-Punkte | (neu) | [ ] |
| **Aithein-Fragment** (NEU) | Final-Boss-Drop only | Endgame-Aithein-Quest-Chain | (neu) | [ ] |

### 6.1 Faction-Rep-Detailspezifikation

> **Update #117 — Foundation komplett implementiert in [sf/faction.py](sf/faction.py).**
> 7 Fraktionen, 8 Tiers (-3 Verflucht .. +4 Geweiht), 21 Tier-Unlocks
> (3 pro Fraktion bei +50/+100/+200), volle Konflikt-Matrix, Quest-
> Reward-Integration, Save/Load.
>
> **Update #118 — Faction-Status-UI als Codex-Tab #5 „Fraktionen".**
> Player drückt N → Codex → Tab 5: alle 7 Fraktionen mit Lore-Name,
> Aspekt-Lineage, Rep-Bar (-200..+200 mit Threshold-Markern bei +50/
> +100/+200), aktuellem Tier-Label, nächstem Unlock und Status. 2-Spalten-
> Grid für kompakte Übersicht. Vendor-Unlock-Wire-Up folgt als Subprojekt.

Sieben Fraktionen aus VELGRAD_LORE_BIBEL Teil 6:

| Fraktion | Rep-Gewinn | Rep-Verlust | Unlocks bei +50 / +100 / +200 |
|---|---|---|---|
| Mahnmal-Gilde | Korven-Quest, Loot-Verkauf | — | Vendor-Discount / Exklusive Crossbows / Korven-Endgame-Quest |
| Erblinde Kirche | Helst-Quest, Augen-Bind-Probe | Tribunal-Quest | Pact-Stones / Exklusive Sceptres / Aspekt-Wahl |
| Tribunal der Asche | Vehren-Hilfsquest (alternative Akt-3-Path) | Erblinde-Quest, Witch-Spielen | Inquisitions-Klinge / Tribunal-Konstrukt-Begleiter |
| Saatträger | Ranger-Hain-Quest | Tribunal-Quest | Saatkind-Bow / Wandelnde-Form-Slot |
| Knochenwitwen | Vossharil-Quest | Erblinde-Quest, Tribunal-Quest | Vossharils-Bruder-Dagger / Skelett-Familiar |
| Speerschwestern | Tameris-/Zhar-Eth-Quest | — | Zhar-Eth-Mondbinder-Spear / Schwestern-Faden-Buff |
| Stille Schritte | Monk-Pagoden-Quest | — | Quarterstaff-Drei-Pagoden / Atem-Disziplin-Passive |

Konflikt-Matrix: Erblinde ↔ Tribunal ↔ Knochenwitwen sind drei-Wege-Konflikt. Tribunal +20 = Erblinde −10 = Knochenwitwen −10.

---

## 7. WELT-ELEMENTE PRO DUNGEON (Pflicht-Check-Liste)

Jeder Akt-Dungeon braucht:

- [ ] Eingangsraum mit Region-Name-Overlay
- [ ] 3–5 Lore-Tafeln (`lore_tablet`) aus `LORE_TABLETS[biome]`
- [ ] 1–2 Mahnmal-Stelen (Fast-Travel + Save-Point)
- [ ] 1 Altar / Rune-Circle (Pre-Boss-Buff)
- [ ] 1 Treasure-Room (W-08 ✅ existiert)
- [ ] 1 Library/Lore-Room (Akt 2 + 5 zwingend, Rest optional)
- [ ] Boss-Room mit Per-Biome-Focal-Anchor (W-06 ✅)
- [ ] Boss-Lore-Tablet (W-07 ✅)
- [ ] Quest-NPC-Spawn-Slots (für Escort/Defend-Quests)
- [ ] 2–3 interaktive Decor-Objekte (Lore- oder Item-Drop)
- [ ] Mindestens 2 Mob-Archetypen aus Bestiarium (kein generisches Zombie)
- [ ] Multi-Stage-Sub-Bereiche (3–4 Areas pro Akt-Dungeon, Akt ≥ 2)

### 7.1 Multi-Stage-Dungeon-Templates (Akt ≥ 2)

- **Akt 4 Wurzelgrab:** Außen-Wurzeln → Kambium-Höhle → Mark-Kammer → Faden-Mutter-Arena
- **Akt 5 Velharn:** Glasgolden-Vorhalle → Götterkrieg-Schlachtfeld → Gegenwart-Senat-Halle → Drei-Zeiten-Arena
- **Akt 6:** Drei separate Mini-Dungeons (Salzwunde / Aschwunde / Hohlwunde) je 2 Stages
- **Akt 7:** Hohlwort-Vestibül → Stille-Zone → Hundertsprachen-Kammer → Im-Nesh-Arena

---

## 8. WELT-EVENTS (für lebendige Welt)

Aus [sf/dungeon_events.py](sf/dungeon_events.py) — derzeit generic, lore-spezifisch ergänzen:

- [ ] **Vergessens-Welle** — Bereich wird kurz transparent, Mobs verschwinden + Mara-Voice-Line
- [ ] **Echo-Sturm** — Boss-Room-Variation: Mobs aus 2 Akten gleichzeitig
- [ ] **Vergessens-Pakt-Event** — Nach 5 Kills in 10 s → Mahnmal-Marke I als Bonus
- [ ] **Tribunal-Patrouille** (Akt 3+) — Inquisitions-Trupp blockt Weg
- [ ] **Speerschwester-Sichtung** (Akt 1b/4) — Tameris-Schwester-Hidden-Quest-Trigger
- [ ] **Stille-Zone** (Akt 5+) — 80×80 Zone ohne Sound, unsichtbare Mobs
- [ ] **Goldstaub-Echo** (Akt 2) — Memory-Fragment-Drop-Event
- [ ] **Drei-Wunden-Resonanz** (Akt 6) — Wunden-Pulsieren während Combat → Damage-Boost
- [ ] **Im-Nesh-Whisper** (Akt 5+) — Random Voice-Line die fragt „Hast du Korven heute schon vertraut?"

---

## 9. ENDGAME-ATLAS (Welkende Welten)

Lore: VELGRAD_LORE_BIBEL Teil 4.2 + 11.5.

### 9.1 Atlas-UI

- [ ] **Atlas-Modal** als neuer Tab in Fullmap (M-Modal Erweiterung)
- [ ] **Map-Pool** 20+ Welkende Welten, jede ist Echo einer Akt-1..7-Region
- [ ] **Map-Tier** 1–16, Drop-Skalierung pro Tier
- [ ] **Map-Modifier** (random pro Map, 2–5 Stück):
  - „+50 % Mob-Damage"
  - „Vergessens-Welle alle 30 s"
  - „Im-Nesh-Echo-Spawns"
  - „Drei-Wunden überlappen" (Cross-Biome-Mobs)
  - „Stille Zone überall" (Audio aus)
  - „Time-Slip" (Mobs aus 3 Akten gleichzeitig)
- [ ] **Atlas-Tree** — passive Punkte (gefüllt mit Endgame-Marken)
- [ ] **Pinnacle-Bosse:**
  - [ ] Aithein-Echo (Mythic, alle 5 Aspekt-Echos vorher)
  - [ ] Im-Nesh-Reborn (Hardmode-Akt-7)
  - [ ] Der-Achte (Lore 11.4 — fehlende Aspektin)
  - [ ] Der-Letzte-Träumer (Lore 11.6 — Aithein-Player-Reveal)

---

## 10. PROGRESSION-GATES (Quest-Flag-gegated)

Aktuell nur `level_req` in `DUNGEONS`. Notwendig: Quest-Flag-Gates.

- [ ] Akt 1 → 2: Flag `quest_completed.akt1_salzwunde`
- [ ] Akt 2 → 3: Flag `quest_completed.akt2_asch_prophezeiung` + Helst-Pact-Stone equipped
- [ ] Akt 3 → 4: Flag `quest_completed.akt3_asch_pakt` + Asche-Aspekt-Wand owned
- [ ] Akt 4 → 5: Flag `quest_completed.akt4_shulavh_faden` + Choice-Outcome
- [ ] Akt 5 → 6: Flag `quest_completed.akt5_drei_zeiten` + Ousen-Reveal seen
- [ ] Akt 6 → 7: Alle drei Wunden gelesen (`flag.wound_salt_read` + `flag.wound_ash_read` + `flag.wound_hollow_read`)
- [ ] Endgame freigeschaltet: `flag.akt7_finished`

Save-Versioning (Z-03) muss `flags`-Dict persistieren.

---

## 11. DREI ENDINGS (Akt-7-Wahl)

Lore 8.4. Choice-System nötig (siehe 3.1 CHOICE-Stage-Type).

- [ ] **Ending A — Pakt erneuern (Sacrifice)**: Spieler wird zur Hohlen Geweihten. Welt überlebt, Spieler verschwindet aus Save (Char wird Memorial-Eintrag).
- [ ] **Ending B — Pakt umschreiben (Im-Nesh-Path)**: Spieler tritt in Im-Neshs Fußstapfen. Endgame-Modus „Verräter-Tour" freigeschaltet (eigener Atlas).
- [ ] **Ending C — Aithein wecken**: Letzter-Träumer-Reveal. Weiße Welt + Ousen-Voice-Line. Endgame-Modus „Träumer-Pfad" — Atlas mit überschriebenen Maps.

---

## 12. ENGINE-FUNKTIONEN — Audit „funktioniert das alles?"

### 12.1 Quest-System-Engine

- [x] Quest-State-Machine (`QuestState.advance_stage`) — vorhanden in [sf/quests.py](sf/quests.py)
- [x] Quest-Tracker-UI (G-12) — Banner-Notification ✅
- [x] Quest-Log-Modal — ✅
- [x] Quest-Compass-Marker (B-16) — Stern + Edge-Arrow ✅
- [ ] **Stage-Types erweitern** (ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL)
- [ ] **Choice-Consequence-Flags** in Save
- [ ] **Quest-Branching** (mehrere Outcomes, eine Quest)
- [ ] **Repeatable-Bounty-Reset** (daily/per-run)
- [ ] **NPC-Quest-Dialog-Modal** (mit Portrait + Choice-Buttons)

### 12.2 NPC-Engine

- [x] NPC-Klasse mit `kind` (vendor/mystic/smith/quest/innkeeper/stash) ✅
- [x] NPC-Schedule day/night (W-11) ✅
- [ ] **NPC-Dialog-Modal** mit Portrait (T-07) + Voice-Line + Branch-Optionen
- [ ] **NPC-Movement-Pfade** zwischen Akten (Tameris reist mit, Otreth-Lehrling spawnt in Echo-Markt)
- [ ] **NPC-Mood-System** abhängig von Faction-Rep (z. B. Helst spricht anders je nach Tribunal-Rep)
- [ ] **NPC-Memory** — NPC erinnert sich an Spieler-Choices

### 12.3 Item-Engine

- [x] Item-Klasse mit slots, affixes, sockets — [sf/items.py](sf/items.py) ✅
- [x] Rarity-Roll (`RARITY_WEIGHTS`) ✅
- [x] Affix-Pool ✅
- [x] Item-Compare-Deltas (G-17) ✅
- [x] Inventory-Stats-Panel (G-18) ✅
- [ ] **Unique-Drop-Pool pro Boss/NPC** (Loot-Table)
- [ ] **Quest-Item-Flag** (verhindert Salvage/Verkauf)
- [ ] **Set-Linking** (Shulavhs Faden)
- [ ] **Corruption** (Atlas-Item-Modifier)
- [ ] **Aspekt-Engraving** in Crafting

### 12.4 Boss-Engine

- [x] `BOSS_ENCOUNTERS`-Registry ✅
- [x] Phase-Threshold-System (E-06) ✅
- [x] Cinematic-Intro (E-02) ✅
- [x] Arena-Features (E-05/E-11) ✅
- [ ] **13 fehlende Boss-Encounters** (siehe Sektion 4)
- [ ] **Choice-Outcome-Bosses** (Shulavh, Im-Nesh)
- [ ] **3-Zeiten-Boss-Mechanik** (Akt 5)
- [ ] **Pinnacle-Boss-Tier** (Endgame-Atlas)

### 12.5 Town/Hub-Engine

- [x] Brassweir-Layout (W-01) ✅
- [x] Decor-Kinds (W-02) ✅
- [x] Per-Biome-Dungeon-Decor (W-04) ✅
- [x] Mahnmal-Schrein-Pakt (W-13) ✅
- [ ] **`town.py` generalisieren** zu `town_by_key(town_key)` mit 7 verschiedenen Hub-Layouts
- [ ] **Fast-Travel-System** zwischen Mahnmal-Stelen
- [ ] **Vorposten-Camp-Generator** (kleinerer Town-Subset)

### 12.6 Welt-Reise

- [ ] **Travel-UI** in Fullmap-Modal als Tab
- [ ] **Waypoint-Unlock-Flag** pro Mahnmal-Stele
- [ ] **Region-Übergangs-Animation** (B-18, schon im PLAN ergänzt)
- [ ] **Multi-Stage-Dungeon-Übergänge** (Sub-Area-Loading)

### 12.7 Faction-Engine

- [ ] **`Player.faction_rep`** Dict (7 Fraktionen)
- [ ] **Rep-Gain-Hooks** in Quest-Reward + Mob-Kill-Reward
- [ ] **Faction-Vendor-Unlock-Logik**
- [ ] **Konflikt-Matrix** (Quest A in Faction X = Rep-Verlust in Y)
- [ ] **Faction-UI** im Codex (neuer Tab)

### 12.8 Cutscene-Engine

- [ ] **Cutscene-Framework** (X-09, schon im PLAN) für Akt-Übergänge + Reveals
- [ ] **9 Pflicht-Cutscenes:**
  - Akt-1-Intro (Schiffbruch)
  - Akt-2-Helst-Pact
  - Akt-3-Vehren-Reveal
  - Akt-4-Shulavh-Choice
  - Akt-5-Ousen-Reveal
  - Akt-6-Korven-oder-Helst-Reveal
  - Akt-7-Im-Nesh-Dialog
  - Ending-A/B/C (drei separate)

### 12.9 Endgame-Engine

- [ ] **Atlas-Modal**
- [ ] **Map-Pool-Generator**
- [ ] **Map-Modifier-Pool**
- [ ] **Atlas-Tree-UI**
- [ ] **Pinnacle-Boss-Spawning**
- [ ] **Atlas-Currency-Sinks**

---

## 13. PHASEN-PLAN (Reihenfolge der Implementierung)

### Phase 1 — Akt-1 vollständig (Foundation, 4–6 Wochen)
1. [ ] Quest-Stage-Types ESCORT + CHOICE einbauen
2. [ ] Faction-Rep-Foundation (`Player.faction_rep` + 7 Fraktionen)
3. [ ] 4 fehlende Akt-1-Quests (Tameris-Schwester / Tribunal-Gerücht / Salzgekreuzte-Bounty / Versunkenes-Grab)
4. [ ] Zhar-Eth-Karawane (Vorposten-Camp + 3 NPCs + 4 Sub-Quests)
5. [ ] NPC-Dialog-Modal mit Portrait
6. [ ] Akt-1-Cutscene (Schiffbruch-Intro)
7. [ ] Akt-1-Crypt-Multi-Stage (2 Sub-Areas)
8. [ ] Quest-Flag-Gating Akt 1 → 2

### Phase 2 — Akt-2 + 3 (Tribunal/Erblinde-Konflikt, 6–8 Wochen)
1. [ ] `frost` → `glass_ruins` Rename + neue Tile-Set
2. [ ] Echo-Markt + Säulen-von-Helst Vorposten-Camps
3. [ ] Helst + Tribunal-NPCs
4. [ ] 14 Akt-2/3-Quests
5. [ ] Senator-Geist-Boss
6. [ ] Akt-2/3-Cutscenes
7. [ ] Faction-Konflikt-Matrix aktiv

### Phase 3 — Akt-4 + 5 (Wurzelgrab + Velharn, 8–10 Wochen)
1. [ ] Knoten-Markt + Spiegelhof
2. [ ] Vossharil + Geist-Senatoren als NPCs
3. [ ] Shulavh-3-Phasen-Boss mit Choice
4. [ ] Drei-Zeiten-Boss (Akt 5)
5. [ ] Drei-Zeiten-Mechanik (Zeit-Slice-Toggle)
6. [ ] Ousen-Reveal-Cutscene
7. [ ] 14 Akt-4/5-Quests

### Phase 4 — Akt-6 + 7 + Endgame (Drei Wunden + Hohlwort + Atlas, 10–12 Wochen)
1. [ ] Drei neue Biomes (wound_salt / wound_ash / wound_hollow)
2. [ ] Akt-7-Biome (hollow_word)
3. [ ] 4 Wunden-Bosse + Im-Nesh-Boss
4. [ ] Drei-Mütter-Trial-System
5. [ ] Drei Endings + Save-Branching
6. [ ] Atlas-Modal + Map-Pool + Atlas-Tree
7. [ ] 5 Pinnacle-Bosse

---

## 14. SOFORT-GAPS (was JETZT fehlt, codegestützt verifiziert)

Direkt aus `town.py` / `quest_data.py` / `boss_encounter.py` / `regions.py` / `constants.py` ablesbar:

- [ ] Bruder Helst nicht als NPC instanziiert
- [ ] Vossharil nicht als NPC
- [ ] Vehren existiert nur als Quest-Target, nicht als Pre-Fight-NPC
- [ ] Drei Mütter komplett fehlend
- [ ] Echo-Markt / Säulen-von-Helst / Knoten-Markt / Spiegelhof als Town-Layouts fehlen
- [ ] 13 BOSS_ENCOUNTERS fehlen (siehe Sektion 4)
- [ ] Akt 6 hat kein eigenes Biome
- [ ] Akt 7 hat kein eigenes Biome
- [ ] 6 Stage-Types fehlen (ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL)
- [ ] Faction-Rep-System komplett fehlend
- [ ] Atlas-System komplett fehlend
- [ ] Waypoint/Fast-Travel-System nicht implementiert (Stelen sind nur Decor)
- [ ] Quest-NPC-Spawning IN Dungeons fehlt
- [ ] Multi-Stage-Dungeons fehlen (alles ist Single-Map)
- [ ] Quest-Board-Modal fehlt (Eldon ist NPC ohne UI)
- [ ] `frost_palace` vs Lore-Akt-2-Glas-Look (Biome-Mismatch)
- [ ] Akt-Gating an Quest-Flag fehlt (nur Level-Req aktiv)
- [ ] 47 Quests fehlen (4 ✅, 47 [ ])
- [ ] 22 NPCs fehlen (6 ✅, 22 [ ])
- [ ] 4 zusätzliche Slot-Typen erwägen (boots/gloves/belt/flask_modifier)
- [ ] Aspekt-Affixes (7 Stück, Lore-getreu)
- [ ] Drei Endings + Choice-Branching im Save

---

## 15. WORKFLOW-REGELN (für Arbeit AN diesem Dokument)

1. **Bei Task-Abschluss:** Checkbox `[x]` setzen + Eintrag in [CHANGELOG.md](CHANGELOG.md).
2. **Bei Konflikt mit Lore:** Quellen-Hierarchie aus Sektion 0 beachten — Lore-Bibel sticht alle.
3. **Bei Engine-Drift:** Sektion 12 ist die Engine-Audit-Tabelle — wenn dort etwas neu ✅ wird, das alte System verbessern.
4. **Bei neuen NPCs:** Sektion 2 ergänzen + VOICE_LINES_POOL prüfen ob Voice-Pool existiert; falls nicht: dort ergänzen.
5. **Bei neuen Items:** Sektion 5.3 Drop-Pfad festlegen + Item-Eintrag in VELGRAD_ITEMS_UNIQUE_BIBEL verifizieren.
6. **Bei neuen Quests:** Sektion 3 Tabelle + [sf/quest_data.py](sf/quest_data.py) Eintrag + `ALL_QUESTS`-Liste.
7. **Bei neuen Bossen:** Sektion 4 Liste + [sf/boss_encounter.py](sf/boss_encounter.py) BOSS_ENCOUNTERS + Bestiarium-Lore-Quote.
8. **Bei Boss-Fairness:** Memory-Hausregel — LOS + Range + auf Map sichtbar (POE2-Style).
9. **Bei Endgame-Tasks:** Erst Phase 1–3 fertig, sonst Tech-Debt unbeherrschbar.
10. **Bei Cutscenes:** X-09-Framework zuerst, danach 9 Pflicht-Cutscenes aus Sektion 12.8.

---

## 16. EMPFOHLENE NÄCHSTE 3 SCHRITTE (konkret startbar)

1. **Quest-Stage-Type CHOICE einbauen** in [sf/quests.py](sf/quests.py) — ist Foundation für 60 % der noch fehlenden Quests. Schema: `stage['choices'] = [{'label': 'Schonen', 'flag': 'shulavh_spared'}, {'label': 'Bezwingen', 'flag': 'shulavh_defeated'}]`.

2. **Faction-Rep-Foundation** in [sf/entities.py](sf/entities.py) `Player.faction_rep = {'mahnmal': 0, 'erblinde': 0, 'tribunal': 0, 'saattraeger': 0, 'knochenwitwen': 0, 'speerschwestern': 0, 'stille_schritte': 0}` + Save-Migration in [sf/save.py](sf/save.py).

3. **Akt-1-Vervollständigung** — 4 fehlende Akt-1-Quests aus Sektion 3.2 in [sf/quest_data.py](sf/quest_data.py) hinzufügen. Sofort spielbar, kein neues Biome nötig.

Danach ist Akt-1 narrative komplett, Player kann sich an einem geschlossenen Loop „satt spielen" — und Phase 2 hat die Foundation.
