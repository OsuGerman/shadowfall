"""Klassen, Attribute, Skill-Tree, Level-Up und effektive Stats."""

from .constants import (
    TREE_NODES, CLASS_TREE_NODES, AURAS,
    SKILL_XP_PER_LEVEL, SKILL_LEVEL_MAX, SKILL_DMG_PER_LEVEL,
)
from . import items as items_mod


# ============================================================
# Akt-Gating (ROADMAP T2.4)
# ============================================================
def can_enter_akt(player, akt):
    """Update #156 (ROADMAP T2.4): Returnt True wenn der Spieler den
    gegebenen Akt betreten darf.

    Regel: Spieler braucht `akt_progress >= akt - 1` abgeschlossene
    Dungeons.  Akt 1 (akt_progress >= 0) ist immer erlaubt.

    Synchron zur outposts.unlocked_outposts und zur Quest-Prereq-Logik.
    Kann von UI-Code (Outpost-Portal-Click, Travel-Modal, Quest-Board)
    aufgerufen werden für einen einheitlichen Gating-Pfad.
    """
    if akt is None or akt <= 1:
        return True
    akt_progress = len(getattr(player, 'completed_dungeons', ()))
    return akt_progress >= (akt - 1)


def akt_block_reason(player, akt):
    """Returnt eine lore-konforme Erklär-Zeile wenn `can_enter_akt`
    False ist — sonst None.

    Beispiel: „Akt 3 noch verschlossen — schließe Akt 1-2 zuerst ab."
    """
    if can_enter_akt(player, akt):
        return None
    akt_progress = len(getattr(player, 'completed_dungeons', ()))
    needed = (akt - 1) - akt_progress
    if needed == 1:
        return f'Akt {akt} noch verschlossen — schließe Akt {akt - 1} zuerst ab.'
    return (f'Akt {akt} noch verschlossen — schließe Akt '
            f'{akt - needed}-{akt - 1} zuerst ab.')


# ---- Effektive Stats (Basis + Attribute + Items + Skill-Tree) ----

