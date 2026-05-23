"""Listet alle in deinem Scenario.gg-Account verfuegbaren Models.

Usage:
  python tools/scenario_list_models.py
  python tools/scenario_list_models.py --search "fantasy"
  python tools/scenario_list_models.py --search "dark"
  python tools/scenario_list_models.py --search "character"
  python tools/scenario_list_models.py --my              # nur eigene Models
  python tools/scenario_list_models.py --public          # nur Stock-Public-Models

Output zeigt: Model-ID + Name + Type + Tags.
Damit kannst du den passenden POE2-Style-Stock entscheiden und in
VELGRAD_SPRITE_BIBEL.md / sprite_gen.py die modelId einsetzen.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.scenario_config import API_BASE, auth_header  # noqa: E402


def fetch_models(privacy: str | None = None, all_pages: bool = False) -> list[dict]:
    """GET /v1/models. Server-side search funktioniert nicht zuverlaessig —
    wir paginieren komplett und filtern clientseitig."""
    all_models: list[dict] = []
    next_page = None
    max_pages = 30 if all_pages else 3
    pages = 0
    while pages < max_pages:
        url = f'{API_BASE}/models?paginationSize=100'
        if privacy:
            url += f'&privacy={privacy}'
        if next_page:
            url += f'&paginationToken={next_page}'
        req = urllib.request.Request(url, headers=auth_header(), method='GET')
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')[:300]
            print(f'HTTP {e.code}: {body}', file=sys.stderr)
            break
        models = data.get('models', data.get('data', []))
        all_models.extend(models)
        next_page = data.get('nextPaginationToken') or data.get('nextPage')
        pages += 1
        if not next_page or not models:
            break
    return all_models


def filter_models(models: list[dict], terms: list[str]) -> list[dict]:
    """Client-seitiger Filter: Modell matched wenn IRGENDEIN term in Name
    oder Tags vorkommt (case-insensitive)."""
    if not terms:
        return models
    terms_lc = [t.lower() for t in terms]
    out = []
    for m in models:
        haystack = (
            (m.get('name') or '') + ' ' +
            ' '.join(str(t) for t in (m.get('tags') or [])) + ' ' +
            (m.get('description') or '')
        ).lower()
        if any(t in haystack for t in terms_lc):
            out.append(m)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--search', type=str, default=None,
                    help='Search filter (z.B. "fantasy", "dark", "character")')
    ap.add_argument('--my', action='store_true', help='Nur eigene private Models')
    ap.add_argument('--public', action='store_true', help='Nur Stock-Public-Models')
    ap.add_argument('--platform', action='store_true',
                    help='Nur Scenario-Platform-Models (kuratiert)')
    ap.add_argument('--limit', type=int, default=50)
    ap.add_argument('--json', action='store_true', help='JSON statt Tabelle')
    args = ap.parse_args()

    privacy = None
    if args.my:
        privacy = 'private'
    elif args.public:
        privacy = 'public'
    elif args.platform:
        privacy = 'platform'

    models = fetch_models(privacy=privacy, all_pages=True)
    if args.search:
        terms = [t.strip() for t in args.search.split(',') if t.strip()]
        models = filter_models(models, terms)
    if args.limit and len(models) > args.limit:
        models = models[:args.limit]

    if args.json:
        print(json.dumps(models, indent=2, ensure_ascii=False))
        return

    if not models:
        print('Keine Models gefunden. Pruefen ob Account Models hat.')
        print('Tipp: Gehe zu https://app.scenario.com/models — dort siehst du')
        print('  Public-Models die du in deinen Account ziehen kannst.')
        return

    print(f'\n{len(models)} Models gefunden:\n')
    print(f'{"id":<48} {"name":<32} {"type":<14} tags')
    print('-' * 130)
    for m in models:
        mid   = (m.get('id') or m.get('modelId', ''))[:47]
        name  = (m.get('name') or '')[:31]
        mtype = (m.get('type') or m.get('modelType') or '')[:13]
        tags = m.get('tags') or []
        if isinstance(tags, list):
            tag_str = ', '.join(str(t) for t in tags[:4])
        else:
            tag_str = str(tags)[:40]
        print(f'{mid:<48} {name:<32} {mtype:<14} {tag_str}')

    print()
    print('Tipp: Kopiere die Model-ID und uebergib sie sprite_gen.py:')
    print('  python tools/sprite_gen.py --model <model_id> --target salzhueter_brut')


if __name__ == '__main__':
    main()
