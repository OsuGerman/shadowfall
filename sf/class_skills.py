"""Klassen-Signature-Skills als SkillGem-Definitionen (PLAN K-Block).

Pro Klasse eine Registry von SkillGem-Instanzen, die im J-Block-Modul
konsumiert werden können. Erfüllt das Briefing Teil 2 (Klassen-Skills)
mit den passenden Tags aus J-02.

Lore-Anker: Velgrad-Klassen ↔ Fraktionen (Lore-Bibel Teil 7):
  - warrior → Eisenwächter (Kharn-Lineage)
  - monk    → Stille Schritte
  - sorceress → Funkengeborene (Valsa-Berührt)
  - witch   → Knochenwitwen (Shulavh-Berührt)
  - ranger  → Saatträgerin (Wilde Lineage)
  - mercenary → Mahnmal-Söldner (Korven-Vor-Lineage)
  - huntress → Speerschwestern (Shulavh-Lineage)
  - druid   → Wandelnde (Drei-Tiere-Lineage)

Skill-Definitionen sind data-only — Cast-Implementation kommt iterativ.
Bestehende cast_*-Funktionen in skills.py funktionieren weiterhin.
"""

from .gems import SkillGem, Tag


# ============================================================
# K-01 — WARRIOR (Eisenwächter / Mace-Brawler)
# ============================================================
WARRIOR_SKILLS = {
    'boneshatter': SkillGem(
        id='boneshatter', name='Boneshatter', key='1',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.PHYSICAL, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=8, cd=0.3, cast_time=0.5, base_damage=60,
        desc='Nahkampf-Strike, akkumuliert Stun. '
             'Explosion bei Heavy-Stunned-Targets.',
        icon='spear', attr_req={'strength': 10},
    ),
    'earthquake': SkillGem(
        id='earthquake', name='Earthquake', key='2',
        tags={Tag.ATTACK, Tag.AOE, Tag.SLAM, Tag.PHYSICAL, Tag.DURATION,
              Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=3.0, cast_time=1.2, base_damage=120,
        desc='Slam mit Aftershock-AoE nach 1.2 s.',
        icon='quake', attr_req={'strength': 16},
    ),
    'rolling_slam': SkillGem(
        id='rolling_slam', name='Rolling Slam', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.SLAM, Tag.PHYSICAL, Tag.TRAVEL},
        damage_type=Tag.PHYSICAL,
        mana=18, cd=2.5, cast_time=0.9, base_damage=80,
        desc='Slam, der nach vorne rollt und mehrfach trifft.',
        icon='quake', attr_req={'strength': 14},
    ),
    'sunder': SkillGem(
        id='sunder', name='Sunder', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.SLAM, Tag.PHYSICAL, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=22, cd=3.0, cast_time=1.0, base_damage=110,
        desc='Slam, sendet AoE-Welle, Payoff gegen Heavy-Stunned.',
        icon='quake', attr_req={'strength': 18},
    ),
    'earthshatter': SkillGem(
        id='earthshatter', name='Earthshatter', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.SLAM, Tag.PHYSICAL, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=28, cd=4.0, cast_time=1.4, base_damage=140,
        desc='Slam, treibt Spike-Reihen aus dem Boden, '
             'danach Detonations-Slam.',
        icon='quake', attr_req={'strength': 22},
    ),
    'leap_slam': SkillGem(
        id='leap_slam', name='Leap Slam', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.SLAM, Tag.PHYSICAL, Tag.TRAVEL,
              Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=5.0, cast_time=0.6, base_damage=95,
        desc='Sprung-Mobility-Slam mit Payoff-Schaden.',
        icon='quake', attr_req={'strength': 12},
    ),
    'shield_charge': SkillGem(
        id='shield_charge', name='Shield Charge', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.CHANNELING, Tag.TRAVEL,
              Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=15, cd=3.5, cast_time=0.4, base_damage=55,
        desc='Channeling-Travel, Schild voran, Knockback.',
        icon='quake', attr_req={'strength': 14},
    ),
    'perfect_strike': SkillGem(
        id='perfect_strike', name='Perfect Strike', key='',
        tags={Tag.ATTACK, Tag.STRIKE, Tag.CHANNELING, Tag.FIRE,
              Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=14, cd=1.2, cast_time=1.0, base_damage=80,
        desc='Channeling-Strike, Timing-Window für massiven Crit-Bonus.',
        icon='fire', attr_req={'strength': 14},
    ),
    'molten_blast': SkillGem(
        id='molten_blast', name='Molten Blast', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.PROJECTILE, Tag.FIRE},
        damage_type=Tag.FIRE,
        mana=18, cd=1.5, cast_time=0.6, base_damage=70,
        desc='Projektil-AoE, Fire.',
        icon='fire', attr_req={'strength': 12, 'intellect': 8},
    ),
    'volcanic_fissure': SkillGem(
        id='volcanic_fissure', name='Volcanic Fissure', key='',
        tags={Tag.ATTACK, Tag.SLAM, Tag.FIRE, Tag.DURATION, Tag.PHYSICAL},
        damage_type=Tag.FIRE,
        mana=26, cd=4.0, cast_time=1.1, base_damage=100,
        desc='Slam mit Lava-Riss, Fire-DoT.',
        icon='quake', attr_req={'strength': 16},
    ),
    'resonating_shield': SkillGem(
        id='resonating_shield', name='Resonating Shield', key='',
        tags={Tag.CHANNELING, Tag.BUFF, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=0.0, cast_time=0.0, base_damage=0,
        desc='Channeling-Buff, akkumuliert Power, dann Release.',
        icon='cross', attr_req={'strength': 12},
    ),
    'infernal_cry': SkillGem(
        id='infernal_cry', name='Infernal Cry', key='',
        tags={Tag.WARCRY, Tag.AOE, Tag.TRIGGER, Tag.FIRE, Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=20, cd=10.0, cast_time=0.4, base_damage=40,
        desc='Warcry: AoE-Buff/Debuff, Trigger-Tag.',
        icon='fire', attr_req={'strength': 18},
    ),
    'magma_barrier': SkillGem(
        id='magma_barrier', name='Magma Barrier', key='',
        tags={Tag.BUFF, Tag.PERSISTENT, Tag.FIRE, Tag.AURA},
        damage_type=Tag.FIRE,
        mana=0, spirit=30, cd=0.0, cast_time=0.5, base_damage=0,
        desc='Persistent Buff, der reflektives Fire-AoE bei Treffer auslöst.',
        icon='fire', attr_req={'strength': 16},
    ),
}


# ============================================================
# K-02 — MONK (Stille Schritte / Quarterstaff-Elementalist)
# ============================================================
MONK_SKILLS = {
    'tempest_bell': SkillGem(
        id='tempest_bell', name='Tempest Bell', key='1',
        tags={Tag.ATTACK, Tag.TRIGGER, Tag.LIGHTNING, Tag.NOVA,
              Tag.QUARTERSTAFF},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=2.0, cast_time=0.5, base_damage=50,
        desc='Beschwört Glocke, die durch eigene Treffer Sound-Wellen '
             'abgibt (Wind+Lightning).',
        icon='spark', attr_req={'dexterity': 14, 'intellect': 14},
    ),
    'killing_palm': SkillGem(
        id='killing_palm', name='Killing Palm', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=0.4, cast_time=0.3, base_damage=70,
        desc='Execute-Strike, Bonus gegen Low-HP, generiert Power Charges.',
        icon='spear', attr_req={'dexterity': 12},
    ),
    'glacial_cascade': SkillGem(
        id='glacial_cascade', name='Glacial Cascade', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.COLD},
        damage_type=Tag.COLD,
        mana=22, cd=2.5, cast_time=0.9, base_damage=80,
        desc='Eis-Spike-Linie, Cold AoE.',
        icon='nova', attr_req={'intellect': 16},
    ),
    'charged_staff': SkillGem(
        id='charged_staff', name='Charged Staff', key='',
        tags={Tag.CHANNELING, Tag.BUFF, Tag.LIGHTNING, Tag.QUARTERSTAFF},
        damage_type=Tag.LIGHTNING,
        mana=12, cd=0.0, cast_time=0.0, base_damage=0,
        desc='Channeling, lädt Stab mit Lightning auf, '
             'nächste Treffer explodieren.',
        icon='spark', attr_req={'dexterity': 12, 'intellect': 14},
    ),
    'falling_thunder': SkillGem(
        id='falling_thunder', name='Falling Thunder', key='',
        tags={Tag.ATTACK, Tag.AOE, Tag.TRAVEL, Tag.LIGHTNING},
        damage_type=Tag.LIGHTNING,
        mana=24, cd=4.0, cast_time=0.7, base_damage=110,
        desc='Sprung mit Lightning-Schlag aus der Luft.',
        icon='spark', attr_req={'dexterity': 14},
    ),
    'tempest_flurry': SkillGem(
        id='tempest_flurry', name='Tempest Flurry', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.AOE, Tag.LIGHTNING,
              Tag.QUARTERSTAFF, Tag.CHANNELING},
        damage_type=Tag.LIGHTNING,
        mana=14, cd=0.8, cast_time=0.4, base_damage=40,
        desc='Multi-Hit Whirlwind aus Lightning/Wind.',
        icon='spark', attr_req={'dexterity': 16},
    ),
    'storm_wave': SkillGem(
        id='storm_wave', name='Storm Wave', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.LIGHTNING, Tag.PROJECTILE},
        damage_type=Tag.LIGHTNING,
        mana=20, cd=1.5, cast_time=0.7, base_damage=75,
        desc='Welle aus Donner und Wind.',
        icon='spark', attr_req={'intellect': 14},
    ),
    'ice_strike': SkillGem(
        id='ice_strike', name='Ice Strike', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.COLD, Tag.QUARTERSTAFF},
        damage_type=Tag.COLD,
        mana=10, cd=0.4, cast_time=0.3, base_damage=55,
        desc='Frost-Strike, baut Freeze-Buildup.',
        icon='nova', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'flicker_strike': SkillGem(
        id='flicker_strike', name='Flicker Strike', key='',
        tags={Tag.ATTACK, Tag.STRIKE, Tag.TRAVEL, Tag.PHYSICAL,
              Tag.QUARTERSTAFF},
        damage_type=Tag.PHYSICAL,
        mana=8, cd=0.0, cast_time=0.2, base_damage=80,
        desc='Teleport-Strike, verbraucht Power/Frenzy-Charges.',
        icon='blink', attr_req={'dexterity': 18},
    ),
}


