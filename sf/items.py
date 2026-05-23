"""Items: Rarities, Affixe, Generierung, Stat-Aggregation."""

import random

from .constants import (
    AFFIXES, FLOAT_AFFIXES, RARITY_WEIGHTS, RARITY_NAME,
    SLOTS, SLOT_NAME,
)

# Item-Namensteile pro Slot (für etwas Flair)
SLOT_BASE_NAMES = {
    'weapon': ['Klinge', 'Hammer', 'Stab', 'Dolch', 'Schwert', 'Axt'],
    'helmet': ['Helm', 'Kapuze', 'Diadem', 'Krone'],
    'chest':  ['Rüstung', 'Robe', 'Harnisch', 'Wams'],
    'ring':   ['Ring', 'Reif', 'Band'],
    'amulet': ['Amulett', 'Anhänger', 'Talisman'],
    # K-09 (Update #69): Crossbow-Offhand-Attachments
    'offhand':['Mahnmal-Sigil', 'Mark-Talisman', 'Köcher', 'Sigil', 'Bandolier'],
}
PREFIXES = ['der Schatten', 'der Glut', 'des Frostes', 'der Wölfe',
            'des Ahnen', 'der Tiefe', 'des Sturmes', 'der Asche']
UNIQUE_NAMES = {
    'weapon': 'Schicksalsschneider',
    'helmet': 'Mondkrone',
    'chest':  'Drachenharnisch',
    'ring':   'Schattenring',
    'amulet': 'Phönixherz',
    # K-09 (Update #69): Lore-konformes Unique-Crossbow-Sigil
    'offhand': 'Letztes Klagelied',
}


class Item:
    __slots__ = ('slot', 'rarity', 'name', 'affixes', 'ilvl', 'sockets',
                 'set_id',
                 # N-08 (Update #65): Unique-Item-Audio-Override (Multiplikator
                 # für Music-Volume während Item equipped, 0.0–1.0).  Beispiel:
                 # „The Last Lament"-Crossbow mit music_mute=0.0.
                 'music_mute',
                 # Update #154 (ROADMAP T1.4): Quest-Item-Flag.  True =
                 # Item lässt sich NICHT verkaufen UND NICHT salvagen.
                 # Lore-Anker: Mahnmal-Marke VII, Tintendolch-von-Im-Nesh,
                 # Helst-Pakt-Stein u.a. — narrative Anker dürfen nicht
                 # versehentlich vernichtet werden.
                 'quest_item')

    def __init__(self, slot, rarity, name, affixes, ilvl=1, sockets=None,
                 set_id=None, music_mute=None, quest_item=False):
        self.slot = slot
        self.rarity = rarity
        self.name = name
        self.affixes = affixes  # list[(key, value)]
        self.ilvl = ilvl
        if sockets is None:
            sockets = [None] * {'common': 0, 'magic': 1, 'rare': 2, 'unique': 3}[rarity]
        self.sockets = sockets
        self.set_id = set_id  # None oder 'dragon' | 'frost' | 'shadow'
        # N-08 (Update #65): None = kein Override, sonst 0.0–1.0 als
        # Multiplikator auf Music-Volume während Item equipped.
        self.music_mute = music_mute
        self.quest_item = bool(quest_item)

    def display_lines(self):
        """Mehrzeilige Tooltip-Beschreibung."""
        from .constants import GEM_TYPES, ITEM_SETS
        lines = [(self.name, self.rarity)]
        sub_lines = f'{SLOT_NAME[self.slot]} (Stufe {self.ilvl})'
        if self.set_id and self.set_id in ITEM_SETS:
            sub_lines += f' · {ITEM_SETS[self.set_id]["name"]}'
        lines.append((sub_lines, 'dim'))
        for k, v in self.affixes:
            label, *_ = AFFIXES[k]
            if k in FLOAT_AFFIXES:
                lines.append((label.format(v=v), 'affix'))
            else:
                lines.append((label.format(v=int(v)), 'affix'))
        if self.sockets:
            socket_str = ''.join(['◆' if g else '◇' for g in self.sockets])
            lines.append((f'Sockel: {socket_str}', 'dim'))
            for gem in self.sockets:
                if gem:
                    gd = GEM_TYPES[gem]
                    lines.append((f'  ◆ {gd["name"]} – {gd["desc"]}', 'gem'))
        if self.set_id and self.set_id in ITEM_SETS:
            spec = ITEM_SETS[self.set_id]
            lines.append(('Set-Boni:', 'dim'))
            for pieces, (akey, val) in spec['bonuses'].items():
                lines.append((f'  ({pieces}P) +{val}% {AFFIXES.get(akey, [akey])[0]}',
                              'affix'))
        # Update #154 (ROADMAP T1.4): Quest-Item-Hint
        if getattr(self, 'quest_item', False):
            lines.append(
                ('Quest-Item — kann nicht verkauft oder zerlegt werden.',
                 'dim'))
        return lines

    def gem_affixes(self):
        """Returnt die Affix-Beiträge durch Edelsteine."""
        from .constants import GEM_TYPES
        out = []
        for gem in self.sockets:
            if gem:
                gd = GEM_TYPES[gem]
                out.append((gd['affix'], gd['value']))
        return out


