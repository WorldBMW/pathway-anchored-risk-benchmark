"""Build the Chinese manuscript version (Manuscript_BiB_zh.docx) for internal review.

Reuses the English build's figures, tables (with translated headers) and references,
with a full Chinese translation of the main text.
"""
from pathlib import Path
import json, re
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

R = Path(__file__).resolve().parents[1]
O = R/'papers/14_BiB_20261016'
F = O/'figures'

def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
REF = read(O/'evidence/references_verified.json')

def element(tag, **attrs):
    e = OxmlElement(tag)
    for k, v in attrs.items():
        e.set(qn(k), v)
    return e

def set_ea(run, eastasia='SimSun'):
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn('w:rFonts'))
    if rfonts is None:
        rfonts = OxmlElement('w:rFonts'); rpr.append(rfonts)
    rfonts.set(qn('w:eastAsia'), eastasia)

def setup():
    d = Document(); s = d.sections[0]
    s.page_width = Inches(8.5); s.page_height = Inches(11)
    s.top_margin = s.bottom_margin = s.left_margin = s.right_margin = Inches(1)
    s.header_distance = s.footer_distance = Inches(.492)
    for name, size, bef, aft, ea in [('Normal', 11, 0, 6, 'SimSun'), ('Title', 16, 0, 12, 'SimHei'),
                                      ('Heading 1', 14, 16, 8, 'SimHei'), ('Heading 2', 12, 12, 6, 'SimHei'),
                                      ('Heading 3', 11, 8, 4, 'SimHei'), ('Caption', 9, 4, 6, 'SimSun')]:
        st = d.styles[name]
        st.font.name = 'Times New Roman'; st.font.size = Pt(size); st.font.color.rgb = RGBColor(0, 0, 0)
        st.font.bold = name.startswith('Heading') or name == 'Title'
        st.paragraph_format.space_before = Pt(bef); st.paragraph_format.space_after = Pt(aft)
        st.paragraph_format.line_spacing = 1.25 if name == 'Normal' else 1.0
        st.paragraph_format.widow_control = True
        if name.startswith('Heading'):
            st.paragraph_format.keep_with_next = True
        el = st.element.get_or_add_rPr()
        rf = el.find(qn('w:rFonts'))
        if rf is None:
            rf = OxmlElement('w:rFonts'); el.append(rf)
        rf.set(qn('w:eastAsia'), ea)
    footer = s.footer.paragraphs[0]; footer.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    footer.add_run('MRP-ST  |  ')
    fld = element('w:fldSimple', **{'w:instr': 'PAGE'})
    footer._p.append(fld)
    return d

