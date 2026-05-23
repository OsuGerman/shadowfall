"""Crafting-Werkstatt: Items aufwerten, Affixe umrollen, Sockel mit Edelsteinen besetzen."""

import random
import pygame

from . import sounds as _snd  # Update #X — Phase-2-AI-SFX hook
from .constants import (
    SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM, WHITE, BLACK,
    SLOTS, SLOT_NAME, RARITY_COLOR, AFFIXES, FLOAT_AFFIXES, GEM_TYPES,
    CRAFT_COSTS,
)
from .items import _roll_value, _affix_count


# ============================================================
# CRAFTING-AKTIONEN
# ============================================================
def upgrade_cost(item):
    spec = CRAFT_COSTS['upgrade']
    return spec['gold'] + spec['per_ilvl'] * item.ilvl


def can_upgrade(player, item):
    return player.gold >= upgrade_cost(item)


def upgrade_item(player, item):
    """+1 ilvl, Affixe werden GARANTIERT besser (mindestens +10%, oft mehr)."""
    cost = upgrade_cost(item)
    if player.gold < cost:
        return False
    player.gold -= cost
    item.ilvl += 1
    new_affixes = []
    from .constants import FLOAT_AFFIXES
    import math as _m
    for key, old_val in item.affixes:
        # Drei Rolls würfeln, höchsten nehmen + immer GARANTIERT besser
        rolls = [_roll_value(key, item.ilvl) for _ in range(3)]
        new_val = max(rolls)
        if key in FLOAT_AFFIXES:
            # mind. +10% (mit ceil), mindestens +0.5
            new_val = max(new_val, old_val * 1.10, old_val + 0.5)
            new_val = round(new_val * 2) / 2
        else:
            # mind. +10% (math.ceil), mindestens +1
            new_val = max(new_val, int(_m.ceil(old_val * 1.10)), int(old_val) + 1)
        new_affixes.append((key, new_val))
    item.affixes = new_affixes
    _snd.play('craft_hammer', volume=0.6)
    _snd.play('upgrade_success', volume=0.5)
    return True


def reroll_cost(item):
    return CRAFT_COSTS['reroll']['gold']


def can_reroll(player, item):
    return player.gold >= reroll_cost(item) and item.rarity != 'common'


def reroll_item(player, item):
    """Komplett neue Affixe würfeln (gleiche Anzahl, gleicher Slot/Rarity)."""
    cost = reroll_cost(item)
    if player.gold < cost or item.rarity == 'common':
        return False
    player.gold -= cost
    pool = [k for k, spec in AFFIXES.items() if item.slot in spec[3]]
    n = min(_affix_count(item.rarity), len(pool))
    chosen = random.sample(pool, n) if n > 0 else []
    item.affixes = [(k, _roll_value(k, item.ilvl)) for k in chosen]
    _snd.play('reroll_orb', volume=0.7)
    return True


def socket_cost():
    return CRAFT_COSTS['socket']['gold']


def can_socket(player, item, gem_type):
    if player.gold < socket_cost():
        return False
    if gem_type not in player.gems:
        return False
    return any(s is None for s in item.sockets)


def socket_gem(player, item, gem_type):
    """Setzt einen Edelstein in den ersten freien Sockel."""
    if not can_socket(player, item, gem_type):
        return False
    player.gold -= socket_cost()
    for i, s in enumerate(item.sockets):
        if s is None:
            item.sockets[i] = gem_type
            player.gems.remove(gem_type)
            _snd.play('gem_socket', volume=0.7)
            return True
    return False


def enchant_cost(item):
    """Verzauberungs-Kosten skalieren mit ilvl."""
    return 200 + item.ilvl * 60


def can_enchant(player, item):
    """Item kann verzaubert werden wenn Spieler genug Gold hat
    und das Item < max Affix-Zahl."""
    max_affixes = {'common': 1, 'magic': 3, 'rare': 5, 'unique': 6}[item.rarity]
    return (player.gold >= enchant_cost(item) and
            len(item.affixes) < max_affixes)


