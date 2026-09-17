# 宫颈空间多模态模型 HTTP API

本目录是对现有 `scripts/train_st.py` 的独立 HTTP 封装，不修改项目原文件。API
产生的任务元数据、日志和结果全部保存在 `src/api/runtime/jobs/`。

## 1. 安装与启动

先进入项目使用的 Python 虚拟环境，并确保原项目依赖已经安装，然后补装 API 依赖：

```powershell
pip install -r src/api/requirements.txt
python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

启动后访问：

- Swagger 调试页：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

生产环境建议只监听内网地址，或在反向代理层增加鉴权；当前版本没有用户认证。

## 2. 提交任务

`POST /v1/predictions`

```json
{
  "slice_dir": "data/st_visium/cervical_cancer_1",
  "epochs": 40,
  "device": "auto",
  "fm": "uni",
  "n_genes": 2000,
  "batch_size": 256,
  "max_spots": 0,
  "hpv_gene_set": "kegg_hpv",
  "permutation_n": 2000
}
```

参数：

| 字段 | 必填 | 默认值 | 含义 |
|---|---:|---:|---|
| `slice_dir` | 是 | — | 项目目录内的10x Visium切片目录 |
| `epochs` | 否 | 40 | 单切片训练轮数，联调可用1–3 |
| `device` | 否 | `auto` | `auto`、`cpu`或`cuda` |
| `fm` | 否 | `uni` | `uni`、`uni2`、`chief`或`none` |
| `n_genes` | 否 | 2000 | 高变基因数 |
| `batch_size` | 否 | 256 | 训练批大小 |
| `max_spots` | 否 | 0 | spot上限；0表示标准Visium不限制，HD会由原脚本自动限流 |
| `hpv_gene_set` | 否 | `kegg_hpv` | HPV基因集模式 |
| `permutation_n` | 否 | 2000 | 置换检验次数 |

提交立即返回HTTP 202：

```json
{
  "job_id": "6ea9...",
  "status": "accepted",
  "status_url": "/v1/predictions/6ea9...",
  "message": "任务已提交；该项目会针对单切片训练/适配模型，请轮询status_url"
}
```

PowerShell调用示例：

```powershell
$body = @{
  slice_dir = "data/st_visium/cervical_cancer_1"
  epochs = 2
  device = "cpu"
  fm = "none"
} | ConvertTo-Json

$job = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/predictions `
  -ContentType "application/json" -Body $body
Invoke-RestMethod -Uri ("http://127.0.0.1:8000" + $job.status_url)
```

## 3. 查询和返回

`GET /v1/predictions/{job_id}`

状态依次为 `accepted`、`queued`、`running`，最后为 `succeeded` 或 `failed`。
成功后响应中的 `result` 包含主摘要字段，例如：

```json
{
  "job_id": "6ea9...",
  "status": "succeeded",
  "result": {
    "run_id": "API_6ea9...",
    "n_samples": 1,
    "n_spots": 2781,
    "fm": "uni",
    "hpv_gene_set_mode": "kegg_hpv",
    "moran_i": 0.82,
    "hpv_proxy_auc": 0.97,
    "per_sample_score": {"cervical_cancer_1": 0.31}
  },
  "artifact_urls": {
    "result.json": "/v1/predictions/6ea9.../artifacts/result.json",
    "run.log": "/v1/predictions/6ea9.../artifacts/run.log"
  }
}
```

完整结果通过 `result.json` 下载；训练标准输出在 `run.log`。具体结果字段由现有
`train_st.py` 产生，因此不同配置下部分统计字段可能为空或不存在。

## 4. 输入目录要求

标准Visium至少需要：

```text
slice_dir/
├── filtered_feature_bc_matrix.h5
└── spatial/
    ├── scalefactors_json.json
    ├── tissue_positions_list.csv（或 tissue_positions.csv）
    └── tissue_hires_image.png
```

API接收的是服务器本地目录路径，不接收几十GB数据的HTTP上传。`slice_dir` 被限制在
当前项目目录内。任务按顺序单并发执行，避免多个请求同时占满GPU显存。

## 5. 重要说明

当前项目没有发布完整主模型checkpoint。因此这个接口并非毫秒级固定权重推理，
而是调用现有训练管线对指定切片进行适配和评分。正式结果推荐 `epochs=40`、
`fm=uni`；仅验证接口连通性时可用 `epochs=1`、`fm=none`。

