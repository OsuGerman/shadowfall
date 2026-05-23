# VELGRAD — QUEST-BIBEL

> **Zweck.** Vollstaendige Quest-Definitionen fuer alle 7 Akte + Endgame.
> Komplement zu [WELT_AUFBAU.md](WELT_AUFBAU.md) §3 (Quest-Master-Liste).
> Diese Datei ist die Daten-Bibel: jedes Quest-Dict ist 1:1 implementierbar
> in [sf/quest_data.py](sf/quest_data.py).
>
> **Quest-Schema** (siehe [sf/quest_data.py](sf/quest_data.py) Header):
> - `id` — unique string
> - `title` — Anzeige-Titel
> - `giver` — NPC-Name
> - `giver_kind` — NPC.kind (vendor/mystic/smith/quest/innkeeper/stash)
> - `region` — "Akt N — Region-Name"
> - `is_main` — bool
> - `prerequisites` — `['quest_id_1', 'quest_id_2']` (Quest-Flag-Gates)
> - `stages` — Liste mit `text`, `type`, `target`, `count`, `on_complete`
> - `reward` — `{gold, xp, item, faction_rep, currency}`
> - `consequences` — Faction-Rep-Aenderungen + Story-Flags
> - `on_complete_quote` — Giver-Final-Line
>
> **Stage-Types** (NEU in Pipeline — siehe WELT_AUFBAU §3.1):
> TALK / KILL / REACH / COLLECT / INTERACT / RETURN / **ESCORT** / **DEFEND** /
> **PUZZLE** / **CHOICE** / **TIMED** / **CONDITIONAL**

---

## INDEX

