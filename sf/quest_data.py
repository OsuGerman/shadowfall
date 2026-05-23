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
# AKT 2 — GLASGOLDENE RUINEN (Update #152, WELT_AUFBAU 3.4)
# ============================================================
# Main-Quest „Asch-Prophezeiung" — Bruder Helst gibt sie im Echo-Markt-
# Outpost.  Player wird zu den Glasgoldenen Ruinen (frost-Biome /
# glass_palace) geschickt um den Senator-Geist-Boss zu bezwingen.
# Lore: Helst sah Velharn fallen vor 100 Jahren, band sich danach die
# Augen ab.  Er weiß, dass die Senatoren noch in den Ruinen reden — und
# einer von ihnen, der Senator-Geist, hält den Pakt-Stein versteckt.
# Voice-Lines aus VELGRAD_VOICE_LINES_POOL.md (Helst-Pool).

QUEST_ASCH_PROPHEZEIUNG = dict(
    id='akt2_asch_prophezeiung',
    title='Die Asch-Prophezeiung',
    giver='Bruder Helst der Hundertjährige',
    giver_kind='quest',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=True,
    stages=[
        dict(text='Sprich mit Bruder Helst im Echo-Markt.',
             type=StageType.TALK,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst: „Geh in die Ruinen. Hör auf das, was '
                         'noch redet. Bring mir den Pakt-Stein zurück."'),
        dict(text='Erreiche die Glasgoldenen Ruinen (Echo-Palast).',
             type=StageType.REACH,
             target={'biome': 'frost'},
             on_complete='Goldstaub legt sich auf deine Sohlen. Niemand '
                         'wischt ihn fort.'),
        dict(text='Sammle 5 Goldstaub-Erinnerungen.',
             type=StageType.KILL,
             target={'bestiary_key': 'goldstaub_diener'}, count=5,
             on_complete='Die Erinnerungen flüstern Namen, die niemand '
                         'mehr ausspricht.'),
        dict(text='Stelle den Senator-Geist im Pakt-Saal.',
             type=StageType.KILL,
             target={'bestiary_key': 'senator_geist'}, count=1,
             on_complete='Senator-Geist: „Ich war hier vor dir. Ich '
                         'werde hier nach dir sein."'),
        dict(text='Kehre zu Bruder Helst zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst nimmt den Pakt-Stein und nickt. '
                         'Seine Augenbinde ist nass.'),
    ],
    reward=dict(gold=400, xp=300, item='Helst-Pakt-Stein',
                # WELT_AUFBAU 6.1: Erblinde Kirche +35 (Hauptauftrag
                # erfüllt) — Tribunal-Konflikt via Konflikt-Matrix
                # -10.  Mahnmal-Gilde +15 (Brassweir's Helst-Verbindung).
                faction_rep={'erblinde_kirche': 35,
                              'mahnmal_gilde': 15}),
    on_complete_quote=(
        "„Du hast einen Toten gehört. Das ist mehr, als die meisten "
        "können. Behalte das. Es wird gegen dich gehalten werden, "
        "aber es ist trotzdem wahr."  # Bruder Helst
    ),
)


# ============================================================
# AKT 4 — WURZELGRAB (Update #152, WELT_AUFBAU 3.6)
# ============================================================
# Main-Quest „Shulavhs Faden" — Vossharil die Dreimalige gibt sie im
# Knoten-Markt-Outpost.  Player wird zum Wurzelgrab (swamp_ruins)
# geschickt um Shulavh, die Faden-Mutter zu konfrontieren.
# Lore: Shulavh ist Vossharils Patin und Knochenwitwen-Aspekt.  Sie
# wickelt Fäden um die Lebenden um sie zu binden.  CHOICE-Stage: heilen
# (sanfter Schluss) oder bezwingen (kämpferisches Ende).  Flag wird
# später für Akt 6 ausgelesen (welche Wahl beeinflusst Akt-6-Pfad).
# Voice-Lines aus VELGRAD_VOICE_LINES_POOL.md (Vossharil/Shulavh-Pool).

QUEST_SHULAVH_FADEN = dict(
    id='akt4_shulavh_faden',
    title='Shulavhs Faden',
    giver='Vossharil die Dreimalige',
    giver_kind='quest',
    region='Akt 4 — Wurzelgrab',
    is_main=True,
    stages=[
        dict(text='Sprich mit Vossharil im Knoten-Markt.',
             type=StageType.TALK,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil: „Shulavh wickelt noch. Geh zu ihr. '
                         'Du wirst wissen, was zu tun ist — oder du '
                         'wirst sterben. Beides ist Antwort genug."'),
        dict(text='Erreiche das Wurzelgrab.',
             type=StageType.REACH,
             target={'biome': 'swamp'},
             on_complete='Der Boden atmet hier. Es atmet zurück, '
                         'wenn du atmest.'),
        dict(text='Erschlage 4 Faden-Gebundene.',
             type=StageType.KILL,
             target={'bestiary_key': 'faden_gebundener'}, count=4,
             on_complete='Die Fäden lösen sich, wenn der Träger fällt. '
                         'Manche fliegen heim.'),
        dict(text='Konfrontiere Shulavh die Faden-Mutter.',
             type=StageType.KILL,
             target={'bestiary_key': 'shulavh'}, count=1,
             on_complete='Shulavh: „Du hast meinen Faden zerschnitten. '
                         'Ich wickle ihn neu — aber nicht mehr um dich."'),
        # CHOICE: Heilen (Faden behalten) ODER Bezwingen (zerstören).
        # Flag steuert spätere Akt-6-Stages (siehe Akt 6 wenn implementiert).
        dict(text='Wähle: Shulavhs Faden heilen ODER endgültig bezwingen.',
             type=StageType.CHOICE,
             target={'flag': 'shulavh_choice',
                      'options': ['heilen', 'bezwingen']},
             on_complete='Die Wahl wiegt mehr als der Kampf.'),
        # CONDITIONAL: Heilen-Pfad — Vossharils Zusatz-Dialog
        dict(text='(Wenn geheilt:) Bringe einen Faden-Splitter zurück.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'shulavh_choice=heilen',
                      'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil hält den Splitter still. '
                         'Sehr still.'),
        dict(text='Kehre zu Vossharil zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete=('Vossharil: „Du hast gewählt. Ich auch. '
                          'Manchmal wählt man, indem man nicht kämpft."')),
    ],
    reward=dict(gold=600, xp=500, item='Vossharils Bruder',
                # WELT_AUFBAU 6.1: Knochenwitwen +40 (Hauptauftrag).
                # Saatträger-Konflikt via Matrix -5 (Knochenwitwen
                # halten den Tod fest, Saatträger pflanzen neu).
                faction_rep={'knochenwitwen': 40}),
    on_complete_quote=(
        "„Du bist nicht meine Schwester. Du bist nicht meine Mutter. "
        "Du bist meine Patin? Vielleicht. Ich brauche eine neue."
        # Vossharil
    ),
)


# ============================================================
# AKT 3 — Nebenquests (Update #157, WELT_AUFBAU 3.5)
# ============================================================
# 6 Sidequests in Säulen-von-Helst (Aschenfelder).  Givers:
#   Acolyt der Erblinden Kirche, Tribunal-Doppelagent Korren,
#   Vehren-Gefangener Selvor, Asche-Händler Brulm.
# Lore-Quellen: VELGRAD_LORE_BIBEL Teil 9 (Aschenfelder + Vehren),
# VELGRAD_VOICE_LINES_POOL.md (Acolyt/Korren/Brulm-Pool).

