"""Velgrad-Quest-Definitionen mit narrative Stufen (Stages).

Lore-Quellen:
  - VELGRAD_LORE_BIBEL.md Teil 10 (Akt-für-Akt-Storyline)
  - VELGRAD_VOICE_LINES_POOL.md (NPC-Quotes pro Quest-Stage)
  - VELGRAD_BESTIARIUM.md (Quest-Targets)
  - VELGRAD_ITEMS_UNIQUE_BIBEL.md (Quest-Rewards)

Quest-Struktur (jede Quest = dict):
  id          unique string
  title       Anzeige-Titel
  giver       NPC-Name oder None (Auto-Quest)
  giver_kind  NPC.kind oder None (für Marker-Lookup)
  region      Akt-/Region-Hint (für Tracker-Subtitle)
  stages      Liste von Stage-Dicts mit:
    text         Anzeige-Text
    type         'talk'|'kill'|'reach'|'collect'|'interact'|'return'
    target       z.B. {'bestiary_key':'salzhueter_brut'} oder {'biome':'crypt'}
    count        Anzahl (für kill/collect), default 1
    on_complete  optional: Lore-Quote, die nach Stage als Toast erscheint
  reward      {'gold':int, 'xp':int, 'item':str (Bestiarium-Item-Name)}
  on_complete_quote  Lore-Quote des Quest-Gebers bei Komplett-Abschluss
"""


# Stage-Type-Konstanten
class StageType:
    TALK     = 'talk'      # Player muss mit NPC reden
    KILL     = 'kill'      # bestiary_key zählen
    REACH    = 'reach'     # Biome/Region/Boss-Room erreichen
    COLLECT  = 'collect'   # Items einsammeln
    INTERACT = 'interact'  # Decor interaktiv (Altar, Lore-Tafel)
    RETURN   = 'return'    # Zurück zu Quest-Giver
    # ============================================================
    # Update #116 — WELT_AUFBAU 3.1: 6 neue Stage-Types
    # ============================================================
    ESCORT      = 'escort'       # NPC begleiten bis Zielpunkt
    DEFEND      = 'defend'       # N Sekunden Position halten (NPC am Leben)
    PUZZLE      = 'puzzle'       # Sequenz von Altären/Schaltern aktivieren
    CHOICE      = 'choice'       # Spieler-Wahl mit Konsequenz-Flag
    TIMED       = 'timed'        # Stage in X Sekunden abschließen (Folge-Stage)
    CONDITIONAL = 'conditional'  # Stage übersprungen wenn flag-Bedingung


# ============================================================
# Stage-Field-Spezifikation pro Type (für quest_data-Definitionen)
# ============================================================
#  ESCORT
#    target['npc_name']       — der NPC, der zu begleiten ist
#    target['destination']    — (x, y) im aktuellen Biome; ODER
#    target['biome']          — Ziel-Biome (irgendwo dort hin)
#    Per-Frame-Tick: prüft Distanz Player↔Goal.  Optional `npc_alive_required=True`.
#
#  DEFEND
#    target['npc_name']       — der zu beschützende NPC
#    target['duration']       — Sekunden, die der NPC überleben muss
#    Per-Frame-Tick: zählt `count` (Sekunden) hoch wenn NPC alive.
#                   reset wenn NPC stirbt.
#
#  PUZZLE
#    target['sequence']       — Liste von Decor-keys/Interactable-IDs in
#                               richtiger Reihenfolge.  Falsche Reihenfolge
#                               resettet count auf 0.
#    Trigger: on_puzzle_step(game, key) prüft, ob next sequence-element.
#
#  CHOICE
#    target['flag']           — `game.flags[flag]` wird auf gewählte Option gesetzt
#    target['options']        — Liste der erlaubten Werte (z.B. ['heal','defeat'])
#    Trigger: on_choice(game, flag, value) — setzt Flag + stage.advance.
#
#  TIMED
#    target['time_limit']     — Sekunden für die Folge-Stage
#    target['fail_action']    — optional: 'revert' (zurück zur Start-Stage),
#                               'fail' (Quest abbrechen).  Default: 'revert'.
#    Per-Frame-Tick: `count` (Sekunden vergangen) hoch bis time_limit.
#                   ALLE anderen Stage-Triggers (kill/reach/talk) checken
#                   sich selbst — TIMED ist nur die Uhr drumherum.
#    Spezialfall: TIMED-Stages werden NICHT durch normalen advance erfüllt.
#                 Sie sind „inner-loop"-Stages, die in Kombination mit dem
#                 nächsten Stage-Trigger geprüft werden (z.B. „reach_in_X").
#
#  CONDITIONAL
#    target['requires_flag']  — string „flag_name=value" (z.B. „shulavh_choice=heal")
#    Wird beim Stage-Übergang ausgewertet: passt das Flag NICHT, wird die
#    Stage übersprungen (next stage_index, kein Reward).


