"""Sprite-Animation-State-Machine (Update #165).

Verwaltet pro Player/Mob den aktuellen Animation-State (idle/walk/attack/
hit/death/cast), die Frame-Position im jeweiligen Cycle, und die
Auto-Transitions zwischen den States.

Designprinzip:
  - Looping-Anims (idle, walk) wechseln frei untereinander basierend
    auf player.moving.
  - One-Shot-Anims (attack, hit, cast) locken die State-Machine bis sie
    durchgelaufen sind, dann release zurueck zu idle/walk.
  - Death lockt permanent (kein Release).

Engine-Integration:
  Player.__init__:
      from .sprite_animation import AnimationState
      self.anim_state = AnimationState()

  Player.update(dt):
      self.anim_state.update(dt, self)

  Bei Attack/Hit/Death-Events:
      self.anim_state.trigger('attack')
      self.anim_state.trigger('hit')
      self.anim_state.trigger('death')

Render-Hook (sf.sprites.draw_player_at):
      a = p.anim_state
      frame = get_class_anim_frame(p.cls, a.current, direction, a.frame)
"""
from __future__ import annotations


# ============================================================
# ANIMATION-KONFIG
# ============================================================
# Pro Anim-Type:
#   frames:    Anzahl Sub-Frames im Strip
#   fps:       Wiedergabe-Geschwindigkeit (Frames pro Sekunde)
#   loop:      True → loopt am Ende; False → bleibt am letzten Frame
#   directional: True → braucht 4 Strips (down/up/left/right)
#                False → 1 Strip ohne Direction (z.B. death)
#   lock_during: True → blockiert auto-Transitions waehrend Anim laeuft
#                (Attack/Hit/Cast/Death). idle+walk lock_during=False.
ANIM_CONFIG = {
    'idle': {
        'frames': 4, 'fps': 4, 'loop': True,
        'directional': True, 'lock_during': False,
    },
    'walk': {
        'frames': 8, 'fps': 10, 'loop': True,
        'directional': True, 'lock_during': False,
    },
    'attack': {
        'frames': 6, 'fps': 14, 'loop': False,
        'directional': True, 'lock_during': True,
    },
    'hit': {
        'frames': 4, 'fps': 12, 'loop': False,
        'directional': True, 'lock_during': True,
    },
    'cast': {
        'frames': 6, 'fps': 10, 'loop': False,
        'directional': True, 'lock_during': True,
    },
    'death': {
        'frames': 8, 'fps': 8, 'loop': False,
        'directional': False, 'lock_during': True,
    },
}

ANIM_TYPES = tuple(ANIM_CONFIG.keys())

# Priority bei Trigger-Conflict (haerter Trigger ueberschreibt weicheren).
# z.B. wenn Player gerade in 'attack' und nimmt Damage → 'hit' wins nicht
# automatisch, ABER 'death' ueberschreibt alles.
TRIGGER_PRIORITY = {
    'death':  100,
    'hit':    50,    # interrupts attack/cast wenn schwerer Treffer
    'cast':   30,
    'attack': 30,
    'walk':   10,
    'idle':   0,
}


