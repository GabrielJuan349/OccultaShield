from fastapi import APIRouter
from api.v1.endpoints import video
from api.v1 import progress

api_router = APIRouter()

api_router.include_router(video.router, prefix="/video", tags=["Video"])
api_router.include_router(progress.router, prefix="/process", tags=["Processing"])
