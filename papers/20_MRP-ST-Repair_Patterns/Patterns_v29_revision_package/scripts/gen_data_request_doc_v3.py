"""生成宫颈空间转录组研究数据需求清单 Word 文档（v3：医院无ST数据版）。

明确标注 ST .h5 数据缺失，策略调整为：ST 公开数据训练 + 医院 bulk/IHC 验证。
"""
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn


def set_cell_bg(cell, color_hex):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = tc_pr.makeelement(qn("w:shd"), {
        qn("w:val"): "clear",
        qn("w:color"): "auto",
        qn("w:fill"): color_hex,
    })
    tc_pr.append(shd)


def add_heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)
    return h


def add_para(doc, text, bold=False, size=11, color=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = color
    return p


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = h
        for p in cell.paragraphs:
            for run in p.runs:
                run.bold = True
                run.font.size = Pt(10)
                run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_bg(cell, "1F4E79")
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = str(val)
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(10)
    if col_widths:
        for j, w in enumerate(col_widths):
            for row in table.rows:
                row.cells[j].width = Cm(w)
    return table


def main():
    doc = Document()
    for section in doc.sections:
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)
        section.left_margin = Cm(2.5)
        section.right_margin = Cm(2.5)

    title = doc.add_heading("宫颈空间转录组多模态多任务学习研究\n数据需求清单（医院合作版）", level=0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x1F, 0x4E, 0x79)

    add_para(doc, "用途：向医大一院病理科/妇产科/信息科申请研究数据", size=10)
    add_para(doc, "研究方向：HPV 通路锚定的宫颈空间转录组基因表达-病理图像多模态多任务学习", size=10)
    add_para(doc, "拟投稿期刊：Computer Methods and Programs in Biomedicine (CMPB, Q2)", size=10)
    add_para(doc, "生成日期：2026-09-06", size=10)
    doc.add_paragraph()

    # ========== 重要声明 ==========
    add_heading(doc, "【重要声明】数据缺失与策略说明", level=1)
    warning = doc.add_paragraph()
    run = warning.add_run(
        "本研究核心技术为空间转录组（Spatial Transcriptomics, ST）分析。"
        "但经前期穷尽搜索，公开数据库中宫颈 ST 疾病样本仅 5 例"
        "（GSE208654 的 N_HPV/HSIL_HPV/CA_HPV_1/CA_HPV_2 + 10x 官方 human-cervical-cancer-1），"
        "无 CIN1/CIN2 中间态样本。\n"
        "贵院病理科目前无 10x Visium / Stereo-seq 等 ST 测序平台，"
        "无法提供 ST 原始 .h5 表达矩阵文件，且本研究无经费送样至商业公司完成 ST 测序。\n"
        "因此，本研究策略调整为："
        "【ST 公开数据训练模型】 + 【贵院 bulk RNA-seq / IHC / 临床数据独立验证】。\n"
        "贵院提供的数据将作为独立外部验证队列，用于验证 ST 模型学到的 HPV 通路基因签名"
        "在 bulk 层面的可转移性、预后价值及 HPV 分层能力。"
    )
    run.font.size = Pt(11)
    run.bold = True
    run.font.color.rgb = RGBColor(0xC0, 0x00, 0x00)
    doc.add_paragraph()

    # ========== 一、数据需求总览 ==========
    add_heading(doc, "一、数据需求总览（按优先级排序）", level=1)
    add_para(doc, "以下数据均用于独立外部验证，不涉及 ST 原始数据。")
    doc.add_paragraph()

    add_table(doc,
        ["序号", "数据类型", "来源科室", "优先级", "最小量", "理想量", "用途"],
        [
            ["1", "bulk RNA-seq 表达矩阵",
             "病理科+检验科/中心实验室", "★★★ 必选", "15例", "30例",
             "HPV通路签名验证、预后分析、HPV分层"],
            ["2", "匹配临床病理信息表",
             "病理科+妇产科+信息科", "★★★ 必选", "同bulk", "同bulk",
             "样本标注、生存分析、HPV分层"],
            ["3", "HPV 检测原始数据",
             "检验科+病理科", "★★ 建议", "同bulk", "同bulk",
             "HPV通路锚定生物学真实性验证"],
            ["4", "IHC 免疫组化结果",
             "病理科", "★★ 建议", "同bulk", "同bulk",
             "HPV通路蛋白水平验证（p16/Ki67等）"],
            ["5", "H&E 全玻片图像(WSI)",
             "病理科", "★ 加分", "同bulk", "同bulk",
             "形态学注释、可解释性分析"],
            ["6", "FFPE 石蜡块",
             "病理科", "★ 可选", "—", "—",
             "未来若有经费可送公司做ST（当前不涉及）"],
        ],
        col_widths=[1.0, 3.5, 3.2, 1.8, 1.2, 1.2, 4.1])
    doc.add_paragraph()

    # ========== 二、bulk RNA-seq ==========
    add_heading(doc, "二、bulk RNA-seq 表达矩阵 — 核心必选", level=1)

    add_heading(doc, "2.1 来源科室", level=2)
    add_para(doc, "• 病理科：组织取材、RNA 提取")
    add_para(doc, "• 检验科 / 中心实验室：测序（Illumina 平台）")
    add_para(doc, "• 信息科：表达矩阵导出")
    doc.add_paragraph()

    add_heading(doc, "2.2 样本要求", level=2)
    add_para(doc, "需宫颈不同疾病阶段的 bulk RNA-seq 数据，优先治疗前样本：")
    doc.add_paragraph()

    add_table(doc,
        ["疾病阶段", "CIN分级", "最小例数", "理想例数", "说明"],
        [
            ["正常宫颈 Normal", "0", "3", "8", "对照"],
            ["CIN1 / LSIL", "1", "2", "5", "中间态，关键"],
            ["CIN2", "2", "2", "5", "中间态，关键"],
            ["CIN3 / HSIL", "3", "2", "5", "当前公开数据仅1例"],
            ["浸润性鳞癌 SCC", "4", "3", "8", "当前公开数据2例"],
            ["浸润性腺癌 ADC", "4", "2", "5", "当前公开数据1例"],
            ["合计", "—", "14", "36", "含正常对照"],
        ],
        col_widths=[4.5, 2.0, 2.0, 2.0, 6.0])
    doc.add_paragraph()

    add_heading(doc, "2.3 数据格式要求", level=2)
    add_table(doc,
        ["数据项", "格式要求", "说明"],
        [
            ["表达矩阵", "gene × sample，CSV/TSV", "raw counts 或 TPM/FPKM 均可"],
            ["基因 ID", "Gene Symbol 或 Ensembl ID", "须可与 ST 基因对齐"],
            ["测序平台", "Illumina NovaSeq / HiSeq", "标准 RNA-seq"],
            ["质控报告", "FastQC / MultiQC", "比对率、基因检出数"],
            ["样本 ID", "sample_id 与临床表一致", "去标识化"],
        ],
        col_widths=[3.0, 5.0, 7.0])
    doc.add_paragraph()

    add_heading(doc, "2.4 数据用途与验证方案", level=2)
    add_table(doc,
        ["验证内容", "方法", "预期结果"],
        [
            ["HPV 通路签名预后价值",
             "ST 模型学到的 108 基因权重 × bulk 表达 → 风险分数 → Cox 生存分析",
             "HR > 1, p < 0.05，C-index > 0.6"],
            ["HPV+ vs HPV- 区分",
             "HPV 通路签名在 HPV+ 与 HPV- 样本间的表达差异检验",
             "HPV+ 组通路活性显著升高"],
            ["疾病进展趋势",
             "Normal→CIN1→CIN2→CIN3→SCC/ADC 的 Kendall τ 趋势检验",
             "τ > 0, p < 0.05"],
            ["HPV 分型分层",
             "按 HPV16/18/其他型别分组，比较通路签名差异",
             "高危型 (16/18) 通路活性更高"],
            ["ST 信号复现性",
             "比较 ST per-spot 风险分数与 bulk 风险分数的一致性",
             "验证空间信号在 bulk 平均中的保留程度"],
        ],
        col_widths=[3.5, 6.5, 5.0])
    doc.add_paragraph()

    # ========== 三、临床病理信息表 ==========
    add_heading(doc, "三、匹配临床病理信息表 — 核心必选", level=1)

    add_heading(doc, "3.1 来源科室", level=2)
    add_para(doc, "• 病理科：组织学亚型、CIN 分级、FIGO 分期、病理报告")
    add_para(doc, "• 妇产科：年龄、治疗状态、随访生存数据")
    add_para(doc, "• 检验科：HPV 检测结果")
    add_para(doc, "• 信息科：数据整合、去标识化、导出")
    doc.add_paragraph()

    add_heading(doc, "3.2 数据表字段明细", level=2)
    add_para(doc, "格式：CSV 或 Excel（UTF-8），每例一行，sample_id 须与 bulk RNA-seq 样本 ID 一致。")
    doc.add_paragraph()

    add_table(doc,
        ["字段名", "数据类型", "来源科室", "必选", "取值/说明"],
        [
            ["sample_id", "字符串", "信息科", "✅", "与 bulk RNA-seq 样本 ID 一致"],
            ["patient_id", "字符串", "信息科", "✅", "去标识化患者 ID"],
            ["age", "整数", "妇产科", "✅", "年龄（岁）"],
            ["histology_subtype", "枚举", "病理科", "✅", "Normal/LSIL/HSIL/SCC/ADC"],
            ["cin_grade", "0–4", "病理科", "✅", "0=正常,1=CIN1,2=CIN2,3=CIN3,4=浸润癌"],
            ["figo_stage", "枚举", "病理科", "⭕", "I/II/III/IV"],
            ["hpv_status", "+/-", "检验科", "✅", "HPV 阳性/阴性"],
            ["hpv_type", "字符串", "检验科", "⭕", "16/18/31/33/52/58/其他"],
            ["tissue_site", "枚举", "病理科", "⭕", "ectocervix/endocervix/transformation zone"],
            ["treatment_naive", "yes/no", "妇产科", "⭕", "是否治疗前样本（优先治疗前）"],
            ["os_months", "浮点数", "妇产科", "⭕", "总生存期（月）"],
            ["os_event", "0/1", "妇产科", "⭕", "1=死亡, 0=删失"],
            ["pfs_months", "浮点数", "妇产科", "⭕", "无进展生存期（月）"],
            ["pfs_event", "0/1", "妇产科", "⭕", "1=进展/死亡, 0=删失"],
            ["pathology_report", "文本", "病理科", "⭕", "病理报告摘要"],
        ],
        col_widths=[3.0, 1.8, 2.5, 1.2, 6.5])
    doc.add_paragraph()

    add_heading(doc, "3.3 字段用途", level=2)
    add_table(doc,
        ["用途", "用到的字段", "分析内容"],
        [
            ["样本标注", "histology_subtype, cin_grade", "进展趋势分组"],
            ["HPV 分层", "hpv_status, hpv_type", "HPV 通路锚定验证"],
            ["生存分析", "os_months, os_event", "Cox 比例风险模型"],
            ["预后分析", "pfs_months, pfs_event", "无进展生存分析"],
            ["多变量校正", "age, figo_stage", "年龄/分期校正 Cox"],
        ],
        col_widths=[3.0, 4.0, 8.0])
    doc.add_paragraph()

    # ========== 四、HPV 检测 ==========
    add_heading(doc, "四、HPV 检测原始数据 — 建议", level=1)

    add_heading(doc, "4.1 来源科室", level=2)
    add_para(doc, "• 检验科：HPV 分型 PCR、E6/E7 mRNA 检测")
    add_para(doc, "• 病理科：p16 IHC 免疫组化")
    doc.add_paragraph()

    add_heading(doc, "4.2 数据表与参数", level=2)
    add_table(doc,
        ["检测类型", "数据表/格式", "参数字段", "优先级"],
        [
            ["HPV 分型 PCR", "Excel/CSV",
             "sample_id, hpv_type, hpv_status, ct_value", "★★★"],
            ["HPV E6/E7 mRNA", "Excel/CSV",
             "sample_id, e6_expression, e7_expression, hpv_type", "★★★"],
            ["HPV DNA 载量", "Excel/CSV",
             "sample_id, viral_load(copies/μL), hpv_type", "★★"],
            ["p16 IHC", "扫描图像+报告",
             "sample_id, p16_score(0/1+/2+/3+), 染色图像", "★★"],
        ],
        col_widths=[3.0, 2.8, 7.0, 1.2])
    doc.add_paragraph()

    add_heading(doc, "4.3 用途", level=2)
    add_para(doc, "• 验证 HPV 通路锚定的生物学真实性：ST 模型学到的 HPV 通路签名是否与"
                  "实际 HPV 感染状态/病毒载量正相关")
    add_para(doc, "• 按 HPV 亚型（16/18/其他）分层，分析通路签名在不同型别间的差异")
    add_para(doc, "• p16 IHC 作为 HPV 感染的替代标志物，验证通路签名与 p16 表达的相关性")
    doc.add_paragraph()

    # ========== 五、IHC 免疫组化 ==========
    add_heading(doc, "五、IHC 免疫组化结果 — 建议", level=1)

    add_heading(doc, "5.1 来源科室", level=2)
    add_para(doc, "• 病理科：免疫组化染色、评分、图像采集")
    doc.add_paragraph()

    add_heading(doc, "5.2 检测项目（以下任一均可，越多越好）", level=2)
    add_table(doc,
        ["标志物", "生物学意义", "与本研究关联"],
        [
            ["p16", "HPV 感染替代标志物", "验证 HPV 通路锚定"],
            ["Ki67", "细胞增殖指数", "验证高风险区域的增殖活性"],
            ["p53", "肿瘤抑制基因", "HPV E6 降解 p53 的下游效应"],
            ["CK7/CK5/6", "鳞状/腺上皮标志物", "SCC vs ADC 分层"],
            ["CD8", "细胞毒性 T 细胞", "肿瘤免疫微环境"],
        ],
        col_widths=[2.5, 4.5, 8.0])
    doc.add_paragraph()

    add_heading(doc, "5.3 数据格式", level=2)
    add_para(doc, "• 染色评分表：sample_id, marker, score (0/1+/2+/3+ 或 H-score)")
    add_para(doc, "• 扫描图像（可选）：SVS/NDPI/TIFF 格式全玻片")
    doc.add_paragraph()

    # ========== 六、H&E WSI ==========
    add_heading(doc, "六、H&E 全玻片图像(WSI) — 加分项", level=1)

    add_heading(doc, "6.1 来源科室", level=2)
    add_para(doc, "• 病理科：切片制备、H&E 染色、全玻片扫描")
    doc.add_paragraph()

    add_heading(doc, "6.2 数据格式", level=2)
    add_table(doc,
        ["数据项", "参数/格式", "说明"],
        [
            ["来源", "与 bulk RNA-seq 同例组织的 H&E 切片", "保证组织区域对应"],
            ["格式", "SVS / NDPI / TIFF / MRXS", "标准 WSI 格式"],
            ["扫描倍率", "20× 或 40×", "—"],
            ["数量", "与 bulk 样本同例数", "—"],
            ["病理区域标注", "XML/JSON（如有）",
             "肿瘤区/基质区/免疫区/坏死区/正常区"],
        ],
        col_widths=[3.5, 5.0, 6.5])
    doc.add_paragraph()

    add_heading(doc, "6.3 用途", level=2)
    add_para(doc, "• 组织病理学注释，辅助解读 bulk RNA-seq 结果")
    add_para(doc, "• 模型可解释性分析（风险基因表达 × 病理形态对应关系）")
    doc.add_paragraph()

    # ========== 七、ST 数据缺失说明 ==========
    add_heading(doc, "七、ST 数据缺失专项说明", level=1)

    add_para(doc, "本节明确说明空间转录组（ST）数据的缺失情况及应对策略，供合作方参考。",
             bold=True, color=RGBColor(0xC0, 0x00, 0x00))
    doc.add_paragraph()

    add_table(doc,
        ["项目", "说明"],
        [
            ["所需 ST 数据",
             "10x Visium / Stereo-seq 空间转录组原始输出："
             "filtered_feature_bc_matrix.h5、tissue_hires_image.png、"
             "scalefactors_json.json、tissue_positions_list.csv"],
            ["贵院现状",
             "病理科无 ST 测序平台，无法提供 ST .h5 文件"],
            ["经费限制",
             "本研究无经费送样至商业公司（华大/诺禾/伯豪）完成 ST 测序"
             "（每例成本 1–2 万元）"],
            ["现有公开 ST 数据",
             "GSE208654（4例：N_HPV/HSIL_HPV/CA_HPV_1/CA_HPV_2）"
             "+ 10x human-cervical-cancer-1（1例 SCC），共 5 例疾病样本"],
            ["应对策略",
             "ST 公开数据用于模型训练；贵院 bulk RNA-seq + IHC + 临床数据"
             "用于独立外部验证"],
            ["局限性说明",
             "ST 训练队列疾病样本仅 5 例且无 CIN1/CIN2，"
             "模型的疾病进展梯度验证依赖贵院 bulk 队列的多阶段样本"],
        ],
        col_widths=[3.5, 11.5])
    doc.add_paragraph()

    # ========== 八、交付规格汇总 ==========
    add_heading(doc, "八、数据交付规格汇总", level=1)
    add_table(doc,
        ["数据项", "来源科室", "数量", "格式", "大小预估", "优先级"],
        [
            ["bulk RNA-seq", "病理科+检验科", "14–36 例", "表达矩阵 CSV", "50–200 MB", "★★★"],
            ["临床病理表", "病理科+妇产科+信息科", "1 份", "CSV/Excel", "<1 MB", "★★★"],
            ["HPV 检测", "检验科+病理科", "同 bulk 例数", "Excel/CSV", "<1 MB", "★★"],
            ["IHC 结果", "病理科", "同 bulk 例数", "Excel+图像", "1–10 GB", "★★"],
            ["H&E WSI", "病理科", "同 bulk 例数", "SVS/NDPI/TIFF", "50–200 GB", "★"],
        ],
        col_widths=[2.5, 3.5, 2.5, 2.5, 2.0, 1.5])
    doc.add_paragraph()

    # ========== 九、科室协同分工 ==========
    add_heading(doc, "九、各科室协同分工说明", level=1)
    add_table(doc,
        ["科室", "提供数据", "负责内容"],
        [
            ["病理科", "bulk RNA-seq 组织取材、IHC、H&E WSI、病理诊断",
             "组织取材、RNA 提取、IHC 染色、病理诊断、WSI 扫描"],
            ["妇产科", "年龄、治疗记录、随访生存数据",
             "患者入组、临床信息、随访"],
            ["检验科", "HPV 分型、E6/E7 mRNA、bulk RNA-seq 测序",
             "HPV 检测、RNA 提取、测序"],
            ["中心实验室", "bulk RNA-seq（如无检验科）",
             "测序与质控"],
            ["信息科", "数据整合、去标识化、导出",
             "数据脱敏、格式转换、伦理合规"],
        ],
        col_widths=[3.0, 5.5, 6.5])
    doc.add_paragraph()

    # ========== 十、伦理与隐私 ==========
    add_heading(doc, "十、伦理与隐私说明", level=1)
    add_para(doc, "1. 所有数据严格去标识化，不含患者姓名、身份证号、住院号等直接标识符。")
    add_para(doc, "2. 仅用于学术研究，不用于商业用途。")
    add_para(doc, "3. 数据存储于加密服务器，访问受密码与权限控制。")
    add_para(doc, "4. 可配合提交伦理审查申请材料。")
    doc.add_paragraph()

    # ========== 十一、联系方式 ==========
    add_heading(doc, "十一、联系方式", level=1)
    add_para(doc, "申请人：________________________")
    add_para(doc, "单位：________________________")
    add_para(doc, "邮箱：________________________")
    add_para(doc, "电话：________________________")
    add_para(doc, "日期：2026 年 9 月 6 日")

    out = r"f:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\数据需求清单_医院合作_v3.docx"
    doc.save(out)
    print(f"Saved -> {out}")


if __name__ == "__main__":
    main()
