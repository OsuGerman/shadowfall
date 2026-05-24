"""Aspekt-Theme-System (Update #29).

Lore-Bibel Teil 2: Die Sieben Aspekte (Kharn / Nheyra / Ousen / Valsa /
Im-Nesh / Shulavh / der Siebte). Jede Klasse ist einem Aspekt zugeordnet
(Lore-Bibel Teil 7 — Eisenwächter→Kharn, Funkengeborene→Valsa, etc.).

Dieses Modul stellt zentrale Aspekt-Theme-Farben + Glyph-Renderer bereit.
Aspekt-Farbcodierung aus `Design idee/project/velgrad-tokens.css`.
"""

import math
import pygame


# ============================================================
# Aspekt-Theme-Palette (aus velgrad-tokens.css adaptiert)
# ============================================================
# Pro Aspekt:
#   primary    — Hauptfarbe (Globe-Rim, Text-Akzent)
#   bright     — heller (Highlight, Pulse)
#   deep       — gedeckt (Schatten, Border)
#   halo       — weiches Glow-Halo
ASPECT_PALETTE = {
    'kharn':   dict(
        primary=(154, 118,  66),   # bronze-warm
        bright =(212, 168, 119),   # bronze-light + warm
        deep   =( 90,  63,  36),   # bronze-deep
        halo   =(212, 168, 119),
        domain ='Form',
    ),
    'nheyra':  dict(
        primary=( 90, 114, 138),   # steel-light
        bright =(138, 165, 192),   # bright steel
        deep   =( 31,  44,  57),   # steel-dark
        halo   =(183, 207, 227),
        domain ='Zeit',
    ),
    'ousen':   dict(
        primary=( 79, 170, 185),   # ghost
        bright =(127, 208, 220),   # ghost-bright
        deep   =(  8,  50,  58),   # ghost-deep
        halo   =(184, 236, 243),
        domain ='Geist',
    ),
    'valsa':   dict(
        primary=(200, 152,  39),   # gold
        bright =(227, 180,  64),   # gold-bright
        deep   =(106,  77,  18),   # gold-deep
        halo   =(250, 233, 176),
        domain ='Wille',
    ),
    'imnesh':  dict(
        primary=(140, 200, 100),   # Sprache-Grün
        bright =(180, 230, 130),
        deep   =( 50, 100,  40),
        halo   =(200, 240, 180),
        domain ='Sprache',
    ),
    'shulavh': dict(
        primary=(134,  69, 102),   # Shulavh-Magenta
        bright =(176, 112, 144),
        deep   =( 58,  24,  40),
        halo   =(217, 179, 197),
        domain ='Bindung',
    ),
    'hollow':  dict(
        primary=(107, 107, 107),   # Vergessen-Grau
        bright =(160, 154, 146),
        deep   =( 28,  28,  28),
        halo   =(212, 205, 193),
        domain ='Vergessen',
    ),
}

# Default-Fallback
DEFAULT_ASPECT = 'valsa'


# ============================================================
# Klasse → Aspekt-Mapping (Lore-Bibel Teil 7)
# ============================================================
CLASS_TO_ASPECT = {
    'warrior':  'kharn',     # Eisenwächter → Form
    'monk':     'imnesh',    # Stille Schritte → Sprache (still sprechen)
    'mage':     'valsa',     # Funkengeborene → Wille (Valsa)
    'witch':    'shulavh',   # Knochenwitwen → Bindung (Shulavh)
    'ranger':   'nheyra',    # Saatträgerinnen (Nheyra-Lineage)
    'rogue':    'ousen',     # Mahnmal-Söldner (Ousen-Geist)
    'huntress': 'nheyra',    # Zhar-Eth-Schwestern (Nheyra)
    'druid':    'hollow',    # Wandelnde (der Siebte / Vergessen)
}


def aspect_for_class(cls):
    """Returnt Aspekt-Key für eine Klasse."""
    return CLASS_TO_ASPECT.get(cls, DEFAULT_ASPECT)


