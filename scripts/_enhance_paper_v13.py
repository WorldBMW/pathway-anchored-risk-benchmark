# -*- coding: utf-8 -*-
"""Manuscript_CMPB_v12 -> v13：用现有 results 数据增强，冲击二区

不新增实验，只把 results/ 中已存在但论文未使用的显著证据补进去：
  A) 主队列 CIN 分级 Kruskal p=0.0048 / 亚型 p=0.0195 / Dunn 正常vs癌 p_adj=0.011
  B) E_cohort 跨癌种病因学阴性对照（乳腺0.335 卵巢0.057 前列腺0.030 TNBC0.016）
  C) 样本级留一交叉验证（Moran's I 均值 0.700）
  D) GSE316098 队列内亚组/批次结构 —— 诚实报告，避免过度声称
全部数值均直接取自 results/*.json 与 _paper_numbers.json
"""
import copy
import shutil
import docx

SRC = r"F:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\Manuscript_CMPB_v12_中文版.docx"
DST = r"F:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\Manuscript_CMPB_v13_中文版.docx"

shutil.copyfile(SRC, DST)
d = docx.Document(DST)
log = []


def set_text(p, new):
    if not p.runs:
        return False
    p.runs[0].text = new
    for r in p.runs[1:]:
        r.text = ""
    return True


def find_one(key):
    for i, p in enumerate(d.paragraphs):
        if key in p.text:
            return i
    print("  !! 未找到锚点:", key[:45])
    return None


def insert_after(idx, text):
    """在 idx 段之后插入一段，格式复制自 idx 段"""
    src = d.paragraphs[idx]
    new_p = copy.deepcopy(src._p)
    src._p.addnext(new_p)
    para = docx.text.paragraph.Paragraph(new_p, src._parent)
    set_text(para, text)
    return para


# ============ A) §3.1 补入分级/亚型统计证据 ============
i = find_one("进展单调性检验：Normal → HSIL → Carcinoma")
if i is not None:
    insert_after(i,
        "风险分数与病理严重程度的一致性检验：按 CIN 分级分组（grade 0 正常 n=31、grade 3 HSIL n=1、"
        "grade 4 癌 n=3），Kruskal–Wallis 检验显示组间差异显著（H = 7.97，p = 0.0048）；"
        "按组织学亚型分组检验亦显著（H = 5.45，p = 0.0195）。Dunn 事后检验经 Bonferroni 校正后，"
        "正常与癌之间差异显著（z = −2.91，p_adj = 0.011）；正常外宫颈与鳞癌的 Mann–Whitney 检验在"
        "5 重比较校正后仍显著（p_raw = 0.004，p_adj = 0.020）。均值风险随严重程度单调上升："
        "正常 0.001 → HSIL 1.160 → 癌 1.903。需注意 HSIL 与癌之间差异不显著（p_adj = 1.000），"
        "符合二者在生物学上的连续性；且各亚组样本量极小（HSIL n=1、腺癌 n=1），"
        "上述检验应结合 LODO 与消融证据综合解读。该组检验为本框架提供了独立于 AUC 的"
        "统计显著性支撑——相较之下，疾病/正常 AUC 虽为 1.000，但受 n_pos=4 限制未能达到"
        "统计显著（DeLong p=0.212）。")
    log.append("§3.1 补入 CIN 分级/亚型 Kruskal 与 Dunn 事后检验（p=0.0048 / 0.0195 / 0.011，均显著）")

# ============ B) §3.5 补入跨癌种病因学阴性对照 ============
i = find_one("p53 通路 AUC 为 0.954，这一较高值有明确的生物学解释")
if i is not None:
    insert_after(i,
        "作为更强的特异性证据，进一步将同一表达分支应用于非 HPV 驱动的肿瘤 Visium 数据（各 1 例）："
        "乳腺浸润癌、卵巢癌、前列腺癌与三阴性乳腺癌（TNBC）的 HPV 通路预测 AUC 分别为 0.335、0.057、"
        "0.030 与 0.016，均接近或低于随机水平，而宫颈队列为 0.991（表 6）。"
        "由于这些癌种的致病机制与 HPV 无关，模型在其上几乎无法预测 HPV 通路活性，"
        "表明所捕获的是 HPV 特异性信号，而非泛肿瘤增殖或组织结构的通用程序。"
        "该「跨癌种病因学对照」较无关通路对照（Wnt、血管生成）更具判别力——"
        "后两者的中等 AUC（0.790、0.731）可能部分源于通路与上皮/基质组成的共性，"
        "而跨癌种对照直接锚定于 HPV 病因学，且效应量差异极大（0.991 vs 0.016–0.335）。")
    log.append("§3.5 补入跨癌种病因学阴性对照（乳腺0.335/卵巢0.057/前列腺0.030/TNBC0.016）")

# ============ B2) 扩展表 6（表索引 5）：加 4 行跨癌种对照 ============
try:
    t6 = d.tables[5]
    rows = [
        ("乳腺浸润癌（跨癌种对照）", "病因学阴性对照", "0.335"),
        ("卵巢癌（跨癌种对照）", "病因学阴性对照", "0.057"),
        ("前列腺癌（跨癌种对照）", "病因学阴性对照", "0.030"),
        ("三阴性乳腺癌（跨癌种对照）", "病因学阴性对照", "0.016"),
    ]
    for name, role, auc in rows:
        r = t6.add_row()
        for c, val in zip(r.cells, (name, role, auc)):
            for p in c.paragraphs:
                if p.runs:
                    p.runs[0].text = val
                    for rr in p.runs[1:]:
                        rr.text = ""
                else:
                    c.text = val
                break
    log.append("表 6 扩展 4 行跨癌种对照")
