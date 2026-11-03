"""Reuse existing verified inference checks/statistics, redirect only summary output."""
from pathlib import Path
import sys,hashlib,json
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'reports/revision_evidence_night_20261102/G1_E1'
OUT.mkdir(exist_ok=True)
src=ROOT/'experiments/e1_clinical_conditioning/summarize_score_removal.py'
sys.path.insert(0,str(src.parent))
code=src.read_text()
old='out = REPORT / "full" / "paired_summary"'
assert code.count(old)==1
code=code.replace(old, 'out = Path('+repr(str(OUT/'paired_summary'))+')')
# Preserve the native script's __file__ so ROOT and all input identities remain native.
(OUT/'source_reuse.json').write_text(json.dumps(dict(source=str(src),sha256=hashlib.sha256(src.read_bytes()).hexdigest(),change='summary output path only'),indent=2))
exec(compile(code,str(src),'exec'),{'__file__':str(src),'__name__':'__main__'})
