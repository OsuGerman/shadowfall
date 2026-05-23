"""Parst VELGRAD_VOICE_LINES_POOL.md + VELGRAD_VOICE_CASTING.md zu
einem Manifest, das voice_gen.py abarbeitet.

Output: sounds/voice/voice_manifest.json

Format pro Entry:
  {
    "line_id":   "korven_greeting_01",
    "npc":       "korven",
    "category":  "greeting",
    "text":      "Verbannter. Du riechst nach Seetang.",
    "voice_id":  "21m00Tcm4TlvDq8ikWAM",  # oder None wenn ungesetzt
    "stability": 0.6,
    "similarity_boost": 0.75,
    "style":     0.3,
    "status":    "pending"  # pending|done|failed|skip
  }

Usage:
  python tools/voice_manifest_builder.py [--force]

  --force   Overwrite existing manifest, alle Status zurück auf pending.
            Default: bestehende Stati werden bewahrt (Idempotenz).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Pfad-Setup: tools/ liegt neben den .md-Files
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.voice_config import (  # noqa: E402
    VOICE_POOL_MD, VOICE_CASTING_MD, VOICE_MANIFEST_JSON,
    DEFAULT_VOICE_SETTINGS,
)


# ============================================================
# NPC-NAME -> Manifest-Key Mapping
# ============================================================
NPC_KEY = {
    'KORVEN VOR':                      'korven',
    'BRUDER HELST DER HUNDERTJÄHRIGE': 'helst',
    'VOSSHARIL DIE DREIMALIGE':        'vossharil',
    'TAMERIS DIE LICHTSUCHERIN':       'tameris',
    'OTRETH HOHLAUGE':                 'otreth',
    'MARA DIE MAHNERIN':               'mara',
    'INQUISITOR-GENERAL VEHREN':       'vehren',
    'DIE DREI MÜTTER':                 'drei_muetter',
    # Spieler-Klassen
    'WARRIOR':    'cls_warrior',
    'MONK':       'cls_monk',
    'SORCERESS':  'cls_sorceress',
    'WITCH':      'cls_witch',
    'RANGER':     'cls_ranger',
    'MERCENARY':  'cls_mercenary',
    'HUNTRESS':   'cls_huntress',
    'DRUID':      'cls_druid',
}


# Section-Heading -> Category
SECTION_KEY = {
    'Greetings':              'greeting',
    'Quest-Offering':         'quest_offer',
    'Quest-Offering / Story': 'quest_offer',
    'Combat / Casual':        'combat',
    'Combat / Pep':           'combat',
    'Combat':                 'combat',
    'Twist-Reveal-Lines':     'twist_reveal',
    'Lore-Drops':             'lore',
    'Service-Offering':       'service',
    'Death / Farewell':       'death',
    'Spezial':                'special',
    'Spezial — Akt-Trigger-Lines': 'special_akt',
    'Atlas / Endgame-Direction':   'atlas',
    'Phase-Transition':       'phase_transition',
    'Last Words':             'death',
    'Threats / Boss-Lines':   'boss_threat',
    'Trial-Intro':            'trial_intro',
    'Trial-Hints':            'trial_hint',
    'Ascendancy-Award':       'ascendancy',
    'Endgame-Reveal':         'endgame_reveal',
    'Reveal-Lines':           'reveal',
    'Pickup-Reactions':       'pickup',
    'Boss-Encounters':        'boss_encounter',
    'Death-Lines':            'death',
    'Wake-Up-Quotes':         'wakeup',
}


# ============================================================
# VOICE-POOL-PARSER
# ============================================================
def parse_voice_pool(md_path: Path) -> list[dict]:
    """Liest die Voice-Pool-MD und gibt eine Line-Liste zurück."""
    text = md_path.read_text(encoding='utf-8')
    lines_out: list[dict] = []

    current_npc_key:      str | None = None
    current_category:     str | None = None
    line_counter:         dict[tuple[str, str], int] = {}

    for raw_line in text.splitlines():
        line = raw_line.rstrip()

        # NPC-Header: "## NPC 1 — KORVEN VOR (..." oder "### KLASSE 1 — WARRIOR (..."
        m = re.match(r'^##\s*NPC\s*\d+\s*[—-]\s*([A-ZÄÖÜ \-]+?)\s*\(', line)
        if m:
            name = m.group(1).strip().upper()
            current_npc_key = NPC_KEY.get(name)
            current_category = None
            continue
        m = re.match(r'^###\s*KLASSE\s*\d+\s*[—-]\s*([A-ZÄÖÜ]+)', line)
        if m:
            name = m.group(1).strip().upper()
            current_npc_key = NPC_KEY.get(name)
            current_category = None
            continue
        # Generic-Section-Header (alle Klassen)
        m = re.match(r'^##\s*GENERIC\s+SITUATIONAL\s+LINES', line, re.IGNORECASE)
        if m:
            current_npc_key = 'generic'
            current_category = None
            continue

        # Section-Header "### A. Greetings" etc.
        m = re.match(r'^###\s*[A-Z]\.\s*(.+?)\s*$', line)
        if m:
            section_title = m.group(1).strip()
            # Klammern entfernen
            section_title_base = re.sub(r'\s*\([^)]*\)\s*$', '', section_title).strip()
            current_category = SECTION_KEY.get(section_title_base) or \
                               SECTION_KEY.get(section_title) or \
                               re.sub(r'[^a-z0-9]+', '_', section_title.lower()).strip('_')
            continue
        # Section-Header ohne A./B. Buchstaben (Generic-Block)
        m = re.match(r'^###\s+(.+?)\s*$', line)
        if m and current_npc_key == 'generic':
            section_title = m.group(1).strip()
            current_category = SECTION_KEY.get(section_title) or \
                               re.sub(r'[^a-z0-9]+', '_', section_title.lower()).strip('_')
            continue

        # Line-Item Format A: numbered "1. „...""  oder bullet "- „..."" oder
        # bullet mit italic-Prefix "- *Trigger:* „...""
        if current_npc_key and current_category:
            list_prefix = re.match(r'^\s*(?:\d+\.|[-*])\s+', line)
            if list_prefix:
                m = re.search(r'[„"]([^„""]+?)[""]', line)
                if m:
                    text_line = m.group(1).strip()
                    if len(text_line) >= 3:
                        key = (current_npc_key, current_category)
                        line_counter[key] = line_counter.get(key, 0) + 1
                        idx = line_counter[key]
                        lines_out.append(dict(
                            line_id=f'{current_npc_key}_{current_category}_{idx:02d}',
                            npc=current_npc_key,
                            category=current_category,
                            text=text_line,
                        ))
                        continue

        # Line-Item Format B: **Label:** „Line1" / „Line2" / „Line3"
        # (genutzt in SPIELER-KLASSEN und GENERIC SITUATIONAL LINES)
        # Auch bullet-prefixed: "- **Label:** „...""
        if current_npc_key:
            m_label = re.match(
                r'^\s*(?:-\s*)?\*\*([^*]+?):\*\*\s*(.*)$', line)
            if m_label:
                label = m_label.group(1).strip()
                rest  = m_label.group(2)
                # Voice-Notes etc. überspringen — die enthalten keine „"-Lines
                if label.lower() in ('voice-notes', 'akzent', 'akzent-hinweis',
                                     'triggers'):
                    continue
                # Category aus Label normalisieren
                inline_cat = re.sub(r'[^a-z0-9]+', '_',
                                    label.lower()).strip('_') or 'misc'
                # Alle „..." Quotes in der Restzeile rausholen
                quotes = re.findall(r'[„"]([^„""]+?)[""]', rest)
                for q in quotes:
                    text_line = q.strip()
                    if len(text_line) >= 2:
                        key = (current_npc_key, inline_cat)
                        line_counter[key] = line_counter.get(key, 0) + 1
                        idx = line_counter[key]
                        lines_out.append(dict(
                            line_id=f'{current_npc_key}_{inline_cat}_{idx:02d}',
                            npc=current_npc_key,
                            category=inline_cat,
                            text=text_line,
                        ))

    return lines_out


# ============================================================
# CASTING-PARSER (voice_id-Lookup pro NPC)
# ============================================================
NPC_CASTING_PATTERNS = {
    'korven':       r'###\s+1\.\s+Korven\s+Vor',
    'helst':        r'###\s+2\.\s+Bruder\s+Helst',
    'vossharil':    r'###\s+3\.\s+Vossharil',
    'tameris':      r'###\s+4\.\s+Tameris',
    'otreth':       r'###\s+5\.\s+Otreth',
    'mara':         r'###\s+6\.\s+Mara',
    'vehren':       r'###\s+7\.\s+Inquisitor[- ]General\s+Vehren',
    'drei_muetter': r'###\s+8a\.\s+Drei\s+M(?:ue|ü)tter',
}

# Spieler-Klassen: Voice-IDs stehen in einer Tabelle in Sektion III
# Format-Zeile: | Warrior | M | Tief, ... | Arnold | `VR6AewLTigWG4xSOukaG` |
CLASS_TABLE_PATTERNS = {
    'cls_warrior':   r'\|\s*Warrior\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_monk':      r'\|\s*Monk\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_sorceress': r'\|\s*Sorceress\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_witch':     r'\|\s*Witch\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_ranger':    r'\|\s*Ranger\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_mercenary': r'\|\s*Mercenary\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_huntress':  r'\|\s*Huntress\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
    'cls_druid':     r'\|\s*Druid\s*\|[^|]+\|[^|]+\|[^|]+\|\s*`([^`]+)`',
}


def parse_casting(md_path: Path) -> dict[str, dict]:
    """Liest die Casting-MD und gibt pro NPC-Key ein Settings-Dict.

    {
      'korven': {
         'voice_id': '21m00Tcm...' | None,
         'stability': 0.6,
         'similarity_boost': 0.75,
         'style': 0.3,
      },
      ...
    }
    """
    if not md_path.is_file():
        return {}
    text = md_path.read_text(encoding='utf-8')
    result: dict[str, dict] = {}

    for npc_key, pattern in NPC_CASTING_PATTERNS.items():
        m = re.search(pattern, text)
        if not m:
            continue
        # Block nach dem Header bis zum nächsten ### oder ---
        start = m.end()
        rest = text[start:start + 1500]
        block = re.split(r'\n###\s|\n---\s', rest, maxsplit=1)[0]

        def find(pat, default=None, cast=str):
            m2 = re.search(pat, block)
            if not m2:
                return default
            try:
                return cast(m2.group(1).strip())
            except (ValueError, TypeError):
                return default

        voice_id  = find(r'\*\*voice_id:\*\*\s*`([^`]+)`')
        stability = find(r'\*\*stability:\*\*\s*([0-9.]+)', cast=float)
        sim_boost = find(r'\*\*similarity_boost:\*\*\s*([0-9.]+)', cast=float)
        style     = find(r'\*\*style:\*\*\s*([0-9.]+)', cast=float)

        # Underscores oder Platzhalter -> als ungesetzt werten
        if voice_id and ('___' in voice_id or voice_id.startswith('__')):
            voice_id = None

        result[npc_key] = dict(
            voice_id=voice_id,
            stability=stability if stability is not None else DEFAULT_VOICE_SETTINGS['stability'],
            similarity_boost=sim_boost if sim_boost is not None else DEFAULT_VOICE_SETTINGS['similarity_boost'],
            style=style if style is not None else DEFAULT_VOICE_SETTINGS['style'],
        )

    # Klassen-Tabelle in Sektion III
    for cls_key, pat in CLASS_TABLE_PATTERNS.items():
        m = re.search(pat, text)
        if m:
            vid = m.group(1).strip()
            if '__' not in vid and '___' not in vid:
                result[cls_key] = dict(
                    voice_id=vid,
                    stability=DEFAULT_VOICE_SETTINGS['stability'],
                    similarity_boost=DEFAULT_VOICE_SETTINGS['similarity_boost'],
                    style=DEFAULT_VOICE_SETTINGS['style'],
                )

    # Generic-Pool: nutzt Mara-Stimme als Default (kannst du im Doc ueberschreiben)
    if 'mara' in result and 'generic' not in result:
        result['generic'] = dict(result['mara'])

    return result


# ============================================================
# MANIFEST-BUILD
# ============================================================
def build_manifest(force: bool = False) -> dict:
    pool_lines = parse_voice_pool(VOICE_POOL_MD)
    casting    = parse_casting(VOICE_CASTING_MD)

    # Bestehendes Manifest laden für Idempotenz
    existing: dict[str, dict] = {}
    if VOICE_MANIFEST_JSON.is_file() and not force:
        try:
            data = json.loads(VOICE_MANIFEST_JSON.read_text(encoding='utf-8'))
            existing = {e['line_id']: e for e in data.get('entries', [])}
        except json.JSONDecodeError:
            existing = {}

    entries = []
    for pl in pool_lines:
        npc_cast = casting.get(pl['npc'], {})
        entry = dict(
            line_id=pl['line_id'],
            npc=pl['npc'],
            category=pl['category'],
            text=pl['text'],
            voice_id=npc_cast.get('voice_id'),
            stability=npc_cast.get('stability', DEFAULT_VOICE_SETTINGS['stability']),
            similarity_boost=npc_cast.get('similarity_boost',
                                          DEFAULT_VOICE_SETTINGS['similarity_boost']),
            style=npc_cast.get('style', DEFAULT_VOICE_SETTINGS['style']),
            status='pending',
        )
        # Status bewahren
        if entry['line_id'] in existing:
            entry['status'] = existing[entry['line_id']].get('status', 'pending')

        entries.append(entry)

    manifest = dict(
        version=1,
        plan='creator',
        total_lines=len(entries),
        total_chars=sum(len(e['text']) for e in entries),
        entries=entries,
    )
    VOICE_MANIFEST_JSON.parent.mkdir(parents=True, exist_ok=True)
    VOICE_MANIFEST_JSON.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding='utf-8',
    )
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--force', action='store_true',
                    help='Manifest neu bauen, Stati zurücksetzen')
    args = ap.parse_args()

    manifest = build_manifest(force=args.force)
    print(f'Manifest geschrieben: {VOICE_MANIFEST_JSON}')
    print(f'  Lines:  {manifest["total_lines"]}')
    print(f'  Chars:  {manifest["total_chars"]:,}')

    # NPC-Aufschlüsselung
    by_npc: dict[str, int] = {}
    for e in manifest['entries']:
        by_npc[e['npc']] = by_npc.get(e['npc'], 0) + 1
    for npc, count in sorted(by_npc.items(), key=lambda x: -x[1]):
        print(f'    {npc:20s} {count:4d} lines')

    # Voice-ID-Coverage
    no_voice = [e for e in manifest['entries'] if not e['voice_id']]
    if no_voice:
        unique_npcs = sorted({e['npc'] for e in no_voice})
        print(f'\nWARN: {len(no_voice)} Lines haben keine voice_id (NPCs: '
              f'{", ".join(unique_npcs)})')
        print('  -> Voice-IDs in VELGRAD_VOICE_CASTING.md eintragen, dann '
              'erneut bauen.')


if __name__ == '__main__':
    main()
