"""Asset-Validator (PLAN AA-08).

Startup-Check ob alle in `assets/sprite_manifest.json` referenzierten
Files (sprites, sounds) existieren.  Bei Fehler: Hard-Warn in Console
+ stiller Fallback (procedural-render).

Wird in `Game.__init__` aufgerufen.  Performance: I/O ein einziges Mal,
nicht pro Frame.
"""

import json
import os
import sys


def validate_assets(manifest_path='assets/sprite_manifest.json'):
    """Return list of missing-paths (empty = all OK).

    Update #171: Erkennt den Procedural-Only-Manifest-Status und skipt
    die Validation komplett wenn `status == 'deprecated'`.
    """
    if not os.path.isfile(manifest_path):
        return []   # Kein Manifest, keine Validierung noetig
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest = json.load(f)
    except Exception as e:
        return [f'failed to parse manifest: {e}']
    # Update #171: Deprecated/Procedural-Only-Manifest skippen
    if isinstance(manifest, dict) and manifest.get('status') == 'deprecated':
        return []
    missing = []
    base = os.path.dirname(manifest_path) or '.'
    # Nur ueber die `entries`-Liste iterieren (sicheres Schema).
    entries = manifest.get('entries', []) if isinstance(manifest, dict) else manifest
    if not isinstance(entries, list):
        return []
    for entry in entries:
        if isinstance(entry, str):
            path = entry
        elif isinstance(entry, dict):
            path = entry.get('path')
            if path is None:
                continue
        else:
            continue
        # Resolve relative to manifest-base
        if not os.path.isabs(path):
            path = os.path.join(base, path)
        if not os.path.isfile(path):
            missing.append(path)
    return missing


def validate_sounds(sounds_dir='Sounds'):
    """Light check ob der Sounds-Ordner existiert + paar erwartete Files."""
    if not os.path.isdir(sounds_dir):
        return ['Sounds/ directory missing']
    return []


def run_startup_validation():
    """Called from Game.__init__ — prints warnings, never raises."""
    issues = []
    issues += validate_assets()
    issues += validate_sounds()
    if not issues:
        return
    print('=' * 50, file=sys.stderr)
    print('Asset-Validator: ', file=sys.stderr)
    for issue in issues[:20]:
        print(f'  MISSING: {issue}', file=sys.stderr)
    if len(issues) > 20:
        print(f'  ...and {len(issues) - 20} more', file=sys.stderr)
    print('  Falling back to procedural-renders/silent-sfx.',
          file=sys.stderr)
    print('=' * 50, file=sys.stderr)
