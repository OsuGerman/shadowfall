"""Scenario.gg API-Key-Loader + Sprite-Pipeline-Konfiguration.

Liest id + secret aus (in dieser Reihenfolge):
  1. Env-Variablen SCENARIO_API_KEY + SCENARIO_API_SECRET
  2. Datei .scenario_key   (Format: id=...\\nsecret=...)
  3. Datei scenario.txt    (gleiches Format ODER CSV-Header id,secret)
  4. Datei shadowfall.csv  (CSV-Header id,secret + Daten-Zeile)

WICHTIG — Sicherheits-Lessons aus dem ElevenLabs-Vorfall:
  - Nur die EINE Zeile / EIN Token pro Feld wird genutzt.
  - Whitespace / Control-Chars im Token → Abbruch (kein API-Call).
  - Datei-Inhalt wird NIEMALS geloggt, gedruckt oder in Fehler-Stacks
    ausgegeben — bei Fehler steht im Stack nur 'INVALID_KEY_FORMAT'.

Scenario.gg API-Doku: https://docs.scenario.com/reference/
Authorization-Header: `Basic base64(id:secret)`
"""
from __future__ import annotations

import base64
import os
import re
from pathlib import Path


# ============================================================
# PROJEKT-PFADE
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
SPRITES_DIR  = PROJECT_ROOT / 'assets' / 'sprites'
PORTRAITS_DIR = PROJECT_ROOT / 'assets' / 'portraits'
TILES_DIR    = PROJECT_ROOT / 'assets' / 'tiles'
ITEMS_DIR    = PROJECT_ROOT / 'assets' / 'items'
SPRITE_MANIFEST_JSON = PROJECT_ROOT / 'assets' / 'sprite_manifest.json'

# Scenario-API-Endpoints (Stand 2026)
API_BASE      = 'https://api.cloud.scenario.com/v1'
ENDPOINT_GENERATE = '/generate/txt2img'  # text-to-image
ENDPOINT_INFERENCE = '/inferences'
ENDPOINT_MODELS   = '/models'

# ============================================================
# DEFAULT-MODELS pro Sprite-Kategorie (Scenario.gg Public-LoRAs)
# ============================================================
# Recherche-Ergebnis aus tools/scenario_list_models.py:
#   "El Diablo"       (model_a2dvNsgst7PCnpiucRY7bEHW)
#     tags: dark, dungeon, isometric  → POE2-Style fuer Mobs/Klassen/Bosse
#   "RPG Avatars"     (model_8Hch3Xqx9rehiKi3jqhCjo8q)
#     tags: character portraits, fantasy, painterly → fuer NPC-Portraits
#   "RPG Environment" (model_EEDXdL4VrRjC5CDXbSddKqj3)
#     tags: Deacon, Flux LoRA, fantasy, rpg props → fuer Tilesets
#   "Fantasy Blades"  (model_FHNbZENXLkay9bUNwMxo8e77)
#     tags: detailed, fantasy weapons → fuer Item-Icons
DEFAULT_MODELS = {
    'mob':        'model_a2dvNsgst7PCnpiucRY7bEHW',  # El Diablo
    'class':      'model_a2dvNsgst7PCnpiucRY7bEHW',  # El Diablo
    'boss_plate': 'model_a2dvNsgst7PCnpiucRY7bEHW',  # El Diablo
    'portrait':   'model_8Hch3Xqx9rehiKi3jqhCjo8q',  # RPG Avatars
    # Update: 'tile' switched zu "Hand-Painted Textures" (sc:texture-Tag).
    # 1. Versuch (RPG Environment) gab Concept-Art mit Architektur.
    # 2. Versuch (Super Top-Down 2.0) gab Game-Maps mit Walls+Charakter.
    # 3. Hand-Painted Textures: tags painterly + sc:texture → wirklich
    #    seamless POE2-Material-Textures.
    'tile':       'model_ySKF8HKAzhQneW5ZQF6w3DDk',  # Hand-Painted Textures
    'item_icon':  'model_FHNbZENXLkay9bUNwMxo8e77',  # Fantasy Blades
}


def model_for_category(category: str) -> str:
    """Returnt die Default-Model-ID fuer eine Sprite-Kategorie."""
    return DEFAULT_MODELS.get(category, DEFAULT_MODELS['mob'])

