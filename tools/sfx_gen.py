"""ElevenLabs Sound-Effects Batch-Generator.

Parst VELGRAD_SFX_BIBEL.md, extrahiert die `id "prompt"` Eintraege
aus den Code-Bloecken, und generiert pro SFX eine MP3 via ElevenLabs
Sound-Effects-API (POST /v1/sound-generation).

Usage:
  python tools/sfx_gen.py --dry-run         # Kosten + Coverage anzeigen
  python tools/sfx_gen.py                   # alle pending SFX
  python tools/sfx_gen.py --section ui      # nur Sektion I (UI)
  python tools/sfx_gen.py --section combat  # nur Sektion II
  python tools/sfx_gen.py --section skills  # nur Sektion III
  python tools/sfx_gen.py --section monster # nur Sektion IV
  python tools/sfx_gen.py --section boss    # nur Sektion V
  python tools/sfx_gen.py --section cinematic
  python tools/sfx_gen.py --section ambience  # NUR Stable Audio - hier nicht generieren
  python tools/sfx_gen.py --section lore
  python tools/sfx_gen.py --limit 10        # erste 10 SFX (Test)
  python tools/sfx_gen.py --akt 1           # nur Akt-1-relevant
  python tools/sfx_gen.py --redo-failed     # failed neu versuchen

Output:
  sounds/sfx/generated/<section>/<sfx_id>.mp3
  sounds/sfx/sfx_manifest.json
  sf/sfx_registry.py (Engine-Integration)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.voice_config import load_api_key, cost_estimate_eur  # noqa: E402

# ============================================================
# PATHS
# ============================================================
PROJECT_ROOT      = Path(__file__).resolve().parent.parent
SFX_BIBEL_MD      = PROJECT_ROOT / 'VELGRAD_SFX_BIBEL.md'
SFX_DIR           = PROJECT_ROOT / 'sounds' / 'sfx' / 'generated'
SFX_MANIFEST_JSON = PROJECT_ROOT / 'sounds' / 'sfx' / 'sfx_manifest.json'
SFX_REGISTRY_PY   = PROJECT_ROOT / 'sf' / 'sfx_registry.py'

SFX_API = 'https://api.elevenlabs.io/v1/sound-generation'
REQUEST_INTERVAL_SEC = 0.6
MAX_BACKOFF_SEC = 30.0
MAX_RETRIES = 4

# ElevenLabs SFX-API constraints (Stand 2026):
#   duration_seconds in [0.5, 22.0]
SFX_MIN_DURATION = 0.5
SFX_MAX_DURATION = 22.0


# ============================================================
# SECTION-MAPPING aus VELGRAD_SFX_BIBEL.md
# Header-Marker -> Section-Key
# ============================================================
SECTION_HEADERS = [
    (r'^##\s+I\.\s+UI',          'ui'),
    (r'^##\s+II\.\s+COMBAT',     'combat'),
    (r'^##\s+III\.\s+SKILL',     'skills'),
    (r'^##\s+IV\.\s+MONSTER',    'monster'),
    (r'^##\s+V\.\s+BOSS',        'boss'),
    (r'^##\s+VI\.\s+CINEMATIC',  'cinematic'),
    (r'^##\s+VII\.\s+ENVIRON',   'ambience'),
    (r'^##\s+VIII\.\s+MUSIC',    'music'),
    (r'^##\s+IX\.\s+LORE',       'lore'),
    (r'^##\s+X\.\s+',            'pipeline'),  # nicht generieren
    # Phase 2 — Sub-Sektionen werden ueber ### XI.N erkannt (siehe SUBSECTION_HEADERS)
    (r'^##\s+XI\.\s+',           'phase2'),
]

# Phase-2 hat Sub-Sektionen pro Kategorie — jede landet in eigenem Folder
SUBSECTION_HEADERS = [
    (r'^###\s+XI\.1\s',  'movement'),
    (r'^###\s+XI\.2\s',  'player_combat'),
    (r'^###\s+XI\.3\s',  'status'),
    (r'^###\s+XI\.4\s',  'interact'),
    (r'^###\s+XI\.5\s',  'crafting'),
    (r'^###\s+XI\.6\s',  'menu'),
    (r'^###\s+XI\.7\s',  'quest'),
    # Phase 3 — Voll-Audit-Lücken
    (r'^###\s+XII\.1\s',  'decor'),
    (r'^###\s+XII\.2\s',  'trap'),
    (r'^###\s+XII\.3\s',  'weather'),
    (r'^###\s+XII\.4\s',  'class_special'),
    (r'^###\s+XII\.5\s',  'currency'),
    (r'^###\s+XII\.6\s',  'event'),
    (r'^###\s+XII\.7\s',  'boss_special'),
    (r'^###\s+XII\.8\s',  'flask'),
    (r'^###\s+XII\.9\s',  'player_voice'),
    (r'^###\s+XII\.10\s', 'achievement'),
    (r'^###\s+XII\.11\s', 'engrave'),
    (r'^###\s+XII\.12\s', 'pakt'),
    (r'^###\s+XII\.13\s', 'daynight'),
    (r'^###\s+XII\.14\s', 'shop'),
    (r'^###\s+XII\.15\s', 'tutorial'),
    (r'^###\s+XII\.16\s', 'saveload'),
    (r'^###\s+XII\.17\s', 'atmos'),
]

# Akt-Hint pro SFX-ID-Prefix
AKT_PREFIXES = {
    'ui_':              0,
    'salzgekreuzter':   1, 'krustenkrabbe': 1, 'ertrunkenes': 1,
    'moewen': 1, 'salzhueter': 1,
    'echo_senator': 2, 'goldstaub': 2, 'glasgolden_waechter': 2,
    'spiegel_stalker': 2, 'verfallener_magister': 2, 'senator_geist': 2,
    'asch_soldat': 3, 'predigtsprecher': 3, 'inquisitions_klinge': 3,
    'asch_wolf': 3, 'tribunal_konstrukt': 3, 'vehren': 3,
    'knochenhexe': 4, 'wurzel_spinne': 4, 'fadengebundene': 4,
    'hohler_sohn': 4, 'mark_krieger': 4, 'shulavh': 4,
    'stunden_wandler': 5, 'senator_phantom': 5, 'glasscherben': 5,
    'sich_selbst': 5, 'spiegel_hueter': 5, 'velharn_trio': 5,
    'ertrunkene_koenigin': 6, 'echo_drache': 6, 'nicht_gott': 6,
    'nicht_mann': 6,
    'im_nesh': 7, 'aspekt_echo': 99, 'aithein': 99, 'der_achte': 99,
}


def akt_for_sfx(sfx_id: str) -> int:
    for prefix, akt in AKT_PREFIXES.items():
        if sfx_id.startswith(prefix):
            return akt
    return -1  # unbekannt


# ============================================================
# BIBEL-PARSER
# ============================================================
def parse_sfx_bibel() -> list[dict]:
    """Liest VELGRAD_SFX_BIBEL.md, extrahiert SFX-Definitionen.

    Format in der Bibel (zwei Varianten):

    A) Tabellen-Form:
       | `ui_click` | ... | "soft stone-on-stone click, ..., 0.2 sec" | 0.2 s |

    B) Code-Block-Form:
       ```
       dagger_whisper_stab    "cold dagger stabbing ..., 0.4 sec"
       ```
    """
    text = SFX_BIBEL_MD.read_text(encoding='utf-8')
    entries: list[dict] = []
    seen_ids: set[str] = set()

    current_section = 'unknown'
    in_codeblock = False

    for raw in text.splitlines():
        line = raw.rstrip()

        # Section-Header (##)
        for pat, key in SECTION_HEADERS:
            if re.match(pat, line):
                current_section = key
                break
        # Sub-Section-Header (### XI.N) — Phase 2 only
        for pat, key in SUBSECTION_HEADERS:
            if re.match(pat, line):
                current_section = key
                break

        # Code-Block-Marker
        if line.strip().startswith('```'):
            in_codeblock = not in_codeblock
            continue

        # Tabellen-Form: | `<id>` | ... | "<prompt>" | <dauer> s |
        m_tbl = re.match(
            r'^\|\s*`([a-z0-9_]+)`\s*\|[^|]*\|\s*"([^"]+)"\s*\|\s*([\d.]+)\s*s',
            line)
        if m_tbl:
            sfx_id = m_tbl.group(1).strip()
            prompt = m_tbl.group(2).strip()
            duration = float(m_tbl.group(3))
            if sfx_id not in seen_ids:
                seen_ids.add(sfx_id)
                entries.append(dict(
                    sfx_id=sfx_id,
                    section=current_section,
                    akt=akt_for_sfx(sfx_id),
                    prompt=prompt,
                    duration_seconds=duration,
                    status='pending',
                ))
            continue

        # Code-Block-Form: <id>    "<prompt>"  oder  <id>  (info)
        if in_codeblock:
            m_cb = re.match(r'^\s*([a-z0-9_]+)\s+"([^"]+)"\s*$', line)
            if m_cb:
                sfx_id = m_cb.group(1).strip()
                prompt = m_cb.group(2).strip()
                # Versuch, Dauer aus dem Prompt zu extrahieren
                m_dur = re.search(r'(\d+(?:\.\d+)?)\s*sec', prompt)
                duration = float(m_dur.group(1)) if m_dur else 1.0
                # Verbindung zu loop
                if 'loop' in prompt.lower():
                    m_loop = re.search(r'loop\s+(\d+(?:\.\d+)?)', prompt)
                    if m_loop:
                        duration = float(m_loop.group(1))
                if sfx_id not in seen_ids and current_section not in ('music', 'pipeline'):
                    seen_ids.add(sfx_id)
                    entries.append(dict(
                        sfx_id=sfx_id,
                        section=current_section,
                        akt=akt_for_sfx(sfx_id),
                        prompt=prompt,
                        duration_seconds=min(duration, 22.0),  # API-Limit
                        status='pending',
                    ))

    return entries


# ============================================================
# MANIFEST I/O
# ============================================================
def build_manifest(force: bool = False) -> dict:
    parsed = parse_sfx_bibel()

    existing: dict[str, dict] = {}
    if SFX_MANIFEST_JSON.is_file() and not force:
        try:
            data = json.loads(SFX_MANIFEST_JSON.read_text(encoding='utf-8'))
            existing = {e['sfx_id']: e for e in data.get('entries', [])}
        except json.JSONDecodeError:
            existing = {}

    for e in parsed:
        if e['sfx_id'] in existing:
            e['status'] = existing[e['sfx_id']].get('status', 'pending')

    manifest = dict(
        version=1,
        total_sfx=len(parsed),
        total_seconds=sum(e['duration_seconds'] for e in parsed),
        entries=parsed,
    )
    SFX_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    SFX_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return manifest


def load_manifest() -> dict:
    if not SFX_MANIFEST_JSON.is_file():
        return build_manifest()
    return json.loads(SFX_MANIFEST_JSON.read_text(encoding='utf-8'))


def save_manifest(manifest: dict) -> None:
    SFX_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


# ============================================================
# API-CALL
# ============================================================
def generate_sfx(api_key: str, entry: dict) -> bytes | None:
    if not api_key or any(c.isspace() or ord(c) < 32 for c in api_key):
        print('\n  FEHLER: API-Key ungueltig', file=sys.stderr)
        return None

    # Clamp duration to API limits. UI-Sounds < 0.5s werden auf 0.5s gehoben
    # (ElevenLabs schneidet danach Stille / Decay weg falls Prompt knapper ist).
    dur = max(SFX_MIN_DURATION, min(entry['duration_seconds'], SFX_MAX_DURATION))
    payload = dict(
        text=entry['prompt'],
        duration_seconds=dur,
        prompt_influence=0.7,
    )
    body = json.dumps(payload).encode('utf-8')
    headers = {
        'xi-api-key':   api_key,
        'Content-Type': 'application/json',
        'Accept':       'audio/mpeg',
    }

    backoff = 1.0
    for attempt in range(1, MAX_RETRIES + 1):
        req = urllib.request.Request(SFX_API, data=body, headers=headers, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                print(f'\n  AUTH-FEHLER {e.code}', file=sys.stderr)
                return None
            if e.code == 429:
                wait = min(backoff, MAX_BACKOFF_SEC)
                print(f'\n  429 Rate-Limit, warte {wait:.1f}s …', file=sys.stderr)
                time.sleep(wait)
                backoff *= 2
                continue
            err = e.read().decode('utf-8', errors='ignore')[:200]
            print(f'\n  HTTP {e.code} bei {entry["sfx_id"]}: {err}', file=sys.stderr)
            # 4xx (ausser 429) sind permanent — kein Retry, sonst Verschwendung
            if 400 <= e.code < 500 and e.code != 429:
                return None
            if attempt >= MAX_RETRIES:
                return None
            time.sleep(backoff)
            backoff *= 2
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'\n  Netzwerk-Fehler {entry["sfx_id"]}: {e}', file=sys.stderr)
            if attempt >= MAX_RETRIES:
                return None
            time.sleep(backoff)
            backoff *= 2
    return None


# ============================================================
# REGISTRY-GENERATION
# ============================================================
def regenerate_registry(manifest: dict) -> None:
    done = [e for e in manifest['entries'] if e.get('status') == 'done']
    if not done:
        return

    by_section: dict[str, list[str]] = {}
    for e in done:
        rel = f"sounds/sfx/generated/{e['section']}/{e['sfx_id']}.mp3"
        by_section.setdefault(e['section'], []).append((e['sfx_id'], rel))

    lines = [
        '"""Auto-generiert von tools/sfx_gen.py.',
        '',
        'SFX-Registry: SFX-ID -> MP3-Pfad.',
        'Erweiterung des bestehenden sf/sounds.py SFX_FILE_ALIASES.',
        '"""',
        'from __future__ import annotations',
        '',
        '',
        'SFX_GENERATED: dict[str, str] = {',
    ]
    for section in sorted(by_section):
        lines.append(f'    # ---- {section} ----')
        for sfx_id, path in sorted(by_section[section]):
            lines.append(f'    {sfx_id!r}: {path!r},')
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def sfx_path(sfx_id: str) -> str | None:')
    lines.append('    return SFX_GENERATED.get(sfx_id)')
    lines.append('')

    SFX_REGISTRY_PY.parent.mkdir(parents=True, exist_ok=True)
    SFX_REGISTRY_PY.write_text('\n'.join(lines), encoding='utf-8')


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run',  action='store_true')
    ap.add_argument('--section',  type=str, default=None,
                    help='ui|combat|skills|monster|boss|cinematic|lore|ambience')
    ap.add_argument('--akt',      type=int, default=None,
                    help='Nur SFX fuer Akt N (0=UI, 1-7=Akt, 99=Endgame)')
    ap.add_argument('--limit',    type=int, default=None)
    ap.add_argument('--redo-failed', action='store_true')
    ap.add_argument('--force-rebuild-manifest', action='store_true')
    args = ap.parse_args()

    manifest = build_manifest(force=args.force_rebuild_manifest)

    if args.redo_failed:
        for e in manifest['entries']:
            if e.get('status') == 'failed':
                e['status'] = 'pending'

    pending = [e for e in manifest['entries'] if e.get('status') == 'pending']

    # Ambient-Section ist Stable-Audio-Domain (lange Loops), nicht ElevenLabs
    pending = [e for e in pending if e['section'] != 'ambience']

    if args.section:
        pending = [e for e in pending if e['section'] == args.section]
    if args.akt is not None:
        pending = [e for e in pending if e['akt'] == args.akt]
    if args.limit:
        pending = pending[:args.limit]

    # Cost-Schaetzung: SFX-API kostet ~50 credits/sec; 1 credit ≈ 1 char (Creator-Plan)
    total_sec = sum(e['duration_seconds'] for e in pending)
    char_equiv = int(total_sec * 50)
    cost = cost_estimate_eur(char_equiv)

    # Section-Aufschluesselung
    by_section: dict[str, int] = {}
    for e in pending:
        by_section[e['section']] = by_section.get(e['section'], 0) + 1

    print('=' * 60)
    print('SFX-GEN — DRY-RUN' if args.dry_run else 'SFX-GEN — START')
    print('=' * 60)
    print(f'  SFX im Manifest insgesamt: {manifest["total_sfx"]:>5}')
    print(f'  Pending (nach Filter):     {len(pending):>5}')
    print(f'  Total Audio-Dauer:         {total_sec:.1f}s ({total_sec/60:.1f} min)')
    print(f'  Char-Equivalent:           {char_equiv:>5,}')
    print(f'  Kosten-Schaetzung:         {cost:.2f} EUR')
    if by_section:
        print('  Aufschluesselung:')
        for s, c in sorted(by_section.items()):
            print(f'    {s:<12} {c:>4} SFX')
    print('=' * 60)

    if args.dry_run:
        return
    if not pending:
        print('Nichts zu generieren.')
        return

    try:
        api_key = load_api_key()
    except RuntimeError as e:
        print(f'\nFEHLER: {e}', file=sys.stderr)
        sys.exit(3)

    done_count = 0
    fail_count = 0
    total_chars_used = 0

    for i, entry in enumerate(pending, 1):
        out_dir = SFX_DIR / entry['section']
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f'{entry["sfx_id"]}.mp3'
        if out_path.exists() and entry.get('status') == 'done':
            continue

        print(f'  [{i:>4}/{len(pending)}] {entry["section"]:<10} '
              f'{entry["sfx_id"]:<35} '
              f'({entry["duration_seconds"]:.1f}s)', end=' ', flush=True)

        t0 = time.time()
        audio = generate_sfx(api_key, entry)
        if audio is None:
            entry['status'] = 'failed'
            fail_count += 1
            print('FAIL')
        else:
            out_path.write_bytes(audio)
            entry['status'] = 'done'
            done_count += 1
            total_chars_used += int(entry['duration_seconds'] * 50)
            print(f'ok ({time.time()-t0:.1f}s, {len(audio)//1024} KiB)')

        if i % 5 == 0:
            save_manifest(manifest)
        time.sleep(REQUEST_INTERVAL_SEC)

    save_manifest(manifest)
    regenerate_registry(manifest)

    print('=' * 60)
    print(f'  Done:     {done_count}')
    print(f'  Failed:   {fail_count}')
    print(f'  Chars:    {total_chars_used:,}')
    print(f'  Kosten:   {cost_estimate_eur(total_chars_used):.2f} EUR (Schaetzung)')
    print(f'  Output:   {SFX_DIR}')
    print(f'  Registry: {SFX_REGISTRY_PY}')
    print('=' * 60)


if __name__ == '__main__':
    main()
