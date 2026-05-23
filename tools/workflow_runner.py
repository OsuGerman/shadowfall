"""Shared infrastructure fuer Scenario.gg Workflow-Runner.

Wird von workflow_character_sheet.py, workflow_animation_frames.py,
workflow_texture_tiler.py und workflow_inpaint.py importiert.

Liefert:
  - WorkflowBase: Abstrakte Basis-Klasse mit submit/poll/download
  - composit_grid(): PNG-Sprite-Sheet-Compositor (cols x rows)
  - upload_asset(): Reference-Image hochladen fuer img2img/referenceImages
  - audit_log(): Append-Only JSON-Log in assets/workflow_runs.json
  - cost_estimate(): Pro-Workflow EUR-Schaetzung

Doku: VELGRAD_WORKFLOWS_BIBEL.md
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from tools.scenario_config import (  # noqa: E402
    PROJECT_ROOT, SPRITES_DIR, API_BASE, auth_header, model_for_category,
)

# ============================================================
# KONSTANTEN
# ============================================================
WORKFLOW_RUNS_JSON = PROJECT_ROOT / 'assets' / 'workflow_runs.json'
SHEETS_DIR         = SPRITES_DIR / 'sheets'
MASKS_DIR          = SPRITES_DIR / 'tiles' / 'masks'

POLL_INTERVAL_SEC  = 3.0
POLL_TIMEOUT_SEC   = 300.0
HTTP_TIMEOUT_SEC   = 60.0

# Cost-Modell (EUR pro Inference-Call, ungefaehr fuer creator-Plan)
COST_PER_INFERENCE_EUR = 0.04   # ~5000 Bilder fuer 200 EUR/Monat

# Workflow-Kategorien — fuer audit_log + Cost-Estimate
WORKFLOW_NAMES = {
    'character_sheet':   'Character Sheet Generator (4-Direction)',
    'animation_frames':  'Sprite Animation Frames (8-Frame Cycle)',
    'texture_tiler':     'Texture Tiler (16-Mask Modular)',
    'inpaint':           'Inpaint / Outpaint',
}


# ============================================================
# HTTP-HELPERS (re-used von sprite_gen.py-Pattern)
# ============================================================
def _http_json(method: str, url: str, headers: dict, body: dict | None = None,
               timeout: float = HTTP_TIMEOUT_SEC) -> tuple[int, dict | None]:
    """JSON-Request. Returnt (status_code, parsed_body_or_None)."""
    data = json.dumps(body).encode('utf-8') if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode('utf-8')
            return resp.status, json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        try:
            raw = e.read().decode('utf-8', errors='ignore')[:300]
        except Exception:
            raw = ''
        return e.code, {'error': raw}
    except (urllib.error.URLError, TimeoutError) as e:
        return 0, {'error': str(e)[:200]}


def _http_bytes(url: str, timeout: float = HTTP_TIMEOUT_SEC) -> bytes | None:
    """GET binary. Returnt bytes oder None."""
    try:
        req = urllib.request.Request(url, headers={'Accept': '*/*'})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except Exception:
        return None


# ============================================================
# ASSET-UPLOAD (Reference-Image fuer img2img / referenceImages)
# ============================================================
def upload_asset(png_path: Path) -> str | None:
    """Laedt PNG zu Scenario.gg hoch. Returnt asset_id oder None.

    Endpoint: POST /v1/assets
    Body: {"file": "<base64>", "name": "<filename>"}
    """
    if not png_path.is_file():
        print(f'    upload: file not found: {png_path}', file=sys.stderr)
        return None
    data = png_path.read_bytes()
    b64  = base64.b64encode(data).decode('ascii')
    headers = auth_header()
    payload = {
        'image': f'data:image/png;base64,{b64}',
        'name':  png_path.name,
    }
    code, body = _http_json('POST', f'{API_BASE}/assets', headers, payload,
                             timeout=120)
    if code not in (200, 201) or not body:
        print(f'    upload HTTP {code}', file=sys.stderr)
        return None
    asset = body.get('asset') or body
    return asset.get('id') or asset.get('assetId')


# ============================================================
# COMPOSIT (Sprite-Sheet aus N Sub-Sprites)
# ============================================================
def composit_grid(image_paths: list[Path], cols: int, rows: int,
                   cell_w: int, cell_h: int, out_path: Path,
                   bg_alpha: int = 0) -> bool:
    """Setzt N Bilder als (cols x rows)-Grid zusammen. Cell-Size cell_w x cell_h.

    Wird auf out_path geschrieben (PNG mit Alpha).
    bg_alpha=0 → transparent (default); fuer debug bg_alpha=255 schwarz.
    """
    # Pygame im Headless-Mode initialisieren (kein Display noetig)
    import os
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    import pygame  # noqa: E402
    if not pygame.get_init():
        pygame.init()
    if not pygame.display.get_init():
        pygame.display.set_mode((1, 1))

    sheet_w = cols * cell_w
    sheet_h = rows * cell_h
    sheet = pygame.Surface((sheet_w, sheet_h), pygame.SRCALPHA)
    if bg_alpha > 0:
        sheet.fill((0, 0, 0, bg_alpha))

    for i, p in enumerate(image_paths):
        if i >= cols * rows:
            break
        if p is None or not Path(p).is_file():
            continue
        try:
            sub = pygame.image.load(str(p))
        except pygame.error:
            continue
        # Auf cell_w x cell_h skalieren (Aspect-Ratio preserve, padding zentral)
        sw, sh = sub.get_size()
        if sw <= 0 or sh <= 0:
            continue
        scale = min(cell_w / sw, cell_h / sh)
        new_w = max(1, int(sw * scale))
        new_h = max(1, int(sh * scale))
        scaled = pygame.transform.smoothscale(sub, (new_w, new_h))
        col = i % cols
        row = i // cols
        bx = col * cell_w + (cell_w - new_w) // 2
        by = row * cell_h + (cell_h - new_h) // 2
        sheet.blit(scaled, (bx, by))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    pygame.image.save(sheet, str(out_path))
    return True


# ============================================================
# AUDIT-LOG
# ============================================================
def audit_log(workflow: str, args: dict, outputs: list[str],
              inference_ids: list[str], duration_sec: float,
              status: str = 'success', cost_eur: float = 0.0,
              error: str | None = None) -> None:
    """Append run zu assets/workflow_runs.json. Atomic via temp-file rename."""
    WORKFLOW_RUNS_JSON.parent.mkdir(parents=True, exist_ok=True)
    if WORKFLOW_RUNS_JSON.is_file():
        try:
            existing = json.loads(WORKFLOW_RUNS_JSON.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            existing = {'runs': []}
    else:
        existing = {'runs': []}
    runs = existing.setdefault('runs', [])
    runs.append({
        'timestamp':          datetime.now(timezone.utc).isoformat(),
        'workflow':           workflow,
        'workflow_label':     WORKFLOW_NAMES.get(workflow, workflow),
        'args':               args,
        'outputs':            outputs,
        'cost_estimate_eur':  round(cost_eur, 2),
        'scenario_inference_ids': inference_ids,
        'duration_sec':       round(duration_sec, 1),
        'status':             status,
        'error':              error,
    })
    # Atomic write
    tmp = WORKFLOW_RUNS_JSON.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False),
                    encoding='utf-8')
    tmp.replace(WORKFLOW_RUNS_JSON)


# ============================================================
# COST-ESTIMATE
# ============================================================
def cost_estimate(num_inferences: int) -> float:
    """EUR-Schaetzung fuer N Inference-Calls (auf creator-Plan)."""
    return num_inferences * COST_PER_INFERENCE_EUR


# ============================================================
# WORKFLOW-BASE
# ============================================================
class WorkflowBase:
    """Abstrakte Basis fuer alle 4 Velgrad-Workflows.

    Concrete subclasses implementieren `run()`. Diese Basis liefert:
      - submit_inference(prompt, ...) -> job_id
      - poll_job(job_id) -> {assetIds: [...]}
      - download_asset(asset_id, out_path) -> bool
      - log_run(args, outputs, ...) -> None
    """
    workflow_name: str = ''   # subclass setzt das

    def __init__(self, *, dry_run: bool = False, model_override: str | None = None):
        self.dry_run = dry_run
        self.model_override = model_override
        self.inference_ids: list[str] = []
        self.t_start = time.time()

    # -------- Submit ------------------------------------------------
    def submit_inference(self, prompt: str, *,
                         category: str = 'class',
                         width: int = 512, height: int = 512,
                         steps: int = 30, guidance: float = 7.0,
                         negative_prompt: str = '',
                         reference_asset_ids: list[str] | None = None,
                         strength: float | None = None,
                         inference_type: str = 'txt2img'
                         ) -> str | None:
        """Wrapper um Scenario POST /v1/models/<mid>/inferences.

        inference_type: txt2img | img2img | controlnet | mask
        reference_asset_ids: vorab via upload_asset() hochgeladene IDs
        """
        if self.dry_run:
            return 'dry-run-job-id'
        mid = self.model_override or model_for_category(category)
        headers = auth_header()
        params: dict = {
            'type':       inference_type,
            'prompt':     prompt,
            'width':      width,
            'height':     height,
            'numSamples': 1,
            'numInferenceSteps': steps,
            'guidance':   guidance,
            'modelId':    mid,
        }
        if negative_prompt:
            params['negativePrompt']         = negative_prompt
            params['negativePromptStrength'] = 1.0
        if reference_asset_ids:
            params['referenceAssets']  = reference_asset_ids
            params['referenceWeight']  = 0.85
        if strength is not None:
            params['strength'] = strength

        payload = {'parameters': params}
        url = f'{API_BASE}/models/{mid}/inferences'
        code, data = _http_json('POST', url, headers, payload, timeout=60)
        if code not in (200, 201, 202) or not data:
            print(f'    submit HTTP {code}: {str(data)[:120]}', file=sys.stderr)
            return None
        job = data.get('job') or data.get('inference') or data
        jid = (job.get('jobId') or job.get('id') or
               (data.get('inference') or {}).get('id'))
        if jid:
            self.inference_ids.append(jid)
        return jid

    # -------- Poll --------------------------------------------------
    def poll_job(self, job_id: str) -> dict | None:
        """Pollt /jobs/<job_id> bis success/failure. Returnt {assetIds:[...]}."""
        if self.dry_run:
            return {'assetIds': ['dry-run-asset']}
        headers = auth_header()
        url = f'{API_BASE}/jobs/{job_id}'
        t0 = time.time()
        while time.time() - t0 < POLL_TIMEOUT_SEC:
            code, data = _http_json('GET', url, headers, timeout=30)
            if code != 200 or not data:
                time.sleep(POLL_INTERVAL_SEC)
                continue
            job = data.get('job') or data
            status = (job.get('status') or '').lower()
            meta = job.get('metadata') or {}
            if status in ('success', 'succeeded', 'complete'):
                return {'assetIds': meta.get('assetIds') or []}
            if status in ('failed', 'failure', 'error', 'cancelled'):
                print(f'    job FAILED: {status}', file=sys.stderr)
                return None
            time.sleep(POLL_INTERVAL_SEC)
        print(f'    poll TIMEOUT after {POLL_TIMEOUT_SEC}s', file=sys.stderr)
        return None

    # -------- Download ----------------------------------------------
    def download_asset(self, asset_id: str, out_path: Path) -> bool:
        """GET /v1/assets/<id> → URL → download bytes → schreibe out_path."""
        if self.dry_run:
            return True
        headers = auth_header()
        code, data = _http_json('GET', f'{API_BASE}/assets/{asset_id}', headers,
                                  timeout=30)
        if code != 200 or not data:
            return False
        asset = data.get('asset') or data
        url = (asset.get('url') or asset.get('downloadUrl') or
               asset.get('signedUrl') or asset.get('imageUrl'))
        if not url:
            return False
        b = _http_bytes(url, timeout=60)
        if not b:
            return False
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b)
        return True

    # -------- Convenience -------------------------------------------
    def run_inference_to_file(self, prompt: str, out_path: Path,
                               **kwargs) -> bool:
        """End-to-end: submit + poll + download in einem Schritt."""
        jid = self.submit_inference(prompt, **kwargs)
        if not jid:
            return False
        result = self.poll_job(jid)
        if not result:
            return False
        assets = result.get('assetIds') or []
        if not assets:
            return False
        return self.download_asset(assets[0], out_path)

    # -------- Audit -------------------------------------------------
    def log_run(self, args: dict, outputs: list[str],
                status: str = 'success', error: str | None = None) -> None:
        duration = time.time() - self.t_start
        cost = cost_estimate(len(self.inference_ids))
        audit_log(
            self.workflow_name, args, outputs,
            self.inference_ids, duration,
            status=status, cost_eur=cost, error=error,
        )


# ============================================================
# CLI fuer Diagnose (zeigt aufgelaufene Runs)
# ============================================================
def _cli_show_runs():
    if not WORKFLOW_RUNS_JSON.is_file():
        print('Noch keine Workflow-Runs geloggt.')
        return
    data = json.loads(WORKFLOW_RUNS_JSON.read_text(encoding='utf-8'))
    runs = data.get('runs', [])
    print(f'\n{len(runs)} Workflow-Runs geloggt:\n')
    print(f'{"timestamp":<22} {"workflow":<18} {"status":<8} '
          f'{"cost":>6} {"calls":>5}  outputs')
    print('-' * 100)
    total_eur = 0.0
    for r in runs[-30:]:
        ts = r.get('timestamp', '')[:19]
        wf = r.get('workflow', '')[:17]
        st = r.get('status', '')[:7]
        cost = r.get('cost_estimate_eur', 0.0)
        calls = len(r.get('scenario_inference_ids') or [])
        outs = ', '.join(r.get('outputs') or [])[:40]
        print(f'{ts:<22} {wf:<18} {st:<8} {cost:>5.2f} {calls:>5}  {outs}')
        total_eur += cost
    print('-' * 100)
    print(f'  Total cost (all runs): {total_eur:.2f} EUR')


if __name__ == '__main__':
    _cli_show_runs()
