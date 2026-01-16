"""API v1 Router Configuration.

This module defines the main API router for version 1 of the OccultaShield API.
It aggregates all endpoint routers and configures their prefixes and tags.

Routes:
    /video: Video upload, processing, and anonymization endpoints.
    /process: Real-time processing progress via Server-Sent Events.
"""

from fastapi import APIRouter
from api.v1.endpoints import video
from api.v1 import progress

api_router = APIRouter()

api_router.include_router(video.router, prefix="/video", tags=["Video"])
api_router.include_router(progress.router, prefix="/process", tags=["Processing"])
