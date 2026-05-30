"""Globale Konstanten — Farben, Bildschirm, Tuning."""

SCREEN_W, SCREEN_H = 1920, 1080
FPS = 60

# ---- Farben ----
BG          = (10, 8, 6)
GOLD        = (212, 175, 55)
GOLD_BRIGHT = (244, 207, 87)
BLOOD       = (139, 26, 26)
BLOOD_LIGHT = (201, 42, 42)
MANA        = (74, 139, 203)
FIRE        = (255, 138, 58)
FROST       = (138, 200, 255)
POISON      = (138, 232, 90)
TEXT        = (200, 184, 136)
TEXT_DIM    = (120, 104, 88)
WHITE       = (255, 255, 255)
BLACK       = (0, 0, 0)

# ---- Rarity-Farben ----
RARITY_COLOR = {
    'common': (180, 180, 180),
    'magic':  (90, 140, 240),
    'rare':   (240, 220, 90),
    'unique': (230, 120, 50),
}
RARITY_NAME = {
    'common': 'Gewöhnlich',
    'magic':  'Magisch',
    'rare':   'Selten',
    'unique': 'Einzigartig',
}
RARITY_WEIGHTS = {  # Drop-Gewichte
    'common': 70,
    'magic':  22,
    'rare':   7,
    'unique': 1,
}

# ---- Item-Slots ----
SLOTS = ['weapon', 'helmet', 'chest', 'ring', 'amulet', 'offhand']
SLOT_NAME = {
    'weapon': 'Waffe',
    'helmet': 'Helm',
    'chest':  'Rüstung',
    'ring':   'Ring',
    'amulet': 'Amulett',
    # K-09 (Update #69): Crossbow-Offhand-Attachment.  Slot für Rogue-
    # Crossbow-Builds — trägt Skill-Gem-Sockels (statt Quiver).  Werden
    # nur von Rogue/Huntress equipt; andere Klassen sehen Slot als
    # „Talisman" oder leer.
    'offhand': 'Offhand',
}

# ---- Affix-Definitionen ----
# Format: key -> (label, min, max, applicable_slots)
AFFIXES = {
    'dmg_flat':    ('+{v} Schaden',                  3, 12,  ['weapon']),
    'dmg_pct':     ('+{v}% Schaden',                 5, 25,  ['weapon', 'ring', 'amulet', 'offhand']),
    'hp':          ('+{v} Leben',                    8, 35,  ['helmet', 'chest', 'ring', 'amulet']),
    'mp':          ('+{v} Mana',                     5, 20,  ['helmet', 'chest', 'amulet']),
    'hp_regen':    ('+{v:.1f} Leben/s',              0.5, 3.0, ['chest', 'amulet']),
    'mp_regen':    ('+{v:.1f} Mana/s',               1.0, 5.0, ['helmet', 'amulet']),
    'crit_chance': ('+{v}% Kritisch',                3, 12,  ['weapon', 'ring', 'amulet']),
    'crit_dmg':    ('+{v}% Krit-Schaden',           10, 50,  ['weapon', 'amulet']),
    'speed':       ('+{v}% Tempo',                   3, 12,  ['chest']),
    'cdr':         ('-{v}% Skill-Abklingzeit',       5, 20,  ['helmet', 'amulet', 'ring', 'offhand']),
    'fire_dmg':    ('+{v}% Feuerschaden',           10, 35,  ['weapon', 'ring']),
    'cold_dmg':    ('+{v}% Frostschaden',           10, 35,  ['weapon', 'ring']),
    'lit_dmg':     ('+{v}% Blitzschaden',           10, 35,  ['weapon', 'ring']),
    'dodge_cdr':   ('-{v}% Ausweich-Abklingzeit',    8, 25,  ['chest', 'ring']),
    'thorns':      ('+{v} Dornen',                   2, 10,  ['chest']),
    # B-05 (Update #50): Light-Radius — Cells/Frame mehr Fog-of-War-Reveal
    'light_radius': ('+{v} Sichtweite',              1, 3,   ['helmet', 'amulet']),
    # Update #159 (WELT_AUFBAU 5.4): Aspekt-Affixes.  7 Lore-getreue
    # Item-Affixes mit Aspekt-Tags.  Engine-Effekt: fold-in zu der
    # zugehörigen Base-Affix-Spalte (siehe items.aggregate_stats),
    # damit kein neuer Engine-Pfad gebaut werden muss.  Lore-Anker:
    # VELGRAD_LORE_BIBEL Teil 2 (Sieben Aspekte).
    'kharns_form':     ('+{v}% Kharns Form',           8, 30,  ['weapon', 'chest', 'helmet']),
    'nheyras_zeit':    ('-{v}% Nheyras Zeit',          4, 15,  ['helmet', 'amulet']),
    'ousens_blick':    ('+{v}% Ousens Blick',         12, 50,  ['weapon', 'amulet']),
    'valsas_wille':    ('+{v}% Valsas Wille',         10, 30,  ['weapon', 'ring']),
    'imnesh_sprache':  ('+{v}% Im-Neshs Sprache',     10, 30,  ['weapon', 'ring']),
    'shulavh_faden':   ('+{v} Shulavhs Faden',         3, 12,  ['chest', 'offhand']),
    'siebter_atem':    ('+{v:.1f} Siebter Atem',     0.5, 3.0, ['amulet']),
}
# Welche Affixe sind float-werte?
FLOAT_AFFIXES = {'hp_regen', 'mp_regen', 'siebter_atem'}

