# tools/ — Voice & SFX Pipeline

## Voice-Pipeline (3-Schritt-Workflow)

### Schritt 1 — Casting fertigstellen
Voice-IDs aus ElevenLabs Voice Library kopieren und in
[../VELGRAD_VOICE_CASTING.md](../VELGRAD_VOICE_CASTING.md) eintragen.
Mindestens NPCs 1–8 für Akt-1-Pass befüllen.

### Schritt 2 — Manifest bauen
```
python tools/voice_manifest_builder.py
```
- Liest VELGRAD_VOICE_LINES_POOL.md + VELGRAD_VOICE_CASTING.md
- Schreibt `sounds/voice/voice_manifest.json`
- Idempotent: vorhandene Status werden bewahrt.
- Mit `--force`: alles zurück auf pending.

### Schritt 3 — Dry-Run (Kosten checken)
```
python tools/voice_gen.py --dry-run
```
Zeigt:
- Anzahl Pending-Lines
- Geschätzte Zeichen
- Geschätzte EUR-Kosten
- NPCs ohne Voice-ID (werden uebersprungen)

### Schritt 4 — Generieren
```
python tools/voice_gen.py
```
Optionen:
- `--npc korven` — nur Lines fuer einen NPC
- `--limit 10` — nur 10 Lines (Test-Run)
- `--redo-failed` — vorher failed Lines neu versuchen

Output:
- MP3s in `sounds/voice/<npc>/<line_id>.mp3`
- Registry `sf/voice_registry.py` automatisch regeneriert

---

## Key-Speicherung

Eines davon (Reihenfolge der Pruefung):

1. Env-Variable `ELEVENLABS_API_KEY`
2. Datei `.elevenlabs_key` im Projekt-Root
3. Datei `ElevenLabs.txt` im Projekt-Root (User-Convenience)

Alle drei sind in `.gitignore` eingetragen.

---

## Engine-Integration

```python
from sf.voice_registry import pick_voice

mp3_path = pick_voice('korven', 'greeting')
if mp3_path:
    # via sf.sounds.play(...) oder direkt pygame.mixer.Sound
    game.sounds.play_voice(mp3_path)
```

---

## Troubleshooting

- **401 / 403**: Key abgelaufen oder Plan-Limit erreicht.
  - Pruefen: https://elevenlabs.io/app/usage
  - Key in der Datei aktualisieren.
- **429**: Rate-Limit. Script wartet automatisch.
- **Falsche Aussprache** ("Im-Nesh" als "Im Nesh-arn"):
  - In `tools/voice_config.py` `PRONUNCIATION`-Dict erweitern.
  - Dann `--redo-failed` oder Status manuell auf pending setzen.
- **Voice klingt anders als erwartet**:
  - `stability` runter (mehr Variation) oder hoch (mehr Konsistenz).
  - `style` hoch fuer mehr Emotion.
  - Settings in VELGRAD_VOICE_CASTING.md anpassen + Manifest neu bauen.
