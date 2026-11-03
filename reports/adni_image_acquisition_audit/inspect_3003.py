"""Read-only 3003 inspection; run with that node's xiaochou Python via SSH stdin.

Print JSON only. Reads NIfTI headers, never voxel arrays; modifies no remote files.
Image IDs from a subject-level search export and the historical DICOM log remain
candidates until an independent link to the current NIfTI has been established.
"""
from pathlib import Path
from collections import Counter
import csv
import gzip
import hashlib
import json
import re
import struct
from datetime import datetime, timezone

import nibabel as nib


BASE = Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')
LOG = Path('/home/data/liutuo/code/processed_files.txt')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def provenance(path):
    s = path.stat()
    return dict(path=str(path), bytes=s.st_size, mtime_ns=s.st_mtime_ns,
                sha256=digest(path))


def csv_rows(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def gzip_strings(path):
    with path.open('rb') as f:
        h = f.read(10)
        if len(h) != 10 or h[:2] != b'\x1f\x8b':
            return {}
        flags = h[3]
        if flags & 4:
            f.read(struct.unpack('<H', f.read(2))[0])
        result = {}
        for bit, key in [(8, 'filename'), (16, 'comment')]:
            if flags & bit:
                b = bytearray()
                while True:
                    c = f.read(1)
                    if c in (b'', b'\0'):
                        break
                    b.extend(c)
                result[key] = b.decode(errors='replace')
        return result


def main():
    cohort_path = BASE / 'filtered_subjects_with_description.csv'
    _, cohort = csv_rows(cohort_path)
    subjects = {r['Subject ID'] for r in cohort}
    export = BASE / 'ADNI MRI and FDG and AV45 csv.csv'
    columns, rows = csv_rows(export)
    current_candidates = [dict(r, source_csv_line=i + 2)
                          for i, r in enumerate(rows) if r['Subject ID'] in subjects]
    header_rows, errors = [], []
    for folder, modality in [('mri', 'mri'), ('PET1_AV45', 'av45'), ('PET2_FDG', 'fdg')]:
        for p in sorted((BASE / folder).iterdir()):
            r = dict(path=str(p), folder=folder, modality=modality,
                     bytes=p.stat().st_size)
            sid = re.search(r'\d{3}_S_\d+', p.name)
            r.update(ptid=sid.group() if sid else '', in_current_cohort=bool(sid and sid.group() in subjects))
            try:
                im = nib.load(str(p))
                h = im.header
                strings = {k: h[k].item().decode(errors='replace')
                           for k in ['data_type', 'db_name', 'descrip', 'aux_file', 'intent_name']}
                extensions = [dict(code=int(e.get_code()), content=str(e.get_content()))
                              for e in h.extensions]
                gz = gzip_strings(p)
                identity_text = json.dumps(dict(strings=strings, extensions=extensions, gzip=gz))
                identity_ids = sorted(set(re.findall(r'(?:\b|_)([IS]\d{4,})(?=\b|_)', identity_text)))
                r.update(shape=list(im.shape), zooms=[float(x) for x in h.get_zooms()],
                         header_strings=strings, extensions=extensions, gzip=gz,
                         embedded_identity_tokens=identity_ids)
            except Exception as e:
                r['error'] = repr(e)
                errors.append(dict(path=str(p), error=repr(e)))
            header_rows.append(r)

    grouped, unmatched = {}, []
    log_lines = 0
    for i, line in enumerate(LOG.open(), 1):
        log_lines = i
        sid = re.search(r'\d{3}_S_\d+', line)
        date = re.search(r'/(\d{4}-\d{2}-\d{2}_[^/]+)/', line)
        image_dir = re.search(r'/(I\d+)/', line)
        series = re.search(r'_S(\d+)_I(\d+)', line)
        if not all([sid, date, image_dir, series]):
            unmatched.append(dict(line=i, text=line.rstrip()))
            continue
        key = (sid.group(), date[1], image_dir[1], 'S' + series[1])
        if key not in grouped:
            grouped[key] = dict(ptid=key[0], acquisition_directory_datetime=key[1],
                                image_id=key[2], series_id=key[3],
                                in_current_cohort=key[0] in subjects,
                                first_log_line=i, source_dicom_path=line.rstrip(),
                                source_path_exists=Path(line.rstrip()).exists(), dicom_log_lines=0,
                                filename_image_id='I' + series[2],
                                historical_root=line[:sid.start()])
        grouped[key]['dicom_log_lines'] += 1

    log_records = list(grouped.values())
    local_cohort = Path('/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/e1_stage01_20261017/cohort.csv')
    local_identity = None
    if local_cohort.is_file():
        _, local_rows = csv_rows(local_cohort)
        local_ids = {r['ptid'] for r in local_rows}
        local_identity = dict(**provenance(local_cohort), subjects=len(local_ids),
                              remote_only=sorted(subjects - local_ids),
                              frozen_only=sorted(local_ids - subjects))
    output = dict(inspected_at_utc=datetime.now(timezone.utc).isoformat(),
                  remote_base=str(BASE), subjects=sorted(subjects),
                  sources=[provenance(p) for p in [cohort_path, export, LOG]],
                  frozen_cohort_comparison=local_identity,
                  export_columns=columns, export_total_rows=len(rows),
                  export_total_subjects=len({r['Subject ID'] for r in rows}),
                  export_current_candidates=current_candidates,
                  nifti_headers=header_rows, header_errors=errors,
                  log_total_lines=log_lines, log_records=log_records,
                  log_unparsed=unmatched)
    print(json.dumps(output, ensure_ascii=False))


if __name__ == '__main__':
    main()
