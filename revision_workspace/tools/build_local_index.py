"""Read-only source indexing; writes only revision_workspace/index. Python stdlib only."""
from pathlib import Path
from urllib.parse import unquote, urlsplit, quote
from collections import Counter, defaultdict
import re, hashlib, json, csv
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'revision_workspace/index'; SRC=ROOT/'rebuttal/BMEF_from_notion'
files=sorted(p for p in SRC.rglob('*') if p.is_file()); main=next(SRC.glob('*.md'))
texts={p:p.read_text(encoding='utf-8') for p in files if p.suffix=='.md'}
lines={p:t.splitlines() for p,t in texts.items()}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
rel=lambda p:str(p.relative_to(ROOT))
def link(p,n=None):
 return f'[{p.name}'+(f':L{n}' if n else '')+']('+quote(__import__('os').path.relpath(p,OUT),safe='/')+(f'#L{n}' if n else '')+')'
def clean(s):return re.sub(r'[*`#]','',s).strip()
def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(c).replace('|','\\|').replace('\n',' ') for c in r)+' |\n' for r in rows)
def write(name,s): (OUT/name).write_text(s,encoding='utf-8')
links=[]
pat=re.compile(r'!?\[([^\]\n]*)\]\(([^\n]*?)\)')
for p,t in texts.items():
 for m in pat.finditer(t):
  raw=m.group(2).strip().strip('<>'); url=urlsplit(raw); n=t[:m.start()].count('\n')+1
  if url.scheme or raw.startswith('//'):status='external_not_fetched'; target=raw
  elif raw.startswith('#'):status='anchor_not_verified';target=raw
  else:
   q=(p.parent/unquote(url.path)).resolve();target=str(q.relative_to(ROOT)) if q.is_relative_to(ROOT) else str(q);status='local_ok' if q.is_file() else 'MISSING'
  links.append(dict(source=rel(p),line=n,label=m.group(1),raw=raw,target=target,status=status))
manifest=[dict(path=rel(p),export_relative=str(p.relative_to(SRC)),bytes=p.stat().st_size,sha256=sha(p),lines=len(lines[p]) if p in lines else None,type='Markdown' if p in texts else 'PDF',integrity='UTF-8 decoded' if p in texts else 'PDF header OK' if p.read_bytes().startswith(b'%PDF-') else 'CHECK') for p in files]
# authoritative group memberships from the opening table, with explicit minor intersections
G={
'G1':('临床条件与 VLM','Results L88；Methods L222–263；Figure 1','R2-5 R2-14 R2-15 R2-16 R3-1 R3-2 R3-8 R3-9 R3-15'),
'G2':('数据划分与复现','Methods L293–303、L345–347；Data Availability','R2-3 R2-6 R2-19 R3-6 R3-13'),
'G3':('Figure 2 与基线公平性','Results L100–115；Methods L306–321','R2-17 R3-9 R3-10 R3-11 R3-12 R3-15'),
'G4':('Figure 4 区域统计','Results L119、L134–148；Methods L324–336；Supplementary','R2-8 R2-9 R2-10 R3-4 R3-5 R3-11 M5 M19'),
'G5':('Figure 5 分类评价','Results L151–167；Methods L338–344','R2-5 R2-11 R2-12 R2-16 R3-1 R3-6 R3-7 R3-9'),
'G6':('单步生成、效率与局限','Methods L276–291、L345–347；Discussion L173、L186','R2-13 R2-18 R3-9 R3-12 R3-15'),
'G7':('临床定位与全文结论','Title、Abstract、Discussion L170–188','R2-4 R2-7 R2-20 R3-3 R3-4 R3-13 R3-14 R3-15'),
'G8':('临床数据与 Table S1','Methods L293–299；Supplementary Table S1','R2-5 R2-16 R3-1 R3-2 R3-6')}
minor_groups={1:['G7'],2:['G7'],3:['G4'],4:['G1','G6'],5:['G4'],6:['G4'],7:['G4','G2'],8:['BIB'],9:['BIB'],10:['BIB'],11:['BIB'],12:['BIB','G2'],13:['BIB','G4'],14:['BIB','G3'],15:['G2'],16:['G1','G6'],17:['G1'],18:['G4'],19:['G4'],20:['SUBMISSION'],21:['G1','G8']}
def groups(cid):
 return sorted(set([g for g,v in G.items() if cid in v[2].split()]+(minor_groups.get(int(cid[1:]),[]) if cid.startswith('M') else [])))