def effective(player):
    """Gibt ein Dict aller relevanten Endwerte zurück."""
    item_stats = items_mod.aggregate_stats(player)
    tree = player.tree
    ctree = player.class_tree

    # Attribute → Multiplikatoren
    str_dmg_pct = player.strength * 0.03
    int_mp = player.intellect * 5
    int_dmg_pct = player.intellect * 0.02
    dex_speed = player.dexterity * 0.02
    dex_crit = player.dexterity * 0.01

    # Universaler Skill-Tree (alle vorhandenen Knoten dynamisch auswerten)
    vit_hp = TREE_NODES['vit']['hp'] * tree.get('vit', 0)
    arc_mp = TREE_NODES['arc']['mp'] * tree.get('arc', 0)
    pow_dmg = TREE_NODES['pow']['dmg_pct'] * tree.get('pow', 0)
    prc_crit = TREE_NODES['prc']['crit'] * tree.get('prc', 0)
    agi_spd = TREE_NODES['agi']['speed'] * tree.get('agi', 0)
    cnc_cdr = TREE_NODES['cnc']['cdr'] * tree.get('cnc', 0)
    # Neue Knoten
    extra_crit_dmg = TREE_NODES.get('crit_dmg', {}).get('crit_dmg', 0) * tree.get('crit_dmg', 0)
    extra_regen = TREE_NODES.get('regen', {}).get('hp_regen', 0) * tree.get('regen', 0)
    extra_dmg_red = TREE_NODES.get('res', {}).get('dmg_red', 0) * tree.get('res', 0)
    extra_magnet = TREE_NODES.get('magnet', {}).get('magnet', 0) * tree.get('magnet', 0)
    extra_gold = TREE_NODES.get('rich', {}).get('gold_bonus', 0) * tree.get('rich', 0)
    extra_xp = TREE_NODES.get('wis', {}).get('xp_bonus', 0) * tree.get('wis', 0)

    # Klassen-Talente: dynamische Bonus-Akkumulation
    class_bonuses = _class_tree_bonuses(player)

    hp_max = player.hp_max_base + item_stats['hp'] + vit_hp
    hp_max *= (1 + class_bonuses.get('hp_pct', 0))
    mp_max = (player.mp_max_base + item_stats['mp'] + int_mp + arc_mp
              + class_bonuses.get('arc_mp', 0))
    hp_regen = player.hp_regen_base + item_stats['hp_regen'] + extra_regen
    mp_regen = (player.mp_regen_base + item_stats['mp_regen']
                + class_bonuses.get('mp_regen', 0))

    dmg_mult = (1.0 + item_stats['dmg_pct'] / 100.0 + str_dmg_pct + int_dmg_pct
                + pow_dmg + class_bonuses.get('elem_dmg', 0))
    # Rage: bei <50% HP zusätzlicher Schaden
    if class_bonuses.get('dmg_low_hp', 0) > 0 and player.hp < hp_max * 0.5:
        dmg_mult += class_bonuses['dmg_low_hp']
    # Combo-Buff
    if getattr(player, 'combo_buff_left', 0) > 0:
        dmg_mult += 0.30
    damage_flat = player.base_damage + item_stats['dmg_flat']
    damage = damage_flat * dmg_mult

    crit_chance = ((item_stats['crit_chance'] / 100.0) + dex_crit + prc_crit
                   + class_bonuses.get('crit_chance', 0)
                   + class_bonuses.get('crit', 0))
    crit_chance = min(0.85, crit_chance)
    crit_mult = (1.5 + item_stats['crit_dmg'] / 100.0
                 + class_bonuses.get('crit_dmg', 0)
                 + class_bonuses.get('crit_spell', 0)
                 + extra_crit_dmg)

    speed_mult = 1.0 + (item_stats['speed'] / 100.0) + dex_speed + agi_spd
    speed = player.base_speed * speed_mult

    cdr = min(0.6, (item_stats['cdr'] / 100.0) + cnc_cdr)
    dodge_cdr = min(0.6, item_stats['dodge_cdr'] / 100.0 + class_bonuses.get('dodge_cdr', 0))

    # Aura-Bonus
    aura_b = _aura_bonuses(player)
    if 'hp_mult' in aura_b:
        hp_max *= aura_b['hp_mult']
    if 'speed_mult' in aura_b:
        speed *= aura_b['speed_mult']
    if 'mp_regen_mult' in aura_b:
        mp_regen *= aura_b['mp_regen_mult']
    crit_chance += aura_b.get('crit_bonus', 0)
    crit_mult += aura_b.get('crit_dmg_bonus', 0)

    # Mana-Reservation durch Aura
    mp_reserved = 0
    if player.aura:
        mp_reserved = int(mp_max * AURAS[player.aura]['reserve'])

    # Effektives Mana-Max
    mp_max_eff = mp_max - mp_reserved

    # Schaden-Reduktion: kombiniert Aura + Tree
    dmg_taken_mult = aura_b.get('dmg_taken_mult', 1.0) * (1.0 - extra_dmg_red)

    # Update #80 W-12: Mahnmal-Schrein-Blessings (Lore-Bibel 6.4).
    # Pro Stack jeweils +%-Bonus, max 5 Stacks/Aspekt.
    # 1=Kharn (Phys-Dmg), 2=Nheyra (HP), 3=Ousen (HP-Regen),
    # 4=Valsa (Fire-Dmg), 5=Im-Nesh (Lit-Dmg), 6=Shulavh (Cold-Dmg),
    # 7=Der Siebte (alle Stats schwach +)
    bless = getattr(player, 'mahnmal_blessings', None) or {}
    if bless:
        k_kharn   = min(5, bless.get(1, 0)) * 0.05
        k_nheyra  = min(5, bless.get(2, 0)) * 0.05
        k_ousen   = min(5, bless.get(3, 0)) * 0.5    # +0.5 hp/s
        k_valsa   = min(5, bless.get(4, 0)) * 0.04
        k_imnesh  = min(5, bless.get(5, 0)) * 0.04
        k_shulavh = min(5, bless.get(6, 0)) * 0.04
        k_siebte  = min(5, bless.get(7, 0)) * 0.02
        # Apply
        damage *= (1 + k_kharn + k_siebte)
        hp_max *= (1 + k_nheyra + k_siebte)
        hp_regen += k_ousen + k_siebte
        # Element-Dmg-Boosts wirken später als Multiplikator additiv
        _bless_fire_extra = k_valsa
        _bless_lit_extra  = k_imnesh
        _bless_cold_extra = k_shulavh
    else:
        _bless_fire_extra = 0.0
        _bless_lit_extra = 0.0
        _bless_cold_extra = 0.0

    return dict(
        hp_max=hp_max, mp_max=mp_max_eff, mp_reserved=mp_reserved,
        hp_regen=hp_regen, mp_regen=mp_regen,
        damage=damage, damage_flat=damage_flat, dmg_mult=dmg_mult,
        crit_chance=crit_chance, crit_mult=crit_mult,
        speed=speed,
        cdr=cdr, dodge_cdr=dodge_cdr,
        fire_dmg=1 + item_stats['fire_dmg'] / 100.0 + aura_b.get('spell_dmg_mult', 1.0) - 1.0 + _bless_fire_extra,
        cold_dmg=1 + item_stats['cold_dmg'] / 100.0 + aura_b.get('spell_dmg_mult', 1.0) - 1.0 + _bless_cold_extra,
        lit_dmg=1 + item_stats['lit_dmg'] / 100.0 + aura_b.get('spell_dmg_mult', 1.0) - 1.0 + _bless_lit_extra,
        thorns=item_stats['thorns'] + class_bonuses.get('thorns', 0),
        light_radius=item_stats.get('light_radius', 0),
        cleave=class_bonuses.get('cleave', 0),
        mp_to_hp=class_bonuses.get('mp_to_hp', 0),
        free_cast=class_bonuses.get('free_cast', 0) + class_bonuses.get('echo_chance', 0),
        dodge_chance=class_bonuses.get('dodge_chance', 0),
        poison_chance=class_bonuses.get('poison_chance', 0),
        dmg_taken_mult=dmg_taken_mult,
        magnet_bonus=extra_magnet,
        gold_bonus=extra_gold,
        xp_bonus=extra_xp,
    )


