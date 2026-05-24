"""Velgrad Render-Spec — Single Source of Truth fuer Asset-Render-Konvention.

Verankert pro Asset-Kategorie:
  - Camera-Angle (Top-Down ARPG / Cinematic / Head&Shoulders / Orthographic)
  - Distance (full body / upper body / no subject)
  - Resolution (Source-PNG-Size)
  - BG-Policy (transparent / vignette / atmospheric / seamless)
  - Engine-Render-Target-Size (target_h-Multiplier oder fixed)

Wird verwendet von:
  - tools/sprite_gen.py + workflow_*.py (Prompt-Komposition + Resolution)
  - sf/sprites.py (target_h-Multiplier fuer Engine-Render)
  - tools/asset_audit.py (Spec-Compliance-Check)

Doku: VELGRAD_RENDER_SPEC.md
"""
from __future__ import annotations


# ============================================================
# MASTER-STYLE (POE2 Dark Fantasy painterly, alle Kategorien)
# ============================================================
MASTER_POSITIVE = (
    'path of exile 2 style, dark fantasy painterly artwork, gothic medieval, '
    'volumetric lighting, dramatic chiaroscuro, hyperdetailed concept art, '
    'muted desaturated palette with selective color accents, weathered textures, '
    'realistic-stylized proportions, ArtStation trending, Greg Rutkowski composition, '
    'moody atmosphere, grimdark fantasy, intricate armor details, leather and iron, '
    '8k quality, sharp focus'
)

MASTER_NEGATIVE = (
    'cartoon, anime, chibi, cel-shaded, low-poly, pixel art, MS Paint, '
    'bright cheerful colors, saturated colors, modern clothing, sci-fi, neon, '
    'deformed anatomy, extra limbs, mutated, blurry, jpeg artifacts, watermark, '
    'text, signature, logo, ugly, low quality, amateur, child-like style'
)


