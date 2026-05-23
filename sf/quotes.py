"""Voice-Line-Pools für Death-Screens, Wake-Up, Bestiarium-Encounter.

Inhalte stammen aus [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md)
+ Beispielen aus [POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md](POE2_GAMEPLAY_SYSTEMS_ERWEITERUNG.md)
Teil A.5. Werden bei jedem Tod, jedem Wake-Up, jedem Boss-Encounter
zufällig gezogen, sodass keine Line zweimal in Folge erscheint.

Klassen-Mapping zur Velgrad-Lore (Lore-Bibel Teil 6 + 7):
  - warrior → Eisenwächter (Kharn-Lineage)
  - mage    → Funkengeborene (Valsa-Berührt)
  - rogue   → Mahnmal-Söldner (Korven-Vor-Lineage)
"""

import random


# ============================================================
# DAMAGE-TYPE-NORMALISIERUNG
# ============================================================
# Engine-Tags → Quote-Pool-Keys (Briefing A.2).
DAMAGE_TYPE_GROUP = {
    'fire':       'fire',
    'burn':       'fire',
    'ignite':     'fire',
    'cold':       'cold',
    'frost':      'cold',
    'freeze':     'cold',
    'chill':      'cold',
    'lightning':  'lightning',
    'shock':      'lightning',
    'physical':   'physical',
    'phys':       'physical',
    'crush':      'physical',
    'bleed':      'bleed',
    'chaos':      'chaos',
    'poison':     'chaos',
    'void':       'void',
    'falling':    'falling',
    'pit':        'falling',
}


def normalize_damage_type(raw):
    """Mappt einen Engine-Damage-Type auf die Quote-Pool-Bucket-Group."""
    if raw is None:
        return 'generic'
    return DAMAGE_TYPE_GROUP.get(str(raw).lower(), 'generic')


# ============================================================
# DEATH-QUOTES (Briefing A.5 + Voice-Lines „Death-Lines"-Sektion)
# ============================================================
# Generic Pool (greift wenn klassen-spezifisch nichts passt).
DEATH_QUOTES_GENERIC = {
    'fire': [
        "Heißer als... gedacht...",
        "Die Asche kennt meinen Namen — noch nicht.",
        "Das Feuer wollte mich nicht behalten.",
        "Valsas Atem... war zu nah.",
    ],
    'cold': [
        "Kalt... endlich...",
        "Selbst Eis schmilzt vor dem Willen.",
        "Frost ist nur eine andere Form des Atems.",
        "Nheyras Spiegel... hat mich behalten.",
    ],
    'lightning': [
        "Zischt...",
        "Ein Funken war zu viel.",
        "Ich hörte den Donner zu spät.",
    ],
    'physical': [
        "Knochen heilen. Stolz auch.",
        "Wer einmal stirbt, kennt den Weg zurück.",
        "Schwer...",
        "Kharn... war zu still.",
    ],
    'bleed': [
        "Ich blute langsamer als der Faden reißt.",
        "Shulavh, halt den Faden... bitte.",
        "Es tropft. Es tropft nicht mehr.",
    ],
    'chaos': [
        "Ich vergaß zuerst meinen Namen.",
        "Im-Nesh... hat mich umgeschrieben.",
        "Es war nicht das Gift. Es war das Wort.",
    ],
    'void': [
        "Es war nichts dort. Und dann ich auch nicht.",
        "Der Siebte... hat mich gehört.",
    ],
    'falling': [
        "Aaaah...",
        "So tief... war Velgrad nicht.",
    ],
    'generic': [
        "Velgrad behält mich nicht.",
        "Ich war hier. Bin ich noch?",
        "Der Atem ist aus. Vorerst.",
        "Mehr Welt als Mensch.",
    ],
}


