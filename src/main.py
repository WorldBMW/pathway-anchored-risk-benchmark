"""Cervix spatial multimodal API launcher.

Examples:
    python src/main.py
    python src/main.py --host 0.0.0.0 --port 8000
    python src/main.py --reload
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


# Running ``python src/main.py`` puts ``src`` rather than the repository root
# on sys.path. Add the root so ``src.api.app`` can always be imported.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@dataclass(frozen=True)
class ApiServer:
    """Configuration and startup entry point for the FastAPI service."""

    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1
    reload: bool = False
    log_level: str = "info"

    def run(self) -> None:
        try:
            import uvicorn
        except ImportError as exc:
            raise SystemExit(
                "缺少API依赖，请先执行：\n"
                "  pip install -r src/api/requirements.txt"
            ) from exc

        # Uvicorn does not support multiple workers together with reload.
        workers = 1 if self.reload else self.workers
        print(
            "Cervix Spatial Multimodal API starting\n"
            f"  address : http://{self.host}:{self.port}\n"
            f"  docs    : http://127.0.0.1:{self.port}/docs\n"
            f"  health  : http://127.0.0.1:{self.port}/health\n"
            f"  workers : {workers}\n",
            flush=True,
        )
        uvicorn.run(
            "src.api.app:app",
            host=self.host,
            port=self.port,
            workers=workers,
            reload=self.reload,
            log_level=self.log_level,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="启动宫颈空间多模态模型HTTP API")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址，默认0.0.0.0")
    parser.add_argument("--port", type=int, default=8000, help="监听端口，默认8000")
    parser.add_argument("--workers", type=int, default=1, help="服务进程数，默认1")
    parser.add_argument("--reload", action="store_true", help="开发模式：代码变化时自动重启")
    parser.add_argument(
        "--log-level",
        choices=("critical", "error", "warning", "info", "debug", "trace"),
        default="info",
        help="Uvicorn日志级别",
    )
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port必须在1到65535之间")
    if args.workers < 1:
        parser.error("--workers必须大于等于1")
    return args


def main() -> None:
    args = parse_args()
    ApiServer(
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
        log_level=args.log_level,
    ).run()


if __name__ == "__main__":
    main()

