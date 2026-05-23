"""Stash-UI: persistente Truhe mit 48 Slots."""

import pygame

from .constants import (
    SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM, WHITE,
    RARITY_COLOR, SLOTS, SLOT_NAME,
)


class StashUI:
    SLOT_SIZE = 46
    INV_COLS = 6
    INV_ROWS = 4
    STASH_COLS = 8
    STASH_ROWS = 6

    def __init__(self, font_small, font_med):
        self.font_small = font_small
        self.font_med = font_med
        self.tab = 'items'  # 'items' | 'gems'

    def _tab_rects(self, modal):
        out = []
        for i, (key, label) in enumerate([('items', 'Items'),
                                           ('gems',  'Edelsteine')]):
            # Tabs unter dem Titel (modal.y + 64 reicht jetzt bis 86, sodass
            # die Sub-Labels darunter kein Overlap mehr verursachen).
            rect = pygame.Rect(modal.x + 24 + i * 120, modal.y + 100, 110, 24)
            out.append((rect, key, label))
        return out

    def _gem_rect(self, idx, modal):
        col = idx % self.STASH_COLS
        row = idx // self.STASH_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 4)
        y = modal.y + 90 + row * (self.SLOT_SIZE + 4)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def modal_rect(self):
        # Update #146 (User-Report „Stash unbenutzbar"): Modal-Höhe von
        # 580 → 720 erhöht damit Stash (6 Reihen × 50 = 300) und
        # Inventar (4 × 50 = 200) NICHT mehr überlappen. Layout-Math:
        # 92 Header + 6*50 Stash + 60 Gap + 20 Inv-Label + 4*50 Inv
        # + 50 Footer = ~720
        w, h = 880, 720
        return pygame.Rect(SCREEN_W // 2 - w // 2,
                            SCREEN_H // 2 - h // 2, w, h)

    def _stash_rect(self, idx, modal):
        col = idx % self.STASH_COLS
        row = idx // self.STASH_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 4)
        # Slots starten unter Tabs (100-124) + Sub-Label (130) = 154
        y = modal.y + 154 + row * (self.SLOT_SIZE + 4)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def _inv_rect(self, idx, modal):
        col = idx % self.INV_COLS
        row = idx // self.INV_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 4)
        # Update #146: Inv-Section nach UNTEN verschoben — Stash endet
        # bei modal.y + 154 + 6*50 = modal.y + 454.  Inv-Sub-Label bei
        # 480, Slots ab 504 → kein Overlap mehr mit Stash.
        y = modal.y + 504 + row * (self.SLOT_SIZE + 4)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        p = game.player

        # Tab-Buttons
        for rect, key, _ in self._tab_rects(modal):
            if rect.collidepoint(mx, my):
                self.tab = key
                return True

        if self.tab == 'gems':
            # Edelsteine sind read-only Anzeige
            return True

        # Update #146 (User-Report „Stash unbenutzbar"): Empty-Slots
        # konsumieren den Click NICHT mehr — sonst werden überlappende
        # Klicks falsch geroutet (Klick auf leeren Stash-Slot blockte
        # vorher den Inv-Click auf den OVERLAP).
        # Stash → Inventar
        for i in range(len(p.stash)):
            if self._stash_rect(i, modal).collidepoint(mx, my):
                it = p.stash[i]
                if it is None:
                    continue   # Click durchreichen
                # Versuche Transfer
                for k, s in enumerate(p.inventory):
                    if s is None:
                        p.inventory[k] = it
                        p.stash[i] = None
                        try:
                            import sf.sounds as _snd
                            _snd.play('ui_click', volume=0.4)
                        except Exception:
                            pass
                        return True
                # Inventar voll — Feedback
                try:
                    game.toast('Inventar voll.', (220, 130, 80))
                except Exception:
                    pass
                return True
        # Inventar → Stash
        for i in range(len(p.inventory)):
            if self._inv_rect(i, modal).collidepoint(mx, my):
                it = p.inventory[i]
                if it is None:
                    continue   # Click durchreichen
                # Versuche Transfer
                for k, s in enumerate(p.stash):
                    if s is None:
                        p.stash[k] = it
                        p.inventory[i] = None
                        try:
                            import sf.sounds as _snd
                            _snd.play('ui_click', volume=0.4)
                        except Exception:
                            pass
                        return True
                try:
                    game.toast('Truhe voll.', (220, 130, 80))
                except Exception:
                    pass
                return True
        return True

    def draw(self, screen, game):
        import math
        p = game.player
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))
        modal = self.modal_rect()
        # --- Truhe-Themed Background ---
        wood = (110, 75, 45)
        wood_dark = (70, 45, 25)
        iron = (90, 90, 100)
        iron_dark = (50, 50, 60)
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((*wood, 245))
        screen.blit(bg, modal.topleft)
        # Holz-Maserung-Linien
        for y in range(modal.y + 16, modal.y + modal.h - 16, 18):
            pygame.draw.line(screen, wood_dark,
                              (modal.x + 16, y), (modal.x + modal.w - 16, y), 1)
        # Eisenbeschläge oben/unten
        pygame.draw.rect(screen, iron,
                         (modal.x + 8, modal.y + 8, modal.w - 16, 14))
        pygame.draw.rect(screen, iron_dark,
                         (modal.x + 8, modal.y + 8, modal.w - 16, 14), 2)
        pygame.draw.rect(screen, iron,
                         (modal.x + 8, modal.y + modal.h - 22, modal.w - 16, 14))
        pygame.draw.rect(screen, iron_dark,
                         (modal.x + 8, modal.y + modal.h - 22, modal.w - 16, 14), 2)
        # Nieten in den Eisenbeschlägen
        for x in range(modal.x + 20, modal.x + modal.w - 20, 28):
            pygame.draw.circle(screen, iron_dark, (x, modal.y + 15), 2)
            pygame.draw.circle(screen, iron_dark, (x, modal.y + modal.h - 15), 2)
        # Großes Schloss oben mittig
        lock_cx = modal.x + modal.w // 2
        lock_cy = modal.y + 30
        pygame.draw.rect(screen, iron, (lock_cx - 20, lock_cy - 4, 40, 28))
        pygame.draw.rect(screen, iron_dark, (lock_cx - 20, lock_cy - 4, 40, 28), 2)
        # Schloss-Bügel (offen, oben drüber)
        pygame.draw.arc(screen, iron_dark, (lock_cx - 14, lock_cy - 18, 28, 24),
                         0, math.pi, 4)
        # Schlüsselloch
        pygame.draw.circle(screen, (20, 20, 20), (lock_cx, lock_cy + 10), 4)
        pygame.draw.line(screen, (20, 20, 20),
                          (lock_cx, lock_cy + 14), (lock_cx, lock_cy + 20), 2)
        # Innen-Rahmen — unter Title (66) und über unteren Eisen-Beschlag
        inner = pygame.Rect(modal.x + 18, modal.y + 92,
                             modal.w - 36, modal.h - 124)
        pygame.draw.rect(screen, (40, 28, 18), inner)
        pygame.draw.rect(screen, wood_dark, inner, 2)

        # Title links über den Tabs — kein Overlap mit Schloss oder Tabs mehr.
        title = self.font_med.render('TRUHE — Mahnmal-Verwahrer',
                                      True, (240, 220, 180))
        screen.blit(title, (modal.x + 26, modal.y + 66))
        # Hint unten, NICHT mehr im oberen Eisenbeschlag.
        hint = self.font_small.render(
            'Klick: Transfer · F: Schließen',
            True, TEXT_DIM)
        screen.blit(hint, (modal.x + modal.w - hint.get_width() - 26,
                           modal.y + 70))

        # Tabs
        for rect, key, label in self._tab_rects(modal):
            active = (key == self.tab)
            bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            bg.fill((40, 30, 14, 240) if active else (24, 18, 10, 200))
            screen.blit(bg, rect.topleft)
            pygame.draw.rect(screen, GOLD if active else (60, 50, 40), rect, 1)
            ls = self.font_small.render(label, True,
                                         GOLD_BRIGHT if active else TEXT_DIM)
            screen.blit(ls, ls.get_rect(center=rect.center))

        if self.tab == 'items':
            sl = self.font_small.render('TRUHE', True, TEXT_DIM)
            screen.blit(sl, (modal.x + 24, modal.y + 134))
            for i, it in enumerate(p.stash):
                r = self._stash_rect(i, modal)
                self._draw_slot(screen, r, it)

            # Update #146: INVENTAR-Label bei modal.y+484 (über _inv_rect-Start
            # bei +504).  Trennlinie zwischen Stash + Inv.
            divider_y = modal.y + 470
            pygame.draw.line(screen, (90, 65, 40),
                              (modal.x + 24, divider_y),
                              (modal.x + modal.w - 24, divider_y), 1)
            il = self.font_small.render('INVENTAR', True, TEXT_DIM)
            screen.blit(il, (modal.x + 24, modal.y + 484))
            for i, it in enumerate(p.inventory):
                r = self._inv_rect(i, modal)
                self._draw_slot(screen, r, it)
        else:
            # Edelsteine-Tab
            sl = self.font_small.render(f'EDELSTEINE ({len(p.gems)})',
                                         True, TEXT_DIM)
            screen.blit(sl, (modal.x + 24, modal.y + 80))
            from .constants import GEM_TYPES
            import math as _m
            for i, gem in enumerate(p.gems[:48]):
                r = self._gem_rect(i, modal)
                gd = GEM_TYPES[gem]
                pygame.draw.rect(screen, (32, 26, 20), r)
                pygame.draw.rect(screen, gd['color'], r, 2)
                # Glow-Hintergrund
                pulse = abs(_m.sin(pygame.time.get_ticks() * 0.004
                                    + i * 0.5))
                glow = pygame.Surface((40, 40), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*gd['color'],
                                            int(80 + pulse * 60)),
                                    (20, 20), 16)
                screen.blit(glow, (r.centerx - 20, r.centery - 20))
                # 3D-Edelstein: Raute mit Facetten
                cx, cy = r.centerx, r.centery
                main = [
                    (cx, cy - 14),
                    (cx + 11, cy),
                    (cx, cy + 14),
                    (cx - 11, cy),
                ]
                # Schatten
                shadow = [(p_[0], p_[1] + 2) for p_ in main]
                pygame.draw.polygon(screen, (0, 0, 0), shadow)
                # Hauptkörper
                pygame.draw.polygon(screen, gd['color'], main)
                # Facetten-Linien (kreuz)
                pygame.draw.line(screen,
                                  tuple(min(255, c + 40) for c in gd['color']),
                                  (cx, cy - 14), (cx, cy + 14), 1)
                pygame.draw.line(screen,
                                  tuple(max(0, c - 40) for c in gd['color']),
                                  (cx - 11, cy), (cx + 11, cy), 1)
                # Heller Glanz oben links
                pygame.draw.polygon(screen, (255, 255, 255), [
                    (cx, cy - 13), (cx + 5, cy - 6), (cx, cy - 2),
                ])
                # Outline
                pygame.draw.polygon(screen, (0, 0, 0), main, 2)

        # Tooltip
        mx, my = pygame.mouse.get_pos()
        hovered = self._hovered(p, modal, mx, my)
        if hovered:
            self._draw_tooltip(screen, hovered, mx, my)

    def _hovered(self, p, modal, mx, my):
        for i, it in enumerate(p.stash):
            if it and self._stash_rect(i, modal).collidepoint(mx, my):
                return it
        for i, it in enumerate(p.inventory):
            if it and self._inv_rect(i, modal).collidepoint(mx, my):
                return it
        return None

    def _draw_slot(self, screen, r, item):
        pygame.draw.rect(screen, (32, 26, 20), r)
        pygame.draw.rect(screen, (60, 48, 32), r, 1)
        if item is not None:
            color = RARITY_COLOR[item.rarity]
            pygame.draw.rect(screen, color, r, 2)
            from . import sprites as sp
            sp.draw_item_icon(screen, item, r)

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
