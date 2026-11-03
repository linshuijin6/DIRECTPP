#!/usr/bin/env python3
"""
Apply verified responses and manuscript revisions from
BMEF_respose_and_revision_details.md to rebuttal/sections/
(02_reviewer2.tex, 03_reviewer3_major.tex, 04_reviewer3_minor.tex).
"""

import os
import re
import csv
from build_rebuttal_skeleton import R2_TOPICS, R3_MAJOR_TOPICS, R3_MINOR_TOPICS

BASE_DIR = "/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP"
DETAILS_MD = os.path.join(BASE_DIR, "rebuttal/BMEF_respose_and_revision_details.md")
SECTIONS_DIR = os.path.join(BASE_DIR, "rebuttal/sections")

LOC_MAP = {
    # General / Section names
    "Results → Superior Fidelity and Generalizability of Synthesized PET": "Results: Superior Fidelity and Generalizability of Synthesized PET",
    "Methods → Materials and Data Preprocessing": "Methods: Materials and Data Preprocessing",
    "Results — Section 2.4": "Results: Precise Diagnostic Classification and MCI Stage Discrimination",
    "Materials and Methods — Section 4.3": "Methods: Clinical Cohorts and Diagnostic Subclasses",
    "Materials and Methods — Section 4.5.2": "Methods: MCI Stage Discrimination Framework",
    "Abstract — Results": "Abstract: Results",
    "Introduction — 研究贡献总结": "Introduction: Summary of Contributions",
    "Results — Section 2.2": "Results: Cross-Dataset Generalizability on OASIS-3",
    "Figure 2 — Caption": "Figure 2 Caption",
    "Results §2.3：区域摄取值定义": "Results §2.3: Regional Uptake Value Definition",
    "Results §2.3：两类统计分析的目的": "Results §2.3: Objectives of Regional Statistical Analyses",
    "Results §2.3：Real–Syn 区域一致性": "Results §2.3: Real-Syn Regional Uptake Concordance",
    "Methods §4.5.1：Real–Syn 配对一致性": "Methods §4.5.1: Real-Syn Pairwise Consistency Testing",
    "Methods §4.5.1：AD/CN 组间效应量": "Methods §4.5.1: AD/CN Between-Group Effect Sizes",
    "Methods §4.5.1：BH-FDR 的比较族": "Methods §4.5.1: False Discovery Rate (BH-FDR) Comparison Families",
    "Results §2.3：AD/CN 疾病效应与 Cohen's d": "Results §2.3: AD/CN Diagnostic Differentiation and Effect Sizes",
    "Figure 4 Caption": "Figure 4 Caption",
    "Methods §4.2.3 — 单步采样的理论表述": "Methods §4.2.3: Theoretical Formulation of One-Step Sampling",
    "Methods §4.2.3 — Eq. (7) 的引出语句": "Methods §4.2.3: Formulation of Eq. (7)",
    "Methods — Domain-Adapted VLM": "Methods: Domain-Adapted VLM Formulation",
    "Results — The DIReCT++ Framework for Precision PET Synthesis": "Results: The DIReCT++ Framework Overview",
    "Supplementary Materials — 新增 Adapter 消融结果": "Supplementary Materials: Adapter Ablation Study",
    "Methods §4.3：修正 EMCI、LMCI 和 MCI-U 的定义": "Methods §4.3: Diagnostic Cohort Specifications (EMCI, LMCI, MCI-U)",
    "Methods §4.5.2：明确分类任务的含义": "Methods §4.5.2: Stage Discrimination vs. Diagnostic Classification",
    "Results → Recapitulation of Disease-Specific Biomarker Patterns": "Results: Recapitulation of Disease-Specific Biomarker Patterns",
    "Methods → Rectified Flow": "Methods: Rectified Flow Formulation",
    "Results → Section 2.3": "Results §2.3: Regional Uptake Analysis",
    "Methods → Statistical Analysis → Regional Group-Wise Comparison": "Methods: Statistical Analysis (Regional Group-Wise Comparison)",
    "Methods → Competing Methods": "Methods: Baseline Implementations and Competing Methods",
    "Methods → Multi-Task Learning and One-Step Generation": "Methods: Multi-Task Learning and One-Step Generation",
    "Methods → Implementation Details": "Methods: Implementation Details and Hardware",
    "Results → Regional Statistical Analysis": "Results §2.3: Regional Statistical Analysis",
    "Results → Overview of DIReCT++": "Results: Overview of the DIReCT++ Framework",
    "References.reference.bib.txt": "References (references.bib)"
}

