"""Velgrad-Tipps-Pool (Update #139 — Y-04).

Lore-konforme Spieltipps gespeist aus:
- VELGRAD_LORE_BIBEL.md (Aspekte, Akte, Drei Wunden)
- VELGRAD_VOICE_LINES_POOL.md (NPC-Sprüche)
- POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md (Skill-Mechaniken)
- VELGRAD_AUDIO_DESIGN_BIBEL.md (Snapshot-System)

Tipps werden im Loading-Screen (X-11) + optional als Loading-Toast
rotiert.  Pro Tip eine `category` damit der Loading-Screen
themen-passende Tipps wählen kann (z.B. crypt-Loading zeigt
crypt-Tipps).

API:
    tips.pick_tip()                  — zufälliger Tip (gleichmäßig)
    tips.pick_tip_for_biome(biome)   — biome-spezifisch, fallback random
    tips.pick_tip_for_class(cls)     — klassen-spezifisch + ein paar generic
    tips.all_tips()                  — Liste aller Tipps

Format pro Tip: dict mit `text` (lore-konformer Tip), `category` (str)
und optional `class_filter` (set von Klassen-Keys) oder
`biome_filter` (set von Biome-Keys).
"""

import random as _r


# ============================================================
# TIPPS-POOL — 30+ Einträge
# ============================================================
# Kategorie-Schlüssel:
#   'combat'    — Combat-Mechanik (Ailments, Crits, Combos, Stun)
#   'gear'      — Items, Affixes, Crafting
#   'world'     — Lore + Welt-Wissen (Aspekte, Wunden, Fraktionen)
#   'skill'     — Skill-Tree + Skill-Gems
#   'audio'     — Audio-/Atmosphere-Lore
#   'survival'  — HP/Mana/Dodge/Flask-Tipps
TIPS = [
    # ---- Combat ----
    dict(text='Cold-Crits applizieren Brittle — Brittle-Stacks stacken '
              'die nächste Crit-Chance um +5 %.', category='combat'),
    dict(text='Frost-Stacks slowen den Gegner.  Bei 5 Stacks wird er '
              'PINNED (1.5 s bewegungsunfähig).', category='combat'),
    dict(text='Phys-Hits laden Stun-Build auf.  Bei 100 % ist der '
              'Gegner 1.5 s benommen — Combo-Payoff ×2.0.',
         category='combat'),
    dict(text='Burning + Fire = Splitter-Combo (×1.3).  Stack Burn '
              'zuerst, dann Fire-Skill für maximalen Payoff.',
         category='combat'),
    dict(text='Crits machen 1.5× Schaden UND applizieren Ailments '
              'zuverlässiger.  Crit-Builds skalieren mit Affix-Crits.',
         category='combat'),
    dict(text='Boss-Specials haben Telegraphs.  Wenn der Boss-Ring '
              'rot pulsiert, ist ein Schlag im Anflug — weiche aus.',
         category='combat'),
    dict(text='Knockback unterbricht Channeling-Skills bei Mobs.  '
              'Warrior-Slams resetten Caster-Wind-Ups.',
         category='combat'),
    dict(text='Pack-Members teilen `last_known_position`.  Wenn ein '
              'Mob dich sieht, weiß das ganze Pack 1.5 s später wo du bist.',
         category='combat'),
    dict(text='Pinned-Mobs können nichts mehr — keine Hits, kein Cast, '
              'keine Bewegung.  Perfekter Burst-Moment.',
         category='combat'),

    # ---- Gear / Items ----
    dict(text='Rare-Items haben 2-4 Affixes, Uniques 5-6.  Affix-Tier '
              'skaliert mit dem Item-Level beim Drop.',
         category='gear'),
    dict(text='Affixes umrollen kostet Aspekt-Splitter bei Otreth '
              'Hohlauge.  Es würfelt ALLE Random-Affixes neu — Implicit '
              'bleibt.', category='gear'),
    dict(text='Uncut Memory-Shards droppen von Bossen + Mini-Bossen.  '
              'Bringe sie zu Otreth um Skills aus dem Klassen-Pool zu '
              'gravieren.', category='gear'),
    dict(text='Light-Radius-Affixes auf Helm/Amulett geben Cells extra '
              'Minimap-Sicht.  Im Crypt-Biome lohnt sich das doppelt.',
         category='gear'),
    dict(text='Item-Compare (Shift-Hold) zeigt im Inventar die Affix-'
              'Deltas zum equipped Item.  Grün = besser, Rot = '
              'schlechter.', category='gear'),
    dict(text='Loot-Filter (L-Taste) blendet common-Items aus.  '
              'Common ab Akt 3 ist Müll — filtere sie weg.',
         category='gear'),

    # ---- World / Lore ----
    dict(text='Aithein dachte — und der Gedanke war eine Welt.  '
              'Sieben Atemzüge, sieben Aspekte: Kharn (Eisen), Nheyra '
              '(Atem), Ousen (Geist), Valsa (Flamme), Im-Nesh (Blitz), '
              'Shulavh (Faden), Der Siebte.', category='world'),
    dict(text='Brassweir ist die letzte Stadt der Mahnmal-Gilde.  '
              'Salz frisst die Mauern; jede Akt-Boss-Niederlage bröckelt '
              'einen Wall-Block.', category='world'),
    dict(text='Die Drei Wunden in Akt 6 sind keine Bosse — sie sind '
              'Aspekt-Fragmente die Aithein im Götterkrieg verlor.',
         category='world'),
    dict(text='Mahnmal-Marken I-VII sind Aspekt-Currencies.  Bringe '
              'sie zu einer Mahnmal-Stele für Pakt-Boni: Kharn=+Dmg, '
              'Nheyra=+HP, Ousen=+HP-Regen, Valsa=+Fire, …',
         category='world'),
    dict(text='Die Salzhüter-Brut wartet immer noch auf Ablösung.  '
              'Niemand kommt mehr.', category='world'),
    dict(text='Fraktionen erinnern sich.  Negative Rep mit Tribunal '
              'der Asche → Asch-Soldaten greifen dich an statt zu '
              'ignorieren.', category='world'),
    dict(text='Echo-Senatoren sind die letzten 412 von Velharn.  Sie '
              'wissen nicht dass sie schon tot sind.',
         category='world'),

    # ---- Skill / Tree ----
    dict(text='Die Mahnmal-Stele in Brassweir öffnet den Aspekt-Schrein '
              '(F).  5 Pakt-Stacks pro Aspekt maximal.',
         category='skill'),
    dict(text='Orb-of-Regret (Right-Click auf einen Skill-Knoten im '
              'Talents-Modal) refundet 1 Punkt.  Drops von Bossen '
              '(100 %), Mini-Bossen (33 %).', category='skill'),
    dict(text='Skill-Bindings sind frei konfigurierbar.  G öffnet das '
              'Skill-Menü, dort kannst du jeden Skill auf eine andere '
              'Taste legen.', category='skill'),
    dict(text='Plan-Mode (P im Talents-Modal) markiert Knoten ohne sie '
              'sofort zu kaufen.  Enter committet die geplante Sequenz.',
         category='skill'),

    # ---- Audio ----
    dict(text='Boss-Phase-Transitions ducken die Music + spielen einen '
              'Bell-Cue.  Achte auf den Sound — Phase 2/3 sind '
              'tödlicher.', category='audio'),
    dict(text='Möwen-Schwärme über Brassweir sind reine Atmosphäre.  '
              'Der Audio-Wind aus Audio-Bibel 7.7 ist Lore-konform.',
         category='audio'),
    dict(text='Stille-Zonen (Snapshot „STILLE_ZONE") senken alle Buses.  '
              'Mara die Mahnerin zieht Stille mit sich.',
         category='audio'),

    # ---- Survival ----
    dict(text='Atemzug-Phiole (F1) heilt HP UND Mana gleichzeitig.  '
              'Boss-Kills laden 5 Charges auf, Mini-Boss 3, Mob 0.5.',
         category='survival'),
    dict(text='Bei HP < 25 % pulsiert dein Globe rot.  Drücke F1 oder '
              'Leertaste zum Dodge.  Spike-Damage ist auf 65 % HP-Max '
              'gecapped.', category='survival'),
    dict(text='Dodge-Roll (Leertaste) hat 0.35 s i-Frame-Window + 2 '
              'Charges (Regen 4 s/Charge).', category='survival'),
    dict(text='Wake-Up nach Tod kostet keine Items — nur Quest-Stage-'
              'Progress kann zurückgesetzt werden.  Im Hardcore-Mode ist '
              'der Slot weg.', category='survival'),
    dict(text='HP/Mana füllen sich bei Stadt-Entry voll auf.  Auch '
              'Flask-Charges werden refresht.', category='survival'),

    # ---- Class-spezifisch (subset) ----
    dict(text='Krieger: Kharns Eisen lebt im Schlag.  Slam-Skills '
              'unterbrechen Caster + applizieren Armour-Break.',
         category='combat',
         class_filter={'warrior'}),
    dict(text='Sorceress: 7 Element-Schlüssel.  Fire+Burn = Splitter '
              'für AoE-Klassen-Spielstil.',
         category='combat',
         class_filter={'sorceress', 'mage'}),
    dict(text='Witch: Vossharils Faden bindet was schon verloren ist.  '
              'Chaos-DoTs skalieren mit Stacks, nicht mit Hit-Damage.',
         category='combat',
         class_filter={'witch'}),
    dict(text='Ranger: Nheyras Atem trägt deine Pfeile weiter.  '
              'Pierce-Affixes auf Bow lohnen sich im Pack-Combat.',
         category='combat',
         class_filter={'ranger'}),
    dict(text='Monk: Stille-Schritte halbiert deinen Noise.  Stehst du '
              'still, dropt der Noise auf 25 % — Stealth-Engagements '
              'sind dir vorbehalten.',
         category='combat',
         class_filter={'monk'}),

    # ---- Biome-spezifisch ----
    dict(text='Crypt: Salzgekreuzte bluten silbrig.  Die Salzwunde ist '
              'in Brassweir-Nähe.',
         category='world',
         biome_filter={'crypt'}),
    dict(text='Frost: Glasgolden-Türme stehen, aber sollten nicht.  '
              'Goldstaub-Diener replizieren sich wenn du wartest.',
         category='world',
         biome_filter={'frost'}),
    dict(text='Lava: Aschenfeld-Boden hinterlässt Footprints.  '
              'Tribunal der Asche jagt Im-Nesh-Berührte.',
         category='world',
         biome_filter={'lava'}),
    dict(text='Swamp: Wurzelgrab-Sporen applizieren Poison-Stacks.  '
              'Knochenwitwen verwesen langsam in Vossharils Faden.',
         category='world',
         biome_filter={'swamp'}),
    dict(text='Astral: Spiegelhof reflektiert deine Hits — der Echo-'
              'Zwilling kopiert dich 1 Sekunde später.',
         category='world',
         biome_filter={'astral'}),
]


