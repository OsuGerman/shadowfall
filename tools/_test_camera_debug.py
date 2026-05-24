"""Debug warum test_camera_lookahead failed."""

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

    # Baseline (kein Movement)
    g._cam_offset_x = 0.0
    g._cam_offset_y = 0.0
    g._cam_prev_player_pos = (g.player.pos.x, g.player.pos.y)
    for _ in range(30):
        g._update_camera(0.016)
    baseline_x = g._cam_offset_x
    print(f"Baseline _cam_offset_x: {baseline_x:.3f}")
    print(f"camera_lookahead setting: {g.settings.get('camera_lookahead')}")
    print(f"camera_cursor_lean setting: {g.settings.get('camera_cursor_lean')}")

    # Movement
    g._cam_offset_x = 0.0
    for i in range(30):
        g._cam_prev_player_pos = (g.player.pos.x - 50,
                                   g.player.pos.y)
        g._update_camera(0.016)
        if i < 3:
            print(f"  frame {i}: _cam_offset_x={g._cam_offset_x:.3f}")
    moving_x = g._cam_offset_x
    print(f"Moving _cam_offset_x: {moving_x:.3f}")


if __name__ == '__main__':
    main()
