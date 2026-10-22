# Gemini 监控与后续执行指令

你接管的是 DIReCT++ 原作者训练语义的隔离两折复现。请先读：

- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/AGENTS.md`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/CORE_CODE.md`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/experiments/original_author_reproduction/README.md`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/config.json`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/fold1_launch_receipt.json`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/parity_receipt.json`
- `/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/input_hash_receipt.json`

## 固定边界

1. 当前训练节点是 `3003`（主机报告名 `pnxc`），只允许使用物理 GPU5，UUID
   `GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417`。GPU0 已按用户要求释放，未经用户重新授权不得使用或占用。
2. 不修改 `run.py`、config、cohort、split、conditions、输入数据或已有 checkpoint；不删除失败目录；不覆盖任何输出。
3. 不终止 PID `951827` 或 `951830`。不因日志暂时不更新而重启。禁止自动 resume、自动修复或自动重跑。
4. 本实验是新重建的 `KFold(2, shuffle=True, random_state=42)`，不是找回的论文历史两折名单；正式训练 RNG 保持原作者 notebook 的未设 seed 语义，即 `training_seed=null`。
5. epoch 165 是主终点，epoch 200 是次终点。只做两折 OOF 生成与 SSIM/PSNR/MSE/MAE，不做分类。
6. 任何“启动”“缓存完成”“出现 checkpoint”都不等于训练完成。只有 `complete.json`、对应 `foldN.exit` 值为 0、进程退出和两个固定终点 checkpoint/收据均成立，才可称该折训练完成。

## 当前已核实状态（接管基线）

- fold1 launcher PID：`951827`
- fold1 Python PID：`951830`
- 启动时间：`2026-10-20 20:51:44 Asia/Shanghai`
- fold1 日志：`/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/fold1.log`
- fold1 退出码文件：`/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/fold1.exit`
- 最后一次移交快照仍在构建第二个 CacheDataset，进度 `150/929`；当时尚无 optimizer update。你必须以新的实时证据更新状态。
- 缓存阶段 Python 会在 GPU5 主动保留约 43 GiB，避免卡被抢占；缓存完成后代码会释放该保留，再创建模型。这是预期行为。
- CUDA 全体积双 tracer 单步预检已 PASS；峰值 allocated `46866800128` bytes，reserved `48901390336` bytes。

## fold1 只读监控

建议每 5–15 分钟检查一次，避免高频轮询：

```sh
ssh 3003 'ps -p 951827,951830 -o pid=,ppid=,stat=,etimes=,rss=,lstart=,cmd='
ssh 3003 'nvidia-smi -i 5 --query-gpu=index,uuid,memory.used,memory.free,utilization.gpu --format=csv,noheader && nvidia-smi --query-compute-apps=pid,gpu_uuid,used_memory --format=csv,noheader'
ssh 3003 "tr '\0' '\n' </proc/951830/environ | grep -Fx 'CUDA_VISIBLE_DEVICES=GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417'"
ssh 3003 "tail -c 65536 /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/fold1.log | tr '\r' '\n' | tail -n 80"
```

缓存结束后应出现：

```text
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/start.json
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/training_trace.jsonl
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/epochs.jsonl
```

首次出现 `training_trace.jsonl` 后，核查最初 5 个记录均有有限的 `loss`，且 epoch/iteration 从 0/1 开始。若出现 traceback、CUDA OOM、nonfinite、进程消失且退出码非 0，立即停止后续动作，保留现场并报告；不要自行恢复。

fold1 完成门槛全部满足后才进入 fold2：

```text
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/complete.json
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/first_part_165.pth
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/first_part_165.json
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/first_part_200.pth
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/first_part_200.json
/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold1/recovery.pt
/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/reports/original_author_reproduction_20261020/fold1.exit  # 内容必须严格为 0
```

同时验证两个 `.pth` 的 SHA-256 与各自 `.json` 收据一致，`complete.json.status` 为
`TRAINING_COMPLETE_NOT_INFERRED`，且 PID 951830 已退出。