def clean_location(loc_raw: str, line_no: str) -> str:
    loc = loc_raw.strip()
    
    if loc in LOC_MAP:
        loc = LOC_MAP[loc]
    else:
        for k, v in LOC_MAP.items():
            if k in loc:
                loc = loc.replace(k, v)
                
    loc = loc.replace('`BMEF_main.tex`', 'BMEF_main.tex')
    loc = re.sub(r'第\s*(\d+(?:[–-]\d+)?)\s*行[。，]?', r'Line \1', loc)
    loc = loc.replace('第一段', 'Paragraph 1').replace('第二段', 'Paragraph 2')
    loc = loc.replace('第一句', 'Sentence 1').replace('第二句', 'Sentence 2').replace('第三句', 'Sentence 3')
    loc = loc.replace('，', ', ').replace('、', ', ')
    loc = loc.replace('：', ': ')
    loc = loc.replace('§', 'Section ')
    loc = loc.replace('→', ' > ')
    
    # Strip any remaining Chinese characters
    loc = re.sub(r'[\u4e00-\u9fff]', '', loc).strip()
    loc = re.sub(r'^[,\s:–-]+|[,\s:–-]+$', '', loc)
    
    line_clean = line_no.replace('、', ', ').replace('–', '--').replace('-', '--').replace('行', '').replace('第', '').replace('：', '').replace(':', '').strip()
    line_clean = re.sub(r'[\u4e00-\u9fff]', '', line_clean).strip()
    
    if 'Original' in line_clean:
        line_clean = ''
    if 'revised-1029-fig1.pdf' in line_clean:
        line_clean = ''
        
    if line_clean and f"Line {line_clean}" not in loc and f"line {line_clean}" not in loc:
        if loc:
            return f"{loc}, Line {line_clean}"
        else:
            return f"Line {line_clean}"
            
    return loc if loc else "Revised Manuscript"

