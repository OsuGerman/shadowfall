"""Vorposten-Camps für Akt 1b/2/3/4/5/6/7 (WELT_AUFBAU.md Sektion 1.1 + 2).

Brassweir (Akt 1) bleibt der Persistenz-Hub mit Stash, Memorial, Crafting.
Pro weitere Akt: eigenes kleines Camp mit 3-5 NPCs aus dem Lore-Roster.
Diese werden über Akt-Portale aus Brassweir erreicht (Future-Wire-Up).

Architektur:
  - `NPC_ROSTER`: Master-Datenbank aller 22 neuen Lore-NPCs aus dem
    WELT_AUFBAU.md Roster (Sektion 2.2-2.8) + die Brassweir-Stamm-NPCs
    als Re-Export.
  - `OUTPOSTS`: pro Akt-Camp ein Dict mit Position-Layout, NPC-Liste,
    Lore-Tafeln, Ambient-Pool, Tier-Gate.
  - `build_outpost_npcs(key)`: Factory die NPC-Instanzen aus dem Roster
    für ein bestimmtes Outpost erzeugt.

Lore-Anker:
  - [WELT_AUFBAU.md](WELT_AUFBAU.md) Sektion 2 (NPC-Roster)
  - [VELGRAD_VOICE_LINES_POOL.md](VELGRAD_VOICE_LINES_POOL.md) (NPC-Voices)
  - [VELGRAD_LORE_BIBEL.md](VELGRAD_LORE_BIBEL.md) Teil 6 (Fraktionen)

Wire-Up-Schritte (zukünftig, nicht Teil von Update #112):
  - Akt-Portale in Brassweir spawnen pro freigeschaltetem Akt
  - `game.enter_outpost(key)` schaltet Town-Layout um
  - Quest-System lädt Outpost-NPCs als Quest-Giver
"""

import math

from .entities import NPC, Decor, OutpostPortal, DungeonPortal


# ============================================================
# NPC-ROSTER (WELT_AUFBAU 2.2 - 2.8)
# ============================================================
# Felder pro Eintrag:
#   name        — Display-Name (Lore-konform)
#   role        — Engine-Rolle: 'vendor' | 'stash' | 'mystic' |
#                 'smith' | 'quest' | 'innkeeper'
#   color       — Sprite-Akzent-Farbe (Lore-Faction-getönt)
#   faction     — Lore-Fraktion ([VELGRAD_LORE_BIBEL.md] Teil 6)
#   outpost     — Outpost-Key (siehe OUTPOSTS unten)
#   x, y        — Default-Position im Outpost-Layout (relativ zu Center)
#   voice_lines — Tuple aus 2–4 Voice-Lines (für Hover/Talk-Modal,
#                 zitiert aus [VELGRAD_VOICE_LINES_POOL.md] wo möglich)

