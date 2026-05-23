"""Gem-/Tag-/Support-System (PLAN J-01 .. J-04).

Foundation für:
  - K-Block (Klassen-Skills nutzen SkillGem-Daten)
  - L-Block (Ailment-Pipeline nutzt Tags + Damage-Type)
  - M/N (VFX/Audio refs liegen am Gem)

Quellen:
  - POE2_SKILLS_BRIEFING_FUER_CLAUDE_CODE.md Teil 1 (Gem-System),
    Teil 3.1 (Tags), Teil 4 (Top-Supports), Teil 6 (Architektur)
  - VELGRAD_LORE_BIBEL.md Teil 5 (Spirit/Erinnerungssteine)

Architektur:
  - `Tag` Enum mit allen Briefing-Tags
  - `SkillGem` Dataclass — statische Skill-Daten
  - `SupportGem` Dataclass — Modifier auf SkillContext
  - `SkillContext` — mutable Werte, die durch Support-Pipeline laufen
  - `compute_context(gem, supports, player)` — Apply-Pipeline (J-03)
  - `TOP_SUPPORTS` — Registry mit 12 Top-Supports (J-04)
"""

from dataclasses import dataclass, field
from typing import Callable, Iterable, Optional


# ============================================================
# J-02 — TAG-SYSTEM
# ============================================================
# Alle Tags aus SKILLS_BRIEFING Teil 3.1.

class Tag:
    # Wirkungs-Tags
    ATTACK     = 'attack'
    SPELL      = 'spell'
    AOE        = 'aoe'
    PROJECTILE = 'projectile'
    MELEE      = 'melee'
    STRIKE     = 'strike'
    SLAM       = 'slam'
    CHANNELING = 'channeling'
    TRAVEL     = 'travel'
    TRIGGER    = 'trigger'
    WARCRY     = 'warcry'
    TOTEM      = 'totem'
    MINION     = 'minion'
    CURSE      = 'curse'
    AURA       = 'aura'
    HERALD     = 'herald'
    BUFF       = 'buff'
    PERSISTENT = 'persistent'
    DURATION   = 'duration'
    SUSTAINED  = 'sustained'
    PAYOFF     = 'payoff'
    NOVA       = 'nova'
    CAST       = 'cast'
    CHAINING   = 'chaining'
    # Damage-Tags
    FIRE       = 'fire'
    COLD       = 'cold'
    LIGHTNING  = 'lightning'
    PHYSICAL   = 'physical'
    CHAOS      = 'chaos'
    # Weapon-Tags
    BOW          = 'bow'
    CROSSBOW     = 'crossbow'
    SPEAR        = 'spear'
    QUARTERSTAFF = 'quarterstaff'
    MACE         = 'mace'
    DAGGER       = 'dagger'
    WAND         = 'wand'
    SCEPTRE      = 'sceptre'
    STAFF        = 'staff'
    TALISMAN     = 'talisman'
    SWORD        = 'sword'


ALL_TAGS = frozenset({
    Tag.ATTACK, Tag.SPELL, Tag.AOE, Tag.PROJECTILE, Tag.MELEE, Tag.STRIKE,
    Tag.SLAM, Tag.CHANNELING, Tag.TRAVEL, Tag.TRIGGER, Tag.WARCRY, Tag.TOTEM,
    Tag.MINION, Tag.CURSE, Tag.AURA, Tag.HERALD, Tag.BUFF, Tag.PERSISTENT,
    Tag.DURATION, Tag.SUSTAINED, Tag.PAYOFF, Tag.NOVA, Tag.CAST, Tag.CHAINING,
    Tag.FIRE, Tag.COLD, Tag.LIGHTNING, Tag.PHYSICAL, Tag.CHAOS,
    Tag.BOW, Tag.CROSSBOW, Tag.SPEAR, Tag.QUARTERSTAFF, Tag.MACE,
    Tag.DAGGER, Tag.WAND, Tag.SCEPTRE, Tag.STAFF, Tag.TALISMAN, Tag.SWORD,
})

DAMAGE_TAGS = frozenset({Tag.FIRE, Tag.COLD, Tag.LIGHTNING,
                          Tag.PHYSICAL, Tag.CHAOS})


