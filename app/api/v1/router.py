"""Main API v1 router combining all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import admin, auth, billing, books, cache, chat, files, health, search, users

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, tags=["Health"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User endpoints
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Book endpoints
api_router.include_router(books.router, prefix="/books", tags=["Books"])

# Chat endpoints
api_router.include_router(chat.router, prefix="/chats", tags=["Chat"])

# Billing endpoints
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])

# Cache management endpoints (admin only)
api_router.include_router(cache.router, prefix="/cache", tags=["Cache"])

# File serving endpoint (local storage only)
api_router.include_router(files.router, prefix="/files", tags=["Files"])

# Admin endpoints (admin role required)
api_router.include_router(admin.router, prefix="/admin", tags=["Admin"])

# Search endpoints
api_router.include_router(search.router, prefix="/search", tags=["Search"])

# Future endpoints (to be added in later phases)
# api_router.include_router(ai.router, prefix="/ai", tags=["AI"])
# api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])
