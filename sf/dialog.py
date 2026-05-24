"""NPC-Dialog-Modal mit Portrait + Choice-Buttons (ROADMAP T1.3).

Macht NPC-Voice-Lines erst spielbar: bisher wurden Lines nur als Toast
gespielt.  Ab jetzt: links Portrait (256x256 Placeholder bis T-07 echte
PNGs hat), rechts Text mit Wort-für-Wort Reveal alle 35 ms, unten bis
zu 4 Choice-Buttons.

Architektur:
  - `DialogTree(npc_key, nodes)` — Daten-Struktur: dict node_id → {
        text: str,
        portrait: optional str,
        choices: [{label, next, action}],
        on_show: optional callable(game),
    }
  - `DialogUI` — State + Render + Input.
  - Game wired via `game.modal = 'dialog'` + `game.dialog_ui.open(tree, start)`.

Lore-Anker: VELGRAD_VOICE_LINES_POOL.md (NPC-spezifische Tonalität).
"""

import math
import pygame

from .constants import SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM


REVEAL_MS_PER_WORD = 35
PORTRAIT_PX = 256
MAX_CHOICES = 4


class DialogTree:
    """Container fuer einen NPC-Konversations-Tree.

    Beispiel:
        tree = DialogTree('korven', {
            'start': {
                'text': 'Schoen, dass du noch atmest.',
                'choices': [
                    {'label': 'Was ist passiert?', 'next': 'lore'},
                    {'label': 'Auf Wiedersehen', 'next': None},
                ],
            },
            'lore': {
                'text': 'Brassweir bricht. Die Salzwunde frisst nach Norden.',
                'choices': [
                    {'label': 'Zurueck', 'next': 'start'},
                ],
            },
        })
    """
    __slots__ = ('npc_key', 'nodes')

    def __init__(self, npc_key, nodes):
        self.npc_key = npc_key
        self.nodes = nodes

    def get(self, node_id):
        return self.nodes.get(node_id)


def _voice_line_quote(text, voice_id=None):
    """Wraps a quote with leading/trailing quotation marks."""
    return f'„{text}"' if not text.startswith('„') else text


