"""Workflow 1 — Character Sheet Generator: 1 Charakter → 4-Direction Sheet.

Generiert pro Charakter ein 2x2-Grid mit Front/Right-Side/Back/3-Quarter
Views, alle style-locked zum Referenz-Sprite. Foundation-Step fuer
Top-Down-ARPG-Animationen (T2.6 Phase 3).

Doku: VELGRAD_WORKFLOWS_BIBEL.md §II
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.workflow_runner import (  # noqa: E402
    WorkflowBase, SHEETS_DIR, upload_asset, composit_grid,
    cost_estimate,
)
from tools.scenario_config import PROJECT_ROOT, SPRITES_DIR  # noqa: E402


# ============================================================
# DIRECTION-PROMPTS — style-locked via referenceImages
# ============================================================
# Update #167: 3/4-Top-Down-ARPG-Konvention aus sf/render_spec.py.
# Direction-Descriptions sind dort zentralisiert (alle 4 sind 3/4-View,
# KEINE flachen Eye-Level-Side-Views — passen sonst nicht zum Tile-System).
# Wir kombinieren die zentrale Direction-Desc mit dem 4-Dir-Sheet-spezifischen
# Pose-Suffix.
from sf.render_spec import DIRECTION_DESC, MASTER_NEGATIVE as _SPEC_MASTER_NEG  # noqa: E402

DIRECTION_PROMPTS = {
    'S':  (DIRECTION_DESC['S']  + ', frontal full-body pose, sprite-ready'),
    'E':  (DIRECTION_DESC['E']  + ', dynamic walking pose hint, sprite-ready'),
    'N':  (DIRECTION_DESC['N']  + ', full-body, sprite-ready'),
    'SE': (DIRECTION_DESC['S']  + ', three-quarter facing down-right, '
           'dynamic walking pose, sprite-ready'),
}
DIRECTION_ORDER = ['S', 'E', 'N', 'SE']   # Reihenfolge im 2x2-Sheet

MASTER_NEGATIVE = _SPEC_MASTER_NEG + ', ' + (
    'multiple characters, group shot, background scene, environment, '
    'props, weapons floating, cropped, partial body'
)

# Default Sub-Sprite-Size im Sheet
DEFAULT_CELL = 1024


# ============================================================
# WORKFLOW
# ============================================================
class CharacterSheetWorkflow(WorkflowBase):
    workflow_name = 'character_sheet'

    def __init__(self, *, target: str, category: str = 'class',
                  cell_size: int = DEFAULT_CELL, **kw):
        super().__init__(**kw)
        self.target = target
        self.category = category
        self.cell_size = cell_size

    # ----------------------------------------------------------------
    def _find_anchor_png(self) -> Path | None:
        """Sucht das Anchor-Sprite (Front-View) fuer diesen Target.
        Priorisiert assets/sprites/<category>/<target>.png."""
        cat_dir = SPRITES_DIR / (
            'classes' if self.category == 'class' else self.category + 's'
        )
        candidate = cat_dir / f'{self.target}.png'
        if candidate.is_file():
            return candidate
        # Fallback: irgendwo unter assets/sprites/
        for p in SPRITES_DIR.rglob(f'{self.target}*.png'):
            return p
        return None

    # ----------------------------------------------------------------
    def run(self) -> dict:
        anchor = self._find_anchor_png()
        if anchor is None:
            err = f'Kein Anchor-Sprite gefunden fuer target={self.target}'
            print(f'    {err}', file=sys.stderr)
            self.log_run(args={'target': self.target}, outputs=[],
                         status='failed', error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': 0.0}

        print(f'    anchor: {anchor.relative_to(PROJECT_ROOT)}')

        # Upload anchor als Reference
        ref_id = None
        if not self.dry_run:
            ref_id = upload_asset(anchor)
            if not ref_id:
                err = 'Anchor-Upload zu Scenario fehlgeschlagen'
                self.log_run(args={'target': self.target}, outputs=[],
                             status='failed', error=err)
                return {'status': 'failed', 'outputs': [], 'error': err,
                        'cost_eur': 0.0}

        # 4 Inference-Calls pro Direction
        sub_paths: list[Path] = []
        tmp_dir = SHEETS_DIR / '_tmp' / self.target
        tmp_dir.mkdir(parents=True, exist_ok=True)

        for direction in DIRECTION_ORDER:
            prompt = (
                f'same character as reference, {DIRECTION_PROMPTS[direction]}, '
                f'consistent style and proportions, top-down ARPG sprite, '
                f'transparent background, no shadow'
            )
            out_path = tmp_dir / f'{self.target}_{direction}.png'
            ok = self.run_inference_to_file(
                prompt, out_path,
                category=self.category,
                width=self.cell_size, height=self.cell_size,
                steps=30, guidance=7.0,
                negative_prompt=MASTER_NEGATIVE,
                reference_asset_ids=[ref_id] if ref_id else None,
            )
            if not ok:
                print(f'    direction {direction} FAIL', file=sys.stderr)
                continue
            sub_paths.append(out_path)

        if len(sub_paths) < 4 and not self.dry_run:
            err = f'nur {len(sub_paths)}/4 Sub-Sprites generiert'
            self.log_run(args={'target': self.target}, outputs=[],
                         status='failed', error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': cost_estimate(len(self.inference_ids))}

        # Composit zu 2x2-Sheet
        out_sheet = SHEETS_DIR / f'{self.target}_4dir.png'
        composit_grid(
            sub_paths, cols=2, rows=2,
            cell_w=self.cell_size, cell_h=self.cell_size,
            out_path=out_sheet, bg_alpha=0,
        )

        outputs = [str(out_sheet.relative_to(PROJECT_ROOT)).replace('\\', '/')]
        self.log_run(args={'target': self.target, 'category': self.category},
                     outputs=outputs, status='success')
        return {
            'status': 'success', 'outputs': outputs,
            'cost_eur': cost_estimate(len(self.inference_ids)),
        }


# ============================================================
# CLI
# ============================================================
CLASS_TARGETS = ['warrior', 'witch', 'sorceress', 'monk', 'ranger',
                  'mercenary', 'huntress', 'druid']


def main():
    ap = argparse.ArgumentParser(
        description='Character Sheet Generator (4-Direction)')
    ap.add_argument('--target', type=str, default=None,
                    help='Sprite-ID (z.B. warrior, salzhueter_brut)')
    ap.add_argument('--category', type=str, default='class',
                    choices=['class', 'mob', 'portrait'])
    ap.add_argument('--all-classes', action='store_true',
                    help='Alle 8 Klassen batch-generieren')
    ap.add_argument('--cell-size', type=int, default=DEFAULT_CELL)
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--model', type=str, default=None)
    args = ap.parse_args()

    if args.all_classes:
        targets = CLASS_TARGETS
    elif args.target:
        targets = [args.target]
    else:
        print('Bitte --target <id> oder --all-classes angeben.')
        return

    total_inferences = len(targets) * 4
    total_cost = cost_estimate(total_inferences)
    print('=' * 60)
    print(f'  Character Sheet Generator')
    print(f'  Targets: {", ".join(targets)}')
    print(f'  Inference-Calls: {total_inferences} (4 pro Target)')
    print(f'  Cost-Estimate:   {total_cost:.2f} EUR')
    print('=' * 60)

    if args.dry_run:
        print('DRY-RUN — keine API-Calls.')
        return

    for target in targets:
        print(f'\n  Generate {target} ...')
        wf = CharacterSheetWorkflow(
            target=target, category=args.category,
            cell_size=args.cell_size,
            dry_run=args.dry_run,
            model_override=args.model,
        )
        result = wf.run()
        print(f'    {result["status"]}: {result["outputs"]} '
              f'(cost {result["cost_eur"]:.2f} EUR)')


if __name__ == '__main__':
    main()
