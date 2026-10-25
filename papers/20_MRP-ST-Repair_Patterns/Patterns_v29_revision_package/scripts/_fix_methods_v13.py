# -*- coding: utf-8 -*-
"""v13 补充：方法章节与结果章节的对应关系
§2.5 补充分级/亚型统计检验；§2.6 补充跨癌种病因学对照与样本级留一交叉验证。
保证所有结果章节报告的检验，方法章节均有定义（二区审稿必查项）。
"""
import copy
import docx

DST = r"F:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\Manuscript_CMPB_v13_中文版.docx"
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
    print("  !! 未找到:", key[:45])
    return None


def insert_after(idx, text):
    src = d.paragraphs[idx]
    new_p = copy.deepcopy(src._p)
    src._p.addnext(new_p)
    para = docx.text.paragraph.Paragraph(new_p, src._parent)
    set_text(para, text)
    return para


# 确认 §3.10 仍在
i310 = find_one("3.10 TCGA-CESC 批量验证")
print("§3.10 状态:", "存在" if i310 is not None else "缺失！")

# ---- §2.5 补充分级/亚型统计检验 ----
i = find_one("次要指标：进展 Kendall's τ（置换 p 值，1000 次）、置换差异基因（FDR<0.05）、通路特异性 AUC。")
if i is not None:
    insert_after(i,
        "补充统计检验：为独立验证风险分数与病理严重程度的对应关系，"
        "按 CIN 分级（grade 0/3/4）与组织学亚型（正常外宫颈、N_HPV、HSIL、鳞癌、腺癌）分组，"
        "执行 Kruskal–Wallis 检验；组间差异显著时以 Dunn 检验做事后两两比较"
        "（Bonferroni 校正），并以 Mann–Whitney 检验做亚型两两比较（5 重比较 Bonferroni 校正）。"
        "由于疾病/正常 AUC 受 n_pos=4 限制统计功效不足（DeLong p=0.212），"
        "该组基于分级的秩和检验构成对「风险分数随病变严重程度上升」这一声称的主要统计支撑。")
    log.append("§2.5 补充 Kruskal–Wallis / Dunn 事后检验方法定义")

# ---- §2.6 补充跨癌种对照与样本级交叉验证 ----
i = find_one("随机基因集对照：30 个随机 108 基因集（种子 0–29），相同管线、相同损失、相同图像特征。")
if i is not None:
    insert_after(i,
        "跨癌种病因学对照：将主实验表达分支应用于非 HPV 驱动的肿瘤 Visium 数据"
        "（乳腺浸润癌、卵巢癌、前列腺癌、三阴性乳腺癌，各 1 例，来自 10× Genomics 公开样本），"
        "比较其 HPV 通路预测 AUC 与宫颈队列的差异。若模型捕获的是 HPV 特异性信号，"
        "则在病因学与 HPV 无关的癌种上该 AUC 应接近随机水平（0.5）或更低。"
        "该对照锚定于病因学，较无关通路（Wnt、血管生成）对照具有更强的判别力。"
        "样本级留一交叉验证：与 LODO（疾病级留出）互补，另执行 spot 级留一样本验证"
        "（4 个带标签样本各留一次，在其余样本上训练），报告留出样本的 Moran's I 与重构 MSE，"
        "用于检验空间一致性是否依赖对训练样本的过拟合。")
    log.append("§2.6 补充跨癌种病因学对照与样本级留一交叉验证的方法定义")

d.save(DST)
print("\n=== 方法章节补充完成 ===")
for x in log:
    print("  [OK]", x)
print("\n已保存:", DST)
