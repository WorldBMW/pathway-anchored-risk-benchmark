# Patterns 投稿独立核查与修订报告

核查日期：2026 年 10 月 25 日。当前修订源：MRP-ST-Repair_manuscript_Patterns_v27.md。修订前四份 Word 均保存在同目录的 *_v27pre_20261025.docx。本轮未改写 results 中的实验记录，也未实际提交、公开代码或发送投稿信。

## 结论

**当前不应标记为“全部通过，可直接投稿”。** 研究主题可以按“分组数据的评价审计”组织，具备跨领域方法讨论的潜力；但原稿把标签相关性、身份可解码性、单位级交叉验证和组级推断混为一谈。这会影响核心结论，属于方法与证据问题，不能仅靠英语润色解决。v27 已收窄主张，修正已确认的口径错误，并保留实验数值及局限。没有依据保证编辑初筛、外审或录用通过。

Patterns 定位的判断：可以强调“可复核的评价流程及失败案例”，但现有证据不足以宣称通用身份泄漏修复工具、已验证的跨域决策边界或临床效益。仅把空间转录组论文改成通用数据科学叙事，并不能增加方法创新性和验证强度。该判断是本轮编辑与方法审读意见，不是期刊编辑的预审意见。

## 已完成的修订

1. 标题改为 Auditing label dependence and sibling-unit inflation in group-structured representations，避免把尚未成立的修复认证写入题目。
2. 重写 Summary、In brief、Highlights、Bigger picture、Introduction 和 Discussion，删除反复推销贡献的段落与绝对化因果解释；保留结果、失败结果和不确定性。
3. 明确 LDI 实际使用 τ_LOO，τ_LGO 是单独报告的组级统计量；R 只有在单位与组一一对应时才可称组间可迁移比例。
4. 将 Proposition 1 限定为“同一个统计量、固定空分布尺度下，两数值区间是否相交”。区间相交不保证任何模型或剂量可达到；两轴统计量不同时不能套用等价条件。
5. 更正 GeoMx 数据单位为 7 份标本来自 6 位患者，93 个 ROI 分离出 186 个上皮/基质区室测量；明确当前代码的七 case 分组不等于患者独立分组。
6. 更正正文补充表图注中 risk、Silva 和 cell type 的数值归属：基线 Δ 分别为 0.3736、0.3955、0.0075；τ_LOO/σ 分别为 9.34、10.39、8.49。
7. 明确宫颈主结果的 35 切片/34 供体与分辨率阶梯的 35 切片组不是同一分组；不能声称两者都严格供体留一。
8. 修正 HAR 实际审计单位数为 299，gas drift 为 300。删除以种子×剂量单元当作独立人群重复的推断性表述。
9. 参考文献 42 的文章号由 43717 改为出版原文的 13246；参考文献 7 第一作者缩写改为 Saeb, S.。补齐所有文内引用，未进行会再次破坏引用的全表重编号。
10. 五幅主图嵌入 Word，并保留原独立图件；重绘与当前证据范围一致的 graphical_abstract_v27，提供 PNG、PDF 和 TIFF。
11. 同步标题页、投稿信、补充材料解释及 REPRODUCE.md。标题页不再夹带已经失效的旧版 DOI 占位符说明。投稿信不再声称不存在证据支持的已公开代码、作者已确认事项或绝无重复结果。
12. Word 已经原生导出 PDF 供内部排版检查；宽表使用横向页面。原生技能渲染器因无 LibreOffice 失败，记录原因后改用已安装的 Word，而非将文本提取冒充排版核验。

## 投稿前必须解决的方法问题

