"""Stand-up Sprites (Quasi-isometrisch): Spieler / Gegner / Bosse.

Konvention: alle draw_X_at(screen, entity, sx, sy) bekommen (sx, sy) als
GROUND/FUSS-Position. Der Sprite wird von dort nach oben (negative Y)
gezeichnet. Das ergibt den "stehende Figur"-Look.

ROADMAP T2.2 (Update #X): AI-Sprite-Atlas-Integration. Wenn fuer eine
Klasse/Mob ein PNG in sf/sprite_registry.py registriert ist, wird der
AI-Sprite gerendert. Procedural-Composit bleibt als Fallback bestehen.
"""

import math
import os
import pygame

from .constants import (
    GOLD, GOLD_BRIGHT, WHITE, BLACK, FIRE, FROST, POISON, CLASSES,
    STATUS_EFFECTS,
)


# ============================================================
# AI-SPRITE-ATLAS (ROADMAP T2.2-B + T2.2-C + T2.2-D)
# ============================================================
# Lazy-load von PNGs aus assets/sprites/, Cache pro target_id.
# Bei fehlender Datei: returnt None → Aufrufer faellt auf Procedural-
# Composit-Renderer zurueck. Kein Hard-Fail.
_SPRITE_CACHE: dict[str, pygame.Surface | None] = {}
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Update #168: Globaler Master-Switch fuer ALLE AI-Sprites.
# Wenn False, returnen ALLE Loader (_load_ai_sprite UND _load_anim_strip)
# sofort None -> Engine zeichnet komplett procedural (Pre-T2.2-Look).
# Default True (AI-Sprites an). Wird von Game.__init__ aus settings['ai_sprites']
# gespiegelt und vom Settings-Modal-Click live umgeschaltet.
# Setting-Toggle ruft set_ai_sprites_enabled() + reload_sprite_cache().
_AI_SPRITES_ENABLED = True


def set_ai_sprites_enabled(enabled: bool) -> None:
    """Setzt den globalen AI-Sprite-Master-Switch.
    Bei Wechsel sollte reload_sprite_cache() folgen damit Caches
    in einen konsistenten Zustand kommen."""
    global _AI_SPRITES_ENABLED
    _AI_SPRITES_ENABLED = bool(enabled)


def ai_sprites_enabled() -> bool:
    """Returnt True wenn AI-Sprites geladen werden, False = pure procedural."""
    return _AI_SPRITES_ENABLED


# Klassen-Aliases (Engine-cls -> Sprite-ID)
CLASS_SPRITE_ALIAS = {
    'mage':  'sorceress',     # Lore: Sorceress ist die Caster-Klasse
    'rogue': 'mercenary',     # Rogue-Slot wird vom Mercenary belegt
}

# Mob-Aliases (bestiary_key -> Sprite-ID)
# Sprite-IDs aus VELGRAD_SPRITE_BIBEL haben Lore-Suffixe — wir mappen
# die Engine-bestiary-keys auf die generierten PNG-Namen.
MOB_SPRITE_ALIAS = {
    'salzhueter_brut': 'salzhueter_brut',
    'glaslord':        'glaslord_senator_geist_akt_2',
    'echo_senator':    'glaslord_senator_geist_akt_2',
    'vehren_echo':     'vehren_echo_akt_3_mini_variante',
    'ertrunkene_koenigin': 'ertrunkene_koenigin_akt_6a_boss_mini',
    'asch_soldat':     'aschenbrut_akt_3_generic_mob',
    'aschenbrut':      'aschenbrut_akt_3_generic_mob',
    'wurzelhueter':    'wurzelhueter_akt_4_generic_mob',
    'mark_krieger':    'wurzelhueter_akt_4_generic_mob',
}