# Klassen-spezifische Pools (überschreiben generic wenn vorhanden).
# Quellen: Voice-Lines-Pool Sektion „SPIELER-KLASSEN VOICE-LINES" + Lore-
# Bibel Teil 7 (Klassen-Origin-Stories).
DEATH_QUOTES_BY_CLASS = {
    'warrior': {  # Eisenwächter, Kharn-Lineage
        'fire': [
            "Die Asche kennt meinen Namen — noch nicht.",
            "Ich habe schon heißer geblutet.",
            "Der Turm steht. Ich nicht mehr.",
        ],
        'cold': [
            "Kharn schläft tief... ich auch.",
            "Eis um den Hammer. Eis um mich.",
        ],
        'physical': [
            "Ich... habe gehalten.",
            "Acht Türme fielen. Heute der neunte.",
            "Mein Eid... habe ich gehalten.",
        ],
        'generic': [
            "Der Turm steht.",
            "Ich war Eisenwächter. Ich bin Eisen.",
        ],
    },
    'mage': {  # Funkengeborene, Valsa-Berührt
        'fire': [
            "Ich war... zu nah... an der Asche...",
            "Funken... wollten mich endlich.",
            "Valsa... ich höre dich nun klarer.",
        ],
        'cold': [
            "Selbst Eis schmilzt vor dem Willen.",
            "Frost... ich brannte zu lange.",
        ],
        'lightning': [
            "Funke gegen Funke. Funke gewann.",
        ],
        'physical': [
            "Mein Körper... hielt nicht mit meinem Atem.",
            "Die Funken erinnern mich.",
        ],
        'generic': [
            "Die Funken kennen mich besser.",
            "Ich brannte. Jetzt schlafe ich.",
        ],
    },
    'rogue': {  # Mahnmal-Söldner, Korven-Vor-Lineage
        'fire': [
            "Korven... schuldet mir... fünf...",
            "Verbrannt. Bezahlt.",
        ],
        'cold': [
            "Letzter Schluck. Kalt. Bezahlt.",
        ],
        'physical': [
            "Korven... schuldet mir... fünf...",
            "Lieferung gescheitert. Tut mir leid.",
            "Hätte mehr verlangt.",
        ],
        'bleed': [
            "Mehr Blut als Gold heute.",
            "Mahnmal-Marke gilt nicht mehr.",
        ],
        'generic': [
            "Mahnmal-Marke verfallen.",
            "Geschäft beendet. Nicht wie geplant.",
        ],
    },
}


# ============================================================
# WAKE-UP-QUOTES (Briefing A.5 + Voice-Lines „Wake-Up-Quotes"-Sektion)
# ============================================================
WAKE_UP_QUOTES_GENERIC = [
    "Wieder hier. Wieder Atemzug.",
    "Tot war kürzer als gedacht.",
    "Velgrad hat mich nicht behalten.",
    "Wer ist diesmal verschwunden, während ich weg war?",
    "Mein Schatten kam vor mir an.",
    "Die Welt war schon ohne mich. Sie merkte es nicht.",
]

WAKE_UP_QUOTES_BY_CLASS = {
    'warrior': [
        "Der Turm hat mich zurückgeschickt.",
        "Kharn hat mich noch nicht erkannt.",
        "Eisen hält. Auch in der Asche.",
    ],
    'monk': [
        "Letzter Atem war kürzer als gedacht.",
        "Drei Pagoden hörten mein Schweigen.",
        "Der Schritt war nicht der letzte.",
    ],
    'mage': [
        "Die Funken kennen den Weg zurück.",
        "Valsa lässt nicht los, was brennt.",
        "Asche kann atmen. Heute lerne ich es.",
    ],
    'witch': [
        "Vossharil sagte, ich sei jetzt Dreimalige.",
        "Die Toten haben mich nicht behalten wollen.",
        "Mein Bruder lacht im Wind.",
    ],
    'ranger': [
        "Der Wald rief mich zurück.",
        "Saatkind-Wind weht stärker heute.",
        "Pfeile vergessen ihren Schützen nicht.",
    ],
    'rogue': [
        "Mahnmal-Klausel: Wiederbelebung kostet extra.",
        "Korven wird mir die Rechnung schreiben.",
        "Tot war ein schlechtes Geschäft. Lebend besser.",
    ],
    'huntress': [
        "Faden hält.",
        "Mond hat mich nicht losgelassen.",
        "Schwester, bring mich nicht nochmal heim.",
    ],
    'druid': [
        "Drei Tiere atmen. Ich auch.",
        "Wurzelgrab spuckt mich wieder aus.",
        "Welche Gestalt war ich vorher? Egal.",
    ],
}


# Boss-Arena spezielle Wake-Up-Quotes (wenn `boss_intro` aktiv oder
# der letzte Tod in einer Boss-Arena war).
WAKE_UP_QUOTES_BOSS_ARENA = [
    "Der Boss erinnert sich an mich. Lästig.",
    "Wieder gegen das Gleiche. Heute anders.",
    "Sie wartet. Ich auch.",
]


