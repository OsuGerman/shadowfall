"""Inventar-UI: Modal mit Inventar-Grid, Ausrüstung und Stat-Übersicht."""

import pygame

from .constants import (
    SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM,
    WHITE, BLOOD_LIGHT, MANA, FIRE,
    RARITY_COLOR, RARITY_NAME, SLOTS, SLOT_NAME,
    CLASSES,
)
from . import progression


SLOT_SIZE = 52
GRID_COLS, GRID_ROWS = 6, 4
GRID_GAP = 6

# Equipment-Slot-Layout (relative Pixel innerhalb des Modals)
EQUIP_POSITIONS = {
    # Update #41: 5 Slots in 2 Spalten am LINKEN Rand — Sprite RECHTS
    # daneben, klare Trennung von Stats-Panel unten.
    'helmet': (40, 90),      # Col1 Row1
    'amulet': (40, 150),     # Col1 Row2
    'weapon': (40, 210),     # Col1 Row3
    'chest':  (102, 90),     # Col2 Row1
    'ring':   (102, 150),    # Col2 Row2
    # K-09 (Update #69): Offhand-Slot (Col2 Row3, unter Ring)
    'offhand':(102, 210),    # Col2 Row3
}


class InventoryUI:
    def __init__(self, font_small, font_med, font_dmg):
        self.font_small = font_small
        self.font_med = font_med
        self.font_dmg = font_dmg
        self._rects = {}  # cache: name -> (rect, kind, payload)

    # ---------- Layout ----------
    def modal_rect(self):
        # Update #103: Modal-Höhe +50 px damit Footer-Quote + Hint INNERHALB
        # der Boxgrenze liegen (User-Screenshot zeigt Hint außerhalb).
        w, h = 820, 570
        x = SCREEN_W // 2 - w // 2
        y = SCREEN_H // 2 - h // 2
        return pygame.Rect(x, y, w, h)

    def inv_slot_rect(self, idx, modal):
        col = idx % GRID_COLS
        row = idx // GRID_COLS
        grid_x = modal.x + modal.w - (GRID_COLS * (SLOT_SIZE + GRID_GAP)) - 30
        grid_y = modal.y + 90
        x = grid_x + col * (SLOT_SIZE + GRID_GAP)
        y = grid_y + row * (SLOT_SIZE + GRID_GAP)
        return pygame.Rect(x, y, SLOT_SIZE, SLOT_SIZE)

    def equip_slot_rect(self, slot, modal):
        ox, oy = EQUIP_POSITIONS[slot]
        return pygame.Rect(modal.x + ox, modal.y + oy, SLOT_SIZE, SLOT_SIZE)

    def _attr_buttons(self, modal):
        """Returnt Liste [(rect, attr_key)] für die '+'-Knöpfe."""
        x = modal.x + 30
        y = modal.y + 270 + 28  # nach 'Stufe N Klasse'
        buttons = []
        for key in ('strength', 'intellect', 'dexterity'):
            buttons.append((pygame.Rect(x + 130, y - 2, 18, 18), key))
            y += 18
        return buttons

    # ---------- Input ----------
    def handle_click(self, game, mx, my):
        """Klick im Inventar verarbeiten. Returnt True wenn verarbeitet."""
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False

        # Attribut-Punkte vergeben — Update #103 Fix:
        # Render-Layout (Update #93 horizontal-Reihe) hat die echten Rects
        # bereits in `self._rects['attr']` gecached. Das veraltete
        # `_attr_buttons()` returnt eine VERTIKAL-gestapelte Position
        # (von vor Update #93), wodurch die Klicks daneben gingen.
        if game.player.attr_points > 0:
            for btn, key in self._rects.get('attr', ()):
                if btn.collidepoint(mx, my):
                    progression.try_invest_attr(game.player, key)
                    return True

        # Inventar-Slots
        for i in range(len(game.player.inventory)):
            if self.inv_slot_rect(i, modal).collidepoint(mx, my):
                progression.try_equip(game.player, i)
                return True
        # Equipment-Slots
        for slot in SLOTS:
            if self.equip_slot_rect(slot, modal).collidepoint(mx, my):
                progression.try_unequip(game.player, slot)
                return True
        return True  # innerhalb Modal → kein Welt-Klick

    # ---------- Rendering ----------
    def draw(self, screen, game):
        modal = self.modal_rect()
        # Hintergrund-Overlay
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        # --- THEMED: Velgrad-Tome-Page (Update #30) ---
        self._draw_tome_frame(screen, modal, game)

        # Header — kompakt, kein Overlap mehr (Update #30 Fix)
        from . import aspects as _asp
        pal = _asp.aspect_palette(game.player.cls)
        # ZEILE 1 (oben): linker Folio-Header / mittiger Titel / rechter Folio
        head_l = self.font_small.render(
            'LIBER RERUM', True, (180, 140, 80))
        screen.blit(head_l, (modal.x + 36, modal.y + 14))
        head_r = self.font_small.render(
            'FOL. CXII · recto', True, (180, 140, 80))
        screen.blit(head_r,
                     (modal.x + modal.w - head_r.get_width() - 36,
                      modal.y + 14))
        # ZEILE 2: Mittiger Titel (groß, mit Shadow)
        title_text = 'D I E   A U S R Ü S T U N G'
        title = self.font_med.render(title_text, True, pal['halo'])
        title_sh = self.font_med.render(title_text, True, (10, 6, 4))
        title_x = modal.x + modal.w // 2 - title.get_width() // 2
        screen.blit(title_sh, (title_x + 1, modal.y + 33))
        screen.blit(title, (title_x, modal.y + 32))
        # Ornament-Divider unter Titel
        _asp.draw_ornament_divider(
            screen, modal.x + 36, modal.y + 70,
            modal.w - 72, (154, 118, 66))

        # Update #41: AUSRÜSTUNG-Label entfernt (überlappte Slots).
        # Slots sind selbsterklärend durch Hel/Amu/Rüs/Waf/Rin-Marker.

        # Equipment-Slots ZUERST (damit Char-Sprite oben drauf liegt)
        for slot in SLOTS:
            r = self.equip_slot_rect(slot, modal)
            self._draw_slot(screen, r, game.player.equipment.get(slot), label=SLOT_NAME[slot][:3])

        # Update #39: Char-Vorschau AFTER Slots — sonst überdecken Slots
        # den Player-Sprite.
        self._draw_char_preview(screen, game, modal)

        # Stats-Panel
        self._draw_stats(screen, game, modal)

        # Inventar-Grid Label
        inv_label = self.font_small.render(
            '— I N V E N T A R —', True, (180, 140, 80))
        first_rect = self.inv_slot_rect(0, modal)
        screen.blit(inv_label, (first_rect.x, first_rect.y - 22))

        # Inventar-Slots
        for i, item in enumerate(game.player.inventory):
            r = self.inv_slot_rect(i, modal)
            self._draw_slot(screen, r, item)

        # Tooltip
        mx, my = pygame.mouse.get_pos()
        hovered = self._hovered_item(game, mx, my, modal)
        if hovered:
            # Update #84: Affix-Delta-Highlights bei gehaltenem Shift.
            # Berechnet pro-Affix-Vergleich und färbt die Tooltip-Zeilen
            # entsprechend (grün=besser, rot=schlechter, gold=neu).
            keys = pygame.key.get_pressed()
            shift_held = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]
            equipped = game.player.equipment.get(hovered.slot)
            delta_map = None
            power_delta = None
            if shift_held and equipped and equipped is not hovered:
                delta_map = self._affix_deltas(hovered, equipped)
                power_delta = (self._item_power(hovered)
                                - self._item_power(equipped))
            self._draw_tooltip(screen, hovered, mx, my,
                                delta_map=delta_map,
                                power_delta=power_delta)
            if shift_held and equipped and equipped is not hovered:
                # Daneben zeichnen (links versetzt)
                self._draw_tooltip(screen, equipped, mx - 240, my,
                                    header='Aktuell ausgerüstet:')

        # Footer mit Lore-Quote + Steuer-Hinweis (Velgrad-Manuskript-Style)
        # Update #103: Quote eine Zeile höher gerückt (modal.h-40 statt -30)
        # damit Hint-Zeile nicht in die Quote läuft und beide innerhalb der
        # Modal-Boundary liegen.
        from . import aspects as _asp
        quote = '„Was du trägst, erinnert sich, dass es einmal jemandem gehörte."'
        qsurf = self.font_small.render(quote, True, (200, 160, 100))
        screen.blit(qsurf, (modal.x + 36, modal.y + modal.h - 40))
        # Ornament-Divider zwischen Quote und Hint
        _asp.draw_ornament_divider(
            screen, modal.x + modal.w // 2 - 90,
            modal.y + modal.h - 24, 180, (90, 63, 36))
        # Hint rechts (etwas mehr Abstand zum Border)
        hint = self.font_small.render(
            'Klick: Anlegen  ·  Rechtsklick: Werfen  ·  Shift: Vergleich',
            True, TEXT_DIM)
        screen.blit(hint, (modal.x + modal.w - hint.get_width() - 36,
                            modal.y + modal.h - 18))

    def _draw_tome_frame(self, screen, modal, game):
        """Velgrad-Tome-Page: Pergament-Look mit Filigree-Eck-Ornamenten,
        zentralem Bronze-Spine + Aspekt-getöntem Akzent.

        Update #30 — Adaption aus velgrad-inventory.jsx PaperDollPage/BagPage.
        """
        from . import aspects as _asp
        pal = _asp.aspect_palette(game.player.cls)
        # Vellum-Gradient (mottled)
        page = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        for y in range(modal.h):
            t = y / max(1, modal.h - 1)
            r = int(42 + (28 - 42) * t)
            g = int(31 + (22 - 31) * t)
            b = int(20 + (16 - 20) * t)
            pygame.draw.line(page, (r, g, b, 250),
                              (0, y), (modal.w, y))
        # Mottling (radial dark patches)
        for cx, cy, rr in [
            (int(modal.w * 0.23), int(modal.h * 0.12), 100),
            (int(modal.w * 0.78), int(modal.h * 0.84), 90),
            (int(modal.w * 0.12), int(modal.h * 0.73), 70),
            (int(modal.w * 0.64), int(modal.h * 0.22), 110),
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
        # Fibre-Noise (subtile diagonal-Linien)
        for x in range(0, modal.w, 4):
            pygame.draw.line(page, (80, 60, 35, 25),
                              (x, 0), (x + modal.h // 2, modal.h), 1)
        screen.blit(page, modal.topleft)

        # Doppel-Rahmen
        pygame.draw.rect(screen, (60, 40, 22),
                          (modal.x, modal.y, modal.w, modal.h), 2)
        pygame.draw.rect(screen, pal['deep'],
                          (modal.x + 4, modal.y + 4,
                           modal.w - 8, modal.h - 8), 1)

        # Filigree-Eck-Ornamente (Aithein-Bronze)
        bronze = (154, 118, 66)
        _asp.draw_filigree_corners(screen, modal, bronze, size=36)
        # Aspekt-Watermark (sehr subtil, hinter dem Inhalt)
        _asp.draw_aspect_watermark(screen, modal, game.player.cls, alpha=18)

        # Zentrales Bronze-Spine (vertikal in der Mitte — trennt Equipment
        # links / Inventar rechts, wie ein aufgeschlagenes Buch).
        spine_x = modal.x + modal.w // 2
        spine_w = 14
        spine_top = modal.y + 80
        spine_bot = modal.y + modal.h - 40
        # Tief-Schatten in der Mitte
        shadow = pygame.Surface((spine_w, spine_bot - spine_top),
                                 pygame.SRCALPHA)
        for x in range(spine_w):
            t = abs(x - spine_w / 2) / (spine_w / 2)
            a = int(140 * (1 - t))
            pygame.draw.line(shadow, (0, 0, 0, a),
                              (x, 0), (x, spine_bot - spine_top))
        screen.blit(shadow, (spine_x - spine_w // 2, spine_top))
        # Mittel-Linie
        pygame.draw.line(screen, pal['deep'],
                          (spine_x, spine_top), (spine_x, spine_bot), 1)
        # Knoten-Punkte alle 80 px
        for ky in range(spine_top + 40, spine_bot, 80):
            pygame.draw.circle(screen, bronze, (spine_x, ky), 3)
            pygame.draw.circle(screen, (10, 6, 4), (spine_x, ky), 3, 1)
            pygame.draw.circle(screen, (235, 220, 175), (spine_x, ky), 1)

    def _draw_satchel_frame(self, screen, modal):
        """Themed Leder-Satchel als Modal-Hintergrund."""
        import math
        # Hauptkörper (leather brown)
        leather = (76, 50, 32)
        leather_dark = (50, 32, 20)
        leather_light = (100, 70, 45)
        brass = (180, 140, 70)
        brass_dark = (130, 100, 50)
        stitch = (200, 170, 120)

        # Bag-Hauptfläche (mit leichtem Verlauf)
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((*leather, 245))
        screen.blit(bg, modal.topleft)

        # Innerer dunklerer Bereich (Tasche-Innenraum)
        inner = pygame.Rect(modal.x + 14, modal.y + 14,
                            modal.w - 28, modal.h - 28)
        pygame.draw.rect(screen, leather_dark, inner)
        pygame.draw.rect(screen, leather_light, inner, 2)

        # Top-Flap (Klappe oben)
        flap_h = 36
        flap_pts = [
            (modal.x + 6, modal.y + 8),
            (modal.x + modal.w - 6, modal.y + 8),
            (modal.x + modal.w - 18, modal.y + flap_h),
            (modal.x + 18, modal.y + flap_h),
        ]
        pygame.draw.polygon(screen, leather_light, flap_pts)
        pygame.draw.polygon(screen, leather_dark, flap_pts, 2)
        # Schnalle in der Mitte der Klappe
        buckle_cx = modal.x + modal.w // 2
        buckle_cy = modal.y + flap_h - 2
        pygame.draw.rect(screen, brass, (buckle_cx - 12, buckle_cy - 6, 24, 12))
        pygame.draw.rect(screen, brass_dark, (buckle_cx - 12, buckle_cy - 6, 24, 12), 2)
        pygame.draw.rect(screen, leather_dark,
                          (buckle_cx - 8, buckle_cy - 2, 16, 4))

        # Nähte (kleine Punkte entlang des Rands)
        for x in range(modal.x + 20, modal.x + modal.w - 20, 12):
            pygame.draw.circle(screen, stitch, (x, modal.y + flap_h + 4), 1)
            pygame.draw.circle(screen, stitch, (x, modal.y + modal.h - 6), 1)
        for y in range(modal.y + flap_h + 16, modal.y + modal.h - 14, 12):
            pygame.draw.circle(screen, stitch, (modal.x + 6, y), 1)
            pygame.draw.circle(screen, stitch, (modal.x + modal.w - 6, y), 1)

        # Messing-Eck-Beschläge
        corner_size = 18
        for cx, cy in [(modal.x + 4, modal.y + flap_h + 8),
                       (modal.x + modal.w - 4 - corner_size, modal.y + flap_h + 8),
                       (modal.x + 4, modal.y + modal.h - 4 - corner_size),
                       (modal.x + modal.w - 4 - corner_size,
                        modal.y + modal.h - 4 - corner_size)]:
            pygame.draw.rect(screen, brass, (cx, cy, corner_size, corner_size))
            pygame.draw.rect(screen, brass_dark, (cx, cy, corner_size, corner_size), 2)
            pygame.draw.circle(screen, brass_dark,
                                (cx + corner_size // 2, cy + corner_size // 2), 3)

        # Trageriemen-Andeutung (zwei kleine Schlaufen oben)
        for offset in (-modal.w // 3, modal.w // 3):
            sx = modal.x + modal.w // 2 + offset
            pygame.draw.arc(screen, leather_dark,
                            (sx - 10, modal.y - 8, 20, 16), 0, math.pi, 3)
            pygame.draw.circle(screen, brass, (sx, modal.y + 2), 3)

    def _draw_slot(self, screen, r, item, label=None):
        pygame.draw.rect(screen, (32, 26, 20), r)
        pygame.draw.rect(screen, (60, 48, 32), r, 1)
        if label and item is None:
            ls = self.font_small.render(label, True, TEXT_DIM)
            screen.blit(ls, (r.x + r.w // 2 - ls.get_width() // 2,
                             r.y + r.h // 2 - ls.get_height() // 2))
        if item is not None:
            color = RARITY_COLOR[item.rarity]
            # Rarity-Glow für Rare/Unique (pulsiert)
            if item.rarity in ('rare', 'unique'):
                import math
                pulse = abs(math.sin(pygame.time.get_ticks() * 0.004))
                a = int(60 + pulse * 80) if item.rarity == 'unique' else int(40 + pulse * 40)
                glow = pygame.Surface((r.w + 8, r.h + 8), pygame.SRCALPHA)
                pygame.draw.rect(glow, (*color, a), (0, 0, r.w + 8, r.h + 8), 4)
                screen.blit(glow, (r.x - 4, r.y - 4))
            pygame.draw.rect(screen, color, r, 2)
            self._draw_item_icon(screen, r, item)

    def _draw_item_icon(self, screen, r, item):
        from . import sprites as sp
        sp.draw_item_icon(screen, item, r)

    def _draw_char_preview(self, screen, game, modal):
        """Render Player-Sprite zwischen den Equipment-Slots.

        Position ist die freie Mitte zwischen helmet/chest/weapon/ring/amulet.
        Lore-Anchor: Klassen-Fraktion-Label unter Sprite.
        """
        from . import sprites
        from . import quotes as _q
        p = game.player
        # Update #41: Sprite NEBEN der Equipment-Spalte (rechts von 2-Col)
        # statt mittendrin. Macht Layout klar und Slots gut sichtbar.
        cx = modal.x + 250
        cy = modal.y + 160
        # Hintergrund-Vignette für den Char
        bg = pygame.Surface((110, 140), pygame.SRCALPHA)
        for ring_r in (54, 46, 38, 30):
            pygame.draw.circle(
                bg, (40, 30, 20, 25),
                (55, 70), ring_r)
        screen.blit(bg, (cx - 55, cy - 70))
        # Boden-Schatten
        sh = pygame.Surface((60, 16), pygame.SRCALPHA)
        pygame.draw.ellipse(sh, (0, 0, 0, 110), (0, 0, 60, 16))
        screen.blit(sh, (cx - 30, cy + 28))
        # Player-Sprite (statisch — moving=False)
        was_moving = p.moving
        was_dying  = getattr(p, 'dying', False)
        try:
            p.moving = False
            p.dying = False
            sprites.draw_player_at(screen, p, cx, cy + 30, 0.0)
        finally:
            p.moving = was_moving
            p.dying = was_dying
        # Klassen-Fraktion-Label unter dem Sprite
        fac = _q.class_faction(p.cls)
        if fac is not None:
            fac_text = fac['name']
            fac_surf = self.font_small.render(fac_text, True, fac['color'])
            screen.blit(fac_surf,
                        fac_surf.get_rect(center=(cx, cy + 56)))
            asp = f"Aspekt: {fac.get('aspect', '—')}"
            asp_surf = self.font_small.render(asp, True, TEXT_DIM)
            screen.blit(asp_surf,
                        asp_surf.get_rect(center=(cx, cy + 70)))

    def _draw_stats(self, screen, game, modal):
        p = game.player
        eff = progression.effective(p)
        x = modal.x + 24
        y = modal.y + 268
        cls = CLASSES[p.cls]
        head = self.font_med.render(f'Stufe {p.level} {cls["name"]}',
                                    True, GOLD_BRIGHT)
        screen.blit(head, (x, y)); y += 24

        # Update #93: Attribute kompakt in einer Reihe (3 Werte + Buttons)
        # damit die Stats-Sektion mehr Platz hat.
        attrs = [
            ('Str', 'strength',  p.strength),
            ('Int', 'intellect', p.intellect),
            ('Dex', 'dexterity', p.dexterity),
        ]
        self._rects['attr'] = []
        ax = x
        for label, key, val in attrs:
            ls = self.font_small.render(
                f'{label} {val}', True, TEXT)
            screen.blit(ls, (ax, y))
            adv = ls.get_width() + 6
            if p.attr_points > 0:
                btn = pygame.Rect(ax + adv, y - 1, 16, 16)
                pygame.draw.rect(screen, (60, 100, 60), btn)
                pygame.draw.rect(screen, GOLD, btn, 1)
                plus = self.font_small.render('+', True, GOLD_BRIGHT)
                screen.blit(plus, (btn.x + 4, btn.y))
                self._rects['attr'].append((btn, key))
                adv += 20
            ax += adv
        if p.attr_points > 0:
            ap = self.font_small.render(
                f'  · {p.attr_points} Punkte', True, GOLD_BRIGHT)
            screen.blit(ap, (ax, y))
        # Stats-Sektion BEGINNT erst UNTER dem Inv-Grid (Modal.y+322), damit
        # die rechte Spalte (UTILITY) nicht mit dem Grid kollidiert.
        y = max(y + 22, modal.y + 330)

        # Update #94 Fix: 3-Sektionen-Layout, das den mittigen Buchrücken-
        # Divider respektiert: 2 Spalten LINKS davon, 1 Spalte RECHTS davon.
        # Spalten-Breite 180 px, Label-Indent 96 px (genug für „Sichtweite:").
        line_h = 15
        col_w = 180
        col_label_indent = 96
        center_div = modal.x + modal.w // 2
        col1_x = x                       # OFFENSIV (linke Hälfte, ganz links)
        col2_x = x + col_w + 14          # DEFENSIV (linke Hälfte, neben col1)
        col3_x = center_div + 22         # UTILITY (rechte Hälfte, hinter Divider)
        dr_pct = int((1.0 - eff.get('dmg_taken_mult', 1.0)) * 100)
        sections = [
            ('OFFENSIV', col1_x, [
                ('Schaden',    f'{int(eff["damage"])}'),
                ('Krit',
                  f'{int(eff["crit_chance"]*100)}% ×{eff["crit_mult"]:.2f}'),
                ('Tempo',      f'{int(eff["speed"])}'),
                ('Abklingz.',  f'-{int(eff["cdr"]*100)}%'),
                ('Feuer',      f'+{int(eff.get("fire_dmg", 0)*100)}%'),
                ('Frost',      f'+{int(eff.get("cold_dmg", 0)*100)}%'),
                ('Blitz',      f'+{int(eff.get("lit_dmg", 0)*100)}%'),
            ]),
            ('DEFENSIV', col2_x, [
                ('Leben',      f'{int(eff["hp_max"])}'),
                ('HP-Regen',   f'{eff.get("hp_regen", 0):.1f}/s'),
                ('Mana',       f'{int(eff["mp_max"])}'),
                ('MP-Regen',   f'{eff.get("mp_regen", 0):.1f}/s'),
                ('Schad-Red',  f'{dr_pct}%'),
                ('Ausweich',   f'{int(eff.get("dodge_chance", 0)*100)}%'),
                ('Dodge-CDR',  f'-{int(eff.get("dodge_cdr", 0)*100)}%'),
            ]),
            ('UTILITY', col3_x, [
                ('Dornen',     f'{int(eff.get("thorns", 0))}'),
                ('Magnet',     f'+{int(eff.get("magnet_bonus", 0))}'),
                ('Sichtweite', f'+{int(eff.get("light_radius", 0))}'),
                ('Gold',       f'+{int(eff.get("gold_bonus", 0)*100)}%'),
                ('XP',         f'+{int(eff.get("xp_bonus", 0)*100)}%'),
            ]),
        ]
        for title, sx, rows in sections:
            self._stats_section_header(screen, sx, y, title)
            for i, (label, val) in enumerate(rows):
                ly = y + 14 + i * line_h
                screen.blit(self.font_small.render(f'{label}:',
                                                     True, TEXT_DIM),
                             (sx, ly))
                screen.blit(self.font_small.render(val, True, WHITE),
                             (sx + col_label_indent, ly))

    def _stats_section_header(self, screen, x, y, label):
        s = self.font_small.render(f'— {label} —', True, GOLD_BRIGHT)
        screen.blit(s, (x, y))

    def _hovered_item(self, game, mx, my, modal):
        for i, item in enumerate(game.player.inventory):
            if item is None:
                continue
            if self.inv_slot_rect(i, modal).collidepoint(mx, my):
                return item
        for slot, item in game.player.equipment.items():
            if item is None:
                continue
            if self.equip_slot_rect(slot, modal).collidepoint(mx, my):
                return item
        return None

    def handle_rightclick(self, game, mx, my):
        """Rechtsklick auf Inv-Slot = Item droppen (Loot in der Welt)."""
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        for i in range(len(game.player.inventory)):
            if self.inv_slot_rect(i, modal).collidepoint(mx, my):
                item = game.player.inventory[i]
                if item is not None:
                    self._drop_item(game, item)
                    game.player.inventory[i] = None
                return True
        # Rechtsklick auf Equipment: in Inventar zurücklegen
        for slot in SLOTS:
            if self.equip_slot_rect(slot, modal).collidepoint(mx, my):
                progression.try_unequip(game.player, slot)
                return True
        return False

    def _drop_item(self, game, item):
        from .entities import Loot
        from .constants import RARITY_COLOR
        p = game.player
        # Update #57: Drop 30 px vor dem Spieler (nicht direkt drunter) +
        # 2.5 s Grace-Period gegen Insta-Re-Pickup.  User-Bug „hebe sie
        # direkt wieder auf" — vorher landete der Drop auf p.pos exakt.
        import math as _m
        ox = _m.cos(p.facing) * 30
        oy = _m.sin(p.facing) * 30
        loot = Loot(p.pos.x + ox, p.pos.y + oy, gold=0, item=item)
        loot.color = RARITY_COLOR[item.rarity]
        loot._drop_grace_t = 2.5  # 2.5 s nicht-pickupbar
        game.loot.append(loot)

    # Update #84: Affix-Power-Weights (heuristisch für Vergleichs-Score).
    # Skala in Punkten / Stat-Einheit, abgeleitet aus AFFIXES-Ranges.
    _AFFIX_WEIGHT = {
        'dmg_flat':    1.2,
        'dmg_pct':     1.5,
        'hp':          0.5,
        'mp':          0.3,
        'hp_regen':    3.0,
        'mp_regen':    1.0,
        'crit_chance': 2.5,
        'crit_dmg':    0.8,
        'speed':       2.0,
        'cdr':         1.5,
        'fire_dmg':    1.0,
        'cold_dmg':    1.0,
        'lit_dmg':     1.0,
        'dodge_cdr':   1.2,
        'thorns':      0.8,
        'light_radius': 4.0,
    }

    def _item_power(self, item):
        """Heuristik-Score für Item-Vergleich.
        Affix-Summe gewichtet + Rarity-Boost + Sockets.
        """
        if item is None:
            return 0.0
        score = 0.0
        for key, val in getattr(item, 'affixes', []):
            score += self._AFFIX_WEIGHT.get(key, 1.0) * float(val)
        rarity_bonus = {'common': 0, 'magic': 8,
                         'rare': 22, 'unique': 45}.get(item.rarity, 0)
        score += rarity_bonus
        score += len(getattr(item, 'sockets', []) or []) * 5
        return score

    def _affix_deltas(self, hovered, equipped):
        """Map affix_key → 'up'/'down'/'eq'/'new' für die Tooltip-Färbung."""
        h_aff = {k: v for k, v in getattr(hovered, 'affixes', [])}
        e_aff = {k: v for k, v in getattr(equipped, 'affixes', [])}
        out = {}
        for k, v in h_aff.items():
            if k not in e_aff:
                out[k] = 'new'
            elif v > e_aff[k]:
                out[k] = 'up'
            elif v < e_aff[k]:
                out[k] = 'down'
            else:
                out[k] = 'eq'
        return out

    def _draw_tooltip(self, screen, item, mx, my, header=None,
                       delta_map=None, power_delta=None):
        lines = list(item.display_lines())
        if header:
            lines.insert(0, (header, 'dim'))
        # Update #84: Power-Delta-Header bei Vergleich
        if power_delta is not None:
            if power_delta > 0.5:
                pd_text = f'▲ STÄRKER  (+{power_delta:.1f})'
                pd_kind = 'delta_up'
            elif power_delta < -0.5:
                pd_text = f'▼ SCHWÄCHER  ({power_delta:.1f})'
                pd_kind = 'delta_down'
            else:
                pd_text = '= GLEICHWERTIG'
                pd_kind = 'delta_eq'
            lines.insert(1 if not header else 2, (pd_text, pd_kind))
        # Map affixes-key zu Tooltip-Line-Index — wir matchen über
        # die label-Strings aus AFFIXES (rendert 1:1 die display_lines-Order)
        # Maße berechnen
        rendered = []
        max_w = 0
        from .constants import AFFIXES as _AFFIXES
        # Build label→key map fürs Color-Coding
        affix_label_to_key = {}
        for k, (label, lo, hi, slots) in _AFFIXES.items():
            # Strip placeholder, take prefix as match-key
            tag = label.split('{v')[0].strip()
            affix_label_to_key[tag] = k
        for text, kind in lines:
            if kind in RARITY_COLOR:
                color = RARITY_COLOR[kind]
                font = self.font_med
            elif kind == 'dim':
                color = TEXT_DIM
                font = self.font_small
            elif kind == 'delta_up':
                color = (140, 230, 140)
                font = self.font_small
            elif kind == 'delta_down':
                color = (230, 140, 140)
                font = self.font_small
            elif kind == 'delta_eq':
                color = (200, 200, 200)
                font = self.font_small
            else:
                # Default: affix-Color, ggf. overridden durch delta_map
                color = (170, 200, 255)
                font = self.font_small
                if delta_map is not None and kind == 'affix':
                    # Find affix-key via label-prefix-match
                    for tag, akey in affix_label_to_key.items():
                        if text.startswith(tag.split(' ')[0]):
                            d = delta_map.get(akey)
                            if d == 'up' or d == 'new':
                                color = (140, 230, 140)
                            elif d == 'down':
                                color = (230, 140, 140)
                            elif d == 'eq':
                                color = (200, 200, 200)
                            break
            surf = font.render(text, True, color)
            rendered.append(surf)
            max_w = max(max_w, surf.get_width())
        pad = 8
        h = sum(s.get_height() for s in rendered) + pad * 2 + 4 * (len(rendered) - 1)
        w = max_w + pad * 2

        # Tooltip-Position so platzieren dass sie sichtbar bleibt
        tx = mx + 18
        ty = my + 8
        if tx + w > SCREEN_W - 8:
            tx = mx - w - 18
        if ty + h > SCREEN_H - 8:
            ty = SCREEN_H - h - 8

        bg = pygame.Surface((w, h), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 240))
        screen.blit(bg, (tx, ty))
        pygame.draw.rect(screen, GOLD, (tx, ty, w, h), 1)
        cy = ty + pad
        for surf in rendered:
            screen.blit(surf, (tx + pad, cy))
            cy += surf.get_height() + 4
