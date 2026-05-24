"""One-shot: reconcile sprite_manifest.json gegen die Disk.
Existierende PNGs in assets/sprites/<out_dir>/<id>.png werden auf
status='done' + file_path gesetzt, ohne sie zu regenerieren.
"""
from __future__ import annotations

import json
import os
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / 'assets' / 'sprite_manifest.json'
SPRITES = ROOT / 'assets' / 'sprites'

CAT_OUT = {
    'mob': 'mobs', 'class': 'classes', 'portrait': 'portraits',
    'boss_plate': 'bosses', 'tile': 'tiles', 'item_icon': 'items',
    'decor': 'decor', 'status_icon': 'status',
}


def main():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    marked_done = 0
    marked_missing = 0
    for e in data['entries']:
        cat = e['category']
        odir = CAT_OUT.get(cat)
        if not odir:
            continue
        p = SPRITES / odir / f'{e["id"]}.png'
        if p.is_file():
            rel = str(p.relative_to(ROOT)).replace(os.sep, '/')
            if e.get('status') != 'done' or e.get('file_path') != rel:
                e['status'] = 'done'
                e['file_path'] = rel
                marked_done += 1
        else:
            # File ist NICHT auf Disk (User-Loesch o.ae.) — Manifest darf
            # nicht weiter 'done' melden, sonst lügt das Registry.
            if e.get('status') == 'done':
                e['status'] = 'pending'
                e['file_path'] = None
                marked_missing += 1

    MANIFEST.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Reconciled: {marked_done} entries newly marked done')
    print(f'            {marked_missing} entries reverted to pending '
          f'(file was deleted)')

    pending = [e for e in data['entries'] if e['status'] == 'pending']
    done = [e for e in data['entries'] if e['status'] == 'done']
    failed = [e for e in data['entries'] if e['status'] == 'failed']
    print(f'Manifest: {len(done)} done, {len(pending)} pending, '
          f'{len(failed)} failed')
    print('Done per category:')
    for c, n in sorted(Counter(e['category'] for e in done).items()):
        print(f'  {c:<14} {n:>3}')


if __name__ == '__main__':
    main()
