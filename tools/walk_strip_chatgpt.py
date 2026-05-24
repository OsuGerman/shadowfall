"""Walk-Strip-Generator via OpenAI gpt-image-1 (Image-Edits-Endpoint).

Generiert pro Klasse 1×8-Frame-Walk-Strips fuer down/up/left/right und legt
sie direkt unter `assets/sprites/classes/<cls>_anims/walk/<dir>.png` ab —
genau dort wo `sf/sprites._anim_strip_path` (Update #165) sie erwartet.

Prompt nutzt 3/4-Top-Down-ARPG-Kamera (POE2/Hades-Style) — passt zur
restlichen Welt (Tiles + Mobs + alte Class-Anchor-Sprites).

Usage:
  python tools/walk_strip_chatgpt.py --cls monk --dry-run
  python tools/walk_strip_chatgpt.py --cls monk
  python tools/walk_strip_chatgpt.py --cls monk --dirs down --quality high

Sicherheit (Pattern wie tools/scenario_config.py):
  - Key aus Env OPENAI_API_KEY, dann .openai_key, dann ChatGPT.txt
  - Whitespace/Control-Chars im Token -> Abbruch (kein API-Call)
  - Key wird NIEMALS geloggt — auch nicht in Fehlerausgaben
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import uuid
from pathlib import Path
from urllib import request, error


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR  = PROJECT_ROOT / 'assets' / 'sprites'
CLASSES_DIR  = SPRITES_DIR / 'classes'

API_URL = 'https://api.openai.com/v1/images/edits'


# ============================================================
# PROMPT-BAUSTEINE — Single Source of Truth aus sf/render_spec.py
# Update #167: DIRECTION_DESC zentral, damit POE2/Hades-3/4-Top-Down-Kamera
# nicht aus Versehen lokal weggepatcht wird.
# ============================================================
sys.path.insert(0, str(PROJECT_ROOT))
from sf.render_spec import DIRECTION_DESC  # noqa: E402

WALK_FRAME_DESCS = [
    'frame 1: contact pose, left foot forward, weight shifting onto front foot',
    'frame 2: down pose, left foot planted, body at lowest point',
    'frame 3: passing pose, right leg passing left, body rising',
    'frame 4: up pose, right leg highest in forward swing',
    'frame 5: contact pose, right foot forward, weight shifting',
    'frame 6: down pose, right foot planted, body at lowest opposite',
    'frame 7: passing pose, left leg passing right',
    'frame 8: up pose, left leg highest in swing',
]


def build_strip_prompt(cls: str, direction: str) -> str:
    """Single-shot mode: ein Bild = ganzer 1x8-Strip. Schneller + billiger,
    aber Frames werden bei 1536x1024 nur ~192px breit pro Frame."""
    dir_desc = DIRECTION_DESC[direction]
    frames = '; '.join(WALK_FRAME_DESCS)
    return (
        f'Generate a 1x8 horizontal sprite sheet of 8 walk-cycle keyframes '
        f'showing the same {cls} character from the reference image. '
        f'{dir_desc}. '
        f'ARPG character sprite in Path of Exile 2 / Hades style three-quarter '
        f'top-down camera angle, head closer to camera than feet, '
        f'character viewed from slightly above eye level, not a flat portrait. '
        f'8 frames evenly spaced left-to-right in one horizontal row, '
        f'each frame showing one walk-cycle phase: {frames}. '
        f'Same outfit, same weapon, same proportions as reference across all '
        f'8 frames. Transparent background. '
        f'Not pixel art, not isometric tile art.'
    )


def build_frame_prompt(cls: str, direction: str, frame_idx: int) -> str:
    """Per-frame mode: ein Bild = ein Frame. Volle Aufloesung pro Frame,
    bessere Pose-Praezision, aber 8x mehr API-Calls pro Direction."""
    dir_desc = DIRECTION_DESC[direction]
    phase = WALK_FRAME_DESCS[frame_idx]
    return (
        f'Single full-body {cls} character from the reference image, '
        f'walking pose: {phase}. '
        f'{dir_desc}. '
        f'ARPG character sprite in Path of Exile 2 / Hades style three-quarter '
        f'top-down camera angle, head closer to camera than feet, '
        f'character viewed from slightly above eye level, not a flat portrait. '
        f'Same outfit, same weapon, same proportions and exact same character '
        f'identity as reference. Centered, full body visible from head to feet, '
        f'transparent background. '
        f'Not pixel art, not isometric tile art, not a portrait headshot.'
    )


# ============================================================
# API-KEY (sanitized, never logged)
# ============================================================
class InvalidKeyFormat(Exception):
    pass


def _sanitize_key(raw: str) -> str:
    if not raw:
        raise InvalidKeyFormat('INVALID_KEY_FORMAT')
    cleaned = raw.strip()
    if not cleaned or not re.fullmatch(r'[A-Za-z0-9_\-.]+', cleaned):
        raise InvalidKeyFormat('INVALID_KEY_FORMAT')
    if not cleaned.startswith('sk-'):
        raise InvalidKeyFormat('INVALID_KEY_FORMAT')
    return cleaned


def load_openai_key() -> str:
    """Read key from env OPENAI_API_KEY, then .openai_key, then ChatGPT.txt.
    Returns cleaned key. Never logs the key in error messages."""
    env = os.environ.get('OPENAI_API_KEY', '').strip()
    if env:
        return _sanitize_key(env)
    for fname in ('.openai_key', 'ChatGPT.txt'):
        p = PROJECT_ROOT / fname
        if p.is_file():
            try:
                content = p.read_text(encoding='utf-8')
            except Exception:
                raise InvalidKeyFormat('INVALID_KEY_FORMAT')
            first_line = content.splitlines()[0] if content else ''
            return _sanitize_key(first_line)
    raise InvalidKeyFormat('NO_KEY_FOUND (set OPENAI_API_KEY or create ChatGPT.txt)')


# ============================================================
# MULTIPART + HTTP
# ============================================================
def _encode_multipart(fields: dict, files: dict) -> tuple[bytes, str]:
    """fields: name -> str. files: name -> (filename, mime, bytes)."""
    boundary = '----walkgen-' + uuid.uuid4().hex
    crlf = b'\r\n'
    parts: list[bytes] = []
    for name, value in fields.items():
        parts.append(f'--{boundary}'.encode())
        parts.append(
            f'Content-Disposition: form-data; name="{name}"'.encode()
        )
        parts.append(b'')
        parts.append(str(value).encode('utf-8'))
    for name, (filename, mime, content) in files.items():
        parts.append(f'--{boundary}'.encode())
        parts.append(
            (f'Content-Disposition: form-data; name="{name}"; '
             f'filename="{filename}"').encode()
        )
        parts.append(f'Content-Type: {mime}'.encode())
        parts.append(b'')
        parts.append(content)
    parts.append(f'--{boundary}--'.encode())
    parts.append(b'')
    return crlf.join(parts), f'multipart/form-data; boundary={boundary}'


def call_edits_api(key: str, anchor_png: Path, prompt: str,
                    size: str, quality: str, timeout: int = 240) -> bytes:
    """Returns PNG bytes of the generated image. Key never appears in errors."""
    with open(anchor_png, 'rb') as f:
        img_bytes = f.read()
    fields = {
        'model':   'gpt-image-1',
        'prompt':  prompt,
        'n':       '1',
        'size':    size,
        'quality': quality,
        'background': 'transparent',
    }
    files = {'image': (anchor_png.name, 'image/png', img_bytes)}
    body, content_type = _encode_multipart(fields, files)
    req = request.Request(API_URL, data=body, method='POST')
    req.add_header('Authorization', f'Bearer {key}')
    req.add_header('Content-Type', content_type)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            payload = json.loads(resp.read().decode('utf-8'))
    except error.HTTPError as e:
        body_text = ''
        try:
            body_text = e.read().decode('utf-8', errors='replace')
        except Exception:
            pass
        raise RuntimeError(
            f'OpenAI API HTTP {e.code}: {e.reason}\n{body_text}'
        ) from None
    except error.URLError as e:
        raise RuntimeError(f'Netzwerk-Fehler: {e.reason}') from None
    data = payload.get('data') or []
    if not data:
        raise RuntimeError('OpenAI API returned no images')
    b64 = data[0].get('b64_json')
    if not b64:
        raise RuntimeError('OpenAI API response missing b64_json')
    return base64.b64decode(b64)


# ============================================================
# COST-SCHAETZUNG
# ============================================================
# gpt-image-1 pricing per output image (Stand 2025-Q2)
COST_USD = {
    ('1024x1024', 'low'):    0.011,
    ('1024x1024', 'medium'): 0.042,
    ('1024x1024', 'high'):   0.167,
    ('1024x1536', 'low'):    0.016,
    ('1024x1536', 'medium'): 0.063,
    ('1024x1536', 'high'):   0.25,
    ('1536x1024', 'low'):    0.016,
    ('1536x1024', 'medium'): 0.063,
    ('1536x1024', 'high'):   0.25,
}


def estimate_cost_usd(n_calls: int, size: str, quality: str) -> float:
    return n_calls * COST_USD.get((size, quality), 0.25)


def composit_horizontal_strip(frame_bytes_list: list[bytes],
                                out_path: Path) -> None:
    """Composit N PNG-Bytes-Frames horizontal zu einem 1×N-Strip-PNG.
    Behaelt Aspect-Ratio; alle Frames werden auf gleiche Hoehe gebracht."""
    from PIL import Image
    import io
    imgs = [Image.open(io.BytesIO(b)).convert('RGBA') for b in frame_bytes_list]
    target_h = max(im.height for im in imgs)
    # Skaliere jedes Frame auf target_h (proportional)
    scaled = []
    for im in imgs:
        if im.height != target_h:
            ratio = target_h / im.height
            new_w = max(1, int(im.width * ratio))
            im = im.resize((new_w, target_h), Image.LANCZOS)
        scaled.append(im)
    total_w = sum(im.width for im in scaled)
    strip = Image.new('RGBA', (total_w, target_h), (0, 0, 0, 0))
    x = 0
    for im in scaled:
        strip.paste(im, (x, 0), im)
        x += im.width
    strip.save(out_path, 'PNG', optimize=True)


# ============================================================
# MAIN
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description='Walk-Strip-Generator (OpenAI gpt-image-1)'
    )
    ap.add_argument('--cls', type=str, required=True,
                    help='Klassen-Slug, z.B. monk, warrior, huntress')
    ap.add_argument('--dirs', type=str, default='down,up,left,right',
                    help='Komma-separiert (Default: down,up,left,right)')
    ap.add_argument('--quality', choices=['low', 'medium', 'high'],
                    default='high',
                    help='Default high — pro Frame deutlich mehr Detail. '
                         'medium reicht oft bei per-frame mode.')
    ap.add_argument('--size', choices=['1024x1024', '1024x1536', '1536x1024'],
                    default=None,
                    help='Auto-default: 1024x1536 (portrait) fuer per-frame, '
                         '1536x1024 (landscape) fuer single-shot strip.')
    ap.add_argument('--single-shot', action='store_true',
                    help='Statt 8 Frames pro Direction nur 1 Bild generieren '
                         '(billiger, aber Frames werden sehr schmal).')
    ap.add_argument('--dry-run', action='store_true',
                    help='Nur Prompts + Pfade ausgeben, keine API-Calls')
    ap.add_argument('--yes', '-y', action='store_true',
                    help='Bestaetigung skippen (Vorsicht: kostet sofort)')
    args = ap.parse_args()

    dirs = [d.strip().lower() for d in args.dirs.split(',') if d.strip()]
    bad = [d for d in dirs if d not in DIRECTION_DESC]
    if bad:
        sys.exit(f'Unbekannte Direction(s): {bad}. '
                 f'Erlaubt: {sorted(DIRECTION_DESC)}')

    anchor = CLASSES_DIR / f'{args.cls}.png'
    if not anchor.is_file():
        sys.exit(f'Anchor nicht gefunden: '
                 f'{anchor.relative_to(PROJECT_ROOT)}')

    out_dir = CLASSES_DIR / f'{args.cls}_anims' / 'walk'
    out_dir.mkdir(parents=True, exist_ok=True)

    # Auto-defaults nach Modus
    per_frame = not args.single_shot
    size = args.size or ('1024x1536' if per_frame else '1536x1024')
    calls_per_dir = 8 if per_frame else 1
    n_calls = len(dirs) * calls_per_dir
    cost = estimate_cost_usd(n_calls, size, args.quality)
    mode_label = (f'per-frame ({calls_per_dir} frames × {len(dirs)} dirs)'
                  if per_frame else f'single-shot strip (1 × {len(dirs)} dirs)')

    print('=' * 60)
    print(f'Walk-Strip-Gen: cls={args.cls}')
    print(f'  Anchor:    {anchor.relative_to(PROJECT_ROOT)}')
    print(f'  Output:    {out_dir.relative_to(PROJECT_ROOT)}/')
    print(f'  Dirs:      {dirs}')
    print(f'  Mode:      {mode_label}')
    print(f'  Size:      {size}')
    print(f'  Quality:   {args.quality}')
    print(f'  API-Calls: {n_calls}')
    print(f'  Kosten:    ~${cost:.2f} USD (Schaetzung)')
    print('=' * 60)

    if args.dry_run:
        print('\n--- DRY-RUN PROMPTS ---')
        for d in dirs:
            if per_frame:
                for i in range(8):
                    print(f'\n[{d} frame {i+1}]')
                    print(build_frame_prompt(args.cls, d, i))
            else:
                print(f'\n[{d}]')
                print(build_strip_prompt(args.cls, d))
        return

    # Warne wenn Output ueberschrieben wird
    will_overwrite = [
        out_dir / f'{d}.png' for d in dirs
        if (out_dir / f'{d}.png').exists()
    ]
    if will_overwrite:
        print(f'\n[!] Werden ueberschrieben: '
              f'{[p.name for p in will_overwrite]}')

    if not args.yes:
        try:
            ans = input('Generieren? [y/N]: ').strip().lower()
        except EOFError:
            ans = ''
        if ans not in ('y', 'yes', 'j', 'ja'):
            print('Abgebrochen.')
            return

    try:
        key = load_openai_key()
    except InvalidKeyFormat as e:
        sys.exit(f'API-Key-Problem: {e}')

    ok, fail = 0, 0
    for d in dirs:
        out_path = out_dir / f'{d}.png'
        print(f'  -> {d}: generiere ({calls_per_dir} call(s)) ...', flush=True)
        if per_frame:
            frame_bytes: list[bytes] = []
            d_fail = False
            for i in range(8):
                prompt = build_frame_prompt(args.cls, d, i)
                try:
                    fb = call_edits_api(
                        key, anchor, prompt, size, args.quality
                    )
                except Exception as e:
                    print(f'     frame {i+1} FAIL: {e}', file=sys.stderr)
                    d_fail = True
                    break
                print(f'     frame {i+1}/8 OK ({len(fb)//1024}K)', flush=True)
                frame_bytes.append(fb)
            if d_fail or len(frame_bytes) != 8:
                fail += 1
                continue
            try:
                composit_horizontal_strip(frame_bytes, out_path)
            except Exception as e:
                print(f'     COMPOSIT FAIL: {e}', file=sys.stderr)
                fail += 1
                continue
            sz_kb = out_path.stat().st_size // 1024
            print(f'     OK -> {out_path.relative_to(PROJECT_ROOT)} '
                  f'({sz_kb}K, 8-frame strip)')
            ok += 1
        else:
            prompt = build_strip_prompt(args.cls, d)
            try:
                img_bytes = call_edits_api(
                    key, anchor, prompt, size, args.quality
                )
            except Exception as e:
                print(f'     FAIL: {e}', file=sys.stderr)
                fail += 1
                continue
            out_path.write_bytes(img_bytes)
            sz_kb = len(img_bytes) // 1024
            print(f'     OK -> '
                  f'{out_path.relative_to(PROJECT_ROOT)} ({sz_kb}K)')
            ok += 1

    print(f'\nFertig. {ok} erfolg, {fail} fehlgeschlagen.')
    if ok > 0:
        print(f'\nIm Game: F5 (Hot-Reload) triggert sprites.reload_sprite_cache().')


if __name__ == '__main__':
    main()
