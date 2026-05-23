"""PLAN S-08 (Update #96): Localization-Foundation.

Minimaler Translation-Service. Default-Locale ist `de_DE` (alle bisherigen
Strings sind deutsch). `en_US`-Fallback dict für Schlüssel-Keys, damit
zukünftige UI-Strings via `t(key)` aufgelöst werden können.

API:
    from sf.locale import t, set_locale, current_locale
    t('inv.equipment')          # → "Die Ausrüstung"
    set_locale('en_US')
    t('inv.equipment')          # → "Equipment"

Bestehender Code bleibt unangetastet — neue Strings können schrittweise
auf `t()` migriert werden. Saubere Migrations-Pfad-Foundation.
"""

_locale = 'de_DE'

_TRANSLATIONS = {
    'de_DE': {
        'inv.equipment':         'Die Ausrüstung',
        'inv.inventory':         'Inventar',
        'inv.stats.offensive':   'Offensiv',
        'inv.stats.defensive':   'Defensiv',
        'inv.stats.utility':     'Utility',
        'tree.title':            'Der Erinnerungs-Baum',
        'tree.universal':        'Universal',
        'tree.class':            'Klasse',
        'shop.title':            'Markt',
        'stash.title':           'Mahnmal-Verwahrer',
        'craft.upgrade':         'Aufwerten',
        'craft.reroll':          'Umrollen',
        'craft.enchant':         'Verzaubern',
        'craft.salvage':         'Salvage',
        'flask.vital':           'Atemzug-Phiole',
        'pause.title':           'Pause',
        'pause.resume':          'Weiterspielen',
        'pause.settings':        'Einstellungen',
        'pause.quit':            'Spiel beenden',
        'death.title':           'Du Stirbst',
        'death.respawn':         'Erneut atmen',
        'codex.achievements':    'Achievements',
        'codex.lore':            'Lore-Tafeln',
        'codex.bestiary':        'Bestiarium',
        'shrine.title':          'Mahnmal-Schrein',
        'currency.gold':         'Gold',
        'currency.marken':       'Mahnmal-Marken',
        'currency.orbs':         'Orbs of Regret',
        'hud.fps':               'FPS',
    },
    'en_US': {
        'inv.equipment':         'Equipment',
        'inv.inventory':         'Inventory',
        'inv.stats.offensive':   'Offensive',
        'inv.stats.defensive':   'Defensive',
        'inv.stats.utility':     'Utility',
        'tree.title':            'The Memory Tree',
        'tree.universal':        'Universal',
        'tree.class':            'Class',
        'shop.title':            'Market',
        'stash.title':           'Memorial Keeper',
        'craft.upgrade':         'Upgrade',
        'craft.reroll':          'Reroll',
        'craft.enchant':         'Enchant',
        'craft.salvage':         'Salvage',
        'flask.vital':           'Breath Phial',
        'pause.title':           'Paused',
        'pause.resume':          'Resume',
        'pause.settings':        'Settings',
        'pause.quit':            'Quit Game',
        'death.title':           'You Die',
        'death.respawn':         'Breathe Again',
        'codex.achievements':    'Achievements',
        'codex.lore':            'Lore Tablets',
        'codex.bestiary':        'Bestiary',
        'shrine.title':          'Memorial Shrine',
        'currency.gold':         'Gold',
        'currency.marken':       'Memorial Marks',
        'currency.orbs':         'Orbs of Regret',
        'hud.fps':               'FPS',
    },
}

AVAILABLE_LOCALES = ('de_DE', 'en_US')


def current_locale():
    """Returnt das aktuelle Locale-Tag."""
    return _locale


def set_locale(loc):
    """Wechselt das aktive Locale. Unbekannte Tags werden ignoriert."""
    global _locale
    if loc in _TRANSLATIONS:
        _locale = loc
        return True
    return False


def t(key, default=None):
    """Übersetzt einen Key in das aktuelle Locale.
    Fallback: 'en_US' → 'de_DE' → default → key selbst."""
    cur = _TRANSLATIONS.get(_locale, {})
    if key in cur:
        return cur[key]
    en = _TRANSLATIONS.get('en_US', {})
    if key in en:
        return en[key]
    de = _TRANSLATIONS.get('de_DE', {})
    if key in de:
        return de[key]
    return default if default is not None else key