QUEST_ERBLINDER_PRIESTER_TRIAL = dict(
    id='akt3_erblinder_priester_trial',
    title='Trial der Augen-Bindung',
    giver='Acolyt der Erblinden Kirche',
    giver_kind='quest',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit dem Acolyt der Erblinden Kirche.',
             type=StageType.TALK,
             target={'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Acolyt: „Bind deine Augen ab. Dann siehst '
                         'du, was Velharn wirklich gefallen ist."'),
        dict(text='Wähle: Augen binden (Erblinde-Trial) ODER '
                  'widerstehen.',
             type=StageType.CHOICE,
             target={'flag': 'erblinde_trial',
                      'options': ['binden', 'widerstehen']},
             on_complete='Die Wahl macht Velharn lauter — oder '
                         'leiser.'),
        dict(text='(Wenn gebunden:) Kehre zum Acolyt zurück — geweiht.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'erblinde_trial=binden',
                      'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Acolyt segnet dich. Du siehst nichts mehr — '
                         'und doch alles.'),
        dict(text='(Wenn widerstanden:) Kehre zum Acolyt zurück.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'erblinde_trial=widerstehen',
                      'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Acolyt: „Du behältst deine Augen. Auch eine '
                         'Antwort."'),
        dict(text='Schließe den Trial ab.',
             type=StageType.RETURN,
             target={'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Velharn dreht sich um. Es hat dich gehört.'),
    ],
    reward=dict(gold=280, xp=220, item=None,
                # Erblinde-Trial: Binden +35, widerstehen +5 (passiv).
                # Wir pflanzen +30 als Default-Reward; das Choice-Flag
                # ist primär narrativ + späterer Akt-6/7-Hook.
                faction_rep={'erblinde_kirche': 30}),
    on_complete_quote=(
        "„Du hast Velharn gehört. Jetzt trägst du das mit dir. "
        "Wir nennen das eine Last. Manche nennen es ein Geschenk."
        # Acolyt der Erblinden Kirche
    ),
)


QUEST_LETZTE_LEGION = dict(
    id='akt3_letzte_legion',
    title='Die letzte Legion',
    giver='Vehren-Gefangener Selvor',
    giver_kind='quest',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit Selvor, dem Vehren-Gefangenen.',
             type=StageType.TALK,
             target={'npc_name': 'Vehren-Gefangener Selvor'},
             on_complete='Selvor: „Asch-Soldaten irren noch herum. '
                         'Schick sie zur Ruhe — bitte."'),
        dict(text='Erschlage 8 Asch-Soldaten in den Aschenfeldern.',
             type=StageType.KILL,
             target={'bestiary_key': 'asch_soldat'}, count=8,
             on_complete='Die Soldaten fallen wie eine letzte '
                         'Atemzug-Reihe.'),
        dict(text='Kehre zu Selvor zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Vehren-Gefangener Selvor'},
             on_complete='Selvor weint. Endlich.'),
    ],
    reward=dict(gold=200, xp=150, item=None,
                faction_rep={'mahnmal_gilde': 15}),
    on_complete_quote=(
        "„Sie waren meine Brüder. Du hast sie heimgebracht — "
        "nicht zu mir, aber nach Hause."  # Selvor
    ),
)


QUEST_TRIBUNAL_INFILTRATION = dict(
    id='akt3_tribunal_infiltration',
    title='Tribunal-Infiltration',
    giver='Tribunal-Doppelagent Korren',
    giver_kind='mystic',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit Korren, dem Tribunal-Doppelagent.',
             type=StageType.TALK,
             target={'npc_name': 'Tribunal-Doppelagent Korren'},
             on_complete='Korren (leise): „Das Tribunal jagt dich. '
                         'Lass uns die Jagd umdrehen — sechs Konstrukte '
                         'sollen verschwinden."'),
        dict(text='Erschlage 6 Tribunal-Konstrukte in den Asche-'
                  'Feldern.',
             type=StageType.KILL,
             target={'bestiary_key': 'tribunal_konstrukt'}, count=6,
             on_complete='Die Konstrukte zerfallen zu Asche. '
                         'Tribunal-Sigille verglühen.'),
        dict(text='Kehre zu Korren zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Tribunal-Doppelagent Korren'},
             on_complete='Korren nickt knapp. Sein Doppelspiel '
                         'hält noch einen Akt länger.'),
    ],
    reward=dict(gold=350, xp=280, item=None,
                faction_rep={'tribunal_asche': -20,
                              'mahnmal_gilde': 25,
                              'erblinde_kirche': 10}),
    on_complete_quote=(
        "„Eines Tages wird das Tribunal merken, wer ich wirklich war. "
        "Hoffentlich nicht heute."  # Korren
    ),
)


QUEST_BOUNTY_ASCH_WOLF = dict(
    id='akt3_bounty_asch_wolf',
    title='Bounty: Asch-Wölfe',
    giver='Asche-Händler Brulm',
    giver_kind='vendor',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit Brulm am Asche-Stand.',
             type=StageType.TALK,
             target={'npc_name': 'Asche-Händler Brulm'},
             on_complete='Brulm: „Die Wölfe stehlen mir die Kunden. '
                         '10 Stück, 8 Gold pro Schwanz."'),
        dict(text='Erschlage 10 Asch-Wölfe.',
             type=StageType.KILL,
             target={'bestiary_key': 'asch_wolf'}, count=10,
             on_complete='Die Wölfe heulen ein letztes Mal. Der '
                         'Markt atmet auf.'),
        dict(text='Kehre zu Brulm zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Asche-Händler Brulm'},
             on_complete='Brulm zählt aus. Es stimmt — fast.'),
    ],
    reward=dict(gold=100, xp=70, item=None,
                faction_rep={'mahnmal_gilde': 5}),
    on_complete_quote=(
        "„Bring mir noch zehn. Asche kostet — selbst die der Wölfe."
        # Brulm
    ),
)


QUEST_VALSA_TRAENE = dict(
    id='akt3_valsa_traene',
    title='Valsas Träne',
    giver='Acolyt der Erblinden Kirche',
    giver_kind='quest',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit dem Acolyt über Valsas Träne.',
             type=StageType.TALK,
             target={'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Acolyt: „Drei Asche-Stelen erinnern an '
                         'Valsas Träne. Lies sie. Trag sie."'),
        dict(text='Interagiere mit 3 Asche-Lore-Tafeln.',
             type=StageType.INTERACT,
             target={'decor_kind': 'lore_tablet'}, count=3,
             on_complete='Die Tafeln glühen kurz. Du hörst, wie '
                         'Valsa atmet — leise, lange.'),
        dict(text='Kehre zum Acolyt zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Acolyt der Erblinden Kirche'},
             on_complete='Acolyt segnet dich. „Valsa kennt dich '
                         'jetzt."'),
    ],
    reward=dict(gold=150, xp=100, item=None,
                lore_codex='Valsas Träne — Eine Träne, die nicht '
                           'fiel. Sie wartet darauf, dass jemand '
                           'um sie weint.',
                faction_rep={'erblinde_kirche': 12}),
    on_complete_quote=(
        "„Asche und Tränen — fast dasselbe. Manchmal ist es."
        # Acolyt
    ),
)