# ============================================================
# CATEGORY-SPECS — die zentrale Tabelle
# ============================================================
# Jede Kategorie hat:
#   camera_prompt:    Kamera-Winkel-Beschreibung
#   distance_prompt:  Subjekt-Distanz-Beschreibung
#   bg_prompt:        BG-Beschreibung (was im Hintergrund passieren soll)
#   negative_extra:   Zusaetzliche Negatives spezifisch fuer diese Kategorie
#   resolution:       (width, height) der Source-PNG
#   bg_policy:        'transparent' | 'vignette' | 'atmospheric' | 'seamless' | 'opaque'
#   target_h_mult:    Engine-Render: target_height = entity.radius * mult (None falls fix)
#   aspect_tolerance: Erlaubte Abweichung vom expected aspect (0.05 = 5%)
RENDER_SPEC: dict[str, dict] = {
    # ============================================================
    # Player Classes — Static (in-world Render + Title-Screen Verwendung)
    # ============================================================
    'class': {
        'camera_prompt': (
            '3/4 top-down ARPG view, camera slightly elevated looking down, '
            'character oriented south facing the camera with body angled '
            'naturally toward viewer, sprite-ready composition'
        ),
        'distance_prompt': (
            'isolated full-body hero, full body visible head to toe, centered '
            'subject, ~10% padding above and below'
        ),
        'bg_prompt': (
            'on plain pure-black background, no environment, no scenery behind'
        ),
        'negative_extra': '',
        'resolution': (512, 768),
        'bg_policy': 'transparent',
        'target_h_mult': 6.0,            # 18 * 6.0 = 108px in-game
        'aspect_tolerance': 0.05,
    },
    # ============================================================
    # Player Animation-Frames (gleicher Stil, Direction + Phase variieren)
    # ============================================================
    'class_anim_frame': {
        # Wird vom Workflow generiert, der pro Frame eigenen Phase-Prompt hat.
        # Camera/Distance/BG identisch zu class.
        'camera_prompt': (
            '3/4 top-down ARPG view, camera slightly elevated looking down, '
            'character oriented [DIRECTION], sprite-ready composition'
        ),
        'distance_prompt': (
            'isolated full-body hero, full body visible head to toe, centered, '
            'single frame in animation cycle'
        ),
        'bg_prompt': (
            'on plain pure-black background, no environment'
        ),
        'negative_extra': (
            'multiple characters, group shot, environment, background scene, '
            'cropped, partial body'
        ),
        # Resolution pro Frame nach 8-Frame-Strip: 313×627. Strip ist 2504×627.
        'resolution': (2504, 627),       # gesamter Strip (8 Frames horizontal)
        'frame_resolution': (313, 627),  # einzelner Frame
        'bg_policy': 'transparent',
        'target_h_mult': 6.0,
        'aspect_tolerance': 0.05,
    },
    # ============================================================
    # Mob (in-world Render, kleinere Cell-Size als Player)
    # ============================================================
    'mob': {
        'camera_prompt': (
            '3/4 top-down ARPG view, camera slightly elevated, full-body '
            'creature, top-down hero shot angle, sprite-ready composition'
        ),
        'distance_prompt': (
            'isolated full-body creature, centered subject, ~10% padding'
        ),
        'bg_prompt': (
            'on plain pure-black background, no environment behind, '
            'no scenery'
        ),
        'negative_extra': '',
        'resolution': (512, 512),
        'bg_policy': 'transparent',
        'target_h_mult': 2.5,            # 14-50 radius → 35-125px
        'aspect_tolerance': 0.05,
    },
    # ============================================================
    # Boss Plate (Cinematic-Intro Modal)
    # ============================================================
    'boss_plate': {
        'camera_prompt': (
            'cinematic dark fantasy boss render, intimidating angle, '
            'dramatic atmospheric lighting, hero-shot composition'
        ),
        'distance_prompt': (
            'full-body boss centered, ~5% padding, dynamic pose'
        ),
        'bg_prompt': (
            'atmospheric background showing boss arena setting, Lore-mood '
            'consistent with boss biome'
        ),
        'negative_extra': '',
        'resolution': (512, 512),
        'bg_policy': 'atmospheric',
        'target_h_mult': None,           # Modal-fuellend (drawn ~600px central)
        'aspect_tolerance': 0.05,
    },
    # ============================================================
    # Portrait (NPC-Dialog-UI, head&shoulders)
    # ============================================================
    'portrait': {
        'camera_prompt': (
            'head and shoulders portrait, frontal eye-contact composition, '
            'upper body and face visible, painterly POE2 style'
        ),
        'distance_prompt': (
            'head and shoulders only, focus on face and upper torso, '
            'centered composition'
        ),
        'bg_prompt': (
            'simple dark vignette gradient behind subject, no detailed '
            'environment, soft dark atmospheric backdrop'
        ),
        'negative_extra': (
            'full body, bottom half visible, environment, complex background'
        ),
        'resolution': (256, 256),
        'bg_policy': 'vignette',
        'target_h_mult': None,           # Fixed ~128×128 in Dialog
        'aspect_tolerance': 0.05,
    },
    # ============================================================
    # Tile (Boden-Material, KEIN Subjekt)
    # ============================================================
    'tile': {
        'camera_prompt': (
            'completely flat top-down orthographic view straight down from '
            'above, no perspective, no depth'
        ),
        'distance_prompt': (
            'seamless repeating tileable ground texture, uniform floor '
            'pattern only, edges loop perfectly, no central focal point, '
            'repeatable game-map tile, pure flat ground material'
        ),
        'bg_prompt': (
            'no environment beyond the tile itself, no walls, no architecture'
        ),
        'negative_extra': (
            'walls, pillars, arches, columns, buildings, scenery, horizon, '
            'perspective, depth, sky, character, person, creature, archway, '
            'ruins, statue, doorway, room, sunbeams, god rays'
        ),
        'resolution': (512, 512),
        'bg_policy': 'seamless',
        'target_h_mult': None,           # Scaled zu cell+1 px
        'aspect_tolerance': 0.02,        # strikter (Tile muss quadratisch sein)
    },
    # ============================================================
    # Tile Wall (Wand-Material, gleiche Convention)
    # ============================================================
    'tile_wall': {
        'camera_prompt': (
            'top-down orthographic wall surface texture, viewed from above '
            'looking down on the wall top'
        ),
        'distance_prompt': (
            'seamless tileable wall material, dense stone/masonry pattern, '
            'edges loop, no perspective'
        ),
        'bg_prompt': (
            'wall material fills entire surface, no environment beyond'
        ),
        'negative_extra': (
            'character, person, perspective, depth, sky, horizon, '
            'environment, sunbeams'
        ),
        'resolution': (512, 512),
        'bg_policy': 'seamless',
        'target_h_mult': None,
        'aspect_tolerance': 0.02,
    },
    # ============================================================
    # Item-Icon (Inventar-UI)
    # ============================================================
    'item_icon': {
        'camera_prompt': (
            'frontal isolated weapon view with slight 3D-twist for depth, '
            'item-card style, sprite-ready'
        ),
        'distance_prompt': (
            'single weapon centered, full object visible, ~10% padding'
        ),
        'bg_prompt': (
            'pure-black background, no environment, item-card composition'
        ),
        'negative_extra': (
            'multiple items, environment, character holding the weapon, '
            'scenery'
        ),
        'resolution': (128, 128),
        'bg_policy': 'transparent',
        'target_h_mult': None,           # Fixed 32-48px in UI
        'aspect_tolerance': 0.02,
    },
    # ============================================================
    # Decor (Phase 2 — Welt-Props, geplant)
    # ============================================================
    'decor': {
        'camera_prompt': (
            '3/4 top-down ARPG view, full object centered, sprite-ready'
        ),
        'distance_prompt': (
            'isolated single prop, full object visible, ~10% padding'
        ),
        'bg_prompt': (
            'pure-black background, no environment'
        ),
        'negative_extra': (
            'character, person, multiple objects, environment, scenery'
        ),
        'resolution': (256, 256),
        'bg_policy': 'transparent',
        'target_h_mult': None,           # Decor-spezifisch (siehe entities.Decor.height)
        'aspect_tolerance': 0.10,        # Decor-Variety erlaubt etwas Flexibilitaet
    },
    # ============================================================
    # Status-Icon (HUD-Buff-Tray + Enemy-Status-Pips, Update #166)
    # ============================================================
    'status_icon': {
        'camera_prompt': (
            'frontal isolated game-ui icon, symbol-centered composition, '
            'painterly icon-card style, sprite-ready'
        ),
        'distance_prompt': (
            'single symbolic object centered, clear silhouette, '
            '~15% padding for icon-readability at small render-size'
        ),
        'bg_prompt': (
            'pure-black background, no environment, minimal background, '
            'inventory-style display'
        ),
        'negative_extra': (
            'multiple icons, character, person, environment, scenery, text, '
            'numbers, ui frame, border'
        ),
        'resolution': (64, 64),
        'bg_policy': 'transparent',
        'target_h_mult': None,           # Fixed 12px im _status_overlay
        'aspect_tolerance': 0.05,
    },
}


