"""POE2-style Skill-Atlas — Update #184 / Phase 1 (Moench).

Ersetzt den flachen Grid-Tree durch einen verbundenen Node-Graph mit
Klassen-Start-Zonen, gemeinsamer Mitte und gameplay-veraendernden
Keystones. Aktuell vollstaendig fuer Moench; andere 7 Klassen haben
Start-Stubs die in spaeteren Phasen ausgebaut werden.

Daten-Modell:
- ATLAS_NODES: dict[str, NodeDef] mit pos, kind, stats, effects, class_
- ATLAS_EDGES: list[tuple[str, str]] symmetrische Verbindungen
- CLASS_STARTS: dict[class_key, root_node_id]

Allocation-Regel: Ein Knoten ist allokierbar wenn
  (a) er der Klassen-Start ist (gratis, immer allokiert),
  (b) ein Nachbar ueber ATLAS_EDGES bereits allokiert ist,
  (c) er entweder neutral (class_=None) oder genau zur Klasse passt,
  (d) der Spieler einen Atlas-Punkt hat.

Stats werden additiv aus allen allokierten Nodes summiert.
Keystone-Effekte sind String-IDs in node['effects'], die von
skills.py / combat.py / progression.py via `has_keystone(player, id)`
abgefragt werden.
"""

from __future__ import annotations

# ============================================================
# Node-Kinds
# ============================================================
SMALL    = 'small'      # +1 Atlas-Punkt, kleiner Stat
NOTABLE  = 'notable'    # +1 Atlas-Punkt, groesserer Stat / kleiner Effekt
KEYSTONE = 'keystone'   # +1 Atlas-Punkt, Gameplay-aenderung (radikal)
START    = 'classstart' # Klassen-Start, gratis, immer allokiert
GATEWAY  = 'gateway'    # Verbindung zwischen Klassen-Zone und Shared-Core

# Visual radii (used by UI)
KIND_RADIUS = {
    SMALL:    7,
    NOTABLE:  12,
    KEYSTONE: 18,
    START:    22,
    GATEWAY:  10,
}

# Canvas-Konventionen
ATLAS_W = 2400
ATLAS_H = 2000
ATLAS_CENTER = (1200, 1000)


# ============================================================
# Helper-Funktionen fuer Cluster-Layouts
# ============================================================
def _cluster(center, items, radius=60, start_angle=0.0):
    """Verteilt items radial um center. Returnt list[(id, x, y)]."""
    import math
    cx, cy = center
    out = []
    n = len(items)
    if n == 1:
        out.append((items[0], cx, cy))
        return out
    for i, key in enumerate(items):
        ang = start_angle + (i / n) * math.tau
        x = cx + math.cos(ang) * radius
        y = cy + math.sin(ang) * radius
        out.append((key, x, y))
    return out


# ============================================================
# NODE-DEFINITIONS — Moench (vollstaendig)
# ============================================================
# Layout-Plan:
#   Class-Start oben-rechts bei (1700, 600).
#   Drei Pfade fahren raus:
#     - STURM (Storm/Lightning) → nach oben/rechts
#     - BAMBUS (Melee/Speed)    → nach rechts
#     - SCHATTEN (Cold/Crit)    → nach unten/rechts
#   Jeder Pfad endet in 2 Keystones.
#   Inner-Side gehen Gateways nach Shared-Core (Mitte).

_MONK_START = (1700, 1000)

ATLAS_NODES = {}
ATLAS_EDGES = []


def _add(node_id, kind, pos, name, desc, class_=None, stats=None,
         effects=None):
    """Helper: registriert einen Node."""
    ATLAS_NODES[node_id] = {
        'id': node_id,
        'kind': kind,
        'pos': pos,
        'name': name,
        'desc': desc,
        'class_': class_,
        'stats': stats or {},
        'effects': effects or [],
    }


def _link(a, b):
    """Helper: registriert eine ungerichtete Kante."""
    ATLAS_EDGES.append((a, b))


# ----------------------------------------------------------------
# MOENCH-START
# ----------------------------------------------------------------
_add('monk_start', START, _MONK_START,
     'Hand des Bambus',
     'Moench-Eingang in den Erinnerungsbaum. Wandere von hier aus.',
     class_='monk')


# ----------------------------------------------------------------
# MOENCH-PFAD A: STURM (Lightning) — nach oben
# ----------------------------------------------------------------
# Layer 1: 2 Small (Verzweigung)
_add('m_sturm_s1', SMALL, (1740, 920), 'Funke',
     '+6% Blitz-Schaden', class_='monk',
     stats={'lit_dmg_pct': 0.06})
_add('m_sturm_s2', SMALL, (1660, 920), 'Geladene Luft',
     '+4% Krit-Chance bei Blitz-Skills', class_='monk',
     stats={'crit_chance_lightning': 0.04})
_link('monk_start', 'm_sturm_s1')
_link('monk_start', 'm_sturm_s2')

# Layer 2: 2 Small + 1 Notable
_add('m_sturm_s3', SMALL, (1760, 860), 'Gewitterherz',
     '+8% Blitz-Schaden', class_='monk',
     stats={'lit_dmg_pct': 0.08})
_add('m_sturm_s4', SMALL, (1680, 860), 'Knisternder Atem',
     '+5% Skill-Geschwindigkeit', class_='monk',
     stats={'cdr': 0.05})
_add('m_sturm_n1', NOTABLE, (1720, 800), 'Sturmkreis',
     'Blitz springt zu +2 zusaetzlichen Gegnern',
     class_='monk',
     stats={'lit_dmg_pct': 0.05},
     effects=['lightning_chains_plus_2'])
_link('m_sturm_s1', 'm_sturm_s3')
_link('m_sturm_s2', 'm_sturm_s4')
_link('m_sturm_s3', 'm_sturm_n1')
_link('m_sturm_s4', 'm_sturm_n1')

