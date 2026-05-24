"""Smoke-Test fuer sf/spatial_grid.py (Audit #179 B.5)."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pygame.math import Vector2
from sf.spatial_grid import SpatialGrid


class E:
    def __init__(self, x, y):
        self.pos = Vector2(x, y)


def main():
    g = SpatialGrid(cell_size=128)
    ents = [E(i * 30, i * 20) for i in range(50)]
    g.rebuild(ents)
    assert len(g) == 50, f"expected 50, got {len(g)}"

    # Query radius 150 around (100, 100): erwartet eine handvoll Kandidaten.
    hits = list(g.query_radius(100, 100, 150))
    # Final-Distance-Check (caller-side, hier explizit):
    real_hits = [e for e in hits
                 if (e.pos - Vector2(100, 100)).length() <= 150]
    print(f"Grid={len(g)} entities")
    print(f"query(100, 100, 150) -> {len(hits)} candidates, "
          f"{len(real_hits)} after distance check")

    # Sanity-Check: linear-loop muss identische real_hits liefern.
    linear_hits = [e for e in ents
                   if (e.pos - Vector2(100, 100)).length() <= 150]
    assert set(id(e) for e in real_hits) == set(id(e) for e in linear_hits), (
        f"grid mismatch: {len(real_hits)} grid vs {len(linear_hits)} linear")
    print(f"Linear-loop matches grid: {len(linear_hits)} hits OK")

    # Update + remove
    ents[0].pos = Vector2(5000, 5000)
    g.update(ents[0])
    assert ents[0] not in [e for e in g.query_radius(0, 0, 100)]
    g.remove(ents[0])
    assert len(g) == 49
    print("update() + remove() OK")

    # Empty radius
    g.clear()
    assert len(list(g.query_radius(0, 0, 1000))) == 0
    print("clear() + empty-query OK")

    print("\nALL TESTS PASSED")


if __name__ == '__main__':
    main()
