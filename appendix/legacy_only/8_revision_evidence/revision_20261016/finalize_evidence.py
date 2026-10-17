"""Finalize verified, image-derived evidence and scoped review deliverables."""
import hashlib
import json
import platform
import subprocess
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.stats.multitest import multipletests

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
FINAL=OUT/'image_derived'


def adjusted_analysis():
    clinical=pd.read_csv(OUT/'clinical_observed_subjects.csv').set_index('Subject ID')
    rows=[]
    for t in ['av45','fdg']:
        for p in sorted((FINAL/f'paired_regions_{t}').glob('*.csv')):
            r=int(float(p.stem.removeprefix('region_')))
            d=pd.read_csv(p).set_index('subject').join(clinical[['Age','Sex','Weight']])
            d=d[d['Research Group'].isin(['AD','CN'])]
            d['AD']=(d['Research Group']=='AD').astype(float)
            d['male']=(d.Sex=='M').astype(float)
            for covars in [['AD','Age','male'],['AD','Age','male','Weight']]:
                X=sm.add_constant(d[covars].astype(float))
                for outcome in ['real','syn','syn_minus_real']:
                    y=d[f'{outcome}_{t}_mean'] if outcome!='syn_minus_real' else d[f'syn_{t}_mean']-d[f'real_{t}_mean']
                    fit=sm.OLS(y,X,missing='drop').fit(cov_type='HC3')
                    ci=fit.conf_int().loc['AD']
                    rows.append(dict(tracer=t,region=r,outcome=outcome,model='age_sex' if len(covars)==3 else 'age_sex_positive_weight',
                                     n=int(fit.nobs),ad_beta=fit.params.AD,ad_se=fit.bse.AD,ad_p=fit.pvalues.AD,
                                     ad_ci_low=ci.iloc[0],ad_ci_high=ci.iloc[1]))
    q=pd.DataFrame(rows);q['ad_q_bh196']=np.nan
    for _,ix in q.groupby(['outcome','model']).groups.items():q.loc[ix,'ad_q_bh196']=multipletests(q.loc[ix,'ad_p'],method='fdr_bh')[1]
    q.to_csv(FINAL/'regional_AD_CN_adjusted_observed_demographics.csv',index=False)
    preliminary=FINAL/'regional_AD_CN_adjusted_HC3.csv'
    if preliminary.exists():preliminary.rename(FINAL/'diagnostic_HC3_unfiltered_weight.csv')
    return q


def table():
    s=pd.read_csv(OUT/'table_s1_observed_continuous.csv');sex=pd.read_csv(OUT/'table_s1_observed_sex_counts.csv').set_index('Research Group')
    groups=['CN','EMCI','LMCI','MCI','AD']
    lines=['% Revision candidate only; original manuscript untouched.',
           r'\begin{tabular}{lccccccl}',r'\hline',
           r'Variable & CN & EMCI & LMCI & MCI & AD & P & Test \\',r'\hline']
    lines.append('n & '+' & '.join(str(int(sex.loc[g].sum())) for g in groups)+r' & -- & -- \\')
    for _,r in s.iterrows():
        cells=[]
        for g in groups:
            n=int(r[g+'_n'])
            cells.append(f"{r[g+'_mean']:.2f} $\\pm$ {r[g+'_sd']:.2f} ({n})" if n>1 else (f"{r[g+'_mean']:.2f} ({n})" if n else '-- (0)'))
        pv=f'{r.anova_p:.6g}' if pd.notna(r.anova_p) else 'NA'
        name=str(r.variable).replace('Weight','Weight (source units)')
        lines.append(name+' & '+' & '.join(cells)+f' & {pv} & '+('ANOVA' if pd.notna(r.anova_p) else 'Unavailable')+r' \\')
    lines.append('Sex (M/F) & '+' & '.join(f'{int(sex.loc[g,"M"])}/{int(sex.loc[g,"F"])}' for g in groups)+r' & $4.95411\times10^{-7}$ & Chi-square \\')
    lines.extend([r'\hline',r'\end{tabular}',
                  '% Parentheses show observed n. Zero weight (65 records) treated as missing.',
                  '% Exact demographic anchor to raw clinical export; no visit-date linkage available.',
                  '% Cognitive five-group tests unavailable: empty or singleton groups; no imputation.',
                  '% Weight source units need a data dictionary before relabelling kg.'])
    (OUT/'table_s1_observed_candidate.tex').write_text('\n'.join(lines)+'\n')


