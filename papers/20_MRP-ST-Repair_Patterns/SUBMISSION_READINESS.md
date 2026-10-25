# 投稿前状态（Patterns · v23）

生成于 2026-10-25。这份清单只列"上传输之前必须为真"的事，不重复正文里的论证。

---

## A0. 本轮处置（v22 → v23）

| 评审意见 | 判断 | 处置 |
|---|---|---|
| 两处 Zenodo 占位符未清零 | **正确，且实际是 3 处**（漏了 Key Resources Table 那一行） | 已清：改写为 Cell Press 的真实时点口径——归档与 DOI 要求发生在**接收前**，tagged release 是冻结态与 interim 可访问位置。全库 `TO BE INSERTED BEFORE SUBMISSION` 计数为 0 |
| ref [1] 预印本 DOI 占位 | **正确** | 已清：ref [1] 改写为"相关稿件"本体 + 可验证 interim 地址，分工边界在投稿信里单列成段。参考文献编号不动：重编 42 条会让累积式 SI 的引用号错位 |
| 稿件声称代码已发布 | **比占位符更致命，评审未发现** | 实测 `github.com/WorldBMW/cervix-st-multimodal` 返回 **404**（该用户存在）。本轮已 `git init` + 白名单 `.gitignore` + 提交 `39a3cc3` + 打 `v1.0.0` 标签；**只剩 push**（见 B2） |
| DSML 仍是强制项 | **不正确** | 已取证：官方 IFA 现版（2026-10-25 实抓）在 Policies / Components to include / Final file requirements 三处均无 DSML；期刊 2024 年起逐步淘汰。**未添加**，理由见 C3 |
| cover letter 正面论证 broad interest | **正确** | 已新增 `Why this is a Patterns paper...` 段并前置到第一段之后；另修投稿信里 3 个评审没看到的瑕疵（整句重复、`sigma_hat` 未统一、`[status to be inserted: under review elsewhere]`） |

补充发现（本轮顺手堵掉的泄密风险）：`scripts/ssh_*.py`、`_put.py`、`pull_reseed_results.py`、
`upload_e2_reseed.py`、`verify_upload_sizes.py` 里**硬编码了云服务器 root 密码**。按早期清单里的
`printf ... > .gitignore` + `git add -A` 整目录推上去会直接公开泄露。现 `.gitignore` 改为
**白名单制**（先 `/*` 全忽略，再逐条放行），凭据脚本、其他期刊稿件工作区、内部策略文档
一律不入库；已验证 `git grep 'PW ='` 为空。入库 785 文件 / 46.3 MB。

v16 新增：STAR-Methods 框架补全（Lead contact / Materials availability / Data and code
availability 三段；**Key Resources Table 作为 Table 6**；"Quantification and statistical
analysis"写明 n 的两重含义、两个种子族、B = 2,000 与 B = 10,000、σ̂ 定义、1.645 来源、SD 而非 SEM）。

---

## A. 本轮已清掉的

| 项 | 状态 | 落点 |
|---|---|---|
| Graphical abstract 尺寸 | 已解决：1200 × 1200 px，300 dpi，Arial | `figures/graphical_abstract_1200.png`、`figures/graphical_abstract_300dpi.tif`、`figures/graphical_abstract_1200.pdf` |
| GA 版式溢出 | 已解决：脚本内置宽度断言，任一标签超框即报错 | `scripts/make_graphical_abstract_square.py` |
| GA 三级证据分层 | 已画进第三带（VALIDATED / AUDITED / NOT TESTED） | 同上，与正文 Summary 措辞一致 |
| 两个 DOI 的替换动作 | 已工具化：一条命令改三处占位并重建 docx | `scripts/_fill_dois.py`（`--check` 列出待清项） |
| Zenodo 归档元数据 | 已就绪，Zenodo 读仓库根的 `.zenodo.json` | `.zenodo.json`（license 现填 MIT，若要用别的许可需改） |
| 代码可复现说明 | 已补：环境、数据来源、逐条命令、两个坑 | `REPRODUCE.md`、`requirements-patterns.txt` |
| TitlePage 统计 | 已校正（Bigger picture 299 → 295；GA 改为方图） | `TitlePage_Patterns.md` |
| STAR-Methods 框架 | 已补全：Resource availability 三段 + Key Resources Table（Table 6）+ Quantification and statistical analysis | `scripts/_rev_v16_star.py`、`Manuscript_Patterns.docx` |
| 措辞统一 | 三级证据 standing qualifier（跨域 Results + Discussion 各一处）、passing gate ≠ erasure、无 optimal λ | 同上 |