ml=lines[main]; starts=[i for i,l in enumerate(ml) if re.match(r'### (R[23]-\d+|Minor-\d+)\.',l)]
comments=[]
for k,a in enumerate(starts):
 b=starts[k+1] if k+1<len(starts) else next(i for i in range(a+1,len(ml)) if ml[i].startswith('## 四'))
 cid=re.match(r'### (R[23]-\d+|Minor-\d+)\.',ml[a]).group(1).replace('Minor-','M')
 p=main; lo=a+1; hi=b
 local=[x for x in links if x['source']==rel(main) and a+1<=x['line']<=b and x['status']=='local_ok' and '回复' in x['label'] and ('正文修改' in x['label'] or '回复细节' in x['label'])]
 # R3-10 response belongs to main, detail page is ancillary.
 if cid in ['R2-8','R2-9','R2-10','R2-15','R3-5','R3-9','R3-12']:
  p=ROOT/local[0]['target'];lo=0;hi=len(lines[p])
 ls=lines[p]; english=[i for i in range(lo,hi) if re.match(r'^(We (?:sincerely |also |would |further |have |agree |appreciate |thank|confirm)|Thank you)',ls[i])]
 assert english,cid
 s=english[0];e=hi
 for i in range(s+1,hi):
  l=ls[i].strip()
  if not l:continue
  if re.search('[\u4e00-\u9fff]',l) and not l.startswith('>') or re.match(r'^\[.*\]\(',l) or re.match(r'^## ',l): e=i;break
 while e>s and not ls[e-1].strip():e-=1
 body='\n'.join(ls[s:e]); comments.append(dict(id=cid,title=ml[a].split('. ',1)[1],source=rel(main),section_start=a+1,section_end=b,response_source=rel(p),response_start=s+1,response_end=e,response_sha256=hashlib.sha256(body.encode()).hexdigest(),response_words=len(body.split()),groups=groups(cid),status='英文段落已定位；作者确认（用户声明）',linked_pages=[x['target'] for x in links if x['source']==rel(main) and a+1<=x['line']<=b and x['status']=='local_ok']))
