"""Recreate regional figures from the author-designated shuijin CSV family only.
No new inferential statistics, cohort changes, outlier trimming or imputation.
"""
from pathlib import Path
import json,hashlib,re,sys,textwrap
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'manuscript/figures';EDIT=OUT/'editable_sources';META=ROOT/'revision_workspace/integration/figures'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':12,'pdf.fonttype':42,'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
audit=pd.read_csv(ROOT/'reports/r2_8_original_roi_stats/input_audit.csv');overall=pd.read_csv(ROOT/'reports/r2_8_original_roi_stats/supplementary_tables/overall_regional_statistics.csv');effect=pd.read_csv(ROOT/'reports/r3_5_effect_size/figure4_effect_sizes.csv');qstats=pd.read_csv(ROOT/'reports/r2_9_figure4_fdr/all_392_student_fdr.csv');data={};receipt=[];figures=[]
for _,r in audit.iterrows():
 p=Path(r.input_file);assert '/shuijin/statistics_of_regions_' in str(p),p
 digest=hashlib.sha256(p.read_bytes()).hexdigest();assert digest==r.sha256,(p,digest,r.sha256)
 d=pd.read_csv(p);real='real_'+r.tracer.lower()+'_mean';syn='syn_'+r.tracer.lower()+'_mean'
 d[real]=pd.to_numeric(d[real],errors='coerce');d[syn]=pd.to_numeric(d[syn],errors='coerce')
 good=np.isfinite(d[real])&np.isfinite(d[syn]);v=d.loc[good].copy();assert len(d)==r.raw_rows and len(v)==r.valid_pairs and v.subject.notna().all() and v.subject.is_unique
 v=v.rename(columns={real:'real',syn:'syn'});data[(r.tracer,int(r.roi_id))]=v
 receipt.append({'tracer':r.tracer,'roi_id':int(r.roi_id),'path':str(p.relative_to(ROOT)),'sha256':digest,'raw_rows':len(d),'valid_pairs':len(v),'excluded_nonfinite':int((~good).sum()),'outside_0_1_retained':int(((v['real']<0)|(v['real']>1)|(v['syn']<0)|(v['syn']>1)).sum())})
assert len(data)==196
digests={(x['tracer'],x['roi_id']):x['sha256'] for x in receipt}
assert all(r.source_sha256==digests[(r.tracer,int(r.roi_id))] for _,r in qstats.iterrows()),'q-value source identity mismatch'
names={(r.Tracer,int(r['ROI ID'])):r['ROI anatomical name'] for _,r in overall.iterrows()}
substitutions={'rostralanteriorcingulate':'rostral ant. cingulate','caudalanteriorcingulate':'caudal ant. cingulate','rostralmiddlefrontal':'rostral middle frontal','caudalmiddlefrontal':'caudal middle frontal','lateralorbitofrontal':'lateral orbitofrontal','medialorbitofrontal':'medial orbitofrontal','isthmuscingulate':'isthmus cingulate','posteriorcingulate':'posterior cingulate','inferiortemporal':'inferior temporal','middletemporal':'middle temporal','superiortemporal':'superior temporal','transversetemporal':'transverse temporal','superiorfrontal':'superior frontal','frontalpole':'frontal pole','temporalpole':'temporal pole','parahippocampal':'parahippocampal','parsopercularis':'pars opercularis','parsorbitalis':'pars orbitalis','parstriangularis':'pars triangularis','lateraloccipital':'lateral occipital','superiorparietal':'superior parietal','inferiorparietal':'inferior parietal','Cerebellum-White-Matter':'cerebellum WM','Cerebral-White-Matter':'cerebral WM','Cerebellum-Cortex':'cerebellum cortex','VentralDC':'ventral DC','Cerebral-Cortex':'cerebral cortex'}
def label(tracer,roi):
 t=names[(tracer,int(roi))].replace('ctx-lh-','L ').replace('ctx-rh-','R ').replace('Left-','L ').replace('Right-','R ')
 for a,b in substitutions.items():t=t.replace(a,b)
 return t.replace('-',' ')
