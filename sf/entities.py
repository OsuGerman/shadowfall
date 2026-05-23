"""Datentyp-Klassen für Spieler, Projektile, Partikel etc."""

import math
import random
from pygame.math import Vector2

from .constants import CLASSES, SLOTS


class Player:
    def __init__(self, cls_key='warrior'):
        c = CLASSES[cls_key]
        self.cls = cls_key
        self.pos = Vector2(0, 0)
        self.target = Vector2(0, 0)
        self.moving = False
        self.radius = 18
        self.base_speed = c['speed']
        self.hp_max_base = c['hp']
        self.hp = float(c['hp'])
        self.mp_max_base = c['mp']
        self.mp = float(c['mp'])
        self.hp_regen_base = c['hp_regen']
        self.mp_regen_base = c['mp_regen']
        self.base_damage = c['damage']

        self.level = 1
        self.xp = 0
        self.xp_to_next = 30
        self.skill_points = 0
        self.attr_points = 0

        # Attribute (STR/INT/DEX)
        self.strength = c['strength']
        self.intellect = c['intellect']
        self.dexterity = c['dexterity']

        self.facing = 0.0
        self.walk_phase = 0.0
        self.attack_cd = 0.0
        self.attack_target = None
        self.skill_cd = {'fireball': 0.0, 'lightning': 0.0,
                         'heal': 0.0, 'frostnova': 0.0}
        self.invuln = 0.0
        self.dodge = 0.0
        self.dodge_dir = Vector2(0, 0)
        self.dodge_cd = 0.0

        # Effekte
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.shield = 0.0  # absorbierte HP
        self.status = {}   # effect_key -> {'stacks', 'time_left', 'next_tick'}
        self.vampire_charges = 0   # aus Heal-Rune
        self.regen_buff = 0.0      # Heilung-über-Zeit
        self.regen_buff_left = 0.0

        # Inventar & Ausrüstung
        self.inventory = [None] * 24
        self.equipment = {s: None for s in SLOTS}
        # L-08 (Update #71): Weapon-Swap — zweites Weapon/Offhand-Set
        # speichert Reserve-Items.  `active_weapon_set` cycelt zwischen 'a'
        # und 'b' bei V-Taste.  Bei Swap werden weapon+offhand mit den
        # Storage-Feldern getauscht.
        self.weapon_set_b = {'weapon': None, 'offhand': None}
        self.active_weapon_set = 'a'

        # Skill-Tree
        self.tree = {}  # node_id -> level

        # Runen: skill_key -> rune_id
        self.runes = {}

        # Edelsteine (Inventar als separate Liste)
        self.gems = []  # list[str] (gem_type)

        # Skill-Levels (PoE-artig)
        self.skill_levels = {'melee': 1, 'fireball': 1, 'lightning': 1,
                             'heal': 1, 'frostnova': 1}
        self.skill_xp = {'melee': 0, 'fireball': 0, 'lightning': 0,
                         'heal': 0, 'frostnova': 0}

        # Klassen-Talentbaum (separat vom universellen)
        self.class_tree = {}
        self.class_points = 0  # 1 pro Stufe

        # Aktive Aura
        self.aura = None  # 'wachsamkeit' | 'macht' | 'praezision' | 'entschlossenheit' | None

        # Persistente Truhe (Stash) - im Town
        self.stash = [None] * 48

        # Dungeon-Tracking
        self.completed_dungeons = set()  # dungeon_id -> completed once
        self.deaths_in_dungeon = 0

        # Loot-Filter
        self.loot_filter = 'common'  # 'off' | 'common' (skip common) | 'magic' (skip <rare)

        # Tod-Animation
        self.dying = False
        self.death_timer = 0.0

        # Combo-Buff
        self.combo_buff_left = 0.0
        # Levelup-Invuln-Buff
        self.levelup_invuln = 0.0

        # PoE2-Style Skill-Gems (welche Skills sind freigeschaltet?)
        # Jede Klasse startet mit melee + 1 Magie-Skill
        # Update #23: Klassen-spezifische Starter-Skills aus CLASS_KEYMAP.
        # Jede Klasse startet mit melee + ihren ersten 3 Hotkey-Skills
        # (Q + W + E). R und 1 werden über Gemcutter freigeschaltet.
        try:
            from .skills import default_unlocked_for_class
            cls_skills = default_unlocked_for_class(cls_key)
        except Exception:
            cls_skills = {'fireball'}
        self.unlocked_skills = {'melee'} | cls_skills

        # Gold + Spezial-Währungen
        self.gold = 50
        self.souls = 0           # von Bossen, für Talent-Punkte
        self.shards = 0          # von Eliten, für Crafting
        self.lore_fragments = 0  # für Lore-Tafeln freischalten
        self.height = 46

        # PLAN J-Block: Gem-/Support-System.
        #   - `skill_supports[skill_id]` = list of support_ids (max 5 pro Skill).
        #   - `unlocked_supports` = set of support_ids, die der Player besitzt.
        #   - `spirit_max` = Basis 100 (Lore-Bibel 5.2), erhöhbar via Tree.
        #   - `spirit_reserved` = Sum der Reservation aller Persistent-Gems.
        #   - `uncut_gem_levels` = wieviele Uncut-Gems pro Level der Player hat
        #     (z.B. {7: 3, 11: 1} = 3 Uncut Lvl-7, 1 Uncut Lvl-11)
        self.skill_supports = {}
        self.unlocked_supports = set()
        self.spirit_max = 100
        self.spirit_reserved = 0
        # PLAN J-10: Uncut Memory-Shards (Lore: rohe Tropfen aus dem
        # Glasgoldenen Zeitalter). Otreth graviert sie zu Skill-Gems.
        # Default: 2 Uncut Lvl 1 für den Start (Tutorial).
        self.uncut_gems = {1: 2}
        # Skill-Gem-Levels (1..20). Default level=1 für alle freigeschalteten.
        self.gem_levels = {}
        # PLAN W-Block / Lore-Bibel 6.4 — Mahnmal-Marken I..VII als
        # Currency (eine pro Aspekt). Salzhüter dropt VII, Eisenwächter-
        # Mobs droppen I, andere Bosse je Aspekt-Lineage.
        self.mahnmal_marken = {1: 0, 2: 0, 3: 0, 4: 0,
                                5: 0, 6: 0, 7: 0}
        # Update #95: KOMBINIERTE Vital-Flasche (User-Wunsch).
        # Ersetzt Update #82 Salz-Trinkflasche + Mahnmal-Wasser.
        # Eine Flasche heilt sowohl HP als auch MP gleichzeitig.
        # Lore: Vereinigter Marrowport-Spiegelhof-Trank — Mahnmal-Gilde
        # nennt es „Atemzug-Phiole". Beide Aspekte (Sole + Echo) in
        # einer einzigen Tinktur.
        self.flasks = {
            'vital': {
                'name': 'Atemzug-Phiole',
                'charges': 4.0,
                'max': 4,
                'hp_pct': 0.35,        # +35 % HP-Max
                'mp_pct': 0.45,        # +45 % MP-Max
                'instant_frac': 0.50,  # 50 % davon sofort, Rest HoT
                'duration': 2.5,
                'color': (220, 130, 180),  # rosé-magenta — vereinigt rot+blau
                'lore': 'Mahnmal-Tinktur — Sole und Echo, ein Atemzug.',
            },
        }
        # Aktive Flask-Effekte (heilen über Zeit): list of dicts
        # {'kind': 'vital', 'remaining': sec, 'hp_per_sec': float,
        #  'mp_per_sec': float}
        self.flask_effects = []
        # Update #80 W-12: Mahnmal-Schrein-Blessings.
        # Lore-Bibel 6.4 + Aspekt-Pakt: Marken werden am zentralen
        # Mahnmal-Stele in Brassweir verzehrt. Jeder Aspekt gewährt
        # einen permanenten Stat-Bonus pro Stack (max 5).
        # Mapping (1..7): Kharn / Nheyra / Ousen / Valsa /
        #                  Im-Nesh / Shulavh / Der Siebte
        self.mahnmal_blessings = {1: 0, 2: 0, 3: 0, 4: 0,
                                    5: 0, 6: 0, 7: 0}
        # Update #117 (WELT_AUFBAU 6.1): Faction-Rep pro Velgrad-Fraktion.
        # Werte werden über `faction.grant_rep(player, key, amount)` gesetzt;
        # geclampt auf [-200, 200].  Keys aus sf/faction.py FACTIONS.
        self.faction_rep = {}
        # Update #75: H-17 Respec via Orb-of-Regret (POE2-Style).
        # Lore: Erinnerungs-Sphäre, gegerbt aus Spiegelhof-Reflexionen —
        # erlaubt das Auslöschen einer einzigen erinnerten Lektion.
        # Drop: ~8% bei Elite-Kills, garantiert von Akt-Bossen.
        self.orbs_of_regret = 2
        # Update #32: Progression-Tracker (sichtbar im Memorial-Panel)
        self.prog_kills_total = 0
        self.prog_kills_boss = 0
        self.prog_kills_mini = 0
        self.prog_kills_elite = 0
        self.prog_dungeons_cleared = set()
        self.prog_lore_read = set()
        self.prog_bestiary_seen = set()
        self.prog_altars_used = 0
        self.prog_runes_used = 0
        self.prog_crits_dealt = 0
        self.prog_distance_walked = 0.0
        self.prog_play_time_s = 0.0
        # Class-Mastery-Rank (0-9, basierend auf Klassen-Aktivitäten)
        self.class_mastery_xp = 0
        # PLAN: Dodge-Charges (G-09). Default 2 Charges, regen 4s pro.
        self.dodge_charges = 2
        self.dodge_charges_max = 2
        self.dodge_regen_t = 0.0
        # PLAN: Salzwunde-Quest-Akt-1-Story-Counter (Korven-Briefings).
        self.akt1_intro_seen = False
        # Update #131 (Y-01): First-Run-Tutorial-Schritt-Tracking.  Wird
        # gespeichert + per Save persistiert, damit ein neuer Char das
        # Tutorial bekommt aber ein erfahrener nicht wieder.
        self.tutorial_step = 0       # 0 = nicht begonnen, n = Schritt n
        self.tutorial_done = False
        # Update #131 (Y-02): Mechanik-Hint-Set — pro Mechanik max 1×
        # angezeigt.  Persist über Save.
        self.seen_mech_hints = set()
        # Update #43: Skill-Keybindings (User: „Skills die man dabei hat ...
        # soll man sich selber auf seine Tasten legen können").
        # Map pygame.key → skill_id. Initialisiert aus CLASS_KEYMAP, kann
        # vom Spieler via Skill-Menü (G) per Rebind-Modus überschrieben werden.
        # Default-Slots: Q=index0, W=index1, E=index2, R=index3, 1=index4.
        try:
            import pygame as _pg
            from .skills import class_keymap as _ckm
            _pool = _ckm(cls_key)
            _slots = [_pg.K_q, _pg.K_w, _pg.K_e, _pg.K_r, _pg.K_1]
            self.skill_bindings = {
                _slots[i]: _pool[i] for i in range(min(len(_slots), len(_pool)))
            }
        except Exception:
            self.skill_bindings = {}