# Layer 3: 3 Small (Sturm-Spur)
_add('m_sturm_s5', SMALL, (1770, 740), 'Donnerklang',
     '+10% Blitz-Schaden', class_='monk',
     stats={'lit_dmg_pct': 0.10})
_add('m_sturm_s6', SMALL, (1720, 740), 'Wolkengang',
     '+5% Bewegungstempo', class_='monk',
     stats={'speed': 0.05})
_add('m_sturm_s7', SMALL, (1670, 740), 'Statischer Stand',
     '+15 Mana', class_='monk',
     stats={'mp': 15})
_link('m_sturm_n1', 'm_sturm_s5')
_link('m_sturm_n1', 'm_sturm_s6')
_link('m_sturm_n1', 'm_sturm_s7')

# Layer 4: 2 Notable (Verzweigung in Keystones)
_add('m_sturm_n2', NOTABLE, (1780, 680), 'Statischer Atem',
     'Pro Schock-Stack auf einem Gegner: +10% Blitz-Schaden ggn ihn',
     class_='monk',
     stats={},
     effects=['lit_dmg_per_shock_stack'])
_add('m_sturm_n3', NOTABLE, (1680, 680), 'Donnerschritt',
     'Beim Ausweichen: Schock-Aura entlaedt sich (5 Stacks an Nachbarn)',
     class_='monk',
     stats={},
     effects=['dodge_shock_burst'])
_link('m_sturm_s5', 'm_sturm_n2')
_link('m_sturm_s6', 'm_sturm_n3')
_link('m_sturm_s7', 'm_sturm_n3')

# Layer 5: 4 Small (Pre-Keystone-Ring)
_add('m_sturm_s8', SMALL, (1810, 620), 'Stromader',
     '+8% Blitz-Schaden', class_='monk',
     stats={'lit_dmg_pct': 0.08})
_add('m_sturm_s9', SMALL, (1760, 600), 'Funken-Sehne',
     '+3% Krit-Chance', class_='monk',
     stats={'crit_chance': 0.03})
_add('m_sturm_s10', SMALL, (1700, 600), 'Trockene Zunge',
     '-8% Skill-Mana-Kosten', class_='monk',
     stats={'mana_cost_red': 0.08})
_add('m_sturm_s11', SMALL, (1650, 620), 'Funkenlauf',
     '+6% Tempo', class_='monk',
     stats={'speed': 0.06})
_link('m_sturm_n2', 'm_sturm_s8')
_link('m_sturm_n2', 'm_sturm_s9')
_link('m_sturm_n3', 'm_sturm_s10')
_link('m_sturm_n3', 'm_sturm_s11')

# Layer 6: 2 KEYSTONES (Gameplay-aendernd)
_add('m_sturm_k1', KEYSTONE, (1820, 540), 'Sturmreiter',
     'Blitz kettet endlos zwischen geschockten Gegnern '
     '(+1 Chain pro 2 Schock-Stacks im Schwarm). Mana-Kosten verdoppelt.',
     class_='monk',
     stats={},
     effects=['keystone_storm_rider'])
_add('m_sturm_k2', KEYSTONE, (1680, 540), 'Auge des Sturms',
     '+100% Krit-Chance ggn geschockte Gegner. Basis-Krit halbiert.',
     class_='monk',
     stats={},
     effects=['keystone_eye_of_storm'])
_link('m_sturm_s8', 'm_sturm_k1')
_link('m_sturm_s9', 'm_sturm_k1')
_link('m_sturm_s10', 'm_sturm_k2')
_link('m_sturm_s11', 'm_sturm_k2')


# ----------------------------------------------------------------
# MOENCH-PFAD B: BAMBUS (Melee/Speed) — nach rechts
# ----------------------------------------------------------------
_add('m_bamb_s1', SMALL, (1780, 1000), 'Bambusrute',
     '+5% Nahkampf-Schaden', class_='monk',
     stats={'melee_dmg_pct': 0.05})
_add('m_bamb_s2', SMALL, (1780, 1040), 'Gelenk',
     '+5% Angriffstempo', class_='monk',
     stats={'attack_speed': 0.05})
_link('monk_start', 'm_bamb_s1')
_link('monk_start', 'm_bamb_s2')

_add('m_bamb_s3', SMALL, (1840, 980), 'Stabwerk',
     '+8% Nahkampf-Schaden', class_='monk',
     stats={'melee_dmg_pct': 0.08})
_add('m_bamb_s4', SMALL, (1840, 1020), 'Schnellbeuge',
     '+5% Angriffstempo', class_='monk',
     stats={'attack_speed': 0.05})
_add('m_bamb_s5', SMALL, (1840, 1060), 'Stille Sohle',
     '-10% Ausweich-Abklingzeit', class_='monk',
     stats={'dodge_cdr': 0.10})
_link('m_bamb_s1', 'm_bamb_s3')
_link('m_bamb_s1', 'm_bamb_s4')
_link('m_bamb_s2', 'm_bamb_s4')
_link('m_bamb_s2', 'm_bamb_s5')

# Notable cluster
_add('m_bamb_n1', NOTABLE, (1900, 1000), 'Bambusbiegung',
     '10% Chance: Ausweichen setzt alle Skill-Abklingzeiten zurueck',
     class_='monk',
     stats={'dodge_cdr': 0.05},
     effects=['dodge_resets_cooldowns'])
_add('m_bamb_n2', NOTABLE, (1900, 1060), 'Eiserne Hand',
     'Nahkampf wandelt 25% Phys-Schaden in Blitz-Schaden um',
     class_='monk',
     stats={'melee_dmg_pct': 0.10},
     effects=['melee_phys_to_lit_25'])
_link('m_bamb_s3', 'm_bamb_n1')
_link('m_bamb_s4', 'm_bamb_n1')
_link('m_bamb_s4', 'm_bamb_n2')
_link('m_bamb_s5', 'm_bamb_n2')