# Tile-Aliases (biome -> Sprite-ID)
TILE_SPRITE_ALIAS = {
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


def _load_ai_sprite(target_id: str) -> pygame.Surface | None:
    """Lazy-load PNG via sf.sprite_registry.sprite_path(). Cached."""
    # Update #168: Master-Switch — wenn aus, alle Loader returnen None.
    # Cache wird nicht angefasst damit beim Wiedereinschalten + reload
    # alles sauber neu geladen wird.
    if not _AI_SPRITES_ENABLED:
        return None
    if target_id in _SPRITE_CACHE:
        return _SPRITE_CACHE[target_id]
    try:
        from . import sprite_registry as _reg
    except ImportError:
        _SPRITE_CACHE[target_id] = None
        return None
    rel = _reg.sprite_path(target_id)
    if not rel:
        _SPRITE_CACHE[target_id] = None
        return None
    abs_path = os.path.join(_PROJECT_ROOT, rel.replace('/', os.sep))
    if not os.path.exists(abs_path):
        _SPRITE_CACHE[target_id] = None
        return None
    try:
        surf = pygame.image.load(abs_path).convert_alpha()
    except Exception:
        _SPRITE_CACHE[target_id] = None
        return None
    _SPRITE_CACHE[target_id] = surf
    return surf


def get_class_sprite(cls: str) -> pygame.Surface | None:
    """Returnt die AI-Klassen-Sprite-Surface oder None (Procedural-Fallback)."""
    sprite_id = CLASS_SPRITE_ALIAS.get(cls, cls)
    return _load_ai_sprite(sprite_id)


# ============================================================
# ANIMATION-SHEETS (Update #164/#165)
# ============================================================
# Convention seit Update #165:
#   assets/sprites/classes/<class>_anims/<anim>/<dir>.png
#     wobei dir in ('down', 'up', 'left', 'right')
#     und anim in ('idle', 'walk', 'attack', 'hit', 'cast', 'death')
#   Fuer non-directional Anims (z.B. death):
#     assets/sprites/classes/<class>_anims/<anim>/all.png
#
# Backward-compat (Update #164):
#   assets/sprites/classes/<class>_walk/<class>_<dir>.png
#   → wird automatisch zu <class>_anims/walk/<dir>.png gemappt
#
# Jedes PNG ist ein horizontaler Strip mit N gleich-breiten Frames.
# N pro Anim siehe sprite_animation.ANIM_CONFIG.
WALK_DIRECTIONS = ('down', 'up', 'left', 'right')
WALK_DIR_ALIAS = {
    'S': 'down', 's': 'down',
    'N': 'up',   'n': 'up',
    'W': 'left', 'w': 'left',
    'E': 'right', 'e': 'right',
}
WALK_FRAMES_PER_STRIP = 8   # Default fuer Walk; andere Anims via ANIM_CONFIG

# Cache: (cls, anim, direction) → list[Surface] der Sub-Frames (oder None)
_ANIM_FRAME_CACHE: dict[tuple[str, str, str], list[pygame.Surface] | None] = {}

# Backward-Compat-Alias (alter Cache-Name)
_WALK_FRAME_CACHE = _ANIM_FRAME_CACHE


def _trim_transparent(surf: pygame.Surface) -> pygame.Surface:
    """Crop alle Aussen-Reihen/Spalten in denen ALLE Pixel alpha=0 sind.
    Engt das Sprite eng um den sichtbaren Charakter ein → fuellt Cell besser.
    Robust gegen vollstaendig leere Surfaces.
    """
    sw, sh = surf.get_size()
    if sw <= 0 or sh <= 0:
        return surf
    bbox = surf.get_bounding_rect()  # native Pygame-Helper, sehr schnell
    if bbox.width <= 0 or bbox.height <= 0:
        return surf
    if bbox.width == sw and bbox.height == sh:
        return surf
    cropped = pygame.Surface((bbox.width, bbox.height), pygame.SRCALPHA)
    cropped.blit(surf, (0, 0), bbox)
    return cropped


# Direction-Fallback-Reihenfolge bei fehlendem Strip (Update #169).
# Wenn der gewuenschte Direction-Strip nicht existiert, versuche diese
# Reihenfolge — vermeidet den hässlichen "static-sprite"-Sprung und
# behaelt visuell durchgehende Animation (auch wenn sie nicht 100%
# directional ist solange nicht alle 4 Strips vorhanden sind).
_DIRECTION_FALLBACK = {
    'down':  ['down', 'up', 'left', 'right'],
    'up':    ['up', 'down', 'left', 'right'],
    'left':  ['left', 'down', 'up', 'right'],
    'right': ['right', 'down', 'up', 'left'],
}


def _anim_strip_path(cls: str, anim: str, direction: str) -> str | None:
    """Findet den Strip-Pfad fuer (cls, anim, direction).

    Sucht in dieser Reihenfolge (erste vorhandene Datei wins):
      1. NEU (Update #165): <cls>_anims/<anim>/<dir>.png (gewuenschte Dir)
      2. NON-DIRECTIONAL:   <cls>_anims/<anim>/all.png  (z.B. death)
      3. BACKWARD (#164):   <cls>_walk/<cls>_<dir>.png  (nur fuer anim='walk')
      4. DIRECTION-FALLBACK (Update #169): andere Directions versuchen
         (z.B. left fehlt → fallback auf down). Vermeidet "Char wechselt
         beim Laufen-nach-Links"-Problem wenn nicht alle 4 Sheets fertig.
    """
    real_cls = CLASS_SPRITE_ALIAS.get(cls, cls)
    base = os.path.join(_PROJECT_ROOT, 'assets', 'sprites', 'classes')
    # 1+2: gewuenschte direction zuerst
    candidates = [
        os.path.join(base, f'{real_cls}_anims', anim, f'{direction}.png'),
        os.path.join(base, f'{real_cls}_anims', anim, 'all.png'),
    ]
    if anim == 'walk':
        # 3: backward-compat alte monk_walk/ Convention
        candidates.append(
            os.path.join(base, f'{real_cls}_walk', f'{real_cls}_{direction}.png'))
    # 4: andere Directions als Fallback
    fallback_order = _DIRECTION_FALLBACK.get(direction, [direction])
    for fb_dir in fallback_order[1:]:  # [0] ist die gewuenschte, schon getestet
        candidates.append(
            os.path.join(base, f'{real_cls}_anims', anim, f'{fb_dir}.png'))
        if anim == 'walk':
            candidates.append(
                os.path.join(base, f'{real_cls}_walk',
                              f'{real_cls}_{fb_dir}.png'))
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def _load_anim_strip(cls: str, anim: str,
                      direction: str) -> list[pygame.Surface] | None:
    """Lazy-load + slice + auto-trim eines Animation-Strips.

    Anzahl Frames bestimmt sich aus sprite_animation.ANIM_CONFIG[anim]['frames'].
    Wenn nicht verfuegbar, fallback auf WALK_FRAMES_PER_STRIP (8).
    """
    # Update #168: Master-Switch respektieren (s. _load_ai_sprite).
    if not _AI_SPRITES_ENABLED:
        return None
    direction = WALK_DIR_ALIAS.get(direction, direction)
    if direction not in WALK_DIRECTIONS:
        return None
    real_cls = CLASS_SPRITE_ALIAS.get(cls, cls)
    key = (real_cls, anim, direction)
    if key in _ANIM_FRAME_CACHE:
        return _ANIM_FRAME_CACHE[key]

    strip_path = _anim_strip_path(cls, anim, direction)
    if strip_path is None:
        _ANIM_FRAME_CACHE[key] = None
        return None
    try:
        strip = pygame.image.load(strip_path)
    except Exception:
        _ANIM_FRAME_CACHE[key] = None
        return None

    # Frame-Count aus ANIM_CONFIG (fallback 8)
    try:
        from .sprite_animation import ANIM_CONFIG
        frame_count = ANIM_CONFIG.get(anim, {}).get(
            'frames', WALK_FRAMES_PER_STRIP)
    except ImportError:
        frame_count = WALK_FRAMES_PER_STRIP

    sw, sh = strip.get_size()
    fw = sw // frame_count
    if fw <= 0:
        _ANIM_FRAME_CACHE[key] = None
        return None

    # Alpha-Premultiplikation: viele AI-Strips speichern transparente Pixel mit
    # RGB=247 (originaler weisser BG, nur Alpha=0). pygame.transform.smoothscale
    # interpoliert bilinear und blendet die weisse RGB-Komponente in die Kanten
    # -> sichtbarer Weiss-Halo um den Charakter. Wir nullen RGB fuer alpha=0.
    try:
        import numpy as _np
        a = pygame.surfarray.pixels_alpha(strip)
        rgb = pygame.surfarray.pixels3d(strip)
        mask = a == 0
        if bool(mask.any()):
            rgb[mask] = 0
        del a, rgb
    except Exception:
        pass

    # Update #175 (Animation-Jitter-Fix): Trim mit UNION-BBox ueber ALLE 8
    # Frames. Vorher: per-Frame eigene BBox → unterschiedliche Frame-Breiten
    # → Char "springt" zwischen Frames weil target_h-Skalierung verschiedene
    # End-Breiten produziert. Jetzt: bbox = max-union → konsistente
    # Frame-Dimensions ueber den ganzen Cycle.
    raw_frames: list[pygame.Surface] = []
    for i in range(frame_count):
        sub = pygame.Surface((fw, sh), pygame.SRCALPHA)
        sub.blit(strip, (0, 0), (i * fw, 0, fw, sh))
        raw_frames.append(sub)
    # Union-BBox: min(x), min(y), max(x+w), max(y+h)
    union_bbox = None
    for f in raw_frames:
        bb = f.get_bounding_rect()
        if bb.width <= 0 or bb.height <= 0:
            continue
        if union_bbox is None:
            union_bbox = pygame.Rect(bb.x, bb.y, bb.width, bb.height)
        else:
            x1 = min(union_bbox.x, bb.x)
            y1 = min(union_bbox.y, bb.y)
            x2 = max(union_bbox.x + union_bbox.width,  bb.x + bb.width)
            y2 = max(union_bbox.y + union_bbox.height, bb.y + bb.height)
            union_bbox = pygame.Rect(x1, y1, x2 - x1, y2 - y1)
    # Crop alle Frames auf die SELBE union-bbox
    frames: list[pygame.Surface] = []
    if union_bbox is not None and (union_bbox.width < fw or union_bbox.height < sh):
        for f in raw_frames:
            cropped = pygame.Surface(
                (union_bbox.width, union_bbox.height), pygame.SRCALPHA)
            cropped.blit(f, (0, 0), union_bbox)
            frames.append(cropped)
    else:
        frames = raw_frames
    _ANIM_FRAME_CACHE[key] = frames
    return frames


def get_class_anim_frame(cls: str, anim: str, direction: str,
                          frame_idx: int) -> pygame.Surface | None:
    """Returnt einen Sub-Frame aus dem Anim-Strip. Cached.

    Args:
        cls:        Klassen-Slug (z.B. 'monk')
        anim:       'idle'|'walk'|'attack'|'hit'|'cast'|'death'
        direction:  'down'|'up'|'left'|'right' oder 'S'|'N'|'W'|'E'
        frame_idx:  0..N-1, wird modulo gerechnet (safe)

    Returns:
        Surface oder None wenn kein Sheet fuer (cls, anim, direction)
        registriert. Aufrufer faellt dann auf statisches Sprite + procedural
        Visual-Effect zurueck.
    """
    frames = _load_anim_strip(cls, anim, direction)
    if not frames:
        return None
    return frames[frame_idx % len(frames)]


def has_anim(cls: str, anim: str) -> bool:
    """True wenn fuer (cls, anim) mind. 1 Direction-Strip existiert."""
    for d in WALK_DIRECTIONS:
        if _anim_strip_path(cls, anim, d) is not None:
            return True
    return False


# ---- Backward-Compat-Wrappers fuer Update #164-API ----
def _load_walk_strip(cls: str, direction: str) -> list[pygame.Surface] | None:
    """Backward-compat alias — ruft generischen Loader fuer 'walk'."""
    return _load_anim_strip(cls, 'walk', direction)


def get_class_walk_frame(cls: str, direction: str,
                          frame_idx: int) -> pygame.Surface | None:
    """Backward-compat alias — ruft generischen Loader fuer 'walk'."""
    return get_class_anim_frame(cls, 'walk', direction, frame_idx)


def has_walk_animation(cls: str) -> bool:
    """Backward-compat — True wenn cls eine Walk-Anim hat."""
    return has_anim(cls, 'walk')


def direction_from_velocity(vx: float, vy: float) -> str:
    """Mappt (vx, vy)-Velocity auf 'down'|'up'|'left'|'right'.

    Top-Down-ARPG-Konvention:
      vy > 0 = nach unten (S, 'down')
      vy < 0 = nach oben  (N, 'up')
      vx > 0 = nach rechts (E, 'right')
      vx < 0 = nach links  (W, 'left')

    Wenn |vx| > |vy|: horizontal dominiert, sonst vertikal.
    """
    if vx == 0 and vy == 0:
        return 'down'   # Idle-Fallback: schaut Kamera an
    if abs(vx) > abs(vy):
        return 'right' if vx > 0 else 'left'
    return 'down' if vy > 0 else 'up'


def direction_from_facing(facing_rad: float) -> str:
    """Mappt atan2-Winkel auf 'down'|'up'|'left'|'right'.

    Engine-Convention (sf/entities.Player.facing):
      facing = atan2(diff.y, diff.x) — Screen-Y ist nach unten positiv.

    Mapping:
      facing in [-pi/4,  pi/4]  → 'right' (E)
      facing in [ pi/4,  3pi/4] → 'down'  (S, screen-Y+ ist unten)
      facing in [-3pi/4, -pi/4] → 'up'    (N)
      sonst                      → 'left' (W)
    """
    import math
    pi = math.pi
    f = math.atan2(math.sin(facing_rad), math.cos(facing_rad))  # normalize [-pi, pi]
    if -pi / 4 <= f <= pi / 4:
        return 'right'
    if pi / 4 < f < 3 * pi / 4:
        return 'down'
    if -3 * pi / 4 < f < -pi / 4:
        return 'up'
    return 'left'


def get_mob_sprite(bestiary_key: str | None) -> pygame.Surface | None:
    """Returnt AI-Mob-Sprite oder None."""
    if not bestiary_key:
        return None
    sprite_id = MOB_SPRITE_ALIAS.get(bestiary_key, bestiary_key)
    return _load_ai_sprite(sprite_id)


def get_tile_sprite(biome: str | None) -> pygame.Surface | None:
    """Returnt AI-Tile-Surface fuer biome oder None.

    Sucht zuerst die alte Single-Tile-ID (biome.png), fuer Backward-Compat.
    Variants werden via get_tile_variant() abgerufen (siehe unten).
    """
    if not biome:
        return None
    sprite_id = TILE_SPRITE_ALIAS.get(biome, biome)
    return _load_ai_sprite(sprite_id)


# Tile-Variants pro Biome (T1a/T1b/T1c/T1d). Wird verwendet wenn
# vorhanden — sonst Fallback auf Single-Tile via get_tile_sprite().
TILE_VARIANT_MAP = {
    # Update: Variants temporaer auf nur 1 reduziert (User-Feedback
    # 2026-05-24: 4 Variants ergaben optisches Patchwork — Variants b/c/d
    # hatten Farb-/Mood-Mismatches. Variant a hat den staerksten Crypt-Salz-Look.
    # Re-Generation mit harmonisierten Prompts oder Asset-Pack-Switch
    # offen — siehe ROADMAP T2.5.
    'crypt':  ['crypt_floor_a'],
    # Update #172 (Town-Tile-Refresh): Brassweir-Hafenstein-Floor mit
    # 4 generierten Variants (a/b/c/d via rotation + tint-shifts).
    # Wie crypt: nur Variant-a aktiv damit kein Patchwork-Look entsteht.
    # Andere Variants in sprite_registry.py registriert fuer spaetere
    # Hash-Picker-Aktivierung wenn Variants harmonisch zusammenpassen.
    'town':   ['town_floor_a'],
}

TILE_WALL_MAP = {
    # Update #170: All-Biome Crypt-Style Rollout. Per-Biom unique Walls
    # via tools/wall_from_floor.py mit biom-spezifischen Algorithmen
    # (joint-pattern fuer crypt/town, crystal-spikes fuer frost/wound_salt,
    # crack-glow fuer lava/wound_ash, diagonal-veins fuer swamp/wound_hollow,
    # star-specks fuer astral, horizontal-strata fuer desert, rune-glyphs
    # fuer hollow_word).
    'crypt':        'crypt_wall_w',
    'frost':        'frost_wall_w',
    'lava':         'lava_wall_w',
    'swamp':        'swamp_wall_w',
    'astral':       'astral_wall_w',
    'desert':       'desert_wall_w',
    'town':         'town_wall_w',
    'wound_salt':   'wound_salt_wall_w',
    'wound_ash':    'wound_ash_wall_w',
    'wound_hollow': 'wound_hollow_wall_w',
    'hollow_word':  'hollow_word_wall_w',
}


def get_tile_variants(biome: str | None) -> list[pygame.Surface]:
    """Returnt alle verfuegbaren Tile-Variants fuer biome.
    Leere Liste wenn keine Variants registriert oder geladen werden konnten."""
    if not biome:
        return []
    ids = TILE_VARIANT_MAP.get(biome, [])
    surfs = []
    for tid in ids:
        s = _load_ai_sprite(tid)
        if s is not None:
            surfs.append(s)
    return surfs


def get_wall_sprite(biome: str | None) -> pygame.Surface | None:
    """Returnt Wall-Tile-Surface fuer biome (T<biome>w-PNG)."""
    if not biome:
        return None
    wid = TILE_WALL_MAP.get(biome)
    return _load_ai_sprite(wid) if wid else None


# ============================================================
# PRIO-PASS HOCH (VELGRAD_SPRITE_BIBEL §XI/§XII/§XIII)
# ============================================================
# 3 neue Sprite-Familien werden hier zentral geladen, alle mit silent-
# fallback auf Procedural-Renderer wenn das PNG (noch) nicht existiert.
#
#   §XI  Decor (17)         → get_decor_sprite(kind)
#   §XII Item-Uniques (50)  → get_item_unique_icon(name_or_slug)
#   §XIII Status-Icons (15) → get_status_icon(key)
#
# Sprite-IDs kommen 1:1 aus der Bibel via tools/sprite_gen.py.

# Optional-Aliases: erlauben dass Engine-interne Kind-Strings auf einen
# Lore-spezifischeren Bibel-Slug mappen.  Beispiel: 'lantern' in den
# Town-Biomes nutzt die Brassweir-Lore-Lampe falls vorhanden.
DECOR_SPRITE_ALIAS = {
    # Engine-kind → Bibel-slug (leer = direkter 1:1-Lookup)
    # Erweitere hier wenn neue Lore-Sprites alte Procedural-Kinds ersetzen
    # sollen (z.B. 'lantern' → 'seedbearer_torch' in Sumpf-Biom).
}

# Status-Slugs sind 1:1 mit STATUS_EFFECTS-Keys in constants.py
# (burn/poison/frost/bleed/shock/chill/brittle/sapped/armour_break/
#  pinned/maim/crush/stun/slow/silence).
STATUS_ICON_ALIAS: dict[str, str] = {}

# 50 Lore-Uniques aus VELGRAD_ITEMS_UNIQUE_BIBEL.md.  Sprite-IDs
# entsprechen 1:1 den U1..U50-Headern in VELGRAD_SPRITE_BIBEL §XII.
# Wenn ein Item.name (deutsche Schreibweise) zu einem dieser Slugs
# slugifiziert → wird der AI-Icon geladen.
UNIQUE_ITEM_SLUGS: frozenset[str] = frozenset({
    # Maces
    'kharns_geduld', 'aschen_ankunft', 'letzter_hammer_von_velhost',
    'der_schweigende', 'wachturm_faust',
    # Swords
    'echo_klinge', 'verbrannte_treue', 'senatorin_stahl', 'der_erste_eid',
    # Axes
    'wurzelschlitzer', 'saatkind_beil', 'brassweir_schaedelbrecher',
    # Daggers
    'vossharils_bruder', 'hohle_zunge', 'tintendolch_von_im_nesh',
    'der_zweite_atem',
    # Spears
    'tameris_suchender', 'zhar_eth_mondbinder', 'faden_spitze',
    'der_sechzehnte', 'sturmspeer_von_veh',
    # Quarterstaves
    'drei_pagoden', 'der_atemzaehler', 'schlafsplitter',
    'bambus_des_schweigens', 'letzter_schritt',
    # Bows
    'saatwaechter', 'erinnerungs_bogen_von_saath', 'tannenbein',
    'der_unbeschriebene',
    # Crossbows
    'mahnmal_marke_vii', 'korvens_wahrheit', 'der_letzte_hauch',
    'verraten_sieben', 'eisenfaust_repetier',
    # Wands
    'funken_fluch', 'asche_aspekt', 'tintenfeder_von_im_nesh',
    # Sceptres
    'bischof_schwur', 'spirit_anker', 'hohlauges_erbe',
    # Staves
    'sieben_atem_stab', 'glasgoldener_zepter_stab', 'wurzelmark_stuetze',
    'vergessens_brand',
    # Talismans
    'drei_tier_anhaenger', 'baerenhirten_kette', 'wolfsmond_amulett',
    # Special / Story
    'kharns_traene', 'der_achte',
})


def _slug_unique_name(name: str) -> str:
    """Slugifiziert einen Item-Namen 1:1 wie tools/sprite_gen._slug().
    Wird hier dupliziert um ImportError-Cycle zu vermeiden (tools/ ist
    nicht garantiert auf dem sys.path zur Runtime)."""
    s = (name or '').lower().strip()
    # Erst Umlaute substituieren BEVOR regex-strippt (sonst werden ä etc.
    # auf die Punktklasse [^\w] gematcht und entfernt — wir wollen sie
    # zu ae/oe/ue umwandeln).
    s = s.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue')
    s = s.replace('ß', 'ss')
    import re as _re
    s = _re.sub(r"[^\w\s-]", '', s, flags=_re.UNICODE)
    s = _re.sub(r"[-\s]+", '_', s)
    return s.strip('_')


def get_decor_sprite(kind: str | None) -> pygame.Surface | None:
    """§XI: Returnt AI-Decor-Sprite oder None (→ Procedural-Fallback in world.draw_decor)."""
    if not kind:
        return None
    sprite_id = DECOR_SPRITE_ALIAS.get(kind, kind)
    return _load_ai_sprite(sprite_id)


def get_status_icon(key: str | None) -> pygame.Surface | None:
    """§XIII: Returnt AI-Status-Icon oder None (→ Procedural-Circle in _status_overlay)."""
    if not key:
        return None
    sprite_id = STATUS_ICON_ALIAS.get(key, key)
    return _load_ai_sprite(sprite_id)


def get_item_unique_icon(name_or_slug: str | None) -> pygame.Surface | None:
    """§XII: Returnt AI-Item-Icon für ein Unique oder None.

    Akzeptiert sowohl den deutschen Item-Namen ("Kharns Geduld") als
    auch den slug ("kharns_geduld").  Items die nicht zu den 50 Bibel-
    Uniques gehören returnen None (→ Slot-basiertes Procedural-Icon).
    """
    if not name_or_slug:
        return None
    slug = name_or_slug if name_or_slug in UNIQUE_ITEM_SLUGS \
        else _slug_unique_name(name_or_slug)
    if slug not in UNIQUE_ITEM_SLUGS:
        return None
    return _load_ai_sprite(slug)


# ============================================================
# EDGE-OVERLAY-SYSTEM (Auto-Tile-Light, Update #160)
# ============================================================
# Statt 47-Mask-Tilesets generieren wir prozedural pro Biom Edge-Shadow-
# Overlays die ueber Floor-Cells geblittet werden wenn diese an Walls
# grenzen. Das produziert den modularen "POE2-/Hades-/D2-Look" mit nur
# einem Floor + einem Wall-Tile pro Biom.
#
# Bitmask-Konvention (4-direction NESW):
#   N = 1 (north neighbor is wall)
#   E = 2
#   S = 4
#   W = 8
# Es gibt 16 Patterns (0..15). Wir cachen pro (biome, cell, mask).
#
# Optional: 8-direction mit NE/NW/SE/SW corners — fuer V1 bleiben wir
# bei 4-direction (16 patterns, reicht fuer den optischen Gewinn).

_EDGE_OVERLAY_CACHE: dict[tuple, pygame.Surface] = {}

EDGE_SHADOW_DEPTH_FRAC = 0.32   # Schatten reicht 32% der Cell-Tiefe ins Floor
EDGE_SHADOW_ALPHA_MAX  = 170    # Wand-anliegend (0..255)
EDGE_SHADOW_ALPHA_MIN  = 0      # Innen-Cell-Mitte (vollstaendig transparent)


def _build_edge_overlay(cell_size: int, mask: int,
                        wall_avg_rgb: tuple[int, int, int] | None = None
                        ) -> pygame.Surface:
    """Baut eine cell+1 grosse Surface mit Edge-Shadow-Gradient.

    Fuer jede gesetzte Mask-Bit (N/E/S/W) wird auf der entsprechenden
    Kante ein Dunkel-Gradient gezeichnet, der zur Cell-Mitte hin in
    Transparenz uebergeht. Schattenfarbe optional getoent durch
    wall_avg_rgb (Color-Bleed wie in painted ARPGs).
    """
    size = cell_size + 1
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    if mask == 0:
        return surf

    depth = max(2, int(cell_size * EDGE_SHADOW_DEPTH_FRAC))
    a_max = EDGE_SHADOW_ALPHA_MAX
    a_min = EDGE_SHADOW_ALPHA_MIN
    # Schattenfarbe: schwarz, optional leicht mit Wand-Avg getoent (15%)
    if wall_avg_rgb is not None:
        r0, g0, b0 = wall_avg_rgb
        # 85% schwarz + 15% Wand-Farbe → faktisch dunkler Stein-Schatten
        sr = int(r0 * 0.15)
        sg = int(g0 * 0.15)
        sb = int(b0 * 0.15)
    else:
        sr = sg = sb = 0

    # Pro gesetzter Bit eine Gradient-Linie
    # N (top edge)
    if mask & 1:
        for d in range(depth):
            t = d / max(1, depth - 1)
            a = int(a_max * (1.0 - t) + a_min * t)
            if a <= 0:
                continue
            pygame.draw.line(surf, (sr, sg, sb, a),
                             (0, d), (size - 1, d), 1)
    # E (right edge)
    if mask & 2:
        for d in range(depth):
            t = d / max(1, depth - 1)
            a = int(a_max * (1.0 - t) + a_min * t)
            if a <= 0:
                continue
            x = size - 1 - d
            pygame.draw.line(surf, (sr, sg, sb, a),
                             (x, 0), (x, size - 1), 1)
    # S (bottom edge)
    if mask & 4:
        for d in range(depth):
            t = d / max(1, depth - 1)
            a = int(a_max * (1.0 - t) + a_min * t)
            if a <= 0:
                continue
            y = size - 1 - d
            pygame.draw.line(surf, (sr, sg, sb, a),
                             (0, y), (size - 1, y), 1)
    # W (left edge)
    if mask & 8:
        for d in range(depth):
            t = d / max(1, depth - 1)
            a = int(a_max * (1.0 - t) + a_min * t)
            if a <= 0:
                continue
            pygame.draw.line(surf, (sr, sg, sb, a),
                             (d, 0), (d, size - 1), 1)
    return surf


def _wall_average_rgb(biome: str) -> tuple[int, int, int] | None:
    """Berechnet Avg-RGB der Wand-Textur fuer Color-Bleed-Schatten.
    Cached pro Biome."""
    key = ('_wall_avg', biome)
    if key in _WALL_AVG_CACHE:
        return _WALL_AVG_CACHE[key]
    wall = get_wall_sprite(biome)
    if wall is None:
        _WALL_AVG_CACHE[key] = None
        return None
    # Sample 16x16 grid, average
    sw, sh = wall.get_size()
    rs = gs = bs = 0
    n = 0
    step_x = max(1, sw // 16)
    step_y = max(1, sh // 16)
    for y in range(0, sh, step_y):
        for x in range(0, sw, step_x):
            try:
                r, g, b, *_ = wall.get_at((x, y))
            except Exception:
                continue
            rs += r
            gs += g
            bs += b
            n += 1
    if n <= 0:
        _WALL_AVG_CACHE[key] = None
        return None
    avg = (rs // n, gs // n, bs // n)
    _WALL_AVG_CACHE[key] = avg
    return avg


_WALL_AVG_CACHE: dict[tuple, tuple[int, int, int] | None] = {}


def get_edge_overlay(biome: str, mask: int, cell_size: int
                     ) -> pygame.Surface | None:
    """Returnt gecachtes Edge-Shadow-Overlay fuer (biome, mask, cell).

    mask = 4-Bit Bitmask NESW. mask == 0 → None (kein Schatten noetig).
    Wird nur erzeugt wenn Biome ein Wall-Tile registriert hat (sonst
    bleibt 3D-Procedural-Look aktiv).
    """
    if mask == 0:
        return None
    if biome not in TILE_WALL_MAP:
        return None
    key = (biome, cell_size, mask)
    surf = _EDGE_OVERLAY_CACHE.get(key)
    if surf is not None:
        return surf
    wall_avg = _wall_average_rgb(biome)
    surf = _build_edge_overlay(cell_size, mask, wall_avg)
    _EDGE_OVERLAY_CACHE[key] = surf
    return surf


def get_portrait(npc_key: str | None) -> pygame.Surface | None:
    """Returnt NPC-Portrait fuer Dialog-UI. Mapping ueber Voice-Keys."""
    if not npc_key:
        return None
    # Portrait-Sprite-IDs aus Manifest sind Lore-Beschreibungs-Slugs
    PORTRAIT_ALIAS = {
        'korven':       'korven_vor_soeldnermeister',
        'helst':        'bruder_helst_der_hundertjaehrige',
        'vossharil':    'vossharil_die_dreimalige',
        'tameris':      'tameris_die_lichtsucherin',
        'otreth':       'otreth_hohlauge_gemcutter',
        'mara':         'mara_die_mahnerin',
        'vehren':       'inquisitor_general_vehren',
        'drei_muetter': 'die_drei_muetter_trias_in_einem_portrait',
    }
    sprite_id = PORTRAIT_ALIAS.get(npc_key, npc_key)
    return _load_ai_sprite(sprite_id)


def get_boss_plate(encounter_key: str | None) -> pygame.Surface | None:
    """Returnt Boss-Concept-Plate fuer Cinematic-Intro (X-06)."""
    if not encounter_key:
        return None
    # Boss-Encounter-Keys mappen 1:1 zu boss_plate-Sprite-IDs
    BOSS_ALIAS = {
        'salzhueter_brut':     'salzhueter_brut',
        'vehren':              'vehren',
        'senator_geist':       'senator_geist',
        'shulavh':             'shulavh',
        'velharn_trio':        'velharn_trio',
        'ertrunkene_koenigin': 'ertrunkene_koenigin',
        'echo_drache':         'echo_drache',
        'nicht_gott':          'nicht_gott',
    }
    sprite_id = BOSS_ALIAS.get(encounter_key, encounter_key)
    return _load_ai_sprite(sprite_id)


def _draw_ai_sprite_at(screen, surf: pygame.Surface, sx: int, sy: int,
                        target_height: int) -> None:
    """Zeichnet die AI-Sprite-Surface so dass deren Fuesse bei (sx, sy) sind
    und Hoehe `target_height` ist. Behaelt Aspect-Ratio bei."""
    _draw_ai_sprite_at_with_fx(screen, surf, sx, sy, target_height)


def _draw_ai_sprite_at_with_fx(screen, surf: pygame.Surface, sx: int, sy: int,
                                target_height: int, *,
                                fx_kind: str = '',
                                fx_progress: float = 0.0,
                                cls: str = '') -> None:
    """Render AI-Sprite + optional procedural Visual-Effect waehrend One-
    Shot-Anim laeuft.

    fx_kind:
        ''       → kein Effect, normales Render
        'attack' → leichter Scale-Pulse + Forward-Shake
        'hit'    → Red-Tint-Flash + Backward-Shake
        'cast'   → Aspekt-Aura-Glow (Klassen-Farbe)
        'death'  → Slide-Down + Fade-Out

    fx_progress: 0.0..1.0 — wie weit die Anim durch ist (von anim_state.progress())
    """
    import math as _m
    sw, sh = surf.get_size()
    if sh <= 0:
        return

    # Effect-Modulation berechnen
    scale_mult = 1.0
    shake_x = 0
    shake_y = 0
    tint = None       # (r, g, b, a) overlay
    alpha = 255
    glow = None       # (r, g, b, a) outer aura

    if fx_kind == 'attack':
        # Wind-up (0.0-0.5): leichter Pull-Back (Scale 0.95)
        # Strike (0.5-0.8): Scale-Pulse auf 1.1 + forward shake
        # Recovery (0.8-1.0): zurueck auf 1.0
        if fx_progress < 0.5:
            scale_mult = 1.0 - 0.05 * (fx_progress / 0.5)
        elif fx_progress < 0.8:
            t = (fx_progress - 0.5) / 0.3
            scale_mult = 0.95 + 0.15 * t   # 0.95 → 1.10
            shake_x = int(_m.sin(fx_progress * 30) * 3)
        else:
            scale_mult = 1.10 - 0.10 * ((fx_progress - 0.8) / 0.2)
    elif fx_kind == 'hit':
        # Strong red flash + backward shake
        flash_intensity = max(0.0, 1.0 - fx_progress * 1.2)
        tint = (255, 60, 60, int(180 * flash_intensity))
        shake_x = int(_m.sin(fx_progress * 40) * 4 * (1.0 - fx_progress))
        scale_mult = 0.98
    elif fx_kind == 'cast':
        # Aspekt-Aura: pulsing glow around sprite, Klassen-Farbe
        try:
            from . import aspects as _asp
            pal = _asp.aspect_palette(cls)
            r, g, b = pal['bright']
        except Exception:
            r, g, b = 200, 180, 255
        puls = abs(_m.sin(fx_progress * _m.pi * 2))
        glow_alpha = int(120 * (0.4 + 0.6 * puls))
        glow = (r, g, b, glow_alpha)
        # Slight scale-up at climax
        scale_mult = 1.0 + 0.05 * puls
    elif fx_kind == 'death':
        # Slide down + fade out
        slide_px = int(target_height * 0.5 * fx_progress)
        sy = sy + slide_px
        alpha = max(0, int(255 * (1.0 - fx_progress * 0.7)))
        # Slight horizontal collapse
        scale_mult = max(0.3, 1.0 - fx_progress * 0.4)

    # Skalieren
    final_h = max(1, int(target_height * scale_mult))
    scale = final_h / sh
    new_w = max(1, int(sw * scale))
    scaled = pygame.transform.smoothscale(surf, (new_w, final_h))

    # Alpha anwenden
    if alpha < 255:
        scaled = scaled.copy()
        scaled.set_alpha(alpha)

    # Tint overlay (z.B. red-flash bei Hit) — wird auf den scaled drauf-multipliziert
    if tint is not None and tint[3] > 0:
        tint_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
        tint_surf.fill(tint)
        scaled = scaled.copy()
        scaled.blit(tint_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

    blit_x = sx - new_w // 2 + shake_x
    blit_y = sy - final_h + shake_y

    # Glow draufzeichnen UNTER den Sprite
    if glow is not None and glow[3] > 0:
        glow_radius = max(new_w, final_h) // 2 + 12
        glow_surf = pygame.Surface(
            (glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, glow,
                            (glow_radius, glow_radius), glow_radius)
        screen.blit(glow_surf,
                     (sx - glow_radius, sy - final_h // 2 - glow_radius))

    screen.blit(scaled, (blit_x, blit_y))


def reload_sprite_cache() -> None:
    """F5-Hot-Reload: Cache leeren, neue Sprites werden beim naechsten
    Draw automatisch geladen. Praktisch wenn man via tools/sprite_gen.py
    re-generiert und das Game laeuft."""
    _SPRITE_CACHE.clear()
    _EDGE_OVERLAY_CACHE.clear()
    _WALL_AVG_CACHE.clear()
    _WALK_FRAME_CACHE.clear()
    # Prio-Pass HOCH (VELGRAD_SPRITE_BIBEL §XII/§XIII):
    # Scaled-Caches der neuen Sprite-Familien
    _STATUS_ICON_SCALED.clear()
    _UNIQUE_ICON_SCALED.clear()


# ============================================================
# PLAN O-01 (Update #100): Sprite-Rig-Foundation
# ============================================================
# Pygame hat keine echten Skeleton-Rigs (Spine/Skeleton2D), aber wir
# können eine simple Bone-Hierarchie als Datenstruktur anbieten — Body-
# Joints (head/torso/arms/legs) mit Offset, die per-Frame durch
# Anim-States moduliert werden.  O-02..O-11 bauen auf dieser Struktur
# auf, sobald Sprite-Sheets / Procedural-Drawing umgestellt sind.
class SpriteRig:
    """Minimaler Bone-Layer für Hit-Reactions, IK und Aim-Offset.

    Joints in lokalem Space (Offsets relativ zum Body-Anchor = `sx, sy`):
        head, torso, left_arm, right_arm, left_leg, right_leg

    Modifizierbare State-Felder:
        hit_offset_x, hit_offset_y   — temporärer Knockback-Versatz
        aim_offset_x, aim_offset_y   — Bow/Crossbow-Aim (O-04)
        recoil                       — Rückstoß-Wert (0..1)
        time_scale                   — Animation-Speed (O-09)

        Root-Motion (O-02):
        root_vx, root_vy             — Root-Velocity (Slam/Charge/Dash)
        root_motion_left             — Restzeit der Root-Motion-Phase

        Inertia + Wind (O-11):
        inertia_x, inertia_y         — Akkumulierte Movement-Inertia
        wind_phase                   — Wind-Cloth-Sim-Phase (sinus-treiber)
    """
    __slots__ = ('hit_offset_x', 'hit_offset_y',
                 'aim_offset_x', 'aim_offset_y',
                 'recoil', 'time_scale',
                 'last_hit_dir',
                 'root_vx', 'root_vy', 'root_motion_left',
                 'inertia_x', 'inertia_y',
                 'wind_phase',
                 'squash_y', 'stretch_left')

    def __init__(self):
        self.hit_offset_x = 0.0
        self.hit_offset_y = 0.0
        self.aim_offset_x = 0.0
        self.aim_offset_y = 0.0
        self.recoil = 0.0
        self.time_scale = 1.0
        self.last_hit_dir = None  # 'N'|'E'|'S'|'W' für O-06 Hit-Reactions
        # O-02 Root-Motion
        self.root_vx = 0.0
        self.root_vy = 0.0
        self.root_motion_left = 0.0
        # O-11 Procedural-Layers
        self.inertia_x = 0.0
        self.inertia_y = 0.0
        self.wind_phase = 0.0
        # M-22 (Update #168): Sprite-Squash-and-Stretch on Movement.
        # squash_y = vertical-scale-Multiplier (1.0 = normal, 0.85 = squashed)
        # stretch_left = Restzeit fuer den Squash-Effekt nach Landung.
        self.squash_y = 1.0
        self.stretch_left = 0.0

    def tick(self, dt):
        # Decay aller Modifikatoren auf 0
        decay = dt * 6.0
        self.hit_offset_x *= max(0.0, 1.0 - decay)
        self.hit_offset_y *= max(0.0, 1.0 - decay)
        self.recoil = max(0.0, self.recoil - dt * 2.0)
        # O-02 Root-Motion: Restzeit dekrementieren
        if self.root_motion_left > 0:
            self.root_motion_left = max(0.0, self.root_motion_left - dt)
            if self.root_motion_left <= 0:
                self.root_vx = 0.0
                self.root_vy = 0.0
        # O-11 Inertia-Decay + Wind-Sim
        self.inertia_x *= max(0.0, 1.0 - dt * 4.0)
        self.inertia_y *= max(0.0, 1.0 - dt * 4.0)
        self.wind_phase = (self.wind_phase + dt * 1.5) % math.tau
        # M-22 Squash decay
        if self.stretch_left > 0:
            self.stretch_left = max(0.0, self.stretch_left - dt)
            if self.stretch_left <= 0:
                self.squash_y = 1.0

    def trigger_squash(self, intensity=0.85, duration=0.08):
        """M-22 (Update #168): Trigger sprite-squash (z.B. Landung nach
        Dodge oder Jump-Land).  Intensity 1.0 = no squash, 0.85 = 15%
        vertical-squash.
        """
        self.squash_y = max(0.7, min(1.0, intensity))
        self.stretch_left = duration

    def push_root_motion(self, vx, vy, duration):
        """O-02: Initiiert Root-Motion. Spawnt einen Velocity-Vector der
        über `duration` Sekunden ausgegeben wird (Slam/Charge/Dash)."""
        self.root_vx = vx
        self.root_vy = vy
        self.root_motion_left = duration

    def apply_inertia(self, vx, vy):
        """O-11: Akkumuliert Movement-Inertia (Anti-Pop-Blending)."""
        self.inertia_x += vx * 0.15
        self.inertia_y += vy * 0.15


def aim_offset_for_movement(player_speed_x, player_speed_y, weapon_type='bow'):
    """PLAN O-04 (Update #101): Additive-Layer Aim-Offset.

    Bei Bow/Crossbow während Movement wird der Aim-Punkt leicht in
    Bewegungsrichtung versetzt, was den „Compensating-Aim"-Look gibt.
    """
    if weapon_type not in ('bow', 'crossbow'):
        return (0.0, 0.0)
    # Aim-Offset ist 10 % der Movement-Velocity, weggekappt
    ox = max(-8.0, min(8.0, player_speed_x * 0.10))
    oy = max(-8.0, min(8.0, player_speed_y * 0.10))
    return (ox, oy)


def hand_ik_grip(rig, weapon_type='one_handed'):
    """PLAN O-03 (Update #101): Hand-IK-Helper für Two-Handed-Grip.

    Returnt ein dict {left_hand: (x, y), right_hand: (x, y)} mit
    Sprite-Joints-Offsets für die jeweilige Waffen-Klasse.
    """
    if weapon_type == 'two_handed':
        return {'left_hand': (-6, -2), 'right_hand': (6, -2)}
    elif weapon_type == 'bow':
        return {'left_hand': (-8, -4), 'right_hand': (0, -6)}
    elif weapon_type == 'crossbow':
        return {'left_hand': (-4, -3), 'right_hand': (8, -3)}
    return {'left_hand': (-5, 0), 'right_hand': (5, 0)}


def get_rig(entity):
    """Lazy-Factory — gibt das `_rig`-Attribut eines Entity zurück,
    legt es bei Bedarf an. O-01-konformer Zugriff."""
    rig = getattr(entity, '_rig', None)
    if rig is None:
        rig = SpriteRig()
        entity._rig = rig
    return rig


# ============================================================
# Hilfsfunktionen
# ============================================================
def _shade(color, factor):
    return tuple(max(0, min(255, int(c * factor))) for c in color[:3])


def _tint(color, hit_flash):
    return WHITE if hit_flash > 0 else color


def _ground_shadow(screen, sx, sy, w, alpha=120):
    """Elliptischer Schatten direkt am Boden."""
    h = max(6, w // 3)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), (0, 0, w, h))
    screen.blit(s, (sx - w // 2, sy - h // 2))


def _leg_bob(walk_phase):
    """Returnt (left_offset, right_offset) für Beinanimation."""
    s = math.sin(walk_phase)
    return -int(s * 4), int(s * 4)


def _status_overlay(screen, sx, sy, h, status):
    """Zeichnet Status-Icons über dem Sprite.

    Prio-Pass HOCH (VELGRAD_SPRITE_BIBEL §XIII): wenn ein 64×64-AI-Icon
    für den Status-Key in assets/sprites/status/<key>.png liegt, wird es
    auf 12×12 runterskaliert geblittet.  Sonst Procedural-Kreis (Legacy-
    Fallback).  Stack-Pixel bleiben in beiden Fällen identisch.
    """
    if not status:
        return
    icons_y = sy - h - 18
    n = len(status)
    for i, (key, st) in enumerate(status.items()):
        if key not in STATUS_EFFECTS:
            continue
        col = STATUS_EFFECTS[key]['color']
        x = sx - n * 5 + i * 10
        ai_icon = get_status_icon(key)
        if ai_icon is not None:
            # Render-Cache pro key (Skalierung ist teuer für 60fps mit vielen Mobs)
            cached = _STATUS_ICON_SCALED.get(key)
            if cached is None:
                cached = pygame.transform.smoothscale(ai_icon, (12, 12))
                _STATUS_ICON_SCALED[key] = cached
            screen.blit(cached, (x - 6, icons_y - 6))
        else:
            pygame.draw.circle(screen, col, (x, icons_y), 4)
            pygame.draw.circle(screen, WHITE, (x, icons_y), 4, 1)
        # Stacks
        if st['stacks'] > 1:
            # kleines weißes Pixel pro Stack (max 5 sichtbar)
            for k in range(min(5, st['stacks'])):
                pygame.draw.circle(screen, WHITE, (x - 2 + k, icons_y - 6), 1)


# Cache für 12×12 skalierte Status-Icons (sonst smoothscale jeden Frame
# pro Mob × Status-Key).  Wird beim Hot-Reload via reload_sprite_cache
# ebenfalls geleert.
_STATUS_ICON_SCALED: dict[str, pygame.Surface] = {}


def _outline_circle(screen, color, pos, r, outline=BLACK):
    """Kreis mit dunkler Outline (Pop-Effekt)."""
    pygame.draw.circle(screen, outline, pos, r + 1)
    pygame.draw.circle(screen, color, pos, r)


# ============================================================
# SPIELER
# ============================================================
def draw_player_at(screen, p, sx, sy, walk_phase):
    """sy = Bodenposition (Füße)."""
    sx, sy = int(sx), int(sy)
    h = p.height
    cls = p.cls
    base_color = CLASSES[cls]['color']

    # Tod-Animation: klassen-spezifisch
    if getattr(p, 'dying', False):
        _draw_player_dying(screen, p, sx, sy)
        return

    # Update #142 (User-Report „Boden so weit unter mir"):
    # Shadow MUSS am echten Boden bleiben (foot-pos `sy`), nur der
    # Körper darf bobben.  Vorher wurde `sy` modifiziert BEVOR der
    # Shadow gemalt wurde → Shadow schwebte mit dem Spieler hoch.
    # Resultat: Spieler+Shadow lifteten 3 px über die Floor-Tiles
    # → optischer Eindruck dass der Boden weiter weg ist.
    foot_sy = sy
    _ground_shadow(screen, sx, foot_sy, p.radius * 2 + 4)
    # Bob/Breath nur auf den Körper anwenden (nicht auf den Shadow)
    import math as _m
    if p.moving:
        walk_bob = abs(_m.sin(walk_phase * 2)) * 3
        body_sy = int(foot_sy - walk_bob)
    else:
        # Idle-Breath: minimaler Auf-Ab-Wiggle um den Foot herum
        # (vorher nur +Y → Body sinkt unter den Foot, was komisch
        # aussah).  Jetzt symmetrisch ±0.75 px.
        breath = _m.sin(pygame.time.get_ticks() * 0.003) * 0.75
        body_sy = int(foot_sy - breath)

    # Schutz-Glow am Body (nicht am Foot)
    if p.dodge > 0 or p.invuln > 0:
        glow = pygame.Surface((h * 2, h * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (160, 200, 255, 90),
                           (h, h), p.radius + 10)
        screen.blit(glow, (sx - h, body_sy - h - p.radius))

    if p.shield > 0:
        glow = pygame.Surface((h * 2, h * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (140, 180, 255, 80),
                           (h, h), p.radius + 14, 3)
        screen.blit(glow, (sx - h, body_sy - h - p.radius))

    # Update #165: Animation-State-aware Render-Pfad.
    # State-Machine entscheidet welche Anim laeuft (idle/walk/attack/hit/
    # cast/death). Wenn ein Sheet fuer (cls, anim, dir) existiert → render
    # echten Frame. Sonst fallback auf walk-frame-0 (oder static-sprite) +
    # procedural Visual-Effect (Scale-Pulse fuer Attack, Red-Flash fuer Hit,
    # Slide-Down+Fade fuer Death, Aspekt-Aura fuer Cast).
    ai_surf = None
    anim_st = getattr(p, 'anim_state', None)
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    fx_kind: str = ''   # procedural overlay key: '' | 'attack' | 'hit' | 'cast' | 'death'
    fx_progress: float = 0.0

    # Update #168 (Flicker-Fix): Unified-Sheet-Source. Wenn Walk-Sheet
    # existiert, IMMER aus dem Walk-Sheet rendern (mit FX-Overlay fuer
    # attack/hit/cast/death) statt zwischen Sheets ↔ static-Sprite zu
    # springen. Verhindert visible "blink" beim State-Wechsel
    # idle ↔ walk weil idle (no sheet) sonst auf monk.png fiel und
    # walk auf monk_anims/walk/<dir>.png frame N — zwei verschiedene
    # Artwork-Versionen mit minimal anderem Silhouetten-Offset.
    has_walk_sheet = has_anim(cls, 'walk')

    if anim_st is not None:
        anim_name = anim_st.current
        # 1. Versuch: echtes Sheet fuer (cls, anim, dir)
        ai_surf = get_class_anim_frame(cls, anim_name, direction, anim_st.frame)
        if ai_surf is None and has_walk_sheet:
            # 2. Unified Fallback: IMMER walk-sheet als Basis, auch fuer
            # idle (zeigt walk-frame-0 = neutrale Standpose). FX-Overlay
            # wenn one-shot-Anim (attack/hit/cast/death).
            if anim_name == 'idle' or not p.moving:
                # Stehender Charakter → walk-frame-0 (neutrale Pose).
                # Statt frame=0 hartcodiert: behalte walk_phase-Position
                # bei wenn gerade aus walk gewechselt → smoother stop.
                base_frame = 0 if not p.moving else int(
                    walk_phase % WALK_FRAMES_PER_STRIP)
            else:
                base_frame = int(walk_phase % WALK_FRAMES_PER_STRIP)
            ai_surf = get_class_anim_frame(cls, 'walk', direction, base_frame)
            if anim_name in ('attack', 'hit', 'cast', 'death'):
                fx_kind = anim_name
                fx_progress = anim_st.progress()
    else:
        # Alte Player-Instanzen ohne anim_state — alter walk_phase-Pfad
        if has_walk_sheet:
            if p.moving:
                frame_idx = int(walk_phase % WALK_FRAMES_PER_STRIP)
            else:
                frame_idx = 0
            ai_surf = get_class_walk_frame(cls, direction, frame_idx)

    # 3. Letzter Fallback: statisches AI-Sprite (nur wenn kein walk-sheet)
    # Wichtig: NUR wenn has_walk_sheet=False, sonst kein-statisch-Sprite-
    # Mixing damit kein Artwork-Sprung auftritt.
    if ai_surf is None and not has_walk_sheet:
        ai_surf = get_class_sprite(cls)

    if ai_surf is not None:
        # AI-Sprites haben mehr Body-Fülle als der Procedural-Composit.
        # Calibration-History:
        #   4.4x → war zu gross in Crypt (head + shoulders sprengten cell)
        #   3.4x → war zu klein in offenen Biomes (Desert/Sumpf/Eisfeld)
        #   3.8x → immer noch zu klein bei radius=18 (nur ~68px tall)
        #   6.0x → Update #164 nach Walk-Sheet-Integration: 18 * 6.0 =
        #          108px tall, ~12% Screen-Hoehe wie PoE2/D2-Heroes
        # Update #167: Multiplier kommt jetzt aus sf/render_spec.py
        # (Single-Source-of-Truth, siehe VELGRAD_RENDER_SPEC.md)
        try:
            from . import render_spec as _rs
            target_mult = _rs.get_target_h_mult('class') or 6.0
        except Exception:
            target_mult = 6.0
        target_h = int(p.radius * target_mult)
        _draw_ai_sprite_at_with_fx(
            screen, ai_surf, sx, body_sy + p.radius, target_h,
            fx_kind=fx_kind, fx_progress=fx_progress, cls=cls,
        )
    else:
        # Sprite-Proxy: neue Lore-Klassen teilen Sprites mit den 3 Base-Klassen
        proxy = CLASSES.get(cls, {}).get('sprite_proxy', cls)
        if proxy == 'warrior':
            _draw_warrior_iso(screen, p, sx, body_sy, walk_phase, base_color)
        elif proxy == 'mage':
            _draw_mage_iso(screen, p, sx, body_sy, walk_phase, base_color)
        else:
            _draw_rogue_iso(screen, p, sx, body_sy, walk_phase, base_color)

    _status_overlay(screen, sx, body_sy, h, p.status)


def _draw_player_dying(screen, p, sx, sy):
    """Klassen-spezifische Tod-Animation (2s)."""
    import math
    t = p.death_timer
    fade = max(0.0, 1.0 - t / 2.0)
    cls = p.cls
    h = p.height
    base = CLASSES[cls]['color']
    alpha = int(255 * fade)
    if alpha <= 0:
        return

    # Death-Anim nutzt sprite_proxy (neue Klassen → base-Anim).
    cls = CLASSES.get(cls, {}).get('sprite_proxy', cls)

    if cls == 'warrior':
        # Krieger fällt zur Seite (rotiert 90°)
        rot_deg = min(90, t * 75)  # über 1.2s zu 90 Grad
        # Wir zeichnen den Körper als rotierte Oberfläche
        surf = pygame.Surface((p.radius * 4, h + p.radius * 2), pygame.SRCALPHA)
        # Vereinfachter Körper auf surf zeichnen
        cx_surf = surf.get_width() // 2
        sy_surf = surf.get_height() - 4
        pygame.draw.rect(surf, (*base, alpha),
                         (cx_surf - 10, sy_surf - h + 10, 20, h - 14))
        pygame.draw.circle(surf, (*_shade(base, 0.6), alpha),
                           (cx_surf, sy_surf - h + 12), 8)
        # Helm-Akzent
        pygame.draw.line(surf, (*FIRE, alpha),
                         (cx_surf - 3, sy_surf - h + 12),
                         (cx_surf + 3, sy_surf - h + 12), 1)
        rot = pygame.transform.rotate(surf, rot_deg)
        screen.blit(rot, (sx - rot.get_width() // 2,
                          sy - rot.get_height() + 12))
    elif cls == 'mage':
        # Magier zerfällt zu Asche-Partikeln (Körper wird transparent)
        # Wenig zeichnen — nur abnehmender Umriss
        size = max(1, int(h * (1 - t / 2.0)))
        body_top = sy - size
        surf = pygame.Surface((24, size + 10), pygame.SRCALPHA)
        pygame.draw.polygon(surf, (*base, alpha // 2), [
            (4, size + 6), (8, 10), (16, 10), (20, size + 6),
        ])
        screen.blit(surf, (sx - 12, body_top))
        # Asche-Flocken (zusätzlich zu Combat-Partikeln)
        if int(t * 30) % 3 == 0:
            pygame.draw.circle(screen, (140, 100, 60, alpha),
                               (sx + int(math.sin(t * 8) * 6), sy - size // 2),
                               3)
    else:  # rogue
        # Schurke versinkt in Schatten (shrink + verschwimmt)
        scale = max(0.1, 1.0 - t / 2.0)
        size = int(h * scale)
        body_top = sy - size
        pygame.draw.ellipse(screen, (40, 40, 50),
                            (sx - 12, sy - size // 2, 24, size // 2 + 4))
        # Schatten-Wolke
        shadow = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(shadow, (0, 0, 0, alpha),
                           (20, 20), int(20 * scale))
        screen.blit(shadow, (sx - 20, sy - 20))


def _swing_offset(p):
    """Schwung-Animation für Waffe."""
    if p.attack_cd > 0.05:
        swing = max(0, (0.4 - p.attack_cd)) * 4
        return (swing - 0.5) * 1.4
    return 0


def _draw_legs_iso(screen, sx, sy, leg_color, walk_phase, leg_w=4, leg_h=10):
    """Zwei stehende Beine, mit Boden-Anker bei (sx, sy)."""
    lo, ro = _leg_bob(walk_phase)
    pygame.draw.rect(screen, _shade(leg_color, 0.5),
                     (sx - 5, sy - leg_h + lo, leg_w, leg_h))
    pygame.draw.rect(screen, _shade(leg_color, 0.45),
                     (sx + 1, sy - leg_h + ro, leg_w, leg_h))
    pygame.draw.line(screen, BLACK, (sx - 5, sy + lo),
                     (sx - 5 + leg_w, sy + lo), 1)
    pygame.draw.line(screen, BLACK, (sx + 1, sy + ro),
                     (sx + 1 + leg_w, sy + ro), 1)


def _draw_warrior_iso(screen, p, sx, sy, walk_phase, color):
    r = p.radius
    h = p.height
    body_top = sy - h
    torso_h = h - 18  # space for legs at bottom
    facing = p.facing
    sw_off = _swing_offset(p)

    # --- Cape hinten (gegen facing) ---
    cape_color = _shade(color, 0.45)
    cape_pts = [
        (sx - 6, body_top + 12),
        (sx + 6, body_top + 12),
        (sx + 8 - int(math.cos(facing) * 6), sy - 12),
        (sx - 8 - int(math.cos(facing) * 6), sy - 12),
    ]
    pygame.draw.polygon(screen, cape_color, cape_pts)
    pygame.draw.polygon(screen, _shade(color, 0.3), cape_pts, 1)

    # --- Beine ---
    _draw_legs_iso(screen, sx, sy, color, walk_phase)

    # --- Rumpf (trapezförmig, schmaler nach oben) ---
    torso_pts = [
        (sx - 9, sy - 12),
        (sx + 9, sy - 12),
        (sx + 8, body_top + 16),
        (sx - 8, body_top + 16),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.85), torso_pts)
    pygame.draw.polygon(screen, BLACK, torso_pts, 2)
    # Brustplatte
    pygame.draw.polygon(screen, _shade(color, 1.15), [
        (sx - 6, body_top + 18),
        (sx + 6, body_top + 18),
        (sx + 5, sy - 14),
        (sx - 5, sy - 14),
    ])
    pygame.draw.line(screen, _shade(color, 0.4),
                     (sx, body_top + 18), (sx, sy - 14), 2)
    # Goldakzent (Gürtel)
    pygame.draw.rect(screen, GOLD, (sx - 9, sy - 14, 18, 3))
    pygame.draw.rect(screen, BLACK, (sx - 9, sy - 14, 18, 3), 1)

    # --- Schultern ---
    pygame.draw.circle(screen, _shade(color, 0.7), (sx - 9, body_top + 14), 4)
    pygame.draw.circle(screen, BLACK, (sx - 9, body_top + 14), 4, 1)
    pygame.draw.circle(screen, _shade(color, 0.7), (sx + 9, body_top + 14), 4)
    pygame.draw.circle(screen, BLACK, (sx + 9, body_top + 14), 4, 1)

    # --- Kopf (Helm mit Visier) ---
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.6), (sx, head_y), 7)
    pygame.draw.circle(screen, GOLD, (sx, head_y), 7, 1)
    # Visier-Schlitz (gerade Augenlinie)
    pygame.draw.rect(screen, BLACK, (sx - 4, head_y - 1, 8, 2))
    pygame.draw.line(screen, FIRE, (sx - 3, head_y), (sx + 3, head_y), 1)
    # Helm-Spitze
    pygame.draw.polygon(screen, _shade(color, 0.5), [
        (sx - 4, head_y - 5), (sx + 4, head_y - 5), (sx, head_y - 10),
    ])

    # --- Schild (links / hinten in Bewegung) ---
    shx = sx - 14
    shy = sy - 16
    pygame.draw.circle(screen, (130, 90, 50), (shx, shy), 7)
    pygame.draw.circle(screen, BLACK, (shx, shy), 7, 1)
    pygame.draw.circle(screen, GOLD, (shx, shy), 4, 1)

    # --- Schwert (rotiert mit facing + swing) ---
    sw_a = facing + sw_off
    grip_x = sx + 10
    grip_y = sy - 18
    # Klinge in facing Richtung
    blade_len = 22
    bx = grip_x + math.cos(sw_a) * blade_len
    by = grip_y + math.sin(sw_a) * blade_len * 0.6
    pygame.draw.line(screen, BLACK, (grip_x, grip_y), (bx, by), 5)
    pygame.draw.line(screen, (235, 235, 215), (grip_x, grip_y), (bx, by), 3)
    pygame.draw.line(screen, WHITE, (grip_x, grip_y), (bx, by), 1)
    # Griff
    pygame.draw.rect(screen, (90, 60, 30), (grip_x - 2, grip_y - 1, 4, 3))
    # Parierstange
    pygame.draw.line(screen, GOLD,
                     (grip_x - 4, grip_y), (grip_x + 4, grip_y), 2)
    pygame.draw.circle(screen, GOLD_BRIGHT, (int(bx), int(by)), 2)


def _draw_mage_iso(screen, p, sx, sy, walk_phase, color):
    r = p.radius
    h = p.height
    body_top = sy - h
    facing = p.facing
    sw_off = _swing_offset(p)

    # --- Lange Robe (versteckt Beine) ---
    robe_bottom = sy + 2
    robe_pts = [
        (sx - 12, robe_bottom),
        (sx - 8, body_top + 12),
        (sx + 8, body_top + 12),
        (sx + 12, robe_bottom),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.55), robe_pts)
    pygame.draw.polygon(screen, BLACK, robe_pts, 2)
    # Robe-Verzierungen (zwei vertikale Bänder)
    pygame.draw.line(screen, GOLD,
                     (sx - 4, body_top + 16), (sx - 6, robe_bottom - 2), 1)
    pygame.draw.line(screen, GOLD,
                     (sx + 4, body_top + 16), (sx + 6, robe_bottom - 2), 1)
    # Runen entlang der Robe
    for k, dy in enumerate((sy - 14, sy - 4, sy + 4)):
        pygame.draw.circle(screen, _shade(color, 1.4), (sx, dy), 2)

    # --- Schultern (kleinere) ---
    pygame.draw.circle(screen, _shade(color, 0.7), (sx - 8, body_top + 14), 3)
    pygame.draw.circle(screen, _shade(color, 0.7), (sx + 8, body_top + 14), 3)

    # --- Kopf mit Spitzhut ---
    head_y = body_top + 8
    _outline_circle(screen, (220, 190, 160), (sx, head_y), 6)
    # Bart
    pygame.draw.polygon(screen, (200, 200, 200), [
        (sx - 4, head_y + 2), (sx + 4, head_y + 2),
        (sx + 3, head_y + 7), (sx, head_y + 9), (sx - 3, head_y + 7),
    ])
    # Augen
    pygame.draw.circle(screen, BLACK, (sx - 2, head_y - 1), 1)
    pygame.draw.circle(screen, BLACK, (sx + 2, head_y - 1), 1)
    # Spitzhut (großes Dreieck)
    hat_pts = [
        (sx - 10, head_y - 4),
        (sx + 10, head_y - 4),
        (sx + 3, head_y - 22),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.4), hat_pts)
    pygame.draw.polygon(screen, BLACK, hat_pts, 2)
    # Hut-Stern
    pygame.draw.circle(screen, GOLD_BRIGHT, (sx - 2, head_y - 12), 2)

    # --- Stab (links gehalten) ---
    pulse = abs(math.sin(walk_phase * 1.5))
    stx = sx - 12
    sty_top = body_top - 4
    sty_bot = sy + 4
    pygame.draw.line(screen, (90, 60, 30), (stx, sty_top), (stx, sty_bot), 3)
    pygame.draw.line(screen, (60, 40, 20), (stx, sty_top), (stx, sty_bot), 1)
    # Kristall an Spitze
    crystal_col = (140, 180, 255) if color[2] > 150 else (200, 130, 255)
    cr_size = 4 + int(pulse * 2)
    glow = pygame.Surface((cr_size * 5, cr_size * 5), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*crystal_col, 150),
                       (cr_size * 2 + 1, cr_size * 2 + 1), cr_size * 2)
    screen.blit(glow, (stx - cr_size * 2 - 1, sty_top - cr_size * 2 - 1))
    pygame.draw.circle(screen, crystal_col, (stx, sty_top), cr_size)
    pygame.draw.circle(screen, WHITE, (stx, sty_top), max(1, cr_size - 2))


def _draw_rogue_iso(screen, p, sx, sy, walk_phase, color):
    r = p.radius
    h = p.height
    body_top = sy - h
    facing = p.facing
    sw_off = _swing_offset(p)

    # --- Cape (kurz, dunkelgrün) ---
    cape_color = (40, 70, 50)
    cape_pts = [
        (sx - 5, body_top + 12),
        (sx + 5, body_top + 12),
        (sx + 9, sy - 4),
        (sx - 9, sy - 4),
    ]
    pygame.draw.polygon(screen, cape_color, cape_pts)
    pygame.draw.polygon(screen, BLACK, cape_pts, 1)

    # --- Schlanke Beine (eng zusammen) ---
    lo, ro = _leg_bob(walk_phase * 1.3)
    pygame.draw.rect(screen, _shade(color, 0.4),
                     (sx - 4, sy - 10 + lo, 3, 10))
    pygame.draw.rect(screen, _shade(color, 0.4),
                     (sx + 1, sy - 10 + ro, 3, 10))

    # --- Leder-Rumpf (schmaler) ---
    torso_pts = [
        (sx - 7, sy - 6),
        (sx + 7, sy - 6),
        (sx + 7, body_top + 14),
        (sx - 7, body_top + 14),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.7), torso_pts)
    pygame.draw.polygon(screen, BLACK, torso_pts, 2)
    # Brust-Riemen kreuzförmig
    pygame.draw.line(screen, (50, 35, 25),
                     (sx - 7, body_top + 16), (sx + 7, sy - 8), 1)
    pygame.draw.line(screen, (50, 35, 25),
                     (sx + 7, body_top + 16), (sx - 7, sy - 8), 1)
    pygame.draw.rect(screen, (40, 30, 20), (sx - 7, sy - 8, 14, 2))

    # --- Schultern ---
    pygame.draw.circle(screen, _shade(color, 0.5), (sx - 7, body_top + 12), 3)
    pygame.draw.circle(screen, _shade(color, 0.5), (sx + 7, body_top + 12), 3)

    # --- Kopf mit Hood ---
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.3), (sx, head_y), 7)
    # Hood-Saum
    pygame.draw.arc(screen, BLACK, (sx - 8, head_y - 2, 16, 12), 0, math.pi, 2)
    # Augen-Glow
    pygame.draw.circle(screen, (200, 240, 220), (sx - 2, head_y), 1)
    pygame.draw.circle(screen, (200, 240, 220), (sx + 2, head_y), 1)

    # --- Zwei Dolche (rechts und links) ---
    for side, ofs in ((-1, sw_off + 0.3), (1, sw_off - 0.3)):
        a = facing + ofs * side
        gx = sx + side * 9
        gy = sy - 16
        bx = gx + math.cos(a) * 12
        by = gy + math.sin(a) * 7
        pygame.draw.line(screen, BLACK, (gx, gy), (bx, by), 3)
        pygame.draw.line(screen, (220, 220, 200), (gx, gy), (bx, by), 1)
        pygame.draw.circle(screen, WHITE, (int(bx), int(by)), 1)


# ============================================================
# GEGNER
# ============================================================
def draw_enemy_at(screen, e, sx, sy):
    sx, sy = int(sx), int(sy)
    # Tod-Animation: ausblenden und auseinanderdriften
    if e.dying:
        prog = e.death_timer
        alpha = max(0, 1 - prog * 2)
        if alpha <= 0:
            return
    # PLAN F-09 (Update #97 + #106): STALKER-Stealth-Rendering.
    # Mobs mit engage_mode='stalk' im non-AGGRO-State werden semi-transparent
    # gerendert (Schatten-Lurker-Style). Sichtbar, aber subtil.
    stealth = False
    if (getattr(e, 'engage_mode', None) == 'stalk'
            and getattr(e, 'ai_state', None) not in ('AGGRO', None)
            and not e.dying and not e.is_boss):
        stealth = True
        e._stealth_render = True
    else:
        e._stealth_render = False
    _ground_shadow(screen, sx, sy,
                    e.radius * 2 + 2,
                    alpha=70 if stealth else 160)
    # Update #106 (Audit F-017): Echter visueller Stealth-Effekt.
    # Wir spawnen pre-Render einen dunklen Veil-Surface der den Bereich
    # über dem Mob darken'd — wirkt wie ein Shadow-Lurker bevor der
    # Mob ins AGGRO geht.  Pulsierend.
    if stealth:
        veil_pulse = 0.7 + 0.3 * math.sin(pygame.time.get_ticks() * 0.004)
        veil_r = int(e.radius + 8)
        veil = pygame.Surface((veil_r * 2 + 4, e.height + veil_r),
                                pygame.SRCALPHA)
        pygame.draw.circle(veil, (12, 8, 16, int(120 * veil_pulse)),
                            (veil_r + 2, veil_r),
                            veil_r)
        screen.blit(veil, (sx - veil_r - 2,
                            sy - e.height // 2 - veil_r // 2))
    # Kontrast-Ring (subtiler heller Ring unter dem Gegner zum Erkennen)
    ring = pygame.Surface((e.radius * 2 + 8, e.radius // 2 + 4), pygame.SRCALPHA)
    pygame.draw.ellipse(ring, (*e.glow, 60),
                        (0, 0, e.radius * 2 + 8, e.radius // 2 + 4), 2)
    screen.blit(ring, (sx - e.radius - 4, sy - e.radius // 4 - 2))

    # Stun-Anzeige (Sterne über Kopf)
    if e.stun_timer > 0:
        _draw_stun(screen, sx, sy - e.height - 14)

    # Elite/Boss-Aura
    # F-17 (Update #45): Affix-Tier-Outline statt Affix-Farbe.
    # magic = blau, rare = gelb, unique = orange. Mehr Tier-Ringe für höhere
    # Stufen — visuell sofort lesbar (POE2-Konvention).
    if e.elite or e.is_boss:
        tier = getattr(e, 'affix_tier', None)
        if e.is_boss:
            aura_col = (255, 200, 80)
            tier_rings = 5
        elif tier == 'unique':
            from .enemies import AFFIX_TIER_COLOR
            aura_col = AFFIX_TIER_COLOR['unique']
            tier_rings = 6
        elif tier == 'rare':
            from .enemies import AFFIX_TIER_COLOR
            aura_col = AFFIX_TIER_COLOR['rare']
            tier_rings = 5
        elif tier == 'magic':
            from .enemies import AFFIX_TIER_COLOR
            aura_col = AFFIX_TIER_COLOR['magic']
            tier_rings = 4
        else:
            aura_col = {
                'fast': (180, 220, 255),
                'fire': (255, 120, 60),
                'vampiric': (255, 60, 60),
                'explosive': (255, 200, 60),
            }.get(e.affix, (255, 200, 80))
            tier_rings = 4
        glow = pygame.Surface((e.height * 2, e.height * 2), pygame.SRCALPHA)
        for i in range(tier_rings, 0, -1):
            pygame.draw.circle(glow, (*aura_col, 50 // i),
                               (e.height, e.height), e.radius + 4 + i * 3)
        screen.blit(glow, (sx - e.height, sy - e.height - e.radius // 2))
        # F-17: Affix-Icons über Health-Bar (kleine farbige Dots, max 6)
        affixes = getattr(e, 'affixes', None)
        if affixes:
            from .enemies import AFFIX_POOL
            icon_y = sy - e.height - 28
            dot_w = 5
            spacing = 7
            total = min(len(affixes), 6)
            start_x = sx - (total * spacing) // 2
            for i, aff in enumerate(affixes[:6]):
                col = AFFIX_POOL.get(aff, {}).get('color', (200, 200, 200))
                cx = start_x + i * spacing
                pygame.draw.circle(screen, col, (cx, icon_y), dot_w // 2 + 1)
                pygame.draw.circle(screen, (10, 6, 4), (cx, icon_y),
                                    dot_w // 2 + 1, 1)

    # ROADMAP T2.2: AI-Mob-Sprite-Hook — wenn bestiary_key auf ein PNG
    # mappt, rendere das statt Procedural. Bosse haben Concept-Plates
    # die nur fuer Cinematic-Intros sind; im Spielfeld bleibt Procedural
    # (Boss-Aura/Phase-VFX brauchen das).
    bestiary_key = getattr(e, 'bestiary_key', None)
    if bestiary_key and not e.is_boss:
        ai_mob = get_mob_sprite(bestiary_key)
        if ai_mob is not None:
            # Mob-Sprite-Calibration: e.height = radius*2.2, plus ~80%
            # Body-Cap. Insgesamt ~2.5x radius. Update analog zum
            # Player-Sprite-Fix nach User-Feedback.
            # Update #167: Multiplier aus sf/render_spec.py.
            try:
                from . import render_spec as _rs
                mob_mult = _rs.get_target_h_mult('mob') or 2.5
            except Exception:
                mob_mult = 2.5
            target_h = int(e.radius * mob_mult)
            _draw_ai_sprite_at(screen, ai_mob, sx, sy, target_h)
            # Status-Effekte trotzdem rendern (uebernimmt der Block unten)
            _status_overlay(screen, sx, sy, e.height, e.status)
            return

    if e.is_boss:
        if e.boss_kind == 'necromancer':
            _draw_boss_necromancer(screen, e, sx, sy)
        elif e.boss_kind == 'frostlord':
            _draw_boss_frostlord(screen, e, sx, sy)
        elif e.boss_kind == 'dragon':
            _draw_boss_dragon(screen, e, sx, sy)
        elif e.boss_kind == 'bone_knight':
            _draw_boss_bone_knight(screen, e, sx, sy)
        elif e.boss_kind == 'snow_queen':
            _draw_boss_snow_queen(screen, e, sx, sy)
        elif e.boss_kind == 'magma_golem':
            _draw_boss_magma_golem(screen, e, sx, sy)
        elif e.boss_kind == 'shadow_lord':
            _draw_boss_shadow_lord(screen, e, sx, sy)
        else:
            _draw_demon_iso(screen, e, sx, sy)
    else:
        drawer = {
            'zombie':    _draw_zombie_iso,
            'skeleton':  _draw_skeleton_iso,
            'wraith':    _draw_wraith_iso,
            'demon':     _draw_demon_iso,
            'brute':     _draw_brute_iso,
            'archer':    _draw_archer_iso,
            'shaman':    _draw_shaman_iso,
            'warlock':   _draw_warlock_iso,
            'berserker': _draw_berserker_iso,
            'lurker':    _draw_lurker_iso,
            'slime':     _draw_slime_iso,
        }.get(e.type_key, _draw_zombie_iso)
        drawer(screen, e, sx, sy)

    # Status-Effekte über dem Kopf
    _status_overlay(screen, sx, sy, e.height, e.status)


def _draw_stun(screen, x, y):
    """Drei Sterne über Kopf für Stun-Anzeige."""
    t = pygame.time.get_ticks() * 0.01
    for k in range(3):
        a = t + k * 2.094
        sx = x + math.cos(a) * 8
        sy = y + math.sin(a) * 4
        pygame.draw.polygon(screen, (255, 240, 120), [
            (int(sx), int(sy - 3)),
            (int(sx + 2), int(sy)),
            (int(sx), int(sy + 3)),
            (int(sx - 2), int(sy)),
        ])


def _draw_zombie_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.07

    # Beine (taumelnd)
    lo, ro = _leg_bob(e.walk_phase)
    pygame.draw.rect(screen, _shade(color, 0.4), (sx - 5, sy - 8 + lo, 4, 8))
    pygame.draw.rect(screen, _shade(color, 0.4), (sx + 1, sy - 8 + ro, 4, 8))

    # Hängender Rumpf
    pygame.draw.polygon(screen, color, [
        (sx - 8, sy - 8),
        (sx + 8, sy - 8),
        (sx + 7, body_top + 10),
        (sx - 7, body_top + 10),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 8, sy - 8),
        (sx + 8, sy - 8),
        (sx + 7, body_top + 10),
        (sx - 7, body_top + 10),
    ], 1)
    # Zerfetzte Hemd-Streifen
    for dy in (sy - 12, sy - 4):
        pygame.draw.line(screen, _shade(color, 0.3),
                         (sx - 7, dy), (sx + 7, dy), 1)

    # Hängende Arme nach vorne (klassisches Zombie-Bild)
    swing = math.sin(e.walk_phase * 0.6) * 3
    for side in (-1, 1):
        sh_x = sx + side * 8
        sh_y = body_top + 12
        hand_x = sh_x + side * 4
        hand_y = sy - 4 + swing * side
        pygame.draw.line(screen, _shade(color, 0.5),
                         (sh_x, sh_y), (hand_x, hand_y), 3)
        pygame.draw.circle(screen, _shade(color, 0.6),
                           (int(hand_x), int(hand_y)), 2)

    # Kopf (hängend, leicht nach unten geneigt)
    head_y = body_top + 6
    _outline_circle(screen, _shade(color, 0.7), (sx + 1, head_y), 6)
    # Tote Augen (glühend)
    pygame.draw.circle(screen, e.glow, (sx - 1, head_y - 1), 1)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y - 1), 1)
    # Geöffneter Mund
    pygame.draw.line(screen, BLACK, (sx - 1, head_y + 3), (sx + 3, head_y + 3), 1)


def _draw_skeleton_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    bone = (220, 210, 180) if e.hit_flash <= 0 else WHITE
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.09

    # Knochenbeine
    lo, ro = _leg_bob(e.walk_phase)
    pygame.draw.line(screen, bone, (sx - 3, sy - 10 + lo), (sx - 3, sy + lo), 2)
    pygame.draw.line(screen, bone, (sx + 3, sy - 10 + ro), (sx + 3, sy + ro), 2)
    pygame.draw.circle(screen, bone, (sx - 3, sy + lo), 2)
    pygame.draw.circle(screen, bone, (sx + 3, sy + ro), 2)

    # Becken
    pygame.draw.polygon(screen, bone, [
        (sx - 6, sy - 10), (sx + 6, sy - 10),
        (sx + 4, sy - 14), (sx - 4, sy - 14),
    ])

    # Wirbelsäule
    pygame.draw.line(screen, bone, (sx, sy - 14), (sx, body_top + 12), 2)
    # Rippen (3 Ovale)
    for dy in (sy - 18, sy - 22, sy - 26):
        pygame.draw.arc(screen, bone, (sx - 7, dy - 3, 14, 8), 0, math.pi, 1)
        pygame.draw.arc(screen, bone, (sx - 7, dy - 3, 14, 8), math.pi, math.tau, 1)

    # Arme + Krummsäbel
    swing = math.sin(e.walk_phase) * 0.5
    sw_a = swing + 0.6
    pygame.draw.line(screen, bone, (sx + 6, body_top + 16),
                     (sx + 10, sy - 14), 2)
    blade_end_x = sx + 10 + math.cos(sw_a) * 12
    blade_end_y = sy - 18 + math.sin(sw_a) * 8
    pygame.draw.line(screen, BLACK,
                     (sx + 10, sy - 14), (blade_end_x, blade_end_y), 3)
    pygame.draw.line(screen, (220, 220, 200),
                     (sx + 10, sy - 14), (blade_end_x, blade_end_y), 1)
    # Linker Arm
    pygame.draw.line(screen, bone, (sx - 6, body_top + 16),
                     (sx - 10, sy - 12), 2)

    # Schädel
    head_y = body_top + 8
    _outline_circle(screen, bone, (sx, head_y), 7)
    # Augenhöhlen
    pygame.draw.circle(screen, BLACK, (sx - 3, head_y - 1), 2)
    pygame.draw.circle(screen, BLACK, (sx + 3, head_y - 1), 2)
    pygame.draw.circle(screen, e.glow, (sx - 3, head_y - 1), 1)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y - 1), 1)
    # Zähne (Linie)
    pygame.draw.line(screen, BLACK, (sx - 4, head_y + 4), (sx + 4, head_y + 4), 1)
    for k in (-3, -1, 1, 3):
        pygame.draw.line(screen, BLACK,
                         (sx + k, head_y + 4), (sx + k, head_y + 6), 1)


def _draw_wraith_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Schwebend → kein Boden-Kontakt, leichtes Bob
    bob = math.sin(e.wobble * 1.2) * 3

    # Tail (unter dem Körper, wabernd)
    tail_pts = [
        (sx - 6, sy + bob),
        (sx - 9 + int(math.sin(e.wobble * 2) * 3), sy + 4 + bob),
        (sx, sy + 8 + bob),
        (sx + 9 - int(math.sin(e.wobble * 2) * 3), sy + 4 + bob),
        (sx + 6, sy + bob),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.4), tail_pts)
    pygame.draw.polygon(screen, e.glow, tail_pts, 1)

    # Hauptkörper (Mantel-Tropfen)
    body_pts = [
        (sx - 10, sy - 6 + bob),
        (sx + 10, sy - 6 + bob),
        (sx + 6, body_top + 14 + bob),
        (sx - 6, body_top + 14 + bob),
    ]
    pygame.draw.polygon(screen, color, body_pts)
    pygame.draw.polygon(screen, BLACK, body_pts, 1)
    # Mantel-Verzierungen (drei Geistlinien)
    for dy in (-4, 0, 4):
        pygame.draw.line(screen, e.glow,
                         (sx - 8, sy + dy + bob), (sx + 8, sy + dy + bob), 1)

    # Kapuze hoch (Dreieck)
    hood_y = body_top + 8 + bob
    pygame.draw.polygon(screen, _shade(color, 0.7), [
        (sx - 8, hood_y + 4), (sx + 8, hood_y + 4),
        (sx, hood_y - 6),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 8, hood_y + 4), (sx + 8, hood_y + 4),
        (sx, hood_y - 6),
    ], 1)
    # Glühende Augen tief in der Kapuze
    pygame.draw.circle(screen, e.glow, (sx - 3, hood_y + 2), 2)
    pygame.draw.circle(screen, e.glow, (sx + 3, hood_y + 2), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, hood_y + 2), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, hood_y + 2), 1)


def _draw_demon_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.08

    # Klauenbeine
    lo, ro = _leg_bob(e.walk_phase)
    for side, off in ((-1, lo), (1, ro)):
        x = sx + side * 5
        pygame.draw.rect(screen, _shade(color, 0.5),
                         (x - 3, sy - 10 + off, 6, 10))
        # Klauen
        for k in (-1, 0, 1):
            pygame.draw.line(screen, (240, 220, 180),
                             (x + k, sy + off), (x + k, sy + 4 + off), 2)

    # Breite, muskulöse Brust
    pygame.draw.polygon(screen, color, [
        (sx - 12, sy - 10), (sx + 12, sy - 10),
        (sx + 10, body_top + 12), (sx - 10, body_top + 12),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 12, sy - 10), (sx + 12, sy - 10),
        (sx + 10, body_top + 12), (sx - 10, body_top + 12),
    ], 2)
    # Muskel-Definition
    pygame.draw.line(screen, _shade(color, 1.3), (sx, body_top + 14), (sx, sy - 12), 2)
    pygame.draw.line(screen, _shade(color, 0.6),
                     (sx - 6, sy - 14), (sx + 6, sy - 14), 1)

    # Arme nach unten mit Klauen
    for side in (-1, 1):
        sh_x = sx + side * 12
        sh_y = body_top + 14
        hand_x = sh_x + side * 4
        hand_y = sy - 6
        pygame.draw.line(screen, _shade(color, 0.7),
                         (sh_x, sh_y), (hand_x, hand_y), 4)
        # Klauen-Hand
        for k in (-1, 0, 1):
            pygame.draw.line(screen, (240, 220, 180),
                             (hand_x + side * k, hand_y),
                             (hand_x + side * k * 2, hand_y + 4), 1)

    # Kopf mit Hörnern
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.7), (sx, head_y), 8)
    # Hörner
    pygame.draw.polygon(screen, (40, 20, 10), [
        (sx - 7, head_y - 2), (sx - 12, head_y - 10), (sx - 5, head_y - 5),
    ])
    pygame.draw.polygon(screen, (40, 20, 10), [
        (sx + 7, head_y - 2), (sx + 12, head_y - 10), (sx + 5, head_y - 5),
    ])
    # Glühende Augen
    pygame.draw.circle(screen, e.glow, (sx - 3, head_y), 2)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, head_y), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, head_y), 1)
    # Reißzähne
    pygame.draw.polygon(screen, WHITE,
                        [(sx - 3, head_y + 4), (sx - 2, head_y + 7), (sx - 1, head_y + 4)])
    pygame.draw.polygon(screen, WHITE,
                        [(sx + 1, head_y + 4), (sx + 2, head_y + 7), (sx + 3, head_y + 4)])


def _draw_brute_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.05

    # Massive Beine
    lo, ro = _leg_bob(e.walk_phase)
    for side, off in ((-1, lo), (1, ro)):
        x = sx + side * 7
        pygame.draw.rect(screen, _shade(color, 0.5),
                         (x - 5, sy - 12 + off, 10, 12))
        pygame.draw.rect(screen, BLACK,
                         (x - 5, sy - 12 + off, 10, 12), 1)

    # Riesiger Rumpf (sehr breit)
    pygame.draw.polygon(screen, color, [
        (sx - 16, sy - 12), (sx + 16, sy - 12),
        (sx + 12, body_top + 16), (sx - 12, body_top + 16),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 16, sy - 12), (sx + 16, sy - 12),
        (sx + 12, body_top + 16), (sx - 12, body_top + 16),
    ], 2)
    # Fell-Striemen
    for k in (-10, -4, 4, 10):
        pygame.draw.line(screen, _shade(color, 1.4),
                         (sx + k, body_top + 18), (sx + k, sy - 14), 1)
    # Gürtel
    pygame.draw.rect(screen, (60, 40, 20), (sx - 14, sy - 12, 28, 4))

    # Massive Schultern
    pygame.draw.circle(screen, _shade(color, 0.6), (sx - 16, body_top + 16), 6)
    pygame.draw.circle(screen, BLACK, (sx - 16, body_top + 16), 6, 1)
    pygame.draw.circle(screen, _shade(color, 0.6), (sx + 16, body_top + 16), 6)
    pygame.draw.circle(screen, BLACK, (sx + 16, body_top + 16), 6, 1)

    # Kleiner Kopf (proportional zur Größe)
    head_y = body_top + 10
    _outline_circle(screen, _shade(color, 0.7), (sx, head_y), 6)
    pygame.draw.circle(screen, e.glow, (sx - 2, head_y), 1)
    pygame.draw.circle(screen, e.glow, (sx + 2, head_y), 1)
    # Mund
    pygame.draw.line(screen, BLACK, (sx - 2, head_y + 3), (sx + 2, head_y + 3), 1)

    # Riesige Axt (auf Schulter)
    ax1, ay1 = sx + 16, body_top + 16
    ax2, ay2 = sx + 22, body_top - 8
    pygame.draw.line(screen, (90, 60, 30), (ax1, ay1), (ax2, ay2), 4)
    # Axt-Kopf
    blade_pts = [
        (ax2 - 6, ay2),
        (ax2 + 8, ay2 - 4),
        (ax2 + 10, ay2 + 6),
        (ax2 + 2, ay2 + 8),
    ]
    pygame.draw.polygon(screen, (210, 210, 190), blade_pts)
    pygame.draw.polygon(screen, BLACK, blade_pts, 1)
    pygame.draw.polygon(screen, (140, 30, 30), blade_pts, 1)


def _draw_archer_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.08

    # Schlanke Beine
    lo, ro = _leg_bob(e.walk_phase)
    pygame.draw.rect(screen, _shade(color, 0.5), (sx - 4, sy - 10 + lo, 3, 10))
    pygame.draw.rect(screen, _shade(color, 0.5), (sx + 1, sy - 10 + ro, 3, 10))

    # Schlanker Rumpf
    pygame.draw.polygon(screen, color, [
        (sx - 7, sy - 10), (sx + 7, sy - 10),
        (sx + 6, body_top + 12), (sx - 6, body_top + 12),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 7, sy - 10), (sx + 7, sy - 10),
        (sx + 6, body_top + 12), (sx - 6, body_top + 12),
    ], 1)
    # Gürtel
    pygame.draw.rect(screen, (60, 40, 20), (sx - 7, sy - 10, 14, 2))

    # Köcher hinten (schräg)
    pygame.draw.rect(screen, (90, 60, 30), (sx - 9, body_top + 14, 3, 12))
    for k in range(3):
        pygame.draw.line(screen, (240, 220, 150),
                         (sx - 8 + k, body_top + 10), (sx - 8 + k, body_top + 14), 1)
        # Federn
        pygame.draw.line(screen, (220, 60, 60),
                         (sx - 9 + k, body_top + 9),
                         (sx - 7 + k, body_top + 11), 1)

    # Kopf mit Kapuze
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.4), (sx, head_y), 6)
    pygame.draw.arc(screen, BLACK, (sx - 7, head_y - 2, 14, 10), 0, math.pi, 2)
    pygame.draw.circle(screen, e.glow, (sx - 2, head_y), 1)
    pygame.draw.circle(screen, e.glow, (sx + 2, head_y), 1)

    # Bogen (rechts, gespannt)
    bow_x = sx + 9
    bow_y_top = body_top + 14
    bow_y_bot = sy - 8
    pygame.draw.arc(screen, (110, 70, 30),
                    (bow_x - 4, bow_y_top, 10, bow_y_bot - bow_y_top), -1.6, 1.6, 2)
    # Sehne
    pygame.draw.line(screen, (220, 220, 200),
                     (bow_x - 1, bow_y_top + 1), (bow_x - 1, bow_y_bot - 1), 1)
    # Aufgelegter Pfeil
    pygame.draw.line(screen, (220, 200, 150),
                     (bow_x - 1, sy - 18), (bow_x + 14, sy - 18), 1)
    pygame.draw.polygon(screen, (220, 200, 150), [
        (bow_x + 14, sy - 19), (bow_x + 18, sy - 18), (bow_x + 14, sy - 17),
    ])


def _draw_shaman_iso(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h

    # Lange Robe
    robe_pts = [
        (sx - 10, sy),
        (sx - 8, body_top + 14),
        (sx + 8, body_top + 14),
        (sx + 10, sy),
    ]
    pygame.draw.polygon(screen, color, robe_pts)
    pygame.draw.polygon(screen, BLACK, robe_pts, 2)
    # Glühende Verzierungen
    for dy in (sy - 14, sy - 6, sy + 2):
        pygame.draw.line(screen, e.glow,
                         (sx - 7, dy), (sx + 7, dy), 1)

    # Kapuze mit Maske
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.4), (sx, head_y), 7)
    # Maske mit Glow-Pattern
    pygame.draw.rect(screen, e.glow, (sx - 4, head_y - 2, 8, 2))
    pygame.draw.circle(screen, e.glow, (sx, head_y + 2), 2)
    pygame.draw.circle(screen, WHITE, (sx, head_y + 2), 1)

    # Stab mit Totem-Aufsatz
    stx = sx + 10
    sty_top = body_top - 6
    sty_bot = sy + 2
    pygame.draw.line(screen, (90, 60, 30), (stx, sty_top), (stx, sty_bot), 3)
    # Totem (Glühender Schädel)
    pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
    glow = pygame.Surface((20, 20), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*e.glow, int(150 * (0.5 + pulse * 0.5))),
                       (10, 10), 9)
    screen.blit(glow, (stx - 10, sty_top - 10))
    pygame.draw.circle(screen, (240, 230, 200), (stx, sty_top), 4)
    pygame.draw.circle(screen, BLACK, (stx - 1, sty_top - 1), 1)
    pygame.draw.circle(screen, BLACK, (stx + 1, sty_top - 1), 1)