# Update #159: Aspekt-Affix-Keys (für Tag-Filter / Mahnmal-Pakt-Logic)
ASPEKT_AFFIX_KEYS = (
    'kharns_form', 'nheyras_zeit', 'ousens_blick', 'valsas_wille',
    'imnesh_sprache', 'shulavh_faden', 'siebter_atem',
)
# Mapping Aspekt-Affix → zugehörige Engine-Stat (für aggregate_stats-Fold)
ASPEKT_AFFIX_FOLD = {
    'kharns_form':    'dmg_pct',
    'nheyras_zeit':   'cdr',
    'ousens_blick':   'crit_dmg',
    'valsas_wille':   'fire_dmg',
    'imnesh_sprache': 'lit_dmg',
    'shulavh_faden':  'thorns',
    'siebter_atem':   'mp_regen',
}

# ---- Klassen-Definitionen ----
CLASSES = {
    # 8 Velgrad-Lore-Klassen (Lore-Bibel Teil 7). 5 davon teilen Sprites
    # mit den 3 Base-Klassen (`sprite_proxy`-Feld) — Engine-Side bleibt
    # kompakt, Lore-Side ist voll repräsentiert.
    'warrior': dict(
        name='Krieger', color=(190, 60, 60),
        hp=120, mp=30, hp_regen=2.0, mp_regen=4.0,
        damage=18, speed=210,
        strength=5, intellect=1, dexterity=2,
        desc='Eisenwächter. Robust, harter Nahkampf, wenig Mana.',
        skills=('melee', 'fireball', 'heal', 'dodge'),
        sprite_proxy='warrior',
        weapon='Mace',
    ),
    'monk': dict(
        name='Mönch', color=(220, 200, 130),
        hp=90, mp=50, hp_regen=1.5, mp_regen=8.0,
        damage=15, speed=240,
        strength=2, intellect=3, dexterity=5,
        desc='Stille Schritte. Quarterstaff-Combo, Power-Charges.',
        skills=('melee', 'lightning', 'frostnova', 'dodge'),
        sprite_proxy='warrior',  # vorerst Warrior-Sprite
        weapon='Quarterstaff',
    ),
    'mage': dict(
        name='Magier', color=(80, 100, 220),
        hp=70, mp=80, hp_regen=1.0, mp_regen=12.0,
        damage=10, speed=200,
        strength=1, intellect=6, dexterity=1,
        desc='Funkengeborene. Hoher Zauberschaden, zerbrechlich.',
        skills=('melee', 'fireball', 'lightning', 'frostnova'),
        sprite_proxy='mage',
        weapon='Wand',
    ),
    'witch': dict(
        name='Hexe', color=(120, 60, 160),
        hp=75, mp=85, hp_regen=1.0, mp_regen=14.0,
        damage=11, speed=195,
        strength=1, intellect=7, dexterity=1,
        desc='Knochenwitwen. Minions, Curses, Chaos/Bone-Spells.',
        skills=('melee', 'fireball', 'bone_spear', 'frostnova'),
        sprite_proxy='mage',
        weapon='Dagger',
    ),
    'ranger': dict(
        name='Jägerin', color=(110, 180, 100),
        hp=85, mp=55, hp_regen=1.5, mp_regen=9.0,
        damage=14, speed=250,
        strength=2, intellect=2, dexterity=6,
        desc='Saatträgerin. Bow, Multi-Projektile, Crits.',
        skills=('melee', 'fireball', 'lightning', 'dodge'),
        sprite_proxy='rogue',
        weapon='Bow',
    ),
    'rogue': dict(
        name='Söldner', color=(80, 200, 130),
        hp=85, mp=50, hp_regen=1.5, mp_regen=8.0,
        damage=14, speed=255,
        strength=2, intellect=2, dexterity=6,
        desc='Mahnmal-Gilde. Crossbow + Grenaden, WASD-Combat.',
        skills=('melee', 'fireball', 'lightning', 'dodge'),
        sprite_proxy='rogue',
        weapon='Crossbow',
    ),
    'huntress': dict(
        name='Speerschwester', color=(220, 160, 80),
        hp=95, mp=45, hp_regen=1.5, mp_regen=7.0,
        damage=16, speed=235,
        strength=3, intellect=2, dexterity=5,
        desc='Zhar-Eth-Schwester. Spear-Tänzerin, Bleed/Wind.',
        skills=('melee', 'fireball', 'lightning', 'dodge'),
        sprite_proxy='rogue',
        weapon='Spear',
    ),
    'druid': dict(
        name='Wandelnde', color=(140, 110, 60),
        hp=105, mp=60, hp_regen=2.5, mp_regen=9.0,
        damage=15, speed=215,
        strength=4, intellect=3, dexterity=3,
        desc='Drei-Tiere-Lineage. Bär/Wolf/Wyvern-Formen, Wetter.',
        skills=('melee', 'fireball', 'heal', 'dodge'),
        sprite_proxy='warrior',
        weapon='Talisman',
    ),
}