class DialogUI:
    """Modal-Renderer fuer NPC-Dialoge.

    Lifecycle:
      - `open(game, tree, start='start', npc_obj=None)` setzt State.
      - `update(dt)` advanced den Word-Reveal-Counter.
      - `draw(screen, ...)` rendert das Modal.
      - `handle_click(mx, my, game)` -> True wenn Click gefangen wurde.
      - `handle_key(key, game)` -> True wenn Key gefangen wurde.
    """

    def __init__(self, font_med, font_small, font_big=None):
        self.font_med = font_med
        self.font_small = font_small
        self.font_big = font_big or font_med
        self.tree = None
        self.node_id = None
        self.npc_obj = None
        self.npc_name = ''
        self.reveal_t = 0.0
        self.full_text = ''
        self.choice_rects = []
        self.skip_rect = None
        self.close_rect = None
        # Portrait-Cache pro npc_key (256x256 Placeholder mit Initial).
        self._portrait_cache = {}

    # ----- Lifecycle -----
    def open(self, game, tree, start_id='start', npc_obj=None):
        self.tree = tree
        self.npc_obj = npc_obj
        self.npc_name = getattr(npc_obj, 'name', tree.npc_key.title()) if npc_obj else tree.npc_key.title()
        self._enter_node(game, start_id)
        try:
            game.modal = 'dialog'
        except Exception:
            pass

    def close(self, game):
        self.tree = None
        self.node_id = None
        self.npc_obj = None
        self.full_text = ''
        self.reveal_t = 0.0
        self.choice_rects = []
        try:
            if getattr(game, 'modal', None) == 'dialog':
                game.modal = None
        except Exception:
            pass

    def _enter_node(self, game, node_id):
        if self.tree is None:
            return
        node = self.tree.get(node_id)
        if node is None:
            self.close(game)
            return
        self.node_id = node_id
        self.full_text = node.get('text', '')
        self.reveal_t = 0.0
        # on_show-Callback (z.B. Voice-Sound triggern, Quest-Flag setzen)
        cb = node.get('on_show')
        if callable(cb):
            try:
                cb(game)
            except Exception:
                pass
        # NPC-Voice-Line (T1.3-B): Wenn Node ein voice_key spezifiziert,
        # spiele die zugehoerige AI-Voice.
        voice_key = node.get('voice')
        if voice_key:
            try:
                from . import sounds as _snd
                _snd.play_voice(self.tree.npc_key, voice_key, volume=0.8)
            except Exception:
                pass

    # ----- Update -----
    def update(self, dt):
        if self.tree is None:
            return
        # Word-Reveal voranbringen — 1 Wort alle REVEAL_MS_PER_WORD ms.
        self.reveal_t += dt

    @property
    def _words_revealed(self):
        if not self.full_text:
            return []
        words = self.full_text.split()
        n_words = int(self.reveal_t * 1000.0 / REVEAL_MS_PER_WORD)
        n_words = max(0, min(n_words, len(words)))
        return words[:n_words]

    @property
    def _is_fully_revealed(self):
        return len(self._words_revealed) >= len(self.full_text.split())

    # ----- Input -----
    def handle_click(self, mx, my, game):
        if self.tree is None:
            return False
        # Skip-Reveal: noch nicht fertig -> erst Click fuellt Text auf.
        if not self._is_fully_revealed:
            self.reveal_t = 9999.0
            return True
        # Choice-Buttons?
        node = self.tree.get(self.node_id)
        choices = node.get('choices', []) if node else []
        for rect, ch in self.choice_rects:
            if rect.collidepoint(mx, my):
                self._do_choice(game, ch)
                return True
        # Close-Button (X oder ESC-Hint)?
        if self.close_rect and self.close_rect.collidepoint(mx, my):
            self.close(game)
            return True
        return True   # Click frisst alle Klicks im Modal-Bereich

    def handle_key(self, key, game):
        if self.tree is None:
            return False
        # ESC -> close
        if key == pygame.K_ESCAPE:
            self.close(game)
            return True
        # SPACE / ENTER -> skip reveal oder erste Choice
        if key in (pygame.K_SPACE, pygame.K_RETURN):
            if not self._is_fully_revealed:
                self.reveal_t = 9999.0
                return True
            node = self.tree.get(self.node_id)
            choices = node.get('choices', []) if node else []
            if choices:
                self._do_choice(game, choices[0])
                return True
        # 1..4 -> direkt waehlen
        if pygame.K_1 <= key <= pygame.K_4:
            idx = key - pygame.K_1
            node = self.tree.get(self.node_id)
            choices = node.get('choices', []) if node else []
            if idx < len(choices) and self._is_fully_revealed:
                self._do_choice(game, choices[idx])
                return True
        return True   # Alle Keys im Modal abfangen

    def _do_choice(self, game, choice):
        """Apply choice-action + transition."""
        action = choice.get('action')
        if callable(action):
            try:
                action(game)
            except Exception:
                pass
        # Quest-Choice-Hook: wenn die aktuelle Stage CHOICE ist, schreiten
        # wir die Stage via on_choice voran.
        flag_set = choice.get('set_flag')
        if flag_set:
            flag, value = flag_set
            try:
                from . import quests as _q
                _q.on_choice(game, flag, value)
            except Exception:
                # Fallback: direkt in game.flags
                if not hasattr(game, 'flags'):
                    game.flags = {}
                game.flags[flag] = value
        nxt = choice.get('next')
        if nxt is None:
            self.close(game)
        else:
            self._enter_node(game, nxt)

    # ----- Render -----
    def _portrait(self, npc_key, color):
        """Returnt eine 256x256-Portrait-Surface.

        Sucht erst nach `assets/portraits/<npc_key>.png` (T-07).
        Fallback: stilisiertes Pergament-Placeholder mit Initialen.
        """
        if npc_key in self._portrait_cache:
            return self._portrait_cache[npc_key]
        # Try loading PNG portrait
        surf = None
        try:
            import os
            path = os.path.join('assets', 'portraits', f'{npc_key}.png')
            if os.path.isfile(path):
                surf = pygame.image.load(path).convert_alpha()
                if surf.get_width() != PORTRAIT_PX:
                    surf = pygame.transform.smoothscale(
                        surf, (PORTRAIT_PX, PORTRAIT_PX))
        except Exception:
            surf = None
        if surf is None:
            surf = self._make_placeholder_portrait(npc_key, color)
        self._portrait_cache[npc_key] = surf
        return surf

    def _make_placeholder_portrait(self, npc_key, color):
        """Procedural-Pergament-Placeholder mit grossem Buchstaben + Aura."""
        surf = pygame.Surface((PORTRAIT_PX, PORTRAIT_PX), pygame.SRCALPHA)
        # Pergament-BG
        pygame.draw.rect(surf, (32, 22, 16, 255),
                         (0, 0, PORTRAIT_PX, PORTRAIT_PX))
        # Radial-Vignette
        for i in range(20):
            t = i / 20.0
            r = int(PORTRAIT_PX * 0.55 - t * 30)
            a = int(60 * (1 - t))
            pygame.draw.circle(surf, (*color, a),
                               (PORTRAIT_PX // 2, PORTRAIT_PX // 2 - 20), r)
        # Border (Lore-Akzent)
        pygame.draw.rect(surf, color,
                         (0, 0, PORTRAIT_PX, PORTRAIT_PX), 3)
        # Innen-Frame (Goldfaden)
        pygame.draw.rect(surf, GOLD,
                         (6, 6, PORTRAIT_PX - 12, PORTRAIT_PX - 12), 1)
        # Initial — gross + zentriert
        try:
            big = pygame.font.SysFont('georgia,times', 140, bold=True)
            initial = npc_key[:1].upper() if npc_key else '?'
            txt = big.render(initial, True, (220, 200, 160))
            surf.blit(txt, txt.get_rect(center=(PORTRAIT_PX // 2,
                                                PORTRAIT_PX // 2)))
        except Exception:
            pass
        return surf

    def draw(self, screen, game):
        if self.tree is None:
            return
        node = self.tree.get(self.node_id)
        if node is None:
            return
        # Modal-Background (semi-opak)
        veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        screen.blit(veil, (0, 0))

        # Modal-Box
        mw = 1080
        mh = 420
        mx = (SCREEN_W - mw) // 2
        my = (SCREEN_H - mh) // 2 + 80
        box = pygame.Surface((mw, mh), pygame.SRCALPHA)
        # Pergament-Hintergrund
        for i in range(mh):
            t = i / mh
            r = int(38 - t * 8)
            g = int(28 - t * 5)
            b = int(20 - t * 3)
            pygame.draw.line(box, (r, g, b, 235), (0, i), (mw, i))
        # Goldener Frame
        pygame.draw.rect(box, GOLD, (0, 0, mw, mh), 2)
        pygame.draw.rect(box, (120, 90, 50), (4, 4, mw - 8, mh - 8), 1)
        screen.blit(box, (mx, my))

        # Portrait — links
        npc_color = getattr(self.npc_obj, 'color', GOLD) if self.npc_obj else GOLD
        portrait = self._portrait(self.tree.npc_key, npc_color)
        px = mx + 26
        py = my + 26
        screen.blit(portrait, (px, py))
        # NPC-Name unter Portrait
        name_surf = self.font_med.render(self.npc_name, True, GOLD_BRIGHT)
        screen.blit(name_surf, (px + (PORTRAIT_PX - name_surf.get_width()) // 2,
                                py + PORTRAIT_PX + 10))

        # Text-Bereich rechts
        tx = px + PORTRAIT_PX + 32
        ty = my + 30
        tw = mx + mw - tx - 26
        # Reveal-Text: gewordene Woerter
        revealed_words = self._words_revealed
        # Soft-Wrap
        lines = self._wrap_words(revealed_words, tw)
        for line in lines:
            surf = self.font_med.render(line, True, TEXT)
            screen.blit(surf, (tx, ty))
            ty += surf.get_height() + 4

        # Cursor wenn nicht fertig: kleiner Caret blinkend
        if not self._is_fully_revealed:
            blink = (pygame.time.get_ticks() // 250) % 2
            if blink:
                pygame.draw.rect(screen, GOLD_BRIGHT,
                                 (tx + 4, ty + 4, 10, 4))

        # Choices unten — nur wenn fully revealed
        self.choice_rects = []
        if self._is_fully_revealed:
            choices = node.get('choices', [])[:MAX_CHOICES]
            cy = my + mh - 30 - len(choices) * 38
            for i, ch in enumerate(choices):
                label = ch.get('label', '...')
                hotkey = f'[{i + 1}] '
                full = f'{hotkey}{label}'
                # Hover-Highlight
                cx = tx
                cw = tw
                ch_rect = pygame.Rect(cx, cy, cw, 32)
                mx_m, my_m = pygame.mouse.get_pos()
                hover = ch_rect.collidepoint(mx_m, my_m)
                bg_col = (60, 44, 28, 200) if hover else (40, 30, 22, 180)
                bg_surf = pygame.Surface((cw, 32), pygame.SRCALPHA)
                bg_surf.fill(bg_col)
                screen.blit(bg_surf, (cx, cy))
                border_col = GOLD_BRIGHT if hover else (120, 90, 50)
                pygame.draw.rect(screen, border_col, ch_rect, 1)
                ts = self.font_small.render(full, True,
                                             GOLD_BRIGHT if hover else TEXT)
                screen.blit(ts, (cx + 12, cy + 7))
                self.choice_rects.append((ch_rect, ch))
                cy += 38
        else:
            # Hint: „Klick = Skip"
            hint = self.font_small.render(
                'Klick / SPACE — Text ueberspringen',
                True, TEXT_DIM)
            screen.blit(hint, (tx, my + mh - 28))

        # ESC-Hint oben rechts
        esc_text = self.font_small.render(
            '[ESC] schliessen', True, TEXT_DIM)
        esc_rect = esc_text.get_rect(
            topright=(mx + mw - 14, my + 10))
        screen.blit(esc_text, esc_rect)
        self.close_rect = esc_rect.inflate(20, 8)

    def _wrap_words(self, words, max_width):
        """Wrap words to fit in max_width pixels using font_med."""
        lines = []
        cur = []
        cur_w = 0
        space_w = self.font_med.size(' ')[0]
        for w in words:
            ww = self.font_med.size(w)[0]
            if cur and cur_w + space_w + ww > max_width:
                lines.append(' '.join(cur))
                cur = [w]
                cur_w = ww
            else:
                cur.append(w)
                cur_w += (space_w if cur_w > 0 else 0) + ww
        if cur:
            lines.append(' '.join(cur))
        return lines


# ============================================================
# DIALOG-TREE FACTORY (T1.3-D)
# ============================================================

def build_default_tree_for_npc(npc_key, npc_obj=None):
    """Returnt einen Default-Dialog-Tree fuer einen NPC.

    Fuer Quest-NPCs: zeigt Quest-Status + Options.
    Fuer Voice-Line-NPCs: zeigt Voice-Lines mit Choice-Buttons.

    Lore-Quelle: VELGRAD_VOICE_LINES_POOL.md.  Wenn der NPC ein
    `roster_key` hat (Outposts), verwenden wir die ersten 4 Voice-Lines
    aus dem Roster.
    """
    nodes = {}
    voice_lines = []
    # Roster-NPC?
    roster_key = getattr(npc_obj, 'roster_key', None) if npc_obj else None
    if roster_key:
        try:
            from . import outposts as _op
            spec = _op.NPC_ROSTER.get(roster_key)
            if spec:
                voice_lines = list(spec.get('voice_lines', ()))[:4]
        except Exception:
            voice_lines = []
    # Brassweir-NPCs (Hard-Coded-Pool)
    if not voice_lines and npc_obj is not None:
        BRASS = {
            'Korven Vor': [
                'Schoen, dass du noch atmest. Setz dich.',
                'Brassweir braucht keine Helden, nur Handler. '
                'Findest du das einen?',
            ],
            'Mara die Mahnerin': [
                'Ich erinnere mich an dich. Auch wenn wir uns nie sahen.',
                'Die Vergessens-Welle hat ein Lied. Hoere zu.',
            ],
            'Otreth Hohlauge': [
                'Bring mir Steine. Bring sie sauber. Bring sie ungelesen.',
                'Jeder Gemstein ist ein Versprechen. Halte deins.',
            ],
            'Tameris': [
                'Der Verbannte. Setz dich an mein Feuer.',
                'Mein Schwester ist verschwunden. Aber sie ist nicht tot.',
            ],
            'Stadtsprecher Eldon': [
                'Das Brett aktualisiert sich selbst. Lies und handle.',
                'Tribunal-Patrouille gesichtet. Vorsicht im Osten.',
            ],
        }
        voice_lines = BRASS.get(getattr(npc_obj, 'name', ''), [])
    if not voice_lines:
        voice_lines = [f'(Stille von {getattr(npc_obj, "name", npc_key)})']
    # Build a simple tree: each line = own node + „weiter"-choice.
    for i, line in enumerate(voice_lines):
        nid = 'start' if i == 0 else f'line_{i}'
        next_id = f'line_{i + 1}' if i + 1 < len(voice_lines) else None
        if next_id is None:
            choices = [
                {'label': 'Auf Wiedersehen', 'next': None},
            ]
        else:
            choices = [
                {'label': 'Weiter', 'next': next_id},
                {'label': 'Auf Wiedersehen', 'next': None},
            ]
        nodes[nid] = {
            'text': line,
            'choices': choices,
        }
    return DialogTree(npc_key or 'npc', nodes)
