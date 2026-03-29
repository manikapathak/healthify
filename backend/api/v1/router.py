from fastapi import APIRouter

from backend.api.v1.analysis import router as analysis_router
from backend.api.v1.health import router as health_router
from backend.api.v1.reports import router as reports_router
from backend.api.v1.risk import router as risk_router

router = APIRouter()

router.include_router(health_router, tags=["health"])
router.include_router(reports_router, prefix="/reports", tags=["reports"])
router.include_router(analysis_router, prefix="/analysis", tags=["analysis"])
router.include_router(risk_router, prefix="/risk", tags=["risk"])
