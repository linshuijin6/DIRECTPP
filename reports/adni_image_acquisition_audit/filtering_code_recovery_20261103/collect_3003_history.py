"""Read-only recovery of narrowly relevant code from 3003; prints JSON.

Run with the 3003 xiaochou Python via SSH stdin. No historical code is run.
Only matching IPython input sources are exported, not unrelated history.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sqlite3


ROOT = Path('/home/data/liutuo/code')
BASE = ROOT / 'liutuo_data/ADNI1234_mri_fdg_av45'
HISTORY = Path('/home/data/liutuo/.ipython/profile_default/history.sqlite')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def main():
    strong = re.compile(r'filtered_subjects|ADNI MRI and FDG and AV45|ADNI1234_mri_fdg_av45|processed_files\.txt', re.I)
    generic = re.compile(r'fillna|drop_duplicates|groupby|to_csv|imput|random\.normal|filtered_ADNI_data', re.I)
    paths = sorted(p for folder in [ROOT, ROOT / '.ipynb_checkpoints', ROOT / 'test']
                   for p in folder.iterdir() if p.is_file()
                   and p.suffix in ['.ipynb', '.py', '.sh', '.R', '.r', '.m']
                   and p.name != 'fslinstaller.py')
    manifest, notebook_sources, errors = [], [], []
    targets = {
        ('chu li shu ju.ipynb', 6),
        ('mri2pet _clip_pretrain .ipynb', 3),
        ('mri2pet _two trace_new.ipynb', 2),
    }
    for p in paths:
        raw = p.read_bytes()
        record = dict(path=str(p), bytes=len(raw), sha256=sha(raw))
        try:
            cells = json.loads(raw).get('cells', []) if p.suffix == '.ipynb' else [
                dict(cell_type='code', source=[raw.decode()])]
            code = [(i, ''.join(c.get('source', []))) for i, c in enumerate(cells)
                    if c.get('cell_type') == 'code']
            record.update(code_cells=len(code),
                          strong_hit_cells=[i for i, s in code if strong.search(s)],
                          generic_operation_hit_cells=[i for i, s in code if generic.search(s)])
            for i, src in code:
                if (p.name, i) in targets and p.parent == ROOT:
                    notebook_sources.append(dict(path=str(p), original_file_sha256=record['sha256'],
                                                 cell_0based=i, source=src,
                                                 source_sha256=sha(src.encode())))
        except Exception as e:
            record['error'] = repr(e)
            errors.append(dict(path=str(p), error=repr(e)))
        manifest.append(record)

    before = sha(HISTORY.read_bytes())
    wal_exists = HISTORY.with_name(HISTORY.name + '-wal').exists()
    if wal_exists:
        raise RuntimeError('History has a WAL; obtain a consistent read-only snapshot before extraction')
    con = sqlite3.connect(HISTORY.as_uri() + '?mode=ro&immutable=1', uri=True)
    con.execute('PRAGMA query_only=ON')
    sessions = []
    for session in [287, 373]:
        row = con.execute('SELECT * FROM sessions WHERE session=?', (session,)).fetchone()
        sessions.append(dict(session=session, session_metadata=row,
                             caveat='Session start is not a timestamp for every individual input'))
    history_sources = []
    for session, line, src in con.execute(
            'SELECT session,line,source_raw FROM history '
            'WHERE (session=373 AND line BETWEEN 16 AND 29) OR (session=287 AND line=19) '
            'ORDER BY session,line'):
        history_sources.append(dict(session=session, input_line=line, source=src,
                                    source_sha256=sha(src.encode())))
    schema = {table: [r[1] for r in con.execute('PRAGMA table_info(' + table + ')')]
              for table in ['history', 'sessions']}
    con.close()
    after = sha(HISTORY.read_bytes())
    if before != after:
        raise RuntimeError('History changed during inspection; retain failure and retry a new snapshot')
    snapshot = dict(inspected_at_utc=datetime.now(timezone.utc).isoformat(),
                    history_path=str(HISTORY), history_bytes=HISTORY.stat().st_size,
                    history_sha256=before, history_hash_unchanged=True, history_wal_exists=False,
                    sqlite_open_mode='mode=ro&immutable=1; PRAGMA query_only=ON',
                    history_schema=schema, sessions=sessions, history_sources=history_sources,
                    searched_source_files=manifest, search_errors=errors,
                    source_code_cells_scanned=sum(r.get('code_cells', 0) for r in manifest),
                    extracted_notebook_sources=notebook_sources,
                    selection_directory=str(BASE / 'mri_strip'),
                    selection_directory_filenames_os_listdir_order=os.listdir(BASE / 'mri_strip'),
                    companion_source_files_in_base=[p.name for p in BASE.iterdir()
                                                   if p.is_file() and p.suffix in ['.py', '.ipynb', '.sh', '.R', '.r', '.m']],
                    raw_source_csv_path=str(BASE / 'ADNI MRI and FDG and AV45 csv.csv'),
                    raw_source_csv_sha256=sha((BASE / 'ADNI MRI and FDG and AV45 csv.csv').read_bytes()),
                    filled_csv_path=str(BASE / 'filtered_subjects_filled.csv'),
                    filled_csv_sha256=sha((BASE / 'filtered_subjects_filled.csv').read_bytes()))
    print(json.dumps(snapshot, ensure_ascii=False))


if __name__ == '__main__':
    main()