# Mid Small ring
_add('m_bamb_s6', SMALL, (1960, 980), 'Drahtgriff',
     '+10% Nahkampf-Schaden', class_='monk',
     stats={'melee_dmg_pct': 0.10})
_add('m_bamb_s7', SMALL, (1960, 1020), 'Klanglos',
     '+6% Krit-Chance', class_='monk',
     stats={'crit_chance': 0.06})
_add('m_bamb_s8', SMALL, (1960, 1060), 'Wirbelschlag',
     '+8% Angriffstempo', class_='monk',
     stats={'attack_speed': 0.08})
_link('m_bamb_n1', 'm_bamb_s6')
_link('m_bamb_n1', 'm_bamb_s7')
_link('m_bamb_n2', 'm_bamb_s7')
_link('m_bamb_n2', 'm_bamb_s8')

# Pre-Keystone Notables
_add('m_bamb_n3', NOTABLE, (2020, 1000), 'Klangloser Tritt',
     '25% Chance nach Treffer auszuweichen (Iframe)',
     class_='monk',
     stats={'dodge_chance': 0.05},
     effects=['evade_after_hit_25'])
_add('m_bamb_n4', NOTABLE, (2020, 1060), 'Tanzendes Holz',
     'Nahkampf-Hits treffen Nachbarn (Cleave 40%)',
     class_='monk',
     stats={'melee_dmg_pct': 0.08},
     effects=['melee_cleave_40'])
_link('m_bamb_s6', 'm_bamb_n3')
_link('m_bamb_s7', 'm_bamb_n3')
_link('m_bamb_s7', 'm_bamb_n4')
_link('m_bamb_s8', 'm_bamb_n4')

# Final small ring + Keystones
_add('m_bamb_s9', SMALL, (2080, 980), 'Eisenfuss',
     '+12% Nahkampf-Schaden', class_='monk',
     stats={'melee_dmg_pct': 0.12})
_add('m_bamb_s10', SMALL, (2080, 1080), 'Atemzug-Pause',
     '+10% Angriffstempo', class_='monk',
     stats={'attack_speed': 0.10})
_link('m_bamb_n3', 'm_bamb_s9')
_link('m_bamb_n4', 'm_bamb_s10')

_add('m_bamb_k1', KEYSTONE, (2150, 1000), 'Eiserne Faust',
     'Nahkampf wandelt 100% Phys-Schaden in Blitz und kettet zu 2 Gegnern. '
     'Nahkampf kann nicht mehr kritisch treffen.',
     class_='monk',
     stats={},
     effects=['keystone_iron_palm'])
_add('m_bamb_k2', KEYSTONE, (2150, 1080), 'Weg des Windes',
     'Ausweichen hat keine Abklingzeit. Du erleidest +40% Schaden waehrend '
     'der Iframe-Phase (1s nach Dodge).',
     class_='monk',
     stats={},
     effects=['keystone_way_of_wind'])
_link('m_bamb_s9', 'm_bamb_k1')
_link('m_bamb_s10', 'm_bamb_k1')
_link('m_bamb_s10', 'm_bamb_k2')

# Hundredfold Echo — extra Keystone fuer Bambus-Pfad (oben)
_add('m_bamb_k3', KEYSTONE, (1960, 920), 'Hundertfaches Echo',
     'Jeder 5. Nahkampf-Hit triggert Frostnova am Ziel kostenlos.',
     class_='monk',
     stats={},
     effects=['keystone_hundredfold_echo'])
_link('m_bamb_n1', 'm_bamb_k3')
_link('m_bamb_s6', 'm_bamb_k3')


# ----------------------------------------------------------------
# MOENCH-PFAD C: SCHATTEN (Cold/Crit) — nach unten
# ----------------------------------------------------------------
_add('m_schat_s1', SMALL, (1740, 1080), 'Atem-Frost',
     '+6% Frost-Schaden', class_='monk',
     stats={'cold_dmg_pct': 0.06})
_add('m_schat_s2', SMALL, (1660, 1080), 'Spiegelblick',
     '+3% Krit-Chance', class_='monk',
     stats={'crit_chance': 0.03})
_link('monk_start', 'm_schat_s1')
_link('monk_start', 'm_schat_s2')

_add('m_schat_s3', SMALL, (1760, 1140), 'Eisring',
     '+8% Frost-Schaden', class_='monk',
     stats={'cold_dmg_pct': 0.08})
_add('m_schat_s4', SMALL, (1680, 1140), 'Stille Hand',
     '+10% Krit-Schaden', class_='monk',
     stats={'crit_dmg': 0.10})
_add('m_schat_n1', NOTABLE, (1720, 1200), 'Atem-Echo',
     'Frostnova-Radius +40%, Cold-Dmg +10%',
     class_='monk',
     stats={'cold_dmg_pct': 0.10},
     effects=['frostnova_radius_40'])
_link('m_schat_s1', 'm_schat_s3')
_link('m_schat_s2', 'm_schat_s4')
_link('m_schat_s3', 'm_schat_n1')
_link('m_schat_s4', 'm_schat_n1')

# Mid layer
_add('m_schat_s5', SMALL, (1770, 1260), 'Frostkristall',
     '+10% Frost-Schaden', class_='monk',
     stats={'cold_dmg_pct': 0.10})
_add('m_schat_s6', SMALL, (1720, 1260), 'Spiegelseele',
     '+4% Krit-Chance', class_='monk',
     stats={'crit_chance': 0.04})
_add('m_schat_s7', SMALL, (1670, 1260), 'Atemleere',
     '+1 MP-Regen', class_='monk',
     stats={'mp_regen': 1.0})
_link('m_schat_n1', 'm_schat_s5')
_link('m_schat_n1', 'm_schat_s6')
_link('m_schat_n1', 'm_schat_s7')

# Notable cluster
_add('m_schat_n2', NOTABLE, (1780, 1320), 'Klang der Stille',
     'Toetungen erstatten 12% deines max. Manas',
     class_='monk',
     stats={},
     effects=['kill_refunds_mana_12'])
