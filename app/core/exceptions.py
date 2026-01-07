"""Custom exception classes for API errors."""

from typing import Any

from fastapi import HTTPException, status


class APIError(HTTPException):
    """Base API error with structured response."""

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Any = None,
    ):
        self.code = code
        self.error_message = message
        self.details = details

        super().__init__(
            status_code=status_code,
            detail={
                "error": {
                    "code": code,
                    "message": message,
                    "details": details,
                }
            },
        )


class NotFoundError(APIError):
    """Resource not found error (404)."""

    def __init__(self, resource: str, resource_id: str | None = None):
        message = f"{resource} not found"
        if resource_id:
            message = f"{resource} with id '{resource_id}' not found"

        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            code="NOT_FOUND",
            message=message,
        )


class UnauthorizedError(APIError):
    """Authentication required error (401)."""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message=message,
        )


class ForbiddenError(APIError):
    """Permission denied error (403)."""

    def __init__(self, message: str = "Permission denied"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            code="FORBIDDEN",
            message=message,
        )


class ValidationError(APIError):
    """Validation error (422)."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            code="VALIDATION_ERROR",
            message=message,
            details=details,
        )


class ConflictError(APIError):
    """Resource conflict error (409)."""

    def __init__(self, message: str, details: Any = None):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            code="CONFLICT",
            message=message,
            details=details,
        )


class RateLimitError(APIError):
    """Rate limit exceeded error (429)."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int | None = None):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            details={"retry_after": retry_after} if retry_after else None,
        )


class PaymentRequiredError(APIError):
    """Premium feature requires payment (402)."""

    def __init__(self, message: str = "Premium subscription required"):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            code="PAYMENT_REQUIRED",
            message=message,
        )


class InsufficientCreditsError(APIError):
    """Insufficient AI credits error (402)."""

    def __init__(self, required: float, available: float):
        super().__init__(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            code="INSUFFICIENT_CREDITS",
            message="Insufficient AI credits",
            details={
                "required": required,
                "available": available,
            },
        )
