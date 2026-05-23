# POE2-STYLE GAMEPLAY SYSTEMS — ERWEITERUNG ZUM SKILL BRIEFING

> **Zweck:** Vertieftes Implementierungs-Dokument für Death/Respawn-Cinematics, Minimap, Partikel-Sichtbarkeit, Monster-KI, Boss-Encounters, UI-Vollständigkeit und Skilltree-Optik. Liest sich als direkter Auftragstext für Claude Code. Ergänzt das `POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md`.

---

## TEIL A — DEATH-ANIMATION & RESPAWN-CINEMATIC

### A.1 Pflicht-Verhalten
Wenn die Health auf 0 fällt, MUSS folgende Sequenz automatisch ablaufen (nicht überspringbar im ersten Run, ab 2. Tod skippbar mit Space):

```
[1] On-Death-Trigger (HP <= 0)
    ↓
[2] Damage-Type wird aus letztem Hit gelesen (last_damage_source)
    ↓
[3] Player wechselt in State PLAYER_DYING (Input gelockt)
    ↓
[4] Damage-Type-spezifische Death-Animation (1.5–3 Sek)
    ↓
[5] Full-Screen Transition-VFX (1.0–1.5 Sek, Damage-Type-spezifisch)
    ↓
[6] Black/Fade-Pause (0.5 Sek, Audio-Ducking)
    ↓
[7] Wake-Up in City: Charakter liegt/kniet, kommt zu sich
    ↓
[8] Voice-Line / Quote-Text aus Pool gewählt (Damage-Type-spezifisch)
    ↓
[9] Wake-Up-Animation → Idle → Control-Restore
```

### A.2 Death-Animations pro Damage-Type

| Damage-Type | Animation | Sound | VFX-Layer |
|---|---|---|---|
| **Fire / Ignite** | Charakter taumelt, Hände schützen Gesicht, knickt ein, brennt auf Boden weiter | Schreie + Knistern + Sizzle-Tail | Flammen-Mesh-Card am Körper, Embers, Heat-Distortion-Shader |
| **Cold / Freeze** | Mid-Action eingefroren, kippt um, **zerschellt** in Eiskristalle (Shatter-Mesh) | Glass-Crack + Crystal-Chime + Sub-Bass-Drop | Ice-Encasement-Shader, dann Polygon-Shatter via GPU |
| **Lightning / Shock** | Spasm-Loop 0.8s (rapid pose-flicker), dann Kollaps verkohlt rauchend | Tesla-Cracker + High-Whine + Body-Thump | Lightning-Arcs am Körper, Burn-Marks-Decals, Ozone-Smoke |
| **Physical / Crush** | Active-Ragdoll-Blend ab Treffer, Knockback-Trajectory, Bone-Crack-Sound | Bone-Crack + Blood-Spurt + Heavy-Body-Drop | Blood-Decals richtungsabhängig, Dust-Burst beim Aufschlag |
| **Bleed** | Kniefall, Hand auf Wunde, langsames Umkippen, Blutpfütze wächst | Wet-Gurgle + Heartbeat-Slowing | Blood-Decal-Projektor, der über 2s wächst |
| **Chaos / Poison** | Würgen, an die Kehle greifen, taumeln, kollabieren, grüner Dampf | Coughing + Wet-Choke + Hiss | Toxic-Subsurface-Tint, Drip-Particles, Green-Steam |
| **Void / Chaos-Pure** | Wird von Inside ausgelöscht (Dissolve-Shader von innen) | Reversed-Whisper + Sub-Drone | Dissolve-Mask-Shader, dunkle Energie spiralt einwärts |
| **Falling / Pit** | Aaaaah-Schrei, Camera folgt nach unten, Cut zu Schwarz | Wind-Doppler + Impact-Off-Screen | Motion-Blur, Vignette closing |
| **Generic / Unknown** | Fallback: Standard-Kollaps nach vorne | Generic-Death-Grunt | Light-Vignette |

**Tech-Hinweis:** Speichere `last_damage_source` permanent im Player-State. Jeder Hit aktualisiert: `{damage_type, source_entity_id, damage_amount, hit_position, hit_vector}`. On-Death liest diesen Snapshot.

### A.3 Full-Screen Transition-VFX

Nach der Body-Animation, kurz bevor zur Stadt geschnitten wird:

- **Fire-Death:** Flammenfront wischt von rechts unten nach links oben über den ganzen Screen, Ember-Layer, danach Asche-Regen-Fade in Schwarz.
- **Cold-Death:** Frost kriecht von Bildschirmrändern nach innen, Kristalle wachsen vom Rand, Picture „friert" und zerspringt in 12-20 Eis-Polygone, Cut zu Schwarz.
- **Lightning-Death:** Screen-White-Flash (max 2 Frames!), Strom-Linien wandern über das Bild, TV-Static-Layer kurz, dann Schwarz.
- **Physical-Death:** Blutstropfen klatschen aufs „Glas" der Kamera, Riss-Shader spinnt sich aus Aufprall-Punkt, Schwarz.
- **Bleed:** Vignette wird rot, langsam radial nach innen verdunkelnd, Herzschlag-Audio wird leiser, Schwarz.
- **Chaos:** Bild zerfließt (Wave-Distortion + Color-Sickness-LUT), grüner Schimmer am Rand, Implosion zum Punkt.
- **Void:** Screen wird von innen heraus „aufgegessen" (Dissolve-Mask aus Mittelpunkt), Negative-Spike, Schwarz.

**Implementierungs-Hinweis:** Implementiere als **PostProcess-Stack** mit eigener „DeathTransition"-Material-Instanz. Damage-Type-Parameter wechselt die Material-Variation, eine Master-Timeline (1.0–1.5s) treibt alle Werte.

### A.4 Wake-Up in der Stadt