# ============================================================
# AKT 1 — DIE SALZKÜSTE
# ============================================================

QUEST_DIE_SALZWUNDE = dict(
    id='akt1_salzwunde',
    title='Die Salzwunde',
    giver='Korven Vor',
    giver_kind='vendor',
    region='Akt 1 — Brassweir',
    is_main=True,  # Hauptquest
    stages=[
        dict(text='Sprich mit Korven Vor in Brassweir.',
             type=StageType.TALK,
             target={'npc_name': 'Korven Vor'},
             on_complete='Korven: „Drei Dörfer fehlen. Bring mir, was übrig ist."'),
        dict(text='Erreiche die Krypta der Vergessenen (Krypta-Portal).',
             type=StageType.REACH,
             target={'biome': 'crypt'},
             on_complete='Du betrittst geheiligten Boden.'),
        dict(text='Erschlage 8 Salzgekreuzte (Marrowport-Vergessene).',
             type=StageType.KILL,
             target={'bestiary_key': 'salzgekreuzter'}, count=8,
             on_complete='„Die Asche kennt meinen Namen — noch nicht."'),
        dict(text='Finde das Salzwund-Heiligtum (Boss-Raum).',
             type=StageType.REACH,
             target={'boss_room': True},
             on_complete='Die Wache wacht. Sie hat lange gewartet.'),
        dict(text='Besiege die Salzhüter-Brut.',
             type=StageType.KILL,
             target={'bestiary_key': 'salzhueter_brut'}, count=1,
             on_complete='Salzhüter: „Niemand kam mehr."'),
        dict(text='Kehre zu Korven Vor in Brassweir zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Korven Vor'},
             on_complete='Korven: „Beeindruckend. Oder lästig. Schwer zu sagen."'),
    ],
    reward=dict(gold=200, xp=180, item='Mahnmal-Marke VII',
                # Update #117 (WELT_AUFBAU 6.1): Mahnmal-Gilde-Rep für
                # Korvens Salzwunden-Auftrag. Erste Stufe (50) wird
                # damit fast erreicht — ein zweiter Korven-Auftrag
                # schaltet den Vendor-Rabatt frei.
                faction_rep={'mahnmal_gilde': 40}),
    on_complete_quote=(
        "„Drei Dörfer sind verschwunden. Jetzt erinnert sich niemand "
        "mehr an ihre Namen — außer du. Behalte das. Es ist mehr wert "
        "als alles, was ich dir bezahlen könnte."  # Korven Vor
    ),
)


QUEST_OTRETHS_STEIN = dict(
    id='akt1_otreth_stein',
    title='Otreths erster Stein',
    giver='Otreth Hohlauge',
    giver_kind='smith',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Otreth Hohlauge (Gemcutter).',
             type=StageType.TALK,
             target={'npc_name': 'Otreth Hohlauge'},
             on_complete='Otreth: „Bring mir Steine. Bring sie ungelesen."'),
        dict(text='Sammle 3 Erinnerungssteine in der Krypta.',
             type=StageType.COLLECT,
             target={'item_kind': 'gem'}, count=3,
             on_complete='Du spürst, dass die Steine atmen.'),
        dict(text='Bringe die Steine zu Otreth zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Otreth Hohlauge'},
             on_complete='Otreth hebt seine Augenklappe.'),
    ],
    reward=dict(gold=80, xp=60, item=None),
    on_complete_quote=(
        "„Ich höre. Sie wollen erinnert werden. Das ist das einzige "
        "Geheimnis dieser Steine. Nimm einen mit — er wird dich tragen, "
        "während du ihn trägst."  # Otreth Hohlauge
    ),
)


