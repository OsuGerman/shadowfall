"""Konkrete Monster-Templates aus VELGRAD_BESTIARIUM.md.

Erste Welle: Akt-1-Mobs (Bestiarium #1–5: Salzgekreuzter, Krustenkrabbe,
Ertrunkenes Echo, Möwen-Schwarm, Salzhüter-Brut).

Jeder Bestiarium-Eintrag verweist auf:
  - Archetyp (siehe sf/archetypes.py)
  - Base-Template aus enemies.ENEMY_TYPES (für HP/Damage/Sprite-Fallback)
  - Lore-Hooks (Audio-Cues, Death-Behavior, Drops, Quote-Hints)

Das ergänzt — nicht ersetzt — das existierende enemies.ENEMY_TYPES.
Spawn-Helper `spawn_bestiary_mob(game, key, x, y)` wickelt die volle
Initialisierung ab.
"""

import random

from . import archetypes as _arch


# ============================================================
# AKT 1 — DIE SALZKÜSTE (Bestiarium #1–5)
# ============================================================
# Felder pro Eintrag:
#   key           Display-/Save-ID
#   display_name  Lore-Name aus Bestiarium
#   base_type     fallback ENEMY_TYPES-Key für Sprite & Basis-Stats
#   archetype     Archetypes.* — bestimmt sight/hearing/engage
#   tier          'L' | 'M' | 'E' | 'X'
#   act           Akt-Nummer (1..7)
#   hp_mult, dmg_mult, speed_mult, radius_mult  → Multiplikatoren auf base_type
#   color, glow   Override-Farben für Lore-Look
#   windup_audio  SFX-Key für Wind-Up vor Signature-Attack (z.B. 'aoe_windup')
#   death_audio   SFX-Key beim Tod (z.B. 'roar')
#   on_death      'salt_explosion' | 'tiny_slow_pool' | 'silent_collapse' | 'death_pop'
#   lore_quote    1-Liner aus Bestiarium, für Codex/Tooltip

