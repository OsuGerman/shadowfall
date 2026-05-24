"""Workflow 2 — Sprite Animation Frames: 1 Pose → 8-Frame Walk/Attack Cycle.

Generiert 8 sequenzielle Animation-Frames aus einem Anchor-Sprite. Wird
nach Workflow 1 (Character Sheet) angewendet. Output: 1×8-Strip pro
(Charakter, Animation-Type, Direction).

Output-Konvention (Update #168):
  Schreibt direkt an den Engine-Pfad `assets/sprites/classes/<target>_anims/
  <engine_anim>/<dir>.png` (siehe sf/sprites._anim_strip_path). Anim-Namen
  werden auf die Engine-Konvention gemappt (attack_light → attack, hit_react
  → hit, idle_breath → idle). Direction-Buchstaben S/E/N/W werden auf
  down/right/up/left gemappt. Death ist non-directional → all.png.

  Mit --keep-sheets-copy wird zusaetzlich der alte sheets/-Pfad beschrieben
  (fuer Audit-Trail).

Doku: VELGRAD_WORKFLOWS_BIBEL.md §III, VELGRAD_RENDER_SPEC.md §III.B
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
# PER-FRAME-PHASE-PROMPTS pro Animation-Type
# ============================================================
ANIM_FRAME_PROMPTS = {
    'walk': [
        'contact pose left foot forward, weight shifting',
        'down pose left foot planted, body lowest',
        'passing pose left, right leg passing',
        'up pose left, right leg highest in swing',
        'contact pose right foot forward, opposite contact',
        'down pose right foot planted, body lowest opposite',
        'passing pose right, left leg passing',
        'up pose right, left leg highest in swing',
    ],
    'attack_light': [
        'idle stance, weapon at side',
        'wind-up start, weapon raising slightly',
        'wind-up mid, weapon raised high above shoulder',
        'wind-up peak, body coiled, weapon held high',
        'strike frame 1, weapon at peak velocity downward',
        'strike frame 2, follow-through, weapon swinging through',
        'recovery, weapon trailing, body unwinding',
        'return to idle, weapon back at side',
    ],
    'attack_heavy': [
        'idle stance, two-handed grip',
        'wind-up frame 1, deep coil',
        'wind-up frame 2, maximum coil, body twisted',
        'wind-up frame 3, peak tension',
        'release, full power strike, weapon at peak',
        'impact pose, weapon stopped against target',
        'recovery frame 1, weapon dropping',
        'recovery frame 2, return to idle',
    ],
    'hit_react': [
        'standing, just hit, slight stagger',
        'recoiling backward, weight shifting',
        'maximum recoil, body leaning back',
        'hold pose, mid-stagger',
        'recovery start, regaining balance',
        'foot replant, stable footing',
        'body straightening',
        'return to idle stance',
    ],
    'death': [
        'standing, mortal blow',
        'staggering, knees buckling',
        'falling forward, hands reaching down',
        'on knees, body slumping',
        'falling sideways, partially on ground',
        'fully on ground, twitching',
        'still on ground, settling',
        'death pose, no movement',
    ],
    'idle_breath': [
        'idle stance neutral, breathing in',
        'chest rising slightly',
        'top of breath, chest expanded',
        'breath held briefly',
        'breathing out, chest lowering',
        'mid exhale, slight shoulder drop',
        'end of exhale, shoulders down',
        'pause, returning to neutral',
    ],
}

ANIM_FRAME_RATES = {
    'walk': 12, 'attack_light': 18, 'attack_heavy': 14,
    'hit_react': 16, 'death': 8, 'idle_breath': 6,
}

# Mapping: Tool-anim-name → Engine-anim-name (fuer Output-Pfad).
# Engine erwartet Folder-Namen aus sf/sprite_animation.ANIM_CONFIG.
ANIM_TO_ENGINE_FOLDER = {
    'walk':         'walk',
    'attack_light': 'attack',
    'attack_heavy': 'attack_heavy',   # bleibt eigener Folder
    'hit_react':    'hit',
    'death':        'death',
    'idle_breath':  'idle',
}

# Engine-Direction-Konvention (sf/sprites.py: down/up/left/right).
# Tool-CLI nimmt traditionell S/E/N/W; wir mappen intern.
DIR_TO_LOWER = {
    'S': 'down', 'N': 'up', 'E': 'right', 'W': 'left',
    # Plus passthrough fuer User die schon lowercase eingeben
    'down': 'down', 'up': 'up', 'left': 'left', 'right': 'right',
}

# Animations die KEIN Direction-Set brauchen (1 Strip statt 4)
NON_DIRECTIONAL_ANIMS = {'death'}

# Update #167: DIRECTION_DESC + MASTER_NEGATIVE werden zentral aus
# sf/render_spec.py importiert. WICHTIG: Alle Klassen-Sprites + Mob-Sprites +
# Welt-Tiles sind in 3/4-Top-Down-ARPG-Perspektive (D2/POE2/Hades) —
# Eye-Level Side-Views passen NICHT zum Tile-System. Single-Source-of-Truth
# verhindert dass das aus Versehen weggepatcht wird.
from sf.render_spec import DIRECTION_DESC, MASTER_NEGATIVE as _SPEC_MASTER_NEG  # noqa: E402

MASTER_NEGATIVE = _SPEC_MASTER_NEG + ' , ' + (
    'multiple characters, background scene, environment, watermark, text, '
    'cropped, partial body'
)


# ============================================================
# WORKFLOW
# ============================================================
class AnimationFramesWorkflow(WorkflowBase):
    workflow_name = 'animation_frames'

    def __init__(self, *, target: str, anim: str, direction: str = 'S',
                  category: str = 'class', frame_size: int = 512,
                  keep_sheets_copy: bool = False, **kw):
        super().__init__(**kw)
        self.target = target
        self.anim = anim
        self.direction = direction
        self.category = category
        self.frame_size = frame_size
        self.keep_sheets_copy = keep_sheets_copy

    def _engine_output_path(self) -> Path:
        """Update #168: Direkt in den Engine-Pfad schreiben.
        `assets/sprites/classes/<target>_anims/<engine_anim>/<dir>.png`
        bzw. `<engine_anim>/all.png` fuer non-directional anims (death).
        """
        engine_anim = ANIM_TO_ENGINE_FOLDER.get(self.anim, self.anim)
        anims_dir = SPRITES_DIR / 'classes' / f'{self.target}_anims' / engine_anim
        if engine_anim in NON_DIRECTIONAL_ANIMS:
            return anims_dir / 'all.png'
        dir_lower = DIR_TO_LOWER.get(self.direction, self.direction.lower())
        return anims_dir / f'{dir_lower}.png'

    def _find_anchor_png(self) -> Path | None:
        # Priorisiere 4-Dir-Sheet wenn vorhanden (Sub-Sprite extrahieren waere
        # eine v2-Feature — vorerst: einfacher Anchor aus assets/sprites/)
        cat_dir = SPRITES_DIR / (
            'classes' if self.category == 'class' else self.category + 's'
        )
        candidate = cat_dir / f'{self.target}.png'
        if candidate.is_file():
            return candidate
        for p in SPRITES_DIR.rglob(f'{self.target}*.png'):
            return p
        return None

    def run(self) -> dict:
        anchor = self._find_anchor_png()
        if anchor is None:
            err = f'Kein Anchor fuer target={self.target}'
            self.log_run(args=self._args_dict(), outputs=[], status='failed',
                         error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': 0.0}

        if self.anim not in ANIM_FRAME_PROMPTS:
            err = f'Unbekannter anim-type: {self.anim}'
            self.log_run(args=self._args_dict(), outputs=[], status='failed',
                         error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': 0.0}

        print(f'    anchor: {anchor.relative_to(PROJECT_ROOT)}')

        ref_id = None
        if not self.dry_run:
            ref_id = upload_asset(anchor)
            if not ref_id:
                err = 'Upload failed'
                self.log_run(args=self._args_dict(), outputs=[],
                             status='failed', error=err)
                return {'status': 'failed', 'outputs': [], 'error': err,
                        'cost_eur': 0.0}

        # 8 Frame-Inferences
        phase_prompts = ANIM_FRAME_PROMPTS[self.anim]
        dir_desc = DIRECTION_DESC.get(self.direction, DIRECTION_DESC['S'])
        tmp_dir = SHEETS_DIR / '_tmp' / f'{self.target}_{self.anim}_{self.direction}'
        tmp_dir.mkdir(parents=True, exist_ok=True)
        frame_paths: list[Path] = []
        for i, phase in enumerate(phase_prompts):
            prompt = (
                f'same character as reference, {dir_desc}, {phase}, '
                f'consistent style and proportions, '
                f'ARPG character sprite in Path of Exile 2 / Hades style '
                f'three-quarter top-down camera, head closer to camera than feet, '
                f'character viewed from slightly above eye level, '
                f'transparent background, single frame in animation cycle, '
                f'not flat eye-level portrait, not pixel art isometric'
            )
            out_path = tmp_dir / f'frame_{i+1:02d}.png'
            ok = self.run_inference_to_file(
                prompt, out_path,
                category=self.category,
                width=self.frame_size, height=self.frame_size,
                steps=25, guidance=7.0,
                negative_prompt=MASTER_NEGATIVE,
                reference_asset_ids=[ref_id] if ref_id else None,
            )
            if not ok:
                print(f'    frame {i+1} FAIL', file=sys.stderr)
                continue
            frame_paths.append(out_path)

        if not frame_paths and not self.dry_run:
            err = 'keine Frames generiert'
            self.log_run(args=self._args_dict(), outputs=[], status='failed',
                         error=err)
            return {'status': 'failed', 'outputs': [], 'error': err,
                    'cost_eur': cost_estimate(len(self.inference_ids))}

        # Composit zu 1×8-Strip — direkt am Engine-Pfad ablegen.
        engine_out = self._engine_output_path()
        engine_out.parent.mkdir(parents=True, exist_ok=True)
        composit_grid(
            frame_paths, cols=8, rows=1,
            cell_w=self.frame_size, cell_h=self.frame_size,
            out_path=engine_out, bg_alpha=0,
        )

        outputs = [str(engine_out.relative_to(PROJECT_ROOT)).replace('\\', '/')]

        # Optional: zusaetzliche Kopie in den alten sheets/-Pfad (Audit-Trail).
        if self.keep_sheets_copy:
            sheet_name = (f'{self.target}_{self.anim}_'
                          f'{self.direction}_8f.png')
            out_sheet = SHEETS_DIR / sheet_name
            out_sheet.parent.mkdir(parents=True, exist_ok=True)
            composit_grid(
                frame_paths, cols=8, rows=1,
                cell_w=self.frame_size, cell_h=self.frame_size,
                out_path=out_sheet, bg_alpha=0,
            )
            outputs.append(
                str(out_sheet.relative_to(PROJECT_ROOT)).replace('\\', '/'))

        # Meta-JSON neben Engine-Output (gleicher Basename, .meta.json)
        meta = {
            'target':     self.target,
            'anim':       self.anim,
            'direction':  self.direction,
            'engine_anim': ANIM_TO_ENGINE_FOLDER.get(self.anim, self.anim),
            'frame_count': 8,
            'frame_size': self.frame_size,
            'fps_hint':   ANIM_FRAME_RATES.get(self.anim, 12),
        }
        import json
        meta_path = engine_out.with_suffix('.png.meta.json')
        meta_path.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False), encoding='utf-8')

        self.log_run(args=self._args_dict(), outputs=outputs, status='success')
        return {
            'status': 'success', 'outputs': outputs,
            'cost_eur': cost_estimate(len(self.inference_ids)),
        }

    def _args_dict(self) -> dict:
        return {
            'target':    self.target,
            'anim':      self.anim,
            'direction': self.direction,
            'category':  self.category,
        }


# ============================================================
# CLI
# ============================================================
CLASS_TARGETS = ['warrior', 'witch', 'sorceress', 'monk', 'ranger',
                  'mercenary', 'huntress', 'druid']
ALL_DIRECTIONS = ['S', 'E', 'N', 'W']
LOWER_DIRECTIONS = ['down', 'up', 'left', 'right']


def main():
    ap = argparse.ArgumentParser(
        description='Animation Frames (8-Frame Walk/Attack Cycle)')
    ap.add_argument('--target', type=str, default=None)
    ap.add_argument('--anim', type=str, default='walk',
                    choices=list(ANIM_FRAME_PROMPTS.keys()))
    ap.add_argument('--dir', dest='direction', type=str, default='S',
                    choices=ALL_DIRECTIONS + LOWER_DIRECTIONS,
                    help='S/E/N/W (klassisch) oder down/up/left/right')
    ap.add_argument('--dirs', type=str, default=None,
                    help='Komma-separierte Liste, z.B. "left,right" oder '
                         '"W,E". Ueberschreibt --dir wenn gesetzt.')
    ap.add_argument('--all-dirs', action='store_true',
                    help='Alle 4 Richtungen batch')
    ap.add_argument('--all-classes', action='store_true')
    ap.add_argument('--frame-size', type=int, default=512)
    ap.add_argument('--category', type=str, default='class')
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--model', type=str, default=None)
    ap.add_argument('--keep-sheets-copy', action='store_true',
                    help='Zusaetzlich in assets/sprites/sheets/ ablegen '
                         '(Audit-Trail). Default: nur Engine-Pfad.')
    args = ap.parse_args()

    targets = CLASS_TARGETS if args.all_classes else (
        [args.target] if args.target else [])
    if not targets:
        print('Bitte --target oder --all-classes angeben.')
        return
    if args.all_dirs:
        directions = ALL_DIRECTIONS
    elif args.dirs:
        raw = [d.strip() for d in args.dirs.split(',') if d.strip()]
        valid = set(ALL_DIRECTIONS) | set(LOWER_DIRECTIONS)
        bad = [d for d in raw if d not in valid]
        if bad:
            print(f'Unbekannte direction(s): {bad}. '
                  f'Erlaubt: {ALL_DIRECTIONS + LOWER_DIRECTIONS}')
            return
        directions = raw
    else:
        directions = [args.direction]

    total_inferences = len(targets) * len(directions) * 8
    total_cost = cost_estimate(total_inferences)
    print('=' * 60)
    print(f'  Animation Frames — {args.anim}')
    print(f'  Targets:    {", ".join(targets)}')
    print(f'  Directions: {", ".join(directions)}')
    print(f'  Inference-Calls: {total_inferences}')
    print(f'  Cost-Estimate:   {total_cost:.2f} EUR')
    print('=' * 60)

    if args.dry_run:
        print('DRY-RUN — keine API-Calls.')
        return

    for target in targets:
        for direction in directions:
            print(f'\n  Generate {target} {args.anim} {direction} ...')
            wf = AnimationFramesWorkflow(
                target=target, anim=args.anim, direction=direction,
                category=args.category, frame_size=args.frame_size,
                keep_sheets_copy=args.keep_sheets_copy,
                dry_run=args.dry_run, model_override=args.model,
            )
            result = wf.run()
            print(f'    {result["status"]}: {result["outputs"]} '
                  f'(cost {result["cost_eur"]:.2f} EUR)')


if __name__ == '__main__':
    main()