QUEST_MARAS_SPUR = dict(
    id='akt1_mara_spur',
    title='Maras Spur',
    giver='Mara die Mahnerin',
    giver_kind='mystic',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Mara der Mahnerin.',
             type=StageType.TALK,
             target={'npc_name': 'Mara die Mahnerin'},
             on_complete='Mara: „Ich habe dich noch nicht getroffen. '
                         'Aber ich erinnere mich an dich."'),
        dict(text='Finde 4 Lore-Tafeln in den Krypten der Vergessenen.',
             type=StageType.INTERACT,
             target={'decor_kind': 'lore_tablet'}, count=4,
             on_complete='Die Tafeln flüstern, was niemand sonst behält.'),
        dict(text='Sprich erneut mit Mara.',
             type=StageType.RETURN,
             target={'npc_name': 'Mara die Mahnerin'},
             on_complete='Mara hört dir zu. Sie kannte die Worte schon.'),
    ],
    reward=dict(gold=120, xp=90, item=None),
    on_complete_quote=(
        "„Es gibt Welten, in denen das Vergessen schon gewonnen hat. "
        "Schöne Welten. Ruhig. Diese hier ist nicht so eine. Noch nicht. "
        "Du machst das."  # Mara die Mahnerin
    ),
)


# ============================================================
# AKT 3 — DIE ASCHENFELDER (Vehren-Quest-Hook)
# ============================================================

QUEST_ASCH_PAKT = dict(
    id='akt3_asch_pakt',
    title='Der Asch-Pakt',
    giver='Stadtsprecher Eldon',
    giver_kind='quest',
    region='Akt 3 — Aschenfelder',
    is_main=True,
    stages=[
        dict(text='Reise zu den Aschenfeldern (Schlund von Pyron).',
             type=StageType.REACH,
             target={'biome': 'lava'},
             on_complete='Die Erde brennt unter deinen Schritten.'),
        dict(text='Stelle dich Inquisitor-General Vehren.',
             type=StageType.KILL,
             target={'bestiary_key': 'vehren'}, count=1,
             on_complete='Vehren: „Du bist Im-Nesh-berührt..."'),
        dict(text='Kehre nach Brassweir zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Stadtsprecher Eldon'},
             on_complete='Eldon nickt nur. Er hat Gerüchte gehört.'),
    ],
    reward=dict(gold=500, xp=400, item='Asche-Aspekt',
                # Update #117 (WELT_AUFBAU 6.1): Erblinde Kirche +30
                # (Spieler erfüllt Helsts Auftrag indirekt durch Vehren-
                # Sturz). Tribunal-Sturz wirkt via Konflikt-Matrix:
                # Tribunal -15, Erblinde-Allianz +0 (Erblinde ist primärer
                # Gewinner; Tribunal-Verlust ist als Bonus dabei).
                faction_rep={'erblinde_kirche': 30}),
    on_complete_quote=(
        "„Das Tribunal wird einen neuen General ernennen. Er wird härter "
        "sein. Sie sind immer härter. Bleib in Bewegung, Verbannter."
    ),
)


# ============================================================
# AKT 1 — Nebenquests (Update #116, WELT_AUFBAU 3.2)
# Demonstration der 6 neuen Stage-Types über Lore-konforme Quests.
# ============================================================