def plots():
    # Fixed anatomical examples, selected before inspecting the corrected results.
    regions=[17,1010,1025]
    names={17:'Left hippocampus',1010:'Left isthmus cingulate',1025:'Left precuneus'}
    fig,axes=plt.subplots(2,3,figsize=(12,7),layout='constrained')
    for i,t in enumerate(['av45','fdg']):
        for j,r in enumerate(regions):
            d=pd.read_csv(FINAL/f'paired_regions_{t}/region_{r}.0.csv')
            x=d[f'real_{t}_mean'].to_numpy();y=d[f'syn_{t}_mean'].to_numpy()
            keep=np.isfinite(x)&np.isfinite(y);x,y=x[keep],y[keep];diff=y-x
            a=axes[i,j];a.scatter((x+y)/2,diff,s=4,alpha=.22,color='#146b8c',rasterized=True)
            bias=diff.mean();sd=diff.std(ddof=1)
            a.axhline(0,color='0.6',lw=.6)
            a.axhline(bias,color='#8a351f',lw=1,label=f'Bias {bias:.4f}')
            a.axhline(bias-1.96*sd,color='0.2',ls='--',lw=.8,label='95% limits of agreement')
            a.axhline(bias+1.96*sd,color='0.2',ls='--',lw=.8)
            a.set_title(f'{t.upper()} · {names[r]} · n={len(x)}',fontsize=10)
            a.set_xlabel('Mean of Real and Syn (normalized uptake)');a.set_ylabel('Syn − Real (normalized uptake)')
            a.legend(fontsize=7,loc='best',frameon=False)
    fig.suptitle('Retrospective agreement of saved Syn-PET and Real regional values',fontsize=13)
    fig.savefig(FINAL/'bland_altman_fixed_regions.png',dpi=180)
    fig.savefig(FINAL/'bland_altman_fixed_regions.pdf')
    plt.close(fig)


