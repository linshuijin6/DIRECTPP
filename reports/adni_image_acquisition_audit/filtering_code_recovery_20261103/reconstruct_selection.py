"""Check historical selection against current CSVs; never run historical code.

Keep the earlier field-only candidate restoration unchanged. This new output
uses the recovered first-source-row rule and explicitly scopes Image ID to
the clinical metadata source, not to the actual NIfTI acquisition.
"""
from pathlib import Path
from collections import Counter
from decimal import Decimal
import csv
import hashlib
import json


OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
BASE = REPO / 'source_archive/vscode-3003/home/data/liutuo/code/liutuo_data'
SOURCE = BASE / 'ADNI MRI and FDG and AV45 csv.csv'
FILLED = BASE / 'filtered_subjects_filled.csv'
SCORES = ['MMSE Total Score', 'GDSCALE Total Score', 'Global CDR', 'FAQ Total Score', 'NPI-Q Total Score']
ANCHORS = ['Subject ID', 'Sex', 'Weight', 'Research Group', 'Age']
LOST = ['Phase', 'Modality', 'Description', 'Imaging Protocol', 'Image ID']
GROUPS = ['CN', 'EMCI', 'MCI', 'LMCI', 'AD']
# Literal support sets from recovered session 373 inputs 22--26.
# No random draws are generated. CDR input 24 has probabilities documented
# separately; support membership cannot recover the original random state.
RULES = {
    'MMSE Total Score': {'CN': [29, 30], 'EMCI': [27, 28], 'MCI': [26, 27], 'LMCI': [24, 25], 'AD': [19, 20, 21]},
    'GDSCALE Total Score': {'CN': [0], 'EMCI': [1], 'MCI': [2], 'LMCI': [3], 'AD': [5]},
    'Global CDR': {'CN': [0], 'EMCI': [0, .5], 'MCI': [0, .5], 'LMCI': [.5], 'AD': [1]},
    'FAQ Total Score': {'CN': [0, 1], 'EMCI': list(range(3, 6)), 'MCI': list(range(4, 8)),
                        'LMCI': list(range(7, 12)), 'AD': list(range(17, 25))},
    'NPI-Q Total Score': {'CN': [0], 'EMCI': [1], 'MCI': [3], 'LMCI': [4], 'AD': [5]},
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        return reader.fieldnames, list(reader)


def write_csv(name, rows):
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    evidence_path = OUT / 'code_evidence_3003.json'
    e = json.loads(evidence_path.read_text())
    hashes = {SOURCE: sha(SOURCE), FILLED: sha(FILLED)}
    assert hashes[SOURCE] == e['raw_source_csv_sha256']
    assert hashes[FILLED] == e['filled_csv_sha256']
    assert e['history_hash_unchanged'] and not e['history_wal_exists']
    assert not e['search_errors']
    extracted = []
    for r in e['history_sources']:
        assert hashlib.sha256(r['source'].encode()).hexdigest() == r['source_sha256']
        name = f"history_session{r['session']}_input{r['input_line']:03d}.py"
        header = (f"# Derived source excerpt; historical code was not executed.\n"
                  f"# Original: 3003:{e['history_path']}\n"
                  f"# Original file SHA-256: {e['history_sha256']}\n"
                  f"# IPython session {r['session']}, input {r['input_line']}.\n"
                  f"# Source SHA-256: {r['source_sha256']}\n\n")
        (OUT / name).write_text(header + r['source'])
        extracted.append(dict(file=name, session=r['session'], input_line=r['input_line'],
                              source_sha256=r['source_sha256']))
    for r in e['extracted_notebook_sources']:
        name = ('notebook_' + Path(r['path']).stem.replace(' ', '_') +
                f"_cell{r['cell_0based']:03d}.py")
        header = (f"# Derived source excerpt; historical notebook was not executed.\n"
                  f"# Original: 3003:{r['path']}\n"
                  f"# Original file SHA-256: {r['original_file_sha256']}\n"
                  f"# Notebook cell (zero-based): {r['cell_0based']}\n"
                  f"# Source SHA-256: {r['source_sha256']}\n\n")
        (OUT / name).write_text(header + r['source'])
    selector = next(r['source'] for r in e['history_sources']
                    if r['session'] == 373 and r['input_line'] == 20)
    assert "matched_rows.iloc[0].to_dict()" in selector
    assert 'mri_strip' in selector and 'file.endswith("_MRI.nii.gz")' in selector

    source_columns, source = read_csv(SOURCE)
    filled_columns, filled = read_csv(FILLED)
    first = {}
    for si, r in enumerate(source, 1):
        first.setdefault(r['Subject ID'], (si, r))
    ids = [r['Subject ID'] for r in filled]
    directory_ids = [name.replace('_MRI.nii.gz', '')
                     for name in e['selection_directory_filenames_os_listdir_order']
                     if name.endswith('_MRI.nii.gz')]
    assert len(set(ids)) == len(ids) == len(set(directory_ids)) == len(directory_ids)
    assert set(ids) == set(directory_ids)
    assert set(ids).issubset(first)

    restored, selected, cells = [], [], []
    for fi, f in enumerate(filled, 1):
        si, s = first[f['Subject ID']]
        for c in ANCHORS:
            assert (Decimal(s[c]) == Decimal(f[c]) if c in ['Weight', 'Age'] else s[c] == f[c])
        sr = dict(s)
        sr.update(filled_csv_record_1based=fi, source_csv_record_1based=si,
                  selection_evidence='history session 373 input 20: first matching CSV row',
                  image_id_scope='clinical_metadata_source_row; actual_NIfTI_identity_not_verified')
        selected.append(sr)
        r = dict(f)
        r.update({c: s[c] for c in LOST})
        r.update(filled_csv_record_1based=fi, source_csv_record_1based=si,
                 selection_history_session=373, selection_history_input=20,
                 image_id_scope='clinical_metadata_source_row; actual_NIfTI_identity_not_verified')
        for index, c in enumerate(SCORES, 22):
            observed = bool(s[c].strip())
            value = Decimal(f[c])
            supported = value in {Decimal(str(v)) for v in RULES[c][f['Research Group']]}
            if observed:
                assert Decimal(s[c]) == value
                state = 'source_first_record_observed_value_preserved'
            else:
                assert supported
                state = 'source_first_record_missing_current_value_within_historical_group_rule'
            r['source_observed__' + c] = s[c]
            r['score_origin__' + c] = state
            cells.append(dict(ptid=f['Subject ID'], research_group=f['Research Group'], variable=c,
                              filled_csv_record_1based=fi, source_csv_record_1based=si,
                              source_image_id=s['Image ID'], source_original_value=s[c],
                              current_filled_value=f[c], source_missing_before_fill=not observed,
                              status=state, applicable_group_support=json.dumps(RULES[c][f['Research Group']]),
                              historical_rule_session=373, historical_rule_input=index,
                              random_state_reconstructed=False))
        restored.append(r)
    write_csv('filled_restored_by_historical_selection.csv', restored)
    write_csv('selected_source_rows.csv', selected)
    write_csv('score_value_provenance.csv', cells)
    grouped = []
    for c in SCORES:
        for g in GROUPS:
            q = [r for r in cells if r['variable'] == c and r['research_group'] == g]
            missing = [r for r in q if r['source_missing_before_fill']]
            grouped.append(dict(variable=c, research_group=g, subjects=len(q),
                                source_observed=len(q) - len(missing), source_missing=len(missing),
                                historical_group_support=json.dumps(RULES[c][g]),
                                filled_values_at_source_missing_positions=json.dumps(dict(Counter(
                                    r['current_filled_value'] for r in missing)))))
    write_csv('score_provenance_by_group.csv', grouped)

    summary = dict(history_evidence_sha256=sha(evidence_path), history_source=e['history_path'],
                   history_database_sha256=e['history_sha256'],
                   history_session373_metadata=next(r for r in e['sessions'] if r['session'] == 373),
                   original_source_sha256=hashes[SOURCE], original_filled_sha256=hashes[FILLED],
                   reconstruction_script_sha256=sha(Path(__file__)),
                   current_directory_subjects=len(directory_ids), filled_subjects=len(ids),
                   current_directory_subject_set_equals_filled=True,
                   current_directory_order_equals_filled=directory_ids == ids,
                   first_record_demographic_matches=len(ids), selected_source_records=len(selected),
                   selected_source_record_modalities=dict(Counter(r['Modality'] for r in selected)),
                   selected_source_record_phases=dict(Counter(r['Phase'] for r in selected)),
                   observed_score_values_preserved=sum(not r['source_missing_before_fill'] for r in cells),
                   source_missing_score_values=sum(r['source_missing_before_fill'] for r in cells),
                   source_missing_values_within_group_rule=sum(r['source_missing_before_fill'] for r in cells),
                   per_score={c: dict(source_observed=sum(r['variable'] == c and not r['source_missing_before_fill'] for r in cells),
                                      source_missing=sum(r['variable'] == c and r['source_missing_before_fill'] for r in cells))
                              for c in SCORES},
                   source_first_record_mmse_refill_input21_additional_values=0,
                   no_historical_code_executed=True, random_draws_generated=0,
                   extracted_history_inputs=extracted,
                   unavailable_evidence=['Removal of the five metadata columns: exact code not found.',
                                         'Original choice of acquired MRI/PET before mri_strip: not established here.',
                                         'Full per-input timestamps and completion outputs: not established.',
                                         'Actual NIfTI acquisition identity remains unverified.',
                                         'Original random draws/state were not recovered.'])
    _, saved = read_csv(OUT / 'filled_restored_by_historical_selection.csv')
    assert all({c: r[c] for c in filled_columns} == f for r, f in zip(saved, filled))
    assert len(saved) == len(filled)
    assert all(sha(p) == v for p, v in hashes.items())
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: summary[k] for k in ['selected_source_records', 'current_directory_order_equals_filled',
                                             'selected_source_record_modalities', 'observed_score_values_preserved',
                                             'source_missing_score_values', 'per_score']}, indent=2))


if __name__ == '__main__':
    main()
