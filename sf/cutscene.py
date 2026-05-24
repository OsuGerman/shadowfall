"""Cutscene-Mini-Framework (PLAN X-09 + ROADMAP T3.5).

Step-basierte Sequenzen die Voice-Lines, Camera-Bewegung, Portraits
und SFX orchestrieren.  Skipbar via SPACE (genauso wie Boss-Intro).

API:
    from sf.cutscene import Cutscene, CutscenePlayer

    scene = (Cutscene()
        .camera_move(target_x=0, target_y=-400, duration=0.6)
        .portrait_show('korven', 'Korven Vor')
        .text_show('Schoen, dass du atmest. Setz dich.', duration=2.4)
        .sfx('quest_marker_reach', volume=0.6)
        .wait(0.4)
        .portrait_hide()
        .text_show('Brassweir bricht. Drei Doerfer sind weg.', duration=3.0)
        .end())

    game.cutscene_player.play(scene)

`CutscenePlayer.update(dt)` advanced den State + ruft Callbacks.
`CutscenePlayer.draw(screen)` rendert Portrait + Lower-Third-Text.
"""

import math
import pygame

from .constants import SCREEN_W, SCREEN_H, GOLD, GOLD_BRIGHT, TEXT


# ============================================================
# STEP-TYPES
# ============================================================
class _Step:
    """Single cutscene step.  duration in seconds (0 = instant)."""
    __slots__ = ('kind', 'duration', 'data')

    def __init__(self, kind, duration=0.0, **data):
        self.kind = kind
        self.duration = float(duration)
        self.data = data


class Cutscene:
    """Builder fuer eine Sequenz von Steps."""

    def __init__(self, name='unnamed', skippable=True):
        self.name = name
        self.skippable = skippable
        self.steps = []

    def camera_move(self, target_x, target_y, duration=0.6):
        self.steps.append(_Step('camera_move', duration,
                                target_x=target_x, target_y=target_y))
        return self

    def hold(self, duration=1.0):
        self.steps.append(_Step('hold', duration))
        return self

    def portrait_show(self, npc_key, name, color=None):
        self.steps.append(_Step('portrait_show', 0.0,
                                npc_key=npc_key, name=name, color=color))
        return self

    def portrait_hide(self):
        self.steps.append(_Step('portrait_hide', 0.0))
        return self

    def text_show(self, text, duration=2.5, voice_id=None):
        self.steps.append(_Step('text_show', duration,
                                text=text, voice_id=voice_id))
        return self

    def sfx(self, name, volume=1.0):
        self.steps.append(_Step('sfx', 0.0, name=name, volume=volume))
        return self

    def voice(self, npc_key, category='quest_offer', volume=0.8):
        self.steps.append(_Step('voice', 0.0,
                                npc_key=npc_key,
                                category=category, volume=volume))
        return self

    def wait(self, duration=0.5):
        self.steps.append(_Step('wait', duration))
        return self

    def fade(self, color=(0, 0, 0), to_alpha=255, duration=0.6):
        self.steps.append(_Step('fade', duration,
                                color=color, to_alpha=to_alpha))
        return self

    def music(self, track_key, crossfade_ms=600):
        self.steps.append(_Step('music', 0.0,
                                track_key=track_key,
                                crossfade_ms=crossfade_ms))
        return self

    def shake(self, intensity=12, duration=0.4):
        self.steps.append(_Step('shake', duration, intensity=intensity))
        return self

    def callback(self, fn):
        """Custom callback `fn(game)` (z.B. Player-State setzen)."""
        self.steps.append(_Step('callback', 0.0, fn=fn))
        return self

    def end(self):
        return self


