"""Velgrad Stack-Diagnose-Tool (Update #179).

Listet was im Projekt aktuell verfuegbar ist — Libraries, Engine-Module,
CLI-Tools, Docs. Komplementaer zu VELGRAD_TOOLBOX.md (curated by hand).

Wenn TOOLBOX.md sagt "X gibt's" aber list_stack.py findet's nicht →
Inkonsistenz. Wenn list_stack.py findet "Y" aber TOOLBOX.md erwaehnt es
nicht → Doc-Update faellig.

Usage:
  python tools/list_stack.py              # human-readable Tabellen
  python tools/list_stack.py --json       # JSON-Output (fuer scripts)
  python tools/list_stack.py --check      # Mismatch-Detector vs TOOLBOX.md
"""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SF_DIR = PROJECT_ROOT / 'sf'
TOOLS_DIR = PROJECT_ROOT / 'tools'
TOOLBOX_MD = PROJECT_ROOT / 'VELGRAD_TOOLBOX.md'


# ============================================================
# LIBRARIES
# ============================================================
# Die Libraries die wir aktiv nutzen. Format: (import_name, friendly_name,
# is_critical). is_critical=True → wenn fehlend, Engine kaputt.
TRACKED_LIBRARIES = [
    ('pygame',              'pygame-ce',          True),
    ('numpy',               'numpy',              True),
    ('OpenGL',              'PyOpenGL',           False),
    ('pymunk',              'pymunk',             False),
    ('pytmx',               'pytmx',              False),
]


def inspect_libraries() -> list[dict]:
    """Returnt list[dict] mit installed library info."""
    out = []
    for import_name, friendly, critical in TRACKED_LIBRARIES:
        info = {'name': friendly, 'import': import_name, 'critical': critical}
        try:
            mod = importlib.import_module(import_name)
            # Try common version attrs
            for attr in ('__version__', 'version', 'VERSION'):
                v = getattr(mod, attr, None)
                if v is not None:
                    info['version'] = str(v) if not isinstance(v, tuple) \
                        else '.'.join(str(x) for x in v)
                    break
            else:
                info['version'] = 'unknown'
            info['installed'] = True
        except ImportError:
            info['installed'] = False
            info['version'] = None
        out.append(info)
    return out


# ============================================================
# ENGINE-MODULE (sf/)
# ============================================================
def inspect_engine_modules() -> list[dict]:
    """Inventar von sf/*.py. Extrahiert 1-Line-Docstring."""
    out = []
    if not SF_DIR.is_dir():
        return out
    for f in sorted(SF_DIR.glob('*.py')):
        if f.name.startswith('_'):
            continue
        info = {'module': f.stem, 'path': f'sf/{f.name}'}
        info['docstring'] = _extract_first_line_docstring(f)
        info['loc'] = _count_loc(f)
        out.append(info)
    return out


# ============================================================
# CLI-TOOLS (tools/)
# ============================================================
def inspect_tools() -> list[dict]:
    """Inventar von tools/*.py. Extrahiert 1-Line-Docstring."""
    out = []
    if not TOOLS_DIR.is_dir():
        return out
    for f in sorted(TOOLS_DIR.glob('*.py')):
        if f.name in ('__init__.py',):
            continue
        info = {'tool': f.stem, 'path': f'tools/{f.name}'}
        info['docstring'] = _extract_first_line_docstring(f)
        info['loc'] = _count_loc(f)
        out.append(info)
    return out