def _class_tree_bonuses(player):
    """Akkumuliert alle Klassen-Tree-Boni."""
    out = {}
    nodes = CLASS_TREE_NODES.get(player.cls, {})
    for node_id, node in nodes.items():
        lvl = player.class_tree.get(node_id, 0)
        if lvl <= 0:
            continue
        for key, val in node.items():
            if key in ('name', 'max', 'desc'):
                continue
            out[key] = out.get(key, 0) + val * lvl
    return out


def _aura_bonuses(player):
    if not player.aura:
        return {}
    return dict(AURAS[player.aura].get('bonuses', {}))


def skill_level_mult(player, skill_key):
    """Damage multiplier from skill level."""
    lvl = player.skill_levels.get(skill_key, 1)
    return 1.0 + (lvl - 1) * SKILL_DMG_PER_LEVEL


def grant_skill_xp(player, amount):
    """Verteilt XP gleichmäßig auf alle Skills."""
    per_skill = max(1, amount // 5)
    for skill_key in list(player.skill_xp.keys()):
        lvl = player.skill_levels.get(skill_key, 1)
        if lvl >= SKILL_LEVEL_MAX:
            continue
        player.skill_xp[skill_key] += per_skill
        need = SKILL_XP_PER_LEVEL[min(lvl - 1, len(SKILL_XP_PER_LEVEL) - 1)]
        while player.skill_xp[skill_key] >= need and lvl < SKILL_LEVEL_MAX:
            player.skill_xp[skill_key] -= need
            lvl += 1
            player.skill_levels[skill_key] = lvl
            if lvl >= SKILL_LEVEL_MAX:
                break
            need = SKILL_XP_PER_LEVEL[min(lvl - 1, len(SKILL_XP_PER_LEVEL) - 1)]


def skill_xp_progress(player, skill_key):
    """Returnt (current_xp, xp_to_next_level)."""
    lvl = player.skill_levels.get(skill_key, 1)
    if lvl >= SKILL_LEVEL_MAX:
        return (0, 0)
    need = SKILL_XP_PER_LEVEL[min(lvl - 1, len(SKILL_XP_PER_LEVEL) - 1)]
    return (player.skill_xp.get(skill_key, 0), need)


def try_invest_class(player, node_id):
    """Investiert einen Klassen-Punkt in einen Klassen-Tree-Knoten."""
    nodes = CLASS_TREE_NODES.get(player.cls, {})
    if node_id not in nodes:
        return False
    if player.class_points <= 0:
        return False
    cur = player.class_tree.get(node_id, 0)
    if cur >= nodes[node_id]['max']:
        return False
    player.class_tree[node_id] = cur + 1
    player.class_points -= 1
    return True


def set_aura(player, aura_key):
    """Aktiviert/deaktiviert eine Aura (nur passend zur Klasse)."""
    if aura_key is None:
        player.aura = None
        return True
    if aura_key not in AURAS:
        return False
    if player.cls not in AURAS[aura_key]['class_']:
        return False
    player.aura = None if player.aura == aura_key else aura_key
    # Mana-Reservation: Spieler-MP kann nicht über neues Maximum sein
    eff = effective(player)
    if player.mp > eff['mp_max']:
        player.mp = eff['mp_max']
    return True


# ---- Level-Up & Punktevergabe ----

def level_up(player):
    """Wendet Level-Up an. Punkte werden vergeben (nicht direkt verteilt)."""
    player.xp -= player.xp_to_next
    player.level += 1
    player.xp_to_next = int(player.xp_to_next * 1.45)
    player.skill_points += 1
    player.attr_points += 3
    player.class_points += 1
    # HP/MP werden voll aufgefüllt (mit neuen Maxwerten)
    eff = effective(player)
    player.hp = eff['hp_max']
    player.mp = eff['mp_max']


def try_invest_skill(player, node_id):
    """Investiert einen Skillpunkt in einen Tree-Knoten."""
    if node_id not in TREE_NODES:
        return False
    if player.skill_points <= 0:
        return False
    cur = player.tree.get(node_id, 0)
    if cur >= TREE_NODES[node_id]['max']:
        return False
    player.tree[node_id] = cur + 1
    player.skill_points -= 1
    return True


def try_invest_mahnmal_blessing(player, aspect_id):
    """Update #80 W-12: Spendet 1 Mahnmal-Marke des Aspekts und erhöht
    den Schrein-Stack (max 5). Lore: das Mahnmal verschluckt die Marke.
    Returns True bei Erfolg."""
    if aspect_id not in (1, 2, 3, 4, 5, 6, 7):
        return False
    marken = getattr(player, 'mahnmal_marken', None)
    bless = getattr(player, 'mahnmal_blessings', None)
    if marken is None or bless is None:
        return False
    if marken.get(aspect_id, 0) <= 0:
        return False
    if bless.get(aspect_id, 0) >= 5:
        return False
    marken[aspect_id] -= 1
    bless[aspect_id] = bless.get(aspect_id, 0) + 1
    return True


def try_refund_skill(player, node_id):
    """H-17 (Update #75): Respec eines Universal-Tree-Knotens.
    Konsumiert eine Orb-of-Regret und gibt einen Skill-Punkt zurück.
    Lore: Erinnerungs-Sphäre löscht die gelernte Lektion (Spiegelhof-Reflexion).
    """
    if node_id not in TREE_NODES:
        return False
    cur = player.tree.get(node_id, 0)
    if cur <= 0:
        return False
    if getattr(player, 'orbs_of_regret', 0) <= 0:
        return False
    player.tree[node_id] = cur - 1
    if player.tree[node_id] == 0:
        del player.tree[node_id]
    player.skill_points += 1
    player.orbs_of_regret -= 1
    return True


def try_refund_class(player, node_id):
    """H-17 (Update #75): Respec eines Klassen-Tree-Knotens.
    Konsumiert eine Orb-of-Regret und gibt einen Klassen-Punkt zurück.
    """
    nodes = CLASS_TREE_NODES.get(player.cls, {})
    if node_id not in nodes:
        return False
    cur = player.class_tree.get(node_id, 0)
    if cur <= 0:
        return False
    if getattr(player, 'orbs_of_regret', 0) <= 0:
        return False
    player.class_tree[node_id] = cur - 1
    if player.class_tree[node_id] == 0:
        del player.class_tree[node_id]
    player.class_points += 1
    player.orbs_of_regret -= 1
    return True


def try_invest_attr(player, attr):
    if player.attr_points <= 0:
        return False
    if attr not in ('strength', 'intellect', 'dexterity'):
        return False
    setattr(player, attr, getattr(player, attr) + 1)
    player.attr_points -= 1
    return True


def try_equip(player, inv_index):
    """Equipt das Item aus Inventar-Slot inv_index. Tauscht falls bereits belegt."""
    if not (0 <= inv_index < len(player.inventory)):
        return False
    item = player.inventory[inv_index]
    if item is None:
        return False
    current = player.equipment.get(item.slot)
    player.equipment[item.slot] = item
    player.inventory[inv_index] = current
    return True


def try_unequip(player, slot):
    item = player.equipment.get(slot)
    if item is None:
        return False
    # Erstes freies Inventar-Feld finden
    for i, slot_item in enumerate(player.inventory):
        if slot_item is None:
            player.inventory[i] = item
            player.equipment[slot] = None
            return True
    return False  # Inventar voll


def try_drop_item(player, inv_index):
    """Entfernt Item aus Inventar (für 'Z' Drop oder Auto-Cleanup)."""
    if 0 <= inv_index < len(player.inventory):
        player.inventory[inv_index] = None
        return True
    return False
