# 投稿前状态（Patterns · v22）

生成于 2026-10-25。这份清单只列"上传输之前必须为真"的事，不重复正文里的论证。

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

**当前这个目录根本不是 git 仓库**（无 `.git`，无 remote），而正文已经写了
`https://github.com/WorldBMW/cervix-st-multimodal` 与"tagged release + Zenodo DOI"。
这是真正的 desk-reject 风险点：审稿人点进去必须是能跑的东西。

```bash
cd /g/project4_cervix_multimodal
git init
# .gitignore 必须先排除数据与缓存，否则 8000+ 文件、数十 GB 会直接推不上去
printf 'data/\nfm_cache/\n.venv/\n__pycache__/\n*.npz\n*.h5\n*.tgz\n.idea/\n.workbuddy/\n' > .gitignore
git add -A && git commit -m "Manuscript release: auditable identity-leakage audit (Patterns submission)"
git remote add origin https://github.com/WorldBMW/cervix-st-multimodal.git
git tag -a v1.0.0 -m "Release matching the submitted manuscript"
git push -u origin main --tags
```

然后在 GitHub 上建 Release（用 v1.0.0 这个 tag），再在 Zenodo 里对本仓库开 archiving，
拿到的 DOI 形如 `10.5281/zenodo.xxxxxxx`。

正文里已经把 tag 链接写死成 `.../releases/tag/v1.0.0`（Key Resources Table、Resource
availability、Data availability 三处）。**如果你的实际 tag 不叫 v1.0.0，必须改这三处**，否则编辑
点进去是 404，等同于代码不可访问。Release 里建议放：README、`requirements-patterns.txt`、
`REPRODUCE.md`，以及一个 manifest 脚本目录（每张图/每张表对应一条可跑命令）。

### 3. 一次性填两个 DOI 并重建

```bash
python scripts/_fill_dois.py --check                       # 先看还剩几处
python scripts/_fill_dois.py --companion 10.xxxx/xxxxx --zenodo 10.5281/zenodo.xxxxxxx --build
python scripts/_qa_v22.py                                  # 重建后必须再跑一遍 QA
```

脚本会同时改 ref [1]、Key Resources Table 的 Zenodo 行、`**Code.**` 段、Data availability 段，并把投稿信里
"DOI will be inserted in place of the current placeholder" 换成真实 DOI。

---

## C. 一个待你决定的问题

**正文 17,461 词**（Introduction 至 Experimental Procedures，不含图注与表）。
TitlePage 已写明"要么在投稿信里申请豁免，要么压缩 Results"。

现状分布：Introduction 3,532 / Results 8,534 / Discussion 4,813 / Procedures 3,129。
若要压，唯一无损的位置是 Results 的剂量–反应枚举（逐剂量逐种子的数字，SI 表里已有），
把枚举换成一句汇总 + 指向 SI，预计可减 900–1,200 词，不动任何论证。
我倾向**不压**：Patterns 对研究论文没有硬性字数上限，而这个长度里没有冗余段落
（已查：正文无重复句），压缩只会让审稿人觉得关键数字被藏起来。但这是你的判断。

---

## C2. 若担心匹配度：Cell Press Multi-Journal Submission（MJS）

一个不需要多花一轮投稿周期的备选通道。官方口径（Cell Press 编辑部公告）：MJS 允许一篇稿件
同时送 **最多 6 本** Cell Press 期刊考虑（现有 27 本以上参与，含 Patterns 之外的物理科学刊
Device），由一名专职编辑协调，各刊**独立**决定是否送审；**超过 80% 的 MJS 投稿至少获得一本
期刊的评审机会**；2025 年通过 MJS 最终接收的论文里 70% 落在作者最初选中的目标刊之一。

对本稿最实际的两点：**MJS 初始投稿阶段大幅放宽格式要求**（17,461 词与 6 张主表不会被卡），
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
python scripts/_qa_v22.py                      # 格式硬指标（含 Highlights ≤85、In brief ≤50、Summary ≤150）
python scripts/_fill_dois.py --check           # 必须输出 "no placeholders left"
python -c "from docx import Document; d=Document('papers/20_MRP-ST-Repair_Patterns/Manuscript_Patterns.docx'); print(len(d.tables), 'main tables')"
```

期望：QA 全绿；占位 0；6 主表。