# ============================================================
# PLAN H-03..H-10 (Update #98): Klassen-Theme-Katalog
# ============================================================
# Pro Klasse: BG-Tönung, Knoten-Form, Linien-Stil, Click-Sound-Fallback.
# Wird vom SkillTreeUI._draw_tree_tome_frame + _push_alloc_anim genutzt.
# Jedes Theme erbt vom Aspekt-Theme der Klasse (subtil), überschreibt
# aber Signature-Elemente.
CLASS_THEMES = {
    'warrior': dict(
        name='Eisenwächter — Stein & Eisen',
        bg_tint=(60, 45, 30),          # warmer Stein-Braun
        node_shape='hex',              # Hex-Runen-Stein
        node_accent=(220, 140, 60),    # orange-bronze
        line_style='chain',            # Eisen-Ketten
        keystone_color=(200, 100, 40), # Lava-Keystone
        click_sound='hit_heavy',       # Hammerschlag-Fallback
        ambience='stone_creak',
    ),
    'witch': dict(
        name='Knochenwitwen — Marmor & Gold',
        bg_tint=(28, 20, 30),          # schwarzer Marmor
        node_shape='skull',            # Schädel/Knochen
        node_accent=(220, 200, 110),   # gold
        line_style='tendril',          # Knochen-Tendrils
        keystone_color=(180, 60, 120), # Pentagramm-Magenta
        click_sound='whisper',         # Flüster-Fallback
        ambience='bone_creak',
    ),
    'mage': dict(
        name='Funkengeborene — Stained-Glass',
        bg_tint=(60, 40, 80),          # mage-purple-glas
        node_shape='gem',              # Edelstein
        node_accent=(255, 220, 100),   # element-gold
        line_style='energy',           # Energie-Linien
        keystone_color=(140, 200, 255),# Element-Cyan
        click_sound='cast_lightning',  # Chime-Fallback
        ambience='glass_chime',
    ),
    'ranger': dict(
        name='Saatträger — Waldboden',
        bg_tint=(40, 55, 30),          # Waldboden-grün
        node_shape='leaf',             # Holz-Embleme/Pfeilspitzen
        node_accent=(180, 140, 90),    # Holz-braun
        line_style='vine',             # Ranken-Linien
        keystone_color=(120, 200, 80), # Baum-Anker-grün
        click_sound='whisper',         # Wind/Vogel-Fallback
        ambience='wind_leaf',
    ),
    'monk': dict(
        name='Stille Schritte — Lotus-Mandala',
        bg_tint=(55, 45, 35),          # Pergament-warm
        node_shape='mudra',            # Kalligraphie/Mudra
        node_accent=(255, 230, 180),   # creme
        line_style='ink',              # Tinte-Striche
        keystone_color=(220, 60, 60),  # Kanji-rot
        click_sound='whisper',         # Klangschale-Fallback
        ambience='bowl_resonance',
    ),
    'druid': dict(
        name='Wandelnde — Weltbaum',
        bg_tint=(35, 45, 28),          # Mooder-tief-grün
        node_shape='totem',            # Tiergeist-Knoten
        node_accent=(160, 130, 80),    # Holz-Erd-Ton
        line_style='root',             # Wurzel-Linien
        keystone_color=(200, 160, 80), # Totem-gold
        click_sound='roar',            # Erdrumpeln-Fallback
        ambience='earth_rumble',
    ),
    'huntress': dict(
        name='Zhar-Eth Schwestern — Wüstenstein',
        bg_tint=(60, 45, 30),          # Wüstenstein-tan
        node_shape='spear',            # Speerspitze/Feder
        node_accent=(220, 180, 100),   # Sand-gold
        line_style='leather',          # Lederriemen
        keystone_color=(220, 100, 60), # Speer-Banner-orange
        click_sound='arrow_impact_1',  # Trommel-Fallback
        ambience='drum_distant',
    ),
    'rogue': dict(
        name='Mahnmal-Söldner — Eisen-Gitter',
        bg_tint=(30, 30, 35),          # Eisen-Grau-Blau
        node_shape='gear',             # Zahnrad
        node_accent=(180, 180, 200),   # Stahl
        line_style='wire',             # Draht/Lunten
        keystone_color=(255, 180, 80), # Zahnrad-Funken
        click_sound='click',           # Reload-Click-Fallback
        ambience='gear_tick',
    ),
}


def class_theme(cls):
    """Returnt das Theme-Dict für eine Klasse, mit Fallback auf valsa-Theme."""
    return CLASS_THEMES.get(cls, CLASS_THEMES['mage'])


def aspect_palette(aspect_or_class):
    """Returnt vollständige Palette dict für einen Aspekt-Key
    oder Klasse-Key (Auto-Resolve)."""
    if aspect_or_class in CLASS_TO_ASPECT:
        aspect = CLASS_TO_ASPECT[aspect_or_class]
    elif aspect_or_class in ASPECT_PALETTE:
        aspect = aspect_or_class
    else:
        aspect = DEFAULT_ASPECT
    return ASPECT_PALETTE[aspect]