BESTIARY = {
    # --- Bestiarium #1: SALZGEKREUZTER ----------------------------------
    'salzgekreuzter': dict(
        display_name='Salzgekreuzter',
        base_type='zombie',
        archetype=_arch.Archetype.BRUTE,
        tier='L', act=1,
        hp_mult=1.6,  dmg_mult=1.2, speed_mult=0.75, radius_mult=1.1,
        color=(180, 196, 208),   # bleich, salzverkrustet
        glow=(220, 230, 240),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death='salt_explosion',  # bei <30% zerfällt → 2s später AoE
        sub_aggro_hint='stalker',   # leichter Stalker-Anflug aus Bestiarium
        lore_quote=("Diese sind die Bewohner von Marrowport. Vor 3 Wochen "
                    "vom Vergessen erfasst. Tötet man sie, vollendet das "
                    "Vergessen — gnädig wie endgültig."),
    ),

    # --- Bestiarium #2: KRUSTENKRABBE -----------------------------------
    'krustenkrabbe': dict(
        display_name='Krustenkrabbe',
        base_type='slime',           # kleiner, schneller, low HP
        archetype=_arch.Archetype.CHARGER,
        tier='L', act=1,
        hp_mult=1.1, dmg_mult=1.0, speed_mult=1.6, radius_mult=0.95,
        color=(200, 180, 130),
        glow=(240, 220, 160),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death='tiny_slow_pool',   # Salzwasser-Pfütze, Slow-Field
        lore_quote=("Normale Krabben wachsen hier aus dem Maß. Eine alte "
                    "Geschichte: sie tragen Glasgoldene Wrack-Stücke "
                    "in ihren Panzern."),
    ),

    # --- Bestiarium #3: ERTRUNKENES ECHO --------------------------------
    'ertrunkenes_echo': dict(
        display_name='Ertrunkenes Echo',
        base_type='wraith',
        archetype=_arch.Archetype.CASTER,
        tier='L', act=1,
        hp_mult=1.0, dmg_mult=1.1, speed_mult=0.9, radius_mult=1.0,
        color=(110, 150, 180),
        glow=(160, 200, 230),
        windup_audio='aoe_windup',
        death_audio='roar',          # „schreit endlich" beim Tod
        on_death='silent_collapse',
        spectral=True,               # sight ignoriert Wände
        lore_quote=("Die Salzwunde lockt Ertrunkene aus 800 Jahren See-"
                    "handel zurück. Manche sterben endlich, wenn ihre "
                    "alten Verträge erfüllt werden. Andere — nicht."),
    ),

    # --- Bestiarium #4: MÖWEN-SCHWARM -----------------------------------
    # Wir modellieren einen Schwarm als ein einzelnes Entity mit
    # Flyer-Verhalten (vereinfachte Variante; volle Multi-Vogel-Simulation
    # wäre F-14 später).
    'moewen_schwarm': dict(
        display_name='Möwen-Schwarm',
        base_type='lurker',          # schnell, mittel-HP, klein
        archetype=_arch.Archetype.FLYER,
        tier='L', act=1,
        hp_mult=0.75, dmg_mult=0.8, speed_mult=1.4, radius_mult=0.85,
        color=(220, 220, 210),
        glow=(240, 240, 230),
        windup_audio=None,           # Dive-Bomb hat eigenen 0.5s-Telegraph
        death_audio=None,
        on_death='death_pop',
        bleed_buildup_bonus=1.5,
        lore_quote=("Sie folgten ein Fischerboot in den Hafen, das nie "
                    "ankam. Jetzt warten sie. Die Augen sind weiß, weil "
                    "sie zu lange gewartet haben."),
    ),

    # --- Bestiarium #5: SALZHÜTER-BRUT (Mini-Boss) ----------------------
    'salzhueter_brut': dict(
        display_name='Salzhüter-Brut',
        base_type='brute',
        archetype=_arch.Archetype.CHAMPION,
        tier='L', act=1,
        hp_mult=2.5, dmg_mult=1.5, speed_mult=0.8, radius_mult=1.3,
        color=(180, 175, 165),       # steinern, Salz-Patina
        glow=(220, 220, 200),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        is_mini_boss=True,
        lore_quote=("War einst Wache an Velharns Hafentor. Wurde im "
                    "Götterkrieg überrannt, niemand kam zur Ablösung. "
                    "Sie wartet immer noch. Niemand kommt mehr."),
    ),

    # ============================================================
    # AKT 3 — DIE ASCHENFELDER (Bestiarium #11-15)
    # ============================================================

    # --- Bestiarium #11: ASCH-SOLDAT ------------------------------------
    'asch_soldat': dict(
        display_name='Asch-Soldat',
        base_type='skeleton',
        archetype=_arch.Archetype.SKIRMISHER,
        tier='M', act=3,
        hp_mult=1.5, dmg_mult=1.3, speed_mult=1.0, radius_mult=1.0,
        color=(210, 180, 100),       # Bronze-Glanz auf weißen Knochen
        glow=(255, 200, 120),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death=None,
        lore_quote=("Sie marschierten mit Valsa. Sie fielen mit ihr. "
                    "Sie marschieren immer noch — weil niemand den "
                    "Befehl zur Auflösung gab."),
    ),

    # --- Bestiarium #12: BRENNENDER PREDIGT-SPRECHER --------------------
    'predigt_sprecher': dict(
        display_name='Brennender Predigt-Sprecher',
        base_type='warlock',
        archetype=_arch.Archetype.CASTER,
        tier='M', act=3,
        hp_mult=1.4, dmg_mult=1.5, speed_mult=0.85, radius_mult=1.05,
        color=(220, 100,  50),       # robe-orange + flammend
        glow=(255, 180, 100),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        lore_quote=("Inquisitoren des Tribunals der Asche, die zu lange "
                    "in den Aschenfeldern blieben. Ihre Predigt ist "
                    "nicht mehr für Sterbliche — sie ist für Valsa selbst."),
    ),

    # --- Bestiarium #13: INQUISITIONS-KLINGENMESSER ---------------------
    'klingenmesser': dict(
        display_name='Inquisitions-Klingenmesser',
        base_type='lurker',
        archetype=_arch.Archetype.STALKER,
        tier='M', act=3,
        hp_mult=1.2, dmg_mult=1.7, speed_mult=1.15, radius_mult=0.95,
        color=( 80,  70,  90),       # dunkle Robe
        glow=(180, 120, 180),
        windup_audio=None,           # Stalker — keine Wind-Up-SFX
        death_audio=None,
        on_death=None,
        lore_quote=("Die unauffällige Hand des Tribunals. Sie jagen "
                    "die, die das Tribunal selbst nicht öffentlich "
                    "verurteilen kann. Sie hinterlassen keine Spuren — "
                    "meistens."),
    ),

    # --- Bestiarium #14: ASCH-WOLF --------------------------------------
    'asch_wolf': dict(
        display_name='Asch-Wolf',
        base_type='berserker',       # schnell + aggressiv
        archetype=_arch.Archetype.CHARGER,
        tier='M', act=3,
        hp_mult=1.3, dmg_mult=1.4, speed_mult=1.4, radius_mult=0.9,
        color=( 60,  40,  40),       # schwarz + Asche
        glow=(255, 130,  70),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='salt_explosion',   # brandige Death-Explosion (kleiner)
        lore_quote=("Normale Wölfe der Region, die zu nah an Valsas "
                    "Asche kamen. Eine Saatträger-Theorie: ihre Seelen "
                    "sind noch dieselben. Tötet man sie, befreit man sie."),
    ),

    # --- Bestiarium #15: TRIBUNAL-KONSTRUKT (Mini-Boss) -----------------
    'tribunal_konstrukt': dict(
        display_name='Tribunal-Konstrukt',
        base_type='brute',
        archetype=_arch.Archetype.GUARDIAN,
        tier='M', act=3,
        hp_mult=2.8, dmg_mult=1.8, speed_mult=0.7, radius_mult=1.35,
        color=(140, 110,  80),       # Bronze-Statue
        glow=(255, 150,  80),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        is_mini_boss=True,
        lore_quote=("Vom Tribunal gebaut aus den Helmen gefallener "
                    "Glasgoldener Wächter. Eine Mischung, die nicht "
                    "hätte funktionieren dürfen. Tut es auch nicht — "
                    "die Konstrukte werden immer wahnsinniger."),
    ),

    # ============================================================
    # AKT 2 — DIE GLASGOLDENEN RUINEN (Bestiarium #6-10)
    # ============================================================
    # Lore-Bibel 4.1: Liga der 412 Senatoren, Glasgolden-Hafen,
    # Spiegel-Anomalien. Biome-Anker: frost (Glas-Affinität).

    # --- Bestiarium #6: ECHO-SENATOR ------------------------------------
    'echo_senator': dict(
        display_name='Echo-Senator',
        base_type='warlock',
        archetype=_arch.Archetype.CASTER,
        tier='L', act=2,
        hp_mult=1.2, dmg_mult=0.9, speed_mult=0.85, radius_mult=1.05,
        color=(220, 200, 140),       # Toga + Goldstaub
        glow=(255, 220, 160),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death=None,
        spectral=True,               # halbtransparent, sieht durch Wände
        lore_quote=("Einer der 412 Senatoren der Glasgoldenen Liga. "
                    "Spricht jeden Tag dieselben 3 Reden, seit 800 "
                    "Jahren. Tötet man ihn, vergisst die Welt, was er "
                    "sagte."),
    ),

    # --- Bestiarium #7: GLASGOLDEN-WÄCHTER ------------------------------
    'glasgolden_waechter': dict(
        display_name='Glasgolden-Wächter',
        base_type='brute',
        archetype=_arch.Archetype.GUARDIAN,
        tier='M', act=2,
        hp_mult=2.4, dmg_mult=1.7, speed_mult=0.65, radius_mult=1.3,
        color=(180, 160, 100),       # Glas + Gold
        glow=(240, 220, 140),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        lore_quote=("Gebaut von der Liga, um den Hafen zu bewachen. "
                    "Wurde nie offiziell deaktiviert. Steht immer noch "
                    "da. Tut immer noch seinen Job — auch wenn der "
                    "Hafen nicht mehr existiert."),
    ),

    # --- Bestiarium #8: GOLDSTAUB-DIENER --------------------------------
    'goldstaub_diener': dict(
        display_name='Goldstaub-Diener',
        base_type='skeleton',
        archetype=_arch.Archetype.SKIRMISHER,
        tier='L', act=2,
        hp_mult=0.9, dmg_mult=1.1, speed_mult=1.25, radius_mult=0.95,
        color=(220, 190, 120),
        glow=(255, 220, 150),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death='death_pop',
        lore_quote=("Die Bediensteten der Senatoren-Häuser. Sie "
                    "servieren immer noch Tee an Tische, die nicht mehr "
                    "da sind. Der Tee ist heiß. Der Goldstaub ebenso."),
    ),

    # --- Bestiarium #9: SPIEGEL-STALKER ---------------------------------
    'spiegel_stalker': dict(
        display_name='Spiegel-Stalker',
        base_type='lurker',
        archetype=_arch.Archetype.STALKER,
        tier='M', act=2,
        hp_mult=1.1, dmg_mult=1.6, speed_mult=1.2, radius_mult=0.9,
        color=(120, 140, 170),       # fast unsichtbar — Glas-Reflexion
        glow=(220, 230, 250),
        windup_audio=None,           # Stalker — leise
        death_audio=None,
        on_death=None,
        lore_quote=("Niemand weiß, wo sie hergekommen sind. Manche "
                    "glauben, sie sind die Reflexionen der Senatoren, "
                    "die in den Spiegeln vergessen wurden."),
    ),

    # --- Bestiarium #10: VERFALLENER MAGISTER ---------------------------
    'verfallener_magister': dict(
        display_name='Verfallener Magister',
        base_type='warlock',
        archetype=_arch.Archetype.SUPPORT,
        tier='M', act=2,
        hp_mult=1.3, dmg_mult=0.85, speed_mult=0.9, radius_mult=1.0,
        color=( 90,  70, 110),       # Tinten-Augen, zerfallene Robe
        glow=(180, 150, 220),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death=None,
        spectral=True,
        lore_quote=("Diese Gelehrten studierten Im-Neshs Pakt. Sie "
                    "haben zuviel gesehen. Die Welt hat sie als Strafe "
                    "halb-vergessen."),
    ),

    # --- Akt-3-Boss: INQUISITOR-GENERAL VEHREN --------------------------
    # Lore-Quellen:
    #   - VELGRAD_VOICE_LINES_POOL.md NPC 7 (Voice-Notes, Threats,
    #     Phase-Transition-, Last-Words)
    #   - VELGRAD_LORE_BIBEL.md Teil 6.3 (Tribunal der Asche) + 10.3
    #     (Akt 3 Story-Beat: „Vehren wird von Valsas Asche besessen")
    'vehren': dict(
        display_name='Inquisitor-General Vehren',
        base_type='warlock',         # Caster-Base mit Fire/Chaos-Affinität
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=3,
        hp_mult=3.0,  dmg_mult=1.6, speed_mult=0.9, radius_mult=1.25,
        color=(210,  90,  40),       # Tribunal-Inquisitor-Orange (Asche+Glut)
        glow=(255, 180, 100),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='silent_collapse',  # Vehren atmet seinen letzten Spruch aus
        is_mini_boss=True,
        lore_quote=("Du bist Im-Nesh-berührt. Es tut mir leid. "
                    "Es ist meine Pflicht."),
    ),

    # ============================================================
    # AKT 4 — DAS WURZELGRAB (Bestiarium #16-20)
    # ============================================================
    # Lore-Bibel 4.1: Shulavhs Wurzelgrab, Knochenwitwen-Lineage,
    # Faden-Bindung. Biome-Anker: swamp.

    # --- Bestiarium #16: KNOCHENWITWEN-SCHWESTER ------------------------
    'knochenwitwe': dict(
        display_name='Knochenwitwen-Schwester',
        base_type='warlock',
        archetype=_arch.Archetype.SUMMONER,
        tier='M', act=4,
        hp_mult=1.3, dmg_mult=1.3, speed_mult=0.95, radius_mult=1.0,
        color=( 60,  50,  70),       # zerfetzte dunkle Robe
        glow=(170, 160, 200),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death=None,
        lore_quote=("Schwestern von Vossharil, die ihren Pakt mit den "
                    "Toten zu weit getrieben haben. Vossharil selbst "
                    "lehnt sie ab — sie sind verdorben durch "
                    "Nachgiebigkeit."),
    ),

    # --- Bestiarium #17: WURZEL-SPINNE ----------------------------------
    'wurzelspinne': dict(
        display_name='Wurzel-Spinne',
        base_type='lurker',
        archetype=_arch.Archetype.STALKER,
        tier='M', act=4,
        hp_mult=1.4, dmg_mult=1.5, speed_mult=1.05, radius_mult=1.15,
        color=( 60,  80,  40),       # Wurzel-Beine
        glow=(140, 200,  80),
        windup_audio=None,
        death_audio='roar',
        on_death='tiny_slow_pool',   # Schleim-Netze am Boden
        lore_quote=("Sie kamen mit Shulavh — sind ihre Boten. Shulavh "
                    "schickt sie aus, um Sterbliche zu testen."),
    ),

    # --- Bestiarium #18: FADEN-GEBUNDENER -------------------------------
    'faden_gebundener': dict(
        display_name='Faden-Gebundener',
        base_type='zombie',
        archetype=_arch.Archetype.SUPPORT,
        tier='M', act=4,
        hp_mult=1.1, dmg_mult=1.2, speed_mult=0.85, radius_mult=1.0,
        color=(170, 130, 120),       # blasse Haut, rote Fäden
        glow=(220, 100, 100),
        windup_audio=None,
        death_audio=None,
        on_death='silent_collapse',
        lore_quote=("Sterbliche, deren Bindung an die Welt fast "
                    "aufgelöst war. Shulavh hat sie als Mitleid an "
                    "Fäden geknüpft, damit sie nicht vergessen werden. "
                    "Aber sie sind nicht mehr ganz Mensch."),
    ),

    # --- Bestiarium #19: HOHLER SOHN ------------------------------------
    'hohler_sohn': dict(
        display_name='Hohler Sohn',
        base_type='lurker',
        archetype=_arch.Archetype.STALKER,
        tier='E', act=4,
        hp_mult=2.2, dmg_mult=1.7, speed_mult=1.1, radius_mult=1.1,
        color=( 90,  85,  95),       # gesichtslos, glatte Oberfläche
        glow=(190, 130, 200),
        windup_audio='aoe_windup',
        death_audio='whisper',
        on_death='silent_collapse',
        is_mini_boss=True,
        lore_quote=("Shulavh sammelt Kinder, die das Vergessen erfasst "
                    "hat. Sie macht sie zu ihren Söhnen. Sie liebt "
                    "sie ehrlich. Sie schickt sie trotzdem in den Tod."),
    ),

    # --- Bestiarium #20: MARK-KRIEGER -----------------------------------
    'mark_krieger': dict(
        display_name='Mark-Krieger',
        base_type='brute',
        archetype=_arch.Archetype.BRUTE,
        tier='M', act=4,
        hp_mult=2.0, dmg_mult=1.6, speed_mult=0.7, radius_mult=1.25,
        color=( 80, 110,  50),       # Wurzelholz
        glow=( 80, 220, 100),        # grüner Lebenssaft
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        lore_quote=("Aus den Wurzeln des toten Weltenbaums geformt. "
                    "Sie sind die letzte Verteidigung Shulavhs. Wer "
                    "sie tötet, schwächt das Wurzelgrab selbst."),
    ),

    # ============================================================
    # AKT 5 — DIE SPIEGELSTADT VELHARN (Bestiarium #21-25)
    # ============================================================
    # Lore-Bibel 4.1: Nheyras Stunden-Spiegel, Zeit-Anomalien,
    # Drei-Zeiten-Senatoren. Biome-Anker: astral.

    # --- Bestiarium #21: STUNDEN-WANDLER --------------------------------
    'stunden_wandler': dict(
        display_name='Stunden-Wandler',
        base_type='wraith',
        archetype=_arch.Archetype.STALKER,
        tier='E', act=5,
        hp_mult=1.3, dmg_mult=1.4, speed_mult=1.2, radius_mult=1.0,
        color=(170, 150, 200),       # glasgolden + Multi-Exposure
        glow=(220, 200, 255),
        windup_audio=None,
        death_audio='whisper',
        on_death='silent_collapse',
        spectral=True,
        lore_quote=("Bürger Velharns, die in Nheyras Stunden-Spiegel "
                    "zu lange gelebt haben. Sie sind nicht mehr in "
                    "einer Zeit zuhause."),
    ),

    # --- Bestiarium #22: SENATOR-PHANTOM (Mini-Boss) --------------------
    'senator_phantom': dict(
        display_name='Senator-Phantom',
        base_type='warlock',
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=5,
        hp_mult=3.2, dmg_mult=1.7, speed_mult=0.85, radius_mult=1.3,
        color=(200, 180, 130),       # drei Köpfe in Toga
        glow=(255, 220, 180),
        windup_audio='aoe_windup',
        death_audio='whisper',
        on_death='silent_collapse',
        is_mini_boss=True,
        spectral=True,
        lore_quote=("Drei Senatoren in einem Körper — vereint, weil "
                    "sie alle in derselben Sekunde starben, in drei "
                    "verschiedenen Zeitlinien."),
    ),

    # --- Bestiarium #23: GLASSCHERBEN-TÄNZERIN --------------------------
    'glasscherben_taenzerin': dict(
        display_name='Glasscherben-Tänzerin',
        base_type='salzgeist',
        archetype=_arch.Archetype.SKIRMISHER,
        tier='E', act=5,
        hp_mult=1.2, dmg_mult=1.4, speed_mult=1.35, radius_mult=0.9,
        color=(220, 220, 240),       # Glas-Reflexion
        glow=(250, 250, 255),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death='death_pop',
        bleed_buildup_bonus=1.4,
        lore_quote=("Eine der Tänzerinnen des Spiegelhofs. Sie tanzte "
                    "800 Jahre lang, weil niemand die Musik abstellte. "
                    "Jetzt ist sie der Tanz."),
    ),

    # --- Bestiarium #24: SICH-SELBST-SPIELENDE-SPIELER (Mini-Boss) ------
    'echo_zwilling': dict(
        display_name='Echo-Zwilling',
        base_type='berserker',
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=5,
        hp_mult=2.8, dmg_mult=1.6, speed_mult=1.0, radius_mult=1.0,
        color=(180, 180, 220),       # Spiegel-Reflexion des Spielers
        glow=(220, 220, 255),
        windup_audio='aoe_windup',
        death_audio=None,
        on_death='silent_collapse',
        is_mini_boss=True,
        lore_quote=("Eine Echo-Anomalie aus einer welkenden Welt, in "
                    "der der Spieler Im-Neshs Seite gewählt hat. "
                    "Dieser Spiegel-Spieler hat die Welt umgeschrieben. "
                    "Er kämpft gegen den Spieler, weil er glaubt, "
                    "der echte Spieler stört seine Realität."),
    ),

    # --- Bestiarium #25: SPIEGEL-HÜTER ----------------------------------
    'spiegel_hueter': dict(
        display_name='Spiegel-Hüter',
        base_type='brute',
        archetype=_arch.Archetype.GUARDIAN,
        tier='E', act=5,
        hp_mult=2.6, dmg_mult=1.5, speed_mult=0.75, radius_mult=1.3,
        color=(160, 170, 200),       # Spiegel-Glas-Tönung
        glow=(220, 230, 250),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death=None,
        lore_quote=("Wächter zwischen den Zeit-Schichten. Sie "
                    "spiegeln, weil sie keine eigene Identität mehr "
                    "haben."),
    ),

    # ============================================================
    # AKT 6 — DIE DREI WUNDEN (Bestiarium #26-29)
    # ============================================================
    # Lore-Bibel Teil 5: Drei-Wunden-Akt. Bosse repräsentieren die drei
    # bleibenden Wunden Velgrads (Salzwunde, Aschwunde, Hohlwunde) plus
    # die Anomaly-Add #29. Tier-3-Boss-Pool für höhere Dungeons.

    # --- Bestiarium #26: ERTRUNKENE KÖNIGIN (Salzwunden-Boss) -----------
    'ertrunkene_koenigin': dict(
        display_name='Die Ertrunkene Königin',
        base_type='warlock',           # Caster-Base, Cold-Affinität
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=6,
        hp_mult=4.5, dmg_mult=1.8, speed_mult=0.85, radius_mult=1.5,
        color=( 90, 130, 170),         # Tiefseewasser-Blau
        glow=(190, 220, 240),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='silent_collapse',
        is_mini_boss=False,
        spectral=False,
        lore_quote=("Sie war die Letzte Königin Velharns, ertränkt im "
                    "Krieg. Sie wachte am Boden der Salzwunde wieder "
                    "auf."),
    ),

    # --- Bestiarium #27: ECHO-DRACHE (Aschwunden-Boss) ------------------
    'echo_drache': dict(
        display_name='Der Echo-Drache',
        base_type='brute',             # Massive Base, Fire-Affinität
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=6,
        hp_mult=5.0, dmg_mult=2.0, speed_mult=0.75, radius_mult=1.8,
        color=( 50,  35,  30),         # versteinertes Asche-Schwarz
        glow=(255, 100,  40),          # brennende Augen
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='salt_explosion',     # Asche-Explosion beim Tod
        is_mini_boss=False,
        lore_quote=("Einer der drei letzten Drachen Velgrads. Er sah "
                    "Valsa fallen und versteinerte vor Trauer. Jetzt "
                    "ist er erwacht — vielleicht, weil das Vergessen "
                    "ihn rufen kommt."),
    ),

    # --- Bestiarium #28: DER NICHT-GOTT (Hohlwunden-Boss / Anomalie) ----
    'nicht_gott': dict(
        display_name='Der Nicht-Gott',
        base_type='wraith',            # Anomalie-Base, untyped Damage
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=6,
        hp_mult=4.0, dmg_mult=2.2, speed_mult=0.95, radius_mult=1.4,
        color=( 16,  16,  20),         # negativer Raum
        glow=( 80,  60, 100),          # nur Konturen leuchten
        windup_audio=None,             # Stille als Telegraph
        death_audio=None,
        on_death='silent_collapse',
        is_mini_boss=False,
        spectral=True,                 # sieht alles, „weiß" überall
        lore_quote=("Manche Theologen flüstern: Das ist der Siebte "
                    "Aspekt höchstpersönlich, in physischer Form. "
                    "Andere: Es ist nur ein Echo. Niemand weiß. "
                    "Niemand fragt."),
    ),

    # ============================================================
    # AKT-BOSSE aus WELT_AUFBAU.md Sektion 4 (Update #111)
    # Bestiarium hat keine eigenen Boss-Entries für Akt 2/4/5 (außer
    # senator_phantom als Mini-Boss). WELT_AUFBAU verlangt aber
    # voll-tier Bosse pro Akt — wir bauen sie hier als bestiary-Entries.
    # ============================================================

    # --- AKT 2: SENATOR-GEIST (Hauptboss Glasgoldene Ruinen) ------------
    # Verstärkte Echo-Senator-Variante (Bestiarium #6) mit Quotes-Phantom
    # + Goldstaub-Cloud + Senatoren-Adds (#8 Goldstaub-Diener als Phase 3).
    'senator_geist': dict(
        display_name='Senator-Geist Vorul',
        base_type='warlock',
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=2,
        hp_mult=3.8, dmg_mult=1.6, speed_mult=0.85, radius_mult=1.4,
        color=(230, 200, 130),       # Toga mit Goldstaub-Aura
        glow=(255, 230, 160),
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='silent_collapse',
        is_mini_boss=False,
        spectral=True,
        lore_quote=("Einer der 412 Senatoren der Glasgoldenen Liga. "
                    "Spricht die letzten 800 Jahre dieselben drei "
                    "Reden. Heute hört ihm zum ersten Mal jemand "
                    "wirklich zu."),
    ),

    # --- AKT 4: SHULAVH die FADEN-MUTTER (Hauptboss Wurzelgrab) ---------
    # Lore-Bibel Teil 6.6: einer der Sieben Aspekte. Multi-Phase mit
    # Choice-Outcome (Heilen vs. Bezwingen). Hier nur die Combat-Hülle —
    # die Choice-Mechanik kommt mit dem Quest-System (Akt-4-Main).
    'shulavh': dict(
        display_name='Shulavh, die Faden-Mutter',
        base_type='warlock',
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=4,
        hp_mult=4.2, dmg_mult=1.7, speed_mult=0.75, radius_mult=1.6,
        color=(110,  60,  90),       # tief-rot/Schmerzgewebe
        glow=(220, 100, 130),        # rote Fäden, pulsierend
        windup_audio='aoe_windup',
        death_audio='roar',
        on_death='silent_collapse',
        is_mini_boss=False,
        lore_quote=("Sie hat dich gewählt. Was auch immer du tust — "
                    "sie liebt dich. Selbst wenn sie dich zerreißt."),
    ),

    # --- AKT 5: VELHARN-TRIO (Hauptboss Spiegelstadt) -------------------
    # Drei-Zeiten-Variante des Senator-Phantom. 3 Köpfe, jede Phase
    # spricht ein anderer Senator aus einer anderen Zeit.
    'velharn_trio': dict(
        display_name='Velharn-Trio',
        base_type='warlock',
        archetype=_arch.Archetype.CHAMPION,
        tier='E', act=5,
        hp_mult=4.0, dmg_mult=1.7, speed_mult=0.85, radius_mult=1.5,
        color=(190, 180, 220),       # Stundenspiegel-Lavendel
        glow=(230, 220, 255),
        windup_audio='aoe_windup',
        death_audio='whisper',
        on_death='silent_collapse',
        is_mini_boss=False,
        spectral=True,
        lore_quote=("Drei Senatoren in einem Körper — vereint, weil "
                    "sie alle in derselben Sekunde starben, in drei "
                    "verschiedenen Zeitlinien."),
    ),

    # --- Bestiarium #29: NICHT-MANN (Anomaly-Add) ----------------------
    # Adds für #28 Nicht-Gott Phase 3. Nicht direkt als Boss spawnen,
    # sondern durch boss-encounter.spawn_adds-Hook.
    'nicht_mann': dict(
        display_name='Nicht-Mann',
        base_type='lurker',
        archetype=_arch.Archetype.STALKER,
        tier='E', act=6,
        hp_mult=1.0, dmg_mult=1.3, speed_mult=1.4, radius_mult=0.95,
        color=( 30,  25,  35),         # Schatten ohne Wesen
        glow=( 80,  60,  90),
        windup_audio=None,
        death_audio=None,              # zerfällt zu Stille
        on_death='silent_collapse',
        spectral=True,
        lore_quote=("Wesen, die nie hätten existieren sollen. Sie sind "
                    "die Lücken, die zurückbleiben, wenn die Welt "
                    "etwas vergisst."),
    ),
}