# ============================================================
# SCENARIO-PLAN-LIMITS
# ============================================================
# Stand 2026 (kann sich aendern; konkrete Zahlen vom User-Plan abhaengig)
PLAN_LIMITS = {
    'free':       {'images_per_month': 100,   'concurrent': 1},
    'creator':    {'images_per_month': 5000,  'concurrent': 4},
    'pro':        {'images_per_month': 20000, 'concurrent': 8},
    'enterprise': {'images_per_month': 99999, 'concurrent': 16},
}
ACTIVE_PLAN = 'creator'  # default Annahme, User kann ueberschreiben


# ============================================================
# KEY-LOADING
# ============================================================
_TOKEN_RE = re.compile(r'^[A-Za-z0-9_\-+/=]+$')


def _sanitize_token(s: str) -> str | None:
    """Validate that a string is a clean API token (no whitespace, no
    control chars, only base64-friendly alphabet). Returns the token if
    valid, None otherwise. Never logs the token itself.
    """
    if not s:
        return None
    s = s.strip().strip('"').strip("'").strip()
    if not s:
        return None
    if any(c.isspace() or ord(c) < 32 for c in s):
        return None
    if not _TOKEN_RE.match(s):
        return None
    return s


def _parse_keyval(content: str) -> tuple[str | None, str | None]:
    """Robust id+secret extraction:
    - `id=...` / `secret=...` (with optional whitespace + quotes)
    - CSV-Header `id,secret\\n<id>,<secret>`
    - 2 Zeilen (Zeile 1 = id, Zeile 2 = secret) als Fallback
    """
    api_id, api_secret = None, None

    # Variante A: key=value pro Zeile
    for line in content.splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if '=' in line:
            k, _, v = line.partition('=')
            k = k.strip().lower()
            v = v.strip().strip('"').strip("'").strip()
            if k in ('id', 'api_id', 'apikey', 'key', 'api_key'):
                api_id = api_id or v
            elif k in ('secret', 'api_secret', 'apisecret'):
                api_secret = api_secret or v

    if api_id and api_secret:
        return _sanitize_token(api_id), _sanitize_token(api_secret)

    # Variante B: CSV-Header (id,secret) + Daten-Zeile
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    if len(lines) >= 2:
        header = [h.strip().lower() for h in lines[0].split(',')]
        data   = [d.strip() for d in lines[1].split(',')]
        if 'id' in header and 'secret' in header and len(data) >= 2:
            i_idx = header.index('id')
            s_idx = header.index('secret')
            if i_idx < len(data) and s_idx < len(data):
                return _sanitize_token(data[i_idx]), _sanitize_token(data[s_idx])

    # Variante C: 2 Zeilen, erste = id, zweite = secret
    if len(lines) >= 2:
        a = _sanitize_token(lines[0])
        b = _sanitize_token(lines[1])
        if a and b:
            return a, b

    return _sanitize_token(api_id), _sanitize_token(api_secret)


def load_credentials() -> tuple[str, str]:
    """Returns (api_id, api_secret). Raises RuntimeError if invalid.

    The raised RuntimeError never contains the credentials themselves —
    only a hint where the user should look. Stack-Traces are safe.
    """
    # 1. Env-Variablen
    env_id  = os.environ.get('SCENARIO_API_KEY', '').strip()
    env_sec = os.environ.get('SCENARIO_API_SECRET', '').strip()
    if env_id and env_sec:
        clean_id  = _sanitize_token(env_id)
        clean_sec = _sanitize_token(env_sec)
        if clean_id and clean_sec:
            return clean_id, clean_sec
        raise RuntimeError(
            'Scenario-Credentials in Env-Vars enthalten Whitespace oder '
            'Steuerzeichen. SCENARIO_API_KEY + SCENARIO_API_SECRET pruefen.')

    # 2-4. Dateien
    for candidate in ('.scenario_key', 'scenario.txt', 'Scenario.txt',
                      'shadowfall.csv'):
        path = PROJECT_ROOT / candidate
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError):
            continue
        api_id, api_secret = _parse_keyval(content)
        if api_id and api_secret:
            return api_id, api_secret

    raise RuntimeError(
        'Scenario-Credentials nicht gefunden. Lege id+secret ab in:\n'
        '  1. Env-Vars SCENARIO_API_KEY + SCENARIO_API_SECRET, oder\n'
        f'  2. {PROJECT_ROOT / ".scenario_key"} (id=... / secret=...), oder\n'
        f'  3. {PROJECT_ROOT / "scenario.txt"} (id=... / secret=...), oder\n'
        f'  4. {PROJECT_ROOT / "shadowfall.csv"} (CSV: id,secret).\n'
        'WICHTIG: Datei niemals committen (.gitignore-Eintrag pruefen).')