def aspect_color(aspect_or_class, slot='primary'):
    """Convenience-Accessor — `slot` ∈ {primary, bright, deep, halo}."""
    pal = aspect_palette(aspect_or_class)
    return pal.get(slot, pal['primary'])


# ============================================================
# Aspekt-Glyphen (Pygame-Render aus velgrad-glyphs.jsx)
# ============================================================
def draw_glyph(screen, cx, cy, size, aspect_key, color=None):
    """Zeichnet das Aspekt-Glyph in pygame.

    Vereinfachte Pygame-Adaption der SVG-Glyphen aus velgrad-glyphs.jsx.
    size = Höhe und Breite (Glyph ist quadratisch). color = optional
    override; Default = Aspekt-Primary.
    """
    if color is None:
        color = aspect_color(aspect_key, 'bright')
    s = size / 64.0  # Skala relativ zu 64×64-Designgröße

    def pt(x, y):
        return (int(cx + (x - 32) * s), int(cy + (y - 32) * s))

    def lw(w):
        return max(1, int(w * s))

    if aspect_key == 'kharn':
        # Amboss mit Träne in der Mitte
        pts = [pt(10, 38), pt(18, 30), pt(46, 30), pt(54, 38),
               pt(48, 38), pt(48, 44), pt(16, 44), pt(16, 38)]
        pygame.draw.polygon(screen, color, pts, lw(1.5))
        pts2 = [pt(22, 30), pt(22, 22), pt(42, 22), pt(42, 30)]
        pygame.draw.lines(screen, color, False, pts2, lw(1.5))
        pygame.draw.line(screen, color, pt(26, 22), pt(26, 14), lw(1.25))
        pygame.draw.line(screen, color, pt(38, 22), pt(38, 14), lw(1.25))
        # Träne
        tear = [pt(32, 33), pt(34, 36), pt(32, 39), pt(30, 36)]
        pygame.draw.polygon(screen, color, tear)
    elif aspect_key == 'nheyra':
        # Zwei verschränkte Kreise (Zeit-Phasen)
        r = int(14 * s)
        pygame.draw.circle(screen, color, pt(25, 32), r, lw(1.25))
        pygame.draw.circle(screen, color, pt(39, 32), r, lw(1.25))
        # Stunden-Ticks
        for a_deg in (0, 45, 90, 135, 180, 225, 270, 315):
            rad = math.radians(a_deg)
            x1 = int(cx + math.cos(rad) * 18 * s)
            y1 = int(cy + math.sin(rad) * 18 * s)
            x2 = int(cx + math.cos(rad) * 21 * s)
            y2 = int(cy + math.sin(rad) * 21 * s)
            pygame.draw.line(screen, color, (x1, y1), (x2, y2), lw(1))
    elif aspect_key == 'ousen':
        # Auge mit drei Pupillen
        pygame.draw.ellipse(screen, color,
                             (pt(6, 22)[0], pt(6, 22)[1],
                              int(52 * s), int(20 * s)), lw(1.25))
        pygame.draw.circle(screen, color, (cx, cy), int(11 * s), lw(1.25))
        pygame.draw.circle(screen, color, pt(32, 27), max(1, int(2.2 * s)))
        pygame.draw.circle(screen, color, pt(28, 35), max(1, int(2.2 * s)))
        pygame.draw.circle(screen, color, pt(36, 35), max(1, int(2.2 * s)))
    elif aspect_key == 'valsa':
        # Hand greift Flamme (vereinfacht: Flamme + Hand-Linien)
        flame_pts = [pt(32, 8), pt(28, 16), pt(24, 28), pt(32, 38),
                      pt(40, 28), pt(36, 16)]
        pygame.draw.polygon(screen, color, flame_pts, lw(1.25))
        # Hand-Linien (vereinfacht zu 3 horizontalen Strichen)
        for y in (40, 44, 48):
            pygame.draw.line(screen, color, pt(20, y), pt(44, y), lw(1.25))
        # Handgelenk
        wrist = [pt(22, 52), pt(42, 52), pt(40, 56), pt(24, 56)]
        pygame.draw.polygon(screen, color, wrist, lw(1.25))
    elif aspect_key == 'imnesh':
        # Buch mit gebrochener Zunge + Streichline (exkommuniziert)
        book = [pt(10, 22), pt(32, 18), pt(54, 22),
                pt(54, 50), pt(32, 46), pt(10, 50)]
        pygame.draw.polygon(screen, color, book, lw(1.25))
        pygame.draw.line(screen, color, pt(32, 18), pt(32, 46), lw(1.25))
        # Strikethrough
        pygame.draw.line(screen, color, pt(6, 58), pt(58, 6), lw(2.5))
    elif aspect_key == 'shulavh':
        # 3 verflochtene Fäden + Knoten
        # Approximiert als 3 Bogen-Linien
        for off, op in ((16, 1.0), (32, 0.7), (48, 0.85)):
            pts = []
            for i in range(8):
                t = i / 7.0
                x = 16 + t * 32
                y = off + math.sin(t * math.pi) * (12 - off / 8)
                pts.append(pt(x, y))
            if len(pts) >= 2:
                pygame.draw.lines(screen, color, False, pts, lw(1.6))
        # Knoten in Mitte
        pygame.draw.circle(screen, color, (cx, cy), max(2, int(3 * s)))
    elif aspect_key == 'hollow':
        # Frame um Nichts
        rect = pygame.Rect(pt(14, 14)[0], pt(14, 14)[1],
                            int(36 * s), int(36 * s))
        # Gestrichelt (Pygame kann nicht direkt, machen wir mit Punkten)
        for k in range(0, int(36 * s), 6):
            pygame.draw.line(screen, color,
                              (rect.x + k, rect.y),
                              (rect.x + k + 2, rect.y), 1)
            pygame.draw.line(screen, color,
                              (rect.x + k, rect.y + rect.h),
                              (rect.x + k + 2, rect.y + rect.h), 1)
            pygame.draw.line(screen, color,
                              (rect.x, rect.y + k),
                              (rect.x, rect.y + k + 2), 1)
            pygame.draw.line(screen, color,
                              (rect.x + rect.w, rect.y + k),
                              (rect.x + rect.w, rect.y + k + 2), 1)