# ---- Skill-Tree-Knoten (Universal) ----
TREE_NODES = {
    'vit':       dict(name='Vitalität',    max=5, hp=15,           desc='+15 max. Leben pro Stufe'),
    'arc':       dict(name='Arkanum',      max=5, mp=8,            desc='+8 max. Mana pro Stufe'),
    'pow':       dict(name='Kraft',        max=5, dmg_pct=0.08,    desc='+8% Gesamtschaden pro Stufe'),
    'prc':       dict(name='Präzision',    max=5, crit=0.03,       desc='+3% Krit-Chance pro Stufe'),
    'agi':       dict(name='Behendigkeit', max=5, speed=0.05,      desc='+5% Bewegungstempo pro Stufe'),
    'cnc':       dict(name='Konzentration',max=5, cdr=0.05,        desc='-5% Skill-Abklingzeit pro Stufe'),
    'wis':       dict(name='Weisheit',     max=5, xp_bonus=0.05,   desc='+5% Erfahrungsgewinn pro Stufe'),
    'rich':      dict(name='Reichtum',     max=5, gold_bonus=0.10, desc='+10% Gold-Drop pro Stufe'),
    'crit_dmg':  dict(name='Hinterhalt',   max=5, crit_dmg=0.15,   desc='+15% Krit-Schaden pro Stufe'),
    'magnet':    dict(name='Magnetismus',  max=3, magnet=30,       desc='+30 Loot-Magnet-Radius pro Stufe'),
    'res':       dict(name='Widerstand',   max=5, dmg_red=0.04,    desc='-4% erlittener Schaden pro Stufe'),
    'regen':     dict(name='Regeneration', max=5, hp_regen=0.5,    desc='+0.5 HP/s Regeneration pro Stufe'),
}