def manifest_and_checks():
    sources=pd.read_csv(OUT/'source_sha256.csv')
    checks=[]
    for _,r in sources.iterrows():
        p=Path(r.path);digest=hashlib.sha256(p.read_bytes()).hexdigest()
        checks.append(dict(path=str(p),unchanged=digest==r.sha256))
    assert all(x['unchanged'] for x in checks)
    pd.DataFrame(checks).to_csv(OUT/'historical_source_preservation_check.csv',index=False)
    extra=[]
    known=[ROOT/'ai_plan/审计报告1015.md',ROOT/'ai_plan/BMEF_Reviewer_Report_English.docx',
           ROOT/'5_data_splits/train_data_1856_first_part_165.json',
           ROOT/'5_data_splits/val_data_1_first_part_165.json',
           Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')/'train_data_with_description.json',
           Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')/'val_data_with_description.json',
           Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')/'filtered_subjects_filled.csv',
           Path('/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45')/'ADNI MRI and FDG and AV45 csv.csv',
           ROOT/'7_training_logs/training_loss_165epochs.csv']
    for folder in ['2_checkpoints/adapter_vectors','2_checkpoints/text_features']:
        known+=list((ROOT/folder).glob('*.pt'))
    for p in known:
        extra.append(dict(path=str(p),bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    pd.DataFrame(extra).to_csv(OUT/'additional_source_sha256.csv',index=False)
    split_receipt=json.loads((OUT/'final165_split_receipt.json').read_text())
    for k in ['train','val']:
        assert hashlib.sha256(Path(split_receipt[k]['path']).read_bytes()).hexdigest()==split_receipt[k]['sha256']
    # Validate key formulas against a different direct calculation, and invariants.
    from analyze_evidence import agreement
    a=np.array([.2,.3,.5,.9]);b=np.array([.22,.31,.49,.86]);icc,ccc=agreement(a,b)
    independent_ccc=2*np.cov(a,b,ddof=0)[0,1]/(np.var(a)+np.var(b)+(a.mean()-b.mean())**2)
    assert np.allclose(ccc,independent_ccc)
    assert np.allclose(agreement(a,a),[1,1])
    overall=pd.read_csv(FINAL/'regional_agreement_overall.csv');strata=pd.read_csv(FINAL/'regional_agreement_by_diagnosis.csv')
    assert len(overall)==196 and len(strata)==980
    assert np.allclose(overall.paired_q_global,multipletests(overall.paired_p,method='fdr_bh')[1])
    assert (overall.ba_loa_low<overall.bias_syn_minus_real).all() and (overall.ba_loa_high>overall.bias_syn_minus_real).all()
    (OUT/'validation_receipt.json').write_text(json.dumps(dict(
        repository_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        final165_train_subjects=1856,final165_validation_subjects=1,
        final165_not_in_training_subjects=['011_S_4105'],final165_unused_by_train_and_validation=0,
        recovered_split_source_hashes_unchanged=True,
        historical_sources_checked=len(checks),all_historical_hashes_unchanged=True,
        overall_tests=196,stratified_tests=980,independent_ccc_formula_pass=True,
        identical_inputs_icc_ccc_pass=True,global_fdr_recalculation_pass=True,
        no_generator_training=True,no_classifier_training=True,no_gpu_execution=True,
        original_csv_statistics_status='QUARANTINED: Syn column mismatches saved volumes',
        primary_region_results='image_derived; Real CSV columns plus all Syn ROI values re-extracted',
        limitation='Real image provenance checked on six cases only; not all Real volumes reprocessed. Final165 split supplied by user and verified externally; no embedded checkpoint manifest. Adapter usage unresolved.'),indent=2))


def report():
    for name in ['regional_agreement_overall.csv','regional_agreement_by_diagnosis.csv']:
        p=FINAL/name;v=pd.read_csv(p)
        v['validation_scope']='retrospective; final165 subjects in train or validation; not an untouched independent cohort'
        v.to_csv(p,index=False)
    receipt_path=FINAL/'extraction_receipt.json'
    receipt=json.loads(receipt_path.read_text())
    receipt['cohort']='retrospective; all1857 in final165 train(1856)/validation(1) manifests; no untouched cohort'
    receipt['final_cohort_receipt']='../final165_split_receipt.json'
    receipt_path.write_text(json.dumps(receipt,indent=2))
    matrix=[
        (1,'科学创新','可低成本解决','保留条件 RF/双 tracer 贡献；域适配的实际使用未绑定，不以概念图代替运行证据。','checkpoint_facts.json; source_extracts/'),
        (2,'临床动机','可低成本解决','保留成本/可及性动机；输入应写 MRI+患者临床文本，避免声称仅 MRI。','source_extracts/mri2pet _two trace_new-final.txt'),
        (3,'三折与两折不一致','需额外实验','旧 loader 作用域及 epoch 平均不构成有效三折；如实撤回旧协议结论，独立分类需重算。','CLASSIFICATION_AND_SENSITIVITY_PLAN.md'),
        (4,'预后夸大','可低成本解决','EMCI/LMCI 改为横断面阶段区分；不声称转换预测。','manuscript/BMEF_main.tex:158,340'),
        (5,'临床信息捷径','需额外实验','提供固定模型三条件敏感性及临床变量对照方案；尚未执行，不能声称已排除捷径。','CLASSIFICATION_AND_SENSITIVITY_PLAN.md'),
        (6,'subject/访视隔离','已解决（划分）；需额外实验（独立分类）','新提供的最终名单核实1856 train/1 CN val，互斥且覆盖1857人；无足够未训练二分类样本。','subject_membership_and_assets_enriched.csv; final165_split_receipt.json'),
        (7,'外部双示踪剂证据不完整','建议以局限性回应','仅可声称经身份核验的 AV45 外部结果；当前软链是 OASIS-1 MRI，419 人 OASIS-3 PET 未闭环。','METHODS_AND_PROVENANCE.md; REPORT'),
        (8,'非显著不能证明等效','已解决（收紧结论）','撤除 p>0.05→等效；报告 bias/CI/LoA；无合理边界不做 TOST。','image_derived/regional_agreement_overall.csv'),
        (9,'多重比较 family','已解决','196 总体、980 分层、392 AD/CN 原始 p 与 BH q 已保存；方法明确 family。','METHODS_AND_PROVENANCE.md'),
        (10,'PET 一致性与校准','已解决（描述性范围）','从真实 Syn 卷重提 98 区，报告 ICC/CCC/BA/校准；用 normalized uptake，不夸大为临床定量替代。','image_derived/'),
        (11,'分类不确定性','需额外实验','旧汇总不能补出有效 OOF CI；新协议逐 subject 概率、fold 结果和 paired subject bootstrap。','CLASSIFICATION_AND_SENSITIVITY_PLAN.md'),
        (12,'显著优效直接检验','可低成本解决或需额外实验','先删无支持的 significantly；若保留优效主张，需相同独立 subjects 的配对预测与直接检验。','CLASSIFICATION_AND_SENSITIVITY_PLAN.md'),
        (13,'exact one-step 术语','可低成本解决','改为 endpoint fine-tuning 后学习的一步近似；双 tracer 两次 forward，不称精确 ODE 积分。','checkpoint_facts.json; source_extracts/'),
        (14,'VLM/adapter 可复现细节','可低成本解决（仍有溯源缺口）','补 512 维、160 切片平均、prompt 与独立 adapter 优化；raw/adapted 运行分歧须声明。','checkpoint_facts.json; CLASSIFICATION_AND_SENSITIVITY_PLAN.md'),
        (15,'Eq.1 与 τ','建议以局限性回应','代码为 cos=0.82 软目标，不是 ≥τ 硬约束；无训练时 τ 消融，不声称已证明最优或稳健。','source_extracts/mri2pet _clip_pretrain -Copy1.txt'),
        (16,'人口学混杂','可低成本解决（部分）','完成 age/sex HC3 和正体重敏感性；真实临床评分缺失及 prompt 捷径仍限制因果解释。','image_derived/regional_AD_CN_adjusted_observed_demographics.csv; table_s1_observed_continuous.csv'),
        (17,'基线改造与公平性','建议以局限性回应','说明可验证的实现差异；未闭环同 split/调参预算，不把雷达图匹配视为公平性证明。','6_test_eval_results/baseline_radar_data/baseline_comparison_metrics.csv; REPORT'),
        (18,'效率实测','需额外实验','已核 generator 参数数；138 GPUh/完整日志未核实。只规划小型同硬件计时，不编造 FLOPs/显存。','checkpoint_facts.json; 7_training_logs/training_loss_165epochs.csv'),
        (19,'复现材料','可低成本解决','提供 commit、源哈希、逐人集合、命令、统计环境；注明最终名单由用户恢复，checkpoint 未内嵌 manifest。','source_sha256.csv; additional_source_sha256.csv; final165_split_receipt.json; METHODS_AND_PROVENANCE.md'),
        (20,'临床转化过强','可低成本解决','删除临床可操作/广泛筛查已成立等说法；限定为回顾性研究，前瞻和多中心验证待开展。','REPORT'),
    ]
    mat=pd.DataFrame(matrix,columns=['reviewer_number','original_topic','status','response_and_limit','evidence'])
    mat.to_csv(OUT/'reviewer_evidence_matrix_1_to_20.csv',index=False)
    md=['| 原编号 | 原始意见主题 | 状态 | 证据/处置 |','|---|---|---|---|']
    md += [f'| #{n} | {topic} | {status} | {response} |' for n,topic,status,response,_ in matrix]
    summ=json.loads((FINAL/'regional_summary.json').read_text())
    q=pd.read_csv(FINAL/'regional_agreement_overall.csv')
    for r in summ:
        ns=q.loc[q.tracer==r['tracer'],'n']
        r['paired_n_min']=int(ns.min());r['paired_n_max']=int(ns.max())
        r.pop('n',None)
    (FINAL/'regional_summary.json').write_text(json.dumps(summ,indent=2))
    stat=['| Tracer | n/ROI | MAE 中位数 | ICC(A,1) 中位数（范围） | CCC 中位数 | p<0.05 / 全196项BH q<0.05 |',
          '|---|---:|---:|---|---:|---|']
    for r in summ:
        ns=q.loc[q.tracer==r['tracer'],'n']
        stat.append(f"| {r['tracer'].upper()} | {ns.min()}–{ns.max()} | {r['mae_median']:.5f} | {r['icc_median']:.4f}（{r['icc_min']:.4f}–{r['icc_max']:.4f}） | {r['ccc_median']:.4f} | {r['paired_p_lt05']}/98；{r['paired_global_q_lt05']}/98 |")
    for t,d in q.groupby('tracer'):
        stat.append(f"\n{t.upper()}：98 区均值偏差范围 {d.bias_syn_minus_real.min():.5f} 至 {d.bias_syn_minus_real.max():.5f}；MAE 范围 {d.mae.min():.5f}–{d.mae.max():.5f}。完整每区 bias CI、ICC/CCC CI、LoA 和校准参数见总表。")
    tmpl=(OUT/'REPORT_TEMPLATE.md').read_text()
    (OUT/'REVISION_EVIDENCE_REPORT.md').write_text(tmpl.replace('{{REGIONAL_RESULTS}}','\n'.join(stat)).replace('{{REVIEW_MATRIX}}','\n'.join(md)))
    (OUT/'README.md').write_text('本轮交付入口：[Revision Evidence Report](REVISION_EVIDENCE_REPORT.md)。\n\n'
        '**最终区域统计仅使用 image_derived/。本目录根部 regional_* 为原 CSV 的诊断计算，不得用于论文；旧目录中无依据 TOST 同样不采用。**\n\n'
        '人口学使用 table_s1_observed_* 和 clinical_observed_*，不使用先前 filled 表的完整认知 P 值。\n\n'
        '分类/敏感性训练与 GPU 推理未执行，方案在 CLASSIFICATION_AND_SENSITIVITY_PLAN.md；所有新训练等待确认。\n')


def candidate_counts():
    m=pd.read_csv(OUT/'subject_membership_and_assets_enriched.csv')
    complete=m.fdg_generated_available&m.av45_generated_available&m.processed_mri_exists&m.registered_fdg_exists&m.registered_av45_exists
    rows=[]
    for scenario,mask in [('all_complete',complete),('outside_recovered539_NOT_certified',complete&m.candidate_outside_recovered539),
                          ('outside_fixed800_NOT_certified',complete&m.candidate_outside_fixed800),
                          ('final165_validation_member',complete&m.final165_val_manifest_member),
                          ('not_in_final165_training_manifest',complete&m.not_in_final165_training_manifest),
                          ('untouched_by_final165_train_or_validation',complete&m.untouched_by_final165_train_or_validation)]:
        for task,groups in [('AD_CN',['AD','CN']),('MCI_legacyEarlyLate_CN',['EMCI','LMCI','CN']),
                            ('EMCI_LMCI',['EMCI','LMCI']),('MCI_all_subtypes_CN',['EMCI','LMCI','MCI','CN'])]:
            d=m[mask&m['Research Group'].isin(groups)]
            rows.append(dict(scenario=scenario,task=task,n=len(d),labels=json.dumps(d['Research Group'].value_counts().to_dict(),sort_keys=True)))
    pd.DataFrame(rows).to_csv(OUT/'classification_final_feasibility_counts.csv',index=False)
    clinical=pd.read_csv(OUT/'clinical_observed_subjects.csv')
    scores=['MMSE Total Score','GDSCALE Total Score','Global CDR','FAQ Total Score','NPI-Q Total Score']
    feasibility=[]
    for variables in [['MMSE Total Score','Global CDR'],scores]:
        q=clinical.dropna(subset=variables)
        for task,groups in [('AD_CN',['AD','CN']),('MCIstrict_CN',['MCI','CN']),('MCIpooled_CN',['EMCI','LMCI','MCI','CN']),('MCI_legacyEarlyLate_CN',['EMCI','LMCI','CN']),('EMCI_LMCI',['EMCI','LMCI'])]:
            sub=q[q['Research Group'].isin(groups)]
            splitmap=m.set_index('subject')
            outside=sub['Subject ID'].map(splitmap.not_in_final165_training_manifest).fillna(False)
            feasibility.append(dict(variables=';'.join(variables),task=task,n=len(sub),
                                    labels=json.dumps(sub['Research Group'].value_counts().to_dict(),sort_keys=True),
                                    not_in_final165_train_n=int(outside.sum()),untouched_train_and_val_n=0))
    pd.DataFrame(feasibility).to_csv(OUT/'clinical_classifier_feasibility.csv',index=False)
    exclusions=[]
    for t in ['av45','fdg']:
        for p in (FINAL/f'paired_regions_{t}').glob('*.csv'):
            d=pd.read_csv(p)
            d=d[d[[f'real_{t}_mean',f'syn_{t}_mean']].isna().any(axis=1)]
            for _,v in d.iterrows():
                exclusions.append(dict(tracer=t,region=p.stem.removeprefix('region_'),subject=v.subject,
                                       reason='missing ROI mean in saved SynthSeg mask; retained as NA'))
    pd.DataFrame(exclusions).to_csv(FINAL/'missing_roi_pair_exclusions.csv',index=False)


if __name__=='__main__':
    adjusted_analysis();table();plots();candidate_counts();manifest_and_checks();report()