# ============================================================
# Filigree-Frame: 4 ornamentale Eck-Brackets (aus velgrad-glyphs.jsx)
# ============================================================
def draw_ornament_corner(screen, x, y, size, color, rotate=0):
    """Zeichnet eine ornamentale Eck-Bracket (45° L-Form + Locke).

    rotate ∈ {0, 90, 180, 270} — bestimmt welche Ecke (TL/TR/BR/BL).
    """
    s = size / 56.0  # Skala

    def map_pt(px, py):
        """Spiegel/Rotation je nach rotate-Winkel."""
        if rotate == 0:    # TL
            return (x + int(px * s), y + int(py * s))
        if rotate == 90:   # TR
            return (x + int((56 - py) * s), y + int(px * s))
        if rotate == 180:  # BR
            return (x + int((56 - px) * s), y + int((56 - py) * s))
        if rotate == 270:  # BL
            return (x + int(py * s), y + int((56 - px) * s))
        return (x + int(px * s), y + int(py * s))

    lw = max(1, int(2 * s))
    # Außen-Right-Angle
    pygame.draw.line(screen, color, map_pt(2, 2), map_pt(2, 28), lw)
    pygame.draw.line(screen, color, map_pt(2, 2), map_pt(28, 2), lw)
    # Innen-Curls (vereinfacht als 2 Linien)
    pygame.draw.line(screen, color, map_pt(2, 18), map_pt(14, 14),
                     max(1, int(1 * s)))
    pygame.draw.line(screen, color, map_pt(18, 2), map_pt(14, 14),
                     max(1, int(1 * s)))
    # Mittler Punkt (Locken-Knoten)
    pygame.draw.circle(screen, color, map_pt(14, 14), max(1, int(2 * s)))
    # Trailing-Flourish-Punkte
    for fy in (36, 42, 48):
        pygame.draw.circle(screen, color, map_pt(2, fy), 1)
    for fx in (36, 42, 48):
        pygame.draw.circle(screen, color, map_pt(fx, 2), 1)
    # Eck-Marker (großer Punkt)
    pygame.draw.circle(screen, color, map_pt(2, 2), max(2, int(2.5 * s)))


def draw_filigree_corners(screen, rect, color, size=24):
    """Zeichnet 4 Eck-Ornamente um ein Rect.

    rect = pygame.Rect — sichtbarer Frame-Bereich
    size = Größe der Ornament-Ecken
    """
    # TL
    draw_ornament_corner(screen, rect.x - 2, rect.y - 2, size, color, 0)
    # TR
    draw_ornament_corner(screen, rect.x + rect.w - size, rect.y - 2,
                          size, color, 90)
    # BR
    draw_ornament_corner(screen, rect.x + rect.w - size,
                          rect.y + rect.h - size, size, color, 180)
    # BL
    draw_ornament_corner(screen, rect.x - 2, rect.y + rect.h - size,
                          size, color, 270)


