from pathlib import Path
import sys,json,re,zipfile,hashlib,shutil,collections
R=Path(__file__).resolve().parents[1];Q=R/'.qa/submission_reaudit_20261016';O=R/'papers/投稿复核_20261016';AUD=O/'_审查记录'
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
stats=read(Q/'build_stats.json');num=read(Q/'numeric_audit.json');docs=read(Q/'document_audit.json');pages=read(Q/'page_audit.json')
assert num['all_tau_match'] and num['all_p_match']
assert len(docs)==31 and len(set(x['file'] for x in pages))==31
assert not any(p['blocks_outside_25pt_margin'] for p in pages)
for name in ['numeric_audit.json','document_audit.json','page_audit.json','portable_reproduction.json']:
    shutil.copy2(Q/name,AUD/name)
archives=[]
for zp in [O/'Audit_evidence.zip',O/'Interdisciplinary Sciences Computational Life Sciences/Audit_evidence_blinded.zip']:
    with zipfile.ZipFile(zp) as z:
        assert z.testzip() is None
        sums=z.read('SHA256SUMS.txt').decode().splitlines()
        for line in sums:
            h,n=line.split('  ',1);assert hashlib.sha256(z.read(n)).hexdigest()==h,(zp,n)
        badjson=[]
        for n in z.namelist():
            if n.endswith('.json'):
                try:json.loads(z.read(n).decode('utf-8-sig'))
                except Exception:badjson.append(n)
        assert not badjson,badjson
        archives.append({'file':str(zp.relative_to(O)),'files':len(z.namelist()),'npz_arrays':sum(n.endswith('.npz') for n in z.namelist()),'sha256_files_verified':len(sums),'json_valid':True})
(AUD/'archive_checks.json').write_text(json.dumps(archives,ensure_ascii=False,indent=2),encoding='utf-8')
refs=read(AUD/'references_corrected.json');original=read(R/'papers/14_BiB_20261016/evidence/references_verified.json');verification=read(Q/'reference_verification.json')
refrows=[]
for k,r in refs.items():
    if k not in original:continue
    changes=[]
    for field,label in [('authors','作者'),('title','题名'),('year','年份'),('journal','刊名'),('volume','卷'),('page','页码/文章号')]:
        if r.get(field)!=original[k].get(field):changes.append(label)
    if changes:refrows.append(f"| {k} | {'、'.join(changes)} | {r.get('doi') or r['url']} |")
