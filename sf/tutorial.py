"""First-Run-Tutorial + Mechanik-Hint-System (Update #131 — Y-01/Y-02).

Y-01 (First-Run-Tutorial): Schrittweise Pop-Ups in Brassweir die die
zentralen Steuerelemente erklären (WASD, Klick, F, I, K, Q/W/E/R, F1).
Schritt-Index liegt auf `player.tutorial_step` (0..N).  Bei `tutorial_done`
True wird das System komplett ausgelassen.

Y-02 (Mechanik-Tooltips): Wenn eine Mechanik zum ersten Mal getriggert
wird, zeigt ein Toast die Lore-Erklärung.  `player.seen_mech_hints` ist
ein Set von Mechanik-Keys (`frost_stacks`, `first_crit`, `first_stun`,
`first_burn`, `low_hp`, `boss_phase`).  Pro Key max 1× pro Save.

API:
    tutorial.tick(game)                    — pro Frame in Town
    tutorial.advance(game)                 — User hat den Schritt bestätigt
    tutorial.skip(game)                    — ESC → Tutorial überspringen
    tutorial.mech_hint(game, key)          — feuert einmaligen Toast für Mechanik
    tutorial.current_step(player)          — dict | None
    tutorial.is_active(game)               — True wenn Tutorial-UI gezeigt wird

Tutorial-UI: zentriertes Lore-Banner mit Titel + Body + „[ENTER] Weiter
([ESC] Überspringen)" Hint.  Wird in `_draw_tutorial_overlay` gerendert
(eigener Pass in game.draw(), nach den Toasts).
"""

# Tutorial-Schritte — sequenziell, von Brassweir-Spawn bis zum Akt-1-Tor.
# Jeder Schritt: id (für Save), title (kurz), body (Lore-Anleitung).
TUTORIAL_STEPS = [
    {
        'id':    'welcome',
        'title': 'Willkommen in Brassweir',
        'body':  ('Du bist gestrandet in der letzten Stadt vor der '
                  'Salzküste.  Bewege dich mit  W A S D  oder Klick '
                  'auf den Boden.'),
    },
    {
        'id':    'interact',
        'title': 'Sprich mit den Bewohnern',
        'body':  ('Drücke  F  vor einem NPC um zu reden.  Korven Vor '
                  'wartet im Mahnmal-Hallen-Bezirk (Osten).'),
    },
    {
        'id':    'combat',
        'title': 'Angriff & Skills',
        'body':  ('Linksklick = Standard-Angriff.  Q / W / E / R / 1 '
                  'belegen deine Klassen-Skills.  Hover über die '
                  'Hotkey-Bar zeigt die Skill-Details.'),
    },
    {
        'id':    'flask',
        'title': 'Atemzug-Phiole',
        'body':  ('Drücke  F1  um deine Phiole zu trinken — heilt '
                  'gleichzeitig Leben und Mana.  Lädt sich beim Töten '
                  'wieder auf.'),
    },
    {
        'id':    'menus',
        'title': 'Inventar & Skills',
        'body':  ('I  öffnet das Inventar,  K  die Talente,  M  die '
                  'Karte,  N  das Codex.  Mit  G  belegst du Skill-Slots '
                  'neu.  Pause:  P.'),
    },
    {
        'id':    'portal',
        'title': 'Erster Dungeon',
        'body':  ('Folge dem Pfad nach Süden zum gelb markierten Portal '
                  '— "Akt I — Krypta der Vergessenen".  Drücke  F  am '
                  'Portal um den Dungeon zu betreten.'),
    },
]


# Mechanik-Hints: key → (title, body, color).  Werden via mech_hint()
# beim ersten Trigger einmalig getoasted.
MECH_HINTS = {
    'frost_stacks': (
        'Frost-Stacks',
        'Frost verlangsamt den Gegner.  Bei 5 Stacks wird er '
        'PINNED (festgefroren, 1.5 s bewegungsunfähig).',
        (180, 220, 255),
    ),
    'first_crit': (
        'Kritischer Treffer!',
        'Crits machen 1.5× Schaden + applizieren Ailments '
        'zuverlässiger.  Achte auf den roten Pop-Floater.',
        (255, 200, 100),
    ),
    'first_stun': (
        'Stun!',
        'Phys-Hits laden Stun-Build auf.  Bei 100 ist der Gegner '
        '1.5 s benommen — Combo-Payoff ×2.0.',
        (240, 220, 130),
    ),
    'first_burn': (
        'Brennen — Valsas Asche',
        'Burn tickt jede Sekunde Feuer-Schaden.  Stacks bis 10. '
        'Fire-Skills auf einem brennenden Gegner: +30 % Damage.',
        (255, 130, 60),
    ),
    'low_hp': (
        'Niedriges Leben',
        'Unter 30 % HP pulsiert dein HP-Globe rot.  Drücke  F1  '
        'für die Atemzug-Phiole — oder Dodge ( SPACE ) zum '
        'Ausweichen.',
        (220, 80, 80),
    ),
    'boss_phase': (
        'Boss-Phase wechselt',
        'Bei 66 % und 33 % HP wechselt der Boss in eine '
        'aggressivere Phase.  Achte auf neue Specials.',
        (255, 150, 100),
    ),
    'first_marken': (
        'Mahnmal-Marke gefunden',
        'Marken (I bis VII) sind Aspekt-Currencies.  An einer '
        'Mahnmal-Stele in Brassweir kannst du Pakt-Bonis erwerben.',
        (220, 180, 110),
    ),
    'first_elite': (
        'Elite-Gegner',
        'Elites haben Affixes (Flameweaver, Vampiric, …) und '
        'droppen mehr Loot.  Tier-Aura-Farbe zeigt die Rarity.',
        (160, 180, 255),
    ),
}