def clean_latex(text: str) -> str:
    """Escapes special characters and formats equations for LaTeX."""
    if not text:
        return ""
    t = text.strip()
    
    # Standardize newlines
    t = t.replace('\r\n', '\n').replace('\r', '\n')
    
    # 1. HTML links: <a href="URL">text</a> -> \href{URL}{text}
    t = re.sub(r'<a href="([^"]+)">([^<]+)</a>', r'\\href{\1}{\2}', t)
    
    # 2. Markdown links: [text](URL) -> \href{URL}{text} or \url{URL}
    def md_link(m):
        txt, url = m.group(1), m.group(2)
        if txt == url:
            return rf"\url{{{url}}}"
        return rf"\href{{{url}}}{{{txt}}}"
    t = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', md_link, t)

    # 3. Protect existing \url{...} and \href{...}{...}
    url_bank = []
    def save_url(m):
        url_bank.append(m.group(0))
        return f"TOKENURLPROTECT{len(url_bank)-1}END"
    t = re.sub(r'\\(?:url|href)\{[^\}]*\}', save_url, t)

    # 4. Raw URLs to \url{...}
    def replace_raw_url(m):
        url = m.group(0)
        trail = ""
        while url and url[-1] in (";", ".", ",", ")", ">", "}", "]", "'", '"'):
            trail = url[-1] + trail
            url = url[:-1]
        return rf"\url{{{url}}}" + trail
    t = re.sub(r'https?://[^\s\)\}\]\>]+', replace_raw_url, t)

    # 5. Restore protected \url and \href
    for i in range(len(url_bank)-1, -1, -1):
        t = t.replace(f"TOKENURLPROTECT{i}END", url_bank[i])
        
    # Standardize citations like ~\cite or \~\\cite
    t = re.sub(r'\\~\\cite', r'~\\cite', t)
    t = re.sub(r'\\cite(?![a-zA-Z])', r'\\cite', t)
    
    # Float / Caption conversion for inline snippets inside \changedtext
    t = re.sub(r'\\begin\{table\}(?:\[[^\]]*\])?', r'\\begin{center}', t)
    t = re.sub(r'\\end\{table\}', r'\\end{center}', t)
    t = re.sub(r'\\caption\{((?:[^{}]|\{[^{}]*\})*)\}', r'\\textbf{Caption:} \1\\\\[4pt]', t)

    # Wrap lonely \item if outside itemize/enumerate
    if r'\item' in t and r'\begin{itemize}' not in t and r'\begin{enumerate}' not in t:
        t = "\\begin{itemize}[leftmargin=1.5em, itemsep=2pt]\n" + t + "\n\\end{itemize}"

    # Protect tabular environments from & escaping
    tab_bank = []
    def save_tab(m):
        tab_bank.append(m.group(0))
        return f"TOKENTABULARPROT{len(tab_bank)-1}END"
    t = re.sub(r'\\begin\{tabular\}\{[^\}]*\}.*?\\end\{tabular\}', save_tab, t, flags=re.DOTALL)

    # Unicode & math replacements
    t = t.replace("±", r"$\pm$")
    t = t.replace("¹⁸F", r"$^{18}\text{F}$")
    t = t.replace(r"\textsuperscript{18}F", r"$^{18}\text{F}$")
    t = t.replace(r"\textsuperscript{18}\text{F}", r"$^{18}\text{F}$")
    t = t.replace("κ", r"$\kappa$")
    t = t.replace("≈", r"$\approx$")
    t = t.replace("≥", r"$\ge$")
    t = t.replace("≤", r"$\le$")
    t = t.replace("→", r"$\rightarrow$")
    t = t.replace("–", "--")  # en-dash
    t = t.replace("—", "---") # em-dash
    t = t.replace("−", "$-$") # minus
    t = t.replace("“", "``").replace("”", "''")
    t = t.replace("‘", "`").replace("’", "'")
    t = t.replace("₀", r"$_0$").replace("₁", r"$_1$").replace("₂", r"$_2$")
    t = t.replace("x$_0$", r"$x_0$")
    t = t.replace("Aβ+", r"A$\beta$+")
    t = t.replace("Aβ−", r"A$\beta$-")
    t = t.replace("Aβ-", r"A$\beta$-")
    t = t.replace("Aβ", r"A$\beta$")
    t = t.replace("α₁", r"$\alpha_1$").replace("α₂", r"$\alpha_2$")
    t = t.replace("β₁", r"$\beta_1$").replace("β₂", r"$\beta_2$")
    t = t.replace("α", r"$\alpha$").replace("β", r"$\beta$")
    t = t.replace("θ", r"$\theta$")
    t = t.replace("τ", r"$\tau$")
    t = t.replace(r"\(\tau\)", r"$\tau$")
    t = t.replace(r"\(\\tau\)", r"$\tau$")
    t = t.replace("λ_F", r"$\lambda_F$").replace("λ_A", r"$\lambda_A$")
    t = t.replace("λ", r"$\lambda$")
    t = t.replace("Vθ", r"$V_\theta$")
    
    # Statistical terms (avoid double $$)
    t = re.sub(r'(?<!\$)\b([pP])\s*>\s*0\.05(?!\$)', r'$\1 > 0.05$', t)
    t = re.sub(r'(?<!\$)\b([pP])\s*<\s*0\.05(?!\$)', r'$\1 < 0.05$', t)
    t = re.sub(r'(?<!\$)\b([pP])\s*<\s*0\.001(?!\$)', r'$\1 < 0.001$', t)
    t = re.sub(r'(?<!\$)\b([pP])-values\b(?!\$)', r'$p$-values', t)
    t = re.sub(r'(?<!\$)\b([tT])-tests\b(?!\$)', r'$t$-tests', t)
    t = t.replace("~55-75%", r"$\sim$55--75\%")

    # Double quotes to LaTeX style: "something" -> ``something''
    t = re.sub(r'"([^"\n]+)"', r"``\1''", t)
    
    # Escape %, &, #, _ outside math mode ($...$)
    parts = t.split("$")
    for idx in range(0, len(parts), 2):
        seg = parts[idx]
        seg = re.sub(r'(?<!\\)%', r'\\%', seg)
        seg = re.sub(r'(?<!\\)&', r'\\&', seg)
        seg = re.sub(r'(?<!\\)#', r'\\#', seg)
        
        # Protect only commands whose arguments may contain underscores
        prot_bank = []
        def save_prot(m):
            prot_bank.append(m.group(0))
            return f"TOKENPROTUNDERSCORE{len(prot_bank)-1}END"
        seg = re.sub(r'\\(?:url|href|cite|ref|eqref|label|texttt)\{[^\}]*\}', save_prot, seg)
        
        # Escape remaining unescaped underscores
        seg = re.sub(r'(?<!\\)_', r'\\_', seg)
        
        # Restore protected commands
        for i in range(len(prot_bank)-1, -1, -1):
            seg = seg.replace(f"TOKENPROTUNDERSCORE{i}END", prot_bank[i])
        parts[idx] = seg
        
    t = "$".join(parts)
    
    # Restore protected tabular environments
    for i in range(len(tab_bank)-1, -1, -1):
        t = t.replace(f"TOKENTABULARPROT{i}END", tab_bank[i])
    
    # Fix any double $$ created by replacements like $$p < 0.001$$
    t = re.sub(r'\$\$([pP]\s*[><]\s*[0-9\.]+)\$\$', r'$\1$', t)
    
    return t

