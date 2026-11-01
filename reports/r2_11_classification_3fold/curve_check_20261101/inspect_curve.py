"""Read-only analysis of the one randomly sampled completed classification fit."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
h = pd.read_csv(ROOT / "history.csv")
s = json.loads((ROOT / "summary.json").read_text())
selection = json.loads((ROOT / "selection.json").read_text())
v = h[h.val_ACC.notna()].copy()
assert h.epoch.tolist() == list(range(1, 201))
assert v.epoch.tolist() == list(range(2, 201, 2))
assert np.isfinite(h.loss).all() and (h.loss > 0).all()
assert np.isfinite(v[["val_ACC", "val_AUC"]].to_numpy()).all()
assert v[["val_ACC", "val_AUC"]].ge(0).all().all()
assert v[["val_ACC", "val_AUC"]].le(1).all().all()
best = v.loc[v.val_ACC.idxmax()]
assert int(best.epoch) == s["best_epoch"]
assert np.isclose(best.val_ACC, s["best_validation_ACC"])
assert int(h.loc[h.checkpoint_s > 0, "epoch"].iloc[-1]) == s["best_epoch"]

windows = []
for lo, hi in [(1, 20), (21, 50), (51, 100), (101, 150), (151, 200)]:
    train = h[h.epoch.between(lo, hi)]
    val = v[v.epoch.between(lo, hi)]
    windows.append(dict(first_epoch=lo, last_epoch=hi, loss_mean=float(train.loss.mean()),
                        loss_median=float(train.loss.median()), loss_min=float(train.loss.min()),
                        loss_max=float(train.loss.max()), val_ACC_mean=float(val.val_ACC.mean()),
                        val_ACC_min=float(val.val_ACC.min()), val_ACC_max=float(val.val_ACC.max()),
                        val_AUC_mean=float(val.val_AUC.mean()), val_AUC_min=float(val.val_AUC.min()),
                        val_AUC_max=float(val.val_AUC.max())))
pd.DataFrame(windows).to_csv(ROOT / "window_statistics.csv", index=False)
result = dict(selected=selection["selected"], candidate_count=selection["candidate_count"],
              random_seed=selection["seed"], epochs=len(h), validation_points=len(v),
              first_loss=float(h.loss.iloc[0]), last_loss=float(h.loss.iloc[-1]),
              best_ACC_epoch=int(best.epoch), best_validation_ACC=float(best.val_ACC),
              AUC_at_selected_checkpoint=float(best.val_AUC),
              best_AUC_epoch=int(v.loc[v.val_AUC.idxmax(), "epoch"]),
              best_validation_AUC=float(v.val_AUC.max()), windows=windows,
              checkpoint_rule_verified="First maximum internal validation ACC; last actual save matches summary",
              validation_loss_available=False,
              scope="One random completed fit; no conclusion about all 63 fits; test metrics not used for convergence assessment",
              interpretation="Training objective reaches a low stable late regime; validation metrics plateau without persistent late deterioration. Strong training fit is not proof of generalization.")
(ROOT / "curve_check.json").write_text(json.dumps(result, indent=2) + "\n")

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                     "axes.spines.top": False, "axes.spines.right": False})
fig, axes = plt.subplots(1, 2, figsize=(12.5, 4.5), constrained_layout=True)
blue, orange, dark = "#235789", "#C46B20", "#454545"
axes[0].semilogy(h.epoch, h.loss, color=blue, linewidth=1.5)
axes[0].set(title="Training objective", xlabel="Epoch", ylabel="Training cross-entropy (log scale)")
axes[0].set_ylim(1e-5, 1)
axes[1].plot(v.epoch, v.val_ACC, color=blue, linewidth=1.3, label="Validation ACC")
axes[1].plot(v.epoch, v.val_AUC, color=orange, linewidth=1.3, linestyle="--", label="Validation AUC")
axes[1].set(title="Internal validation performance", xlabel="Epoch", ylabel="Score", ylim=(0, 1))
axes[1].scatter([best.epoch], [best.val_ACC], marker="*", s=120, color=dark, zorder=5)
axes[1].annotate(f"Selected epoch {int(best.epoch)}\nACC = {best.val_ACC:.3f}",
                 xy=(best.epoch, best.val_ACC), xytext=(65, .92),
                 arrowprops=dict(arrowstyle="->", color=dark, lw=.9), color=dark)
axes[1].legend(loc="lower right", frameon=False)
for ax in axes:
    ax.axvline(best.epoch, color=dark, linestyle=":", linewidth=1)
    ax.axvspan(151, 200, color="#C7C7C7", alpha=.16, zorder=0)
    ax.set_xlim(1, 200)
    ax.set_xticks([1, 24, 50, 100, 150, 200])
    ax.grid(axis="y", alpha=.18)
fig.suptitle("EMCI+LMCI vs CN | MRI + Real FDG + Real AV45 | Fold 1\n"
             "Train n=419; validation n=75; raw curves; shaded region: epochs 151-200", fontsize=11)
fig.savefig(ROOT / "training_curves.png", dpi=180)
plt.close(fig)
print(json.dumps(result, indent=2))