# ============================================================
# K-03 — SORCERESS (Funkengeborene / Element-Casterin)
# ============================================================
SORCERESS_SKILLS = {
    'fireball': SkillGem(
        id='fireball', name='Fireball', key='Q',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.FIRE, Tag.AOE},
        damage_type=Tag.FIRE,
        mana=15, cd=0.5, cast_time=0.5, base_damage=80,
        desc='Projektil, Explosion bei Aufprall, Ignite.',
        icon='fire', attr_req={'intellect': 8},
    ),
    'spark': SkillGem(
        id='spark', name='Spark', key='2',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.LIGHTNING},
        damage_type=Tag.LIGHTNING,
        mana=12, cd=0.4, cast_time=0.3, base_damage=45,
        desc='Lightning-Projektil-Ricochets, Multi-Hit-Potenzial.',
        icon='spark', attr_req={'intellect': 10},
    ),
    'frost_bomb': SkillGem(
        id='frost_bomb', name='Frost Bomb', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.COLD, Tag.DURATION, Tag.PAYOFF},
        damage_type=Tag.COLD,
        mana=18, cd=2.5, cast_time=0.6, base_damage=70,
        desc='Verzögerter Frost-Burst, Cold Exposure.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'frostbolt': SkillGem(
        id='frostbolt', name='Frostbolt', key='',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.COLD},
        damage_type=Tag.COLD,
        mana=14, cd=0.5, cast_time=0.5, base_damage=65,
        desc='Langsame, harte Frost-Bullets.',
        icon='nova', attr_req={'intellect': 12},
    ),
    'ice_nova': SkillGem(
        id='ice_nova', name='Ice Nova', key='4',
        tags={Tag.SPELL, Tag.AOE, Tag.NOVA, Tag.COLD, Tag.PAYOFF},
        damage_type=Tag.COLD,
        mana=30, cd=2.5, cast_time=0.7, base_damage=110,
        desc='Cold-Nova um Spieler. Detoniert Frost-Stacks (Shatter).',
        icon='nova', attr_req={'intellect': 16},
    ),
    'cold_snap': SkillGem(
        id='cold_snap', name='Cold Snap', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.COLD},
        damage_type=Tag.COLD,
        mana=22, cd=3.0, cast_time=0.6, base_damage=90,
        desc='Kalte AoE-Explosion, scaled mit Freeze.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'arc': SkillGem(
        id='arc', name='Arc', key='',
        tags={Tag.SPELL, Tag.CHAINING, Tag.LIGHTNING},
        damage_type=Tag.LIGHTNING,
        mana=20, cd=0.8, cast_time=0.6, base_damage=60,
        desc='Chain-Lightning zwischen Feinden.',
        icon='spark', attr_req={'intellect': 14},
    ),
    'lightning_conduit': SkillGem(
        id='lightning_conduit', name='Lightning Conduit', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.LIGHTNING, Tag.PAYOFF},
        damage_type=Tag.LIGHTNING,
        mana=32, cd=2.0, cast_time=0.5, base_damage=140,
        desc='Detoniert Shock-Stacks zu massivem Schaden.',
        icon='spark', attr_req={'intellect': 18},
    ),
    'comet': SkillGem(
        id='comet', name='Comet', key='5',
        tags={Tag.SPELL, Tag.AOE, Tag.COLD, Tag.SLAM},
        damage_type=Tag.COLD,
        mana=55, cd=6.0, cast_time=1.4, base_damage=220,
        desc='Riesiger Cold-Asteroid fällt vom Himmel mit Verzögerung.',
        icon='comet', attr_req={'intellect': 20},
    ),
    'flame_wall': SkillGem(
        id='flame_wall', name='Flame Wall', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.FIRE, Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=22, cd=4.0, cast_time=0.6, base_damage=40,
        desc='Brennende Wand, durch die Projektile Bonus-Fire bekommen.',
        icon='fire', attr_req={'intellect': 14},
    ),
    'solar_orb': SkillGem(
        id='solar_orb', name='Solar Orb', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.FIRE, Tag.DURATION, Tag.PERSISTENT},
        damage_type=Tag.FIRE,
        mana=0, spirit=25, cd=0.0, cast_time=0.0, base_damage=25,
        desc='Persistent Pulsing Fire-Orbit-AoE.',
        icon='fire', attr_req={'intellect': 18},
    ),
}


