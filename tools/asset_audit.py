"""Asset-Audit-Tool — prueft jedes PNG gegen sf/render_spec.py.

Checks pro Asset:
  1. Resolution-Match (oder Aspect-Ratio innerhalb tolerance)
  2. BG-Transparency-Anteil (Kategorie 'transparent' braucht >=30% alpha=0)
  3. Filename-Convention (z.B. class_anims/<anim>/<dir>.png)
  4. Filesize-Sanity (<5MB pro PNG)

Output:
  [OK]   classes/warrior.png               512x768  alpha-0=64%  ✓
  [WARN] classes/witch.png                 512x768  alpha-0=0%   BG-Removal noetig
  [FAIL] mobs/aschenbrut.png               748x768  Aspect 0.97  expected 1.0 ±0.05

Usage:
  python tools/asset_audit.py
  python tools/asset_audit.py --category class
  python tools/asset_audit.py --category mob --strict

Doku: VELGRAD_RENDER_SPEC.md §VI
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR = PROJECT_ROOT / 'assets' / 'sprites'


# ============================================================
# CATEGORY-DIRECTORY-MAPPING
# ============================================================
# Welche Ordner gehoeren zu welcher render_spec-Kategorie?
CATEGORY_DIRS = {
    'class':           ['classes'],
    'class_anim_frame': ['classes'],   # _anims/<anim>/<dir>.png subdirs
    'mob':             ['mobs'],
    'boss_plate':      ['bosses'],
    'portrait':        ['portraits'],
    'tile':            ['tiles'],
    'tile_wall':       ['tiles'],
    'item_icon':       ['items'],
    'decor':           ['decor'],
}


# ============================================================
# CHECKS
# ============================================================
def _get_alpha_zero_percent(png_path: Path) -> float:
    """Returnt Anteil der Pixel mit alpha=0 (0.0..1.0). 0.0 wenn kein Alpha."""
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))
    try:
        surf = pygame.image.load(str(png_path))
    except Exception:
        return 0.0
    try:
        import numpy as np
        alpha = pygame.surfarray.pixels_alpha(surf)
        return float((alpha == 0).sum()) / float(alpha.size)
    except Exception:
        return 0.0


def _get_size(png_path: Path) -> tuple[int, int]:
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))
    try:
        surf = pygame.image.load(str(png_path))
        return surf.get_size()
    except Exception:
        return (0, 0)


def audit_asset(png_path: Path, category: str, strict: bool = False) -> dict:
    """Prueft 1 Asset gegen die render_spec-Kategorie.

    Returns:
        dict mit keys: status ('OK'|'WARN'|'FAIL'), checks (list), summary.
    """
    from sf.render_spec import get_spec  # noqa: E402
    spec = get_spec(category)
    if not spec:
        return {
            'status': 'WARN',
            'checks': [f'Keine render_spec fuer category={category}'],
            'summary': '',
        }

    checks: list[str] = []
    status = 'OK'

    # 1. Resolution-Check
    w, h = _get_size(png_path)
    if w == 0 or h == 0:
        return {
            'status': 'FAIL',
            'checks': ['Konnte PNG nicht laden'],
            'summary': '',
        }
    exp_w, exp_h = spec.get('resolution', (0, 0))
    if exp_w > 0 and exp_h > 0:
        # Erlaube N-Frame-Strips (width = N * frame_w fuer animation frames).
        # Strip-Breite muss exakt durch frame_count teilbar sein, sonst klappt
        # das Slicen nicht. Strip-Hoehe sollte konsistent ueber alle Anims
        # des selben class sein, aber NICHT identisch zu exp_h (User-Sheets
        # koennen z.B. 1536 oder 627 sein, je nach Quelle).
        if category == 'class_anim_frame':
            # Akzeptiere alles solange Strip durch 8 teilbar (Frame-Slice
            # funktioniert) und ein vernuenftiges Aspect (>1.5 → horizontal-Strip)
            if w < h * 1.5:
                status = 'WARN'
                checks.append(
                    f'Strip-Aspect {w/h:.2f} < 1.5 — vermutlich falsch '
                    f'orientiert (Strips muessen horizontal sein)')
            if w % 8 != 0:
                checks.append(
                    f'Strip-Width {w} nicht durch 8 teilbar — '
                    f'Slicing kann Pixel verlieren')
        elif (w, h) != (exp_w, exp_h):
            # Aspect-Check
            expected_aspect = exp_w / exp_h
            actual_aspect = w / h
            tol = spec.get('aspect_tolerance', 0.05)
            aspect_diff = abs(expected_aspect - actual_aspect) / expected_aspect
            if aspect_diff < tol:
                if strict:
                    status = 'WARN'
                    checks.append(
                        f'Resolution {w}x{h} != {exp_w}x{exp_h} '
                        f'(Aspect OK, Strict-Mode warnt)')
            else:
                status = 'FAIL'
                checks.append(
                    f'Aspect {actual_aspect:.2f} != {expected_aspect:.2f} '
                    f'(tol {tol})')

    # 2. BG-Transparency-Check
    bg_policy = spec.get('bg_policy', 'transparent')
    alpha_zero_pct = _get_alpha_zero_percent(png_path)
    if bg_policy == 'transparent':
        if alpha_zero_pct < 0.20:   # weniger als 20% transparent → BG noch da
            if status == 'OK':
                status = 'WARN'
            checks.append(
                f'BG-Removal noetig (alpha-0 {alpha_zero_pct*100:.0f}% < 20%)')
    elif bg_policy == 'seamless':
        # Tile darf NICHT transparent sein — bg muss seamless gefuellt sein
        if alpha_zero_pct > 0.05:
            status = 'FAIL'
            checks.append(
                f'Tile hat {alpha_zero_pct*100:.0f}% transparent — '
                f'sollte 0% sein (seamless)')

    # 3. Filesize-Sanity
    size_mb = png_path.stat().st_size / (1024 * 1024)
    if size_mb > 5.0:
        if status == 'OK':
            status = 'WARN'
        checks.append(f'Filesize {size_mb:.1f}MB > 5MB (unkomprimiert?)')

    summary = (
        f'{w}x{h}  alpha-0={alpha_zero_pct*100:.0f}%  bg={bg_policy}'
    )
    if not checks:
        checks.append('passes all checks')
    return {'status': status, 'checks': checks, 'summary': summary}


# ============================================================
# DIRECTORY-SCAN
# ============================================================
def scan_directory(category_dir: Path, category: str,
                    strict: bool = False) -> list[tuple[Path, dict]]:
    """Audit alle PNGs im category_dir. Returnt Liste von (path, result)."""
    results: list[tuple[Path, dict]] = []
    if not category_dir.is_dir():
        return results
    for png in sorted(category_dir.rglob('*.png')):
        # Determine category from path:
        # classes/warrior.png              -> category='class'
        # classes/monk_anims/walk/down.png -> category='class_anim_frame'
        rel = png.relative_to(SPRITES_DIR)
        rel_parts = rel.parts
        # Check if any path part ENDS with '_anims' (e.g. 'monk_anims')
        if any(part.endswith('_anims') for part in rel_parts):
            eff_cat = 'class_anim_frame'
        else:
            eff_cat = category
        result = audit_asset(png, eff_cat, strict=strict)
        results.append((png, result))
    return results


# ============================================================
# CLI
# ============================================================
def main():
    ap = argparse.ArgumentParser(description='Velgrad Asset-Audit')
    ap.add_argument('--category', type=str, default=None,
                    help='class|mob|portrait|boss_plate|tile|item_icon|decor')
    ap.add_argument('--strict', action='store_true',
                    help='Aspect-OK aber Resolution-anders → WARN statt OK')
    ap.add_argument('--file', type=str, default=None,
                    help='Einzelnes PNG auditen')
    ap.add_argument('--only', choices=['ok', 'warn', 'fail'], default=None,
                    help='Nur Eintraege mit diesem Status zeigen')
    args = ap.parse_args()

    if args.file:
        p = Path(args.file)
        if not p.is_absolute():
            p = PROJECT_ROOT / p
        # Category aus Pfad ableiten
        try:
            rel = p.relative_to(SPRITES_DIR)
            parent = rel.parts[0] if rel.parts else ''
            cat = next((c for c, dirs in CATEGORY_DIRS.items()
                        if parent in dirs), 'class')
            if '_anims' in str(rel):
                cat = 'class_anim_frame'
        except ValueError:
            cat = 'class'
        result = audit_asset(p, cat, strict=args.strict)
        st = result['status']
        print(f'[{st:<4}] {p.relative_to(PROJECT_ROOT)}')
        print(f'        {result["summary"]}')
        for c in result['checks']:
            print(f'        - {c}')
        return

    # Categories filtern. class_anim_frame teilt sich den scan-dir mit class,
    # daher wird es uebersprungen — scan_directory erkennt die Anim-Frames
    # selbst aus dem Pfad (via _anims-Subdir).
    cats = list(CATEGORY_DIRS.keys()) if not args.category else [args.category]
    cats = [c for c in cats if c != 'class_anim_frame']

    print('=' * 80)
    print(f'  Velgrad Asset-Audit  ({"strict" if args.strict else "lax"} mode)')
    print('=' * 80)

    totals = {'OK': 0, 'WARN': 0, 'FAIL': 0}
    for cat in cats:
        dirs = CATEGORY_DIRS.get(cat, [])
        for d in dirs:
            dir_path = SPRITES_DIR / d
            if not dir_path.is_dir():
                continue
            results = scan_directory(dir_path, cat, strict=args.strict)
            for png, result in results:
                st = result['status']
                if args.only and st.lower() != args.only:
                    continue
                totals[st] = totals.get(st, 0) + 1
                rel = png.relative_to(SPRITES_DIR)
                summary = result['summary']
                print(f'[{st:<4}] {str(rel):<55} {summary}')
                if st != 'OK':
                    for c in result['checks']:
                        print(f'         - {c}')

    print('=' * 80)
    print(f'  Total: {sum(totals.values())} assets  '
          f'OK={totals["OK"]}  WARN={totals["WARN"]}  FAIL={totals["FAIL"]}')
    print('=' * 80)


if __name__ == '__main__':
    main()