---

## B. 只能由你本人完成的三步（我无法代做）

### 1. Companion preprint 上线（阻塞 ref [1]）

`papers/19_ISCLS_20261016/Manuscript_ISCLS.md` 已完稿。挂到 bioRxiv/medRxiv 后拿到 DOI。
注意 Patterns 的口径：**投稿时该 preprint 必须已 online 且可访问**，只有"已提交待审"不算。

### 2. GitHub 仓库 + tag + Zenodo 归档（阻塞 Data availability）

**仓库本地已建好**（commit `39a3cc3`，tag `v1.0.0`，785 文件 / 46.3 MB，工作区干净）。
线上 `github.com/WorldBMW/cervix-st-multimodal` 目前仍是 **404**，所以这一步还没走完；
只要不 push，正文里六处链接就都是死链，等同"代码不可访问"——这是本稿唯一真正的
desk-reject 风险点。你要做的只有三行：

```bash
cd /g/project4_cervix_multimodal
git remote add origin https://github.com/WorldBMW/cervix-st-multimodal.git
git push -u origin main --tags        # v1.0.0 一并推上去
```

（GitHub 上先建好同名空仓库，不要勾 README / .gitignore。）

然后在 GitHub 上给 `v1.0.0` 建 Release（正文三处写死的正是 `.../releases/tag/v1.0.0`，
**若实际 tag 改名，正文三处必须同步改**），再到 <https://zenodo.org/account/settings/github/>
对本仓库开启 archiving——Zenodo 会自动为这个 tag 建记录并**当场分配 DOI**，
形如 `10.5281/zenodo.xxxxxxx`。仓库根的 `.zenodo.json` 已写好（MIT、五位作者、
关键词、related identifier），Zenodo 会直接读取。

> 若你想让 DOI 在投稿时就已解析：Zenodo 建好记录后直接 **Publish**（开放获取，无 embargo），
> 不要留成 draft。reserved DOI 在未发布状态下点开是"not publicly available"，
> 反而会给编辑一个比"DOI 待填"更差的印象。

正文里已经把 tag 链接写死成 `.../releases/tag/v1.0.0`（Key Resources Table、Resource
availability、Data availability 三处）。**如果你的实际 tag 不叫 v1.0.0，必须改这三处**，否则编辑
点进去是 404，等同于代码不可访问。Release 里建议放：README、`requirements-patterns.txt`、
`REPRODUCE.md`，以及一个 manifest 脚本目录（每张图/每张表对应一条可跑命令）。

### 3. 一次性填两个 DOI 并重建

```bash
python scripts/_fill_dois.py --check                       # 列出 4 个填充点
python scripts/_fill_dois.py --companion 10.xxxx/xxxxx --zenodo 10.5281/zenodo.xxxxxxx --build
python scripts/_qa_v23.py                                  # 重建后必须再跑一遍 QA
```

脚本会同时改 ref [1]、Key Resources Table 的 Zenodo 行、`**Code.**` 段、Data availability 段，
并把投稿信里对 ref [1] 的状态描述换成真实 DOI。

v23 起稿件里已无 `TO BE INSERTED BEFORE SUBMISSION` 字样，`--check` 报的是**填充点**
（3 个 Zenodo 锚点 + 1 个 companion 锚点 + 投稿信 1 处），不是占位符。

---

## C. 一个待你决定的问题

**正文 17,619 词**（Introduction 至 Experimental Procedures，不含图注与表）。
TitlePage 已写明"要么在投稿信里申请豁免，要么压缩 Results"。