class Enemy:
    def __init__(self, type_key, x, y, wave, template, elite=False, affix=None):
        self.type_key = type_key
        self.color = template['color']
        self.glow = template['glow']
        # Update #95: Schwierigkeit erhöht (User-Wunsch „Gegner viel zu leicht").
        # HP-Scaling: +28 %/Wave (vorher +18 %).
        # DMG-Scaling: +20 %/Wave (vorher +12 %).
        # Base-DMG-Multiplier: ×1.30 — alle Mobs schlagen 30 % stärker.
        # Base-HP-Multiplier: ×1.20 — alle Mobs halten 20 % mehr aus.
        scale_hp = 1 + (wave - 1) * 0.28
        scale_dmg = 1 + (wave - 1) * 0.20
        self.hp_max = template['hp'] * scale_hp * 1.20
        self.dmg = template['dmg'] * scale_dmg * 1.30
        self.speed = template['speed']
        self.radius = template['radius']
        self.xp = template['xp']
        self.gold_range = template['gold']
        self.att_range = template['att_range']
        self.att_cd = template['att_cd']
        self.ranged = template.get('ranged', False)

        # Elite-Skalierung
        self.elite = elite
        self.affix = affix  # 'fast' | 'fire' | 'vampiric' | 'explosive' | None
        if elite:
            self.hp_max *= 2.2
            self.dmg *= 1.4
            self.radius = int(self.radius * 1.25)
            self.xp = int(self.xp * 2.5)
            self.gold_range = (self.gold_range[0] * 2, self.gold_range[1] * 3)
        if affix == 'fast':
            self.speed *= 1.5
        elif affix == 'fire':
            self.dmg *= 1.15

        self.hp = self.hp_max
        self.pos = Vector2(x, y)
        self.attack_timer = 0.0
        self.hit_flash = 0.0
        self.wobble = random.uniform(0, math.tau)
        self.slow_timer = 0.0
        self.slow_factor = 1.0
        self.status = {}    # effect_key -> {'stacks', 'time_left', 'next_tick'}
        self.stun_timer = 0.0
        # Update #34: Stun-Buildup-System (L-04)
        # Akkumuliert mit jedem Schlag; bei 100 → Heavy-Stun.
        # Decays bei Idle. Maces/Phys-Skills bauen schneller auf.
        self.stun_buildup = 0.0
        self.stun_buildup_max = 100.0
        self.heavy_stunned = False  # Phase-1: visible "GROGGY"-Marker
        # Update #40: Attack-Animation-State
        # phase: 'idle' | 'windup' | 'swing' | 'recover'
        self.atk_phase = 'idle'
        self.atk_phase_t = 0.0
        self.atk_target_pos = None  # Vector2: wohin gerichtet
        self.walk_phase = random.uniform(0, math.tau)
        self.dying = False
        self.death_timer = 0.0
        self.height = int(self.radius * 2.2)
        # Pathfinding
        self.path = None         # list of (cx, cy) cells
        self.path_age = 0.0      # Sekunden seit letztem Repath
        self.stuck_timer = 0.0   # Falls Bewegung blockiert

        # Schadens-Resistenzen (0.0 - 0.75)
        self.resistances = dict(template.get('resistances', {}))
        # Standard-Schwächen pro Typ (kann von Template überschrieben werden)
        # Demons: feuerresistent. Frostlord: kälteresistent. Etc.
        if not self.resistances:
            if type_key == 'demon':
                self.resistances = {'fire': 0.6, 'physical': 0.1}
            elif type_key == 'wraith':
                self.resistances = {'physical': 0.3, 'cold': 0.3}
            elif type_key == 'skeleton':
                self.resistances = {'physical': 0.2, 'poison': 0.5}
            elif type_key == 'brute':
                self.resistances = {'physical': 0.3}
            elif type_key == 'shaman':
                self.resistances = {'lightning': 0.5}
            elif type_key == 'archer':
                self.resistances = {'physical': 0.1}
            else:
                self.resistances = {}

        # Boss-Spezifika (None für normale Gegner)
        self.is_boss = False
        self.is_mini_boss = False
        self.boss_name = None
        self.boss_title = ''
        self.boss_ability_cd = 0.0
        self.boss_kind = None
        self.boss_phase = 1
        self.phase2_triggered = False
        self.shield = 0.0
        self.shield_max = 0.0
        self.heal_used = False  # Boss-Heal-Once
        # Charged-Attack: aktiviert wenn boss eine 'big' attack ankündigt
        self.charged_attack = None  # None oder {'target_pos', 'timer', 'radius', 'damage'}
        self.charge_cd = 6.0  # countdown bis nächste Charged-Attack
        # Hit-Recoil (visueller Knockback)
        self.recoil = Vector2(0, 0)

        # ----------------------------------------------------------------
        # PLAN D/F — KI-State-Machine + Archetypen-Felder.
        # Default-OFF: alte Mobs verhalten sich wie bisher.
        # bestiary.spawn_bestiary_mob() opted das Wesen über
        # archetypes.apply_to_enemy() ein und füllt diese Felder.
        # ----------------------------------------------------------------
        self.uses_state_machine = False
        self.archetype = None
        self.sight = None
        self.hearing = None
        self.engage_mode = 'melee'
        self.pack_alert_radius_px = 0
        self.prefers_distance_px = 0
        self.sticky_aggro = False
        self.priority_kill = False
        # Lore-/Bestiarium-Metadaten (optional)
        self.bestiary_key = None
        self.display_name = None
        self.lore_quote = None
        self.tier = None
        self.act = None
        self.windup_audio = None
        self.death_audio = None
        self.on_death_behavior = None
        # State-Machine-Felder (Default-Init; tick_ai_state setzt sie neu)
        self.ai_state = None
        self.ai_state_t = 0.0
        self.last_known_player_pos = None
        self.ai_lost_sight_t = 0.0
        self.ai_sight_tick_phase = 0
        # Facing (0° = rechts, 90° = unten in Bildschirm-Koordinaten)
        self.facing_deg = 90.0
        # Patrol-Konfiguration (None = kein Patrouille → IDLE-Default)
        self.patrol_pattern = None
        self.patrol_waypoints = None
        self.patrol_index = 0
        self.spawn_pos = Vector2(x, y)


