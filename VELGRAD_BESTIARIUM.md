# VELGRAD — BESTIARIUM (30 Monster)

> Jedes Monster ist nach Akt/Region geordnet, einem **Archetyp** aus `POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md` (Teil F) zugeordnet, und mit Lore-Bezug zur **Velgrad Lore-Bibel** versehen.

**Lese-Konventionen:**
- **Archetyp:** Welche KI/Mechanik-Vorlage. Referenz auf Gameplay-Doc.
- **Tier:** L = Leveling (Akt 1-2), M = Mid (Akt 3-5), E = Endgame (Akt 6-7 + Atlas), X = Mythic
- **Sight:** FOV° / Range in Metern (siehe Gameplay-Doc Teil D.3)
- **Behavior-Tree:** Welche Logik in der KI
- **Drops:** Welcher Loot-Pool

---

## AKT 1 — DIE SALZKÜSTE (5 Monster)

### 1. SALZGEKREUZTER — Hohler Fischer [L]
**Archetyp:** Brute (mit Stalker-Anflug)
**Visuell:** Bleicher Ertrunkener, salzverkrustete Haut, Augenhöhlen voll Kristalle. Trägt zerfetzte Fischerkleidung. Bewegt sich langsam, ruckartig — als würde er sich nicht mehr ganz an Gehen erinnern.
**Sight:** 70° / 12m. Hearing 8m.
**Verhalten:**
- Patrouilliert langsam zwischen Pier-Resten
- Bei Sichtkontakt: dreht sich, *„summt"* (Wind-Up-Audio) für 1.5s, dann **Charge-Strike**
- Wenn HP < 30%: zerfällt zu Salzkristallen, die nach 2s als AoE explodieren
- Pack-Behavior: andere Salzgekreuzte in 6m teleportieren zusammen
**Damage-Profile:** Hoher Phys-Damage, langsam.
**Drops:** Currency, Salz-Kristalle (Crafting), seltener: *Salzfischer-Logbuch* (Quest-Item).
**Lore:** Diese sind die Bewohner von **Marrowport**, einem Dorf, das vor 3 Wochen vom Vergessen erfasst wurde. Sie sind nicht ganz weg — und nicht ganz da. Wer sie tötet, „vollendet" das Vergessen, was sowohl gnädig als auch endgültig ist.

### 2. KRUSTENKRABBE — Aggressives Strand-Wesen [L]
**Archetyp:** Charger
**Visuell:** Hundegroße Krabbe mit Panzer aus geronnenem Salz und Goldschimmer. Augen auf langen Stielen. Schäumt beim Atmen.
**Sight:** 360° (Augenstiele), 8m. Hearing 15m (sie hört Schritte sehr gut).
**Verhalten:**
- Versteckt im Sand (Tunneler-Anteil), springt hervor
- Charge mit Schere, telegraphed durch hochgezogene Pinzette (1s)
- Death-Pop: zerplatzt zu Salzwasser-Pfütze (Slow-Field, kein Damage)
**Damage-Profile:** Mittlerer Phys, sehr schnell.
**Drops:** Currency, Salz, *Krabbenpanzer* (Armour-Crafting).
**Lore:** Normale Krabben in der Salzwunden-Region wachsen aus dem Maß. Eine alte Geschichte sagt, sie tragen kleine Stücke Glasgoldener Wracks in ihren Panzern.

### 3. ERTRUNKENES ECHO — Geist eines Seemanns [L]
**Archetyp:** Caster (Ranged)
**Visuell:** Halbtransparente Gestalt in alter Seemanns-Uniform. Lautlos. Mund offen, aber kein Geräusch. Wasser tropft, das nicht da ist.
**Sight:** 180° / 20m (kann durch Wände sehen — Geist).
**Verhalten:**
- Bleibt auf Distanz
- Casted **Wasser-Speer** (langsam, hohe Cold-Damage), telegraphed 1.2s
- Bei Nahkampf: Phase-Out (kurz unsichtbar), Repositioning
- Death: schreit endlich (Audio-Event, sehr unangenehm), zerfällt
**Damage-Profile:** Cold-Damage, Freeze-Buildup.
**Drops:** Currency, Geist-Splitter (Crafting), seltene Drops: *Salz-Spell-Stones*.
**Lore:** Die Salzwunde lockt Ertrunkene aus 800 Jahren Seehandel zurück. Manche sterben endlich, wenn ihre alten Verträge erfüllt werden. Andere — nicht.

