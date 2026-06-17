"""Rate limiting configuration using slowapi with Redis storage."""

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.config import settings


def get_user_or_ip(request: Request) -> str:
    """Rate limit key: user ID if authenticated, IP otherwise."""
    from app.core.security import verify_access_token

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            payload = verify_access_token(auth[7:])
            if payload and payload.get("sub"):
                return f"user:{payload['sub']}"
        except Exception:
            pass
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(
    key_func=get_user_or_ip,
    storage_uri=str(settings.redis_url),
    strategy="fixed-window",
)
