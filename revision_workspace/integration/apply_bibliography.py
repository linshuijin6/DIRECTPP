from edit_registry import ROOT,WORK,apply
import re,json
folder=WORK/'reference_evidence'
def entries(text):return {re.match(r'@\w+\s*\{\s*([^,]+)',x).group(1):x.strip() for x in re.split(r'(?=@\w+\s*\{)',text) if re.match(r'@\w+\s*\{\s*([^,]+)',x)}
new={}
for key in ['synthseg','friston1995spatial','mosconi2005reduced','he2015meta','strom2022cortical','jack2024revised']:
 d=json.loads((folder/(key+'.json')).read_text())['message'];authors=' and '.join((f"{a['family']}, {a.get('given','')}" if 'family' in a else '{'+a['name']+'}') for a in d['author']);title=d['title'][0];subtitle=d.get('subtitle',[])
 if subtitle and subtitle[0]:title+=': '+subtitle[0]
 year={'synthseg':2023,'friston1995spatial':1995,'mosconi2005reduced':2005,'he2015meta':2015,'strom2022cortical':2022,'jack2024revised':2024}[key]
 fields={'title':title,'author':authors,'journal':d['container-title'][0],'year':str(year),'volume':d.get('volume'),'number':d.get('issue'),'pages':d.get('page') or d.get('article-number'),'doi':d['DOI']}
 new[key]='@article{'+key+',\n'+',\n'.join('  '+k+' = {'+str(v).replace('&',r'\&').replace('–','--')+'}' for k,v in fields.items() if v)+'\n}'
new['spm']=r'''@book{spm,
 title = {Statistical Parametric Mapping: The Analysis of Functional Brain Images},
 editor = {Friston, Karl J. and Ashburner, John T. and Kiebel, Stefan J. and Nichols, Thomas E. and Penny, William D.},
 publisher = {Academic Press},
 year = {2007},
 isbn = {9780123725608},
 url = {https://www.fil.ion.ucl.ac.uk/spm/doc/books/spm/Statistical_Parametric_Mapping_The_Analysis_of_Functional_Brain_Images.pdf}
}'''
new['Xing2022']=r'''@inproceedings{Xing2022,
 title = {Flow Straight and Fast: Learning to Generate and Transfer Data with Rectified Flow},
 author = {Liu, Xingchao and Gong, Chengyue and Liu, Qiang},
 booktitle = {International Conference on Learning Representations},
 year = {2023},
 eprint = {2209.03003},
 archiveprefix = {arXiv},
 url = {https://openreview.net/forum?id=XVjTT1nw5z}
}'''
new['song2021ddim']=r'''@inproceedings{song2021ddim,
 title = {Denoising Diffusion Implicit Models},
 author = {Song, Jiaming and Meng, Chenlin and Ermon, Stefano},
 booktitle = {International Conference on Learning Representations},
 year = {2021},
 eprint = {2010.02502},
 archiveprefix = {arXiv},
 url = {https://openreview.net/forum?id=St1giarCHLP}
}'''
new['pinaya2023generative']=r'''@article{pinaya2023generative,
 title = {Generative AI for Medical Imaging: Extending the MONAI Framework},
 author = {Pinaya, Walter H. L. and Graham, Mark S. and Kerfoot, Eric and Tudosiu, Petru-Daniel and Dafflon, Jessica and Fernandez, Virginia and Sanchez, Pedro and Wolleb, Julia and others},
 journal = {arXiv preprint arXiv:2307.15208},
 year = {2023},
 doi = {10.48550/arXiv.2307.15208}
}'''
new['Cao2021swin']=r'''@article{Cao2021swin,
 title = {Swin-Unet: Unet-like Pure Transformer for Medical Image Segmentation},
 author = {Cao, Hu and Wang, Yueyue and Chen, Joy and Jiang, Dongsheng and Zhang, Xiaopeng and Tian, Qi and Wang, Manning},
 year = {2021},
 journal = {arXiv preprint arXiv:2105.05537},
 eprint = {2105.05537},
 archiveprefix = {arXiv},
 doi = {10.48550/arXiv.2105.05537}
}'''
refs=['rebuttal/BMEF_from_notion/BMEF审稿回复 3d295d43b2dd8300b74601d792205677.md','rebuttal/BMEF_from_notion/BMEF审稿回复/R3-14正文修改 d9795d43b2dd8393a4fd01048b566331.md']+[str(p.relative_to(ROOT)) for p in folder.glob('*.json')]
for target,pid in [('manuscript/references.bib','BIB-MANUSCRIPT'),('rebuttal/references.bib','BIB-REBUTTAL')]:
 old=(ROOT/target).read_text();e=entries(old)
 for key in ['fischl2012freesurfer','dalca2022synthseg']:e.pop(key,None)
 e.update(new);updated='\n\n'.join(e.values())+'\n'
 apply(pid,target,old,updated,['M8','M9','M10','M11','M12','M13','M14','R3-14'],['BIB'],refs,'Correct author/title/publication records against primary publications and DOI metadata; remove duplicate FreeSurfer and incorrect SynthSeg entry; preserve all unrelated records',section='Bibliography')
# Add the confirmed spatial-normalization method citation at its actual use site.
p=ROOT/'manuscript/BMEF_main.tex';t=p.read_text();old='using SPM~\\cite{spm}, with identical transformation matrices applied to preserve cross-modality alignment.';new='using SPM~\\cite{spm,friston1995spatial}, with identical transformation matrices applied to preserve cross-modality alignment.'
apply('BIB-SPM-METHOD-CITATION','manuscript/BMEF_main.tex',old,new,['M12'],['BIB','G2'],refs,'Cite SPM reference book and actual spatial-registration method at the use site',section='Materials and Data Preprocessing / SPM')
receipt={'metadata_files':[p.name for p in folder.glob('*.json')],'additional_primary_sources':{'spm':'https://www.sciencedirect.com/book/edited-volume/9780123725608/statistical-parametric-mapping','Xing2022':'https://par.nsf.gov/servlets/purl/10445517','song2021ddim':'https://arxiv.org/abs/2010.02502','pinaya2023generative':'https://arxiv.org/abs/2307.15208','Cao2021swin':'https://arxiv.org/abs/2105.05537','synthseg':'https://www.sciencedirect.com/science/article/pii/S1361841523000506','jack2024revised':'https://alz-journals.onlinelibrary.wiley.com/doi/10.1002/alz.13859'},'openreview_browser_challenge':['XVjTT1nw5z','St1giarCHLP'],'verification_scope':'new/corrected records and referenced primary publications; not a full independent audit of every historical reference'}
(folder/'verification.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
