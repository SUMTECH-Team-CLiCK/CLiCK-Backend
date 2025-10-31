from fastapi import APIRouter
from app.api.v1.routers import gpt,test
router = APIRouter(
    prefix="/api"
)

router.include_router(gpt.router, prefix="", tags=["imporve prompt"])
router.include_router(test.router, prefix="", tags=["test"])