NPC_ROSTER = {
    # ============================================================
    # AKT 1b — ZHAR-ETH-KARAWANE (3 NPCs + Tameris-Wandert-Hier)
    # ============================================================
    'naveth': dict(
        name='Schwester-Kommandantin Naveth',
        role='quest',
        color=(200, 180, 100),
        faction='Speerschwestern',
        outpost='zhar_eth_karawane',
        x=0, y=-60,
        voice_lines=(
            "Die Wüste lehrt drei Dinge: Geduld, Speerwurf, "
            "Schweigen. Du beherrschst keines davon. Noch nicht.",
            "Schwester-Sein ist kein Bündnis. Es ist eine Bindung — "
            "wie Shulavhs Faden, nur weniger grausam.",
        ),
    ),
    'sheh': dict(
        name='Mond-Priesterin Sheh',
        role='mystic',
        color=(180, 200, 240),
        faction='Speerschwestern',
        outpost='zhar_eth_karawane',
        x=-110, y=20,
        voice_lines=(
            "Der Mond wandert. Wir wandern. Das ist kein Zufall.",
            "Shulavh schickte uns Sand-Spinnen. Wir lernten "
            "von ihnen, lautlos zu jagen.",
        ),
    ),
    'yul': dict(
        name='Karawanen-Händlerin Yul',
        role='vendor',
        color=(220, 180, 80),
        faction='Speerschwestern',
        outpost='zhar_eth_karawane',
        x=120, y=20,
        voice_lines=(
            "Glas-Splitter aus Velharn — drei Marken. "
            "Eine Mondbinde — fünf. Eine Geschichte — gratis.",
            "Die Karawane bewegt sich morgen. Du kannst mit. "
            "Oder du bleibst und vergisst, dass es uns gab.",
        ),
    ),

    # ============================================================
    # AKT 2 — ECHO-MARKT (4 NPCs)
    # ============================================================
    'helst': dict(
        name='Bruder Helst der Hundertjährige',
        role='quest',
        color=(160, 140, 100),
        faction='Erblinde Kirche',
        outpost='echo_markt',
        x=0, y=-80,
        voice_lines=(
            "Ich sah Velharn fallen. Dann band ich mir die Augen. "
            "Seitdem sehe ich klarer.",
            "Die Pact-Stones tragen Erinnerungen, die niemand "
            "ausspricht. Aber sie wiegen schwer.",
        ),
    ),
    'vorul': dict(
        name='Senator-Geist Vorul',
        role='vendor',
        color=(220, 200, 140),
        faction='Echo-Senatoren',
        outpost='echo_markt',
        x=120, y=20,
        voice_lines=(
            "Ich verkaufe erinnerte Waren. Sie sind nicht ganz da — "
            "aber sie schneiden trotzdem.",
            "Das war einmal das Lager der Liga. Heute ist es "
            "ein Markt. Beides ist wahr.",
        ),
    ),
    'athrek': dict(
        name='Glasgolden-Schmied Athrek',
        role='smith',
        color=(180, 160, 100),
        faction='Echo-Senatoren',
        outpost='echo_markt',
        x=-110, y=20,
        voice_lines=(
            "Glas und Gold zugleich — die Liga wusste, wie man "
            "das schmilzt. Ich habe es aus Dokumenten gelernt, "
            "die keiner mehr lesen kann.",
            "Otreth hat es mir gezeigt. Er sagt, ich darf nichts "
            "davon weitererzählen. Aber du fragst nicht.",
        ),
    ),
    'salir': dict(
        name='Otreth-Lehrling Salir',
        role='smith',
        color=(170, 110, 60),
        faction='Mahnmal-Gilde',
        outpost='echo_markt',
        x=-110, y=110,
        voice_lines=(
            "Mein Meister Otreth hat mich hier gelassen. Er sagt, "
            "ich lerne nichts, wenn er immer Korrekturen schreit.",
            "Glas-Gravuren sind anders als Mahnmal-Gravuren. "
            "Sie vergessen schneller.",
        ),
    ),

    # ============================================================
    # AKT 3 — SÄULEN-VON-HELST (4 NPCs)
    # ============================================================
    'acolyt_helst': dict(
        name='Acolyt der Erblinden Kirche',
        role='quest',
        color=(140, 120, 90),
        faction='Erblinde Kirche',
        outpost='saeulen_von_helst',
        x=0, y=-80,
        voice_lines=(
            "Bruder Helst schickte mich. Er sagt, du wirst die "
            "Probe bestehen. Oder du wirst sehen, was du nicht "
            "sehen solltest.",
            "Tribunal sagt, wir seien Verräter. Wir sagen: wir "
            "haben nur das Vergessen mitgebracht in die Aschenfelder.",
        ),
    ),
    'korren': dict(
        name='Tribunal-Doppelagent Korren',
        role='mystic',
        color=(180, 100, 80),
        faction='Tribunal der Asche',
        outpost='saeulen_von_helst',
        x=110, y=20,
        voice_lines=(
            "Sprich leise. Vehrens Geist hört noch. Tribunal "
            "weiß noch nicht, dass ich für die Erblinden arbeite. "
            "Lass es so.",
            "Wenn du Korven Vor triffst, frag ihn nach Velharn. "
            "Schau ihm dabei in die Augen.",
        ),
    ),
    'selvor': dict(
        name='Vehren-Gefangener Selvor',
        role='quest',
        color=(120, 90, 70),
        faction='—',
        outpost='saeulen_von_helst',
        x=0, y=80,
        voice_lines=(
            "Ich war Vehrens Hand. Er nahm mich gefangen, als ich "
            "zögerte zu töten. Jetzt warte ich auf eine Wahl, die "
            "niemand mir geben wird.",
            "Vehren war kein Monster. Er war ein Mensch, in den "
            "Valsas Asche reinkroch. Das ist schlimmer.",
        ),
    ),
    'brulm': dict(
        name='Asche-Händler Brulm',
        role='vendor',
        color=(160, 110, 70),
        faction='Tribunal der Asche',
        outpost='saeulen_von_helst',
        x=-110, y=20,
        voice_lines=(
            "Tribunal-Stahl. Heiß geschmiedet, kalt verkauft. "
            "Die Klinge erinnert sich an Valsas Wille.",
            "Du willst Asche-Reliquien? Ich habe drei Sorten — "
            "billig (Lüge), teuer (echt), und unbezahlbar (mein).",
        ),
    ),

    # ============================================================
    # AKT 4 — KNOTEN-MARKT (4 NPCs)
    # ============================================================
    'vossharil': dict(
        name='Vossharil die Dreimalige',
        role='quest',
        color=(100, 60, 90),
        faction='Knochenwitwen',
        outpost='knoten_markt',
        x=0, y=-80,
        voice_lines=(
            "Ich starb dreimal. Beim ersten Mal weinte ich. "
            "Beim zweiten Mal kämpfte ich. Beim dritten Mal "
            "blieb ich. Du wirst lernen, wann du bleibst.",
            "Shulavh ist meine Patin. Sie weiß meinen Namen. Sie "
            "ruft ihn aber nicht mehr — höflich von ihr.",
        ),
    ),
    'bran': dict(
        name='Wurzel-Apotheker Bran',
        role='vendor',
        color=(80, 130, 70),
        faction='Knochenwitwen',
        outpost='knoten_markt',
        x=110, y=20,
        voice_lines=(
            "Wurzel-Tinkturen. Gift, das heilt. Heilkraut, das "
            "tötet. Frag mich, was du brauchst — ich weiß es "
            "schneller als du.",
            "Saatträger lernten viel von uns. Sie geben es nicht "
            "zu. Das ist okay. Wir wissen es trotzdem.",
        ),
    ),
    'marvel': dict(
        name='Knochen-Hexe Marvel',
        role='smith',
        color=(140, 120, 130),
        faction='Knochenwitwen',
        outpost='knoten_markt',
        x=-110, y=20,
        voice_lines=(
            "Knochen-Crafting ist wie Otreths Stein-Arbeit — nur "
            "lebendiger. Diese Knochen erinnern sich.",
            "Wenn dein Schwert spricht, lass es. Antworte nicht. "
            "Knochen sind ungeduldig.",
        ),
    ),
    'hohler_sohn_npc': dict(
        name='Hohler Sohn',
        role='mystic',
        color=(90, 85, 95),
        faction='Knochenwitwen',
        outpost='knoten_markt',
        x=0, y=80,
        voice_lines=(
            "…",   # er schweigt — Quests via Gesten
            "…",
        ),
    ),

    # ============================================================
    # AKT 5 — SPIEGELHOF (4 NPCs)
    # ============================================================
    'voraius': dict(
        name='Erster Senator Voraius',
        role='quest',
        color=(220, 200, 160),
        faction='Echo-Senatoren',
        outpost='spiegelhof',
        x=0, y=-80,
        voice_lines=(
            "Ich war der Erste der 412. Heute bin ich der Letzte, "
            "der noch spricht. Die anderen hören nur noch.",
            "Drei Zeiten. Glasgolden, Götterkrieg, Gegenwart. "
            "Du musst durch alle drei. Wähle nicht falsch.",
        ),
    ),
    'nheya': dict(
        name='Spiegel-Magierin Nheya',
        role='mystic',
        color=(200, 180, 240),
        faction='Echo-Senatoren',
        outpost='spiegelhof',
        x=110, y=20,
        voice_lines=(
            "Eine Stunde drinnen ist drei draußen. Eine Stunde "
            "draußen ist… länger drinnen. Beides ist wahr.",
            "Mein Name ist Nheya. Nicht Nheyra. Ich bekam ihn "
            "von einer Mutter, die sich verschrieb.",
        ),
    ),
    'sehir': dict(
        name='Glasgolden-Händlerin Sehir',
        role='vendor',
        color=(220, 200, 130),
        faction='Echo-Senatoren',
        outpost='spiegelhof',
        x=-110, y=20,
        voice_lines=(
            "Reflektierte Klingen. Sie schneiden, was du dachtest, "
            "schon vergessen zu haben.",
            "Wenn du nicht zahlen kannst — du erinnerst dich an "
            "etwas, das du nie hattest. Das ist auch Währung.",
        ),
    ),
    'mara_velharn': dict(
        name='Mara die Mahnerin (Reveal-Stage)',
        role='quest',
        color=(160, 80, 200),
        faction='Mahnmal-Gilde',
        outpost='spiegelhof',
        x=-30, y=80,
        voice_lines=(
            "Du erinnerst dich an mich aus Brassweir. Ich war "
            "dieselbe — und doch eine andere. Hier in Velharn "
            "bin ich beides.",
            "Frag mich, wer Im-Nesh ist. Ich kann antworten. "
            "Ob du die Antwort hören willst, ist eine andere "
            "Frage.",
        ),
    ),

    # ============================================================
    # AKT 6 — DREI-WUNDEN-LAGER (3 NPCs)
    # ============================================================
    'mara_wunden': dict(
        name='Mara die Mahnerin (Akt-6-Stage)',
        role='quest',
        color=(140, 70, 180),
        faction='Mahnmal-Gilde',
        outpost='drei_wunden_lager',
        x=0, y=-60,
        voice_lines=(
            "Drei Wunden. Drei Aspekte. Du wirst alle drei "
            "Schmerz lesen. Dann wirst du wählen.",
            "Ich habe dich hierher geführt, weil außer mir "
            "niemand den Weg kennt. Das ist nicht stolz — "
            "das ist Pflicht.",
        ),
    ),
    'korven_helst_reveal': dict(
        name='Korven Vor ODER Helst',     # Choice-Outcome
        role='mystic',
        color=(180, 130, 80),
        faction='—',
        outpost='drei_wunden_lager',
        x=120, y=20,
        voice_lines=(
            "Du dachtest, du kennst mich. Du kennst meine Maske. "
            "In den Wunden trage ich keine Maske mehr.",
            "Im-Nesh sprach durch mich. Er spricht durch mich. "
            "Er wird durch mich sprechen, wenn er fertig ist.",
        ),
    ),
    'tehrnal': dict(
        name='Wunden-Lesende Tehrnal',
        role='quest',
        color=(160, 110, 90),
        faction='Drei Mütter',
        outpost='drei_wunden_lager',
        x=-110, y=20,
        voice_lines=(
            "Der Pakt steht in einer Sprache, die nur die Drei "
            "Mütter sprechen. Ich kann ihn dir nur in Bildern "
            "geben.",
            "Du hast bereits drei Worte verstanden. Drei Worte "
            "mehr und du wirst Aithein hören.",
        ),
    ),

    # ============================================================
    # AKT 7 — HOHLWORT (3 NPCs)
    # ============================================================
    'drei_muetter': dict(
        name='Die Drei Mütter',
        role='mystic',
        color=(220, 200, 255),
        faction='Drei Mütter',
        outpost='hohlwort',
        x=0, y=-60,
        voice_lines=(
            "Wir sind drei. Wir sind eine. Wir sind, was "
            "übrig blieb, als die Sprache erschöpft war.",
            "Du hast drei Trials. Drei Wege. Drei Worte. Wenn "
            "du sie aussprichst, beginnt Aithein zu hören.",
        ),
    ),
    'mara_final': dict(
        name='Mara die Mahnerin (Final-Stage)',
        role='quest',
        color=(120, 60, 160),
        faction='Mahnmal-Gilde',
        outpost='hohlwort',
        x=-110, y=20,
        voice_lines=(
            "Das ist mein letztes Auftauchen. Du wirst mich "
            "nicht mehr brauchen — oder ich werde nicht mehr "
            "sein.",
            "Drei Endings warten. Wähle nicht aus Stolz. Wähle "
            "nicht aus Angst. Wähle, weil du es musst.",
        ),
    ),
    'im_nesh_echo_npc': dict(
        name="Im-Neshs Echo",
        role='mystic',
        color=(180, 160, 200),
        faction='—',
        outpost='hohlwort',
        x=110, y=20,
        voice_lines=(
            "Du hast mich getroffen, bevor du dachtest, mich zu "
            "treffen. Korven, Helst, Mara — jeder von ihnen war "
            "auch ein bisschen ich.",
            "Sprich mit mir, bevor du kämpfst. Vielleicht musst "
            "du nicht kämpfen. Vielleicht doch.",
        ),
    ),
}