# ============================================================
# DIRECTION-DESCRIPTIONS — fuer Animation-Frames
# ============================================================
# Wichtig: alle 4 Directions teilen die gleiche 3/4 Top-Down Konvention.
# Reine Eye-Level Side-Views passen NICHT zum Tile-System.
DIRECTION_DESC = {
    'S':     ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented south facing the camera with body angled '
              'naturally toward viewer'),
    'down':  ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented south facing the camera with body angled '
              'naturally toward viewer'),
    'E':     ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented east (screen right) shown in three-quarter '
              'profile, not flat side view'),
    'right': ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented east (screen right) shown in three-quarter '
              'profile, not flat side view'),
    'N':     ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented north away from camera, three-quarter '
              'rear angle'),
    'up':    ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented north away from camera, three-quarter '
              'rear angle'),
    'W':     ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented west (screen left) shown in three-quarter '
              'profile, not flat side view'),
    'left':  ('3/4 top-down ARPG view, camera slightly elevated looking down, '
              'character oriented west (screen left) shown in three-quarter '
              'profile, not flat side view'),
}


# ============================================================
# PUBLIC HELPERS
# ============================================================
def get_spec(category: str) -> dict:
    """Returnt die Spec fuer eine Kategorie (oder leeres Dict)."""
    return RENDER_SPEC.get(category, {})


