"""J-12 (Update #65): Event-Bus für lose Kopplung Combat/UI/Audio/VFX.

Lore-Anker: Audio-Bibel Teil 1.6 („Event-Driven Audio"), Briefing J-12.

API:
    from . import events as _ev
    _ev.subscribe('player_died', my_callback)
    _ev.publish('player_died', game=game, damage_type='fire')

Subscribers werden als `callback(**kwargs)` gerufen.  Exceptions in
einem Subscriber blocken die anderen NICHT (each-callback try/except).

Vordefinierte Events (in `EventKey`):
    ON_PLAYER_DIED       — Player.hp ≤ 0
    ON_PLAYER_LEVELUP    — Player levelt up
    ON_ENEMY_KILLED      — kill_enemy() final
    ON_BOSS_SPAWNED      — Boss spawn (BossEncounter.start)
    ON_BOSS_DEFEATED     — Boss stirbt
    ON_BOSS_PHASE        — Boss-Phase-Transition (siehe N-09)
    ON_AOE_SPAWNED       — Decal mit Wind-Up spawned
    ON_PLAYER_ENTERED_AREA   — Town/Dungeon-Wechsel
    ON_LOOT_PICKED       — Item ins Inventar
    ON_CRIT              — Crit-Hit-Damage

Listener müssen ihre Subscriptions nicht abmelden — die Bus-State ist
prozess-lebenslang.  Bei Bedarf `unsubscribe(key, callback)`.

Module die das nutzen wollen, können einfach beim Import subscriben.
"""

import sys


class EventKey:
    """String-Konstanten für Event-Topics."""
    ON_PLAYER_DIED        = 'player_died'
    ON_PLAYER_LEVELUP     = 'player_levelup'
    ON_PLAYER_ENTERED_AREA = 'player_entered_area'
    ON_ENEMY_KILLED       = 'enemy_killed'
    ON_BOSS_SPAWNED       = 'boss_spawned'
    ON_BOSS_DEFEATED      = 'boss_defeated'
    ON_BOSS_PHASE         = 'boss_phase'
    ON_AOE_SPAWNED        = 'aoe_spawned'
    ON_LOOT_PICKED        = 'loot_picked'
    ON_CRIT               = 'crit_hit'
    ON_SKILL_CAST         = 'skill_cast'
    ON_DUNGEON_CLEARED    = 'dungeon_cleared'


_subscribers = {}  # key → list of callables


def subscribe(key, callback):
    """Hängt einen Callback an einen Event-Key. Idempotent."""
    if not callable(callback):
        return
    bucket = _subscribers.setdefault(key, [])
    if callback not in bucket:
        bucket.append(callback)


def unsubscribe(key, callback):
    """Entfernt einen Callback.  Silent wenn nicht subscribed."""
    bucket = _subscribers.get(key)
    if not bucket:
        return
    try:
        bucket.remove(callback)
    except ValueError:
        pass


def publish(key, **kwargs):
    """Feuert ein Event.  Alle Subscriber bekommen `**kwargs`.

    Ein Exception in einem Subscriber blockt die anderen NICHT —
    Bus ist isolation-tolerant.  Errors gehen nach stderr.
    """
    bucket = _subscribers.get(key)
    if not bucket:
        return
    for cb in list(bucket):  # snapshot, falls Sub während Publish addet
        try:
            cb(**kwargs)
        except Exception as ex:
            print(f'[events] subscriber {cb!r} for {key!r} '
                  f'raised: {ex!r}', file=sys.stderr)


def clear_all():
    """Löscht alle Subscriber.  Für Test-Setups, nicht für Game-Code."""
    _subscribers.clear()


def subscriber_count(key=None):
    """Returnt #subscriber für key, oder total wenn key=None."""
    if key is None:
        return sum(len(v) for v in _subscribers.values())
    return len(_subscribers.get(key, []))
