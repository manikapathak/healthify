from fastapi import APIRouter

from backend.api.schemas.common import APIResponse
from backend.config import settings

router = APIRouter()


@router.get("/health", response_model=APIResponse[dict])
async def health_check() -> APIResponse[dict]:
    return APIResponse.ok({"status": "ok", "version": settings.app_version})
