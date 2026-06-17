"""Main API v1 router combining all endpoint routers."""

from fastapi import APIRouter

from app.api.v1 import (
    addons,
    admin,
    announcements,
    annotations,
    auth,
    billing,
    blog,
    book_club_ai,
    book_clubs,
    book_extras,
    books,
    cache,
    chat,
    director,
    errors,
    experts,
    files,
    gamification,
    health,
    help,
    issues,
    premium,
    progress,
    public_qa,
    quotes,
    rankings,
    rbac,
    recommendations,
    search,
    suggestions,
    users,
)

api_router = APIRouter()

# Health check (no auth required)
api_router.include_router(health.router, tags=["Health"])

# Authentication endpoints
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])

# User endpoints
api_router.include_router(users.router, prefix="/users", tags=["Users"])

# Book endpoints
api_router.include_router(books.router, prefix="/books", tags=["Books"])
api_router.include_router(book_extras.router, tags=["Book Extras"])

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

# Reading progress endpoints
api_router.include_router(progress.router, prefix="/progress", tags=["Progress"])

# Recommendations endpoints
api_router.include_router(recommendations.router, prefix="/recommendations", tags=["Recommendations"])

# Annotations endpoints (bookmarks, highlights, notes)
api_router.include_router(annotations.router, tags=["Annotations"])

# Book clubs endpoints
api_router.include_router(book_clubs.router, prefix="/book-clubs", tags=["Book Clubs"])

# Book club AI endpoints
api_router.include_router(book_club_ai.router, prefix="/book-clubs", tags=["Book Club AI"])

# Error logging endpoints
api_router.include_router(errors.router, prefix="/errors", tags=["Error Logging"])

# Premium endpoints
api_router.include_router(premium.router, prefix="/premium", tags=["Premium"])

# Issues / feature requests endpoints
api_router.include_router(issues.router, prefix="/issues", tags=["Issues"])

# Quotes endpoints
api_router.include_router(quotes.router, prefix="/quotes", tags=["Quotes"])

# Expert configuration endpoints
api_router.include_router(experts.router, prefix="/experts", tags=["Experts"])

# Suggestion system endpoints
api_router.include_router(suggestions.router, prefix="/suggestions", tags=["Suggestions"])

# Rankings endpoints
api_router.include_router(rankings.router, prefix="/rankings", tags=["Rankings"])

# Public Q&A endpoints
api_router.include_router(public_qa.router, prefix="/public-qa", tags=["Public Q&A"])

# Blog endpoints
api_router.include_router(blog.router, prefix="/blog", tags=["Blog"])

# Help/Documentation endpoints
api_router.include_router(help.router, prefix="/help", tags=["Help"])

# Feature announcements endpoints
api_router.include_router(announcements.router, prefix="/announcements", tags=["Announcements"])

# Director dashboard endpoints (director role required)
api_router.include_router(director.router, prefix="/director", tags=["Director Dashboard"])

# RBAC endpoints (roles, permissions, user roles)
api_router.include_router(rbac.router, tags=["RBAC"])

# Gamification endpoints
api_router.include_router(gamification.router, prefix="/gamification", tags=["Gamification"])

# Addon marketplace endpoints
api_router.include_router(addons.router, prefix="/addons", tags=["Addons"])
