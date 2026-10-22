# Tracer-only control

This entrypoint reuses `experiments/original_author_reproduction/run.py` and
changes only the runtime conditioning context from `[patient, tracer]` to
`[fixed empty-patient, tracer]`.  It does not import the E1 trainer.

The prepared control keeps a byte-identical link to Full `conditions.pt` only
to address the already completed PersistentDataset cache namespace.  Cached
`fdg_index` and `av45_index` values are never sent to the model: the shared
train, validation, and inference paths call a context hook which this entrypoint
replaces with the frozen tracer-only context.

Run `prepare` once, then require both static and CUDA preflight to pass.  Formal
training is a separate manual action and must run both folds.

```sh
python experiments/tracer_only_control/run.py prepare \
  --full-config reports/original_author_reproduction_20261020/config_autodl.json \
  --out reports/tracer_only_control_20261022 \
  --assets /root/autodl-tmp/directpp_tracer_only_assets

# The base entrypoint must still pass its unchanged CUDA formula check after
# the context hook was introduced. This writes only into the control report.
python experiments/original_author_reproduction/run.py parity-check \
  --config reports/tracer_only_control_20261022/config.json --cuda

python experiments/tracer_only_control/run.py preflight \
  --config reports/tracer_only_control_20261022/config.json --cuda
```

Formal commands are intentionally not launched by preparation or preflight:

```sh
python -u experiments/tracer_only_control/run.py train --config reports/tracer_only_control_20261022/config.json --fold 1
python -u experiments/tracer_only_control/run.py train --config reports/tracer_only_control_20261022/config.json --fold 2
```

Resume only from the same control fold's recovery file.  Inference is allowed
only at the preregistered epochs 165 and 200, using the same CLI shape as the
Full entrypoint.