def extract_clean_text(seg: str):
    """Extracts fenced block or quote, separating English text from Chinese notes."""
    if not seg:
        return "", []
    # Check fenced code block
    fences = re.findall(r'```(?:txt|latex|tex)?\n(.*?)```', seg, re.DOTALL)
    if fences:
        non_fence = re.sub(r'```(?:txt|latex|tex)?\n(.*?)```', '', seg, flags=re.DOTALL).strip()
        cn_notes = [l.strip() for l in non_fence.split('\n') if l.strip()]
        return fences[0].strip(), cn_notes
    # Check blockquote
    quotes = re.findall(r'^(?:>\s?.*(?:\n|$))+', seg, re.MULTILINE)
    if quotes:
        lines = [re.sub(r'^>\s?', '', l) for l in quotes[0].split('\n')]
        non_q = seg.replace(quotes[0], '').strip()
        cn_notes = [l.strip() for l in non_q.split('\n') if l.strip()]
        return '\n'.join(lines).strip(), cn_notes
    # Check lines without Chinese
    lines = [l.strip() for l in seg.split('\n') if l.strip()]
    eng_lines = []
    cn_notes = []
    for l in lines:
        cn = re.findall(r'[\u4e00-\u9fff]', l)
        if len(cn) > 0:
            cn_notes.append(l)
        else:
            eng_lines.append(l)
    return '\n'.join(eng_lines).strip(), cn_notes

