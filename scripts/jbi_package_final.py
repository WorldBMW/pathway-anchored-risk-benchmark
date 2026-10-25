"""Assemble clean JBI upload files and a concise author-facing handoff."""
from pathlib import Path
import shutil,zipfile,json,hashlib
P=Path('papers/08_JBI');S=P/'Submission_JBI_20260925';S.mkdir(exist_ok=True);U=S/'Upload';U.mkdir(exist_ok=True)
O=P/'_qa_20260924/source_data'
# Refresh scripts and their hashes without re-reading the large source embeddings.
m=json.loads((O/'source_manifest.json').read_text(encoding='utf-8'))
for e in m:
 if e['original'].startswith('scripts/'):
  src=Path(e['original']);shutil.copy2(src,O/e['path']);e['sha256']=hashlib.sha256(src.read_bytes()).hexdigest()
(O/'source_manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
with zipfile.ZipFile(P/'Supplementary_Source_Data_JBI.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(O.rglob('*')):
  if f.is_file():z.write(f,f.relative_to(O))
for n in ['Manuscript_JBI.docx','CoverLetter_JBI.docx','Highlights_JBI.docx','Supplementary_Information_JBI.docx','Supplementary_Source_Data_JBI.zip','GraphicalAbstract_JBI.tiff']:shutil.copy2(P/n,U/n)
figs=['Fig1_Framework','Fig2_risk_violin','Fig3_ablation_multiseed','Fig4_biology_correlation','Fig5_external_transfer']
for n in figs:shutil.copy2(P/'Figures'/(n+'.pdf'),U/(n+'.pdf'))
A=S/'Alternative_TIFF_figures';A.mkdir(exist_ok=True)
for n in figs:shutil.copy2(P/'Figures'/(n+'.tiff'),A/(n+'.tiff'))
shutil.copy2(P/'GraphicalAbstract_JBI.pdf',A/'GraphicalAbstract_JBI.pdf')
C=S/'Chinese_reference_only';C.mkdir(exist_ok=True);shutil.copy2(P/'Manuscript_JBI_中文.docx',C/'Manuscript_JBI_中文.docx')
text='''JBI 投稿文件说明（2026-09-25）

请从 Upload 文件夹逐项上传文件，不要把整个交付压缩包当作论文上传。
Manuscript_JBI.docx：英文主文（含作者信息、摘要、关键词、意义声明、正文、图表、声明和参考文献）。
CoverLetter_JBI.docx：投稿附信。
Highlights_JBI.docx：5条Highlights，每条不超过85字符。
Supplementary_Information_JBI.docx：补充说明与表S1–S5。
Supplementary_Source_Data_JBI.zip：数值附件、评分/坐标、来源清单和复核脚本，作为补充数据上传。
Fig1–Fig5 PDF：独立主图，保留矢量文字与图形；图1含真实组织图。
GraphicalAbstract_JBI.tiff：独立图形摘要，3984×1593像素，300 dpi。
Alternative_TIFF_figures：5张600 dpi TIFF主图和图摘PDF备选。对同一主图选择PDF或TIFF之一，不要重复上传。
Chinese_reference_only：中文对照稿，供作者核对，不作为JBI英文投稿主文上传。

本轮主要修订
1. 从当前NPZ重新计算切片级排序和固定评分置换检验，并补充209,440种排列的精确敏感性分析。FULL现存种子为0、3、4；NO-PROG为0–3，其余变体为0–2，未写成完全匹配种子。
2. 区分切片内与全局中心化Moran’s I：FULL切片内均值0.744，NO-IMAGE为0.734。旧0.931/0.859保留为敏感性结果，不再把0.072差值解释为切片内形态学增益。
3. 顺序去除有序目标、代理目标和通路项后的平均Kendall τ为0.460、0.251、0.210、−0.105。NO-PROG固定评分置换p为0.030–0.053（3/4种子名义显著）。去除目标反映目标依赖，不能单独证明标签记忆；固定评分置换不能替代置换重训或独立验证。
4. 不再将形态学LOSO表达代理任务约0.497的AUC与样本内疾病AUC 1.00直接比较。NO-ALL方向未锚定，不显著不等于已证明不存在排序。
5. 区分两类随机对照：队列内30个重训随机面板仅匹配基因数；外部头颈部未训练面板采用表达匹配。0.962/0.949来自另一训练配置的模型，不是未训练通路均值。
6. GeoMx采用与186个ROI标签一致的部署输出；主要推断单位为6对患者，配对p=0.03125。芯/ROI及Silva模式分析保留为探索性，不写成独立样本或概率校准验证。
7. 限定MRP-ST为待独立验证的五项报告建议，撤回未被数据建立的临床分级、预后和形态学增益主张。同步英文润色、中文、附信、Highlights、补充材料及所有图注。
8. 更正ST-Align作者列表及链接、Wu文献卷年（2026）和Cox页码；统一单位中文为“集镁”。

已完成的交付检查
英文摘要262词；正文约3,900词（不含摘要、参考文献和表格；计数工具可能有差异）。
主文5图、2张编号表及1张意义声明表，共8个展示项；48条参考文献顺序完整。
5张主图的Word内嵌PNG与独立最终图件一致；无遗留修订标记、批注和引用占位符。
文档已由WPS导出并检查页面图像。主图提供矢量PDF及600 dpi TIFF；图摘尺寸与字体按出版社规范整理。
所有组织图来自原始公开图像，仅裁剪及显示缩放，未使用生成式图像或添加不存在的细节；局部原始图像的细节上限取决于公开源文件，导出dpi不会增加原始信息。
本次数值附件包含22次保存运行、770条切片级记录及SHA256来源信息。训练结果原文件未修改。未向公共代码仓库推送本轮文件。

投稿前需由通讯作者最终确认的事实
用户已确认“集镁”和第一作者贡献属实。其余作者贡献、全体作者同意投稿、无专项资助、利益冲突（包括公司关联是否需进一步披露）、未一稿多投、伦理及公开数据使用声明仍需作者确认。这些事实不能仅由results证明。文稿现有资助/利益冲突文字沿用原稿，不能将本轮校对视为对其真实性的确认。提交前全体作者应核阅最终文稿及AI辅助声明。

格式依据及边界
Elsevier官方图件指南：https://www.elsevier.com/about/policies-and-standards/author/artwork-and-media-instructions/artwork-faq
Elsevier官方图形摘要指南：https://www.elsevier.com/researcher/author/tools-and-resources/graphical-abstract
JBI官方范围页：https://shop.elsevier.com/journals/journal-of-biomedical-informatics/1532-0464
JBI官方作者指南：https://www.sciencedirect.com/journal/journal-of-biomedical-informatics/publish/guide-for-authors
本次访问JBI作者指南返回403，未能直接核实其完整最新条款。已采用保守篇幅和展示项数量，并按可核实的出版社图件规则整理；上传时以Editorial Manager实际文件分类、必填声明和生成的投稿PDF为最终核对依据。不将第三方分区网页当作当前中科院/JCR分区证明。
'''
(S/'投稿文件与核对说明.txt').write_text(text,encoding='utf-8-sig')
(P/'投稿文件与核对说明_20260925.txt').write_text(text,encoding='utf-8-sig')
checks=[]
for f in sorted(S.rglob('*')):
 if f.is_file():checks.append({'file':str(f.relative_to(S)).replace('\\','/'),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(S/'SHA256_manifest.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
with zipfile.ZipFile(P/'JBI_Submission_20260925.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in sorted(S.rglob('*')):
  if f.is_file():z.write(f,Path(S.name)/f.relative_to(S))
with zipfile.ZipFile(P/'JBI_Submission_20260925.zip') as z:assert z.testzip() is None
print('Created',P/'JBI_Submission_20260925.zip','bytes=',(P/'JBI_Submission_20260925.zip').stat().st_size,'upload files=',len(list(U.iterdir())))