def normalize_tags(tags) -> set:
    """Akzeptiert einen Iterable von Strings (Engine-/Lore-Aliases) und
    returnt das normalisierte Set in Lowercase.
    """
    return {str(t).lower() for t in tags}


# ============================================================
# J-01 — SKILL-GEM-DATENMODELL
# ============================================================
@dataclass
class SkillGem:
    """Statische Skill-Daten (Briefing Teil 1.1).

    Felder, die in einem POE2-Style-System pro Skill stehen müssen:
      - Identität: id, name, key
      - Klassifikation: tags, damage_type
      - Kosten/Kadenz: cost, cooldown, cast_time
      - Damage: base_damage
      - Asset-Refs: vfx, sfx, anim (Strings für Lookup)
      - Level: aktuelle + maximale Stufe
      - Sockets: Liste der eingebetteten Support-Gem-IDs
      - Attribut-Req: STR/INT/DEX-Mindestwerte
    """
    id: str
    name: str
    key: str = ''                  # Hotkey-Label
    tags: set = field(default_factory=set)
    damage_type: str = Tag.PHYSICAL
    mana: float = 0.0              # Mana-Kosten
    spirit: float = 0.0            # Spirit-Reservation (für Persistent/Aura)
    cd: float = 0.0
    cast_time: float = 0.4
    base_damage: float = 0.0
    desc: str = ''
    icon: str = ''                 # Icon-ID
    vfx_refs: dict = field(default_factory=dict)
    sfx_refs: dict = field(default_factory=dict)
    anim_refs: dict = field(default_factory=dict)
    level: int = 1
    max_level: int = 20
    attr_req: dict = field(default_factory=dict)
    socket_count: int = 3          # Slot-Anzahl (Default 3, max 5)
    sockets: list = field(default_factory=list)  # [support_id, ...]

    def has_tag(self, tag: str) -> bool:
        return tag in self.tags

    def has_any_tag(self, tags: Iterable[str]) -> bool:
        return any(t in self.tags for t in tags)

    def add_support(self, support_id: str) -> bool:
        """Sockelt einen Support, wenn noch Platz."""
        if len(self.sockets) >= self.socket_count:
            return False
        if support_id in self.sockets:
            return False  # No duplicates (siehe Lineage-Restriction Teil 1.5)
        self.sockets.append(support_id)
        return True

    def remove_support(self, support_id: str) -> bool:
        if support_id in self.sockets:
            self.sockets.remove(support_id)
            return True
        return False


# ============================================================
# SKILL-CONTEXT (mutiert durch Support-Pipeline, J-03)
# ============================================================
@dataclass
class SkillContext:
    """Pro-Cast-Kontext, durch Support-Pipeline mutiert.

    Caster (skills.cast_*) liest diesen Kontext anstelle von Hardcoded-Werten.
    """
    skill_id: str
    base_damage: float = 0.0
    damage_mult: float = 1.0       # multiplikativ
    more_damage: float = 1.0       # POE-Style „more damage" (multiplikativ)
    cost_mult: float = 1.0
    cooldown_mult: float = 1.0
    cast_time_mult: float = 1.0
    aoe_radius_mult: float = 1.0
    duration_mult: float = 1.0
    projectile_count: int = 1
    pierce: int = 0
    chain: int = 0
    fork: int = 0
    crit_chance_bonus: float = 0.0
    crit_mult_bonus: float = 0.0
    stun_buildup_mult: float = 1.0
    cascade_lines: int = 0         # Spell Cascade — zusätzliche Spell-Lines
    added_damage: dict = field(default_factory=dict)
    only_damage_types: Optional[set] = None  # z.B. {'physical'} für Brutality
    tags: set = field(default_factory=set)
    # Caster-spezifische Convenience-Felder
    damage_taken_aura: float = 0.0   # für später (auras)
    has_ignite: bool = False
    has_freeze: bool = False
    has_shock: bool = False

    def effective_damage(self) -> float:
        """Finale Damage = base × mult × more + sum(added)."""
        dmg = self.base_damage * self.damage_mult * self.more_damage
        for amt in self.added_damage.values():
            dmg += amt
        # Brutality filter (only_damage_types beschränkt)
        # Wenn only Physical: alle non-phys added wurden bereits gefiltert.
        return dmg

    def effective_cost(self, base_cost: float) -> float:
        """Cost-Multiplier wirkt auf Mana, NICHT auf Spirit (Briefing 1.2)."""
        return max(0.0, base_cost * self.cost_mult)


