# DIReCT Single, frozen Full two-fold OOF

This experiment retrains four independent, single-tracer Rectified Flow models
under the Full cohort/split/cache protocol. It is not a historical checkpoint
recovery. The Single notebook's FDG PET text is extracted exactly from cell 2.
AV45 uses the Full author's `AV45_TEXT` wording, encoded afresh with the Single
BiomedCLIP tokenizer and `get_text_features(input_ids)` mechanism. Full adapted
tracer tensors never enter this experiment. Patient embeddings come from the
verified frozen Full Description and BiomedCLIP encoding receipt.

Each task owns its report, log, checkpoint, recovery, and OOF output. No task
writes the global summary. The outer held-out fold is never used in training.
Checkpoints are fixed at epoch 165 (primary) and 200 (secondary); training
continues through 200 epochs before OOF inference. Each task may start as soon
as its own resource and full-size preflight pass. One blocked task does not
block the others. A >72-hour task estimate blocks only that task.

## One-time condition preparation

On a machine with the verified Full BiomedCLIP bundle and Full conditions:

```sh
python experiments/baselines/direct_single/run.py prepare-conditions \
  --out reports/direct_single_2fold_20261030
```

`conditions_receipt.json` contains the exact FDG and AV45 input text batches,
their sources, encoding contract, weight identity, vector hashes, and Full
patient-vector source. Copy this read-only condition artifact to each target
instance. The task configuration is generated on each instance using its own
absolute paths.

The original model source is used unchanged. On nodes without `xformers`, the
experiment's isolated compatibility module implements its attention call with
PyTorch SDPA; the actual backend is recorded in the full-size preflight.

## Each task, independently

Run from the project root with the node's verified Python interpreter. Copy
the archived `generative` package unchanged if the node lacks it, and verify
its source hash. A resource receipt must establish `EXCLUSIVE` or
`SAFE_HANDOFF`, current host and GPU UUID, issuer and protection ID, and have
been issued within five minutes. Bind that UUID with `CUDA_VISIBLE_DEVICES`.

```sh
python experiments/baselines/direct_single/run.py prepare \
  --task fdg_fold1 \
  --out reports/direct_single_2fold_20261030 \
  --assets-root <isolated-assets-root> \
  --cache-dir <verified-Full-cache> \
  --conditions reports/direct_single_2fold_20261030/conditions.pt \
  --condition-receipt reports/direct_single_2fold_20261030/conditions_receipt.json
python experiments/baselines/direct_single/run.py check-config \
  --config reports/direct_single_2fold_20261030/fdg_fold1/config.json
CUDA_VISIBLE_DEVICES=<allocated-gpu-uuid> python experiments/baselines/direct_single/run.py smoke-test \
  --config reports/direct_single_2fold_20261030/fdg_fold1/config.json \
  --resource-receipt <fresh-resource-receipt.json>
CUDA_VISIBLE_DEVICES=<allocated-gpu-uuid> python -u experiments/baselines/direct_single/run.py train \
  --config reports/direct_single_2fold_20261030/fdg_fold1/config.json \
  --resource-receipt <fresh-resource-receipt.json> \
  --log-path reports/direct_single_2fold_20261030/fdg_fold1/train.log
```

Use `fdg_fold2`, `av45_fold1`, or `av45_fold2` in place of `fdg_fold1`.
The runner refuses training without a matching full-size preflight and current
resource receipt. To resume, pass only that task's `<assets>/formal/recovery.pt`.
The per-instance `handoff_and_launch.py` normally waits for the preceding Swin
training and OOF completion receipts and an empty dedicated GPU, then performs
this preflight and starts only its own task when its estimate is at most 72
hours. The `--allow-prior-oof-pending` option retains the preceding training
completion and GPU safety gates while allowing the independent Single training
to start before the preceding Swin OOF inference. This option was used for all
four launches on 2026-10-31 following the user's start instruction; the exact
handoff and launch receipts are in each task report directory.

After a task completes training, run `infer --config <task-config> --epoch 165`
and `infer --config <task-config> --epoch 200` on its held-out fold. Once all
four tasks have both OOF completion receipts, run `summarize` once with
`--out reports/direct_single_2fold_20261030`. The summary enforces the
one-to-one subject/tracer/fold match to Full epoch 165.