- [Akt 1 — Die Salzkueste (Brassweir)](#akt-1) — 7 Quests
- [Akt 1b — Zhar-Eth (Desert, Optional)](#akt-1b) — 4 Quests
- [Akt 2 — Glasgoldene Ruinen (Echo-Markt)](#akt-2) — 7 Quests
- [Akt 3 — Aschenfelder (Saeulen-von-Helst)](#akt-3) — 7 Quests
- [Akt 4 — Wurzelgrab (Knoten-Markt)](#akt-4) — 7 Quests
- [Akt 5 — Spiegelstadt Velharn (Spiegelhof)](#akt-5) — 6 Quests
- [Akt 6 — Drei Wunden](#akt-6) — 6 Quests
- [Akt 7 — Hohlwort](#akt-7) — 4 Quests
- [Cross-Akt-Chains](#cross-akt) — Mara, Tameris, Korven/Helst
- [Endgame-Atlas](#endgame) — 5 Pinnacle-Chains

---

<a name="akt-1"></a>
## AKT 1 — DIE SALZKUESTE (Brassweir-Hub)

### Q1.1 `akt1_salzwunde` — Die Salzwunde ✅ (existiert)
- **Status:** ✅ in `sf/quest_data.py`
- **Giver:** Korven Vor (vendor) · **Main**
- **Stages:** 6 (TALK → REACH crypt → KILL salzgekreuzter ×8 → REACH boss_room → KILL salzhueter_brut → RETURN)
- **Reward:** 200 Gold, 180 XP, Mahnmal-Marke VII
- **Consequences:** `flag.akt1_finished = True` (Gate fuer Akt 2)
- **Reputation:** Mahnmal-Gilde +30

### Q1.2 `akt1_otreth_stein` — Otreths erster Stein ✅ (existiert)
- **Status:** ✅ in `sf/quest_data.py`
- **Giver:** Otreth Hohlauge (smith) · Crafting-Quest

### Q1.3 `akt1_mara_spur` — Maras Spur ✅ (existiert)
- **Status:** ✅ in `sf/quest_data.py`
- **Giver:** Mara die Mahnerin (mystic) · Lore-Quest
- **Cross-Chain:** Erster Teil der Mara-Chain (siehe Cross-Akt-Chains).

### Q1.4 `akt1_tameris_schwester` — Die verschwundene Schwester
- **Giver:** Tameris (innkeeper) · Side / Escort / Hidden
- **Region:** Akt 1 — Brassweir + Akt 1b Zhar-Eth (Tameris-Schwester-Chain Stage 1)
- **Prerequisites:** `akt1_salzwunde` Stage 2 erreicht (Spieler ist in der Krypta gewesen)
- **Voice-Notes:** Tameris ist verzweifelt, spricht in halben Saetzen.
- **Stages:**
  1. **TALK** Tameris im Wirtshaus: *„Meine Schwester schreibt nicht mehr. Speerschwestern schreiben immer."*
     - target: `{'npc_name': 'Tameris'}`
     - on_complete: „Tameris haendigt dir ihren Speer als Zeichen aus."
  2. **REACH** Krypta-Treasure-Room: Spuren ihrer Schwester finden.
     - target: `{'biome': 'crypt', 'room_kind': 'treasure'}`
     - on_complete: „Auf dem Boden liegt ein zerbrochener Mond-Anhaenger."
  3. **COLLECT** Mond-Anhaenger-Fragmente (3 Stueck im Crypt).
     - target: `{'item_id': 'mond_fragment'}` · count: 3
     - on_complete: „Du spuerst, dass jemand sie dorthin gefuehrt hat. Bewusst."
  4. **ESCORT** Tameris zum Salzwund-Heiligtum (Boss-Room).
     - target: `{'npc_name': 'Tameris', 'destination': 'boss_room'}`
     - escort_hp: 0.6 (HP-Bar, Game-Over bei Tameris-Tod)
     - on_complete: „Tameris sieht ihre Schwester. Sie hat keinen Schatten."
  5. **CHOICE** Tameris-Schwester (Hohle Gewordene) konfrontieren.
     - choices:
       - `{label: 'Schwester erloesen (toeten)', flag: 'tameris_sister_killed'}`
       - `{label: 'Schwester in Frieden lassen', flag: 'tameris_sister_spared'}`
  6. **RETURN** Tameris in Brassweir.
- **Reward:**
  - 150 Gold, 120 XP
  - Item: **„Tameris' Suchender"** (Spear [M], Lore-Bibel Items #17) — Unique-Drop
  - Speerschwestern-Rep +25
  - Bei *erloesen*: Speerschwestern-Rep zusaetzlich +15 (Gnade)
  - Bei *spared*: Mahnmal-Gilde-Rep +10 (Mara-Faden)
- **on_complete_quote** (Tameris):
  *„Sie war meine Faden-Schwester. Du hast sie gesehen, als ich nicht konnte. Das wiegt schwer. Geh, bevor ich dich noch mehr brauche."*

### Q1.5 `akt1_tribunal_geruecht` — Tribunals Vorboten
- **Giver:** Stadtsprecher Eldon (quest) · Faction (Mahnmal-Gilde / Anti-Tribunal)
- **Region:** Akt 1 — Brassweir
- **Prerequisites:** —
- **Stages:**
  1. **TALK** Eldon am Quest-Board.
  2. **KILL** Tribunal-Spaeher (5 Stueck) im Crypt-Eingangs-Bereich.
     - target: `{'bestiary_key': 'tribunal_spaeher'}` · count: 5
     - on_complete: „Sie tragen alle das gleiche Brandzeichen. Frisch."
  3. **COLLECT** Tribunal-Befehl (Decor in Spaeher-Hideout).
     - target: `{'item_id': 'tribunal_befehl_v1'}`
     - on_complete: „Der Befehl nennt deinen Namen. Du bist auf einer Liste."
  4. **RETURN** Eldon.
- **Reward:** 120 Gold, 80 XP, Mahnmal-Gilde-Rep +20, **Tribunal-Rep −15**
- **Consequences:** `flag.player_on_tribunal_list = True` (triggert Patrouille-Events ab Akt 2)
- **on_complete_quote** (Eldon):
  *„Sie wissen jetzt von dir. Bleib nicht zu lange am gleichen Ort. Brassweir ist sicher — solange ich hier bin."*

### Q1.6 `akt1_bounty_salzgekreuzte` — Mahnmal-Kopfgeld (Repeatable)
- **Giver:** Eldon (quest) · Bounty
- **Region:** Akt 1 — Brassweir
- **Repeatable:** Daily-Reset (1 Run pro 24h Realtime ODER pro Dungeon-Run)
- **Stages:**
  1. **KILL** Salzgekreuzte (10 Stueck).
     - target: `{'bestiary_key': 'salzgekreuzter'}` · count: 10
- **Reward:** 60 Gold, 40 XP, Mahnmal-Gilde-Rep +5
- **on_complete_quote** (Eldon):
  *„Auch wenn niemand sich an sie erinnert — ihre Bezahlung tut es."*

### Q1.7 `akt1_versunkenes_grab` — Das versunkene Grab (Hidden)
- **Giver:** Decor-Trigger (Salz-Stele im Crypt, schreibend findbar) · Hidden
- **Region:** Akt 1 — Brassweir / Salzkueste
- **Prerequisites:** `akt1_salzwunde` Stage 3 erreicht (Spieler ist tief im Crypt)
- **Discovery-Type:** INTERACT mit Salz-Stele triggert Quest-Start automatisch.
- **Stages:**
  1. **INTERACT** Salz-Stele lesen.
     - on_complete: „Eine Inschrift in alter Sprache. Sie endet mit drei Zahlen."
  2. **PUZZLE** Drei Salz-Altaere in der Reihenfolge der Inschrift aktivieren.
     - target: `{'puzzle': 'salt_altars', 'sequence': [2, 3, 1]}`
     - on_complete: „Eine versteckte Tuer im Crypt oeffnet sich."
  3. **KILL** Salz-Wraith-Boss-Mini (im Versteck).
     - target: `{'bestiary_key': 'salz_wraith'}` · count: 1
  4. **COLLECT** Salz-Koenigin-Tagebuch (Lore-Codex).
- **Reward:** 100 Gold, 80 XP, Codex-Entry „Die Letzte Salz-Koenigin", **Mahnmal-Marke I** ×2

---

<a name="akt-1b"></a>
## AKT 1b — ZHAR-ETH-KARAWANE (Desert, Optional)

### Q1b.1 `akt1b_speerschwester_aufnahme` — Die Speerschwester-Aufnahme
- **Giver:** Schwester-Kommandantin Naveth (quest) · Main fuer 1b
- **Region:** Akt 1b — Zhar-Eth
- **Prerequisites:** `akt1_tameris_schwester` Stage 1 ODER `akt1_salzwunde` complete
- **Stages:**
  1. **TALK** Naveth in der Karawane.
  2. **KILL** 3 Wuesten-Salzgekreuzte mit nur Speer-Skill (Trial).
     - target: `{'bestiary_key': 'wuesten_salzgekreuzter', 'restriction': 'spear_only'}` · count: 3
  3. **PUZZLE** Speerwurf-Test (Drei Strohpuppen auf Distanz treffen).
  4. **DEFEND** Karawanen-Mondaltar (60 s gegen Wuesten-Wesen).
     - target: `{'defend_pos': 'karawane_altar', 'duration_sec': 60}`
- **Reward:** 200 Gold, 150 XP, Speerschwestern-Rep +40, **Zhar-Eth Mondbinder-Spear**

### Q1b.2 `akt1b_mondbund` — Der Mondbund (Faction)
- **Giver:** Mond-Priesterin Sheh (mystic)
- **Prerequisites:** `akt1b_speerschwester_aufnahme` Stage 2 erreicht
- **Stages:**
  1. **TALK** Sheh.
  2. **INTERACT** Mond-Glyphen in der Karawane (5 Stueck) auf den Saeulen.
     - target: `{'decor_kind': 'moon_glyph'}` · count: 5
  3. **CHOICE** Mondbund-Eid.
     - choices:
       - `{label: 'Mond schwoeren', flag: 'moon_oath_taken'}` — Speerschwestern +30, **Mahnmal-Gilde −15**
       - `{label: 'Eid ablehnen', flag: 'moon_oath_refused'}` — neutral
- **Reward:** 150 Gold, 100 XP. Bei Eid: passiver Mond-Buff (+5% phys, nachts), Faden-Spitze-Item-Vendor
- **on_complete_quote** (Sheh):
  *„Der Mond bindet, was die Sonne loslaesst. Du hast jetzt zwei Faden — oder einen weniger."*

### Q1b.3 `akt1b_wandernde_karawane` — Spuren der Karawane (Lore)
- **Giver:** Karawanen-Haendlerin Yul (vendor)
- **Stages:**
  1. INTERACT 4 Karawanen-Lagerplatz-Stelen entlang des Wuestentempel-Pfads.
  2. RETURN Yul.
- **Reward:** 80 Gold, 60 XP, Codex-Entry „Warum Zhar-Eth wandert"

### Q1b.4 `akt1b_bounty_wuestenwesen` — Wuesten-Bounty (Repeatable)
- **Giver:** Naveth · Bounty (Daily)
- **Stages:** KILL Wuesten-Wesen ×12
- **Reward:** 70 Gold, 50 XP, Speerschwestern-Rep +5

---

<a name="akt-2"></a>
## AKT 2 — GLASGOLDENE RUINEN (Echo-Markt)

### Q2.1 `akt2_asch_prophezeiung` — Die Asch-Prophezeiung
- **Giver:** Bruder Helst (quest/mystic) · **Main**
- **Region:** Akt 2 — Echo-Markt
- **Prerequisites:** `akt1_salzwunde` complete (= `flag.akt1_finished`)
- **Stages:**
  1. **TALK** Helst am Echo-Markt-Tempel.
     - on_complete (Voice-Line `helst_quest_offer_01`): *„Die Asche kennt deinen Namen. Bring mir, was sie sich noch nicht zurueckholen konnte."*
  2. **REACH** Glasgolden-Vorhalle (Tier-1 Sub-Area des Akt-2-Dungeons).
  3. **KILL** Echo-Senator (5) + Goldstaub-Diener (8).
  4. **REACH** Spiegel-Tor-Vorraum (Tier-2).
  5. **KILL** Senator-Geist (Boss, `senator_geist`).
     - target: `{'boss_encounter': 'senator_geist'}`
  6. **COLLECT** Glasgolden-Schluessel (Boss-Drop).
  7. **RETURN** Helst.
- **Reward:** 500 Gold, 400 XP, **Pact-Stone „Helst-Schwur"** (Spirit-Gem [E]), Erblinde-Kirche-Rep +50
- **Consequences:** `flag.akt2_finished = True`, `flag.im_nesh_named = True` (Helst nennt Im-Nesh erstmals)
- **on_complete_quote** (Helst):
  *„Ein Verraeter hat unsere Welt eingeschrieben. Sein Name ist Im-Nesh. Jetzt weisst du es. Es laesst sich nicht mehr ungeschehen machen."*

### Q2.2 `akt2_helst_pact_stones` — Helsts Pakt-Steine (Faction)
- **Giver:** Helst · Faction (Erblinde Kirche)
- **Prerequisites:** `akt2_asch_prophezeiung` Stage 2 erreicht
- **Stages:**
  1. **COLLECT** 3 ungeschnittene Pact-Shards (Drops von Echo-Senatoren).
  2. **INTERACT** Aspekt-Schrein in Helsts Tempel (Pakt-Ritual).
  3. **CHOICE** Pakt-Form waehlen:
     - `{label: 'Kharn-Pakt (Form)', flag: 'pact_kharn', reward_gem: 'pact_form'}`
     - `{label: 'Nheyra-Pakt (Zeit)', flag: 'pact_nheyra', reward_gem: 'pact_time'}`
     - `{label: 'Ousen-Pakt (Geist)', flag: 'pact_ousen', reward_gem: 'pact_mind'}`
- **Reward:** 1× Pact-Stone (Skill-Gem [E]) je nach Choice, Erblinde-Kirche-Rep +40
- **Consequences:** `flag.player_pact = <choice>` (wirkt sich auf Akt-5 Reveal aus)

### Q2.3 `akt2_echo_handel` — Echo-Handel (Side)
- **Giver:** Senator-Geist Vorul (vendor)
- **Stages:**
  1. TALK Vorul.
  2. COLLECT 5 Goldstaub-Pakete (Drops von Goldstaub-Dienern).
  3. RETURN Vorul → schaltet Echo-Markt-Vendor-Inventar frei (Glasgolden-Items).
- **Reward:** 150 Gold, 100 XP, Vendor-Unlock

### Q2.4 `akt2_otreth_glas_gravur` — Glas-Gravur (Crafting)
- **Giver:** Otreth-Lehrling Salir (smith)
- **Prerequisites:** Otreth in Brassweir hat `akt1_otreth_stein` complete
- **Stages:**
  1. TALK Salir.
  2. COLLECT 1× Spiegel-Splitter (vom Spiegel-Stalker).
  3. COLLECT 3× Uncut Memory-Shard.
  4. INTERACT Salir-Werkbank: Glas-Gem schleifen lassen.
- **Reward:** 200 Gold, 150 XP, **Glasgolden-Skill-Gem** (Random Skill aus Aspekt-Pool)
- **Consequences:** Otreth lernt Glas-Engraving (oeffnet neue Crafting-Option in Brassweir)

### Q2.5 `akt2_goldstaub_erinnerung` — Goldstaub-Erinnerungen (Lore)
- **Giver:** Mara (sie taucht in Echo-Markt auf — Cross-Chain Stage 2)
- **Stages:**
  1. TALK Mara.
  2. INTERACT 4 Goldstaub-Echo-Events (random spawns im Akt-2-Dungeon).
     - target: `{'event': 'goldstaub_echo'}` · count: 4
  3. RETURN Mara.
- **Reward:** 180 Gold, 130 XP, **Memory-Fragments** ×5, Codex-Entry „Der Glasgoldene Hof"
- **on_complete_quote** (Mara):
  *„Sie hatten alles. Sogar Zeit. Verschwendet. Habe ich auch."*

### Q2.6 `akt2_bounty_goldstaub_diener` — Goldstaub-Bounty
- **Giver:** Vorul · Bounty
- **Stages:** KILL Goldstaub-Diener ×15
- **Reward:** 100 Gold, 70 XP, Echo-Markt-Vendor-Discount 10 %

### Q2.7 `akt2_velharn_vorhof` — Spiegel-Tor finden (Hidden)
- **Discovery:** INTERACT mit Spiegel-Bruchstueck im Akt-2-Library-Room
- **Stages:**
  1. INTERACT Spiegel-Bruchstueck.
  2. COLLECT 3 Spiegel-Splitter (in versteckten Crannies des Akt-2-Dungeons).
  3. REACH Spiegel-Tor-Vorraum (entkoppelt von Hauptquest).
  4. INTERACT Spiegel-Tor: aktiviert Akt-5-Vorschau (geheimer Spiegel-Tafel-Raum mit Velharn-Lore).
- **Reward:** Lore-Codex „Spiegelstadt", **Akt-5-Preview** Map-Notiz

---

<a name="akt-3"></a>
## AKT 3 — DIE ASCHENFELDER (Saeulen-von-Helst)

### Q3.1 `akt3_asch_pakt` — Der Asch-Pakt ✅ (existiert)
- **Status:** ✅ in `sf/quest_data.py` (Vehren-Boss)
- **Erweiterung empfohlen:** `prerequisites = ['akt2_asch_prophezeiung']`, `consequences: faction_rep.tribunal -= 50, erblinde += 30`

### Q3.2 `akt3_erblinder_priester_trial` — Die Augen-Bind-Probe (Faction)
- **Giver:** Acolyt der Erblinden Kirche (quest)
- **Region:** Akt 3 — Saeulen-von-Helst
- **Prerequisites:** Erblinde-Kirche-Rep >= 50
- **Stages:**
  1. TALK Acolyt.
  2. **CHOICE** Probe annehmen?
     - `{label: 'Ja, ich binde mir die Augen', flag: 'blind_trial_taken'}` — eroeffnet Stage 3-5
     - `{label: 'Nein', flag: 'blind_trial_refused'}` — Quest endet, Erblinde-Rep −20
  3. **TIMED** Erschlage 3 Tribunal-Konstrukte mit verbundenen Augen (Blind-Mechanik: Bildschirm 80 % dunkel, nur Sound-Cues).
     - target: `{'bestiary_key': 'tribunal_konstrukt', 'restriction': 'blind'}` · count: 3 · duration_sec: 300
  4. RETURN Acolyt → Schwur-Ritual.
- **Reward:** 400 Gold, 300 XP, **Erblinde-Buff** „Hoeren statt sehen" (+10 % CDR, +30 % Echolocation-Range), Erblinde-Kirche-Rep +60
- **Consequences:** Erblinde-Vendor Pact-Stones-Preise −30 %

### Q3.3 `akt3_letzte_legion` — Die Letzte Legion (Side)
- **Giver:** Asche-Haendler Brulm (vendor)
- **Stages:**
  1. TALK Brulm.
  2. COLLECT 7 Letzte-Legion-Brandzeichen (Drops von Asch-Soldaten).
  3. INTERACT 3 Legion-Grabstelen im Aschenfeld.
     - on_complete (Stelen-Lore): *„Wir warten auf den Befehl. Niemand hat ihn gegeben."*
  4. **CHOICE** Letzte-Legion-Befehl erteilen?
     - `{label: 'Aufloesen (Frieden)', flag: 'legion_dissolved'}` — Asch-Soldaten despawnen aus Aschenfeld
     - `{label: 'Stehen lassen', flag: 'legion_eternal'}` — Asch-Soldaten bleiben, Bounty bleibt repeatable
- **Reward:** 250 Gold, 180 XP, **Verbrannte Treue** (Two-Hand Sword [M], Items #7), Codex „Valsas Soldaten"

### Q3.4 `akt3_tribunal_infiltration` — Tribunal-Infiltration (Hidden)
- **Discovery:** INTERACT mit Tribunal-Befehl-Decor (Spaeher-Lager im Lava-Pit)
- **Prerequisites:** Tribunal-Rep <= −30
- **Stages:**
  1. INTERACT Tribunal-Befehl.
  2. REACH Tribunal-Versteck (versteckter Sub-Bereich des Lava-Pits).
  3. **TIMED** Drei Akten stehlen ohne entdeckt zu werden (Stealth, 90 s).
     - target: `{'item_kind': 'tribunal_akte', 'restriction': 'stealth'}` · count: 3
  4. RETURN Eldon in Brassweir → Beweise abliefern.
- **Reward:** 600 Gold, 500 XP, Mahnmal-Gilde-Rep +50, **Tribunal-Rep −80** (du bist offizieller Staatsfeind), Codex „Tribunal-Hierarchie"

### Q3.5 `akt3_bounty_asch_wolf` — Asch-Wolf-Bounty
- **Giver:** Brulm · Bounty
- **Stages:** KILL Asch-Wolf ×8
- **Reward:** 90 Gold, 60 XP, Tribunal-Konstrukt-Spawn-Chance −5 % (Asch-Wolf hielt sie an)

### Q3.6 `akt3_valsa_traene` — Valsas Traene (Lore)
- **Giver:** Tribunal-Doppelagent Korren (mystic)
- **Voice-Notes:** Korren flueschert, schaut sich um.
- **Stages:**
  1. TALK Korren (er muss erst durch Akt-3-Streufeld gefunden werden).
  2. INTERACT 3 Asche-Stelen (in besonders heissen Bereichen).
  3. **PUZZLE** Asche-Spirale ausrichten (Decor-Rotation in Boss-Vorraum).
  4. COLLECT „Valsas Traene" (Lore-Item, kann angeblich Tote wiederbringen — siehe Lore 11.3).
- **Reward:** Codex „Valsas Tod war Verrat", **Endgame-Quest-Item** (wird in Endgame 11.3 freigeschaltet)
- **on_complete_quote** (Korren):
  *„Sie wurde nicht im Krieg getoetet. Im-Nesh kam zuerst. Helst weiss das. Er sagt nichts. Frag dich, warum."*

### Q3.7 `akt3_inquisitions_klinge` — Tribunal-Stahl (Crafting)
- **Giver:** Brulm
- **Prerequisites:** `akt3_letzte_legion` Stage 2 abgeschlossen
- **Stages:**
  1. COLLECT 5 Inquisitions-Klingenmesser-Drops (vom Bestiarium-Mob).
  2. INTERACT Brulms Aschen-Schmelze (Decor in Saeulen-von-Helst).
  3. **CHOICE** Schmiede-Stil:
     - `{label: 'Tribunal-Klinge (Hard-Hitter)', flag: 'forged_tribunal_blade'}`
     - `{label: 'Erblinde-Klinge (Holy-Damage)', flag: 'forged_erblinde_blade'}`
- **Reward:** Unique-Schwert je nach Choice (One-Hand Sword [M])

---

<a name="akt-4"></a>
## AKT 4 — DAS WURZELGRAB (Knoten-Markt)

### Q4.1 `akt4_shulavh_faden` — Shulavhs Faden (Main, **Choice-Quest**)
- **Giver:** Vossharil die Dreimalige (quest)
- **Region:** Akt 4 — Knoten-Markt → Wurzelgrab
- **Prerequisites:** `akt3_asch_pakt` complete + Helst- ODER Vossharil-Sponsorship
- **Stages:**
  1. TALK Vossharil. *(Voice: „Sie ruft. Sie ruft seit achthundert Jahren. Du bist der erste, der lauter ist als sie.")*
  2. REACH Wurzelgrab-Tier-1 (Aussen-Wurzeln).
  3. KILL Wurzel-Spinne (8) + Faden-Gebundener (6).
  4. REACH Wurzelgrab-Tier-2 (Kambium-Hoehle).
  5. **DEFEND** Vossharil-Ritual (90 s, Mark-Krieger-Wellen).
     - target: `{'defend_pos': 'vossharil_circle', 'duration_sec': 90}`
  6. REACH Wurzelgrab-Tier-3 (Mark-Kammer).
  7. KILL Hohler Sohn (Mini-Boss, optionale Phase-Sub-Quest).
  8. REACH Faden-Mutter-Arena.
  9. **CHOICE** (Boss-Encounter) Shulavh schonen oder bezwingen:
     - `{label: 'Shulavh heilen (Pakt-Wahl)', flag: 'shulavh_spared', condition: 'must_complete_3_phase_dialogue'}` — **Schwerer Weg**: alle 3 Phasen muessen mit Spezial-Dialog-Options abgeschlossen werden
     - `{label: 'Shulavh bezwingen', flag: 'shulavh_defeated'}` — Standard-Bossfight
  10. RETURN Vossharil.
- **Reward:**
  - 1000 Gold, 800 XP
  - Bei *spared*: **„Wahre Name Im-Neshs"** (Story-Reveal, freigeschaltet in Akt 5 Dialog), **Faden-Spitze** (Spear [E], #19)
  - Bei *defeated*: **„Vossharils Bruder"** (Dagger [M], #13), Knochenwitwen-Rep −20 (Vossharil ist enttaeuscht)
- **Consequences:** `flag.shulavh_outcome = <choice>`, `flag.akt4_finished = True`

### Q4.2 `akt4_knochenwitwen_aufnahme` — Knochenwitwen-Trial (Faction)
- **Giver:** Vossharil
- **Prerequisites:** Klasse = Witch ODER Knochenwitwen-Rep >= 30
- **Stages:**
  1. TALK Vossharil.
  2. KILL 3 Tribunal-Spaeher (sie jagen Knochenwitwen).
  3. **DEFEND** Drei-Maetterin-Ritual (60 s).
  4. **CHOICE** Drei-Maetterin-Eid:
     - `{label: 'Schwoeren', flag: 'witch_oath'}` — Knochenwitwen-Rep +60, **Tribunal −40, Erblinde −20**
     - `{label: 'Ablehnen', flag: 'witch_refused'}` — neutral
- **Reward:** Skelett-Familiar (passiver Begleiter, sf/entities.py-Erweiterung), **Vossharils Bruder** Dagger garantiert (auch wenn `akt4_shulavh_faden` = spared)

### Q4.3 `akt4_hohle_sohn` — Der Hohle Sohn (Side)
- **Giver:** Hohler Sohn (mystic, spricht NICHT — Quest startet via Gesten-Cutscene)
- **Stages:**
  1. INTERACT Hohler-Sohn-NPC im Knoten-Markt → er deutet auf die Wurzeln.
  2. REACH 3 versteckte Hohle-Sohn-Erinnerungsorte (Wurzelgrab).
  3. KILL Faden-Gebundener (Boss-Variante, ehemaliger Mensch des Hohlen Sohns).
  4. RETURN Hohler Sohn → Cutscene: er senkt den Kopf, du verstehst.
- **Reward:** Codex „Was Shulavh adoptiert hat", **Faden-Anker** (Amulett mit +20 Faction-Rep zur kleinsten Faction)

### Q4.4 `akt4_drei_tode` — Vossharils Drei Tode (Lore)
- **Giver:** Vossharil
- **Stages:**
  1. TALK Vossharil → 3 Lore-Fragmente suchen.
  2. INTERACT 3 Grab-Stelen in der Krypta (Akt 1), den Aschenfeldern (Akt 3) und im Wurzelgrab (Akt 4) — eine pro Tod.
  3. RETURN Vossharil → sie erzaehlt ihre dritte Geschichte (Voice-Line `vossharil_lore_03`).
- **Reward:** Codex „Die Dreimalige", **Mahnmal-Marke III** ×2

### Q4.5 `akt4_wurzel_gift` — Wurzel-Gift (Crafting)
- **Giver:** Wurzel-Apotheker Bran (vendor)
- **Stages:**
  1. COLLECT 5 Wurzel-Faser + 3 Tribunal-Klingenmesser-Drops.
  2. INTERACT Bran-Apotheke (Brau-Vorgang).
- **Reward:** **Wurzel-Gift-Flask** (passt auf Daggers/Spears, Poison-DOT)

### Q4.6 `akt4_bounty_fadengebundene` — Faden-Bounty (Repeatable)
- **Giver:** Knochen-Hexe Marvel (smith) · Bounty
- **Stages:** KILL Faden-Gebundener ×12
- **Reward:** 110 Gold, 80 XP, Knochenwitwen-Rep +5

### Q4.7 `akt4_versteckter_garten` — Versteckter Saatkind-Hain (Hidden)
- **Discovery:** INTERACT mit Saatträger-Wegmarker am Knoten-Markt-Rand
- **Prerequisites:** Klasse = Ranger ODER Druid ODER Saattraeger-Rep >= 20
- **Stages:**
  1. INTERACT Wegmarker.
  2. REACH Saatkind-Hain (versteckte Sub-Karte).
  3. **PUZZLE** Drei-Tiere-Steine in Reihenfolge Baer-Wolf-Wyvern aktivieren.
  4. KILL Korrumpierter Saatkind-Waechter (Mini-Boss).
  5. COLLECT „Saatkind-Erinnerung".
- **Reward:** Codex „Saatkinder", **Saatkind-Beil** (Two-Hand Axe [E], #11), Saattraeger-Rep +50

---

<a name="akt-5"></a>
## AKT 5 — DIE SPIEGELSTADT VELHARN (Spiegelhof)

### Q5.1 `akt5_drei_zeiten` — Die Drei Zeiten (Main, **Puzzle + Choice**)
- **Giver:** Erster Senator Voraius (quest)
- **Prerequisites:** `akt4_shulavh_faden` complete
- **Stages:**
  1. TALK Voraius.
  2. REACH Glasgolden-Zeit-Schicht.
  3. **PUZZLE** Drei Zeit-Glyphen aktivieren in Reihenfolge Glasgolden → Götterkrieg → Gegenwart.
  4. KILL Erster Senator Glasgolden (Phase 1 von Boss).
  5. REACH Goetterkrieg-Zeit-Schicht.
  6. KILL Brennender General (Phase 2).
  7. REACH Gegenwarts-Zeit-Schicht.
  8. KILL Hohler Koenig (Phase 3).
  9. **REVEAL-CUTSCENE** Ousen identifiziert sich als die Stimme.
  10. **CHOICE** Im-Nesh-Disguise-Verdacht aussprechen:
      - `{label: 'Korven ist Im-Nesh', flag: 'im_nesh_is_korven'}` — Setup fuer Akt 6
      - `{label: 'Helst ist Im-Nesh', flag: 'im_nesh_is_helst'}` — Setup fuer Akt 6
      - `{label: 'Weiss noch nicht', flag: 'im_nesh_uncertain'}` — laesst Choice fuer Akt 6 offen
  11. RETURN Voraius.
- **Reward:** 2000 Gold, 1500 XP, **„Senatorin-Stahl"** (Sword [L], #8), Ousen-Pakt-Buff (passiv), `flag.akt5_finished = True`

### Q5.2 `akt5_senator_streit` — Senatoren-Streit (Side)
- **Giver:** Voraius
- **Stages:**
  1. TALK 3 Geist-Senatoren (alle 3 in unterschiedlichen Zeit-Schichten).
  2. **CHOICE** Mediation:
     - `{label: 'Glasgolden-Faktion', flag: 'senate_glasgold'}` — Erschliesst Glas-Items
     - `{label: 'Goetterkrieg-Faktion', flag: 'senate_war'}` — Erschliesst Asche-Items
     - `{label: 'Stille fordern', flag: 'senate_silence'}` — Senatoren despawnen, Akt-5-Map ruhiger
- **Reward:** 800 Gold, 600 XP, Vendor-Inventar-Variation je nach Choice

### Q5.3 `akt5_stunden_spiegel_meister` — Spiegel-Magier-Aufnahme (Faction)
- **Giver:** Spiegel-Magierin Nheya (mystic)
- **Prerequisites:** Spieler hat alle 3 Zeit-Schichten besucht
- **Stages:**
  1. TALK Nheya.
  2. **PUZZLE** Stunden-Spiegel-Test (Zeit-Switch-Mechanik: Mobs in 3 Zeitschichten gleichzeitig kontern).
  3. RETURN Nheya.
- **Reward:** **Stunden-Sprung-Skill** (Active-Skill: 1× pro Boss-Fight zurueck-zurueck in der Zeit, 60 s CD)
- **Consequences:** Spiegel-Magier-Faction-Unlock (kleine Faction, kein Konflikt)

### Q5.4 `akt5_velharn_geschichte` — Velharns Geschichte (Lore)
- **Giver:** Mara die Mahnerin (Cross-Chain Stage 3)
- **Stages:**
  1. TALK Mara im Spiegelhof.
  2. INTERACT Lore-Tafeln in den 3 Zeit-Schichten (4 + 4 + 4 = 12 Tafeln, jeweils Akt-Geschichte).
  3. RETURN Mara.
- **Reward:** Codex „Die Drei Zeiten Velharns", **Memory-Fragments** ×15
- **on_complete_quote** (Mara):
  *„Drei Zeiten gleichzeitig. So sehe ich immer. Du wirst es lernen, oder du wirst es vergessen. Beides ist Heimat."*

### Q5.5 `akt5_bounty_stunden_wandler` — Zeit-Wandler-Bounty
- **Giver:** Voraius · Bounty
- **Stages:** KILL Stunden-Wandler ×10
- **Reward:** 200 Gold, 150 XP, Spiegel-Magier-Rep +5

### Q5.6 `akt5_korven_oder_helst` — Wer ist Im-Nesh? (Hidden, **Reveal-Setup**)
- **Discovery:** Automatisch ausgeloest wenn `akt5_drei_zeiten` Stage 9 (Ousen-Reveal) erreicht
- **Stages:**
  1. **CONDITIONAL** Wenn `flag.player_pact == 'pact_ousen'`: zusaetzliche Hint-Cutscene mit Mara.
  2. INTERACT 3 alte Briefe (1 in Brassweir-Korven-Schreibtisch, 1 in Echo-Markt-Helst-Tempel, 1 im Wurzelgrab).
  3. **CHOICE** (finalisiert die Akt-5-CHOICE): wer ist Im-Nesh?
- **Reward:** Codex „Die Maske", legt Akt-6-NPC-Identitaet fest: `korven_helst_reveal` zeigt entweder Korven oder Helst Lore-Konfrontation.

---

<a name="akt-6"></a>
## AKT 6 — DIE DREI WUNDEN

### Q6.1 `akt6_salzwunde_lesen` — Die Salzwunde lesen (Main)
- **Giver:** Wunden-Lesende Tehrnal
- **Region:** Akt 6 — Drei-Wunden-Lager → Salzwunde
- **Prerequisites:** `akt5_drei_zeiten` complete
- **Stages:**
  1. TALK Tehrnal.
  2. REACH Salzwunde-Dungeon.
  3. KILL Ertrunkene Wesen (Mob-Pool).
  4. KILL Ertrunkene Koenigin (Boss).
     - target: `{'boss_encounter': 'ertrunkene_koenigin'}`
  5. INTERACT Salz-Pakt-Tafel (Boss-Drop platziert auf Lese-Pult).
  6. RETURN Tehrnal.
- **Reward:** 1500 Gold, 1200 XP, **„Verraten Sieben"** (Crossbow [E], #34), `flag.wound_salt_read = True`

### Q6.2 `akt6_aschwunde_lesen` — Die Aschwunde lesen (Main)
- **Giver:** Tehrnal
- **Stages:** REACH Aschwunde-Dungeon → KILL Echo-Drache (Boss `echo_drache`) → COLLECT Aschen-Pakt-Tafel → RETURN
- **Reward:** 1500 Gold, 1200 XP, **„Sieben-Atem-Stab"** (Staff [X], #42), `flag.wound_ash_read = True`

### Q6.3 `akt6_hohlwunde_lesen` — Die Hohlwunde lesen (Main)
- **Giver:** Tehrnal
- **Stages:** REACH Hohlwunde-Dungeon → KILL Nicht-Gott (Boss `nicht_gott`) → COLLECT Hohle-Pakt-Tafel → RETURN
- **Reward:** 1500 Gold, 1200 XP, **„Hohle Zunge"** (Dagger [E], #14), `flag.wound_hollow_read = True`

### Q6.4 `akt6_pakt_uebersetzen` — Pakt-Uebersetzung (Main-Finale)
- **Giver:** Tehrnal
- **Prerequisites:** Alle 3 Wunden gelesen (`wound_salt_read` + `wound_ash_read` + `wound_hollow_read`)
- **Stages:**
  1. INTERACT Drei-Wunden-Pakt-Tafel (Tehrnal-Tisch).
  2. **PUZZLE** Pakt-Glyphen in der korrekten Reihenfolge anordnen (Sprache-Aspekt-Logik).
  3. RETURN Tehrnal → Tehrnal liest das endgueltige Wort: **Im-Neshs wahre Identitaet wird benannt**.
- **Reward:** 3000 Gold, 2500 XP, **„Tintendolch von Im-Nesh"** (Mythic Dagger [X], #15, Quest-Item, NICHT verkaufbar), `flag.akt6_finished = True`

### Q6.5 `akt6_korven_helst_reveal` — Die Demaskierung (Cross-Chain, **Choice**)
- **Giver:** Mara (Akt-6-Stage)
- **Stages:**
  1. TALK Mara.
  2. TALK `korven_helst_reveal`-NPC (Korven ODER Helst, je nach `flag.im_nesh_is_*`).
  3. **CHOICE** Konfrontation:
     - `{label: 'Wahrheit fordern (peaceful)', flag: 'imnesh_revealed_peaceful'}`
     - `{label: 'Sofort angreifen (hostile)', flag: 'imnesh_revealed_hostile'}`
  4. KILL Korven ODER Helst (Mini-Boss-Encounter)
     - target: `{'boss_encounter': 'korven_imnesh' OR 'helst_imnesh', 'condition': 'flag.im_nesh_is_*'}`
- **Reward:** 1000 Gold, 800 XP, Codex „Wer Im-Nesh wirklich war"
- **Consequences:** Der jeweils andere NPC bleibt Lebend und tritt in Akt 7 als Verbuendeter auf.

### Q6.6 `akt6_bounty_anomalien` — Anomalien-Bounty (Repeatable)
- **Giver:** Tehrnal · Bounty
- **Stages:** KILL Anomalien-Mobs ×6 (sehr selten)
- **Reward:** 300 Gold, 250 XP, Memory-Fragments ×3

---

<a name="akt-7"></a>
## AKT 7 — DAS HOHLWORT

### Q7.1 `akt7_drei_muetter_trial` — Drei-Muetter-Trial (Ascendancy)
- **Giver:** Die Drei Muetter (mystic-Trias)
- **Prerequisites:** `akt6_pakt_uebersetzen` complete
- **Stages:**
  1. TALK Drei Muetter (Trio-Dialog mit Voice-IDs 8a/8b/8c).
  2. REACH Trial 1 — Mutter Eins (Geduld-Trial: 5 min ohne Hit).
  3. REACH Trial 2 — Mutter Zwei (Strenge-Trial: nur 3 Skills nutzbar).
  4. REACH Trial 3 — Mutter Drei (Wahnsinn-Trial: invertierte Steuerung).
  5. **CHOICE** Ascendancy:
     - `{label: 'Ascendancy A: Gnade', flag: 'asc_mercy'}`
     - `{label: 'Ascendancy B: Wille', flag: 'asc_will'}`
     - `{label: 'Ascendancy C: Bindung', flag: 'asc_bond'}`
- **Reward:** **Ascendancy-Klassen-Upgrade** (3 Ascendancy-Skill-Slots freigeschaltet, [sf/progression.py](sf/progression.py)-Erweiterung), Codex „Wer die Drei Muetter sind"

### Q7.2 `akt7_im_nesh_dialog` — Dialog mit Im-Nesh
- **Giver:** Im-Nesh's Echo-NPC
- **Prerequisites:** `akt7_drei_muetter_trial` complete
- **Stages:**
  1. TALK Im-Nesh-Echo (3 Dialog-Stages, jeweils mit Choice der Antwort).
  2. **CONDITIONAL** Wenn Choice in Dialog drei = „verstehe deinen Schmerz" → freigeschaltete Diplomatie-Option in `akt7_im_nesh_boss`.
- **Reward:** Codex „Im-Neshs Argument" (Pakt-Text in voller Laenge)
- **Voice-Hint:** Diese Quest nutzt die spezielle Im-Nesh-Voice-IDs aus `VELGRAD_VOICE_CASTING §IV`.

### Q7.3 `akt7_im_nesh_boss` — Im-Nesh-Confrontation (Final Boss)
- **Giver:** auto-triggered nach `akt7_im_nesh_dialog`
- **Stages:**
  1. REACH Hohlwort-Arena.
  2. KILL Im-Nesh Phase 1 („Der Hoefliche").
     - target: `{'boss_encounter': 'im_nesh', 'phase': 1}`
  3. KILL Im-Nesh Phase 2 („Der Verzweifelte").
  4. KILL Im-Nesh Phase 3 („Der Hundertzuengige", Layer-Voice).
  5. **CONDITIONAL** Wenn Diplomatie-Option aus Q7.2 verfuegbar: Wahl Phase 3 vs Reden.
- **Reward:** 10000 Gold, 8000 XP, **„Der Erste Eid"** (Two-Hand Sword [X, Mythic], #9), `flag.akt7_finished = True`

### Q7.4 `akt7_finale_wahl` — Die letzte Wahl (Endings, **Choice**)
- **Giver:** auto-triggered nach `akt7_im_nesh_boss`
- **Stages:**
  1. **CHOICE** Drei Endings:
     - `{label: 'A: Pakt erneuern (Sacrifice)', flag: 'ending_sacrifice', save_action: 'char_to_memorial'}`
       Spieler wird Hohler Geweihter. Welt ueberlebt. Char-Save wird in Memorial-Eintrag konvertiert (z. B. `saves/memorial/<char_name>.json`).
     - `{label: 'B: Pakt umschreiben (Im-Nesh-Path)', flag: 'ending_betrayer', save_action: 'unlock_betrayer_atlas'}`
       Spieler tritt in Im-Neshs Fussstapfen. Endgame-Modus „Verraeter-Tour" freigeschaltet (eigener Atlas-Tab).
     - `{label: 'C: Aithein wecken', flag: 'ending_dreamer', save_action: 'unlock_dreamer_atlas'}`
       Letzter-Traeumer-Reveal. Endgame-Modus „Traeumer-Pfad" (Atlas mit ueberschriebenen Maps).
- **Reward (alle Endings):** Atlas-Modus-Freischaltung gemaess Choice, Achievement, End-Cinematic
- **Consequences:** `flag.game_finished = True`, `flag.ending = <choice>`

---

<a name="cross-akt"></a>
## CROSS-AKT-CHAINS (Multi-Akt-NPCs)

### Mara-Chain (Akt 1 → 7)
Stage 1: `akt1_mara_spur` ✅
Stage 2: `akt2_goldstaub_erinnerung`
Stage 3: `akt5_velharn_geschichte`
Stage 4 (Akt 6): `akt6_korven_helst_reveal` (Mara fuehrt jetzt direkt)
Stage 5 (Akt 7): Mara verschwindet in Cutscene vor Hohlwort-Arena. Reveal: sie war eine Echo-Anomalie aus einer welkenden Parallelwelt. Endgame-Atlas-Quest-Giver.

### Tameris-Chain (Akt 1 → 5)
Stage 1: `akt1_tameris_schwester`
Stage 2 (Akt 1b): `akt1b_speerschwester_aufnahme` (Tameris ist Mentorin)
Stage 3 (Akt 3): Tameris-Schwester-Hohle-Bestaetigung (Cutscene, kein Quest-Item)
Stage 4 (Akt 5): Tameris-Echo in Velharn (3 Zeit-Schichten, alle drei Tameris-Versionen sprechen)
Stage 5 (Akt 6): Tameris stirbt in Akt-6-Cutscene ODER ueberlebt — abhaengig von `flag.tameris_sister_*` aus Q1.4.

### Korven/Helst-Im-Nesh-Chain (Akt 1 → 6)
Setup:   Akt 1 Korven-Hauptquest baut Vertrauen.
Setup:   Akt 2 Helst-Hauptquest baut Vertrauen.
Twist:   Akt 5 `akt5_korven_oder_helst` setzt Verdacht.
Reveal:  Akt 6 `akt6_korven_helst_reveal` enthuellt.
Final:   Akt 7 Im-Nesh-Boss ist die Manifestation des Disguise-Charakters.

---

<a name="endgame"></a>
## ENDGAME-ATLAS-QUEST-CHAINS

### A1 `atlas_aspekt_echos` — Die Aspekt-Echos
- **Giver:** Mara (Endgame)
- **Stages:** Besiege alle 5 Aspekt-Echo-Bosse (Kharn, Nheyra, Ousen, Valsa, Shulavh).
- **Reward:** **Aithein-Fragment** ×1 pro Boss, Codex pro Aspekt

### A2 `atlas_aithein_echo` — Aithein-Echo (Pinnacle)
- **Prerequisites:** Alle 5 Aithein-Fragmente
- **Stages:** Atlas-Map „Aithein-Schlaf" abschliessen, Aithein-Echo besiegen.
- **Reward:** **Sieben-Atem-Stab** Mythic-Upgrade

### A3 `atlas_der_achte` — Die fehlende Aspektin (Pinnacle, Lore 11.4)
- **Discovery:** Hidden — INTERACT mit Acht-Punkt-Stern-Decor in einer Welkenden Welt
- **Stages:** Sammle 8 Aspekt-Echo-Drops + besiege Der-Achte in versteckter Map.
- **Reward:** **Der-Achte-Echo-Begleiter** (passiver Begleiter, +5 % alle Stats)

### A4 `atlas_kharns_traene` — Kharns Traene (Endgame-Lore 11.3)
- **Prerequisites:** `akt3_valsa_traene` complete (Valsa-Traene gesammelt)
- **Stages:**
  1. COLLECT 3 Kharn-Traenen-Fragmente (in welkenden Welten).
  2. **CHOICE** Traene auf einen toten NPC anwenden:
     - `{label: 'Tameris zurueckbringen' (nur wenn tot)`}
     - `{label: 'Korven/Helst zurueckbringen' (nur wenn tot)`}
     - `{label: 'Player-Memorial-Eintrag wiederbeleben' (Hardcore-Char retten)`}
- **Reward:** NPC-Resurrection (Welt-State-Mod), Endgame-Cutscene

### A5 `atlas_letzter_traeumer` — Der Letzte Traeumer (Lore 11.6)
- **Discovery:** Nur wenn `flag.ending == 'ending_dreamer'`
- **Stages:** Atlas-Modus „Traeumer-Pfad" durchspielen, finale Cutscene mit Ousen-Voice.
- **Reward:** Achievement „Atme. Wieder. Bitte." + Hidden-Klassen-Skin-Unlock

---

## QUEST-DEPENDENCY-GRAPH (Mermaid-tauglich, fuer Visualization)

```
akt1_salzwunde
  └─ akt2_asch_prophezeiung
       └─ akt3_asch_pakt
            └─ akt4_shulavh_faden (CHOICE: spared/defeated)
                 └─ akt5_drei_zeiten
                      └─ akt6_salzwunde_lesen + akt6_aschwunde_lesen + akt6_hohlwunde_lesen
                           └─ akt6_pakt_uebersetzen
                                └─ akt7_drei_muetter_trial (ASCENDANCY)
                                     └─ akt7_im_nesh_dialog
                                          └─ akt7_im_nesh_boss
                                               └─ akt7_finale_wahl (3 ENDINGS)
                                                    ├─ ending_sacrifice
                                                    ├─ ending_betrayer  → Verraeter-Atlas
                                                    └─ ending_dreamer   → Traeumer-Atlas + atlas_letzter_traeumer
```

---

## QUEST-COUNT-SUMMARY

| Akt | Main | Faction | Side | Lore | Crafting | Bounty | Hidden | Total |
|---|---|---|---|---|---|---|---|---|
| 1  | 1✅ | 1 | 1 | 1✅ | 1✅ | 1 | 1 | 7 |
| 1b | 1  | 1 | — | 1 | — | 1 | — | 4 |
| 2  | 1  | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| 3  | 1✅ | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| 4  | 1  | 1 | 1 | 1 | 1 | 1 | 1 | 7 |
| 5  | 1  | 1 | 1 | 1 | — | 1 | 1 | 6 |
| 6  | 4 (Drei-Wunden+Pakt) | — | 1 | — | — | 1 | — | 6 |
| 7  | 3 | — | — | — | — | — | 1 (Ascendancy) | 4 |
| Endgame-Atlas | — | — | — | — | — | — | 5 | 5 |
| **Total** | **13** | **6** | **5** | **6** | **4** | **7** | **11** | **53** |

✅ = bereits in `sf/quest_data.py`. Rest implementierbar.

---

## ITEM-DROP-CROSSREF (Welche Quest gibt welches Unique?)

| Item | Akt | Quest | Item-Bibel-# |
|---|---|---|---|
| Mahnmal-Marke VII (Crossbow [M]) | 1 | `akt1_salzwunde` | #31 |
| Tameris' Suchender (Spear [M]) | 1 | `akt1_tameris_schwester` | #17 |
| Zhar-Eth Mondbinder (Spear [E]) | 1b | `akt1b_speerschwester_aufnahme` | #18 |
| Pact-Stone (Helst-Schwur) | 2 | `akt2_asch_prophezeiung` | n/a (Spirit-Gem) |
| Verbrannte Treue (2H-Sword [M]) | 3 | `akt3_letzte_legion` | #7 |
| Asche-Aspekt (Wand [E]) | 3 | `akt3_asch_pakt` ✅ | #37 |
| Faden-Spitze (Spear [E]) | 4 | `akt4_shulavh_faden` (spared) | #19 |
| Vossharils Bruder (Dagger [M]) | 4 | `akt4_knochenwitwen_aufnahme` | #13 |
| Saatkind-Beil (2H-Axe [E]) | 4 | `akt4_versteckter_garten` | #11 |
| Senatorin-Stahl (1H-Sword [L]) | 5 | `akt5_drei_zeiten` | #8 |
| Verraten Sieben (Crossbow [E]) | 6 | `akt6_salzwunde_lesen` | #34 |
| Sieben-Atem-Stab (Staff [X]) | 6 | `akt6_aschwunde_lesen` | #42 |
| Hohle Zunge (Dagger [E]) | 6 | `akt6_hohlwunde_lesen` | #14 |
| Tintendolch von Im-Nesh (Dagger [X]) | 6 | `akt6_pakt_uebersetzen` | #15 |
| Der Erste Eid (2H-Sword [X]) | 7 | `akt7_im_nesh_boss` | #9 |

Restliche Uniques (~35 Stueck): verteilt auf Side-Bounty-Rewards, Vendor-Rotationen, Atlas-Drops.

---

## REPUTATIONS-MATRIX (welche Quest beeinflusst welche Faktion)

| Quest | Mahnmal | Erblinde | Tribunal | Saattraeger | Knochen | Speer | Stille |
|---|---|---|---|---|---|---|---|
| akt1_salzwunde | +30 | — | — | — | — | — | — |
| akt1_tameris_schwester (spared) | +10 | — | — | — | — | +25 | — |
| akt1_tribunal_geruecht | +20 | — | **−15** | — | — | — | — |
| akt1b_speerschwester_aufnahme | — | — | — | — | — | **+40** | — |
| akt1b_mondbund (oath) | **−15** | — | — | — | — | +30 | — |
| akt2_asch_prophezeiung | — | **+50** | — | — | — | — | — |
| akt2_helst_pact_stones | — | +40 | — | — | — | — | — |
| akt3_asch_pakt | — | +30 | **−50** | — | — | — | — |
| akt3_erblinder_priester_trial | — | **+60** | — | — | — | — | — |
| akt3_tribunal_infiltration | +50 | — | **−80** | — | — | — | — |
| akt4_shulavh_faden (spared) | — | — | — | — | +30 | — | — |
| akt4_knochenwitwen_aufnahme (oath) | — | **−20** | **−40** | — | **+60** | — | — |
| akt4_versteckter_garten | — | — | — | **+50** | — | — | — |

**Konfliktregel:** Erblinde ↔ Tribunal ↔ Knochenwitwen sind Drei-Wege-Konflikt. Tribunal +20 entspricht Erblinde −10 und Knochenwitwen −10 (Beispielregel; pro Quest oben explizit definiert).

---

## NAECHSTE IMPLEMENTIERUNGS-PRIO

1. **Stage-Type-Erweiterungen** (ESCORT/DEFEND/PUZZLE/CHOICE/TIMED/CONDITIONAL) in [sf/quests.py](sf/quests.py).
2. **`Player.faction_rep`** + Save-Migration ([sf/entities.py](sf/entities.py) + [sf/save.py](sf/save.py)).
3. **Q1.4 `akt1_tameris_schwester`** als CHOICE+ESCORT-Quest implementieren (testet beide neuen Stage-Types).
4. **Q1.5–Q1.7** als reine Standard-Stages (TALK/KILL/INTERACT/COLLECT/RETURN), kein neuer Engine-Bedarf.
5. **Faction-Rep-UI** im Codex-Modal.

Akt 1 ist damit narrativ + mechanisch komplett. Phase 2 (Akt 2/3) baut auf Stage-Types auf, die in Phase 1 schon validiert wurden.