# ============================================================
# SUPPORT-GEM (J-03)
# ============================================================
ApplyFn = Callable[[SkillContext, SkillGem], None]


@dataclass
class SupportGem:
    """Modifier auf SkillContext. Wird in `compute_context` aufgerufen."""
    id: str
    name: str
    desc: str
    cost_mult: float = 1.0          # erhöht Mana, nicht Spirit
    required_tags: frozenset = frozenset()
    forbidden_tags: frozenset = frozenset()
    apply: ApplyFn = lambda ctx, gem: None
    lore_hint: str = ''             # Velgrad-Lore-Note

    def applicable(self, gem: SkillGem) -> bool:
        gem_tags = set(gem.tags)
        if self.required_tags and not self.required_tags.issubset(gem_tags):
            return False
        if self.forbidden_tags and self.forbidden_tags & gem_tags:
            return False
        return True


# ============================================================
# J-03 — APPLY-PIPELINE
# ============================================================
def compute_context(gem: SkillGem, supports: Iterable[SupportGem] = (),
                    player=None) -> SkillContext:
    """Baut den Skill-Context. Returnt ein Snapshot pro Cast.

    Reihenfolge: SkillGem → for support in supports: apply(ctx).
    Reihenfolge ist linear (kein Topological Sort) — Support-Ordering
    bestimmt der Spieler durch Socket-Ordnung.
    """
    ctx = SkillContext(
        skill_id=gem.id,
        base_damage=gem.base_damage,
        tags=set(gem.tags),
    )
    for sup in supports:
        if not sup.applicable(gem):
            continue
        try:
            sup.apply(ctx, gem)
            # Cost-Mult akkumuliert multiplikativ (Briefing 1.2 +
            # J-05-Semantik: Mana ja, Spirit nein).
            ctx.cost_mult *= sup.cost_mult
        except Exception:
            pass
    # Brutality: bereits-added non-phys ausfiltern
    if ctx.only_damage_types is not None:
        ctx.added_damage = {dt: v for dt, v in ctx.added_damage.items()
                             if dt in ctx.only_damage_types}
    return ctx


def resolve_supports(support_ids: Iterable[str],
                     registry: dict = None) -> list:
    """Wandelt Support-IDs in SupportGem-Instanzen."""
    if registry is None:
        registry = TOP_SUPPORTS
    out = []
    for sid in support_ids:
        sup = registry.get(sid)
        if sup is not None:
            out.append(sup)
    return out


# ============================================================
# J-04 — TOP-SUPPORT-REGISTRY
# ============================================================
# Aus SKILLS_BRIEFING Teil 4 (Top-10-Supports) + Klassen-spezifische.
# Lore: jedes Support-Gem ist ein „Whisper-Stone" (Lore-Bibel 5.4).

def _apply_magnified(ctx: SkillContext, gem: SkillGem):
    ctx.aoe_radius_mult *= 1.30


def _apply_concentrated(ctx: SkillContext, gem: SkillGem):
    ctx.aoe_radius_mult *= 0.65
    ctx.more_damage *= 1.40


def _apply_multi_proj(ctx: SkillContext, gem: SkillGem):
    ctx.projectile_count += 2


def _apply_fork(ctx: SkillContext, gem: SkillGem):
    ctx.fork += 1


def _apply_chain(ctx: SkillContext, gem: SkillGem):
    ctx.chain += 2


def _apply_pierce(ctx: SkillContext, gem: SkillGem):
    ctx.pierce += 2


def _apply_brutality(ctx: SkillContext, gem: SkillGem):
    # NUR Physical-Damage; non-phys-added wird in compute_context gefiltert.
    ctx.only_damage_types = {Tag.PHYSICAL}
    ctx.more_damage *= 1.50