except Exception as e:
    print("  表6扩展失败:", e)

# ============ C) §3.2 补入样本级留一交叉验证 ============
i = find_one("CA_HPV_2 为队列中唯一腺癌，模型 Top DEGs 均为鳞状谱系标志物")
if i is not None:
    insert_after(i,
        "补充验证：另执行样本级留一交叉验证（spot 级留出，4 个带标签样本各留一次），"
        "留出样本的 Moran's I 为 0.605–0.780（均值 0.700；CA_HPV_1 0.780、HSIL_HPV 0.772、"
        "CA_HPV_2 0.643、N_HPV 0.605），表明在未参与训练的样本上仍能维持空间结构。"
        "该值低于全数据主实验（0.866），符合留出样本可用信息减少的预期，"
        "且与 LODO 结果共同说明空间一致性并非对训练样本的过拟合。")
    log.append("§3.2 补入样本级留一交叉验证（Moran's I 均值 0.700）")

# ============ D) §3.7 诚实报告 GSE316098 队列内亚组结构 ============
i = find_one("本模型捕获的是 HPV 驱动的上皮异常信号而非临床预后风险")
if i is not None:
    t = d.paragraphs[i].text
    add = (" 进一步按患者内配对比较（44 例同时含两种模式区段的患者）得到一致方向"
           "（配对 t 检验 p = 0.0011，Wilcoxon 符号秩 p = 0.0033，Cohen's d_z = 0.53）。"
           "但须谨慎解读：该差值与患者编号存在中等强度相关（Spearman ρ = 0.615，p < 0.001），"
           "按编号前半段（001–022，n=22）与后半段（023–046，n=22）分层后，均值差分别为 −0.17 与 +2.49"
           "（两段差异 p = 3×10⁻⁵），提示队列内存在亚组/批次结构。由于公开元数据未提供批次信息，"
           "该混杂无法在本数据中完全排除，故 Silva 模式间的风险差异应视为需独立队列验证的"
           "探索性发现；本外部验证的核心价值在于证实通路锚定表达分支可跨平台（Visium→GeoMx）"
           "与跨亚型（鳞癌训练→腺癌验证）迁移，而非 Silva 模式的效应量估计。")
    if "患者内配对" not in t:
        set_text(d.paragraphs[i], t.rstrip() + add)
        log.append("§3.7 诚实报告队列内亚组/批次混杂（ρ=0.615），避免过度声称")

# ============ E) §4.4 新增局限性：GSE316098 亚组结构 ============
i = find_one("（6）腺癌泛化能力有限")
if i is not None:
    insert_after(i,
        "（7）外部验证队列的内部异质性：GSE316098 中 Silva 模式为区段级标注"
        "（49 例患者中 44 例同时含两种模式区段），风险差值与患者编号存在中等强度相关"
        "（Spearman ρ = 0.615），分层后前后两段效应方向不一致（−0.17 vs +2.49）。"
        "公开元数据缺少批次与临床分期信息，该混杂无法完全排除，"
        "因此 Silva 模式区分结果仅作探索性证据，需具备完整批次注释的独立队列验证。")
    log.append("§4.4 补入局限性 (7) GSE316098 队列内部异质性")

# ============ F) 摘要更新：加入显著统计证据 ============
i = find_one("结果：在 35 例公开样本（31 正常 + 4 疾病）上")
if i is not None:
    t = d.paragraphs[i].text
    if "Kruskal" not in t:
        t2 = t.replace(
            "30-seed 随机基因集对照证实 KEGG HPV 基因集 Moran's I 显著高于随机（p=0.032）。",
            "风险分数随病理严重程度单调上升（正常 0.001 → HSIL 1.160 → 癌 1.903），"
            "CIN 分级间差异显著（Kruskal–Wallis p=0.0048），正常与癌的 Dunn 事后检验"
            "经 Bonferroni 校正后仍显著（p_adj=0.011），为框架提供了独立于 AUC 的统计支撑。"
            "30-seed 随机基因集对照证实 KEGG HPV 基因集 Moran's I 显著高于随机（p=0.032）。")
        t2 = t2.replace(
            "HPV 通路内部一致性 AUC 因",
            "跨癌种病因学对照显示，同一表达分支在乳腺（0.335）、卵巢（0.057）、前列腺（0.030）"
            "与三阴性乳腺癌（0.016）等非 HPV 驱动肿瘤上的 HPV 通路 AUC 接近随机，"
            "而宫颈队列为 0.991，证实所捕获信号的 HPV 病因学特异性。"
            "HPV 通路内部一致性 AUC 因")
        set_text(d.paragraphs[i], t2)
        log.append("摘要补入 Kruskal/Dunn 显著证据与跨癌种特异性")

# ============ G) 结论更新 ============
i = find_one("本文提出通路锚定的小样本多模态框架，仅基于 4 例公开宫颈疾病 ST 样本")
if i is not None:
    t = d.paragraphs[i].text
    if "Kruskal" not in t:
        t2 = t.replace(
            "NO-IMAGE 消融证实图像分支对空间一致性（Moran's I +0.105）和进展排序"
            "（Kendall p 从显著变为不显著）的独立贡献，",
            "风险分数随病理分级单调上升且组间差异显著（Kruskal–Wallis p=0.0048，"
            "正常 vs 癌 Dunn p_adj=0.011），NO-IMAGE 消融证实图像分支对空间一致性"
            "（Moran's I +0.105）和进展排序（Kendall p 从显著变为不显著）的独立贡献，")
        set_text(d.paragraphs[i], t2)
        log.append("结论补入分级显著性证据")

d.save(DST)
print("\n=== v13 增强完成 ===")
for x in log:
    print("  [OK]", x)
print("\n已保存:", DST)