| 问题 | 直接证据 | 对结论的影响 | 所需工作 |
|---|---|---|---|
| LDI 不是身份去除检验 | exp_crossdomain_audit.py 的 audit_bundle 对标签 y 计算 τ_LOO；group_id_acc 是另一个分类器 | 低 LDI 可来自真实标签信号被破坏；不能证明身份已去除 | 分别定义标签效用、身份解码和泄漏差值，预先指定独立验收目标 |
| 多单位实验没有组保持的置换空分布 | sigma_null 与 refit_grid_audit.operator 使用单位留一/标签置换；跨域 dual_gate_pass 使用 τ_LOO 和 safety_tau_loo_kept | 不能把 1.645 当作经过组级验证的 5% 门限，也不能称组级验收 | 依科学问题重做组保持置换或受限置换；重算空分布、图表及相关结论 |
| 编码器先拟合，探针才留组 | 审计读取已有嵌入，留一发生在探针阶段 | 可做条件表示审计，不能当完整学习流程的未知患者泛化 | 若保留该主张，外层留患者后重新拟合预处理、编码器与下游模型 |
| 宫颈分组口径不一致 | dump_cervix.json n_donors=34，但 samples 长度=35；unit_ladder_cervical.json G=35；build_arm 按 sample_ids 唯一值分组 | “每供体一个切片”“LOO=LGO”的表述不成立 | 从来源元数据建立明确 donor_id 对照表，按真实供体重做比较 |
| GeoMx case 不是独立患者 | 出版原文 Methods 和 Results 明确 seven specimens, six unique patients；93 ROIs 分离两类区室 | 七 case 留一可能让同一患者标本跨折，ROI 配对相关性也不能忽略 | 核实 case→patient→ROI→compartment 映射，再按目标层级重做 holdout 与置换 |
| HAR 和 gas 是名义多分类 | 代码把类别编号当数值，使用 Kendall τ/岭回归 | 编号改变可影响数值，不能声称无编码依赖的任务性能或通用边界 | 多分类 AUROC、balanced accuracy 或其他明确任务指标，增加重编码敏感性检验 |
| 基线与剂量尺度混用 | σ 每个 run 重估，而推导用基线 σ；外部表格保留率使用 cohort-mean baseline | 基线阈值不是无条件“任何剂量均不可能”的证明；换种子基线可能改计数 | 预先冻结基线/空分布约定，或给出有界尺度条件；重算时明确逐种子或队列均值 |
| 未证明下游收益 | 归档 endpoint 表；原稿也承认 no accepted repair improved a downstream endpoint | 不应以提高预测或临床获益作为卖点 | 可按审计/负结果论文如实投稿；若要保留有效修复主张，需要独立任务收益证据 |

这些问题已在文字中澄清，但**澄清不等于已完成重新实验**。本轮没有伪造“新结果”补齐缺口，也没有为了获得漂亮验收数量改变门限。

## 图件和结果对应范围

主图 1–4 的绘图入口为 scripts/make_figures_patterns.py，使用 results 中的 JSON/NPZ；主图 5 的入口为 scripts/make_fig_crossdomain.py，使用 crossdomain_audit.json。归档图形中的 LDI/accept 字样应按 v27 的统计定义与限定解释，不能继续引用旧稿的“已证明身份去除”解释。

本轮逐行复核了两个跨域数据集共 30 个种子×剂量单元：LDI=(τ_LOO−0.001)/σ、Δ=τ_LOO−τ_LGO、实际 dual gate 以及每域 0/12 个 dosed pass 均与 JSON 一致。还核对了 GeoMx 三标签基线、宫颈供体计数、外部队列剂量记录和补充材料表对象。主图 1–4 的实验配置存在不同种子、稳定化方案、样本量与训练轮数，不应互相当作同一配置的重复结果。

**这不是所有原始实验的完整重跑，也不是对每幅图每个基因条目的独立再分析认证。** 完整的行/面板级结果映射、输入哈希与原始数据重现仍需完善。AUDIT_v27_checks.json 保存本轮确实运行的检查和图件哈希，不能据此声称“全部实验验证通过”。旧图形摘要不再用于 v27；使用 figures/graphical_abstract_v27.tif。