QUEST_INQUISITIONS_KLINGE = dict(
    id='akt3_inquisitions_klinge',
    title='Die Inquisitions-Klinge',
    giver='Asche-Händler Brulm',
    giver_kind='vendor',
    region='Akt 3 — Aschenfelder',
    is_main=False,
    stages=[
        dict(text='Sprich mit Brulm über Tribunal-Stahl.',
             type=StageType.TALK,
             target={'npc_name': 'Asche-Händler Brulm'},
             on_complete='Brulm: „Tribunal-Stahl. Sechs Splitter. '
                         'Bring sie mir — ich schmelze, du kassierst."'),
        dict(text='Sammle 5 Erinnerungssteine (Gem-Drops).',
             type=StageType.COLLECT,
             target={'item_kind': 'gem'}, count=5,
             on_complete='Die Splitter klirren miteinander — sie '
                         'erinnern sich nicht.'),
        dict(text='Kehre zu Brulm zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Asche-Händler Brulm'},
             on_complete='Brulm schmilzt sie nicht — er verkauft '
                         'sie weiter. Du fragst nicht.'),
    ],
    reward=dict(gold=200, xp=150, item=None,
                faction_rep={'mahnmal_gilde': 10}),
    on_complete_quote=(
        "„Brulm ist ehrlich, wenn er ehrlich sein muss. Sonst ist er "
        "nützlich."  # Brulm über sich selbst
    ),
)


# ============================================================
# AKT 4 — Nebenquests (Update #157, WELT_AUFBAU 3.6)
# ============================================================
# 6 Sidequests im Knoten-Markt (Wurzelgrab).  Givers:
#   Vossharil, Bran (Apotheker), Marvel (Knochen-Hexe), Hohler Sohn.

QUEST_KNOCHENWITWEN_AUFNAHME = dict(
    id='akt4_knochenwitwen_aufnahme',
    title='Knochenwitwen-Aufnahme',
    giver='Vossharil die Dreimalige',
    giver_kind='quest',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    requires_quests=['akt4_shulavh_faden'],
    stages=[
        dict(text='Sprich mit Vossharil über die Witwen-Aufnahme.',
             type=StageType.TALK,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil: „Zur Witwe werden — fünf Faden-'
                         'Gebundene befreien. Dann reden wir weiter."'),
        dict(text='Erschlage 5 Faden-Gebundene.',
             type=StageType.KILL,
             target={'bestiary_key': 'faden_gebundener'}, count=5,
             on_complete='Die Fäden lösen sich. Manche fliegen heim. '
                         'Andere bleiben um deinen Atem.'),
        dict(text='Wähle: Witwen-Eid leisten ODER neutral bleiben.',
             type=StageType.CHOICE,
             target={'flag': 'witwen_eid',
                      'options': ['leisten', 'neutral']},
             on_complete='Die Wahl bindet — oder lässt frei. Beides '
                         'wirkt.'),
        dict(text='Kehre zu Vossharil zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil neigt den Kopf. Du gehörst nun '
                         'irgendwo — egal wohin.'),
    ],
    reward=dict(gold=280, xp=220, item=None,
                faction_rep={'knochenwitwen': 35}),
    on_complete_quote=(
        "„Du bist nicht Witwe geworden. Du bist Faden geworden. "
        "Das ist mehr — oder weniger. Vielleicht beides."
        # Vossharil
    ),
)


QUEST_HOHLE_SOHN = dict(
    id='akt4_hohle_sohn',
    title='Folge dem Hohlen Sohn',
    giver='Hohler Sohn',
    giver_kind='mystic',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    stages=[
        dict(text='Sprich mit dem Hohlen Sohn.',
             type=StageType.TALK,
             target={'npc_name': 'Hohler Sohn'},
             on_complete='Der Hohle Sohn schweigt. Du verstehst '
                         'trotzdem.'),
        dict(text='Lies 3 Wurzel-Lore-Tafeln.',
             type=StageType.INTERACT,
             target={'decor_kind': 'lore_tablet'}, count=3,
             on_complete='Die Tafeln flüstern Namen — alle deine.'),
        dict(text='Kehre zum Hohlen Sohn zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Hohler Sohn'},
             on_complete='Der Sohn nickt. Endlich verstanden — '
                         'oder nie.'),
    ],
    reward=dict(gold=250, xp=200, item=None,
                lore_codex='Der Hohle Sohn — Er hat einen Namen. '
                           'Niemand sagt ihn. Auch er nicht.',
                faction_rep={'knochenwitwen': 15}),
    on_complete_quote=(
        "( — der Sohn nickt. Mehr braucht es nicht. — )"
    ),
)


QUEST_DREI_TODE = dict(
    id='akt4_drei_tode',
    title='Vossharils Drei Tode',
    giver='Vossharil die Dreimalige',
    giver_kind='quest',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    stages=[
        dict(text='Frage Vossharil nach ihren drei Toden.',
             type=StageType.TALK,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil: „Drei Tode. Drei Tafeln. Finde '
                         'sie. Sie werden dir mehr sagen als ich."'),
        dict(text='Finde 3 Wurzel-Lore-Tafeln über Vossharils Geschichte.',
             type=StageType.INTERACT,
             target={'decor_kind': 'lore_tablet'}, count=3,
             on_complete='Die Tafeln erzählen drei Tode — keiner '
                         'davon endgültig.'),
        dict(text='Kehre zu Vossharil zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Vossharil die Dreimalige'},
             on_complete='Vossharil schaut dich an. Lange. Sie '
                         'erinnert sich jetzt mit dir.'),
    ],
    reward=dict(gold=150, xp=100, item=None,
                lore_codex='Drei Tode — Erstes Mal weinte sie. '
                           'Zweites Mal kämpfte sie. Drittes Mal '
                           'blieb sie.',
                faction_rep={'knochenwitwen': 10}),
    on_complete_quote=(
        "„Du kennst meine Tode jetzt. Ich kenne deinen ersten Tod "
        "auch — er ist näher als du denkst."  # Vossharil
    ),
)


QUEST_WURZEL_GIFT = dict(
    id='akt4_wurzel_gift',
    title='Brans Wurzel-Tinktur',
    giver='Wurzel-Apotheker Bran',
    giver_kind='vendor',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    stages=[
        dict(text='Sprich mit Bran, dem Wurzel-Apotheker.',
             type=StageType.TALK,
             target={'npc_name': 'Wurzel-Apotheker Bran'},
             on_complete='Bran: „Vier Wurzel-Splitter. Gift, das '
                         'heilt. Heilkraut, das tötet. Bring sie."'),
        dict(text='Sammle 4 Erinnerungssteine (Wurzel-Substrate).',
             type=StageType.COLLECT,
             target={'item_kind': 'gem'}, count=4,
             on_complete='Die Substrate atmen — leise, langsam.'),
        dict(text='Kehre zu Bran zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Wurzel-Apotheker Bran'},
             on_complete='Bran mischt. Es riecht nach Wurzel '
                         'und Erinnerung.'),
    ],
    reward=dict(gold=200, xp=150, item=None,
                faction_rep={'knochenwitwen': 10}),
    on_complete_quote=(
        "„Gift und Heilkraut — derselbe Stoff. Nur die Dosis "
        "entscheidet. So wie bei Lügen."  # Bran
    ),
)


QUEST_BOUNTY_FADENGEBUNDENE = dict(
    id='akt4_bounty_fadengebundene',
    title='Bounty: Faden-Gebundene',
    giver='Knochen-Hexe Marvel',
    giver_kind='smith',
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    stages=[
        dict(text='Sprich mit Marvel am Knochen-Stand.',
             type=StageType.TALK,
             target={'npc_name': 'Knochen-Hexe Marvel'},
             on_complete='Marvel: „10 Faden-Gebundene. Ihre Knochen '
                         'sind mir was wert."'),
        dict(text='Erschlage 10 Faden-Gebundene.',
             type=StageType.KILL,
             target={'bestiary_key': 'faden_gebundener'}, count=10,
             on_complete='Die Fäden fallen. Die Knochen bleiben.'),
        dict(text='Kehre zu Marvel zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Knochen-Hexe Marvel'},
             on_complete='Marvel zählt aus. Sie ist zufrieden.'),
    ],
    reward=dict(gold=110, xp=80, item=None,
                faction_rep={'knochenwitwen': 7}),
    on_complete_quote=(
        "„Komm wieder. Ich brauche immer Knochen. Und manchmal "
        "frische Augen."  # Marvel
    ),
)