- Spawn-Position: fester Wegpunkt in der Stadt (z.B. „Town Shrine").
- Charakter spawnt liegend oder kniend, je nach Klasse:
  - Warrior: auf dem Rücken, schwerer Atem, dreht sich auf die Seite, steht auf.
  - Sorceress / Witch: kniend, eine Hand am Boden, hebt langsam den Kopf.
  - Ranger / Huntress: hockend, ein Knie unten, prüft Waffe.
  - Monk: Schneidersitz, öffnet Augen, atmet aus.
  - Druid: in Tierform am Boden, morpht zurück in Menschenform.
  - Mercenary: liegt seitlich, hustet, prüft Crossbow.
- Camera: leichte Iso-Tilt-Variation, langsam einzoomen auf Charakter (3 Sek), dann zurück auf Standard-Iso.
- Audio: Atem-Loop, Herzschlag verklingt, ambiente Town-Music verzögert einsetzen lassen (1-2 Sek nach Wake).

### A.5 Quote-System (Death-Lines)

Pool von 8-12 Sprüchen pro Damage-Type pro Klasse. Random aus Pool, niemals selbe Line zweimal hintereinander.

**Beispiele (Fire-Death, Warrior):**
- „Die Asche kennt meinen Namen — noch nicht."
- „Ich habe schon heißer geblutet."
- „Das Feuer wollte mich nicht behalten."

**Beispiele (Cold-Death, Sorceress):**
- „Selbst Eis schmilzt vor dem Willen."
- „Frost ist nur eine andere Form des Atems."

**Beispiele (Physical-Death, generic):**
- „Knochen heilen. Stolz auch."
- „Wer einmal stirbt, kennt den Weg zurück."

**Format-Empfehlung:** JSON / YAML pro Sprache, gekeyt nach `{class, damage_type, idx}`. Sub-Pools für „first_death", „repeated_deaths_same_session", „death_in_boss_arena" für Variation.

UI: Text fadet 0.5s nach Wake-Up von unten ein, hält 3-4 Sek, fadet aus. Schriftart: Display-Serif (Cinzel, Trajan Pro, oder selbstgemacht). Subtle Texture (etwas Papier-Grain).

### A.6 Code-Architektur (Pseudo-Code)

```python
# Pseudocode — Engine-agnostisch
class PlayerDeathSystem:
    def on_player_died(self, last_damage: DamageEvent):
        damage_type = last_damage.type
        self.player.set_state(PlayerState.DYING)
        self.player.disable_input()

        # 1) Death-Animation
        anim = self.death_anims[damage_type]  # dict mit AnimRef
        self.player.play_animation(anim, blocking=True)

        # 2) Transition VFX
        self.postprocess.play_death_transition(damage_type, duration=1.2)

        # 3) Black-Pause
        yield wait(0.5)
        self.audio.duck_all(amount=-60dB, fade=0.3)

        # 4) Teleport to Town
        self.player.teleport(self.town_shrine_position)
        self.player.set_state(PlayerState.WAKING)

        # 5) Wake-Up Anim
        wake_anim = self.wake_anims[self.player.class_id]
        self.player.play_animation(wake_anim)

        # 6) Quote
        quote = self.quote_pool.pick(self.player.class_id, damage_type)
        self.ui.show_death_quote(quote, duration=4.0)

        # 7) Restore Control
        yield wait(2.0)
        self.player.enable_input()
        self.player.set_state(PlayerState.IDLE)
```

---

## TEIL B — MINIMAP & NAVIGATION

### B.1 Status-Quo-Problem
Aktuelle Minimap zeigt die Umgebung nicht präzise genug, Spieler verlieren Orientierung. Ziel: **Sofort lesbare**, kontextreiche Karte mit Wegfindung.

### B.2 Tech-Architektur

**Empfehlung:** Procedural Mini-Map aus Level-Daten generieren — NICHT Render-To-Texture von oben (zu teuer, falsche Stilistik).

```
Level-Loaded
    ↓
Floor-Mesh + Walkable-Area-NavMesh wird gesamplet
    ↓
2D-Topdown-Grid (z.B. 1m pro Pixel)
    ↓
Walkable = hell, Wand = dunkel, Lava/Hole = rote Markierung
    ↓
Render in RenderTexture / Off-Screen-Buffer
    ↓
Minimap-Widget zeigt Crop um Spieler herum
```

### B.3 Fog of War
- **Discovered-Tiles** werden zur Laufzeit revealed (Radius z.B. 25m um Player).
- Persistiert pro Map-Instance (in POE-Sprache: pro Map-Layout-Seed).
- Gradient-Edge an Fog-Grenze (kein Hard-Cutoff — sieht billig aus).
- Sichtradius skalierbar via Item-Mod „+X% Light Radius".

### B.4 POI- und Icon-System

Pflicht-Icons auf Minimap UND Full-Map:

| Icon | Bedeutung | Farbe / Form |
|---|---|---|
| ⭐ | Quest-Ziel | Gold, pulsierend |
| 🏠 | Stadtportal / Waypoint | Cyan, Diamant |
| 💀 | Boss-Position | Rot, Totenkopf |
| 📦 | Truhe | Goldgelb |
| 🛒 | Vendor / NPC | Weiß |
| ⚒ | Crafting-Bench | Grau-Bronze |
| 🚪 | Unentdeckter Ausgang | Cyan-Outline, transparent |
| 🚪✓ | Entdeckter Ausgang | Cyan, solid |
| ⚠ | Spezial-Encounter (Breach, Ritual) | Lila |

**Quest-Path:** Schimmernde Spur (Breadcrumb-Trail) auf Boden in der Welt UND als gestrichelte Linie auf Karte. Schaltbar (manche Spieler mögen das nicht).

### B.5 Full-Map (Tab/M)
- Volle Map als Overlay, halbtransparent über Spielwelt.
- Zoom-Levels: 0.5x / 1x / 2x / 4x.
- Hover über Icon zeigt Tooltip („Vendor: Clarissa — Verkauft Tränke").
- Spieler kann eigene Marker setzen (Rechtsklick → Marker-Picker).

### B.6 Layout-Pflicht
- Minimap top-right, **mind. 250x250 Pixel**, idealerweise resizable.
- Klassen-Theme im Rahmen (siehe Teil H — Skilltree-Optik).
- Norden ist fix oben (Toggle für „Rotate with Player" für Spieler, die das wollen).
- Compass-Strip (oben Mitte, optional): zeigt Richtungen der nächsten 2-3 Objectives auch wenn off-map.

### B.7 Code-Hinweise
```
- NavMeshSampler-Service generiert Walkability-Texture On-Level-Load
- FogOfWar-System persistiert in MapInstance.Save() / .Load()
- POIRegistry registriert Icons mit (WorldPos, IconType, Lifetime)
- MinimapRenderer pollt POIRegistry + Player.Position pro Frame, rendert UI
```

---

## TEIL C — PARTIKEL-SICHTBARKEIT & AOE-TELEGRAPH-HIERARCHIE

### C.1 Status-Quo-Problem
Im Flammen-Dungeon sind Partikel zu dicht und Spieler wissen nicht, was tödlich ist. Player stirbt, weil tödliche AoE im VFX-Lärm untergeht. Das ist **inakzeptabel** und MUSS gefixt werden.

### C.2 Zwei-Schichten-Partikel-Architektur (PFLICHT)

Jeder Partikel im Spiel gehört zu **genau einer** dieser zwei Kategorien:

#### Schicht 1: AMBIENT (atmosphärisch, gameplay-irrelevant)
- Beispiel: Asche-Flocken, Fackel-Funken, Glühwürmchen, Dust-Motes, Rauch-Schwaden im Hintergrund.
- Wird durch Density-Slider in den Settings reduzierbar (Low/Medium/High/Ultra).
- Wird **automatisch reduziert**, wenn `gameplay_critical_vfx_count > Threshold` (Dynamic Culling).
- Wird **automatisch reduziert** im Boss-Encounter um 60-80%.
- Render-Layer: niedrige Priorität, weiter weg von Camera, additive blend, niedriges Bloom-Gewicht.

#### Schicht 2: GAMEPLAY-CRITICAL (Telegraph oder Damage-Carrier)
- Beispiel: AoE-Telegraph, Skill-Indicator, Projektil, Hazard-Field, Ground-DoT.
- NIEMALS culling-bar.
- Sind durch alle Ambient-Effekte hindurch sichtbar (Z-Test angepasst oder höherer Z-Order).
- Eigenes Farbschema mit hohem Kontrast.

### C.3 AoE-Telegraph-Standards (NICHT VERHANDELBAR)

Jede tödliche Boden-AoE braucht **drei Indikatoren**:

1. **Ground-Decal (Outline)** — pulsierend, klar erkennbar
   - **Rot** = Schaden bei Eintritt, sofort tödlich
   - **Orange** = Schaden über Zeit (Lava, Poison-Pool)
   - **Gelb** = Knockback / CC, kein Direkt-Schaden
   - **Lila** = Chaos / Curse-Field
   - **Cyan** = Verbündete Buff-Zone

2. **Sound-Cue** — Wind-Up-Sound mit klarer Direktionalität
   - Tieffrequenter Warn-Brumm 0.5-1.0s vor Aktivierung
   - Funktioniert AUCH wenn Partikel gerade unsichtbar wäre (Audio = Backup-Telegraph)

3. **Mid-Air-Indicator** für aerial AoE (Comet, Slam aus Luft)
   - Sphärischer Marker mit Countdown-Pulse
   - Bei Comet z.B. ein Schatten am Boden + ein wachsender Stern-Riss

### C.4 Critical-VFX-„See-Through"-Lösung

Wenn ein Spieler in einem dichten Particle-Feld (z.B. Fire-Storm) steht:

- **Player-Outline-Shader (Rim Light)** macht den Charakter durch jedes VFX sichtbar.
- **Critical-AoE-Shader** rendert mit Stencil-Test, sodass er IMMER über Ambient-Particles gezeichnet wird.
- **Tactical Reduce-Mode** in Settings: Alle eigenen + ally Skill-Effekte um 50% transparent, gegnerische AoE bleibt 100%.

### C.5 Accessibility (zwingend)

- **Photosensitive-Mode:** entfernt rapid-flashing (Lightning-Spam), max. 3 Flash-Frames/Sekunde.
- **High-Contrast-AoE-Mode:** Telegraph-Decals werden mit Solid-Fill statt Outline gerendert.
- **Sound-Only-AoE-Cue:** für sehbehinderte Spieler, accentuierte Audio-Cues für AoE.

### C.6 Code-Architektur

```
class VFXSystem:
    AMBIENT_LAYER     = Layer(priority=10, cullable=True,  bloom_strength=0.3)
    GAMEPLAY_LAYER    = Layer(priority=50, cullable=False, bloom_strength=0.8)
    TELEGRAPH_LAYER   = Layer(priority=80, cullable=False, bloom_strength=1.0, stencil_write=True)
    UI_OVERLAY_LAYER  = Layer(priority=99, cullable=False)

class AoeTelegraph:
    def __init__(self, position, radius, damage_type, windup_time, lifetime):
        self.decal = spawn_decal(layer=TELEGRAPH_LAYER, color=color_for(damage_type))
        self.audio = play_sound_3d("aoe_windup", position=position)
        if damage_type == AERIAL:
            self.add_air_indicator()
    def on_activate(self):
        self.spawn_damage_volume()
        self.audio.play("aoe_impact")
```

---

## TEIL D — MONSTER-KI (Sichtfeld, Patrouille, Reaktionen)

### D.1 Status-Quo-Problem
Monster verhalten sich wie magnetisch angezogen — sie wissen sofort wo der Spieler ist, egal wo. Das zerstört das immersive Combat-Erlebnis. Fix-Ziel: **Realistische Wahrnehmung mit Patrouille → Alert → Engage → Lose Sight → Reset.**

### D.2 State Machine (Pflicht-Struktur)

```
┌─ IDLE ──────────┐
│  - Steht, evtl. Idle-Anim (umschauen, kratzen)
│  - Polling: sees_player? hears_noise?
└────────┬────────┘
         │ Patrouille-Pfad gesetzt
         ▼
┌─ PATROL ────────┐
│  - Bewegt sich zwischen Waypoints oder in Random-Area
│  - Polling: sees_player? hears_noise?
└────────┬────────┘
         │ sieht/hört etwas
         ▼
┌─ ALERT ─────────┐  (3-5 Sek, untersucht Quelle)
│  - Dreht sich zum Geräusch
│  - Bewegt sich vorsichtig zur Position
│  - Wenn Sichtkontakt → AGGRO
│  - Wenn nichts → zurück zu PATROL
└────────┬────────┘
         │ Bestätigte Bedrohung
         ▼
┌─ AGGRO / COMBAT ┐
│  - Engagement nach Archetyp (siehe Teil F)
│  - Pack-Awareness: ruft andere im Radius
└────────┬────────┘
         │ Verliert Sicht > Leash-Timer abgelaufen
         ▼
┌─ SEARCH ────────┐ (5-8 Sek)
│  - Bewegt sich zu letzter bekannter Position
│  - Wenn nichts → RESET
└────────┬────────┘
         │
         ▼
┌─ RESET ─────────┐
│  - Bewegt sich zurück zu Patrouille-Pfad
│  - Heilt sich auf Full-HP (klassisches MMO/ARPG-Verhalten)
└─────────────────┘
```

### D.3 Sichtfeld-System

```
class SightCone:
    fov_degrees = 90       # Standard humanoid
    range_meters = 15      # Standard
    peripheral_fov = 180   # halbiert effektive Range (Augenwinkel)
    peripheral_range = 6
    requires_line_of_sight = True
```

**Archetypen-Variation:**
- **Wachen / Soldaten:** FOV 100°, Range 18m
- **Tiere / Spürer (Wolf, Hund):** FOV 140°, Range 12m, plus Geruchssinn (siehe D.4)
- **Schlafende Monster:** FOV 0° bis ge-„weckt", dann normal
- **Blinde Monster (Bat, Mole):** FOV 0°, Range 0, nur Hearing
- **Eyestalk / Boss-Augen:** FOV 360°, aber langsam (rotating)

### D.4 Hearing & Smell

- **Hearing-Range:** Standard 10m, Spieler-Geräusche werden „lauter" durch Skill-Casts.
- **Noise-Values pro Player-Action:**
  - Walken: 3m
  - Rennen (Sprint/Dodge): 8m
  - Skill-Cast: 12-25m je nach Skill (Comet = sehr laut, Smoke Arrow = leise)
  - Schritt auf Glas / Holz: +5m
- **Stealth-Bonus:** Monk/Shadow können „Quiet Movement" als Passive haben.
- **Smell** (für Tiere): ignoriert LOS, aber benötigt Wind-Direction-Logic optional, sonst einfach Radius.

### D.5 Patrol-Behavior

Drei Patrol-Patterns je nach Mob-Setup:

1. **Waypoint-Path:** Designer setzt Spline mit 3-8 Punkten, Mob läuft Ping-Pong oder Loop. Idle-Pause an jedem Punkt (1-3 Sek randomisiert).
2. **Random-In-Area:** Spawn-Area definiert eine Box/Kreis, Mob wählt Random-Punkt innerhalb, läuft hin, Idle, wiederholt.
3. **Stationary-Guard:** Mob steht fest, dreht sich periodisch (Scan-Rotation +-45°).

### D.6 Pack-Awareness

- Monster im Radius des Alerters (z.B. 8m) gehen ebenfalls in ALERT-State, aber mit **0.5–1.5 Sek Verzögerung** (sieht natürlicher aus).
- **Alpha-Mob:** Wenn Alpha im Pack stirbt, Beta-Mobs werden 2 Sek lang fearful (Backstep) oder enraged (Damage-Buff). Random.
- **Coordination-Patterns:** Manche Archetypen (siehe Teil F) machen flanking, andere bilden Schildwall.

### D.7 Aggro-Dropping & Reset

- **Leash:** Wenn Spieler > 30m vom Mob entfernt UND keine Sichtlinie für > 5 Sek → SEARCH State.
- **Out-of-Combat-Heal:** Bei RESET regeneriert Mob 100% HP über 3 Sek (verhindert Cheese durch Run-Away).
- **Sticky-Aggro:** Manche Bosse / Elite-Mobs haben Leash 100m+ und resetten nie (Boss-Arena-Mechanik).

### D.8 Behavior-Tree-Empfehlung

Implementierung als **Behavior Tree** (Unreal: BT/Blackboard, Unity: Behavior Designer / NodeCanvas / eigenes), NICHT als monolithische State Machine im Code. Vorteile:
- Designer-Friendly
- Per-Archetyp wiederverwendbar (Wolf vs. Goblin teilen 80%, unterscheiden sich in Leaf-Nodes)
- Debug-Visualisierung Pflicht (BT-Viewer im Editor)

### D.9 Performance

- Nicht alle Mobs auf der Map ticken jeden Frame. **LOD-System:**
  - In 30m+: Full-Tick
  - 30-80m: 0.2s-Tick
  - 80m+: Frozen (kein Update bis Player nähert sich)
- **Sight-Check** ist teuer (Raycast) — staggere über Frames (Round-Robin pro Mob alle 5-10 Frames statt jeden Frame).

---

## TEIL E — BOSS-ENCOUNTERS

### E.1 Status-Quo-Problem
Bosse sind sofort da, haben generische Attacken, gleiche Arena. Fix-Ziel: **Jeder Boss ist ein Event mit eigener Identität, Arena, Intro, Moveset, Phasen.**

### E.2 Boss-Spawn-Architektur (PFLICHT)

```
class BossArena:
    trigger_volume: TriggerBox  # Spieler-Eintritt löst Encounter
    spawn_method: SpawnMethod   # ENUM: RISE_FROM_GRAVE, RIDE_IN, PORTAL,
                                #        ASSEMBLE, FALL_FROM_SKY, AWAKEN,
                                #        REVEAL, DESCEND_FROM_THRONE
    intro_cinematic: CinematicSequence
    boss_prefab: ActorPrefab
    door_lock_on_enter: bool = True
    door_unlock_on_death: bool = True
    music_swap: AudioSnapshot
    arena_state_changes: List[PhaseTrigger]  # Bei HP-Schwellen
```

**Spieler betritt → Trigger löst aus:**
1. Türen schließen sich (visuell und mechanisch).
2. Music swappt (Combat-Boss-Stem).
3. Camera-Cut auf Boss-Spawn-Point.
4. Intro-Cinematic (Boss-spezifisch, 3-8 Sek).
5. Spieler-Control gesperrt während Cinematic.
6. „BOSS NAME — Boss-Title" Lower-Third-UI faded ein.
7. Health-Bar oben oder unten erscheint.
8. Boss attackiert.

Beim zweiten Encounter: Cinematic skippbar (Space hält → skip).

### E.3 Boss-Spawn-Methoden (Beispiele, alle als Templates verfügbar machen!)

| Methode | Beschreibung | Beispiel-Boss |
|---|---|---|
| **RISE_FROM_GRAVE** | Erdriss öffnet sich, Knochen-Hand greift heraus, Boss klettert raus, schüttelt Erde ab | Necromancer, Undead Champion |
| **RIDE_IN** | Cinematic: Boss reitet (Pferd/Wyvern/Insect-Mount) in Arena, dismount mit Animation | Knight-Boss, Skull King |
| **PORTAL** | Rote/Lila Portal-Spirale öffnet sich, Boss tritt heraus, Portal kollabiert hinter ihm | Demon, Eldritch Being |
| **ASSEMBLE** | Boss-Stücke fliegen zusammen (Magnetic-Attract VFX), Click-Snap-Anim | Construct, Mechanical Boss |
| **FALL_FROM_SKY** | Camera blickt nach oben, Boss crasht ein, Schockwelle, Staub | Dragon, Meteor-Boss |
| **AWAKEN** | Boss saß die ganze Zeit verkleidet als Statue / Sarg / Stein. Augen leuchten, bewegt sich erstmals | Stone Guardian, Sealed Demon |
| **REVEAL** | Boss war im Raum, aber NPC-Kostüm. Maske fällt, transformiert. | Verräter-NPC, Politiker-Boss |
| **DESCEND_FROM_THRONE** | Sitzt auf Thron, erhebt sich pathetisch langsam, läuft Stufen runter | König, Lord-Boss |
| **EMERGE_FROM_LIQUID** | Aus Lava/Wasser/Schleim taucht Boss empor | Lava-Lord, Slime-Boss |
| **SHATTER_PRISON** | Eingeschlossen in Kristall/Käfig, sprengt sich frei | Bound Demon |

### E.4 Arena-Design (boss-spezifisch)

Jede Boss-Arena MUSS arena-spezifische Features haben:

- **Necromancer-Arena:** Gräber überall (können Skelette spawnen), zentraler Altar (Phase-2-Buff).
- **Knight-Arena:** Stables an Seiten (Pferd kann zurückkommen für Charge), Banner-Pillars (zerstörbar für Cover).
- **Lava-Lord-Arena:** Lava-Strömungen am Rand (Damage), kühlere Inseln (Safe-Spots), die sich erhitzen.
- **Mechanical-Boss-Arena:** Conveyor-Belts, Stamp-Pillars (Hazard), Power-Cores (zerstörbar für Stagger).
- **Mage-Boss-Arena:** Floating Stones (Cover, aber zerstörbar), Magic-Circles am Boden (Buff oder Hazard).

**Pflicht:** Arena bestimmt Mechanik. Nie generischer leerer Raum.

### E.5 Multi-Phase-Encounter

Standard: 3 Phasen pro Boss.

- **Phase 1 (100%–66% HP):** Grund-Moveset, 3-4 Attacken.
- **Phase 2 (66%–33% HP):** Boss enraged, neue Attacken (2-3), Arena verändert sich (z.B. Lava bricht durch Boden).
- **Phase 3 (33%–0% HP):** Verzweiflungs-Phase, schnellere Casts, Ultimate-Skill alle 30 Sek, Adds spawnen.

Phase-Trigger:
```
{
  "hp_threshold": 0.66,
  "play_animation": "phase_2_transition",
  "invuln_during": true,
  "spawn_adds": ["skeleton_warrior", "skeleton_warrior"],
  "arena_change": "lava_phase_2",
  "music_layer_add": "drums_phase_2",
  "screen_shake": 0.7,
  "voice_line": "boss_phase2_quote"
}
```

### E.6 Attack-Pool-Design (jeder Boss UNIQUE)

Minimum-Attack-Pool pro Boss (skill-design-mäßig diversifiziert):

| Slot | Typ | Beispiel |
|---|---|---|
| **A1** | Basis-Melee (kurzer Wind-Up) | Schwertschwung, Klauenhieb |
| **A2** | Ranged / Projektil | Speerwurf, Feuerball, Pfeilregen |
| **A3** | AoE-Zone (langer Wind-Up, telegraphed) | Boden-Slam, Lava-Pool, Frost-Nova |
| **A4** | Mobility / Gap-Closer | Charge, Teleport, Leap |
| **A5** | Crowd-Control | Stun-Roar, Fear-Aura, Slow-Web |
| **U1** | Ultimate / Signature (Phase 2+ unlock) | Boss-spezifisch, lang telegraphed, hoher Damage |
| **R1** | Reaktion / Counter (situational) | Block-Counter, Parry-Riposte, Phase-Shift |

**WICHTIG:** Jeder Boss hat EIGENE Variation jedes Slots. Nicht „Fireball" wiederverwendet. Wenn zwei Bosse beide Lightning machen, dann z.B. Boss A „Chained Lightning" und Boss B „Static Field Pulse".

### E.7 Telegraph-Standards (Boss-Edition)

- Jede Attack mit Damage > 30% Player-HP MUSS sichtbares Wind-Up haben (Animation + Decal + Sound).
- Wind-Up-Zeit skaliert mit Damage: Big-Damage-Hits = 1.0-2.0s Wind-Up (dodgeable).
- Schnelle Pokes (A1) = 0.2-0.4s Wind-Up (testet Reflexe).
- Ultimate (U1) = 2.0-4.0s mit unverkennbarem Camera-Shake oder Music-Spike.

### E.8 Adds & Mechanics

- **Add-Spawning:** Adds in Phase 2/3, an festen Spawn-Points der Arena. Adds haben eigene KI (siehe Teil D + F).
- **Environmental Mechanics:** Zerstörbare Pillars, ausnutzbare Hazards (Lock Boss in Frost-Pool für Stagger).
- **Player-Action-Required-Mechanics:** „Spieler muss zu Altar laufen und Glyph aktivieren, sonst Wipe in 10 Sek." — fördert Engagement.

### E.9 Boss-Health-UI

- Dedicated Boss-Bar (zentriert unten oder oben Mitte).
- Boss-Name + Title („Asariel — der Erste Verräter").
- Phase-Indikatoren als Marker am Health-Bar (kleine Linien bei 66% und 33%).
- Status-Effekt-Icons auf der Bar (Boss is „Burned", „Stunned", „Vulnerable").

---

## TEIL F — MONSTER-ARCHETYPEN & ATTACK-VIELFALT

### F.1 Status-Quo-Problem
Mobs machen alle dasselbe. Fix: **Klar erkennbare Archetypen mit Signature-Mechaniken.**

### F.2 Pflicht-Archetypen-Roster

| Archetyp | Verhalten | Signature-Attacken | Beispiel-Skin |
|---|---|---|---|
| **BRUTE** | Tank, langsame schwere Hits, hohe HP | Slam (AoE-Telegraph), Charge, Grab | Ogre, Big Zombie |
| **SKIRMISHER** | Schnell, Hit-and-Run, dodged | Stab + Backstep, Dual-Strike, Roll-Away | Goblin, Cultist |
| **CASTER** | Bleibt auf Distanz, telegraphed Spells | Fireball, Curse, Summon-Add | Witch, Warlock |
| **RANGED** | Pfeile/Bolts, Kiting | Aimed Shot, Volley, Snipe | Archer, Crossbowman |
| **SUPPORT/HEALER** | Heilt Allies, buffs, prio kill | Heal-Beam, Resurrect, Damage-Aura für Pack | Cleric, Shaman |
| **SUMMONER** | Spawned Adds dauerhaft, schwach selbst | Summon-Skeleton, Necromantic Pulse | Bone Witch |
| **CHARGER** | Sprintet auf Spieler zu, explodiert oder Knockback | Suicide-Boom (Telegraphed!), Knockback-Tackle | Demon-Dog, Bomb-Goblin |
| **STALKER** | Stealth/Invisible, ambush von hinten | Backstab, Stealth-Strike, Disappear-Reappear | Shadow, Assassin |
| **ELITE / RARE** | Stronger version, 1-2 zusätzliche Affixes | Random aus Affix-Pool | Goldener Champion |
| **CHAMPION / MINI-BOSS** | Quasi-Boss, eigenes Moveset, kein Pack | 3-4 Eigene Attacken | Pack-Leader |
| **GUARDIAN / SHIELD** | Blockt Hits in Richtung Schild, Schild zerstörbar | Schildwall mit Pack, Bash-Counter | Knight |
| **EXPLODER** | DoT-Aura, Death-Explosion | Death-Boom, Poison-Cloud-On-Death | Plague-Zombie |
| **FLYER** | Air, schwer per Melee zu treffen | Dive-Bomb, Aerial-Projectile | Bat, Wyvern-Whelp |
| **TUNNELER** | Burrowed Spawning, Hit-and-Hide | Pop-Up-Attack, Ground-Track | Sandworm |

### F.3 Affix-System (Rare/Magic-Monsters in POE-Style)

Random-Rares (gelbe Bosse aus Mob-Pack) bekommen Affixe aus Pool:

- **Flameweaver** — schießt zusätzlich Fireball-Salve
- **Frostbearer** — Aura: Player slow in 5m
- **Stormcaller** — Lightning-Strike alle 5 Sek auf Player-Pos
- **Vampiric** — heilt sich durch Hits
- **Bloodthirsty** — gewinnt Speed bei niedriger HP
- **Soul-Eater** — buffed sich bei Add-Death
- **Necromancer** — beschwört Skelette
- **Phasing** — kurze Invuln-Phasen
- **Teleporter** — teleportiert kurz vor Tod weg
- **Detonating** — explodiert bei Tod (1.5s Telegraph)

Affix-Stack: 1 Affix = magic (blau), 2-4 Affixes = rare (gelb), 5-6+ = unique (orange) Pack-Boss.

### F.4 Mob-Variety durch Affixe + Archetyp

Beispiel-Berechnung: 14 Archetypen × 10 Affixe (in versch. Kombos) = praktisch unendliche Kombinationen.

### F.5 Visuelle Identifikation

- Affix-Mobs haben **Outline-Glow** in Affix-Farbe (Blau=Magic, Gelb=Rare, Orange=Unique).
- Affix-Icons über Health-Bar.
- Distinctive Skin-Tints (z.B. Flameweaver = leicht rötlich, Frostbearer = leicht bläulich).

---

## TEIL G — UI / HUD VOLLSTÄNDIGKEIT

### G.1 Status-Quo-Problem
Manche Attacken erscheinen nicht in der Hotkey-Leiste — Spieler weiß nicht, was er drücken kann. Fix: **JEDE aktive Fähigkeit MUSS sichtbar gebunden sein.**

### G.2 Hotkey-Bar-Anforderungen (PFLICHT)

Layout (untere Mitte, ähnlich POE2):

```
[LMB]  [RMB]  [Q]  [W]  [E]  [R]  [T]  [1]  [2]  [3]  [4]  [Space=Dodge]
```

- **Standard: 10-12 Skill-Slots** (Maus + Q W E R T + 1 2 3 4).
- Jeder Slot zeigt:
  - Skill-Icon
  - Hotkey-Label
  - Cooldown-Sweep (radial)
  - Mana/Spirit/Ammo-Kosten unten klein
  - Charge-Counter (z.B. „2/3" für aufladbare Skills, Granaten)
  - Buff/Active-Status-Border (leuchtend, wenn Skill toggled-on ist)

### G.3 Auto-Bind-Regel

```
Wenn Spieler einen Skill-Gem ins Skill-Panel slottet UND noch keinen Hotkey hat:
  → Auto-bind auf nächsten freien Slot
  → UI-Notification „X wurde auf [Slot] gebunden"
```

**KEIN Skill darf existieren, ohne in der Bar zu erscheinen.** Sonst weiß der Spieler nicht, dass er ihn hat.

### G.4 Separates Buff-/Debuff-Tray

Über oder neben Player-Health-Globe:
- **Aktive Buffs** (eigene Auras, Flask-Effects, Charges): kleine Icons mit Cooldown/Duration.
- **Debuffs auf Player** (poisoned, chilled, on fire): farb-kodiert, Dauer-Anzeige.
- **Charges** (Power, Frenzy, Endurance): unter Health-Globe als kleine Orbs (POE-Style).

### G.5 Resource-Bars

- **Health-Globe** (rot, links).
- **Mana-Globe ODER Mana-Bar** (blau, rechts).
- **Energy-Shield-Layer** über Health (cyan-Overlay).
- **Spirit-Indicator** (klein, in der Nähe des Hotkey-Bars): „X / Y Spirit reserviert".
- **Stamina/Dodge-Charges** als Bar mit Tick-Segments.

### G.6 Notifications & Floating-Combat-Text

- **Floating Damage Numbers** (toggle-bar):
  - Eigener Damage: Weiß
  - Crit: Gelb mit Pop-Scale
  - DoT-Ticks: kleiner, gedeckt
  - Heilung: Grün
- **Pickup-Notifications** rechts/links Rand (Item-Drops, Currency, XP).
- **Quest-Update-Notification** oben Mitte (kurzer Fade).
- **Level-Up-Notification** dominant aber kurz (Particle-Burst hinter Charakter + UI).

### G.7 Inspector / Skill-Tooltip

Hover über Skill in Skill-Panel zeigt:
- Skill-Name, Tier, Tags (siehe Skill-Bible Teil 3.1)
- Damage-Pre-Calc mit aktuellen Stats
- Mana-Cost, Cooldown, Cast-Time
- Welche Supports gerade linked sind, mit ihren Effekten
- „Compare to currently equipped" wenn beim Wechsel hovered

---

## TEIL H — SKILLTREE-VISUELLE-IDENTITÄT (PRO KLASSE)

### H.1 Status-Quo-Problem
Skilltree sieht aus wie ein generisches Menü mit Kacheln. Fix: **Jede Klasse hat eine atmosphärisch passende Skilltree-Optik.**

### H.2 Konzept: Class-Themed Skill-Constellation

Der Skilltree ist eine **Karte / Konstellation**, nicht eine Grid-UI. Knoten verbunden mit Linien. Pan + Zoom (POE-Style). Aber:

- **Background** ist klassen-thematisch und atmosphärisch.
- **Knoten-Skin** passt zur Klasse.
- **Linien-Stil** passt zur Klasse.
- **Hover-/Allocate-VFX** passt zur Klasse.

### H.3 Per-Klasse-Mockup

#### Warrior (STR)
- **Background:** Steinplatte mit eingemeißelten Runen, Fackel-Licht von oben, leichter Rauch.
- **Knoten:** Runen-Steine, glühen orange wenn allocated.
- **Linien:** geschmiedete Eisen-Ketten, klicken/clanken bei Allocation.
- **Keystone-Nodes:** große, in Stein gefräste Symbole mit Lava-Kern.
- **Sound:** Hammerschlag bei Allocation, Amboss-Klingen.

#### Witch (INT)
- **Background:** Schwarzer Marmor mit Filigran-Goldlinien (Decay-Patina), Spinnweben, Kerzenflackern.
- **Knoten:** Schädel-Cameos, Knochen-Kreise, Augen-Symbole.
- **Linien:** Wurzelartige Knochen-Tendrils, wachsen visuell bei Allocation.
- **Keystone-Nodes:** Blutige Pentagramme oder Auge-des-Schicksals-Motive.
- **Sound:** Flüstern, Knochen-Knacken, Glas-Tinkle.

#### Sorceress (INT)
- **Background:** Stained-Glass-Fenster mit Element-Mandala, Lichtschein.
- **Knoten:** Edelsteine in Element-Farben (Rubin, Saphir, Topas).
- **Linien:** Energie-Schimmer, animiert pulsierend.
- **Keystone-Nodes:** Großer Element-Stein mit Aura-Glow.
- **Sound:** Hoher Chime, Energie-Sweep.

#### Ranger (DEX)
- **Background:** Waldboden, Blätter, Sonnenstrahlen durch Baumkronen.
- **Knoten:** Holz-Embleme, Blattmotive, Pfeilspitzen.
- **Linien:** Ranken & Wurzeln, organisch verzweigt.
- **Keystone-Nodes:** Geschnitzter Baum-Anker, leuchtet grün.
- **Sound:** Holz-Knacken, Wind-Rauschen, Vogel-Ruf.

#### Monk (DEX/INT)
- **Background:** Lotus-Mandala-Hintergrund, Tinte-auf-Papier-Aesthetik, Schwarz-Weiß-Kontrast.
- **Knoten:** Kalligraphie-Symbole, Mudra-Hände.
- **Linien:** Tinte-Striche, animiert beim Allocate (zeichnet sich entlang).
- **Keystone-Nodes:** Großer Kanji-Stempel.
- **Sound:** Pinselstrich, Glocke, Zen-Klangschale.

#### Druid (STR/INT)
- **Background:** Großer „Weltbaum" mit Wurzelsystem, Tierfellen, Sterneneinblick.
- **Knoten:** Tiergeister (Bär, Wolf, Wyvern als Reliefs).
- **Linien:** Wurzeln, leuchten grün wenn aktiviert.
- **Keystone-Nodes:** Vollständige Tier-Totems, animiert (Bär brüllt bei Allocate).
- **Sound:** Erdrumpeln, Tier-Geräusche, Wind.

#### Huntress (DEX)
- **Background:** Wüstenstein-Relief mit Speer-Wandbildern (Amazonen-Theme).
- **Knoten:** Speerspitzen, Federn, Mond-Glyphen.
- **Linien:** Lederriemen-/Sehnen-Look.
- **Keystone-Nodes:** Großer Speer mit Banner.
- **Sound:** Speer-Vibration, Trommel.

#### Mercenary (STR/DEX)
- **Background:** Industrielles Eisen-Gitter, Zahnräder im Hintergrund, Schwarzpulver-Rauch.
- **Knoten:** Munitions-Kartuschen, Zahnräder, Granaten-Pin.
- **Linien:** Drähte/Lunten, Funken bei Allocation.
- **Keystone-Nodes:** Großes Zahnrad-Symbol, dreht sich.
- **Sound:** Klick eines Reload-Mechanismus, Funken-Sprühen.

### H.4 Node-State-Visualisierung

Jeder Knoten hat 4 visuelle Zustände:

1. **Locked** (kein Pfad führt hin): grau, dunkel, vielleicht halb-transparent.
2. **Available** (anliegender Knoten allocated): hell, pulsierend leicht.
3. **Allocated**: voll farbig, klassen-spezifischer Glow.
4. **Masterworked / Special** (z.B. Keystone): zusätzlicher unique-Glow.

### H.5 Allocation-Animation (KRITISCH FÜR „PUNCH")

Wenn Spieler einen Punkt setzt:
1. **0.1s:** Cursor-Click-Sound + leichter UI-Sound.
2. **0.1-0.4s:** Knoten lädt sich auf (Particle-Burst, Klassen-spezifisch).
3. **0.4-0.6s:** Verbindungs-Linie animiert sich (z.B. Druid-Wurzel wächst rein, Mercenary-Funkenkette zündet).
4. **0.5s:** Sound-Cue für Klasse (Hammerschlag Warrior, Pinsel Monk).
5. **0.6s+:** Knoten in Allocated-State, leicht pulsierend.

### H.6 Pfad-Vorschau (Quality-of-Life)

- Hover über entfernten Knoten → zeigt **gepunkteten Pfad** vom aktuell allocateten Tree-Ende zu diesem Knoten.
- Zeigt Anzahl Punkte, die nötig wären.
- Klick auf entfernten Knoten → öffnet „Plan Path"-Mode, der die Allocation-Reihenfolge schon mal visualisiert (ohne tatsächliche Allokation).

### H.7 Search & Filter

- Suchfeld oben: „Bleed", „Cold Damage", „Spirit" — passende Knoten highlighten, andere fadeen aus.
- Filter-Tags: „Show all Defense", „Show all Crit Nodes" etc.

### H.8 Camera / Pan / Zoom

- Smooth-Damped Pan (kein Snap).
- Zoom mit Mouse-Wheel, 3-4 Zoom-Stufen.
- „Center on Allocated" Button (zentriert Camera auf zuletzt gesetzten Knoten).
- „Reset View" Button.

### H.9 Respec-Mechanik

- Refund-Currency (z.B. „Orb of Regret" wie POE) oder Limited-Free-Respecs early.
- Visualisierung: Beim Refund spielt Reverse-Allocation-Animation (Funken werden in Knoten zurückgezogen, Linie de-animiert sich).

---

## TEIL I — INTEGRATION & PRIORISIERUNG FÜR CLAUDE CODE

### I.1 Implementierungs-Reihenfolge

Wenn dir die Zeit knapp wird, in dieser Reihenfolge umsetzen:

1. **AoE-Telegraph-System** (Teil C) — größter Impact aufs Gameplay, fixt „ich sterbe ohne zu wissen warum".
2. **Hotkey-Bar-Vollständigkeit** (Teil G) — niedriger Aufwand, hoher UX-Win.
3. **Monster-KI mit Sichtfeld** (Teil D) — immersionskritisch.
4. **Boss-Spawn-on-Trigger + Intro-Cinematics** (Teil E) — Event-Feeling.
5. **Death-Animation + Respawn-Cinematic** (Teil A) — emotionaler Punch.
6. **Minimap-Polish** (Teil B) — QoL-Foundation.
7. **Monster-Archetypen mit Signature-Mechaniken** (Teil F) — Content-Variety.
8. **Skilltree-Visuelle-Identität** (Teil H) — größter Aufwand, daher zuletzt, aber „Wow-Factor" für Reviews.

### I.2 Globale Code-Patterns

- **Event-Bus** für: `OnPlayerDied`, `OnBossSpawned`, `OnAoESpawned`, `OnPlayerEnteredArea`. Lose Kopplung.
- **Data-Driven** für: Boss-Definitions, Monster-Archetypes, Skill-Tree-Layouts, Death-Quotes, Affixes. Designer/Modder-Friendly.
- **Behavior-Tree-Asset** pro Archetyp, gesharte Subtrees für gemeinsames Verhalten (Patrol, Sight-Check).
- **Cinematic-Sequence-System** mit Timeline (Unity Timeline / UE Sequencer-ähnlich). Boss-Intros, Death-Transitions, Wake-Ups als Sequences.
- **PostProcess-Volume-Stack** mit eigenen Material-Instances für Damage-Type-Transitions.

### I.3 Test-Checkliste pro Feature

Bevor ein Feature „done" ist:

- [ ] Funktioniert mit allen Klassen?
- [ ] Funktioniert in Co-Op (Sync-State)?
- [ ] Skippbar / Toggleable (Accessibility)?
- [ ] Performance-Test mit 6 Spielern + 50 Mobs?
- [ ] Audio in 3D-Position + 2D-Layer korrekt?
- [ ] UI lesbar bei 1080p / 1440p / 4K / Ultrawide?
- [ ] Controller-Support (wenn relevant)?
- [ ] Localization-Strings extrahiert?

---

## ABSCHLUSS

Diese Erweiterung adressiert die kritischen UX-/Gameplay-Lücken, die in der Praxis darüber entscheiden, ob das Spiel sich **gut anfühlt** oder nicht. Skill-Anzahl und Build-Komplexität sind die Hardware — diese Systeme hier sind das Betriebssystem.

**Goldene Regel:** Der Spieler darf NIE sterben, ohne zu verstehen warum. Er darf NIE einen Boss-Raum betreten, ohne dass der Boss ein Event ist. Er darf NIE einen Skill besitzen, der nicht in der Bar liegt. Er darf NIE ein Menü öffnen, das wie ein Excel-Sheet aussieht.

*Verwende dieses Dokument zusammen mit `POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md` als kombinierten Briefing-Stack.*