### 4. MÖWEN-SCHWARM — Aggressive Vogel-Plage [L]
**Archetyp:** Skirmisher (Flyer-Pack)
**Visuell:** 8-12 große, blutverkrustete Möwen. Augen sind alle weiß. Schreien wie Kinder.
**Sight:** 120° / 15m (aerial).
**Verhalten:**
- Kreisen erst über dem Spieler
- Stürzen einzeln im Wechsel ab (jeweils 0.5s Telegraph mit Schatten am Boden)
- Wenn ein Vogel stirbt, der Rest wird aggressiver (+10% Speed)
- Kann nur mit Ranged oder Tier-Skills effektiv getroffen werden
**Damage-Profile:** Niedrig Phys, hoher Bleed-Buildup.
**Drops:** Federn, Knochen-Splitter.
**Lore:** Sie folgten ein Fischerboot in den Hafen, das nie ankam. Jetzt warten sie. Die Augen sind weiß, weil sie zu lange gewartet haben.

### 5. SALZHÜTER-BRUT — Mini-Boss [L+]
**Archetyp:** Elite Brute / Pack-Leader
**Visuell:** Übergroße korrupterte Statue eines Aspekts (vermutlich Nheyra), mit Salz überzogen. Bewegt sich steinern langsam. Augen sind zwei rote Kristalle.
**Sight:** 360° / 25m.
**Verhalten:**
- Drei-Phasen-Encounter
- Phase 1 (100%-66%): Slam-Attacks mit AoE-Telegraph, ruft Salzgekreuzte als Adds
- Phase 2 (66%-33%): Wirft Salz-Speere (3-Salve), erzeugt Salz-Pfützen
- Phase 3 (33%-0%): Zerfällt teilweise — wird **schneller**, ruft alle vergangenen Adds nochmal
**Damage-Profile:** Hoher Phys + Cold.
**Drops:** Garantiert eines: *Salz-Kristall-Ring*, *Mahnmal-Marke VII* (Crossbow), oder *Salzhüter-Splitter* (Crafting-Mat).
**Lore:** War einst Wache an Velharns Hafentor. Wurde im Götterkrieg überrannt, und niemand kam, um sie abzulösen. Sie wartet immer noch auf Ablösung. Niemand kommt mehr.

---

## AKT 2 — DIE GLASGOLDENEN RUINEN (5 Monster)

### 6. ECHO-SENATOR — Politischer Geist [L+]
**Archetyp:** Caster + Support
**Visuell:** Toga-bekleidete halbtransparente Gestalt mit Goldstaub-Aura. Hält ständig eine Rede an niemanden.
**Sight:** 180° / 18m.
**Verhalten:**
- Casted **Goldstaub-Cloud** (Slow-AoE)
- Buffed andere Echos in 10m (+30% Damage)
- Kann **Quote** zitieren (1.5s-Cast): ein lang verstorbener Spruch erscheint als Text-Damage-Number über Feinden
- Resistent gegen Phys; verwundbar gegen Chaos
**Damage-Profile:** Niedrig direkt, hoch durch Buffs.
**Drops:** Goldstaub-Mat, *Senator-Toga* (Body-Armour), seltener: *Senatorin-Stahl* (Sword).
**Lore:** Einer der 412 Senatoren der Glasgoldenen Liga. Spricht jeden Tag dieselben 3 Reden, in derselben Reihenfolge, seit 800 Jahren. Tötet man ihn, vergisst die Welt, was er sagte. Manche Historiker zahlen viel für solche Tötungen.

### 7. GLASGOLDEN-WÄCHTER — Construct [M]
**Archetyp:** Tank / Brute / Guardian
**Visuell:** Statue aus Glas und Gold, fast 4m hoch. Innen zirkulieren leuchtende Glyphen. Trägt ein riesiges Schild.
**Sight:** 100° / 20m.
**Verhalten:**
- Blockt Damage von vorne mit Schild (front-blocking-mechanic)
- Schild zerstörbar (5000 HP separat)
- Nach Schild-Bruch: enraged (+50% Speed), keine Defensive mehr
- Slam-Attack mit großem AoE-Telegraph (2s Wind-Up, rote Linie zeigt Reichweite)
**Damage-Profile:** Sehr hoher Phys, langsam.
**Drops:** Glasgolden-Splitter (sehr wertvoll), *Wächter-Schild* (Shield), seltener: *Glasgoldener Zepter-Stab*.
**Lore:** Gebaut von der Liga, um den Hafen zu bewachen. Wurde nie offiziell deaktiviert. Steht immer noch da. Tut immer noch seinen Job. Auch wenn der Hafen nicht mehr existiert.

