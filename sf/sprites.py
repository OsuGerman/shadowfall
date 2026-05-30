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

# Update #171: PROCEDURAL-ONLY-PIVOT.
# User-Entscheidung: alle KI-generierten Sprite-PNGs entfernt; das Spiel
# rendert ausschliesslich procedural. Der Master-Switch bleibt als
# Opt-Out fuer experimentelles Re-Enablement bestehen.
#
# Update #168-Konvention (historisch):
#   Wenn False, returnen ALLE Loader (_load_ai_sprite UND _load_anim_strip)
#   sofort None -> Engine zeichnet komplett procedural.
#
# Default war bis Update #170 True; seit Update #171 ist False der
# kanonische Wert. Wer das wieder anschalten will, muss
# `set_ai_sprites_enabled(True)` aufrufen UND die assets/sprites/-Dateien
# bereitstellen.
_AI_SPRITES_ENABLED = False


def set_ai_sprites_enabled(enabled: bool) -> None:
    """Setzt den globalen AI-Sprite-Master-Switch.
    Bei Wechsel sollte reload_sprite_cache() folgen damit Caches
    in einen konsistenten Zustand kommen."""
    global _AI_SPRITES_ENABLED
    _AI_SPRITES_ENABLED = bool(enabled)


def ai_sprites_enabled() -> bool:
    """Returnt True wenn AI-Sprites geladen werden, False = pure procedural."""
    return _AI_SPRITES_ENABLED


# Audit #179 B.3: Alias-Maps wurden nach sf/sprite_registry.py verschoben.
# Re-Imports fuer Backward-Compat — Code der die Module-Level-Symbole
# direkt referenziert (z.B. tools/) funktioniert weiterhin.
from .sprite_registry import (
    CLASS_SPRITE_ALIAS, MOB_SPRITE_ALIAS, TILE_SPRITE_ALIAS,
    resolve_class as _resolve_class,
    resolve_mob as _resolve_mob,
    resolve_tile as _resolve_tile,
    resolve_portrait as _resolve_portrait,
    resolve_boss as _resolve_boss,
)


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
    sprite_id = _resolve_class(cls)
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
    real_cls = _resolve_class(cls)
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
    real_cls = _resolve_class(cls)
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


_HAS_ANIM_CACHE: dict = {}


def has_anim(cls: str, anim: str) -> bool:
    """True wenn fuer (cls, anim) mind. 1 Direction-Strip existiert.

    Update #191: Result-Caching — vorher 72 File-System-Calls/Frame
    (4 Directions * 2 Player-Draws * ~9 Sprites), jetzt 1 Lookup.
    Cache wird ungueltig wenn der Renderer reload_sprite_cache() ruft.
    """
    key = (cls, anim)
    cached = _HAS_ANIM_CACHE.get(key)
    if cached is not None:
        return cached
    result = False
    for d in WALK_DIRECTIONS:
        if _anim_strip_path(cls, anim, d) is not None:
            result = True
            break
    _HAS_ANIM_CACHE[key] = result
    return result


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
    sprite_id = _resolve_mob(bestiary_key)
    return _load_ai_sprite(sprite_id)


def get_tile_sprite(biome: str | None) -> pygame.Surface | None:
    """Returnt AI-Tile-Surface fuer biome oder None.

    Sucht zuerst die alte Single-Tile-ID (biome.png), fuer Backward-Compat.
    Variants werden via get_tile_variant() abgerufen (siehe unten).
    """
    if not biome:
        return None
    sprite_id = _resolve_tile(biome)
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
    return _load_ai_sprite(_resolve_portrait(npc_key))


def get_boss_plate(encounter_key: str | None) -> pygame.Surface | None:
    """Returnt Boss-Concept-Plate fuer Cinematic-Intro (X-06)."""
    if not encounter_key:
        return None
    return _load_ai_sprite(_resolve_boss(encounter_key))


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

    # Alpha + Tint zusammen anwenden — eine Kopie reicht (Audit #179 A.3).
    needs_copy = alpha < 255 or (tint is not None and tint[3] > 0)
    if needs_copy:
        scaled = scaled.copy()
        if alpha < 255:
            scaled.set_alpha(alpha)
        if tint is not None and tint[3] > 0:
            tint_surf = pygame.Surface(scaled.get_size(), pygame.SRCALPHA)
            tint_surf.fill(tint)
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
    # Update #191: Anim-Existence-Cache muss bei Hot-Reload auch leer.
    _HAS_ANIM_CACHE.clear()


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
    """Elliptischer Schatten direkt am Boden.

    Update #184: Wird nur noch als Fallback fuer Charaktere/Objekte ohne
    eigenes Sprite genutzt. Sprite-basierte Objekte sollen
    `_silhouette_shadow` verwenden (echte Form statt Oval).
    """
    h = max(6, w // 3)
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(s, (0, 0, 0, alpha), (0, 0, w, h))
    screen.blit(s, (sx - w // 2, sy - h // 2))


# Cache fuer Silhouette-Shadows. Key = (id(sprite_surface), squash_y, alpha).
# Sprite-Surfaces sind stabil (kommen aus get_class_anim_frame Cache),
# d.h. id() ist als Key OK; das spart pro Frame den teuren scale-Aufruf.
_SILHOUETTE_CACHE: dict = {}


def _silhouette_shadow(screen, sprite: pygame.Surface, sx: int, sy: int,
                       target_w: int, *, alpha: int = 110,
                       squash_y: float = 0.32) -> None:
    """Schatten der ECHTEN Sprite-Silhouette folgt (statt generisches Oval).

    Args:
        sprite: Quellsprite (SRCALPHA — Alpha-Kanal definiert die Form).
        sx, sy: Foot-Anchor in Screen-Space.
        target_w: Ziel-Breite des Schattens in Pixeln.
        alpha: 0..255 — wie kraeftig.
        squash_y: 0.0..1.0 — vertikale Stauchung (0.3 = flacher Boden-Schatten).

    Update #184: Statt fuer jedes Decor/Char ein Oval, projizieren wir
    das Sprite als gestauchten dunklen Stempel — wirkt wie echte
    Top-Down-Schatten und matched die Silhouette (POE2-Style).
    """
    if sprite is None:
        return
    sw, sh = sprite.get_size()
    if sw <= 0 or sh <= 0:
        return
    # Aspect-Erhalt: target_h aus target_w über Original-Verhaeltnis,
    # dann mit squash_y stauchen.
    target_h = max(4, int(target_w * (sh / max(1, sw)) * squash_y))
    key = (id(sprite), target_w, target_h, alpha)
    cached = _SILHOUETTE_CACHE.get(key)
    if cached is None:
        try:
            scaled = pygame.transform.smoothscale(
                sprite, (target_w, target_h))
        except (pygame.error, ValueError):
            return
        # Alpha-Kanal als Maske; alles non-transparent wird schwarz mit `alpha`.
        shadow = pygame.Surface((target_w, target_h), pygame.SRCALPHA)
        shadow.fill((0, 0, 0, 255))
        # Multiplikativer Alpha-Blit: src-Alpha-Kanal × Shadow's Schwarz
        shadow.blit(scaled, (0, 0),
                     special_flags=pygame.BLEND_RGBA_MULT)
        # Globalen Alpha-Faktor anwenden (alpha 0-255).
        if alpha < 255:
            shadow.set_alpha(alpha)
        cached = shadow
        # Cache-Bound: max 256 Eintraege (Sprite-Cache ist klein, aber
        # bei FX-Animationen koennten viele Frames akkumulieren).
        if len(_SILHOUETTE_CACHE) > 256:
            _SILHOUETTE_CACHE.clear()
        _SILHOUETTE_CACHE[key] = cached
    screen.blit(cached,
                 (sx - target_w // 2, sy - target_h // 2))


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
    # Update #184: Wenn ein Walk-Sheet existiert, projizieren wir das
    # aktuelle Frame als Silhouette-Shadow (folgt der echten Form);
    # sonst Fallback auf Oval.
    foot_sy = sy
    direction_pre = direction_from_facing(getattr(p, 'facing', 0.0))
    walk_frame_for_shadow = None
    if has_anim(cls, 'walk'):
        wp = int(walk_phase % WALK_FRAMES_PER_STRIP) if p.moving else 0
        walk_frame_for_shadow = get_class_anim_frame(
            cls, 'walk', direction_pre, wp)
    if walk_frame_for_shadow is not None:
        # target_w skaliert mit Player-Radius (~6x wie das Body-Sprite)
        try:
            from . import render_spec as _rs
            mult = _rs.get_target_h_mult('class') or 6.0
        except Exception:
            mult = 6.0
        shadow_w = int(p.radius * mult * 0.55)
        _silhouette_shadow(screen, walk_frame_for_shadow,
                            sx, foot_sy + 2, shadow_w,
                            alpha=120, squash_y=0.30)
    else:
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
        # Update #188: Klasse selbst hat Vorrang vor sprite_proxy — Moench
        # bekommt eigenen Renderer statt Warrior-Proxy.
        proxy = CLASSES.get(cls, {}).get('sprite_proxy', cls)
        if cls == 'monk':
            _draw_monk_iso(screen, p, sx, body_sy, walk_phase, base_color)
        elif cls == 'mage':
            _draw_mage_iso_new(screen, p, sx, body_sy, walk_phase, base_color)
        elif cls == 'witch':
            _draw_witch_iso(screen, p, sx, body_sy, walk_phase, base_color)
        elif cls in ('ranger', 'rogue', 'huntress'):
            # Update #196: Eigener Hooded-Ranger-Sprite (alle 3 rogue-proxy
            # Klassen bekommen den gleichen Body, Waffen-Variation kommt
            # in Folge-Update).
            _draw_ranger_iso(screen, p, sx, body_sy, walk_phase, base_color)
        elif cls == 'druid':
            # Update #199: Druid/Wandelnde eigenes Design — Wolfspelz-Hood,
            # Holz-Totem, Tribal-Markierungen. Klar weg vom Warrior-Proxy.
            _draw_druid_iso(screen, p, sx, body_sy, walk_phase, base_color)
        elif proxy == 'warrior':
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


_PROC_SPRITE_CACHE: dict = {}

# Sprite-Canvas-Groesse fuer alle procedural Chars (matched AI-Sprite-Skala
# ~120 px aus render_spec target_h_mult=6.0 * radius=18).
# Update #186: Etwas groesser als #185 fuer bessere Lesbarkeit (+15%).
PROC_SPRITE_W = 84
PROC_SPRITE_H = 124
PROC_SPRITE_FOOT_Y = 120   # Foot-Anchor innerhalb der Surface (px von oben)

# Update #203 (User „Player+Mobs zu gross fuer die Map"): Die Charaktere
# werden bei voller Aufloesung generiert (84x124, scharfe Details) und
# beim Blitten auf PROC_SPRITE_SCALE herunterskaliert. Tile = 80 px →
# vorher ~1.55 Tiles hoch, jetzt ~1.27. Rein visuell — Kollision (radius)
# bleibt unveraendert.
PROC_SPRITE_SCALE = 0.82
PROC_DRAW_FOOT_Y = int(PROC_SPRITE_FOOT_Y * PROC_SPRITE_SCALE)


def _scale_proc(surf):
    """Skaliert ein generiertes Char-Sprite auf die Draw-Groesse herunter."""
    if surf is None or PROC_SPRITE_SCALE == 1.0:
        return surf
    w = max(1, int(surf.get_width() * PROC_SPRITE_SCALE))
    h = max(1, int(surf.get_height() * PROC_SPRITE_SCALE))
    return pygame.transform.smoothscale(surf, (w, h))


def _palette_for_color(base_color):
    """Erzeugt eine 6-Ton-Palette aus base_color fuer Char-Render.

    Lichtquelle = oben links → Highlights links/oben, Shadow rechts/unten.
    """
    return {
        'lightest': _shade(base_color, 1.50),
        'light':    _shade(base_color, 1.22),
        'mid':      base_color,
        'shade':    _shade(base_color, 0.72),
        'dark':     _shade(base_color, 0.42),
        'outline':  BLACK,
    }


# Sekundaer-Farben (gemeinsam fuer alle Klassen)
_SKIN = (220, 178, 138)
_SKIN_SH = (170, 130, 95)
_METAL = (162, 165, 172)
_METAL_LIGHT = (215, 220, 228)
_METAL_DARK = (95, 100, 108)
_LEATHER = (88, 56, 30)
_LEATHER_LIGHT = (140, 95, 55)
_CRIMSON = (160, 30, 35)
_CRIMSON_LIGHT = (210, 60, 60)


def _gen_warrior_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Eisenwaechter (Update #187): kompletter Redesign weg vom
    Roman-Legionaer-Look. Dunkles Iron-Plate, kein Crest, zerschlissenes
    Cape, gedrungener Stand. Palette muted (Iron + Bronze + Rust statt
    knall-rot).

    Layer-Reihenfolge (back→front):
      cape → boots → legs → tassets → torso → belt →
      pauldrons → arms → neck → head/helmet → weapon → shield
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Velgrad-Eisenwaechter-Palette ---
    # Iron: stumpf, dunkel; Bronze: warmes Akzent-Metall; Rust: getragenes Rot
    iron       = (62, 64, 70)       # Haupt-Plate
    iron_lt    = (96, 100, 108)     # Plate-Highlight
    iron_dk    = (32, 34, 40)       # Plate-Shadow / Outline
    bronze     = (122, 88, 52)      # Akzent-Trim
    bronze_lt  = (172, 132, 78)     # Bronze-Highlight
    rust       = (108, 48, 38)      # Cape, Tabard
    rust_dk    = (62, 28, 24)       # Cape-Shadow / Falten
    leather    = (52, 38, 26)       # Stiefel, Gurt
    leather_lt = (82, 60, 38)
    skin       = (158, 122, 92)     # leicht braeunlich, abgehaertet
    skin_sh    = (108, 82, 58)
    bone       = (190, 180, 150)    # Knochen-Sigil / Akzent
    OL = (16, 16, 20)               # Outline (fast schwarz, leicht kalt)

    # Walk-Bob — gedaempfter als vorher (Eisenwaechter, kein flotter Soldat)
    if frame == 1:
        l_dy, r_dy = -2, 1
        arm_swing = -1
    elif frame == 3:
        l_dy, r_dy = 1, -2
        arm_swing = 1
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0

    # ============================================================
    # CAPE / TABARD (zerschlissen, dunkel-rost, kein Knall-Rot)
    # ============================================================
    if direction == 'up':
        cape_pts = [
            (cx - 18, fy - 70),
            (cx + 18, fy - 70),
            (cx + 20, fy - 18),
            (cx + 12, fy - 8),
            (cx + 4, fy - 4),
            (cx - 4, fy - 4),
            (cx - 12, fy - 8),
            (cx - 20, fy - 18),
        ]
        pygame.draw.polygon(surf, rust, cape_pts)
        pygame.draw.polygon(surf, OL, cape_pts, 1)
        # Zerschlissene Saum-Linie
        for fx in range(cx - 18, cx + 19, 4):
            pygame.draw.line(surf, rust_dk,
                              (fx, fy - 14), (fx + 2, fy - 6), 1)
        # Falten
        for fx in (cx - 10, cx, cx + 10):
            pygame.draw.line(surf, rust_dk,
                              (fx, fy - 64), (fx, fy - 18), 1)
    else:
        # Cape ragt nur leicht hinter den Schultern raus
        cape_w = 26 if direction == 'down' else 18
        cape_pts = [
            (cx - cape_w // 2, fy - 68),
            (cx + cape_w // 2, fy - 68),
            (cx + cape_w // 2 + 3, fy - 18),
            (cx + 2, fy - 10),
            (cx - 2, fy - 10),
            (cx - cape_w // 2 - 3, fy - 18),
        ]
        pygame.draw.polygon(surf, rust, cape_pts)
        pygame.draw.polygon(surf, OL, cape_pts, 1)
        # Center-Fold + Saum-Frays
        pygame.draw.line(surf, rust_dk,
                          (cx, fy - 66), (cx, fy - 14), 1)
        for fx in (cx - 8, cx + 8):
            pygame.draw.line(surf, rust_dk,
                              (fx, fy - 18), (fx + 1, fy - 12), 1)

    # ============================================================
    # BOOTS (breit, geerdet)
    # ============================================================
    boot_l = pygame.Rect(cx - 14, fy - 6 + l_dy, 12, 6)
    pygame.draw.rect(surf, leather, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_l.x + 1, boot_l.y + 1),
                      (boot_l.right - 2, boot_l.y + 1), 1)
    boot_r = pygame.Rect(cx + 2, fy - 6 + r_dy, 12, 6)
    pygame.draw.rect(surf, leather, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_r.x + 1, boot_r.y + 1),
                      (boot_r.right - 2, boot_r.y + 1), 1)

    # ============================================================
    # LEGS — Plate-Greaves (eisen, mit Knie-Cop)
    # ============================================================
    leg_l = pygame.Rect(cx - 12, fy - 22 + l_dy, 9, 16)
    pygame.draw.rect(surf, iron, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, iron_lt,
                      (leg_l.x + 1, leg_l.y + 2),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Knie-Cop (Halbkreis vorne)
    pygame.draw.circle(surf, iron, (leg_l.centerx, leg_l.y + 4), 4)
    pygame.draw.circle(surf, OL, (leg_l.centerx, leg_l.y + 4), 4, 1)
    pygame.draw.circle(surf, iron_lt, (leg_l.centerx - 1, leg_l.y + 3), 1)

    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 9, 16)
    pygame.draw.rect(surf, iron, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, iron_lt,
                      (leg_r.x + 1, leg_r.y + 2),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    pygame.draw.circle(surf, iron, (leg_r.centerx, leg_r.y + 4), 4)
    pygame.draw.circle(surf, OL, (leg_r.centerx, leg_r.y + 4), 4, 1)
    pygame.draw.circle(surf, iron_lt, (leg_r.centerx - 1, leg_r.y + 3), 1)

    # ============================================================
    # TASSETS (haengende Plate-Streifen unter dem Guertel)
    # ============================================================
    tas_y0 = fy - 36
    tas_y1 = fy - 22
    # Mittlerer Streifen (vor dem Cape)
    tas_mid = [(cx - 7, tas_y0), (cx + 7, tas_y0),
               (cx + 8, tas_y1), (cx - 8, tas_y1)]
    pygame.draw.polygon(surf, iron_dk, tas_mid)
    pygame.draw.polygon(surf, OL, tas_mid, 1)
    pygame.draw.line(surf, iron, (cx - 6, tas_y0 + 1),
                      (cx - 6, tas_y1 - 1), 1)
    # Aeussere Streifen
    tas_l_pts = [(cx - 16, tas_y0), (cx - 8, tas_y0),
                 (cx - 9, tas_y1), (cx - 17, tas_y1)]
    pygame.draw.polygon(surf, iron_dk, tas_l_pts)
    pygame.draw.polygon(surf, OL, tas_l_pts, 1)
    pygame.draw.line(surf, iron, (cx - 15, tas_y0 + 1),
                      (cx - 16, tas_y1 - 1), 1)
    tas_r_pts = [(cx + 8, tas_y0), (cx + 16, tas_y0),
                 (cx + 17, tas_y1), (cx + 9, tas_y1)]
    pygame.draw.polygon(surf, iron_dk, tas_r_pts)
    pygame.draw.polygon(surf, OL, tas_r_pts, 1)

    # ============================================================
    # TORSO — breite Plate-Cuirass (gedrungen, kein Center-Ridge)
    # ============================================================
    torso_top = fy - 64
    torso_bot = fy - 36
    torso_pts = [(cx - 17, torso_top + 4),
                 (cx - 16, torso_top),
                 (cx + 16, torso_top),
                 (cx + 17, torso_top + 4),
                 (cx + 18, torso_bot),
                 (cx - 18, torso_bot)]
    pygame.draw.polygon(surf, iron, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Light-Fall von oben links (subtle, KEIN Brustplatten-Highlight-Streifen)
    pygame.draw.polygon(surf, iron_lt, [
        (cx - 14, torso_top + 2),
        (cx - 4, torso_top + 2),
        (cx - 8, torso_top + 8),
        (cx - 16, torso_top + 8),
    ])
    # Bronze-Trim-Linie oberer Rand
    pygame.draw.line(surf, bronze,
                      (cx - 15, torso_top + 1),
                      (cx + 15, torso_top + 1), 1)
    pygame.draw.line(surf, bronze_lt,
                      (cx - 13, torso_top + 2),
                      (cx + 13, torso_top + 2), 1)
    # Mahnmal-Sigil (Knochen-Stempel auf Brust) — Velgrad-Lore-Anker
    sig_cy = (torso_top + torso_bot) // 2
    pygame.draw.line(surf, bone, (cx, sig_cy - 3), (cx, sig_cy + 3), 1)
    pygame.draw.line(surf, bone, (cx - 2, sig_cy - 1), (cx + 2, sig_cy - 1), 1)
    pygame.draw.line(surf, bone, (cx - 2, sig_cy + 1), (cx + 2, sig_cy + 1), 1)
    # Diagonale Plate-Kratzer (battle-worn)
    pygame.draw.line(surf, iron_dk, (cx + 6, torso_top + 6),
                      (cx + 12, torso_top + 12), 1)
    pygame.draw.line(surf, iron_dk, (cx - 10, torso_top + 14),
                      (cx - 6, torso_top + 18), 1)

    # ============================================================
    # BELT (schmal, Leder mit Bronze-Buckle)
    # ============================================================
    belt_y = torso_bot - 4
    pygame.draw.rect(surf, leather, (cx - 18, belt_y, 36, 4))
    pygame.draw.rect(surf, OL, (cx - 18, belt_y, 36, 4), 1)
    pygame.draw.line(surf, leather_lt,
                      (cx - 17, belt_y + 1),
                      (cx + 16, belt_y + 1), 1)
    buckle = pygame.Rect(cx - 5, belt_y - 1, 10, 6)
    pygame.draw.rect(surf, bronze, buckle)
    pygame.draw.rect(surf, OL, buckle, 1)
    pygame.draw.line(surf, bronze_lt,
                      (buckle.x + 1, buckle.y + 1),
                      (buckle.right - 2, buckle.y + 1), 1)

    # ============================================================
    # PAULDRONS — eckig & schwer (kein runder Tin-Soldier-Look)
    # ============================================================
    # Linke Pauldron (Lichtseite)
    pl_l = [(cx - 22, torso_top + 4), (cx - 14, torso_top - 2),
            (cx - 8, torso_top + 2), (cx - 12, torso_top + 10),
            (cx - 22, torso_top + 8)]
    pygame.draw.polygon(surf, iron, pl_l)
    pygame.draw.polygon(surf, OL, pl_l, 1)
    pygame.draw.line(surf, iron_lt,
                      (cx - 20, torso_top + 4),
                      (cx - 14, torso_top), 1)
    # Bronze-Trim Pauldron-Rand
    pygame.draw.line(surf, bronze,
                      (cx - 22, torso_top + 7),
                      (cx - 12, torso_top + 10), 1)

    # Rechte Pauldron (Shadow)
    pl_r = [(cx + 22, torso_top + 4), (cx + 14, torso_top - 2),
            (cx + 8, torso_top + 2), (cx + 12, torso_top + 10),
            (cx + 22, torso_top + 8)]
    pygame.draw.polygon(surf, iron_dk, pl_r)
    pygame.draw.polygon(surf, OL, pl_r, 1)
    pygame.draw.line(surf, iron,
                      (cx + 14, torso_top),
                      (cx + 18, torso_top + 4), 1)
    pygame.draw.line(surf, bronze,
                      (cx + 12, torso_top + 10),
                      (cx + 22, torso_top + 7), 1)

    # ============================================================
    # ARMS (kurz, Gauntlets visible)
    # ============================================================
    arm_top = torso_top + 8
    # Linker Arm
    pygame.draw.rect(surf, iron,
                      (cx - 20, arm_top + arm_swing, 6, 14))
    pygame.draw.rect(surf, OL,
                      (cx - 20, arm_top + arm_swing, 6, 14), 1)
    pygame.draw.line(surf, iron_lt,
                      (cx - 19, arm_top + arm_swing + 1),
                      (cx - 19, arm_top + arm_swing + 12), 1)
    # Gauntlet links
    gl = pygame.Rect(cx - 21, arm_top + arm_swing + 12, 8, 5)
    pygame.draw.rect(surf, iron_dk, gl)
    pygame.draw.rect(surf, OL, gl, 1)

    # Rechter Arm
    pygame.draw.rect(surf, iron,
                      (cx + 14, arm_top - arm_swing, 6, 14))
    pygame.draw.rect(surf, OL,
                      (cx + 14, arm_top - arm_swing, 6, 14), 1)
    pygame.draw.line(surf, iron_lt,
                      (cx + 15, arm_top - arm_swing + 1),
                      (cx + 15, arm_top - arm_swing + 12), 1)
    gr = pygame.Rect(cx + 13, arm_top - arm_swing + 12, 8, 5)
    pygame.draw.rect(surf, iron_dk, gr)
    pygame.draw.rect(surf, OL, gr, 1)

    # ============================================================
    # NECK + HEAD/HELM — gedrungener, kein hoher Crest
    # ============================================================
    # Neck-Plate (Gorget)
    pygame.draw.rect(surf, iron_dk, (cx - 5, torso_top - 5, 10, 6))
    pygame.draw.rect(surf, OL, (cx - 5, torso_top - 5, 10, 6), 1)
    pygame.draw.line(surf, iron, (cx - 4, torso_top - 4),
                      (cx + 4, torso_top - 4), 1)

    head_cx = cx
    head_cy = torso_top - 12   # Helmet sitzt direkt auf der Halsplatte
    if direction == 'up':
        # Back-of-helmet — eine glatte Kuppel, kein Crest
        helm_back = [(head_cx - 10, head_cy + 4),
                     (head_cx - 9, head_cy - 7),
                     (head_cx - 4, head_cy - 10),
                     (head_cx + 4, head_cy - 10),
                     (head_cx + 9, head_cy - 7),
                     (head_cx + 10, head_cy + 4)]
        pygame.draw.polygon(surf, iron_dk, helm_back)
        pygame.draw.polygon(surf, OL, helm_back, 2)
        pygame.draw.line(surf, iron, (head_cx - 8, head_cy - 5),
                          (head_cx + 8, head_cy - 5), 1)
        # Bronze-Top-Trim
        pygame.draw.arc(surf, bronze,
                         (head_cx - 8, head_cy - 11, 16, 8),
                         math.pi + 0.2, 2 * math.pi - 0.2, 1)
    elif direction == 'down':
        # Full-face Sallet/Great-Helm — KEIN Plume, KEIN Crest
        # Helm-Silhouette (breit, kantig)
        helm_pts = [(head_cx - 11, head_cy + 6),
                    (head_cx - 11, head_cy - 4),
                    (head_cx - 8, head_cy - 9),
                    (head_cx - 2, head_cy - 11),
                    (head_cx + 2, head_cy - 11),
                    (head_cx + 8, head_cy - 9),
                    (head_cx + 11, head_cy - 4),
                    (head_cx + 11, head_cy + 6)]
        pygame.draw.polygon(surf, iron_dk, helm_pts)
        pygame.draw.polygon(surf, OL, helm_pts, 2)
        # Helm-Top-Highlight (Licht von oben-links)
        pygame.draw.polygon(surf, iron, [
            (head_cx - 9, head_cy - 4),
            (head_cx - 6, head_cy - 8),
            (head_cx - 2, head_cy - 9),
            (head_cx, head_cy - 4),
        ])
        pygame.draw.line(surf, iron_lt,
                          (head_cx - 7, head_cy - 7),
                          (head_cx - 3, head_cy - 9), 1)
        # Bronze-Stirnband
        pygame.draw.line(surf, bronze,
                          (head_cx - 10, head_cy - 4),
                          (head_cx + 10, head_cy - 4), 2)
        pygame.draw.line(surf, bronze_lt,
                          (head_cx - 8, head_cy - 4),
                          (head_cx - 2, head_cy - 4), 1)
        # Visor-Slit (schmal, lang, leicht V-foermig)
        pygame.draw.polygon(surf, (0, 0, 0), [
            (head_cx - 8, head_cy - 1),
            (head_cx + 8, head_cy - 1),
            (head_cx + 8, head_cy + 1),
            (head_cx - 8, head_cy + 1),
        ])
        # Subtle gluehender Punkt im Spalt (Aspekt-Aura, kein knall-Gold)
        pygame.draw.circle(surf, (180, 130, 80),
                            (head_cx - 3, head_cy), 1)
        pygame.draw.circle(surf, (180, 130, 80),
                            (head_cx + 3, head_cy), 1)
        # Atemschlitze unter dem Visor
        for vx in (head_cx - 4, head_cx, head_cx + 4):
            pygame.draw.line(surf, iron_dk,
                              (vx, head_cy + 3), (vx, head_cy + 5), 1)
    else:
        # Profil (right; left wird per flip generiert)
        helm_pts = [(head_cx - 9, head_cy + 6),
                    (head_cx - 10, head_cy - 3),
                    (head_cx - 6, head_cy - 9),
                    (head_cx + 4, head_cy - 11),
                    (head_cx + 9, head_cy - 8),
                    (head_cx + 11, head_cy - 2),
                    (head_cx + 11, head_cy + 6)]
        pygame.draw.polygon(surf, iron_dk, helm_pts)
        pygame.draw.polygon(surf, OL, helm_pts, 2)
        # Highlight
        pygame.draw.polygon(surf, iron, [
            (head_cx - 6, head_cy - 7),
            (head_cx, head_cy - 9),
            (head_cx + 2, head_cy - 4),
            (head_cx - 4, head_cy - 2),
        ])
        # Visor-Slit (vorne, also rechts)
        pygame.draw.rect(surf, (0, 0, 0),
                          (head_cx + 2, head_cy - 1, 8, 2))
        pygame.draw.circle(surf, (180, 130, 80),
                            (head_cx + 6, head_cy), 1)
        # Bronze-Rand am Helm-Eingang
        pygame.draw.line(surf, bronze,
                          (head_cx + 1, head_cy + 1),
                          (head_cx + 10, head_cy + 1), 1)

    # ============================================================
    # WEAPON & SHIELD — kein knall-gold, schweres Schwert + Heater
    # ============================================================
    if direction != 'up':
        # === SCHWERT (rechte Hand, vertikal gehalten) ===
        sw_x = cx + 17
        grip_y = arm_top + 18
        # Grip (Leder)
        pygame.draw.rect(surf, leather, (sw_x - 1, grip_y - 1, 3, 8))
        pygame.draw.line(surf, leather_lt,
                          (sw_x, grip_y), (sw_x, grip_y + 6), 1)
        # Pommel (Bronze, klein)
        pygame.draw.circle(surf, bronze, (sw_x, grip_y + 9), 2)
        pygame.draw.circle(surf, OL, (sw_x, grip_y + 9), 2, 1)
        # Crossguard (eisen, leicht angewinkelt)
        cg = [(sw_x - 5, grip_y - 1), (sw_x + 6, grip_y - 1),
              (sw_x + 5, grip_y - 3), (sw_x - 4, grip_y - 3)]
        pygame.draw.polygon(surf, iron_dk, cg)
        pygame.draw.polygon(surf, OL, cg, 1)
        pygame.draw.line(surf, iron, (sw_x - 4, grip_y - 2),
                          (sw_x + 5, grip_y - 2), 1)
        # Klinge (lang, mit Fuller)
        blade_top = grip_y - 32
        blade = [(sw_x - 2, grip_y - 3),
                 (sw_x + 2, grip_y - 3),
                 (sw_x + 2, blade_top + 4),
                 (sw_x, blade_top),
                 (sw_x - 2, blade_top + 4)]
        pygame.draw.polygon(surf, iron, blade)
        pygame.draw.polygon(surf, OL, blade, 1)
        # Fuller (dunkle Mittellinie)
        pygame.draw.line(surf, iron_dk,
                          (sw_x, grip_y - 3),
                          (sw_x, blade_top + 4), 1)
        # Mini-Glanzpunkt (subtle, kein Bling-Highlight)
        pygame.draw.line(surf, iron_lt,
                          (sw_x - 1, grip_y - 8),
                          (sw_x - 1, grip_y - 14), 1)

        # === SCHILD (linke Hand, Heater-Shape statt Round) ===
        sh_cx = cx - 19
        sh_cy = arm_top + 12
        # Heater-Shield Outline
        heater = [(sh_cx - 6, sh_cy - 8),
                  (sh_cx + 6, sh_cy - 8),
                  (sh_cx + 6, sh_cy - 1),
                  (sh_cx, sh_cy + 8),
                  (sh_cx - 6, sh_cy - 1)]
        pygame.draw.polygon(surf, rust_dk, heater)
        pygame.draw.polygon(surf, OL, heater, 2)
        # Schild-Light-Side
        pygame.draw.polygon(surf, rust, [
            (sh_cx - 5, sh_cy - 7),
            (sh_cx, sh_cy - 7),
            (sh_cx, sh_cy + 6),
            (sh_cx - 5, sh_cy - 1),
        ])
        # Bronze-Boss (zentriert, klein)
        pygame.draw.circle(surf, bronze, (sh_cx, sh_cy - 1), 2)
        pygame.draw.circle(surf, OL, (sh_cx, sh_cy - 1), 2, 1)
        pygame.draw.circle(surf, bronze_lt, (sh_cx - 1, sh_cy - 2), 1)
        # Vertikale Naht
        pygame.draw.line(surf, rust_dk,
                          (sh_cx, sh_cy - 7),
                          (sh_cx, sh_cy + 6), 1)

    return surf


def _get_proc_sprite(class_kind, base_color, direction, frame):
    key = (class_kind, tuple(base_color), direction, frame)
    cached = _PROC_SPRITE_CACHE.get(key)
    if cached is None:
        gen = _SPRITE_GENERATORS.get(class_kind)
        if gen is None:
            return None
        # Update #186: 'left' = horizontaler Flip von 'right' — vorher
        # waren beide identisch und User konnte Richtung nicht erkennen.
        if direction == 'left':
            base = _get_proc_sprite(class_kind, base_color, 'right', frame)
            if base is not None:
                # `base` ist bereits skaliert → nur flippen, nicht doppelt.
                cached = pygame.transform.flip(base, True, False)
            else:
                cached = _scale_proc(gen(base_color, direction, frame))
        else:
            cached = _scale_proc(gen(base_color, direction, frame))
        if len(_PROC_SPRITE_CACHE) > 1024:
            _PROC_SPRITE_CACHE.clear()
        _PROC_SPRITE_CACHE[key] = cached
    return cached


def _draw_warrior_iso(screen, p, sx, sy, walk_phase, color):
    """Update #185: detailliertes 72x104 Sprite aus Cache statt Inline-Polys.

    Vorher ~15 Inline-Polygons bei 36x46 Aufloesung — flach.  Jetzt
    vorgenerierte Sprites (50+ Render-Ops in einer Cache-Surface), 4
    Directions x 4 Walk-Frames = 16 Cache-Eintraege pro Klasse.
    """
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('warrior', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


def _gen_monk_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Moench (Update #188): „Stille Schritte"-Kampfmoench mit
    Quarterstaff. KEIN Plate-Armor — Stoff-Robe, sichtbare Haut, Fuss-
    Wraps. Visuell deutlich anders als der Eisenwaechter.

    Lore-Anker: Lore-Bibel Teil 7. Mahnmal-orientiert; Asketen-Optik mit
    Sigil-Tatauierung am Kopf.

    Layer (back→front):
      staff-back-half → wraps/feet → legs → robe-skirt → sash →
      torso → arms (bare) → prayer-beads → head (shaven) → sigil →
      staff-front-half
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Moench-Palette: warm, gedaempft, eindeutig kein Iron ---
    robe_lt    = (218, 188, 142)   # Hauptrobe (Sandstein / verwaschen)
    robe       = (178, 142, 96)
    robe_dk    = (122, 92, 58)
    sash       = (78, 36, 36)      # Schaerpe (dunkelrot/Wein)
    sash_lt    = (132, 60, 56)
    skin       = (210, 168, 124)   # Haende, Unterarme, Glatze
    skin_sh    = (158, 118, 82)
    skin_hl    = (235, 198, 152)
    bead       = (52, 32, 24)      # Holz-Gebetsperlen
    bead_hl    = (138, 92, 52)
    wood       = (108, 76, 44)     # Quarterstaff (dunkles Holz)
    wood_lt    = (158, 116, 74)
    wood_dk    = (62, 40, 22)
    bronze     = (122, 88, 52)     # Staff-Bands
    bronze_lt  = (172, 132, 78)
    sigil      = (90, 28, 36)      # Stirn-Sigil (rote Tinte)
    OL         = (16, 14, 12)

    # Walk-Bob — moench bewegt sich leichter, mehr Bounce
    if frame == 1:
        l_dy, r_dy = -3, 1
        staff_tilt = -2
        arm_swing = -1
    elif frame == 3:
        l_dy, r_dy = 1, -3
        staff_tilt = 2
        arm_swing = 1
    else:
        l_dy, r_dy = 0, 0
        staff_tilt = 0
        arm_swing = 0

    # ============================================================
    # QUARTERSTAFF — Update #189c: fast vertikal, an der rechten Seite
    # des Bodys gefuehrt (kreuzt nicht mehr Gesicht/Brust).
    # ============================================================
    if direction != 'up':
        # Staff steht aufrecht rechts neben dem Body, minimal nach vorn
        # gekippt durch staff_tilt (Walk-Sway).
        staff_x_top = cx + 19 + staff_tilt
        staff_x_bot = cx + 17 - staff_tilt
        staff_top_y = fy - 96
        staff_bot_y = fy - 2
        # Back-Half: nur das obere Stueck (oberhalb der Hand)
        grip_y = fy - 50  # Hand-Grip auf Brusthoehe
        pygame.draw.line(surf, wood,
                          (staff_x_top, staff_top_y),
                          (staff_x_top, grip_y), 3)
        pygame.draw.line(surf, OL,
                          (staff_x_top, staff_top_y),
                          (staff_x_top, grip_y), 1)
        pygame.draw.line(surf, wood_lt,
                          (staff_x_top - 1, staff_top_y + 2),
                          (staff_x_top - 1, grip_y), 1)
        # Bronze-Cap am oberen Ende (eisernes Knaufstueck)
        pygame.draw.circle(surf, bronze, (staff_x_top, staff_top_y), 3)
        pygame.draw.circle(surf, OL, (staff_x_top, staff_top_y), 3, 1)
        pygame.draw.circle(surf, bronze_lt,
                            (staff_x_top - 1, staff_top_y - 1), 1)
        # Drei Holz-Maserungs-Linien (back-half)
        for ry in (staff_top_y + 12, staff_top_y + 24, staff_top_y + 36):
            pygame.draw.line(surf, wood_dk,
                              (staff_x_top - 1, ry),
                              (staff_x_top + 1, ry + 2), 1)

    # ============================================================
    # FEET — bare mit Stoff-Wraps (kein Stiefel)
    # ============================================================
    # Linker Fuss
    foot_l = pygame.Rect(cx - 11, fy - 5 + l_dy, 9, 5)
    pygame.draw.ellipse(surf, skin, foot_l)
    pygame.draw.ellipse(surf, OL, foot_l, 1)
    # Wickel-Linien
    pygame.draw.line(surf, robe_dk,
                      (foot_l.x + 1, foot_l.y + 2),
                      (foot_l.right - 2, foot_l.y + 2), 1)
    # Rechter Fuss
    foot_r = pygame.Rect(cx + 2, fy - 5 + r_dy, 9, 5)
    pygame.draw.ellipse(surf, skin, foot_r)
    pygame.draw.ellipse(surf, OL, foot_r, 1)
    pygame.draw.line(surf, robe_dk,
                      (foot_r.x + 1, foot_r.y + 2),
                      (foot_r.right - 2, foot_r.y + 2), 1)

    # ============================================================
    # LEGS — sichtbare Wickel-Hose (Stoff, kein Metall)
    # ============================================================
    # Unterer Wickel
    leg_l = pygame.Rect(cx - 10, fy - 16 + l_dy, 7, 11)
    pygame.draw.rect(surf, robe, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, robe_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Wrap-Bandagen (drei diagonale Linien)
    for ly in (leg_l.y + 2, leg_l.y + 5, leg_l.y + 8):
        pygame.draw.line(surf, robe_dk,
                          (leg_l.x, ly), (leg_l.right, ly + 1), 1)

    leg_r = pygame.Rect(cx + 3, fy - 16 + r_dy, 7, 11)
    pygame.draw.rect(surf, robe, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, robe_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    for ly in (leg_r.y + 2, leg_r.y + 5, leg_r.y + 8):
        pygame.draw.line(surf, robe_dk,
                          (leg_r.x, ly), (leg_r.right, ly + 1), 1)

    # ============================================================
    # ROBE-SKIRT — Update #189c: weicher Saum (sanfter Bogen statt
    # Zickzack), Falten als subtiles Schattengradient.
    # ============================================================
    skirt_top = fy - 36
    skirt_bot = fy - 14
    skirt_pts = [
        (cx - 17, skirt_top),
        (cx + 17, skirt_top),
        (cx + 17, skirt_bot - 4),
        (cx + 14, skirt_bot - 1),
        (cx + 9, skirt_bot),
        (cx + 4, skirt_bot - 2),
        (cx, skirt_bot - 3),
        (cx - 4, skirt_bot - 2),
        (cx - 9, skirt_bot),
        (cx - 14, skirt_bot - 1),
        (cx - 17, skirt_bot - 4),
    ]
    pygame.draw.polygon(surf, robe_lt, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 2)
    # Falten — subtile vertikale Schattenlinien
    for fx_, alpha_shade in (
        (cx - 12, robe), (cx - 6, robe_dk),
        (cx, robe_dk), (cx + 6, robe_dk), (cx + 12, robe),
    ):
        pygame.draw.line(surf, alpha_shade,
                          (fx_, skirt_top + 2),
                          (fx_, skirt_bot - 5), 1)
    # Mahnmal-Saum-Trim (Bronze-Band oben)
    pygame.draw.line(surf, bronze,
                      (cx - 16, skirt_top + 1),
                      (cx + 16, skirt_top + 1), 1)
    pygame.draw.line(surf, bronze_lt,
                      (cx - 14, skirt_top + 2),
                      (cx + 14, skirt_top + 2), 1)
    # Saum-Highlight (untere Kante leicht heller)
    pygame.draw.line(surf, robe,
                      (cx - 14, skirt_bot - 5),
                      (cx + 14, skirt_bot - 5), 1)

    # ============================================================
    # TORSO — Wickelrobe (verkreuzt, kein Plate)
    # Update #189b: Schultern direkt ins Torso-Polygon eingebunden
    # (keine freistehenden Kreis-Baelle mehr).  Sanfte Tropfen-
    # Silhouette: schmale Schultern oben, leicht ausgestellt zur Huefte.
    # ============================================================
    torso_top = fy - 64
    torso_bot = fy - 36
    # 14-Punkt-Polygon fuer organische Silhouette (kein hartes Trapez)
    torso_pts = [
        (cx - 10, torso_top),         # Schulter-Top links
        (cx + 10, torso_top),         # Schulter-Top rechts
        (cx + 13, torso_top + 3),     # Schulter-Aussenkante
        (cx + 14, torso_top + 8),
        (cx + 15, torso_top + 14),    # Taille
        (cx + 16, torso_top + 20),
        (cx + 17, torso_bot - 2),     # Huefte-Aussen
        (cx + 15, torso_bot),
        (cx - 15, torso_bot),
        (cx - 17, torso_bot - 2),
        (cx - 16, torso_top + 20),
        (cx - 15, torso_top + 14),
        (cx - 14, torso_top + 8),
        (cx - 13, torso_top + 3),
    ]
    pygame.draw.polygon(surf, robe_lt, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Wickel-Overlap (diagonale Stoff-Bahn ueber die Brust)
    overlap_pts = [(cx - 9, torso_top + 3),
                   (cx + 10, torso_top + 8),
                   (cx + 14, torso_bot - 4),
                   (cx - 15, torso_bot - 4)]
    pygame.draw.polygon(surf, robe, overlap_pts)
    pygame.draw.polygon(surf, robe_dk, overlap_pts, 1)
    # Wickel-Naht (schraege Linie)
    pygame.draw.line(surf, robe_dk,
                      (cx - 14, torso_top + 6),
                      (cx + 12, torso_top + 10), 1)

    # ============================================================
    # SASH — rote Schaerpe am Bauch (Mahnmal-Treuegelubde)
    # ============================================================
    sash_y = torso_bot - 6
    pygame.draw.rect(surf, sash, (cx - 17, sash_y, 34, 6))
    pygame.draw.rect(surf, OL, (cx - 17, sash_y, 34, 6), 1)
    pygame.draw.line(surf, sash_lt,
                      (cx - 16, sash_y + 1),
                      (cx + 15, sash_y + 1), 1)
    # Sash-Knoten (rechts) — haengt herab
    knot_pts = [(cx + 12, sash_y), (cx + 16, sash_y),
                (cx + 18, sash_y + 9), (cx + 14, sash_y + 11),
                (cx + 10, sash_y + 6)]
    pygame.draw.polygon(surf, sash, knot_pts)
    pygame.draw.polygon(surf, OL, knot_pts, 1)
    # Hanging tail
    pygame.draw.line(surf, sash,
                      (cx + 14, sash_y + 11),
                      (cx + 13, sash_y + 14), 2)
    pygame.draw.line(surf, OL,
                      (cx + 14, sash_y + 11),
                      (cx + 13, sash_y + 14), 1)

    # ============================================================
    # ARMS — Update #189b: enger an den Torso angedockt, mit kleinem
    # Schulter-Cap der sanft in den Arm uebergeht (kein Ball-Look).
    # ============================================================
    arm_top = torso_top + 6
    # Schulter-Cap links (kleine Rundung am Uebergang)
    pygame.draw.circle(surf, robe, (cx - 14, torso_top + 4), 4)
    pygame.draw.circle(surf, OL, (cx - 14, torso_top + 4), 4, 1)
    # Arm links (Haut)
    arm_l = pygame.Rect(cx - 17, arm_top + arm_swing, 5, 11)
    pygame.draw.rect(surf, skin, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, skin_hl,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Mahnmal-Tattoo (3 horizontale Striche, sigil-Farbe)
    for tat_y in (arm_l.y + 3, arm_l.y + 5, arm_l.y + 7):
        pygame.draw.line(surf, sigil,
                          (arm_l.x + 1, tat_y),
                          (arm_l.right - 1, tat_y), 1)
    # Handgelenk-Wrap
    pygame.draw.rect(surf, robe_dk,
                      (arm_l.x - 1, arm_l.bottom - 3, 7, 3))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 3, 7, 3), 1)
    # Faust
    fist_l = pygame.Rect(arm_l.x, arm_l.bottom, 5, 4)
    pygame.draw.rect(surf, skin, fist_l)
    pygame.draw.rect(surf, OL, fist_l, 1)

    # Schulter-Cap rechts (Shadow-Seite, leicht dunkler)
    pygame.draw.circle(surf, robe_dk, (cx + 14, torso_top + 4), 4)
    pygame.draw.circle(surf, OL, (cx + 14, torso_top + 4), 4, 1)
    # Arm rechts
    arm_r = pygame.Rect(cx + 12, arm_top - arm_swing, 5, 11)
    pygame.draw.rect(surf, skin, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, skin_hl,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, robe_dk,
                      (arm_r.x, arm_r.bottom - 3, 7, 3))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 3, 7, 3), 1)
    fist_r = pygame.Rect(arm_r.x + 1, arm_r.bottom, 5, 4)
    pygame.draw.rect(surf, skin, fist_r)
    pygame.draw.rect(surf, OL, fist_r, 1)

    # ============================================================
    # PRAYER BEADS — um den Hals, Mahnmal-Aspekt-Anker
    # ============================================================
    beads_y = torso_top + 2
    for bx in range(cx - 8, cx + 9, 3):
        pygame.draw.circle(surf, bead, (bx, beads_y), 1)
        pygame.draw.circle(surf, bead_hl, (bx - 1, beads_y - 1), 1)
    # Zentral-Anhaenger (Bronze-Token mit Sigil)
    pygame.draw.circle(surf, bronze, (cx, beads_y + 3), 3)
    pygame.draw.circle(surf, OL, (cx, beads_y + 3), 3, 1)
    pygame.draw.line(surf, bone if False else sigil,
                      (cx - 1, beads_y + 3),
                      (cx + 1, beads_y + 3), 1)
    pygame.draw.line(surf, sigil,
                      (cx, beads_y + 2),
                      (cx, beads_y + 4), 1)

    # ============================================================
    # NECK — Update #189: Skin-Strip damit Kopf nicht mehr schwebt.
    # Schmaler als Krieger-Gorget (kein Plate), dafuer mit Haut-Tone.
    # ============================================================
    neck_y = torso_top - 6
    neck_pts = [(cx - 4, neck_y), (cx + 4, neck_y),
                (cx + 5, torso_top + 2), (cx - 5, torso_top + 2)]
    pygame.draw.polygon(surf, skin, neck_pts)
    pygame.draw.polygon(surf, OL, neck_pts, 1)
    # Hals-Schatten unter dem Kinn
    pygame.draw.line(surf, skin_sh, (cx - 3, neck_y + 1),
                      (cx + 3, neck_y + 1), 1)

    # ============================================================
    # HEAD — Glatze (rasiert), Stirn-Sigil
    # Update #189: Kopf groesser (radius 10 statt 9), tiefer positioniert
    # damit Kopf-Bottom mit Hals-Top ueberlappt → kein Floating.
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 14   # Bottom des Kopfes (cy+10) sitzt bei neck_y
    if direction == 'up':
        # Rueckansicht: Glatze
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 10)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 9)
        pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 8)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 10, 1)
        # Light-Highlight oben links
        pygame.draw.circle(surf, skin_hl, (head_cx - 3, head_cy - 4), 2)
        # Hinterkopf-Schatten der Schaedelform
        pygame.draw.arc(surf, skin_sh,
                         (head_cx - 8, head_cy - 4, 16, 14),
                         math.pi + 0.2, 2 * math.pi - 0.2, 1)
    elif direction == 'down':
        # Frontansicht — Update #189c: lesbarere Gesichtszuege
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 10)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 9)
        pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 8)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 10, 1)
        # Light-Highlight oben links (Glatze-Glanz)
        pygame.draw.circle(surf, skin_hl, (head_cx - 4, head_cy - 5), 2)
        pygame.draw.circle(surf, skin_hl, (head_cx - 2, head_cy - 6), 1)
        # Wangenknochen-Schatten (definiert das Gesicht)
        pygame.draw.line(surf, skin_sh,
                          (head_cx - 7, head_cy + 2),
                          (head_cx - 5, head_cy + 4), 1)
        pygame.draw.line(surf, skin_sh,
                          (head_cx + 7, head_cy + 2),
                          (head_cx + 5, head_cy + 4), 1)
        # Augenbrauen (dunkle, klare Striche)
        pygame.draw.line(surf, OL,
                          (head_cx - 5, head_cy - 3),
                          (head_cx - 2, head_cy - 2), 1)
        pygame.draw.line(surf, OL,
                          (head_cx + 2, head_cy - 2),
                          (head_cx + 5, head_cy - 3), 1)
        # Geschlossene Augen (Meditation) — solid statt nur Linie
        pygame.draw.line(surf, OL,
                          (head_cx - 5, head_cy),
                          (head_cx - 2, head_cy), 2)
        pygame.draw.line(surf, OL,
                          (head_cx + 2, head_cy),
                          (head_cx + 5, head_cy), 2)
        # Nase — kurzer dunkler Strich mit Schatten
        pygame.draw.line(surf, skin_sh,
                          (head_cx - 1, head_cy + 1),
                          (head_cx - 1, head_cy + 4), 1)
        pygame.draw.line(surf, OL,
                          (head_cx, head_cy + 4),
                          (head_cx + 1, head_cy + 4), 1)
        # Mund — minimal nach oben gezogen (ruhige Konzentration)
        pygame.draw.line(surf, OL,
                          (head_cx - 2, head_cy + 6),
                          (head_cx + 2, head_cy + 6), 1)
        pygame.draw.circle(surf, skin_sh, (head_cx - 3, head_cy + 7), 1)
        pygame.draw.circle(surf, skin_sh, (head_cx + 3, head_cy + 7), 1)
        # Stirn-Sigil (rotes Mahnmal-Symbol) — etwas groesser & klarer
        pygame.draw.line(surf, sigil,
                          (head_cx, head_cy - 8),
                          (head_cx, head_cy - 4), 2)
        pygame.draw.circle(surf, sigil, (head_cx, head_cy - 9), 1)
        pygame.draw.line(surf, sigil,
                          (head_cx - 2, head_cy - 6),
                          (head_cx + 2, head_cy - 6), 1)
        # Ohren
        pygame.draw.circle(surf, skin_sh, (head_cx - 9, head_cy + 1), 2)
        pygame.draw.circle(surf, OL, (head_cx - 9, head_cy + 1), 2, 1)
        pygame.draw.circle(surf, skin_sh, (head_cx + 9, head_cy + 1), 2)
        pygame.draw.circle(surf, OL, (head_cx + 9, head_cy + 1), 2, 1)
    else:
        # Profil (right; left via flip)
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 10)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 9)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 10, 1)
        # Nase (Seitlich-Profil — kleiner Vorsprung)
        pygame.draw.polygon(surf, skin, [
            (head_cx + 7, head_cy),
            (head_cx + 9, head_cy + 1),
            (head_cx + 8, head_cy + 3),
            (head_cx + 6, head_cy + 2),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 7, head_cy),
            (head_cx + 9, head_cy + 1),
            (head_cx + 8, head_cy + 3),
            (head_cx + 6, head_cy + 2),
        ], 1)
        # Auge (geschlossen)
        pygame.draw.line(surf, OL,
                          (head_cx + 2, head_cy),
                          (head_cx + 5, head_cy), 1)
        # Augenbraue
        pygame.draw.line(surf, OL,
                          (head_cx + 2, head_cy - 2),
                          (head_cx + 5, head_cy - 2), 1)
        # Ohr
        pygame.draw.circle(surf, skin_sh, (head_cx - 5, head_cy + 1), 2)
        pygame.draw.circle(surf, OL, (head_cx - 5, head_cy + 1), 2, 1)
        # Stirn-Sigil
        pygame.draw.line(surf, sigil,
                          (head_cx + 1, head_cy - 6),
                          (head_cx + 1, head_cy - 4), 1)

    # ============================================================
    # QUARTERSTAFF — Front-Half (Update #189c: vertikal, vor Arm/Bein)
    # ============================================================
    if direction != 'up':
        staff_x_top = cx + 19 + staff_tilt
        staff_x_bot = cx + 17 - staff_tilt
        grip_y = fy - 50
        staff_bot_y = fy - 2
        # Lederwickel-Grip an der Hand-Position (zentral)
        pygame.draw.rect(surf, wood_dk,
                          (staff_x_top - 2, grip_y - 4, 5, 10))
        pygame.draw.rect(surf, OL,
                          (staff_x_top - 2, grip_y - 4, 5, 10), 1)
        for gy in (grip_y - 2, grip_y + 1, grip_y + 4):
            pygame.draw.line(surf, OL,
                              (staff_x_top - 2, gy),
                              (staff_x_top + 2, gy), 1)
        # Unterer Schaft
        pygame.draw.line(surf, wood,
                          (staff_x_top, grip_y + 6),
                          (staff_x_bot, staff_bot_y), 3)
        pygame.draw.line(surf, OL,
                          (staff_x_top, grip_y + 6),
                          (staff_x_bot, staff_bot_y), 1)
        pygame.draw.line(surf, wood_lt,
                          (staff_x_top - 1, grip_y + 7),
                          (staff_x_bot - 1, staff_bot_y - 1), 1)
        # Bronze-Cap unten (eisernes Bodenende)
        pygame.draw.circle(surf, bronze,
                            (staff_x_bot, staff_bot_y), 3)
        pygame.draw.circle(surf, OL,
                            (staff_x_bot, staff_bot_y), 3, 1)
        pygame.draw.circle(surf, bronze_lt,
                            (staff_x_bot - 1, staff_bot_y - 1), 1)

    return surf


