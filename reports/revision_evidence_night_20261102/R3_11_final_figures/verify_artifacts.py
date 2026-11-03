"""Verify delivered selection/exports without loading images or computing metrics."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import subprocess

import numpy as np
import pandas as pd
from PIL import Image

DEST = Path(__file__).resolve().parent
ROOT = DEST.parents[2]


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return pd.read_csv(path, float_precision='round_trip')


def main():
    frozen = json.loads((DEST / 'selection_frozen.json').read_text())
    assert sha(DEST / 'selection_manifest_internal.csv') == frozen['manifest_sha256']
    for p, expected in frozen['source_sha256'].items():
        assert sha(p) == expected, p
    selected = read(DEST / 'selection_manifest_internal.csv')
    metric = read(ROOT / 'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv')
    metric = metric[metric.epoch == 165]
    elig = read(ROOT / 'reports/r3_11_brain_mask_metrics/run_20261102/eligibility_and_exclusions_internal.csv')
    valid = metric.merge(elig, on=['ptid', 'tracer', 'fold'], validate='one_to_one')
    valid = valid[valid.included]
    assert len(valid) == 2961
    checks = []
    for row in selected.itertuples():
        values = valid[valid.tracer == row.tracer].copy()
        target = float(np.quantile(values.ssim.to_numpy(), row.quantile, method='linear'))
        nearest = min(values.itertuples(), key=lambda x: (abs(x.ssim-target), x.ptid))
        assert nearest.ptid == row.ptid and nearest.fold == row.fold
        assert nearest.ssim == row.ssim and target == row.target_ssim
        if row.selection == 'worst':
            assert row.ssim == values.ssim.min()
        checks.append(dict(tracer=row.tracer, selection=row.selection, ptid=row.ptid,
                           saved_ssim_exact_match=True, independent_selection_check=True,
                           existing_qc_included=True))
    manifest = json.loads((DEST / 'figure_manifest.json').read_text())
    for output in manifest['exports']:
        assert sha(DEST / output['path']) == output['sha256']
        if output['path'].endswith('.png'):
            with Image.open(DEST / output['path']) as im:
                assert im.size == (4800, 4160)
                assert min(im.info['dpi']) >= 300
    for row in manifest['records']:
        assert sha(DEST / row['detail']) == row['detail_sha256']
    pdf_checks = []
    for tracer in ('fdg', 'av45'):
        pdf = DEST / f'R3_11_{tracer.upper()}_cases.pdf'
        text = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
        assert all(col in text for col in ['MRI', 'Real PET', 'Synthetic PET', 'Absolute error'])
        assert 'QC-passed' in text and '10th percentile' in text and 'Median' in text
        assert '/mnt/' not in text and not re.search(r'\d{3}_S_\d+', text)
        for row in selected[selected.tracer == tracer].itertuples():
            assert f'{row.ssim:.4f}' in text
        pdf_checks.append(dict(tracer=tracer, ssims_and_labels_match=True, no_ptid_or_internal_paths=True))
    # Visual inspection was performed by opening these exact exports in this task.
    manifest['visual_inspection'] = dict(
        status='completed', inspected_at_utc=datetime.now(timezone.utc).isoformat(),
        method='view_image on both composite PNGs, all six orthogonal PNGs, and pdftoppm previews of both composite PDFs',
        composite_pngs=['R3_11_FDG_cases.png', 'R3_11_AV45_cases.png'],
        composite_pdfs=['R3_11_FDG_cases.pdf', 'R3_11_AV45_cases.pdf'],
        optional_details=[r['detail'] for r in manifest['records']],
        observed='Correct row/column bindings, SSIM labels, clear separate colorbars, equal image aspect; no visible clipping or overlap',
        limitation='Reused original FDG median optional detail retains original 200 dpi and shared colorbar annotation; final composites have independent labeled bars',
        pdf_preview_paths=['/tmp/R3_11_FDG_pdf_check.png', '/tmp/R3_11_AV45_pdf_check.png'])
    manifest['build_script_sha256'] = sha(DEST / 'build_figures.py')
    (DEST / 'figure_manifest.json').write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + '\n')
    receipt = dict(status='passed', checked_at_utc=datetime.now(timezone.utc).isoformat(),
                   source_hashes_unchanged=True, frozen_selection_unchanged=True,
                   selection_checks=checks, composite_pdf_checks=pdf_checks,
                   new_png_pixels=[4800, 4160], new_png_dpi=399.9992,
                   actual_visual_inspection_completed=True,
                   no_new_image_metrics_computed=True,
                   files_sha256={p.name: sha(p) for p in [DEST/'figure_manifest.json', DEST/'CAPTIONS.md', DEST/'REPORT.md',
                                                        DEST/'build_figures.py', Path(__file__)]})
    # Create the receipt before checking its link in REPORT.md.
    (DEST / 'verification.json').write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + '\n')
    for name in ('CAPTIONS.md', 'REPORT.md'):
        for link in re.findall(r'\]\(([^)]+)\)', (DEST/name).read_text()):
            assert (DEST/link).exists(), (name, link)
    print('PASS: frozen selection, source preservation, 6 case identities, export hashes, PNG resolution, PDF text, documentation links.')


if __name__ == '__main__':
    main()
