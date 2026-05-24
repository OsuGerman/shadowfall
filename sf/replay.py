"""Replay-Recording (PLAN AA-06).

Pro Run werden Player-Input-Events + RNG-Seed protokolliert →
deterministische Replays moeglich (Bug-Repro + Leaderboard-Verify).

Architektur:
  - `ReplayRecorder.start(seed)` resetted state, schreibt header.
  - `ReplayRecorder.record_event(t, kind, payload)` haengt an.
  - `ReplayRecorder.save(path)` flushed nach JSON.
  - `ReplayPlayer.load(path)` + `step(t)` iteriert vorberechnete
    Events.

Aktuelle Implementierung: Recording-Skeleton, Player als API.  Volle
Game-Sim-Replay-Integration (Input-Injection in Game.handle_events)
ist Folge-Aufgabe.

Format `replay.json`:
  {
    "version": 1,
    "seed": 42,
    "class": "warrior",
    "events": [
      {"t": 0.034, "kind": "key", "key": "K_w", "down": true},
      {"t": 0.230, "kind": "mouse", "btn": 1, "down": true, "x": 800, "y": 450},
      ...
    ]
  }
"""

import json
import os
import time


REPLAY_VERSION = 1


class ReplayRecorder:
    def __init__(self):
        self.seed = None
        self.cls = None
        self.events = []
        self.start_t = 0.0
        self.active = False

    def start(self, seed, cls):
        self.seed = int(seed)
        self.cls = cls
        self.events = []
        self.start_t = time.monotonic()
        self.active = True

    def record(self, kind, payload=None):
        if not self.active:
            return
        ev = {
            't': round(time.monotonic() - self.start_t, 4),
            'kind': kind,
        }
        if payload:
            ev.update(payload)
        self.events.append(ev)

    def stop(self):
        self.active = False

    def save(self, path):
        data = {
            'version': REPLAY_VERSION,
            'seed': self.seed,
            'class': self.cls,
            'events': self.events,
        }
        try:
            os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f)
            return True
        except Exception:
            return False


class ReplayPlayer:
    def __init__(self):
        self.data = None
        self.cursor = 0

    def load(self, path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.cursor = 0
            return True
        except Exception:
            return False

    def step(self, t):
        """Returnt alle Events <= t (chronologisch), advances cursor."""
        if self.data is None:
            return []
        events = self.data.get('events', [])
        out = []
        while self.cursor < len(events) and events[self.cursor]['t'] <= t:
            out.append(events[self.cursor])
            self.cursor += 1
        return out

    @property
    def seed(self):
        return self.data.get('seed') if self.data else None

    @property
    def cls(self):
        return self.data.get('class') if self.data else None
