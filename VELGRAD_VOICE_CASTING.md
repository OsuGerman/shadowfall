# VELGRAD — VOICE CASTING

> **Zweck.** Pro NPC + Spieler-Klasse + Boss-Phase eine ElevenLabs-Voice-ID festlegen.
> Das Batch-Script ([tools/voice_gen.py](tools/voice_gen.py)) liest diese Tabelle und generiert
> alle Lines mit konsistenter Stimme.
>
> **Quelle der Charakter-Beschreibungen:** [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md) §VOICE-ACTOR-CASTING-EMPFEHLUNGEN
> + [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md) Teil 12.

---

## STATUS: PREMADE-DEFAULTS EINGETRAGEN

Alle Voice-IDs unten sind **ElevenLabs Premade-Voices** (stabile, account-unabhaengige IDs).
Sie sind primaer englisch — mit `eleven_multilingual_v2` sprechen sie aber Deutsch
passabel. Sie sind ein **funktionierender Starting-Point**:

- Du kannst sofort `python tools/voice_manifest_builder.py && python tools/voice_gen.py --npc korven --limit 3` laufen lassen.
- Falls dir eine Stimme nicht passt: `python tools/voice_list.py --search "deutsch"` listet alle in deinem Account verfuegbaren Voices. Voice-ID austauschen, Manifest neu bauen, erneut generieren.
- Premade-Voices sind im Creator-Plan kostenlos. Voice-Library-Voices (Community-Stimmen) auch — aber `eleven_multilingual_v2` muss unterstuetzt werden.

---

## ANLEITUNG (falls du Voice-IDs ersetzen willst)

1. `python tools/voice_list.py --gender male` (oder `--gender female`, `--search german`)
2. Aus der Tabelle die `voice_id` rauskopieren
3. Unten beim entsprechenden NPC einfuegen (`voice_id:` Feld)
4. `python tools/voice_manifest_builder.py` neu bauen
5. `python tools/voice_gen.py --dry-run` → Kosten checken
6. `python tools/voice_gen.py --npc <name> --limit 3` → Test-Lines
7. Hoeren. Wenn passt: voller Run.

**Spoiler-Lock:** Korven + Helst Twist-Reveal-Lines sollten dieselbe Voice-ID wie Im-Nesh haben (Pitch-Shift via Audio-Filter macht den Unterschied). Erst tauschen wenn du dich fuer eine Reveal-Variante entschieden hast.

---

## I. HAUPT-NPCS (8 Stueck, aus Voice-Pool)

### 1. Korven Vor — Soeldnermeister, Mahnmal-Gilde
- **Lore:** Mittelalter, vernarbtes Gesicht, geschaeftsmaessig freundlich. Eine der zwei Im-Nesh-Disguise-Kandidaten.
- **Stimm-Typ:** Tiefer Bariton, kraeftig, maennlich-volumioes. Hafenmeister-Vibe. **Duester, bedrohlich-ruhig, autoritaer.**
- **Reference:** Tom Waits (rauher) / Mads Mikkelsen (geschaeftsmaessig).
- **Premade-Match:** "Bill" — strong middle-aged male, voll und tief.
- **voice_id:** `pqHfZKP75CvOlQylNhV4`
- **stability:** 0.45 / **similarity_boost:** 0.85 / **style:** 0.55

### 2. Bruder Helst der Hundertjaehrige — Erblinde Kirche
- **Lore:** Geweihter blinder Priester. Spricht in Andeutungen. Zweite Im-Nesh-Disguise-Kandidat.
- **Stimm-Typ:** Tiefer Bass, sehr langsam, weise.
- **Reference:** Christopher Lee / Max von Sydow.
- **Premade-Match:** "George" — warm, narrative, low.
- **voice_id:** `JBFqnCBsd6RMkjVDRZzb`
- **stability:** 0.7 / **similarity_boost:** 0.7 / **style:** 0.2

### 3. Vossharil die Dreimalige — Knochenwitwe
- **Lore:** Dreimal gestorben, zurueckgekehrt. Sehr alt. Spricht mit ihren toten Schwestern.
- **Stimm-Typ:** Alt-Hexe-Kraechzen, bruechig, mit ueberraschender Waerme.
- **Reference:** Maggie Smith (alt) / Tilda Swinton (mystisch).
- **Premade-Match:** "Dorothy" — pleasant elderly female.
- **voice_id:** `ThT5KcBeYPX3keUQqHPh`
- **stability:** 0.45 / **similarity_boost:** 0.7 / **style:** 0.55