# ============================================================
# K-04 — WITCH (Knochenwitwen / Minion- & Chaos-Hexe)
# Lore-Bibel Teil 6.6: Shulavh-Berührt. Vossharil-Lineage.
# ============================================================
WITCH_SKILLS = {
    'bone_spear': SkillGem(
        id='bone_spear', name='Bone Spear', key='3',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=0.6, cast_time=0.5, base_damage=85,
        desc='Schnelles Bone-Projektil, hohes Single-Target.',
        icon='spear', attr_req={'intellect': 12},
    ),
    'bone_storm': SkillGem(
        id='bone_storm', name='Bone Storm', key='',
        tags={Tag.SPELL, Tag.CHANNELING, Tag.PHYSICAL, Tag.AOE},
        damage_type=Tag.PHYSICAL,
        mana=16, cd=0.0, cast_time=0.0, base_damage=35,
        desc='Channeling, ruft Bone-Vortex herab. Impale-Build.',
        icon='spear', attr_req={'intellect': 14},
    ),
    'bone_cage': SkillGem(
        id='bone_cage', name='Bone Cage', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.PHYSICAL, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=24, cd=4.0, cast_time=0.8, base_damage=70,
        desc='Sperrt Feinde in Knochenkäfig ein, AoE-Crusher.',
        icon='spear', attr_req={'intellect': 16},
    ),
    'bone_blast': SkillGem(
        id='bone_blast', name='Bone Blast', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.PHYSICAL, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=22, cd=2.0, cast_time=0.6, base_damage=100,
        desc='Bone-AoE-Detonation. Skaliert mit Bone-Stacks am Ziel.',
        icon='quake', attr_req={'intellect': 14},
    ),
    'bone_offering': SkillGem(
        id='bone_offering', name='Bone Offering', key='',
        tags={Tag.BUFF, Tag.PERSISTENT, Tag.PHYSICAL, Tag.MINION,
              Tag.SUSTAINED},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=20, cd=0.0, cast_time=0.6, base_damage=0,
        desc='Sacrificed corpse → minion buff (Vossharil-Pakt).',
        icon='cross', attr_req={'intellect': 14},
    ),
    'summon_skeletal_warrior': SkillGem(
        id='summon_skeletal_warrior', name='Summon Skeletal Warrior', key='',
        tags={Tag.SPELL, Tag.MINION, Tag.DURATION, Tag.PERSISTENT},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=15, cd=0.0, cast_time=0.8, base_damage=0,
        desc='Basis-Skelette (Krieger). Reservieren Spirit.',
        icon='spear', attr_req={'intellect': 12},
    ),
    'summon_skeletal_arsonist': SkillGem(
        id='summon_skeletal_arsonist', name='Summon Skeletal Arsonist', key='',
        tags={Tag.SPELL, Tag.MINION, Tag.FIRE, Tag.PROJECTILE,
              Tag.PERSISTENT},
        damage_type=Tag.FIRE,
        mana=0, spirit=20, cd=0.0, cast_time=0.8, base_damage=0,
        desc='Skelette werfen Bomben, können andere Skelette detonieren.',
        icon='fire', attr_req={'intellect': 14},
    ),
    'summon_skeletal_cleric': SkillGem(
        id='summon_skeletal_cleric', name='Summon Skeletal Cleric', key='',
        tags={Tag.SPELL, Tag.MINION, Tag.BUFF, Tag.PERSISTENT},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=25, cd=0.0, cast_time=0.8, base_damage=0,
        desc='Heal-Minion für die eigene Armee.',
        icon='cross', attr_req={'intellect': 16},
    ),
    'raise_zombie': SkillGem(
        id='raise_zombie', name='Raise Zombie', key='',
        tags={Tag.SPELL, Tag.MINION, Tag.PERSISTENT},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=15, cd=0.0, cast_time=1.0, base_damage=0,
        desc='Klassische Reanimation aus Leiche.',
        icon='spear', attr_req={'intellect': 10},
    ),
    'detonate_dead': SkillGem(
        id='detonate_dead', name='Detonate Dead', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.FIRE, Tag.TRIGGER},
        damage_type=Tag.FIRE,
        mana=20, cd=1.0, cast_time=0.5, base_damage=80,
        desc='Lässt Corpse als Fire-AoE explodieren.',
        icon='fire', attr_req={'intellect': 14},
    ),
    'unearth': SkillGem(
        id='unearth', name='Unearth', key='',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=0.5, cast_time=0.4, base_damage=40,
        desc='Beschwört Corpse aus Boden für Detonations-Combos.',
        icon='spear', attr_req={'intellect': 10},
    ),
    'contagion': SkillGem(
        id='contagion', name='Contagion', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.CHAOS, Tag.DURATION},
        damage_type=Tag.CHAOS,
        mana=22, cd=1.5, cast_time=0.7, base_damage=50,
        desc='Chaos-DoT, breitet sich aus.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'essence_drain': SkillGem(
        id='essence_drain', name='Essence Drain', key='',
        tags={Tag.SPELL, Tag.PROJECTILE, Tag.CHAOS, Tag.DURATION},
        damage_type=Tag.CHAOS,
        mana=18, cd=0.4, cast_time=0.4, base_damage=45,
        desc='Chaos-Projektil mit langem DoT. Heilt den Caster.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'despair': SkillGem(
        id='despair', name='Despair', key='',
        tags={Tag.CURSE, Tag.AOE, Tag.CHAOS, Tag.DURATION},
        damage_type=Tag.CHAOS,
        mana=24, cd=4.0, cast_time=0.6, base_damage=0,
        desc='Curse: Ziele nehmen mehr Chaos-Damage.',
        icon='nova', attr_req={'intellect': 16},
    ),
    'enfeeble': SkillGem(
        id='enfeeble', name='Enfeeble', key='',
        tags={Tag.CURSE, Tag.AOE, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=24, cd=4.0, cast_time=0.6, base_damage=0,
        desc='Curse: Ziele verursachen weniger Schaden.',
        icon='cross', attr_req={'intellect': 16},
    ),
    'blasphemy': SkillGem(
        id='blasphemy', name='Blasphemy', key='',
        tags={Tag.CURSE, Tag.AURA, Tag.PERSISTENT, Tag.BUFF},
        damage_type=Tag.CHAOS,
        mana=0, spirit=30, cd=0.0, cast_time=0.5, base_damage=0,
        desc='Curse-as-Aura: Spirit-reservierter Curse-Bereich.',
        icon='nova', attr_req={'intellect': 18},
    ),
    'ravenous_swarm': SkillGem(
        id='ravenous_swarm', name='Ravenous Swarm', key='',
        tags={Tag.MINION, Tag.PERSISTENT, Tag.CHAOS},
        damage_type=Tag.CHAOS,
        mana=0, spirit=25, cd=0.0, cast_time=0.7, base_damage=20,
        desc='Untargetable Insektenschwarm.',
        icon='nova', attr_req={'intellect': 16},
    ),
}