_add('m_schat_n3', NOTABLE, (1680, 1320), 'Kalter Spiegel',
     'Frostnova fuegt 5 Frost-Stacks zu (statt Slow)',
     class_='monk',
     stats={'cold_dmg_pct': 0.08},
     effects=['frostnova_applies_frost_5'])
_link('m_schat_s5', 'm_schat_n2')
_link('m_schat_s6', 'm_schat_n2')
_link('m_schat_s6', 'm_schat_n3')
_link('m_schat_s7', 'm_schat_n3')

# Pre-Keystone ring
_add('m_schat_s8', SMALL, (1810, 1380), 'Frostkern',
     '+10% Frost-Schaden', class_='monk',
     stats={'cold_dmg_pct': 0.10})
_add('m_schat_s9', SMALL, (1760, 1400), 'Glasknochen',
     '+15% Krit-Schaden', class_='monk',
     stats={'crit_dmg': 0.15})
_add('m_schat_s10', SMALL, (1700, 1400), 'Stille Lunge',
     '-10% Skill-Mana-Kosten', class_='monk',
     stats={'mana_cost_red': 0.10})
_add('m_schat_s11', SMALL, (1650, 1380), 'Echo-Schritt',
     '+10% Krit-Schaden', class_='monk',
     stats={'crit_dmg': 0.10})
_link('m_schat_n2', 'm_schat_s8')
_link('m_schat_n2', 'm_schat_s9')
_link('m_schat_n3', 'm_schat_s10')
_link('m_schat_n3', 'm_schat_s11')

# Keystones
_add('m_schat_k1', KEYSTONE, (1820, 1460), 'Kalter Spiegel',
     'Frostnova feuert 3x hintereinander (0.15s Versatz). Jeder Cast kostet '
     'nur 60% Mana, aber Schaden -25% pro Welle.',
     class_='monk',
     stats={},
     effects=['keystone_cold_mirror'])
_add('m_schat_k2', KEYSTONE, (1680, 1460), 'Glasherz',
     '+100% Krit-Schaden, aber -40% max. Leben.',
     class_='monk',
     stats={},
     effects=['keystone_glass_heart'])
_link('m_schat_s8', 'm_schat_k1')
_link('m_schat_s9', 'm_schat_k1')
_link('m_schat_s10', 'm_schat_k2')
_link('m_schat_s11', 'm_schat_k2')


# ----------------------------------------------------------------
# MOENCH GATEWAYS zu SHARED-CORE (inneres Drittel)
# ----------------------------------------------------------------
_add('m_gate_sturm', GATEWAY, (1560, 800), 'Tor der Boe',
     '+15 max. Mana — Verbindung zum Inneren', class_='monk',
     stats={'mp': 15})
_add('m_gate_bamb', GATEWAY, (1560, 1000), 'Tor des Stocks',
     '+30 max. Leben — Verbindung zum Inneren', class_='monk',
     stats={'hp': 30})
_add('m_gate_schat', GATEWAY, (1560, 1200), 'Tor des Spiegels',
     '+1 HP-Regen — Verbindung zum Inneren', class_='monk',
     stats={'hp_regen': 1.0})

_link('m_sturm_s4', 'm_gate_sturm')
_link('m_bamb_s2', 'm_gate_bamb')
_link('m_schat_s2', 'm_gate_schat')


# ============================================================
# SHARED-CORE (neutral, alle Klassen koennen hier rein)
# ============================================================
# Layout: konzentrische Ringe um (1200, 1000).
_CC = (1200, 1000)

# Outer ring: 8 Gateways pro Klassen-Himmelsrichtung (nur Moench bisher)
_add('core_outer_e', GATEWAY, (1450, 1000), 'Aeusseres Tor (Ost)',
     '+20 max. Leben — Mond-Ring', stats={'hp': 20})
_add('core_outer_ne', GATEWAY, (1380, 850), 'Aeusseres Tor (Nord-Ost)',
     '+15 max. Mana — Mond-Ring', stats={'mp': 15})
_add('core_outer_se', GATEWAY, (1380, 1150), 'Aeusseres Tor (Sued-Ost)',
     '+0.5 HP-Regen — Mond-Ring', stats={'hp_regen': 0.5})

_link('m_gate_sturm', 'core_outer_ne')
_link('m_gate_bamb', 'core_outer_e')
_link('m_gate_schat', 'core_outer_se')

# Outer ring middle smalls
_add('core_outer_s1', SMALL, (1440, 920), 'Mondsteig (Nord)',
     '+15 max. Leben', stats={'hp': 15})
_add('core_outer_s2', SMALL, (1440, 1080), 'Mondsteig (Sued)',
     '+15 max. Leben', stats={'hp': 15})
_add('core_outer_s3', SMALL, (1380, 950), 'Sterneglas',
     '+2% Krit-Chance', stats={'crit_chance': 0.02})
_add('core_outer_s4', SMALL, (1380, 1050), 'Salzlauf',
     '+5% Tempo', stats={'speed': 0.05})
_link('core_outer_e', 'core_outer_s1')
_link('core_outer_e', 'core_outer_s2')
_link('core_outer_ne', 'core_outer_s3')
_link('core_outer_se', 'core_outer_s4')

# Mid ring: Notables (universal)
_add('core_mid_vit', NOTABLE, (1320, 1000), 'Lebenskern',
     '+40 max. Leben, +1 HP-Regen',
     stats={'hp': 40, 'hp_regen': 1.0})
_add('core_mid_arc', NOTABLE, (1340, 880), 'Arkankern',
     '+30 max. Mana, +1 MP-Regen',
     stats={'mp': 30, 'mp_regen': 1.0})
_add('core_mid_pwr', NOTABLE, (1340, 1120), 'Kraftkern',
     '+12% Gesamtschaden',
     stats={'dmg_pct': 0.12})
