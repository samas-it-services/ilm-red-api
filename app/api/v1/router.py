"""Main API v1 router combining all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import health, auth, users, books

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, tags=["Health"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User endpoints
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Book endpoints
api_router.include_router(books.router, prefix="/books", tags=["Books"])

# Future endpoints (to be added in later phases)
# api_router.include_router(search.router, prefix="/search", tags=["Search"])
# api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
# api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])