class Projectile:
    def __init__(self, x, y, vx, vy, damage, kind='fireball',
                 friendly=True, radius=9, life=1.2, extra=None):
        self.pos = Vector2(x, y)
        self.vel = Vector2(vx, vy)
        self.damage = damage
        self.kind = kind
        self.friendly = friendly
        self.radius = radius
        self.life = life
        self.age = 0.0
        self.hit_ids = set()
        self.extra = extra or {}


class Loot:
    def __init__(self, x, y, gold=0, item=None, vital_orb=False,
                  vital_amount=0):
        self.pos = Vector2(x, y)
        self.gold = gold
        self.item = item
        self.bob = random.uniform(0, math.tau)
        # Update #96: Vital-Orb-Pickups (Heal+Mana) — Boss-/Elite-Drops.
        self.vital_orb = vital_orb
        self.vital_amount = vital_amount
        if vital_orb:
            self.kind = 'vital_orb'
            self.color = (220, 130, 180)   # rosé wie die Phiole
        elif item is not None:
            self.kind = 'item'
            from .constants import RARITY_COLOR
            self.color = RARITY_COLOR[item.rarity]
        else:
            self.kind = 'gold'
            from .constants import GOLD
            self.color = GOLD


class Particle:
    def __init__(self, x, y, vx, vy, color, life, size, gravity=0,
                 layer='gameplay'):
        self.pos = Vector2(x, y)
        self.vel = Vector2(vx, vy)
        self.color = color
        self.life = life
        self.age = 0.0
        self.size = size
        self.gravity = gravity
        # Particle-Layer (siehe effects.ParticleLayer): 'ambient' | 'gameplay'
        # | 'telegraph' | 'ui_overlay'. Default GAMEPLAY = Hit-Feedback,
        # nicht cullable. Ambient wird via Settings/Dynamic-Cull reduziert.
        self.layer = layer

    def reset(self, x, y, vx, vy, color, life, size, gravity=0,
              layer='gameplay'):
        """J-13 (Update #64): Object-Pool-Reuse — vermeidet Allocation."""
        self.pos.x = x
        self.pos.y = y
        self.vel.x = vx
        self.vel.y = vy
        self.color = color
        self.life = life
        self.age = 0.0
        self.size = size
        self.gravity = gravity
        self.layer = layer
        return self


