"""Restore supplied filled-table metadata without choosing an arbitrary image.

Only the two user-specified CSVs control the linkage. Original values and all
demographic-anchor candidates are retained, including observed-score conflicts.
No fuzzy matching, score imputation, visit substitution or NIfTI identity claim.
"""
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
BASE = REPO / 'source_archive/vscode-3003/home/data/liutuo/code/liutuo_data'
SOURCE = BASE / 'ADNI MRI and FDG and AV45 csv.csv'
FILLED = BASE / 'filtered_subjects_filled.csv'
ANCHORS = ['Subject ID', 'Sex', 'Weight', 'Research Group', 'Age']
SCORES = ['MMSE Total Score', 'GDSCALE Total Score', 'Global CDR',
          'FAQ Total Score', 'NPI-Q Total Score']
NUMERIC = {'Weight', 'Age', *SCORES}
LOST = ['Phase', 'Modality', 'Description', 'Imaging Protocol', 'Image ID']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def norm(value, column):
    value = value.strip()
    if not value:
        return None
    return Decimal(value) if column in NUMERIC else value


def key(row):
    return tuple(norm(row[c], c) for c in ANCHORS)


def write_csv(name, columns, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def arr(values):
    return json.dumps(list(values), ensure_ascii=False)


def unique(values):
    return list(dict.fromkeys(values))


def tracer(row):
    """Description tokens only; generic PET descriptions remain unknown."""
    if row['Modality'].strip().upper() == 'MRI':
        return 'MRI'
    if row['Modality'].strip().upper() != 'PET':
        return 'OTHER_MODALITY'
    text = row['Description']
    found = []
    for name, pattern in [
        ('AV45', r'AV[\s_-]?45(?!\d)|florbetapir'),
        ('FDG', r'FDG|fluorodeoxyglucose'),
        ('FBB', r'\bFBB\b|florbetaben'),
        ('TAU', r'AV[\s_-]?1451\b|flortaucipir|\bFTP\b'),
        ('PIB', r'\bPIB\b'),
    ]:
        if re.search(pattern, text, flags=re.I):
            found.append(name)
    return 'PET_' + found[0] if len(found) == 1 else (
        'PET_MULTIPLE_TOKENS' if found else 'PET_TRACER_UNSPECIFIED')


def consensus(rows, column):
    values = unique(r[column] for r in rows if r[column].strip())
    nmissing = sum(not r[column].strip() for r in rows)
    if not values:
        return '', 'unavailable_in_source'
    if len(values) == 1 and nmissing == 0:
        return values[0], 'unanimous_at_demographic_anchor'
    if len(values) == 1:
        return '', 'one_observed_value_but_some_source_rows_missing'
    return '', 'ambiguous_multiple_source_values'


def main():
    hashes = {str(p.relative_to(REPO)): sha(p) for p in [SOURCE, FILLED]}
    source_columns, source = read_csv(SOURCE)
    filled_columns, filled = read_csv(FILLED)
    assert set(filled_columns) == set(ANCHORS + SCORES)
    assert all(c in source_columns for c in filled_columns + LOST)
    assert len({r['Subject ID'] for r in filled}) == len(filled)
    assert len({r['Image ID'] for r in source}) == len(source)
    assert all(norm(r[c], c) is not None for r in filled for c in filled_columns)
    grouped = defaultdict(list)
    subject_rows = defaultdict(list)
    for i, row in enumerate(source):
        grouped[key(row)].append((i + 1, row))
        subject_rows[row['Subject ID']].append(row)

    restored, candidate_rows, conflict_cells, evidence_rows = [], [], [], []
    for fi, f in enumerate(filled, 1):
        matches = grouped.get(key(f), [])
        evaluated = []
        for si, s in matches:
            observed = [c for c in SCORES if norm(s[c], c) is not None]
            missing = [c for c in SCORES if norm(s[c], c) is None]
            conflicts = [c for c in observed if norm(s[c], c) != norm(f[c], c)]
            status = ('observed_score_conflict' if conflicts else
                      'all_ten_retained_fields_equal' if len(observed) == len(SCORES) else
                      'demographics_only_all_source_scores_missing' if not observed else
                      'observed_scores_equal_source_has_missing_scores')
            for c in conflicts:
                conflict_cells.append(dict(filled_csv_record_1based=fi,
                                           source_csv_record_1based=si,
                                           ptid=f['Subject ID'], image_id=s['Image ID'],
                                           modality=s['Modality'], description=s['Description'],
                                           variable=c, filled_value=f[c], source_observed_value=s[c],
                                           resolution='retained_as_conflicting_anchor_candidate; not overwritten'))
            candidate = dict(s)
            candidate.update(filled_csv_record_1based=fi, source_csv_record_1based=si,
                             candidate_basis='exact Subject ID + Sex + Weight + Research Group + Age',
                             score_comparison_status=status, score_compatible=not conflicts,
                             source_observed_score_count=len(observed),
                             equal_observed_score_count=len(observed) - len(conflicts),
                             observed_score_fields=arr(observed), source_missing_score_fields=arr(missing),
                             conflicting_score_fields=arr(conflicts),
                             tracer_from_description=tracer(s),
                             nifti_identity_status='not_verified_against_current_nifti')
            candidate.update({f'filled__{c}': f[c] for c in SCORES})
            candidate_rows.append(candidate)
            evaluated.append(candidate)
        compatible = [r for r in evaluated if r['score_compatible']]
        r = dict(f)
        r.update(filled_csv_record_1based=fi,
                 anchor_source_record_count=len(matches),
                 score_compatible_source_record_count=len(compatible),
                 score_conflicting_source_record_count=len(evaluated) - len(compatible),
                 all_ten_fields_equal_source_record_count=sum(
                     s['score_comparison_status'] == 'all_ten_retained_fields_equal' for s in evaluated),
                 max_observed_score_count_among_compatible=max(
                     (s['source_observed_score_count'] for s in compatible), default=0),
                 restoration_status=('unique_source_record_at_demographic_anchor' if len(matches) == 1 else
                                     'multiple_source_records_at_demographic_anchor' if matches else
                                     'unmatched_demographic_anchor'),
                 nifti_identity_status='not_verified_against_current_nifti',
                 candidate_image_ids=arr(s['Image ID'] for _, s in matches),
                 score_compatible_image_ids=arr(s['Image ID'] for s in compatible),
                 score_conflicting_image_ids=arr(s['Image ID'] for s in evaluated if not s['score_compatible']),
                 candidate_source_csv_records_1based=arr(si for si, _ in matches))
        for c in LOST:
            value, state = consensus([s for _, s in matches], c)
            r[c] = value
            r[f'{c}__restoration_status'] = state
            value, state = consensus(compatible, c)
            r[f'score_compatible__{c}'] = value
            r[f'score_compatible__{c}__restoration_status'] = state
        r['candidate_descriptions'] = arr(unique(s['Description'] for _, s in matches))
        r['candidate_modalities'] = arr(unique(s['Modality'] for _, s in matches))
        r['candidate_phases'] = arr(unique(s['Phase'] for _, s in matches))
        r['same_subject_other_anchor_source_record_count'] = len(subject_rows[f['Subject ID']]) - len(matches)
        for label in ['MRI', 'PET_AV45', 'PET_FDG', 'PET_TRACER_UNSPECIFIED',
                      'PET_FBB', 'PET_TAU', 'PET_PIB', 'PET_MULTIPLE_TOKENS', 'OTHER_MODALITY']:
            r[f'candidate_image_ids__{label}'] = arr(s['Image ID'] for s in evaluated
                                                   if s['tracer_from_description'] == label)
        for c in SCORES:
            observed = [s[c] for _, s in matches if norm(s[c], c) is not None]
            normalized = unique(norm(v, c) for v in observed)
            original_value = observed[0] if len(normalized) == 1 else ''
            status = ('not_observed_at_anchor' if not normalized else
                      'multiple_conflicting_source_observations' if len(normalized) > 1 else
                      'source_observation_equals_filled' if normalized[0] == norm(f[c], c) else
                      'source_observation_differs_from_filled')
            r[f'source_observed__{c}'] = original_value
            r[f'source_evidence__{c}'] = status
            evidence_rows.append(dict(filled_csv_record_1based=fi, ptid=f['Subject ID'], variable=c,
                                      filled_value=f[c], source_observed_value=original_value,
                                      source_observed_values=arr(str(v) for v in normalized),
                                      status=status,
                                      source_records_observed=arr(si for si, s in matches
                                                                  if norm(s[c], c) is not None),
                                      source_records_missing=arr(si for si, s in matches
                                                                 if norm(s[c], c) is None)))
        restored.append(r)

    candidate_columns = source_columns + [c for c in candidate_rows[0] if c not in source_columns]
    write_csv('filled_restored.csv', list(restored[0]), restored)
    write_csv('anchor_source_candidates.csv', candidate_columns, candidate_rows)
    compatible_rows = [r for r in candidate_rows if r['score_compatible']]
    write_csv('score_compatible_source_candidates.csv', candidate_columns, compatible_rows)
    write_csv('observed_score_conflicts.csv', list(conflict_cells[0]), conflict_cells)
    write_csv('clinical_field_evidence.csv', list(evidence_rows[0]), evidence_rows)
    unique_rows = [r for r in restored if r['anchor_source_record_count'] == 1]
    write_csv('unique_source_record_restorations.csv', list(restored[0]), unique_rows)

    summary = dict(created_at_utc=datetime.now(timezone.utc).isoformat(),
                   source_paths_and_sha256=hashes, script_sha256=sha(Path(__file__)),
                   anchor_columns=ANCHORS, score_columns=SCORES,
                   comparison='exact Decimal equality for numeric fields; trimmed text equality; no tolerance',
                   missing_score_rule='blank source scores remain unknown, never equal to a filled observation',
                   source_rows=len(source), source_subjects=len(subject_rows),
                   filled_rows=len(filled), matched_subjects=sum(bool(r['anchor_source_record_count']) for r in restored),
                   anchor_source_candidates=len(candidate_rows), score_compatible_source_candidates=len(compatible_rows),
                   compatible_subjects=len({r['Subject ID'] for r in compatible_rows}),
                   unique_source_record_subjects=len(unique_rows),
                   unique_source_record_after_score_comparison_subjects=sum(
                       r['score_compatible_source_record_count'] == 1 for r in restored),
                   fully_observed_ten_field_equal_rows=sum(
                       r['score_comparison_status'] == 'all_ten_retained_fields_equal' for r in candidate_rows),
                   fully_observed_ten_field_equal_subjects=len({r['Subject ID'] for r in candidate_rows
                       if r['score_comparison_status'] == 'all_ten_retained_fields_equal'}),
                   candidate_score_status_counts=dict(Counter(r['score_comparison_status'] for r in candidate_rows)),
                   observed_score_conflict_candidate_rows=sum(not r['score_compatible'] for r in candidate_rows),
                   observed_score_conflict_cells=len(conflict_cells),
                   observed_score_conflict_subjects=len({r['ptid'] for r in conflict_cells}),
                   clinical_field_evidence_counts={c: dict(Counter(r['status'] for r in evidence_rows
                                                                   if r['variable'] == c)) for c in SCORES},
                   lost_field_restoration_status_counts={c: dict(Counter(r[f'{c}__restoration_status']
                                                                         for r in restored)) for c in LOST},
                   score_compatible_field_restoration_status_counts={c: dict(Counter(
                       r[f'score_compatible__{c}__restoration_status'] for r in restored)) for c in LOST},
                   phase_counts=dict(Counter(r['Phase'] for r in restored)),
                   anchor_candidate_count_distribution=dict(sorted(Counter(r['anchor_source_record_count']
                                                                           for r in restored).items())),
                   candidate_tracer_description_counts={label: dict(rows=sum(r['tracer_from_description'] == label
                                                                                               for r in candidate_rows),
                                                                   subjects=len({r['Subject ID'] for r in candidate_rows
                                                                         if r['tracer_from_description'] == label}))
                                                        for label in sorted({r['tracer_from_description'] for r in candidate_rows})},
                   limitations=['Image/Series ID of actual NIfTI still needs file-level linkage.',
                                'Source CSV has no acquisition dates or Series ID.',
                                'Imaging Protocol is empty in the supplied source.',
                                'Same clinical anchor is not a verified acquisition visit.',
                                'Generic PET descriptions do not establish tracer identity.',
                                'Missing original observations are not reconstructed or reimputed.'])
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')

    # Independent output-to-input checks use the saved row references and csv
    # strings, not the join's constructed keys. No source values are overwritten.
    _, saved_main = read_csv(OUT / 'filled_restored.csv')
    _, saved_long = read_csv(OUT / 'anchor_source_candidates.csv')
    assert len(saved_main) == len(filled)
    assert all({c: r[c] for c in filled_columns} == f for r, f in zip(saved_main, filled))
    assert len(saved_long) == len(candidate_rows)
    assert len({r['Image ID'] for r in saved_long}) == len(saved_long)
    for r in saved_long:
        s = source[int(r['source_csv_record_1based']) - 1]
        f = filled[int(r['filled_csv_record_1based']) - 1]
        assert all(r[c] == s[c] for c in source_columns)
        assert s['Subject ID'] == f['Subject ID']
        assert all(norm(s[c], c) == norm(f[c], c) for c in ANCHORS)
        assert all(r[f'filled__{c}'] == f[c] for c in SCORES)
    assert all(r['score_compatible_source_record_count'] > 0 for r in restored)
    assert all(sha(REPO / path) == digest for path, digest in hashes.items())
    validation = dict(original_filled_values_preserved=True, original_source_columns_preserved=True,
                      source_record_references_checked=len(saved_long),
                      output_subject_count_checked=len(saved_main), all_subjects_have_compatible_candidates=True,
                      source_hashes_unchanged=True,
                      output_sha256={p.name: sha(p) for p in sorted(OUT.glob('*.csv'))})
    (OUT / 'validation.json').write_text(json.dumps(validation, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ['filled_rows', 'matched_subjects', 'anchor_source_candidates',
                                             'score_compatible_source_candidates', 'unique_source_record_subjects',
                                             'observed_score_conflict_subjects', 'lost_field_restoration_status_counts']},
                     ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
