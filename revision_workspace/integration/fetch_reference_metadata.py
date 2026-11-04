from pathlib import Path
import json,urllib.request,urllib.parse,concurrent.futures
D=Path(__file__).resolve().parent/'reference_evidence'
items={'synthseg':'10.1016/j.media.2023.102789','friston1995spatial':'10.1002/hbm.460030303','mosconi2005reduced':'10.1212/01.WNL.0000163856.13524.08','he2015meta':'10.1007/s12013-014-0138-7','strom2022cortical':'10.1093/brain/awab294','jack2024revised':'10.1002/alz.13859'}
def fetch(pair):
 key,doi=pair;p=D/(key+'.json')
 if p.exists():return key,'retained existing metadata'
 url='https://api.crossref.org/works/'+urllib.parse.quote(doi,safe='')
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'DIRECTPP-local-revision/1.0'})
  with urllib.request.urlopen(req,timeout=45) as r:data=json.load(r)
  p.write_text(json.dumps({'request_url':url,'message':data['message']},ensure_ascii=False,indent=2)+'\n')
  return key, data['message']['title'][0]
 except Exception as e:return key,str(e)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for x in pool.map(fetch,items.items()):print(x)
