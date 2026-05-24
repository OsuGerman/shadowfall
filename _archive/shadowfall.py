"""
Shadowfall — Ein einfacher PoE-artiger ARPG-Prototyp in Pygame.

Installation:
    pip install pygame

Start:
    python shadowfall.py

Steuerung:
    Linksklick auf Boden  ->  bewegen
    Linksklick auf Feind  ->  Nahkampfangriff
    Q                     ->  Feuerball (15 Mana, AoE)
    W                     ->  Kettenblitz (25 Mana, bis zu 3 Gegner)
    E                     ->  Heilung (30 Mana)
    Leertaste             ->  Ausweichrolle (kurze Unverwundbarkeit)
    ESC                   ->  Beenden
"""

import math
import random
import pygame
from pygame.math import Vector2


# ============================================================
# KONSTANTEN
# ============================================================
SCREEN_W, SCREEN_H = 1280, 720
FPS = 60

# Farben
BG          = (10, 8, 6)
GOLD        = (212, 175, 55)
GOLD_BRIGHT = (244, 207, 87)
BLOOD       = (139, 26, 26)
BLOOD_LIGHT = (201, 42, 42)
MANA        = (74, 139, 203)
FIRE        = (255, 138, 58)
TEXT        = (200, 184, 136)
TEXT_DIM    = (120, 104, 88)
WHITE       = (255, 255, 255)

# Gegner-Vorlagen
ENEMY_TYPES = {
    'zombie':   dict(name='Zombie',    color=(90, 122, 58),  glow=(154, 255, 122),
                     hp=25,  dmg=8,  speed=60,  radius=14, xp=8,  gold=(1, 4),
                     att_range=25, att_cd=1.2),
    'skeleton': dict(name='Skelett',   color=(216, 200, 168), glow=(255, 255, 204),
                     hp=18,  dmg=6,  speed=90,  radius=12, xp=10, gold=(2, 5),
                     att_range=28, att_cd=0.9),
    'wraith':   dict(name='Geist',     color=(74, 58, 106),  glow=(170, 138, 255),
                     hp=35,  dmg=10, speed=140, radius=13, xp=18, gold=(4, 10),
                     att_range=30, att_cd=1.1),
    'demon':    dict(name='Dämon',     color=(139, 26, 26),  glow=(255, 74, 74),
                     hp=50,  dmg=14, speed=110, radius=17, xp=22, gold=(5, 12),
                     att_range=32, att_cd=1.0),
    'brute':    dict(name='Berserker', color=(106, 58, 26),  glow=(255, 170, 58),
                     hp=120, dmg=22, speed=70,  radius=22, xp=50, gold=(12, 25),
                     att_range=38, att_cd=1.5),
}


def lerp(a, b, t):
    return a + (b - a) * t


# ============================================================
# ENTITÄTEN
# ============================================================
class Player:
    def __init__(self):
        self.pos = Vector2(0, 0)
        self.target = Vector2(0, 0)
        self.moving = False
        self.radius = 14
        self.speed = 220
        self.hp_max = 100
        self.hp = 100.0
        self.mp_max = 50
        self.mp = 50.0
        self.hp_regen = 1.5
        self.mp_regen = 8.0
        self.level = 1
        self.xp = 0
        self.xp_to_next = 30
        self.damage = 14
        self.facing = 0.0
        self.attack_cd = 0.0
        self.attack_target = None
        self.skill_cd = {'fireball': 0.0, 'lightning': 0.0, 'heal': 0.0}
        self.invuln = 0.0
        self.dodge = 0.0
        self.dodge_dir = Vector2(0, 0)
        self.dodge_cd = 0.0


class Enemy:
    def __init__(self, type_key, x, y, wave):
        t = ENEMY_TYPES[type_key]
        self.type_key = type_key
        self.color = t['color']
        self.glow = t['glow']
        scale_hp = 1 + (wave - 1) * 0.18
        scale_dmg = 1 + (wave - 1) * 0.12
        self.hp_max = t['hp'] * scale_hp
        self.hp = self.hp_max
        self.dmg = t['dmg'] * scale_dmg
        self.speed = t['speed']
        self.radius = t['radius']
        self.xp = t['xp']
        self.gold_range = t['gold']
        self.att_range = t['att_range']
        self.att_cd = t['att_cd']
        self.pos = Vector2(x, y)
        self.attack_timer = 0.0
        self.hit_flash = 0.0
        self.wobble = random.uniform(0, math.tau)


class Projectile:
    def __init__(self, x, y, vx, vy, damage, kind='fireball'):
        self.pos = Vector2(x, y)
        self.vel = Vector2(vx, vy)
        self.damage = damage
        self.kind = kind
        self.radius = 9
        self.life = 1.2
        self.age = 0.0
        self.hit_ids = set()


class Loot:
    def __init__(self, x, y, gold):
        self.pos = Vector2(x, y)
        self.gold = gold
        self.bob = random.uniform(0, math.tau)
        r = random.random()
        if r > 0.93:
            self.kind, self.color = 'gem', (170, 58, 255)
        elif r > 0.85:
            self.kind, self.color = 'gem', (58, 170, 255)
        elif r > 0.75:
            self.kind, self.color = 'gem', (58, 255, 122)
        else:
            self.kind, self.color = 'gold', GOLD


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size, gravity=0):
        self.pos = Vector2(x, y)
        self.vel = Vector2(vx, vy)
        self.color = color
        self.life = life
        self.age = 0.0
        self.size = size
        self.gravity = gravity