# ============================================================
# K-05 — RANGER (Saatträgerinnen / Bow-Marksman, Nheyra-Lineage)
# ============================================================
# Skill-Briefing Teil 2.5: Bow-Archetypen + Elemental-Arrows + Movement.
# Lore-Hint: Saatträgerinnen tragen Nheyras Atem in ihren Pfeilspitzen —
# jeder Schuss ist eine kleine Aussaat von Frost/Sturm/Verfall.
RANGER_SKILLS = {
    'lightning_arrow': SkillGem(
        id='lightning_arrow', name='Lightning Arrow', key='1',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.BOW,
              Tag.AOE, Tag.CHAINING},
        damage_type=Tag.LIGHTNING,
        mana=8, cd=0.0, cast_time=0.4, base_damage=42,
        desc='Pfeil mit Lightning-Splash bei Impact, kettet zu '
             '3 nahen Zielen.',
        icon='bolt', attr_req={'dexterity': 10, 'intellect': 6},
    ),
    'frost_arrow': SkillGem(
        id='frost_arrow', name='Frost Arrow', key='2',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.COLD, Tag.BOW, Tag.PAYOFF},
        damage_type=Tag.COLD,
        mana=8, cd=0.0, cast_time=0.4, base_damage=46,
        desc='Pfeil, der Frost auflädt; Payoff-Crit gegen brittle-Ziele.',
        icon='bolt', attr_req={'dexterity': 10, 'intellect': 6},
    ),
    'burning_arrow': SkillGem(
        id='burning_arrow', name='Burning Arrow', key='3',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.FIRE, Tag.BOW, Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=8, cd=0.0, cast_time=0.4, base_damage=50,
        desc='Brennender Pfeil, hohe Ignite-Chance.',
        icon='bolt', attr_req={'dexterity': 10, 'intellect': 4},
    ),
    'storm_rain': SkillGem(
        id='storm_rain', name='Storm Rain', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.LIGHTNING, Tag.BOW,
              Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=2.5, cast_time=0.6, base_damage=24,
        desc='Pfeilsalve in den Himmel; regnet Blitzschläge in AoE 4 s.',
        icon='quake', attr_req={'dexterity': 14, 'intellect': 8},
    ),
    'galvanic_shards': SkillGem(
        id='galvanic_shards', name='Galvanic Shards', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.BOW},
        damage_type=Tag.LIGHTNING,
        mana=12, cd=0.0, cast_time=0.35, base_damage=18,
        desc='5 Splitter im Kegel, hohe Crit-Chance bei nahem Ziel.',
        icon='spear', attr_req={'dexterity': 12, 'intellect': 6},
    ),
    'lightning_rod': SkillGem(
        id='lightning_rod', name='Lightning Rod', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.BOW,
              Tag.DURATION, Tag.PAYOFF},
        damage_type=Tag.LIGHTNING,
        mana=14, cd=1.2, cast_time=0.5, base_damage=30,
        desc='Markiert Ziel als Blitzanker; Payoff-Blitze bei Folge-Treffern.',
        icon='bolt', attr_req={'dexterity': 12, 'intellect': 10},
    ),
    'rain_of_arrows': SkillGem(
        id='rain_of_arrows', name='Rain of Arrows', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.BOW, Tag.PHYSICAL,
              Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=22, cd=3.0, cast_time=0.8, base_damage=32,
        desc='Großer AoE-Pfeilhagel, 3 s Duration.',
        icon='quake', attr_req={'dexterity': 16},
    ),
    'toxic_growth': SkillGem(
        id='toxic_growth', name='Toxic Growth', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.CHAOS, Tag.BOW,
              Tag.DURATION, Tag.AOE},
        damage_type=Tag.CHAOS,
        mana=16, cd=2.0, cast_time=0.5, base_damage=28,
        desc='Pfeil, pflanzt Gift-Schwamm; tickt Chaos in AoE.',
        icon='nova', attr_req={'dexterity': 12, 'intellect': 10},
    ),
    'snipe': SkillGem(
        id='snipe', name='Snipe', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.BOW, Tag.PHYSICAL, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=1.6, cast_time=1.0, base_damage=140,
        desc='Geladener Präzisionsschuss; Crit-Multiplikator skaliert mit '
             'Channel-Time.',
        icon='spear', attr_req={'dexterity': 18},
    ),
    'mirage_archer': SkillGem(
        id='mirage_archer', name='Mirage Archer', key='',
        tags={Tag.PERSISTENT, Tag.PROJECTILE, Tag.BOW, Tag.MINION, Tag.AURA},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=20, cd=0.0, cast_time=0.8, base_damage=20,
        desc='Persistenter Spiegel-Bogenschütze schießt mit dir mit.',
        icon='shield', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'smoke_arrow': SkillGem(
        id='smoke_arrow', name='Smoke Arrow', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.BOW, Tag.AOE,
              Tag.DURATION, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=12, cd=4.0, cast_time=0.4, base_damage=6,
        desc='Erzeugt Rauchwand; brichst LOS, baut Stealth-Bonus auf.',
        icon='nova', attr_req={'dexterity': 12},
    ),
    'hunters_mark': SkillGem(
        id='hunters_mark', name='Hunters Mark', key='',
        tags={Tag.CURSE, Tag.SPELL, Tag.DURATION, Tag.PAYOFF, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=1.0, cast_time=0.3, base_damage=0,
        desc='Markiert Ziel; +25% Bow-Damage gegen es, Auto-Refresh '
             'bei Tod.',
        icon='shield', attr_req={'dexterity': 12, 'intellect': 12},
    ),
    'disengage': SkillGem(
        id='disengage', name='Disengage', key='',
        tags={Tag.ATTACK, Tag.TRAVEL, Tag.BOW, Tag.PROJECTILE},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=5.0, cast_time=0.3, base_damage=30,
        desc='Rückwärts-Salto + Konter-Schuss; i-Frames 0.4 s.',
        icon='quake', attr_req={'dexterity': 14},
    ),
    'blink': SkillGem(
        id='blink', name='Blink', key='',
        tags={Tag.SPELL, Tag.TRAVEL, Tag.CAST},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=6.0, cast_time=0.15, base_damage=0,
        desc='Sofort-Teleport in Sichtrichtung; bricht Aggro-LOS.',
        icon='bolt', attr_req={'dexterity': 12, 'intellect': 14},
    ),
    'tornado_shot': SkillGem(
        id='tornado_shot', name='Tornado Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.BOW, Tag.PHYSICAL, Tag.AOE},
        damage_type=Tag.PHYSICAL,
        mana=16, cd=0.0, cast_time=0.45, base_damage=30,
        desc='Pfeil platzt mid-air in 5 Sekundärgeschosse.',
        icon='nova', attr_req={'dexterity': 16},
    ),
    'caltrops': SkillGem(
        id='caltrops', name='Caltrops', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.DURATION, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=12, cd=4.0, cast_time=0.4, base_damage=10,
        desc='Wirft Stacheln; Bleed + Slow auf alle Durchläufer, 8 s.',
        icon='quake', attr_req={'dexterity': 12},
    ),
    'explosive_trap': SkillGem(
        id='explosive_trap', name='Explosive Trap', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.FIRE, Tag.TRIGGER},
        damage_type=Tag.FIRE,
        mana=18, cd=3.0, cast_time=0.5, base_damage=85,
        desc='Stellt Falle; explodiert bei Gegner-Berührung.',
        icon='quake', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'cluster_grenade': SkillGem(
        id='cluster_grenade', name='Cluster Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.FIRE, Tag.BOW},
        damage_type=Tag.FIRE,
        mana=22, cd=4.0, cast_time=0.6, base_damage=60,
        desc='Pfeil mit Cluster-Sprengkopf; 3 Sekundär-Explosionen.',
        icon='quake', attr_req={'dexterity': 16, 'intellect': 8},
    ),
}


# ============================================================
# K-06 — MERCENARY (Mahnmal-Gilde / Crossbow + Grenaden, Korven-Vor-Lineage)
# ============================================================
# Skill-Briefing Teil 2.6: Crossbow-Archetypen (Rapid/Power/Burst) +
# Granaten-Familie + Reload-Mechanik. Lore-Hint: Söldner der Mahnmal-
# Gilde tragen umgebaute Belagerungs-Crossbows mit Ousens Mahnungen
# eingraviert — jede Salve „rechnet ab".
MERCENARY_SKILLS = {
    'galvanic_shot': SkillGem(
        id='galvanic_shot', name='Galvanic Shot', key='1',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.CROSSBOW},
        damage_type=Tag.LIGHTNING,
        mana=10, cd=0.0, cast_time=0.35, base_damage=44,
        desc='Crossbow-Schuss; sprüht 3 Blitzfunken bei Impact.',
        icon='bolt', attr_req={'dexterity': 10, 'intellect': 8},
    ),
    'permafrost_bolts': SkillGem(
        id='permafrost_bolts', name='Permafrost Bolts', key='2',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.COLD, Tag.CROSSBOW},
        damage_type=Tag.COLD,
        mana=10, cd=0.0, cast_time=0.4, base_damage=40,
        desc='Schnelle Frost-Bolts; +Slow pro Treffer.',
        icon='bolt', attr_req={'dexterity': 10, 'intellect': 8},
    ),
    'plasma_blast': SkillGem(
        id='plasma_blast', name='Plasma Blast', key='3',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.AOE,
              Tag.CROSSBOW, Tag.PAYOFF},
        damage_type=Tag.LIGHTNING,
        mana=22, cd=2.0, cast_time=0.7, base_damage=120,
        desc='Geladener Plasma-Schuss; AoE-Explosion auf Shocked-Ziel.',
        icon='nova', attr_req={'dexterity': 14, 'intellect': 14},
    ),
    'glacial_bolt': SkillGem(
        id='glacial_bolt', name='Glacial Bolt', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.COLD, Tag.CROSSBOW, Tag.PAYOFF},
        damage_type=Tag.COLD,
        mana=18, cd=1.2, cast_time=0.6, base_damage=80,
        desc='Schwerer Eis-Bolt; Crit-Payoff gegen Frozen.',
        icon='spear', attr_req={'dexterity': 12, 'intellect': 12},
    ),
    'fragmentation_rounds': SkillGem(
        id='fragmentation_rounds', name='Fragmentation Rounds', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.CROSSBOW,
              Tag.AOE},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=0.5, cast_time=0.4, base_damage=36,
        desc='Bolt platzt bei Impact in 4 Splitter.',
        icon='quake', attr_req={'dexterity': 12, 'strength': 10},
    ),
    'incendiary_shot': SkillGem(
        id='incendiary_shot', name='Incendiary Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.FIRE, Tag.CROSSBOW,
              Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=14, cd=0.0, cast_time=0.45, base_damage=48,
        desc='Brand-Bolt; hohe Ignite-Chance.',
        icon='bolt', attr_req={'dexterity': 12, 'intellect': 8},
    ),
    'explosive_shot': SkillGem(
        id='explosive_shot', name='Explosive Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.FIRE, Tag.AOE, Tag.CROSSBOW},
        damage_type=Tag.FIRE,
        mana=20, cd=1.5, cast_time=0.6, base_damage=90,
        desc='AoE-Explosions-Bolt; richtungs-Knockback.',
        icon='quake', attr_req={'dexterity': 14, 'strength': 8},
    ),
    'armour_piercing': SkillGem(
        id='armour_piercing', name='Armour Piercing Rounds', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.CROSSBOW},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=0.6, cast_time=0.5, base_damage=70,
        desc='Bolts ignorieren 50% Armour; durchschlagen 1 Ziel.',
        icon='spear', attr_req={'strength': 12, 'dexterity': 12},
    ),
    'gas_grenade': SkillGem(
        id='gas_grenade', name='Gas Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.CHAOS, Tag.AOE, Tag.DURATION},
        damage_type=Tag.CHAOS,
        mana=16, cd=4.0, cast_time=0.5, base_damage=24,
        desc='Wirft Gas-Granate; Chaos-DoT in AoE 6 s.',
        icon='nova', attr_req={'intellect': 10, 'dexterity': 10},
    ),
    'flash_grenade': SkillGem(
        id='flash_grenade', name='Flash Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=14, cd=5.0, cast_time=0.4, base_damage=10,
        desc='Blendgranate; Stun + Blind 2.5 s.',
        icon='nova', attr_req={'dexterity': 12},
    ),
    'oil_grenade': SkillGem(
        id='oil_grenade', name='Oil Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.DURATION, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=12, cd=4.0, cast_time=0.4, base_damage=8,
        desc='Öl-Lache; verstärkt nachfolgende Fire-Trigger (+50% Burn-Tick).',
        icon='quake', attr_req={'dexterity': 10},
    ),
    'cluster_grenade_merc': SkillGem(
        id='cluster_grenade_merc', name='Cluster Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.FIRE, Tag.DURATION},
        damage_type=Tag.FIRE,
        mana=22, cd=3.0, cast_time=0.6, base_damage=70,
        desc='Granate teilt sich mid-air in 4 kleine Bomben.',
        icon='quake', attr_req={'dexterity': 14, 'strength': 8},
    ),
    'voltaic_grenade': SkillGem(
        id='voltaic_grenade', name='Voltaic Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.LIGHTNING, Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=3.0, cast_time=0.5, base_damage=66,
        desc='Tesla-Granate; pulsiert Lightning-Ringe in AoE 4 s.',
        icon='quake', attr_req={'intellect': 12, 'dexterity': 12},
    ),
    'he_grenade': SkillGem(
        id='he_grenade', name='HE Grenade', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.PHYSICAL, Tag.FIRE},
        damage_type=Tag.PHYSICAL,
        mana=24, cd=4.0, cast_time=0.7, base_damage=140,
        desc='High-Explosive Granate; flacher Schaden-Kegel + Knockback.',
        icon='quake', attr_req={'strength': 14, 'dexterity': 12},
    ),
    'emergency_reload': SkillGem(
        id='emergency_reload', name='Emergency Reload', key='',
        tags={Tag.SPELL, Tag.CAST, Tag.BUFF, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=0, cd=10.0, cast_time=0.3, base_damage=0,
        desc='Sofort-Reload + 50% Attack-Speed-Boost 4 s.',
        icon='shield', attr_req={'dexterity': 12},
    ),
    'active_reload': SkillGem(
        id='active_reload', name='Active Reload', key='',
        tags={Tag.SPELL, Tag.CAST, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=0, cd=0.0, cast_time=0.8, base_damage=0,
        desc='Manueller Reload mit Timing-Window; +Damage bei Perfect-Click.',
        icon='shield', attr_req={'dexterity': 10},
    ),
    'shockburst_rounds': SkillGem(
        id='shockburst_rounds', name='Shockburst Rounds', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.CROSSBOW,
              Tag.AOE, Tag.PAYOFF},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=1.0, cast_time=0.5, base_damage=60,
        desc='3-Schuss-Salve; Payoff-Stunk Shock-Wave bei letztem Bolt.',
        icon='bolt', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'rapid_shot': SkillGem(
        id='rapid_shot', name='Rapid Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.CROSSBOW},
        damage_type=Tag.PHYSICAL,
        mana=6, cd=0.0, cast_time=0.2, base_damage=22,
        desc='Crossbow-Schnellfeuer; -50% Cast-Time, -50% Damage/Shot.',
        icon='spear', attr_req={'dexterity': 12},
    ),
    'power_shot': SkillGem(
        id='power_shot', name='Power Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.CROSSBOW, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=18, cd=1.0, cast_time=0.9, base_damage=130,
        desc='Voll-aufgeladener Crossbow-Schuss; Auto-Crit auf Heavy-Stunned.',
        icon='spear', attr_req={'strength': 12, 'dexterity': 14},
    ),
    'burst_shot': SkillGem(
        id='burst_shot', name='Burst Shot', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.CROSSBOW},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=0.6, cast_time=0.4, base_damage=30,
        desc='3-Round-Burst; mittlerer Schuss garantiert Crit.',
        icon='spear', attr_req={'dexterity': 14},
    ),
}


