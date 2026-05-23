"""Biome ↔ Velgrad-Akt/Region-Mapping.

Lore-Quelle: VELGRAD_LORE_BIBEL.md Teil 4 (Geographie) +
VELGRAD_BESTIARIUM.md (Mobs pro Akt) +
VELGRAD_VOICE_LINES_POOL.md (NPCs).

Dieses Modul ist die zentrale Stelle, an der Engine-Biome-Keys
(crypt/frost/lava/desert/swamp/astral/town) zu In-World-Regionen werden.
HUD, Minimap, Music und Spawn-Pools können das nutzen, ohne sich
selbst um Lore-Mapping zu kümmern.
"""


# ============================================================
# REGIONS-REGISTRY
# ============================================================
# Pro Biome:
#   akt           — Akt-Nummer (1–7), 0 = Hub/Stadt
#   region_name   — In-World-Name (z.B. „Die Salzküste")
#   hub_town      — Hub-Name (z.B. „Brassweir" für Akt 1)
#   faction       — vorherrschende Fraktion in der Region
#   aspect        — verbundener Aspekt (Lore-Bibel Teil 2)
#   short_desc    — Ein-Satz-Atmosphäre für Hover/Tooltip
#   accent_color  — Lore-passende Akzent-Farbe (für HUD/Minimap-Rahmen)

REGIONS = {
    'town': dict(
        akt=0,
        region_name='Brassweir',
        hub_town='Brassweir',
        faction='Mahnmal-Gilde',
        aspect='—',
        short_desc='Halb in Salz versunkene Hafenstadt. Letzter Vorposten.',
        accent_color=(220, 180, 110),
    ),
    'crypt': dict(
        akt=1,
        region_name='Die Salzküste',
        hub_town='Brassweir',
        faction='Mahnmal-Gilde',
        aspect='Nheyra (verfallen)',
        short_desc='Verfallene Hafenstädte. Salzgekreuzte Dörfer. '
                   'Hier liegt die Salzwunde.',
        accent_color=(180, 200, 220),
    ),
    'frost': dict(
        akt=2,
        region_name='Die Glasgoldenen Ruinen',
        hub_town='Echo-Markt',
        faction='Echo-Senatoren',
        aspect='Nheyra',
        short_desc='Glas-Türme, die noch stehen, aber nicht stehen sollten. '
                   'Goldstaub. Stille zwischen Worten.',
        accent_color=(220, 200, 100),
    ),
    'lava': dict(
        akt=3,
        region_name='Die Aschenfelder',
        hub_town='Säulen-von-Helst',
        faction='Tribunal der Asche',
        aspect='Valsa (gefallen)',
        short_desc='Wo Valsa fiel. Schwarzer Schnee aus Asche, ferne Schreie. '
                   'Inquisitoren-Sekte bewohnt.',
        accent_color=(255, 140, 60),
    ),
    'swamp': dict(
        akt=4,
        region_name='Das Wurzelgrab',
        hub_town='Knoten-Markt',
        faction='Knochenwitwen',
        aspect='Shulavh',
        short_desc='Toter Weltenbaum unter der Erde. Wurzelgänge. '
                   'Organisch, beklemmend, sehr falsch.',
        accent_color=(120, 200, 120),
    ),
    'desert': dict(
        akt=1,  # Akt-1-Bonus-Gebiet: Zhar-Eth Speerschwestern-Karawane
        region_name='Zhar-Eth',
        hub_town='Zhar-Eth',
        faction='Speerschwestern',
        aspect='Shulavh',
        short_desc='Wandernde Karawanen-Stadt der Speerschwestern. '
                   'Wüstenstein-Reliefs, Mond-Glyphen.',
        accent_color=(240, 200, 100),
    ),
    'astral': dict(
        akt=5,
        region_name='Die Spiegelstadt Velharn',
        hub_town='Spiegelhof',
        faction='Geist-Senatoren',
        aspect='Nheyra (zeitgefangen)',
        short_desc='Die alte Hauptstadt, gefangen in den Stunden-Spiegeln. '
                   'Eine Stunde drinnen ist drei draußen.',
        accent_color=(200, 180, 240),
    ),
    # ============================================================
    # AKT 6 — DIE DREI WUNDEN (Update #112)
    # Lore-Bibel Teil 4.1 + 10.6: Drei bleibende Wunden Velgrads.
    # Sie teilen einen gemeinsamen Hub („Drei-Wunden-Lager").
    # Engine-Biome-Keys neu, werden zunächst gegen bestehende Biomes
    # gefaltet (siehe `FALLBACK_BIOME` unten) bis dedizierte Biome-Render-
    # Pipelines existieren.
    # ============================================================
    'wound_salt': dict(
        akt=6,
        region_name='Die Salzwunde',
        hub_town='Drei-Wunden-Lager',
        faction='Drei Mütter (Wache)',
        aspect='Nheyra (verfallen)',
        short_desc='Eine Wunde, die Velgrad nie heilt. Salz weint aus den '
                   'Felsen. Wer hier zu lange bleibt, vergisst seinen Namen.',
        accent_color=(150, 200, 230),
    ),
    'wound_ash': dict(
        akt=6,
        region_name='Die Aschwunde',
        hub_town='Drei-Wunden-Lager',
        faction='Tribunal (Reste)',
        aspect='Valsa (gefallen)',
        short_desc='Wo Valsa ihren letzten Atem ließ. Die Asche brennt '
                   'immer noch. Niemand kann sie löschen.',
        accent_color=(255, 110, 50),
    ),
    'wound_hollow': dict(
        akt=6,
        region_name='Die Hohlwunde',
        hub_town='Drei-Wunden-Lager',
        faction='—',
        aspect='Der Siebte',
        short_desc='Eine Stelle, an der nichts ist. Wirklich nichts. Der '
                   'Mut zu schauen kostet einen Atemzug.',
        accent_color=(80, 60, 100),
    ),
    # ============================================================
    # AKT 7 — HOHLWORT (Update #112)
    # Final-Akt. Im-Nesh, Drei Mütter, drei Endings.
    # ============================================================
    'hollow_word': dict(
        akt=7,
        region_name='Hohlwort',
        hub_town='Drei Mütter',
        faction='Drei Mütter',
        aspect='Im-Nesh / Aithein',
        short_desc='Ein Ort jenseits der Sprache. Die Drei Mütter warten '
                   'auf das letzte Wort. Hier endet die Welt — oder fängt '
                   'neu an.',
        accent_color=(220, 200, 255),
    ),
}