# ============================================================
# CUTSCENE-PLAYER
# ============================================================
class CutscenePlayer:
    """Render + Update Engine fuer eine aktive Cutscene."""

    def __init__(self, font_med, font_small, font_big=None):
        self.font_med = font_med
        self.font_small = font_small
        self.font_big = font_big or font_med
        self.cutscene = None
        self.step_idx = -1
        self.step_t = 0.0
        # Aktuelle Render-State (akkumuliert ueber Steps)
        self.portrait_key = None
        self.portrait_name = ''
        self.portrait_color = GOLD
        self.text_line = ''
        self.text_left = 0.0
        self.fade_alpha = 0
        self.fade_color = (0, 0, 0)
        self.fade_total = 0.0
        self.fade_from = 0
        self.fade_to = 0
        self.fade_t = 0.0
        self.cam_target = None   # (tx, ty, t, total, from_x, from_y)
        # Portrait-Cache
        self._portrait_cache = {}

    def play(self, cutscene, game=None):
        self.cutscene = cutscene
        self.step_idx = -1
        self.step_t = 0.0
        self.portrait_key = None
        self.text_line = ''
        self.text_left = 0.0
        self.fade_alpha = 0
        self.cam_target = None
        self._advance(game)

    def stop(self, game=None):
        self.cutscene = None
        self.portrait_key = None
        self.text_line = ''
        self.text_left = 0.0
        self.fade_alpha = 0
        self.cam_target = None

    @property
    def is_playing(self):
        return self.cutscene is not None

    def _advance(self, game):
        """Move to next step, fire instant actions."""
        if self.cutscene is None:
            return
        self.step_idx += 1
        self.step_t = 0.0
        if self.step_idx >= len(self.cutscene.steps):
            self.stop(game)
            return
        step = self.cutscene.steps[self.step_idx]
        # Instant-Actions immediately apply
        if step.kind == 'portrait_show':
            self.portrait_key = step.data.get('npc_key')
            self.portrait_name = step.data.get('name', '')
            col = step.data.get('color')
            self.portrait_color = col or GOLD
        elif step.kind == 'portrait_hide':
            self.portrait_key = None
        elif step.kind == 'text_show':
            self.text_line = step.data.get('text', '')
            self.text_left = step.duration
            voice_id = step.data.get('voice_id')
            if voice_id and game is not None:
                try:
                    from . import sounds as _snd
                    _snd.play(voice_id, volume=0.8)
                except Exception:
                    pass
        elif step.kind == 'sfx':
            if game is not None:
                try:
                    from . import sounds as _snd
                    _snd.play(step.data['name'],
                              volume=step.data.get('volume', 1.0))
                except Exception:
                    pass
        elif step.kind == 'voice':
            if game is not None:
                try:
                    from . import sounds as _snd
                    _snd.play_voice(
                        step.data['npc_key'],
                        step.data.get('category', 'quest_offer'),
                        volume=step.data.get('volume', 0.8))
                except Exception:
                    pass
        elif step.kind == 'shake':
            if game is not None:
                try:
                    game.shake = max(getattr(game, 'shake', 0),
                                     step.data.get('intensity', 8))
                except Exception:
                    pass
        elif step.kind == 'camera_move':
            tx = step.data.get('target_x', 0.0)
            ty = step.data.get('target_y', 0.0)
            if game is not None:
                px = game.player.pos.x
                py = game.player.pos.y
            else:
                px, py = 0.0, 0.0
            self.cam_target = (tx, ty, 0.0, step.duration, px, py)
        elif step.kind == 'fade':
            self.fade_color = step.data.get('color', (0, 0, 0))
            self.fade_from = self.fade_alpha
            self.fade_to = step.data.get('to_alpha', 255)
            self.fade_total = max(0.001, step.duration)
            self.fade_t = 0.0
        elif step.kind == 'music':
            if game is not None:
                try:
                    from . import sounds as _snd
                    _snd.crossfade_music(
                        step.data['track_key'],
                        step.data.get('crossfade_ms', 600))
                except Exception:
                    pass
        elif step.kind == 'callback':
            fn = step.data.get('fn')
            if callable(fn) and game is not None:
                try:
                    fn(game)
                except Exception:
                    pass
        # Steps with zero duration auto-advance next frame
        if step.duration <= 0.0 and step.kind not in ('hold', 'wait',
                                                       'text_show',
                                                       'camera_move',
                                                       'fade'):
            self._advance(game)

    def request_skip(self, game):
        """Skip current cutscene (SPACE-Hold)."""
        if self.cutscene is None:
            return
        if not self.cutscene.skippable:
            return
        self.stop(game)

    def update(self, dt, game=None):
        if self.cutscene is None:
            return
        step = self.cutscene.steps[self.step_idx] \
            if 0 <= self.step_idx < len(self.cutscene.steps) else None
        if step is None:
            return
        self.step_t += dt
        # Tick text-left
        if self.text_left > 0:
            self.text_left -= dt
            if self.text_left < 0:
                self.text_left = 0
        # Fade tick
        if self.fade_total > 0:
            self.fade_t += dt
            t = min(1.0, self.fade_t / self.fade_total)
            self.fade_alpha = int(self.fade_from + (self.fade_to - self.fade_from) * t)
            if t >= 1.0:
                self.fade_total = 0.0
        # Camera-move tick
        if self.cam_target is not None and game is not None:
            tx, ty, ct, total, fx, fy = self.cam_target
            ct += dt
            if total > 0:
                k = min(1.0, ct / total)
            else:
                k = 1.0
            # Smooth ease
            k_eased = k * k * (3 - 2 * k)
            cur_x = fx + (tx - fx) * k_eased
            cur_y = fy + (ty - fy) * k_eased
            # Game has _cam_offset_x/y — direkt schreiben (X-01 macht das auch)
            game._cam_cutscene_x = cur_x - game.player.pos.x
            game._cam_cutscene_y = cur_y - game.player.pos.y
            self.cam_target = (tx, ty, ct, total, fx, fy)
            if k >= 1.0:
                # camera_move done -> advance
                self._advance(game)
                return
        # Step duration over?
        if step.duration > 0 and self.step_t >= step.duration:
            self._advance(game)

    def _portrait_surface(self, npc_key, color):
        if npc_key in self._portrait_cache:
            return self._portrait_cache[npc_key]
        # Try load PNG
        try:
            import os
            path = os.path.join('assets', 'portraits', f'{npc_key}.png')
            if os.path.isfile(path):
                surf = pygame.image.load(path).convert_alpha()
                if surf.get_width() != 256:
                    surf = pygame.transform.smoothscale(surf, (256, 256))
                self._portrait_cache[npc_key] = surf
                return surf
        except Exception:
            pass
        # Procedural placeholder
        surf = pygame.Surface((256, 256), pygame.SRCALPHA)
        surf.fill((24, 18, 12, 255))
        # Radial vignette
        for i in range(20):
            t = i / 20.0
            r = int(140 - t * 50)
            a = int(60 * (1 - t))
            pygame.draw.circle(surf, (*color, a),
                               (128, 108), r)
        pygame.draw.rect(surf, color, (0, 0, 256, 256), 3)
        pygame.draw.rect(surf, GOLD, (5, 5, 246, 246), 1)
        # Big initial
        try:
            big = pygame.font.SysFont('georgia,times', 130, bold=True)
            txt = big.render(npc_key[:1].upper(), True, (220, 200, 150))
            surf.blit(txt, txt.get_rect(center=(128, 128)))
        except Exception:
            pass
        self._portrait_cache[npc_key] = surf
        return surf

    def draw(self, screen):
        if self.cutscene is None:
            return
        # Letterbox bars (top + bottom)
        bar_h = 90
        pygame.draw.rect(screen, (0, 0, 0), (0, 0, SCREEN_W, bar_h))
        pygame.draw.rect(screen, (0, 0, 0),
                         (0, SCREEN_H - bar_h, SCREEN_W, bar_h))
        # Portrait left + text right
        if self.portrait_key:
            portrait = self._portrait_surface(
                self.portrait_key, self.portrait_color)
            p_x = 60
            p_y = SCREEN_H - bar_h - 256 - 20
            screen.blit(portrait, (p_x, p_y))
            name = self.font_med.render(
                self.portrait_name, True, GOLD_BRIGHT)
            screen.blit(name, (p_x + (256 - name.get_width()) // 2,
                                p_y + 256 + 6))
        if self.text_line:
            # Lower-Third text — soft-wrap
            tx = 360 if self.portrait_key else SCREEN_W // 2 - 400
            ty = SCREEN_H - bar_h + 18
            for line in _wrap(self.text_line, self.font_med, SCREEN_W - tx - 60):
                surf = self.font_med.render(line, True, TEXT)
                screen.blit(surf, (tx, ty))
                ty += surf.get_height() + 4
        # Fade overlay
        if self.fade_alpha > 0:
            f = pygame.Surface((SCREEN_W, SCREEN_H))
            f.fill(self.fade_color)
            f.set_alpha(self.fade_alpha)
            screen.blit(f, (0, 0))
        # Skip-Hint
        if self.cutscene.skippable:
            hint = self.font_small.render(
                'SPACE — ueberspringen', True, (200, 180, 130))
            screen.blit(hint, (SCREEN_W - hint.get_width() - 20,
                               SCREEN_H - 28))


