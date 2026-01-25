"""Core router package that aggregates proxy and subscriber endpoints."""

from fastapi import APIRouter

from .root import router as root_router
from .proxy import router as proxy_router
from .subscribers import router as subscribers_router

router = APIRouter()
router.include_router(root_router)
router.include_router(proxy_router)
router.include_router(subscribers_router)

__all__ = ["router"]
