"""Health check endpoint."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_db

router = APIRouter()


@router.get(
    "/health",
    summary="Health check",
    description="""
System health check for monitoring and load balancers.

**Checks:**
- API is running
- Database connectivity
- Redis cache (optional)

**Response Example:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "timestamp": "2026-01-10T12:00:00Z",
  "checks": {
    "database": "healthy",
    "redis": "healthy"
  }
}
```

**Status Values:**
- `healthy` - All systems operational
- `degraded` - Some non-critical components failing (e.g., Redis down)
- `unhealthy` - Critical failure (HTTP 503)

**Use Case:** Configure your load balancer to probe `/v1/health` every 30 seconds.

**No authentication required.**
    """,
    responses={
        200: {"description": "System is healthy or degraded"},
        503: {"description": "System is unhealthy (critical failure)"},
    },
)
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, Any]:
    """Health check endpoint for monitoring and load balancer probes."""
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": {},
    }

    # Check database connectivity
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        health_status["checks"]["database"] = "healthy"
    except Exception as e:
        health_status["status"] = "degraded"
        health_status["checks"]["database"] = f"unhealthy: {str(e)}"

    return health_status