# ============================================================
# OUTPOSTS-REGISTRY (WELT_AUFBAU 1.2 + 1.3)
# ============================================================
# Pro Eintrag:
#   region_name  — In-World-Lore-Name (übernimmt regions.REGIONS)
#   biome_key    — Engine-Biome (Render-Pipeline-Key)
#   akt          — Akt-Nummer für Tier-Gating
#   tier_gate    — Min-Akt-Progress um Vorposten zu betreten (Future-Wire)
#   npcs         — Liste der NPC_ROSTER-Keys (3-5 pro Camp)
#   ambient_pool — Welcher Ambient-Sound-Pool (siehe sounds.BIOME_AMBIENT_POOL)
#   short_desc   — 1-Liner für UI-Tooltip
#   color        — Hub-Akzent-Farbe
#   has_stash    — Bool: Stash-Service vorhanden? (False außer Brassweir)
#   has_crafting — Bool: Crafting-Modal verfügbar?

OUTPOSTS = {
    # Brassweir bleibt der Persistenz-Hub — hier nur zum Vollständigkeits-
    # Lookup. Town-Layout liegt weiter in town.py.
    'brassweir': dict(
        region_name='Brassweir',
        biome_key='town',
        akt=1,
        tier_gate=0,
        npcs=[],   # bleiben in town.py hardcoded; nicht roster-driven
        ambient_pool='town',
        short_desc='Halb-versunkene Hafenstadt. Letzter Vorposten der '
                   'Mahnmal-Gilde.',
        color=(220, 180, 110),
        has_stash=True,
        has_crafting=True,
    ),

    'zhar_eth_karawane': dict(
        region_name='Zhar-Eth-Karawane',
        biome_key='desert',
        akt=1,                     # Akt 1b — optional
        tier_gate=1,
        npcs=['naveth', 'sheh', 'yul'],
        ambient_pool='desert',
        short_desc='Wanderende Karawanen-Stadt der Speerschwestern. '
                   'Mondglyphen, Sand, ferne Trommeln.',
        color=(240, 200, 100),
        has_stash=False,
        has_crafting=False,
        dungeon_id='desert_temple',     # Update #115
    ),

    'echo_markt': dict(
        region_name='Echo-Markt',
        biome_key='frost',          # WELT_AUFBAU 1.2: glass_ruins-Rename
        akt=2,
        tier_gate=2,
        npcs=['helst', 'vorul', 'athrek', 'salir'],
        ambient_pool='frost',
        short_desc='Markt zwischen den Glasgoldenen Ruinen. Senatoren-'
                   'Geister handeln mit „erinnerten Waren".',
        color=(220, 200, 140),
        has_stash=False,
        has_crafting=True,           # Athrek + Salir
        dungeon_id='frost_palace',      # Update #115 (Engine-Key)
    ),

    'saeulen_von_helst': dict(
        region_name='Säulen-von-Helst',
        biome_key='lava',
        akt=3,
        tier_gate=3,
        npcs=['acolyt_helst', 'korren', 'selvor', 'brulm'],
        ambient_pool='lava',
        short_desc='Steinerne Säulen-Hain auf den Aschenfeldern. '
                   'Erblinde-Außenposten und Tribunal-Spitzel.',
        color=(180, 100, 70),
        has_stash=False,
        has_crafting=False,
        dungeon_id='lava_pit',          # Update #115
    ),

    'knoten_markt': dict(
        region_name='Knoten-Markt',
        biome_key='swamp',
        akt=4,
        tier_gate=4,
        npcs=['vossharil', 'bran', 'marvel', 'hohler_sohn_npc'],
        ambient_pool='swamp',
        short_desc='Wurzelgrab-Markt der Knochenwitwen. Vossharil führt. '
                   'Hohler Sohn schweigt.',
        color=(100, 130, 90),
        has_stash=False,
        has_crafting=True,           # Marvel (Knochen)
        dungeon_id='swamp_ruins',       # Update #115
    ),

    'spiegelhof': dict(
        region_name='Spiegelhof',
        biome_key='astral',
        akt=5,
        tier_gate=5,
        npcs=['voraius', 'nheya', 'sehir', 'mara_velharn'],
        ambient_pool='astral',
        short_desc='Spiegel-Hof in der Spiegelstadt Velharn. Drei-Zeiten-'
                   'Hauptquest beginnt hier.',
        color=(200, 180, 240),
        has_stash=False,
        has_crafting=False,
        dungeon_id='astral_realm',      # Update #115
    ),

    'drei_wunden_lager': dict(
        region_name='Drei-Wunden-Lager',
        biome_key='wound_salt',      # Lager liegt an der Salzwunde
        akt=6,
        tier_gate=6,
        npcs=['mara_wunden', 'korven_helst_reveal', 'tehrnal'],
        ambient_pool='crypt',        # Salz-Fallback
        short_desc='Drei-Wunden-Forschungslager. Mara führt. Korven oder '
                   'Helst zeigt sein wahres Gesicht.',
        color=(150, 200, 230),
        has_stash=False,
        has_crafting=False,
        # Update #115: Drei-Wunden-Lager hat einen Salzwunden-Crypt-Portal,
        # der bei Tier ≥ 3 auf Ertrunkene-Königin route-t (siehe
        # Game._spawn_dungeon_boss tier-routing).
        dungeon_id='crypt_lost',
    ),

    'hohlwort': dict(
        region_name='Hohlwort',
        biome_key='hollow_word',
        akt=7,
        tier_gate=7,
        npcs=['drei_muetter', 'mara_final', 'im_nesh_echo_npc'],
        ambient_pool='astral',       # bis hollow_word-Renderer existiert
        short_desc='Jenseits der Sprache. Drei Mütter, Mara ein letztes '
                   'Mal, und Im-Neshs Echo.',
        color=(220, 200, 255),
        has_stash=False,
        has_crafting=False,
        # Update #115: Akt 7 hat keinen regulären Dungeon — der Im-Nesh-Boss
        # ist ein Spezial-Encounter, der direkt aus dem Camp gestartet wird.
        dungeon_id=None,
    ),
}