# ============================================================
# DOCS (VELGRAD_*.md + Top-Level Markdown)
# ============================================================
def inspect_docs() -> list[dict]:
    """Inventar von VELGRAD_*.md + anderen Root-Docs."""
    out = []
    interesting = (
        'VELGRAD_TOOLBOX.md', 'VELGRAD_RENDER_SPEC.md',
        'VELGRAD_WORKFLOWS_BIBEL.md', 'VELGRAD_SPRITE_BIBEL.md',
        'VELGRAD_SFX_BIBEL.md', 'VELGRAD_VOICE_CASTING.md',
        'VELGRAD_VOICE_LINES_POOL.md', 'VELGRAD_AUDIO_DESIGN_BIBEL.md',
        'VELGRAD_LORE_BIBEL.md', 'VELGRAD_BESTIARIUM.md',
        'VELGRAD_ITEMS_UNIQUE_BIBEL.md',
        'PLAN.md', 'ROADMAP.md', 'WELT_AUFBAU.md', 'QUEST_BIBEL.md',
        'CHANGELOG.md', 'README.md', 'CLAUDE.md',
    )
    for name in interesting:
        p = PROJECT_ROOT / name
        if p.is_file():
            out.append({
                'doc':  name,
                'size_kb': round(p.stat().st_size / 1024, 1),
                'lines':   _count_lines(p),
            })
    return out


# ============================================================
# ASSET-COUNT (Quick-Heuristic)
# ============================================================
def inspect_assets() -> dict:
    """Asset-Inventar (Sprites + Maps + Sounds + Voice)."""
    counts = {}
    for label, glob_pattern in [
        ('sprites_total',     'assets/sprites/**/*.png'),
        ('class_static',      'assets/sprites/classes/*.png'),
        ('class_anims',       'assets/sprites/classes/**/*_anims/**/*.png'),
        ('tiles',             'assets/sprites/tiles/*.png'),
        ('tile_masks',        'assets/sprites/tiles/masks/**/*.png'),
        ('mobs',              'assets/sprites/mobs/*.png'),
        ('bosses',            'assets/sprites/bosses/*.png'),
        ('portraits',         'assets/sprites/portraits/*.png'),
        ('maps_tmx',          'assets/maps/**/*.tmx'),
        ('voice_mp3',         'Sounds/voice/**/*.mp3'),
        ('sfx_mp3',           'Sounds/sfx/**/*.mp3'),
    ]:
        cnt = len(list(PROJECT_ROOT.glob(glob_pattern)))
        counts[label] = cnt
    return counts


# ============================================================
# HELPERS
# ============================================================
def _extract_first_line_docstring(path: Path) -> str:
    """Holt die 1. Zeile des Module-Docstrings (oder leeren str)."""
    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return ''
    in_doc = False
    quote_chars = ('"""', "'''")
    for line in lines[:60]:
        s = line.strip()
        if not in_doc:
            for q in quote_chars:
                if s.startswith(q):
                    after = s[len(q):]
                    if after and not after.startswith(q):
                        return after.rstrip(q).strip()
                    in_doc = True
                    break
            if in_doc:
                continue
        else:
            if s:
                return s
    return ''


def _count_loc(path: Path) -> int:
    """Code-Lines (ohne leere oder Kommentar-only)."""
    try:
        lines = path.read_text(encoding='utf-8', errors='ignore').splitlines()
    except Exception:
        return 0
    return sum(1 for line in lines
                if line.strip() and not line.strip().startswith('#'))


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.read_text(encoding='utf-8',
                                              errors='ignore').splitlines())
    except Exception:
        return 0


# ============================================================
# TOOLBOX-COMPLIANCE-CHECK
# ============================================================
def check_toolbox_consistency() -> list[str]:
    """Prueft ob TOOLBOX.md alle aktuellen Tools/Module erwaehnt.
    Returnt Liste der Inkonsistenzen."""
    if not TOOLBOX_MD.is_file():
        return ['VELGRAD_TOOLBOX.md fehlt!']
    toolbox_text = TOOLBOX_MD.read_text(encoding='utf-8', errors='ignore')
    issues = []
    # Engine-Module
    for mod_info in inspect_engine_modules():
        mod = mod_info['module']
        if f'sf/{mod}.py' not in toolbox_text and mod not in toolbox_text:
            issues.append(
                f'Modul sf/{mod}.py nicht in TOOLBOX.md erwaehnt')
    # CLI-Tools
    for tool_info in inspect_tools():
        tool = tool_info['tool']
        if f'tools/{tool}.py' not in toolbox_text and tool not in toolbox_text:
            issues.append(
                f'Tool tools/{tool}.py nicht in TOOLBOX.md erwaehnt')
    return issues