def _draw_warlock_iso(screen, e, sx, sy):
    """Hexenmeister: lila Robe, schwebende Schädel-Orbs."""
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Lange Robe
    robe_pts = [
        (sx - 11, sy + 2),
        (sx - 8, body_top + 14),
        (sx + 8, body_top + 14),
        (sx + 11, sy + 2),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.7), robe_pts)
    pygame.draw.polygon(screen, BLACK, robe_pts, 2)
    # Verzierungen
    for dy in (sy - 14, sy - 4, sy + 4):
        pygame.draw.line(screen, e.glow, (sx - 8, dy), (sx + 8, dy), 1)
    # Hauptkörper / Bust
    pygame.draw.circle(screen, color, (sx, sy - 4), 9)
    pygame.draw.circle(screen, e.glow, (sx, sy - 4), 9, 1)
    # Kapuze
    head_y = body_top + 10
    pygame.draw.polygon(screen, _shade(color, 0.5), [
        (sx - 8, head_y + 4), (sx + 8, head_y + 4),
        (sx, head_y - 12),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 8, head_y + 4), (sx + 8, head_y + 4),
        (sx, head_y - 12),
    ], 1)
    # Augen tief in der Kapuze
    pygame.draw.circle(screen, e.glow, (sx - 3, head_y + 1), 2)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y + 1), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, head_y + 1), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, head_y + 1), 1)
    # Schwebender Schädel als Begleiter (links neben Kopf)
    import math
    bob = math.sin(e.wobble * 1.5) * 3
    sk_x = sx - 16
    sk_y = body_top + 6 + int(bob)
    glow = pygame.Surface((22, 22), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*e.glow, 120), (11, 11), 10)
    screen.blit(glow, (sk_x - 11, sk_y - 11))
    pygame.draw.circle(screen, (240, 230, 200), (sk_x, sk_y), 5)
    pygame.draw.circle(screen, BLACK, (sk_x - 1, sk_y - 1), 1)
    pygame.draw.circle(screen, BLACK, (sk_x + 1, sk_y - 1), 1)