def get_resolution(category: str) -> tuple[int, int]:
    """Returnt die expected (width, height) der Source-PNG."""
    spec = get_spec(category)
    return spec.get('resolution', (512, 512))


def get_target_h_mult(category: str) -> float | None:
    """Returnt den target_h-Multiplier (target_h = radius * mult).
    None wenn kategorie eine fixe Render-Groesse hat (z.B. portrait, item)."""
    return get_spec(category).get('target_h_mult')


def get_bg_policy(category: str) -> str:
    """Returnt 'transparent' | 'vignette' | 'atmospheric' | 'seamless' | 'opaque'."""
    return get_spec(category).get('bg_policy', 'transparent')


def format_prompt(category: str, lore_prompt: str,
                   direction: str | None = None) -> tuple[str, str]:
    """Komponiert (positive_prompt, negative_prompt) aus Spec + Lore.

    Aufbau (positive):
      [MASTER_POSITIVE], [lore_prompt], [camera_prompt], [distance_prompt],
      [bg_prompt]

    Bei directional anims wird [DIRECTION] im camera_prompt mit der
    konkreten DIRECTION_DESC ersetzt.

    Returns:
      (positive, negative) Tupel.
    """
    spec = get_spec(category)
    if not spec:
        # Fallback: nur master + lore
        return (
            f'{MASTER_POSITIVE}, {lore_prompt}',
            MASTER_NEGATIVE,
        )
    camera = spec.get('camera_prompt', '')
    if direction and '[DIRECTION]' in camera:
        camera = camera.replace('[DIRECTION]', DIRECTION_DESC.get(direction, ''))
    distance = spec.get('distance_prompt', '')
    bg = spec.get('bg_prompt', '')
    neg_extra = spec.get('negative_extra', '')

    pos_parts = [MASTER_POSITIVE, lore_prompt, camera, distance, bg]
    positive = ', '.join(p.strip() for p in pos_parts if p and p.strip())

    if neg_extra:
        negative = f'{MASTER_NEGATIVE}, {neg_extra}'
    else:
        negative = MASTER_NEGATIVE
    return positive, negative


def validate_resolution(category: str, w: int, h: int) -> bool:
    """True wenn (w, h) zur Spec passt (innerhalb aspect-tolerance)."""
    spec = get_spec(category)
    exp_w, exp_h = spec.get('resolution', (0, 0))
    if exp_w == 0 or exp_h == 0:
        return True  # keine Spec → keine Validation
    if w == exp_w and h == exp_h:
        return True
    # Aspect-Check
    expected_aspect = exp_w / exp_h
    actual_aspect = w / max(1, h)
    tol = spec.get('aspect_tolerance', 0.05)
    return abs(expected_aspect - actual_aspect) / expected_aspect < tol


def categories() -> list[str]:
    """Liste aller registrierten Kategorien."""
    return list(RENDER_SPEC.keys())


# ============================================================
# CLI-Diagnose
# ============================================================
if __name__ == '__main__':
    print('Velgrad Render-Spec — Kategorien:')
    print('=' * 60)
    for cat in categories():
        spec = RENDER_SPEC[cat]
        res = spec['resolution']
        bg = spec['bg_policy']
        mult = spec.get('target_h_mult')
        print(f'  {cat:<22} {res[0]}x{res[1]:<5}  bg={bg:<12}  '
              f'target_h_mult={mult}')
    print('=' * 60)
    print('\nBeispiel-Prompt (class):')
    pos, neg = format_prompt('class', 'Warrior in iron-plate armor, wielding halberd')
    print(f'POSITIVE: {pos[:200]}...')
    print(f'NEGATIVE: {neg[:200]}...')