# Hidden Akt 4 — Versteckter Garten der Saatträger.
# Discovery: 3 Wurzel-Lore-Tafeln → versteckter Hain wo die
# Saatträger eine Aspekt-Probe ablegen.
QUEST_VERSTECKTER_GARTEN = dict(
    id='akt4_versteckter_garten',
    title='Der versteckte Garten',
    giver=None,
    giver_kind=None,
    region='Akt 4 — Wurzelgrab',
    is_main=False,
    discover_via_interact={'decor_kind': 'lore_tablet', 'count': 3},
    stages=[
        dict(text='Aktiviere die drei Saatträger-Sigille in '
                  'chronologischer Reihenfolge.',
             type=StageType.PUZZLE,
             target={'sequence': ['saat_keim',
                                   'saat_wachsen',
                                   'saat_blueht']},
             on_complete='Drei Sigille glühen. Der Garten antwortet '
                         'mit einem leisen Atemzug.'),
        dict(text='Empfange Nheyras Segnung — wähle das Aspekt.',
             type=StageType.CHOICE,
             target={'flag': 'nheyra_blessing',
                      'options': ['atem', 'wind', 'samen']},
             on_complete='Der Atem bindet sich an dich.'),
    ],
    reward=dict(gold=250, xp=200, item=None,
                lore_codex='Versteckter Garten — Nheyra atmet hier. '
                           'Wer ihn betritt, atmet mit.',
                faction_rep={'saattraeger': 25}),
    on_complete_quote=(
        "Etwas in dir wurzelt — leise, aber endgültig."
    ),
)


# ============================================================
# AKT 5 — Nebenquests (Update #157, WELT_AUFBAU 3.7)
# ============================================================
# 5 Sidequests im Spiegelhof (Velharn-Spiegelstadt).  Givers:
#   Voraius, Nheya (Spiegel-Magierin), Sehir (Glasgolden-Händlerin),
#   Mara die Mahnerin (Reveal-Stage).

QUEST_SENATOR_STREIT = dict(
    id='akt5_senator_streit',
    title='Senator-Streit',
    giver='Erster Senator Voraius',
    giver_kind='quest',
    region='Akt 5 — Spiegelstadt',
    is_main=False,
    stages=[
        dict(text='Sprich mit Voraius über den Senator-Streit.',
             type=StageType.TALK,
             target={'npc_name': 'Erster Senator Voraius'},
             on_complete='Voraius: „Sechs Senator-Phantome streiten. '
                         'Mediiere — oder ende den Streit anders."'),
        dict(text='Erschlage 6 Senator-Phantome.',
             type=StageType.KILL,
             target={'bestiary_key': 'senator_phantom'}, count=6,
             on_complete='Die Phantome verschwinden — manche dankbar, '
                         'andere wütend.'),
        dict(text='Wähle: Voraius unterstützen ODER neutral '
                  'mediieren.',
             type=StageType.CHOICE,
             target={'flag': 'senator_mediation',
                      'options': ['voraius', 'neutral']},
             on_complete='Velharn dreht sich entweder zu dir hin — '
                         'oder von dir weg.'),
        dict(text='Kehre zu Voraius zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Erster Senator Voraius'},
             on_complete='Voraius weint. Nicht aus Trauer.'),
    ],
    reward=dict(gold=350, xp=280, item=None,
                faction_rep={'mahnmal_gilde': 20}),
    on_complete_quote=(
        "„Velharn hörte dich. Velharn antwortet vielleicht. Velharn "
        "vielleicht."  # Voraius
    ),
)


QUEST_STUNDEN_SPIEGEL_MEISTER = dict(
    id='akt5_stunden_spiegel_meister',
    title='Stunden-Spiegel-Meister',
    giver='Spiegel-Magierin Nheya',
    giver_kind='mystic',
    region='Akt 5 — Spiegelstadt',
    is_main=False,
    stages=[
        dict(text='Sprich mit Nheya, der Spiegel-Magierin.',
             type=StageType.TALK,
             target={'npc_name': 'Spiegel-Magierin Nheya'},
             on_complete='Nheya: „Acht Spiegel-Stalker. Sie kopieren '
                         'dich. Mach Schluss mit dem Original-Streit."'),
        dict(text='Erschlage 8 Spiegel-Stalker.',
             type=StageType.KILL,
             target={'bestiary_key': 'spiegel_stalker'}, count=8,
             on_complete='Die Stalker fallen wie Spiegel-Scherben — '
                         'jeder reflektiert deinen letzten Atem.'),
        dict(text='Kehre zu Nheya zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Spiegel-Magierin Nheya'},
             on_complete='Nheya: „Du bist jetzt Spiegel-Meister. '
                         'Ein gefährlicher Titel."'),
    ],
    reward=dict(gold=300, xp=230, item=None,
                faction_rep={'mahnmal_gilde': 25}),
    on_complete_quote=(
        "„Spiegel zeigen, was ist. Spiegel-Meister zeigen, was war. "
        "Beides ist gefährlich."  # Nheya
    ),
)


QUEST_VELHARN_GESCHICHTE = dict(
    id='akt5_velharn_geschichte',
    title='Velharns Geschichte',
    giver='Glasgolden-Händlerin Sehir',
    giver_kind='vendor',
    region='Akt 5 — Spiegelstadt',
    is_main=False,
    stages=[
        dict(text='Sprich mit Sehir, der Glasgolden-Händlerin.',
             type=StageType.TALK,
             target={'npc_name': 'Glasgolden-Händlerin Sehir'},
             on_complete='Sehir: „Drei Zeiten — Glasgolden, '
                         'Götterkrieg, Gegenwart. Lies sie."'),
        dict(text='Interagiere mit 3 Velharn-Lore-Tafeln.',
             type=StageType.INTERACT,
             target={'decor_kind': 'lore_tablet'}, count=3,
             on_complete='Drei Zeiten falten sich. Du weißt jetzt, '
                         'wie alt Velharn wirklich ist.'),
        dict(text='Kehre zu Sehir zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Glasgolden-Händlerin Sehir'},
             on_complete='Sehir nickt. „Du trägst Velharn jetzt — '
                         'leichter als ich."'),
    ],
    reward=dict(gold=200, xp=150, item=None,
                lore_codex='Velharns drei Zeiten — Glasgolden, '
                           'Götterkrieg, Gegenwart.  Eine Stadt, drei '
                           'Atemzüge.',
                faction_rep={'mahnmal_gilde': 12}),
    on_complete_quote=(
        "„Velharn ist nicht alt. Velharn ist verspätet. Das ist "
        "ein Unterschied."  # Sehir
    ),
)


QUEST_BOUNTY_STUNDEN_WANDLER = dict(
    id='akt5_bounty_stunden_wandler',
    title='Bounty: Glasscherben-Tänzerinnen',
    giver='Glasgolden-Händlerin Sehir',
    giver_kind='vendor',
    region='Akt 5 — Spiegelstadt',
    is_main=False,
    stages=[
        dict(text='Sprich mit Sehir — Bounty-Brett.',
             type=StageType.TALK,
             target={'npc_name': 'Glasgolden-Händlerin Sehir'},
             on_complete='Sehir: „10 Tänzerinnen — sie zerschneiden '
                         'meine Auslage. 13 Gold pro Stück."'),
        dict(text='Erschlage 10 Glasscherben-Tänzerinnen.',
             type=StageType.KILL,
             target={'bestiary_key': 'glasscherben_taenzerin'}, count=10,
             on_complete='Die Tänzerinnen splittern. Velharn ist '
                         'leiser.'),
        dict(text='Kehre zu Sehir zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Glasgolden-Händlerin Sehir'},
             on_complete='Sehir zählt. Es stimmt — fast.'),
    ],
    reward=dict(gold=130, xp=90, item=None,
                faction_rep={'mahnmal_gilde': 6}),
    on_complete_quote=(
        "„Komm wieder. Velharn produziert Tänzerinnen schneller "
        "als ich sie zählen kann."  # Sehir
    ),
)


