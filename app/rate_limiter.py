"""Rate limiting configuration using slowapi."""

from slowapi import Limiter
from slowapi.util import get_remote_address

# Rate limiter instance - uses client IP as key
# This can be imported throughout the application without circular imports
limiter = Limiter(key_func=get_remote_address)