### 4. Tameris die Lichtsucherin — Speerschwester
- **Lore:** Trifft den Spieler in Akt 1, sucht ihre verschwundene Schwester. Junge Kriegerin.
- **Stimm-Typ:** Junge Frauenstimme, klar, fokussiert, aber Trauer im Unterton.
- **Reference:** Cate Blanchett (jung) / Rebecca Ferguson.
- **Premade-Match:** "Charlotte" — young adult female, expressive.
- **voice_id:** `XB0fDUnXU5powFXDhCwa`
- **stability:** 0.55 / **similarity_boost:** 0.8 / **style:** 0.35

### 5. Otreth Hohlauge — Gemcutter
- **Lore:** Linkes Auge fehlt (fuer eine Erinnerung verkauft). Praezise, fast manisch.
- **Stimm-Typ:** Mittlerer Bariton, praezise, leicht obsessiv.
- **Reference:** David Tennant (aelter) / Cillian Murphy.
- **Premade-Match:** "Daniel" — authoritative middle-aged British.
- **voice_id:** `onwK4e9ZLuTAKqWW03F9`
- **stability:** 0.6 / **similarity_boost:** 0.75 / **style:** 0.3

### 6. Mara die Mahnerin — Mysterioese Frau (Akt 1–7)
- **Lore:** Echo-Anomalie aus einer Parallelwelt. Spricht in Zukunftsform ueber Vergangenes.
- **Stimm-Typ:** Sanft, vertraeumt, wie hinter einem Schleier.
- **Reference:** Tilda Swinton / Cate Blanchett (Galadriel-Modus).
- **Premade-Match:** "Matilda" — warm, soft, narrative female.
- **voice_id:** `XrExE9yKIg1WjnnlVkGX`
- **stability:** 0.4 / **similarity_boost:** 0.7 / **style:** 0.6

### 7. Inquisitor-General Vehren — Antagonist Akt 3
- **Lore:** Tribunal-Boss. Glaubt aufrichtig, das Richtige zu tun. Moralisch grau.
- **Stimm-Typ:** Tiefer Bass, autoritaer, kalt, mit Ueberzeugung.
- **Reference:** Lance Reddick / Mads Mikkelsen.
- **Premade-Match:** "Arnold" — deep authoritative.
- **voice_id:** `VR6AewLTigWG4xSOukaG`
- **stability:** 0.65 / **similarity_boost:** 0.75 / **style:** 0.4
- **Phase 2 Settings:** stability=0.3, style=0.7 (Valsa-Besessenheit, instabil)

### 8a. Drei Muetter — Mutter Eins (sanft, fragend)
- **Stimm-Typ:** Sanft, fragend, kindlich-alt.
- **Premade-Match:** "Lily" — gentle, warm female.
- **voice_id:** `pFZP5JQG7iQjIQuC4Bku`
- **stability:** 0.5 / **similarity_boost:** 0.7 / **style:** 0.5

### 8b. Drei Muetter — Mutter Zwei (streng, mahnend)
- **Stimm-Typ:** Streng, mahnend, mittlerer Alt.
- **Premade-Match:** "Sarah" — soft but firm.
- **voice_id:** `EXAVITQu4vr4xnSDxMaL`
- **stability:** 0.55 / **similarity_boost:** 0.7 / **style:** 0.4

### 8c. Drei Muetter — Mutter Drei (leise, kichernd)
- **Stimm-Typ:** Sehr leise, kichernd, unheimlich, duenne Stimme.
- **Premade-Match:** "Alice" / "Glinda" — high, expressive (Premade `z9fAnlkpzviPz146aGWa`).
- **voice_id:** `z9fAnlkpzviPz146aGWa`
- **stability:** 0.35 / **similarity_boost:** 0.7 / **style:** 0.7

---

## II. ZUSAETZLICHE LORE-NPCs (Outpost-Roster)

### 9. Schwester-Kommandantin Naveth (Zhar-Eth, Akt 1b)
- Frau, militaerisch hart. "Matilda" / "Charlotte" als Fallback.
- **voice_id:** `XrExE9yKIg1WjnnlVkGX`

### 10. Mond-Priesterin Sheh (Zhar-Eth)
- Frau, sanft, ritualisiert. "Sarah".
- **voice_id:** `EXAVITQu4vr4xnSDxMaL`

### 11. Karawanen-Haendlerin Yul (Zhar-Eth)
- Frau, geschaeftsmaessig. "Rachel" — classic narrative female.
- **voice_id:** `21m00Tcm4TlvDq8ikWAM`

### 12. Senator-Geist Vorul (Echo-Markt, Akt 2)
- Mann, altertuemlich, hallend. "Antoni" — well-rounded male.
- **voice_id:** `ErXwobaYiN019PkySvjV`