class Floater:
    def __init__(self, x, y, text, color):
        self.pos = Vector2(x, y)
        self.text = str(text)
        self.color = color
        self.life = 0.9
        self.age = 0.0
        self.vy = -50.0


class LightningBolt:
    def __init__(self, x1, y1, x2, y2):
        # Vorgenerierte zackige Punkte (Welt-Koordinaten)
        segs = 8
        self.points = [(x1, y1)]
        for i in range(1, segs):
            t = i / segs
            self.points.append((
                lerp(x1, x2, t) + random.uniform(-12, 12),
                lerp(y1, y2, t) + random.uniform(-12, 12),
            ))
        self.points.append((x2, y2))
        self.life = 0.2
        self.age = 0.0


class Decor:
    def __init__(self, x, y, kind, rot=0.0, size=60, shade=0.1):
        self.x = x
        self.y = y
        self.kind = kind  # 'stone', 'skull', 'bone', 'rock', 'rune'
        self.rot = rot
        self.size = size
        self.shade = shade


# ============================================================
# HAUPTSPIEL
# ============================================================
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption('Shadowfall')
        self.clock = pygame.time.Clock()

        # Fonts (Fallback wenn georgia nicht da)
        self.font_big   = pygame.font.SysFont('georgia,times', 56, bold=True)
        self.font_med   = pygame.font.SysFont('georgia,times', 22, bold=True)
        self.font_small = pygame.font.SysFont('georgia,times', 14, bold=True)
        self.font_dmg   = pygame.font.SysFont('georgia,times', 16, bold=True)

        self.running = True
        self.state = 'title'  # 'title' | 'playing' | 'dead'
        self._vignette = None
        self._click_grace = 0.0  # verhindert sofortige Bewegung nach Start
        self.reset()

    # ---------- Reset / Setup ----------
    def reset(self):
        self.player = Player()
        self.enemies = []
        self.projectiles = []
        self.loot = []
        self.particles = []
        self.floaters = []
        self.bolts = []
        self.tiles = []
        self.wave = 1
        self.spawned_this_wave = 0
        self.enemies_per_wave = 6
        self.spawn_timer = 1.5
        self.kills = 0
        self.gold = 0
        self.shake = 0.0
        self.camera = Vector2(0, 0)
        self.camera_shake_offset = (0, 0)
        self.generate_decor()

    def generate_decor(self):
        self.tiles = []
        bounds = 2200
        for _ in range(90):
            self.tiles.append(Decor(
                random.uniform(-bounds, bounds),
                random.uniform(-bounds, bounds),
                'stone',
                random.uniform(0, math.tau),
                random.uniform(40, 110),
                random.uniform(0.05, 0.18),
            ))
        for _ in range(50):
            self.tiles.append(Decor(
                random.uniform(-bounds, bounds),
                random.uniform(-bounds, bounds),
                random.choice(['skull', 'bone', 'rock', 'rune']),
                random.uniform(0, math.tau),
            ))

    # ---------- Koordinaten ----------
    def w2s(self, pos):
        """Welt-Koordinaten -> Bildschirm-Koordinaten (inkl. Camera-Shake)."""
        sx, sy = self.camera_shake_offset
        return (pos.x - self.camera.x + SCREEN_W / 2 + sx,
                pos.y - self.camera.y + SCREEN_H / 2 + sy)

    def s2w(self, sx, sy):
        """Bildschirm -> Welt (ignoriert Shake, da das nur visuell ist)."""
        return Vector2(sx - SCREEN_W / 2 + self.camera.x,
                       sy - SCREEN_H / 2 + self.camera.y)

    # ---------- Input ----------
    def handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                self.running = False
            elif ev.type == pygame.KEYDOWN:
                if ev.key == pygame.K_ESCAPE:
                    self.running = False
                elif self.state in ('title', 'dead'):
                    if ev.key in (pygame.K_RETURN, pygame.K_SPACE):
                        self.start_game()
                elif self.state == 'playing':
                    if ev.key == pygame.K_q:
                        self.cast_fireball()
                    elif ev.key == pygame.K_w:
                        self.cast_lightning()
                    elif ev.key == pygame.K_e:
                        self.cast_heal()
                    elif ev.key == pygame.K_SPACE:
                        self.dodge_roll()
            elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if self.state in ('title', 'dead'):
                    self.start_game()
                elif self.state == 'playing' and self._click_grace <= 0:
                    self.handle_click(*ev.pos)

        # Gedrückte Maus = kontinuierliche Bewegung
        if self.state == 'playing' and self._click_grace <= 0:
            if pygame.mouse.get_pressed()[0]:
                self.handle_click(*pygame.mouse.get_pos())

    def start_game(self):
        self.reset()
        self.state = 'playing'
        self._click_grace = 0.25  # 250ms Schonfrist

    def handle_click(self, sx, sy):
        wpos = self.s2w(sx, sy)
        # Klick auf Gegner?
        clicked = None
        for e in self.enemies:
            if (e.pos - wpos).length() < e.radius + 6:
                clicked = e
                break
        if clicked:
            self.player.attack_target = clicked
            self.player.target = Vector2(clicked.pos)
        else:
            self.player.attack_target = None
            self.player.target = wpos
        self.player.moving = True

    # ---------- Skills ----------
    def cast_fireball(self):
        p = self.player
        if p.mp < 15 or p.skill_cd['fireball'] > 0:
            return
        p.mp -= 15
        p.skill_cd['fireball'] = 0.5
        wpos = self.s2w(*pygame.mouse.get_pos())
        direction = wpos - p.pos
        if direction.length_squared() == 0:
            return
        direction = direction.normalize()
        self.projectiles.append(Projectile(
            p.pos.x + direction.x * p.radius,
            p.pos.y + direction.y * p.radius,
            direction.x * 520, direction.y * 520,
            p.damage * 1.8, 'fireball',
        ))
        self.spawn_particles(p.pos.x, p.pos.y, 8, FIRE)

    def cast_lightning(self):
        p = self.player
        if p.mp < 25 or p.skill_cd['lightning'] > 0:
            return
        wpos = self.s2w(*pygame.mouse.get_pos())
        # Bis zu 3 nächstgelegene Gegner in Reichweite
        candidates = sorted(
            ((e, (e.pos - wpos).length()) for e in self.enemies),
            key=lambda t: t[1],
        )
        targets = [c[0] for c in candidates if c[1] < 220][:3]
        if not targets:
            return
        p.mp -= 25
        p.skill_cd['lightning'] = 0.8
        prev = p.pos
        for e in targets:
            self.bolts.append(LightningBolt(prev.x, prev.y, e.pos.x, e.pos.y))
            self.hit_enemy(e, p.damage * 1.4)
            prev = Vector2(e.pos)
        self.shake = max(self.shake, 5)

    def cast_heal(self):
        p = self.player
        if p.mp < 30 or p.skill_cd['heal'] > 0:
            return
        p.mp -= 30
        p.skill_cd['heal'] = 1.5
        amt = p.hp_max * 0.35
        p.hp = min(p.hp_max, p.hp + amt)
        self.spawn_particles(p.pos.x, p.pos.y, 30, (170, 255, 170))
        self.floaters.append(Floater(p.pos.x, p.pos.y - 30, f'+{int(amt)}', (170, 255, 170)))

    def dodge_roll(self):
        p = self.player
        if p.dodge_cd > 0 or p.dodge > 0:
            return
        mx, my = pygame.mouse.get_pos()
        dx, dy = mx - SCREEN_W / 2, my - SCREEN_H / 2
        length = math.hypot(dx, dy)
        if length == 0:
            return
        p.dodge_dir = Vector2(dx / length, dy / length)
        p.dodge = 0.25
        p.dodge_cd = 1.0
        p.invuln = max(p.invuln, 0.3)

    # ---------- Kampf ----------
    def hit_enemy(self, e, dmg):
        e.hp -= dmg
        e.hit_flash = 0.15
        self.spawn_particles(e.pos.x, e.pos.y, 6, e.glow, life_max=0.4)
        self.floaters.append(Floater(e.pos.x, e.pos.y - e.radius - 8,
                                     int(dmg), (255, 100, 100)))
        if e.hp <= 0:
            self.kill_enemy(e)

    def kill_enemy(self, e):
        self.spawn_particles(e.pos.x, e.pos.y, 22, e.color,
                             life_max=0.9, size_max=5, gravity=60)
        self.spawn_particles(e.pos.x, e.pos.y, 8, WHITE)
        gold = random.randint(*e.gold_range)
        self.loot.append(Loot(e.pos.x + random.uniform(-20, 20),
                              e.pos.y + random.uniform(-20, 20),
                              gold))
        self.player.xp += e.xp
        self.kills += 1
        self.shake = max(self.shake, 4)
        if self.player.xp >= self.player.xp_to_next:
            self.level_up()
        if e in self.enemies:
            self.enemies.remove(e)

    def damage_player(self, dmg):
        p = self.player
        if p.invuln > 0 or p.dodge > 0:
            return
        p.hp -= dmg
        p.invuln = 0.3
        self.shake = max(self.shake, 8)
        self.floaters.append(Floater(p.pos.x, p.pos.y - p.radius - 10,
                                     int(dmg), (255, 136, 136)))
        self.spawn_particles(p.pos.x, p.pos.y, 8, (255, 68, 68))
        if p.hp <= 0:
            self.state = 'dead'

    def level_up(self):
        p = self.player
        p.xp -= p.xp_to_next
        p.level += 1
        p.xp_to_next = int(p.xp_to_next * 1.5)
        p.hp_max += 12
        p.hp = p.hp_max
        p.mp_max += 6
        p.mp = p.mp_max
        p.damage += 3
        self.spawn_particles(p.pos.x, p.pos.y, 50, (255, 215, 90),
                             life_max=1.2, size_max=6)
        self.floaters.append(Floater(p.pos.x, p.pos.y - 40,
                                     'STUFENAUFSTIEG!', (255, 215, 90)))
        self.shake = max(self.shake, 6)

    def spawn_particles(self, x, y, count, color, life_max=0.7,
                        size_max=5, gravity=0):
        for _ in range(count):
            a = random.uniform(0, math.tau)
            s = random.uniform(40, 180)
            self.particles.append(Particle(
                x, y,
                math.cos(a) * s, math.sin(a) * s,
                color,
                random.uniform(0.3, life_max),
                random.uniform(2, size_max),
                gravity,
            ))

    # ---------- Spawning ----------
    def spawn_wave_enemy(self):
        p = self.player
        angle = random.uniform(0, math.tau)
        radius = max(SCREEN_W, SCREEN_H) * 0.7
        x = p.pos.x + math.cos(angle) * radius
        y = p.pos.y + math.sin(angle) * radius

        pool = ['zombie', 'zombie']
        if self.wave >= 2: pool += ['skeleton', 'skeleton']
        if self.wave >= 3: pool += ['wraith']
        if self.wave >= 4: pool += ['demon']
        if self.wave >= 6 and random.random() < 0.15: pool += ['brute']

        self.enemies.append(Enemy(random.choice(pool), x, y, self.wave))
        self.spawned_this_wave += 1

    # ============================================================
    # UPDATE
    # ============================================================
    def update(self, dt):
        self._click_grace -= dt
        # Camera-Shake
        if self.shake > 0.3:
            self.camera_shake_offset = (random.uniform(-self.shake, self.shake),
                                        random.uniform(-self.shake, self.shake))
            self.shake *= 0.85
        else:
            self.shake = 0
            self.camera_shake_offset = (0, 0)

        if self.state != 'playing':
            self.update_particles(dt)
            return

        self.update_player(dt)
        self.update_enemies(dt)
        self.update_projectiles(dt)
        self.update_loot(dt)
        self.update_particles(dt)
        self.update_waves(dt)
        # Kamera folgt Spieler
        self.camera = Vector2(self.player.pos)

    def update_player(self, dt):
        p = self.player
        p.attack_cd -= dt
        p.dodge_cd -= dt
        p.invuln -= dt
        p.dodge -= dt
        for k in p.skill_cd:
            p.skill_cd[k] -= dt
        p.hp = min(p.hp_max, p.hp + p.hp_regen * dt)
        p.mp = min(p.mp_max, p.mp + p.mp_regen * dt)

        # Ausweichrolle hat Vorrang
        if p.dodge > 0:
            p.pos += p.dodge_dir * 560 * dt
            return

        # Ziel-Gegner überprüfen
        if p.attack_target and p.attack_target not in self.enemies:
            p.attack_target = None
            p.moving = False

        if p.attack_target:
            p.target = Vector2(p.attack_target.pos)
            diff = p.attack_target.pos - p.pos
            d = diff.length()
            att_range = p.radius + p.attack_target.radius + 6
            if d <= att_range:
                p.moving = False
                if d > 0:
                    p.facing = math.atan2(diff.y, diff.x)
                if p.attack_cd <= 0:
                    self.hit_enemy(p.attack_target, p.damage)
                    p.attack_cd = 0.4
                    # Schwert-Schwung-Partikel
                    for _ in range(5):
                        a = p.facing + random.uniform(-0.4, 0.4)
                        r = p.radius + random.uniform(4, 18)
                        self.particles.append(Particle(
                            p.pos.x + math.cos(a) * r,
                            p.pos.y + math.sin(a) * r,
                            0, 0, (255, 238, 170),
                            0.3, random.uniform(2, 3),
                        ))
            else:
                p.moving = True

        if p.moving:
            diff = p.target - p.pos
            d = diff.length()
            if d < 3:
                p.moving = False
            else:
                p.facing = math.atan2(diff.y, diff.x)
                step = min(p.speed * dt, d)
                p.pos += diff.normalize() * step

    def update_enemies(self, dt):
        p = self.player
        for e in self.enemies:
            e.attack_timer -= dt
            e.hit_flash -= dt
            e.wobble += dt * 4
            diff = p.pos - e.pos
            d = diff.length()
            if d == 0:
                continue
            if d > e.att_range:
                e.pos += diff.normalize() * e.speed * dt
            elif e.attack_timer <= 0:
                self.damage_player(e.dmg)
                e.attack_timer = e.att_cd
                e.pos += diff.normalize() * 6  # kleiner Ausfallschritt

            # Separation (leichtes Abstoßen)
            for o in self.enemies:
                if o is e:
                    continue
                ddiff = e.pos - o.pos
                od = ddiff.length()
                min_d = e.radius + o.radius
                if 0 < od < min_d:
                    e.pos += ddiff.normalize() * (min_d - od) * 0.5

    def update_projectiles(self, dt):
        for proj in self.projectiles[:]:
            proj.age += dt
            proj.pos += proj.vel * dt
            if proj.age >= proj.life:
                if proj.kind == 'fireball':
                    self.spawn_particles(proj.pos.x, proj.pos.y, 14,
                                         (255, 106, 26), life_max=0.6, size_max=5)
                if proj in self.projectiles:
                    self.projectiles.remove(proj)
                continue

            # Schweif
            if proj.kind == 'fireball' and random.random() < 0.7:
                self.particles.append(Particle(
                    proj.pos.x, proj.pos.y,
                    random.uniform(-30, 30), random.uniform(-30, 30),
                    FIRE, random.uniform(0.15, 0.3), random.uniform(2, 4),
                ))

            # Kollision
            for e in self.enemies[:]:
                if id(e) in proj.hit_ids:
                    continue
                if (e.pos - proj.pos).length() < e.radius + proj.radius:
                    proj.hit_ids.add(id(e))
                    self.hit_enemy(e, proj.damage)
                    if proj.kind == 'fireball':
                        # AoE-Explosion
                        for e2 in self.enemies[:]:
                            if e2 is e:
                                continue
                            dd = (e2.pos - proj.pos).length()
                            if dd < 60:
                                self.hit_enemy(e2, proj.damage * 0.5 * (1 - dd / 60))
                        self.spawn_particles(proj.pos.x, proj.pos.y, 22,
                                             (255, 106, 26), life_max=0.7, size_max=6)
                        self.shake = max(self.shake, 4)
                        if proj in self.projectiles:
                            self.projectiles.remove(proj)
                        break

    def update_loot(self, dt):
        p = self.player
        for l in self.loot[:]:
            l.bob += dt * 3
            diff = p.pos - l.pos
            d = diff.length()
            if 0 < d < 80:
                l.pos += diff.normalize() * 320 * dt
            if d < p.radius + 6:
                self.gold += l.gold
                self.floaters.append(Floater(p.pos.x, p.pos.y - 30,
                                             f'+{l.gold} Gold', (255, 215, 90)))
                self.spawn_particles(l.pos.x, l.pos.y, 8, l.color,
                                     life_max=0.4, size_max=3)
                self.loot.remove(l)

    def update_particles(self, dt):
        for p in self.particles[:]:
            p.age += dt
            p.pos += p.vel * dt
            p.vel.y += p.gravity * dt
            p.vel *= 0.94
            if p.age >= p.life:
                self.particles.remove(p)
        for f in self.floaters[:]:
            f.age += dt
            f.pos.y += f.vy * dt
            f.vy *= 0.92
            if f.age >= f.life:
                self.floaters.remove(f)
        for b in self.bolts[:]:
            b.age += dt
            if b.age >= b.life:
                self.bolts.remove(b)

    def update_waves(self, dt):
        self.spawn_timer -= dt
        remaining = self.enemies_per_wave - self.spawned_this_wave
        if remaining > 0 and self.spawn_timer <= 0:
            self.spawn_wave_enemy()
            self.spawn_timer = random.uniform(0.4, 1.2)
        elif remaining <= 0 and not self.enemies:
            self.wave += 1
            self.spawned_this_wave = 0
            self.enemies_per_wave = int(6 + self.wave * 1.8)
            self.spawn_timer = 2.5
            self.floaters.append(Floater(self.player.pos.x, self.player.pos.y - 50,
                                         f'WELLE {self.wave}', GOLD_BRIGHT))

    # ============================================================
    # RENDER
    # ============================================================
    def draw(self):
        self.screen.fill(BG)
        if self.state in ('playing', 'dead'):
            self.draw_world()
        self.draw_vignette()
        if self.state == 'playing':
            self.draw_hud()
        elif self.state == 'title':
            self.draw_title()
        elif self.state == 'dead':
            self.draw_hud()
            self.draw_death()
        self.draw_cursor()
        pygame.display.flip()

    def draw_world(self):
        # Boden-Halo um Spieler
        center = self.w2s(self.player.pos)
        halo = pygame.Surface((1200, 1200), pygame.SRCALPHA)
        for i in range(15, 0, -1):
            alpha = int(12 * (1 - i / 15))
            if alpha > 0:
                pygame.draw.circle(halo, (50, 30, 20, alpha),
                                   (600, 600), i * 40)
        self.screen.blit(halo, (center[0] - 600, center[1] - 600))

        # Decor (nur in Sichtbereich)
        for t in self.tiles:
            sx, sy = self.w2s(Vector2(t.x, t.y))
            if -150 < sx < SCREEN_W + 150 and -150 < sy < SCREEN_H + 150:
                self.draw_decor(t, (sx, sy))

        # Loot, Projektile, Gegner, Spieler
        for l in self.loot:        self.draw_loot(l)
        for pr in self.projectiles: self.draw_projectile(pr)
        for e in self.enemies:     self.draw_enemy(e)
        self.draw_player()

        # Effekte oben drüber
        for p in self.particles:   self.draw_particle(p)
        for b in self.bolts:       self.draw_bolt(b)
        for f in self.floaters:    self.draw_floater(f)

    def draw_decor(self, t, sp):
        sx, sy = int(sp[0]), int(sp[1])
        if t.kind == 'stone':
            alpha = int(80 * t.shade)
            s = int(t.size)
            surf = pygame.Surface((s, s), pygame.SRCALPHA)
            pygame.draw.rect(surf, (60, 40, 25, alpha), (0, 0, s, s))
            pygame.draw.rect(surf, (120, 90, 60, alpha // 2), (0, 0, s, s), 1)
            rot = pygame.transform.rotate(surf, math.degrees(t.rot))
            self.screen.blit(rot, (sx - rot.get_width() // 2,
                                   sy - rot.get_height() // 2))
        elif t.kind == 'skull':
            pygame.draw.circle(self.screen, (180, 160, 130), (sx, sy), 6)
            pygame.draw.circle(self.screen, (10, 5, 0), (sx - 2, sy - 1), 1)
            pygame.draw.circle(self.screen, (10, 5, 0), (sx + 2, sy - 1), 1)
        elif t.kind == 'bone':
            pygame.draw.line(self.screen, (200, 180, 150),
                             (sx - 8, sy), (sx + 8, sy), 3)
            pygame.draw.circle(self.screen, (200, 180, 150), (sx - 8, sy), 2)
            pygame.draw.circle(self.screen, (200, 180, 150), (sx + 8, sy), 2)
        elif t.kind == 'rock':
            pts = [(sx - 10, sy + 4), (sx - 6, sy - 6),
                   (sx + 4, sy - 5), (sx + 8, sy + 3)]
            pygame.draw.polygon(self.screen, (55, 42, 32), pts)
        elif t.kind == 'rune':
            pygame.draw.circle(self.screen, (140, 40, 40), (sx, sy), 14, 1)
            pygame.draw.line(self.screen, (140, 40, 40),
                             (sx - 10, sy), (sx + 10, sy), 1)
            pygame.draw.line(self.screen, (140, 40, 40),
                             (sx, sy - 10), (sx, sy + 10), 1)

    def draw_player(self):
        p = self.player
        sx, sy = self.w2s(p.pos)
        sx, sy = int(sx), int(sy)

        # Schatten
        shadow = pygame.Surface((p.radius * 2, p.radius), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 120),
                            (0, 0, p.radius * 2, p.radius))
        self.screen.blit(shadow, (sx - p.radius, sy + p.radius - 6))

        # Unverwundbarkeits-Glow
        if p.dodge > 0 or p.invuln > 0:
            glow = pygame.Surface((p.radius * 4, p.radius * 4), pygame.SRCALPHA)
            pygame.draw.circle(glow, (150, 200, 255, 90),
                               (p.radius * 2, p.radius * 2), p.radius + 8)
            self.screen.blit(glow, (sx - p.radius * 2, sy - p.radius * 2))

        # Körper
        pygame.draw.circle(self.screen, (60, 74, 124), (sx, sy), p.radius)
        pygame.draw.circle(self.screen, (110, 130, 200), (sx, sy), int(p.radius * 0.65))
        pygame.draw.circle(self.screen, GOLD, (sx, sy), p.radius, 2)

        # Schwert mit Schwung-Animation
        swing = max(0, (0.4 - p.attack_cd)) * 4 if p.attack_cd > 0.05 else 0
        facing = p.facing + (swing - 0.5) * 1.4 if p.attack_cd > 0.05 else p.facing
        x1 = sx + math.cos(facing) * (p.radius - 2)
        y1 = sy + math.sin(facing) * (p.radius - 2)
        x2 = sx + math.cos(facing) * (p.radius + 18)
        y2 = sy + math.sin(facing) * (p.radius + 18)
        pygame.draw.line(self.screen, (232, 232, 208), (x1, y1), (x2, y2), 3)
        pygame.draw.circle(self.screen, (255, 250, 204), (int(x2), int(y2)), 2)

    def draw_enemy(self, e):
        sx, sy = self.w2s(e.pos)
        sy += math.sin(e.wobble) * 1.5
        sx, sy = int(sx), int(sy)

        # Schatten
        shadow = pygame.Surface((e.radius * 2, e.radius), pygame.SRCALPHA)
        pygame.draw.ellipse(shadow, (0, 0, 0, 100),
                            (0, 0, e.radius * 2, e.radius))
        self.screen.blit(shadow, (sx - e.radius, sy + e.radius - 6))

        # Körper
        color = WHITE if e.hit_flash > 0 else e.color
        pygame.draw.circle(self.screen, color, (sx, sy), e.radius)
        pygame.draw.circle(self.screen, e.glow, (sx, sy), e.radius, 1)
        # Glühende Augen
        pygame.draw.circle(self.screen, e.glow,
                           (int(sx - e.radius * 0.3), int(sy - e.radius * 0.2)), 2)
        pygame.draw.circle(self.screen, e.glow,
                           (int(sx + e.radius * 0.3), int(sy - e.radius * 0.2)), 2)

        # HP-Balken
        if e.hp < e.hp_max:
            w = int(e.radius * 2.2)
            x = sx - w // 2
            y = sy - e.radius - 10
            pygame.draw.rect(self.screen, (20, 10, 10), (x, y, w, 4))
            fill = int(w * e.hp / e.hp_max)
            pygame.draw.rect(self.screen, BLOOD_LIGHT, (x, y, fill, 4))

    def draw_projectile(self, proj):
        sx, sy = self.w2s(proj.pos)
        sx, sy = int(sx), int(sy)
        if proj.kind == 'fireball':
            glow = pygame.Surface((80, 80), pygame.SRCALPHA)
            for i in range(5, 0, -1):
                alpha = 60 // i
                pygame.draw.circle(glow, (255, 100, 30, alpha),
                                   (40, 40), proj.radius * i // 2 + 6)
            self.screen.blit(glow, (sx - 40, sy - 40))
            pygame.draw.circle(self.screen, (255, 244, 168), (sx, sy), int(proj.radius * 0.6))

    def draw_bolt(self, b):
        a = 1 - b.age / b.life
        pts = [self.w2s(Vector2(x, y)) for x, y in b.points]
        if len(pts) >= 2:
            color = (180, 200, 255)
            try:
                pygame.draw.lines(self.screen, color, False, pts,
                                  max(1, int(3 * a)))
            except (TypeError, ValueError):
                pass

    def draw_loot(self, l):
        sx, sy = self.w2s(l.pos)
        sy += math.sin(l.bob) * 2
        sx, sy = int(sx), int(sy)
        glow = pygame.Surface((40, 40), pygame.SRCALPHA)
        for i in range(4, 0, -1):
            alpha = 50 // i
            pygame.draw.circle(glow, (*l.color, alpha), (20, 20), i * 4)
        self.screen.blit(glow, (sx - 20, sy - 20))
        if l.kind == 'gold':
            pygame.draw.circle(self.screen, l.color, (sx, sy), 4)
        else:
            pts = [(sx, sy - 5), (sx + 4, sy), (sx, sy + 5), (sx - 4, sy)]
            pygame.draw.polygon(self.screen, l.color, pts)

    def draw_particle(self, p):
        a = 1 - p.age / p.life
        if a <= 0:
            return
        sx, sy = self.w2s(p.pos)
        size = max(1, int(p.size * a))
        color = (*p.color[:3], int(255 * a))
        surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
        pygame.draw.circle(surf, color, (size, size), size)
        self.screen.blit(surf, (sx - size, sy - size))

    def draw_floater(self, f):
        sx, sy = self.w2s(f.pos)
        a = 1 - f.age / f.life
        surf = self.font_dmg.render(f.text, True, f.color)
        surf.set_alpha(int(255 * a))
        self.screen.blit(surf, (sx - surf.get_width() / 2, sy))

    def draw_vignette(self):
        if self._vignette is None:
            v = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            cx, cy = SCREEN_W // 2, SCREEN_H // 2
            max_r = max(SCREEN_W, SCREEN_H)
            for i in range(30):
                t = i / 30
                r = int(max_r * (1 - t * 0.6))
                alpha = int(t * 5)
                pygame.draw.circle(v, (0, 0, 0, alpha), (cx, cy), r)
            self._vignette = v
        self.screen.blit(self._vignette, (0, 0))

    # ---------- HUD ----------
    def draw_hud(self):
        # Oberer Statusbalken
        bar = pygame.Surface((720, 40), pygame.SRCALPHA)
        bar.fill((10, 8, 6, 220))
        self.screen.blit(bar, (SCREEN_W // 2 - 360, 16))
        pygame.draw.line(self.screen, GOLD,
                         (SCREEN_W // 2 - 360, 16), (SCREEN_W // 2 + 360, 16), 2)

        stats = [
            ('STUFE',      self.player.level),
            ('GOLD',       self.gold),
            ('WELLE',      self.wave),
            ('ERSCHLAGEN', self.kills),
        ]
        x = SCREEN_W // 2 - 320
        for label, value in stats:
            ls = self.font_small.render(label, True, TEXT_DIM)
            vs = self.font_med.render(str(value), True, GOLD_BRIGHT)
            self.screen.blit(ls, (x, 26))
            self.screen.blit(vs, (x + ls.get_width() + 6, 21))
            x += ls.get_width() + vs.get_width() + 40

        # Lebens-, Mana-, XP-Balken
        bar_x = SCREEN_W // 2 - 230
        self.draw_bar(bar_x, SCREEN_H - 70, 460, 18,
                      self.player.hp, self.player.hp_max,
                      BLOOD_LIGHT, 'Leben',
                      f'{int(self.player.hp)} / {self.player.hp_max}')
        self.draw_bar(bar_x, SCREEN_H - 48, 460, 18,
                      self.player.mp, self.player.mp_max,
                      MANA, 'Mana',
                      f'{int(self.player.mp)} / {self.player.mp_max}')
        self.draw_bar(bar_x, SCREEN_H - 26, 460, 6,
                      self.player.xp, self.player.xp_to_next,
                      GOLD, 'Erf.', '')

        # Skill-Leiste
        skills = [
            ('LMB', '⚔', None,                          True),
            ('Q',   'F', self.player.skill_cd['fireball'],  self.player.mp >= 15),
            ('W',   'B', self.player.skill_cd['lightning'], self.player.mp >= 25),
            ('E',   'H', self.player.skill_cd['heal'],      self.player.mp >= 30),
        ]
        sw, gap = 56, 12
        total = len(skills) * sw + (len(skills) - 1) * gap
        sx0 = SCREEN_W // 2 - total // 2
        sy0 = SCREEN_H - 140
        for i, (key, icon, cd, can_cast) in enumerate(skills):
            x = sx0 + i * (sw + gap)
            slot = pygame.Surface((sw, sw), pygame.SRCALPHA)
            slot.fill((26, 22, 18, 230))
            self.screen.blit(slot, (x, sy0))
            pygame.draw.line(self.screen, GOLD, (x, sy0), (x + sw, sy0), 2)
            pygame.draw.rect(self.screen, (42, 34, 24), (x, sy0, sw, sw), 1)
            # Icon (geometrisch statt Emoji für Cross-Platform-Kompatibilität)
            self.draw_skill_icon(x, sy0, sw, i, can_cast)
            key_surf = self.font_small.render(key, True, GOLD)
            self.screen.blit(key_surf, (x + sw - key_surf.get_width() - 4, sy0 + 2))
            if cd and cd > 0:
                ov = pygame.Surface((sw, sw), pygame.SRCALPHA)
                ov.fill((0, 0, 0, 180))
                self.screen.blit(ov, (x, sy0))
                cd_surf = self.font_med.render(f'{cd:.1f}', True, GOLD_BRIGHT)
                self.screen.blit(cd_surf,
                                 (x + sw // 2 - cd_surf.get_width() // 2,
                                  sy0 + sw // 2 - cd_surf.get_height() // 2))

    def draw_skill_icon(self, x, y, sw, idx, active):
        """Zeichnet ein einfaches geometrisches Icon im Skill-Slot."""
        cx, cy = x + sw // 2, y + sw // 2
        col = TEXT if active else TEXT_DIM
        if idx == 0:  # Schwert
            pygame.draw.line(self.screen, col, (cx - 10, cy + 10), (cx + 10, cy - 10), 3)
            pygame.draw.line(self.screen, col, (cx - 14, cy + 6), (cx - 6, cy + 14), 2)
        elif idx == 1:  # Feuerball
            pygame.draw.circle(self.screen, (255, 138, 58) if active else (120, 80, 50),
                               (cx, cy), 10)
            pygame.draw.circle(self.screen, (255, 220, 120) if active else (140, 110, 70),
                               (cx, cy), 5)
        elif idx == 2:  # Blitz
            pts = [(cx - 4, cy - 14), (cx + 4, cy - 4), (cx - 2, cy - 4),
                   (cx + 6, cy + 14), (cx - 2, cy + 2), (cx + 2, cy + 2)]
            pygame.draw.polygon(self.screen,
                                (170, 200, 255) if active else (90, 100, 130), pts)
        elif idx == 3:  # Heilung (Kreuz)
            pygame.draw.rect(self.screen,
                             (170, 255, 170) if active else (90, 130, 90),
                             (cx - 3, cy - 12, 6, 24))
            pygame.draw.rect(self.screen,
                             (170, 255, 170) if active else (90, 130, 90),
                             (cx - 12, cy - 3, 24, 6))

    def draw_bar(self, x, y, w, h, val, max_val, color, label, text):
        pygame.draw.rect(self.screen, (15, 10, 8), (x, y, w, h))
        pygame.draw.rect(self.screen, (42, 34, 24), (x, y, w, h), 1)
        fill_w = int(w * (val / max_val)) if max_val > 0 else 0
        if fill_w > 0:
            pygame.draw.rect(self.screen, color, (x, y, fill_w, h))
            hl = pygame.Surface((fill_w, max(1, h // 3)), pygame.SRCALPHA)
            hl.fill((255, 255, 255, 40))
            self.screen.blit(hl, (x, y))
        ls = self.font_small.render(label, True, TEXT_DIM)
        self.screen.blit(ls, (x - ls.get_width() - 10,
                              y + h // 2 - ls.get_height() // 2))
        if text:
            ts = self.font_small.render(text, True, WHITE)
            self.screen.blit(ts, (x + w // 2 - ts.get_width() // 2,
                                  y + h // 2 - ts.get_height() // 2))

    # ---------- Title / Death Screens ----------
    def draw_title(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((5, 3, 2, 240))
        self.screen.blit(ov, (0, 0))

        # Titel mit Schatten-Glow
        title = self.font_big.render('SHADOWFALL', True, GOLD_BRIGHT)
        tr = title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 180))
        for ox, oy in [(-2, -2), (2, 2), (-2, 2), (2, -2)]:
            sh = self.font_big.render('SHADOWFALL', True, (60, 30, 10))
            self.screen.blit(sh, (tr.x + ox, tr.y + oy))
        self.screen.blit(title, tr)

        sub = self.font_med.render('— Eine Reise in die Tiefen —', True, TEXT_DIM)
        self.screen.blit(sub, sub.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 120)))

        lines = [
            ('STEUERUNG',                          GOLD_BRIGHT),
            ('',                                   None),
            ('Linksklick auf Boden  →  bewegen',   TEXT),
            ('Linksklick auf Feind  →  Nahkampf',  TEXT),
            ('Q  →  Feuerball  (15 Mana)',         TEXT),
            ('W  →  Kettenblitz  (25 Mana)',       TEXT),
            ('E  →  Heilen  (30 Mana)',            TEXT),
            ('Leertaste  →  Ausweichrolle',        TEXT),
        ]
        y = SCREEN_H // 2 - 60
        for line, color in lines:
            if not line:
                y += 12
                continue
            surf = self.font_med.render(line, True, color)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_W // 2, y)))
            y += 32

        if pygame.time.get_ticks() % 1600 < 1000:
            start = self.font_med.render('► Klicken oder ENTER zum Starten ◄', True, GOLD)
            self.screen.blit(start, start.get_rect(center=(SCREEN_W // 2, SCREEN_H - 80)))

    def draw_death(self):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((30, 5, 5, 200))
        self.screen.blit(ov, (0, 0))
        title = self.font_big.render('GEFALLEN', True, BLOOD_LIGHT)
        self.screen.blit(title, title.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 - 60)))
        summary = (f'Stufe {self.player.level}   ·   {self.kills} Erschlagen'
                   f'   ·   {self.gold} Gold   ·   Welle {self.wave}')
        ss = self.font_med.render(summary, True, TEXT)
        self.screen.blit(ss, ss.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 10)))
        if pygame.time.get_ticks() % 1600 < 1000:
            r = self.font_med.render('► Klicken oder ENTER für neuen Versuch ◄', True, GOLD)
            self.screen.blit(r, r.get_rect(center=(SCREEN_W // 2, SCREEN_H // 2 + 80)))

    def draw_cursor(self):
        mx, my = pygame.mouse.get_pos()
        col = GOLD
        pygame.draw.circle(self.screen, col, (mx, my), 10, 1)
        pygame.draw.line(self.screen, col, (mx - 14, my), (mx - 4, my), 1)
        pygame.draw.line(self.screen, col, (mx + 4, my), (mx + 14, my), 1)
        pygame.draw.line(self.screen, col, (mx, my - 14), (mx, my - 4), 1)
        pygame.draw.line(self.screen, col, (mx, my + 4), (mx, my + 14), 1)

    # ---------- Main loop ----------
    def run(self):
        pygame.mouse.set_visible(False)
        while self.running:
            dt = min(0.05, self.clock.tick(FPS) / 1000)
            self.handle_events()
            self.update(dt)
            self.draw()
        pygame.quit()


if __name__ == '__main__':
    Game().run()