# ============================================================
# QUOTE-AUSWAHL (Briefing A.5: kein Repeat in Folge)
# ============================================================
_LAST_PICKED = {}  # key → last_quote_text


def _pick_no_repeat(pool_key, options):
    """Wählt zufällig, vermeidet aber direktes Wiederholen."""
    if not options:
        return None
    last = _LAST_PICKED.get(pool_key)
    if len(options) == 1:
        _LAST_PICKED[pool_key] = options[0]
        return options[0]
    choices = [o for o in options if o != last] or options
    picked = random.choice(choices)
    _LAST_PICKED[pool_key] = picked
    return picked


def pick_death_quote(cls, damage_type, first_death=False):
    """Returnt eine Death-Quote für (class, damage_type).

    Reihenfolge: class+type → class+generic → generic+type → generic+generic.
    `first_death` Sub-Pool ist Vorbereitung — aktuell identisch.
    """
    bucket = normalize_damage_type(damage_type)
    cls_pool = DEATH_QUOTES_BY_CLASS.get(cls, {})
    options = (cls_pool.get(bucket)
               or cls_pool.get('generic')
               or DEATH_QUOTES_GENERIC.get(bucket)
               or DEATH_QUOTES_GENERIC['generic'])
    return _pick_no_repeat(f'death|{cls}|{bucket}', options)


def pick_wake_up_quote(cls, boss_arena=False):
    if boss_arena:
        return _pick_no_repeat('wake|boss_arena', WAKE_UP_QUOTES_BOSS_ARENA)
    cls_pool = WAKE_UP_QUOTES_BY_CLASS.get(cls)
    if cls_pool:
        # 60 % Klassen-spezifisch, 40 % generic — verhindert ewig dieselbe Phrasen.
        if random.random() < 0.6:
            return _pick_no_repeat(f'wake|{cls}', cls_pool)
    return _pick_no_repeat('wake|generic', WAKE_UP_QUOTES_GENERIC)


# ============================================================
# DAMAGE-TYPE → DEATH-TRANSITION-FARBE (Briefing A.3)
# ============================================================
# Wird in game._draw_death_transition gelesen.
DEATH_TRANSITION_COLORS = {
    'fire':      (255, 110,  40),   # Flammenfront
    'cold':      (180, 220, 255),   # Frost-Crawl
    'lightning': (240, 240, 255),   # Weiß-Flash (max 2 Frames)
    'physical':  (180,  20,  20),   # Blut-Klatsch + Riss
    'bleed':     (140,   0,   0),   # Vignette rot, Herzschlag
    'chaos':     (160,  80, 220),   # Wave-Distortion + Grünschimmer
    'void':      ( 30,  10,  40),   # Dissolve von innen
    'falling':   ( 10,  10,  18),   # Motion-Blur, Vignette closing
    'generic':   ( 40,  20,  16),
}


# ============================================================
# KLASSEN ↔ FRAKTIONEN aus VELGRAD_LORE_BIBEL.md Teil 6
# ============================================================
# Wird im HUD oben links als subtle Lore-Label angezeigt.
CLASS_FACTION = {
    'warrior':  dict(name='Eisenwächter',     color=(200, 170, 110),
                      aspect='Kharn',
                      creed='Kharn schläft. Wir halten die Form.'),
    'monk':     dict(name='Stille Schritte',  color=(220, 220, 200),
                      aspect='Selbst',
                      creed='Schweigen ist die letzte Sprache, die nicht lügt.'),
    'mage':     dict(name='Funkengeborene',   color=(255, 140,  60),
                      aspect='Valsa',
                      creed='Wer mit Funken spricht, brennt mit ihnen.'),
    'witch':    dict(name='Knochenwitwen',    color=(180,  80, 200),
                      aspect='Shulavh',
                      creed='Die Toten erinnern, was die Lebenden vergessen.'),
    'ranger':   dict(name='Saatträger',       color=(120, 200, 120),
                      aspect='Saatkinder',
                      creed='Vor allen Namen waren wir.'),
    'rogue':    dict(name='Mahnmal-Gilde',    color=(200, 200, 200),
                      aspect='—',
                      creed='Wir verkaufen, was ihr braucht — '
                            'vor allem Erinnerungen.'),
    'huntress': dict(name='Speerschwestern',  color=(240, 180, 100),
                      aspect='Shulavh',
                      creed='Der Mond bindet jede Schwester.'),
    'druid':    dict(name='Wandelnde',        color=(160, 140,  90),
                      aspect='Drei Tiere',
                      creed='Drei Gestalten. Drei Tode. Drei Wiederkünfte.'),
}