_link('core_outer_s1', 'core_mid_vit')
_link('core_outer_s2', 'core_mid_vit')
_link('core_outer_s3', 'core_mid_arc')
_link('core_outer_s4', 'core_mid_pwr')

# Mid smalls
_add('core_mid_s1', SMALL, (1260, 950), 'Geduldsstein',
     '+15 max. Leben', stats={'hp': 15})
_add('core_mid_s2', SMALL, (1260, 1050), 'Aderschlag',
     '+8% Schaden', stats={'dmg_pct': 0.08})
_add('core_mid_s3', SMALL, (1280, 880), 'Sand-Sanduhr',
     '-4% Abklingzeit', stats={'cdr': 0.04})
_add('core_mid_s4', SMALL, (1280, 1120), 'Eisernes Wort',
     '-3% Schaden erlitten', stats={'dmg_red': 0.03})
_link('core_mid_vit', 'core_mid_s1')
_link('core_mid_vit', 'core_mid_s2')
_link('core_mid_arc', 'core_mid_s3')
_link('core_mid_pwr', 'core_mid_s4')

# Inner ring: bigger notables + 1 universal Keystone
_add('core_inner_n1', NOTABLE, (1220, 950), 'Salzhueterin',
     '+25 max. Leben, +5% Schaden-Reduktion',
     stats={'hp': 25, 'dmg_red': 0.05})
_add('core_inner_n2', NOTABLE, (1220, 1050), 'Echo-Glocke',
     '+8% Gesamtschaden, +3% Krit-Chance',
     stats={'dmg_pct': 0.08, 'crit_chance': 0.03})
_link('core_mid_s1', 'core_inner_n1')
_link('core_mid_s3', 'core_inner_n1')
_link('core_mid_s2', 'core_inner_n2')
_link('core_mid_s4', 'core_inner_n2')

# Universal Keystone in der Mitte (POE-Klassiker)
_add('core_keystone_resolute', KEYSTONE, _CC, 'Eiserne Technik',
     'Du kannst nicht mehr kritisch treffen. Aber alle Treffer treffen '
     'garantiert (kein Miss/Dodge-Roll, ignoriert Ausweichen).',
     stats={},
     effects=['keystone_resolute_technique'])

_link('core_inner_n1', 'core_keystone_resolute')
_link('core_inner_n2', 'core_keystone_resolute')


# ============================================================
# KLASSEN-ARME fuer die anderen 7 Klassen
# ============================================================
# Jede Klasse bekommt einen echten themed Arm (Start + 9 Nodes), radial
# vom Atlas-Zentrum nach aussen orientiert, als verbundener Baum mit 3
# Pfaden (Offensiv / Vital / Utility) und einem starken Capstone-Notable.
# Alle Stats nutzen Keys, die progression.py / combat.py aggregieren
# (wirken also sofort, kein Effekt-Wiring noetig). Moench bleibt der
# einzige Arm mit gameplay-aendernden Keystones (Phase 1).

# Lokale Slot-Geometrie (+x = nach aussen, +y = senkrecht dazu):
_ARM_SLOTS = [
    # (slot_key, kind, local_x, local_y)
    ('s1',  SMALL,    78, -54),
    ('s2',  SMALL,    78,   0),
    ('s3',  SMALL,    78,  54),
    ('nA',  NOTABLE, 160, -80),
    ('nB',  NOTABLE, 170,   0),
    ('nC',  NOTABLE, 160,  80),
    ('sA',  SMALL,   232, -64),
    ('sC',  SMALL,   232,  64),
    ('cap', NOTABLE, 262,   0),
]
_ARM_LINKS = [
    ('start', 's1'), ('start', 's2'), ('start', 's3'),
    ('s1', 'nA'), ('s2', 'nB'), ('s3', 'nC'),
    ('nA', 'sA'), ('nC', 'sC'), ('nB', 'cap'),
]


def _add_class_arm(cls_key, name, start_pos, entries):
    """Baut Start + 9 themed Nodes als verbundenen Arm.

    `entries`: geordnete Liste von 9 (display_name, desc, stats), passend
    zu _ARM_SLOTS (s1,s2,s3,nA,nB,nC,sA,sC,cap). Der Arm wird radial vom
    Atlas-Zentrum (1200,1000) weg gedreht, damit Klassen-Cluster sich
    nicht ueberlappen.
    """
    import math
    sx, sy = start_pos
    sid = f'{cls_key}_start'
    _add(sid, START, start_pos, name,
         f'{name} — Erinnerungspfad. Nach aussen liegt dein Klassen-Weg, '
         f'nach innen der gemeinsame Kern.',
         class_=cls_key)
    ang = math.atan2(sy - 1000, sx - 1200)   # nach aussen vom Zentrum
    ca, sa = math.cos(ang), math.sin(ang)
    ids = {'start': sid}
    for (slot_key, kind, lx, ly), (dname, desc, stats) in zip(_ARM_SLOTS, entries):
        wx = sx + lx * ca - ly * sa
        wy = sy + lx * sa + ly * ca
        nid = f'{cls_key}_{slot_key}'
        _add(nid, kind, (int(wx), int(wy)), dname, desc,
             class_=cls_key, stats=stats)
        ids[slot_key] = nid
    for a, b in _ARM_LINKS:
        _link(ids[a], ids[b])