def _apply_added_fire(ctx: SkillContext, gem: SkillGem):
    # Flat fire-Damage zum Cast addieren
    ctx.added_damage['fire'] = ctx.added_damage.get('fire', 0.0) + gem.base_damage * 0.25


def _apply_added_cold(ctx: SkillContext, gem: SkillGem):
    ctx.added_damage['cold'] = ctx.added_damage.get('cold', 0.0) + gem.base_damage * 0.25


def _apply_added_lightning(ctx: SkillContext, gem: SkillGem):
    ctx.added_damage['lightning'] = ctx.added_damage.get('lightning', 0.0) + gem.base_damage * 0.30


def _apply_fire_mastery(ctx: SkillContext, gem: SkillGem):
    ctx.more_damage *= 1.40


def _apply_cold_mastery(ctx: SkillContext, gem: SkillGem):
    ctx.more_damage *= 1.40


def _apply_lightning_mastery(ctx: SkillContext, gem: SkillGem):
    ctx.more_damage *= 1.40


def _apply_heavy_swing(ctx: SkillContext, gem: SkillGem):
    # -25% Attack-Speed, +50% More-Damage (Mace-Skills)
    ctx.cast_time_mult *= 1.33
    ctx.more_damage *= 1.50


def _apply_persistence(ctx: SkillContext, gem: SkillGem):
    ctx.duration_mult *= 1.50


def _apply_impact_force(ctx: SkillContext, gem: SkillGem):
    ctx.stun_buildup_mult *= 1.50
    ctx.more_damage *= 1.10


def _apply_spell_cascade(ctx: SkillContext, gem: SkillGem):
    ctx.cascade_lines += 2          # 1 vor, 1 hinter Cast-Position


