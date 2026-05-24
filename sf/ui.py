"""HUD, Titel-/Tod-Screen, Skill-Tree-UI, Boss-Bar, Portal-Prompt."""

import math
import pygame

from .constants import (
    SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM,
    WHITE, BLOOD_LIGHT, BLOOD, MANA, FIRE, FROST,
    CLASSES, TREE_NODES,
)
from .skills import SKILL_INFO
from . import progression


# ============================================================
# HUD
# ============================================================
def _draw_buff_tray(screen, game, font_small):
    """Buff-/Debuff-Tray (PLAN G-05).

    Position: links unter Klassen-Fraktion-Label. Zeigt aktive Status-
    Effekte am Spieler mit Dauer-Indikator und Stack-Counter.

    Lore-Naming (Audio-Bibel / Lore-Glossar):
      burn → Ignite, frost → Freeze, chill → Chill, shock → Shock,
      poison → Poison, bleed → Bleed.
    """
    p = game.player
    status = getattr(p, 'status', {})
    if not status:
        return
    # Display-Mapping (Engine-Key → Lore-Name + Farbe).
    # Lore-Quelle: VELGRAD_LORE_BIBEL.md Glossar + POE2-Skill-Briefing 3.2.
    # P-08 (Update #61): Colorblind-Modus.  Wenn aktiv, werden Ailment-
    # Farben auf gut-unterscheidbare Töne gemappt (kein rot↔grün-Pair).
    cb = bool(game.settings.get('colorblind_ailments', False))
    if cb:
        DISPLAY = {
            'burn':    ('Ignite',  (255, 165,   0)),   # orange (klar)
            'frost':   ('Freeze',  (  0, 178, 255)),   # cyan
            'chill':   ('Chill',   (140, 220, 255)),   # hell-cyan
            'shock':   ('Shock',   (255, 240, 120)),   # gelb
            'poison':  ('Poison',  (160,  90, 230)),   # lila (statt grün)
            'bleed':   ('Bleed',   (180,  30,  30)),   # dunkel-rot
            'brittle': ('Brittle', (200, 230, 255)),
            'sapped':  ('Sapped',  (180, 180, 200)),
        }
    else:
        DISPLAY = {
            'burn':    ('Ignite',  (255, 130,  60)),
            'frost':   ('Freeze',  (140, 200, 255)),
            'chill':   ('Chill',   (180, 220, 255)),
            'shock':   ('Shock',   (255, 240, 120)),
            'poison':  ('Poison',  (150, 220, 100)),
            'bleed':   ('Bleed',   (220,  60,  60)),
            'brittle': ('Brittle', (200, 230, 255)),
            'sapped':  ('Sapped',  (180, 180, 200)),
        }
    # Update #54: Buff-Tray UNTER der gesamten Cartouche + Skill-Pills,
    # damit die Status-Icons nicht das Portrait überdecken (Update #29
    # Cartouche reicht von y=28 bis y~145, Pills bei y=162 enden y~184).
    x = 12
    y = 210
    sz = 26
    gap = 4
    # Update #92: Hover-Tracking — Buff-Tooltip
    game._buff_tray_rects = []
    for key, st in status.items():
        if key not in DISPLAY:
            continue
        name, col = DISPLAY[key]
        stacks = st.get('stacks', 1)
        time_left = st.get('time_left', 0)
        # Icon-Box
        bg = pygame.Surface((sz, sz), pygame.SRCALPHA)
        bg.fill((20, 14, 10, 200))
        screen.blit(bg, (x, y))
        pygame.draw.rect(screen, col, (x, y, sz, sz), 1)
        # Stack-Counter
        if stacks > 1:
            sc = font_small.render(str(stacks), True, col)
            screen.blit(sc, (x + 4, y + 4))
        # Dauer-Balken unten
        dur_w = max(0, int(sz * min(1.0, time_left / 6.0)))
        pygame.draw.rect(screen, col, (x, y + sz - 3, dur_w, 3))
        # Name rechts neben Icon
        ns = font_small.render(name, True, col)
        screen.blit(ns, (x + sz + 4, y + 5))
        # Rect für Hover-Detection (Icon + Name)
        full_rect = pygame.Rect(x, y, sz + 4 + ns.get_width(), sz)
        game._buff_tray_rects.append((full_rect, key, name, col, st))
        y += sz + gap
    # Hover-Tooltip rendern
    _draw_buff_tooltip(screen, game, font_small)


_AILMENT_DESCRIPTIONS = {
    'burn':    ('Ignite',  'Brennt — DoT 2 dmg/Tick × Stacks. Lore: Valsas Asche.'),
    'frost':   ('Freeze',  'Eingefroren — 60 % Slow + bei voller Stack: Pinned.'),
    'chill':   ('Chill',   'Erkältet — 35 % Slow. Vor-Stufe zu Freeze.'),
    'shock':   ('Shock',   'Geschockt — +50 % erlittener Schaden. Im-Nesh-Echo.'),
    'poison':  ('Poison',  'Vergiftet — DoT 1.4 dmg/Tick × Stacks. Shulavhs Faden.'),
    'bleed':   ('Bleed',   'Blutet — DoT 2.5 dmg/Tick × Stacks bei Bewegung.'),
    'brittle': ('Brittle', 'Spröde — +10 % Krit-Chance erlitten / Stack.'),
    'sapped':  ('Sapped',  'Ausgelaugt — -15 % verursachter Schaden / Stack.'),
}


def _draw_buff_tooltip(screen, game, font_small):
    """Update #92: Hover-Tooltip für Buff-Tray-Icons mit Lore-Beschreibung."""
    rects = getattr(game, '_buff_tray_rects', None)
    if not rects:
        return
    try:
        mx, my = pygame.mouse.get_pos()
    except Exception:
        return
    for rect, key, name, col, st in rects:
        if not rect.collidepoint(mx, my):
            continue
        title, desc = _AILMENT_DESCRIPTIONS.get(
            key, (name, 'Status-Effekt.'))
        stacks = st.get('stacks', 1)
        time_left = st.get('time_left', 0)
        # Tooltip-Inhalt
        l1 = font_small.render(
            f'{title}  (×{stacks})', True, col)
        l2 = font_small.render(desc, True, (210, 200, 180))
        l3 = font_small.render(
            f'Verbleibend: {time_left:.1f} s', True, (180, 170, 150))
        w = max(l1.get_width(), l2.get_width(), l3.get_width()) + 20
        h = l1.get_height() + l2.get_height() + l3.get_height() + 18
        # Position rechts neben Tray
        tx = rect.right + 8
        ty = rect.y
        if tx + w > SCREEN_W - 8:
            tx = rect.x - w - 8
        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((14, 10, 8, 245))
        screen.blit(bg, (tx, ty))
        pygame.draw.rect(screen, col, (tx, ty, w, h), 2)
        screen.blit(l1, (tx + 10, ty + 6))
        screen.blit(l2, (tx + 10, ty + 6 + l1.get_height() + 2))
        screen.blit(l3, (tx + 10,
                         ty + 6 + l1.get_height() + 2
                         + l2.get_height() + 2))
        break


def _draw_charge_orbs(screen, game, font_small):
    """Power/Frenzy/Endurance-Charges rund um die HP-Globe (PLAN G-06).

    Update #104: Position wird jetzt aus `game._hp_globe_pos` gelesen
    (in draw_hud gesetzt). Vorher hardcoded → desync mit echtem Globe.
    """
    p = game.player
    pc = getattr(p, 'power_charges', 0)
    fc = getattr(p, 'frenzy_charges', 0)
    ec = getattr(p, 'endurance_charges', 0)
    if pc == 0 and fc == 0 and ec == 0:
        return
    tint = class_tint(game, GOLD_BRIGHT)
    # Globe-Position aus draw_hud (sync). Fallback auf grobe Defaults.
    gp = getattr(game, '_hp_globe_pos', None)
    if gp is not None:
        hp_cx, hp_cy, globe_r = gp
    else:
        globe_r = 56
        hp_cx = 130
        hp_cy = SCREEN_H - 120
    # Orbs sitzen auf einem Bogen ÜBER der Globe
    arc_r = globe_r + 22
    orb_r = 7
    # Layout: Power links-oben, Frenzy mitte-oben, Endurance rechts-oben
    arcs = [
        (pc, (180, 110, 240)),  # Power = lila
        (fc, (240, 100,  80)),  # Frenzy = orange
        (ec, (200, 200, 240)),  # Endurance = silber
    ]
    base_angle = -math.pi
    arc_span = math.pi
    total_orbs = sum(min(c, 5) for c, _ in arcs)
    if total_orbs == 0:
        return
    step = arc_span / max(total_orbs + 1, 6)
    idx = 0
    for charges, col in arcs:
        for k in range(min(charges, 5)):
            a = base_angle + step * (idx + 1)
            ox = hp_cx + math.cos(a) * arc_r
            oy = hp_cy + math.sin(a) * arc_r
            # Glow ring
            glow = pygame.Surface((orb_r * 4, orb_r * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*col, 100),
                                (orb_r * 2, orb_r * 2), orb_r + 4)
            screen.blit(glow, (int(ox) - orb_r * 2,
                                int(oy) - orb_r * 2))
            # Orb-Kern (klassen-Akzent als Rim)
            pygame.draw.circle(screen, col, (int(ox), int(oy)), orb_r)
            pygame.draw.circle(screen, tint, (int(ox), int(oy)), orb_r, 1)
            # Inneres Highlight
            pygame.draw.circle(screen, (255, 255, 255),
                                (int(ox) - 2, int(oy) - 2), 2)
            idx += 1


def _draw_flasks(screen, game, font_small):
    """Update #96: Echte Flaschenform statt Rechteck (User-Wunsch).

    Zeichnet eine bauchige Phiole: Korken oben (8 px hoch), Hals (12 px),
    schräger Übergang, bauchiger Körper. Flüssigkeit füllt nur den
    Körper-Innenraum. Lore: Mahnmal-Atemzug-Phiole.
    """
    p = game.player
    flasks = getattr(p, 'flasks', None)
    if not flasks:
        return
    f = flasks.get('vital')
    if f is None:
        return
    # Layout: links unter den Globes
    fx = 22
    fy = SCREEN_H - 110
    fw = 56
    fh = 100
    ready = f['charges'] >= 1.0
    col = f['color'] if ready else (90, 80, 70)
    fill_pct = min(1.0, f['charges'] / max(1, f['max']))

    # Background Slot (subtle für Click-Area)
    bg = pygame.Surface((fw + 8, fh + 4), pygame.SRCALPHA)
    bg.fill((18, 14, 10, 180))
    screen.blit(bg, (fx - 4, fy - 2))

    # --- Phiolen-Geometrie -----------------------------------
    # Korken (Top): 16 px breit × 8 px hoch, zentriert
    cork_w = 18
    cork_h = 8
    cork_x = fx + fw // 2 - cork_w // 2
    cork_y = fy
    # Hals (Neck): 14 px breit × 14 px hoch
    neck_w = 14
    neck_h = 14
    neck_x = fx + fw // 2 - neck_w // 2
    neck_y = cork_y + cork_h
    # Übergang (Shoulder): trapezoid 14 → fw
    shoulder_h = 12
    shoulder_top_y = neck_y + neck_h
    # Bauch (Body): bauchige Form bis fast unten, 4 px Fuß
    body_y = shoulder_top_y + shoulder_h
    body_h = fh - cork_h - neck_h - shoulder_h - 2
    body_w = fw - 4

    # --- Glas-Hülle (Outline) --------------------------------
    # Polygon der Flaschen-Umrisse (Aussen)
    cx_mid = fx + fw // 2
    outline_pts = [
        # Linke Seite: Korken-links → Neck-links → Shoulder-Diag → Body-links-oben
        (cork_x, cork_y + 2),
        (cork_x, cork_y + cork_h),
        (neck_x, neck_y),
        (neck_x, neck_y + neck_h),
        # Shoulder-Diag links
        (fx + 2, body_y),
        # Body-Bottom-Curve über Punkte
        (fx + 2, body_y + body_h - 4),
        (fx + 6, body_y + body_h),
        (fx + fw - 6, body_y + body_h),
        (fx + fw - 2, body_y + body_h - 4),
        # Body rechts hoch
        (fx + fw - 2, body_y),
        # Shoulder-Diag rechts
        (neck_x + neck_w, neck_y + neck_h),
        (neck_x + neck_w, neck_y),
        # Korken rechts
        (cork_x + cork_w, cork_y + cork_h),
        (cork_x + cork_w, cork_y + 2),
        # Korken Top
        (cork_x + cork_w - 1, cork_y),
        (cork_x + 1, cork_y),
    ]

    # --- Flüssigkeit (Fill) ----------------------------------
    # Wir clipen den Fill auf das Polygon der "inneren" Flasche
    # — vereinfacht: ein Rechteck im Body, hochskaliert wenn voll
    inner_y_min = neck_y + 2  # Flüssigkeit kann bis in den Hals
    inner_y_max = body_y + body_h - 3
    fill_h = int((inner_y_max - inner_y_min) * fill_pct)
    if fill_h > 0:
        fill_y_top = inner_y_max - fill_h
        # Surface für die Flüssigkeit, dann clip via Polygon-Maske
        liquid = pygame.Surface((fw, fh), pygame.SRCALPHA)
        for hy in range(fill_h):
            ly = inner_y_max - hy - 1
            local_y = ly - fy
            # Body-Breite (constant) vs Hals-Bereich (schmal)
            if ly < shoulder_top_y:
                # Im Hals/Korken-Bereich
                seg_w = neck_w - 4
                seg_x = neck_x - fx + 2
            elif ly < body_y:
                # Shoulder-Übergang (linear interpolieren)
                t = (ly - shoulder_top_y) / max(1, shoulder_h)
                seg_w = int(neck_w - 4 + (body_w - 4 - (neck_w - 4)) * t)
                seg_x = (fw - seg_w) // 2
            else:
                # Body
                seg_w = body_w - 4
                seg_x = (fw - seg_w) // 2
            # Gradient: oben rosig, unten lila-blau
            t = (hy / max(1, fill_h - 1))
            r_c = int(230 - t * 100)
            g_c = int(130 + t * 30)
            b_c = int(160 + t * 80)
            pygame.draw.line(liquid, (r_c, g_c, b_c, 220),
                              (seg_x, local_y),
                              (seg_x + seg_w, local_y))
        # Wave-Surface am Top (kleine Sinus-Welle)
        wave_ly = inner_y_max - fill_h - fy
        if 0 <= wave_ly < fh:
            ws_amp = 1.5
            ws_t = pygame.time.get_ticks() * 0.004
            for wx in range(2, fw - 2):
                phase = (wx * 0.25) + ws_t
                offs = int(math.sin(phase) * ws_amp)
                pygame.draw.circle(liquid, (255, 220, 240, 200),
                                    (wx, wave_ly + offs), 1)
        screen.blit(liquid, (fx, fy))

    # --- Outline (Glas) zuletzt zeichnen ---------------------
    glass_col = col if ready else (100, 90, 80)
    pygame.draw.polygon(screen, glass_col, outline_pts, 2)
    # Korken-Fill (braun)
    cork_col = (110, 78, 44) if ready else (60, 48, 30)
    pygame.draw.rect(screen, cork_col,
                      (cork_x + 1, cork_y + 1, cork_w - 2, cork_h - 1))
    pygame.draw.line(screen, (60, 38, 18),
                      (cork_x + 1, cork_y + 3),
                      (cork_x + cork_w - 2, cork_y + 3), 1)
    # Highlight-Glanz links auf der Flasche (1 px Linie)
    pygame.draw.line(screen, (255, 240, 220, 180),
                      (fx + 5, body_y + 6),
                      (fx + 5, body_y + body_h - 10), 1)

    # Hotkey-Label oben links (außerhalb der Flasche)
    kt = font_small.render('F1', True, (220, 200, 160))
    screen.blit(kt, (fx - 2, fy - 14))
    # Charge-Counter unter der Flasche
    ct_col = (240, 230, 200) if ready else (140, 130, 110)
    ct = font_small.render(
        f'{int(f["charges"])}/{f["max"]}', True, ct_col)
    screen.blit(ct, (fx + fw // 2 - ct.get_width() // 2,
                      fy + fh + 2))


def _draw_mahnmal_marken(screen, game, font_small):
    """Mahnmal-Marken I..VII Currency-Display (User-Wahl Update #22).

    Lore-Bibel 6.4 + Items-Bibel: Mahnmal-Marken werden von Bossen
    gedroppt (eine pro Aspekt-Lineage). Mahnmal-Halle in Brassweir
    erkennt sie an. UI: kompakte Reihe oben rechts unter Quest-Box.
    """
    p = game.player
    marken = getattr(p, 'mahnmal_marken', {})
    if not marken:
        return
    held = [(k, v) for k, v in sorted(marken.items()) if v > 0]
    if not held:
        return
    # Aspekt-Farben (Lore-Bibel Teil 2)
    ASPEKT_COL = {
        1: (220, 160,  80),   # Kharn — Eisen-Bronze
        2: (180, 200, 220),   # Nheyra — Glas-Blau
        3: (200, 180, 240),   # Ousen — Geist-Violett
        4: (255, 140,  60),   # Valsa — Flamme
        5: (140, 220, 140),   # Im-Nesh — Sprach-Grün
        6: (200,  80, 160),   # Shulavh — Faden-Magenta
        7: (255, 240, 100),   # Der Siebte — Gold
    }
    ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV',
              5: 'V', 6: 'VI', 7: 'VII'}
    # Position: unter Quest-Tracker rechts (gleicher Stack)
    # Update #54: y dynamisch aus dem cached Quest-Tracker-Bottom statt
    # festem 492 — lange Quest-Texte (5+ Zeilen) reichten sonst in die
    # Marken-Area hinein.  `game._quest_tracker_bottom_y` wird in
    # draw_hud nach dem Quest-Render gesetzt; Default Fallback 492.
    box_x = SCREEN_W - 280 - 18
    box_y = getattr(game, '_quest_tracker_bottom_y', 70 + 256 + 26 + 140) + 14
    # Update #180: Pill-Layout breiter + Roman in font_med + Divider —
    # vorher 36×22 mit allem in font_small → "I" und "×2" lagen direkt
    # nebeneinander und wirkten wie Platzhalter ("Ix2").
    sw = 62
    sh = 30
    gap = 6
    font_med = getattr(game, 'font_med', font_small)
    title = font_small.render('MAHNMAL-MARKEN', True, GOLD_BRIGHT)
    screen.blit(title, (box_x, box_y))
    y = box_y + title.get_height() + 6
    for i, (mk, cnt) in enumerate(held):
        col = ASPEKT_COL.get(mk, GOLD)
        row = i // 4
        ccol = i % 4
        x = box_x + ccol * (sw + gap)
        yy = y + row * (sh + gap)
        # Pergament-Hintergrund mit leichtem Gradient (oben heller)
        bg = pygame.Surface((sw, sh), pygame.SRCALPHA)
        for by in range(sh):
            tt = by / max(1, sh - 1)
            rr = int(28 + (16 - 28) * tt)
            gg = int(20 + (10 - 20) * tt)
            bb = int(12 + (6 - 12) * tt)
            pygame.draw.line(bg, (rr, gg, bb, 235), (0, by), (sw, by))
        screen.blit(bg, (x, yy))
        # Doppel-Rahmen (Aspekt-Farbe außen, dunkel innen)
        pygame.draw.rect(screen, col, (x, yy, sw, sh), 1)
        pygame.draw.rect(screen, (60, 40, 22),
                          (x + 2, yy + 2, sw - 4, sh - 4), 1)
        # Roman-Zahl (font_med, Aspekt-Farbe, mit Schatten)
        rs_sh = font_med.render(ROMAN[mk], True, (10, 6, 4))
        rs = font_med.render(ROMAN[mk], True, col)
        roman_w = rs.get_width()
        # Linke Zelle (Roman) ist ca. 45% der Breite, rechte 55% (Count)
        left_cell_w = int(sw * 0.42)
        rx = x + (left_cell_w - roman_w) // 2
        ry = yy + (sh - rs.get_height()) // 2
        screen.blit(rs_sh, (rx + 1, ry + 1))
        screen.blit(rs, (rx, ry))
        # Vertikaler Divider zwischen Numeral und Count
        div_x = x + left_cell_w
        pygame.draw.line(screen, (90, 63, 36),
                          (div_x, yy + 5),
                          (div_x, yy + sh - 5), 1)
        # Count rechts (font_small, weiß)
        cs = font_small.render(f'x{cnt}', True, WHITE)
        right_cell_w = sw - left_cell_w
        cx = div_x + (right_cell_w - cs.get_width()) // 2
        cy = yy + (sh - cs.get_height()) // 2
        screen.blit(cs, (cx, cy))