def _wrap(text, font, max_w):
    """Soft-wrap text to fit max_w."""
    words = text.split()
    lines = []
    cur = []
    cur_w = 0
    space_w = font.size(' ')[0]
    for w in words:
        ww = font.size(w)[0]
        if cur and cur_w + space_w + ww > max_w:
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
# PRE-BUILT CUTSCENES (T3.5-B..F)
# ============================================================

def akt1_shipwreck_intro():
    """T3.5-B: Akt-1-Schiffbruch-Intro.

    Wird beim ersten Spawn nach New-Game gespielt.  Stellt Korven Vor
    + die Salzwunde vor.
    """
    return (Cutscene('akt1_intro', skippable=True)
        .fade(color=(0, 0, 0), to_alpha=255, duration=0.0)
        .fade(color=(0, 0, 0), to_alpha=0, duration=1.2)
        .text_show(
            'Du erwachst am Strand von Brassweir. Salz brennt in '
            'deinen Wunden, der Mond ist eine fremde Sprache.',
            duration=4.0)
        .wait(0.4)
        .portrait_show('korven', 'Korven Vor', color=(200, 170, 120))
        .voice('korven', 'greeting', volume=0.8)
        .text_show(
            '„Schoen, dass du noch atmest. Setz dich. Drei Doerfer '
            'sind weg, und ich glaube nicht an Zufaelle."',
            duration=4.4)
        .wait(0.3)
        .portrait_hide()
        .text_show(
            'Akt I beginnt: Die Salzwunde.',
            duration=2.0)
        .end())


