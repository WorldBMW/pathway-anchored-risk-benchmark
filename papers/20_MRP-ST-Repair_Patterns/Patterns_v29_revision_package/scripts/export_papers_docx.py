# -*- coding: utf-8 -*-
"""
export_papers_docx.py
按照 Elsevier 期刊标准 Word 版本要求，把 papers/ 下 5 本期刊的：
  中文论文(可复制粘贴进Word).md → Word标准版本_投稿论文_<期刊缩写>_v1.docx
并为每本期刊同步生成：
  - CoverLetter_投稿信_<期刊缩写>_v1.docx
  - TitlePage_标题页_<期刊缩写>_v1.docx
  - Highlights_5条_<期刊缩写>_v1.txt（每条 ≤85 字符）
调用方式：
  python scripts/export_papers_docx.py
"""
import os, re, csv, json
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.section import WD_SECTION_START, WD_ORIENT
from docx.enum.table import WD_ALIGN_VERTICAL, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent.parent
PAPERS = ROOT / 'papers'

# 期刊元信息（与 gen_paper_bundle.py 完全一致）
JOURNALS = [
    {'id':'01','zh':'计算机方法与生物医学程序','en':'Computer Methods and Programs in Biomedicine','abbr':'CMPB',
     'if_':'IF6.4','zone':'CAS_MED_Z2','rank':'综合性价比第一，建议优先投稿'},
    {'id':'02','zh':'生物医学信号处理与控制','en':'Biomedical Signal Processing and Control','abbr':'BSPC',
     'if_':'IF5.7','zone':'CAS_MED_Z2','rank':'审稿速度第一，口碑快(1.5-3月)'},
    {'id':'03','zh':'生物学与医学中的计算机','en':'Computers in Biology and Medicine','abbr':'CBM',
     'if_':'IF6.3','zone':'CAS_MED_Z2','rank':'录取率11%，IF稍高'},
    {'id':'04','zh':'国际医学信息学杂志','en':'International Journal of Medical Informatics','abbr':'IJMI',
     'if_':'IF5.4','zone':'CAS_MED_Z2','rank':'医学信息学口碑最佳'},
    {'id':'05','zh':'癌症流行病学','en':'Cancer Epidemiology','abbr':'CancerEpi',
     'if_':'IF4.9','zone':'CAS_ONCO_Z2','rank':'临床肿瘤+HPV主题最对口'},
]

J_ABBREV = {j['id']:j['abbr'] for j in JOURNALS}
J_ABBR_RANK = {j['id']:j['rank'] for j in JOURNALS}
J_ABBR_IF = {j['id']:j['if_'] for j in JOURNALS}
J_ABBR_ZONE = {j['id']:j['zone'] for j in JOURNALS}
J_ABBR_EN = {j['id']:j['en'] for j in JOURNALS}
J_ABBR_ZH = {j['id']:j['zh'] for j in JOURNALS}


# ------------------------------------------------------------
# Word 样式工具函数（字体/段落/行距/页边距）
# ------------------------------------------------------------
def set_cn_font(run, cn='宋体', en='Times New Roman', size=12, bold=False, italic=False, color=None):
    run.font.name = en
    run._element.rPr.rFonts.set(qn('w:eastAsia'), cn)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color: run.font.color.rgb = RGBColor(*color)

def set_para_format(p, align=WD_ALIGN_PARAGRAPH.JUSTIFY, first_line_cm=None, space_before=0, space_after=0, line_spacing=1.5):
    pf = p.paragraph_format
    pf.alignment = align
    if first_line_cm is not None: pf.first_line_indent = Cm(first_line_cm)
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line_spacing

def add_newline_paragraph(doc, n=1):
    for _ in range(n):
        p = doc.add_paragraph('')
        set_para_format(p, space_before=0, space_after=0)

def add_heading_with_style(doc, text, level):
    p = doc.add_heading(level=level)
    r = p.add_run(text)
    size_map = {1: 16, 2: 14, 3: 12, 4: 12}
    set_cn_font(r, size=size_map.get(level,12), bold=True, color=(0,0,0))
    return p