def _draw_monk_iso(screen, p, sx, sy, walk_phase, color):
    """Moench-Renderer (Update #188) — eigenes Sprite-Set, klar
    unterscheidbar vom Eisenwaechter (Robe + Quarterstaff statt Plate).
    """
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('monk', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


def _gen_mage_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Funkengeborener Magier (Update #195).

    Lore: Aspekt Nheyras (Zeit-Glas-Blau). Hoher Zauberschaden, zerbrechlich.
    Visual: Lange dunkle Robe mit pulsierenden Runen, breitkrempiger
    Hut (KEIN Disney-Wizard-Spitzhut), grauer Bart, Stab mit Kristall.
    Klar unterschiedlich von Krieger (Plate) und Moench (Wickel-Robe).

    Layer (back→front):
      cape-half (back) → robe-skirt → torso → sash → arms (long sleeves)
      → prayer pouch → head → hat → staff (in front-arm)
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Mage-Palette (kuehl, blau-violett, mystisch) ---
    robe       = (52, 60, 110)     # tiefes Indigo
    robe_lt    = (88, 100, 158)    # blue highlight
    robe_dk    = (28, 32, 64)      # dark shadow
    robe_trim  = (180, 145, 60)    # warmer Bronze-Trim als Kontrast
    robe_trim_lt = (235, 200, 110)
    rune       = base_color        # Klassen-Farbe = Rune-Glow
    rune_glow  = _shade(base_color, 1.6)
    skin       = (218, 188, 158)   # blasser als Krieger/Moench (Studierter)
    skin_sh    = (172, 138, 108)
    skin_hl    = (240, 215, 188)
    beard      = (210, 215, 220)   # eis-grau, alt
    beard_dk   = (160, 165, 175)
    hat        = (40, 38, 58)
    hat_lt     = (78, 76, 102)
    hat_dk     = (20, 18, 30)
    wood       = (78, 52, 32)      # Staff (dunkles Walnussholz)
    wood_lt    = (122, 88, 58)
    wood_dk    = (42, 28, 18)
    crystal    = _shade(base_color, 1.45)   # gluehender Kristall
    crystal_core = _shade(base_color, 1.85)
    OL         = (10, 8, 14)

    # Walk-Bob: Robe schwingt, Beine nicht sichtbar
    if frame == 1:
        robe_dy = -1
        arm_swing = -2
        staff_tilt = -1
    elif frame == 3:
        robe_dy = 1
        arm_swing = 2
        staff_tilt = 1
    else:
        robe_dy = 0
        arm_swing = 0
        staff_tilt = 0

    # ============================================================
    # STAFF — Back-Half (haelt hinter dem Body)
    # ============================================================
    if direction != 'up':
        # Staff aufrecht an linker Seite (Mage haelt linke Hand am Stab)
        staff_x = cx - 19 + staff_tilt
        staff_top_y = fy - 100
        staff_bot_y = fy - 4
        grip_y = fy - 52   # Hand-Grip
        # Back-Schaft (oben)
        pygame.draw.line(surf, wood, (staff_x, staff_top_y),
                          (staff_x, grip_y), 3)
        pygame.draw.line(surf, OL, (staff_x, staff_top_y),
                          (staff_x, grip_y), 1)
        pygame.draw.line(surf, wood_lt, (staff_x - 1, staff_top_y + 2),
                          (staff_x - 1, grip_y), 1)

    # ============================================================
    # ROBE-SKIRT — sehr lang, fast bis zum Boden, fliesst
    # ============================================================
    skirt_top = fy - 42
    skirt_bot = fy - 2
    skirt_pts = [
        (cx - 18, skirt_top),
        (cx + 18, skirt_top),
        (cx + 22, skirt_bot - 6),
        (cx + 18, skirt_bot - 2 + robe_dy),
        (cx + 10, skirt_bot + robe_dy),
        (cx + 3, skirt_bot - 1),
        (cx - 3, skirt_bot - 1),
        (cx - 10, skirt_bot - robe_dy),
        (cx - 18, skirt_bot - 2 - robe_dy),
        (cx - 22, skirt_bot - 6),
    ]
    pygame.draw.polygon(surf, robe, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 2)
    # Falten — vertikale Schattenstreifen
    for fx_ in (cx - 13, cx - 6, cx, cx + 6, cx + 13):
        pygame.draw.line(surf, robe_dk,
                          (fx_, skirt_top + 2),
                          (fx_ + (1 if fx_ > cx else -1),
                           skirt_bot - 4), 1)
    # Subtiler Highlight links (light-source upper-left)
    pygame.draw.line(surf, robe_lt,
                      (cx - 17, skirt_top + 3),
                      (cx - 20, skirt_bot - 8), 1)
    # Bronze-Trim am Saum (gold-pattern)
    for tx in range(cx - 16, cx + 17, 4):
        pygame.draw.line(surf, robe_trim,
                          (tx, skirt_bot - 3),
                          (tx + 2, skirt_bot - 3), 1)
    # Runen-Glyphen am Robe-Saum (3 magische Symbole)
    for rx, ry in ((cx - 12, skirt_bot - 10),
                    (cx, skirt_bot - 12),
                    (cx + 12, skirt_bot - 10)):
        pygame.draw.circle(surf, rune_glow, (rx, ry), 2)
        pygame.draw.circle(surf, rune, (rx, ry), 1)

    # ============================================================
    # TORSO — schmaler als Krieger, Robe-Oberteil mit Vertikal-Falten
    # ============================================================
    torso_top = fy - 66
    torso_bot = fy - 42
    torso_pts = [
        (cx - 11, torso_top),
        (cx + 11, torso_top),
        (cx + 14, torso_top + 4),
        (cx + 17, torso_top + 12),
        (cx + 18, torso_bot),
        (cx - 18, torso_bot),
        (cx - 17, torso_top + 12),
        (cx - 14, torso_top + 4),
    ]
    pygame.draw.polygon(surf, robe, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Vertikal-Naht (Mantel-Mitte)
    pygame.draw.line(surf, robe_dk, (cx, torso_top), (cx, torso_bot), 1)
    # Bronze-V-Kragen
    collar_pts = [(cx - 8, torso_top + 1), (cx + 8, torso_top + 1),
                  (cx, torso_top + 8)]
    pygame.draw.polygon(surf, robe_trim, collar_pts)
    pygame.draw.polygon(surf, OL, collar_pts, 1)
    pygame.draw.line(surf, robe_trim_lt,
                      (cx - 6, torso_top + 2),
                      (cx, torso_top + 6), 1)
    # Light-Highlight (oben links)
    pygame.draw.line(surf, robe_lt,
                      (cx - 12, torso_top + 4),
                      (cx - 16, torso_top + 16), 1)

    # ============================================================
    # SASH / GIRDLE — schmaler Stoff-Guertel, kein Plate
    # ============================================================
    sash_y = torso_bot - 3
    pygame.draw.rect(surf, robe_dk, (cx - 18, sash_y, 36, 4))
    pygame.draw.rect(surf, OL, (cx - 18, sash_y, 36, 4), 1)
    pygame.draw.line(surf, robe_trim,
                      (cx - 17, sash_y + 1),
                      (cx + 16, sash_y + 1), 1)
    # Buckle (kleiner Bronze-Ring)
    pygame.draw.circle(surf, robe_trim_lt, (cx, sash_y + 2), 3)
    pygame.draw.circle(surf, OL, (cx, sash_y + 2), 3, 1)
    pygame.draw.circle(surf, robe, (cx, sash_y + 2), 1)

    # ============================================================
    # SLEEVES / ARMS — lange Robe-Aermel mit Bronze-Cuff
    # ============================================================
    arm_top = torso_top + 8
    # Linker Aermel (haelt Staff)
    sleeve_l_pts = [
        (cx - 19, arm_top - 1 + arm_swing),
        (cx - 14, arm_top + 1 + arm_swing),
        (cx - 16, arm_top + 16 + arm_swing),
        (cx - 22, arm_top + 14 + arm_swing),
    ]
    pygame.draw.polygon(surf, robe, sleeve_l_pts)
    pygame.draw.polygon(surf, OL, sleeve_l_pts, 1)
    pygame.draw.line(surf, robe_lt,
                      (cx - 21, arm_top + arm_swing),
                      (cx - 21, arm_top + 13 + arm_swing), 1)
    # Bronze-Cuff
    pygame.draw.line(surf, robe_trim,
                      (cx - 22, arm_top + 13 + arm_swing),
                      (cx - 16, arm_top + 16 + arm_swing), 2)
    # Hand (haelt Staff)
    pygame.draw.circle(surf, skin, (cx - 19, arm_top + 16 + arm_swing), 3)
    pygame.draw.circle(surf, OL, (cx - 19, arm_top + 16 + arm_swing), 3, 1)

    # Rechter Aermel (frei, vor der Brust)
    sleeve_r_pts = [
        (cx + 14, arm_top - 1 - arm_swing),
        (cx + 19, arm_top + 1 - arm_swing),
        (cx + 22, arm_top + 14 - arm_swing),
        (cx + 16, arm_top + 16 - arm_swing),
    ]
    pygame.draw.polygon(surf, robe, sleeve_r_pts)
    pygame.draw.polygon(surf, OL, sleeve_r_pts, 1)
    pygame.draw.line(surf, robe_dk,
                      (cx + 17, arm_top - arm_swing),
                      (cx + 19, arm_top + 13 - arm_swing), 1)
    pygame.draw.line(surf, robe_trim,
                      (cx + 16, arm_top + 16 - arm_swing),
                      (cx + 22, arm_top + 13 - arm_swing), 2)
    # Hand (Geste)
    pygame.draw.circle(surf, skin, (cx + 19, arm_top + 16 - arm_swing), 3)
    pygame.draw.circle(surf, OL, (cx + 19, arm_top + 16 - arm_swing), 3, 1)
    # Funke ueber der Geste-Hand (mage-typisch)
    if direction != 'up':
        spark_x = cx + 19
        spark_y = arm_top + 11 - arm_swing
        pygame.draw.circle(surf, rune_glow, (spark_x, spark_y), 2)
        pygame.draw.circle(surf, rune, (spark_x, spark_y), 1)
        # Tiny rays
        pygame.draw.line(surf, rune_glow,
                          (spark_x - 3, spark_y),
                          (spark_x - 5, spark_y - 1), 1)
        pygame.draw.line(surf, rune_glow,
                          (spark_x + 3, spark_y),
                          (spark_x + 5, spark_y + 1), 1)
        pygame.draw.line(surf, rune_glow,
                          (spark_x, spark_y - 3),
                          (spark_x, spark_y - 5), 1)

    # ============================================================
    # PRAYER POUCH / SCROLL-CASE — am Sash haengend
    # ============================================================
    pouch_x = cx - 8
    pouch_y = sash_y + 5
    pygame.draw.rect(surf, wood, (pouch_x, pouch_y, 5, 8))
    pygame.draw.rect(surf, OL, (pouch_x, pouch_y, 5, 8), 1)
    pygame.draw.line(surf, wood_lt,
                      (pouch_x + 1, pouch_y + 1),
                      (pouch_x + 1, pouch_y + 6), 1)
    # Tiny Schloss
    pygame.draw.line(surf, robe_trim,
                      (pouch_x + 1, pouch_y + 3),
                      (pouch_x + 4, pouch_y + 3), 1)

    # ============================================================
    # NECK — Update #197: kuerzer (3 statt 8px), Kopf 4px tiefer.
    # User-Report: alter Hals war 5px sichtbar = Giraffe-Optik.
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 3, 2, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    # ============================================================
    # HEAD — Update #197: 4px naeher am Torso
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    if direction == 'up':
        # Hinterkopf mit Hut
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
        # Bart-Andeutung hinten? Eher nein, von hinten = nur Hut sichtbar
    elif direction == 'down':
        # Skin (Kopf)
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 8)
        pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 7)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
        pygame.draw.circle(surf, skin_hl, (head_cx - 3, head_cy - 4), 2)
        # Augen — wachsam (offen, KEIN Meditation)
        pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 1)
        pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 1)
        pygame.draw.circle(surf, rune_glow, (head_cx - 3, head_cy - 1), 1)
        pygame.draw.circle(surf, rune_glow, (head_cx + 3, head_cy - 1), 1)
        # Tiefere Augenhoehlen (Schatten unter Augenbrauen)
        pygame.draw.line(surf, skin_sh,
                          (head_cx - 5, head_cy - 2),
                          (head_cx - 1, head_cy - 2), 1)
        pygame.draw.line(surf, skin_sh,
                          (head_cx + 1, head_cy - 2),
                          (head_cx + 5, head_cy - 2), 1)
        # Augenbrauen (grau, buschig)
        pygame.draw.line(surf, beard,
                          (head_cx - 5, head_cy - 3),
                          (head_cx - 2, head_cy - 3), 2)
        pygame.draw.line(surf, beard,
                          (head_cx + 2, head_cy - 3),
                          (head_cx + 5, head_cy - 3), 2)
        # Nase
        pygame.draw.line(surf, skin_sh,
                          (head_cx, head_cy + 1),
                          (head_cx - 1, head_cy + 3), 1)
        # Bart (langer, grauer Bart bis zur Robe runter)
        beard_pts = [
            (head_cx - 5, head_cy + 4),
            (head_cx + 5, head_cy + 4),
            (head_cx + 4, head_cy + 8),
            (head_cx + 2, head_cy + 11),
            (head_cx, head_cy + 13),
            (head_cx - 2, head_cy + 11),
            (head_cx - 4, head_cy + 8),
        ]
        pygame.draw.polygon(surf, beard, beard_pts)
        pygame.draw.polygon(surf, OL, beard_pts, 1)
        # Bart-Strähnen
        pygame.draw.line(surf, beard_dk,
                          (head_cx - 3, head_cy + 5),
                          (head_cx - 1, head_cy + 11), 1)
        pygame.draw.line(surf, beard_dk,
                          (head_cx + 1, head_cy + 5),
                          (head_cx + 3, head_cy + 11), 1)
        # Schnurrbart-Andeutung
        pygame.draw.line(surf, beard_dk,
                          (head_cx - 4, head_cy + 4),
                          (head_cx + 4, head_cy + 4), 1)
        # Mund (versteckt im Bart, nur Andeutung)
        # — implizit durch den Bart
    else:
        # Profil (right)
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 8)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
        # Nase (Profil)
        pygame.draw.polygon(surf, skin, [
            (head_cx + 7, head_cy - 1),
            (head_cx + 10, head_cy + 1),
            (head_cx + 8, head_cy + 3),
            (head_cx + 6, head_cy + 2),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 7, head_cy - 1),
            (head_cx + 10, head_cy + 1),
            (head_cx + 8, head_cy + 3),
            (head_cx + 6, head_cy + 2),
        ], 1)
        # Auge
        pygame.draw.circle(surf, rune_glow, (head_cx + 4, head_cy - 1), 1)
        # Augenbraue
        pygame.draw.line(surf, beard,
                          (head_cx + 2, head_cy - 3),
                          (head_cx + 6, head_cy - 3), 2)
        # Bart-Profil (haengt zur Seite herab)
        beard_profile = [
            (head_cx - 3, head_cy + 4),
            (head_cx + 5, head_cy + 4),
            (head_cx + 4, head_cy + 12),
            (head_cx + 1, head_cy + 13),
            (head_cx - 2, head_cy + 10),
        ]
        pygame.draw.polygon(surf, beard, beard_profile)
        pygame.draw.polygon(surf, OL, beard_profile, 1)

    # ============================================================
    # HAT — breitkrempig + flache Spitze (NICHT der spitze D&D-Wizard)
    # Velgrad-Style: scholar/inquisitor mit weitem Krempen-Hut.
    # ============================================================
    if direction == 'up':
        # Hut von hinten (nur die Krempe + Top sichtbar)
        # Breite Krempe
        brim_pts = [
            (head_cx - 16, head_cy - 5),
            (head_cx + 16, head_cy - 5),
            (head_cx + 14, head_cy - 3),
            (head_cx - 14, head_cy - 3),
        ]
        pygame.draw.polygon(surf, hat, brim_pts)
        pygame.draw.polygon(surf, OL, brim_pts, 1)
        # Hut-Krone (cylindrisch)
        crown_pts = [
            (head_cx - 7, head_cy - 5),
            (head_cx + 7, head_cy - 5),
            (head_cx + 6, head_cy - 14),
            (head_cx - 6, head_cy - 14),
        ]
        pygame.draw.polygon(surf, hat, crown_pts)
        pygame.draw.polygon(surf, OL, crown_pts, 1)
        pygame.draw.line(surf, hat_lt,
                          (head_cx - 5, head_cy - 6),
                          (head_cx - 5, head_cy - 13), 1)
        # Bronze-Hatband
        pygame.draw.line(surf, robe_trim,
                          (head_cx - 7, head_cy - 6),
                          (head_cx + 7, head_cy - 6), 2)
    elif direction == 'down':
        # Hut von vorne
        # Krone (cylindrisch, leicht konisch)
        crown_pts = [
            (head_cx - 8, head_cy - 4),
            (head_cx + 8, head_cy - 4),
            (head_cx + 6, head_cy - 18),
            (head_cx - 6, head_cy - 18),
        ]
        pygame.draw.polygon(surf, hat, crown_pts)
        pygame.draw.polygon(surf, OL, crown_pts, 1)
        # Krone-Highlight links
        pygame.draw.polygon(surf, hat_lt, [
            (head_cx - 7, head_cy - 4),
            (head_cx - 4, head_cy - 4),
            (head_cx - 5, head_cy - 18),
            (head_cx - 6, head_cy - 18),
        ])
        # Krempe (breit, schwingend)
        brim_pts = [
            (head_cx - 17, head_cy - 3),
            (head_cx + 17, head_cy - 3),
            (head_cx + 15, head_cy - 1),
            (head_cx + 10, head_cy),
            (head_cx - 10, head_cy),
            (head_cx - 15, head_cy - 1),
        ]
        pygame.draw.polygon(surf, hat, brim_pts)
        pygame.draw.polygon(surf, OL, brim_pts, 2)
        pygame.draw.line(surf, hat_lt,
                          (head_cx - 16, head_cy - 2),
                          (head_cx + 16, head_cy - 2), 1)
        # Bronze-Hatband mit Sigil
        pygame.draw.line(surf, robe_trim,
                          (head_cx - 6, head_cy - 5),
                          (head_cx + 6, head_cy - 5), 2)
        pygame.draw.line(surf, robe_trim_lt,
                          (head_cx - 5, head_cy - 5),
                          (head_cx + 5, head_cy - 5), 1)
        # Center-Sigil am Hatband
        pygame.draw.circle(surf, rune_glow, (head_cx, head_cy - 5), 2)
        pygame.draw.circle(surf, rune, (head_cx, head_cy - 5), 1)
    else:
        # Profil (right)
        # Krone
        crown_pts = [
            (head_cx - 7, head_cy - 4),
            (head_cx + 7, head_cy - 4),
            (head_cx + 5, head_cy - 18),
            (head_cx - 5, head_cy - 18),
        ]
        pygame.draw.polygon(surf, hat, crown_pts)
        pygame.draw.polygon(surf, OL, crown_pts, 1)
        # Krempe (Profil — eine Seite ueberhaengend)
        brim_pts = [
            (head_cx - 13, head_cy - 3),
            (head_cx + 15, head_cy - 3),
            (head_cx + 12, head_cy),
            (head_cx - 11, head_cy),
        ]
        pygame.draw.polygon(surf, hat, brim_pts)
        pygame.draw.polygon(surf, OL, brim_pts, 2)
        # Hatband
        pygame.draw.line(surf, robe_trim,
                          (head_cx - 4, head_cy - 5),
                          (head_cx + 4, head_cy - 5), 2)

    # ============================================================
    # STAFF — Front-Half + Crystal
    # ============================================================
    if direction != 'up':
        staff_x = cx - 19 + staff_tilt
        staff_top_y = fy - 100
        staff_bot_y = fy - 4
        grip_y = fy - 52
        # Front-Schaft (unten, von Hand bis Boden)
        pygame.draw.line(surf, wood, (staff_x, grip_y + 6),
                          (staff_x, staff_bot_y), 3)
        pygame.draw.line(surf, OL, (staff_x, grip_y + 6),
                          (staff_x, staff_bot_y), 1)
        pygame.draw.line(surf, wood_lt, (staff_x - 1, grip_y + 7),
                          (staff_x - 1, staff_bot_y - 1), 1)
        # Lederwickel-Grip an Hand-Position
        pygame.draw.rect(surf, wood_dk,
                          (staff_x - 2, grip_y - 3, 5, 10))
        pygame.draw.rect(surf, OL,
                          (staff_x - 2, grip_y - 3, 5, 10), 1)
        for gy in (grip_y - 1, grip_y + 2, grip_y + 5):
            pygame.draw.line(surf, OL,
                              (staff_x - 2, gy),
                              (staff_x + 2, gy), 1)
        # Bronze-Cap unten
        pygame.draw.circle(surf, robe_trim, (staff_x, staff_bot_y), 3)
        pygame.draw.circle(surf, OL, (staff_x, staff_bot_y), 3, 1)
        # Bronze-Halterung am Staff-Top (Krallen die Kristall halten)
        for px, py in ((staff_x - 3, staff_top_y + 3),
                        (staff_x + 3, staff_top_y + 3),
                        (staff_x, staff_top_y + 6)):
            pygame.draw.circle(surf, robe_trim, (px, py), 1)
            pygame.draw.circle(surf, OL, (px, py), 1, 1)
        # Kristall (gluehend, pulsierend) am Stab-Top
        # Mehrschichtiger Glow
        for r_, alpha_ in ((6, 70), (5, 110), (4, 180)):
            glow = pygame.Surface((r_ * 2 + 2, r_ * 2 + 2), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*rune_glow, alpha_),
                                (r_ + 1, r_ + 1), r_)
            surf.blit(glow, (staff_x - r_ - 1, staff_top_y - r_ - 1))
        # Kristall selbst (Diamant-Form)
        diamond_pts = [
            (staff_x, staff_top_y - 6),
            (staff_x + 4, staff_top_y),
            (staff_x, staff_top_y + 6),
            (staff_x - 4, staff_top_y),
        ]
        pygame.draw.polygon(surf, crystal, diamond_pts)
        pygame.draw.polygon(surf, OL, diamond_pts, 1)
        # Crystal-Core (sehr hell)
        pygame.draw.circle(surf, crystal_core,
                            (staff_x, staff_top_y), 2)
        pygame.draw.circle(surf, (255, 255, 255),
                            (staff_x - 1, staff_top_y - 1), 1)

    return surf