# list every Original/Revised proposal marker outside original-review archives; content kept in original files
revs=[]; extra=[]
for p,ls in lines.items():
 if '原始审稿意见' in str(p):continue
 current_comment=None; heading=[]; last_original=None
 for i,l in enumerate(ls):
  m=re.match(r'### (R[23]-\d+|Minor-\d+)\.',l)
  if m:current_comment=m.group(1).replace('Minor-','M');last_original=None;heading=[]
  if l.startswith('#') or re.match(r'^(修改\s*[一二三四五六七八九十\d]|位置[一二三四五六七八九十]|[一二三四五六七八九十]+、)',clean(l)):heading.append((i,l))
  c=clean(l)
  if re.match(r'^Original(?:\b|[（： —])',c,re.I):last_original=i
  if not re.match(r'^Revised(?:\b|[（： —])',c,re.I):continue
  # pointers include full marker-led source section; no copying of prose
  orig=last_original
  if orig is not None and i-orig>100:orig=None
  before=[(n,h) for n,h in heading if n<i and (orig is None or n<orig)]
  context=before[-1][1] if before else p.stem
  structural=[h for n,h in before if h.startswith('#')]
  context=(structural[-1]+' / '+context) if structural and structural[-1]!=context else context
  end=next((j for j in range(i+1,len(ls)) if (ls[j].startswith('#') or re.match(r'^(修改\s*[一二三四五六七八九十\d]|位置[一二三四五六七八九十]|[一二三四五六七八九十]+、|Original)',clean(ls[j])))),len(ls))
  localcid=current_comment if p==main else (re.search(r'(R[23]-\d+|M\d+)',p.name).group(1) if re.search(r'(R[23]-\d+|M\d+)',p.name) else None)
  gs=groups(localcid) if localcid else [p.name[:2]] if p.name.startswith(('G4','G5')) else []
  if p.name.startswith('R3-9回复'):gs=['G3'] if i<80 else ['G5']
  if p.name.startswith('G4') and i>=277:gs=sorted(set(gs+(['G3'] if i<492 else [])))
  status='作者方案候选；按位置合并，未实施'
  if p.name.startswith('G4'):status='集中方案；核心为合并入口，扩展须保留范围限制'
  if p.name.startswith('G5'):status='集中方案；与 G3/G5 共享位置合并'
  if p.name.startswith(('R2-8回复','R2-9回复','R2-10回复')):status='旧独立方案；已由 G4 核心合并继承，禁止逐页覆盖'
  if p.name.startswith('G4') and i==177:status='旧图注候选；由本页修改16明确整合 M19（L509）'
  if p==main and current_comment=='R2-14' and i>575:status='已被 R3-8 修改四明确取代（主页面 L1287）'
  revs.append(dict(id=f'V{len(revs)+1:03}',source=rel(p),original_marker=orig+1 if orig is not None else None,revised_marker=i+1,section_end=end,location=context,comment=localcid,groups=gs,status=status,marker=c))
 # headings for additions that might have no Revised marker, including tables, bibliography, axes
 for i,l in enumerate(ls):
  if re.search(r'补充表|Supplementary|BibTeX|参考文献处理|图像本身|图像坐标轴|新增修改|修改 10',l,re.I) and (l.startswith('#') or re.match(r'^(修改|[一二三四五六七八九十]+、|\*\*Supplementary)',l)):
   extra.append(dict(source=rel(p),line=i+1,title=l))
# duplicate English responses
by=defaultdict(list)
for c in comments:
 p=ROOT/c['response_source'];s=' '.join(lines[p][c['response_start']-1:c['response_end']]);by[re.sub(r'\s+',' ',s).strip()].append(c['id'])
dups=[v for v in by.values() if len(v)>1]
content_findings=[]
for pair in dups:
 content_findings.append('重复英文回复：'+', '.join(pair))
for c in comments:
 if c['id']=='R3-9':
  page=texts[ROOT/c['response_source']]
  if any('R3-9' in pair for pair in dups):
   c['status']='英文重复，须核对主题及来源'
  elif '历史英文定稿虽已确认，但未能逐字恢复' in page:
   c['status']='消融英文已补齐；按已确认中文方向整理，非历史逐字稿（子页L23）'
   c['response_provenance_note']='子页L23：历史英文定稿虽已确认，但未能逐字恢复；本段不冒充历史逐字稿。'
   content_findings.append('R3-9 English reconstructed from confirmed Chinese direction; historical verbatim text not recovered')
