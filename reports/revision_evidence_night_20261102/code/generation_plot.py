from pathlib import Path
import pandas as pd,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import MaxNLocator
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102'
d=pd.read_csv(OUT/'G3/paired_comparisons.csv');models=['ClinicalUNet','SwinUNETR','Single','TabularMLP','TracerOnly'];names=['Clinical U-Net e165','SwinUNETR e200 (MRI only)','Single e165','Tabular MLP e165','Tracer-only e165']
fig,axes=plt.subplots(2,4,figsize=(16,7.4),sharey=True)
for ti,tracer in enumerate(('fdg','av45')):
    for mi,metric in enumerate(('ssim','psnr','mse','mae')):
        ax=axes[ti,mi]
        for yi,model in enumerate(models):
            r=d[(d.model==model)&(d.tracer==tracer)&(d.metric==metric)].iloc[0]
            ax.plot([r.ci_low,r.ci_high],[yi,yi],lw=1.5,color='#2864A5');ax.scatter([r.mean_delta],[yi],s=36,edgecolor='#2864A5',facecolor='#2864A5' if r.p_holm<.05 else 'white',zorder=3)
        ax.axvline(0,color='.4',ls='--',lw=1);ax.set_yticks(range(5),names);ax.set_ylim(4.6,-.6)
        ax.set_title(tracer.upper()+' / '+metric.upper()+(' ↑' if metric in ('ssim','psnr') else ' ↓'))
        ax.set_xlabel('Full − comparator'+(' (dB)' if metric=='psnr' else ''))
        ax.spines[['top','right']].set_visible(False);ax.tick_params(axis='x',labelsize=8);ax.grid(axis='x',alpha=.15)
        ax.xaxis.set_major_locator(MaxNLocator(nbins=4))
        if metric=='mse':ax.ticklabel_format(axis='x',style='sci',scilimits=(0,0),useMathText=True)
fig.suptitle('Frozen OOF generation comparisons: paired mean differences and 95% CIs',fontsize=14)
fig.legend(handles=[Line2D([0],[0],marker='o',color='none',markerfacecolor='#2864A5',markeredgecolor='#2864A5',label='Holm p < 0.05'),Line2D([0],[0],marker='o',color='none',markerfacecolor='white',markeredgecolor='#2864A5',label='Holm p ≥ 0.05')],loc='lower center',bbox_to_anchor=(.6,.035),ncol=2,frameon=False)
fig.text(.6,.01,'Positive favors Full for SSIM/PSNR; negative favors Full for MSE/MAE. CIs are marginal; Holm family: 8 tests per comparator.\nFull e165; different inputs/endpoints and independent training realizations limit causal comparisons.',ha='center',fontsize=9)
fig.tight_layout(rect=(0,.11,1,.95));fig.savefig(OUT/'figures/G3_paired_forest.png',dpi=220);plt.close(fig)
print('COMPLETE generation forest',flush=True)