def _draw_mage_iso_new(screen, p, sx, sy, walk_phase, color):
    """Mage-Renderer (Update #195) — eigenes Sprite-Set.
    Klar unterscheidbar von Krieger (Plate) und Moench (Wickelrobe).
    """
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('mage', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


def _gen_ranger_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Ranger/Jaegerin (Update #196).

    Lore: Saattraegerin, Mahnmal-Gilde-Soeldner, Zhar-Eth-Speertraegerin
    teilen diese Silhouette (gemeinsamer rogue-proxy). Visual: dunkle
    Kapuze, schlanke Leder-Armor, Carquois auf dem Ruecken, Bogen
    seitlich gehalten. Klar anders als Krieger (Plate), Moench (Robe)
    und Mage (Hut+Bart).

    Layer (back→front):
      bow-back-half → cloak → quiver → boots → legs → torso →
      bracers → arms → hood → bow-front-half
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Ranger-Palette (Forest/Hunter — Natur-Toene) ---
    leather    = (68, 48, 32)        # Lederpanzer-Haupt
    leather_lt = (118, 86, 56)       # Highlights
    leather_dk = (38, 26, 16)        # Schatten / Outline
    cloth      = base_color          # Klassen-Farbe = Stoff/Kapuze
    cloth_lt   = _shade(base_color, 1.22)
    cloth_dk   = _shade(base_color, 0.62)
    skin       = (200, 158, 118)     # gebraeunt (Outdoor)
    skin_sh    = (148, 108, 78)
    skin_hl    = (228, 188, 148)
    metal      = (162, 165, 172)
    metal_lt   = (215, 220, 228)
    metal_dk   = (95, 100, 108)
    wood       = (88, 60, 36)        # Bogenholz
    wood_lt    = (138, 100, 64)
    wood_dk    = (52, 36, 20)
    string     = (220, 215, 195)     # Sehne / Bow-string
    OL         = (12, 10, 8)

    # Walk-Bob
    if frame == 1:
        l_dy, r_dy = -3, 1
        arm_swing = -1
        cloak_sway = -1
    elif frame == 3:
        l_dy, r_dy = 1, -3
        arm_swing = 1
        cloak_sway = 1
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0
        cloak_sway = 0

    # ============================================================
    # BOW — Back-Half (oberer Halbkreis hinter Kopf/Schulter)
    # ============================================================
    if direction != 'up':
        # Bow haengt vertikal an der linken Seite (linke Hand)
        bow_cx = cx - 18
        bow_cy_top = fy - 88
        bow_cy_bot = fy - 36
        # Bogen als Bogen-Form (zwei Halbkreise verbunden)
        # Oberer Limb (back-half)
        pygame.draw.arc(surf, wood,
                         (bow_cx - 6, bow_cy_top - 4, 12, 32),
                         math.pi * 0.3, math.pi * 0.95, 3)
        pygame.draw.arc(surf, OL,
                         (bow_cx - 6, bow_cy_top - 4, 12, 32),
                         math.pi * 0.3, math.pi * 0.95, 1)

    # ============================================================
    # CLOAK — kurz, hinten, schwingt mit Walk
    # ============================================================
    cloak_top = fy - 60
    cloak_bot = fy - 22
    cloak_pts = [
        (cx - 14, cloak_top),
        (cx + 14, cloak_top),
        (cx + 16, cloak_top + 12),
        (cx + 14 + cloak_sway, cloak_bot - 2),
        (cx + 8, cloak_bot),
        (cx, cloak_bot - 3),
        (cx - 8, cloak_bot),
        (cx - 14 + cloak_sway, cloak_bot - 2),
        (cx - 16, cloak_top + 12),
    ]
    pygame.draw.polygon(surf, cloth_dk, cloak_pts)
    pygame.draw.polygon(surf, OL, cloak_pts, 2)
    # Falten
    for fx_ in (cx - 8, cx, cx + 8):
        pygame.draw.line(surf, cloak_pts[0][0:1] and (28, 22, 14),
                          (fx_, cloak_top + 2),
                          (fx_ + cloak_sway, cloak_bot - 4), 1)
    # Saum-Highlight
    pygame.draw.line(surf, cloth,
                      (cx - 13, cloak_bot - 4),
                      (cx + 13, cloak_bot - 4), 1)

    # ============================================================
    # QUIVER — auf dem Ruecken (linke Schulter)
    # ============================================================
    if direction != 'up':
        quiver_x = cx + 14
        quiver_y_top = cloak_top - 4
        quiver_y_bot = cloak_top + 22
        pygame.draw.rect(surf, leather,
                          (quiver_x - 3, quiver_y_top,
                           6, quiver_y_bot - quiver_y_top))
        pygame.draw.rect(surf, OL,
                          (quiver_x - 3, quiver_y_top,
                           6, quiver_y_bot - quiver_y_top), 1)
        pygame.draw.line(surf, leather_lt,
                          (quiver_x - 2, quiver_y_top + 1),
                          (quiver_x - 2, quiver_y_bot - 2), 1)
        # Pfeile (Federn oben sichtbar)
        for ax in (quiver_x - 1, quiver_x + 1):
            # Pfeil-Federn
            pygame.draw.line(surf, cloth_lt,
                              (ax - 1, quiver_y_top - 3),
                              (ax + 1, quiver_y_top - 3), 1)
            pygame.draw.line(surf, cloth,
                              (ax, quiver_y_top - 5),
                              (ax, quiver_y_top - 2), 1)
        # Strap-Linie ueber die Schulter
        pygame.draw.line(surf, leather_dk,
                          (cx - 12, cloak_top + 6),
                          (quiver_x, quiver_y_top + 4), 2)

    # ============================================================
    # BOOTS — bzw. Stiefel mit Wickel
    # ============================================================
    boot_l = pygame.Rect(cx - 12, fy - 6 + l_dy, 10, 6)
    pygame.draw.rect(surf, leather, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_l.x + 1, boot_l.y + 1),
                      (boot_l.right - 2, boot_l.y + 1), 1)
    # Schnuerung
    for ly in (boot_l.y + 2, boot_l.y + 4):
        pygame.draw.line(surf, leather_dk,
                          (boot_l.x + 2, ly),
                          (boot_l.right - 2, ly), 1)
    boot_r = pygame.Rect(cx + 2, fy - 6 + r_dy, 10, 6)
    pygame.draw.rect(surf, leather, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_r.x + 1, boot_r.y + 1),
                      (boot_r.right - 2, boot_r.y + 1), 1)
    for ly in (boot_r.y + 2, boot_r.y + 4):
        pygame.draw.line(surf, leather_dk,
                          (boot_r.x + 2, ly),
                          (boot_r.right - 2, ly), 1)

    # ============================================================
    # LEGS — schlanke Hose, dunkel
    # ============================================================
    leg_l = pygame.Rect(cx - 11, fy - 20 + l_dy, 8, 14)
    pygame.draw.rect(surf, cloth_dk, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, cloth,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    leg_r = pygame.Rect(cx + 3, fy - 20 + r_dy, 8, 14)
    pygame.draw.rect(surf, cloth_dk, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, cloth,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)

    # ============================================================
    # TORSO — Leder-Brustpanzer mit Schnuerung
    # ============================================================
    torso_top = fy - 60
    torso_bot = fy - 22
    torso_pts = [
        (cx - 12, torso_top + 2),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 12, torso_top + 2),
        (cx + 16, torso_top + 12),
        (cx + 15, torso_bot),
        (cx - 15, torso_bot),
        (cx - 16, torso_top + 12),
    ]
    pygame.draw.polygon(surf, leather, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brust-Highlight links
    pygame.draw.polygon(surf, leather_lt, [
        (cx - 10, torso_top + 3),
        (cx - 4, torso_top + 4),
        (cx - 6, torso_top + 14),
        (cx - 13, torso_top + 14),
    ])
    # Schnuerung in der Mitte (X-Cross-Pattern)
    lace_top = torso_top + 6
    lace_bot = torso_bot - 4
    for ly in range(lace_top, lace_bot, 4):
        pygame.draw.line(surf, string,
                          (cx - 3, ly), (cx + 3, ly + 2), 1)
        pygame.draw.line(surf, string,
                          (cx + 3, ly), (cx - 3, ly + 2), 1)
    # Cinch-Punkte (Loecher)
    for ly in range(lace_top, lace_bot, 4):
        pygame.draw.circle(surf, OL, (cx - 4, ly + 1), 1)
        pygame.draw.circle(surf, OL, (cx + 4, ly + 1), 1)

    # Belt
    belt_y = torso_bot - 4
    pygame.draw.rect(surf, leather_dk, (cx - 15, belt_y, 30, 4))
    pygame.draw.rect(surf, OL, (cx - 15, belt_y, 30, 4), 1)
    # Buckle (metall)
    pygame.draw.rect(surf, metal, (cx - 2, belt_y - 1, 4, 6))
    pygame.draw.rect(surf, OL, (cx - 2, belt_y - 1, 4, 6), 1)
    pygame.draw.line(surf, metal_lt,
                      (cx - 1, belt_y),
                      (cx - 1, belt_y + 4), 1)

    # ============================================================
    # ARMS — kurz mit Lederwickel-Bracers
    # ============================================================
    arm_top = torso_top + 6
    # Linker Arm
    arm_l = pygame.Rect(cx - 18, arm_top + arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Bracer (Stoff-Wrap)
    pygame.draw.rect(surf, cloth_dk,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5), 1)
    # Hand
    pygame.draw.rect(surf, skin, (arm_l.x, arm_l.bottom, 5, 4))
    pygame.draw.rect(surf, OL, (arm_l.x, arm_l.bottom, 5, 4), 1)

    # Rechter Arm
    arm_r = pygame.Rect(cx + 13, arm_top - arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, cloth_dk,
                      (arm_r.x, arm_r.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 5, 7, 5), 1)
    pygame.draw.rect(surf, skin, (arm_r.x + 1, arm_r.bottom, 5, 4))
    pygame.draw.rect(surf, OL, (arm_r.x + 1, arm_r.bottom, 5, 4), 1)

    # ============================================================
    # HEAD + HOOD/COWL — Update #196b: Hood drapiert sich JETZT auf
    # die Schultern, kein Gap mehr zwischen Kopf-Bottom und Torso.
    # Kopf 2px tiefer (torso_top - 10 statt - 12).
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    # Cowl-Bottom-Y: das ist die unterste Stelle wo das Hood/Cape den
    # Body trifft (sollte mit dem Torso ueberlappen).
    cowl_y = torso_top + 4
    if direction == 'up':
        # Hood von hinten — geht von Kopf-Top runter ueber die Schultern
        hood_back = [
            (head_cx - 14, cowl_y),         # links auf der Schulter
            (head_cx - 13, head_cy - 2),    # Hood-Side links
            (head_cx - 8, head_cy - 10),    # Hood-Schulter oben links
            (head_cx, head_cy - 12),        # Hood-Top
            (head_cx + 8, head_cy - 10),
            (head_cx + 13, head_cy - 2),
            (head_cx + 14, cowl_y),         # rechts auf der Schulter
        ]
        pygame.draw.polygon(surf, cloth_dk, hood_back)
        pygame.draw.polygon(surf, OL, hood_back, 2)
        # Center-Naht
        pygame.draw.line(surf, cloak_pts[0][0:1] and (28, 22, 14),
                          (head_cx, head_cy - 10),
                          (head_cx, cowl_y - 1), 1)
        # Hood-Top-Highlight links
        pygame.draw.line(surf, cloth,
                          (head_cx - 11, head_cy - 4),
                          (head_cx - 7, head_cy - 9), 1)
    elif direction == 'down':
        # Hood-Cowl: drapiert sich auf die Schultern und umrahmt das Gesicht
        # Layer 1: Hood-Body (von Schulter zu Schulter ueber den Kopf)
        hood_outline = [
            (head_cx - 14, cowl_y),         # linke Schulter
            (head_cx - 13, head_cy - 1),    # Hood-Seite links
            (head_cx - 10, head_cy - 8),    # Hood-Ecke links
            (head_cx - 3, head_cy - 12),    # Hood-Top links
            (head_cx + 3, head_cy - 12),    # Hood-Top rechts
            (head_cx + 10, head_cy - 8),
            (head_cx + 13, head_cy - 1),
            (head_cx + 14, cowl_y),         # rechte Schulter
            # Innenkanten — Gesichts-Oeffnung
            (head_cx + 7, head_cy + 1),
            (head_cx + 8, head_cy - 4),
            (head_cx + 5, head_cy - 8),
            (head_cx, head_cy - 9),
            (head_cx - 5, head_cy - 8),
            (head_cx - 8, head_cy - 4),
            (head_cx - 7, head_cy + 1),
        ]
        pygame.draw.polygon(surf, cloth_dk, hood_outline)
        pygame.draw.polygon(surf, OL, hood_outline, 2)
        # Skin/Face IN der Hood-Oeffnung
        pygame.draw.circle(surf, skin, (head_cx, head_cy - 2), 7)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy - 1), 6)
        pygame.draw.circle(surf, OL, (head_cx, head_cy - 2), 7, 1)
        # Hood-Highlight links
        pygame.draw.line(surf, cloth,
                          (head_cx - 12, head_cy - 3),
                          (head_cx - 9, head_cy - 9), 1)
        # Schatten ueber Augen (typischer Hood-Look)
        pygame.draw.rect(surf, leather_dk,
                          (head_cx - 5, head_cy - 5, 10, 3))
        # Gluehende Augen aus dem Schatten
        pygame.draw.circle(surf, cloth_lt, (head_cx - 2, head_cy - 3), 1)
        pygame.draw.circle(surf, cloth_lt, (head_cx + 2, head_cy - 3), 1)
        # Nase-Andeutung
        pygame.draw.line(surf, skin_sh,
                          (head_cx, head_cy),
                          (head_cx, head_cy + 2), 1)
        # Kinn-Schatten
        pygame.draw.line(surf, skin_sh,
                          (head_cx - 2, head_cy + 3),
                          (head_cx + 2, head_cy + 3), 1)
    else:
        # Profil — Hood seitlich, drapiert auf Schultern
        # Skin zuerst (wird vom Hood teilweise verdeckt)
        pygame.draw.circle(surf, skin, (head_cx, head_cy - 2), 7)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy - 1), 6)
        pygame.draw.circle(surf, OL, (head_cx, head_cy - 2), 7, 1)
        # Hood-Profil
        hood_profile = [
            (head_cx - 13, cowl_y),         # linke Schulter
            (head_cx - 12, head_cy - 3),    # Hood-Seite links
            (head_cx - 7, head_cy - 11),    # Hood-Ecke
            (head_cx + 3, head_cy - 12),    # Hood-Top
            (head_cx + 10, head_cy - 7),    # Hood-Front
            (head_cx + 11, head_cy - 1),
            # Innenkanten (Gesicht sichtbar nach rechts)
            (head_cx + 7, head_cy + 1),
            (head_cx + 6, head_cy - 4),
            (head_cx + 2, head_cy - 7),
            (head_cx - 4, head_cy - 6),
            (head_cx - 6, head_cy - 2),
            (head_cx - 8, head_cy + 1),
            (head_cx - 14, cowl_y),
        ]
        pygame.draw.polygon(surf, cloth_dk, hood_profile)
        pygame.draw.polygon(surf, OL, hood_profile, 2)
        # Hood-Highlight oben
        pygame.draw.line(surf, cloth,
                          (head_cx - 7, head_cy - 9),
                          (head_cx + 2, head_cy - 11), 1)
        # Sichtbares Auge
        pygame.draw.circle(surf, cloth_lt, (head_cx + 4, head_cy - 1), 1)
        # Nase-Andeutung
        pygame.draw.polygon(surf, skin, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ], 1)

    # ============================================================
    # BOW — Front-Half (vor dem Body)
    # ============================================================
    if direction != 'up':
        bow_cx = cx - 18
        bow_cy_top = fy - 88
        bow_cy_bot = fy - 36
        # Unterer Limb
        pygame.draw.arc(surf, wood,
                         (bow_cx - 6, bow_cy_bot - 28, 12, 32),
                         math.pi * 1.05, math.pi * 1.7, 3)
        pygame.draw.arc(surf, OL,
                         (bow_cx - 6, bow_cy_bot - 28, 12, 32),
                         math.pi * 1.05, math.pi * 1.7, 1)
        # Sehne — durchgehende Linie
        pygame.draw.line(surf, string,
                          (bow_cx + 2, bow_cy_top + 4),
                          (bow_cx + 2, bow_cy_bot - 4), 1)
        # Mittel-Grip
        pygame.draw.rect(surf, wood_dk,
                          (bow_cx - 2, fy - 60, 4, 8))
        pygame.draw.rect(surf, OL,
                          (bow_cx - 2, fy - 60, 4, 8), 1)
        # Lederwickel am Grip
        for gy in (fy - 58, fy - 55):
            pygame.draw.line(surf, leather_dk,
                              (bow_cx - 2, gy),
                              (bow_cx + 2, gy), 1)

    return surf


def _draw_ranger_iso(screen, p, sx, sy, walk_phase, color):
    """Ranger/Jaeger-Renderer (Update #196)."""
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('ranger', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


def _gen_witch_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Knochenwitwe (Update #198).

    Lore: Curses, Bone-Spells, Minions. KEIN Stab — Dolch + Schaedel-
    Amulett. Dunkle Robe mit Knochen-Saum-Pattern. Hood mit Skull-
    Ornament an der Stirn. Lange schwarze Haare aus der Hood.
    Klar anders als Mage (Hut+Bart) und Ranger (einfache Hood).

    Layer (back→front):
      hair-back → robe-skirt → torso → bone-belt → sleeves → bone-amulet →
      hair-front → face → hood-cowl → skull-ornament → dagger
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Witch-Palette ---
    robe       = base_color                # tiefes Violett aus CLASSES
    robe_lt    = _shade(base_color, 1.18)
    robe_dk    = _shade(base_color, 0.50)
    robe_blk   = _shade(base_color, 0.30)
    bone       = (218, 210, 180)            # Knochen-Weiss
    bone_lt    = (248, 240, 215)
    bone_dk    = (152, 142, 110)
    blood      = (108, 28, 36)              # Bluttropfen / Blade-Stains
    skin       = (228, 200, 178)            # blass (Untote-Aesthetik)
    skin_sh    = (172, 140, 120)
    skin_hl    = (250, 232, 220)
    hair       = (24, 18, 28)               # schwarz mit Violett-Stich
    hair_lt    = (62, 48, 78)
    hood       = robe_dk
    hood_lt    = robe
    metal      = (162, 165, 172)
    metal_lt   = (215, 220, 228)
    eye_glow   = _shade(base_color, 1.6)
    OL         = (10, 8, 12)

    if frame == 1:
        l_dy, r_dy = -2, 1
        sleeve_swing = -2
    elif frame == 3:
        l_dy, r_dy = 1, -2
        sleeve_swing = 2
    else:
        l_dy, r_dy = 0, 0
        sleeve_swing = 0

    # ============================================================
    # HAIR — BACK (lange dunkle Haare hinter den Schultern)
    # ============================================================
    if direction in ('down', 'left', 'right'):
        hair_back_pts = [
            (cx - 13, fy - 78),
            (cx + 13, fy - 78),
            (cx + 16, fy - 54),
            (cx + 14, fy - 40),
            (cx - 14, fy - 40),
            (cx - 16, fy - 54),
        ]
        pygame.draw.polygon(surf, hair, hair_back_pts)
        pygame.draw.polygon(surf, OL, hair_back_pts, 1)
        # Haar-Straehnen-Highlights
        for hx in (cx - 8, cx, cx + 8):
            pygame.draw.line(surf, hair_lt,
                              (hx, fy - 76), (hx + 1, fy - 44), 1)

    # ============================================================
    # ROBE-SKIRT — fliesst zum Boden, Knochen-Saum
    # ============================================================
    skirt_top = fy - 42
    skirt_bot = fy - 2
    skirt_pts = [
        (cx - 18, skirt_top),
        (cx + 18, skirt_top),
        (cx + 22, skirt_bot - 6),
        (cx + 16, skirt_bot - 1),
        (cx + 8, skirt_bot),
        (cx, skirt_bot - 2),
        (cx - 8, skirt_bot),
        (cx - 16, skirt_bot - 1),
        (cx - 22, skirt_bot - 6),
    ]
    pygame.draw.polygon(surf, robe, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 2)
    # Falten
    for fx_ in (cx - 13, cx - 6, cx, cx + 6, cx + 13):
        pygame.draw.line(surf, robe_dk,
                          (fx_, skirt_top + 2),
                          (fx_, skirt_bot - 4), 1)
    # Highlight links
    pygame.draw.line(surf, robe_lt,
                      (cx - 17, skirt_top + 3),
                      (cx - 20, skirt_bot - 8), 1)
    # Knochen-Pattern am Saum — kleine Knochen-Streben
    for bx in range(cx - 14, cx + 15, 6):
        # Vertikales Knochen-Symbol (kleines |-mit Punkten)
        pygame.draw.line(surf, bone,
                          (bx, skirt_bot - 9),
                          (bx, skirt_bot - 4), 1)
        pygame.draw.circle(surf, bone, (bx, skirt_bot - 10), 1)
        pygame.draw.circle(surf, bone, (bx, skirt_bot - 3), 1)

    # ============================================================
    # TORSO — schmaler als Mage (femininere Silhouette)
    # ============================================================
    torso_top = fy - 62
    torso_bot = fy - 42
    torso_pts = [
        (cx - 9, torso_top),
        (cx + 9, torso_top),
        (cx + 13, torso_top + 4),
        (cx + 15, torso_top + 12),
        (cx + 16, torso_bot),
        (cx - 16, torso_bot),
        (cx - 15, torso_top + 12),
        (cx - 13, torso_top + 4),
    ]
    pygame.draw.polygon(surf, robe, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Center-Naht
    pygame.draw.line(surf, robe_dk, (cx, torso_top + 1),
                      (cx, torso_bot - 1), 1)
    # Light-Highlight links
    pygame.draw.line(surf, robe_lt,
                      (cx - 10, torso_top + 4),
                      (cx - 14, torso_top + 16), 1)
    # Brust-Akzent — V-Linie zu beiden Seiten
    pygame.draw.line(surf, robe_dk, (cx - 8, torso_top + 2),
                      (cx, torso_top + 7), 1)
    pygame.draw.line(surf, robe_dk, (cx + 8, torso_top + 2),
                      (cx, torso_top + 7), 1)

    # ============================================================
    # BONE-BELT — Knochen-Schnur am Bauch (kein Lederguertel)
    # ============================================================
    belt_y = torso_bot - 3
    pygame.draw.rect(surf, robe_blk, (cx - 17, belt_y, 34, 4))
    pygame.draw.rect(surf, OL, (cx - 17, belt_y, 34, 4), 1)
    # Reihe von Knochen-Glyphs auf dem Guertel
    for bx in range(cx - 14, cx + 15, 5):
        pygame.draw.circle(surf, bone, (bx, belt_y + 2), 1)
    # Center-Skull-Buckle (kleiner Schaedel)
    pygame.draw.circle(surf, bone, (cx, belt_y + 2), 3)
    pygame.draw.circle(surf, OL, (cx, belt_y + 2), 3, 1)
    pygame.draw.circle(surf, OL, (cx - 1, belt_y + 1), 1)
    pygame.draw.circle(surf, OL, (cx + 1, belt_y + 1), 1)
    pygame.draw.line(surf, OL, (cx, belt_y + 3),
                      (cx, belt_y + 4), 1)

    # ============================================================
    # SLEEVES — schmal, mit Bell-Cuff am Ende
    # ============================================================
    arm_top = torso_top + 6
    # Linker Aermel
    sleeve_l_pts = [
        (cx - 16, arm_top + sleeve_swing),
        (cx - 12, arm_top + sleeve_swing),
        (cx - 14, arm_top + 14 + sleeve_swing),
        (cx - 19, arm_top + 16 + sleeve_swing),
    ]
    pygame.draw.polygon(surf, robe, sleeve_l_pts)
    pygame.draw.polygon(surf, OL, sleeve_l_pts, 1)
    pygame.draw.line(surf, robe_lt,
                      (cx - 17, arm_top + 1 + sleeve_swing),
                      (cx - 18, arm_top + 14 + sleeve_swing), 1)
    # Bell-Cuff (kleiner Knochen-Ring)
    pygame.draw.line(surf, bone,
                      (cx - 19, arm_top + 14 + sleeve_swing),
                      (cx - 14, arm_top + 14 + sleeve_swing), 2)
    # Hand (pale)
    pygame.draw.circle(surf, skin, (cx - 17, arm_top + 18 + sleeve_swing), 3)
    pygame.draw.circle(surf, OL, (cx - 17, arm_top + 18 + sleeve_swing), 3, 1)

    # Rechter Aermel (haelt Dolch)
    sleeve_r_pts = [
        (cx + 12, arm_top - sleeve_swing),
        (cx + 16, arm_top - sleeve_swing),
        (cx + 19, arm_top + 16 - sleeve_swing),
        (cx + 14, arm_top + 14 - sleeve_swing),
    ]
    pygame.draw.polygon(surf, robe, sleeve_r_pts)
    pygame.draw.polygon(surf, OL, sleeve_r_pts, 1)
    pygame.draw.line(surf, robe_dk,
                      (cx + 17, arm_top + 1 - sleeve_swing),
                      (cx + 18, arm_top + 14 - sleeve_swing), 1)
    pygame.draw.line(surf, bone,
                      (cx + 14, arm_top + 14 - sleeve_swing),
                      (cx + 19, arm_top + 14 - sleeve_swing), 2)
    # Hand
    pygame.draw.circle(surf, skin, (cx + 17, arm_top + 18 - sleeve_swing), 3)
    pygame.draw.circle(surf, OL, (cx + 17, arm_top + 18 - sleeve_swing), 3, 1)

    # ============================================================
    # BONE-AMULET — Schaedel-Anhaenger an Kette
    # ============================================================
    if direction != 'up':
        # Kette
        for cy_ in range(torso_top - 2, torso_top + 12, 2):
            pygame.draw.circle(surf, metal, (cx, cy_), 1)
            pygame.draw.circle(surf, metal_lt, (cx, cy_), 1, 1)
        # Schaedel-Pendant
        skull_y = torso_top + 14
        pygame.draw.circle(surf, bone, (cx, skull_y), 4)
        pygame.draw.circle(surf, OL, (cx, skull_y), 4, 1)
        # Augenhoehlen
        pygame.draw.circle(surf, OL, (cx - 1, skull_y - 1), 1)
        pygame.draw.circle(surf, OL, (cx + 2, skull_y - 1), 1)
        # Nase (3-eck)
        pygame.draw.polygon(surf, OL, [
            (cx, skull_y + 1), (cx + 1, skull_y + 2),
            (cx - 1, skull_y + 2),
        ])
        # Kiefer
        pygame.draw.line(surf, OL, (cx - 2, skull_y + 3),
                          (cx + 2, skull_y + 3), 1)
        # Highlight am Schaedel
        pygame.draw.circle(surf, bone_lt, (cx - 2, skull_y - 2), 1)

    # ============================================================
    # NECK — sehr kurz, Witch-Hals
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 3, 2, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    # ============================================================
    # HEAD — schmaler, blass
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    if direction == 'up':
        # Hinten — Haare + Hood-Rueckseite
        pygame.draw.circle(surf, hair, (head_cx, head_cy), 9)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
        # Haar-Highlights
        pygame.draw.line(surf, hair_lt,
                          (head_cx - 5, head_cy - 4),
                          (head_cx + 4, head_cy - 6), 1)
        # Side-Haar-Strands (sichtbar an den Seiten)
        for sx_ in (head_cx - 10, head_cx + 10):
            pygame.draw.line(surf, hair,
                              (sx_, head_cy + 2),
                              (sx_, head_cy + 12), 2)
            pygame.draw.line(surf, OL,
                              (sx_, head_cy + 2),
                              (sx_, head_cy + 12), 1)
    elif direction == 'down':
        # Pale Skin
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 7)
        pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 6)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)
        # Highlight oben links (pale glow)
        pygame.draw.circle(surf, skin_hl, (head_cx - 3, head_cy - 3), 2)
        # Augenringe (Schatten unter Augen — sunken)
        pygame.draw.line(surf, skin_sh,
                          (head_cx - 4, head_cy), (head_cx - 1, head_cy), 1)
        pygame.draw.line(surf, skin_sh,
                          (head_cx + 1, head_cy), (head_cx + 4, head_cy), 1)
        # Glow-Augen (Klassen-Color)
        pygame.draw.circle(surf, eye_glow, (head_cx - 3, head_cy - 1), 1)
        pygame.draw.circle(surf, eye_glow, (head_cx + 3, head_cy - 1), 1)
        pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 1, 1)
        pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 1, 1)
        # Schmale Augenbrauen (boese)
        pygame.draw.line(surf, hair,
                          (head_cx - 5, head_cy - 3),
                          (head_cx - 2, head_cy - 2), 1)
        pygame.draw.line(surf, hair,
                          (head_cx + 2, head_cy - 2),
                          (head_cx + 5, head_cy - 3), 1)
        # Nase (schmal)
        pygame.draw.line(surf, skin_sh,
                          (head_cx, head_cy + 1),
                          (head_cx, head_cy + 3), 1)
        # Mund (schmal, leicht laecheln)
        pygame.draw.line(surf, blood,
                          (head_cx - 2, head_cy + 5),
                          (head_cx + 2, head_cy + 5), 1)
        # Front-Haar-Pony-Strands (rahmen das Gesicht ein)
        pygame.draw.line(surf, hair,
                          (head_cx - 7, head_cy - 3),
                          (head_cx - 5, head_cy + 4), 2)
        pygame.draw.line(surf, hair,
                          (head_cx + 7, head_cy - 3),
                          (head_cx + 5, head_cy + 4), 2)
    else:
        # Profil (right; left via flip)
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 7)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)
        # Nase (Profil)
        pygame.draw.polygon(surf, skin, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ], 1)
        # Glow-Auge
        pygame.draw.circle(surf, eye_glow, (head_cx + 3, head_cy - 1), 1)
        # Augenbraue
        pygame.draw.line(surf, hair,
                          (head_cx + 2, head_cy - 3),
                          (head_cx + 6, head_cy - 2), 1)
        # Haar-Strand (von hinten ueber die Schulter)
        pygame.draw.line(surf, hair,
                          (head_cx - 3, head_cy - 5),
                          (head_cx - 6, head_cy + 6), 2)

    # ============================================================
    # HOOD/COWL — eng anliegend (kein breiter Hut), oben spitz
    # ============================================================
    if direction == 'up':
        # Hood von hinten
        hood_pts = [
            (head_cx - 11, head_cy + 4),
            (head_cx - 12, head_cy - 4),
            (head_cx - 8, head_cy - 10),
            (head_cx - 2, head_cy - 13),
            (head_cx + 3, head_cy - 13),
            (head_cx + 9, head_cy - 10),
            (head_cx + 12, head_cy - 4),
            (head_cx + 11, head_cy + 4),
        ]
        pygame.draw.polygon(surf, hood, hood_pts)
        pygame.draw.polygon(surf, OL, hood_pts, 2)
        # Center-Naht
        pygame.draw.line(surf, OL,
                          (head_cx, head_cy - 12),
                          (head_cx, head_cy + 3), 1)
    elif direction == 'down':
        # Hood von vorn — umrahmt das Gesicht, oben spitz
        # Layer 1: Hood-Background (von hinten)
        hood_back_pts = [
            (head_cx - 11, head_cy + 5),
            (head_cx - 12, head_cy - 4),
            (head_cx - 8, head_cy - 10),
            (head_cx - 2, head_cy - 14),
            (head_cx + 3, head_cy - 14),
            (head_cx + 9, head_cy - 10),
            (head_cx + 12, head_cy - 4),
            (head_cx + 11, head_cy + 5),
            (head_cx + 7, head_cy + 4),
            (head_cx + 8, head_cy - 4),
            (head_cx + 4, head_cy - 8),
            (head_cx, head_cy - 9),
            (head_cx - 4, head_cy - 8),
            (head_cx - 8, head_cy - 4),
            (head_cx - 7, head_cy + 4),
        ]
        pygame.draw.polygon(surf, hood, hood_back_pts)
        pygame.draw.polygon(surf, OL, hood_back_pts, 2)
        # Hood-Highlight links (Stoff-Falte)
        pygame.draw.line(surf, hood_lt,
                          (head_cx - 11, head_cy - 4),
                          (head_cx - 7, head_cy - 11), 1)
        # ============================================================
        # SKULL-ORNAMENT — kleiner Schaedel an der Hood-Stirn
        # ============================================================
        skull_x = head_cx
        skull_y = head_cy - 9
        pygame.draw.circle(surf, bone, (skull_x, skull_y), 3)
        pygame.draw.circle(surf, OL, (skull_x, skull_y), 3, 1)
        # Augenhoehlen
        pygame.draw.circle(surf, OL, (skull_x - 1, skull_y - 1), 1)
        pygame.draw.circle(surf, OL, (skull_x + 1, skull_y - 1), 1)
        # Nase
        pygame.draw.line(surf, OL, (skull_x, skull_y + 1),
                          (skull_x, skull_y + 2), 1)
        # Schaedel-Highlight
        pygame.draw.circle(surf, bone_lt, (skull_x - 1, skull_y - 2), 1)
    else:
        # Profil — Hood seitlich
        hood_profile = [
            (head_cx - 11, head_cy + 5),
            (head_cx - 11, head_cy - 4),
            (head_cx - 6, head_cy - 11),
            (head_cx + 3, head_cy - 13),
            (head_cx + 10, head_cy - 8),
            (head_cx + 12, head_cy - 1),
            (head_cx + 8, head_cy + 3),
            (head_cx + 6, head_cy - 3),
            (head_cx + 2, head_cy - 7),
            (head_cx - 3, head_cy - 6),
            (head_cx - 7, head_cy - 2),
            (head_cx - 7, head_cy + 4),
        ]
        pygame.draw.polygon(surf, hood, hood_profile)
        pygame.draw.polygon(surf, OL, hood_profile, 2)
        # Skull-Ornament (Profil — nur Seite sichtbar)
        skull_x = head_cx + 1
        skull_y = head_cy - 9
        pygame.draw.circle(surf, bone, (skull_x, skull_y), 3)
        pygame.draw.circle(surf, OL, (skull_x, skull_y), 3, 1)

    # ============================================================
    # DAGGER — schmale Klinge in der rechten Hand
    # ============================================================
    if direction != 'up':
        dx = cx + 17
        grip_y = arm_top + 16 - sleeve_swing
        # Grip (Leder)
        pygame.draw.rect(surf, (52, 36, 24),
                          (dx - 1, grip_y, 3, 5))
        # Crossguard (Bronze)
        pygame.draw.rect(surf, (122, 88, 52),
                          (dx - 3, grip_y - 1, 7, 2))
        pygame.draw.rect(surf, OL,
                          (dx - 3, grip_y - 1, 7, 2), 1)
        # Klinge (schmal, mit Blut-Spur)
        blade_top = grip_y - 14
        pygame.draw.polygon(surf, metal, [
            (dx - 1, grip_y - 1),
            (dx + 1, grip_y - 1),
            (dx, blade_top),
        ])
        pygame.draw.polygon(surf, OL, [
            (dx - 1, grip_y - 1),
            (dx + 1, grip_y - 1),
            (dx, blade_top),
        ], 1)
        # Highlight
        pygame.draw.line(surf, metal_lt,
                          (dx - 1, grip_y - 3),
                          (dx, blade_top + 2), 1)
        # Blut-Tropfen an der Spitze
        pygame.draw.circle(surf, blood,
                            (dx, blade_top - 2), 1)
        pygame.draw.line(surf, blood,
                          (dx, blade_top + 1),
                          (dx, blade_top + 4), 1)

    return surf


