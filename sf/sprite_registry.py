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
    # ---- decor ----
    'anvil': 'assets/sprites/decor/anvil.png',
    'bonewitch_skull_altar': 'assets/sprites/decor/bonewitch_skull_altar.png',
    'brassweir_barrel': 'assets/sprites/decor/brassweir_barrel.png',
    'caravan_wagon': 'assets/sprites/decor/caravan_wagon.png',
    'drowned_idol': 'assets/sprites/decor/drowned_idol.png',
    'echo_glass_shard': 'assets/sprites/decor/echo_glass_shard.png',
    'forgotten_obelisk': 'assets/sprites/decor/forgotten_obelisk.png',
    'inquisitor_pyre_stake': 'assets/sprites/decor/inquisitor_pyre_stake.png',
    'mahnmal_chain': 'assets/sprites/decor/mahnmal_chain.png',
    'mahnmal_pyre': 'assets/sprites/decor/mahnmal_pyre.png',
    'mahnmal_stele': 'assets/sprites/decor/mahnmal_stele.png',
    'monk_meditation_bell': 'assets/sprites/decor/monk_meditation_bell.png',
    'pier_post': 'assets/sprites/decor/pier_post.png',
    'salt_spire': 'assets/sprites/decor/salt_spire.png',
    'seedbearer_torch': 'assets/sprites/decor/seedbearer_torch.png',
    'shulavh_loom': 'assets/sprites/decor/shulavh_loom.png',
    'velharn_mirror': 'assets/sprites/decor/velharn_mirror.png',
    # ---- item_icon ----
    'aschen_ankunft': 'assets/sprites/items/aschen_ankunft.png',
    'brassweir_schaedelbrecher': 'assets/sprites/items/brassweir_schaedelbrecher.png',
    'der_erste_eid': 'assets/sprites/items/der_erste_eid.png',
    'der_schweigende': 'assets/sprites/items/der_schweigende.png',
    'echo_klinge': 'assets/sprites/items/echo_klinge.png',
    'kharns_geduld': 'assets/sprites/items/kharns_geduld.png',
    'letzter_hammer_von_velhost': 'assets/sprites/items/letzter_hammer_von_velhost.png',
    'saatkind_beil': 'assets/sprites/items/saatkind_beil.png',
    'senatorin_stahl': 'assets/sprites/items/senatorin_stahl.png',
    'verbrannte_treue': 'assets/sprites/items/verbrannte_treue.png',
    'wachturm_faust': 'assets/sprites/items/wachturm_faust.png',
    'wurzelschlitzer': 'assets/sprites/items/wurzelschlitzer.png',
    # ---- mob ----
    'aschenbrut_akt_3_generic_mob': 'assets/sprites/mobs/aschenbrut_akt_3_generic_mob.png',
    'ertrunkene_koenigin_akt_6a_boss_mini': 'assets/sprites/mobs/ertrunkene_koenigin_akt_6a_boss_mini.png',
    'glaslord_senator_geist_akt_2': 'assets/sprites/mobs/glaslord_senator_geist_akt_2.png',
    'salzhueter_brut': 'assets/sprites/mobs/salzhueter_brut.png',
    'vehren_echo_akt_3_mini_variante': 'assets/sprites/mobs/vehren_echo_akt_3_mini_variante.png',
    'wurzelhueter_akt_4_generic_mob': 'assets/sprites/mobs/wurzelhueter_akt_4_generic_mob.png',
    # ---- tile ----
    'crypt_floor_a': 'assets/sprites/tiles/crypt_floor_a.png',
    'crypt_floor_c': 'assets/sprites/tiles/crypt_floor_c.png',
    'crypt_wall_w': 'assets/sprites/tiles/crypt_wall_w.png',
    'town_brassweir': 'assets/sprites/tiles/town_brassweir.png',
    # Update #172: Town-Floor 4-Variants (Brassweir-Hafenstein-Refresh)
    'town_floor_a': 'assets/sprites/tiles/town_floor_a.png',
    'town_floor_b': 'assets/sprites/tiles/town_floor_b.png',
    'town_floor_c': 'assets/sprites/tiles/town_floor_c.png',
    'town_floor_d': 'assets/sprites/tiles/town_floor_d.png',
    'town_wall_w':  'assets/sprites/tiles/town_wall_w.png',
}


def sprite_path(target_id: str) -> str | None:
    return SPRITES.get(target_id)