def akt2_helst_pact():
    """T3.5-C: Akt-2-Helst-Pakt-Cutscene."""
    return (Cutscene('akt2_helst', skippable=True)
        .portrait_show('helst', 'Bruder Helst', color=(160, 200, 240))
        .voice('helst', 'greeting', volume=0.8)
        .text_show(
            '„Der Aschen-Pakt ist alt. Die Erblinde tragen ihn — und er '
            'traegt uns."',
            duration=4.0)
        .wait(0.4)
        .text_show(
            '„Wenn du Glas sehen willst, musst du blind sein lernen."',
            duration=3.2)
        .portrait_hide()
        .end())


def akt3_vehren_reveal():
    """T3.5-D: Akt-3-Vehren-Reveal-Cutscene (Valsa-Besessenheit)."""
    return (Cutscene('akt3_vehren', skippable=True)
        .fade(color=(180, 60, 30), to_alpha=80, duration=0.4)
        .portrait_show('vehren', 'Inquisitor-General Vehren',
                       color=(220, 80, 40))
        .voice('vehren', 'phase', volume=0.85)
        .text_show(
            '„Valsa flackert in meinem Knochenmark. Ich brenne — '
            'und ich liebe es."',
            duration=4.4)
        .shake(intensity=14, duration=0.4)
        .wait(0.3)
        .portrait_hide()
        .fade(color=(180, 60, 30), to_alpha=0, duration=0.8)
        .end())


def akt4_shulavh_encounter():
    """T3.5-E: Akt-4-Shulavh-Encounter (Pre-Choice)."""
    return (Cutscene('akt4_shulavh', skippable=True)
        .portrait_show('shulavh', 'Shulavh, die Faden-Mutter',
                       color=(180, 100, 200))
        .voice('drei_muetter', 'greeting', volume=0.8)
        .text_show(
            '„Du kommst, mein Faden. Wirst du mich heilen — oder '
            'schneiden?"',
            duration=4.4)
        .wait(0.4)
        .portrait_hide()
        .text_show(
            'Eine Wahl wartet auf dich.',
            duration=2.4)
        .end())


def akt5_ousen_reveal():
    """T3.5-F: Akt-5-Ousen-Reveal-Cutscene (groesster Story-Moment).

    Wird beim Velharn-Trio-Phase-3-Death getriggert.
    """
    return (Cutscene('akt5_ousen', skippable=False)
        .fade(color=(220, 200, 140), to_alpha=160, duration=0.8)
        .shake(intensity=18, duration=0.5)
        .text_show(
            'Drei Spiegel zerbrechen. Du siehst sie zum ersten Mal.',
            duration=3.0)
        .wait(0.4)
        .portrait_show('ousen', 'Ousen, der Siebte Aspekt',
                       color=(255, 220, 140))
        .voice('drei_muetter', 'final', volume=0.95)
        .text_show(
            '„Ich habe euch beobachtet. Sieben mal sieben Generationen. '
            'Und ich habe nichts gesagt."',
            duration=5.0)
        .wait(0.4)
        .text_show(
            '„Bis jetzt."',
            duration=2.2)
        .fade(color=(220, 200, 140), to_alpha=0, duration=1.0)
        .end())


# ============================================================
# CUTSCENE-CATALOG (lookup by key)
# ============================================================

CUTSCENES = {
    'akt1_intro':       akt1_shipwreck_intro,
    'akt2_helst':       akt2_helst_pact,
    'akt3_vehren':      akt3_vehren_reveal,
    'akt4_shulavh':     akt4_shulavh_encounter,
    'akt5_ousen':       akt5_ousen_reveal,
}


def play_cutscene(game, key):
    """High-Level-API: Spielt die Cutscene `key` im laufenden Game."""
    factory = CUTSCENES.get(key)
    if factory is None:
        return False
    cs = factory()
    player = getattr(game, 'cutscene_player', None)
    if player is None:
        return False
    player.play(cs, game=game)
    return True
