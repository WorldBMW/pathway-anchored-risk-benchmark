# 邮件：向昆士兰大学（UQ）申请 CIN3 宫颈 Visium 数据

> 目标论文：*Spatial analysis of HPV-associated cervical intraepithelial neoplastic tissues demonstrate distinct immune signatures associated with cervical cancer progression*, **The Journal of Pathology**, DOI **10.1002/path.70002**（2025/2026）
> 数据源：UQ eSpace **UQ:1bd2e07**（已公开 8 张 H&E TIFF；表达矩阵未公开）
> 数据代码库：GitHub **BiomedicalMachineLearning/CIN3**

---

## 收件人（按 UQ 标准邮箱格式推断，发前请核对）

| 角色 | 姓名 | 机构 | 建议邮箱 | 说明 |
|---|---|---|---|---|
| **主送（首选）** | **Quan Nguyen** | UQ 分子生物科学研究所（IMB） | `quan.nguyen@uq.edu.au` | 计算 PI，数据+代码库（BiomedicalMachineLearning）负责人，ORCID 0000-0001-7870-5703 |
| 抄送 | Gianna Pavilion | UQ IMB（第一作者） | `gianna.pavilion@uq.edu.au` | 实际执行分析者（仓库里有 "Gianna's R code"），回复通常最快 |
| 抄送 | Ian H Frazer | UQ Frazer Institute | `i.frazer@uq.edu.au` | 资深作者（HPV 疫苗共同发明人），有数据放行话语权 |

> ⚠️ 邮箱为 UQ 通用格式推断。**发送前 30 秒确认**：打开论文 PDF → 首页 `Correspondence` 脚注的邮箱即为通讯作者地址，把它设为主送最稳妥。若脚注是 Nguyen，则本表无误。

---

## 邮件正文（英文，可直接复制发送）

**Subject:** Data request – CIN3 Visium CytAssist cohort (J Pathol 2026, UQ eSpace UQ:1bd2e07)

Dear Dr. Nguyen,

I am **Bai Mingwei**, a researcher at **Jimei Technology Co., Ltd.**, currently working on a multimodal deep-learning framework that fuses 10x Visium spatial transcriptomics with H&E histology for cervical cancer subtyping and risk stratification.

Your recent paper, *"Spatial analysis of HPV-associated cervical intraepithelial neoplastic tissues demonstrate distinct immune signatures associated with cervical cancer progression"* (J Pathol, DOI 10.1002/path.70002), is directly relevant to our external-validation plan. We have assembled the only other public cervical Visium cohort (GSE208654, n=4) as our training set, but it is too small for independent validation. Your **7 CIN3 Visium CytAssist sections** would be an ideal, independent cervical lesion cohort.

The H&E images are already publicly available via UQ eSpace (UQ:1bd2e07). What we would need for computational reuse are the **spatial expression matrices** for the 7 CIN3 samples, i.e.:

- `filtered_feature_bc_matrix.h5` (or `barcodes.tsv` + `features.tsv` + `matrix.mtx.gz`), and
- spatial coordinate files (`tissue_positions_*.csv/.json`) and `scalefactors_json.json`.

We will: (1) use the data strictly for academic external validation; (2) cite your paper and acknowledge the UQ cohort; and (3) gladly offer co-authorship / methodological collaboration if the validation leads to a joint analysis. Data will not be redistributed.

Could you let us know the easiest way to obtain these files, or whether they could be deposited to GEO under a controlled-access token?

Thank you for considering this request.

Best regards,
**Bai Mingwei**
Researcher, Jimei Technology Co., Ltd.
[你的邮箱]  [你的 ORCID，选填]

---

## 备选：GitHub Issue（与邮件并行，常回得更快）

仓库：https://github.com/BiomedicalMachineLearning/CIN3 → New Issue

**Title:** Request for CIN3 Visium expression matrices (companion to UQ eSpace UQ:1bd2e07)

**Body:**
> Hi authors — I'm Bai Mingwei (Jimei Technology Co., Ltd.), building a Visium+H&E multimodal fusion model for cervical cancer. Your J Pathol 2026 CIN3 Visium CytAssist cohort (UQ:1bd2e07) is the only independent cervical lesion ST dataset we've found, and would be ideal external validation for our GSE208654-trained model. The H&E is already public; could you share the `filtered_feature_bc_matrix.h5` + spatial coordinates for the 7 CIN3 samples? Happy to cite, acknowledge, and collaborate (co-authorship) if it leads to a joint analysis. Thanks!

---

## 跟进节奏

1. 发送后 **2 周**无回复 → 发一封简短 follow-up（邮件 + Issue 各一次）。
2. 仍无回复 → 把主送改为 **Ian H Frazer**（`i.frazer@uq.edu.au`），说明已联系 Nguyen 组未获回复。
3. 若明确拒绝/无数据 → 把"公开无第二宫颈 Visium 队列、UQ CIN3 表达矩阵未公开（已联系作者待回复）"写入论文 Limitation；主外部验证改用 GSE316098（分子层，已下载验证）+ GSE281978/268014（跨器官方法学）。