# ============================================================
# API
# ============================================================

def get_outpost(key):
    """Returnt das Outpost-Dict (oder None)."""
    return OUTPOSTS.get(key)


def list_outposts(min_akt=0, max_akt=99):
    """Returnt Outpost-Keys in Akt-Reihenfolge gefiltert nach Akt-Range."""
    items = [(k, v['akt']) for k, v in OUTPOSTS.items()]
    items.sort(key=lambda kv: kv[1])
    return [k for k, akt in items if min_akt <= akt <= max_akt]


def outpost_for_biome(biome):
    """Returnt das Outpost-Key, dessen biome_key matched. None wenn keiner.

    Beachte: ein Biome kann mehrere Outposts haben (z.B. wound_salt für
    drei_wunden_lager); wir geben den ersten Match nach Akt-Reihenfolge.
    """
    matches = [(k, v) for k, v in OUTPOSTS.items() if v['biome_key'] == biome]
    if not matches:
        return None
    matches.sort(key=lambda kv: kv[1]['akt'])
    return matches[0][0]


def build_outpost_npcs(key):
    """Factory: returnt eine Liste von NPC-Instanzen für ein Outpost.

    Verwendet die Default-Positionen aus NPC_ROSTER. Wird in zukünftigen
    `Game.enter_outpost(key)` aufgerufen, um die Town-Szene zu befüllen.
    """
    cfg = OUTPOSTS.get(key)
    if cfg is None:
        return []
    out = []
    for npc_key in cfg['npcs']:
        spec = NPC_ROSTER.get(npc_key)
        if spec is None:
            continue
        npc = NPC(spec['x'], spec['y'], spec['role'], spec['name'],
                  spec['color'])
        # Lore-Metadaten am Instance hängen lassen, damit Hover/Talk-UI
        # darauf zugreifen kann.
        npc.faction = spec['faction']
        npc.outpost = key
        npc.voice_lines = spec['voice_lines']
        npc.roster_key = npc_key
        out.append(npc)
    return out


