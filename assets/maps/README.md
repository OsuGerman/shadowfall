# Hand-Crafted Maps (Tiled .tmx)

Diese Maps werden vom [Tiled Map Editor](https://www.mapeditor.org/) erstellt
und vom Game ueber `sf/tiled_loader.py` geladen. Sie sind eine **Alternative
zum prozeduralen Generator** — d.h. fuer Boss-Arenen, Story-Spots oder
hand-designte Outposts.

## Folder-Convention

```
assets/maps/
├── town/                — Outpost-Hubs (Brassweir, Echo-Markt, etc.)
│   └── brassweir_hub.tmx
├── crypt/               — Marrowport + Boss-Arenen
│   └── marrowport_boss.tmx
├── frost/, lava/, ...   — Akt-spezifische Layouts
└── README.md            — diese Datei
```

## Tiled-Layer-Convention

Layer-Namen muessen **diese Substring-Patterns** enthalten (case-insensitive):

| Layer-Name      | Funktion |
|---|---|
| `floor*`        | Tile-Layer mit Floor-Tiles → FLOOR-Cells |
| `walls*`        | Tile-Layer mit Wall-Tiles → WALL-Cells |
| `doors*`        | Optional → DOOR-Cells |
| `traps*`        | Optional → TRAP-Cells |
| `spawns*`       | Object-Layer mit Spawnpoints (Player, NPCs, Mobs, Boss) |
| `decor*`        | Object-Layer mit Decor-Objekten (Faesser, Statuen, Torches) |
| `regions*`      | Object-Layer mit named Polygonen (Lighting-Zone, Quest-Trigger) |

## Object-Types (in Spawn-Layer)

Object `type` (oder `class` in neuerer Tiled-Version) bestimmt was gespawnt
wird:

| Type-String                | Effekt |
|---|---|
| `player_spawn`             | Spawn-Position fuer Player-Start |
| `npc:<key>`                | NPC mit Voice/Quest-Key (z.B. `npc:korven`) |
| `mob:<bestiary_key>`       | Mob (z.B. `mob:salzhueter_brut`) |
| `boss:<encounter_key>`     | Boss-Encounter-Trigger (z.B. `boss:vehren`) |
| `decor:<kind>`             | Decor (z.B. `decor:torch`, `decor:lava_pool`) |
| `interactive:<kind>`       | Chest/Lever/Sign |
| `region:lighting`          | Optional special lighting zone |

## Workflow

1. Tiled Editor oeffnen → File → New → Map (orthogonal, 32×32 px tiles)
2. Tileset hinzufuegen (aktuell aus `assets/sprites/tiles/` einbinden)
3. Layer hinzufuegen (siehe Convention oben)
4. Save as → `assets/maps/<biome>/<name>.tmx`
5. Im Game (Update Game.enter_outpost/enter_dungeon) wird automatisch
   die .tmx versucht zu laden; bei Erfolg wird sie statt procedural
   verwendet, bei Fehler/Missing faellt auf procedural zurueck.

## Engine-Side

`sf/tiled_loader.py` exportiert:
- `is_available()` — True wenn pytmx installiert
- `has_map(name, biome)` — True wenn .tmx existiert
- `load_map(name, biome)` — laedt TiledMap
- `tmx_to_engine(tmx_data)` — konvertiert in
  `{grid, spawns, decor, regions, meta}` Engine-Format
- `list_maps()` — Diagnose, listet alle vorhandenen Maps

## Status

- ✅ Loader-Modul implementiert (Update #178)
- ⏳ Engine-Integration in Game.enter_outpost (geplant Update #179)
- ⏳ Erste hand-crafted Map als Pilot (Brassweir-Hub geplant)