def auth_header() -> dict:
    """Build the Authorization header for Scenario API calls.

    Returns dict with Basic-Auth header. Never logs the encoded value.
    """
    api_id, api_secret = load_credentials()
    token = base64.b64encode(f'{api_id}:{api_secret}'.encode('utf-8')).decode('ascii')
    return {
        'Authorization': f'Basic {token}',
        'Content-Type':  'application/json',
        'Accept':        'application/json',
    }


# ============================================================
# SPRITE-PIPELINE-KATEGORIEN (was generiert wird)
# ============================================================
# Aligned mit ROADMAP.md TIER 2.2 + TIER 3.4
SPRITE_CATEGORIES = {
    'mob': dict(
        out_dir='mobs',
        size=(512, 512),
        steps=30,
        targets=[
            # Phase 1 (TIER 2.2-E) — 6 Lore-Mobs
            'salzhueter_brut', 'glaslord', 'vehren_echo',
            'ertrunkene_koenigin', 'aschenbrut', 'wurzelhueter',
        ],
    ),
    'class': dict(
        out_dir='classes',
        size=(512, 768),
        steps=30,
        targets=[
            # Phase 1 (TIER 2.2-F) — 3 Klassen
            'warrior', 'witch', 'sorceress',
            # Phase 2 (TIER 3.4-A) — 5 weitere
            'monk', 'ranger', 'mercenary', 'huntress', 'druid',
        ],
    ),
    'portrait': dict(
        out_dir='portraits',
        size=(256, 256),
        steps=25,
        targets=[
            # TIER 2.2-G — 8 NPC-Portraits
            'korven', 'helst', 'vossharil', 'tameris',
            'otreth', 'mara', 'vehren', 'drei_muetter',
        ],
    ),
    'boss_plate': dict(
        out_dir='bosses',
        size=(512, 512),
        steps=30,
        targets=[
            # TIER 3.4-B — Boss-Concept-Plates
            'salzhueter_brut', 'vehren', 'senator_geist', 'shulavh',
            'velharn_trio', 'ertrunkene_koenigin', 'echo_drache',
            'nicht_gott',
        ],
    ),
    'item_icon': dict(
        out_dir='items',
        size=(128, 128),
        steps=20,
        targets=[],  # Wird aus VELGRAD_ITEMS_UNIQUE_BIBEL.md geparst
    ),
    'tile': dict(
        out_dir='tiles',
        size=(512, 512),
        steps=25,
        targets=[
            # TIER 3.4-D — Tilesets pro Biome (512×512 → wird in 32×32 zerschnitten)
            'crypt', 'frost', 'lava', 'swamp',
            'astral', 'desert', 'town',
            # Akt 6/7 Biomes (neu)
            'wound_salt', 'wound_ash', 'wound_hollow', 'hollow_word',
        ],
    ),
}


def plan_budget() -> int:
    """Returns max images per month for the active plan."""
    return PLAN_LIMITS.get(ACTIVE_PLAN, PLAN_LIMITS['free'])['images_per_month']


def total_targets() -> int:
    """Total number of sprite targets across all categories."""
    return sum(len(c['targets']) for c in SPRITE_CATEGORIES.values())


if __name__ == '__main__':
    # Diagnose ohne Credentials-Leak
    try:
        api_id, _ = load_credentials()
        # Nur die ersten 6 Zeichen der ID drucken, Secret NIE
        masked = api_id[:6] + '…' if len(api_id) > 6 else '…'
        print(f'OK — Scenario-Credentials geladen (ID-Prefix: {masked})')
    except RuntimeError as e:
        print(f'FEHLER: {e}')
    print(f'Plan: {ACTIVE_PLAN}, Budget: {plan_budget()} Bilder/Monat')
    print(f'Sprite-Targets: {total_targets()} total')
    for cat, cfg in SPRITE_CATEGORIES.items():
        print(f'  {cat:<12} {len(cfg["targets"]):>3} targets, {cfg["size"]}')