# --- Krieger (Eisen & Wucht) ---
_add_class_arm('warrior', 'Krieger', (700, 1000), [
    ('Schildhand',       '+18 max. Leben', {'hp': 18}),
    ('Wuchtschlag',      '+8% Nahkampfschaden', {'melee_dmg_pct': 0.08}),
    ('Zaeher Leib',      '-3% Schaden erlitten', {'dmg_red': 0.03}),
    ('Berserkerblut',    '+14% Nahkampf, +10% Krit-Schaden',
     {'melee_dmg_pct': 0.14, 'crit_dmg': 0.10}),
    ('Eisenwall',        '+45 Leben, -4% Schaden erlitten',
     {'hp': 45, 'dmg_red': 0.04}),
    ('Schlachtruf',      '+10% Nahkampf, +6% Angriffstempo',
     {'melee_dmg_pct': 0.10, 'attack_speed': 0.06}),
    ('Narbenleder',      '-3% Schaden erlitten', {'dmg_red': 0.03}),
    ('Kriegsfuror',      '+5% Angriffstempo', {'attack_speed': 0.05}),
    ('Unerschuetterlich', '+60 Leben, -6% Schaden, +10% Nahkampf',
     {'hp': 60, 'dmg_red': 0.06, 'melee_dmg_pct': 0.10}),
])

# --- Magier (Arkan & Elemente) ---
_add_class_arm('mage', 'Magier', (1200, 400), [
    ('Manabronnen',  '+20 max. Mana', {'mp': 20}),
    ('Funkenflug',   '+8% Zauberschaden', {'spell_dmg_pct': 0.08}),
    ('Klarsicht',    '-4% Abklingzeit', {'cdr': 0.04}),
    ('Pyromantie',   '+16% Feuer, +8% Zauberschaden',
     {'fire_dmg_pct': 0.16, 'spell_dmg_pct': 0.08}),
    ('Arkane Tiefe', '+40 Mana, +1 MP-Regen', {'mp': 40, 'mp_regen': 1.0}),
    ('Kryomantie',   '+16% Kaelte, +3% Krit-Chance',
     {'cold_dmg_pct': 0.16, 'crit_chance': 0.03}),
    ('Brennglas',    '+6% Feuerschaden', {'fire_dmg_pct': 0.06}),
    ('Frostlinse',   '+6% Kaelteschaden', {'cold_dmg_pct': 0.06}),
    ('Magus-Krone',  '+16% Zauber, -6% Abklingzeit, +30 Mana',
     {'spell_dmg_pct': 0.16, 'cdr': 0.06, 'mp': 30}),
])

# --- Soeldner (Krit & Tempo) ---
_add_class_arm('rogue', 'Soeldner', (700, 600), [
    ('Fingerfertig',   '+3% Krit-Chance', {'crit_chance': 0.03}),
    ('Leichtfuss',     '+5% Tempo', {'speed': 0.05}),
    ('Ausweichen',     '+4% Ausweichen', {'dodge_chance': 0.04}),
    ('Meucheln',       '+18% Krit-Schaden, +3% Krit-Chance',
     {'crit_dmg': 0.18, 'crit_chance': 0.03}),
    ('Schattenschritt', '+8% Tempo, +5% Ausweichen',
     {'speed': 0.08, 'dodge_chance': 0.05}),
    ('Praeziser Stich', '+5% Krit-Chance, +8% Schaden',
     {'crit_chance': 0.05, 'dmg_pct': 0.08}),
    ('Schnellklinge',  '+5% Angriffstempo', {'attack_speed': 0.05}),
    ('Katzentritt',    '+3% Ausweichen', {'dodge_chance': 0.03}),
    ('Klingentanz',    '+6% Krit, +16% Krit-Schaden, +6% Angriffstempo',
     {'crit_chance': 0.06, 'crit_dmg': 0.16, 'attack_speed': 0.06}),
])

# --- Jaegerin (Fernkampf & Praezision) ---
_add_class_arm('ranger', 'Jaegerin', (700, 1400), [
    ('Falkenauge',  '+4% Krit-Chance', {'crit_chance': 0.04}),
    ('Windlauf',    '+5% Tempo', {'speed': 0.05}),
    ('Zielsicher',  '+6% Gesamtschaden', {'dmg_pct': 0.06}),
    ('Durchschlag', '+14% Schaden, +10% Krit-Schaden',
     {'dmg_pct': 0.14, 'crit_dmg': 0.10}),
    ('Jagdinstinkt', '+5% Krit-Chance, +6% Angriffstempo',
     {'crit_chance': 0.05, 'attack_speed': 0.06}),
    ('Spurengang',  '+8% Tempo, -3% Schaden erlitten',
     {'speed': 0.08, 'dmg_red': 0.03}),
    ('Sehnenkraft', '+5% Angriffstempo', {'attack_speed': 0.05}),
    ('Pfadfinder',  '+4% Tempo', {'speed': 0.04}),
    ('Sturmpfeil',  '+6% Krit, +18% Krit-Schaden, +8% Schaden',
     {'crit_chance': 0.06, 'crit_dmg': 0.18, 'dmg_pct': 0.08}),
])

# --- Hexe (Hexerei & Elemente) ---
_add_class_arm('witch', 'Hexe', (1200, 1600), [
    ('Hexenmal',     '+7% Zauberschaden', {'spell_dmg_pct': 0.07}),
    ('Manaquell',    '+20 max. Mana', {'mp': 20}),
    ('Frostsegen',   '+7% Kaelteschaden', {'cold_dmg_pct': 0.07}),
    ('Aschehexerei', '+14% Feuer, +7% Zauberschaden',
     {'fire_dmg_pct': 0.14, 'spell_dmg_pct': 0.07}),
    ('Bluthexe',     '+35 Mana, +10% Zauberschaden',
     {'mp': 35, 'spell_dmg_pct': 0.10}),
    ('Eishexerei',   '+14% Kaelte, +3% Krit-Chance',
     {'cold_dmg_pct': 0.14, 'crit_chance': 0.03}),
    ('Schwelglut',   '+6% Feuerschaden', {'fire_dmg_pct': 0.06}),
    ('Raureif',      '+6% Kaelteschaden', {'cold_dmg_pct': 0.06}),
    ('Schwesternpakt', '+16% Zauber, +8% Feuer, +8% Kaelte',
     {'spell_dmg_pct': 0.16, 'fire_dmg_pct': 0.08, 'cold_dmg_pct': 0.08}),
])