def _draw_witch_iso(screen, p, sx, sy, walk_phase, color):
    """Witch-Renderer (Update #198) — eigenes Sprite-Set."""
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('witch', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


def _gen_druid_sprite(base_color, direction, frame) -> pygame.Surface:
    """Velgrad-Wandelnde / Druidin (Update #199).

    Lore: Drei-Tiere-Lineage (Baer/Wolf/Wyvern), Wetter-Magie.
    Visual: Wolfspelz-Hood mit Ohren, Leder/Pelz-Layered-Outfit, gnarled
    Holz-Walking-Staff, Holz-Totem-Anhaenger, Tribal-Face-Paint, Bone-
    Tooth-Halskette. Erdtoene (Braun + Moos-Gruen).

    Klar anders als:
      Krieger (Iron-Plate) / Moench (Stoff-Wickelrobe) / Mage (Hut+Bart)
      Witch (Hood+Skull) / Ranger (Simple Hood+Bow)
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Druid-Palette (Erde/Wald) ---
    leather    = base_color                # braun
    leather_lt = _shade(base_color, 1.30)
    leather_dk = _shade(base_color, 0.55)
    fur        = (172, 142, 96)            # Wolfsfell-Brown
    fur_lt     = (212, 178, 130)
    fur_dk     = (108, 86, 56)
    moss       = (88, 112, 62)             # Moos-Akzent
    moss_lt    = (132, 162, 92)
    bone       = (220, 210, 178)
    bone_dk    = (158, 148, 118)
    wood       = (88, 60, 36)
    wood_lt    = (132, 96, 60)
    wood_dk    = (52, 34, 18)
    skin       = (212, 172, 130)           # gebraunt
    skin_sh    = (162, 122, 88)
    skin_hl    = (238, 198, 156)
    paint      = (148, 38, 42)             # Tribal-Rot
    eye_glow   = (220, 210, 130)           # Bernstein-Augen
    OL         = (12, 10, 8)

    if frame == 1:
        l_dy, r_dy = -3, 1
        arm_swing = -2
        staff_tilt = -1
    elif frame == 3:
        l_dy, r_dy = 1, -3
        arm_swing = 2
        staff_tilt = 1
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0
        staff_tilt = 0

    # ============================================================
    # STAFF — Back-Half (gnarled wood, kein gerader Stab)
    # ============================================================
    if direction != 'up':
        staff_x = cx + 19 + staff_tilt
        staff_top_y = fy - 94
        staff_bot_y = fy - 4
        grip_y = fy - 50
        # Back-Half — leicht gekruemmt mit Knubbeln
        # Hauptlinie
        pygame.draw.line(surf, wood, (staff_x, staff_top_y),
                          (staff_x - 1, staff_top_y + 20), 3)
        pygame.draw.line(surf, OL, (staff_x, staff_top_y),
                          (staff_x - 1, staff_top_y + 20), 1)
        pygame.draw.line(surf, wood, (staff_x - 1, staff_top_y + 20),
                          (staff_x + 1, grip_y), 3)
        pygame.draw.line(surf, OL, (staff_x - 1, staff_top_y + 20),
                          (staff_x + 1, grip_y), 1)
        # Knubbel (gnarled-Aesthetik)
        pygame.draw.circle(surf, wood, (staff_x - 1, staff_top_y + 10), 3)
        pygame.draw.circle(surf, OL, (staff_x - 1, staff_top_y + 10), 3, 1)
        pygame.draw.circle(surf, wood_lt,
                            (staff_x - 2, staff_top_y + 9), 1)
        # Top: kleines Eichel-/Wurzel-Geflecht (zwei kleine Aeste)
        pygame.draw.line(surf, wood, (staff_x, staff_top_y),
                          (staff_x - 4, staff_top_y - 4), 2)
        pygame.draw.line(surf, OL, (staff_x, staff_top_y),
                          (staff_x - 4, staff_top_y - 4), 1)
        pygame.draw.line(surf, wood, (staff_x, staff_top_y),
                          (staff_x + 3, staff_top_y - 5), 2)
        pygame.draw.line(surf, OL, (staff_x, staff_top_y),
                          (staff_x + 3, staff_top_y - 5), 1)
        # Moos-Bewuchs am Top
        pygame.draw.circle(surf, moss, (staff_x - 1, staff_top_y - 2), 2)
        pygame.draw.circle(surf, moss_lt, (staff_x - 2, staff_top_y - 3), 1)

    # ============================================================
    # PELT-CAPE — Wolfsfell-Mantel hinten (kurz)
    # ============================================================
    cape_top = fy - 58
    cape_bot = fy - 32
    cape_pts = [
        (cx - 16, cape_top),
        (cx + 16, cape_top),
        (cx + 18, cape_top + 8),
        (cx + 14, cape_bot),
        (cx + 6, cape_bot - 2),
        (cx, cape_bot),
        (cx - 6, cape_bot - 2),
        (cx - 14, cape_bot),
        (cx - 18, cape_top + 8),
    ]
    pygame.draw.polygon(surf, fur, cape_pts)
    pygame.draw.polygon(surf, OL, cape_pts, 2)
    # Fell-Textur (Strich-Linien)
    for fx_, fy_off in (
        (cx - 10, 2), (cx - 6, 4), (cx - 2, 3), (cx + 2, 4),
        (cx + 6, 3), (cx + 10, 2),
    ):
        pygame.draw.line(surf, fur_dk,
                          (fx_, cape_top + fy_off),
                          (fx_ + 1, cape_top + fy_off + 5), 1)
        pygame.draw.line(surf, fur_lt,
                          (fx_ + 1, cape_top + fy_off + 1),
                          (fx_ + 2, cape_top + fy_off + 4), 1)

    # ============================================================
    # FEET — Lederstiefel mit Fellbesatz
    # ============================================================
    boot_l = pygame.Rect(cx - 12, fy - 7 + l_dy, 11, 7)
    pygame.draw.rect(surf, leather_dk, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, leather,
                      (boot_l.x + 1, boot_l.y + 2),
                      (boot_l.right - 2, boot_l.y + 2), 1)
    # Fell-Rand oben
    pygame.draw.line(surf, fur,
                      (boot_l.x, boot_l.y),
                      (boot_l.right, boot_l.y), 2)
    boot_r = pygame.Rect(cx + 1, fy - 7 + r_dy, 11, 7)
    pygame.draw.rect(surf, leather_dk, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, leather,
                      (boot_r.x + 1, boot_r.y + 2),
                      (boot_r.right - 2, boot_r.y + 2), 1)
    pygame.draw.line(surf, fur,
                      (boot_r.x, boot_r.y),
                      (boot_r.right, boot_r.y), 2)

    # ============================================================
    # LEGS — leder mit Wickelband-Wraps
    # ============================================================
    leg_l = pygame.Rect(cx - 10, fy - 20 + l_dy, 7, 13)
    pygame.draw.rect(surf, leather, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Wickel-Linien
    for ly in (leg_l.y + 3, leg_l.y + 7, leg_l.y + 10):
        pygame.draw.line(surf, leather_dk,
                          (leg_l.x, ly), (leg_l.right, ly + 1), 1)
    leg_r = pygame.Rect(cx + 3, fy - 20 + r_dy, 7, 13)
    pygame.draw.rect(surf, leather, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    for ly in (leg_r.y + 3, leg_r.y + 7, leg_r.y + 10):
        pygame.draw.line(surf, leather_dk,
                          (leg_r.x, ly), (leg_r.right, ly + 1), 1)

    # ============================================================
    # TUNIC-SKIRT — kurz, Leder-Plate-Streifen am Saum
    # ============================================================
    skirt_top = fy - 32
    skirt_bot = fy - 20
    skirt_pts = [
        (cx - 16, skirt_top),
        (cx + 16, skirt_top),
        (cx + 16, skirt_bot - 2),
        (cx + 12, skirt_bot),
        (cx + 6, skirt_bot - 2),
        (cx - 6, skirt_bot - 2),
        (cx - 12, skirt_bot),
        (cx - 16, skirt_bot - 2),
    ]
    pygame.draw.polygon(surf, leather, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 2)
    # Vertikale Trennlinien (Stoff-Streifen-Look)
    for fx_ in (cx - 11, cx - 4, cx + 4, cx + 11):
        pygame.draw.line(surf, leather_dk,
                          (fx_, skirt_top + 1),
                          (fx_, skirt_bot - 2), 1)
    # Highlight links
    pygame.draw.line(surf, leather_lt,
                      (cx - 15, skirt_top + 1),
                      (cx - 15, skirt_bot - 3), 1)

    # ============================================================
    # TORSO — Leder-Cuirass mit Fellrand-Akzent
    # ============================================================
    torso_top = fy - 62
    torso_bot = fy - 32
    torso_pts = [
        (cx - 13, torso_top + 4),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 13, torso_top + 4),
        (cx + 17, torso_top + 14),
        (cx + 16, torso_bot),
        (cx - 16, torso_bot),
        (cx - 17, torso_top + 14),
    ]
    pygame.draw.polygon(surf, leather, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brust-Highlight links
    pygame.draw.polygon(surf, leather_lt, [
        (cx - 9, torso_top + 2),
        (cx - 2, torso_top + 4),
        (cx - 4, torso_top + 18),
        (cx - 13, torso_top + 16),
    ])
    # Fell-Rand am Schulter-Kragen (oben)
    pygame.draw.line(surf, fur, (cx - 11, torso_top),
                      (cx + 11, torso_top), 2)
    pygame.draw.line(surf, fur_lt, (cx - 10, torso_top - 1),
                      (cx, torso_top - 1), 1)
    pygame.draw.line(surf, fur_dk, (cx + 1, torso_top - 1),
                      (cx + 10, torso_top - 1), 1)

    # Center-Riemen (Leder-Strap mit Knoten)
    pygame.draw.line(surf, leather_dk, (cx, torso_top + 4),
                      (cx, torso_bot - 4), 2)
    # 3 Knoten
    for ky in (torso_top + 8, torso_top + 16, torso_top + 24):
        pygame.draw.circle(surf, leather_dk, (cx, ky), 2)
        pygame.draw.circle(surf, OL, (cx, ky), 2, 1)
        pygame.draw.circle(surf, leather_lt, (cx - 1, ky - 1), 1)

    # ============================================================
    # BELT — Lederguertel
    # ============================================================
    belt_y = torso_bot - 4
    pygame.draw.rect(surf, leather_dk, (cx - 17, belt_y, 34, 4))
    pygame.draw.rect(surf, OL, (cx - 17, belt_y, 34, 4), 1)
    pygame.draw.line(surf, leather,
                      (cx - 16, belt_y + 1),
                      (cx + 15, belt_y + 1), 1)
    # Buckle: Holz-Symbol (kein Metall — Naturmotif)
    pygame.draw.rect(surf, wood, (cx - 3, belt_y - 1, 6, 6))
    pygame.draw.rect(surf, OL, (cx - 3, belt_y - 1, 6, 6), 1)
    # Triskele-Symbol auf Buckle (3-Spirale)
    pygame.draw.circle(surf, wood_lt, (cx, belt_y + 1), 1)
    pygame.draw.circle(surf, wood_lt, (cx - 1, belt_y + 3), 1)
    pygame.draw.circle(surf, wood_lt, (cx + 1, belt_y + 3), 1)

    # ============================================================
    # ARMS / SLEEVES — bare oder leicht bekleidet, mit Bracers
    # ============================================================
    arm_top = torso_top + 8
    # Linker Arm
    arm_l = pygame.Rect(cx - 18, arm_top + arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Bracer (Leder-Wrap mit Bone-Studs)
    pygame.draw.rect(surf, leather_dk,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5), 1)
    # Bone-Studs
    pygame.draw.circle(surf, bone,
                        (arm_l.x + 1, arm_l.bottom - 3), 1)
    pygame.draw.circle(surf, bone,
                        (arm_l.x + 4, arm_l.bottom - 2), 1)
    # Hand
    pygame.draw.rect(surf, skin, (arm_l.x, arm_l.bottom, 5, 4))
    pygame.draw.rect(surf, OL, (arm_l.x, arm_l.bottom, 5, 4), 1)
    # Tribal-Tattoo (linker Oberarm — 3 horizontale Linien)
    for ty in (arm_l.y + 2, arm_l.y + 5, arm_l.y + 8):
        pygame.draw.line(surf, paint,
                          (arm_l.x + 1, ty),
                          (arm_l.right - 1, ty), 1)

    # Rechter Arm (haelt Staff)
    arm_r = pygame.Rect(cx + 13, arm_top - arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, leather_dk,
                      (arm_r.x, arm_r.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 5, 7, 5), 1)
    pygame.draw.circle(surf, bone,
                        (arm_r.x + 1, arm_r.bottom - 3), 1)
    pygame.draw.circle(surf, bone,
                        (arm_r.x + 4, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, skin, (arm_r.x + 1, arm_r.bottom, 5, 4))
    pygame.draw.rect(surf, OL, (arm_r.x + 1, arm_r.bottom, 5, 4), 1)

    # ============================================================
    # TOTEM-ANHAENGER — Holz-Schnitz-Tier auf der Brust
    # ============================================================
    if direction != 'up':
        # Kette
        for cy_ in range(torso_top - 1, torso_top + 12, 2):
            pygame.draw.circle(surf, bone, (cx, cy_), 1)
        # Totem — kleines geschnitztes Wolf-/Bear-Symbol
        tot_y = torso_top + 14
        pygame.draw.rect(surf, wood, (cx - 3, tot_y - 2, 6, 7))
        pygame.draw.rect(surf, OL, (cx - 3, tot_y - 2, 6, 7), 1)
        # Geschnitzte Linien (Tier-Andeutung)
        pygame.draw.line(surf, wood_lt,
                          (cx - 2, tot_y - 1),
                          (cx + 2, tot_y - 1), 1)
        pygame.draw.line(surf, wood_dk,
                          (cx - 1, tot_y + 1),
                          (cx + 1, tot_y + 1), 1)
        pygame.draw.line(surf, wood_lt,
                          (cx - 2, tot_y + 3),
                          (cx + 2, tot_y + 3), 1)
        # 2 Punkte = Wolf-Augen
        pygame.draw.circle(surf, eye_glow, (cx - 1, tot_y), 1)
        pygame.draw.circle(surf, eye_glow, (cx + 1, tot_y), 1)

    # ============================================================
    # NECK — kurz (wie Mage-Update)
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 3, 2, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    # ============================================================
    # HEAD — gebraunt, mit Tribal-Markierungen
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    if direction == 'up':
        # Wolfsfell-Hood von hinten + Ohren
        # Hauptkapuze
        hood_back = [
            (head_cx - 12, head_cy + 5),
            (head_cx - 11, head_cy - 6),
            (head_cx - 4, head_cy - 12),
            (head_cx + 4, head_cy - 12),
            (head_cx + 11, head_cy - 6),
            (head_cx + 12, head_cy + 5),
        ]
        pygame.draw.polygon(surf, fur, hood_back)
        pygame.draw.polygon(surf, OL, hood_back, 2)
        # Fell-Textur
        for fx_ in (head_cx - 6, head_cx, head_cx + 6):
            pygame.draw.line(surf, fur_dk,
                              (fx_, head_cy - 8),
                              (fx_ + 1, head_cy + 3), 1)
            pygame.draw.line(surf, fur_lt,
                              (fx_ + 1, head_cy - 8),
                              (fx_ + 2, head_cy + 1), 1)
        # WOLFSOHREN (links + rechts oben)
        left_ear = [
            (head_cx - 9, head_cy - 9),
            (head_cx - 5, head_cy - 8),
            (head_cx - 7, head_cy - 14),
        ]
        pygame.draw.polygon(surf, fur, left_ear)
        pygame.draw.polygon(surf, OL, left_ear, 1)
        pygame.draw.polygon(surf, fur_dk, [
            (head_cx - 8, head_cy - 9),
            (head_cx - 6, head_cy - 9),
            (head_cx - 7, head_cy - 12),
        ])
        right_ear = [
            (head_cx + 5, head_cy - 8),
            (head_cx + 9, head_cy - 9),
            (head_cx + 7, head_cy - 14),
        ]
        pygame.draw.polygon(surf, fur, right_ear)
        pygame.draw.polygon(surf, OL, right_ear, 1)
        pygame.draw.polygon(surf, fur_dk, [
            (head_cx + 6, head_cy - 9),
            (head_cx + 8, head_cy - 9),
            (head_cx + 7, head_cy - 12),
        ])
    elif direction == 'down':
        # Skin (Gesicht)
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 7)
        pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 6)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)
        pygame.draw.circle(surf, skin_hl, (head_cx - 3, head_cy - 3), 2)
        # Tribal-Paint (rote Querstreifen ueber Augen)
        pygame.draw.line(surf, paint,
                          (head_cx - 6, head_cy - 2),
                          (head_cx + 6, head_cy - 2), 2)
        pygame.draw.line(surf, paint,
                          (head_cx - 4, head_cy + 4),
                          (head_cx + 4, head_cy + 4), 1)
        # Augen (bernsteinfarben, intensiv)
        pygame.draw.circle(surf, eye_glow, (head_cx - 3, head_cy), 1)
        pygame.draw.circle(surf, eye_glow, (head_cx + 3, head_cy), 1)
        pygame.draw.circle(surf, OL, (head_cx - 3, head_cy), 1, 1)
        pygame.draw.circle(surf, OL, (head_cx + 3, head_cy), 1, 1)
        # Augenbrauen
        pygame.draw.line(surf, leather_dk,
                          (head_cx - 5, head_cy - 4),
                          (head_cx - 2, head_cy - 3), 1)
        pygame.draw.line(surf, leather_dk,
                          (head_cx + 2, head_cy - 3),
                          (head_cx + 5, head_cy - 4), 1)
        # Nase
        pygame.draw.line(surf, skin_sh,
                          (head_cx, head_cy + 1),
                          (head_cx, head_cy + 3), 1)
        # Mund
        pygame.draw.line(surf, leather_dk,
                          (head_cx - 2, head_cy + 5),
                          (head_cx + 2, head_cy + 5), 1)

        # Wolfsfell-Hood drueber (umrahmt Gesicht)
        hood_front = [
            (head_cx - 12, head_cy + 5),
            (head_cx - 11, head_cy - 5),
            (head_cx - 6, head_cy - 11),
            (head_cx + 6, head_cy - 11),
            (head_cx + 11, head_cy - 5),
            (head_cx + 12, head_cy + 5),
            (head_cx + 8, head_cy + 3),
            (head_cx + 7, head_cy - 4),
            (head_cx + 3, head_cy - 7),
            (head_cx - 3, head_cy - 7),
            (head_cx - 7, head_cy - 4),
            (head_cx - 8, head_cy + 3),
        ]
        pygame.draw.polygon(surf, fur, hood_front)
        pygame.draw.polygon(surf, OL, hood_front, 2)
        # Fell-Strands
        for fx_ in (head_cx - 9, head_cx - 7, head_cx + 7, head_cx + 9):
            pygame.draw.line(surf, fur_dk,
                              (fx_, head_cy - 6),
                              (fx_, head_cy + 2), 1)
        # Highlight oben
        pygame.draw.line(surf, fur_lt,
                          (head_cx - 9, head_cy - 4),
                          (head_cx - 5, head_cy - 9), 1)
        # WOLFSOHREN
        left_ear = [
            (head_cx - 9, head_cy - 8),
            (head_cx - 5, head_cy - 7),
            (head_cx - 7, head_cy - 13),
        ]
        pygame.draw.polygon(surf, fur, left_ear)
        pygame.draw.polygon(surf, OL, left_ear, 1)
        # Inner-Ear (rosa-braun)
        pygame.draw.polygon(surf, (160, 110, 88), [
            (head_cx - 8, head_cy - 8),
            (head_cx - 6, head_cy - 8),
            (head_cx - 7, head_cy - 11),
        ])
        right_ear = [
            (head_cx + 5, head_cy - 7),
            (head_cx + 9, head_cy - 8),
            (head_cx + 7, head_cy - 13),
        ]
        pygame.draw.polygon(surf, fur, right_ear)
        pygame.draw.polygon(surf, OL, right_ear, 1)
        pygame.draw.polygon(surf, (160, 110, 88), [
            (head_cx + 6, head_cy - 8),
            (head_cx + 8, head_cy - 8),
            (head_cx + 7, head_cy - 11),
        ])
    else:
        # Profil
        pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
        pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 7)
        pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)
        # Tribal-Paint
        pygame.draw.line(surf, paint,
                          (head_cx - 5, head_cy - 2),
                          (head_cx + 5, head_cy - 2), 2)
        # Auge
        pygame.draw.circle(surf, eye_glow,
                            (head_cx + 3, head_cy - 1), 1)
        pygame.draw.circle(surf, OL,
                            (head_cx + 3, head_cy - 1), 1, 1)
        # Nase (Profil)
        pygame.draw.polygon(surf, skin, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 6, head_cy),
            (head_cx + 8, head_cy + 1),
            (head_cx + 7, head_cy + 3),
            (head_cx + 5, head_cy + 2),
        ], 1)
        # Wolfsfell-Hood (Profil)
        hood_profile = [
            (head_cx - 11, head_cy + 5),
            (head_cx - 11, head_cy - 5),
            (head_cx - 6, head_cy - 11),
            (head_cx + 4, head_cy - 11),
            (head_cx + 11, head_cy - 6),
            (head_cx + 12, head_cy + 1),
            (head_cx + 8, head_cy + 4),
            (head_cx + 7, head_cy - 3),
            (head_cx + 4, head_cy - 6),
            (head_cx - 4, head_cy - 6),
            (head_cx - 7, head_cy - 3),
            (head_cx - 8, head_cy + 3),
        ]
        pygame.draw.polygon(surf, fur, hood_profile)
        pygame.draw.polygon(surf, OL, hood_profile, 2)
        # Eine sichtbare Wolfsohre vorn
        ear = [
            (head_cx + 1, head_cy - 8),
            (head_cx + 6, head_cy - 7),
            (head_cx + 4, head_cy - 13),
        ]
        pygame.draw.polygon(surf, fur, ear)
        pygame.draw.polygon(surf, OL, ear, 1)
        pygame.draw.polygon(surf, (160, 110, 88), [
            (head_cx + 2, head_cy - 8),
            (head_cx + 5, head_cy - 8),
            (head_cx + 4, head_cy - 11),
        ])

    # ============================================================
    # STAFF — Front-Half + Top-Knubbel
    # ============================================================
    if direction != 'up':
        staff_x = cx + 19 + staff_tilt
        staff_top_y = fy - 94
        grip_y = fy - 50
        staff_bot_y = fy - 4
        # Lederwickel-Grip
        pygame.draw.rect(surf, wood_dk,
                          (staff_x - 1, grip_y - 3, 5, 10))
        pygame.draw.rect(surf, OL,
                          (staff_x - 1, grip_y - 3, 5, 10), 1)
        for gy in (grip_y - 1, grip_y + 2, grip_y + 5):
            pygame.draw.line(surf, OL,
                              (staff_x - 1, gy),
                              (staff_x + 3, gy), 1)
        # Unterer Schaft (von Grip bis Boden, leicht gekruemmt)
        pygame.draw.line(surf, wood, (staff_x + 1, grip_y + 6),
                          (staff_x, staff_bot_y), 3)
        pygame.draw.line(surf, OL, (staff_x + 1, grip_y + 6),
                          (staff_x, staff_bot_y), 1)
        pygame.draw.line(surf, wood_lt, (staff_x, grip_y + 7),
                          (staff_x - 1, staff_bot_y - 1), 1)
        # Wurzel-Spitze unten (statt Metall-Cap → Holz-Geflecht)
        pygame.draw.line(surf, wood,
                          (staff_x - 2, staff_bot_y),
                          (staff_x + 2, staff_bot_y), 3)
        pygame.draw.line(surf, OL,
                          (staff_x - 2, staff_bot_y),
                          (staff_x + 2, staff_bot_y), 1)

    return surf


def _draw_druid_iso(screen, p, sx, sy, walk_phase, color):
    """Druid-Renderer (Update #199)."""
    direction = direction_from_facing(getattr(p, 'facing', 0.0))
    frame = (int(walk_phase) % 4) if p.moving else 0
    sprite = _get_proc_sprite('druid', color, direction, frame)
    if sprite is None:
        return
    screen.blit(sprite, (int(sx) - sprite.get_width() // 2,
                          int(sy) - PROC_DRAW_FOOT_Y))


_SPRITE_GENERATORS = {
    'warrior': _gen_warrior_sprite,
    'monk':    _gen_monk_sprite,
    'mage':    _gen_mage_sprite,
    'witch':   _gen_witch_sprite,
    'ranger':  _gen_ranger_sprite,
    'druid':   _gen_druid_sprite,
}


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
_MOB_SPRITE_CACHE: dict = {}


def _gen_skeleton_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #202: Detail-Skeleton auf 84x124-Canvas.

    Iconic Undead-Warrior — Schaedel mit Glow-Augen, sichtbare Rippen,
    zerfetzte Plate-Reste, rostiger Krummsaebel, gerissene Schild-
    Halterung. Klar als Skeleton lesbar.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    bone        = (228, 220, 188)
    bone_lt     = (248, 240, 210)
    bone_dk     = (172, 162, 130)
    bone_blk    = (108, 100, 78)
    rust        = (118, 76, 48)
    rust_lt     = (158, 108, 72)
    rust_dk     = (78, 48, 28)
    metal       = (142, 138, 132)
    metal_lt    = (192, 188, 178)
    metal_dk    = (78, 76, 72)
    cloth_rot   = (62, 52, 38)         # zerfetzte Reste
    cloth_rot_lt= (98, 84, 62)
    OL          = (8, 6, 8)

    # Walk-Phase Leg-Offset
    if walk_frame == 1:
        l_dy, r_dy = -2, 1
        arm_swing = -2
    elif walk_frame == 3:
        l_dy, r_dy = 1, -2
        arm_swing = 2
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0

    # ============================================================
    # LEGS — Knochen-Beine (kein Fleisch)
    # ============================================================
    # Linker Fuss-Knochen
    pygame.draw.rect(surf, bone, (cx - 10, fy - 5 + l_dy, 6, 5))
    pygame.draw.rect(surf, OL, (cx - 10, fy - 5 + l_dy, 6, 5), 1)
    # Linker Tibia/Fibula
    pygame.draw.rect(surf, bone, (cx - 9, fy - 22 + l_dy, 4, 17))
    pygame.draw.rect(surf, OL, (cx - 9, fy - 22 + l_dy, 4, 17), 1)
    pygame.draw.line(surf, bone_lt, (cx - 8, fy - 21 + l_dy),
                      (cx - 8, fy - 7 + l_dy), 1)
    # Linke Knochen-Knie
    pygame.draw.circle(surf, bone, (cx - 7, fy - 22 + l_dy), 3)
    pygame.draw.circle(surf, OL, (cx - 7, fy - 22 + l_dy), 3, 1)

    # Rechter Fuss
    pygame.draw.rect(surf, bone, (cx + 4, fy - 5 + r_dy, 6, 5))
    pygame.draw.rect(surf, OL, (cx + 4, fy - 5 + r_dy, 6, 5), 1)
    pygame.draw.rect(surf, bone, (cx + 5, fy - 22 + r_dy, 4, 17))
    pygame.draw.rect(surf, OL, (cx + 5, fy - 22 + r_dy, 4, 17), 1)
    pygame.draw.line(surf, bone_lt, (cx + 6, fy - 21 + r_dy),
                      (cx + 6, fy - 7 + r_dy), 1)
    pygame.draw.circle(surf, bone, (cx + 7, fy - 22 + r_dy), 3)
    pygame.draw.circle(surf, OL, (cx + 7, fy - 22 + r_dy), 3, 1)

    # ============================================================
    # PELVIS — Becken-Knochen
    # ============================================================
    pelvis_pts = [
        (cx - 10, fy - 22),
        (cx + 10, fy - 22),
        (cx + 12, fy - 30),
        (cx + 8, fy - 36),
        (cx - 8, fy - 36),
        (cx - 12, fy - 30),
    ]
    pygame.draw.polygon(surf, bone, pelvis_pts)
    pygame.draw.polygon(surf, OL, pelvis_pts, 1)
    # Becken-Loch (innen)
    pygame.draw.circle(surf, bone_blk, (cx, fy - 28), 4)
    # Highlight
    pygame.draw.line(surf, bone_lt, (cx - 9, fy - 30), (cx - 6, fy - 35), 1)

    # ============================================================
    # ROTTING-CLOTH-REMNANTS — zerfetzte Tunika ueber dem Becken
    # ============================================================
    cloth_pts = [
        (cx - 14, fy - 36),
        (cx + 14, fy - 36),
        (cx + 16, fy - 26),
        (cx + 12, fy - 22),
        (cx + 4, fy - 24),
        (cx - 2, fy - 21),
        (cx - 4, fy - 24),
        (cx - 12, fy - 22),
        (cx - 16, fy - 26),
    ]
    pygame.draw.polygon(surf, cloth_rot, cloth_pts)
    pygame.draw.polygon(surf, OL, cloth_pts, 1)
    # Falten
    for fx_ in (cx - 8, cx, cx + 8):
        pygame.draw.line(surf, (40, 32, 22),
                          (fx_, fy - 34), (fx_, fy - 24), 1)

    # ============================================================
    # SPINE + RIBS — sichtbare Wirbelsaeule + Rippenbogen
    # ============================================================
    spine_top = fy - 64
    spine_bot = fy - 36
    # Wirbel als kleine Kreise alle 4px
    for sy_ in range(spine_top, spine_bot, 4):
        pygame.draw.circle(surf, bone, (cx, sy_), 2)
        pygame.draw.circle(surf, OL, (cx, sy_), 2, 1)
        pygame.draw.circle(surf, bone_lt, (cx - 1, sy_ - 1), 1)
    # Rippen (3 Paar Boegen)
    for ry in (spine_top + 4, spine_top + 12, spine_top + 20):
        # Linke Rippe
        pygame.draw.arc(surf, bone, (cx - 12, ry - 4, 14, 14),
                         math.pi * 0.5, math.pi, 2)
        # Rechte Rippe
        pygame.draw.arc(surf, bone, (cx - 1, ry - 4, 14, 14),
                         0, math.pi * 0.5, 2)
        # Outline
        pygame.draw.arc(surf, OL, (cx - 12, ry - 4, 14, 14),
                         math.pi * 0.5, math.pi, 1)
        pygame.draw.arc(surf, OL, (cx - 1, ry - 4, 14, 14),
                         0, math.pi * 0.5, 1)

    # ============================================================
    # PLATE-RESTS — Rost-Brustpanzer-Bruchstuecke (gehaengt am Skelett)
    # ============================================================
    plate_pts = [
        (cx - 16, spine_top - 2),
        (cx - 12, spine_top),
        (cx - 14, spine_top + 14),
        (cx - 18, spine_top + 8),
    ]
    pygame.draw.polygon(surf, rust, plate_pts)
    pygame.draw.polygon(surf, OL, plate_pts, 1)
    pygame.draw.line(surf, rust_lt,
                      (cx - 15, spine_top),
                      (cx - 17, spine_top + 6), 1)
    # Rost-Flecken
    pygame.draw.circle(surf, rust_dk, (cx - 15, spine_top + 4), 1)
    # Rechte Plate-Bruchstueck
    plate_r = [
        (cx + 12, spine_top),
        (cx + 16, spine_top - 2),
        (cx + 18, spine_top + 10),
        (cx + 14, spine_top + 14),
    ]
    pygame.draw.polygon(surf, rust, plate_r)
    pygame.draw.polygon(surf, OL, plate_r, 1)
    pygame.draw.circle(surf, rust_dk, (cx + 15, spine_top + 6), 1)

    # ============================================================
    # PAULDRONS — angeschlagene Schulter-Plates
    # ============================================================
    # Linke (mit Riss)
    pygame.draw.circle(surf, metal, (cx - 14, spine_top + 2), 6)
    pygame.draw.circle(surf, OL, (cx - 14, spine_top + 2), 6, 1)
    pygame.draw.circle(surf, metal_lt, (cx - 15, spine_top), 2)
    # Riss
    pygame.draw.line(surf, metal_dk,
                      (cx - 17, spine_top + 1),
                      (cx - 13, spine_top + 4), 1)
    pygame.draw.line(surf, OL,
                      (cx - 17, spine_top + 1),
                      (cx - 13, spine_top + 4), 1)

    # Rechte (mit Rost)
    pygame.draw.circle(surf, metal_dk, (cx + 14, spine_top + 2), 6)
    pygame.draw.circle(surf, OL, (cx + 14, spine_top + 2), 6, 1)
    pygame.draw.circle(surf, rust, (cx + 13, spine_top + 4), 1)

    # ============================================================
    # ARMS — Knochen-Arme (radius + ulna)
    # ============================================================
    arm_top = spine_top + 6
    # Linker Arm (haelt Schild)
    pygame.draw.rect(surf, bone, (cx - 19, arm_top + arm_swing, 4, 14))
    pygame.draw.rect(surf, OL, (cx - 19, arm_top + arm_swing, 4, 14), 1)
    pygame.draw.line(surf, bone_lt, (cx - 18, arm_top + 1 + arm_swing),
                      (cx - 18, arm_top + 13 + arm_swing), 1)
    # Ellbogen-Knochen
    pygame.draw.circle(surf, bone, (cx - 17, arm_top + 7 + arm_swing), 2)
    pygame.draw.circle(surf, OL, (cx - 17, arm_top + 7 + arm_swing), 2, 1)
    # Hand (Knochenfinger)
    for fx_ in range(-1, 3):
        pygame.draw.line(surf, bone,
                          (cx - 19 + fx_, arm_top + 13 + arm_swing),
                          (cx - 19 + fx_, arm_top + 16 + arm_swing), 1)

    # Rechter Arm (haelt Schwert)
    pygame.draw.rect(surf, bone, (cx + 15, arm_top - arm_swing, 4, 14))
    pygame.draw.rect(surf, OL, (cx + 15, arm_top - arm_swing, 4, 14), 1)
    pygame.draw.line(surf, bone_lt, (cx + 16, arm_top + 1 - arm_swing),
                      (cx + 16, arm_top + 13 - arm_swing), 1)
    pygame.draw.circle(surf, bone, (cx + 17, arm_top + 7 - arm_swing), 2)
    pygame.draw.circle(surf, OL, (cx + 17, arm_top + 7 - arm_swing), 2, 1)
    for fx_ in range(-1, 3):
        pygame.draw.line(surf, bone,
                          (cx + 15 + fx_, arm_top + 13 - arm_swing),
                          (cx + 15 + fx_, arm_top + 16 - arm_swing), 1)

    # ============================================================
    # SKULL — der Hauptattraktion
    # ============================================================
    head_cx = cx
    head_cy = spine_top - 12
    # Schaedel-Form (leicht eckig)
    skull_pts = [
        (head_cx - 8, head_cy + 7),
        (head_cx - 9, head_cy + 2),
        (head_cx - 9, head_cy - 4),
        (head_cx - 6, head_cy - 9),
        (head_cx + 6, head_cy - 9),
        (head_cx + 9, head_cy - 4),
        (head_cx + 9, head_cy + 2),
        (head_cx + 8, head_cy + 7),
        (head_cx + 4, head_cy + 9),
        (head_cx - 4, head_cy + 9),
    ]
    pygame.draw.polygon(surf, bone, skull_pts)
    pygame.draw.polygon(surf, OL, skull_pts, 2)
    # Schädel-Highlight (Stirn)
    pygame.draw.polygon(surf, bone_lt, [
        (head_cx - 6, head_cy - 7),
        (head_cx, head_cy - 8),
        (head_cx - 2, head_cy - 4),
        (head_cx - 7, head_cy - 3),
    ])
    # Stirn-Risse (battle-damage)
    pygame.draw.line(surf, OL,
                      (head_cx - 4, head_cy - 6),
                      (head_cx - 1, head_cy - 3), 1)
    pygame.draw.line(surf, OL,
                      (head_cx + 2, head_cy - 7),
                      (head_cx + 4, head_cy - 5), 1)

    # Augenhoehlen — tief, schwarz mit Glow
    pygame.draw.ellipse(surf, OL, (head_cx - 6, head_cy - 3, 5, 5))
    pygame.draw.ellipse(surf, OL, (head_cx + 1, head_cy - 3, 5, 5))
    # Glow-Augen (klassen-coloriert)
    pygame.draw.circle(surf, glow_col, (head_cx - 4, head_cy - 1), 1)
    pygame.draw.circle(surf, glow_col, (head_cx + 3, head_cy - 1), 1)
    # Outer-Glow
    glow = pygame.Surface((8, 8), pygame.SRCALPHA)
    pygame.draw.circle(glow, (*glow_col, 80), (4, 4), 3)
    surf.blit(glow, (head_cx - 8, head_cy - 5))
    surf.blit(glow, (head_cx - 1, head_cy - 5))

    # Nase (3-eckiges Loch)
    pygame.draw.polygon(surf, OL, [
        (head_cx, head_cy + 1),
        (head_cx + 2, head_cy + 4),
        (head_cx - 2, head_cy + 4),
    ])

    # Zaehne — gerade Reihe
    pygame.draw.rect(surf, bone_dk, (head_cx - 5, head_cy + 5, 10, 4))
    pygame.draw.rect(surf, OL, (head_cx - 5, head_cy + 5, 10, 4), 1)
    # Zahn-Trenner
    for tx in (-3, -1, 1, 3):
        pygame.draw.line(surf, OL,
                          (head_cx + tx, head_cy + 5),
                          (head_cx + tx, head_cy + 9), 1)

    # Kiefer-Bruch (rechts)
    pygame.draw.line(surf, OL,
                      (head_cx + 4, head_cy + 8),
                      (head_cx + 6, head_cy + 6), 1)

    # ============================================================
    # SWORD — Rost-Krummsaebel rechts
    # ============================================================
    sw_grip_x = cx + 17
    sw_grip_y = arm_top + 14 - arm_swing
    # Grip
    pygame.draw.rect(surf, rust_dk,
                      (sw_grip_x - 1, sw_grip_y, 3, 6))
    pygame.draw.rect(surf, OL,
                      (sw_grip_x - 1, sw_grip_y, 3, 6), 1)
    # Pommel
    pygame.draw.circle(surf, rust, (sw_grip_x, sw_grip_y + 8), 2)
    pygame.draw.circle(surf, OL, (sw_grip_x, sw_grip_y + 8), 2, 1)
    # Crossguard (S-Form)
    pygame.draw.line(surf, rust,
                      (sw_grip_x - 4, sw_grip_y - 1),
                      (sw_grip_x + 4, sw_grip_y - 1), 2)
    pygame.draw.line(surf, OL,
                      (sw_grip_x - 4, sw_grip_y - 1),
                      (sw_grip_x + 4, sw_grip_y - 1), 1)
    # Klinge — leicht gekruemmt (Krummsaebel)
    blade_top = sw_grip_y - 28
    blade_pts = [
        (sw_grip_x - 1, sw_grip_y - 2),
        (sw_grip_x + 1, sw_grip_y - 2),
        (sw_grip_x + 4, blade_top + 8),
        (sw_grip_x + 2, blade_top),
        (sw_grip_x, blade_top - 2),
    ]
    pygame.draw.polygon(surf, metal_dk, blade_pts)
    pygame.draw.polygon(surf, OL, blade_pts, 1)
    # Rost-Flecken
    pygame.draw.circle(surf, rust, (sw_grip_x + 1, sw_grip_y - 10), 1)
    pygame.draw.circle(surf, rust, (sw_grip_x + 3, blade_top + 6), 1)
    # Klinge-Highlight
    pygame.draw.line(surf, metal_lt,
                      (sw_grip_x, sw_grip_y - 4),
                      (sw_grip_x + 2, blade_top + 2), 1)

    # ============================================================
    # SHIELD — gerissener Rund-Schild links
    # ============================================================
    sh_cx = cx - 22
    sh_cy = arm_top + 14 + arm_swing
    # Holz-Schild
    pygame.draw.circle(surf, (90, 60, 36), (sh_cx, sh_cy), 7)
    pygame.draw.circle(surf, OL, (sh_cx, sh_cy), 7, 1)
    # Holz-Maserung
    for dy in (-3, 0, 3):
        pygame.draw.line(surf, (60, 40, 22),
                          (sh_cx - 5, sh_cy + dy),
                          (sh_cx + 5, sh_cy + dy), 1)
    # Metall-Rim
    pygame.draw.circle(surf, metal_dk, (sh_cx, sh_cy), 7, 1)
    # Riss durch den Schild
    pygame.draw.line(surf, OL,
                      (sh_cx - 4, sh_cy - 3),
                      (sh_cx + 5, sh_cy + 4), 1)
    pygame.draw.line(surf, (40, 30, 16),
                      (sh_cx - 4, sh_cy - 3),
                      (sh_cx + 5, sh_cy + 4), 1)
    # Boss in der Mitte (verrostet)
    pygame.draw.circle(surf, rust, (sh_cx, sh_cy), 2)
    pygame.draw.circle(surf, OL, (sh_cx, sh_cy), 2, 1)

    return surf


def _gen_zombie_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #202: Detail-Zombie auf 84x124-Canvas.

    Verrottende Leiche — gruene-graue Haut, zerfetzte Klamotten,
    sichtbare Knochen-Risse, schlurfende Pose, leerstehender Mund.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    rot_skin    = (124, 142, 96)        # gruenlich-grau
    rot_skin_lt = (162, 178, 122)
    rot_skin_sh = (78, 92, 60)
    blood       = (108, 28, 36)
    blood_dk    = (62, 18, 24)
    bone        = (220, 210, 188)
    cloth       = (62, 52, 38)
    cloth_lt    = (98, 84, 62)
    cloth_dk    = (38, 32, 22)
    eye         = (218, 200, 90)         # gelbliche tote Augen
    OL          = (8, 6, 8)

    if walk_frame == 1:
        l_dy, r_dy = -1, 1
        slump = 2
    elif walk_frame == 3:
        l_dy, r_dy = 1, -1
        slump = 2
    else:
        l_dy, r_dy = 0, 0
        slump = 1

    # ============================================================
    # LEGS — verrottete Beine mit blutigen Stellen
    # ============================================================
    # Linker Fuss (barefoot, verrottend)
    pygame.draw.ellipse(surf, rot_skin,
                         (cx - 12, fy - 5 + l_dy, 11, 5))
    pygame.draw.ellipse(surf, OL,
                         (cx - 12, fy - 5 + l_dy, 11, 5), 1)
    # Linker Bein
    leg_l = pygame.Rect(cx - 11, fy - 22 + l_dy, 8, 17)
    pygame.draw.rect(surf, rot_skin, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, rot_skin_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Blut-Flecken
    pygame.draw.circle(surf, blood, (leg_l.x + 3, leg_l.y + 8), 2)
    pygame.draw.circle(surf, blood_dk, (leg_l.x + 4, leg_l.y + 9), 1)
    # Knochen-Spitze (Bruch sichtbar)
    pygame.draw.line(surf, bone,
                      (leg_l.x + 4, leg_l.y + 13),
                      (leg_l.x + 4, leg_l.y + 15), 2)

    # Rechter Fuss + Bein
    pygame.draw.ellipse(surf, rot_skin,
                         (cx + 1, fy - 5 + r_dy, 11, 5))
    pygame.draw.ellipse(surf, OL,
                         (cx + 1, fy - 5 + r_dy, 11, 5), 1)
    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 8, 17)
    pygame.draw.rect(surf, rot_skin, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, rot_skin_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    # Wunde
    pygame.draw.circle(surf, blood, (leg_r.x + 4, leg_r.y + 5), 2)

    # ============================================================
    # TUNIKA / ROTTING-TUNIC — zerfetzt
    # ============================================================
    # Beim Slump leicht nach vorn geneigt (Zombie-Pose)
    torso_top = fy - 62 + slump
    torso_bot = fy - 32
    # Tunika-Polygon (zerfetzt am Saum)
    tunic_pts = [
        (cx - 13, torso_top + 3),
        (cx - 11, torso_top),
        (cx + 11, torso_top),
        (cx + 13, torso_top + 3),
        (cx + 16, torso_top + 14),
        (cx + 15, torso_bot - 2),
        (cx + 12, torso_bot - 4),
        (cx + 8, torso_bot),
        (cx + 4, torso_bot - 3),
        (cx - 4, torso_bot - 3),
        (cx - 8, torso_bot),
        (cx - 12, torso_bot - 4),
        (cx - 15, torso_bot - 2),
        (cx - 16, torso_top + 14),
    ]
    pygame.draw.polygon(surf, cloth, tunic_pts)
    pygame.draw.polygon(surf, OL, tunic_pts, 2)
    # Falten
    for fx_ in (cx - 8, cx, cx + 8):
        pygame.draw.line(surf, cloth_dk,
                          (fx_, torso_top + 2),
                          (fx_, torso_bot - 4), 1)
    # Loecher im Stoff (Haut sichtbar)
    pygame.draw.circle(surf, rot_skin, (cx - 5, torso_top + 8), 3)
    pygame.draw.circle(surf, OL, (cx - 5, torso_top + 8), 3, 1)
    pygame.draw.circle(surf, rot_skin_sh, (cx - 4, torso_top + 9), 2)
    pygame.draw.circle(surf, rot_skin, (cx + 7, torso_top + 16), 2)
    pygame.draw.circle(surf, OL, (cx + 7, torso_top + 16), 2, 1)

    # Blutige Splatter am Stoff
    pygame.draw.circle(surf, blood_dk, (cx - 3, torso_top + 18), 2)
    pygame.draw.circle(surf, blood, (cx + 4, torso_top + 6), 2)
    pygame.draw.line(surf, blood,
                      (cx + 5, torso_top + 7),
                      (cx + 7, torso_top + 11), 1)

    # Highlight links
    pygame.draw.line(surf, cloth_lt,
                      (cx - 13, torso_top + 4),
                      (cx - 14, torso_top + 16), 1)

    # ============================================================
    # ARMS — hängend (Zombie-Pose, leicht ausgestreckt)
    # ============================================================
    arm_top = torso_top + 6
    # Linker Arm — gerade nach unten
    pygame.draw.rect(surf, rot_skin,
                      (cx - 18, arm_top, 5, 15))
    pygame.draw.rect(surf, OL,
                      (cx - 18, arm_top, 5, 15), 1)
    pygame.draw.line(surf, rot_skin_lt,
                      (cx - 17, arm_top + 1),
                      (cx - 17, arm_top + 14), 1)
    # Hand (verkrampft)
    pygame.draw.circle(surf, rot_skin,
                        (cx - 16, arm_top + 17), 3)
    pygame.draw.circle(surf, OL,
                        (cx - 16, arm_top + 17), 3, 1)
    # Knochen-Fingerspitzen
    for fx_ in (-1, 1):
        pygame.draw.line(surf, bone,
                          (cx - 17 + fx_, arm_top + 19),
                          (cx - 17 + fx_, arm_top + 21), 1)

    # Rechter Arm — leicht nach vorn (Greif-Pose)
    pygame.draw.rect(surf, rot_skin,
                      (cx + 13, arm_top + 2, 5, 15))
    pygame.draw.rect(surf, OL,
                      (cx + 13, arm_top + 2, 5, 15), 1)
    pygame.draw.line(surf, rot_skin_lt,
                      (cx + 14, arm_top + 3),
                      (cx + 14, arm_top + 16), 1)
    # Schnittwunde am Arm
    pygame.draw.line(surf, blood,
                      (cx + 14, arm_top + 8),
                      (cx + 17, arm_top + 9), 1)
    # Hand
    pygame.draw.circle(surf, rot_skin,
                        (cx + 15, arm_top + 19), 3)
    pygame.draw.circle(surf, OL,
                        (cx + 15, arm_top + 19), 3, 1)
    for fx_ in (-1, 1):
        pygame.draw.line(surf, bone,
                          (cx + 15 + fx_, arm_top + 21),
                          (cx + 15 + fx_, arm_top + 23), 1)

    # ============================================================
    # NECK + HEAD
    # ============================================================
    # Neck (gebogen — Zombie hat schiefe Haltung)
    pygame.draw.rect(surf, rot_skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    head_cx = cx + slump
    head_cy = torso_top - 10
    # Skin — etwas asymmetrisch
    pygame.draw.circle(surf, rot_skin, (head_cx, head_cy), 9)
    pygame.draw.circle(surf, rot_skin_sh, (head_cx + 1, head_cy + 1), 8)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
    # Highlight
    pygame.draw.circle(surf, rot_skin_lt, (head_cx - 3, head_cy - 3), 2)
    # Stirn-Wunde
    pygame.draw.line(surf, blood,
                      (head_cx - 4, head_cy - 6),
                      (head_cx + 1, head_cy - 4), 2)
    pygame.draw.line(surf, blood_dk,
                      (head_cx - 4, head_cy - 6),
                      (head_cx + 1, head_cy - 4), 1)
    # Verfaulte Wangenpartie (Knochen sichtbar)
    pygame.draw.polygon(surf, bone, [
        (head_cx - 9, head_cy + 1),
        (head_cx - 6, head_cy),
        (head_cx - 5, head_cy + 4),
        (head_cx - 8, head_cy + 4),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx - 9, head_cy + 1),
        (head_cx - 6, head_cy),
        (head_cx - 5, head_cy + 4),
        (head_cx - 8, head_cy + 4),
    ], 1)
    # Augen — leerer Stier (gelblich)
    pygame.draw.circle(surf, eye, (head_cx - 3, head_cy - 1), 2)
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 2, 1)
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, eye, (head_cx + 3, head_cy - 1), 2)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 2, 1)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 1)
    # Augenringe (dunkel)
    pygame.draw.arc(surf, OL,
                     (head_cx - 6, head_cy, 6, 4),
                     0, math.pi, 1)
    pygame.draw.arc(surf, OL,
                     (head_cx, head_cy, 6, 4),
                     0, math.pi, 1)
    # Nase — teilweise weggefault
    pygame.draw.line(surf, OL,
                      (head_cx, head_cy + 1),
                      (head_cx + 1, head_cy + 4), 1)
    # Mund — geoeffnet, mit verfaulten Zaehnen
    pygame.draw.rect(surf, OL,
                      (head_cx - 4, head_cy + 5, 8, 4))
    # Zaehne (Stumpfe)
    for tx in (-3, -1, 1, 3):
        pygame.draw.line(surf, bone,
                          (head_cx + tx, head_cy + 5),
                          (head_cx + tx, head_cy + 7), 1)
    # Sabber/Blut am Mund
    pygame.draw.line(surf, blood,
                      (head_cx + 1, head_cy + 9),
                      (head_cx + 2, head_cy + 12), 1)

    # Haar-Stoppeln (sparse, zerzaust)
    for hx, hy in ((head_cx - 5, head_cy - 8),
                    (head_cx - 1, head_cy - 9),
                    (head_cx + 3, head_cy - 8),
                    (head_cx + 6, head_cy - 7)):
        pygame.draw.line(surf, OL,
                          (hx, hy), (hx, hy + 3), 1)

    return surf