def class_faction(cls):
    return CLASS_FACTION.get(cls)


# ============================================================
# KLASSEN-ORIGIN-STORIES (Lore-Bibel Teil 7)
# ============================================================
# Werden im Title-Screen unter der ausgewählten Klassen-Karte angezeigt.
# Texte sind 1:1 aus VELGRAD_LORE_BIBEL.md (Verbannungs-Origin-Quotes).
CLASS_ORIGIN_QUOTES = {
    'warrior': (
        "Ich war im Wachturm Velhost stationiert, als das Tor zu reden "
        "begann. Es sprach den Namen meiner Mutter, die nie gelebt hat. "
        "Ich schlug es nieder. Mein Hauptmann verbannte mich für Häresie."
    ),
    'monk': (
        "Mein Meister atmete dreitausendmal pro Tag. Ich atme dreißig-"
        "tausend. Jeder Atem hält ein Stückchen der Welt fest. Als sie "
        "meinen Tempel auslöschten, atmete ich weiter."
    ),
    'mage': (
        "Mein Dorf lag drei Tagesreisen von der Aschwunde. Ich bin in "
        "einer Nacht geboren, in der die Asche grün brannte. Mit sieben "
        "warfen meine Geschwister mich aus. Mit dreizehn fanden mich die "
        "Erblinden. Sie sagten, ich solle nicht atmen. Ich brenne "
        "stattdessen."
    ),
    'witch': (
        "Mein Bruder starb. Ich hörte seine Stimme im Wind. Sie sagten, "
        "ich solle aufhören zu hören. Ich hörte stattdessen besser. "
        "Vossharil fand mich. Sie sagte, ich sei wie sie. Sie hatte recht."
    ),
    'ranger': (
        "Ich kannte die Namen aller Bäume in der Saatfeste. Eines Tages "
        "erinnerte sich der Wald nicht mehr an mich. Ich kannte alle "
        "Namen, aber niemand wusste meinen. Da wusste ich, ich bin allein "
        "draußen. Also bin ich rausgegangen."
    ),
    'rogue': (
        "Ich habe Erinnerungen für Gold getauscht, seit ich elf war. Mein "
        "erstes Geschäft: die Erinnerung meines Vaters an meine Mutter, "
        "an einen alten Bauern, der seine Frau vergessen hatte. Mein "
        "Vater erinnerte sich nicht, dass er sie verkauft hatte. Das war "
        "der Punkt."
    ),
    'huntress': (
        "Ich war die Sechzehnte unter neunzehn Schwestern. Wir waren ein "
        "Faden. Sie zogen mich aus, weil ich Im-Nesh gesehen haben soll. "
        "Ich habe niemanden gesehen. Aber jetzt suche ich ihn. Vielleicht "
        "haben sie recht gehabt."
    ),
    'druid': (
        "Mein Großvater wurde zu einem Bären, als er starb. Mein Vater zu "
        "einem Wolf. Ich werde — was ich gerade bin. Manchmal Wolf. "
        "Manchmal Wyvern. Manchmal vergesse ich, was ich vorher war. Das "
        "ist normal, sagte mein Großvater."
    ),
}


def class_origin_quote(cls):
    return CLASS_ORIGIN_QUOTES.get(cls)


