"""Task-based HTTP wrapper around the existing single-slice training pipeline.

All API-owned files are written below ``src/api/runtime``.  The original
project sources, data and results are never modified by this module.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator


API_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = API_DIR.parents[1]
TRAIN_SCRIPT = PROJECT_ROOT / "scripts" / "train_st.py"
RUNTIME_DIR = API_DIR / "runtime"
JOBS_DIR = RUNTIME_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

_jobs: dict[str, dict[str, Any]] = {}
_jobs_lock = threading.Lock()
# A training run can consume all GPU memory. Queue API jobs one at a time.
_training_lock = threading.Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _write_job(job: dict[str, Any]) -> None:
    job_dir = JOBS_DIR / job["job_id"]
    job_dir.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in job.items() if not k.startswith("_")}
    (job_dir / "job.json").write_text(
        json.dumps(public, ensure_ascii=False, indent=2), encoding="utf-8"
    )


class PredictionRequest(BaseModel):
    """One 10x Visium slide and the supported train_st.py controls."""

    slice_dir: str = Field(
        ...,
        description="Visium切片目录；可传项目内相对路径或绝对路径",
        examples=["data/st_visium/cervical_cancer_1"],
    )
    epochs: int = Field(40, ge=1, le=200)
    device: Literal["auto", "cpu", "cuda"] = "auto"
    fm: Literal["uni", "uni2", "chief", "none"] = "uni"
    n_genes: int = Field(2000, ge=200, le=10000)
    batch_size: int = Field(256, ge=1, le=2048)
    max_spots: int = Field(0, ge=0)
    hpv_gene_set: Literal["default", "kegg_hpv", "dropout_20pct"] = "kegg_hpv"
    permutation_n: int = Field(2000, ge=100, le=100000)

    @field_validator("slice_dir")
    @classmethod
    def non_empty_path(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("slice_dir不能为空")
        return value.strip()


class SubmitResponse(BaseModel):
    job_id: str
    status: str
    status_url: str
    message: str


def _resolve_slide(raw: str) -> Path:
    candidate = Path(raw).expanduser()
    if not candidate.is_absolute():
        candidate = PROJECT_ROOT / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise HTTPException(400, "slice_dir必须位于项目目录内") from exc
    if not candidate.is_dir():
        raise HTTPException(400, f"切片目录不存在: {candidate}")
    standard_h5 = candidate / "filtered_feature_bc_matrix.h5"
    hd_h5 = list((candidate / "binned_outputs").glob("*/filtered_feature_bc_matrix.h5"))
    if not standard_h5.exists() and not hd_h5:
        raise HTTPException(400, "目录中未找到filtered_feature_bc_matrix.h5（标准Visium或HD）")
    return candidate


def _set_job(job_id: str, **changes: Any) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs[job_id]
        job.update(changes)
        _write_job(job)
        return dict(job)


def _result_summary(raw: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "run_id", "n_samples", "n_spots", "fm", "hpv_gene_set_mode",
        "hpv_gene_set_size", "recon_mse_proxy", "score_median", "moran_i",
        "moran_perm_p", "hpv_proxy_auc", "hpv_gene_high_low_gap",
        "n_deg_perm_fdr05_effect", "per_sample_spots", "per_sample_score",
    )
    return {key: raw[key] for key in keys if key in raw}


def _run_job(job_id: str, request: PredictionRequest, slide_dir: Path) -> None:
    job_dir = JOBS_DIR / job_id
    work_dir = job_dir / "work"
    work_dir.mkdir(parents=True, exist_ok=True)
    log_path = job_dir / "run.log"
    run_id = f"API_{job_id}"
    result_path = work_dir / "results" / f"results_{run_id}.json"
    device = request.device
    if device == "auto":
        # train_st.py itself picks CUDA when available if --device is omitted.
        device_args: list[str] = []
    else:
        device_args = ["--device", device]
    cmd = [
        sys.executable, "-u", str(TRAIN_SCRIPT),
        "--data", str(slide_dir),
        "--epochs", str(request.epochs),
        "--bs", str(request.batch_size),
        "--n_genes", str(request.n_genes),
        "--fm", request.fm,
        "--max_spots", str(request.max_spots),
        "--hpv_gene_set", request.hpv_gene_set,
        "--permutation_n", str(request.permutation_n),
        "--run_id", run_id,
        *device_args,
    ]
    try:
        _set_job(job_id, status="queued", command=cmd)
        with _training_lock:
            _set_job(job_id, status="running", started_at=_utc_now())
            env = os.environ.copy()
            env["PYTHONPATH"] = str(PROJECT_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
            env.setdefault("PYTHONHASHSEED", "42")
            env.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
            with log_path.open("w", encoding="utf-8", errors="replace") as log:
                proc = subprocess.run(
                    cmd,
                    cwd=work_dir,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    text=True,
                    check=False,
                )
        if proc.returncode != 0:
            _set_job(
                job_id,
                status="failed",
                finished_at=_utc_now(),
                exit_code=proc.returncode,
                error="模型进程执行失败，请查看run.log",
            )
            return
        if not result_path.exists():
            raise RuntimeError(f"模型进程成功结束，但未生成结果文件: {result_path}")
        raw = json.loads(result_path.read_text(encoding="utf-8"))
        _set_job(
            job_id,
            status="succeeded",
            finished_at=_utc_now(),
            exit_code=0,
            result=_result_summary(raw),
            artifacts=["result.json", "run.log"],
        )
        # Stable API-owned artifact name; leave train_st.py's raw output intact.
        (job_dir / "result.json").write_text(
            json.dumps(raw, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception as exc:  # keep background failures visible through HTTP
        (job_dir / "exception.log").write_text(traceback.format_exc(), encoding="utf-8")
        _set_job(
            job_id,
            status="failed",
            finished_at=_utc_now(),
            error=f"{type(exc).__name__}: {exc}",
            artifacts=[name for name in ("run.log", "exception.log") if (job_dir / name).exists()],
        )


app = FastAPI(
    title="Cervix Spatial Multimodal API",
    version="1.0.0",
    description="10x Visium单切片HPV空间风险评分任务接口",
)


@app.get("/health")
def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "project_root": str(PROJECT_ROOT),
        "python": sys.executable,
        "train_script_found": TRAIN_SCRIPT.exists(),
    }


@app.post("/v1/predictions", response_model=SubmitResponse, status_code=202)
def submit_prediction(request: PredictionRequest) -> SubmitResponse:
    slide_dir = _resolve_slide(request.slice_dir)
    job_id = uuid.uuid4().hex
    job = {
        "job_id": job_id,
        "status": "accepted",
        "created_at": _utc_now(),
        "request": request.model_dump(),
        "resolved_slice_dir": str(slide_dir),
    }
    with _jobs_lock:
        _jobs[job_id] = job
        _write_job(job)
    threading.Thread(target=_run_job, args=(job_id, request, slide_dir), daemon=True).start()
    return SubmitResponse(
        job_id=job_id,
        status="accepted",
        status_url=f"/v1/predictions/{job_id}",
        message="任务已提交；该项目会针对单切片训练/适配模型，请轮询status_url",
    )


@app.get("/v1/predictions/{job_id}")
def get_prediction(job_id: str) -> dict[str, Any]:
    with _jobs_lock:
        job = _jobs.get(job_id)
    if job is None:
        saved = JOBS_DIR / job_id / "job.json"
        if not saved.exists():
            raise HTTPException(404, "任务不存在")
        job = json.loads(saved.read_text(encoding="utf-8"))
    response = {k: v for k, v in job.items() if not k.startswith("_") and k != "command"}
    if response.get("artifacts"):
        response["artifact_urls"] = {
            name: f"/v1/predictions/{job_id}/artifacts/{name}"
            for name in response["artifacts"]
        }
    return response


@app.get("/v1/predictions/{job_id}/artifacts/{name}")
def download_artifact(job_id: str, name: str) -> FileResponse:
    allowed = {"result.json", "run.log", "exception.log"}
    if name not in allowed:
        raise HTTPException(404, "产物不存在")
    path = JOBS_DIR / job_id / name
    if not path.is_file():
        raise HTTPException(404, "产物尚未生成或任务不存在")
    media = "application/json" if name.endswith(".json") else "text/plain"
    return FileResponse(path, media_type=media, filename=f"{job_id}_{name}")

