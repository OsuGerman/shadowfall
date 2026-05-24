"""Sprite-Registry & Aliase (Audit #179 B.3 erweitert).

Diese Datei war urspruenglich von tools/sprite_gen.py generiert und mappte
target-IDs auf PNG-Pfade in assets/sprites/.  Nach dem Procedural-Pivot
(Update #171) ist `SPRITES` ein No-Op-Stub — die Engine rendert procedural.

Update #179 B.3: Vorher waren die Alias-Maps (CLASS, MOB, TILE, PORTRAIT,
BOSS) hardcoded in sf/sprites.py. Jetzt zentralisiert hier — single source
of truth fuer Engine-Key -> Sprite-ID Mappings. Hat 3 Vorteile:
  1. sprites.py kuerzer (weniger Hardcodes im Renderer)
  2. Aenderungen an Mappings nur an einer Stelle
  3. Tools koennen Mappings inspizieren ohne sprites.py importieren

Wenn jemand experimentell wieder PNG-Assets bereitstellt, fuege die in
`SPRITES` ein UND rufe `sf.sprites.set_ai_sprites_enabled(True)` auf.
"""
from __future__ import annotations


SPRITES: dict[str, str] = {}


def sprite_path(target_id: str) -> str | None:
    return SPRITES.get(target_id)


# ============================================================
# ALIAS-MAPS (Engine-Key -> Sprite-ID)
# ============================================================
# Klassen-Aliases: Engine-cls -> Sprite-ID.
# Lore: Sorceress ist die Caster-Klasse (engine: 'mage'),
# Mercenary belegt den Rogue-Slot (engine: 'rogue').
CLASS_SPRITE_ALIAS: dict[str, str] = {
    'mage':  'sorceress',
    'rogue': 'mercenary',
}

# Mob-Aliases: bestiary_key -> Sprite-ID.
# Sprite-IDs aus VELGRAD_SPRITE_BIBEL haben Lore-Suffixe — wir mappen
# die Engine-bestiary-keys auf die generierten PNG-Namen.
MOB_SPRITE_ALIAS: dict[str, str] = {
    'salzhueter_brut':     'salzhueter_brut',
    'glaslord':            'glaslord_senator_geist_akt_2',
    'echo_senator':        'glaslord_senator_geist_akt_2',
    'vehren_echo':         'vehren_echo_akt_3_mini_variante',
    'ertrunkene_koenigin': 'ertrunkene_koenigin_akt_6a_boss_mini',
    'asch_soldat':         'aschenbrut_akt_3_generic_mob',
    'aschenbrut':          'aschenbrut_akt_3_generic_mob',
    'wurzelhueter':        'wurzelhueter_akt_4_generic_mob',
    'mark_krieger':        'wurzelhueter_akt_4_generic_mob',
}

# Tile-Aliases: biome -> Sprite-ID.
TILE_SPRITE_ALIAS: dict[str, str] = {
    'crypt':        'crypt_akt_1',
    'frost':        'frost_glass_ruins_akt_2',
    'lava':         'lava_akt_3',
    'swamp':        'swamp_akt_4',
    'astral':       'astral_akt_5',
    'desert':       'desert_akt_1b',
    'town':         'town_brassweir',
    'wound_salt':   'wound_salt_akt_6a',
    'wound_ash':    'wound_ash_akt_6b',
    'wound_hollow': 'wound_hollow_akt_6c',
    'hollow_word':  'hollow_word_akt_7',
}

# Portrait-Aliases: NPC-Voice-Key -> Sprite-ID (Lore-Beschreibungs-Slugs).
PORTRAIT_ALIAS: dict[str, str] = {
    'korven':       'korven_vor_soeldnermeister',
    'helst':        'bruder_helst_der_hundertjaehrige',
    'vossharil':    'vossharil_die_dreimalige',
    'tameris':      'tameris_die_lichtsucherin',
    'otreth':       'otreth_hohlauge_gemcutter',
    'mara':         'mara_die_mahnerin',
    'vehren':       'inquisitor_general_vehren',
    'drei_muetter': 'die_drei_muetter_trias_in_einem_portrait',
}

# Boss-Aliases: encounter-key -> boss_plate Sprite-ID (Cinematic-Intro X-06).
# 1:1-Mappings dokumentieren explizit dass die Keys identisch sind — falls
# das mal divergiert, hat man die einzige zu aktualisierende Stelle hier.
BOSS_ALIAS: dict[str, str] = {
    'salzhueter_brut':     'salzhueter_brut',
    'vehren':              'vehren',
    'senator_geist':       'senator_geist',
    'shulavh':             'shulavh',
    'velharn_trio':        'velharn_trio',
    'ertrunkene_koenigin': 'ertrunkene_koenigin',
    'echo_drache':         'echo_drache',
    'nicht_gott':          'nicht_gott',
}


def resolve_class(cls: str) -> str:
    """Engine-cls -> Sprite-ID (Identity wenn kein Alias)."""
    return CLASS_SPRITE_ALIAS.get(cls, cls)


def resolve_mob(bestiary_key: str) -> str:
    """bestiary_key -> Sprite-ID (Identity wenn kein Alias)."""
    return MOB_SPRITE_ALIAS.get(bestiary_key, bestiary_key)


def resolve_tile(biome: str) -> str:
    """biome -> Sprite-ID (Identity wenn kein Alias)."""
    return TILE_SPRITE_ALIAS.get(biome, biome)


def resolve_portrait(npc_key: str) -> str:
    """NPC-Voice-Key -> Sprite-ID (Identity wenn kein Alias)."""
    return PORTRAIT_ALIAS.get(npc_key, npc_key)


def resolve_boss(encounter_key: str) -> str:
    """encounter_key -> Sprite-ID (Identity wenn kein Alias)."""
    return BOSS_ALIAS.get(encounter_key, encounter_key)