TOP_SUPPORTS = {
    'magnified_effect': SupportGem(
        id='magnified_effect', name='Magnified Effect',
        desc='+30% AoE-Radius. Briefing #1.',
        cost_mult=1.30,
        required_tags=frozenset({Tag.AOE}),
        apply=_apply_magnified,
        lore_hint='Lauter geflüstert — die Welt erinnert sich weiter.',
    ),
    'concentrated_effect': SupportGem(
        id='concentrated_effect', name='Concentrated Effect',
        desc='-35% AoE, +40% More-Damage. Briefing #4.',
        cost_mult=1.35,
        required_tags=frozenset({Tag.AOE}),
        apply=_apply_concentrated,
        lore_hint='Der Schnitt wird tiefer, der Schmerz schmaler.',
    ),
    'multiple_projectiles': SupportGem(
        id='multiple_projectiles', name='Multiple Projectiles',
        desc='+2 Projektile. Briefing #2.',
        cost_mult=1.30,
        required_tags=frozenset({Tag.PROJECTILE}),
        apply=_apply_multi_proj,
        lore_hint='Drei Worte gleichzeitig — die Welt antwortet dreifach.',
    ),
    'fork': SupportGem(
        id='fork', name='Fork',
        desc='+1 Fork pro Projektil. Briefing #3.',
        cost_mult=1.20,
        required_tags=frozenset({Tag.PROJECTILE}),
        apply=_apply_fork,
    ),
    'chain': SupportGem(
        id='chain', name='Chain',
        desc='+2 Chain-Sprünge.',
        cost_mult=1.20,
        required_tags=frozenset({Tag.PROJECTILE}),
        apply=_apply_chain,
    ),
    'pierce': SupportGem(
        id='pierce', name='Pierce',
        desc='+2 Pierce.',
        cost_mult=1.15,
        required_tags=frozenset({Tag.PROJECTILE}),
        apply=_apply_pierce,
    ),
    'brutality': SupportGem(
        id='brutality', name='Brutality',
        desc='Nur Physical-Damage, +50% More. Briefing #5.',
        cost_mult=1.40,
        required_tags=frozenset({Tag.ATTACK}),
        apply=_apply_brutality,
        lore_hint='Kharn-Lineage. Nichts brennt, nichts friert. Nur Knochen.',
    ),
    'added_fire_damage': SupportGem(
        id='added_fire_damage', name='Added Fire Damage',
        desc='+25% Base-Damage als Fire. Briefing #6.',
        cost_mult=1.20,
        apply=_apply_added_fire,
        lore_hint='Valsa atmet mit.',
    ),
    'added_cold_damage': SupportGem(
        id='added_cold_damage', name='Added Cold Damage',
        desc='+25% Base-Damage als Cold.',
        cost_mult=1.20,
        apply=_apply_added_cold,
        lore_hint='Nheyra hält die Stunde an.',
    ),
    'added_lightning_damage': SupportGem(
        id='added_lightning_damage', name='Added Lightning Damage',
        desc='+30% Base-Damage als Lightning.',
        cost_mult=1.20,
        apply=_apply_added_lightning,
        lore_hint='Ousens tausend Augen funken.',
    ),
    'fire_mastery': SupportGem(
        id='fire_mastery', name='Fire Mastery',
        desc='+40% More-Damage. Nur für Fire-Skills.',
        cost_mult=1.30,
        required_tags=frozenset({Tag.FIRE}),
        apply=_apply_fire_mastery,
    ),
    'cold_mastery': SupportGem(
        id='cold_mastery', name='Cold Mastery',
        desc='+40% More-Damage. Nur für Cold-Skills.',
        cost_mult=1.30,
        required_tags=frozenset({Tag.COLD}),
        apply=_apply_cold_mastery,
    ),
    'lightning_mastery': SupportGem(
        id='lightning_mastery', name='Lightning Mastery',
        desc='+40% More-Damage. Nur für Lightning-Skills.',
        cost_mult=1.30,
        required_tags=frozenset({Tag.LIGHTNING}),
        apply=_apply_lightning_mastery,
    ),
    'heavy_swing': SupportGem(
        id='heavy_swing', name='Heavy Swing',
        desc='-25% Attack-Speed, +50% More-Damage. Mace-Skills.',
        cost_mult=1.35,
        required_tags=frozenset({Tag.MELEE}),
        apply=_apply_heavy_swing,
        lore_hint='Eisenwächter-Disziplin: schwerer Schlag wiegt schwerer.',
    ),
    'persistence': SupportGem(
        id='persistence', name='Persistence',
        desc='+50% Duration. Für DoTs / Buffs.',
        cost_mult=1.20,
        required_tags=frozenset({Tag.DURATION}),
        apply=_apply_persistence,
    ),
    'impact_force': SupportGem(
        id='impact_force', name='Impact Force',
        desc='+50% Stun-Buildup, +10% More-Damage.',
        cost_mult=1.25,
        required_tags=frozenset({Tag.MELEE}),
        apply=_apply_impact_force,
        lore_hint='Kharn-Lineage. Was hält, wird zum Halt.',
    ),
    'spell_cascade': SupportGem(
        id='spell_cascade', name='Spell Cascade',
        desc='+2 zusätzliche Spell-Lines (vor und hinter Cast).',
        cost_mult=1.30,
        required_tags=frozenset({Tag.SPELL, Tag.AOE}),
        apply=_apply_spell_cascade,
    ),
}


# ============================================================
# SKILLGEM-Migrations-Helper
# ============================================================
def skillgem_from_legacy(skill_id: str, info: dict) -> SkillGem:
    """Baut eine SkillGem aus einem Legacy-SKILL_INFO-Dict.

    Erlaubt iterative Migration: cast_*-Funktionen können weiter mit
    SKILL_INFO arbeiten und gleichzeitig die SkillGem-API nutzen.
    """
    tags = normalize_tags(info.get('tags', []))
    # Damage-Type ableiten (POE2-Briefing 3.2: erstes Damage-Tag = primary)
    dmg_type = Tag.PHYSICAL
    for dt in (Tag.FIRE, Tag.COLD, Tag.LIGHTNING, Tag.CHAOS, Tag.PHYSICAL):
        if dt in tags:
            dmg_type = dt
            break
    return SkillGem(
        id=skill_id,
        name=info.get('name', skill_id),
        key=info.get('key', ''),
        tags=tags,
        damage_type=dmg_type,
        mana=float(info.get('mana', 0)),
        spirit=float(info.get('spirit', 0)),
        cd=float(info.get('cd', 0)),
        cast_time=float(info.get('cast_time', 0.4)),
        base_damage=float(info.get('base_damage', 0)),
        desc=info.get('desc', ''),
        icon=info.get('icon', ''),
        vfx_refs=dict(info.get('vfx_refs', {})),
        sfx_refs=dict(info.get('sfx_refs', {})),
        anim_refs=dict(info.get('anim_refs', {})),
        attr_req=dict(info.get('attr_req', {})),
        socket_count=int(info.get('socket_count', 3)),
        sockets=list(info.get('sockets', [])),
    )