## 启动 fold2 前的失败关闭门槛

先在 3003 上验证代码和输入身份，任何不一致都不要启动：

```sh
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
sha256sum experiments/original_author_reproduction/run.py \
  reports/original_author_reproduction_20261020/config.json \
  reports/original_author_reproduction_20261020/input_hashes.csv \
  /mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/conditions.pt
```

期望值：

```text
a5920654d5215d1089b04ba8f3e2b53cd49e5f37e378d7499aaac173a9f66095  run.py
ebf7c664c6017ba459fb5875cd04952faf75c5f7d6010112740fdfde00afe454  config.json
3f362cdb3ebe8a945b106cc6974e4fbcea9e450474f3cc1f0db28a88ce81ed07  input_hashes.csv
bbcd413100d8ece3e878acffc1969723d091f64c49c57c76b486bd474f84384a  conditions.pt
```

然后确认：

- `/proc/meminfo` 的 `MemAvailable` 至少 `134217728 kB`（128 GiB）。
- GPU5 没有任何其他 compute PID，空闲显存至少 `48318382080` bytes（约 46080 MiB）。
- fold2 目录 `/mnt/datas230/users/linshuijin/DIRECTPP_original_author_repro/20261020/formal/fold2` 不存在。
- fold2 日志和退出码文件尚不存在；若已存在则停下调查，不覆盖。

满足全部门槛后，在 3003 上仅启动 fold2：

```sh
ssh 3003 'cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP && setsid sh -c '\''CUDA_VISIBLE_DEVICES=GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417 /home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py train --config reports/original_author_reproduction_20261020/config.json --fold 2 > reports/original_author_reproduction_20261020/fold2.log 2>&1; rc=$?; printf "%s\n" "$rc" > reports/original_author_reproduction_20261020/fold2.exit; exit "$rc"'\'' </dev/null >/dev/null 2>&1 & echo $!'
```

立刻记录新的 launcher PID、Python PID、`/proc/<python_pid>/stat` start time、GPU UUID、完整命令、日志路径和上述四个 SHA 到
`reports/original_author_reproduction_20261020/fold2_launch_receipt.json`。fold2 的监控和完成判据与 fold1 相同，但预期 train=929、held-out=928。

## 两折完成后的串行推理

只有 fold1 和 fold2 都通过完整完成门槛后，才在空闲 GPU5 上逐项串行执行。每个命令只有退出码 0 且对应 `oof/.../complete.json` 完整时才能进行下一项。不要并行，不要使用 GPU0。

```sh
cd /mnt/nfsdata/nfsdata/linshuijin/DIRECTPP
export CUDA_VISIBLE_DEVICES=GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py infer --config reports/original_author_reproduction_20261020/config.json --fold 1 --epoch 165
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py infer --config reports/original_author_reproduction_20261020/config.json --fold 2 --epoch 165
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py infer --config reports/original_author_reproduction_20261020/config.json --fold 1 --epoch 200
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py infer --config reports/original_author_reproduction_20261020/config.json --fold 2 --epoch 200
/home/data/linshuijin/.conda/envs/xiaochou/bin/python -u experiments/original_author_reproduction/run.py summarize --config reports/original_author_reproduction_20261020/config.json
```

建议为四次 infer 和 summarize 分别重定向独立日志并保存退出码；如果某个输出目录已经存在，不要删除或覆盖，先报告。

最终汇总必须验证每个 epoch 的 OOF 计数为 FDG `1598`、AV45 `1365`，并确认：

```text
reports/original_author_reproduction_20261020/oof_summary/completion.json
status = COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION
historical_fold_identity_recovered = false
training_seed = null
```

向用户报告时将状态严格区分为 `CACHE_BUILD`、`TRAINING_RUNNING`、`TRAINING_COMPLETE_NOT_INFERRED`、`INFERENCE_RUNNING` 和 `COMPLETE_TWO_FOLD_OOF_RECONSTRUCTION`。最终结果只能称为“原作者代码语义的新两折重建复现”，不能声称恢复了论文历史运行身份。