# Hidden Akt 5 — Korven oder Helst? Akt-6-Reveal-Setup.
# Discovery: 4 Spiegel-Lore-Tafeln → versteckter Hinweis darauf,
# wer in Akt 7 als Im-Nesh in Disguise auftritt.
QUEST_KORVEN_ODER_HELST = dict(
    id='akt5_korven_oder_helst',
    title='Korven oder Helst?',
    giver=None,
    giver_kind=None,
    region='Akt 5 — Spiegelstadt',
    is_main=False,
    discover_via_interact={'decor_kind': 'lore_tablet', 'count': 4},
    stages=[
        dict(text='Aktiviere die drei Spiegel-Sigille (Vergangenheit '
                  '→ Gegenwart → Zukunft).',
             type=StageType.PUZZLE,
             target={'sequence': ['mirror_past',
                                   'mirror_now',
                                   'mirror_future']},
             on_complete='Drei Spiegel zeigen kurz ein Gesicht — du '
                         'erkennst es, aber sagst nichts.'),
        dict(text='Empfange den Hinweis: Wer ist Im-Nesh in Disguise?',
             type=StageType.CHOICE,
             target={'flag': 'akt5_im_nesh_clue',
                      'options': ['korven_hint', 'helst_hint',
                                   'beide_zweifeln']},
             on_complete='Der Hinweis wickelt sich um deinen '
                         'Brustkasten — eng, leise.'),
    ],
    reward=dict(gold=180, xp=140, item=None,
                lore_codex='Korven oder Helst? — Einer von beiden '
                           'trägt Im-Neshs Stimme. Akt 6 wird klären.',
                faction_rep={'erblinde_kirche': 15}),
    on_complete_quote=(
        "Du trägst jetzt einen Verdacht. Verdacht ist eine andere "
        "Art von Wissen."
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
# AKT 2 — Nebenquests (Update #155, WELT_AUFBAU 3.4)
# ============================================================
# 5 Sidequests im Echo-Markt-Outpost (Glasgoldene Ruinen):
#  - Helst-Pact-Stones (Faction Erblinde Kirche)
#  - Echo-Handel (Side, Vorul-Vendor-Unlock)
#  - Otreth-Glas-Gravur (Crafting via Salir)
#  - Goldstaub-Erinnerung (Lore, Mara-Chain Stage 2)
#  - Bounty-Goldstaub-Diener (Bounty, repeatable)
#  - Velharn-Vorhof (Hidden, Akt-5-Setup via Decor-Discovery)
# Lore-Quellen: VELGRAD_LORE_BIBEL Teil 8 (Velharn-Geschichte),
# VELGRAD_VOICE_LINES_POOL.md (Helst/Vorul-Pool).

QUEST_HELST_PACT_STONES = dict(
    id='akt2_helst_pact_stones',
    title='Helsts Pakt-Steine',
    giver='Bruder Helst der Hundertjährige',
    giver_kind='quest',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    stages=[
        dict(text='Sprich mit Bruder Helst über die Pakt-Steine.',
             type=StageType.TALK,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst: „Drei Pakt-Steine. Jeder erinnert sich '
                         'an einen anderen Vertrag. Geh — und höre genau."'),
        dict(text='Erschlage 6 Senator-Phantome in den Ruinen.',
             type=StageType.KILL,
             target={'bestiary_key': 'senator_phantom'}, count=6,
             on_complete='Die Phantome bröckeln zu Goldstaub. Du atmest '
                         'sie ein, ohne es zu wollen.'),
        dict(text='Kehre zu Helst zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst nickt. „Jetzt ist Velharn ein '
                         'Stück leichter."'),
    ],
    reward=dict(gold=250, xp=200, item=None,
                # WELT_AUFBAU 6.1: Erblinde Kirche +30
                # (Helst-Mahnmal-Auftrag).  Tribunal -8 via Matrix.
                faction_rep={'erblinde_kirche': 30}),
    on_complete_quote=(
        "„Die Senatoren reden noch. Aber sie hören jetzt auch zu. "
        "Du hast eine Stille gemacht — eine, die antwortet."
        # Bruder Helst
    ),
)


QUEST_ECHO_HANDEL = dict(
    id='akt2_echo_handel',
    title='Vorul der Erinnerten Waren',
    giver='Senator-Geist Vorul',
    giver_kind='vendor',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    stages=[
        dict(text='Sprich mit Senator-Geist Vorul im Echo-Markt.',
             type=StageType.TALK,
             target={'npc_name': 'Senator-Geist Vorul'},
             on_complete='Vorul: „Bring mir, was die Diener vergessen '
                         'haben. Goldstaub ist auch eine Erinnerung."'),
        dict(text='Erschlage 8 Goldstaub-Diener.',
             type=StageType.KILL,
             target={'bestiary_key': 'goldstaub_diener'}, count=8,
             on_complete='Der Staub findet Form, wenn du ihn nicht ansiehst.'),
        dict(text='Kehre zu Vorul zurück — er wird seinen Laden öffnen.',
             type=StageType.RETURN,
             target={'npc_name': 'Senator-Geist Vorul'},
             on_complete='Vorul lächelt — soweit ein Geist lächeln kann.'),
    ],
    reward=dict(gold=200, xp=150, item=None,
                # WELT_AUFBAU 6.1: Echo-Senatoren sind keine eigene
                # Faction in der Registry — Rep geht an Erblinde Kirche
                # (Helst hat sie zu Vorul geführt).
                faction_rep={'erblinde_kirche': 15}),
    on_complete_quote=(
        "„Mein Laden ist ein Versprechen, das ich mir selbst gemacht "
        "habe. Bevor ich gestorben bin. Und nachher."  # Vorul
    ),
)


QUEST_OTRETH_GLAS_GRAVUR = dict(
    id='akt2_otreth_glas_gravur',
    title='Salirs Glas-Gravur',
    giver='Otreth-Lehrling Salir',
    giver_kind='smith',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    stages=[
        dict(text='Sprich mit Salir, Otreths Lehrling.',
             type=StageType.TALK,
             target={'npc_name': 'Otreth-Lehrling Salir'},
             on_complete='Salir: „Otreth hat mir Glas-Gravur '
                         'beigebracht. Sammle 3 Erinnerungssteine, '
                         'ich graviere sie für dich."'),
        dict(text='Sammle 3 Erinnerungssteine in den Ruinen.',
             type=StageType.COLLECT,
             target={'item_kind': 'gem'}, count=3,
             on_complete='Die Steine summen leise — als ob sie '
                         'wüssten, wo sie hingehören.'),
        dict(text='Kehre zu Salir zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Otreth-Lehrling Salir'},
             on_complete='Salir gravierst die Steine. Otreth wäre stolz.'),
    ],
    reward=dict(gold=180, xp=120, item=None,
                faction_rep={'mahnmal_gilde': 10}),
    on_complete_quote=(
        "„Otreth sagt, jeder Stein erinnert sich an seinen Träger. "
        "Trag sie gut."  # Salir
    ),
)


QUEST_GOLDSTAUB_ERINNERUNG = dict(
    id='akt2_goldstaub_erinnerung',
    title='Goldstaub-Erinnerung',
    giver='Bruder Helst der Hundertjährige',
    giver_kind='quest',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    # Nur nach Helst-Pact-Stones offerable (Mara-Chain-artige Logik)
    requires_quests=['akt2_helst_pact_stones'],
    stages=[
        dict(text='Sprich mit Helst über die Goldstaub-Erinnerungen.',
             type=StageType.TALK,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst: „Goldstaub-Diener tragen das, was '
                         'Velharn nicht mehr sagen darf. Sammle '
                         '4 ihrer Erinnerungen."'),
        dict(text='Erschlage 4 Goldstaub-Diener.',
             type=StageType.KILL,
             target={'bestiary_key': 'goldstaub_diener'}, count=4,
             on_complete='Die Erinnerungen flüstern leise — eine '
                         'davon klingt wie deine Mutter.'),
        dict(text='Kehre zu Helst zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst legt seine Hand auf deinen Arm. '
                         'Lange. Schweigend.'),
    ],
    reward=dict(gold=150, xp=100, item=None,
                lore_codex='Goldstaub-Erinnerung — Was Velharn '
                           'vergessen wollte, tragen die Diener jetzt.',
                faction_rep={'erblinde_kirche': 10}),
    on_complete_quote=(
        "„Manche Erinnerungen sind nicht für uns. Aber sie tragen "
        "uns trotzdem."  # Helst
    ),
)


QUEST_BOUNTY_GOLDSTAUB_DIENER = dict(
    id='akt2_bounty_goldstaub_diener',
    title='Bounty: Goldstaub-Diener',
    giver='Bruder Helst der Hundertjährige',
    giver_kind='quest',
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    stages=[
        dict(text='Sprich mit Helst — Bounty-Brett.',
             type=StageType.TALK,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst: „10 Diener. Sie tragen Goldstaub, '
                         'der nicht uns gehört. Bring ihn zurück."'),
        dict(text='Erschlage 10 Goldstaub-Diener.',
             type=StageType.KILL,
             target={'bestiary_key': 'goldstaub_diener'}, count=10,
             on_complete='Die Diener fallen wie Staub auf Staub.'),
        dict(text='Kehre zu Helst zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Bruder Helst der Hundertjährige'},
             on_complete='Helst zählt. Es stimmt.'),
    ],
    reward=dict(gold=120, xp=80, item=None,
                faction_rep={'erblinde_kirche': 8}),
    on_complete_quote=(
        "„Das Brett wird nie leer. Komm wieder, wenn du Gold "
        "brauchst — oder Vergessen."  # Helst
    ),
)


