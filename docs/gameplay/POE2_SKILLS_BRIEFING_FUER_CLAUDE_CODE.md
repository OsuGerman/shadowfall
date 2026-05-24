# PATH OF EXILE 2 — SKILL BIBLE & PRODUCTION BRIEFING FÜR CLAUDE CODE

> **Zweck dieses Dokuments:** Vollständiges Referenzdokument für die Implementierung eines POE2-inspirierten Action-RPGs. Enthält alle Skill-Systeme, Klassen-Skills, Skill-Mechaniken sowie verbindliche Vorgaben zu Grafik, Sound und Animation. Stand: Patch-Cycle 0.4.x „The Last of the Druids" / 0.5.0 „Fate of the Vaal" (Mai 2026). Aktuell existieren ca. **222 Skill Gems, 16 Meta Gems und 505 Support Gems** im Spiel — insgesamt 743 Gems.

---

## TEIL 1 — DAS GEM-SYSTEM (Architektonisches Grundgerüst)

POE2 unterscheidet sich von klassischen ARPGs dadurch, dass Skills nicht mehr an Ausrüstung gebunden sind, sondern in einem dedizierten **Skill Panel** verwaltet werden. Jeder Charakter hat 9 Skill-Slots. Es gibt vier (mit Lineage fünf) Gem-Kategorien:

