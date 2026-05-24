"""One-Command-Biome-Tile-Pipeline (Update #173).

Wenn du einen neuen AI-generierten Floor-Tile fuer ein Biom hast, drop ihn
in `assets/sprites/tiles/` und run dieses Tool — es macht alles auf
einmal:

  1. Source-Image auf 512×512 normalisieren (Pygame smoothscale)
  2. 4 Variants generieren (a/b/c/d via rotation + tint-shifts)
  3. Wall-Tile generieren (biom-spezifischer Algorithm aus wall_from_floor)
  4. 16-Mask-Set via workflow_texture_tiler procedural baken
  5. sf/sprite_registry.py die neuen IDs eintragen
  6. sf/sprites.py TILE_VARIANT_MAP + TILE_WALL_MAP + TILE_SPRITE_ALIAS
     updaten (nur die zugewiesene Biom-Zeile)

Usage:
  # Mit konkreter Source-Datei:
  python tools/process_biome_tile.py --biome frost --source frost_drop.png

  # Wenn das Source-File schon mit korrektem Namen in tiles/ liegt:
  python tools/process_biome_tile.py --biome frost
    (sucht assets/sprites/tiles/frost_floor_a.png oder <biome>_*.png)

  # Dry-Run (zeigt was es machen wuerde, ohne zu schreiben):
  python tools/process_biome_tile.py --biome lava --source x.png --dry-run

Doku: VELGRAD_RENDER_SPEC.md (tile category) + VELGRAD_WORKFLOWS_BIBEL.md
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TILES_DIR = PROJECT_ROOT / 'assets' / 'sprites' / 'tiles'


# ============================================================
# BIOM-LISTE (muss zu sf/sprites.py + sf/render_spec.py passen)
# ============================================================
BIOMES = ['crypt', 'frost', 'lava', 'swamp', 'astral', 'desert', 'town',
           'wound_salt', 'wound_ash', 'wound_hollow', 'hollow_word']


# ============================================================
# STEP 1: Normalize + 4 Variants
# ============================================================
def normalize_and_variants(biome: str, source_path: Path,
                            target_size: int = 512) -> list[Path]:
    """Skaliert Source auf target_size×target_size + erzeugt a/b/c/d.

    Returnt Liste der erzeugten Variant-Paths.
    """
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))
    import numpy as np

    if not source_path.is_file():
        raise FileNotFoundError(f'Source nicht gefunden: {source_path}')

    src = pygame.image.load(str(source_path))
    sw, sh = src.get_size()
    print(f'  Source: {source_path.name} ({sw}x{sh})')
    src_scaled = pygame.transform.smoothscale(
        src, (target_size, target_size))

    out_paths = []

    # Variant A: Original
    pa = TILES_DIR / f'{biome}_floor_a.png'
    pygame.image.save(src_scaled, str(pa))
    out_paths.append(pa)

    # Variant B: 90° + leichter blue-shift
    img = pygame.transform.rotate(src_scaled, 90)
    arr = pygame.surfarray.pixels3d(img).astype(np.float32)
    arr[..., 2] = np.clip(arr[..., 2] + 8, 0, 255)
    arr[..., 0] = np.clip(arr[..., 0] - 4, 0, 255)
    arr = arr.astype(np.uint8)
    out = pygame.Surface((target_size, target_size))
    pygame.surfarray.blit_array(out, arr)
    pb = TILES_DIR / f'{biome}_floor_b.png'
    pygame.image.save(out, str(pb))
    out_paths.append(pb)

    # Variant C: 180° + leichter brown-shift
    img = pygame.transform.rotate(src_scaled, 180)
    arr = pygame.surfarray.pixels3d(img).astype(np.float32)
    arr[..., 0] = np.clip(arr[..., 0] + 8, 0, 255)
    arr[..., 2] = np.clip(arr[..., 2] - 5, 0, 255)
    arr = arr.astype(np.uint8)
    out = pygame.Surface((target_size, target_size))
    pygame.surfarray.blit_array(out, arr)
    pc = TILES_DIR / f'{biome}_floor_c.png'
    pygame.image.save(out, str(pc))
    out_paths.append(pc)

    # Variant D: 270° + slight darken
    img = pygame.transform.rotate(src_scaled, 270)
    arr = pygame.surfarray.pixels3d(img).astype(np.float32) * 0.92
    arr = np.clip(arr, 0, 255).astype(np.uint8)
    out = pygame.Surface((target_size, target_size))
    pygame.surfarray.blit_array(out, arr)
    pd = TILES_DIR / f'{biome}_floor_d.png'
    pygame.image.save(out, str(pd))
    out_paths.append(pd)

    return out_paths


# ============================================================
# STEP 2: Wall via wall_from_floor.py
# ============================================================
def generate_wall(biome: str) -> Path:
    """Ruft tools/wall_from_floor.py mit BIOME_FLOOR_SOURCE-Update auf."""
    from tools.wall_from_floor import (
        BIOME_FLOOR_SOURCE, generate_wall as _gen_wall,
    )
    # Override BIOME_FLOOR_SOURCE damit auf <biome>_floor_a.png zeigt
    BIOME_FLOOR_SOURCE[biome] = f'{biome}_floor_a.png'

    floor_path = TILES_DIR / f'{biome}_floor_a.png'
    out_path = TILES_DIR / f'{biome}_wall_w.png'
    ok = _gen_wall(biome, floor_path, out_path)
    if not ok:
        raise RuntimeError(f'Wall-Generation fuer {biome} fehlgeschlagen')
    return out_path


# ============================================================
# STEP 3: 16-Mask-Set via workflow_texture_tiler.py procedural
# ============================================================
def bake_masks(biome: str) -> int:
    """Ruft workflow_texture_tiler procedural fuer das Biom. Returnt Anzahl der
    geschriebenen Mask-Files."""
    # Direkter Import statt subprocess
    from tools.workflow_texture_tiler import TextureTilerWorkflow
    wf = TextureTilerWorkflow(biome=biome, mode='procedural', cell_size=128)
    result = wf.run()
    if result['status'] != 'success':
        raise RuntimeError(
            f'Mask-Bake fuer {biome} fehlgeschlagen: {result.get("error")}')
    return len(result['outputs'])


# ============================================================
# STEP 4: sprite_registry.py update
# ============================================================
def update_sprite_registry(biome: str, dry_run: bool = False) -> None:
    """Fuegt die 5 neuen Eintraege (a/b/c/d + wall) in sf/sprite_registry.py."""
    reg_path = PROJECT_ROOT / 'sf' / 'sprite_registry.py'
    new_entries = [
        f"    '{biome}_floor_a': 'assets/sprites/tiles/{biome}_floor_a.png',",
        f"    '{biome}_floor_b': 'assets/sprites/tiles/{biome}_floor_b.png',",
        f"    '{biome}_floor_c': 'assets/sprites/tiles/{biome}_floor_c.png',",
        f"    '{biome}_floor_d': 'assets/sprites/tiles/{biome}_floor_d.png',",
        f"    '{biome}_wall_w':  'assets/sprites/tiles/{biome}_wall_w.png',",
    ]
    txt = reg_path.read_text(encoding='utf-8')
    if f"'{biome}_floor_a'" in txt:
        print(f'  sprite_registry: {biome} bereits registriert, skip')
        return
    # Insertion-Point: vor dem schliessenden "}"
    marker_lines = []
    for ln in txt.splitlines():
        marker_lines.append(ln)
    # Find last line that starts with "    '..': '..'" then insert before "}"
    insert_idx = None
    for i in range(len(marker_lines) - 1, -1, -1):
        if marker_lines[i].strip() == '}':
            insert_idx = i
            break
    if insert_idx is None:
        print('  WARNUNG: sprite_registry konnte nicht geparst werden', file=sys.stderr)
        return
    new_lines = marker_lines[:insert_idx] + new_entries + marker_lines[insert_idx:]
    new_txt = '\n'.join(new_lines)
    if dry_run:
        print(f'  sprite_registry (DRY-RUN): wuerde {len(new_entries)} Eintraege adden')
        return
    reg_path.write_text(new_txt, encoding='utf-8')
    print(f'  sprite_registry: {len(new_entries)} Eintraege fuer {biome} ergaenzt')


# ============================================================
# STEP 5: sprites.py TILE_VARIANT_MAP / TILE_WALL_MAP / TILE_SPRITE_ALIAS
# ============================================================
def update_sprites_maps(biome: str, dry_run: bool = False) -> None:
    """Update TILE_VARIANT_MAP + TILE_WALL_MAP fuer das Biom.
    TILE_SPRITE_ALIAS wird auch aktualisiert auf <biome>_floor_a damit
    der Single-Tile-Fallback ebenfalls den neuen Tile findet.

    Aenderungen sind idempotent — wenn bereits richtig gesetzt, no-op.
    """
    sprites_path = PROJECT_ROOT / 'sf' / 'sprites.py'
    txt = sprites_path.read_text(encoding='utf-8')

    changes = 0
    new_alias = f"    '{biome}':"
    if new_alias + f"        '{biome}_floor_a'," in txt:
        pass   # already configured

    # 1. TILE_SPRITE_ALIAS — point biome at <biome>_floor_a
    import re
    alias_pattern = re.compile(
        rf"('{biome}':\s*)'[^']*'", re.MULTILINE)
    new_txt = alias_pattern.sub(
        rf"\1'{biome}_floor_a'", txt, count=1)
    if new_txt != txt:
        txt = new_txt
        changes += 1

    # 2. TILE_VARIANT_MAP — add 'biome': ['<biome>_floor_a'] entry
    if f"'{biome}':" not in _extract_block(txt, 'TILE_VARIANT_MAP'):
        # Add line before closing brace
        txt = _add_to_dict(
            txt, 'TILE_VARIANT_MAP',
            f"    '{biome}':   ['{biome}_floor_a'],")
        changes += 1

    # 3. TILE_WALL_MAP — add 'biome': '<biome>_wall_w'
    if f"'{biome}':" not in _extract_block(txt, 'TILE_WALL_MAP'):
        txt = _add_to_dict(
            txt, 'TILE_WALL_MAP',
            f"    '{biome}':        '{biome}_wall_w',")
        changes += 1

    if dry_run:
        print(f'  sprites.py (DRY-RUN): {changes} Maps wuerden geupdated')
        return
    sprites_path.write_text(txt, encoding='utf-8')
    print(f'  sprites.py: {changes} Maps fuer {biome} aktualisiert')


def _extract_block(text: str, dict_name: str) -> str:
    """Extrahiert den text-Inhalt zwischen 'NAME = {' und '}'."""
    start_marker = f'{dict_name} = {{'
    si = text.find(start_marker)
    if si < 0:
        return ''
    ei = text.find('\n}', si)
    if ei < 0:
        return ''
    return text[si:ei]


def _add_to_dict(text: str, dict_name: str, entry_line: str) -> str:
    """Fuegt eine Zeile vor dem schliessenden '}' eines dict-Literals ein."""
    start_marker = f'{dict_name} = {{'
    si = text.find(start_marker)
    if si < 0:
        return text
    # Find matching closing '}' at start-of-line
    ei = text.find('\n}', si)
    if ei < 0:
        return text
    return text[:ei] + '\n' + entry_line + text[ei:]


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description='One-Command-Biome-Tile-Pipeline')
    ap.add_argument('--biome', required=True, choices=BIOMES)
    ap.add_argument('--source', type=str, default=None,
                    help='Source-PNG (absolut oder relativ). Falls leer, '
                         'wird <biome>_drop.png oder das erste passende '
                         'unbekannte PNG im tiles/-Folder genutzt.')
    ap.add_argument('--no-variants', action='store_true',
                    help='Skip Variant-Generation (nur Wall + Masks)')
    ap.add_argument('--no-wall', action='store_true',
                    help='Skip Wall-Generation')
    ap.add_argument('--no-masks', action='store_true',
                    help='Skip Mask-Bake')
    ap.add_argument('--no-engine-update', action='store_true',
                    help='Skip sprite_registry + sprites.py Updates')
    ap.add_argument('--dry-run', action='store_true')
    args = ap.parse_args()

    # Source bestimmen
    if args.source:
        src = Path(args.source)
        if not src.is_absolute():
            src = PROJECT_ROOT / src
            if not src.is_file():
                src = Path(args.source)   # absoluter Fallback
    else:
        # Suche im tiles/-Folder nach moeglichen Source-Files
        candidates = [
            TILES_DIR / f'{args.biome}_drop.png',
            TILES_DIR / f'{args.biome}_source.png',
            TILES_DIR / f'{args.biome}_new.png',
        ]
        src = next((p for p in candidates if p.is_file()), None)
        if src is None:
            print('Keine Source angegeben + keine Default-Datei gefunden.')
            print(f'  Erwartet: --source <PNG> ODER eines von:')
            for c in candidates:
                print(f'    {c.relative_to(PROJECT_ROOT)}')
            return

    print('=' * 60)
    print(f'  Biome-Tile-Pipeline: {args.biome}')
    print(f'  Source: {src}')
    print('=' * 60)

    if not args.no_variants:
        print('\n[1/4] Normalize + 4 Variants')
        if args.dry_run:
            print('  (DRY-RUN) wuerde a/b/c/d generieren')
        else:
            variants = normalize_and_variants(args.biome, src)
            for v in variants:
                print(f'  ✓ {v.relative_to(PROJECT_ROOT)}')

    if not args.no_wall:
        print('\n[2/4] Wall-Tile via wall_from_floor')
        if args.dry_run:
            print(f'  (DRY-RUN) wuerde {args.biome}_wall_w.png generieren')
        else:
            try:
                wall_path = generate_wall(args.biome)
                print(f'  ✓ {wall_path.relative_to(PROJECT_ROOT)}')
            except Exception as e:
                print(f'  FAIL: {e}', file=sys.stderr)

    if not args.no_masks:
        print('\n[3/4] 16-Mask-Set via texture_tiler procedural')
        if args.dry_run:
            print('  (DRY-RUN) wuerde 16 mask-PNGs baken')
        else:
            try:
                count = bake_masks(args.biome)
                print(f'  ✓ {count} Mask-PNGs')
            except Exception as e:
                print(f'  FAIL: {e}', file=sys.stderr)

    if not args.no_engine_update:
        print('\n[4/4] sprite_registry + sprites.py update')
        update_sprite_registry(args.biome, dry_run=args.dry_run)
        update_sprites_maps(args.biome, dry_run=args.dry_run)

    print('\n' + '=' * 60)
    print(f'  Pipeline-Fertig fuer Biom: {args.biome}')
    print('=' * 60)


if __name__ == '__main__':
    main()
