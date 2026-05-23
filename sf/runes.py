"""Rune-System: Skill-Modifikatoren.

Runen werden in `player.runes[skill_key] = rune_id` gespeichert.
Die eigentliche Logik wird in skills.py per `rune == 'rune_id'` ausgewertet.
"""

import random

from .constants import RUNES


def random_choice(player, count=3):
    """Returnt eine Liste von 'count' Runen, die der Spieler noch NICHT hat.

    Jede Rune ist ein dict mit {'skill', 'id', 'name', 'desc'}.
    """
    candidates = []
    for skill_key, rune_list in RUNES.items():
        for rune in rune_list:
            if player.runes.get(skill_key) != rune['id']:
                candidates.append({
                    'skill': skill_key,
                    'id': rune['id'],
                    'name': rune['name'],
                    'desc': rune['desc'],
                })
    if not candidates:
        return []
    n = min(count, len(candidates))
    return random.sample(candidates, n)


def apply_rune(player, skill_key, rune_id):
    """Setzt eine Rune (ersetzt vorherige am gleichen Skill)."""
    player.runes[skill_key] = rune_id


def rune_label(skill_key, rune_id):
    """Returnt den Anzeigenamen einer Rune (oder None)."""
    if rune_id is None:
        return None
    for r in RUNES.get(skill_key, []):
        if r['id'] == rune_id:
            return r['name']
    return None