def gem_registry_from_legacy(skill_info_dict: dict) -> dict:
    """Bulk-Migration: SKILL_INFO → {skill_id: SkillGem}."""
    return {sid: skillgem_from_legacy(sid, info)
            for sid, info in skill_info_dict.items()}


# ============================================================
# J-06 — SPIRIT-ÖKONOMIE (Briefing 3.3 + Lore-Bibel 5.2)
# ============================================================
# Spirit = Erster Atem im Träger. Basis 100, erhöhbar via Tree/Sceptre/
# Amulet. Persistent Buffs / Heralds / Auras / Meta Gems reservieren
# dauerhaft Spirit. Mana bleibt unbeeinflusst.

def available_spirit(player) -> float:
    """Frei verfügbarer Spirit = max - reserved."""
    mx = getattr(player, 'spirit_max', 100)
    res = getattr(player, 'spirit_reserved', 0)
    return max(0.0, mx - res)


def can_reserve(player, gem: SkillGem) -> bool:
    """True wenn der Player genug freien Spirit für gem.spirit hat."""
    return available_spirit(player) >= gem.spirit


def reserve_spirit(player, gem: SkillGem) -> bool:
    """Reserviert gem.spirit. Returnt False wenn zu wenig Spirit frei."""
    if gem.spirit <= 0:
        return True
    if not can_reserve(player, gem):
        return False
    player.spirit_reserved = getattr(player, 'spirit_reserved', 0) + gem.spirit
    if not hasattr(player, 'reserved_gems'):
        player.reserved_gems = set()
    player.reserved_gems.add(gem.id)
    return True


def unreserve_spirit(player, gem: SkillGem):
    """Gibt die Spirit-Reservation eines Gems frei."""
    if gem.spirit <= 0:
        return
    res_set = getattr(player, 'reserved_gems', set())
    if gem.id not in res_set:
        return
    player.spirit_reserved = max(
        0, getattr(player, 'spirit_reserved', 0) - gem.spirit)
    res_set.discard(gem.id)


# ============================================================
# J-07 / J-08 — META-GEM-TRIGGER-SYSTEM
# ============================================================
# Meta Gems reservieren Spirit und akkumulieren „Energy" durch
# Trigger-Bedingungen (Briefing 1.4 + 4-#12). Wenn Energy ≥ threshold,
# wird der gesockelte Skill auto-gecastet.
#
# Trigger-Events: ON_CRIT, ON_FREEZE, ON_IGNITE, ON_ELEMENTAL_AILMENT,
# ON_MINION_DEATH, ON_BLOCK, ON_SHOCK.

class TriggerEvent:
    ON_CRIT             = 'on_crit'
    ON_FREEZE           = 'on_freeze'
    ON_IGNITE           = 'on_ignite'
    ON_ELEMENTAL_AILMENT = 'on_elemental_ailment'
    ON_MINION_DEATH     = 'on_minion_death'
    ON_BLOCK            = 'on_block'
    ON_SHOCK            = 'on_shock'


@dataclass
class MetaGem:
    """Trigger-Gem (Briefing 1.4): reserviert Spirit, sammelt Energy,
    feuert den gesockelten Skill bei Bedingungs-Match.
    """
    id: str
    name: str
    trigger: str                        # TriggerEvent.*
    energy_per_event: float = 25.0
    energy_threshold: float = 100.0
    spirit: float = 30.0
    socket: Optional[str] = None        # innerer Skill-Gem-ID
    desc: str = ''
    lore_hint: str = ''
    # Runtime state
    energy: float = 0.0
    cooldown: float = 0.0

    def can_fire(self) -> bool:
        return self.energy >= self.energy_threshold and self.cooldown <= 0

    def consume(self):
        self.energy = 0.0
        self.cooldown = 0.5    # min 0.5 s zwischen Auto-Casts

    def tick(self, dt: float):
        if self.cooldown > 0:
            self.cooldown = max(0.0, self.cooldown - dt)


