"""Read-only checks of the imported ChatGPT Phase 2 audit; write local evidence only."""
from pathlib import Path
import csv
import hashlib
import json
import re
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def read(path):
    return (ROOT / path).read_text(encoding="utf-8-sig")


def argument(text, name):
    match = re.search(r"\\" + name + r"\{", text)
    if not match:
        return None
    start = match.end()
    depth = 1
    for i in range(start, len(text)):
        if text[i] in "{}" and (i == 0 or text[i - 1] != "\\"):
            depth += 1 if text[i] == "{" else -1
            if depth == 0:
                return text[start:i]
    raise ValueError(f"Unclosed {name}")


def pdf_pages(path):
    output = subprocess.check_output(
        ["pdftotext", "-layout", str(ROOT / path), "-"], text=True
    ).split("\f")
    return output[:-1] if not output[-1].strip() else output


sections = {}
source_paths = [
    f"rebuttal/sections/{name}.tex"
    for name in ("02_reviewer2", "03_reviewer3_major", "04_reviewer3_minor")
]
for path in source_paths:
    text = read(path)
    for match in re.finditer(
        r"\\subsection\*\{([^}]+)\}([\s\S]*?)(?=\\subsection\*|\Z)", text
    ):
        ident = match[1].split()[0]
        sections[ident] = {
            "path": path,
            "line": text[:match.start()].count("\n") + 1,
            "body": match[2],
        }

imported = "review_audit/chatgpt/phase2"
matrix_path = next((ROOT / imported).glob("*.csv"))
with matrix_path.open(encoding="utf-8-sig", newline="") as stream:
    matrix = list(csv.DictReader(stream))
with (ROOT / "reports/source_reports/review_comment_register.csv").open(
    encoding="utf-8-sig", newline=""
) as stream:
    registered = [row["comment_id"] for row in csv.DictReader(stream)]
expected = {
    "M" + str(int(x.rsplit("-", 1)[1])) if x.startswith("R3-minor-") else x
    for x in registered if not x.startswith("EDITOR-")
}

pdf_paths = {
    "rebuttal": "revision_workspace/delivery/01_submission/Response_to_Reviewers.pdf",
    "clean": "revision_workspace/delivery/01_submission/Manuscript_clean.pdf",
    "supplementary": "revision_workspace/delivery/01_submission/Supplementary_Materials.pdf",
    "combined": "revision_workspace/delivery/05_internal_audit/Combined_reference_copy.pdf",
}
pdfs = {key: pdf_pages(path) for key, path in pdf_paths.items()}
evidence = {
    "baseline_commit": subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip(),
    "scope": "Document coverage and location checks, not scientific validation or submission",
    "expected_ids": sorted(expected),
    "missing_ids": sorted(expected - sections.keys()),
    "unexpected_ids": sorted(sections.keys() - expected),
    "matrix_rows": len(matrix),
    "matrix_ids_unique": len({row["ID"] for row in matrix}) == len(matrix),
    "pdf_pages": {key: len(value) for key, value in pdfs.items()},
    "macro_counts": {
        name: sum(len(re.findall(r"\\" + name + r"\{", x["body"])) for x in sections.values())
        for name in ("revcomment", "response", "actiontaken", "changedtext")
    },
}
reference_pattern = r"\(p\. (\d+), lines (\d+)--(\d+)\)"
locations = []
supplementary_references = []
bibliography_locations = []
future_phrases = []
for ident, section in sections.items():
    body = section["body"]
    for match in re.finditer(reference_pattern, body):
        page, first, last = map(int, match.groups())
        page_text = pdfs["combined"][page - 1]
        locations.append({
            "id": ident, "page": page, "first": first, "last": last,
            "first_line_exists": bool(re.search(rf"^\s*{first}\s+", page_text, re.M)),
            "last_line_exists": bool(re.search(rf"^\s*{last}\s+", page_text, re.M)),
        })
    for line in body.splitlines():
        if "Bibliography (p." in line:
            bibliography_locations.append({"id": ident, "reference": line.strip()})
        if "Supplementary Materials, p." in line:
            supplementary_references.append({"id": ident, "reference": line.strip()})
    response = argument(body, "response") or ""
    for match in re.finditer(r"\bwill\b", response, re.I):
        future_phrases.append({
            "id": ident,
            "context": response[max(0, match.start() - 40):match.end() + 170],
        })

pdf_heading_checks = []
for row in matrix:
    ident = row["ID"]
    page = int(row["Rebuttal_PDF_Page"])
    text = pdfs["rebuttal"][page - 1]
    pdf_heading_checks.append({
        "id": ident, "page": page,
        "heading_present": bool(re.search(rf"^\s*{re.escape(ident)}(?:\s|$)", text, re.M)),
        "response_source_exists": (ROOT / f"revision_workspace/integration/responses/{ident}.final.md").exists(),
    })

citation_keys = {
    key.strip()
    for value in sections.values()
    for match in re.finditer(r"\\cite\{([^}]+)\}", value["body"])
    for key in match[1].split(",")
}
bib_keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", read("rebuttal/references.bib")))
evidence.update({
    "pdf_heading_checks": pdf_heading_checks,
    "main_locations": locations,
    "main_location_count": len(locations),
    "main_start_line_exists_count": sum(x["first_line_exists"] for x in locations),
    "main_end_line_exists_count": sum(x["last_line_exists"] for x in locations),
    "bibliography_locations": bibliography_locations,
    "supplementary_references": supplementary_references,
    "supplementary_reference_count": len(supplementary_references),
    "future_phrases_for_manual_classification": future_phrases,
    "unique_citation_keys": sorted(citation_keys),
    "missing_bib_keys": sorted(citation_keys - bib_keys),
})

captions = {}
for kind in ("supplementary", "combined"):
    captions[kind] = {}
    for number, page in enumerate(pdfs[kind], 1):
        for match in re.finditer(r"\b(Table|Figure)\s+S(\d+)\s*:", page):
            captions[kind].setdefault(f"{match[1]} S{match[2]}", []).append(number)
evidence["supplementary_caption_pages"] = captions

hash_paths = source_paths + list(pdf_paths.values()) + [
    str(path.relative_to(ROOT)) for path in sorted((ROOT / imported).iterdir()) if path.is_file()
]
evidence["sha256"] = {
    path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in hash_paths
}
(OUT / "evidence.json").write_text(
    json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps({
    key: evidence[key] for key in (
        "baseline_commit", "missing_ids", "unexpected_ids", "matrix_rows", "macro_counts",
        "pdf_pages", "main_location_count", "main_start_line_exists_count",
        "main_end_line_exists_count", "supplementary_reference_count", "missing_bib_keys",
    )
}, ensure_ascii=False, indent=2))
print("PDF headings present:", sum(x["heading_present"] for x in pdf_heading_checks))
print("Final response sources:", sum(x["response_source_exists"] for x in pdf_heading_checks))
print("Unique citation keys:", len(citation_keys))
print("Wrote", OUT / "evidence.json")