def read_md_lines(path):
    return path.read_text(encoding='utf-8').splitlines()

def read_csv_rows(path):
    rows = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        reader = csv.reader(f)
        for r in reader: rows.append(r)
    return rows

def add_table_from_csv(doc, csv_path, caption):
    if not csv_path.exists():
        p = doc.add_paragraph(f'[WARN] 找不到表格素材：{csv_path.name}')
        set_para_format(p)
        return None, 0
    rows = read_csv_rows(csv_path)
    if not rows: return None, 0
    cap = doc.add_paragraph()
    cr = cap.add_run(caption)
    set_cn_font(cr, size=11, bold=True, color=(0,0,0))
    set_para_format(cap, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=6, space_after=2)
    cols = max(len(r) for r in rows)
    for r in rows:
        while len(r) < cols: r.append('')
    t = doc.add_table(rows=len(rows), cols=cols)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    header_pass = True
    for ri, row in enumerate(rows):
        for ci, cell_text in enumerate(row):
            cell = t.cell(ri, ci)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            cell.text = ''  # 先清空默认段落
            p = cell.paragraphs[0]
            run = p.add_run(str(cell_text))
            set_cn_font(run, size=10.5, bold=(ri==0))
            # PASS/FAIL 简单高亮
            is_pass = '✅' in str(cell_text) or str(cell_text).strip() == 'PASS'
            is_fail = '❌' in str(cell_text) or 'FAIL' in str(cell_text) or 'CHECK' == str(cell_text).strip()
            if ri == 0:
                # 表头浅灰底
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:fill'), 'D9E1F2')
                tcPr.append(shd)
            if is_pass:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:fill'), 'E2EFDA')
                tcPr.append(shd)
            elif is_fail:
                tcPr = cell._tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:val'), 'clear')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:fill'), 'FCE4D6')
                tcPr.append(shd)
    add_newline_paragraph(doc, 1)
    return t, len(rows) - 1

def add_figure_placeholder(doc, fig_caption, width_cm=17.0, height_cm=8.5, note=None):
    """添加一个 Figure 占位（文本框提示用户粘贴图片，宽度=双栏宽度17cm，高度8.5cm）"""
    cap = doc.add_paragraph()
    r = cap.add_run(fig_caption)
    set_cn_font(r, size=11, bold=True, color=(0,0,0))
    set_para_format(cap, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=8, space_after=2)

    # 1×1 表做一个浅灰底占位框（比 Word 图形框更兼容）
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.style = 'Table Grid'
    cell = t.cell(0, 0)
    cell.width = Cm(width_cm)
    # 行高设置
    tr = t.rows[0]._tr
    trPr = tr.get_or_add_trPr()
    trHeight = OxmlElement('w:trHeight')
    trHeight.set(qn('w:val'), str(int(height_cm * 567)))  # 1 cm ≈ 567 twips
    trHeight.set(qn('w:hRule'), 'exact')
    trPr.append(trHeight)
    tcPr = cell._tc.get_or_add_tcPr()
    tcW = OxmlElement('w:tcW')
    tcW.set(qn('w:w'), str(int(width_cm * 567)))
    tcW.set(qn('w:type'), 'dxa')
    tcPr.append(tcW)
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), 'F2F2F2')
    tcPr.append(shd)
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    cell.text = ''
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run('【图片占位：请在此粘贴对应 Figure 图像（300 dpi TIFF/EPS，双栏 17 cm）】')
    set_cn_font(run, size=11, color=(0x80,0x80,0x80), bold=True, italic=True)
    if note:
        p2 = cell.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r2 = p2.add_run(note)
        set_cn_font(r2, size=10, color=(0x60,0x60,0x60), italic=True)
    note_para = doc.add_paragraph()
    nr = note_para.add_run(f'图注(legend)写作处：请在此处用 ≤150 字英文详细描述该 Figure（最终投稿必须英文）。')
    set_cn_font(nr, size=10, italic=True, color=(0x60,0x60,0x60))
    set_para_format(note_para, space_before=2, space_after=4)
    add_newline_paragraph(doc, 1)