def enchant_item(player, item):
    """Fügt einen zufälligen neuen Affix hinzu."""
    import random
    from .constants import AFFIXES
    if not can_enchant(player, item):
        return False
    player.gold -= enchant_cost(item)
    # Pool aller Affixe die noch nicht am Item sind
    existing = {k for k, _ in item.affixes}
    pool = [k for k, spec in AFFIXES.items()
            if item.slot in spec[3] and k not in existing]
    if not pool:
        return False
    new_key = random.choice(pool)
    item.affixes.append((new_key, _roll_value(new_key, item.ilvl)))
    _snd.play('upgrade_success', volume=0.5)
    _snd.play('craft_anvil', volume=0.45)
    return True


def salvage_value(item):
    """Wieviel Gold gibt Salvage zurück (besser als Vendor-Verkauf)."""
    base = {'common': 12, 'magic': 35, 'rare': 90, 'unique': 220}[item.rarity]
    return base + item.ilvl * 8


def salvage_item(player, item):
    """Recycelt Item → Gold + Chance auf Gem. Entfernt aus Inventar nicht
    (Aufrufer macht das nach erfolgreichem Call).
    """
    import random
    gold = salvage_value(item)
    player.gold += gold
    extra_gem = None
    chance = {'common': 0.05, 'magic': 0.20, 'rare': 0.50, 'unique': 1.0}[item.rarity]
    if random.random() < chance:
        from .constants import GEM_TYPES
        extra_gem = random.choice(list(GEM_TYPES.keys()))
        player.gems.append(extra_gem)
    _snd.play('salvage_breakdown', volume=0.6)
    return (gold, extra_gem)


def random_gem():
    """Returnt einen zufälligen Gem-Type-Key."""
    return random.choice(list(GEM_TYPES.keys()))