def _draw_berserker_iso(screen, e, sx, sy):
    """Berserker: aggressive rot/orange Figur, große Axt."""
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.10
    # Beine
    lo, ro = _leg_bob(e.walk_phase)
    for side, off in ((-1, lo), (1, ro)):
        x = sx + side * 6
        pygame.draw.rect(screen, _shade(color, 0.5),
                         (x - 4, sy - 12 + off, 8, 12))
        pygame.draw.rect(screen, BLACK, (x - 4, sy - 12 + off, 8, 12), 1)
    # Rumpf (muskulös)
    pygame.draw.polygon(screen, color, [
        (sx - 13, sy - 12), (sx + 13, sy - 12),
        (sx + 11, body_top + 14), (sx - 11, body_top + 14),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 13, sy - 12), (sx + 13, sy - 12),
        (sx + 11, body_top + 14), (sx - 11, body_top + 14),
    ], 2)
    # Tribal-Bemalung (rot)
    pygame.draw.line(screen, (255, 80, 30), (sx - 5, sy - 8), (sx + 5, sy - 8), 1)
    pygame.draw.line(screen, (255, 80, 30), (sx - 7, sy), (sx + 7, sy), 1)
    pygame.draw.circle(screen, (255, 80, 30), (sx, sy - 4), 2)
    # Schultern
    pygame.draw.circle(screen, _shade(color, 0.6), (sx - 13, body_top + 14), 5)
    pygame.draw.circle(screen, _shade(color, 0.6), (sx + 13, body_top + 14), 5)
    # Kopf mit Hörnern oder Maske
    head_y = body_top + 8
    _outline_circle(screen, _shade(color, 0.7), (sx, head_y), 7)
    # Rote Augen
    pygame.draw.circle(screen, (255, 100, 60), (sx - 3, head_y - 1), 2)
    pygame.draw.circle(screen, (255, 100, 60), (sx + 3, head_y - 1), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, head_y - 1), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, head_y - 1), 1)
    # Wilde Mähne (Hörner-artig)
    pygame.draw.polygon(screen, (60, 30, 20),
                        [(sx - 8, head_y - 4), (sx - 12, head_y - 10), (sx - 4, head_y - 6)])
    pygame.draw.polygon(screen, (60, 30, 20),
                        [(sx + 8, head_y - 4), (sx + 12, head_y - 10), (sx + 4, head_y - 6)])
    # Doppel-Axt (über Kopf, dual wield)
    import math
    swing = math.sin(e.walk_phase) * 0.4
    for side in (-1, 1):
        ax = sx + side * (14 + int(math.cos(e.walk_phase) * 2))
        ay_top = body_top - 4
        pygame.draw.line(screen, (90, 60, 30), (sx + side * 12, body_top + 14),
                         (ax, ay_top), 3)
        # Klinge
        bl_x = ax
        bl_y = ay_top
        pygame.draw.polygon(screen, (200, 200, 180), [
            (bl_x, bl_y - 4),
            (bl_x + side * 5, bl_y - 8),
            (bl_x + side * 6, bl_y),
            (bl_x + side * 4, bl_y + 3),
        ])
        pygame.draw.polygon(screen, BLACK, [
            (bl_x, bl_y - 4),
            (bl_x + side * 5, bl_y - 8),
            (bl_x + side * 6, bl_y),
            (bl_x + side * 4, bl_y + 3),
        ], 1)