class AnimationState:
    """Per-Player Animation-State-Tracker.

    Attributes:
        current:  Aktueller Anim-Type-Name (z.B. 'walk')
        frame:    Index 0..config['frames']-1
        timer:    Zeit-Accumulator seit letztem Frame-Advance
        locked:   True → auto-transition blockiert (One-Shot laeuft)
    """

    __slots__ = ('current', 'frame', 'timer', 'locked', '_finished')

    def __init__(self):
        self.current: str = 'idle'
        self.frame: int = 0
        self.timer: float = 0.0
        self.locked: bool = False
        self._finished: bool = False   # True wenn One-Shot grad fertig wurde

    # ----------------------------------------------------------------
    def update(self, dt: float, player) -> None:
        """Advance Frame + Auto-Transition zwischen idle/walk.

        Wird einmal pro Game-Tick mit dt-seconds aufgerufen.
        """
        if self.current not in ANIM_CONFIG:
            self.current = 'idle'
        cfg = ANIM_CONFIG[self.current]

        # Frame-Advance basierend auf fps
        self.timer += dt
        frame_dur = 1.0 / max(1, cfg['fps'])
        advanced = False
        while self.timer >= frame_dur:
            self.timer -= frame_dur
            self.frame += 1
            advanced = True
            if self.frame >= cfg['frames']:
                if cfg['loop']:
                    self.frame = 0
                else:
                    # One-Shot: bleibt am letzten Frame stehen
                    self.frame = cfg['frames'] - 1
                    if self.locked:
                        self._finished = True
                        # Lock NICHT sofort hier loesen — death soll
                        # permanent locked bleiben. Lock-Release passiert
                        # weiter unten kontrolliert.
                    break  # nicht weiter im while-loop

        # Lock-Release fuer One-Shots (ausser death — death bleibt fuer immer)
        if self._finished and self.current != 'death':
            self.locked = False
            self._finished = False
            # Auto-Transition zurueck zu idle/walk wird unten gemacht

        # Auto-Transition idle ↔ walk (nur wenn nicht locked)
        if not self.locked and self.current in ('idle', 'walk'):
            target = 'walk' if getattr(player, 'moving', False) else 'idle'
            if target != self.current:
                self._switch(target)

    # ----------------------------------------------------------------
    def trigger(self, anim_name: str) -> bool:
        """Externer Trigger fuer One-Shot-Anims (attack/hit/cast/death).

        Returns True wenn Anim gestartet wurde. Returns False wenn ein
        gerade laufender State eine hoehere Prio hat (z.B. Trigger 'hit'
        waehrend 'death' laeuft → ignoriert).

        Update #168 (Flicker-Fix): Re-Trigger des SELBEN States wird
        ignoriert solange der Cycle noch laeuft (verhindert Frame-Reset
        bei rapid-fire Events wie LMB-held-attack oder Multi-Hit-Damage).
        Death darf sich nicht selbst neu starten — bleibt am letzten Frame.
        """
        if anim_name not in ANIM_CONFIG:
            return False
        # Re-Trigger des gleichen States waehrend er laeuft → ignorieren.
        # Verhindert dass Attack/Hit-Frame jede 0.4s auf 0 zurueckspringt.
        if self.current == anim_name and self.locked and not self._finished:
            return False
        # Priority-Check: nur ueberschreiben wenn neu >= alt.
        new_prio = TRIGGER_PRIORITY.get(anim_name, 0)
        cur_prio = TRIGGER_PRIORITY.get(self.current, 0)
        if self.locked:
            if new_prio < cur_prio:
                return False
            # Spezialfall: 'death' kann alles unterbrechen
            if anim_name != 'death' and self.current == 'death':
                return False
        self._switch(anim_name)
        cfg = ANIM_CONFIG[anim_name]
        if cfg['lock_during']:
            self.locked = True
        return True

    # ----------------------------------------------------------------
    def reset(self) -> None:
        """Reset zu idle (z.B. nach Respawn)."""
        self._switch('idle')
        self.locked = False
        self._finished = False

    # ----------------------------------------------------------------
    def is_directional(self) -> bool:
        """True wenn der aktuelle State 4 Direction-Sheets braucht."""
        cfg = ANIM_CONFIG.get(self.current, ANIM_CONFIG['idle'])
        return bool(cfg.get('directional', True))

    # ----------------------------------------------------------------
    def is_one_shot(self) -> bool:
        """True wenn der aktuelle State eine One-Shot-Anim ist."""
        cfg = ANIM_CONFIG.get(self.current, ANIM_CONFIG['idle'])
        return not cfg.get('loop', True)

    # ----------------------------------------------------------------
    def progress(self) -> float:
        """0.0..1.0 — wie weit der aktuelle Cycle durchlaufen ist.

        Nuetzlich fuer procedural Effects (z.B. attack-scale-pulse, der
        bei progress=0.5 am groessten ist).
        """
        cfg = ANIM_CONFIG.get(self.current, ANIM_CONFIG['idle'])
        n = max(1, cfg['frames'])
        frame_dur = 1.0 / max(1, cfg['fps'])
        sub = min(1.0, self.timer / frame_dur)
        return (self.frame + sub) / n

    # ----------------------------------------------------------------
    def _switch(self, new_state: str) -> None:
        if new_state == self.current:
            return
        self.current = new_state
        self.frame = 0
        self.timer = 0.0
        self._finished = False
