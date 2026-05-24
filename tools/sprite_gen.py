"""Scenario.gg Batch-Sprite-Generator.

Parst VELGRAD_SPRITE_BIBEL.md, extrahiert die Target-Prompts,
und generiert pro Target ein PNG via Scenario.gg Inference-API.

Scenario.gg API-Flow (Stand 2026):
  1. POST /v1/generate/txt2img  → returnt inference_id (job)
  2. GET  /v1/inferences/<id>    → poll bis status=succeeded
  3. Download PNG-URL aus result

Usage:
  python tools/sprite_gen.py --dry-run               # nur Kosten
  python tools/sprite_gen.py --target salzhueter_brut  # 1 Sprite Test
  python tools/sprite_gen.py --category mob          # alle 6 Mobs
  python tools/sprite_gen.py --variants 4            # 4 Varianten pro Target
  python tools/sprite_gen.py                         # alles pending
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
from tools.scenario_config import (  # noqa: E402
    PROJECT_ROOT, SPRITES_DIR, SPRITE_MANIFEST_JSON,
    API_BASE, SPRITE_CATEGORIES, auth_header, plan_budget,
    model_for_category,
)

# ============================================================
# CONSTANTS
# ============================================================
SPRITE_BIBEL_MD = PROJECT_ROOT / 'VELGRAD_SPRITE_BIBEL.md'
SPRITE_REGISTRY_PY = PROJECT_ROOT / 'sf' / 'sprite_registry.py'

REQUEST_INTERVAL_SEC = 1.0
POLL_INTERVAL_SEC    = 3.0
POLL_TIMEOUT_SEC     = 300.0   # Boss-Plates + grosse Tiles brauchen bis 4 Min
MAX_RETRIES          = 3

# Update #167: Master-Style + Per-Category-Specs werden zentral aus
# sf/render_spec.py importiert (Single-Source-of-Truth). VELGRAD_RENDER_SPEC.md
# dokumentiert die Konvention. CATEGORY_SUFFIX bleibt als lokale Erweiterung
# fuer Kategorien die noch nicht in render_spec sind (decor, status_icon, etc.).
from sf.render_spec import (  # noqa: E402
    MASTER_POSITIVE, MASTER_NEGATIVE,
    get_resolution as spec_get_resolution,
    RENDER_SPEC as _RENDER_SPEC,
)

# Per-Category-Suffixes — werden ans Ende des Lore-Prompts gehaengt
CATEGORY_SUFFIX = {
    'mob': (
        ', isolated full-body character on plain pure-black background, '
        'no environment, no scenery behind, top-down 3/4 angled hero shot, '
        'sprite-ready composition, centered subject'
    ),
    'class': (
        ', isolated full-body hero on plain pure-black background, no '
        'environment behind, frontal hero pose, sprite-ready composition, '
        'full body visible head to toe, centered'
    ),
    'portrait': (
        ', head and shoulders portrait with simple dark vignette gradient '
        'behind subject, no detailed environment, focus on face and upper '
        'torso, centered composition'
    ),
    'boss_plate': '',  # Backdrop erwuenscht
    'item_icon': (
        ', single isolated weapon on pure-black background, no environment'
    ),
    'tile': (
        ', seamless repeating tileable ground texture, completely flat '
        'top-down orthographic view straight down from above, no perspective, '
        'no depth, no walls, no pillars, no arches, no architecture, no '
        'buildings, no scenery, no horizon, no sky, no characters, no objects, '
        'uniform floor pattern only, edges loop perfectly, '
        'no central focal point, repeatable game-map tile, '
        'pure flat ground material'
    ),
    # Prio-Pass HOCH (VELGRAD_SPRITE_BIBEL §XI/§XIII)
    'decor': (
        ', single isolated prop object on plain pure-black background, '
        'no environment, no scenery behind, top-down 3/4 angled view, '
        'sprite-ready composition, centered subject, full silhouette visible, '
        'ground-anchored bottom edge'
    ),
    'status_icon': (
        ', small isolated game-ui icon on plain pure-black background, '
        'no environment, single symbolic object, painterly icon style, '
        'clear silhouette, centered, minimal background, ARPG status-effect '
        'icon for inventory-style display'
    ),
}


# ============================================================
# BIBEL-PARSER
# ============================================================
# Sucht Headings der Form "### M1. Salzhueter-Brut" + danach den ```code-block```
# Prefix-Letters:
#   M = mob, C = class, P = portrait, B = boss_plate, T = tile
#   D = decor (§XI), U = item_icon-unique (§XII), S = status_icon (§XIII)
TARGET_HEADER_RE = re.compile(
    # Matched: "### M1. Salzhueter-Brut *(Akt-1-Boss)*" oder
    #          "### C1. Warrior — Eisenwaechter (Kharn-Lineage)" oder
    #          "### U7. Verbrannte-Treue *(Two-Hand Sword [M])*"
    # Name = alles vor dem ersten "*" oder "—"; danach Lore-Suffix ignoriert.
    r'^###\s+([MCPBTDUS]\d+[a-z]?)\.\s+([^\n*—]+?)(?:\s*[*—].*)?\s*$',
    re.MULTILINE
)


def _slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r'[^\w\s-]', '', s, flags=re.UNICODE)
    s = re.sub(r'[-\s]+', '_', s)
    s = s.replace('ä', 'ae').replace('ö', 'oe').replace('ü', 'ue').replace('ß', 'ss')
    return s.strip('_')


def parse_sprite_bibel() -> list[dict]:
    """Returnt Liste von Target-Dicts: id, category, name, prompt."""
    text = SPRITE_BIBEL_MD.read_text(encoding='utf-8')

    # Kategorie-Mapping über Header-Prefix (M, C, P, B, T, D, U, S)
    PREFIX_CATEGORY = {
        'M': 'mob',
        'C': 'class',
        'P': 'portrait',
        'B': 'boss_plate',
        'T': 'tile',
        # Prio-Pass HOCH (VELGRAD_SPRITE_BIBEL §XI/§XII/§XIII)
        'D': 'decor',
        'U': 'item_icon',     # 50 Uniques aus VELGRAD_ITEMS_UNIQUE_BIBEL
        'S': 'status_icon',
    }

    targets = []
    # Find alle Headings + code-blocks
    pos = 0
    for m in TARGET_HEADER_RE.finditer(text):
        prefix = m.group(1)
        name = m.group(2).strip()
        # Suche den naechsten ```...```  Block (Prompt) nach dem Header
        rest = text[m.end():]
        cb = re.search(r'```\s*\n(.+?)\n```', rest, re.DOTALL)
        if not cb:
            continue
        prompt = cb.group(1).strip()
        # [MASTER-PREFIX] durch echten Master-Prompt ersetzen
        prompt = prompt.replace('[MASTER-PREFIX]', MASTER_POSITIVE)
        prompt = ' '.join(prompt.split())  # Zeilen-Whitespace normalisieren

        cat_letter = prefix[0]
        category = PREFIX_CATEGORY.get(cat_letter)
        if category is None:
            continue

        # Variant-Letter aus Prefix extrahieren (T1a/T1b/T1c/T1d/T1w/M3a/...)
        # Slug bekommt einen Suffix `_<letter>` damit Variants unterscheidbar.
        variant_m = re.match(r'^[MCPBTDUS]\d+([a-z])$', prefix)
        variant_suffix = ('_' + variant_m.group(1)) if variant_m else ''
        target_id = _slug(name) + variant_suffix
        targets.append(dict(
            id=target_id,
            label=prefix,
            category=category,
            name=name,
            prompt=prompt,
            status='pending',
        ))

    return targets


# ============================================================
# MANIFEST I/O
# ============================================================
def build_manifest(force: bool = False) -> dict:
    parsed = parse_sprite_bibel()
    existing = {}
    if SPRITE_MANIFEST_JSON.is_file() and not force:
        try:
            data = json.loads(SPRITE_MANIFEST_JSON.read_text(encoding='utf-8'))
            existing = {e['id']: e for e in data.get('entries', [])}
        except json.JSONDecodeError:
            existing = {}

    for e in parsed:
        if e['id'] in existing:
            e['status'] = existing[e['id']].get('status', 'pending')
            e['file_path'] = existing[e['id']].get('file_path')

    manifest = dict(
        version=1,
        total=len(parsed),
        entries=parsed,
    )
    SPRITE_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    SPRITE_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return manifest


def save_manifest(manifest: dict) -> None:
    SPRITE_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )


# ============================================================
# SCENARIO API
# ============================================================
def _http_json(method: str, url: str, headers: dict, body: dict | None = None,
               timeout: float = 60) -> tuple[int, dict | None]:
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode('utf-8', errors='ignore')[:300]
        except Exception:
            raw = ''
        return e.code, {'error': raw}


def submit_inference(entry: dict, size: tuple[int, int], steps: int,
                     model_id: str | None = None) -> str | None:
    """POST /v1/models/<model_id>/inferences. Returnt inference_id oder None.

    Scenario.gg routet die Inference ueber das gewaehlte Model (LoRA-Base).
    Fallback: DEFAULT_MODELS aus scenario_config.
    """
    headers = auth_header()
    mid = model_id or model_for_category(entry['category'])
    # Lore-Prompt + Kategorie-Suffix (transparent BG / atmospheric / seamless)
    full_prompt = entry['prompt'] + CATEGORY_SUFFIX.get(entry['category'], '')
    # Tile-Kategorie: zusaetzliche Anti-Architektur-Negatives
    neg = MASTER_NEGATIVE
    if entry['category'] == 'tile':
        neg += (
            ', walls, pillars, arches, columns, buildings, scenery, '
            'horizon, perspective, depth, sky, character, person, '
            'creature, archway, ruins, statue, doorway, room, '
            'sunbeams, god rays'
        )
    payload = dict(
        parameters=dict(
            type='txt2img',
            prompt=full_prompt,
            negativePrompt=neg,
            negativePromptStrength=1.0,   # API verlangt > 0 wenn negativePrompt gesetzt
            width=size[0],
            height=size[1],
            numSamples=1,
            numInferenceSteps=steps,
            guidance=7.0,
            modelId=mid,
        ),
    )
    # Scenario-API: POST /v1/models/<modelId>/inferences
    url = f'{API_BASE}/models/{mid}/inferences'
    code, data = _http_json('POST', url, headers, payload, timeout=60)
    if code not in (200, 201, 202) or not data:
        print(f'    submit HTTP {code}: {str(data)[:120]}', file=sys.stderr)
        return None
    # Scenario.gg returnt {"job":{"jobId":..., "metadata":{"inferenceId":...}}}
    # Wir geben den jobId zurueck — Polling laeuft ueber /jobs/<jobId>.
    job = data.get('job') or data.get('inference') or data
    return (job.get('jobId') or job.get('id') or
            (data.get('inference') or {}).get('id'))


def _fetch_asset_url(asset_id: str) -> str | None:
    """GET /v1/assets/<id> → image URL."""
    headers = auth_header()
    url = f'{API_BASE}/assets/{asset_id}'
    code, data = _http_json('GET', url, headers, timeout=30)
    if code != 200 or not data:
        print(f'    asset-fetch HTTP {code}', file=sys.stderr)
        return None
    asset = data.get('asset') or data
    # Probier mehrere bekannte Felder
    return (asset.get('url') or asset.get('downloadUrl') or
            asset.get('signedUrl') or asset.get('imageUrl') or
            (asset.get('data') or {}).get('url'))


def poll_inference(job_id: str, model_id: str) -> dict | None:
    """Pollt /jobs/<jobId> bis 'success'. Asset-IDs sind in metadata.assetIds.

    Scenario.gg Flow (verifiziert):
      1. POST /models/<mid>/inferences        → {job: {jobId}}
      2. GET  /jobs/<jobId>                   → {job: {status, metadata: {assetIds: [...]}}}
      3. GET  /assets/<assetId>               → {asset: {url}}
    """
    headers = auth_header()
    job_url = f'{API_BASE}/jobs/{job_id}'
    t0 = time.time()
    while time.time() - t0 < POLL_TIMEOUT_SEC:
        code, data = _http_json('GET', job_url, headers, timeout=30)
        if code != 200 or not data:
            time.sleep(POLL_INTERVAL_SEC)
            continue
        job = data.get('job') or data
        status = (job.get('status') or '').lower()
        meta = job.get('metadata') or {}
        if status in ('success', 'succeeded', 'complete'):
            asset_ids = meta.get('assetIds') or []
            if not asset_ids:
                print('    job success aber keine assetIds', file=sys.stderr)
                return None
            # Asset-URLs holen
            images = []
            for aid in asset_ids:
                u = _fetch_asset_url(aid)
                if u:
                    images.append({'url': u, 'assetId': aid})
            if not images:
                return None
            return {'images': images}
        if status in ('failed', 'failure', 'error', 'cancelled'):
            print(f'    job FAILED: {status}', file=sys.stderr)
            return None
        time.sleep(POLL_INTERVAL_SEC)
    print(f'    poll TIMEOUT after {POLL_TIMEOUT_SEC}s', file=sys.stderr)
    return None


def download_png(url: str, out_path: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={'Accept': 'image/png'})
        with urllib.request.urlopen(req, timeout=60) as resp:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(resp.read())
            return True
    except Exception as e:
        print(f'    download FAILED: {e}', file=sys.stderr)
        return False


def generate_sprite(entry: dict, model_override: str | None = None) -> str | None:
    """End-to-end: submit + poll + download. Returnt rel-Path oder None."""
    cat_cfg = SPRITE_CATEGORIES.get(entry['category'])
    if cat_cfg is None:
        return None
    # Update #167: Size kommt primaer aus render_spec (single source of truth),
    # fallback auf scenario_config.SPRITE_CATEGORIES wenn nicht spec'd.
    spec_size = spec_get_resolution(entry['category'])
    if spec_size != (512, 512) or entry['category'] in _RENDER_SPEC:
        # render_spec hat einen expliziten Eintrag → den verwenden
        size = spec_size
    else:
        size = cat_cfg['size']
    steps = cat_cfg['steps']
    out_dir_name = cat_cfg['out_dir']
    out_path = SPRITES_DIR / out_dir_name / f"{entry['id']}.png"
    mid = model_override or model_for_category(entry['category'])

    # 1) Submit
    inf_id = submit_inference(entry, size, steps, model_id=mid)
    if not inf_id:
        return None
    print(f'    inf_id={inf_id[:10]}…', end=' ', flush=True)

    # 2) Poll
    result = poll_inference(inf_id, mid)
    if not result:
        return None

    # 3) Download
    images = result.get('images') or result.get('outputs') or []
    if not images:
        print('    no images in result', file=sys.stderr)
        return None
    first = images[0]
    url = first.get('url') or first.get('imageUrl') or first
    if not isinstance(url, str):
        print(f'    no url in image: {first}', file=sys.stderr)
        return None

    ok = download_png(url, out_path)
    if not ok:
        return None
    return str(out_path.relative_to(PROJECT_ROOT)).replace('\\', '/')


# ============================================================
# REGISTRY-GENERATION
# ============================================================
def regenerate_registry(manifest: dict) -> None:
    done = [e for e in manifest['entries']
            if e.get('status') == 'done' and e.get('file_path')]
    by_cat: dict[str, list[tuple[str, str]]] = {}
    for e in done:
        by_cat.setdefault(e['category'], []).append((e['id'], e['file_path']))

    lines = [
        '"""Auto-generiert von tools/sprite_gen.py.',
        '',
        'Sprite-Registry: target_id -> projekt-relativer PNG-Pfad.',
        '"""',
        'from __future__ import annotations',
        '',
        '',
        'SPRITES: dict[str, str] = {',
    ]
    for cat in sorted(by_cat):
        lines.append(f'    # ---- {cat} ----')
        for tid, path in sorted(by_cat[cat]):
            lines.append(f'    {tid!r}: {path!r},')
    lines.append('}')
    lines.append('')
    lines.append('')
    lines.append('def sprite_path(target_id: str) -> str | None:')
    lines.append('    return SPRITES.get(target_id)')
    lines.append('')

    SPRITE_REGISTRY_PY.parent.mkdir(parents=True, exist_ok=True)
    SPRITE_REGISTRY_PY.write_text('\n'.join(lines), encoding='utf-8')


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run',  action='store_true')
    ap.add_argument('--category', type=str, default=None,
                    help='mob|class|portrait|boss_plate|tile|item_icon')
    ap.add_argument('--target',   type=str, default=None,
                    help='Spezifischer Target-Slug (z.B. salzhueter_brut)')
    ap.add_argument('--model',    type=str, default=None,
                    help='Override Model-ID (default: aus scenario_config DEFAULT_MODELS)')
    ap.add_argument('--variants', type=int, default=1,
                    help='Variants pro Target (Default 1 fuer Test, 4 fuer Pass)')
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
    if args.category:
        pending = [e for e in pending if e['category'] == args.category]
    if args.target:
        pending = [e for e in pending if e['id'] == args.target]
    if args.limit:
        pending = pending[:args.limit]

    total_calls = len(pending) * max(1, args.variants)
    budget = plan_budget()

    by_cat: dict[str, int] = {}
    for e in pending:
        by_cat[e['category']] = by_cat.get(e['category'], 0) + 1

    print('=' * 60)
    print('SPRITE-GEN — DRY-RUN' if args.dry_run else 'SPRITE-GEN — START')
    print('=' * 60)
    print(f'  Targets im Manifest: {manifest["total"]:>4}')
    print(f'  Pending (Filter):    {len(pending):>4}')
    print(f'  Variants pro Target: {args.variants:>4}')
    print(f'  Total API-Calls:     {total_calls:>4}')
    print(f'  Plan-Budget/Monat:   {budget:>4} Bilder ({total_calls/budget*100:.1f} %)')
    if by_cat:
        print('  Pro Kategorie:')
        for c, n in sorted(by_cat.items()):
            print(f'    {c:<12} {n:>3} targets')
    print('=' * 60)

    if args.dry_run:
        return
    if not pending:
        print('Nichts zu generieren.')
        return

    # Generate
    done = 0
    failed = 0
    for i, entry in enumerate(pending, 1):
        for v in range(max(1, args.variants)):
            tag = f' (var{v+1}/{args.variants})' if args.variants > 1 else ''
            print(f'  [{i:>3}/{len(pending)}] {entry["category"]:<10} '
                  f'{entry["id"]:<28}{tag}', end=' ', flush=True)
            t0 = time.time()
            rel = generate_sprite(entry, model_override=args.model)
            if rel:
                entry['status'] = 'done'
                entry['file_path'] = rel
                done += 1
                print(f'ok ({time.time()-t0:.1f}s)')
            else:
                entry['status'] = 'failed'
                failed += 1
                print('FAIL')
            if i % 3 == 0 or v < args.variants - 1:
                save_manifest(manifest)
            time.sleep(REQUEST_INTERVAL_SEC)

    save_manifest(manifest)
    regenerate_registry(manifest)

    print('=' * 60)
    print(f'  Done:   {done}')
    print(f'  Failed: {failed}')
    print(f'  Output: {SPRITES_DIR}')
    print(f'  Registry: {SPRITE_REGISTRY_PY}')
    print('=' * 60)


if __name__ == '__main__':
    main()
