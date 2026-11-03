"""Inspect the supplied IDA ZIP in place; preserve XML scopes and provenance.

No archive members are extracted or altered. Main-image dates are never assigned
to other related images. Parent protocols and external reference-image protocols
are kept separate. Missing requested records are skipped, not chased or imputed.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
import csv
import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile


OUT = Path(__file__).resolve().parent
REPO = OUT.parents[2]
ARCHIVE = REPO / 'source_archive/1103_IDA_Metadata.zip'
SELECTED = OUT.parent / 'filtering_code_recovery_20261103/selected_source_rows.csv'
TERMS = ['Manufacturer', 'Mfg Model', 'Radiopharmaceutical', 'Radioisotope',
         'Field Strength', 'Reconstruction', 'Convolution Kernel', 'Frames',
         'Acquisition Type', 'Weighting', 'Pulse Sequence', 'TE', 'TR', 'TI',
         'Coil', 'Flip Angle', 'Acquisition Plane', 'Matrix X', 'Matrix Y',
         'Matrix Z', 'Number of Rows', 'Number of Columns', 'Number of Slices',
         'Pixel Spacing X', 'Pixel Spacing Y', 'Slice Thickness',
         'Counts Source', 'Randoms Correction', 'Attenuation Correction',
         'Decay Correction', 'Scatter Correction']


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def uid(value, prefix='I'):
    value = (value or '').strip()
    if not value:
        return ''
    result = value if value.startswith(prefix) else prefix + value
    assert re.fullmatch(prefix + r'\d+', result), result
    return result


def text(node, path):
    return (node.findtext(path) or '').strip()


def values(items):
    return list(dict.fromkeys(x for x in items if x))


def j(items):
    return json.dumps(items, ensure_ascii=False)


def write_csv(name, rows, columns=None):
    if columns is None:
        columns = list(dict.fromkeys(k for r in rows for k in r))
    with (OUT / name).open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=columns)
        w.writeheader()
        w.writerows(rows)


def walk(node, path=''):
    current = path + '/' + node.tag
    yield node, current
    for child in node:
        yield from walk(child, current)


def main():
    archive_hash = sha(ARCHIVE.read_bytes())
    selected_hash = sha(SELECTED.read_bytes())
    with SELECTED.open(encoding='utf-8-sig', newline='') as f:
        selected = list(csv.DictReader(f))
    requested = {uid(r['Image ID']): r for r in selected}
    assert len(requested) == len(selected) == 1857
    images, pointers, protocols, steps, relations, flags, members, errors = [], [], [], [], [], [], [], []
    with zipfile.ZipFile(ARCHIVE) as z:
        for info in z.infolist():
            raw = z.read(info)
            root = ET.fromstring(raw)
            for el in root.iter():
                el.tag = el.tag.rsplit('}', 1)[-1]
            members.append(dict(member=info.filename, bytes=info.file_size,
                                sha256=sha(raw), root_type=root.tag))
            if root.tag == 'metadata':
                image_id = uid(root.find('image').get('uid'))
                match = re.search(r'/(\d{4}-\d{2}-\d{2}_[^/]+)/I\d+/', info.filename)
                pointers.append(dict(image_id=image_id, subject_id=root.find('subject').get('id'),
                                     series_id=uid(root.find('series').get('uid'), 'S'),
                                     study_id=root.find('study').get('uid'), member=info.filename,
                                     directory_datetime_from_archive_path=match[1] if match else ''))
                continue
            if root.tag != 'idaxs':
                errors.append(dict(member=info.filename, reason='unsupported XML root', root=root.tag))
                continue
            series = root.find('project/subject/study/series')
            assert series is not None
            products = series.findall('seriesLevelMeta/derivedProduct')
            assert len(products) == 1, info.filename
            product = products[0]
            image_id = uid(text(product, 'imageUID'))
            subject_id = text(root, 'project/subject/subjectIdentifier')
            modality = text(series, 'modality')
            acquired = text(series, 'dateAcquired')
            date.fromisoformat(acquired)
            row = dict(image_id=image_id, subject_id=subject_id, modality=modality,
                       acquisition_date=acquired,
                       acquisition_date_scope='main series/dateAcquired; not creationDate or provenance timestamp',
                       series_id=uid(text(series, 'seriesIdentifier'), 'S'),
                       study_id=text(root, 'project/subject/study/studyIdentifier'),
                       site_id=text(root, 'project/siteKey'),
                       visit=text(root, 'project/subject/visit/visitIdentifier'),
                       processed_data_label=text(product, 'processedDataLabel'),
                       image_type=text(product, 'imageType'), registration=text(product, 'registration'),
                       processing_institution=text(product, 'processingInstitution'),
                       creation_date_not_acquisition=text(product, 'creationDate'),
                       xml_member=info.filename, xml_sha256=sha(raw),
                       image_id_scope='historically selected clinical-source record; current NIfTI identity unverified')
            primary = []
            for node, xpath in walk(root):
                if node.tag != 'originalRelatedImage':
                    continue
                scope = ('main_series_original_source' if xpath.endswith(
                    '/series/seriesLevelMeta/relatedImageDetail/originalRelatedImage') else
                    'additional_reference_context')
                p = dict(derived_image_id=image_id, subject_id=subject_id, main_modality=modality,
                         original_image_id=uid(text(node, 'imageUID')), scope=scope,
                         source_description=text(node, 'description'), xml_xpath=xpath,
                         xml_member=info.filename)
                all_terms = {x.get('term'): (x.text or '').strip()
                             for x in node.findall('protocolTerm/protocol')}
                p.update(all_terms)
                p['original_protocol_json'] = j(all_terms)
                protocols.append(p)
                if scope == 'main_series_original_source':
                    primary.append(p)
            row['primary_original_image_ids'] = j(values(p['original_image_id'] for p in primary))
            row['primary_original_descriptions'] = j(values(p['source_description'] for p in primary))
            row['primary_original_count'] = len(primary)
            for term in TERMS:
                vals = values(p.get(term, '') for p in primary)
                row['original_protocol__' + term] = vals[0] if len(vals) == 1 else ''
                row['original_protocol_values__' + term] = j(vals)
            processes = []
            for index, node in enumerate(product.findall('provenanceDetail'), 1):
                s = dict(image_id=image_id, subject_id=subject_id, modality=modality,
                         step_ordinal=index, xml_member=info.filename)
                s.update({child.tag: (child.text or '').strip() for child in node})
                steps.append(s)
                processes.append(text(node, 'process'))
            row['processing_steps'] = j(processes)
            row['step_count'] = len(processes)
            row['uniform_6mm_label'] = 'Uniform 6mm Res' in row['processed_data_label']
            row['variable_smooth_step'] = 'Variable Smooth' in processes
            row['cerebellar_gray_matter_normalization_step'] = any(
                'Intensity Normalization to Cerebellar Gray Matter' in x for x in processes)
            row['generic_intensity_normalization_step'] = 'Intensity Normalization' in processes
            row['av45_early_label'] = 'AV45-Early' in row['processed_data_label']
            radiopharm = row['original_protocol__Radiopharmaceutical']
            row['tracer_field_status'] = ('not_applicable_MRI' if modality != 'PET' else
                'label_FBB_conflicts_with_original_protocol_AV45' if
                'FBB' in row['processed_data_label'] and 'AV45' in radiopharm else
                'explicit_original_protocol_value' if radiopharm else 'not_available')
            if row['tracer_field_status'].startswith('label_FBB'):
                flags.append(dict(image_id=image_id, subject_id=subject_id,
                                  finding='FBB product label versus AV45 original protocol',
                                  evidence=row['processed_data_label'] + ' | Radiopharmaceutical=' + radiopharm,
                                  implication='tracer unresolved for this source record; do not resolve by folder name',
                                  xml_member=info.filename))
            if row['av45_early_label']:
                flags.append(dict(image_id=image_id, subject_id=subject_id,
                                  finding='AV45-Early acquisition product', evidence=j(processes),
                                  implication='distinct frame averaging window; current NIfTI membership unverified',
                                  xml_member=info.filename))
            if row['image_type'].lower() == 'mask':
                flags.append(dict(image_id=image_id, subject_id=subject_id,
                                  finding='source record is a mask', evidence=row['processed_data_label'],
                                  implication='clinical-source record is not evidence of the actual T1 intensity NIfTI',
                                  xml_member=info.filename))
            if row['processed_data_label'] == 'EPI current corrected image':
                flags.append(dict(image_id=image_id, subject_id=subject_id,
                                  finding='EPI/diffusion processing source record', evidence=j(processes),
                                  implication='source record does not establish the actual structural MRI input',
                                  xml_member=info.filename))
            for r in product.findall('relatedImage'):
                relations.append(dict(image_id=image_id, subject_id=subject_id,
                                      related_image_id=uid(text(r, 'imageUID')),
                                      relation=text(r, 'relation'), xml_member=info.filename))
            assert image_id in requested, image_id
            assert requested[image_id]['Subject ID'] == subject_id
            assert requested[image_id]['Modality'] == modality
            row['source_csv_description'] = requested[image_id]['Description']
            images.append(row)
    assert not errors, errors
    by_id = {r['image_id']: r for r in images}
    by_pointer = {r['image_id']: r for r in pointers}
    assert len(by_id) == len(images)
    assert len(by_pointer) == len(pointers)
    assert set(by_pointer).issubset(requested)
    for iid, r in by_id.items():
        p = by_pointer[iid]
        assert r['subject_id'] == p['subject_id'] and r['series_id'] == p['series_id']
        assert p['directory_datetime_from_archive_path'].split('_')[0] == r['acquisition_date']
    coverage, pairing = [], []
    for iid, r in requested.items():
        meta = by_id.get(iid, {})
        coverage.append(dict(subject_id=r['Subject ID'], image_id=iid, source_modality=r['Modality'],
                             availability='detailed_XML' if iid in by_id else 'ID_pointer_only_skipped' if
                             iid in by_pointer else 'not_in_ZIP_skipped',
                             acquisition_date=meta.get('acquisition_date', ''),
                             detailed_xml_member=meta.get('xml_member', '')))
        pairing.append(dict(subject_id=r['Subject ID'], requested_image_id=iid,
                            MRI_main_image_id=iid if meta.get('modality') == 'MRI' else '',
                            PET_main_image_id=iid if meta.get('modality') == 'PET' else '',
                            acquisition_date=meta.get('acquisition_date', ''),
                            pair_status='no_MRI_PET_pair_in_this_ZIP', interval_days='',
                            interval_status='not_computable; not zero days'))
    subject_modalities = defaultdict(set)
    for r in images:
        subject_modalities[r['subject_id']].add(r['modality'])
    paired_subjects = [s for s, mods in subject_modalities.items() if {'MRI', 'PET'}.issubset(mods)]
    assert not paired_subjects
    write_csv('image_metadata.csv', images)
    write_csv('original_protocols.csv', protocols)
    write_csv('processing_steps.csv', steps)
    write_csv('image_relations.csv', relations)
    write_csv('metadata_coverage.csv', coverage)
    write_csv('mri_pet_pairing_check.csv', pairing)
    write_csv('metadata_findings.csv', flags)
    summary = dict(inspected_at_utc=datetime.now(timezone.utc).isoformat(),
                   archive_path=str(ARCHIVE.relative_to(REPO)), archive_sha256=archive_hash,
                   selected_source_records_sha256=selected_hash, script_sha256=sha(Path(__file__).read_bytes()),
                   requested_images=len(requested), archive_xml_members=len(members),
                   roots=dict(Counter(m['root_type'] for m in members)),
                   detailed_images=len(images), detailed_subjects=len(subject_modalities),
                   detailed_modalities=dict(Counter(r['modality'] for r in images)),
                   acquisition_date_range=[min(r['acquisition_date'] for r in images), max(r['acquisition_date'] for r in images)],
                   usable_mri_pet_pairs=len(paired_subjects), interval_days=None,
                   unobserved_requested_images_ignored=True,
                   coverage_status=dict(Counter(r['availability'] for r in coverage)),
                   per_modality={}, metadata_flags=dict(Counter(r['finding'] for r in flags)),
                   all_main_ID_subject_modality_matches_verified=True,
                   all_pointer_ID_subject_series_date_matches_verified=True,
                   original_protocol_rows=len(protocols), processing_step_rows=len(steps),
                   no_missing_metadata_download_or_imputation=True,
                   limitations=['Main image IDs identify clinical-source rows, not verified current NIfTI inputs.',
                                'One requested main image per subject prevents within-subject MRI-PET pairing.',
                                'Source-original protocol geometry and scanner are not the processed output geometry.',
                                'Processing timestamps/creationDate are not acquisition dates.',
                                'FBB-labelled source with AV45 protocol remains unresolved.',
                                'No inference that multi-scanner effects have been eliminated.'])
    for modality in ['MRI', 'PET']:
        q = [r for r in images if r['modality'] == modality]
        counts = dict(images=len(q), sites=len({r['site_id'] for r in q}),
                      processed_labels=dict(Counter(r['processed_data_label'] for r in q)),
                      image_types=dict(Counter(r['image_type'] for r in q)),
                      registrations=dict(Counter(r['registration'] for r in q)),
                      processing_institutions=dict(Counter(r['processing_institution'] for r in q)),
                      pipeline_sequences=dict(Counter(' -> '.join(json.loads(r['processing_steps'])) for r in q)),
                      uniform_6mm_labels=sum(r['uniform_6mm_label'] for r in q),
                      variable_smooth_steps=sum(r['variable_smooth_step'] for r in q),
                      cerebellar_gray_normalizations=sum(r['cerebellar_gray_matter_normalization_step'] for r in q),
                      generic_intensity_normalizations=sum(r['generic_intensity_normalization_step'] for r in q),
                      av45_early_labels=sum(r['av45_early_label'] for r in q),
                      acquisition_date_range=[min(r['acquisition_date'] for r in q), max(r['acquisition_date'] for r in q)])
        for term in ['Manufacturer', 'Mfg Model', 'Field Strength', 'Radiopharmaceutical',
                     'Reconstruction', 'Convolution Kernel', 'Frames']:
            counts[term] = dict(Counter(r['original_protocol__' + term] for r in q))
        summary['per_modality'][modality] = counts
    (OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    (OUT / 'archive_member_manifest.json').write_text(json.dumps(members, ensure_ascii=False, indent=2) + '\n')
    assert sha(ARCHIVE.read_bytes()) == archive_hash
    assert sha(SELECTED.read_bytes()) == selected_hash
    print(json.dumps({k: summary[k] for k in ['detailed_images', 'detailed_modalities', 'usable_mri_pet_pairs',
                                             'coverage_status', 'metadata_flags']}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
