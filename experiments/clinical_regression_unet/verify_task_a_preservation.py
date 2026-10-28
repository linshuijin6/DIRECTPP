"""Local preservation verification for the Task A lightweight transfer.

Run AFTER ``sync_task_a_lightweight.sh``.  Verifies, strictly against receipts
produced by the remote run (hashes are read from receipt files; the only
hardcoded value is the preregistered tolerance), that:

  1. the local instance-1 ``config.json`` is byte-identical to the deployed
     remote copy, proven through the ``config_sha256`` identity embedded in
     every checkpoint receipt (not through hardcoded digests);
  2. the instance-1 config agrees with the node3014 local-path twin on every
     scientific field, so local dataset construction is legitimate;
  3. ``oof_summary`` CSVs match the hashes recorded in
     ``oof_summary/completion.json``;
  4. every snapshot checkpoint in ``formal/fold*`` matches its
     ``checkpoint_epoch{N}.json`` receipt, and the four fixed-endpoint
     checkpoints additionally cross-match ``oof/epoch*/fold*/complete.json``;
  5. every ``metrics.csv`` matches its ``complete.json`` receipt and the
     preregistered expected effective counts;
  6. the local Full cache name-set matches the frozen expectation, and the
     cache file used by the forward test is byte-identical to the remote one
     (remote hash captured by the sync script before instance release);
  7. all four fixed-endpoint checkpoints load in PyTorch with finite tensors;
  8. a single-sample forward pass on the local GPU reproduces the remote MSE
     within FORWARD_REL_TOLERANCE.  Cross-device (RTX 4090 -> RTX 3090,
     torch 2.7.0+cu128 -> 2.5.1) bit-exactness is NOT expected; the actual
     deviation is always recorded in the receipt.

Writes ``download_receipt.json`` and prints ``ALL_VERIFICATIONS_PASSED`` on
success; exits non-zero otherwise.  ``--print-heldout-first`` prints the first
held-out subject of a fold (used by the sync script for the remote snapshot).
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))

import run  # noqa: E402  -- experiments/clinical_regression_unet/run.py

REPORT_DIR = REPO / "reports" / "clinical_regression_unet_task_a_20261027_instance1"
INSTANCE1_CONFIG = REPORT_DIR / "config.json"
NODE3014_CONFIG = REPO / "reports" / "clinical_regression_unet_task_a_20261027_node3014_parallel" / "config.json"
TARGET_STORAGE = Path("/mnt/datas230/users/linshuijin/DIRECTPP_clinical_regression_unet/task_a_20261027")
REMOTE_HASH_FILE = TARGET_STORAGE / "remote_cache_subject_hashes.json"
FORWARD_REL_TOLERANCE = 1e-6
FOLDS = (1, 2)
EPOCHS = (165, 200)

SCIENTIFIC_FIELDS = (
    "cohort_sha256",
    "split_manifest_sha256",
    "input_hashes_sha256",
    "clinical_table_sha256",
    "clinical_features_sha256",
    "fold_normalization",
    "fold_counts",
    "expected_effective_by_fold",
    "expected_effective",
    "model",
    "seed",
    "epochs",
    "primary_epoch",
    "secondary_epoch",
)

CHECKPOINT_KEYS = (
    "model",
    "optimizer",
    "epoch",
    "experiment",
    "fold",
    "config_sha256",
    "cohort_sha256",
    "split_manifest_sha256",
    "clinical_features_sha256",
    "model_source_sha256",
)


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


def config_phase(checks: Checks) -> tuple[dict, str, dict, list, list]:
    instance1 = json.loads(INSTANCE1_CONFIG.read_text())
    node_cfg = json.loads(NODE3014_CONFIG.read_text())
    config_sha = run.sha256(INSTANCE1_CONFIG)
    mismatched = [k for k in SCIENTIFIC_FIELDS if instance1.get(k) != node_cfg.get(k)]
    checks.record(
        "config.scientific_fields_match_local_twin",
        not mismatched,
        f"mismatched fields: {mismatched}" if mismatched else "all scientific fields identical",
    )

    cfg, cohort, features = run.load_config(NODE3014_CONFIG)
    checks.record("config.local_twin_loads_frozen_artifacts", True, "load_config verified all frozen hashes")
    for key in ("cohort_sha256", "split_manifest_sha256", "clinical_features_sha256"):
        checks.record(
            f"config.local_twin_identity[{key}]",
            cfg[key] == instance1[key],
            f"{cfg[key]}",
        )
    return instance1, config_sha, cfg, cohort, features


def summary_phase(checks: Checks, instance1: dict) -> None:
    summary_dir = REPORT_DIR / "oof_summary"
    completion = json.loads((summary_dir / "completion.json").read_text())
    checks.record(
        "oof_summary.status",
        completion["status"] == "COMPLETE_TWO_FOLD_OOF_CLINICAL_REGRESSION_UNET",
        completion["status"],
    )
    for key, filename in (
        ("per_subject_sha256", "per_subject_metrics.csv"),
        ("overall_sha256", "overall_summary.csv"),
        ("by_fold_sha256", "by_fold_summary.csv"),
    ):
        digest = run.sha256(summary_dir / filename)
        checks.record(f"oof_summary.receipt[{filename}]", digest == completion[key], digest)

    per_subject = run.read_csv(summary_dir / "per_subject_metrics.csv")
    overall = run.read_csv(summary_dir / "overall_summary.csv")
    by_fold = run.read_csv(summary_dir / "by_fold_summary.csv")
    expected_per_subject = 2 * sum(instance1["expected_effective"].values())
    checks.record(
        "oof_summary.row_counts",
        len(per_subject) == expected_per_subject and len(overall) == 4 and len(by_fold) == 8,
        f"per_subject={len(per_subject)}/{expected_per_subject} overall={len(overall)}/4 by_fold={len(by_fold)}/8",
    )


def checkpoint_phase(checks: Checks, config_sha: str) -> None:
    for fold in FOLDS:
        fold_dir = TARGET_STORAGE / "formal" / f"fold{fold}"
        snapshots = sorted(fold_dir.glob("checkpoint_epoch*.pt"))
        checks.record(
            f"formal.fold{fold}.snapshot_count",
            len(snapshots) == 21,
            f"{len(snapshots)} snapshot checkpoints",
        )
        receipt_failures = []
        for checkpoint in snapshots:
            receipt = json.loads(checkpoint.with_suffix(".json").read_text())
            if run.sha256(checkpoint) != receipt["checkpoint_sha256"]:
                receipt_failures.append(checkpoint.name)
        checks.record(
            f"formal.fold{fold}.all_snapshot_receipts",
            not receipt_failures,
            f"{len(snapshots)} receipts verified; mismatches: {receipt_failures}",
        )

        for epoch in EPOCHS:
            receipt = json.loads((fold_dir / f"checkpoint_epoch{epoch}.json").read_text())
            checks.record(
                f"checkpoint.identity[fold{fold}/e{epoch}]",
                receipt["config_sha256"] == config_sha,
                f"receipt config_sha256 {receipt['config_sha256']}",
            )
            oof_receipt = json.loads(
                (REPORT_DIR / "oof" / f"epoch{epoch}" / f"fold{fold}" / "complete.json").read_text()
            )
            checkpoint = fold_dir / f"checkpoint_epoch{epoch}.pt"
            checks.record(
                f"oof.cross_checkpoint_sha[fold{fold}/e{epoch}]",
                oof_receipt["checkpoint_sha256"] == run.sha256(checkpoint),
                f"{oof_receipt['checkpoint_sha256']}",
            )


def metrics_phase(checks: Checks, cfg: dict) -> None:
    for fold in FOLDS:
        for epoch in EPOCHS:
            directory = REPORT_DIR / "oof" / f"epoch{epoch}" / f"fold{fold}"
            receipt = json.loads((directory / "complete.json").read_text())
            checks.record(
                f"oof.metrics_receipt[fold{fold}/e{epoch}]",
                run.sha256(directory / "metrics.csv") == receipt["metrics_sha256"],
                receipt["metrics_sha256"],
            )
            rows = run.read_csv(directory / "metrics.csv")
            counts = {t: sum(r["tracer"] == t for r in rows) for t in run.TRACERS}
            expected = {k: int(v) for k, v in cfg["expected_effective_by_fold"][str(fold)].items()}
            checks.record(
                f"oof.metric_counts[fold{fold}/e{epoch}]",
                counts == expected,
                f"actual {counts} vs expected {expected}",
            )


def checkpoint_health_phase(checks: Checks, config_sha: str) -> None:
    import torch

    for fold in FOLDS:
        for epoch in EPOCHS:
            checkpoint = TARGET_STORAGE / "formal" / f"fold{fold}" / f"checkpoint_epoch{epoch}.pt"
            state = torch.load(checkpoint, map_location="cpu", weights_only=False)
            missing = [k for k in CHECKPOINT_KEYS if k not in state]
            checks.record(
                f"checkpoint.structure[fold{fold}/e{epoch}]",
                not missing,
                f"missing keys: {missing}" if missing else f"epoch={state.get('epoch')} fold={state.get('fold')}",
            )
            checks.record(
                f"checkpoint.embedded_identity[fold{fold}/e{epoch}]",
                state.get("config_sha256") == config_sha,
                f"{state.get('config_sha256')}",
            )
            finite = all(
                bool(torch.isfinite(tensor).all())
                for tensor in state["model"].values()
                if hasattr(tensor, "isfinite")
            )
            checks.record(f"checkpoint.finite_tensors[fold{fold}/e{epoch}]", finite)


def cache_phase(checks: Checks, cfg: dict, cohort: list) -> dict:
    cache_dir = Path(cfg["cache"]["cache_dir"])
    receipt = run.validate_cache(cache_dir, cohort)
    checks.record(
        "cache.name_set_matches_frozen_expectation",
        receipt["cache_name_set_sha256"] == cfg["cache"]["cache_name_set_sha256"]
        and receipt["files"] == cfg["cache"]["files"],
        f"files={receipt['files']} name_set_sha256={receipt['cache_name_set_sha256']}",
    )
    if not REMOTE_HASH_FILE.is_file():
        checks.record("cache.remote_hash_file", False, f"missing {REMOTE_HASH_FILE}")
        return {}
    return json.loads(REMOTE_HASH_FILE.read_text())


def forward_phase(checks: Checks, cfg: dict, cohort: list, features: list, remote_hashes: dict) -> dict:
    """Single-sample forward reproduction test.

    Gated comparison: the remote-cache probe file (byte-identical to the
    instance-1 input, fetched into remote_cache_probe/) isolates the pure
    compute difference (RTX 4090/torch 2.7.0+cu128 -> local GPU/torch).  The
    local nfs_backup cache differs from the remote cache at the float32
    last-bit level (documented in the node3014 deployment receipt: max abs
    1.79e-7, voxels over 1e-6 = 0), so its forward is recorded as INFO
    diagnostics, not as a release gate.
    """
    import torch
    import torch.nn.functional as F

    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False
    if not torch.cuda.is_available():
        checks.record("forward.cuda_available", False, "no CUDA device visible")
        return {}

    _, held_ds = run.datasets_for_fold(cfg, cohort, features, 1)
    ptid = held_ds.rows[0]["name"]
    cache_path = held_ds.paths[0]
    remote_entry = remote_hashes.get("subjects", {}).get("1", {})
    checks.record(
        "forward.first_subject_matches_remote_selection",
        remote_entry.get("ptid") == ptid and remote_entry.get("cache_file") == cache_path.name,
        f"local ptid={ptid} cache={cache_path.name}; remote ptid={remote_entry.get('ptid')} "
        f"cache={remote_entry.get('cache_file')}",
    )
    checks.info(
        "forward.cache_provenance_note",
        "local nfs_backup cache differs from the instance-1 cache at the float32 last-bit level "
        "(node3014 deployment_receipt.json: mri/fdg max abs 1.79e-7, av45 0.0, voxels over 1e-6 = 0); "
        "whole-file SHA differs accordingly",
    )

    def load_cache_sample(path: Path) -> dict:
        cached = torch.load(path, map_location="cpu", weights_only=False)
        checks.record(
            f"forward.cache_identity[{path.name}]",
            cached.get("name") == ptid,
            f"cached name={cached.get('name')} expected={ptid}",
        )
        sample = {"name": cached["name"]}
        for key in ("mri", "fdg", "av45"):
            tensor = cached[key].as_tensor() if hasattr(cached[key], "as_tensor") else cached[key]
            tensor = tensor.detach().float()
            if tuple(tensor.shape) != (1, 160, 192, 160) or not torch.isfinite(tensor).all():
                raise RuntimeError(f"Invalid cached tensor for {ptid}/{key} in {path.name}")
            sample[key] = tensor
        sample["clinical"] = torch.from_numpy(
            run.standardized_vector(held_ds.features[ptid], held_ds.normalization)
        )
        return sample

    probe_path = TARGET_STORAGE / "remote_cache_probe" / cache_path.name
    if not probe_path.is_file():
        checks.record(
            "forward.remote_cache_probe_file",
            False,
            f"missing {probe_path}; fetch the probe file before verification",
        )
        return {}
    probe_digest = run.sha256(probe_path)
    checks.record(
        "forward.remote_cache_probe_file_identical_to_instance1",
        probe_digest == remote_entry.get("remote_cache_sha256"),
        probe_digest,
    )
    remote_sample = load_cache_sample(probe_path)
    local_digest = run.sha256(cache_path)
    checks.info(
        "forward.local_cache_file_hash",
        f"local {local_digest} vs instance-1 {remote_entry.get('remote_cache_sha256')} "
        "(expected: differs at float32 last-bit level, see provenance note)",
    )

    metrics_path = REPORT_DIR / "oof" / "epoch165" / "fold1" / "metrics.csv"
    rows = run.read_csv(metrics_path)
    by_key = {(r["ptid"], r["tracer"]): r for r in rows}

    checkpoint = TARGET_STORAGE / "formal" / "fold1" / "checkpoint_epoch165.pt"
    state = torch.load(checkpoint, map_location="cpu", weights_only=False)
    model = run.new_model()
    model.load_state_dict(state["model"])
    model.cuda().eval()

    device = torch.device("cuda")
    results: dict = {}

    def forward_sample(sample: dict, label: str, gated: bool) -> None:
        mri = sample["mri"].unsqueeze(0).to(device)
        clinical = sample["clinical"].unsqueeze(0).to(device)
        with torch.no_grad():
            for tracer in run.TRACERS:
                target = sample[tracer].unsqueeze(0).to(device)
                if bool(torch.all(target == 0)):
                    continue
                condition = run.tracer_condition(tracer, 1, device)
                prediction = torch.clamp(model(mri, clinical, condition).float(), 0, 1)
                repeat = torch.clamp(model(mri, clinical, condition).float(), 0, 1)
                if gated:
                    checks.record(
                        f"forward.deterministic[{tracer}]",
                        bool(torch.equal(prediction, repeat)),
                        "repeated eval forward must be identical",
                    )
                mse = float(F.mse_loss(prediction, target.float()))
                remote_row = by_key.get((ptid, tracer))
                checks.record(
                    f"forward.remote_row_present[{tracer}]",
                    remote_row is not None,
                    f"ptid={ptid} tracer={tracer}",
                )
                if remote_row is None:
                    continue
                remote_mse = float(remote_row["mse"])
                rel_diff = abs(mse - remote_mse) / abs(remote_mse)
                entry = {
                    "ptid": ptid,
                    "cache_source": label,
                    "local_mse": mse,
                    "remote_mse": remote_mse,
                    "abs_diff": abs(mse - remote_mse),
                    "rel_diff": rel_diff,
                    "tolerance": FORWARD_REL_TOLERANCE,
                }
                results.setdefault(tracer, {})[label] = entry
                detail = (
                    f"local={mse:.17g} remote={remote_mse:.17g} rel_diff={rel_diff:.3e} "
                    f"(tolerance {FORWARD_REL_TOLERANCE:.0e})"
                )
                if gated:
                    checks.record(
                        f"forward.remote_cache.mse_within_tolerance[{tracer}]",
                        rel_diff <= FORWARD_REL_TOLERANCE,
                        detail,
                    )
                else:
                    checks.info(
                        f"forward.local_cache.mse_diff[{tracer}]",
                        detail + " [INFO: local cache last-bit difference documented upstream]",
                    )

    forward_sample(remote_sample, "remote_cache_probe", gated=True)
    local_sample = load_cache_sample(cache_path)
    forward_sample(local_sample, "local_nfs_backup", gated=False)
    return results


def environment() -> dict:
    import torch

    info = {
        "host": socket.gethostname(),
        "python": sys.version.split()[0],
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "cudnn": torch.backends.cudnn.version(),
        "cudnn_deterministic": True,
    }
    if torch.cuda.is_available():
        props = torch.cuda.get_device_properties(0)
        info["gpu"] = {
            "name": props.name,
            "uuid": str(getattr(props, "uuid", None)),
            "total_memory_bytes": props.total_memory,
        }
    try:
        import monai  # noqa: F401

        import importlib.metadata as metadata

        info["monai"] = metadata.version("monai")
    except Exception:
        info["monai"] = None
    return info


def print_heldout_first(fold: int) -> None:
    cfg, cohort, features = run.load_config(NODE3014_CONFIG)
    _, held_ds = run.datasets_for_fold(cfg, cohort, features, fold)
    print(
        json.dumps(
            {
                "fold": fold,
                "ptid": held_ds.rows[0]["name"],
                "cache_file": held_ds.paths[0].name,
                "local_cache_dir": str(Path(cfg["cache"]["cache_dir"])),
                "held_out_subjects": len(held_ds),
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--print-heldout-first", action="store_true")
    parser.add_argument("--fold", type=int, choices=(1, 2))
    args = parser.parse_args()
    if args.print_heldout_first:
        if args.fold is None:
            parser.error("--print-heldout-first requires --fold")
        print_heldout_first(args.fold)
        return

    started = time.time()
    checks = Checks()
    instance1, config_sha, cfg, cohort, features = config_phase(checks)
    summary_phase(checks, instance1)
    checkpoint_phase(checks, config_sha)
    metrics_phase(checks, cfg)
    checkpoint_health_phase(checks, config_sha)
    remote_hashes = cache_phase(checks, cfg, cohort)
    forward = forward_phase(checks, cfg, cohort, features, remote_hashes)

    passed = checks.all_passed
    receipt = {
        "status": "ALL_VERIFICATIONS_PASSED" if passed else "VERIFICATION_FAILED",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "host": socket.gethostname(),
        "duration_seconds": round(time.time() - started, 1),
        "environment": environment(),
        "instance1_config_sha256": config_sha,
        "forward_tolerance_policy": (
            "cross-device (RTX 4090/torch 2.7.0+cu128 -> local) bit-exactness not expected; "
            f"MSE relative deviation <= {FORWARD_REL_TOLERANCE:.0e} required, actual recorded"
        ),
        "forward": forward,
        "checks": checks.items,
        "symlink_note": (
            "results/clinical_regression_unet_task_a_20261027/{formal,runtime} are symlinks to "
            "/mnt/datas230/users/linshuijin/DIRECTPP_clinical_regression_unet/task_a_20261027/ ; "
            "absolute paths are valid on this host only"
        ),
        "release_gate": (
            "AutoDL instance 1 (ssh -p 36733 root@connect.weste.seetacloud.com) and instance 2 "
            "(ssh -p 40818 root@connect.westb.seetacloud.com) may be shut down and released by "
            "the user only when status is ALL_VERIFICATIONS_PASSED"
        ),
    }
    run.json_write(REPORT_DIR / "download_receipt.json", receipt)
    print(json.dumps({"status": receipt["status"], "checks": len(checks.items)}, ensure_ascii=False))
    if not passed:
        sys.exit(1)
    print("ALL_VERIFICATIONS_PASSED")


if __name__ == "__main__":
    main()