# ---- Status-Effekte ----
STATUS_EFFECTS = {
    'burn':    dict(label='Brennen',    color=FIRE,   tick=0.5,  max_stacks=10, dmg_per_tick=2.0,  duration=4.0),
    'poison':  dict(label='Gift',       color=POISON, tick=0.6,  max_stacks=15, dmg_per_tick=1.4,  duration=7.0),
    'frost':   dict(label='Frost',      color=FROST,  tick=1.0,  max_stacks=5,  dmg_per_tick=0.0,  duration=3.0,
                    slow=0.6),
    'bleed':   dict(label='Bluten',     color=(220, 50, 50), tick=0.4, max_stacks=8, dmg_per_tick=2.5, duration=5.0),
    'shock':   dict(label='Schock',     color=(180, 200, 255), tick=0.3, max_stacks=4, dmg_per_tick=3.0, duration=2.0),
    # ---- Neue POE2-Ailments ----
    'chill':   dict(label='Kaelte',     color=(140, 200, 240), tick=1.0, max_stacks=3,
                    dmg_per_tick=0.0, duration=2.5, slow=0.35),
    'brittle': dict(label='Sproede',    color=(200, 230, 255), tick=1.0, max_stacks=3,
                    dmg_per_tick=0.0, duration=4.0, crit_taken_bonus=0.10),
    'sapped':  dict(label='Ausgelaugt', color=(180, 180, 200), tick=1.0, max_stacks=3,
                    dmg_per_tick=0.0, duration=4.0, dmg_dealt_mult=0.85),
    # ---- L-05 / L-06 (Update #47) ----
    # Armour-Break: reduziert Physical-Resist um stacks * armour_break_per_stack
    'armour_break': dict(label='Panzer-Bruch', color=(180, 150, 100),
                         tick=1.0, max_stacks=5, dmg_per_tick=0.0,
                         duration=4.0, armour_break_per_stack=0.10),
    # Pinned: vollständige Bewegungssperre für duration (kein Slow-Stack mehr,
    # echter Movement-Lock). Wird ausgelöst wenn frost/chill stacks ≥ 5.
    'pinned': dict(label='Festgepinnt', color=(140, 200, 240),
                   tick=1.0, max_stacks=1, dmg_per_tick=0.0,
                   duration=1.5, movement_lock=True),
    # ---- L-02 (Update #96): Physical-Ailments Maim + Crush ----
    # Maim: Bewegungs-Verlangsamung als Phys-Ailment (Sehnen-Schnitt).
    # Crush: kurzzeitiger Defense-Break, jeder Hit auf Crushed nimmt +25 % Dmg.
    'maim':   dict(label='Verkrüppelt', color=(180, 50, 50), tick=1.0,
                   max_stacks=4, dmg_per_tick=0.0, duration=4.0, slow=0.30),
    'crush':  dict(label='Zerschmettert', color=(200, 130, 80), tick=1.0,
                   max_stacks=3, dmg_per_tick=0.0, duration=3.0,
                   dmg_taken_bonus=0.25),
}

# Element-Combos: wenn (a, b) gleichzeitig wirken → Detonation mit Spezial-Effekt
# Reihenfolge sortiert (alphabetisch von Effekt-Key)
ELEMENT_COMBOS = {
    ('burn', 'frost'):   dict(name='Splitter',   color=(220, 240, 255), dmg_mult=3.5, radius=80,
                              desc='Splitterung: 3.5x Schaden, AoE Frost'),
    ('burn', 'poison'):  dict(name='Toxische Detonation', color=(255, 180, 100), dmg_mult=2.5, radius=110,
                              desc='Toxische Detonation: 2.5x Schaden im Umkreis'),
    ('bleed', 'poison'): dict(name='Verwesung',  color=(150, 100, 60), dmg_mult=2.0, radius=60,
                              desc='Verwesung: 2x Schaden + +5 Bluten-Stacks'),
    ('frost', 'shock'):  dict(name='Sturmblitz', color=(200, 220, 255), dmg_mult=2.8, radius=90,
                              desc='Sturmblitz: 2.8x Schaden, kettet zu Nachbarn'),
    ('burn', 'shock'):   dict(name='Plasma',     color=(255, 200, 255), dmg_mult=3.0, radius=100,
                              desc='Plasma: 3x Schaden, AoE Schock'),
    ('bleed', 'shock'):  dict(name='Krampf',     color=(255, 100, 150), dmg_mult=2.2, radius=70,
                              desc='Krampf: 2.2x Schaden, kurzer Stun'),
}