## 参考文献和期刊要求核查边界

- 43 条文献编号连续，文内单号、多号和范围引用均在 1–43 内，每条均有文内引用。
- 出版原文核实并修正了 Axelrod 等文献文章号、患者/标本/ROI 数；arXiv 核实了 Nishimura 等文献的题名、作者和 ISBI 2025 状态。
- Crossref 对所有 43 条进行了查询尝试，但多数返回 HTTP 429。没有 DOI 的模糊检索还返回若干错配结果（例如 ref 2、17、28），这些候选**未被采纳为正文文献**。完整返回记录见 REFERENCE_LOOKUP_v27.json。因此不能把本轮说成“43 条均外部核实”。
- Patterns 官方 information-for-authors 页面经网页工具及直接请求均返回 403，未能本轮全文复核。不得据旧 SUBMISSION_READINESS 中的断言宣称“2026 官方全部合规”，特别是文章长度、图表数量、STAR Methods 最终格式和各类前置材料要求。当前文件采用可审阅研究稿结构；最终上传前仍需从可访问的官方指南/投稿系统核实。
- 本轮摘要为 131 词，In brief 为 48 词，Highlights 四条各不超过 85 字符。Introduction 至 Discussion 约 8,510 个空白分词，**包括内嵌表格文字**；不同统计口径会不同，不应沿用旧稿的 17,521 词声明。

## 公开材料与作者事项

2026-10-25 直接请求以下两个 URL 均返回 HTTP 404：

- https://github.com/WorldBMW/cervix-st-multimodal
- https://github.com/WorldBMW/cervix-st-multimodal/releases/tag/v1.0.0

404 表示在本轮匿名访问中不可获得，不能区分仓库私有或不存在。需验证投稿审稿人可访问的冻结代码、依赖与数据说明，再更新稿件；不能写成已发布。requirements-patterns.txt 的版本与硬件声明尚未逐一通过完整环境重建验证；本轮未把本机编辑环境冒充实验环境。

相关稿件确实在目录中被既有材料声明。本轮保留相关稿件披露，但未核验其全部内容、投稿状态和与当前稿的结果/文字重叠，因此删除了“绝无任何重叠”的无证据保证。通讯作者需确认真实状态、作者批准、独家投稿与应随稿提供的 related file。这里是作者事实确认，不是要求为已授权的本地修订另行批准。

## 文件使用

- Manuscript_Patterns.docx：v27 可审阅修订稿，包含五幅主图；仍有上述重新分析缺口。
- Supplemental_Information_Patterns.docx：保留归档表格，修正统计口径解释与标题。
- TitlePage_Patterns.docx：同步后的标题页。
- CoverLetter_Patterns.docx：与证据一致的投稿信草稿，保留待作者核实事项，**不是可以不读即上传的最终声明**。
- MRP-ST-Repair_manuscript_Patterns_v27.md：本轮主稿源文件。
- figures/graphical_abstract_v27.*：与收窄后证据范围一致的图形摘要。
- *_v27pre_20261025.docx：本轮前备份，不用于上传。

旧 v16–v26 文件及旧中文稿未被当作同步后的投稿版本。不要把旧版本与 v27 混合上传。

## 可复核来源

1. Axelrod 等，出版原文：https://www.nature.com/articles/s41598-026-43717-z （文章号 13246，7 标本/6 患者，93 ROI，分区室采集）。
2. Nishimura 等：https://arxiv.org/abs/2503.07173 。
3. Patterns 官方作者指南入口：https://www.cell.com/patterns/information-for-authors （本轮 403，未声称已全文验证）。
4. 归档实现：scripts/exp_crossdomain_audit.py、scripts/refit_grid_audit.py、scripts/exp_unit_ladder_cervical.py。
5. 归档结果：results/crossdomain_audit.json、results/within_group_label_geomx.json、results/unit_ladder_cervical.json、results/dump_cervix.json，以及外部剂量记录。