# Tameris' Schwester — ESCORT + CHOICE + CONDITIONAL.
# Lore: Tameris ist Speerschwester, ihre Schwester ist auf dem Weg nach
# Zhar-Eth-Karawane (Akt 1b).  Spieler eskortiert eine Schwester-Wache
# (Stadttor-NPC) zu Tameris im Wirtshaus.  Choice: Schwester behalten
# (heimkehren lassen) oder zurück nach Zhar-Eth.
QUEST_TAMERIS_SCHWESTER = dict(
    id='akt1_tameris_schwester',
    title='Tameris\' Schwester',
    giver='Tameris',
    giver_kind='innkeeper',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Tameris im Wirtshaus.',
             type=StageType.TALK,
             target={'npc_name': 'Tameris'},
             on_complete='Tameris: „Meine Schwester ist auf dem Weg. '
                         'Bring sie sicher zu mir."'),
        # ESCORT: NPC „Schwester-Wache" muss zu Tameris-Position
        dict(text='Eskortiere die Schwester-Wache zu Tameris.',
             type=StageType.ESCORT,
             target={'npc_name': 'Schwester-Wache',
                     'destination': (-360, 250)},   # Tameris-Pos
             on_complete='Schwester: „Tameris. Dein Faden zittert noch."'),
        # CHOICE: Bei Tameris bleiben (heal) oder Zhar-Eth (defeat-Equivalent)
        dict(text='Wähle: Schwester bleibt bei Tameris ODER reist nach '
                  'Zhar-Eth zurück.',
             type=StageType.CHOICE,
             target={'flag': 'tameris_schwester_choice',
                     'options': ['bleibt', 'reist']},
             on_complete='Die Wahl wiegt schwerer als du dachtest.'),
        # CONDITIONAL: nur wenn Spieler „reist" gewählt hat
        dict(text='(Wenn die Schwester reist:) Sprich mit Naveth '
                  'in Zhar-Eth.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'tameris_schwester_choice=reist',
                     'npc_name': 'Schwester-Kommandantin Naveth'},
             on_complete='Naveth nickt knapp. Der Mond bindet.'),
        # Return zu Tameris
        dict(text='Kehre zu Tameris zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Tameris'},
             on_complete='Tameris hebt das Glas. Schweigend.'),
    ],
    reward=dict(gold=150, xp=120, item=None,
                # Update #117 (WELT_AUFBAU 6.1): Speerschwestern-Rep für
                # Schwester-Eskorte. Tameris ist ehemalige Speerschwester
                # → Auftrag stärkt Spieler-Verbindung zur Schwesternschaft.
                faction_rep={'speerschwestern': 25}),
    on_complete_quote=(
        "„Sie ist sicher. Oder sie ist weg. Beides nährt mich gleich."
        # Tameris
    ),
)

