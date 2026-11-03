"""Derive inspectable candidate tables from the saved read-only 3003 inspection."""
import csv
import gzip
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parent
SNAPSHOT = ROOT / 'inspection_3003_20261103.json.gz'


def write_csv(name, rows):
    if not rows:
        raise ValueError(f'No rows for {name}')
    with (ROOT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    with gzip.open(SNAPSHOT, 'rt', encoding='utf-8') as f:
        d = json.load(f)
    log = [r for r in d['log_records'] if r['in_current_cohort']]
    by_subject = defaultdict(list)
    for r in log:
        by_subject[r['ptid']].append(r)
    write_csv('av45_historical_image_series_candidates.csv', log)
    inventory = []
    for r in d['nifti_headers']:
        inventory.append(dict(ptid=r['ptid'], modality=r['modality'], path=r['path'],
                              bytes=r['bytes'], shape='x'.join(map(str, r.get('shape', []))),
                              voxel_sizes_mm='x'.join(map(str, r.get('zooms', []))),
                              header_strings=json.dumps(r.get('header_strings', {})),
                              extensions=json.dumps(r.get('extensions', [])),
                              gzip_strings=json.dumps(r.get('gzip', {})),
                              embedded_identity_tokens=';'.join(r.get('embedded_identity_tokens', [])),
                              in_current_cohort=r['in_current_cohort'], error=r.get('error', '')))
    write_csv('nifti_header_inventory.csv', inventory)

    clock_rows = []
    for h in d['nifti_headers']:
        if h['modality'] != 'av45':
            continue
        candidates = by_subject[h['ptid']]
        description = h.get('header_strings', {}).get('descrip', '')
        m = re.search(r'Time=(\d+)(?:\.(\d+))?', description)
        header_clock = m[1].zfill(6) if m else ''
        matches = []
        if m:
            for c in candidates:
                parts = c['acquisition_directory_datetime'].split('_')
                log_clock = parts[1] + parts[2] + parts[3].split('.')[0]
                if header_clock == log_clock:
                    matches.append(c)
        if not candidates:
            status = 'no_historical_log_candidate'
        elif not m:
            status = 'no_header_clock'
        elif len(matches) == 1:
            status = 'unique_second_precision_clock_candidate_NOT_confirmed'
        elif matches:
            status = 'multiple_second_precision_clock_candidates_NOT_confirmed'
        else:
            status = 'no_second_precision_clock_match'
        unique = matches[0] if len(matches) == 1 else {}
        clock_rows.append(dict(ptid=h['ptid'], nifti_path=h['path'],
                               nifti_descrip=description, header_clock_hhmmss=header_clock,
                               comparison_precision='integer seconds; fractional seconds discarded',
                               log_candidate_count=len(candidates),
                               log_image_ids=';'.join(c['image_id'] for c in candidates),
                               clock_match_count=len(matches), match_status=status,
                               candidate_image_id=unique.get('image_id', ''),
                               candidate_series_id=unique.get('series_id', ''),
                               candidate_directory_datetime=unique.get('acquisition_directory_datetime', ''),
                               candidate_log_line=unique.get('first_log_line', ''),
                               limitation='Historical source candidate; current NIfTI identity unverified'))
    write_csv('av45_header_clock_candidates.csv', clock_rows)

    summary = dict(inspected_at_utc=d['inspected_at_utc'], sources=d['sources'],
                   inspection_script_sha256=hashlib.sha256((ROOT / 'inspect_3003.py').read_bytes()).hexdigest(),
                   snapshot_sha256=hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest(),
                   frozen_cohort_comparison=d['frozen_cohort_comparison'],
                   current_subjects=len(d['subjects']), nifti_files=len(d['nifti_headers']),
                   files_by_modality=dict(Counter(h['modality'] for h in d['nifti_headers'])),
                   header_error_count=len(d['header_errors']),
                   headers_with_identity_tokens=sum(bool(h.get('embedded_identity_tokens')) for h in d['nifti_headers']),
                   export_columns=d['export_columns'], export_total_rows=d['export_total_rows'],
                   export_total_subjects=d['export_total_subjects'],
                   export_current_rows=len(d['export_current_candidates']),
                   export_current_subjects=len({r['Subject ID'] for r in d['export_current_candidates']}),
                   export_caveat='Subject search candidates, multiple visits/tracers/processing stages; no direct NIfTI identity',
                   log_total_lines=d['log_total_lines'], log_unparsed_lines=len(d['log_unparsed']),
                   log_records_all=len(d['log_records']), log_records_current=len(log),
                   log_current_subjects=len({r['ptid'] for r in log}),
                   log_current_distinct_images=len({r['image_id'] for r in log}),
                   log_current_distinct_series=len({r['series_id'] for r in log}),
                   log_existing_source_path_count=sum(r['source_path_exists'] for r in d['log_records']),
                   log_image_id_disagreement_count=sum(r['image_id'] != r['filename_image_id'] for r in log),
                   clock_status_counts=dict(Counter(r['match_status'] for r in clock_rows)),
                   conclusions=['Current file identities remain unverified.',
                                'Second-precision clock matching is candidate evidence only.',
                                'Native-space/unstripped NIfTI does not establish raw acquisition or ADNI processing level.'])
    assert summary['header_error_count'] == 0
    assert summary['log_unparsed_lines'] == 0
    assert summary['log_image_id_disagreement_count'] == 0
    assert summary['log_current_subjects'] == sum(bool(v) for v in by_subject.values())
    assert len({(h['ptid'], h['modality']) for h in d['nifti_headers']}) == len(d['nifti_headers'])
    assert not d['frozen_cohort_comparison']['remote_only']
    assert not d['frozen_cohort_comparison']['frozen_only']
    (ROOT / 'summary_3003_20261103.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps({k: summary[k] for k in ['files_by_modality', 'log_records_current',
                                               'log_current_subjects', 'clock_status_counts']}, indent=2))


if __name__ == '__main__':
    main()