# ============================================================
# KLASSEN-VOICE-LINES (Voice-Lines-Pool „SPIELER-KLASSEN")
# ============================================================
# Kurze Combat-/Kill-Lines, klassen-spezifisch. Aus
# VELGRAD_VOICE_LINES_POOL.md Sektion „SPIELER-KLASSEN VOICE-LINES".
CLASS_VOICELINES = {
    'warrior': dict(
        boss_kill=['„Vorbei."', '„Der Turm steht."', '„Ich habe gehalten."'],
        combat_start=['„Steh fest!"', '„Komm her!"'],
        levelup=['„Eisen wird härter."'],
        low_hp=['„Eisen biegt sich."', '„Halten."', '„Nicht jetzt."'],
    ),
    'monk': dict(
        boss_kill=['*Lautloses Lächeln*', '„Hm."'],
        combat_start=['*Atemzug*', '*Ki-Atem*'],
        levelup=['„Stiller. Schneller. Klarer."'],
        low_hp=['*flacher Atem*', '„Mitte."', '„Wieder atmen."'],
    ),
    'mage': dict(
        boss_kill=['„Schöner Tod."', '„Valsa hat zugesehen."'],
        combat_start=['„Brenn."', '„Funken kennen mich."'],
        levelup=['„Die Funken kennen mich besser."'],
        low_hp=['„Glut schwindet."', '„Asche, nicht jetzt."'],
    ),
    'witch': dict(
        boss_kill=['„Tot. Sauber."', '„Bruder, hilf."'],
        combat_start=['„Knochen, steh."', '„Faden, halt."'],
        levelup=['„Mehr Tote hören mich nun."'],
        low_hp=['„Faden reißt."', '„Bruder — hilf."'],
    ),
    'ranger': dict(
        boss_kill=['„Sauber."', '„Genau."'],
        combat_start=['„Geh."', '„Tannen-Auge."'],
        levelup=['„Der Wald kennt mich tiefer."'],
        low_hp=['„Bogen wird schwer."', '„Wurzel, halt mich."'],
    ),
    'rogue': dict(
        boss_kill=['„Bezahlt."', '„Mahnmal-Marke fällig."'],
        combat_start=['„Geschäft."', '„Hier ist deine Quittung."'],
        levelup=['„Mehr Sterne auf der Lizenz."'],
        low_hp=['„Lizenz beinahe abgelaufen."', '„Schatten — gleich."'],
    ),
    'huntress': dict(
        boss_kill=['„Treffer!"', '„Saubere Linie."'],
        combat_start=['„Speer!"', '„Zhar-Eth!"'],
        levelup=['„Eine bessere Schwester werde ich."'],
        low_hp=['„Speer wackelt."', '„Schwester, sieh."'],
    ),
    'druid': dict(
        boss_kill=['*Tieflauter*', '„Mein."'],
        combat_start=['*Grollen*', '*Knurren*'],
        levelup=['„Tiefere Wurzel. Stärkere Form."'],
        low_hp=['*Winseln*', '*flaches Knurren*'],
    ),
}


def class_voice_line(cls, event):
    import random as _r
    pool = CLASS_VOICELINES.get(cls, {}).get(event, [])
    if not pool:
        return None
    return _r.choice(pool)


# ============================================================
# DIE SIEBEN ASPEKTE (Lore-Bibel Teil 2) — für Codex
# ============================================================
ASPECTS = [
    dict(name='Kharn',     domain='Form (Erster Atem)',
         color=(200, 170, 110),
         status='Schläft in der Tiefen Ader',
         note='Sein Schnarchen — Erdbeben.'),
    dict(name='Nheyra',    domain='Zeit (Zweiter Atem)',
         color=(180, 200, 240),
         status='Wandelt in den Stunden-Spiegeln',
         note='Wird in Träumen gesehen, nie wach.'),
    dict(name='Ousen',     domain='Geist (Dritter Atem)',
         color=(140, 180, 230),
         status='Zersplittert in tausend Augen',
         note='Sieht überall — kann nicht mehr handeln.'),
    dict(name='Valsa',     domain='Wille (Vierter Atem)',
         color=(255, 120,  60),
         status='Gefallen — ihr Körper sind die Aschenfelder',
         note='Ihre Asche brennt ohne Brennstoff.'),
    dict(name='Im-Nesh',   domain='Sprache (Fünfter Atem)',
         color=( 80,  60,  90),
         status='Verräter — Antagonist',
         note='Falsche Übersetzung des Ur-Pakts.'),
    dict(name='Shulavh',   domain='Bindung (Sechster Atem)',
         color=(180,  80, 120),
         status='Wahnsinnig im Wurzelgrab',
         note='Jeder gerissene Faden schmerzt sie.'),
    dict(name='Der Siebte', domain='Vergessen (Siebter Atem)',
         color=( 40,  30,  50),
         status='Namenlos. Wacht langsam auf.',
         note='Tut nur, was Aithein vorgesehen hat.'),
]
