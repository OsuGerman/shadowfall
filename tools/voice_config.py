"""Voice-Pipeline Konfiguration & Secret-Loading.

Liest den ElevenLabs-API-Key aus (in dieser Reihenfolge):
  1. Environment-Variable ELEVENLABS_API_KEY
  2. Datei .elevenlabs_key im Projekt-Root
  3. Datei ElevenLabs.txt im Projekt-Root (User-Convenience)

Der Key wird zur Laufzeit gelesen und NIE geloggt, gedruckt oder in
generierten Dateien gespeichert.

Plan-Limits (Stand 2026):
  - Free        : 10k chars / mo, 3 custom voices, kein Pro-Voice-Lib
  - Starter     : 30k chars / mo, kommerzielle Lizenz
  - Creator     : 100k chars / mo, Pro Voice Library
  - Pro         : 500k chars / mo, höhere Qualität
"""
from __future__ import annotations

import os
from pathlib import Path

# ============================================================
# PROJEKT-PFADE
# ============================================================
PROJECT_ROOT = Path(__file__).resolve().parent.parent
TOOLS_DIR    = PROJECT_ROOT / 'tools'
SOUNDS_DIR   = PROJECT_ROOT / 'Sounds'   # bestehender Ordner
VOICE_DIR    = PROJECT_ROOT / 'sounds' / 'voice'
SFX_DIR      = PROJECT_ROOT / 'sounds' / 'sfx' / 'generated'

VOICE_POOL_MD       = PROJECT_ROOT / 'VELGRAD_VOICE_LINES_POOL_EN.md'  # Update #178: EN-Switch
VOICE_POOL_DE_MD    = PROJECT_ROOT / 'VELGRAD_VOICE_LINES_POOL.md'      # Legacy-Quelle, fuer Lore-Bibel
VOICE_CASTING_MD    = PROJECT_ROOT / 'VELGRAD_VOICE_CASTING.md'
VOICE_MANIFEST_JSON = VOICE_DIR / 'voice_manifest.json'
VOICE_REGISTRY_PY   = PROJECT_ROOT / 'sf' / 'voice_registry.py'

# ============================================================
# PLAN-LIMITS
# ============================================================
PLAN_LIMITS = {
    'free':     {'chars_per_month':  10_000, 'model_v3': False},
    'starter':  {'chars_per_month':  30_000, 'model_v3': False},
    'creator':  {'chars_per_month': 100_000, 'model_v3': True},
    'pro':      {'chars_per_month': 500_000, 'model_v3': True},
}
ACTIVE_PLAN = 'creator'     # User-Bestätigung 23.05.2026

# ============================================================
# MODELL & AUDIO-SETTINGS
# ============================================================
# eleven_multilingual_v2 = stabilste deutsche Aussprache, Creator-fähig.
# eleven_v3 (alpha) = bessere Emotion, instabilere Aussprache bei Eigennamen.
TTS_MODEL = 'eleven_multilingual_v2'

# MP3-Output: 44.1 kHz, 128 kbit/s = guter Pygame-Default
OUTPUT_FORMAT = 'mp3_44100_128'

# Default Voice-Settings pro NPC-Kategorie. Werden im Casting pro NPC
# überschrieben.
DEFAULT_VOICE_SETTINGS = dict(
    stability=0.55,         # 0.0 = sehr expressiv, 1.0 = monoton-konsistent
    similarity_boost=0.75,  # wie nah an der Library-Stimme
    style=0.30,             # Emotion-Verstärkung (v2 + v3)
    use_speaker_boost=True,
)

# ============================================================
# PRONUNCIATION-HINTS für Velgrad'sche Eigennamen
# ============================================================
# Update #178 (EN-Switch): Die deutschen Phonetik-Hints (Velgrad -> Wellgrahd
# etc.) wurden deaktiviert. eleven_multilingual_v2 liest englischen Text
# mit englischer Aussprache — deutsche Lautschriften wuerden mit englischer
# Phonetik gemangelt. Eigennamen bleiben in der Originalschreibung;
# Bindestrich-Namen erhalten ein Leerzeichen, damit der TTS keine Pause
# als Wortgrenze interpretiert.
PRONUNCIATION = {
    'Im-Nesh':   'Im Nesh',
    'Zhar-Eth':  'Zhar Eth',
}

