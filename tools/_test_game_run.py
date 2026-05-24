"""Live-Smoke: Game startet, laeuft 60 frames, kein Crash. Audit #179 B.5."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ['SDL_VIDEODRIVER'] = 'dummy'
os.environ['SDL_AUDIODRIVER'] = 'dummy'

import pygame
pygame.init()
pygame.mixer.init()
pygame.display.set_mode((1280, 720))

from sf.game import Game


def main():
    g = Game()
    g.start_game('adventure')

    # Spawn 30 enemies manuell um Grid zu stressen
    from sf.enemies import spawn_enemy
    for i in range(30):
        e = spawn_enemy('skeleton', 500 + (i % 6) * 80,
                         500 + (i // 6) * 80, 1)
        g.enemies.append(e)
    print(f"Spawned {len(g.enemies)} enemies")

    # 60 Frames laufen lassen
    for i in range(60):
        g.update(0.016)
        if i in (0, 30, 59):
            print(f"  frame {i}: enemies={len(g.enemies)}, "
                  f"grid_size={len(g.enemy_grid)}, "
                  f"grid_cells={len(g.enemy_grid.cells)}")

    # Test query_radius
    hits = list(g.enemy_grid.query_radius(540, 540, 150))
    print(f"\nquery_radius(540, 540, 150) candidates: {len(hits)}")

    print("\nALL 60 FRAMES OK - no crash")


if __name__ == '__main__':
    main()
