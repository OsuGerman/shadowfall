"""ElevenLabs Batch-Voice-Generator.

Liest sounds/voice/voice_manifest.json und generiert pro Entry eine
MP3-Datei via ElevenLabs-API. Idempotent: bereits generierte Lines
werden übersprungen.

Usage:
  python tools/voice_gen.py --dry-run        # nur Kosten + Plan zeigen
  python tools/voice_gen.py                  # los, alles pending
  python tools/voice_gen.py --npc korven     # nur Korven-Lines
  python tools/voice_gen.py --limit 10       # nur 10 Lines (Test-Run)
  python tools/voice_gen.py --redo-failed    # failed Stati neu versuchen

Was das Script tut:
  1. Manifest lesen, alle 'pending' Lines finden
  2. Pro Line: ElevenLabs-API mit voice_id + text + settings rufen
  3. Audio-Bytes empfangen, als sounds/voice/<npc>/<line_id>.mp3 ablegen
  4. Manifest-Status auf 'done' setzen, Cost-Tracking aktualisieren
  5. Bei Fehler: Status 'failed', Retry mit Backoff
  6. Am Ende: sf/voice_registry.py regenerieren

Rate-Limiting:
  - Pro Sekunde max 2 Requests (sehr konservativ).
  - HTTP 429 -> exponentielles Backoff bis 30s.
  - HTTP 401/403 -> Abbruch mit Hinweis (Key-Fehler).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

# Package-Pfad
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.voice_config import (  # noqa: E402
    load_api_key, apply_pronunciation,
    VOICE_DIR, VOICE_MANIFEST_JSON, VOICE_REGISTRY_PY,
    TTS_MODEL, OUTPUT_FORMAT, plan_char_budget, cost_estimate_eur,
)

try:
    import urllib.request
    import urllib.error
except ImportError as e:
    print(f'urllib import failed: {e}', file=sys.stderr)
    sys.exit(1)


# ============================================================
# CONSTANTS
# ============================================================
ELEVENLABS_API = 'https://api.elevenlabs.io/v1/text-to-speech/{voice_id}'
REQUEST_INTERVAL_SEC = 0.5    # 2 req/s
MAX_BACKOFF_SEC = 30.0
MAX_RETRIES = 4


# ============================================================
# MANIFEST I/O
# ============================================================
def load_manifest() -> dict:
    if not VOICE_MANIFEST_JSON.is_file():
        print(f'Manifest fehlt: {VOICE_MANIFEST_JSON}', file=sys.stderr)
        print('  -> erst `python tools/voice_manifest_builder.py` ausführen',
              file=sys.stderr)
        sys.exit(2)
    return json.loads(VOICE_MANIFEST_JSON.read_text(encoding='utf-8'))


def save_manifest(manifest: dict) -> None:
    VOICE_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


# ============================================================
# ELEVENLABS API-CALL
# ============================================================
def generate_line(api_key: str, entry: dict) -> bytes | None:
    """POST an ElevenLabs, returnt MP3-Bytes oder None bei dauerhaftem Fehler."""
    voice_id = entry['voice_id']
    if not voice_id:
        return None

    payload = dict(
        text=apply_pronunciation(entry['text']),
        model_id=TTS_MODEL,
        voice_settings=dict(
            stability=entry['stability'],
            similarity_boost=entry['similarity_boost'],
            style=entry['style'],
            use_speaker_boost=True,
        ),
    )

    url = ELEVENLABS_API.format(voice_id=voice_id) + f'?output_format={OUTPUT_FORMAT}'
    body = json.dumps(payload).encode('utf-8')
    headers = {
        'xi-api-key':  api_key,
        'Content-Type': 'application/json',
        'Accept':       'audio/mpeg',
    }

    # Sicherheits-Check: API-Key darf keinerlei Whitespace/Newlines enthalten
    # (sonst leaked er in HTTP-Header-Errors). Wenn doch -> Abbruch ohne
    # ihn auszugeben.
    if not api_key or any(c.isspace() or ord(c) < 32 for c in api_key):
        print('\n  FEHLER: API-Key ist ungueltig (Whitespace/Control-Chars). '
              'ElevenLabs.txt mit nur dem Key neu schreiben.', file=sys.stderr)
        return None

    backoff = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(url, data=body, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                print(f'\n  AUTH-FEHLER {e.code}: Key ungültig / Plan-Limit.',
                      file=sys.stderr)
                return None
            if e.code == 429:
                # Rate-Limit -> Backoff
                wait = min(backoff, MAX_BACKOFF_SEC)
                print(f'\n  429 Rate-Limit, warte {wait:.1f}s …',
                      file=sys.stderr)
                time.sleep(wait)
                backoff *= 2
                continue
            err = e.read().decode('utf-8', errors='ignore')[:200]
            print(f'\n  HTTP {e.code} bei {entry["line_id"]}: {err}',
                  file=sys.stderr)
            if attempt >= MAX_RETRIES:
                return None
            time.sleep(backoff)
            backoff *= 2
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'\n  Netzwerk-Fehler bei {entry["line_id"]}: {e}',
                  file=sys.stderr)
            if attempt >= MAX_RETRIES:
                return None
            time.sleep(backoff)
            backoff *= 2
    return None


# ============================================================
# REGISTRY-GENERIERUNG (sf/voice_registry.py)
# ============================================================
def regenerate_registry(manifest: dict) -> None:
    """Schreibt sf/voice_registry.py aus dem aktuellen Manifest-Stand."""
    done = [e for e in manifest['entries'] if e.get('status') == 'done']
    if not done:
        return

    # Pro (npc, category): Liste der Pfade
    pools: dict[tuple[str, str], list[str]] = {}
    for e in done:
        key = (e['npc'], e['category'])
        rel_path = f"sounds/voice/{e['npc']}/{e['line_id']}.mp3"
        pools.setdefault(key, []).append(rel_path)

    lines = [
        '"""Auto-generiert von tools/voice_gen.py.',
        '',
        'Voice-Line-Registry: pro (npc, category) -> Liste von MP3-Pfaden.',
        'Nicht von Hand editieren — wird beim nächsten voice_gen-Run überschrieben.',
        '"""',
        'from __future__ import annotations',
        '',
        'import random',
        '',
        '',
        'VOICE_POOLS: dict[tuple[str, str], list[str]] = {',
    ]
    for key in sorted(pools):
        paths = sorted(pools[key])
        lines.append(f'    {key!r}: [')
        for p in paths:
            lines.append(f'        {p!r},')
        lines.append('    ],')
    lines.append('}')
    lines.append('')
    lines.append('# Per-Pool letzten Index speichern (Voice-Variation-System)')
    lines.append('_LAST_INDEX: dict[tuple[str, str], int] = {}')
    lines.append('')
    lines.append('')
    lines.append('def pick_voice(npc: str, category: str) -> str | None:')
    lines.append('    """Zieht eine MP3 aus dem Pool, wiederholt nie zweimal in Folge."""')
    lines.append('    pool = VOICE_POOLS.get((npc, category))')
    lines.append('    if not pool:')
    lines.append('        return None')
    lines.append('    last = _LAST_INDEX.get((npc, category), -1)')
    lines.append('    candidates = [i for i in range(len(pool)) if i != last]')
    lines.append('    if not candidates:')
    lines.append('        candidates = list(range(len(pool)))')
    lines.append('    idx = random.choice(candidates)')
    lines.append('    _LAST_INDEX[(npc, category)] = idx')
    lines.append('    return pool[idx]')
    lines.append('')

    VOICE_REGISTRY_PY.parent.mkdir(parents=True, exist_ok=True)
    VOICE_REGISTRY_PY.write_text('\n'.join(lines), encoding='utf-8')


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true',
                    help='Nichts generieren — nur Kosten + Plan-Check.')
    ap.add_argument('--npc', type=str, default=None,
                    help='Nur Lines für diesen NPC-Key (z.B. korven).')
    ap.add_argument('--limit', type=int, default=None,
                    help='Maximal N Lines generieren (Test-Run).')
    ap.add_argument('--redo-failed', action='store_true',
                    help='Vorher failed Lines wieder auf pending setzen.')
    args = ap.parse_args()

    manifest = load_manifest()

    # Optional: failed -> pending
    if args.redo_failed:
        cnt = 0
        for e in manifest['entries']:
            if e.get('status') == 'failed':
                e['status'] = 'pending'
                cnt += 1
        print(f'Reset {cnt} failed -> pending')

    # Filter
    pending = [e for e in manifest['entries'] if e.get('status') == 'pending']
    if args.npc:
        pending = [e for e in pending if e['npc'] == args.npc]
    if args.limit:
        pending = pending[:args.limit]

    # Voice-IDs Check
    no_voice = [e for e in pending if not e.get('voice_id')]
    has_voice = [e for e in pending if e.get('voice_id')]

    # Cost-Schätzung
    total_chars = sum(len(e['text']) for e in has_voice)
    cost = cost_estimate_eur(total_chars)
    budget = plan_char_budget()

    print('='*60)
    print('VOICE-GEN — DRY-RUN' if args.dry_run else 'VOICE-GEN — START')
    print('='*60)
    print(f'  Pending insgesamt:        {len(manifest["entries"]):>6}')
    print(f'  Pending mit voice_id:     {len(has_voice):>6}')
    print(f'  Pending ohne voice_id:    {len(no_voice):>6}  (übersprungen)')
    print(f'  Zeichen zu generieren:    {total_chars:>6,}')
    print(f'  Plan-Budget pro Monat:    {budget:>6,} chars')
    print(f'  Kosten-Schätzung:         {cost:.2f} EUR')
    if no_voice:
        unique_npcs = sorted({e["npc"] for e in no_voice})
        print(f'  NPCs ohne Voice-ID:       {", ".join(unique_npcs)}')
    print('='*60)

    if args.dry_run:
        return
    if not has_voice:
        print('Nichts zu generieren.')
        return

    # API-Key laden (erst hier, damit dry-run keinen Key braucht)
    try:
        api_key = load_api_key()
    except RuntimeError as e:
        print(f'\nFEHLER: {e}', file=sys.stderr)
        sys.exit(3)

    # Generieren
    done_count = 0
    fail_count = 0
    chars_used = 0
    for i, entry in enumerate(has_voice, 1):
        out_path = VOICE_DIR / entry['npc'] / f'{entry["line_id"]}.mp3'
        if out_path.exists() and entry.get('status') == 'done':
            continue

        out_path.parent.mkdir(parents=True, exist_ok=True)
        print(f'  [{i:>4}/{len(has_voice)}] {entry["line_id"]:<50} '
              f'({len(entry["text"]):>3} chars)', end=' ', flush=True)

        t0 = time.time()
        audio = generate_line(api_key, entry)
        if audio is None:
            entry['status'] = 'failed'
            fail_count += 1
            print('FAIL')
        else:
            out_path.write_bytes(audio)
            entry['status'] = 'done'
            done_count += 1
            chars_used += len(entry['text'])
            print(f'ok ({time.time()-t0:.1f}s, {len(audio)//1024} KiB)')

        # Manifest speichern alle 5 Lines (Crash-Safety)
        if i % 5 == 0:
            save_manifest(manifest)

        # Rate-Limit-Spacer
        time.sleep(REQUEST_INTERVAL_SEC)

    # Manifest final speichern
    save_manifest(manifest)

    # Registry regenerieren
    regenerate_registry(manifest)

    print('='*60)
    print(f'  Done:     {done_count}')
    print(f'  Failed:   {fail_count}')
    print(f'  Chars:    {chars_used:,}')
    print(f'  Kosten:   {cost_estimate_eur(chars_used):.2f} EUR (Schätzung)')
    print(f'  Output:   {VOICE_DIR}')
    print(f'  Registry: {VOICE_REGISTRY_PY}')
    print('='*60)


if __name__ == '__main__':
    main()