### 13. Glasgolden-Schmied Athrek (Echo-Markt)
- Mann, ruhig, handwerklich. "Liam" — articulate young adult.
- **voice_id:** `TX3LPaxmHKxFdv7VOQHJ`

### 14. Otreth-Lehrling Salir (Echo-Markt)
- Junger Mann, ehrfuerchtig. "Josh" — young adult male.
- **voice_id:** `TxGEqnHWrfWFTfGW9XjX`

### 15. Acolyt der Erblinden Kirche (Saeulen-von-Helst, Akt 3)
- Junger Mann, devotional. "Adam" — deep narrative male.
- **voice_id:** `pNInz6obpgDQGcFmaJgB`

### 16. Tribunal-Doppelagent Korren (Saeulen-von-Helst)
- Mann, gedaempft, paranoid. "Brian" — middle-aged narrative.
- **voice_id:** `nPczCjzI2devNBz1zQrb`

### 17. Vehren-Gefangener Selvor (Saeulen-von-Helst, vor Boss-Fight)
- Mann, gebrochen, leise. "Bill" — strong middle-aged.
- **voice_id:** `pqHfZKP75CvOlQylNhV4`

### 18. Asche-Haendler Brulm (Saeulen-von-Helst)
- Mann, alt, raschelnd. "Patrick" — shouty / weathered.
- **voice_id:** `ODq5zmih8GrVes37Dizd`

### 19. Wurzel-Apotheker Bran (Knoten-Markt, Akt 4)
- Mann, leise, schuechtern. "Callum" — hoarse middle-aged.
- **voice_id:** `N2lVS1w4EtoT3dr4eOWO`

### 20. Knochen-Hexe Marvel (Knoten-Markt)
- Frau, mittleren Alters, trocken-zynisch. "Domi" — strong confident female.
- **voice_id:** `AZnzlk1XvdvUeBnXmlld`

### 21. Hohler Sohn (Knoten-Markt) — SPRICHT NICHT
- Keine Voice-Lines. Nur SFX (Atem, Gestik).
- **voice_id:** `__SKIP__`

### 22. Erster Senator Voraius (Spiegelhof, Akt 5)
- Mann, altertuemlich, hochnaesig. "Charlie" — natural casual mid-bass.
- **voice_id:** `IKne3meq5aSn9XLyUdCD`

### 23. Spiegel-Magierin Nheya (Spiegelhof)
- Frau, kristallklar. "Freya" — overhyped expressive young female.
- **voice_id:** `jsCqWAovK2LkecY7zXl4`

### 24. Glasgolden-Haendlerin Sehir (Spiegelhof)
- Frau, kuehl-geschaeftlich. "Grace" — soothing professional.
- **voice_id:** `oWAxZDx7w5VEj9dCyTzz`

### 25. Wunden-Lesende Tehrnal (Drei-Wunden-Lager, Akt 6)
- Genderfluid, ritualisiert. "Fin" — sailor / mystic mid-male.
- **voice_id:** `D38z5RcWu1voky8WS1ja`

### 26. Im-Nesh's Echo-NPC (Hohlwort, Akt 7)
- **Stimm-Typ:** Dieselbe Voice-ID wie Korven ODER Helst (je nach Disguise-Choice), aber Pitch +2 semitones + Reverb.
- **voice_id:** `2EiwWnXFnvU5JabPnv8n`  (= Korven-Default; tausch zu Helst falls Reveal-Wahl anders)
- **post_processing:** `pitch_shift +2st, reverb 30%`

---

## III. SPIELER-KLASSEN (8 Stueck, Voice-Lines aus Pool §SPIELER-KLASSEN)

| Klasse | Gender | Stimm-Beschreibung | Premade | voice_id |
|---|---|---|---|---|
| Warrior | M | Tief, fest, kontrolliert. Eisenwaechter-Disziplin. | Arnold | `VR6AewLTigWG4xSOukaG` |
| Monk | M | Ruhig, atemkontrolliert, Pausen. | Adam | `pNInz6obpgDQGcFmaJgB` |
| Sorceress | F | Hoch, leicht hektisch, manchmal Lachen. | Freya | `jsCqWAovK2LkecY7zXl4` |
| Witch | F | Mittlere Stimme, Trauer-Ton, leise. | Matilda | `XrExE9yKIg1WjnnlVkGX` |
| Ranger | F | Klar, draussen-Stimme, leicht rau. | Charlotte | `XB0fDUnXU5powFXDhCwa` |
| Mercenary | M | Pragmatisch, lakonisch. | Brian | `nPczCjzI2devNBz1zQrb` |
| Huntress | F | Wie Tameris-Typ, fokussiert. | Rachel | `21m00Tcm4TlvDq8ikWAM` |
| Druid | M | Wild, manchmal Tier-Echo. | Daniel | `onwK4e9ZLuTAKqWW03F9` |