### 8. GOLDSTAUB-DIENER — Glasgoldenes Bedienstetes-Echo [L+]
**Archetyp:** Skirmisher
**Visuell:** Hagere humanoide Gestalt aus Goldstaub und Glassplittern. Trägt eine Servierschüssel.
**Sight:** 90° / 12m.
**Verhalten:**
- Bewegt sich schnell, in 8-12er Packs
- Bietet zuerst „Tee" an (Audio-Cue) — wenn Spieler in 3m, AoE-Explosion (kochender Goldstaub)
- Wenn nicht in 3m: wirft Schale (Projektil)
**Damage-Profile:** Mittel Phys + Fire (Burns).
**Drops:** Goldstaub, *Servier-Set* (eccentric Item für RP-Builds).
**Lore:** Die Bediensteten der Senatoren-Häuser. Sie servieren immer noch Tee an Tische, die nicht mehr da sind. Der Tee ist heiß. Der Goldstaub ebenso.

### 9. SPIEGEL-STALKER — Glas-Anomalie [M]
**Archetyp:** Stalker
**Visuell:** Spinnenartiges Wesen aus Glas-Scherben, fast unsichtbar wenn es still steht. Reflektiert die Umgebung.
**Sight:** 360° / 25m (Spiegelsicht aus allen Glas-Oberflächen).
**Verhalten:**
- Bleibt unsichtbar, bis Spieler nahe ist
- Pop-Up-Attack aus dem Boden / der Wand (Stealth-Strike, Crit)
- Nach Strike: rennt 5m weg, wird wieder unsichtbar
- Audio: hörbares Glas-Tinkle 0.5s vor Strike (Skill-Check für Spieler)
**Damage-Profile:** Hohe Phys + Crit (Stealth-Damage).
**Drops:** Spiegel-Scherben, seltener: *Echo-Klinge*.
**Lore:** Niemand weiß, wo sie hergekommen sind. Manche glauben, sie sind die Reflexionen der Senatoren, die in den Spiegeln vergessen wurden.

### 10. VERFALLENER MAGISTER — Magier-Geist [M]
**Archetyp:** Support / Healer + Caster
**Visuell:** Alter Gelehrter in zerfallener Robe. Bücher schweben um ihn, deren Seiten leer geworden sind. Augen sind aus Tinte.
**Sight:** 360° / 25m.
**Verhalten:**
- Heilt andere Echos in 15m (Heal-Beam mit Channeling 2s — unterbrechbar)
- Casted **Vergessens-Strahl**: bei Treffer verlierst du temporär 1 Skill-Slot (3s, kein Cast möglich) — extremes Mechaniks-Beispiel
- Repositioniert ständig
- Priority-Kill: tötet ihn, oder die anderen Echos sind unsterblich
**Damage-Profile:** Niedrig direkt, devastatorischer Support.
**Drops:** Tinten-Bücher (Crafting), *Vergessens-Notizen* (Spell-Stone-Mat).
**Lore:** Diese Gelehrten studierten Im-Neshs Pakt. Sie haben zuviel gesehen. Die Welt hat sie als Strafe halb-vergessen.

---

## AKT 3 — DIE ASCHENFELDER (5 Monster)

### 11. ASCH-SOLDAT — Skelett aus der Letzten Legion [M]
**Archetyp:** Skirmisher (Pack)
**Visuell:** Halb-verbrannter Skelett-Krieger mit Bronze-Rüstung. Knochen sind weiß-glühend. Trägt zerbrochenes Schwert oder Schild.
**Sight:** 90° / 15m.
**Verhalten:**
- Pack-Behavior: gehen in Formation (4-6 Mob-Squad)
- Wenn ein Soldat „Vorrücken!" ruft (Audio-Cue), greifen alle in 8m simultan an
- Wenn Anführer (Sergeant) im Pack stirbt, andere werden 2s frozen
**Damage-Profile:** Mittel Phys + Fire-Burn (von der Asche).
**Drops:** Bronze-Splitter, *Asch-Soldaten-Marken* (Crafting), seltener: *Aschen-Ankunft* (Mace).
**Lore:** Sie marschierten mit Valsa. Sie fielen mit ihr. Sie marschieren immer noch — weil niemand den Befehl zur Auflösung gab.

### 12. BRENNENDER PREDIGT-SPRECHER — Tribunal-Caster [M]
**Archetyp:** Caster (Ranged + Buff)
**Visuell:** Robe-tragender Inquisitor, sein eigener Körper brennt — aber er bemerkt es nicht. Hält ein brennendes Buch.
**Sight:** 180° / 22m.
**Verhalten:**
- Casted **Tribunal-Urteil** (3s Telegraph): markiert Spieler, nach Telegraph schlägt Feuer vom Himmel
- Buffed andere Tribunal-Mobs in 12m (+Damage, +Fire-Damage)
- Reagiert auf Heilung: wenn Spieler heilt, +Speed-Buff für 2s
**Damage-Profile:** Hoher Fire.
**Drops:** Tribunal-Marken, *Brennendes Buch* (Spell-Item), seltener: *Funken-Fluch* (Wand).
**Lore:** Inquisitoren des Tribunals der Asche, die zu lange in den Aschenfeldern blieben. Ihre Predigt ist nicht mehr für Sterbliche — sie ist für Valsa selbst.