def _gen_demon_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #202: Detail-Demon auf 84x124-Canvas.

    Hellspawn — rote Haut, Hoerner, Klauen, Schwanz, gluehende Augen,
    dunkles Plate-Stueckwerk. Klar als Demon lesbar.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    skin        = (148, 32, 38)
    skin_lt     = (200, 60, 64)
    skin_sh     = (98, 22, 28)
    skin_blk    = (62, 14, 20)
    horn        = (30, 20, 22)
    horn_lt     = (88, 60, 60)
    plate       = (38, 28, 28)
    plate_lt    = (78, 60, 60)
    plate_dk    = (16, 12, 14)
    metal       = (122, 88, 52)
    metal_lt    = (172, 132, 78)
    fire        = (255, 180, 60)
    fire_dk     = (200, 100, 30)
    claw        = (210, 200, 180)
    OL          = (6, 4, 6)

    if walk_frame == 1:
        l_dy, r_dy = -2, 1
        arm_swing = -2
    elif walk_frame == 3:
        l_dy, r_dy = 1, -2
        arm_swing = 2
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0

    # ============================================================
    # TAIL — vor dem Body, hinten haengt der Schwanz
    # ============================================================
    tail_pts = [
        (cx + 2, fy - 36),
        (cx + 16, fy - 32),
        (cx + 22, fy - 24),
        (cx + 24, fy - 14),
        (cx + 20, fy - 16),
        (cx + 18, fy - 22),
        (cx + 10, fy - 28),
        (cx + 2, fy - 32),
    ]
    pygame.draw.polygon(surf, skin, tail_pts)
    pygame.draw.polygon(surf, OL, tail_pts, 1)
    # Schwanz-Spitze (Stachel)
    pygame.draw.polygon(surf, claw, [
        (cx + 24, fy - 14),
        (cx + 28, fy - 18),
        (cx + 26, fy - 10),
    ])
    pygame.draw.polygon(surf, OL, [
        (cx + 24, fy - 14),
        (cx + 28, fy - 18),
        (cx + 26, fy - 10),
    ], 1)

    # ============================================================
    # LEGS — Demonen-Hufe / klauenfuesse
    # ============================================================
    # Linker Klauenfuss
    foot_l_pts = [
        (cx - 13, fy - 4 + l_dy),
        (cx - 8, fy - 7 + l_dy),
        (cx - 3, fy - 4 + l_dy),
        (cx - 4, fy + l_dy),
        (cx - 12, fy + l_dy),
    ]
    pygame.draw.polygon(surf, skin_sh, foot_l_pts)
    pygame.draw.polygon(surf, OL, foot_l_pts, 1)
    # Klauen
    for cx_, cy_ in ((cx - 12, fy + l_dy), (cx - 8, fy + l_dy), (cx - 4, fy + l_dy)):
        pygame.draw.polygon(surf, claw, [
            (cx_, cy_), (cx_ + 2, cy_ + 2), (cx_ + 1, cy_ - 1),
        ])
        pygame.draw.polygon(surf, OL, [
            (cx_, cy_), (cx_ + 2, cy_ + 2), (cx_ + 1, cy_ - 1),
        ], 1)
    # Linkes Bein
    leg_l = pygame.Rect(cx - 11, fy - 22 + l_dy, 8, 16)
    pygame.draw.rect(surf, skin, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Knie-Plate (kleines Iron-Cap)
    pygame.draw.circle(surf, plate, (leg_l.centerx, leg_l.y + 4), 3)
    pygame.draw.circle(surf, OL, (leg_l.centerx, leg_l.y + 4), 3, 1)

    # Rechter Klauenfuss + Bein
    foot_r_pts = [
        (cx + 3, fy - 4 + r_dy),
        (cx + 8, fy - 7 + r_dy),
        (cx + 13, fy - 4 + r_dy),
        (cx + 12, fy + r_dy),
        (cx + 4, fy + r_dy),
    ]
    pygame.draw.polygon(surf, skin_sh, foot_r_pts)
    pygame.draw.polygon(surf, OL, foot_r_pts, 1)
    for cx_, cy_ in ((cx + 4, fy + r_dy), (cx + 8, fy + r_dy), (cx + 12, fy + r_dy)):
        pygame.draw.polygon(surf, claw, [
            (cx_, cy_), (cx_ + 2, cy_ + 2), (cx_ + 1, cy_ - 1),
        ])
        pygame.draw.polygon(surf, OL, [
            (cx_, cy_), (cx_ + 2, cy_ + 2), (cx_ + 1, cy_ - 1),
        ], 1)
    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 8, 16)
    pygame.draw.rect(surf, skin, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    pygame.draw.circle(surf, plate, (leg_r.centerx, leg_r.y + 4), 3)
    pygame.draw.circle(surf, OL, (leg_r.centerx, leg_r.y + 4), 3, 1)

    # ============================================================
    # LOINCLOTH — schwarzer Stoff um die Hueften
    # ============================================================
    loin_pts = [
        (cx - 14, fy - 32),
        (cx + 14, fy - 32),
        (cx + 16, fy - 24),
        (cx + 8, fy - 18),
        (cx + 2, fy - 24),
        (cx - 2, fy - 24),
        (cx - 8, fy - 18),
        (cx - 16, fy - 24),
    ]
    pygame.draw.polygon(surf, plate_dk, loin_pts)
    pygame.draw.polygon(surf, OL, loin_pts, 2)
    # Metal-Trim
    pygame.draw.line(surf, metal, (cx - 14, fy - 31),
                      (cx + 14, fy - 31), 1)
    pygame.draw.line(surf, metal_lt, (cx - 12, fy - 31),
                      (cx + 12, fy - 31), 1)
    # Skull-Buckle in der Mitte
    pygame.draw.circle(surf, metal, (cx, fy - 29), 3)
    pygame.draw.circle(surf, OL, (cx, fy - 29), 3, 1)
    # Eye-sockets im Buckle
    pygame.draw.circle(surf, OL, (cx - 1, fy - 30), 1)
    pygame.draw.circle(surf, OL, (cx + 1, fy - 30), 1)

    # ============================================================
    # TORSO — muskuloese Brust
    # ============================================================
    torso_top = fy - 64
    torso_bot = fy - 32
    torso_pts = [
        (cx - 12, torso_top + 4),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 12, torso_top + 4),
        (cx + 17, torso_top + 14),
        (cx + 16, torso_bot),
        (cx - 16, torso_bot),
        (cx - 17, torso_top + 14),
    ]
    pygame.draw.polygon(surf, skin, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brust-Definition (Muskel-Linien)
    pygame.draw.line(surf, skin_sh,
                      (cx - 8, torso_top + 4),
                      (cx, torso_top + 8), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx + 8, torso_top + 4),
                      (cx, torso_top + 8), 1)
    # Bauch-Muskeln (6-Pack)
    for by in (torso_top + 12, torso_top + 18, torso_top + 24):
        pygame.draw.line(surf, skin_sh,
                          (cx - 6, by), (cx + 6, by), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx, torso_top + 10),
                      (cx, torso_top + 28), 1)
    # Highlight links (Light-Source)
    pygame.draw.polygon(surf, skin_lt, [
        (cx - 9, torso_top + 3),
        (cx - 4, torso_top + 4),
        (cx - 6, torso_top + 16),
        (cx - 13, torso_top + 14),
    ])
    # Narben (Hellraiser-Style)
    pygame.draw.line(surf, skin_blk,
                      (cx + 4, torso_top + 6),
                      (cx + 8, torso_top + 12), 1)
    pygame.draw.line(surf, skin_blk,
                      (cx - 5, torso_top + 20),
                      (cx + 2, torso_top + 22), 1)

    # ============================================================
    # PAULDRONS — dunkles Iron-Plate mit Spikes
    # ============================================================
    # Linke Pauldron mit Spikes
    pl_l_pts = [
        (cx - 18, torso_top + 8),
        (cx - 14, torso_top - 1),
        (cx - 8, torso_top + 2),
        (cx - 10, torso_top + 12),
    ]
    pygame.draw.polygon(surf, plate, pl_l_pts)
    pygame.draw.polygon(surf, OL, pl_l_pts, 1)
    pygame.draw.line(surf, plate_lt,
                      (cx - 17, torso_top + 6),
                      (cx - 14, torso_top), 1)
    # Spikes
    pygame.draw.polygon(surf, plate, [
        (cx - 15, torso_top - 2), (cx - 13, torso_top - 6),
        (cx - 11, torso_top - 2),
    ])
    pygame.draw.polygon(surf, OL, [
        (cx - 15, torso_top - 2), (cx - 13, torso_top - 6),
        (cx - 11, torso_top - 2),
    ], 1)

    # Rechte Pauldron
    pl_r_pts = [
        (cx + 8, torso_top + 2),
        (cx + 14, torso_top - 1),
        (cx + 18, torso_top + 8),
        (cx + 10, torso_top + 12),
    ]
    pygame.draw.polygon(surf, plate, pl_r_pts)
    pygame.draw.polygon(surf, OL, pl_r_pts, 1)
    pygame.draw.polygon(surf, plate, [
        (cx + 11, torso_top - 2), (cx + 13, torso_top - 6),
        (cx + 15, torso_top - 2),
    ])
    pygame.draw.polygon(surf, OL, [
        (cx + 11, torso_top - 2), (cx + 13, torso_top - 6),
        (cx + 15, torso_top - 2),
    ], 1)

    # ============================================================
    # ARMS — muskuloese, mit Klauen
    # ============================================================
    arm_top = torso_top + 8
    # Linker Arm
    arm_l = pygame.Rect(cx - 19, arm_top + arm_swing, 6, 14)
    pygame.draw.rect(surf, skin, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Iron-Bracer
    pygame.draw.rect(surf, plate,
                      (arm_l.x - 1, arm_l.bottom - 4, 8, 4))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 4, 8, 4), 1)
    # Hand mit Klauen
    pygame.draw.rect(surf, skin, (arm_l.x, arm_l.bottom, 6, 4))
    pygame.draw.rect(surf, OL, (arm_l.x, arm_l.bottom, 6, 4), 1)
    # 3 Klauen-Spitzen
    for cx_ in (arm_l.x + 1, arm_l.x + 3, arm_l.x + 5):
        pygame.draw.line(surf, claw,
                          (cx_, arm_l.bottom + 4),
                          (cx_, arm_l.bottom + 6), 1)
        pygame.draw.line(surf, OL,
                          (cx_, arm_l.bottom + 4),
                          (cx_, arm_l.bottom + 6), 1)

    # Rechter Arm
    arm_r = pygame.Rect(cx + 13, arm_top - arm_swing, 6, 14)
    pygame.draw.rect(surf, skin, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, plate,
                      (arm_r.x, arm_r.bottom - 4, 8, 4))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 4, 8, 4), 1)
    pygame.draw.rect(surf, skin, (arm_r.x + 1, arm_r.bottom, 6, 4))
    pygame.draw.rect(surf, OL, (arm_r.x + 1, arm_r.bottom, 6, 4), 1)
    for cx_ in (arm_r.x + 2, arm_r.x + 4, arm_r.x + 6):
        pygame.draw.line(surf, claw,
                          (cx_, arm_r.bottom + 4),
                          (cx_, arm_r.bottom + 6), 1)
        pygame.draw.line(surf, OL,
                          (cx_, arm_r.bottom + 4),
                          (cx_, arm_r.bottom + 6), 1)

    # ============================================================
    # NECK + HEAD — demonisches Antlitz
    # ============================================================
    # Neck
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 4, 6, 5))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 4, 2, 5))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 4, 6, 5), 1)

    head_cx = cx
    head_cy = torso_top - 11
    # Schaedel — schmal, kantig
    head_pts = [
        (head_cx - 8, head_cy + 7),
        (head_cx - 9, head_cy + 2),
        (head_cx - 8, head_cy - 4),
        (head_cx - 5, head_cy - 9),
        (head_cx + 5, head_cy - 9),
        (head_cx + 8, head_cy - 4),
        (head_cx + 9, head_cy + 2),
        (head_cx + 8, head_cy + 7),
        (head_cx + 4, head_cy + 9),
        (head_cx - 4, head_cy + 9),
    ]
    pygame.draw.polygon(surf, skin, head_pts)
    pygame.draw.polygon(surf, OL, head_pts, 2)
    # Stirn-Highlight
    pygame.draw.polygon(surf, skin_lt, [
        (head_cx - 6, head_cy - 7),
        (head_cx - 1, head_cy - 8),
        (head_cx - 3, head_cy - 4),
        (head_cx - 7, head_cy - 3),
    ])
    # Wangenknochen
    pygame.draw.line(surf, skin_sh,
                      (head_cx - 8, head_cy + 2),
                      (head_cx - 5, head_cy + 5), 1)
    pygame.draw.line(surf, skin_sh,
                      (head_cx + 8, head_cy + 2),
                      (head_cx + 5, head_cy + 5), 1)
    # Augen — gluehend
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 2)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 2)
    pygame.draw.circle(surf, fire, (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, fire, (head_cx + 3, head_cy - 1), 1)
    # Augenglow
    glow = pygame.Surface((10, 6), pygame.SRCALPHA)
    pygame.draw.ellipse(glow, (*fire, 100), (0, 0, 10, 6))
    surf.blit(glow, (head_cx - 8, head_cy - 4))
    surf.blit(glow, (head_cx - 2, head_cy - 4))
    # Augenbrauen (steil, boese)
    pygame.draw.line(surf, OL,
                      (head_cx - 6, head_cy - 4),
                      (head_cx - 1, head_cy - 2), 2)
    pygame.draw.line(surf, OL,
                      (head_cx + 1, head_cy - 2),
                      (head_cx + 6, head_cy - 4), 2)
    # Nase — schmal, scharf
    pygame.draw.polygon(surf, skin_sh, [
        (head_cx, head_cy + 1),
        (head_cx + 1, head_cy + 4),
        (head_cx - 1, head_cy + 4),
    ])
    # Mund — knurrend, mit Fangzaehnen
    pygame.draw.line(surf, OL,
                      (head_cx - 4, head_cy + 5),
                      (head_cx + 4, head_cy + 5), 2)
    # Fangzaehne
    pygame.draw.polygon(surf, claw, [
        (head_cx - 3, head_cy + 5),
        (head_cx - 2, head_cy + 7),
        (head_cx - 4, head_cy + 7),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx - 3, head_cy + 5),
        (head_cx - 2, head_cy + 7),
        (head_cx - 4, head_cy + 7),
    ], 1)
    pygame.draw.polygon(surf, claw, [
        (head_cx + 3, head_cy + 5),
        (head_cx + 4, head_cy + 7),
        (head_cx + 2, head_cy + 7),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx + 3, head_cy + 5),
        (head_cx + 4, head_cy + 7),
        (head_cx + 2, head_cy + 7),
    ], 1)

    # ============================================================
    # HORNS — die ikonischen Demonen-Hoerner
    # ============================================================
    # Linkes Horn
    horn_l_pts = [
        (head_cx - 6, head_cy - 8),
        (head_cx - 4, head_cy - 7),
        (head_cx - 8, head_cy - 16),
        (head_cx - 10, head_cy - 18),
    ]
    pygame.draw.polygon(surf, horn, horn_l_pts)
    pygame.draw.polygon(surf, OL, horn_l_pts, 1)
    pygame.draw.line(surf, horn_lt,
                      (head_cx - 7, head_cy - 9),
                      (head_cx - 9, head_cy - 16), 1)
    # Rechtes Horn
    horn_r_pts = [
        (head_cx + 4, head_cy - 7),
        (head_cx + 6, head_cy - 8),
        (head_cx + 10, head_cy - 18),
        (head_cx + 8, head_cy - 16),
    ]
    pygame.draw.polygon(surf, horn, horn_r_pts)
    pygame.draw.polygon(surf, OL, horn_r_pts, 1)
    pygame.draw.line(surf, horn_lt,
                      (head_cx + 7, head_cy - 9),
                      (head_cx + 9, head_cy - 16), 1)

    return surf