# ---- Skill-Runen ----
# Format: skill_key -> list of runes
# Rune-Effekt-Keys werden in skills.py interpretiert.
RUNES = {
    'fireball': [
        dict(id='fb_split',     name='Spaltung',          desc='Feuerball spaltet sich beim Aufprall in 3 kleinere Sprengsätze.'),
        dict(id='fb_burn',      name='Sengende Flamme',   desc='Treffer entzünden Gegner (Brennen-Effekt).'),
        dict(id='fb_giant',     name='Lavabombe',         desc='+80% AoE-Radius, +40% Schaden, -30% Tempo.'),
        dict(id='fb_volley',    name='Salve',             desc='Wirft 3 Feuerbälle im Fächer.'),
    ],
    'lightning': [
        dict(id='lt_chains',    name='Verzweigung',       desc='Springt zu bis zu 6 Gegnern statt 3.'),
        dict(id='lt_shock',     name='Statische Ladung',  desc='Jeder Treffer fügt Schock-Stacks zu.'),
        dict(id='lt_arc',       name='Lichtbogen',        desc='Verursacht +60% Schaden beim ersten Ziel.'),
        dict(id='lt_thunder',   name='Donnerschlag',      desc='Auslöser eines Blitz-Stuns + Bildschirmschütteln.'),
    ],
    'heal': [
        dict(id='hl_shield',    name='Schutzmantel',      desc='Heilt nicht, sondern gibt 60% max-HP als Schild.'),
        dict(id='hl_vampire',   name='Blutbund',          desc='Die nächsten 4 Treffer heilen für 30% Schaden.'),
        dict(id='hl_nova',      name='Helle Nova',        desc='Heilung verursacht zusätzlich AoE-Schaden.'),
        dict(id='hl_regen',     name='Anhaltend',         desc='Heilt über 4s statt sofort, aber +40% gesamt.'),
    ],
    'frostnova': [
        dict(id='fn_frost',     name='Eis-Echo',          desc='Wendet Frost-Stacks an statt nur zu verlangsamen.'),
        dict(id='fn_wall',      name='Eismauer',          desc='Verlangsamte Gegner erleiden +50% Schaden.'),
        dict(id='fn_wide',      name='Ausdehnung',        desc='+60% Radius.'),
        dict(id='fn_shatter',   name='Kristallbruch',     desc='+80% Schaden und Splitter (Combo-Trigger).'),
    ],
}


# ---- Set-Items ----
ITEM_SETS = {
    'dragon': dict(
        name='Drachen-Set', color=(220, 80, 60),
        bonuses={
            2: ('fire_dmg', 25),  # +25% Feuerschaden
            3: ('fire_dmg', 60),  # +60% Feuerschaden
            4: ('fire_dmg', 100),
        },
    ),
    'frost': dict(
        name='Frost-Set', color=(120, 200, 240),
        bonuses={
            2: ('cold_dmg', 25),
            3: ('cold_dmg', 60),
            4: ('cold_dmg', 100),
        },
    ),
    'shadow': dict(
        name='Schatten-Set', color=(180, 100, 220),
        bonuses={
            2: ('crit_chance', 10),
            3: ('crit_chance', 25),
            4: ('crit_dmg', 80),
        },
    ),
}


# ---- Edelsteine ----
# Werden in Sockel von Items eingesetzt.
GEM_TYPES = {
    'ruby':     dict(name='Rubin',     color=(220, 60, 60),   affix='dmg_pct',     value=8,  desc='+8% Schaden'),
    'sapphire': dict(name='Saphir',    color=(60, 100, 220),  affix='mp',          value=15, desc='+15 Mana'),
    'emerald':  dict(name='Smaragd',   color=(60, 200, 100),  affix='speed',       value=6,  desc='+6% Tempo'),
    'topaz':    dict(name='Topas',     color=(240, 220, 80),  affix='crit_chance', value=5,  desc='+5% Krit'),
    'amethyst': dict(name='Amethyst',  color=(180, 100, 240), affix='hp',          value=20, desc='+20 Leben'),
    'opal':     dict(name='Opal',      color=(220, 230, 255), affix='cdr',         value=6,  desc='-6% Abklingzeit'),
}

# ---- Crafting-Kosten ----
CRAFT_COSTS = {
    'upgrade': dict(gold=80, per_ilvl=40),
    'reroll':  dict(gold=120),
    'socket':  dict(gold=60),
}

# ---- Schadensarten ----
DAMAGE_TYPES = {
    'physical': dict(label='Physisch', color=(220, 220, 200)),
    'fire':     dict(label='Feuer',    color=FIRE),
    'cold':     dict(label='Frost',    color=FROST),
    'lightning':dict(label='Blitz',    color=(180, 200, 255)),
    'poison':   dict(label='Gift',     color=POISON),
}

# Welche Schadensart hat welcher Skill?
SKILL_DAMAGE_TYPE = {
    'melee':     'physical',
    'fireball':  'fire',
    'lightning': 'lightning',
    'heal':      'physical',     # nur für hl_nova
    'frostnova': 'cold',
}