statuses=collections.Counter(str(v['status']) for v in verification.values())
table='\n'.join(f"| {s['code']} | {s['abstract_words']} | 约 {s['body_words']} | {s['references']} | [打开文件夹]({s['folder'].replace(' ','%20').replace('&','%26')}/投稿文件说明.md) |" for s in stats)
report=f'''# 六刊投稿文件复核说明

复核日期：2026年10月16日。原始六个投稿目录保留；本目录为修订后的备选版本。

已完成稿件内容、方法解释、主要数值、参考文献、配图与投稿文件结构的实质修订。不能把这套文件标为“无条件立即提交”：投稿作者尚无 ORCID；尚未收到机构关于公开人类数据二次分析的伦理认定；本轮修改后的作者批准和系统声明仍须由真实作者完成。稿件目前是可供作者最终审阅的投稿候选包。

## 文件入口

每刊目录包含英文正文 Word、完整补充材料 Word、标题页 Word、投稿信 Word、独立声明、可读 Markdown 文本、参考文献和独立配图。CBM 另有五条独立 Highlights；GPB 另有补充材料 PDF；ISCLS 的正文、补充材料和证据包为匿名版本。Word 保留可编辑公式和表格。

| 期刊 | 摘要词数 | 正文词数 | 参考文献数 | 文件说明 |
| --- | ---: | ---: | ---: | --- |
{table}

正文词数不含参考文献、表格及图注；摘要不含结构小标题。最终统计以期刊系统为准。每刊4张主图、3张主表；补充材料4张图、2张表。独立图件包含矢量 PDF/SVG 和600 dpi TIFF/PNG。`Audit_evidence.zip` 为共用非匿名证据包；ISCLS 只能使用其目录中的匿名证据包。

## 主要科学修订

| 原稿问题 | 修订结果与依据 |
| --- | --- |
| 把 AUC 1.00 和0.497写成同一疾病预测任务的性能下降 | 核对 baseline_hpv_auc_eval.py 和原始 JSON 后确认：0.4967是独立 ridge 基线的切片内 spot 级表达代理 AUC，35折中仅16折有效；与切片级病变/正常分类不是同一模型、目标或统计单位。已删除“疾病预测性能崩溃”的论证，并增加补充注S8。 |
| 将 LDI 解释成已校准的标签依赖检测器 | 固定监督得分、只置换标签，得到的是描述性关联屏幕，不能区分真实信号、监督依赖、记忆或泄漏。限定其解释；补充训练过程未重拟合、离散零分布采用高斯参考门槛等边界。 |
| LDI 主报告与稳定性分析混用均值和单次运行 | 明确主报告用跨种子均值和代表运行的零分布作描述性标准化；种子0的稳定性分析使用同一运行的观测值和零分布。 |
| 把18个运行当作独立的误差率样本 | 明确三次训练共享一个生成队列；二项式区间只是忽略队列内依赖的名义描述区间，并非经过独立队列验证的临床误差率。 |
| 混淆仅看tau的运行阈值与还要求种子显著性的队列等级 | 分开定义、解释和标注；重绘图2的阈值坐标。 |
| 无依据使用“first”“prespecified”等措辞 | 去除未经全面优先权检索和预注册材料支持的优先性、预设性声明。 |
| 声称两个尺度均单调下降 | 保留主尺度L4回升的实际数字，改为总体下降并明确局部反弹。 |
| 将固定通路读出的负关联归因于无监督坐标任意翻转 | 限定为描述性反向关联，不能凭一侧p≈0.99证明结构，也不能仅凭嵌入坐标任意符号解释固定通路均值的反向排序。 |
| NOALL标量头精度敏感却按稳定效应画图 | 不再绘制其任意数值排序，在补充图中标记不确定；表示探针单独报告。 |
| 训练内编码器见过留出标签，却称为泛化 | 明确为受标签污染的传导式读出；标签自由探针仍不是完全归纳式患者级验证。 |
| 宣称v1.1完整公开但本次无法访问 | GitHub API对所给release返回404，只能认定本次未核实公开可访问性，不能断言永久不存在。删除稿内对该release的可访问性保证，改由随稿数据附件提供证据；恢复或更换公开代码地址仍可由作者办理。 |
| AI披露与本轮编辑不一致 | 如实加入本轮使用 OpenAI Codex 进行证据核对、编辑、按刊重组和文件准备的披露，保留原材料所述Trae使用情况，要求作者核实。 |

这些修改不构成新增临床验证或机制实验。仿真设计覆盖范围、病变样本量、来源混杂和方法新颖性仍是研究本身的局限，不能通过格式修改消除。

## 逐刊适配

- BiB：按 Problem solving protocols 组织；保留问题求解工作流；3–5条 Key Points 放在文末；标题页保留作者简介；参考文献采用前三位作者后 et al. 的形式。2000–5000词文章类型范围来自[官方指南](https://academic.oup.com/bib/pages/msprep_submission)。投稿作者须补 ORCID。
- BMC：按 Research article 组织；使用 Background / Results / Conclusions 结构式摘要；补齐全部必需的 Declarations 子标题；按[官方研究论文要求](https://link.springer.com/journal/12859/submission-guidelines/research-article)准备。摘要上限350词。
- CBM：突出计算医学解释与验证边界；提供独立 Highlights（5条，每条≤85字符），保留独立图摘要、贡献和AI声明。其[官方指南](https://www.sciencedirect.com/journal/computers-in-biology-and-medicine/publish/guide-for-authors)本次直接访问403，无法将所有细则认定为已完整核验；按保守的250词摘要等格式准备，提交时须核对当前系统字段。Highlights字符要求依据[Elsevier官方说明](https://www.elsevier.support/publishing/answer/how-do-i-include-highlights-with-my-manuscript)。
- CSBJ：使用[当前SPJ作者指南](https://spj.science.org/page/csbj/for-authors)，不沿用原路由中的Elsevier旧套版；选择 Research article，加入 Experimental and Technical Design 定位；现有7个主展示项不适用于Method article的5项限制；AI披露并入致谢。许可和利益冲突签署表由作者按系统要求完成。
- GPB：按[当前OUP作者指南](https://academic.oup.com/gpb/pages/general-instructions)准备 Research article；摘要181词，无缩略语或引用；标题页有短标题、关键词、基金和致谢；补充材料另供PDF。研究定位为组学评估，不虚构新机制或新组学数据。
- ISCLS：按[官方双盲要求](https://link.springer.com/journal/12539/submission-guidelines)移除审稿正文、补充材料及证据附件中的作者身份；作者、基金和利益声明独立放置。摘要在150–250词范围，提供6个关键词。仅投稿信、标题页、声明文件给编辑，不能标成供审稿文件。

部分官方网站直接抓取403，但BiB、CSBJ、GPB的官方页面正文可通过网页检索访问；CBM细则访问受限的边界已单独记录。没有用第三方模板站代替其官方合规确认。

## 参考文献与来源核验

使用 Crossref 元数据核对 DOI 文献，修订作者、题名、卷页和年份；团体作者按团体名称保留。UNI的Crossref请求曾返回429，本次另用Nature Medicine原文页面核对题名、卷页与年份。无DOI资料的网页可访问性与完整元数据核验分开记录。新增实际使用的GEO及10x数据源条目，并在相应方法中引用。

自动抓取状态计数：{dict(statuses)}。详细请求结果见 `_审查记录/reference_verification.json`；最终文献元数据见 `_审查记录/references_corrected.json`。历史证据包中的原references_verified.json保留为来源记录，其旧信息不能替代修订后的References.txt/.bib。

| 引用键 | 相对原元数据修订字段 | DOI或原始链接 |
| --- | --- | --- |
{chr(10).join(refrows)}

## 验证范围

- 重算21项主探针的留一预测、Kendall tau和每项10,000次重拟合置换检验：全部与存档一致。用本轮交付的独立CPU入口再次运行得到一致结果。未重新训练编码器或重做所有原始数据预处理。
- 复算表达代理baseline：16/35有效折，均值0.4966914072、标准差0.0204632137，与原始JSON一致。
- 明确float32标准化/Gram乘积与float64求解；全float64敏感性计算改变两个宫颈种子的tau，但其三种子均值保持0.27041。这与NOALL标量头的不确定性是两个问题。
- 31个Word检查：无残留插值占位符、未处理修订或评论；主稿各含5个可编辑公式、3个可编辑表、4张主图。匿名稿检查未发现本研究作者姓名、单位域名或所给仓库账号。
- 全部31个文件均渲染成PDF并生成页面图；总页数{len(pages)}。检查页面概览、关键公式表格及配图；文本边界检查未发现越过25pt外边界的文本块。渲染器说明：技能指定的render_docx.py因本环境缺少LibreOffice而失败，改用隐藏WPS实例导出PDF，再用PyMuPDF逐页光栅化。未将渲染中间文件混入投稿文件。
- 两个证据包的CRC、SHA-256清单和JSON解析均通过；每包包含141份池化数组（21项主探针、12个发表方法嵌入、108份仿真网格导出）。这是部分计算的可复现证据，不是完整原始数据和模型权重的重新发布。

## 提交前由作者完成

1. 注册真实 ORCID，至少满足 BiB 投稿作者的必需字段。
2. 提供机构关于公开人类数据二次分析的伦理认定或豁免材料；未提供之前不能填造审批编号或宣称已获豁免。
3. 所有作者审阅本轮稿件并确认贡献、单位、商业利益、基金、AI披露与单一在审声明；完成需要本人签署的表单。
4. 在所选期刊当前投稿系统复核必填字段、作者账号、文件类型和费用安排。特别是CBM细则未能完整直接访问。
5. 六个版本属于同一研究的备选投稿文件，一次只选择一家提交。不要同时投稿；不得把替换标题和侧重点的版本当作六项独立研究发表。
'''
(O/'00_复核结果与投稿须知.md').write_text(report,encoding='utf-8')
# Build one clearly named archive per alternative; include only its relevant evidence.
for s in stats:
    folder=O/s['folder'];dest=O/('投稿包_'+s['code']+'.zip')
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob('*'):
            if p.is_file():z.write(p,p.relative_to(folder).as_posix())
        if s['code']!='ISCLS':z.write(O/'Audit_evidence.zip','Audit_evidence.zip')
        z.write(O/'00_复核结果与投稿须知.md','00_复核结果与投稿须知.md')
    with zipfile.ZipFile(dest) as z:assert z.testzip() is None
manifest=[hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.relative_to(O).as_posix() for p in sorted(O.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt']
(O/'SHA256SUMS.txt').write_text('\n'.join(manifest)+'\n',encoding='utf-8')
print('FINALIZED',len(docs),'Word files',len(pages),'rendered pages',len(stats),'journal archives',flush=True)
print('Archive checks',archives,flush=True)
