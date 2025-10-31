from fastapi import FastAPI
from app.api.v1.api import router as v1_router
from starlette.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CLiCK API",
    version="1.0.0"
)

# CORS 설정 추가#
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(v1_router)