class Floater:
    def __init__(self, x, y, text, color, *, crit=False, heal=False,
                  dot=False, big=False, life=0.9):
        self.pos = Vector2(x, y)
        self.text = str(text)
        self.color = color
        self.life = life
        self.age = 0.0
        self.vy = -50.0
        # PLAN G-10: Damage-Number-Varianten.
        # crit → Pop-Scale + Crit-Outline; heal → Grün; dot → halbe Alpha.
        self.big = big or crit
        self.crit = crit
        self.heal = heal
        self.dot = dot


class Decal:
    """Boden-Decal für AoE-Telegraphs (Briefing Teil C.3 / PLAN C-05, C-07).

    kind: siehe effects.DECAL_KIND — bestimmt die Outline-Farbe (Rot=tödlich,
    Orange=DoT, Gelb=CC, Lila=Chaos, Cyan=Buff).
    windup: Wind-Up-Dauer in Sekunden bis zur Aktivierung (Telegraph).
    lifetime: Dauer NACH der Aktivierung, in der der Decal sichtbar bleibt
        (z.B. brennender Boden hält Lifetime, Boss-Slam = 0).
    aerial: True für Skyfall-AoE (Comet) — fügt Schatten + wachsenden
        Stern-Riss hinzu.
    on_activate: Callback game→None, der beim Trigger gefeuert wird
        (Damage-Application, Particles, ...). Kann None sein für reine VFX.
    """
    def __init__(self, x, y, radius, kind='deadly', windup=0.8, lifetime=0.0,
                 aerial=False, on_activate=None, source=None):
        self.pos = Vector2(x, y)
        self.radius = float(radius)
        self.kind = kind
        self.windup = float(windup)
        self.lifetime = float(lifetime)
        self.aerial = bool(aerial)
        self.on_activate = on_activate
        self.source = source
        self.age = 0.0
        self.activated = False