# Vossharil-Ritual — DEFEND.
# Lore: Vossharil führt ein Knochenwitwen-Ritual (Akt 4), Spieler muss
# sie 30 s vor Mob-Wellen schützen.  Hook für späteren Quest-Trigger
# im swamp_ruins-Dungeon.
QUEST_VOSSHARIL_RITUAL = dict(
    id='akt4_vossharil_ritual',
    title='Vossharils Faden-Bindung',
    giver='Vossharil die Dreimalige',
    giver_kind='quest',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    stages=[
        dict(text='Sprich mit Vossharil im Knoten-Markt.',
             type=StageType.TALK,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil: „Bleib bei mir. Lass den Faden nicht reißen."'),
        # DEFEND: 30 s in Vossharils Nähe
        dict(text='Verteidige Vossharil 30 Sekunden lang.',
             type=StageType.DEFEND,
             target={'npc_name': 'Vossharil die Dreimalige',
                     'duration': 30.0},
             on_complete='Der Faden hält. Shulavh nickt — irgendwo.'),
        dict(text='Sprich erneut mit Vossharil.',
             type=StageType.RETURN,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil schaut dich an. Lange.'),
    ],
    reward=dict(gold=200, xp=180, item=None,
                # Update #117 (WELT_AUFBAU 6.1): Knochenwitwen-Rep.
                # Vossharils Faden-Bindung erlebt → die Schwesternschaft
                # akzeptiert dich als Verwandten.
                faction_rep={'knochenwitwen': 35}),
    on_complete_quote=(
        "„Du hieltest. Beim ersten Mal hielt mich auch jemand. "
        "Beim zweiten nicht. Vielleicht hältst du beim dritten."
        # Vossharil
    ),
)

# Velharn-Drei-Zeiten — PUZZLE.
# Lore: Erster Senator Voraius gibt Spieler 3 Altäre (Glasgolden /
# Götterkrieg / Gegenwart) — muss in dieser Reihenfolge aktiviert
# werden (= chronologisch).
QUEST_VELHARN_DREI_ZEITEN = dict(
    id='akt5_drei_zeiten',
    title='Die Drei Zeiten von Velharn',
    giver='Erster Senator Voraius',
    giver_kind='quest',
    region='Akt 5 — Spiegelstadt',
    is_main=True,
    stages=[
        dict(text='Sprich mit Erstem Senator Voraius.',
             type=StageType.TALK,
             target={'npc_name': 'Erster Senator Voraius'},
             on_complete='Voraius: „Drei Zeiten. Erinnere sie in der '
                         'Reihenfolge, in der sie geschahen."'),
        # PUZZLE: Glasgolden → Götterkrieg → Gegenwart
        dict(text='Aktiviere die Drei-Zeiten-Altäre in chronologischer '
                  'Reihenfolge.',
             type=StageType.PUZZLE,
             target={'sequence': ['glasgolden', 'goetterkrieg',
                                   'gegenwart']},
             on_complete='Die drei Zeiten falten sich. Velharn atmet aus.'),
        dict(text='Sprich erneut mit Voraius.',
             type=StageType.RETURN,
             target={'npc_name': 'Erster Senator Voraius'},
             on_complete='Voraius weint. Nicht aus Trauer.'),
    ],
    reward=dict(gold=350, xp=300, item=None),
    on_complete_quote=(
        "„Du hast uns in eine Reihenfolge gestellt. Wir hatten das "
        "schon vergessen. Es war wichtig."
        # Voraius
    ),
)

# Vergessens-Welle — TIMED.
# Lore: Mara die Mahnerin warnt vor Vergessens-Welle; Spieler muss
# Mahnmal-Stein vor Ablauf der Zeit erreichen.  Demo der Time-Critical-
# Mechanik.
QUEST_VERGESSENS_WELLE = dict(
    id='akt1_vergessens_welle',
    title='Welle des Vergessens',
    giver='Mara die Mahnerin',
    giver_kind='mystic',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Mara der Mahnerin.',
             type=StageType.TALK,
             target={'npc_name': 'Mara die Mahnerin'},
             on_complete='Mara: „Die Welle kommt. Erreiche den nördlichen '
                         'Mahnmal-Stein in 30 Sekunden."'),
        # TIMED: 30 s Zeitlimit für die Folge-Stage
        dict(text='(Zeitlimit aktiv — beeil dich!)',
             type=StageType.TIMED,
             target={'time_limit': 30.0, 'fail_action': 'revert'},
             on_complete='Die Welle hält den Atem an.'),
        # Folge-Stage: Mahnmal-Stein erreichen
        dict(text='Erreiche den Mahnmal-Stein im Norden.',
             type=StageType.INTERACT,
             target={'decor_kind': 'mahnmal_stele'}, count=1,
             on_complete='Du fasst den Stein. Die Welle teilt sich.'),
        dict(text='Kehre zu Mara zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Mara die Mahnerin'},
             on_complete='Mara nickt. „Schneller diesmal."'),
    ],
    reward=dict(gold=100, xp=80, item=None),
    on_complete_quote=(
        "„Es gab eine Welt, in der du den Stein nicht erreicht hast. "
        "Wir leben gerade nicht in dieser."
        # Mara die Mahnerin
    ),
)


# ============================================================
# REGISTRY
# ============================================================
ALL_QUESTS = [
    QUEST_DIE_SALZWUNDE,
    QUEST_OTRETHS_STEIN,
    QUEST_MARAS_SPUR,
    QUEST_ASCH_PAKT,
    # Update #116 — neue Stage-Type-Demonstration:
    QUEST_TAMERIS_SCHWESTER,
    QUEST_VOSSHARIL_RITUAL,
    QUEST_VELHARN_DREI_ZEITEN,
    QUEST_VERGESSENS_WELLE,
]


def quest_by_id(qid):
    for q in ALL_QUESTS:
        if q['id'] == qid:
            return q
    return None


def quests_offered_by_npc(npc_name):
    """Returnt alle Quests, deren Giver dieser NPC ist."""
    return [q for q in ALL_QUESTS if q['giver'] == npc_name]