def _gen_brute_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #202: Detail-Brute auf 84x124-Canvas.

    Heavy-Enemy — muskuloeser Bulk, schwere Mace, vernarbte Haut,
    zerlumpte Hose, breite Schultern. Klar als Brute lesbar.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    skin        = (172, 132, 102)
    skin_lt     = (218, 178, 142)
    skin_sh     = (122, 92, 68)
    skin_blk    = (78, 58, 42)
    scar        = (88, 30, 32)
    cloth       = (52, 38, 28)
    cloth_lt    = (88, 64, 42)
    metal       = (108, 100, 90)
    metal_lt    = (162, 152, 138)
    metal_dk    = (60, 56, 50)
    leather     = (62, 42, 28)
    leather_lt  = (108, 78, 50)
    blood       = (122, 38, 36)
    OL          = (8, 6, 8)

    if walk_frame == 1:
        l_dy, r_dy = -3, 1
        shoulder_lean = -2
    elif walk_frame == 3:
        l_dy, r_dy = 1, -3
        shoulder_lean = 2
    else:
        l_dy, r_dy = 0, 0
        shoulder_lean = 0

    # ============================================================
    # LEGS — riesige Stiefel + Hose
    # ============================================================
    # Linker Schwer-Stiefel
    boot_l = pygame.Rect(cx - 14, fy - 7 + l_dy, 12, 7)
    pygame.draw.rect(surf, leather, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_l.x + 1, boot_l.y + 1),
                      (boot_l.right - 2, boot_l.y + 1), 1)
    # Metall-Beschlaege
    pygame.draw.line(surf, metal,
                      (boot_l.x, boot_l.y + 4),
                      (boot_l.right, boot_l.y + 4), 1)
    # Hose
    leg_l = pygame.Rect(cx - 13, fy - 24 + l_dy, 10, 17)
    pygame.draw.rect(surf, cloth, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, cloth_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Riss in der Hose
    pygame.draw.line(surf, skin,
                      (leg_l.right - 2, leg_l.y + 8),
                      (leg_l.right - 2, leg_l.y + 14), 2)

    # Rechter
    boot_r = pygame.Rect(cx + 2, fy - 7 + r_dy, 12, 7)
    pygame.draw.rect(surf, leather, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_r.x + 1, boot_r.y + 1),
                      (boot_r.right - 2, boot_r.y + 1), 1)
    pygame.draw.line(surf, metal,
                      (boot_r.x, boot_r.y + 4),
                      (boot_r.right, boot_r.y + 4), 1)
    leg_r = pygame.Rect(cx + 3, fy - 24 + r_dy, 10, 17)
    pygame.draw.rect(surf, cloth, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, cloth_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)

    # Belt
    belt_y = fy - 36
    pygame.draw.rect(surf, leather, (cx - 18, belt_y, 36, 6))
    pygame.draw.rect(surf, OL, (cx - 18, belt_y, 36, 6), 1)
    # Big Buckle
    pygame.draw.rect(surf, metal, (cx - 5, belt_y - 1, 10, 8))
    pygame.draw.rect(surf, OL, (cx - 5, belt_y - 1, 10, 8), 1)
    pygame.draw.line(surf, metal_lt,
                      (cx - 4, belt_y),
                      (cx - 4, belt_y + 6), 1)

    # ============================================================
    # TORSO — RIESIG, muskuloes
    # ============================================================
    torso_top = fy - 70
    torso_bot = fy - 36
    # Breite Brust
    torso_pts = [
        (cx - 18, torso_top + 4),
        (cx - 15, torso_top),
        (cx + 15, torso_top),
        (cx + 18, torso_top + 4),
        (cx + 22, torso_top + 16),
        (cx + 20, torso_bot),
        (cx - 20, torso_bot),
        (cx - 22, torso_top + 16),
    ]
    pygame.draw.polygon(surf, skin, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brust-Muskulatur
    pygame.draw.line(surf, skin_sh,
                      (cx - 12, torso_top + 4),
                      (cx, torso_top + 10), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx + 12, torso_top + 4),
                      (cx, torso_top + 10), 1)
    # 6-Pack
    for by in (torso_top + 14, torso_top + 22, torso_top + 28):
        pygame.draw.line(surf, skin_sh,
                          (cx - 9, by), (cx + 9, by), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx, torso_top + 12),
                      (cx, torso_top + 32), 1)
    # Big Highlight (light source upper-left)
    pygame.draw.polygon(surf, skin_lt, [
        (cx - 14, torso_top + 3),
        (cx - 6, torso_top + 5),
        (cx - 9, torso_top + 18),
        (cx - 18, torso_top + 16),
    ])
    # Brustnarben (mehrere)
    pygame.draw.line(surf, scar,
                      (cx + 4, torso_top + 6),
                      (cx + 12, torso_top + 14), 2)
    pygame.draw.line(surf, skin_blk,
                      (cx + 4, torso_top + 6),
                      (cx + 12, torso_top + 14), 1)
    pygame.draw.line(surf, scar,
                      (cx - 8, torso_top + 22),
                      (cx - 2, torso_top + 26), 1)
    # Brand-Mal (rotes Sigil)
    pygame.draw.circle(surf, blood, (cx + 10, torso_top + 24), 2)
    pygame.draw.line(surf, OL,
                      (cx + 9, torso_top + 23),
                      (cx + 11, torso_top + 25), 1)

    # ============================================================
    # PAULDRONS — riesige Schulter-Plates mit Spikes
    # ============================================================
    # Linke (groesser)
    pl_l_pts = [
        (cx - 22, torso_top + 8),
        (cx - 18, torso_top - 2),
        (cx - 10, torso_top + 2),
        (cx - 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, metal, pl_l_pts)
    pygame.draw.polygon(surf, OL, pl_l_pts, 2)
    pygame.draw.line(surf, metal_lt,
                      (cx - 21, torso_top + 6),
                      (cx - 17, torso_top), 1)
    # 3 Spikes
    for spike_x in (cx - 19, cx - 16, cx - 13):
        pygame.draw.polygon(surf, metal_dk, [
            (spike_x, torso_top - 3),
            (spike_x + 2, torso_top - 9),
            (spike_x + 3, torso_top - 3),
        ])
        pygame.draw.polygon(surf, OL, [
            (spike_x, torso_top - 3),
            (spike_x + 2, torso_top - 9),
            (spike_x + 3, torso_top - 3),
        ], 1)

    # Rechte
    pl_r_pts = [
        (cx + 10, torso_top + 2),
        (cx + 18, torso_top - 2),
        (cx + 22, torso_top + 8),
        (cx + 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, metal_dk, pl_r_pts)
    pygame.draw.polygon(surf, OL, pl_r_pts, 2)
    for spike_x in (cx + 13, cx + 16, cx + 19):
        pygame.draw.polygon(surf, metal_dk, [
            (spike_x, torso_top - 3),
            (spike_x + 2, torso_top - 9),
            (spike_x + 3, torso_top - 3),
        ])
        pygame.draw.polygon(surf, OL, [
            (spike_x, torso_top - 3),
            (spike_x + 2, torso_top - 9),
            (spike_x + 3, torso_top - 3),
        ], 1)

    # ============================================================
    # ARMS — riesige Muskel-Arme
    # ============================================================
    arm_top = torso_top + 10
    # Linker Arm
    arm_l = pygame.Rect(cx - 22, arm_top + shoulder_lean, 7, 18)
    pygame.draw.rect(surf, skin, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Bizeps-Definition
    pygame.draw.arc(surf, skin_sh,
                     (arm_l.x, arm_l.y + 4, arm_l.width, 10),
                     math.pi, 2 * math.pi, 1)
    # Bracer (Stoff-Wrap)
    pygame.draw.rect(surf, cloth,
                      (arm_l.x - 1, arm_l.bottom - 5, 9, 5))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 5, 9, 5), 1)
    # Faust (riesig)
    pygame.draw.circle(surf, skin,
                        (arm_l.centerx - 1, arm_l.bottom + 3), 4)
    pygame.draw.circle(surf, OL,
                        (arm_l.centerx - 1, arm_l.bottom + 3), 4, 1)

    # Rechter Arm
    arm_r = pygame.Rect(cx + 15, arm_top - shoulder_lean, 7, 18)
    pygame.draw.rect(surf, skin, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.arc(surf, skin_sh,
                     (arm_r.x, arm_r.y + 4, arm_r.width, 10),
                     math.pi, 2 * math.pi, 1)
    pygame.draw.rect(surf, cloth,
                      (arm_r.x, arm_r.bottom - 5, 9, 5))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 5, 9, 5), 1)
    # Faust haelt Mace
    pygame.draw.circle(surf, skin,
                        (arm_r.centerx + 1, arm_r.bottom + 3), 4)
    pygame.draw.circle(surf, OL,
                        (arm_r.centerx + 1, arm_r.bottom + 3), 4, 1)

    # ============================================================
    # MACE — riesige Schlachtkeule rechts
    # ============================================================
    mace_x = cx + 23
    mace_grip_y = arm_top + 18 - shoulder_lean
    # Grip (Holz)
    pygame.draw.rect(surf, leather,
                      (mace_x - 1, mace_grip_y - 4, 3, 12))
    pygame.draw.rect(surf, OL,
                      (mace_x - 1, mace_grip_y - 4, 3, 12), 1)
    for gy in (mace_grip_y - 2, mace_grip_y + 1, mace_grip_y + 4):
        pygame.draw.line(surf, OL,
                          (mace_x - 1, gy),
                          (mace_x + 2, gy), 1)
    # Mace-Kopf (sternartig, mit Spikes)
    mace_top_y = mace_grip_y - 22
    pygame.draw.circle(surf, metal, (mace_x, mace_top_y), 7)
    pygame.draw.circle(surf, OL, (mace_x, mace_top_y), 7, 2)
    pygame.draw.circle(surf, metal_lt, (mace_x - 2, mace_top_y - 2), 2)
    # Spikes rund herum
    for ang in (0, math.pi / 4, math.pi / 2, 3 * math.pi / 4,
                math.pi, 5 * math.pi / 4, 3 * math.pi / 2, 7 * math.pi / 4):
        tip_x = mace_x + math.cos(ang) * 10
        tip_y = mace_top_y + math.sin(ang) * 10
        base_x = mace_x + math.cos(ang) * 6
        base_y = mace_top_y + math.sin(ang) * 6
        # Spike-Polygon
        perp = ang + math.pi / 2
        b1_x = base_x + math.cos(perp) * 2
        b1_y = base_y + math.sin(perp) * 2
        b2_x = base_x - math.cos(perp) * 2
        b2_y = base_y - math.sin(perp) * 2
        pygame.draw.polygon(surf, metal_dk, [
            (b1_x, b1_y), (tip_x, tip_y), (b2_x, b2_y),
        ])
        pygame.draw.polygon(surf, OL, [
            (b1_x, b1_y), (tip_x, tip_y), (b2_x, b2_y),
        ], 1)
    # Blut am Mace-Kopf
    pygame.draw.circle(surf, blood,
                        (mace_x - 1, mace_top_y + 2), 1)
    pygame.draw.line(surf, blood,
                      (mace_x - 1, mace_top_y + 3),
                      (mace_x - 2, mace_top_y + 6), 1)

    # ============================================================
    # NECK + HEAD — kahler Schaedel, vernarbt
    # ============================================================
    # Neck (kurz, dick)
    pygame.draw.rect(surf, skin, (cx - 5, torso_top - 5, 10, 6))
    pygame.draw.rect(surf, OL, (cx - 5, torso_top - 5, 10, 6), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx - 4, torso_top - 4),
                      (cx + 4, torso_top - 4), 1)

    head_cx = cx
    head_cy = torso_top - 12
    # Schaedel (rund, kantig)
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
    pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 8)
    pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 7)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 2)
    # Highlight (kahl + glaenzend)
    pygame.draw.circle(surf, skin_lt, (head_cx - 3, head_cy - 5), 3)
    # Glatze-Glanz
    pygame.draw.circle(surf, (240, 200, 168), (head_cx - 2, head_cy - 6), 1)
    # Narben am Kopf
    pygame.draw.line(surf, scar,
                      (head_cx - 6, head_cy - 6),
                      (head_cx - 2, head_cy - 8), 2)
    pygame.draw.line(surf, skin_blk,
                      (head_cx - 6, head_cy - 6),
                      (head_cx - 2, head_cy - 8), 1)
    pygame.draw.line(surf, scar,
                      (head_cx + 3, head_cy + 4),
                      (head_cx + 6, head_cy + 1), 1)
    # Augen — wild, blutunterlaufen
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 2)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 2)
    pygame.draw.circle(surf, (200, 60, 60),
                        (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, (200, 60, 60),
                        (head_cx + 3, head_cy - 1), 1)
    pygame.draw.circle(surf, glow_col, (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, glow_col, (head_cx + 3, head_cy - 1), 1)
    # Augenringe (rot, gereizt)
    pygame.draw.arc(surf, scar,
                     (head_cx - 6, head_cy, 6, 4),
                     0, math.pi, 1)
    pygame.draw.arc(surf, scar,
                     (head_cx, head_cy, 6, 4),
                     0, math.pi, 1)
    # Buschige Augenbrauen
    pygame.draw.line(surf, OL,
                      (head_cx - 6, head_cy - 4),
                      (head_cx - 1, head_cy - 3), 2)
    pygame.draw.line(surf, OL,
                      (head_cx + 1, head_cy - 3),
                      (head_cx + 6, head_cy - 4), 2)
    # Nase — gebrochen (Boxer)
    pygame.draw.polygon(surf, skin_sh, [
        (head_cx, head_cy + 1),
        (head_cx + 2, head_cy + 4),
        (head_cx - 2, head_cy + 4),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx, head_cy + 1),
        (head_cx + 2, head_cy + 4),
        (head_cx - 2, head_cy + 4),
    ], 1)
    # Schief-Linie (gebrochen)
    pygame.draw.line(surf, OL,
                      (head_cx, head_cy + 2),
                      (head_cx + 1, head_cy + 3), 1)
    # Mund — grimmig
    pygame.draw.line(surf, OL,
                      (head_cx - 3, head_cy + 5),
                      (head_cx + 3, head_cy + 5), 2)
    # Spitzen-Bart
    pygame.draw.polygon(surf, OL, [
        (head_cx - 2, head_cy + 6),
        (head_cx + 2, head_cy + 6),
        (head_cx, head_cy + 9),
    ])

    return surf


def _get_mob_sprite(type_key: str, color, glow_col, walk_frame: int) -> pygame.Surface | None:
    """Cache-Wrapper fuer Detail-Mob-Sprites (Update #202).

    Returnt None wenn `type_key` keinen Detail-Generator hat — Caller
    soll dann auf den scaled-Iso-Drawer-Pfad fallen.
    """
    gen = _MOB_DETAIL_GENERATORS.get(type_key)
    if gen is None:
        return None
    key = (type_key, tuple(color), tuple(glow_col), walk_frame)
    cached = _MOB_SPRITE_CACHE.get(key)
    if cached is None:
        cached = gen(color, glow_col, walk_frame)
        if len(_MOB_SPRITE_CACHE) > 256:
            _MOB_SPRITE_CACHE.clear()
        _MOB_SPRITE_CACHE[key] = cached
    return cached


def _gen_wraith_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #203: Detail-Wraith — Geist/Spectre, translucent, floats.

    Kein solides Bein, Body fadet in Mist; gluehende Eye-Sockets;
    zerfetzte Schroud; Klaue-Haende; spektrale Tendrils.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # Wraith-Palette (kalt, halbtransparent)
    shroud      = (62, 60, 88)
    shroud_lt   = (108, 108, 142)
    shroud_dk   = (28, 26, 42)
    mist        = (148, 158, 200)
    mist_dk     = (62, 70, 102)
    bone_pale   = (208, 210, 220)
    bone_pale_lt= (240, 240, 248)
    eye         = glow_col
    OL          = (8, 8, 14)
    OL_soft     = (28, 28, 44)

    # Float-Bob: Wraith schwebt — Y-Offset statt Walk
    if walk_frame == 1:
        float_dy = -2
        sway = -1
    elif walk_frame == 3:
        float_dy = -2
        sway = 1
    else:
        float_dy = 0
        sway = 0

    # ============================================================
    # MIST-BASE — am Boden fadet die Erscheinung in Nebel
    # ============================================================
    # Nebel-Wolke unten (mehrere uebereinandergelegte Ellipsen)
    for r_, a_ in ((22, 35), (18, 60), (14, 100), (10, 140)):
        mist_l = pygame.Surface((r_ * 2, r_ // 2 + 4), pygame.SRCALPHA)
        pygame.draw.ellipse(mist_l, (*mist, a_),
                             (0, 0, r_ * 2, r_ // 2 + 4))
        surf.blit(mist_l, (cx - r_, fy - r_ // 4 - 2))

    # Tendrils — schwingende Mist-Faeden nach unten
    for tx in (-12, -4, 6, 14):
        for ty_ in range(-2, 10, 3):
            alpha = 100 - ty_ * 8
            if alpha <= 0:
                continue
            t_surf = pygame.Surface((4, 4), pygame.SRCALPHA)
            pygame.draw.circle(t_surf, (*mist, alpha), (2, 2), 2)
            surf.blit(t_surf,
                       (cx + tx + sway, fy - 12 + ty_))

    # ============================================================
    # LOWER-SHROUD — zerfetzte Robe-Unterteil, transparent
    # ============================================================
    shroud_top = fy - 64 + float_dy
    shroud_bot = fy - 18
    # Polygon mit ausgefranstem Saum
    shroud_pts = [
        (cx - 16, shroud_top + 8),
        (cx + 16, shroud_top + 8),
        (cx + 20, shroud_top + 18),
        (cx + 22, shroud_bot - 12),
        (cx + 18, shroud_bot - 4),
        (cx + 12, shroud_bot - 8),
        (cx + 6, shroud_bot - 2),
        (cx, shroud_bot - 6),
        (cx - 6, shroud_bot - 2),
        (cx - 12, shroud_bot - 8),
        (cx - 18, shroud_bot - 4),
        (cx - 22, shroud_bot - 12),
        (cx - 20, shroud_top + 18),
    ]
    # Render auf Alpha-Surface fuer Translucenz
    shroud_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(shroud_layer, (*shroud, 200), shroud_pts)
    pygame.draw.polygon(shroud_layer, (*OL_soft, 220), shroud_pts, 2)
    # Falten (vertikal)
    for fx_ in (cx - 12, cx - 4, cx + 4 + sway, cx + 12):
        pygame.draw.line(shroud_layer, (*shroud_dk, 180),
                          (fx_, shroud_top + 10),
                          (fx_ + sway, shroud_bot - 10), 1)
    surf.blit(shroud_layer, (0, 0))

    # ============================================================
    # TORSO — schmales spektrales Bust
    # ============================================================
    torso_top = fy - 70 + float_dy
    torso_bot = fy - 50 + float_dy
    torso_pts = [
        (cx - 10, torso_top + 2),
        (cx - 8, torso_top),
        (cx + 8, torso_top),
        (cx + 10, torso_top + 2),
        (cx + 14, torso_top + 12),
        (cx + 16, torso_bot),
        (cx - 16, torso_bot),
        (cx - 14, torso_top + 12),
    ]
    body_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(body_layer, (*shroud, 220), torso_pts)
    pygame.draw.polygon(body_layer, (*OL_soft, 230), torso_pts, 2)
    # Brust-Highlight
    pygame.draw.polygon(body_layer, (*shroud_lt, 180), [
        (cx - 7, torso_top + 2),
        (cx - 2, torso_top + 3),
        (cx - 4, torso_top + 12),
        (cx - 12, torso_top + 10),
    ])
    surf.blit(body_layer, (0, 0))

    # ============================================================
    # ARMS — gespenstische Klauen-Arme
    # ============================================================
    arm_top = torso_top + 6
    # Linker Arm — ausgestreckt
    arm_l_pts = [
        (cx - 16, arm_top + sway),
        (cx - 12, arm_top + sway),
        (cx - 14, arm_top + 14 + sway),
        (cx - 19, arm_top + 16 + sway),
    ]
    arm_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.polygon(arm_layer, (*shroud, 200), arm_l_pts)
    pygame.draw.polygon(arm_layer, (*OL_soft, 220), arm_l_pts, 1)
    # Klauen-Hand
    pygame.draw.circle(arm_layer, (*bone_pale, 230),
                        (cx - 18, arm_top + 18 + sway), 3)
    pygame.draw.circle(arm_layer, OL, (cx - 18, arm_top + 18 + sway), 3, 1)
    # Klauen-Finger (lang, krumm)
    for fx_, fy_ in ((-2, 4), (-1, 5), (0, 5), (1, 4)):
        pygame.draw.line(arm_layer, bone_pale,
                          (cx - 18 + fx_, arm_top + 18 + sway),
                          (cx - 19 + fx_, arm_top + 18 + sway + fy_), 1)

    # Rechter Arm — auch ausgestreckt
    arm_r_pts = [
        (cx + 12, arm_top - sway),
        (cx + 16, arm_top - sway),
        (cx + 19, arm_top + 16 - sway),
        (cx + 14, arm_top + 14 - sway),
    ]
    pygame.draw.polygon(arm_layer, (*shroud, 200), arm_r_pts)
    pygame.draw.polygon(arm_layer, (*OL_soft, 220), arm_r_pts, 1)
    pygame.draw.circle(arm_layer, (*bone_pale, 230),
                        (cx + 18, arm_top + 18 - sway), 3)
    pygame.draw.circle(arm_layer, OL, (cx + 18, arm_top + 18 - sway), 3, 1)
    for fx_, fy_ in ((-1, 4), (0, 5), (1, 5), (2, 4)):
        pygame.draw.line(arm_layer, bone_pale,
                          (cx + 18 + fx_, arm_top + 18 - sway),
                          (cx + 19 + fx_, arm_top + 18 - sway + fy_), 1)
    surf.blit(arm_layer, (0, 0))

    # ============================================================
    # HEAD — spektrale Schaedel-Maske unter Hood
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 11
    head_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    # Hood-Cowl
    hood_pts = [
        (head_cx - 12, head_cy + 6),
        (head_cx - 13, head_cy - 4),
        (head_cx - 9, head_cy - 11),
        (head_cx - 2, head_cy - 13),
        (head_cx + 2, head_cy - 13),
        (head_cx + 9, head_cy - 11),
        (head_cx + 13, head_cy - 4),
        (head_cx + 12, head_cy + 6),
        # Innere Gesichts-Oeffnung
        (head_cx + 8, head_cy + 4),
        (head_cx + 7, head_cy - 4),
        (head_cx + 2, head_cy - 8),
        (head_cx - 2, head_cy - 8),
        (head_cx - 7, head_cy - 4),
        (head_cx - 8, head_cy + 4),
    ]
    pygame.draw.polygon(head_layer, (*shroud_dk, 235), hood_pts)
    pygame.draw.polygon(head_layer, OL, hood_pts, 2)
    # Inside the Hood — Schwarz (Void)
    void_pts = [
        (head_cx + 7, head_cy + 4),
        (head_cx + 6, head_cy - 4),
        (head_cx + 2, head_cy - 7),
        (head_cx - 2, head_cy - 7),
        (head_cx - 6, head_cy - 4),
        (head_cx - 7, head_cy + 4),
    ]
    pygame.draw.polygon(head_layer, (0, 0, 0, 220), void_pts)
    # Glow-Augen aus dem Void
    pygame.draw.circle(head_layer, (*eye, 240), (head_cx - 3, head_cy - 1), 2)
    pygame.draw.circle(head_layer, (*eye, 240), (head_cx + 3, head_cy - 1), 2)
    # Outer-Glow
    glow_l = pygame.Surface((12, 12), pygame.SRCALPHA)
    pygame.draw.circle(glow_l, (*eye, 120), (6, 6), 5)
    pygame.draw.circle(glow_l, (*eye, 60), (6, 6), 6)
    head_layer.blit(glow_l, (head_cx - 9, head_cy - 7))
    head_layer.blit(glow_l, (head_cx - 3, head_cy - 7))

    surf.blit(head_layer, (0, 0))

    return surf


def _gen_archer_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #203: Detail-Archer — feindlicher Bogenschuetze.

    Dunkle Hood, Brigandine-Leder, gespannter Bogen, Quiver hinten.
    Klar vom Player-Ranger unterscheidbar (mehr boese/wild).
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    leather     = color
    leather_lt  = _shade(color, 1.28)
    leather_dk  = _shade(color, 0.55)
    cloth_blk   = (28, 24, 32)
    cloth_dk    = (52, 42, 52)
    skin        = (172, 132, 102)
    skin_sh     = (118, 88, 68)
    wood        = (88, 60, 36)
    wood_lt     = (132, 96, 60)
    wood_dk     = (52, 36, 20)
    string      = (220, 215, 195)
    metal       = (142, 138, 132)
    metal_lt    = (192, 188, 178)
    blood       = (108, 28, 36)
    OL          = (8, 6, 8)

    if walk_frame == 1:
        l_dy, r_dy = -2, 1
        arm_swing = -2
    elif walk_frame == 3:
        l_dy, r_dy = 1, -2
        arm_swing = 2
    else:
        l_dy, r_dy = 0, 0
        arm_swing = 0

    # ============================================================
    # BOW — Back-Half (oberer Bogen-Arm hinter Schulter)
    # ============================================================
    bow_cx = cx - 22
    bow_cy = fy - 56
    pygame.draw.arc(surf, wood,
                     (bow_cx - 6, bow_cy - 8, 12, 28),
                     math.pi * 0.3, math.pi * 0.95, 3)
    pygame.draw.arc(surf, OL,
                     (bow_cx - 6, bow_cy - 8, 12, 28),
                     math.pi * 0.3, math.pi * 0.95, 1)

    # ============================================================
    # QUIVER — Pfeile hinten ueber Schulter
    # ============================================================
    quiver_x = cx + 14
    pygame.draw.rect(surf, leather_dk,
                      (quiver_x - 3, fy - 56, 6, 24))
    pygame.draw.rect(surf, OL,
                      (quiver_x - 3, fy - 56, 6, 24), 1)
    pygame.draw.line(surf, leather,
                      (quiver_x - 2, fy - 55),
                      (quiver_x - 2, fy - 34), 1)
    # Pfeile (Federn oben)
    for ax in (quiver_x - 1, quiver_x + 1):
        pygame.draw.line(surf, leather_lt,
                          (ax - 1, fy - 60), (ax + 1, fy - 60), 1)
        pygame.draw.line(surf, leather,
                          (ax, fy - 62), (ax, fy - 59), 1)
        pygame.draw.line(surf, blood,
                          (ax, fy - 63), (ax, fy - 62), 1)
    # Strap ueber die Schulter
    pygame.draw.line(surf, leather_dk,
                      (cx - 10, fy - 50),
                      (quiver_x, fy - 52), 2)

    # ============================================================
    # BOOTS — Lederstiefel
    # ============================================================
    boot_l = pygame.Rect(cx - 12, fy - 6 + l_dy, 10, 6)
    pygame.draw.rect(surf, cloth_blk, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, cloth_dk,
                      (boot_l.x + 1, boot_l.y + 1),
                      (boot_l.right - 2, boot_l.y + 1), 1)
    for ly in (boot_l.y + 2, boot_l.y + 4):
        pygame.draw.line(surf, OL,
                          (boot_l.x + 2, ly),
                          (boot_l.right - 2, ly), 1)
    boot_r = pygame.Rect(cx + 2, fy - 6 + r_dy, 10, 6)
    pygame.draw.rect(surf, cloth_blk, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, cloth_dk,
                      (boot_r.x + 1, boot_r.y + 1),
                      (boot_r.right - 2, boot_r.y + 1), 1)
    for ly in (boot_r.y + 2, boot_r.y + 4):
        pygame.draw.line(surf, OL,
                          (boot_r.x + 2, ly),
                          (boot_r.right - 2, ly), 1)

    # ============================================================
    # LEGS — schmale dunkle Hose
    # ============================================================
    leg_l = pygame.Rect(cx - 11, fy - 20 + l_dy, 8, 14)
    pygame.draw.rect(surf, cloth_blk, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, cloth_dk,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    leg_r = pygame.Rect(cx + 3, fy - 20 + r_dy, 8, 14)
    pygame.draw.rect(surf, cloth_blk, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, cloth_dk,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)

    # ============================================================
    # TORSO — Brigandine-Leder (Metall-Studs)
    # ============================================================
    torso_top = fy - 60
    torso_bot = fy - 22
    torso_pts = [
        (cx - 12, torso_top + 2),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 12, torso_top + 2),
        (cx + 16, torso_top + 14),
        (cx + 15, torso_bot),
        (cx - 15, torso_bot),
        (cx - 16, torso_top + 14),
    ]
    pygame.draw.polygon(surf, leather, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brigandine-Studs (kleine Metall-Nieten in Reihen)
    for sy_ in (torso_top + 6, torso_top + 14, torso_top + 22):
        for sx_ in (cx - 8, cx - 3, cx + 2, cx + 7):
            pygame.draw.circle(surf, metal, (sx_, sy_), 1)
            pygame.draw.circle(surf, OL, (sx_, sy_), 1, 1)
    # Highlight
    pygame.draw.polygon(surf, leather_lt, [
        (cx - 9, torso_top + 3),
        (cx - 2, torso_top + 4),
        (cx - 4, torso_top + 18),
        (cx - 13, torso_top + 16),
    ])

    # Belt
    belt_y = torso_bot - 4
    pygame.draw.rect(surf, leather_dk, (cx - 15, belt_y, 30, 4))
    pygame.draw.rect(surf, OL, (cx - 15, belt_y, 30, 4), 1)
    pygame.draw.rect(surf, metal, (cx - 2, belt_y - 1, 4, 6))
    pygame.draw.rect(surf, OL, (cx - 2, belt_y - 1, 4, 6), 1)

    # ============================================================
    # ARMS — Bow-Stance: linker vorne, rechter zurueck (Pfeil ziehen)
    # ============================================================
    arm_top = torso_top + 6
    # Linker Arm haelt Bogen
    arm_l = pygame.Rect(cx - 18, arm_top + arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Bracer
    pygame.draw.rect(surf, cloth_blk,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 5, 7, 5), 1)
    # Hand am Bogen-Grip
    pygame.draw.circle(surf, skin,
                        (arm_l.centerx - 1, arm_l.bottom + 1), 3)
    pygame.draw.circle(surf, OL,
                        (arm_l.centerx - 1, arm_l.bottom + 1), 3, 1)

    # Rechter Arm — zieht Sehne (nach hinten)
    arm_r = pygame.Rect(cx + 13, arm_top - arm_swing, 5, 11)
    pygame.draw.rect(surf, leather, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.rect(surf, cloth_blk,
                      (arm_r.x, arm_r.bottom - 5, 7, 5))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 5, 7, 5), 1)
    pygame.draw.circle(surf, skin,
                        (arm_r.centerx + 1, arm_r.bottom + 1), 3)
    pygame.draw.circle(surf, OL,
                        (arm_r.centerx + 1, arm_r.bottom + 1), 3, 1)

    # ============================================================
    # HEAD + HOOD — dunkle Hood mit Schatten ueber Augen
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    # Skin (Gesicht in der Hood-Oeffnung)
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 7)
    pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 6)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 7, 1)
    # Hood (drapiert auf Schultern)
    hood_pts = [
        (head_cx - 13, torso_top + 4),
        (head_cx - 12, head_cy - 3),
        (head_cx - 8, head_cy - 10),
        (head_cx - 2, head_cy - 12),
        (head_cx + 2, head_cy - 12),
        (head_cx + 8, head_cy - 10),
        (head_cx + 12, head_cy - 3),
        (head_cx + 13, torso_top + 4),
        (head_cx + 7, head_cy + 2),
        (head_cx + 8, head_cy - 4),
        (head_cx + 4, head_cy - 8),
        (head_cx - 4, head_cy - 8),
        (head_cx - 8, head_cy - 4),
        (head_cx - 7, head_cy + 2),
    ]
    pygame.draw.polygon(surf, cloth_blk, hood_pts)
    pygame.draw.polygon(surf, OL, hood_pts, 2)
    # Hood-Highlight
    pygame.draw.line(surf, cloth_dk,
                      (head_cx - 11, head_cy - 3),
                      (head_cx - 7, head_cy - 9), 1)
    # Schatten ueber Augen
    pygame.draw.rect(surf, (16, 14, 18),
                      (head_cx - 5, head_cy - 4, 10, 3))
    # Glow-Augen
    pygame.draw.circle(surf, glow_col, (head_cx - 2, head_cy - 2), 1)
    pygame.draw.circle(surf, glow_col, (head_cx + 2, head_cy - 2), 1)
    # Mund (schmal)
    pygame.draw.line(surf, OL,
                      (head_cx - 2, head_cy + 3),
                      (head_cx + 2, head_cy + 3), 1)

    # ============================================================
    # BOW — Front-Half + Sehne + Pfeil im Anschlag
    # ============================================================
    bow_cx = cx - 22
    bow_cy_bot = fy - 32
    # Unterer Limb
    pygame.draw.arc(surf, wood,
                     (bow_cx - 6, bow_cy_bot - 20, 12, 28),
                     math.pi * 1.05, math.pi * 1.7, 3)
    pygame.draw.arc(surf, OL,
                     (bow_cx - 6, bow_cy_bot - 20, 12, 28),
                     math.pi * 1.05, math.pi * 1.7, 1)
    # Sehne — gezogen (V-Form, weil Pfeil im Anschlag)
    pygame.draw.line(surf, string,
                      (bow_cx + 2, fy - 56),
                      (bow_cx + 8, fy - 50), 1)
    pygame.draw.line(surf, string,
                      (bow_cx + 8, fy - 50),
                      (bow_cx + 2, fy - 36), 1)
    # Pfeil (horizontal, gespannt)
    arrow_y = fy - 50
    arrow_tip_x = bow_cx - 4
    pygame.draw.line(surf, wood,
                      (arrow_tip_x, arrow_y),
                      (bow_cx + 8, arrow_y), 2)
    pygame.draw.line(surf, OL,
                      (arrow_tip_x, arrow_y),
                      (bow_cx + 8, arrow_y), 1)
    # Pfeilspitze (Metall)
    pygame.draw.polygon(surf, metal, [
        (arrow_tip_x - 3, arrow_y),
        (arrow_tip_x, arrow_y - 2),
        (arrow_tip_x, arrow_y + 2),
    ])
    pygame.draw.polygon(surf, OL, [
        (arrow_tip_x - 3, arrow_y),
        (arrow_tip_x, arrow_y - 2),
        (arrow_tip_x, arrow_y + 2),
    ], 1)
    pygame.draw.line(surf, metal_lt,
                      (arrow_tip_x - 2, arrow_y),
                      (arrow_tip_x, arrow_y - 1), 1)
    # Federn am Ende
    pygame.draw.line(surf, blood,
                      (bow_cx + 6, arrow_y - 2),
                      (bow_cx + 8, arrow_y), 1)
    pygame.draw.line(surf, blood,
                      (bow_cx + 6, arrow_y + 2),
                      (bow_cx + 8, arrow_y), 1)

    return surf


def _gen_berserker_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #203: Detail-Berserker — wilde Krieger, twin Axes,
    bare-chest, wilde Haare, blutverschmiert.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    skin        = color
    skin_lt     = _shade(color, 1.30)
    skin_sh     = _shade(color, 0.62)
    skin_blk    = _shade(color, 0.35)
    hair        = (78, 28, 22)            # rot-braun, wild
    hair_lt     = (138, 58, 42)
    hair_dk     = (38, 14, 10)
    blood       = (140, 32, 32)
    blood_dk    = (78, 18, 22)
    leather     = (52, 36, 22)
    leather_lt  = (98, 68, 42)
    fur         = (138, 108, 76)
    fur_dk      = (88, 64, 42)
    metal       = (118, 110, 100)
    metal_lt    = (172, 162, 148)
    metal_dk    = (62, 56, 50)
    bone        = (220, 210, 188)
    OL          = (8, 6, 8)

    if walk_frame == 1:
        l_dy, r_dy = -3, 1
        lean = -1
    elif walk_frame == 3:
        l_dy, r_dy = 1, -3
        lean = 1
    else:
        l_dy, r_dy = 0, 0
        lean = 0

    # ============================================================
    # FEET — barfuss / Wickel
    # ============================================================
    foot_l_pts = [
        (cx - 13, fy - 4 + l_dy),
        (cx - 5, fy - 4 + l_dy),
        (cx - 4, fy + l_dy),
        (cx - 13, fy + l_dy),
    ]
    pygame.draw.polygon(surf, skin_sh, foot_l_pts)
    pygame.draw.polygon(surf, OL, foot_l_pts, 1)
    foot_r_pts = [
        (cx + 5, fy - 4 + r_dy),
        (cx + 13, fy - 4 + r_dy),
        (cx + 13, fy + r_dy),
        (cx + 4, fy + r_dy),
    ]
    pygame.draw.polygon(surf, skin_sh, foot_r_pts)
    pygame.draw.polygon(surf, OL, foot_r_pts, 1)

    # ============================================================
    # LEGS — bare Beine mit Wickel
    # ============================================================
    leg_l = pygame.Rect(cx - 12, fy - 22 + l_dy, 9, 18)
    pygame.draw.rect(surf, skin, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Wickel-Bandagen
    for ly in (leg_l.y + 3, leg_l.y + 8, leg_l.y + 13):
        pygame.draw.line(surf, leather,
                          (leg_l.x - 1, ly),
                          (leg_l.right + 1, ly + 1), 2)
    # Blut-Streifen
    pygame.draw.line(surf, blood,
                      (leg_l.x + 4, leg_l.y + 6),
                      (leg_l.x + 5, leg_l.y + 14), 1)

    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 9, 18)
    pygame.draw.rect(surf, skin, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    for ly in (leg_r.y + 3, leg_r.y + 8, leg_r.y + 13):
        pygame.draw.line(surf, leather,
                          (leg_r.x - 1, ly),
                          (leg_r.right + 1, ly + 1), 2)

    # ============================================================
    # LOINCLOTH — Fell-Lendenschurz
    # ============================================================
    loin_pts = [
        (cx - 15, fy - 30),
        (cx + 15, fy - 30),
        (cx + 17, fy - 22),
        (cx + 10, fy - 18),
        (cx + 2, fy - 22),
        (cx - 2, fy - 22),
        (cx - 10, fy - 18),
        (cx - 17, fy - 22),
    ]
    pygame.draw.polygon(surf, fur, loin_pts)
    pygame.draw.polygon(surf, OL, loin_pts, 2)
    # Fell-Textur
    for fx_ in (cx - 10, cx - 4, cx + 4, cx + 10):
        pygame.draw.line(surf, fur_dk,
                          (fx_, fy - 29), (fx_, fy - 20), 1)
    pygame.draw.line(surf, leather,
                      (cx - 15, fy - 30),
                      (cx + 15, fy - 30), 2)

    # ============================================================
    # TORSO — bare-chest mit Narben und Blut
    # ============================================================
    torso_top = fy - 64
    torso_bot = fy - 30
    torso_pts = [
        (cx - 15, torso_top + 4),
        (cx - 12, torso_top),
        (cx + 12, torso_top),
        (cx + 15, torso_top + 4),
        (cx + 19, torso_top + 16),
        (cx + 17, torso_bot),
        (cx - 17, torso_bot),
        (cx - 19, torso_top + 16),
    ]
    pygame.draw.polygon(surf, skin, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Muskel-Definition
    pygame.draw.line(surf, skin_sh,
                      (cx - 10, torso_top + 4),
                      (cx, torso_top + 10), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx + 10, torso_top + 4),
                      (cx, torso_top + 10), 1)
    # 6-Pack
    for by in (torso_top + 14, torso_top + 22, torso_top + 28):
        pygame.draw.line(surf, skin_sh,
                          (cx - 8, by), (cx + 8, by), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx, torso_top + 12),
                      (cx, torso_bot - 2), 1)
    # Highlight
    pygame.draw.polygon(surf, skin_lt, [
        (cx - 11, torso_top + 3),
        (cx - 4, torso_top + 4),
        (cx - 7, torso_top + 18),
        (cx - 14, torso_top + 16),
    ])
    # Narben (mehrere, kreuz und quer)
    pygame.draw.line(surf, blood,
                      (cx + 3, torso_top + 6),
                      (cx + 10, torso_top + 14), 2)
    pygame.draw.line(surf, skin_blk,
                      (cx + 3, torso_top + 6),
                      (cx + 10, torso_top + 14), 1)
    pygame.draw.line(surf, blood,
                      (cx - 6, torso_top + 18),
                      (cx + 2, torso_top + 24), 1)
    # Tribale Markierungen (rote Striche)
    for stripe_y in (torso_top + 12, torso_top + 20):
        pygame.draw.line(surf, blood,
                          (cx - 10, stripe_y),
                          (cx - 12, stripe_y + 2), 2)
        pygame.draw.line(surf, blood,
                          (cx + 10, stripe_y),
                          (cx + 12, stripe_y + 2), 2)
    # Blutspritzer (frische Battle-Wounds)
    pygame.draw.circle(surf, blood, (cx + 6, torso_top + 8), 2)
    pygame.draw.circle(surf, blood_dk, (cx + 7, torso_top + 9), 1)
    pygame.draw.circle(surf, blood, (cx - 4, torso_top + 22), 1)

    # ============================================================
    # SHOULDER-FUR-PADS — Fellschulter (Bear/Wolf)
    # ============================================================
    # Links
    pl_l_pts = [
        (cx - 18, torso_top + 8),
        (cx - 14, torso_top - 2),
        (cx - 8, torso_top),
        (cx - 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, fur, pl_l_pts)
    pygame.draw.polygon(surf, OL, pl_l_pts, 1)
    # Fell-Strands
    for fx_, fy_ in ((-16, -1), (-13, -3), (-10, -1)):
        pygame.draw.line(surf, fur_dk,
                          (cx + fx_, torso_top + fy_),
                          (cx + fx_, torso_top + fy_ + 4), 1)
    # Rechts
    pl_r_pts = [
        (cx + 8, torso_top),
        (cx + 14, torso_top - 2),
        (cx + 18, torso_top + 8),
        (cx + 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, fur, pl_r_pts)
    pygame.draw.polygon(surf, OL, pl_r_pts, 1)
    for fx_, fy_ in ((10, -1), (13, -3), (16, -1)):
        pygame.draw.line(surf, fur_dk,
                          (cx + fx_, torso_top + fy_),
                          (cx + fx_, torso_top + fy_ + 4), 1)

    # ============================================================
    # ARMS — riesige Bare-Muskel-Arme
    # ============================================================
    arm_top = torso_top + 10
    # Linker Arm
    arm_l = pygame.Rect(cx - 20, arm_top + lean * 2, 6, 16)
    pygame.draw.rect(surf, skin, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_l.x + 1, arm_l.y + 1),
                      (arm_l.x + 1, arm_l.bottom - 2), 1)
    # Bicep-Schatten
    pygame.draw.arc(surf, skin_sh,
                     (arm_l.x, arm_l.y + 3, arm_l.width, 8),
                     math.pi, 2 * math.pi, 1)
    # Tribal-Tattoo
    for ty in (arm_l.y + 2, arm_l.y + 5, arm_l.y + 8):
        pygame.draw.line(surf, blood,
                          (arm_l.x + 1, ty),
                          (arm_l.right - 1, ty), 1)
    # Hand
    pygame.draw.circle(surf, skin,
                        (arm_l.centerx - 1, arm_l.bottom + 3), 3)
    pygame.draw.circle(surf, OL,
                        (arm_l.centerx - 1, arm_l.bottom + 3), 3, 1)

    # Rechter Arm
    arm_r = pygame.Rect(cx + 14, arm_top - lean * 2, 6, 16)
    pygame.draw.rect(surf, skin, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (arm_r.x + 1, arm_r.y + 1),
                      (arm_r.x + 1, arm_r.bottom - 2), 1)
    pygame.draw.arc(surf, skin_sh,
                     (arm_r.x, arm_r.y + 3, arm_r.width, 8),
                     math.pi, 2 * math.pi, 1)
    # Faust
    pygame.draw.circle(surf, skin,
                        (arm_r.centerx + 1, arm_r.bottom + 3), 3)
    pygame.draw.circle(surf, OL,
                        (arm_r.centerx + 1, arm_r.bottom + 3), 3, 1)

    # ============================================================
    # TWIN AXES — eine in jeder Hand
    # ============================================================
    # Linke Axt
    ax_l_x = arm_l.centerx - 1
    ax_l_y = arm_l.bottom + 6
    # Stiel
    pygame.draw.rect(surf, leather,
                      (ax_l_x - 1, ax_l_y - 8, 3, 14))
    pygame.draw.rect(surf, OL,
                      (ax_l_x - 1, ax_l_y - 8, 3, 14), 1)
    # Axt-Kopf links
    head_pts = [
        (ax_l_x - 1, ax_l_y - 8),
        (ax_l_x - 7, ax_l_y - 10),
        (ax_l_x - 8, ax_l_y - 4),
        (ax_l_x - 2, ax_l_y - 4),
    ]
    pygame.draw.polygon(surf, metal, head_pts)
    pygame.draw.polygon(surf, OL, head_pts, 1)
    pygame.draw.line(surf, metal_lt,
                      (ax_l_x - 6, ax_l_y - 9),
                      (ax_l_x - 7, ax_l_y - 5), 1)
    pygame.draw.line(surf, blood,
                      (ax_l_x - 8, ax_l_y - 6),
                      (ax_l_x - 8, ax_l_y - 8), 1)
    # Lederwickel-Grip
    for gy in (ax_l_y - 4, ax_l_y - 1, ax_l_y + 2):
        pygame.draw.line(surf, leather_lt,
                          (ax_l_x - 1, gy),
                          (ax_l_x + 1, gy), 1)
    # Pommel-Knochen unten
    pygame.draw.circle(surf, bone, (ax_l_x, ax_l_y + 7), 2)
    pygame.draw.circle(surf, OL, (ax_l_x, ax_l_y + 7), 2, 1)

    # Rechte Axt (Spiegel)
    ax_r_x = arm_r.centerx + 1
    ax_r_y = arm_r.bottom + 6
    pygame.draw.rect(surf, leather,
                      (ax_r_x - 1, ax_r_y - 8, 3, 14))
    pygame.draw.rect(surf, OL,
                      (ax_r_x - 1, ax_r_y - 8, 3, 14), 1)
    head_r_pts = [
        (ax_r_x + 2, ax_r_y - 8),
        (ax_r_x + 8, ax_r_y - 10),
        (ax_r_x + 9, ax_r_y - 4),
        (ax_r_x + 3, ax_r_y - 4),
    ]
    pygame.draw.polygon(surf, metal, head_r_pts)
    pygame.draw.polygon(surf, OL, head_r_pts, 1)
    pygame.draw.line(surf, metal_lt,
                      (ax_r_x + 6, ax_r_y - 9),
                      (ax_r_x + 7, ax_r_y - 5), 1)
    pygame.draw.line(surf, blood,
                      (ax_r_x + 8, ax_r_y - 6),
                      (ax_r_x + 8, ax_r_y - 8), 1)
    for gy in (ax_r_y - 4, ax_r_y - 1, ax_r_y + 2):
        pygame.draw.line(surf, leather_lt,
                          (ax_r_x - 1, gy),
                          (ax_r_x + 1, gy), 1)
    pygame.draw.circle(surf, bone, (ax_r_x, ax_r_y + 7), 2)
    pygame.draw.circle(surf, OL, (ax_r_x, ax_r_y + 7), 2, 1)

    # ============================================================
    # NECK + HEAD — wild, Blut-Paint
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 4, torso_top - 4, 8, 5))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 4, 3, 5))
    pygame.draw.rect(surf, OL, (cx - 4, torso_top - 4, 8, 5), 1)

    head_cx = cx
    head_cy = torso_top - 11
    # Skin
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
    pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 8)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 2)
    # Highlight
    pygame.draw.circle(surf, skin_lt, (head_cx - 3, head_cy - 4), 2)
    # Tribal-Paint (blut-rot, ueber Augen)
    pygame.draw.line(surf, blood,
                      (head_cx - 7, head_cy - 1),
                      (head_cx + 7, head_cy - 1), 3)
    pygame.draw.line(surf, blood_dk,
                      (head_cx - 7, head_cy - 1),
                      (head_cx + 7, head_cy - 1), 1)
    # Augen (wild, weiss)
    pygame.draw.circle(surf, (250, 240, 230),
                        (head_cx - 3, head_cy + 1), 2)
    pygame.draw.circle(surf, OL,
                        (head_cx - 3, head_cy + 1), 2, 1)
    pygame.draw.circle(surf, OL,
                        (head_cx - 3, head_cy + 1), 1)
    pygame.draw.circle(surf, (250, 240, 230),
                        (head_cx + 3, head_cy + 1), 2)
    pygame.draw.circle(surf, OL,
                        (head_cx + 3, head_cy + 1), 2, 1)
    pygame.draw.circle(surf, OL,
                        (head_cx + 3, head_cy + 1), 1)
    # Mund — bruellt (offen)
    pygame.draw.ellipse(surf, OL,
                         (head_cx - 4, head_cy + 4, 8, 5))
    # Zaehne
    pygame.draw.line(surf, bone,
                      (head_cx - 3, head_cy + 5),
                      (head_cx + 3, head_cy + 5), 1)
    pygame.draw.line(surf, bone,
                      (head_cx - 3, head_cy + 7),
                      (head_cx + 3, head_cy + 7), 1)

    # ============================================================
    # HAIR — wilde Mähne / Mohawk
    # ============================================================
    # Mohawk-Mittelstrang
    for hy in range(head_cy - 14, head_cy - 5):
        pygame.draw.line(surf, hair,
                          (head_cx - 1, hy),
                          (head_cx + 1, hy), 1)
    pygame.draw.line(surf, hair_lt,
                      (head_cx, head_cy - 14),
                      (head_cx, head_cy - 6), 1)
    # Side-Strands (zerzaust, fallen ueber Schultern)
    for sx_, lean_ in ((-9, -2), (-7, -3), (9, 2), (7, 3)):
        pygame.draw.line(surf, hair,
                          (head_cx + sx_, head_cy - 4),
                          (head_cx + sx_ + lean_, head_cy + 8), 2)
        pygame.draw.line(surf, hair_dk,
                          (head_cx + sx_, head_cy - 4),
                          (head_cx + sx_ + lean_, head_cy + 8), 1)
    # Stirn-Strähne
    pygame.draw.line(surf, hair_dk,
                      (head_cx - 3, head_cy - 5),
                      (head_cx + 1, head_cy - 3), 2)

    return surf


