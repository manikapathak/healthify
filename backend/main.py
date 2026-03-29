from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.v1.router import router as v1_router
from backend.config import settings

logger = structlog.get_logger()

_ROOT = Path(__file__).parent.parent
_REQUIRED_MODELS = [
    _ROOT / "models" / "isolation_forest.joblib",
    _ROOT / "models" / "classifier.joblib",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    missing = [str(p) for p in _REQUIRED_MODELS if not p.exists()]
    if missing:
        logger.error("missing_model_files", files=missing)
        raise RuntimeError(
            f"Required model files not found: {missing}. "
            "Run scripts/train_isolation_forest.py and scripts/train_classifier.py first."
        )
    logger.info("healthify_started", version=settings.app_version)
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Healthify",
        description="Blood Report Analysis System",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")

    return app


app = create_app()