# ============================================================
# FALLBACK-BIOME-MAPPING (Update #112)
# ============================================================
# Bis die neuen Akt-6/7-Biomes eigene Dungeon-Renderer haben, falten wir
# sie engine-seitig auf den nächst-verwandten existierenden Biome-Key.
# Verwendung: Dungeon-Generator nutzt FALLBACK_BIOME[biome_key], wenn der
# echte Renderer fehlt. Region-Label/Accent/Lore bleiben original.
FALLBACK_BIOME = {
    'wound_salt':   'crypt',     # Salzkrypta-Optik passt zur Salzwunde
    'wound_ash':    'lava',      # Aschenfelder-Renderer
    'wound_hollow': 'astral',    # Astral-Look für „nichts ist da"
    'hollow_word':  'astral',    # Final-Akt: lavendel/Stundenspiegel-Look
}


def fallback_biome(biome):
    """Falls `biome` ein Akt-6/7-Key ist, returnt den nächst-fallback-
    Renderer-Key. Sonst gibt es `biome` 1:1 zurück."""
    return FALLBACK_BIOME.get(biome, biome)


def region_for_biome(biome):
    """Returnt das Region-Dict für ein Engine-Biome. None wenn unbekannt."""
    return REGIONS.get(biome)


def region_label(biome):
    """Kurz-Label für HUD: ‚Akt N — <Region-Name>'."""
    r = REGIONS.get(biome)
    if r is None:
        return ''
    akt = r.get('akt', 0)
    name = r.get('region_name', biome)
    if akt == 0:
        return name  # Stadt
    return f'Akt {akt} — {name}'


def region_accent(biome, fallback=(200, 200, 200)):
    r = REGIONS.get(biome)
    return r.get('accent_color', fallback) if r else fallback