def parse_markdown_details():
    with open(DETAILS_MD, encoding="utf-8") as f:
        text = f.read()

    sections = re.split(r'\n(?=## )', text)
    data = {}

    for s in sections[1:]:
        lines = s.strip().split('\n')
        header = lines[0]
        m_id = re.search(r'##\s*(R[23]-\d+|Minor-\d+)', header)
        if not m_id:
            continue
        raw_id = m_id.group(1)
        if raw_id.startswith('Minor-'):
            num = int(raw_id.split('-')[1])
            cid = f'R3-minor-{num:02d}'
        else:
            cid = raw_id

        parts = re.split(r'\n(?=### )', s)
        orig_text = ''
        resp_text = ''
        mod_text = ''
        for p in parts:
            if p.startswith('### Original'):
                orig_text = p[len('### Original'):].strip()
            elif p.startswith('### Response'):
                resp_text = p[len('### Response'):].strip()
            elif p.startswith('### Modified in Manuscript'):
                mod_text = p[len('### Modified in Manuscript'):].strip()

        # Separate audit notes (**核查提示：**)
        audit_notes = []
        clean_resp_lines = []
        for line in resp_text.split('\n'):
            if '核查提示：' in line:
                audit_notes.append(line.replace('**核查提示：**', '').strip())
            else:
                clean_resp_lines.append(line)
        clean_resp = '\n'.join(clean_resp_lines).strip()

        # Parse modifications
        mods = []
        if mod_text:
            blocks = re.split(r'\n(?=######\s*修改|####\s*G4\s*修改|#####\s*)', mod_text)
            for b in blocks:
                if not re.search(r'(?:Revised|Original|原文|建议替换为|建议替换|替换为)', b, re.IGNORECASE):
                    continue
                loc_m = re.search(r'[-–•]?\s*位置[：:]\s*(.*?)(?:\n|$)', b)
                line_m = re.search(r'[-–•]?\s*TeX\s*行号[：:]\s*(.*?)(?:\n|$)', b)
                loc = loc_m.group(1).strip() if loc_m else ''
                line_no = line_m.group(1).strip() if line_m else ''
                
                # Check for special figure update
                if 'revised-1029-fig1.pdf' in b:
                    mods.append({
                        'loc_raw': 'Figure 1',
                        'line_raw': '',
                        'location': 'Figure 1 Caption and Schematic',
                        'orig': 'Fig. 1 legend: "Just Add It"',
                        'rev': 'We have updated Figure 1 (revised-1029-fig1.pdf) by replacing the informal label ``Just Add It\'\' with ``Element-wise Addition\'\' to accurately depict the underlying mathematical operation.',
                        'notes': ['替换为 revised-1029-fig1.pdf']
                    })
                    continue

                p_orig = re.search(r'(?:(?:\*\*Original\*\*|Original|原文)[：:]?)(.*?)(?=(?:\*\*Revised\*\*|Revised|建议替换为|建议|替换为|#####|####)[：:]?|\Z)', b, re.DOTALL)
                p_rev = re.search(r'(?:(?:\*\*Revised\*\*|Revised|建议替换为|建议|替换为)[：:]?)(.*?)(?=(?:修改理由|说明|状态|修改原因|#####|####)[：:]?|\Z)', b, re.DOTALL)

                orig_raw = p_orig.group(1).strip() if p_orig else ''
                rev_raw = p_rev.group(1).strip() if p_rev else ''

                clean_orig, notes_o = extract_clean_text(orig_raw)
                clean_rev, notes_r = extract_clean_text(rev_raw)

                # Collect any trailing notes
                notes = []
                p_note = re.search(r'(?:(?:修改理由|说明|状态|修改原因)[：:]?)(.*)', b, re.DOTALL)
                if p_note:
                    n_lines = [l.strip() for l in p_note.group(1).strip().split('\n') if l.strip()]
                    notes.extend(n_lines)
                notes.extend(notes_o)
                notes.extend(notes_r)

                if clean_rev or clean_orig or loc:
                    norm_loc = clean_location(loc, line_no)
                    mods.append({
                        'loc_raw': loc,
                        'line_raw': line_no,
                        'location': norm_loc,
                        'orig': clean_orig,
                        'rev': clean_rev,
                        'notes': notes
                    })

        data[cid] = {
            'raw_id': raw_id,
            'original': orig_text,
            'response': clean_resp,
            'audit_notes': audit_notes,
            'mods': mods
        }

    return data

def build_major_latex_block(cid: str, english_topic: str, entry: dict) -> str:
    orig = clean_latex(entry['original'])
    resp = clean_latex(entry['response'])
    
    out = [f"\\subsection*{{{cid}: {english_topic}}}"]
    out.append(f"\\revcomment{{{cid}}}{{{orig}}}\n")
    out.append(f"\\response{{\n{resp}\n}}\n")
    
    # Audit notes as LaTeX comments
    for note in entry.get('audit_notes', []):
        out.append(f"% [Audit Note: {note}]")
    
    mods = entry.get('mods', [])
    valid_revs = [m for m in mods if m['rev']]
    
    if valid_revs:
        out.append("\n\\actiontaken{")
        out.append(r"We have revised the manuscript accordingly across the following sections:")
        out.append(r"\begin{itemize}[leftmargin=1.5em, itemsep=2pt]")
        seen_locs = set()
        for m in valid_revs:
            loc_label = m['location']
            if loc_label not in seen_locs:
                out.append(f"  \\item \\textbf{{{clean_latex(loc_label)}}}")
                seen_locs.add(loc_label)
        out.append(r"\end{itemize}")
        out.append("}\n")
        
        # Add changedtext for each revised snippet
        for m in valid_revs:
            rev = clean_latex(m['rev'])
            loc_label = clean_latex(m['location'])
            out.append(f"\\changedtext{{{loc_label}}}{{%\n{rev}%\n}}\n")
            for note in m.get('notes', []):
                out.append(f"% [Revision Note: {note}]")
    else:
        out.append("\n\\actiontaken{\nWe have carefully verified this point. No further manuscript text modifications were required beyond clarifying the discussion.\n}\n")
        
    return "\n".join(out)

