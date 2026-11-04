"""Reproducible native vector figures; no training, inference, data filling or result selection."""
from pathlib import Path
import json,hashlib,re,sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Patch
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'manuscript/figures';EDIT=OUT/'editable_sources';META=ROOT/'revision_workspace/integration/figures';records=[]
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':11,'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False,'axes.labelcolor':'#26313e','text.color':'#26313e','xtick.color':'#26313e','ytick.color':'#26313e'})
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(fig,name,sources,note):
 if sys.argv[1:] and name not in sys.argv[1:]:plt.close(fig);return
 for ext,p in [('pdf',OUT/(name+'.pdf')),('svg',EDIT/(name+'.svg')),('png',META/(name+'.png'))]:fig.savefig(p,dpi=400,bbox_inches='tight',facecolor='white')
 records.append({'figure':name,'pdf':str((OUT/(name+'.pdf')).relative_to(ROOT)),'svg':str((EDIT/(name+'.svg')).relative_to(ROOT)),'source_files':[{'path':str(Path(p).relative_to(ROOT)),'sha256':sha(p)} for p in sources],'note':note});plt.close(fig)
# Figure 1: a vector-native schematic tied to the actual code and configurations.
fig=plt.figure(figsize=(13,10));ax=fig.add_axes([0,0,1,1]);ax.set_xlim(0,13);ax.set_ylim(0,10);ax.axis('off')
def box(x,y,w,h,text,fc='#eef3f7',edge='#6f879b',size=11):
 ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.06,rounding_size=0.08',facecolor=fc,edgecolor=edge,linewidth=1));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size)
def arrow(x1,y1,x2,y2):ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle='-|>',mutation_scale=12,color='#556b7b',linewidth=1.2))
def title(x,y,label,text):ax.text(x,y,label,weight='bold',fontsize=17,va='top');ax.text(x+.38,y-.02,text,weight='bold',fontsize=12,va='top')
title(.15,9.75,'A','MRI and fixed text conditions')
box(.35,7.85,1.55,.85,'T1-weighted\nMRI',fc='#f0f0f0');box(2.35,8.75,3.25,.7,'Patient prompt: 8 fields',size=10.5);box(2.35,7.6,3.25,.7,'Target-tracer prompt\nFDG or AV45',size=10.5);box(6.2,7.95,2.45,1.15,'Frozen BiomedCLIP\ntext encoder',fc='#e0ecf4');arrow(5.7,9.1,6.15,8.8);arrow(5.7,7.95,6.15,8.25);box(9.35,8,3.1,1.1,'Two-token context\n[patient, tracer]\n2 × 512',fc='#e7f1ea');arrow(8.7,8.55,9.3,8.55)
ax.text(2.35,7.24,'Age, sex, weight, CDR, MMSE, GDS, FAQ, NPI-Q\nClinical scores include diagnosis-conditioned fills.',fontsize=9.5,va='top')
title(.15,6.65,'B','Affine tracer adaptation (separate configuration / analysis)')
box(.35,5.15,2.35,.9,'Frozen text and PET\nfeatures (512-D)',size=10.5);box(3.4,5.15,2.4,.9,'Two affine adapters\nFDG: α₁, α₂\nAV45: β₁, β₂',fc='#fff0dc',size=10.5);box(6.5,5.15,2.75,.9,'Text–PET alignment\n+ soft similarity target\nτ = 0.82',fc='#fff0dc',size=10.5);box(9.95,5.15,2.4,.9,'Fixed adapted\ntracer vectors',size=10.5);arrow(2.8,5.6,3.35,5.6);arrow(5.9,5.6,6.45,5.6);arrow(9.35,5.6,9.9,5.6)
ax.text(.35,4.88,'BiomedCLIP weights stay frozen. Reconstructed Full uses raw tracer vectors; adapter results do not establish its generation benefit.',fontsize=9.5)
title(.15,4.45,'C','Shared tracer-conditioned 3D rectified flow')
for i,(w,c) in enumerate(zip([1.5,1.75,1.75,2.0],[32,64,64,128])):
 x=.4+i*2.05;box(x,3.1,w,.68,f'U-Net level {i+1}\n{c} channels',fc='#e1edf4',size=10); 
 if i<3:arrow(x+w+.05,3.44,x+2.0,3.44)