### 1.1 Skill Gems (Aktive Fähigkeiten)
- Verleihen aktive Kampf-Fähigkeiten (Angriffe, Sprüche, Beschwörungen, Buffs).
- Werden aus **Uncut Skill Gems** im Gemcutting-Menü graviert.
- Können bis zu 5 Support-Gems aufnehmen (Start mit 2-3, Erweiterung via Jeweller's Orbs).
- Leveln bis Level 20 (21 mit Corruption) via höherwertige Uncut Gems.
- Attributsanforderungen (STR/DEX/INT) steigen mit Level.

### 1.2 Support Gems (Modifier)
- Werden in Skill-Gem-Sockel eingesetzt, modifizieren nur diesen einen Skill.
- Seit Patch 0.3.0 „The Third Edict": Multiple Kopien erlaubt, Kategorie-Restriktionen ersetzen den alten „1 pro Skill"-Block.
- Beispiele: Multiple Projectiles, Added Fire Damage, Magnified Effect, Brutality, Concentrated Effect.
- Cost Multiplier erhöht Mana-Kosten, NICHT Spirit-Reservation.

### 1.3 Spirit Gems (Persistent Buffs / Auras)
- Reservieren dauerhaft **Spirit** (Ressource, Basis 100, skalierbar via Tree, Sceptres, Amulets).
- Wirken wie Auras/Heralds aus POE1.
- Beispiele: Herald of Ash, Herald of Ice, Herald of Thunder, Grim Feast, Hatred, Wrath, Skeletal Warrior, Iron Ward.

### 1.4 Meta Gems (Trigger-Gems)
- Reservieren Spirit + besitzen eigene Sockel für Skill Gems.
- Akkumulieren **Energy** durch Bedingungs-Trigger und feuern dann automatisch.
- Schlüssel-Beispiele: Cast on Shock, Cast on Freeze, Cast on Ignite, Cast on Elemental Ailment, Cast on Crit, Cast on Minion Death, Cast on Block.

### 1.5 Lineage Gems (Endgame, seit 0.3.0)
- Drop-Only, einzigartige Effekte ähnlich Unique-Items.
- Mehrere Tiers möglich, aber Restriktion: nicht mehrfach derselbe Lineage-Support quer über alle Skills.

### 1.6 Uncut Gems (Loot-Form)
- Drop-Ressource. Hat ein Gem-Level (z.B. Uncut Skill Gem Level 7 bis 19+).
- Im Gemcutting-Menü zum gewünschten Skill graviert oder zum Aufleveln existierender Gems verwendet.

---

## TEIL 2 — KLASSEN-ÜBERSICHT & SIGNATURE-SKILLS

Es gibt 12 geplante Klassen, davon 8+ aktuell verfügbar. Jede Klasse hat 2-3 Ascendancies. Alle Klassen können theoretisch jeden Skill nutzen — Klassenidentität ergibt sich aus Startposition im Passive Tree und Ascendancy-Synergien.

### 2.1 WARRIOR (STR) — Mace-Brawler
**Ascendancies:** Titan, Warbringer, Smith of Kitava
**Fantasy:** Brutaler Nahkampf, Slam-Skills, Warcries, Armour-Breaking, Stun-Plays.
**Signature-Skills:**
- **Boneshatter** — Nahkampf-Strike, akkumuliert Stun, Explosion bei Heavy-Stunned-Targets.
- **Earthquake** — Slam, hinterlässt nach Verzögerung Aftershock-AoE.
- **Rolling Slam** — Slam, der nach vorne rollt und mehrfach trifft.
- **Sunder** — Slam, sendet AoE-Welle, „Payoff"-Mechanik gegen Heavy-Stunned-Feinde.
- **Earthshatter** — Slam, der Spike-Reihen aus dem Boden treibt, danach Detonations-Slam.
- **Leap Slam** — Sprung-Mobility-Slam mit Payoff-Schaden.
- **Shield Charge** — Channeling-Travel, Schild voran, Knockback.
- **Perfect Strike** — Channeling-Strike, Timing-Window für massiven Crit-Bonus.
- **Molten Blast** — Projektil-AoE, Fire.
- **Volcanic Fissure** — Slam mit Lava-Riss, Fire-DoT.
- **Resonating Shield** — Channeling-Buff, akkumuliert Power, dann Release.
- **Shockwave Totem** — Totem feuert Slam-Novas.
- **Shield Wall** — Errichtet temporäre AoE-Wand, blockiert Projektile.
- **Armour Breaker** — Strike, der gegnerische Armour shreddert.
- **Infernal Cry / Seismic Cry / Rallying Cry** — Warcries (AoE-Buff/Debuff, Trigger-Tag).
- **Magma Barrier** — Persistent Buff, der reflektives Fire-AoE bei Treffer auslöst.
- **Scavenged Plating** — Persistent Buff, der Phys-Damage zwischenspeichert.
- **Time of Need** — Persistent Buff, Recovery-on-Need.
- **Overwhelming Presence** — Persistent Buff, Crit/Stun-Aura.

### 2.2 MONK (DEX/INT) — Quarterstaff-Elementalist
**Ascendancies:** Invoker, Acolyte of Chayula
**Fantasy:** Blitz-schnelle Combo-Strikes, Dash-In/Out, Power-Charges, Elemental Convergence.
**Signature-Skills:**
- **Tempest Bell** — Beschwört Glocke, die durch eigene Treffer Sound-Wellen abgibt (Wind+Lightning).
- **Killing Palm** — Execute-Strike, Bonus gegen Low-HP, generiert Power Charges.
- **Glacial Cascade** — Eis-Spike-Linie, Cold AoE.
- **Charged Staff** — Channeling, lädt Stab mit Lightning auf, nächste Treffer explodieren.
- **Falling Thunder** — Sprung mit Lightning-Schlag aus der Luft.
- **Tempest Flurry** — Multi-Hit Whirlwind aus Lightning/Wind.
- **Storm Wave** — Welle aus Donner und Wind.
- **Ice Strike** — Frost-Strike, baut Freeze-Buildup.
- **Whirling Assault** — Travel-Spinner, generiert Power Charges, Combo-Anker für Flicker Strike.
- **Flicker Strike** — Teleport-Strike, verbraucht Power/Frenzy-Charges.
- **Combat Frenzy** — Auto-Trigger Frenzy Charges bei Status-Ailment.
- **Heavenly Pillar** — Beschwört Lichtsäule, Lightning-AoE.
- **Palm Strike, Quarterstaff Techniques** — Combo-Setup-Strikes.

### 2.3 SORCERESS (INT) — Element-Casterin
**Ascendancies:** Stormweaver, Chronomancer, Disciple of Varashta (NEU 0.4)
**Fantasy:** Pure Spell-Power, Fire/Cold/Lightning, Burst-Magie.
**Signature-Skills:**
- **Fireball** — Klassiker, Projektil, Explosion bei Aufprall, Ignite.
- **Spark** — Lightning-Projektil-Ricochets, Multi-Hit-Potenzial.
- **Frost Bomb** — Verzögerter Frost-Burst, Cold Exposure.
- **Frostbolt** — Langsame, harte Frost-Bullets.
- **Ice Nova** — Nova um Caster oder Frostbolt-Projektil.
- **Cold Snap** — Kalte AoE-Explosion, scaled mit Freeze.
- **Arc** — Chain-Lightning zwischen Feinden.
- **Lightning Conduit** — Detoniert Shock-Stacks zu massivem Schaden.
- **Spark Spray, Ball Lightning** — Lightning-AoE-Werkzeuge.
- **Solar Orb** — Persistent Pulsing Fire-Orbit-AoE.
- **Flame Wall** — Setzt brennende Wand, durch die Projektile Bonus-Fire bekommen.
- **Comet** — Slam-Spell, massiver Cold-Asteroid aus dem Himmel (Build-Around-Skill).
- **Eye of Winter** — Frost-Projektil-Splitter.
- **Frost Wall** — Beschwört zerbrechliche Eiswand, Shatter-Triggern.
- **Hypothermia, Ignite Aura** — Persistent Buffs (Spirit).
- **Tempest Spectral Eye** — (Disciple-spezifisch) Djinn-basiert seit 0.5.
- **Time Snap, Time Pulse** — Chronomancer-spezifisch (Cooldown-Manipulation).

### 2.4 WITCH (INT) — Minion- & Chaos-Hexe
**Ascendancies:** Infernalist, Blood Mage, Lich, Abyssal Lich
**Fantasy:** Minion-Armee, Curses, Chaos/Bone-Spells, Necromancy.
**Signature-Skills:**
- **Bone Spear** — Schnelles Bone-Projektil, hohes Single-Target.
- **Bone Storm** — Channeling, ruft Bone-Vortex herab (Impale-Build).
- **Bone Cage** — Sperrt Feinde in Knochenkäfig ein, AoE-Crusher.
- **Bone Blast** — Bone-AoE-Detonation.
- **Bone Offering** — Persistent Buff, sacrificed corpse → minion buff.
- **Summon Skeletal Warrior** — Basis-Skelette (Krieger).
- **Summon Skeletal Arsonist** — Skelette werfen Bomben, können andere Skelette detonieren.
- **Summon Skeletal Cleric** — Heal-Minion.
- **Summon Skeletal Sniper / Reaver / Brute / Frost Mage / Storm Mage** — Spezialisten.
- **Raise Zombie / Raise Skeleton** — Klassische Reanimationen.
- **Summon Reaper** — Großer Boss-Minion.
- **Detonate Dead** — Lässt Corpse als Fire-AoE explodieren.
- **Unearth** — Beschwört Corpse aus Boden für Detonations-Combos.
- **Contagion** — Chaos-DoT, breitet sich aus.
- **Essence Drain** — Chaos-Projektil, langer DoT.
- **Despair / Enfeeble / Temporal Chains** — Curses (Single + Aura-Variante).
- **Blasphemy** — Curse-as-Aura (Spirit-reserviert).
- **Profane Ritual** — Stack-Sammler, dann Schlachten-Burst.
- **Ravenous Swarm** — (NEU 0.3) Untargetable Insektenschwarm.
- **Pain Offering, Flesh Offering, Spirit Offering** — Minion-Buff-Sacrifices.

### 2.5 RANGER (DEX) — Bow-Markswoman
**Ascendancies:** Deadeye, Pathfinder
**Fantasy:** Lange Distanz, Multi-Projektile, Crits, Mobilität.
**Signature-Skills:**
- **Lightning Arrow** — Pfeil mit Lightning-Splash, S-Tier-Meta.
- **Frost Arrow** — Cold-Variante, Freeze-Buildup.
- **Burning Arrow** — Fire/Ignite-Build.
- **Storm Rain** — Errichtet kontinuierliches AoE-Lightning-Bombardement.
- **Galvanic Shards** — Cone-Bow-Shotgun, Lightning.
- **Lightning Rod** — Pfeil platziert Marker, Lightning Conduit triggert massiv.
- **Rain of Arrows** — AoE-Pfeilregen.
- **Toxic Growth** — Wachsende Poison-AoE.
- **Snipe** — Channeling, ein extrem starker Schuss.
- **Mirage Archer** — (NEU 0.3) Dodge erzeugt Mirage, der eigene Bow-Skills nachfeuert.
- **Smoke Arrow** — Setzt Smoke-Cloud (Movement/Stealth).
- **Hunters Mark** — Mark-Curse (Cull, Crit-Bonus).
- **Disengage / Blink / Tornado Shot** — Mobility/AoE.
- **Caltrops, Explosive Trap, Cluster Grenade-Type** — DEX-Trap-Pool.

### 2.6 MERCENARY (STR/DEX) — Crossbow & Grenades
**Ascendancies:** Witchhunter, Gemling Legionnaire, Tactician
**Fantasy:** FPS-artiger Combat, WASD-Movement, Crossbow + Ammo-Skills + Grenades.
**Crossbow-Archetypen:**
- **Rapid Shot** (Sturmgewehr-Feeling), **Power Shot** (Sniper), **Burst Shot** (Shotgun).
**Signature-Skills:**
- **Galvanic Shot** — Lightning-Cone aus Crossbow.
- **Permafrost Bolts** — Frost-Bolts, Freeze-Buildup.
- **Plasma Blast** — Burst, Lightning-Konsumption.
- **Glacial Bolt** — Cold-Projektil, friert.
- **Fragmentation Rounds** — Triggert Shatter auf gefrorenen Feinden.
- **Incendiary Shot / Explosive Shot** — Fire-Bolts.
- **Armour Piercing Rounds** — Pierces shields/armour.
- **Gas Grenade** — Vergiftungs-Wolke (zündbar).
- **Flash Grenade** — Stun/Blind.
- **Oil Grenade** — Beschichtet Feinde, später entzündbar.
- **Cluster Grenade** — Mehrere Teilexplosionen.
- **Voltaic Grenade** — Lightning-AoE.
- **HE Grenade** — Reine Sprengkraft.
- **Emergency Reload, Active Reload** — Reload-Tactical-Skills.
- **Shockburst Rounds** — Lightning-AoE pro Bolt.
**Crossbow-Attachments:** Offhand-Skill-Slot statt Quiver, eigene Skill-Gems mit Support-Slots.

### 2.7 HUNTRESS (DEX) — Spear-Tänzerin (NEU in POE2)
**Ascendancies:** Amazon, Ritualist
**Fantasy:** Spear (Melee + Throw), Hit-and-Run, Wind/Storm-Themes, Bleed/Element-Hybrid.
**Signature-Skills:**
- **Lightning Spear** — Geworfener Spear mit Chain-Lightning.
- **Whirling Slash / Whirlwind Slash** — Wind-Vortex, explodiert bei Re-Cast.
- **Wall of Spears** — Stellt Spear-Reihe auf, slow + Damage.
- **Rake** — Bleed-Buildup-Strike.
- **Storm Spear / Spear Throw / Spiral Volley** — Wurftechniken.
- **Twister** — Wind-Tornado, der Feinde aufsammelt (Crowd-Control).
- **Spearfield** — Stellt rotierende Spear-Krone.
- **Disengage** — Flip-Backwards-Mobility.
- **Predator's Mark** — Mark, das Treffer chained.
- **Rapid Assault** — Multi-Stab-Combo, Poison/Bleed Build-Around.
- **Mortar Cannon** — (Spirit Gem 0.3) Totem-Granatwerfer.
- **Iron Ward** — (Spirit Gem 0.3) Speichert Phys-Damage, Release als Nova.

### 2.8 DRUID (STR/INT) — Shapeshifter (NEU 0.4 „Last of the Druids")
**Ascendancies:** Shaman, Oracle
**Fantasy:** Bear/Wolf/Wyvern-Formen, Wetter-Spells, Hybrid Phys/Element.
**Signature-Skills:**
- **Werebear Form** — Tank-Shift, mehr HP/Armour, neue Strike-Skillset.
- **Werewolf Form** — Speed-Shift, Bleed-Crits, Frenzy.
- **Wyvern/Drake Form** — Air-Mobility, Fire-Breath.
- **Maul, Rend, Pounce** — Form-spezifische Strikes.
- **Storm Call / Apocalypse** — Wettersturm-Ulti.
- **Vine Arrow / Spore Burst / Thornwall** — Natur-Spells.
- **Primal Roar** — Warcry-Variante (animalisch).
- **Lightning Storm / Hailstorm** — Wetter-AoE.
- **Bond of Nature** — Persistent Heal-Aura.
- Oracle-spezifisch: **Foresight, Echo Strike, Time Phantom** (cast same spell across timelines).

### 2.9 GEPLANT / TEASED: Templar (Flail), Shadow (Dagger), Marauder, Duelist
- Templar: Flail-Hybrid (INT/STR), Mace-Replacement-Möglichkeiten, religiöses Caster-Theme.
- Shadow: Dagger, Crit/Poison/Trap-Archetypen.

---

## TEIL 3 — KRITISCHE SKILL-MECHANIKEN

### 3.1 Tags / Keywords (System-Backbone)
Jeder Skill trägt Tags, die definieren, welche Supports/Passives wirken:
`Attack, Spell, AoE, Projectile, Melee, Strike, Slam, Channeling, Travel, Trigger, Warcry, Totem, Minion, Curse, Aura, Herald, Buff, Persistent, Duration, Sustained, Payoff, Nova, Fire, Cold, Lightning, Physical, Chaos, Cast, Bow, Crossbow, Spear, Quarterstaff, Mace, Dagger, Wand, Sceptre, Staff, Talisman`

### 3.2 Damage- & Status-Pipeline
- **Elemental Ailments:** Ignite (Fire DoT), Freeze (Hard-CC), Chill (Slow), Shock (Damage-Taken-Up), Brittle (Crit-Chance-Up), Sapped (Less Damage).
- **Physical Ailments:** Bleed (Movement scaliert), Maim, Crush (Armour-debuff).
- **Chaos:** Poison (stackbar, DoT).
- **Stun-System:** Stun-Buildup → Heavy Stun, sehr lange Disable bei Bossen — Hauptmechanik für Maces.
- **Armour Break:** Reduziert Armour additiv & lässt Phys-Damage durchschlagen.
- **Pin:** Bewegungssperre (Slow Stack → Pin).

### 3.3 Spirit-Ökonomie
- Basis: 100 Spirit.
- Erhöhung via Passive Tree, Sceptres (geben „+X to Spirit"), Amulets (Unique).
- Persistent Buffs (Heralds, Auras, Minion-Summons) reservieren Spirit dauerhaft.
- Meta Gems reservieren ebenfalls Spirit.
- Mana hingegen bleibt für aktive Casts/Attacks (kein Reservation-Konflikt mehr wie in POE1).

### 3.4 Dodge Roll & WASD
- Universelle Mechanik: i-Frames während Dodge.
- WASD-Movement seit Mercenary-Reveal — erlaubt Aim-while-Move, besonders für Ranged.

### 3.5 Weapon Swap & Dual Specialization
- Zwei Waffen-Sets gleichzeitig equipped (Hotkey-Wechsel oder Skill-Auto-Swap).
- Passive Tree erlaubt Weapon-Set-spezifische Punkte (Dual Spec).

### 3.6 Combo-System
Viele POE2-Skills sind explizit auf Combos designt:
- **Setup → Payoff:** z.B. Frost Bomb → Ice Nova; Stun-Buildup → Boneshatter-Explosion; Freeze → Shatter via Fragmentation Rounds; Ignite → Detonate Dead.
- **Tag-„Sustained" vs „Payoff":** Sustained-Skills bauen einen State auf, Payoff-Skills konsumieren ihn für Damage-Spike.

---

## TEIL 4 — TOP-10 SUPPORT GEMS (Auswahl, Pflichtwissen)

1. **Magnified Effect** — vergrößert AoE und Effekt-Größe.
2. **Multiple Projectiles** — +N Projektile.
3. **Fork / Chain / Pierce** — Projektil-Behavior-Tuner.
4. **Concentrated Effect** — kleinerer AoE, mehr Damage.
5. **Brutality** — nur Physical Damage, aber massiv mehr.
6. **Added Fire/Cold/Lightning Damage** — Element-Injection.
7. **Fire Mastery / Cold Mastery / Lightning Mastery** — More-Damage-Multiplikator pro Element.
8. **Heavy Swing** — Slower Attack, mehr Damage (Mace).
9. **Persistence** — Mehr Duration für Buffs/DoTs.
10. **Impact Force / Heavy Stun** — Skaliert Stun-Buildup.
11. **Spell Cascade** — Spell trifft zusätzlich in Linien davor/dahinter.
12. **Cast on Crit / Cast on Ignite** (Meta) — Auto-Trigger.
13. **Herbalism I/II** (Spirit-Support) — Flask-Recovery-Buffs.
14. **Profane Ritual Support** — siehe Witch-Sektion.

---

## TEIL 5 — PRODUCTION-PFLICHTENHEFT FÜR CLAUDE CODE

> **Auftrag:** Bring beim Programmieren das Maximum aus dem Spiel heraus — grafisch, klanglich, animationstechnisch. Folgende Anforderungen sind verbindlich, NICHT optional.

### 5.1 GRAFIK / RENDERING

**Engine-Empfehlung (in Reihenfolge der Eignung):**
- **Unreal Engine 5** (Nanite, Lumen, Niagara für VFX, World Partition für große Atlas-Maps) — bevorzugt, wenn AAA-Look gewünscht.
- **Unity HDRP** mit VFX Graph + Shader Graph + Addressables — wenn schnellere Iteration nötig.
- **Godot 4** mit Compute-Shadern — Open-Source-Fallback, bei kleinerem Scope.

**Visual-Direction (POE2-Referenz):**
- **Realistic Dark Fantasy.** Keine Cartoon-Glättung. Physically Based Rendering (PBR) Pflicht.
- Material-Authoring: Metall reagiert authentisch auf Fackellicht, Stoff hat Subsurface-Scattering, Wasser-Shader mit Wellengang + Reflection-Probes.
- **Dynamisches GI:** Lumen / Voxel-GI oder mindestens Light Probes mit Reflection-Probes.
- **Volumetric Lighting & Fog:** God Rays in Tempeln, dichter Nebel in Sümpfen, Lichtschächte in Höhlen.
- **Wetter-System:** Regen → flooded low-lying areas, Lightning-Spells profitieren visuell von Regen. Fog reduziert Sicht für Ranged.

**Skill-VFX-Standards (KRITISCH):**
Jeder Skill braucht **drei VFX-Phasen**:
1. **Cast/Wind-Up:** Telegraph für Spieler & Gegner (Particle-Buildup an Waffe/Hand).
2. **Travel/Active:** Trail, Sublayer, Light-Emission. Lightning = arc-noise mit additive blending; Fire = volumetric flame card + ember particles + heat distortion shader; Cold = ice-crystal-mesh + frost decals + chill-fog; Physical = dust + bone/stone debris.
3. **Impact:** Screen-Shake (skill-tier-abhängig), Hit-Decals, Element-spezifischer Burst, Slow-Mo-Frame bei Crit (1-3 Frames).

**Pro-Element-Shader-Rezept:**
- **Fire:** Animated Noise UV-Scroll, Fresnel-Glow, Bloom-Threshold tief, Ember-GPU-Particles mit gravity-curl.
- **Cold:** Refraction-Shader auf Eis-Geo, Frost-Decals als deferred-decal-volumes, Specular-Sparkle als micro-flake-normal-map.
- **Lightning:** Mesh-Lightning mit Catmull-Spline + dynamic-jitter-time, additive blend, post-process bloom + chromatic-aberration-Spike beim Cast.
- **Chaos/Poison:** Subsurface-Scatter mit purple/green absorption, miasma-fog mit slow-warp-noise, drip-particles.
- **Bone/Phys:** Hard-Surface Mesh, GPU-shatter-system, blood-decal-system mit projektor-mesh.

**Performance-Targets:**
- 60 FPS minimum auf Mid-Range (RTX 3060 / RX 6600).
- Skill-VFX müssen via **LOD und Particle-Budget-Manager** skalieren — 100+ Minions oder Storm Rain dürfen nicht crashen.
- **GPU-Instancing** für Minion-Skelette und Projektil-Sprites.
- **Mesh-Decals** statt Projector-Decals für Boden-Effekte (Frost Wall, Flame Wall).

**UI/HUD-Stil:**
- Diegetisch-okkultistisch: Verzierte Filigrane an Skill-Slots, Tropfen-Effekte für Health Globe.
- **Two Globes** (Life rot links, Mana/ES blau rechts) als ikonische POE-Komponente.
- Skill-Bar zentriert unten, Cooldown-Sweeps mit Light-Burst-Endung.
- Damage-Numbers: optional, klein, gedeckt (kein Hyperscale wie in Diablo 4).

### 5.2 SOUND DESIGN

**Audio-Middleware:**
- **FMOD** (POE2 nutzt FMOD selbst) oder **Wwise** — beide unterstützen RTPCs, Snapshots, Side-Chains.
- Programmiere ein **Snapshot-System** für Combat (Music-Duck), Boss-Encounter (Stem-Crossfade), Town (Reverb-Wechsel).

**Skill-Sound-Schichten (Pflicht pro Skill):**
1. **Wind-Up-Sound:** klanglich aufladend (Spannungs-Sweep, Synth-Riser, Whoosh-In).
2. **Body-Sound:** der eigentliche Cast (Crackle, Roar, Slam, Whoosh).
3. **Tail-Sound:** Ausklang/Echo/Sizzle.
4. **Impact-Sound:** abhängig vom Material des Ziels (Flesh = squelch, Armour = clank, Stone = crack).

**Element-spezifische Sonic-Signatures:**
- **Fire:** tiefes Whoom + Crackle-Loop + High-Sizzle-Tail. Niemals melodisch.
- **Cold:** Glass-Shatter, Wind-Whistle, Crystal-Chime (sparsam!), Sub-Bass-Drop bei Freeze.
- **Lightning:** Cracker + Tesla-Coil-Spark + Low-Hum-Bed.
- **Physical Slam:** Sub-Bass-Punch (40-80 Hz), Bone-Crack-Layer, Earth-Rumble-Tail.
- **Bow/Crossbow:** Sehnen-Twang oder Mechanischer-Klick + Whoosh + Impact-Schicht.
- **Spear Throw:** Sehr direktional, kurzer Whip-Sound.

**Positional Audio (Pflicht):**
- HRTF-fähig (Steam Audio, Microsoft Spatial Sound, oder Wwise Reflect).
- Telegraph-Sounds für Gegner-Specials: Brute-Charge = guttural growl, Construct-Beam = metallic whir. Spieler MUSS aus dem Off vorgewarnt werden.
- Distanz-Filter: Tiefpass + Reverb-Send skalieren mit Range.

**Weapon Impact Identity:**
- Mace = visceral crunch, low-thump.
- Sword = clean slice + metallic ring.
- Quarterstaff = wooden thwack mit element-overlay.
- Crossbow = mechanisches Click-Reload + heavy-thunk-fire.
- Spear = wind-whip + stab-puncture.

**Music & Adaptive Audio:**
- Orchestral-Dark-Ambient-Bed mit Stems (Strings, Choir, Percussion, Synth-Drone).
- **Side-Chain Music auf SFX-Bus**, damit Combat klanglich Platz hat.
- **Skill-spezifische Music-Mute-Overrides** für einzigartige Waffen (POE2-Vorbild „The Last Lament" Crossbow — eigene haunted Music-Schicht, mutet andere Music während Compose Requiem).
- **Boss-Phase-Transitions:** Music-Stem-Swap (z.B. Strings-Layer einblenden bei Phase 2).

**Environmental Audio:**
- Layered Ambience: Wind-Bed + Distant-Drips + Creature-Calls + Whisper-Loops (in Ruinen).
- Footstep-System mit Material-Detection (Mud, Stone, Wood, Metal, Water) — eigene 5+ Variations pro Material.
- Dynamic Rain: Light Patter → Roaring Downpour Crossfade (Volume + Filter + Reverb-Wet).

### 5.3 ANIMATION

**Tech-Foundation:**
- **Komplett neu aufgesetzte Rigs** (POE2 hat das genau deshalb als separates Spiel gebaut — die Rigs wurden NICHT von POE1 übernommen). Lerne daraus: investiere früh in saubere Rigs.
- **Root-Motion** für Slam-, Charge- und Travel-Skills (Shield Charge, Leap Slam, Whirling Assault).
- **Inverse Kinematics (IK):** Foot-IK auf unebenem Terrain Pflicht. Hand-IK für Two-Handed-Grip auf Mace/Staff.
- **Additive Layer Animation:** Aim-Offset für Bow/Crossbow während Movement.

**Animation-Pipeline:**
- Mocap für Base-Layer (Run, Idle, Walk, Dodge, Damage-Reactions).
- Keyframe-Polishing für Skills — jeder Skill braucht **Anticipation → Action → Recovery → Settle**.
- **Hit-Reactions** in mindestens 4 Richtungen (Front, Back, Left, Right) + Heavy-Stagger + Knockdown-To-Get-Up.
- **Death Animations:** Element-spezifische Variants (Ignite = burn-collapse, Freeze = shatter, Lightning = jolt-spasm, Phys = ragdoll-blend).

**Frame-Data-Disziplin (KRITISCH für Combat-Feeling):**
- Jeder Skill braucht definierte Frames:
  - **Startup (i-Frame-freie Windup-Phase)**
  - **Active (Damage-Window)**
  - **Recovery (Cancelable-Window)**
- Animation-Canceling über Dodge-Roll: alle Skills müssen ab Recovery cancelable sein.
- **Attack-Speed-Scaling:** Animationen müssen mit Stat skalieren (Time-Scale auf Animator/AnimMontage), aber Audio-Pitch-Shift mitkoppeln.

**Skill-spezifische Animation-Hooks:**
- **Slam-Skills (Earthquake, Sunder):** Camera-Shake on hit-frame, Foot-Plant mit dust-VFX-burst.
- **Channeling-Skills (Charged Staff, Resonating Shield):** Loop-Anim mit Charge-Visual-Build-Up, dedizierter Release-Anim.
- **Multi-Hit Combos (Tempest Flurry, Whirling Slash):** Frame-perfect-Loops, Combo-Counter-UI optional.
- **Bow-Skills:** Draw → Hold → Release, mit String-Bone-Physics auf Bogen-Mesh.
- **Crossbow:** Reload-Animationen sichtbar (Bolt-Insertion), Ammo-Indicator.
- **Shapeshift (Druid):** Saubere Morph-Transitions, mind. 6-12 Frames Übergang, VFX-Mask während Transition.
- **Minion-Summon:** Cast-Anim mit Ground-Crack-VFX-Sync, Minion fades in mit Skeleton-Build-Up.

**Procedural Animation Layer:**
- **Inertia/Anti-Pop-Blending** (Unity Animation Rigging / UE Motion Matching).
- **Wind/Cloth-Sim** auf Capes, Robes, Long-Hair (Druid, Sorceress).
- **Active Ragdoll** für Death + Knockback.
- **Procedural Lookat-IK** für Head-Tracking auf Gegner (Combat-Awareness-Feeling).

**Combat-Game-Feel Checkliste (zwingend):**
- **Hitstop** (Hit Pause): 2-5 Frames Freeze bei jedem Treffer, skaliert mit Damage.
- **Screen-Shake**, aber abschaltbar (POE2 hat dafür Setting!) — bias zu wenig.
- **Camera-Punch** (kurzer Kick) statt Dauer-Shake.
- **Slow-Mo-Crit:** 1-3 Frames bei Crit oder Execute.
- **Knockback-Forces** physical (nicht nur Anim).
- **Blood/Debris-Spray** richtungsabhängig vom Treffer-Vektor.

### 5.4 PERFORMANCE & QUALITY-OF-LIFE

**Settings-Menü (POE2-Standard):**
- Screen-Shake toggle.
- Particle-Density-Slider (Low / Medium / High / Ultra).
- Flashy-Effects-Reduce-Mode (Accessibility: für Photosensitive).
- Dynamic Resolution Scaling (FSR3 / DLSS3 Frame Generation Support).
- Frame-Cap (30/60/120/144/unlimited).
- Renderer-Wahl: DirectX 12 + Vulkan-Fallback (Vulkan ist auf Linux/Steam Deck oft stabiler).
- Multi-Threading toggle.

**Build-Diversity-Mantra:**
> "Du kannst jede Waffe und jeden Skill auf jeder Klasse im Endgame spielen."

Dieses Versprechen ist Gold wert. Implementiere ein **Skill-Slot-System, das NICHT klassengebunden ist** — Klassen-Identität entsteht aus Startposition im Passive Tree, nicht aus Skill-Locks.

### 5.5 NETZWERK & CO-OP

- POE2 ist Online-Only mit Co-Op bis 6 Spieler.
- Lockstep für Spell-Effekte vermeiden — Client-Side-Prediction für VFX, Server-Authoritative für Damage.
- Wenn dein Spiel offline-fähig sein soll: lerne aus POE2s Online-Only-Beschränkung und biete optional Singleplayer-Modus an.

---

## TEIL 6 — KONKRETE IMPLEMENTIERUNGS-REIHENFOLGE FÜR CLAUDE CODE

1. **Core-Loop zuerst:** Movement (WASD + Dodge), Basic-Attack, ein einziger Skill mit vollem VFX/Audio/Anim-Stack. Polish > Quantität.
2. **Skill-Gem-Data-Driven-Architecture:** Jeder Skill ist ein ScriptableObject / DataAsset mit Tags, Damage-Type, VFX-Refs, SFX-Refs, Anim-Refs, Cost, Cooldown. Code liest nur die Daten — kein Hardcoding.
3. **Support-Gem-System** als Decorator/Modifier-Pipeline (Strategy-Pattern). Jeder Support Gem mutiert das Skill-Output.
4. **Damage-Pipeline:** Hit-Event → Damage-Event-Bus → Resistance-Calc → Ailment-Buildup → Final-Damage. Plug-in-fähig.
5. **Spirit/Mana/Life-Resources** als Subscribable Observables (Event-Source-Pattern).
6. **Passive Tree als Graph:** Node-Asset + Connection-Graph. UI rendert via Pan/Zoom Canvas. Allocation = einfache Adjacency-Validation.
7. **Endgame Atlas:** Map-Pool als Pool von Procedural-Seed-Templates. Boss-Encounter als eigene Levels.

**Kritischer Hinweis zum Programmierstil:**
- **Data-Driven > Hardcoded.** Skills, Items, Passives als Assets, nicht im Code. Designer/Modder/du selbst kannst dann ohne Recompile iterieren.
- **Event-Bus** statt Direct-Coupling — Combat, UI, Audio, VFX hören mit, statt sich gegenseitig zu kennen.
- **Object-Pooling** für Projektile, Particles, Minions. Niemals Instantiate/Destroy pro Frame.
- **Asynchronous Loading** für Skill-Assets (Addressables in Unity, Soft-References in UE).

---

## TEIL 7 — SCHNELL-REFERENZ: SKILL-NAME → DAMAGE-TYPE → TAGS

| Skill | Damage | Wichtigste Tags |
|---|---|---|
| Boneshatter | Physical | Attack, Melee, Strike |
| Earthquake | Physical | Attack, AoE, Slam, Duration |
| Sunder | Physical | Attack, AoE, Slam, Payoff |
| Leap Slam | Physical | Attack, AoE, Slam, Travel, Payoff |
| Shield Charge | Physical | Attack, AoE, Channeling, Travel |
| Perfect Strike | Fire | Attack, Strike, Channeling, Fire, Duration |
| Volcanic Fissure | Phys/Fire | Attack, Slam, Fire, Duration |
| Molten Blast | Fire | Attack, AoE, Projectile, Fire |
| Infernal Cry | Fire | Warcry, AoE, Trigger, Fire, Duration |
| Herald of Ash | Fire | Buff, Persistent, AoE, Fire, Herald |
| Fireball | Fire | Spell, Projectile, Fire |
| Flame Wall | Fire | Spell, AoE, Fire, Duration |
| Solar Orb | Fire | Spell, AoE, Fire, Duration |
| Spark | Lightning | Spell, Projectile, Lightning |
| Arc | Lightning | Spell, Chaining, Lightning |
| Lightning Conduit | Lightning | Spell, AoE, Lightning, Payoff |
| Ball Lightning | Lightning | Spell, Projectile, Lightning |
| Frostbolt | Cold | Spell, Projectile, Cold |
| Ice Nova | Cold | Spell, AoE, Nova, Cold |
| Cold Snap | Cold | Spell, AoE, Cold |
| Comet | Cold | Spell, AoE, Cold, Slam |
| Frost Wall | Cold | Spell, AoE, Cold, Duration |
| Bone Spear | Phys | Spell, Projectile, Physical |
| Bone Storm | Phys | Spell, Channeling, Physical |
| Detonate Dead | Fire | Spell, AoE, Fire, Trigger |
| Contagion | Chaos | Spell, AoE, Chaos, Duration |
| Essence Drain | Chaos | Spell, Projectile, Chaos, Duration |
| Despair | Chaos | Curse, AoE, Chaos |
| Summon Skeletal Warrior | — | Spell, Minion |
| Raise Zombie | — | Spell, Minion |
| Lightning Arrow | Lightning | Attack, AoE, Projectile, Bow, Lightning |
| Rain of Arrows | Phys | Attack, AoE, Projectile, Bow |
| Tornado Shot | Phys | Attack, Projectile, Bow |
| Snipe | Phys | Attack, Channeling, Bow |
| Mirage Archer | — | Spirit, Trigger, Buff |
| Galvanic Shot | Lightning | Attack, AoE, Projectile, Crossbow, Lightning |
| Permafrost Bolts | Cold | Attack, Projectile, Crossbow, Cold |
| Glacial Bolt | Cold | Attack, Projectile, Crossbow, Cold |
| Fragmentation Rounds | Phys/Cold | Attack, AoE, Crossbow, Trigger |
| Explosive Shot | Fire | Attack, AoE, Crossbow, Fire |
| Gas Grenade | Chaos | Attack, AoE, Grenade, Duration |
| Flash Grenade | — | Attack, AoE, Grenade, Trigger |
| Oil Grenade | — | Attack, AoE, Grenade, Duration |
| Cluster Grenade | Phys | Attack, AoE, Grenade |
| Voltaic Grenade | Lightning | Attack, AoE, Grenade, Lightning |
| Killing Palm | Phys | Attack, Melee, Strike, Execute |
| Tempest Flurry | Lightning | Attack, Melee, AoE, Lightning |
| Charged Staff | Lightning | Channeling, Buff, Lightning |
| Falling Thunder | Lightning | Attack, AoE, Travel, Lightning |
| Glacial Cascade | Cold | Spell, AoE, Cold |
| Tempest Bell | Lightning | Attack, Trap-like, Lightning, Nova |
| Whirling Assault | Phys | Attack, Travel, Melee |
| Flicker Strike | Phys | Attack, Strike, Travel |
| Lightning Spear | Lightning | Attack, Projectile, Spear, Lightning |
| Whirling Slash | Phys | Attack, AoE, Spear, Melee |
| Wall of Spears | Phys | Attack, AoE, Spear, Duration |
| Rake | Phys | Attack, Strike, Spear, Bleed |
| Twister | Phys | Attack, AoE, Spear |
| Iron Ward | Phys | Spirit, Buff, Persistent, Physical |
| Mortar Cannon | Phys | Spirit, Totem |
| Ravenous Swarm | Chaos | Spirit, Minion, Chaos |

---

## ABSCHLUSS — GOLDENE REGELN

1. **Skill-Feeling > Skill-Anzahl.** Lieber 30 hervorragend animierte, klingende, aussehende Skills als 200 generische.
2. **Telegraph alles.** Jeder Skill (Spieler & Gegner) braucht Wind-Up, das Spieler lesen können — visuell UND akustisch.
3. **Combo-Design einbauen.** Setup → Payoff ist die DNA von POE2. Plane jeden Skill mit Blick auf einen Partner-Skill.
4. **Data-Driven von Tag 1.** Sonst stirbst du in technischer Schuld.
5. **Performance ist Feature.** 60 FPS minimum, sonst fühlen sich Skills nicht „crisp" an.
6. **Audio macht 50% des Feelings.** Investiere mindestens so viel Aufwand in Sound wie in VFX.
7. **Animations-Frame-Disziplin.** Anticipation/Action/Recovery sauber definiert, sonst fühlt sich der Combat „schwammig" an.
8. **Accessibility nicht vergessen.** Photosensitive-Mode, Screen-Shake-Toggle, Colorblind-Modi für Ailments.

---

*Quellen-Snapshot: poewiki.net, pathofexile2.wiki.fextralife.com, maxroll.gg/poe2, game8.co Path of Exile 2, offizielle Path of Exile Foren (Skill Sound Design Dev-Blogs), Patch 0.3 „The Third Edict" / 0.4 „The Last of the Druids" / 0.5 „Fate of the Vaal".*
