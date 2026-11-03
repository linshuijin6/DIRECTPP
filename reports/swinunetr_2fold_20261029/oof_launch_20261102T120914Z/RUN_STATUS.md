# SwinUNETR epoch-200 OOF inference

Status observed at 2026-11-02T12:11:33.152115+00:00. Four concurrent remote inference tasks were authorized by the user; existing GPU tasks were retained. These are running tasks, not completed results.

| Instance | Tracer | Fold | Evaluated / expected | Seconds / subject | Estimated finish (Asia/Shanghai) |
|---|---|---|---|---|---|
| 3 | FDG | 1 | 98 / 792 | 1.35 | 2026-11-02 20:27 |
| 4 | FDG | 2 | 101 / 806 | 1.30 | 2026-11-02 20:26 |
| 5 | AV45 | 1 | 85 / 690 | 1.53 | 2026-11-02 20:27 |
| 6 | AV45 | 2 | 99 / 675 | 1.31 | 2026-11-02 20:24 |

Allow until approximately 20:35 on 2026-11-02 for GPU contention and final checks. These are measured-rate estimates, not guaranteed completion times. No OOM or inference errors were observed in the initial outputs.

The detached collector checks remote exit codes, metrics hashes, expected counts, finite metrics, checkpoint identity, and one-to-one subject/tracer/fold agreement with the frozen Full epoch-165 OOF identity set. It collects only metrics and receipts; images stay remote. It does not launch, stop or restart GPU tasks.

Live state: [status.json](status.json). Launch records: [launch.json](launch.json). On success the collector writes `per_subject_metrics.csv`, `summary.csv`, and `completion.json`; on failure it records `failure.json` or `collector_error.txt`. No automatic retraining or alternative checkpoint selection is performed.