# --- Speerschwester (Speer & Mondtempo) ---
_add_class_arm('huntress', 'Speerschwester', (1700, 1600), [
    ('Speerhand',      '+7% Nahkampfschaden', {'melee_dmg_pct': 0.07}),
    ('Mondlauf',       '+6% Tempo', {'speed': 0.06}),
    ('Wachsam',        '+3% Krit-Chance', {'crit_chance': 0.03}),
    ('Speerwurf',      '+14% Nahkampf, +8% Krit-Schaden',
     {'melee_dmg_pct': 0.14, 'crit_dmg': 0.08}),
    ('Mondbund',       '+8% Tempo, +6% Angriffstempo',
     {'speed': 0.08, 'attack_speed': 0.06}),
    ('Schwesternschild', '+30 Leben, -4% Schaden erlitten',
     {'hp': 30, 'dmg_red': 0.04}),
    ('Sprungkraft',    '+5% Angriffstempo', {'attack_speed': 0.05}),
    ('Jagdtempo',      '+4% Tempo', {'speed': 0.04}),
    ('Mondklinge',     '+16% Nahkampf, +6% Angriffstempo, +5% Krit',
     {'melee_dmg_pct': 0.16, 'attack_speed': 0.06, 'crit_chance': 0.05}),
])

# --- Wandelnde (Natur & Regeneration) ---
_add_class_arm('druid', 'Wandelnde', (1700, 400), [
    ('Lebenssaft',   '+18 max. Leben', {'hp': 18}),
    ('Wildwuchs',    '+1 HP-Regen', {'hp_regen': 1.0}),
    ('Naturgang',    '+4% Tempo', {'speed': 0.04}),
    ('Bestienform',  '+12% Nahkampf, +20 Leben',
     {'melee_dmg_pct': 0.12, 'hp': 20}),
    ('Uralter Hain', '+45 Leben, +1.5 HP-Regen', {'hp': 45, 'hp_regen': 1.5}),
    ('Sturmgestalt', '+12% Blitzschaden, +6% Gesamtschaden',
     {'lit_dmg_pct': 0.12, 'dmg_pct': 0.06}),
    ('Dornenhaut',   '-3% Schaden erlitten', {'dmg_red': 0.03}),
    ('Frischwasser', '+1 HP-Regen', {'hp_regen': 1.0}),
    ('Weltenbaum',   '+60 Leben, +2 HP-Regen, -5% Schaden erlitten',
     {'hp': 60, 'hp_regen': 2.0, 'dmg_red': 0.05}),
])


# Klassen-Starts → Outer-Core Gateways: verbindet jeden Klassen-Arm mit
# dem gemeinsamen Kern, damit von jeder Klasse aus die Shared-Core-Nodes
# erreichbar sind. (Core hat 3 oestliche Gateways; weiter entfernte
# Klassen verbinden ueber eine laengere Bruecke — Geometrie-Politur der
# Gateway-Verteilung ist eine separate Aufgabe.)
_link('warrior_start',  'core_outer_e')
_link('mage_start',     'core_outer_ne')
_link('rogue_start',    'core_outer_ne')
_link('ranger_start',   'core_outer_se')
_link('witch_start',    'core_outer_se')
_link('huntress_start', 'core_outer_e')
_link('druid_start',    'core_outer_ne')


# ============================================================
# CLASS-STARTS-MAP (root node pro Klasse)
# ============================================================
CLASS_STARTS = {
    'warrior':  'warrior_start',
    'monk':     'monk_start',
    'mage':     'mage_start',
    'witch':    'witch_start',
    'ranger':   'ranger_start',
    'rogue':    'rogue_start',
    'huntress': 'huntress_start',
    'druid':    'druid_start',
}


# ============================================================
# Adjazenz-Cache fuer schnelle Nachbar-Lookups
# ============================================================
_NEIGHBORS = None


def _build_neighbors():
    global _NEIGHBORS
    _NEIGHBORS = {nid: set() for nid in ATLAS_NODES}
    for a, b in ATLAS_EDGES:
        if a in _NEIGHBORS and b in _NEIGHBORS:
            _NEIGHBORS[a].add(b)
            _NEIGHBORS[b].add(a)


def neighbors(node_id):
    """Returnt set() der Nachbarn eines Knotens."""
    if _NEIGHBORS is None:
        _build_neighbors()
    return _NEIGHBORS.get(node_id, set())


# Initial-Build
_build_neighbors()


# ============================================================
# Player-Atlas-Helpers
# ============================================================
def initial_atlas(player):
    """Returnt das initiale allokierte Set fuer einen Spieler — nur sein
    Klassen-Start, der gratis ist."""
    start = CLASS_STARTS.get(player.cls)
    if start is None:
        return set()
    return {start}


def is_allocated(player, node_id):
    atlas = getattr(player, 'atlas', None)
    if atlas is None:
        return False
    return node_id in atlas


def can_allocate(player, node_id):
    """Prueft ob ein Knoten allokierbar ist."""
    if node_id not in ATLAS_NODES:
        return False
    node = ATLAS_NODES[node_id]
    atlas = getattr(player, 'atlas', None)
    if atlas is None:
        return False
    if node_id in atlas:
        return False
    # Klassen-Restriction
    if node['class_'] is not None and node['class_'] != player.cls:
        return False
    # Punkt-Check
    if getattr(player, 'atlas_points', 0) <= 0:
        return False
    # Adjacency-Check
    for nb in neighbors(node_id):
        if nb in atlas:
            return True
    return False


def try_allocate(player, node_id):
    """Versucht einen Knoten zu allokieren. True wenn erfolgreich."""
    if not can_allocate(player, node_id):
        return False
    player.atlas.add(node_id)
    player.atlas_points -= 1
    return True


