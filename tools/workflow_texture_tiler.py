"""Workflow 3 — Texture Tiler: 1 Floor + 1 Wall → 16-Mask modular Tileset.

Loest das Modular-Tile-Problem strukturell. Generiert pro Biome 16 PNGs
(eine pro Bitmask-Pattern N/E/S/W), die der Engine erlauben die exakte
Edge-Variante per Floor-Cell zu blitten — POE2/Hades/D2-Look.

Modi:
  --procedural   (default, 0 Kosten): Bake unser Edge-Overlay-System
                  in PNG-Files aus.
  --ai-hybrid    (~3 EUR/Biome): Generiere 4 transition-edge-Tiles via
                  Scenario.gg + composit mit Procedural-Shadows.

Doku: VELGRAD_WORKFLOWS_BIBEL.md §IV
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.workflow_runner import (  # noqa: E402
    WorkflowBase, SPRITES_DIR, MASKS_DIR, audit_log, cost_estimate,
)
from tools.scenario_config import PROJECT_ROOT  # noqa: E402


# ============================================================
# 16-MASK BITMASK-PATTERNS (4-Direction: N=1, E=2, S=4, W=8)
# ============================================================
ALL_MASKS = list(range(16))  # 0..15

# Edge-Overlay-Parameter — IDENTISCH zu sf.sprites (Update #160)
EDGE_SHADOW_DEPTH_FRAC = 0.32
EDGE_SHADOW_ALPHA_MAX  = 170
EDGE_SHADOW_ALPHA_MIN  = 0


def _sample_avg_rgb(surf):
    """Avg-RGB einer Surface (16x16 grid samples). Wie sf.sprites._wall_average_rgb."""
    sw, sh = surf.get_size()
    rs = gs = bs = 0
    n = 0
    step_x = max(1, sw // 16)
    step_y = max(1, sh // 16)
    for y in range(0, sh, step_y):
        for x in range(0, sw, step_x):
            try:
                r, g, b, *_ = surf.get_at((x, y))
            except Exception:
                continue
            rs += r
            gs += g
            bs += b
            n += 1
    if n <= 0:
        return None
    return (rs // n, gs // n, bs // n)


def _build_edge_overlay_local(cell_size, mask, wall_avg_rgb):
    """Kopie von sf.sprites._build_edge_overlay (semantisch identisch).

    Wird hier inline gehalten damit der Bake-Output bit-exakt dem
    Laufzeit-Render der Engine entspricht.
    """
    import pygame
    size = cell_size + 1
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    if mask == 0:
        return surf

    depth = max(2, int(cell_size * EDGE_SHADOW_DEPTH_FRAC))
    a_max = EDGE_SHADOW_ALPHA_MAX
    a_min = EDGE_SHADOW_ALPHA_MIN
    if wall_avg_rgb is not None:
        r0, g0, b0 = wall_avg_rgb
        sr = int(r0 * 0.15)
        sg = int(g0 * 0.15)
        sb = int(b0 * 0.15)
    else:
        sr = sg = sb = 0

    def grad(side):
        for d in range(depth):
            t = d / max(1, depth - 1)
            a = int(a_max * (1.0 - t) + a_min * t)
            if a <= 0:
                continue
            if side == 'N':
                pygame.draw.line(surf, (sr, sg, sb, a),
                                  (0, d), (size - 1, d), 1)
            elif side == 'E':
                x = size - 1 - d
                pygame.draw.line(surf, (sr, sg, sb, a),
                                  (x, 0), (x, size - 1), 1)
            elif side == 'S':
                y = size - 1 - d
                pygame.draw.line(surf, (sr, sg, sb, a),
                                  (0, y), (size - 1, y), 1)
            elif side == 'W':
                pygame.draw.line(surf, (sr, sg, sb, a),
                                  (d, 0), (d, size - 1), 1)

    if mask & 1: grad('N')
    if mask & 2: grad('E')
    if mask & 4: grad('S')
    if mask & 8: grad('W')
    return surf


# ============================================================
# WORKFLOW
# ============================================================
class TextureTilerWorkflow(WorkflowBase):
    workflow_name = 'texture_tiler'

    def __init__(self, *, biome: str, mode: str = 'procedural',
                  cell_size: int = 128, **kw):
        super().__init__(**kw)
        self.biome = biome
        self.mode = mode
        self.cell_size = cell_size

    # -------- Procedural Mode --------------------------------------
    def _bake_procedural(self) -> list[Path]:
        """Bake unser Edge-Overlay-System in 16 separate PNG-Files aus.

        Direkt-Load der PNGs (umgeht _load_ai_sprite-Issues im headless
        Worker-Context). Generiert Procedural-Shadows wie in
        sf.sprites._build_edge_overlay, sodass Files semantisch identisch
        sind zu dem was die Engine zur Laufzeit blittet.
        """
        os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
        import pygame  # noqa: E402
        if not pygame.get_init():
            pygame.init()
        if not pygame.display.get_init():
            pygame.display.set_mode((1, 1))

        # Tile-Mappings holen (read-only) ohne Surface-Load
        sys.path.insert(0, str(PROJECT_ROOT))
        from sf.sprites import (   # noqa: E402
            TILE_VARIANT_MAP, TILE_WALL_MAP, TILE_SPRITE_ALIAS,
        )
        from sf import sprite_registry as _reg   # noqa: E402

        # Floor-PNG-Pfad finden
        floor_ids = TILE_VARIANT_MAP.get(self.biome) or [
            TILE_SPRITE_ALIAS.get(self.biome, self.biome)
        ]
        floor_path = None
        for fid in floor_ids:
            p = _reg.sprite_path(fid)
            if p:
                abs_p = PROJECT_ROOT / p.replace('/', os.sep)
                if abs_p.is_file():
                    floor_path = abs_p
                    break
        if floor_path is None:
            print(f'    keine Floor-Tiles fuer biome={self.biome}',
                  file=sys.stderr)
            return []

        wall_id = TILE_WALL_MAP.get(self.biome)
        wall_path = None
        if wall_id:
            wp = _reg.sprite_path(wall_id)
            if wp:
                abs_wp = PROJECT_ROOT / wp.replace('/', os.sep)
                if abs_wp.is_file():
                    wall_path = abs_wp
        if wall_path is None:
            print(f'    HINWEIS: kein Wall-Tile registriert fuer biome='
                  f'{self.biome} — Shadows ohne Color-Bleed', file=sys.stderr)

        # Direkt-Load
        floor = pygame.image.load(str(floor_path))
        floor_scaled = pygame.transform.smoothscale(
            floor, (self.cell_size + 1, self.cell_size + 1))

        wall_avg_rgb = None
        if wall_path is not None:
            wall = pygame.image.load(str(wall_path))
            wall_avg_rgb = _sample_avg_rgb(wall)

        out_dir = MASKS_DIR / self.biome
        out_dir.mkdir(parents=True, exist_ok=True)
        out_files: list[Path] = []

        for mask in ALL_MASKS:
            sheet = pygame.Surface(
                (self.cell_size + 1, self.cell_size + 1), pygame.SRCALPHA)
            sheet.blit(floor_scaled, (0, 0))
            if mask > 0:
                overlay = _build_edge_overlay_local(
                    self.cell_size, mask, wall_avg_rgb)
                sheet.blit(overlay, (0, 0))
            out_path = out_dir / f'{self.biome}_mask_{mask:02d}.png'
            pygame.image.save(sheet, str(out_path))
            out_files.append(out_path)

        # Mask-Index als JSON schreiben fuer Engine-Lookup
        index = {
            'biome':     self.biome,
            'cell_size': self.cell_size,
            'masks':     {
                f'{m:02d}': f'masks/{self.biome}/{self.biome}_mask_{m:02d}.png'
                for m in ALL_MASKS
            },
            'mode':      'procedural',
        }
        (out_dir / f'{self.biome}_mask_index.json').write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding='utf-8')
        return out_files

    # -------- AI-Hybrid Mode ---------------------------------------
    def _bake_ai_hybrid(self) -> list[Path]:
        """Generiere 4 transition-edges via Scenario, dann composit.

        Approach:
          1. Procedural Masks als Basis bauen (alle 16)
          2. 4 Inference-Calls: N/E/S/W floor-meets-wall transition tiles
          3. AI-Tiles in wandberuehrende Masks integrieren via Mask-Blend
        """
        # Schritt 1: Procedural Basis
        base_files = self._bake_procedural()
        if not base_files:
            return []

        if self.dry_run:
            print(f'    DRY-RUN: 4 AI-Inference-Calls fuer {self.biome} '
                  f'transitions')
            return base_files

        # Schritt 2: 4 transition-Tiles generieren
        # Prompt-Templates pro Direction (N/E/S/W bzgl. Wall-Position)
        biome_materials = {
            'crypt':  ('weathered stone floor', 'mossy stone wall'),
            'frost':  ('icy stone floor', 'crystallized ice wall'),
            'lava':   ('volcanic rock floor', 'cracked obsidian wall'),
            'swamp':  ('wet mud floor', 'rotted timber wall'),
            'astral': ('starlit obsidian floor', 'purple crystal wall'),
            'desert': ('sandstone floor', 'weathered sandstone wall'),
            'town':   ('cobblestone floor', 'plaster wall'),
            'wound_salt':   ('salt-crusted floor', 'salt pillar wall'),
            'wound_ash':    ('ash-covered floor', 'burnt timber wall'),
            'wound_hollow': ('hollow stone floor', 'void rift wall'),
            'hollow_word':  ('inscribed stone floor', 'glowing rune wall'),
        }
        floor_mat, wall_mat = biome_materials.get(
            self.biome, ('stone floor', 'stone wall'))

        directions = [
            ('N', f'top-down view, seamless transition with '
                  f'{wall_mat} along the top edge fading into '
                  f'{floor_mat} below, weathered, naturally worn'),
            ('E', f'top-down view, seamless transition with '
                  f'{wall_mat} along the right edge fading into '
                  f'{floor_mat}, weathered, naturally worn'),
            ('S', f'top-down view, seamless transition with '
                  f'{floor_mat} fading into '
                  f'{wall_mat} along the bottom edge, weathered'),
            ('W', f'top-down view, seamless transition with '
                  f'{wall_mat} along the left edge fading into '
                  f'{floor_mat}, weathered, naturally worn'),
        ]
        tmp_dir = MASKS_DIR / self.biome / '_ai_transitions'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        for direction, prompt in directions:
            out_path = tmp_dir / f'transition_{direction}.png'
            ok = self.run_inference_to_file(
                prompt, out_path,
                category='tile', width=512, height=512, steps=25,
                negative_prompt=('characters, creatures, perspective, depth, '
                                  'sky, horizon, buildings'),
            )
            if not ok:
                print(f'    AI-transition {direction} FAIL', file=sys.stderr)

        # Schritt 3: Procedural-Masks bleiben Basis; AI-Tiles werden als
        # Detail-Overlay zusaetzlich gespeichert. Die Engine kann sie
        # spaeter via Mask-Blend (alpha + position) integrieren — dafuer
        # ist v2 vorgesehen.
        return base_files

    # -------- Main entry -------------------------------------------
    def run(self) -> dict:
        outputs: list[str] = []
        status = 'success'
        error = None
        try:
            if self.mode == 'ai-hybrid':
                files = self._bake_ai_hybrid()
            else:
                files = self._bake_procedural()
            outputs = [str(p.relative_to(PROJECT_ROOT)).replace('\\', '/')
                       for p in files]
            if not outputs:
                status = 'failed'
                error = 'no output files generated'
        except Exception as e:
            status = 'failed'
            error = str(e)
            print(f'    ERROR: {e}', file=sys.stderr)

        self.log_run(
            args={'biome': self.biome, 'mode': self.mode,
                  'cell_size': self.cell_size},
            outputs=outputs,
            status=status, error=error,
        )
        return {
            'status': status, 'outputs': outputs, 'error': error,
            'cost_eur': cost_estimate(len(self.inference_ids)),
        }


# ============================================================
# CLI
# ============================================================
def main():
    ap = argparse.ArgumentParser(
        description='Texture Tiler — 1 Floor + 1 Wall → 16-Mask Set')
    ap.add_argument('--biome', type=str, default=None,
                    help='crypt|frost|lava|swamp|astral|desert|town|...')
    ap.add_argument('--all', action='store_true',
                    help='Alle Biome mit Wall-Tile registriert')
    ap.add_argument('--procedural', action='store_true', default=True,
                    help='(default) Procedural-Mode, 0 Kosten')
    ap.add_argument('--ai-hybrid', action='store_true',
                    help='Generiere 4 AI-Transition-Tiles (~3 EUR/Biome)')
    ap.add_argument('--cell-size', type=int, default=128)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--model', type=str, default=None)
    args = ap.parse_args()

    mode = 'ai-hybrid' if args.ai_hybrid else 'procedural'

    # Biome-Liste bestimmen
    sys.path.insert(0, str(PROJECT_ROOT))
    from sf import sprites as _spr  # noqa: E402
    if args.all:
        biomes = sorted(_spr.TILE_WALL_MAP.keys())
    elif args.biome:
        biomes = [args.biome]
    else:
        print('Bitte --biome <name> oder --all angeben.')
        print(f'Verfuegbare biomes mit Wall: {sorted(_spr.TILE_WALL_MAP.keys())}')
        return

    if not biomes:
        print('Keine Biome mit Wall-Tile registriert. Erst Walls via '
              'sprite_gen.py --category tile generieren.')
        return

    total_inferences = (len(biomes) * 4) if mode == 'ai-hybrid' else 0
    total_cost = cost_estimate(total_inferences)
    print('=' * 60)
    print(f'  Texture Tiler — Mode: {mode}')
    print(f'  Biome: {", ".join(biomes)}')
    print(f'  Cell-Size: {args.cell_size}px')
    print(f'  AI-Inference-Calls: {total_inferences}')
    print(f'  Cost-Estimate: {total_cost:.2f} EUR')
    print('=' * 60)

    if args.dry_run:
        print('DRY-RUN — keine PNGs werden geschrieben.')
        return

    for biome in biomes:
        print(f'\n  Bake {biome} ...')
        wf = TextureTilerWorkflow(
            biome=biome, mode=mode,
            cell_size=args.cell_size,
            dry_run=args.dry_run,
            model_override=args.model,
        )
        result = wf.run()
        print(f'    {result["status"]}: {len(result["outputs"])} PNGs '
              f'(cost {result["cost_eur"]:.2f} EUR)')


if __name__ == '__main__':
    main()