# Hidden — Velharn-Vorhof (Akt-5-Setup).
# Discovery: 4 Lore-Tafeln in den Glasgoldenen Ruinen → versteckter
# Vorhof zu Velharn (Akt 5).  Setup-Quest die später für Akt 5
# einen Bonus-Pfad öffnet.
QUEST_VELHARN_VORHOF = dict(
    id='akt2_velharn_vorhof',
    title='Der Vorhof zu Velharn',
    giver=None,
    giver_kind=None,
    region='Akt 2 — Glasgoldene Ruinen',
    is_main=False,
    discover_via_interact={'decor_kind': 'lore_tablet', 'count': 4},
    stages=[
        dict(text='Aktiviere die drei Spiegel-Sigille in '
                  'chronologischer Reihenfolge (Glasgolden → '
                  'Götterkrieg → Gegenwart).',
             type=StageType.PUZZLE,
             target={'sequence': ['mirror_glasgolden',
                                   'mirror_goetterkrieg',
                                   'mirror_gegenwart']},
             on_complete='Drei Spiegel atmen synchron — sehr leise.'),
        dict(text='Setze ein Velharn-Vorhof-Flag — du wirst '
                  'Akt 5 anders betreten.',
             type=StageType.CHOICE,
             target={'flag': 'velharn_vorhof',
                      'options': ['glasgolden', 'goetterkrieg',
                                   'gegenwart']},
             on_complete='Die Wahl bindet einen Faden zu Voraius.'),
    ],
    reward=dict(gold=120, xp=100, item=None,
                lore_codex='Velharn-Vorhof — Drei Zeiten falten sich, '
                           'wenn du sie in der richtigen Reihenfolge '
                           'verlässt.',
                faction_rep={'erblinde_kirche': 15}),
    on_complete_quote=(
        "Etwas in Velharn dreht sich. Es wird auf dich warten."
    ),
)


# ============================================================
# AKT 6 — DREI WUNDEN (Update #153, WELT_AUFBAU 3.8)
# ============================================================
# Im Drei-Wunden-Lager (Akt-6-Hub) führt Mara die Mahnerin (Akt-6-Stage)
# den Spieler durch drei parallel-laufende Main-Quests, eine pro Wunde:
#   - Salzwunde  → Ertrunkene Königin  (Bestiarium #26)
#   - Aschwunde  → Echo-Drache         (Bestiarium #27)
#   - Hohlwunde  → Nicht-Gott          (Bestiarium #28)
# Reihenfolge frei.  Nach Abschluss aller drei wird die Finale-Quest
# „Pakt übersetzen" (Tehrnal) freigeschaltet — der Spieler erfährt dort,
# wer im Verborgenen Im-Nesh ist (Korven oder Helst — abhängig von
# `flags['korven_helst_reveal']`).  Die Quests verwenden das neue
# `requires_quests`-Prerequisite-Feld (Update #153) für saubere Gating.
# Lore-Quellen:
#   - VELGRAD_LORE_BIBEL.md Teil 6 (Drei Wunden Theologie)
#   - VELGRAD_VOICE_LINES_POOL.md (Mara-Akt-6-Pool, Tehrnal-Pool)

QUEST_SALZWUNDE_LESEN = dict(
    id='akt6_salzwunde_lesen',
    title='Salzwunde lesen',
    giver='Mara die Mahnerin (Akt-6-Stage)',
    giver_kind='quest',
    region='Akt 6 — Drei-Wunden',
    is_main=True,
    stages=[
        dict(text='Sprich mit Mara im Drei-Wunden-Lager.',
             type=StageType.TALK,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara: „Die Salzwunde ruft. Geh hinunter zu '
                         'ihr — sie wird dich kennen, bevor du sie kennst."'),
        dict(text='Stelle dich der Ertrunkenen Königin.',
             type=StageType.KILL,
             target={'bestiary_key': 'ertrunkene_koenigin'}, count=1,
             on_complete='Ertrunkene Königin: „Ich war ihre Königin. '
                         'Sie haben mich ertränkt. Ich erinnere mich '
                         'an euren Vater."'),
        dict(text='Kehre zu Mara zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara schreibt etwas in ihr Bündel. '
                         'Sie zittert nicht.'),
    ],
    reward=dict(gold=700, xp=600, item=None,
                faction_rep={'mahnmal_gilde': 25}),
    on_complete_quote=(
        "„Sie kannte deinen Namen. Manche Wunden geben dir einen Namen "
        "zurück. Du wirst lernen, ihn nicht zu sagen."  # Mara Akt 6
    ),
)


QUEST_ASCHWUNDE_LESEN = dict(
    id='akt6_aschwunde_lesen',
    title='Aschwunde lesen',
    giver='Mara die Mahnerin (Akt-6-Stage)',
    giver_kind='quest',
    region='Akt 6 — Drei-Wunden',
    is_main=True,
    stages=[
        dict(text='Sprich mit Mara — sie weist zur Aschwunde.',
             type=StageType.TALK,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara: „Der Echo-Drache schläft im '
                         'Aschen-Schlund. Geh — er träumt Valsa."'),
        dict(text='Stelle dich dem Echo-Drachen.',
             type=StageType.KILL,
             target={'bestiary_key': 'echo_drache'}, count=1,
             on_complete='Echo-Drache: „Asche kennt eure Namen. '
                         'Eine schmeckt nach mir."'),
        dict(text='Kehre zu Mara zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara: „Du hast einen Aspekt geatmet. '
                         'Behalte das."'),
    ],
    reward=dict(gold=700, xp=600, item=None,
                faction_rep={'erblinde_kirche': 20}),
    on_complete_quote=(
        '„Asche bleibt. Asche erinnert. Das ist alles, was Valsa '
        'jemals gesagt hat."'   # Mara Akt 6
    ),
)