box(9.1,3.1,3.2,.68,'Cross-attention at deepest level\ncontext dimension = 512',fc='#e7f1ea',size=9.7);arrow(8.6,3.44,9.05,3.44)
ax.text(.4,2.78,'Train on available FDG / AV45 targets only; λF = λA = 1. Timesteps become t = 0 from epoch 140.',fontsize=9.5)
title(.15,2.37,'D','Learned one-step inference')
box(.4,1.25,1.5,.7,'MRI x₀',fc='#f0f0f0');box(2.65,1.25,3.5,.7,'Tracer-conditioned velocity\nVθ(x₀, c, 0)',size=10.5);box(6.9,1.25,2.45,.7,'Residual addition\nx₀ + velocity',fc='#fff0dc',size=10.5);box(10.05,1.25,2.25,.7,'Clip to [0,1]\nOne tracer / pass',size=10.5);arrow(2,1.6,2.6,1.6);arrow(6.25,1.6,6.85,1.6);arrow(9.45,1.6,10,1.6)
ax.text(.4,.98,'A learned endpoint approximation, not exact ODE integration. Repeat with the other tracer condition to obtain the second PET estimate.',fontsize=9.5)
title(.15,.72,'E','Evaluation streams')
for x,w,t in [(.5,3.6,'Image quality: two-fold OOF'),(4.65,3.3,'Historical regional uptake'),(8.5,3.7,'Cross-sectional classification: 3-fold')]:box(x,.09,w,.36,t,fc='white',size=9.5)
save(fig,'figure_1',[ROOT/'experiments/original_author_reproduction/run.py',ROOT/'reports/revision_evidence_night_20261102/G1/REPORT.md'],'New schematic; separate affine-adapter analysis and reconstructed raw-tracer Full. No historical classification numbers embedded.')
# Figure 5: aligned points and SD intervals, with all 9 completed input conditions.
base=ROOT/'reports/revision_evidence_night_20261102/G5';a=pd.read_csv(base/'existing_imaging_bootstrap_metrics.csv');b=pd.read_csv(base/'clinical_summary.csv');tasks=['ad_cn','mci_cn','emci_lmci'];tnames=['A  AD vs CN (N=470)','B  EMCI+LMCI vs CN (N=741)','C  EMCI vs LMCI (N=436)'];conds=['mri','mri_real_fdg','mri_syn_fdg','mri_real_av45','mri_syn_av45','mri_real_both','mri_syn_both','clinical','mri_clinical'];names=['MRI','MRI + Real FDG','MRI + Syn FDG','MRI + Real AV45','MRI + Syn AV45','MRI + Real both','MRI + Syn both','Clinical-only','MRI + Clinical'];metrics=['ACC','AUC','SEN','SPE','balanced_ACC'];mnames=['ACC','AUC','SEN','SPE','Balanced ACC'];colors=['#59636e','#246a9a','#ce6a27','#246a9a','#ce6a27','#246a9a','#ce6a27','#38794e','#7255a5'];marks=['s','o','D','o','D','o','D','^','^'];binding=[]
fig,axs=plt.subplots(3,5,figsize=(10.5,13.4),sharex=True,sharey=True);fig.subplots_adjust(left=.20,right=.985,top=.95,bottom=.06,wspace=.12,hspace=.28)
for ti,(task,ttitle) in enumerate(zip(tasks,tnames)):
 for mi,(metric,mname) in enumerate(zip(metrics,mnames)):
  ax=axs[ti,mi]
  for ci,(cond,name) in enumerate(zip(conds,names)):
   if ci<7:
    r=a[(a.task==task)&(a.condition==cond)].iloc[0];mean=r[metric+'_point_pct'];sd=r[metric+'_original_fold_sd_pp'];n=int(r.n_subjects)
   else:
    r=b[(b.task==task)&(b.condition==cond)&(b.metric==metric)].iloc[0];mean=100*r['mean'];sd=100*r.sample_sd;n=int(r.n_subjects)
   ax.errorbar(mean,ci,xerr=sd,fmt=marks[ci],color=colors[ci],markersize=5,capsize=2,elinewidth=1.2)
   binding.append(dict(task=task,condition=cond,metric=metric,n=n,mean_percent=mean,sample_sd_percentage_points=sd))
  ax.set_xlim(-3,103);ax.set_xticks([0,50,100]);ax.grid(axis='x',color='#e3e6e9',linewidth=.6);ax.set_axisbelow(True);ax.tick_params(labelsize=9);ax.set_title(mname,fontsize=11,pad=8)
  if mi==0:ax.set_yticks(range(9),names,fontsize=10)
  else:ax.tick_params(axis='y',left=False,labelleft=False)
  if ti==2:ax.set_xlabel('Percent',fontsize=10)
  ax.invert_yaxis() if ti==0 and mi==0 else None
 # Row title is aligned above the left edge of all metrics, not a data annotation.
 pos=axs[ti,0].get_position();fig.text(.035,pos.y1+.025,ttitle,weight='bold',fontsize=13)
fig.text(.20,.015,'Points: equally weighted 3-fold means. Error bars: sample SD across folds (percentage points).',fontsize=10)
pd.DataFrame(binding).to_csv(META/'figure_5_plot_data.csv',index=False)
assert len(binding)==135
save(fig,'figure_5',[base/'existing_imaging_bootstrap_metrics.csv',base/'clinical_summary.csv'],'9 input conditions × 3 tasks × 5 metrics; points and fold sample SD, not confidence intervals. No PET-only configurations invented.')
previous=json.loads((META/'primary_figure_manifest.json').read_text()) if (META/'primary_figure_manifest.json').exists() else []
records=[x for x in previous if x['figure'] not in {n['figure'] for n in records}]+records
(META/'primary_figure_manifest.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('Built native vector figures', [x['figure'] for x in records])
