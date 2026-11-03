"""Read existing classification completion metadata and checkpoint existence."""
import sys,json,hashlib
from pathlib import Path
jobs=json.loads(Path(sys.argv[1]).read_text());out=[]
for row in jobs:
    path=Path(row['source_metadata']);s=json.loads(path.read_text());cp=path.parent/'best_model.pth'
    pp=Path(row['source_predictions']);mm=Path(row['source_test_metrics'])
    out.append(dict(task=row['task'],condition=row['condition'],fold=row['fold'],summary=s,
        source_metadata=str(path),metadata_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
        predictions_sha256=hashlib.sha256(pp.read_bytes()).hexdigest(),test_metrics_sha256=hashlib.sha256(mm.read_bytes()).hexdigest(),
        checkpoint=str(cp),checkpoint_exists=cp.is_file(),checkpoint_bytes=cp.stat().st_size if cp.is_file() else None))
print(json.dumps(out))