# ============================================================
# SPAWN-HELPER
# ============================================================
def spawn_bestiary_mob(game, key, x, y, wave=None):
    """Spawnt einen Bestiarium-Mob an (x, y) und gibt das Enemy-Objekt zurück.

    - Nutzt enemies.spawn_enemy mit dem fallback base_type
    - Wendet Multiplikatoren an
    - Setzt Color/Glow für Lore-Look
    - Hängt Archetyp-Felder an
    - Speichert bestiary-Metadaten unter `e.bestiary_key` / `e.lore_quote`
    """
    from . import enemies as _enemies
    entry = BESTIARY.get(key)
    if entry is None:
        raise KeyError(f"Unknown bestiary key: {key}")
    if wave is None:
        # Update #121: game.wave entfernt. Fallback auf player.level
        # (game.wave-getattr bleibt als Backward-Compat-Stub falls
        # zukünftige Atlas-Mechanik wave-State zurückbringt).
        wave = getattr(game, 'wave',
                        max(1, getattr(game.player, 'level', 1)))

    e = _enemies.spawn_enemy(entry['base_type'], x, y, wave, elite_chance=0.0)

    # Multiplikatoren
    e.hp_max = e.hp_max * entry['hp_mult']
    e.hp = e.hp_max
    e.dmg = e.dmg * entry['dmg_mult']
    e.speed = e.speed * entry['speed_mult']
    e.radius = int(e.radius * entry['radius_mult'])
    e.height = int(e.radius * 2.2)

    # Look
    e.color = entry['color']
    e.glow = entry['glow']

    # Bestiarium-Metadaten
    e.bestiary_key = key
    e.display_name = entry['display_name']
    e.lore_quote = entry['lore_quote']
    e.tier = entry['tier']
    e.act = entry['act']
    e.windup_audio = entry.get('windup_audio')
    e.death_audio = entry.get('death_audio')
    e.on_death_behavior = entry.get('on_death')

    # Sub-Flags
    if entry.get('spectral'):
        # Geist sieht durch Wände — sight muss requires_los=False sein
        from . import ai as _ai
        e.sight = _ai.SIGHT_PROFILES['spectral']
    if entry.get('is_mini_boss'):
        e.is_mini_boss = True
        e.boss_name = entry['display_name']

    # Archetyp + State-Machine
    _arch.apply_to_enemy(e, entry['archetype'])

    return e