### 13. INQUISITIONS-KLINGENMESSER — Tribunal-Stalker [M]
**Archetyp:** Stalker / Assassin
**Visuell:** Schmaler Inquisitor in dunkler Robe, Gesicht mit Maske bedeckt. Drei Dolche an Gürtel.
**Sight:** 60° / 15m, aber hört sehr gut (Hearing 18m).
**Verhalten:**
- Versteckt sich hinter Steinen / in Schatten
- Sprintet auf den Spieler zu, Backstab-Combo (3 schnelle Stiche)
- Nach Combo: dodged rückwärts, wartet, repeats
- Bei niedrigem HP: wirft Rauchbombe (Stealth-Reset)
**Damage-Profile:** Sehr hoher Phys + Bleed.
**Drops:** Tribunal-Dolche (Dagger-Crafting), *Inquisitions-Maske* (Helm).
**Lore:** Die unauffällige Hand des Tribunals. Sie jagen die, die das Tribunal selbst nicht öffentlich verurteilen kann. Sie hinterlassen keine Spuren — meistens.

### 14. ASCH-WOLF — Korrumpierte Bestie [M]
**Archetyp:** Charger (Tier-Variation)
**Visuell:** Schwarzer Wolf, in dem Asche statt Fell wächst. Augen sind kleine Flammen. Hinterlässt Brandspuren beim Laufen.
**Sight:** 140° / 14m. Smell-Range: 20m (ignoriert LOS).
**Verhalten:**
- Pack-Behavior (3-5 Wölfe)
- Umkreisen den Spieler, einer attackiert von hinten während andere ablenken
- Charge mit Bite-and-Drag (zieht Spieler 3m)
- Brandige Death-Explosion (kleine AoE)
**Damage-Profile:** Mittel Phys + Fire-DoT.
**Drops:** Asch-Pelz, *Wolfsmond-Amulett* selten.
**Lore:** Normale Wölfe der Region, die zu nah an Valsas Asche kamen. Eine Saatträger-Theorie: ihre Seelen sind noch dieselben. Tötet man sie, befreit man sie.

### 15. TRIBUNAL-KONSTRUKT — Guardian [M+]
**Archetyp:** Guardian / Tank
**Visuell:** Bronzene Statue mit Inquisitor-Maske, 3m hoch. Trägt schweren Hammer. Lava-glühende Innereien.
**Sight:** 100° / 20m.
**Verhalten:**
- Stationärer Wächter — patrouilliert nur kurzen Bereich
- Smash-Attack (3s Telegraph, riesige AoE)
- Bei 50% HP: Maske fällt — darunter ist nichts (Tribunal-Lore: leer)
- Nach Maske-Fall: schneller, aber blind (kann nur in Sicht-Linie folgen)
**Damage-Profile:** Massiv Phys, sehr langsam.
**Drops:** Bronze-Komponenten, *Tribunal-Maske* (Helm), garantierter Drop bei erstem Kill: *Asche-Aspekt* (Wand).
**Lore:** Vom Tribunal gebaut aus den Helmen gefallener Glasgoldener Wächter. Eine Mischung, die nicht hätte funktionieren dürfen. Tut es auch nicht — die Konstrukte werden immer wahnsinniger.

---

## AKT 4 — DAS WURZELGRAB (5 Monster)

### 16. KNOCHENWITWEN-SCHWESTER — Niederer Hexe [M]
**Archetyp:** Caster + Summoner
**Visuell:** Hagere Frau in zerfetzter dunkler Robe. Knochen sind eingewebt im Stoff. Hält einen Knochen-Stab.
**Sight:** 180° / 18m.
**Verhalten:**
- Beschwört kleine Skelett-Diener (2 pro Cast, Cooldown 8s)
- Casted **Knochen-Speer** (Ranged, mittel Damage)
- Bei niedrigem HP: opfert eigene Knochen für Heal (visuelles Schmerz-Event)
**Damage-Profile:** Mittel Phys + Chaos.
**Drops:** Knochen-Splitter, Knochen-Stab (Wand-Crafting), seltener: *Vossharils Bruder* (Dagger).
**Lore:** Schwestern von Vossharil, die ihren Pakt mit den Toten zu weit getrieben haben. Vossharil selbst lehnt sie ab — sie sind „verdorben durch Nachgiebigkeit".