# ---- Auren (Klassen-Pässive, reservieren % max Mana) ----
AURAS = {
    'wachsamkeit': dict(
        name='Wachsamkeit', class_=['warrior'], reserve=0.30,
        desc='+30% Leben, +20% Schaden-Reduktion',
        bonuses=dict(hp_mult=1.30, dmg_taken_mult=0.80),
    ),
    'macht': dict(
        name='Macht der Arkana', class_=['mage'], reserve=0.40,
        desc='+40% Zauberschaden (Feuer/Frost/Blitz)',
        bonuses=dict(spell_dmg_mult=1.40),
    ),
    'praezision': dict(
        name='Präzision', class_=['rogue'], reserve=0.25,
        desc='+25% Krit-Chance, +50% Krit-Schaden',
        bonuses=dict(crit_bonus=0.25, crit_dmg_bonus=0.50),
    ),
    'entschlossenheit': dict(
        name='Entschlossenheit', class_=['warrior', 'mage', 'rogue'], reserve=0.20,
        desc='+15% Bewegungstempo, +20% Manaregen',
        bonuses=dict(speed_mult=1.15, mp_regen_mult=1.20),
    ),
}

# ---- Klassen-spezifische Talentbaum-Knoten ----
CLASS_TREE_NODES = {
    'warrior': {
        'iron_skin':   dict(name='Eisenhaut',      max=3, hp_pct=0.10,     desc='+10% max. Leben pro Stufe'),
        'cleave':      dict(name='Spaltung',       max=3, cleave=0.20,     desc='Nahkampf-Hits treffen Nachbarn 20/40/60%'),
        'taunt':       dict(name='Provokation',    max=3, thorns=5,        desc='+5 Dornen-Schaden pro Stufe'),
        'rage':        dict(name='Berserker-Wut',  max=5, dmg_low_hp=0.06, desc='Bei <50% HP: +6% Schaden pro Stufe'),
        'titan':       dict(name='Titan',          max=5, hp_pct=0.06,     desc='+6% max. Leben pro Stufe'),
        'fortitude':   dict(name='Standfest',      max=5, dmg_red=0.03,    desc='-3% Schaden erhalten pro Stufe'),
        'whirlwind':   dict(name='Wirbel-Affinitaet', max=3, ult_cdr=0.08, desc='-8% Ultimate-CD pro Stufe'),
        'last_stand':  dict(name='Letzter Stand',  max=3, last_stand=0.20, desc='Bei <20% HP: +20% Schaden + 20% Tempo'),
    },
    'mage': {
        'elem_mastery':dict(name='Element-Meisterschaft', max=5, elem_dmg=0.06, desc='+6% Element-Schaden pro Stufe'),
        'mana_shield': dict(name='Manaschild',     max=3, mp_to_hp=0.15,   desc='15/30/45% Schaden trifft Mana statt HP'),
        'arcane_orb':  dict(name='Arkanstrom',     max=3, free_cast=0.10,  desc='+10% Chance auf Gratis-Cast pro Stufe'),
        'overload':    dict(name='Ueberladung',    max=5, crit_spell=0.04, desc='+4% Krit-Schaden f. Zauber pro Stufe'),
        'arcane_pool': dict(name='Arkanpool',      max=5, arc_mp=10,       desc='+10 max. Mana pro Stufe'),
        'fast_cast':   dict(name='Schnellzauber',  max=5, cdr=0.03,        desc='-3% Skill-Abklingzeit pro Stufe'),
        'echo':        dict(name='Echo',           max=3, echo_chance=0.05,desc='5/10/15% Chance Skill wird wiederholt'),
        'mana_regen':  dict(name='Manaflut',       max=5, mp_regen=1.0,    desc='+1 Mana/s Regeneration pro Stufe'),
    },
    'rogue': {
        'evasion':     dict(name='Ausweichen',     max=5, dodge_chance=0.04, desc='+4% Ausweichen pro Stufe'),
        'poison':      dict(name='Giftklingen',    max=3, poison_chance=0.20, desc='20/40/60% Chance Gift auf Treffer'),
        'shadow':      dict(name='Schattenschritt',max=3, dodge_cdr=0.15,  desc='-15% Ausweich-CD pro Stufe'),
        'backstab':    dict(name='Hinterhalt',     max=5, crit_dmg=0.10,   desc='+10% Krit-Schaden pro Stufe'),
        'venom_stack': dict(name='Schlangengift',  max=5, poison_extra=1,  desc='+1 Gift-Stack pro Anwendung'),
        'speed_demon': dict(name='Schnellfuss',    max=5, speed=0.04,      desc='+4% Tempo pro Stufe'),
        'twin_strike': dict(name='Doppelstich',    max=3, twin=0.10,       desc='10/20/30% Chance doppelten Hit'),
        'crit_streak': dict(name='Krit-Serie',     max=5, crit=0.02,       desc='+2% Krit pro Stufe'),
    },
}

