"""Pymunk-Physics-Wrapper (Update #171).

SELEKTIVE Physics-Integration — der Velgrad-Engine eigenes Movement-System
(Click-to-Move, radius-based-collision) bleibt UNANGETASTET. Pymunk wird
nur fuer specific Features verwendet:

  1. **Breakable Decor** — Faesser, Vasen, Glas-Saeulen die beim Hit
     zerbrechen + die Splitter fliegen mit physikalischer Trajectory.
  2. **Throwables** — Boss-Wurf-Projektile (Vehren-Aether-Kugel,
     Stein-Wurf, etc.) mit echter Parabel + Bounce.
  3. **Ragdoll-Effects** (optional) — Decor-Splitter koennen am Boden
     liegen + langsam ausgleiten statt instant verschwinden.

Wichtig:
  - Pymunk-Space ist OPTIONAL — wenn pymunk nicht installiert, fallback
    auf alte Engine-Logik (keine Splitter, keine Throwables).
  - Pymunk-Bodies leben SEPARAT von Game.entities — kein Sync-Konflikt
    mit dem bestehenden Player/Enemy-System.
  - Coordinate-Space: 1 pixel = 1 unit (game uses pixel-coords).

Doku: VELGRAD_RENDER_SPEC.md (Decor + Throwable category specs)
"""
from __future__ import annotations

import math
import random
import sys

_PYMUNK_AVAILABLE = False
try:
    import pymunk  # type: ignore
    _PYMUNK_AVAILABLE = True
except ImportError:
    pymunk = None  # type: ignore
    pass


# ============================================================
# CONSTANTS
# ============================================================
GRAVITY_TOPDOWN = (0.0, 0.0)   # Top-Down → keine Gravity (Splitter bremsen via Damping)
DEFAULT_DAMPING = 0.6           # 60% Energie-Erhalt pro Frame → bremst Splitter

# Splitter-Config fuer Breakable-Decor
SPLITTER_RADIUS = 4.0
SPLITTER_DENSITY = 0.5
SPLITTER_FRICTION = 0.4
SPLITTER_ELASTICITY = 0.2

# Throwable-Config (Boss-Projektile)
THROWABLE_RADIUS = 12.0
THROWABLE_DENSITY = 1.0