def _draw_lurker_iso(screen, e, sx, sy):
    """Schatten-Lurker: semi-transparent wenn weit weg, glühende Augen."""
    import math as _m
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Pulsiertes Schatten-Glow
    pulse = abs(_m.sin(e.wobble * 1.5))
    aura = pygame.Surface((h * 2, h * 2), pygame.SRCALPHA)
    pygame.draw.circle(aura, (60, 30, 120, int(60 + pulse * 40)),
                       (h, h), e.radius + 8)
    screen.blit(aura, (sx - h, sy - h))
    # Schattengestalt (Tropfen-Form)
    body_pts = [
        (sx - 12, sy - 4),
        (sx, body_top + 8),
        (sx + 12, sy - 4),
        (sx + 8, sy + 8),
        (sx - 8, sy + 8),
    ]
    pygame.draw.polygon(screen, color, body_pts)
    pygame.draw.polygon(screen, BLACK, body_pts, 2)
    # Glühende Wisp-Linien
    for dy in (-4, 0, 4):
        pygame.draw.line(screen, e.glow,
                         (sx - 10, sy + dy), (sx + 10, sy + dy), 1)
    # Glühende Augen (gross)
    eye_y = body_top + 12
    pygame.draw.circle(screen, e.glow, (sx - 4, eye_y), 3)
    pygame.draw.circle(screen, e.glow, (sx + 4, eye_y), 3)
    pygame.draw.circle(screen, WHITE, (sx - 4, eye_y), 1)
    pygame.draw.circle(screen, WHITE, (sx + 4, eye_y), 1)