def list_act(act):
    """Returnt alle Bestiarium-Keys eines Akts (für Spawn-Pools)."""
    return [k for k, v in BESTIARY.items() if v['act'] == act]


# ============================================================
# WAVE-SPAWN-INTEGRATION
# ============================================================
# Lore-Mapping: aktuelle Game-Biomes ↔ Bestiarium-Akte.
# Akt 1 = Salzküste → wir leihen das `crypt`-Biome (Startregion, atmospärisch
# verwandt: feucht, nebelig, melancholisch). Sobald `salt_coast` als eigenes
# Biome existiert, hier umtypen.
#
# Pro Biome: Liste der Bestiarium-Keys + Spawn-Wahrscheinlichkeit (0..1).
# Mini-Bosse (z.B. salzhueter_brut) gehören NICHT in Wave-Spawns —
# sie werden über Boss-Encounter getriggert (E-Block).
BESTIARY_BIOME_POOLS = {
    'crypt': {
        'chance': 0.40,
        'keys': ['salzgekreuzter', 'krustenkrabbe',
                 'ertrunkenes_echo', 'moewen_schwarm'],
    },
    'lava': {
        'chance': 0.50,
        'keys': ['asch_soldat', 'predigt_sprecher',
                 'klingenmesser', 'asch_wolf'],
        # tribunal_konstrukt bewusst NICHT in Wave-Spawn — Mini-Boss-Tier.
    },
    # Update #109: Akt 2/4/5 Biome-Pools (Lore: Glasgoldene Ruinen ↔ frost,
    # Wurzelgrab ↔ swamp, Spiegelstadt Velharn ↔ astral).
    'frost': {
        'chance': 0.50,
        'keys': ['echo_senator', 'glasgolden_waechter',
                 'goldstaub_diener', 'spiegel_stalker',
                 'verfallener_magister'],
    },
    'swamp': {
        'chance': 0.55,
        'keys': ['knochenwitwe', 'wurzelspinne',
                 'faden_gebundener', 'mark_krieger'],
        # hohler_sohn bewusst NICHT — Mini-Boss-Tier.
    },
    'astral': {
        'chance': 0.55,
        'keys': ['stunden_wandler', 'glasscherben_taenzerin',
                 'spiegel_hueter'],
        # senator_phantom + echo_zwilling bewusst NICHT — Mini-Boss-Tier.
    },
}


def maybe_spawn_bestiary_for_biome(game, biome, x, y, wave=None):
    """Versucht, statt einer generischen Wave einen Bestiarium-Mob zu spawnen.

    Returns das Enemy-Objekt oder None (fallback auf alten Spawn-Pfad).
    """
    import random as _r
    cfg = BESTIARY_BIOME_POOLS.get(biome)
    if cfg is None:
        return None
    if _r.random() >= cfg['chance']:
        return None
    key = _r.choice(cfg['keys'])
    return spawn_bestiary_mob(game, key, x, y, wave=wave)