def wrapped(t,width=13):return '\n'.join(textwrap.wrap(t,width=width,break_long_words=False,break_on_hyphens=False))
def half(ax,values,pos,side,color,hatch=False,width=.85,horizontal=False):
 vals=np.asarray(values);assert len(vals)>1 and np.isfinite(vals).all()
 if np.std(vals)<1e-12:
  if horizontal:ax.plot([vals[0],vals[0]],[pos-.12,pos+.12],color=color,lw=1)
  else:ax.plot([pos-.12,pos+.12],[vals[0],vals[0]],color=color,lw=1)
  return
 parts=ax.violinplot([vals],positions=[pos],widths=width,vert=not horizontal,showmeans=False,showmedians=False,showextrema=False,points=80)
 body=parts['bodies'][0];xy=body.get_paths()[0].vertices;dimension=1 if horizontal else 0
 if side=='left':xy[:,dimension]=np.minimum(xy[:,dimension],pos)
 else:xy[:,dimension]=np.maximum(xy[:,dimension],pos)
 body.set_facecolor('white' if hatch else color);body.set_edgecolor(color);body.set_linewidth(.6);body.set_alpha(1 if hatch else .75)
 if hatch:body.set_hatch('////')
def stars(q):
 if q<1e-4:return '****'
 if q<1e-3:return '***'
 if q<1e-2:return '**'
 if q<.05:return '*'
 return 'ns'
def bracket(ax,x1,x2,y,text,ls='-'):
 ax.plot([x1,x1,x2,x2],[y-.025,y,y,y-.025],color='#555',lw=.7,linestyle=ls);ax.text((x1+x2)/2,y+.012,text,ha='center',va='bottom',fontsize=10)
def compare(ax,tracer,ids,letter='',title='',horizontal=False):
 for i,roi in enumerate(ids):
  d=data[(tracer,int(roi))];half(ax,d['real'],i,'left','#287eb5',horizontal=horizontal);half(ax,d['syn'],i,'right','#d87830',horizontal=horizontal)
  if not horizontal:
   q=overall[(overall.Tracer==tracer)&(overall['ROI ID']==roi)].iloc[0]['BH-FDR q'];ax.text(i,1.04,stars(q),ha='center',fontsize=10)
 if horizontal:
  ax.set_yticks(range(len(ids)),[label(tracer,i) for i in ids],fontsize=9.5);ax.set_xlim(-.025,1.025);ax.set_xticks([0,.5,1]);ax.invert_yaxis();ax.grid(axis='x',color='#e3e5e7',lw=.5);ax.set_xlabel('Normalized uptake (a.u.)',fontsize=10)
 else:
  ax.set_xticks(range(len(ids)),[wrapped(label(tracer,i),10 if len(ids)==8 else 14) for i in ids],rotation=0,ha='center',fontsize=10.5);ax.set_ylim(-.02,1.14);ax.set_ylabel('Normalized uptake (a.u.)',fontsize=11)
 if title:ax.set_title(title,fontsize=12,loc='left',pad=12)
 if letter:ax.text(-.11,1.07,letter,transform=ax.transAxes,weight='bold',fontsize=17)
def disease(ax,tracer,ids,letter='',title=''):
 for i,roi in enumerate(ids):
  d=data[(tracer,int(roi))]
  for group,offset,col in [('CN',-.55,'#2c9164'),('AD',.55,'#cc4d69')]:
   v=d[d['Research Group']==group];half(ax,v['real'],i*3+offset,'left',col);half(ax,v['syn'],i*3+offset,'right',col,hatch=True)
  q=[]
  for modality in ['real','syn']:
   r=qstats[(qstats.tracer==tracer)&(qstats.roi_id==roi)&(qstats.modality==modality)].iloc[0]
   assert len(d[d['Research Group']=='AD'])==r.N_AD and len(d[d['Research Group']=='CN'])==r.N_CN
   q.append(float(r.bh_q))
  bracket(ax,i*3-.55,i*3+.55,1.015,stars(q[0]));bracket(ax,i*3-.55,i*3+.55,1.11,stars(q[1]),'--')
 ax.set_xticks(np.arange(len(ids))*3,[wrapped(label(tracer,i),10 if len(ids)==8 else 14) for i in ids],rotation=0,ha='center',fontsize=10.5);ax.set_ylim(-.02,1.2);ax.set_ylabel('Normalized uptake (a.u.)',fontsize=11)
 if title:ax.set_title(title,loc='left',fontsize=12,pad=12)
 if letter:ax.text(-.11,1.07,letter,transform=ax.transAxes,weight='bold',fontsize=17)

