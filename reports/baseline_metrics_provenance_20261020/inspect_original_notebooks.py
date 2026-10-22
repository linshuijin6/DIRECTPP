"""Bounded read-only discovery of author evaluation code and text outputs.

Never executes notebook code or copies image/base64 outputs.
"""
from pathlib import Path
import ast
import csv
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
SOURCES = [
    ROOT / "source_archive/vscode-3002/home/ssddata/liutuo",
    ROOT / "source_archive/vscode-3003/home/data/liutuo/code",
    ROOT / "source_archive/vscode-3014/mnt/ssd/liutuo",
    ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/Github/train",
]
CODE = OUT / "source_extracts"
CODE.mkdir(exist_ok=True)


def joined(value):
    return value if isinstance(value, str) else "".join(value)


records = []
inventory = []
for folder in SOURCES:
    for path in sorted(folder.glob("*.ipynb")):
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        notebook = json.loads(raw)
        inventory.append({"path": str(path.relative_to(ROOT)), "sha256": digest})
        for index, cell in enumerate(notebook["cells"]):
            if cell["cell_type"] != "code":
                continue
            source = joined(cell.get("source", []))
            if not re.search(r"PSNRMetric|SSIMMetric|peak_signal_noise_ratio|structural_similarity|mean_psnr|ssim_mean|67\.82|59\.56|40\.27", source, re.I):
                continue
            key = f"{path.parts[path.parts.index('source_archive')+1]}_{path.stem}_cell{index}_{hashlib.sha256(str(path).encode()).hexdigest()[:8]}"
            derived = CODE / (key + ".py")
            derived.write_text(f"# Original={path.relative_to(ROOT)}\n# original_sha256={digest}; zero_based_cell={index}\n" + source)
            outputs = []
            for output in cell.get("outputs", []):
                text = joined(output.get("text", []))
                if output.get("output_type") == "error":
                    text += "\n" + joined(output.get("traceback", []))
                # text/plain is small metadata, but exclude figure reprs.
                plain = joined(output.get("data", {}).get("text/plain", []))
                if plain and not plain.startswith("<Figure"):
                    text += plain
                if text:
                    outputs.append(text)
            output_text = "\n".join(outputs)
            interesting = [line for line in output_text.splitlines() if re.search(
                r"PSNR|SSIM|MSE:|MAE:|mean|average|Average|平均|Error|Saved|saved|[0-9]{3}_S_[0-9]+", line)]
            output_path = CODE / (key + ".outputs.txt")
            output_path.write_text("\n".join(interesting) + ("\n" if interesting else ""))
            records.append({
                "original": str(path.relative_to(ROOT)), "original_sha256": digest,
                "cell": index, "execution_count": cell.get("execution_count"),
                "source_sha256": hashlib.sha256(source.encode()).hexdigest(),
                "derived": str(derived.relative_to(ROOT)),
                "output_extract": str(output_path.relative_to(ROOT)),
                "output_text_characters": len(output_text),
                "output_subjects": sorted(set(re.findall(r"(?<![0-9])\d{3}_S_\d+(?![0-9])", output_text))),
                "metric_output_lines": len(interesting),
                "aggregate_output_tail": [x for x in interesting if re.search(r"[Mm]ean|[Aa]verage|平均", x)][-12:],
                "source_directives": [{"line": n, "text": line} for n, line in enumerate(source.splitlines(), 1)
                    if re.search(r"torch.load|checkpoint|json_path|loader|_dir\s*=|_dirs\s*=|SSIMMetric\(|PSNRMetric\(|np.mean|torch.mean|mean\(.*values", line)],
            })

(OUT / "bounded_notebook_inventory.json").write_text(json.dumps(inventory, ensure_ascii=False, indent=2) + "\n")
(OUT / "metric_cell_index.json").write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n")

# Extract Fig.2 inputs as literal data; never execute the plotting cell.
figure = ROOT / "source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_AV45-swin unet or fanhua.ipynb"
notebook = json.loads(figure.read_text())
with (OUT / "paper_figure2_values.csv").open("w", newline="") as handle:
    writer = csv.writer(handle)
    writer.writerow(["cohort", "method", "SSIM_percent", "PSNR", "MSE_percent", "MAE_percent", "source", "cell_zero_based"])
    for index, cohort in [(9, "ADNI_FDG"), (10, "ADNI_AV45"), (11, "OASIS")]:
        assignments = {}
        for statement in ast.parse(joined(notebook["cells"][index]["source"])).body:
            if isinstance(statement, ast.Assign) and isinstance(statement.targets[0], ast.Name):
                name = statement.targets[0].id
                if name in {"methods", "data"}:
                    assignments[name] = ast.literal_eval(statement.value)
        for method, values in zip(assignments["methods"], assignments["data"]):
            writer.writerow([cohort, method, *values, str(figure.relative_to(ROOT)), index])

print(f"Inspected {len(inventory)} notebooks; {len(records)} metric/plot cells; exported 21 Fig.2 rows.")
for record in records:
    print(record["original"].split("/")[-1], "cell", record["cell"],
          "output_PTIDs", len(record["output_subjects"]), "aggregates", record["aggregate_output_tail"][:3])
