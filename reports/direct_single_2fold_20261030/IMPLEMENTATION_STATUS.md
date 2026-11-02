# DIReCT Single two-fold OOF: implementation state

Initial deployment checked 2026-10-30 (UTC). This is an engineering receipt, not an OOF result.

- The four isolated task configurations exist under `fdg_fold1`, `fdg_fold2`,
  `av45_fold1`, and `av45_fold2`. The four corresponding cloud configurations
  and `check-config` receipts are copied into each task directory with a
  `remote_` prefix. All four remote checks passed.
- Frozen Full cohort SHA-256:
  `91ee8eeec5ea853c4517df868e85fccd2857164a8e4171ba81e45121e5dc9311`.
  Split SHA-256:
  `007e49835ed44c73dea69a94e390dded33c495c21033089f83d05b429519977c`.
  Input manifest SHA-256:
  `3f362cdb3ebe8a945b106cc6974e4fbcea9e450474f3cc1f0db28a88ce81ed07`.
- Both local and target cloud cache key sets contain 1,857 entries with the
  expected name-set hash
  `4284fd52b2c5b4b556fa3c32fbbeaa83fb88aaa324b21ddcfd6e991a0a517e5a`;
  sampled tensors have shape `[1,160,192,160]`.
- Frozen Single condition file SHA-256:
  `eb0ccf53b26c3a7ba3d06d6dc9ab71c0596fc695befca73fc4c931835fed64ba`.
  Exact texts, source locations, encoding steps, patient and tracer vector
  hashes are in `conditions_receipt.json`. Full adapted tracer vectors were
  not read into this file.
- Model construction on the local verified environment yielded 9,925,921
  parameters. This is not a target GPU full-size preflight.

| Task | Preferred instance | Training targets | Held-out valid targets | Initial state on 2026-10-30 |
|---|---:|---:|---:|---|
| FDG Fold 1 | 3 | 806 | 792 | Waiting for prior Swin training and OOF completion |
| FDG Fold 2 | 4 | 792 | 806 | Waiting for prior Swin training and OOF completion |
| AV45 Fold 1 | 5 | 675 | 690 | Waiting for prior Swin training and OOF completion |
| AV45 Fold 2 | 6 | 690 | 675 | Waiting for prior Swin training and OOF completion |

The initial handoff processes waited for both prior Swin training and OOF
completion receipts. They were replaced on 2026-10-31 as described below.

## Training launch update: 2026-10-31 UTC

The user requested an immediate start once the preceding four trainings had
finished. All four preceding Swin **training** completion receipts were present;
their OOF receipts were still absent. The four original CPU-only handoff
monitors were stopped after verifying their process identities. The updated
per-instance handoff allowed the preceding OOF to remain pending, but still
required the preceding training receipt, an empty dedicated GPU with at least
46,080 MiB free, a full-size optimizer preflight, and an estimated task duration
under 72 hours. The four Single tasks started independently. The pending Swin
OOF work is not represented here as complete.

| Single task | Instance | Training PID | Start UTC | Full-size median step | Estimated training hours | Status at launch check |
|---|---:|---:|---|---:|---:|---|
| FDG Fold 1 | 3 | 57412 | 2026-10-31 02:47:04 | 0.486 s | 21.78 | Running on dedicated GPU |
| FDG Fold 2 | 4 | 60766 | 2026-10-31 02:47:05 | 0.487 s | 21.43 | Running on dedicated GPU |
| AV45 Fold 1 | 5 | 42438 | 2026-10-31 02:49:04 | 0.483 s | 18.10 | Running on dedicated GPU |
| AV45 Fold 2 | 6 | 59831 | 2026-10-31 02:47:04 | 0.480 s | 18.39 | Running on dedicated GPU |

Each preflight used 12 full-volume forward/backward/optimizer steps (2 warmup,
10 measured) at image shape `[1,1,160,192,160]` and context shape `[1,2,512]`.
All 12 optimizer updates succeeded on each instance. Peak allocated GPU memory
was 24.18 GiB and peak reserved memory was 28.04 GiB on each. The attention
backend was the isolated `torch_sdpa_compat` implementation. These estimates
cover model-step time and may understate total wall time due to data loading,
checkpoint writes, and other overhead.

Actual launch, allocation, preflight, and handoff receipts are copied into each
task's report directory. Training logs remain on the corresponding instance at
`/root/autodl-tmp/DIRECTPP/reports/direct_single_2fold_20261030/<task>/train.log`;
checkpoint and recovery files will be written under
`/root/autodl-tmp/DIRECTPP_direct_single/20261030/<task>/formal/`. The first
recovery is scheduled at completed epoch 10. No training completion, checkpoint
milestone, or Single OOF result is claimed by this launch update.