def _draw_slime_iso(screen, e, sx, sy):
    """Schleim: blob mit pulsiertem Körper, transparente Hülle."""
    import math as _m
    color = _tint(e.color, e.hit_flash)
    h = e.height
    pulse = abs(_m.sin(e.wobble * 2))
    body_h = int(h * (0.7 + pulse * 0.2))
    # Hauptkörper (Tropfen / Halbkugel)
    body_rect = pygame.Rect(sx - e.radius, sy - body_h,
                              e.radius * 2, body_h)
    pygame.draw.ellipse(screen, color, body_rect)
    pygame.draw.ellipse(screen, BLACK, body_rect, 2)
    # Glanz-Highlight
    pygame.draw.ellipse(screen, _shade(color, 1.4),
                         (sx - e.radius + 4, sy - body_h + 4,
                          e.radius - 4, body_h // 3))
    # Augen
    eye_y = sy - body_h // 2
    pygame.draw.circle(screen, BLACK, (sx - 4, eye_y), 3)
    pygame.draw.circle(screen, BLACK, (sx + 4, eye_y), 3)
    pygame.draw.circle(screen, WHITE, (sx - 3, eye_y - 1), 1)
    pygame.draw.circle(screen, WHITE, (sx + 5, eye_y - 1), 1)
    # Tropfen am Boden
    pygame.draw.ellipse(screen, _shade(color, 0.6),
                         (sx - e.radius - 2, sy - 3, e.radius * 2 + 4, 6))


# ============================================================
# BOSSE
# ============================================================
def _draw_boss_necromancer(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Schwebende dunkle Wolke unter
    cloud = pygame.Surface((h * 2, 16), pygame.SRCALPHA)
    for i in range(3):
        pygame.draw.ellipse(cloud, (60, 20, 80, 100 - i * 25),
                            (i * 8, i * 3, h * 2 - i * 16, 14 - i * 3))
    screen.blit(cloud, (sx - h, sy - 8))

    # Hohe Robe
    robe_pts = [
        (sx - 14, sy + 2),
        (sx - 10, body_top + 16),
        (sx + 10, body_top + 16),
        (sx + 14, sy + 2),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.7), robe_pts)
    pygame.draw.polygon(screen, BLACK, robe_pts, 2)
    # Pentagramm-Linien
    pygame.draw.line(screen, e.glow, (sx, body_top + 20), (sx, sy - 4), 1)
    pygame.draw.line(screen, e.glow, (sx - 10, sy - 8), (sx + 10, sy - 8), 1)
    pygame.draw.line(screen, e.glow, (sx - 8, sy - 16), (sx + 8, sy + 2), 1)
    pygame.draw.line(screen, e.glow, (sx + 8, sy - 16), (sx - 8, sy + 2), 1)

    # Hohe spitze Kapuze
    head_y = body_top + 10
    pygame.draw.polygon(screen, _shade(color, 0.4), [
        (sx - 11, head_y + 8), (sx + 11, head_y + 8),
        (sx, head_y - 16),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 11, head_y + 8), (sx + 11, head_y + 8),
        (sx, head_y - 16),
    ], 2)
    pygame.draw.circle(screen, _shade(color, 0.3), (sx, head_y + 2), 7)
    pygame.draw.circle(screen, e.glow, (sx - 3, head_y + 2), 2)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y + 2), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, head_y + 2), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, head_y + 2), 1)

    # Stab mit Totenschädel (rechts)
    stx = sx + 16
    sty_top = body_top - 8
    sty_bot = sy + 4
    pygame.draw.line(screen, (60, 40, 20), (stx, sty_top), (stx, sty_bot), 3)
    # Schädel
    glow = pygame.Surface((28, 28), pygame.SRCALPHA)
    pygame.draw.circle(glow, (180, 80, 240, 120), (14, 14), 12)
    screen.blit(glow, (stx - 14, sty_top - 14))
    pygame.draw.circle(screen, (220, 210, 190), (stx, sty_top), 6)
    pygame.draw.circle(screen, BLACK, (stx - 2, sty_top - 1), 2)
    pygame.draw.circle(screen, BLACK, (stx + 2, sty_top - 1), 2)
    pygame.draw.circle(screen, e.glow, (stx - 2, sty_top - 1), 1)
    pygame.draw.circle(screen, e.glow, (stx + 2, sty_top - 1), 1)
    pygame.draw.line(screen, BLACK, (stx - 3, sty_top + 3), (stx + 3, sty_top + 3), 1)