def initial_quests_for_new_game():
    """Quests, die beim Game-Start verfügbar sein sollen (nicht ausgelöst).

    Die Akt-1-Hauptquest „Die Salzwunde" startet automatisch.
    """
    return ['akt1_salzwunde', 'akt1_otreth_stein', 'akt1_mara_spur']


# ============================================================
# LORE-TAFEL-POOL (Velgrad-Kanon, ersetzt die generischen Texte)
# ============================================================
# Pro Region. Wird von dungeon.py beim Tafel-Platzieren konsumiert.
LORE_TABLETS = {
    'crypt': [
        "Marrowport ist seit drei Wochen vergessen. Das Wasser kennt "
        "seinen Namen noch.",
        "Die Salzwunde lockt die Ertrunkenen aus achthundert Jahren "
        "Seehandel zurück. Manche sterben endlich.",
        "Sie war die Letzte Königin Velharns. Ertränkt im Krieg. "
        "Sie wacht.",
        "Wer dreimal stirbt, kommt dreimal zurück. Vossharil sagt, "
        "danach zählt niemand mehr.",
        "Die Mahnmal-Gilde verkauft Erinnerungen. Was sie nicht verkauft, "
        "vergessen sie zuerst.",
    ],
    'frost': [
        "Velharn steht noch. Velharn ist gefallen. Beides ist wahr — "
        "in den Stunden-Spiegeln gilt nichts nur einmal.",
        "Die Senatoren reden seit achthundert Jahren über dasselbe "
        "Gesetz. Es war nie fertig.",
        "Goldstaub fällt nicht. Er erinnert sich nur, dass er fiel.",
        "Nheyra wandelt hier. Manche sehen sie. Sie sehen sich nicht "
        "zweimal in derselben Stunde.",
    ],
    'lava': [
        "Valsa fiel hier. Ihre Asche brennt ohne Brennstoff. Wer atmet, "
        "atmet einen Funken ihres Schmerzes.",
        "Die Letzte Legion marschiert noch. Niemand hat den Befehl "
        "zur Auflösung gegeben.",
        "Das Tribunal reinigt durch Feuer. Was vergessen werden soll, "
        "brennen sie zweimal.",
        "Im-Nesh war hier vor dem Krieg. Er übersetzte den Pakt — "
        "und übersetzte ihn falsch.",
    ],
    'swamp': [
        "Shulavh sammelt Fäden, die brechen. Sie weint nicht, aber "
        "ihr Faden tropft.",
        "Wer in das Wurzelgrab geht, kommt verändert wieder. Oder gar "
        "nicht.",
        "Die Knochenwitwen sprechen mit den Toten. Die Toten antworten. "
        "Das ist das Problem.",
    ],
    'astral': [
        "Eine Stunde im Spiegel sind drei draußen. Manche wählen den "
        "Spiegel — sie altern langsamer, aber sie sind nicht mehr da.",
        "Velharn ist die einzige Stadt, die nicht weiß, dass sie "
        "gefallen ist.",
        "Der Senat tagt. Der Senat hat seit achthundert Jahren "
        "abgestimmt. Beides stimmt.",
    ],
    'desert': [
        "Zhar-Eth wandert. Sie weiß nicht, wovor sie flieht — aber "
        "sie bleibt nirgends lange.",
        "Die Speerschwestern teilen einen Faden. Wenn er reißt, fühlen "
        "alle es. Tameris fühlt es seit Akt 1.",
        "Der Mond bindet die Schwesternschaft. Wer dem Mond untreu wird, "
        "läuft allein.",
    ],
    'town': [
        "Brassweir war einst Hafen für sieben Handelsrouten. Heute "
        "noch für eine. Aber die kommt zurück.",
        "Korven Vor hat einen Stein im Schreibtisch, den er nie verkauft. "
        "Frag ihn nicht warum.",
        "Mara die Mahnerin spricht in Zukunftsform über Vergangenes. "
        "Sie hat recht, beides.",
    ],
}


def lore_tablet_for_region(biome, idx):
    pool = LORE_TABLETS.get(biome) or LORE_TABLETS['crypt']
    return pool[idx % len(pool)]
