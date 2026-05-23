"""Workflow 4 — Inpaint / Outpaint via Scenario.gg img2img mit Mask.

Allzweck-Werkzeug fuer Spot-Fixes:
  - BG-Removal-Fehler nachbessern
  - Decor-Variations (1 Fass → 5 verschiedene)
  - Door-Sprites aus Wand-Tiles
  - Helm/Waffen-Varianten an existing Charakteren
  - Wand-Boden-Uebergaenge polieren

Mask-Modi:
  --mask <path>      : PNG-Maske (weiss=inpaint, schwarz=keep)
  --bounds X,Y,W,H   : Rechteck-Bereich (Mask wird intern gebaut)

Doku: VELGRAD_WORKFLOWS_BIBEL.md §V
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.workflow_runner import (  # noqa: E402
    WorkflowBase, upload_asset, cost_estimate,
)
from tools.scenario_config import PROJECT_ROOT, SPRITES_DIR  # noqa: E402


# ============================================================
# HELPERS
# ============================================================
def _build_rect_mask(image_path: Path, bounds: tuple[int, int, int, int],
                      out_path: Path) -> bool:
    """Erzeugt eine PNG-Maske: schwarz everywhere, weiss im bounds-Bereich.
    Bounds = (x, y, w, h) in Source-Image-Pixeln."""
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))
    src = pygame.image.load(str(image_path))
    w, h = src.get_size()
    mask = pygame.Surface((w, h))
    mask.fill((0, 0, 0))
    x, y, bw, bh = bounds
    pygame.draw.rect(mask, (255, 255, 255),
                      (max(0, x), max(0, y),
                       min(bw, w - x), min(bh, h - y)))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(mask, str(out_path))
    return True


# ============================================================
# WORKFLOW
# ============================================================
class InpaintWorkflow(WorkflowBase):
    workflow_name = 'inpaint'

    def __init__(self, *, image_path: Path, prompt: str,
                  mask_path: Path | None = None,
                  bounds: tuple[int, int, int, int] | None = None,
                  strength: float = 0.7,
                  variants: int = 1,
                  category: str = 'class',
                  replace_source: bool = False, **kw):
        super().__init__(**kw)
        self.image_path = image_path
        self.prompt = prompt
        self.mask_path = mask_path
        self.bounds = bounds
        self.strength = strength
        self.variants = max(1, variants)
        self.category = category
        self.replace_source = replace_source

    def run(self) -> dict:
        if not self.image_path.is_file():
            err = f'image not found: {self.image_path}'
            self.log_run(args=self._args_dict(), outputs=[], status='failed',
                         error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': 0.0}

        # Mask vorbereiten
        mask_path = self.mask_path
        if mask_path is None and self.bounds is not None:
            mask_path = (SPRITES_DIR / '_masks' /
                          f'mask_{self.image_path.stem}_{int(time.time())}.png')
            _build_rect_mask(self.image_path, self.bounds, mask_path)
        if mask_path is None:
            err = 'Kein Mask gegeben (weder --mask noch --bounds)'
            self.log_run(args=self._args_dict(), outputs=[], status='failed',
                         error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': 0.0}

        # Uploads
        src_id = None
        mask_id = None
        if not self.dry_run:
            src_id = upload_asset(self.image_path)
            mask_id = upload_asset(mask_path)
            if not src_id or not mask_id:
                err = 'Asset-Upload fehlgeschlagen'
                self.log_run(args=self._args_dict(), outputs=[],
                             status='failed', error=err)
                return {'status': 'failed', 'outputs': [], 'error': err,
                        'cost_eur': 0.0}

        # N Variants generieren
        outputs: list[Path] = []
        for vi in range(self.variants):
            suffix = f'_inpaint_{int(time.time())}'
            if self.variants > 1:
                suffix += f'_v{vi+1}'
            out_path = self.image_path.parent / (
                self.image_path.stem + suffix + '.png')
            ok = self.run_inference_to_file(
                self.prompt, out_path,
                category=self.category,
                width=512, height=512, steps=25, guidance=7.0,
                negative_prompt='watermark, text, distorted, deformed',
                reference_asset_ids=[src_id, mask_id] if src_id else None,
                strength=self.strength,
                inference_type='img2img-mask',
            )
            if not ok:
                print(f'    variant {vi+1} FAIL', file=sys.stderr)
                continue
            outputs.append(out_path)

        # Optional Source ersetzen
        if self.replace_source and outputs and not self.dry_run:
            outputs[0].replace(self.image_path)
            outputs[0] = self.image_path

        rel_outputs = [str(p.relative_to(PROJECT_ROOT)).replace('\\', '/')
                        for p in outputs]
        self.log_run(args=self._args_dict(), outputs=rel_outputs,
                     status='success' if outputs else 'failed')
        return {
            'status': 'success' if outputs else 'failed',
            'outputs': rel_outputs,
            'cost_eur': cost_estimate(len(self.inference_ids)),
        }

    def _args_dict(self) -> dict:
        return {
            'image':    str(self.image_path.relative_to(PROJECT_ROOT)).replace('\\', '/'),
            'prompt':   self.prompt[:100],
            'bounds':   self.bounds,
            'mask':     str(self.mask_path) if self.mask_path else None,
            'strength': self.strength,
            'variants': self.variants,
        }


# ============================================================
# CLI
# ============================================================
def _parse_bounds(s: str) -> tuple[int, int, int, int]:
    parts = [int(x.strip()) for x in s.split(',')]
    if len(parts) != 4:
        raise argparse.ArgumentTypeError('bounds muss X,Y,W,H sein')
    return tuple(parts)  # type: ignore[return-value]


def main():
    ap = argparse.ArgumentParser(description='Inpaint / Outpaint via Scenario.gg')
    ap.add_argument('--image', type=str, required=True,
                    help='Source-PNG-Pfad (relativ zu Projekt oder absolut)')
    ap.add_argument('--prompt', type=str, required=True)
    ap.add_argument('--mask', type=str, default=None,
                    help='Mask-PNG-Pfad (weiss=inpaint, schwarz=keep)')
    ap.add_argument('--bounds', type=_parse_bounds, default=None,
                    help='Rechteck X,Y,W,H als Inpaint-Region')
    ap.add_argument('--strength', type=float, default=0.7,
                    help='0.0..1.0 (default 0.7)')
    ap.add_argument('--variants', type=int, default=1)
    ap.add_argument('--category', type=str, default='class')
    ap.add_argument('--replace', action='store_true',
                    help='Original-PNG durch Result ersetzen')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--model', type=str, default=None)
    args = ap.parse_args()

    image_path = Path(args.image)
    if not image_path.is_absolute():
        image_path = PROJECT_ROOT / image_path
    mask_path = None
    if args.mask:
        mask_path = Path(args.mask)
        if not mask_path.is_absolute():
            mask_path = PROJECT_ROOT / mask_path

    if not args.mask and not args.bounds:
        print('Bitte --mask <png> ODER --bounds X,Y,W,H angeben.')
        return

    print('=' * 60)
    print(f'  Inpaint / Outpaint')
    print(f'  Image:    {image_path}')
    print(f'  Mask:     {mask_path or f"bounds={args.bounds}"}')
    print(f'  Prompt:   {args.prompt[:80]}')
    print(f'  Strength: {args.strength}')
    print(f'  Variants: {args.variants}')
    print(f'  Cost:     {cost_estimate(args.variants):.2f} EUR')
    print('=' * 60)

    if args.dry_run:
        print('DRY-RUN — keine API-Calls.')
        return

    wf = InpaintWorkflow(
        image_path=image_path, prompt=args.prompt,
        mask_path=mask_path, bounds=args.bounds,
        strength=args.strength, variants=args.variants,
        category=args.category, replace_source=args.replace,
        dry_run=args.dry_run, model_override=args.model,
    )
    result = wf.run()
    print(f'\n  {result["status"]}: {result["outputs"]} '
          f'(cost {result["cost_eur"]:.2f} EUR)')


if __name__ == '__main__':
    main()