r314=next(p for p in texts if p.name.startswith('R3-14正文'))
r314_count=sum(r['source']==rel(r314) for r in revs)
coverage_text=('56/56 意见入口、56/56 英文段落已定位；未发现重复英文，R3-9 消融主题英文已补齐。其英文来源按子页说明标为按已确认中文方向整理，非历史逐字稿。' if not dups else '56条意见及英文入口已定位，但存在重复回复，须核对。')
for name,obj in [('source_manifest.json',manifest),('local_links.json',links),('comment_index.json',comments),('revision_candidates.json',revs),('addition_locations.json',extra)]:write(name,json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
intro='编号和行号均基于未改写的导出原件；行号为 1 起算，链接后的 #L 仅作定位提示，阅读时以文件行号为准。文件身份见 SOURCE_MANIFEST.md。\n\n'
write('COMMENT_INDEX.md','# 56 条审稿意见与英文回复索引\n\n'+intro+'作者确认状态沿用本轮用户声明；导出中的旧“待定/进行中”文字不自动推翻确认。文本存在不等于科学结论已验证。**'+coverage_text+'**\n\nM1–M21 = 导出 Minor-1–21 = 原登记 R3-minor-01–21。\n\n'+table(['编号 / 标题','意见范围','完整英文 Response 范围','字数','修改组','正文入口 / 状态'],[(c['id']+' '+c['title'],link(ROOT/c['source'],c['section_start'])+f'–{c["section_end"]}',link(ROOT/c['response_source'],c['response_start'])+f'–{c["response_end"]}',c['response_words'],', '.join(c['groups']) or '致谢', '[正文候选](REVISION_INDEX.md) '+', '.join(r['id'] for r in revs if r['comment']==c['id'])+'；'+c['status']) for c in comments])+'\n双向查询：comment_index.json 保存关联子页；revision_candidates.json 保存意见编号、组、Original/Revised 起点。正文最终版本须通过计划中的位置登记后才可实施。\n')
write('REVISION_INDEX.md','# 正文修改来源与版本索引\n\n'+intro+'这是来源目录，不是可按行执行的补丁。Original/Revised 原文保存在下表指向的文件中；范围包括完整修改片段及局部说明。旧稿行号只作定位，实施时以标题、label 和 Original 原文重新匹配。\n\n'+'''版本裁定规则：用户确认逐条回复；不据页面时间或先后顺序决定正文版本。G4 核心明确合并 R2-8/9/10、R3-5；R2-8 的 CN/MCI/AD 目的旧句已由 G4 L49–67 明确纠正为两类比较。G4 修改16明确“整合原 G4 已确认修改及 M-19”，图注采用其合并入口，修改8保留为历史候选。R3-8 修改四明确取代 R2-14 的 prompt 段（主页面 L1287），其他维度和优化参数继续保留。M2 Original 已包含 M1，合并为一句；M13 Revised 明确整合 M6。这些是文字明示的继承，非以先后决定。\n\nG4 扩展包含 G3 图像评价、Figure 2 表格和补充图，不应因页面名而全部归入 ROI。G5 页前三处只有两处位于 Comparison Methods、一处分类 Methods，不能当作完整 Figure 5 Results 方案。\n\n真实待合并位置：Results L119（G4、M3、M7）、L134/138（G4、M18）、Methods L229–241（R2-14/15、M16）、L263（R3-8、M16）、L297（R3-2、G2、G8）、L342（G5、R3-3）、L347（M16、R2-18/19）、Discussion L186（G4、G6、G7、G8）。这里是不同要求叠加，尚未形成单一最终源码；不可任选整段覆盖。\n\n'''+table(['候选','目标位置 / 上下文','Original 起点','Revised 起点–局部范围末行','关联意见 / 组','版本状态'],[(r['id'],r['location'],link(ROOT/r['source'],r['original_marker']) if r['original_marker'] else '新增/未发现配对 Original，局部核对',link(ROOT/r['source'],r['revised_marker'])+f'–{r["section_end"]}',(r['comment'] or '集中页，见 GROUP_INDEX')+' / '+','.join(r['groups']),r['status']) for r in revs])+'\n## 新增表格、引文与无标准配对标记的入口\n\n'+table(['来源','说明'],[(link(ROOT/x['source'],x['line']),x['title']) for x in extra])+'\n## 替换文件后的方案状态与整合缺口\n\nR3-9 已补三处正文方案（L49/55、L67/73、L85/91），与 G5 集中页三项同文，属于同一方案的重复来源，合并一次即可。R3-14 已补四处正文方案（L13/19、L31/37、L49/55、L67/73）和引文提案；L43明确纠正 R2-20 旧稿仍含 widespread screening 的冲突，按这一明示关系合并，而非依时间覆盖。L186只插入两句，须保留其他组局限。R3-9 英文来源说明见 COMMENT_INDEX。G5 Results L151–167、Figure 5 图注与最终图需要据已完成分类报告统一撰写，不能假定此子页已包含。真实冲突、旧状态与未决事实见 INTEGRITY_REPORT.md。\n')
write('GROUP_INDEX.md','# G1–G8 统一修改入口\n\n分组原文：'+link(main,39)+'；一条意见可属于多组，一个正文位置只生成一份最终版本。以下原稿行号需实施前重新匹配。Minor 的扩展映射为索引判断，原分组明确列出的 M5/M19 除外。\n\n'+table(['组','正文 / 图表','原分组关联意见','执行来源和归并要求'],[(g+' '+v[0],v[1],v[2],{'G1':'主页面 R2-14、R3-8/15；R2-15 子页；M16/17；保留 prompt 继承关系','G2':'主页面 R2-3/6/19、R3-6；M15；R3-13；与 G8 同段合并','G3':'R2-17、R3-10；G4 修改11–15；G5 修改1/2；Figure 2 历史值与新 OOF 分开','G4':'G4 集中页核心 + 修改16/17；M7/M18；不恢复旧 CN/MCI/AD 句','G5':'G5 修改3 + 分类最终统计；R3-3 方法标题；Figure 5 统一重建','G6':'R2-13 子页、R2-18 主页面、R3-12 子页、M16；核对单步及效率限定','G7':'R2-4/7/20、R3-3/13/14 子页和 R3-14 主页面；R3-14明确纠正旧筛查句；最后收敛结论','G8':'R3-2 子页；Table S1；11月3日临床来源报告；不沿用其他任务 OUT_OF_SCOPE 为本轮豁免'}[g]) for g,v in G.items()])+'\n'+table(['组','集中/关联候选编号'],[(g,', '.join(r['id'] for r in revs if g in r['groups'])) for g in G])+'\n逐条到组见 COMMENT_INDEX；组到候选见 revision_candidates.json 的 groups。G4/G5 集中页只有部分明确关联编号，其候选需同时参考本表全部意见，不把文件名当作唯一归属。\n')
write('SOURCE_MANIFEST.md','# Notion 导出完整文件清单\n\n只读递归遍历全部目录，不修改、移动或补写任何源文件。共 '+str(len(files))+' 文件：'+str(len(texts))+' Markdown、'+str(len(files)-len(texts))+' PDF；没有单独图片文件。PDF 可能内嵌图片，未据此声称图源可编辑。SHA-256 为本轮读取字节的身份快照，不等于科学有效性或云端导出完整性。\n\n'+table(['导出内相对路径','字节 / 行数','SHA-256','本地完整性'],[(link(ROOT/x['path'])+' (`'+x['export_relative']+'`)',str(x['bytes'])+' / '+str(x['lines'] or 'PDF'),x['sha256'],x['integrity']) for x in manifest])+'\n机器清单：source_manifest.json；逐链接解析结果：local_links.json。路径按 URL 解码并相对链接所在文件解析，保留 Notion ID 与特殊字符。外部网址只登记，未联网认证。\n')
write('INTEGRITY_REPORT.md','# 完整性与版本冲突报告\n\n'+intro+f'全目录 {len(files)} 文件；意见 20+15+21=56；56 个英文段落入口；同文回复组：{dups}。UTF-8 全部可解码。这里只核查本地导出快照，无法证明 Notion 云端不存在未导出页面。\n\n'+'''## 已修复缺口与剩余整合事项\n\n- **R3-9 旧错配已修复**：用户替换文件后，消融英文位于 L25–39，不再与 R3-6 重复；三处 Original/Revised 已补入。子页 L23 明确该英文按已确认中文方向整理，未恢复历史逐字定稿；保留这一来源限定，不将其声称为历史原文。\n- **R3-14 旧空页已补齐**：四处 Discussion Original/Revised 和 jack2024revised 引文提案已定位；引文尚未写入 BibTeX。L43 明确纠正 R2-20 旧稿的 widespread screening，L65/79/98 要求保留其他组的局限与合并范围。\n- **G5 方案不完整**：集中页仅3项 Methods 修改；末尾“当前 G5 正文页面尚无具体修改内容”与同页实际内容矛盾，为保存的旧状态说明。Figure 5 Results/图注仍待整合，不能直接宣布方案齐备。\n\n## 有依据的继承与重叠\n\n- R3-9 三处正文与 G5 集中页同文，为同一修改的多来源，不形成竞争版本。R3-14 L43 明示修正 R2-20 的 widespread screening；Discussion L175/177/179/186 与 G7 既有方案合并，不能丢弃其他意见要求。\n- G4 L49–67 明确纠正 R2-8 旧目的段；G4 L69–85、L113–127 明示采用 R2-10 合并版；L493–524 图注明示整合核心和 M19；旧版全部保留，实施入口为合并要求。\n- 主页面 L1287 明确 R3-8 prompt 段取代 R2-14 先前版本；M2 包含 M1，M13 整合 M6。\n- G4/M7/M18、R3-8/M16、R3-2/G2、G4/G6/G7/G8 Discussion 等位置属于真实重叠，必须生成逐位置最终合成版本，再与全部要求比对。未经逐句核对，不认定不同方案已可无冲突覆盖。\n- G4 页保留“待最终确认”标签；按本轮用户声明逐条回复已确认，但不将正文提案的旧标签自动改为最终定稿。替换文件的新正文已作为来源收录，不等于正式源码已实施。\n\n## 事实与表述的待核对冲突\n\n- 主页面开头记载历史分类三折重复使用同一折，R2-3/R3-6 英文则笼统描述独立三折。须区分历史与新实验的身份；不重开全库追查，也不以协议说明认证历史执行。\n- R3-6 英文称 MRI/PET 最大时差不可重建；11月3日 metadata_1103_review 和 filtering_code_recovery 有新证据。只按覆盖范围更新，不能将新增元数据外推全部 cohort。\n- R3-2 方案承认诊断组条件模拟填补；11月3日 filled_information_restoration 有更细来源证据。核对 observed/filled、组、字段和人数后才能决定 Table S1。不能以旧补全方案替代新来源核实。\n- 旧 G3/主稿的 Full 全面优于所有方法、G5 普遍改善结论与新实验不一致；新报告保留任务/指标负结果，整合时逐数校验。\n- G4 扩展部分为建议或结构方案，拟定 input 路径并不等于文件已存在；不得直接粘贴后声称可编译。\n- 未发现以“.../…”结尾的截断证据不等于全文完整；替换后 R3-9 主题错配与 R3-14 空页已消除；仍须保留 R3-9 英文重建说明及旧状态/方案整合限制。无任意补写导出。\n\n## 链接检查\n\n'''+table(['状态','数量'],Counter(x['status'] for x in links).items())+'\n'+table(['来源','目标','状态'],[(link(ROOT/x['source'],x['line']),x['raw'],x['status']) for x in links if x['status'] not in ['local_ok','external_not_fetched']])+'\n全部链接明细在 local_links.json。外部 Notion/GitHub/DOI 未联网访问；即使外部 GitHub 指向本仓库，外部 URL 本身未认证。下阶段优先使用本地对应报告。\n')
assert len(comments)==56 and len({c['id'] for c in comments})==56
assert set(c['id'] for c in comments)=={f'R2-{i}' for i in range(1,21)}|{f'R3-{i}' for i in range(1,16)}|{f'M{i}' for i in range(1,22)}
print(json.dumps(dict(files=len(files),markdown=len(texts),comments=len(comments),revision_candidates=len(revs),additions=len(extra),link_status=dict(Counter(x['status'] for x in links)),duplicate_responses=dups),ensure_ascii=False,indent=2))

with (OUT/'INTEGRITY_REPORT.md').open('a') as f:f.write('\n## 本轮工程验证\n\n见 [validation.json](validation.json)：25个导出文件哈希复核、56段回复范围哈希、'+str(len(revs))+'个修改标记范围；实际链接、PDF与代码围栏检查结果以该JSON为准。工程验证不认证科学结论，R3-9英文重建来源限定仍保留。\n')

if (OUT/'SOURCE_UPDATE_R3_9_R3_14.json').is_file():
 with (OUT/'INTEGRITY_REPORT.md').open('a') as f:f.write('\n## R3-9 / R3-14 来源替换记录\n\n见 [更新收据](SOURCE_UPDATE_R3_9_R3_14.json)：两文件新旧哈希、旧索引快照位置、116个旧候选到当前编号的映射。新增7处Original均与当前稿件源码在忽略空白后匹配；R3-9三处Revised与G5对应三处同文。候选编号随本轮重建发生变化，应结合来源路径/行号/快照使用，不把裸编号视为跨版本永久ID。\n')