QUEST_HOHLWUNDE_LESEN = dict(
    id='akt6_hohlwunde_lesen',
    title='Hohlwunde lesen',
    giver='Mara die Mahnerin (Akt-6-Stage)',
    giver_kind='quest',
    region='Akt 6 — Drei-Wunden',
    is_main=True,
    stages=[
        dict(text='Sprich mit Mara — sie weist zur Hohlwunde.',
             type=StageType.TALK,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara: „Die Hohlwunde antwortet nicht. Aber '
                         'sie hört. Geh — und sei leise."'),
        dict(text='Stelle dich dem Nicht-Gott.',
             type=StageType.KILL,
             target={'bestiary_key': 'nicht_gott'}, count=1,
             on_complete='Nicht-Gott: ( — keine Worte — )'),
        dict(text='Kehre zu Mara zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Mara die Mahnerin (Akt-6-Stage)'},
             on_complete='Mara schweigt lange. Dann nickt sie nur.'),
    ],
    reward=dict(gold=700, xp=600, item=None,
                faction_rep={'mahnmal_gilde': 25}),
    on_complete_quote=(
        "„Du hast eine Stille gehört. Das ist mehr als die meisten. "
        "Behalte sie. Sie wird dich fragen, ob du noch da bist."
        # Mara Akt 6
    ),
)


# Akt 6 Finale — Pakt übersetzen.  Erfordert alle 3 Wunden-Reads.
# CHOICE: korven_helst_reveal — der Spieler wählt, wessen Stimme er
# in Akt 7 als Im-Nesh-Maske trifft.  Tehrnal moderiert.
QUEST_PAKT_UEBERSETZEN = dict(
    id='akt6_pakt_uebersetzen',
    title='Pakt übersetzen',
    giver='Wunden-Lesende Tehrnal',
    giver_kind='quest',
    region='Akt 6 — Drei-Wunden',
    is_main=True,
    # Update #153: requires_quests — Tehrnal redet erst wenn alle drei
    # Wunden gelesen sind.  Akt-Gate (Akt 6 → completed_dungeons>=5)
    # bleibt zusätzlich aktiv.
    requires_quests=['akt6_salzwunde_lesen',
                      'akt6_aschwunde_lesen',
                      'akt6_hohlwunde_lesen'],
    stages=[
        dict(text='Sprich mit Tehrnal, der Wunden-Lesenden.',
             type=StageType.TALK,
             target={'npc_name': 'Wunden-Lesende Tehrnal'},
             on_complete='Tehrnal: „Du hast drei Wunden gelesen. Eine '
                         'davon hat dich gelesen. Das ist die, die '
                         'jetzt zählt."'),
        # CHOICE: Korven oder Helst als Im-Nesh-Maske (Akt 7 Setup)
        dict(text='Wähle: Wer ist Im-Nesh — Korven Vor ODER Bruder Helst?',
             type=StageType.CHOICE,
             target={'flag': 'korven_helst_reveal',
                      'options': ['korven', 'helst']},
             on_complete='Die Wahl wickelt einen Faden, der dich nach '
                         'Hohlwort führt.'),
        # CONDITIONAL: Korven-Pfad — Tehrnal-Zusatz-Lore
        dict(text='(Wenn Korven:) Höre Tehrnals Korven-Lesung.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'korven_helst_reveal=korven',
                      'npc_name': 'Wunden-Lesende Tehrnal'},
             on_complete='Tehrnal: „Korven war immer leiser als seine '
                         'Stimme. Das verriet ihn."'),
        # CONDITIONAL: Helst-Pfad — Tehrnal-Zusatz-Lore
        dict(text='(Wenn Helst:) Höre Tehrnals Helst-Lesung.',
             type=StageType.CONDITIONAL,
             target={'requires_flag': 'korven_helst_reveal=helst',
                      'npc_name': 'Wunden-Lesende Tehrnal'},
             on_complete='Tehrnal: „Helsts Augenbinde war eine '
                         'Maske auf einer Maske. Du hast es '
                         'gerochen."'),
        dict(text='Bereite dich auf Hohlwort vor — kehre zu Tehrnal.',
             type=StageType.RETURN,
             target={'npc_name': 'Wunden-Lesende Tehrnal'},
             on_complete='Tehrnal: „Wenn du Hohlwort betrittst — '
                         'sei nicht ganz da. Das ist die einzige '
                         'Regel."'),
    ],
    reward=dict(gold=1200, xp=1000, item='Sieben-Atem-Stab',
                faction_rep={'mahnmal_gilde': 50,
                              'erblinde_kirche': 30}),
    on_complete_quote=(
        "„Du gehst nicht mit Wissen nach Hohlwort. Du gehst mit Echo. "
        "Echo schützt nicht. Aber es hallt zurück, wenn du fällst."
        # Tehrnal
    ),
)


# ============================================================
# AKT 1 — Tribunal-Faction-Sidequest (Update #153, WELT_AUFBAU 3.2)
# ============================================================
# Stadtsprecher Eldon gibt Akt-1-Bounty: 5 Tribunal-Konstrukt-Späher
# bei den Stadtmauern erschlagen.  Wirkt auf Tribunal-Faction-Rep
# (−Faction-Rep zu Tribunal, +Faction-Rep zu Mahnmal-Gilde via
# Konflikt-Matrix).  Lore-Anker: Eldon ist Stadtsprecher, das Tribunal
# stellt Brassweir unter Verdacht — erste Reibung mit dem Inquisitions-
# System, bevor der Akt-3-Vehren-Boss kommt.

QUEST_TRIBUNAL_GERUECHT = dict(
    id='akt1_tribunal_geruecht',
    title='Das Tribunal-Gerücht',
    giver='Stadtsprecher Eldon',
    giver_kind='quest',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Stadtsprecher Eldon am Quest-Board.',
             type=StageType.TALK,
             target={'npc_name': 'Stadtsprecher Eldon'},
             on_complete='Eldon: „Tribunal-Konstrukte schleichen an '
                         'unseren Mauern. Mach ihnen klar, dass '
                         'Brassweir keine Asche-Stadt ist."'),
        dict(text='Erschlage 5 Tribunal-Konstrukt-Späher.',
             type=StageType.KILL,
             target={'bestiary_key': 'tribunal_konstrukt'}, count=5,
             on_complete='Die Konstrukte fallen still. Asche bleibt '
                         'auf deinen Sohlen.'),
        dict(text='Kehre zu Eldon zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Stadtsprecher Eldon'},
             on_complete='Eldon: „Das hat man im Helst-Lager gehört. '
                         'Sie werden sich erinnern."'),
    ],
    reward=dict(gold=150, xp=110, item=None,
                # WELT_AUFBAU 6.1: Tribunal -15 (Spieler hat ihre
                # Späher getötet).  Mahnmal-Gilde +20 (Eldon dankt).
                # Erblinde Kirche +5 (Konflikt-Matrix-Bonus — sie
                # hasst das Tribunal auch).
                faction_rep={'tribunal_asche': -15,
                              'mahnmal_gilde': 20,
                              'erblinde_kirche': 5}),
    on_complete_quote=(
        "„Du hast Asche an deinen Sohlen. Das wirst du nicht "
        "abschütteln. Aber du wirst lernen, sie anders zu tragen."
        # Eldon
    ),
)