# ============================================================
# K-07 — HUNTRESS (Zhar-Eth-Schwestern / Spear-Tänzerin, Nheyra-Lineage)
# ============================================================
# Skill-Briefing Teil 2.7: Spear-Throw + Wirbel + Wind/Sturm-Affinität.
# Lore-Hint: Die Zhar-Eth-Schwestern lernen Speerkunst aus dem Wind —
# jede Drehung zeichnet ein altes Schutzzeichen in die Luft.
HUNTRESS_SKILLS = {
    'lightning_spear': SkillGem(
        id='lightning_spear', name='Lightning Spear', key='1',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.SPEAR},
        damage_type=Tag.LIGHTNING,
        mana=12, cd=0.0, cast_time=0.45, base_damage=60,
        desc='Geschleuderter Blitz-Speer; entlädt Arc auf Impact.',
        icon='bolt', attr_req={'dexterity': 12, 'intellect': 8},
    ),
    'whirling_slash': SkillGem(
        id='whirling_slash', name='Whirling Slash', key='2',
        tags={Tag.ATTACK, Tag.MELEE, Tag.AOE, Tag.SPEAR, Tag.PHYSICAL,
              Tag.CHANNELING},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=0.0, cast_time=0.4, base_damage=40,
        desc='Channeling-Wirbel mit Speer; trifft alle nahen Gegner.',
        icon='nova', attr_req={'dexterity': 14, 'strength': 10},
    ),
    'wall_of_spears': SkillGem(
        id='wall_of_spears', name='Wall of Spears', key='3',
        tags={Tag.SPELL, Tag.AOE, Tag.DURATION, Tag.PHYSICAL, Tag.SPEAR},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=4.0, cast_time=0.8, base_damage=50,
        desc='Errichtet Speer-Phalanx; blockt Projektile + Bleed-Tick.',
        icon='quake', attr_req={'dexterity': 14, 'strength': 12},
    ),
    'rake': SkillGem(
        id='rake', name='Rake', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.PHYSICAL, Tag.SPEAR},
        damage_type=Tag.PHYSICAL,
        mana=8, cd=0.0, cast_time=0.4, base_damage=55,
        desc='Schneller Speer-Stich; hohe Bleed-Apply-Chance.',
        icon='spear', attr_req={'dexterity': 10, 'strength': 8},
    ),
    'storm_spear': SkillGem(
        id='storm_spear', name='Storm Spear', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.LIGHTNING, Tag.SPEAR,
              Tag.CHAINING},
        damage_type=Tag.LIGHTNING,
        mana=14, cd=0.3, cast_time=0.5, base_damage=58,
        desc='Speer kettet zu 4 weiteren Gegnern.',
        icon='bolt', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'spear_throw': SkillGem(
        id='spear_throw', name='Spear Throw', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.SPEAR},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=0.0, cast_time=0.4, base_damage=70,
        desc='Wurf-Speer; durchschlägt erste 2 Gegner.',
        icon='spear', attr_req={'dexterity': 12, 'strength': 8},
    ),
    'spiral_volley': SkillGem(
        id='spiral_volley', name='Spiral Volley', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.SPEAR, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=2.0, cast_time=0.7, base_damage=44,
        desc='Spiralförmige Speer-Salve in Spirale; 8 Speere.',
        icon='nova', attr_req={'dexterity': 16},
    ),
    'twister': SkillGem(
        id='twister', name='Twister', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.DURATION, Tag.LIGHTNING, Tag.TRAVEL},
        damage_type=Tag.LIGHTNING,
        mana=24, cd=4.0, cast_time=0.7, base_damage=30,
        desc='Wirbel-Storm wandert über Boden, zieht Gegner an, 5 s.',
        icon='nova', attr_req={'dexterity': 14, 'intellect': 12},
    ),
    'spearfield': SkillGem(
        id='spearfield', name='Spearfield', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.DURATION, Tag.PHYSICAL,
              Tag.PERSISTENT, Tag.SPEAR},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=25, cd=0.0, cast_time=1.0, base_damage=20,
        desc='Persistent: rotierende Speere kreisen um dich.',
        icon='shield', attr_req={'dexterity': 16, 'strength': 12},
    ),
    'disengage_huntress': SkillGem(
        id='disengage_huntress', name='Disengage', key='',
        tags={Tag.SPELL, Tag.TRAVEL, Tag.SPEAR, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=14, cd=5.0, cast_time=0.25, base_damage=0,
        desc='Speer-Sprung rückwärts; +30% Damage 3 s.',
        icon='quake', attr_req={'dexterity': 14},
    ),
    'predators_mark': SkillGem(
        id='predators_mark', name="Predator's Mark", key='',
        tags={Tag.CURSE, Tag.SPELL, Tag.DURATION, Tag.PAYOFF},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=1.0, cast_time=0.3, base_damage=0,
        desc='Markiert Ziel; Crits auf das Mal sind garantiert.',
        icon='shield', attr_req={'dexterity': 14, 'intellect': 10},
    ),
    'rapid_assault': SkillGem(
        id='rapid_assault', name='Rapid Assault', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.SPEAR, Tag.PHYSICAL,
              Tag.AOE},
        damage_type=Tag.PHYSICAL,
        mana=16, cd=2.0, cast_time=0.6, base_damage=70,
        desc='3-Hit-Combo; dritter Schlag stößt zurück.',
        icon='quake', attr_req={'dexterity': 14, 'strength': 10},
    ),
    'mortar_cannon': SkillGem(
        id='mortar_cannon', name='Mortar Cannon', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.AOE, Tag.PHYSICAL, Tag.SPEAR},
        damage_type=Tag.PHYSICAL,
        mana=22, cd=2.5, cast_time=0.8, base_damage=85,
        desc='Hoch-bogenförmig geschleuderter Wurfspeer; AoE-Impact.',
        icon='quake', attr_req={'dexterity': 14, 'strength': 12},
    ),
    'iron_ward': SkillGem(
        id='iron_ward', name='Iron Ward', key='',
        tags={Tag.SPELL, Tag.CAST, Tag.BUFF, Tag.DURATION, Tag.AURA},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=12.0, cast_time=0.6, base_damage=0,
        desc='Eisen-Aegis; absorbiert 40% Damage 6 s.',
        icon='shield', attr_req={'strength': 14, 'dexterity': 10},
    ),
}