# ============================================================
# PHYSICS-WORLD
# ============================================================
class PhysicsWorld:
    """Wrappt pymunk.Space + bietet game-spezifische Helpers.

    Lifecycle:
        world = PhysicsWorld()
        if world.enabled:
            world.step(dt)
            world.add_splitter_burst((x, y), n=8)
            world.add_throwable(start_pos, velocity)
            for body in world.iter_bodies(): ...

    Wenn pymunk nicht installiert, world.enabled == False — alle Calls
    sind no-ops. Engine kann robust ohne aufrufen.
    """

    def __init__(self):
        self.enabled = _PYMUNK_AVAILABLE
        self.space = None
        self.bodies: list = []   # tracked bodies (fuer rendering + cleanup)
        if self.enabled:
            self.space = pymunk.Space()
            self.space.gravity = GRAVITY_TOPDOWN
            self.space.damping = DEFAULT_DAMPING

    # ----------------------------------------------------------------
    def step(self, dt: float) -> None:
        """Advance simulation by dt seconds. Cleanup old/stopped bodies."""
        if not self.enabled:
            return
        self.space.step(dt)
        # Cleanup: bodies die LIFE-end haben (z.B. Splitter nach 2 Sek)
        now = self._now()
        alive = []
        for b in self.bodies:
            if b.get('life_end', math.inf) > now:
                alive.append(b)
            else:
                self._remove_body(b)
        self.bodies = alive

    # ----------------------------------------------------------------
    def add_splitter_burst(self, pos: tuple[float, float], *,
                            count: int = 8,
                            speed_min: float = 80.0,
                            speed_max: float = 240.0,
                            life_sec: float = 1.5,
                            color: tuple[int, int, int] = (180, 140, 100),
                            radius: float = SPLITTER_RADIUS,
                            ) -> list:
        """Erzeugt N Splitter-Particles mit zufaelliger Trajectory.

        Wird bei Breakable-Decor-Hit aufgerufen (Fass zerbricht, Vase
        explodiert). Splitter haben pymunk-bodies → realistische
        Wurf-Bahn + Damping.

        Returnt Liste der gespawnten body-Dicts (fuer rendering).
        """
        if not self.enabled:
            return []
        spawned = []
        for _ in range(count):
            ang = random.uniform(0, math.tau)
            speed = random.uniform(speed_min, speed_max)
            vx = math.cos(ang) * speed
            vy = math.sin(ang) * speed

            mass = SPLITTER_DENSITY * math.pi * radius * radius
            inertia = pymunk.moment_for_circle(mass, 0, radius)
            body = pymunk.Body(mass, inertia)
            body.position = pos
            body.velocity = (vx, vy)
            shape = pymunk.Circle(body, radius)
            shape.friction = SPLITTER_FRICTION
            shape.elasticity = SPLITTER_ELASTICITY
            self.space.add(body, shape)

            entry = {
                'body':     body,
                'shape':    shape,
                'kind':     'splitter',
                'color':    color,
                'radius':   radius,
                'life_end': self._now() + life_sec,
            }
            self.bodies.append(entry)
            spawned.append(entry)
        return spawned

    # ----------------------------------------------------------------
    def add_throwable(self, start_pos: tuple[float, float],
                       velocity: tuple[float, float], *,
                       radius: float = THROWABLE_RADIUS,
                       life_sec: float = 4.0,
                       color: tuple[int, int, int] = (220, 180, 100),
                       kind_id: str = 'throwable',
                       payload: dict | None = None,
                       ) -> dict | None:
        """Boss-Throwable (Stein, Aether-Kugel, etc.) mit Parabel-Trajectory.

        Top-Down: Gravity ist 0, also fliegt das Objekt linear — der
        Effekt ist mehr "Drift mit Damping" als echte Parabel. Optional
        kann die Engine einen sin-Y-Offset fuer 'fake-arc' addieren.

        payload: dict mit damage/effect-data, wird bei Treffer ausgelesen.
        Returnt das body-Dict (oder None falls disabled).
        """
        if not self.enabled:
            return None
        mass = THROWABLE_DENSITY * math.pi * radius * radius
        inertia = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, inertia)
        body.position = start_pos
        body.velocity = velocity
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.3
        shape.friction = 0.2
        self.space.add(body, shape)

        entry = {
            'body':     body,
            'shape':    shape,
            'kind':     'throwable',
            'kind_id':  kind_id,
            'color':    color,
            'radius':   radius,
            'life_end': self._now() + life_sec,
            'payload':  payload or {},
        }
        self.bodies.append(entry)
        return entry

    # ----------------------------------------------------------------
    def iter_bodies(self):
        """Iteriere alle Tracked-Bodies fuer Render-Loop."""
        if not self.enabled:
            return iter([])
        return iter(self.bodies)

    # ----------------------------------------------------------------
    def clear(self) -> None:
        """Loescht alle Bodies (z.B. bei Dungeon-Transition)."""
        if not self.enabled:
            return
        for entry in self.bodies:
            self._remove_body(entry)
        self.bodies = []

    # ----------------------------------------------------------------
    def _remove_body(self, entry: dict) -> None:
        try:
            self.space.remove(entry['shape'])
            self.space.remove(entry['body'])
        except Exception:
            pass

    # ----------------------------------------------------------------
    @staticmethod
    def _now() -> float:
        import pygame
        return pygame.time.get_ticks() * 0.001


# ============================================================
# CONVENIENCE
# ============================================================
def is_available() -> bool:
    """True wenn pymunk installiert ist."""
    return _PYMUNK_AVAILABLE
