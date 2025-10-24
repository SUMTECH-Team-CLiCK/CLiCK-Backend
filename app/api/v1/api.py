from fastapi import APIRouter
from app.api.v1.routers import gpt
router = APIRouter(
    prefix="/api"
)

router.include_router(gpt.router, prefix="", tags=["imporve prompt"])