# ============================================================
# API
# ============================================================
def all_tips():
    """Returnt alle Tipps als Liste (read-only)."""
    return list(TIPS)


def pick_tip():
    """Returnt einen zufälligen Tip aus dem gesamten Pool."""
    if not TIPS:
        return None
    return _r.choice(TIPS)


def pick_tip_for_biome(biome):
    """Returnt einen Tip der entweder zum biome passt ODER global ist.

    Fallback: wenn keine biome-spezifischen Tips matchen, irgendein
    generischer Tip.
    """
    matching = [t for t in TIPS
                if 'biome_filter' not in t
                or biome in t.get('biome_filter', ())]
    if not matching:
        return pick_tip()
    return _r.choice(matching)


def pick_tip_for_class(cls):
    """Returnt einen Tip der entweder zur Klasse passt ODER global ist.

    Fallback: irgendein generischer Tip wenn nichts klassen-spezifisch
    matched.
    """
    matching = [t for t in TIPS
                if 'class_filter' not in t
                or cls in t.get('class_filter', ())]
    if not matching:
        return pick_tip()
    return _r.choice(matching)


def pick_tip_for_context(biome=None, cls=None):
    """Picks a tip that matches BOTH biome + class (if given).
    Fallback-Chain: biome+class > class > biome > random.
    """
    if biome and cls:
        matching = [
            t for t in TIPS
            if (cls in t.get('class_filter', ()) if 'class_filter' in t
                else True)
            and (biome in t.get('biome_filter', ()) if 'biome_filter' in t
                 else True)
        ]
        if matching:
            return _r.choice(matching)
    if cls:
        return pick_tip_for_class(cls)
    if biome:
        return pick_tip_for_biome(biome)
    return pick_tip()