def draw_bar(screen, font_small, x, y, w, h, val, max_val, color, label, text):
    pygame.draw.rect(screen, (15, 10, 8), (x, y, w, h))
    pygame.draw.rect(screen, (42, 34, 24), (x, y, w, h), 1)
    fill_w = int(w * (val / max_val)) if max_val > 0 else 0
    if fill_w > 0:
        pygame.draw.rect(screen, color, (x, y, fill_w, h))
        hl = pygame.Surface((fill_w, max(1, h // 3)), pygame.SRCALPHA)
        hl.fill((255, 255, 255, 40))
        screen.blit(hl, (x, y))
    if label:
        ls = font_small.render(label, True, TEXT_DIM)
        screen.blit(ls, (x - ls.get_width() - 10,
                         y + h // 2 - ls.get_height() // 2))
    if text:
        ts = font_small.render(text, True, WHITE)
        screen.blit(ts, (x + w // 2 - ts.get_width() // 2,
                         y + h // 2 - ts.get_height() // 2))


def _draw_low_hp_vignette(screen, hp_frac):
    """Pulsierender roter Vignette-Rand bei kritischer HP (G-Block).

    Intensität skaliert invers mit hp_frac (näher bei 0 = stärker).
    Pulse-Frequenz ebenfalls (Herzschlag-Feeling).
    """
    intensity = 1.0 - (hp_frac / 0.30)
    pulse_freq = 0.004 + intensity * 0.005
    pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * pulse_freq)
    max_alpha = int(80 + intensity * 120)
    base_alpha = int(max_alpha * pulse)
    # Eckiges Vignette: vier Bänder (Rand) mit Gradient
    band = 80
    # Top
    top = pygame.Surface((SCREEN_W, band), pygame.SRCALPHA)
    for y in range(band):
        a = int(base_alpha * (1 - y / band))
        pygame.draw.line(top, (180, 30, 30, a), (0, y), (SCREEN_W, y))
    screen.blit(top, (0, 0))
    # Bottom
    bot = pygame.Surface((SCREEN_W, band), pygame.SRCALPHA)
    for y in range(band):
        a = int(base_alpha * (y / band))
        pygame.draw.line(bot, (180, 30, 30, a), (0, y), (SCREEN_W, y))
    screen.blit(bot, (0, SCREEN_H - band))
    # Left
    lf = pygame.Surface((band, SCREEN_H), pygame.SRCALPHA)
    for x in range(band):
        a = int(base_alpha * (1 - x / band))
        pygame.draw.line(lf, (180, 30, 30, a), (x, 0), (x, SCREEN_H))
    screen.blit(lf, (0, 0))
    # Right
    rt = pygame.Surface((band, SCREEN_H), pygame.SRCALPHA)
    for x in range(band):
        a = int(base_alpha * (x / band))
        pygame.draw.line(rt, (180, 30, 30, a), (x, 0), (x, SCREEN_H))
    screen.blit(rt, (SCREEN_W - band, 0))


def draw_event_notifications(screen, game, font_med, font_small):
    """Event-Notifications stack (G-12/G-13).

    Großer Banner oben Mitte für: Level-Up, Quest-Update, Currency-Pickup,
    Story-Moment. Fade-in/Fade-out via time_left/total.
    """
    notifs = getattr(game, 'event_notifications', [])
    if not notifs:
        return
    tint = class_tint(game)
    # Update #134 (User-Screenshot): base_y von 95 → 110 — schafft mehr
    # Luft zum Top-Status-Bar (endet bei y=74) damit die Story/Quest-
    # Notifications nicht an die untere Border kleben.
    base_y = 110
    box_w = 480
    box_h = 60
    for i, n in enumerate(notifs):
        # Alpha-Kurve: fade-in (erstes 0.25s), fade-out (letztes 0.5s)
        elapsed = n['total'] - n['time_left']
        if elapsed < 0.25:
            alpha = elapsed / 0.25
        elif n['time_left'] < 0.5:
            alpha = n['time_left'] / 0.5
        else:
            alpha = 1.0
        alpha = max(0.0, min(1.0, alpha))
        y = base_y + i * (box_h + 8)
        x = SCREEN_W // 2 - box_w // 2
        # Glow-Hintergrund (klassen-getönt)
        glow = pygame.Surface((box_w + 20, box_h + 20), pygame.SRCALPHA)
        pygame.draw.rect(glow, (*tint, int(60 * alpha)),
                          (0, 0, box_w + 20, box_h + 20),
                          border_radius=6)
        screen.blit(glow, (x - 10, y - 10))
        # Box
        bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        bg.fill((14, 10, 6, int(230 * alpha)))
        screen.blit(bg, (x, y))
        # Border (oben + unten + klassen-getönt)
        border_col = (*tint, int(255 * alpha))
        # Pygame draw_rect mit alpha: zeichne auf separate Surface
        bs = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        pygame.draw.line(bs, border_col, (0, 0), (box_w, 0), 2)
        pygame.draw.line(bs, border_col,
                          (0, box_h - 1), (box_w, box_h - 1), 2)
        # Kind-Marker als Akzent links
        kind_col = {
            'levelup':     (255, 220, 90),
            'quest':       (220, 200, 100),
            'pickup_rare': (180, 100, 240),
            'currency':    (220, 180, 110),  # Aithein-Bronze
            'story':       (180, 200, 220),
        }.get(n.get('kind'), tint)
        pygame.draw.rect(bs, (*kind_col, int(255 * alpha)),
                          (0, 0, 4, box_h))
        screen.blit(bs, (x, y))
        # Title (groß, fett)
        title_text = n.get('title', '')
        ts = font_med.render(title_text, True, n.get('color', WHITE))
        ts.set_alpha(int(255 * alpha))
        screen.blit(ts, (x + 22, y + 8))
        # Sub (kleiner, gedeckt)
        sub_text = n.get('sub')
        if sub_text:
            ss = font_small.render(sub_text, True, TEXT_DIM)
            ss.set_alpha(int(220 * alpha))
            screen.blit(ss, (x + 22, y + 8 + ts.get_height() + 2))


def draw_event_log(screen, game, font_small):
    """Pickup-/Story-Event-Log rechts unten (G-11)."""
    log = getattr(game, 'event_log', [])
    if not log:
        return
    x = SCREEN_W - 320
    base_y = SCREEN_H - 230
    for i, ev in enumerate(log[:6]):
        a = max(0.0, min(1.0, ev['time_left'] / max(0.5, ev.get('total', 4.5))))
        if ev['time_left'] < 0.5:
            a = ev['time_left'] / 0.5
        y = base_y - i * 22
        text_col = ev['color']
        ts = font_small.render(ev['text'], True, text_col)
        # Hintergrund-Strip
        bg = pygame.Surface((ts.get_width() + 18, ts.get_height() + 6),
                             pygame.SRCALPHA)
        bg.fill((10, 8, 6, int(180 * a)))
        screen.blit(bg, (x - 8, y - 2))
        # Akzent-Strich links
        pygame.draw.rect(screen, (*text_col[:3], int(220 * a)),
                          (x - 8, y - 2, 3, ts.get_height() + 6))
        ts.set_alpha(int(255 * a))
        screen.blit(ts, (x, y + 1))


def class_tint(game, fallback=GOLD_BRIGHT):
    """Klassen-Aspekt-Akzentfarbe.

    Update #29: zieht jetzt aus aspects.py (Aspekt-Theme-System), nicht
    mehr direkt aus CLASSES[cls]['color']. Lore-Bibel Teil 7 mapt Klasse
    → Aspekt; aspects.aspect_color() liefert die `bright`-Palette.
    """
    try:
        from . import aspects as _asp
        cls = game.player.cls
        return _asp.aspect_color(cls, 'bright')
    except Exception:
        try:
            cls = game.player.cls
            return CLASSES.get(cls, {}).get('color', fallback)
        except Exception:
            return fallback


def _shade_color(c, factor):
    """Färbung heller (factor>1) oder dunkler (factor<1)."""
    r, g, b = c[:3]
    return (max(0, min(255, int(r * factor))),
            max(0, min(255, int(g * factor))),
            max(0, min(255, int(b * factor))))


def _draw_globe(screen, cx, cy, radius, val, max_val, base_color,
                rim_color, label, font_med, font_small, low_pulse=False):
    """Diablo/POE2-Style runde Globe (gefüllt nach val/max_val).

    base_color = HP/MP-Hauptton, rim_color = klassen-getöntes Outline.
    Bei low_pulse=True pulsiert der Rand bei < 30 % Füllung (HP-Warning).
    """
    if max_val <= 0:
        max_val = 1
    frac = max(0.0, min(1.0, val / max_val))
    # Schatten-Boden
    sh = pygame.Surface((radius * 2 + 12, radius // 2 + 8),
                         pygame.SRCALPHA)
    pygame.draw.ellipse(sh, (0, 0, 0, 180), (0, 0, radius * 2 + 12,
                                              radius // 2 + 8))
    screen.blit(sh, (cx - radius - 6, cy + radius // 2 - 2))
    # Hintergrund-Globus (sehr dunkel, klassen-getönt)
    bg = pygame.Surface((radius * 2 + 4, radius * 2 + 4),
                         pygame.SRCALPHA)
    pygame.draw.circle(bg, (12, 10, 8, 255), (radius + 2, radius + 2),
                       radius)
    screen.blit(bg, (cx - radius - 2, cy - radius - 2))
    # Gefüllter Anteil — als horizontaler Wasserstand
    if frac > 0:
        liquid_h = int(radius * 2 * frac)
        liquid_top_y = cy + radius - liquid_h
        fill_surf = pygame.Surface((radius * 2, radius * 2),
                                    pygame.SRCALPHA)
        # Gradient-Fill (heller Top, dunkler Boden)
        light = _shade_color(base_color, 1.25)
        dark = _shade_color(base_color, 0.65)
        for ly in range(liquid_h):
            t = ly / max(1, liquid_h)
            col = (
                int(light[0] * (1 - t) + dark[0] * t),
                int(light[1] * (1 - t) + dark[1] * t),
                int(light[2] * (1 - t) + dark[2] * t),
                235,
            )
            pygame.draw.line(fill_surf, col,
                             (0, radius * 2 - liquid_h + ly),
                             (radius * 2, radius * 2 - liquid_h + ly), 1)
        # Maskieren mit Kreis
        mask = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(mask, (255, 255, 255, 255),
                            (radius, radius), radius)
        fill_surf.blit(mask, (0, 0),
                       special_flags=pygame.BLEND_RGBA_MULT)
        screen.blit(fill_surf, (cx - radius, cy - radius))
        # Wellen-Linie am Wasserstand (subtle animation)
        wave_y = cy + radius - liquid_h
        wave_w = int(math.sqrt(max(0, radius ** 2 -
                                       (cy - wave_y) ** 2)) * 2)
        if wave_w > 0:
            wave_off = math.sin(pygame.time.get_ticks() * 0.003) * 1.5
            pygame.draw.line(screen, _shade_color(base_color, 1.6),
                              (cx - wave_w // 2, wave_y + int(wave_off)),
                              (cx + wave_w // 2,
                               wave_y - int(wave_off)), 1)
    # Outline-Rim (klassen-getönt)
    rim_w = 3
    if low_pulse and frac < 0.30:
        pulse = abs(math.sin(pygame.time.get_ticks() * 0.006))
        rim_w = 3 + int(pulse * 2)
        rim_color = _shade_color(rim_color, 1.0 + pulse * 0.3)
    pygame.draw.circle(screen, rim_color, (cx, cy), radius, rim_w)
    # Innen-Highlight (Glanz oben links)
    hl = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(hl, (255, 255, 255, 60),
                        (radius // 4, radius // 4, radius // 2, radius // 3))
    screen.blit(hl, (cx - radius, cy - radius))
    # Label oberhalb
    if label:
        lbl = font_small.render(label, True, _shade_color(base_color, 1.5))
        screen.blit(lbl, (cx - lbl.get_width() // 2,
                          cy - radius - lbl.get_height() - 4))
    # Wert innerhalb
    val_text = f'{int(val)}/{int(max_val)}'
    vs = font_med.render(val_text, True, WHITE)
    # Subtle shadow
    vs_sh = font_med.render(val_text, True, (0, 0, 0))
    screen.blit(vs_sh,
                (cx - vs.get_width() // 2 + 1,
                 cy - vs.get_height() // 2 + 1))
    screen.blit(vs, (cx - vs.get_width() // 2,
                     cy - vs.get_height() // 2))


def _draw_spirit_bar(screen, cx, cy, w, h, val_reserved, val_max,
                      rim_color, font_small):
    """Spirit-Bar (Lore-Bibel 5.2: Erster Atem im Träger, Aithein-Bronze).

    Reservierter Spirit = ausgefüllter Teil. Verfügbar = leerer Teil.
    Klassen-Akzent als Rim.
    """
    if val_max <= 0:
        val_max = 1
    frac = max(0.0, min(1.0, val_reserved / val_max))
    spirit_col = (220, 180, 110)  # Aithein-Bronze
    # Hintergrund
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((14, 10, 6, 220))
    screen.blit(bg, (cx - w // 2, cy - h // 2))
    # Available (heller Strom)
    avail_w = int(w * (1.0 - frac))
    if avail_w > 0:
        a_surf = pygame.Surface((avail_w, h), pygame.SRCALPHA)
        for hy in range(h):
            t = hy / max(1, h - 1)
            col = _shade_color(spirit_col, 1.2 - t * 0.5)
            pygame.draw.line(a_surf, (*col, 235), (0, hy),
                             (avail_w, hy), 1)
        screen.blit(a_surf, (cx - w // 2, cy - h // 2))
    # Reserved (dunklere Hälfte rechts mit Cross-Hatch)
    res_x = cx - w // 2 + avail_w
    res_w = w - avail_w
    if res_w > 0:
        r_surf = pygame.Surface((res_w, h), pygame.SRCALPHA)
        r_surf.fill((60, 44, 22, 180))
        for k in range(0, res_w + h, 6):
            pygame.draw.line(r_surf, (90, 70, 40, 200),
                             (k, 0), (k - h, h), 1)
        screen.blit(r_surf, (res_x, cy - h // 2))
    # Rim
    pygame.draw.rect(screen, rim_color,
                     (cx - w // 2, cy - h // 2, w, h), 2)
    # Tick-Marks alle 25 Spirit
    if val_max >= 25:
        ticks = int(val_max // 25)
        for k in range(1, ticks):
            tx = cx - w // 2 + int(w * k / ticks)
            pygame.draw.line(screen, (40, 30, 16),
                             (tx, cy - h // 2 + 1),
                             (tx, cy + h // 2 - 1), 1)
    # Label oben — Velgrad-Design nennt es „GEIST" (Spirit), aber wir
    # haben GEIST schon für Mana verwendet. Lore-Bibel 5.2: Spirit ist
    # der „Erste Atem" → wir nutzen „ATEM" als Label.
    label = font_small.render(
        f'ATEM  {int(val_max - val_reserved)}/{int(val_max)}',
        True, _shade_color(spirit_col, 1.4))
    screen.blit(label, (cx - label.get_width() // 2,
                         cy - h // 2 - label.get_height() - 2))


def _draw_xp_thin_bar(screen, cx, cy, w, h, val, max_val,
                       rim_color, font_small):
    """Dünner XP-Streifen (gold, klassen-getönte Rim)."""
    if max_val <= 0:
        max_val = 1
    frac = max(0.0, min(1.0, val / max_val))
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    bg.fill((10, 8, 4, 220))
    screen.blit(bg, (cx - w // 2, cy - h // 2))
    fw = int(w * frac)
    if fw > 0:
        for hy in range(h):
            t = hy / max(1, h - 1)
            col = _shade_color(GOLD_BRIGHT, 1.0 - t * 0.4)
            pygame.draw.line(screen, col,
                             (cx - w // 2, cy - h // 2 + hy),
                             (cx - w // 2 + fw, cy - h // 2 + hy), 1)
    pygame.draw.rect(screen, rim_color,
                     (cx - w // 2, cy - h // 2, w, h), 1)
    # Compact label — Velgrad-Design nennt XP-Bar „ERINNERUNG"
    # (Memory, Lore-Bibel: jeder Skill ist eine Erinnerung).
    txt = font_small.render(
        f'ERINNERUNG  {int(val)}/{int(max_val)}',
        True, GOLD_BRIGHT)
    screen.blit(txt, (cx - txt.get_width() // 2,
                       cy - h // 2 - txt.get_height() - 1))


def _draw_dodge_charges(screen, cx, cy, charges, max_charges,
                        regen_t, rim_color):
    """Dodge-Charges-Indicator (G-09): tick-segmente.

    cx, cy = Position der ganzen Reihe (centered).
    """
    if max_charges <= 0:
        return
    pad = 4
    seg_w = 26
    seg_h = 6
    total = max_charges * seg_w + (max_charges - 1) * pad
    x0 = cx - total // 2
    for i in range(max_charges):
        sx = x0 + i * (seg_w + pad)
        if i < charges:
            # voll
            pygame.draw.rect(screen, (220, 200, 120),
                             (sx, cy - seg_h // 2, seg_w, seg_h))
            pygame.draw.rect(screen, rim_color,
                             (sx, cy - seg_h // 2, seg_w, seg_h), 1)
        else:
            # leer (mit regen-Fortschritt für die nächste)
            pygame.draw.rect(screen, (28, 22, 16),
                             (sx, cy - seg_h // 2, seg_w, seg_h))
            pygame.draw.rect(screen, (60, 50, 36),
                             (sx, cy - seg_h // 2, seg_w, seg_h), 1)
            if i == charges and regen_t > 0:
                # Regen-Fortschritt: regen_t läuft von 4.0 → 0
                prog = max(0.0, 1.0 - regen_t / 4.0)
                pygame.draw.rect(screen, (140, 130, 90),
                                  (sx, cy - seg_h // 2,
                                   int(seg_w * prog), seg_h))


def draw_skill_icon(screen, x, y, sw, idx, active):
    cx, cy = x + sw // 2, y + sw // 2
    col = TEXT if active else TEXT_DIM
    if idx == 0:  # Schwert
        pygame.draw.line(screen, col, (cx - 10, cy + 10), (cx + 10, cy - 10), 3)
        pygame.draw.line(screen, col, (cx - 14, cy + 6), (cx - 6, cy + 14), 2)
    elif idx == 1:  # Feuerball
        pygame.draw.circle(screen, (255, 138, 58) if active else (120, 80, 50),
                           (cx, cy), 10)
        pygame.draw.circle(screen, (255, 220, 120) if active else (140, 110, 70),
                           (cx, cy), 5)
    elif idx == 2:  # Blitz
        pts = [(cx - 4, cy - 14), (cx + 4, cy - 4), (cx - 2, cy - 4),
               (cx + 6, cy + 14), (cx - 2, cy + 2), (cx + 2, cy + 2)]
        pygame.draw.polygon(screen,
                            (170, 200, 255) if active else (90, 100, 130), pts)
    elif idx == 3:  # Heilung
        pygame.draw.rect(screen,
                         (170, 255, 170) if active else (90, 130, 90),
                         (cx - 3, cy - 12, 6, 24))
        pygame.draw.rect(screen,
                         (170, 255, 170) if active else (90, 130, 90),
                         (cx - 12, cy - 3, 24, 6))
    elif idx == 4:  # Frostnova
        for i in range(6):
            a = (i / 6) * math.tau
            r1, r2 = 4, 13
            x1 = cx + math.cos(a) * r1
            y1 = cy + math.sin(a) * r1
            x2 = cx + math.cos(a) * r2
            y2 = cy + math.sin(a) * r2
            pygame.draw.line(screen,
                             FROST if active else (90, 110, 140),
                             (x1, y1), (x2, y2), 2)
    elif idx == 5:  # Earthquake (Riss-Linien)
        c = (180, 120, 60) if active else (100, 80, 60)
        pygame.draw.line(screen, c, (cx - 12, cy + 4), (cx, cy - 6), 3)
        pygame.draw.line(screen, c, (cx, cy - 6), (cx + 12, cy + 4), 3)
        pygame.draw.line(screen, c, (cx, cy - 6), (cx - 4, cy + 10), 2)
        pygame.draw.line(screen, c, (cx, cy - 6), (cx + 4, cy + 12), 2)
    elif idx == 6:  # Spark (Stern)
        c = (180, 200, 255) if active else (90, 110, 130)
        pts = []
        for k in range(8):
            ang = k * math.pi / 4
            r = 12 if k % 2 == 0 else 5
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        pygame.draw.polygon(screen, c, pts)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 2)
    elif idx == 7:  # Bone Spear
        c = (240, 230, 200) if active else (130, 120, 90)
        pygame.draw.line(screen, c, (cx - 11, cy + 11), (cx + 11, cy - 11), 4)
        pygame.draw.polygon(screen, c, [
            (cx + 11, cy - 11), (cx + 14, cy - 4), (cx + 4, cy - 14),
        ])
    elif idx == 8:  # Ice Nova
        c = FROST if active else (110, 130, 160)
        pygame.draw.circle(screen, c, (cx, cy), 12, 2)
        for k in range(8):
            ang = k * math.pi / 4
            x1 = cx + math.cos(ang) * 4
            y1 = cy + math.sin(ang) * 4
            x2 = cx + math.cos(ang) * 11
            y2 = cy + math.sin(ang) * 11
            pygame.draw.line(screen, c, (x1, y1), (x2, y2), 1)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)
    elif idx == 9:  # Comet (Kreis mit Schweif)
        c = (180, 220, 255) if active else (110, 130, 160)
        pygame.draw.circle(screen, c, (cx + 4, cy - 4), 7)
        pygame.draw.circle(screen, (255, 255, 255), (cx + 4, cy - 4), 3)
        # Schweif
        for k in range(4):
            sz = 5 - k
            pygame.draw.circle(screen, c,
                                (cx - 2 - k * 3, cy + 2 + k * 3), sz)
    elif idx == 10:  # Ultimate (Stern in Krone)
        c = (255, 220, 80) if active else (120, 110, 70)
        # Krone — Stern mit 5 Zacken
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            r = 12 if k % 2 == 0 else 5
            pts.append((cx + math.cos(ang) * r, cy + math.sin(ang) * r))
        pygame.draw.polygon(screen, c, pts)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), 3)
    elif idx == 11:  # Time Freeze (Uhr-Symbol mit Eis)
        c = (180, 210, 255) if active else (100, 120, 160)
        pygame.draw.circle(screen, c, (cx, cy), 12, 2)
        # Zeiger
        pygame.draw.line(screen, c, (cx, cy), (cx, cy - 8), 2)
        pygame.draw.line(screen, c, (cx, cy), (cx + 6, cy), 2)
        # Eis-Sterne um die Uhr
        for k in range(4):
            ang = k * math.pi / 2 + math.pi / 4
            x1 = cx + math.cos(ang) * 14
            y1 = cy + math.sin(ang) * 14
            pygame.draw.circle(screen, c, (int(x1), int(y1)), 2)
    elif idx == 12:  # Blink / Teleport (Pfeil + Spur)
        c = (200, 130, 240) if active else (110, 80, 130)
        # Pfeil-Form
        pts = [(cx - 6, cy + 8), (cx + 8, cy - 2), (cx + 8, cy + 4),
               (cx + 12, cy + 4), (cx + 5, cy + 12), (cx - 2, cy + 4),
               (cx + 2, cy + 4)]
        pygame.draw.polygon(screen, c, pts)
        # Geist-Spur dahinter
        pygame.draw.circle(screen, c, (cx - 8, cy), 2)
        pygame.draw.circle(screen, c, (cx - 12, cy + 4), 2)


def _draw_stat_icon(screen, cx, cy, kind, color, t=0.0):
    """Mini-Icon pro Stat-Typ (8×8 px)."""
    if kind == 'level':
        # 5-zack-Stern (gold)
        pts = []
        for k in range(10):
            a = -math.pi / 2 + k * math.pi / 5
            rr = 7 if k % 2 == 0 else 3
            pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, (40, 30, 10), pts, 1)
    elif kind == 'gold':
        # Münze mit "$"
        pygame.draw.circle(screen, color, (cx, cy), 7)
        pygame.draw.circle(screen, (255, 240, 180), (cx - 2, cy - 2), 2)
        pygame.draw.circle(screen, (40, 30, 10), (cx, cy), 7, 1)
        pygame.draw.line(screen, (40, 30, 10), (cx, cy - 4), (cx, cy + 4), 1)
        pygame.draw.line(screen, (40, 30, 10),
                          (cx - 2, cy - 2), (cx + 2, cy - 2), 1)
        pygame.draw.line(screen, (40, 30, 10),
                          (cx - 2, cy + 2), (cx + 2, cy + 2), 1)
    elif kind == 'souls':
        # Flammen-Tropfen (Lila-Geist)
        pulse = 0.7 + 0.3 * math.sin(t * 3)
        pts = [(cx, cy - 8), (cx + 5, cy - 2), (cx + 4, cy + 6),
                (cx, cy + 8), (cx - 4, cy + 6), (cx - 5, cy - 2)]
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, (255, 220, 255),
                             [(cx, cy - 5), (cx + 2, cy - 1),
                              (cx, cy + 3), (cx - 2, cy - 1)])
    elif kind == 'shards':
        # Kristall-Polygon (Cyan)
        pts = [(cx, cy - 8), (cx + 5, cy - 2),
                (cx + 3, cy + 6), (cx - 3, cy + 6), (cx - 5, cy - 2)]
        pygame.draw.polygon(screen, color, pts)
        pygame.draw.polygon(screen, (40, 30, 10), pts, 1)
        pygame.draw.line(screen, (255, 255, 255),
                          (cx - 1, cy - 5), (cx + 1, cy + 3), 1)
    elif kind == 'kills':
        # Gekreuzte Schwerter
        pygame.draw.line(screen, color,
                          (cx - 5, cy - 5), (cx + 5, cy + 5), 2)
        pygame.draw.line(screen, color,
                          (cx + 5, cy - 5), (cx - 5, cy + 5), 2)
        # Griffe (klein)
        pygame.draw.circle(screen, (180, 140, 80), (cx - 5, cy - 5), 1)
        pygame.draw.circle(screen, (180, 140, 80), (cx + 5, cy - 5), 1)


# ============================================================
# Update #144: Akt-Progression-HUD
# ============================================================
# Maps Akt-Nummer → (Region-Name, nächster-Outpost-Key, kurzer-Hint)
# Spieler-driven via len(completed_dungeons) = akt_progress.
# Diese Map ist die Single-Source-of-Truth für die Akt-Reihenfolge
# (synchron zu sf/outposts.py + sf/regions.py).
_AKT_PROGRESSION = [
    # (akt_idx, region_name, next_outpost_key, next_hint)
    (0, 'Akt 1 — Brassweir', 'crypt_lost',
     'Krypta der Vergessenen abschließen'),
    (1, 'Akt 2 — Glasgoldene Ruinen', 'echo_markt',
     'Echo-Markt-Outpost · Frost-Palast clearen'),
    (2, 'Akt 3 — Aschenfelder', 'saeulen_von_helst',
     'Säulen-von-Helst · Lava-Pit clearen'),
    (3, 'Akt 4 — Wurzelgrab', 'knoten_markt',
     'Knoten-Markt · Wurzel-Ruinen clearen'),
    (4, 'Akt 5 — Spiegelstadt Velharn', 'spiegelhof',
     'Spiegelhof · Astral-Reich clearen'),
    (5, 'Akt 6 — Die Drei Wunden', 'drei_wunden_lager',
     'Drei-Wunden-Lager · Tier-3-Krypta'),
    (6, 'Akt 7 — Hohlwort', 'hohlwort',
     'Hohlwort-Camp · Finale'),
    (7, 'Akt 7 — Abgeschlossen',
     None, 'Atlas-Maps & Endgame'),
]


def _draw_akt_progression_hud(screen, game, font_small):
    """Update #144: persistenter Akt-Indikator unter der Cartouche.

    Zeigt: „Akt N — Region" (gold, bold) + „Nächstes Ziel: …" (creme).
    Größe minimal, sodass es keine andere UI verdeckt.  Pos relativ
    zur Cartouche (px=30, py=28, psize=82) → start bei y ≈ 170.
    """
    p = game.player
    akt = len(getattr(p, 'completed_dungeons', ()))
    # Clamp auf Max-Index
    idx = max(0, min(len(_AKT_PROGRESSION) - 1, akt))
    _, region_name, _, next_hint = _AKT_PROGRESSION[idx]
    # Update #181: Position dynamisch — direkt unter dem Pillen-Block,
    # der wiederum unter der Cartouche sitzt.  Fallback 192 falls Pillen-
    # Bottom noch nicht gesetzt (Game-Init / Test-Frame).
    base_x = 30
    base_y = getattr(game, '_pills_bottom_y', 192)
    # Background-Strip (sehr dezent — kein dicker Block)
    region_surf = font_small.render(region_name, True, (243, 213, 114))
    hint_surf = font_small.render(
        f'→ {next_hint}', True, (200, 180, 140))
    box_w = max(region_surf.get_width(), hint_surf.get_width()) + 18
    box_h = region_surf.get_height() + hint_surf.get_height() + 12
    bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
    bg.fill((16, 12, 8, 200))
    screen.blit(bg, (base_x, base_y))
    # Bronze-Border + Akzent-Line links (Akt-Farbe)
    bronze = (154, 118, 66)
    pygame.draw.rect(screen, bronze, (base_x, base_y, box_w, box_h), 1)
    # Linke Akzent-Linie in Akt-Color
    AKT_COLORS = [
        (180, 200, 220),  # Akt 1 — Salz-Blau (crypt)
        (220, 200, 100),  # Akt 2 — Glas-Gold (frost)
        (255, 140, 60),   # Akt 3 — Asche-Rot (lava)
        (120, 200, 120),  # Akt 4 — Wurzel-Grün (swamp)
        (200, 170, 255),  # Akt 5 — Spiegel-Lila (astral)
        (240, 200, 100),  # Akt 6 — Drei-Wunden-Gold
        (180, 180, 200),  # Akt 7 — Hohlwort-Stille
        (220, 220, 180),  # Endgame
    ]
    acc_col = AKT_COLORS[min(len(AKT_COLORS) - 1, idx)]
    pygame.draw.rect(screen, acc_col, (base_x, base_y, 3, box_h))
    # Region-Name + Hint
    screen.blit(region_surf, (base_x + 10, base_y + 4))
    screen.blit(hint_surf,
                 (base_x + 10,
                  base_y + 4 + region_surf.get_height() + 2))


def _draw_character_cartouche(screen, game, font_small, font_med):
    """Character-Portrait-Cartouche oben-links (Velgrad-Design-Adoption).

    Layout (aus velgrad-hud.jsx CharCartouche):
      [Hexagon-Portrait mit Aspekt-Glow + Aspekt-Sigil unten rechts]
      [STUFE N · FAKTION  /  Klassen-Name  /  Faction-Creed]
    """
    from . import quotes as _q
    from . import aspects as _asp
    p = game.player
    fac = _q.class_faction(p.cls)
    aspect_key = _asp.aspect_for_class(p.cls)
    pal = _asp.aspect_palette(aspect_key)
    t = pygame.time.get_ticks() * 0.001

    # Portrait-Hexagon
    px, py = 30, 28
    psize = 82
    cx, cy = px + psize // 2, py + psize // 2
    hex_pts = []
    for k in range(6):
        a = -math.pi / 2 + k * (math.pi / 3)
        hex_pts.append((cx + math.cos(a) * psize // 2,
                         cy + math.sin(a) * psize // 2))
    # Hex-Hintergrund (dunkel radial)
    pygame.draw.polygon(screen, (10, 6, 4), hex_pts)
    pygame.draw.polygon(screen, (42, 26, 16), hex_pts, 2)
    # Innen-Glow (aspekt-getönt, pulsiert)
    pulse = 0.7 + 0.3 * math.sin(t * 1.4)
    glow = pygame.Surface((psize, psize), pygame.SRCALPHA)
    pygame.draw.circle(glow,
                        (*pal['bright'], int(60 * pulse)),
                        (psize // 2, psize // 2), psize // 2 - 6)
    screen.blit(glow, (px, py))
    # Innen-Hexagon (kleiner, ohne Fill — Frame-Look)
    inner_pts = []
    for k in range(6):
        a = -math.pi / 2 + k * (math.pi / 3)
        inner_pts.append((cx + math.cos(a) * (psize // 2 - 5),
                          cy + math.sin(a) * (psize // 2 - 5)))
    pygame.draw.polygon(screen, _shade_color(pal['deep'], 1.4),
                         inner_pts, 1)
    # Klassen-Initialbuchstabe (groß, gilded)
    cls_name = CLASSES.get(p.cls, {}).get('name', '?')
    initial = cls_name[0].upper() if cls_name else '?'
    init_surf = font_med.render(initial, True, pal['halo'])
    # Drop-Shadow
    init_sh = font_med.render(initial, True, (10, 6, 4))
    screen.blit(init_sh, (cx - init_surf.get_width() // 2 + 1,
                            cy - init_surf.get_height() // 2 + 1))
    screen.blit(init_surf, (cx - init_surf.get_width() // 2,
                              cy - init_surf.get_height() // 2))
    # Aspekt-Sigil unten rechts (Mini-Badge)
    sig_cx = px + psize - 4
    sig_cy = py + psize - 4
    pygame.draw.circle(screen, (10, 6, 4), (sig_cx, sig_cy), 14)
    pygame.draw.circle(screen, pal['primary'], (sig_cx, sig_cy), 14, 1)
    _asp.draw_glyph(screen, sig_cx, sig_cy, 20,
                     aspect_key, color=pal['bright'])

    # Rechts neben Portrait: Stufe + Mastery / Klassen-Name / Faktion.
    # Update #181 (User-Fix „HUD ordentlich, kein Ueberlappen"):
    # Vorher 4 Zeilen mit harten Y-Offsets -> Lines ueberschnitten sich
    # + Rail klemmte unter dem Aspekt-Text.  Jetzt 3 Zeilen mit dyn.
    # Hoehen-Stacking.  Aspekt+Domain entfernt (war redundant -- der
    # Aspekt-Sigil + Halo am Portrait kommunizieren das schon visuell).
    tx = px + psize + 14
    line1_col = (180, 140, 80)  # bronze-warm
    fac_name = fac['name'].upper() if fac else 'WANDERER'
    MILESTONES = [0, 50, 150, 400, 900, 1800, 3500, 6000, 10000, 16000]
    mastery_xp = getattr(p, 'class_mastery_xp', 0)
    mastery_rank = max(1, sum(1 for m in MILESTONES if mastery_xp >= m))
    ROMAN = ['', 'I', 'II', 'III', 'IV', 'V',
              'VI', 'VII', 'VIII', 'IX', 'X']
    line1_text = (f'STUFE {p.level}  ·  MEISTER '
                   f'{ROMAN[min(mastery_rank, 10)]}')
    line1 = font_small.render(line1_text, True, line1_col)
    name_surf = font_med.render(cls_name.upper(), True, (235, 220, 175))
    name_sh = font_med.render(cls_name.upper(), True, (10, 6, 4))
    fac_surf = font_small.render(fac_name, True,
                                   _shade_color(pal['primary'], 1.3))

    # Dynamisches Stacking — jede Zeile bekommt eigene Hoehe + 4 px Gap.
    line_gap = 4
    ly = py + 2
    screen.blit(line1, (tx, ly))
    ly += line1.get_height() + line_gap
    screen.blit(name_sh, (tx + 1, ly + 1))
    screen.blit(name_surf, (tx, ly))
    ly += name_surf.get_height() + line_gap
    screen.blit(fac_surf, (tx, ly))
    text_bottom = ly + fac_surf.get_height()

    # XP-Rail sitzt unter PORTRAIT oder TEXT (je nachdem was tiefer ist).
    rail_y = max(py + psize, text_bottom) + 8
    rail_w = psize + 14 + 220
    rail_x = px
    pygame.draw.rect(screen, (10, 6, 4), (rail_x, rail_y, rail_w, 4))
    pygame.draw.rect(screen, (90, 63, 36), (rail_x, rail_y, rail_w, 4), 1)
    if p.xp_to_next > 0:
        fw = int(rail_w * min(1.0, p.xp / p.xp_to_next))
        for hy in range(4):
            col = _shade_color((227, 180, 64), 1.0 - hy * 0.15)
            pygame.draw.line(screen, col,
                              (rail_x, rail_y + hy),
                              (rail_x + fw, rail_y + hy))
    xp_pct = min(100, int(100 * p.xp / max(1, p.xp_to_next)))
    erin = font_small.render(
        f'ERINNERUNG · {xp_pct}%', True, (154, 118, 66))
    screen.blit(erin, (rail_x, rail_y + 8))
    # Update #181: Bottom-Y der Cartouche an Game durchreichen damit
    # nachfolgende HUD-Elemente (Pillen + Akt-Tracker) sauber darunter
    # einrasten ohne Ueberlappen.
    game._cartouche_bottom_y = rail_y + 8 + erin.get_height() + 4


def _draw_top_status_bar(screen, game, font_small, font_med, font_dmg):
    """Ornamentierte Top-Stats-Bar (Update #26).

    Pro Stat eine kompakte „Pille" mit Mini-Icon, Label und Wert.
    Diamond-Separatoren zwischen Pillen. Doppel-Rahmen außen
    (Aithein-Bronze + Gold-Highlight). Class-tint als Akzent-Linie.
    """
    p = game.player
    t = pygame.time.get_ticks() * 0.001
    tint = class_tint(game)
    stats = [
        ('level',   'STUFE',    str(p.level),
            (255, 220, 100)),
        ('gold',    'GOLD',     str(p.gold),
            (255, 215, 90)),
        ('souls',   'SEELEN',   str(getattr(p, 'souls', 0)),
            (180, 110, 230)),
        ('shards',  'SPLITTER', str(getattr(p, 'shards', 0)),
            (140, 200, 255)),
        ('kills',   'KILLS',    str(game.kills),
            (220, 100, 90)),
    ]
    # Pille-Größen ausrechnen
    pill_padding = 14
    icon_w = 18
    pills = []
    total_inner_w = 0
    for kind, label, value, col in stats:
        ls = font_small.render(label, True, (180, 160, 110))
        vs = font_med.render(value, True, GOLD_BRIGHT)
        pw = icon_w + 8 + ls.get_width() + 8 + vs.get_width() + pill_padding
        pills.append((kind, label, value, col, ls, vs, pw))
        total_inner_w += pw
    # Separator-Diamonds zwischen den Pillen
    sep_w = 16
    total_w = total_inner_w + (len(pills) - 1) * sep_w + 24  # äußere padding
    bar_x = SCREEN_W // 2 - total_w // 2
    bar_y = 14
    # Update #105: bar_h vergrößert von 44 → 60.  Label (font_small ~17px) +
    # Wert (font_med ~26px) = 43 px Content + 8 px padding = 51 px brauchen
    # mindestens 56 px Bar-Höhe.  Vorher liefen die Werte unter den Boden.
    bar_h = 60

    # Schatten unter Bar
    sh = pygame.Surface((total_w + 16, bar_h + 14), pygame.SRCALPHA)
    pygame.draw.rect(sh, (0, 0, 0, 160),
                     (4, 4, total_w + 12, bar_h + 8),
                     border_radius=4)
    screen.blit(sh, (bar_x - 8, bar_y))

    # Bar-Background (vertical gradient)
    bg = pygame.Surface((total_w, bar_h), pygame.SRCALPHA)
    for y in range(bar_h):
        ty = y / bar_h
        r = int(20 + 8 * (1 - ty))
        g = int(15 + 6 * (1 - ty))
        b = int(10 + 4 * (1 - ty))
        pygame.draw.line(bg, (r, g, b, 240), (0, y), (total_w, y))
    screen.blit(bg, (bar_x, bar_y))

    # Doppel-Rahmen
    pygame.draw.rect(screen, (220, 180, 110),
                     (bar_x, bar_y, total_w, bar_h), 2)
    pygame.draw.rect(screen, (60, 50, 30),
                     (bar_x + 3, bar_y + 3, total_w - 6, bar_h - 6), 1)
    # Top-Akzent-Linie (klassen-getönt)
    pygame.draw.line(screen, tint,
                     (bar_x + 6, bar_y + 1),
                     (bar_x + total_w - 6, bar_y + 1), 1)
    # Bottom-Akzent
    pygame.draw.line(screen, (160, 130, 80),
                     (bar_x + 6, bar_y + bar_h - 1),
                     (bar_x + total_w - 6, bar_y + bar_h - 1), 1)

    # Eck-Ornament-Diamonds (4 Ecken)
    for cx_, cy_ in [
        (bar_x + 3, bar_y + 3),
        (bar_x + total_w - 4, bar_y + 3),
        (bar_x + 3, bar_y + bar_h - 4),
        (bar_x + total_w - 4, bar_y + bar_h - 4),
    ]:
        pygame.draw.polygon(screen, (220, 180, 110), [
            (cx_, cy_ - 2), (cx_ + 2, cy_),
            (cx_, cy_ + 2), (cx_ - 2, cy_),
        ])

    # Pillen rendern
    x = bar_x + 12
    for i, (kind, label, value, col, ls, vs, pw) in enumerate(pills):
        # Icon-Box (mit getönter Akzent-Linie links)
        pygame.draw.line(screen, col,
                          (x, bar_y + 8), (x, bar_y + bar_h - 8), 2)
        # Icon
        icon_cx = x + 12
        icon_cy = bar_y + bar_h // 2
        _draw_stat_icon(screen, icon_cx, icon_cy, kind, col, t)
        # Update #105: Label + Wert vertikal innerhalb bar_h=60 zentrieren.
        # Total Content-Höhe = label.h + 4 spacing + value.h. Top-Margin so
        # gewählt dass Content vertikal mittig liegt.
        content_h = ls.get_height() + 4 + vs.get_height()
        top_margin = (bar_h - content_h) // 2
        screen.blit(ls, (x + icon_w + 8, bar_y + top_margin))
        screen.blit(vs, (x + icon_w + 8,
                          bar_y + top_margin + ls.get_height() + 4))
        x += pw
        # Separator-Diamond (außer nach letztem)
        if i < len(pills) - 1:
            d_cx = x + sep_w // 2
            d_cy = bar_y + bar_h // 2
            pulse = 0.7 + 0.3 * math.sin(t * 2 + i)
            pygame.draw.polygon(screen, (40, 28, 14),
                                  [(d_cx, d_cy - 4), (d_cx + 4, d_cy),
                                   (d_cx, d_cy + 4), (d_cx - 4, d_cy)])
            pygame.draw.polygon(screen, (220, 180, 110),
                                  [(d_cx, d_cy - 4), (d_cx + 4, d_cy),
                                   (d_cx, d_cy + 4), (d_cx - 4, d_cy)], 1)
            pygame.draw.circle(screen, (255, 230, 140),
                                (d_cx, d_cy), max(1, int(pulse * 2)))
            x += sep_w

    # Region-Label unter der Bar
    from . import regions as _reg
    region_text = _reg.region_label(game.biome)
    if region_text:
        reg_col = _reg.region_accent(game.biome, GOLD_BRIGHT)
        rs = font_small.render(region_text, True, reg_col)
        screen.blit(rs,
                     (SCREEN_W // 2 - rs.get_width() // 2,
                      bar_y + bar_h + 6))


def draw_hud(screen, game, font_small, font_med, font_dmg):
    p = game.player
    eff = progression.effective(p)

    # Update #133 (Z-02): Hardcore-Mode → roter Rand-Akzent am
    # Bildschirm.  Permadeath-Warnung im peripheren Sichtfeld.
    if getattr(game, 'hardcore', False):
        pulse = 0.6 + 0.4 * abs(math.sin(
            pygame.time.get_ticks() * 0.002))
        col = (int(180 * pulse), int(40 * pulse), int(40 * pulse))
        # Dünner roter Rand (4 px) am gesamten Bildschirmrand
        pygame.draw.rect(screen, col,
                          (0, 0, SCREEN_W, SCREEN_H), 4)
        # „HARDCORE"-Label unten rechts neben Minimap
        hc_lbl = font_small.render('⚰ HARDCORE', True,
                                     (220, 80, 80))
        screen.blit(hc_lbl,
                     (SCREEN_W - hc_lbl.get_width() - 30, 12))

    # Update #29: Character-Cartouche oben-links (aus velgrad-hud.jsx).
    # Portrait-Hexagon + Aspekt-Glyph + Klassen-Stufe + Mini-XP-Rail.
    _draw_character_cartouche(screen, game, font_small, font_med)
    # Update #181: Akt-Progression-HUD wird weiter unten nach den
    # Skill-Pillen gerendert (siehe Pillen-Block) damit es deren
    # Bottom-Y kennt — dynamische Y-Positionierung statt fester 192.

    # ============================================================
    # OBERER STATUS-BAR (Update #26 ornamentiert)
    # ============================================================
    # Ornament-Rahmen mit Aithein-Bronze, gold-Akzent oben/unten,
    # Eck-Diamanten. Pro Stat eine "Pille" mit Mini-Icon + Wert.
    _draw_top_status_bar(screen, game, font_small, font_med, font_dmg)

    # Quest-Tracker-Box rechts oben unter der Minimap.
    # Update #30: Velgrad-Pergament-Style + Filigree-Ecken.
    log = getattr(game, 'quest_log', None)
    if log is not None:
        main = log.main_quest_state()
        if main is not None and main.stage is not None:
            from . import aspects as _asp
            box_w = 320
            box_x = SCREEN_W - box_w - 18
            box_y = 70 + 256 + 32
            # Update #180: Typografie-Hierarchie — Titel in font_med
            # (vorher alles font_small → flat, kein Eye-Catch).
            font_title = getattr(game, 'font_med', font_small)
            # Header: Eyebrow "QUEST" + Title
            eyebrow = font_small.render(
                '— DEINE AUFGABE —', True, (180, 140, 80))
            title_surf = font_title.render(
                main.title.upper(), True, (243, 213, 114))
            title_sh = font_title.render(main.title.upper(), True, (10, 6, 4))
            region_surf = font_small.render(
                main.region, True, (154, 118, 66))
            # Stage-Text
            stage_text = main.display_text()
            stage_lines = []
            words = stage_text.split(' ')
            cur = ''
            for w in words:
                if font_small.size(cur + ' ' + w)[0] > box_w - 28 and cur:
                    stage_lines.append(cur)
                    cur = w
                else:
                    cur = (cur + ' ' + w) if cur else w
            if cur:
                stage_lines.append(cur)
            line_h = font_small.get_height() + 2
            # Update #180 fix: groessere Gaps — font_med (Cinzel 24pt)
            # rendert optisch hoeher als get_height() angibt; Divider
            # schnitt sonst durch die Title-Baseline.
            # Layout: top14 + eyebrow + 10 + title + 14 + 10
            #       + region + 12 + stages + bottom14
            box_h = (14 + eyebrow.get_height() + 10
                     + title_surf.get_height() + 14 + 10
                     + region_surf.get_height() + 12
                     + len(stage_lines) * line_h + 14)
            # Pergament-Hintergrund mit Gradient
            bg = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
            for y in range(box_h):
                t = y / max(1, box_h - 1)
                r = int(28 + (18 - 28) * t)
                g = int(20 + (12 - 20) * t)
                b = int(12 + (8 - 12) * t)
                pygame.draw.line(bg, (r, g, b, 230),
                                  (0, y), (box_w, y))
            screen.blit(bg, (box_x, box_y))
            # Doppel-Rahmen
            bronze = (154, 118, 66)
            pygame.draw.rect(screen, bronze,
                              (box_x, box_y, box_w, box_h), 1)
            pygame.draw.rect(screen, (60, 40, 22),
                              (box_x + 3, box_y + 3,
                               box_w - 6, box_h - 6), 1)
            # Filigree-Ecken (kleiner als Modal)
            _asp.draw_filigree_corners(
                screen,
                pygame.Rect(box_x, box_y, box_w, box_h),
                bronze, size=14)
            # Top-Tab „QUEST" (überlagert auf der Border)
            tab_w = 80
            tab_x = box_x + box_w // 2 - tab_w // 2
            pygame.draw.rect(screen, (10, 6, 4),
                              (tab_x, box_y - 8, tab_w, 14))
            pygame.draw.rect(screen, bronze,
                              (tab_x, box_y - 8, tab_w, 14), 1)
            qlbl = font_small.render('QUEST', True, (227, 180, 64))
            screen.blit(qlbl,
                         (tab_x + tab_w // 2 - qlbl.get_width() // 2,
                          box_y - 8))
            # Eyebrow
            y = box_y + 14
            screen.blit(eyebrow, (box_x + box_w // 2 -
                                    eyebrow.get_width() // 2, y))
            y += eyebrow.get_height() + 10
            # Titel zentriert mit Schatten (font_med)
            t_x = box_x + (box_w - title_surf.get_width()) // 2
            screen.blit(title_sh, (t_x + 1, y + 1))
            screen.blit(title_surf, (t_x, y))
            y += title_surf.get_height() + 14
            # Mini-Divider
            pygame.draw.line(screen, (90, 63, 36),
                              (box_x + 24, y),
                              (box_x + box_w - 24, y), 1)
            y += 10
            # Region zentriert
            r_x = box_x + (box_w - region_surf.get_width()) // 2
            screen.blit(region_surf, (r_x, y))
            y += region_surf.get_height() + 12
            # Stage-Text
            for line in stage_lines:
                ls = font_small.render(line, True, (220, 200, 170))
                screen.blit(ls, (box_x + 12, y))
                y += line_h
            # Update #145: Lock-Hint wenn die Quest aktuell unerreichbar
            # ist (Akt-Gate noch nicht erfüllt).  User-Report „komme
            # nicht weiter" — Quest zeigte „Reise zu Aschenfeldern"
            # ohne Hint dass Akt 2 vorher dran ist.
            import re as _re
            qregion = main.quest.get('region', '')
            m = _re.search(r'Akt (\d+)', qregion)
            if m is not None:
                req_akt = int(m.group(1))
                akt_progress = len(getattr(
                    game.player, 'completed_dungeons', ()))
                if akt_progress < (req_akt - 1):
                    needed = (req_akt - 1) - akt_progress
                    lock_text = (f'🔒 Erst Akt {req_akt - 1} abschließen'
                                  if needed == 1 else
                                  f'🔒 Erst {needed} Akte abschließen')
                    # Render Box + Border in Warn-Orange
                    lock_surf = font_small.render(
                        lock_text, True, (255, 150, 80))
                    # Dünne Hint-Box am Boden der Quest
                    lock_y = y + 2
                    lock_h = lock_surf.get_height() + 6
                    lock_bg = pygame.Surface(
                        (box_w - 24, lock_h), pygame.SRCALPHA)
                    lock_bg.fill((60, 30, 14, 200))
                    screen.blit(lock_bg, (box_x + 12, lock_y))
                    pygame.draw.rect(screen, (220, 130, 60),
                                      (box_x + 12, lock_y,
                                       box_w - 24, lock_h), 1)
                    screen.blit(lock_surf,
                                 (box_x + 18, lock_y + 3))
                    y += lock_h + 4
                    box_h += lock_h + 4   # Box vergrößern
            # Update #54: Cache Quest-Tracker-Bottom für Marken-Position
            game._quest_tracker_bottom_y = box_y + box_h
        else:
            game._quest_tracker_bottom_y = 70 + 256 + 26
    else:
        game._quest_tracker_bottom_y = 70 + 256 + 26

    # PLAN G-05: Buff-/Debuff-Tray links oben (über Health-Bar).
    # Zeigt aktive Status-Effekte am Spieler mit Dauer + Stacks.
    _draw_buff_tray(screen, game, font_small)
    # PLAN G-06: Power/Frenzy/Endurance-Charge-Orbs unter Health-Bar.
    _draw_charge_orbs(screen, game, font_small)
    # Update #22: Mahnmal-Marken I..VII oben rechts (User-Wahl).
    _draw_mahnmal_marken(screen, game, font_small)
    # Update #82: Flask-Slots (F1/F2) am linken HUD-Rand unter Health-Globe.
    _draw_flasks(screen, game, font_small)

    # ----------------------------------------------------------------
    # SKILL-/HOTKEY-BAR (PLAN G-01..G-04, G-07, G-14)
    # Update #26: Geometrie wird VOR den Globes berechnet, sodass die
    # Globes dynamisch außerhalb der Hotbar flankieren (vorher überlappten
    # sie mit der Bar wenn mehr Skills freigeschaltet waren).
    # ----------------------------------------------------------------
    unlocked = getattr(p, 'unlocked_skills', set())

    def _mana_ok(skill_id):
        info = SKILL_INFO.get(skill_id)
        return info is None or p.mp >= info['mana']

    # Universal-Cooldowns für X/Y/B (separate Felder am Player)
    ult_cd  = getattr(p, 'ult_cd', 0.0)
    tf_cd   = getattr(p, 'tf_cd', 0.0)
    tp_cd   = getattr(p, 'tp_cd', 0.0)

    # Update #23: Klassen-spezifische Hotbar via skills.CLASS_KEYMAP.
    # Q/W/E/R/1 zeigen die Klassen-Signatur-Skills. 2/3/4/5 nur für mage
    # (Legacy-Slots) oder leer für andere Klassen.
    from . import skills as _sk
    cls_pool = _sk.class_keymap(p.cls)
    # Icon-Index pro Skill-ID (statisch zugeordnet — Sprite-Layout)
    ICON_IDX = {
        'melee': 0, 'fireball': 1, 'lightning': 2, 'heal': 3, 'frostnova': 4,
        'earthquake': 5, 'spark': 6, 'bone_spear': 7, 'ice_nova': 8, 'comet': 9,
        # Class signatures (icon-fallback auf passendes Element)
        'boneshatter':     7, 'killing_palm':     0,
        'detonate_dead':   8, 'lightning_arrow':  2,
        'galvanic_shot':   2, 'lightning_spear':  7,
        'storm_call':      2,
    }
    full_skill_data = [
        ('LMB', 'melee', True, None, 0),
    ]
    for hk_label, sid in zip(_sk.HOTKEY_LABELS, cls_pool):
        info = SKILL_INFO.get(sid, {})
        cost = info.get('mana', 0)
        can = (cost == 0) or _mana_ok(sid)
        cd_left = p.skill_cd.get(sid, 0)
        full_skill_data.append(
            (hk_label, sid, can, cd_left, ICON_IDX.get(sid, 1)))
    # Mage behält Legacy-Slots 2-5 (Tutorials/Compat)
    if p.cls == 'mage':
        legacy_extra = [
            ('2', 'spark',      _mana_ok('spark'),
             p.skill_cd.get('spark', 0), 6),
            ('3', 'bone_spear', _mana_ok('bone_spear'),
             p.skill_cd.get('bone_spear', 0), 7),
            ('4', 'ice_nova',   _mana_ok('ice_nova'),
             p.skill_cd.get('ice_nova', 0), 8),
            ('5', 'comet',      _mana_ok('comet'),
             p.skill_cd.get('comet', 0), 9),
        ]
        # Mage hat Slot 1 'spark' bereits in CLASS_KEYMAP — dedupe:
        cls_ids = set(cls_pool)
        for entry in legacy_extra:
            if entry[1] not in cls_ids:
                full_skill_data.append(entry)
    # Universal-Skills (immer in der Bar)
    full_skill_data += [
        ('X', 'ultimate',     True, ult_cd, 10),
        ('Y', 'time_freeze',  True, tf_cd, 11),
        ('B', 'teleport',     True, tp_cd, 12),
    ]
    # G-04-Invariante: jeder freigeschaltete Skill MUSS auf der Bar liegen.
    # Universal-Skills (X/Y/B) und melee zeigen wir IMMER an.
    UNIVERSAL = {'melee', 'ultimate', 'time_freeze', 'teleport'}
    skill_data = [t for t in full_skill_data
                  if t[1] in UNIVERSAL or t[1] in unlocked]

    # Slot-Größe dynamisch — passt sich Bar-Länge an damit alle Skills (10–13)
    # in den Screen passen.
    n_slots = len(skill_data)
    if n_slots <= 10:
        sw = 60
    elif n_slots <= 12:
        sw = 54
    else:
        sw = 50
    gap = 6
    total = n_slots * sw + (n_slots - 1) * gap
    sx0 = SCREEN_W // 2 - total // 2
    sy0 = SCREEN_H - 150

    # Optional: HUD-State-Helper für Tooltip (G-14).
    # Speichert pro Frame die Slot-Rects, damit Game den Hover prüfen kann.
    game._hotkey_slot_rects = []

    # Klassen-getönter Akzent für Slot-Borders + Globe-Rims.
    tint_color = class_tint(game)
    tint = tint_color  # alias für Globe-Block

    # ----------------------------------------------------------------
    # TWO-GLOBES + SPIRIT-BAR HUD (PLAN M-08 + Lore-Bibel 5.2)
    # Update #26: Globes positionieren sich DYNAMISCH außerhalb der
    # Hotbar — `total` ist die echte Hotbar-Breite. So überlappen sie
    # nie mehr, egal wie viele Skills freigeschaltet sind.
    # ----------------------------------------------------------------
    globe_r = 56  # leicht kleiner als vorher (56 statt 60) für mehr Luft
    hotbar_left = sx0  # linke Kante der Hotbar
    hotbar_right = sx0 + total  # rechte Kante
    globe_cy = sy0 + sw // 2  # vertikal mittig zur Hotbar
    # Update #104: Globe-Position für Charge-Orbs exposen
    # damit _draw_charge_orbs (kommt später im Render) sich syncen kann.
    margin = 18  # Abstand zwischen Hotbar-Kante und Globe-Kante
    hp_cx = hotbar_left - margin - globe_r
    game._hp_globe_pos = (hp_cx, globe_cy, globe_r)
    mp_cx = hotbar_right + margin + globe_r
    # Update #28: Velgrad-Design-Tokens — Mana-Globe wird zu „GEIST"
    # (Ghost-Cyan) und Lebens-Globe behält Blood-Red. Lore-Bibel 5.2
    # nennt Mana = „Persönliches Leben"; das Design-Manual nennt es
    # konsequent „Geist".
    VG_BLOOD = (216, 56, 56)   # vg-blood-glow
    VG_GHOST = (127, 208, 220) # vg-ghost-bright
    _draw_globe(screen, hp_cx, globe_cy, globe_r,
                 p.hp, eff['hp_max'], VG_BLOOD, tint,
                 'LEBEN', font_med, font_small, low_pulse=True)
    _draw_globe(screen, mp_cx, globe_cy, globe_r,
                 p.mp, eff['mp_max'], VG_GHOST, tint,
                 'GEIST', font_med, font_small)
    # Update #29: Filigree-Eck-Ornamente um beide Globes (Aithein-Bronze).
    from . import aspects as _asp
    bronze_warm = (154, 118, 66)
    for cx in (hp_cx, mp_cx):
        frame_rect = pygame.Rect(cx - globe_r - 14, globe_cy - globe_r - 14,
                                  (globe_r + 14) * 2, (globe_r + 14) * 2)
        _asp.draw_filigree_corners(screen, frame_rect, bronze_warm, size=22)
    # Spirit-Bar mittig über der Hotbar
    sp_max = int(getattr(p, 'spirit_max', 100))
    sp_res = int(getattr(p, 'spirit_reserved', 0))
    spirit_cx = SCREEN_W // 2
    spirit_cy = sy0 - 32
    spirit_w = min(360, total - 20)
    _draw_spirit_bar(screen, spirit_cx, spirit_cy, spirit_w, 12,
                      sp_res, sp_max, tint, font_small)
    # XP-Bar dünn unter Spirit
    _draw_xp_thin_bar(screen, spirit_cx, spirit_cy + 18, spirit_w, 5,
                       p.xp, p.xp_to_next, tint, font_small)
    # Dodge-Charges (G-09)
    dc = int(getattr(p, 'dodge_charges', 0))
    dc_max = int(getattr(p, 'dodge_charges_max', 0))
    dc_regen = float(getattr(p, 'dodge_regen_t', 0.0))
    if dc_max > 0:
        _draw_dodge_charges(screen, spirit_cx, spirit_cy + 32,
                            dc, dc_max, dc_regen, tint)

    # Schild-Anzeige falls aktiv — animated-dashed-Ring um HP-Globe
    if p.shield > 0:
        shield_r = globe_r + 6
        dash_count = 24
        for k in range(dash_count):
            if k % 2 == 0:
                a0 = (k / dash_count) * math.tau + \
                    pygame.time.get_ticks() * 0.0008
                a1 = a0 + (math.tau / dash_count) * 0.7
                pygame.draw.arc(screen, (160, 200, 255),
                                 (hp_cx - shield_r, globe_cy - shield_r,
                                  shield_r * 2, shield_r * 2),
                                 a0, a1, 3)
        ss = font_small.render(f'Schild {int(p.shield)}',
                                True, (160, 200, 255))
        screen.blit(ss, (hp_cx - ss.get_width() // 2,
                          globe_cy + globe_r + 8))

    import math as _m
    for i, (key, skill, can_cast, cd, icon_idx) in enumerate(skill_data):
        x = sx0 + i * (sw + gap)
        rect = pygame.Rect(x, sy0, sw, sw)
        game._hotkey_slot_rects.append((rect, skill))

        # Slot-Hintergrund
        slot = pygame.Surface((sw, sw), pygame.SRCALPHA)
        slot.fill((24, 20, 16, 235))
        screen.blit(slot, (x, sy0))
        # Top-Akzent (klassen-getönt — User-Wahl Update #22)
        pygame.draw.line(screen, tint_color, (x, sy0), (x + sw, sy0), 2)
        # Border-Farbe: leuchtend wenn castbar (can_cast & kein CD), sonst gedeckt
        active = can_cast and (not cd or cd <= 0) and skill in unlocked
        border_col = tint_color if active else (70, 56, 36)
        border_w = 2 if active else 1
        pygame.draw.rect(screen, border_col, (x, sy0, sw, sw), border_w)

        # Icon
        draw_skill_icon(screen, x, sy0, sw, icon_idx, can_cast)

        # Hotkey-Label oben rechts
        key_surf = font_small.render(key, True, GOLD)
        screen.blit(key_surf, (x + sw - key_surf.get_width() - 4, sy0 + 2))

        # Mana-Kosten unten zentriert (skip für melee = keine Kosten)
        info = SKILL_INFO.get(skill, {})
        cost = info.get('mana', 0)
        if cost > 0:
            cost_col = MANA if p.mp >= cost else (200, 80, 80)
            cost_surf = font_small.render(str(int(cost)), True, cost_col)
            cost_x = x + sw // 2 - cost_surf.get_width() // 2
            cost_y = sy0 + sw - cost_surf.get_height() - 2
            # Hintergrund-Strip für Lesbarkeit
            strip = pygame.Surface(
                (cost_surf.get_width() + 8, cost_surf.get_height() + 2),
                pygame.SRCALPHA)
            strip.fill((0, 0, 0, 160))
            screen.blit(strip, (cost_x - 4, cost_y - 1))
            screen.blit(cost_surf, (cost_x, cost_y))

        # Rune-Indikator (kleiner Punkt unten links)
        if skill and p.runes.get(skill):
            pygame.draw.circle(screen, (255, 200, 80), (x + 6, sy0 + sw - 6), 4)
            pygame.draw.circle(screen, WHITE, (x + 6, sy0 + sw - 6), 4, 1)

        # Cooldown-Sweep mit echter Skill-CD aus SKILL_INFO.
        if cd and cd > 0:
            max_cd = info.get('cd', 4.0)
            frac = min(1.0, cd / max(0.01, max_cd))
            ov = pygame.Surface((sw, sw), pygame.SRCALPHA)
            cx = sw // 2
            cy = sw // 2
            steps = max(3, int(36 * frac))
            pts = [(cx, cy)]
            start_angle = -_m.pi / 2
            end_angle = start_angle + _m.tau * frac
            for k in range(steps + 1):
                a = start_angle + (end_angle - start_angle) * k / steps
                pts.append((cx + _m.cos(a) * (sw // 2 + 2),
                            cy + _m.sin(a) * (sw // 2 + 2)))
            pygame.draw.polygon(ov, (0, 0, 0, 200), pts)
            screen.blit(ov, (x, sy0))
            cd_surf = font_med.render(f'{cd:.1f}', True, GOLD_BRIGHT)
            screen.blit(cd_surf,
                        (x + sw // 2 - cd_surf.get_width() // 2,
                         sy0 + sw // 2 - cd_surf.get_height() // 2))

    # Skill-Punkt-/Attribut-Hinweise als kompakte Pillen UNTER der
    # ERINNERUNG-Bar.
    # Update #181: pill_y dynamisch aus _cartouche_bottom_y damit es nie
    # mit dem ERINNERUNG-Label kollidiert (Fallback 150 falls Cartouche
    # noch nicht gezeichnet wurde).
    pill_y = getattr(game, '_cartouche_bottom_y', 150)
    pill_x = 30
    pills = []
    if p.skill_points > 0:
        pills.append(('Skill (K)', p.skill_points, (255, 220, 100)))
    if p.attr_points > 0:
        pills.append(('Attr (I)', p.attr_points, (180, 220, 255)))
    if p.class_points > 0:
        pills.append(('Klasse (K)', p.class_points, (220, 180, 255)))
    pill_h_total = 0
    for label, count, col in pills:
        text = font_small.render(f'{count} {label}', True, col)
        pad = 8
        dot_r = 4
        dot_gap = 6
        pw = text.get_width() + pad * 2 + dot_r * 2 + dot_gap
        ph = text.get_height() + 4
        pill_h_total = max(pill_h_total, ph)
        bg = pygame.Surface((pw, ph), pygame.SRCALPHA)
        bg.fill((20, 14, 8, 220))
        screen.blit(bg, (pill_x, pill_y))
        pygame.draw.rect(screen, col, (pill_x, pill_y, pw, ph), 1)
        dot_cx = pill_x + pad + dot_r
        dot_cy = pill_y + ph // 2
        pygame.draw.circle(screen, col, (dot_cx, dot_cy), dot_r)
        pygame.draw.circle(screen, (10, 6, 4),
                            (dot_cx, dot_cy), dot_r, 1)
        screen.blit(text,
                     (pill_x + pad + dot_r * 2 + dot_gap, pill_y + 2))
        pill_x += pw + 6
    # Update #181: Bottom-Y der Pillen-Reihe an Akt-Tracker durchreichen
    # (auch wenn keine Pillen aktiv sind — dann == Cartouche-Bottom).
    game._pills_bottom_y = pill_y + pill_h_total + (8 if pills else 0)

    # Update #144 + #181: Akt-Progression-HUD jetzt HIER (nach Pillen)
    # damit es _pills_bottom_y kennt und sauber darunter einrastet.
    _draw_akt_progression_hud(screen, game, font_small)

    # Hinweise (links unten)
    keys = font_small.render(
        'I: Inventar  ·  K: Talente  ·  C: Werkstatt  ·  Leertaste: Ausweichen',
        True, TEXT_DIM)
    screen.blit(keys, (16, SCREEN_H - 18))

    # Event-Notifications oben Mitte (G-12/G-13/Pickup-Rare)
    draw_event_notifications(screen, game, font_med, font_small)
    # Event-Log rechts unten (G-11)
    draw_event_log(screen, game, font_small)
    # Low-HP-Vignette: pulsierender Rot-Rand wenn HP < 30 %
    if eff['hp_max'] > 0 and p.hp / eff['hp_max'] < 0.30 and p.hp > 0:
        _draw_low_hp_vignette(screen, p.hp / eff['hp_max'])
    # Crit-Flash: 1-Frame Yellow-Tint nach Crit (gesetzt in combat.hit_enemy)
    crit_flash = getattr(game, 'crit_flash_t', 0.0)
    if crit_flash > 0:
        alpha = int(min(80, crit_flash * 400))
        flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        flash.fill((255, 220, 100, alpha))
        screen.blit(flash, (0, 0))


# ============================================================
# BOSS-BAR
# ============================================================
def draw_boss_bar(screen, font_med, font_small, boss):
    """Boss-Banner im Velgrad-Memorial-Style (Update #30).

    Layout (aus velgrad-hud.jsx BossBanner adaption):
      [Eyebrow „— Anomalie der Aschwunde —"]
      [BOSS-NAME-GROSS mit Blood-Glow]
      [Boss-Titel-Quote in italic]
      [HP-Bar 760 px mit Phase-Markern + Mono-Zahlen drauf]
      [PHASE-Indicator (4 Segmente)]
    """
    bw = 760
    bx = SCREEN_W // 2 - bw // 2
    by = 86
    t = pygame.time.get_ticks() * 0.001

    # Eyebrow (über dem Namen, gold/bronze)
    boss_title = getattr(boss, 'boss_title', '— Anomalie —')
    eyebrow = font_small.render(
        f'—  {boss_title.upper()}  —', True, (180, 140, 80))
    screen.blit(eyebrow,
                 eyebrow.get_rect(center=(SCREEN_W // 2, by - 60)))

    # Boss-Name (groß, mit Blood-Glow-Shadow)
    name_text = boss.boss_name.upper()
    # Glow-Stack
    for k in range(4):
        glow = font_med.render(name_text, True, (184, 30, 30))
        glow.set_alpha(40 + k * 18)
        glow_r = glow.get_rect(center=(SCREEN_W // 2 + (k % 2) - 0.5,
                                         by - 32 + (k % 2)))
        screen.blit(glow, glow_r)
    # Schatten
    sh = font_med.render(name_text, True, (0, 0, 0))
    screen.blit(sh, sh.get_rect(center=(SCREEN_W // 2 + 1, by - 31)))
    name_surf = font_med.render(name_text, True, (237, 224, 192))
    screen.blit(name_surf,
                 name_surf.get_rect(center=(SCREEN_W // 2, by - 32)))

    # Optional Boss-Quote (italic-style)
    boss_quote = getattr(boss, 'boss_quote', None)
    if boss_quote:
        q = font_small.render(f'„{boss_quote}"', True, (200, 165, 110))
        screen.blit(q, q.get_rect(center=(SCREEN_W // 2, by - 12)))

    # HP-Bar mit Border + Gradient (Blood-Deep → Blood-Glow)
    bar_h = 22
    # Outer Frame
    pygame.draw.rect(screen, (40, 12, 12),
                      (bx - 1, by - 1, bw + 2, bar_h + 2), 1)
    pygame.draw.rect(screen, (10, 6, 4), (bx, by, bw, bar_h))
    pygame.draw.rect(screen, (60, 12, 12), (bx, by, bw, bar_h), 2)
    # Fill
    if boss.hp_max > 0:
        fill_w = int(bw * (boss.hp / boss.hp_max))
        if fill_w > 0:
            for hy in range(bar_h):
                t_y = hy / max(1, bar_h - 1)
                # Vertical gradient: hell oben, dunkel unten
                r = int(216 + (86 - 216) * t_y)
                g = int(56 + (12 - 56) * t_y)
                b = int(56 + (12 - 56) * t_y)
                pygame.draw.line(screen, (r, g, b),
                                  (bx, by + hy),
                                  (bx + fill_w, by + hy))
            # Glanz-Linie oben
            pygame.draw.line(screen, (255, 200, 200),
                              (bx + 2, by + 2),
                              (bx + fill_w - 2, by + 2), 1)

    # Phase-Marker bei 66 %, 33 % (mit Pulse-Glow)
    for thresh in (0.66, 0.33):
        mx = bx + int(bw * thresh)
        pulse = 0.5 + 0.5 * math.sin(t * 2.6 + thresh)
        pygame.draw.line(screen, (227, 180, 64),
                          (mx, by), (mx, by + bar_h), 2)
        # Glow
        glow = pygame.Surface((6, bar_h + 8), pygame.SRCALPHA)
        pygame.draw.line(glow, (255, 230, 140, int(150 * pulse)),
                          (3, 0), (3, bar_h + 8), 3)
        screen.blit(glow, (mx - 3, by - 4))

    # HP-Zahlen mittig auf der Bar (mono-style)
    hp_text = f'{int(boss.hp)}  /  {int(boss.hp_max)}'
    hp_surf = font_small.render(hp_text, True, (235, 220, 175))
    hp_sh = font_small.render(hp_text, True, (0, 0, 0))
    hp_r = hp_surf.get_rect(center=(SCREEN_W // 2, by + bar_h // 2))
    screen.blit(hp_sh, (hp_r.x + 1, hp_r.y + 1))
    screen.blit(hp_surf, hp_r)

    # Phase-Indicator (4 Segmente unter der Bar)
    phase_y = by + bar_h + 8
    phase_label = font_small.render('PHASE', True, (180, 140, 80))
    plx = SCREEN_W // 2 - 80
    screen.blit(phase_label, (plx, phase_y))
    # 4 Segmente
    cur_phase = getattr(boss, 'boss_phase', 1)
    for k in range(4):
        seg_x = plx + 50 + k * 18
        if k < cur_phase:
            col = (227, 180, 64)
            pygame.draw.rect(screen, col,
                              (seg_x, phase_y + 4, 14, 4))
            # Glow auf aktivem Segment
            if k == cur_phase - 1:
                glow = pygame.Surface((18, 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (255, 230, 140, 120),
                                  (0, 0, 18, 8))
                screen.blit(glow, (seg_x - 2, phase_y + 2))
        else:
            pygame.draw.rect(screen, (74, 55, 30),
                              (seg_x, phase_y + 4, 14, 4))
    # Roman-Phase-Zahl
    ROMAN = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}
    pr_text = f'{ROMAN.get(cur_phase, "I")} / IV'
    pr = font_small.render(pr_text, True, (140, 110, 70))
    screen.blit(pr, (plx + 132, phase_y))

    # Encounter-Invuln-Anzeige während Cinematic-Intro
    if getattr(boss, '_encounter_invuln_left', 0.0) > 0.0:
        iv = boss._encounter_invuln_left
        inv_surf = font_small.render(f'UNVERWUNDBAR ({iv:.1f}s)',
                                      True, (220, 220, 240))
        screen.blit(inv_surf,
                     inv_surf.get_rect(center=(SCREEN_W // 2,
                                                 phase_y + 24)))

    # Shield-Bar (über HP)
    if getattr(boss, 'shield', 0) > 0:
        sh_y = by - 8
        pygame.draw.rect(screen, (10, 14, 30), (bx, sh_y, bw, 6))
        sh_fill = int(bw * (boss.shield / max(1, boss.shield_max)))
        pygame.draw.rect(screen, (160, 200, 255),
                          (bx, sh_y, sh_fill, 6))
        pygame.draw.rect(screen, (200, 220, 255),
                          (bx, sh_y, bw, 6), 1)


# ============================================================
# PORTAL-PROMPT
# ============================================================
def draw_portal_prompt(screen, font_med, font_small, portal_near):
    from .world import BIOMES
    biome_data = BIOMES[portal_near.biome]
    msg = f'Portal nach {biome_data["name"]} — F zum Betreten'
    surf = font_med.render(msg, True, biome_data['accent'])
    x = SCREEN_W // 2 - surf.get_width() // 2
    y = SCREEN_H - 200
    bg = pygame.Surface((surf.get_width() + 24, surf.get_height() + 12),
                        pygame.SRCALPHA)
    bg.fill((10, 8, 6, 200))
    screen.blit(bg, (x - 12, y - 6))
    pygame.draw.rect(screen, biome_data['accent'],
                     (x - 12, y - 6, surf.get_width() + 24, surf.get_height() + 12), 1)
    screen.blit(surf, (x, y))


# ============================================================
# TITEL- & KLASSEN-AUSWAHL
# ============================================================
class TitleUI:
    """Velgrad-Title-Screen (Update #25 komplett überarbeitet).

    Layout-Schichten:
      1. Atmospheric Background — Gradient (Nachtmeer→Aschehimmel),
         Brassweir-Silhouette + Pier, drift-Embers + Salzstaub
      2. Title-Block — SHADOWFALL mit Doppel-Glow + Ornament-Divider
      3. Klassen-Cards — 4×2 Grid mit Faktion-Sigil-Band, Aspekt-Akzent-
         Linie, Eck-Ornamenten, größerem Weapon-Icon
      4. Detail-Panel — Mahnmal-Steine-Style-Frame mit Faktion-Crest,
         Aspekt-Glyph, Lore-Quote als Pergament-Box
      5. Buttons — als-Polygon gezeichnete Pfeile (statt „►"), Aithein-
         Bronze-Tönung, Hover-Glow
    """
    def __init__(self, font_big, font_med, font_small):
        self.font_big = font_big
        self.font_med = font_med
        self.font_small = font_small
        self.selected = 'warrior'
        self._class_rects = {}
        self._adv_rect = None
        self._surv_rect = None
        self._continue_rect = None
        self.save_exists = False
        # Update #25: deterministische Ember-Partikel-Positionen.
        # (Werden lazy beim ersten Draw gefüllt — pygame.time muss da sein.)
        self._embers = None
        self._stars = None

    def handle_click(self, mx, my):
        """Returnt 'start_adventure' / 'continue' / 'select' / None.

        Update #121: Survival-Modus entfernt.
        """
        for cls_key, rect in self._class_rects.items():
            if rect.collidepoint(mx, my):
                self.selected = cls_key
                return 'select'
        if self._continue_rect and self._continue_rect.collidepoint(mx, my):
            return 'continue'
        if self._adv_rect and self._adv_rect.collidepoint(mx, my):
            return 'start_adventure'
        return None

    # ---------- Background ----------
    def _init_embers(self):
        import random as _r
        rng = _r.Random(42)
        # 60 Embers (kleine glühende Punkte, driften nach oben)
        self._embers = []
        for _ in range(60):
            self._embers.append({
                'x':     rng.uniform(0, SCREEN_W),
                'y':     rng.uniform(0, SCREEN_H),
                'speed': rng.uniform(8, 26),
                'sway':  rng.uniform(0.6, 1.8),
                'phase': rng.uniform(0, math.tau),
                'size':  rng.uniform(1.0, 2.4),
                'col_idx': rng.randint(0, 3),  # 0..3 Glut-Töne
            })
        # 40 Sterne / Salz-Reflexionen
        self._stars = []
        for _ in range(40):
            self._stars.append({
                'x':     rng.uniform(0, SCREEN_W),
                'y':     rng.uniform(0, 380),  # nur oben
                'phase': rng.uniform(0, math.tau),
                'period': rng.uniform(2.0, 5.0),
                'size':  rng.uniform(0.8, 1.6),
            })

    def _draw_atmospheric_bg(self, screen, t):
        """Gradient + Brassweir-Silhouette + drift-Embers + Sterne."""
        # 1) Vertikaler Gradient: oben Asche-Violett, Mitte Salz-Blau,
        #    unten Tinten-Schwarz. Lore-Bibel Akt 1 + Audio 7.1.A.
        bg = pygame.Surface((SCREEN_W, SCREEN_H))
        for y in range(SCREEN_H):
            t_y = y / SCREEN_H
            if t_y < 0.35:
                # Asche-Himmel
                t2 = t_y / 0.35
                r = int(28 + (20 - 28) * t2)
                g = int(20 + (24 - 20) * t2)
                b = int(34 + (38 - 34) * t2)
            elif t_y < 0.55:
                # Horizont (Salz-Nebel)
                t2 = (t_y - 0.35) / 0.20
                r = int(20 + (16 - 20) * t2)
                g = int(24 + (22 - 24) * t2)
                b = int(38 + (42 - 38) * t2)
            else:
                # Nachtmeer / Tinte
                t2 = (t_y - 0.55) / 0.45
                r = int(16 + (4 - 16) * t2)
                g = int(22 + (6 - 22) * t2)
                b = int(42 + (10 - 42) * t2)
            pygame.draw.line(bg, (r, g, b), (0, y), (SCREEN_W, y))
        screen.blit(bg, (0, 0))

        # 2) Sterne / Salzstaub-Glimmern (oben)
        if self._stars:
            for s in self._stars:
                pulse = 0.4 + 0.6 * (0.5 + 0.5 * math.sin(
                    t * math.tau / s['period'] + s['phase']))
                a = int(180 * pulse)
                sz = max(1, int(s['size'] * pulse))
                pygame.draw.circle(screen, (220, 230, 250),
                                    (int(s['x']), int(s['y'])), sz)
                if sz >= 2:
                    pygame.draw.circle(screen, (255, 255, 255),
                                        (int(s['x']), int(s['y'])), 1)

        # 3) Distant ocean horizon (subtile horizontale Linien)
        horizon_y = int(SCREEN_H * 0.62)
        for k in range(6):
            ly = horizon_y + k * 18
            alpha = max(0, 60 - k * 9)
            line = pygame.Surface((SCREEN_W, 1), pygame.SRCALPHA)
            line.fill((180, 200, 220, alpha))
            screen.blit(line, (0, ly))

        # 4) Brassweir-Silhouette (Hafenstadt mit Pier am Horizont)
        sil_y = int(SCREEN_H * 0.66)
        sil_col = (8, 6, 4)
        # Felsen-Linie + Häuser-Silhouetten als Polygon
        sil_pts = [
            (0, sil_y + 20), (60, sil_y + 10), (90, sil_y - 4),
            (120, sil_y - 8), (140, sil_y - 22), (170, sil_y - 20),
            (200, sil_y - 32), (240, sil_y - 28), (260, sil_y - 14),
            (290, sil_y - 12), (320, sil_y - 24), (360, sil_y - 22),
            (380, sil_y - 8), (430, sil_y - 8), (460, sil_y - 30),
            (490, sil_y - 28), (520, sil_y - 14), (570, sil_y - 12),
            # Mahnmal-Halle (großes Häuser-Trapezoid in der Mitte)
            (640, sil_y - 12), (640, sil_y - 44), (700, sil_y - 56),
            (760, sil_y - 56), (820, sil_y - 44), (820, sil_y - 12),
            (870, sil_y - 12), (900, sil_y - 26), (940, sil_y - 22),
            (980, sil_y - 30), (1020, sil_y - 28), (1050, sil_y - 14),
            (1090, sil_y - 12), (1120, sil_y - 22), (1170, sil_y - 24),
            (1200, sil_y - 12), (1240, sil_y - 16), (1290, sil_y - 8),
            (1340, sil_y - 14), (1380, sil_y - 8), (1430, sil_y - 18),
            (1480, sil_y - 12), (1520, sil_y - 4), (1560, sil_y + 4),
            (SCREEN_W, sil_y + 14), (SCREEN_W, SCREEN_H), (0, SCREEN_H),
        ]
        pygame.draw.polygon(screen, sil_col, sil_pts)
        # Subtile warme Fenster-Lichter in der Stadt (Pier-Laternen)
        windows = [(700, sil_y - 30), (740, sil_y - 38), (780, sil_y - 30),
                   (200, sil_y - 18), (480, sil_y - 18),
                   (1100, sil_y - 16), (1340, sil_y - 10)]
        for wx, wy in windows:
            flicker = 0.7 + 0.3 * math.sin(t * 3 + wx * 0.01)
            a = int(180 * flicker)
            pygame.draw.circle(screen, (255, 200, 110, a)[:3], (wx, wy), 2)
            glow = pygame.Surface((10, 10), pygame.SRCALPHA)
            pygame.draw.circle(glow, (255, 180, 90, int(60 * flicker)),
                                (5, 5), 5)
            screen.blit(glow, (wx - 5, wy - 5))

        # 5) Drift-Embers (drift langsam nach oben, leichte Sway)
        if self._embers:
            ember_cols = [
                (255, 180, 90), (255, 140, 60),
                (220, 110, 50), (255, 220, 130),
            ]
            for em in self._embers:
                em_t = t
                y = (em['y'] - em['speed'] * em_t) % (SCREEN_H + 40) - 20
                x = em['x'] + math.sin(em_t * em['sway']
                                         + em['phase']) * 14
                col = ember_cols[em['col_idx']]
                sz = em['size']
                # Glow
                glow = pygame.Surface((10, 10), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*col, 100),
                                    (5, 5), int(sz + 2))
                screen.blit(glow, (int(x) - 5, int(y) - 5))
                pygame.draw.circle(screen, col, (int(x), int(y)),
                                    max(1, int(sz)))

        # 6) Vignette außen — fokussiert Blick auf die Mitte
        vig = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for k in range(80):
            a = int(k * 1.6)
            pygame.draw.rect(vig, (0, 0, 0, a),
                              (k, k, SCREEN_W - 2 * k, SCREEN_H - 2 * k), 1)
        screen.blit(vig, (0, 0))

    # ---------- Title Block ----------
    def _draw_title_block(self, screen, t):
        # Pulsierender Hintergrund-Glow hinter dem Titel
        pulse = 0.5 + 0.5 * math.sin(t * 0.8)
        glow_alpha = int(40 + 20 * pulse)
        glow = pygame.Surface((900, 200), pygame.SRCALPHA)
        pygame.draw.ellipse(glow, (220, 180, 110, glow_alpha),
                             (0, 0, 900, 200))
        screen.blit(glow, (SCREEN_W // 2 - 450, 50))
        # X-10 (Update #168): Rotierendes Aspekt-Sigil hinter Logo —
        # 7-zackiger Mahnmal-Stern (Aspekt-Lineage-Lore).
        sigil_surf = pygame.Surface((220, 220), pygame.SRCALPHA)
        sigil_cx = sigil_cy = 110
        angle = t * 0.18
        for i in range(7):
            a = angle + math.tau * i / 7
            outer = 96
            inner = 38
            x_out = sigil_cx + math.cos(a) * outer
            y_out = sigil_cy + math.sin(a) * outer
            x_in = sigil_cx + math.cos(a + math.pi / 7) * inner
            y_in = sigil_cy + math.sin(a + math.pi / 7) * inner
            pygame.draw.line(sigil_surf, (220, 180, 110, 50),
                             (sigil_cx, sigil_cy), (x_out, y_out), 1)
            pygame.draw.circle(sigil_surf, (255, 220, 140, 80),
                                (int(x_out), int(y_out)), 2)
        pygame.draw.circle(sigil_surf, (220, 180, 110, 90),
                            (sigil_cx, sigil_cy), 96, 1)
        pygame.draw.circle(sigil_surf, (220, 180, 110, 60),
                            (sigil_cx, sigil_cy), 36, 1)
        screen.blit(sigil_surf, (SCREEN_W // 2 - 110, 38))

        # Title-Shadow-Stack (vier-Richtungen-Tiefe)
        title_text = 'SHADOWFALL'
        title_y = 100
        for ox, oy, col in [
            (-3, -3, (90, 30, 10)), (3, -3, (90, 30, 10)),
            (-3, 3, (40, 20, 8)),   (3, 3, (40, 20, 8)),
            (0, -1, (255, 240, 180)),  # subtle highlight
        ]:
            sh = self.font_big.render(title_text, True, col)
            r = sh.get_rect(center=(SCREEN_W // 2 + ox, title_y + oy))
            screen.blit(sh, r)
        title = self.font_big.render(title_text, True, GOLD_BRIGHT)
        screen.blit(title, title.get_rect(center=(SCREEN_W // 2, title_y)))

        # Ornament-Divider (Linie mit Mahnmal-Stele-Symbol in der Mitte)
        line_y = 152
        # Linke Linie
        pygame.draw.line(screen, (160, 140, 90),
                          (SCREEN_W // 2 - 230, line_y),
                          (SCREEN_W // 2 - 22, line_y), 1)
        pygame.draw.line(screen, (220, 180, 110),
                          (SCREEN_W // 2 - 200, line_y - 1),
                          (SCREEN_W // 2 - 30, line_y - 1), 1)
        # Rechte Linie
        pygame.draw.line(screen, (160, 140, 90),
                          (SCREEN_W // 2 + 22, line_y),
                          (SCREEN_W // 2 + 230, line_y), 1)
        pygame.draw.line(screen, (220, 180, 110),
                          (SCREEN_W // 2 + 30, line_y - 1),
                          (SCREEN_W // 2 + 200, line_y - 1), 1)
        # Mitte: kleines Raute-Mahnmal-Symbol mit Gold-Fill
        cx_div = SCREEN_W // 2
        diamond = [(cx_div, line_y - 8), (cx_div + 10, line_y),
                   (cx_div, line_y + 8), (cx_div - 10, line_y)]
        pygame.draw.polygon(screen, (40, 30, 16), diamond)
        pygame.draw.polygon(screen, (220, 180, 110), diamond, 1)
        pygame.draw.circle(screen, (255, 220, 130), (cx_div, line_y), 2)

        # Subtitle in „Italic"-Look (per Spacing)
        sub_text = '— W Ä H L E   D E I N E N   P F A D —'
        sub = self.font_med.render(sub_text, True, (200, 180, 140))
        screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, 178)))

        # Velgrad-Lore-Quote in Pergament-Box (zentriert)
        quote = '„Velgrad atmet seinen letzten Atemzug. Du bist sein Mund."'
        qsurf = self.font_small.render(quote, True, (215, 195, 160))
        qw = qsurf.get_width() + 32
        qh = qsurf.get_height() + 12
        qx = SCREEN_W // 2 - qw // 2
        qy = 200
        # Pergament-Hintergrund
        pbg = pygame.Surface((qw, qh), pygame.SRCALPHA)
        pbg.fill((28, 20, 12, 200))
        screen.blit(pbg, (qx, qy))
        # Linien an den Seiten
        pygame.draw.line(screen, (160, 140, 90),
                          (qx, qy), (qx, qy + qh), 1)
        pygame.draw.line(screen, (160, 140, 90),
                          (qx + qw - 1, qy), (qx + qw - 1, qy + qh), 1)
        screen.blit(qsurf, (qx + 16, qy + 6))

    # ---------- Class Cards ----------
    # Update #166: Portrait-Scale-Cache fuer Title-Screen Class-Cards.
    # Skalierte Klassen-Sprites werden 1× geladen und gecached — vermeidet
    # smoothscale-Cost pro Frame fuer 8 Klassen × 2 Sizes (card + detail).
    _portrait_cache: dict = {}

    def _draw_hero_portrait(self, screen, hero_surf, x, y, w, h,
                              accent, t):
        """Grosses Klassen-Portrait im Detail-Panel.

        Layout:
          - Sprite aspect-preserve scaled in das (w, h) Frame
          - Klassen-Akzent-Doppel-Border + Eck-Ornamente
          - Aspekt-Aura hinter dem Sprite (gepulst)
          - Vertikaler Vignette-Fade unten → blendet in Panel-BG
        """
        sw, sh = hero_surf.get_size()
        if sh <= 0:
            return
        # Aspect-fit
        scale = min(w / sw, h / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        cache_key = ('hero', self.selected, new_w, new_h)
        scaled = self._portrait_cache.get(cache_key)
        if scaled is None:
            scaled = pygame.transform.smoothscale(hero_surf, (new_w, new_h))
            self._portrait_cache[cache_key] = scaled

        # Aura hinter dem Sprite (gepulst, klassen-Farbe)
        pulse = 0.55 + 0.45 * math.sin(t * 1.6)
        aura_radius = int(min(new_w, new_h) * 0.55)
        aura_surf = pygame.Surface(
            (aura_radius * 2, aura_radius * 2), pygame.SRCALPHA)
        # Outer soft glow
        pygame.draw.circle(aura_surf, (*accent, int(40 * pulse)),
                            (aura_radius, aura_radius), aura_radius)
        pygame.draw.circle(aura_surf, (*accent, int(80 * pulse)),
                            (aura_radius, aura_radius), int(aura_radius * 0.7))
        aura_cx = x + w // 2
        aura_cy = y + h // 2
        screen.blit(aura_surf, (aura_cx - aura_radius, aura_cy - aura_radius))

        # Sprite zentriert
        blit_x = x + (w - new_w) // 2
        blit_y = y + (h - new_h) // 2
        screen.blit(scaled, (blit_x, blit_y))

        # Vignette-Fade unten (versteckt Sprite-BG-Reste)
        vign = pygame.Surface((w, h), pygame.SRCALPHA)
        for vy in range(h):
            t_v = vy / max(1, h)
            if t_v > 0.78:
                a = int(220 * ((t_v - 0.78) / 0.22))
                pygame.draw.line(vign, (16, 12, 8, a),
                                  (0, vy), (w, vy))
        # Side-Edges
        for ex in range(20):
            a = int(80 * (1.0 - ex / 20))
            pygame.draw.line(vign, (16, 12, 8, a), (ex, 0), (ex, h))
            pygame.draw.line(vign, (16, 12, 8, a),
                              (w - 1 - ex, 0), (w - 1 - ex, h))
        screen.blit(vign, (x, y))

        # Doppel-Rahmen + Eck-Ornamente
        outer = (220, 180, 110)
        pygame.draw.rect(screen, accent, (x, y, w, h), 2)
        pygame.draw.rect(screen, outer, (x - 1, y - 1, w + 2, h + 2), 1)
        corner = 14
        for cx_, cy_, dx, dy in [
            (x, y, 1, 1),
            (x + w - 1, y, -1, 1),
            (x, y + h - 1, 1, -1),
            (x + w - 1, y + h - 1, -1, -1),
        ]:
            pygame.draw.line(screen, outer, (cx_, cy_),
                              (cx_ + corner * dx, cy_), 2)
            pygame.draw.line(screen, outer, (cx_, cy_),
                              (cx_, cy_ + corner * dy), 2)

    def _draw_class_portrait_on_card(self, screen, key, card_rect, accent,
                                       is_sel, t) -> bool:
        """Zeichnet das AI-Klassen-Sprite als Portrait in den oberen Card-Bereich.

        Layout:
          - Portrait-Frame nimmt ~60% der Card-Hoehe oben ein
          - Vertikaler Verlauf von dunkel oben nach transparent unten →
            blendet den Sprite-BG sanft in die Card aus (egal ob Sprite
            transparent oder dark-BG ist)
          - Klassen-Akzent-Ring um den Sprite (gepulst bei is_sel)

        Returnt True wenn AI-Sprite geladen wurde, False fuer Fallback.
        """
        try:
            from . import sprites as _spr
        except ImportError:
            return False
        surf = _spr.get_class_sprite(key)
        if surf is None:
            return False

        # Portrait-Area auf der Card (zentral oben, 50% Card-Hoehe)
        pad_x = 12
        pad_y = 8
        port_w = card_rect.w - 2 * pad_x
        port_h = int(card_rect.h * 0.50) - pad_y
        port_x = card_rect.x + pad_x
        port_y = card_rect.y + pad_y

        # Sprite-aspect-preserving scale ins Portrait-Frame
        sw, sh = surf.get_size()
        if sh <= 0:
            return False
        scale = min(port_w / sw, port_h / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        cache_key = (key, new_w, new_h)
        scaled = self._portrait_cache.get(cache_key)
        if scaled is None:
            scaled = pygame.transform.smoothscale(surf, (new_w, new_h))
            self._portrait_cache[cache_key] = scaled

        # Aura/Akzent-Pulse hinter dem Sprite (klassen-Farbe)
        if is_sel:
            pulse = 0.6 + 0.4 * math.sin(t * 2.4)
            aura_r = 56
            aura = pygame.Surface((aura_r * 2, aura_r * 2), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*accent, int(70 * pulse)),
                                (aura_r, aura_r), aura_r)
            pygame.draw.circle(aura, (*accent, int(100 * pulse)),
                                (aura_r, aura_r), aura_r - 14)
            aura_cx = port_x + port_w // 2
            aura_cy = port_y + port_h // 2
            screen.blit(aura, (aura_cx - aura_r, aura_cy - aura_r))

        # Sprite zentriert ins Portrait-Frame blitten
        blit_x = port_x + (port_w - new_w) // 2
        blit_y = port_y + (port_h - new_h) // 2
        screen.blit(scaled, (blit_x, blit_y))

        # Vignette-Overlay — fade-out unten und an den Raendern zur Card-Farbe.
        # Versteckt unbeabsichtigte Sprite-Backgrounds (z.B. witch/sorceress
        # mit Rest-Dunkelheit) elegant in die Card hinein.
        vign = pygame.Surface((port_w, port_h), pygame.SRCALPHA)
        # Unten-Fade (transparent-zu-dunkel) — soft-blend in stats-Bereich
        for vy in range(port_h):
            t_v = vy / max(1, port_h)
            # Nur die untersten 25% sind sichtbar dunkler
            if t_v > 0.75:
                alpha = int(220 * ((t_v - 0.75) / 0.25))
                pygame.draw.line(vign, (16, 12, 8, alpha),
                                  (0, vy), (port_w, vy))
        # Rand-Vignette (vertikal) — leichtes Darkening an l/r Edges
        edge_w = 16
        for ex in range(edge_w):
            a = int(60 * (1.0 - ex / edge_w))
            pygame.draw.line(vign, (16, 12, 8, a),
                              (ex, 0), (ex, port_h))
            pygame.draw.line(vign, (16, 12, 8, a),
                              (port_w - 1 - ex, 0), (port_w - 1 - ex, port_h))
        screen.blit(vign, (port_x, port_y))

        # Klassen-Akzent-Unterstreichung (1 dicker Strich am Portrait-Fuss)
        underline_y = port_y + port_h - 2
        underline_col = _shade_color(accent, 1.2) if is_sel else accent
        pygame.draw.line(screen, underline_col,
                          (port_x + 4, underline_y),
                          (port_x + port_w - 4, underline_y), 2)
        return True

    def _draw_class_card(self, screen, key, c, rect, is_sel, t,
                         hovered):
        from . import quotes as _q
        fac = _q.class_faction(key)
        accent = c['color']
        # Hover-/Selected-State: Card hebt sich an
        lift = 0
        if is_sel:
            lift = -6 + int(math.sin(t * 2) * 1.5)
        elif hovered:
            lift = -3
        card_rect = rect.move(0, lift)

        # Schatten unter der Card
        sh = pygame.Surface((card_rect.w + 16, 12), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 160),
                             (0, 0, card_rect.w + 16, 12))
        screen.blit(sh, (card_rect.x - 8, card_rect.y + card_rect.h - 2))

        # Card-Hintergrund (Vertikal-Gradient von dunkel zu sehr-dunkel)
        bg = pygame.Surface((card_rect.w, card_rect.h), pygame.SRCALPHA)
        for y in range(card_rect.h):
            t2 = y / card_rect.h
            base = (20, 16, 12) if not is_sel else (36, 28, 18)
            r = int(base[0] + 6 * (1 - t2))
            g = int(base[1] + 4 * (1 - t2))
            b = int(base[2] + 3 * (1 - t2))
            a = 240 if is_sel else 220
            pygame.draw.line(bg, (r, g, b, a), (0, y),
                              (card_rect.w, y))
        screen.blit(bg, card_rect.topleft)

        # Aspekt-Akzent-Band oben (klassen-Farbe)
        band_h = 4
        pygame.draw.rect(screen, accent,
                          (card_rect.x, card_rect.y,
                           card_rect.w, band_h))
        # Heller Akzent-Strich
        light = _shade_color(accent, 1.4)
        pygame.draw.line(screen, light,
                          (card_rect.x, card_rect.y),
                          (card_rect.x + card_rect.w, card_rect.y), 1)

        # Card-Border (selected = dicker + leichter Glow)
        if is_sel:
            glow = pygame.Surface((card_rect.w + 20, card_rect.h + 20),
                                    pygame.SRCALPHA)
            pulse = 0.6 + 0.4 * math.sin(t * 3)
            pygame.draw.rect(glow, (*accent, int(50 * pulse)),
                              (0, 0, card_rect.w + 20,
                               card_rect.h + 20), 6)
            screen.blit(glow, (card_rect.x - 10, card_rect.y - 10))
            pygame.draw.rect(screen, accent, card_rect, 3)
        else:
            pygame.draw.rect(screen, (80, 70, 50), card_rect, 1)

        # Ornamentale Eck-Marker (4 Ecken kleine L-Striche)
        corner = 10
        corner_col = (220, 180, 110) if is_sel else (120, 100, 70)
        for cx_, cy_, dx, dy in [
            (card_rect.x, card_rect.y, 1, 1),
            (card_rect.x + card_rect.w - 1, card_rect.y, -1, 1),
            (card_rect.x, card_rect.y + card_rect.h - 1, 1, -1),
            (card_rect.x + card_rect.w - 1,
             card_rect.y + card_rect.h - 1, -1, -1),
        ]:
            pygame.draw.line(screen, corner_col,
                              (cx_, cy_), (cx_ + corner * dx, cy_), 2)
            pygame.draw.line(screen, corner_col,
                              (cx_, cy_), (cx_, cy_ + corner * dy), 2)

        # Update #166: AI-Klassen-Portrait wenn vorhanden, sonst Fallback
        # auf Procedural-Weapon-Icon.
        ic_cx = card_rect.centerx
        portrait_rendered = self._draw_class_portrait_on_card(
            screen, key, card_rect, accent, is_sel, t)
        if portrait_rendered:
            # ic_cy als Anker fuer Name/Weapon/Divider unter dem Portrait
            # Portrait nimmt 50% der Card-Hoehe (siehe Helper).
            ic_cy = card_rect.y + int(card_rect.h * 0.50) + 4
        else:
            ic_cy = card_rect.y + 56
            # Fallback: alter Weapon-Icon-Render
            aura = pygame.Surface((80, 80), pygame.SRCALPHA)
            pygame.draw.circle(aura, (*accent, 60), (40, 40), 36)
            pygame.draw.circle(aura, (*accent, 100), (40, 40), 28)
            screen.blit(aura, (ic_cx - 40, ic_cy - 40))
            self._draw_class_icon(screen, ic_cx, ic_cy, key, accent, size=30)

        # Faktion-Sigil oben rechts (kleines Glyph)
        if fac:
            sig_x = card_rect.x + card_rect.w - 22
            sig_y = card_rect.y + 14
            self._draw_faction_sigil(screen, sig_x, sig_y,
                                      key, fac['color'])

        # Name
        name = self.font_med.render(c['name'], True,
                                     GOLD_BRIGHT if is_sel else GOLD)
        # Update #166: kompaktere Spacing wenn Portrait-Mode (Portrait
        # nimmt 50% der Card → weniger Platz fuer Text-Bloecke).
        if portrait_rendered:
            name_dy, weap_dy, div_dy, stats_dy = 6, 28, 44, 50
        else:
            name_dy, weap_dy, div_dy, stats_dy = 28, 50, 70, 76
        screen.blit(name, (card_rect.centerx - name.get_width() // 2,
                            ic_cy + name_dy))

        # Weapon-Type-Label (klein, gedeckt)
        weap = c.get('weapon', '')
        if weap:
            ws = self.font_small.render(weap, True, (160, 140, 100))
            screen.blit(ws, (card_rect.centerx - ws.get_width() // 2,
                              ic_cy + weap_dy))

        # Divider-Linie
        dl_y = ic_cy + div_dy
        pygame.draw.line(screen, (60, 50, 36),
                          (card_rect.x + 14, dl_y),
                          (card_rect.x + card_rect.w - 14, dl_y), 1)

        # Mini-Stats (kompakt, 2 Spalten, Mini-Icons)
        stats_top = ic_cy + stats_dy
        stats = [
            (f'HP {c["hp"]}',  (200, 100, 100)),
            (f'MP {c["mp"]}',  (120, 150, 230)),
            (f'DMG {c["damage"]}', (220, 180, 100)),
            (f'SPD {c["speed"]}', (180, 220, 180)),
        ]
        for idx, (txt, col) in enumerate(stats):
            ts = self.font_small.render(txt, True, col)
            sx = card_rect.x + 14 + (idx % 2) * (card_rect.w // 2 - 6)
            sy = stats_top + (idx // 2) * 16
            screen.blit(ts, (sx, sy))

    def _draw_faction_sigil(self, screen, cx, cy, key, color):
        """Klein Sigil pro Faktion (oben rechts auf der Card)."""
        # Hintergrund-Kreis
        pygame.draw.circle(screen, (16, 12, 8), (cx, cy), 9)
        pygame.draw.circle(screen, color, (cx, cy), 9, 1)
        # Per-Klasse-Glyph (vereinfachte Geometrie)
        if key == 'warrior':
            # Eisen-Wachen: Schwert-Kreuz
            pygame.draw.line(screen, color, (cx, cy - 5), (cx, cy + 5), 1)
            pygame.draw.line(screen, color, (cx - 3, cy - 2),
                              (cx + 3, cy - 2), 1)
        elif key == 'monk':
            # Stille Schritte: Lotus-Kreis
            pygame.draw.circle(screen, color, (cx, cy), 4, 1)
            pygame.draw.circle(screen, color, (cx, cy), 2)
        elif key == 'mage':
            # Funkengeborene: Funken-Stern
            for a in range(0, 360, 60):
                x = cx + int(math.cos(math.radians(a)) * 5)
                y = cy + int(math.sin(math.radians(a)) * 5)
                pygame.draw.line(screen, color, (cx, cy), (x, y), 1)
        elif key == 'witch':
            # Knochenwitwen: Schädel-Punkt
            pygame.draw.circle(screen, color, (cx, cy), 4)
            pygame.draw.circle(screen, (10, 5, 8), (cx - 1, cy - 1), 1)
            pygame.draw.circle(screen, (10, 5, 8), (cx + 1, cy - 1), 1)
        elif key == 'ranger':
            # Saatträger: Blatt-Triangel
            pygame.draw.polygon(screen, color, [
                (cx, cy - 5), (cx + 4, cy + 3), (cx - 4, cy + 3)])
        elif key == 'rogue':
            # Mahnmal-Gilde: Kreuz-im-Quadrat
            pygame.draw.rect(screen, color, (cx - 4, cy - 4, 8, 8), 1)
            pygame.draw.line(screen, color, (cx - 3, cy), (cx + 3, cy), 1)
        elif key == 'huntress':
            # Zhar-Eth: Speer-V
            pygame.draw.line(screen, color, (cx - 4, cy - 4),
                              (cx, cy + 4), 1)
            pygame.draw.line(screen, color, (cx + 4, cy - 4),
                              (cx, cy + 4), 1)
        elif key == 'druid':
            # Wandelnde: Drei-Wellen
            for k in range(3):
                yy = cy - 3 + k * 3
                pygame.draw.arc(screen, color, (cx - 4, yy - 1, 8, 3),
                                 math.pi, math.tau, 1)

    # ---------- Detail Panel ----------
    def _draw_detail_panel(self, screen, panel_x, panel_y, panel_w,
                            panel_h, t):
        from . import quotes as _q
        c = CLASSES[self.selected]
        fac = _q.class_faction(self.selected)
        origin = _q.class_origin_quote(self.selected)
        accent = c['color']
        # Update #166: Hero-Portrait belegt rechte 42% des Panels (vertikal),
        # text-width wird auf linke 58% reduziert damit nichts ueberlappt.
        try:
            from . import sprites as _spr
            hero_surf = _spr.get_class_sprite(self.selected)
        except Exception:
            hero_surf = None
        portrait_col_w = int(panel_w * 0.42) if hero_surf is not None else 0
        text_w = panel_w - portrait_col_w - 48 if portrait_col_w > 0 else (panel_w - 48)

        # Panel-Hintergrund (Pergament-Gradient + Vignette)
        pbg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        for y in range(panel_h):
            t2 = y / panel_h
            r = int(20 + 6 * (1 - t2))
            g = int(15 + 4 * (1 - t2))
            b = int(10 + 3 * (1 - t2))
            pygame.draw.line(pbg, (r, g, b, 240), (0, y), (panel_w, y))
        screen.blit(pbg, (panel_x, panel_y))

        # Doppel-Rahmen (innen klassen-Akzent, außen Aithein-Bronze)
        outer = (220, 180, 110)
        pygame.draw.rect(screen, outer,
                          (panel_x - 1, panel_y - 1,
                           panel_w + 2, panel_h + 2), 1)
        pygame.draw.rect(screen, accent,
                          (panel_x + 3, panel_y + 3,
                           panel_w - 6, panel_h - 6), 2)
        # Ornamentale Eck-Striche
        for cx_, cy_, dx, dy in [
            (panel_x + 3, panel_y + 3, 1, 1),
            (panel_x + panel_w - 4, panel_y + 3, -1, 1),
            (panel_x + 3, panel_y + panel_h - 4, 1, -1),
            (panel_x + panel_w - 4, panel_y + panel_h - 4, -1, -1),
        ]:
            pygame.draw.line(screen, outer, (cx_, cy_),
                              (cx_ + 18 * dx, cy_), 2)
            pygame.draw.line(screen, outer, (cx_, cy_),
                              (cx_, cy_ + 18 * dy), 2)

        # Aspekt-Akzent-Band oben
        band_y = panel_y + 12
        pygame.draw.rect(screen, accent,
                          (panel_x + 16, band_y, panel_w - 32, 3))

        # Klassen-Name (Mega-Header mit Glyph)
        pname = self.font_big.render(c['name'], True, accent)
        # Schatten für Tiefe
        pname_sh = self.font_big.render(c['name'], True, (10, 6, 4))
        screen.blit(pname_sh, (panel_x + 26, band_y + 14))
        screen.blit(pname, (panel_x + 24, band_y + 12))
        # Aspekt-Glyph rechts neben Name
        if fac:
            self._draw_faction_sigil(screen,
                                      panel_x + panel_w - 32,
                                      band_y + 22 + pname.get_height() // 2,
                                      self.selected, fac['color'])

        cursor_y = band_y + 12 + pname.get_height() + 14

        # Beschreibung
        self._wrap_text(screen, c['desc'], panel_x + 24, cursor_y,
                         text_w, (220, 210, 190), self.font_small)
        cursor_y += 40

        # Fraktion + Aspekt (mit Sigil + Farb-Balken)
        if fac:
            # Faktion-Header
            fac_label = f"{fac['name'].upper()}  ·  ASPEKT {fac['aspect'].upper()}"
            fs = self.font_small.render(fac_label, True, fac['color'])
            screen.blit(fs, (panel_x + 24, cursor_y))
            cursor_y += fs.get_height() + 6
            # Creed in Pergament-Box
            creed_text = f'„{fac["creed"]}"'
            cs = self.font_small.render(creed_text, True, (210, 190, 150))
            cb_w = cs.get_width() + 24
            cb_h = cs.get_height() + 8
            cb_x = panel_x + 24
            cb_y = cursor_y
            cb_bg = pygame.Surface((cb_w, cb_h), pygame.SRCALPHA)
            cb_bg.fill((30, 24, 16, 200))
            screen.blit(cb_bg, (cb_x, cb_y))
            pygame.draw.line(screen, fac['color'],
                              (cb_x, cb_y), (cb_x, cb_y + cb_h), 2)
            screen.blit(cs, (cb_x + 12, cb_y + 4))
            cursor_y += cb_h + 12

        # Origin-Quote (mehrzeilig, in Italic-Style)
        if origin:
            oq_label = self.font_small.render('LEGENDE',
                                                True, (200, 170, 110))
            screen.blit(oq_label, (panel_x + 24, cursor_y))
            cursor_y += oq_label.get_height() + 4
            self._wrap_text(screen, f'„{origin}"',
                             panel_x + 24, cursor_y,
                             text_w, (225, 215, 195),
                             self.font_small)

        # Update #166: Hero-Portrait rechts (zwischen Name-Header und Skills)
        if hero_surf is not None and portrait_col_w > 0:
            hero_x = panel_x + panel_w - portrait_col_w - 12
            hero_y = band_y + 14
            hero_h = panel_h - (hero_y - panel_y) - 80   # bis ueber Skills
            hero_w = portrait_col_w
            self._draw_hero_portrait(
                screen, hero_surf, hero_x, hero_y, hero_w, hero_h,
                accent, t)

        # Starter-Skills am unteren Panel-Rand
        skills_y = panel_y + panel_h - 64
        # Divider
        pygame.draw.line(screen, (90, 70, 40),
                          (panel_x + 24, skills_y - 8),
                          (panel_x + panel_w - 24, skills_y - 8), 1)
        sl = self.font_small.render('★  STARTER-SKILLS  ★',
                                     True, (220, 200, 150))
        screen.blit(sl, (panel_x + 24, skills_y))
        # Skills aus CLASS_KEYMAP (Update #23 — klassen-spezifisch)
        try:
            from .skills import CLASS_KEYMAP, SKILL_INFO
            pool = CLASS_KEYMAP.get(self.selected, [])[:3]
            sk_names = []
            for sid in pool:
                info = SKILL_INFO.get(sid, {})
                sk_names.append(info.get('name', sid.title()))
            sk_text = '  ·  '.join(sk_names) if sk_names else '—'
        except Exception:
            sk_text = ', '.join(s.title() for s in c['skills'][1:])
        self._wrap_text(screen, sk_text, panel_x + 24,
                         skills_y + 18, panel_w - 48,
                         (200, 200, 210), self.font_small)

    # ---------- Buttons ----------
    def _draw_arrow_polygon(self, screen, cx, cy, color, size=10):
        """Zeichnet einen Play-Pfeil als Polygon (statt unrendered „►")."""
        pts = [
            (cx - size // 2, cy - size),
            (cx + size, cy),
            (cx - size // 2, cy + size),
        ]
        pygame.draw.polygon(screen, color, pts)
        # Outline für Tiefe
        pygame.draw.polygon(screen, (60, 40, 12), pts, 1)

    def _draw_button(self, screen, rect, label, text_col, bg_col,
                      border_col, hovered, arrow=False):
        # Schatten unter Button
        sh = pygame.Surface((rect.w + 12, 10), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 180),
                             (0, 0, rect.w + 12, 10))
        screen.blit(sh, (rect.x - 6, rect.y + rect.h - 2))

        # Hover-Lift
        r = rect.copy()
        if hovered:
            r = r.move(0, -3)

        # Vertikal-Gradient
        bg = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        for y in range(r.h):
            t = y / r.h
            br = int(bg_col[0] + 18 * (1 - t))
            bg2 = int(bg_col[1] + 12 * (1 - t))
            bb = int(bg_col[2] + 6 * (1 - t))
            pygame.draw.line(bg, (br, bg2, bb, 250), (0, y), (r.w, y))
        screen.blit(bg, r.topleft)

        # Border + Top-Akzent
        pygame.draw.line(screen, _shade_color(border_col, 1.4),
                          (r.x, r.y), (r.x + r.w, r.y), 2)
        pygame.draw.rect(screen, border_col, r, 2)

        # Hover-Glow
        if hovered:
            glow = pygame.Surface((r.w + 16, r.h + 16), pygame.SRCALPHA)
            pygame.draw.rect(glow, (*border_col, 80),
                              (0, 0, r.w + 16, r.h + 16), 4)
            screen.blit(glow, (r.x - 8, r.y - 8))

        # Inhalt: Optional-Pfeil + Label
        lbl_surf = self.font_med.render(label, True, text_col)
        if arrow:
            arrow_x = r.x + 22
            arrow_y = r.centery
            self._draw_arrow_polygon(screen, arrow_x, arrow_y,
                                       text_col, size=8)
            lbl_x = arrow_x + 22
        else:
            lbl_x = r.centerx - lbl_surf.get_width() // 2
        screen.blit(lbl_surf,
                     (lbl_x, r.centery - lbl_surf.get_height() // 2))

    def draw(self, screen):
        if self._embers is None:
            self._init_embers()
        t = pygame.time.get_ticks() * 0.001
        # 1) Atmospheric Background
        self._draw_atmospheric_bg(screen, t)
        # 2) Title-Block
        self._draw_title_block(screen, t)

        # 3) Klassen-Cards 4×2 Grid
        mx, my = pygame.mouse.get_pos()
        keys = list(CLASSES.keys())
        cards_per_row = 4
        card_w, card_h = 180, 198
        row_gap = 14
        col_gap = 14
        grid_w = cards_per_row * card_w + (cards_per_row - 1) * col_gap
        grid_x = 30
        grid_y = 254
        self._class_rects = {}
        for i, key in enumerate(keys):
            c = CLASSES[key]
            row = i // cards_per_row
            col = i % cards_per_row
            cx_card = grid_x + col * (card_w + col_gap)
            cy_card = grid_y + row * (card_h + row_gap)
            rect = pygame.Rect(cx_card, cy_card, card_w, card_h)
            self._class_rects[key] = rect
            is_sel = (key == self.selected)
            hovered = rect.collidepoint(mx, my) and not is_sel
            self._draw_class_card(screen, key, c, rect, is_sel, t, hovered)

        # 4) Detail Panel
        panel_x = grid_x + grid_w + 28
        panel_y = grid_y
        panel_w = SCREEN_W - panel_x - 30
        panel_h = card_h * 2 + row_gap
        self._draw_detail_panel(screen, panel_x, panel_y, panel_w,
                                  panel_h, t)

        # 5) Buttons
        bw, bh = 240, 56
        gap = 22
        buttons = []
        if self.save_exists:
            buttons.append(('continue', 'Weiter',
                             (255, 240, 200), (40, 30, 12),
                             (220, 180, 110), True))
        buttons.append(('adventure', 'Abenteuer',
                         (255, 240, 200), (50, 35, 14),
                         (220, 180, 110), True))
        # Update #121: Endlos-Modus-Button entfernt (kein Survival mehr).
        total_w = bw * len(buttons) + gap * (len(buttons) - 1)
        bx_start = SCREEN_W // 2 - total_w // 2
        by = SCREEN_H - 90
        self._continue_rect = None
        self._adv_rect = None
        self._surv_rect = None    # Kompat-Stub für alte Code-Pfade
        for i, (kind, label, text_col, bg_col, border, arrow) in enumerate(buttons):
            rect = pygame.Rect(bx_start + i * (bw + gap), by, bw, bh)
            if kind == 'continue':
                self._continue_rect = rect
            elif kind == 'adventure':
                self._adv_rect = rect
            hovered = rect.collidepoint(mx, my)
            self._draw_button(screen, rect, label, text_col,
                                bg_col, border, hovered, arrow=arrow)

        # 6) Footer-Hint
        hint = self.font_small.render(
            'KLICK eine Klasse · ENTER startet Abenteuer · ESC beendet',
            True, (140, 130, 110))
        screen.blit(hint, hint.get_rect(center=(SCREEN_W // 2,
                                                  SCREEN_H - 22)))

    def _draw_class_icon(self, screen, cx, cy, key, color, size=22):
        """Klassen-Icon: Waffe als Pictogramm im Münz-Kreis.

        size = Radius des Hintergrund-Kreises. Die Waffen-Geometrie
        skaliert proportional. Update #25: größer + mit Innen-Glanz.
        """
        # Hintergrund-Kreis mit Tiefe (3 Lagen für 3D-Münz-Look)
        pygame.draw.circle(screen, (12, 10, 6), (cx, cy + 1), size + 2)
        pygame.draw.circle(screen, (28, 22, 14), (cx, cy), size + 1)
        pygame.draw.circle(screen, color, (cx, cy), size)
        # Innen-Schatten (oben dunkler Halbkreis)
        pygame.draw.circle(screen, _shade_color(color, 0.7),
                            (cx, cy - size // 4), size - 2)
        pygame.draw.circle(screen, color, (cx, cy + 2), size - 4)
        # Highlight oben-links
        hl = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.ellipse(hl, (255, 255, 255, 90),
                             (size // 3, size // 4, size // 2, size // 3))
        screen.blit(hl, (cx - size, cy - size))
        # Doppel-Rand: Gold außen, Dunkel innen
        pygame.draw.circle(screen, GOLD, (cx, cy), size + 1, 2)
        pygame.draw.circle(screen, (12, 8, 4), (cx, cy), size, 1)
        dark = tuple(max(0, c - 70) for c in color[:3])
        white = (250, 240, 220)
        s = size / 22.0  # Skalierungs-Faktor relativ zur Original-Größe

        def _scaled(*pts):
            return [(cx + int(px * s), cy + int(py * s)) for px, py in pts]

        if key == 'warrior':
            # Mace: dicker Schaft + Kopf mit Spikes
            pygame.draw.line(screen, dark, *_scaled((-8, 14), (8, -14)),
                             max(2, int(5 * s)))
            head_cx = cx + int(8 * s)
            head_cy = cy + int(-14 * s)
            pygame.draw.circle(screen, white, (head_cx, head_cy),
                                max(3, int(8 * s)))
            pygame.draw.circle(screen, dark, (head_cx, head_cy),
                                max(3, int(8 * s)), 1)
            # 4 Spikes
            for a_deg in (0, 90, 180, 270):
                a = math.radians(a_deg)
                px = head_cx + int(math.cos(a) * 10 * s)
                py = head_cy + int(math.sin(a) * 10 * s)
                pygame.draw.line(screen, dark, (head_cx, head_cy),
                                  (px, py), max(1, int(2 * s)))
        elif key == 'monk':
            # Quarterstaff: lange Diagonale + Endknöpfe
            pygame.draw.line(screen, white, *_scaled((-15, -15), (15, 15)),
                             max(2, int(4 * s)))
            for px, py in ((-15, -15), (15, 15)):
                bx = cx + int(px * s)
                by = cy + int(py * s)
                pygame.draw.circle(screen, dark, (bx, by),
                                    max(2, int(4 * s)))
                pygame.draw.circle(screen, white, (bx, by),
                                    max(2, int(4 * s)), 1)
        elif key == 'mage':
            # Wand mit großem Edelstein
            pygame.draw.line(screen, (200, 160, 100),
                              *_scaled((-12, 12), (6, -6)),
                              max(2, int(3 * s)))
            gem_cx = cx + int(6 * s)
            gem_cy = cy + int(-10 * s)
            gem_size = max(4, int(8 * s))
            pygame.draw.polygon(screen, white, [
                (gem_cx, gem_cy - gem_size),
                (gem_cx + gem_size, gem_cy),
                (gem_cx, gem_cy + gem_size),
                (gem_cx - gem_size, gem_cy)])
            pygame.draw.polygon(screen, dark, [
                (gem_cx, gem_cy - gem_size),
                (gem_cx + gem_size, gem_cy),
                (gem_cx, gem_cy + gem_size),
                (gem_cx - gem_size, gem_cy)], 1)
            # Inneres Glanz-Highlight (kleines Dreieck oben)
            pygame.draw.polygon(screen, (255, 255, 255), [
                (gem_cx, gem_cy - gem_size + 2),
                (gem_cx + gem_size // 2, gem_cy - 2),
                (gem_cx - 1, gem_cy - 2)])
        elif key == 'witch':
            # Detailierter Schädel
            sk_r = max(7, int(11 * s))
            pygame.draw.circle(screen, white, (cx, cy - int(3 * s)), sk_r)
            pygame.draw.circle(screen, dark, (cx, cy - int(3 * s)), sk_r, 1)
            # Augenhöhlen
            eye_r = max(2, int(3 * s))
            pygame.draw.circle(screen, (10, 5, 8),
                                (cx - int(5 * s), cy - int(5 * s)), eye_r)
            pygame.draw.circle(screen, (10, 5, 8),
                                (cx + int(5 * s), cy - int(5 * s)), eye_r)
            # Nasenloch
            pygame.draw.polygon(screen, (10, 5, 8), _scaled(
                (-2, -1), (2, -1), (0, 3)))
            # Kiefer-Zähne
            jaw_y = cy + int(5 * s)
            pygame.draw.rect(screen, white,
                              (cx - int(6 * s), jaw_y,
                               int(12 * s), int(6 * s)))
            for tx in (-4, -2, 0, 2, 4):
                pygame.draw.line(screen, (10, 5, 8),
                                  (cx + int(tx * s), jaw_y),
                                  (cx + int(tx * s),
                                   jaw_y + int(6 * s)), 1)
        elif key == 'ranger':
            # Bow + diagonaler Pfeil
            arc_rect = (cx - int(14 * s), cy - int(14 * s),
                         int(12 * s), int(28 * s))
            pygame.draw.arc(screen, white, arc_rect, -1.3, 1.3,
                             max(2, int(3 * s)))
            # Sehne
            pygame.draw.line(screen, dark,
                              (cx - int(8 * s), cy - int(12 * s)),
                              (cx - int(8 * s), cy + int(12 * s)), 1)
            # Pfeil
            pygame.draw.line(screen, white, *_scaled((-8, 0), (12, 0)),
                             max(2, int(2 * s)))
            pygame.draw.polygon(screen, dark, _scaled(
                (12, 0), (6, -4), (6, 4)))
            # Fiedern
            pygame.draw.line(screen, dark, *_scaled((-8, -2), (-12, -4)), 1)
            pygame.draw.line(screen, dark, *_scaled((-8, 2), (-12, 4)), 1)
        elif key == 'rogue':
            # Crossbow: T-Body + Bolt
            pygame.draw.rect(screen, dark,
                              (cx - int(14 * s), cy - int(2 * s),
                               int(28 * s), int(5 * s)))
            pygame.draw.rect(screen, white,
                              (cx - int(2 * s), cy - int(12 * s),
                               int(4 * s), int(18 * s)))
            # Sehne
            pygame.draw.line(screen, white,
                              (cx - int(14 * s), cy),
                              (cx + int(14 * s), cy), 1)
            # Bolt (diagonal)
            pygame.draw.line(screen, white, *_scaled((0, 0), (14, -5)),
                             max(2, int(2 * s)))
            pygame.draw.polygon(screen, white, _scaled(
                (14, -5), (10, -8), (10, -2)))
        elif key == 'huntress':
            # Langer Speer mit Spitze + Federn
            pygame.draw.line(screen, (160, 120, 80),
                              *_scaled((-15, 15), (8, -8)),
                              max(2, int(4 * s)))
            # Spitze
            pygame.draw.polygon(screen, white, _scaled(
                (8, -14), (14, -8), (8, -2), (4, -8)))
            pygame.draw.polygon(screen, dark, _scaled(
                (8, -14), (14, -8), (8, -2), (4, -8)), 1)
            # Federn am unteren Ende
            for k in range(-2, 3):
                ox = k * 2
                pygame.draw.line(screen, white,
                                  (cx + int((-15 + ox) * s),
                                   cy + int(15 * s)),
                                  (cx + int((-18 + ox) * s),
                                   cy + int(12 * s)), 1)
        elif key == 'druid':
            # 3 Klauen + Pflanzen-Element
            for ox in (-8, 0, 8):
                ay = cy - int(10 * s)
                by_ = cy + int(8 * s)
                pygame.draw.line(screen, white,
                                  (cx + int(ox * s), ay),
                                  (cx + int(ox * s), by_),
                                  max(2, int(3 * s)))
                # Krallen-Hook am Boden
                pygame.draw.polygon(screen, white, [
                    (cx + int(ox * s) - 3, by_),
                    (cx + int(ox * s) + 3, by_),
                    (cx + int(ox * s), by_ + int(5 * s))])
                pygame.draw.polygon(screen, dark, [
                    (cx + int(ox * s) - 3, by_),
                    (cx + int(ox * s) + 3, by_),
                    (cx + int(ox * s), by_ + int(5 * s))], 1)
            # Blatt-Marker oben
            pygame.draw.polygon(screen, (130, 200, 120), _scaled(
                (-3, -14), (3, -14), (0, -10)))
        else:
            pygame.draw.circle(screen, white, (cx, cy), int(8 * s))

    def _wrap_text(self, screen, text, x, y, max_w, color, font):
        words = text.split(' ')
        line = ''
        cy = y
        for word in words:
            test = line + (' ' if line else '') + word
            if font.size(test)[0] > max_w:
                if line:
                    surf = font.render(line, True, color)
                    screen.blit(surf, (x, cy))
                    cy += font.get_height() + 2
                line = word
            else:
                line = test
        if line:
            surf = font.render(line, True, color)
            screen.blit(surf, (x, cy))


# ============================================================
# SKILL-TREE-UI (Universal + Klasse + Auren)
# ============================================================
class ShrineUI:
    """W-12 (Update #80): Mahnmal-Schrein-Modal.

    Spielt am zentralen Mahnmal-Stelen in Brassweir. Spieler verzehrt
    Mahnmal-Marken I..VII für permanente Aspekt-Blessings (max 5 Stacks
    pro Aspekt). Lore-Bibel 6.4 — Aspekt-Pakt-Mechanik.
    """
    ASPECT_NAMES = {
        1: ('Kharn',       (200, 80, 80),
            '+5 % Schaden / Stack'),
        2: ('Nheyra',      (140, 200, 240),
            '+5 % Maximales Leben / Stack'),
        3: ('Ousen',       (200, 180, 120),
            '+0.5 HP/s Regeneration / Stack'),
        4: ('Valsa',       (240, 130, 70),
            '+4 % Feuerschaden / Stack'),
        5: ('Im-Nesh',     (170, 200, 255),
            '+4 % Blitzschaden / Stack'),
        6: ('Shulavh',     (180, 240, 180),
            '+4 % Frostschaden / Stack'),
        7: ('Der Siebte',  (220, 200, 240),
            '+2 % auf alle Kategorien / Stack'),
    }

    def __init__(self, font_med, font_small):
        self.font_med = font_med
        self.font_small = font_small
        self._row_rects = {}  # aspect_id → rect

    def modal_rect(self):
        w, h = 980, 660
        return pygame.Rect(SCREEN_W // 2 - w // 2,
                            SCREEN_H // 2 - h // 2, w, h)

    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        for aid, rect in self._row_rects.items():
            if rect.collidepoint(mx, my):
                ok = progression.try_invest_mahnmal_blessing(game.player, aid)
                if ok:
                    name = self.ASPECT_NAMES[aid][0]
                    new_stacks = game.player.mahnmal_blessings.get(aid, 0)
                    game.toast(
                        f'Mahnmal-Marke {self._roman(aid)} verzehrt → '
                        f'„Pakt des {name}" Stufe {new_stacks}',
                        self.ASPECT_NAMES[aid][1])
                    # HP/MP an neues Maximum anpassen
                    eff = progression.effective(game.player)
                    if game.player.hp > eff['hp_max']:
                        game.player.hp = eff['hp_max']
                else:
                    marken = game.player.mahnmal_marken.get(aid, 0)
                    bless = game.player.mahnmal_blessings.get(aid, 0)
                    if marken <= 0:
                        game.toast(
                            f'Keine Mahnmal-Marke {self._roman(aid)} im Bestand.',
                            (180, 140, 120))
                    elif bless >= 5:
                        game.toast(
                            f'Pakt des {self.ASPECT_NAMES[aid][0]} ist '
                            f'bereits voll erinnert (Stufe 5).',
                            (200, 180, 120))
                return True
        return True

    @staticmethod
    def _roman(n):
        return {1: 'I', 2: 'II', 3: 'III', 4: 'IV',
                5: 'V', 6: 'VI', 7: 'VII'}.get(n, str(n))

    def draw(self, screen, game):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (0, 0))
        modal = self.modal_rect()
        # Stein-Tafel-Hintergrund
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((28, 22, 16, 245))
        screen.blit(bg, modal.topleft)
        pygame.draw.rect(screen, (154, 118, 66), modal, 3)
        pygame.draw.rect(screen, (60, 46, 30), modal, 1)
        # Header
        title = self.font_med.render('MAHNMAL-SCHREIN', True, (243, 213, 114))
        screen.blit(title, (modal.centerx - title.get_width() // 2,
                             modal.y + 18))
        sub = self.font_small.render(
            'Verzehre Mahnmal-Marken, um an die Aspekte zu erinnern.',
            True, (180, 160, 130))
        screen.blit(sub, (modal.centerx - sub.get_width() // 2,
                           modal.y + 54))
        sub2 = self.font_small.render(
            'Klick auf einen Aspekt · ESC: Schließen',
            True, (160, 140, 110))
        screen.blit(sub2, (modal.centerx - sub2.get_width() // 2,
                            modal.y + 76))
        # 7 Zeilen
        row_y = modal.y + 110
        row_h = 70
        row_w = modal.w - 80
        row_x = modal.x + 40
        self._row_rects = {}
        marken = getattr(game.player, 'mahnmal_marken', {})
        bless = getattr(game.player, 'mahnmal_blessings', {})
        for aid in range(1, 8):
            name, color, desc = self.ASPECT_NAMES[aid]
            rect = pygame.Rect(row_x, row_y, row_w, row_h - 4)
            self._row_rects[aid] = rect
            cur_b = bless.get(aid, 0)
            cur_m = marken.get(aid, 0)
            can = cur_m > 0 and cur_b < 5
            # Background-Tint
            tint = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            tint.fill((40, 32, 24, 220) if can else (24, 20, 16, 220))
            screen.blit(tint, rect.topleft)
            pygame.draw.rect(screen, color if can else (80, 70, 60),
                              rect, 2)
            # Roman + Name
            head = self.font_small.render(
                f'{self._roman(aid)}  ·  Pakt des {name}',
                True, color)
            screen.blit(head, (rect.x + 14, rect.y + 6))
            # Desc
            d_col = (200, 190, 170) if can else (140, 130, 110)
            screen.blit(self.font_small.render(desc, True, d_col),
                         (rect.x + 14, rect.y + 26))
            # Stacks (5 Pips)
            for k in range(5):
                pip_x = rect.right - 220 + k * 18
                pip_y = rect.y + 30
                filled = k < cur_b
                pygame.draw.circle(
                    screen, color if filled else (60, 50, 40),
                    (pip_x, pip_y), 6)
                if filled:
                    pygame.draw.circle(screen, (255, 230, 180),
                                        (pip_x, pip_y), 6, 1)
            # Marken-Counter
            txt_col = (220, 220, 200) if cur_m > 0 else (140, 130, 110)
            screen.blit(self.font_small.render(
                f'Marken: {cur_m}', True, txt_col),
                (rect.right - 110, rect.y + 26))
            # Hint
            if cur_b >= 5:
                hint = '✓ voll erinnert'
                hcol = (140, 220, 140)
            elif cur_m > 0:
                hint = '+ verzehren'
                hcol = color
            else:
                hint = '— keine Marke —'
                hcol = (140, 130, 110)
            hs = self.font_small.render(hint, True, hcol)
            screen.blit(hs, (rect.right - hs.get_width() - 14,
                              rect.y + 6))
            row_y += row_h


class TravelUI:
    """Update #114 (WELT_AUFBAU 1.3): Mahnmal-Stelen-Fast-Travel-Modal.

    Spielt an den Mahnmal-Stelen in Outpost-Camps. Listet alle aktuell
    freigeschalteten Vorposten + Brassweir als Reise-Ziele. Klick auf
    ein Ziel → `game.travel_to_outpost(key)` ruft `enter_outpost` /
    `enter_town` auf.

    Lore-Anker: Mahnmal-Stelen sind über die Mahnmal-Gilde verbunden;
    eine Stele weiß, wohin die anderen Stelen führen.

    Brassweir-Mahnmal bleibt der Aspekt-Schrein (W-13 ShrineUI). Outpost-
    Mahnmals sind die Wegmarker.
    """

    def __init__(self, font_med, font_small):
        self.font_med = font_med
        self.font_small = font_small
        self._row_rects = {}   # outpost_key → rect

    def modal_rect(self):
        w, h = 900, 600
        return pygame.Rect(SCREEN_W // 2 - w // 2,
                            SCREEN_H // 2 - h // 2, w, h)

    def _destinations(self, game):
        """Returnt geordnete Liste [(key, cfg)] der erreichbaren Ziele.

        Brassweir first, dann freigeschaltete Outposts nach Akt.
        Aktueller Outpost ist enthalten aber als „bereits hier" markiert.
        """
        from . import outposts as _op
        unlocked = _op.unlocked_outposts(game.player)
        current = getattr(game, 'outpost_id', None)
        out = []
        # Brassweir immer dabei (Persistenz-Hub)
        out.append(('brassweir', _op.OUTPOSTS['brassweir']))
        # Andere Outposts in Akt-Reihenfolge
        items = [(k, _op.OUTPOSTS[k]) for k in unlocked]
        items.sort(key=lambda kv: kv[1]['akt'])
        for k, cfg in items:
            out.append((k, cfg))
        return out, current

    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        for key, rect in self._row_rects.items():
            if rect.collidepoint(mx, my):
                if key == getattr(game, 'outpost_id', None):
                    # bereits hier
                    game.toast('Du bist bereits hier.', (200, 180, 140))
                    return True
                # Reisen!
                if key == 'brassweir':
                    game.enter_town()
                else:
                    game.enter_outpost(key)
                game.modal = None
                return True
        return True

    def draw(self, screen, game):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 220))
        screen.blit(overlay, (0, 0))
        modal = self.modal_rect()
        # Pergament-Hintergrund
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((28, 22, 16, 245))
        screen.blit(bg, modal.topleft)
        pygame.draw.rect(screen, (154, 118, 66), modal, 3)
        pygame.draw.rect(screen, (60, 46, 30), modal, 1)

        # Header
        title = self.font_med.render('MAHNMAL-WEGE', True, (243, 213, 114))
        screen.blit(title, (modal.centerx - title.get_width() // 2,
                             modal.y + 18))
        sub = self.font_small.render(
            '„Eine Stele weiß, wohin die anderen führen."',
            True, (180, 160, 130))
        screen.blit(sub, (modal.centerx - sub.get_width() // 2,
                           modal.y + 54))
        sub2 = self.font_small.render(
            'Klick auf ein Ziel · ESC: Schließen',
            True, (160, 140, 110))
        screen.blit(sub2, (modal.centerx - sub2.get_width() // 2,
                            modal.y + 76))

        # Destinations
        rows, current = self._destinations(game)
        row_y = modal.y + 110
        row_h = 64
        row_w = modal.w - 80
        row_x = modal.x + 40
        self._row_rects = {}
        for key, cfg in rows:
            rect = pygame.Rect(row_x, row_y, row_w, row_h - 4)
            self._row_rects[key] = rect
            is_current = (key == current) or (
                key == 'brassweir' and game.area == 'town')
            color = cfg['color']
            # Hintergrund
            tint = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            if is_current:
                tint.fill((50, 40, 30, 200))
            else:
                tint.fill((34, 28, 22, 230))
            screen.blit(tint, rect.topleft)
            pygame.draw.rect(screen, color if not is_current
                              else (120, 100, 80), rect, 2)
            # Akt-Marker links
            akt_lbl = f"Akt {cfg['akt']}" if cfg['akt'] > 0 \
                else 'Hub'
            ak_surf = self.font_small.render(akt_lbl, True,
                                              (200, 180, 140))
            screen.blit(ak_surf, (rect.x + 14, rect.y + 8))
            # Name
            name_color = color if not is_current else (160, 150, 130)
            name = self.font_med.render(cfg['region_name'], True,
                                         name_color)
            screen.blit(name, (rect.x + 100, rect.y + 4))
            # Desc unter Name (gekürzt)
            desc = cfg.get('short_desc', '')
            if len(desc) > 88:
                desc = desc[:85] + '…'
            d_col = (180, 170, 150) if not is_current else (130, 120, 100)
            d_surf = self.font_small.render(desc, True, d_col)
            screen.blit(d_surf, (rect.x + 100, rect.y + 32))
            # Status-Marker rechts
            if is_current:
                lbl = self.font_small.render('• Hier •', True,
                                               (200, 200, 160))
            else:
                lbl = self.font_small.render('→ Reisen', True, color)
            screen.blit(lbl, (rect.right - lbl.get_width() - 14,
                                rect.y + (row_h - lbl.get_height()) // 2 - 2))
            row_y += row_h


class SkillTreeUI:
    # H-15 (Update #76): Filter-Tags für Search & Filter im Skill-Tree.
    # Heuristik aus TREE_NODES-Effekten + Klassen-Knoten-Namen.
    # 'all' = kein Filter; Cycle via F-Taste im Modal.
    FILTER_TAGS = ('all', 'defense', 'offense', 'utility')
    FILTER_LABELS = {
        'all':      'Alle',
        'defense':  'Verteidigung',
        'offense':  'Angriff',
        'utility':  'Wandel & Pakt',
    }
    # Universal-Node-Mapping nach Tag (für TREE_NODES keys).
    _UNI_TAGS = {
        'vit':      'defense', 'arc':     'defense',
        'res':      'defense', 'regen':   'defense',
        'pow':      'offense', 'prc':     'offense',
        'crit_dmg': 'offense',
        'agi':      'utility', 'cnc':     'utility',
        'wis':      'utility', 'rich':    'utility',
        'magnet':   'utility',
    }

    def __init__(self, font_med, font_small):
        self.font_med = font_med
        self.font_small = font_small
        self._node_rects = {}     # universal
        self._cnode_rects = {}    # class
        self._aura_rects = {}     # aura toggles
        # H-13 (Update #75): Hover-Preview — gespeicherter (kind, key)
        # damit draw() den fokussierten Knoten extra hervorhebt.
        self._hover_node = None   # ('skill'|'class', key) | None
        # H-15 (Update #76): Filter-State (cycelt via F-Taste)
        self.filter_tag = 'all'
        # H-14 (Update #76): Plan-Path-Mode — Vorab-Markierung von
        # Knoten ohne Punkte zu zahlen; Enter/Confirm-Button kauft alle.
        # Toggle via P-Taste; planned[(kind, node_id)] = order_index.
        self.plan_mode = False
        self.planned = {}  # {(kind, node_id): order_int}
        self._plan_seq = 0
        self._confirm_rect = None  # für Click-Detection
        # H-12 (Update #77): Allocation-Animation — pro erfolgreichem
        # Invest wird ein Burst + Ring eingereiht. Liste von Dicts:
        #   {'rect': pygame.Rect, 'age': float, 'life': float,
        #    'color': (r,g,b), 'pop': bool}
        self._anims = []
        self._last_anim_tick_ms = pygame.time.get_ticks()

    def modal_rect(self):
        w, h = 1280, 800
        return pygame.Rect(SCREEN_W // 2 - w // 2, SCREEN_H // 2 - h // 2, w, h)

    def cycle_filter(self):
        """H-15 (Update #76): Wechselt zum nächsten Filter-Tag."""
        idx = self.FILTER_TAGS.index(self.filter_tag)
        self.filter_tag = self.FILTER_TAGS[(idx + 1) % len(self.FILTER_TAGS)]

    # PLAN H-16 (Update #96): Skill-Tree Mouse-Wheel-Zoom für die Tooltip-
    # Card-Größe. Da das Tree-Layout flach ist (kein Canvas), zoomt das
    # Wheel den Hover-Tooltip + Pulse-Glow-Größe.
    ZOOM_LEVELS = (0.85, 1.0, 1.15, 1.30)

    def wheel_zoom(self, delta):
        cur_idx = getattr(self, '_zoom_idx', 1)
        cur_idx += 1 if delta > 0 else -1
        cur_idx = max(0, min(len(self.ZOOM_LEVELS) - 1, cur_idx))
        self._zoom_idx = cur_idx
        self.zoom = self.ZOOM_LEVELS[cur_idx]

    def _matches_filter(self, kind, key, node):
        """H-15: True wenn Knoten zum aktuellen Filter passt."""
        if self.filter_tag == 'all':
            return True
        if kind == 'skill':
            return self._UNI_TAGS.get(key) == self.filter_tag
        # Klassen-Knoten: heuristisch nach Effekt-Keys.
        d = node
        if self.filter_tag == 'defense':
            return any(k in d for k in ('hp', 'mp', 'dmg_red',
                                          'hp_regen', 'block',
                                          'armor', 'shield'))
        if self.filter_tag == 'offense':
            return any(k in d for k in ('dmg_pct', 'crit', 'crit_dmg',
                                          'free_cast', 'aoe'))
        if self.filter_tag == 'utility':
            return any(k in d for k in ('speed', 'cdr', 'xp_bonus',
                                          'gold_bonus', 'magnet'))
        return True

    def toggle_plan_mode(self, game):
        """H-14 (Update #76): Plan-Mode an/aus. Beim Verlassen werden
        Plan-Einträge gelöscht (Reset)."""
        self.plan_mode = not self.plan_mode
        if not self.plan_mode:
            self.planned.clear()
            self._plan_seq = 0
            game.toast('Plan-Modus verlassen', (180, 200, 220))
        else:
            game.toast('Plan-Modus aktiv (P=Aus · Enter=Kaufen · Klick=markieren)',
                        (140, 230, 220))

    def _toggle_plan_node(self, kind, key, game):
        """H-14: Markiert/entmarkiert Knoten als geplant.
        Validiert Max-Stufe und nicht-bereits-allocated."""
        from .constants import CLASS_TREE_NODES as _ctn
        if kind == 'skill':
            node = TREE_NODES.get(key)
            cur = game.player.tree.get(key, 0)
        else:
            node = _ctn.get(game.player.cls, {}).get(key)
            cur = game.player.class_tree.get(key, 0)
        if node is None:
            return
        max_lvl = node['max']
        tag = (kind, key)
        already_planned = sum(1 for k in self.planned if k == tag)
        if tag in self.planned:
            del self.planned[tag]
        elif cur + already_planned < max_lvl:
            self._plan_seq += 1
            self.planned[tag] = self._plan_seq

    def commit_plan(self, game):
        """H-14 (Update #76): Kauft alle geplanten Knoten in Order-
        Reihenfolge — solange Punkte verfügbar sind."""
        if not self.planned:
            game.toast('Kein Plan zum Kaufen.', (200, 180, 140))
            return
        ordered = sorted(self.planned.items(), key=lambda kv: kv[1])
        bought = 0
        for (kind, key), _idx in ordered:
            if kind == 'skill':
                if progression.try_invest_skill(game.player, key):
                    bought += 1
            else:
                if progression.try_invest_class(game.player, key):
                    bought += 1
        self.planned.clear()
        self._plan_seq = 0
        self.plan_mode = False
        if bought > 0:
            game.toast(f'Plan ausgeführt: {bought} Punkt(e) investiert.',
                        (140, 230, 180))
        else:
            game.toast('Keine Punkte verfügbar — Plan verworfen.',
                        (200, 140, 140))

    def update_hover(self, mx, my):
        """H-13 (Update #75): Pfad-Vorschau via Hover. Setzt _hover_node,
        damit draw() den Knoten unter dem Mauszeiger hervorhebt und ein
        Tooltip-Overlay mit Vorschau der nächsten Stufe rendert."""
        self._hover_node = None
        for k, r in self._node_rects.items():
            if r.collidepoint(mx, my):
                self._hover_node = ('skill', k)
                return
        for k, r in self._cnode_rects.items():
            if r.collidepoint(mx, my):
                self._hover_node = ('class', k)
                return

    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        # H-14 (Update #76): Confirm-Plan-Button hat Vorrang in Plan-Mode
        if (self.plan_mode and self._confirm_rect is not None
                and self._confirm_rect.collidepoint(mx, my)):
            self.commit_plan(game)
            return True
        for node_id, rect in self._node_rects.items():
            if rect.collidepoint(mx, my):
                if self.plan_mode:
                    self._toggle_plan_node('skill', node_id, game)
                else:
                    if progression.try_invest_skill(game.player, node_id):
                        self._push_alloc_anim(rect, (243, 213, 114), game)
                return True
        for node_id, rect in self._cnode_rects.items():
            if rect.collidepoint(mx, my):
                if self.plan_mode:
                    self._toggle_plan_node('class', node_id, game)
                else:
                    if progression.try_invest_class(game.player, node_id):
                        self._push_alloc_anim(rect, (220, 150, 70), game)
                return True
        for aura_key, rect in self._aura_rects.items():
            if rect.collidepoint(mx, my):
                progression.set_aura(game.player, aura_key)
                return True
        return True

    def _push_alloc_anim(self, rect, color, game):
        """H-12 (Update #77): Reiht Allocation-Animation ein und spielt
        Click + Allocation-SFX. Update #98 (H-03..H-10): Klassen-Theme-
        Sound wird zusätzlich gelayered (Hammerschlag/Flüster/Chime/etc.)."""
        self._anims.append({
            'rect': rect.copy(),
            'age': 0.0,
            'life': 1.0,
            'color': color,
            'pop': False,
        })
        try:
            from . import sounds as _snd
            from . import aspects as _asp
            _snd.play_with_fallback('ui_click', 'click', volume=0.6)
            _snd.play_with_fallback('level_up', 'click', volume=0.35)
            # H-03..H-10: Klassen-spezifischer Signature-Sound auf Allocation
            theme = _asp.class_theme(game.player.cls)
            sig_sound = theme.get('click_sound', 'click')
            _snd.play_with_fallback(sig_sound, 'click', volume=0.45)
        except Exception:
            pass

    def handle_rightclick(self, game, mx, my):
        """H-17 (Update #75): Rechtsklick auf einen allocierten Knoten
        refunded einen Punkt, sofern eine Orb-of-Regret im Bestand ist.
        Lore: Spiegelhof-Reflexion löscht die Lektion.
        """
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        for node_id, rect in self._node_rects.items():
            if rect.collidepoint(mx, my):
                ok = progression.try_refund_skill(game.player, node_id)
                if ok:
                    game.toast(
                        f'Erinnerung „{TREE_NODES[node_id]["name"]}" gelöscht (-1 Orb-of-Regret)',
                        (220, 180, 240))
                elif game.player.orbs_of_regret <= 0:
                    game.toast('Keine Orb-of-Regret im Bestand.',
                                (200, 120, 120))
                return True
        from .constants import CLASS_TREE_NODES as _ctn
        for node_id, rect in self._cnode_rects.items():
            if rect.collidepoint(mx, my):
                ok = progression.try_refund_class(game.player, node_id)
                if ok:
                    cnodes = _ctn.get(game.player.cls, {})
                    nname = cnodes.get(node_id, {}).get('name', node_id)
                    game.toast(
                        f'Klassen-Erinnerung „{nname}" gelöscht (-1 Orb-of-Regret)',
                        (220, 180, 240))
                elif game.player.orbs_of_regret <= 0:
                    game.toast('Keine Orb-of-Regret im Bestand.',
                                (200, 120, 120))
                return True
        return True

    def draw(self, screen, game):
        from .constants import CLASS_TREE_NODES, AURAS
        from . import aspects as _asp
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        modal = self.modal_rect()
        pal = _asp.aspect_palette(game.player.cls)
        # Update #30: Velgrad-Tome-Style Skill-Tree-Page
        self._draw_tree_tome_frame(screen, modal, game, pal)

        # Header — Folio + Titel + Folio (Update #30 Fix, Layout-Cleanup)
        head_l = self.font_small.render(
            'LIBER MEMORIAE', True, (180, 140, 80))
        screen.blit(head_l, (modal.x + 36, modal.y + 14))
        head_r = self.font_small.render(
            'FOL. CCXLVII · recto', True, (180, 140, 80))
        screen.blit(head_r,
                     (modal.x + modal.w - head_r.get_width() - 36,
                      modal.y + 14))
        # Mittiger Titel
        title_text = 'D E R   E R I N N E R U N G S - B A U M'
        title = self.font_med.render(title_text, True, pal['halo'])
        title_sh = self.font_med.render(title_text, True, (10, 6, 4))
        title_x = modal.x + modal.w // 2 - title.get_width() // 2
        screen.blit(title_sh, (title_x + 1, modal.y + 33))
        screen.blit(title, (title_x, modal.y + 32))
        # Divider unter dem Titel — trennt Header-Chrome vom Statusband
        _asp.draw_ornament_divider(
            screen, modal.x + 36, modal.y + 58,
            modal.w - 72, (154, 118, 66))

        sp = game.player.skill_points
        cp = game.player.class_points
        oor = getattr(game.player, 'orbs_of_regret', 0)
        # Status-Band (nur Ressourcen + Filter — Keybinds liegen im Footer).
        # Update #76 H-14/H-15: Filter + Plan-Mode-Anzeige.
        filt_lbl = self.FILTER_LABELS.get(self.filter_tag, '?')
        plan_str = f'   ·   PLAN ({len(self.planned)})' if self.plan_mode else ''
        sp_text = self.font_small.render(
            f'Universal: {sp}   ·   Klasse: {cp}   ·   Orbs: {oor}   ·   '
            f'Filter [F]: {filt_lbl}{plan_str}',
            True, pal['halo'] if sp + cp > 0 else TEXT_DIM)
        screen.blit(sp_text, (modal.x + modal.w // 2 - sp_text.get_width() // 2,
                              modal.y + 68))

        # H-13 (Update #75): Hover-Tracking aktualisieren BEVOR Nodes
        # gezeichnet werden — Rects aus letztem Frame sind noch valide
        # (Layout statisch).
        try:
            _mx, _my = pygame.mouse.get_pos()
            self.update_hover(_mx, _my)
        except Exception:
            pass

        # ----- Universaler Tree (oben links) -----
        sec_lbl = self.font_small.render('UNIVERSAL', True, GOLD_BRIGHT)
        screen.blit(sec_lbl, (modal.x + 24, modal.y + 92))

        node_keys = list(TREE_NODES.keys())
        cols = 4
        node_w = 200
        node_h = 100
        gx = modal.x + 24
        gy = modal.y + 112
        self._node_rects = {}
        for i, key in enumerate(node_keys):
            col = i % cols
            row = i // cols
            x = gx + col * (node_w + 10)
            y = gy + row * (node_h + 10)
            rect = pygame.Rect(x, y, node_w, node_h)
            self._node_rects[key] = rect
            node = TREE_NODES[key]
            lvl = game.player.tree.get(key, 0)
            maxed = lvl >= node['max']
            self._draw_node(screen, rect, node['name'], lvl, node['max'],
                            node['desc'], sp > 0 and not maxed)

        # ----- Klassen-Tree (unter Universal) -----
        from .constants import CLASSES
        class_name = CLASSES[game.player.cls]['name']
        # gy = modal.y + 112, node_h = 100 (+10 gap) → 3 Reihen = 330
        rows_univ = (len(node_keys) + cols - 1) // cols
        cgy = gy + rows_univ * (node_h + 10) + 36
        sec_lbl = self.font_small.render(
            f'KLASSE: {class_name.upper()}', True, GOLD_BRIGHT)
        screen.blit(sec_lbl, (modal.x + 24, cgy - 22))

        cnodes = CLASS_TREE_NODES.get(game.player.cls, {})
        cnode_keys = list(cnodes.keys())
        self._cnode_rects = {}
        if not cnode_keys:
            # Empty-State: noch keine Klassen-Erinnerungen für diese Klasse
            # definiert.  Hinweis-Karte über die volle Tree-Breite statt
            # leerer Platzhalter-Fläche.
            empty_w = cols * node_w + (cols - 1) * 10
            empty_rect = pygame.Rect(gx, cgy, empty_w, node_h)
            self._draw_empty_card(
                screen, empty_rect,
                title=f'Erinnerungen für {class_name} folgen',
                body=('Diese Klasse erhält in einem späteren Akt ihren '
                      'eigenen Erinnerungszweig.'))
        for i, key in enumerate(cnode_keys):
            col = i % cols
            row = i // cols
            x = gx + col * (node_w + 10)
            y = cgy + row * (node_h + 10)
            rect = pygame.Rect(x, y, node_w, node_h)
            self._cnode_rects[key] = rect
            node = cnodes[key]
            lvl = game.player.class_tree.get(key, 0)
            maxed = lvl >= node['max']
            # Update #106 (Audit F-020): Klassen-Theme-Keystone-Color für
            # Class-Tree-Nodes statt static bronze.  Visuelle Klassen-
            # Identifikation pro Tree.
            theme = _asp.class_theme(game.player.cls)
            cnode_border = theme.get('node_accent') or (180, 120, 60)
            self._draw_node(screen, rect, node['name'], lvl, node['max'],
                            node['desc'], cp > 0 and not maxed,
                            border_color=cnode_border)

        # ----- Auren (rechte Spalte) -----
        ax = modal.x + 24 + cols * (node_w + 10) + 16
        ay = modal.y + 112
        aw = modal.w - (ax - modal.x) - 24
        sec_lbl = self.font_small.render('AUREN (Mana-Reservation)',
                                          True, GOLD_BRIGHT)
        screen.blit(sec_lbl, (ax, modal.y + 92))
        self._aura_rects = {}
        rendered_auras = 0
        for aura_key, spec in AURAS.items():
            if game.player.cls not in spec['class_']:
                continue
            rect = pygame.Rect(ax, ay, aw, 70)
            active = (game.player.aura == aura_key)
            self._aura_rects[aura_key] = rect
            bg_col = (60, 50, 18, 220) if active else (26, 22, 18, 220)
            sf = pygame.Surface((aw, 70), pygame.SRCALPHA)
            sf.fill(bg_col)
            screen.blit(sf, (ax, ay))
            pygame.draw.rect(screen, GOLD_BRIGHT if active else (60, 50, 40),
                             rect, 2)
            name = self.font_small.render(
                f'{spec["name"]} ({int(spec["reserve"]*100)}% Mana)',
                True, GOLD_BRIGHT if active else TEXT)
            screen.blit(name, (ax + 10, ay + 6))
            desc = self.font_small.render(spec['desc'], True, TEXT_DIM)
            screen.blit(desc, (ax + 10, ay + 26))
            status = self.font_small.render(
                'AKTIV — klicken um zu deaktivieren' if active else 'klicken zum aktivieren',
                True, (180, 220, 100) if active else TEXT_DIM)
            screen.blit(status, (ax + 10, ay + 46))
            ay += 80
            rendered_auras += 1
        if rendered_auras == 0:
            # Empty-State: keine Auren für diese Klasse (z. B. Mönch /
            # Huntress / Druid).  Anstelle eines leeren Spaltenkopfs eine
            # dezente Hinweis-Karte.
            empty_rect = pygame.Rect(ax, ay, aw, 70)
            self._draw_empty_card(
                screen, empty_rect,
                title='Keine Auren verfügbar',
                body=('Diese Klasse kanalisiert ihre Kraft direkt — '
                      'kein Mana-Reservation-Slot.'))
            ay += 80

        # Skill-Level-Anzeige unter Auren
        ay += 6
        sec_lbl = self.font_small.render('SKILL-STUFEN', True, GOLD_BRIGHT)
        screen.blit(sec_lbl, (ax, ay))
        ay += 18
        from .constants import SKILL_LEVEL_MAX
        for skill_key in ('melee', 'fireball', 'lightning', 'heal', 'frostnova'):
            lvl = game.player.skill_levels.get(skill_key, 1)
            cur_xp, need = progression.skill_xp_progress(game.player, skill_key)
            label = {'melee': 'Nahkampf', 'fireball': 'Feuerball',
                     'lightning': 'Blitz', 'heal': 'Heilung',
                     'frostnova': 'Frostnova'}.get(skill_key, skill_key)
            txt = self.font_small.render(
                f'{label}: Lv {lvl}/{SKILL_LEVEL_MAX}', True, TEXT)
            screen.blit(txt, (ax, ay))
            # Mini progress bar
            bx0 = ax + 140
            pygame.draw.rect(screen, (15, 10, 8), (bx0, ay + 4, 80, 6))
            if need > 0:
                pygame.draw.rect(screen, GOLD,
                                 (bx0, ay + 4, int(80 * cur_xp / need), 6))
            ay += 16

        # H-15 (Update #76): Filter-Dim-Overlay über nicht-matchende Knoten.
        # H-14 (Update #76): Plan-Marker (cyan-dashed Rahmen + Sequenz-Nr.)
        self._draw_filter_dim(screen, game)
        self._draw_plan_markers(screen, game, modal)

        # H-12 (Update #77): Allocation-Animationen vorrendern.
        self._tick_and_draw_anims(screen)

        # H-13 (Update #75): Hover-Preview-Overlay — fokussierter Knoten
        # bekommt türkisen Resonanz-Ring + Tooltip-Card mit der Vorschau
        # auf die nächste Stufe (oder Refund-Hinweis bei allocierten).
        self._draw_hover_preview(screen, game, modal, pal)

    def _tick_and_draw_anims(self, screen):
        """H-12 (Update #77): Anim-Sequenz pro Knoten —
        0.0–0.4 s: Partikel-Burst aus Zentrum (Particle-Burst).
        0.0–0.6 s: Expandierender Ring (Aspekt-Color).
        0.6–1.0 s: Halo-Pulse abklingend.
        Wird im UI-Overlay-Layer gerendert (überlebt Modal).
        """
        if not self._anims:
            self._last_anim_tick_ms = pygame.time.get_ticks()
            return
        now = pygame.time.get_ticks()
        dt = max(0.0, (now - self._last_anim_tick_ms) / 1000.0)
        self._last_anim_tick_ms = now
        keep = []
        for a in self._anims:
            a['age'] += dt
            if a['age'] >= a['life']:
                continue
            keep.append(a)
            t = a['age'] / a['life']
            cx = a['rect'].centerx
            cy = a['rect'].centery
            col = a['color']
            # Particle-Burst: 8 radial Lines (0.0–0.4 s)
            if t < 0.4:
                bt = t / 0.4
                alpha = int(255 * (1.0 - bt))
                r_out = 8 + int(50 * bt)
                surf = pygame.Surface((140, 140), pygame.SRCALPHA)
                for k in range(8):
                    ang = (math.pi * 2 / 8) * k + bt * 0.6
                    dx = math.cos(ang) * r_out
                    dy = math.sin(ang) * r_out
                    pygame.draw.line(
                        surf, (*col, alpha),
                        (70, 70), (70 + dx, 70 + dy), 3)
                screen.blit(surf, (cx - 70, cy - 70))
            # Expandierender Ring (0.0–0.6 s)
            if t < 0.6:
                rt = t / 0.6
                r_ring = int(a['rect'].w * 0.5 + 36 * rt)
                ring_a = int(220 * (1.0 - rt))
                ring = pygame.Surface(
                    (r_ring * 2 + 4, r_ring * 2 + 4), pygame.SRCALPHA)
                pygame.draw.circle(ring, (*col, ring_a),
                                    (r_ring + 2, r_ring + 2),
                                    r_ring, 3)
                screen.blit(ring, (cx - r_ring - 2, cy - r_ring - 2))
            # Halo-Pulse (0.4–1.0 s)
            if t >= 0.4:
                ht = (t - 0.4) / 0.6
                halo_a = int(150 * (1.0 - ht))
                pulse = 1.0 + 0.25 * math.sin(ht * math.pi * 4)
                halo_w = int(a['rect'].w * pulse) + 12
                halo_h = int(a['rect'].h * pulse) + 12
                halo = pygame.Surface(
                    (halo_w + 8, halo_h + 8), pygame.SRCALPHA)
                pygame.draw.rect(halo, (*col, halo_a),
                                  (0, 0, halo_w + 8, halo_h + 8),
                                  4, border_radius=6)
                screen.blit(halo, (cx - halo_w // 2 - 4,
                                    cy - halo_h // 2 - 4))
        self._anims = keep

    def _draw_filter_dim(self, screen, game):
        """H-15: Dim alle Knoten, die nicht zum aktuellen Filter passen.
        'all' = kein Dim."""
        if self.filter_tag == 'all':
            return
        from .constants import CLASS_TREE_NODES as _ctn
        # Universal
        for key, rect in self._node_rects.items():
            node = TREE_NODES.get(key, {})
            if not self._matches_filter('skill', key, node):
                dim = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 150))
                screen.blit(dim, rect.topleft)
        # Klasse
        cnodes = _ctn.get(game.player.cls, {})
        for key, rect in self._cnode_rects.items():
            node = cnodes.get(key, {})
            if not self._matches_filter('class', key, node):
                dim = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
                dim.fill((0, 0, 0, 150))
                screen.blit(dim, rect.topleft)

    def _draw_plan_markers(self, screen, game, modal):
        """H-14: Markiert geplante Knoten mit cyan-dashed Rahmen +
        Sequenz-Nummer, rendert Confirm-Button am Modal-Unterrand."""
        self._confirm_rect = None
        if not self.plan_mode:
            return
        # Pulse-Cyan-Border + Plan-Number
        pulse = 0.5 + 0.5 * math.sin(pygame.time.get_ticks() * 0.008)
        cyan = (int(80 + 80 * pulse), 220, 220)
        for (kind, key), order in self.planned.items():
            rect = (self._node_rects if kind == 'skill'
                    else self._cnode_rects).get(key)
            if rect is None:
                continue
            # Dashed-Rahmen via Segmente
            pygame.draw.rect(screen, cyan, rect, 3, border_radius=2)
            # Sequenz-Bubble oben rechts
            bub = pygame.Surface((24, 18), pygame.SRCALPHA)
            bub.fill((10, 30, 30, 240))
            pygame.draw.rect(bub, cyan, (0, 0, 24, 18), 1)
            num = self.font_small.render(str(order), True, cyan)
            bub.blit(num, (12 - num.get_width() // 2,
                            9 - num.get_height() // 2))
            screen.blit(bub, (rect.right - 26, rect.y + 2))
        # Confirm-Button am unteren Modal-Rand
        sp = game.player.skill_points
        cp = game.player.class_points
        skill_planned = sum(1 for (k, _) in self.planned if k == 'skill')
        class_planned = sum(1 for (k, _) in self.planned if k == 'class')
        affordable = (skill_planned <= sp and class_planned <= cp
                       and len(self.planned) > 0)
        btn_w, btn_h = 280, 36
        bx = modal.x + modal.w // 2 - btn_w // 2
        by = modal.bottom - btn_h - 14
        rect = pygame.Rect(bx, by, btn_w, btn_h)
        self._confirm_rect = rect
        bg_col = (40, 80, 70, 235) if affordable else (40, 30, 26, 235)
        bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg.fill(bg_col)
        screen.blit(bg, (bx, by))
        border = cyan if affordable else (120, 100, 80)
        pygame.draw.rect(screen, border, rect, 2)
        if affordable:
            label = f'PLAN KAUFEN ({len(self.planned)})  ·  Enter'
        elif len(self.planned) == 0:
            label = 'KEIN PLAN MARKIERT'
        else:
            label = f'PUNKTE FEHLEN  ({skill_planned}/{sp} · {class_planned}/{cp})'
        ls = self.font_small.render(label, True,
                                     (220, 240, 220) if affordable
                                     else (180, 160, 140))
        screen.blit(ls, (rect.centerx - ls.get_width() // 2,
                          rect.centery - ls.get_height() // 2))

    def _draw_hover_preview(self, screen, game, modal, pal):
        """H-13: Pfad-/Stufen-Vorschau für den Knoten unter dem Mauszeiger."""
        if self._hover_node is None:
            return
        kind, key = self._hover_node
        if kind == 'skill':
            rect = self._node_rects.get(key)
            node = TREE_NODES.get(key)
            cur = game.player.tree.get(key, 0)
            avail = game.player.skill_points
        else:
            from .constants import CLASS_TREE_NODES as _ctn
            rect = self._cnode_rects.get(key)
            cnodes = _ctn.get(game.player.cls, {})
            node = cnodes.get(key)
            cur = game.player.class_tree.get(key, 0)
            avail = game.player.class_points
        if rect is None or node is None:
            return
        max_lvl = node['max']
        ring = pygame.Surface((rect.w + 16, rect.h + 16), pygame.SRCALPHA)
        pulse = 0.55 + 0.45 * math.sin(pygame.time.get_ticks() * 0.006)
        pygame.draw.rect(ring, (120, 230, 220, int(180 * pulse)),
                          (0, 0, rect.w + 16, rect.h + 16), 3,
                          border_radius=4)
        screen.blit(ring, (rect.x - 8, rect.y - 8))

        tip_w = 280
        tip_h = 96
        tip_x = min(rect.right + 12, modal.right - tip_w - 8)
        tip_y = min(rect.y, modal.bottom - tip_h - 8)
        tip = pygame.Surface((tip_w, tip_h), pygame.SRCALPHA)
        tip.fill((22, 18, 12, 240))
        pygame.draw.rect(tip, (180, 140, 80), (0, 0, tip_w, tip_h), 2)
        screen.blit(tip, (tip_x, tip_y))
        ty = tip_y + 6
        hdr = self.font_small.render(
            f'{node["name"]}  ({cur}/{max_lvl})', True, GOLD_BRIGHT)
        screen.blit(hdr, (tip_x + 8, ty))
        ty += 18
        if cur < max_lvl:
            nxt_col = (180, 230, 180) if avail > 0 else (200, 140, 140)
            nxt_msg = (f'+1 Stufe → {cur + 1}/{max_lvl}'
                        if avail > 0 else
                        f'Punkt fehlt (haben: {avail})')
            screen.blit(self.font_small.render(nxt_msg, True, nxt_col),
                         (tip_x + 8, ty))
            ty += 16
        else:
            screen.blit(self.font_small.render(
                'Meisterhaft (Masterworked)', True, (220, 230, 240)),
                (tip_x + 8, ty))
            ty += 16
        if cur > 0:
            oor = getattr(game.player, 'orbs_of_regret', 0)
            rc = (220, 180, 240) if oor > 0 else (160, 120, 140)
            rmsg = (f'RMB: Refund (Orbs: {oor})' if oor > 0
                     else 'RMB: Refund (keine Orb-of-Regret)')
            screen.blit(self.font_small.render(rmsg, True, rc),
                         (tip_x + 8, ty))
            ty += 16
        # Effekt-Vorschau
        desc = node.get('desc', '')
        if desc:
            d = self.font_small.render(desc[:46], True, (200, 200, 180))
            screen.blit(d, (tip_x + 8, ty))

    def _draw_tree_tome_frame(self, screen, modal, game, pal):
        """Pergament-Background + Doppelrahmen + Filigree-Ecken für
        Skill-Tree-Modal. Update #30. Update #98: Klassen-Theme-Tint
        wird der Standard-Pergament-Page überlagert (H-03..H-10)."""
        from . import aspects as _asp
        theme = _asp.class_theme(game.player.cls)
        bg_tint = theme.get('bg_tint', (42, 31, 20))
        # Page-Gradient — interpoliert Standard-Pergament mit Klassen-Tint
        page = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        for y in range(modal.h):
            t = y / max(1, modal.h - 1)
            r = int(42 + (28 - 42) * t)
            g = int(31 + (22 - 31) * t)
            b = int(20 + (16 - 20) * t)
            # Klassen-BG-Tint dezent (15 %) für Klassen-Wiedererkennung
            r = int(r * 0.85 + bg_tint[0] * 0.15)
            g = int(g * 0.85 + bg_tint[1] * 0.15)
            b = int(b * 0.85 + bg_tint[2] * 0.15)
            pygame.draw.line(page, (r, g, b, 248), (0, y), (modal.w, y))
        # Mottling
        for cx, cy, rr in [
            (int(modal.w * 0.18), int(modal.h * 0.10), 110),
            (int(modal.w * 0.82), int(modal.h * 0.88), 100),
            (int(modal.w * 0.10), int(modal.h * 0.78), 75),
            (int(modal.w * 0.74), int(modal.h * 0.22), 120),
        ]:
            spot = pygame.Surface((rr * 2, rr * 2), pygame.SRCALPHA)
            pygame.draw.circle(spot, (74, 55, 30, 60), (rr, rr), rr)
            page.blit(spot, (cx - rr, cy - rr))
        # Edge-Vignette
        vig = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        for k in range(40):
            a = int(k * 3.0)
            pygame.draw.rect(vig, (0, 0, 0, a),
                              (k, k, modal.w - 2 * k, modal.h - 2 * k), 1)
        page.blit(vig, (0, 0))
        screen.blit(page, modal.topleft)
        # Doppelrahmen
        pygame.draw.rect(screen, (60, 40, 22),
                          (modal.x, modal.y, modal.w, modal.h), 2)
        pygame.draw.rect(screen, pal['deep'],
                          (modal.x + 4, modal.y + 4,
                           modal.w - 8, modal.h - 8), 1)
        # Filigree-Eck-Ornamente
        _asp.draw_filigree_corners(screen, modal, (154, 118, 66), size=36)
        # Aspekt-Watermark in der Mitte (subtile Pergament-Schicht)
        _asp.draw_aspect_watermark(screen, modal, game.player.cls, alpha=18)
        # Footer — Keybind-Hinweis (links) + Quote (zentriert) + Divider.
        # Keybinds wurden aus dem überfrachteten Header-Statusband in den
        # Footer verschoben, damit das obere Band nicht in die AUREN-Spalte
        # bleedet.
        keybinds = 'RMB: Refund   ·   P: Plan   ·   F: Filter   ·   K: Schließen'
        kb_surf = self.font_small.render(keybinds, True, (150, 120, 80))
        screen.blit(kb_surf, (modal.x + 36, modal.y + modal.h - 52))
        quote = '„Was du erinnerst, wirst du sein. Was du vergisst, fällt aus dir heraus."'
        qsurf = self.font_small.render(quote, True, (200, 160, 100))
        screen.blit(qsurf, (modal.x + modal.w // 2 - qsurf.get_width() // 2,
                             modal.y + modal.h - 30))
        _asp.draw_ornament_divider(
            screen, modal.x + modal.w // 2 - 90,
            modal.y + modal.h - 14, 180, (90, 63, 36))

    def _draw_node(self, screen, rect, name, lvl, max_lvl, desc, can_invest,
                   border_color=None):
        """Skill-Tree-Node im Velgrad-Hex-Stil (Update #30).

        Allocated (lvl>0)  → Aspekt-Bright-Glow + voller Fill
        Available (lvl=0, can_invest) → halb-transparent + bronze-Border
        Locked    (lvl=0, !can_invest) → dunkel
        """
        maxed = lvl >= max_lvl
        # Hintergrund: Gradient
        slot_bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        if lvl > 0:
            # Allocated: subtle aspekt-tint
            base_top = (60, 50, 28)
            base_bot = (32, 26, 16)
        elif can_invest:
            base_top = (42, 32, 20)
            base_bot = (22, 16, 10)
        else:
            base_top = (24, 18, 14)
            base_bot = (14, 10, 6)
        for hy in range(rect.h):
            t = hy / max(1, rect.h - 1)
            rr = int(base_top[0] + (base_bot[0] - base_top[0]) * t)
            gg = int(base_top[1] + (base_bot[1] - base_top[1]) * t)
            bb = int(base_top[2] + (base_bot[2] - base_top[2]) * t)
            pygame.draw.line(slot_bg, (rr, gg, bb, 240),
                              (0, hy), (rect.w, hy))
        screen.blit(slot_bg, rect.topleft)

        # H-11 (Update #74): Node-States Locked/Available/Allocated/Masterworked
        if border_color is None:
            if maxed:
                # Masterworked = silbern-platinum (Lore: Mahnmal-Vollendung)
                border_color = (220, 230, 240)
            elif lvl > 0:
                border_color = (227, 180, 64)  # gold-bright (allocated)
            elif can_invest:
                border_color = (154, 118, 66)  # bronze (available)
            else:
                border_color = (60, 50, 40)    # locked (dunkel)
        # Glow: Masterworked pulst stärker, Allocated normal
        if lvl > 0:
            glow = pygame.Surface((rect.w + 12, rect.h + 12),
                                    pygame.SRCALPHA)
            pulse = 0.6 + 0.4 * math.sin(
                pygame.time.get_ticks() * 0.003 + rect.x * 0.01)
            # Masterworked: 1.5× Glow-Stärke + breiter Ring
            glow_a = int((120 if maxed else 80) * pulse)
            glow_w = 6 if maxed else 4
            pygame.draw.rect(glow, (*border_color, glow_a),
                              (0, 0, rect.w + 12, rect.h + 12), glow_w)
            screen.blit(glow, (rect.x - 6, rect.y - 6))
        pygame.draw.rect(screen, border_color, rect, 2)
        # Top-Highlight
        pygame.draw.line(screen,
                          tuple(min(255, c + 30)
                                 for c in border_color[:3]),
                          (rect.x, rect.y), (rect.right, rect.y), 1)

        # H-18 (Update #168): Hex-Polygon-Akzent rechts unten am Node-Rect.
        # Subtle 6-eckiges Symbol als Mahnmal-Lore-Akzent.  Bei
        # Masterworked ein 2. Inner-Hex (Diamant-Marker).
        hex_cx = rect.right - 14
        hex_cy = rect.bottom - 14
        hex_r = 8 if not maxed else 9
        hex_pts = []
        for i in range(6):
            a = math.pi / 3 * i - math.pi / 6
            hex_pts.append((hex_cx + math.cos(a) * hex_r,
                             hex_cy + math.sin(a) * hex_r))
        try:
            pygame.draw.polygon(screen, border_color, hex_pts, 1)
            if maxed:
                inner_pts = [(hex_cx + (px - hex_cx) * 0.55,
                              hex_cy + (py - hex_cy) * 0.55)
                             for (px, py) in hex_pts]
                pygame.draw.polygon(screen, (255, 255, 255), inner_pts)
        except (ValueError, TypeError):
            pass

        # Allocated: dot links oben als Lvl-Indikator
        if lvl > 0:
            for k in range(min(lvl, 6)):
                pygame.draw.circle(screen, (255, 220, 130),
                                    (rect.x + 8 + k * 8, rect.y + 12), 2)

        # Name
        name_col = (243, 213, 114) if lvl > 0 else (
            (220, 200, 170) if can_invest else (140, 130, 100))
        name_s = self.font_small.render(name, True, name_col)
        screen.blit(name_s, (rect.x + 10, rect.y + 22))

        # Lvl-Text rechts oben
        lvl_col = ((140, 220, 140) if maxed
                    else ((255, 220, 100) if lvl > 0 else (120, 110, 80)))
        lvl_text = self.font_small.render(
            f'{lvl}/{max_lvl}', True, lvl_col)
        screen.blit(lvl_text,
                     (rect.right - lvl_text.get_width() - 10, rect.y + 8))

        # Desc — voller Vertikalraum bis kurz vor unteren Rand (kein
        # '+ Investieren' Button-Text mehr; Bronze-Border signalisiert
        # Investierbarkeit, kleines '+' Glyph rechts unten als Affordance).
        desc_col = (210, 200, 180) if lvl > 0 or can_invest else (120, 110, 90)
        self._wrap(screen, desc, rect.x + 10, rect.y + 42,
                    rect.w - 28, desc_col)

        if can_invest:
            plus = self.font_small.render('+', True, (227, 180, 64))
            screen.blit(plus, (rect.right - plus.get_width() - 24,
                                rect.bottom - plus.get_height() - 4))

    def _wrap(self, screen, text, x, y, max_w, color):
        font = self.font_small
        words = text.split(' ')
        line = ''
        cy = y
        for word in words:
            test = line + (' ' if line else '') + word
            if font.size(test)[0] > max_w:
                if line:
                    screen.blit(font.render(line, True, color), (x, cy))
                    cy += font.get_height() + 2
                line = word
            else:
                line = test
        if line:
            screen.blit(font.render(line, True, color), (x, cy))

    def _draw_empty_card(self, screen, rect, title, body):
        """Hinweis-Karte für leere Tree-/Auren-Bereiche.  Dezent
        gestrichelter Bronze-Rand + zentrierter Titel + gewrappte
        Body-Zeile.  Verhindert dass leere Klassen (z. B. Mönch ohne
        Klassen-Erinnerungen oder Auren) als unfertiger Platzhalter
        wirken.
        """
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((22, 18, 14, 200))
        screen.blit(bg, rect.topleft)
        col = (110, 86, 50)
        dash, gap = 6, 4
        x0, y0, x1, y1 = rect.left, rect.top, rect.right - 1, rect.bottom - 1
        cx = x0
        while cx < x1:
            pygame.draw.line(screen, col, (cx, y0), (min(cx + dash, x1), y0), 1)
            pygame.draw.line(screen, col, (cx, y1), (min(cx + dash, x1), y1), 1)
            cx += dash + gap
        cy = y0
        while cy < y1:
            pygame.draw.line(screen, col, (x0, cy), (x0, min(cy + dash, y1)), 1)
            pygame.draw.line(screen, col, (x1, cy), (x1, min(cy + dash, y1)), 1)
            cy += dash + gap
        t_surf = self.font_small.render(title, True, (180, 150, 100))
        screen.blit(t_surf,
                     (rect.centerx - t_surf.get_width() // 2, rect.y + 12))
        body_y = rect.y + 12 + t_surf.get_height() + 8
        self._wrap(screen, body, rect.x + 14, body_y,
                    rect.w - 28, (140, 125, 100))


# ============================================================
# RUNE-CHOICE-UI
# ============================================================
class RuneChoiceUI:
    def __init__(self, font_med, font_small):
        self.font_med = font_med
        self.font_small = font_small
        self._card_rects = []

    def _layout(self, choices):
        card_w, card_h = 240, 280
        n = len(choices)
        total_w = n * card_w + (n - 1) * 20
        start_x = SCREEN_W // 2 - total_w // 2
        cy = SCREEN_H // 2 - card_h // 2
        rects = []
        for i in range(n):
            rects.append(pygame.Rect(start_x + i * (card_w + 20), cy,
                                     card_w, card_h))
        return rects

    def handle_click(self, choices, mx, my):
        rects = self._layout(choices)
        for i, r in enumerate(rects):
            if r.collidepoint(mx, my):
                return choices[i]
        return None

    def draw(self, screen, choices):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        title = self.font_big_safe(screen, 'BOSS BESIEGT — WÄHLE EINE RUNE',
                                   GOLD_BRIGHT, SCREEN_H // 2 - 220)

        rects = self._layout(choices)
        for i, rect in enumerate(rects):
            choice = choices[i]
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((18, 14, 10, 245))
            screen.blit(bg, rect.topleft)
            pygame.draw.rect(screen, GOLD, rect, 2)

            # Skill-Symbol oben
            from .skills import SKILL_INFO
            skill = SKILL_INFO.get(choice['skill'], {})
            skill_name = skill.get('name', choice['skill'])
            skill_lbl = self.font_small.render(
                f'Modifiziert: {skill_name}', True, TEXT_DIM)
            screen.blit(skill_lbl,
                        (rect.centerx - skill_lbl.get_width() // 2, rect.y + 20))

            # Skill-Icon
            icon_y = rect.y + 80
            icon_idx = {'fireball': 1, 'lightning': 2, 'heal': 3, 'frostnova': 4}.get(
                choice['skill'], 0)
            draw_skill_icon(screen, rect.centerx - 28, icon_y, 56, icon_idx, True)

            name = self.font_med.render(choice['name'], True, GOLD_BRIGHT)
            screen.blit(name, (rect.centerx - name.get_width() // 2,
                               rect.y + 150))

            # Beschreibung (umbrechen)
            self._wrap(screen, choice['desc'], rect.x + 16, rect.y + 190,
                       rect.w - 32, TEXT)

        hint = self.font_small.render('Klicke eine Rune zum Auswählen',
                                       True, GOLD)
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                           SCREEN_H // 2 + 170))

    def font_big_safe(self, screen, text, color, y):
        s = self.font_med.render(text, True, color)
        screen.blit(s, (SCREEN_W // 2 - s.get_width() // 2, y))

    def _wrap(self, screen, text, x, y, max_w, color):
        font = self.font_small
        words = text.split(' ')
        line = ''
        cy = y
        for word in words:
            test = line + (' ' if line else '') + word
            if font.size(test)[0] > max_w:
                if line:
                    screen.blit(font.render(line, True, color), (x, cy))
                    cy += font.get_height() + 2
                line = word
            else:
                line = test
        if line:
            screen.blit(font.render(line, True, color), (x, cy))


# ============================================================
# DEATH-SCREEN
# ============================================================
def draw_death(screen, game, font_big, font_med):
    """Wake-Up-Phase nach der Death-Transition (PLAN A-05/A-06/A-12).

    Update #30 — Velgrad-Death-Screen: „VERGANGEN"-Memorial-Tablet mit
    riesigem Aspekt-Glyph im Hintergrund, Pergament-Tint, Player-Namen
    durchgestrichen, Blutspur, Ornament-Rail.
    """
    from . import quotes as _q
    from . import aspects as _asp
    p = game.player
    cls = getattr(p, 'cls', None)
    last = getattr(game, 'last_damage_source', None) or {}
    dmg_type = last.get('type', 'physical')
    bucket = _q.normalize_damage_type(dmg_type)
    tint_col = _q.DEATH_TRANSITION_COLORS.get(bucket,
                                              _q.DEATH_TRANSITION_COLORS['generic'])
    pal = _asp.aspect_palette(cls or 'mage')
    t = pygame.time.get_ticks() * 0.001

    # 1) Radial-Memorial-Background (Blood→Black)
    base_bg = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    base_bg.fill((0, 0, 0, 240))
    # Radial Pulse (Atem-langsam)
    pulse = 0.5 + 0.5 * math.sin(t * 0.5)
    cx_s, cy_s = SCREEN_W // 2, SCREEN_H // 2
    for k in range(8):
        rad = 200 + k * 90
        a = int(40 * (1 - k / 8) * pulse)
        if a > 0:
            ring = pygame.Surface((rad * 2, rad * 2), pygame.SRCALPHA)
            pygame.draw.circle(ring, (140, 30, 30, a), (rad, rad), rad)
            base_bg.blit(ring, (cx_s - rad, cy_s - rad))
    screen.blit(base_bg, (0, 0))

    # 2) Riesiges Aspekt-Glyph im Hintergrund (sehr dunkel-blutrot)
    bg_glyph_size = 800
    bg_col = (90, 30, 24)
    _asp.draw_glyph(screen, cx_s, cy_s, bg_glyph_size,
                     _asp.aspect_for_class(cls or 'mage'), color=bg_col)

    # 3) Eyebrow „— die welt vergißt einen namen —"
    eyebrow = font_med.render(
        'D I E   W E L T   V E R G I S S T   E I N E N   N A M E N',
        True, (154, 118, 66))
    screen.blit(eyebrow,
                 eyebrow.get_rect(center=(SCREEN_W // 2,
                                           SCREEN_H // 2 - 220)))

    # 4) Ornament-Divider oben
    _asp.draw_ornament_divider(
        screen, SCREEN_W // 2 - 220, SCREEN_H // 2 - 200,
        440, (154, 118, 66))

    # 5) Title "VERGANGEN" mit Gold-Gradient-Stil + Blood-Glow
    title_text = 'VERGANGEN'
    # Glow-Hintergrund
    for k in range(6):
        glow_surf = font_big.render(title_text, True,
                                     (184, 30, 30))
        glow_surf.set_alpha(40 + k * 15)
        glow_rect = glow_surf.get_rect(
            center=(SCREEN_W // 2 + (k % 3 - 1) * 2,
                    SCREEN_H // 2 - 120 + (k // 3) * 2))
        screen.blit(glow_surf, glow_rect)
    # Schatten-Stack
    for ox, oy, col in [
        (-3, -3, (90, 30, 10)), (3, 3, (40, 16, 6)),
        (-3, 3, (50, 18, 8)),   (3, -3, (50, 18, 8)),
    ]:
        sh = font_big.render(title_text, True, col)
        sh_r = sh.get_rect(center=(SCREEN_W // 2 + ox,
                                     SCREEN_H // 2 - 120 + oy))
        screen.blit(sh, sh_r)
    title = font_big.render(title_text, True, (243, 213, 114))
    screen.blit(title, title.get_rect(
        center=(SCREEN_W // 2, SCREEN_H // 2 - 120)))

    # 6) Player-Name (durchgestrichen)
    cls_name = CLASSES.get(cls, {}).get('name', 'WANDERER')
    name_surf = font_med.render(
        f'  {cls_name.upper()}  ', True, (214, 195, 159))
    name_rect = name_surf.get_rect(
        center=(SCREEN_W // 2, SCREEN_H // 2 - 60))
    screen.blit(name_surf, name_rect)
    # Streich-Linie (Blood-Bright)
    pygame.draw.line(screen, (216, 56, 56),
                      (name_rect.x + 12, name_rect.centery),
                      (name_rect.right - 12, name_rect.centery), 2)

    # 7) Lore-Quote (gepuffert)
    quote_cache = getattr(game, '_current_death_quote', None)
    if quote_cache is None or quote_cache[0] != game.death_count:
        q = _q.pick_death_quote(cls, dmg_type,
                                first_death=(game.death_count == 1))
        game._current_death_quote = (game.death_count, q)
    quote_text = game._current_death_quote[1]
    if quote_text:
        # Wrap auf max-width 760
        words = quote_text.split(' ')
        lines = []
        cur = ''
        for w in words:
            test = (cur + ' ' + w).strip()
            if font_med.size(test)[0] > 760:
                if cur:
                    lines.append(cur)
                cur = w
            else:
                cur = test
        if cur:
            lines.append(cur)
        ly = SCREEN_H // 2 + 10
        for line in lines:
            ls = font_med.render(line, True, (200, 165, 110))
            screen.blit(ls, ls.get_rect(
                center=(SCREEN_W // 2, ly)))
            ly += font_med.get_height() + 4

    # 8) Ornament-Divider unten
    _asp.draw_ornament_divider(
        screen, SCREEN_W // 2 - 220, SCREEN_H // 2 + 130,
        440, (154, 118, 66))

    # 9) Summary (klein, gedeckt) — Memorial-Stats
    # Update #121: 'Welle' entfernt (kein Survival mehr); stattdessen
    # zeigen wir Akt-Progress (Anzahl der abgeschlossenen Dungeons).
    akt = len(getattr(p, 'completed_dungeons', ()))
    summary = (f'Stufe {p.level}   ·   {game.kills} Erschlagen'
               f'   ·   {p.gold} Gold   ·   Akt {max(1, akt)}')
    ss = font_med.render(summary, True, (140, 110, 70))
    screen.blit(ss, ss.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 170)))

    # 10) Skip-Hint (Update #132 Y-07: kürzer — Buttons sind jetzt unten)
    death_count = getattr(game, 'death_count', 1)
    if pygame.time.get_ticks() % 1600 < 1000 and death_count >= 2:
        r_surf = font_med.render(
            '  LEERTASTE überspringt Quote  ',
            True, pal['halo'])
        screen.blit(r_surf, r_surf.get_rect(
            center=(SCREEN_W // 2, SCREEN_H // 2 + 230)))

    # 11) Update #132 (Y-07): Drei Action-Buttons unten:
    #     [ENTER] Neuer Versuch  ·  [T] Charakter wechseln  ·  [Q] Beenden
    # Buttons sind Mouse-clickable; Game-Code mapt Klicks auf Actions.
    game._death_action_rects = {}
    btn_y = SCREEN_H - 90
    btn_w = 200
    btn_h = 44
    btn_gap = 24
    actions = [
        ('retry',   'Neuer Versuch',     '[ENTER]', (220, 200, 140)),
        ('charsel', 'Charakter wechseln', '[T]',     (180, 180, 220)),
        ('quit',    'Spiel beenden',     '[Q]',     (200, 150, 130)),
    ]
    total_w = btn_w * len(actions) + btn_gap * (len(actions) - 1)
    bx = (SCREEN_W - total_w) // 2
    for action_key, label, hot, col in actions:
        rect = pygame.Rect(bx, btn_y, btn_w, btn_h)
        game._death_action_rects[action_key] = rect
        # Hover-Detect via Mouse-Position (Game-Loop liest mouse pos)
        mx, my = pygame.mouse.get_pos()
        hover = rect.collidepoint(mx, my)
        bg_col = (40, 30, 14) if not hover else (60, 44, 20)
        pygame.draw.rect(screen, bg_col, rect)
        pygame.draw.rect(screen, col, rect, 2)
        lbl = font_med.render(label, True, col)
        screen.blit(lbl, lbl.get_rect(
            center=(bx + btn_w // 2, btn_y + 16)))
        hk = pygame.font.match_font('georgia') and font_big or font_med
        hot_surf = font_med.render(hot, True, (150, 130, 100))
        screen.blit(hot_surf, hot_surf.get_rect(
            center=(bx + btn_w // 2, btn_y + 33)))
        bx += btn_w + btn_gap


def draw_death_transition(screen, game):
    """Voll-Bildschirm-VFX während der Death-Animation-Phase (A-05/A-06).

    Wird gerendert während `state=='playing'` aber `player.dying=True`,
    überlagert die normale Szene. Damage-Type bestimmt das visuelle Muster
    (rot-Klatsch für Phys, Frost-Crawl für Cold, Weiß-Flash für Lightning).
    """
    from . import quotes as _q
    last = getattr(game, 'last_damage_source', None) or {}
    bucket = _q.normalize_damage_type(last.get('type'))
    col = _q.DEATH_TRANSITION_COLORS.get(bucket,
                                         _q.DEATH_TRANSITION_COLORS['generic'])
    # 0..1 über 0..2 s
    t = max(0.0, min(1.0, getattr(game, 'death_phase_t', 0.0) / 2.0))
    photosensitive = bool(game.settings.get('photosensitive', False))

    if bucket == 'lightning':
        # White-Flash max 2 Frames, dann TV-Static-Artefakte
        if not photosensitive and t < 0.05:
            flash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash.fill((255, 255, 255, 220))
            screen.blit(flash, (0, 0))
        else:
            tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            tint.fill((*col, int(140 * t)))
            screen.blit(tint, (0, 0))
        return

    if bucket == 'fire':
        # Flammenfront von rechts unten nach links oben — Diagonal-Wipe
        wipe_extent = int((SCREEN_W + SCREEN_H) * t)
        wipe = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        # Wir blittten ein Triangle-Wedge per Polygon.
        pts = [
            (SCREEN_W + 100, SCREEN_H + 100),
            (SCREEN_W + 100 - wipe_extent, SCREEN_H + 100),
            (SCREEN_W + 100, SCREEN_H + 100 - wipe_extent),
        ]
        pygame.draw.polygon(wipe, (*col, 180), pts)
        screen.blit(wipe, (0, 0))
        # Asche-Tint überall
        ash = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ash.fill((40, 20, 10, int(120 * t)))
        screen.blit(ash, (0, 0))
        return

    if bucket == 'cold':
        # Frost crawls von Bildschirmrändern nach innen — Border-Mask
        border = int(min(SCREEN_W, SCREEN_H) * 0.5 * t)
        frost = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        frost.fill((*col, int(160 * t)))
        # Zentral-Hole (= unfrozen)
        hole_r = max(20, int(min(SCREEN_W, SCREEN_H) * 0.4 * (1 - t)))
        pygame.draw.circle(frost, (0, 0, 0, 0),
                           (SCREEN_W // 2, SCREEN_H // 2), hole_r)
        screen.blit(frost, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
        return

    if bucket in ('physical', 'bleed'):
        # Vignette wird rot, radial nach innen
        vig = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        vig.fill((*col, int(110 * t)))
        # Heartbeat-Pulse
        pulse = abs(math.sin(game.death_phase_t * 6))
        rim_alpha = int(120 * t * pulse)
        pygame.draw.rect(vig, (*col, rim_alpha), (0, 0, SCREEN_W, 40))
        pygame.draw.rect(vig, (*col, rim_alpha),
                          (0, SCREEN_H - 40, SCREEN_W, 40))
        screen.blit(vig, (0, 0))
        return

    if bucket == 'chaos':
        # Wave-Distortion + grüner Tint
        tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        tint.fill((100, 160, 80, int(80 * t)))
        screen.blit(tint, (0, 0))
        purple = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        purple.fill((*col, int(60 * t)))
        screen.blit(purple, (0, 0))
        return

    if bucket == 'void':
        # Dissolve aus der Mitte — alles wird schwarz von innen
        r_void = int(min(SCREEN_W, SCREEN_H) * t * 0.7)
        void = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        pygame.draw.circle(void, (5, 0, 10, 250),
                           (SCREEN_W // 2, SCREEN_H // 2), r_void)
        screen.blit(void, (0, 0))
        return

    # generic / falling
    tint = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    tint.fill((*col, int(160 * t)))
    screen.blit(tint, (0, 0))


# ============================================================
# CURSOR & VIGNETTE
# ============================================================
def draw_cursor(screen, game=None):
    """Animierter Cursor: pulsierender Ring + Richtungs-Pfeil vom Spieler."""
    import math as _m
    mx, my = pygame.mouse.get_pos()
    pulse = abs(_m.sin(pygame.time.get_ticks() * 0.005))
    col = (255, int(180 + 50 * pulse), 60)
    # Pulsierender Außenring
    pygame.draw.circle(screen, col, (mx, my), int(12 + pulse * 2), 1)
    # Innerer fixer Ring
    pygame.draw.circle(screen, col, (mx, my), 7, 1)
    # Fadenkreuz
    pygame.draw.line(screen, col, (mx - 16, my), (mx - 8, my), 2)
    pygame.draw.line(screen, col, (mx + 8, my), (mx + 16, my), 2)
    pygame.draw.line(screen, col, (mx, my - 16), (mx, my - 8), 2)
    pygame.draw.line(screen, col, (mx, my + 8), (mx, my + 16), 2)
    # Zentraler Punkt
    pygame.draw.circle(screen, (255, 255, 200), (mx, my), 2)
    # Richtungs-Pfeil vom Spieler (wenn weit entfernt vom Cursor)
    if game is not None and game.state == 'playing':
        psx, psy = SCREEN_W // 2, SCREEN_H // 2
        dx, dy = mx - psx, my - psy
        dist = _m.hypot(dx, dy)
        if dist > 120:
            # Pfeil-Spitze auf halbem Weg zwischen Spieler und Cursor
            t = 0.5
            ax = psx + dx * t
            ay = psy + dy * t
            angle = _m.atan2(dy, dx)
            arrow_pts = [
                (ax + _m.cos(angle) * 14, ay + _m.sin(angle) * 14),
                (ax + _m.cos(angle + 2.5) * 8, ay + _m.sin(angle + 2.5) * 8),
                (ax + _m.cos(angle - 2.5) * 8, ay + _m.sin(angle - 2.5) * 8),
            ]
            pygame.draw.polygon(screen, (255, 200, 80), arrow_pts)
            pygame.draw.polygon(screen, (0, 0, 0), arrow_pts, 1)


def make_vignette():
    v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    cx, cy = SCREEN_W // 2, SCREEN_H // 2
    max_r = max(SCREEN_W, SCREEN_H)
    for i in range(30):
        t = i / 30
        r = int(max_r * (1 - t * 0.6))
        alpha = int(t * 5)
        pygame.draw.circle(v, (0, 0, 0, alpha), (cx, cy), r)
    return v
