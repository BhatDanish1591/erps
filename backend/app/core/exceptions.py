from __future__ import annotations

from typing import Any, Dict, List, Optional


class AppException(Exception):
    """Base exception for the application."""
    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message: str = "An unexpected error occurred"

    def __init__(
        self,
        *args: Any,
        message: Optional[str] = None,
        details: Optional[List[Dict[str, Any]]] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
    ) -> None:
        if args and isinstance(args[0], int):
            # Positional style: AppException(status_code, error_code, message, details)
            self.status_code = args[0]
            if len(args) > 1 and isinstance(args[1], str):
                self.error_code = args[1]
            if len(args) > 2 and isinstance(args[2], str):
                self.message = args[2]
            if len(args) > 3 and isinstance(args[3], list):
                self.details = args[3]
            else:
                self.details = details or []
        elif args and isinstance(args[0], str):
            # Standard style: AppException(message, details)
            self.message = args[0]
            self.details = args[1] if len(args) > 1 and isinstance(args[1], list) else (details or [])
        else:
            self.message = message or self.message
            self.details = details or []

        if status_code is not None:
            self.status_code = status_code
        if error_code is not None:
            self.error_code = error_code
        super().__init__(self.message)


class ValidationException(AppException):
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message = "Validation failed"


class BadRequestException(AppException):
    status_code = 400
    error_code = "BAD_REQUEST"
    message = "Bad request"


class AuthenticationException(AppException):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication required"


class AuthorizationException(AppException):
    status_code = 403
    error_code = "AUTHORIZATION_ERROR"
    message = "You do not have permission to perform this action"


ForbiddenException = AuthorizationException


class NotFoundException(AppException):
    status_code = 404
    error_code = "NOT_FOUND"
    message = "Resource not found"


class ConflictException(AppException):
    status_code = 409
    error_code = "CONFLICT"
    message = "Resource already exists"


class TenantException(AppException):
    status_code = 403
    error_code = "TENANT_ACCESS_DENIED"
    message = "Access to this tenant is not allowed"


class RateLimitException(AppException):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later."


class ServiceUnavailableException(AppException):
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    message = "Service temporarily unavailable"
