from pathlib import Path
import json,hashlib,importlib.util
import numpy as np,pandas as pd,torch,nibabel as nib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'reports/revision_evidence_night_20261102';DEST=OUT/'G3_cases';DEST.mkdir(exist_ok=True)
metrics=pd.read_csv(ROOT/'reports/original_author_reproduction_20261020/oof_summary/per_subject_metrics.csv',float_precision='round_trip');metrics=metrics[metrics.epoch==165]
manifest=DEST/'selection_manifest_internal.csv'
if not manifest.exists():
    selections=[]
    for tracer in ('fdg','av45'):
        s=metrics[metrics.tracer==tracer].sort_values(['ssim','ptid']).reset_index(drop=True)
        for rule,q in [('median',.5),('p10',.1),('worst',0.)]:
            target=float(s.ssim.quantile(q));j=s.assign(distance=abs(s.ssim-target)).sort_values(['distance','ptid']).iloc[0]
            selections.append(dict(**j.drop('distance').to_dict(),selection=rule,quantile=q,target_ssim=target,ranking_N=len(s),selection_rule='nearest linear empirical quantile; tie by PTID; fixed before image loading'))
    pd.DataFrame(selections).to_csv(manifest,index=False)
    (DEST/'selection_frozen.json').write_text(json.dumps(dict(sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),images_viewed_before_selection=False,protocol=str(OUT/'code/PROTOCOL.md')),indent=2))
assert hashlib.sha256(manifest.read_bytes()).hexdigest()==json.loads((DEST/'selection_frozen.json').read_text())['sha256']
selected=pd.read_csv(manifest);idx=pd.read_csv(ROOT/'reports/r3_11_brain_mask_metrics/run_20261102/input_index.csv');idx=idx[idx.model=='Full']
cohort={r['name']:r for r in json.loads((ROOT/'reports/original_author_reproduction_20261020/cohort.json').read_text())}
cache_root=ROOT/'results/cache/original_author_reproduction/v1_3f362cdb3ebe8a94_bbcd413100d8ece3_nfs_backup'
records=[]
for row in selected.itertuples():
    hit=idx[(idx.ptid==row.ptid)&(idx.tracer==row.tracer)]
    if len(hit):cache=Path(hit.iloc[0].target_cache)
    else:
        from monai.data.utils import pickle_hashing
        cache=cache_root/(pickle_hashing(cohort[row.ptid]).decode()+'.pt')
    data=torch.load(cache,map_location='cpu',weights_only=False);assert data['name']==row.ptid
    p=Path(row.prediction);assert hashlib.sha256(p.read_bytes()).hexdigest()==row.prediction_sha256
    pred=np.asarray(nib.load(str(p)).dataobj,dtype=np.float32)
    real=np.asarray(data[row.tracer]).squeeze().astype(np.float32);mri=np.asarray(data['mri']).squeeze().astype(np.float32)
    assert pred.shape==real.shape==mri.shape==(160,192,160)
    assert all(np.isfinite(v).all() for v in (pred,real,mri));error=np.abs(pred-real)
    fig,axes=plt.subplots(3,4,figsize=(10,8.7));cmaps=['gray','magma','magma','inferno'];arrays=[mri,real,pred,error]
    for ai,axrow in enumerate(axes):
        for col,(ax,arr) in enumerate(zip(axrow,arrays)):
            sl=np.take(arr,arr.shape[ai]//2,axis=ai)
            h=ax.imshow(np.rot90(sl),cmap=cmaps[col],vmin=0,vmax=1,interpolation='nearest');ax.set_xticks([]);ax.set_yticks([])
            if ai==0:ax.set_title(['MRI reference','Real PET','Synthetic PET','Absolute error'][col],fontsize=10)
            if col==0:ax.set_ylabel(f'Grid axis {ai}; index {arr.shape[ai]//2}',fontsize=8)
    fig.suptitle(f'{row.tracer.upper()} | {row.selection} SSIM case | fold {row.fold} | saved SSIM {row.ssim:.4f}',fontsize=12)
    cax=fig.add_axes([.3,.09,.4,.018]);cb=fig.colorbar(h,cax=cax,orientation='horizontal');cb.set_label('Normalized intensity / absolute error (arbitrary units; all panels 0–1)',fontsize=8,labelpad=2)
    note='Central slices in the frozen MRI-anchored array grid; no anatomical left/right inference from NIfTI affine.'
    if row.selection=='worst':note+='\nPre-existing MRI/mask QC failure; retained in whole-volume ranking, excluded from masked statistics.'
    fig.text(.5,.012,note,ha='center',fontsize=7.5)
    fig.subplots_adjust(top=.92,bottom=.16,wspace=.03,hspace=.04)
    f=OUT/f'figures/G3_case_{row.tracer}_{row.selection}.png';fig.savefig(f,dpi=200);plt.close(fig)
    records.append(dict(ptid=row.ptid,tracer=row.tracer,selection=row.selection,fold=row.fold,ssim=row.ssim,target_cache=str(cache),prediction=str(p),prediction_sha256=row.prediction_sha256,real_array_sha256=hashlib.sha256(real.tobytes()).hexdigest(),figure=str(f.relative_to(OUT)),grid='160,192,160',pet_scale='0,1',error_scale='0,1',qc_scope='Full whole-volume eligible set; no additional exclusions'))
    print('COMPLETE',row.tracer,row.selection,flush=True)
pd.DataFrame(records).to_csv(DEST/'render_manifest_internal.csv',index=False)