### 17. WURZEL-SPINNE — Untergrund-Predator [M]
**Archetyp:** Tunneler / Stalker
**Visuell:** Pferdegroße Spinne mit Wurzel-Beinen statt normalen. Hinterleib pulsiert organisch.
**Sight:** 360° / 18m (Vibrations-Sinn ignoriert LOS).
**Verhalten:**
- Vergraben in Wurzeln, springt hervor (Pop-Up-Attack)
- Webt Schleim-Netze am Boden (Slow-Field)
- Lockt Spieler in Falle: Spinnt Web-Cocoon-Schau (Quest-NPC oder Item) als Lockmittel
- Death: legt 3-5 Eier, die nach 5s schlüpfen (kleine Spider-Adds)
**Damage-Profile:** Phys + Poison.
**Drops:** Wurzel-Seide (Crafting), *Wurzelschlitzer* selten.
**Lore:** Sie kamen mit Shulavh — sind ihre Boten. Shulavh schickt sie aus, um Sterbliche zu testen.

### 18. FADEN-GEBUNDENER — Untoter Marionetten-Mensch [M]
**Archetyp:** Support (passiv-aggressiv)
**Visuell:** Humanoid, an roten Fäden hängend, die ins Dunkel verschwinden. Bewegt sich nur, wenn die Fäden zucken. Augen sind aus Knöpfen.
**Sight:** 0° (blind), nur durch Faden-Vibration.
**Verhalten:**
- Greift erst an, wenn ein anderes Monster im Pack stirbt
- Beim Angreifen: alle Bewegungen sind ruckartig (lore: jemand zieht die Fäden)
- Wenn man die Fäden trifft (über ihm): er fällt zusammen (Insta-Kill, easy)
- Drops manchmal Faden-Echo (kann Mara Quest-Item sein)
**Damage-Profile:** Phys, aber inkonsistent.
**Drops:** Marionetten-Fäden, *Faden-Spitze* selten.
**Lore:** Sterbliche, deren Bindung an die Welt fast aufgelöst war. Shulavh hat sie als Mitleid an Fäden geknüpft, damit sie nicht vergessen werden. Aber sie sind nicht mehr ganz Mensch.

### 19. HOHLER SOHN — Shulavhs Adoptierter [E]
**Archetyp:** Stalker (Mini-Boss-Tier)
**Visuell:** Junge Gestalt in zerlumpter Kleidung, Gesicht ist eine glatte Oberfläche ohne Züge. Spricht mit Shulavhs Stimme.
**Sight:** 180° / 25m.
**Verhalten:**
- Phasing-Stealth: verschwindet jede 6s für 1s
- Während Phasing: reappears hinter Spieler
- Schreit *„Mutter!"* vor jedem Strike (verstörendes Audio-Telegraph)
- HP-niedrig: bittet um Gnade in Vossharils Stimme (verstörendes Mind-Game)
**Damage-Profile:** Hoher Phys + Chaos.
**Drops:** *Hohle Maske* (Helm), garantiert: *Faden-Splitter* (Crafting).
**Lore:** Shulavh sammelt Kinder, die das Vergessen erfasst hat. Sie macht sie zu ihren „Söhnen". Sie liebt sie ehrlich. Sie schickt sie trotzdem in den Tod.

### 20. MARK-KRIEGER — Wurzel-Wächter [M]
**Archetyp:** Brute
**Visuell:** Massiver humanoid aus verwachsenem Wurzelholz. Wo Augen sein sollten, leuchtet grüner Saft.
**Sight:** 100° / 18m.
**Verhalten:**
- Sehr langsam, aber massiv hoch HP
- Slam-Attacks aus Wurzeln (AoE-Telegraph)
- Bei niedrigem HP: pflanzt sich in den Boden (verwurzelt = Heal-Phase 5s, kann unterbrochen werden)
**Damage-Profile:** Sehr hoch Phys, langsam.
**Drops:** Wurzel-Mark (Crafting), seltener: *Wurzelmark-Stütze* (Staff).
**Lore:** Aus den Wurzeln des toten Weltenbaums geformt. Sie sind die letzte Verteidigung Shulavhs. Wer sie tötet, schwächt das Wurzelgrab selbst.

---

## AKT 5 — DIE SPIEGELSTADT VELHARN (5 Monster)