def _gen_slime_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #203: Slime — Gel/Schleim-Blob mit innerem Kern.

    Wobble-Anim via walk_frame, transluzent, kein Skelett/Anatomie.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    base       = color
    base_lt    = _shade(color, 1.40)
    base_dk    = _shade(color, 0.55)
    core       = glow_col
    core_lt    = _shade(glow_col, 1.40)
    OL         = (8, 6, 10)

    # Wobble (Blob squishes/stretches)
    if walk_frame == 1:
        wobble_w = 4
        wobble_h = -2
    elif walk_frame == 3:
        wobble_w = -4
        wobble_h = 2
    else:
        wobble_w = 0
        wobble_h = 0

    # ============================================================
    # BLOB-BODY — Halbkugel/Wassertropfen-Form
    # ============================================================
    blob_w = 56 + wobble_w
    blob_h = 56 + wobble_h
    blob_cx = cx
    blob_cy = fy - 22 + wobble_h // 2
    # Schatten am Boden
    sh = pygame.Surface((blob_w + 8, 14), pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 120),
                         (0, 0, blob_w + 8, 14))
    surf.blit(sh, (blob_cx - blob_w // 2 - 4, fy - 6))

    # Body (Hauptblob, leicht halbtransparent)
    body_layer = pygame.Surface((W, H), pygame.SRCALPHA)
    pygame.draw.ellipse(body_layer, (*base, 220),
                         (blob_cx - blob_w // 2,
                          blob_cy - blob_h // 2,
                          blob_w, blob_h))
    pygame.draw.ellipse(body_layer, OL,
                         (blob_cx - blob_w // 2,
                          blob_cy - blob_h // 2,
                          blob_w, blob_h), 2)
    surf.blit(body_layer, (0, 0))

    # ============================================================
    # CORE — innerer Kristall/Auge (gluehend)
    # ============================================================
    core_cx = blob_cx
    core_cy = blob_cy - 4
    # Outer-Glow
    for r_, a_ in ((10, 60), (8, 100), (6, 180)):
        glow = pygame.Surface((r_ * 2 + 2, r_ * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow, (*core, a_), (r_ + 1, r_ + 1), r_)
        surf.blit(glow, (core_cx - r_ - 1, core_cy - r_ - 1))
    # Core selbst
    pygame.draw.circle(surf, core, (core_cx, core_cy), 5)
    pygame.draw.circle(surf, core_lt, (core_cx - 1, core_cy - 1), 3)
    pygame.draw.circle(surf, (255, 255, 255), (core_cx - 2, core_cy - 2), 1)

    # ============================================================
    # HIGHLIGHTS — Glanzlichter auf der Blob-Oberflaeche (oben links)
    # ============================================================
    # Oben links (Top-Light)
    hl = pygame.Surface((blob_w, blob_h), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (*base_lt, 180),
                         (4, 4, blob_w // 3, blob_h // 4))
    pygame.draw.ellipse(hl, (255, 255, 255, 100),
                         (8, 6, blob_w // 4, blob_h // 6))
    surf.blit(hl, (blob_cx - blob_w // 2, blob_cy - blob_h // 2))

    # Tropfen am Body (auflaufende Schleim-Tropfen)
    for dx_, dy_ in ((-20, 6), (-14, 14), (12, 10), (18, 4)):
        drop_cy = blob_cy + dy_
        pygame.draw.circle(surf, base,
                            (blob_cx + dx_, drop_cy), 3)
        pygame.draw.circle(surf, OL,
                            (blob_cx + dx_, drop_cy), 3, 1)
        pygame.draw.circle(surf, base_lt,
                            (blob_cx + dx_ - 1, drop_cy - 1), 1)

    # Bubbles im Inneren des Blobs (transluzent durch)
    for bx_, by_, br_ in ((-6, 8, 2), (8, -4, 1), (-10, -6, 1),
                            (6, 12, 1), (12, 2, 2)):
        bubble = pygame.Surface((br_ * 2 + 2, br_ * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(bubble, (*base_lt, 200),
                            (br_ + 1, br_ + 1), br_)
        surf.blit(bubble,
                   (blob_cx + bx_ - br_ - 1,
                    blob_cy + by_ - br_ - 1))

    # Bottom-Drip (haengender Tropfen — Slime ist nass)
    drip_x = blob_cx + 3 + wobble_w // 2
    drip_y = blob_cy + blob_h // 2 - 2
    pygame.draw.circle(surf, base, (drip_x, drip_y), 3)
    pygame.draw.circle(surf, OL, (drip_x, drip_y), 3, 1)
    pygame.draw.circle(surf, base_lt, (drip_x - 1, drip_y - 1), 1)

    return surf


def _gen_shaman_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #204: Detail-Shaman — Tribal-Caster mit Knochen-Maske,
    Federn-Schmuck, Totem-Staff. Erkennbar als boeser Naturalist.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    skin       = (172, 132, 92)
    skin_lt    = (218, 178, 138)
    skin_sh    = (118, 88, 60)
    paint      = (138, 28, 32)
    paint_y    = (228, 200, 80)
    fur        = (88, 62, 38)
    fur_lt     = (138, 100, 60)
    fur_dk     = (52, 36, 22)
    bone       = (218, 210, 178)
    bone_dk    = (158, 148, 118)
    feather    = color
    feather_lt = _shade(color, 1.35)
    feather_dk = _shade(color, 0.50)
    wood       = (62, 42, 28)
    wood_lt    = (108, 78, 50)
    glow       = glow_col
    OL         = (10, 8, 12)

    if walk_frame == 1:
        l_dy, r_dy = -2, 1
        staff_sway = -1
    elif walk_frame == 3:
        l_dy, r_dy = 1, -2
        staff_sway = 1
    else:
        l_dy, r_dy = 0, 0
        staff_sway = 0

    # ============================================================
    # STAFF — Back-Half (Totem-Stab hinter Body)
    # ============================================================
    staff_x = cx + 19 + staff_sway
    staff_top_y = fy - 100
    staff_bot_y = fy - 4
    grip_y = fy - 50
    # Back-Schaft
    pygame.draw.line(surf, wood, (staff_x, staff_top_y),
                      (staff_x, grip_y), 3)
    pygame.draw.line(surf, OL, (staff_x, staff_top_y),
                      (staff_x, grip_y), 1)
    pygame.draw.line(surf, wood_lt, (staff_x - 1, staff_top_y + 2),
                      (staff_x - 1, grip_y), 1)

    # ============================================================
    # FEET / LEGS — bare mit Knochen-Schmuck
    # ============================================================
    foot_l = pygame.Rect(cx - 12, fy - 4 + l_dy, 10, 4)
    pygame.draw.ellipse(surf, skin_sh, foot_l)
    pygame.draw.ellipse(surf, OL, foot_l, 1)
    foot_r = pygame.Rect(cx + 2, fy - 4 + r_dy, 10, 4)
    pygame.draw.ellipse(surf, skin_sh, foot_r)
    pygame.draw.ellipse(surf, OL, foot_r, 1)

    leg_l = pygame.Rect(cx - 11, fy - 22 + l_dy, 8, 18)
    pygame.draw.rect(surf, skin, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Tribal-Paint-Stripes
    for ly in (leg_l.y + 4, leg_l.y + 10, leg_l.y + 15):
        pygame.draw.line(surf, paint,
                          (leg_l.x, ly), (leg_l.right, ly + 1), 1)
    # Knochen-Ringe an Fessel
    pygame.draw.line(surf, bone,
                      (leg_l.x - 1, leg_l.bottom - 2),
                      (leg_l.right + 1, leg_l.bottom - 2), 2)

    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 8, 18)
    pygame.draw.rect(surf, skin, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, skin_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    for ly in (leg_r.y + 4, leg_r.y + 10, leg_r.y + 15):
        pygame.draw.line(surf, paint,
                          (leg_r.x, ly), (leg_r.right, ly + 1), 1)
    pygame.draw.line(surf, bone,
                      (leg_r.x - 1, leg_r.bottom - 2),
                      (leg_r.right + 1, leg_r.bottom - 2), 2)

    # ============================================================
    # LOINCLOTH / FUR-SKIRT
    # ============================================================
    skirt_top = fy - 32
    skirt_bot = fy - 20
    skirt_pts = [
        (cx - 15, skirt_top),
        (cx + 15, skirt_top),
        (cx + 16, skirt_bot - 1),
        (cx + 10, skirt_bot),
        (cx + 4, skirt_bot - 2),
        (cx - 4, skirt_bot - 2),
        (cx - 10, skirt_bot),
        (cx - 16, skirt_bot - 1),
    ]
    pygame.draw.polygon(surf, fur, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 1)
    # Fell-Strands
    for fx_ in (cx - 11, cx - 5, cx + 5, cx + 11):
        pygame.draw.line(surf, fur_dk,
                          (fx_, skirt_top + 2),
                          (fx_, skirt_bot - 3), 1)

    # ============================================================
    # TORSO — bare chest mit Tribal-Paint
    # ============================================================
    torso_top = fy - 62
    torso_bot = fy - 32
    torso_pts = [
        (cx - 12, torso_top + 2),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 12, torso_top + 2),
        (cx + 16, torso_top + 14),
        (cx + 15, torso_bot),
        (cx - 15, torso_bot),
        (cx - 16, torso_top + 14),
    ]
    pygame.draw.polygon(surf, skin, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Muskel-Linien
    pygame.draw.line(surf, skin_sh,
                      (cx - 8, torso_top + 4),
                      (cx, torso_top + 8), 1)
    pygame.draw.line(surf, skin_sh,
                      (cx + 8, torso_top + 4),
                      (cx, torso_top + 8), 1)
    # Brust-Tribal-Paint (Symbole)
    # Spiral-Symbol (rot)
    pygame.draw.arc(surf, paint,
                     (cx - 5, torso_top + 4, 10, 8),
                     0, math.pi * 1.8, 2)
    pygame.draw.circle(surf, paint, (cx, torso_top + 8), 1)
    # Punkt-Reihen (gelb)
    for px_ in (cx - 7, cx - 4, cx, cx + 4, cx + 7):
        pygame.draw.circle(surf, paint_y, (px_, torso_top + 18), 1)
    # Highlight
    pygame.draw.polygon(surf, skin_lt, [
        (cx - 9, torso_top + 3),
        (cx - 4, torso_top + 4),
        (cx - 6, torso_top + 16),
        (cx - 13, torso_top + 14),
    ])
    # Knochen-Ketten ueber Brust
    for cy_ in (torso_top + 22, torso_top + 26):
        pygame.draw.line(surf, bone,
                          (cx - 12, cy_),
                          (cx + 12, cy_), 1)
        # Anhänger
        for hx_ in (cx - 8, cx - 4, cx, cx + 4, cx + 8):
            pygame.draw.line(surf, bone,
                              (hx_, cy_),
                              (hx_, cy_ + 2), 1)

    # ============================================================
    # SHOULDER-PADS — Fellschulter mit Federn
    # ============================================================
    # Linke Fur-Pad
    pl_l_pts = [
        (cx - 18, torso_top + 6),
        (cx - 14, torso_top - 1),
        (cx - 8, torso_top + 1),
        (cx - 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, fur, pl_l_pts)
    pygame.draw.polygon(surf, OL, pl_l_pts, 1)
    pygame.draw.line(surf, fur_lt,
                      (cx - 16, torso_top + 4),
                      (cx - 14, torso_top), 1)
    # Feder am Shoulder (links)
    feather_pts = [
        (cx - 16, torso_top - 2),
        (cx - 18, torso_top - 8),
        (cx - 14, torso_top - 10),
        (cx - 12, torso_top - 4),
    ]
    pygame.draw.polygon(surf, feather, feather_pts)
    pygame.draw.polygon(surf, OL, feather_pts, 1)
    pygame.draw.line(surf, feather_lt,
                      (cx - 15, torso_top - 8),
                      (cx - 13, torso_top - 4), 1)
    pygame.draw.line(surf, feather_dk,
                      (cx - 15, torso_top - 3),
                      (cx - 15, torso_top - 9), 1)

    # Rechte Fur-Pad + Feder
    pl_r_pts = [
        (cx + 8, torso_top + 1),
        (cx + 14, torso_top - 1),
        (cx + 18, torso_top + 6),
        (cx + 12, torso_top + 12),
    ]
    pygame.draw.polygon(surf, fur, pl_r_pts)
    pygame.draw.polygon(surf, OL, pl_r_pts, 1)
    feather_r_pts = [
        (cx + 12, torso_top - 4),
        (cx + 14, torso_top - 10),
        (cx + 18, torso_top - 8),
        (cx + 16, torso_top - 2),
    ]
    pygame.draw.polygon(surf, feather, feather_r_pts)
    pygame.draw.polygon(surf, OL, feather_r_pts, 1)
    pygame.draw.line(surf, feather_dk,
                      (cx + 15, torso_top - 3),
                      (cx + 15, torso_top - 9), 1)

    # ============================================================
    # ARMS — bare arms mit tribal Paint
    # ============================================================
    arm_top = torso_top + 8
    # Linker
    arm_l = pygame.Rect(cx - 17, arm_top, 5, 14)
    pygame.draw.rect(surf, skin, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    # Tribal-Paint
    for ty in (arm_l.y + 2, arm_l.y + 7, arm_l.y + 11):
        pygame.draw.line(surf, paint,
                          (arm_l.x + 1, ty),
                          (arm_l.right - 1, ty), 1)
    # Bracer (Knochen-Wickel)
    pygame.draw.rect(surf, bone_dk,
                      (arm_l.x - 1, arm_l.bottom - 3, 7, 3))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 3, 7, 3), 1)
    # Hand
    pygame.draw.circle(surf, skin,
                        (arm_l.centerx, arm_l.bottom + 2), 2)
    pygame.draw.circle(surf, OL,
                        (arm_l.centerx, arm_l.bottom + 2), 2, 1)

    # Rechter (haelt Staff)
    arm_r = pygame.Rect(cx + 12, arm_top, 5, 14)
    pygame.draw.rect(surf, skin, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    for ty in (arm_r.y + 2, arm_r.y + 7, arm_r.y + 11):
        pygame.draw.line(surf, paint,
                          (arm_r.x + 1, ty),
                          (arm_r.right - 1, ty), 1)
    pygame.draw.rect(surf, bone_dk,
                      (arm_r.x, arm_r.bottom - 3, 7, 3))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 3, 7, 3), 1)
    pygame.draw.circle(surf, skin,
                        (arm_r.centerx + 1, arm_r.bottom + 2), 2)
    pygame.draw.circle(surf, OL,
                        (arm_r.centerx + 1, arm_r.bottom + 2), 2, 1)

    # ============================================================
    # HEAD — Knochen-Maske
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    # Skin (Hals + Kinn sichtbar unter der Maske)
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 1)
    # Knochen-Maske ueber dem Gesicht (laesst nur Mund/Kinn frei)
    mask_pts = [
        (head_cx - 9, head_cy - 3),
        (head_cx - 9, head_cy - 9),
        (head_cx - 5, head_cy - 11),
        (head_cx + 5, head_cy - 11),
        (head_cx + 9, head_cy - 9),
        (head_cx + 9, head_cy - 3),
        (head_cx + 4, head_cy + 2),
        (head_cx - 4, head_cy + 2),
    ]
    pygame.draw.polygon(surf, bone, mask_pts)
    pygame.draw.polygon(surf, OL, mask_pts, 2)
    # Maske-Mund (Zaehne-Schnitzerei)
    pygame.draw.rect(surf, OL,
                      (head_cx - 4, head_cy + 1, 8, 2))
    for tx in (-3, -1, 1, 3):
        pygame.draw.line(surf, bone,
                          (head_cx + tx, head_cy + 1),
                          (head_cx + tx, head_cy + 2), 1)
    # Augen-Loecher in der Maske (dunkel + Glow)
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 4), 2)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 4), 2)
    pygame.draw.circle(surf, glow, (head_cx - 3, head_cy - 4), 1)
    pygame.draw.circle(surf, glow, (head_cx + 3, head_cy - 4), 1)
    # Maske-Highlight (Stirn)
    pygame.draw.line(surf, (240, 230, 200),
                      (head_cx - 6, head_cy - 8),
                      (head_cx - 2, head_cy - 10), 1)
    # Maske-Risse / Battle-Damage
    pygame.draw.line(surf, OL,
                      (head_cx + 5, head_cy - 9),
                      (head_cx + 7, head_cy - 6), 1)
    # Tribal-Symbol auf der Stirn (paint)
    pygame.draw.circle(surf, paint, (head_cx, head_cy - 8), 1)
    pygame.draw.line(surf, paint,
                      (head_cx, head_cy - 9),
                      (head_cx, head_cy - 6), 1)

    # ============================================================
    # FEDERN-KRONE — Federn um den Kopf (Schamanen-Krone)
    # ============================================================
    for ang_idx in (-2, -1, 0, 1, 2):
        ang = ang_idx * 0.35
        base_x = head_cx + math.sin(ang) * 9
        base_y = head_cy - 10
        tip_x = head_cx + math.sin(ang) * 14
        tip_y = head_cy - 18
        # Federn-Stiel
        pygame.draw.line(surf, OL,
                          (base_x, base_y),
                          (tip_x, tip_y), 1)
        # Federn-Pinsel (3 Polygons)
        for offset in (-1, 0, 1):
            perp_x = math.cos(ang) * 2
            perp_y = math.sin(ang) * 2
            f_pts = [
                (tip_x - offset * 2, tip_y),
                (tip_x + perp_x - offset * 2, tip_y + perp_y),
                (tip_x - perp_x - offset * 2, tip_y - perp_y),
            ]
            col_ = feather if offset == 0 else feather_dk
            pygame.draw.polygon(surf, col_, f_pts)

    # ============================================================
    # STAFF — Front-Half + Totem-Top
    # ============================================================
    # Lederwickel-Grip
    pygame.draw.rect(surf, fur_dk,
                      (staff_x - 2, grip_y - 3, 5, 10))
    pygame.draw.rect(surf, OL,
                      (staff_x - 2, grip_y - 3, 5, 10), 1)
    for gy in (grip_y - 1, grip_y + 2, grip_y + 5):
        pygame.draw.line(surf, OL,
                          (staff_x - 2, gy),
                          (staff_x + 2, gy), 1)
    # Unterer Schaft
    pygame.draw.line(surf, wood, (staff_x, grip_y + 6),
                      (staff_x, staff_bot_y), 3)
    pygame.draw.line(surf, OL, (staff_x, grip_y + 6),
                      (staff_x, staff_bot_y), 1)
    pygame.draw.line(surf, wood_lt, (staff_x - 1, grip_y + 7),
                      (staff_x - 1, staff_bot_y - 1), 1)
    # Totem-Top — kleiner Schaedel
    skull_y = staff_top_y - 4
    pygame.draw.circle(surf, bone, (staff_x, skull_y), 5)
    pygame.draw.circle(surf, OL, (staff_x, skull_y), 5, 1)
    pygame.draw.circle(surf, OL, (staff_x - 1, skull_y - 1), 1)
    pygame.draw.circle(surf, OL, (staff_x + 1, skull_y - 1), 1)
    pygame.draw.line(surf, OL,
                      (staff_x - 2, skull_y + 2),
                      (staff_x + 2, skull_y + 2), 1)
    # Federn unter Schaedel
    for offset in (-3, 0, 3):
        pygame.draw.line(surf, feather,
                          (staff_x + offset, staff_top_y),
                          (staff_x + offset, staff_top_y + 6), 1)

    return surf


def _gen_warlock_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #204: Detail-Warlock — dunkler Sorcerer, Skull-Crown,
    Schwarze Robe mit Bone-Trim, Wand mit Skull. Boese Mage-Variante.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    robe       = (32, 24, 38)
    robe_lt    = (62, 50, 78)
    robe_dk    = (16, 12, 22)
    robe_blk   = (10, 8, 14)
    trim       = color
    trim_lt    = _shade(color, 1.35)
    skin       = (188, 168, 168)        # blass-grau
    skin_sh    = (138, 118, 122)
    bone       = (218, 210, 188)
    bone_dk    = (158, 148, 118)
    eye        = glow_col
    eye_dk     = _shade(glow_col, 0.55)
    OL         = (4, 4, 8)

    if walk_frame == 1:
        sway = -1
        wand_pulse = 1
    elif walk_frame == 3:
        sway = 1
        wand_pulse = 1
    else:
        sway = 0
        wand_pulse = 0

    # ============================================================
    # WAND — Back-Half (wenn rechte Hand vorn)
    # Skull-Wand in der rechten Hand
    # ============================================================
    wand_x = cx + 20
    wand_top_y = fy - 70
    wand_bot_y = fy - 30
    pygame.draw.line(surf, robe_dk, (wand_x, wand_top_y),
                      (wand_x, wand_bot_y - 6), 2)
    pygame.draw.line(surf, OL, (wand_x, wand_top_y),
                      (wand_x, wand_bot_y - 6), 1)

    # ============================================================
    # ROBE-SKIRT (lang, dunkel, mit Bone-Saum)
    # ============================================================
    skirt_top = fy - 44
    skirt_bot = fy - 2
    skirt_pts = [
        (cx - 18, skirt_top),
        (cx + 18, skirt_top),
        (cx + 22, skirt_bot - 6),
        (cx + 16, skirt_bot - 1),
        (cx + 8, skirt_bot),
        (cx, skirt_bot - 2),
        (cx - 8, skirt_bot),
        (cx - 16, skirt_bot - 1),
        (cx - 22, skirt_bot - 6),
    ]
    pygame.draw.polygon(surf, robe, skirt_pts)
    pygame.draw.polygon(surf, OL, skirt_pts, 2)
    # Falten
    for fx_ in (cx - 13, cx - 6, cx, cx + 6, cx + 13):
        pygame.draw.line(surf, robe_dk,
                          (fx_, skirt_top + 2),
                          (fx_, skirt_bot - 4), 1)
    # Highlight links
    pygame.draw.line(surf, robe_lt,
                      (cx - 17, skirt_top + 3),
                      (cx - 20, skirt_bot - 8), 1)
    # Bone-Akzente am Saum (mini-Schaedel-Symbole)
    for bx in (cx - 12, cx, cx + 12):
        pygame.draw.circle(surf, bone, (bx, skirt_bot - 8), 2)
        pygame.draw.circle(surf, OL, (bx, skirt_bot - 8), 2, 1)
        pygame.draw.circle(surf, OL, (bx - 1, skirt_bot - 9), 1)
        pygame.draw.circle(surf, OL, (bx + 1, skirt_bot - 9), 1)
    # Trim-Linie
    pygame.draw.line(surf, trim,
                      (cx - 17, skirt_top + 1),
                      (cx + 17, skirt_top + 1), 1)

    # ============================================================
    # TORSO — schmaler dunkler Robe-Oberteil
    # ============================================================
    torso_top = fy - 66
    torso_bot = fy - 44
    torso_pts = [
        (cx - 11, torso_top),
        (cx + 11, torso_top),
        (cx + 14, torso_top + 4),
        (cx + 17, torso_top + 12),
        (cx + 18, torso_bot),
        (cx - 18, torso_bot),
        (cx - 17, torso_top + 12),
        (cx - 14, torso_top + 4),
    ]
    pygame.draw.polygon(surf, robe, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Vertikal-Naht
    pygame.draw.line(surf, robe_dk, (cx, torso_top), (cx, torso_bot), 1)
    # V-Kragen (trim)
    pygame.draw.polygon(surf, trim, [
        (cx - 7, torso_top + 1),
        (cx + 7, torso_top + 1),
        (cx, torso_top + 8),
    ])
    pygame.draw.polygon(surf, OL, [
        (cx - 7, torso_top + 1),
        (cx + 7, torso_top + 1),
        (cx, torso_top + 8),
    ], 1)
    # Highlight
    pygame.draw.line(surf, robe_lt,
                      (cx - 12, torso_top + 4),
                      (cx - 16, torso_top + 16), 1)

    # ============================================================
    # SLEEVES — wide, mit Bone-Cuff
    # ============================================================
    arm_top = torso_top + 8
    sleeve_l_pts = [
        (cx - 18, arm_top - 1 + sway),
        (cx - 14, arm_top + 1 + sway),
        (cx - 16, arm_top + 16 + sway),
        (cx - 21, arm_top + 14 + sway),
    ]
    pygame.draw.polygon(surf, robe, sleeve_l_pts)
    pygame.draw.polygon(surf, OL, sleeve_l_pts, 1)
    pygame.draw.line(surf, robe_lt,
                      (cx - 20, arm_top + sway),
                      (cx - 20, arm_top + 13 + sway), 1)
    # Bone-Cuff
    pygame.draw.line(surf, bone,
                      (cx - 21, arm_top + 13 + sway),
                      (cx - 15, arm_top + 16 + sway), 2)
    # Klauen-Hand
    pygame.draw.circle(surf, skin,
                        (cx - 18, arm_top + 18 + sway), 3)
    pygame.draw.circle(surf, OL,
                        (cx - 18, arm_top + 18 + sway), 3, 1)
    # Lange Naegel
    for fx_, fy_ in ((-2, 4), (-1, 5), (0, 5), (1, 4)):
        pygame.draw.line(surf, bone,
                          (cx - 18 + fx_, arm_top + 18 + sway),
                          (cx - 18 + fx_, arm_top + 18 + sway + fy_), 1)

    # Rechter Aermel (haelt Wand)
    sleeve_r_pts = [
        (cx + 14, arm_top - 1 - sway),
        (cx + 18, arm_top + 1 - sway),
        (cx + 21, arm_top + 14 - sway),
        (cx + 16, arm_top + 16 - sway),
    ]
    pygame.draw.polygon(surf, robe, sleeve_r_pts)
    pygame.draw.polygon(surf, OL, sleeve_r_pts, 1)
    pygame.draw.line(surf, bone,
                      (cx + 16, arm_top + 16 - sway),
                      (cx + 21, arm_top + 13 - sway), 2)
    # Hand am Wand-Grip
    pygame.draw.circle(surf, skin,
                        (cx + 19, arm_top + 18 - sway), 3)
    pygame.draw.circle(surf, OL,
                        (cx + 19, arm_top + 18 - sway), 3, 1)
    for fx_, fy_ in ((-2, 4), (-1, 5), (0, 5), (1, 4)):
        pygame.draw.line(surf, bone,
                          (cx + 19 + fx_, arm_top + 18 - sway),
                          (cx + 19 + fx_, arm_top + 18 - sway + fy_), 1)

    # ============================================================
    # NECKLACE — Knochen-Kette mit Schaedel-Anhaenger
    # ============================================================
    for cy_ in range(torso_top - 2, torso_top + 10, 2):
        pygame.draw.circle(surf, bone_dk, (cx, cy_), 1)
    pygame.draw.circle(surf, bone, (cx, torso_top + 12), 3)
    pygame.draw.circle(surf, OL, (cx, torso_top + 12), 3, 1)
    pygame.draw.circle(surf, OL, (cx - 1, torso_top + 11), 1)
    pygame.draw.circle(surf, OL, (cx + 1, torso_top + 11), 1)

    # ============================================================
    # NECK + HEAD — pale, sunken
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 3, 2, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    head_cx = cx
    head_cy = torso_top - 10
    # Pale Skin
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 9)
    pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 8)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 9, 2)
    # Highlight
    pygame.draw.circle(surf, (218, 200, 200), (head_cx - 3, head_cy - 4), 2)
    # Sunken Augenringe
    pygame.draw.arc(surf, eye_dk,
                     (head_cx - 6, head_cy - 1, 6, 4),
                     0, math.pi, 1)
    pygame.draw.arc(surf, eye_dk,
                     (head_cx, head_cy - 1, 6, 4),
                     0, math.pi, 1)
    # Augen — tief, gluehend
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 2)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 2)
    pygame.draw.circle(surf, eye, (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, eye, (head_cx + 3, head_cy - 1), 1)
    # Outer-Glow
    glow_layer = pygame.Surface((12, 6), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_layer, (*eye, 120), (0, 0, 12, 6))
    surf.blit(glow_layer, (head_cx - 9, head_cy - 4))
    surf.blit(glow_layer, (head_cx - 3, head_cy - 4))
    # Augenbrauen (boese, steil)
    pygame.draw.line(surf, OL,
                      (head_cx - 6, head_cy - 4),
                      (head_cx - 1, head_cy - 2), 2)
    pygame.draw.line(surf, OL,
                      (head_cx + 1, head_cy - 2),
                      (head_cx + 6, head_cy - 4), 2)
    # Nase (schmal, scharf)
    pygame.draw.line(surf, skin_sh,
                      (head_cx, head_cy + 1),
                      (head_cx, head_cy + 4), 1)
    # Mund (schmal)
    pygame.draw.line(surf, OL,
                      (head_cx - 2, head_cy + 5),
                      (head_cx + 2, head_cy + 5), 1)

    # ============================================================
    # SKULL-CROWN — Knochen-Diadem mit Hoernern
    # ============================================================
    # Schaedel-Front (Mini-Schaedel auf der Stirn)
    pygame.draw.polygon(surf, bone, [
        (head_cx - 4, head_cy - 8),
        (head_cx - 5, head_cy - 12),
        (head_cx - 2, head_cy - 14),
        (head_cx + 2, head_cy - 14),
        (head_cx + 5, head_cy - 12),
        (head_cx + 4, head_cy - 8),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx - 4, head_cy - 8),
        (head_cx - 5, head_cy - 12),
        (head_cx - 2, head_cy - 14),
        (head_cx + 2, head_cy - 14),
        (head_cx + 5, head_cy - 12),
        (head_cx + 4, head_cy - 8),
    ], 1)
    # Augen-Loecher im Crown-Skull
    pygame.draw.circle(surf, OL, (head_cx - 2, head_cy - 11), 1)
    pygame.draw.circle(surf, OL, (head_cx + 2, head_cy - 11), 1)
    # Horns aus den Seiten der Krone
    pygame.draw.polygon(surf, robe_dk, [
        (head_cx - 5, head_cy - 11),
        (head_cx - 8, head_cy - 17),
        (head_cx - 6, head_cy - 13),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx - 5, head_cy - 11),
        (head_cx - 8, head_cy - 17),
        (head_cx - 6, head_cy - 13),
    ], 1)
    pygame.draw.polygon(surf, robe_dk, [
        (head_cx + 5, head_cy - 11),
        (head_cx + 8, head_cy - 17),
        (head_cx + 6, head_cy - 13),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx + 5, head_cy - 11),
        (head_cx + 8, head_cy - 17),
        (head_cx + 6, head_cy - 13),
    ], 1)
    # Hood-Cape hinter dem Kopf
    hood_back_pts = [
        (head_cx - 11, head_cy + 4),
        (head_cx - 10, head_cy - 6),
        (head_cx - 5, head_cy - 8),
        (head_cx + 5, head_cy - 8),
        (head_cx + 10, head_cy - 6),
        (head_cx + 11, head_cy + 4),
        (head_cx + 8, head_cy + 6),
        (head_cx - 8, head_cy + 6),
    ]
    # Render hinter dem Kopf — Layering-Trick: zuerst hinten, dann
    # Kopf drueber. Aber wir haben Kopf schon gezeichnet. Cape geht
    # nach unten / aussen — daher Hood-Seitenfluegel
    pygame.draw.polygon(surf, robe_dk, hood_back_pts)
    pygame.draw.polygon(surf, OL, hood_back_pts, 2)
    # Re-Render Skin im inneren (Kopf wieder sichtbar)
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)

    # ============================================================
    # WAND — Front-Half + Glow-Skull am Top
    # ============================================================
    wand_x = cx + 20
    wand_top_y = fy - 70
    wand_bot_y = fy - 30
    pygame.draw.line(surf, robe_dk, (wand_x, wand_bot_y - 6),
                      (wand_x, wand_bot_y), 2)
    pygame.draw.line(surf, OL, (wand_x, wand_bot_y - 6),
                      (wand_x, wand_bot_y), 1)
    # Skull am Wand-Top
    pygame.draw.circle(surf, bone, (wand_x, wand_top_y), 4)
    pygame.draw.circle(surf, OL, (wand_x, wand_top_y), 4, 1)
    pygame.draw.circle(surf, OL, (wand_x - 1, wand_top_y - 1), 1)
    pygame.draw.circle(surf, OL, (wand_x + 1, wand_top_y - 1), 1)
    pygame.draw.line(surf, OL,
                      (wand_x - 2, wand_top_y + 2),
                      (wand_x + 2, wand_top_y + 2), 1)
    # Glow am Skull-Top
    for r_, a_ in ((6, 60), (5, 100), (4, 160 + wand_pulse * 40)):
        glow_l = pygame.Surface((r_ * 2 + 2, r_ * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_l, (*eye, a_), (r_ + 1, r_ + 1), r_)
        surf.blit(glow_l, (wand_x - r_ - 1, wand_top_y - r_ - 1))
    pygame.draw.circle(surf, eye, (wand_x, wand_top_y - 6), 2)
    pygame.draw.circle(surf, (255, 255, 255), (wand_x - 1, wand_top_y - 7), 1)

    return surf


def _gen_lurker_sprite(color, glow_col, walk_frame=0) -> pygame.Surface:
    """Update #204: Detail-Lurker — Stealth-Assassin, schmale Silhouette,
    Twin-Daggers, dunkle Kapuze + Mask.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    cloak       = (22, 22, 30)
    cloak_lt    = (52, 52, 70)
    cloak_dk    = (10, 10, 16)
    leather     = (42, 32, 24)
    leather_lt  = (78, 60, 42)
    skin        = (132, 102, 88)         # dunkel-getoent
    skin_sh     = (92, 72, 60)
    metal       = (162, 165, 172)
    metal_lt    = (215, 220, 228)
    metal_dk    = (78, 82, 90)
    blood       = (138, 32, 32)
    eye         = glow_col
    OL          = (4, 4, 6)

    if walk_frame == 1:
        l_dy, r_dy = -2, 1
        crouch = 1
    elif walk_frame == 3:
        l_dy, r_dy = 1, -2
        crouch = 1
    else:
        l_dy, r_dy = 0, 0
        crouch = 0

    # ============================================================
    # BOOTS — schmal, leise
    # ============================================================
    boot_l = pygame.Rect(cx - 11, fy - 5 + l_dy, 9, 5)
    pygame.draw.rect(surf, cloak_dk, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    boot_r = pygame.Rect(cx + 2, fy - 5 + r_dy, 9, 5)
    pygame.draw.rect(surf, cloak_dk, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)

    # ============================================================
    # LEGS — schlanke schwarze Hose
    # ============================================================
    leg_l = pygame.Rect(cx - 10, fy - 22 + l_dy, 7, 17)
    pygame.draw.rect(surf, cloak, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    pygame.draw.line(surf, cloak_lt,
                      (leg_l.x + 1, leg_l.y + 1),
                      (leg_l.x + 1, leg_l.bottom - 2), 1)
    # Knee-Strap
    pygame.draw.line(surf, leather,
                      (leg_l.x - 1, leg_l.y + 5),
                      (leg_l.right + 1, leg_l.y + 5), 1)
    leg_r = pygame.Rect(cx + 3, fy - 22 + r_dy, 7, 17)
    pygame.draw.rect(surf, cloak, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)
    pygame.draw.line(surf, cloak_lt,
                      (leg_r.x + 1, leg_r.y + 1),
                      (leg_r.x + 1, leg_r.bottom - 2), 1)
    pygame.draw.line(surf, leather,
                      (leg_r.x - 1, leg_r.y + 5),
                      (leg_r.right + 1, leg_r.y + 5), 1)

    # ============================================================
    # TORSO — schmal (slender assassin)
    # ============================================================
    torso_top = fy - 62 + crouch
    torso_bot = fy - 22
    torso_pts = [
        (cx - 10, torso_top + 2),
        (cx - 8, torso_top),
        (cx + 8, torso_top),
        (cx + 10, torso_top + 2),
        (cx + 13, torso_top + 14),
        (cx + 12, torso_bot),
        (cx - 12, torso_bot),
        (cx - 13, torso_top + 14),
    ]
    pygame.draw.polygon(surf, cloak, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Cross-Straps (X ueber Brust mit Dolch-Halftern)
    pygame.draw.line(surf, leather,
                      (cx - 10, torso_top + 4),
                      (cx + 8, torso_top + 16), 2)
    pygame.draw.line(surf, leather,
                      (cx + 10, torso_top + 4),
                      (cx - 8, torso_top + 16), 2)
    pygame.draw.line(surf, leather_lt,
                      (cx - 9, torso_top + 5),
                      (cx + 7, torso_top + 15), 1)
    # Holfter-Dolche (kleine Linien an den Cross-Straps)
    pygame.draw.line(surf, metal,
                      (cx - 9, torso_top + 12),
                      (cx - 7, torso_top + 18), 1)
    pygame.draw.line(surf, metal,
                      (cx + 9, torso_top + 12),
                      (cx + 7, torso_top + 18), 1)

    # Belt
    belt_y = torso_bot - 4
    pygame.draw.rect(surf, leather, (cx - 13, belt_y, 26, 4))
    pygame.draw.rect(surf, OL, (cx - 13, belt_y, 26, 4), 1)
    # Wurf-Messer am Belt (3 Klingen)
    for kx in (cx - 8, cx - 4, cx + 8):
        pygame.draw.line(surf, metal,
                          (kx, belt_y),
                          (kx, belt_y - 2), 1)
        pygame.draw.circle(surf, metal_lt, (kx, belt_y - 3), 1)

    # ============================================================
    # ARMS — schmal, in Action-Pose (Daggers gezogen)
    # ============================================================
    arm_top = torso_top + 6
    # Linker Arm — ausgestreckt
    arm_l = pygame.Rect(cx - 16, arm_top, 4, 12)
    pygame.draw.rect(surf, cloak, arm_l)
    pygame.draw.rect(surf, OL, arm_l, 1)
    # Bracer
    pygame.draw.rect(surf, leather,
                      (arm_l.x - 1, arm_l.bottom - 4, 6, 4))
    pygame.draw.rect(surf, OL,
                      (arm_l.x - 1, arm_l.bottom - 4, 6, 4), 1)
    # Hand mit Dolch
    pygame.draw.circle(surf, skin,
                        (arm_l.centerx, arm_l.bottom + 2), 2)
    pygame.draw.circle(surf, OL,
                        (arm_l.centerx, arm_l.bottom + 2), 2, 1)

    # Rechter Arm
    arm_r = pygame.Rect(cx + 12, arm_top, 4, 12)
    pygame.draw.rect(surf, cloak, arm_r)
    pygame.draw.rect(surf, OL, arm_r, 1)
    pygame.draw.rect(surf, leather,
                      (arm_r.x, arm_r.bottom - 4, 6, 4))
    pygame.draw.rect(surf, OL,
                      (arm_r.x, arm_r.bottom - 4, 6, 4), 1)
    pygame.draw.circle(surf, skin,
                        (arm_r.centerx + 1, arm_r.bottom + 2), 2)
    pygame.draw.circle(surf, OL,
                        (arm_r.centerx + 1, arm_r.bottom + 2), 2, 1)

    # ============================================================
    # TWIN DAGGERS — eine in jeder Hand, mit Reverse-Grip
    # ============================================================
    # Linker Dolch — Klinge ZURUECK gehalten (assassin reverse-grip)
    dx_l = arm_l.centerx
    dy_l = arm_l.bottom + 3
    # Klinge geht NACH OBEN/AUSSEN
    blade_l_pts = [
        (dx_l, dy_l - 2),
        (dx_l + 1, dy_l - 2),
        (dx_l + 1, dy_l - 12),
        (dx_l - 1, dy_l - 14),
    ]
    pygame.draw.polygon(surf, metal, blade_l_pts)
    pygame.draw.polygon(surf, OL, blade_l_pts, 1)
    pygame.draw.line(surf, metal_lt,
                      (dx_l, dy_l - 3),
                      (dx_l, dy_l - 12), 1)
    # Grip
    pygame.draw.rect(surf, leather,
                      (dx_l - 1, dy_l - 1, 3, 4))
    pygame.draw.rect(surf, OL,
                      (dx_l - 1, dy_l - 1, 3, 4), 1)
    # Blut-Spitze
    pygame.draw.line(surf, blood,
                      (dx_l - 1, dy_l - 13),
                      (dx_l - 1, dy_l - 11), 1)

    # Rechter Dolch — gleiche Pose, Spiegel
    dx_r = arm_r.centerx + 1
    dy_r = arm_r.bottom + 3
    blade_r_pts = [
        (dx_r - 1, dy_r - 2),
        (dx_r, dy_r - 2),
        (dx_r, dy_r - 12),
        (dx_r + 2, dy_r - 14),
    ]
    pygame.draw.polygon(surf, metal, blade_r_pts)
    pygame.draw.polygon(surf, OL, blade_r_pts, 1)
    pygame.draw.line(surf, metal_lt,
                      (dx_r, dy_r - 3),
                      (dx_r, dy_r - 12), 1)
    pygame.draw.rect(surf, leather,
                      (dx_r - 1, dy_r - 1, 3, 4))
    pygame.draw.rect(surf, OL,
                      (dx_r - 1, dy_r - 1, 3, 4), 1)
    pygame.draw.line(surf, blood,
                      (dx_r + 1, dy_r - 13),
                      (dx_r + 1, dy_r - 11), 1)

    # ============================================================
    # HOOD + MASK
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 9
    # Hood-Cowl (eng anliegend)
    hood_pts = [
        (head_cx - 11, torso_top + 4),
        (head_cx - 11, head_cy - 3),
        (head_cx - 7, head_cy - 10),
        (head_cx - 2, head_cy - 12),
        (head_cx + 2, head_cy - 12),
        (head_cx + 7, head_cy - 10),
        (head_cx + 11, head_cy - 3),
        (head_cx + 11, torso_top + 4),
        (head_cx + 6, head_cy + 3),
        (head_cx + 7, head_cy - 4),
        (head_cx + 3, head_cy - 7),
        (head_cx - 3, head_cy - 7),
        (head_cx - 7, head_cy - 4),
        (head_cx - 6, head_cy + 3),
    ]
    pygame.draw.polygon(surf, cloak_dk, hood_pts)
    pygame.draw.polygon(surf, OL, hood_pts, 2)
    # Hood-Highlight
    pygame.draw.line(surf, cloak_lt,
                      (head_cx - 9, head_cy - 3),
                      (head_cx - 6, head_cy - 9), 1)
    # Face-Mask (dunkler Stoff, deckt Mund + Nase)
    mask_pts = [
        (head_cx - 6, head_cy - 1),
        (head_cx + 6, head_cy - 1),
        (head_cx + 5, head_cy + 6),
        (head_cx - 5, head_cy + 6),
    ]
    pygame.draw.polygon(surf, leather, mask_pts)
    pygame.draw.polygon(surf, OL, mask_pts, 1)
    # Mask-Streifen (subtle)
    pygame.draw.line(surf, leather_lt,
                      (head_cx - 5, head_cy + 1),
                      (head_cx + 5, head_cy + 1), 1)
    # Skin-Streifen ueber dem Mask (Augenpartie)
    pygame.draw.rect(surf, skin,
                      (head_cx - 6, head_cy - 3, 12, 2))
    pygame.draw.rect(surf, OL,
                      (head_cx - 6, head_cy - 3, 12, 2), 1)
    # Augen — gluehende Schlitze
    pygame.draw.rect(surf, OL,
                      (head_cx - 5, head_cy - 3, 4, 2))
    pygame.draw.rect(surf, OL,
                      (head_cx + 1, head_cy - 3, 4, 2))
    pygame.draw.circle(surf, eye, (head_cx - 3, head_cy - 2), 1)
    pygame.draw.circle(surf, eye, (head_cx + 3, head_cy - 2), 1)
    # Outer-Glow
    glow_l = pygame.Surface((8, 4), pygame.SRCALPHA)
    pygame.draw.ellipse(glow_l, (*eye, 100), (0, 0, 8, 4))
    surf.blit(glow_l, (head_cx - 7, head_cy - 4))
    surf.blit(glow_l, (head_cx - 1, head_cy - 4))

    # Hood-Spitze nach hinten (verlaengert)
    pygame.draw.polygon(surf, cloak_dk, [
        (head_cx - 6, head_cy - 10),
        (head_cx + 2, head_cy - 14),
        (head_cx - 2, head_cy - 8),
    ])
    pygame.draw.polygon(surf, OL, [
        (head_cx - 6, head_cy - 10),
        (head_cx + 2, head_cy - 14),
        (head_cx - 2, head_cy - 8),
    ], 1)

    return surf


_MOB_DETAIL_GENERATORS = {
    'skeleton':  _gen_skeleton_sprite,
    'zombie':    _gen_zombie_sprite,
    'demon':     _gen_demon_sprite,
    'brute':     _gen_brute_sprite,
    'wraith':    _gen_wraith_sprite,
    'archer':    _gen_archer_sprite,
    'berserker': _gen_berserker_sprite,
    'slime':     _gen_slime_sprite,
    'shaman':    _gen_shaman_sprite,
    'warlock':   _gen_warlock_sprite,
    'lurker':    _gen_lurker_sprite,
}


def _draw_mob_scaled(drawer, screen, e, sx, sy, scale: float = 1.7):
    """Update #201: Wrapper der einen Mob in Offscreen-Buffer rendert,
    auf `scale` hochskaliert und mit Foot-Anchor auf `sy` blittet.

    Update #202: Wenn fuer `e.type_key` ein Detail-Generator existiert,
    wird stattdessen direkt das gecachte 84x124-Sprite geblittet (kein
    Scaling, schaerfer). Fallback ist der alte scaled Iso-Pfad.

    State-Mutation in den Drawern (e.walk_phase += ...) passiert normal
    da der Drawer einmal pro Frame aufgerufen wird, gleiche Frequenz
    wie vorher.
    """
    # Update #202: Detail-Sprite-Pfad
    detail = _get_mob_sprite(
        getattr(e, 'type_key', ''),
        tuple(e.color),
        tuple(getattr(e, 'glow', (255, 80, 80))),
        int(getattr(e, 'walk_phase', 0)) % 4,
    )
    if detail is not None:
        # walk_phase fuer naechsten Frame inkrementieren
        e.walk_phase = getattr(e, 'walk_phase', 0) + 0.12
        # hit_flash-Tint
        if getattr(e, 'hit_flash', 0) > 0:
            flash = pygame.Surface(detail.get_size(), pygame.SRCALPHA)
            flash.fill((255, 255, 255, int(160 * e.hit_flash)))
            tmp = detail.copy()
            tmp.blit(flash, (0, 0),
                      special_flags=pygame.BLEND_RGBA_MULT)
            screen.blit(tmp, (sx - PROC_SPRITE_W // 2,
                               sy - PROC_SPRITE_FOOT_Y))
        else:
            screen.blit(detail, (sx - PROC_SPRITE_W // 2,
                                  sy - PROC_SPRITE_FOOT_Y))
        return

    # Fallback: Scaled Iso-Drawer Pfad fuer alle anderen Mobs
    buf_w = max(48, int(e.radius * 4 + 28))
    buf_h = max(60, int(e.height + 28))
    buf_cx = buf_w // 2
    buf_fy = buf_h - 14
    buf = pygame.Surface((buf_w, buf_h), pygame.SRCALPHA)
    drawer(buf, e, buf_cx, buf_fy)
    new_w = int(buf_w * scale)
    new_h = int(buf_h * scale)
    try:
        scaled = pygame.transform.smoothscale(buf, (new_w, new_h))
    except (pygame.error, ValueError):
        scaled = pygame.transform.scale(buf, (new_w, new_h))
    blit_x = sx - new_w // 2
    blit_y = sy - int(buf_fy * scale)
    screen.blit(scaled, (blit_x, blit_y))


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
        # Bosse bleiben native rendered (sind schon detailliert + haben FX)
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
        # Update #193 (User-Fix "Salzhuter schaut noch gleich aus"):
        # Bestiary-spezifische Drawer haben Vorrang vor base_type — damit
        # Mini-Bosses wie Salzhueter-Brut sich von generischen brutes
        # optisch abheben (Salz-Patina, verwitterte Ruestung, etc.).
        bestiary_drawer = _BESTIARY_SPECIFIC_DRAWERS.get(bestiary_key)
        if bestiary_drawer is not None:
            drawer = bestiary_drawer
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
        # Update #201: Render mob in einen Offscreen-Buffer, dann hoch-
        # skalieren — Mobs nicht winzig neben dem Player-Sprite. Bestehende
        # 12 Iso-Drawer unveraendert.
        # Update #203 (User „Mobs+Player zu gross"): Scale 1.7 → 1.4, passend
        # zum auf 0.82x verkleinerten Player (PROC_SPRITE_SCALE) — Mobs
        # bleiben proportional, aber die ganze Szene wird kompakter/luftiger.
        _draw_mob_scaled(drawer, screen, e, sx, sy, scale=1.4)

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


def _draw_salzhueter_brut_iso(screen, e, sx, sy):
    """Update #193: Salzhueter-Brut — Hafenwache des Velharner Tores.

    Lore: war einst Wache, wurde im Goetterkrieg ueberrannt, niemand kam zur
    Abloesung — wartet immer noch.  Visuell:
      - verwitterte Bronze-Ruestung (gruene Salz-Patina-Oxidation)
      - Salzkristall-Encrustation auf Schultern und Helm
      - rissiger Helm mit Gravur ueber dem Gesicht (Velharner Wache-Wappen)
      - schwerer Hellebarden-Speer statt Axt (Hafenwachen-Waffe)
      - leuchtende Augen-Schlitze durch das geschlossene Visier
    """
    color = _tint(e.color, e.hit_flash)
    h = e.height
    body_top = sy - h
    e.walk_phase += 0.04  # langsam, schwer

    # Massive Beine in verwitterter Schienenbein-Ruestung
    lo, ro = _leg_bob(e.walk_phase)
    armor_dark = _shade(color, 0.45)
    armor_mid = _shade(color, 0.65)
    for side, off in ((-1, lo), (1, ro)):
        x = sx + side * 7
        # Schienbein
        pygame.draw.rect(screen, armor_dark,
                          (x - 5, sy - 12 + off, 10, 12))
        pygame.draw.rect(screen, BLACK,
                          (x - 5, sy - 12 + off, 10, 12), 1)
        # Knie-Cap
        pygame.draw.rect(screen, armor_mid,
                          (x - 5, sy - 12 + off, 10, 3))

    # Riesiger Rumpf — Brustpanzer mit Salzkristall-Verkrustung
    chest_pts = [
        (sx - 16, sy - 12), (sx + 16, sy - 12),
        (sx + 12, body_top + 16), (sx - 12, body_top + 16),
    ]
    pygame.draw.polygon(screen, color, chest_pts)
    pygame.draw.polygon(screen, BLACK, chest_pts, 2)
    # Brustplatte mit Wappen-Linie (Velharner Hafentor)
    pygame.draw.line(screen, armor_dark,
                      (sx, sy - 12), (sx, body_top + 18), 2)
    pygame.draw.polygon(screen, armor_mid, [
        (sx - 5, body_top + 22), (sx + 5, body_top + 22),
        (sx + 3, body_top + 30), (sx - 3, body_top + 30),
    ], 1)
    # Salz-Patina-Streifen (gruene Oxidation Vertical)
    for k in (-10, -4, 4, 10):
        pygame.draw.line(screen, (140, 175, 150),
                          (sx + k, body_top + 18), (sx + k, sy - 14), 1)
    # Guertel mit Niete
    pygame.draw.rect(screen, (75, 60, 40), (sx - 14, sy - 12, 28, 4))
    for nx in (-9, -3, 3, 9):
        pygame.draw.circle(screen, (180, 165, 130),
                            (sx + nx, sy - 10), 1)

    # Massive Schultern mit Salzkristall-Encrustation
    for side in (-1, 1):
        sx_sh = sx + side * 16
        sy_sh = body_top + 16
        pygame.draw.circle(screen, _shade(color, 0.6),
                            (sx_sh, sy_sh), 6)
        pygame.draw.circle(screen, BLACK, (sx_sh, sy_sh), 6, 1)
        # 3 Salzkristalle als Spikes pro Schulter (helle Kristall-Farbe)
        crystal_col = (235, 240, 230)
        crystal_dark = (190, 195, 185)
        for k, (dx, dy) in enumerate([(-3, -4), (0, -5), (3, -4)]):
            cx, cy = sx_sh + dx, sy_sh + dy
            spike = [
                (cx, cy - 3),
                (cx + 2, cy),
                (cx, cy + 1),
                (cx - 2, cy),
            ]
            pygame.draw.polygon(screen, crystal_col, spike)
            pygame.draw.polygon(screen, crystal_dark, spike, 1)

    # Helm mit geschlossenem Visier — Velharner Hafen-Wache
    head_y = body_top + 10
    helm_col = _shade(color, 0.75)
    # Helm-Schaedel (eckig statt rund — Plattenhelm)
    helm_pts = [
        (sx - 6, head_y - 4), (sx + 6, head_y - 4),
        (sx + 7, head_y + 3), (sx + 5, head_y + 6),
        (sx - 5, head_y + 6), (sx - 7, head_y + 3),
    ]
    pygame.draw.polygon(screen, helm_col, helm_pts)
    pygame.draw.polygon(screen, BLACK, helm_pts, 1)
    # Helm-Kamm (vertikaler Grat)
    pygame.draw.line(screen, _shade(helm_col, 1.3),
                      (sx, head_y - 4), (sx, head_y + 2), 1)
    # Augen-Schlitz: schmaler horizontaler Spalt mit Glow
    pygame.draw.rect(screen, BLACK, (sx - 4, head_y, 8, 2))
    # Leuchtende Augen im Schlitz (Lore: noch nicht ganz tot)
    pygame.draw.circle(screen, e.glow, (sx - 2, head_y + 1), 1)
    pygame.draw.circle(screen, e.glow, (sx + 2, head_y + 1), 1)
    # Salz-Verkrustung am Helm-Rand
    for dx in (-6, -3, 3, 6):
        pygame.draw.circle(screen, (220, 225, 215),
                            (sx + dx, head_y + 6), 1)

    # Hellebarde (Hafenwache-Stangenwaffe) — laenger als die alte Axt
    pole_top_x = sx + 18
    pole_top_y = body_top - 14
    pole_bot_x = sx + 14
    pole_bot_y = sy - 4
    pygame.draw.line(screen, (90, 65, 35),
                      (pole_bot_x, pole_bot_y),
                      (pole_top_x, pole_top_y), 3)
    # Spitze + Beil-Blatt (Hellebarde-Klassisch)
    blade_pts = [
        (pole_top_x, pole_top_y - 6),       # Spitze
        (pole_top_x + 7, pole_top_y - 3),   # Beil-Auswurf
        (pole_top_x + 9, pole_top_y + 4),   # Beil-Unterkante
        (pole_top_x + 2, pole_top_y + 2),
    ]
    pygame.draw.polygon(screen, (200, 200, 185), blade_pts)
    pygame.draw.polygon(screen, BLACK, blade_pts, 1)
    # Salz-Patina auf der Klinge (Verwitterung)
    pygame.draw.line(screen, (160, 180, 165),
                      (pole_top_x + 1, pole_top_y - 1),
                      (pole_top_x + 6, pole_top_y + 2), 1)


# Registry: Mappt Bestiary-Keys auf spezialisierte Drawer-Funktionen.
# Eintrag hat Vorrang vor base_type-Drawer.  Default-Mob ohne Eintrag
# faellt auf type_key-Mapping zurueck (zombie/brute/etc.).
_BESTIARY_SPECIFIC_DRAWERS = {
    'salzhueter_brut': _draw_salzhueter_brut_iso,
}


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


_NPC_SPRITE_CACHE: dict = {}


def _gen_npc_sprite(kind: str, color) -> pygame.Surface:
    """NPC-Sprite-Generator (Update #200) — gleiche 84x124-Canvas wie
    der Player, deutlich detaillierter als das alte 38-px-Strichmaennchen.
    Jeder Kind hat distinct Klamotten + Akzente.

    Kinds: vendor / smith / mystic / stash / innkeeper / quest.
    """
    W, H = PROC_SPRITE_W, PROC_SPRITE_H
    surf = pygame.Surface((W, H), pygame.SRCALPHA)
    cx = W // 2
    fy = PROC_SPRITE_FOOT_Y

    # --- Gemeinsame Palette ---
    base       = color
    base_lt    = _shade(color, 1.22)
    base_dk    = _shade(color, 0.62)
    base_blk   = _shade(color, 0.38)
    skin       = (218, 178, 138)
    skin_sh    = (172, 132, 96)
    skin_hl    = (240, 200, 158)
    leather    = (72, 50, 32)
    leather_lt = (122, 88, 56)
    leather_dk = (42, 30, 18)
    bone       = (218, 210, 178)
    metal      = (162, 165, 172)
    metal_lt   = (215, 220, 228)
    metal_dk   = (95, 100, 108)
    cloth_wht  = (228, 218, 195)
    hair_brn   = (78, 52, 32)
    hair_gry   = (180, 175, 160)
    OL         = (12, 10, 8)

    # ============================================================
    # GEMEINSAME UNTERTEILE (Boots + Legs)
    # ============================================================
    # Boots
    boot_l = pygame.Rect(cx - 12, fy - 6, 10, 6)
    pygame.draw.rect(surf, leather, boot_l)
    pygame.draw.rect(surf, OL, boot_l, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_l.x + 1, boot_l.y + 1),
                      (boot_l.right - 2, boot_l.y + 1), 1)
    boot_r = pygame.Rect(cx + 2, fy - 6, 10, 6)
    pygame.draw.rect(surf, leather, boot_r)
    pygame.draw.rect(surf, OL, boot_r, 1)
    pygame.draw.line(surf, leather_lt,
                      (boot_r.x + 1, boot_r.y + 1),
                      (boot_r.right - 2, boot_r.y + 1), 1)
    # Beine (kurz, dunkel)
    leg_l = pygame.Rect(cx - 11, fy - 14, 8, 9)
    pygame.draw.rect(surf, base_dk, leg_l)
    pygame.draw.rect(surf, OL, leg_l, 1)
    leg_r = pygame.Rect(cx + 3, fy - 14, 8, 9)
    pygame.draw.rect(surf, base_dk, leg_r)
    pygame.draw.rect(surf, OL, leg_r, 1)

    # ============================================================
    # SKIRT/ROBE-UNTERTEIL (lang je nach kind)
    # ============================================================
    if kind in ('mystic', 'stash'):
        # Lange Robe bis Boden
        skirt_top = fy - 40
        skirt_bot = fy - 2
        skirt_pts = [
            (cx - 17, skirt_top),
            (cx + 17, skirt_top),
            (cx + 20, skirt_bot - 6),
            (cx + 14, skirt_bot),
            (cx + 5, skirt_bot - 2),
            (cx - 5, skirt_bot - 2),
            (cx - 14, skirt_bot),
            (cx - 20, skirt_bot - 6),
        ]
        pygame.draw.polygon(surf, base, skirt_pts)
        pygame.draw.polygon(surf, OL, skirt_pts, 2)
        # Falten
        for fx_ in (cx - 12, cx - 6, cx, cx + 6, cx + 12):
            pygame.draw.line(surf, base_dk,
                              (fx_, skirt_top + 2),
                              (fx_, skirt_bot - 4), 1)
        pygame.draw.line(surf, base_lt,
                          (cx - 16, skirt_top + 3),
                          (cx - 18, skirt_bot - 8), 1)
    else:
        # Kurzer Rock / Tunika
        skirt_top = fy - 32
        skirt_bot = fy - 14
        skirt_pts = [
            (cx - 16, skirt_top),
            (cx + 16, skirt_top),
            (cx + 16, skirt_bot - 2),
            (cx + 10, skirt_bot),
            (cx + 4, skirt_bot - 2),
            (cx - 4, skirt_bot - 2),
            (cx - 10, skirt_bot),
            (cx - 16, skirt_bot - 2),
        ]
        pygame.draw.polygon(surf, base, skirt_pts)
        pygame.draw.polygon(surf, OL, skirt_pts, 2)
        for fx_ in (cx - 11, cx - 4, cx + 4, cx + 11):
            pygame.draw.line(surf, base_dk,
                              (fx_, skirt_top + 1),
                              (fx_, skirt_bot - 2), 1)

    # ============================================================
    # TORSO
    # ============================================================
    torso_top = fy - 62
    if kind in ('mystic', 'stash'):
        torso_bot = fy - 40
    else:
        torso_bot = fy - 32
    torso_pts = [
        (cx - 12, torso_top + 2),
        (cx - 10, torso_top),
        (cx + 10, torso_top),
        (cx + 12, torso_top + 2),
        (cx + 16, torso_top + 14),
        (cx + 15, torso_bot),
        (cx - 15, torso_bot),
        (cx - 16, torso_top + 14),
    ]
    pygame.draw.polygon(surf, base, torso_pts)
    pygame.draw.polygon(surf, OL, torso_pts, 2)
    # Brust-Highlight links
    pygame.draw.polygon(surf, base_lt, [
        (cx - 9, torso_top + 3),
        (cx - 2, torso_top + 4),
        (cx - 4, torso_top + 18),
        (cx - 13, torso_top + 16),
    ])

    # ============================================================
    # KIND-SPECIFIC OVERLAYS — Apron, Belt, Markings
    # ============================================================
    if kind == 'smith':
        # Heavy Leather-Apron ueber dem Torso
        apron_pts = [
            (cx - 12, torso_top + 8),
            (cx + 12, torso_top + 8),
            (cx + 14, torso_bot),
            (cx + 12, fy - 16),
            (cx - 12, fy - 16),
            (cx - 14, torso_bot),
        ]
        pygame.draw.polygon(surf, leather, apron_pts)
        pygame.draw.polygon(surf, OL, apron_pts, 2)
        # Apron-Schmutz/Brand-Flecken
        pygame.draw.circle(surf, leather_dk, (cx - 4, torso_top + 18), 2)
        pygame.draw.circle(surf, leather_dk, (cx + 5, torso_bot - 4), 2)
        pygame.draw.circle(surf, leather_dk, (cx + 8, fy - 20), 1)
        # Schultergurte (X-Cross über die Brust)
        pygame.draw.line(surf, leather_dk,
                          (cx - 10, torso_top + 4),
                          (cx + 10, torso_top + 10), 2)
        pygame.draw.line(surf, leather_dk,
                          (cx + 10, torso_top + 4),
                          (cx - 10, torso_top + 10), 2)
        # Stahl-Nieten
        for nx, ny in ((cx - 9, torso_top + 12),
                        (cx + 9, torso_top + 12),
                        (cx, fy - 17)):
            pygame.draw.circle(surf, metal, (nx, ny), 1)
            pygame.draw.circle(surf, OL, (nx, ny), 1, 1)

    elif kind == 'vendor':
        # Klamotten-Akzente: V-Kragen + Brust-Knopfleiste
        # V-Kragen (Gold)
        pygame.draw.polygon(surf, (210, 170, 80), [
            (cx - 6, torso_top + 1),
            (cx + 6, torso_top + 1),
            (cx, torso_top + 8),
        ])
        pygame.draw.polygon(surf, OL, [
            (cx - 6, torso_top + 1),
            (cx + 6, torso_top + 1),
            (cx, torso_top + 8),
        ], 1)
        # Knöpfe in Mittellinie
        for by in (torso_top + 12, torso_top + 18, torso_top + 24):
            pygame.draw.circle(surf, (210, 170, 80), (cx, by), 1)
            pygame.draw.circle(surf, OL, (cx, by), 1, 1)

    elif kind == 'mystic':
        # Schaerpe + Sigil
        sash_y = torso_bot - 6
        pygame.draw.rect(surf, base_blk, (cx - 16, sash_y, 32, 4))
        pygame.draw.rect(surf, OL, (cx - 16, sash_y, 32, 4), 1)
        # Aspekt-Sigil (zentral)
        pygame.draw.circle(surf, base_lt, (cx, sash_y + 2), 3)
        pygame.draw.circle(surf, OL, (cx, sash_y + 2), 3, 1)
        pygame.draw.line(surf, base_blk, (cx, sash_y),
                          (cx, sash_y + 4), 1)

    elif kind == 'stash':
        # Custos-Riemen (Cross-Strap mit Schluessel)
        pygame.draw.line(surf, leather,
                          (cx - 12, torso_top + 4),
                          (cx + 8, torso_bot - 2), 3)
        pygame.draw.line(surf, leather_dk,
                          (cx - 12, torso_top + 4),
                          (cx + 8, torso_bot - 2), 1)
        # Schluessel-Bund
        key_x, key_y = cx + 6, torso_bot - 4
        pygame.draw.circle(surf, metal, (key_x, key_y), 2)
        pygame.draw.circle(surf, OL, (key_x, key_y), 2, 1)
        pygame.draw.line(surf, metal,
                          (key_x, key_y + 2),
                          (key_x + 3, key_y + 5), 1)
        pygame.draw.line(surf, metal,
                          (key_x + 3, key_y + 4),
                          (key_x + 4, key_y + 5), 1)

    elif kind == 'innkeeper':
        # Apron — heller Stoff ueber den Torso/Skirt
        apron_pts = [
            (cx - 10, torso_top + 10),
            (cx + 10, torso_top + 10),
            (cx + 12, torso_bot),
            (cx + 10, fy - 18),
            (cx - 10, fy - 18),
            (cx - 12, torso_bot),
        ]
        pygame.draw.polygon(surf, cloth_wht, apron_pts)
        pygame.draw.polygon(surf, OL, apron_pts, 2)
        pygame.draw.line(surf, (180, 170, 145),
                          (cx - 9, torso_top + 11),
                          (cx - 11, fy - 20), 1)
        # Apron-Schleife
        pygame.draw.line(surf, base_dk,
                          (cx - 10, torso_top + 12),
                          (cx + 10, torso_top + 12), 1)

    elif kind == 'quest':
        # Vest-Look mit Knopf-Reihe
        for by in range(torso_top + 6, torso_bot - 2, 4):
            pygame.draw.circle(surf, (180, 150, 80), (cx, by), 1)
            pygame.draw.circle(surf, OL, (cx, by), 1, 1)
        # Schulter-Akzent (Vest-Border)
        pygame.draw.line(surf, base_blk,
                          (cx - 11, torso_top + 1),
                          (cx - 13, torso_bot - 2), 2)
        pygame.draw.line(surf, base_blk,
                          (cx + 11, torso_top + 1),
                          (cx + 13, torso_bot - 2), 2)

    # ============================================================
    # BELT (alle kinds, ausser mystic/stash die Schaerpe haben)
    # ============================================================
    if kind not in ('mystic',):
        belt_y = torso_bot - 4
        pygame.draw.rect(surf, leather_dk, (cx - 16, belt_y, 32, 4))
        pygame.draw.rect(surf, OL, (cx - 16, belt_y, 32, 4), 1)
        pygame.draw.line(surf, leather_lt,
                          (cx - 15, belt_y + 1),
                          (cx + 14, belt_y + 1), 1)
        # Buckle
        pygame.draw.rect(surf, (180, 150, 80),
                          (cx - 3, belt_y - 1, 6, 6))
        pygame.draw.rect(surf, OL,
                          (cx - 3, belt_y - 1, 6, 6), 1)

    # ============================================================
    # ARMS / SLEEVES
    # ============================================================
    arm_top = torso_top + 6
    if kind == 'smith':
        # Bare Arms (muscular)
        arm_l = pygame.Rect(cx - 18, arm_top, 5, 16)
        pygame.draw.rect(surf, skin, arm_l)
        pygame.draw.rect(surf, OL, arm_l, 1)
        pygame.draw.line(surf, skin_hl,
                          (arm_l.x + 1, arm_l.y + 1),
                          (arm_l.x + 1, arm_l.bottom - 2), 1)
        arm_r = pygame.Rect(cx + 13, arm_top, 5, 16)
        pygame.draw.rect(surf, skin, arm_r)
        pygame.draw.rect(surf, OL, arm_r, 1)
        # Soot-Streifen
        pygame.draw.line(surf, leather_dk,
                          (arm_l.x + 1, arm_l.y + 8),
                          (arm_l.right - 1, arm_l.y + 9), 1)
    else:
        # Aermel (gleiche Robe-Farbe)
        arm_l = pygame.Rect(cx - 18, arm_top, 5, 13)
        pygame.draw.rect(surf, base, arm_l)
        pygame.draw.rect(surf, OL, arm_l, 1)
        pygame.draw.line(surf, base_lt,
                          (arm_l.x + 1, arm_l.y + 1),
                          (arm_l.x + 1, arm_l.bottom - 2), 1)
        # Cuff
        pygame.draw.rect(surf, base_dk,
                          (arm_l.x - 1, arm_l.bottom - 3, 7, 3))
        pygame.draw.rect(surf, OL,
                          (arm_l.x - 1, arm_l.bottom - 3, 7, 3), 1)
        # Hand
        pygame.draw.circle(surf, skin,
                            (arm_l.centerx, arm_l.bottom + 2), 2)
        pygame.draw.circle(surf, OL,
                            (arm_l.centerx, arm_l.bottom + 2), 2, 1)

        arm_r = pygame.Rect(cx + 13, arm_top, 5, 13)
        pygame.draw.rect(surf, base, arm_r)
        pygame.draw.rect(surf, OL, arm_r, 1)
        pygame.draw.line(surf, base_dk,
                          (arm_r.x + 3, arm_r.y + 1),
                          (arm_r.x + 3, arm_r.bottom - 2), 1)
        pygame.draw.rect(surf, base_dk,
                          (arm_r.x, arm_r.bottom - 3, 7, 3))
        pygame.draw.rect(surf, OL,
                          (arm_r.x, arm_r.bottom - 3, 7, 3), 1)
        pygame.draw.circle(surf, skin,
                            (arm_r.centerx, arm_r.bottom + 2), 2)
        pygame.draw.circle(surf, OL,
                            (arm_r.centerx, arm_r.bottom + 2), 2, 1)

    # ============================================================
    # NECK (kurz)
    # ============================================================
    pygame.draw.rect(surf, skin, (cx - 3, torso_top - 3, 6, 4))
    pygame.draw.rect(surf, skin_sh, (cx + 1, torso_top - 3, 2, 4))
    pygame.draw.rect(surf, OL, (cx - 3, torso_top - 3, 6, 4), 1)

    # ============================================================
    # HEAD
    # ============================================================
    head_cx = cx
    head_cy = torso_top - 10
    # Skin
    pygame.draw.circle(surf, skin, (head_cx, head_cy), 8)
    pygame.draw.circle(surf, skin_sh, (head_cx + 1, head_cy + 1), 7)
    pygame.draw.circle(surf, skin, (head_cx - 1, head_cy - 1), 6)
    pygame.draw.circle(surf, OL, (head_cx, head_cy), 8, 1)
    pygame.draw.circle(surf, skin_hl, (head_cx - 3, head_cy - 3), 2)

    # Augen
    pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 1)
    pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 1)
    # Nase
    pygame.draw.line(surf, skin_sh,
                      (head_cx, head_cy + 1),
                      (head_cx, head_cy + 3), 1)
    # Mund
    pygame.draw.line(surf, leather_dk,
                      (head_cx - 2, head_cy + 5),
                      (head_cx + 2, head_cy + 5), 1)

    # ============================================================
    # KIND-SPECIFIC HEAD-FEATURES
    # ============================================================
    if kind == 'vendor':
        # Korven Vor: Glatze + voller Bart
        # Bart
        beard_pts = [
            (head_cx - 5, head_cy + 4),
            (head_cx + 5, head_cy + 4),
            (head_cx + 4, head_cy + 8),
            (head_cx + 1, head_cy + 11),
            (head_cx - 1, head_cy + 11),
            (head_cx - 4, head_cy + 8),
        ]
        pygame.draw.polygon(surf, hair_brn, beard_pts)
        pygame.draw.polygon(surf, OL, beard_pts, 1)
        # Schnauzer
        pygame.draw.line(surf, hair_brn,
                          (head_cx - 4, head_cy + 4),
                          (head_cx + 4, head_cy + 4), 2)
        # Buschige Augenbrauen
        pygame.draw.line(surf, hair_brn,
                          (head_cx - 5, head_cy - 3),
                          (head_cx - 2, head_cy - 2), 2)
        pygame.draw.line(surf, hair_brn,
                          (head_cx + 2, head_cy - 2),
                          (head_cx + 5, head_cy - 3), 2)

    elif kind == 'smith':
        # Otreth Hohlauge: kurzes Haar, Augenklappe (rechtes Auge)
        # Haar oben
        pygame.draw.polygon(surf, hair_brn, [
            (head_cx - 6, head_cy - 5),
            (head_cx - 7, head_cy - 8),
            (head_cx + 7, head_cy - 8),
            (head_cx + 6, head_cy - 5),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx - 6, head_cy - 5),
            (head_cx - 7, head_cy - 8),
            (head_cx + 7, head_cy - 8),
            (head_cx + 6, head_cy - 5),
        ], 1)
        # Augenklappe (rechts) + Riemen
        eye_patch = pygame.Rect(head_cx + 1, head_cy - 3, 5, 4)
        pygame.draw.rect(surf, leather_dk, eye_patch)
        pygame.draw.rect(surf, OL, eye_patch, 1)
        pygame.draw.line(surf, leather_dk,
                          (head_cx + 6, head_cy - 1),
                          (head_cx + 8, head_cy - 5), 1)
        # Bartlinien
        pygame.draw.line(surf, hair_brn,
                          (head_cx - 4, head_cy + 4),
                          (head_cx + 4, head_cy + 4), 1)
        pygame.draw.line(surf, hair_brn,
                          (head_cx - 3, head_cy + 6),
                          (head_cx + 3, head_cy + 6), 1)

    elif kind == 'mystic':
        # Mara die Mahnerin: lange Haare + Hood-Andeutung
        # Lange Haare hinten/seitlich
        hair_pts = [
            (head_cx - 8, head_cy - 4),
            (head_cx - 9, head_cy + 4),
            (head_cx - 6, head_cy + 12),
            (head_cx + 6, head_cy + 12),
            (head_cx + 9, head_cy + 4),
            (head_cx + 8, head_cy - 4),
            (head_cx + 4, head_cy - 8),
            (head_cx - 4, head_cy - 8),
        ]
        pygame.draw.polygon(surf, base_dk, hair_pts)
        pygame.draw.polygon(surf, OL, hair_pts, 1)
        # Hood oben (klein, mystisch)
        hood_pts = [
            (head_cx - 8, head_cy - 4),
            (head_cx - 6, head_cy - 11),
            (head_cx + 6, head_cy - 11),
            (head_cx + 8, head_cy - 4),
        ]
        pygame.draw.polygon(surf, base_blk, hood_pts)
        pygame.draw.polygon(surf, OL, hood_pts, 1)
        # Re-render Skin + Augen on top (haare verdecken sonst Gesicht)
        pygame.draw.circle(surf, skin, (head_cx, head_cy + 1), 6)
        pygame.draw.circle(surf, OL, (head_cx, head_cy + 1), 6, 1)
        # Augen + Mund
        pygame.draw.circle(surf, OL, (head_cx - 2, head_cy), 1)
        pygame.draw.circle(surf, OL, (head_cx + 2, head_cy), 1)
        pygame.draw.line(surf, leather_dk,
                          (head_cx - 1, head_cy + 4),
                          (head_cx + 1, head_cy + 4), 1)
        # Stirn-Sigil
        pygame.draw.circle(surf, base_lt,
                            (head_cx, head_cy - 4), 1)

    elif kind == 'stash':
        # Mahnmal-Verwahrer: Tonsur (kahler Scheitel, Haar-Kranz)
        # Haar-Kranz (laterale Streifen)
        pygame.draw.polygon(surf, hair_gry, [
            (head_cx - 8, head_cy - 2),
            (head_cx - 8, head_cy - 6),
            (head_cx - 5, head_cy - 8),
            (head_cx - 5, head_cy - 4),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx - 8, head_cy - 2),
            (head_cx - 8, head_cy - 6),
            (head_cx - 5, head_cy - 8),
            (head_cx - 5, head_cy - 4),
        ], 1)
        pygame.draw.polygon(surf, hair_gry, [
            (head_cx + 5, head_cy - 8),
            (head_cx + 8, head_cy - 6),
            (head_cx + 8, head_cy - 2),
            (head_cx + 5, head_cy - 4),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx + 5, head_cy - 8),
            (head_cx + 8, head_cy - 6),
            (head_cx + 8, head_cy - 2),
            (head_cx + 5, head_cy - 4),
        ], 1)
        # Tonsur-Linie hinten
        pygame.draw.arc(surf, hair_gry,
                         (head_cx - 6, head_cy - 9, 12, 6),
                         math.pi, 2 * math.pi, 1)

    elif kind == 'innkeeper':
        # Tameris: Haar zusammengebunden, Bandana
        # Bandana ueber dem Kopf
        bandana_pts = [
            (head_cx - 7, head_cy - 4),
            (head_cx + 7, head_cy - 4),
            (head_cx + 6, head_cy - 8),
            (head_cx - 6, head_cy - 8),
        ]
        pygame.draw.polygon(surf, (180, 80, 60), bandana_pts)
        pygame.draw.polygon(surf, OL, bandana_pts, 1)
        pygame.draw.line(surf, (140, 60, 40),
                          (head_cx - 6, head_cy - 5),
                          (head_cx + 6, head_cy - 5), 1)
        # Bandana-Knoten links
        pygame.draw.polygon(surf, (180, 80, 60), [
            (head_cx - 7, head_cy - 7),
            (head_cx - 11, head_cy - 5),
            (head_cx - 9, head_cy - 3),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx - 7, head_cy - 7),
            (head_cx - 11, head_cy - 5),
            (head_cx - 9, head_cy - 3),
        ], 1)
        # Haar-Strands seitlich
        pygame.draw.line(surf, hair_brn,
                          (head_cx - 8, head_cy - 2),
                          (head_cx - 8, head_cy + 4), 2)
        pygame.draw.line(surf, hair_brn,
                          (head_cx + 8, head_cy - 2),
                          (head_cx + 8, head_cy + 4), 2)
        # Sommersprossen + freundlicher Mund (Smile)
        pygame.draw.circle(surf, skin_sh, (head_cx - 4, head_cy + 2), 1)
        pygame.draw.circle(surf, skin_sh, (head_cx + 4, head_cy + 2), 1)

    elif kind == 'quest':
        # Stadtsprecher Eldon: grauer Bart, Brille, Hut?
        # Kurzes Haar
        pygame.draw.polygon(surf, hair_gry, [
            (head_cx - 6, head_cy - 4),
            (head_cx - 7, head_cy - 7),
            (head_cx + 7, head_cy - 7),
            (head_cx + 6, head_cy - 4),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx - 6, head_cy - 4),
            (head_cx - 7, head_cy - 7),
            (head_cx + 7, head_cy - 7),
            (head_cx + 6, head_cy - 4),
        ], 1)
        # Brille (2 Kreise mit Steg)
        pygame.draw.circle(surf, OL, (head_cx - 3, head_cy - 1), 2, 1)
        pygame.draw.circle(surf, OL, (head_cx + 3, head_cy - 1), 2, 1)
        pygame.draw.line(surf, OL,
                          (head_cx - 1, head_cy - 1),
                          (head_cx + 1, head_cy - 1), 1)
        # Grauer Schnurrbart
        pygame.draw.line(surf, hair_gry,
                          (head_cx - 4, head_cy + 3),
                          (head_cx + 4, head_cy + 3), 2)
        # Ziegenbart
        pygame.draw.polygon(surf, hair_gry, [
            (head_cx - 2, head_cy + 5),
            (head_cx + 2, head_cy + 5),
            (head_cx, head_cy + 9),
        ])
        pygame.draw.polygon(surf, OL, [
            (head_cx - 2, head_cy + 5),
            (head_cx + 2, head_cy + 5),
            (head_cx, head_cy + 9),
        ], 1)

    return surf


def _get_npc_sprite(kind, color):
    """Cache-Wrapper fuer NPC-Sprites (Update #203: auf PROC_SPRITE_SCALE
    herunterskaliert, konsistent mit Player/Klassen-Sprites)."""
    key = (kind, tuple(color))
    cached = _NPC_SPRITE_CACHE.get(key)
    if cached is None:
        cached = _scale_proc(_gen_npc_sprite(kind, color))
        if len(_NPC_SPRITE_CACHE) > 64:
            _NPC_SPRITE_CACHE.clear()
        _NPC_SPRITE_CACHE[key] = cached
    return cached


def draw_npc_at(screen, npc, sx, sy):
    """Stadt-NPC: detailliertes 84x124-Sprite (Update #200, vorher 38px).

    Update #135 (O-22): Pro NPC-Kind eine Idle-Fidget-Animation (Hammer,
    Buch, etc.) bleibt erhalten — rendered on top des Cache-Sprites.

    Trigger pro NPC: `npc._fidget_t` zaehlt rueckwaerts; bei <=0 wird
    eine 0.8 s Idle-Anim ausgeloest.  Anim-Dauer in `npc._fidget_left`.
    """
    import math
    sx, sy = int(sx), int(sy)
    # Update #200: Silhouette-Shadow statt einfaches Oval
    sprite = _get_npc_sprite(npc.kind, npc.color)
    _silhouette_shadow(screen, sprite, sx, sy + 2,
                        target_w=int(sprite.get_width() * 0.85),
                        alpha=110, squash_y=0.32)
    color = npc.color
    # Bob (Atmen)
    npc.bob += 0.04
    bob = math.sin(npc.bob) * 1.5
    # Blit-Position mit Foot-Anchor sy + Bob-Offset (skalierte Groesse)
    screen.blit(sprite,
                (sx - sprite.get_width() // 2,
                 sy - PROC_DRAW_FOOT_Y + int(bob)))
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
        # Default-Fidget pro Kind
        DEFAULT_FIDGETS = {
            'smith':     'hammer',
            'vendor':    'count_coin',
            'mystic':    'page_flip',
            'innkeeper': 'wipe',
            'quest':     'gesture',
            'stash':     'inspect',
        }
        npc._fidget_kind = DEFAULT_FIDGETS.get(npc.kind, 'gesture')
    body_top = sy - 70   # an neue 84x124-Skala angepasst (vorher -38)
    # Update #135 (O-22): NPC-Idle-Fidget-Animation pro Kind, weiter
    # rendered on top des Cache-Sprites. Positions an neue Skala angepasst.
    if getattr(npc, '_fidget_left', 0) > 0:
        f_t = 1.0 - (npc._fidget_left / 0.9)
        fk = getattr(npc, '_fidget_kind', None)
        hand_y = sy - 38 + int(bob)   # rechts neben Body (Belt-Hoehe)
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