def _draw_boss_frostlord(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h

    # Eisige Aura
    aura = pygame.Surface((h * 3, h * 3), pygame.SRCALPHA)
    for i in range(5, 0, -1):
        pygame.draw.circle(aura, (140, 200, 255, 30 // i),
                           (int(h * 1.5), int(h * 1.5)), e.radius + i * 5)
    screen.blit(aura, (sx - int(h * 1.5), sy - h - int(h * 0.5)))

    # Plattenbeine
    for side in (-1, 1):
        x = sx + side * 7
        pygame.draw.rect(screen, _shade(color, 0.6), (x - 6, sy - 14, 12, 14))
        pygame.draw.rect(screen, FROST, (x - 6, sy - 14, 12, 14), 1)
        # Kniegelenk
        pygame.draw.rect(screen, _shade(color, 1.2), (x - 4, sy - 8, 8, 2))

    # Riesiger Rumpf
    torso_pts = [
        (sx - 18, sy - 14),
        (sx + 18, sy - 14),
        (sx + 14, body_top + 16),
        (sx - 14, body_top + 16),
    ]
    pygame.draw.polygon(screen, color, torso_pts)
    pygame.draw.polygon(screen, FROST, torso_pts, 3)
    # Brustplatte mit V
    pygame.draw.polygon(screen, _shade(color, 1.4), [
        (sx - 8, body_top + 20),
        (sx + 8, body_top + 20),
        (sx + 10, sy - 8),
        (sx, sy - 16),
        (sx - 10, sy - 8),
    ])
    # Schultern (groß, eisig)
    for side in (-1, 1):
        x = sx + side * 18
        pygame.draw.circle(screen, _shade(color, 0.5), (x, body_top + 20), 8)
        pygame.draw.circle(screen, FROST, (x, body_top + 20), 8, 2)
        # Eisspitzen oben
        pygame.draw.polygon(screen, (220, 240, 255), [
            (x - 3, body_top + 14), (x + 3, body_top + 14),
            (x, body_top + 6),
        ])

    # Helm mit Eis-Krone
    head_y = body_top + 10
    _outline_circle(screen, _shade(color, 0.5), (sx, head_y), 8)
    pygame.draw.circle(screen, FROST, (sx, head_y), 8, 1)
    # Krone: 5 Spitzen
    for k in range(-2, 3):
        spike_x = sx + k * 4
        spike_y_base = head_y - 8
        spike_h = 10 - abs(k) * 2
        pygame.draw.polygon(screen, (220, 240, 255), [
            (spike_x - 2, spike_y_base), (spike_x + 2, spike_y_base),
            (spike_x, spike_y_base - spike_h),
        ])
    # Augen
    pygame.draw.circle(screen, (180, 230, 255), (sx - 3, head_y), 2)
    pygame.draw.circle(screen, (180, 230, 255), (sx + 3, head_y), 2)
    pygame.draw.circle(screen, WHITE, (sx - 3, head_y), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, head_y), 1)

    # Eis-Großschwert (gehoben)
    bx1 = sx + 18
    by1 = body_top + 12
    bx2 = sx + 28
    by2 = body_top - 14
    pygame.draw.line(screen, (60, 40, 20), (bx1, by1), (bx1 + 2, by1 - 6), 4)
    pygame.draw.polygon(screen, (200, 230, 255), [
        (bx1, by1 - 6), (bx1 + 6, by1 - 8),
        (bx2 + 4, by2), (bx2 - 2, by2 + 4),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (bx1, by1 - 6), (bx1 + 6, by1 - 8),
        (bx2 + 4, by2), (bx2 - 2, by2 + 4),
    ], 1)
    pygame.draw.line(screen, WHITE, (bx1 + 2, by1 - 5), (bx2, by2 + 2), 1)


def _draw_boss_dragon(screen, e, sx, sy):
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    wing_phase = math.sin(e.wobble) * 5

    # Hinterbeine + Vorderbeine (4-beinig)
    for side, leg_off in ((-1, sy - 12), (1, sy - 12)):
        x = sx + side * 14
        pygame.draw.rect(screen, _shade(color, 0.6),
                         (x - 4, leg_off, 8, 12))
        # Klauen
        for k in (-2, 0, 2):
            pygame.draw.line(screen, (240, 220, 180),
                             (x + k, sy), (x + k, sy + 4), 2)

    # Flügel hinter dem Körper
    for side in (-1, 1):
        wing_pts = [
            (sx + side * 8, body_top + 20),
            (sx + side * 32, body_top + 4 + int(wing_phase)),
            (sx + side * 36, body_top + 22),
            (sx + side * 30, body_top + 28),
            (sx + side * 14, body_top + 22),
        ]
        pygame.draw.polygon(screen, _shade(color, 0.5), wing_pts)
        pygame.draw.polygon(screen, BLACK, wing_pts, 2)
        # Flügeladern
        for k in range(3):
            pygame.draw.line(screen, _shade(color, 0.3),
                             (sx + side * 10, body_top + 22 + k * 2),
                             (sx + side * (28 - k * 4), body_top + 12 + k * 4 + int(wing_phase // 2)), 1)

    # Schwanz hinten (vom Körper weg)
    tail_phase = math.sin(e.wobble * 1.5) * 4
    tail_pts = [
        (sx - 12, sy - 4),
        (sx - 24 + int(tail_phase), sy + 4),
        (sx - 34 - int(tail_phase), sy + 2),
        (sx - 28, sy - 4),
    ]
    pygame.draw.polygon(screen, color, tail_pts)
    pygame.draw.polygon(screen, BLACK, tail_pts, 2)
    # Schwanz-Spike
    pygame.draw.polygon(screen, (60, 20, 10), [
        (sx - 34, sy + 2), (sx - 38, sy - 2), (sx - 32, sy - 4),
    ])

    # Hauptkörper (breit und massiv)
    body_pts = [
        (sx - 18, sy - 6),
        (sx + 18, sy - 6),
        (sx + 16, body_top + 18),
        (sx - 16, body_top + 18),
    ]
    pygame.draw.polygon(screen, color, body_pts)
    pygame.draw.polygon(screen, BLACK, body_pts, 2)
    # Schuppen
    for dy in range(body_top + 22, sy - 8, 4):
        for dx in range(-14, 15, 5):
            if abs(dx) + (dy - body_top - 20) // 2 < 14:
                pygame.draw.arc(screen, _shade(color, 1.3),
                                (sx + dx - 2, dy - 2, 4, 4),
                                0, math.pi, 1)
    # Rückenstacheln
    for k in range(-3, 4):
        pygame.draw.polygon(screen, (60, 20, 10), [
            (sx + k * 4 - 2, body_top + 20),
            (sx + k * 4 + 2, body_top + 20),
            (sx + k * 4, body_top + 10),
        ])

    # Drachenkopf (groß, vorne)
    head_pts = [
        (sx - 8, body_top + 8),
        (sx + 8, body_top + 8),
        (sx + 12, body_top + 22),
        (sx - 12, body_top + 22),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.7), head_pts)
    pygame.draw.polygon(screen, BLACK, head_pts, 2)
    # Maul
    pygame.draw.rect(screen, BLACK, (sx - 8, body_top + 18, 16, 4))
    # Reißzähne
    for k in (-6, -2, 2, 6):
        pygame.draw.polygon(screen, WHITE, [
            (sx + k, body_top + 22), (sx + k + 1, body_top + 26),
            (sx + k + 2, body_top + 22),
        ])
    # Glühendes Feuer im Maul
    glow = pygame.Surface((24, 8), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (255, 120, 40, 200), (0, 0, 24, 8))
    screen.blit(glow, (sx - 12, body_top + 19))
    # Hörner
    pygame.draw.polygon(screen, (40, 20, 10), [
        (sx - 8, body_top + 8), (sx - 14, body_top - 6), (sx - 4, body_top + 4),
    ])
    pygame.draw.polygon(screen, (40, 20, 10), [
        (sx + 8, body_top + 8), (sx + 14, body_top - 6), (sx + 4, body_top + 4),
    ])
    # Glühende Augen
    pygame.draw.circle(screen, (255, 200, 80), (sx - 3, body_top + 14), 3)
    pygame.draw.circle(screen, (255, 200, 80), (sx + 3, body_top + 14), 3)
    pygame.draw.circle(screen, WHITE, (sx - 3, body_top + 14), 1)
    pygame.draw.circle(screen, WHITE, (sx + 3, body_top + 14), 1)


# ============================================================
# LICHT-EMITTER (für lighting.py: welche Sprites geben Licht ab)
# ============================================================
def draw_item_icon(screen, item, rect):
    """Zeichnet ein detailliertes Item-Sprite in den gegebenen Rect (z.B. Inventar-Slot).

    Größe passt sich rect.w / rect.h an. Farbe leitet sich von Rarity ab.

    Prio-Pass HOCH (VELGRAD_SPRITE_BIBEL §XII): Unique-Items mit Lore-
    Namen aus VELGRAD_ITEMS_UNIQUE_BIBEL (50 Stück) bekommen automatisch
    den AI-generierten 128×128-Icon, sobald das PNG vorliegt.  Procedural-
    Slot-Icon (sword/helmet/...) bleibt Fallback für alle anderen.
    """
    from .constants import RARITY_COLOR
    col = RARITY_COLOR[item.rarity]
    col_dark = _shade(col, 0.55)
    col_bright = _shade(col, 1.3)
    cx, cy = rect.x + rect.w // 2, rect.y + rect.h // 2
    s = min(rect.w, rect.h)

    # Hintergrund-Glow (rarity-farbig) — vor jedem Icon-Stil
    glow = pygame.Surface((s, s), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*col, 60), (s // 2, s // 2), s // 2 - 2)
    screen.blit(glow, (rect.x, rect.y))

    # Step 1: AI-Unique-Icon-Pfad (silent fallback wenn PNG fehlt)
    if item.rarity == 'unique':
        ai = get_item_unique_icon(item.name)
        if ai is not None:
            cached_key = ('_uniqitem', item.name, s)
            scaled = _UNIQUE_ICON_SCALED.get(cached_key)
            if scaled is None:
                ai_w, ai_h = ai.get_size()
                # In rect einpassen, Aspect-Ratio bewahren
                scale = (s - 4) / max(ai_w, ai_h)
                tw, th = max(1, int(ai_w * scale)), max(1, int(ai_h * scale))
                scaled = pygame.transform.smoothscale(ai, (tw, th))
                _UNIQUE_ICON_SCALED[cached_key] = scaled
            sw_, sh_ = scaled.get_size()
            screen.blit(scaled, (cx - sw_ // 2, cy - sh_ // 2))
            return

    if item.slot == 'weapon':
        _icon_sword(screen, cx, cy, s, col, col_dark, col_bright)
    elif item.slot == 'helmet':
        _icon_helmet(screen, cx, cy, s, col, col_dark, col_bright)
    elif item.slot == 'chest':
        _icon_chest(screen, cx, cy, s, col, col_dark, col_bright)
    elif item.slot == 'ring':
        _icon_ring(screen, cx, cy, s, col, col_dark, col_bright)
    elif item.slot == 'amulet':
        _icon_amulet(screen, cx, cy, s, col, col_dark, col_bright)


# Per-Item-Name + Slot-Size Cache für skalierte Unique-Icons
_UNIQUE_ICON_SCALED: dict[tuple, pygame.Surface] = {}


def _icon_sword(screen, cx, cy, s, col, dark, bright):
    # Klinge (Diagonal)
    blade_len = s * 0.55
    grip_x1 = cx - int(blade_len * 0.5)
    grip_y1 = cy + int(blade_len * 0.5)
    tip_x = cx + int(blade_len * 0.5)
    tip_y = cy - int(blade_len * 0.5)
    # Schatten der Klinge
    pygame.draw.line(screen, BLACK, (grip_x1, grip_y1 + 2), (tip_x, tip_y + 2), 5)
    # Klinge
    pygame.draw.line(screen, bright, (grip_x1, grip_y1), (tip_x, tip_y), 4)
    pygame.draw.line(screen, WHITE, (grip_x1, grip_y1), (tip_x, tip_y), 1)
    # Spitze (Diamant)
    pygame.draw.circle(screen, WHITE, (tip_x, tip_y), 2)
    # Parierstange (Quer)
    perp_x = (grip_x1 + cx) // 2 - cy // 6
    perp_y = (grip_y1 + cy) // 2 + cx // 6
    cross_dx = int(s * 0.12)
    cross_dy = int(s * 0.12)
    pygame.draw.line(screen, GOLD,
                     (perp_x - cross_dx, perp_y + cross_dy),
                     (perp_x + cross_dx, perp_y - cross_dy), 4)
    pygame.draw.line(screen, GOLD_BRIGHT,
                     (perp_x - cross_dx, perp_y + cross_dy),
                     (perp_x + cross_dx, perp_y - cross_dy), 2)
    # Griff
    grip_x2 = grip_x1 - int(s * 0.10)
    grip_y2 = grip_y1 + int(s * 0.10)
    pygame.draw.line(screen, (60, 40, 25), (grip_x1, grip_y1), (grip_x2, grip_y2), 4)
    # Pommel
    pygame.draw.circle(screen, GOLD, (grip_x2, grip_y2), 4)
    pygame.draw.circle(screen, GOLD_BRIGHT, (grip_x2 - 1, grip_y2 - 1), 2)
    pygame.draw.circle(screen, col, (grip_x2, grip_y2), 4, 1)


def _icon_helmet(screen, cx, cy, s, col, dark, bright):
    w = int(s * 0.62)
    h = int(s * 0.55)
    # Helm-Körper (Trapezoid)
    pts = [
        (cx - w // 2, cy + h // 4),
        (cx - w // 2 + 4, cy - h // 2),
        (cx + w // 2 - 4, cy - h // 2),
        (cx + w // 2, cy + h // 4),
        (cx + w // 2 - 6, cy + h // 4 + 4),
        (cx - w // 2 + 6, cy + h // 4 + 4),
    ]
    pygame.draw.polygon(screen, col, pts)
    pygame.draw.polygon(screen, BLACK, pts, 2)
    # Helm-Highlight oben
    pygame.draw.polygon(screen, bright, [
        (cx - w // 2 + 4, cy - h // 2 + 2),
        (cx, cy - h // 2 + 2),
        (cx, cy - h // 4),
        (cx - w // 2 + 6, cy - h // 4 + 2),
    ])
    # Visier (horizontaler Schlitz)
    pygame.draw.rect(screen, BLACK, (cx - w // 2 + 4, cy - 2, w - 8, 4))
    pygame.draw.line(screen, (255, 80, 60), (cx - w // 2 + 6, cy),
                     (cx + w // 2 - 6, cy), 1)
    # Plume (rote Federbusch oben)
    plume_pts = [
        (cx - 4, cy - h // 2),
        (cx, cy - h // 2 - 8),
        (cx + 4, cy - h // 2),
    ]
    pygame.draw.polygon(screen, (180, 40, 40), plume_pts)
    pygame.draw.polygon(screen, (220, 60, 60), plume_pts, 1)


def _icon_chest(screen, cx, cy, s, col, dark, bright):
    w = int(s * 0.62)
    h = int(s * 0.65)
    # Breastplate-Umriss (V-förmig)
    pts = [
        (cx - w // 2 + 4, cy - h // 2 + 4),
        (cx + w // 2 - 4, cy - h // 2 + 4),
        (cx + w // 2, cy + h // 2 - 4),
        (cx, cy + h // 2),
        (cx - w // 2, cy + h // 2 - 4),
    ]
    pygame.draw.polygon(screen, col, pts)
    pygame.draw.polygon(screen, BLACK, pts, 2)
    # Brustplatten-Highlight (V-Linie)
    pygame.draw.polygon(screen, bright, [
        (cx - w // 4, cy - h // 2 + 6),
        (cx, cy - 4),
        (cx + w // 4, cy - h // 2 + 6),
    ])
    # Schultern (Kreise)
    pygame.draw.circle(screen, dark, (cx - w // 2 + 4, cy - h // 2 + 6), 4)
    pygame.draw.circle(screen, BLACK, (cx - w // 2 + 4, cy - h // 2 + 6), 4, 1)
    pygame.draw.circle(screen, dark, (cx + w // 2 - 4, cy - h // 2 + 6), 4)
    pygame.draw.circle(screen, BLACK, (cx + w // 2 - 4, cy - h // 2 + 6), 4, 1)
    # Gürtel
    pygame.draw.rect(screen, GOLD, (cx - w // 2 + 4, cy + h // 4, w - 8, 4))
    pygame.draw.rect(screen, BLACK, (cx - w // 2 + 4, cy + h // 4, w - 8, 4), 1)
    # Schnalle
    pygame.draw.rect(screen, GOLD_BRIGHT, (cx - 3, cy + h // 4, 6, 4))


def _icon_ring(screen, cx, cy, s, col, dark, bright):
    r = int(s * 0.28)
    # Ring-Band
    pygame.draw.circle(screen, dark, (cx, cy + 4), r + 2)
    pygame.draw.circle(screen, col, (cx, cy + 4), r)
    pygame.draw.circle(screen, BLACK, (cx, cy + 4), r, 2)
    pygame.draw.circle(screen, (32, 24, 16), (cx, cy + 4), r - 4)
    # Edelstein on top (Raute)
    gem_y = cy - r // 2 - 2
    gem_size = max(4, int(s * 0.15))
    gem_pts = [
        (cx, gem_y - gem_size),
        (cx + gem_size, gem_y),
        (cx, gem_y + gem_size),
        (cx - gem_size, gem_y),
    ]
    # Schatten unter Gem
    pygame.draw.polygon(screen, BLACK, [(p[0], p[1] + 2) for p in gem_pts])
    pygame.draw.polygon(screen, bright, gem_pts)
    pygame.draw.polygon(screen, WHITE, gem_pts, 1)
    # Facetten-Highlight
    pygame.draw.polygon(screen, WHITE, [
        (cx, gem_y - gem_size + 1),
        (cx + gem_size - 2, gem_y),
        (cx, gem_y),
    ])


def _icon_amulet(screen, cx, cy, s, col, dark, bright):
    # Kette (zwei Bögen oben)
    chain_y = cy - int(s * 0.3)
    pygame.draw.arc(screen, (180, 160, 100),
                    (cx - int(s * 0.35), chain_y - 2, int(s * 0.35), int(s * 0.35)),
                    0.2, 2.9, 2)
    pygame.draw.arc(screen, (180, 160, 100),
                    (cx, chain_y - 2, int(s * 0.35), int(s * 0.35)),
                    0.2, 2.9, 2)
    # Aufhängung
    pygame.draw.line(screen, (140, 120, 80),
                     (cx - 2, cy - 4), (cx + 2, cy - 4), 2)
    # Pendant Form (Diamant + Kreis)
    pendant_y = cy + 2
    pendant_size = int(s * 0.20)
    # Schatten
    pygame.draw.circle(screen, BLACK, (cx, pendant_y + 2), pendant_size + 1)
    # Rahmen
    pygame.draw.circle(screen, GOLD, (cx, pendant_y), pendant_size + 2)
    pygame.draw.circle(screen, BLACK, (cx, pendant_y), pendant_size + 2, 1)
    # Stein (von Rarity-Farbe)
    pygame.draw.circle(screen, col, (cx, pendant_y), pendant_size)
    pygame.draw.circle(screen, bright, (cx - 2, pendant_y - 2), pendant_size // 2)
    pygame.draw.circle(screen, WHITE, (cx - 3, pendant_y - 3), 2)


def draw_npc_at(screen, npc, sx, sy):
    """Stadt-NPC: einfaches humanoides Sprite.

    Update #135 (O-22): Pro NPC-Kind eine Idle-Fidget-Animation —
    Korven schmiedet (Hammer-Bob), Otreth schleift (Funken-Spawn),
    Mara liest (Page-Flip), Tameris wischt (Putztuch-Sweep), Eldon
    schreibt (Buch-Schreib-Geste).  Visuelle Lebendigkeit für
    Brassweir („Statuen-Park"-Problem aus User-Feedback).

    Trigger pro NPC: `npc._fidget_t` zählt rückwärts;  bei <=0 wird
    eine 0.8 s Idle-Anim ausgelöst.  Anim-Dauer in `npc._fidget_left`.
    """
    import math
    sx, sy = int(sx), int(sy)
    _ground_shadow(screen, sx, sy, 28)
    color = npc.color
    # Bob (Atmen)
    npc.bob += 0.04
    bob = math.sin(npc.bob) * 1.5
    # Update #135 (O-22): Fidget-Tick + Auto-Trigger alle 4-8 s
    import random as _r
    if not hasattr(npc, '_fidget_t'):
        npc._fidget_t = _r.uniform(2.0, 6.0)
        npc._fidget_left = 0.0
        npc._fidget_kind = None
    npc._fidget_t -= 0.016  # approx 60 FPS
    if npc._fidget_left > 0:
        npc._fidget_left -= 0.016
    elif npc._fidget_t <= 0:
        # Neue Fidget-Anim starten
        npc._fidget_t = _r.uniform(4.0, 8.0)
        npc._fidget_left = 0.9
        # Default-Fidget pro Kind (kann via npc._fidget_kind override)
        DEFAULT_FIDGETS = {
            'smith':     'hammer',     # Otreth/Smith: Hammer-Schlag
            'vendor':    'count_coin', # Korven: Münze prüfen
            'mystic':    'page_flip',  # Mara: Buch blättern
            'innkeeper': 'wipe',       # Tameris: Tresen wischen
            'quest':     'gesture',    # Eldon: zur Anschlagtafel gestikulieren
            'stash':     'inspect',    # Mahnmal-Verwahrer: Truhen-Check
        }
        npc._fidget_kind = DEFAULT_FIDGETS.get(npc.kind, 'gesture')
    body_top = sy - 38
    # Robe / Körper
    pygame.draw.polygon(screen, _shade(color, 0.6), [
        (sx - 10, sy + bob),
        (sx - 7, body_top + 14 + bob),
        (sx + 7, body_top + 14 + bob),
        (sx + 10, sy + bob),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 10, sy + bob),
        (sx - 7, body_top + 14 + bob),
        (sx + 7, body_top + 14 + bob),
        (sx + 10, sy + bob),
    ], 2)
    # Schultern
    pygame.draw.circle(screen, _shade(color, 0.5), (sx - 8, body_top + 12 + int(bob)), 3)
    pygame.draw.circle(screen, _shade(color, 0.5), (sx + 8, body_top + 12 + int(bob)), 3)
    # Kopf
    head_y = body_top + 6 + int(bob)
    _outline_circle(screen, (220, 190, 160), (sx, head_y), 6)
    pygame.draw.circle(screen, BLACK, (sx - 2, head_y - 1), 1)
    pygame.draw.circle(screen, BLACK, (sx + 2, head_y - 1), 1)
    # Kennzeichnung (kleines Symbol über Kopf)
    label_y = body_top - 4
    if npc.kind == 'vendor':
        # Goldsymbol
        pygame.draw.circle(screen, GOLD_BRIGHT, (sx, label_y), 5)
        pygame.draw.circle(screen, BLACK, (sx, label_y), 5, 1)
    elif npc.kind == 'stash':
        # Truhe
        pygame.draw.rect(screen, (140, 100, 60), (sx - 6, label_y - 3, 12, 8))
        pygame.draw.rect(screen, BLACK, (sx - 6, label_y - 3, 12, 8), 1)
        pygame.draw.line(screen, GOLD, (sx - 6, label_y + 1), (sx + 6, label_y + 1), 1)
    elif npc.kind == 'mystic':
        # Stern
        pts = []
        for k in range(5):
            a = k * math.pi * 2 / 5 - math.pi / 2
            pts.append((sx + math.cos(a) * 5, label_y + math.sin(a) * 5))
            a2 = (k + 0.5) * math.pi * 2 / 5 - math.pi / 2
            pts.append((sx + math.cos(a2) * 2, label_y + math.sin(a2) * 2))
        pygame.draw.polygon(screen, (200, 120, 240), pts)
        pygame.draw.polygon(screen, BLACK, pts, 1)
    elif npc.kind == 'smith':
        # Hammer-Symbol
        pygame.draw.rect(screen, (180, 80, 30), (sx - 5, label_y - 4, 10, 8))
        pygame.draw.rect(screen, BLACK, (sx - 5, label_y - 4, 10, 8), 1)
        pygame.draw.line(screen, (90, 60, 30), (sx, label_y + 4), (sx, label_y + 10), 2)
    elif npc.kind == 'quest':
        # Ausrufezeichen
        pygame.draw.rect(screen, GOLD_BRIGHT, (sx - 1, label_y - 4, 3, 6))
        pygame.draw.rect(screen, GOLD_BRIGHT, (sx - 1, label_y + 4, 3, 2))
        pygame.draw.rect(screen, BLACK, (sx - 1, label_y - 4, 3, 6), 1)
        pygame.draw.rect(screen, BLACK, (sx - 1, label_y + 4, 3, 2), 1)
    elif npc.kind == 'innkeeper':
        # Bierkrug
        pygame.draw.rect(screen, (200, 160, 90), (sx - 4, label_y - 3, 8, 7))
        pygame.draw.rect(screen, BLACK, (sx - 4, label_y - 3, 8, 7), 1)
        pygame.draw.arc(screen, BLACK, (sx + 2, label_y - 2, 5, 5), -1.5, 1.5, 1)
        pygame.draw.rect(screen, WHITE, (sx - 3, label_y - 3, 6, 2))

    # Update #135 (O-22): NPC-Idle-Fidget-Animation pro Kind.  Wird über
    # 0.9 s gerendert wenn `_fidget_left > 0`.  Verschiedene Posen für
    # die 6 Brassweir-NPC-Rollen — Lore-konforme Mikro-Animation.
    if getattr(npc, '_fidget_left', 0) > 0:
        f_t = 1.0 - (npc._fidget_left / 0.9)  # 0..1
        fk = getattr(npc, '_fidget_kind', None)
        hand_y = body_top + 12 + int(bob)
        if fk == 'hammer':
            # Otreth: Hammer hoch/runter (Sinus-Schwung)
            ham_swing = math.sin(f_t * math.pi * 2) * 8
            ham_x = sx + 12
            ham_y = hand_y - 8 + int(ham_swing)
            pygame.draw.line(screen, (70, 50, 30),
                              (sx + 6, hand_y), (ham_x, ham_y), 2)
            pygame.draw.rect(screen, (140, 110, 80),
                              (ham_x - 3, ham_y - 4, 6, 6))
            pygame.draw.rect(screen, BLACK,
                              (ham_x - 3, ham_y - 4, 6, 6), 1)
            # Funken am Aufschlagpunkt
            if f_t > 0.4 and f_t < 0.6:
                for _ in range(3):
                    fx = sx + 14 + int(math.cos(f_t * 20) * 6)
                    fy = sy - 4 + int(math.sin(f_t * 18) * 4)
                    pygame.draw.circle(screen, (255, 200, 80),
                                        (fx, fy), 1)
        elif fk == 'count_coin':
            # Korven: Münze hochhalten + drehen (gold-Glitzer)
            coin_y = hand_y - 14 + int(math.sin(f_t * math.pi) * -4)
            r_x = max(1, abs(int(math.cos(f_t * math.pi * 4) * 3)))
            pygame.draw.ellipse(screen, (255, 215, 90),
                                 (sx + 7 - r_x, coin_y - 3,
                                  r_x * 2, 6))
            pygame.draw.ellipse(screen, (120, 80, 30),
                                 (sx + 7 - r_x, coin_y - 3,
                                  r_x * 2, 6), 1)
        elif fk == 'page_flip':
            # Mara: Buch aufgeschlagen mit Page-Flip
            book_y = hand_y - 6
            pygame.draw.rect(screen, (200, 180, 130),
                              (sx - 8, book_y, 16, 8))
            pygame.draw.rect(screen, (60, 44, 30),
                              (sx - 8, book_y, 16, 8), 1)
            # Mittellinie (Buchrücken)
            pygame.draw.line(screen, (60, 44, 30),
                              (sx, book_y), (sx, book_y + 8), 1)
            # Page-Flip: bei f_t > 0.5 fliegt rechte Seite hoch
            if f_t > 0.5:
                flip_h = int((f_t - 0.5) * 16)
                pygame.draw.polygon(screen, (240, 220, 170), [
                    (sx, book_y),
                    (sx + 8 - flip_h // 2, book_y - flip_h),
                    (sx + 8, book_y),
                ])
        elif fk == 'wipe':
            # Tameris: Putztuch-Sweep links-rechts
            sweep_x = sx + int(math.sin(f_t * math.pi * 2) * 12)
            rag_y = hand_y + 2
            pygame.draw.rect(screen, (220, 200, 160),
                              (sweep_x - 4, rag_y, 8, 4))
            pygame.draw.rect(screen, (90, 70, 50),
                              (sweep_x - 4, rag_y, 8, 4), 1)
            # Arm-Verbindung
            pygame.draw.line(screen, (180, 130, 80),
                              (sx + 8, hand_y),
                              (sweep_x, rag_y), 2)
        elif fk == 'gesture':
            # Eldon: zur Anschlagtafel gestikulieren (Arm hoch + zeigen)
            arm_a = math.pi * 0.25 + math.sin(f_t * math.pi * 3) * 0.2
            tip_x = sx + int(math.cos(arm_a) * 16)
            tip_y = hand_y - int(math.sin(arm_a) * 12)
            pygame.draw.line(screen, (180, 130, 80),
                              (sx + 7, hand_y),
                              (tip_x, tip_y), 2)
            pygame.draw.circle(screen, (220, 190, 160),
                                (tip_x, tip_y), 2)
        elif fk == 'inspect':
            # Mahnmal-Verwahrer: kniet und checkt eine Truhe (head-tilt)
            tilt = int(math.sin(f_t * math.pi) * 4)
            pygame.draw.line(screen, (140, 110, 80),
                              (sx - 6, sy + 2),
                              (sx - 12 + tilt, sy + 6), 2)
            # Truhen-Skizze unten links
            pygame.draw.rect(screen, (110, 80, 50),
                              (sx - 16, sy + 2, 10, 6))
            pygame.draw.rect(screen, BLACK,
                              (sx - 16, sy + 2, 10, 6), 1)


def draw_dungeon_portal_at(screen, portal, sx, sy):
    """Großes Dungeon-Portal mit Biom-spezifischer Farbe."""
    import math
    from .constants import DUNGEONS
    from .world import BIOMES
    sx, sy = int(sx), int(sy)
    spec = DUNGEONS[portal.dungeon_id]
    accent = BIOMES[spec['biome']]['accent']
    portal.bob += 0.05
    pulse = abs(math.sin(portal.bob * 2))

    # Großer Boden-Schatten
    _ground_shadow(screen, sx, sy, 50, alpha=160)

    # Aura
    glow = pygame.Surface((160, 160), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        alpha = int(50 / i * (0.6 + pulse * 0.4))
        pygame.draw.circle(glow, (*accent, alpha), (80, 80), 30 + i * 8)
    screen.blit(glow, (sx - 80, sy - 80))

    # Säulen-Bogen
    pygame.draw.rect(screen, (70, 60, 50), (sx - 30, sy - 10, 8, 60))
    pygame.draw.rect(screen, BLACK, (sx - 30, sy - 10, 8, 60), 2)
    pygame.draw.rect(screen, (70, 60, 50), (sx + 22, sy - 10, 8, 60))
    pygame.draw.rect(screen, BLACK, (sx + 22, sy - 10, 8, 60), 2)
    # Bogenoberteil
    pygame.draw.arc(screen, (70, 60, 50),
                    (sx - 30, sy - 50, 60, 80), 0, math.pi, 6)

    # Portal-Wirbel
    portal_rect = pygame.Rect(sx - 22, sy - 10, 44, 60)
    pygame.draw.ellipse(screen, (*accent, 200), portal_rect)
    pygame.draw.ellipse(screen, accent, portal_rect, 3)
    for k in range(3):
        a = portal.bob * 2 + k * 2
        px = sx + math.cos(a) * 8
        py = sy + 14 + math.sin(a) * 14
        pygame.draw.circle(screen, WHITE, (int(px), int(py)), 2)


def _draw_boss_bone_knight(screen, e, sx, sy):
    """Knochenritter: massive Plattenrüstung mit Schädel-Helm + Greatsword."""
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Beine
    for side in (-1, 1):
        x = sx + side * 7
        pygame.draw.rect(screen, _shade(color, 0.5), (x - 5, sy - 12, 10, 12))
        pygame.draw.rect(screen, BLACK, (x - 5, sy - 12, 10, 12), 1)
    # Großer Rumpf
    pygame.draw.polygon(screen, color, [
        (sx - 16, sy - 12), (sx + 16, sy - 12),
        (sx + 14, body_top + 14), (sx - 14, body_top + 14),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 16, sy - 12), (sx + 16, sy - 12),
        (sx + 14, body_top + 14), (sx - 14, body_top + 14),
    ], 2)
    # Brustplatte mit Kreuz
    pygame.draw.polygon(screen, _shade(color, 1.2), [
        (sx - 7, body_top + 18), (sx + 7, body_top + 18),
        (sx + 8, sy - 10), (sx, sy - 14), (sx - 8, sy - 10),
    ])
    pygame.draw.line(screen, GOLD, (sx, body_top + 20), (sx, sy - 12), 2)
    pygame.draw.line(screen, GOLD, (sx - 7, sy - 6), (sx + 7, sy - 6), 2)
    # Schultern (groß)
    for side in (-1, 1):
        x = sx + side * 16
        pygame.draw.circle(screen, _shade(color, 0.7), (x, body_top + 18), 7)
        pygame.draw.circle(screen, BLACK, (x, body_top + 18), 7, 2)
    # Schädel-Helm
    head_y = body_top + 8
    pygame.draw.circle(screen, (240, 230, 200), (sx, head_y), 9)
    pygame.draw.circle(screen, BLACK, (sx, head_y), 9, 2)
    # Augenhöhlen
    pygame.draw.circle(screen, BLACK, (sx - 3, head_y - 1), 2)
    pygame.draw.circle(screen, BLACK, (sx + 3, head_y - 1), 2)
    pygame.draw.circle(screen, e.glow, (sx - 3, head_y - 1), 1)
    pygame.draw.circle(screen, e.glow, (sx + 3, head_y - 1), 1)
    # Zähne
    pygame.draw.line(screen, BLACK, (sx - 5, head_y + 4), (sx + 5, head_y + 4), 1)
    for k in (-3, -1, 1, 3):
        pygame.draw.line(screen, BLACK,
                         (sx + k, head_y + 4), (sx + k, head_y + 6), 1)
    # Großschwert (rechts hoch)
    bx1, by1 = sx + 18, body_top + 14
    bx2, by2 = sx + 30, body_top - 16
    pygame.draw.line(screen, (60, 40, 20), (bx1, by1), (bx1 + 2, by1 - 6), 4)
    pygame.draw.polygon(screen, (230, 230, 210), [
        (bx1, by1 - 6), (bx1 + 6, by1 - 8),
        (bx2 + 2, by2), (bx2 - 2, by2 + 2),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (bx1, by1 - 6), (bx1 + 6, by1 - 8),
        (bx2 + 2, by2), (bx2 - 2, by2 + 2),
    ], 1)
    # Parierstange Gold
    pygame.draw.line(screen, GOLD, (bx1 - 4, by1 - 4), (bx1 + 8, by1 - 4), 3)


def _draw_boss_snow_queen(screen, e, sx, sy):
    """Schneekönigin: schlank, lange Robe mit Kristall-Krone."""
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    # Eisige Aura
    aura = pygame.Surface((h * 3, h * 3), pygame.SRCALPHA)
    for i in range(5, 0, -1):
        pygame.draw.circle(aura, (180, 220, 255, 30 // i),
                           (int(h * 1.5), int(h * 1.5)), e.radius + i * 4)
    screen.blit(aura, (sx - int(h * 1.5), sy - h - int(h * 0.5)))
    # Lange Eis-Robe (kein Bein)
    robe_pts = [
        (sx - 14, sy + 2),
        (sx - 8, body_top + 14),
        (sx + 8, body_top + 14),
        (sx + 14, sy + 2),
    ]
    pygame.draw.polygon(screen, _shade(color, 0.6), robe_pts)
    pygame.draw.polygon(screen, FROST, robe_pts, 2)
    # Bänder (vertikale Linien)
    for dx in (-6, 0, 6):
        pygame.draw.line(screen, (220, 240, 255),
                         (sx + dx, body_top + 18), (sx + dx, sy - 2), 1)
    # Hauptkörper / Bust
    pygame.draw.circle(screen, color, (sx, sy - 4), 10)
    pygame.draw.circle(screen, FROST, (sx, sy - 4), 10, 2)
    # Kopf
    head_y = body_top + 10
    _outline_circle(screen, (220, 230, 240), (sx, head_y), 7)
    # Augen
    pygame.draw.circle(screen, (140, 200, 255), (sx - 2, head_y - 1), 2)
    pygame.draw.circle(screen, (140, 200, 255), (sx + 2, head_y - 1), 2)
    pygame.draw.circle(screen, WHITE, (sx - 2, head_y - 1), 1)
    pygame.draw.circle(screen, WHITE, (sx + 2, head_y - 1), 1)
    # Eis-Krone (hohe Kristallspitzen)
    for k in range(-3, 4):
        spike_x = sx + k * 3
        spike_y_base = head_y - 6
        spike_h = 12 - abs(k) * 2
        pygame.draw.polygon(screen, (200, 230, 255), [
            (spike_x - 2, spike_y_base), (spike_x + 2, spike_y_base),
            (spike_x, spike_y_base - spike_h),
        ])
        pygame.draw.polygon(screen, WHITE, [
            (spike_x - 1, spike_y_base - 1), (spike_x + 1, spike_y_base - 1),
            (spike_x, spike_y_base - spike_h + 1),
        ], 1)
    # Eiszauberstab
    stx = sx + 14
    sty_top = body_top - 4
    sty_bot = sy + 2
    pygame.draw.line(screen, (180, 200, 230), (stx, sty_top), (stx, sty_bot), 3)
    # Kristall an Spitze
    import math
    pulse = abs(math.sin(e.wobble * 1.5))
    cr = 5 + int(pulse * 2)
    glow = pygame.Surface((cr * 5, cr * 5), pygame.SRCALPHA)
    pygame.draw.circle(glow, (140, 200, 255, 180),
                       (cr * 2 + 1, cr * 2 + 1), cr * 2)
    screen.blit(glow, (stx - cr * 2 - 1, sty_top - cr * 2 - 1))
    pygame.draw.polygon(screen, (220, 240, 255), [
        (stx, sty_top - cr), (stx + cr - 1, sty_top),
        (stx, sty_top + cr), (stx - cr + 1, sty_top),
    ])
    pygame.draw.polygon(screen, WHITE, [
        (stx, sty_top - cr + 1), (stx + cr - 2, sty_top),
        (stx, sty_top + cr - 1), (stx - cr + 2, sty_top),
    ], 1)


def _draw_boss_magma_golem(screen, e, sx, sy):
    """Magma-Golem: massiver Steinkörper mit Lava-Adern."""
    import math
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    pulse = abs(math.sin(e.wobble * 2))
    # Massive Beine
    for side in (-1, 1):
        x = sx + side * 9
        pygame.draw.rect(screen, _shade(color, 0.7), (x - 7, sy - 14, 14, 14))
        pygame.draw.rect(screen, BLACK, (x - 7, sy - 14, 14, 14), 2)
        # Lava-Risse
        pygame.draw.line(screen, (255, 140, 60),
                         (x - 3, sy - 12), (x + 3, sy - 4), 2)
    # Riesiger Steinrumpf
    body_pts = [
        (sx - 20, sy - 14),
        (sx + 20, sy - 14),
        (sx + 18, body_top + 18),
        (sx - 18, body_top + 18),
    ]
    pygame.draw.polygon(screen, color, body_pts)
    pygame.draw.polygon(screen, BLACK, body_pts, 2)
    # Lava-Adern (animiert)
    glow_a = int(150 + pulse * 80)
    for line_pts in [
        [(sx - 14, body_top + 22), (sx - 6, sy - 4), (sx + 4, sy - 14)],
        [(sx + 16, body_top + 22), (sx + 6, sy - 4), (sx - 6, sy - 16)],
        [(sx, body_top + 18), (sx - 4, sy - 4), (sx + 8, sy - 14)],
    ]:
        for i in range(len(line_pts) - 1):
            pygame.draw.line(screen, (255, glow_a // 2, 30),
                             line_pts[i], line_pts[i + 1], 3)
            pygame.draw.line(screen, (255, 220, 80),
                             line_pts[i], line_pts[i + 1], 1)
    # Arme (massive)
    for side in (-1, 1):
        sh_x = sx + side * 20
        sh_y = body_top + 18
        hand_x = sh_x + side * 6
        hand_y = sy - 10
        pygame.draw.line(screen, _shade(color, 0.6),
                         (sh_x, sh_y), (hand_x, hand_y), 6)
        # Faust
        pygame.draw.circle(screen, _shade(color, 0.7),
                           (hand_x, hand_y), 7)
        pygame.draw.circle(screen, BLACK, (hand_x, hand_y), 7, 2)
        pygame.draw.circle(screen, (255, 140, 60), (hand_x, hand_y), 3)
    # Kopf (Stein mit Lava-Augen)
    head_y = body_top + 10
    pygame.draw.polygon(screen, _shade(color, 0.7), [
        (sx - 7, head_y - 8), (sx + 7, head_y - 8),
        (sx + 10, head_y + 6), (sx - 10, head_y + 6),
    ])
    pygame.draw.polygon(screen, BLACK, [
        (sx - 7, head_y - 8), (sx + 7, head_y - 8),
        (sx + 10, head_y + 6), (sx - 10, head_y + 6),
    ], 2)
    # Lava-Augen (glühend)
    glow = pygame.Surface((20, 10), pygame.SRCALPHA)
    pygame.draw.circle(glow, (255, 140, 40, 200), (5, 5), 4)
    pygame.draw.circle(glow, (255, 140, 40, 200), (15, 5), 4)
    screen.blit(glow, (sx - 10, head_y - 5))
    pygame.draw.circle(screen, (255, 220, 120), (sx - 3, head_y), 2)
    pygame.draw.circle(screen, (255, 220, 120), (sx + 3, head_y), 2)


def _draw_boss_shadow_lord(screen, e, sx, sy):
    """Schattenfürst: dunkle Gestalt mit pulsierender Aura."""
    import math
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    pulse = abs(math.sin(e.wobble * 2))
    # Schwebende Schatten-Wolke unten
    cloud = pygame.Surface((h * 3, 24), pygame.SRCALPHA)
    for i in range(4):
        pygame.draw.ellipse(cloud, (40, 0, 60, 130 - i * 25),
                            (i * 10, i * 4, h * 3 - i * 20, 22 - i * 4))
    screen.blit(cloud, (sx - int(h * 1.5), sy - 6))
    # Schatten-Aura
    aura = pygame.Surface((h * 4, h * 4), pygame.SRCALPHA)
    for i in range(6, 0, -1):
        pygame.draw.circle(aura, (180, 80, 240, int(40 / i * (0.5 + pulse * 0.5))),
                           (h * 2, h * 2), e.radius + i * 5)
    screen.blit(aura, (sx - h * 2, sy - h * 2))
    # Hohe Robe (schwebt)
    robe_pts = [
        (sx - 16, sy + 4),
        (sx - 10, body_top + 18),
        (sx + 10, body_top + 18),
        (sx + 16, sy + 4),
    ]
    pygame.draw.polygon(screen, color, robe_pts)
    pygame.draw.polygon(screen, e.glow, robe_pts, 2)
    # Runen auf Robe
    for k, (dx, dy) in enumerate([(-6, sy - 14), (6, sy - 4), (-4, sy + 4), (5, sy - 18)]):
        pygame.draw.circle(screen, e.glow, (sx + dx, dy), 2)
        pygame.draw.circle(screen, WHITE, (sx + dx, dy), 1)
    # Hohe Kapuze
    head_y = body_top + 10
    pygame.draw.polygon(screen, _shade(color, 0.5), [
        (sx - 12, head_y + 8), (sx + 12, head_y + 8),
        (sx, head_y - 18),
    ])
    pygame.draw.polygon(screen, e.glow, [
        (sx - 12, head_y + 8), (sx + 12, head_y + 8),
        (sx, head_y - 18),
    ], 2)
    pygame.draw.circle(screen, _shade(color, 0.3), (sx, head_y + 2), 8)
    # Augen: drei statt zwei (unheimlich)
    pygame.draw.circle(screen, e.glow, (sx - 4, head_y), 2)
    pygame.draw.circle(screen, e.glow, (sx + 4, head_y), 2)
    pygame.draw.circle(screen, e.glow, (sx, head_y - 5), 2)
    pygame.draw.circle(screen, WHITE, (sx - 4, head_y), 1)
    pygame.draw.circle(screen, WHITE, (sx + 4, head_y), 1)
    pygame.draw.circle(screen, WHITE, (sx, head_y - 5), 1)
    # Hände schweben links/rechts mit Schattenkugeln
    for side, ofs in ((-1, math.sin(e.wobble) * 2), (1, math.cos(e.wobble) * 2)):
        hx = sx + side * 20
        hy = sy - 8 + int(ofs)
        pygame.draw.circle(screen, _shade(color, 0.4), (hx, hy), 4)
        glow_h = pygame.Surface((16, 16), pygame.SRCALPHA)
        pygame.draw.circle(glow_h, (180, 80, 240, 180), (8, 8), 7)
        screen.blit(glow_h, (hx - 8, hy - 8))


def light_for_player(p):
    """Returnt (radius, color, intensity) für Spieler-Licht."""
    return (260, (255, 230, 190), 0.85)


def light_for_enemy(e):
    """Glühende Gegner (Bosse, Elites) geben Licht ab."""
    if e.is_boss:
        return (180, e.glow, 0.6)
    if e.elite:
        return (60, e.glow, 0.3)
    return None


def light_for_projectile(proj):
    """Glühende Projektile geben Licht."""
    if proj.kind == 'fireball':
        return (80, (255, 140, 60), 0.8)
    if proj.kind in ('firebolt', 'shadowbolt', 'frostbolt'):
        col = {
            'firebolt': (255, 140, 60),
            'shadowbolt': (180, 100, 240),
            'frostbolt': (140, 200, 255),
        }[proj.kind]
        return (50, col, 0.5)
    return None
