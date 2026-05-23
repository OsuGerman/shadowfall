"""
Shadowfall — Erweitert (modulare Version)

Klassen, Skills, Builds:
- 3 Klassen: Krieger / Magier / Schurke (Titelbild-Auswahl)
- Attribute STR/INT/DEX, 3 Punkte pro Stufe (Vergabe im Inventar)
- Talentbaum mit 6 Knoten (Taste K)
- 16 Runen (4 pro Skill): Skill-Modifikatoren, wählbar nach jedem Boss

Status-Effekte & Element-Combos:
- Brennen, Gift, Frost, Bluten, Schock — stapelbar mit Tick-Schaden
- 6 Element-Combos: Splitter, Toxische Detonation, Plasma, Sturmblitz …

Items, Gems, Crafting (Taste C):
- 4 Seltenheiten × 15 Affixe × 5 Slots, Sockel für Edelsteine
- Aufwerten (+ilvl), Affixe umrollen, Edelsteine sockeln
- 6 Edelstein-Typen, droppen von Gegnern

Welt, Gegner, Bosse:
- 3 Biome (Krypta / Eisfeld / Lavakammer) mit Portal-Auswahl
- Gekachelter Boden + 12 Decor-Typen (Säulen, Fackeln, Sarkophage …)
- 7 Gegnertypen inkl. Ranged (Bogner, Schamane)
- Elite-Affixe (fast/fire/vampiric/explosive)
- 3 Bosse mit eigenen Mechaniken (alle 5 Wellen)
- Mini-Map, Boss-Bar, Y-sortierte Sprites

Grafik:
- Stehende isometrische Sprites mit Klassen-Look (Helm/Hut/Hood, Waffen, Beine)
- Dynamisches Licht-System (Spieler, Fackeln, Projektile, Bosse)
- Blutspritzer-Partikel, Schaden-Bildschirmblitz, Boss-Aura

NEU in dieser Version:
- WETTER pro Biom (Regen/Schnee/Asche/Sand/Sporen/Staub)
- TAG/NACHT-Zyklus in der Stadt (60s = 1 Tag)
- PARALLAX-Hintergrund (Wolken/Nebel-Schichten)
- BLUT-PFÜTZEN am Boden (persistent 25s)
- RARITY-GLOW im Inventar (Rare/Unique pulsiert)
- DETAILLIERTE Item-Sprites (Schwert/Helm/Brustplatte/Ring/Amulett)
- BESSERE SOUNDS (ADSR-Envelopes, FM-Synthese, layered)
- HINTERGRUND-MUSIK 3 Tracks (Town/Dungeon/Boss)
- SCHRITT-SOUNDS pro Biom (Stein/Schnee/Lava/Holz)
- KLASSEN-TOD-Animation (Krieger fällt, Magier zerfällt, Schurke verschwindet)
- IDLE-Atmung (Brust hebt/senkt sich beim Stehen)
- BUFFS/DEBUFFS-HUD-Leiste (zeigt Shield/Combo/Vampir/Regen/etc.)
- COMBO-System (3 Skills in 2s = +30% Schaden)
- BOSS-XP × 3, LEVELUP heilt voll + 5s Invuln
- LOOT-BEAM (Lichtsäule über Rare+ Items) + Auto-Pickup für Rare+
- MULTI-DROP bei Bossen (5-8 Items garantiert)
- BOSS-DEATH-Cinematic (Slow-Mo 1.5s + Flash + Explosion)
- BOSS-SHIELD (muss erst gebrochen werden) + BOSS-HEAL (1x bei <30% HP)
- BOSS-Phase-2-Roar (Bildschirm-Pulse + Sound)
- CHARGED-Attack-Markierung am Boden (1.2s Warnung vor Wucht-Schlag)
- HEAL-FIELD (Zone am Boden, heilt 4s lang über Zeit)
- KLASSEN-Ultimate (Taste X, CD 60s): Wirbel/Meteor/Schatten-Klon
- BOSS-BAR mit Portrait + Phasen-Marker + Shield-Bar
- QUEST-LOG (Taste J): aktive Quest + abgeschlossen + Statistik
- BUYBACK-System beim Händler (letzte 5 verkaufte zurückkaufen)
- VENDOR-FILTER (Alle/Waffen/Rüstung/Schmuck)
- STASH-TABS (Items / Edelsteine)
- WIRT mit Story-Dialog (4 Kapitel je nach Fortschritt)
- SCHMIED-NPC mit Item-VERZAUBERUNG (+ Affix für Gold)
- TELEPORT zum letzten Dungeon (Statue in der Stadt)
- ROAMING-Boss (12% Chance: Bonus-Boss im Dungeon)
- SCHATTEN-INVASION (15% Chance: dunklerer Dungeon + Schatten-Gegner)
- 2 NEUE GEGNER: Hexenmeister (buff-Caster), Berserker (low-HP rampage)
- 2 NEUE BIOME: Wüste + Sumpf, 2 NEUE Dungeons (Wüstentempel, Sumpf-Ruinen)
- SET-ITEMS (Drachen/Frost/Schatten, 2-4 Teile-Boni)
- PROCEDURAL DUNGEONS mit Räumen + Korridoren + Wänden (3/4-View, Schatten)
- Mini-Bosse, Geheime Räume, 4 Trap-Typen (Stachel/Feuer/Pfeil/Druckplatte)
- DORF: 8 Häuser + Marktplatz + Brunnen + 6 NPCs (Händler/Stash/Mystiker/
  Schmied/Quest/Wirt)
- 7 BOSSE (3 alte + 4 neue): Knochenritter, Schneekönigin, Magma-Golem,
  Schattenfürst (Endgame). Boss-Intro-Splash + Phase 2 bei 50% HP
- SCHWIERIGKEITSGRADE pro Dungeon: Normal/Heroisch/Mythisch (T-Taste am Portal)
- 15 ACHIEVEMENTS mit Gold-Belohnungen
- SAVE/LOAD (Autosave bei Town, "Weiter" auf Titel)
- SALVAGE: Items in Werkstatt zu Gold + Chance auf Gem
- PROZEDURALE SOUND-EFFEKTE (Hit/Cast/Pickup/Levelup/Boss/Death)
- UI: Aura-Icon, Hover-Outline auf Gegnern, Toast-Notifications,
  größere Krit-Zahlen, Mini-Boss-Labels
- Welt-Struktur (vorherige Version): Stadt → Wegpunkt → Dungeon → Boss
- 3 Klassen, Klassen-Talentbaum, Skill-Levels, Runen, Auren, Schadensarten
- Vendor + Stash, Quests pro Dungeon, Loot-Filter, Vollbild (F11)
- Item-Vergleich (Shift), Item-Drop (Rechtsklick), Auto-Sort (Z)

Tastatur:
    Linksklick      bewegen / angreifen
    Rechtsklick     Item im Inventar wegwerfen
    Q W E R         Feuerball / Kettenblitz / Heilen / Frostnova
    X               Klassen-Ultimate (CD 60s)
    Y               Zeitstillstand (CD 35s, friert Gegner 4s)
    B               Teleport (CD 8s, Kurz-Blink)
    Leertaste       Ausweichrolle
    I / K / C       Inventar / Talente / Werkstatt
    J               Quest-Log
    L               Loot-Filter wechseln
    Z               Inventar sortieren
    T               (in Stadt am Portal) Schwierigkeit wechseln
    F               Interagieren (NPC, Portal, Dungeon, Heimkehr-Statue)
    Shift           Item-Vergleich beim Hover
    F11             Vollbild
    ESC             Schließen / Beenden

Start:
    python shadowfall2.py
"""
from sf.game import main

if __name__ == '__main__':
    main()