def disease_horizontal(ax,tracer,ids,letter='',title=''):
 for i,roi in enumerate(ids):
  d=data[(tracer,int(roi))]
  for group,offset,col in [('CN',-.21,'#2c9164'),('AD',.21,'#cc4d69')]:
   v=d[d['Research Group']==group];half(ax,v['real'],i+offset,'left',col,width=.34,horizontal=True);half(ax,v['syn'],i+offset,'right',col,hatch=True,width=.34,horizontal=True)
  for modality,x,ls in [('real',1.04,'-'),('syn',1.20,'--')]:
   r=qstats[(qstats.tracer==tracer)&(qstats.roi_id==roi)&(qstats.modality==modality)].iloc[0]
   assert len(d[d['Research Group']=='AD'])==r.N_AD and len(d[d['Research Group']=='CN'])==r.N_CN
   ax.plot([x-.01,x,x,x-.01],[i-.21,i-.21,i+.21,i+.21],color='#666',lw=.7,linestyle=ls)
   ax.text(x+.015,i,stars(float(r.bh_q)),ha='left',va='center',fontsize=9)
 ax.set_yticks(range(len(ids)),[wrapped(label(tracer,i),20) for i in ids],fontsize=10.5)
 ax.set_ylim(-.6,len(ids)-.4);ax.invert_yaxis();ax.set_xlim(-.025,1.36);ax.set_xticks([0,.5,1]);ax.set_xlabel('Normalized uptake (a.u.)',fontsize=11);ax.grid(axis='x',color='#e3e5e7',lw=.5)
 ax.set_title(title,loc='left',fontsize=12,pad=22)
 ax.text(1.04,-.58,'Real',fontsize=8.5,ha='left');ax.text(1.20,-.58,'Syn',fontsize=8.5,ha='left')
 ax.text(-.45,1.08,letter,transform=ax.transAxes,weight='bold',fontsize=17)

def save(fig,name,note):
 if sys.argv[1:] and name not in sys.argv[1:]:plt.close(fig);return
 for ext,p in [('pdf',OUT/(name+'.pdf')),('svg',EDIT/(name+'.svg')),('png',META/(name+'.png'))]:fig.savefig(p,dpi=400,bbox_inches='tight',facecolor='white')
 plt.close(fig);figures.append({'figure':name,'note':note,'pdf':str((OUT/(name+'.pdf')).relative_to(ROOT)),'svg':str((EDIT/(name+'.svg')).relative_to(ROOT))})
primary=[1025,2025,1032,2032,1033,2033,1028,2028]
fig,axs=plt.subplots(3,2,figsize=(11.5,12.6));fig.subplots_adjust(left=.16,right=.985,bottom=.09,top=.94,wspace=.88,hspace=.44)
for j,t in enumerate(['AV45','FDG']):
 ax=axs[0,j];compare(ax,t,primary,'',t+' real–synthetic agreement',horizontal=True);ax.set_xlim(-.025,1.25)
 for i,roi in enumerate(primary):
  q=overall[(overall.Tracer==t)&(overall['ROI ID']==roi)].iloc[0]['BH-FDR q'];ax.text(1.10,i,stars(float(q)),ha='center',va='center',fontsize=10)
 ax.text(1.10,-.65,'Overall q',ha='center',fontsize=8.5);ax.set_title(t+' real–synthetic agreement',loc='left',fontsize=12,pad=22);ax.text(-.45,1.08,'AB'[j],transform=ax.transAxes,weight='bold',fontsize=17)
