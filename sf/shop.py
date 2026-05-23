"""Vendor / Händler-UI: kaufen und verkaufen."""

import random
import pygame

from .constants import (
    SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM, WHITE,
    RARITY_COLOR, SLOTS, SLOT_NAME, AFFIXES, FLOAT_AFFIXES,
)
from . import items as items_mod


def item_value(item):
    """Verkaufspreis basierend auf Rarity und ilvl."""
    base = {'common': 5, 'magic': 18, 'rare': 50, 'unique': 120}[item.rarity]
    return base + item.ilvl * 5


def buy_price(item):
    """Kaufpreis (~3× Verkaufswert)."""
    return item_value(item) * 3


class ShopUI:
    SLOT_SIZE = 50
    GRID_COLS = 6
    GRID_ROWS = 4

    def __init__(self, font_small, font_med):
        self.font_small = font_small
        self.font_med = font_med
        self._stock = []
        self._stock_level = 0
        self.filter = 'all'  # 'all' | 'weapon' | 'armor' | 'jewelry'
        self.buyback = []    # zuletzt verkaufte Items (max 5)

    def restock(self, level):
        """Generiert 12 zufällige Items basierend auf Level."""
        self._stock = []
        self._stock_level = level
        for _ in range(12):
            ilvl = max(1, level + random.randint(-2, 2))
            it = items_mod.make_item(ilvl=ilvl)
            self._stock.append(it)

    def maybe_restock(self, level):
        """Erstmaliges Auffüllen oder bei Level-Änderung."""
        if not self._stock or abs(self._stock_level - level) >= 3:
            self.restock(level)

    def modal_rect(self):
        # Update #147 (User-Report „Shop-UI sieht man nicht ganz"):
        # Modal-Höhe von 540 → 720.  Layout vorher:
        #   - Stock-Grid endete bei y=314
        #   - Inv-Grid startete bei y=320, endete bei y=544 (über Modal-Rand!)
        #   - Buyback bei y=460 → ÜBERLAPPTE Inv-Reihe 3
        # Jetzt: jede Section in eigenem Y-Bereich, klare Trennung.
        w, h = 820, 720
        return pygame.Rect(SCREEN_W // 2 - w // 2,
                            SCREEN_H // 2 - h // 2, w, h)

    def _stock_rect(self, idx, modal):
        col = idx % self.GRID_COLS
        row = idx // self.GRID_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 6)
        y = modal.y + 100 + row * (self.SLOT_SIZE + 6)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def _inv_rect(self, idx, modal):
        col = idx % self.GRID_COLS
        row = idx // self.GRID_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 6)
        # Update #147: Inv von y=320 → y=360 verschoben.
        # Stock endet bei modal.y + 100 + 4*56 = +324.  Gap 36 px für
        # Sub-Label „INVENTAR".  Inv 4×56 = 224 → endet bei +584.
        y = modal.y + 360 + row * (self.SLOT_SIZE + 6)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def _restock_btn(self, modal):
        return pygame.Rect(modal.x + modal.w - 130, modal.y + 16, 110, 28)

    def _filter_rects(self, modal):
        """4 Filter-Buttons: Alle / Waffen / Rüstung / Schmuck."""
        labels = [('all', 'Alle'), ('weapon', 'Waffen'),
                  ('armor', 'Rüstung'), ('jewelry', 'Schmuck')]
        bx = modal.x + 24
        by = modal.y + 56
        out = []
        for i, (key, label) in enumerate(labels):
            out.append((pygame.Rect(bx + i * 86, by, 80, 22), key, label))
        return out

    def _filtered_stock(self):
        """Returnt Stock gefiltert nach self.filter."""
        weapon_slots = {'weapon'}
        armor_slots = {'helmet', 'chest'}
        jewelry_slots = {'ring', 'amulet'}
        out = []
        for it in self._stock:
            if it is None:
                out.append(None)
                continue
            if self.filter == 'all':
                out.append(it)
            elif self.filter == 'weapon' and it.slot in weapon_slots:
                out.append(it)
            elif self.filter == 'armor' and it.slot in armor_slots:
                out.append(it)
            elif self.filter == 'jewelry' and it.slot in jewelry_slots:
                out.append(it)
            else:
                out.append(None)
        return out

    def _buyback_rect(self, idx, modal):
        # Update #147: Buyback-Row unter dem Inv-Grid (klar getrennt).
        # Inv endet bei modal.y + 360 + 4*56 = +584.  Sub-Label „RÜCKKAUF"
        # bei +604.  Buyback-Row bei +630 → endet bei +680.  Modal 720
        # gibt 40 px Footer-Padding.
        x = modal.x + 24 + idx * (self.SLOT_SIZE + 6)
        y = modal.y + 630
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        p = game.player
        # Filter-Buttons
        for rect, key, _ in self._filter_rects(modal):
            if rect.collidepoint(mx, my):
                self.filter = key
                return True
        # Restock-Button
        if self._restock_btn(modal).collidepoint(mx, my):
            cost = 50
            if p.gold >= cost:
                p.gold -= cost
                self.restock(p.level)
            return True
        # Items kaufen (durch Filter)
        filtered = self._filtered_stock()
        for i, it in enumerate(filtered):
            if it is None:
                continue
            if self._stock_rect(i, modal).collidepoint(mx, my):
                price = buy_price(it)
                if p.gold >= price:
                    for k, s in enumerate(p.inventory):
                        if s is None:
                            p.inventory[k] = it
                            p.gold -= price
                            self._stock[self._stock.index(it)] = None
                            return True
                return True
        # Buyback (gleicher Preis wie verkauft)
        for i, bb in enumerate(self.buyback):
            if self._buyback_rect(i, modal).collidepoint(mx, my):
                price = item_value(bb)  # Buyback = gleicher Preis
                if p.gold >= price:
                    for k, s in enumerate(p.inventory):
                        if s is None:
                            p.inventory[k] = bb
                            p.gold -= price
                            self.buyback.pop(i)
                            return True
                return True
        # Items verkaufen (aus Inventar)
        for i in range(len(p.inventory)):
            if self._inv_rect(i, modal).collidepoint(mx, my):
                it = p.inventory[i]
                if it is not None:
                    p.gold += item_value(it)
                    p.inventory[i] = None
                    # In Buyback-Liste (max 5)
                    self.buyback.insert(0, it)
                    if len(self.buyback) > 5:
                        self.buyback.pop()
                return True
        return True

    def draw(self, screen, game):
        import math
        p = game.player
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        modal = self.modal_rect()
        # --- Marktstand-Themed Background ---
        wood = (110, 75, 45)
        wood_dark = (70, 45, 25)
        sail_red = (180, 50, 50)
        sail_red_dark = (130, 30, 30)
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((90, 65, 40, 245))
        screen.blit(bg, modal.topleft)
        # Sonnensegel oben (rotes Stoff-Dach mit Wellen)
        sail_h = 40
        sail_pts = [
            (modal.x + 8, modal.y + 8),
            (modal.x + modal.w // 2, modal.y + 4),
            (modal.x + modal.w - 8, modal.y + 8),
            (modal.x + modal.w - 8, modal.y + sail_h),
            (modal.x + 8, modal.y + sail_h),
        ]
        pygame.draw.polygon(screen, sail_red, sail_pts)
        pygame.draw.polygon(screen, sail_red_dark, sail_pts, 3)
        # Wellen am Sonnensegel-Rand
        for k in range(int(modal.w / 30) - 1):
            cx_s = modal.x + 20 + k * 30
            pygame.draw.arc(screen, sail_red_dark,
                             (cx_s, modal.y + sail_h - 4, 30, 12),
                             math.pi, math.tau, 2)
        # Goldene Quasten
        for x_t in (modal.x + 20, modal.x + modal.w - 20):
            pygame.draw.line(screen, GOLD,
                              (x_t, modal.y + sail_h),
                              (x_t, modal.y + sail_h + 14), 2)
            pygame.draw.circle(screen, GOLD,
                                (x_t, modal.y + sail_h + 16), 3)
        # Pfosten links/rechts (Holz)
        pygame.draw.rect(screen, wood, (modal.x + 8, modal.y + sail_h,
                                          12, modal.h - sail_h - 8))
        pygame.draw.rect(screen, wood, (modal.x + modal.w - 20, modal.y + sail_h,
                                          12, modal.h - sail_h - 8))
        pygame.draw.rect(screen, wood_dark, (modal.x + 8, modal.y + sail_h,
                                              12, modal.h - sail_h - 8), 2)
        pygame.draw.rect(screen, wood_dark, (modal.x + modal.w - 20, modal.y + sail_h,
                                              12, modal.h - sail_h - 8), 2)
        # Innen
        inner = pygame.Rect(modal.x + 22, modal.y + sail_h + 4,
                             modal.w - 44, modal.h - sail_h - 12)
        pygame.draw.rect(screen, (40, 28, 18), inner)
        pygame.draw.rect(screen, wood_dark, inner, 2)
        # Verkaufstheke (Hervorgehobener Streifen)
        pygame.draw.rect(screen, wood_dark, (modal.x + 22, modal.y + sail_h + 4,
                                              modal.w - 44, 8))
        # Schild oben mittig
        sign_x = modal.x + modal.w // 2 - 80
        sign_y = modal.y + sail_h - 6
        pygame.draw.rect(screen, (170, 130, 80), (sign_x, sign_y, 160, 20))
        pygame.draw.rect(screen, wood_dark, (sign_x, sign_y, 160, 20), 2)

        title = self.font_med.render('ALDRIC', True, (60, 30, 10))
        screen.blit(title, title.get_rect(center=(modal.x + modal.w // 2,
                                                   sign_y + 11)))
        gold_t = self.font_small.render(f'Gold: {p.gold}', True, GOLD_BRIGHT)
        screen.blit(gold_t, (modal.x + 28, modal.y + sail_h + 18))

        rb = self._restock_btn(modal)
        pygame.draw.rect(screen, (40, 30, 14), rb)
        pygame.draw.rect(screen, GOLD, rb, 2)
        rt = self.font_small.render('Neu: 50g', True, GOLD_BRIGHT)
        screen.blit(rt, (rb.centerx - rt.get_width() // 2, rb.y + 6))

        # Filter-Buttons
        for rect, key, label in self._filter_rects(modal):
            active = (key == self.filter)
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((40, 30, 14, 240) if active else (24, 18, 10, 200))
            screen.blit(bg, rect.topleft)
            pygame.draw.rect(screen, GOLD if active else (60, 50, 40), rect, 1)
            ls = self.font_small.render(label, True,
                                         GOLD_BRIGHT if active else TEXT_DIM)
            screen.blit(ls, ls.get_rect(center=rect.center))

        # Bestand
        for i, it in enumerate(self._filtered_stock()):
            r = self._stock_rect(i, modal)
            self._draw_item_slot(screen, r, it, price=buy_price(it) if it else None,
                                 can_afford=(it is not None and p.gold >= buy_price(it)))

        # Update #147: Layout-Refactor — alle Labels zur neuen Position.
        # Trennlinie zwischen Stock und Inv
        pygame.draw.line(screen, (90, 65, 40),
                          (modal.x + 24, modal.y + 340),
                          (modal.x + modal.w - 24, modal.y + 340), 1)
        # Inventar-Label
        il = self.font_small.render(
            'INVENTAR (Klick = verkaufen)', True, TEXT_DIM)
        screen.blit(il, (modal.x + 24, modal.y + 344))
        for i, it in enumerate(p.inventory):
            r = self._inv_rect(i, modal)
            self._draw_item_slot(screen, r, it,
                                 price=item_value(it) if it else None,
                                 can_afford=True, sell=True)

        # Trennlinie zwischen Inv und Buyback
        pygame.draw.line(screen, (90, 65, 40),
                          (modal.x + 24, modal.y + 600),
                          (modal.x + modal.w - 24, modal.y + 600), 1)
        # Buyback-Bereich (Label + Row)
        bb_label = self.font_small.render(
            'ZURÜCKKAUFEN (letzte 5 verkaufte)', True, TEXT_DIM)
        screen.blit(bb_label, (modal.x + 24, modal.y + 606))
        for i, it in enumerate(self.buyback):
            r = self._buyback_rect(i, modal)
            self._draw_item_slot(screen, r, it, price=item_value(it),
                                 can_afford=(p.gold >= item_value(it)))

        # Hinweis
        hint = self.font_small.render('F: Schließen', True, TEXT_DIM)
        screen.blit(hint, (modal.x + 24, modal.y + modal.h - 22))

        # Tooltip
        mx, my = pygame.mouse.get_pos()
        hovered = self._hovered(p, modal, mx, my)
        if hovered:
            self._draw_tooltip(screen, hovered, mx, my)

    def _hovered(self, p, modal, mx, my):
        for i, it in enumerate(self._stock):
            if it and self._stock_rect(i, modal).collidepoint(mx, my):
                return it
        for i, it in enumerate(p.inventory):
            if it and self._inv_rect(i, modal).collidepoint(mx, my):
                return it
        return None

    def _draw_item_slot(self, screen, r, item, price=None, can_afford=True, sell=False):
        pygame.draw.rect(screen, (32, 26, 20), r)
        pygame.draw.rect(screen, (60, 48, 32), r, 1)
        if item is not None:
            color = RARITY_COLOR[item.rarity]
            pygame.draw.rect(screen, color, r, 2)
            from . import sprites as sp
            sp.draw_item_icon(screen, item, r)
            if price is not None:
                col = GOLD_BRIGHT if can_afford else (160, 80, 80)
                ps = self.font_small.render(f'{price}g', True, col)
                screen.blit(ps, (r.x + 2, r.bottom - 14))

    def _draw_tooltip(self, screen, item, mx, my):
        lines = item.display_lines()
        rendered = []
        max_w = 0
        for text, kind in lines:
            if kind in RARITY_COLOR:
                color = RARITY_COLOR[kind]
                font = self.font_med
            elif kind == 'dim':
                color = TEXT_DIM
                font = self.font_small
            else:
                color = (170, 200, 255)
                font = self.font_small
            s = font.render(text, True, color)
            rendered.append(s)
            max_w = max(max_w, s.get_width())
        pad = 8
        h = sum(s.get_height() for s in rendered) + pad * 2 + 4 * (len(rendered) - 1)
        w = max_w + pad * 2
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
        for s in rendered:
            screen.blit(s, (tx + pad, cy))
            cy += s.get_height() + 4
