"""Spatial-Grid fuer schnelle Radius-Queries (Audit #179 B.5).

Ersetzt O(N^2)-Loops in AoE-Schaden, Pack-Death-Reaktionen und Decor-
Kollision. Statt `for e in self.enemies: if (e.pos - origin).length() < r`
laeuft die Query nur ueber Entities in den raumlich relevanten Zellen.

Design:
- Bucket-Grid: `cells: dict[(cx, cy)] -> set[entity]`
- Cell-Size = 128 px (typische AoE-Radien 40-240 px decken 1-4 Zellen ab)
- Caller macht Final-Distance-Check; Grid liefert Kandidaten (mit
  false-positives an Zell-Raendern, das ist erwartet und billiger als ein
  zweiter Kreis-Check im Grid).

Strategie fuer Integration:
- `rebuild(entities)` einmal pro Frame VOR allen Queries (Game._update_world).
  Bei N=50 Entities ~5 us; rebuild ist amortisiert gratis verglichen mit
  einer einzigen O(N^2)-Operation pro Frame.
- Alternativ: `insert/remove/update` bei Spawn/Death/Move — invasiver, aber
  noch billiger wenn Move-Events selten passieren (statische Decor).

Hot-Path-Calls:
- Fireball-AoE: `grid.query_radius(proj.pos.x, proj.pos.y, aoe)`
- Pack-Death: `grid.query_radius(e.pos.x, e.pos.y, 220)`
- Decor-Collision: `decor_grid.query_radius(x, y, r + max_collide_r)`
"""

from __future__ import annotations


_DEFAULT_CELL_SIZE = 128


class SpatialGrid:
    """Bucket-Grid fuer 2D-Radius-Queries.

    Entities muessen `pos.x` und `pos.y` als float-Attribute haben (pygame
    `Vector2` reicht). Decor mit `x`, `y` wird per `insert_xy()` unterstuetzt.
    """

    __slots__ = ('cell_size', 'cells', '_entity_cells')

    def __init__(self, cell_size=_DEFAULT_CELL_SIZE):
        self.cell_size = cell_size
        self.cells = {}            # (cx, cy) -> set[entity]
        self._entity_cells = {}    # id(entity) -> (cx, cy)

    # ---------- Basic ops ----------
    def _key(self, x, y):
        cs = self.cell_size
        return (int(x // cs), int(y // cs))

    def clear(self):
        self.cells.clear()
        self._entity_cells.clear()

    def insert(self, entity):
        """Insert Entity mit .pos.x/.pos.y."""
        k = self._key(entity.pos.x, entity.pos.y)
        bucket = self.cells.get(k)
        if bucket is None:
            self.cells[k] = bucket = set()
        bucket.add(entity)
        self._entity_cells[id(entity)] = k

    def insert_xy(self, entity, x, y):
        """Insert mit expliziten Koordinaten (z.B. Decor mit .x/.y)."""
        k = self._key(x, y)
        bucket = self.cells.get(k)
        if bucket is None:
            self.cells[k] = bucket = set()
        bucket.add(entity)
        self._entity_cells[id(entity)] = k

    def remove(self, entity):
        k = self._entity_cells.pop(id(entity), None)
        if k is None:
            return
        bucket = self.cells.get(k)
        if bucket is not None:
            bucket.discard(entity)
            if not bucket:
                del self.cells[k]

    def update(self, entity):
        """Re-bucket entity wenn .pos sich geaendert hat. O(1) bei gleicher Cell."""
        new_k = self._key(entity.pos.x, entity.pos.y)
        old_k = self._entity_cells.get(id(entity))
        if old_k == new_k:
            return
        if old_k is not None:
            old_bucket = self.cells.get(old_k)
            if old_bucket is not None:
                old_bucket.discard(entity)
                if not old_bucket:
                    del self.cells[old_k]
        bucket = self.cells.get(new_k)
        if bucket is None:
            self.cells[new_k] = bucket = set()
        bucket.add(entity)
        self._entity_cells[id(entity)] = new_k

    def rebuild(self, entities):
        """Komplett-Reset und neu befuellen.

        Nutzung: einmal pro Frame in Game._update_world() vor AoE-Queries.
        O(N) — bei N=50 Entities ~5-10 us.
        """
        self.cells.clear()
        self._entity_cells.clear()
        for e in entities:
            k = self._key(e.pos.x, e.pos.y)
            bucket = self.cells.get(k)
            if bucket is None:
                self.cells[k] = bucket = set()
            bucket.add(e)
            self._entity_cells[id(e)] = k

    def rebuild_xy(self, entities):
        """Wie rebuild(), aber Entities haben .x/.y statt .pos."""
        self.cells.clear()
        self._entity_cells.clear()
        for e in entities:
            k = self._key(e.x, e.y)
            bucket = self.cells.get(k)
            if bucket is None:
                self.cells[k] = bucket = set()
            bucket.add(e)
            self._entity_cells[id(e)] = k

    # ---------- Queries ----------
    def query_radius(self, x, y, radius):
        """Yield alle Entities, deren Cell mit Kreis (x,y,radius) ueberlappt.

        WICHTIG: Caller muss Final-Distance-Check machen. Grid liefert
        konservative Kandidaten (alle in den ueberlappenden Cells), inklusive
        false-positives an Zell-Raendern. Das ist Absicht — billiger als
        zweimal Kreis-Math hier UND beim Caller.
        """
        cs = self.cell_size
        r_cells = int(radius // cs) + 1
        cx, cy = self._key(x, y)
        cells_dict = self.cells
        for ix in range(cx - r_cells, cx + r_cells + 1):
            for iy in range(cy - r_cells, cy + r_cells + 1):
                bucket = cells_dict.get((ix, iy))
                if bucket:
                    yield from bucket

    def __len__(self):
        return len(self._entity_cells)

    def __contains__(self, entity):
        return id(entity) in self._entity_cells
