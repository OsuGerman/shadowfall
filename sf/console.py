"""Debug-Console (PLAN AA-02).

`~`-Taste oeffnet ein Modal, in dem Slash-Commands an die Engine
geschickt werden koennen.  Wird ueber `Game.console`-Attribut wired.

Commands:
  /spawn <mob>         — Spawn a bestiary mob at cursor
  /give <item>         — Give a base-item by name
  /level <n>            — Set player level to n
  /tp <x> <y>           — Teleport player to world-pos
  /god                  — Toggle god-mode (invincibility)
  /noclip               — Toggle decor collision
  /seed <n>             — Set dungeon-gen seed for next entry
  /gold <n>             — Set/add gold
  /xp <n>               — Grant xp
  /heal                 — Refill HP/MP/Flask
  /killall              — Kill all enemies
  /reload_skills        — Reload skill registry
  /flag <name> <value>  — Set quest-flag
  /quest <id>           — Offer quest
  /cutscene <key>       — Play cutscene by key
  /clear                — Clear console history

Nur in Debug-Build aktiv (Setting `dev_console`).
"""

import pygame

from .constants import SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT, TEXT_DIM


class DebugConsole:
    def __init__(self, font_med, font_small):
        self.font_med = font_med
        self.font_small = font_small
        self.open = False
        self.input_buf = ''
        self.history = []   # list of (text, color)
        self.cmd_history = []
        self.cmd_hist_idx = -1
        self.god_mode = False
        self.noclip = False
        self.next_seed = None

    def toggle(self):
        self.open = not self.open
        if self.open:
            self.input_buf = ''

    def handle_key(self, ev, game):
        if not self.open:
            return False
        if ev.key == pygame.K_RETURN:
            line = self.input_buf.strip()
            if line:
                self.cmd_history.append(line)
                self.cmd_hist_idx = len(self.cmd_history)
                self._execute(line, game)
            self.input_buf = ''
            return True
        if ev.key == pygame.K_BACKSPACE:
            self.input_buf = self.input_buf[:-1]
            return True
        if ev.key == pygame.K_ESCAPE:
            self.open = False
            return True
        if ev.key == pygame.K_UP:
            if self.cmd_history:
                self.cmd_hist_idx = max(0, self.cmd_hist_idx - 1)
                self.input_buf = self.cmd_history[self.cmd_hist_idx]
            return True
        if ev.key == pygame.K_DOWN:
            if self.cmd_history:
                self.cmd_hist_idx = min(len(self.cmd_history) - 1,
                                          self.cmd_hist_idx + 1)
                self.input_buf = self.cmd_history[self.cmd_hist_idx]
            return True
        # Printable char via .unicode
        ch = ev.unicode
        if ch and (ch.isprintable() and ch != '`'):
            if len(self.input_buf) < 80:
                self.input_buf += ch
            return True
        return True

    def _log(self, text, color=(220, 220, 220)):
        self.history.append((text, color))
        if len(self.history) > 30:
            self.history.pop(0)

    def _execute(self, line, game):
        if not line.startswith('/'):
            line = '/' + line
        parts = line[1:].split()
        if not parts:
            return
        cmd = parts[0].lower()
        args = parts[1:]
        self._log(f'> {line}', (180, 220, 255))
        try:
            getattr(self, f'_cmd_{cmd}',
                    self._cmd_unknown)(args, game)
        except Exception as e:
            self._log(f'  error: {e}', (220, 100, 80))

    def _cmd_unknown(self, args, game):
        self._log(f'  unknown command. /help for list.', (220, 180, 80))

    def _cmd_help(self, args, game):
        self._log('  /spawn /give /level /tp /god /noclip /seed', GOLD)
        self._log('  /gold /xp /heal /killall /flag /quest /cutscene',
                  GOLD)

    def _cmd_god(self, args, game):
        self.god_mode = not self.god_mode
        game.player.invuln = 9999.0 if self.god_mode else 0.0
        self._log(f'  god-mode: {self.god_mode}', GOLD_BRIGHT)

    def _cmd_noclip(self, args, game):
        self.noclip = not self.noclip
        self._log(f'  noclip: {self.noclip}', GOLD_BRIGHT)

    def _cmd_heal(self, args, game):
        from . import progression
        eff = progression.effective(game.player)
        game.player.hp = eff['hp_max']
        game.player.mp = eff['mp_max']
        try:
            game._refill_flasks()
        except Exception:
            pass
        self._log('  healed.', (140, 220, 140))

    def _cmd_level(self, args, game):
        if not args:
            self._log('  /level <n>', (220, 180, 80))
            return
        try:
            n = int(args[0])
            game.player.level = max(1, min(99, n))
            self._log(f'  level set to {n}', GOLD_BRIGHT)
        except ValueError:
            self._log('  /level expects integer', (220, 100, 80))

    def _cmd_gold(self, args, game):
        if not args:
            self._log(f'  gold: {game.player.gold}', GOLD)
            return
        try:
            n = int(args[0])
            game.player.gold += n
            self._log(f'  +{n} gold ({game.player.gold})', GOLD_BRIGHT)
        except ValueError:
            self._log('  /gold expects integer', (220, 100, 80))

    def _cmd_xp(self, args, game):
        if not args:
            return
        try:
            n = int(args[0])
            from . import progression
            progression.grant_xp(game.player, n)
            self._log(f'  +{n} xp', GOLD_BRIGHT)
        except (ValueError, Exception) as e:
            self._log(f'  err: {e}', (220, 100, 80))

    def _cmd_tp(self, args, game):
        if len(args) < 2:
            return
        from pygame.math import Vector2
        try:
            x = float(args[0])
            y = float(args[1])
            game.player.pos = Vector2(x, y)
            self._log(f'  tp to ({x}, {y})', GOLD_BRIGHT)
        except ValueError:
            self._log('  /tp expects floats', (220, 100, 80))

    def _cmd_killall(self, args, game):
        n = 0
        for e in list(game.enemies):
            if not e.is_boss:
                e.hp = 0
                n += 1
        try:
            from . import combat as _c
            for e in list(game.enemies):
                if e.hp <= 0 and not getattr(e, 'dying', False):
                    _c.kill_enemy(game, e)
        except Exception:
            pass
        self._log(f'  killed {n} mobs', (220, 140, 80))

    def _cmd_flag(self, args, game):
        if len(args) < 2:
            self._log('  /flag <name> <value>', (220, 180, 80))
            return
        if not hasattr(game, 'flags'):
            game.flags = {}
        game.flags[args[0]] = ' '.join(args[1:])
        self._log(f'  flag[{args[0]}] = {game.flags[args[0]]}',
                  GOLD_BRIGHT)

    def _cmd_quest(self, args, game):
        if not args:
            return
        qid = args[0]
        log = getattr(game, 'quest_log', None)
        if log is None:
            self._log('  no quest_log', (220, 100, 80))
            return
        st = log.offer(qid)
        if st:
            self._log(f'  quest offered: {qid}', GOLD_BRIGHT)
        else:
            self._log(f'  quest already active/done', (220, 180, 80))

    def _cmd_cutscene(self, args, game):
        if not args:
            return
        try:
            from . import cutscene as _cs
            ok = _cs.play_cutscene(game, args[0])
            self._log(f'  cutscene: {args[0]} -> {ok}', GOLD_BRIGHT)
        except Exception as e:
            self._log(f'  err: {e}', (220, 100, 80))

    def _cmd_seed(self, args, game):
        if not args:
            return
        try:
            self.next_seed = int(args[0])
            self._log(f'  next dungeon seed = {self.next_seed}',
                      GOLD_BRIGHT)
        except ValueError:
            pass

    def _cmd_give(self, args, game):
        if not args:
            return
        try:
            from . import items as _it
            it = _it.make_item(' '.join(args))
            if hasattr(game.player, 'inventory'):
                game.player.inventory.append(it)
                self._log(f'  +{it.name}', GOLD_BRIGHT)
        except Exception as e:
            self._log(f'  err: {e}', (220, 100, 80))

    def _cmd_spawn(self, args, game):
        if not args:
            return
        try:
            from . import bestiary as _b
            from pygame.math import Vector2
            mx, my = pygame.mouse.get_pos()
            wx, wy = game.s2w(mx, my)
            e = _b.spawn_bestiary_mob(args[0], wx, wy, game.player.level)
            if e is not None:
                game.enemies.append(e)
                self._log(f'  spawned {args[0]}', GOLD_BRIGHT)
        except Exception as e:
            self._log(f'  err: {e}', (220, 100, 80))

    def _cmd_clear(self, args, game):
        self.history = []

    def draw(self, screen):
        if not self.open:
            return
        h = 320
        veil = pygame.Surface((SCREEN_W, h), pygame.SRCALPHA)
        veil.fill((10, 10, 14, 220))
        screen.blit(veil, (0, 0))
        pygame.draw.line(screen, GOLD, (0, h), (SCREEN_W, h), 2)
        # Title
        title = self.font_med.render('DEBUG CONSOLE', True, GOLD_BRIGHT)
        screen.blit(title, (12, 8))
        # History
        y = 38
        for txt, col in self.history[-12:]:
            surf = self.font_small.render(txt, True, col)
            screen.blit(surf, (12, y))
            y += surf.get_height() + 2
        # Input
        prompt = self.font_small.render(
            '> ' + self.input_buf + '_', True, (240, 240, 255))
        screen.blit(prompt, (12, h - 28))