### 21. STUNDEN-WANDLER — Zeit-Anomalie [E]
**Archetyp:** Phasing-Stalker
**Visuell:** Sterbliche Gestalt in glasgoldener Kleidung, aber mit acht Versionen ihrer selbst, alle leicht versetzt — wie Multi-Exposure.
**Sight:** 360° / 30m (sieht in mehreren Zeit-Schichten).
**Verhalten:**
- Existiert in 3 Zeit-Schichten gleichzeitig — Spieler trifft alle 3, eine nach der anderen
- Wenn man eine „Version" tötet, die anderen werden enraged
- Casted **Zeit-Verzerrung**: 2s lang läuft der Spieler langsamer
**Damage-Profile:** Mittel Phys, aber Cooldown-Verzerrung (eigene Cooldowns dauern länger).
**Drops:** Zeit-Echo (Crafting), seltener: *Echo-Klinge*.
**Lore:** Bürger Velharns, die in Nheyras Stunden-Spiegel zu lange gelebt haben. Sie sind nicht mehr in einer Zeit zuhause.

### 22. SENATOR-PHANTOM — Akt-5-Boss-Variante [E]
**Archetyp:** Caster Mini-Boss
**Visuell:** Wie Echo-Senator, aber 4m groß, mit drei Köpfen (jeder spricht aus einer anderen Zeit).
**Sight:** 360° / 30m.
**Verhalten:**
- Drei-Köpfe-Phasen-Mechanik: jeder Kopf castet einen anderen Spell
- Kopf 1 (Glasgoldener): goldener Pfeil-Salve
- Kopf 2 (Götterkrieg): Brennende Schwert-Beschwörung
- Kopf 3 (Gegenwart): Vergessens-Strahl (siehe Magister)
- Wenn 1 Kopf abgetrennt: Spieler ist gegen den Spell immun, andere Köpfe werden enraged
**Damage-Profile:** Verschieden, schwierig.
**Drops:** Garantiert: *Senatorin-Stahl*. Selten: *Sieben-Atem-Stab* (Mythic).
**Lore:** Drei Senatoren in einem Körper — vereint, weil sie alle in derselben Sekunde starben, in drei verschiedenen Zeitlinien.

### 23. GLASSCHERBEN-TÄNZERIN — Ballet-Anomalie [E]
**Archetyp:** Skirmisher
**Visuell:** Filigrane weibliche Gestalt aus geschliffenem Glas, in einer ewigen Tanzpose. Bewegt sich graziös aber schnell.
**Sight:** 90° / 18m (sieht nur in Tanz-Posen).
**Verhalten:**
- Pirouetten-Charge (Spinner-Attack, multi-hit)
- Springt anmutig (Telegraphed 0.8s)
- Bei jedem Treffer auf sie: Splitter fliegen weg (kleiner AoE-Damage als Reflektion)
**Damage-Profile:** Mittel Phys + Bleed.
**Drops:** Glas-Splitter, seltener: *Tänzerin-Gürtel* (Speed-Belt).
**Lore:** Eine der Tänzerinnen des Spiegelhofs. Sie tanzte 800 Jahre lang, weil niemand die Musik abstellte. Jetzt ist sie der Tanz.

### 24. DER SICH-SELBST-SPIELENDE-SPIELER — Echo-Zwilling [E+]
**Archetyp:** Mini-Boss / Anomaly
**Visuell:** Ein perfekter Spiegel des Spielers, mit allen seinen aktuellen Skills und Items.
**Sight:** 360° / 30m (kennt Spieler-Position perfekt).
**Verhalten:**
- Spielt exakt den Build des Spielers
- Reagiert auf Spieler-Skills mit Counter-Skills aus derselben Pool
- Ändert Skill-Setup, wenn der Spieler seines ändert (live-Adaption!)
- Wirft eine **Linie aus Tinte** auf den Boden — wenn beide auf derselben Seite stehen, kein Effekt; wenn entgegengesetzt, Damage
**Damage-Profile:** Spiegelt den Spieler-Output.
**Drops:** *Doppelgänger-Marke* (lore-relevant), *Spiegel-Splitter* (Crafting).
**Lore:** Eine Echo-Anomalie aus einer welkenden Welt, in der der Spieler **Im-Neshs Seite** gewählt hat. Dieser Spiegel-Spieler hat die Welt umgeschrieben. Er kämpft gegen den Spieler, weil er glaubt, der „echte" Spieler stört seine Realität.

