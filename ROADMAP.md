# ROADMAP — Priorisierte naechste Schritte

> **Zweck.** Synthese aus [PLAN.md](PLAN.md) (Engine-Tasks A-AA) + [WELT_AUFBAU.md](WELT_AUFBAU.md) (Content-Gaps Akt 2-7) + [QUEST_BIBEL.md](QUEST_BIBEL.md) (53 Quests). PLAN.md ist Update-Historie (#1-#151+), diese Datei ist der **Was-kommt-als-naechstes-Plan**.
>
> **Stand:** 2026-05-23, nach Update #151 (Quest-Progression-Fix + Settings-Persistence + Class-VFX).
> **Repo:** https://github.com/OsuGerman/shadowfall
>
> **Lese-Konvention:** Tiers sind Prioritaets-Cluster, nicht zwingend strikt sequentiell. Innerhalb eines Tiers koennen mehrere Tasks parallel laufen.

---

## STATUS-SNAPSHOT (was funktioniert, was nicht)

### Foundation (komplett ✅)
- **Pygame-Engine** — 30 Module in [sf/](sf/), Smoke-Tests bestehen
- **Akt 1 spielbar** — Brassweir-Hub, Korven/Otreth/Tameris/Mara/Eldon/Verwahrer NPCs, Krypta-Dungeon, Salzhueter-Boss
- **KI-Audio komplett** — 227 Voice-Lines + 433 SFX (10,35 EUR ElevenLabs)
- **Engine-Wiring** — Footsteps pro Biome, bestiary_key-Death-Sounds, Boss-Stinger, Mahnmal-Stelen-Activate, Crafting-SFX, Status-Apply-Sounds, Quest-Marker-Sounds, NPC-Voice-Greeting
- **Quest-Engine** — 12 Stage-Types (TALK/KILL/REACH/COLLECT/INTERACT/RETURN/ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL)
- **Crafting-System** — Otreth-Gemcutter, Affix-Roll, Reroll, Socket, Salvage
- **22 Outpost-NPCs** als Daten in [sf/outposts.py](sf/outposts.py) `NPC_ROSTER` (Spawn-Wiring teils ✅)
- **8 von 15 Boss-Encounters** im Code: salzhueter_brut, vehren, senator_geist, shulavh, velharn_trio, ertrunkene_koenigin, echo_drache, nicht_gott

### Was JETZT blockiert
- **47 von 53 Quests** sind nur in QUEST_BIBEL.md ausformuliert, nicht in [sf/quest_data.py](sf/quest_data.py) implementiert
- **Faction-Rep-System** komplett fehlend — blockiert alle Faction-Quests
- **NPC-Dialog-Modal mit Portrait + Choice-Buttons** fehlt — Voice-Lines werden nur als Toast gespielt
- **Cutscene-Framework** (X-09) fehlt — die 27 generierten Cinematic-Stinger sind nicht abspielbar
- **3 Endings** nicht implementierbar ohne Cutscene-Framework + Save-Branching
- **Endgame-Atlas** komplett fehlend
- **Sprites prozedural** — keine echten Mob-/Boss-/Klassen-Sprite-Sheets

---

## TIER 1 — Akt-1-Sealing + Faction-Foundation (Sprint-1, ~2 Wochen)

> Macht Akt 1 zu einem geschlossenen, saettigenden Erlebnis und legt die Foundation fuer alle weiteren Akte.

### 1.1 Akt-1-Quest-Bukett vervollstaendigen *(4 Quests, hoechste Impact-Dichte)*
- [x] **T1.1-A** `akt1_tameris_schwester` (Side/Escort/Hidden) — ✅ #149 (Lazy-Spawn) + #116 (Stages)
- [x] **T1.1-B** `akt1_tribunal_geruecht` (Faction, Eldon-Quest-Board) — ✅ #153
- [x] **T1.1-C** `akt1_bounty_salzgekreuzte` (Repeatable Daily-Reset) — ✅ #153
- [x] **T1.1-D** `akt1_versunkenes_grab` (Hidden via Decor-Trigger) — ✅ #154 (discover_via_interact + PUZZLE)

**Files:** [sf/quest_data.py](sf/quest_data.py), [sf/quests.py](sf/quests.py) (evtl. Repeatable-Reset-Logik)
**Akzeptanz:** Spieler kann Akt 1 mit allen 7 Quest-Slots (Main/Crafting/Lore/Faction/Side/Bounty/Hidden) erleben.

### 1.2 Faction-Rep-System Foundation *(Foundation fuer Akt 2+)* ✅ #159 verifiziert
- [x] **T1.2-A** `Player.faction_rep` Dict mit 7 Fraktionen — ✅ #117 ([sf/entities.py](sf/entities.py))
- [x] **T1.2-B** Save-Persistenz mit Clamp ±200 — ✅ #117 ([sf/save.py:707-711](sf/save.py#L707-L711))
- [x] **T1.2-C** Rep-Gain-Hook via `faction.apply_quest_reward` — ✅ #117 ([sf/quests.py](sf/quests.py) `_mark_complete`)
- [x] **T1.2-D** `CONFLICT_MATRIX` Drei-Wege-Dreieck — ✅ #117 ([sf/faction.py](sf/faction.py))
- [x] **T1.2-E** Codex-Tab „Fraktionen" — ✅ #118 (`_draw_codex_factions`)
- [x] **T1.2-F** Faction-Vendor-Unlock-Logik — ✅ #155 (`vendor_discount_small` → 10 % Rabatt via `buy_price(item, player=p)`)

**Files:** [sf/entities.py](sf/entities.py), [sf/save.py](sf/save.py), [sf/quests.py](sf/quests.py), [sf/game.py](sf/game.py) (Codex-Tab), [sf/shop.py](sf/shop.py)
**Akzeptanz:** Tameris-Schwester-Spared gibt Speerschwestern +25, Tribunal-Quest gibt Tribunal −15 sichtbar im Codex.

### 1.3 NPC-Dialog-Modal mit Portrait + Choice-Buttons *(macht Voice-Lines erst wirksam)*
- [ ] **T1.3-A** `DialogUI`-Modal in [sf/ui.py](sf/ui.py) — links Portrait (256×256 Placeholder bis T-07), rechts Text + bis zu 4 Choice-Buttons
- [ ] **T1.3-B** Voice-Line-Synced Subtitle (Wort-fuer-Wort Reveal alle 35 ms)
- [ ] **T1.3-C** Choice-Hover ueber Y_1 (NPC-Talk) → wenn Quest-Stage CHOICE, oeffnet Modal statt Auto-Toast
- [ ] **T1.3-D** Konversation-Tree-Format in [sf/quest_data.py](sf/quest_data.py) `dialog`-Feld pro NPC

**Files:** [sf/ui.py](sf/ui.py), [sf/quest_data.py](sf/quest_data.py), [sf/game.py](sf/game.py)
**Akzeptanz:** Korven-Talk oeffnet Dialog mit Portrait, Voice spielt, Choice-Buttons fuehren zu Quest-Stage-Branch.

### 1.4 Quest-Item-Flag *(verhindert Datenverlust)* ✅ #154
- [x] **T1.4-A** `Item.quest_item=True` Flag in [sf/items.py](sf/items.py) — ✅ #154 (Konstruktor-Param + __slots__)
- [x] **T1.4-B** [sf/crafting.py](sf/crafting.py) `salvage_item` returnt None bei quest_item — ✅ #154 (+ Toast im Modal-Handler)
- [x] **T1.4-C** [sf/shop.py](sf/shop.py) Verkaufs-Pfad blockt bei quest_item — ✅ #154 (+ Toast)
- [x] **T1.4-D** Tooltip-Hint „Quest-Item — kann nicht verkauft werden" — ✅ #154 (`display_lines`)
- [x] *(Bonus)* Drop-Schutz im Inventory (Shift+RClick) — ✅ #154
- [x] *(Bonus)* Save/Load-Persistenz mit Backward-Compat — ✅ #154

**Akzeptanz:** Tintendolch-von-Im-Nesh, Mahnmal-Marke VII u.a. lassen sich nicht versehentlich vernichten.

---

## TIER 2 — Akt 2 voll spielbar + Visuelles Foundation (Sprint-2/3, ~4-6 Wochen)

> Erweitert das Spiel auf 2 komplette Akte mit der ersten Faction-Konflikt-Story (Tribunal vs Erblinde). Parallel: visuelles Foundation-Upgrade (Sprite-Pipeline).

### 2.1 Akt-2-Content (Echo-Markt → Glasgolden-Ruinen)
- [x] **T2.1-A** Echo-Markt-Outpost-Layout — ✅ #156 (verifiziert; bereits seit #112-114 via `outposts.generate_outpost('echo_markt')` + `build_outpost_npcs`)
- [ ] **T2.1-B** Frost→Glass-Ruins Biome-Rename + Tile-Variation (W-09 Erweiterung)
- [x] **T2.1-C** 6 Akt-2-Quests — ✅ #155 (alle 6 Quests im Quest-Registry, Akt-Gating verifiziert):
  - `akt2_helst_pact_stones` (Faction Erblinde Kirche) ✅
  - `akt2_echo_handel` (Side, Vendor-Setup) ✅
  - `akt2_otreth_glas_gravur` (Crafting via Salir) ✅
  - `akt2_goldstaub_erinnerung` (Lore, Chain via requires_quests) ✅
  - `akt2_bounty_goldstaub_diener` (Bounty) ✅
  - `akt2_velharn_vorhof` (Hidden, Akt-5-Setup mit CHOICE-Flag) ✅
- [x] **T2.1-D** Senator-Geist-Boss-Encounter live im Code — ✅ #156 (verifiziert; seit #111 via `_spawn_dungeon_boss_in_room` mit frost→senator_geist Routing)

### 2.2 Sprite-Pipeline-Foundation *(TEIL T aus PLAN.md — groesster visueller Hebel)*

✅ **PHASE 1 KOMPLETT (heute, 2026-05-23)** — Scenario.gg Pipeline + 41 Sprites + Engine-Hooks live.

- [x] **T2.2-A** `assets/sprites/`-Struktur + `manifest.json` (T-01) — ✅ via [tools/sprite_gen.py](tools/sprite_gen.py) `assets/sprite_manifest.json`
- [x] **T2.2-B** `SpriteAtlas`-Loader mit Cache (T-02) — ✅ [sf/sprites.py](sf/sprites.py) `_load_ai_sprite()` + `_SPRITE_CACHE` + `reload_sprite_cache()`
- [x] **T2.2-C** `SpriteAnimator` mit State-Machine (T-03) — ⚠ **partial**: Single-Frame-Render funktioniert. Multi-Frame-Animation-Sheets sind Phase 3 (`T2.6-Anim` unten)
- [x] **T2.2-D** Procedural-Fallback bleibt aktiv (T-04) — ✅ `draw_player_at` + `draw_enemy_at` fallen auf Composit zurueck wenn PNG fehlt
- [x] **T2.2-E** **6 Lore-Mobs Sprite-Sheets Phase 1** (T-05) — ✅ Salzhueter-Brut + Glaslord + Vehren-Echo + Ertrunkene-Koenigin + Aschenbrut + Wurzelhueter (POE2 via El-Diablo-LoRA)
- [x] **T2.2-F** **8 Klassen-Sprites** (T-06) — ✅ alle 8 (Warrior/Witch/Sorceress/Monk/Ranger/Mercenary/Huntress/Druid), POE2-Style mit transparentem BG via Background-Removal-Pass
- [x] **T2.2-G** **8 NPC-Portraits 256×256** (T-07) — ✅ Korven, Helst, Vossharil, Tameris, Otreth, Mara, Vehren, Drei Muetter (via RPG-Avatars-LoRA)
- [x] **T2.2-H** **8 Boss-Concept-Plates 512×512** (T-08) — ✅ atmospheric backdrop, fuer Cinematic-Intros (X-06 wartet auf Display-Hook)
- [x] **T2.2-I** **11 Biome-Tilesets seamless** (T-10) — ✅ Crypt/Frost/Lava/Swamp/Astral/Desert/Town + 4 Wound/Hollow-Word (via Hand-Painted-Textures-LoRA nach 2 Failed-LoRA-Versuchen)
- [x] **T2.2-J** **Tile-Renderer-Hook in world.py** — ✅ `_get_ai_tile(biome)` + `_dungeon_cell_cache` in [sf/world.py](sf/world.py)
- [x] **T2.2-K** **Background-Removal Post-Processing** — ✅ [tools/sprite_postprocess.py](tools/sprite_postprocess.py) mit Numpy-Backed Alpha-Generation + Feathering. Auto-applied auf Mob+Class+Item nach Generation
- [x] **T2.2-L** **Sicherheit:** Scenario-Credentials-Loader (3-File-Fallback + Whitespace-Validation) — ✅ [tools/scenario_config.py](tools/scenario_config.py) `load_credentials()` mit Token-Regex-Whitelist; Key niemals geloggt

**Realisierte Kosten:** ~64 API-Calls / 5000 Plan-Budget = **1,3 %**. Final-Sprite-Count: **41 PNGs / ~5 MB**.

**Lessons learned:**
- POE2-Style mit `El Diablo`-LoRA fuer Mob/Class/Boss → 1-Shot-Hit
- Seamless Tiles brauchten 3 LoRA-Versuche: RPG-Environment (Architektur), Super-Top-Down (Game-Maps mit Walls/Charakter), schliesslich **Hand-Painted Textures** (richtig: sc:texture-Tag)
- Mob/Class brauchen Background-Removal-Pass (Alpha aus schwarzem BG)
- Single-Frame-Sprites reichen fuer ARPG-Top-Down-View — Multi-Frame ist Phase 3
- Tools-Pfad: [tools/scenario_config.py](tools/scenario_config.py) + [tools/sprite_gen.py](tools/sprite_gen.py) + [tools/sprite_postprocess.py](tools/sprite_postprocess.py) + [tools/scenario_list_models.py](tools/scenario_list_models.py)

### 2.5 Sprite-Pipeline-PHASE 2 *(NEU — was nach Phase-1-Run noch fehlt)*

Liste basiert auf System-Audit nach dem 41-Sprite-Run. Reihenfolge nach Sichtbarkeits-Impact im Spielfluss.

- [ ] **T2.5-A** **Decor-Sprites** (17 Velgrad-Lore-Decors) — `mahnmal_stele`, `pier_post`, `fishing_net`, `salt_puddle`, `gravestone`, `salt_crystal`, `salt_statue`, `anvil`, `cursed_altar`, `rune_anchor`, `lore_tablet`, `underworld_rift`, `bookshelf`, `fountain`, `chest_decor`, `sumpf_pool`, `sarcophagus`. Engine-Hook in `draw_decor()`. **Geschaetzt: ~3 EUR / ~17 Calls**
- [ ] **T2.5-B** **Item-Icons fuer 50 Unique-Weapons** aus VELGRAD_ITEMS_UNIQUE_BIBEL — pro Item ein 128×128 PNG mit Rarity-Border. Inventar sieht sonst leer aus. Model: `Fantasy Blades`. **~10 EUR / ~50 Calls**
- [ ] **T2.5-C** **Status-Effect-Icons** (15 Status) — `burn`, `frost`, `chill`, `shock`, `poison`, `bleed`, `stun`, `silence`, `armour_break`, `pinned`, `brittle`, `sapped`, `maim`, `crush`, `heal_tick`. Pro Status 32×32 PNG fuer Buff-Tray-UI. **~3 EUR**
- [ ] **T2.5-D** **Hit-Spark-Sheets** pro Damage-Type (8 Types) — 4-8 Frames pro Sheet als Strip, played on hit. Aktuelle Procedural-Particles bleiben als Layer drueber. **~2 EUR**
- [ ] **T2.5-E** **AoE-Ring-Templates** pro Element (6 Elements) — Single PNG mit Glow-Ring, gescaled je nach Decal-Radius. Ersetzt aktuelle Procedural-Outline. **~1,5 EUR**
- [ ] **T2.5-F** **Aspekt-Auren** (7 Aspekte) — Single PNG pro Aspekt-Pakt, additiv geblittet um Player-Body wenn Pakt aktiv. **~1,5 EUR**
- [ ] **T2.5-G** **Door + Chest Sprites** (Wood/Metal/Locked/Unique-Chest) — 6 PNGs fuer interactable Decors. **~1,5 EUR**
- [ ] **T2.5-H** **Trap-Sprites** (Spike/Fire/Arrow/Plate, je armed + triggered) — 8 PNGs. **~2 EUR**
- [ ] **T2.5-I** **Cursor + UI-Frames** (Buttons/Borders/Modal-Frames/Scroll-Track) — ~10 PNGs fuer UI-Polish. **~2 EUR**
- [ ] **T2.5-J** **Parallax-Backgrounds** fuer 7 Akt-Outposts (Brassweir-Harbor, Echo-Markt-Ruinen, Saeulen-von-Helst, ...) — Single Wide-PNG (1920×600) pro Outpost als Background-Layer. **~2 EUR**

**Phase-2-Total:** ~115 PNGs, ~25 EUR, ~30 min Generation.

### 2.6 Sprite-Pipeline-PHASE 3 *(Multi-Frame Animation, Phase-3-Material)*

Animation-Sheets sind aufwendiger — Scenario.gg hat „Animator"-Models die Multi-Frame-Sheets generieren, oder wir nutzen Stable Diffusion + AnimateDiff lokal.

- [ ] **T2.6-A** **Klassen-Animation-Sheets** (8 Klassen × Idle 6F + Walk 8F + Attack 6F + Hit 3F + Death 8F = ~31 Frames pro Klasse, 8-Direction optional) — `~250 Sheets` fuer voll-animierte ARPG-Klassen. **~50 EUR**
- [ ] **T2.6-B** **Boss-Animation-Sheets** (15 Bosse × Idle + Attack + Phase-Transition × ~10 Frames) — **~30 EUR**
- [ ] **T2.6-C** **Skill-VFX-Sequences** pro Aspekt-Cast (7 Aspekte × Wind-up + Travel + Impact als Frame-Strips) — Aktuelle Procedural-Particles bleiben Foundation, AI-Frames overlayen. **~20 EUR**
- [ ] **T2.6-D** **Mob-Direction-Sprites** — wenn Top-Down-View wichtig wird, brauchen Mobs 4-8 Richtungs-Sprites statt nur Frontal. **~20 EUR**

**Phase-3-Total:** ~600 Files, ~95-120 EUR (eigenes Sprint-Set fuer Animation-Polish-Phase).

### 2.7 Sprite-Pipeline-PHASE 4 *(Modulare Architektur)*

- [ ] **T2.7-A** **Modulare Building-Tilesets** fuer 7 Outpost-Architekturen — pro Stil ~50 Module (Wall-Corner-Innen/Aussen/Straight, Door-Frame, Roof-Section, Window). Quelle: VELGRAD_LORE_BIBEL pro Outpost. **~15 EUR**
- [ ] **T2.7-B** **Tile-Auto-Tiling (47-Bitmask)** in [sf/world.py](sf/world.py) — M-15 aus PLAN.md. Code-Task ohne neue Assets. Macht aus den Phase-1-Tiles organische Walls statt Klotz-Look.

**Phase-4-Total:** ~350 Building-Module + Engine-Code, ~15 EUR + Code-Work.

---

**Tool-Empfehlung:** Scenario.gg Creator-Plan (29 EUR/mo) deckt Phase 1+2 bequem ab. Phase 3+4 brauchen Pro-Plan (99 EUR/mo) oder lokal Stable Diffusion.

### 2.3 Quest-Board-Modal *(Eldon hat aktuell keinen UI)*
- [x] **T2.3-A** Quest-Board-Sektion im QuestLog-Modal — ✅ #156 (`_draw_quest_board_section` listet AVAILABLE + LOCKED, filtert Hidden-Quests)
- [x] **T2.3-B** Eldon-Talk öffnet QuestLog-Modal — ✅ Seit Day-1 (npc.kind='quest' → modal='questlog'), jetzt mit Quest-Board-Sektion sichtbar
- [x] **T2.3-C** Quest-Pin-Funktion — ✅ #160 (`QuestLog.tracked_quest_id` + P-Hotkey im QuestLog + Compass-Priorität + 📌-Marker + Save-Persistenz)

### 2.4 Akt-Gating an Quest-Flags ✅ #156
- [x] **T2.4-A** `progression.can_enter_akt(player, akt)` + `akt_block_reason(player, akt)` — ✅ #156
- [x] **T2.4-B** Outpost-Portal-Check vor Travel: blockt wenn akt-gate nicht erfüllt — ✅ #156 (refactored auf Helper)
- [x] **T2.4-C** Toast „Vollende erst Akt N-1 zuerst" bei Block — ✅ #156 (`akt_block_reason` liefert lore-konforme Erklärung)

**Files:** [sf/progression.py](sf/progression.py), [sf/game.py](sf/game.py)

---

## TIER 3 — Akte 3-5 + Sprite-Phase-2 + Cutscene-Framework (Sprint-4/5/6, ~8-12 Wochen)

> Das Spiel waechst auf 5 Akte mit der vollen Tribunal/Erblinde/Knochenwitwen-Konflikt-Triade + Velharn-Drei-Zeiten-Mechanik.

### 3.1 Akt-3-Content (Aschenfelder → Vehren-Boss)
- [ ] **T3.1-A** Saeulen-von-Helst-Outpost-Layout (Acolyt, Korren, Selvor, Brulm)
- [ ] **T3.1-B** 6 Akt-3-Quests (siehe QUEST_BIBEL §3.5)
- [ ] **T3.1-C** Tribunal-Patrouille-Event (zufaelliger Encounter ab Akt 3)
- [ ] **T3.1-D** Asche-Stelen-Decor + Lore-Tablets fuer Valsa-Traene-Quest

### 3.2 Akt-4-Content (Wurzelgrab → Shulavh-Choice-Boss)
- [ ] **T3.2-A** Knoten-Markt-Outpost (Vossharil, Bran, Marvel, Hohler-Sohn)
- [ ] **T3.2-B** 7 Akt-4-Quests inkl. **shulavh_faden Choice** (Heilen vs Bezwingen, Save-Flag)
- [ ] **T3.2-C** Shulavh-3-Phasen-Boss-Mechanik (Muetterlich/Wahnsinnig/Vergessend) mit Voice-Pool
- [ ] **T3.2-D** Multi-Stage-Wurzelgrab-Dungeon (Aussen-Wurzeln → Kambium-Hoehle → Mark-Kammer → Faden-Mutter-Arena)

### 3.3 Akt-5-Content (Velharn → Drei-Zeiten-Boss)
- [ ] **T3.3-A** Spiegelhof-Outpost (Voraius, Nheya, Sehir, Mara)
- [ ] **T3.3-B** 6 Akt-5-Quests inkl. **akt5_drei_zeiten Puzzle**
- [ ] **T3.3-C** Drei-Zeiten-Mechanik (Player wechselt zwischen 3 Zeit-Schichten via Spiegel-Splitter)
- [ ] **T3.3-D** Ousen-Reveal-Cutscene (braucht T3.5 Cutscene-Framework)
- [ ] **T3.3-E** `akt5_korven_oder_helst` Hidden-Quest (legt Disguise-Identity fuer Akt 6 fest)

### 3.4 Sprite-Sheets Phase 2 (T-05 + T-06 Rest)
- [ ] **T3.4-A** 5 weitere Klassen-Sheets: Monk, Ranger, Mercenary, Huntress, Druid
- [ ] **T3.4-B** Boss-Portraits 512×512 (T-08) fuer alle 8 implementierten Bosse
- [ ] **T3.4-C** Item-Icons 64×64 (T-09) fuer 50 Uniques aus VELGRAD_ITEMS_UNIQUE_BIBEL
- [ ] **T3.4-D** Tilesets pro Biome (T-10) — 32×32 Sheets fuer Crypt/Frost/Lava/Swamp/Astral/Desert/Town

### 3.5 Cutscene-Framework (X-09 + 9 Pflicht-Cutscenes)
- [ ] **T3.5-A** `Cutscene`-Klasse in `sf/cutscene.py` (neu) mit Steps:
  - `camera_move(target, duration)`
  - `hold(t)`
  - `portrait_show(npc_key)`
  - `text_show(text, voice_id, dur)`
  - `sfx(name, vol)`
  - `wait(t)`
- [ ] **T3.5-B** Akt-1-Schiffbruch-Intro-Cutscene (verwendet `akt1_intro_*` SFX)
- [ ] **T3.5-C** Akt-2-Helst-Pact-Cutscene
- [ ] **T3.5-D** Akt-3-Vehren-Reveal-Cutscene (Valsa-Besessenheit)
- [ ] **T3.5-E** Akt-4-Shulavh-Encounter (Pre-Choice)
- [ ] **T3.5-F** Akt-5-Ousen-Reveal-Cutscene (groesster Story-Moment)

### 3.6 Lighting & Shadow Engine 2.0 (TEIL U)
- [ ] **T3.6-A** Multi-Source-Light-Buffer (U-01) — Foundation fuer alles weitere
- [ ] **T3.6-B** Dynamic Shadow-Casting fuer Player-Halo + Boss-Light (U-02)
- [ ] **T3.6-C** Decor-Shadows (U-03) — Drop-Shadow-Ellipsen am Ground-Anker
- [ ] **T3.6-D** Lava/Glow-Cell-Tint (U-06) + Player-Casting-Hand-Light (U-07)
- [ ] **T3.6-E** M-10 Bloom-Pass (haengt an U-01)

### 3.7 NPC-Quest-Spawning in Dungeons
- [ ] **T3.7-A** `quests.spawn_quest_npc(game, npc_key, x, y)` — spawnt einen NPC im aktuellen Dungeon
- [ ] **T3.7-B** Tameris-Schwester (Hohle Gewordene) als spawnable NPC im Krypta-Boss-Vorraum
- [ ] **T3.7-C** Vossharil-Guide im Wurzelgrab-Tier-2
- [ ] **T3.7-D** Despawn beim Stage-Advance (analog ESCORT-Despawn aus Update #150)

---

## TIER 4 — Akt 6-7 + Endgame + 3 Endings (Sprint-7/8/9, ~12-16 Wochen)

> Das Spiel wird storymaessig komplett. Drei-Wunden-Trial + Im-Nesh-Final + 3 Endings + Endgame-Atlas-Foundation.

### 4.1 Akt-6-Content (Drei Wunden — Hub-artiger Akt)
- [ ] **T4.1-A** **3 neue Biomes**: `wound_salt`, `wound_ash`, `wound_hollow`
- [ ] **T4.1-B** Drei-Wunden-Lager-Outpost (Mara-Wunden, Korven_oder_Helst, Tehrnal)
- [ ] **T4.1-C** 6 Akt-6-Quests (3× Wunden-Lesen + Pakt-Uebersetzen + Korven/Helst-Reveal + Bounty)
- [ ] **T4.1-D** 3 Boss-Encounters live im Code:
  - Ertrunkene Koenigin (Bestiarium #26) — Salzwunde
  - Echo-Drache (Bestiarium #27) — Aschwunde
  - Nicht-Gott (Bestiarium #28) — Hohlwunde
- [ ] **T4.1-E** **Korven-oder-Helst-Reveal-Cutscene** — eine von zwei Identitaeten ist Im-Nesh
- [ ] **T4.1-F** Drei-Wunden-Resonanz-Event (Damage-Boost beim Wunden-Pulsieren)

### 4.2 Akt-7-Content (Hohlwort — Endgame-Threshold)
- [ ] **T4.2-A** **Neues Biome** `hollow_word` — Pseudo-Realitaet, invertierte Farben
- [ ] **T4.2-B** Drei-Muetter-Outpost (3 NPCs als Trial-Geber)
- [ ] **T4.2-C** `akt7_drei_muetter_trial` Ascendancy-Quest (3 Sub-Trials)
- [ ] **T4.2-D** **Im-Nesh-Final-Boss** (3 Phasen mit Layered-Voice) + Cutscene
- [ ] **T4.2-E** Hohlwort-Multi-Stage-Dungeon (Vestibuel → Stille-Zone → Hundertsprachen → Im-Nesh-Arena)

### 4.3 Drei Endings (Akt-7-Wahl)
- [ ] **T4.3-A** Choice-System mit 3 Optionen + jeweils Save-Branching
- [ ] **T4.3-B** **Ending A (Sacrifice)** — Char wird Memorial-Eintrag, Save-Slot bleibt locked
- [ ] **T4.3-C** **Ending B (Betrayer)** — Verraeter-Atlas-Modus freigeschaltet (eigene Map-Pool)
- [ ] **T4.3-D** **Ending C (Dreamer)** — Aithein-Pfad-Atlas, ueberschriebene Maps
- [ ] **T4.3-E** Pro Ending eigener Cinematic + End-Cutscene
- [ ] **T4.3-F** Achievement-System pro Ending

### 4.4 Endgame-Atlas Foundation
- [ ] **T4.4-A** `Atlas`-Modul `sf/atlas.py` (neu) — Map-Pool, Tier-System, Modifier-Roll
- [ ] **T4.4-B** Atlas-Modal als neuer Tab in Fullmap (M-Modal-Erweiterung)
- [ ] **T4.4-C** 20+ Welkende-Welten-Maps (Echos von Akt 1-7 Regions mit Korruption)
- [ ] **T4.4-D** Map-Modifier-Pool (10-15 Modifier wie „+50% Mob-Damage", „Vergessens-Welle alle 30s", „Im-Nesh-Echo-Spawns")
- [ ] **T4.4-E** Atlas-Tree (Passive-Punkte fuer Map-Region-Modifier)
- [ ] **T4.4-F** Atlas-Currency `atlas_stones` + Map-Tier-Upgrade-Loop

### 4.5 Pinnacle-Bosse
- [ ] **T4.5-A** 5 Aspekt-Echo-Bosse (Kharn / Nheyra / Ousen / Valsa / Shulavh) — verzerrte Aspekt-Versionen
- [ ] **T4.5-B** Aithein-Echo (Pinnacle, alle 5 Aspekt-Echos vorher)
- [ ] **T4.5-C** Im-Nesh-Reborn (Hardmode Akt-7)
- [ ] **T4.5-D** Der-Achte (Hidden, Lore 11.4 — fehlende Aspektin)
- [ ] **T4.5-E** Der-Letzte-Traeumer (Lore 11.6 — Aithein=Player-Reveal, nur Dreamer-Ending)

---

## TIER 5 — Polish, Tech-Debt, Distribution (kontinuierlich + Release-Vorbereitung)

> Vor erstem Public-Release. Parallel zu Tier 1-4 ueber die ganze Laufzeit.

### 5.1 Animation-Polish (PLAN TEIL O Rest)
- [ ] **T5.1-A** O-13: Echte Frame-Animationen aus Sprite-Sheets (T-05/T-06)
- [ ] **T5.1-B** O-14: Animation-Blending zwischen States
- [ ] **T5.1-C** O-15: Cloth/Hair Verlet-Sim pro Klasse
- [ ] **T5.1-D** O-16: Death-Ragdoll (Light, Pygame-Pragmatik)
- [ ] **T5.1-E** O-17: Walk-Cycle-Bob + phase-getriggerte Footsteps
- [ ] **T5.1-F** O-18: Skill-Cast-Pose-Library
- [ ] **T5.1-G** O-20: Idle-Variations (Fidgets) fuer Mobs
- [ ] **T5.1-H** O-21: Boss-Phase-Transformation-Anim (Scale-Pulse + Aura-Burst)

### 5.2 Render-Polish (PLAN TEIL M Rest)
- [ ] **T5.2-A** M-12: Heat-Distortion bei Fire-AoE / Lava
- [ ] **T5.2-B** M-14: Render-Layer-Manager (Z-Index-Sort, saubere Layer-Stack)
- [ ] **T5.2-C** M-15: Tile-Auto-Tiling (47-Tile Bitmask)
- [ ] **T5.2-D** M-16: Parallax-Background-Layer in Town + Boss-Arenen
- [ ] **T5.2-E** M-17: Reflection-Layer fuer Wasser/Eis/Glas
- [ ] **T5.2-F** M-22: Sprite-Squash-and-Stretch on Movement

### 5.3 Material- & Surface-Effekte (PLAN TEIL V Rest)
- [ ] **T5.3-A** V-01: Wet-Surface nach Rain
- [ ] **T5.3-B** V-02: Ice-Surface auf Frost-Stack ≥3
- [ ] **T5.3-C** V-03: Scorched-Earth nach Fire-AoE
- [ ] **T5.3-D** V-04: Glas-Splitter-Boden in Glaslord-Arena
- [ ] **T5.3-E** V-07: Dust-Trail beim Sprint/Dodge
- [ ] **T5.3-F** V-08: Cloth-Sim fuer Banner in Town

### 5.4 Camera & Cinematics (PLAN TEIL X Rest)
- [ ] **T5.4-A** X-03: Camera-Zoom-Out im Combat
- [ ] **T5.4-B** X-06: Vollwertige Boss-Intro-Cinematic-Sequenz (mit Portrait-Plate)
- [ ] **T5.4-C** X-07: Level-Up-Mini-Cinematic
- [ ] **T5.4-D** X-08: Death-Replay (Last-3-Seconds)
- [ ] **T5.4-E** X-10: Title-Screen-Animation (Wind, Embers, Aspekt-Sigil)

### 5.5 UI/UX & Onboarding (PLAN TEIL Y Rest)
- [ ] **T5.5-A** Y-05: Echte Slider mit Drag (statt Cycle-Click)
- [ ] **T5.5-B** Y-06: Keybind-Rebind-UI in Settings

### 5.6 Save & Distribution (PLAN TEIL Z Rest)
- [ ] **T5.6-A** Z-05: Steam-Integration (steamworks.py, Cloud-Save, Achievement-Mapping)
- [ ] **T5.6-B** Z-08: Leaderboard-Hook fuer Survival-Mode

### 5.7 Debug & Tools (PLAN TEIL AA Rest)
- [ ] **T5.7-A** AA-02: Debug-Console (~-Taste, Slash-Commands)
- [ ] **T5.7-B** AA-04: Telemetrie (opt-in, anonyme Stats)
- [ ] **T5.7-C** AA-05: Mod-Hook-API Foundation
- [ ] **T5.7-D** AA-06: Replay-Recording (deterministisch via RNG-Seed)
- [ ] **T5.7-E** AA-07: Profiler-Mode (cProfile-Wrapper)
- [ ] **T5.7-F** AA-08: Asset-Validator beim Startup

### 5.8 Tests (PLAN TEIL S Rest)
- [ ] **T5.8-A** S-09: Visual-Regression-Tests (Pillow.ImageChops gegen Baseline)
- [ ] **T5.8-B** S-08 Erweiterung: Localization en_US Vollausbau

### 5.9 Repo & Release-Hygiene
- [ ] **T5.9-A** **LICENSE-File** — aktuell „kein Lizenz-Modell" = strenges Copyright. MIT? CC-BY-NC? Eigene Lizenz?
- [ ] **T5.9-B** **Screenshots im Repo** + GIF in README
- [ ] **T5.9-C** **`v0.1.0` Release-Tag** mit Release-Notes
- [ ] **T5.9-D** `.github/ISSUE_TEMPLATE/` (Bug-Report + Feature-Request)
- [ ] **T5.9-E** GitHub-Action fuer Smoke-Tests bei Push
- [ ] **T5.9-F** Linux/Mac-Build testen

### 5.10 Music & Ambience (separate Pipeline, parallel)
- [ ] **T5.10-A** Suno-AI-Pro abonnieren (~30 EUR/mo) + 42 Music-Tracks generieren:
  - 7 Town-Themes (pro Hub)
  - 7 Akt-Dungeon-Themes
  - 15 Boss-Themes
  - 9 Cinematic-Themes
  - 4 Endgame-Atlas-Themes
- [ ] **T5.10-B** Stable Audio (Free-Tier) — 14 Velgrad-spezifische Ambience-Loops (Crypt-Echo, Aschen-Brand, Wurzel-Knarren, Stille-Zonen, Spiegelhof-Drei-Zeiten, Hohlwort-Stille)
- [ ] **T5.10-C** Loop-Cross-Fade-Polish via Audacity (sonst Click an Loop-Punkten)

---

## ENGINE-LUECKEN aus PLAN.md die JEDERZEIT mitlaufen koennen

> Nicht auf einen Tier festgelegt — kleine Tasks die ad-hoc passen.

- [x] **AI-Mob-Alert/Attack-Sounds** — ✅ #159 (`_enter_state(AGGRO)` ruft `play_with_fallback(f'{bestiary_key}_alert', 'ambient_monster_growl')` mit globaler Throttle 1×/0.8s; bosse skip)
- [ ] **Aspekt-Skill-Sounds** wired — Phase-1-SFX `aspekt_<aspekt>_cast/impact/tick` existieren, aber `skills.py` ruft noch `cast_lightning`/`cast_frost`/`cast_fire`. Mapping aufbauen.
- [ ] **Music-Stem-Swap pro Akt** — N-09 ist als Volume-Duck implementiert; echter Stem-Crossfade braucht Suno-Tracks pro Akt (T5.10-A).
- [ ] **Quest-Compass durchgaengig** — Portal-Highlight ist da (#151), aber INTERACT/COLLECT-Stages haben noch keinen Welt-Marker.
- [x] **Aspekt-Affixes (7 Stueck, Lore-getreu)** aus WELT_AUFBAU 5.4 — ✅ #159 (alle 7 in AFFIXES + Fold-Mapping zu Engine-Stats; Aspekt-Akkumulatoren separat für späteres Mahnmal-Pakt-Tag-Buff)
- [ ] **4 zusaetzliche Item-Slots erwaegen** — boots/gloves/belt/flask_modifier (WELT_AUFBAU 5.1)
- [ ] **Unique-Drop-Pool pro Boss** — aktuell nur generischer Affix-Roll, kein Lore-Mapping (WELT_AUFBAU 5.3 + QUEST_BIBEL Item-Drop-Crossref)
- [ ] **Set-Linking** (Shulavhs Faden) — 2 Items verbinden, Set-Bonus bei beiden equipped

---

## ENDE — Wie diese ROADMAP genutzt wird

1. **Sprint-Format:** 1 Sprint = 2 Wochen, fokussiert auf 1-2 Tier-Sub-Sections.
2. **Tier-Sequenz nicht strikt:** Tier 5 (Polish) laeuft parallel zu Tier 1-4.
3. **Bei jedem Sprint-Ende:** Tasks `[x]` markieren + Eintrag in [CHANGELOG.md](CHANGELOG.md).
4. **Bei Lore-Konflikten:** Quellen-Hierarchie aus PLAN.md Regel 0 beachten — Lore-Bibel sticht alle.
5. **Optisch + Animations-Hebel** (PLAN.md Note unten): Bei Knappheit der Zeit T-05+T-06+T-10+U-01+U-03+M-10+M-20 priorisieren (groesster Visual-Impact); O-13+O-14+O-15+O-16+O-22+X-06 fuer Animation-Impact.
6. **Repo-public-Hygiene** (T5.9) bevor erstes oeffentliches Release.

---

## ZUSAMMENFASSUNG — TOP-10 wenn nichts anderes geht

Wenn du nur 10 Tasks aus der ganzen ROADMAP machen koenntest, in dieser Reihenfolge:

1. **T1.1** — Akt-1-Quest-Bukett (4 Quests) → Akt 1 ist saettigend
2. **T1.2** — Faction-Rep-System Foundation → unblocked alles weitere
3. **T1.3** — NPC-Dialog-Modal mit Portrait → macht Voice-Lines wirksam
4. **T2.1** — Akt-2-Content komplett → Spiel waechst um 1 Akt
5. **T2.2-E/F/G** — Sprite-Sheets Phase 1 (6 Mobs + 3 Klassen + 8 Portraits) → groesster visueller Hebel
6. **T3.5** — Cutscene-Framework + 5 Pflicht-Cutscenes → Story wird erlebbar
7. **T3.2** — Akt-4-Content + Shulavh-Choice → erster echter Choice-Moment
8. **T4.1** — Akt-6-Drei-Wunden → Boss-Hub-Variation
9. **T4.2 + T4.3** — Akt-7 + 3 Endings → Story ist komplett
10. **T5.9** — Repo-Public-Hygiene (LICENSE, Screenshots, v0.1.0) → veroeffentlichbar

Geschaetzte Gesamtzeit: 8-12 Monate Solo-Dev mit moderater Investition (~100-150 EUR fuer Music + Sprite-Tools).