for idx,panel in enumerate('CDEF'):
 r=effect[effect.panel==panel].sort_values('panel_order');t=r.tracer.iloc[0];disease_horizontal(axs[1+idx//2,idx%2],t,r.roi_id.tolist(),panel,t+(' AD–CN selected differences' if panel in 'CD' else ' AD–CN nonsignificant regions'))
handles=[Patch(facecolor='#287eb5',label='Real (A,B)'),Patch(facecolor='#d87830',label='Synthetic (A,B)'),Patch(facecolor='#2c9164',label='CN (C–F)'),Patch(facecolor='#cc4d69',label='AD (C–F)'),Patch(facecolor='white',edgecolor='#555',hatch='////',label='Synthetic lower half (C–F)')]
fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.52,.006),ncol=3,frameon=False,fontsize=10)
save(fig,'figure_4','Recreated from designated shuijin CSVs; six-panel organization and selected ROI identities retained; horizontal orientation replaces historical layout; normalized uptake units and recomputed BH-FDR annotations. Not claimed identical to historical drawing files.')
# Remaining pooled ROIs: fixed sorted atlas IDs, excluding the eight Figure4A/B primary ROIs.
for tracer,start_num in [('AV45',1),('FDG',3)]:
 ids=sorted(roi for tr,roi in data if tr==tracer and roi not in primary);assert len(ids)==90
 for part in [0,1]:
  chosen=ids[part*45:(part+1)*45];fig,axs=plt.subplots(1,2,figsize=(11.4,11),gridspec_kw={'width_ratios':[1,1]});fig.subplots_adjust(left=.21,right=.98,top=.93,bottom=.07,wspace=.95)
  for ax,sub in zip(axs,[chosen[:23],chosen[23:]]):compare(ax,tracer,sub,horizontal=True)
  fig.suptitle(f'{tracer}: remaining regional real–synthetic uptake (part {part+1}/2)',fontsize=14,y=.985)
  fig.legend(handles=[Patch(facecolor='#287eb5',label='Real'),Patch(facecolor='#d87830',label='Synthetic')],loc='lower center',ncol=2,frameon=False,fontsize=11)
  save(fig,f'supplementary_figure_{start_num+part}',f'{tracer}; 45 of 90 remaining ROIs; pooled available subjects; finite-pair filter identical to source statistics. Two small negative synthetic intensities in ROI2019 retained when applicable.')
# The complementary canonical disease regions match the inspected historical S5/S6 panels.
for tracer,ids,num in [('AV45',[2025,2009,2015,2030,2034],5),('FDG',[2031],6)]:
 fig,ax=plt.subplots(figsize=(9.4 if len(ids)>1 else 4.8,5.8));fig.subplots_adjust(left=.12 if len(ids)>1 else .19,right=.98,bottom=.32,top=.86);disease(ax,tracer,ids,title=tracer+' AD–CN complementary atlas regions')
 fig.legend(handles=[Patch(facecolor='#2c9164',label='CN'),Patch(facecolor='#cc4d69',label='AD'),Patch(facecolor='white',edgecolor='#555',hatch='////',label='Synthetic half')],loc='lower center',ncol=3,frameon=False,fontsize=10)
 save(fig,f'supplementary_figure_{num}',f'{tracer}; canonical disease-region complement of Figure4C/D; real/synthetic AD–CN annotations from the existing 98-ROI-per-family BH-FDR results.')
previous=json.loads((META/'roi_figure_manifest.json').read_text())['figures'] if (META/'roi_figure_manifest.json').exists() else []
figures=[x for x in previous if x['figure'] not in {n['figure'] for n in figures}]+figures
(META/'roi_figure_manifest.json').write_text(json.dumps({'input_family':'user-designated shuijin only; abandon directories not read','inputs':receipt,'figures':figures,'statistics_recomputed':False,'outliers_trimmed':False,'imputation_performed':False,'hashes_match_existing_input_audit':True},ensure_ascii=False,indent=2)+'\n')
print('Recreated ROI figures',len(figures),'from',len(data),'verified source CSVs',flush=True)