META_GEMS = {
    'cast_on_crit': MetaGem(
        id='cast_on_crit', name='Cast on Crit',
        trigger=TriggerEvent.ON_CRIT,
        energy_per_event=20, energy_threshold=100, spirit=30,
        desc='Sammelt Energie bei jedem Crit. Auto-Cast bei voller Bar.',
        lore_hint='Ousens Auge sieht den Treffer — und antwortet.',
    ),
    'cast_on_freeze': MetaGem(
        id='cast_on_freeze', name='Cast on Freeze',
        trigger=TriggerEvent.ON_FREEZE,
        energy_per_event=33, energy_threshold=100, spirit=25,
        desc='Auto-Cast wenn ein Feind eingefroren wird.',
        lore_hint='Nheyra hält die Stunde an — du nutzt die Pause.',
    ),
    'cast_on_ignite': MetaGem(
        id='cast_on_ignite', name='Cast on Ignite',
        trigger=TriggerEvent.ON_IGNITE,
        energy_per_event=33, energy_threshold=100, spirit=25,
        desc='Auto-Cast wenn ein Feind entzündet wird.',
        lore_hint='Valsa atmet ein — du atmest aus.',
    ),
    'cast_on_elemental_ailment': MetaGem(
        id='cast_on_elemental_ailment', name='Cast on Elemental Ailment',
        trigger=TriggerEvent.ON_ELEMENTAL_AILMENT,
        energy_per_event=15, energy_threshold=100, spirit=35,
        desc='Auto-Cast bei jedem Elemental-Ailment (Ignite/Freeze/Shock).',
    ),
    'cast_on_minion_death': MetaGem(
        id='cast_on_minion_death', name='Cast on Minion Death',
        trigger=TriggerEvent.ON_MINION_DEATH,
        energy_per_event=50, energy_threshold=100, spirit=20,
        desc='Auto-Cast wenn ein verbündeter Minion stirbt.',
        lore_hint='Vossharil-Lineage. Tot zählt mehr als Lebendig.',
    ),
    'cast_on_block': MetaGem(
        id='cast_on_block', name='Cast on Block',
        trigger=TriggerEvent.ON_BLOCK,
        energy_per_event=33, energy_threshold=100, spirit=25,
        desc='Auto-Cast wenn ein Hit geblockt wird (Shield-Build).',
    ),
    'cast_on_shock': MetaGem(
        id='cast_on_shock', name='Cast on Shock',
        trigger=TriggerEvent.ON_SHOCK,
        energy_per_event=25, energy_threshold=100, spirit=25,
        desc='Auto-Cast wenn ein Feind geschockt wird.',
    ),
}


def trigger_meta_event(player, event: str, game=None, target=None):
    """Wird von Combat/Game gerufen, wenn ein Event passiert.

    Iteriert über die aktiven Meta-Gems des Spielers, addiert Energy,
    feuert bei Threshold-Match den inneren Skill (über skills.cast).
    """
    metas = getattr(player, 'active_meta_gems', [])
    for meta in metas:
        if meta.trigger != event and meta.trigger != TriggerEvent.ON_ELEMENTAL_AILMENT:
            continue
        # ON_ELEMENTAL_AILMENT triggert auf alle drei Elemental-Events
        if meta.trigger == TriggerEvent.ON_ELEMENTAL_AILMENT and event not in (
                TriggerEvent.ON_IGNITE, TriggerEvent.ON_FREEZE,
                TriggerEvent.ON_SHOCK):
            continue
        meta.energy += meta.energy_per_event
        if meta.can_fire() and meta.socket and game is not None:
            try:
                from . import skills as _sk
                _sk.cast(meta.socket, game)
                meta.consume()
            except Exception:
                pass