# Legacy: deutsche Phonetik (fuer Referenz, falls jemand zurueck switcht)
PRONUNCIATION_DE_LEGACY = {
    'Aithein':   'Aithäin',
    'Im-Nesh':   'Im Nesch',
    'Shulavh':   'Schulawh',
    'Nheyra':    'N-Hejra',
    'Kharn':     'Karn',
    'Ousen':     'Ohsen',
    'Valsa':     'Walsa',
    'Velgrad':   'Wellgrahd',
    'Velharn':   'Welharn',
    'Brassweir': 'Brasswehr',
    'Zhar-Eth':  'Zar-Et',
    'Vossharil': 'Wosharil',
    'Korven':    'Korwen',
    'Tameris':   'Tameris',
    'Otreth':    'Otret',
    'Helst':     'Helst',
    'Vehren':    'Wehren',
}


# ============================================================
# KEY-LOADING
# ============================================================
def load_api_key() -> str:
    """Liest den ElevenLabs-API-Key, raised wenn nicht gefunden.

    Reihenfolge:
      1. Env-Var ELEVENLABS_API_KEY
      2. .elevenlabs_key   (Projekt-Root)
      3. ElevenLabs.txt    (Projekt-Root, User-Convenience)
    """
    env_key = os.environ.get('ELEVENLABS_API_KEY', '').strip()
    if env_key:
        return env_key

    for candidate in ('.elevenlabs_key', 'ElevenLabs.txt'):
        path = PROJECT_ROOT / candidate
        if path.is_file():
            content = path.read_text(encoding='utf-8')
            # Nur die erste nicht-leere Zeile als Key nehmen — User können
            # darunter Plan-Info / Notizen ablegen ohne dass es in den
            # HTTP-Header geleakt wird.
            first_token = None
            for raw_line in content.splitlines():
                line = raw_line.strip().strip('"').strip("'").strip()
                if line:
                    # Falls jemand "API-Key: sk_..." schreibt, nur den Key
                    if ':' in line and line.lower().startswith(('api', 'key', 'sk-', 'bearer')):
                        line = line.split(':', 1)[1].strip()
                    # Whitespace im Token selbst gibt's nie -> wir nehmen
                    # nur den ersten Token (Sicherheits-Backstop)
                    first_token = line.split()[0] if line.split() else None
                    break
            if first_token:
                # Final-Sicherheits-Check: keine Whitespace-/Control-Chars
                if any(c.isspace() or ord(c) < 32 for c in first_token):
                    raise RuntimeError(
                        f'API-Key in {path.name} enthaelt Whitespace oder '
                        'Steuerzeichen. Datei mit NUR dem Key (keine weiteren '
                        'Zeilen) neu schreiben.'
                    )
                return first_token

    raise RuntimeError(
        'Kein ElevenLabs-API-Key gefunden. Lege einen Key ab in:\n'
        f'  1. Env-Variable ELEVENLABS_API_KEY, oder\n'
        f'  2. {PROJECT_ROOT / ".elevenlabs_key"}, oder\n'
        f'  3. {PROJECT_ROOT / "ElevenLabs.txt"}\n'
        'WICHTIG: Datei niemals committen (.gitignore prüfen).'
    )


def plan_char_budget() -> int:
    return PLAN_LIMITS[ACTIVE_PLAN]['chars_per_month']


def cost_estimate_eur(char_count: int) -> float:
    """Grobe Kosten-Schätzung. Creator = 22€ für 100k Chars."""
    eur_per_char = {
        'free':    0.0,
        'starter': 5.0 / 30_000,
        'creator': 22.0 / 100_000,
        'pro':     99.0 / 500_000,
    }[ACTIVE_PLAN]
    return char_count * eur_per_char


def apply_pronunciation(text: str) -> str:
    """Ersetzt Velgrad'sche Eigennamen durch phonetische Schreibung."""
    out = text
    # Längere Namen zuerst (vermeidet Im-Nesh → Im Nesh-arn Konflikt)
    for name in sorted(PRONUNCIATION, key=len, reverse=True):
        out = out.replace(name, PRONUNCIATION[name])
    return out