def apply_section_margins(section):
    # 标准：Elsevier 1 英寸上下边距，左右 2cm
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.header_distance = Cm(1.25)
    section.footer_distance = Cm(1.25)


# ------------------------------------------------------------
# Markdown → Word 主文档转换器
# ------------------------------------------------------------
def build_main_docx(j_dir, journal_id):
    abbr = J_ABBREV[journal_id]
    jif = J_ABBR_IF[journal_id]
    jz = J_ABBR_ZONE[journal_id]
    jname = f"{J_ABBR_EN[journal_id]} ({J_ABBR_ZH[journal_id]})｜{jif}｜{jz}"
    md_path = j_dir / '中文论文(可复制粘贴进Word).md'
    lines = read_md_lines(md_path)
    mat = j_dir / '素材'

    doc = Document()
    # ----- 初始节（Title Page 单独一节）-----
    sec0 = doc.sections[0]
    apply_section_margins(sec0)
    add_heading_with_style(doc, 'Title Page（标题页｜最终英文稿提交必须单独上传本页为独立文件 TitlePage.docx）', 1)
    add_newline_paragraph(doc, 2)

    # 期刊 + 稿件类型
    info_lines = [
        f'投稿期刊：{jname}',
        f'稿件类型：Original Research Article（原创研究论文）',
        f'语言版本：本文件为中文版写作底稿，翻译后将提交英文版',
        '',
    ]
    for t in info_lines:
        p = doc.add_paragraph()
        r = p.add_run(t if t else '')
        set_cn_font(r, size=12)
        set_para_format(p, space_before=0, space_after=2)

    # 标题
    title_zh = lines[2].lstrip('## ').strip() if len(lines) > 2 else '标题待替换'
    title_en = ''
    for i, l in enumerate(lines[3:20], start=3):
        if l.startswith('**') and l.endswith('**') and len(l) < 500:
            title_en = l.strip('*').strip()
            break
    tp = doc.add_paragraph()
    tr = tp.add_run('中文标题：' + title_zh)
    set_cn_font(tr, size=14, bold=True)
    set_para_format(tp, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=18, space_after=6)
    tep = doc.add_paragraph()
    ter = tep.add_run('English Title: ' + title_en)
    set_cn_font(ter, size=13, bold=True, cn='SimSun', en='Times New Roman')
    set_para_format(tep, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=18)

    # 作者 / 单位 / 通讯作者占位
    authors = doc.add_paragraph()
    ar = authors.add_run('作者姓名（按 ICMJE 规范排序，对应单位用上标 1/2/3 标注）：作者1¹，作者2¹²，作者3²*')
    set_cn_font(ar, size=12, bold=True)
    set_para_format(authors, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    aff = doc.add_paragraph()
    af = aff.add_run('¹ 单位一（科室/学院/医院，城市，邮编，国家）\n² 单位二（科室/学院/医院，城市，邮编，国家）\n* 通讯作者 Corresponding Author: E-mail: ___________________;  Tel: +86-___-_______')
    set_cn_font(af, size=11)
    set_para_format(aff, space_after=8)

    # Funding / COI / Ethics / Data / Short Title
    for label, placeholder in [
        ('Funding / 基金支持：', '【待回填：NSFC / 省基金 / 其他，含项目编号】'),
        ('Conflict of Interest / 利益冲突：', '作者声明无利益冲突（The authors declare no conflict of interest.）'),
        ('Ethics Approval / 伦理：', '本研究使用公开 ST 数据集与 TCGA-CESC 公共队列二次分析，符合无人类受试者风险伦理规范。'),
        ('Data Availability / 数据可用性：', '代码 scripts/ 与结果 results/ 均在项目根目录保存，投稿前上传 GitHub / Zenodo 获得 DOI。'),
        ('Short Title / 短标题（≤80 字符）：', 'HPV-Anchored ST Multitask Cervical Prognosis + TCGA HR=1.69'),
    ]:
        p = doc.add_paragraph()
        r1 = p.add_run(label)
        set_cn_font(r1, size=11, bold=True)
        r2 = p.add_run(placeholder)
        set_cn_font(r2, size=11)
        set_para_format(p, space_before=2, space_after=2)

    # ----- 主文节（新节）-----
    sec1 = doc.add_section(WD_SECTION_START.NEW_PAGE)
    apply_section_margins(sec1)
    add_heading_with_style(doc, 'Manuscript Main Body（主文正文｜英文版最终 Word 字数建议 ≤ 8000 words）', 1)

    # 遍历 md 正文行（跳过 投稿备忘头 + #标题页那段，从 Abstract 那行开始进入正文）
    start_idx = 0
    for i, l in enumerate(lines):
        if l.startswith('# 摘要（Abstract｜') or l.startswith('# 1. 引言（Introduction）'):
            start_idx = i
            break

    figure_slots = {}
    table_slots = {}

    def place_table(doc_internal, table_tag):
        # 根据 table_tag 选对应素材 CSV
        mapping = {
            'Table 1': mat/'table1_12pass.csv',
            'Table 2': mat/'table2_tcga_cox_summary.csv',
            'Table 3': mat/'table3_ablation_all7.csv',
            'Table 4': mat/'table4_baseline_vs_ours.csv',
        }
        if table_tag in mapping:
            csv_path = mapping[table_tag]
            cap = f'{table_tag}（数据来源：{csv_path.name}）'
            return add_table_from_csv(doc_internal, csv_path, cap)
        # 尝试模糊匹配
        for key, pth in mapping.items():
            if key in table_tag:
                return add_table_from_csv(doc_internal, pth, f'{table_tag}（数据来源：{pth.name}）')
        return None, 0

    def place_figure(doc_internal, fig_tag_plus_caption):
        # fig_tag_plus_caption = 整行例如: "Figure 3｜Suppl Fig ..."
        return add_figure_placeholder(
            doc_internal,
            fig_caption=fig_tag_plus_caption,
            note='用户可从素材 CSV + 现有 PNG（explain35_*/results_*）作图后粘到此框'
        )

    def add_md_paragraph(doc_internal, text):
        if not text.strip():
            add_newline_paragraph(doc_internal, 1)
            return
        p = doc_internal.add_paragraph()
        r = p.add_run(text)
        # 首行缩进 2 字符≈0.7cm
        set_cn_font(r, size=12)
        set_para_format(p, first_line_cm=0.7, space_before=0, space_after=0)

    for i in range(start_idx, len(lines)):
        line = lines[i].rstrip()
        if not line:
            add_newline_paragraph(doc, 1)
            continue
        # Markdown 标题
        m_h = re.match(r'^(#{1,6})\s+(.+)$', line)
        if m_h:
            level = min(len(m_h.group(1)), 4)
            text = m_h.group(2)
            add_heading_with_style(doc, text, level)
            continue
        # 有序/无序列表
        m_ul = re.match(r'^[-*]\s+(.+)$', line)
        m_ol = re.match(r'^(\d+)\.\s+(.+)$', line)
        if m_ul or m_ol:
            text = (m_ul.group(1) if m_ul else m_ol.group(2))
            prefix = '• ' if m_ul else f'{m_ol.group(1)}. '
            p = doc.add_paragraph()
            r0 = p.add_run(prefix)
            set_cn_font(r0, size=12, bold=False)
            r1 = p.add_run(text)
            set_cn_font(r1, size=12)
            set_para_format(p, first_line_cm=0.0, space_before=0, space_after=0)
            continue
        # Table x｜xxxx 占位 → 插入真实 CSV 表格
        m_tab = re.match(r'^Table\s*\d+.*｜.*$', line)
        if m_tab:
            tname = re.match(r'^Table\s*\d+', line).group(0) if re.match(r'^Table\s*\d+', line) else 'Table'
            place_table(doc, tname)
            # 表格 caption 行写在 caption 里了，正文里再把行文本写入说明段落（若 != caption 行默认）
            add_md_paragraph(doc, '正文描述：' + line)
            continue
        # Figure x｜xxxx 占位 → 插入图文框占位
        m_fig = re.match(r'^Figure\s*\d+.*｜.*$', line)
        if m_fig:
            place_figure(doc, line)
            continue
        # Suppl Figure S-x 也占位（可选）
        m_sfig = re.match(r'^Suppl\s+Figure\s+\S+.*：.*$', line)
        if m_sfig:
            add_figure_placeholder(doc, line, width_cm=16.5, height_cm=7.5,
                                  note='Suppl Figure 投稿前放 Suppl.zip，此处保留正文方便你写 legend')
            continue
        # 粗体 **xxx** → Word run 粗体
        if '**' in line:
            tokens = re.split(r'(\*\*[^*]+\*\*)', line)
            p = doc.add_paragraph()
            set_para_format(p, first_line_cm=0.7, space_before=0, space_after=0)
            for tok in tokens:
                if tok.startswith('**') and tok.endswith('**') and len(tok) >= 4:
                    inner = tok[2:-2]
                    r = p.add_run(inner)
                    set_cn_font(r, size=12, bold=True)
                else:
                    r = p.add_run(tok)
                    set_cn_font(r, size=12)
            continue
        # 普通段落
        add_md_paragraph(doc, line)

    # 字数统计段落（写在最后便于用户检查）
    doc.add_section(WD_SECTION_START.NEW_PAGE)
    secn = doc.sections[-1]
    apply_section_margins(secn)
    add_heading_with_style(doc, 'Submission Checklist（投稿检查清单｜中文版 Word 导出校验）', 1)
    ck_lines = [
        f'期刊：{J_ABBR_EN[journal_id]} ({abbr})，{jif} {jz}｜{J_ABBR_RANK[journal_id]}',
        '',
        '【字数控制】最终英文稿：Abstract ≤ 250 words；主文正文（不含参考文献/图注/Suppl）≤ 8000 words。',
        '【关键词】最终英文版关键词控制在 3–6 个；Elsevier Highlights 5 条每条 ≤ 85 字符。',
        '【字体/行距】中文：宋体 12pt（小四）；英文/数字：Times New Roman 12pt；1.5 行距；首行缩进 0.7cm；对齐方式：两端对齐。',
        '【页面设置】上下 1 inch；左右 2 cm；Elsevier 默认单栏排版（后续可在 Proof 时选择双栏 PDF 预览）。',
        '【表格】所有 Table 使用 Word 内置表格、每页一张；表头着色蓝/浅灰，PASS 绿色、FAIL 红色，便于审稿人一眼识别 PASS/FAIL。',
        '【图片】所有 Figure 在上传时需单独存为 ≥300dpi 的 TIFF/EPS，单栏 8.5cm / 双栏 17cm 宽度；本文中的灰色占位仅为写作时定位使用。',
        '【参考文献】使用 Zotero / EndNote 按 Vancouver 数字编号格式批量替换。',
        '',
        '【推荐审稿人（5 位，最终投稿系统填）：】',
        '① [临床 HPV 宫颈方向] 姓名 / 单位 / 邮箱 / 研究方向：宫颈癌 HPV 通路与预后（国际 HPV 协作组 / 国内妇科肿瘤团队）',
        '② [临床 HPV 宫颈方向] 姓名 / 单位 / 邮箱 / 研究方向：TCGA-CESC 生存分析 / CIN 自然史进展',
        '③ [ST 方法学] 姓名 / 单位 / 邮箱 / 研究方向：空间转录组 AI / 空间自相关 Moran I / 多任务学习',
        '④ [ST 方法学] 姓名 / 单位 / 邮箱 / 研究方向：可解释性 ST Saliency / 病理学家联合标注',
        '⑤ [医学信息学/流行病学] 姓名 / 单位 / 邮箱 / 研究方向：医学 AI 外部验证 / 流行病学 proxy signature',
    ]
    for t in ck_lines:
        if t == '':
            add_newline_paragraph(doc, 1)
        elif t.startswith('【推荐审稿人') or t.startswith('【字数') or t.startswith('期刊：'):
            p = doc.add_paragraph()
            r = p.add_run(t)
            set_cn_font(r, size=12, bold=True)
            set_para_format(p, first_line_cm=0, space_before=4, space_after=2)
        else:
            p = doc.add_paragraph()
            r = p.add_run(t)
            set_cn_font(r, size=11)
            set_para_format(p, first_line_cm=0, space_before=1, space_after=1)
    return doc


# ------------------------------------------------------------
# Cover Letter（投稿信）生成器
# ------------------------------------------------------------
def build_cover_letter(journal_id):
    abbr = J_ABBREV[journal_id]
    jname_en = J_ABBR_EN[journal_id]
    jname_zh = J_ABBR_ZH[journal_id]
    rank = J_ABBR_RANK[journal_id]
    doc = Document()
    apply_section_margins(doc.sections[0])

    pdate = doc.add_paragraph()
    set_para_format(pdate, align=WD_ALIGN_PARAGRAPH.RIGHT, space_before=0)
    rdate = pdate.add_run('Date: ________________（投稿日期填）')
    set_cn_font(rdate, en='Times New Roman', size=12)

    # Editor
    ped = doc.add_paragraph()
    set_para_format(ped, space_before=10, space_after=2)
    red = ped.add_run(
        f"The Editors-in-Chief\n{jname_en}\nDear Prof./Dr. Editors,"
    )
    set_cn_font(red, size=12)

    # Subject
    subj = doc.add_paragraph()
    set_para_format(subj, space_before=10, space_after=4)
    rs = subj.add_run('Subject: Submission of Original Research Article')
    set_cn_font(rs, size=12, bold=True)

    title_en = (
        "HPV Pathway-Anchored Multitask Learning for Prognostic Risk Stratification of Cervical "
        "Spatial Transcriptomics with External TCGA-CESC Survival Validation"
    )
    titlep = doc.add_paragraph()
    set_para_format(titlep, space_after=6)
    rt = titlep.add_run(f'Title: "{title_en}"')
    set_cn_font(rt, size=12, bold=True)

    # 正文 Cover Letter 中文底稿（用户翻英文）
    paragraphs = [
        f"We are submitting the above manuscript to be considered for publication as an Original Research Article in {jname_en}.",
        "",
        "本研究背景与临床意义：",
        "宫颈癌是全球女性第四大恶性肿瘤，高危 HPV 持续感染是核心驱动因素。尽管现有筛查与疫苗已显著降低发病率，CIN 到 SCC 的进展异质性仍缺少客观分层工具。空间转录组学（ST）可同时解析表达与位置，但目前 ST 预后工作普遍面临 3 大瓶颈：① HPV 通路先验未融入损失；② 小样本缺少多维质量体系；③ 缺少独立公共队列（TCGA-CESC 真实生存终点）的外部验证。",
        "",
        "本工作方法与创新（4 条）：",
        "(1) 提出 KEGG HPV 通路锚定的五目标多任务框架（λ_hpv=1.0 / λ_sup=5.0 / λ_prog=1.5 / λ_recon=0.2 / λ_neigh=0.3）；",
        "(2) 建立涵盖 12 项硬门槛的联合质量控制体系，主模型在 35 例宫颈 ST 队列上 12/12 全部通过；",
        "(3) 4 条 35 样本完整消融量化 HPV 通路约束与空间邻域的独立贡献；",
        "(4) 在 TCGA-CESC 独立 bulk RNA-seq 队列（n=302, 72 events）用 352 基因 HPV proxy 签名完成单变量 + 年龄校正 Cox 外部生存验证：Uni HR=1.69 p=0.029，年龄校正后 HR=1.69 p=0.029，均满足二区阈值 HR≥1.2 & p<0.05。",
        "",
        "稿件原创性与伦理声明：",
        "本稿件未在其他期刊投稿/接受/发表；所有作者同意提交；所有数据均来自公开 ST 队列与 TCGA-CESC 公共数据库，符合二次分析伦理，无利益冲突。推荐审稿人 5 位已在投稿系统中填写（见末尾清单）。",
        "",
        f"本期刊（{jname_zh}，{rank}）在方向上高度匹配本文：『{rank}』，因此诚挚邀请贵刊审稿团队审阅。若有返修意见，作者团队承诺在 10 个工作日内提交完整修订。",
        "",
        "Sincerely,",
        "Corresponding Author: ____________________",
        "Affiliation: ____________________",
        "Email: ____________________",
        "Tel / ORCID: ____________________",
    ]
    for line in paragraphs:
        if not line:
            add_newline_paragraph(doc, 1)
            continue
        p = doc.add_paragraph()
        r = p.add_run(line)
        set_cn_font(r, size=12)
        first_line = (0.7 if (len(line)>=2 and '\u4e00' <= line[0] <= '\u9fff'
                        and not line.startswith(('(1)','(2)','(3)','(4)','Dear ','We are','Sincerely','Corresponding','Affiliation','Email','Tel ','Subj','Title'))
                        and not line.startswith('The Editors')) else 0)
        set_para_format(p, space_before=0, space_after=2, first_line_cm=first_line)
    return doc


# ------------------------------------------------------------
# Title Page.docx（单独标题页）
# ------------------------------------------------------------
def build_title_page(journal_id):
    abbr = J_ABBREV[journal_id]
    jname = f"{J_ABBR_EN[journal_id]} ({J_ABBR_ZH[journal_id]})｜{J_ABBR_IF[journal_id]}｜{J_ABBR_ZONE[journal_id]}"
    doc = Document()
    apply_section_margins(doc.sections[0])

    p0 = doc.add_paragraph()
    set_para_format(p0, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=10)
    r0 = p0.add_run(f'Submission to {jname}')
    set_cn_font(r0, size=11, italic=True, color=(0x33,0x33,0x33))

    p1 = doc.add_paragraph()
    set_para_format(p1, align=WD_ALIGN_PARAGRAPH.CENTER, space_before=24, space_after=6)
    r1 = p1.add_run(
        'HPV Pathway-Anchored Multitask Learning for Prognostic Risk Stratification of Cervical Spatial Transcriptomics with External TCGA-CESC Survival Validation'
    )
    set_cn_font(r1, size=15, bold=True)

    p2 = doc.add_paragraph()
    set_para_format(p2, align=WD_ALIGN_PARAGRAPH.CENTER, space_after=20)
    r2 = p2.add_run('作者1¹，作者2¹²，作者3²*（等 __ 位作者，最终英文稿按 ICMJE 规范填写全部作者名单）')
    set_cn_font(r2, size=12, bold=True)

    for t in [
        '¹ 单位一：____________________',
        '² 单位二：____________________',
        '* Corresponding Author. E-mail: ____________________',
        '',
        'Short title (≤80 char): HPV-Anchored Cervical ST Multitask + TCGA HR=1.69',
        '',
        'Funding（基金）：____________________',
        'Conflict of Interest：The authors declare no conflict of interest.',
        'Ethics：Public ST/TCGA cohorts, retrospective algorithm validation; no human subjects risk.',
        'Data & Code Availability：Saved at project root (scripts/ + results/); GitHub/Zenodo DOI before submission.',
        '',
        'Word Count Manuscript：_______ words (不含 References / Figure legends / Suppl)',
        'Abstract word count：_______ words（Elsevier 结构化摘要 250 words 上限）',
        'Total Tables：4 (主文) + 1 (Suppl Table S1)；Total Figures：4 (主文) + 4 (Suppl Figures S1-S4)',
    ]:
        p = doc.add_paragraph()
        r = p.add_run(t)
        set_cn_font(r, size=12)
        set_para_format(p, space_before=1, space_after=2, first_line_cm=0)
    return doc


# ------------------------------------------------------------
# Highlights.txt（Elsevier 5 条，每条 ≤85 字符，中/英文各一份）
# ------------------------------------------------------------
def highlights_lines():
    zh = [
        '提出 HPV 通路锚定的五目标多任务宫颈空间转录组风险分层框架',
        '35 例宫颈队列 12 项硬门槛 MAIN_MODEL_PASS 全部 12/12 通过',
        'TCGA-CESC 302/72 事件外部验证：年龄校正 HR=1.69 p=0.029',
        '消融量化 HPV 通路约束与空间邻域在风险分层中的独立贡献',
        '3 例病例级解释可视化提供病理学家直观可解释证据',
    ]
    en = [
        'HPV pathway-anchored multitask cervical ST prognostic framework (5 objectives)',
        'All 12 quality gates PASS on a 35-case cervical ST cohort (MAIN_MODEL_PASS)',
        'TCGA-CESC external validation (n=302, 72 events): age-adjusted HR=1.69, p=0.029',
        'Ablations quantify independent contributions of HPV loss and spatial smoothness',
        'Three case-level explainable visualizations for pathologist usability',
    ]
    # 英文每条字符数必须 ≤85
    assert all(len(l) <= 85 for l in en), f'Highlights over 85 chars: {[len(l) for l in en]}'
    return zh, en


# ------------------------------------------------------------
# 主流程：遍历 5 本期刊 → 导出 docx / txt
# ------------------------------------------------------------
def export_one(j_dir, journal_id):
    abbr = J_ABBREV[journal_id]
    os.makedirs(j_dir, exist_ok=True)

    main_p = j_dir / f'Word标准版本_投稿论文_{abbr}_v1.docx'
    cl_p   = j_dir / f'CoverLetter_投稿信_{abbr}_v1.docx'
    tp_p   = j_dir / f'TitlePage_标题页_{abbr}_v1.docx'
    hi_p   = j_dir / f'Highlights_5条_{abbr}_v1.txt'

    main_doc = build_main_docx(j_dir, journal_id)
    main_doc.save(main_p)

    cl_doc = build_cover_letter(journal_id)
    cl_doc.save(cl_p)

    tp_doc = build_title_page(journal_id)
    tp_doc.save(tp_p)

    zh_l, en_l = highlights_lines()
    txt = f"# Elsevier Highlights（每条 ≤85 字符）\n"
    txt += f"期刊：{J_ABBR_EN[journal_id]} ({abbr})｜{J_ABBR_IF[journal_id]}｜{J_ABBR_ZONE[journal_id]}\n\n"
    txt += "## 中文版 Highlights（供作者确认含义；最终系统中请粘贴英文版）\n"
    for i, l in enumerate(zh_l, 1):
        txt += f"  H{i}. {l}\n"
    txt += "\n## 英文版 Highlights（提交到 Elsevier Editorial Manager 系统中使用，每条字符数统计如下）\n"
    for i, l in enumerate(en_l, 1):
        txt += f"  H{i}. (len={len(l):>2d}) {l}\n"
    # 额外加 85 字符上限提醒
    txt += "\nCHARACTER LIMIT CHECK: All ≤85 ✅\n"
    hi_p.write_text(txt, encoding='utf-8')

    return main_p, cl_p, tp_p, hi_p


def main():
    # 搜索 papers/ 下 5 本目录（用 id 前缀精确匹配）
    id_to_dir = {}
    for j_id in [j['id'] for j in JOURNALS]:
        cand = [p for p in PAPERS.iterdir() if p.is_dir() and p.name.startswith(j_id + '_')]
        if cand:
            id_to_dir[j_id] = cand[0]
    print(f'Found {len(id_to_dir)} / 5 journal dirs')
    total_files = []
    for j in JOURNALS:
        jid = j['id']
        if jid not in id_to_dir:
            print(f'[SKIP] {jid} {j["abbr"]} 目录不存在')
            continue
        files = export_one(id_to_dir[jid], jid)
        total_files.extend(files)
        print(f'[OK] {jid} {j["abbr"]}: {[f.name for f in files]}')
    print(f'TOTAL_EXPORTED_FILES = {len(total_files)}')


if __name__ == '__main__':
    main()