# ============================================================
# CRAFTING-UI
# ============================================================
class CraftingUI:
    SLOT_SIZE = 50
    GRID_COLS = 6
    GRID_ROWS = 4

    def __init__(self, font_small, font_med, font_dmg):
        self.font_small = font_small
        self.font_med = font_med
        self.font_dmg = font_dmg
        self.selected = None  # ('inv', idx) | ('equip', slot) | None

    def modal_rect(self):
        w, h = 820, 540
        return pygame.Rect(SCREEN_W // 2 - w // 2, SCREEN_H // 2 - h // 2, w, h)

    # -------- Layout-Helfer --------
    def _inv_slot_rect(self, idx, modal):
        col = idx % self.GRID_COLS
        row = idx // self.GRID_COLS
        x = modal.x + 24 + col * (self.SLOT_SIZE + 6)
        y = modal.y + 80 + row * (self.SLOT_SIZE + 6)
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def _equip_slot_rect(self, slot, modal):
        idx = SLOTS.index(slot)
        x = modal.x + 24 + idx * (self.SLOT_SIZE + 6)
        y = modal.y + 80 + 4 * (self.SLOT_SIZE + 6) + 24
        return pygame.Rect(x, y, self.SLOT_SIZE, self.SLOT_SIZE)

    def _action_rects(self, modal):
        bx = modal.x + 24 + self.GRID_COLS * (self.SLOT_SIZE + 6) + 30
        by = modal.y + 80
        return {
            'upgrade': pygame.Rect(bx, by, 200, 40),
            'reroll':  pygame.Rect(bx, by + 44, 200, 40),
            'enchant': pygame.Rect(bx, by + 88, 200, 40),
            'salvage': pygame.Rect(bx, by + 132, 200, 40),
        }

    def _gem_rects(self, modal, player):
        # Update #70: Action-Buttons enden bei modal.y + 80+132+40 = y+252.
        # Vorher waren Gems bei y+200 → kollidierten mit Verzaubern/Salvage.
        # Fix: Gems-Grid auf y+280 verschoben (28 px gap nach Salvage).
        bx = modal.x + 24 + self.GRID_COLS * (self.SLOT_SIZE + 6) + 30
        by = modal.y + 280
        rects = []
        for i, gem in enumerate(player.gems[:40]):
            col = i % 8
            row = i // 8
            rects.append((
                pygame.Rect(bx + col * 26, by + row * 26, 22, 22),
                gem, i,
            ))
        return rects

    # -------- Selection / Item-Zugriff --------
    def _selected_item(self, player):
        if not self.selected:
            return None
        kind, key = self.selected
        if kind == 'inv':
            if 0 <= key < len(player.inventory):
                return player.inventory[key]
        elif kind == 'equip':
            return player.equipment.get(key)
        return None

    # -------- Input --------
    def handle_click(self, game, mx, my):
        modal = self.modal_rect()
        if not modal.collidepoint(mx, my):
            return False
        p = game.player

        # Item-Auswahl: Inventar
        for i in range(len(p.inventory)):
            if self._inv_slot_rect(i, modal).collidepoint(mx, my):
                if p.inventory[i] is not None:
                    self.selected = ('inv', i)
                return True
        # Item-Auswahl: Ausrüstung
        for slot in SLOTS:
            if self._equip_slot_rect(slot, modal).collidepoint(mx, my):
                if p.equipment.get(slot) is not None:
                    self.selected = ('equip', slot)
                return True

        item = self._selected_item(p)
        actions = self._action_rects(modal)
        if item is not None:
            if actions['upgrade'].collidepoint(mx, my):
                if upgrade_item(p, item) and hasattr(game, '_check_achievements'):
                    from . import achievements as ach
                    ach.on_upgrade(game)
                    game._check_achievements()
                return True
            if actions['reroll'].collidepoint(mx, my):
                reroll_item(p, item)
                return True
            if actions['enchant'].collidepoint(mx, my):
                enchant_item(p, item)
                return True
            if actions['salvage'].collidepoint(mx, my):
                result = salvage_item(p, item)
                # Item entfernen
                kind, key = self.selected
                if kind == 'inv':
                    p.inventory[key] = None
                else:
                    p.equipment[key] = None
                self.selected = None
                return True
            # Gem-Klick (Sockel setzen)
            for rect, gem, idx in self._gem_rects(modal, p):
                if rect.collidepoint(mx, my):
                    if socket_gem(p, item, gem) and hasattr(game, '_check_achievements'):
                        from . import achievements as ach
                        ach.on_socket(game)
                        game._check_achievements()
                    return True

        return True  # innerhalb Modal — Klick verbraucht

    # -------- Render --------
    def draw(self, screen, game):
        import math
        p = game.player
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 200))
        screen.blit(overlay, (0, 0))

        modal = self.modal_rect()
        # --- Schmiede-Themed Background ---
        bg = pygame.Surface((modal.w, modal.h), pygame.SRCALPHA)
        bg.fill((42, 32, 22, 245))
        screen.blit(bg, modal.topleft)
        # Innenraum-Rahmen
        inner = pygame.Rect(modal.x + 14, modal.y + 14, modal.w - 28, modal.h - 28)
        pygame.draw.rect(screen, (24, 18, 12), inner)
        pygame.draw.rect(screen, (90, 70, 50), inner, 2)
        # Stein-Mauerwerk-Linien oben
        for k in range(int(modal.w / 100)):
            x = modal.x + 20 + k * 100
            pygame.draw.rect(screen, (70, 56, 38), (x, modal.y + 4, 90, 8), 1)
            pygame.draw.rect(screen, (60, 46, 30), (x + 45, modal.y + 12, 90, 8), 1)
        # Schmiede-Glüh-Effekt unten (Esse)
        glow_pulse = abs(math.sin(pygame.time.get_ticks() * 0.003))
        for k in range(60):
            t = k / 60
            alpha = int((1 - t) * 100 * (0.6 + 0.4 * glow_pulse))
            pygame.draw.rect(screen, (255, 120, 40, alpha),
                              (modal.x + 14, modal.y + modal.h - 14 - k,
                               modal.w - 28, 1))
        # Amboss + Hammer dekorativ oben links
        ax = modal.x + 28
        ay = modal.y + 38
        pygame.draw.polygon(screen, (80, 80, 80), [
            (ax, ay), (ax + 32, ay), (ax + 28, ay + 12), (ax + 4, ay + 12),
        ])
        pygame.draw.polygon(screen, BLACK, [
            (ax, ay), (ax + 32, ay), (ax + 28, ay + 12), (ax + 4, ay + 12),
        ], 1)
        pygame.draw.rect(screen, (60, 60, 60), (ax + 10, ay + 12, 14, 10))
        # Hammer
        pygame.draw.line(screen, (90, 60, 30), (ax + 12, ay - 8), (ax + 28, ay), 4)
        pygame.draw.rect(screen, (140, 100, 50), (ax + 4, ay - 12, 16, 6))
        # Funken um Amboss
        for k in range(5):
            angle = k * (math.pi * 2 / 5) + pygame.time.get_ticks() * 0.001
            sx_f = ax + 16 + int(math.cos(angle) * (12 + glow_pulse * 4))
            sy_f = ay + 6 + int(math.sin(angle) * (8 + glow_pulse * 2))
            pygame.draw.circle(screen, (255, 200, 80), (sx_f, sy_f), 1)
        # Messing-Eckbeschläge
        for cx, cy in [(modal.x + 6, modal.y + 6),
                       (modal.x + modal.w - 22, modal.y + 6),
                       (modal.x + 6, modal.y + modal.h - 22),
                       (modal.x + modal.w - 22, modal.y + modal.h - 22)]:
            pygame.draw.rect(screen, (160, 120, 60), (cx, cy, 16, 16))
            pygame.draw.rect(screen, BLACK, (cx, cy, 16, 16), 2)
            pygame.draw.circle(screen, BLACK, (cx + 8, cy + 8), 2)

        title = self.font_med.render('SCHMIEDE', True, (255, 200, 100))
        screen.blit(title, (modal.x + 72, modal.y + 36))
        gold_text = self.font_small.render(
            f'Gold: {p.gold}   ·   C: Schließen', True, GOLD_BRIGHT)
        screen.blit(gold_text, (modal.x + modal.w - gold_text.get_width() - 24,
                                modal.y + 42))

        # Inventar
        lbl = self.font_small.render('INVENTAR', True, TEXT_DIM)
        screen.blit(lbl, (modal.x + 24, modal.y + 60))
        for i, item in enumerate(p.inventory):
            r = self._inv_slot_rect(i, modal)
            sel = (self.selected == ('inv', i))
            self._draw_slot(screen, r, item, selected=sel)

        # Ausrüstung
        lbl = self.font_small.render('AUSGERÜSTET', True, TEXT_DIM)
        first_eq = self._equip_slot_rect(SLOTS[0], modal)
        screen.blit(lbl, (modal.x + 24, first_eq.y - 18))
        for slot in SLOTS:
            r = self._equip_slot_rect(slot, modal)
            sel = (self.selected == ('equip', slot))
            self._draw_slot(screen, r, p.equipment.get(slot), label=SLOT_NAME[slot][:3], selected=sel)

        # Aktionen
        item = self._selected_item(p)
        actions = self._action_rects(modal)
        self._draw_action(screen, actions['upgrade'], 'Aufwerten',
                          upgrade_cost(item) if item else None,
                          can_upgrade(p, item) if item else False,
                          item is not None)
        self._draw_action(screen, actions['reroll'], 'Umrollen',
                          reroll_cost(item) if item else None,
                          can_reroll(p, item) if item else False,
                          item is not None and item.rarity != 'common')
        self._draw_action(screen, actions['enchant'], 'Verzaubern',
                          enchant_cost(item) if item else None,
                          can_enchant(p, item) if item else False,
                          item is not None)
        self._draw_action(screen, actions['salvage'], 'Salvage',
                          salvage_value(item) if item else None,
                          item is not None, item is not None,
                          gain=True)

        # Gem-Bereich UNTER den Action-Buttons (nicht überlappend)
        # Update #58: Label-Y synchron mit `_gem_rects` (by=200 → Label by=178)
        gem_x = modal.x + 24 + self.GRID_COLS * (self.SLOT_SIZE + 6) + 30
        # Update #70: Label-Y synchron mit `_gem_rects` (by=280 → Label by=258)
        gem_y = modal.y + 258
        gem_count = len(p.gems)
        lbl_text = f'EDELSTEINE ({gem_count}) — Sockel: {socket_cost()}g'
        lbl = self.font_small.render(lbl_text, True, TEXT_DIM)
        screen.blit(lbl, (gem_x, gem_y))
        for rect, gem, idx in self._gem_rects(modal, p):
            gd = GEM_TYPES[gem]
            pygame.draw.rect(screen, (26, 22, 18), rect)
            pygame.draw.rect(screen, gd['color'], rect, 2)
            pts = [
                (rect.centerx, rect.y + 4),
                (rect.right - 4, rect.centery),
                (rect.centerx, rect.bottom - 4),
                (rect.x + 4, rect.centery),
            ]
            pygame.draw.polygon(screen, gd['color'], pts)
            pygame.draw.polygon(screen, WHITE, pts, 1)

        # Item-Info
        if item is not None:
            self._draw_item_details(screen, item, modal)

        # Tooltip für gehoverten Gem
        mx, my = pygame.mouse.get_pos()
        for rect, gem, idx in self._gem_rects(modal, p):
            if rect.collidepoint(mx, my):
                gd = GEM_TYPES[gem]
                tt = self.font_small.render(f'{gd["name"]}: {gd["desc"]}',
                                            True, gd['color'])
                bg_tt = pygame.Surface((tt.get_width() + 12, tt.get_height() + 6),
                                       pygame.SRCALPHA)
                bg_tt.fill((10, 8, 6, 240))
                screen.blit(bg_tt, (mx + 12, my + 8))
                pygame.draw.rect(screen, GOLD,
                                 (mx + 12, my + 8, tt.get_width() + 12, tt.get_height() + 6), 1)
                screen.blit(tt, (mx + 18, my + 11))
                break
        # Update #90: Action-Button-Hover-Tooltip (Aufwerten/Umrollen/etc.)
        self._draw_action_tooltips(screen, modal, item, mx, my)

    _ACTION_LORE = {
        'upgrade': (
            'Aufwerten',
            'Erhöht die Item-Stufe um +1 (max 20). Affixe rollen leicht stärker.',
            'Otreth Hohlauge: „Der Stein lernt schneller, wenn man ihn schlägt."',
        ),
        'reroll':  (
            'Umrollen',
            'Würfelt ALLE Affixe neu — gleiche Rarity bleibt. Sockel + Edelsteine bleiben.',
            'Korven Vor: „Würfle die Erinnerung. Vielleicht stimmt sie diesmal."',
        ),
        'enchant': (
            'Verzaubern',
            'Fügt einen neuen Affix hinzu (bis zum Slot-Max). Erhöht Rarity nicht.',
            'Mara: „Ein Wort dazu. Nur eins. Mehr trägt es nicht."',
        ),
        'salvage': (
            'Salvage',
            'Zerlegt das Item in Gold. Sockel + Gems werden in den Bestand zurückgegeben.',
            'Tameris: „Was nicht erinnert wird, gibt zumindest Kupfer."',
        ),
    }

    def _draw_action_tooltips(self, screen, modal, item, mx, my):
        actions = self._action_rects(modal)
        for key, rect in actions.items():
            if not rect.collidepoint(mx, my):
                continue
            spec = self._ACTION_LORE.get(key)
            if spec is None:
                return
            title, desc, lore = spec
            # Box mit Title (gold), Desc (white), Lore (italic-dim)
            t_surf = self.font_med.render(title, True, GOLD_BRIGHT)
            d_surf = self.font_small.render(desc, True, (220, 210, 190))
            l_surf = self.font_small.render(lore, True, (180, 160, 130))
            w = max(t_surf.get_width(), d_surf.get_width(),
                     l_surf.get_width()) + 24
            h = (t_surf.get_height() + d_surf.get_height()
                  + l_surf.get_height() + 24)
            tx = rect.right + 8
            ty = rect.y
            if tx + w > modal.right - 8:
                tx = rect.left - w - 8
            bg = pygame.Surface((w, h), pygame.SRCALPHA)
            bg.fill((14, 10, 8, 245))
            screen.blit(bg, (tx, ty))
            pygame.draw.rect(screen, GOLD, (tx, ty, w, h), 2)
            screen.blit(t_surf, (tx + 12, ty + 8))
            screen.blit(d_surf, (tx + 12, ty + 10 + t_surf.get_height()))
            screen.blit(l_surf,
                         (tx + 12,
                          ty + 12 + t_surf.get_height() + d_surf.get_height()))
            return

    def _draw_slot(self, screen, r, item, label=None, selected=False):
        pygame.draw.rect(screen, (32, 26, 20), r)
        pygame.draw.rect(screen, GOLD_BRIGHT if selected else (60, 48, 32),
                         r, 2 if selected else 1)
        if label and item is None:
            ls = self.font_small.render(label, True, TEXT_DIM)
            screen.blit(ls, (r.x + r.w // 2 - ls.get_width() // 2,
                             r.y + r.h // 2 - ls.get_height() // 2))
        if item is not None:
            color = RARITY_COLOR[item.rarity]
            pygame.draw.rect(screen, color, r, 2)
            from . import sprites as sp
            sp.draw_item_icon(screen, item, r)
            # Sockel-Indikatoren
            for k, s in enumerate(item.sockets):
                ix = r.x + 3 + k * 8
                iy = r.bottom - 8
                pygame.draw.circle(screen, (60, 50, 40), (ix, iy), 3)
                if s:
                    pygame.draw.circle(screen, GEM_TYPES[s]['color'], (ix, iy), 2)

    def _draw_action(self, screen, rect, label, cost, can_do, active, gain=False):
        col_bg = (40, 32, 18) if can_do and active else (30, 24, 18)
        col_border = GOLD if can_do and active else (60, 50, 40)
        bg = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        bg.fill((*col_bg, 240))
        screen.blit(bg, rect.topleft)
        pygame.draw.rect(screen, col_border, rect, 2)
        ls = self.font_med.render(label, True, GOLD_BRIGHT if can_do and active else TEXT_DIM)
        screen.blit(ls, (rect.x + 12, rect.y + 4))
        if cost is not None:
            prefix = '+' if gain else ''
            color = (140, 220, 140) if gain else (GOLD_BRIGHT if can_do else (160, 80, 80))
            cs = self.font_small.render(f'{prefix}{cost} Gold', True, color)
            screen.blit(cs, (rect.x + 12, rect.y + 26))

    def _draw_item_details(self, screen, item, modal):
        y = modal.y + modal.h - 110
        x = modal.x + 24
        w = modal.w - 48

        bg = pygame.Surface((w, 96), pygame.SRCALPHA)
        bg.fill((10, 8, 6, 240))
        screen.blit(bg, (x, y))
        pygame.draw.rect(screen, RARITY_COLOR[item.rarity], (x, y, w, 96), 1)

        name = self.font_med.render(item.name, True, RARITY_COLOR[item.rarity])
        screen.blit(name, (x + 12, y + 8))
        sub = self.font_small.render(
            f'{SLOT_NAME[item.slot]} · Stufe {item.ilvl}', True, TEXT_DIM)
        screen.blit(sub, (x + 12, y + 32))

        afy = y + 52
        for k, v in item.affixes:
            label, *_ = AFFIXES[k]
            if k in FLOAT_AFFIXES:
                text = label.format(v=v)
            else:
                text = label.format(v=int(v))
            afx = self.font_small.render(text, True, (170, 200, 255))
            screen.blit(afx, (x + 16, afy))
            afy += 14
            if afy > y + 90:
                break