# Bounty (Repeatable) — Salzgekreuzte-Cleanup-Auftrag.
# Eldon hängt regelmäßig Bounty-Aufträge ans Quest-Board.  Diese hier
# ist die einfachste: 10 Salzgekreuzte erledigen, 60 Gold + 50 XP.
# Lore: Bounties sind das täglich Brot der Mahnmal-Gilde — kleine
# Geld-Quellen, die Brassweir am Leben halten.

# Hidden — Versunkenes Grab.
# Discovery: Der Spieler interagiert mit 3 Lore-Tafeln in der Krypta;
# danach „findet" er hinweise auf ein versunkenes Grab.  Hauptetappen:
# PUZZLE (3 Sigil-Tafeln in richtiger Reihenfolge: Salz → Asche → Hohl),
# KILL Mini-Boss (salzhueter_brut), und ein Lore-Codex-Entry als Reward.
# Lore-Anker: VELGRAD_LORE_BIBEL Teil 6 (Drei Wunden Sigil-Sequence),
# Brassweir-Vergangenheit als Akt-1-Hidden-Trigger.

QUEST_VERSUNKENES_GRAB = dict(
    id='akt1_versunkenes_grab',
    title='Das Versunkene Grab',
    giver=None,
    giver_kind=None,
    region='Akt 1 — Brassweir',
    is_main=False,
    # Discovery: 3 Lore-Tafeln in der Krypta angefasst → Quest erscheint
    discover_via_interact={'decor_kind': 'lore_tablet', 'count': 3},
    stages=[
        dict(text='Aktiviere die drei Sigil-Tafeln in chronologischer '
                  'Wunden-Reihenfolge: Salz → Asche → Hohl.',
             type=StageType.PUZZLE,
             target={'sequence': ['sigil_salz',
                                   'sigil_asche',
                                   'sigil_hohl']},
             on_complete='Die Tafeln glühen kurz. Etwas atmet auf, '
                         'tief unter dir.'),
        dict(text='Stelle dich der Salzhüter-Brut im Grab-Boss-Raum.',
             type=StageType.KILL,
             target={'bestiary_key': 'salzhueter_brut'}, count=1,
             on_complete='Die Brut bricht ein. Das Grab schweigt wieder.'),
    ],
    reward=dict(gold=100, xp=80, item=None,
                # Kein Faction-Rep, dafür Codex-Entry (Lore-Block)
                lore_codex='Versunkenes Grab — Vor Aithein gab es '
                           'das Grab. Vor dem Grab gab es Brassweir.',
                faction_rep={'mahnmal_gilde': 10}),
    on_complete_quote=(
        "Etwas Altes nickt dir zu. Du verstehst nicht, von wem es nickt."
    ),
)


QUEST_BOUNTY_SALZGEKREUZTE = dict(
    id='akt1_bounty_salzgekreuzte',
    title='Bounty: Salzgekreuzte',
    giver='Stadtsprecher Eldon',
    giver_kind='quest',
    region='Akt 1 — Brassweir',
    is_main=False,
    stages=[
        dict(text='Sprich mit Eldon (Bounty-Brett).',
             type=StageType.TALK,
             target={'npc_name': 'Stadtsprecher Eldon'},
             on_complete='Eldon: „10 Salzgekreuzte. Pro Stück 6 Gold. '
                         'Brassweir braucht ihre Asche zurück."'),
        dict(text='Erschlage 10 Salzgekreuzte in der Krypta.',
             type=StageType.KILL,
             target={'bestiary_key': 'salzgekreuzter'}, count=10,
             on_complete='Du zählst nicht mehr mit. Die Krypta atmet '
                         'kürzer aus.'),
        dict(text='Kehre zu Eldon zurück.',
             type=StageType.RETURN,
             target={'npc_name': 'Stadtsprecher Eldon'},
             on_complete='Eldon zählt aus. Es stimmt.'),
    ],
    reward=dict(gold=60, xp=50, item=None,
                faction_rep={'mahnmal_gilde': 5}),
    on_complete_quote=(
        "„Du kannst wiederkommen. Das Brett wird nie leer."  # Eldon
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
    # Update #152 — Akt 2 + Akt 4 Main-Quests (Quest-Spine durchziehen):
    QUEST_ASCH_PROPHEZEIUNG,
    QUEST_SHULAVH_FADEN,
    # Update #153 — Akt 6 Drei-Wunden + Akt 1 Tribunal-Faction:
    QUEST_SALZWUNDE_LESEN,
    QUEST_ASCHWUNDE_LESEN,
    QUEST_HOHLWUNDE_LESEN,
    QUEST_PAKT_UEBERSETZEN,
    QUEST_TRIBUNAL_GERUECHT,
    QUEST_BOUNTY_SALZGEKREUZTE,
    # Update #154 — Hidden Quest mit Discovery via Decor-Interact:
    QUEST_VERSUNKENES_GRAB,
    # Update #155 — Akt-2-Sidequest-Bukett (5 NPC-given + 1 Hidden):
    QUEST_HELST_PACT_STONES,
    QUEST_ECHO_HANDEL,
    QUEST_OTRETH_GLAS_GRAVUR,
    QUEST_GOLDSTAUB_ERINNERUNG,
    QUEST_BOUNTY_GOLDSTAUB_DIENER,
    QUEST_VELHARN_VORHOF,
    # Update #157 — Akt-3-Sidequest-Bukett (5 NPC + 0 Hidden):
    QUEST_ERBLINDER_PRIESTER_TRIAL,
    QUEST_LETZTE_LEGION,
    QUEST_TRIBUNAL_INFILTRATION,
    QUEST_BOUNTY_ASCH_WOLF,
    QUEST_VALSA_TRAENE,
    QUEST_INQUISITIONS_KLINGE,
    # Update #157 — Akt-4-Sidequest-Bukett (5 NPC + 1 Hidden):
    QUEST_KNOCHENWITWEN_AUFNAHME,
    QUEST_HOHLE_SOHN,
    QUEST_DREI_TODE,
    QUEST_WURZEL_GIFT,
    QUEST_BOUNTY_FADENGEBUNDENE,
    QUEST_VERSTECKTER_GARTEN,
    # Update #157 — Akt-5-Sidequest-Bukett (4 NPC + 1 Hidden):
    QUEST_SENATOR_STREIT,
    QUEST_STUNDEN_SPIEGEL_MEISTER,
    QUEST_VELHARN_GESCHICHTE,
    QUEST_BOUNTY_STUNDEN_WANDLER,
    QUEST_KORVEN_ODER_HELST,
]


def quest_by_id(qid):
    for q in ALL_QUESTS:
        if q['id'] == qid:
            return q
    return None


def quests_offered_by_npc(npc_name):
    """Returnt alle Quests, deren Giver dieser NPC ist."""
    return [q for q in ALL_QUESTS if q.get('giver') == npc_name]


def initial_quests_for_new_game():
    """Quests, die beim Game-Start verfügbar sein sollen.

    Update #149 (User-Report „zu viele Quests auf einmal"):
    NUR die Akt-1-Hauptquest „Die Salzwunde" startet automatisch.
    Otreth-Stein und Mara-Spur werden jetzt über NPC-Talk (mit
    „!"-Marker) angeboten — Spieler bekommt sie nur wenn er aktiv
    mit dem entsprechenden NPC redet. Verhindert dass der Quest-Log
    von Anfang an mit 3 parallelen Aufgaben überladen ist.
    """
    return ['akt1_salzwunde']


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