def _roll_value(key, ilvl):
    label, lo, hi, _ = AFFIXES[key]
    # Leichter Scale mit ilvl
    scale = 1 + (ilvl - 1) * 0.08
    if key in FLOAT_AFFIXES:
        v = random.uniform(lo, hi) * scale
        return round(v * 2) / 2  # auf 0.5 runden
    v = random.uniform(lo, hi) * scale
    return max(1, int(round(v)))


def _affix_count(rarity):
    return {'common': 0, 'magic': 2, 'rare': 4, 'unique': 5}[rarity]


def roll_rarity(boost=0):
    weights = dict(RARITY_WEIGHTS)
    if boost:
        weights['magic']  += boost
        weights['rare']   += boost // 2
        weights['unique'] += max(0, boost // 6)
    total = sum(weights.values())
    r = random.uniform(0, total)
    acc = 0
    for k, w in weights.items():
        acc += w
        if r <= acc:
            return k
    return 'common'


def make_item(ilvl=1, rarity=None, slot=None, rarity_boost=0):
    if slot is None:
        slot = random.choice(SLOTS)
    if rarity is None:
        rarity = roll_rarity(boost=rarity_boost)

    # Set-Item-Chance (15% bei rare, 40% bei unique)
    set_id = None
    set_chance = {'common': 0, 'magic': 0, 'rare': 0.15, 'unique': 0.40}[rarity]
    if random.random() < set_chance:
        from .constants import ITEM_SETS
        set_id = random.choice(list(ITEM_SETS.keys()))

    if rarity == 'unique':
        name = UNIQUE_NAMES[slot]
    else:
        base = random.choice(SLOT_BASE_NAMES[slot])
        if rarity in ('rare', 'magic'):
            name = f'{base} {random.choice(PREFIXES)}'
        else:
            name = base

    if set_id:
        from .constants import ITEM_SETS
        name = f'{ITEM_SETS[set_id]["name"]}: {name}'

    pool = [k for k, spec in AFFIXES.items() if slot in spec[3]]
    n = min(_affix_count(rarity), len(pool))
    chosen = random.sample(pool, n) if n > 0 else []
    affixes = [(k, _roll_value(k, ilvl)) for k in chosen]
    return Item(slot, rarity, name, affixes, ilvl, set_id=set_id)


# ---------- Aggregation der Item-Stats für den Spieler ----------

def aggregate_stats(player):
    """Summiert alle Affixe der equipped Items + Set-Boni.

    Update #159 (WELT_AUFBAU 5.4): Aspekt-Affixes werden eingesammelt
    und in die zugehörigen Engine-Stats gefoldet (z.B. `kharns_form`
    → `dmg_pct`).  Die Aspekt-Werte bleiben ebenfalls separat im out
    Dict — für Tag-Filter (Mahnmal-Pakt W-13) + UI-Display.
    """
    from .constants import ASPEKT_AFFIX_KEYS, ASPEKT_AFFIX_FOLD
    out = {
        'dmg_flat': 0, 'dmg_pct': 0,
        'hp': 0, 'mp': 0,
        'hp_regen': 0.0, 'mp_regen': 0.0,
        'crit_chance': 0, 'crit_dmg': 0,
        'speed': 0, 'cdr': 0,
        'fire_dmg': 0, 'cold_dmg': 0, 'lit_dmg': 0,
        'dodge_cdr': 0,
        'thorns': 0,
        # B-05 (Update #50): Light-Radius-Bonus aus Helmen/Amuletten.
        # Cells, die der Spieler aufdeckt pro Frame (Minimap Fog-of-War).
        'light_radius': 0,
        # Update #159: Aspekt-Affix-Akkumulatoren (Lore-getreu, gefoldet)
        'kharns_form': 0, 'nheyras_zeit': 0, 'ousens_blick': 0,
        'valsas_wille': 0, 'imnesh_sprache': 0, 'shulavh_faden': 0,
        'siebter_atem': 0.0,
    }
    set_counts = {}
    for item in player.equipment.values():
        if item is None:
            continue
        for k, v in item.affixes:
            if k in out:
                out[k] += v
        for k, v in item.gem_affixes():
            if k in out:
                out[k] += v
        if item.set_id:
            set_counts[item.set_id] = set_counts.get(item.set_id, 0) + 1
    # Set-Boni
    from .constants import ITEM_SETS
    for sid, count in set_counts.items():
        if sid not in ITEM_SETS:
            continue
        bonuses = ITEM_SETS[sid]['bonuses']
        # Höchster verfügbarer Schwellenwert
        for threshold in sorted(bonuses.keys(), reverse=True):
            if count >= threshold:
                key, val = bonuses[threshold]
                if key in out:
                    out[key] += val
                break
    # Update #159: Aspekt-Affixes in die Engine-Stat-Spalten folden,
    # damit kein progression.effective()-Refactor nötig ist.
    # Die Aspekt-Werte bleiben separat im out-Dict erhalten (für
    # Tag-Filter / UI-Display).
    for asp_key in ASPEKT_AFFIX_KEYS:
        if out[asp_key] > 0:
            target = ASPEKT_AFFIX_FOLD[asp_key]
            if target in out:
                out[target] += out[asp_key]
    return out