class LightningBolt:
    def __init__(self, x1, y1, x2, y2):
        segs = 8
        self.points = [(x1, y1)]
        for i in range(1, segs):
            t = i / segs
            self.points.append((
                x1 + (x2 - x1) * t + random.uniform(-12, 12),
                y1 + (y2 - y1) * t + random.uniform(-12, 12),
            ))
        self.points.append((x2, y2))
        self.life = 0.2
        self.age = 0.0


class Decor:
    def __init__(self, x, y, kind, rot=0.0, size=60, shade=0.1, collide_radius=0):
        self.x = x
        self.y = y
        self.kind = kind
        self.rot = rot
        self.size = size
        self.shade = shade
        # >0 = blockt Spieler-/Gegnerbewegung (für Häuser, Säulen, etc.)
        self.collide_radius = collide_radius


class Portal:
    def __init__(self, x, y, biome):
        self.pos = Vector2(x, y)
        self.biome = biome
        self.bob = 0.0


class NPC:
    """Stadt-NPC: Händler, Truhen-Wächter, etc."""
    def __init__(self, x, y, kind, name, color):
        self.pos = Vector2(x, y)
        self.kind = kind   # 'vendor' | 'stash' | 'mystic'
        self.name = name
        self.color = color
        self.bob = random.uniform(0, math.tau)


class DungeonPortal:
    """Portal in der Stadt, das einen bestimmten Dungeon öffnet."""
    def __init__(self, x, y, dungeon_id):
        self.pos = Vector2(x, y)
        self.dungeon_id = dungeon_id
        self.bob = 0.0


class OutpostPortal:
    """Portal in Brassweir oder in einem Outpost, das zu einem anderen
    Outpost (oder zurück nach Brassweir) führt.

    `outpost_key` = Ziel-Outpost-Key aus sf/outposts.py:OUTPOSTS, oder
    der Sentinel 'brassweir' für den Rückweg.
    """
    def __init__(self, x, y, outpost_key, label=None):
        self.pos = Vector2(x, y)
        self.outpost_key = outpost_key
        self.label = label
        self.bob = 0.0