def get_npc_voice(npc_key, index=0):
    """Returnt eine Voice-Line aus dem Roster. index modulo verfügbare."""
    spec = NPC_ROSTER.get(npc_key)
    if spec is None or not spec.get('voice_lines'):
        return None
    lines = spec['voice_lines']
    return lines[index % len(lines)]


def total_npc_count():
    """Sanity-Check-Helper."""
    return len(NPC_ROSTER)


# ============================================================
# LAYOUT-GENERATOREN (Update #113)
# ============================================================
# Pro Outpost: Lore-fitting Decor-Cluster + NPCs + Return-Portal nach
# Brassweir. Layout ist klein (~ 400×400 weltspace), kein Mauerring —
# Camps statt voller Städte.

# Pro Outpost-Key: Decor-Liste (kind, x, y, optional size/rot/collide).
_OUTPOST_DECOR = {
    # ---- AKT 1b — Zhar-Eth-Karawane (desert) ----
    # Wanderzelt-Markt. Mond-Glyphen-Stelen, Trommeln (= barrel als Stand-In),
    # Lager-Kisten, Mahnmal-Stele am Eingang.
    'zhar_eth_karawane': [
        ('mahnmal_stele', 0, 200, 50),
        ('market_stall', 120, 60, 60),
        ('market_stall', -130, 60, 60),
        ('barrel', 80, -120, None),
        ('barrel', -70, -90, None),
        ('crate', 160, -80, None),
        ('crate', -160, -100, None),
        ('lantern', 60, -200, None),
        ('lantern', -60, -200, None),
        ('rock', 200, 150, None),
        ('rock', -200, 150, None),
    ],
    # ---- AKT 2 — Echo-Markt (frost) ----
    # Glas-Reliquien-Markt unter den Glasgoldenen Ruinen.
    # Bookshelf = Senatoren-Akten, frozen_pillar = Ruinensäulen.
    'echo_markt': [
        ('mahnmal_stele', 0, 200, 50),
        ('market_stall', 100, 80, 60),
        ('market_stall', -130, 80, 60),
        ('frozen_pillar', 180, -80, 60),
        ('frozen_pillar', -180, -80, 60),
        ('bookshelf', 80, -180, None),
        ('bookshelf', -90, -180, None),
        ('crystal', 0, -240, None),
        ('lantern', 50, 30, None),
        ('lantern', -50, 30, None),
        ('crate', 160, 0, None),
        ('crate', -160, 0, None),
    ],
    # ---- AKT 3 — Säulen-von-Helst (lava) ----
    # Erblinde-Hain auf den Aschenfeldern. Pillars als Säulen,
    # lava_pool für Atmosphäre, mahnmal_stele für die Kirche.
    'saeulen_von_helst': [
        ('mahnmal_stele', 0, 200, 50),
        ('pillar', 140, 50, 70),
        ('pillar', -140, 50, 70),
        ('pillar', 140, -120, 70),
        ('pillar', -140, -120, 70),
        ('lava_pool', 80, -180, None),
        ('lava_pool', -90, -180, None),
        ('statue', 0, -80, None),
        ('crate', 200, 0, None),
        ('crate', -200, 0, None),
        ('lantern', 70, 80, None),
        ('lantern', -70, 80, None),
    ],
    # ---- AKT 4 — Knoten-Markt (swamp) ----
    # Wurzelgrab-Lager der Knochenwitwen.
    'knoten_markt': [
        ('mahnmal_stele', 0, 200, 50),
        ('mushroom', 110, 50, None),
        ('mushroom', -130, 60, None),
        ('mushroom', 60, -120, None),
        ('mushroom', -80, -130, None),
        ('gravestone', 150, -50, None),
        ('gravestone', -150, -50, None),
        ('market_stall', 100, -200, 60),
        ('market_stall', -110, -200, 60),
        ('crystal', 0, -260, None),
        ('lantern', 50, 30, None),
        ('lantern', -50, 30, None),
        ('bone', 180, 100, None),
        ('bone', -180, 100, None),
    ],
    # ---- AKT 5 — Spiegelhof (astral) ----
    # Stundenspiegel-Hof in Velharn.
    'spiegelhof': [
        ('mahnmal_stele', 0, 200, 50),
        ('fountain', 0, 0, None),
        ('crystal', 130, -100, None),
        ('crystal', -130, -100, None),
        ('crystal', 130, 100, None),
        ('crystal', -130, 100, None),
        ('statue', 0, -200, None),
        ('rune_anchor', 80, -50, None),
        ('rune_anchor', -80, -50, None),
        ('lantern', 60, 130, None),
        ('lantern', -60, 130, None),
    ],
    # ---- AKT 6 — Drei-Wunden-Lager (wound_salt) ----
    # Provisorisches Lager auf der Salzwunde-Spitze.
    'drei_wunden_lager': [
        ('salt_statue', 0, -200, 70),         # Wunden-Anker
        ('salt_crystal', 100, -120, None),
        ('salt_crystal', -100, -120, None),
        ('salt_crystal', 130, 80, None),
        ('salt_crystal', -130, 80, None),
        ('crate', 80, 60, None),
        ('crate', -80, 60, None),
        ('lore_tablet', 60, -50, 50),
        ('lore_tablet', -60, -50, 50),
        ('lantern', 40, 130, None),
        ('lantern', -40, 130, None),
    ],
    # ---- AKT 7 — Hohlwort (hollow_word) ----
    # Final-Akt. Drei Mütter erwarten den Spieler in stiller Halle.
    'hohlwort': [
        ('rune_anchor', 0, -180, 80),
        ('crystal', 130, -100, None),
        ('crystal', -130, -100, None),
        ('crystal', 0, -80, None),
        ('statue', 100, 50, None),
        ('statue', -100, 50, None),
        ('mahnmal_stele', 0, 180, 50),
        ('lantern', 70, 130, None),
        ('lantern', -70, 130, None),
    ],
}