def try_refund(player, node_id):
    """Refundet einen Knoten (kostet Orb-of-Regret). Pruefen, dass kein
    anderer allokierter Knoten dadurch vom Start abgeschnitten wird."""
    atlas = getattr(player, 'atlas', None)
    if atlas is None or node_id not in atlas:
        return False
    node = ATLAS_NODES.get(node_id)
    if node is None or node['kind'] == START:
        return False  # Start kann nicht entfernt werden
    if getattr(player, 'orbs_of_regret', 0) <= 0:
        return False
    # Connectivity-Check: alle anderen allokierten muessen weiter erreichbar
    # sein vom Klassen-Start aus, OHNE diesen Knoten.
    start = CLASS_STARTS.get(player.cls)
    if start is None:
        return False
    remaining = set(atlas)
    remaining.discard(node_id)
    if not _all_reachable(start, remaining):
        return False
    player.atlas.discard(node_id)
    player.atlas_points += 1
    player.orbs_of_regret -= 1
    return True


def _all_reachable(start, allocated):
    """BFS: prueft ob alle Knoten in `allocated` vom `start` aus
    ueber Kanten erreichbar sind, die nur durch allokierte Knoten gehen."""
    if start not in allocated:
        return False
    seen = {start}
    queue = [start]
    while queue:
        node = queue.pop()
        for nb in neighbors(node):
            if nb in allocated and nb not in seen:
                seen.add(nb)
                queue.append(nb)
    return seen == allocated


# ============================================================
# Aggregat-Funktionen (von progression.py / skills.py benutzt)
# ============================================================
def aggregate_stats(player):
    """Sammelt alle Stats aus den allokierten Atlas-Nodes."""
    out = {}
    atlas = getattr(player, 'atlas', None)
    if not atlas:
        return out
    for nid in atlas:
        node = ATLAS_NODES.get(nid)
        if node is None:
            continue
        for k, v in node['stats'].items():
            out[k] = out.get(k, 0) + v
    return out


def active_effects(player):
    """Returnt set() der Effekt-IDs (Keystones + Notable-Effekte)
    die der Spieler aktuell aktiv hat."""
    out = set()
    atlas = getattr(player, 'atlas', None)
    if not atlas:
        return out
    for nid in atlas:
        node = ATLAS_NODES.get(nid)
        if node is None:
            continue
        for eff in node['effects']:
            out.add(eff)
    return out


def has_keystone(player, effect_id):
    """Convenience: prueft ob ein bestimmter Effect aktiv ist."""
    return effect_id in active_effects(player)


# ============================================================
# Migration: alte tree+class_tree → atlas-points
# ============================================================
def migrate_legacy_points(player):
    """Konvertiert alte skill_points + class_points zu atlas_points.
    Wird einmalig beim Save-Load aufgerufen wenn `atlas` noch nicht
    existiert. Refundet alte tree/class_tree-Investitionen 1:1 zurueck."""
    if hasattr(player, 'atlas') and player.atlas:
        return  # bereits migriert
    # Atlas-Points = ungesetzte universal + class points + summe der bereits
    # in alten Trees gesetzten Punkte (Refund) + 1 pro Level als Faustregel
    invested_uni = sum(player.tree.values()) if hasattr(player, 'tree') else 0
    invested_cls = (sum(player.class_tree.values())
                    if hasattr(player, 'class_tree') else 0)
    sp = getattr(player, 'skill_points', 0)
    cp = getattr(player, 'class_points', 0)
    player.atlas = initial_atlas(player)
    player.atlas_points = sp + cp + invested_uni + invested_cls
    # Alte Trees leeren (Punkte wurden erstattet)
    if hasattr(player, 'tree'):
        player.tree = {}
    if hasattr(player, 'class_tree'):
        player.class_tree = {}
    player.skill_points = 0
    player.class_points = 0


# ============================================================
# Stat-Key-Doku (was die UI/progression.py kennen muss)
# ============================================================
# Atlas liefert folgende Stat-Keys (additiv aggregiert):
#   hp, mp, hp_regen, mp_regen                   (flat)
#   dmg_pct, melee_dmg_pct, spell_dmg_pct        (multiplikative %)
#   fire_dmg_pct, cold_dmg_pct, lit_dmg_pct      (element %)
#   crit_chance, crit_chance_lightning, crit_dmg (additiv)
#   speed, attack_speed, cdr, dodge_cdr          (multiplikative %)
#   dmg_red                                      (additiv 0..1)
#   dodge_chance                                 (additiv 0..1)
#   mana_cost_red                                (additiv 0..1, Spend-Side)
#
# Effekt-IDs (von skills.py / combat.py / game.py abgefragt):
#   lightning_chains_plus_2          — +2 max_targets fuer cast_lightning
#   lit_dmg_per_shock_stack          — +10% lit-dmg pro shock-stack auf target
#   dodge_shock_burst                — beim dodge: 5 shock-stacks an Nachbarn
#   keystone_storm_rider             — endlos chaining auf geschockte
#   keystone_eye_of_storm            — 100% crit ggn shocked, base crit /2
#   dodge_resets_cooldowns           — 10% chance bei dodge: alle CDs reset
#   melee_phys_to_lit_25             — 25% phys→lit conversion bei melee
#   evade_after_hit_25               — 25% chance nach hit zu evaden
#   melee_cleave_40                  — melee trifft nachbarn 40%
#   keystone_iron_palm               — 100% phys→lit melee + chain to 2
#   keystone_way_of_wind             — no dodge-cd, +40% dmg taken in iframe
#   keystone_hundredfold_echo        — jeder 5. melee → free frostnova
#   frostnova_radius_40              — +40% frostnova radius
#   kill_refunds_mana_12             — kill returnt 12% max mp
#   frostnova_applies_frost_5        — frostnova → 5 frost-stacks
#   keystone_cold_mirror             — frostnova 3x, -25% dmg, 60% mana
#   keystone_glass_heart             — +100% crit-dmg, -40% hp_max
#   keystone_resolute_technique      — kein crit, aber kein miss/dodge