---

## IV. END-BOSS — IM-NESH (Akt 7, 3 Phasen)

### Phase 1 — "Der Hoefliche"
- **Stimm-Typ:** Ruhig, freundlich, fast einladend.
- **Premade-Match:** "Antoni" — well-rounded, narrative.
- **voice_id:** `ErXwobaYiN019PkySvjV`
- **stability:** 0.7 / **similarity_boost:** 0.7 / **style:** 0.3

### Phase 2 — "Der Verzweifelte"
- Selbe Voice-ID mit anderen Settings.
- **voice_id:** `ErXwobaYiN019PkySvjV`
- **stability:** 0.4 / **similarity_boost:** 0.6 / **style:** 0.65

### Phase 3 — "Der Hundertzuengige" (Layer 3 Voices in Audacity)
- **voice_id_a:** `VR6AewLTigWG4xSOukaG`  (Arnold, tief, maennlich)
- **voice_id_b:** `XrExE9yKIg1WjnnlVkGX`  (Matilda, mittel, weiblich)
- **voice_id_c:** `z9fAnlkpzviPz146aGWa`  (Glinda, hoch, gender-neutral)
- **post_processing:** Layer alle drei, Pan L/C/R, Reverb 50%, leichte Detune

---

## V. ENDGAME-BOSSE (Aspekt-Echos, Atlas)

| Boss | Stimm-Beschreibung | Premade | voice_id |
|---|---|---|---|
| Aspekt-Echo Kharn | Tiefster Bass, granitig | Arnold | `VR6AewLTigWG4xSOukaG` |
| Aspekt-Echo Nheyra | Frau, doppelte Stimme | Charlotte | `XB0fDUnXU5powFXDhCwa` |
| Aspekt-Echo Ousen | Genderless | Adam | `pNInz6obpgDQGcFmaJgB` |
| Aspekt-Echo Valsa | Frau, brennend-wuetend | Domi | `AZnzlk1XvdvUeBnXmlld` |
| Aspekt-Echo Shulavh | Frau, drei Phasen | Matilda | `XrExE9yKIg1WjnnlVkGX` |
| Aithein-Echo | Stille mit Voice-Layer | George | `JBFqnCBsd6RMkjVDRZzb` |
| Der-Achte (Mythic) | UNDECIDED | tbd | `__UNDECIDED__` |

---

## CHECK-LISTE VOR BATCH-RUN

- [x] Premade-Voice-Defaults eingetragen
- [ ] `ElevenLabs.txt` oder `.elevenlabs_key` im Projekt-Root liegt (✓ checked)
- [x] `.gitignore` enthaelt `ElevenLabs.txt`
- [ ] Casting-Tabelle in Git committen (KEINE voice_ids sind Secrets — koennen committet werden)
- [ ] `python tools/voice_manifest_builder.py` ohne Fehler durchgelaufen
- [ ] `python tools/voice_gen.py --dry-run` zeigt akzeptable Kosten
- [ ] `python tools/voice_list.py --search german` einmal laufen um deutsche Library-Voices zu finden (optional)

---

## PREMADE-VOICE-DISCLAIMER

Die oben eingetragenen IDs sind ElevenLabs-Premades. Sie sprechen primaer
Englisch mit Akzent — `eleven_multilingual_v2` macht sie deutsch-faehig, aber
es klingt nicht nativ. Fuer ein deutsches AAA-Voice-Acting-Gefuehl solltest du:

1. `python tools/voice_list.py --search "german"` laufen lassen.
2. Aus der ElevenLabs Voice Library (https://elevenlabs.io/app/voice-library)
   gezielt deutsche Native-Voices "Add to my Voices" klicken.
3. Voice-IDs hier ersetzen.

Aber: Premade-Defaults reichen voellig fuer einen ersten Test-Pass und einen
funktionierenden Akt-1-Prototypen.

---

## KOSTEN-SCHAETZUNG (Creator-Plan: 100k chars/mo, 22 EUR)

Mit den eingetragenen Defaults und 227 Lines / 11.786 Zeichen:
~2,60 EUR Kosten fuer kompletten Initial-Pass.
Bleibt ~88k Chars Reserve fuer Iteration / Re-Generations / Endgame-Bosse.
