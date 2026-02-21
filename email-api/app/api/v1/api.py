"""API v1 router aggregation."""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, bigdata, dashboard, emails, mailbox, websocket

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(mailbox.router, prefix="/mailbox", tags=["mailbox"])
api_router.include_router(websocket.router, tags=["websocket"])
api_router.include_router(bigdata.router, prefix="/bigdata", tags=["bigdata"])