### 25. SPIEGEL-HÜTER — Guardian der Stunden-Spiegel [E]
**Archetyp:** Guardian
**Visuell:** Riesige humanoide Gestalt, ein Spiegel statt Gesicht. Trägt einen Spiegel-Schild und Spiegel-Schwert.
**Sight:** 100° / 25m.
**Verhalten:**
- Spiegelt 50% des erlittenen Damages zurück zum Spieler
- Bei Phys-Damage: hoher Reflect
- Bei Element-Damage: Reflect schwächer
- Wenn man den Schild-Spiegel zerbricht: Reflect deaktiviert, aber Boss schneller
**Damage-Profile:** Hoch Phys + Reflect-Mechanik.
**Drops:** Spiegel-Glas (Crafting), garantiert: *Spiegel-Splitter-Ring*.
**Lore:** Wächter zwischen den Zeit-Schichten. Sie spiegeln, weil sie keine eigene Identität mehr haben.

---

## AKT 6 — DIE DREI WUNDEN (3 Mini-Bosse + 1 Anomaly) + AKT 7 + ENDGAME (1)

### 26. DIE ERTRUNKENE KÖNIGIN — Salzwunden-Boss [E]
**Archetyp:** Boss (RISE_FROM_GRAVE / EMERGE_FROM_LIQUID-Spawn)
**Visuell:** Königin in zerlumpter Robe mit Salzkristallen statt Haar. Krone aus Korallen. Wandelt halbschwimmend.
**Sight:** 360° / 35m.
**Verhalten / Attack-Pool:**
- A1: Korallen-Schnitt (Melee, Crit)
- A2: Wasser-Tornado (AoE, telegraphed)
- A3: „Ertränken" — kanalisiert Wasser-Cocoon um Spieler (3s Telegraph, ausweichbar mit Dodge)
- A4: Beschwört 3 Ertrunkenes Echo Adds
- U1 (Phase 3): „Tiefes Vergessen" — der ganze Raum füllt sich mit Wasser für 10s, Spieler erstickt langsam, muss auf höhere Plattformen kommen
**Drops:** Garantiert: *Saphir der Salzwunde* (Endgame-Amulet), Chance auf *Sturmspeer von Veh*.
**Lore:** Sie war die Letzte Königin Velharns, ertränkt im Krieg. Sie wachte am Boden der Salzwunde wieder auf.

### 27. DER ECHO-DRACHE — Aschwunden-Boss [E]
**Archetyp:** Boss (AWAKEN-Spawn — war versteinert)
**Visuell:** Drache, einst lebend, jetzt halb-Asche. Augen sind die einzige Stelle, die noch wirklich brennt. Flügel sind durchlöchert wie aus Papier.
**Sight:** 360° / 40m.
**Verhalten / Attack-Pool:**
- A1: Klauen-Sweep (Melee, Bleed)
- A2: Asche-Atem (Cone, Fire-DoT 5s)
- A3: Flügelschlag (AoE-Wind, Knockback)
- A4: Schwanz-Sweep (180° Telegraph)
- U1 (Phase 3): „Letzter Atem Valsas" — fliegt hoch, schickt Meteoren-Schauer (10 Meteoren, jeder 2s Telegraph mit Schatten)
**Drops:** Garantiert: *Drachen-Schädel-Trophäe* (Belt), Chance auf *Verbrannte Treue* (Sword).
**Lore:** Einer der drei letzten Drachen Velgrads. Er sah Valsa fallen und versteinerte vor Trauer. Jetzt ist er erwacht — vielleicht, weil das Vergessen ihn rufen kommt.

