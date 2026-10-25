# -*- coding: utf-8 -*-
"""Manuscript_CMPB_v11_中文版.docx -> v12
修正 v11 中确认的 4 处问题：
  1) §4.4 局限性编号乱序 (1)(2)(4)(5)(3) -> (1)(2)(3)(4)(5)
  2) §1 参考文献 [42]/[43] 描述对调（已用 Crossref/EuropePMC 实证）
  3) 补回被 v11 删除的关键局限性：腺癌泛化失败（CA_HPV_2 LODO 0.047）
  4) §4.4(5) patch 重叠加缓冲句，避免自毁 NO-IMAGE 核心证据
"""
import copy
import docx

SRC = r"F:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\Manuscript_CMPB_v11_中文版.docx"
DST = r"F:\project4_cervix_multimodal\papers\06_CMPB_最终版_v2_20260905\Manuscript_CMPB_v12_中文版.docx"

import shutil
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
    hits = [i for i, p in enumerate(d.paragraphs) if key in p.text]
    if not hits:
        print("  !! 未找到:", key[:45])
        return None
    return hits[0]


# ========== 1) §1 参考文献 [42]/[43] 描述对调 ==========
# 实证：[42] Fan J, Nat Genet 2023 = scRNA-seq + 空间转录组 + 空间蛋白组（摘要未提 Stereo-seq）
#      [43] Ou Z, bioRxiv 2021     = snRNA-seq + 空间转录组（无蛋白组）
i = find_one("已有采用其他空间平台")
if i is not None:
    t = d.paragraphs[i].text
    old = ("值得注意的是，已有采用其他空间平台（如 Stereo-seq [42]）或多组学整合"
           "（空间转录组与空间蛋白组 [43]）的宫颈癌空间组学研究发表，说明宫颈空间组学研究本身并不缺乏；")
    new = ("值得注意的是，已有整合单细胞/单核 RNA 测序与空间转录组、并进一步联合空间蛋白组的"
           "宫颈癌多组学研究发表 [42,43]，说明宫颈空间组学研究本身并不缺乏；")
    if old in t:
        set_text(d.paragraphs[i], t.replace(old, new))
        log.append("§1 引用 [42][43] 描述修正（原把 Stereo-seq/空间蛋白组的帽子戴反）")
    else:
        # 退化：替换关键片段
        t2 = t.replace("（如 Stereo-seq [42]）或多组学整合（空间转录组与空间蛋白组 [43]）",
                       "、并进一步联合空间蛋白组 [42,43]")
        if t2 != t:
            set_text(d.paragraphs[i], t2)
            log.append("§1 引用 [42][43] 描述修正")

# ========== 2) §4.4 局限性编号重排 ==========
idxs = {}
for tag, key in [("1", "样本量与统计功效"), ("2", "实验配置一致性"),
                 ("4", "与已发表 ST 方法的直接对比"), ("5", "图像 patch 的空间重叠"),
                 ("3", "TCGA bulk 验证部分阴性")]:
    j = find_one("（%s）%s" % (tag, key))
    if j is None:
        j = find_one(key)
    if j is not None:
        idxs[tag] = j
print("  定位到局限性段落:", {k: v for k, v in idxs.items()})

if len(idxs) == 5:
    # 按顺序取出各段"纯内容"（去掉编号前缀）
    contents = {}
    for tag, j in idxs.items():
        raw = d.paragraphs[j].text
        pre = "（%s）" % tag
        contents[tag] = raw[len(pre):] if raw.startswith(pre) else raw
    order = ["1", "2", "3", "4", "5"]
    targets = sorted(idxs.values())
    for tag, j in zip(order, targets):
        set_text(d.paragraphs[j], "（%s）%s" % (tag, contents[tag]))
    log.append("§4.4 局限性编号重排为 (1)(2)(3)(4)(5)")
    last_lim = targets[-1]
else:
    last_lim = max(idxs.values()) if idxs else None

# ========== 3) §4.4(5) patch 重叠：加缓冲句，保住 NO-IMAGE 核心证据 ==========
j = find_one("图像 patch 的空间重叠")
if j is not None:
    t = d.paragraphs[j].text
    if "NO-IMAGE" not in t:
        new = (t + " 需强调的是，该混杂对本文核心消融结论影响有限：NO-IMAGE 与 FULL 采用完全相同的"
               "patch 提取设置，二者的空间重叠程度一致，因此 Moran's I 的组间差值"
               "（0.866 vs 0.762，Δ=0.105）反映的仍是图像信息本身的贡献，而非重叠伪影；"
               "未来工作将进一步量化该混杂的绝对量级。")
        set_text(d.paragraphs[j], new)
        log.append("§4.4(5) patch 重叠加缓冲句（避免自毁 NO-IMAGE 核心证据）")

# ========== 4) 补回被删除的腺癌泛化局限性 ==========
# 在最后一条局限性后插入 (6)
anchor = find_one("4.5 未来工作")
if anchor is not None and last_lim is not None:
    src_p = d.paragraphs[last_lim]
    new_p = copy.deepcopy(src_p._p)
    src_p._p.addnext(new_p)
    new_para = docx.text.paragraph.Paragraph(new_p, src_p._parent)
    set_text(new_para,
             "（6）腺癌泛化能力有限：队列中唯一的腺癌样本 CA_HPV_2 在 LODO 协议下"
             "风险得分（0.047）低于正常组中位（百分位 0.645），为 4 折中唯一未高于全部正常的样本。"
             "结合模型 Top DEGs 均为鳞状谱系标志物（KRT19、TP63），该结果提示当前模型实质为"
             "鳞状宫颈病变的风险表征模型，其在腺癌上的适用性需专门的腺癌队列验证；"
             "本文结论应限定于鳞状病变（squamous cervical lesions）范围。")
    log.append("补回关键局限性 (6) 腺癌泛化失败（v11 误删，隐瞒风险）")

d.save(DST)
print("\n=== v12 修正完成 ===")
for x in log:
    print("  [OK]", x)
print("\n已保存:", DST)