# ============================================================
# K-08 — DRUID (Wandelnde / Shapeshift + Sturm, "der Siebte"-Lineage)
# ============================================================
# Skill-Briefing Teil 2.8: Werebear/Werewolf/Wyvern + Sturm-Sprüche +
# Vine-Familie + Time-Sprüche. Lore-Hint: Die Wandelnden hören die
# Stimme des Siebten und antworten in Tiergestalt.
DRUID_SKILLS = {
    'werebear_form': SkillGem(
        id='werebear_form', name='Werebear Form', key='1',
        tags={Tag.SPELL, Tag.PERSISTENT, Tag.AURA, Tag.PHYSICAL, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=30, cd=0.0, cast_time=0.8, base_damage=0,
        desc='Verwandlung in Bären: +50% HP, +Phys-Damage, -Speed.',
        icon='shield', attr_req={'strength': 16},
    ),
    'werewolf_form': SkillGem(
        id='werewolf_form', name='Werewolf Form', key='2',
        tags={Tag.SPELL, Tag.PERSISTENT, Tag.AURA, Tag.PHYSICAL, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=25, cd=0.0, cast_time=0.7, base_damage=0,
        desc='Verwandlung in Wolf: +Attack-Speed, +Move-Speed.',
        icon='shield', attr_req={'dexterity': 14, 'strength': 10},
    ),
    'wyvern_form': SkillGem(
        id='wyvern_form', name='Wyvern Form', key='3',
        tags={Tag.SPELL, Tag.PERSISTENT, Tag.AURA, Tag.LIGHTNING, Tag.BUFF},
        damage_type=Tag.LIGHTNING,
        mana=0, spirit=40, cd=0.0, cast_time=1.0, base_damage=0,
        desc='Verwandlung in Wyvern: Flug-Move, Lightning-Breath.',
        icon='shield', attr_req={'intellect': 14, 'dexterity': 12},
    ),
    'maul': SkillGem(
        id='maul', name='Maul', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=10, cd=0.6, cast_time=0.5, base_damage=85,
        desc='Bären-Pranken-Hieb; Heavy-Damage, Knockback.',
        icon='quake', attr_req={'strength': 14},
    ),
    'rend': SkillGem(
        id='rend', name='Rend', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.STRIKE, Tag.PHYSICAL, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=8, cd=0.0, cast_time=0.3, base_damage=40,
        desc='Wolf-Biss; hohe Bleed-Apply-Chance.',
        icon='spear', attr_req={'strength': 10, 'dexterity': 10},
    ),
    'pounce': SkillGem(
        id='pounce', name='Pounce', key='',
        tags={Tag.ATTACK, Tag.MELEE, Tag.TRAVEL, Tag.PHYSICAL},
        damage_type=Tag.PHYSICAL,
        mana=12, cd=4.0, cast_time=0.4, base_damage=60,
        desc='Wolf-Sprung auf Ziel; landet hinter ihm.',
        icon='quake', attr_req={'dexterity': 12},
    ),
    'storm_call': SkillGem(
        id='storm_call', name='Storm Call', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.LIGHTNING, Tag.DURATION, Tag.PAYOFF},
        damage_type=Tag.LIGHTNING,
        mana=18, cd=1.2, cast_time=0.5, base_damage=90,
        desc='Markiert Boden; Blitz schlägt nach 1.2 s ein.',
        icon='bolt', attr_req={'intellect': 14},
    ),
    'apocalypse': SkillGem(
        id='apocalypse', name='Apocalypse', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.LIGHTNING, Tag.FIRE, Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=40, cd=20.0, cast_time=2.0, base_damage=200,
        desc='Ultimate: Sturm-Inferno auf weiter AoE, 8 s.',
        icon='nova', attr_req={'intellect': 20, 'strength': 14},
    ),
    'vine_arrow': SkillGem(
        id='vine_arrow', name='Vine Arrow', key='',
        tags={Tag.ATTACK, Tag.PROJECTILE, Tag.PHYSICAL, Tag.AOE,
              Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=12, cd=2.0, cast_time=0.5, base_damage=30,
        desc='Pflanz-Pfeil; Ranken halten Ziele fest, Pin-Stack.',
        icon='spear', attr_req={'dexterity': 12, 'intellect': 10},
    ),
    'spore_burst': SkillGem(
        id='spore_burst', name='Spore Burst', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.CHAOS, Tag.DURATION, Tag.NOVA},
        damage_type=Tag.CHAOS,
        mana=16, cd=2.5, cast_time=0.5, base_damage=42,
        desc='Sporen-Nova um Caster; Chaos-DoT auf Treffer.',
        icon='nova', attr_req={'intellect': 12},
    ),
    'thornwall': SkillGem(
        id='thornwall', name='Thornwall', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.DURATION, Tag.PHYSICAL, Tag.PERSISTENT},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=20, cd=0.0, cast_time=0.8, base_damage=18,
        desc='Persistente Dornenwand; blockt Movement, Bleed-Tick.',
        icon='quake', attr_req={'strength': 10, 'intellect': 10},
    ),
    'primal_roar': SkillGem(
        id='primal_roar', name='Primal Roar', key='',
        tags={Tag.WARCRY, Tag.AOE, Tag.BUFF, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=20, cd=10.0, cast_time=0.6, base_damage=0,
        desc='Brüll-AoE; Fear 2 s + Selbstbuff +20% Damage 6 s.',
        icon='shield', attr_req={'strength': 14},
    ),
    'lightning_storm_d': SkillGem(
        id='lightning_storm_d', name='Lightning Storm', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.LIGHTNING, Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=26, cd=4.0, cast_time=0.9, base_damage=55,
        desc='Wandernde Blitz-Wolke; 6 s.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'hailstorm': SkillGem(
        id='hailstorm', name='Hailstorm', key='',
        tags={Tag.SPELL, Tag.AOE, Tag.COLD, Tag.DURATION},
        damage_type=Tag.COLD,
        mana=24, cd=4.0, cast_time=0.9, base_damage=50,
        desc='Hagelschauer; Slow + Frost-Apply auf alle Treffer.',
        icon='nova', attr_req={'intellect': 14},
    ),
    'bond_of_nature': SkillGem(
        id='bond_of_nature', name='Bond of Nature', key='',
        tags={Tag.SPELL, Tag.AURA, Tag.PERSISTENT, Tag.BUFF},
        damage_type=Tag.PHYSICAL,
        mana=0, spirit=20, cd=0.0, cast_time=0.6, base_damage=0,
        desc='Aura: regen +2 HP/s für Caster und Allies.',
        icon='shield', attr_req={'intellect': 12, 'strength': 10},
    ),
    'foresight': SkillGem(
        id='foresight', name='Foresight', key='',
        tags={Tag.SPELL, Tag.BUFF, Tag.CAST, Tag.DURATION},
        damage_type=Tag.LIGHTNING,
        mana=20, cd=12.0, cast_time=0.4, base_damage=0,
        desc='+40% Crit-Chance, +30% Move-Speed 4 s.',
        icon='shield', attr_req={'intellect': 16},
    ),
    'echo_strike': SkillGem(
        id='echo_strike', name='Echo Strike', key='',
        tags={Tag.SPELL, Tag.CAST, Tag.TRIGGER, Tag.DURATION},
        damage_type=Tag.PHYSICAL,
        mana=18, cd=8.0, cast_time=0.4, base_damage=0,
        desc='Nächster Skill wird 2x in 0.6 s wiederholt.',
        icon='shield', attr_req={'intellect': 14, 'dexterity': 10},
    ),
    'time_phantom': SkillGem(
        id='time_phantom', name='Time Phantom', key='',
        tags={Tag.SPELL, Tag.CAST, Tag.DURATION, Tag.MINION},
        damage_type=Tag.PHYSICAL,
        mana=30, cd=20.0, cast_time=0.8, base_damage=0,
        desc='Phantom-Klon des Casters wiederholt letzte Aktionen 4 s.',
        icon='shield', attr_req={'intellect': 18, 'dexterity': 12},
    ),
}


# ============================================================
# CONSOLIDATED — alle Klassen-Skill-Pools
# ============================================================
CLASS_SKILL_POOLS = {
    'warrior':   WARRIOR_SKILLS,
    'monk':      MONK_SKILLS,
    'sorceress': SORCERESS_SKILLS,
    'mage':      SORCERESS_SKILLS,  # Lore-Alias (Funkengeborene)
    'witch':     WITCH_SKILLS,
    'ranger':    RANGER_SKILLS,
    'mercenary': MERCENARY_SKILLS,
    'rogue':     MERCENARY_SKILLS,  # Lore-Alias (Mahnmal-Söldner = Mercenary)
    'huntress':  HUNTRESS_SKILLS,
    'druid':     DRUID_SKILLS,
}


def get_skill_pool(class_id: str) -> dict:
    """Returnt die SkillGem-Registry für eine Klasse."""
    return CLASS_SKILL_POOLS.get(class_id, {})


def all_skill_gems() -> dict:
    """Returnt alle SkillGems aus allen Klassen, als {skill_id: gem}."""
    out = {}
    for pool in CLASS_SKILL_POOLS.values():
        out.update(pool)
    return out