### 28. DER NICHT-GOTT — Hohlwunden-Boss / Anomalie [E+]
**Archetyp:** Boss (REVEAL-Spawn — war die ganze Zeit „Nichts" im Raum)
**Visuell:** Eine humanoide Silhouette, die nur aus *negativem Raum* besteht. Die Welt um ihn herum ist da; er ist nicht.
**Sight:** 360° / 50m (er weiß alles in der Karte, da er „nicht da" ist).
**Verhalten / Attack-Pool:**
- A1: „Nicht-Schlag" — schlägt, aber du kannst ihn nicht sehen kommen (Audio-Cue Pflicht!)
- A2: „Vergessens-Welle" — Spieler verliert 2s lang einen zufälligen Skill (Mechanik)
- A3: „Auslöschen" — markiert einen Bereich, wenn Spieler nach 3s noch drin → 90% Max-HP-Damage
- A4: Beschwört 3 *Nicht-Männer* (siehe #29)
- U1 (Phase 3): „Stille Sekunde" — alles ist 2s lang vollständig still (Audio aus, Animationen frozen), dann massiver Damage-Burst auf alle Spieler im Sichtfeld
**Drops:** Garantiert: *Splitter des Nicht-Seins* (Mythic-Crafting). Chance auf *Der Achte* (Mystery-Weapon).
**Lore:** Manche Theologen flüstern: Das ist der Siebte Aspekt höchstpersönlich, in physischer Form. Andere: Es ist nur ein Echo. Niemand weiß. Niemand fragt.

### 29. NICHT-MANN — Anomaly-Add [E]
**Archetyp:** Stalker (Anomaly-Variation)
**Visuell:** Humanoid-Form aus Leere. Hat einen „Schatten", aber kein Wesen.
**Sight:** 360° (er ist überall und nirgends).
**Verhalten:**
- Phasing alle 4s
- Während Phasing: zieht Spielers Position auf
- Bei Reappear: schlägt sofort zu
- Death: zerfällt zu kurzem Lacher-Audio, dann Stille
**Damage-Profile:** Untyped Damage (ignoriert Resistances), niedrig aber konsistent.
**Drops:** Selten: *Splitter des Nicht-Seins*.
**Lore:** Wesen, die nie hätten existieren sollen. Sie sind die Lücken, die zurückbleiben, wenn die Welt etwas vergisst.

### 30. ASPEKT-ECHO (GENERIC ENDGAME-BOSS) — Verzerrtes Götter-Echo [X — Mythic]
**Archetyp:** Atlas-Boss (Pool — randomisiert welche Aspektin/welcher Aspekt erscheint)
**Visuell:** Eine zerbrochene Manifestation eines der Sieben. Variations:
- **Kharn-Echo:** Steinerne Gigant-Figur, Brust offen, Inneres Lava
- **Nheyra-Echo:** Frau mit Uhr-Gesicht, dreht sich rückwärts
- **Ousen-Echo:** Schwebende Augen-Wolke, alle Augen rotieren
- **Valsa-Echo:** Brennende Kriegerin, verkohlt aber noch in voller Rüstung
- **Im-Nesh-Echo:** Mehrarmige Gestalt mit hundert Mündern, alle reden gleichzeitig
- **Shulavh-Echo:** Frau in Spinnen-Pose, Hände aus roten Fäden
- **Siebter-Echo:** Leere Stelle (ähnlich Nicht-Gott, aber langsamer + größer)
**Sight:** Voll.
**Verhalten:** Jedes Echo hat eigenes Moveset, basierend auf seinem Aspekt-Element. Werden zufällig in Atlas-Maps generiert.
**Damage-Profile:** Hoch, variantenreich.
**Drops:** Aspekt-Echo-Fragmente (Crafting), Chance auf entsprechendes Aspekt-Unique (z.B. Kharn-Echo dropt *Kharns Geduld*).
**Lore:** Echos der Sieben aus den welkenden Welten. Sie sind nicht die echten Aspekte — sie sind, was die Aspekte in toten Welten gewesen wären. Im Endgame der zentrale Boss-Pool.

---

## ANHANG — KI-DESIGN-PRINZIPIEN AUS DIESEM BESTIARIUM

1. **Jedes Monster braucht 1 Telegraph-Mechanik**, die Spielern beibringt, **wann zu dodgen**. Salzhüter mit AoE-Slam-Telegraph, Tribunal-Predigt mit 3s-Sky-Strike-Telegraph, etc.
2. **Pack-Behavior** (Salzgekreuzte, Wölfe, Asch-Soldaten) testet Spieler-Positioning. Solo-Mobs (Stalker, Bosse) testen Spieler-Skill-Timing.
3. **Mechanik-Tests:** Verfallener Magister testet Priority-Targeting. Glasgolden-Wächter testet Schild-Brechen. Spiegel-Hüter testet Element-Switch.
4. **Lore aus Mechanik:** Wenn ein Monster „Stunden-Wandler" heißt, muss seine Mechanik mit Zeit zu tun haben. Nicht-Mann muss „Nicht-da-Sein" mechanisch demonstrieren.
5. **Audio-Pflicht:** Jedes Monster braucht eine einzigartige Sound-Signatur (siehe Skill-Briefing Teil 5.2). Salzgekreuzter summt, Asch-Wolf knurrt mit Knistern, Stunden-Wandler tickt wie eine Uhr.
6. **Affixe (siehe Gameplay-Doc):** Jedes Monster kann mit Affixen als Rare/Magic spawnen. Ein Asch-Wolf mit Affix „Stormcaller" wird zu einem Mini-Boss.
7. **Drops müssen sinnvoll sein.** Salzhüter-Brut dropt Salzkristalle UND eine Mahnmal-Gilde-Crossbow (Mahnmal handelt mit Bergungsgut aus solchen Ruinen — lore-konsistent).

---

*„Jedes Wesen in Velgrad erinnert sich an etwas. Wenn du es triffst, vergisst du, was es war. Wenn du es überlebst, lernst du, dass das ein gnädiger Handel war."*
— Vossharil die Dreimalige