# ---- Skill-Levels (PoE-artig) ----
SKILL_XP_PER_LEVEL = [
    30, 60, 100, 150, 220, 320, 460, 640, 880, 1200,
    1600, 2100, 2700, 3500, 4500, 5800, 7400, 9400, 12000, 15500,
]
SKILL_LEVEL_MAX = 20
SKILL_DMG_PER_LEVEL = 0.05  # +5% Skill-Schaden pro Skill-Level

# ---- Dungeon-Definitionen ----
# Update #43: Größere Dungeons (User „größere Dungeons sind sehr wichtig")
# enemy_count auf +45 % aufgestockt, parallel mit num_rooms-Bump in dungeon.py
DUNGEONS = {
    'crypt_lost':  dict(
        name='Krypta der Vergessenen', biome='crypt',  level_req=1,
        enemy_count=32, boss='necromancer',
        objectives=[
            ('boss',     'Besiege Mortis den Beschwörer', 200, 1),
            ('kills',    'Erschlage 20 Untote',           80,  20),
            ('elite',    'Besiege einen Elite-Gegner',    60,  1),
        ],
    ),
    'frost_palace': dict(
        # Update #183 (WELT_AUFBAU Sektion 14): User-sichtbarer Name jetzt
        # Lore-konform "Glasgoldener Palast" (Akt 2 = Glasgoldene Ruinen).
        # Engine-Key `frost_palace` bleibt bis Phase 2 (Save-Compat + 8
        # Test-Sites + outposts.py-Referenz) — Voll-Rename auf `glass_palace`
        # in Phase 2 zusammen mit dem `glass_ruins`-Biome-Buildout.
        name='Glasgoldener Palast', biome='frost', level_req=4,
        enemy_count=42, boss='frostlord',
        objectives=[
            ('boss',     'Besiege den Glasherrn',          400, 1),
            ('kills',    'Erschlage 25 Gegner',            120, 25),
            ('no_death', 'Kein Tod im Dungeon',            200, 1),
        ],
    ),
    'lava_pit':    dict(
        name='Schlund von Pyron', biome='lava',  level_req=8,
        enemy_count=48, boss='dragon',
        objectives=[
            ('boss',     'Besiege Pyron den Drachen',     700, 1),
            ('kills',    'Erschlage 30 Höllenbewohner',   180, 30),
            ('gems',     'Sammle 3 Edelsteine',           150, 3),
        ],
    ),
    'desert_temple': dict(
        # Update #115 (WELT_AUFBAU 1.2 Akt 1b): level_req 12 → 4. Der
        # Wüstentempel ist der Zhar-Eth-Speerschwester-Schauplatz und
        # gehört zum Akt-1b-Bonus-Zweig — sollte früh erreichbar sein.
        name='Wüstentempel', biome='desert', level_req=4,
        enemy_count=52, boss='shadow_lord',
        objectives=[
            ('boss',     'Besiege Nox Eternus',            900, 1),
            ('kills',    'Erschlage 35 Wüstenbewohner',    200, 35),
            ('elite',    'Besiege 2 Eliten',               220, 2),
        ],
    ),
    'swamp_ruins': dict(
        name='Sumpf-Ruinen', biome='swamp', level_req=10,
        enemy_count=44, boss='bone_knight',
        objectives=[
            ('boss',     'Besiege Sir Ossian',             650, 1),
            ('kills',    'Erschlage 28 Sumpfwesen',        160, 28),
            ('no_death', 'Kein Tod im Sumpf',              280, 1),
        ],
    ),
    'astral_realm': dict(
        name='Astral-Ebene', biome='astral', level_req=15,
        enemy_count=58, boss='shadow_lord',
        objectives=[
            ('boss',     'Besiege Nox Eternus',           1200, 1),
            ('kills',    'Erschlage 35 Astral-Wesen',     250, 35),
            ('no_death', 'Kein Tod im Astral',            400, 1),
        ],
    ),
}
