"""Post-Generation-Pipeline: BG-Removal + Audit nach Scenario.gg-Batch.

Aufruf nach jedem `sprite_gen.py --category <cat>`-Lauf damit die
transparent-BG-Kategorien (mob/class/item/decor/status) sofort sauber
in der Engine ankommen.  Idempotent — kann mehrfach laufen.

Usage:
    python tools/_post_gen_pipeline.py <category>
    python tools/_post_gen_pipeline.py all

Wo <category> ein Render-Spec-Key ist (mob/class/decor/item_icon/
status_icon/portrait/boss_plate/tile).  Categories mit bg_policy !=
'transparent' werden nur audited, nicht postprocessed.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SPRITES = ROOT / 'assets' / 'sprites'


CAT_TO_DIR = {
    'mob': 'mobs',
    'class': 'classes',
    'portrait': 'portraits',
    'boss_plate': 'bosses',
    'tile': 'tiles',
    'item_icon': 'items',
    'decor': 'decor',
    'status_icon': 'status',
}


def _postprocess_dir(dir_name: str) -> None:
    """Ruf sprite_postprocess.py auf einen Ordner an."""
    cli_key = {'mobs': 'mob', 'classes': 'class', 'items': 'item',
                'decor': 'decor', 'status': 'status'}.get(dir_name)
    if not cli_key:
        print(f'  [skip] {dir_name}/ — keine transparent-Policy')
        return
    cmd = [
        sys.executable, str(ROOT / 'tools' / 'sprite_postprocess.py'),
        '--category', cli_key, '--threshold', '40', '--feather', '10',
    ]
    print(f'  postprocess {dir_name}/ ...')
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        # nur die summary-Zeile durchreichen
        for line in res.stdout.splitlines()[-3:]:
            print(f'    {line}')
    else:
        print(f'  [warn] postprocess returned {res.returncode}')
        print(res.stderr[:500])


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    cat = sys.argv[1]
    if cat == 'all':
        cats = list(CAT_TO_DIR.keys())
    else:
        cats = [cat]

    from sf.render_spec import get_bg_policy

    for c in cats:
        dirn = CAT_TO_DIR.get(c)
        if not dirn:
            print(f'[err] unknown category: {c}')
            continue
        policy = get_bg_policy(c)
        if policy == 'transparent':
            _postprocess_dir(dirn)
        else:
            print(f'  [skip] {c} bg_policy={policy} — Background bleibt erhalten')


if __name__ == '__main__':
    sys.path.insert(0, str(ROOT))
    main()
