"""Auto-generiert von tools/sprite_gen.py.

Sprite-Registry: target_id -> projekt-relativer PNG-Pfad.
"""
from __future__ import annotations


SPRITES: dict[str, str] = {
    # ---- boss_plate ----
    'echo_drache': 'assets/sprites/bosses/echo_drache.png',
    'ertrunkene_koenigin': 'assets/sprites/bosses/ertrunkene_koenigin.png',
    'nicht_gott': 'assets/sprites/bosses/nicht_gott.png',
    'salzhueter_brut': 'assets/sprites/bosses/salzhueter_brut.png',
    'senator_geist': 'assets/sprites/bosses/senator_geist.png',
    'shulavh': 'assets/sprites/bosses/shulavh.png',
    'vehren': 'assets/sprites/bosses/vehren.png',
    'velharn_trio': 'assets/sprites/bosses/velharn_trio.png',
    # ---- class ----
    'druid': 'assets/sprites/classes/druid.png',
    'huntress': 'assets/sprites/classes/huntress.png',
    'mercenary': 'assets/sprites/classes/mercenary.png',
    'monk': 'assets/sprites/classes/monk.png',
    'ranger': 'assets/sprites/classes/ranger.png',
    'sorceress': 'assets/sprites/classes/sorceress.png',
    'warrior': 'assets/sprites/classes/warrior.png',
    'witch': 'assets/sprites/classes/witch.png',
    # ---- mob ----
    'aschenbrut_akt_3_generic_mob': 'assets/sprites/mobs/aschenbrut_akt_3_generic_mob.png',
    'ertrunkene_koenigin_akt_6a_boss_mini': 'assets/sprites/mobs/ertrunkene_koenigin_akt_6a_boss_mini.png',
    'glaslord_senator_geist_akt_2': 'assets/sprites/mobs/glaslord_senator_geist_akt_2.png',
    'salzhueter_brut': 'assets/sprites/bosses/salzhueter_brut.png',
    'vehren_echo_akt_3_mini_variante': 'assets/sprites/mobs/vehren_echo_akt_3_mini_variante.png',
    'wurzelhueter_akt_4_generic_mob': 'assets/sprites/mobs/wurzelhueter_akt_4_generic_mob.png',
    # ---- portrait ----
    'bruder_helst_der_hundertjaehrige': 'assets/sprites/portraits/bruder_helst_der_hundertjaehrige.png',
    'die_drei_muetter_trias_in_einem_portrait': 'assets/sprites/portraits/die_drei_muetter_trias_in_einem_portrait.png',
    'inquisitor_general_vehren': 'assets/sprites/portraits/inquisitor_general_vehren.png',
    'korven_vor': 'assets/sprites/portraits/korven_vor.png',
    'mara_die_mahnerin': 'assets/sprites/portraits/mara_die_mahnerin.png',
    'otreth_hohlauge': 'assets/sprites/portraits/otreth_hohlauge.png',
    'tameris_die_lichtsucherin': 'assets/sprites/portraits/tameris_die_lichtsucherin.png',
    'vossharil_die_dreimalige': 'assets/sprites/portraits/vossharil_die_dreimalige.png',
    # ---- tile ----
    'astral_akt_5': 'assets/sprites/tiles/astral_akt_5.png',
    'crypt_floor_a': 'assets/sprites/tiles/crypt_floor_a.png',
    'crypt_floor_b': 'assets/sprites/tiles/crypt_floor_b.png',
    'crypt_floor_c': 'assets/sprites/tiles/crypt_floor_c.png',
    'crypt_floor_d': 'assets/sprites/tiles/crypt_floor_d.png',
    'crypt_wall_w': 'assets/sprites/tiles/crypt_wall_w.png',
    'desert_akt_1b': 'assets/sprites/tiles/desert_akt_1b.png',
    'frost_glass_ruins_akt_2': 'assets/sprites/tiles/frost_glass_ruins_akt_2.png',
    'hollow_word_akt_7': 'assets/sprites/tiles/hollow_word_akt_7.png',
    'lava_akt_3': 'assets/sprites/tiles/lava_akt_3.png',
    'swamp_akt_4': 'assets/sprites/tiles/swamp_akt_4.png',
    'town_brassweir': 'assets/sprites/tiles/town_brassweir.png',
    'wound_ash_akt_6b': 'assets/sprites/tiles/wound_ash_akt_6b.png',
    'wound_hollow_akt_6c': 'assets/sprites/tiles/wound_hollow_akt_6c.png',
    'wound_salt_akt_6a': 'assets/sprites/tiles/wound_salt_akt_6a.png',
}


def sprite_path(target_id: str) -> str | None:
    return SPRITES.get(target_id)