# ============================================================
# OUTPUT-FORMATTER
# ============================================================
def _safe_str(s) -> str:
    """Strip non-ASCII Chars (cp1252-Console-Safety)."""
    return str(s).encode('ascii', 'replace').decode('ascii')


def _print_table(title: str, headers: list[str], rows: list[list]) -> None:
    if not rows:
        return
    # Sanitize rows fuer cp1252-Console
    rows = [[_safe_str(c) for c in row] for row in rows]
    # Compute column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    print(f'\n=== {title} ===')
    hdr = '  '.join(h.ljust(w) for h, w in zip(headers, widths))
    print(hdr)
    print('-' * len(hdr))
    for row in rows:
        print('  '.join(c.ljust(w) for c, w in zip(row, widths)))


def main():
    ap = argparse.ArgumentParser(description='Velgrad Stack-Diagnose')
    ap.add_argument('--json', action='store_true',
                    help='JSON-Output statt human-Tabelle')
    ap.add_argument('--check', action='store_true',
                    help='Mismatch-Check vs TOOLBOX.md')
    args = ap.parse_args()

    libs   = inspect_libraries()
    sf_mod = inspect_engine_modules()
    tools  = inspect_tools()
    docs   = inspect_docs()
    assets = inspect_assets()

    if args.json:
        out = {
            'libraries':       libs,
            'engine_modules':  sf_mod,
            'cli_tools':       tools,
            'docs':            docs,
            'assets':          assets,
        }
        if args.check:
            out['toolbox_issues'] = check_toolbox_consistency()
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    # Human-readable
    print('=' * 70)
    print('  VELGRAD STACK DIAGNOSTIC')
    print('  Doku: VELGRAD_TOOLBOX.md')
    print('=' * 70)

    # Libraries
    _print_table(
        '1. LIBRARIES (pip-installed)',
        ['Name', 'Version', 'Status'],
        [[L['name'], L.get('version') or '-',
          ('OK' if L['installed'] else
           ('MISSING (critical)' if L['critical'] else 'optional, not installed'))]
         for L in libs],
    )

    # Engine modules
    _print_table(
        f'2. ENGINE-MODULE ({len(sf_mod)} Module in sf/)',
        ['Module', 'LOC', 'Docstring'],
        [[m['module'], m['loc'], (m['docstring'] or '-')[:60]]
         for m in sf_mod],
    )

    # CLI tools
    _print_table(
        f'3. CLI-TOOLS ({len(tools)} in tools/)',
        ['Tool', 'LOC', 'Docstring'],
        [[t['tool'], t['loc'], (t['docstring'] or '-')[:60]]
         for t in tools],
    )

    # Docs
    _print_table(
        f'4. DOCS ({len(docs)} Markdown-Files)',
        ['Doc', 'Lines', 'Size (KB)'],
        [[d['doc'], d['lines'], d['size_kb']] for d in docs],
    )

    # Assets
    print(f'\n=== 5. ASSETS ===')
    for k, v in sorted(assets.items()):
        print(f'  {k:<22} {v:>5}')

    # Check-Mode
    if args.check:
        print(f'\n=== 6. TOOLBOX-CONSISTENCY-CHECK ===')
        issues = check_toolbox_consistency()
        if not issues:
            print('  OK — TOOLBOX.md ist konsistent mit aktuellem Stack.')
        else:
            print(f'  {len(issues)} Inkonsistenzen gefunden:')
            for i in issues:
                print(f'    - {i}')

    print()
    print('=' * 70)
    print('  Tip: python tools/list_stack.py --json > stack.json')
    print('  Tip: python tools/list_stack.py --check (Mismatch-Detection)')
    print('=' * 70)


if __name__ == '__main__':
    main()
