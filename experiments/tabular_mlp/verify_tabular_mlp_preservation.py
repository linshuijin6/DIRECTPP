"""Local preservation verification for the Tabular MLP lightweight transfer.

Run AFTER ``sync_tabular_mlp_lightweight.sh``. Verifies, strictly against receipts
produced by the remote run, that:

  1. local ``config.json`` matches the config_sha256 recorded in the checkpoint receipts;
  2. local preparation artifacts (cohort, split, input_hashes, clinical_features) match
     all hashes recorded in config;
  3. ``oof_summary`` CSVs match the digests recorded in ``oof_summary/completion.json``;
  4. all snapshot checkpoints in ``formal/fold*`` match their ``first_part_*.json``
     receipts, and the four fixed-endpoint checkpoints additionally cross-match
     ``oof/epoch*/fold*/complete.json``;
  5. every ``metrics.csv`` in ``oof/`` matches its ``complete.json`` receipt and expected
     row counts;
  6. all four fixed-endpoint checkpoints load in PyTorch with valid keys and finite tensors.

Writes ``download_receipt.json`` and prints ``ALL_VERIFICATIONS_PASSED`` on success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

DEFAULT_REPORT = REPO / "reports" / "tabular_mlp_20261028_v3"
DEFAULT_ASSETS = Path("/mnt/datas230/users/linshuijin/DIRECTPP_tabular_mlp/20261028_v3")
FOLDS = (1, 2)
SNAPSHOT_EPOCHS = (10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140, 150, 160, 165, 170, 180, 190, 200)
ENDPOINT_EPOCHS = (165, 200)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


class Checks:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def record(self, name: str, ok: bool, detail: str = "") -> bool:
        status = "PASS" if ok else "FAIL"
        self.items.append({"check": name, "status": status, "detail": str(detail)})
        suffix = f" -- {detail}" if detail else ""
        print(f"[{status}] {name}{suffix}")
        return ok

    def info(self, name: str, detail: str = "") -> None:
        self.items.append({"check": name, "status": "INFO", "detail": str(detail)})
        suffix = f" -- {detail}" if detail else ""
        print(f"[INFO] {name}{suffix}")

    @property
    def all_passed(self) -> bool:
        return all(item["status"] in ("PASS", "INFO") for item in self.items)


def verify(report_dir: Path, assets_dir: Path) -> bool:
    checks = Checks()
    t0 = time.time()
    checks.info("host", socket.gethostname())
    checks.info("report_dir", str(report_dir))
    checks.info("assets_dir", str(assets_dir))

    # --- 1. Config & preparation artifacts ---
    config_file = report_dir / "config.json"
    checks.record("config.exists", config_file.exists(), str(config_file))
    cfg = json.loads(config_file.read_text())
    cfg_sha = sha256(config_file)
    checks.record("config.sha256", cfg_sha == "16199d88e3812c905d26e89fa6d398d2ea53d00305e24abc47d8cc34f4e6bcf7", cfg_sha)

    for field, filename in (
        ("cohort_sha256", "cohort.json"),
        ("split_manifest_sha256", "split_manifest.csv"),
        ("input_hashes_sha256", "input_hashes.csv"),
        ("clinical_features_sha256", "clinical_features.csv"),
    ):
        target = report_dir / filename
        checks.record(f"prep.{filename}.exists", target.exists(), str(target))
        digest = sha256(target)
        checks.record(f"prep.{filename}.sha256", digest == cfg[field], f"actual={digest} expected={cfg[field]}")

    checks.record("prep.preflight_fold1.exists", (report_dir / "preflight_fold1.json").exists())
    checks.record("prep.preflight_fold2.exists", (report_dir / "preflight_fold2.json").exists())

    # --- 2. OOF Summary ---
    summary_dir = report_dir / "oof_summary"
    completion_file = summary_dir / "completion.json"
    checks.record("oof_summary.completion_exists", completion_file.exists())
    completion = json.loads(completion_file.read_text())
    checks.record("oof_summary.status", completion.get("status") == "COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION", completion.get("status"))

    per_subject_file = summary_dir / "per_subject_metrics.csv"
    per_subject_sha = sha256(per_subject_file)
    checks.record(
        "oof_summary.per_subject_metrics_sha256",
        per_subject_sha == completion["per_subject_sha256"],
        f"actual={per_subject_sha} receipt={completion['per_subject_sha256']}",
    )
    with open(per_subject_file) as f:
        row_count = sum(1 for _ in f) - 1
    checks.record("oof_summary.per_subject_rows", row_count == 5926, f"{row_count} rows")

    overall_file = summary_dir / "overall_summary.csv"
    overall_sha = sha256(overall_file)
    checks.record(
        "oof_summary.overall_summary_sha256",
        overall_sha == completion["summary_sha256"],
        f"actual={overall_sha} receipt={completion['summary_sha256']}",
    )

    # --- 3. Formal checkpoints & receipts ---
    formal_dir = assets_dir / "formal"
    fold_endpoint_checkpoints: dict[tuple[int, int], str] = {}

    for fold in FOLDS:
        fdir = formal_dir / f"fold{fold}"
        complete_p = fdir / "complete.json"
        checks.record(f"formal.fold{fold}.complete_exists", complete_p.exists())
        fold_comp = json.loads(complete_p.read_text())
        checks.record(f"formal.fold{fold}.status", fold_comp.get("status") == "TRAINING_COMPLETE_NOT_INFERRED")
        checks.record(f"formal.fold{fold}.config_sha256", fold_comp.get("config_sha256") == cfg_sha)

        epochs_p = fdir / "epochs.jsonl"
        with open(epochs_p) as f:
            epoch_lines = sum(1 for _ in f)
        checks.record(f"formal.fold{fold}.epochs_count", epoch_lines == 200, f"{epoch_lines} epochs")

        checks.record(f"formal.fold{fold}.recovery_exists", (fdir / "recovery.pt").exists())

        for ep in SNAPSHOT_EPOCHS:
            pth_file = fdir / f"first_part_{ep}.pth"
            receipt_file = fdir / f"first_part_{ep}.json"
            checks.record(f"formal.fold{fold}.ep{ep}.pth_exists", pth_file.exists())
            receipt = json.loads(receipt_file.read_text())
            pth_sha = sha256(pth_file)
            checks.record(
                f"formal.fold{fold}.ep{ep}.sha256",
                pth_sha == receipt["checkpoint_sha256"],
                f"actual={pth_sha} receipt={receipt['checkpoint_sha256']}",
            )
            if ep in ENDPOINT_EPOCHS:
                fold_endpoint_checkpoints[(fold, ep)] = pth_sha

    # --- 4. OOF receipts & cross-matching ---
    oof_dir = report_dir / "oof"
    expected_rows = {1: 1482, 2: 1481}

    for ep in ENDPOINT_EPOCHS:
        for fold in FOLDS:
            f_oof = oof_dir / f"epoch{ep}" / f"fold{fold}"
            comp_file = f_oof / "complete.json"
            checks.record(f"oof.ep{ep}.fold{fold}.complete_exists", comp_file.exists())
            oof_comp = json.loads(comp_file.read_text())
            checks.record(
                f"oof.ep{ep}.fold{fold}.checkpoint_cross_match",
                oof_comp["checkpoint_sha256"] == fold_endpoint_checkpoints[(fold, ep)],
                f"oof_receipt={oof_comp['checkpoint_sha256']} formal_pth={fold_endpoint_checkpoints[(fold, ep)]}",
            )

            metrics_file = f_oof / "metrics.csv"
            metrics_sha = sha256(metrics_file)
            checks.record(
                f"oof.ep{ep}.fold{fold}.metrics_sha256",
                metrics_sha == oof_comp["metrics_sha256"],
                f"actual={metrics_sha} receipt={oof_comp['metrics_sha256']}",
            )
            with open(metrics_file) as f:
                m_rows = sum(1 for _ in f) - 1
            checks.record(
                f"oof.ep{ep}.fold{fold}.metric_rows",
                m_rows == expected_rows[fold],
                f"rows={m_rows} expected={expected_rows[fold]}",
            )

    # --- 5. PyTorch weights load test ---
    import torch

    for (fold, ep), pth_sha in fold_endpoint_checkpoints.items():
        pth_file = formal_dir / f"fold{fold}" / f"first_part_{ep}.pth"
        try:
            ckpt = torch.load(pth_file, map_location="cpu", weights_only=False)
            keys = set(ckpt.keys())
            has_keys = {"model", "optimizer", "epoch"}.issubset(keys)
            checks.record(f"torch.load.fold{fold}.ep{ep}.keys", has_keys, str(sorted(keys)))

            # Check parameter finiteness
            model_sd = ckpt["model"]
            non_finite = []
            for k, v in model_sd.items():
                if torch.is_tensor(v) and v.is_floating_point():
                    if not torch.isfinite(v).all():
                        non_finite.append(k)
            checks.record(
                f"torch.load.fold{fold}.ep{ep}.tensors_finite",
                len(non_finite) == 0,
                f"non-finite={non_finite}" if non_finite else "all parameters finite",
            )
        except Exception as e:
            checks.record(f"torch.load.fold{fold}.ep{ep}.exception", False, str(e))

    # --- 6. Symlink check ---
    results_dir = REPO / "results" / "tabular_mlp_20261028_v3"
    checks.record("symlink.formal", (results_dir / "formal").is_symlink() and (results_dir / "formal").exists())
    checks.record("symlink.runtime", (results_dir / "runtime").is_symlink() and (results_dir / "runtime").exists())

    # --- 7. Final status & download receipt ---
    duration = time.time() - t0
    checks.info("verification_duration_sec", f"{duration:.2f}")

    receipt_status = "ALL_VERIFICATIONS_PASSED" if checks.all_passed else "VERIFICATION_FAILED"
    receipt_payload = {
        "status": receipt_status,
        "verified_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "hostname": socket.gethostname(),
        "duration_sec": duration,
        "config_sha256": cfg_sha,
        "report_dir": str(report_dir),
        "assets_dir": str(assets_dir),
        "endpoint_checkpoints": {f"fold{f}_ep{e}": s for (f, e), s in fold_endpoint_checkpoints.items()},
        "release_gate": (
            "AutoDL instance 1 (ssh -p 36733 root@connect.weste.seetacloud.com) and instance 2 "
            "(ssh -p 40818 root@connect.westb.seetacloud.com) may be safely shut down and unsubscribed "
            "by the user only when status is ALL_VERIFICATIONS_PASSED"
        ),
        "checks": checks.items,
    }

    out_receipt = report_dir / "download_receipt.json"
    out_receipt.write_text(json.dumps(receipt_payload, indent=2, ensure_ascii=False) + "\n")
    print(f"[RECEIPT] wrote {out_receipt}")

    if checks.all_passed:
        print("\n========================================================")
        print("   ALL_VERIFICATIONS_PASSED -- SAFE TO UNSUBSCRIBE")
        print("========================================================\n")
        return True
    else:
        print("\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        print("   VERIFICATION_FAILED -- DO NOT UNSUBSCRIBE")
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--assets", type=Path, default=DEFAULT_ASSETS)
    args = parser.parse_args()
    success = verify(args.report, args.assets)
    sys.exit(0 if success else 1)