def current_step(player):
    """Returnt das aktuelle Tutorial-Step-Dict oder None wenn fertig/aus."""
    if getattr(player, 'tutorial_done', False):
        return None
    idx = int(getattr(player, 'tutorial_step', 0))
    if 0 <= idx < len(TUTORIAL_STEPS):
        return TUTORIAL_STEPS[idx]
    return None


def is_active(game):
    """True wenn das Tutorial-Overlay gerade gezeigt werden soll.

    Aktiv nur in der Stadt (nicht im Dungeon, nicht in einem Modal,
    nicht während Boss-Cinematic), und solange der Spieler noch nicht
    durchgewunken hat.
    """
    p = getattr(game, 'player', None)
    if p is None:
        return False
    if getattr(p, 'tutorial_done', False):
        return False
    if getattr(game, 'area', None) != 'town':
        return False
    # Nicht zeigen wenn ein Modal offen ist
    if getattr(game, 'modal', None):
        return False
    # Nicht während Tod/Cinematic
    if getattr(game, 'state', '') != 'playing':
        return False
    return current_step(p) is not None


def advance(game):
    """Nächster Schritt; bei letztem Schritt → tutorial_done=True."""
    p = game.player
    if getattr(p, 'tutorial_done', False):
        return
    p.tutorial_step = int(getattr(p, 'tutorial_step', 0)) + 1
    if p.tutorial_step >= len(TUTORIAL_STEPS):
        p.tutorial_done = True
        try:
            game.toast_queue.append([
                'Tutorial abgeschlossen — viel Glück, Vergessener.',
                (220, 200, 140), 3.5])
        except (AttributeError, TypeError):
            pass


def skip(game):
    """User-ESC: Tutorial überspringen + als done markieren."""
    p = game.player
    p.tutorial_done = True
    p.tutorial_step = len(TUTORIAL_STEPS)
    try:
        game.toast_queue.append([
            'Tutorial übersprungen (kann nicht erneut geöffnet werden).',
            (200, 180, 140), 3.0])
    except (AttributeError, TypeError):
        pass


def tick(game):
    """Wird pro Frame in Town aufgerufen.

    Auto-Advance einzelner Schritte wenn der Spieler die jeweilige
    Aktion bereits ausgeführt hat (z.B. mit einem NPC gesprochen).
    Verhindert dass das Tutorial den Spieler ausbremst der den Flow
    intuitiv versteht.
    """
    p = getattr(game, 'player', None)
    if p is None or getattr(p, 'tutorial_done', False):
        return
    step = current_step(p)
    if step is None:
        return
    sid = step['id']
    # Auto-Advance-Heuristiken pro Step:
    if sid == 'welcome':
        # Sobald der Spieler sich >120 px vom Spawn bewegt hat
        try:
            if (p.pos.x * p.pos.x + p.pos.y * p.pos.y) > 120 * 120:
                advance(game)
        except (AttributeError, TypeError):
            pass
    elif sid == 'interact':
        # Sobald ein NPC-Greeting gezeigt wurde, springt der Schritt
        # weiter.  Trigger erfolgt via mech_hint('first_npc_talk') aus
        # _show_npc_greeting.
        if 'first_npc_talk' in getattr(p, 'seen_mech_hints', set()):
            advance(game)
    elif sid == 'portal':
        # Wenn der Spieler in den Krypta-Tor-Bereich kommt (y >= 500),
        # markiert das den Schritt als „weiß wo es lang geht" — auto.
        try:
            if p.pos.y >= 500:
                advance(game)
        except (AttributeError, TypeError):
            pass


def mech_hint(game, key):
    """Zeigt einmal pro Save einen Mechanik-Hint-Toast.

    Returnt True wenn Toast gezeigt wurde, False wenn schon gesehen.
    """
    p = getattr(game, 'player', None)
    if p is None:
        return False
    if not hasattr(p, 'seen_mech_hints'):
        p.seen_mech_hints = set()
    if key in p.seen_mech_hints:
        return False
    p.seen_mech_hints.add(key)
    spec = MECH_HINTS.get(key)
    if spec is None:
        return False
    title, body, color = spec
    try:
        # Längerer Toast als üblich (5.5 s) — Spieler soll lesen können.
        game.toast_queue.append(
            [f'{title} — {body}', color, 5.5])
    except (AttributeError, TypeError):
        return False
    return True