def build_minor_latex_block(cid: str, english_topic: str, entry: dict) -> str:
    orig = clean_latex(entry['original'])
    resp = clean_latex(entry['response'])
    
    out = [f"\\minorcomment{{{cid}}}{{{english_topic}}}{{{orig}}}{{%"]
    out.append(f"{resp}%\n}}")
    
    for note in entry.get('audit_notes', []):
        out.append(f"% [Audit Note: {note}]")
        
    mods = entry.get('mods', [])
    valid_revs = [m for m in mods if m['rev']]
    for m in valid_revs:
        rev = clean_latex(m['rev'])
        loc_label = clean_latex(m['location'])
        out.append(f"\\changedtext{{{loc_label}}}{{%\n{rev}%\n}}")
        for note in m.get('notes', []):
            out.append(f"% [Revision Note: {note}]")
            
    return "\n".join(out)

def main():
    data = parse_markdown_details()
    print(f"Loaded {len(data)} detailed entries from markdown.")

    # 1. Update 02_reviewer2.tex
    r2_file = os.path.join(SECTIONS_DIR, "02_reviewer2.tex")
    with open(r2_file, encoding="utf-8") as f:
        r2_content = f.read()

    r2_blocks = re.split(r'\n(?=\\subsection\*\{R2-)', r2_content)
    new_r2_blocks = [r2_blocks[0]] # header
    
    r2_updated = 0
    for b in r2_blocks[1:]:
        m = re.search(r'\\subsection\*\{(R2-\d+)', b)
        if m:
            cid = m.group(1)
            if cid in data:
                topic = R2_TOPICS.get(cid, cid)
                new_b = build_major_latex_block(cid, topic, data[cid])
                new_r2_blocks.append(new_b)
                r2_updated += 1
                continue
        new_r2_blocks.append(b)

    with open(r2_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_r2_blocks).strip() + "\n")
    print(f"Updated 02_reviewer2.tex: {r2_updated} of 12 entries updated.")

    # 2. Update 03_reviewer3_major.tex
    r3m_file = os.path.join(SECTIONS_DIR, "03_reviewer3_major.tex")
    with open(r3m_file, encoding="utf-8") as f:
        r3m_content = f.read()

    r3m_blocks = re.split(r'\n(?=\\subsection\*\{R3-)', r3m_content)
    new_r3m_blocks = [r3m_blocks[0]]
    
    r3m_updated = 0
    for b in r3m_blocks[1:]:
        m = re.search(r'\\subsection\*\{(R3-\d+)', b)
        if m:
            cid = m.group(1)
            if cid in data:
                topic = R3_MAJOR_TOPICS.get(cid, cid)
                new_b = build_major_latex_block(cid, topic, data[cid])
                new_r3m_blocks.append(new_b)
                r3m_updated += 1
                continue
        new_r3m_blocks.append(b)

    with open(r3m_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_r3m_blocks).strip() + "\n")
    print(f"Updated 03_reviewer3_major.tex: {r3m_updated} of 2 entries updated.")

    # 3. Update 04_reviewer3_minor.tex
    r3min_file = os.path.join(SECTIONS_DIR, "04_reviewer3_minor.tex")
    with open(r3min_file, encoding="utf-8") as f:
        r3min_content = f.read()

    r3min_blocks = re.split(r'\n(?=\\minorcomment\{R3-minor-)', r3min_content)
    new_r3min_blocks = [r3min_blocks[0]]

    r3min_updated = 0
    for b in r3min_blocks[1:]:
        m = re.search(r'\\minorcomment\{(R3-minor-\d+)', b)
        if m:
            cid = m.group(1)
            if cid in data:
                topic = R3_MINOR_TOPICS.get(cid, cid)
                new_b = build_minor_latex_block(cid, topic, data[cid])
                new_r3min_blocks.append(new_b)
                r3min_updated += 1
                continue
        new_r3min_blocks.append(b)

    with open(r3min_file, "w", encoding="utf-8") as f:
        f.write("\n\n".join(new_r3min_blocks).strip() + "\n")
    print(f"Updated 04_reviewer3_minor.tex: {r3min_updated} of 19 entries updated.")

if __name__ == "__main__":
    main()