def table(d, headers, rows, widths, title):
    d.add_paragraph(title, style='Caption').paragraph_format.keep_with_next = True
    t = d.add_table(rows=1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.LEFT; t.autofit = False
    pr = t._tbl.tblPr; w = pr.find(qn('w:tblW')); w.set(qn('w:w'), '9360'); w.set(qn('w:type'), 'dxa')
    pr.append(element('w:tblInd', **{'w:w': '120', 'w:type': 'dxa'}))
    pr.append(element('w:tblLayout', **{'w:type': 'fixed'}))
    borders = element('w:tblBorders')
    for side in ['top', 'bottom', 'insideH']:
        borders.append(element('w:' + side, **{'w:val': 'single', 'w:sz': '4', 'w:color': 'AAAAAA'}))
    for side in ['left', 'right', 'insideV']:
        borders.append(element('w:' + side, **{'w:val': 'nil'}))
    pr.append(borders)
    grid = t._tbl.tblGrid
    for c in list(grid): grid.remove(c)
    for wdt in widths: grid.append(element('w:gridCol', **{'w:w': str(wdt)}))
    for ri, vals in enumerate([headers] + rows):
        row = t.rows[0] if ri == 0 else t.add_row()
        trpr = row._tr.get_or_add_trPr(); trpr.append(element('w:cantSplit'))
        if ri == 0: trpr.append(element('w:tblHeader'))
        for i, (c, v) in enumerate(zip(row.cells, vals)):
            c.width = Inches(widths[i] / 1440)
            tc = c._tc.get_or_add_tcPr(); tw = tc.find(qn('w:tcW'))
            tw.set(qn('w:w'), str(widths[i])); tw.set(qn('w:type'), 'dxa')
            mar = element('w:tcMar')
            for side, value in [('top', 80), ('bottom', 80), ('start', 120), ('end', 120)]:
                mar.append(element('w:' + side, **{'w:w': str(value), 'w:type': 'dxa'}))
            tc.append(mar); c.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            p = c.paragraphs[0]; p.paragraph_format.space_after = Pt(3); p.paragraph_format.line_spacing = 1
            r = p.add_run(str(v)); r.font.size = Pt(9); r.bold = ri == 0; set_ea(r)
            if ri == 0: tc.append(element('w:shd', **{'w:fill': 'F4F6F9'}))
    return t

def reftext(k):
    r = REF[k]; a = '; '.join(r['authors'])
    return f"{a}. {r['title']}. {r.get('journal', '')}. {r.get('year', '')};{r.get('volume', '')}:{r.get('page', '')}. {r['url']}"

# ---- 中文全文（按空行分段；[[TABLE1]] 等为占位；[@@] 为公式行）----
TEXT = r'''
# MRP-ST：空间转录组模型审计的校准标签依赖指数与实测操作特性

白明伟¹、顾正敏²、张烨²、郭朗³*

¹ 集美科技集团有限公司，沈阳 110002，中国（Mingwei Bai, JiMei Technology Group Co., Ltd., Shenyang 110002, China）
² 中国医科大学附属第一医院病案管理中心，沈阳 110000，中国（Zhengmin Gu, Ye Zhang, Medical Record Management Center, The First Hospital of China Medical University, Shenyang 110000, China）
³ 沈阳医学院药学院，沈阳 110034，中国（Lang Guo, School of Pharmacy, Shenyang Medical College, Shenyang 110034, China）
* 通讯作者：郭朗，沈阳医学院药学院，沈阳市皇姑区黄河北大街 146 号，邮编 110034。电话：+86 13555707001；电子邮箱：guolang1016@symc.edu.cn。

作者邮箱：白明伟 baimingwei@jm360.cn；顾正敏 guzm@cmu1h.com；张烨 13332457636@163.com；郭朗（通讯作者）guolang1016@symc.edu.cn。

作者简介：白明伟是沈阳集美科技集团研究工程师，开发多模态空间转录组模型并建立了本文报告的审计方法。顾正敏就职于中国医科大学附属第一医院病案管理中心，从事临床数据整理与空间队列注释的验证工作。张烨就职于中国医科大学附属第一医院病案管理中心，为本研究的宫颈演示队列提供临床数据整理与资源。郭朗就职于沈阳医学院药学院，负责概念化与方法设计，并监督和管理本研究。

文章类型：Problem solving protocols（问题解决协议）

要点：

• MRP-ST 将"一个空间疾病评分究竟学到了什么？"转化为五项可审计实验，并配套一个校准的标签依赖指数。

• 实测操作特性：预设阈值处灵敏度 1.00，0/18 对照假阳性，宽完美分离窗口。

• 一个身份混杂对照区分记忆、编码器向"留出"探针的泄漏与无标签零假设。

• 相同的探针、推断与定级判据原样迁移到 SpaGCN、STAGATE 与 GraphST 嵌入。

• 宫颈演示：LDI 3.26，种子不稳定的探针信息（0.270），队列内 AUC 崩塌（1.00 → 0.497）。

## 摘要
空间转录组模型通常会输出空间上连贯的疾病评分，但在仅由少数独立取样病灶构成的小样本队列中，队列内的一致性并不是"评分学到了任何可迁移内容"的可靠证据。我们提出 MRP-ST——空间转录组模型审计最低报告协议、一个校准的标签依赖指数（LDI），以及据我们所知此类审计规则的首个实测操作特性。五项条款分别覆盖监督消融、评估单位、标签依赖、无标签探针与终点特异外部检验。在以非应答者比例为剂量、覆盖 90 样本与宫颈匹配 35 样本尺度的剂量-反应网格上，定级规则以灵敏度 1.00（9/9；精确 95% CI 0.66–1.00）检出注入的程序，阈值假阳性为零（0/18；精确 95% CI 0–18.5%），并具有宽完美分离窗口；一个精确的有限样本上界区分饱和与估计。在身份混杂对照下，监督评分头样本内拟合良好，而标签训练的转导嵌入返回上界水平的"留出"探针值（0.70 与 0.457，全部 p ≤ 10⁻⁴）：这是编码器泄漏，而非泛化。相同的探针与判据原样迁移到 SpaGCN、STAGATE 与 GraphST 嵌入。在由 35 张切片构成的宫颈演示中，LDI 为 3.26；队列内分离（AUC 1.00）在留一评估下坍缩为随机水平（0.497）；冻结表征保留种子不稳定的信息（0.270）。MRP-ST 将一个解释性问题转化为一个误差率带区间、可复现的测量。

关键字：空间转录组；模型审计；标签依赖；表征探针；置换检验；操作特性；可复现性

## 1. 引言
空间转录组学在组织背景中测量基因表达，与组织病理学的整合拓展了计算组织表征的范围 [@stahl;@moses;@stnet;@uni]。因此，一个空间平滑的标量输出看起来可以概括某个疾病过程：它可能追踪上皮区域、与通路活性相关并区分已注释的样本。然而这些观察回答的是不同的问题，且它们在训练队列内的一致并不能证明发现了一个可迁移的疾病轴。

当成千上万个空间位置仅来自少数几个独立取样的病灶时，这一困难尤为突出：点位共享组织背景、制备与注释，训练种子复用同一批样本。基因组机器学习对观测间的依赖、混杂的采集结构与跨越验证边界的预处理十分脆弱 [@whalen]；数据泄漏与乐观评估会产生无法通过独立检验的科学论断 [@kapoor;@varo]。TRIPOD+AI [@tripod]、REFORMS [@reforms] 与 DOME [@dome] 等报告与验证框架规定了应当记录与如何验证的项目，但均不判定一个空间评分究竟学到了什么信息。

必须区分两个问题：拟合的评分是否依赖标签或强加其方向的表达衍生目标？移除这些目标之后，其表征是否仍保留探针可在留出样本上恢复的疾病信息？当可用特征主要编码样本身份时，监督评分也能对训练样本排序；而无监督评分可以在不破坏其下层信息的情况下翻转方向。将评分坍缩或训练分离中的任何一种视为完整答案，都会混淆输出方向、表征内容与泛化。

我们提出 MRP-ST——空间转录组模型审计最低报告协议——包含四项贡献：(i) 五项条款，覆盖监督消融、评估单位、标签依赖、无标签探针与终点特异外部检验；(ii) 一个以置换零分布校准的标签依赖指数（LDI），将"该排序是否依赖标签？"转化为门限判定；(iii) 据我们所知此类审计规则的首个实测操作特性——一个带身份混杂对照的剂量-反应网格给出检出率、假阳性率与阈值窗口，一个精确的有限样本 tau 上界区分饱和与估计；(iv) 一个统一审计，将相同的探针、推断与定级判据迁移到三种已发表的无监督嵌入方法。一个由 35 张切片构成的宫颈队列提供真实数据演示。MRP-ST 是对报告框架的补充：它们规定文档内容，而 MRP-ST 规定针对"一个空间疾病评分支持哪些论断"这一问题的判定实验，并在已知信号队列上测量这些实验的误差率。

## 2. 材料与方法
### 2.1. 被审计模型、统计单位与池化
审计对象是为本工作构建的参考模型：一个编码器，融合对齐的表达（4,991 个基因）、来自冻结 UNI 骨架的形态学特征 [@uni] 与点位坐标，一个四头注意力融合，一个标量评分头与一个重建解码器。训练复合了加权重建、邻域平滑、二分类代理、有序严重程度、通路对齐与方差下限目标。监督在六个消融变体中被移除（NOIMAGE、NOHPV、NONEIGH、NOPROG、NOSUP 以及无标签的 NOALL，后者进一步移除代理、有序与对齐目标）；补充说明 S2 列出架构、权重与各变体。严重程度按样本注释。评分与嵌入在任意比较之前先池化为样本均值，因此每个切片——而非每个点位——恰好贡献一个观测。存储的样本标识是可用的分组单位；不假设患者独立性。预处理与编码在协变量上保持转导。图 1 概括了工作流程及其推断边界。

### 2.2. 校准标签依赖指数（LDI）
评分依赖在样本尺度上以池化评分与有序注释之间的肯德尔 tau-b 量化，并保留结（ties）：

[@@]

裸的无监督点估计不能作为监督依赖的有效标尺：NOALL 评分头本身坍缩为近常数的偏移，其排序是浮点噪声而非生物学（补充说明 S2）。因此 LDI 针对监督评分的置换零分布进行校准：

[@@]

其中 τ_⊥ 与 σ_null 是 B=10,000 次完整样本标签置换下 tau-b 的均值与标准差，θ=Φ⁻¹(1−α) 是单侧高斯门限。LDI 对评分的正仿射重标定不变，当 LDI > θ 时判定排序是标签依赖的。在宫颈队列上，校准值为 τ_⊥=0.001 与 σ_null=0.141。

### 2.3. 带重拟合置换推断的留出探针
表征信息在冻结的无标签 NOALL 编码器上探测。对每个留出的样本 i，嵌入维度在其余样本上标准化，一个岭回归（惩罚 1、无截距）预测严重程度；留一预测与注释以 tau-b 比较。这是转导表征中的留一样本探针，而非完全归纳的患者级验证。显著性置换完整标签向量并重拟合所有折 [@ojala]：

[@@]

其中 B=10,000，+1 修正防止零蒙特卡洛 p 值 [@phipson]。岭预测对标签是线性的，因此一个预计算的留一算子可以精确重拟合每一次置换，且预测与标签联合置换；这一"重拟合检验"——而非针对固定预测的标签洗牌——正是全文所称"校准"的含义。线性探针是表征内容的标准读出 [@alainbengio;@belinkov]。全部 21 个主要种子×队列探针检验均汇报 Benjamini–Hochberg 校正 [@bh]；证据文件 Table_S1_corrected_probes.csv 将每个检验映射到其证据文件。探针显著性量化的是在拟合表征下可恢复的关联，而非生物学机制。

### 2.4. 剂量-反应网格与操作特性
具有已知注入程序的合成队列用于校准定级规则。每个队列抽取 n 个样本并分为正常与患病供体（主尺度 50/40，n=90；宫颈匹配尺度 31/4，n=35）。患病供体在 KEGG 衍生 HPV 通路基因 [@kegg] 上携带固定反应幅度的表达程序，应答者比例为 1−f；非应答者比例 f ∈ {0, 0.25, 0.50, 0.75} 定义水平 L1–L4。三个生成器种子（20261006–20261008）与三个训练种子（0–2）产生每格九个 run；标签为二分类。身份混杂对照臂（CTRL）为每个供体分配一个与标签无关的随机表达指纹，因此严重程度排序只能通过记忆供体身份来实现。生成器参数见补充说明 S3。

由于标签是二分类的，tau-b 受一个在完美有序分离处恰好达到的有限样本最大值所约束：

[@@]

得到 τ_max=0.707（n=90）与 0.457（n=35）；处于上界的探针值标志着完美留一分离，而非巧合性重复。队列级定级规则（表 1）在平均探针 τ ≥ 0.35 且至少两个种子显著时判定该队列为"支持"，在 |平均 τ| ≤ 0.15 且无显著种子时判定为"不支持"，否则为"提示性"。其 run 级误差率直接估计：

[@@]

在每一尺度的九个 L1 与九个 CTRL run 上进行，并对每个汇报的比例给出精确的 Clopper–Pearson 区间。

[[TABLE1]]

### 2.5. 已发表嵌入的统一审计与统一读出
三种已发表的无监督嵌入方法——SpaGCN [@spagcn]、STAGATE [@stagate] 与 GraphST [@graphst]——在相同队列上以其已发表流程与默认参数被审计（基于 ScanPy [@scanpy] 构建；SpaGCN 在占位图像上禁用组织学模块；k-means 经 scikit-learn [@sklearn]）。点位被聚类；每个聚类计算 HPV 通路均值表达；每个样本的风险读出来自最大聚类值——这是对空间聚焦程序最有利的聚合方式。针对严重程度的肯德尔 tau-b 在固定 21 样本子集（12 正常 + 9 患病；19 + 2 匹配）上使用 2,000 次标签置换，并按表 1 的阈值定级。为分离表征差异与读出差异，统一读出额外导出每个流程的样本级池化嵌入（STAGATE 30 维；GraphST 3,000 维），覆盖两个尺度的 L1、L3 与 L4 队列，并在完整队列上施加与 §2.3 相同的探针——带重拟合置换的留一岭回归。SpaGCN 在结构上被排除：其逐样本空间域不产生跨样本共享的连续表征。每种方法一个生成器队列、一个嵌入，意味着采用单 run 判据（支持：τ ≥ 0.35 且 p < 0.05）。其他空间域方法亦存在 [@bayesspace;@banksy;@stbench]；本审计评定的是判据，而非方法性能。

### 2.6. 宫颈演示队列
真实数据演示包含 35 张宫颈切片（31 正常、1 HSIL、3 癌；46,820 个点位），来自 GEO GSE208654、GSE217237 与一个公开的 10x Genomics 切片。四个病灶决定了有限的疾病多样性，且采集来源与注释部分对齐，因此残余探针信息无法唯一归因于疾病。该队列展示协议在真实数据上的运行；它既不对临床预测器加以验证，也不测量进展。

## 3. 结果
### 3.1. 定级规则的实测操作特性
[[TABLE2]]

平均探针 tau 随非应答者比例在两个尺度上下降（主尺度：0.704、0.276、0.125、0.182；匹配尺度：0.457、0.394、0.286、0.177），L1 值达到上界的 99.6% 与 100%（图 2）。run 级显著性在匹配尺度上单调（9/9、6/9、2/9、2/9），在主尺度上则由 L1 到 L3 的下降（9/9、6/9、1/9、3/9）承载，L4 比例追随平均平台而非注入水平。在身份混杂对照下，两个尺度上均无 run 在重拟合检验下显著（0/9 与 0/9；合并 0/18，精确 95% CI 0–18.5%），与该 run 数下名义 5% 相容。队列级上，每个尺度的三个 L1 生成器队列均获支持（每尺度 3/3），而无 CTRL 队列获支持（0/6；精确 95% 上界 45.9%）。阈值操作特性显示预设定级阈值并非刀锋：在 θ=0.35 处，灵敏度为 1.00（9/9；精确 95% CI 0.66–1.00），两个尺度的阈值假阳性率均为 0.00，完美分离窗口覆盖 θ ∈ [0.20, 0.675]（主尺度）与 [0.20, 0.45]（匹配尺度）。每格九个 run 使精确区间较宽；它们是实测操作特性的一部分，而非精度主张。

### 3.2. 对照臂区分记忆、泄漏与信息
监督 FULL 评分头在 CTRL 队列上样本内拟合良好（90 样本处 tau-b 0.415–0.643，均值 0.490；匹配尺度 0.162–0.280，均值 0.237），而标签训练的转导嵌入返回上界水平的"留出"探针值（0.692–0.707 与 0.457，全部 p ≤ 1×10⁻⁴）（图 3）。这些探针在任何有意义的意义上都不是留出的：编码器见过每一个样本，联合训练把标签轴写入了共享表征。相同探针下的无标签 NOALL 编码器返回 −0.030 ± 0.111（主尺度）与 +0.042 ± 0.102（匹配尺度），两个尺度上九个 run 均无显著——在无可泄漏标签信息的设计下这是正确的零行为。0.73 与 0.41 个 tau 单位的差距正是条款 C4 所排除的编码器泄漏量级：一份探测标签训练转导嵌入的报告，会在真实可迁移信号为零的设计下读出 0.70。

### 3.3. 判据跨已发表架构的迁移
[[TABLE3]]

在 21 样本子集的簇最大读出下，支持级仅出现在 L1：90 样本处 SpaGCN（0.677，p=0.0005）与 GraphST（0.491，p=0.007）；匹配尺度处 GraphST 处于子集上界（0.425，p=0.005），参考探针亦然（0.425，三之三种子显著）（图 4）。STAGATE 未获支持（−0.173，p=0.83；−0.045，p=0.61）。在弱水平上无子集读出达到显著；GraphST 匹配尺度的 0.336 在 α 边界处 p=0.050，而 STAGATE 的负弱水平值是某一无监督轴的符号反转而非零结果（补充说明 S4 讨论读出压缩与符号反转）。

完整队列上的统一读出完成迁移。GraphST 的池化嵌入在两个尺度上返回上界水平的 L1 值（0.707 与 0.457，p=1×10⁻⁴）——高于其自身焦点读出——并在主尺度上单调下降（L3 处 0.353，p=3×10⁻⁴；L4 处 0.207，p=0.035），在 L3 获支持、在 L4 获提示性；其匹配尺度的弱水平压缩为相同值（L3 与 L4 处 0.339，p=0.015）。STAGATE 的 30 维嵌入在每级、两个尺度上返回 |τ| ≤ 0.10 且全部 p ≥ 0.34，处于零带之内：其焦点读出所揭示的符号反转结构无法从点位均值线性恢复。因此读出选择本身是一个被审计的量——焦点聚合低估了 GraphST 可线性恢复的样本级信号——而相同的探针、重拟合推断与判据评定的是任务机制而非任何特定编码器：每一种在最强水平获支持的读出，都会随非应答者比例增加而失去支持，这一点在两个尺度、全部四种表征家族中成立。

### 3.4. 宫颈演示
在 35 切片队列上 LDI 门限触发：τ_⊥=0.001 与 σ_null=0.141 给出 LDI=3.26，对照 θ=1.645，即一个标签依赖的排序；该判定在 α ∈ {0.01, 0.05, 0.10, 0.20} 与五个置换种子下稳定（LDI 3.25–3.30）。移除监督通道使评分在描述意义上退饱和（FULL 0.460；NOPROG 0.251；NOSUP 0.210；NOALL 头在数值上不确定；补充说明 S2）。无标签表征保留真实但种子不稳定的信息：NOALL 探针返回 0.270（SD 0.116），仅中间种子显著（p=0.0019），包括在 21 个主要检验上 Benjamini–Hochberg 校正之后。以供体标签训练的编码器返回 0.420–0.462 的留一供体探针值，且三之三种子显著——这正是 §3.2 在零真实信号下测量的泄漏轴——因此 0.19 的差距即是该协议的分离器。队列内将四个患病切片与 31 个正常切片分离对监督评分是完美的（AUC 1.00），却在留一评估下坍缩：同一 108 基因代理面板上的岭回归以平均 AUC 0.497 ± 0.021 预测状态。审计将这一 1.00 到 0.497 的坍缩作为泄漏基线汇报，而非把队列内分离读作可迁移的疾病轴。残余探针信息可能反映疾病、采集来源或其他共享结构；四个病灶无法建立轨迹或标志物，且临床校准需要定义明确的结局与人群，这是无界组织评分所不能提供的。

## 4. 讨论
MRP-ST 解决一个实际问题：可复现地评定一个空间疾病评分支持哪些生物学论断。评分消融描述移除信息通道后会改变什么；探针追问可恢复的结构是否在表征中留存；外部检验追问何种性质在队列或平台变化后仍存续。这些是互补的实验，而非可互换的效度度量，MRP-ST 规定它们——而 TRIPOD+AI、REFORMS 与 DOME 规定的是文档与通用验证 [@tripod;@reforms;@dome]。

对照臂把泄漏论证转化为测量。在标签与共享表达结构按构造相互独立的设计下，监督评分头样本内拟合，标签训练的转导嵌入返回上界水平的"留出"探针，而只有无标签编码器返回正确的零行为。仅审计评分头会把第一个量误读为学习；对标签训练嵌入做朴素探针会把第二个量误读为泛化。本框架避免这两种误读：一个标量评分的阴性审计未必否证其下层的表征，而一个标签训练嵌入的阳性探针未必指示可迁移信息。

剂量-反应网格把定级词汇转化为实测误差率：检出率随非应答者比例下降，合并对照假阳性率为 0/18（精确 95% CI 0–18.5%），预设阈值落于宽完美分离窗口内，因此定级不依赖精调。上界分析分离饱和与估计，而弱水平定级仍受机制限制：在匹配尺度仅一个应答患病供体时，一条"不支持"定级记录的是该尺度下证据不足，而非生物学缺失——连续估计优先于定级。

统一审计回应了"协议与某一模型同出自一处可能令其判据向该模型校准"的循环性质疑。三级规则约束第三方读出，每一种无标签读出在相同的难度水平上失去支持，而统一读出分离表征内容与读出选择——GraphST 可线性恢复的信号超过其焦点聚合所揭示的水平，而 STAGATE 的反转结构对点位均值的线性探针不可见。匹配尺度机制——宫颈队列自身的机制——正是本研究中每一种无标签读出失去支持之处。

在宫颈示例中，残余探针信息可能反映疾病、采集来源或其他共享结构；不均匀的组织学配准制约形态学解释，而移除图像后排序几乎不变，说明在此设置下形态学的增量排序有限，而非形态学普遍无关。外部分析（补充说明 S5）展示的是终点特异性而非普遍成功：配对组织分离与反转的评分方向并存，空间组织在没有令人信服的表型区分下仍持续存在。

局限包括转导预处理与编码、来源混杂的宫颈标签、仅一个监督参考架构（部分由审计三种已发表无监督方法所补偿）、每种已发表方法每队列单 run（审计评定判据而非方法；系统比较见 [@stbench]）、一个固定的簇最大读出（其匹配尺度压缩暴露了相同 tau 值）、批内局部邻域目标，以及仅改变非应答者比例与尺度、而不改变采集伪影的仿真。完全归纳验证必须在患者留出边界内重拟合所有已学习预处理与编码器，而无限制标签置换要求可交换性，采集混杂可能破坏这种可交换性。审计暴露这些约束，而非将其转化为机制性论断。

实际交付物是一个可追溯的证据包：变体定义、池化表征（含导出的已发表方法嵌入及其统一读出结果）、重拟合置换代码、校验和与终点特异解释。修正后的探针计算无需 GPU 即可复现，使计算论断可复核，同时不暗示临床就绪。

## 5. 结论
MRP-ST 将空间评分的监督依赖与表征中可恢复的信息分离开来，校准的 LDI 使这一分离成为零分布导出的门限。在已知信号队列上，定级规则以灵敏度 1.00（9/9；精确 95% CI 0.66–1.00）与零阈值假阳性（0/18；精确 95% CI 0–18.5%）检出注入程序，并随非应答者比例下降；一个身份混杂对照显示标签训练编码器把标签泄漏进"留出"探针，而无标签编码器返回零结果。相同判据、探针与推断原样迁移到已发表嵌入：每一种在最强水平获支持的读出都会随非应答者比例增加而失去支持。宫颈演示返回 LDI 3.26、种子不稳定的表征信息（0.270，三之一种子）与队列内分离（AUC 1.00）在留一评估下坍缩为随机（0.497）——诸项正是该协议被设计用来暴露的失效模式。前瞻应用时，MRP-ST 将每一项生物学论断限定于支持它的信息与验证单位之内。

## 致谢与声明
我们感谢负责公开数据集的调查者与参与者。

经费：本工作未获得来自公共、商业或非营利资助机构的任何特定资助。

作者贡献：白明伟：概念化、方法、软件、形式分析、调查、数据整理、可视化与撰写—初稿。顾正敏：数据整理、验证与撰写—审阅与编辑。张烨：数据整理、资源与撰写—审阅与编辑。郭朗：概念化、方法、监督、项目管理与撰写—审阅与编辑。

利益冲突：白明伟任职于集美科技集团有限公司。作者声明不存在可能影响本工作的已知经济利益或私人关系冲突。

伦理：本工作重分析公开数据集，无新的招募或干预。源研究的知情同意、伦理与数据使用条件适用。不主张新的机构批准号或豁免决定。

数据与代码可得性：源数据集在方法与补充材料中指明。全部分析代码、模型配置与完整审计证据包（池化表征，含导出的已发表方法嵌入及其统一读出结果、结果摘录、SHA-256 校验和与修正分析脚本）在 https://github.com/WorldBMW/pathway-anchored-risk-benchmark 公开可得；本投稿对应该仓库的 release v1.1（https://github.com/WorldBMW/pathway-anchored-risk-benchmark/releases/tag/v1.1）。

AI 协助声明：在准备本稿件过程中，作者使用了 AI 辅助编码工具（Trae）进行分析代码生成、计算结果的数值核验、由数值输出生成图表以及英文语言润色。研究设计，以及全部分析的选择、执行、解释与撰写均由作者完成，作者对内容承担全部责任。没有任何 AI 系统被列为作者。详细使用说明见补充材料。

[[REFERENCES]]

[[FIGURES]]
'''

# ---- 中文表格（表头译中文，数据/数值保留）----
T3H_cn = ['级别', '判据（条款 C4：各种子留一探针 tau-b 的均值）', '解释']
T3R_cn = [
    ['支持', '平均 τ ≥ 0.35 且 ≥ 2/3 种子 p < 0.05', '无标签表征中可复现的信息'],
    ['提示性', '既不满足支持也不满足不支持', '弱或种子不稳定的信息；以连续估计为准'],
    ['不支持', '|平均 τ| ≤ 0.15 且 0/3 种子 p < 0.05', '该样本量下证据不足，而非生物学缺失'],
]
T4H_cn = ['水平（非应答者比例 f）', '主尺度 τ̄ (SD)', '显著 run 数', '级别', '匹配尺度 τ̄ (SD)', '显著 run 数', '级别']
T4R_cn = [
    ['L1 (f = 0)', '0.704 (0.009)', '9/9', '支持', '0.457 (0.000)', '9/9', '支持'],
    ['L2 (f = 0.25)', '0.276 (0.154)', '6/9', '提示性', '0.394 (0.095)', '6/9', '支持'],
    ['L3 (f = 0.50)', '0.125 (0.122)', '1/9', '提示性', '0.286 (0.096)', '2/9', '提示性'],
    ['L4 (f = 0.75)', '0.182 (0.104)', '3/9', '提示性', '0.177 (0.148)', '2/9', '提示性'],
    ['CTRL（身份混杂）', '−0.030 (0.111)', '0/9', '—', '0.042 (0.102)', '0/9', '—'],
]
T4T_cn = '表 2. C4 留出探针在剂量-反应网格上的操作特性。每格九个 run（三个生成器 × 三个训练种子）。CTRL 行的显著 run 比例即 α=0.05 下的经验假阳性率（合并 0/18；精确 95% CI 0–18.5%，与名义 5% 相容）。二分类标签上界：τ_max = 0.707（主尺度）与 0.457（匹配尺度）；L1 均值达到上界的 99.6% 与 100%。'
T5H_cn = ['队列（子集）', 'SpaGCN τ (p)', 'STAGATE τ (p)', 'GraphST τ (p)', 'STAGATE 探针 τ (p)†', 'GraphST 探针 τ (p)†', '参考 τ̄ (种子)']
T5R_cn = [
    ['L1, 90 样本', '0.677 (0.0005) *', '−0.173 (0.83)', '0.491 (0.007) *', '−0.045 (0.65)', '0.707 (0.0001) *', '0.717 (3/3) *'],
    ['L3, 90 样本', '0.093 (0.33)', '0.173 (0.20)', '0.213 (0.14)', '−0.026 (0.59)', '0.353 (0.0003) *', '0.243 (0/3)'],
    ['L4, 90 样本', '0.080 (0.36)', '−0.465 (0.99)', '0.226 (0.14)', '−0.005 (0.51)', '0.207 (0.035) *', '0.155 (0/3)'],
    ['L1, 35 样本', '0.291 (0.073)', '−0.045 (0.61)', '0.425 (0.005) *', '0.103 (0.34)', '0.457 (0.0001) *', '0.425 (3/3) *'],
    ['L3, 35 样本', '0.291 (0.073)', '−0.381 (0.99)', '0.336 (0.050)', '0.029 (0.47)', '0.339 (0.015) *', '−0.201 (0/3)'],
    ['L4, 35 样本', '0.291 (0.073)', '−0.336 (0.96)', '0.336 (0.050)', '−0.022 (0.57)', '0.339 (0.015) *', '−0.194 (0/3)'],
]
T5T_cn = ('表 3. 已发表嵌入方法与参考协议的统一审计。簇最大列：固定 21 样本子集上的单 run（12 + 9；19 + 2 匹配），'
          '2,000 次标签置换；子集二分类标签上界 τ_max = 0.717 与 0.425。探针列（†）：将相同的留一岭探针与重拟合置换（B=10,000）'
          '施加于完整队列（90 与 35 样本；上界 0.707 与 0.457）上导出的池化嵌入；SpaGCN 因其逐样本空间域不产生跨样本共享连续表征而被排除。'
          '参考列：冻结 NOALL 嵌入在相同 21 样本子集上的岭探针，三个训练种子（α=0.05 时显著种子的个数）。* p < 0.05。'
          '子集读出仅在最强水平 L1 获支持；统一探针额外使 GraphST 在 90 样本队列 L3 获支持（0.353）。')

# 中文公式（文字版）
EQS_cn = [
    '（公式 1）肯德尔 tau-b：τ_b = (C − D) / √[(C + D + T_s)(C + D + T_y)]',
    '（公式 2）标签依赖指数：LDI = (τ̄_FULL − τ_⊥) / σ_null',
    '（公式 3）重拟合置换 p 值：p_refit = (1 + #{b : τ_b ≥ τ̂_obs}) / (1 + B)',
    '（公式 4）二分类标签的精确有限样本上界：τ_max = √[ n₀ n₁ · 2 / ((n₀ + n₁)(n₀ + n₁ − 1)) ]',
    '（公式 5）操作特性：sens(θ) = Pr(τ̂ ≥ θ | L1)，fpr(θ) = Pr(τ̂ ≥ θ | CTRL)',
]

CAPTIONS_cn = [
    ('Fig1_Audit_workflow', '图 1. MRP-ST 工作流程。独立的消融对比量化标量评分依赖；留出探针评估冻结 NOALL 嵌入中的信息。样本标签置换重拟合完整探针。一个带身份混杂对照的剂量-反应网格测量定级规则的误差率，统一审计将相同判据施加于已发表嵌入方法。外部终点单独评估。编码在协变量上保持转导；宫颈疾病提供演示而非临床验证。'),
    ('Fig2_Operating_characteristics', '图 2. C4 定级规则在剂量-反应网格上的实测操作特性。A：平均留出探针 tau-b（九个 run 的 ± SD）对非应答者比例 f，90 样本（圆圈）与宫颈匹配 35 样本（方块）尺度；身份混杂对照绘于右侧；虚线标记二分类标签上界 tau_max（0.707 与 0.457）。B：重拟合 p < 0.05 的 run 比例；虚线标记名义 α = 0.05，对照列给出经验假阳性率（0/9 与 0/9）。C：支持级阈值的函数——灵敏度（L1 队列）与假阳性率（CTRL 队列）；阴影标记完美分离窗口 [0.20, 0.675]（主尺度）与 [0.20, 0.45]（匹配尺度）；预设阈值 0.35 落于两个窗口之内。'),
    ('Fig3_Dissociation', '图 3. 对照臂区分评分头记忆、编码器泄漏与表征信息。所有面板使用身份混杂 CTRL 队列，其标签按构造与共享表达结构独立。A：90 样本尺度。B：宫颈匹配 35 样本尺度。柱为九个 run 的均值；点为单个 run。每尺度三种读出：FULL 评分头样本内 tau-b（监督拟合；不适用检验）、FULL 嵌入留一探针 tau-b（标签训练转导编码器；全部 p ≤ 1e-4）与 NOALL 嵌入留一探针 tau-b（无标签冻结编码器；实心点 p < 0.05）。虚线：二分类标签上界 tau_max（0.707 与 0.457）。仅无标签编码器返回正确零行为（−0.030 ± 0.111 与 +0.042 ± 0.102）；与标签训练嵌入之间 0.73 与 0.41 个 tau 单位差距即条款 C4 排除的编码器泄漏量级。'),
    ('Fig4_Methods_benchmark', '图 4. 统一审计在相同 21 样本子集上评定已发表无监督嵌入方法与参考协议。A：90 样本队列。B：宫颈匹配 35 样本队列。每面板展示逐样本风险读出对严重程度的肯德尔 tau-b：SpaGCN、STAGATE 与 GraphST（单 run；簇最大 HPV 通路读出；2,000 次标签置换；实心标记 p < 0.05）与参考协议在冻结 NOALL 嵌入上的岭探针（三个训练种子的均值 ± SD；重拟合置换；实心菱形：至少一个种子 p < 0.05）。虚线：子集二分类标签上界（0.717 与 0.425）。支持级仅出现在最强水平 L1；无读出将弱水平与零假设区分开，SpaGCN 匹配尺度读出在三级返回相同 tau（读出压缩）。'),
]

# ---- 构建 ----
def build():
    # 引用顺序复用英文版 prescan
    order = []
    for f in ['Manuscript_BiB.md', 'Supplementary_BiB.md']:
        text = (O / f).read_text(encoding='utf-8-sig')
        for m in re.finditer(r'\[@([^\]]+)\]', text):
            for k in m.group(1).split(';'):
                k = k.strip().lstrip('@')
                if k and k not in order:
                    order.append(k)

    def cite(m):
        ks = [k.strip().lstrip('@') for k in m.group(1).split(';')]
        for k in ks:
            if k and k not in order:
                order.append(k)
        return '[' + ', '.join(str(order.index(k) + 1) for k in ks) + ']'

    text = re.sub(r'\[@(?!@)([^\]]+)\]', cite, TEXT)
    d = setup()
    eq = 0
    for b in text.split('\n'):
        b = b.strip()
        if not b:
            continue
        if b == '[[TABLE1]]':
            table(d, T3H_cn, T3R_cn, [1300, 3900, 4160], '表 1. 条款 C4（表征信息）的三级定级判据。')
            continue
        if b == '[[TABLE2]]':
            table(d, T4H_cn, T4R_cn, [2050, 1500, 850, 1150, 1500, 850, 1460], T4T_cn)
            continue
        if b == '[[TABLE3]]':
            table(d, T5H_cn, T5R_cn, [1160, 1320, 1280, 1320, 1380, 1440, 1460], T5T_cn)
            continue
        if b == '[[REFERENCES]]':
            for i, k in enumerate(order, 1):
                p = d.add_paragraph(f'[{i}] ' + reftext(k))
                p.paragraph_format.line_spacing = 1
                p.paragraph_format.space_after = Pt(5)
                for r in p.runs:
                    r.font.size = Pt(9)
            continue
        if b == '[[FIGURES]]':
            for name, cap in CAPTIONS_cn:
                d.add_page_break()
                p = d.add_paragraph()
                p.paragraph_format.keep_with_next = True
                p.add_run().add_picture(str(F / (name + '.png')), width=Inches(6.45))
                d.add_paragraph(cap, style='Caption')
            continue
        if b == '[@@]':
            p = d.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            r = p.add_run(EQS_cn[eq]); r.font.size = Pt(10); set_ea(r)
            eq += 1
            continue
        if b.startswith('### '):
            d.add_heading(b[4:], 2)
        elif b.startswith('## '):
            d.add_heading(b[3:], 1)
        elif b.startswith('# '):
            d.add_paragraph(b[2:], style='Title')
        else:
            p = d.add_paragraph(b)
            for r in p.runs:
                set_ea(r)
    d.save(O / 'Manuscript_BiB_zh.docx')
    # 词数（中文按字符数粗估）
    chars = len(re.sub(r'\s', '', text))
    print(f'MAIN zh chars={chars} refs={len(order)}')
    return chars, eq

if __name__ == '__main__':
    build()