现状分布：Introduction 3,532 / Results 8,534 / Discussion 4,813 / Procedures 3,129。
若要压，唯一无损的位置是 Results 的剂量–反应枚举（逐剂量逐种子的数字，SI 表里已有），
把枚举换成一句汇总 + 指向 SI，预计可减 900–1,200 词，不动任何论证。
我倾向**不压**：Patterns 对研究论文没有硬性字数上限，而这个长度里没有冗余段落
（已查：正文无重复句），压缩只会让审稿人觉得关键数字被藏起来。但这是你的判断。

---

## C3. DSML（Data Science Maturity Scale）：已核实**不需要**，故未添加

评审要求"以官方 IFA 为准"确认并补齐 DSML。按官方 IFA 核对的结果是**不用补**：

- 官方《Information for Authors》（<https://www.cell.com/patterns/information-for-authors>，
  2026-10-25 实抓）全文**没有** DSML / "maturity scale" 任何一处：Policies 目录下无，
  "Components to include"（Title / Summary / … / Resource availability / …）无，
  "Final file requirements" 无。
- 该刊 2024 年起在主编 Andrew Hufton 任内**逐步淘汰** DSML（与"明确聚焦机器学习与 AI 的
  创造性应用"同步调整）。
- 因此若在正文里加一段 `Data Science Maturity Scale: Proof-of-Concept`，等于告诉编辑
  这份稿子是按 2022 年的模板准备的——**扣分而非加分**。

若 handling editor 真的开口要，一行即可补（挂到 Experimental Procedures 末尾）：

> **Data science maturity level.** This work corresponds to *Proof-of-Concept*:
> the instrument is validated on simulated cohorts with known ground truth and on
> public real cohorts, and is not yet deployed in an operational pipeline.

除此之外，本稿也**不适用** IFA 里的 "Standardized data reporting checklists"：
Cell Press 现只有 battery、photovoltaic cell、catalysis 三张表，与本稿无关。

## C2. 若担心匹配度：Cell Press Multi-Journal Submission（MJS）

一个不需要多花一轮投稿周期的备选通道。官方口径（Cell Press 编辑部公告）：MJS 允许一篇稿件
同时送 **最多 6 本** Cell Press 期刊考虑（现有 27 本以上参与，含 Patterns 之外的物理科学刊
Device），由一名专职编辑协调，各刊**独立**决定是否送审；**超过 80% 的 MJS 投稿至少获得一本
期刊的评审机会**；2025 年通过 MJS 最终接收的论文里 70% 落在作者最初选中的目标刊之一。

对本稿最实际的两点：**MJS 初始投稿阶段大幅放宽格式要求**（17,619 词与 6 张主表不会被卡），
且多刊若都要审会共用同一组审稿人，不会重复消耗审稿资源。

投稿前需自行确认：Patterns 是否在当期 MJS 参与刊名单内（名单会变动）。若不在，MJS 就只能当
作转投其他 Cell Press 子刊的通道，而投 Patterns 仍需直接投稿。

---

## D. 上传清单

| 文件 | 说明 |
|---|---|
| `Manuscript_Patterns.docx` | 正文 + 6 主表（含 STAR-Methods Key Resources Table）+ 图注，0 em-dash，0 字面 `**` |
| `Supplemental_Information_Patterns.docx` | 19 个表对象（S1–S17 + 两张分表），**追加式维护，勿从 md 重建** |
| `TitlePage_Patterns.docx` | 首页、统计、投稿前清单 |
| `CoverLetter_Patterns.docx` | 含三级证据说明与"算子不是贡献"的声明 |
| `figures/fig1–4, fig5_crossdomain` | 每图 PDF（矢量）+ PNG（300 dpi） |
| `figures/graphical_abstract_300dpi.tif` | Cell Press 接受格式，1200 × 1200 |
| `figures/graphical_abstract_1200.png` | 备用（系统若要求 png） |

---

## E. 上传前 30 秒自查

```bash
python scripts/_qa_v23.py                      # 格式硬指标（含 Highlights ≤85、In brief ≤50、Summary ≤150）
python scripts/_fill_dois.py --check           # 4 个填充点；若已拿到 DOI 应先 --build 再自查
python -c "from docx import Document; d=Document('papers/20_MRP-ST-Repair_Patterns/Manuscript_Patterns.docx'); print(len(d.tables), 'main tables')"
```

期望：QA 全绿；占位 0；6 主表。
