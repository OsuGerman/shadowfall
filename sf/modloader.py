"""Mod-Hook-API (PLAN AA-05).

Beim Startup wird der `mods/`-Ordner gescannt.  Jedes `.py`-File mit
einer `register(game)`-Funktion wird registriert.  Mods koennen via
`sf.events.subscribe(...)` (J-12) auf Game-Events reagieren.

API Contract (`mods/example.py`):
    def register(game):
        from sf import events
        events.subscribe(events.EventKey.ON_PLAYER_LEVELUP,
                         lambda payload: print('level up!'))
        # Optional: return a dict with metadata
        return {'name': 'Example', 'version': '0.1.0'}

Sicherheits-Hinweis: Mods koennen beliebigen Python-Code ausfuehren.
Nur trusted Mods nutzen.

Discoverer wird via `Game.__init__` aufgerufen.
"""

import importlib.util
import os
import sys
import traceback
from pathlib import Path


# Audit #179 A.12: Absolute Pfad relativ zum Projekt-Root, nicht zum CWD.
# Vorher: `MOD_DIR = 'mods'` bricht, wenn das Spiel aus einem anderen
# Arbeits-Verzeichnis gestartet wird (z.B. via IDE-Launcher).
MOD_DIR = str(Path(__file__).resolve().parent.parent / 'mods')


class ModLoader:
    def __init__(self):
        self.loaded = []   # list of dicts with 'name', 'version', 'path'

    def discover_and_register(self, game):
        if not os.path.isdir(MOD_DIR):
            return
        for fname in sorted(os.listdir(MOD_DIR)):
            if not fname.endswith('.py'):
                continue
            if fname.startswith('_'):
                continue
            path = os.path.join(MOD_DIR, fname)
            self._load_one(path, game)

    def _load_one(self, path, game):
        mod_name = 'shadowfall_mod_' + os.path.basename(path)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(mod_name, path)
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod_name] = mod
            spec.loader.exec_module(mod)
            register = getattr(mod, 'register', None)
            if not callable(register):
                return
            meta = register(game) or {}
            meta = {
                'name': meta.get('name', mod_name),
                'version': meta.get('version', '0.0.0'),
                'path': path,
            }
            self.loaded.append(meta)
        except Exception:
            traceback.print_exc()

    def list_loaded(self):
        return list(self.loaded)
