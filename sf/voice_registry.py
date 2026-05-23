"""Auto-generiert von tools/voice_gen.py.

Voice-Line-Registry: pro (npc, category) -> Liste von MP3-Pfaden.
Nicht von Hand editieren — wird beim nächsten voice_gen-Run überschrieben.
"""
from __future__ import annotations

import random


VOICE_POOLS: dict[tuple[str, str], list[str]] = {
    ('cls_druid', 'attack'): [
        'sounds/voice/cls_druid/cls_druid_attack_01.mp3',
    ],
    ('cls_druid', 'big_skill'): [
        'sounds/voice/cls_druid/cls_druid_big_skill_01.mp3',
        'sounds/voice/cls_druid/cls_druid_big_skill_02.mp3',
    ],
    ('cls_druid', 'crit'): [
        'sounds/voice/cls_druid/cls_druid_crit_01.mp3',
    ],
    ('cls_druid', 'death'): [
        'sounds/voice/cls_druid/cls_druid_death_01.mp3',
    ],
    ('cls_druid', 'level_up'): [
        'sounds/voice/cls_druid/cls_druid_level_up_01.mp3',
    ],
    ('cls_huntress', 'attack'): [
        'sounds/voice/cls_huntress/cls_huntress_attack_01.mp3',
        'sounds/voice/cls_huntress/cls_huntress_attack_02.mp3',
        'sounds/voice/cls_huntress/cls_huntress_attack_03.mp3',
    ],
    ('cls_huntress', 'big_skill'): [
        'sounds/voice/cls_huntress/cls_huntress_big_skill_01.mp3',
        'sounds/voice/cls_huntress/cls_huntress_big_skill_02.mp3',
        'sounds/voice/cls_huntress/cls_huntress_big_skill_03.mp3',
    ],
    ('cls_huntress', 'crit'): [
        'sounds/voice/cls_huntress/cls_huntress_crit_01.mp3',
        'sounds/voice/cls_huntress/cls_huntress_crit_02.mp3',
    ],
    ('cls_huntress', 'death'): [
        'sounds/voice/cls_huntress/cls_huntress_death_01.mp3',
    ],
    ('cls_huntress', 'level_up'): [
        'sounds/voice/cls_huntress/cls_huntress_level_up_01.mp3',
    ],
    ('cls_mercenary', 'attack'): [
        'sounds/voice/cls_mercenary/cls_mercenary_attack_01.mp3',
        'sounds/voice/cls_mercenary/cls_mercenary_attack_02.mp3',
        'sounds/voice/cls_mercenary/cls_mercenary_attack_03.mp3',
    ],
    ('cls_mercenary', 'big_skill'): [
        'sounds/voice/cls_mercenary/cls_mercenary_big_skill_01.mp3',
        'sounds/voice/cls_mercenary/cls_mercenary_big_skill_02.mp3',
        'sounds/voice/cls_mercenary/cls_mercenary_big_skill_03.mp3',
    ],
    ('cls_mercenary', 'crit'): [
        'sounds/voice/cls_mercenary/cls_mercenary_crit_01.mp3',
        'sounds/voice/cls_mercenary/cls_mercenary_crit_02.mp3',
    ],
    ('cls_mercenary', 'death'): [
        'sounds/voice/cls_mercenary/cls_mercenary_death_01.mp3',
    ],
    ('cls_mercenary', 'level_up'): [
        'sounds/voice/cls_mercenary/cls_mercenary_level_up_01.mp3',
    ],
    ('cls_monk', 'big_skill'): [
        'sounds/voice/cls_monk/cls_monk_big_skill_01.mp3',
        'sounds/voice/cls_monk/cls_monk_big_skill_02.mp3',
        'sounds/voice/cls_monk/cls_monk_big_skill_03.mp3',
    ],
    ('cls_monk', 'crit'): [
        'sounds/voice/cls_monk/cls_monk_crit_01.mp3',
    ],
    ('cls_monk', 'death'): [
        'sounds/voice/cls_monk/cls_monk_death_01.mp3',
    ],
    ('cls_monk', 'level_up'): [
        'sounds/voice/cls_monk/cls_monk_level_up_01.mp3',
    ],
    ('cls_ranger', 'attack'): [
        'sounds/voice/cls_ranger/cls_ranger_attack_01.mp3',
        'sounds/voice/cls_ranger/cls_ranger_attack_02.mp3',
        'sounds/voice/cls_ranger/cls_ranger_attack_03.mp3',
    ],
    ('cls_ranger', 'big_skill'): [
        'sounds/voice/cls_ranger/cls_ranger_big_skill_01.mp3',
        'sounds/voice/cls_ranger/cls_ranger_big_skill_02.mp3',
        'sounds/voice/cls_ranger/cls_ranger_big_skill_03.mp3',
    ],
    ('cls_ranger', 'crit'): [
        'sounds/voice/cls_ranger/cls_ranger_crit_01.mp3',
        'sounds/voice/cls_ranger/cls_ranger_crit_02.mp3',
    ],
    ('cls_ranger', 'death'): [
        'sounds/voice/cls_ranger/cls_ranger_death_01.mp3',
    ],
    ('cls_ranger', 'level_up'): [
        'sounds/voice/cls_ranger/cls_ranger_level_up_01.mp3',
    ],
    ('cls_sorceress', 'attack'): [
        'sounds/voice/cls_sorceress/cls_sorceress_attack_01.mp3',
        'sounds/voice/cls_sorceress/cls_sorceress_attack_02.mp3',
        'sounds/voice/cls_sorceress/cls_sorceress_attack_03.mp3',
    ],
    ('cls_sorceress', 'big_skill'): [
        'sounds/voice/cls_sorceress/cls_sorceress_big_skill_01.mp3',
        'sounds/voice/cls_sorceress/cls_sorceress_big_skill_02.mp3',
        'sounds/voice/cls_sorceress/cls_sorceress_big_skill_03.mp3',
    ],
    ('cls_sorceress', 'crit'): [
        'sounds/voice/cls_sorceress/cls_sorceress_crit_01.mp3',
    ],
    ('cls_sorceress', 'death'): [
        'sounds/voice/cls_sorceress/cls_sorceress_death_01.mp3',
    ],
    ('cls_sorceress', 'level_up'): [
        'sounds/voice/cls_sorceress/cls_sorceress_level_up_01.mp3',
    ],
    ('cls_warrior', 'attack_skill_casts'): [
        'sounds/voice/cls_warrior/cls_warrior_attack_skill_casts_01.mp3',
        'sounds/voice/cls_warrior/cls_warrior_attack_skill_casts_02.mp3',
        'sounds/voice/cls_warrior/cls_warrior_attack_skill_casts_03.mp3',
        'sounds/voice/cls_warrior/cls_warrior_attack_skill_casts_04.mp3',
        'sounds/voice/cls_warrior/cls_warrior_attack_skill_casts_05.mp3',
    ],
    ('cls_warrior', 'big_skill_slam_etc'): [
        'sounds/voice/cls_warrior/cls_warrior_big_skill_slam_etc_01.mp3',
        'sounds/voice/cls_warrior/cls_warrior_big_skill_slam_etc_02.mp3',
        'sounds/voice/cls_warrior/cls_warrior_big_skill_slam_etc_03.mp3',
    ],
    ('cls_warrior', 'crit'): [
        'sounds/voice/cls_warrior/cls_warrior_crit_01.mp3',
        'sounds/voice/cls_warrior/cls_warrior_crit_02.mp3',
    ],
    ('cls_warrior', 'death'): [
        'sounds/voice/cls_warrior/cls_warrior_death_01.mp3',
    ],
    ('cls_warrior', 'level_up'): [
        'sounds/voice/cls_warrior/cls_warrior_level_up_01.mp3',
    ],
    ('cls_witch', 'attack'): [
        'sounds/voice/cls_witch/cls_witch_attack_01.mp3',
        'sounds/voice/cls_witch/cls_witch_attack_02.mp3',
        'sounds/voice/cls_witch/cls_witch_attack_03.mp3',
    ],
    ('cls_witch', 'big_skill'): [
        'sounds/voice/cls_witch/cls_witch_big_skill_01.mp3',
        'sounds/voice/cls_witch/cls_witch_big_skill_02.mp3',
        'sounds/voice/cls_witch/cls_witch_big_skill_03.mp3',
    ],
    ('cls_witch', 'crit'): [
        'sounds/voice/cls_witch/cls_witch_crit_01.mp3',
    ],
    ('cls_witch', 'death'): [
        'sounds/voice/cls_witch/cls_witch_death_01.mp3',
    ],
    ('cls_witch', 'level_up'): [
        'sounds/voice/cls_witch/cls_witch_level_up_01.mp3',
    ],
    ('drei_muetter', 'ascendancy'): [
        'sounds/voice/drei_muetter/drei_muetter_ascendancy_01.mp3',
        'sounds/voice/drei_muetter/drei_muetter_ascendancy_02.mp3',
        'sounds/voice/drei_muetter/drei_muetter_ascendancy_03.mp3',
    ],
    ('drei_muetter', 'endgame_reveal'): [
        'sounds/voice/drei_muetter/drei_muetter_endgame_reveal_01.mp3',
    ],
    ('drei_muetter', 'trial_hint'): [
        'sounds/voice/drei_muetter/drei_muetter_trial_hint_01.mp3',
        'sounds/voice/drei_muetter/drei_muetter_trial_hint_02.mp3',
        'sounds/voice/drei_muetter/drei_muetter_trial_hint_03.mp3',
    ],
    ('drei_muetter', 'trial_intro'): [
        'sounds/voice/drei_muetter/drei_muetter_trial_intro_01.mp3',
        'sounds/voice/drei_muetter/drei_muetter_trial_intro_02.mp3',
    ],
    ('generic', 'boss_encounter'): [
        'sounds/voice/generic/generic_boss_encounter_01.mp3',
        'sounds/voice/generic/generic_boss_encounter_02.mp3',
        'sounds/voice/generic/generic_boss_encounter_03.mp3',
        'sounds/voice/generic/generic_boss_encounter_04.mp3',
    ],
    ('generic', 'death_lines_pool_ber_alle_klassen_klassen_agnostisch'): [
        'sounds/voice/generic/generic_death_lines_pool_ber_alle_klassen_klassen_agnostisch_01.mp3',
        'sounds/voice/generic/generic_death_lines_pool_ber_alle_klassen_klassen_agnostisch_02.mp3',
        'sounds/voice/generic/generic_death_lines_pool_ber_alle_klassen_klassen_agnostisch_03.mp3',
        'sounds/voice/generic/generic_death_lines_pool_ber_alle_klassen_klassen_agnostisch_04.mp3',
    ],
    ('generic', 'pickup'): [
        'sounds/voice/generic/generic_pickup_01.mp3',
        'sounds/voice/generic/generic_pickup_02.mp3',
        'sounds/voice/generic/generic_pickup_03.mp3',
    ],
    ('generic', 'wake_up_quotes_pool_siehe_gameplay_doc_teil_a_5'): [
        'sounds/voice/generic/generic_wake_up_quotes_pool_siehe_gameplay_doc_teil_a_5_01.mp3',
        'sounds/voice/generic/generic_wake_up_quotes_pool_siehe_gameplay_doc_teil_a_5_02.mp3',
        'sounds/voice/generic/generic_wake_up_quotes_pool_siehe_gameplay_doc_teil_a_5_03.mp3',
        'sounds/voice/generic/generic_wake_up_quotes_pool_siehe_gameplay_doc_teil_a_5_04.mp3',
    ],
    ('helst', 'death'): [
        'sounds/voice/helst/helst_death_01.mp3',
        'sounds/voice/helst/helst_death_02.mp3',
        'sounds/voice/helst/helst_death_03.mp3',
    ],
    ('helst', 'greeting'): [
        'sounds/voice/helst/helst_greeting_01.mp3',
        'sounds/voice/helst/helst_greeting_02.mp3',
        'sounds/voice/helst/helst_greeting_03.mp3',
        'sounds/voice/helst/helst_greeting_04.mp3',
        'sounds/voice/helst/helst_greeting_05.mp3',
    ],
    ('helst', 'lore'): [
        'sounds/voice/helst/helst_lore_01.mp3',
        'sounds/voice/helst/helst_lore_02.mp3',
        'sounds/voice/helst/helst_lore_03.mp3',
        'sounds/voice/helst/helst_lore_04.mp3',
        'sounds/voice/helst/helst_lore_05.mp3',
    ],
    ('helst', 'quest_offer'): [
        'sounds/voice/helst/helst_quest_offer_01.mp3',
        'sounds/voice/helst/helst_quest_offer_02.mp3',
        'sounds/voice/helst/helst_quest_offer_03.mp3',
        'sounds/voice/helst/helst_quest_offer_04.mp3',
        'sounds/voice/helst/helst_quest_offer_05.mp3',
    ],
    ('helst', 'special_akt'): [
        'sounds/voice/helst/helst_special_akt_01.mp3',
        'sounds/voice/helst/helst_special_akt_02.mp3',
    ],
    ('helst', 'twist_reveal'): [
        'sounds/voice/helst/helst_twist_reveal_01.mp3',
        'sounds/voice/helst/helst_twist_reveal_02.mp3',
        'sounds/voice/helst/helst_twist_reveal_03.mp3',
        'sounds/voice/helst/helst_twist_reveal_04.mp3',
    ],
    ('korven', 'combat'): [
        'sounds/voice/korven/korven_combat_01.mp3',
        'sounds/voice/korven/korven_combat_02.mp3',
        'sounds/voice/korven/korven_combat_03.mp3',
        'sounds/voice/korven/korven_combat_04.mp3',
        'sounds/voice/korven/korven_combat_05.mp3',
    ],
    ('korven', 'death'): [
        'sounds/voice/korven/korven_death_01.mp3',
        'sounds/voice/korven/korven_death_02.mp3',
        'sounds/voice/korven/korven_death_03.mp3',
    ],
    ('korven', 'greeting'): [
        'sounds/voice/korven/korven_greeting_01.mp3',
        'sounds/voice/korven/korven_greeting_02.mp3',
        'sounds/voice/korven/korven_greeting_03.mp3',
        'sounds/voice/korven/korven_greeting_04.mp3',
        'sounds/voice/korven/korven_greeting_05.mp3',
        'sounds/voice/korven/korven_greeting_06.mp3',
    ],
    ('korven', 'quest_offer'): [
        'sounds/voice/korven/korven_quest_offer_01.mp3',
        'sounds/voice/korven/korven_quest_offer_02.mp3',
        'sounds/voice/korven/korven_quest_offer_03.mp3',
        'sounds/voice/korven/korven_quest_offer_04.mp3',
        'sounds/voice/korven/korven_quest_offer_05.mp3',
    ],
    ('korven', 'special_akt'): [
        'sounds/voice/korven/korven_special_akt_01.mp3',
        'sounds/voice/korven/korven_special_akt_02.mp3',
        'sounds/voice/korven/korven_special_akt_03.mp3',
    ],
    ('korven', 'twist_reveal'): [
        'sounds/voice/korven/korven_twist_reveal_01.mp3',
        'sounds/voice/korven/korven_twist_reveal_02.mp3',
        'sounds/voice/korven/korven_twist_reveal_03.mp3',
        'sounds/voice/korven/korven_twist_reveal_04.mp3',
    ],
    ('mara', 'atlas'): [
        'sounds/voice/mara/mara_atlas_01.mp3',
        'sounds/voice/mara/mara_atlas_02.mp3',
    ],
    ('mara', 'death'): [
        'sounds/voice/mara/mara_death_01.mp3',
        'sounds/voice/mara/mara_death_02.mp3',
    ],
    ('mara', 'greeting'): [
        'sounds/voice/mara/mara_greeting_01.mp3',
        'sounds/voice/mara/mara_greeting_02.mp3',
        'sounds/voice/mara/mara_greeting_03.mp3',
        'sounds/voice/mara/mara_greeting_04.mp3',
    ],
    ('mara', 'lore'): [
        'sounds/voice/mara/mara_lore_01.mp3',
        'sounds/voice/mara/mara_lore_02.mp3',
        'sounds/voice/mara/mara_lore_03.mp3',
        'sounds/voice/mara/mara_lore_04.mp3',
    ],
    ('mara', 'quest_offer'): [
        'sounds/voice/mara/mara_quest_offer_01.mp3',
        'sounds/voice/mara/mara_quest_offer_02.mp3',
        'sounds/voice/mara/mara_quest_offer_03.mp3',
    ],
    ('otreth', 'death'): [
        'sounds/voice/otreth/otreth_death_01.mp3',
    ],
    ('otreth', 'greeting'): [
        'sounds/voice/otreth/otreth_greeting_01.mp3',
        'sounds/voice/otreth/otreth_greeting_02.mp3',
        'sounds/voice/otreth/otreth_greeting_03.mp3',
        'sounds/voice/otreth/otreth_greeting_04.mp3',
    ],
    ('otreth', 'lore'): [
        'sounds/voice/otreth/otreth_lore_01.mp3',
        'sounds/voice/otreth/otreth_lore_02.mp3',
        'sounds/voice/otreth/otreth_lore_03.mp3',
        'sounds/voice/otreth/otreth_lore_04.mp3',
    ],
    ('otreth', 'service'): [
        'sounds/voice/otreth/otreth_service_01.mp3',
        'sounds/voice/otreth/otreth_service_02.mp3',
        'sounds/voice/otreth/otreth_service_03.mp3',
        'sounds/voice/otreth/otreth_service_04.mp3',
    ],
    ('otreth', 'spezial_wenn_spieler_eine_mythic_item_bringt'): [
        'sounds/voice/otreth/otreth_spezial_wenn_spieler_eine_mythic_item_bringt_01.mp3',
        'sounds/voice/otreth/otreth_spezial_wenn_spieler_eine_mythic_item_bringt_02.mp3',
        'sounds/voice/otreth/otreth_spezial_wenn_spieler_eine_mythic_item_bringt_03.mp3',
    ],
    ('tameris', 'combat'): [
        'sounds/voice/tameris/tameris_combat_01.mp3',
        'sounds/voice/tameris/tameris_combat_02.mp3',
        'sounds/voice/tameris/tameris_combat_03.mp3',
        'sounds/voice/tameris/tameris_combat_04.mp3',
    ],
    ('tameris', 'death'): [
        'sounds/voice/tameris/tameris_death_01.mp3',
        'sounds/voice/tameris/tameris_death_02.mp3',
    ],
    ('tameris', 'greeting'): [
        'sounds/voice/tameris/tameris_greeting_01.mp3',
        'sounds/voice/tameris/tameris_greeting_02.mp3',
        'sounds/voice/tameris/tameris_greeting_03.mp3',
        'sounds/voice/tameris/tameris_greeting_04.mp3',
        'sounds/voice/tameris/tameris_greeting_05.mp3',
    ],
    ('tameris', 'quest_offer'): [
        'sounds/voice/tameris/tameris_quest_offer_01.mp3',
        'sounds/voice/tameris/tameris_quest_offer_02.mp3',
        'sounds/voice/tameris/tameris_quest_offer_03.mp3',
    ],
    ('tameris', 'reveal'): [
        'sounds/voice/tameris/tameris_reveal_01.mp3',
        'sounds/voice/tameris/tameris_reveal_02.mp3',
        'sounds/voice/tameris/tameris_reveal_03.mp3',
    ],
    ('tameris', 'special'): [
        'sounds/voice/tameris/tameris_special_01.mp3',
        'sounds/voice/tameris/tameris_special_02.mp3',
    ],
    ('vehren', 'boss_threat'): [
        'sounds/voice/vehren/vehren_boss_threat_01.mp3',
        'sounds/voice/vehren/vehren_boss_threat_02.mp3',
        'sounds/voice/vehren/vehren_boss_threat_03.mp3',
        'sounds/voice/vehren/vehren_boss_threat_04.mp3',
    ],
    ('vehren', 'death'): [
        'sounds/voice/vehren/vehren_death_01.mp3',
        'sounds/voice/vehren/vehren_death_02.mp3',
    ],
    ('vehren', 'phase_transition'): [
        'sounds/voice/vehren/vehren_phase_transition_01.mp3',
        'sounds/voice/vehren/vehren_phase_transition_02.mp3',
        'sounds/voice/vehren/vehren_phase_transition_03.mp3',
    ],
    ('vehren', 'spezial_wenn_spieler_ihn_schont_alt_ending'): [
        'sounds/voice/vehren/vehren_spezial_wenn_spieler_ihn_schont_alt_ending_01.mp3',
        'sounds/voice/vehren/vehren_spezial_wenn_spieler_ihn_schont_alt_ending_02.mp3',
    ],
    ('vossharil', 'combat'): [
        'sounds/voice/vossharil/vossharil_combat_01.mp3',
        'sounds/voice/vossharil/vossharil_combat_02.mp3',
        'sounds/voice/vossharil/vossharil_combat_03.mp3',
    ],
    ('vossharil', 'death'): [
        'sounds/voice/vossharil/vossharil_death_01.mp3',
        'sounds/voice/vossharil/vossharil_death_02.mp3',
    ],
    ('vossharil', 'greeting'): [
        'sounds/voice/vossharil/vossharil_greeting_01.mp3',
        'sounds/voice/vossharil/vossharil_greeting_02.mp3',
        'sounds/voice/vossharil/vossharil_greeting_03.mp3',
        'sounds/voice/vossharil/vossharil_greeting_04.mp3',
        'sounds/voice/vossharil/vossharil_greeting_05.mp3',
    ],
    ('vossharil', 'lore'): [
        'sounds/voice/vossharil/vossharil_lore_01.mp3',
        'sounds/voice/vossharil/vossharil_lore_02.mp3',
        'sounds/voice/vossharil/vossharil_lore_03.mp3',
        'sounds/voice/vossharil/vossharil_lore_04.mp3',
    ],
    ('vossharil', 'quest_offer'): [
        'sounds/voice/vossharil/vossharil_quest_offer_01.mp3',
        'sounds/voice/vossharil/vossharil_quest_offer_02.mp3',
        'sounds/voice/vossharil/vossharil_quest_offer_03.mp3',
        'sounds/voice/vossharil/vossharil_quest_offer_04.mp3',
    ],
    ('vossharil', 'special'): [
        'sounds/voice/vossharil/vossharil_special_01.mp3',
        'sounds/voice/vossharil/vossharil_special_02.mp3',
    ],
}

# Per-Pool letzten Index speichern (Voice-Variation-System)
_LAST_INDEX: dict[tuple[str, str], int] = {}


def pick_voice(npc: str, category: str) -> str | None:
    """Zieht eine MP3 aus dem Pool, wiederholt nie zweimal in Folge."""
    pool = VOICE_POOLS.get((npc, category))
    if not pool:
        return None
    last = _LAST_INDEX.get((npc, category), -1)
    candidates = [i for i in range(len(pool)) if i != last]
    if not candidates:
        candidates = list(range(len(pool)))
    idx = random.choice(candidates)
    _LAST_INDEX[(npc, category)] = idx
    return pool[idx]