def draw_aspect_watermark(screen, rect, aspect_or_class, alpha=22):
    """Großes Aspekt-Glyph als Pergament-Watermark in der Mitte eines Modals.

    Sehr subtil (alpha-Wert ~20) — nur dezente Lore-Andeutung im Hintergrund.

    H-22 (Update #168): Animierte Aspekt-Specific-Layer.  Kharn pulsiert
    glühend, Nheyra driftet horizontal, Valsa-Asche flockt fallend,
    Shulavh wickelt sich.  Pro Aspekt eigener Loop.
    """
    pal = aspect_palette(aspect_or_class)
    color = pal['primary']
    aspect_key = (CLASS_TO_ASPECT.get(aspect_or_class)
                   if aspect_or_class in CLASS_TO_ASPECT
                   else aspect_or_class)
    if aspect_key not in ASPECT_PALETTE:
        return
    cx = rect.x + rect.w // 2
    cy = rect.y + rect.h // 2
    size = min(rect.w, rect.h) - 120
    if size < 100:
        return
    # H-22: Animations-Faktor pro Aspekt
    t = pygame.time.get_ticks() / 1000.0
    drift_x = 0
    drift_y = 0
    pulse_mult = 1.0
    if aspect_key == 'kharn':
        # Pulsierendes Eisen-Glüh
        pulse_mult = 0.85 + 0.15 * math.sin(t * 0.8)
    elif aspect_key == 'nheyra':
        # Horizontale Drift
        drift_x = int(math.sin(t * 0.3) * 8)
    elif aspect_key == 'valsa':
        # Asche flockt langsam fallend
        drift_y = int((t * 6.0) % 12) - 6
    elif aspect_key == 'shulavh':
        # Wickel-Drehung (rotational subtle, simulated via x/y)
        drift_x = int(math.cos(t * 0.4) * 5)
        drift_y = int(math.sin(t * 0.4) * 5)
    elif aspect_key == 'im_nesh':
        # Funken-Zucken (kurze Bursts)
        if int(t * 4) % 3 == 0:
            pulse_mult = 1.15
    elif aspect_key == 'ousen':
        # Sanftes Atmen
        pulse_mult = 0.9 + 0.1 * math.sin(t * 0.5)
    # Render Glyph in eigene Surface mit Alpha
    eff_alpha = int(alpha * pulse_mult)
    glyph_surf = pygame.Surface((size + 40, size + 40), pygame.SRCALPHA)
    draw_glyph(glyph_surf, size // 2 + 20, size // 2 + 20,
                size, aspect_key,
                color=(*color, eff_alpha))
    # Glyph drawn directly with rgb — manually set alpha via blit
    glyph_surf.set_alpha(int(eff_alpha * 2))
    screen.blit(glyph_surf,
                 (cx - (size + 40) // 2 + drift_x,
                  cy - (size + 40) // 2 + drift_y))


def draw_ornament_divider(screen, x, y, width, color):
    """Horizontale Trenn-Linie mit zentriertem Diamant.

    Aus velgrad-glyphs.jsx OrnamentDivider.
    """
    # Zwei Linien-Hälften
    cx = x + width // 2
    pygame.draw.line(screen, color, (x, y), (cx - 12, y), 1)
    pygame.draw.line(screen, color, (cx + 12, y), (x + width, y), 1)
    # Innere parallele Linien (schwächer)
    inner_col = tuple(max(0, c - 40) for c in color[:3])
    pygame.draw.line(screen, inner_col, (x + 20, y - 4),
                     (cx - 20, y - 4), 1)
    pygame.draw.line(screen, inner_col, (cx + 20, y - 4),
                     (x + width - 20, y - 4), 1)
    pygame.draw.line(screen, inner_col, (x + 20, y + 4),
                     (cx - 20, y + 4), 1)
    pygame.draw.line(screen, inner_col, (cx + 20, y + 4),
                     (x + width - 20, y + 4), 1)
    # Zentraler Diamant
    diamond = [(cx, y - 7), (cx + 6, y), (cx, y + 7), (cx - 6, y)]
    pygame.draw.polygon(screen, color, diamond)
    inner_d = [(cx, y - 4), (cx + 3, y), (cx, y + 4), (cx - 3, y)]
    pygame.draw.polygon(screen, (235, 220, 175), inner_d)
    # Flankier-Punkte
    pygame.draw.circle(screen, color, (cx - 20, y), 2)
    pygame.draw.circle(screen, color, (cx + 20, y), 2)