def generate_outpost(outpost_key):
    """Layout-Generator für einen Vorposten.

    Returnt (tiles, npcs, return_portal, dungeon_portal):
      - tiles: Decor-Liste (entitäten-fähig)
      - npcs:  NPC-Instanzen aus build_outpost_npcs()
      - return_portal: OutpostPortal zurück nach Brassweir (südlich)
      - dungeon_portal: DungeonPortal zum lore-passenden Akt-Dungeon
                        (nördlich); None wenn der Outpost keinen
                        regulären Dungeon hat (z.B. Hohlwort).

    Layout-Konvention (WELT_AUFBAU 1.3):
        Nord  → Dungeon-Portal
        Mitte → Decor + NPCs
        Süd   → Return-Portal nach Brassweir
    """
    cfg = OUTPOSTS.get(outpost_key)
    if cfg is None:
        raise KeyError(f"Unknown outpost: {outpost_key}")

    tiles = []

    # Path-Tiles als gehbarer Untergrund (Kreuz-Pattern)
    for y in range(-260, 260, 40):
        tiles.append(Decor(0, y, 'path_tile'))
    for x in range(-260, 260, 40):
        tiles.append(Decor(x, 0, 'path_tile'))
    # Path-Verlängerungen nach Norden (zum Dungeon-Portal) + Süden
    # (zum Return-Portal). Player kann nicht „in der Luft" laufen,
    # also brauchen wir Pfade dorthin.
    for y in range(-460, -260, 40):
        tiles.append(Decor(0, y, 'path_tile'))
    for y in range(260, 420, 40):
        tiles.append(Decor(0, y, 'path_tile'))

    # Lore-fitting Decor-Cluster
    for entry in _OUTPOST_DECOR.get(outpost_key, ()):
        kind = entry[0]
        x, y = entry[1], entry[2]
        size = entry[3] if len(entry) > 3 and entry[3] is not None else 60
        # Collide für solid Decor (pillar/statue/mahnmal_stele), nicht für
        # path_tile/lantern.
        collide = 14 if kind in ('pillar', 'frozen_pillar', 'statue',
                                  'mahnmal_stele', 'salt_statue',
                                  'fountain', 'rune_anchor',
                                  'bookshelf', 'market_stall',
                                  'gravestone', 'crystal',
                                  'crate', 'barrel') else 0
        tiles.append(Decor(x, y, kind, 0.0, size, 0.1, collide))

    # NPCs
    npcs = build_outpost_npcs(outpost_key)

    # Return-Portal nach Brassweir (südlich, am Camp-Rand)
    return_portal = OutpostPortal(0, 380, 'brassweir',
                                   label='Zurück nach Brassweir')

    # Update #115: Dungeon-Portal nördlich (Vorposten → Akt-Dungeon).
    dungeon_id = cfg.get('dungeon_id')
    dungeon_portal = None
    if dungeon_id:
        dungeon_portal = DungeonPortal(0, -440, dungeon_id)

    return tiles, npcs, return_portal, dungeon_portal


# ============================================================
# AKT-PROGRESS-GATING
# ============================================================

def unlocked_outposts(player):
    """Returnt die Liste der Outpost-Keys, die für den Player verfügbar sind.

    Aktuelle Heuristik: `tier_gate` ≤ Anzahl abgeschlossener Dungeons
    (= Akt-Progress). Sobald Quest-System steht, wird dies durch
    explizite Quest-Flags ersetzt.
    """
    akt_progress = len(getattr(player, 'completed_dungeons', ()))
    return [k for k, v in OUTPOSTS.items()
            if k != 'brassweir' and v['tier_gate'] <= akt_progress + 1]
