"""Tiled (.tmx) Level-Loader (Update #178).

Erlaubt hand-crafted Maps aus dem Tiled-Map-Editor (https://www.mapeditor.org/)
als Alternative/Erganzung zum prozeduralen Dungeon-Generator. Boss-Arenen,
Outpost-Hubs und Story-Lore-Spots profitieren von kontrollierten Layouts.

Convention:
  assets/maps/<biome>/<map_name>.tmx
  z.B. assets/maps/town/brassweir_hub.tmx
       assets/maps/crypt/marrowport_boss.tmx
       assets/maps/lava/pyron_arena.tmx

TMX-Layer-Konvention (in Tiled):
  - Layer "floor"       — Tile-Layer mit FLOOR-Tiles (Floor-Cells)
  - Layer "walls"       — Tile-Layer mit WALL-Tiles
  - Layer "spawns"      — Object-Layer mit Player/NPC/Mob-Spawnpoints
                          (Object-Type = 'player_spawn' | 'npc:<key>' |
                          'mob:<bestiary_key>' | 'boss:<key>' | 'decor:<kind>')
  - Layer "interactive" — Object-Layer mit Triggern (chest, portal, sign)
  - Layer "regions"     — Optional, Object-Layer mit named Polygonen
                          (lighting-zone, fog-zone, quest-trigger)

Properties pro Object:
  rotation, properties.<key>, type → werden in dem TiledMap-Result-Dict
  abgespeichert und vom Game-Code interpretiert.

Usage:
    from sf.tiled_loader import load_map, has_map
    if has_map(map_name='brassweir_hub', biome='town'):
        tmx_data = load_map('brassweir_hub', 'town')
        grid, spawns, decor, regions = tmx_to_engine(tmx_data)
        # → in Game.enter_outpost / enter_dungeon einbauen
    else:
        # Fallback: prozedural (alte Logik)
        ...

Doku: VELGRAD_WORKFLOWS_BIBEL.md §VI (geplant)
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MAPS_DIR = PROJECT_ROOT / 'assets' / 'maps'

# Lazy-Import pytmx — fehlt es, faellt Engine auf procedural-only zurueck.
_PYTMX_AVAILABLE = False
try:
    import pytmx  # type: ignore
    _PYTMX_AVAILABLE = True
except ImportError:
    pytmx = None  # type: ignore


# ============================================================
# QUERY-API
# ============================================================
def is_available() -> bool:
    """True wenn pytmx installiert + verwendbar."""
    return _PYTMX_AVAILABLE


def has_map(map_name: str, biome: str | None = None) -> bool:
    """True wenn fuer (biome, map_name) eine .tmx-Datei existiert.
    Sucht zuerst in assets/maps/<biome>/, dann in assets/maps/."""
    if not _PYTMX_AVAILABLE:
        return False
    return _find_map_path(map_name, biome) is not None


def _find_map_path(map_name: str, biome: str | None = None) -> Path | None:
    candidates = []
    if biome:
        candidates.append(MAPS_DIR / biome / f'{map_name}.tmx')
    candidates.append(MAPS_DIR / f'{map_name}.tmx')
    for p in candidates:
        if p.is_file():
            return p
    return None


# ============================================================
# LOAD + PARSE
# ============================================================
def load_map(map_name: str, biome: str | None = None) -> Any:
    """Laedt eine .tmx-Datei via pytmx. Returnt pytmx.TiledMap.

    Wirft FileNotFoundError wenn nicht gefunden, ImportError wenn pytmx fehlt.
    """
    if not _PYTMX_AVAILABLE:
        raise ImportError('pytmx nicht installiert')
    path = _find_map_path(map_name, biome)
    if path is None:
        raise FileNotFoundError(
            f'Map nicht gefunden: {map_name} (biome={biome})')
    # pytmx erwartet str-Pfad
    return pytmx.TiledMap(str(path))


# ============================================================
# CONVERT TMX → ENGINE-FORMAT
# ============================================================
def tmx_to_engine(tmx_data) -> dict:
    """Konvertiert ein TiledMap-Objekt in Engine-Daten.

    Returnt dict mit keys:
        grid:       DungeonGrid (mit FLOOR/WALL/etc.)
        spawns:     list[dict]   — spawn-points (player/npc/mob/boss/decor)
        decor:      list[dict]   — explicit decor objects
        regions:    list[dict]   — named regions/triggers
        meta:       dict         — map-properties (lighting, biome-override)

    Die Engine-Coordinaten passen direkt zu dungeon_gen.DungeonGrid:
        grid.tiles[cy][cx] in (VOID, FLOOR, WALL, DOOR, TRAP, SECRET)
    """
    from .dungeon_gen import DungeonGrid, VOID, FLOOR, WALL, DOOR, TRAP

    w = tmx_data.width
    h = tmx_data.height
    grid = DungeonGrid(w, h)

    # Default ist VOID (siehe DungeonGrid.__init__)
    # Layer-Mapping: erste passende Layer wins
    for layer in tmx_data.layers:
        layer_name = getattr(layer, 'name', '').lower()
        if not hasattr(layer, 'data'):
            continue
        for y in range(h):
            for x in range(w):
                gid = layer.data[y][x]
                if gid == 0:
                    continue
                # Layer-Name bestimmt Tile-Type
                if 'floor' in layer_name:
                    grid.tiles[y][x] = FLOOR
                elif 'wall' in layer_name:
                    grid.tiles[y][x] = WALL
                elif 'door' in layer_name:
                    grid.tiles[y][x] = DOOR
                elif 'trap' in layer_name:
                    grid.tiles[y][x] = TRAP

    # Spawns + Decor + Regions aus Object-Layers
    spawns: list[dict] = []
    decor_objects: list[dict] = []
    regions: list[dict] = []

    for layer in tmx_data.layers:
        if not hasattr(layer, '__iter__'):
            continue
        layer_name = getattr(layer, 'name', '').lower()
        for obj in layer:
            otype = getattr(obj, 'type', None) or getattr(obj, 'class', None) or ''
            entry = {
                'name':       getattr(obj, 'name', ''),
                'type':       otype,
                'x':          obj.x,
                'y':          obj.y,
                'width':      getattr(obj, 'width', 0),
                'height':     getattr(obj, 'height', 0),
                'rotation':   getattr(obj, 'rotation', 0),
                'properties': dict(getattr(obj, 'properties', {})),
            }
            if 'spawn' in layer_name or otype.startswith(('player_spawn',
                                                          'npc:', 'mob:',
                                                          'boss:')):
                spawns.append(entry)
            elif otype.startswith('decor:') or 'decor' in layer_name:
                decor_objects.append(entry)
            else:
                regions.append(entry)

    # Map-Properties (lighting-tint, biome-override, name, etc.)
    meta = dict(getattr(tmx_data, 'properties', {}))
    meta['width']      = w
    meta['height']     = h
    meta['tilewidth']  = tmx_data.tilewidth
    meta['tileheight'] = tmx_data.tileheight

    return {
        'grid':    grid,
        'spawns':  spawns,
        'decor':   decor_objects,
        'regions': regions,
        'meta':    meta,
    }


# ============================================================
# LIST + DIAGNOSTICS
# ============================================================
def list_maps() -> list[tuple[str, str]]:
    """Listet alle verfuegbaren .tmx-Files unter assets/maps/.
    Returnt Liste von (biome, map_name)-Tuples."""
    out: list[tuple[str, str]] = []
    if not MAPS_DIR.is_dir():
        return out
    for tmx in MAPS_DIR.rglob('*.tmx'):
        rel = tmx.relative_to(MAPS_DIR)
        parts = rel.parts
        if len(parts) >= 2:
            biome = parts[0]
            name = parts[-1].replace('.tmx', '')
        else:
            biome = ''
            name = parts[0].replace('.tmx', '')
        out.append((biome, name))
    return out


# ============================================================
# CLI
# ============================================================
if __name__ == '__main__':
    print(f'pytmx available: {_PYTMX_AVAILABLE}')
    maps = list_maps()
    print(f'\n{len(maps)} maps gefunden in {MAPS_DIR}:')
    for biome, name in maps:
        print(f'  [{biome}] {name}')
    if not maps:
        print('  (keine — Hand-crafted Maps via Tiled Editor speichern '
              'unter assets/maps/<biome>/<name>.tmx)')
