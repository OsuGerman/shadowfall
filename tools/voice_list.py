"""Listet alle Voices die in deinem ElevenLabs-Account verfuegbar sind.

Usage:
  python tools/voice_list.py                  # alle Voices
  python tools/voice_list.py --gender female  # nur weibliche
  python tools/voice_list.py --search german  # Name/Description-Search
  python tools/voice_list.py --premade        # nur Premade-Voices
  python tools/voice_list.py --my             # nur eigene/cloned Voices

Output pro Voice:
  <voice_id>  <name>  <gender>  <age>  <accent>  <description>

Damit kannst du Voice-IDs identifizieren und in
VELGRAD_VOICE_CASTING.md eintragen.
"""
from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.voice_config import load_api_key  # noqa: E402


VOICES_API = 'https://api.elevenlabs.io/v1/voices'


def fetch_voices(api_key: str) -> list[dict]:
    req = urllib.request.Request(
        VOICES_API,
        headers={'xi-api-key': api_key, 'Accept': 'application/json'},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('voices', [])
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')[:200]
        print(f'HTTP {e.code}: {body}', file=sys.stderr)
        sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--gender', choices=['male', 'female', 'neutral'])
    ap.add_argument('--search', type=str, default=None,
                    help='Case-insensitive Substring-Match auf name/description/labels')
    ap.add_argument('--premade', action='store_true',
                    help='Nur Premade-Voices (category=premade)')
    ap.add_argument('--my',      action='store_true',
                    help='Nur eigene/cloned/generated Voices')
    ap.add_argument('--json',    action='store_true',
                    help='JSON-Output statt Tabelle')
    args = ap.parse_args()

    api_key = load_api_key()
    voices = fetch_voices(api_key)

    # Filter
    def labels(v):
        return v.get('labels') or {}

    if args.gender:
        voices = [v for v in voices if labels(v).get('gender', '').lower() == args.gender]
    if args.premade:
        voices = [v for v in voices if v.get('category') == 'premade']
    if args.my:
        voices = [v for v in voices if v.get('category') in
                  ('cloned', 'generated', 'professional')]
    if args.search:
        s = args.search.lower()
        def matches(v):
            blob = ' '.join([
                v.get('name', ''),
                v.get('description', '') or '',
                json.dumps(labels(v), ensure_ascii=False),
            ]).lower()
            return s in blob
        voices = [v for v in voices if matches(v)]

    if args.json:
        print(json.dumps(voices, indent=2, ensure_ascii=False))
        return

    # Tabelle
    print(f'\n{len(voices)} Voice(s) gefunden:\n')
    print(f'{"voice_id":<25} {"name":<22} {"gender":<8} {"age":<10} {"accent":<14} description')
    print('-' * 130)
    for v in voices:
        lab = labels(v)
        vid    = v.get('voice_id', '')[:24]
        name   = v.get('name', '')[:21]
        gender = lab.get('gender', '')[:7]
        age    = lab.get('age', '')[:9]
        accent = lab.get('accent', '')[:13]
        desc   = (v.get('description') or lab.get('description') or '')[:60]
        cat    = v.get('category', '')
        print(f'{vid:<25} {name:<22} {gender:<8} {age:<10} {accent:<14} [{cat}] {desc}')

    print()
    print('Tipp: voice_id rauskopieren -> in VELGRAD_VOICE_CASTING.md eintragen.')
    print('Dann: python tools/voice_manifest_builder.py && python tools/voice_gen.py --dry-run')


if __name__ == '__main__':
    main()
